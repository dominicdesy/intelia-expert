# -*- coding: utf-8 -*-
"""
postgresql_query_builder.py - Construction de requêtes SQL pour PostgreSQL
Version CORRIGÉE avec normalisation robuste des noms de souches
"""

import logging
import re
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)


class PostgreSQLQueryBuilder:
    """Construit les requêtes SQL pour la recherche de métriques avec normalisation robuste"""

    def __init__(self, query_normalizer):
        """
        Args:
            query_normalizer: Instance de SQLQueryNormalizer pour normalisation
        """
        self.query_normalizer = query_normalizer

    def build_sex_aware_sql_query(
        self,
        query: str,
        entities: Dict[str, str] = None,
        top_k: int = 10,
        strict_sex_match: bool = False,
    ) -> Tuple[str, List]:
        """
        Construit une requête SQL avec logique de sexe adaptative et normalisation robuste

        Args:
            query: Requête utilisateur
            entities: Entités extraites (breed, sex, age_days, etc.)
            top_k: Nombre de résultats
            strict_sex_match: Si True, ne cherche que le sexe exact (pas de fallback as_hatched)

        Returns:
            Tuple[str, List]: (requête SQL, paramètres)
        """
        base_query = """
        SELECT 
            c.company_name,
            b.breed_name,
            s.strain_name,
            s.species,
            m.metric_name,
            m.value_numeric,
            m.value_text,
            m.unit,
            m.age_min,
            m.age_max,
            m.sheet_name,
            dc.category_name,
            d.sex,
            d.housing_system,
            d.data_type,
            m.metadata
        FROM companies c
        JOIN breeds b ON c.id = b.company_id
        JOIN strains s ON b.id = s.breed_id  
        JOIN documents d ON s.id = d.strain_id
        JOIN metrics m ON d.id = m.document_id
        JOIN data_categories dc ON m.category_id = dc.id
        WHERE 1=1
        """

        params = []
        conditions = []
        param_count = 0

        # Extraction du sexe depuis query et entities
        sex_from_query = self.query_normalizer.extract_sex_from_query(query)
        sex_from_entities = entities.get("sex") if entities else None
        sex_specified = entities.get("sex_specified") == "true" if entities else False

        target_sex = sex_from_entities or sex_from_query
        actual_sex_specified = sex_specified or (sex_from_query is not None)

        # Construction de la condition de sexe
        sex_priority_case = self._build_sex_condition(
            target_sex,
            actual_sex_specified,
            strict_sex_match,
            param_count,
            conditions,
            params,
        )

        if target_sex and (actual_sex_specified or strict_sex_match):
            param_count += 1

        # Normalisation des concepts
        normalized_concepts, raw_words = self.query_normalizer.get_search_terms(query)
        logger.debug(f"Normalized concepts: {normalized_concepts[:5]}")
        logger.debug(f"Raw words: {raw_words[:3]}")

        # Extraction de l'âge
        age_extracted = self._extract_age_from_query(query)
        if age_extracted:
            logger.debug(f"Age extracted from query: {age_extracted} days")
            param_count = self._add_age_condition(
                age_extracted, param_count, conditions, params
            )

        # Filtres d'entités (CORRIGÉ avec normalisation)
        if entities:
            param_count = self._add_entity_filters(
                entities, age_extracted, param_count, conditions, params
            )

        # Conditions de recherche métrique
        param_count = self._add_metric_search_conditions(
            normalized_concepts, raw_words, param_count, conditions, params
        )

        # Assemblage final
        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        # Ordre de tri
        order_clauses = [sex_priority_case]
        if age_extracted:
            order_clauses.append(f"ABS(COALESCE(m.age_min, 999) - {age_extracted})")
        order_clauses.extend(["m.value_numeric DESC NULLS LAST", "m.metric_name"])

        base_query += f" ORDER BY {', '.join(order_clauses)}"
        base_query += f" LIMIT {top_k}"

        return base_query, params

    def _normalize_breed_name(self, breed: str) -> str:
        """
        Normalise un nom de souche pour la recherche
        Retire espaces, tirets, underscores et met en minuscules

        Args:
            breed: Nom de souche à normaliser

        Returns:
            str: Nom normalisé (ex: "Cobb 500" -> "cobb500")
        """
        if not breed:
            return ""

        normalized = breed.lower()
        # Retirer tous les séparateurs communs
        normalized = re.sub(r"[\s\-_\.]+", "", normalized)

        logger.debug(f"Breed normalization: '{breed}' -> '{normalized}'")
        return normalized

    def _build_sex_condition(
        self,
        target_sex: Optional[str],
        sex_specified: bool,
        strict_sex_match: bool,
        param_count: int,
        conditions: List[str],
        params: List[Any],
    ) -> str:
        """
        Construit la condition SQL pour le sexe

        Returns:
            str: Expression CASE pour le tri par priorité de sexe
        """
        if not target_sex or target_sex == "as_hatched":
            # Pas de sexe spécifié -> priorité as_hatched
            logger.debug("No specific sex requested, prioritizing as_hatched")
            return """
                CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched') THEN 1
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = 'male' THEN 2
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = 'female' THEN 3
                    ELSE 4
                END
            """

        # Sexe spécifié
        if strict_sex_match:
            # Mode strict : SEULEMENT le sexe demandé (pour comparaisons)
            logger.debug(f"Strict sex match: {target_sex} only")
            conditions.append(f"LOWER(d.sex) = ${param_count + 1}")
            params.append(target_sex.lower())

            return f"""
                CASE 
                    WHEN LOWER(d.sex) = ${param_count + 1} THEN 1
                    ELSE 2
                END
            """
        else:
            # Mode normal : sexe spécifié + fallback as_hatched
            logger.debug(f"Sex specified: {target_sex}, with as_hatched fallback")
            conditions.append(
                f"""
                (LOWER(COALESCE(d.sex, 'as_hatched')) = ${param_count + 1} 
                 OR LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched', 'straight_run'))
            """
            )
            params.append(target_sex.lower())

            return f"""
                CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = ${param_count + 1} THEN 1
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched') THEN 2
                    ELSE 3
                END
            """

    def _add_age_condition(
        self, age: int, param_count: int, conditions: List[str], params: List[Any]
    ) -> int:
        """Ajoute la condition d'âge avec tolérance"""
        age_tolerance = 3

        param_count += 1
        param_age1 = param_count
        param_age2 = param_count + 1
        param_tolerance = param_count + 2

        conditions.append(
            f"""
            ((m.age_min <= ${param_age1} AND m.age_max >= ${param_age2}) 
             OR ABS(COALESCE(m.age_min, 0) - ${param_age1}) <= ${param_tolerance}
             OR ABS(COALESCE(m.age_max, 0) - ${param_age2}) <= ${param_tolerance})
        """
        )

        params.extend([age, age, age_tolerance])
        return param_count + 2

    def _add_entity_filters(
        self,
        entities: Dict[str, str],
        age_extracted: Optional[int],
        param_count: int,
        conditions: List[str],
        params: List[Any],
    ) -> int:
        """
        Ajoute les filtres basés sur les entités
        VERSION CORRIGÉE avec normalisation robuste des noms de souches
        """

        # Filtre de souche/race (breed) - NORMALISATION ROBUSTE
        if entities.get("breed"):
            param_count += 1

            breed_normalized = self._normalize_breed_name(entities["breed"])

            # Chercher en normalisant aussi le champ de la BD
            # REPLACE(REPLACE(REPLACE(...))) retire espaces, tirets, underscores
            conditions.append(
                f"LOWER(REPLACE(REPLACE(REPLACE(s.strain_name, ' ', ''), '-', ''), '_', '')) LIKE ${param_count}"
            )
            params.append(f"%{breed_normalized}%")
            logger.debug(
                f"Adding breed filter: {entities['breed']} -> normalized: {breed_normalized}"
            )

        # Filtre de ligne génétique (legacy support)
        elif entities.get("line"):
            param_count += 1
            line_normalized = self._normalize_breed_name(entities["line"])

            conditions.append(
                f"LOWER(REPLACE(REPLACE(REPLACE(s.strain_name, ' ', ''), '-', ''), '_', '')) LIKE ${param_count}"
            )
            params.append(f"%{line_normalized}%")
            logger.debug(
                f"Adding line filter: {entities['line']} -> normalized: {line_normalized}"
            )

        # Filtre d'âge depuis entities (si pas déjà extrait de la query)
        if entities.get("age_days") and not age_extracted:
            try:
                age_days = int(entities["age_days"])
                param_count += 1
                param_age1 = param_count
                param_age2 = param_count + 1

                conditions.append(
                    f"""
                    (m.age_min <= ${param_age1} AND m.age_max >= ${param_age2}) 
                    OR (m.age_min IS NULL AND m.age_max IS NULL)
                """
                )
                params.extend([age_days, age_days])
                param_count += 1
            except ValueError:
                logger.warning(f"Invalid age_days value: {entities.get('age_days')}")

        return param_count

    def _add_metric_search_conditions(
        self,
        normalized_concepts: List[str],
        raw_words: List[str],
        param_count: int,
        conditions: List[str],
        params: List[Any],
    ) -> int:
        """Ajoute les conditions de recherche de métriques"""
        metric_search_conditions = []

        # Concepts normalisés (max 8)
        for concept in normalized_concepts[:8]:
            param_count += 1
            metric_search_conditions.append(
                f"LOWER(m.metric_name) ILIKE ${param_count}"
            )
            params.append(f"%{concept}%")

        # Mots bruts (max 3)
        for word in raw_words[:3]:
            param_count += 1
            param_word1 = param_count
            param_word2 = param_count + 1

            metric_search_conditions.extend(
                [
                    f"LOWER(m.metric_name) ILIKE ${param_word1}",
                    f"LOWER(m.value_text) ILIKE ${param_word2}",
                ]
            )
            params.extend([f"%{word}%", f"%{word}%"])
            param_count += 1

        if metric_search_conditions:
            conditions.append(f"({' OR '.join(metric_search_conditions)})")

        return param_count

    def _extract_age_from_query(self, query: str) -> Optional[int]:
        """Extrait l'âge en jours depuis la requête"""
        patterns = [
            r"day\s+(\d+)",
            r"jour\s+(\d+)",
            r"j\s*(\d+)",
            r"(\d+)\s*day",
            r"(\d+)\s*jour",
            r"a\s+(\d+)\s+jours?",
            r"at\s+day\s+(\d+)",
            r"age\s+(\d+)",
            r"(\d+)\s*j\b",
            r"d(\d+)",
            r"age_day_(\d+)",
        ]

        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    if 0 <= age <= 150:
                        logger.debug(
                            f"Age detected: {age} days via pattern '{pattern}'"
                        )
                        return age
                except ValueError:
                    continue

        # Patterns implicites
        implicit_patterns = [
            r"à\s+(\d+)\s+jours?",
            r"at\s+(\d+)\s+days?",
            r"de\s+(\d+)\s+jours?",
            r"of\s+(\d+)\s+days?",
        ]

        for pattern in implicit_patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    if 0 <= age <= 150:
                        logger.debug(f"Implicit age: {age} days via '{pattern}'")
                        return age
                except ValueError:
                    continue

        return None


