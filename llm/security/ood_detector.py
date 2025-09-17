# -*- coding: utf-8 -*-
"""
ood_detector.py - Détecteur hors-domaine avec seuil dynamique basé sur l'intent
"""

import logging
import json
import os
from typing import Dict, List, Tuple
from config.config import DOMAIN_KEYWORDS, OOD_MIN_SCORE, OOD_STRICT_SCORE
from utils.utilities import METRICS
from utils.imports_and_dependencies import UNIDECODE_AVAILABLE

if UNIDECODE_AVAILABLE:
    from unidecode import unidecode

logger = logging.getLogger(__name__)


class EnhancedOODDetector:
    """Détecteur hors-domaine avec seuil dynamique basé sur l'intent"""

    def __init__(self, blocked_terms_path: str = None):
        self.blocked_terms = self._load_blocked_terms(blocked_terms_path)
        self.domain_keywords = DOMAIN_KEYWORDS

    def _load_blocked_terms(self, path: str = None) -> Dict[str, List[str]]:
        """Charge les termes bloqués depuis le fichier configuré"""
        if path is None:
            path = os.getenv("BLOCKED_TERMS_FILE", "/app/blocked_terms.json")
            if not os.path.exists(path):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                path = os.path.join(base_dir, "blocked_terms.json")

        try:
            with open(path, "r", encoding="utf-8") as f:
                blocked_terms = json.load(f)

            logger.info(
                f"Loaded {len(blocked_terms)} blocked term categories from {path}"
            )
            return blocked_terms

        except Exception as e:
            logger.warning(f"Erreur chargement blocked_terms depuis {path}: {e}")
            fallback = {
                "general": [
                    "crypto",
                    "bitcoin",
                    "football",
                    "film",
                    "politique",
                    "news",
                ]
            }
            logger.warning("Using fallback blocked_terms: %s", fallback)
            return fallback

    def calculate_ood_score(
        self, query: str, intent_result=None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """MODIFICATION: Calcul score OOD avec seuil dynamique basé sur l'intent"""
        query_lower = unidecode(query).lower() if UNIDECODE_AVAILABLE else query.lower()
        words = query_lower.split()

        # Boost entités métier
        entities_boost = 0.0
        genetic_metric_present = False
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
            if detected_business:
                entities_boost = 0.3 * len(detected_business)
                # Détecter si génétique + métrique sont présents
                if ("line" in entities or "species" in entities) and (
                    "weight" in entities or "fcr" in entities
                ):
                    genetic_metric_present = True

        # NOUVEAU: Boost intent confidence si disponible
        intent_boost = 0.0
        if intent_result and hasattr(intent_result, "confidence_breakdown"):
            breakdown = intent_result.confidence_breakdown
            # Si génétique + métrique détectés avec forte confidence
            if (
                breakdown.get("genetic_confidence", 0) > 0.7
                and breakdown.get("metric_confidence", 0) > 0.7
            ):
                intent_boost = 0.2

        # Score vocabulaire domaine
        domain_words = [word for word in words if word in self.domain_keywords]
        vocab_score = (
            (len(domain_words) / len(words) if words else 0.0)
            + entities_boost
            + intent_boost
        )

        # Score termes bloqués
        blocked_score = 0.0
        for category, terms in self.blocked_terms.items():
            category_matches = sum(1 for term in terms if term in query_lower)
            if category_matches > 0:
                blocked_score = max(
                    blocked_score, min(0.7, category_matches / max(2, len(words) // 2))
                )

        # Score final
        if vocab_score > 0.4:
            final_score = max(0.7, vocab_score - blocked_score * 0.3)
        elif entities_boost > 0:
            final_score = 0.6 + entities_boost - blocked_score * 0.2
        elif blocked_score > 0.6:
            final_score = 0.1
        else:
            final_score = (vocab_score * 0.8) - (blocked_score * 0.2)

        # MODIFICATION: Seuil dynamique
        threshold = OOD_MIN_SCORE
        generic_vocab_only = len(domain_words) <= 1 and entities_boost == 0

        if genetic_metric_present:
            # Requête spécifique avec génétique + métrique -> seuil plus souple
            threshold = max(0.2, OOD_MIN_SCORE - 0.1)
            METRICS.ood_stats["genetic_metric_threshold_applied"] += 1
        elif generic_vocab_only and len(words) > 3:
            # Vocabulaire générique seulement -> seuil plus strict
            threshold = OOD_STRICT_SCORE
            METRICS.ood_stats["strict_threshold_applied"] += 1

        is_in_domain = final_score > threshold
        logger.debug(
            "OOD score detail: vocab=%.3f ent=%.3f intent=%.3f blocked=%.3f final=%.3f thr=%.3f in_domain=%s",
            vocab_score,
            entities_boost,
            intent_boost,
            blocked_score,
            final_score,
            threshold,
            is_in_domain,
        )

        # MODIFICATION: Tracer les raisons de filtrage
        if not is_in_domain:
            if blocked_score > 0.5:
                METRICS.ood_filtered(final_score, "blocked_terms")
            elif generic_vocab_only:
                METRICS.ood_filtered(final_score, "generic_vocab")
            else:
                METRICS.ood_filtered(final_score, "low_domain_score")

        score_details = {
            "vocab_score": vocab_score,
            "entities_boost": entities_boost,
            "intent_boost": intent_boost,
            "blocked_score": blocked_score,
            "final_score": final_score,
            "threshold_used": threshold,
            "genetic_metric_present": genetic_metric_present,
            "generic_vocab_only": generic_vocab_only,
        }

        return is_in_domain, final_score, score_details
