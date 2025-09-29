# -*- coding: utf-8 -*-
"""
rag_postgresql_validator.py - Validateur flexible pour requêtes PostgreSQL
VERSION FINALE CORRIGÉE: Préserve tous les champs originaux + Logs diagnostiques
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

        CORRECTION FINALE: Commence toujours par les entités ORIGINALES,
        puis enrichit SEULEMENT les champs manquants avec auto-détection.
        Cela garantit que 'sex' et autres champs du comparison_handler sont préservés.

        Returns:
            Dict avec status: "complete" | "incomplete_but_processable" | "needs_fallback"
        """

        entities = entities or {}
        missing = []
        suggestions = []

        # 🔥 LOG CRITIQUE #1 : Ce qui ARRIVE au validator
        logger.debug(f"🔍 VALIDATOR INPUT entities: {entities}")
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'sex' present: {'sex' in entities}, value: {entities.get('sex')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'breed' present: {'breed' in entities}, value: {entities.get('breed')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'age_days' present: {'age_days' in entities}, value: {entities.get('age_days')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'explicit_sex_request' present: {'explicit_sex_request' in entities}, value: {entities.get('explicit_sex_request')}"
        )

        # 🟢 CORRECTION CRITIQUE: Copier TOUTES les entités originales en priorité
        # Cela préserve automatiquement 'sex', 'explicit_sex_request', etc.
        enhanced_entities = dict(entities) if entities else {}

        # 🔥 LOG CRITIQUE #2 : Juste après dict(entities)
        logger.debug(f"🔍 enhanced_entities AFTER dict(entities): {enhanced_entities}")
        logger.debug(
            f"🔍 AFTER COPY - 'sex' present: {'sex' in enhanced_entities}, value: {enhanced_entities.get('sex')}"
        )
        logger.debug(
            f"🔍 AFTER COPY - 'explicit_sex_request' present: {'explicit_sex_request' in enhanced_entities}"
        )

        # 🟢 Auto-détection breed SEULEMENT si absent dans les entités originales
        if not enhanced_entities.get("breed"):
            logger.debug("🔍 Breed ABSENT, auto-detecting from query...")
            detected_breed = self._detect_breed_from_query(query)
            if detected_breed:
                enhanced_entities["breed"] = detected_breed
                logger.debug(f"✅ Auto-detected breed: {detected_breed}")
            else:
                logger.debug("❌ No breed detected in query")
                missing.append("breed")
                suggestions.append("Spécifiez une race (Cobb 500, Ross 308, etc.)")
        else:
            logger.debug(
                f"🔍 Breed PRESENT: '{enhanced_entities.get('breed')}', skipping auto-detection"
            )

        # 🟢 Auto-détection age SEULEMENT si absent dans les entités originales
        if not enhanced_entities.get("age_days"):
            logger.debug("🔍 Age ABSENT, auto-detecting from query...")
            detected_age = self._detect_age_from_query(query)
            if detected_age:
                enhanced_entities["age_days"] = detected_age
                logger.debug(f"✅ Auto-detected age: {detected_age} days")
            else:
                logger.debug("❌ No age detected in query")
                # Pour certaines requêtes, l'âge n'est pas critique
                if any(
                    word in query.lower()
                    for word in ["recommande", "meilleur", "compare", "général"]
                ):
                    logger.debug("🔍 General query, age not critical")
                    pass  # Requête générale - pas besoin d'âge spécifique
                else:
                    missing.append("age")
                    suggestions.append("Précisez un âge (21 jours, 42 jours, etc.)")
        else:
            logger.debug(
                f"🔍 Age PRESENT: '{enhanced_entities.get('age_days')}', skipping auto-detection"
            )

        # 🟢 Auto-détection metric SEULEMENT si absent dans les entités originales
        if not enhanced_entities.get("metric_type"):
            logger.debug("🔍 Metric ABSENT, auto-detecting from query...")
            detected_metric = self._detect_metric_from_query(query)
            if detected_metric:
                enhanced_entities["metric_type"] = detected_metric
                logger.debug(f"✅ Auto-detected metric: {detected_metric}")
            else:
                logger.debug("❌ No metric detected in query")
        else:
            logger.debug(
                f"🔍 Metric PRESENT: '{enhanced_entities.get('metric_type')}', skipping auto-detection"
            )

        # 🔥 LOG CRITIQUE #3 : Avant de retourner
        logger.debug(f"🔍 enhanced_entities FINAL before return: {enhanced_entities}")
        logger.debug(
            f"🔍 FINAL - 'sex' present: {'sex' in enhanced_entities}, value: {enhanced_entities.get('sex')}"
        )
        logger.debug(
            f"🔍 FINAL - 'explicit_sex_request' present: {'explicit_sex_request' in enhanced_entities}, value: {enhanced_entities.get('explicit_sex_request')}"
        )

        # 🔥 VÉRIFICATION CRITIQUE : Comparaison INPUT vs OUTPUT
        input_keys = set(entities.keys())
        output_keys = set(enhanced_entities.keys())
        lost_keys = input_keys - output_keys

        if lost_keys:
            logger.error(f"❌❌❌ VALIDATOR LOST KEYS: {lost_keys}")
            logger.error(f"❌ INPUT had: {input_keys}")
            logger.error(f"❌ OUTPUT has: {output_keys}")

            # 🟢 CORRECTION : RESTAURER les champs perdus
            for key in lost_keys:
                enhanced_entities[key] = entities[key]
                logger.warning(f"⚠️ RESTORED lost key '{key}': {entities[key]}")

            logger.debug(f"🔍 enhanced_entities AFTER restoration: {enhanced_entities}")
        else:
            logger.debug("✅ No keys lost, all fields preserved")

        # 🟢 Log de debug pour vérifier que tous les champs sont préservés
        if entities:
            preserved_fields = [k for k in entities.keys() if k in enhanced_entities]
            if preserved_fields:
                logger.debug(f"✅ Preserved original fields: {preserved_fields}")

        # Déterminer le statut
        if not missing:
            logger.debug("✅ Validation complete, returning enhanced_entities")
            return {"status": "complete", "enhanced_entities": enhanced_entities}

        elif len(missing) <= 1 and ("breed" not in missing):
            # Si juste l'âge ou métrique manque, on peut souvent traiter
            logger.debug(f"⚠️ Validation incomplete but processable, missing: {missing}")
            return {
                "status": "incomplete_but_processable",
                "message": f"Autoriser la requête sans {', '.join(missing)} spécifique",
                "enhanced_entities": enhanced_entities,
                "missing": missing,
            }

        else:
            # Trop d'informations manquantes
            logger.debug(f"❌ Validation needs fallback, missing: {missing}")
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
