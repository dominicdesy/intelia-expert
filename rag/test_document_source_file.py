"""
Test if Document objects have source_file in metadata
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
    print("Testing Document source_file access...")

    from core.rag_engine import InteliaRAGEngine

    engine = InteliaRAGEngine()
    await engine.initialize()

    result = await engine.generate_response(
        query="Comment installer le systeme Nano pour volailles?",
        language="fr",
        user_id="test"
    )

    print(f"\nResults:")
    print(f"  Context docs: {len(result.context_docs)}")
    print(f"  Images: {len(result.images)}")

    if result.context_docs:
        doc = result.context_docs[0]
        print(f"\n  First Document:")
        print(f"    Type: {type(doc).__name__}")

        # Try to access source_file via get()
        sf_via_get = doc.get("source_file") if hasattr(doc, 'get') else None
        print(f"    doc.get('source_file'): {sf_via_get[:80] if sf_via_get else 'None'}")

        # Try to access metadata directly
        if hasattr(doc, 'metadata'):
            print(f"    doc.metadata keys: {list(doc.metadata.keys())[:10]}")
            if 'source_file' in doc.metadata:
                print(f"    doc.metadata['source_file']: {doc.metadata['source_file'][:80]}")
            else:
                print(f"    [ERROR] source_file NOT in doc.metadata")

    if result.images:
        print(f"\n  [SUCCESS] {len(result.images)} images found!")
        for img in result.images[:2]:
            print(f"    - {img.get('image_id')}")
    else:
        print(f"\n  [ERROR] No images found")

    await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
