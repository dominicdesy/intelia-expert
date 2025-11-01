"""
Verify source_file is now present in context_docs after fix
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
    print("Verifying source_file is present in context_docs...")

    from core.rag_engine import InteliaRAGEngine

    engine = InteliaRAGEngine()
    await engine.initialize()

    # Query that finds Nano documents
    result = await engine.generate_response(
        query="Comment installer le systeme Nano pour volailles?",
        language="fr",
        user_id="test"
    )

    print(f"\nResults:")
    print(f"  Context docs: {len(result.context_docs)}")
    print(f"  Images: {len(result.images)}")

    # Check first 3 docs
    if result.context_docs:
        for i, doc in enumerate(result.context_docs[:3], 1):
            print(f"\n  Doc {i}:")
            print(f"    Type: {type(doc)}")

            if isinstance(doc, dict):
                print(f"    Keys: {list(doc.keys())}")
                # Check direct source_file
                if 'source_file' in doc:
                    print(f"    [OK] Has source_file (direct): {doc['source_file'][:80]}...")
                # Check metadata source_file
                elif 'metadata' in doc and isinstance(doc['metadata'], dict):
                    if 'source_file' in doc['metadata']:
                        sf = doc['metadata']['source_file']
                        print(f"    [OK] Has source_file (metadata): {sf[:80] if sf else 'EMPTY'}")
                    else:
                        print(f"    [ERROR] No source_file in metadata")
                        print(f"    metadata keys: {list(doc['metadata'].keys())}")
                else:
                    print(f"    [ERROR] No source_file field found")
            else:
                print(f"    [ERROR] Not a dict!")
    else:
        print("\n  [ERROR] No context_docs")

    if result.images:
        print(f"\n  [SUCCESS] {len(result.images)} images retrieved!")
        for img in result.images[:2]:
            print(f"    - {img.get('image_id')}")
    else:
        print(f"\n  [INFO] No images retrieved")

    await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
