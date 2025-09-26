# -*- coding: utf-8 -*-
"""
intent_classifier.py - Classificateur d'intentions multilingue
Version 3.0 - Utilisation complète des dictionnaires universels (universal_terms_*.json)
CORRECTION MAJEURE: Suppression du texte hardcodé, chargement depuis dictionnaires JSON
"""

import re
import logging
import os
import json
from typing import Dict, Set, Tuple, Optional, List
from pathlib import Path

# Imports configuration multilingue
from config.config import (
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    UNIVERSAL_DICT_PATH,
)

# Imports service traduction et utilitaires
from utils.translation_service import get_translation_service
from utils.utilities import detect_language_enhanced, normalize_language_code
from processing.intent_types import IntentType

logger = logging.getLogger(__name__)


class MultilingualIntentClassifier:
    """
    Classificateur d'intentions multilingue avec chargement dynamique depuis dictionnaires
    NOUVELLE VERSION: Élimine tout le texte hardcodé en faveur des fichiers universal_terms_*.json
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

        # Chemin des dictionnaires universels
        self.dict_path = Path(UNIVERSAL_DICT_PATH)

        # Cache pour optimiser les performances
        self.intent_keywords_cache = {}
        self.patterns_cache = {}
        self.loaded_dictionaries = {}  # Cache des dictionnaires chargés

        # Construction du vocabulaire multilingue DEPUIS LES DICTIONNAIRES
        self.intent_keywords = self._build_multilingual_intent_keywords_from_dicts()
        self.intent_patterns = self._build_multilingual_intent_patterns_from_dicts()
        self.intent_metrics = self._build_intent_metrics()

    def _get_default_weights(self) -> Dict[str, float]:
        """Poids par défaut pour le scoring"""
        return {
            "keyword": 1.0,
            "entity": 5.0,
            "explain_bonus": 2.0,
            "regex": 2.5,
            "translation_penalty": 0.8,
            "language_confidence_bonus": 1.2,
        }

    # ===== NOUVELLES MÉTHODES: CHARGEMENT DEPUIS DICTIONNAIRES =====

    def _load_dictionary_for_language(self, language: str) -> Dict:
        """
        Charge le dictionnaire universel pour une langue spécifique
        Utilise un cache pour éviter les rechargements
        """
        if language in self.loaded_dictionaries:
            return self.loaded_dictionaries[language]

        dict_file = self.dict_path / f"universal_terms_{language}.json"

        if not dict_file.exists():
            logger.warning(f"Dictionnaire manquant pour {language}: {dict_file}")
            return {}

        try:
            with open(dict_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.loaded_dictionaries[language] = data
                logger.debug(
                    f"Dictionnaire chargé pour {language}: {len(data)} domaines"
                )
                return data
        except Exception as e:
            logger.error(f"Erreur chargement dictionnaire {language}: {e}")
            return {}

    def _build_multilingual_intent_keywords_from_dicts(
        self,
    ) -> Dict[str, Dict[str, Set[str]]]:
        """
        Construit les mots-clés par intention et par langue DEPUIS LES DICTIONNAIRES
        Structure: {intent_type: {language: {keywords}}}

        Mapping des intentions vers les domaines des dictionnaires:
        - METRIC_QUERY -> performance_metrics, units_measures
        - ENVIRONMENT_SETTING -> infrastructure_environment, equipment_settings
        - PROTOCOL_QUERY -> biosecurity_health, pathology_specific
        - DIAGNOSIS_TRIAGE -> health_symptoms, pathology_specific
        - ECONOMICS_COST -> (termes économiques génériques)
        """
        keywords = {}

        # Mapping intention -> domaines dans les dictionnaires
        intent_to_domains = {
            IntentType.METRIC_QUERY.value: [
                "performance_metrics",
                "units_measures",
                "nutrition_detailed",
            ],
            IntentType.ENVIRONMENT_SETTING.value: [
                "infrastructure_environment",
                "equipment_settings",
                "equipment_types",
            ],
            IntentType.PROTOCOL_QUERY.value: [
                "biosecurity_health",
                "pathology_specific",
                "reproduction_laying",
            ],
            IntentType.DIAGNOSIS_TRIAGE.value: [
                "health_symptoms",
                "pathology_specific",
                "additional_pathologies",
            ],
            IntentType.ECONOMICS_COST.value: [
                "performance_metrics",  # Inclut des métriques économiques
            ],
        }

        # Construction pour chaque intention
        for intent_type, domains in intent_to_domains.items():
            keywords[intent_type] = {}

            # Pour chaque langue supportée
            for language in self.supported_languages:
                dict_data = self._load_dictionary_for_language(language)
                intent_keywords = set()

                # Extraire les termes des domaines pertinents
                for domain in domains:
                    if domain in dict_data:
                        domain_data = dict_data[domain]

                        # Extraire tous les termes du domaine
                        if isinstance(domain_data, dict):
                            for category, terms in domain_data.items():
                                if isinstance(terms, list):
                                    intent_keywords.update(
                                        term.lower() for term in terms
                                    )
                                elif isinstance(terms, str):
                                    intent_keywords.add(terms.lower())
                        elif isinstance(domain_data, list):
                            intent_keywords.update(term.lower() for term in domain_data)

                keywords[intent_type][language] = intent_keywords

                logger.debug(
                    f"Intent {intent_type} [{language}]: {len(intent_keywords)} mots-clés chargés"
                )

        # Ajout de mots-clés spécifiques pour les questions (depuis question_patterns si disponible)
        self._enrich_keywords_with_question_patterns(keywords)

        logger.info(
            f"Vocabulaire multilingue construit depuis dictionnaires: "
            f"{len(keywords)} intentions, {len(self.supported_languages)} langues"
        )
        return keywords

    def _enrich_keywords_with_question_patterns(self, keywords: Dict) -> None:
        """
        Enrichit les mots-clés avec les patterns de questions depuis les dictionnaires
        Cherche le domaine 'question_patterns' dans chaque dictionnaire
        """
        for language in self.supported_languages:
            dict_data = self._load_dictionary_for_language(language)

            if "question_patterns" not in dict_data:
                continue

            question_data = dict_data["question_patterns"]

            # Ajouter les mots-clés de questions aux intentions appropriées
            for intent_type in keywords.keys():
                if intent_type in question_data:
                    intent_question_data = question_data[intent_type]

                    # Extraire les mots-clés si présents
                    if isinstance(intent_question_data, dict):
                        if "keywords" in intent_question_data:
                            question_keywords = intent_question_data["keywords"]
                            if isinstance(question_keywords, list):
                                keywords[intent_type][language].update(
                                    kw.lower() for kw in question_keywords
                                )

    def _build_multilingual_intent_patterns_from_dicts(
        self,
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Construit les patterns regex multilingues DEPUIS LES DICTIONNAIRES
        Cherche les regex_patterns dans le domaine 'question_patterns'
        """
        patterns = {}

        # Mapping intention -> patterns
        for intent_type in [e.value for e in IntentType]:
            patterns[intent_type] = {}

            for language in self.supported_languages:
                dict_data = self._load_dictionary_for_language(language)
                intent_patterns = []

                # Chercher dans question_patterns
                if "question_patterns" in dict_data:
                    question_data = dict_data["question_patterns"]

                    if intent_type in question_data:
                        intent_question_data = question_data[intent_type]

                        if isinstance(intent_question_data, dict):
                            if "regex_patterns" in intent_question_data:
                                regex_list = intent_question_data["regex_patterns"]
                                if isinstance(regex_list, list):
                                    intent_patterns.extend(regex_list)

                # Si aucun pattern trouvé, utiliser des patterns génériques
                if not intent_patterns:
                    intent_patterns = self._get_fallback_patterns(intent_type, language)

                patterns[intent_type][language] = intent_patterns

                logger.debug(
                    f"Patterns pour {intent_type} [{language}]: {len(intent_patterns)} patterns"
                )

        return patterns

    def _get_fallback_patterns(self, intent_type: str, language: str) -> List[str]:
        """
        Patterns regex génériques de fallback si non présents dans les dictionnaires
        Patterns minimaux universels
        """
        # Patterns universels (nombres, unités, marques)
        universal_patterns = [
            r"\b\d+\s*(?:g|kg|%|ml|l)\b",  # Unités métriques
            r"\b(?:cobb|ross|hubbard|isa)\b",  # Marques génétiques
            r"\b\d+\s*(?:day|jour|dia|tag|día)\b",  # Âges
        ]

        # Patterns spécifiques par intention (minimalistes)
        if intent_type == IntentType.METRIC_QUERY.value:
            if language in ["fr", "es", "it", "pt"]:
                return universal_patterns + [
                    r"\b(?:combien|cuanto|quanto|poids|peso)\b"
                ]
            elif language in ["en"]:
                return universal_patterns + [r"\b(?:how much|what|weight|fcr)\b"]
            elif language in ["de", "nl"]:
                return universal_patterns + [r"\b(?:wieviel|hoeveel|gewicht)\b"]

        return universal_patterns

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
            # Utilise des patterns multilingues au lieu de texte hardcodé
            economic_keywords = self._get_economic_keywords(text)
            if economic_keywords:
                entity_score += 0.6
            if "flock_size" in entities:
                entity_score += 0.4

        elif intent_type == IntentType.DIAGNOSIS_TRIAGE.value:
            # Utilise des patterns multilingues au lieu de texte hardcodé
            diagnostic_keywords = self._get_diagnostic_keywords(text)
            if diagnostic_keywords:
                entity_score += 0.8
            if "species" in entities:
                entity_score += 0.3

        return entity_score * self.weights.get("entity", 5.0)

    def _get_economic_keywords(self, text: str) -> bool:
        """Détecte des mots-clés économiques de manière multilingue"""
        # Chercher dans les dictionnaires chargés
        for dict_data in self.loaded_dictionaries.values():
            if "performance_metrics" in dict_data:
                metrics = dict_data["performance_metrics"]
                if isinstance(metrics, dict):
                    for term in metrics.values():
                        if isinstance(term, str) and "cost" in term.lower():
                            if term.lower() in text.lower():
                                return True
        return False

    def _get_diagnostic_keywords(self, text: str) -> bool:
        """Détecte des mots-clés de diagnostic de manière multilingue"""
        # Chercher dans les dictionnaires chargés
        for dict_data in self.loaded_dictionaries.values():
            if "health_symptoms" in dict_data:
                symptoms = dict_data["health_symptoms"]
                if isinstance(symptoms, list):
                    for symptom in symptoms:
                        if symptom.lower() in text.lower():
                            return True
        return False

    def validate_dictionaries_completeness(self) -> Dict[str, any]:
        """
        Valide que tous les dictionnaires nécessaires sont chargés et complets
        Retourne un rapport de validation
        """
        validation_report = {
            "status": "ok",
            "languages_found": [],
            "languages_missing": [],
            "domains_coverage": {},
            "warnings": [],
            "errors": [],
        }

        required_domains = [
            "performance_metrics",
            "units_measures",
            "infrastructure_environment",
            "equipment_settings",
            "biosecurity_health",
            "health_symptoms",
        ]

        for language in self.supported_languages:
            dict_data = self._load_dictionary_for_language(language)

            if not dict_data:
                validation_report["languages_missing"].append(language)
                validation_report["errors"].append(
                    f"Dictionnaire manquant pour {language}"
                )
                continue

            validation_report["languages_found"].append(language)

            # Vérifier les domaines
            missing_domains = []
            for domain in required_domains:
                if domain not in dict_data:
                    missing_domains.append(domain)

            if missing_domains:
                validation_report["domains_coverage"][language] = {
                    "complete": False,
                    "missing_domains": missing_domains,
                }
                validation_report["warnings"].append(
                    f"Langue {language}: domaines manquants {missing_domains}"
                )
            else:
                validation_report["domains_coverage"][language] = {
                    "complete": True,
                    "missing_domains": [],
                }

        # Statut global
        if validation_report["errors"]:
            validation_report["status"] = "error"
        elif validation_report["warnings"]:
            validation_report["status"] = "warning"

        return validation_report

    def get_intent_keywords_for_language(
        self, intent_type: str, language: str
    ) -> Set[str]:
        """
        Retourne les mots-clés pour une intention et une langue spécifiques
        Utile pour le debugging et les tests
        """
        if (
            intent_type in self.intent_keywords
            and language in self.intent_keywords[intent_type]
        ):
            return self.intent_keywords[intent_type][language]
        return set()

    def get_intent_patterns_for_language(
        self, intent_type: str, language: str
    ) -> List[str]:
        """
        Retourne les patterns regex pour une intention et une langue spécifiques
        Utile pour le debugging et les tests
        """
        if (
            intent_type in self.intent_patterns
            and language in self.intent_patterns[intent_type]
        ):
            return self.intent_patterns[intent_type][language]
        return []

    def export_loaded_vocabulary(self, output_path: str = None) -> Dict:
        """
        Exporte tout le vocabulaire chargé pour inspection
        Utile pour le debugging et la documentation
        """
        export_data = {
            "metadata": {
                "version": "3.0",
                "total_languages": len(self.supported_languages),
                "total_intents": len(self.intent_keywords),
                "dictionaries_loaded": len(self.loaded_dictionaries),
            },
            "keywords_by_intent": {},
            "patterns_by_intent": {},
            "statistics": {},
        }

        # Export des mots-clés
        for intent_type, lang_keywords in self.intent_keywords.items():
            export_data["keywords_by_intent"][intent_type] = {}
            for language, keywords in lang_keywords.items():
                export_data["keywords_by_intent"][intent_type][language] = list(
                    keywords
                )

        # Export des patterns
        for intent_type, lang_patterns in self.intent_patterns.items():
            export_data["patterns_by_intent"][intent_type] = {}
            for language, patterns in lang_patterns.items():
                export_data["patterns_by_intent"][intent_type][language] = patterns

        # Statistiques par intention
        for intent_type in self.intent_keywords.keys():
            total_keywords = sum(
                len(keywords) for keywords in self.intent_keywords[intent_type].values()
            )
            total_patterns = sum(
                len(patterns) for patterns in self.intent_patterns[intent_type].values()
            )

            export_data["statistics"][intent_type] = {
                "total_keywords": total_keywords,
                "total_patterns": total_patterns,
                "languages_coverage": len(self.intent_keywords[intent_type]),
            }

        # Sauvegarder si chemin fourni
        if output_path:
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Vocabulaire exporté vers {output_path}")
            except Exception as e:
                logger.error(f"Erreur export vocabulaire: {e}")

        return export_data

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
        self.loaded_dictionaries.clear()
        logger.info("Cache de traduction vidé")

    def reload_dictionaries(self) -> None:
        """Recharge tous les dictionnaires depuis les fichiers"""
        self.loaded_dictionaries.clear()
        self.intent_keywords = self._build_multilingual_intent_keywords_from_dicts()
        self.intent_patterns = self._build_multilingual_intent_patterns_from_dicts()
        logger.info("Dictionnaires rechargés")

    def get_classifier_stats(self) -> Dict:
        """Retourne les statistiques du classificateur"""
        return {
            "version": "multilingual_v3.0_dict_based",
            "supported_languages": list(self.supported_languages),
            "intent_types": [intent.value for intent in IntentType],
            "translation_service_available": self.translation_service is not None,
            "dictionaries_loaded": len(self.loaded_dictionaries),
            "cache_size": len(self.intent_keywords_cache),
            "total_keywords": sum(
                len(lang_keywords)
                for intent_keywords in self.intent_keywords.values()
                for lang_keywords in intent_keywords.values()
            ),
            "total_patterns": sum(
                len(lang_patterns)
                for intent_patterns in self.intent_patterns.values()
                for lang_patterns in intent_patterns.values()
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
            "dictionaries_used": list(self.loaded_dictionaries.keys()),
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