# Tests unitaires
if __name__ == "__main__":
    from unittest.mock import Mock

    # Mock normalizer
    mock_normalizer = Mock()
    mock_normalizer.extract_sex_from_query.return_value = "male"
    mock_normalizer.get_search_terms.return_value = (
        ["feed conversion", "fcr", "indice consommation"],
        ["cobb", "conversion"],
    )

    builder = PostgreSQLQueryBuilder(mock_normalizer)

    print("=" * 80)
    print("TEST 1: Mode normal avec Cobb 500")
    print("=" * 80)
    sql, params = builder.build_sex_aware_sql_query(
        "FCR du Cobb 500 mâle à 17 jours",
        entities={"breed": "Cobb 500", "sex": "male", "age_days": "17"},
        top_k=10,
        strict_sex_match=False,
    )
    print(f"SQL (extrait): ...{sql[-300:]}")
    print(f"\nParams: {params}")

    print("\n" + "=" * 80)
    print("TEST 2: Mode strict avec Ross 308")
    print("=" * 80)
    sql, params = builder.build_sex_aware_sql_query(
        "Conversion du Ross 308 mâle à 21 jours",
        entities={"breed": "Ross 308", "sex": "male", "age_days": "21"},
        top_k=10,
        strict_sex_match=True,
    )
    print(f"SQL (extrait): ...{sql[-300:]}")
    print(f"\nParams: {params}")

    print("\n" + "=" * 80)
    print("TEST 3: Test de normalisation")
    print("=" * 80)
    test_breeds = [
        "Cobb 500",
        "Cobb-500",
        "cobb500",
        "Ross 308",
        "Ross-308",
        "ross308",
        "Hy-Line Brown",
        "HyLine Brown",
    ]
    for breed in test_breeds:
        normalized = builder._normalize_breed_name(breed)
        print(f"  {breed:20s} -> {normalized}")

    print("\n" + "=" * 80)
    print("TESTS TERMINÉS")
    print("=" * 80)
