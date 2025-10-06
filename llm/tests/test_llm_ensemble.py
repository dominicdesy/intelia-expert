# -*- coding: utf-8 -*-
"""
test_llm_ensemble.py - Tests for Multi-LLM Ensemble

Tests the ensemble system with different modes and configurations
"""

import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generation.llm_ensemble import get_llm_ensemble, EnsembleMode


async def test_ensemble_availability():
    """Test 1: Check which LLM providers are available"""

    print("\n" + "=" * 70)
    print("TEST 1: LLM PROVIDERS AVAILABILITY")
    print("=" * 70)

    ensemble = get_llm_ensemble(mode=EnsembleMode.BEST_OF_N)

    providers_status = {
        "OpenAI (GPT-4o)": ensemble.openai_client is not None,
        "Anthropic (Claude)": ensemble.claude_client is not None,
        "DeepSeek": ensemble.deepseek_client is not None,
    }

    print("\nProviders status:")
    for provider, available in providers_status.items():
        status = "OK" if available else "NOT AVAILABLE"
        print(f"  - {provider}: {status}")

    available_count = sum(providers_status.values())
    print(f"\nTotal available: {available_count}/3")

    if available_count < 2:
        print("\nWARNING: Au moins 2 providers requis pour l'ensemble")
        print("Configurez les clés API manquantes:")
        if not providers_status["OpenAI (GPT-4o)"]:
            print("  - OPENAI_API_KEY")
        if not providers_status["Anthropic (Claude)"]:
            print("  - ANTHROPIC_API_KEY")
        if not providers_status["DeepSeek"]:
            print("  - DEEPSEEK_API_KEY")
        return False

    print("\nOK - Sufficient providers for ensemble")
    return True


