"""
Debug script to understand why images aren't being matched
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import weaviate
from weaviate.classes.init import Auth
import weaviate.classes as wvc

# Connect to Weaviate
headers = {"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")}
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=os.getenv("WEAVIATE_URL"),
    auth_credentials=Auth.api_key(os.getenv("WEAVIATE_API_KEY")),
    headers=headers,
    skip_init_checks=True
)

print("=" * 80)
print("DEBUGGING IMAGE MATCHING")
print("=" * 80)

# 1. Check what source_file values exist in InteliaKnowledge for Nano
print("\n[1/4] Checking source_file values in InteliaKnowledge for Nano chunks...")
knowledge = client.collections.get("InteliaKnowledge")
response = knowledge.query.fetch_objects(
    filters=wvc.query.Filter.by_property("content").contains_any(["Nano"]),
    limit=10,
    return_properties=["source_file", "content"]
)

print(f"Found {len(response.objects)} Nano chunks in InteliaKnowledge")
if response.objects:
    print("\nSample source_file values:")
    for i, obj in enumerate(response.objects[:3]):
        source_file = obj.properties.get("source_file", "N/A")
        content_preview = obj.properties.get("content", "")[:100]
        print(f"  {i+1}. {source_file}")
        print(f"     Content: {content_preview}...")

# 2. Check what source_file values exist in InteliaImages
print("\n[2/4] Checking source_file values in InteliaImages...")
images = client.collections.get("InteliaImages")
response = images.query.fetch_objects(limit=5, return_properties=["source_file", "image_id"])

print(f"Found {len(response.objects)} images (showing first 5)")
if response.objects:
    print("\nSample source_file values:")
    for i, obj in enumerate(response.objects):
        source_file = obj.properties.get("source_file", "N/A")
        image_id = obj.properties.get("image_id", "N/A")
        print(f"  {i+1}. {image_id}: {source_file}")

# 3. Compare the two
print("\n[3/4] Checking if source_file values match...")
nano_source = None
if response.objects:
    first_obj = list(knowledge.query.fetch_objects(
        filters=wvc.query.Filter.by_property("content").contains_any(["Nano"]),
        limit=1,
        return_properties=["source_file"]
    ).objects)
    if first_obj:
        nano_source = first_obj[0].properties.get("source_file")
        print(f"\nNano chunk source_file: {nano_source}")

        # Try to find images with this exact source_file
        print(f"\nSearching for images with this source_file...")
        image_response = images.query.fetch_objects(
            filters=wvc.query.Filter.by_property("source_file").equal(nano_source),
            limit=5
        )
        print(f"Found {len(image_response.objects)} images with exact match")

        # Try contains_any
        print(f"\nTrying contains_any instead of equal...")
        image_response2 = images.query.fetch_objects(
            filters=wvc.query.Filter.by_property("source_file").contains_any([nano_source]),
            limit=5
        )
        print(f"Found {len(image_response2.objects)} images with contains_any")

# 4. Show the actual ImageRetriever logic
print("\n[4/4] Testing ImageRetriever logic...")
from retrieval.image_retriever import ImageRetriever

fake_chunks = [{
    "source_file": nano_source,
    "content": "Test content",
    "chunk_id": "test_001"
}] if nano_source else []

if fake_chunks:
    retriever = ImageRetriever(client)
    images_found = retriever.get_images_for_chunks(fake_chunks, max_images_per_chunk=3)
    print(f"\nImageRetriever found: {len(images_found)} images")
    if images_found:
        for img in images_found[:3]:
            print(f"  - {img['image_id']}")
    else:
        print("  NO IMAGES FOUND - This is the problem!")

client.close()

print("\n" + "=" * 80)
print("DEBUGGING COMPLETE")
print("=" * 80)
