"""
Test de Charge - Intelia LLM Service

Ce script teste la capacité du service LLM à gérer plusieurs requêtes simultanées.
Il simule plusieurs utilisateurs envoyant des requêtes en parallèle.
"""

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict
import json


# Queries de test variées pour simuler des utilisateurs réels
TEST_QUERIES = [
    {"query": "What is the FCR of Ross 308?", "language": "en"},
    {"query": "Quel est le poids de Cobb 500 à 35 jours?", "language": "fr"},
    {"query": "What is the ideal temperature for broilers?", "language": "en"},
    {"query": "Comment améliorer le GMQ?", "language": "fr"},
    {"query": "What is the average weight of Ross 308 at 21 days?", "language": "en"},
    {"query": "Quelle est la différence entre brooding et rearing?", "language": "fr"},
    {"query": "How to reduce mortality in broiler chickens?", "language": "en"},
    {"query": "Quel est le taux de conversion alimentaire optimal?", "language": "fr"},
    {"query": "What vaccinations are needed for day-old chicks?", "language": "en"},
    {"query": "Comment contrôler la température dans le poulailler?", "language": "fr"},
]


async def make_request(
    session: aiohttp.ClientSession, query: str, language: str, request_id: int
) -> Dict:
    """
    Envoie une requête au service LLM et mesure le temps de réponse
    """
    start_time = time.time()

    try:
        async with session.post(
            "http://localhost:8081/v1/generate",
            json={
                "query": query,
                "domain": "aviculture",
                "language": language,
                "session_id": f"load_test_{request_id}",
            },
            timeout=aiohttp.ClientTimeout(total=60),
        ) as response:
            latency = time.time() - start_time

            if response.status == 200:
                data = await response.json()
                return {
                    "request_id": request_id,
                    "status": "success",
                    "latency_ms": int(latency * 1000),
                    "cached": data.get("cached", False),
                    "tokens": data.get("total_tokens", 0),
                    "query": query[:50],
                    "language": language,
                }
            else:
                return {
                    "request_id": request_id,
                    "status": "error",
                    "latency_ms": int(latency * 1000),
                    "error": f"HTTP {response.status}",
                }

    except asyncio.TimeoutError:
        latency = time.time() - start_time
        return {
            "request_id": request_id,
            "status": "timeout",
            "latency_ms": int(latency * 1000),
            "error": "Request timeout (>60s)",
        }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "request_id": request_id,
            "status": "error",
            "latency_ms": int(latency * 1000),
            "error": str(e),
        }


async def run_load_test(num_requests: int) -> List[Dict]:
    """
    Exécute un test de charge avec un nombre donné de requêtes simultanées
    """
    print(f"\n{'='*70}")
    print(f"TEST DE CHARGE: {num_requests} requêtes simultanées")
    print(f"{'='*70}\n")

    # Créer les tâches (cycle à travers les queries de test)
    tasks = []
    async with aiohttp.ClientSession() as session:
        for i in range(num_requests):
            query_data = TEST_QUERIES[i % len(TEST_QUERIES)]
            task = make_request(
                session, query_data["query"], query_data["language"], i + 1
            )
            tasks.append(task)

        # Lancer toutes les requêtes en parallèle
        print(f"[START] Lancement de {num_requests} requêtes simultanées...")
        start_time = time.time()

        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time
        print(f"[DONE] Toutes les requêtes terminées en {total_time:.2f}s\n")

    return results


