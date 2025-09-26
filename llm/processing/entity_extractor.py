# -*- coding: utf-8 -*-
"""
entity_extractor.py - Extracteur d'entités métier pour l'aviculture
CORRIGÉ: Imports modulaires selon nouvelle architecture + logique sexe/as-hatched
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extracteur d'entités métier - Version robuste avec normalisation cache et gestion sexe/as-hatched"""

    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        self.universal_slots = intents_config.get("universal_slots", {})

        # Patterns regex optimisés et étendus
        self.age_pattern = re.compile(
            r"\b(\d+)\s*(jour|day|semaine|week|j|sem|d|days|weeks)\b", re.IGNORECASE
        )
        self.weight_pattern = re.compile(
            r"\b(\d+(?:[.,]\d+)?)\s*(g|gramme|kg|kilogramme|gram|grams)\b",
            re.IGNORECASE,
        )
        self.percentage_pattern = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*%\b")
        self.temperature_pattern = re.compile(
            r"\b(\d+(?:[.,]\d+)?)\s*(?:°C|celsius|degré|degrees?)\b", re.IGNORECASE
        )
        self.flock_size_pattern = re.compile(
            r"\b(\d+(?:[\s,]\d{3})*)\s*(?:bird|birds|poulet|poulets|head)\b",
            re.IGNORECASE,
        )

        # NOUVEAU: Patterns spécialisés pour détection sexe avec fallback as-hatched
        self.sex_patterns = {
            "male": [
                "male",
                "mâle",
                "mâles",
                "masculin",
                "masculins",
                "coq",
                "coqs",
                "rooster",
                "roosters",
                "cock",
                "cocks",
                "mâle broiler",
                "male broiler",
                "mâle poulet",
                "male chicken",
            ],
            "female": [
                "female",
                "femelle",
                "femelles",
                "féminin",
                "féminins",
                "poule",
                "poules",
                "hen",
                "hens",
                "pullet",
                "pullets",
                "femelle broiler",
                "female broiler",
                "femelle poulet",
                "female chicken",
            ],
            "as_hatched": [
                "as-hatched",
                "ashatched",
                "as hatched",
                "mixed",
                "mixte",
                "mélangé",
                "non sexé",
                "non-sexé",
                "unsexed",
                "straight run",
                "straight-run",
                "mixed sex",
                "sexes mélangés",
                "les deux sexes",
                "both sexes",
            ],
        }

    def extract_entities(self, text: str) -> Dict[str, str]:
        """Extrait les entités métier avec validation renforcée et normalisation"""
        entities = {}
        text_lower = text.lower()

        try:
            # Extractions existantes améliorées
            entities.update(self._extract_lines(text_lower))
            entities.update(self._extract_ages(text))
            entities.update(self._extract_site_types(text_lower))
            entities.update(self._extract_metrics(text_lower))
            entities.update(self._extract_phases(text_lower))
            entities.update(self._extract_numeric_values(text))

            # Nouvelles extractions
            entities.update(self._extract_bird_types(text_lower))
            entities.update(self._extract_flock_size(text))
            entities.update(self._extract_environment_type(text_lower))

            # MODIFICATION MAJEURE: Nouvelle logique sexe avec fallback as-hatched
            entities.update(self._extract_sex_with_fallback(text_lower))

            # Normalisation pour clés cache
            entities = self._normalize_entities_for_cache(entities)

            # Validation et nettoyage
            entities = self._validate_entities(entities)

        except Exception as e:
            logger.error(f"Erreur extraction entités: {e}")

        return entities

    def _extract_sex_with_fallback(self, text: str) -> Dict[str, str]:
        """
        NOUVELLE MÉTHODE: Extrait le sexe avec logique de fallback vers as-hatched

        Logique:
        1. Si sexe explicite détecté (male/female) -> retourner ce sexe
        2. Si as-hatched/mixed détecté explicitement -> retourner as-hatched
        3. Si AUCUN sexe détecté -> fallback automatique vers as-hatched
        """

        # 1. Recherche sexe explicite (male/female)
        for sex_type in ["male", "female"]:
            patterns = self.sex_patterns[sex_type]
            if any(pattern in text for pattern in patterns):
                logger.debug(f"Sexe explicite détecté: {sex_type}")
                return {
                    "sex": sex_type,
                    "sex_specified": "true",
                    "sex_detection_method": "explicit",
                }

        # 2. Recherche as-hatched/mixed explicite
        as_hatched_patterns = self.sex_patterns["as_hatched"]
        if any(pattern in text for pattern in as_hatched_patterns):
            logger.debug("As-hatched explicite détecté")
            return {
                "sex": "as_hatched",
                "sex_specified": "true",
                "sex_detection_method": "explicit_mixed",
            }

        # 3. FALLBACK: Aucun sexe détecté -> défaut as-hatched
        logger.debug("Aucun sexe détecté, fallback vers as-hatched")
        return {
            "sex": "as_hatched",
            "sex_specified": "false",
            "sex_detection_method": "fallback_default",
        }

    def _normalize_entities_for_cache(self, entities: Dict[str, str]) -> Dict[str, str]:
        """Normalise les entités pour améliorer les clés de cache"""
        if "line" in entities:
            line = entities["line"]
            # Normalisation des lignées courantes
            if "ross 308" in line.lower():
                entities["line_normalized"] = "ross308"
            elif "cobb 500" in line.lower():
                entities["line_normalized"] = "cobb500"
            elif "hubbard" in line.lower():
                entities["line_normalized"] = "hubbard"
            else:
                entities["line_normalized"] = re.sub(r"[\s\-\.]+", "", line.lower())

        return entities

    def _extract_bird_types(self, text: str) -> Dict[str, str]:
        """Extrait les types d'oiseaux"""
        for canonical, aliases in (
            self.intents_config.get("aliases", {}).get("bird_type", {}).items()
        ):
            if canonical.lower() in text or any(
                alias.lower() in text for alias in aliases
            ):
                return {"bird_type": canonical}
        return {}

    def _extract_flock_size(self, text: str) -> Dict[str, str]:
        """Extrait la taille du troupeau"""
        matches = self.flock_size_pattern.findall(text)
        if matches:
            try:
                size_str = matches[0].replace(" ", "").replace(",", "")
                size = int(size_str)
                if 100 <= size <= 1000000:  # Validation réaliste
                    return {"flock_size": str(size)}
            except ValueError:
                pass
        return {}

    def _extract_environment_type(self, text: str) -> Dict[str, str]:
        """Extrait le type d'environnement d'élevage"""
        env_types = {
            "tunnel": ["tunnel", "tunnelisé"],
            "natural": ["natural", "naturel", "fenêtres"],
            "mechanical": ["mécanique", "mechanical", "extracteur"],
        }

        for env_type, keywords in env_types.items():
            if any(keyword in text for keyword in keywords):
                return {"environment": env_type}
        return {}

    def _validate_entities(self, entities: Dict[str, str]) -> Dict[str, str]:
        """Valide les entités extraites selon les universal_slots"""
        validated = {}

        for key, value in entities.items():
            slot_config = self.universal_slots.get(key)
            if not slot_config:
                validated[key] = value  # Garde les entités non définies
                continue

            # Validation par type
            if slot_config.get("type") == "int":
                try:
                    int_val = int(value)
                    min_val = slot_config.get("min", float("-inf"))
                    max_val = slot_config.get("max", float("inf"))
                    if min_val <= int_val <= max_val:
                        validated[key] = value
                except ValueError:
                    logger.warning(f"Valeur invalide pour {key}: {value}")

            # Validation par enum
            elif "enum" in slot_config:
                if value in slot_config["enum"]:
                    validated[key] = value
                else:
                    logger.warning(f"Valeur enum invalide pour {key}: {value}")

            else:
                validated[key] = value

        return validated

    def _extract_lines(self, text: str) -> Dict[str, str]:
        """Extrait les lignées avec correspondance floue améliorée et normalisation"""
        line_aliases = self.intents_config.get("aliases", {}).get("line", {})

        # Stratégie multi-niveaux pour améliorer la détection
        for canonical, aliases in line_aliases.items():
            canonical_lower = canonical.lower()

            # 1. Correspondance exacte
            if canonical_lower in text:
                return {"line": canonical}

            # 2. Correspondance par alias
            for alias in aliases:
                if alias.lower() in text:
                    return {"line": canonical}

            # 3. Correspondance par variantes normalisées
            canonical_normalized = re.sub(r"[\s\-\.]+", "", canonical_lower)
            if canonical_normalized in text.replace(" ", "").replace("-", ""):
                return {"line": canonical}

            # 4. Correspondance par mots-clés décomposés (ex: "ross" + "308")
            canonical_words = canonical_lower.split()
            if len(canonical_words) > 1:
                matches = sum(1 for word in canonical_words if word in text)
                if matches == len(canonical_words):
                    return {"line": canonical}

            # 5. Correspondance floue pour codes numériques
            numbers = re.findall(r"\d+", canonical)
            if numbers:
                for num in numbers:
                    if num in text:
                        # Vérifier le contexte pour éviter faux positifs
                        context = text[
                            max(0, text.find(num) - 15) : text.find(num) + 25
                        ]
                        brand_words = ["ross", "cobb", "hubbard", "isa", "lohmann"]
                        if any(brand in context for brand in brand_words):
                            return {"line": canonical}

        return {}

    def _extract_ages(self, text: str) -> Dict[str, str]:
        """Extrait les informations d'âge avec validation étendue"""
        entities = {}

        matches = self.age_pattern.findall(text)
        for number_str, unit in matches:
            try:
                age_value = int(number_str)

                # Validation étendue selon le contexte
                unit_lower = unit.lower()

                if unit_lower in ["jour", "day", "j", "d", "days"]:
                    if 0 <= age_value <= 600:  # Validation broilers + layers
                        entities["age_days"] = str(age_value)
                        entities["age_weeks"] = str(max(1, age_value // 7))
                elif unit_lower in ["semaine", "week", "sem", "weeks"]:
                    if 0 <= age_value <= 100:  # Validation étendue layers
                        entities["age_weeks"] = str(age_value)
                        entities["age_days"] = str(age_value * 7)

                break  # Premier âge trouvé

            except ValueError:
                continue

        return entities

    def _extract_site_types(self, text: str) -> Dict[str, str]:
        """Extrait les types de site d'élevage"""
        for canonical, aliases in (
            self.intents_config.get("aliases", {}).get("site_type", {}).items()
        ):
            if canonical.lower() in text or any(
                alias.lower() in text for alias in aliases
            ):
                return {"site_type": canonical}
        return {}

    def _extract_metrics(self, text: str) -> Dict[str, str]:
        """Extrait les métriques avec matching amélioré"""
        detected_metrics = []

        # Utiliser le vocabulaire de métriques construit
        vocab_extractor = getattr(self, "_vocab_extractor", None)
        if vocab_extractor and hasattr(vocab_extractor, "metrics_vocabulary"):
            for (
                metric_variant,
                metric_info,
            ) in vocab_extractor.metrics_vocabulary.items():
                if metric_variant in text.lower():
                    detected_metrics.append(metric_info["canonical_name"])
        else:
            # Fallback vers l'ancienne méthode
            for intent_config in self.intents_config.get("intents", {}).values():
                metrics = intent_config.get("metrics", {})
                for metric_name in metrics.keys():
                    metric_lower = metric_name.lower()

                    if metric_lower in text or metric_lower.replace("_", " ") in text:
                        detected_metrics.append(metric_name)

        if detected_metrics:
            return {"metrics": ",".join(detected_metrics[:5])}  # Limite étendue
        return {}

    def _extract_phases(self, text: str) -> Dict[str, str]:
        """Extrait les phases d'élevage"""
        for canonical, aliases in (
            self.intents_config.get("aliases", {}).get("phase", {}).items()
        ):
            if canonical.lower() in text or any(
                alias.lower() in text for alias in aliases
            ):
                return {"phase": canonical}
        return {}

    def _extract_numeric_values(self, text: str) -> Dict[str, str]:
        """Extrait les valeurs numériques avec contexte étendu"""
        entities = {}

        # Poids
        weight_matches = self.weight_pattern.findall(text)
        if weight_matches:
            value, unit = weight_matches[0]
            entities["weight_value"] = value.replace(",", ".")
            entities["weight_unit"] = unit.lower()

        # Pourcentages
        percentage_matches = self.percentage_pattern.findall(text)
        if percentage_matches:
            entities["percentage_value"] = percentage_matches[0].replace(",", ".")

        # Températures
        temp_matches = self.temperature_pattern.findall(text)
        if temp_matches:
            entities["temperature_value"] = temp_matches[0].replace(",", ".")

        return entities
