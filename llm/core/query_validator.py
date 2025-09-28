# -*- coding: utf-8 -*-
"""
query_validator.py - Validation de complétude des requêtes
Vérifie si une requête contient toutes les entités nécessaires
"""

import logging
from typing import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Résultat de validation"""

    is_complete: bool
    missing_entities: List[str]
    clarification_message: str
    confidence: float = 1.0


class QueryValidator:
    """Validateur de complétude des requêtes utilisateur"""

    # Entités requises par type de requête
    REQUIRED_ENTITIES = {
        "performance_query": ["breed", "age"],  # sex optionnel (défaut: as_hatched)
        "comparison_query": ["breed", "age"],  # Deux valeurs pour la dimension comparée
        "calculation_query": ["breed", "age"],
        "nutrition_query": ["breed"],  # Age optionnel pour nutrition
        "carcass_query": ["breed", "weight"],  # Poids vif pour rendement
    }

    # Métriques nécessitant un âge
    AGE_DEPENDENT_METRICS = {
        "body_weight",
        "weight",
        "poids",
        "feed_conversion_ratio",
        "fcr",
        "ic",
        "conversion",
        "daily_gain",
        "gain",
        "croissance",
        "feed_intake",
        "intake",
        "consommation",
    }

    def __init__(self):
        """Initialise le validateur"""
        pass

    def validate_query_completeness(
        self, query: str, entities: Dict[str, str]
    ) -> Dict[str, any]:
        """
        Vérifie si une requête contient toutes les entités nécessaires

        INTERFACE CORRIGÉE: Retourne un dict au lieu d'un objet ValidationResult

        Args:
            query: Requête originale de l'utilisateur
            entities: Entités extraites par EntityExtractor

        Returns:
            Dict avec clés: is_complete, missing_entities, confidence, clarification_message
        """
        # Détecter le type de requête
        query_type = self._detect_query_type(query)

        missing = self.identify_missing_entities(entities, query_type, query)

        if not missing:
            return {
                "is_complete": True,
                "missing_entities": [],
                "confidence": 1.0,
                "clarification_message": "",
            }

        # Générer message de clarification
        clarification = self.generate_clarification_prompt(missing, query)

        return {
            "is_complete": False,
            "missing_entities": missing,
            "confidence": 0.8,
            "clarification_message": clarification,
        }

    def _detect_query_type(self, query: str) -> str:
        """Détecte le type de requête basé sur le contenu"""
        query_lower = query.lower()

        if any(
            word in query_lower
            for word in ["compare", "comparaison", "vs", "versus", "différence"]
        ):
            return "comparison_query"
        elif any(word in query_lower for word in ["nutrition", "aliment", "régime"]):
            return "nutrition_query"
        elif any(word in query_lower for word in ["rendement", "carcasse", "abattage"]):
            return "carcass_query"
        elif any(word in query_lower for word in ["calcul", "calculer"]):
            return "calculation_query"
        else:
            return "performance_query"

    def identify_missing_entities(
        self, entities: Dict[str, str], query_type: str, query: str
    ) -> List[str]:
        """
        Identifie les entités manquantes pour une requête

        Args:
            entities: Entités extraites
            query_type: Type de requête
            query: Requête originale

        Returns:
            Liste d'entités manquantes
        """
        missing = []
        required = self.REQUIRED_ENTITIES.get(query_type, ["breed"])

        # Vérifier entités de base
        for entity in required:
            if entity not in entities or not entities[entity]:
                missing.append(entity)

        # Vérifier si métrique nécessite un âge
        if self._query_needs_age(query) and "age" not in entities:
            if "age" not in missing:
                missing.append("age")

        # Cas spécial: comparaison nécessite deux valeurs
        if "comparison" in query_type.lower() or self._is_comparative(query):
            if not self._has_comparison_dimension(entities):
                missing.append("comparison_dimension")

        return missing

    def _query_needs_age(self, query: str) -> bool:
        """Vérifie si la requête nécessite un âge"""
        query_lower = query.lower()

        # Vérifier présence de métriques dépendantes de l'âge
        for metric in self.AGE_DEPENDENT_METRICS:
            if metric in query_lower:
                return True

        # Patterns nécessitant un âge
        age_patterns = [
            "poids",
            "weight",
            "conversion",
            "fcr",
            "ic",
            "gain",
            "consommation",
            "intake",
        ]

        return any(pattern in query_lower for pattern in age_patterns)

    def _is_comparative(self, query: str) -> bool:
        """Détecte si c'est une requête comparative"""
        query_lower = query.lower()

        comparative_keywords = [
            "compare",
            "comparaison",
            "différence",
            "vs",
            "versus",
            "mieux",
            "meilleur",
            "plus",
            "moins",
            "entre",
            "et",
        ]

        return any(keyword in query_lower for keyword in comparative_keywords)

    def _has_comparison_dimension(self, entities: Dict[str, str]) -> bool:
        """Vérifie si les entités contiennent une dimension de comparaison claire"""

        # Si plusieurs souches mentionnées
        if "breed" in entities and "," in str(entities.get("breed", "")):
            return True

        # Si sexes multiples
        if "sex" in entities and "," in str(entities.get("sex", "")):
            return True

        # Si plusieurs âges
        if "age_days" in entities and "," in str(entities.get("age_days", "")):
            return True

        return False

    def generate_clarification_prompt(
        self, missing_entities: List[str], original_query: str
    ) -> str:
        """
        Génère un message de clarification pour les entités manquantes

        Args:
            missing_entities: Liste d'entités manquantes
            original_query: Requête originale

        Returns:
            Message de clarification
        """
        if not missing_entities:
            return ""

        # Messages de clarification par entité
        clarifications = {
            "breed": "Quelle souche vous intéresse? (Ross 308, Cobb 500, etc.)",
            "age": "À quel âge (en jours)?",
            "sex": "Quel sexe? (mâle, femelle, ou mixte)",
            "weight": "Quel poids vif?",
            "comparison_dimension": "Que souhaitez-vous comparer exactement?",
        }

        # Construire message
        if len(missing_entities) == 1:
            entity = missing_entities[0]
            return f"Pour répondre précisément à votre question, j'ai besoin d'une information supplémentaire: {clarifications.get(entity, entity)}?"
        else:
            messages = [clarifications.get(e, e) for e in missing_entities]
            return (
                "Pour répondre précisément, j'ai besoin de clarifications:\n- "
                + "\n- ".join(messages)
            )

    def validate_entity_values(self, entities: Dict[str, str]) -> Dict[str, bool]:
        """
        Valide les valeurs des entités extraites

        Args:
            entities: Entités extraites

        Returns:
            Dict avec validation par entité
        """
        validation = {}

        # Validation âge
        if "age_days" in entities:
            try:
                age = int(entities["age_days"])
                validation["age_days"] = 0 <= age <= 100  # Plage raisonnable
            except ValueError:
                validation["age_days"] = False

        # Validation souche
        if "breed" in entities:
            valid_breeds = ["308/308 FF", "500", "ross 308", "cobb 500", "ross", "cobb"]
            breed_lower = entities["breed"].lower()
            validation["breed"] = any(vb in breed_lower for vb in valid_breeds)

        # Validation sexe
        if "sex" in entities:
            valid_sex = [
                "male",
                "female",
                "as_hatched",
                "mixed",
                "mâle",
                "femelle",
                "mixte",
            ]
            validation["sex"] = entities["sex"].lower() in valid_sex

        return validation

    def is_ambiguous_query(self, query: str, entities: Dict[str, str]) -> bool:
        """
        Détecte si une requête est trop ambiguë

        Args:
            query: Requête utilisateur
            entities: Entités extraites

        Returns:
            True si ambiguë
        """
        query_lower = query.lower()

        # Patterns ambigus
        ambiguous_patterns = [
            "le meilleur poulet",
            "quel poulet",
            "lequel",
            "combien",
            "performances",
            "données",
        ]

        # Si requête très courte avec pattern ambigu
        if len(query.split()) < 5:
            if any(pattern in query_lower for pattern in ambiguous_patterns):
                # Et peu d'entités extraites
                if len(entities) < 2:
                    return True

        # Si aucune entité principale
        if "breed" not in entities and "strain" not in entities:
            return True

        return False
