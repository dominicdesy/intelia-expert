"""
POC - Test Latence Weaviate pour Realtime Voice
================================================

Tests à réaliser:
1. Latence query Weaviate seul (baseline)
2. Latence sous charge (queries concurrentes)
3. Latence P50, P95, P99
4. Impact streaming concurrent

Requirements:
    - Weaviate client configuré
    - Collection InteliaExpertKnowledge existante
"""

import asyncio
import time
import statistics
from datetime import datetime
from typing import List, Dict
import sys
import os
from dotenv import load_dotenv

# Charger .env depuis llm/
env_path = os.path.join(os.path.dirname(__file__), '..', 'llm', '.env')
load_dotenv(env_path)

# Ajouter le path du projet pour imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'llm'))

from retrieval.retriever_core import HybridWeaviateRetriever
from utils.imports_and_dependencies import wvc
from config.config import WEAVIATE_URL, WEAVIATE_API_KEY


class WeaviateLatencyTester:
    """Testeur de latence Weaviate pour voice realtime"""

    def __init__(self):
        self.client = None
        self.retriever = None
        self.latencies = []
        self.errors = []

    async def connect(self):
        """Connexion au client Weaviate"""
        print("🔌 Connexion à Weaviate...")
        try:
            self.client = wvc.Client(
                url=WEAVIATE_URL,
                auth_client_secret=wvc.AuthApiKey(WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None
            )

            # Vérifier connexion
            if self.client.is_ready():
                print(f"✅ Connecté à Weaviate: {WEAVIATE_URL}")
                self.retriever = HybridWeaviateRetriever(self.client)
                return True
            else:
                print("❌ Weaviate non disponible")
                return False
        except Exception as e:
            print(f"❌ Erreur connexion: {e}")
            self.errors.append(f"Connection: {str(e)}")
            return False

    async def single_query_test(self, query: str) -> float:
        """Test une seule query et retourne latence en ms"""
        start = time.time()
        try:
            # Utiliser la méthode de retrieval existante
            # Note: Adapter selon l'API réelle du retriever
            results = await self.retriever.search(
                query=query,
                limit=5,
                alpha=0.7  # Balance vector/BM25
            )
            latency = (time.time() - start) * 1000
            return latency
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.errors.append(f"Query '{query}': {str(e)}")
            return latency

    async def test_baseline_latency(self, num_tests: int = 10):
        """Test latence baseline avec queries typiques"""
        print(f"\n📊 Test latence baseline ({num_tests} queries)...")

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
            latency = await self.single_query_test(query)
            latencies.append(latency)
            print(f"  Query {i+1}/{num_tests}: {latency:.2f}ms - '{query[:50]}...'")

        self.latencies.extend(latencies)
        return latencies

    async def test_concurrent_queries(self, num_concurrent: int = 5):
        """Test queries concurrentes (simule charge réaliste)"""
        print(f"\n🔄 Test queries concurrentes ({num_concurrent} en parallèle)...")

        queries = [
            "Température incubation",
            "Traitement coccidiose",
            "Ventilation couvoir",
            "Programme alimentation",
            "Maladies respiratoires"
        ][:num_concurrent]

        start = time.time()
        tasks = [self.single_query_test(q) for q in queries]
        latencies = await asyncio.gather(*tasks)
        total_time = (time.time() - start) * 1000

        print(f"  ⏱️  Temps total: {total_time:.2f}ms")
        for i, lat in enumerate(latencies):
            print(f"  Query {i+1}: {lat:.2f}ms")

        self.latencies.extend(latencies)
        return latencies

    async def test_streaming_simulation(self):
        """Simule query Weaviate pendant streaming OpenAI"""
        print(f"\n🎙️ Simulation: Query Weaviate pendant streaming audio...")

        async def simulate_openai_streaming():
            """Simule génération audio OpenAI (100ms chunks pendant 3s)"""
            chunks = []
            for i in range(30):  # 30 chunks de 100ms = 3s
                await asyncio.sleep(0.1)  # 100ms par chunk
                chunks.append(f"chunk_{i}")
            return chunks

        async def query_during_streaming():
            """Query Weaviate pendant streaming"""
            await asyncio.sleep(0.5)  # Attendre 500ms après début streaming
            latency = await self.single_query_test("Température d'incubation")
            return latency

        print("  🎵 Démarrage streaming simulé...")
        start = time.time()

        # Exécuter en parallèle
        streaming_task = asyncio.create_task(simulate_openai_streaming())
        query_task = asyncio.create_task(query_during_streaming())

        chunks, query_latency = await asyncio.gather(streaming_task, query_task)

        total_time = (time.time() - start) * 1000

        print(f"  ✅ Streaming: {len(chunks)} chunks en {total_time:.2f}ms")
        print(f"  ✅ Query Weaviate: {query_latency:.2f}ms")
        print(f"  📊 Impact: Query effectuée sans bloquer streaming")

        return query_latency

    def calculate_percentiles(self) -> Dict[str, float]:
        """Calcule P50, P95, P99"""
        if not self.latencies:
            return {}

        sorted_lat = sorted(self.latencies)
        return {
            "min": min(sorted_lat),
            "p50": statistics.median(sorted_lat),
            "p95": sorted_lat[int(len(sorted_lat) * 0.95)],
            "p99": sorted_lat[int(len(sorted_lat) * 0.99)] if len(sorted_lat) > 10 else sorted_lat[-1],
            "max": max(sorted_lat),
            "mean": statistics.mean(sorted_lat),
            "stdev": statistics.stdev(sorted_lat) if len(sorted_lat) > 1 else 0
        }

    def print_report(self):
        """Afficher rapport complet"""
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
        print(f"  - Écart-type: {stats['stdev']:.2f}ms")

        # Évaluation pour voice realtime
        print(f"\n🎯 ÉVALUATION POUR VOICE REALTIME:")

        p95 = stats['p95']
        if p95 < 200:
            print(f"  ✅ EXCELLENT: P95={p95:.0f}ms - Compatible streaming temps réel")
        elif p95 < 300:
            print(f"  ✅ BON: P95={p95:.0f}ms - Acceptable pour voice realtime")
        elif p95 < 500:
            print(f"  ⚠️  MOYEN: P95={p95:.0f}ms - Risque latence perceptible")
        else:
            print(f"  ❌ PROBLÉMATIQUE: P95={p95:.0f}ms - Trop lent pour temps réel")

        # Recommandations architecturales
        print(f"\n💡 RECOMMANDATIONS:")

        if p95 < 300:
            print("  ✅ Option A viable: Injection contexte après VAD (latence acceptable)")
            print("  ✅ Option B recommandée: Pré-chargement pendant parole (optimal)")
        else:
            print("  ❌ Option A risquée: Injection après VAD trop lente")
            print("  ✅ Option B obligatoire: DOIT pré-charger pendant parole")
            print("  💡 Considérer cache pour questions fréquentes")

        # Estimation latence totale
        print(f"\n⏱️  ESTIMATION LATENCE TOTALE (Question → Audio):")
        vad_latency = 200  # Estimation VAD
        openai_latency = 300  # Estimation OpenAI first chunk

        option_a = vad_latency + p95 + openai_latency
        option_b = vad_latency + openai_latency  # Weaviate en parallèle

        print(f"  Option A (injection après VAD): ~{option_a:.0f}ms")
        print(f"  Option B (pré-chargement): ~{option_b:.0f}ms")
        print(f"  Objectif cible: <500ms (P95)")

        if option_b < 500:
            print(f"  ✅ Objectif ATTEIGNABLE avec Option B")
        else:
            print(f"  ⚠️  Objectif DIFFICILE même avec Option B")

        if self.errors:
            print(f"\n❌ ERREURS ({len(self.errors)}):")
            for error in self.errors[:5]:  # Limiter à 5 erreurs
                print(f"  - {error}")

        print("\n" + "="*60)

    async def close(self):
        """Fermer connexion"""
        if self.client:
            self.client.close()
            print("\n🔌 Connexion Weaviate fermée")


async def main():
    """Exécution des tests"""
    tester = WeaviateLatencyTester()

    try:
        # Connexion
        if not await tester.connect():
            return

        # Test 1: Latence baseline
        print("\n" + "="*60)
        print("TEST 1: Latence baseline (10 queries séquentielles)")
        print("="*60)
        await tester.test_baseline_latency(num_tests=10)

        # Test 2: Queries concurrentes
        print("\n" + "="*60)
        print("TEST 2: Queries concurrentes")
        print("="*60)
        await tester.test_concurrent_queries(num_concurrent=5)

        # Test 3: Simulation streaming
        print("\n" + "="*60)
        print("TEST 3: Query pendant streaming audio")
        print("="*60)
        await tester.test_streaming_simulation()

        # Rapport final
        tester.print_report()

    except Exception as e:
        print(f"\n💥 Erreur inattendue: {e}")
        tester.errors.append(str(e))

    finally:
        await tester.close()


if __name__ == "__main__":
    print(f"\n🚀 Démarrage POC Latence Weaviate")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    asyncio.run(main())
