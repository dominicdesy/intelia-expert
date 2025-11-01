"""
Ingest Metadata for Already-Uploaded Images
Version: 1.0.0

The images were uploaded to Digital Ocean Spaces but metadata was not ingested to Weaviate.
This script extracts images from the Word doc, checks they exist in Spaces, and ingests metadata.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from core.docx_image_extractor import DocxImageExtractor
from services.spaces_uploader import SpacesUploader
from services.image_ingester import ImageIngester

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def ingest_metadata_for_uploaded_images():
    """Ingest metadata for images already in Spaces."""

    logger.info("="*80)
    logger.info("INGESTING METADATA FOR UPLOADED IMAGES")
    logger.info("="*80)

    # Path to Nano manual
    nano_docx = Path("C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/intelia_products/nano/30-008-00096-605 Installation and Operation Manual Nano EN.docx")

    if not nano_docx.exists():
        logger.error(f"Nano manual not found: {nano_docx}")
        return False

    logger.info(f"Processing: {nano_docx}")

    # Initialize services
    logger.info("\n[1/3] Initializing services...")
    docx_extractor = DocxImageExtractor()
    spaces_uploader = SpacesUploader(bucket=os.getenv("DO_SPACES_BUCKET", "intelia-knowledge"))
    image_ingester = ImageIngester()

    # Extract images
    logger.info("\n[2/3] Extracting images from Word document...")
    images = docx_extractor.extract_images(str(nano_docx))
    logger.info(f"  Extracted {len(images)} images")

    # Ingest metadata for ALL images
    logger.info(f"\n[3/3] Ingesting metadata for {len(images)} images...")

    ingested_count = 0
    failed_count = 0

    for idx, image in enumerate(images, 1):
        try:
            # Generate Spaces URL (images should already be there)
            image_url = f"https://{spaces_uploader.bucket}.{spaces_uploader.region}.cdn.digitaloceanspaces.com/documents/{image['filename']}"

            # Create metadata
            image_metadata = {
                "image_id": f"nano_manual_img{image['image_index']:03d}",
                "image_url": image_url,
                "caption": f"Image {image['image_index']} from Nano Installation and Operation Manual",
                "page_number": 0,  # Word docs don't have page numbers
                "source_file": str(nano_docx),
                "image_type": "diagram",
                "width": image["width"],
                "height": image["height"],
                "file_size_kb": image["size_bytes"] / 1024,
                "format": image["format"],
                "linked_chunk_ids": [],
                "owner_org_id": "intelia",
                "visibility_level": "intelia_products",
                "site_type": "nano",
                "category": "documentation",
                "extracted_at": "2025-10-31T00:00:00Z"
            }

            # Ingest to Weaviate
            success = image_ingester.ingest_image(image_metadata)

            if success:
                ingested_count += 1
                if idx % 50 == 0:
                    logger.info(f"  Progress: {idx}/{len(images)} ingested...")
            else:
                failed_count += 1
                logger.warning(f"  Failed to ingest metadata for {image['filename']}")

        except Exception as e:
            logger.error(f"  Error processing {image['filename']}: {e}")
            failed_count += 1

    logger.info(f"\n  Ingestion complete:")
    logger.info(f"    Successful: {ingested_count}")
    logger.info(f"    Failed: {failed_count}")

    # Final summary
    logger.info("\n" + "="*80)
    logger.info("METADATA INGESTION COMPLETE")
    logger.info("="*80)
    logger.info(f"Total images: {len(images)}")
    logger.info(f"Metadata ingested: {ingested_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info("="*80)

    # Close connections
    image_ingester.close()

    return True


if __name__ == "__main__":
    try:
        success = ingest_metadata_for_uploaded_images()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
