# -*- coding: utf-8 -*-
"""
comparison_handler.py - Gestion des requêtes comparatives
VERSION CORRIGÉE : Passage du contexte (âge, sexe) à format_comparison_text
"""

import logging
from typing import Dict, List, Any, Optional
from .metric_calculator import MetricCalculator

logger = logging.getLogger(__name__)


class ComparisonHandler:
    """Gère les requêtes comparatives avec requêtes multiples et calculs"""

    def __init__(self, postgresql_system):
        """
        Args:
            postgresql_system: Instance de PostgreSQLSystem pour exécuter les requêtes
        """
        self.postgresql_system = postgresql_system
        self.calculator = MetricCalculator()

    async def handle_comparative_query(
        self, query: str, preprocessed: Dict[str, Any], top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Traite une requête comparative

        Args:
            query: Requête utilisateur originale
            preprocessed: Résultat du preprocessing avec comparative_info
            top_k: Nombre de résultats par requête

        Returns:
            {
                'results': List[Dict],
                'comparison': ComparisonResult,
                'success': bool,
                'error': Optional[str],
                'context': Dict  # NOUVEAU: contexte pour la génération de réponse
            }
        """
        try:
            comparative_info = preprocessed.get("comparative_info", {})
            comparison_entities = preprocessed.get("comparison_entities", [])

            if not comparison_entities:
                logger.warning("No comparison entities found")
                return {
                    "success": False,
                    "error": "No entities to compare",
                    "results": [],
                    "comparison": None,
                }

            logger.info(
                f"Handling comparative query with {len(comparison_entities)} entity sets"
            )

            # Exécuter une requête pour chaque jeu d'entités
            results = []
            for entity_set in comparison_entities:
                result = await self._execute_single_query(query, entity_set, top_k)
                if result:
                    results.append(result)

            if len(results) < 2:
                return {
                    "success": False,
                    "error": f"Insufficient results: found {len(results)}, need 2",
                    "results": results,
                    "comparison": None,
                }

            # Calculer la comparaison
            comparison = self.calculator.calculate_comparison(results)

            # NOUVEAU: Extraire le contexte commun (âge, sexe, etc.)
            context = self._extract_common_context(results, comparison_entities)

            logger.info(
                f"Comparison successful: {comparison.label1} vs {comparison.label2}"
            )

            return {
                "success": True,
                "results": results,
                "comparison": comparison,
                "operation": comparative_info.get("operation"),
                "comparison_type": comparative_info.get("type"),
                "context": context,  # NOUVEAU
            }

        except Exception as e:
            logger.error(f"Error handling comparative query: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "comparison": None,
            }

    def _extract_common_context(
        self, results: List[Dict], comparison_entities: List[Dict]
    ) -> Dict[str, Any]:
        """
        Extrait le contexte commun aux deux résultats (âge, sexe si comparaison de souches, etc.)

        Args:
            results: Résultats des deux requêtes
            comparison_entities: Entités de comparaison originales

        Returns:
            Dict avec age_days, sex, breed, comparison_dimension, etc.
        """
        context = {}

        if not results or len(results) == 0:
            return context

        # Extraire depuis les entity_sets
        if results[0].get("entity_set"):
            first_entity_set = results[0]["entity_set"]

            # Âge (commun aux deux)
            if "age_days" in first_entity_set:
                context["age_days"] = first_entity_set["age_days"]

            # Sexe (si comparaison de souches, le sexe est commun)
            if "sex" in first_entity_set:
                # Vérifier si c'est la dimension de comparaison
                comparison_dimension = (
                    comparison_entities[0].get("_comparison_dimension")
                    if comparison_entities
                    else None
                )
                if comparison_dimension != "sex":
                    # Le sexe est commun (on compare autre chose)
                    context["sex"] = first_entity_set["sex"]

        # Extraire depuis les métadonnées des résultats
        if results[0].get("data") and len(results[0]["data"]) > 0:
            first_metric = results[0]["data"][0]
            metadata = first_metric.get("metadata", {})

            if "age_min" in metadata and "age_days" not in context:
                context["age_days"] = metadata["age_min"]

        logger.debug(f"Extracted context: {context}")
        return context

    async def _execute_single_query(
        self, query: str, entities: Dict[str, Any], top_k: int
    ) -> Optional[Dict[str, Any]]:
        """
        Exécute une requête PostgreSQL avec un jeu d'entités spécifique

        Args:
            query: Requête originale
            entities: Jeu d'entités pour cette requête
            top_k: Nombre de résultats

        Returns:
            {
                'sex': str,  # ou autre label
                'label': str,
                'data': List[Dict],
                'entity_set': Dict  # NOUVEAU: pour extraire le contexte
            }
        """
        try:
            # Extraire le label de comparaison
            comparison_label = entities.get("_comparison_label", "unknown")
            comparison_dimension = entities.get("_comparison_dimension", "sex")

            # Créer une copie sans les métadonnées internes
            clean_entities = {
                k: v for k, v in entities.items() if not k.startswith("_")
            }

            logger.debug(
                f"Executing query for {comparison_dimension}={comparison_label}"
            )

            # Appel au système PostgreSQL avec strict_sex_match=True
            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=clean_entities,
                top_k=top_k,
                strict_sex_match=True,
            )

            # Vérifier si on a des résultats
            if not result or not hasattr(result, "context_docs"):
                logger.warning(f"No results for {comparison_label}")
                return None

            context_docs = result.context_docs
            if not context_docs or len(context_docs) == 0:
                logger.warning(f"Empty context_docs for {comparison_label}")
                return None

            # Convertir les documents en format exploitable
            metrics = self._extract_metrics_from_docs(context_docs)

            if not metrics:
                logger.warning(f"No metrics extracted for {comparison_label}")
                return None

            # Sélectionner le meilleur résultat
            best_metric = self._select_best_metric(metrics, entities)

            return {
                comparison_dimension: comparison_label,
                "label": comparison_label,
                "data": [best_metric],
                "all_metrics": metrics,
                "entity_set": clean_entities,  # GARDÉ pour extraction de contexte
            }

        except Exception as e:
            logger.error(f"Error executing single query: {e}")
            return None

    def _extract_metrics_from_docs(
        self, context_docs: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Extrait les métriques des documents de contexte"""
        metrics = []

        # Debug: inspecter le premier document
        if context_docs and len(context_docs) > 0:
            first_doc = context_docs[0]
            logger.debug(f"First doc type: {type(first_doc)}")
            if isinstance(first_doc, dict):
                logger.debug(f"First doc keys: {list(first_doc.keys())}")
                if "metadata" in first_doc:
                    logger.debug(f"Metadata keys: {list(first_doc['metadata'].keys())}")
                if "content" in first_doc:
                    logger.debug(f"Content preview: {first_doc['content'][:200]}")

        for doc in context_docs:
            if not isinstance(doc, dict):
                logger.warning(f"Skipping non-dict doc: {type(doc)}")
                continue

            metadata = doc.get("metadata", {})
            content = doc.get("content", "")

            # Extraire les infos du metadata
            metric_name = metadata.get("metric_name", "")
            unit = ""
            value_numeric = None

            # Parser le content pour extraire value_numeric et unit
            if content:
                import re

                value_match = re.search(r"Value:\s*([0-9.]+)\s*(\w*)", content)
                if value_match:
                    try:
                        value_numeric = float(value_match.group(1))
                        unit = value_match.group(2) if value_match.group(2) else ""

                        metrics.append(
                            {
                                "value_numeric": value_numeric,
                                "unit": unit,
                                "metric_name": metric_name,
                                "metadata": metadata,
                            }
                        )
                        logger.debug(
                            f"Extracted: {metric_name} = {value_numeric} {unit}"
                        )
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Failed to parse value from: {value_match.group(1)}, error: {e}"
                        )
                else:
                    logger.debug(f"No value pattern found in content: {content[:100]}")

        logger.info(
            f"Successfully extracted {len(metrics)} metrics from {len(context_docs)} docs"
        )
        return metrics

    def _select_best_metric(
        self, metrics: List[Dict], entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sélectionne la meilleure métrique selon les critères"""
        if not metrics:
            return {}

        # Prendre la première (déjà triée par pertinence)
        best = metrics[0]

        logger.debug(
            f"Selected best metric: {best.get('metric_name')} = "
            f"{best.get('value_numeric')} {best.get('unit')}"
        )

        return best

    async def generate_comparative_response(
        self, query: str, comparison_result: Dict[str, Any], language: str = "fr"
    ) -> str:
        """
        Génère une réponse naturelle pour une comparaison
        VERSION AMÉLIORÉE : Utilise OpenAI pour une réponse professionnelle

        Args:
            query: Requête originale
            comparison_result: Résultat de handle_comparative_query
            language: Langue de la réponse

        Returns:
            Texte de réponse formaté et enrichi par OpenAI
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

        # Extraire le nom de métrique
        metric_name = "métrique"
        if results and len(results) > 0:
            first_result = results[0]
            if "data" in first_result and len(first_result["data"]) > 0:
                metric_data = first_result["data"][0]
                metric_name = metric_data.get("metric_name", metric_name)

        # Construire les données structurées pour OpenAI
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

        # Prompt système pour OpenAI
        if language == "fr":
            system_prompt = """Tu es un expert en aviculture qui rédige des réponses professionnelles et claires pour comparer des performances entre souches.

Règles importantes :
1. Utilise les noms corrects : "Cobb 500", "Ross 308" (avec majuscules)
2. Traduis les métriques techniques en français : "feed_conversion_ratio" → "conversion alimentaire (FCR)"
3. Pour le FCR et la mortalité : une valeur PLUS BASSE est MEILLEURE
4. Pour le poids et la production : une valeur PLUS HAUTE est MEILLEURE
5. Fournis un contexte métier pour interpréter l'écart
6. Sois concis mais informatif

Format attendu :
- Titre avec contexte (âge, sexe si pertinent)
- Valeurs comparées avec unités
- Différence avec pourcentage
- Interprétation : qui est meilleur et pourquoi
- Note explicative courte sur l'impact pratique"""

            user_prompt = f"""Génère une réponse professionnelle pour cette comparaison :

Données :
- Métrique : {comparison_data['metric_name']}
- {comparison_data['label1']} : {comparison_data['value1']:.3f} {comparison_data['unit']}
- {comparison_data['label2']} : {comparison_data['value2']:.3f} {comparison_data['unit']}
- Différence : {abs(comparison_data['difference_absolute']):.3f} ({abs(comparison_data['difference_percent']):.1f}%)
- Meilleur : {comparison_data['better']}
- Contexte : {'mâles' if comparison_data['sex'] == 'male' else 'femelles' if comparison_data['sex'] == 'female' else 'sexes mélangés'} à {comparison_data['age_days']} jours
- Type métrique : {"plus bas = meilleur" if comparison_data['is_lower_better'] else "plus haut = meilleur"}

Requête originale : {query}"""

        else:  # English
            system_prompt = """You are a poultry expert writing professional and clear responses comparing strain performances.

Important rules:
1. Use proper names: "Cobb 500", "Ross 308" (capitalized)
2. Translate technical metrics: "feed_conversion_ratio" → "feed conversion ratio (FCR)"
3. For FCR and mortality: LOWER value is BETTER
4. For weight and production: HIGHER value is BETTER
5. Provide business context to interpret the difference
6. Be concise but informative

Expected format:
- Title with context (age, sex if relevant)
- Compared values with units
- Difference with percentage
- Interpretation: who is better and why
- Brief note on practical impact"""

            user_prompt = f"""Generate a professional response for this comparison:

Data:
- Metric: {comparison_data['metric_name']}
- {comparison_data['label1']}: {comparison_data['value1']:.3f} {comparison_data['unit']}
- {comparison_data['label2']}: {comparison_data['value2']:.3f} {comparison_data['unit']}
- Difference: {abs(comparison_data['difference_absolute']):.3f} ({abs(comparison_data['difference_percent']):.1f}%)
- Better: {comparison_data['better']}
- Context: {'males' if comparison_data['sex'] == 'male' else 'females' if comparison_data['sex'] == 'female' else 'mixed'} at {comparison_data['age_days']} days
- Metric type: {"lower is better" if comparison_data['is_lower_better'] else "higher is better"}

Original query: {query}"""

        try:
            # Appel OpenAI pour génération de réponse de qualité
            if hasattr(self.postgresql_system, "postgres_retriever"):
                retriever = self.postgresql_system.postgres_retriever
                if hasattr(retriever, "query_normalizer"):
                    # Utiliser le client OpenAI déjà existant
                    from openai import AsyncOpenAI
                    import os

                    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                    response = await client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.3,  # Un peu de créativité mais pas trop
                        max_tokens=500,
                    )

                    enhanced_response = response.choices[0].message.content.strip()
                    logger.info("Réponse comparative enrichie par OpenAI")
                    return enhanced_response

        except Exception as e:
            logger.warning(
                f"Erreur enrichissement OpenAI: {e}, utilisation template de base"
            )
            # Fallback sur le template basique
            pass

        # Fallback : utiliser le formatter basique si OpenAI échoue
        terminology = None
        if hasattr(self.postgresql_system, "postgres_retriever"):
            retriever = self.postgresql_system.postgres_retriever
            if hasattr(retriever, "query_normalizer"):
                terminology = retriever.query_normalizer.terminology

        formatted_text = self.calculator.format_comparison_text(
            comparison=comparison,
            metric_name=metric_name,
            language=language,
            terminology=terminology,
            context=context,
        )

        return formatted_text


