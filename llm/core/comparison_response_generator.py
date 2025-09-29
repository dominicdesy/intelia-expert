# -*- coding: utf-8 -*-
"""
comparison_response_generator.py - Génération de réponses comparatives
Utilise OpenAI pour générer des réponses professionnelles et claires
"""

import logging
from typing import Dict, Any
from .metric_calculator import MetricCalculator

logger = logging.getLogger(__name__)


class ComparisonResponseGenerator:
    """Génère des réponses comparatives enrichies par OpenAI"""

    def __init__(self, postgresql_system=None):
        """
        Args:
            postgresql_system: Instance PostgreSQLSystem pour accéder au client OpenAI
        """
        self.postgresql_system = postgresql_system
        self.calculator = MetricCalculator()

    def _is_higher_better_metric(self, metric_name: str) -> bool:
        """Détermine si une valeur plus élevée est meilleure"""
        metric_name_lower = metric_name.lower()

        higher_better_keywords = [
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

        lower_better_keywords = [
            "conversion",
            "fcr",
            "mortality",
            "mortalité",
            "cost",
            "coût",
        ]

        if any(keyword in metric_name_lower for keyword in higher_better_keywords):
            return True
        elif any(keyword in metric_name_lower for keyword in lower_better_keywords):
            return False
        else:
            return True

    async def generate_comparative_response(
        self, query: str, comparison_result: Dict[str, Any], language: str = "fr"
    ) -> str:
        """
        Génère une réponse naturelle pour une comparaison

        Args:
            query: Requête originale
            comparison_result: Résultat de handle_comparative_query
            language: Langue de la réponse

        Returns:
            Texte de réponse formatté et enrichi par OpenAI
        """
        if not comparison_result.get("success"):
            error = comparison_result.get("error", "Unknown error")
            if language == "fr":
                return f"Impossible de comparer: {error}"
            else:
                return f"Cannot compare: {error}"

        comparison = comparison_result["comparison"]
        results = comparison_result["results"]
        context = comparison_result.get("context", {})

        metric_name = "métrique"
        if results and len(results) > 0:
            first_result = results[0]
            if "data" in first_result and len(first_result["data"]) > 0:
                metric_data = first_result["data"][0]
                metric_name = metric_data.get("metric_name", metric_name)

        comparison_data = {
            "metric_name": metric_name,
            "label1": comparison.label1,
            "value1": comparison.value1,
            "label2": comparison.label2,
            "value2": comparison.value2,
            "difference_absolute": comparison.absolute_difference,
            "difference_percent": comparison.relative_difference_pct,
            "better": comparison.better_label,
            "unit": comparison.unit,
            "age_days": context.get("age_days"),
            "sex": context.get("sex"),
            "is_lower_better": self.calculator._is_lower_better(
                comparison.metric_name or metric_name
            ),
        }

        if language == "fr":
            system_prompt = """Tu es un expert en aviculture qui rédige des réponses professionnelles et claires pour comparer des performances entre souches.

Règles importantes :
1. TOUJOURS reformuler la question au début de la réponse pour donner le contexte
2. Utilise les noms corrects : "Cobb 500", "Ross 308" (avec majuscules)
3. Présente les deux souches de manière identique, SANS mettre l'une en gras
4. Traduis les métriques techniques en français : "feed_conversion_ratio" → "conversion alimentaire (FCR)"
5. Pour le FCR et la mortalité : une valeur PLUS BASSE est MEILLEURE
6. Pour le poids et la production : une valeur PLUS HAUTE est MEILLEURE
7. Fournis une interprétation concise de l'écart
8. NE termine PAS avec une section "Impact pratique" ou "Recommandations"

Format attendu :
- Reformulation de la question en une ligne
- Valeurs comparées avec unités (format : "Souche : valeur (unité)" sur deux lignes distinctes, sans gras)
- Différence avec pourcentage en gras
- Interprétation : qui est meilleur et pourquoi en 1-2 phrases maximum
- Pas de conclusion ou d'impact pratique"""

            user_prompt = f"""Génère une réponse concise pour cette comparaison :

Données :
- Métrique : {comparison_data['metric_name']}
- {comparison_data['label1']} : {comparison_data['value1']:.3f} {comparison_data['unit']}
- {comparison_data['label2']} : {comparison_data['value2']:.3f} {comparison_data['unit']}
- Différence : {abs(comparison_data['difference_absolute']):.3f} ({abs(comparison_data['difference_percent']):.1f}%)
- Meilleur : {comparison_data['better']}
- Contexte : {'mâles' if comparison_data['sex'] == 'male' else 'femelles' if comparison_data['sex'] == 'female' else 'sexes mélangés'} à {comparison_data['age_days']} jours
- Type métrique : {"plus bas = meilleur" if comparison_data['is_lower_better'] else "plus haut = meilleur"}"""

        else:  # English
            system_prompt = """You are a poultry expert writing professional and clear responses comparing strain performances.

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
                    logger.info("Réponse comparative enrichie par OpenAI")
                    return enhanced_response

        except Exception as e:
            logger.warning(
                f"Erreur enrichissement OpenAI: {e}, utilisation template de base"
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
