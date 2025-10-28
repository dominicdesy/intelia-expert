#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_embedding_quality.py - Test qualité embeddings

Compare la qualité des embeddings entre différents modèles OpenAI:
- text-embedding-ada-002 (ancien, baseline)
- text-embedding-3-small
- text-embedding-3-large (nouveau)

Mesure la similarité cosinus entre queries et documents de référence
pour démontrer l'amélioration du recall.

Usage:
    python scripts/test_embedding_quality.py [--models MODEL1,MODEL2] [--dimensions DIM]

Options:
    --models      Liste de modèles à comparer (défaut: ada-002,3-large)
    --dimensions  Dimensions pour text-embedding-3-* (défaut: 1536)
    --lang        Langue de test (fr, en, both - défaut: both)
"""

import asyncio
import os
import sys
import argparse
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple

# Ajouter le répertoire parent au path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports après path setup
from utils.imports_and_dependencies import AsyncOpenAI

# Configuration logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class EmbeddingQualityTester:
    """Testeur de qualité des embeddings"""

    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions
        self.openai_client = None

        # Test queries multilingues
        self.test_cases = {
            "fr": [
                {
                    "reference": (
                        "À 35 jours d'âge, les poulets mâles Ross 308 ont un poids corporel "
                        "moyen de 2190 grammes avec un indice de conversion alimentaire de 1.52. "
                        "Les femelles pèsent 1920 grammes avec un IC de 1.58."
                    ),
                    "queries": [
                        "Poids Ross 308 35 jours",
                        "Quel est le poids cible poulets Ross 308 à 35 jours",
                        "Combien pèsent les Ross 308 mâles à 5 semaines",
                        "IC Ross 308 jour 35",
                    ],
                },
                {
                    "reference": (
                        "La température optimale dans un poulailler pour jeunes poussins est de "
                        "32-34°C la première semaine, puis diminue de 2-3°C par semaine jusqu'à "
                        "atteindre 20-22°C à l'âge adulte. L'humidité doit être maintenue entre 50-70%."
                    ),
                    "queries": [
                        "Température poulailler poussins",
                        "Quelle température pour les jeunes poulets",
                        "Chaleur nécessaire première semaine poussins",
                    ],
                },
                {
                    "reference": (
                        "Les vaccins essentiels en aviculture incluent Marek (1er jour), "
                        "Newcastle et Gumboro (7-14 jours), et Influenza aviaire selon la région. "
                        "Le respect du calendrier vaccinal est critique pour prévenir les épidémies."
                    ),
                    "queries": [
                        "Vaccins poulets obligatoires",
                        "Programme vaccination avicole",
                        "Quand vacciner contre Newcastle",
                    ],
                },
            ],
            "en": [
                {
                    "reference": (
                        "At 35 days of age, Ross 308 male chickens have an average body weight "
                        "of 2190 grams with a feed conversion ratio of 1.52. "
                        "Females weigh 1920 grams with FCR of 1.58."
                    ),
                    "queries": [
                        "Ross 308 weight 35 days",
                        "What is the target weight Ross 308 chickens at 35 days",
                        "How much do Ross 308 males weigh at 5 weeks",
                        "FCR Ross 308 day 35",
                    ],
                },
                {
                    "reference": (
                        "The optimal temperature in a chicken house for young chicks is "
                        "32-34°C in the first week, then decreases by 2-3°C per week until "
                        "reaching 20-22°C at adult age. Humidity should be maintained at 50-70%."
                    ),
                    "queries": [
                        "Temperature chicken house chicks",
                        "What temperature for young chickens",
                        "Heat needed first week chicks",
                    ],
                },
            ],
        }

    async def initialize(self):
        """Initialise le client OpenAI"""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY non configurée")

        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        logger.info("✅ Client OpenAI initialisé\n")

    async def get_embedding(
        self, text: str, model: str, dimensions: int = None
    ) -> List[float]:
        """Génère un embedding pour un texte"""
        try:
            # Préparer paramètres
            params = {"model": model, "input": text, "encoding_format": "float"}

            # Ajouter dimensions pour text-embedding-3-*
            if "text-embedding-3" in model and dimensions:
                params["dimensions"] = dimensions

            response = await self.openai_client.embeddings.create(**params)

            if not response or not response.data:
                logger.error(f"❌ Réponse vide pour modèle {model}")
                return []

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"❌ Erreur embedding {model}: {e}")
            return []

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calcule similarité cosinus entre deux vecteurs"""
        if not vec1 or not vec2:
            return 0.0

        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)

        # Similarité cosinus
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def test_model(
        self, model: str, language: str, dimensions: int = None
    ) -> Dict[str, float]:
        """Teste un modèle sur un ensemble de queries"""
        results = {
            "model": model,
            "language": language,
            "dimensions": dimensions if "text-embedding-3" in model else "default",
            "test_cases": [],
        }

        test_cases = self.test_cases.get(language, [])

        for i, test_case in enumerate(test_cases, 1):
            reference = test_case["reference"]
            queries = test_case["queries"]

            # Générer embedding référence
            ref_embedding = await self.get_embedding(reference, model, dimensions)
            if not ref_embedding:
                logger.error(f"❌ Échec embedding référence (test case {i})")
                continue

            # Tester chaque query
            case_results = {"reference_preview": reference[:100] + "...", "queries": []}

            for query in queries:
                query_embedding = await self.get_embedding(query, model, dimensions)
                if not query_embedding:
                    logger.error(f"❌ Échec embedding query: {query}")
                    continue

                # Calculer similarité
                similarity = self.cosine_similarity(ref_embedding, query_embedding)

                case_results["queries"].append(
                    {"query": query, "similarity": similarity}
                )

            results["test_cases"].append(case_results)

        return results

    def calculate_metrics(self, results: Dict) -> Tuple[float, float, float]:
        """Calcule métriques globales"""
        all_similarities = []

        for test_case in results["test_cases"]:
            for query_result in test_case["queries"]:
                all_similarities.append(query_result["similarity"])

        if not all_similarities:
            return 0.0, 0.0, 0.0

        avg_similarity = np.mean(all_similarities)
        min_similarity = np.min(all_similarities)
        max_similarity = np.max(all_similarities)

        return avg_similarity, min_similarity, max_similarity

    def print_results(self, all_results: List[Dict]):
        """Affiche résultats formatés"""
        logger.info("=" * 90)
        logger.info("📊 RÉSULTATS TEST QUALITÉ EMBEDDINGS")
        logger.info("=" * 90)

        # Grouper par langue
        results_by_lang = {}
        for result in all_results:
            lang = result["language"]
            if lang not in results_by_lang:
                results_by_lang[lang] = []
            results_by_lang[lang].append(result)

        # Afficher par langue
        for lang, lang_results in results_by_lang.items():
            logger.info(f"\n🌍 Langue: {lang.upper()}")
            logger.info("-" * 90)

            # Tableau comparatif
            logger.info(
                f"\n{'Modèle':<35} {'Dimensions':<12} {'Avg Sim':<12} {'Min':<10} {'Max':<10}"
            )
            logger.info("-" * 90)

            baseline_avg = None
            baseline_model = None

            for result in lang_results:
                model = result["model"]
                dims = result["dimensions"]
                avg_sim, min_sim, max_sim = self.calculate_metrics(result)

                # Stocker baseline (premier modèle)
                if baseline_avg is None:
                    baseline_avg = avg_sim
                    baseline_model = model

                # Calculer amélioration
                improvement = ""
                if baseline_avg and baseline_avg > 0 and model != baseline_model:
                    improvement_pct = ((avg_sim - baseline_avg) / baseline_avg) * 100
                    improvement = f" ({improvement_pct:+.1f}%)"

                logger.info(
                    f"{model:<35} {str(dims):<12} "
                    f"{avg_sim:.4f}{improvement:<12} "
                    f"{min_sim:.4f}    {max_sim:.4f}"
                )

            # Détails par test case
            logger.info(f"\n📋 Détails par test case ({lang}):")
            logger.info("-" * 90)

            for model_result in lang_results:
                model = model_result["model"]
                logger.info(f"\n  Model: {model}")

                for i, test_case in enumerate(model_result["test_cases"], 1):
                    logger.info(f"  Test case {i}: {test_case['reference_preview']}")

                    for query_result in test_case["queries"]:
                        query = query_result["query"]
                        sim = query_result["similarity"]
                        logger.info(f'    • "{query[:60]}...": {sim:.4f}')

        logger.info("\n" + "=" * 90)

        # Recommandation
        logger.info("\n💡 RECOMMANDATION:")

        # Trouver meilleur modèle (avg similarity max)
        best_model = None
        best_avg = 0.0

        for result in all_results:
            avg_sim, _, _ = self.calculate_metrics(result)
            if avg_sim > best_avg:
                best_avg = avg_sim
                best_model = result

        if best_model:
            logger.info(f"  ⭐ Meilleur modèle: {best_model['model']}")
            logger.info(f"     Dimensions: {best_model['dimensions']}")
            logger.info(f"     Similarité moyenne: {best_avg:.4f}")

            # Calculer amélioration vs baseline
            if baseline_avg and baseline_avg > 0:
                improvement_pct = ((best_avg - baseline_avg) / baseline_avg) * 100
                logger.info(
                    f"     Amélioration vs {baseline_model}: {improvement_pct:+.1f}%"
                )

                if improvement_pct >= 5:
                    logger.info(
                        f"\n  ✅ Migration RECOMMANDÉE: amélioration significative (+{improvement_pct:.1f}%)"
                    )
                elif improvement_pct >= 2:
                    logger.info(
                        f"\n  ⚠️ Migration OPTIONNELLE: amélioration modérée (+{improvement_pct:.1f}%)"
                    )
                else:
                    logger.info(
                        f"\n  ❌ Migration NON RECOMMANDÉE: amélioration négligeable (+{improvement_pct:.1f}%)"
                    )

        logger.info("\n" + "=" * 90)

    async def run_tests(self, models: List[str], languages: List[str]):
        """Lance les tests pour tous les modèles et langues"""
        all_results = []

        logger.info("🚀 Lancement tests qualité embeddings...\n")

        for model in models:
            for language in languages:
                logger.info(f"📝 Test {model} ({language})...")

                # Déterminer dimensions
                dims = None
                if "text-embedding-3" in model:
                    dims = self.dimensions

                # Tester
                result = await self.test_model(model, language, dims)
                all_results.append(result)

                # Pause pour éviter rate limiting
                await asyncio.sleep(1)

        # Afficher résultats
        self.print_results(all_results)

    async def close(self):
        """Fermeture propre"""
        if self.openai_client:
            try:
                await self.openai_client.close()
            except Exception as e:
                logger.warning(f"⚠️ Erreur fermeture OpenAI: {e}")