# Tests unitaires
if __name__ == "__main__":
    import asyncio

    async def test_comparison_handler():
        """Test avec des données mockées"""

        # Mock PostgreSQL System
        class MockPostgreSQLSystem:
            async def search_metrics(
                self, query, entities, top_k, strict_sex_match=False
            ):
                # Simuler des résultats différents selon le sexe
                sex = entities.get("sex", "male")

                class MockResult:
                    def __init__(self, sex_val):
                        self.context_docs = [
                            {
                                "content": f"Value: {'1.081' if sex_val == 'male' else '1.045'} ratio",
                                "metadata": {
                                    "value_numeric": (
                                        1.081 if sex_val == "male" else 1.045
                                    ),
                                    "unit": "ratio",
                                    "metric_name": "feed_conversion_ratio for 17",
                                    "age_min": 17,
                                },
                            }
                        ]

                return MockResult(sex)

        mock_system = MockPostgreSQLSystem()
        handler = ComparisonHandler(mock_system)

        # Simuler un preprocessing comparatif
        preprocessed = {
            "comparative_info": {
                "is_comparative": True,
                "type": "difference",
                "operation": "subtract",
            },
            "comparison_entities": [
                {
                    "sex": "male",
                    "age_days": 17,
                    "_comparison_label": "Cobb 500",
                    "_comparison_dimension": "breed",
                },
                {
                    "sex": "male",
                    "age_days": 17,
                    "_comparison_label": "Ross 308",
                    "_comparison_dimension": "breed",
                },
            ],
        }

        result = await handler.handle_comparative_query(
            "Quelle est la différence de FCR entre Cobb 500 et Ross 308 mâle à 17 jours ?",
            preprocessed,
        )

        print("Comparison Result:")
        print(f"  Success: {result['success']}")
        if result["success"]:
            comp = result["comparison"]
            print(f"  {comp.label1}: {comp.value1}")
            print(f"  {comp.label2}: {comp.value2}")
            print(f"  Difference: {comp.absolute_difference:.3f}")
            print(f"  Context: {result.get('context')}")

            # Générer la réponse
            response = await handler.generate_comparative_response(
                "Test query", result, "fr"
            )
            print("\nGenerated Response:")
            print(response)

    asyncio.run(test_comparison_handler())
