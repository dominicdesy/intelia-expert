"""
Quick script to check InteliaImages count in Weaviate
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

# Count
response = collection.aggregate.over_all(total_count=True)
print(f"Total images in InteliaImages: {response.total_count}")

# Get a sample
sample = collection.query.fetch_objects(limit=3)
print(f"\nSample images:")
for obj in sample.objects:
    props = obj.properties
    print(f"  - {props.get('image_id')}: {props.get('source_file', 'no source')[:80]}...")

client.close()
