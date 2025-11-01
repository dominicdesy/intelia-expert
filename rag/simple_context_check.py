"""
Minimal test to check context_docs structure
"""
import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise

async def main():
    print("Checking context_docs structure...")

    from core.rag_engine import InteliaRAGEngine

    engine = InteliaRAGEngine()
    await engine.initialize()

    # Simple Nano query
    result = await engine.generate_response(
        query="What is the Nano system?",
        language="en",
        user_id="test"
    )

    print(f"\nResults:")
    print(f"  Context docs: {len(result.context_docs)}")
    print(f"  Images: {len(result.images)}")

    if result.context_docs:
        doc = result.context_docs[0]
        print(f"\nFirst doc:")
        print(f"  Type: {type(doc)}")

        if isinstance(doc, dict):
            print(f"  Keys: {list(doc.keys())}")

            # Check for source_file
            if 'source_file' in doc:
                print(f"  [OK] source_file: {doc['source_file'][:80]}...")
            elif 'metadata' in doc and isinstance(doc['metadata'], dict):
                if 'source_file' in doc['metadata']:
                    print(f"  [OK] metadata.source_file: {doc['metadata']['source_file'][:80]}...")
                else:
                    print(f"  [ERROR] source_file NOT in metadata")
                    print(f"  metadata keys: {list(doc['metadata'].keys())}")
            else:
                print(f"  [ERROR] source_file NOT FOUND")
                print(f"  Available keys: {list(doc.keys())}")

    await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
