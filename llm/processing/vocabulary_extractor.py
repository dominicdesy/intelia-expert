# -*- coding: utf-8 -*-
"""
vocabulary_extractor.py - Extracteur de vocabulaire spécialisé pour l'aviculture
CORRIGÉ: Imports modulaires selon nouvelle architecture
"""

import re
import logging
from utils.types import Dict, List, Set, Tuple, Any
from functools import lru_cache

# Imports modulaires corrigés
# Note: validate_numeric_range et normalize_text vérifiées présentes dans utils/utilities.py
# from utils.utilities import validate_numeric_range, normalize_text

# Suppression temporaire des imports non utilisés pour éviter les erreurs
# Ces fonctions peuvent être ajoutées si nécessaires

logger = logging.getLogger(__name__)


def validate_alias_coverage(required_aliases: dict, vocab: dict) -> dict:
    """
    Retourne les alias manquants pour aider au debug (clé → [manquants]).
    """
    missing = {}
    for k, expected in required_aliases.items():
        have = set(map(str.lower, vocab.get(k, [])))
        miss = [e for e in expected if e.lower() not in have]
        if miss:
            missing[k] = miss
    return missing


class PoultryVocabularyExtractor:
    """Extracteur de vocabulaire spécialisé - Version avec seuils adaptatifs"""

    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        self.poultry_keywords = self._build_vocabulary()
        self.alias_mappings = self._build_alias_mappings()
        self.specialized_terms = self._build_specialized_terms()
        self.metrics_vocabulary = self._build_metrics_vocabulary()
        self.topic_defaults = self._load_topic_defaults()

        # Nouveaux: patterns de haute confiance pour seuils adaptatifs
        self.high_confidence_patterns = self._build_high_confidence_patterns()
        self.genetic_terms = self._extract_genetic_vocabulary()

        # Statistiques de couverture
        self.coverage_stats = {
            "total_keywords": len(self.poultry_keywords),
            "alias_mappings": len(self.alias_mappings),
            "specialized_terms": len(self.specialized_terms),
            "metrics_covered": len(self.metrics_vocabulary),
            "topic_defaults": len(self.topic_defaults),
            "high_confidence_patterns": len(self.high_confidence_patterns),
            "genetic_terms": len(self.genetic_terms),
        }

        logger.info(f"Vocabulaire avicole étendu: {self.coverage_stats}")

    def _build_high_confidence_patterns(self) -> Dict[str, float]:
        """Patterns de haute confiance pour seuils adaptatifs OOD"""
        return {
            # Combinaisons genetics + metrics = très haute confiance
            "genetics_metrics": 0.95,
            "specific_line_age": 0.90,
            "technical_metrics": 0.85,
            "environment_technical": 0.80,
            "protocol_specific": 0.85,
        }

    def _extract_genetic_vocabulary(self) -> Set[str]:
        """Extrait le vocabulaire génétique pour détection haute confiance"""
        genetic_terms = set()

        # Lignées depuis aliases
        for line_type, line_aliases in (
            self.intents_config.get("aliases", {}).get("line", {}).items()
        ):
            genetic_terms.add(line_type.lower())
            genetic_terms.update([alias.lower() for alias in line_aliases])

        # Termes génétiques étendus
        genetic_terms.update(
            [
                "ross",
                "cobb",
                "hubbard",
                "isa",
                "lohmann",
                "hyline",
                "dekalb",
                "bovans",
                "shaver",
                "novogen",
                "hisex",
                "nick",
                "ranger",
                "sasso",
                "parent",
                "stock",
                "breeding",
                "strain",
                "line",
                "genetic",
            ]
        )

        return genetic_terms

    def _build_vocabulary(self) -> Set[str]:
        """Construit le vocabulaire complet - Version avec normalisation clés"""
        keywords = set()

        aliases = self.intents_config.get("aliases", {})

        # Lignées de volailles (coverage complète du fichier intents.json)
        for line_type, line_aliases in aliases.get("line", {}).items():
            keywords.add(line_type.lower())
            keywords.update([alias.lower() for alias in line_aliases])
            # Ajout: variantes normalisées pour clés cache
            keywords.add(self._normalize_for_cache_key(line_type))
            for alias in line_aliases:
                keywords.add(self._normalize_for_cache_key(alias))

        # Types d'élevage et sites
        for site_type, site_aliases in aliases.get("site_type", {}).items():
            keywords.add(site_type.lower())
            keywords.update([alias.lower() for alias in site_aliases])

        # Types d'oiseaux
        for bird_type, bird_aliases in aliases.get("bird_type", {}).items():
            keywords.add(bird_type.lower())
            keywords.update([alias.lower() for alias in bird_aliases])

        # Phases d'élevage
        for phase, phase_aliases in aliases.get("phase", {}).items():
            keywords.add(phase.lower())
            keywords.update([alias.lower() for alias in phase_aliases])

        # Sexes
        for sex, sex_aliases in aliases.get("sex", {}).items():
            keywords.add(sex.lower())
            keywords.update([alias.lower() for alias in sex_aliases])

        # Métriques techniques depuis tous les intents
        for intent_name, intent_config in self.intents_config.get(
            "intents", {}
        ).items():
            metrics = intent_config.get("metrics", {})
            keywords.update(
                [metric.lower().replace("_", " ") for metric in metrics.keys()]
            )
            keywords.update(
                [metric.lower().replace("_", "") for metric in metrics.keys()]
            )

        # Vocabulaire spécialisé étendu pour améliorer la couverture
        extended_poultry_terms = {
            # Termes de base
            "poulet",
            "poule",
            "aviculture",
            "élevage",
            "volaille",
            "poids",
            "fcr",
            "aliment",
            "vaccination",
            "maladie",
            "production",
            "croissance",
            "chicken",
            "poultry",
            "broiler",
            "layer",
            "feed",
            "weight",
            "growth",
            # Environnement et équipement
            "température",
            "ventilation",
            "eau",
            "water",
            "temperature",
            "incubation",
            "couvoir",
            "hatchery",
            "biosécurité",
            "mortalité",
            "mortality",
            "performance",
            "tunnel",
            "natural",
            "mechanical",
            "pad",
            "cooling",
            "heating",
            "inlet",
            "static",
            "pressure",
            "lux",
            "lighting",
            "hours",
            "intensity",
            # Lignées et génétique (avec variantes normalisées)
            "ross",
            "cobb",
            "hubbard",
            "isa",
            "lohmann",
            "hyline",
            "dekalb",
            "bovans",
            "shaver",
            "novogen",
            "hisex",
            "nick",
            "ranger",
            "sasso",
            "freedom",
            "classic",
            "flex",
            "color",
            "brown",
            "white",
            "parent",
            "stock",
            # Variantes normalisées pour cache
            "ross308",
            "ross 308",
            "r308",
            "cobb500",
            "cobb 500",
            "c500",
            # Stades et âges
            "poussin",
            "chick",
            "œuf",
            "egg",
            "day-old",
            "starter",
            "grower",
            "finisher",
            "breeding",
            "reproduction",
            "ponte",
            "laying",
            "pullet",
            "rearing",
            # Nutrition et performance
            "feed conversion",
            "conversion",
            "welfare",
            "bien-être",
            "animal",
            "density",
            "densité",
            "housing",
            "logement",
            "epef",
            "uniformity",
            "daily",
            "gain",
            "intake",
            "cumulative",
            "stocking",
            "feeder",
            "nipple",
            # Composition nutritionnelle
            "protein",
            "energy",
            "lysine",
            "methionine",
            "calcium",
            "phosphorus",
            "sodium",
            "chloride",
            "potassium",
            "fiber",
            "starch",
            "fat",
            "oil",
            "metabolizable",
            "digestible",
            "crude",
            "available",
            "kcal",
            "meg",
            # Pathologie et santé
            "vaccine",
            "virus",
            "bacteria",
            "parasite",
            "antibiotic",
            "treatment",
            "diagnosis",
            "pathology",
            "immune",
            "immunity",
            "stress",
            "welfare",
            # Économie
            "cost",
            "price",
            "margin",
            "profit",
            "roi",
            "budget",
            "economics",
            "efficiency",
            "optimization",
            "investment",
            "return",
        }
        keywords.update(extended_poultry_terms)

        logger.info(f"Vocabulaire avicole construit: {len(keywords)} termes")
        return keywords

    def _normalize_for_cache_key(self, term: str) -> str:
        """Normalise un terme pour les clés de cache Redis"""
        # Enlever espaces, tirets, points
        normalized = re.sub(r"[\s\-\.]+", "", term.lower())

        # Variantes fréquentes
        normalized = normalized.replace("r-", "r").replace("c-", "c")

        # Garde-fou: minimum 3 caractères pour éviter collisions
        if len(normalized) < 3:
            return term.lower()

        return normalized

    def _build_metrics_vocabulary(self) -> Dict[str, Dict[str, Any]]:
        """Construit un index des métriques avec métadonnées"""
        metrics_vocab = {}

        for intent_name, intent_config in self.intents_config.get(
            "intents", {}
        ).items():
            metrics = intent_config.get("metrics", {})
            for metric_name, metric_config in metrics.items():

                # Variantes du nom de métrique
                variants = [
                    metric_name,
                    metric_name.replace("_", " "),
                    metric_name.replace("_", ""),
                    metric_name.lower(),
                    metric_name.lower().replace("_", " "),
                    metric_name.lower().replace("_", ""),
                ]

                metric_info = {
                    "canonical_name": metric_name,
                    "intent": intent_name,
                    "unit": metric_config.get("unit", ""),
                    "requires": metric_config.get("requires", []),
                    "requires_one_of": metric_config.get("requires_one_of", []),
                    "variants": variants,
                    "is_technical": metric_name
                    in ["fcr", "epef", "uniformity", "mortality"],  # Nouveau
                    "confidence_boost": (
                        1.5 if metric_name in ["fcr", "epef"] else 1.0
                    ),  # Nouveau
                }

                for variant in variants:
                    metrics_vocab[variant.lower()] = metric_info

        return metrics_vocab

    def _load_topic_defaults(self) -> Dict[str, str]:
        """Charge les defaults par topic pour améliorer la classification"""
        return self.intents_config.get("defaults_by_topic", {})

    def _build_alias_mappings(self) -> Dict[str, str]:
        """Construit les mappings alias -> terme canonique"""
        mappings = {}

        for category, items in self.intents_config.get("aliases", {}).items():
            for canonical, aliases in items.items():
                canonical_lower = canonical.lower()
                canonical_normalized = self._normalize_for_cache_key(canonical)

                mappings[canonical_lower] = canonical_lower
                mappings[canonical_normalized] = (
                    canonical_lower  # Nouveau: mapping normalisé
                )

                for alias in aliases:
                    alias_lower = alias.lower()
                    alias_normalized = self._normalize_for_cache_key(alias)

                    mappings[alias_lower] = canonical_lower
                    mappings[alias_normalized] = canonical_lower  # Nouveau

        return mappings

    def _build_specialized_terms(self) -> Dict[str, float]:
        """Construit un dictionnaire de termes spécialisés avec scores de spécificité améliorés"""
        specialized = {}

        # Termes très spécifiques (score élevé) - Étendu
        high_specificity = [
            "ross",
            "cobb",
            "hubbard",
            "fcr",
            "epef",
            "biosécurité",
            "couvoir",
            "isa",
            "lohmann",
            "hyline",
            "dekalb",
            "bovans",
            "shaver",
            "novogen",
            "tunnel",
            "pad",
            "cooling",
            "static pressure",
            "nipple",
            "uniformity",
            "ross308",
            "cobb500",
            "r308",
            "c500",  # Nouveaux: variantes normalisées
        ]
        for term in high_specificity:
            specialized[term] = 2.0

        # Termes modérément spécifiques - Étendu
        medium_specificity = [
            "poulet",
            "chicken",
            "aviculture",
            "poultry",
            "poussin",
            "chick",
            "broiler",
            "layer",
            "breeding",
            "vaccination",
            "mortality",
            "density",
            "starter",
            "grower",
            "finisher",
            "temperature",
            "ventilation",
            "lighting",
        ]
        for term in medium_specificity:
            specialized[term] = 1.5

        # Termes généraux mais dans le domaine - Étendu
        low_specificity = [
            "élevage",
            "production",
            "croissance",
            "growth",
            "farming",
            "feed",
            "water",
            "weight",
            "performance",
            "management",
            "health",
            "nutrition",
        ]
        for term in low_specificity:
            specialized[term] = 1.0

        return specialized

    @lru_cache(maxsize=2000)
    def is_poultry_related(self, text: str) -> Tuple[bool, float, Dict[str, Any]]:
        """Détermine si un texte est lié à l'aviculture - Version avec seuils adaptatifs"""
        text_lower = text.lower()
        words = re.findall(r"\b\w+\b", text_lower)

        if not words:
            return False, 0.0, {"reason": "no_words_found"}

        # Analyse de couverture vocabulaire
        vocab_matches = []
        vocab_score = 0.0

        for word in words:
            if word in self.poultry_keywords:
                specificity = self.specialized_terms.get(word, 1.0)
                vocab_score += specificity
                vocab_matches.append(
                    {
                        "word": word,
                        "specificity": specificity,
                        "canonical": self.alias_mappings.get(word, word),
                    }
                )

        # Détection de métriques spécialisées avec boost
        metrics_detected = []
        metrics_score = 0.0
        technical_metrics_found = False

        for phrase in [text_lower] + [
            " ".join(words[i : i + 3]) for i in range(len(words) - 2)
        ]:
            for metric_variant, metric_info in self.metrics_vocabulary.items():
                if metric_variant in phrase:
                    metrics_detected.append(metric_info["canonical_name"])
                    confidence_boost = metric_info.get("confidence_boost", 1.0)
                    metrics_score += 1.5 * confidence_boost
                    if metric_info.get("is_technical", False):
                        technical_metrics_found = True

        # Nouveau: Détection de patterns haute confiance
        high_confidence_detected = self._detect_high_confidence_patterns(
            text_lower, words
        )
        genetics_detected = any(term in text_lower for term in self.genetic_terms)

        # Score de couverture par domaine
        domain_coverage = self._analyze_domain_coverage(text_lower, words)

        # Normalisation et calcul final
        normalized_vocab_score = vocab_score / len(words) if words else 0.0
        normalized_metrics_score = min(1.0, metrics_score / 10.0)
        domain_bonus = sum(domain_coverage.values()) * 0.1

        # Nouveau: Bonus pour patterns haute confiance
        high_confidence_bonus = 0.0
        if high_confidence_detected:
            high_confidence_bonus = 0.3
        elif genetics_detected and technical_metrics_found:
            high_confidence_bonus = 0.25
        elif genetics_detected and len(metrics_detected) > 0:
            high_confidence_bonus = 0.2

        # Score final avec facteurs multiples
        final_score = min(
            1.0,
            normalized_vocab_score
            + normalized_metrics_score
            + domain_bonus
            + high_confidence_bonus,
        )

        # Nouveau: Seuils adaptatifs basés sur la confiance
        base_threshold = self._get_adaptive_threshold(
            high_confidence_detected,
            genetics_detected,
            technical_metrics_found,
            len(metrics_detected),
        )

        is_poultry = final_score >= base_threshold

        # Métriques détaillées pour debug et monitoring
        coverage_details = {
            "vocab_matches": vocab_matches,
            "metrics_detected": list(set(metrics_detected)),
            "domain_coverage": domain_coverage,
            "high_confidence_patterns": high_confidence_detected,
            "genetics_detected": genetics_detected,
            "technical_metrics": technical_metrics_found,
            "scores": {
                "vocab_score": normalized_vocab_score,
                "metrics_score": normalized_metrics_score,
                "domain_bonus": domain_bonus,
                "high_confidence_bonus": high_confidence_bonus,
                "final_score": final_score,
            },
            "threshold_used": base_threshold,
            "text_length": len(words),
            "coverage_ratio": len(vocab_matches) / len(words) if words else 0.0,
            "adaptive_factors": {
                "high_confidence": high_confidence_detected,
                "genetics_present": genetics_detected,
                "technical_metrics": technical_metrics_found,
                "metrics_count": len(metrics_detected),
            },
        }

        logger.debug(
            f"Classification vocabulaire: '{text[:50]}...' -> {is_poultry} "
            f"(score: {final_score:.3f}, seuil: {base_threshold:.3f})"
        )

        return is_poultry, final_score, coverage_details

    def _detect_high_confidence_patterns(
        self, text_lower: str, words: List[str]
    ) -> bool:
        """Détecte des patterns de très haute confiance pour seuils adaptatifs"""
        # Pattern genetics + metrics
        has_genetics = any(term in text_lower for term in self.genetic_terms)
        has_metrics = any(
            variant in text_lower for variant in self.metrics_vocabulary.keys()
        )

        if has_genetics and has_metrics:
            return True

        # Pattern lignée spécifique + âge
        line_patterns = ["ross 308", "cobb 500", "hubbard", "isa brown"]
        age_patterns = [r"\d+\s*(?:jour|day|semaine|week|j|d)"]

        has_specific_line = any(pattern in text_lower for pattern in line_patterns)
        has_age = any(re.search(pattern, text_lower) for pattern in age_patterns)

        if has_specific_line and has_age:
            return True

        # Pattern technique spécialisé
        technical_patterns = [
            "fcr",
            "epef",
            "biosécurité",
            "tunnel ventilation",
            "static pressure",
        ]
        if any(pattern in text_lower for pattern in technical_patterns):
            return True

        return False

    def _get_adaptive_threshold(
        self,
        high_confidence: bool,
        genetics: bool,
        technical_metrics: bool,
        metrics_count: int,
    ) -> float:
        """Calcule un seuil adaptatif basé sur les indicateurs de confiance"""

        # Seuil très bas pour patterns haute confiance
        if high_confidence:
            return 0.05

        # Seuil bas pour genetics + metrics
        if genetics and technical_metrics:
            return 0.08

        # Seuil réduit pour genetics seul ou metrics multiples
        if genetics or metrics_count >= 2:
            return 0.10

        # Seuil normal pour vocabulaire générique
        return 0.12

    def _analyze_domain_coverage(
        self, text_lower: str, words: List[str]
    ) -> Dict[str, float]:
        """Analyse la couverture par domaine spécialisé"""
        domains = {
            "genetics": ["ross", "cobb", "hubbard", "isa", "lohmann", "line", "strain"],
            "nutrition": ["feed", "protein", "energy", "lysine", "calcium", "fcr"],
            "environment": [
                "temperature",
                "ventilation",
                "humidity",
                "lighting",
                "tunnel",
            ],
            "performance": [
                "weight",
                "gain",
                "mortality",
                "uniformity",
                "epef",
                "production",
            ],
            "health": [
                "vaccination",
                "disease",
                "antibiotic",
                "biosecurity",
                "diagnosis",
            ],
            "economics": ["cost", "price", "margin", "profit", "efficiency", "roi"],
        }

        coverage = {}
        for domain, keywords in domains.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            coverage[domain] = min(1.0, matches / len(keywords))

        return coverage

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de couverture - Nouveau pour health-check"""
        return {
            **self.coverage_stats,
            "cache_info": {
                "hits": self.is_poultry_related.cache_info().hits,
                "misses": self.is_poultry_related.cache_info().misses,
                "maxsize": self.is_poultry_related.cache_info().maxsize,
                "currsize": self.is_poultry_related.cache_info().currsize,
            },
        }

    def generate_semantic_fallback_candidates(
        self, entities: Dict[str, str]
    ) -> List[str]:
        """Génère des candidats de fallback sémantique pour le cache Redis"""
        candidates = []

        # Fallback 1: lignée + métrique (sans âge)
        if "line" in entities and "metrics" in entities:
            line_normalized = self._normalize_for_cache_key(entities["line"])
            metrics = entities["metrics"].split(",")[0]  # Première métrique
            candidates.append(f"{line_normalized}_{metrics}")

        # Fallback 2: lignée seule
        if "line" in entities:
            line_normalized = self._normalize_for_cache_key(entities["line"])
            candidates.append(f"{line_normalized}_general")

        # Fallback 3: métrique + type site
        if "metrics" in entities and "site_type" in entities:
            metrics = entities["metrics"].split(",")[0]
            candidates.append(f"{entities['site_type']}_{metrics}")

        return candidates[:3]  # Limite à 3 candidats
