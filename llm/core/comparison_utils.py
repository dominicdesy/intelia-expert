# -*- coding: utf-8 -*-
"""
comparison_utils.py - Utilitaires pour le ComparisonHandler
Extraction, parsing, validation et sélection de métriques
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ComparisonUtils:
    """Utilitaires pour extraction et manipulation de métriques comparatives"""

    @staticmethod
    def parse_multiple_entities_from_preprocessing(
        preprocessed: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Parse les entités multiples depuis le preprocessing"""
        entities_list = []
        base_entities = preprocessed.get("entities", {})
        logger.debug(f"Base entities from preprocessing: {base_entities}")

        comparison_found = False
        for field, value in base_entities.items():
            if isinstance(value, str) and "," in value:
                values = [v.strip() for v in value.split(",")]
                logger.debug(f"Field {field} has multiple values: {values}")

                if len(values) > 1:
                    comparison_found = True
                    for val in values:
                        entity_set = base_entities.copy()
                        entity_set[field] = val
                        entity_set["_comparison_label"] = val
                        entity_set["_comparison_dimension"] = field
                        entities_list.append(entity_set)
                    break

        if not comparison_found:
            entities_list = [base_entities]
            logger.debug("No multiple entities found, using base entities")

        logger.info(f"Parsed {len(entities_list)} entity sets for comparison")
        return entities_list

    @staticmethod
    def validate_comparison_entities(entities: List[Dict]) -> Dict[str, Any]:
        """Validation des entités de comparaison"""
        if not entities or len(entities) < 2:
            return {"valid": False, "reason": "Au moins 2 entités requises"}

        for i, entity in enumerate(entities):
            clean_entity = {k: v for k, v in entity.items() if not k.startswith("_")}
            if not clean_entity:
                return {
                    "valid": False,
                    "reason": f"Entité {i+1} est vide après nettoyage",
                }

        return {"valid": True, "reason": "Entités valides"}

    @staticmethod
    def generate_entity_key(entity_set: Dict[str, Any]) -> str:
        """Génère une clé unique pour identifier un jeu d'entités"""
        if "_comparison_label" in entity_set:
            return entity_set["_comparison_label"]

        key_parts = []
        for field in ["breed", "sex", "age_days", "line", "species"]:
            if field in entity_set and entity_set[field]:
                key_parts.append(f"{field}:{entity_set[field]}")

        return "_".join(key_parts) if key_parts else f"entity_{hash(str(entity_set))}"

    @staticmethod
    def generate_entity_name(entity_set: Dict[str, Any], index: int) -> str:
        """Génère un nom descriptif pour l'entité"""
        parts = []

        if entity_set.get("breed"):
            parts.append(entity_set["breed"])

        sex = entity_set.get("sex", "as_hatched")
        if sex == "male":
            parts.append("mâle")
        elif sex == "female":
            parts.append("femelle")
        elif sex != "as_hatched":
            parts.append(sex)

        if entity_set.get("age_days"):
            parts.append(f"{entity_set['age_days']} jours")

        if not parts:
            return f"Entité {index + 1}"

        return " ".join(parts)

    @staticmethod
    def extract_metrics_from_docs(context_docs: List[Dict]) -> List[Dict[str, Any]]:
        """Extrait les métriques des documents de contexte avec gestion des unités"""
        metrics = []

        if context_docs and len(context_docs) > 0:
            first_doc = context_docs[0]
            logger.debug(f"First doc type: {type(first_doc)}")
            if isinstance(first_doc, dict):
                logger.debug(f"First doc keys: {list(first_doc.keys())}")

        for doc in context_docs:
            if not isinstance(doc, dict):
                logger.warning(f"Skipping non-dict doc: {type(doc)}")
                continue

            parsed_metric = ComparisonUtils.parse_metric_from_content(
                doc.get("content", "")
            )
            if parsed_metric:
                metadata = doc.get("metadata", {})
                sheet_name = metadata.get("sheet_name", "").lower()

                if "imperial" in sheet_name:
                    parsed_metric["unit_system"] = "imperial"
                else:
                    parsed_metric["unit_system"] = "metric"

                metric_dict = {
                    "value_numeric": parsed_metric.get("value", 0),
                    "unit": parsed_metric.get("unit", ""),
                    "metric_name": parsed_metric.get(
                        "metric_name", metadata.get("metric_name", "")
                    ),
                    "metadata": metadata,
                    "age": parsed_metric.get("age", 0),
                    "unit_system": parsed_metric.get("unit_system", "metric"),
                    "likely_unit_error": parsed_metric.get("likely_unit_error", False),
                    "probable_unit": parsed_metric.get("probable_unit", ""),
                }

                metrics.append(metric_dict)
                logger.debug(
                    f"Extracted: {metric_dict['metric_name']} = {metric_dict['value_numeric']} {metric_dict['unit']}"
                )

        logger.info(
            f"Successfully extracted {len(metrics)} metrics from {len(context_docs)} docs"
        )
        return metrics

    @staticmethod
    def parse_metric_from_content(content: str) -> Optional[Dict]:
        """Parse le contenu pour extraire les informations de métrique"""
        if not content:
            return None

        try:
            patterns = {
                "metric_name": r"\*\*(.*?)\*\*",
                "strain": r"Strain:\s*(.+)",
                "sex": r"Sex:\s*(.+)",
                "value": r"Value:\s*([\d.]+)",
                "unit": r"Value:.*?(grams?|kg|pounds?|lbs?)",
                "age": r"Age:\s*(\d+)\s*days?",
            }

            extracted = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    extracted[key] = match.group(1).strip()

            if "value" in extracted:
                try:
                    extracted["value"] = float(extracted["value"])
                except (ValueError, TypeError):
                    logger.warning(f"Valeur non numérique: {extracted.get('value')}")
                    return None

            if "age" in extracted:
                try:
                    extracted["age"] = int(extracted["age"])
                except (ValueError, TypeError):
                    extracted["age"] = 0

            if extracted.get("value") and extracted.get("unit"):
                value = extracted["value"]
                unit = extracted["unit"].lower()

                if "gram" in unit and value < 10:
                    extracted["likely_unit_error"] = True
                    extracted["probable_unit"] = "pounds"
                elif "pound" in unit and value > 100:
                    extracted["likely_unit_error"] = True
                    extracted["probable_unit"] = "grams"

            return extracted

        except Exception as e:
            logger.error(f"Erreur parsing métrique: {e}")
            return None

    @staticmethod
    def select_best_metric_by_age(
        metrics: List[Dict], target_age: int = None
    ) -> Optional[Dict]:
        """Sélectionne la meilleure métrique selon la proximité d'âge"""
        if not metrics:
            return None

        if not target_age:
            return metrics[0]

        def age_distance(metric):
            metric_age = metric.get("age", 0)
            if metric_age == 0:
                return float("inf")
            return abs(metric_age - target_age)

        sorted_metrics = sorted(metrics, key=age_distance)
        best_metric = sorted_metrics[0]

        if age_distance(best_metric) <= 3:
            logger.debug(
                f"Métrique sélectionnée: âge {best_metric.get('age')} (cible: {target_age})"
            )
            return best_metric
        else:
            logger.warning(f"Aucune métrique proche trouvée pour âge {target_age}")
            return sorted_metrics[0]

    @staticmethod
    def select_best_metric(
        metrics: List[Dict], entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sélectionne la meilleure métrique selon les critères"""
        if not metrics:
            return {}

        target_age = entities.get("age_days")

        if target_age:
            best_metric = ComparisonUtils.select_best_metric_by_age(metrics, target_age)
            if best_metric:
                return {
                    "value_numeric": best_metric.get(
                        "value_numeric", best_metric.get("value", 0)
                    ),
                    "unit": best_metric.get("unit", ""),
                    "metric_name": best_metric.get("metric_name", ""),
                    "metadata": best_metric.get("metadata", {}),
                    "unit_system": best_metric.get("unit_system", "metric"),
                    "age": best_metric.get("age", 0),
                }

        best = metrics[0]
        logger.debug(
            f"Selected best metric: {best.get('metric_name')} = "
            f"{best.get('value_numeric')} {best.get('unit')}"
        )
        return best

    @staticmethod
    def extract_common_context(
        results: List[Dict], comparison_entities: List[Dict]
    ) -> Dict[str, Any]:
        """Extrait le contexte commun aux deux résultats"""
        context = {}

        if not results or len(results) == 0:
            return context

        if results[0].get("entity_set"):
            first_entity_set = results[0]["entity_set"]

            if "age_days" in first_entity_set:
                context["age_days"] = first_entity_set["age_days"]

            if "sex" in first_entity_set:
                comparison_dimension = (
                    comparison_entities[0].get("_comparison_dimension")
                    if comparison_entities
                    else None
                )
                if comparison_dimension != "sex":
                    context["sex"] = first_entity_set["sex"]

        if results[0].get("data") and len(results[0]["data"]) > 0:
            first_metric = results[0]["data"][0]
            metadata = first_metric.get("metadata", {})

            if "age_min" in metadata and "age_days" not in context:
                context["age_days"] = metadata["age_min"]

        logger.debug(f"Extracted context: {context}")
        return context

    @staticmethod
    def convert_to_old_format(
        results: Dict[str, Any], comparison_entities: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Convertit le nouveau format de résultats vers l'ancien format"""
        old_format_results = []

        for entity_set in comparison_entities:
            entity_key = ComparisonUtils.generate_entity_key(entity_set)
            result = results.get(entity_key)

            if result and hasattr(result, "context_docs"):
                comparison_label = entity_set.get("_comparison_label", entity_key)
                comparison_dimension = entity_set.get(
                    "_comparison_dimension", "unknown"
                )

                metrics = ComparisonUtils.extract_metrics_from_docs(result.context_docs)

                if metrics:
                    clean_entities = {
                        k: v for k, v in entity_set.items() if not k.startswith("_")
                    }
                    best_metric = ComparisonUtils.select_best_metric(
                        metrics, clean_entities
                    )

                    old_format_result = {
                        comparison_dimension: comparison_label,
                        "label": comparison_label,
                        "data": [best_metric],
                        "all_metrics": metrics,
                        "entity_set": clean_entities,
                    }

                    old_format_results.append(old_format_result)

        return old_format_results

    @staticmethod
    def is_temporal_range_query(query: str) -> bool:
        """Détecte si la requête concerne une plage temporelle"""
        query_lower = query.lower()

        temporal_patterns = [
            r"entre\s+\d+\s+et\s+\d+\s+jours?",
            r"de\s+\d+\s+à\s+\d+\s+jours?",
            r"du\s+jour\s+\d+\s+au\s+jour\s+\d+",
            r"évolu(e|tion).*entre\s+\d+",
            r"gain.*entre\s+\d+",
            r"croissance.*entre\s+\d+",
            r"progression.*entre\s+\d+",
            r"variation.*entre\s+\d+",
            r"between\s+\d+\s+and\s+\d+\s+days?",
        ]

        for pattern in temporal_patterns:
            if re.search(pattern, query_lower):
                logger.debug(f"Temporal pattern detected: {pattern}")
                return True

        evolution_keywords = [
            "évolution",
            "evolution",
            "gain",
            "croissance",
            "growth",
            "progression",
        ]
        age_ranges = re.findall(r"\d+.*\d+.*jours?|\d+.*\d+.*days?", query_lower)

        if any(keyword in query_lower for keyword in evolution_keywords) and age_ranges:
            logger.debug("Evolution keywords + age ranges detected")
            return True

        return False

    @staticmethod
    def extract_metric_value(document: Dict) -> Optional[float]:
        """Extrait la valeur numérique d'un document"""
        try:
            metadata = document.get("metadata", {})
            if "value_numeric" in metadata:
                return float(metadata["value_numeric"])

            content = document.get("content", "")
            if content:
                value_match = re.search(r"Value:\s*([0-9.]+)", content)
                if value_match:
                    return float(value_match.group(1))

            return None

        except (ValueError, TypeError) as e:
            logger.warning(f"Error extracting metric value: {e}")
            return None

    @staticmethod
    def extract_unit_from_doc(document: Dict) -> str:
        """Extrait l'unité d'un document"""
        try:
            metadata = document.get("metadata", {})
            if "unit" in metadata:
                return metadata["unit"]

            content = document.get("content", "")
            if content:
                unit_match = re.search(r"Value:\s*[0-9.]+\s*(\w+)", content)
                if unit_match:
                    return unit_match.group(1)

            return ""

        except Exception as e:
            logger.warning(f"Error extracting unit: {e}")
            return ""
