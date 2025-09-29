# -*- coding: utf-8 -*-
"""
rag_postgresql_validator.py - Validateur flexible pour requêtes PostgreSQL
VERSION CORRIGÉE: Préserve tous les champs originaux non détectés
"""

import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class PostgreSQLValidator:
    """Validateur intelligent avec auto-détection et alternatives"""

    def flexible_query_validation(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validation flexible qui essaie de compléter les requêtes incomplètes

        CORRECTION CRITIQUE: Préserve TOUS les champs originaux qui ne sont pas auto-détectés

        Returns:
            Dict avec status: "complete" | "incomplete_but_processable" | "needs_fallback"
        """

        entities = entities or {}
        missing = []
        suggestions = []

        # 🔧 CORRECTION: Créer une vraie copie des entités originales
        enhanced_entities = dict(entities) if entities else {}

        # Vérifier breed
        if not entities.get("breed"):
            detected_breed = self._detect_breed_from_query(query)
            if detected_breed:
                enhanced_entities["breed"] = detected_breed
                logger.debug(f"Auto-detected breed: {detected_breed}")
            else:
                missing.append("breed")
                suggestions.append("Spécifiez une race (Cobb 500, Ross 308, etc.)")

        # Vérifier âge
        if not entities.get("age_days"):
            detected_age = self._detect_age_from_query(query)
            if detected_age:
                enhanced_entities["age_days"] = detected_age
                logger.debug(f"Auto-detected age: {detected_age} days")
            else:
                # Pour certaines requêtes, l'âge n'est pas critique
                if any(
                    word in query.lower()
                    for word in ["recommande", "meilleur", "compare", "général"]
                ):
                    pass  # Requête générale - pas besoin d'âge spécifique
                else:
                    missing.append("age")
                    suggestions.append("Précisez un âge (21 jours, 42 jours, etc.)")

        # Vérifier métrique
        if not entities.get("metric_type"):
            detected_metric = self._detect_metric_from_query(query)
            if detected_metric:
                enhanced_entities["metric_type"] = detected_metric
                logger.debug(f"Auto-detected metric: {detected_metric}")

        # 🔧 CORRECTION CRITIQUE: Préserver TOUS les champs originaux non détectés
        # Ceci est essentiel pour les comparaisons où 'sex' vient du comparison_handler
        for key, value in (entities or {}).items():
            if key not in enhanced_entities and value is not None:
                enhanced_entities[key] = value
                logger.debug(f"Preserved original field: {key} = {value}")

        # Déterminer le statut
        if not missing:
            return {"status": "complete", "enhanced_entities": enhanced_entities}

        elif len(missing) <= 1 and ("breed" not in missing):
            # Si juste l'âge ou métrique manque, on peut souvent traiter
            return {
                "status": "incomplete_but_processable",
                "message": f"Autoriser la requête sans {', '.join(missing)} spécifique",
                "enhanced_entities": enhanced_entities,
                "missing": missing,
            }

        else:
            # Trop d'informations manquantes
            helpful_message = self._generate_validation_help_message(
                query, missing, suggestions
            )
            return {
                "status": "needs_fallback",
                "missing": missing,
                "suggestions": suggestions,
                "helpful_message": helpful_message,
            }

    def _detect_breed_from_query(self, query: str) -> Optional[str]:
        """Détecte la race dans le texte de la requête"""
        query_lower = query.lower()

        breed_patterns = {
            "cobb 500": ["cobb 500", "cobb500", "c500"],
            "ross 308": ["ross 308", "ross308", "r308"],
            "hubbard ja87": ["hubbard", "ja87", "j87"],
        }

        for canonical_breed, patterns in breed_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    return canonical_breed

        return None

    def _detect_age_from_query(self, query: str) -> Optional[int]:
        """Détecte l'âge dans le texte de la requête"""
        age_patterns = [
            r"à\s+(\d+)\s+jours?",
            r"(\d+)\s+jours?",
            r"(\d+)\s*j\b",
            r"(\d+)\s+semaines?",
            r"at\s+(\d+)\s+days?",
        ]

        for pattern in age_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                if "semaine" in pattern.lower() or "week" in pattern.lower():
                    age = age * 7
                return age

        return None

    def _detect_metric_from_query(self, query: str) -> Optional[str]:
        """Détecte le type de métrique dans la requête"""
        query_lower = query.lower()

        metric_keywords = {
            "weight": ["poids", "weight", "body weight"],
            "feed_conversion": [
                "conversion",
                "fcr",
                "ic",
                "feed conversion",
                "conversion alimentaire",
            ],
            "mortality": ["mortalité", "mortality", "viabilité", "viability"],
        }

        for metric_type, keywords in metric_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return metric_type

        return None

    def _generate_validation_help_message(
        self, query: str, missing: List[str], suggestions: List[str]
    ) -> str:
        """Génère un message d'aide pour validation"""
        return (
            f"Informations manquantes pour traiter votre requête : {', '.join(missing)}. "
            f"Suggestions : {' '.join(suggestions)}"
        )

    def check_data_availability_flexible(
        self, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Vérifie si les données demandées sont disponibles
        Version flexible avec alternatives
        """

        # Plages d'âges disponibles par race (approximatif)
        age_ranges = {
            "cobb 500": (0, 56),
            "ross 308": (0, 56),
            "hubbard ja87": (0, 56),
        }

        breed = entities.get("breed", "").lower() if entities.get("breed") else None
        age_days = entities.get("age_days")

        if not breed or not age_days:
            return {"available": True}

        age = int(age_days) if isinstance(age_days, (int, str)) else None
        if not age:
            return {"available": True}

        # Vérifier la plage d'âge
        for breed_key, (min_age, max_age) in age_ranges.items():
            if breed_key in breed:
                if min_age <= age <= max_age:
                    return {"available": True}
                else:
                    # Proposer des alternatives
                    alternatives = []
                    if age < min_age:
                        alternatives.append(f"{min_age} jours (âge minimum)")
                    if age > max_age:
                        alternatives.append(f"{max_age} jours (âge maximum)")

                    return {
                        "available": False,
                        "alternatives": alternatives,
                        "helpful_response": f"Données non disponibles pour {breed} à {age} jours. Alternatives : {', '.join(alternatives)}",
                    }

        return {"available": True}
