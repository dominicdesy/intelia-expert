# -*- coding: utf-8 -*-
"""
ood_detector.py - Détecteur hors-domaine intelligent et multilingue
Version 2.1 - CORRECTION CIBLÉE: service de traduction avec fallback robuste
"""

import logging
import json
import os
import re
from utils.types import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from enum import Enum

# Imports configuration multilingue
from config.config import (
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    DOMAIN_KEYWORDS,
)

# Imports service traduction et utilitaires
from utils.utilities import METRICS, detect_language_enhanced
from utils.imports_and_dependencies import UNIDECODE_AVAILABLE

if UNIDECODE_AVAILABLE:
    from unidecode import unidecode

logger = logging.getLogger(__name__)


class DomainRelevance(Enum):
    """Niveaux de pertinence pour le domaine avicole"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    GENERIC = "generic"
    BLOCKED = "blocked"


@dataclass
class DomainScore:
    """Score détaillé du domaine avec contexte multilingue"""

    final_score: float
    relevance_level: DomainRelevance
    domain_words: List[str]
    blocked_terms: List[str]
    confidence_boosters: Dict[str, float]
    threshold_applied: float
    reasoning: str
    translation_used: bool = False
    original_language: str = "fr"
    translated_query: Optional[str] = None


class MultilingualOODDetector:
    """
    Détecteur hors-domaine intelligent avec support multilingue intégré
    CORRECTION: Gestion robuste du service de traduction avec fallback
    """

    def __init__(self, blocked_terms_path: str = None):
        self.blocked_terms = self._load_blocked_terms(blocked_terms_path)

        # CORRECTION: Initialisation sécurisée du service de traduction
        self.translation_service = self._init_translation_service_safe()
        self.translation_cache = {}

        # Configuration multilingue
        self.supported_languages = SUPPORTED_LANGUAGES
        self.default_language = DEFAULT_LANGUAGE

        # Vocabulaire dynamique depuis dictionnaire universel
        self.domain_vocabulary = self._build_domain_vocabulary_from_service()

        # Seuils adaptatifs selon le contexte et la langue
        self.adaptive_thresholds = {
            "technical_query": 0.10,
            "numeric_query": 0.15,
            "standard_query": 0.20,
            "generic_query": 0.30,
            "suspicious_query": 0.50,
        }

        # Ajustements par langue (plus permissif pour langues à script non-latin)
        self.language_adjustments = {
            "fr": 1.0,
            "en": 0.95,
            "es": 0.90,
            "it": 0.90,
            "pt": 0.90,
            "de": 0.85,
            "nl": 0.85,
            "pl": 0.80,
            "hi": 0.70,  # Plus permissif pour Hindi
            "th": 0.70,  # Plus permissif pour Thaï
            "zh": 0.70,  # Plus permissif pour Chinois
            "id": 0.85,
        }

    def _init_translation_service_safe(self):
        """CORRECTION: Initialise le service de traduction avec gestion d'erreurs robuste"""
        try:
            # Tentative d'import et d'initialisation
            from utils.translation_service import get_translation_service

            # Récupération du service existant
            service = get_translation_service()

            if service is None:
                logger.debug(
                    "Service de traduction non initialisé, tentative d'initialisation..."
                )

                # Import des configurations si disponibles
                try:
                    from utils.translation_service import (
                        init_global_translation_service,
                    )
                    from config.config import (
                        UNIVERSAL_DICT_PATH,
                        GOOGLE_TRANSLATE_API_KEY,
                        ENABLE_GOOGLE_TRANSLATE_FALLBACK,
                        TRANSLATION_CACHE_SIZE,
                        TRANSLATION_CACHE_TTL,
                        TRANSLATION_CONFIDENCE_THRESHOLD,
                    )

                    # Initialisation avec configuration
                    service = init_global_translation_service(
                        dict_path=UNIVERSAL_DICT_PATH,
                        supported_languages=SUPPORTED_LANGUAGES,
                        google_api_key=GOOGLE_TRANSLATE_API_KEY,
                        enable_google_fallback=ENABLE_GOOGLE_TRANSLATE_FALLBACK,
                        cache_size=TRANSLATION_CACHE_SIZE,
                        cache_ttl=TRANSLATION_CACHE_TTL,
                        confidence_threshold=TRANSLATION_CONFIDENCE_THRESHOLD,
                    )

                    if service:
                        logger.info("Service de traduction initialisé avec succès")
                    else:
                        logger.debug("Échec d'initialisation du service de traduction")

                except ImportError:
                    logger.debug(
                        "Configuration de traduction manquante, utilisation fallback"
                    )
                    service = None

            elif hasattr(service, "is_healthy") and not service.is_healthy():
                logger.debug("Service de traduction disponible mais non fonctionnel")
                service = None
            else:
                logger.debug("Service de traduction disponible et fonctionnel")

            return service

        except Exception as e:
            logger.debug(f"Erreur initialisation service de traduction: {e}")
            return None

    def _load_blocked_terms(self, path: str = None) -> Dict[str, List[str]]:
        """Charge les termes explicitement bloqués depuis JSON"""
        if path is None:
            possible_paths = [
                os.getenv("BLOCKED_TERMS_FILE", ""),
                "/app/config/blocked_terms.json",
                "config/blocked_terms.json",
                os.path.join(
                    os.path.dirname(__file__), "..", "config", "blocked_terms.json"
                ),
            ]
        else:
            possible_paths = [path]

        for attempt_path in possible_paths:
            if not attempt_path or not os.path.exists(attempt_path):
                continue
            try:
                with open(attempt_path, "r", encoding="utf-8") as f:
                    blocked_terms = json.load(f)
                logger.info(f"Termes bloqués chargés depuis: {attempt_path}")
                return blocked_terms
            except Exception as e:
                logger.warning(f"Erreur lecture {attempt_path}: {e}")
                continue

        # Fallback avec termes critiques minimaux
        fallback_terms = {
            "adult_content": ["porn", "sex", "nude", "adult", "xxx"],
            "crypto_finance": ["bitcoin", "crypto", "blockchain", "trading", "forex"],
            "politics": ["election", "politics", "vote", "government"],
            "entertainment": ["movie", "film", "netflix", "game", "gaming"],
            "sports": ["football", "soccer", "basketball", "tennis"],
            "technology": ["iphone", "android", "computer", "software", "app"],
        }
        logger.warning(
            f"Utilisation des termes bloqués fallback: {len(fallback_terms)} catégories"
        )
        return fallback_terms

    def _build_domain_vocabulary_from_service(self) -> Dict[DomainRelevance, Set[str]]:
        """
        Construit le vocabulaire du domaine depuis le service de traduction universel
        CORRECTION: Fallback robuste si service indisponible
        """
        vocabulary = {level: set() for level in DomainRelevance}

        # Base à partir de DOMAIN_KEYWORDS (configuration)
        high_priority_base = set()
        for keyword in DOMAIN_KEYWORDS[:20]:  # Les 20 premiers sont haute priorité
            high_priority_base.add(keyword.lower())

        medium_priority_base = set()
        for keyword in DOMAIN_KEYWORDS[20:40]:  # Les suivants sont moyenne priorité
            medium_priority_base.add(keyword.lower())

        low_priority_base = set()
        for keyword in DOMAIN_KEYWORDS[40:]:  # Le reste est basse priorité
            low_priority_base.add(keyword.lower())

        # Extension via service de traduction si disponible
        if self.translation_service:
            try:
                # Récupérer termes par domaine depuis le dictionnaire universel
                aviculture_domains = [
                    "genetic_lines",
                    "performance_metrics",
                    "equipment_types",
                    "health_symptoms",
                    "feeding_systems",
                    "housing_types",
                ]

                for domain in aviculture_domains:
                    # Récupérer pour chaque langue supportée
                    for lang in self.supported_languages:
                        if hasattr(self.translation_service, "get_domain_terms"):
                            terms = self.translation_service.get_domain_terms(
                                domain, lang
                            )
                        else:
                            # Fallback si méthode non disponible
                            terms = []

                        # Classification automatique selon le domaine
                        if domain in ["genetic_lines", "performance_metrics"]:
                            high_priority_base.update(term.lower() for term in terms)
                        elif domain in ["equipment_types", "health_symptoms"]:
                            medium_priority_base.update(term.lower() for term in terms)
                        else:
                            low_priority_base.update(term.lower() for term in terms)

                logger.debug(
                    f"Vocabulaire étendu via service traduction: "
                    f"{len(high_priority_base)} haute priorité, "
                    f"{len(medium_priority_base)} moyenne, "
                    f"{len(low_priority_base)} basse"
                )

            except Exception as e:
                logger.debug(
                    f"Erreur extension vocabulaire via service traduction: {e}"
                )
        else:
            # CORRECTION: Vocabulaire étendu de fallback
            logger.debug(
                "Service traduction indisponible, utilisation vocabulaire étendu de fallback"
            )

            # Ajouter termes multilingues essentiels
            high_priority_base.update(
                [
                    "ross",
                    "cobb",
                    "hubbard",
                    "isa",
                    "aviagen",
                    "peterson",
                    "fcr",
                    "adr",
                    "adg",
                    "epef",
                    "eef",
                    "conversion",
                    "broiler",
                    "poulet",
                    "pollo",
                    "frango",
                    "鸡",
                    "دجاج",
                    "poultry",
                    "volaille",
                    "avicultura",
                    "aviculture",
                ]
            )

            medium_priority_base.update(
                [
                    "feed",
                    "nutrition",
                    "alimentation",
                    "pienso",
                    "ração",
                    "weight",
                    "poids",
                    "peso",
                    "waga",
                    "重量",
                    "وزن",
                    "mortality",
                    "mortalité",
                    "mortalidad",
                    "मृत्यु दर",
                    "housing",
                    "élevage",
                    "crianza",
                    "alojamiento",
                ]
            )

        # Construction finale du vocabulaire hiérarchisé
        vocabulary[DomainRelevance.HIGH] = high_priority_base
        vocabulary[DomainRelevance.MEDIUM] = medium_priority_base
        vocabulary[DomainRelevance.LOW] = low_priority_base

        # Termes génériques multilingues (mots-outils)
        vocabulary[DomainRelevance.GENERIC] = {
            "comment",
            "how",
            "quoi",
            "what",
            "pourquoi",
            "why",
            "quand",
            "when",
            "où",
            "where",
            "combien",
            "how much",
            "quel",
            "quelle",
            "which",
            "que",
            "qui",
            "who",
            "meilleur",
            "best",
            "optimal",
            "idéal",
            "ideal",
            "कैसे",
            "क्या",
            "क्यों",
            "कब",
            "कहाँ",
            "कितना",
            "कौन",
            "कौन सा",
            "如何",
            "什么",
            "为什么",
            "什么时候",
            "哪里",
            "多少",
            "哪个",
            "谁",
            "อย่างไร",
            "อะไร",
            "ทำไม",
            "เมื่อไหร่",
            "ที่ไหน",
            "เท่าไหร่",
            "ไหน",
            "ใคร",
        }

        return vocabulary

    # ===== MÉTHODES PUBLIQUES =====

    def calculate_ood_score_multilingual(
        self, query: str, intent_result=None, language: str = None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Point d'entrée principal multilingue
        Détecte la langue automatiquement si non fournie
        """
        # Détection automatique de la langue si nécessaire
        if language is None:
            detection_result = detect_language_enhanced(query)
            language = detection_result.language
            logger.debug(
                f"Langue détectée automatiquement: {language} (confiance: {detection_result.confidence:.2f})"
            )

        # Validation langue supportée
        actual_language = (
            language.language if hasattr(language, "language") else language
        )
        if actual_language not in self.supported_languages:
            logger.warning(
                f"Langue non supportée: {actual_language}, utilisation fallback {self.default_language}"
            )
            language = self.default_language
        else:
            language = actual_language

        # Traitement selon la stratégie de langue
        return self._calculate_ood_score_for_language(query, intent_result, language)

    def calculate_ood_score(
        self, query: str, intent_result=None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Méthode de compatibilité pour l'interface existante"""
        return self.calculate_ood_score_multilingual(
            query, intent_result, self.default_language
        )

    # ===== LOGIQUE PRINCIPALE =====

    def _calculate_ood_score_for_language(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Calcule le score OOD selon la langue avec logique adaptée
        """
        try:
            # Stratégie selon la langue
            if language in ["fr", "en"]:
                # Langues principales : traitement direct optimisé
                return self._calculate_ood_direct(query, intent_result, language)

            elif language in ["es", "de", "it", "pt", "nl", "pl", "id"]:
                # Langues latines/européennes : traduction via service
                return self._calculate_ood_with_translation(
                    query, intent_result, language
                )

            else:
                # Langues à script non-latin : analyse adaptée + fallback
                return self._calculate_ood_non_latin(query, intent_result, language)

        except Exception as e:
            logger.error(f"Erreur calcul OOD pour langue {language}: {e}")
            return self._calculate_ood_fallback(query, intent_result, language)

    def _calculate_ood_direct(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul OOD direct pour français/anglais (pas de traduction nécessaire)"""

        # Normalisation adaptée à la langue
        normalized_query = self._normalize_query(query, language)
        words = normalized_query.split()

        if not words:
            return False, 0.0, {"error": "empty_query", "language": language}

        # Analyse contextuelle
        context_analysis = self._analyze_query_context(
            normalized_query, words, intent_result
        )

        # Analyse du domaine
        domain_analysis = self._calculate_domain_relevance(
            words, context_analysis, language
        )

        # Détection termes bloqués
        blocked_analysis = self._detect_blocked_terms(normalized_query, words)

        # Application boosters contextuels
        boosted_score = self._apply_context_boosters(
            domain_analysis.final_score, context_analysis, intent_result
        )

        # Sélection seuil adaptatif
        base_threshold = self._select_adaptive_threshold(
            context_analysis, domain_analysis
        )
        adjusted_threshold = base_threshold * self.language_adjustments.get(
            language, 1.0
        )

        # Décision finale
        is_in_domain = (
            boosted_score > adjusted_threshold and not blocked_analysis["is_blocked"]
        )

        # Logging et métriques
        self._log_ood_decision(
            query,
            domain_analysis,
            boosted_score,
            adjusted_threshold,
            is_in_domain,
            language,
        )
        self._update_ood_metrics(domain_analysis, adjusted_threshold, is_in_domain)

        # Construction réponse détaillée
        score_details = {
            "vocab_score": domain_analysis.final_score,
            "boosted_score": boosted_score,
            "threshold_used": adjusted_threshold,
            "base_threshold": base_threshold,
            "language_adjustment": self.language_adjustments.get(language, 1.0),
            "domain_words_found": len(domain_analysis.domain_words),
            "blocked_terms_found": len(domain_analysis.blocked_terms),
            "context_type": context_analysis["type"],
            "relevance_level": domain_analysis.relevance_level.value,
            "reasoning": domain_analysis.reasoning,
            "language": language,
            "translation_used": False,
            "method": "direct",
        }

        return is_in_domain, boosted_score, score_details

    def _calculate_ood_with_translation(
        self, query: str, intent_result=None, language: str = "es"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """CORRECTION: Calcul OOD avec traduction via service universel"""

        if not self.translation_service:
            logger.debug(
                f"Service traduction indisponible, utilisation fallback pour langue {language}"
            )
            return self._calculate_ood_fallback(query, intent_result, language)

        try:
            # Traduction vers français via service universel
            translation_result = self.translation_service.translate_term(
                query, "fr", source_language=language, domain="general_poultry"
            )

            translated_query = translation_result.text
            translation_confidence = translation_result.confidence

            logger.debug(
                f"Traduction [{language}→fr]: '{query[:30]}...' → '{translated_query[:30]}...' (confiance: {translation_confidence:.2f})"
            )

            # Analyse OOD sur la version traduite
            is_in_domain, score, details = self._calculate_ood_direct(
                translated_query, intent_result, "fr"
            )

            # Ajustement du seuil pour traductions
            translation_penalty = 1.0 - (0.3 * (1.0 - translation_confidence))
            adjusted_threshold = details["threshold_used"] * translation_penalty
            is_in_domain = score > adjusted_threshold

            # Enrichissement des détails
            details.update(
                {
                    "original_language": language,
                    "original_query": query,
                    "translated_query": translated_query,
                    "translation_used": True,
                    "translation_confidence": translation_confidence,
                    "translation_penalty": translation_penalty,
                    "final_threshold": adjusted_threshold,
                    "translation_source": translation_result.source,
                    "method": "translation",
                }
            )

            self._log_ood_decision(
                query,
                None,
                score,
                adjusted_threshold,
                is_in_domain,
                language,
                translated_query,
            )

            return is_in_domain, score, details

        except Exception as e:
            logger.debug(f"Erreur traduction {language}: {e}, utilisation fallback")
            return self._calculate_ood_fallback(query, intent_result, language)

    def _calculate_ood_non_latin(
        self, query: str, intent_result=None, language: str = "hi"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul OOD adapté aux langues à script non-latin (Hindi, Chinois, Thaï)"""

        # Détection patterns universels d'abord
        universal_score = self._detect_universal_patterns(query, language)

        if universal_score > 0.3:
            # Score élevé sur patterns universels = probablement aviculture
            logger.debug(
                f"Patterns universels détectés [{language}]: score {universal_score:.2f}"
            )
            return (
                True,
                universal_score,
                {
                    "language": language,
                    "method": "universal_patterns",
                    "universal_score": universal_score,
                    "reasoning": f"Patterns aviculture universels détectés (score: {universal_score:.2f})",
                    "translation_used": False,
                },
            )

        # Sinon, essayer traduction si service disponible
        if self.translation_service:
            try:
                return self._calculate_ood_with_translation(
                    query, intent_result, language
                )
            except Exception as e:
                logger.debug(f"Traduction échouée pour {language}: {e}")

        # Fallback : analyse permissive
        return self._calculate_ood_fallback(query, intent_result, language)

    def _calculate_ood_fallback(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """CORRECTION: Méthode de fallback robuste avec vocabulaire multilingue étendu"""

        logger.debug(f"OOD Fallback [{language}]: '{query[:30]}...'")

        # Analyse de base avec vocabulaire multilingue étendu
        query_lower = query.lower()
        domain_score = 0.0
        matched_terms = []

        # Termes universels reconnus (multilingues)
        universal_terms = {
            # Lignées (multilingue)
            "ross",
            "cobb",
            "hubbard",
            "isa",
            "aviagen",
            "peterson",
            # Métriques universelles
            "fcr",
            "adr",
            "adg",
            "epef",
            "eef",
            # Mots génériques aviculture
            "broiler",
            "poultry",
            "chicken",
            "pullet",
            "hen",
            "poulet",
            "volaille",
            "aviculture",
            "élevage",
            "pollo",
            "ave",
            "crianza",
            "avicultura",
            "frango",
            "franga",
            "avicultura",
            "鸡",
            "家禽",
            "养殖",
            "饲养",
            "دجاج",
            "دواجن",
            "تربية",
        }

        # Recherche de termes pertinents
        for term in universal_terms:
            if term in query_lower:
                domain_score += 0.3
                matched_terms.append(term)

        # Boost pour valeurs numériques (probablement techniques)
        if re.search(r"\b\d+\s*(?:j|day|días?|jours?|天|يوم)\b", query_lower):
            domain_score += 0.4
            matched_terms.append("age_numeric")

        if re.search(r"\b\d+\.?\d*\s*(?:kg|g|lb|%)\b", query_lower):
            domain_score += 0.3
            matched_terms.append("weight_numeric")

        # Détermination du seuil ajusté par langue
        base_threshold = 0.30 if language in ["hi", "zh", "th", "ar"] else 0.20
        language_adjustment = self.language_adjustments.get(language, 0.80)
        adjusted_threshold = base_threshold * language_adjustment

        is_in_domain = domain_score >= adjusted_threshold

        details = {
            "method": "fallback",
            "language": language,
            "score": domain_score,
            "threshold_used": adjusted_threshold,
            "base_threshold": base_threshold,
            "language_adjustment": language_adjustment,
            "matched_terms": matched_terms,
            "term_count": len(matched_terms),
            "translation_used": False,
            "fallback_reason": "translation_service_unavailable",
        }

        # Log de la décision
        decision = "ACCEPTÉ" if is_in_domain else "REJETÉ"
        logger.info(
            f"OOD Fallback [{language}]: '{query[:30]}...' | "
            f"Score: {domain_score:.3f} | {decision}"
        )

        return is_in_domain, domain_score, details

    # ===== MÉTHODES UTILITAIRES =====

    def _normalize_query(self, query: str, language: str) -> str:
        """Normalisation adaptée selon la langue"""
        if not query:
            return ""

        # Pour scripts non-latins, préserver les caractères spéciaux
        if language in ["hi", "th", "zh"]:
            normalized = query.lower()
            # Nettoyage minimal pour préserver les scripts
            normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)
            normalized = re.sub(r"\s+", " ", normalized).strip()
            return normalized

        # Pour scripts latins, normalisation standard
        normalized = unidecode(query).lower() if UNIDECODE_AVAILABLE else query.lower()
        normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Expansion acronymes
        acronym_expansions = {
            "ic": "indice conversion",
            "fcr": "feed conversion ratio",
            "pv": "poids vif",
            "gmq": "gain moyen quotidien",
        }

        for acronym, expansion in acronym_expansions.items():
            normalized = re.sub(rf"\b{acronym}\b", expansion, normalized)

        return normalized

    def _analyze_query_context(
        self, query: str, words: List[str], intent_result=None
    ) -> Dict:
        """Analyse contextuelle multilingue"""
        context = {
            "type": "standard_query",
            "technical_indicators": [],
            "numeric_indicators": [],
            "specificity_level": "medium",
            "intent_confidence": 0.0,
        }

        # Détection indicateurs techniques multilingues
        technical_patterns = [
            (
                r"\b(?:fcr|ic|indice|feed.conversion|料肉比|फसीआर)\b",
                "conversion_metric",
            ),
            (r"\b(?:ross|cobb|hubbard|isa|罗斯|科宝|रॉस|कॉब)\s*\d*\b", "genetic_line"),
            (
                r"\b\d+\s*(?:jour|day|semaine|week|dia|tag|วัน|天|दिन|hari)s?\b",
                "age_specification",
            ),
            (
                r"\b\d+[.,]?\d*\s*(?:g|kg|gramme|gram|克|公斤|ग्राम|किलो)\b",
                "weight_measure",
            ),
            (r"\b\d+[.,]?\d*\s*%\b", "percentage_value"),
        ]

        for pattern, indicator_type in technical_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                context["technical_indicators"].append(
                    {"type": indicator_type, "matches": matches, "count": len(matches)}
                )

        # Classification type requête
        if len(context["technical_indicators"]) >= 2:
            context["type"] = "technical_query"
            context["specificity_level"] = "high"

        # Analyse intention si disponible
        if intent_result:
            try:
                if hasattr(intent_result, "confidence"):
                    context["intent_confidence"] = float(intent_result.confidence)
                if hasattr(intent_result, "detected_entities"):
                    entities = intent_result.detected_entities
                    if isinstance(entities, dict) and len(entities) >= 2:
                        context["type"] = "technical_query"
                        context["specificity_level"] = "very_high"
            except Exception as e:
                logger.debug(f"Erreur analyse intention: {e}")

        return context

    def _calculate_domain_relevance(
        self, words: List[str], context_analysis: Dict, language: str
    ) -> DomainScore:
        """Calcul de pertinence du domaine avec support multilingue"""
        domain_words = []
        relevance_scores = {level: 0 for level in DomainRelevance}

        # Analyse mot par mot contre vocabulaire
        for word in words:
            word_clean = word.strip().lower()
            if len(word_clean) < 2:
                continue

            for level, vocabulary in self.domain_vocabulary.items():
                if word_clean in vocabulary:
                    domain_words.append(word_clean)
                    relevance_scores[level] += 1
                    break

        # Calcul score pondéré
        weight_multipliers = {
            DomainRelevance.HIGH: 1.0,
            DomainRelevance.MEDIUM: 0.6,
            DomainRelevance.LOW: 0.3,
            DomainRelevance.GENERIC: 0.1,
        }

        weighted_score = sum(
            count * weight_multipliers.get(level, 0.1)
            for level, count in relevance_scores.items()
            if level != DomainRelevance.BLOCKED
        )

        significant_words = [w for w in words if len(w.strip()) >= 2]
        base_score = weighted_score / len(significant_words) if significant_words else 0

        # Détermination niveau pertinence
        if relevance_scores[DomainRelevance.HIGH] >= 2:
            overall_relevance = DomainRelevance.HIGH
        elif (
            relevance_scores[DomainRelevance.HIGH] >= 1
            or relevance_scores[DomainRelevance.MEDIUM] >= 2
        ):
            overall_relevance = DomainRelevance.MEDIUM
        elif (
            sum(
                relevance_scores[level]
                for level in [
                    DomainRelevance.HIGH,
                    DomainRelevance.MEDIUM,
                    DomainRelevance.LOW,
                ]
            )
            >= 1
        ):
            overall_relevance = DomainRelevance.LOW
        else:
            overall_relevance = DomainRelevance.GENERIC

        # Bonus contextuel
        context_bonus = 0.0
        if context_analysis["type"] == "technical_query":
            context_bonus += 0.15
        if len(context_analysis["technical_indicators"]) >= 1:
            context_bonus += 0.1

        final_score = min(1.0, base_score + context_bonus)

        confidence_boosters = {
            "context_bonus": context_bonus,
            "high_relevance_words": relevance_scores[DomainRelevance.HIGH],
            "medium_relevance_words": relevance_scores[DomainRelevance.MEDIUM],
            "technical_indicators": len(context_analysis["technical_indicators"]),
        }

        reasoning = f"Mots domaine: {len(domain_words)}/{len(significant_words)} | Niveau: {overall_relevance.value} | Score: {final_score:.3f}"

        return DomainScore(
            final_score=final_score,
            relevance_level=overall_relevance,
            domain_words=domain_words,
            blocked_terms=[],
            confidence_boosters=confidence_boosters,
            threshold_applied=0.0,
            reasoning=reasoning,
            original_language=language,
        )

    def _detect_blocked_terms(self, query: str, words: List[str]) -> Dict:
        """Détection termes bloqués"""
        blocked_found = []
        for category, terms in self.blocked_terms.items():
            for term in terms:
                if term.lower() in query:
                    blocked_found.append(term)

        is_blocked = len(blocked_found) >= 2

        return {
            "is_blocked": is_blocked,
            "blocked_terms": blocked_found,
            "block_score": len(blocked_found) / max(len(words), 1),
        }

    def _detect_universal_patterns(self, query: str, language: str) -> float:
        """
        Détection de patterns aviculture universels pour langues non-latines
        Reconnaît les termes techniques indépendamment de la langue
        """
        score = 0.0

        # Marques universelles (même écriture dans toutes langues)
        universal_brands = ["cobb", "ross", "hubbard", "isa", "lohmann"]
        brand_matches = sum(
            1 for brand in universal_brands if brand.lower() in query.lower()
        )
        score += brand_matches * 0.4

        # Nombres avec unités (patterns universels)
        weight_patterns = [
            r"\d+\s*(?:g|kg|gram|kilogram|公斤|克|किलो|ग्राम)",
            r"\d+\s*(?:day|jour|วัน|天|दिन|hari)",
            r"\d+\s*%",
        ]

        for pattern in weight_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                score += 0.15

        # Termes techniques spécifiques par langue
        if language == "hi":
            hindi_terms = ["मुर्गी", "चिकन", "कॉब", "रॉस", "वजन", "दिन", "अंडा"]
            hindi_matches = sum(1 for term in hindi_terms if term in query)
            score += hindi_matches * 0.3

        elif language == "zh":
            chinese_terms = ["鸡", "鸡肉", "肉鸡", "蛋鸡", "科宝", "罗斯", "体重", "天"]
            chinese_matches = sum(1 for term in chinese_terms if term in query)
            score += chinese_matches * 0.3

        elif language == "th":
            thai_terms = ["ไก่", "เนื้อไก่", "คอบบ์", "รอสส์", "น้ำหนัก", "วัน", "ไข่"]
            thai_matches = sum(1 for term in thai_terms if term in query)
            score += thai_matches * 0.3

        return min(1.0, score)

    def _apply_context_boosters(
        self, base_score: float, context_analysis: Dict, intent_result=None
    ) -> float:
        """Application boosters contextuels"""
        boosted_score = base_score

        if context_analysis["type"] == "technical_query":
            boosted_score += 0.15

        technical_count = len(context_analysis.get("technical_indicators", []))
        if technical_count >= 2:
            boosted_score += 0.1
        elif technical_count == 1:
            boosted_score += 0.05

        if context_analysis["intent_confidence"] > 0.8:
            boosted_score += 0.1

        return min(0.98, boosted_score)

    def _select_adaptive_threshold(
        self, context_analysis: Dict, domain_analysis: DomainScore
    ) -> float:
        """Sélection seuil adaptatif"""
        base_threshold = self.adaptive_thresholds.get(
            context_analysis["type"], self.adaptive_thresholds["standard_query"]
        )

        # Ajustements selon contexte
        if (
            context_analysis["specificity_level"] == "low"
            and domain_analysis.relevance_level == DomainRelevance.GENERIC
        ):
            base_threshold += 0.1

        if len(context_analysis["technical_indicators"]) >= 2:
            base_threshold -= 0.05

        return max(0.05, min(0.6, base_threshold))

    def _log_ood_decision(
        self,
        query: str,
        domain_analysis: Optional[DomainScore],
        score: float,
        threshold: float,
        is_in_domain: bool,
        language: str,
        translated_query: str = None,
    ) -> None:
        """Logging multilingue des décisions"""
        decision = "ACCEPTÉ" if is_in_domain else "REJETÉ"

        if translated_query:
            logger.debug(
                f"OOD {decision} [{language}]: '{query[:30]}...' → '{translated_query[:30]}...' | Score: {score:.3f} vs {threshold:.3f}"
            )
        else:
            logger.debug(
                f"OOD {decision} [{language}]: '{query[:40]}...' | Score: {score:.3f} vs {threshold:.3f}"
            )

    def _update_ood_metrics(
        self,
        domain_analysis: Optional[DomainScore],
        threshold: float,
        is_in_domain: bool,
    ) -> None:
        """Mise à jour métriques"""
        try:
            if is_in_domain:
                score_value = domain_analysis.final_score if domain_analysis else 0.5
                relevance = (
                    domain_analysis.relevance_level.value
                    if domain_analysis
                    else "unknown"
                )
                METRICS.ood_accepted(score_value, relevance)
            else:
                score_value = domain_analysis.final_score if domain_analysis else 0.0
                METRICS.ood_filtered(score_value, "threshold_not_met")
        except Exception as e:
            logger.warning(f"Erreur MAJ métriques OOD: {e}")

    # ===== MÉTHODES UTILITAIRES ET STATS =====

    def get_detector_stats(self) -> Dict:
        """Statistiques du détecteur multilingue"""
        vocab_stats = {
            level.value: len(terms) for level, terms in self.domain_vocabulary.items()
        }
        blocked_stats = {
            category: len(terms) for category, terms in self.blocked_terms.items()
        }

        return {
            "version": "multilingual_v2.1_corrected",
            "vocabulary_stats": vocab_stats,
            "blocked_terms_stats": blocked_stats,
            "adaptive_thresholds": self.adaptive_thresholds.copy(),
            "language_adjustments": self.language_adjustments.copy(),
            "supported_languages": list(self.supported_languages),
            "translation_service_available": self.translation_service is not None,
            "translation_service_healthy": (
                self.translation_service.is_healthy()
                if self.translation_service
                and hasattr(self.translation_service, "is_healthy")
                else False
            ),
            "total_domain_terms": sum(
                len(terms) for terms in self.domain_vocabulary.values()
            ),
            "integration_features": [
                "universal_translation_service_with_fallback",
                "dynamic_vocabulary_from_dict",
                "language_specific_analysis",
                "unicode_script_preservation",
                "adaptive_thresholds_by_language",
                "robust_error_handling",
            ],
        }

    def test_query_analysis(self, query: str, language: str = None) -> Dict:
        """Test et diagnostic d'une requête"""
        is_in_domain, score, details = self.calculate_ood_score_multilingual(
            query, None, language
        )

        return {
            "original_query": query,
            "detected_language": details.get("language", "unknown"),
            "final_score": score,
            "is_in_domain": is_in_domain,
            "decision": "ACCEPTED" if is_in_domain else "REJECTED",
            "method": details.get("method", "unknown"),
            "translation_used": details.get("translation_used", False),
            "details": details,
        }


# ===== CLASSES DE COMPATIBILITÉ =====


class EnhancedOODDetector(MultilingualOODDetector):
    """Alias pour compatibilité avec le code existant"""

    def __init__(self, blocked_terms_path: str = None, openai_client=None):
        # Note: openai_client ignoré car on utilise le service de traduction universel
        super().__init__(blocked_terms_path)

    def calculate_ood_score(
        self, query: str, intent_result=None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Méthode de compatibilité"""
        return self.calculate_ood_score_multilingual(
            query, intent_result, self.default_language
        )


# ===== FONCTIONS FACTORY =====


def create_ood_detector(
    blocked_terms_path: str = None, openai_client=None
) -> EnhancedOODDetector:
    """Crée une instance du détecteur OOD avec compatibilité"""
    return EnhancedOODDetector(blocked_terms_path)


def create_multilingual_ood_detector(
    blocked_terms_path: str = None,
) -> MultilingualOODDetector:
    """Crée une instance du détecteur OOD multilingue complet"""
    return MultilingualOODDetector(blocked_terms_path)
