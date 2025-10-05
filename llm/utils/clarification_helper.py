# -*- coding: utf-8 -*-
"""
clarification_helper.py - Helper pour messages de clarification intelligents
Charge et utilise clarification_strategies.json pour questions contextuelles
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ClarificationHelper:
    """Gère les messages de clarification intelligents"""

    def __init__(self, config_path: str = "config/clarification_strategies.json"):
        """
        Initialise le helper avec les stratégies de clarification

        Args:
            config_path: Chemin vers clarification_strategies.json
        """
        self.strategies = self._load_strategies(config_path)
        self.ambiguity_types = self.strategies.get("ambiguity_types", {})
        self.missing_field_templates = self.strategies.get(
            "missing_field_templates", {}
        )

    def _load_strategies(self, config_path: str) -> Dict:
        """Charge les stratégies depuis le fichier JSON"""
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(
                    f"clarification_strategies.json non trouvé: {config_path}"
                )
                return {}

            with open(path, "r", encoding="utf-8") as f:
                strategies = json.load(f)

            logger.info(
                f"Stratégies de clarification chargées: {len(strategies.get('ambiguity_types', {}))} types"
            )
            return strategies

        except Exception as e:
            logger.error(f"Erreur chargement clarification_strategies.json: {e}")
            return {}

    def detect_ambiguity_type(
        self, query: str, missing_fields: List[str], entities: Dict
    ) -> Optional[str]:
        """
        Détecte le type d'ambiguïté basé sur la query et les champs manquants

        Args:
            query: Question de l'utilisateur
            missing_fields: Liste des champs manquants
            entities: Entités déjà extraites

        Returns:
            Type d'ambiguïté ou None
        """
        query_lower = query.lower()

        # Nutrition: keywords + missing production_phase
        nutrition_keywords = [
            "aliment",
            "ration",
            "formule",
            "nutrition",
            "feed",
            "diet",
        ]
        if any(kw in query_lower for kw in nutrition_keywords) and (
            "age" in missing_fields or not entities.get("age_days")
        ):
            return "nutrition_ambiguity"

        # Santé: keywords + symptômes vagues
        health_keywords = [
            "maladie",
            "malade",
            "symptôme",
            "mort",
            "mortalité",
            "disease",
            "sick",
            "mortality",
        ]
        if any(kw in query_lower for kw in health_keywords) and (
            "age" in missing_fields or "breed" in missing_fields
        ):
            return "health_symptom_vague"

        # Performance: missing breed ou age pour métrique
        performance_keywords = [
            "poids",
            "fcr",
            "conversion",
            "performance",
            "weight",
            "gain",
        ]
        if any(kw in query_lower for kw in performance_keywords) and (
            "breed" in missing_fields or "age" in missing_fields
        ):
            return "performance_incomplete"

        # Environnement: ambiance/ventilation sans précisions
        environment_keywords = [
            "température",
            "ventilation",
            "ambiance",
            "humidité",
            "temperature",
            "climate",
        ]
        if any(kw in query_lower for kw in environment_keywords) and (
            "age" in missing_fields
        ):
            return "environment_vague"

        # Gestion: questions larges sans objectif clair
        management_keywords = [
            "gestion",
            "rentabilité",
            "améliorer",
            "optimiser",
            "management",
            "profitability",
            "improve",
        ]
        if any(kw in query_lower for kw in management_keywords) and len(query_lower.split()) < 10:
            return "management_broad"

        # Génétique: comparaison sans critères
        genetics_keywords = [
            "comparer",
            "vs",
            "versus",
            "meilleur",
            "différence",
            "compare",
            "better",
            "difference",
        ]
        if any(kw in query_lower for kw in genetics_keywords) and (
            "breed" in missing_fields or len(missing_fields) > 2
        ):
            return "genetics_incomplete"

        # Protocole: traitement/vaccin sans détails
        protocol_keywords = [
            "protocole",
            "vaccin",
            "traitement",
            "antibiotique",
            "protocol",
            "vaccine",
            "treatment",
        ]
        if any(kw in query_lower for kw in protocol_keywords) and (
            "age" in missing_fields or "breed" in missing_fields
        ):
            return "treatment_protocol_vague"

        return None

    def build_clarification_message(
        self,
        missing_fields: List[str],
        language: str,
        query: str = "",
        entities: Dict = None,
    ) -> str:
        """
        Construit un message de clarification intelligent

        Args:
            missing_fields: Champs manquants
            language: Langue (fr/en)
            query: Question originale (pour détecter ambiguïté)
            entities: Entités déjà extraites

        Returns:
            Message de clarification contextuel
        """
        if entities is None:
            entities = {}

        # Essayer de détecter un type d'ambiguïté spécifique
        ambiguity_type = None
        if query:
            ambiguity_type = self.detect_ambiguity_type(query, missing_fields, entities)

        # Si type détecté, utiliser la stratégie spécifique
        if ambiguity_type and ambiguity_type in self.ambiguity_types:
            strategy = self.ambiguity_types[ambiguity_type]
            message = strategy.get(language, strategy.get("fr", ""))
            if message:
                logger.info(
                    f"Clarification contextuelle: type={ambiguity_type}, lang={language}"
                )
                return message

        # Sinon, utiliser les templates de champs manquants
        return self._build_from_missing_fields(missing_fields, language)

    def _build_from_missing_fields(
        self, missing_fields: List[str], language: str
    ) -> str:
        """
        Construit un message basé sur les champs manquants

        Args:
            missing_fields: Liste des champs manquants
            language: Langue

        Returns:
            Message de clarification
        """
        if not missing_fields:
            return (
                "Informations manquantes pour traiter la requête."
                if language == "fr"
                else "Missing information to process the query."
            )

        # Un seul champ manquant: message simple
        if len(missing_fields) == 1:
            field = missing_fields[0]
            template = self.missing_field_templates.get(field, {})
            message = template.get(language, template.get("fr", ""))

            if message:
                return message

            # Fallback générique
            field_fr = self._translate_field_name(field)
            return (
                f"Veuillez préciser {field_fr} pour continuer."
                if language == "fr"
                else f"Please specify the {field} to continue."
            )

        # Plusieurs champs manquants: liste
        intro = (
            "Pour vous aider au mieux, j'ai besoin de précisions sur:"
            if language == "fr"
            else "To help you best, I need details on:"
        )

        field_messages = []
        for field in missing_fields:
            template = self.missing_field_templates.get(field, {})
            field_msg = template.get(language, template.get("fr", ""))

            if not field_msg:
                # Fallback
                field_fr = self._translate_field_name(field)
                field_msg = (
                    f"**{field_fr.capitalize()}**"
                    if language == "fr"
                    else f"**{field.capitalize()}**"
                )

            field_messages.append(f"- {field_msg}")

        return intro + "\n" + "\n".join(field_messages)

    def _translate_field_name(self, field: str) -> str:
        """Traduit le nom d'un champ en français"""
        translations = {
            "breed": "la race",
            "age": "l'âge",
            "sex": "le sexe",
            "gender": "le sexe",
            "weight": "le poids",
            "metric": "la métrique",
            "period": "la période",
            "date": "la date",
            "location": "le lieu",
            "building": "le bâtiment",
            "batch": "le lot",
            "production_phase": "la phase de production",
            "symptom": "les symptômes",
            "objective": "l'objectif",
        }
        return translations.get(field, field)


# Factory singleton
_clarification_helper_instance = None


def get_clarification_helper(
    config_path: str = "config/clarification_strategies.json",
) -> ClarificationHelper:
    """
    Récupère l'instance singleton du ClarificationHelper

    Args:
        config_path: Chemin vers clarification_strategies.json

    Returns:
        Instance ClarificationHelper
    """
    global _clarification_helper_instance

    if _clarification_helper_instance is None:
        _clarification_helper_instance = ClarificationHelper(config_path)

    return _clarification_helper_instance
