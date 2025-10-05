# -*- coding: utf-8 -*-
"""
entity_manager.py - Entity management for context enrichment
Handles entity descriptions, performance metrics, and context building for response generation.
"""

import logging
import json
from pathlib import Path
from utils.types import Dict, List, Optional
from .models import ContextEnrichment
from config.config import ENTITY_CONTEXTS

logger = logging.getLogger(__name__)


class EntityDescriptionsManager:
    """
    Centralized manager for entity descriptions used in contextual enrichment.

    This class loads and manages entity descriptions from a JSON configuration file,
    providing access to genetic line descriptions, species characteristics, production
    phases, and performance metrics used to enrich LLM prompts with domain-specific context.

    Attributes:
        descriptions: Dictionary mapping entity types to their detailed descriptions
        performance_metrics: Dictionary mapping performance categories to related keywords

    Example:
        >>> manager = EntityDescriptionsManager()
        >>> desc = manager.get_entity_description("line", "ross")
        >>> print(desc)
        "lignée à croissance rapide, optimisée pour le rendement carcasse"
    """

    def __init__(self, descriptions_path: Optional[str] = None):
        """
        Initialize the entity descriptions manager and load descriptions from JSON.

        Args:
            descriptions_path: Custom path to entity_descriptions.json. If not provided,
                             defaults to llm/config/entity_descriptions.json

        The loader will:
        1. Try to load from the specified or default path
        2. Fall back to hardcoded descriptions if file not found
        3. Log appropriate warnings/errors during the process
        """
        self.descriptions = {}
        self.performance_metrics = {}

        # Determine the configuration file path
        if descriptions_path:
            config_path = Path(descriptions_path)
        else:
            # Default path: llm/config/entity_descriptions.json
            config_path = (
                Path(__file__).parent.parent / "config" / "entity_descriptions.json"
            )

        # Load descriptions from JSON file
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.descriptions = data.get("entity_contexts", {})
                    self.performance_metrics = data.get("performance_metrics", {})
                logger.info(f"✅ Entity descriptions loaded from {config_path}")
            else:
                logger.warning(
                    f"⚠️ File {config_path} not found, using fallback descriptions"
                )
                self._load_fallback_descriptions()
        except Exception as e:
            logger.error(f"❌ Error loading entity_descriptions.json: {e}")
            self._load_fallback_descriptions()

    def _load_fallback_descriptions(self):
        """
        Load fallback entity descriptions when JSON file is unavailable.

        Provides hardcoded descriptions for:
        - Genetic lines: ross, cobb, hubbard, isa, lohmann
        - Species: broiler, layer, breeder
        - Production phases: starter, grower, finisher, laying, breeding

        Also includes performance metrics categories with related keywords.
        """
        self.descriptions = {
            "line": {
                "ross": "lignée à croissance rapide, optimisée pour le rendement carcasse",
                "cobb": "lignée équilibrée performance/robustesse, bonne conversion alimentaire",
                "hubbard": "lignée rustique, adaptée à l'élevage extensif et labels qualité",
                "isa": "lignée ponte, optimisée pour la production d'œufs",
                "lohmann": "lignée ponte, excellence en persistance de ponte",
            },
            "species": {
                "broiler": "poulet de chair, objectifs: poids vif, FCR, rendement carcasse",
                "layer": "poule pondeuse, objectifs: intensité de ponte, qualité œuf, persistance",
                "breeder": "reproducteur, objectifs: fertilité, éclosabilité, viabilité descendance",
            },
            "phase": {
                "starter": "phase démarrage (0-10j), croissance critique, thermorégulation",
                "grower": "phase croissance (11-24j), développement squelettique et musculaire",
                "finisher": "phase finition (25j+), optimisation du poids final et FCR",
                "laying": "phase ponte, maintien de la production et qualité œuf",
                "breeding": "phase reproduction, optimisation fertilité et éclosabilité",
            },
        }

        self.performance_metrics = {
            "weight": [
                "poids vif",
                "gain de poids",
                "homogénéité",
                "courbe de croissance",
            ],
            "fcr": [
                "indice de consommation",
                "efficacité alimentaire",
                "coût alimentaire",
            ],
            "mortality": [
                "mortalité",
                "viabilité",
                "causes de mortalité",
                "prévention",
            ],
            "production": [
                "intensité de ponte",
                "pic de ponte",
                "persistance",
                "qualité œuf",
            ],
            "feed": ["consommation", "appétence", "digestibilité", "conversion"],
        }

    def get_entity_description(
        self, entity_type: str, entity_value: str
    ) -> Optional[str]:
        """
        Retrieve the description for a specific entity.

        Args:
            entity_type: Type of entity (e.g., "line", "species", "phase")
            entity_value: Value of the entity (e.g., "ross", "broiler", "starter")

        Returns:
            Description string if found, None otherwise

        Example:
            >>> manager.get_entity_description("line", "Ross")
            "lignée à croissance rapide, optimisée pour le rendement carcasse"

        Note:
            Entity values are case-insensitive (converted to lowercase for lookup)
        """
        entity_value_lower = entity_value.lower()
        return self.descriptions.get(entity_type, {}).get(entity_value_lower)

    def get_metric_keywords(self, metric: str) -> List[str]:
        """
        Retrieve keywords associated with a performance metric.

        Args:
            metric: Name of the metric (e.g., "weight", "fcr", "mortality")

        Returns:
            List of related keywords for the metric, empty list if not found

        Example:
            >>> manager.get_metric_keywords("weight")
            ["poids vif", "gain de poids", "homogénéité", "courbe de croissance"]
        """
        return self.performance_metrics.get(metric, [])

    def get_all_metrics(self) -> Dict[str, List[str]]:
        """
        Return all performance metrics with their associated keywords.

        Returns:
            Copy of the complete performance metrics dictionary

        Example:
            >>> metrics = manager.get_all_metrics()
            >>> print(metrics.keys())
            dict_keys(['weight', 'fcr', 'mortality', 'production', 'feed'])
        """
        return self.performance_metrics.copy()


