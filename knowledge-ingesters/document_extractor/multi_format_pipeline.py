"""
Multi-Format Knowledge Extraction Pipeline
Processes PDF, DOCX, and Web documents into Weaviate

Pipeline flow:
1. File type detection
2. Content extraction (PDF Text [FREE pdfplumber] / DOCX Text / Web Scrape)
3. Path-based classification (70%)
4. Vision-based enrichment (25%)
5. Smart defaults (5%)
6. Text chunking (600 words, 120 overlap) + Quality scoring + Entity extraction
7. Weaviate ingestion

Cost savings: ~490$ USD for 54 PDFs by using FREE pdfplumber instead of Claude Vision
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()  # Load from .env in current directory
# Also try parent directories
if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("CLAUDE_API_KEY"):
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from: {env_path}")

# Core extractors
from core.pdf_text_extractor import PDFTextExtractor, PDFExtractionResult  # FREE pdfplumber (was: pdf_vision_extractor)
from core.docx_extractor import DOCXExtractor, DOCXExtractionResult
from core.web_scraper import WebScraper, WebExtractionResult
from core.path_based_classifier import PathBasedClassifier, PathMetadata
from core.metadata_enricher import MetadataEnricher, EnrichedMetadata
from core.chunking_service import ChunkingService, ChunkConfig


@dataclass
class PipelineResult:
    """Result of pipeline processing"""
    file_path: str
    success: bool
    chunks_created: int
    chunks_ingested: int
    extraction_method: str
    chunks_with_metadata: List[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata_summary: Dict[str, Any] = None


class MultiFormatPipeline:
    """
    Process multi-format documents through complete extraction pipeline.

    Supported formats:
    - PDF (via FREE pdfplumber - saves ~490$ on 54 PDFs!)
    - DOCX (via python-docx)
    - Web pages (via requests + BeautifulSoup)

    Note: Claude Vision API still available for table_extractor (specialized table extraction)
    """

    def __init__(self):
        """Initialize pipeline with all components"""
        print("Initializing Multi-Format Knowledge Extraction Pipeline...")

        # Extractors
        self.pdf_extractor = PDFTextExtractor()  # FREE pdfplumber (was: PDFVisionExtractor)
        self.docx_extractor = DOCXExtractor()
        self.web_scraper = WebScraper()

        # Classifiers
        self.path_classifier = PathBasedClassifier()
        self.metadata_enricher = MetadataEnricher()

        # Chunking
        self.chunking_service = ChunkingService(
            config=ChunkConfig(
                min_chunk_words=50,
                max_chunk_words=600,  # VALIDATED: Optimal for text-embedding-3-large
                overlap_words=120,  # 20% overlap
                prefer_markdown_sections=True,
                prefer_paragraph_boundaries=True,
                prefer_sentence_boundaries=True
            )
        )

        print("Pipeline initialized successfully")

    def process_file(self, file_path: str, max_pages: Optional[int] = None) -> PipelineResult:
        """
        Process a single file through the complete pipeline.

        Args:
            file_path: Path to file (PDF, DOCX) or URL (web page)
            max_pages: For PDFs, max pages to process (None = all)

        Returns:
            PipelineResult with processing summary
        """
        print(f"\n{'='*80}")
        print(f"PROCESSING: {file_path}")
        print(f"{'='*80}\n")

        try:
            # Step 1: Detect file type and extract content
            extraction_method, full_text, extraction_metadata = self._extract_content(
                file_path, max_pages
            )

            if not full_text:
                return PipelineResult(
                    file_path=file_path,
                    success=False,
                    chunks_created=0,
                    chunks_ingested=0,
                    extraction_method=extraction_method,
                    error="No text content extracted"
                )

            print(f"OK Content extracted: {len(full_text)} characters")
            print(f"  Method: {extraction_method}")

            # Step 2: Path-based classification (70%)
            print("\nStep 2: Path-based classification...")
            path_metadata = self.path_classifier.classify_path(file_path)
            print(f"OK Path classification complete")
            print(f"  Org: {path_metadata.owner_org_id}")
            print(f"  Site: {path_metadata.site_type}")
            print(f"  Breed: {path_metadata.breed}")
            print(f"  Confidence: {path_metadata.confidence_score:.2f}")

            # Step 3: Vision-based enrichment (25%) + Smart defaults (5%)
            print("\nStep 3: Metadata enrichment...")
            enriched_metadata = self.metadata_enricher.enrich_metadata(
                path_metadata=self._path_to_dict(path_metadata),
                document_text=full_text,
                extraction_method=extraction_method
            )
            print(f"OK Metadata enrichment complete")
            print(f"  Species: {enriched_metadata.species}")
            print(f"  Genetic Line: {enriched_metadata.genetic_line}")
            print(f"  Document Type: {enriched_metadata.document_type}")
            print(f"  Overall Confidence: {enriched_metadata.overall_confidence:.2f}")

            # Step 4: Text chunking with quality scoring + entity extraction
            print("\nStep 4: Text chunking (600 words, 120 overlap) + Quality scoring + Entity extraction...")
            chunk_objects = self.chunking_service.chunk_text(
                text=full_text,
                metadata={"extraction_method": extraction_method}
            )
            print(f"OK Created {len(chunk_objects)} enriched chunks")

            # Step 5: Prepare for ingestion (would integrate with Weaviate here)
            print("\nStep 5: Preparing chunks for ingestion...")
            chunks_with_metadata = self._prepare_chunks_for_ingestion(
                chunk_objects, enriched_metadata
            )
            print(f"OK {len(chunks_with_metadata)} chunks ready for Weaviate")

            # TODO: Step 6: Ingest into Weaviate
            # This would call the updated WeaviateIngester with new schema

            return PipelineResult(
                file_path=file_path,
                success=True,
                chunks_created=len(chunk_objects),
                chunks_ingested=0,  # TODO: Update when ingestion implemented
                extraction_method=extraction_method,
                chunks_with_metadata=chunks_with_metadata,
                metadata_summary={
                    "owner_org_id": enriched_metadata.owner_org_id,
                    "visibility_level": enriched_metadata.visibility_level,
                    "site_type": enriched_metadata.site_type,
                    "breed": enriched_metadata.breed,
                    "species": enriched_metadata.species,
                    "genetic_line": enriched_metadata.genetic_line,
                    "document_type": enriched_metadata.document_type,
                    "overall_confidence": enriched_metadata.overall_confidence
                }
            )

        except Exception as e:
            return PipelineResult(
                file_path=file_path,
                success=False,
                chunks_created=0,
                chunks_ingested=0,
                extraction_method="unknown",
                error=str(e)
            )

    def _extract_content(
        self, file_path: str, max_pages: Optional[int]
    ) -> tuple[str, str, Dict[str, Any]]:
        """
        Extract content based on file type.

        Returns:
            (extraction_method, full_text, metadata)
        """
        file_path_lower = file_path.lower()

        # PDF
        if file_path_lower.endswith('.pdf'):
            result = self.pdf_extractor.extract_pdf(file_path, max_pages=max_pages)
            if not result.success:
                raise Exception(f"PDF extraction failed: {result.error}")
            return "pdf_text", result.full_text, result.metadata  # Using FREE pdfplumber (was: pdf_vision)

        # DOCX
        elif file_path_lower.endswith('.docx'):
            result = self.docx_extractor.extract_docx(file_path)
            if not result.success:
                raise Exception(f"DOCX extraction failed: {result.error}")
            return "docx_text", result.full_text, result.metadata

        # Web page (URL)
        elif file_path.startswith('http://') or file_path.startswith('https://'):
            result = self.web_scraper.extract_web_page(file_path)
            if not result.success:
                raise Exception(f"Web scraping failed: {result.error}")
            return "web_scrape", result.full_text, result.metadata

        else:
            raise Exception(f"Unsupported file type: {file_path}")

    def _path_to_dict(self, path_metadata: PathMetadata) -> Dict[str, Any]:
        """Convert PathMetadata to dictionary"""
        return {
            "owner_org_id": path_metadata.owner_org_id,
            "visibility_level": path_metadata.visibility_level,
            "site_type": path_metadata.site_type,
            "breed": path_metadata.breed,
            "category": path_metadata.category,
            "subcategory": path_metadata.subcategory,
            "climate_zone": path_metadata.climate_zone,
            "source_file": path_metadata.source_file,
            "filename": path_metadata.filename,
            "confidence_score": path_metadata.confidence_score
        }

    def _prepare_chunks_for_ingestion(
        self, chunk_objects: List, metadata: EnrichedMetadata
    ) -> List[Dict[str, Any]]:
        """
        Prepare chunks with metadata for Weaviate ingestion.

        Each chunk gets:
        - Full enriched metadata (path-based + vision-based)
        - Quality scores from chunk_quality_scorer
        - Extracted entities from entity_extractor
        """
        prepared_chunks = []

        for chunk in chunk_objects:
            # Start with base chunk metadata (quality scores + entities)
            chunk_data = chunk.metadata.copy()

            # Add content and basic info
            chunk_data.update({
                "content": chunk.content,
                "word_count": chunk.word_count,
                "chunk_id": f"{metadata.source_file}_{chunk.chunk_index}",

                # Path-based metadata (70%)
                "owner_org_id": metadata.owner_org_id,
                "visibility_level": metadata.visibility_level,
                "site_type": metadata.site_type,
                "breed": metadata.breed,
                "category": metadata.category,
                "subcategory": metadata.subcategory,
                "climate_zone": metadata.climate_zone,

                # Vision-based metadata (25%)
                "species": metadata.species,
                "genetic_line": metadata.genetic_line,
                "company": metadata.company,
                "document_type": metadata.document_type,
                "target_audience": metadata.target_audience,
                "technical_level": metadata.technical_level,
                "topics": metadata.topics,

                # Document-level
                "language": metadata.language,
                "unit_system": metadata.unit_system,

                # Confidence scores
                "path_confidence": metadata.path_confidence,
                "vision_confidence": metadata.vision_confidence,
                "overall_confidence": metadata.overall_confidence,

                # Source tracking
                "source_file": metadata.source_file,
                "extraction_method": metadata.extraction_method,
            })

            prepared_chunks.append(chunk_data)

        return prepared_chunks


def main():
    """Main entry point for testing"""
    if len(sys.argv) < 2:
        print("Usage: python multi_format_pipeline.py <file_path_or_url> [max_pages]")
        print("\nExamples:")
        print("  python multi_format_pipeline.py document.pdf")
        print("  python multi_format_pipeline.py document.pdf 5")
        print("  python multi_format_pipeline.py document.docx")
        print("  python multi_format_pipeline.py https://example.com/article")
        sys.exit(1)

    file_path = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None

    # Initialize pipeline
    pipeline = MultiFormatPipeline()

    # Process file
    result = pipeline.process_file(file_path, max_pages=max_pages)

    # Print results
    print(f"\n{'='*80}")
    print("PIPELINE RESULT")
    print(f"{'='*80}")

    if result.success:
        print("SUCCESS")
        print(f"\nFile: {result.file_path}")
        print(f"Method: {result.extraction_method}")
        print(f"Chunks Created: {result.chunks_created}")
        print(f"Chunks Ingested: {result.chunks_ingested}")

        if result.metadata_summary:
            print(f"\nMetadata Summary:")
            for key, value in result.metadata_summary.items():
                print(f"  {key}: {value}")
    else:
        print("FAILED")
        print(f"Error: {result.error}")

    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
