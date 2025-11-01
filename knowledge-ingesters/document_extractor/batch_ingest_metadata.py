"""
Batch Ingest Image Metadata - Optimized Version
Version: 1.0.0

Uses batch insertion for fast ingestion of 308 image metadata records.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from core.docx_image_extractor import DocxImageExtractor
from services.image_ingester import ImageIngester

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def batch_ingest_all_metadata():
    """Batch ingest metadata for all images."""

    logger.info("="*80)
    logger.info("BATCH INGESTING IMAGE METADATA")
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
    image_ingester = ImageIngester()

    # Extract images
    logger.info("\n[2/3] Extracting images from Word document...")
    images = docx_extractor.extract_images(str(nano_docx))
    logger.info(f"  Extracted {len(images)} images")

    # Prepare metadata for all images
    logger.info(f"\n[3/3] Preparing metadata for batch ingestion...")

    image_metadata_list = []

    for image in images:
        # Generate Spaces URL
        bucket = os.getenv("DO_SPACES_BUCKET", "intelia-knowledge")
        region = os.getenv("DO_SPACES_REGION", "tor1")
        image_url = f"https://{bucket}.{region}.cdn.digitaloceanspaces.com/documents/{image['filename']}"

        # Create metadata
        image_metadata = {
            "image_id": f"nano_manual_img{image['image_index']:03d}",
            "image_url": image_url,
            "caption": f"Image {image['image_index']} from Nano Installation and Operation Manual",
            "page_number": 0,
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

        image_metadata_list.append(image_metadata)

    # Batch ingest
    logger.info(f"\nBatch ingesting {len(image_metadata_list)} metadata records...")
    stats = image_ingester.ingest_images(image_metadata_list)

    # Results
    logger.info("\n" + "="*80)
    logger.info("BATCH INGESTION COMPLETE")
    logger.info("="*80)
    logger.info(f"Total images: {len(images)}")
    logger.info(f"Successfully ingested: {stats['success']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info("="*80)

    # Close connections
    image_ingester.close()

    return stats['success'] > 0


if __name__ == "__main__":
    try:
        success = batch_ingest_all_metadata()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
