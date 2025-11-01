"""
Check if Weaviate InteliaKnowledge objects have source_file property
"""
import asyncio
from retrieval.weaviate.core import WeaviateCore

async def main():
    # Init Weaviate
    weaviate_core = WeaviateCore()
    await weaviate_core.init()

    if not weaviate_core.weaviate_client:
        print("ERROR: Weaviate client not initialized")
        return

    collection = weaviate_core.weaviate_client.collections.get("InteliaKnowledge")

    # Fetch objects
    response = collection.query.fetch_objects(limit=10)

    print(f"\n=== Checking {len(response.objects)} objects from InteliaKnowledge ===\n")

    has_source_file_count = 0
    missing_source_file_count = 0

    for i, obj in enumerate(response.objects, 1):
        has_source_file = "source_file" in obj.properties

        if has_source_file:
            has_source_file_count += 1
            source_file = obj.properties.get("source_file", "")
            print(f"Object {i}: HAS source_file = '{source_file[:80]}'")
        else:
            missing_source_file_count += 1
            print(f"Object {i}: MISSING source_file")
            # Show what properties it does have
            props = list(obj.properties.keys())
            print(f"  Available properties: {props[:10]}")

    print(f"\n=== Summary ===")
    print(f"Objects with source_file: {has_source_file_count}/{len(response.objects)}")
    print(f"Objects missing source_file: {missing_source_file_count}/{len(response.objects)}")

    if missing_source_file_count > 0:
        print("\nPROBLEM: Weaviate objects are missing 'source_file' property!")
        print("This explains why ImageRetriever finds 'No source files found in chunks'")

    weaviate_core.weaviate_client.close()

if __name__ == "__main__":
    asyncio.run(main())
