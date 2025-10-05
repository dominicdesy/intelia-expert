# -*- coding: utf-8 -*-
"""
hallucination_detector.py - Hallucination detection methods for guardrails system

This module contains methods for detecting hallucination risks and internal contradictions
in AI-generated responses. Extracted from advanced_guardrails.py for better modularity.
"""

import asyncio
import re
import logging
from utils.types import Dict, List, Tuple

from .config import HALLUCINATION_PATTERNS

logger = logging.getLogger(__name__)


class HallucinationDetector:
    """Detector for hallucination risks and internal contradictions in responses"""

    def __init__(self):
        """Initialize the hallucination detector"""
        self.hallucination_patterns = HALLUCINATION_PATTERNS

    async def _detect_hallucination_risk(
        self, response: str, context_docs: List[Dict]
    ) -> Tuple[float, Dict]:
        """Détection améliorée du risque d'hallucination"""
        try:
            risk_score = 0.0
            detected_patterns = []
            response_lower = response.lower()

            # Vérification des patterns suspects avec scoring pondéré
            for pattern in self.hallucination_patterns:
                matches = re.findall(pattern, response_lower, re.IGNORECASE)
                if matches:
                    detected_patterns.extend(matches)
                    # Pondération selon la criticité du pattern
                    if "opinion" in pattern or "think" in pattern:
                        risk_score += 0.2 * len(matches)  # Opinions = risque élevé
                    elif "généralement" in pattern or "usually" in pattern:
                        risk_score += 0.15 * len(
                            matches
                        )  # Généralisations = risque modéré
                    else:
                        risk_score += 0.1 * len(matches)  # Autres = risque faible

            # Détection d'affirmations sans support avec parallélisme
            unsupported_statements = await self._find_unsupported_statements_parallel(
                response, context_docs
            )
            risk_score += 0.2 * len(unsupported_statements)

            # Vérification des données numériques sans source
            numeric_claims = re.findall(
                r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|semaine|°C|kcal)",
                response,
                re.IGNORECASE,
            )

            if numeric_claims:
                verification_tasks = [
                    self._verify_enhanced_numeric_claim(numeric, context_docs)
                    for numeric in numeric_claims
                ]

                verification_results = await asyncio.gather(
                    *verification_tasks, return_exceptions=True
                )
                supported_numerics = sum(1 for r in verification_results if r is True)

                unsupported_ratio = 1 - (supported_numerics / len(numeric_claims))
                risk_score += 0.25 * unsupported_ratio

            # Détection de contradictions internes
            internal_contradictions = self._detect_internal_contradictions(response)
            risk_score += 0.3 * len(internal_contradictions)

            # Normalisation et plafonnement
            risk_score = min(1.0, risk_score)

            return risk_score, {
                "suspected_patterns": detected_patterns,
                "unsupported_statements": len(unsupported_statements),
                "numeric_claims": len(numeric_claims),
                "supported_numerics": (
                    sum(1 for r in verification_results if r is True)
                    if numeric_claims
                    else 0
                ),
                "internal_contradictions": internal_contradictions,
                "risk_factors": {
                    "opinion_expressions": len(
                        [
                            p
                            for p in detected_patterns
                            if any(word in p for word in ["opinion", "think", "avis"])
                        ]
                    ),
                    "generalizations": len(
                        [
                            p
                            for p in detected_patterns
                            if any(
                                word in p
                                for word in ["généralement", "usually", "often"]
                            )
                        ]
                    ),
                    "vague_quantifiers": len(
                        [
                            p
                            for p in detected_patterns
                            if any(
                                word in p
                                for word in ["environ", "about", "approximativement"]
                            )
                        ]
                    ),
                },
            }

        except Exception as e:
            logger.warning(f"Erreur détection hallucination: {e}")
            return 0.5, {"error": str(e)}

    def _detect_internal_contradictions(self, response: str) -> List[str]:
        """Détecte les contradictions internes dans la réponse"""
        contradictions = []

        try:
            sentences = [s.strip() for s in re.split(r"[.!?]+", response)]

            # Patterns de contradiction simples
            contradiction_pairs = [
                (r"recommandé|conseillé|optimal", r"éviter|déconseillé|problématique"),
                (r"augmenter|élever|accroître", r"diminuer|réduire|baisser"),
                (r"maximum|élevé|haut", r"minimum|faible|bas"),
                (r"meilleur|supérieur|excellent", r"pire|inférieur|mauvais"),
            ]

            for i, sentence1 in enumerate(sentences):
                for j, sentence2 in enumerate(sentences[i + 1 :], i + 1):
                    for pos_pattern, neg_pattern in contradiction_pairs:
                        if re.search(pos_pattern, sentence1.lower()) and re.search(
                            neg_pattern, sentence2.lower()
                        ):
                            contradictions.append(
                                f"Contradiction entre phrases {i+1} et {j+1}: '{sentence1[:50]}...' vs '{sentence2[:50]}...'"
                            )
                            break

        except Exception as e:
            logger.warning(f"Erreur détection contradictions: {e}")

        return contradictions

    # Helper methods

    async def _find_unsupported_statements_parallel(
        self, response: str, context_docs: List[Dict]
    ) -> List[str]:
        """Recherche parallélisée des affirmations non supportées"""
        try:
            sentences = [
                s.strip() for s in re.split(r"[.!?]+", response) if len(s.strip()) > 10
            ]

            if not sentences:
                return []

            # Vérification parallèle du support
            support_tasks = [
                self._find_enhanced_claim_support(sentence, context_docs)
                for sentence in sentences
            ]

            support_scores = await asyncio.gather(
                *support_tasks, return_exceptions=True
            )

            unsupported = []
            threshold = 0.3

            for i, score in enumerate(support_scores):
                if not isinstance(score, Exception) and score < threshold:
                    unsupported.append(sentences[i])

            return unsupported

        except Exception as e:
            logger.warning(f"Erreur détection statements non supportés: {e}")
            return []

    async def _find_enhanced_claim_support(
        self, claim: str, context_docs: List[Dict]
    ) -> float:
        """Recherche de support améliorée avec similarité sémantique"""
        try:
            max_support = 0.0
            claim_words = set(self._normalize_text(claim).split())

            # Extraction des éléments clés de la claim
            key_elements = self._extract_key_elements(claim)

            for doc in context_docs:
                content = doc.get("content", "")
                if not content:
                    continue

                content_normalized = self._normalize_text(content)
                content_words = set(content_normalized.split())

                # Similarité lexicale de base
                if claim_words and content_words:
                    overlap = len(claim_words.intersection(content_words))
                    lexical_similarity = overlap / len(claim_words)

                    # Bonus pour éléments clés
                    key_matches = sum(
                        1 for key in key_elements if key in content_normalized
                    )
                    key_bonus = (
                        (key_matches / len(key_elements)) * 0.3 if key_elements else 0
                    )

                    similarity = min(1.0, lexical_similarity + key_bonus)
                    max_support = max(max_support, similarity)

                # Vérification de présence directe avec variations
                if self._fuzzy_match(claim, content):
                    max_support = max(max_support, 0.9)

            return min(1.0, max_support)

        except Exception as e:
            logger.warning(f"Erreur recherche support claim: {e}")
            return 0.3

    async def _verify_enhanced_numeric_claim(
        self, numeric_text: str, context_docs: List[Dict]
    ) -> bool:
        """Vérification améliorée des valeurs numériques"""
        try:
            # Extraction du nombre et de l'unité
            number_match = re.search(r"(\d+[.,]?\d*)\s*([a-zA-Z%°]+)", numeric_text)
            if not number_match:
                return False

            value_str = number_match.group(1)
            unit = number_match.group(2).lower()

            try:
                value = float(value_str.replace(",", "."))
            except ValueError:
                return False

            # Recherche dans les documents avec tolérance
            for doc in context_docs:
                content = doc.get("content", "").lower()

                # Recherche exacte
                if numeric_text.lower() in content:
                    return True

                # Recherche avec tolérance de ±15%
                similar_pattern = rf"(\d+[.,]?\d*)\s*{re.escape(unit)}"
                matches = re.findall(similar_pattern, content, re.IGNORECASE)

                for match in matches:
                    try:
                        doc_value = float(match.replace(",", "."))
                        tolerance = 0.15  # ±15%
                        if abs(doc_value - value) / value <= tolerance:
                            return True
                    except ValueError:
                        continue

            return False

        except Exception as e:
            logger.warning(f"Erreur vérification numérique: {e}")
            return False

    def _extract_key_elements(self, text: str) -> List[str]:
        """Extrait les éléments clés d'un texte (nombres, termes techniques, etc.)"""
        key_elements = []

        # Nombres avec unités
        numbers = re.findall(
            r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|°C|kcal)", text, re.IGNORECASE
        )
        key_elements.extend(numbers)

        # Lignées génétiques
        genetic_lines = re.findall(
            r"(?:ross|cobb|hubbard|isa)\s*\d*", text, re.IGNORECASE
        )
        key_elements.extend(genetic_lines)

        return key_elements

    def _fuzzy_match(self, claim: str, content: str) -> bool:
        """Correspondance floue entre claim et contenu"""
        claim_norm = self._normalize_text(claim)
        content_norm = self._normalize_text(content)

        # Recherche de segments significatifs
        claim_segments = [seg for seg in claim_norm.split() if len(seg) > 3]

        if not claim_segments:
            return False

        matches = sum(1 for seg in claim_segments if seg in content_norm)
        return (matches / len(claim_segments)) > 0.6

    def _normalize_text(self, text: str) -> str:
        """Normalisation de texte pour comparaisons"""
        # Conversion en minuscules
        normalized = text.lower()

        # Suppression accents (version simple)
        accent_map = {
            "é": "e",
            "è": "e",
            "ê": "e",
            "ë": "e",
            "à": "a",
            "â": "a",
            "ä": "a",
            "ù": "u",
            "û": "u",
            "ü": "u",
            "ô": "o",
            "ö": "o",
            "î": "i",
            "ï": "i",
            "ç": "c",
        }

        for accented, simple in accent_map.items():
            normalized = normalized.replace(accented, simple)

        # Suppression ponctuation excessive
        normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized


__all__ = ["HallucinationDetector"]
