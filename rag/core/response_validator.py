# -*- coding: utf-8 -*-
"""
response_validator.py - Validation de la qualité des réponses générées
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
response_validator.py - Validation de la qualité des réponses générées
Version 1.0 - Détecte problèmes de qualité et calcule score
"""

import logging
import re
from typing import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Représente un problème de qualité détecté"""

    issue_type: str
    severity: str  # "critical" | "warning" | "info"
    description: str
    suggestion: str = ""


@dataclass
class ResponseQualityReport:
    """Rapport de qualité d'une réponse"""

    is_valid: bool
    quality_score: float  # 0.0 à 1.0
    issues: List[ValidationIssue]
    metrics: Dict[str, any]


class ResponseQualityValidator:
    """Valide la qualité des réponses générées par le LLM"""

    # Phrases interdites mentionnant les sources
    FORBIDDEN_SOURCE_MENTIONS = [
        "selon les documents",
        "d'après les documents",
        "d'après les sources",
        "les données fournies",
        "selon les données",
        "based on the documents",
        "according to the documents",
        "according to the data",
        "the provided documents",
        "the sources indicate",
    ]

    # Mots-clés nécessitant des valeurs chiffrées
    NUMERIC_KEYWORDS = {
        "fr": [
            "poids",
            "fcr",
            "conversion",
            "température",
            "densité",
            "mortalité",
            "ponte",
            "âge",
        ],
        "en": [
            "weight",
            "fcr",
            "conversion",
            "temperature",
            "density",
            "mortality",
            "production",
            "age",
        ],
    }

    def validate_response(
        self,
        response: str,
        query: str,
        domain: str = None,
        language: str = "fr",
        context_docs: List = None,
    ) -> ResponseQualityReport:
        """
        Valide une réponse générée

        Args:
            response: Réponse générée par le LLM
            query: Question originale
            domain: Domaine détecté (nutrition, health, etc.)
            language: Langue
            context_docs: Documents de contexte utilisés

        Returns:
            ResponseQualityReport avec score et issues
        """
        issues = []
        metrics = {}

        # Métriques de base
        metrics["response_length"] = len(response)
        metrics["response_words"] = len(response.split())
        metrics["query_words"] = len(query.split())

        # Check 1: Mentions de sources interdites
        source_issues = self._check_source_mentions(response)
        issues.extend(source_issues)

        # Check 2: Longueur appropriée
        length_issues = self._check_length(response, query)
        issues.extend(length_issues)

        # Check 3: Structure et formatage
        structure_issues = self._check_structure(response)
        issues.extend(structure_issues)

        # Check 4: Présence de valeurs chiffrées si nécessaire
        numeric_issues = self._check_numeric_values(response, query, language)
        issues.extend(numeric_issues)

        # Check 5: Recommandations actionnables
        recommendation_issues = self._check_recommendations(response, domain, language)
        issues.extend(recommendation_issues)

        # Check 6: Vérifier cohérence avec documents
        if context_docs:
            coherence_issues = self._check_coherence(response, context_docs)
            issues.extend(coherence_issues)

        # Calculer score de qualité
        quality_score = self._calculate_quality_score(issues, metrics)

        # Déterminer validité
        critical_issues = [i for i in issues if i.severity == "critical"]
        is_valid = len(critical_issues) == 0 and quality_score >= 0.6

        logger.info(
            f"Validation: score={quality_score:.2f}, issues={len(issues)}, "
            f"valid={is_valid}, domain={domain}"
        )

        return ResponseQualityReport(
            is_valid=is_valid,
            quality_score=quality_score,
            issues=issues,
            metrics=metrics,
        )

    def _check_source_mentions(self, response: str) -> List[ValidationIssue]:
        """Vérifie absence de mentions de sources"""
        issues = []
        response_lower = response.lower()

        for forbidden_phrase in self.FORBIDDEN_SOURCE_MENTIONS:
            if forbidden_phrase in response_lower:
                issues.append(
                    ValidationIssue(
                        issue_type="source_mention",
                        severity="critical",
                        description=f"Mention de source détectée: '{forbidden_phrase}'",
                        suggestion="Reformuler pour présenter l'information comme connaissance établie",
                    )
                )
                logger.warning(f"Source mention détectée: '{forbidden_phrase}'")
                break  # Une seule issue par type suffit

        return issues

    def _check_length(self, response: str, query: str) -> List[ValidationIssue]:
        """Vérifie longueur appropriée"""
        issues = []

        response_len = len(response)
        query_words = len(query.split())

        # Réponse trop courte pour question complexe
        if query_words > 10 and response_len < 200:
            issues.append(
                ValidationIssue(
                    issue_type="response_too_short",
                    severity="warning",
                    description=f"Réponse courte ({response_len} car) pour question complexe ({query_words} mots)",
                    suggestion="Développer davantage avec détails techniques et recommandations",
                )
            )

        # Réponse trop longue (> 1500 caractères)
        if response_len > 1500:
            issues.append(
                ValidationIssue(
                    issue_type="response_too_long",
                    severity="info",
                    description=f"Réponse très longue: {response_len} caractères",
                    suggestion="Peut-être synthétiser davantage pour plus de clarté",
                )
            )

        return issues

    def _check_structure(self, response: str) -> List[ValidationIssue]:
        """Vérifie structure et formatage"""
        issues = []

        # Absence de structure si réponse longue
        if len(response) > 500:
            has_structure = (
                "**" in response  # Titres en gras
                or "\n- " in response  # Listes à puces
                or "\n\n" in response  # Paragraphes séparés
            )

            if not has_structure:
                issues.append(
                    ValidationIssue(
                        issue_type="missing_structure",
                        severity="warning",
                        description="Réponse longue sans structure claire (titres, listes, paragraphes)",
                        suggestion="Ajouter titres en gras (**Titre**) et listes à puces pour lisibilité",
                    )
                )

        # Trop de formatage (listes numérotées interdites)
        numbered_lists = re.findall(r"\n\d+\.", response)
        if len(numbered_lists) > 3:
            issues.append(
                ValidationIssue(
                    issue_type="excessive_numbered_lists",
                    severity="warning",
                    description=f"Listes numérotées détectées ({len(numbered_lists)} items)",
                    suggestion="Utiliser puces (- ) au lieu de listes numérotées (1., 2., 3.)",
                )
            )

        return issues

    def _check_numeric_values(
        self, response: str, query: str, language: str
    ) -> List[ValidationIssue]:
        """Vérifie présence de valeurs chiffrées si approprié"""
        issues = []

        query_lower = query.lower()
        keywords = self.NUMERIC_KEYWORDS.get(language, self.NUMERIC_KEYWORDS["fr"])

        # Détecter si query demande des chiffres
        needs_numbers = any(kw in query_lower for kw in keywords)

        if needs_numbers:
            # Chercher des nombres dans la réponse
            numbers = re.findall(r"\d+(?:\.\d+)?", response)

            if len(numbers) == 0:
                issues.append(
                    ValidationIssue(
                        issue_type="missing_numeric_values",
                        severity="warning",
                        description="Question métrique sans valeurs chiffrées dans la réponse",
                        suggestion="Ajouter valeurs cibles, plages optimales ou standards de référence",
                    )
                )

        return issues

    def _check_recommendations(
        self, response: str, domain: str, language: str
    ) -> List[ValidationIssue]:
        """Vérifie présence de recommandations actionnables"""
        issues = []

        # Domains nécessitant recommandations
        recommendation_domains = ["nutrition", "health", "management", "environment"]

        if domain in recommendation_domains:
            response_lower = response.lower()

            # Mots-clés indiquant recommandation
            recommendation_keywords = {
                "fr": [
                    "recommande",
                    "recommandation",
                    "conseil",
                    "préconise",
                    "suggère",
                    "propose",
                ],
                "en": ["recommend", "recommendation", "advise", "suggest", "propose"],
            }

            keywords = recommendation_keywords.get(
                language, recommendation_keywords["fr"]
            )
            has_recommendation = any(kw in response_lower for kw in keywords)

            if not has_recommendation and len(response) > 300:
                issues.append(
                    ValidationIssue(
                        issue_type="missing_recommendations",
                        severity="info",
                        description=f"Domaine {domain} sans recommandations actionnables explicites",
                        suggestion="Ajouter section recommandations pratiques ou prochaines étapes",
                    )
                )

        return issues

    def _check_coherence(
        self, response: str, context_docs: List
    ) -> List[ValidationIssue]:
        """Vérifie cohérence avec documents sources avec analyse sémantique"""
        issues = []

        if not context_docs:
            return issues

        response_lower = response.lower()

        # Extraire entités clés des documents sources
        source_entities = {
            "breeds": set(),
            "metrics": set(),
            "ages": set(),
            "values": set(),
        }

        # Parser les documents sources pour extraire entités
        import re

        for doc in context_docs:
            if isinstance(doc, dict):
                content = doc.get("content", "").lower()
            else:
                content = str(doc).lower()

            # Extraire souches mentionnées
            breed_patterns = [
                r"\b(ross\s*\d+)\b",
                r"\b(cobb\s*\d+)\b",
                r"\b(hubbard\s*\d+)\b",
                r"\b(isa\s*\d+)\b",
            ]
            for pattern in breed_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                source_entities["breeds"].update(matches)

            # Extraire métriques mentionnées
            metrics = ["fcr", "ic", "poids", "weight", "gain", "mortalité", "mortality"]
            for metric in metrics:
                if metric in content:
                    source_entities["metrics"].add(metric)

            # Extraire âges mentionnés
            age_matches = re.findall(r"(\d+)\s+(?:jours?|days?|j\b)", content)
            source_entities["ages"].update(age_matches)

            # Extraire valeurs numériques importantes
            value_matches = re.findall(r"(\d+[.,]\d+)", content)
            source_entities["values"].update(value_matches)

        # Vérifier cohérence breed: si source mentionne breed spécifique, réponse devrait aussi
        if source_entities["breeds"]:
            response_has_breed = False
            for breed in source_entities["breeds"]:
                if breed in response_lower:
                    response_has_breed = True
                    break

            if not response_has_breed and len(source_entities["breeds"]) == 1:
                # Un seul breed dans sources mais pas dans réponse
                issues.append(
                    ValidationIssue(
                        issue_type="breed_mismatch",
                        severity="warning",
                        description=f"Documents sources mentionnent {list(source_entities['breeds'])[0]} mais la réponse ne le mentionne pas explicitement",
                        suggestion="Clarifier quelle souche est concernée dans la réponse",
                    )
                )

        # Vérifier cohérence des valeurs numériques
        # Si la réponse contient des valeurs, elles devraient être cohérentes avec les sources
        response_values = set(re.findall(r"(\d+[.,]\d+)", response))
        if response_values and source_entities["values"]:
            # Vérifier si au moins certaines valeurs de la réponse sont présentes dans les sources
            common_values = response_values.intersection(source_entities["values"])
            if len(common_values) == 0 and len(response_values) > 2:
                issues.append(
                    ValidationIssue(
                        issue_type="value_coherence",
                        severity="info",
                        description="Aucune valeur numérique de la réponse ne correspond exactement aux documents sources",
                        suggestion="Vérifier que les valeurs sont correctement calculées ou interpolées",
                    )
                )

        # Vérifier présence des métriques clés si la question les concerne
        if source_entities["metrics"]:
            metrics_in_response = sum(
                1 for m in source_entities["metrics"] if m in response_lower
            )
            if metrics_in_response == 0:
                issues.append(
                    ValidationIssue(
                        issue_type="missing_metrics",
                        severity="warning",
                        description="Documents sources contiennent des métriques spécifiques non mentionnées dans la réponse",
                        suggestion=f"Considérer mentionner: {', '.join(list(source_entities['metrics'])[:3])}",
                    )
                )

        # Analyse sémantique: vérifier contradiction flagrante
        # Exemple: si sources disent "FCR 1.5" et réponse dit "FCR 2.5" pour même contexte
        fcr_in_sources = re.findall(
            r"(?:fcr|ic)[:\s]+(\d+[.,]\d+)",
            " ".join(
                [
                    doc.get("content", "") if isinstance(doc, dict) else str(doc)
                    for doc in context_docs
                ]
            ),
            re.IGNORECASE,
        )

        fcr_in_response = re.findall(
            r"(?:fcr|ic)[:\s]+(\d+[.,]\d+)", response, re.IGNORECASE
        )

        if fcr_in_sources and fcr_in_response:
            # Convertir en float et comparer
            try:
                source_fcr = float(fcr_in_sources[0].replace(",", "."))
                response_fcr = float(fcr_in_response[0].replace(",", "."))

                # Si différence > 20%, signaler
                if abs(response_fcr - source_fcr) / source_fcr > 0.2:
                    issues.append(
                        ValidationIssue(
                            issue_type="fcr_discrepancy",
                            severity="warning",
                            description=f"FCR dans réponse ({response_fcr}) diffère significativement des sources ({source_fcr})",
                            suggestion="Vérifier calculs ou clarifier contexte différent",
                        )
                    )
            except (ValueError, ZeroDivisionError):
                pass  # Skip si conversion échoue

        return issues

    def _calculate_quality_score(
        self, issues: List[ValidationIssue], metrics: Dict
    ) -> float:
        """
        Calcule score de qualité (0.0 à 1.0)

        Pénalités:
        - Critical: -0.3 par issue
        - Warning: -0.15 par issue
        - Info: -0.05 par issue
        """
        score = 1.0

        for issue in issues:
            if issue.severity == "critical":
                score -= 0.3
            elif issue.severity == "warning":
                score -= 0.15
            elif issue.severity == "info":
                score -= 0.05

        # Bonus si bonne longueur
        response_len = metrics.get("response_length", 0)
        if 300 <= response_len <= 800:
            score += 0.05

        return max(0.0, min(1.0, score))


# Factory singleton
_validator_instance = None


def get_response_validator() -> ResponseQualityValidator:
    """Récupère instance singleton du validator"""
    global _validator_instance

    if _validator_instance is None:
        _validator_instance = ResponseQualityValidator()

    return _validator_instance
