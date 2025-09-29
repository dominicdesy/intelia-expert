# -*- coding: utf-8 -*-
"""
query_preprocessor.py - Préprocesseur de requêtes refactoré
Version REFACTORÉE avec délégation aux modules spécialisés
✅ Conservation des méthodes non listées pour suppression
✅ Délégation à EntityExtractor, QueryClassifier, ValidationCore
"""

import logging
import re
from typing import Dict, Any, List, Optional

# NOUVEAUX IMPORTS - Modules spécialisés
from .entity_extractor import EntityExtractor
from .query_classifier import UnifiedQueryClassifier, QueryType, ClassificationResult
from .validation_core import ValidationCore

logger = logging.getLogger(__name__)


class QueryPreprocessor:
    """
    Préprocesseur de requêtes refactoré

    Délègue l'extraction/validation/classification aux modules spécialisés,
    mais conserve les méthodes utilitaires et de détection de patterns.
    """

    # Constantes conservées (non mentionnées dans la liste de suppression)
    INVALID_BREED_VALUES = {"as_hatched", "as-hatched", "mixed", "none", "", "null"}
    INVALID_METRIC_VALUES = {
        "as_hatched",
        "as-hatched",
        "mixed",
        "none",
        "",
        "null",
        "male",
        "female",
    }

    FRENCH_METRICS = {
        "gain quotidien moyen": "average_daily_gain",
        "gain moyen quotidien": "average_daily_gain",
        "gain quotidien": "daily_weight_gain",
        "gain de poids quotidien": "daily_weight_gain",
        "gain journalier": "daily_weight_gain",
        "gmq": "average_daily_gain",
        "gmo": "average_daily_gain",
        "adg": "average_daily_gain",
        "consommation cumulée": "cumulative_feed_intake",
        "consommation cumulative": "cumulative_feed_intake",
        "consommation totale": "cumulative_feed_intake",
        "aliment total": "cumulative_feed_intake",
        "quantité totale d'aliment": "cumulative_feed_intake",
        "combien d'aliment": "cumulative_feed_intake",
        "quantité d'aliment": "cumulative_feed_intake",
        "prévoir aliment": "cumulative_feed_intake",
        "besoin en aliment": "cumulative_feed_intake",
        "consommation d'aliment": "feed_intake",
        "ingestion": "feed_intake",
        "indice de consommation": "feed_conversion_ratio",
        "indice de conversion": "feed_conversion_ratio",
        "conversion alimentaire": "feed_conversion_ratio",
        "taux de conversion": "feed_conversion_ratio",
        "ic": "feed_conversion_ratio",
        "fcr": "feed_conversion_ratio",
        "poids vif": "body_weight",
        "poids corporel": "body_weight",
        "masse corporelle": "body_weight",
        "poids": "body_weight",
        "weight": "body_weight",
        "taux de mortalité": "mortality",
        "mortalité": "mortality",
        "mortality": "mortality",
        "pertes": "mortality",
        "décès": "mortality",
        "taux de ponte": "egg_production",
        "production d'œufs": "egg_production",
        "production": "egg_production",
        "ponte": "egg_production",
        "efficacité alimentaire": "feed_efficiency",
        "efficience alimentaire": "feed_efficiency",
        "rendement": "feed_efficiency",
    }

    PROJECTION_PATTERNS = [
        r"si (?:je|on) pars? (?:de|d\') (\d+)",
        r"en partant de (\d+)",
        r"à partir de (\d+)",
        r"starting from (\d+)",
        r"from age (\d+)",
    ]

    WEIGHT_PATTERNS = [
        r"à (\d+\.?\d*)\s*kg",
        r"à (\d+)\s*grammes?",
        r"(\d+\.?\d*)\s*kg",
        r"(\d+)\s*g\b",
        r"at (\d+\.?\d*)\s*kg",
        r"at (\d+)\s*grams?",
    ]

    def __init__(self):
        """Initialisation avec modules centralisés"""

        # Modules spécialisés
        self.entity_extractor = EntityExtractor()
        self.query_classifier = UnifiedQueryClassifier()
        self.validator = ValidationCore()

        # État interne
        self._cache = {}
        self._is_initialized = False
        self._current_query = ""

        logger.info("QueryPreprocessor initialisé avec modules spécialisés")

    async def initialize(self):
        """Initialisation et validation du preprocessor"""
        try:
            logger.info("Initialisation du Query Preprocessor refactoré...")
            self._is_initialized = True
            logger.info("Query Preprocessor initialisé avec succès")
            return self
        except Exception as e:
            logger.error(f"Erreur initialisation QueryPreprocessor: {e}")
            raise

    async def close(self):
        """Fermeture propre du preprocessor"""
        self._is_initialized = False
        self._cache.clear()
        logger.debug("Query Preprocessor fermé")

    async def preprocess_query(
        self, query: str, language: str = "fr"
    ) -> Dict[str, Any]:
        """
        Preprocessing simplifié - délègue aux modules spécialisés

        Args:
            query: Requête utilisateur
            language: Langue de la requête

        Returns:
            Dict avec query_type, entities, validation, etc.
        """

        # Cache check
        cache_key = f"{query}:{language}"
        if cache_key in self._cache:
            logger.debug(f"Cache hit pour: {query}")
            return self._cache[cache_key]

        # Stocker la requête courante
        self._current_query = query

        try:
            # 1. Classification de la requête
            classification = self.query_classifier.classify(query)
            logger.debug(f"Classification: {classification.query_type.value}")

            # 2. Extraction des entités
            extracted = self.entity_extractor.extract(query)
            entities_dict = extracted.to_dict()
            logger.debug(f"Entités extraites: {entities_dict}")

            # 3. Enrichissement avec détection de patterns
            query_patterns = self._detect_query_patterns(query)

            # 4. Enrichissement métrique française
            entities_dict = self._enhance_metric_detection(query, entities_dict)

            # 5. Extraction patterns avancés
            entities_dict = self._extract_advanced_patterns(query, entities_dict)

            # 6. Validation des entités
            validation = self.validator.validate_entities(entities_dict)
            logger.debug(
                f"Validation: valid={validation.is_valid}, conf={validation.confidence}"
            )

            # 7. Analyse des exigences strictes
            strict_requirements = self._analyze_strict_requirements(
                query, entities_dict
            )

            # 8. Construction des entités de comparaison
            comparison_entities = []
            if classification.is_comparative:
                comparison_entities = (
                    self._build_comparison_entities_from_classification(
                        classification, entities_dict
                    )
                )
            else:
                comparison_entities = self._build_comparison_entities_from_base(
                    entities_dict
                )

            # 9. Construction du résultat
            result = {
                "normalized_query": self._normalize_query_text(query),
                "original_query": query,
                "query_type": classification.query_type.value,
                "entities": entities_dict,
                # Informations comparatives
                "is_comparative": classification.is_comparative,
                "comparative_info": {
                    "type": (
                        classification.comparison_type.value
                        if classification.comparison_type
                        else None
                    ),
                    "requires_multiple_queries": classification.requires_multiple_queries,
                    "entities": classification.entities_to_compare,
                },
                "comparison_entities": comparison_entities,
                # Informations temporelles
                "temporal_range": classification.temporal_range,
                "is_temporal_range": classification.is_temporal_range,
                # Patterns détectés
                "query_patterns": query_patterns,
                "strict_requirements": strict_requirements,
                "requires_calculation": (
                    classification.is_comparative
                    or classification.is_temporal_range
                    or query_patterns.get("is_calculation", False)
                ),
                # Validation
                "validation": {
                    "is_valid": validation.is_valid,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                    "suggestions": validation.suggestions,
                    "confidence": validation.confidence,
                },
                # Métadonnées
                "confidence": extracted.confidence * validation.confidence,
                "routing": self._determine_routing(classification),
                "metadata": {
                    "classification": classification.to_dict(),
                    "extraction_source": extracted.extraction_source,
                    "has_explicit_entities": {
                        "breed": extracted.has_explicit_breed,
                        "age": extracted.has_explicit_age,
                        "sex": extracted.has_explicit_sex,
                    },
                },
            }

            # Cache du résultat
            self._cache[cache_key] = result

            logger.info(
                f"Query preprocessed: '{query}' -> type={classification.query_type.value}, "
                f"entities={len(entities_dict)}, valid={validation.is_valid}"
            )

            return result

        except Exception as e:
            logger.error(f"Erreur preprocessing: {e}", exc_info=True)
            return self._fallback_preprocessing(query, {}, {}, {})

        finally:
            self._current_query = ""

    def _normalize_query_text(self, query: str) -> str:
        """Normalise le texte de la requête"""

        corrections = {
            "IC": "conversion alimentaire",
            "FCR": "conversion alimentaire",
            "poid": "poids",
            "convertion": "conversion",
            "aliment": "alimentaire",
        }

        normalized = query
        for wrong, correct in corrections.items():
            normalized = re.sub(
                rf"\b{re.escape(wrong)}\b", correct, normalized, flags=re.IGNORECASE
            )

        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def _determine_routing(self, classification: ClassificationResult) -> str:
        """Détermine le routing basé sur la classification"""

        routing_map = {
            QueryType.TEMPORAL_RANGE: "postgresql",
            QueryType.COMPARATIVE: "postgresql",
            QueryType.RECOMMENDATION: "postgresql",
            QueryType.CALCULATION: "postgresql",
            QueryType.OPTIMIZATION: "postgresql",
            QueryType.METRIC: "postgresql",
            QueryType.DIAGNOSTIC: "weaviate",
            QueryType.GENERAL: "weaviate",
        }

        return routing_map.get(classification.query_type, "postgresql")

    def _detect_query_patterns(self, query: str) -> Dict[str, Any]:
        """Détecte les patterns spéciaux dans la requête"""

        age_patterns = [
            r"à \s+(\d+)\s+jours?",
            r"(\d+)\s+jours?",
            r"de\s+(\d+)\s+jours?",
            r"(\d+)\s*j\b",
            r"day\s+(\d+)",
            r"(\d+)\s+days?",
            r"(\d+)-?jours?",
            r"(\d+)\s+semaines?",
        ]

        query_lower = query.lower()
        extracted_age = None

        for pattern in age_patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    if "semaine" in pattern:
                        age = age * 7
                    if 0 <= age <= 150:
                        extracted_age = age
                        logger.debug(
                            f"Age détecté: {age} jours via pattern '{pattern}'"
                        )
                        break
                except ValueError:
                    continue

        patterns = {
            "is_calculation": self._is_calculation_query(query_lower),
            "is_temporal_reverse": self._is_temporal_reverse_query(query_lower),
            "is_optimization": self._is_optimization_query(query_lower),
            "is_economic": self._is_economic_query(query_lower),
            "is_planning": self._is_planning_query(query_lower),
            "extracted_age": extracted_age,
        }

        if patterns["is_calculation"]:
            patterns["calculation_type"] = self._identify_calculation_type(query_lower)

        if patterns["is_planning"]:
            patterns["flock_size"] = self._extract_flock_size(query)

        if patterns["is_temporal_reverse"]:
            patterns["target_value"] = self._extract_target_value(query)

        return patterns

    def _is_calculation_query(self, query_lower: str) -> bool:
        """Détecte requêtes nécessitant des calculs"""
        calculation_keywords = [
            "projette",
            "projection",
            "calcul",
            "calculer",
            "total",
            "totaux",
            "somme",
            "entre",
            "de X à Y",
            "from X to Y",
            "combien",
            "how much",
            "how many",
        ]
        return any(keyword in query_lower for keyword in calculation_keywords)

    def _is_temporal_reverse_query(self, query_lower: str) -> bool:
        """Détecte requêtes de recherche inversée (valeur → âge)"""
        reverse_patterns = [
            "quel âge",
            "à quel âge",
            "combien de jours",
            "quand atteint",
            "when reach",
            "at what age",
            "pour atteindre",
            "to reach",
        ]
        return any(pattern in query_lower for pattern in reverse_patterns)

    def _is_optimization_query(self, query_lower: str) -> bool:
        """Détecte requêtes d'optimisation"""
        optimization_keywords = [
            "optimal",
            "optimis",
            "meilleur",
            "best",
            "maximis",
            "minimis",
            "maximize",
            "minimize",
            "idéal",
            "ideal",
        ]
        return any(keyword in query_lower for keyword in optimization_keywords)

    def _is_economic_query(self, query_lower: str) -> bool:
        """Détecte requêtes économiques"""
        economic_keywords = [
            "coût",
            "cout",
            "cost",
            "prix",
            "price",
            "rentabilité",
            "rentabilite",
            "profitability",
            "marge",
            "margin",
            "roi",
            "€",
            "$",
            "dollar",
            "euro",
        ]
        return any(keyword in query_lower for keyword in economic_keywords)

    def _is_planning_query(self, query_lower: str) -> bool:
        """Détecte requêtes de planification de troupeau"""
        planning_patterns = [
            r"\d+[\s,]?\d{3}.*poulet",
            r"\d+[\s,]?\d{3}.*bird",
            r"pour \d+.*oiseaux",
            r"for \d+.*chickens",
        ]
        return any(re.search(pattern, query_lower) for pattern in planning_patterns)

    def _identify_calculation_type(self, query_lower: str) -> str:
        """Identifie le type de calcul demandé"""
        if "projection" in query_lower or "projette" in query_lower:
            return "projection"
        elif "total" in query_lower or "somme" in query_lower:
            return "total"
        elif "entre" in query_lower or "from" in query_lower:
            return "range_calculation"
        elif "taux" in query_lower or "rate" in query_lower:
            return "rate_calculation"
        else:
            return "general_calculation"

    def _extract_flock_size(self, query: str) -> Optional[int]:
        """Extrait la taille du troupeau"""
        numbers = re.findall(r"\b(\d{1,3}(?:[,\s]\d{3})*|\d+)\b", query)
        for num_str in numbers:
            num = int(num_str.replace(",", "").replace(" ", ""))
            if num > 100:
                return num
        return None

    def _extract_target_value(self, query: str) -> Optional[float]:
        """Extrait valeur cible pour recherche inversée"""
        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:kg|g|grammes?|kilos?)",
            r"(\d+(?:\.\d+)?)\s*(?=\s|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    def _enhance_metric_detection(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Détection améliorée des métriques françaises"""

        if (
            entities.get("metric_type")
            and entities["metric_type"] not in self.INVALID_METRIC_VALUES
        ):
            return entities

        query_lower = query.lower()

        for pattern in sorted(self.FRENCH_METRICS.keys(), key=len, reverse=True):
            if pattern in query_lower:
                detected = self.FRENCH_METRICS[pattern]
                logger.debug(f"Métrique FR détectée: '{pattern}' → {detected}")
                entities["metric_type"] = detected
                entities["metric_detection_method"] = "french_dictionary"
                break

        if not entities.get("metric_type"):
            basic_patterns = {
                r"\bpoids\b": "body_weight",
                r"\bweight\b": "body_weight",
                r"\bfcr\b": "feed_conversion_ratio",
                r"\bic\b": "feed_conversion_ratio",
                r"\bmortalit[eé]\b": "mortality",
            }

            for pattern, metric in basic_patterns.items():
                if re.search(pattern, query_lower):
                    logger.debug(
                        f"Métrique basique détectée: pattern '{pattern}' → {metric}"
                    )
                    entities["metric_type"] = metric
                    entities["metric_detection_method"] = "regex_fallback"
                    break

        return entities

    def _extract_advanced_patterns(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extraction des patterns avancés (projection, poids cible)"""

        query_lower = query.lower()

        for pattern in self.PROJECTION_PATTERNS:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    start_age = int(match.group(1))
                    if 0 <= start_age <= 150:
                        entities["start_age"] = start_age
                        entities["is_projection"] = True
                        logger.debug(f"Projection détectée: start_age={start_age}")
                        break
                except (ValueError, IndexError):
                    continue

        for pattern in self.WEIGHT_PATTERNS:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    weight_value = float(match.group(1))

                    if "kg" in pattern:
                        weight_value *= 1000
                    elif weight_value < 50:
                        weight_value *= 1000

                    if 100 <= weight_value <= 10000:
                        entities["target_weight"] = weight_value
                        logger.debug(f"Poids cible détecté: {weight_value}g")
                        break
                except (ValueError, IndexError):
                    continue

        return entities

    def _analyze_strict_requirements(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Analyse si la requête nécessite des correspondances strictes"""

        strict_requirements = {
            "strict_sex_match": False,
            "strict_age_match": False,
            "strict_breed_match": False,
            "exclude_imperial_units": True,
        }

        if entities.get("explicit_sex_request", False):
            strict_requirements["strict_sex_match"] = True
            logger.debug("Demande de correspondance sexe stricte détectée")

        precision_keywords = [
            "exactement",
            "précisément",
            "spécifiquement",
            "uniquement",
            "seulement",
            "exactly",
            "specifically",
            "only",
            "precisely",
        ]

        query_lower = query.lower()
        if any(keyword in query_lower for keyword in precision_keywords):
            strict_requirements.update(
                {
                    "strict_sex_match": True,
                    "strict_age_match": True,
                    "strict_breed_match": True,
                }
            )
            logger.debug("Demande de correspondance stricte détectée via mots-clés")

        precise_age_patterns = [
            r"à \s+(\d+)\s+jours?",
            r"at\s+(\d+)\s+days?",
            r"day\s+(\d+)",
            r"jour\s+(\d+)",
        ]

        if any(re.search(pattern, query_lower) for pattern in precise_age_patterns):
            strict_requirements["strict_age_match"] = True
            logger.debug("Demande d'âge précis détectée")

        return strict_requirements

    def _build_comparison_entities_from_base(
        self, base_entities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Construit les entités individuelles pour comparaison"""

        entities_list = []

        if "sex" in base_entities:
            sex_str = str(base_entities.get("sex", ""))
            if "," in sex_str:
                sexes = [s.strip() for s in sex_str.split(",")]
                for sex in sexes:
                    entity = base_entities.copy()
                    entity["sex"] = sex
                    entity["explicit_sex_request"] = True
                    entities_list.append(entity)
                logger.info(f"Comparaison sexes splittée: {len(entities_list)} entités")
                return entities_list

        if "breed" in base_entities:
            breed_str = str(base_entities.get("breed", ""))
            if breed_str and "," in breed_str:
                breeds = [b.strip() for b in breed_str.split(",")]
                for breed in breeds:
                    entity = base_entities.copy()
                    entity["breed"] = breed
                    entities_list.append(entity)
                logger.info(
                    f"Comparaison breeds splittée: {len(entities_list)} entités"
                )
                return entities_list

        if "age_days" in base_entities:
            age_val = base_entities.get("age_days")
            if isinstance(age_val, list) and len(age_val) > 1:
                for age in age_val:
                    entity = base_entities.copy()
                    entity["age_days"] = age
                    entity["is_age_range"] = False
                    entities_list.append(entity)
                logger.info(f"Comparaison âges splittée: {len(entities_list)} entités")
                return entities_list

        return [base_entities]

    def _build_comparison_entities_from_classification(
        self, classification: ClassificationResult, base_entities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Construit les entités de comparaison depuis la classification"""

        if not classification.entities_to_compare:
            return self._build_comparison_entities_from_base(base_entities)

        entity_sets = []

        for comp_entity in classification.entities_to_compare:
            dimension = comp_entity.get("dimension")
            values = comp_entity.get("values", [])

            if dimension == "sex" and len(values) >= 2:
                for sex_value in values:
                    entity_set = base_entities.copy()
                    entity_set["sex"] = sex_value
                    entity_set["explicit_sex_request"] = True
                    entity_sets.append(entity_set)

            elif dimension == "breed" and len(values) >= 2:
                for breed_value in values:
                    entity_set = base_entities.copy()
                    entity_set["breed"] = breed_value.strip()
                    entity_sets.append(entity_set)

            elif dimension == "age_days" and len(values) >= 2:
                for age_value in values:
                    entity_set = base_entities.copy()
                    try:
                        entity_set["age_days"] = int(age_value)
                        entity_sets.append(entity_set)
                    except (ValueError, TypeError):
                        logger.warning(f"Âge invalide ignoré: {age_value}")

        if not entity_sets:
            entity_sets = [base_entities]

        logger.info(f"Jeux d'entités construits: {len(entity_sets)}")
        return entity_sets

    def _fallback_preprocessing(
        self,
        query: str,
        comparative_info: Dict,
        query_patterns: Dict,
        strict_requirements: Dict,
    ) -> Dict[str, Any]:
        """Preprocessing de secours en cas d'erreur"""

        logger.warning("Utilisation du preprocessing de secours")

        return {
            "normalized_query": self._normalize_query_text(query),
            "query_type": "general",
            "entities": {},
            "routing": "postgresql",
            "confidence": 0.5,
            "is_comparative": False,
            "comparative_info": comparative_info,
            "requires_calculation": False,
            "comparison_entities": [],
            "query_patterns": query_patterns,
            "strict_requirements": strict_requirements,
            "preprocessing_fallback": True,
        }

    def should_use_strict_matching(self, preprocessing_result: Dict[str, Any]) -> bool:
        """Détermine si les requêtes doivent utiliser la correspondance stricte"""

        strict_reqs = preprocessing_result.get("strict_requirements", {})

        if any(strict_reqs.values()):
            return True

        if preprocessing_result.get("comparative_info", {}).get(
            "is_comparative", False
        ):
            return False

        return preprocessing_result.get("entities", {}).get(
            "explicit_sex_request", False
        )

    def get_status(self) -> Dict[str, Any]:
        """Status du preprocessor"""
        return {
            "initialized": self._is_initialized,
            "cache_size": len(self._cache),
            "modules": {
                "entity_extractor": self.entity_extractor is not None,
                "query_classifier": self.query_classifier is not None,
                "validator": self.validator is not None,
            },
            "capabilities": {
                "entity_extraction": True,
                "query_classification": True,
                "entity_validation": True,
                "comparative_detection": True,
                "temporal_range_detection": True,
                "pattern_detection": True,
                "strict_matching_support": True,
                "french_metrics_dictionary": True,
                "advanced_pattern_extraction": True,
            },
            "supported_french_metrics": len(self.FRENCH_METRICS),
            "architecture": "modular_refactored",
            "version": "2.0.0",
        }
