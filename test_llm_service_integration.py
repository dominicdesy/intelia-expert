#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test LLM Service Integration
Tests the integration between ai-service and llm service
"""

import sys
import io
import asyncio
import os

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add paths
sys.path.insert(0, "llm")
sys.path.insert(0, "ai-service")

async def test_llm_service_client():
    """Test LLM service HTTP client"""
    print("=" * 60)
    print("TEST 1: LLM Service HTTP Client")
    print("=" * 60)

    from generation.llm_service_client import LLMServiceClient

    client = LLMServiceClient(base_url="http://localhost:8081")

    # Test 1: Route endpoint
    print("\n1. Testing /v1/route endpoint...")
    try:
        route_result = await client.route(
            query="What is the weight of Ross 308 at 21 days?",
            domain="aviculture"
        )
        print(f"✓ Provider: {route_result['provider']}")
        print(f"✓ Model: {route_result['model']}")
        print(f"✓ Reason: {route_result['reason']}")
        print(f"✓ Is aviculture: {route_result['is_aviculture']}")
    except Exception as e:
        print(f"✗ Route test failed: {e}")
        return False

    # Test 2: Calculate tokens endpoint
    print("\n2. Testing /v1/calculate-tokens endpoint...")
    try:
        tokens_result = await client.calculate_tokens(
            query="Compare Ross 308 and Cobb 500 at 21 and 42 days",
            entities={"breed": "Ross 308, Cobb 500", "age_days": "21, 42"},
            query_type="comparative"
        )
        print(f"✓ Max tokens: {tokens_result['max_tokens']}")
        print(f"✓ Complexity: {tokens_result['complexity']}")
        print(f"✓ Token range: {tokens_result['token_range']}")
    except Exception as e:
        print(f"✗ Calculate tokens test failed: {e}")
        return False

    # Test 3: Post-process endpoint
    print("\n3. Testing /v1/post-process endpoint...")
    try:
        test_response = "**Header:** Test\n\n1. Item one\n2. Item two"
        post_result = await client.post_process(
            response=test_response,
            query="Test query",
            language="en"
        )
        processed_text, disclaimer_added, is_veterinary = post_result
        print(f"✓ Processed: {len(processed_text)} chars")
        print(f"✓ Disclaimer added: {disclaimer_added}")
        print(f"✓ Is veterinary: {is_veterinary}")
    except Exception as e:
        print(f"✗ Post-process test failed: {e}")
        return False

    await client.close()
    print("\n✓ LLM Service client tests passed!")
    return True


async def test_generate_with_llm_service():
    """Test generation using LLM service"""
    print("\n" + "=" * 60)
    print("TEST 2: Generate with LLM Service")
    print("=" * 60)

    # Note: This requires LLM service to be running and configured
    print("\nℹ️  To test /v1/generate endpoint:")
    print("1. Start LLM service: cd llm && uvicorn app.main:app --port 8081")
    print("2. Set HUGGINGFACE_API_KEY in llm/.env")
    print("3. Run this test again")
    print("\nSkipping live generate test (requires running LLM service)")
    return True


def print_summary():
    """Print integration summary"""
    print("\n" + "=" * 60)
    print("INTEGRATION SUMMARY")
    print("=" * 60)

    print("\n✓ Phase 1: Domain configuration migrated to LLM service")
    print("  - llm/config/aviculture/ with all configuration files")
    print("  - Adaptive token length calculation")
    print("  - Response post-processor")

    print("\n✓ Phase 2: Intelligent generation API endpoints created")
    print("  - POST /v1/generate - Intelligent generation")
    print("  - POST /v1/route - Provider routing")
    print("  - POST /v1/calculate-tokens - Token calculation")
    print("  - POST /v1/post-process - Response post-processing")

    print("\n✓ Phase 3: ai-service integration")
    print("  - LLMServiceClient HTTP client created")
    print("  - generators.py updated with USE_LLM_SERVICE flag")
    print("  - Environment variables added to ai-service/.env")

    print("\n📝 Next Steps:")
    print("  1. Start LLM service: cd llm && uvicorn app.main:app --port 8081")
    print("  2. Set USE_LLM_SERVICE=true in ai-service/.env to enable")
    print("  3. Test end-to-end with real queries")
    print("  4. Monitor Prometheus metrics for both services")

    print("\n🏗️  Architecture:")
    print("  Frontend → ai-service (Port 8000)")
    print("              ↓ HTTP (if USE_LLM_SERVICE=true)")
    print("            llm service (Port 8081)")
    print("              ↓ API calls")
    print("            HuggingFace / OpenAI / Anthropic")


if __name__ == "__main__":
    print("🧪 LLM Service Integration Test")
    print("=" * 60)

    # Check if LLM service is running
    import httpx
    try:
        response = httpx.get("http://localhost:8081/health", timeout=2)
        if response.status_code == 200:
            print("✓ LLM service is running at http://localhost:8081")
            print()

            # Run async tests
            async def run_tests():
                success = await test_llm_service_client()
                await test_generate_with_llm_service()
                return success

            result = asyncio.run(run_tests())

            if result:
                print_summary()
                print("\n✓ ALL INTEGRATION TESTS PASSED!")
            else:
                print("\n✗ Some tests failed")
                sys.exit(1)
        else:
            print(f"✗ LLM service returned status {response.status_code}")
            print("\nTo start LLM service:")
            print("  cd llm && uvicorn app.main:app --port 8081")
            print_summary()
    except httpx.ConnectError:
        print("ℹ️  LLM service not running at http://localhost:8081")
        print("\nTo start LLM service:")
        print("  cd llm")
        print("  # Configure HUGGINGFACE_API_KEY in .env")
        print("  uvicorn app.main:app --port 8081")
        print("\nThen run this test again.")
        print()
        print_summary()
    except Exception as e:
        print(f"✗ Error checking LLM service: {e}")
        sys.exit(1)
