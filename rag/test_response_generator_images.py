"""
Direct Test - Response Generator Image Integration
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import weaviate
from weaviate.classes.init import Auth
from core.data_models import RAGResult, RAGSource

# Fake document with Nano source
fake_docs = [{
    "source_file": "C:\\Software_Development\\intelia-cognito\\knowledge-ingesters\\Sources\\intelia\\intelia_products\\nano\\30-008-00096-605 Installation and Operation Manual Nano EN.docx",
    "content": "Installation instructions for Nano system",
    "chunk_id": "test_001"
}]

# Create RAGResult
result = RAGResult(
    source=RAGSource.RAG_SUCCESS,
    answer="Installation instructions...",
    confidence=0.9,
    context_docs=fake_docs
)

print(f"Initial state:")
print(f"  context_docs: {len(result.context_docs)}")
print(f"  images: {len(result.images)}")

# Connect to Weaviate
headers = {"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")}
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=os.getenv("WEAVIATE_URL"),
    auth_credentials=Auth.api_key(os.getenv("WEAVIATE_API_KEY")),
    headers=headers
)

# Test ImageRetriever directly
print("\nTesting ImageRetriever...")
from retrieval.image_retriever import ImageRetriever

retriever = ImageRetriever(client)
images = retriever.get_images_for_chunks(fake_docs, max_images_per_chunk=3)

print(f"\nResults:")
print(f"  Images found: {len(images)}")

if images:
    for img in images[:3]:
        print(f"    - {img['image_id']}: {img['image_url']}")
else:
    print("  NO IMAGES FOUND - This is the problem!")

client.close()
