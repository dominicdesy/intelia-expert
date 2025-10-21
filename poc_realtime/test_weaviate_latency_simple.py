"""
POC - Test Latence Weaviate (Version Simplifiée)
=================================================

Test direct sans dépendances au projet llm/
"""

import asyncio
import time
import statistics
import os
from datetime import datetime
from dotenv import load_dotenv
import requests

# Charger .env depuis llm/
env_path = os.path.join(os.path.dirname(__file__), '..', 'llm', '.env')
load_dotenv(env_path)

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

if not WEAVIATE_URL:
    raise ValueError("WEAVIATE_URL not found in .env")

print(f"🔌 Connexion à Weaviate: {WEAVIATE_URL}")


class SimpleWeaviateLatencyTester:
    """Testeur simplifié de latence Weaviate via API REST"""

    def __init__(self):
        self.base_url = WEAVIATE_URL.rstrip('/')
        self.headers = {
            "Content-Type": "application/json",
        }
        if WEAVIATE_API_KEY:
            self.headers["Authorization"] = f"Bearer {WEAVIATE_API_KEY}"

        self.latencies = []
        self.errors = []

    def test_connection(self):
        """Test connexion Weaviate"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/meta",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                print(f"✅ Weaviate accessible")
                return True
            else:
                print(f"❌ Weaviate erreur: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connexion impossible: {e}")
            self.errors.append(str(e))
            return False

    def single_query(self, query_text: str):
        """Effectue une query hybride et mesure latence"""
        start = time.time()

        # Query GraphQL hybride (vector + keyword)
        graphql_query = """
        {
          Get {
            InteliaExpertKnowledge(
              hybrid: {
                query: "%s"
                alpha: 0.7
              }
              limit: 5
            ) {
              content
              _additional {
                distance
              }
            }
          }
        }
        """ % query_text.replace('"', '\\"')

        try:
            response = requests.post(
                f"{self.base_url}/v1/graphql",
                headers=self.headers,
                json={"query": graphql_query},
                timeout=5
            )

            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    self.errors.append(f"GraphQL error: {data['errors']}")
                    return latency

                results = data.get("data", {}).get("Get", {}).get("InteliaExpertKnowledge", [])
                print(f"  ✅ Query OK: {latency:.2f}ms ({len(results)} résultats)")
                return latency
            else:
                self.errors.append(f"HTTP {response.status_code}: {response.text[:100]}")
                return latency

        except Exception as e:
            latency = (time.time() - start) * 1000
            self.errors.append(f"Query error: {str(e)}")
            print(f"  ❌ Erreur: {e}")
            return latency

    def test_baseline_latency(self, num_tests=10):
        """Test latence baseline"""
        print(f"\n📊 Test latence baseline ({num_tests} queries)...\n")

        test_queries = [
            "Quelle est la température d'incubation des œufs de poule ?",
            "Comment traiter la coccidiose ?",
            "Quel est le taux d'humidité optimal en couvoir ?",
            "Paramètres de ventilation en poussinière",
            "Prophylaxie sanitaire en élevage",
            "Densité optimale en bâtiment",
            "Programme d'éclairage pour pondeuses",
            "Aliment démarrage poussin",
            "Détection maladie de Marek",
            "Température corporelle normale poulet"
        ]

        latencies = []
        for i in range(num_tests):
            query = test_queries[i % len(test_queries)]
            print(f"Query {i+1}/{num_tests}: '{query[:40]}...'")
            latency = self.single_query(query)
            latencies.append(latency)
            time.sleep(0.2)  # Petite pause entre queries

        self.latencies.extend(latencies)
        return latencies

    def calculate_percentiles(self):
        """Calcule P50, P95, P99"""
        if not self.latencies:
            return {}

        sorted_lat = sorted(self.latencies)
        return {
            "min": min(sorted_lat),
            "p50": statistics.median(sorted_lat),
            "p95": sorted_lat[int(len(sorted_lat) * 0.95)] if len(sorted_lat) > 1 else sorted_lat[-1],
            "p99": sorted_lat[int(len(sorted_lat) * 0.99)] if len(sorted_lat) > 10 else sorted_lat[-1],
            "max": max(sorted_lat),
            "mean": statistics.mean(sorted_lat),
            "stdev": statistics.stdev(sorted_lat) if len(sorted_lat) > 1 else 0
        }

    def print_report(self):
        """Rapport final"""
        print("\n" + "="*60)
        print("📊 RAPPORT DE TEST - Latence Weaviate")
        print("="*60)

        if not self.latencies:
            print("\n❌ Aucune donnée de latence")
            return

        stats = self.calculate_percentiles()

        print(f"\n📈 STATISTIQUES LATENCE ({len(self.latencies)} queries):")
        print(f"  - Min:    {stats['min']:.2f}ms")
        print(f"  - P50:    {stats['p50']:.2f}ms")
        print(f"  - P95:    {stats['p95']:.2f}ms")
        print(f"  - P99:    {stats['p99']:.2f}ms")
        print(f"  - Max:    {stats['max']:.2f}ms")
        print(f"  - Moyenne: {stats['mean']:.2f}ms")

        # Ajustement pour production (Toronto vs ton PC)
        print(f"\n📍 AJUSTEMENT PRODUCTION (Digital Ocean Toronto):")
        print(f"  - Ton PC → Weaviate Cloud: {stats['p95']:.0f}ms")
        print(f"  - Toronto → Weaviate Cloud: ~{stats['p95'] - 80:.0f}ms (estimation -80ms)")

        p95_prod = stats['p95'] - 80

        print(f"\n🎯 ÉVALUATION POUR VOICE REALTIME:")
        if p95_prod < 200:
            print(f"  ✅ EXCELLENT: P95 prod ~{p95_prod:.0f}ms - Compatible streaming temps réel")
        elif p95_prod < 300:
            print(f"  ✅ BON: P95 prod ~{p95_prod:.0f}ms - Acceptable pour voice realtime")
        elif p95_prod < 500:
            print(f"  ⚠️  MOYEN: P95 prod ~{p95_prod:.0f}ms - Option B obligatoire")
        else:
            print(f"  ❌ PROBLÉMATIQUE: P95 prod ~{p95_prod:.0f}ms - Cache nécessaire")

        # Estimation latence totale
        print(f"\n⏱️  ESTIMATION LATENCE TOTALE (avec Q2: 558ms):")

        openai_latency = 558  # Résultat Q2
        vad_latency = 200

        option_a = vad_latency + p95_prod + openai_latency
        option_b = vad_latency + openai_latency

        print(f"  Option A (injection après VAD): ~{option_a:.0f}ms")
        print(f"  Option B (pré-chargement): ~{option_b:.0f}ms")
        print(f"  Objectif: <800ms")

        if option_b < 800:
            print(f"\n  ✅ Objectif ATTEINT avec Option B ({option_b:.0f}ms < 800ms)")
            print(f"  💡 RECOMMANDATION: Utiliser Option B (pré-chargement pendant parole)")
        else:
            print(f"\n  ⚠️  Objectif DIFFICILE même avec Option B ({option_b:.0f}ms)")

        if self.errors:
            print(f"\n❌ ERREURS ({len(self.errors)}):")
            for error in self.errors[:5]:
                print(f"  - {error}")

        print("\n" + "="*60)


def main():
    """Exécution des tests"""
    tester = SimpleWeaviateLatencyTester()

    # Test connexion
    if not tester.test_connection():
        print("\n❌ Impossible de continuer sans connexion Weaviate")
        return

    # Test baseline
    print("\n" + "="*60)
    print("TEST: Latence baseline (10 queries)")
    print("="*60)
    tester.test_baseline_latency(num_tests=10)

    # Rapport
    tester.print_report()


if __name__ == "__main__":
    print(f"\n🚀 Démarrage POC Latence Weaviate (Version Simplifiée)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    main()
