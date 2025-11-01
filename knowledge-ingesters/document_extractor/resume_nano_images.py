"""
Resume Nano Image Upload
Version: 1.0.0

Intelligently resumes image upload from where it stopped:
1. Extracts all images from Nano Word document
2. Checks which images already exist in Digital Ocean Spaces
3. Uploads only missing images
4. Ingests missing metadata to Weaviate
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.docx_image_extractor import DocxImageExtractor
from services.spaces_uploader import SpacesUploader
from services.image_ingester import ImageIngester

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_image_exists_in_spaces(uploader: SpacesUploader, filename: str, folder: str = "documents") -> bool:
    """
    Check if an image already exists in Digital Ocean Spaces.

    Args:
        uploader: SpacesUploader instance
        filename: Image filename
        folder: Folder in Spaces

    Returns:
        True if image exists
    """
    try:
        s3_key = f"{folder}/{filename}"
        uploader.s3_client.head_object(Bucket=uploader.bucket, Key=s3_key)
        return True
    except:
        return False


def resume_nano_image_upload():
    """Resume image upload from where it stopped."""

    logger.info("="*80)
    logger.info("RESUMING NANO IMAGE UPLOAD")
    logger.info("="*80)

    # Path to Nano manual
    nano_docx = Path("C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/intelia_products/nano/30-008-00096-605 Installation and Operation Manual Nano EN.docx")

    if not nano_docx.exists():
        logger.error(f"Nano manual not found: {nano_docx}")
        return False

    logger.info(f"Processing: {nano_docx}")

    # Initialize extractors
    logger.info("\n[1/4] Initializing services...")
    docx_extractor = DocxImageExtractor()
    spaces_uploader = SpacesUploader(bucket=os.getenv("DO_SPACES_BUCKET", "intelia-knowledge"))
    image_ingester = ImageIngester()

    # Extract all images from Word document
    logger.info("\n[2/4] Extracting images from Word document...")
    images = docx_extractor.extract_images(str(nano_docx))

    logger.info(f"  Total images in document: {len(images)}")

    # Check which images already exist
    logger.info("\n[3/4] Checking which images already exist in Spaces...")

    existing_images = []
    missing_images = []

    for idx, image in enumerate(images, 1):
        filename = image["filename"]
        exists = check_image_exists_in_spaces(spaces_uploader, filename)

        if exists:
            existing_images.append(image)
            logger.debug(f"  [{idx}/{len(images)}] ✓ Already exists: {filename}")
        else:
            missing_images.append(image)
            logger.info(f"  [{idx}/{len(images)}] ✗ Missing: {filename}")

        # Log progress every 50 images
        if idx % 50 == 0:
            logger.info(f"  Progress: {idx}/{len(images)} checked...")

    logger.info(f"\n  Summary:")
    logger.info(f"    Already uploaded: {len(existing_images)}")
    logger.info(f"    Missing (need upload): {len(missing_images)}")

    # Upload missing images
    if missing_images:
        logger.info(f"\n[4/4] Uploading {len(missing_images)} missing images...")

        uploaded_count = 0
        failed_count = 0

        for idx, image in enumerate(missing_images, 1):
            try:
                # Upload to Digital Ocean Spaces
                image_url = spaces_uploader.upload_image(
                    image_data=image["image_data"],
                    filename=image["filename"],
                    content_type=f"image/{image['format']}"
                )

                logger.info(f"  [{idx}/{len(missing_images)}] ✓ Uploaded: {image['filename']}")
                logger.debug(f"      URL: {image_url}")

                # Create metadata for Weaviate
                image_metadata = {
                    "image_id": f"nano_manual_img{image['image_index']:03d}",
                    "image_url": image_url,
                    "caption": f"Image {image['image_index']} from Nano Installation and Operation Manual",
                    "page_number": 0,  # Word docs don't have page numbers
                    "source_file": str(nano_docx),
                    "image_type": "diagram",  # Default type
                    "width": image["width"],
                    "height": image["height"],
                    "file_size_kb": image["size_bytes"] / 1024,
                    "format": image["format"],
                    "linked_chunk_ids": [],  # No page correlation for Word docs
                    "owner_org_id": "intelia",
                    "visibility_level": "intelia_products",
                    "site_type": "nano",
                    "category": "documentation",
                    "extracted_at": "2025-10-31T00:00:00Z"
                }

                # Ingest to Weaviate
                success = image_ingester.ingest_image(image_metadata)

                if success:
                    uploaded_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"  ✗ Failed to ingest metadata for {image['filename']}")

            except Exception as e:
                logger.error(f"  ✗ Error uploading {image['filename']}: {e}")
                failed_count += 1

        logger.info(f"\n  Upload complete:")
        logger.info(f"    Successful: {uploaded_count}")
        logger.info(f"    Failed: {failed_count}")
    else:
        logger.info("\n[4/4] All images already uploaded - nothing to do!")

    # Final summary
    logger.info("\n" + "="*80)
    logger.info("RESUME COMPLETE")
    logger.info("="*80)
    logger.info(f"Total images in document: {len(images)}")
    logger.info(f"Already uploaded: {len(existing_images)}")
    logger.info(f"Newly uploaded: {len(missing_images)}")
    logger.info("="*80)

    # Close connections
    image_ingester.close()

    return True


if __name__ == "__main__":
    try:
        success = resume_nano_image_upload()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
