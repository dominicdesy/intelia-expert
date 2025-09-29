# -*- coding: utf-8 -*-
"""
comparison_handler.py - Gestion des requêtes comparatives
VERSION CORRIGÉE : Bug du champ 'sex' résolu avec préservation garantie
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
        """
        Args:
            postgresql_system: Instance de PostgreSQLSystem pour exécuter les requêtes
        """
        self.postgresql_system = postgresql_system
        self.calculator = MetricCalculator()
        self.utils = ComparisonUtils()
        self.response_generator = ComparisonResponseGenerator(postgresql_system)

    def _preserve_critical_fields(
        self, entity_set: Dict[str, Any], cleaned: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Préserve les champs critiques (sex, age_days, breed) après nettoyage

        Args:
            entity_set: Dictionnaire original avec tous les champs
            cleaned: Dictionnaire nettoyé (sans underscores)

        Returns:
            Dictionnaire avec champs critiques garantis
        """
        critical_fields = ["sex", "age_days", "breed", "line"]

        for field in critical_fields:
            if field not in cleaned and field in entity_set:
                cleaned[field] = entity_set[field]
                logger.debug(f"✅ Champ critique '{field}' restauré: {cleaned[field]}")

        return cleaned

    async def handle_comparison_query(
        self, preprocessed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gère les requêtes comparatives avec support des entités séparées"""

        comparison_entities = preprocessed_data.get("comparison_entities", [])
        base_entities = preprocessed_data.get("entities", {})

        logger.debug(
            f"DEBUG: preprocessed_data keys = {list(preprocessed_data.keys())}"
        )
        logger.debug(
            f"DEBUG: comparison_entities from preprocessing = {comparison_entities}"
        )
        logger.debug(f"DEBUG: comparison_entities length = {len(comparison_entities)}")

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

        results = []
        for i, entity_set in enumerate(entity_sets):
            entity_name = self.utils.generate_entity_name(entity_set, i)
            logger.debug(f"Executing query for {entity_name}")

            strict_sex_match = entity_set.get("explicit_sex_request", False)

            try:
                # 🔧 CORRECTION: Nettoyage avec préservation des champs critiques
                clean_entities = {
                    k: v for k, v in entity_set.items() if not k.startswith("_")
                }

                logger.debug(f"🔍 entity_set BEFORE cleaning: {entity_set}")
                logger.debug(f"🔍 clean_entities AFTER cleaning: {clean_entities}")

                # 🟢 GARANTIR la présence des champs critiques
                clean_entities = self._preserve_critical_fields(
                    entity_set, clean_entities
                )

                logger.debug(
                    f"🎯 Final entities envoyées à search_metrics: {clean_entities}"
                )

                # 🔥 Appel avec arguments nommés explicites
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
                    results.append(
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

        if len(results) < 2:
            return self._create_error_response(
                f"Données insuffisantes: {len(results)} entité(s) trouvée(s)"
            )

        try:
            comparison_result = self._compare_entities(results, preprocessed_data)
            return self._format_comparison_response(
                comparison_result, preprocessed_data
            )

        except Exception as e:
            logger.error(f"Comparison failed: {e}", exc_info=True)
            return self._create_error_response(f"Erreur de comparaison: {str(e)}")

    async def handle_comparative_query(
        self, query: str, preprocessed: Dict[str, Any], top_k: int = 12
    ) -> Dict[str, Any]:
        """Version alternative pour compatibilité avec l'ancien code"""
        logger.info("Handling comparative query with preprocessed data")

        if self.utils.is_temporal_range_query(query):
            logger.info("Query detected as temporal range, not comparative")
            return {
                "success": False,
                "error": "Query is temporal, not comparative",
                "suggestion": "Use temporal handler instead",
                "query_type": "temporal",
                "results": [],
                "comparison": None,
            }

        comparison_entities = self.utils.parse_multiple_entities_from_preprocessing(
            preprocessed
        )

        if len(comparison_entities) < 2:
            logger.warning(
                f"Comparaison nécessite au moins 2 entités, trouvé: {len(comparison_entities)}"
            )
            return {
                "success": False,
                "error": "Comparaison impossible avec une seule entité",
                "entities_found": comparison_entities,
                "suggestion": "Vérifiez que votre requête contient bien 2 éléments à comparer",
                "results": [],
                "comparison": None,
            }

        logger.info(
            f"Proceeding with comparison of {len(comparison_entities)} entities"
        )

        validation_result = self.utils.validate_comparison_entities(comparison_entities)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": f"Entités de comparaison invalides: {validation_result['reason']}",
                "entities": comparison_entities,
                "results": [],
                "comparison": None,
            }

        results = {}
        successful_queries = 0

        for i, entity_set in enumerate(comparison_entities):
            entity_key = self.utils.generate_entity_key(entity_set)
            logger.debug(f"Executing query for {entity_key}")

            try:
                # 🔧 CORRECTION: Même logique de préservation
                clean_entities = {
                    k: v for k, v in entity_set.items() if not k.startswith("_")
                }

                logger.debug(f"🔍 entity_set original: {entity_set}")
                logger.debug(f"🔍 clean_entities avant restauration: {clean_entities}")

                # 🟢 Préserver les champs critiques
                clean_entities = self._preserve_critical_fields(
                    entity_set, clean_entities
                )

                logger.debug(f"🎯 Final entities pour {entity_key}: {clean_entities}")

                result = await self.postgresql_system.search_metrics(
                    query=query,
                    entities=clean_entities,
                    top_k=top_k,
                    strict_sex_match=True,
                )

                if result and hasattr(result, "context_docs") and result.context_docs:
                    results[entity_key] = result
                    successful_queries += 1
                    logger.debug(
                        f"Found {len(result.context_docs)} results for {entity_key}"
                    )
                else:
                    logger.warning(f"Empty context_docs for {entity_key}")
                    results[entity_key] = None

            except Exception as e:
                logger.error(f"Error querying {entity_key}: {e}", exc_info=True)
                results[entity_key] = None

        if successful_queries < 2:
            logger.warning(f"Insufficient results: found {successful_queries}, need 2")

            if successful_queries == 0:
                logger.info("Trying fallback with relaxed sex matching...")
                return await self._fallback_relaxed_search(
                    query, comparison_entities, top_k
                )

            return {
                "success": False,
                "error": f"Insufficient results: found {successful_queries}, need 2",
                "details": {
                    "successful_entities": [
                        k for k, v in results.items() if v is not None
                    ],
                    "failed_entities": [k for k, v in results.items() if v is None],
                },
                "results": [],
                "comparison": None,
            }

        try:
            old_format_results = self.utils.convert_to_old_format(
                results, comparison_entities
            )

            if len(old_format_results) < 2:
                return {
                    "success": False,
                    "error": f"Insufficient results after conversion: {len(old_format_results)}",
                    "results": old_format_results,
                    "comparison": None,
                }

            comparison = self.calculator.calculate_comparison(old_format_results)
            context = self.utils.extract_common_context(
                old_format_results, comparison_entities
            )

            comparative_info = preprocessed.get("comparative_info", {})

            logger.info(
                f"Comparison successful: {comparison.label1} vs {comparison.label2}"
            )

            return {
                "success": True,
                "results": old_format_results,
                "comparison": comparison,
                "operation": comparative_info.get("operation"),
                "comparison_type": comparative_info.get("type"),
                "context": context,
                "metadata": {
                    "entities_compared": len(comparison_entities),
                    "successful_queries": successful_queries,
                    "query_type": "comparative",
                    "fallback_used": False,
                },
            }

        except Exception as e:
            logger.error(f"Error in comparison analysis: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erreur dans l'analyse comparative: {str(e)}",
                "results": [],
                "comparison": None,
            }

    async def _fallback_relaxed_search(
        self, query: str, comparison_entities: List[Dict], top_k: int
    ) -> Dict[str, Any]:
        """Recherche de secours avec critères assouplis"""
        logger.info("Executing fallback search with relaxed criteria")

        results = {}
        successful_queries = 0

        for entity_set in comparison_entities:
            # 🔧 Nettoyage avec préservation
            relaxed_entity = {
                k: v for k, v in entity_set.items() if not k.startswith("_")
            }

            relaxed_entity = self._preserve_critical_fields(entity_set, relaxed_entity)

            # Override sex pour recherche plus large
            if "sex" in relaxed_entity:
                relaxed_entity["sex"] = "as_hatched"
                logger.debug("Fallback: sex set to 'as_hatched' for broader search")

            entity_key = self.utils.generate_entity_key(entity_set)

            try:
                result = await self.postgresql_system.search_metrics(
                    query=query,
                    entities=relaxed_entity,
                    top_k=top_k,
                    strict_sex_match=False,
                )

                if result and hasattr(result, "context_docs") and result.context_docs:
                    results[entity_key] = result
                    successful_queries += 1
                    logger.debug(f"Fallback successful for {entity_key}")

            except Exception as e:
                logger.error(f"Fallback search failed for {entity_key}: {e}")

        if successful_queries >= 2:
            old_format_results = self.utils.convert_to_old_format(
                results, comparison_entities
            )

            if len(old_format_results) >= 2:
                try:
                    comparison = self.calculator.calculate_comparison(
                        old_format_results
                    )
                    context = self.utils.extract_common_context(
                        old_format_results, comparison_entities
                    )

                    return {
                        "success": True,
                        "results": old_format_results,
                        "comparison": comparison,
                        "context": context,
                        "metadata": {
                            "entities_compared": len(comparison_entities),
                            "successful_queries": successful_queries,
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
        self, results: List[Dict], preprocessed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare les entités"""
        if len(results) < 2:
            raise ValueError(f"Impossible de comparer {len(results)} entité(s)")

        entity1 = results[0]
        entity2 = results[1]

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

        comparison["entity1"] = entity1["entity_name"]
        comparison["entity2"] = entity2["entity_name"]
        comparison["context"] = self._extract_context_from_entities(results)

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
            logger.warning(
                "Systèmes d'unités différents détectés, tentative de conversion"
            )

            if unit_system1 == "imperial" and value1 < 20:
                value1 = value1 * 453.6
                logger.debug(f"Conversion impérial->métrique: {value1} g")

            if unit_system2 == "imperial" and value2 < 20:
                value2 = value2 * 453.6
                logger.debug(f"Conversion impérial->métrique: {value2} g")

        difference = abs(value2 - value1)
        percentage = (difference / value1 * 100) if value1 > 0 else 0

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

    def _extract_context_from_entities(self, results: List[Dict]) -> Dict[str, Any]:
        """Extrait le contexte commun des entités comparées"""
        context = {}

        if results and len(results) > 0:
            first_entity = results[0].get("entity_set", {})

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

    def _format_comparison_response(
        self, comparison_result: Dict[str, Any], preprocessed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Formate la réponse de comparaison"""
        return {
            "success": True,
            "comparison": comparison_result,
            "results": comparison_result,
            "metadata": {
                "query_type": "comparative",
                "entities_compared": 2,
                "preprocessing_applied": True,
            },
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

            # 🔧 Préservation pour l'âge de départ
            entities_start = entities.copy()
            entities_start["age_days"] = age_start
            entities_start = self._preserve_critical_fields(entities, entities_start)

            result_start = await self.postgresql_system.search_metrics(
                query=f"Métrique à {age_start} jours",
                entities=entities_start,
                top_k=12,
                strict_sex_match=True,
            )

            # 🔧 Préservation pour l'âge de fin
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
                logger.warning(f"No results for age {age_start} days")
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
                logger.warning(f"No results for age {age_end} days")
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

            logger.info(
                f"Temporal comparison successful: {metric_start} -> {metric_end} ({percent_change:.1f}%)"
            )

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
