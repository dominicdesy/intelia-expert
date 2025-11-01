"""
Check what structure context_docs has after retrieval
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Set minimal logging
import logging
logging.basicConfig(level=logging.ERROR)

print("=" * 80)
print("CHECKING CONTEXT_DOCS STRUCTURE")
print("=" * 80)

from core.rag_engine import InteliaRAGEngine

# Initialize RAG engine
print("\n[1/3] Initializing RAG engine...")
engine = InteliaRAGEngine()

# Run a simple query about Nano
query = "What are the installation steps for the Nano system?"
print(f"\n[2/3] Running query: '{query}'")
print("(This will take 10-20 seconds...)\n")

# Process query
result = engine.query_sync(query, language="en", user_id="test")

print(f"\n[3/3] RESULTS:")
print(f"  - Answer length: {len(result.get('answer', ''))} chars")
print(f"  - Context docs: {len(result.get('context_docs', []))} documents")
print(f"  - Images: {len(result.get('images', []))} images")

# Check structure of context_docs
context_docs = result.get('context_docs', [])
if context_docs:
    print(f"\n  Context docs structure:")
    first_doc = context_docs[0]
    print(f"    Type: {type(first_doc)}")
    if isinstance(first_doc, dict):
        print(f"    Keys: {list(first_doc.keys())}")
        print(f"    Has 'source_file': {'source_file' in first_doc}")
        if 'source_file' in first_doc:
            print(f"    source_file value: {first_doc['source_file'][:100]}...")
        if 'metadata' in first_doc:
            print(f"    Has metadata dict: True")
            print(f"    metadata keys: {list(first_doc['metadata'].keys())}")
            if 'source_file' in first_doc['metadata']:
                print(f"    metadata.source_file: {first_doc['metadata']['source_file'][:100]}...")
else:
    print("\n  NO CONTEXT DOCS - This is a problem!")

# Show images info
images = result.get('images', [])
if images:
    print(f"\n  Images found:")
    for img in images[:3]:
        print(f"    - {img.get('image_id', 'N/A')}: {img.get('image_url', 'N/A')[:80]}...")
else:
    print(f"\n  NO IMAGES - Why?")
    if context_docs:
        print(f"    Possible reason: context_docs don't have source_file field")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
