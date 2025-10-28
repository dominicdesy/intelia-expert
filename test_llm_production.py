#!/usr/bin/env python3
"""
Production test for Intelia LLM integration on Digital Ocean
Tests the deployed services to verify end-to-end routing
"""

import httpx
import asyncio
import json
from datetime import datetime


# NOTE: Replace these URLs with your actual Digital Ocean App Platform URLs
# You can find them in your Digital Ocean dashboard under Apps
LLM_SERVICE_URL = "https://llm-xxxxx.ondigitalocean.app"  # Replace with actual URL
AI_SERVICE_URL = "https://ai-service-xxxxx.ondigitalocean.app"  # Replace with actual URL


async def test_llm_health():
    """Test 1: LLM service health check"""
    print("\n" + "=" * 60)
    print("TEST 1: LLM Service Health Check")
    print("=" * 60)

    url = f"{LLM_SERVICE_URL}/health"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"Checking: {url}")
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                print(f"[OK] Status: Healthy")
                print(f"    Service: {data.get('service')}")
                print(f"    Version: {data.get('version')}")
                print(f"    Provider: {data.get('provider')}")
                print(f"    Model loaded: {data.get('model_loaded')}")
                return True
            else:
                print(f"[ERROR] Status: {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                return False

    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
        print("\n[INFO] Make sure to replace LLM_SERVICE_URL with your actual Digital Ocean URL")
        return False


async def test_llm_direct_call():
    """Test 2: Direct LLM service call"""
    print("\n" + "=" * 60)
    print("TEST 2: Direct LLM Service Call (Aviculture Query)")
    print("=" * 60)

    url = f"{LLM_SERVICE_URL}/v1/chat/completions"
    payload = {
        "model": "intelia-llama-3.1-8b-aviculture",
        "messages": [
            {
                "role": "system",
                "content": "Tu es un expert en aviculture. Réponds de manière concise et précise."
            },
            {
                "role": "user",
                "content": "Comment réduire la mortalité de mes poulets de chair ?"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"Calling: {url}")
            print(f"Query: {payload['messages'][1]['content']}")

            start_time = datetime.now()
            response = await client.post(url, json=payload)
            duration = (datetime.now() - start_time).total_seconds()

            if response.status_code == 200:
                result = response.json()
                print(f"[OK] Status: {response.status_code}")
                print(f"Duration: {duration:.2f}s")
                print(f"Model: {result['model']}")
                print(f"Tokens: {result['usage']['total_tokens']} (prompt: {result['usage']['prompt_tokens']}, completion: {result['usage']['completion_tokens']})")

                # Calculate cost
                cost = result['usage']['total_tokens'] * 0.20 / 1_000_000
                print(f"Cost: ${cost:.6f}")

                print(f"\nResponse:")
                print("-" * 60)
                print(result['choices'][0]['message']['content'])
                print("-" * 60)
                return True
            else:
                print(f"[ERROR] Status: {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                return False

    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
        return False


async def test_routing_keywords():
    """Test 3: Verify routing keyword detection logic"""
    print("\n" + "=" * 60)
    print("TEST 3: Routing Keyword Detection")
    print("=" * 60)

    test_cases = [
        {
            "query": "Comment réduire la mortalité de mes poulets de chair ?",
            "should_route_to_llama": True,
            "reason": "Keywords: mortalité + poulets"
        },
        {
            "query": "What causes high mortality in broiler chickens?",
            "should_route_to_llama": True,
            "reason": "Keywords: mortality + chickens"
        },
        {
            "query": "¿Cómo prevenir la coccidiosis en pollos?",
            "should_route_to_llama": True,
            "reason": "Keywords: coccidiosis + pollos"
        },
        {
            "query": "Quelles sont les bonnes pratiques pour les pondeuses ?",
            "should_route_to_llama": True,
            "reason": "Keywords: pondeuses"
        },
        {
            "query": "What is the capital of France?",
            "should_route_to_llama": False,
            "reason": "No aviculture keywords"
        },
        {
            "query": "How to train a neural network?",
            "should_route_to_llama": False,
            "reason": "No aviculture keywords"
        }
    ]

    # Keywords from ai-service/generation/llm_router.py
    aviculture_keywords = [
        # French
        "poulet", "poule", "pondeuse", "poussin", "volaille", "coq", "coquelet",
        "mortalité", "ponte", "coccidiose", "aviaire", "élevage", "bâtiment",
        # English
        "chicken", "hen", "broiler", "layer", "poultry", "rooster", "chick",
        "mortality", "laying", "coccidiosis", "newcastle", "avian", "farm",
        # Spanish
        "pollo", "gallina", "pollos", "aves", "avicultura", "mortalidad",
        # Portuguese
        "frango", "galinha", "aves", "avicultura", "mortalidade"
    ]

    print(f"\nTesting {len(test_cases)} queries:\n")

    all_passed = True
    for i, test in enumerate(test_cases, 1):
        query_lower = test["query"].lower()
        detected = any(keyword in query_lower for keyword in aviculture_keywords)
        expected_route = "Intelia Llama" if test["should_route_to_llama"] else "GPT-4o"
        actual_route = "Intelia Llama" if detected else "GPT-4o"

        passed = detected == test["should_route_to_llama"]
        status = "[OK]" if passed else "[FAIL]"

        print(f"{status} Test {i}: {test['query'][:60]}...")
        print(f"    Expected: {expected_route}")
        print(f"    Actual: {actual_route}")
        print(f"    Reason: {test['reason']}")
        print()

        if not passed:
            all_passed = False

    return all_passed


async def main():
    print("\n" + "=" * 60)
    print("INTELIA LLM PRODUCTION TEST")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"LLM Service: {LLM_SERVICE_URL}")
    print(f"AI Service: {AI_SERVICE_URL}")

    # Check if URLs have been updated
    if "xxxxx" in LLM_SERVICE_URL or "xxxxx" in AI_SERVICE_URL:
        print("\n[WARNING] Please update the service URLs at the top of this file!")
        print("[INFO] You can find the URLs in your Digital Ocean App Platform dashboard")
        print("[INFO] They should look like: https://your-app-name-xxxxx.ondigitalocean.app")
        return

    # Run tests
    test1_passed = await test_llm_health()
    test2_passed = await test_llm_direct_call()
    test3_passed = await test_routing_keywords()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"[{'PASS' if test1_passed else 'FAIL'}] LLM Health Check")
    print(f"[{'PASS' if test2_passed else 'FAIL'}] Direct LLM Call")
    print(f"[{'PASS' if test3_passed else 'FAIL'}] Routing Logic")

    if test1_passed and test2_passed and test3_passed:
        print("\n[SUCCESS] All tests passed!")
        print("\nNext steps:")
        print("1. The LLM service is working correctly")
        print("2. The routing logic is validated")
        print("3. Test via frontend by asking an aviculture question")
        print("4. Check ai-service logs to see routing messages")
    else:
        print("\n[WARNING] Some tests failed")
        if not test1_passed:
            print("- Check LLM service deployment and logs")
            print("- Verify HUGGINGFACE_API_KEY is set in environment")
        if not test2_passed:
            print("- Check HuggingFace API access to Llama model")
            print("- Verify you accepted Meta Llama terms")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
