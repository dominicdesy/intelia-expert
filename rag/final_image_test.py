"""
Final Image Retrieval Test - Forces Intelia documents
"""
import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.WARNING)

async def main():
    print("="*80)
    print("FINAL IMAGE RETRIEVAL TEST")
    print("="*80)

    from core.rag_engine import InteliaRAGEngine

    engine = InteliaRAGEngine()
    await engine.initialize()

    # Query that will force Intelia Nano documents (avoid external search)
    # By asking specifically about Nano installation, it should find high-confidence matches
    test_queries = [
        ("How do I connect the Nano controller to my poultry barn equipment?", "en"),
        ("Comment installer le systeme Nano pour volailles?", "fr"),
    ]

    for i, (query, lang) in enumerate(test_queries, 1):
        print(f"\n[Test {i}/{len(test_queries)}]")
        print(f"Query: {query}")
        print(f"Language: {lang}")

        result = await engine.generate_response(
            query=query,
            language=lang,
            user_id="test"
        )

        print(f"\nResults:")
        print(f"  Source: {result.source.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Context docs: {len(result.context_docs)}")
        print(f"  Images: {len(result.images)}")

        # Check first doc structure
        if result.context_docs:
            doc = result.context_docs[0]
            if isinstance(doc, dict):
                has_source_file = 'source_file' in doc or ('metadata' in doc and 'source_file' in doc.get('metadata', {}))
                doc_source = doc.get('metadata', {}).get('source', 'unknown')
                print(f"  First doc has source_file: {has_source_file}")
                print(f"  First doc source: {doc_source}")

        # Show images
        if result.images:
            print(f"\n  [SUCCESS] Found {len(result.images)} images:")
            for img in result.images[:3]:
                print(f"    - {img.get('image_id')}: {img.get('caption', 'N/A')[:60]}...")
        else:
            print(f"\n  [INFO] No images found")
            if result.context_docs:
                print(f"    Reason: Documents may not have source_file or are external sources")

    await engine.close()

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
