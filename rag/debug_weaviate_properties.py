"""
Debug script to check if Weaviate objects have source_file property
"""
import weaviate
import os

# Connect to Weaviate
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=os.getenv("WEAVIATE_URL"),
    auth_credentials=weaviate.auth.AuthApiKey(os.getenv("WEAVIATE_ADMIN_KEY")),
)

try:
    # Get InteliaKnowledge collection
    collection = client.collections.get("InteliaKnowledge")

    # Fetch a few objects
    response = collection.query.fetch_objects(limit=5)

    print(f"\n=== Checking {len(response.objects)} objects ===\n")

    for i, obj in enumerate(response.objects, 1):
        print(f"Object {i}:")
        print(f"  UUID: {obj.uuid}")
        print(f"  Properties keys: {list(obj.properties.keys())}")

        # Check specific properties
        has_source = "source" in obj.properties
        has_source_file = "source_file" in obj.properties

        print(f"  Has 'source': {has_source}")
        if has_source:
            print(f"    source = {obj.properties['source'][:80] if obj.properties.get('source') else 'None'}...")

        print(f"  Has 'source_file': {has_source_file}")
        if has_source_file:
            print(f"    source_file = {obj.properties['source_file']}")
        else:
            print(f"    source_file = NOT PRESENT")

        print()

finally:
    client.close()

print("\n=== Done ===")