async def main():
    """Point d'entrée principal"""
    # Parser arguments
    parser = argparse.ArgumentParser(description="Tester qualité embeddings OpenAI")
    parser.add_argument(
        "--models",
        type=str,
        default="text-embedding-ada-002,text-embedding-3-large",
        help="Liste de modèles à comparer (séparés par virgule)",
    )
    parser.add_argument(
        "--dimensions",
        type=int,
        default=1536,
        choices=[1536, 3072],
        help="Dimensions pour text-embedding-3-* (défaut: 1536)",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="both",
        choices=["fr", "en", "both"],
        help="Langue de test (fr, en, both - défaut: both)",
    )

    args = parser.parse_args()

    # Parser modèles
    models = [m.strip() for m in args.models.split(",")]

    # Parser langues
    if args.lang == "both":
        languages = ["fr", "en"]
    else:
        languages = [args.lang]

    # Vérifier OPENAI_API_KEY
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY non configurée")
        sys.exit(1)

    # Créer tester
    tester = EmbeddingQualityTester(dimensions=args.dimensions)

    try:
        # Initialiser
        await tester.initialize()

        # Lancer tests
        await tester.run_tests(models, languages)

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Tests interrompus par l'utilisateur")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup
        await tester.close()


if __name__ == "__main__":
    # Compatibilité Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
