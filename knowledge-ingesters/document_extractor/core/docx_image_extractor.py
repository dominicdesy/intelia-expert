"""
DOCX Image Extractor
Version: 1.0.0
Last modified: 2025-10-31

Extract images from Microsoft Word (.docx) files without quality loss.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import zipfile
from PIL import Image
import io

logger = logging.getLogger(__name__)


class DocxImageExtractor:
    """
    Extract images from Word (.docx) files.

    .docx files are ZIP archives containing:
    - word/document.xml (content)
    - word/media/ (embedded images)
    - word/_rels/document.xml.rels (relationships)
    """

    def extract_images(self, docx_path: str, output_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract all images from a .docx file.

        Args:
            docx_path: Path to .docx file
            output_dir: Optional directory to save images locally

        Returns:
            List of image metadata dictionaries
        """
        logger.info(f"Extracting images from Word document: {docx_path}")

        docx_path = Path(docx_path)
        if not docx_path.exists():
            logger.error(f"File not found: {docx_path}")
            return []

        images = []
        doc_name = docx_path.stem

        try:
            # Open .docx as ZIP archive
            with zipfile.ZipFile(docx_path, 'r') as docx_zip:
                # List all files in the archive
                file_list = docx_zip.namelist()

                # Find all images in word/media/ folder
                image_files = [
                    f for f in file_list
                    if f.startswith('word/media/') and self._is_image_file(f)
                ]

                logger.info(f"  Found {len(image_files)} images in document")

                for idx, image_path in enumerate(image_files, 1):
                    try:
                        # Extract image data
                        image_data = docx_zip.read(image_path)

                        # Get original filename
                        original_filename = Path(image_path).name

                        # Determine format from extension
                        file_ext = Path(image_path).suffix.lower().replace('.', '')

                        # Open with PIL to get dimensions
                        pil_image = Image.open(io.BytesIO(image_data))
                        width, height = pil_image.size

                        # Filter out tiny images (icons, bullets)
                        if width < 100 or height < 100:
                            logger.debug(f"    Skipping small image: {original_filename} ({width}x{height})")
                            continue

                        # Generate descriptive filename
                        new_filename = f"{doc_name}_img{idx:02d}.{file_ext}"

                        # Save locally if output_dir specified
                        if output_dir:
                            output_path = Path(output_dir) / new_filename
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(output_path, 'wb') as f:
                                f.write(image_data)
                            logger.debug(f"    Saved locally: {output_path}")

                        # Store image metadata
                        images.append({
                            "filename": new_filename,
                            "original_filename": original_filename,
                            "image_index": idx,
                            "width": width,
                            "height": height,
                            "format": file_ext,
                            "size_bytes": len(image_data),
                            "image_data": image_data,
                            "pil_image": pil_image,
                            "source_path": image_path  # Path within .docx archive
                        })

                        logger.info(f"    Extracted: {new_filename} ({width}x{height})")

                    except Exception as e:
                        logger.error(f"    Error extracting {image_path}: {e}")

            logger.info(f"Total images extracted: {len(images)}")
            return images

        except zipfile.BadZipFile:
            logger.error(f"Invalid .docx file (not a valid ZIP archive): {docx_path}")
            return []
        except Exception as e:
            logger.error(f"Error processing .docx file: {e}")
            return []

    def _is_image_file(self, filename: str) -> bool:
        """
        Check if a file is an image based on extension.

        Args:
            filename: Filename to check

        Returns:
            True if image file
        """
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.emf', '.wmf', '.svg'}
        ext = Path(filename).suffix.lower()
        return ext in image_extensions

    def get_image_count(self, docx_path: str) -> int:
        """
        Quickly count images in a .docx file without extracting them.

        Args:
            docx_path: Path to .docx file

        Returns:
            Number of images
        """
        try:
            with zipfile.ZipFile(docx_path, 'r') as docx_zip:
                file_list = docx_zip.namelist()
                image_files = [
                    f for f in file_list
                    if f.startswith('word/media/') and self._is_image_file(f)
                ]
                return len(image_files)
        except Exception as e:
            logger.error(f"Error counting images: {e}")
            return 0


# Example usage
if __name__ == "__main__":
    """Test DOCX image extractor."""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Test with Nano manual
    extractor = DocxImageExtractor()

    docx_file = "C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/intelia_products/nano/30-008-00096-605 Installation and Operation Manual Nano EN.docx"

    # Count images
    count = extractor.get_image_count(docx_file)
    print(f"\nDocument contains {count} images")

    # Extract images
    images = extractor.extract_images(docx_file, output_dir="temp_images")

    print(f"\nExtracted {len(images)} images:")
    for img in images:
        print(f"  - {img['filename']}: {img['width']}x{img['height']} ({img['size_bytes']/1024:.1f} KB)")
