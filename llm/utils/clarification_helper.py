# -*- coding: utf-8 -*-
"""
clarification_helper.py - Helper pour messages de clarification intelligents
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
clarification_helper.py - Helper pour messages de clarification intelligents
Version 3.0 - Templates EN avec traduction LLM robuste
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from utils.llm_translator import get_llm_translator

logger = logging.getLogger(__name__)


class ClarificationHelper:
    """Gère les messages de clarification intelligents avec traduction dynamique"""

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
        # LLM-based translator pour traductions robustes
        self.translator = get_llm_translator()

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

    def _translate_message(self, message_en: str, language: str) -> str:
        """
        Traduit un message EN vers la langue cible via LLM

        Args:
            message_en: Message en anglais
            language: Code langue cible (fr, es, th, etc.)

        Returns:
            Message traduit avec qualité native
        """
        if language == "en":
            return message_en

        # Utiliser LLMTranslator pour traduction robuste
        return self.translator.translate(
            text=message_en,
            target_language=language,
            source_language="en"
        )

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
        if (
            any(kw in query_lower for kw in management_keywords)
            and len(query_lower.split()) < 10
        ):
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
            message_en = self.ambiguity_types[ambiguity_type]
            # Traduire le template EN vers la langue cible
            message = self._translate_message(message_en, language)
            if message:
                # Personnaliser le message en fonction des entités déjà connues
                message = self._customize_message(message, entities, missing_fields, language)
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
        Construit un message basé sur les champs manquants (avec traduction)

        Args:
            missing_fields: Liste des champs manquants
            language: Langue

        Returns:
            Message de clarification traduit
        """
        if not missing_fields:
            message_en = "Missing information to process the query."
            return self._translate_message(message_en, language)

        # Un seul champ manquant: message simple
        if len(missing_fields) == 1:
            field = missing_fields[0]
            template_en = self.missing_field_templates.get(field, "")

            if template_en:
                return self._translate_message(template_en, language)

            # Fallback générique
            message_en = f"Please specify the {field} to continue."
            return self._translate_message(message_en, language)

        # Plusieurs champs manquants: liste
        intro_en = "To help you best, I need details on:"
        intro = self._translate_message(intro_en, language)

        field_messages = []
        for field in missing_fields:
            template_en = self.missing_field_templates.get(field, "")

            if template_en:
                field_msg = self._translate_message(template_en, language)
            else:
                # Fallback
                field_msg = f"**{field.capitalize()}**"

            field_messages.append(f"- {field_msg}")

        return intro + "\n" + "\n".join(field_messages)

    def _customize_message(
        self, message: str, entities: Dict, missing_fields: List[str], language: str
    ) -> str:
        """
        Personnalise le message de clarification en ne demandant que ce qui manque vraiment

        Args:
            message: Message de clarification de base (déjà traduit)
            entities: Entités déjà extraites
            missing_fields: Champs manquants
            language: Langue

        Returns:
            Message personnalisé (traduit)
        """
        # Construire les éléments à demander (EN puis traduire)
        items_to_ask = []

        # Vérifier breed
        if "breed" in missing_fields and not entities.get("breed"):
            item_en = "**Breed**: Ross 308, Cobb 500, other?"
            items_to_ask.append(self._translate_message(item_en, language))

        # Vérifier age
        if "age" in missing_fields and not entities.get("age_days"):
            item_en = "**Age**: in days or weeks (e.g., 21 days, 35 days)?"
            items_to_ask.append(self._translate_message(item_en, language))

        # Vérifier sex
        if "sex" in missing_fields and not entities.get("sex"):
            item_en = "**Sex**: male, female, or as-hatched?"
            items_to_ask.append(self._translate_message(item_en, language))

        # Vérifier metric
        if "metric" in missing_fields and not entities.get("metric_type"):
            item_en = "**Metric**: body weight, FCR, mortality, uniformity?"
            items_to_ask.append(self._translate_message(item_en, language))

        # Si aucun item à demander, retourner message original
        if not items_to_ask:
            return message

        # Construire le message personnalisé avec traduction par morceaux
        # 🔧 FIX: Détecter le type de question pour adapter l'intro
        message_lower = message.lower()

        if "treatment" in message_lower or "protocol" in message_lower or "vaccin" in message_lower:
            # Question de traitement médical
            intro_part1 = self._translate_message("To recommend a treatment", language)
        elif "nutrition" in message_lower or "feed" in message_lower or "aliment" in message_lower:
            # Question de nutrition
            intro_part1 = self._translate_message("To provide nutritional advice", language)
        else:
            # Question de performance générale
            intro_part1 = self._translate_message("To analyze performance", language)

        # Ajouter le contexte (breed, disease, etc.)
        context_parts = []

        if entities.get("breed"):
            of_label = self._translate_message("of", language)
            # 🔧 FIX: Capitaliser le breed (ross 308 → Ross 308)
            breed = entities['breed']
            breed_capitalized = breed.title() if breed else breed
            context_parts.append(f"{of_label} {breed_capitalized}")

        # Si une maladie est mentionnée dans les entités ou le message
        if entities.get("disease"):
            for_label = self._translate_message("for", language)
            context_parts.append(f"{for_label} {entities['disease']}")

        if context_parts:
            intro_part2 = " " + " ".join(context_parts)
        else:
            intro_part2 = ""

        need_to_know = self._translate_message("I need to know", language)
        intro = f"{intro_part1}{intro_part2}, {need_to_know}:"

        custom_message = intro + "\n" + "\n".join(f"- {item}" for item in items_to_ask)

        return custom_message



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
