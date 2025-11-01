"""
Multimodal Document Extractor
Version: 1.0.0
Last modified: 2025-10-31

Extracts both TEXT and IMAGES from PDF documents:
- Text → Weaviate (InteliaKnowledge collection)
- Images → Digital Ocean Spaces (Object Storage)
- Image Metadata → Weaviate (InteliaImages collection)

Usage:
    python multimodal_extractor.py path/to/document.pdf
    python multimodal_extractor.py --folder path/to/folder
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

# Third-party imports
import fitz  # PyMuPDF for image extraction
from PIL import Image
import io
import anthropic
import base64

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from multi_format_pipeline import MultiFormatPipeline
from weaviate_integration.ingester_v2 import WeaviateIngesterV2
from core.docx_image_extractor import DocxImageExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultimodalExtractor:
    """
    Extract text and images from PDF documents.

    Text → Weaviate (InteliaKnowledge)
    Images → Digital Ocean Spaces → Metadata in Weaviate (InteliaImages)
    """

    def __init__(
        self,
        spaces_bucket: str = "intelia-knowledge",
        enable_image_extraction: bool = True
    ):
        """
        Initialize multimodal extractor.

        Args:
            spaces_bucket: Digital Ocean Spaces bucket name
            enable_image_extraction: Whether to extract images (default: True)
        """
        self.spaces_bucket = spaces_bucket
        self.enable_image_extraction = enable_image_extraction

        # Initialize text extraction pipeline (existing)
        self.text_pipeline = MultiFormatPipeline()

        # Initialize text ingester (existing collection)
        self.text_ingester = WeaviateIngesterV2(collection_name="InteliaKnowledge")

        # Initialize DOCX image extractor
        self.docx_extractor = DocxImageExtractor()

        # Initialize image ingester (new collection)
        if enable_image_extraction:
            from services.spaces_uploader import SpacesUploader
            from services.image_ingester import ImageIngester

            self.spaces_uploader = SpacesUploader(bucket=spaces_bucket)
            self.image_ingester = ImageIngester()

        # Statistics
        self.stats = {
            "text_chunks": 0,
            "images_extracted": 0,
            "images_uploaded": 0,
            "images_ingested": 0,
            "errors": 0
        }

    def extract_images_from_docx(
        self,
        docx_path: str,
        output_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract all images from a Word (.docx) file.

        Args:
            docx_path: Path to .docx file
            output_dir: Optional directory to save images locally (for debugging)

        Returns:
            List of image metadata dictionaries
        """
        return self.docx_extractor.extract_images(docx_path, output_dir)

    def extract_images_from_pdf(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract all images from a PDF file.

        Args:
            pdf_path: Path to PDF file
            output_dir: Optional directory to save images locally (for debugging)

        Returns:
            List of image metadata dictionaries
        """
        logger.info(f"Extracting images from: {pdf_path}")

        images = []
        pdf_name = Path(pdf_path).stem

        try:
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(pdf_path)

            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]

                # Get all images on this page
                image_list = page.get_images(full=True)

                logger.info(f"  Page {page_num + 1}: Found {len(image_list)} images")

                for img_index, img in enumerate(image_list):
                    try:
                        # Extract image data
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)

                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Convert to PIL Image for processing
                        pil_image = Image.open(io.BytesIO(image_bytes))

                        # Filter out tiny images (likely icons or decorations)
                        width, height = pil_image.size
                        if width < 100 or height < 100:
                            logger.debug(f"    Skipping small image: {width}x{height}")
                            continue

                        # Generate unique filename
                        image_filename = f"{pdf_name}_page{page_num + 1:03d}_img{img_index + 1:02d}.{image_ext}"

                        # Save locally if output_dir specified (for debugging)
                        if output_dir:
                            output_path = Path(output_dir) / image_filename
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            pil_image.save(output_path)
                            logger.debug(f"    Saved locally: {output_path}")

                        # Store image metadata
                        images.append({
                            "filename": image_filename,
                            "page_number": page_num + 1,
                            "image_index": img_index + 1,
                            "width": width,
                            "height": height,
                            "format": image_ext,
                            "size_bytes": len(image_bytes),
                            "image_data": image_bytes,  # Raw bytes for upload
                            "pil_image": pil_image  # PIL Image for processing
                        })

                        logger.info(f"    Extracted: {image_filename} ({width}x{height})")

                    except Exception as e:
                        logger.error(f"    Error extracting image {img_index}: {e}")
                        self.stats["errors"] += 1

            pdf_document.close()
            logger.info(f"Total images extracted: {len(images)}")

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            self.stats["errors"] += 1

        self.stats["images_extracted"] += len(images)
        return images

    def extract_image_context(
        self,
        pdf_path: str,
        page_number: int,
        text_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Extract rich text context around an image for better captioning.

        IMPORTANT: Includes cross-page context to handle cases where image is
        at top of page and relevant text is on previous page.

        Args:
            pdf_path: Path to PDF file
            page_number: Page number where image is located
            text_chunks: All text chunks from the document

        Returns:
            Rich context text (current page + previous page if needed)
        """
        context_parts = []

        # Get chunks from PREVIOUS page (in case image is at top of current page)
        if page_number > 0:
            prev_page_chunks = [
                chunk for chunk in text_chunks
                if chunk.get("page_number") == page_number - 1
            ]

            if prev_page_chunks:
                # Take last 3 chunks from previous page (most relevant)
                prev_text = " ".join([
                    chunk.get("content", "")
                    for chunk in prev_page_chunks[-3:]
                ])
                if prev_text:
                    context_parts.append(f"[Previous page context]: {prev_text}")

        # Get chunks from CURRENT page
        current_page_chunks = [
            chunk for chunk in text_chunks
            if chunk.get("page_number") == page_number
        ]

        if current_page_chunks:
            current_text = " ".join([
                chunk.get("content", "")
                for chunk in current_page_chunks
            ])
            context_parts.append(current_text)

        # Get chunks from NEXT page (for completeness)
        next_page_chunks = [
            chunk for chunk in text_chunks
            if chunk.get("page_number") == page_number + 1
        ]

        if next_page_chunks:
            # Take first 2 chunks from next page
            next_text = " ".join([
                chunk.get("content", "")
                for chunk in next_page_chunks[:2]
            ])
            if next_text:
                context_parts.append(f"[Following context]: {next_text}")

        # Combine all context
        full_context = "\n\n".join(context_parts)

        # Truncate if too long (keep first 2000 chars for prompt)
        if len(full_context) > 2000:
            full_context = full_context[:2000] + "..."

        logger.debug(f"Extracted context for image on page {page_number}: {len(full_context)} chars")

        return full_context if full_context else "No context available"

    def process_document(
        self,
        file_path: str,
        classification_path: Optional[str] = None,
        extract_images: bool = True
    ) -> Dict[str, Any]:
        """
        Process a document: extract text and images.

        Args:
            file_path: Path to PDF document
            classification_path: Optional classification (e.g., intelia/public/broiler_farms/management/common)
            extract_images: Whether to extract images (default: True)

        Returns:
            Processing results dictionary
        """
        logger.info("="*80)
        logger.info(f"PROCESSING DOCUMENT: {file_path}")
        logger.info("="*80)

        results = {
            "success": False,
            "file_path": file_path,
            "text_chunks": 0,
            "images": 0,
            "errors": []
        }

        # Step 1: Extract TEXT (existing pipeline)
        logger.info("\n[1/3] Extracting TEXT...")
        try:
            text_result = self.text_pipeline.process_file(file_path)

            if not text_result.success:
                logger.error(f"Text extraction failed: {text_result.error}")
                results["errors"].append(f"Text extraction: {text_result.error}")
                return results

            # Override classification if provided
            if classification_path:
                parts = classification_path.strip("/").split("/")
                for chunk in text_result.chunks_with_metadata:
                    if len(parts) >= 2:
                        chunk["owner_org_id"] = parts[0]
                        chunk["visibility_level"] = parts[1]
                    if len(parts) >= 3:
                        chunk["site_type"] = parts[2]
                    if len(parts) >= 4:
                        chunk["category"] = parts[3]
                    if len(parts) >= 5:
                        chunk["subcategory"] = parts[4]

            # Ingest text to Weaviate
            text_ingestion_stats = self.text_ingester.ingest_chunks(text_result.chunks_with_metadata)

            results["text_chunks"] = len(text_result.chunks_with_metadata)
            self.stats["text_chunks"] += results["text_chunks"]

            logger.info(f"✓ Text extraction complete: {results['text_chunks']} chunks")
            logger.info(f"  Ingested to Weaviate: {text_ingestion_stats['success']} successful")

        except Exception as e:
            logger.error(f"Error during text extraction: {e}")
            results["errors"].append(f"Text extraction: {str(e)}")
            return results

        # Step 2: Extract IMAGES (if enabled)
        if extract_images and self.enable_image_extraction:
            logger.info("\n[2/3] Extracting IMAGES...")
            try:
                # Detect file type and use appropriate extractor
                file_ext = Path(file_path).suffix.lower()

                if file_ext == '.pdf':
                    images = self.extract_images_from_pdf(file_path)
                elif file_ext in ['.docx', '.doc']:
                    images = self.extract_images_from_docx(file_path)
                else:
                    logger.warning(f"Unsupported file type for image extraction: {file_ext}")
                    images = []

                if images:
                    logger.info(f"✓ Image extraction complete: {len(images)} images")

                    # Step 3: Upload images and create metadata
                    logger.info("\n[3/3] Uploading IMAGES to Spaces...")

                    for image in images:
                        try:
                            # Upload to Digital Ocean Spaces
                            image_url = self.spaces_uploader.upload_image(
                                image_data=image["image_data"],
                                filename=image["filename"],
                                content_type=f"image/{image['format']}"
                            )

                            logger.info(f"  ✓ Uploaded: {image['filename']}")
                            logger.info(f"    URL: {image_url}")
                            self.stats["images_uploaded"] += 1

                            # Extract context from surrounding text
                            context = self.extract_image_context(
                                file_path,
                                image["page_number"],
                                text_result.chunks_with_metadata
                            )

                            # Generate caption with Claude Vision (optional)
                            caption = self._generate_caption(image["pil_image"], context)

                            # Create image metadata for Weaviate
                            image_metadata = {
                                "image_id": f"{Path(file_path).stem}_page{image['page_number']}_img{image['image_index']}",
                                "image_url": image_url,
                                "caption": caption,
                                "page_number": image["page_number"],
                                "source_file": str(file_path),
                                "image_type": self._classify_image_type(caption),
                                "width": image["width"],
                                "height": image["height"],
                                "file_size_kb": image["size_bytes"] / 1024,
                                "format": image["format"],
                                "extracted_at": datetime.now().isoformat(),
                                # Link to text chunks from same page
                                "linked_chunk_ids": [
                                    chunk.get("chunk_id")
                                    for chunk in text_result.chunks_with_metadata
                                    if chunk.get("page_number") == image["page_number"]
                                ]
                            }

                            # Add classification metadata
                            if classification_path:
                                parts = classification_path.strip("/").split("/")
                                if len(parts) >= 2:
                                    image_metadata["owner_org_id"] = parts[0]
                                    image_metadata["visibility_level"] = parts[1]
                                if len(parts) >= 3:
                                    image_metadata["site_type"] = parts[2]
                                if len(parts) >= 4:
                                    image_metadata["category"] = parts[3]

                            # Ingest image metadata to Weaviate
                            self.image_ingester.ingest_image(image_metadata)
                            self.stats["images_ingested"] += 1

                            logger.info(f"  ✓ Ingested metadata to Weaviate")

                        except Exception as e:
                            logger.error(f"  ✗ Error processing {image['filename']}: {e}")
                            results["errors"].append(f"Image {image['filename']}: {str(e)}")
                            self.stats["errors"] += 1

                    results["images"] = len(images)
                else:
                    logger.info("  No images found in document")

            except Exception as e:
                logger.error(f"Error during image extraction: {e}")
                results["errors"].append(f"Image extraction: {str(e)}")
        else:
            logger.info("\n[2/3] Image extraction DISABLED")

        # Final results
        results["success"] = results["text_chunks"] > 0

        logger.info("\n" + "="*80)
        logger.info("PROCESSING COMPLETE")
        logger.info("="*80)
        logger.info(f"Text chunks: {results['text_chunks']}")
        logger.info(f"Images: {results['images']}")
        logger.info(f"Errors: {len(results['errors'])}")

        return results

    def _generate_caption(self, image: Image.Image, context: str) -> str:
        """
        Generate caption for an image using Claude Vision API with rich context.

        Args:
            image: PIL Image
            context: Surrounding text context (may include previous page text)

        Returns:
            Image caption/description
        """
        try:
            # Check if Claude API key is available
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not found - using context-based caption")
                return self._generate_fallback_caption(context)

            # Initialize Claude client
            client = anthropic.Anthropic(api_key=api_key)

            # Convert image to base64
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            image_data = base64.standard_b64encode(img_buffer.read()).decode("utf-8")

            # Detect document type and section from context
            doc_type = self._detect_document_type(context)
            section_hint = self._extract_section_hint(context)

            # Build enriched prompt
            prompt = self._build_vision_prompt(context, doc_type, section_hint)

            # Call Claude Vision API
            logger.info(f"Calling Claude Vision API for image caption...")
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=150,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )

            # Extract caption from response
            caption = message.content[0].text.strip()

            # Validate and clean caption
            caption = self._validate_caption(caption)

            logger.info(f"Generated caption: {caption[:80]}...")
            return caption

        except Exception as e:
            logger.error(f"Error in Claude Vision captioning: {e}", exc_info=True)
            return self._generate_fallback_caption(context)

    def _build_vision_prompt(self, context: str, doc_type: str, section_hint: str) -> str:
        """
        Build enriched prompt for Claude Vision based on context.

        Args:
            context: Text context around image
            doc_type: Type of document (manual, guide, etc.)
            section_hint: Detected section/topic

        Returns:
            Formatted prompt for Claude Vision
        """
        # Truncate context if too long (keep most relevant parts)
        context_preview = self._extract_key_context(context, max_chars=800)

        prompt = f"""You are analyzing an image from a poultry farm controller technical manual.

DOCUMENT CONTEXT:
{context_preview}

TASK:
Generate a concise, descriptive caption (15-25 words) that:

1. **Describes what's visible**: UI elements, buttons, graphs, data displays, diagrams
2. **Explains the purpose**: What this screen/feature does (based on surrounding text)
3. **Uses keywords**: Include specific terms from the context for semantic search

REQUIREMENTS:
- Be specific (e.g., "Export history page" not just "Settings screen")
- Mention key UI elements (buttons, icons, data fields)
- Include the functional purpose (monitoring, exporting, configuring, etc.)
- Use terminology from the context

EXAMPLES OF GOOD CAPTIONS:
- "Export history interface with USB drive icon and data type selection checkboxes for mortality, feed consumption, and environmental records"
- "Humidity monitoring graph displaying daily readings with minimum/maximum threshold lines and alarm indicators"
- "Main navigation menu showing icons for environment control, feed management, mortality tracking, and system settings"
- "Alarm configuration page with threshold inputs for temperature, humidity, and feed levels with notification options"

CAPTION:"""

        return prompt

    def _extract_key_context(self, context: str, max_chars: int = 800) -> str:
        """
        Extract most relevant parts of context for prompt.

        Args:
            context: Full context text
            max_chars: Maximum characters to include

        Returns:
            Truncated context with key information
        """
        if len(context) <= max_chars:
            return context

        # Split into sentences
        sentences = context.replace('\n', ' ').split('. ')

        # Priority keywords for poultry farm controllers
        priority_keywords = [
            'export', 'history', 'monitoring', 'alarm', 'temperature', 'humidity',
            'feed', 'mortality', 'USB', 'graph', 'chart', 'screen', 'page',
            'menu', 'button', 'icon', 'data', 'settings', 'configuration'
        ]

        # Score sentences by keyword relevance
        scored_sentences = []
        for sent in sentences:
            score = sum(1 for keyword in priority_keywords if keyword.lower() in sent.lower())
            scored_sentences.append((score, sent))

        # Sort by relevance and take top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        selected = [sent for score, sent in scored_sentences[:5]]  # Top 5 most relevant

        result = '. '.join(selected)

        # Truncate if still too long
        if len(result) > max_chars:
            result = result[:max_chars] + "..."

        return result

    def _detect_document_type(self, context: str) -> str:
        """Detect document type from context."""
        context_lower = context.lower()

        if 'manual' in context_lower or 'installation' in context_lower:
            return 'technical_manual'
        elif 'guide' in context_lower:
            return 'user_guide'
        else:
            return 'technical_document'

    def _extract_section_hint(self, context: str) -> str:
        """
        Extract section/topic hint from context.

        Args:
            context: Text context

        Returns:
            Section hint (e.g., "Export History", "Monitoring", "Alarms")
        """
        # Look for section headers (usually in all caps or title case)
        lines = context.split('\n')
        for line in lines[:5]:  # Check first few lines
            line = line.strip()
            # Section headers are often short and in title case
            if len(line) < 50 and len(line.split()) <= 5:
                if line.isupper() or line.istitle():
                    return line

        # Fallback: extract topic from context
        topics = {
            'export': 'Data Export',
            'history': 'History View',
            'alarm': 'Alarm Configuration',
            'temperature': 'Temperature Control',
            'humidity': 'Humidity Monitoring',
            'feed': 'Feed Management',
            'mortality': 'Mortality Tracking',
            'settings': 'System Settings',
            'menu': 'Navigation'
        }

        context_lower = context.lower()
        for keyword, topic in topics.items():
            if keyword in context_lower:
                return topic

        return 'Unknown Section'

    def _validate_caption(self, caption: str) -> str:
        """
        Validate and clean generated caption.

        Args:
            caption: Generated caption

        Returns:
            Cleaned caption
        """
        # Remove common prefix/suffix artifacts
        caption = caption.strip('"\'').strip()

        # Remove "Caption:" prefix if present
        if caption.lower().startswith('caption:'):
            caption = caption[8:].strip()

        # Ensure reasonable length (truncate if too long)
        if len(caption) > 150:
            caption = caption[:147] + "..."

        # Ensure minimum quality
        if len(caption) < 10:
            return "Interface screenshot from controller manual"

        return caption

    def _generate_fallback_caption(self, context: str) -> str:
        """
        Generate fallback caption when Claude Vision is not available.

        Args:
            context: Text context

        Returns:
            Context-based caption
        """
        # Extract key phrases from context
        context_lower = context.lower()

        # Detect topic
        if 'export' in context_lower:
            topic = 'Export history interface'
        elif 'alarm' in context_lower:
            topic = 'Alarm configuration screen'
        elif 'temperature' in context_lower or 'humidity' in context_lower:
            topic = 'Environmental monitoring display'
        elif 'feed' in context_lower:
            topic = 'Feed management screen'
        elif 'mortality' in context_lower:
            topic = 'Mortality tracking interface'
        elif 'menu' in context_lower or 'navigation' in context_lower:
            topic = 'Navigation menu screen'
        else:
            topic = 'Controller interface screen'

        # Add context hint
        context_preview = context[:100].strip()
        return f"{topic} - {context_preview}..."

    def _classify_image_type(self, caption: str) -> str:
        """
        Classify image type based on caption.

        Args:
            caption: Image caption

        Returns:
            Image type (diagram, chart, photo, table, infographic)
        """
        caption_lower = caption.lower()

        if any(word in caption_lower for word in ["diagram", "schematic", "flowchart"]):
            return "diagram"
        elif any(word in caption_lower for word in ["chart", "graph", "plot"]):
            return "chart"
        elif any(word in caption_lower for word in ["table", "data"]):
            return "table"
        elif any(word in caption_lower for word in ["photo", "image", "picture"]):
            return "photo"
        elif any(word in caption_lower for word in ["infographic", "illustration"]):
            return "infographic"
        else:
            return "unknown"

    def print_statistics(self):
        """Print extraction statistics."""
        logger.info("\n" + "="*80)
        logger.info("EXTRACTION STATISTICS")
        logger.info("="*80)
        logger.info(f"Text chunks created: {self.stats['text_chunks']}")
        logger.info(f"Images extracted: {self.stats['images_extracted']}")
        logger.info(f"Images uploaded to Spaces: {self.stats['images_uploaded']}")
        logger.info(f"Image metadata ingested to Weaviate: {self.stats['images_ingested']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("="*80)


def main():
    """CLI interface."""
    parser = argparse.ArgumentParser(description="Multimodal Document Extractor (Text + Images)")
    parser.add_argument("path", help="Path to PDF file or folder")
    parser.add_argument("--classification", help="Classification path (e.g., intelia/public/broiler_farms/management/common)")
    parser.add_argument("--no-images", action="store_true", help="Disable image extraction")
    parser.add_argument("--spaces-bucket", default="intelia-knowledge", help="Digital Ocean Spaces bucket")

    args = parser.parse_args()

    # Initialize extractor
    extractor = MultimodalExtractor(
        spaces_bucket=args.spaces_bucket,
        enable_image_extraction=not args.no_images
    )

    path = Path(args.path)

    if path.is_file():
        # Process single file
        extractor.process_document(
            str(path),
            classification_path=args.classification,
            extract_images=not args.no_images
        )
    elif path.is_dir():
        # Process all PDFs in folder
        pdf_files = list(path.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {path}")

        for pdf_file in pdf_files:
            extractor.process_document(
                str(pdf_file),
                classification_path=args.classification,
                extract_images=not args.no_images
            )
    else:
        logger.error(f"Path not found: {path}")
        sys.exit(1)

    # Print final statistics
    extractor.print_statistics()


if __name__ == "__main__":
    main()
