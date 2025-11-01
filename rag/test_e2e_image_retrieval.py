"""
End-to-end test for image retrieval in RAG flow
Tests the complete flow: query → retrieval → image retrieval → response
"""
import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    print("=" * 80)
    print("END-TO-END IMAGE RETRIEVAL TEST")
    print("=" * 80)

    from core.rag_engine import InteliaRAGEngine

    engine = InteliaRAGEngine()
    await engine.initialize()

    # Test with a query that should match Nano documents
    test_queries = [
        ("Comment installer le systeme Nano pour volailles?", "fr"),
        ("How to install the Nano system for poultry?", "en"),
    ]

    for query, language in test_queries:
        print(f"\n{'=' * 80}")
        print(f"Query: {query}")
        print(f"Language: {language}")
        print(f"{'=' * 80}\n")

        result = await engine.generate_response(
            query=query,
            language=language,
            user_id="test"
        )

        print(f"\nResults:")
        print(f"  Answer length: {len(result.answer) if result.answer else 0} chars")
        print(f"  Context docs: {len(result.context_docs)}")
        print(f"  Images: {len(result.images)}")

        if result.context_docs:
            print(f"\n  First document:")
            doc = result.context_docs[0]
            print(f"    Content preview: {doc.content[:100]}...")

            # Check source_file
            if hasattr(doc, 'metadata') and 'source_file' in doc.metadata:
                source_file = doc.metadata['source_file']
                print(f"    Source file: {source_file[:80]}...")
            else:
                print(f"    [WARNING] No source_file in metadata")

        if result.images:
            print(f"\n  ✅ SUCCESS: Retrieved {len(result.images)} images!")
            for i, img in enumerate(result.images[:3], 1):
                print(f"\n    Image {i}:")
                print(f"      ID: {img.get('image_id')}")
                print(f"      URL: {img.get('image_url', 'N/A')[:80]}...")
                print(f"      Caption: {img.get('caption', 'N/A')[:60]}...")
                print(f"      Type: {img.get('image_type', 'N/A')}")
                print(f"      Source: {img.get('source_file', 'N/A')[:60]}...")
        else:
            print(f"\n  ❌ ERROR: No images retrieved!")
            print(f"  This indicates the image retrieval is not working properly.")

    await engine.close()

    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print(f"{'=' * 80}\n")

if __name__ == "__main__":
    asyncio.run(main())
