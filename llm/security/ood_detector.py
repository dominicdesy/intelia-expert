# -*- coding: utf-8 -*-
"""
ood_detector.py - Détecteur hors-domaine intelligent et adaptatif
Version perfectionnée avec scoring précis et seuils dynamiques
"""

import logging
import json
import os
import re
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from config.config import OOD_MIN_SCORE, OOD_STRICT_SCORE
from utils.utilities import METRICS
from utils.imports_and_dependencies import UNIDECODE_AVAILABLE

if UNIDECODE_AVAILABLE:
    from unidecode import unidecode

logger = logging.getLogger(__name__)


class DomainRelevance(Enum):
    """Niveaux de pertinence pour le domaine avicole"""

    HIGH = "high"  # Très pertinent (lignées, FCR, etc.)
    MEDIUM = "medium"  # Moyennement pertinent (animaux, élevage)
    LOW = "low"  # Faiblement pertinent (agriculture générale)
    GENERIC = "generic"  # Générique (comment, quoi, etc.)
    BLOCKED = "blocked"  # Explicitement bloqué


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


class EnhancedOODDetector:
    """Détecteur hors-domaine intelligent pour l'aviculture"""

    def __init__(self, blocked_terms_path: str = None):
        self.blocked_terms = self._load_blocked_terms(blocked_terms_path)
        self.domain_vocabulary = self._build_domain_vocabulary()

        # Seuils adaptatifs selon le contexte
        self.adaptive_thresholds = {
            "technical_query": 0.10,  # Requêtes avec termes techniques
            "numeric_query": 0.15,  # Requêtes avec chiffres/mesures
            "standard_query": 0.20,  # Requêtes standards
            "generic_query": 0.30,  # Requêtes génériques
            "suspicious_query": 0.50,  # Requêtes suspectes
        }

    def _load_blocked_terms(self, path: str = None) -> Dict[str, List[str]]:
        """Charge les termes explicitement bloqués"""
        if path is None:
            # Recherche multi-emplacements pour blocked_terms.json
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
        """Construit un vocabulaire hiérarchisé du domaine avicole"""
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

    def calculate_ood_score(
        self, query: str, intent_result=None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul intelligent du score OOD avec analyse contextuelle"""

        # Normalisation et préparation
        normalized_query = self._normalize_query(query)
        words = normalized_query.split()

        if not words:
            return False, 0.0, {"error": "empty_query"}

        # Analyse contextuelle de la requête
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

        # Sélection du seuil adaptatif
        threshold = self._select_adaptive_threshold(context_analysis, domain_analysis)

        # Décision finale
        is_in_domain = boosted_score > threshold and not blocked_analysis["is_blocked"]

        # Logging détaillé pour debugging
        self._log_ood_decision(
            query, words, domain_analysis, boosted_score, threshold, is_in_domain
        )

        # Métriques et statistiques
        self._update_ood_metrics(domain_analysis, threshold, is_in_domain)

        # Construction de la réponse détaillée
        score_details = {
            "vocab_score": domain_analysis.final_score,
            "boosted_score": boosted_score,
            "threshold_used": threshold,
            "domain_words_found": len(domain_analysis.domain_words),
            "blocked_terms_found": len(domain_analysis.blocked_terms),
            "context_type": context_analysis["type"],
            "relevance_level": domain_analysis.relevance_level.value,
            "confidence_boosters": domain_analysis.confidence_boosters,
            "reasoning": domain_analysis.reasoning,
            "technical_indicators": context_analysis.get("technical_indicators", []),
            "numeric_indicators": context_analysis.get("numeric_indicators", []),
        }

        return is_in_domain, boosted_score, score_details

    def _normalize_query(self, query: str) -> str:
        """Normalisation avancée de la requête"""
        if not query:
            return ""

        # Conversion unicode si disponible
        normalized = unidecode(query).lower() if UNIDECODE_AVAILABLE else query.lower()

        # Nettoyage des caractères spéciaux mais préservation des chiffres
        normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)

        # Normalisation des espaces
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Expansion des acronymes courants en aviculture
        acronym_expansions = {
            "ic": "indice conversion",
            "fcr": "feed conversion ratio",
            "adr": "alimentation distribution",
            "pv": "poids vif",
            "gmq": "gain moyen quotidien",
        }

        for acronym, expansion in acronym_expansions.items():
            normalized = re.sub(rf"\b{acronym}\b", expansion, normalized)

        return normalized

    def _analyze_query_context(
        self, query: str, words: List[str], intent_result=None
    ) -> Dict:
        """Analyse contextuelle approfondie de la requête"""

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
            (r"\b\d+\s*(?:jour|day|semaine|week)s?\b", "age_specification"),
            (r"\b\d+[.,]?\d*\s*(?:g|kg|gramme|kilo)\b", "weight_measure"),
            (r"\b\d+[.,]?\d*\s*%\b", "percentage_value"),
            (r"\b(?:température|temp|°c|celsius)\b", "environmental_param"),
            (r"\b(?:vaccination|vaccin|prophylaxie)\b", "health_protocol"),
        ]

        for pattern, indicator_type in technical_patterns:
            matches = re.findall(pattern, query)
            if matches:
                context["technical_indicators"].append(
                    {"type": indicator_type, "matches": matches, "count": len(matches)}
                )

        # Détection d'indicateurs numériques
        numeric_patterns = [
            r"\b\d+[.,]?\d*\s*(?:g|kg|gramme|kilogramme)s?\b",
            r"\b\d+[.,]?\d*\s*%\b",
            r"\b\d+[.,]?\d*\s*(?:°c|degré|celsius)\b",
            r"\b\d+\s*(?:jour|day|semaine|week|mois|month)s?\b",
            r"\b\d+[.,]?\d*\s*(?:l|litre|ml|millilitre)s?\b",
        ]

        for pattern in numeric_patterns:
            matches = re.findall(pattern, query)
            context["numeric_indicators"].extend(matches)

        # Classification du type de requête
        if len(context["technical_indicators"]) >= 2:
            context["type"] = "technical_query"
            context["specificity_level"] = "high"
        elif len(context["numeric_indicators"]) >= 1:
            context["type"] = "numeric_query"
            context["specificity_level"] = "high"
        elif any(word in query for word in ["comment", "how", "pourquoi", "why"]):
            context["question_type"] = "how_to"
            context["specificity_level"] = "medium"
        elif any(word in query for word in ["quel", "quelle", "what", "which"]):
            context["question_type"] = "information_seeking"
            context["specificity_level"] = "medium"

        # Intégration des informations d'intention si disponibles
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
        """Calcul précis de la pertinence domaine avec scoring hiérarchique"""

        domain_words = []
        relevance_scores = {level: 0 for level in DomainRelevance}
        word_contributions = {}

        # Analyse mot par mot avec pondération
        for word in words:
            word_clean = word.strip().lower()
            if len(word_clean) < 2:  # Ignorer mots trop courts
                continue

            # Recherche dans chaque niveau de pertinence
            for level, vocabulary in self.domain_vocabulary.items():
                if word_clean in vocabulary:
                    domain_words.append(word_clean)
                    relevance_scores[level] += 1
                    word_contributions[word_clean] = level
                    break  # Un mot ne peut appartenir qu'à un niveau

                # Recherche de correspondances partielles pour les termes composés
                for vocab_term in vocabulary:
                    if len(vocab_term) > 4 and (
                        word_clean in vocab_term or vocab_term in word_clean
                    ):
                        domain_words.append(f"{word_clean}~{vocab_term}")
                        relevance_scores[
                            level
                        ] += 0.7  # Score réduit pour match partiel
                        word_contributions[word_clean] = level
                        break

        # Calcul du score final avec pondération hiérarchique
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

        # Normalisation par rapport au nombre total de mots significatifs
        significant_words = [w for w in words if len(w.strip()) >= 2]
        base_score = weighted_score / len(significant_words) if significant_words else 0

        # Détermination du niveau de pertinence global
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

        # Bonus pour cohérence contextuelle
        context_bonus = 0.0
        if context_analysis["type"] == "technical_query" and overall_relevance in [
            DomainRelevance.HIGH,
            DomainRelevance.MEDIUM,
        ]:
            context_bonus += 0.15
        if len(context_analysis["technical_indicators"]) >= 1:
            context_bonus += 0.1
        if len(context_analysis["numeric_indicators"]) >= 1:
            context_bonus += 0.05

        final_score = min(1.0, base_score + context_bonus)

        # Construction du raisonnement
        reasoning_parts = [
            f"Mots domaine: {len(domain_words)}/{len(significant_words)}",
            f"Niveau: {overall_relevance.value}",
            f"Score base: {base_score:.3f}",
        ]
        if context_bonus > 0:
            reasoning_parts.append(f"Bonus contexte: +{context_bonus:.3f}")

        confidence_boosters = {
            "context_bonus": context_bonus,
            "high_relevance_words": relevance_scores[DomainRelevance.HIGH],
            "medium_relevance_words": relevance_scores[DomainRelevance.MEDIUM],
            "technical_indicators": len(context_analysis["technical_indicators"]),
        }

        return DomainScore(
            final_score=final_score,
            relevance_level=overall_relevance,
            domain_words=domain_words,
            blocked_terms=[],  # Sera rempli par _detect_blocked_terms
            confidence_boosters=confidence_boosters,
            threshold_applied=0.0,  # Sera défini plus tard
            reasoning=" | ".join(reasoning_parts),
        )

    def _detect_blocked_terms(self, query: str, words: List[str]) -> Dict:
        """Détection intelligente des termes explicitement bloqués"""

        blocked_found = []
        blocking_categories = []
        is_blocked = False

        for category, terms in self.blocked_terms.items():
            category_matches = []

            for term in terms:
                # Recherche exacte et partielle
                if term.lower() in query:
                    category_matches.append(term)
                    blocked_found.append(term)

            if category_matches:
                blocking_categories.append(
                    {
                        "category": category,
                        "matches": category_matches,
                        "severity": self._get_blocking_severity(category),
                    }
                )

        # Décision de blocage basée sur la sévérité
        high_severity_blocks = [
            cat
            for cat in blocking_categories
            if cat["severity"] in ["critical", "high"]
        ]

        if high_severity_blocks:
            is_blocked = True
        elif len(blocking_categories) >= 2:  # Multiple catégories = suspect
            is_blocked = True
        elif len(blocked_found) >= 3:  # Beaucoup de termes bloqués = suspect
            is_blocked = True

        return {
            "is_blocked": is_blocked,
            "blocked_terms": blocked_found,
            "blocking_categories": blocking_categories,
            "block_score": len(blocked_found) / max(len(words), 1),
        }

    def _get_blocking_severity(self, category: str) -> str:
        """Détermine la sévérité d'une catégorie de blocage"""
        severity_mapping = {
            "adult_content": "critical",
            "illegal": "critical",
            "hate_speech": "critical",
            "violence": "critical",
            "crypto_finance": "high",
            "politics": "high",
            "medical_advice": "high",
            "entertainment": "medium",
            "sports": "medium",
            "technology": "low",
            "general": "low",
        }
        return severity_mapping.get(category, "medium")

    def _apply_context_boosters(
        self, base_score: float, context_analysis: Dict, intent_result=None
    ) -> float:
        """Application de boosters contextuels intelligents"""

        boosted_score = base_score

        # Booster pour requêtes techniques
        if context_analysis["type"] == "technical_query":
            boosted_score += 0.15

        # Booster pour indicateurs numériques spécifiques
        numeric_count = len(context_analysis["numeric_indicators"])
        if numeric_count >= 2:
            boosted_score += 0.1
        elif numeric_count == 1:
            boosted_score += 0.05

        # Booster pour confiance d'intention élevée
        if context_analysis["intent_confidence"] > 0.8:
            boosted_score += 0.1
        elif context_analysis["intent_confidence"] > 0.6:
            boosted_score += 0.05

        # Booster pour spécificité élevée
        if context_analysis["specificity_level"] == "very_high":
            boosted_score += 0.12
        elif context_analysis["specificity_level"] == "high":
            boosted_score += 0.08

        # Booster pour entités métier détectées
        if intent_result and hasattr(intent_result, "detected_entities"):
            entities = intent_result.detected_entities
            business_entities = [
                "line",
                "species",
                "age_days",
                "weight",
                "fcr",
                "phase",
            ]
            detected_business = [e for e in business_entities if e in entities]

            if len(detected_business) >= 3:
                boosted_score += 0.2
            elif len(detected_business) >= 2:
                boosted_score += 0.15
            elif len(detected_business) >= 1:
                boosted_score += 0.1

        # Limitation du score final
        return min(0.98, boosted_score)

    def _select_adaptive_threshold(
        self, context_analysis: Dict, domain_analysis: DomainScore
    ) -> float:
        """Sélection intelligente du seuil adaptatif"""

        # Seuil de base selon le type de requête
        base_threshold = self.adaptive_thresholds.get(
            context_analysis["type"], self.adaptive_thresholds["standard_query"]
        )

        # Ajustements contextuels
        adjustments = []

        # Plus strict pour requêtes très génériques
        if (
            context_analysis["specificity_level"] == "low"
            and domain_analysis.relevance_level == DomainRelevance.GENERIC
        ):
            adjustments.append(("generic_penalty", +0.1))

        # Plus permissif pour requêtes avec indicateurs techniques
        if len(context_analysis["technical_indicators"]) >= 2:
            adjustments.append(("technical_bonus", -0.05))

        # Plus permissif pour requêtes avec entités métier
        if domain_analysis.confidence_boosters.get("high_relevance_words", 0) >= 2:
            adjustments.append(("domain_expert", -0.05))

        # Application des ajustements
        final_threshold = base_threshold
        for reason, adjustment in adjustments:
            final_threshold += adjustment
            logger.debug(f"Ajustement seuil {reason}: {adjustment:+.3f}")

        # Limites de sécurité
        final_threshold = max(0.05, min(0.6, final_threshold))

        return final_threshold

    def _log_ood_decision(
        self,
        query: str,
        words: List[str],
        domain_analysis: DomainScore,
        final_score: float,
        threshold: float,
        is_in_domain: bool,
    ) -> None:
        """Logging détaillé des décisions OOD pour debugging"""

        decision = "ACCEPTÉ" if is_in_domain else "REJETÉ"

        logger.debug(
            f"OOD {decision}: '{query[:50]}...' | "
            f"Score: {final_score:.3f} vs Seuil: {threshold:.3f} | "
            f"Mots domaine: {len(domain_analysis.domain_words)}/{len(words)} | "
            f"Niveau: {domain_analysis.relevance_level.value} | "
            f"Raisonnement: {domain_analysis.reasoning}"
        )

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"  Mots trouvés: {domain_analysis.domain_words}")
            logger.debug(f"  Boosters: {domain_analysis.confidence_boosters}")

    def _update_ood_metrics(
        self, domain_analysis: DomainScore, threshold: float, is_in_domain: bool
    ) -> None:
        """Mise à jour des métriques et statistiques OOD"""

        try:
            # Métriques de base
            if is_in_domain:
                METRICS.ood_accepted(
                    domain_analysis.final_score, domain_analysis.relevance_level.value
                )
            else:
                METRICS.ood_filtered(domain_analysis.final_score, "threshold_not_met")

            # Statistiques détaillées
            METRICS.ood_stats["total_queries"] += 1
            METRICS.ood_stats[f"level_{domain_analysis.relevance_level.value}"] += 1
            METRICS.ood_stats["threshold_applications"][threshold] = (
                METRICS.ood_stats["threshold_applications"].get(threshold, 0) + 1
            )

            # Métriques de performance du système
            if len(domain_analysis.domain_words) >= 2:
                METRICS.ood_stats["high_domain_content"] += 1

            if domain_analysis.confidence_boosters.get("technical_indicators", 0) >= 1:
                METRICS.ood_stats["technical_queries"] += 1

        except Exception as e:
            logger.warning(f"Erreur mise à jour métriques OOD: {e}")

    def get_detector_stats(self) -> Dict:
        """Statistiques détaillées du détecteur"""

        vocab_stats = {
            level.value: len(terms) for level, terms in self.domain_vocabulary.items()
        }

        blocked_stats = {
            category: len(terms) for category, terms in self.blocked_terms.items()
        }

        return {
            "version": "enhanced_adaptive_v2.0",
            "vocabulary_stats": vocab_stats,
            "blocked_terms_stats": blocked_stats,
            "adaptive_thresholds": self.adaptive_thresholds.copy(),
            "total_domain_terms": sum(
                len(terms) for terms in self.domain_vocabulary.values()
            ),
            "total_blocked_terms": sum(
                len(terms) for terms in self.blocked_terms.values()
            ),
            "current_config": {
                "base_min_score": OOD_MIN_SCORE,
                "base_strict_score": OOD_STRICT_SCORE,
                "unidecode_available": UNIDECODE_AVAILABLE,
            },
        }

    def test_query_analysis(self, query: str) -> Dict:
        """Méthode de test pour analyser une requête en détail"""

        normalized = self._normalize_query(query)
        words = normalized.split()
        context = self._analyze_query_context(normalized, words, None)
        domain_analysis = self._calculate_domain_relevance(words, context)
        blocked_analysis = self._detect_blocked_terms(normalized, words)

        boosted_score = self._apply_context_boosters(
            domain_analysis.final_score, context, None
        )
        threshold = self._select_adaptive_threshold(context, domain_analysis)
        is_in_domain = boosted_score > threshold and not blocked_analysis["is_blocked"]

        return {
            "original_query": query,
            "normalized_query": normalized,
            "words": words,
            "context_analysis": context,
            "domain_analysis": {
                "score": domain_analysis.final_score,
                "relevance_level": domain_analysis.relevance_level.value,
                "domain_words": domain_analysis.domain_words,
                "reasoning": domain_analysis.reasoning,
                "boosters": domain_analysis.confidence_boosters,
            },
            "blocked_analysis": blocked_analysis,
            "final_results": {
                "boosted_score": boosted_score,
                "threshold": threshold,
                "is_in_domain": is_in_domain,
                "decision": "ACCEPTED" if is_in_domain else "REJECTED",
            },
        }


# Factory pour compatibilité
def create_ood_detector(blocked_terms_path: str = None) -> EnhancedOODDetector:
    """Crée une instance du détecteur OOD optimisé"""
    return EnhancedOODDetector(blocked_terms_path)