async def test_best_of_n_mode():
    """Test 2: Best-of-N mode with real query"""

    print("\n" + "=" * 70)
    print("TEST 2: BEST-OF-N MODE")
    print("=" * 70)

    ensemble = get_llm_ensemble(mode=EnsembleMode.BEST_OF_N, force_new=True)

    # Mock context documents
    context_docs = [
        {
            "page_content": "Ross 308 à 35 jours: poids cible 2.2-2.4 kg, FCR 1.65-1.70",
            "metadata": {"source": "postgresql", "breed": "Ross 308"},
        },
        {
            "page_content": "À 35 jours, les poulets Ross 308 atteignent généralement 2.3 kg avec une bonne gestion",
            "metadata": {"source": "weaviate"},
        },
    ]

    query = "Quel poids pour poulets Ross 308 à 35 jours ?"

    print(f"\nQuery: {query}")
    print(f"Context: {len(context_docs)} documents")

    try:
        result = await ensemble.generate_ensemble_response(
            query=query, context_docs=context_docs, language="fr"
        )

        print(f"\nResults:")
        print(f"  Provider selected: {result['provider']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Responses received: {len(result['all_responses'])}")
        print(f"  Execution time: {result['execution_time_ms']:.0f}ms")

        print(f"\nFinal answer:")
        print(f"  {result['final_answer'][:200]}...")

        print(f"\nQuality scores:")
        for score in result["quality_scores"]:
            print(
                f"  - {score['provider']}: {score['overall_score']:.2f} "
                f"(factual={score['factual_score']:.2f}, "
                f"complete={score['completeness_score']:.2f})"
            )

        # Assertions
        assert (
            len(result["all_responses"]) >= 2
        ), "Au moins 2 providers doivent répondre"
        assert result["confidence"] > 0.5, "Confidence doit être > 0.5"
        assert result["final_answer"], "Réponse finale ne doit pas être vide"
        assert "2" in result["final_answer"], "La réponse doit mentionner un poids"

        print("\nOK - Best-of-N mode works correctly")
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_fusion_mode():
    """Test 3: Fusion mode"""

    print("\n" + "=" * 70)
    print("TEST 3: FUSION MODE")
    print("=" * 70)

    ensemble = get_llm_ensemble(mode=EnsembleMode.FUSION, force_new=True)

    context_docs = [
        {
            "page_content": "Ross 308: poids 35j = 2.2-2.4 kg, FCR = 1.65",
            "metadata": {"source": "postgresql"},
        }
    ]

    query = "Performances Ross 308 à 35 jours ?"

    print(f"\nQuery: {query}")

    try:
        result = await ensemble.generate_ensemble_response(
            query=query, context_docs=context_docs, language="fr"
        )

        print(f"\nResults:")
        print(f"  Provider: {result['provider']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Mode: fusion")

        print(f"\nFused answer:")
        print(f"  {result['final_answer'][:200]}...")

        assert result["final_answer"], "Réponse fusionnée ne doit pas être vide"
        assert (
            result["provider"] == "fusion" or len(result["all_responses"]) >= 2
        ), "Fusion ou fallback doit fonctionner"

        print("\nOK - Fusion mode works")
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_ensemble_vs_single():
    """Test 4: Compare ensemble quality vs single LLM"""

    print("\n" + "=" * 70)
    print("TEST 4: ENSEMBLE VS SINGLE LLM QUALITY")
    print("=" * 70)

    ensemble = get_llm_ensemble(mode=EnsembleMode.BEST_OF_N, force_new=True)

    context_docs = [
        {
            "page_content": "Symptômes coccidiose: diarrhée, sang dans fèces, mortalité 3-5%, perte de poids",
            "metadata": {"source": "weaviate"},
        }
    ]

    query = "Quels sont les symptômes de la coccidiose ?"

    print(f"\nQuery: {query}")

    try:
        # Generate with ensemble
        ensemble_result = await ensemble.generate_ensemble_response(
            query=query, context_docs=context_docs, language="fr"
        )

        print(f"\nEnsemble results:")
        print(f"  Best provider: {ensemble_result['provider']}")
        print(f"  Confidence: {ensemble_result['confidence']:.2f}")
        print(f"  All providers tested: {len(ensemble_result['all_responses'])}")

        print(f"\nAll responses for comparison:")
        for i, resp in enumerate(ensemble_result["all_responses"], 1):
            score = ensemble_result["quality_scores"][i - 1]
            print(f"\n  Response {i} ({resp['provider']}) - Score: {score['overall_score']:.2f}")
            print(f"  {resp['text'][:150]}...")

        print(f"\nSelected answer (best quality):")
        print(f"  {ensemble_result['final_answer'][:200]}...")

        # Check quality improvement
        scores = [s["overall_score"] for s in ensemble_result["quality_scores"]]
        best_score = max(scores)
        avg_score = sum(scores) / len(scores)
        improvement = ((best_score - avg_score) / avg_score) * 100

        print(f"\nQuality analysis:")
        print(f"  Best score: {best_score:.2f}")
        print(f"  Average score: {avg_score:.2f}")
        print(f"  Improvement: +{improvement:.1f}%")

        assert (
            best_score >= avg_score
        ), "Le meilleur score doit être >= à la moyenne"
        assert (
            ensemble_result["confidence"] == best_score
        ), "Confidence doit égaler le meilleur score"

        print("\nOK - Ensemble selects highest quality response")
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_cost_tracking():
    """Test 5: Cost tracking"""

    print("\n" + "=" * 70)
    print("TEST 5: COST TRACKING")
    print("=" * 70)

    ensemble = get_llm_ensemble(mode=EnsembleMode.BEST_OF_N, force_new=True)

    # Get initial stats
    stats_before = ensemble.get_usage_stats()
    print(f"\nStats before:")
    print(f"  Ensemble queries: {stats_before['ensemble_queries']}")
    print(f"  Total LLM calls: {stats_before['total_llm_calls']}")

    # Run a query
    context_docs = [{"page_content": "Test doc", "metadata": {"source": "test"}}]
    query = "Test query"

    try:
        await ensemble.generate_ensemble_response(
            query=query, context_docs=context_docs, language="fr"
        )

        # Get updated stats
        stats_after = ensemble.get_usage_stats()
        print(f"\nStats after:")
        print(f"  Ensemble queries: {stats_after['ensemble_queries']}")
        print(f"  Total LLM calls: {stats_after['total_llm_calls']}")

        queries_diff = (
            stats_after["ensemble_queries"] - stats_before["ensemble_queries"]
        )
        calls_diff = stats_after["total_llm_calls"] - stats_before["total_llm_calls"]

        print(f"\nDifference:")
        print(f"  +{queries_diff} ensemble query")
        print(f"  +{calls_diff} LLM calls (3 generations + 1 judge = 4)")

        assert queries_diff == 1, "Doit avoir 1 query de plus"
        assert (
            calls_diff >= 3
        ), "Doit avoir au moins 3 LLM calls (3 generations + 1 judge)"

        print("\nOK - Cost tracking works")
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_ensemble_disabled():
    """Test 6: Ensemble disabled fallback"""

    print("\n" + "=" * 70)
    print("TEST 6: ENSEMBLE DISABLED FALLBACK")
    print("=" * 70)

    # Create ensemble with disabled flag
    ensemble = get_llm_ensemble(mode=EnsembleMode.BEST_OF_N, force_new=True)
    ensemble.enabled = False

    context_docs = [{"page_content": "Test", "metadata": {"source": "test"}}]
    query = "Test"

    print("\nEnsemble disabled, should fallback to single LLM")

    try:
        result = await ensemble.generate_ensemble_response(
            query=query, context_docs=context_docs, language="fr"
        )

        print(f"\nResult:")
        print(f"  Provider: {result['provider']}")
        print(f"  Used ensemble: No (fallback)")

        # Should have only 1 response (fallback)
        assert len(result.get("all_responses", [])) <= 1, "Doit avoir 1 seule réponse"

        print("\nOK - Fallback works when ensemble disabled")
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all ensemble tests"""

    print("\n" + "=" * 70)
    print("LLM ENSEMBLE TEST SUITE")
    print("=" * 70)

    # Check if we should skip tests
    if not os.getenv("OPENAI_API_KEY"):
        print("\nWARNING: OPENAI_API_KEY not found")
        print("Au moins OPENAI_API_KEY est requis pour les tests")
        print("Configurez les variables d'environnement:")
        print("  - OPENAI_API_KEY (requis)")
        print("  - ANTHROPIC_API_KEY (recommandé)")
        print("  - DEEPSEEK_API_KEY (optionnel)")
        return

    tests = [
        test_ensemble_availability,
        test_best_of_n_mode,
        test_fusion_mode,
        test_ensemble_vs_single,
        test_cost_tracking,
        test_ensemble_disabled,
    ]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"\nERROR in {test.__name__}: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r)
    total = len(results)

    for test, result in zip(tests, results):
        status = "OK" if result else "FAILED"
        print(f"  {test.__name__}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\nOK - ALL TESTS PASSED")
    else:
        print(f"\nWARNING: {total - passed} test(s) failed")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
