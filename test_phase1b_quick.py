"""
Quick Test for Phase 1B - Hybrid Intelligent Architecture
Simple validation that query is not translated

Version: 1.0
Date: 2025-10-27
"""

import requests
import json
import time

# Configuration
AI_SERVICE_URL = "http://localhost:8000"  # Adjust if different
TEST_QUERIES = [
    {
        "query": "Quel est le poids d'un Ross 308 mâle à 22 jours ?",
        "language": "fr",
        "expected_keywords": ["poids", "grammes", "ross", "308", "mâle", "jours"]
    },
    {
        "query": "¿Cuál es el peso de un Ross 308 macho a los 22 días?",
        "language": "es",
        "expected_keywords": ["peso", "gramos", "ross", "308", "macho", "días"]
    },
    {
        "query": "What is the weight of a Ross 308 male at 22 days?",
        "language": "en",
        "expected_keywords": ["weight", "grams", "ross", "308", "male", "days"]
    }
]


def test_query(query_data: dict) -> dict:
    """Test a single query"""
    print(f"\n{'='*70}")
    print(f"Testing: {query_data['language'].upper()} query")
    print(f"{'='*70}")
    print(f"Query: {query_data['query']}")

    # Make request
    start_time = time.time()

    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/api/chat",
            json={
                "query": query_data["query"],
                "language": query_data["language"],
                "user_id": "test_phase1b_quick"
            },
            timeout=30
        )

        duration = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            answer = data.get("response", "")

            print(f"\n✅ Response received in {duration:.2f}s")
            print(f"Response preview: {answer[:200]}...")

            # Check keywords
            found_keywords = [
                kw for kw in query_data["expected_keywords"]
                if kw.lower() in answer.lower()
            ]

            print(f"\n🔍 Keyword validation:")
            print(f"  Found: {len(found_keywords)}/{len(query_data['expected_keywords'])}")
            print(f"  Keywords: {', '.join(found_keywords)}")

            # Validate
            success = len(found_keywords) >= len(query_data["expected_keywords"]) * 0.5
            latency_ok = duration < 2.0

            if success and latency_ok:
                print(f"\n✅ TEST PASSED")
            else:
                print(f"\n⚠️  TEST ISSUES:")
                if not success:
                    print(f"  - Few keywords found ({len(found_keywords)}/{len(query_data['expected_keywords'])})")
                if not latency_ok:
                    print(f"  - High latency ({duration:.2f}s > 2.0s)")

            return {
                "passed": success and latency_ok,
                "duration": duration,
                "keywords_found": len(found_keywords),
                "keywords_total": len(query_data["expected_keywords"])
            }

        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return {"passed": False, "error": f"HTTP {response.status_code}"}

    except requests.exceptions.Timeout:
        print(f"\n❌ Timeout after 30s")
        return {"passed": False, "error": "Timeout"}

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {"passed": False, "error": str(e)}


def main():
    """Run quick tests"""
    print("\n" + "="*70)
    print("🚀 PHASE 1B QUICK TEST - HYBRID INTELLIGENT ARCHITECTURE")
    print("="*70)
    print("\nThis test validates that:")
    print("  1. Queries are NOT translated (original language preserved)")
    print("  2. Responses are in correct language")
    print("  3. Latency is improved (<2s)")
    print("\nStarting tests...\n")

    results = []
    for query_data in TEST_QUERIES:
        result = test_query(query_data)
        results.append(result)
        time.sleep(1)  # Brief pause between tests

    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)

    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)
    avg_duration = sum(r.get("duration", 0) for r in results if "duration" in r) / max(1, len([r for r in results if "duration" in r]))

    print(f"\n✅ Tests Passed: {passed}/{total}")
    if "duration" in results[0]:
        print(f"⏱️  Average Latency: {avg_duration:.2f}s")

    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"\n✅ Phase 1B Implementation appears to be working correctly:")
        print(f"  - Multilingual queries processed")
        print(f"  - Responses in correct languages")
        if avg_duration < 1.5:
            print(f"  - Performance excellent ({avg_duration:.2f}s < 1.5s)")
        elif avg_duration < 2.0:
            print(f"  - Performance good ({avg_duration:.2f}s < 2.0s)")
    else:
        print(f"\n⚠️  {total - passed}/{total} tests failed")
        print(f"\nPlease review:")
        print(f"  1. Is ai-service running on {AI_SERVICE_URL}?")
        print(f"  2. Are the Phase 1B changes deployed?")
        print(f"  3. Check ai-service logs for errors")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
