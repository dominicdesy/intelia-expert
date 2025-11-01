"""
Simple Test - Ingest Just ONE Image to Weaviate
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

# Get collection
collection = client.collections.get("InteliaImages")

# Simple test metadata
test_metadata = {
    "image_id": "test_001",
    "image_url": "https://intelia-knowledge.tor1.cdn.digitaloceanspaces.com/documents/test.png",
    "caption": "Test image",
    "page_number": 1,
    "source_file": "test.pdf",
    "image_type": "diagram",
    "width": 800,
    "height": 600,
    "file_size_kb": 100.0,
    "format": "png",
    "linked_chunk_ids": [],
    "owner_org_id": "intelia",
    "visibility_level": "public",
    "site_type": "test",
    "category": "test",
    "extracted_at": "2025-10-31T00:00:00Z"
}

# Insert
print("Inserting test image...")
uuid = collection.data.insert(properties=test_metadata)
print(f"SUCCESS - Inserted with UUID: {uuid}")

# Count
response = collection.aggregate.over_all(total_count=True)
print(f"\nTotal images in InteliaImages: {response.total_count}")

client.close()
print("\nSUCCESS - Test complete!")
