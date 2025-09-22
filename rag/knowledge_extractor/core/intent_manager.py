"""
Gestionnaire des intents basé sur intents.json - VERSION CORRIGÉE
Support complet des lignées génétiques multiples
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import re


class IntentManager:
    """Gestionnaire des intents avec normalisation automatique multi-lignées"""

    def __init__(self, intents_file_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.intents_data = self._load_intents_data(intents_file_path)

    def _load_intents_data(self, intents_file_path: str = None) -> Dict:
        """Charge les données d'intents depuis le fichier JSON"""
        if intents_file_path and Path(intents_file_path).exists():
            try:
                with open(intents_file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Erreur chargement intents.json: {e}")

        # Recherche automatique
        search_paths = [
            Path(__file__).parent.parent / "intents.json",
            Path(__file__).parent / "intents.json",
            Path.cwd() / "intents.json",
        ]

        for path in search_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.logger.info(f"Intents chargé depuis: {path}")
                        return json.load(f)
                except Exception:
                    continue

        self.logger.warning("intents.json non trouvé - métadonnées basiques")
        return {}

    def normalize_genetic_line(self, raw_text: str) -> str:
        """Normalise une lignée génétique selon les alias - VERSION CORRIGÉE"""
        if not raw_text or not isinstance(raw_text, str):
            return "unknown"

        if not self.intents_data or "aliases" not in self.intents_data:
            return self._fallback_genetic_normalization(raw_text)

        line_aliases = self.intents_data["aliases"].get("line", {})
        text_lower = raw_text.lower().strip()

        # Nettoyage du texte
        text_clean = re.sub(r"[^\w\s-]", "", text_lower)

        # 1. Recherche exacte du nom canonique
        for canonical_line, aliases in line_aliases.items():
            if canonical_line.lower() == text_clean:
                self.logger.debug(
                    f"Correspondance exacte: '{raw_text}' -> '{canonical_line}'"
                )
                return canonical_line

        # 2. Recherche dans les alias
        best_match = None
        best_score = 0

        for canonical_line, aliases in line_aliases.items():
            score = 0

            # Score pour correspondance partielle dans le nom canonique
            canonical_words = canonical_line.lower().split()
            for word in canonical_words:
                if word in text_clean:
                    score += 8

            # Score pour correspondance dans les alias
            for alias in aliases:
                alias_lower = alias.lower()

                # Correspondance exacte d'alias
                if alias_lower == text_clean:
                    score += 20

                # Correspondance partielle d'alias
                elif alias_lower in text_clean or text_clean in alias_lower:
                    score += 10

                # Correspondance par mots
                alias_words = alias_lower.split()
                for word in alias_words:
                    if len(word) > 2 and word in text_clean:
                        score += 5

            if score > best_score:
                best_score = score
                best_match = canonical_line

        if best_match and best_score >= 5:
            self.logger.debug(
                f"Correspondance trouvée: '{raw_text}' -> '{best_match}' (score: {best_score})"
            )
            return best_match

        # 3. Fallback avec patterns spécifiques
        normalized = self._fallback_genetic_normalization(raw_text)
        self.logger.debug(f"Normalisation fallback: '{raw_text}' -> '{normalized}'")
        return normalized

    def _fallback_genetic_normalization(self, raw_text: str) -> str:
        """Normalisation fallback pour les cas non couverts par intents.json"""
        text_lower = raw_text.lower().strip()

        # Patterns spécifiques pour les lignées courantes
        genetic_patterns = {
            "ross 308": [
                r"ross\s*308",
                r"r-?308",
                r"ross.*308",
                r"aviagen.*ross",
                r"ross(?!\s*7)",
            ],
            "ross 708": [r"ross\s*708", r"r-?708", r"ross.*708"],
            "cobb 500": [
                r"cobb\s*500",
                r"c-?500",
                r"cobb.*500",
                r"cobb(?!\s*[47])",
                r"cobb(?:\s|$)",
            ],
            "cobb 700": [r"cobb\s*700", r"c-?700", r"cobb.*700"],
            "cobb 400": [r"cobb\s*400", r"c-?400", r"cobb.*400"],
            "hubbard classic": [r"hubbard.*classic", r"classic", r"hclassic"],
            "hubbard flex": [r"hubbard.*flex", r"flex", r"hflex"],
            "isa brown": [r"isa.*brown", r"isa(?!\s*white)", r"isa\s+brown"],
            "lohmann brown": [r"lohmann.*brown", r"lohmann(?!\s*white)", r"lb(?:\s|$)"],
        }

        for canonical_line, patterns in genetic_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return canonical_line

        # Si aucun pattern ne correspond, retourner le texte nettoyé
        return text_lower if text_lower else "unknown"

    def detect_intent_category(self, content: str) -> Dict[str, Any]:
        """Détecte la catégorie d'intent d'un contenu - VERSION AMÉLIORÉE"""
        if not self.intents_data or "intents" not in self.intents_data:
            return {"primary_intent": "general", "confidence": 0.3}

        content_lower = content.lower()
        intent_scores = {}

        # Analyse par mots-clés des intents
        for intent_name, intent_config in self.intents_data["intents"].items():
            score = 0

            # Score basé sur la description
            description = intent_config.get("description", "")
            if description:
                desc_keywords = self._extract_keywords_from_description(description)
                for keyword in desc_keywords:
                    if keyword.lower() in content_lower:
                        score += 2

            # Score basé sur les métriques
            if "metrics" in intent_config:
                for metric_name in intent_config["metrics"].keys():
                    metric_keywords = self._metric_to_keywords(metric_name)
                    for keyword in metric_keywords:
                        if keyword in content_lower:
                            score += 3

            # Score basé sur les thèmes de suivi
            followup_themes = intent_config.get("followup_themes", [])
            for theme in followup_themes:
                theme_keywords = theme.replace("_", " ").split()
                for keyword in theme_keywords:
                    if len(keyword) > 3 and keyword in content_lower:
                        score += 1

            if score > 0:
                intent_scores[intent_name] = score

        if not intent_scores:
            # Analyse fallback basée sur le contenu
            return self._fallback_intent_detection(content_lower)

        primary_intent = max(intent_scores, key=intent_scores.get)
        max_score = intent_scores[primary_intent]
        confidence = min(max_score / 15.0, 1.0)  # Normalisation améliorée

        return {
            "primary_intent": primary_intent,
            "confidence": confidence,
            "all_intents": list(intent_scores.keys()),
            "debug_scores": intent_scores if confidence < 0.5 else {},
        }

    def _extract_keywords_from_description(self, description: str) -> List[str]:
        """Extrait des mots-clés pertinents d'une description d'intent"""
        # Nettoie la description et extrait les mots significatifs
        cleaned = re.sub(r"[^\w\s]", " ", description.lower())
        words = cleaned.split()

        # Filtre les mots significatifs (plus de 3 caractères, pas des mots vides)
        stop_words = {"the", "and", "for", "with", "des", "les", "pour", "avec"}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]

        return keywords

    def _fallback_intent_detection(self, content_lower: str) -> Dict[str, Any]:
        """Détection fallback d'intent basée sur des patterns simples"""

        # Patterns pour détection fallback
        intent_patterns = {
            "metric_query": [
                "weight",
                "poids",
                "fcr",
                "conversion",
                "performance",
                "target",
                "consumption",
                "intake",
                "mortality",
                "production",
            ],
            "environment_setting": [
                "temperature",
                "humidity",
                "ventilation",
                "lighting",
                "environment",
                "housing",
                "ambient",
                "air",
            ],
            "protocol_query": [
                "vaccination",
                "protocol",
                "treatment",
                "medication",
                "vaccine",
                "biosecurity",
                "disinfection",
            ],
            "diagnosis_triage": [
                "disease",
                "illness",
                "symptoms",
                "diagnosis",
                "pathology",
                "mortality",
                "health",
                "clinical",
            ],
            "economics_cost": [
                "cost",
                "economic",
                "profit",
                "price",
                "budget",
                "financial",
                "investment",
                "roi",
            ],
        }

        scores = {}
        for intent, patterns in intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in content_lower)
            if score > 0:
                scores[intent] = score

        if scores:
            primary = max(scores, key=scores.get)
            confidence = min(
                scores[primary] / 8.0, 0.7
            )  # Confidence limitée pour fallback
            return {
                "primary_intent": primary,
                "confidence": confidence,
                "all_intents": list(scores.keys()),
                "fallback": True,
            }

        return {"primary_intent": "general", "confidence": 0.3, "fallback": True}

    def _metric_to_keywords(self, metric_name: str) -> List[str]:
        """Convertit un nom de métrique en mots-clés - VERSION ÉTENDUE"""

        # Mapping étendu pour toutes les métriques possibles
        mapping = {
            # Performance metrics
            "body_weight_target": ["body weight", "weight", "poids", "live weight"],
            "body_weight_avg": ["average weight", "mean weight", "poids moyen"],
            "daily_gain": ["daily gain", "gain", "croissance", "growth"],
            "fcr_target": ["fcr", "feed conversion", "conversion", "feed:gain"],
            "production_index_epef": ["epef", "index", "production index"],
            "uniformity_pct": ["uniformity", "uniformité", "cv", "coefficient"],
            "mortality_expected_pct": ["mortality", "mortalité", "death", "deaths"],
            # Feed and water
            "water_intake_daily": ["water", "eau", "intake", "consumption"],
            "water_feed_ratio": ["water ratio", "water:feed", "ratio eau"],
            "feed_intake_daily": ["feed", "aliment", "intake", "consumption"],
            "feed_intake_cumulative": ["cumulative feed", "total feed"],
            # Housing
            "stocking_density_kgm2": ["density", "densité", "stocking", "kg/m2"],
            "stocking_density_birdsm2": ["birds/m2", "bird density", "densité oiseaux"],
            "feeder_space_cm": ["feeder", "mangeoire", "feeding space"],
            "birds_per_nipple": ["nipple", "abreuvoir", "water point"],
            # Environment
            "ambient_temp_target": ["temperature", "température", "temp", "ambient"],
            "litter_temp_target": ["litter", "litière", "bedding"],
            "humidity_target": ["humidity", "humidité", "rh", "relative humidity"],
            "co2_max_ppm": ["co2", "carbon dioxide", "ppm"],
            "nh3_max_ppm": ["nh3", "ammonia", "ammoniac"],
            "air_speed_tunnel": ["air speed", "ventilation", "tunnel"],
            # Lighting
            "lighting_hours": ["lighting", "light", "éclairage", "hours", "heures"],
            "light_intensity_lux": ["lux", "intensity", "intensité lumineuse"],
            # Layer specific
            "egg_production_pct": ["egg production", "ponte", "laying", "production"],
            "hen_daily_feed": ["hen", "poule", "layer", "pondeuse"],
            "egg_weight_target": ["egg weight", "poids oeuf"],
            # Nutrition
            "me_kcalkg": ["energy", "énergie", "kcal", "metabolizable"],
            "cp_pct": ["protein", "protéine", "crude protein", "cp"],
            "lys_digestible_pct": ["lysine", "lysine digestible"],
            "ca_pct": ["calcium", "ca"],
            "av_p_pct": ["phosphorus", "phosphore", "available"],
        }

        keywords = mapping.get(metric_name, [])

        # Si pas de mapping spécifique, génère des mots-clés à partir du nom
        if not keywords:
            # Transforme le nom de métrique en mots-clés
            base_keywords = metric_name.replace("_", " ").split()
            # Retire les suffixes techniques
            filtered_keywords = [
                word
                for word in base_keywords
                if word not in ["target", "pct", "daily", "max", "min"]
            ]
            keywords = filtered_keywords

        return keywords

    def extract_applicable_metrics(
        self, content: str, intent_category: str
    ) -> List[str]:
        """Extrait les métriques applicables mentionnées dans le contenu - VERSION AMÉLIORÉE"""
        if not self.intents_data or "intents" not in self.intents_data:
            return []

        intent_config = self.intents_data["intents"].get(intent_category, {})
        if "metrics" not in intent_config:
            return []

        content_lower = content.lower()
        detected_metrics = []

        for metric_name, metric_config in intent_config["metrics"].items():
            metric_keywords = self._metric_to_keywords(metric_name)

            # Score de correspondance pour chaque métrique
            match_score = 0
            for keyword in metric_keywords:
                if keyword in content_lower:
                    match_score += 1

            # Ajoute la métrique si elle a un score suffisant
            if match_score > 0:
                detected_metrics.append(metric_name)

        return detected_metrics

    def get_genetic_lines_supported(self) -> List[str]:
        """Retourne la liste des lignées génétiques supportées"""
        if not self.intents_data or "aliases" not in self.intents_data:
            return []

        line_aliases = self.intents_data["aliases"].get("line", {})
        return list(line_aliases.keys())

    def validate_genetic_line(self, genetic_line: str) -> bool:
        """Valide qu'une lignée génétique est supportée"""
        supported_lines = self.get_genetic_lines_supported()
        return genetic_line.lower() in [line.lower() for line in supported_lines]
