"""
Batch Document Processor with Deduplication
Processes all documents in a directory, skipping already-processed files
"""

import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from multi_format_pipeline import MultiFormatPipeline
from weaviate_integration.ingester_v2 import WeaviateIngesterV2
from weaviate_integration.deduplication_tracker import DeduplicationTracker


class BatchDocumentProcessor:
    """
    Batch processor for multi-format documents with deduplication.

    Features:
    - Processes PDF, DOCX, and web pages
    - Automatic deduplication (skips already-processed files)
    - Progress tracking with statistics
    - Error handling and recovery
    - Weaviate ingestion integration
    """

    def __init__(
        self,
        base_directory: str,
        collection_name: str = "InteliaKnowledgeBase",
        max_pages_per_pdf: int = None
    ):
        """
        Initialize batch processor.

        Args:
            base_directory: Root directory containing documents
            collection_name: Weaviate collection name
            max_pages_per_pdf: Optional limit on PDF pages
        """
        self.base_directory = Path(base_directory)
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.pipeline = MultiFormatPipeline()
        self.ingester = WeaviateIngesterV2(collection_name=collection_name)
        self.tracker = DeduplicationTracker()

        self.max_pages_per_pdf = max_pages_per_pdf

        # Statistics
        self.stats = {
            "total_found": 0,
            "already_processed": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0
        }

    def find_documents(self, extensions: List[str] = None) -> List[Path]:
        """
        Find all documents in base directory.

        Args:
            extensions: List of file extensions (default: ['.pdf', '.docx', '.doc'])

        Returns:
            List of document paths
        """
        if extensions is None:
            extensions = ['.pdf', '.docx', '.doc']

        documents = []

        for ext in extensions:
            documents.extend(self.base_directory.rglob(f"*{ext}"))

        return sorted(documents)

    def process_all(
        self,
        extensions: List[str] = None,
        force_reprocess: bool = False,
        delay_seconds: int = 2
    ) -> Dict[str, Any]:
        """
        Process all documents in base directory.

        Args:
            extensions: File extensions to process
            force_reprocess: If True, reprocess even if already done
            delay_seconds: Delay between documents (for API rate limiting)

        Returns:
            Processing statistics
        """
        print("\n" + "="*80)
        print("BATCH DOCUMENT PROCESSING - START")
        print("="*80)
        print(f"Base Directory: {self.base_directory}")
        print(f"Collection: {self.ingester.collection_name}")
        print(f"Force Reprocess: {force_reprocess}")
        print(f"Delay: {delay_seconds}s between documents")

        # Find all documents
        documents = self.find_documents(extensions)
        self.stats["total_found"] = len(documents)

        print(f"\nFound {len(documents)} documents")

        if len(documents) == 0:
            print("\nNo documents to process")
            return self.stats

        # Process each document
        start_time = datetime.now()

        for i, doc_path in enumerate(documents, 1):
            print(f"\n{'-'*80}")
            print(f"[{i}/{len(documents)}] {doc_path.relative_to(self.base_directory)}")
            print(f"{'-'*80}")

            # Check if already processed
            if not force_reprocess and self.tracker.is_processed(doc_path):
                processed_info = self.tracker.get_processed_info(doc_path)
                print(f"SKIPPED - Already processed")
                print(f"  Processed: {processed_info['processed_timestamp']}")
                print(f"  Chunks: {processed_info['chunks_created']}")
                self.stats["already_processed"] += 1
                continue

            # Process document
            try:
                result = self._process_single_document(doc_path)

                if result["success"]:
                    self.stats["processed"] += 1
                    self.stats["total_chunks"] += result["chunks_created"]
                    print(f"SUCCESS")
                    print(f"  Chunks created: {result['chunks_created']}")
                    print(f"  Ingested to Weaviate: {result['ingested']}")
                else:
                    self.stats["failed"] += 1
                    print(f"FAILED: {result.get('error', 'Unknown error')}")

            except Exception as e:
                self.stats["failed"] += 1
                self.logger.error(f"Error processing {doc_path}: {e}")
                print(f"FAILED: {e}")

            # Rate limiting delay
            if i < len(documents):
                time.sleep(delay_seconds)

        # Final statistics
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        print(f"\n{'='*80}")
        print("BATCH PROCESSING COMPLETE")
        print(f"{'='*80}")
        print(f"Total Found: {self.stats['total_found']}")
        print(f"Already Processed (skipped): {self.stats['already_processed']}")
        print(f"Newly Processed: {self.stats['processed']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Total Chunks Created: {self.stats['total_chunks']}")
        print(f"Elapsed Time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")

        if self.stats['processed'] > 0:
            avg_time = elapsed / self.stats['processed']
            print(f"Average Time per Document: {avg_time:.1f}s")

        # Show tracker statistics
        tracker_stats = self.tracker.get_statistics()
        print(f"\nOverall Statistics:")
        print(f"  Total documents in tracker: {tracker_stats['total_documents']}")
        print(f"  Total chunks in tracker: {tracker_stats['total_chunks']}")
        print(f"  Total size: {tracker_stats['total_size_mb']} MB")

        return self.stats

    def _process_single_document(self, doc_path: Path) -> Dict[str, Any]:
        """
        Process a single document end-to-end.

        Args:
            doc_path: Path to document

        Returns:
            Processing result dictionary
        """
        # Step 1: Extract and chunk
        pipeline_result = self.pipeline.process_file(
            str(doc_path),
            max_pages=self.max_pages_per_pdf
        )

        if not pipeline_result.success:
            return {
                "success": False,
                "error": pipeline_result.error,
                "chunks_created": 0,
                "ingested": False
            }

        # Step 2: Ingest to Weaviate
        ingestion_stats = self.ingester.ingest_chunks(pipeline_result.chunks_with_metadata)

        if ingestion_stats["failed"] > 0:
            self.logger.warning(
                f"Partial ingestion failure: {ingestion_stats['failed']} chunks failed"
            )

        # Step 3: Mark as processed in tracker
        self.tracker.mark_as_processed(
            file_path=doc_path,
            chunks_created=len(pipeline_result.chunks_with_metadata),
            metadata_summary=pipeline_result.metadata_summary
        )

        return {
            "success": True,
            "chunks_created": len(pipeline_result.chunks_with_metadata),
            "ingested": ingestion_stats["success"] > 0,
            "ingestion_stats": ingestion_stats
        }


# CLI Interface
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Default configuration
    base_dir = "C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources"
    collection_name = "InteliaKnowledgeBase"
    force_reprocess = False

    # Parse command line arguments
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]

    if len(sys.argv) > 2:
        if sys.argv[2].lower() in ['true', '1', 'yes', 'force']:
            force_reprocess = True

    # Initialize processor
    processor = BatchDocumentProcessor(
        base_directory=base_dir,
        collection_name=collection_name,
        max_pages_per_pdf=None  # No limit
    )

    # Process all documents
    stats = processor.process_all(
        extensions=['.pdf'],  # Start with PDFs only
        force_reprocess=force_reprocess,
        delay_seconds=2  # 2 second delay between documents
    )

    # Exit code based on results
    if stats["failed"] > 0 and stats["processed"] == 0:
        sys.exit(1)  # Complete failure
    elif stats["failed"] > 0:
        sys.exit(2)  # Partial failure
    else:
        sys.exit(0)  # Success
