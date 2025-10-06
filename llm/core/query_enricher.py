# -*- coding: utf-8 -*-
"""
query_enricher.py - Enrichissement conversationnel des requêtes
Version 1.0 - Reformule les questions de suivi avec le contexte précédent
"""

import logging
import re
from utils.types import Dict, Set

logger = logging.getLogger(__name__)


class ConversationalQueryEnricher:
    """Enrichit les questions de suivi avec le contexte conversationnel"""

    def __init__(self):
        # Patterns de questions de suivi
        self.followup_patterns = {
            "fr": [
                r"^(quel|quelle|quels|quelles)\s+\w+\s*\??$",
                r"^et\s+(pour|chez|avec|à)",
                r"^(comment|pourquoi|où|quand)\s+\w+\s*\??$",
            ],
            "en": [
                r"^(what|which)\s+\w+\s*\??$",
                r"^(and|what\s+about)\s+",
                r"^(how|why|where|when)\s+\w+\s*\??$",
            ],
        }

        # Entités importantes
        self.entity_keywords = {
            "diseases": [
                "ascite",
                "ascites",
                "coccidiosis",
                "newcastle",
                "gumboro",
                "bronchite",
                "colibacillose",
            ],
            "breeds": ["ross", "cobb", "hubbard", "ross 308", "cobb 500"],
            "species": ["poulet", "broiler", "layer", "chair", "pondeuse"],
            "metrics": ["poids", "weight", "fcr", "mortalité", "ponte"],
            "treatments": ["traitement", "treatment", "vaccin", "antibiotique"],
        }

    def enrich(self, query: str, contextual_history: str, language: str = "fr") -> str:
        """Enrichit une query avec le contexte conversationnel"""

        if not query or not contextual_history:
            return query

        # 1. Détecter question de suivi
        if not self._is_followup_question(query, language):
            return query

        logger.info(f"Question de suivi détectée: '{query}'")

        # 2. Extraire entités du contexte
        entities = self._extract_entities_from_history(contextual_history)

        if not entities:
            return query

        # 3. Reformuler
        enriched = self._rewrite_query(query, entities, language)

        if enriched != query:
            logger.info(f"Query enrichie: '{query}' → '{enriched}'")

        return enriched

    def _is_followup_question(self, query: str, language: str) -> bool:
        """Détecte si c'est une question de suivi"""

        query_lower = query.lower().strip()

        # Critère 1: Très courte (< 6 mots)
        word_count = len(query_lower.split())
        if word_count > 6:
            return False

        # Critère 2: Match patterns de suivi
        patterns = self.followup_patterns.get(language, self.followup_patterns["fr"])

        for pattern in patterns:
            if re.search(pattern, query_lower):
                return True

        # Critère 3: Pronoms sans antécédent clair
        pronouns = ["il", "elle", "le", "la", "les", "celui", "celle", "ceux"]
        if any(pronoun in query_lower.split()[:3] for pronoun in pronouns):
            return True

        return False

    def _extract_entities_from_history(self, history: str) -> Dict[str, Set[str]]:
        """Extrait les entités du dernier échange"""

        entities = {
            "diseases": set(),
            "breeds": set(),
            "species": set(),
            "metrics": set(),
            "treatments": set(),
        }

        history_lower = history.lower()

        # Extraire chaque type d'entité
        for entity_type, keywords in self.entity_keywords.items():
            for keyword in keywords:
                if keyword in history_lower:
                    entities[entity_type].add(keyword)

        return entities

    def _rewrite_query(
        self, query: str, entities: Dict[str, Set[str]], language: str
    ) -> str:
        """Reformule la query en ajoutant le contexte"""

        query_lower = query.lower()
        additions = []

        # Cas 1: "Quel traitement ?" + maladie connue
        if "traitement" in query_lower or "treatment" in query_lower:
            if entities["diseases"]:
                disease = list(entities["diseases"])[0]
                additions.append(f"pour {disease}")
            if entities["species"]:
                species = list(entities["species"])[0]
                if species not in query_lower:
                    additions.append(f"chez {species}")

        # Cas 2: "Et pour X ?" → ajouter race/métrique du contexte
        if query_lower.startswith("et ") or query_lower.startswith("and "):
            if entities["breeds"]:
                breed = list(entities["breeds"])[0]
                if breed not in query_lower:
                    additions.insert(0, breed)
            if entities["metrics"]:
                metric = list(entities["metrics"])[0]
                if metric not in query_lower:
                    additions.append(metric)

        # Cas 3: Question vague → ajouter espèce si disponible
        if len(query.split()) < 4 and entities["species"]:
            species = list(entities["species"])[0]
            if species not in query_lower:
                additions.append(f"chez {species}")

        # Construire query enrichie
        if additions:
            enriched = query.rstrip("?") + " " + " ".join(additions)
            return enriched.strip() + ("?" if query.endswith("?") else "")

        return query

    def extract_entities_from_context(self, contextual_history: str, language: str = "fr") -> Dict[str, any]:
        """
        Extract structured entities from conversation history for router

        Args:
            contextual_history: Formatted conversation history
            language: Query language

        Returns:
            Dict with extracted entities (breed, age_days, sex, etc.)
        """
        if not contextual_history:
            return {}

        entities = {}
        history_lower = contextual_history.lower()

        # Extract breed
        breed_patterns = [
            (r"ross\s*308", "Ross 308"),
            (r"cobb\s*500", "Cobb 500"),
            (r"hubbard\s*(classic|flex)", "Hubbard"),
            (r"\bross\b", "Ross"),
            (r"\bcobb\b", "Cobb"),
        ]

        for pattern, breed_name in breed_patterns:
            if re.search(pattern, history_lower):
                entities["breed"] = breed_name
                logger.debug(f"Breed extracted from context: {breed_name}")
                break

        # Extract age in days
        age_patterns = [
            r"(\d+)\s*(?:jour|day)s?",
            r"(\d+)\s*j\b",
            r"day\s*(\d+)",
            r"à\s*(\d+)",
        ]

        for pattern in age_patterns:
            match = re.search(pattern, history_lower)
            if match:
                age_days = int(match.group(1))
                entities["age_days"] = age_days
                logger.debug(f"Age extracted from context: {age_days} days")
                break

        # Extract sex
        sex_keywords = {
            "mâle": "male",
            "male": "male",
            "femelle": "female",
            "female": "female",
            "mixte": "mixed",
            "mixed": "mixed",
        }

        for keyword, sex_value in sex_keywords.items():
            if keyword in history_lower:
                entities["sex"] = sex_value
                logger.debug(f"Sex extracted from context: {sex_value}")
                break

        # Extract metric type
        metric_keywords = {
            "poids": "weight",
            "weight": "weight",
            "fcr": "fcr",
            "conversion": "fcr",
            "mortalité": "mortality",
            "mortality": "mortality",
            "consommation": "feed_consumption",
        }

        for keyword, metric_value in metric_keywords.items():
            if keyword in history_lower:
                entities["metric_type"] = metric_value
                logger.debug(f"Metric extracted from context: {metric_value}")
                break

        if entities:
            logger.info(f"📦 Extracted {len(entities)} entities from context: {list(entities.keys())}")

        return entities


# Factory function
def create_query_enricher() -> ConversationalQueryEnricher:
    """Crée une instance de l'enrichisseur"""
    return ConversationalQueryEnricher()
