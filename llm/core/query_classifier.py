# -*- coding: utf-8 -*-
"""
query_classifier.py - Classificateur de requêtes unifié
Fusionne: comparative_detector + rag_engine_query_classifier + partie de query_preprocessor
Version 1.1 - Ajout des types METRIC, GENERAL, RECOMMENDATION manquants
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types de requêtes supportés"""

    STANDARD = "standard"
    METRIC = "metric"  # ← AJOUTÉ pour requêtes de métriques spécifiques
    GENERAL = "general"  # ← AJOUTÉ pour requêtes générales/documentaires
    COMPARATIVE = "comparative"
    TEMPORAL_RANGE = "temporal_range"
    RECOMMENDATION = "recommendation"  # ← AJOUTÉ pour recommandations/suggestions
    OPTIMIZATION = "optimization"
    CALCULATION = "calculation"
    ECONOMIC = "economic"
    DIAGNOSTIC = "diagnostic"


class ComparisonType(Enum):
    """Types de comparaisons"""

    DIFFERENCE = "difference"
    VERSUS = "versus"
    RATIO = "ratio"
    EVOLUTION = "evolution"
    AVERAGE = "average"
    TEMPORAL = "temporal"


@dataclass
class ClassificationResult:
    """Résultat complet de classification"""

    query_type: QueryType
    confidence: float

    # Informations comparatives
    is_comparative: bool = False
    comparison_type: Optional[ComparisonType] = None
    requires_multiple_queries: bool = False
    entities_to_compare: List[Dict] = field(default_factory=list)

    # Informations temporelles
    temporal_range: Optional[Tuple[int, int]] = None
    is_temporal_range: bool = False

    # Métadonnées de classification
    matched_patterns: List[str] = field(default_factory=list)
    detection_method: str = "pattern_matching"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "query_type": self.query_type.value,
            "confidence": self.confidence,
            "is_comparative": self.is_comparative,
            "comparison_type": (
                self.comparison_type.value if self.comparison_type else None
            ),
            "requires_multiple_queries": self.requires_multiple_queries,
            "temporal_range": self.temporal_range,
            "is_temporal_range": self.is_temporal_range,
            "matched_patterns": self.matched_patterns,
        }


