"""
DOCX Extractor
Extracts text content from DOCX files using python-docx
Simple text extraction - no vision API needed for text documents
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


@dataclass
class DOCXExtractionResult:
    """Result of DOCX extraction"""
    file_path: str
    full_text: str
    metadata: Dict[str, Any]
    paragraph_count: int
    table_count: int
    word_count: int
    success: bool
    error: Optional[str] = None


class DOCXExtractor:
    """
    Extract text content from DOCX files.

    Strategy:
    1. Extract all paragraphs in order
    2. Extract text from tables (small reference tables only)
    3. Note large tables without extracting (handled by performance_extractor)
    4. Return markdown-formatted content
    """

    def __init__(self):
        """Initialize DOCX Extractor"""
        self.large_table_threshold = 50  # cells

    def extract_docx(self, docx_path: str | Path) -> DOCXExtractionResult:
        """
        Extract text content from DOCX file.

        Args:
            docx_path: Path to DOCX file

        Returns:
            DOCXExtractionResult with extracted content
        """
        docx_path = Path(docx_path)

        if not docx_path.exists():
            return DOCXExtractionResult(
                file_path=str(docx_path),
                full_text="",
                metadata={},
                paragraph_count=0,
                table_count=0,
                word_count=0,
                success=False,
                error=f"File not found: {docx_path}"
            )

        try:
            # Open document
            doc = Document(docx_path)

            print(f"Processing {docx_path.name}")

            # Extract metadata
            metadata = self._extract_metadata(doc)

            # Extract content
            content_parts = []
            paragraph_count = 0
            table_count = 0

            # Process document elements in order
            for element in doc.element.body:
                # Paragraph
                if element.tag.endswith('p'):
                    para = Paragraph(element, doc)
                    text = para.text.strip()
                    if text:
                        # Check if it's a heading
                        style = para.style.name if para.style else ""
                        if "Heading" in style:
                            level = self._get_heading_level(style)
                            content_parts.append(f"\n{'#' * level} {text}\n")
                        else:
                            content_parts.append(text)
                        paragraph_count += 1

                # Table
                elif element.tag.endswith('tbl'):
                    table = Table(element, doc)
                    table_text = self._extract_table(table)
                    content_parts.append(table_text)
                    table_count += 1

            # Combine all content
            full_text = "\n\n".join(content_parts)
            word_count = len(full_text.split())

            return DOCXExtractionResult(
                file_path=str(docx_path),
                full_text=full_text,
                metadata=metadata,
                paragraph_count=paragraph_count,
                table_count=table_count,
                word_count=word_count,
                success=True
            )

        except Exception as e:
            return DOCXExtractionResult(
                file_path=str(docx_path),
                full_text="",
                metadata={},
                paragraph_count=0,
                table_count=0,
                word_count=0,
                success=False,
                error=str(e)
            )

    def _extract_metadata(self, doc: Document) -> Dict[str, Any]:
        """Extract document metadata"""
        core_props = doc.core_properties

        return {
            "title": core_props.title or "",
            "author": core_props.author or "",
            "subject": core_props.subject or "",
            "keywords": core_props.keywords or "",
            "created": str(core_props.created) if core_props.created else "",
            "modified": str(core_props.modified) if core_props.modified else "",
            "last_modified_by": core_props.last_modified_by or "",
        }

    def _get_heading_level(self, style_name: str) -> int:
        """Extract heading level from style name"""
        # Style names like "Heading 1", "Heading 2", etc.
        if "Heading" in style_name:
            try:
                # Extract number from style name
                level_str = style_name.split()[-1]
                return int(level_str)
            except (ValueError, IndexError):
                return 1
        return 1

    def _extract_table(self, table: Table) -> str:
        """
        Extract text from table.

        For small tables: Extract as markdown
        For large tables: Just note presence
        """
        # Count cells
        total_cells = len(table.rows) * len(table.columns) if table.columns else 0

        if total_cells > self.large_table_threshold:
            # Large table - probably performance data
            return "\n[PERFORMANCE TABLE - See performance_extractor]\n"

        # Small table - extract as markdown
        table_lines = []

        for i, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells]

            # Add row
            table_lines.append("| " + " | ".join(cells) + " |")

            # Add header separator after first row
            if i == 0:
                table_lines.append("| " + " | ".join(["---"] * len(cells)) + " |")

        return "\n" + "\n".join(table_lines) + "\n"


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python docx_extractor.py <docx_file>")
        sys.exit(1)

    docx_file = sys.argv[1]

    # Initialize extractor
    extractor = DOCXExtractor()

    # Extract DOCX
    result = extractor.extract_docx(docx_file)

    if result.success:
        print("\n" + "="*80)
        print("EXTRACTION SUCCESSFUL")
        print("="*80)
        print(f"File: {result.file_path}")
        print(f"Paragraphs: {result.paragraph_count}")
        print(f"Tables: {result.table_count}")
        print(f"Total words: {result.word_count}")
        print()

        # Show metadata
        print("Metadata:")
        for key, value in result.metadata.items():
            if value:
                print(f"  {key}: {value}")
        print()

        # Show first 500 characters
        print("Content preview:")
        print("-" * 80)
        print(result.full_text[:500])
        if len(result.full_text) > 500:
            print("...")
        print()
    else:
        print(f"ERROR: {result.error}")
