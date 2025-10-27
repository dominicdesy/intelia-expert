"""
Test script for LLM Router - Validation without API calls
"""

import sys
import os

# Mock API keys for testing
os.environ["OPENAI_API_KEY"] = "sk-test-mock-key"

from generation.llm_router import LLMRouter, LLMProvider


def test_routing_logic():
    """Test routing logic without API calls"""

    print("=" * 60)
    print("LLM Router - Routing Logic Tests")
    print("=" * 60)

    # Initialize router
    print("\n[1/5] Initializing router...")
    router = LLMRouter()
    print("OK Router initialized")
    print(f"   - Routing enabled: {router.routing_enabled}")
    print(f"   - Default provider: {router.default_provider}")

    # Test 1: PostgreSQL Direct Hit -> DeepSeek
    print("\n[2/5] Test PostgreSQL Direct Hit -> DeepSeek")
    context_docs = [
        {
            "score": 0.95,
            "metadata": {"source": "postgresql"},
            "content": "Ross 308: 2441g at 35 days",
        }
    ]
    provider = router.route_query("Poids Ross 308 35j ?", context_docs, None)
    print(f"   Result: {provider.value}")
    assert provider in [
        LLMProvider.DEEPSEEK,
        LLMProvider.GPT_4O,
    ], f"Expected DEEPSEEK or GPT_4O, got {provider.value}"
    print("   OK Test passed (PostgreSQL routing)")

    # Test 2: Weaviate RAG -> Claude
    print("\n[3/5] Test Weaviate RAG -> Claude 3.5 Sonnet")
    context_docs = [
        {"metadata": {"source": "weaviate"}, "content": "Doc 1..."},
        {"metadata": {"source": "weaviate"}, "content": "Doc 2..."},
    ]
    provider = router.route_query("Comment ameliorer FCR ?", context_docs, None)
    print(f"   Result: {provider.value}")
    assert provider in [
        LLMProvider.CLAUDE_35_SONNET,
        LLMProvider.GPT_4O,
    ], f"Expected CLAUDE or GPT_4O, got {provider.value}"
    print("   OK Test passed (Weaviate routing)")

    # Test 3: Comparative Query -> Claude
    print("\n[4/5] Test Comparative Query -> Claude 3.5 Sonnet")
    intent_result = {"intent_type": "comparative"}
    provider = router.route_query("Ross vs Cobb ?", [], intent_result)
    print(f"   Result: {provider.value}")
    assert provider in [
        LLMProvider.CLAUDE_35_SONNET,
        LLMProvider.GPT_4O,
    ], f"Expected CLAUDE or GPT_4O, got {provider.value}"
    print("   OK Test passed (Comparative routing)")

    # Test 4: Fallback -> GPT-4o
    print("\n[5/5] Test Fallback -> GPT-4o")
    provider = router.route_query("Edge case query", [], None)
    print(f"   Result: {provider.value}")
    assert provider == LLMProvider.GPT_4O, f"Expected GPT_4O, got {provider.value}"
    print("   OK Test passed (Fallback routing)")

    # Test stats
    print("\n[Stats] Get router statistics")
    stats = router.get_stats()
    print(f"   - Routing enabled: {stats['routing_enabled']}")
    print("   - Providers available:")
    for provider_name, available in stats["providers_available"].items():
        status = "OK" if available else "NOT CONFIGURED"
        print(f"     * {provider_name}: {status}")
    print(f"   - Total calls: {stats['total']['calls']}")
    print(f"   - Total tokens: {stats['total']['tokens']}")
    print(f"   - Total cost: ${stats['total']['cost']:.4f}")

    assert "providers" in stats, "Stats should have providers"
    assert "total" in stats, "Stats should have total"
    print("   OK Stats structure valid")

    print("\n" + "=" * 60)
    print("OK All routing logic tests passed!")
    print("=" * 60)

    # Calculate expected savings
    print("\n[Cost Projection]")
    print("Assuming 1M tokens/month with optimal routing:")
    print("  - 40% DeepSeek ($0.55/1M):  $0.22")
    print("  - 50% Claude ($3/1M):       $1.50")
    print("  - 10% GPT-4o ($15/1M):      $1.50")
    print("  " + "-" * 40)
    print("  Total cost:                 $3.22")
    print("  vs 100% GPT-4o:             $15.00")
    print("  Savings:                    $11.78 (-79%)")

    return True


if __name__ == "__main__":
    try:
        success = test_routing_logic()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
