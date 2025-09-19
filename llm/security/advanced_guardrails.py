# -*- coding: utf-8 -*-
"""
advanced_guardrails.py - Système de guardrails avancé pour la vérification RAG
Vérifie que les réponses sont basées sur les documents et détecte les hallucinations
Version corrigée avec parallélisme optimisé et encodage fixé
"""

import logging
import re
import asyncio
import hashlib
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)


class VerificationLevel(Enum):
    """Niveaux de vérification avec seuils adaptatifs"""

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
    processing_time: float = 0.0


class AdvancedResponseGuardrails:
    """Système de guardrails avancé pour vérifier les réponses RAG"""

    def __init__(
        self,
        client,
        verification_level: VerificationLevel = VerificationLevel.STANDARD,
        enable_cache: bool = True,
        cache_size: int = 1000,
    ):
        self.client = client
        self.verification_level = verification_level
        self.enable_cache = enable_cache

        # Cache pour optimiser les vérifications répétées
        self._verification_cache = {} if enable_cache else None
        self._cache_max_size = cache_size

        # Patterns suspects multilingues (potentielles hallucinations)
        self.hallucination_patterns = [
            # Français
            r"selon moi|à mon avis|je pense que|il me semble|personnellement",
            r"généralement|habituellement|en général|typiquement|souvent",
            r"il est recommandé|il faut|vous devriez|on conseille|il vaut mieux",
            r"dans la plupart des cas|parfois|quelquefois|peut-être",
            r"environ|approximativement|autour de|près de|à peu près",
            r"probablement|vraisemblablement|sans doute|apparemment",
            # Anglais
            r"i think|i believe|in my opinion|personally|it seems to me",
            r"usually|typically|generally|commonly|often",
            r"it is recommended|you should|one should|it's better to",
            r"in most cases|sometimes|probably|likely|apparently",
            r"approximately|around|about|roughly|nearly",
            # Expressions vagues
            r"comme vous le savez|comme on dit|il paraît que",
            r"on dit que|d'après ce qu'on sait|il semblerait",
        ]

        # Indicateurs de support documentaire renforcés
        self.evidence_indicators = [
            # Références explicites
            r"selon le document|d'après les données|les résultats montrent",
            r"d'après l'étude|selon l'analyse|les mesures indiquent",
            r"tableau \d+|figure \d+|source\s*:|référence\s*:",
            r"page \d+|section \d+|annexe \d+",
            # Termes scientifiques
            r"étude de|essai|test|mesure|observation|expérience",
            r"recherche|analyse|évaluation|examen|investigation",
            r"protocole|méthodologie|procédure|standard",
            # Données quantitatives avec contexte
            r"les données montrent|les chiffres révèlent|l'analyse démontre",
            r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|semaine|°C|kcal)\s+(?:mesurés?|observés?|enregistrés?)",
        ]

        # Vocabulaire métier aviculture enrichi et organisé
        self.domain_keywords = {
            "performance": [
                "fcr",
                "ic",
                "indice",
                "conversion",
                "poids",
                "gain",
                "croissance",
                "rendement",
                "efficacité",
                "productivité",
                "performance",
                "résultats",
                "vitesse",
                "développement",
                "évolution",
                "progression",
            ],
            "sante": [
                "mortalité",
                "morbidité",
                "maladie",
                "pathologie",
                "infection",
                "vaccination",
                "vaccin",
                "prophylaxie",
                "traitement",
                "santé",
                "viabilité",
                "résistance",
                "immunité",
                "symptômes",
                "diagnostic",
            ],
            "nutrition": [
                "aliment",
                "alimentation",
                "nutrition",
                "nutritionnel",
                "protéine",
                "énergie",
                "calories",
                "digestibilité",
                "nutriment",
                "vitamines",
                "minéraux",
                "calcium",
                "phosphore",
                "acides",
                "aminés",
                "fibres",
            ],
            "reproduction": [
                "ponte",
                "œuf",
                "œufs",
                "fertility",
                "fertilité",
                "éclosabilité",
                "couvaison",
                "incubation",
                "éclosion",
                "reproduction",
                "couvoir",
                "hatchabilité",
                "embryon",
                "poussin",
                "poussins",
            ],
            "technique": [
                "ventilation",
                "température",
                "densité",
                "éclairage",
                "logement",
                "bâtiment",
                "poulailler",
                "équipement",
                "installation",
                "système",
                "automatisation",
                "contrôle",
                "régulation",
                "ambiance",
            ],
            "genetique": [
                "lignée",
                "souche",
                "race",
                "ross",
                "cobb",
                "hubbard",
                "isa",
                "lohmann",
                "hy-line",
                "hybride",
                "sélection",
                "amélioration",
                "génétique",
                "héritabilité",
                "consanguinité",
            ],
        }

        # Seuils de validation adaptatifs par niveau
        self.validation_thresholds = {
            VerificationLevel.MINIMAL: {
                "evidence_min": 0.2,
                "hallucination_max": 0.8,
                "consistency_min": 0.1,
                "max_violations": 1,
                "max_warnings": 5,
            },
            VerificationLevel.STANDARD: {
                "evidence_min": 0.4,
                "hallucination_max": 0.7,
                "consistency_min": 0.3,
                "max_violations": 0,
                "max_warnings": 3,
            },
            VerificationLevel.STRICT: {
                "evidence_min": 0.6,
                "hallucination_max": 0.5,
                "consistency_min": 0.5,
                "max_violations": 0,
                "max_warnings": 2,
            },
            VerificationLevel.CRITICAL: {
                "evidence_min": 0.8,
                "hallucination_max": 0.3,
                "consistency_min": 0.7,
                "max_violations": 0,
                "max_warnings": 1,
            },
        }

    async def verify_response(
        self,
        query: str,
        response: str,
        context_docs: List[Dict],
        intent_result=None,
        use_cache: bool = True,
    ) -> GuardrailResult:
        """Vérification complète de la réponse avec parallélisme optimisé"""
        start_time = time.time()

        try:
            # Génération de clé de cache
            cache_key = None
            if self.enable_cache and use_cache:
                cache_key = self._generate_cache_key(query, response, context_docs)
                cached_result = self._get_from_cache(cache_key)
                if cached_result:
                    cached_result.processing_time = time.time() - start_time
                    return cached_result

            # CORRECTION PRINCIPALE: Vrai parallélisme avec asyncio.gather
            verification_tasks = [
                self._check_evidence_support(response, context_docs),
                self._detect_hallucination_risk(response, context_docs),
                self._check_domain_consistency(response, query, intent_result),
                self._verify_factual_claims(response, context_docs),
            ]

            # Exécution parallèle réelle
            results = await asyncio.gather(*verification_tasks, return_exceptions=True)

            # Traitement des résultats avec gestion d'erreurs
            evidence_score, evidence_details = self._safe_extract_result(
                results[0], (0.5, {})
            )
            hallucination_risk, hallucination_details = self._safe_extract_result(
                results[1], (0.5, {})
            )
            consistency_score, consistency_issues = self._safe_extract_result(
                results[2], (0.5, [])
            )
            factual_accuracy, factual_issues = self._safe_extract_result(
                results[3], (0.6, [])
            )

            # Agrégation intelligente des résultats
            violations, warnings, corrections = self._analyze_violations(
                evidence_score,
                hallucination_risk,
                consistency_score,
                consistency_issues,
                factual_issues,
            )

            # Calcul de confiance optimisé
            confidence = self._calculate_enhanced_confidence(
                evidence_score,
                hallucination_risk,
                consistency_score,
                factual_accuracy,
                len(violations),
                len(warnings),
            )

            # Décision finale basée sur seuils adaptatifs
            is_valid = self._make_adaptive_validation_decision(
                evidence_score,
                hallucination_risk,
                consistency_score,
                len(violations),
                len(warnings),
            )

            processing_time = time.time() - start_time

            result = GuardrailResult(
                is_valid=is_valid,
                confidence=confidence,
                violations=violations,
                warnings=warnings,
                evidence_support=evidence_score,
                hallucination_risk=hallucination_risk,
                correction_suggestions=corrections,
                processing_time=processing_time,
                metadata={
                    "verification_level": self.verification_level.value,
                    "evidence_details": evidence_details,
                    "hallucination_details": hallucination_details,
                    "consistency_score": consistency_score,
                    "factual_accuracy": factual_accuracy,
                    "consistency_issues": consistency_issues,
                    "parallel_execution": True,
                    "cache_used": False,
                    "thresholds_applied": self.validation_thresholds[
                        self.verification_level
                    ],
                },
            )

            # Mise en cache du résultat
            if self.enable_cache and cache_key:
                self._store_in_cache(cache_key, result)

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Erreur vérification guardrails: {e}")
            return GuardrailResult(
                is_valid=True,  # Fail-open par sécurité
                confidence=0.5,
                violations=[],
                warnings=[f"Erreur vérification: {str(e)}"],
                evidence_support=0.5,
                hallucination_risk=0.5,
                correction_suggestions=["Vérification manuelle recommandée"],
                processing_time=processing_time,
                metadata={"error": str(e), "fallback_mode": True},
            )

    def _safe_extract_result(self, result, default):
        """Extraction sécurisée des résultats avec gestion d'exceptions"""
        if isinstance(result, Exception):
            logger.warning(f"Erreur dans vérification parallèle: {result}")
            return default
        return result

    def _analyze_violations(
        self,
        evidence_score: float,
        hallucination_risk: float,
        consistency_score: float,
        consistency_issues: List[str],
        factual_issues: List[str],
    ) -> Tuple[List[str], List[str], List[str]]:
        """Analyse intelligente des violations avec seuils adaptatifs"""
        thresholds = self.validation_thresholds[self.verification_level]
        violations = []
        warnings = []
        corrections = []

        # Violations critiques
        if evidence_score < thresholds["evidence_min"]:
            violations.append(
                f"Support documentaire insuffisant ({evidence_score:.2f} < {thresholds['evidence_min']})"
            )
            corrections.append(
                "Reformuler en s'appuyant davantage sur les documents fournis"
            )

        if hallucination_risk > thresholds["hallucination_max"]:
            violations.append(
                f"Risque élevé d'hallucination détecté ({hallucination_risk:.2f} > {thresholds['hallucination_max']})"
            )
            corrections.append("Vérifier chaque affirmation avec les sources")

        if consistency_score < thresholds["consistency_min"]:
            violations.append(
                f"Incohérence avec le domaine aviculture ({consistency_score:.2f} < {thresholds['consistency_min']})"
            )
            corrections.append("Recentrer sur le contexte technique avicole")

        # Avertissements avec seuils gradués
        warning_threshold_evidence = thresholds["evidence_min"] + 0.2
        warning_threshold_hallucination = thresholds["hallucination_max"] - 0.2

        if (
            evidence_score < warning_threshold_evidence
            and evidence_score >= thresholds["evidence_min"]
        ):
            warnings.append(f"Support documentaire modéré ({evidence_score:.2f})")

        if (
            hallucination_risk > warning_threshold_hallucination
            and hallucination_risk <= thresholds["hallucination_max"]
        ):
            warnings.append(f"Éléments génériques détectés ({hallucination_risk:.2f})")

        # Intégration des problèmes spécifiques
        warnings.extend(consistency_issues[:3])  # Limiter le nombre d'avertissements
        warnings.extend(factual_issues[:3])

        return violations, warnings, corrections

    async def _check_evidence_support(
        self, response: str, context_docs: List[Dict]
    ) -> Tuple[float, Dict]:
        """Vérification optimisée du support documentaire"""
        try:
            if not context_docs:
                return 0.1, {"no_documents": True}

            # Extraction améliorée des affirmations factuelles
            claims = self._extract_enhanced_factual_claims(response)

            if not claims:
                return 0.5, {"no_factual_claims": True}

            # Vérification parallèle du support pour chaque affirmation
            support_tasks = [
                self._find_enhanced_claim_support(claim, context_docs)
                for claim in claims
            ]

            support_scores = await asyncio.gather(
                *support_tasks, return_exceptions=True
            )

            # Calcul du score d'évidence avec pondération
            valid_scores = [
                s
                for s in support_scores
                if not isinstance(s, Exception) and s is not None
            ]

            if not valid_scores:
                evidence_score = 0.3
            else:
                # Score pondéré: favorise les claims bien supportées
                strong_support = sum(1 for s in valid_scores if s > 0.7)
                moderate_support = sum(1 for s in valid_scores if 0.4 <= s <= 0.7)
                weak_support = sum(1 for s in valid_scores if s < 0.4)

                evidence_score = (
                    strong_support * 1.0 + moderate_support * 0.6 + weak_support * 0.2
                ) / len(valid_scores)

            # Bonus pour indicateurs explicites d'évidence
            evidence_indicators_found = sum(
                1
                for pattern in self.evidence_indicators
                if re.search(pattern, response.lower(), re.IGNORECASE)
            )

            if evidence_indicators_found > 0:
                evidence_score = min(
                    1.0, evidence_score + 0.1 * evidence_indicators_found
                )

            return evidence_score, {
                "total_claims": len(claims),
                "supported_claims": len([s for s in valid_scores if s > 0.6]),
                "evidence_indicators": evidence_indicators_found,
                "support_distribution": {
                    "strong": strong_support if valid_scores else 0,
                    "moderate": moderate_support if valid_scores else 0,
                    "weak": weak_support if valid_scores else 0,
                },
            }

        except Exception as e:
            logger.warning(f"Erreur vérification evidence: {e}")
            return 0.5, {"error": str(e)}

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

    async def _check_domain_consistency(
        self, response: str, query: str, intent_result
    ) -> Tuple[float, List[str]]:
        """Vérification améliorée de la cohérence domaine"""
        try:
            issues = []
            domain_score = 0.0
            response_lower = response.lower()

            # Analyse du vocabulaire métier par catégorie
            category_scores = {}
            total_domain_relevance = 0

            for category, keywords in self.domain_keywords.items():
                found_keywords = sum(
                    1 for keyword in keywords if keyword.lower() in response_lower
                )
                category_score = found_keywords / len(keywords) if keywords else 0
                category_scores[category] = category_score
                total_domain_relevance += found_keywords

            # Score basé sur la diversité et la densité du vocabulaire
            if total_domain_relevance > 0:
                # Bonus pour diversité des catégories
                active_categories = sum(
                    1 for score in category_scores.values() if score > 0
                )
                diversity_bonus = min(0.3, active_categories * 0.05)

                # Score de densité normalisé
                total_words = len(response.split())
                density_score = min(
                    1.0, total_domain_relevance / max(total_words * 0.1, 1)
                )

                domain_score = min(1.0, density_score + diversity_bonus)
            else:
                domain_score = 0.1  # Score minimal si aucun terme métier

            # Vérification de cohérence avec l'intention détectée
            if intent_result and hasattr(intent_result, "detected_entities"):
                entity_consistency = await self._check_entity_consistency(
                    response, intent_result.detected_entities
                )
                domain_score = (domain_score + entity_consistency) / 2

            # Détection d'incohérences flagrantes avec scoring sévère
            inconsistent_terms = {
                "technology": [
                    "crypto",
                    "bitcoin",
                    "blockchain",
                    "smartphone",
                    "app",
                    "software",
                ],
                "entertainment": [
                    "film",
                    "movie",
                    "cinema",
                    "netflix",
                    "game",
                    "gaming",
                ],
                "politics": [
                    "election",
                    "politics",
                    "vote",
                    "government",
                    "politician",
                ],
                "sports": ["football", "soccer", "basketball", "tennis", "sport"],
                "finance": ["trading", "forex", "investment", "stock", "market"],
            }

            for category, terms in inconsistent_terms.items():
                found_terms = [term for term in terms if term in response_lower]
                if found_terms:
                    issues.append(
                        f"Termes hors-domaine ({category}): {', '.join(found_terms)}"
                    )
                    domain_score *= 0.3  # Pénalité sévère

            # Vérification de la cohérence numérique (ordres de grandeur)
            numeric_coherence = self._check_numeric_coherence(response)
            if not numeric_coherence["is_coherent"]:
                issues.extend(numeric_coherence["issues"])
                domain_score *= 0.8

            return max(0.0, min(1.0, domain_score)), issues

        except Exception as e:
            logger.warning(f"Erreur vérification cohérence: {e}")
            return 0.5, [f"Erreur cohérence: {str(e)}"]

    async def _verify_factual_claims(
        self, response: str, context_docs: List[Dict]
    ) -> Tuple[float, List[str]]:
        """Vérification améliorée de la précision factuelle"""
        try:
            issues = []

            # Extraction des différents types de claims
            numeric_claims = self._extract_numeric_claims(response)
            qualitative_claims = self._extract_qualitative_claims(response)
            comparative_claims = self._extract_comparative_claims(response)

            total_claims = (
                len(numeric_claims) + len(qualitative_claims) + len(comparative_claims)
            )
            if total_claims == 0:
                return 0.8, []  # Pas de claims = pas d'erreurs

            verified_claims = 0

            # Vérification parallèle des claims numériques
            if numeric_claims:
                numeric_tasks = [
                    self._verify_specific_numeric_claim(claim, context_docs)
                    for claim in numeric_claims
                ]
                numeric_results = await asyncio.gather(
                    *numeric_tasks, return_exceptions=True
                )

                for i, result in enumerate(numeric_results):
                    if result is True:
                        verified_claims += 1
                    elif not isinstance(result, Exception):
                        issues.append(
                            f"Valeur numérique non vérifiée: {numeric_claims[i]}"
                        )

            # Vérification des claims qualitatifs
            for claim in qualitative_claims:
                if await self._verify_enhanced_qualitative_claim(
                    claim, response, context_docs
                ):
                    verified_claims += 1
                else:
                    issues.append(f"Affirmation qualitative non supportée: {claim}")

            # Vérification des comparaisons
            for claim in comparative_claims:
                if await self._verify_comparative_claim(claim, context_docs):
                    verified_claims += 1
                else:
                    issues.append(f"Comparaison non vérifiée: {claim}")

            # Calcul du score de précision avec pondération
            accuracy_score = verified_claims / total_claims if total_claims > 0 else 0.8

            # Bonus pour précision élevée
            if accuracy_score > 0.9:
                accuracy_score = min(1.0, accuracy_score + 0.05)

            return accuracy_score, issues

        except Exception as e:
            logger.warning(f"Erreur vérification factuelle: {e}")
            return 0.6, [f"Erreur vérification factuelle: {str(e)}"]

    # ===== MÉTHODES UTILITAIRES AMÉLIORÉES =====

    def _extract_enhanced_factual_claims(self, response: str) -> List[str]:
        """Extraction améliorée des affirmations factuelles"""
        claims = []

        # Segmentation en phrases avec préservation du contexte
        sentences = re.split(r"(?<=[.!?])\s+", response)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15:
                continue

            # Patterns pour identifier les affirmations factuelles
            factual_patterns = [
                r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|°C|kcal)",  # Valeurs numériques
                r"(?:poids|fcr|mortalité|ponte|croissance)\s+(?:de|est|atteint)",  # Métriques
                r"(?:recommandé|optimal|maximum|minimum|idéal)\s+(?:est|de)",  # Recommandations
                r"(?:lignée|espèce|phase|âge)\s+\w+",  # Classifications
                r"(?:ross|cobb|hubbard|isa)\s*\d*",  # Lignées génétiques
                r"(?:température|densité|ventilation)\s+(?:de|doit|optimal)",  # Paramètres techniques
            ]

            for pattern in factual_patterns:
                if re.search(pattern, sentence.lower(), re.IGNORECASE):
                    claims.append(sentence)
                    break

        return claims

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

    def _extract_key_elements(self, text: str) -> List[str]:
        """Extrait les éléments clés d'un texte (nombres, termes techniques, etc.)"""
        key_elements = []

        # Nombres avec unités
        numbers = re.findall(
            r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|°C|kcal)", text, re.IGNORECASE
        )
        key_elements.extend(numbers)

        # Termes techniques aviculture
        for category_terms in self.domain_keywords.values():
            for term in category_terms:
                if term.lower() in text.lower():
                    key_elements.append(term)

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

    # ===== MÉTHODES DE CACHE =====

    def _generate_cache_key(
        self, query: str, response: str, context_docs: List[Dict]
    ) -> str:
        """Génère une clé de cache unique"""
        try:
            # Combine les éléments essentiels
            content_hash = hashlib.md5(
                f"{query}|{response}|{len(context_docs)}|{self.verification_level.value}".encode()
            ).hexdigest()
            return f"guardrail_{content_hash}"
        except Exception:
            return None

    def _get_from_cache(self, cache_key: str) -> Optional[GuardrailResult]:
        """Récupère un résultat du cache"""
        if not self._verification_cache or not cache_key:
            return None
        return self._verification_cache.get(cache_key)

    def _store_in_cache(self, cache_key: str, result: GuardrailResult) -> None:
        """Stocke un résultat en cache avec gestion de la taille"""
        if not self._verification_cache or not cache_key:
            return

        # Gestion simple de la taille du cache
        if len(self._verification_cache) >= self._cache_max_size:
            # Supprime 20% des entrées les plus anciennes
            keys_to_remove = list(self._verification_cache.keys())[
                : self._cache_max_size // 5
            ]
            for key in keys_to_remove:
                del self._verification_cache[key]

        self._verification_cache[cache_key] = result

    # ===== MÉTHODES DE CALCUL AMÉLIORÉES =====

    def _calculate_enhanced_confidence(
        self,
        evidence_score: float,
        hallucination_risk: float,
        consistency_score: float,
        factual_accuracy: float,
        violation_count: int,
        warning_count: int,
    ) -> float:
        """Calcul de confiance amélioré avec pondération adaptive"""
        try:
            # Poids adaptatifs selon le niveau de vérification
            base_weights = {
                "evidence": 0.35,
                "hallucination": 0.25,
                "consistency": 0.20,
                "factual": 0.20,
            }

            # Ajustement des poids selon le niveau de vérification
            if self.verification_level == VerificationLevel.CRITICAL:
                base_weights["evidence"] = 0.4
                base_weights["factual"] = 0.25
            elif self.verification_level == VerificationLevel.MINIMAL:
                base_weights["consistency"] = 0.15
                base_weights["evidence"] = 0.3

            # Calcul de base
            confidence = (
                evidence_score * base_weights["evidence"]
                + (1 - hallucination_risk) * base_weights["hallucination"]
                + consistency_score * base_weights["consistency"]
                + factual_accuracy * base_weights["factual"]
            )

            # Pénalités pour violations et avertissements
            violation_penalty = violation_count * 0.2
            warning_penalty = warning_count * 0.05

            confidence = max(0.05, confidence - violation_penalty - warning_penalty)

            # Bonus pour performance exceptionnelle
            if violation_count == 0 and warning_count <= 1 and confidence > 0.8:
                confidence = min(0.95, confidence + 0.05)

            return confidence

        except Exception as e:
            logger.warning(f"Erreur calcul confiance: {e}")
            return 0.5

    def _make_adaptive_validation_decision(
        self,
        evidence_score: float,
        hallucination_risk: float,
        consistency_score: float,
        violation_count: int,
        warning_count: int,
    ) -> bool:
        """Décision de validation avec seuils adaptatifs"""
        try:
            thresholds = self.validation_thresholds[self.verification_level]

            # Vérification des seuils de base
            basic_checks = (
                evidence_score >= thresholds["evidence_min"]
                and hallucination_risk <= thresholds["hallucination_max"]
                and consistency_score >= thresholds["consistency_min"]
                and violation_count <= thresholds["max_violations"]
                and warning_count <= thresholds["max_warnings"]
            )

            # Pour les niveaux élevés, vérifications supplémentaires
            if self.verification_level in [
                VerificationLevel.STRICT,
                VerificationLevel.CRITICAL,
            ]:
                # Score composite minimal
                composite_score = (
                    evidence_score + (1 - hallucination_risk) + consistency_score
                ) / 3
                composite_threshold = (
                    0.6 if self.verification_level == VerificationLevel.STRICT else 0.75
                )

                return basic_checks and composite_score >= composite_threshold

            return basic_checks

        except Exception as e:
            logger.warning(f"Erreur décision validation: {e}")
            return True  # Fail-open par sécurité

    # ===== MÉTHODES UTILITAIRES SUPPLÉMENTAIRES =====

    def _extract_numeric_claims(self, response: str) -> List[str]:
        """Extrait les affirmations numériques"""
        patterns = [
            r"\d+[.,]?\d*\s*(?:g|kg|grammes?|kilogrammes?)",
            r"\d+[.,]?\d*\s*%",
            r"\d+[.,]?\d*\s*(?:j|jours?|semaines?)",
            r"FCR.*?\d+[.,]?\d*",
            r"\d+[.,]?\d*\s*(?:°C|degrés?)",
            r"\d+[.,]?\d*\s*(?:kcal|calories?)",
        ]

        claims = []
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            claims.extend(matches)

        return claims

    def _extract_qualitative_claims(self, response: str) -> List[str]:
        """Extrait les affirmations qualitatives"""
        qualitative_words = [
            "recommandé",
            "optimal",
            "idéal",
            "maximum",
            "minimum",
            "meilleur",
            "préférable",
            "conseillé",
            "éviter",
            "problématique",
            "excellent",
            "supérieur",
            "inférieur",
            "critique",
            "essentiel",
        ]

        claims = []
        for word in qualitative_words:
            pattern = rf"\b{re.escape(word)}\b[^.!?]*"
            matches = re.findall(pattern, response, re.IGNORECASE)
            claims.extend(matches)

        return claims

    def _extract_comparative_claims(self, response: str) -> List[str]:
        """Extrait les affirmations comparatives"""
        comparative_patterns = [
            r"\w+\s+(?:plus|moins)\s+\w+\s+que\s+\w+",
            r"\w+\s+(?:supérieur|inférieur)\s+à\s+\w+",
            r"\w+\s+(?:mieux|pire)\s+que\s+\w+",
            r"(?:comparé|par rapport)\s+à\s+\w+",
        ]

        claims = []
        for pattern in comparative_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            claims.extend(matches)

        return claims

    async def _check_entity_consistency(self, response: str, entities: Dict) -> float:
        """Vérifie la cohérence avec les entités détectées"""
        try:
            consistency_score = 1.0
            response_lower = response.lower()

            key_entities = ["line", "species", "phase", "age", "sex"]
            mentioned_entities = 0
            total_key_entities = 0

            for entity_type in key_entities:
                if entity_type in entities:
                    total_key_entities += 1
                    entity_value = str(entities[entity_type]).lower()

                    if entity_value in response_lower:
                        mentioned_entities += 1
                    else:
                        # Recherche de variantes ou synonymes
                        if self._find_entity_variants(entity_value, response_lower):
                            mentioned_entities += 0.5

            if total_key_entities > 0:
                consistency_score = mentioned_entities / total_key_entities

            return min(1.0, consistency_score)

        except Exception as e:
            logger.warning(f"Erreur vérification entités: {e}")
            return 0.5

    def _find_entity_variants(self, entity: str, text: str) -> bool:
        """Recherche de variantes d'entités"""
        variants_map = {
            "ross": ["ross 308", "ross308"],
            "cobb": ["cobb 500", "cobb500"],
            "male": ["mâle", "coq", "mâles"],
            "female": ["femelle", "poule", "femelles"],
            "chick": ["poussin", "poussins", "young"],
        }

        variants = variants_map.get(entity, [])
        return any(variant in text for variant in variants)

    def _check_numeric_coherence(self, response: str) -> Dict:
        """Vérifie la cohérence des valeurs numériques"""
        try:
            # Extraction des valeurs avec contexte
            weight_values = re.findall(
                r"(\d+[.,]?\d*)\s*(?:g|kg)", response, re.IGNORECASE
            )
            percentage_values = re.findall(
                r"(\d+[.,]?\d*)\s*%", response, re.IGNORECASE
            )
            re.findall(r"(\d+[.,]?\d*)\s*(?:j|jour)", response, re.IGNORECASE)

            issues = []
            is_coherent = True

            # Vérification des poids (ordres de grandeur)
            for weight_str in weight_values:
                try:
                    weight = float(weight_str.replace(",", "."))
                    if "kg" in response and weight > 10:  # Poids poulet > 10kg suspect
                        issues.append(
                            f"Poids suspect: {weight}kg (trop élevé pour volaille)"
                        )
                        is_coherent = False
                    elif "g" in response and weight > 10000:  # > 10kg en grammes
                        issues.append(f"Poids suspect: {weight}g (trop élevé)")
                        is_coherent = False
                except ValueError:
                    continue

            # Vérification des pourcentages
            for pct_str in percentage_values:
                try:
                    pct = float(pct_str.replace(",", "."))
                    if pct > 100:
                        issues.append(f"Pourcentage invalide: {pct}%")
                        is_coherent = False
                except ValueError:
                    continue

            return {"is_coherent": is_coherent, "issues": issues}

        except Exception as e:
            logger.warning(f"Erreur vérification cohérence numérique: {e}")
            return {"is_coherent": True, "issues": []}

    async def _verify_specific_numeric_claim(
        self, claim: str, context_docs: List[Dict]
    ) -> bool:
        """Vérification spécifique d'une claim numérique"""
        return await self._verify_enhanced_numeric_claim(claim, context_docs)

    async def _verify_enhanced_qualitative_claim(
        self, claim: str, response: str, context_docs: List[Dict]
    ) -> bool:
        """Vérification améliorée des claims qualitatives"""
        try:
            # Extraction du contexte autour du claim
            claim_context = self._extract_claim_context(claim, response)

            # Recherche de support dans les documents
            for doc in context_docs:
                content = doc.get("content", "").lower()

                # Recherche directe
                if claim.lower() in content:
                    return True

                # Recherche de contexte similaire
                context_words = set(claim_context.split())
                content_words = set(content.split())

                if context_words and content_words:
                    overlap = len(context_words.intersection(content_words))
                    similarity = overlap / len(context_words)

                    if similarity > 0.7:
                        return True

            return False

        except Exception as e:
            logger.warning(f"Erreur vérification claim qualitatif: {e}")
            return False

    async def _verify_comparative_claim(
        self, claim: str, context_docs: List[Dict]
    ) -> bool:
        """Vérification des claims comparatives"""
        try:
            # Extraction des éléments comparés
            comparison_elements = self._extract_comparison_elements(claim)

            if not comparison_elements:
                return False

            # Recherche de support pour la comparaison
            for doc in context_docs:
                content = doc.get("content", "").lower()

                # Vérifier si les éléments de comparaison sont présents
                elements_found = sum(
                    1 for elem in comparison_elements if elem.lower() in content
                )

                if (
                    elements_found >= len(comparison_elements) * 0.7
                ):  # 70% des éléments trouvés
                    return True

            return False

        except Exception as e:
            logger.warning(f"Erreur vérification comparaison: {e}")
            return False

    def _extract_claim_context(self, claim: str, response: str) -> str:
        """Extrait le contexte autour d'un claim"""
        try:
            claim_pos = response.lower().find(claim.lower())
            if claim_pos == -1:
                return claim

            # Contexte de ±50 caractères
            start = max(0, claim_pos - 50)
            end = min(len(response), claim_pos + len(claim) + 50)

            return response[start:end]

        except Exception:
            return claim

    def _extract_comparison_elements(self, claim: str) -> List[str]:
        """Extrait les éléments d'une comparaison"""
        try:
            # Patterns pour extraire les éléments comparés
            patterns = [
                r"(\w+)\s+(?:plus|moins)\s+(\w+)\s+que\s+(\w+)",
                r"(\w+)\s+(?:supérieur|inférieur)\s+à\s+(\w+)",
                r"(\w+)\s+(?:mieux|pire)\s+que\s+(\w+)",
            ]

            elements = []
            for pattern in patterns:
                matches = re.findall(pattern, claim, re.IGNORECASE)
                for match in matches:
                    elements.extend(match)

            return [elem.strip() for elem in elements if elem.strip()]

        except Exception:
            return []

    async def quick_verify(self, response: str, context_docs: List[Dict]) -> bool:
        """Vérification rapide optimisée"""
        try:
            if not context_docs:
                return False

            # Vérification basique parallélisée
            tasks = [
                self._quick_document_overlap(response, doc)
                for doc in context_docs[:5]  # Limite à 5 docs pour rapidité
            ]

            overlaps = await asyncio.gather(*tasks, return_exceptions=True)
            valid_overlaps = [o for o in overlaps if not isinstance(o, Exception)]

            if not valid_overlaps:
                return False

            # Au moins 30% des docs doivent avoir un overlap significatif
            significant_overlaps = sum(1 for overlap in valid_overlaps if overlap > 0.1)
            return (significant_overlaps / len(valid_overlaps)) >= 0.3

        except Exception as e:
            logger.warning(f"Erreur vérification rapide: {e}")
            return True  # Fail-open

    async def _quick_document_overlap(self, response: str, doc: Dict) -> float:
        """Calcul rapide de l'overlap avec un document"""
        try:
            content = doc.get("content", "")
            if not content:
                return 0.0

            response_words = set(self._normalize_text(response).split())
            content_words = set(self._normalize_text(content).split())

            if not response_words or not content_words:
                return 0.0

            overlap = len(response_words.intersection(content_words))
            return overlap / min(len(response_words), len(content_words))

        except Exception:
            return 0.0

    def get_guardrails_config(self) -> Dict[str, Any]:
        """Configuration complète des guardrails"""
        return {
            "version": "2.0_optimized",
            "verification_level": self.verification_level.value,
            "cache_enabled": self.enable_cache,
            "cache_size": (
                len(self._verification_cache) if self._verification_cache else 0
            ),
            "patterns": {
                "hallucination_patterns": len(self.hallucination_patterns),
                "evidence_indicators": len(self.evidence_indicators),
            },
            "domain_vocabulary": {
                category: len(keywords)
                for category, keywords in self.domain_keywords.items()
            },
            "validation_thresholds": self.validation_thresholds,
            "features": {
                "parallel_execution": True,
                "enhanced_claim_support": True,
                "contradiction_detection": True,
                "numeric_coherence_check": True,
                "entity_consistency_check": True,
                "multilingual_patterns": True,
                "adaptive_thresholds": True,
                "performance_cache": True,
            },
        }

    def clear_cache(self) -> int:
        """Vide le cache et retourne le nombre d'entrées supprimées"""
        if not self._verification_cache:
            return 0

        count = len(self._verification_cache)
        self._verification_cache.clear()
        return count

    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        if not self._verification_cache:
            return {"cache_disabled": True}

        return {
            "cache_enabled": True,
            "entries_count": len(self._verification_cache),
            "max_size": self._cache_max_size,
            "utilization": len(self._verification_cache) / self._cache_max_size,
        }


# Factory function améliorée
def create_response_guardrails(
    client,
    verification_level: str = "standard",
    enable_cache: bool = True,
    cache_size: int = 1000,
) -> AdvancedResponseGuardrails:
    """Crée un système de guardrails avec configuration optimisée"""
    level_map = {
        "minimal": VerificationLevel.MINIMAL,
        "standard": VerificationLevel.STANDARD,
        "strict": VerificationLevel.STRICT,
        "critical": VerificationLevel.CRITICAL,
    }

    level = level_map.get(verification_level.lower(), VerificationLevel.STANDARD)
    return AdvancedResponseGuardrails(client, level, enable_cache, cache_size)
