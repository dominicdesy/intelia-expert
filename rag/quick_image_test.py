"""
Quick Test - Verify Image Retrieval Works
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test():
    from core.rag_engine import InteliaRAGEngine

    logger.info("Initializing RAG Engine...")
    engine = InteliaRAGEngine()
    await engine.initialize()

    logger.info("Running query...")
    result = await engine.generate_response(
        query="What are the installation steps for the Nano system?",
        language="en",
        user_id="test"
    )

    logger.info(f"=== RESULTS ===")
    logger.info(f"Answer: {result.answer[:200]}...")
    logger.info(f"Context docs: {len(result.context_docs)}")
    logger.info(f"Images: {len(result.images)}")
    logger.info(f"Has images: {result.metadata.get('has_images', False)}")

    if result.images:
        logger.info(f"\nIMAGES FOUND:")
        for img in result.images[:3]:
            logger.info(f"  - {img['image_id']}: {img['image_url']}")
    else:
        logger.info("\nNO IMAGES FOUND")

    await engine.close()

if __name__ == "__main__":
    asyncio.run(test())
