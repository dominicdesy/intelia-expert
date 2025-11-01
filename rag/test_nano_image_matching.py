"""
Test Nano Image Matching - Debug why images don't match question context
"""
import os
import sys
from dotenv import load_dotenv
import weaviate
from weaviate.auth import Auth
import weaviate.classes as wvc

# Fix Windows console encoding
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

# Connect to Weaviate
openai_key = os.getenv('OPENAI_API_KEY')
headers = {'X-OpenAI-Api-Key': openai_key} if openai_key else {}

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=os.getenv('WEAVIATE_URL'),
    auth_credentials=Auth.api_key(os.getenv('WEAVIATE_API_KEY')),
    headers=headers,
    skip_init_checks=True
)

print("="*80)
print("TESTING NANO IMAGE MATCHING")
print("="*80)

# Step 1: Simulate a Nano question - retrieve text chunks
print("\n[1/4] Retrieving text chunks for 'nano ventilation system'...")
text_coll = client.collections.get('InteliaKnowledge')
text_response = text_coll.query.near_text(
    query='nano ventilation system',
    limit=5,
    return_properties=['source_file', 'content']
)

print(f"Found {len(text_response.objects)} text chunks")
for i, obj in enumerate(text_response.objects, 1):
    source_file = obj.properties.get('source_file', 'N/A')
    content = obj.properties.get('content', '')[:100]
    print(f"\n  Chunk {i}:")
    print(f"    source_file: {source_file}")
    print(f"    content: {content}...")

# Step 2: Extract unique source files
print("\n[2/4] Extracting unique source files from chunks...")
source_files = set()
for obj in text_response.objects:
    sf = obj.properties.get('source_file')
    if sf:
        source_files.add(sf)

print(f"Unique source files: {len(source_files)}")
for sf in source_files:
    print(f"  - {sf}")

# Step 3: Query images using the EXACT source_file
print("\n[3/4] Querying images with source_file filter...")
img_coll = client.collections.get('InteliaImages')

for source_file in source_files:
    print(f"\n  Testing filter: {source_file}")

    # Test 1: contains_any (current method)
    try:
        response = img_coll.query.fetch_objects(
            filters=wvc.query.Filter.by_property('source_file').contains_any([source_file]),
            limit=5,
            return_properties=['image_url', 'page_number', 'caption']
        )
        print(f"    contains_any() → Found {len(response.objects)} images")
        for obj in response.objects:
            page = obj.properties.get('page_number', 'N/A')
            url = obj.properties.get('image_url', 'N/A')
            print(f"      - Page {page}: {url[-60:]}")
    except Exception as e:
        print(f"    contains_any() → ERROR: {e}")

    # Test 2: equal (exact match)
    try:
        response2 = img_coll.query.fetch_objects(
            filters=wvc.query.Filter.by_property('source_file').equal(source_file),
            limit=5,
            return_properties=['image_url', 'page_number', 'caption']
        )
        print(f"    equal() → Found {len(response2.objects)} images")
    except Exception as e:
        print(f"    equal() → ERROR: {e}")

# Step 4: Check all Nano images
print("\n[4/4] Checking ALL Nano images in database...")
all_images = img_coll.query.fetch_objects(limit=1000, return_properties=['source_file', 'image_url'])
nano_images = [obj for obj in all_images.objects if 'nano' in obj.properties.get('source_file', '').lower()]

print(f"Total images in database: {len(all_images.objects)}")
print(f"Nano images: {len(nano_images)}")

if nano_images:
    print("\nSample Nano image source_files:")
    for obj in nano_images[:3]:
        print(f"  - {obj.properties.get('source_file', 'N/A')}")

client.close()

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