def analyze_results(results: List[Dict]) -> None:
    """
    Analyse et affiche les statistiques des résultats
    """
    print(f"\n{'='*70}")
    print("ANALYSE DES RÉSULTATS")
    print(f"{'='*70}\n")

    # Séparer succès et erreurs
    successes = [r for r in results if r["status"] == "success"]
    errors = [r for r in results if r["status"] != "success"]

    # Statistiques globales
    print(f"Total requêtes:       {len(results)}")
    print(
        f"Succès:               {len(successes)} ({len(successes)/len(results)*100:.1f}%)"
    )
    print(f"Erreurs:              {len(errors)} ({len(errors)/len(results)*100:.1f}%)")

    if successes:
        latencies = [r["latency_ms"] for r in successes]
        cache_hits = [r for r in successes if r["cached"]]
        cache_misses = [r for r in successes if not r["cached"]]

        print("\n--- Latence ---")
        print(f"Moyenne:              {statistics.mean(latencies):.0f}ms")
        print(f"Médiane:              {statistics.median(latencies):.0f}ms")
        print(f"Min:                  {min(latencies)}ms")
        print(f"Max:                  {max(latencies)}ms")
        print(
            f"Écart-type:           {statistics.stdev(latencies):.0f}ms"
            if len(latencies) > 1
            else "N/A"
        )

        print("\n--- Cache ---")
        print(
            f"Cache Hits:           {len(cache_hits)} ({len(cache_hits)/len(successes)*100:.1f}%)"
        )
        print(
            f"Cache Misses:         {len(cache_misses)} ({len(cache_misses)/len(successes)*100:.1f}%)"
        )

        if cache_hits:
            cache_hit_latencies = [r["latency_ms"] for r in cache_hits]
            print(
                f"Latence moyenne (hit): {statistics.mean(cache_hit_latencies):.0f}ms"
            )

        if cache_misses:
            cache_miss_latencies = [r["latency_ms"] for r in cache_misses]
            print(
                f"Latence moyenne (miss): {statistics.mean(cache_miss_latencies):.0f}ms"
            )

        print("\n--- Tokens ---")
        total_tokens = sum(r["tokens"] for r in successes)
        print(f"Total tokens:         {total_tokens}")
        print(f"Moyenne par requête:  {total_tokens/len(successes):.0f}")

    if errors:
        print("\n--- Erreurs ---")
        for error in errors:
            print(
                f"Request {error['request_id']}: {error['error']} (latency: {error['latency_ms']}ms)"
            )

    # Top 5 requêtes les plus rapides
    if len(successes) >= 5:
        print("\n--- Top 5 Requêtes les Plus Rapides ---")
        fastest = sorted(successes, key=lambda x: x["latency_ms"])[:5]
        for i, r in enumerate(fastest, 1):
            cache_str = "[CACHE]" if r["cached"] else "[LLM]  "
            print(f"{i}. {r['latency_ms']:5d}ms {cache_str} - {r['query']}")

    # Top 5 requêtes les plus lentes
    if len(successes) >= 5:
        print("\n--- Top 5 Requêtes les Plus Lentes ---")
        slowest = sorted(successes, key=lambda x: x["latency_ms"], reverse=True)[:5]
        for i, r in enumerate(slowest, 1):
            cache_str = "[CACHE]" if r["cached"] else "[LLM]  "
            print(f"{i}. {r['latency_ms']:5d}ms {cache_str} - {r['query']}")

    print(f"\n{'='*70}\n")


async def main():
    """
    Fonction principale - exécute plusieurs tests de charge
    """
    print("\n" + "=" * 70)
    print(" " * 20 + "TEST DE CHARGE - INTELIA LLM")
    print("=" * 70)

    # Test 1: 10 requêtes simultanées
    results_10 = await run_load_test(10)
    analyze_results(results_10)

    # Pause entre les tests
    print("\n[WAIT] Pause de 3 secondes avant le prochain test...\n")
    await asyncio.sleep(3)

    # Test 2: 25 requêtes simultanées
    results_25 = await run_load_test(25)
    analyze_results(results_25)

    # Sauvegarder les résultats
    output_file = "load_test_results.json"
    with open(output_file, "w") as f:
        json.dump(
            {"test_10_requests": results_10, "test_25_requests": results_25},
            f,
            indent=2,
        )

    print(f"[SAVE] Résultats sauvegardés dans: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
