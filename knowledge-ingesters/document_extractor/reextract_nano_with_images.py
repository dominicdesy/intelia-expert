"""
Re-extract Nano Manual with Images
1. Clean existing Nano data from Weaviate
2. Extract text + images from PDF
3. Upload images to Spaces
4. Ingest everything to Weaviate
"""

import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cleanup_nano import cleanup_nano_manual
from multimodal_extractor import MultimodalExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def reextract_nano_manual():
    """Complete workflow: cleanup + re-extract with images."""

    print("\n" + "="*80)
    print("NANO MANUAL RE-EXTRACTION WITH IMAGES")
    print("="*80)
    print("This script will:")
    print("  1. DELETE existing Nano manual data from Weaviate")
    print("  2. EXTRACT text and images from Nano manual PDF")
    print("  3. UPLOAD images to Digital Ocean Spaces (documents/ folder)")
    print("  4. INGEST text and image metadata to Weaviate")
    print("="*80)

    # Confirm
    response = input("\nContinue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return

    # Step 1: Cleanup existing data
    logger.info("\n" + "="*80)
    logger.info("STEP 1/2: CLEANING EXISTING DATA")
    logger.info("="*80)

    success = cleanup_nano_manual()
    if not success:
        logger.error("Cleanup failed. Aborting.")
        return

    # Step 2: Re-extract with images
    logger.info("\n" + "="*80)
    logger.info("STEP 2/2: EXTRACTING WITH IMAGES")
    logger.info("="*80)

    # Find Nano manual PDF
    nano_pdf = Path("Sources/intelia/intelia_products/nano/nano-manual.pdf")

    if not nano_pdf.exists():
        logger.error(f"Nano manual PDF not found: {nano_pdf}")
        logger.info("Please specify the correct path to the Nano manual PDF")
        return

    # Initialize multimodal extractor
    extractor = MultimodalExtractor(
        spaces_bucket="intelia-knowledge",
        enable_image_extraction=True
    )

    # Process Nano manual
    result = extractor.process_document(
        str(nano_pdf),
        classification_path="intelia/intelia_products/nano/documentation/common",
        extract_images=True
    )

    # Print results
    logger.info("\n" + "="*80)
    logger.info("RE-EXTRACTION COMPLETE")
    logger.info("="*80)
    logger.info(f"Success: {result['success']}")
    logger.info(f"Text chunks: {result['text_chunks']}")
    logger.info(f"Images extracted: {result['images']}")
    logger.info(f"Errors: {len(result['errors'])}")

    if result['errors']:
        logger.warning("\nErrors encountered:")
        for error in result['errors']:
            logger.warning(f"  - {error}")

    # Print statistics
    extractor.print_statistics()

    # Final instructions
    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS")
    logger.info("="*80)
    logger.info("1. Verify images in Digital Ocean Spaces:")
    logger.info("   https://cloud.digitalocean.com/spaces")
    logger.info("   → Navigate to: intelia-knowledge/documents/")
    logger.info("")
    logger.info("2. Test image search:")
    logger.info("   python -c \"from services.image_ingester import ImageIngester; i = ImageIngester(); print(i.search_images('diagram', limit=5))\"")
    logger.info("")
    logger.info("3. Test text + images retrieval in your application")
    logger.info("="*80)


if __name__ == "__main__":
    reextract_nano_manual()
