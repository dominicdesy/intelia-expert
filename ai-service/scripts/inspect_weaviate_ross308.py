"""
Script to directly query Weaviate and inspect what Ross 308 content is indexed.

This will help us understand:
1. Do good Ross 308 chunks exist in Weaviate?
2. What's the difference between "good" chunks and the "bad" calculation metadata chunks?
3. Why are calculation chunks ranking higher than source data chunks?
"""

import os
import sys
import weaviate
import json
from typing import List, Dict

def connect_weaviate():
    """Connect to Weaviate instance"""
    weaviate_url = os.getenv(
        "WEAVIATE_URL",
        "https://xmlc4jvtu6hfw9zrrmnw.c0.us-east1.gcp.weaviate.cloud",
    )
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY", "")

    if "weaviate.cloud" in weaviate_url:
        try:
            import weaviate.classes as wvc_classes
            client = weaviate.connect_to_weaviate_cloud(
                cluster_url=weaviate_url,
                auth_credentials=wvc_classes.init.Auth.api_key(weaviate_api_key),
            )
            print(f"✅ Connected to Weaviate: {weaviate_url}")
            return client
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return None
    else:
        print("❌ Only cloud instances supported by this script")
        return None

def search_keyword_bm25(client, keyword: str, limit: int = 10) -> List[Dict]:
    """Search using BM25 (keyword search)"""
    try:
        collection = client.collections.get("InteligencePoultryCollection")

        # BM25 search for keyword
        response = collection.query.bm25(
            query=keyword,
            limit=limit
        )

        results = []
        for obj in response.objects:
            results.append({
                "content": obj.properties.get("content", "")[:500],
                "metadata": obj.properties.get("metadata", {}),
                "uuid": str(obj.uuid)
            })

        return results

    except Exception as e:
        print(f"❌ BM25 search failed: {e}")
        return []

def search_by_metadata(client, metadata_field: str, metadata_value: str, limit: int = 10) -> List[Dict]:
    """Search by metadata filter"""
    try:
        collection = client.collections.get("InteligencePoultryCollection")

        # Filter by metadata
        response = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property(metadata_field).equal(metadata_value),
            limit=limit
        )

        results = []
        for obj in response.objects:
            results.append({
                "content": obj.properties.get("content", "")[:500],
                "metadata": obj.properties.get("metadata", {}),
                "uuid": str(obj.uuid)
            })

        return results

    except Exception as e:
        print(f"❌ Metadata search failed: {e}")
        return []

def main():
    print("="*100)
    print("WEAVIATE INSPECTION: Ross 308 Content Analysis")
    print("="*100)
    print()

    # Connect to Weaviate
    client = connect_weaviate()
    if not client:
        sys.exit(1)

    try:
        # Test 1: BM25 search for "Ross 308"
        print("TEST 1: BM25 Search for 'Ross 308'")
        print("-"*100)
        ross_results = search_keyword_bm25(client, "Ross 308", limit=5)

        if not ross_results:
            print("⚠️ NO results found for 'Ross 308' in BM25 search!")
            print("   This means the breed name may not be in the indexed chunks.")
        else:
            print(f"✅ Found {len(ross_results)} results for 'Ross 308'")
            for i, result in enumerate(ross_results, 1):
                print(f"\n--- Result {i} ---")
                print(f"Content preview: {result['content'][:200]}")
                print(f"Metadata: {json.dumps(result['metadata'], indent=2)}")

                # Check for "0.0 kg" problem
                if "0.0" in result['content']:
                    print("⚠️ WARNING: Contains '0.0' - likely a calculation metadata chunk")

        print("\n")

        # Test 2: BM25 search for "jour 18" + "consommation" (French keywords from query)
        print("TEST 2: BM25 Search for 'jour 18 consommation'")
        print("-"*100)
        french_results = search_keyword_bm25(client, "jour 18 consommation", limit=5)

        if not french_results:
            print("⚠️ NO results found for French keywords")
        else:
            print(f"✅ Found {len(french_results)} results")
            for i, result in enumerate(french_results, 1):
                print(f"\n--- Result {i} ---")
                print(f"Content preview: {result['content'][:200]}")

                # Check if this is a calculation or source data
                has_breed = 'ross' in result['content'].lower() or '308' in result['content'].lower()
                has_zero = '0.0' in result['content']

                print(f"Contains breed name: {has_breed}")
                print(f"Contains 0.0 (calculation metadata): {has_zero}")

        print("\n")

        # Test 3: BM25 search for "2400g" or "2.4 kg" (target weight)
        print("TEST 3: BM25 Search for '2400' (target weight)")
        print("-"*100)
        weight_results = search_keyword_bm25(client, "2400", limit=5)

        if not weight_results:
            print("⚠️ NO results found for target weight")
        else:
            print(f"✅ Found {len(weight_results)} results")
            for i, result in enumerate(weight_results, 1):
                print(f"\n--- Result {i} ---")
                print(f"Content preview: {result['content'][:200]}")

        print("\n")
        print("="*100)
        print("DIAGNOSTIC SUMMARY")
        print("="*100)
        print()

        if not ross_results:
            print("❌ PROBLEM 1: No 'Ross 308' chunks found in BM25 search")
            print("   → Possible causes:")
            print("     - Breed name not included in chunk content")
            print("     - Chunks are too generic or metadata-only")
            print("     - Source PDF processing removed breed names")

        if french_results:
            has_calculation_chunks = any("0.0" in r['content'] for r in french_results)
            if has_calculation_chunks:
                print("❌ PROBLEM 2: French keywords retrieve calculation metadata (0.0 values)")
                print("   → BM25 is matching calculation descriptions instead of source data")

        print("\nRECOMMENDED NEXT STEPS:")
        print("1. Check if breed names are preserved during PDF → JSON chunking")
        print("2. Inspect source JSONs in rag/vectorize_iris_json_generator/output/")
        print("3. Consider filtering calculation metadata during Weaviate indexing")
        print("4. Test if hybrid search (vector + BM25) retrieves better results")

    finally:
        client.close()
        print("\n✅ Weaviate connection closed")

if __name__ == "__main__":
    main()
