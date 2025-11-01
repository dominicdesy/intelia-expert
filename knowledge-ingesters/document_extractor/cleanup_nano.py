"""
Cleanup Nano Manual from Weaviate
Delete all existing Nano manual chunks before re-extraction with images
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import Filter

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_nano_manual():
    """Delete all Nano manual data from Weaviate."""

    # Connect to Weaviate
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
        # 1. Clean InteliaKnowledge collection (text chunks)
        logger.info("\n" + "="*80)
        logger.info("CLEANING INTELIA KNOWLEDGE (Text Chunks)")
        logger.info("="*80)

        collection = client.collections.get("InteliaKnowledge")

        # Count existing Nano chunks
        logger.info("Counting existing Nano manual chunks...")

        # Search for Nano manual chunks (multiple possible patterns)
        nano_patterns = [
            "nano-manual",
            "nano_manual",
            "nano/",
            "/nano/"
        ]

        total_deleted = 0

        for pattern in nano_patterns:
            try:
                # Find objects matching pattern
                response = collection.query.fetch_objects(
                    filters=Filter.by_property("source_file").contains_any([pattern]),
                    limit=1000
                )

                count = len(response.objects)

                if count > 0:
                    logger.info(f"  Found {count} chunks matching pattern '{pattern}'")

                    # Delete them
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

        # 2. Clean InteliaImages collection (if exists)
        logger.info("\n" + "="*80)
        logger.info("CLEANING INTELIA IMAGES (Image Metadata)")
        logger.info("="*80)

        if client.collections.exists("InteliaImages"):
            images_collection = client.collections.get("InteliaImages")

            total_images_deleted = 0

            for pattern in nano_patterns:
                try:
                    # Find image objects matching pattern
                    response = images_collection.query.fetch_objects(
                        filters=Filter.by_property("source_file").contains_any([pattern]),
                        limit=1000
                    )

                    count = len(response.objects)

                    if count > 0:
                        logger.info(f"  Found {count} images matching pattern '{pattern}'")

                        # Delete them
                        for obj in response.objects:
                            try:
                                images_collection.data.delete_by_id(obj.uuid)
                                total_images_deleted += 1
                            except Exception as e:
                                logger.error(f"    Error deleting {obj.uuid}: {e}")

                        logger.info(f"  ✓ Deleted {count} images")

                except Exception as e:
                    logger.warning(f"  Warning with pattern '{pattern}': {e}")

            logger.info(f"\n✓ Total image metadata deleted: {total_images_deleted}")
        else:
            logger.info("  InteliaImages collection does not exist yet (will be created)")

        # Summary
        logger.info("\n" + "="*80)
        logger.info("CLEANUP COMPLETE")
        logger.info("="*80)
        logger.info(f"Text chunks deleted: {total_deleted}")
        logger.info(f"Image metadata deleted: {total_images_deleted if client.collections.exists('InteliaImages') else 0}")
        logger.info("\nYou can now run multimodal extraction:")
        logger.info('  python multimodal_extractor.py "Sources/intelia/intelia_products/nano/nano-manual.pdf"')
        logger.info("="*80)

        return True

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return False

    finally:
        client.close()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("NANO MANUAL CLEANUP")
    print("="*80)
    print("This will DELETE all existing Nano manual data from Weaviate")
    print("  - Text chunks from InteliaKnowledge collection")
    print("  - Image metadata from InteliaImages collection")
    print("="*80)

    response = input("\nAre you sure you want to continue? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        success = cleanup_nano_manual()
        sys.exit(0 if success else 1)
    else:
        print("\nCleanup cancelled.")
        sys.exit(0)
