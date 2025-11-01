"""
Simple Image Retrieval Test
Version: 1.0.0

Direct test of ImageRetriever without full RAG pipeline.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import weaviate
from weaviate.classes.init import Auth


def test_image_retrieval_direct():
    """Direct test of image retrieval."""

    logger.info("="*80)
    logger.info("SIMPLE IMAGE RETRIEVAL TEST")
    logger.info("="*80)

    # Connect to Weaviate
    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")

    logger.info(f"\n[1/4] Connecting to Weaviate...")
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(weaviate_api_key)
    )

    # Check InteliaImages collection exists
    logger.info(f"\n[2/4] Checking InteliaImages collection...")
    exists = client.collections.exists("InteliaImages")
    logger.info(f"  InteliaImages exists: {exists}")

    if not exists:
        logger.error("❌ InteliaImages collection does not exist!")
        client.close()
        return

    # Get a sample of images
    logger.info(f"\n[3/4] Fetching sample images...")
    collection = client.collections.get("InteliaImages")

    response = collection.query.fetch_objects(limit=5)

    logger.info(f"  Found {len(response.objects)} images")

    for obj in response.objects:
        logger.info(f"\n  Image:")
        logger.info(f"    ID: {obj.properties.get('image_id')}")
        logger.info(f"    URL: {obj.properties.get('image_url')}")
        logger.info(f"    Source: {obj.properties.get('source_file')}")
        logger.info(f"    Caption: {obj.properties.get('caption', '')[:100]}...")

    # Test ImageRetriever
    logger.info(f"\n[4/4] Testing ImageRetriever...")
    from retrieval.image_retriever import ImageRetriever

    retriever = ImageRetriever(client)

    # Create fake chunk to test
    test_chunks = [{
        "source_file": "C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/intelia_products/nano/30-008-00096-605 Installation and Operation Manual Nano EN.docx"
    }]

    images = retriever.get_images_for_chunks(test_chunks, max_images_per_chunk=5)

    logger.info(f"\n  Retrieved {len(images)} images")
    for img in images[:3]:  # Show first 3
        logger.info(f"\n    Image:")
        logger.info(f"      ID: {img.get('image_id')}")
        logger.info(f"      URL: {img.get('image_url')}")

    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETE")
    logger.info("="*80)

    client.close()


if __name__ == "__main__":
    test_image_retrieval_direct()
