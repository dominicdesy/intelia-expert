"""
Check if Weaviate InteliaKnowledge objects have source_file property
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.WARNING)

async def main():
    print("\n" + "=" * 80)
    print("CHECKING source_file PROPERTY IN WEAVIATE")
    print("=" * 80 + "\n")

    from core.rag_engine import InteliaRAGEngine

    engine = InteliaRAGEngine()
    await engine.initialize()

    if not engine.weaviate_core or not engine.weaviate_core.weaviate_client:
        print("[ERROR] Weaviate client not initialized")
        return

    client = engine.weaviate_core.weaviate_client
    collection = client.collections.get("InteliaKnowledge")

    # Fetch a sample of objects
    response = collection.query.fetch_objects(limit=10)

    print(f"Checking {len(response.objects)} objects from InteliaKnowledge collection\n")

    has_source_file_count = 0
    missing_source_file_count = 0

    for i, obj in enumerate(response.objects, 1):
        has_source_file = "source_file" in obj.properties

        if has_source_file:
            has_source_file_count += 1
            source_file = obj.properties.get("source_file", "")
            print(f"[OK] Object {i}: source_file = '{source_file[:80] if source_file else 'EMPTY'}'")
        else:
            missing_source_file_count += 1
            print(f"[FAIL] Object {i}: source_file property MISSING")
            # Show available properties
            props = list(obj.properties.keys())[:12]
            print(f"       Available properties: {props}")

    print(f"\n" + "=" * 80)
    print(f"RESULTS:")
    print(f"  Objects with source_file: {has_source_file_count}/{len(response.objects)}")
    print(f"  Objects missing source_file: {missing_source_file_count}/{len(response.objects)}")

    if missing_source_file_count > 0:
        print(f"\n[ROOT CAUSE IDENTIFIED]")
        print(f"  Weaviate objects are missing 'source_file' property!")
        print(f"  This explains production error: 'No source files found in chunks'")
        print(f"\n[SOLUTION]")
        print(f"  Need to re-ingest data with source_file property included")
    else:
        print(f"\n[OK] All objects have source_file property")
        print(f"  The problem must be elsewhere in the code")

    print("=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
