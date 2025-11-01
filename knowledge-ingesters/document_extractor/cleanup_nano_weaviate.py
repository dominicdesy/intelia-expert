"""
Clean up Nano data from Weaviate
Deletes all Nano text chunks and images to prepare for fresh ingestion
Version: 1.0.0
"""
import os
import sys
from dotenv import load_dotenv
import weaviate
from weaviate.auth import Auth
import weaviate.classes as wvc

# Fix Windows encoding
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

print("="*80)
print("CLEANING UP NANO DATA FROM WEAVIATE")
print("="*80)
print("\n⚠️  WARNING: This will DELETE all Nano text chunks and images!")
print("This operation cannot be undone.\n")

# Ask for confirmation
confirmation = input("Type 'DELETE NANO' to confirm: ")
if confirmation != "DELETE NANO":
    print("❌ Cleanup cancelled.")
    sys.exit(0)

print("\n✅ Confirmation received. Starting cleanup...\n")

# Connect to Weaviate
openai_key = os.getenv('OPENAI_API_KEY')
headers = {'X-OpenAI-Api-Key': openai_key} if openai_key else {}

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=os.getenv('WEAVIATE_URL'),
    auth_credentials=Auth.api_key(os.getenv('WEAVIATE_API_KEY')),
    headers=headers,
    skip_init_checks=True
)

# Nano source file pattern
NANO_SOURCE = "30-008-00096-605 Installation and Operation Manual Nano EN.docx"

try:
    # Step 1: Delete Nano text chunks from InteliaKnowledge
    print("[1/2] Deleting Nano text chunks from InteliaKnowledge...")

    knowledge_coll = client.collections.get("InteliaKnowledge")

    # Query all Nano chunks
    response = knowledge_coll.query.fetch_objects(
        filters=wvc.query.Filter.by_property("source_file").contains_any([NANO_SOURCE]),
        limit=10000,
        return_properties=["source_file"]
    )

    chunk_count = len(response.objects)
    print(f"   Found {chunk_count} Nano text chunks")

    if chunk_count > 0:
        # Delete by filter (more efficient than one-by-one)
        deleted = knowledge_coll.data.delete_many(
            where=wvc.query.Filter.by_property("source_file").contains_any([NANO_SOURCE])
        )
        print(f"   ✅ Deleted {deleted.successful} text chunks")
        if deleted.failed > 0:
            print(f"   ⚠️  Failed to delete {deleted.failed} chunks")
    else:
        print("   ℹ️  No Nano text chunks found")

    # Step 2: Delete Nano images from InteliaImages
    print("\n[2/2] Deleting Nano images from InteliaImages...")

    images_coll = client.collections.get("InteliaImages")

    # Query all Nano images
    response = images_coll.query.fetch_objects(
        filters=wvc.query.Filter.by_property("source_file").contains_any([NANO_SOURCE]),
        limit=1000,
        return_properties=["source_file", "image_url"]
    )

    image_count = len(response.objects)
    print(f"   Found {image_count} Nano images")

    if image_count > 0:
        # Delete by filter
        deleted = images_coll.data.delete_many(
            where=wvc.query.Filter.by_property("source_file").contains_any([NANO_SOURCE])
        )
        print(f"   ✅ Deleted {deleted.successful} images")
        if deleted.failed > 0:
            print(f"   ⚠️  Failed to delete {deleted.failed} images")
    else:
        print("   ℹ️  No Nano images found")

    print("\n" + "="*80)
    print("CLEANUP COMPLETE")
    print("="*80)
    print(f"\n✅ Summary:")
    print(f"   - Text chunks deleted: {chunk_count}")
    print(f"   - Images deleted: {image_count}")
    print(f"\n🎯 Ready for fresh Nano ingestion!")

except Exception as e:
    print(f"\n❌ Error during cleanup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    client.close()
