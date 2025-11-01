"""
Simple end-to-end test for image retrieval (no Unicode emojis)
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
    print("\n" + "=" * 80)
    print("END-TO-END IMAGE RETRIEVAL TEST")
    print("=" * 80 + "\n")

    from core.rag_engine import InteliaRAGEngine

    engine = InteliaRAGEngine()
    await engine.initialize()

    # Test with Nano query
    query = "Comment installer le systeme Nano pour volailles?"
    language = "fr"

    print(f"Query: {query}")
    print(f"Language: {language}\n")

    result = await engine.generate_response(
        query=query,
        language=language,
        user_id="test"
    )

    print(f"Results:")
    print(f"  Answer length: {len(result.answer) if result.answer else 0} chars")
    print(f"  Context docs: {len(result.context_docs)}")
    print(f"  Images: {len(result.images)}")

    if result.context_docs:
        doc = result.context_docs[0]
        if hasattr(doc, 'metadata') and 'source_file' in doc.metadata:
            source_file = doc.metadata['source_file']
            print(f"\n  First doc source: {source_file}")

    if result.images:
        print(f"\n  [SUCCESS] Retrieved {len(result.images)} images!")
        for i, img in enumerate(result.images, 1):
            print(f"\n    Image {i}:")
            print(f"      ID: {img.get('image_id')}")
            caption = img.get('caption', 'N/A')
            if len(caption) > 60:
                caption = caption[:60] + "..."
            print(f"      Caption: {caption}")
            print(f"      Type: {img.get('image_type', 'N/A')}")
    else:
        print(f"\n  [ERROR] No images retrieved!")

    await engine.close()

    print(f"\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
