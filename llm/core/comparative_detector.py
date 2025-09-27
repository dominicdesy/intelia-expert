# -*- coding: utf-8 -*-
"""
comparative_detector.py - Détection de requêtes comparatives
Extrait du query_preprocessor.py pour modularité
"""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ComparativeQueryDetector:
    """Détecte les requêtes nécessitant des comparaisons ou calculs mathématiques"""

    COMPARATIVE_PATTERNS = {
        "difference": [
            r"(?:quelle|quel)\s+(?:est|sont)\s+la\s+diff[ée]rence",
            r"diff[ée]rence\s+(?:de|entre|d\')",
            r"compar(?:er|aison)",
            r"écart\s+entre",
        ],
        "versus": [
            r"(?:versus|vs|contre)",
            r"entre\s+(?:un|une)\s+\w+\s+et\s+(?:un|une)",
            r"par\s+rapport\s+[aà]",
        ],
        "ratio": [
            r"rapport\s+entre",
            r"ratio\s+(?:de|entre)",
            r"taux\s+(?:de|entre)",
        ],
        "evolution": [
            r"[ée]volution",
            r"progression",
            r"variation\s+(?:de|entre)",
            r"changement\s+entre",
        ],
        "average": [
            r"moyenne\s+(?:de|entre)",
            r"en\s+moyenne",
        ],
    }

    SEX_PATTERNS = {
        "male": r"m[aâ]le?s?",
        "female": r"femelles?",
    }

    AGE_PATTERN = r"(\d+)\s*jours?"
    BREED_PATTERN = r"((?:Cobb|Ross|Hubbard|Arbor\s*Acres)\s*\d+)"

    def detect(self, query: str) -> Dict[str, Any]:
        """
        Détecte si la requête demande une comparaison

        Returns:
            {
                'is_comparative': bool,
                'type': str,
                'entities': List[Dict],
                'requires_multiple_queries': bool,
                'operation': str
            }
        """
        query_lower = query.lower()

        # 1. Détection du type de comparaison
        comparison_type = None
        for comp_type, patterns in self.COMPARATIVE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    comparison_type = comp_type
                    break
            if comparison_type:
                break

        if not comparison_type:
            return {
                "is_comparative": False,
                "type": None,
                "entities": [],
                "requires_multiple_queries": False,
            }

        # 2. Extraction des entités à comparer
        entities_to_compare = self._extract_comparison_entities(query_lower)

        # 3. Déterminer l'opération mathématique
        operation = self._determine_operation(comparison_type)

        return {
            "is_comparative": True,
            "type": comparison_type,
            "entities": entities_to_compare,
            "requires_multiple_queries": len(entities_to_compare) > 0,
            "operation": operation,
            "entity_count": len(entities_to_compare),
        }

    def _extract_comparison_entities(self, query: str) -> List[Dict[str, Any]]:
        """Extrait les entités qui doivent être comparées"""
        entities = []

        # 1. Détection mâle vs femelle
        has_male = re.search(self.SEX_PATTERNS["male"], query)
        has_female = re.search(self.SEX_PATTERNS["female"], query)

        if has_male and has_female:
            entities.append(
                {
                    "dimension": "sex",
                    "values": ["male", "female"],
                    "comparison_axis": "sex",
                }
            )
            logger.debug("Détection comparaison sexe: male vs female")

        # 2. Détection de différents âges
        ages = re.findall(self.AGE_PATTERN, query)
        unique_ages = sorted(set(int(age) for age in ages))

        if len(unique_ages) > 1:
            entities.append(
                {
                    "dimension": "age_days",
                    "values": unique_ages,
                    "comparison_axis": "age",
                }
            )
            logger.debug(f"Détection comparaison âges: {unique_ages}")
        elif len(unique_ages) == 1:
            logger.debug(f"Un seul âge détecté: {unique_ages[0]} jours")

        # 3. Détection de différentes souches
        breeds = re.findall(self.BREED_PATTERN, query, re.IGNORECASE)
        unique_breeds = sorted(set(breeds), key=lambda x: breeds.index(x))

        if len(unique_breeds) > 1:
            entities.append(
                {
                    "dimension": "breed",
                    "values": unique_breeds,
                    "comparison_axis": "breed",
                }
            )
            logger.debug(f"Détection comparaison souches: {unique_breeds}")

        return entities

    def _determine_operation(self, comparison_type: str) -> str:
        """Détermine l'opération mathématique à effectuer"""
        operation_map = {
            "difference": "subtract",
            "versus": "subtract",
            "ratio": "divide",
            "evolution": "subtract",
            "average": "average",
        }
        return operation_map.get(comparison_type, "subtract")


# Test unitaire
if __name__ == "__main__":
    detector = ComparativeQueryDetector()

    test_queries = [
        "Quelle est la différence de FCR entre un Cobb 500 mâle et femelle de 17 jours ?",
        "Compare le poids vif mâle vs femelle à 21 jours",
        "FCR du Cobb 500 mâle à 17 jours",
    ]

    for query in test_queries:
        result = detector.detect(query)
        print(f"\nQuery: {query}")
        print(f"Comparative: {result['is_comparative']}")
        if result["is_comparative"]:
            print(f"Type: {result['type']}")
            print(f"Entities: {result['entities']}")
