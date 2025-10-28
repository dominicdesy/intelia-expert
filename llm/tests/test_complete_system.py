"""
Test complet du système LLM avec caching Redis et HuggingFace
"""

import httpx
import time

BASE_URL = "http://localhost:8081"


def test_complete_flow():
    """Test: Query → Cache Miss → LLM Call → Cache → Cache Hit"""

    print("=" * 80)
    print("TEST COMPLET: LLM SERVICE + REDIS CACHE + HUGGINGFACE")
    print("=" * 80)

    # Test request
    request_data = {
        "query": "What is the average weight of Ross 308 at 35 days?",
        "language": "en",
        "domain": "aviculture",
        "query_type": "genetics_performance",
        "entities": {"breed": "Ross 308", "age": 35},
        "context_docs": [
            {
                "text": "Ross 308 broiler performance at 35 days shows average weight of 2.2kg with feed conversion ratio of 1.65",
                "metadata": {"source": "Ross 308 Standards"},
            }
        ],
    }

    print("\n[1] FIRST REQUEST (Cache Miss)")
    print("-" * 80)
    start = time.time()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{BASE_URL}/v1/generate", json=request_data)
            duration1 = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                print(f"[OK] Status: {response.status_code}")
                print(f"[OK] Duration: {duration1:.0f}ms")
                print(f"[OK] Cached: {data.get('cached', False)}")
                print(
                    f"[OK] Response Length: {len(data.get('generated_text', ''))} chars"
                )
                print(f"[OK] Model: {data.get('model', 'N/A')}")
                print(f"[OK] Tokens: {data.get('total_tokens', 0)}")
                print("\nResponse Preview:")
                print(data.get("generated_text", "")[:200] + "...")
            else:
                print(f"[ERROR] Status: {response.status_code}")
                print(response.text)
                return False

    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False

    # Wait a bit
    print("\n[2] SECOND REQUEST (Cache Hit Expected)")
    print("-" * 80)
    time.sleep(1)
    start = time.time()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{BASE_URL}/v1/generate", json=request_data)
            duration2 = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                print(f"[OK] Status: {response.status_code}")
                print(f"[OK] Duration: {duration2:.0f}ms")
                print(f"[OK] Cached: {data.get('cached', False)}")

                if data.get("cached"):
                    print(
                        f"\n[SUCCESS] CACHE HIT! Latency reduced from {duration1:.0f}ms -> {duration2:.0f}ms"
                    )
                    improvement = ((duration1 - duration2) / duration1) * 100
                    print(f"   Performance improvement: {improvement:.1f}%")
                else:
                    print("\n[WARNING] Expected cache hit but got cache miss")
            else:
                print(f"[ERROR] Status: {response.status_code}")

    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False

    # Check cache stats
    print("\n[3] CACHE STATISTICS")
    print("-" * 80)
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{BASE_URL}/v1/cache/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"[OK] Cache Keys: {stats.get('cache_keys', 0)}")
                print(f"[OK] Redis Memory: {stats.get('redis_memory', 'N/A')}")
                print(f"[OK] TTL: {stats.get('ttl', 0)}s")
    except Exception as e:
        print(f"[WARNING] Could not fetch cache stats: {e}")

    print("\n" + "=" * 80)
    print("[OK] TEST COMPLETE")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_complete_flow()
    exit(0 if success else 1)
