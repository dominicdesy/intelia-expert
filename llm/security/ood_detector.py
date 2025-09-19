# -*- coding: utf-8 -*-
"""
ood_detector.py - Détecteur hors-domaine intelligent et multilingue
Version corrigée avec support complet pour toutes les langues via traduction
CORRECTION: Ajout de la méthode publique calculate_ood_score_multilingual manquante
"""

import logging
import json
import os
import re
import asyncio
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from utils.utilities import METRICS
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
    """Score détaillé du domaine"""

    final_score: float
    relevance_level: DomainRelevance
    domain_words: List[str]
    blocked_terms: List[str]
    confidence_boosters: Dict[str, float]
    threshold_applied: float
    reasoning: str
    translation_used: bool = False
    original_language: str = "fr"


class MultilingualOODDetector:
    """Détecteur hors-domaine intelligent avec support multilingue complet"""

    def __init__(self, blocked_terms_path: str = None, openai_client=None):
        self.blocked_terms = self._load_blocked_terms(blocked_terms_path)
        self.domain_vocabulary = self._build_domain_vocabulary()
        self.openai_client = openai_client
        self.translation_cache = {}

        # Langues supportées (basé sur languages.json)
        self.supported_languages = [
            "fr",
            "en",
            "es",
            "de",
            "it",
            "pt",
            "nl",
            "pl",
            "hi",
            "id",
            "th",
            "zh",
        ]

        # Seuils adaptatifs selon le contexte et la langue
        self.adaptive_thresholds = {
            "technical_query": 0.10,
            "numeric_query": 0.15,
            "standard_query": 0.20,
            "generic_query": 0.30,
            "suspicious_query": 0.50,
        }

        # Ajustements par langue (plus permissif pour langues éloignées)
        self.language_adjustments = {
            "fr": 1.0,  # Langue de référence
            "en": 0.95,  # Très proche
            "es": 0.90,  # Langues latines
            "it": 0.90,
            "pt": 0.90,
            "de": 0.85,  # Germanique
            "nl": 0.85,
            "pl": 0.80,  # Slave
            "hi": 0.75,  # Scripts non-latins, plus permissif
            "th": 0.75,
            "zh": 0.75,
            "id": 0.85,  # Austronésien mais script latin
        }

    def _load_blocked_terms(self, path: str = None) -> Dict[str, List[str]]:
        """Charge les termes explicitement bloqués"""
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
            "politics": ["election", "politics", "vote", "government", "politician"],
            "entertainment": ["movie", "film", "cinema", "netflix", "game", "gaming"],
            "sports": ["football", "soccer", "basketball", "tennis", "sport"],
            "technology": ["iphone", "android", "computer", "software", "app"],
        }
        logger.warning(
            f"Utilisation des termes bloqués fallback: {len(fallback_terms)} catégories"
        )
        return fallback_terms

    def _build_domain_vocabulary(self) -> Dict[DomainRelevance, Set[str]]:
        """Construit un vocabulaire hiérarchisé du domaine avicole (français/anglais de base)"""
        return {
            DomainRelevance.HIGH: {
                # Termes hautement spécifiques à l'aviculture
                "fcr",
                "ic",
                "indice",
                "conversion",
                "alimentaire",
                "ponte",
                "pondeuse",
                "pondeuses",
                "œuf",
                "œufs",
                "oeufs",
                "egg",
                "eggs",
                "poulet",
                "poulets",
                "poule",
                "poules",
                "poussin",
                "poussins",
                "broiler",
                "broilers",
                "layer",
                "layers",
                "chick",
                "chicks",
                "ross",
                "cobb",
                "hubbard",
                "isa",
                "lohmann",
                "hy-line",
                "aviculture",
                "avicole",
                "poultry",
                "fowl",
                "couvoir",
                "incubation",
                "éclosion",
                "hatchery",
                "hatching",
                "vaccination",
                "vaccin",
                "prophylaxie",
                "biosécurité",
                "mortalité",
                "mortality",
                "morbidité",
                "viabilité",
                "chair",
                "meat",
                "carcasse",
                "carcass",
                "rendement",
                "yield",
            },
            DomainRelevance.MEDIUM: {
                # Termes liés à l'élevage et la nutrition animale
                "élevage",
                "éleveur",
                "farm",
                "farming",
                "farmer",
                "alimentation",
                "aliment",
                "aliments",
                "feed",
                "feeding",
                "nutrition",
                "nutritionnel",
                "nutritive",
                "nutriment",
                "protéine",
                "protéines",
                "protein",
                "proteins",
                "énergie",
                "energy",
                "calorie",
                "calories",
                "kcal",
                "vitamines",
                "minéraux",
                "calcium",
                "phosphore",
                "croissance",
                "growth",
                "développement",
                "development",
                "poids",
                "weight",
                "masse",
                "mass",
                "gramme",
                "kg",
                "performance",
                "productivité",
                "productivity",
                "efficacité",
                "santé",
                "health",
                "maladie",
                "disease",
                "pathologie",
                "vétérinaire",
                "veterinary",
                "traitement",
                "treatment",
                "logement",
                "housing",
                "bâtiment",
                "building",
                "poulailler",
                "température",
                "temperature",
                "ventilation",
                "éclairage",
                "densité",
                "density",
                "espace",
                "space",
                "surface",
            },
            DomainRelevance.LOW: {
                # Termes agricoles généraux
                "agriculture",
                "agricultural",
                "rural",
                "campagne",
                "animal",
                "animaux",
                "animals",
                "bétail",
                "livestock",
                "ferme",
                "exploitation",
                "production",
                "producteur",
                "qualité",
                "quality",
                "sécurité",
                "safety",
                "hygiène",
                "économique",
                "economic",
                "coût",
                "cost",
                "prix",
                "price",
                "marché",
                "market",
                "vente",
                "sale",
                "commercial",
                "environnement",
                "environmental",
                "durable",
                "sustainable",
                "biologique",
                "organic",
                "naturel",
                "natural",
                "règlement",
                "regulation",
                "norme",
                "standard",
                "label",
            },
            DomainRelevance.GENERIC: {
                # Mots-outils et termes génériques
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
                "recommandé",
                "recommended",
                "conseiller",
                "advice",
                "problème",
                "problem",
                "solution",
                "aide",
                "help",
                "information",
                "données",
                "data",
                "étude",
                "study",
                "exemple",
                "example",
                "cas",
                "case",
                "situation",
                "méthode",
                "method",
                "technique",
                "technologie",
                "système",
                "system",
                "processus",
                "process",
            },
        }

    async def calculate_ood_score(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Point d'entrée principal avec support multilingue automatique"""

        # Si la langue est français ou anglais, traitement direct
        if language in ["fr", "en"]:
            return await self._calculate_ood_score_direct(
                query, intent_result, language
            )

        # Pour les autres langues, utiliser la traduction
        return await self._calculate_ood_score_multilingual(
            query, intent_result, language
        )

    async def _calculate_ood_score_direct(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul OOD direct pour français/anglais"""

        # Normalisation adaptée (sans destruction des scripts non-latins)
        normalized_query = self._normalize_query_preserve_script(query, language)
        words = normalized_query.split()

        if not words:
            return False, 0.0, {"error": "empty_query"}

        # Analyse contextuelle
        context_analysis = self._analyze_query_context(
            normalized_query, words, intent_result
        )

        # Calcul du score de domaine
        domain_analysis = self._calculate_domain_relevance(words, context_analysis)

        # Détection de termes bloqués
        blocked_analysis = self._detect_blocked_terms(normalized_query, words)

        # Application de boosters contextuels
        boosted_score = self._apply_context_boosters(
            domain_analysis.final_score, context_analysis, intent_result
        )

        # Sélection du seuil adaptatif avec ajustement linguistique
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
            words,
            domain_analysis,
            boosted_score,
            adjusted_threshold,
            is_in_domain,
        )
        self._update_ood_metrics(domain_analysis, adjusted_threshold, is_in_domain)

        # Construction de la réponse détaillée
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
            "confidence_boosters": domain_analysis.confidence_boosters,
            "reasoning": domain_analysis.reasoning,
            "language": language,
            "translation_used": False,
        }

        return is_in_domain, boosted_score, score_details

    async def _calculate_ood_score_multilingual(
        self, query: str, intent_result=None, language: str = "hi"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul OOD avec traduction automatique pour langues non-françaises/anglaises"""

        try:
            # Tentative de traduction vers le français
            translated_query = await self._translate_to_french(query, language)

            if not translated_query or translated_query == query:
                # Traduction échouée, utiliser l'analyse de fallback
                return await self._fallback_analysis(query, language)

            # Analyse OOD sur la version traduite
            is_in_domain, score, details = await self._calculate_ood_score_direct(
                translated_query, intent_result, "fr"
            )

            # Ajustement du seuil pour les langues traduites (plus permissif)
            translation_adjustment = self.language_adjustments.get(language, 0.75)
            adjusted_threshold = details["threshold_used"] * translation_adjustment
            is_in_domain = score > adjusted_threshold

            # Enrichir les détails avec les informations de traduction
            details.update(
                {
                    "original_language": language,
                    "original_query": query,
                    "translated_query": translated_query,
                    "translation_used": True,
                    "translation_adjustment": translation_adjustment,
                    "final_threshold": adjusted_threshold,
                    "final_decision_overridden": details["threshold_used"]
                    != adjusted_threshold,
                }
            )

            # Log spécifique pour traductions
            logger.debug(
                f"OOD Multilingue [{language}]: '{query[:30]}...' -> "
                f"'{translated_query[:30]}...' | Score: {score:.3f} | "
                f"Seuil ajusté: {adjusted_threshold:.3f} | "
                f"Décision: {'ACCEPTÉ' if is_in_domain else 'REJETÉ'}"
            )

            return is_in_domain, score, details

        except Exception as e:
            logger.warning(f"Erreur traduction {language}: {e}")
            # Fallback robuste
            return await self._fallback_analysis(query, language)

    async def _translate_to_french(self, query: str, source_lang: str) -> str:
        """Traduction vers le français via OpenAI avec cache"""

        # Vérification du cache
        cache_key = f"{source_lang}:{hash(query)}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]

        # Traduction via OpenAI si client disponible
        if self.openai_client:
            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": f"Translate the following poultry/agriculture query from {source_lang} to French. "
                            "Keep technical terms like 'Cobb 500', 'Ross 308', 'FCR' unchanged. "
                            "Return only the French translation, no explanations.",
                        },
                        {"role": "user", "content": query},
                    ],
                    max_tokens=150,
                    temperature=0,
                )

                translated = response.choices[0].message.content.strip()

                # Validation basique de la traduction
                if len(translated) > 0 and len(translated) < len(query) * 3:
                    self.translation_cache[cache_key] = translated
                    logger.debug(
                        f"Traduction OpenAI [{source_lang}->fr]: '{query}' -> '{translated}'"
                    )
                    return translated
                else:
                    logger.warning(f"Traduction OpenAI suspecte pour: {query}")

            except Exception as e:
                logger.error(f"Erreur traduction OpenAI: {e}")

        # Fallback avec traduction basique par patterns
        return self._simple_translation_fallback(query, source_lang)

    def _simple_translation_fallback(self, query: str, source_lang: str) -> str:
        """Traduction basique par patterns pour les cas d'urgence"""

        # Dictionnaires de base pour termes courants aviculture
        basic_translations = {
            "en": {
                "chicken": "poulet",
                "poultry": "volaille",
                "weight": "poids",
                "days": "jours",
                "day": "jour",
                "male": "mâle",
                "female": "femelle",
                "feed": "aliment",
                "growth": "croissance",
                "mortality": "mortalité",
            },
            "es": {
                "pollo": "poulet",
                "peso": "poids",
                "días": "jours",
                "día": "jour",
                "macho": "mâle",
                "hembra": "femelle",
                "gallina": "poule",
                "alimentación": "alimentation",
                "crecimiento": "croissance",
            },
            "de": {
                "huhn": "poulet",
                "hähnchen": "poulet",
                "gewicht": "poids",
                "tage": "jours",
                "tag": "jour",
                "männlich": "mâle",
                "weiblich": "femelle",
                "futter": "aliment",
                "wachstum": "croissance",
            },
            "it": {
                "pollo": "poulet",
                "peso": "poids",
                "giorni": "jours",
                "giorno": "jour",
                "maschio": "mâle",
                "femmina": "femelle",
                "alimentazione": "alimentation",
            },
            "pt": {
                "frango": "poulet",
                "peso": "poids",
                "dias": "jours",
                "dia": "jour",
                "macho": "mâle",
                "fêmea": "femelle",
                "alimentação": "alimentation",
            },
            "hi": {
                "मुर्गी": "poulet",
                "चिकन": "poulet",
                "वजन": "poids",
                "दिन": "jour",
                "नर": "mâle",
                "मादा": "femelle",
                "भोजन": "aliment",
            },
            "zh": {
                "鸡": "poulet",
                "体重": "poids",
                "重量": "poids",
                "天": "jour",
                "公": "mâle",
                "母": "femelle",
                "饲料": "aliment",
            },
            "th": {
                "ไก่": "poulet",
                "น้ำหนัก": "poids",
                "วัน": "jour",
                "ตัวผู้": "mâle",
                "ตัวเมีย": "femelle",
                "อาหาร": "aliment",
            },
        }

        translated = query.lower()
        if source_lang in basic_translations:
            for foreign_term, french_term in basic_translations[source_lang].items():
                translated = re.sub(
                    rf"\b{re.escape(foreign_term)}\b",
                    french_term,
                    translated,
                    flags=re.IGNORECASE,
                )

        # Conserver les termes techniques universels
        technical_terms = ["cobb", "ross", "hubbard", "isa", "fcr"]
        for term in technical_terms:
            if term in query.lower():
                translated = translated.replace(term, term)

        logger.debug(
            f"Traduction fallback [{source_lang}->fr]: '{query}' -> '{translated}'"
        )
        return translated

    async def _fallback_analysis(
        self, query: str, language: str
    ) -> Tuple[bool, float, Dict]:
        """Analyse de secours sans traduction pour cas d'urgence"""

        # Recherche de termes techniques universels
        universal_terms = ["cobb", "ross", "hubbard", "isa", "fcr", "308", "500"]
        found_universal = sum(
            1 for term in universal_terms if term.lower() in query.lower()
        )

        # Recherche de nombres (indicateurs de spécificité technique)
        numbers = re.findall(r"\d+", query)

        # Recherche de patterns aviculture (unités, âges)
        poultry_patterns = [
            r"\d+\s*(?:g|kg|gram|kilogram)",  # Poids
            r"\d+\s*(?:day|jour|dia|tag|giorno|วัน|天|दिन)",  # Âge
            r"\d+\s*%",  # Pourcentages
        ]
        pattern_matches = sum(
            1
            for pattern in poultry_patterns
            if re.search(pattern, query, re.IGNORECASE)
        )

        # Score basique avec bonus pour termes techniques
        base_score = (
            (found_universal * 0.4) + (len(numbers) * 0.1) + (pattern_matches * 0.2)
        )

        # Seuil très permissif pour éviter de bloquer des questions légitimes
        fallback_threshold = 0.08
        is_in_domain = base_score > fallback_threshold or found_universal > 0

        logger.info(
            f"OOD Fallback [{language}]: '{query[:40]}...' | "
            f"Score: {base_score:.3f} | Termes techniques: {found_universal} | "
            f"Patterns: {pattern_matches} | Décision: {'ACCEPTÉ' if is_in_domain else 'REJETÉ'}"
        )

        return (
            is_in_domain,
            base_score,
            {
                "fallback_used": True,
                "language": language,
                "universal_terms_found": found_universal,
                "numbers_found": len(numbers),
                "poultry_patterns": pattern_matches,
                "threshold": fallback_threshold,
                "reasoning": f"Fallback analysis - {found_universal} universal terms, {pattern_matches} patterns",
                "translation_failed": True,
            },
        )

    def _normalize_query_preserve_script(self, query: str, language: str) -> str:
        """Normalisation qui préserve les scripts non-latins"""
        if not query:
            return ""

        # Pour les scripts non-latins, ne PAS utiliser unidecode
        if language in ["hi", "th", "zh"]:
            # Normalisation légère sans destruction du script
            normalized = query.lower()
            # Supprimer seulement la ponctuation excessive
            normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)
            normalized = re.sub(r"\s+", " ", normalized).strip()
            return normalized

        # Pour les scripts latins, normalisation standard
        normalized = unidecode(query).lower() if UNIDECODE_AVAILABLE else query.lower()
        normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Expansion des acronymes courants
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
        """Analyse contextuelle de la requête"""
        context = {
            "type": "standard_query",
            "technical_indicators": [],
            "numeric_indicators": [],
            "question_type": None,
            "specificity_level": "medium",
            "intent_confidence": 0.0,
        }

        # Détection d'indicateurs techniques
        technical_patterns = [
            (r"\b(?:fcr|ic|indice)\b", "conversion_metric"),
            (r"\b(?:ross|cobb|hubbard|isa)\s*\d*\b", "genetic_line"),
            (
                r"\b\d+\s*(?:jour|day|semaine|week|dia|tag|giorno|วัน|天|दिन)s?\b",
                "age_specification",
            ),
            (r"\b\d+[.,]?\d*\s*(?:g|kg|gramme|gram|kilogram)\b", "weight_measure"),
            (r"\b\d+[.,]?\d*\s*%\b", "percentage_value"),
        ]

        for pattern, indicator_type in technical_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                context["technical_indicators"].append(
                    {"type": indicator_type, "matches": matches, "count": len(matches)}
                )

        # Détection d'indicateurs numériques
        numeric_patterns = [
            r"\b\d+[.,]?\d*\s*(?:g|kg|gramme|gram|kilogram)s?\b",
            r"\b\d+[.,]?\d*\s*%\b",
            r"\b\d+\s*(?:jour|day|semaine|week|dia|tag|giorno|วัน|天|दिन)s?\b",
        ]

        for pattern in numeric_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            context["numeric_indicators"].extend(matches)

        # Classification du type de requête
        if len(context["technical_indicators"]) >= 2:
            context["type"] = "technical_query"
            context["specificity_level"] = "high"
        elif len(context["numeric_indicators"]) >= 1:
            context["type"] = "numeric_query"
            context["specificity_level"] = "high"

        # Intégration des informations d'intention
        if intent_result:
            try:
                if hasattr(intent_result, "confidence"):
                    context["intent_confidence"] = float(intent_result.confidence)
                if hasattr(intent_result, "detected_entities"):
                    entities = intent_result.detected_entities
                    if len(entities) >= 2:
                        context["type"] = "technical_query"
                        context["specificity_level"] = "very_high"
            except Exception as e:
                logger.warning(f"Erreur analyse intention: {e}")

        return context

    def _calculate_domain_relevance(
        self, words: List[str], context_analysis: Dict
    ) -> DomainScore:
        """Calcul de la pertinence domaine"""
        domain_words = []
        relevance_scores = {level: 0 for level in DomainRelevance}

        # Analyse mot par mot
        for word in words:
            word_clean = word.strip().lower()
            if len(word_clean) < 2:
                continue

            for level, vocabulary in self.domain_vocabulary.items():
                if word_clean in vocabulary:
                    domain_words.append(word_clean)
                    relevance_scores[level] += 1
                    break

        # Calcul du score avec pondération
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

        # Détermination du niveau de pertinence
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
        if len(context_analysis["numeric_indicators"]) >= 1:
            context_bonus += 0.05

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
        )

    def _detect_blocked_terms(self, query: str, words: List[str]) -> Dict:
        """Détection des termes bloqués"""
        blocked_found = []
        is_blocked = False

        for category, terms in self.blocked_terms.items():
            for term in terms:
                if term.lower() in query:
                    blocked_found.append(term)

        # Décision de blocage
        if len(blocked_found) >= 2:
            is_blocked = True

        return {
            "is_blocked": is_blocked,
            "blocked_terms": blocked_found,
            "block_score": len(blocked_found) / max(len(words), 1),
        }

    def _apply_context_boosters(
        self, base_score: float, context_analysis: Dict, intent_result=None
    ) -> float:
        """Application de boosters contextuels"""
        boosted_score = base_score

        if context_analysis["type"] == "technical_query":
            boosted_score += 0.15

        numeric_count = len(context_analysis["numeric_indicators"])
        if numeric_count >= 2:
            boosted_score += 0.1
        elif numeric_count == 1:
            boosted_score += 0.05

        if context_analysis["intent_confidence"] > 0.8:
            boosted_score += 0.1

        return min(0.98, boosted_score)

    def _select_adaptive_threshold(
        self, context_analysis: Dict, domain_analysis: DomainScore
    ) -> float:
        """Sélection du seuil adaptatif"""
        base_threshold = self.adaptive_thresholds.get(
            context_analysis["type"], self.adaptive_thresholds["standard_query"]
        )

        # Ajustements
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
        words: List[str],
        domain_analysis: DomainScore,
        final_score: float,
        threshold: float,
        is_in_domain: bool,
    ) -> None:
        """Logging des décisions OOD"""
        decision = "ACCEPTÉ" if is_in_domain else "REJETÉ"
        logger.debug(
            f"OOD {decision}: '{query[:50]}...' | "
            f"Score: {final_score:.3f} vs Seuil: {threshold:.3f} | "
            f"Mots domaine: {len(domain_analysis.domain_words)}/{len(words)}"
        )

    def _update_ood_metrics(
        self, domain_analysis: DomainScore, threshold: float, is_in_domain: bool
    ) -> None:
        """Mise à jour des métriques"""
        try:
            if is_in_domain:
                METRICS.ood_accepted(
                    domain_analysis.final_score, domain_analysis.relevance_level.value
                )
            else:
                METRICS.ood_filtered(domain_analysis.final_score, "threshold_not_met")
        except Exception as e:
            logger.warning(f"Erreur mise à jour métriques OOD: {e}")

    def get_detector_stats(self) -> Dict:
        """Statistiques du détecteur"""
        vocab_stats = {
            level.value: len(terms) for level, terms in self.domain_vocabulary.items()
        }
        blocked_stats = {
            category: len(terms) for category, terms in self.blocked_terms.items()
        }

        return {
            "version": "multilingual_v1.0",
            "vocabulary_stats": vocab_stats,
            "blocked_terms_stats": blocked_stats,
            "adaptive_thresholds": self.adaptive_thresholds.copy(),
            "language_adjustments": self.language_adjustments.copy(),
            "supported_languages": self.supported_languages.copy(),
            "translation_cache_size": len(self.translation_cache),
            "total_domain_terms": sum(
                len(terms) for terms in self.domain_vocabulary.values()
            ),
        }

    async def test_query_analysis(self, query: str, language: str = "fr") -> Dict:
        """Méthode de test pour analyser une requête en détail"""
        is_in_domain, score, details = await self.calculate_ood_score(
            query, None, language
        )

        return {
            "original_query": query,
            "language": language,
            "final_score": score,
            "is_in_domain": is_in_domain,
            "decision": "ACCEPTED" if is_in_domain else "REJECTED",
            "details": details,
        }


