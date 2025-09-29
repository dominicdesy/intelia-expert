# -*- coding: utf-8 -*-
"""
comparison_handler.py - Gestion des requêtes comparatives
VERSION HARMONISÉE : Structure de données cohérente pour tous les chemins d'exécution
"""

import logging
from typing import Dict, List, Any, Optional
from .metric_calculator import MetricCalculator
from .comparison_utils import ComparisonUtils
from .comparison_response_generator import ComparisonResponseGenerator

logger = logging.getLogger(__name__)


class ComparisonHandler:
    """Gère les requêtes comparatives avec requêtes multiples et calculs"""

    def __init__(self, postgresql_system):
        self.postgresql_system = postgresql_system
        self.calculator = MetricCalculator()
        self.utils = ComparisonUtils()
        self.response_generator = ComparisonResponseGenerator(postgresql_system)

    def _preserve_critical_fields(
        self, entity_set: Dict[str, Any], cleaned: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Préserve les champs critiques après nettoyage"""
        critical_fields = ["sex", "age_days", "breed", "line"]

        for field in critical_fields:
            if field not in cleaned and field in entity_set:
                cleaned[field] = entity_set[field]
                logger.debug(f"✅ Champ critique '{field}' restauré: {cleaned[field]}")

        return cleaned

    def _build_results_structure(
        self, entity_results: List[Dict], comparison_result: Dict
    ) -> List[Dict]:
        """
        Construit la structure results attendue par le générateur de réponses

        Args:
            entity_results: Liste de résultats bruts [{entity_name, entity_set, docs}]
            comparison_result: Résultat de la comparaison

        Returns:
            Liste formatée [{"entity": ..., "data": [{"metric_name": ...}]}]
        """
        formatted_results = []

        for entity_result in entity_results:
            entity_name = entity_result.get("entity_name")
            docs = entity_result.get("docs", [])

            if not docs:
                continue

            # Extraire les données du premier document (meilleure métrique)
            first_doc = docs[0]
            metadata = first_doc.get("metadata", {})

            formatted_results.append(
                {
                    "entity": entity_name,
                    "data": [
                        {
                            "metric_name": metadata.get("metric_name", ""),
                            "value_numeric": metadata.get("value_numeric"),
                            "unit": metadata.get("unit", "g"),
                            "age_days": metadata.get("age_days"),
                            "sex": metadata.get("sex"),
                            "breed": metadata.get("strain_name", ""),
                        }
                    ],
                    "all_docs": docs,  # Conserver tous les docs pour référence
                }
            )

        logger.debug(
            f"📊 Structure results construite: {len(formatted_results)} entités"
        )
        return formatted_results

    async def handle_comparison_query(
        self, preprocessed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Gère les requêtes comparatives - POINT D'ENTRÉE PRINCIPAL

        Returns:
            Structure harmonisée:
            {
                "success": bool,
                "comparison": Dict (données de comparaison),
                "results": List[Dict] (documents formatés),
                "context": Dict,
                "metadata": Dict
            }
        """
        comparison_entities = preprocessed_data.get("comparison_entities", [])
        base_entities = preprocessed_data.get("entities", {})

        logger.debug(f"DEBUG: comparison_entities = {comparison_entities}")
        logger.debug(f"DEBUG: comparison_entities length = {len(comparison_entities)}")

        # Récupérer ou parser les entités de comparaison
        if comparison_entities and len(comparison_entities) >= 2:
            entity_sets = comparison_entities
            logger.info(
                f"✓ Utilisation des {len(entity_sets)} entités du preprocessing"
            )
        else:
            logger.warning("Entités de comparaison non disponibles, tentative parsing")
            entity_sets = self.utils.parse_multiple_entities_from_preprocessing(
                {"entities": base_entities}
            )
            logger.info(f"Parsing traditionnel: {len(entity_sets)} entités")

        if len(entity_sets) < 2:
            logger.error(
                f"Comparaison impossible: seulement {len(entity_sets)} entité(s)"
            )
            return self._create_error_response(
                "Comparaison nécessite au moins 2 entités"
            )

        logger.info(f"Proceeding with comparison of {len(entity_sets)} entities")

        # Exécuter les recherches pour chaque entité
        entity_results = []
        for i, entity_set in enumerate(entity_sets):
            entity_name = self.utils.generate_entity_name(entity_set, i)
            logger.debug(f"Executing query for {entity_name}")

            strict_sex_match = entity_set.get("explicit_sex_request", False)

            try:
                clean_entities = {
                    k: v for k, v in entity_set.items() if not k.startswith("_")
                }
                clean_entities = self._preserve_critical_fields(
                    entity_set, clean_entities
                )

                logger.debug(f"🎯 Final entities pour {entity_name}: {clean_entities}")

                docs = await self.postgresql_system.search_metrics(
                    query=preprocessed_data.get("normalized_query", ""),
                    entities=clean_entities,
                    top_k=12,
                    strict_sex_match=strict_sex_match,
                )

                if docs and hasattr(docs, "context_docs") and docs.context_docs:
                    logger.debug(
                        f"Found {len(docs.context_docs)} results for {entity_name}"
                    )
                    entity_results.append(
                        {
                            "entity_name": entity_name,
                            "entity_set": entity_set,
                            "docs": docs.context_docs,
                        }
                    )
                else:
                    logger.warning(f"No results found for {entity_name}")

            except Exception as e:
                logger.error(f"Query failed for {entity_name}: {e}", exc_info=True)
                continue

        if len(entity_results) < 2:
            return self._create_error_response(
                f"Données insuffisantes: {len(entity_results)} entité(s) trouvée(s)"
            )

        try:
            # Effectuer la comparaison
            comparison_data = self._compare_entities(entity_results, preprocessed_data)

            # Construire la structure results formatée
            formatted_results = self._build_results_structure(
                entity_results, comparison_data
            )

            # Retourner la structure harmonisée
            return {
                "success": True,
                "comparison": comparison_data,
                "results": formatted_results,  # Liste de documents formatés
                "context": comparison_data.get("context", {}),
                "metadata": {
                    "query_type": "comparative",
                    "entities_compared": len(entity_results),
                    "preprocessing_applied": True,
                },
            }

        except Exception as e:
            logger.error(f"Comparison failed: {e}", exc_info=True)
            return self._create_error_response(f"Erreur de comparaison: {str(e)}")

    async def handle_comparative_query(
        self, query: str, preprocessed: Dict[str, Any], top_k: int = 12
    ) -> Dict[str, Any]:
        """
        Version alternative pour compatibilité - REDIRIGE vers handle_comparison_query

        Cette méthode maintient la compatibilité avec l'ancien code tout en
        utilisant la nouvelle structure harmonisée.
        """
        logger.info("Redirecting to harmonized handle_comparison_query")

        # Construire preprocessed_data au format attendu
        preprocessed_data = {
            "normalized_query": query,
            "entities": preprocessed.get("entities", {}),
            "comparison_entities": preprocessed.get("comparison_entities", []),
            "routing_hint": "postgresql",
            "is_comparative": True,
        }

        # Appeler la méthode principale harmonisée
        return await self.handle_comparison_query(preprocessed_data)

    async def _fallback_relaxed_search(
        self, query: str, comparison_entities: List[Dict], top_k: int
    ) -> Dict[str, Any]:
        """Recherche de secours avec critères assouplis"""
        logger.info("Executing fallback search with relaxed criteria")

        entity_results = []

        for entity_set in comparison_entities:
            relaxed_entity = {
                k: v for k, v in entity_set.items() if not k.startswith("_")
            }
            relaxed_entity = self._preserve_critical_fields(entity_set, relaxed_entity)

            if "sex" in relaxed_entity:
                relaxed_entity["sex"] = "as_hatched"

            entity_key = self.utils.generate_entity_key(entity_set)

            try:
                result = await self.postgresql_system.search_metrics(
                    query=query,
                    entities=relaxed_entity,
                    top_k=top_k,
                    strict_sex_match=False,
                )

                if result and hasattr(result, "context_docs") and result.context_docs:
                    entity_results.append(
                        {
                            "entity_name": entity_key,
                            "entity_set": entity_set,
                            "docs": result.context_docs,
                        }
                    )

            except Exception as e:
                logger.error(f"Fallback search failed for {entity_key}: {e}")

        if len(entity_results) >= 2:
            try:
                comparison_data = self._compare_entities(entity_results, {})
                formatted_results = self._build_results_structure(
                    entity_results, comparison_data
                )

                return {
                    "success": True,
                    "comparison": comparison_data,
                    "results": formatted_results,
                    "context": comparison_data.get("context", {}),
                    "metadata": {
                        "entities_compared": len(entity_results),
                        "query_type": "comparative",
                        "fallback_used": True,
                    },
                    "fallback_used": True,
                    "note": "Résultats avec critères assouplis",
                }
            except Exception as e:
                logger.error(f"Error in fallback comparison: {e}")

        return {
            "success": False,
            "error": "Aucun résultat même avec critères assouplis",
            "results": [],
            "comparison": None,
        }

    def _compare_entities(
        self, entity_results: List[Dict], preprocessed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare les entités et retourne les données de comparaison

        Returns:
            Dict avec structure:
            {
                "metric_name": str,
                "entity1": str,
                "entity2": str,
                "value1": float,
                "value2": float,
                "difference": float,
                "percentage_diff": float,
                "better_entity": str,
                "unit": str,
                "context": Dict
            }
        """
        if len(entity_results) < 2:
            raise ValueError(f"Impossible de comparer {len(entity_results)} entité(s)")

        entity1 = entity_results[0]
        entity2 = entity_results[1]

        metric1 = self._extract_best_metric_with_units(
            entity1["docs"], preprocessed_data
        )
        metric2 = self._extract_best_metric_with_units(
            entity2["docs"], preprocessed_data
        )

        if not metric1 or not metric2:
            raise ValueError("Impossible d'extraire les métriques pour comparaison")

        comparison = self._compare_metrics_with_unit_handling(
            metric1,
            metric2,
            {
                "entity1_name": entity1["entity_name"],
                "entity2_name": entity2["entity_name"],
            },
        )

        # Enrichir avec les informations des entités
        comparison["entity1"] = entity1["entity_name"]
        comparison["entity2"] = entity2["entity_name"]
        comparison["context"] = self._extract_context_from_entities(entity_results)
        comparison["unit"] = metric1.get("unit", "g")

        logger.debug(f"✅ Comparaison effectuée: {comparison}")
        return comparison

    def _extract_best_metric_with_units(
        self, docs: List[Dict], preprocessed_data: Dict[str, Any]
    ) -> Optional[Dict]:
        """Extrait la meilleure métrique en gérant les unités"""
        target_age = preprocessed_data.get("entities", {}).get("age_days")

        metric_docs = []
        imperial_docs = []

        for doc in docs:
            sheet_name = doc.get("metadata", {}).get("sheet_name", "").lower()
            if "imperial" in sheet_name:
                imperial_docs.append(doc)
            else:
                metric_docs.append(doc)

        primary_docs = metric_docs if metric_docs else imperial_docs

        if not primary_docs:
            return None

        metrics = []
        for doc in primary_docs:
            parsed = self.utils.parse_metric_from_content(doc.get("content", ""))
            if parsed:
                parsed["unit_system"] = (
                    "imperial"
                    if "imperial"
                    in doc.get("metadata", {}).get("sheet_name", "").lower()
                    else "metric"
                )
                parsed["unit"] = doc.get("metadata", {}).get("unit", "g")
                metrics.append(parsed)

        if not metrics:
            return None

        if target_age:
            best_metric = self.utils.select_best_metric_by_age(metrics, int(target_age))
        else:
            best_metric = metrics[0]

        return best_metric

    def _compare_metrics_with_unit_handling(
        self, metric1: Dict, metric2: Dict, entities: Dict
    ) -> Dict:
        """Compare deux métriques en gérant les différences d'unités"""
        unit_system1 = metric1.get("unit_system", "metric")
        unit_system2 = metric2.get("unit_system", "metric")

        value1 = metric1.get("value_numeric", metric1.get("value", 0))
        value2 = metric2.get("value_numeric", metric2.get("value", 0))

        if unit_system1 != unit_system2:
            logger.warning("Systèmes d'unités différents, tentative de conversion")

            if unit_system1 == "imperial" and value1 < 20:
                value1 = value1 * 453.6
            if unit_system2 == "imperial" and value2 < 20:
                value2 = value2 * 453.6

        difference = value2 - value1
        percentage = (abs(difference) / value1 * 100) if value1 > 0 else 0

        metric_name = metric1.get("metric_name", "").lower()
        higher_is_better = self.response_generator._is_higher_better_metric(metric_name)

        if higher_is_better:
            better_entity = (
                entities.get("entity2_name")
                if value2 > value1
                else entities.get("entity1_name")
            )
        else:
            better_entity = (
                entities.get("entity1_name")
                if value1 < value2
                else entities.get("entity2_name")
            )

        return {
            "metric_name": metric1.get("metric_name"),
            "value1": value1,
            "value2": value2,
            "difference": difference,
            "percentage_diff": percentage,
            "better_entity": better_entity,
            "unit_conversion_applied": unit_system1 != unit_system2,
            "confidence": "high" if unit_system1 == unit_system2 else "medium",
        }

    def _extract_context_from_entities(
        self, entity_results: List[Dict]
    ) -> Dict[str, Any]:
        """Extrait le contexte commun des entités comparées"""
        context = {}

        if entity_results and len(entity_results) > 0:
            first_entity = entity_results[0].get("entity_set", {})

            for field in ["age_days", "sex", "breed", "line"]:
                if field in first_entity:
                    context[field] = first_entity[field]

        return context

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Crée une réponse d'erreur standardisée"""
        return {
            "success": False,
            "error": error_message,
            "results": [],
            "comparison": None,
        }

    async def generate_comparative_response(
        self, query: str, comparison_result: Dict[str, Any], language: str = "fr"
    ) -> str:
        """Délègue la génération de réponse au ResponseGenerator"""
        return await self.response_generator.generate_comparative_response(
            query, comparison_result, language
        )

    async def handle_temporal_comparison(
        self, query: str, age_start: int, age_end: int, entities: Dict
    ) -> Dict:
        """Gère les comparaisons temporelles entre deux âges"""
        try:
            logger.info(f"Handling temporal comparison: {age_start} -> {age_end} days")

            entities_start = entities.copy()
            entities_start["age_days"] = age_start
            entities_start = self._preserve_critical_fields(entities, entities_start)

            result_start = await self.postgresql_system.search_metrics(
                query=f"Métrique à {age_start} jours",
                entities=entities_start,
                top_k=12,
                strict_sex_match=True,
            )

            entities_end = entities.copy()
            entities_end["age_days"] = age_end
            entities_end = self._preserve_critical_fields(entities, entities_end)

            result_end = await self.postgresql_system.search_metrics(
                query=f"Métrique à {age_end} jours",
                entities=entities_end,
                top_k=12,
                strict_sex_match=True,
            )

            if not (
                result_start
                and hasattr(result_start, "context_docs")
                and result_start.context_docs
            ):
                return {
                    "success": False,
                    "error": f"Aucun résultat trouvé pour {age_start} jours",
                    "comparison_type": "temporal",
                }

            if not (
                result_end
                and hasattr(result_end, "context_docs")
                and result_end.context_docs
            ):
                return {
                    "success": False,
                    "error": f"Aucun résultat trouvé pour {age_end} jours",
                    "comparison_type": "temporal",
                }

            metric_start = self.utils.extract_metric_value(result_start.context_docs[0])
            metric_end = self.utils.extract_metric_value(result_end.context_docs[0])

            if metric_start is None or metric_end is None:
                return {
                    "success": False,
                    "error": "Impossible d'extraire les valeurs numériques",
                    "comparison_type": "temporal",
                }

            difference = metric_end - metric_start
            percent_change = (
                (difference / metric_start * 100) if metric_start != 0 else 0
            )

            evolution = "stable"
            if abs(percent_change) > 1:
                evolution = "croissance" if difference > 0 else "diminution"

            start_doc = result_start.context_docs[0]
            start_metadata = start_doc.get("metadata", {})
            metric_name = start_metadata.get("metric_name", "métrique")
            unit = self.utils.extract_unit_from_doc(start_doc)

            return {
                "success": True,
                "comparison_type": "temporal",
                "start_age": age_start,
                "end_age": age_end,
                "start_value": metric_start,
                "end_value": metric_end,
                "difference": difference,
                "percent_change": percent_change,
                "evolution": evolution,
                "metric_name": metric_name,
                "unit": unit,
                "entities": entities,
                "metadata": {
                    "age_range": f"{age_start}-{age_end} jours",
                    "evolution_type": evolution,
                    "significant_change": abs(percent_change) > 1,
                },
            }

        except Exception as e:
            logger.error(f"Error in temporal comparison: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erreur dans la comparaison temporelle: {str(e)}",
                "comparison_type": "temporal",
            }
