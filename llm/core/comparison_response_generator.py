# -*- coding: utf-8 -*-
"""
comparison_response_generator.py - Génération de réponses comparatives
VERSION CORRIGÉE : Accès correct à results (Dict vs List)
"""

import logging
from typing import Dict, Any
from .metric_calculator import MetricCalculator

logger = logging.getLogger(__name__)


class ComparisonResponseGenerator:
    """Génère des réponses comparatives enrichies par OpenAI"""

    def __init__(self, postgresql_system=None):
        self.postgresql_system = postgresql_system
        self.calculator = MetricCalculator()

    def _is_higher_better_metric(self, metric_name: str) -> bool:
        """Détermine si une valeur plus élevée est meilleure"""
        metric_name_lower = metric_name.lower()

        higher_better = [
            "weight",
            "poids",
            "production",
            "yield",
            "rendement",
            "growth",
            "croissance",
            "gain",
            "efficiency",
        ]
        lower_better = ["conversion", "fcr", "mortality", "mortalité", "cost", "coût"]

        if any(kw in metric_name_lower for kw in higher_better):
            return True
        elif any(kw in metric_name_lower for kw in lower_better):
            return False
        return True

    async def generate_comparative_response(
        self, query: str, comparison_result: Dict[str, Any], language: str = "fr"
    ) -> str:
        """
        Génère une réponse naturelle pour une comparaison

        CORRECTION: Gère results comme Dict ou List selon le format retourné
        """
        if not comparison_result.get("success"):
            error = comparison_result.get("error", "Unknown error")
            return (
                f"Impossible de comparer: {error}"
                if language == "fr"
                else f"Cannot compare: {error}"
            )

        comparison = comparison_result["comparison"]
        results = comparison_result["results"]
        context = comparison_result.get("context", {})

        # 🔧 CORRECTION: Déterminer le format de results
        metric_name = "métrique"

        logger.debug(f"🔍 Type de results: {type(results)}")
        logger.debug(f"🔍 Contenu de results: {results}")

        # Cas 1: results est un Dict (format de _compare_entities)
        if isinstance(results, dict):
            logger.debug("✅ Format Dict détecté pour results")

            # Extraire metric_name depuis comparison ou context
            metric_name = (
                comparison.metric_name
                or comparison.get("metric_name")
                or context.get("metric_name")
                or "métrique"
            )

        # Cas 2: results est une List (ancien format)
        elif isinstance(results, list) and len(results) > 0:
            logger.debug("✅ Format List détecté pour results")

            first_result = results[0]
            if "data" in first_result and len(first_result["data"]) > 0:
                metric_data = first_result["data"][0]
                metric_name = metric_data.get("metric_name", metric_name)

        else:
            logger.warning(f"⚠️ Format de results inattendu: {type(results)}")

        # Préparer les données pour OpenAI
        comparison_data = {
            "metric_name": metric_name,
            "label1": (
                comparison.label1
                if hasattr(comparison, "label1")
                else comparison.get("entity1")
            ),
            "value1": (
                comparison.value1
                if hasattr(comparison, "value1")
                else comparison.get("value1")
            ),
            "label2": (
                comparison.label2
                if hasattr(comparison, "label2")
                else comparison.get("entity2")
            ),
            "value2": (
                comparison.value2
                if hasattr(comparison, "value2")
                else comparison.get("value2")
            ),
            "difference_absolute": (
                comparison.absolute_difference
                if hasattr(comparison, "absolute_difference")
                else comparison.get("difference")
            ),
            "difference_percent": (
                comparison.relative_difference_pct
                if hasattr(comparison, "relative_difference_pct")
                else comparison.get("percentage_diff")
            ),
            "better": (
                comparison.better_label
                if hasattr(comparison, "better_label")
                else comparison.get("better_entity")
            ),
            "unit": comparison.unit if hasattr(comparison, "unit") else "g",
            "age_days": context.get("age_days"),
            "sex": context.get("sex"),
            "is_lower_better": self.calculator._is_lower_better(metric_name),
        }

        logger.debug(f"📊 Données de comparaison préparées: {comparison_data}")

        # Prompts pour OpenAI
        if language == "fr":
            system_prompt = """Tu es un expert en aviculture qui rédige des réponses professionnelles et claires pour comparer des performances entre souches.

Règles importantes :
1. TOUJOURS reformuler la question au début de la réponse pour donner le contexte
2. Utilise les noms corrects : "Cobb 500", "Ross 308" (avec majuscules)
3. Présente les deux souches de manière identique, SANS mettre l'une en gras
4. Traduis les métriques techniques : "feed_conversion_ratio" → "conversion alimentaire (FCR)"
5. Pour le FCR et la mortalité : une valeur PLUS BASSE est MEILLEURE
6. Pour le poids et la production : une valeur PLUS HAUTE est MEILLEURE
7. Fournis une interprétation concise de l'écart
8. NE termine PAS par une section "Impact pratique" ou "Recommandations\""""

            user_prompt = f"""Génère une réponse concise pour cette comparaison :

Données :
- Métrique : {comparison_data['metric_name']}
- {comparison_data['label1']} : {comparison_data['value1']:.3f} {comparison_data['unit']}
- {comparison_data['label2']} : {comparison_data['value2']:.3f} {comparison_data['unit']}
- Différence : {abs(comparison_data['difference_absolute']):.3f} ({abs(comparison_data['difference_percent']):.1f}%)
- Meilleur : {comparison_data['better']}
- Contexte : {'mâles' if comparison_data['sex'] == 'male' else 'femelles' if comparison_data['sex'] == 'female' else 'mixte'} à {comparison_data['age_days']} jours
- Type : {"moins est mieux" if comparison_data['is_lower_better'] else "plus est mieux"}"""

        else:
            system_prompt = """You are a poultry expert writing professional and clear responses to compare performances between strains.

Important rules:
1. ALWAYS rephrase the question at the beginning to provide context
2. Use proper names: "Cobb 500", "Ross 308" (capitalized)
3. Present both strains identically, WITHOUT bolding one
4. Translate technical metrics: "feed_conversion_ratio" → "feed conversion ratio (FCR)"
5. For FCR and mortality: LOWER value is BETTER
6. For weight and production: HIGHER value is BETTER
7. Provide concise interpretation of the difference
8. DO NOT end with "Practical impact" or "Recommendations" section"""

            user_prompt = f"""Generate a concise response for this comparison:

Data:
- Metric: {comparison_data['metric_name']}
- {comparison_data['label1']}: {comparison_data['value1']:.3f} {comparison_data['unit']}
- {comparison_data['label2']}: {comparison_data['value2']:.3f} {comparison_data['unit']}
- Difference: {abs(comparison_data['difference_absolute']):.3f} ({abs(comparison_data['difference_percent']):.1f}%)
- Better: {comparison_data['better']}
- Context: {'males' if comparison_data['sex'] == 'male' else 'females' if comparison_data['sex'] == 'female' else 'mixed'} at {comparison_data['age_days']} days
- Metric type: {"lower is better" if comparison_data['is_lower_better'] else "higher is better"}"""

        # Tentative avec OpenAI
        try:
            if hasattr(self.postgresql_system, "postgres_retriever"):
                retriever = self.postgresql_system.postgres_retriever
                if hasattr(retriever, "query_normalizer"):
                    from openai import AsyncOpenAI
                    import os

                    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                    response = await client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.3,
                        max_tokens=500,
                    )

                    enhanced_response = response.choices[0].message.content.strip()
                    logger.info("✅ Réponse comparative enrichie par OpenAI")
                    return enhanced_response

        except Exception as e:
            logger.warning(
                f"⚠️ Erreur enrichissement OpenAI: {e}, utilisation template de base"
            )

        # Fallback sur template basique
        terminology = None
        if hasattr(self.postgresql_system, "postgres_retriever"):
            retriever = self.postgresql_system.postgres_retriever
            if hasattr(retriever, "query_normalizer"):
                terminology = retriever.query_normalizer.terminology

        return self.calculator.format_comparison_text(
            comparison=comparison,
            metric_name=metric_name,
            language=language,
            terminology=terminology,
            context=context,
        )
