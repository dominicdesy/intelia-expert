# -*- coding: utf-8 -*-
"""
postgresql_query_builder.py - Construction de requêtes SQL pour PostgreSQL
Version CORRIGÉE - Alignement des paramètres et placeholders SQL
"""

import logging
import re
import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PostgreSQLQueryBuilder:
    """Construit les requêtes SQL en utilisant intents.json et les noms réels de la BD"""

    # Mapping des noms normalisés -> noms RÉELS dans la base de données
    DB_STRAIN_MAPPING = {
        # Ross
        "ross308": "308/308 FF",
        "ross 308": "308/308 FF",
        "ross-308": "308/308 FF",
        "r308": "308/308 FF",
        # Cobb
        "cobb500": "500",
        "cobb 500": "500",
        "cobb-500": "500",
        "c500": "500",
    }

    def __init__(self, query_normalizer):
        """
        Args:
            query_normalizer: Instance de SQLQueryNormalizer
        """
        self.query_normalizer = query_normalizer
        self.intents_config = self._load_intents_config()
        self.line_aliases = self._extract_line_aliases()

    def _load_intents_config(self) -> Dict:
        """Charge intents.json pour récupérer les aliases"""
        config_paths = [
            Path(__file__).parent.parent / "config" / "intents.json",
            Path(__file__).parent / "config" / "intents.json",
            Path.cwd() / "config" / "intents.json",
            Path.cwd() / "llm" / "config" / "intents.json",
        ]

        for path in config_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                        logger.info(f"Intents.json chargé depuis: {path}")
                        return config
                except Exception as e:
                    logger.warning(f"Erreur chargement {path}: {e}")

        logger.warning("intents.json non trouvé - utilisation mappings par défaut")
        return {}

    def _extract_line_aliases(self) -> Dict[str, List[str]]:
        """Extrait les aliases de lignées depuis intents.json"""
        if not self.intents_config:
            return {}

        aliases = self.intents_config.get("aliases", {}).get("line", {})
        logger.info(f"Aliases chargés pour {len(aliases)} lignées")
        return aliases

    def _normalize_breed_for_db(self, breed_input: str) -> Optional[str]:
        """
        Convertit l'entrée utilisateur en nom RÉEL de la base de données

        Args:
            breed_input: Ex: "Cobb 500", "ross 308", "cobb500"

        Returns:
            Nom réel BD: "500", "308/308 FF", ou None
        """
        if not breed_input:
            return None

        breed_normalized = breed_input.lower().strip()
        breed_clean = re.sub(r"[\s\-_]+", "", breed_normalized)

        # 1. Vérifier le mapping direct vers la BD
        if breed_clean in self.DB_STRAIN_MAPPING:
            result = self.DB_STRAIN_MAPPING[breed_clean]
            logger.debug(f"Breed DB mapping: '{breed_input}' -> '{result}'")
            return result

        # 2. Vérifier les variantes avec espaces/tirets
        for key, value in self.DB_STRAIN_MAPPING.items():
            if breed_normalized == key:
                logger.debug(
                    f"Breed DB mapping (avec espaces): '{breed_input}' -> '{value}'"
                )
                return value

        # 3. Fallback: chercher dans les aliases intents.json
        for canonical_line, aliases in self.line_aliases.items():
            canonical_clean = re.sub(r"[\s\-_]+", "", canonical_line.lower())

            if breed_clean == canonical_clean:
                if canonical_clean in self.DB_STRAIN_MAPPING:
                    result = self.DB_STRAIN_MAPPING[canonical_clean]
                    logger.debug(f"Breed via intents+DB: '{breed_input}' -> '{result}'")
                    return result

            for alias in aliases:
                alias_clean = re.sub(r"[\s\-_]+", "", alias.lower())
                if breed_clean == alias_clean and alias_clean in self.DB_STRAIN_MAPPING:
                    result = self.DB_STRAIN_MAPPING[alias_clean]
                    logger.debug(f"Breed via alias+DB: '{breed_input}' -> '{result}'")
                    return result

        # 4. Dernier recours: retourner l'input nettoyé
        logger.warning(
            f"Aucun mapping trouvé pour '{breed_input}', utilisation directe"
        )
        return breed_normalized

    def build_sex_aware_sql_query(
        self,
        query: str,
        entities: Dict[str, str] = None,
        top_k: int = 10,
        strict_sex_match: bool = False,
    ) -> Tuple[str, List]:
        """
        Construit une requête SQL adaptée à la structure réelle de la BD

        Args:
            query: Requête utilisateur
            entities: Entités extraites (breed, sex, age_days, etc.)
            top_k: Nombre de résultats
            strict_sex_match: Si True, ne cherche que le sexe exact

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
        param_index = 0  # FIXE: Compteur séquentiel pour les placeholders

        # Extraction du sexe
        sex_from_query = self.query_normalizer.extract_sex_from_query(query)
        sex_from_entities = entities.get("sex") if entities else None
        sex_specified = entities.get("sex_specified") == "true" if entities else False

        target_sex = sex_from_entities or sex_from_query
        actual_sex_specified = sex_specified or (sex_from_query is not None)

        # Construction de la condition de sexe
        sex_priority_case, param_index = self._build_sex_condition(
            target_sex,
            actual_sex_specified,
            strict_sex_match,
            param_index,
            conditions,
            params,
        )

        # Extraction de l'âge
        age_extracted = self._extract_age_from_query(query)
        if age_extracted:
            logger.debug(f"Age extracted from query: {age_extracted} days")
            param_index = self._add_age_condition(
                age_extracted, param_index, conditions, params
            )

        # Filtres d'entités avec normalisation BD
        if entities:
            param_index = self._add_entity_filters(
                entities, age_extracted, param_index, conditions, params
            )

        # Conditions de recherche métrique (feed_conversion_ratio for X)
        param_index = self._add_metric_search_conditions(
            query, age_extracted, param_index, conditions, params
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

        logger.debug(f"Final SQL: {base_query}")
        logger.debug(f"Final params count: {len(params)}")
        logger.debug(f"Final params: {params}")

        return base_query, params

    # ========================================================================
    # NOUVELLE MÉTHODE: Recherche inversée (valeur → âge)
    # ========================================================================

    def build_reverse_lookup_query(
        self, breed: str, sex: str, metric_type: str, target_value: float
    ) -> Tuple[str, List]:
        """
        Construit une requête pour trouver l'âge correspondant à une valeur cible

        Args:
            breed: Nom de la souche (normalisé)
            sex: Sexe
            metric_type: Type de métrique ("body_weight", "feed_conversion_ratio", etc.)
            target_value: Valeur cible à trouver

        Returns:
            Tuple[str, List]: (requête SQL, paramètres)
        """
        # Normaliser breed pour DB
        db_strain_name = self._normalize_breed_for_db(breed)

        query = """
        SELECT 
            m.age_min,
            m.value_numeric as value,
            m.unit,
            ABS(m.value_numeric - $1) as difference,
            s.strain_name,
            d.sex
        FROM metrics m
        JOIN documents d ON m.document_id = d.id
        JOIN strains s ON d.strain_id = s.id
        WHERE s.strain_name = $2
          AND d.sex = $3
          AND m.metric_name LIKE $4
          AND m.value_numeric IS NOT NULL
        ORDER BY difference ASC
        LIMIT 1
        """

        params = [target_value, db_strain_name, sex, f"%{metric_type}%"]

        logger.debug(
            f"Reverse lookup: {metric_type}={target_value} for {db_strain_name} {sex}"
        )

        return query, params

    def _build_sex_condition(
        self,
        target_sex: Optional[str],
        sex_specified: bool,
        strict_sex_match: bool,
        param_index: int,
        conditions: List[str],
        params: List[Any],
    ) -> Tuple[str, int]:
        """
        FIXE: Construit la condition SQL pour le sexe avec comptage correct

        Returns:
            Tuple[str, int]: (ORDER BY clause, nouveau param_index)
        """
        if not target_sex or target_sex == "as_hatched":
            logger.debug("No specific sex requested, prioritizing as_hatched")
            return (
                """
                CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched') THEN 1
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = 'male' THEN 2
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = 'female' THEN 3
                    ELSE 4
                END
            """,
                param_index,
            )

        if strict_sex_match:
            logger.debug(f"Strict sex match: {target_sex} only")
            param_index += 1
            conditions.append(f"LOWER(d.sex) = ${param_index}")
            params.append(target_sex.lower())

            return (
                f"""
                CASE 
                    WHEN LOWER(d.sex) = ${param_index} THEN 1
                    ELSE 2
                END
            """,
                param_index,
            )
        else:
            logger.debug(f"Sex specified: {target_sex}, with as_hatched fallback")
            param_index += 1
            conditions.append(
                f"""
                (LOWER(COALESCE(d.sex, 'as_hatched')) = ${param_index} 
                 OR LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched', 'straight_run'))
            """
            )
            params.append(target_sex.lower())

            return (
                f"""
                CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = ${param_index} THEN 1
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched') THEN 2
                    ELSE 3
                END
            """,
                param_index,
            )

    def _add_age_condition(
        self, age: int, param_index: int, conditions: List[str], params: List[Any]
    ) -> int:
        """FIXE: Ajoute la condition d'âge avec tolérance"""
        age_tolerance = 3

        # Trois paramètres: age, age, tolerance
        param_age1 = param_index + 1
        param_age2 = param_index + 2
        param_tolerance = param_index + 3

        conditions.append(
            f"""
            ((m.age_min <= ${param_age1} AND m.age_max >= ${param_age2}) 
             OR ABS(COALESCE(m.age_min, 0) - ${param_age1}) <= ${param_tolerance}
             OR ABS(COALESCE(m.age_max, 0) - ${param_age2}) <= ${param_tolerance})
        """
        )

        params.extend([age, age, age_tolerance])
        return param_index + 3

    def _add_entity_filters(
        self,
        entities: Dict[str, str],
        age_extracted: Optional[int],
        param_index: int,
        conditions: List[str],
        params: List[Any],
    ) -> int:
        """FIXE: Ajoute les filtres basés sur les entités - VERSION BD RÉELLE"""

        # Filtre de souche avec normalisation vers noms BD
        if entities.get("breed"):
            db_strain_name = self._normalize_breed_for_db(entities["breed"])

            if db_strain_name:
                param_index += 1
                conditions.append(f"s.strain_name = ${param_index}")
                params.append(db_strain_name)
                logger.debug(
                    f"Adding breed filter: {entities['breed']} -> DB: '{db_strain_name}'"
                )

        elif entities.get("line"):
            db_strain_name = self._normalize_breed_for_db(entities["line"])

            if db_strain_name:
                param_index += 1
                conditions.append(f"s.strain_name = ${param_index}")
                params.append(db_strain_name)
                logger.debug(
                    f"Adding line filter: {entities['line']} -> DB: '{db_strain_name}'"
                )

        # Filtre d'âge depuis entities (si pas déjà extrait)
        if entities.get("age_days") and not age_extracted:
            try:
                age_days = int(entities["age_days"])
                param_age1 = param_index + 1
                param_age2 = param_index + 2

                conditions.append(
                    f"""
                    (m.age_min <= ${param_age1} AND m.age_max >= ${param_age2}) 
                    OR (m.age_min IS NULL AND m.age_max IS NULL)
                """
                )
                params.extend([age_days, age_days])
                param_index += 2
            except ValueError:
                logger.warning(f"Invalid age_days value: {entities.get('age_days')}")

        return param_index

    def _add_metric_search_conditions(
        self,
        query: str,
        age_extracted: Optional[int],
        param_index: int,
        conditions: List[str],
        params: List[Any],
    ) -> int:
        """
        FIXE: Ajoute les conditions de recherche de métriques
        Adapté à la structure réelle: "feed_conversion_ratio for X"
        """
        metric_search_conditions = []

        query_lower = query.lower()

        # Pattern pour FCR/conversion
        if any(term in query_lower for term in ["fcr", "conversion", "indice"]):
            if age_extracted:
                param_index += 1
                metric_search_conditions.append(
                    f"LOWER(m.metric_name) LIKE ${param_index}"
                )
                params.append(f"%feed_conversion_ratio for {age_extracted}%")
                logger.debug(
                    f"Searching for: feed_conversion_ratio for {age_extracted}"
                )

            param_index += 1
            metric_search_conditions.append(f"LOWER(m.metric_name) LIKE ${param_index}")
            params.append("%feed_conversion_ratio%")

        # Pattern pour poids/weight
        elif any(term in query_lower for term in ["poids", "weight", "body"]):
            if age_extracted:
                param_index += 1
                metric_search_conditions.append(
                    f"LOWER(m.metric_name) LIKE ${param_index}"
                )
                params.append(f"%body_weight for {age_extracted}%")

            param_index += 1
            metric_search_conditions.append(f"LOWER(m.metric_name) LIKE ${param_index}")
            params.append("%body_weight%")

        # Pattern générique si rien de spécifique
        else:
            if age_extracted:
                param_index += 1
                metric_search_conditions.append(
                    f"LOWER(m.metric_name) LIKE ${param_index}"
                )
                params.append(f"% for {age_extracted}%")

        if metric_search_conditions:
            conditions.append(f"({' OR '.join(metric_search_conditions)})")

        return param_index

    def _extract_age_from_query(self, query: str) -> Optional[int]:
        """Extrait l'âge en jours depuis la requête"""
        patterns = [
            r"(\d+)\s*jours?",
            r"(\d+)\s*days?",
            r"jour\s+(\d+)",
            r"day\s+(\d+)",
            r"à\s+(\d+)\s+jours?",
            r"at\s+(\d+)\s+days?",
            r"de\s+(\d+)\s+jours?",
            r"of\s+(\d+)\s+days?",
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

        return None


# Tests unitaires
if __name__ == "__main__":
    from unittest.mock import Mock

    # Mock normalizer
    mock_normalizer = Mock()
    mock_normalizer.extract_sex_from_query.return_value = "male"

    builder = PostgreSQLQueryBuilder(mock_normalizer)

    print("=" * 80)
    print("TEST: Construction requête complète avec paramètres alignés")
    print("=" * 80)
    sql, params = builder.build_sex_aware_sql_query(
        "Quelle est la conversion alimentaire du Cobb 500 mâle à 17 jours ?",
        entities={"breed": "Cobb 500", "sex": "male", "age_days": "17"},
        top_k=10,
        strict_sex_match=True,
    )

    # Compter les placeholders dans la requête
    import re

    placeholders = re.findall(r"\$\d+", sql)
    unique_placeholders = set(placeholders)

    print(f"Paramètres fournis: {len(params)}")
    print(f"Placeholders uniques trouvés: {len(unique_placeholders)}")
    print(f"Placeholders: {sorted(unique_placeholders)}")
    print(f"Correspondance: {'✓' if len(params) >= len(unique_placeholders) else '✗'}")

    if len(params) >= len(unique_placeholders):
        print("\n🎉 CORRECTION RÉUSSIE: Nombre de paramètres >= placeholders")
    else:
        print(
            f"\n❌ PROBLÈME RESTANT: {len(unique_placeholders) - len(params)} paramètres manquants"
        )
