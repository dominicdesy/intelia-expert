# -*- coding: utf-8 -*-
"""
rag_postgresql_validator.py - Validateur flexible pour requêtes PostgreSQL
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

        Returns:
            Dict avec status: "complete" | "incomplete_but_processable" | "needs_fallback"
        """

        entities = entities or {}
        missing = []
        suggestions = []
        enhanced_entities = entities.copy()

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
            r"(\d+)\s+semaines?",  # Sera multiplié par 7
        ]

        query_lower = query.lower()

        for pattern in age_patterns:
            match = re.search(pattern, query_lower)
            if match:
                age = int(match.group(1))
                # Convertir semaines en jours
                if "semaine" in pattern:
                    age *= 7
                if 0 <= age <= 150:  # Validation range
                    return age

        return None

    def _detect_metric_from_query(self, query: str) -> Optional[str]:
        """Détecte le type de métrique dans la requête"""
        query_lower = query.lower()

        metric_keywords = {
            "weight": ["poids", "weight", "masse"],
            "fcr": ["fcr", "conversion", "indice", "ic"],
            "mortality": ["mortalité", "mortality", "mort"],
            "production": ["production", "ponte", "œuf", "egg"],
            "feed": ["alimentation", "feed", "aliment"],
        }

        for metric_type, keywords in metric_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return metric_type

        return None

    def _generate_validation_help_message(
        self, query: str, missing: List[str], suggestions: List[str]
    ) -> str:
        """Génère un message d'aide pour requêtes incomplètes"""

        if "recommande" in query.lower() or "meilleur" in query.lower():
            return """Pour une recommandation personnalisée, précisez :

**Races disponibles :**
• Cobb 500 - Croissance rapide, bon FCR
• Ross 308 - Excellent rendement, robustesse  
• Hubbard JA87 - Adaptabilité, rusticité

**Contexte nécessaire :**
• Type de production (chair, ponte)
• Objectifs (croissance, conversion, mortalité)
• Conditions d'élevage

**Exemple :** "Recommande une race pour production intensive de chair"."""

        else:
            return f"""Informations manquantes : {', '.join(missing)}

**Suggestions :**
{chr(10).join(f'• {s}' for s in suggestions)}

**Exemple de requête complète :**
"Quel est le poids du Cobb 500 à 42 jours ?"

Reformulez avec plus de détails pour des données précises."""

    def check_data_availability_flexible(
        self, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Vérification flexible de disponibilité avec alternatives
        """

        breed = entities.get("breed", "").lower()
        age_days = entities.get("age_days")

        if not age_days or not breed:
            return {"available": True}  # Skip si données incomplètes

        # Ranges de données connus
        data_ranges = {
            "cobb 500": {"min": 0, "max": 56},
            "ross 308": {"min": 0, "max": 56},
            "hubbard ja87": {"min": 0, "max": 49},
        }

        range_info = data_ranges.get(breed)
        if not range_info:
            return {"available": True}  # Breed inconnu - laisser passer

        if range_info["min"] <= age_days <= range_info["max"]:
            return {"available": True}

        # Hors plage - proposer alternatives
        alternatives = []
        if age_days > range_info["max"]:
            alternatives.append(
                f"Données disponibles jusqu'à {range_info['max']} jours"
            )
            alternatives.append(f"Essayez: poids à {range_info['max']} jours")

        helpful_response = f"""L'âge demandé ({age_days} jours) est hors de la plage de données disponibles pour {breed.title()} ({range_info['min']}-{range_info['max']} jours).

**Alternatives disponibles :**
{chr(10).join(f'• {alt}' for alt in alternatives)}

**Données disponibles pour {breed.title()} :**
• Poids corporel (0-{range_info['max']} jours)
• FCR et conversion alimentaire  
• Mortalité et performance"""

        return {
            "available": False,
            "message": f"L'âge demandé ({age_days} jours) est hors de la plage de données disponibles pour {breed} ({range_info['min']}-{range_info['max']} jours).",
            "alternatives": alternatives,
            "helpful_response": helpful_response,
        }