class EntityEnrichmentBuilder:
    """
    Builder for creating context enrichment based on detected entities.

    This class analyzes intent detection results and constructs a ContextEnrichment
    object containing structured contextual information to enhance LLM prompts with
    domain-specific knowledge about genetic lines, production phases, metrics, etc.

    Attributes:
        entity_descriptions: EntityDescriptionsManager instance for accessing entity data

    Example:
        >>> builder = EntityEnrichmentBuilder()
        >>> enrichment = builder.build_enrichment(intent_result)
        >>> print(enrichment.entity_context)
        "Lignée ross: lignée à croissance rapide, optimisée pour le rendement carcasse"
    """

    def __init__(self, descriptions_path: Optional[str] = None):
        """
        Initialize the enrichment builder with an entity descriptions manager.

        Args:
            descriptions_path: Optional custom path to entity_descriptions.json,
                             passed through to EntityDescriptionsManager
        """
        self.entity_descriptions = EntityDescriptionsManager(descriptions_path)

        # Merge with ENTITY_CONTEXTS from config for backward compatibility
        if ENTITY_CONTEXTS:
            for entity_type, contexts in ENTITY_CONTEXTS.items():
                if entity_type not in self.entity_descriptions.descriptions:
                    self.entity_descriptions.descriptions[entity_type] = {}
                self.entity_descriptions.descriptions[entity_type].update(contexts)

    def build_enrichment(self, intent_result) -> ContextEnrichment:
        """
        Build context enrichment from detected entities in intent analysis results.

        This method extracts entities from the intent result and constructs a comprehensive
        ContextEnrichment object containing:
        - Entity context: Descriptions of detected genetic lines, species, and phases
        - Metric focus: Identified performance metrics and related keywords
        - Temporal context: Age-based production phase insights
        - Species focus: Species-specific production objectives
        - Performance indicators: Relevant KPIs based on detected entities
        - Confidence boosters: Flags indicating what contextual information was identified

        Args:
            intent_result: Intent detection result object containing:
                - detected_entities: Dict of entity type to entity value
                - expanded_query: String of query expanded with synonyms/context

        Returns:
            ContextEnrichment object with all detected contextual information

        Example:
            >>> intent = IntentResult(
            ...     detected_entities={"line": "ross", "age_days": 35, "species": "broiler"},
            ...     expanded_query="What is the target weight for Ross broilers?"
            ... )
            >>> enrichment = builder.build_enrichment(intent)
            >>> print(enrichment.entity_context)
            "Lignée ross: lignée à croissance rapide; Type broiler: poulet de chair"
            >>> print(enrichment.temporal_context)
            "Phase de finition - Optimisation FCR et qualité carcasse"

        Note:
            Returns empty ContextEnrichment if intent_result is None or parsing fails
        """
        try:
            entities = getattr(intent_result, "detected_entities", {})

            # Build entity context using EntityDescriptionsManager
            entity_contexts = []

            if "line" in entities:
                description = self.entity_descriptions.get_entity_description(
                    "line", entities["line"]
                )
                if description:
                    entity_contexts.append(f"Lignée {entities['line']}: {description}")

            if "species" in entities:
                description = self.entity_descriptions.get_entity_description(
                    "species", entities["species"]
                )
                if description:
                    entity_contexts.append(f"Type {entities['species']}: {description}")

            if "phase" in entities:
                description = self.entity_descriptions.get_entity_description(
                    "phase", entities["phase"]
                )
                if description:
                    entity_contexts.append(f"Phase {entities['phase']}: {description}")

            # Build metric focus
            metric_focus = ""
            detected_metrics = []
            expanded_query = getattr(intent_result, "expanded_query", "")

            all_metrics = self.entity_descriptions.get_all_metrics()
            for metric, keywords in all_metrics.items():
                metric_in_entities = metric in entities
                metric_in_query = (
                    any(kw in expanded_query.lower() for kw in keywords)
                    if expanded_query
                    else False
                )

                if metric_in_entities or metric_in_query:
                    detected_metrics.extend(keywords)

            if detected_metrics:
                metric_focus = f"Focus métriques: {', '.join(detected_metrics[:3])}"

            # Build temporal context based on age
            temporal_context = ""
            if "age_days" in entities:
                age = entities["age_days"]
                if isinstance(age, (int, float)):
                    if age <= 7:
                        temporal_context = "Période critique première semaine - Focus thermorégulation et démarrage"
                    elif age <= 21:
                        temporal_context = "Phase de croissance rapide - Développement osseux et musculaire"
                    elif age <= 35:
                        temporal_context = (
                            "Phase d'optimisation - Maximisation du gain de poids"
                        )
                    else:
                        temporal_context = (
                            "Phase de finition - Optimisation FCR et qualité carcasse"
                        )

            # Build species focus
            species_focus = ""
            if "species" in entities:
                species = entities["species"].lower()
                if "broiler" in species or "chair" in species:
                    species_focus = (
                        "Objectifs chair: poids vif, FCR, rendement, qualité carcasse"
                    )
                elif "layer" in species or "ponte" in species:
                    species_focus = "Objectifs ponte: intensité, persistance, qualité œuf, viabilité"

            # Build performance indicators
            performance_indicators = []
            if "weight" in entities or (
                "poids" in expanded_query.lower() if expanded_query else False
            ):
                performance_indicators.extend(
                    ["poids vif", "gain quotidien", "homogénéité du lot"]
                )
            if "fcr" in entities or any(
                term in expanded_query.lower() if expanded_query else False
                for term in ["conversion", "indice"]
            ):
                performance_indicators.extend(
                    ["FCR", "consommation", "efficacité alimentaire"]
                )

            # Build confidence boosters
            confidence_boosters = []
            if entity_contexts:
                confidence_boosters.append("Contexte lignée/espèce identifié")
            if temporal_context:
                confidence_boosters.append("Phase d'élevage précisée")
            if metric_focus:
                confidence_boosters.append("Métriques cibles identifiées")

            return ContextEnrichment(
                entity_context="; ".join(entity_contexts),
                metric_focus=metric_focus,
                temporal_context=temporal_context,
                species_focus=species_focus,
                performance_indicators=performance_indicators,
                confidence_boosters=confidence_boosters,
            )

        except Exception as e:
            logger.warning(f"Error building entity enrichment: {e}")
            return ContextEnrichment("", "", "", "", [], [])


__all__ = [
    "EntityDescriptionsManager",
    "EntityEnrichmentBuilder",
]
