# -*- coding: utf-8 -*-

"""

advanced_guardrails.py - Système de guardrails avancé pour la vérification RAG
Vérifie que les réponses sont basées sur les documents et détecte les hallucinations

"""

import logging
import re
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class VerificationLevel(Enum):
    MINIMAL = "minimal"  # Vérification basique
    STANDARD = "standard"  # Vérification normale
    STRICT = "strict"  # Vérification rigoureuse
    CRITICAL = "critical"  # Vérification maximale


@dataclass
class GuardrailResult:
    """Résultat de la vérification par guardrails"""

    is_valid: bool
    confidence: float
    violations: List[str]
    warnings: List[str]
    evidence_support: float
    hallucination_risk: float
    correction_suggestions: List[str]
    metadata: Dict[str, Any]


class AdvancedResponseGuardrails:
    """Système de guardrails avancé pour vérifier les réponses RAG"""

    def __init__(
        self, client, verification_level: VerificationLevel = VerificationLevel.STANDARD
    ):
        self.client = client
        self.verification_level = verification_level

        # Patterns suspects (potentielles hallucinations)
        self.hallucination_patterns = [
            r"selon moi|à mon avis|je pense que|il me semble",
            r"généralement|habituellement|en général|typiquement",
            r"il est recommandé|il faut|vous devriez|on conseille",
            r"dans la plupart des cas|souvent|parfois",
            r"environ|approximativement|autour de|près de",
        ]

        # Indicateurs de support documentaire
        self.evidence_indicators = [
            r"selon le document|d'après les données|les résultats montrent",
            r"tableau \d+|figure \d+|source:|référence:",
            r"étude de|essai|test|mesure|observation",
            r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|semaine)",
        ]

        # Mots-clés métier aviculture (pour cohérence domaine)
        self.domain_keywords = {
            "performance": ["fcr", "poids", "gain", "croissance", "conversion"],
            "sante": ["mortalité", "maladie", "vaccination", "prophylaxie"],
            "nutrition": ["aliment", "protéine", "énergie", "digestibilité"],
            "reproduction": ["ponte", "fertilité", "éclosabilité", "couvaison"],
            "technique": ["ventilation", "température", "densité", "éclairage"],
        }

    async def verify_response(
        self, query: str, response: str, context_docs: List[Dict], intent_result=None
    ) -> GuardrailResult:
        """Vérification complète de la réponse"""
        try:
            # Vérifications en parallèle pour optimiser
            evidence_task = self._check_evidence_support(response, context_docs)
            hallucination_task = self._detect_hallucination_risk(response, context_docs)
            consistency_task = self._check_domain_consistency(
                response, query, intent_result
            )
            factual_task = self._verify_factual_claims(response, context_docs)

            evidence_score, evidence_details = await evidence_task
            hallucination_risk, hallucination_details = await hallucination_task
            consistency_score, consistency_issues = await consistency_task
            factual_accuracy, factual_issues = await factual_task

            # Agrégation des résultats
            violations = []
            warnings = []
            corrections = []

            # Analyse des violations critiques
            if evidence_score < 0.3:
                violations.append("Support documentaire insuffisant")
                corrections.append(
                    "Reformuler en s'appuyant davantage sur les documents fournis"
                )

            if hallucination_risk > 0.7:
                violations.append("Risque élevé d'hallucination détecté")
                corrections.append("Vérifier chaque affirmation avec les sources")

            if consistency_score < 0.4:
                violations.append("Incohérence avec le domaine aviculture")
                corrections.append("Recentrer sur le contexte technique avicole")

            # Analyse des avertissements
            if evidence_score < 0.6:
                warnings.append("Support documentaire modéré")

            if hallucination_risk > 0.4:
                warnings.append("Éléments génériques détectés")

            if len(factual_issues) > 0:
                warnings.extend(factual_issues)

            # Calcul de la confiance globale
            confidence = self._calculate_global_confidence(
                evidence_score, hallucination_risk, consistency_score, factual_accuracy
            )

            # Décision finale basée sur le niveau de vérification
            is_valid = self._make_validation_decision(
                evidence_score,
                hallucination_risk,
                consistency_score,
                len(violations),
                len(warnings),
            )

            return GuardrailResult(
                is_valid=is_valid,
                confidence=confidence,
                violations=violations,
                warnings=warnings,
                evidence_support=evidence_score,
                hallucination_risk=hallucination_risk,
                correction_suggestions=corrections,
                metadata={
                    "verification_level": self.verification_level.value,
                    "evidence_details": evidence_details,
                    "hallucination_details": hallucination_details,
                    "consistency_score": consistency_score,
                    "factual_accuracy": factual_accuracy,
                    "consistency_issues": consistency_issues,
                },
            )

        except Exception as e:
            logger.error(f"Erreur vérification guardrails: {e}")
            return GuardrailResult(
                is_valid=True,  # Fail-open par sécurité
                confidence=0.5,
                violations=[],
                warnings=[f"Erreur vérification: {str(e)}"],
                evidence_support=0.5,
                hallucination_risk=0.5,
                correction_suggestions=[],
                metadata={"error": str(e)},
            )

    async def _check_evidence_support(
        self, response: str, context_docs: List[Dict]
    ) -> Tuple[float, Dict]:
        """Vérifie le support documentaire de la réponse"""
        try:
            # Extraire les affirmations factuelles
            claims = self._extract_factual_claims(response)

            # Vérifier le support pour chaque affirmation
            supported_claims = 0
            total_claims = len(claims)

            if total_claims == 0:
                return 0.5, {"no_factual_claims": True}

            claim_support = []
            for claim in claims:
                support_score = await self._find_claim_support(claim, context_docs)
                claim_support.append({"claim": claim, "support_score": support_score})
                if support_score > 0.6:
                    supported_claims += 1

            evidence_score = (
                supported_claims / total_claims if total_claims > 0 else 0.5
            )

            # Bonus pour indicateurs explicites d'évidence
            evidence_indicators_found = sum(
                1
                for pattern in self.evidence_indicators
                if re.search(pattern, response.lower())
            )

            if evidence_indicators_found > 0:
                evidence_score = min(
                    1.0, evidence_score + 0.1 * evidence_indicators_found
                )

            return evidence_score, {
                "total_claims": total_claims,
                "supported_claims": supported_claims,
                "claim_support": claim_support,
                "evidence_indicators": evidence_indicators_found,
            }

        except Exception as e:
            logger.warning(f"Erreur vérification evidence: {e}")
            return 0.5, {"error": str(e)}

    async def _detect_hallucination_risk(
        self, response: str, context_docs: List[Dict]
    ) -> Tuple[float, Dict]:
        """Détecte le risque d'hallucination dans la réponse"""
        try:
            risk_score = 0.0
            detected_patterns = []

            # Vérifier les patterns suspects
            for pattern in self.hallucination_patterns:
                matches = re.findall(pattern, response.lower())
                if matches:
                    detected_patterns.extend(matches)
                    risk_score += 0.15 * len(matches)

            # Vérifier les affirmations sans support
            unsupported_statements = await self._find_unsupported_statements(
                response, context_docs
            )
            risk_score += 0.2 * len(unsupported_statements)

            # Vérifier les données numériques sans source
            numeric_claims = re.findall(r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour)", response)
            supported_numerics = 0

            for numeric in numeric_claims:
                if await self._verify_numeric_claim(numeric, context_docs):
                    supported_numerics += 1

            if numeric_claims:
                unsupported_ratio = 1 - (supported_numerics / len(numeric_claims))
                risk_score += 0.3 * unsupported_ratio

            # Normaliser le score
            risk_score = min(1.0, risk_score)

            return risk_score, {
                "suspected_patterns": detected_patterns,
                "unsupported_statements": unsupported_statements,
                "numeric_claims": len(numeric_claims),
                "supported_numerics": supported_numerics,
            }

        except Exception as e:
            logger.warning(f"Erreur détection hallucination: {e}")
            return 0.5, {"error": str(e)}

    async def _check_domain_consistency(
        self, response: str, query: str, intent_result
    ) -> Tuple[float, List[str]]:
        """Vérifie la cohérence avec le domaine aviculture"""
        try:
            issues = []
            domain_score = 0.5  # Score neutre par défaut

            # Vérifier la présence de vocabulaire métier
            domain_words_found = 0
            total_domain_words = 0

            for category, keywords in self.domain_keywords.items():
                total_domain_words += len(keywords)
                for keyword in keywords:
                    if keyword.lower() in response.lower():
                        domain_words_found += 1

            if total_domain_words > 0:
                domain_score = min(
                    1.0, 0.3 + (domain_words_found / total_domain_words) * 0.7
                )

            # Vérifier la cohérence avec l'intention détectée
            if intent_result and hasattr(intent_result, "detected_entities"):
                entities = intent_result.detected_entities

                # Vérifier mention des entités clés
                key_entities_mentioned = 0
                total_key_entities = 0

                for entity_type in ["line", "species", "phase"]:
                    if entity_type in entities:
                        total_key_entities += 1
                        entity_value = entities[entity_type].lower()
                        if entity_value in response.lower():
                            key_entities_mentioned += 1
                        else:
                            issues.append(
                                f"Entité {entity_type} '{entities[entity_type]}' non mentionnée"
                            )

                if total_key_entities > 0:
                    entity_consistency = key_entities_mentioned / total_key_entities
                    domain_score = (domain_score + entity_consistency) / 2

            # Détecter les incohérences flagrantes
            inconsistent_terms = [
                "crypto",
                "bitcoin",
                "politique",
                "football",
                "cinéma",
            ]

            for term in inconsistent_terms:
                if term in response.lower():
                    issues.append(f"Terme hors-domaine détecté: {term}")
                    domain_score *= 0.5

            return domain_score, issues

        except Exception as e:
            logger.warning(f"Erreur vérification consistance: {e}")
            return 0.5, [f"Erreur: {str(e)}"]

    async def _verify_factual_claims(
        self, response: str, context_docs: List[Dict]
    ) -> Tuple[float, List[str]]:
        """Vérifie la précision factuelle des affirmations"""
        try:
            issues = []

            # Extraire les valeurs numériques spécifiques
            numeric_patterns = [
                r"(\d+[.,]?\d*)\s*(g|kg|grammes?|kilogrammes?)",  # Poids
                r"(\d+[.,]?\d*)\s*%",  # Pourcentages
                r"(\d+[.,]?\d*)\s*(j|jours?|semaines?)",  # Durées
                r"FCR.*?(\d+[.,]?\d*)",  # FCR
                r"(\d+[.,]?\d*)\s*(°C|degrés?)",  # Températures
            ]

            verified_claims = 0
            total_claims = 0

            for pattern in numeric_patterns:
                matches = re.findall(pattern, response, re.IGNORECASE)
                for match in matches:
                    total_claims += 1
                    value = match[0] if isinstance(match, tuple) else match
                    unit = (
                        match[1] if isinstance(match, tuple) and len(match) > 1 else ""
                    )

                    # Vérifier si cette valeur est supportée par les documents
                    if await self._verify_specific_value(value, unit, context_docs):
                        verified_claims += 1
                    else:
                        issues.append(f"Valeur non vérifiée: {value} {unit}")

            # Vérifier les affirmations qualitatives
            qualitative_claims = [
                "recommandé",
                "optimal",
                "idéal",
                "maximum",
                "minimum",
                "meilleur",
                "préférable",
                "conseillé",
                "éviter",
            ]

            for claim_word in qualitative_claims:
                if claim_word in response.lower():
                    total_claims += 1
                    if await self._verify_qualitative_claim(
                        claim_word, response, context_docs
                    ):
                        verified_claims += 1
                    else:
                        issues.append(
                            f"Affirmation qualitative non supportée: {claim_word}"
                        )

            # Calculer le score de précision factuelle
            accuracy_score = verified_claims / total_claims if total_claims > 0 else 0.8

            return accuracy_score, issues

        except Exception as e:
            logger.warning(f"Erreur vérification factuelle: {e}")
            return 0.6, [f"Erreur vérification: {str(e)}"]

    async def _find_claim_support(self, claim: str, context_docs: List[Dict]) -> float:
        """Trouve le support documentaire pour une affirmation"""
        try:
            max_support = 0.0
            claim_words = set(claim.lower().split())

            for doc in context_docs:
                content = doc.get("content", "").lower()
                content_words = set(content.split())

                # Calculer la similarité lexicale
                if claim_words and content_words:
                    overlap = len(claim_words.intersection(content_words))
                    similarity = overlap / len(claim_words)
                    max_support = max(max_support, similarity)

                # Vérifier la présence directe
                if claim.lower() in content:
                    max_support = max(max_support, 0.9)

            return min(1.0, max_support)

        except Exception as e:
            logger.warning(f"Erreur recherche support claim: {e}")
            return 0.3

    async def _find_unsupported_statements(
        self, response: str, context_docs: List[Dict]
    ) -> List[str]:
        """Identifie les affirmations sans support documentaire"""
        try:
            # Diviser la réponse en phrases
            sentences = re.split(r"[.!?]+", response)
            unsupported = []

            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 10:  # Ignorer les phrases trop courtes
                    continue

                # Vérifier si la phrase a un support
                support_score = await self._find_claim_support(sentence, context_docs)
                if support_score < 0.3:
                    unsupported.append(sentence)

            return unsupported

        except Exception as e:
            logger.warning(f"Erreur détection statements non supportés: {e}")
            return []

    async def _verify_numeric_claim(
        self, numeric_text: str, context_docs: List[Dict]
    ) -> bool:
        """Vérifie si une valeur numérique est présente dans les documents"""
        try:
            # Extraire juste le nombre
            number_match = re.search(r"\d+[.,]?\d*", numeric_text)
            if not number_match:
                return False

            number = number_match.group()

            # Chercher dans les documents
            for doc in context_docs:
                content = doc.get("content", "")
                if number in content:
                    return True

            return False

        except Exception as e:
            logger.warning(f"Erreur vérification numérique: {e}")
            return False

    async def _verify_specific_value(
        self, value: str, unit: str, context_docs: List[Dict]
    ) -> bool:
        """Vérifie une valeur spécifique avec son unité"""
        try:
            for doc in context_docs:
                content = doc.get("content", "").lower()

                # Recherche exacte
                if f"{value} {unit}".lower() in content:
                    return True

                # Recherche avec variations d'espacement
                if f"{value}{unit}".lower() in content:
                    return True

                # Recherche de valeurs proches (±10%)
                try:
                    val_float = float(value.replace(",", "."))
                    # Chercher des valeurs dans une plage de ±10%
                    range_min = val_float * 0.9
                    range_max = val_float * 1.1

                    # Pattern pour trouver des nombres similaires avec la même unité
                    similar_pattern = rf"(\d+[.,]?\d*)\s*{re.escape(unit)}"
                    matches = re.findall(similar_pattern, content, re.IGNORECASE)

                    for match in matches:
                        doc_val = float(match.replace(",", "."))
                        if range_min <= doc_val <= range_max:
                            return True

                except ValueError:
                    pass

            return False

        except Exception as e:
            logger.warning(f"Erreur vérification valeur spécifique: {e}")
            return False

    async def _verify_qualitative_claim(
        self, claim_word: str, response: str, context_docs: List[Dict]
    ) -> bool:
        """Vérifie les affirmations qualitatives"""
        try:
            # Extraire le contexte autour du mot-clé
            context_pattern = rf".{{0,50}}{re.escape(claim_word)}.{{0,50}}"
            matches = re.findall(context_pattern, response.lower(), re.IGNORECASE)

            for match in matches:
                # Vérifier si ce contexte apparaît dans les documents
                for doc in context_docs:
                    content = doc.get("content", "").lower()

                    # Recherche de contexte similaire
                    words_in_match = set(match.split())
                    content_words = set(content.split())

                    overlap = len(words_in_match.intersection(content_words))
                    similarity = overlap / len(words_in_match) if words_in_match else 0

                    if similarity > 0.6:
                        return True

            return False

        except Exception as e:
            logger.warning(f"Erreur vérification claim qualitatif: {e}")
            return False

    def _extract_factual_claims(self, response: str) -> List[str]:
        """Extrait les affirmations factuelles de la réponse"""
        try:
            claims = []

            # Diviser en phrases
            sentences = re.split(r"[.!?]+", response)

            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 15:  # Ignorer les phrases trop courtes
                    continue

                # Filtrer les phrases contenant des faits mesurables
                factual_indicators = [
                    r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|°C)",  # Valeurs numériques
                    r"(?:poids|fcr|mortalité|ponte|croissance)",  # Métriques clés
                    r"(?:recommandé|optimal|maximum|minimum)",  # Recommandations
                    r"(?:lignée|espèce|phase|âge)",  # Classifications
                ]

                for pattern in factual_indicators:
                    if re.search(pattern, sentence.lower()):
                        claims.append(sentence)
                        break

            return claims

        except Exception as e:
            logger.warning(f"Erreur extraction claims: {e}")
            return []

    def _calculate_global_confidence(
        self,
        evidence_score: float,
        hallucination_risk: float,
        consistency_score: float,
        factual_accuracy: float,
    ) -> float:
        """Calcule la confiance globale basée sur tous les indicateurs"""
        try:
            # Pondération des différents facteurs
            weights = {
                "evidence": 0.35,
                "hallucination": 0.25,  # Inversé car c'est un risque
                "consistency": 0.20,
                "factual": 0.20,
            }

            # Calcul pondéré (hallucination_risk est inversé)
            confidence = (
                evidence_score * weights["evidence"]
                + (1 - hallucination_risk) * weights["hallucination"]
                + consistency_score * weights["consistency"]
                + factual_accuracy * weights["factual"]
            )

            return min(0.95, max(0.05, confidence))

        except Exception as e:
            logger.warning(f"Erreur calcul confiance: {e}")
            return 0.5

    def _make_validation_decision(
        self,
        evidence_score: float,
        hallucination_risk: float,
        consistency_score: float,
        violation_count: int,
        warning_count: int,
    ) -> bool:
        """Décision de validation basée sur le niveau de vérification"""
        try:
            if self.verification_level == VerificationLevel.MINIMAL:
                return violation_count == 0

            elif self.verification_level == VerificationLevel.STANDARD:
                return (
                    violation_count == 0
                    and evidence_score >= 0.4
                    and hallucination_risk <= 0.7
                )

            elif self.verification_level == VerificationLevel.STRICT:
                return (
                    violation_count == 0
                    and warning_count <= 2
                    and evidence_score >= 0.6
                    and hallucination_risk <= 0.5
                    and consistency_score >= 0.5
                )

            elif self.verification_level == VerificationLevel.CRITICAL:
                return (
                    violation_count == 0
                    and warning_count <= 1
                    and evidence_score >= 0.8
                    and hallucination_risk <= 0.3
                    and consistency_score >= 0.7
                )

            return True  # Fallback

        except Exception as e:
            logger.warning(f"Erreur décision validation: {e}")
            return True  # Fail-open par sécurité

    async def quick_verify(self, response: str, context_docs: List[Dict]) -> bool:
        """Vérification rapide pour les cas simples"""
        try:
            # Vérification basique sans LLM
            if not context_docs:
                return False

            # Vérifier la présence de contenu des documents dans la réponse
            doc_overlap = 0
            total_docs = len(context_docs)

            for doc in context_docs:
                content_words = set(doc.get("content", "").lower().split())
                response_words = set(response.lower().split())

                if content_words and response_words:
                    overlap = len(content_words.intersection(response_words))
                    similarity = overlap / min(len(content_words), len(response_words))

                    if similarity > 0.1:  # Seuil bas pour vérification rapide
                        doc_overlap += 1

            overlap_ratio = doc_overlap / total_docs if total_docs > 0 else 0
            return (
                overlap_ratio >= 0.3
            )  # Au moins 30% des docs doivent avoir un overlap

        except Exception as e:
            logger.warning(f"Erreur vérification rapide: {e}")
            return True  # Fail-open

    def get_guardrails_config(self) -> Dict[str, Any]:
        """Retourne la configuration des guardrails"""
        return {
            "verification_level": self.verification_level.value,
            "hallucination_patterns": len(self.hallucination_patterns),
            "evidence_indicators": len(self.evidence_indicators),
            "domain_categories": list(self.domain_keywords.keys()),
            "validation_thresholds": {
                "minimal": {"violations": 0},
                "standard": {
                    "violations": 0,
                    "evidence_min": 0.4,
                    "hallucination_max": 0.7,
                },
                "strict": {
                    "violations": 0,
                    "warnings_max": 2,
                    "evidence_min": 0.6,
                    "hallucination_max": 0.5,
                },
                "critical": {
                    "violations": 0,
                    "warnings_max": 1,
                    "evidence_min": 0.8,
                    "hallucination_max": 0.3,
                },
            },
        }


# Factory function pour créer le système de guardrails
def create_response_guardrails(client, verification_level: str = "standard"):
    """Crée un système de guardrails avec le niveau de vérification spécifié"""
    level_map = {
        "minimal": VerificationLevel.MINIMAL,
        "standard": VerificationLevel.STANDARD,
        "strict": VerificationLevel.STRICT,
        "critical": VerificationLevel.CRITICAL,
    }

    level = level_map.get(verification_level.lower(), VerificationLevel.STANDARD)
    return AdvancedResponseGuardrails(client, level)
