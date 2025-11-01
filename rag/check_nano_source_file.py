"""
Check if Nano manual documents in Weaviate have source_file property
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
    print("CHECKING source_file IN NANO MANUAL DOCUMENTS")
    print("=" * 80 + "\n")

    from core.rag_engine import InteliaRAGEngine

    engine = InteliaRAGEngine()
    await engine.initialize()

    if not engine.weaviate_core or not engine.weaviate_core.weaviate_client:
        print("[ERROR] Weaviate client not initialized")
        return

    client = engine.weaviate_core.weaviate_client
    collection = client.collections.get("InteliaKnowledge")

    # Search for Nano documents using "nano" keyword
    from utils.imports_and_dependencies import wvc

    response = collection.query.fetch_objects(
        filters=wvc.query.Filter.by_property("content").contains_any(["nano", "Nano", "NANO"]),
        limit=20
    )

    print(f"Found {len(response.objects)} documents mentioning 'Nano'\n")

    has_source_file_count = 0
    missing_source_file_count = 0
    empty_source_file_count = 0

    for i, obj in enumerate(response.objects, 1):
        has_prop = "source_file" in obj.properties
        source_file_value = obj.properties.get("source_file", None)

        title = (obj.properties.get("title") or "No title")[:60]

        if has_prop and source_file_value:
            has_source_file_count += 1
            print(f"[OK] Doc {i}: '{title}'")
            print(f"      source_file = '{source_file_value[:80]}'")
        elif has_prop and not source_file_value:
            empty_source_file_count += 1
            print(f"[EMPTY] Doc {i}: '{title}'")
            print(f"        source_file property exists but is EMPTY or None")
        else:
            missing_source_file_count += 1
            print(f"[MISSING] Doc {i}: '{title}'")
            print(f"          source_file property does NOT exist")

    print(f"\n" + "=" * 80)
    print(f"RESULTS for Nano documents:")
    print(f"  With source_file (valid): {has_source_file_count}/{len(response.objects)}")
    print(f"  With source_file (empty): {empty_source_file_count}/{len(response.objects)}")
    print(f"  Missing source_file: {missing_source_file_count}/{len(response.objects)}")

    if empty_source_file_count > 0 or missing_source_file_count > 0:
        print(f"\n[PROBLEM IDENTIFIED]")
        print(f"  Nano documents are missing or have empty source_file property!")
        print(f"  This explains why ImageRetriever cannot find images.")
        print(f"\n[SOLUTION]")
        print(f"  Need to re-ingest Nano manual with source_file properly populated")
    else:
        print(f"\n[OK] All Nano documents have valid source_file")

    print("=" * 80 + "\n")

    client.close()

if __name__ == "__main__":
    asyncio.run(main())
