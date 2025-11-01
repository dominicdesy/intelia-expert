"""
Test Image Retrieval Integration
Version: 1.0.0

Test that images are properly retrieved and included in RAG responses.
"""

import asyncio
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_image_retrieval():
    """Test image retrieval with a Nano manual query."""

    logger.info("="*80)
    logger.info("TESTING IMAGE RETRIEVAL INTEGRATION")
    logger.info("="*80)

    # Initialize RAG Engine
    from core.rag_engine import InteliaRAGEngine

    logger.info("\n[1/3] Initializing RAG Engine...")
    engine = InteliaRAGEngine()
    await engine.initialize()

    # Test query about Nano manual
    test_query = "What are the installation steps for the Nano system?"

    logger.info(f"\n[2/3] Running test query: '{test_query}'")
    result = await engine.generate_response(
        query=test_query,
        language="fr",
        user_id="test_user"
    )

    # Check results
    logger.info("\n[3/3] Analyzing results...")
    logger.info("="*80)
    logger.info("RESULTS")
    logger.info("="*80)

    logger.info(f"Source: {result.source.value}")
    logger.info(f"Confidence: {result.confidence}")
    logger.info(f"Answer length: {len(result.answer) if result.answer else 0} characters")
    logger.info(f"Context docs: {len(result.context_docs)}")
    logger.info(f"Images: {len(result.images)}")
    logger.info(f"Has images: {result.metadata.get('has_images', False)}")

    if result.images:
        logger.info("\n📸 IMAGES FOUND:")
        for idx, image in enumerate(result.images, 1):
            logger.info(f"\n  Image {idx}:")
            logger.info(f"    ID: {image.get('image_id')}")
            logger.info(f"    URL: {image.get('image_url')}")
            logger.info(f"    Caption: {image.get('caption')}")
            logger.info(f"    Type: {image.get('image_type')}")
            logger.info(f"    Size: {image.get('width')}x{image.get('height')}")
    else:
        logger.info("\n❌ No images found")

    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETE")
    logger.info("="*80)

    # Close engine
    await engine.close()

    return result


if __name__ == "__main__":
    asyncio.run(test_image_retrieval())
