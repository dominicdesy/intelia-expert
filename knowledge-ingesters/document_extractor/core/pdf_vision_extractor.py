"""
PDF Vision Extractor
Extracts text content from PDFs using Claude Vision API
Focus: Narrative text, explanations, recommendations (NOT performance tables)
Performance tables are handled by performance_extractor
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import anthropic
import os
import io
from PIL import Image


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


class PDFVisionExtractor:
    """
    Extract text content from PDFs using Claude Vision API.

    Strategy:
    1. Convert PDF pages to images (300 DPI)
    2. Send to Claude Vision API for text extraction
    3. Combine all pages into full document text
    4. Return markdown-formatted content

    Note: This extractor focuses on narrative content.
    Performance tables are handled separately by performance_extractor.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize PDF Vision Extractor.

        Args:
            api_key: Anthropic API key (default: from ANTHROPIC_API_KEY or CLAUDE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY or CLAUDE_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.dpi = 300  # High quality for text extraction

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
            # Open PDF
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            # Limit pages if specified
            pages_to_process = min(total_pages, max_pages) if max_pages else total_pages

            print(f"Processing {pages_to_process}/{total_pages} pages from {pdf_path.name}")

            # Extract metadata
            metadata = self._extract_metadata(doc)

            # Process each page
            pages = []
            for page_num in range(pages_to_process):
                print(f"  Processing page {page_num + 1}/{pages_to_process}...")

                page_result = self._process_page(doc, page_num)
                pages.append(page_result)

            doc.close()

            # Combine all page text
            full_text = "\n\n".join([
                f"# Page {p.page_number}\n\n{p.text_content}"
                for p in pages if p.text_content
            ])

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
                error=str(e)
            )

    def _process_page(self, doc: fitz.Document, page_num: int) -> PDFPage:
        """
        Process a single PDF page.

        Args:
            doc: PyMuPDF document
            page_num: Page number (0-indexed)

        Returns:
            PDFPage with extracted content
        """
        page = doc[page_num]

        # Convert page to image
        pix = page.get_pixmap(dpi=self.dpi)
        img_bytes = pix.tobytes("png")

        # Send to Claude Vision API
        text_content = self._extract_text_from_image(img_bytes, page_num + 1)

        # Calculate word count
        word_count = len(text_content.split()) if text_content else 0

        return PDFPage(
            page_number=page_num + 1,
            text_content=text_content,
            word_count=word_count,
            has_images=len(page.get_images()) > 0,
            has_tables=self._has_tables(page)
        )

    def _extract_text_from_image(self, img_bytes: bytes, page_num: int) -> str:
        """
        Extract text from page image using Claude Vision API.

        Args:
            img_bytes: PNG image bytes
            page_num: Page number for context

        Returns:
            Extracted text in markdown format
        """
        try:
            # Encode image to base64
            import base64
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

            # Call Claude Vision API
            message = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": """Extract all text content from this PDF page.

Focus on:
- Main narrative text, paragraphs, explanations
- Section headings and subheadings
- Bullet points and lists
- Important notes and recommendations
- Image captions

For tables: Only extract small reference tables.
For large performance/data tables, just note: [PERFORMANCE TABLE - See performance_extractor]

Return the content in clean markdown format.
Preserve document structure (headings, lists, etc.).
Do NOT add any commentary or explanations."""
                            }
                        ]
                    }
                ]
            )

            # Extract text from response
            if message.content and len(message.content) > 0:
                return message.content[0].text
            else:
                return ""

        except Exception as e:
            print(f"    Error extracting text from page {page_num}: {e}")
            return ""

    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """Extract PDF metadata"""
        metadata = doc.metadata or {}
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
        }

    def _has_tables(self, page: fitz.Page) -> bool:
        """
        Detect if page contains tables (simple heuristic).

        This is just for metadata - we don't extract the tables.
        Performance tables are handled by performance_extractor.
        """
        # Simple heuristic: look for grid-like patterns
        text = page.get_text()

        # Count tab characters and aligned spaces
        tab_count = text.count('\t')

        # If many tabs, likely has tables
        return tab_count > 10


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_vision_extractor.py <pdf_file>")
        sys.exit(1)

    pdf_file = sys.argv[1]

    # Initialize extractor
    extractor = PDFVisionExtractor()

    # Extract PDF (limit to first 3 pages for testing)
    result = extractor.extract_pdf(pdf_file, max_pages=3)

    if result.success:
        print("\n" + "="*80)
        print("EXTRACTION SUCCESSFUL")
        print("="*80)
        print(f"File: {result.file_path}")
        print(f"Total pages: {result.total_pages}")
        print(f"Pages processed: {len(result.pages)}")
        print(f"Total words extracted: {sum(p.word_count for p in result.pages)}")
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
            print("-" * 80)
            print(first_page.text_content[:500])
            if len(first_page.text_content) > 500:
                print("...")
            print()
    else:
        print(f"ERROR: {result.error}")
