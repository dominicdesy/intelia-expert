"""
Fix Image URLs in Weaviate - Remove .cdn. subdomain
Version: 1.0.0
Last modified: 2025-11-01

This script updates all image URLs in Weaviate to use the origin endpoint
instead of the CDN endpoint (which is disabled).

Changes: https://bucket.region.cdn.digitaloceanspaces.com/...
To: https://bucket.region.digitaloceanspaces.com/...
"""

import os
import sys
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import weaviate
from weaviate.auth import Auth

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_weaviate_client():
    """Initialize Weaviate client (v4 API)"""
    weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if weaviate_api_key:
        # Cloud connection with OpenAI headers for vectorization
        headers = {}
        if openai_api_key:
            headers["X-OpenAI-Api-Key"] = openai_api_key

        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
            headers=headers,
            skip_init_checks=True
        )
    else:
        # Local connection
        client = weaviate.connect_to_local()

    logger.info(f"✅ Connected to Weaviate at {weaviate_url}")
    return client


def fix_image_urls():
    """Update all image URLs to remove .cdn. subdomain"""

    client = get_weaviate_client()

    try:
        # Get collection
        collection = client.collections.get("InteliaImages")
        logger.info("✅ Got InteliaImages collection")

        # Query all objects
        logger.info("🔍 Querying all images from InteliaImages...")
        response = collection.query.fetch_objects(
            limit=10000,
            return_properties=["image_url", "source_file", "page_number"]
        )

        if not response or not response.objects:
            logger.warning("⚠️ No images found in database")
            return

        images = response.objects
        logger.info(f"📊 Found {len(images)} images in database")

        # Count and fix URLs
        fixed_count = 0
        already_correct = 0

        for obj in images:
            image_id = obj.uuid
            old_url = obj.properties.get("image_url", "")

            if not old_url:
                logger.warning(f"⚠️ Image {image_id} has no URL")
                continue

            # Check if URL uses .cdn. subdomain
            if ".cdn.digitaloceanspaces.com" in old_url:
                # Fix URL by removing .cdn.
                new_url = old_url.replace(
                    ".cdn.digitaloceanspaces.com",
                    ".digitaloceanspaces.com"
                )

                logger.info(f"🔧 Fixing image {image_id}")
                logger.info(f"   Old: {old_url}")
                logger.info(f"   New: {new_url}")

                # Update object in Weaviate (v4 API)
                try:
                    collection.data.update(
                        uuid=image_id,
                        properties={"image_url": new_url}
                    )
                    fixed_count += 1
                except Exception as e:
                    logger.error(f"❌ Failed to update image {image_id}: {e}")
            else:
                # URL already correct
                already_correct += 1

        logger.info(f"\n✅ Migration complete!")
        logger.info(f"   📊 Total images: {len(images)}")
        logger.info(f"   🔧 Fixed: {fixed_count}")
        logger.info(f"   ✓ Already correct: {already_correct}")

    finally:
        # Close connection
        client.close()


if __name__ == "__main__":
    try:
        fix_image_urls()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
