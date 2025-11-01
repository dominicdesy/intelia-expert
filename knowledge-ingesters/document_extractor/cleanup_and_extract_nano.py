"""
Cleanup and Re-extract Nano Manual (No Interactive Prompts)
Automated version for non-interactive execution
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import Filter

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from multimodal_extractor import MultimodalExtractor

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_nano_data():
    """Delete all Nano manual data from Weaviate."""

    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")

    if not weaviate_url or not weaviate_api_key:
        logger.error("Weaviate credentials not found in .env")
        return False

    logger.info(f"Connecting to Weaviate: {weaviate_url}")
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(weaviate_api_key)
    )

    try:
        logger.info("\n" + "="*80)
        logger.info("STEP 1: CLEANING EXISTING NANO DATA")
        logger.info("="*80)

        collection = client.collections.get("InteliaKnowledge")

        nano_patterns = ["nano-manual", "nano_manual", "nano/", "/nano/"]
        total_deleted = 0

        for pattern in nano_patterns:
            try:
                response = collection.query.fetch_objects(
                    filters=Filter.by_property("source_file").contains_any([pattern]),
                    limit=1000
                )

                count = len(response.objects)

                if count > 0:
                    logger.info(f"  Found {count} chunks matching '{pattern}'")

                    for obj in response.objects:
                        try:
                            collection.data.delete_by_id(obj.uuid)
                            total_deleted += 1
                        except Exception as e:
                            logger.error(f"    Error deleting {obj.uuid}: {e}")

                    logger.info(f"  ✓ Deleted {count} chunks")

            except Exception as e:
                logger.warning(f"  Warning with pattern '{pattern}': {e}")

        logger.info(f"\n✓ Total text chunks deleted: {total_deleted}")

        # Clean images if collection exists
        if client.collections.exists("InteliaImages"):
            images_collection = client.collections.get("InteliaImages")
            total_images_deleted = 0

            for pattern in nano_patterns:
                try:
                    response = images_collection.query.fetch_objects(
                        filters=Filter.by_property("source_file").contains_any([pattern]),
                        limit=1000
                    )

                    count = len(response.objects)

                    if count > 0:
                        logger.info(f"  Found {count} images matching '{pattern}'")

                        for obj in response.objects:
                            try:
                                images_collection.data.delete_by_id(obj.uuid)
                                total_images_deleted += 1
                            except Exception as e:
                                logger.error(f"    Error deleting {obj.uuid}: {e}")

                except Exception as e:
                    logger.warning(f"  Warning with pattern '{pattern}': {e}")

            logger.info(f"✓ Total image metadata deleted: {total_images_deleted}")

        return True

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return False

    finally:
        client.close()


def extract_nano_with_images():
    """Extract Nano manual with images."""

    logger.info("\n" + "="*80)
    logger.info("STEP 2: EXTRACTING NANO MANUAL WITH IMAGES")
    logger.info("="*80)

    # Find Nano manual Word document
    nano_docx = Path("C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/intelia_products/nano/30-008-00096-605 Installation and Operation Manual Nano EN.docx")

    if not nano_docx.exists():
        logger.error(f"Nano manual Word document not found: {nano_docx}")
        return False

    logger.info(f"Processing: {nano_docx}")

    # Initialize extractor
    extractor = MultimodalExtractor(
        spaces_bucket=os.getenv("DO_SPACES_BUCKET", "intelia-knowledge"),
        enable_image_extraction=True
    )

    # Extract
    result = extractor.process_document(
        str(nano_docx),
        classification_path="intelia/intelia_products/nano/documentation/common",
        extract_images=True
    )

    # Results
    logger.info("\n" + "="*80)
    logger.info("EXTRACTION RESULTS")
    logger.info("="*80)
    logger.info(f"Success: {result['success']}")
    logger.info(f"Text chunks: {result['text_chunks']}")
    logger.info(f"Images extracted: {result['images']}")
    logger.info(f"Errors: {len(result['errors'])}")

    if result['errors']:
        logger.warning("\nErrors:")
        for error in result['errors']:
            logger.warning(f"  - {error}")

    extractor.print_statistics()

    return result['success']


if __name__ == "__main__":
    logger.info("="*80)
    logger.info("NANO MANUAL: CLEANUP & RE-EXTRACT WITH IMAGES")
    logger.info("="*80)

    # Step 1: Cleanup
    if not cleanup_nano_data():
        logger.error("Cleanup failed. Aborting.")
        sys.exit(1)

    # Step 2: Extract
    if not extract_nano_with_images():
        logger.error("Extraction failed.")
        sys.exit(1)

    logger.info("\n" + "="*80)
    logger.info("✓ COMPLETE - Nano manual re-extracted with images!")
    logger.info("="*80)
    sys.exit(0)
