# -*- coding: utf-8 -*-
"""
intent_classifier.py - Classificateur d'intentions multilingue
Version 2.0 - Intégration complète avec le service de traduction universel
"""

import re
import logging
import os
import json
from typing import Dict, Set, Tuple, Optional, List

# Imports configuration multilingue
from config.config import (
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
)

# Imports service traduction et utilitaires
from utils.translation_service import get_translation_service
from utils.utilities import detect_language_enhanced, normalize_language_code
from processing.intent_types import IntentType

logger = logging.getLogger(__name__)


class MultilingualIntentClassifier:
    """
    Classificateur d'intentions multilingue avec service de traduction intégré
    Remplace les mots-clés hardcodés par une approche dynamique via dictionnaire universel
    """

    def __init__(
        self,
        intents_config: dict = None,
        vocab=None,
        guardrails=None,
        weights: dict = None,
    ):
        # Configuration des poids
        if weights:
            self.weights = weights
        else:
            cfg_path = os.getenv("INTENT_WEIGHTS_FILE", "")
            if cfg_path and os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        self.weights = json.load(f)
                except Exception as e:
                    logger.warning(f"Erreur chargement poids: {e}, utilisation défauts")
                    self.weights = self._get_default_weights()
            else:
                self.weights = self._get_default_weights()

        self.intents_config = intents_config or {}
        self.vocab = vocab
        self.guardrails = guardrails

        # Configuration multilingue
        self.supported_languages = SUPPORTED_LANGUAGES
        self.default_language = DEFAULT_LANGUAGE
        self.translation_service = get_translation_service()

        # Cache pour optimiser les performances
        self.intent_keywords_cache = {}
        self.patterns_cache = {}

        # Construction du vocabulaire multilingue
        self.intent_keywords = self._build_multilingual_intent_keywords()
        self.intent_patterns = self._build_multilingual_intent_patterns()
        self.intent_metrics = self._build_intent_metrics()

    def _get_default_weights(self) -> Dict[str, float]:
        """Poids par défaut pour le scoring"""
        return {
            "keyword": 1.0,
            "entity": 5.0,
            "explain_bonus": 2.0,
            "regex": 2.5,
            "translation_penalty": 0.8,  # Nouveau: pénalité pour termes traduits
            "language_confidence_bonus": 1.2,  # Nouveau: bonus pour langue bien détectée
        }

    def _build_multilingual_intent_keywords(self) -> Dict[str, Dict[str, Set[str]]]:
        """
        Construit les mots-clés par intention et par langue
        Structure: {intent_type: {language: {keywords}}}
        """
        keywords = {}

        # Définition des termes de base par intention
        base_keywords = {
            IntentType.METRIC_QUERY.value: {
                "fr": {
                    "poids",
                    "fcr",
                    "conversion",
                    "consommation",
                    "eau",
                    "performance",
                    "production",
                    "croissance",
                    "optimal",
                    "gramme",
                    "kg",
                    "litre",
                    "pourcentage",
                    "combien",
                    "quelle",
                    "indice",
                    "ratio",
                    "rendement",
                    "objectif",
                    "standard",
                    "gain",
                    "quotidien",
                    "hebdomadaire",
                    "cumul",
                    "epef",
                    "mortalité",
                    "densité",
                    "mangeoire",
                    "abreuvoir",
                },
                "en": {
                    "weight",
                    "fcr",
                    "conversion",
                    "consumption",
                    "water",
                    "performance",
                    "production",
                    "growth",
                    "optimal",
                    "gram",
                    "kg",
                    "liter",
                    "percentage",
                    "how much",
                    "what",
                    "index",
                    "ratio",
                    "efficiency",
                    "target",
                    "standard",
                    "gain",
                    "daily",
                    "weekly",
                    "cumulative",
                    "epef",
                    "mortality",
                    "density",
                    "feeder",
                    "nipple",
                    "intake",
                },
            },
            IntentType.ENVIRONMENT_SETTING.value: {
                "fr": {
                    "température",
                    "ventilation",
                    "climatisation",
                    "chauffage",
                    "humidité",
                    "air",
                    "climat",
                    "ambiance",
                    "réglage",
                    "environnement",
                    "conditions",
                    "tunnel",
                    "refroidissement",
                    "entrée",
                    "pression",
                    "éclairage",
                    "lux",
                    "intensité",
                    "heures",
                    "photopériode",
                    "co2",
                    "nh3",
                    "poussière",
                },
                "en": {
                    "temperature",
                    "ventilation",
                    "air conditioning",
                    "heating",
                    "humidity",
                    "air",
                    "climate",
                    "ambience",
                    "setting",
                    "environment",
                    "conditions",
                    "tunnel",
                    "cooling",
                    "inlet",
                    "pressure",
                    "lighting",
                    "lux",
                    "intensity",
                    "hours",
                    "photoperiod",
                    "co2",
                    "nh3",
                    "dust",
                },
            },
            IntentType.PROTOCOL_QUERY.value: {
                "fr": {
                    "vaccination",
                    "protocole",
                    "traitement",
                    "biosécurité",
                    "prévention",
                    "vaccin",
                    "programme",
                    "planning",
                    "sanitaire",
                    "antibiotique",
                    "médicament",
                    "délai",
                    "timing",
                    "injection",
                    "schedule",
                },
                "en": {
                    "vaccination",
                    "protocol",
                    "treatment",
                    "biosecurity",
                    "prevention",
                    "vaccine",
                    "program",
                    "schedule",
                    "planning",
                    "sanitary",
                    "antibiotic",
                    "medication",
                    "withdrawal",
                    "timing",
                    "injection",
                },
            },
            IntentType.DIAGNOSIS_TRIAGE.value: {
                "fr": {
                    "maladie",
                    "symptôme",
                    "diagnostic",
                    "mortalité",
                    "problème",
                    "signes",
                    "pathologie",
                    "infection",
                    "virus",
                    "bactérie",
                    "parasite",
                    "malade",
                    "santé",
                    "clinique",
                    "lésion",
                    "autopsie",
                    "nécropsie",
                    "laboratoire",
                    "analyses",
                },
                "en": {
                    "disease",
                    "symptom",
                    "diagnosis",
                    "mortality",
                    "problem",
                    "signs",
                    "pathology",
                    "infection",
                    "virus",
                    "bacteria",
                    "parasite",
                    "sick",
                    "health",
                    "clinical",
                    "lesion",
                    "postmortem",
                    "necropsy",
                    "lab",
                    "analysis",
                },
            },
            IntentType.ECONOMICS_COST.value: {
                "fr": {
                    "coût",
                    "prix",
                    "économique",
                    "rentabilité",
                    "marge",
                    "budget",
                    "finance",
                    "euros",
                    "investissement",
                    "retour",
                    "roi",
                    "amortissement",
                    "efficacité",
                    "optimisation",
                    "coût aliment",
                    "coût énergie",
                    "main-d'œuvre",
                },
                "en": {
                    "cost",
                    "price",
                    "economic",
                    "profitability",
                    "margin",
                    "budget",
                    "finance",
                    "dollars",
                    "investment",
                    "return",
                    "roi",
                    "amortization",
                    "efficiency",
                    "optimization",
                    "feed cost",
                    "energy cost",
                    "labor",
                },
            },
        }

        # Extension via service de traduction si disponible
        if self.translation_service:
            for intent_type, lang_keywords in base_keywords.items():
                keywords[intent_type] = {}

                for language in self.supported_languages:
                    if language in lang_keywords:
                        # Utiliser les mots-clés définis
                        keywords[intent_type][language] = lang_keywords[language]
                    else:
                        # Traduire depuis l'anglais ou le français
                        source_lang = "en" if "en" in lang_keywords else "fr"
                        source_keywords = lang_keywords[source_lang]

                        translated_keywords = self._translate_keywords(
                            source_keywords,
                            source_lang,
                            language,
                            f"intent_{intent_type}",
                        )
                        keywords[intent_type][language] = translated_keywords
        else:
            # Fallback sans service de traduction
            keywords = {
                intent_type: lang_keywords
                for intent_type, lang_keywords in base_keywords.items()
            }

        logger.info(
            f"Vocabulaire multilingue construit pour {len(keywords)} intentions, {len(self.supported_languages)} langues"
        )
        return keywords

    def _translate_keywords(
        self, keywords: Set[str], source_lang: str, target_lang: str, domain: str
    ) -> Set[str]:
        """Traduit un ensemble de mots-clés vers une langue cible"""
        if not self.translation_service:
            return keywords  # Fallback: garder les mots-clés originaux

        cache_key = f"{domain}:{source_lang}:{target_lang}"
        if cache_key in self.intent_keywords_cache:
            return self.intent_keywords_cache[cache_key]

        translated_keywords = set()

        for keyword in keywords:
            try:
                result = self.translation_service.translate_term(
                    keyword, target_lang, source_lang, domain
                )
                if (
                    result.confidence >= 0.6
                ):  # Seuil de confiance pour accepter la traduction
                    translated_keywords.add(result.text.lower())
                else:
                    # Si traduction peu fiable, garder le terme original
                    translated_keywords.add(keyword.lower())
            except Exception as e:
                logger.debug(
                    f"Erreur traduction '{keyword}' {source_lang}->{target_lang}: {e}"
                )
                translated_keywords.add(keyword.lower())  # Fallback

        self.intent_keywords_cache[cache_key] = translated_keywords
        return translated_keywords

    def _build_multilingual_intent_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Construit les patterns regex multilingues par intention"""
        patterns = {}

        base_patterns = {
            IntentType.METRIC_QUERY.value: {
                "fr": [
                    r"\b(?:combien|quelle?\s+(?:est|sont))\b",
                    r"\b(?:poids|fcr)\s+(?:de|du|des|à|au)\b",
                    r"\b\d+\s*(?:g|kg|%|litres?|jours?|semaines?)\b",
                    r"\b(?:optimal|optimale|cible|objectif)\b",
                    r"\b(?:quel|quelle)\s+(?:poids|fcr|consommation)\b",
                ],
                "en": [
                    r"\b(?:how much|what\s+(?:is|are))\b",
                    r"\b(?:weight|fcr)\s+(?:of|at|for)\b",
                    r"\b\d+\s*(?:g|kg|%|liters?|days?|weeks?)\b",
                    r"\b(?:optimal|target|goal)\b",
                    r"\b(?:what|which)\s+(?:weight|fcr|consumption)\b",
                ],
            },
            IntentType.ENVIRONMENT_SETTING.value: {
                "fr": [
                    r"\b(?:température|ventilation)\s+(?:optimale?|recommandée?)\b",
                    r"\b(?:comment|comment)\s+(?:régler|ajuster|paramétrer)\b",
                    r"\b(?:ambiance|climat|réglage|setting)\b",
                    r"\b(?:degré|°c|celsius)\b",
                ],
                "en": [
                    r"\b(?:temperature|ventilation)\s+(?:optimal|recommended)\b",
                    r"\b(?:how to|how)\s+(?:set|adjust|configure)\b",
                    r"\b(?:climate|setting|environment)\b",
                    r"\b(?:degree|°c|celsius|°f|fahrenheit)\b",
                ],
            },
            IntentType.DIAGNOSIS_TRIAGE.value: {
                "fr": [
                    r"\b(?:mes|nos)\s+(?:poulets?|poules?)\s+(?:sont|ont)\b",
                    r"\b(?:symptômes?|signes?)\s+(?:de|d')\b",
                    r"\b(?:diagnostic|problème|maladie)\b",
                    r"\b(?:mortalité|décès|morts?)\b",
                ],
                "en": [
                    r"\b(?:my|our)\s+(?:chickens?|birds?)\s+(?:are|have)\b",
                    r"\b(?:symptoms?|signs?)\s+(?:of|from)\b",
                    r"\b(?:diagnosis|problem|disease)\b",
                    r"\b(?:mortality|death|dead)\b",
                ],
            },
        }

        # Extension automatique pour toutes les langues supportées via traduction
        if self.translation_service:
            for intent_type, lang_patterns in base_patterns.items():
                patterns[intent_type] = {}

                for language in self.supported_languages:
                    if language in lang_patterns:
                        patterns[intent_type][language] = lang_patterns[language]
                    else:
                        # Pour les langues non définies, adapter les patterns anglais
                        if "en" in lang_patterns:
                            adapted_patterns = self._adapt_patterns_for_language(
                                lang_patterns["en"], language
                            )
                            patterns[intent_type][language] = adapted_patterns
                        else:
                            patterns[intent_type][language] = []
        else:
            patterns = base_patterns

        return patterns

    def _adapt_patterns_for_language(
        self, base_patterns: List[str], target_language: str
    ) -> List[str]:
        """Adapte les patterns regex pour une langue cible"""
        if target_language in ["es", "it", "pt"]:  # Langues latines
            adapted = []
            for pattern in base_patterns:
                # Adaptations basiques pour langues latines
                adapted_pattern = pattern
                adapted_pattern = adapted_pattern.replace(
                    "how much", "cuanto|quanto|quanto"
                )
                adapted_pattern = adapted_pattern.replace("what", "que|cosa|que")
                adapted_pattern = adapted_pattern.replace("weight", "peso")
                adapted_pattern = adapted_pattern.replace(
                    "optimal", "optimal|ottimale|óptimo"
                )
                adapted.append(adapted_pattern)
            return adapted

        elif target_language in ["de", "nl"]:  # Langues germaniques
            adapted = []
            for pattern in base_patterns:
                adapted_pattern = pattern
                adapted_pattern = adapted_pattern.replace("how much", "wieviel|hoeveel")
                adapted_pattern = adapted_pattern.replace("what", "was|wat")
                adapted_pattern = adapted_pattern.replace("weight", "gewicht")
                adapted_pattern = adapted_pattern.replace("optimal", "optimal")
                adapted.append(adapted_pattern)
            return adapted

        else:
            # Pour les autres langues, patterns universels (nombres, unités)
            return [
                r"\b\d+\s*(?:g|kg|%)\b",  # Unités universelles
                r"\b(?:cobb|ross|hubbard)\b",  # Marques universelles
                r"\b\d+\s*(?:day|jour|dia|tag|день)\b",  # Âges
            ]

    def _build_intent_metrics(self) -> Dict[str, Set[str]]:
        """Construit l'association intentions -> métriques depuis la configuration"""
        intent_metrics = {}

        for intent_name, intent_config in self.intents_config.get(
            "intents", {}
        ).items():
            metrics = set(intent_config.get("metrics", {}).keys())
            intent_metrics[intent_name] = metrics

        return intent_metrics

    # ===== MÉTHODES PRINCIPALES =====

    def classify_intent_multilingual(
        self,
        text: str,
        entities: Dict[str, str] = None,
        explain_score: Optional[float] = None,
        language: str = None,
    ) -> Tuple[IntentType, Dict[str, float]]:
        """
        Classification d'intention multilingue
        Détecte automatiquement la langue si non fournie
        """
        # Détection automatique de la langue
        if language is None:
            detection_result = detect_language_enhanced(text)
            language = detection_result.language
            language_confidence = detection_result.confidence
            logger.debug(
                f"Langue détectée: {language} (confiance: {language_confidence:.2f})"
            )
        else:
            language = normalize_language_code(language)
            language_confidence = 1.0

        # Validation langue supportée
        if language not in self.supported_languages:
            logger.warning(
                f"Langue non supportée: {language}, fallback vers {self.default_language}"
            )
            language = self.default_language
            language_confidence = 0.5

        return self._classify_for_language(
            text, entities, explain_score, language, language_confidence
        )

    def classify_intent(
        self,
        text: str,
        entities: Dict[str, str] = None,
        explain_score: Optional[float] = None,
    ) -> Tuple[IntentType, Dict[str, float]]:
        """Méthode de compatibilité avec l'interface existante"""
        return self.classify_intent_multilingual(text, entities, explain_score)

    def _classify_for_language(
        self,
        text: str,
        entities: Dict[str, str],
        explain_score: Optional[float],
        language: str,
        language_confidence: float,
    ) -> Tuple[IntentType, Dict[str, float]]:
        """Classification pour une langue spécifique"""
        text_lower = text.lower()
        entities = entities or {}
        scores = {}
        score_breakdown = {}

        for intent_type in IntentType:
            intent_value = intent_type.value

            # Score par mots-clés pour la langue
            keyword_score = self._calculate_keyword_score(
                text_lower, intent_value, language
            )

            # Score par patterns regex pour la langue
            pattern_score = self._calculate_pattern_score(
                text_lower, intent_value, language
            )

            # Score par entités (indépendant de la langue)
            entity_score = self._calculate_entity_score(
                entities, intent_value, text_lower
            )

            # Score par métriques spécialisées
            metrics_score = self._calculate_metrics_score(entities, intent_value)

            # Bonus explain_score
            explain_bonus = self._calculate_explain_bonus(explain_score)

            # Bonus/pénalité selon la confiance de détection de langue
            language_bonus = self._calculate_language_bonus(language_confidence)

            # Score total avec ajustements multilingues
            total_score = (
                keyword_score
                + pattern_score
                + entity_score
                + metrics_score
                + explain_bonus
                + language_bonus
            )

            # Pénalité si traduction utilisée (termes moins précis)
            if language not in ["fr", "en"] and self.translation_service:
                total_score *= self.weights.get("translation_penalty", 0.8)

            scores[intent_value] = total_score
            score_breakdown[intent_value] = {
                "keyword_score": keyword_score,
                "pattern_score": pattern_score,
                "entity_score": entity_score,
                "metrics_score": metrics_score,
                "explain_bonus": explain_bonus,
                "language_bonus": language_bonus,
                "total_score": total_score,
                "language": language,
                "language_confidence": language_confidence,
            }

        # Retourner l'intention avec le meilleur score
        if max(scores.values()) > 0:
            best_intent = max(scores, key=scores.get)
            logger.debug(
                f"Intent classifié [{language}]: {best_intent} (score: {scores[best_intent]:.2f})"
            )
            return IntentType(best_intent), score_breakdown

        return IntentType.GENERAL_POULTRY, score_breakdown

    # ===== MÉTHODES DE CALCUL DE SCORE =====

    def _calculate_keyword_score(
        self, text: str, intent_type: str, language: str
    ) -> float:
        """Calcule le score basé sur les mots-clés pour une langue"""
        if (
            intent_type not in self.intent_keywords
            or language not in self.intent_keywords[intent_type]
        ):
            return 0.0

        keywords = self.intent_keywords[intent_type][language]
        keyword_matches = sum(1 for keyword in keywords if keyword in text)

        return keyword_matches * self.weights.get("keyword", 1.0)

    def _calculate_pattern_score(
        self, text: str, intent_type: str, language: str
    ) -> float:
        """Calcule le score basé sur les patterns regex pour une langue"""
        if (
            intent_type not in self.intent_patterns
            or language not in self.intent_patterns[intent_type]
        ):
            return 0.0

        patterns = self.intent_patterns[intent_type][language]
        pattern_matches = sum(
            1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE)
        )

        return pattern_matches * self.weights.get("regex", 2.5)

    def _calculate_entity_score(
        self, entities: Dict[str, str], intent_type: str, text: str
    ) -> float:
        """Calcule le score basé sur les entités détectées"""
        entity_score = 0.0

        if intent_type == IntentType.METRIC_QUERY.value:
            if "metrics" in entities:
                entity_score += 1.0
            if any(
                key in entities
                for key in ["weight_value", "percentage_value", "temperature_value"]
            ):
                entity_score += 0.6
            if any(key in entities for key in ["age_days", "age_weeks", "line"]):
                entity_score += 0.4
            if "line_normalized" in entities:
                entity_score += 0.2

        elif intent_type == IntentType.ENVIRONMENT_SETTING.value:
            if "temperature_value" in entities:
                entity_score += 0.8
            if "site_type" in entities:
                entity_score += 0.4
            if "environment" in entities:
                entity_score += 0.6

        elif intent_type == IntentType.ECONOMICS_COST.value:
            if any(word in text for word in ["coût", "cost", "prix", "econom"]):
                entity_score += 0.6
            if "flock_size" in entities:
                entity_score += 0.4

        elif intent_type == IntentType.DIAGNOSIS_TRIAGE.value:
            if any(
                word in text
                for word in ["symptom", "symptôme", "maladie", "disease", "mort"]
            ):
                entity_score += 0.8
            if "species" in entities:
                entity_score += 0.3

        return entity_score * self.weights.get("entity", 5.0)

    def _calculate_metrics_score(
        self, entities: Dict[str, str], intent_type: str
    ) -> float:
        """Calcule le score basé sur les métriques spécialisées"""
        if intent_type not in self.intent_metrics:
            return 0.0

        intent_specific_metrics = self.intent_metrics[intent_type]
        detected_metrics = entities.get("metrics", "").split(",")
        matching_metrics = [m for m in detected_metrics if m in intent_specific_metrics]

        return len(matching_metrics) * 3.0

    def _calculate_explain_bonus(self, explain_score: Optional[float]) -> float:
        """Calcule le bonus pour explain_score élevé"""
        if explain_score is not None and explain_score > 0.7:
            return self.weights.get("explain_bonus", 2.0)
        return 0.0

    def _calculate_language_bonus(self, language_confidence: float) -> float:
        """Calcule le bonus selon la confiance de détection de langue"""
        if language_confidence > 0.9:
            return self.weights.get("language_confidence_bonus", 1.2)
        elif language_confidence > 0.7:
            return 0.5
        else:
            return 0.0

    # ===== MÉTHODES UTILITAIRES =====

    def get_supported_languages(self) -> List[str]:
        """Retourne la liste des langues supportées"""
        return list(self.supported_languages)

    def get_weights_config(self) -> dict:
        """Retourne la configuration actuelle des poids"""
        return self.weights.copy()

    def update_weights(self, new_weights: dict) -> None:
        """Met à jour les poids de scoring"""
        self.weights.update(new_weights)
        logger.info(f"Poids mis à jour: {self.weights}")

    def clear_cache(self) -> None:
        """Vide le cache de traduction"""
        self.intent_keywords_cache.clear()
        self.patterns_cache.clear()
        logger.info("Cache de traduction vidé")

    def get_classifier_stats(self) -> Dict:
        """Retourne les statistiques du classificateur"""
        return {
            "version": "multilingual_v2.0",
            "supported_languages": list(self.supported_languages),
            "intent_types": [intent.value for intent in IntentType],
            "translation_service_available": self.translation_service is not None,
            "cache_size": len(self.intent_keywords_cache),
            "total_keywords": sum(
                len(lang_keywords)
                for intent_keywords in self.intent_keywords.values()
                for lang_keywords in intent_keywords.values()
            ),
            "weights": self.weights.copy(),
        }

    def test_classification(self, text: str, language: str = None) -> Dict:
        """Test et diagnostic d'une classification"""
        intent_type, breakdown = self.classify_intent_multilingual(
            text, {}, None, language
        )

        return {
            "input_text": text,
            "detected_language": breakdown[intent_type.value].get(
                "language", "unknown"
            ),
            "classified_intent": intent_type.value,
            "confidence_score": breakdown[intent_type.value]["total_score"],
            "language_confidence": breakdown[intent_type.value].get(
                "language_confidence", 0.0
            ),
            "score_breakdown": breakdown,
        }


# ===== CLASSE DE COMPATIBILITÉ =====


class IntentClassifier(MultilingualIntentClassifier):
    """Alias pour compatibilité avec l'interface existante"""

    def __init__(
        self,
        intents_config: dict = None,
        vocab=None,
        guardrails=None,
        weights: dict = None,
    ):
        super().__init__(intents_config, vocab, guardrails, weights)


# ===== FONCTION FACTORY =====


def create_intent_classifier(intents_config: dict = None, **kwargs) -> IntentClassifier:
    """Crée une instance du classificateur d'intentions multilingue"""
    return IntentClassifier(intents_config, **kwargs)
