# -*- coding: utf-8 -*-
"""
Base handler with common utilities for all query handlers
"""

import logging
from utils.types import Dict, Any, List

logger = logging.getLogger(__name__)


class BaseQueryHandler:
    """Handler de base avec fonctionnalités communes"""

    def __init__(self):
        self.postgresql_system = None
        self.weaviate_core = None
        self.postgresql_validator = None

    def configure(self, **kwargs):
        """Configure le handler avec les modules nécessaires"""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _should_skip_postgresql_for_age(self, entities: Dict[str, Any]) -> bool:
        """
        Vérifie si l'âge est hors plage broilers typique
        Broilers typiquement <= 56 jours, on élargit à 60j pour sécurité
        """
        age = entities.get("age_days")
        if age and age > 60:
            logger.info(
                f"Age {age}j hors plage broilers -> fallback Weaviate recommande"
            )
            return True
        return False

    def _is_qualitative_query(self, entities: Dict[str, Any]) -> bool:
        """
        Vérifie si la requête est qualitative (sans âge/métrique précis)
        """
        has_age = entities.get("age_days") is not None
        has_metric = entities.get("metric_type") is not None

        return not has_age and not has_metric

    def _is_result_relevant_to_query(
        self, query: str, context_docs: List[Dict], entities: Dict[str, Any]
    ) -> bool:
        """
        Vérifie si les documents retournés sont pertinents pour la query

        Args:
            query: Question originale
            context_docs: Documents retournés par PostgreSQL
            entities: Entités extraites

        Returns:
            True si pertinent, False sinon
        """
        if not context_docs:
            logger.debug("Aucun document à vérifier - non pertinent")
            return False

        # Extraire les mots-clés importants de la query (lowercase)
        query_lower = query.lower()

        # Liste de termes qui indiquent une query qualitative (non métrique)
        qualitative_terms = [
            "traitement",
            "vaccin",
            "maladie",
            "symptôme",
            "diagnostic",
            "prévention",
            "antibiotique",
            "protocole",
            "soins",
            "sanitaire",
            "hygiène",
            "infection",
            "virus",
            "bactérie",
            "pathologie",
            "treatment",
            "vaccine",
            "disease",
            "symptom",
            "prevention",
            "antibiotic",
            "protocol",
            "care",
            "sanitary",
            "hygiene",
            "infection",
            "virus",
            "bacteria",
            "pathology",
            "behandlung",
            "impfstoff",
            "krankheit",
            "symptom",
            "tratamiento",
            "vacuna",
            "enfermedad",
            "síntoma",
            "trattamento",
            "vaccino",
            "malattia",
            "sintomo",
        ]

        # Termes métriques quantitatifs
        metric_terms = [
            "feed intake",
            "weight",
            "fcr",
            "gain",
            "grams",
            "consumption",
            "consommation",
            "poids",
            "gain",
            "grammes",
            "futterverzehr",
            "gewicht",
            "zunahme",
            "consumo",
            "peso",
            "ganancia",
            "consumo",
            "peso",
            "guadagno",
        ]

        # Vérifier si la query a une intention qualitative
        has_qualitative_intent = any(term in query_lower for term in qualitative_terms)

        if has_qualitative_intent:
            # Examiner le contenu des premiers documents
            doc_contents = " ".join(
                [str(doc.get("content", "")) for doc in context_docs[:5]]
            ).lower()

            # Vérifier si les docs contiennent des informations qualitatives
            has_qualitative_content = any(
                term in doc_contents for term in qualitative_terms
            )

            # Vérifier si les docs ne contiennent QUE des métriques
            has_only_metrics = (
                any(term in doc_contents for term in metric_terms)
                and not has_qualitative_content
            )

            if has_only_metrics:
                logger.info(
                    f"🔍 PERTINENCE: Documents contiennent UNIQUEMENT des métriques, "
                    f"mais query cherche info qualitative ('{query[:50]}...') → NON PERTINENT"
                )
                return False

            logger.debug(
                "✅ PERTINENCE: Documents contiennent info qualitative → PERTINENT"
            )
            return True

        # Pour les queries métriques, toujours considérer comme pertinent
        logger.debug("✅ PERTINENCE: Query métrique, documents acceptés → PERTINENT")
        return True

    def _extract_filters_from_entities(
        self, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extrait les filtres depuis les entités détectées

        Args:
            entities: Dictionnaire des entités extraites par le preprocessing

        Returns:
            Dict contenant les filtres à appliquer (species, genetic_line, etc.)
        """
        filters = {}

        # Extraire species
        if "species" in entities and entities["species"]:
            filters["species"] = entities["species"]
            logger.info(f"🐔 Species filter extracted: {entities['species']}")

        # Extraire genetic_line si présent
        if "genetic_line" in entities and entities["genetic_line"]:
            filters["genetic_line"] = entities["genetic_line"]
            logger.info(f"🧬 Genetic line filter extracted: {entities['genetic_line']}")

        return filters
