"""
End-to-End Test: Extract -> Chunk -> Ingest -> Deduplicate
Tests the complete pipeline with Weaviate ingestion
"""

import sys
import logging
from pathlib import Path

from multi_format_pipeline import MultiFormatPipeline
from weaviate_integration.ingester_v2 import WeaviateIngesterV2
from weaviate_integration.deduplication_tracker import DeduplicationTracker


def test_end_to_end(test_file: str, max_pages: int = 2):
    """
    Test complete pipeline end-to-end.

    Args:
        test_file: Path to test PDF
        max_pages: Max pages to process
    """
    print("\n" + "="*80)
    print("END-TO-END PIPELINE TEST")
    print("="*80)
    print(f"Test File: {test_file}")
    print(f"Max Pages: {max_pages}")

    # Step 1: Initialize components
    print("\nStep 1: Initializing components...")
    pipeline = MultiFormatPipeline()
    ingester = WeaviateIngesterV2(collection_name="InteliaKnowledgeBase")
    tracker = DeduplicationTracker()
    print("OK Components initialized")

    # Step 2: Check if already processed
    print("\nStep 2: Checking deduplication...")
    if tracker.is_processed(test_file):
        processed_info = tracker.get_processed_info(test_file)
        print(f"WARNING - File already processed:")
        print(f"  Timestamp: {processed_info['processed_timestamp']}")
        print(f"  Chunks: {processed_info['chunks_created']}")
        print(f"\nTo reprocess, remove from tracker:")
        print(f"  tracker.remove_document('{test_file}')")
        return False
    else:
        print("OK File not yet processed")

    # Step 3: Extract and chunk
    print("\nStep 3: Running extraction pipeline...")
    result = pipeline.process_file(test_file, max_pages=max_pages)

    if not result.success:
        print(f"FAILED: {result.error}")
        return False

    print("OK Pipeline complete")
    print(f"  Chunks created: {len(result.chunks_with_metadata)}")
    print(f"  Metadata confidence: {result.metadata_summary['overall_confidence']:.2%}")

    # Step 4: Ingest to Weaviate
    print("\nStep 4: Ingesting to Weaviate...")
    ingestion_stats = ingester.ingest_chunks(result.chunks_with_metadata)

    print(f"OK Ingestion complete")
    print(f"  Success: {ingestion_stats['success']}")
    print(f"  Failed: {ingestion_stats['failed']}")

    if ingestion_stats['failed'] > 0:
        print(f"WARNING: Some chunks failed to ingest")

    # Step 5: Mark as processed
    print("\nStep 5: Marking as processed...")
    tracker.mark_as_processed(
        file_path=test_file,
        chunks_created=len(result.chunks_with_metadata),
        metadata_summary=result.metadata_summary
    )
    print("OK Marked as processed")

    # Step 6: Verify deduplication
    print("\nStep 6: Verifying deduplication...")
    if tracker.is_processed(test_file):
        print("OK Deduplication working - file marked as processed")
    else:
        print("FAILED: Deduplication not working")
        return False

    # Step 7: Get collection stats
    print("\nStep 7: Weaviate collection statistics...")
    collection_stats = ingester.get_collection_stats()
    print(f"  Collection: {collection_stats['collection_name']}")
    print(f"  Total chunks: {collection_stats.get('total_chunks', 0)}")
    print(f"  Status: {collection_stats.get('status', 'unknown')}")

    # Step 8: Tracker statistics
    print("\nStep 8: Deduplication tracker statistics...")
    tracker_stats = tracker.get_statistics()
    print(f"  Total documents: {tracker_stats['total_documents']}")
    print(f"  Total chunks: {tracker_stats['total_chunks']}")
    print(f"  Total size: {tracker_stats['total_size_mb']} MB")

    print("\n" + "="*80)
    print("END-TO-END TEST: SUCCESS")
    print("="*80)
    print("\nNext Steps:")
    print("  1. Run batch processing: python batch_process_documents.py")
    print("  2. Process all 54 PDFs in library")
    print("  3. Query Weaviate to verify data")

    # Close connections
    ingester.close()

    return True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test file
    test_file = "C:/Software_Development/intelia-cognito/data-pipelines/documents/Sources/intelia/public/veterinary_services/common/ascites.pdf"

    if len(sys.argv) > 1:
        test_file = sys.argv[1]

    max_pages = 2
    if len(sys.argv) > 2:
        max_pages = int(sys.argv[2])

    # Run test
    success = test_end_to_end(test_file, max_pages)

    sys.exit(0 if success else 1)
