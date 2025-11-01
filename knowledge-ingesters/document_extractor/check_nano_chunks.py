"""
Check if Nano manual text chunks are in Weaviate
"""
import os
import weaviate
from weaviate.classes.init import Auth
from dotenv import load_dotenv

load_dotenv()

# Prepare headers with OpenAI API key
headers = {}
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    headers["X-OpenAI-Api-Key"] = openai_api_key

# Connect
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=os.getenv("WEAVIATE_URL"),
    auth_credentials=Auth.api_key(os.getenv("WEAVIATE_API_KEY")),
    headers=headers
)

# Check InteliaKnowledge collection
print("Checking InteliaKnowledge collection...")
if client.collections.exists("InteliaKnowledge"):
    collection = client.collections.get("InteliaKnowledge")

    # Try to find Nano chunks
    response = collection.query.fetch_objects(
        limit=5,
        return_properties=["chunk_id", "source_file", "content"]
    )

    print(f"Total objects in collection: (need to aggregate)")

    # Show sample
    print(f"\nSample chunks:")
    for obj in response.objects:
        props = obj.properties
        source = props.get('source_file', 'unknown')
        if 'Nano' in source:
            print(f"  FOUND NANO: {props.get('chunk_id')}: {source}")
        else:
            print(f"  {props.get('chunk_id')}: {source[:80]}...")
else:
    print("InteliaKnowledge collection does NOT exist")

# Check InteliaExpertKnowledge collection
print("\n\nChecking InteliaExpertKnowledge collection...")
if client.collections.exists("InteliaExpertKnowledge"):
    collection = client.collections.get("InteliaExpertKnowledge")

    # Count
    count_response = collection.aggregate.over_all(total_count=True)
    print(f"Total objects: {count_response.total_count}")

    # Try to find Nano chunks
    response = collection.query.fetch_objects(
        limit=10,
        return_properties=["chunk_id", "source_file", "content"]
    )

    print(f"\nSample chunks:")
    nano_found = False
    for obj in response.objects:
        props = obj.properties
        source = props.get('source_file', 'unknown')
        if 'Nano' in source or 'nano' in source:
            print(f"  FOUND NANO: {props.get('chunk_id')}: {source}")
            nano_found = True
        else:
            print(f"  {props.get('chunk_id')}: {source[:80]}...")

    if not nano_found:
        print("\n  No Nano chunks in first 10 results")
else:
    print("InteliaExpertKnowledge collection does NOT exist")

client.close()
