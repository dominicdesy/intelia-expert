"""
Direct test of ImageRetriever with known source_file
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import weaviate
from weaviate.classes.init import Auth

# Source file we know exists (from previous test)
nano_source_file = "C:\\Software_Development\\intelia-cognito\\knowledge-ingesters\\Sources\\intelia\\intelia_products\\nano\\30-008-00096-605 Installation and Operation Manual Nano EN.docx"

print("Testing ImageRetriever directly...")
print(f"Source file: {nano_source_file[:80]}...")

# Connect to Weaviate
headers = {"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")}
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=os.getenv("WEAVIATE_URL"),
    auth_credentials=Auth.api_key(os.getenv("WEAVIATE_API_KEY")),
    headers=headers,
    skip_init_checks=True
)

# Create fake chunks with this source_file
from core.data_models import Document

fake_chunks = [
    Document(
        content="Test content",
        metadata={"source_file": nano_source_file}
    )
]

print(f"\nCreated {len(fake_chunks)} fake Document with source_file in metadata")
print(f"  doc.get('source_file'): {fake_chunks[0].get('source_file')[:80]}...")

# Test ImageRetriever
from retrieval.image_retriever import ImageRetriever

retriever = ImageRetriever(client)
images = retriever.get_images_for_chunks(fake_chunks, max_images_per_chunk=5)

print(f"\nResults:")
print(f"  Images found: {len(images)}")

if images:
    print(f"\n  [SUCCESS] Retrieved images:")
    for i, img in enumerate(images[:3], 1):
        print(f"    {i}. {img.get('image_id')}: {img.get('caption', 'N/A')[:60]}")
else:
    print(f"\n  [ERROR] No images found!")
    print(f"  This means ImageRetriever cannot find images even with correct source_file")

client.close()