class UnifiedQueryClassifier:
    """
    Classificateur unifié remplaçant 3 modules:
    - comparative_detector.py
    - rag_engine_query_classifier.py
    - Partie classification de query_preprocessor.py
    """

    # ========================================================================
    # PATTERNS COMPARATIFS (depuis comparative_detector.py)
    # ========================================================================

    COMPARATIVE_PATTERNS = {
        ComparisonType.DIFFERENCE: [
            r"(?:quelle|quel)\s+(?:est|sont)\s+la\s+diff[ée]rence",
            r"diff[ée]rence\s+(?:de|entre|d\')",
            r"compar(?:er|aison)",
            r"écart\s+entre",
            r"comparer\s+(?:le|la|les)",
        ],
        ComparisonType.VERSUS: [
            r"(?:versus|vs\.?|contre)",
            r"entre\s+(?:un|une)\s+\w+\s+et\s+(?:un|une)",
            r"par\s+rapport\s+[aà]",
            r"\bvs\b",
            r"face\s+[aà]",
        ],
        ComparisonType.RATIO: [
            r"rapport\s+entre",
            r"ratio\s+(?:de|entre)",
            r"taux\s+(?:de|entre)",
            r"pourcentage\s+(?:de|entre)",
        ],
        ComparisonType.EVOLUTION: [
            r"[ée]volution",
            r"progression",
            r"variation\s+(?:de|entre)",
            r"changement\s+entre",
            r"tendance",
        ],
        ComparisonType.AVERAGE: [
            r"moyenne\s+(?:de|entre)",
            r"en\s+moyenne",
            r"moyen(?:ne)?",
        ],
        ComparisonType.TEMPORAL: [
            r"entre\s+(\d+)\s+et\s+(\d+)\s+jours?",
            r"diff[ée]rence.*(\d+).*(\d+)\s+jours?",
            r"[ée]volution.*(\d+).*(\d+)",
            r"de\s+(\d+)\s+[aà]\s+(\d+)\s+jours?",
        ],
    }

    # ========================================================================
    # PATTERNS TEMPORELS (plages d'âge)
    # ========================================================================

    TEMPORAL_RANGE_PATTERNS = [
        r"entre\s+(\d+)\s+et\s+(\d+)\s+(?:jours?|j)\b",
        r"de\s+(\d+)\s+[aà]\s+(\d+)\s+(?:jours?|j)?\b",
        r"(\d+)\s*-\s*(\d+)\s+jours?",
        r"(\d+)\s+[aà]\s+(\d+)\s+jours?",
        r"plage\s+(\d+)\s*-\s*(\d+)",
    ]

    # ========================================================================
    # PATTERNS RECOMMENDATION (NOUVEAU)
    # ========================================================================

    RECOMMENDATION_PATTERNS = [
        r"recommand\w*",
        r"sugg[ée]r\w*",
        r"conseil\w*",
        r"que\s+me\s+(?:conseillez?|recommandez?)",
        r"(?:quel(?:le)?|quoi)\s+(?:choisir|utiliser|faire)",
        r"mieux\s+de\b",
        r"devr(?:ais?|ions?)\b",
    ]

    # ========================================================================
    # PATTERNS METRIC (NOUVEAU)
    # ========================================================================

    METRIC_PATTERNS = [
        r"(?:quel(?:le)?)\s+(?:est|sont)\s+(?:le|la|les)\s+(?:poids|fcr|ic|mortalité|gain)",
        r"valeur\s+(?:de|du|de\s+la)",
        r"donn[ée]es?\s+(?:de|pour)",
        r"chiffres?\s+(?:de|pour)",
        r"m[ée]trique",
        r"performance",
    ]

    # ========================================================================
    # PATTERNS GENERAL (NOUVEAU)
    # ========================================================================

    GENERAL_PATTERNS = [
        r"(?:comment|pourquoi|qu['']est-ce\s+que)",
        r"expliqu\w*",
        r"d[ée]cri\w*",
        r"d[ée]finition",
        r"c['']est\s+quoi",
        r"qu['']est-ce",
        r"guide",
        r"information",
    ]

    # ========================================================================
    # PATTERNS OPTIMISATION
    # ========================================================================

    OPTIMIZATION_PATTERNS = [
        r"optimal\w*",
        r"id[ée]al\w*",
        r"meilleur\w*",
        r"choisir",
        r"quel(?:le)?\s+(?:est|sont)\s+(?:le|la)\s+meilleur",
        r"perfection",
        r"maxim(?:is|al)\w*",
        r"minim(?:is|al)\w*",
    ]

    # ========================================================================
    # PATTERNS CALCUL
    # ========================================================================

    CALCULATION_PATTERNS = [
        r"\bcalcul\w*\b",
        r"\bprojection\b",
        r"\bprojette\w*\b",
        r"\bestim\w*\b",
        r"\btotal\w*\b",
        r"\bsomme\b",
        r"\bcombien\b",
        r"[0-9,]+\s+(?:poulets?|oiseaux)",  # Calculs de troupeau
    ]

    # ========================================================================
    # PATTERNS ÉCONOMIQUES
    # ========================================================================

    ECONOMIC_PATTERNS = [
        r"co[ûu]t",
        r"prix",
        r"rentabilit[ée]",
        r"marge",
        r"profit",
        r"€|\\$|dollar|euro",
        r"[ée]conomique",
        r"financier",
    ]

    # ========================================================================
    # PATTERNS DIAGNOSTICS
    # ========================================================================

    DIAGNOSTIC_PATTERNS = [
        r"maladie",
        r"symptôme",
        r"diagnostic",
        r"traitement",
        r"pathologie",
        r"infection",
        r"probl[èe]me\s+de\s+sant[ée]",
    ]

    def __init__(self):
        """Initialise le classificateur et compile les patterns"""
        self._compile_all_patterns()
        logger.info("UnifiedQueryClassifier initialisé avec types étendus")

    def _compile_all_patterns(self):
        """Compile tous les patterns regex pour performance"""

        # Comparatifs
        self.compiled_comparative = {}
        for comp_type, patterns in self.COMPARATIVE_PATTERNS.items():
            self.compiled_comparative[comp_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

        # Temporels
        self.compiled_temporal = [
            re.compile(p, re.IGNORECASE) for p in self.TEMPORAL_RANGE_PATTERNS
        ]

        # NOUVEAUX: Recommendation, Metric, General
        self.compiled_recommendation = [
            re.compile(p, re.IGNORECASE) for p in self.RECOMMENDATION_PATTERNS
        ]

        self.compiled_metric = [
            re.compile(p, re.IGNORECASE) for p in self.METRIC_PATTERNS
        ]

        self.compiled_general = [
            re.compile(p, re.IGNORECASE) for p in self.GENERAL_PATTERNS
        ]

        # Optimisation
        self.compiled_optimization = [
            re.compile(p, re.IGNORECASE) for p in self.OPTIMIZATION_PATTERNS
        ]

        # Calcul
        self.compiled_calculation = [
            re.compile(p, re.IGNORECASE) for p in self.CALCULATION_PATTERNS
        ]

        # Économiques
        self.compiled_economic = [
            re.compile(p, re.IGNORECASE) for p in self.ECONOMIC_PATTERNS
        ]

        # Diagnostics
        self.compiled_diagnostic = [
            re.compile(p, re.IGNORECASE) for p in self.DIAGNOSTIC_PATTERNS
        ]

        logger.debug(
            f"Patterns compilés: {len(self.compiled_comparative)} types comparatifs, "
            f"{len(self.compiled_temporal)} temporels, "
            f"{len(self.compiled_recommendation)} recommendation, "
            f"{len(self.compiled_metric)} metric, "
            f"{len(self.compiled_general)} general"
        )

    def classify(self, query: str) -> ClassificationResult:
        """
        Classification complète de la requête

        Args:
            query: Requête utilisateur

        Returns:
            ClassificationResult avec type et métadonnées complètes
        """
        query_lower = query.lower()
        matched_patterns = []

        # PRIORITÉ 1: Détection COMPARATIVE
        comparative_result = self._detect_comparative(query_lower)
        if comparative_result["is_comparative"]:
            matched_patterns.extend(comparative_result["matched_patterns"])

            return ClassificationResult(
                query_type=QueryType.COMPARATIVE,
                confidence=0.92,
                is_comparative=True,
                comparison_type=comparative_result["type"],
                requires_multiple_queries=True,
                entities_to_compare=comparative_result.get("entities", []),
                matched_patterns=matched_patterns,
                detection_method="comparative_patterns",
            )

        # PRIORITÉ 2: Détection TEMPORAL RANGE
        temporal_range = self._detect_temporal_range(query_lower)
        if temporal_range:
            matched_patterns.append(f"temporal_range_{temporal_range}")

            return ClassificationResult(
                query_type=QueryType.TEMPORAL_RANGE,
                confidence=0.95,
                is_comparative=False,
                temporal_range=temporal_range,
                is_temporal_range=True,
                matched_patterns=matched_patterns,
                detection_method="temporal_patterns",
            )

        # PRIORITÉ 3: Détection ECONOMIC
        if self._matches_patterns(query_lower, self.compiled_economic):
            matched_patterns.append("economic")

            return ClassificationResult(
                query_type=QueryType.ECONOMIC,
                confidence=0.88,
                is_comparative=False,
                matched_patterns=matched_patterns,
                detection_method="economic_patterns",
            )

        # PRIORITÉ 4: Détection DIAGNOSTIC
        if self._matches_patterns(query_lower, self.compiled_diagnostic):
            matched_patterns.append("diagnostic")

            return ClassificationResult(
                query_type=QueryType.DIAGNOSTIC,
                confidence=0.85,
                is_comparative=False,
                matched_patterns=matched_patterns,
                detection_method="diagnostic_patterns",
            )

        # PRIORITÉ 5: Détection RECOMMENDATION (NOUVEAU)
        if self._matches_patterns(query_lower, self.compiled_recommendation):
            matched_patterns.append("recommendation")

            return ClassificationResult(
                query_type=QueryType.RECOMMENDATION,
                confidence=0.83,
                is_comparative=False,
                matched_patterns=matched_patterns,
                detection_method="recommendation_patterns",
            )

        # PRIORITÉ 6: Détection OPTIMIZATION
        if self._matches_patterns(query_lower, self.compiled_optimization):
            matched_patterns.append("optimization")

            return ClassificationResult(
                query_type=QueryType.OPTIMIZATION,
                confidence=0.82,
                is_comparative=False,
                matched_patterns=matched_patterns,
                detection_method="optimization_patterns",
            )

        # PRIORITÉ 7: Détection CALCULATION
        if self._matches_patterns(query_lower, self.compiled_calculation):
            matched_patterns.append("calculation")

            return ClassificationResult(
                query_type=QueryType.CALCULATION,
                confidence=0.80,
                is_comparative=False,
                matched_patterns=matched_patterns,
                detection_method="calculation_patterns",
            )

        # PRIORITÉ 8: Détection METRIC (NOUVEAU)
        if self._matches_patterns(query_lower, self.compiled_metric):
            matched_patterns.append("metric")

            return ClassificationResult(
                query_type=QueryType.METRIC,
                confidence=0.78,
                is_comparative=False,
                matched_patterns=matched_patterns,
                detection_method="metric_patterns",
            )

        # PRIORITÉ 9: Détection GENERAL (NOUVEAU)
        if self._matches_patterns(query_lower, self.compiled_general):
            matched_patterns.append("general")

            return ClassificationResult(
                query_type=QueryType.GENERAL,
                confidence=0.75,
                is_comparative=False,
                matched_patterns=matched_patterns,
                detection_method="general_patterns",
            )

        # PAR DÉFAUT: STANDARD
        return ClassificationResult(
            query_type=QueryType.STANDARD,
            confidence=0.70,
            is_comparative=False,
            matched_patterns=matched_patterns,
            detection_method="default",
        )

    def _detect_comparative(self, query: str) -> Dict[str, Any]:
        """
        Détecte si la requête est comparative

        Returns:
            Dict avec 'is_comparative', 'type', 'entities', 'matched_patterns'
        """
        for comp_type, patterns in self.compiled_comparative.items():
            for pattern in patterns:
                match = pattern.search(query)
                if match:
                    return {
                        "is_comparative": True,
                        "type": comp_type,
                        "entities": self._extract_comparison_entities(query, comp_type),
                        "matched_patterns": [f"comparative_{comp_type.value}"],
                        "match_text": match.group(0),
                    }

        return {
            "is_comparative": False,
            "type": None,
            "entities": [],
            "matched_patterns": [],
        }

    def _detect_temporal_range(self, query: str) -> Optional[Tuple[int, int]]:
        """
        Détecte une plage temporelle (ex: "entre 21 et 35 jours")

        Returns:
            Tuple (age_start, age_end) ou None
        """
        for pattern in self.compiled_temporal:
            match = pattern.search(query)
            if match:
                try:
                    age1 = int(match.group(1))
                    age2 = int(match.group(2))

                    # Validation plausibilité
                    if 0 <= age1 <= 100 and 0 <= age2 <= 100 and age1 < age2:
                        return (age1, age2)

                except (ValueError, IndexError) as e:
                    logger.debug(f"Erreur parsing temporal range: {e}")
                    continue

        return None

    def _matches_patterns(self, query: str, compiled_patterns: List) -> bool:
        """Vérifie si la requête matche au moins un pattern de la liste"""
        return any(pattern.search(query) for pattern in compiled_patterns)

    def _extract_comparison_entities(
        self, query: str, comparison_type: ComparisonType
    ) -> List[Dict]:
        """
        Extrait les entités à comparer depuis la requête

        Args:
            query: Requête utilisateur
            comparison_type: Type de comparaison détecté

        Returns:
            Liste de dictionnaires d'entités à comparer
        """
        entities = []

        # Détection de comparaison MALE vs FEMALE
        if self._is_sex_comparison(query):
            entities.append({"sex": "male", "_comparison_label": "mâle"})
            entities.append({"sex": "female", "_comparison_label": "femelle"})
            logger.debug("Détection comparaison sexe: male vs female")
            return entities

        # Détection de comparaison BREEDS
        breeds_found = self._extract_multiple_breeds(query)
        if len(breeds_found) >= 2:
            for breed in breeds_found:
                entities.append(
                    {
                        "breed": breed,
                        "_comparison_label": breed.upper(),
                    }
                )
            logger.debug(f"Détection comparaison breeds: {breeds_found}")
            return entities

        # Détection de comparaison AGES (temporel)
        if comparison_type == ComparisonType.TEMPORAL:
            temporal_range = self._detect_temporal_range(query)
            if temporal_range:
                age1, age2 = temporal_range
                entities.append(
                    {
                        "age_days": age1,
                        "_comparison_label": f"{age1}j",
                    }
                )
                entities.append(
                    {
                        "age_days": age2,
                        "_comparison_label": f"{age2}j",
                    }
                )
                logger.debug(f"Détection comparaison temporelle: {age1}j vs {age2}j")
                return entities

        # Si aucune entité spécifique détectée, retour vide
        # Le handler devra extraire les entités de manière plus avancée
        return entities

    def _is_sex_comparison(self, query: str) -> bool:
        """Détecte si la requête compare mâle et femelle"""
        has_male = bool(re.search(r"\bm[aâ]les?\b|\bmale\b", query, re.IGNORECASE))
        has_female = bool(re.search(r"\bfemelles?\b|\bfemale\b", query, re.IGNORECASE))

        # Mots de comparaison
        has_comparison_word = bool(
            re.search(
                r"\bet\b|\bvs\b|\bversus\b|\bentre\b|\bcompare", query, re.IGNORECASE
            )
        )

        return has_male and has_female and has_comparison_word

    def _extract_multiple_breeds(self, query: str) -> List[str]:
        """Extrait potentiellement plusieurs breeds depuis une requête"""
        breeds_found = []

        breed_patterns = {
            "cobb500": r"cobb\s*500",
            "ross308": r"ross\s*308",
            "hubbard": r"hubbard",
        }

        for breed_name, pattern in breed_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                breeds_found.append(breed_name)

        return breeds_found

    def get_classification_details(self, result: ClassificationResult) -> str:
        """
        Retourne une description textuelle de la classification

        Args:
            result: ClassificationResult

        Returns:
            Description lisible de la classification
        """
        details = [
            f"Type: {result.query_type.value}",
            f"Confiance: {result.confidence:.2%}",
        ]

        if result.is_comparative:
            details.append(f"Comparatif: {result.comparison_type.value}")
            details.append(f"Entités: {len(result.entities_to_compare)}")

        if result.is_temporal_range:
            details.append(
                f"Plage: {result.temporal_range[0]}-{result.temporal_range[1]}j"
            )

        if result.matched_patterns:
            details.append(f"Patterns: {', '.join(result.matched_patterns)}")

        return " | ".join(details)


# Factory function
def create_query_classifier() -> UnifiedQueryClassifier:
    """Factory pour créer une instance UnifiedQueryClassifier"""
    return UnifiedQueryClassifier()


# Tests unitaires
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    classifier = UnifiedQueryClassifier()

    test_queries = [
        ("Quel est le poids d'un Cobb 500 mâle à 21 jours ?", QueryType.METRIC),
        (
            "Quelle est la différence de FCR entre mâle et femelle ?",
            QueryType.COMPARATIVE,
        ),
        ("Évolution du poids entre 0 et 42 jours", QueryType.TEMPORAL_RANGE),
        (
            "Quelle est la meilleure souche pour l'efficacité alimentaire ?",
            QueryType.OPTIMIZATION,
        ),
        (
            "Que me recommandez-vous comme alimentation ?",
            QueryType.RECOMMENDATION,
        ),
        ("Calculer le poids total de 10000 poulets à 35 jours", QueryType.CALCULATION),
        ("Quel est le coût d'alimentation pour un troupeau ?", QueryType.ECONOMIC),
        ("Symptômes de la maladie de Newcastle", QueryType.DIAGNOSTIC),
        ("Comment améliorer le FCR ?", QueryType.GENERAL),
    ]

    print("=== TESTS QUERY CLASSIFIER (VERSION ÉTENDUE) ===\n")

    for query, expected_type in test_queries:
        result = classifier.classify(query)
        status = "✅" if result.query_type == expected_type else "❌"

        print(f"{status} Query: {query}")
        print(f"   Attendu: {expected_type.value}")
        print(f"   Obtenu: {result.query_type.value}")
        print(f"   Détails: {classifier.get_classification_details(result)}")
        print()