# Classe pour compatibilité descendante - CORRECTION PRINCIPALE
class EnhancedOODDetector(MultilingualOODDetector):
    """Alias pour compatibilité avec le code existant"""

    def __init__(self, blocked_terms_path: str = None, openai_client=None):
        # CORRECTION: Passer le client OpenAI à la classe parent
        super().__init__(blocked_terms_path, openai_client)

    def calculate_ood_score(
        self, query: str, intent_result=None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Méthode synchrone pour compatibilité - utilise le français par défaut"""
        # Conversion en appel asynchrone avec langue française par défaut
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            super().calculate_ood_score(query, intent_result, "fr")
        )

    # AJOUT DE LA MÉTHODE PUBLIQUE MANQUANTE - CORRECTION CRITIQUE
    def calculate_ood_score_multilingual(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Méthode publique pour calcul OOD multilingue
        CORRECTION: Cette méthode était manquante et causait l'erreur dans les logs
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Appel de la méthode privée _calculate_ood_score_multilingual
        return loop.run_until_complete(
            self._calculate_ood_score_multilingual(query, intent_result, language)
        )

    # AJOUT MÉTHODE ASYNC PUBLIQUE POUR API MODERNE
    async def async_calculate_ood_score_multilingual(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Version asynchrone publique pour la méthode multilingue"""
        return await self._calculate_ood_score_multilingual(
            query, intent_result, language
        )


# Factory functions - CORRECTION DES PARAMÈTRES
def create_ood_detector(
    blocked_terms_path: str = None, openai_client=None
) -> EnhancedOODDetector:
    """Crée une instance du détecteur OOD avec compatibilité - PARAMÈTRES CORRIGÉS"""
    return EnhancedOODDetector(blocked_terms_path, openai_client)


def create_multilingual_ood_detector(
    blocked_terms_path: str = None, openai_client=None
) -> MultilingualOODDetector:
    """Crée une instance du détecteur OOD multilingue complet"""
    return MultilingualOODDetector(blocked_terms_path, openai_client)
