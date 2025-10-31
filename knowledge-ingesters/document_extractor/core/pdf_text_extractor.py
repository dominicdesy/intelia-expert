# -*- coding: utf-8 -*-
"""
PDF Text Extractor (FREE alternative to Claude Vision)
Extracts text content from PDFs using pdfplumber
Zero API costs - Ideal for text-heavy documents without complex layouts

Winner from A/B/C test:
- Speed: 0.738s for 6 pages
- Quality: 20,693 chars extracted (best)
- Tables: YES (supports table detection and extraction)
- Cost: FREE (vs 0.21$/page with Claude Vision)

Cost savings: ~490$ for 54 PDFs (2,335 pages)
"""

import pdfplumber
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class PDFPage:
    """Represents a single PDF page"""
    page_number: int
    text_content: str
    has_images: bool = False
    has_tables: bool = False
    word_count: int = 0


@dataclass
class PDFExtractionResult:
    """Result of PDF extraction"""
    file_path: str
    total_pages: int
    pages: List[PDFPage]
    full_text: str
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None


class PDFTextExtractor:
    """
    Extract text content from PDFs using pdfplumber (FREE).

    Strategy:
    1. Open PDF with pdfplumber
    2. Extract text from each page
    3. Detect tables (but don't extract - leave for table_extractor)
    4. Combine all pages into markdown-formatted content
    5. Return full document text

    Advantages:
    - FREE (no API costs)
    - Fast (0.738s for 6 pages)
    - Good quality (20,693 chars extracted in test)
    - Supports table detection
    - Works offline

    Limitations:
    - Won't extract images/diagrams (use Claude Vision for those)
    - May struggle with complex layouts (use Claude Vision as fallback)
    - OCR not supported (use Claude Vision for scanned PDFs)
    """

    def __init__(self):
        """Initialize PDF Text Extractor"""
        # No API keys needed - completely free!
        pass

    def extract_pdf(self, pdf_path: str | Path, max_pages: Optional[int] = None) -> PDFExtractionResult:
        """
        Extract text content from PDF.

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to process (None = all pages)

        Returns:
            PDFExtractionResult with extracted content
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            return PDFExtractionResult(
                file_path=str(pdf_path),
                total_pages=0,
                pages=[],
                full_text="",
                metadata={},
                success=False,
                error=f"File not found: {pdf_path}"
            )

        try:
            # Open PDF with pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)

                # Limit pages if specified
                pages_to_process = min(total_pages, max_pages) if max_pages else total_pages

                print(f"Processing {pages_to_process}/{total_pages} pages from {pdf_path.name}")
                print(f"  Using FREE pdfplumber (no API costs!)")

                # Extract metadata
                metadata = self._extract_metadata(pdf)

                # Process each page
                pages = []
                for page_num in range(pages_to_process):
                    page = pdf.pages[page_num]

                    if (page_num + 1) % 10 == 0 or page_num == 0:
                        print(f"  Processing page {page_num + 1}/{pages_to_process}...")

                    page_result = self._process_page(page, page_num + 1)
                    pages.append(page_result)

                # Combine all page text
                full_text = "\n\n".join([
                    f"# Page {p.page_number}\n\n{p.text_content}"
                    for p in pages if p.text_content
                ])

                total_words = sum(p.word_count for p in pages)
                print(f"OK Extraction complete: {total_words:,} words from {len(pages)} pages")

                return PDFExtractionResult(
                    file_path=str(pdf_path),
                    total_pages=total_pages,
                    pages=pages,
                    full_text=full_text,
                    metadata=metadata,
                    success=True
                )

        except Exception as e:
            return PDFExtractionResult(
                file_path=str(pdf_path),
                total_pages=0,
                pages=[],
                full_text="",
                metadata={},
                success=False,
                error=f"pdfplumber extraction failed: {str(e)}"
            )

    def _process_page(self, page, page_num: int) -> PDFPage:
        """
        Process a single PDF page.

        Args:
            page: pdfplumber page object
            page_num: Page number (1-indexed)

        Returns:
            PDFPage with extracted content
        """
        # Extract text
        text_content = page.extract_text() or ""

        # Calculate word count
        word_count = len(text_content.split()) if text_content else 0

        # Detect tables
        tables = page.extract_tables()
        has_tables = len(tables) > 0 if tables else False

        # Check for images (pdfplumber can detect images)
        has_images = len(page.images) > 0 if hasattr(page, 'images') else False

        return PDFPage(
            page_number=page_num,
            text_content=text_content,
            word_count=word_count,
            has_images=has_images,
            has_tables=has_tables
        )

    def _extract_metadata(self, pdf) -> Dict[str, Any]:
        """
        Extract PDF metadata.

        Args:
            pdf: pdfplumber PDF object

        Returns:
            Dict with metadata
        """
        metadata = pdf.metadata or {}

        # pdfplumber uses different keys than PyMuPDF
        return {
            "title": metadata.get("Title", ""),
            "author": metadata.get("Author", ""),
            "subject": metadata.get("Subject", ""),
            "creator": metadata.get("Creator", ""),
            "producer": metadata.get("Producer", ""),
            "creation_date": metadata.get("CreationDate", ""),
            "modification_date": metadata.get("ModDate", ""),
        }


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_text_extractor.py <pdf_file> [max_pages]")
        sys.exit(1)

    pdf_file = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None

    # Initialize extractor
    extractor = PDFTextExtractor()

    # Extract PDF
    result = extractor.extract_pdf(pdf_file, max_pages=max_pages)

    if result.success:
        print("\n" + "="*80)
        print("EXTRACTION SUCCESSFUL")
        print("="*80)
        print(f"File: {result.file_path}")
        print(f"Total pages: {result.total_pages}")
        print(f"Pages processed: {len(result.pages)}")
        print(f"Total words extracted: {sum(p.word_count for p in result.pages):,}")
        print(f"Cost: FREE (pdfplumber)")
        print()

        # Show metadata
        print("Metadata:")
        for key, value in result.metadata.items():
            if value:
                print(f"  {key}: {value}")
        print()

        # Show first page content (first 500 chars)
        if result.pages:
            first_page = result.pages[0]
            print(f"First page content (page {first_page.page_number}):")
            print(f"  Words: {first_page.word_count}")
            print(f"  Has tables: {first_page.has_tables}")
            print(f"  Has images: {first_page.has_images}")
            print("-" * 80)
            print(first_page.text_content[:500])
            if len(first_page.text_content) > 500:
                print("...")
            print()
    else:
        print(f"ERROR: {result.error}")
