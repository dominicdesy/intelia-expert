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
        Normalisation robuste des noms de souches - VERSION CORRIGÉE
        
        Args:
            breed_input: Ex: "Cobb 500", "ross 308", "cobb500"
        
        Returns:
            Nom réel BD: "500", "308/308 FF", ou None
        """
        if not breed_input:
            return None
        
        breed_lower = breed_input.lower().strip()
        
        # Mappings complets avec toutes les variantes
        breed_mappings = {
            # Cobb 500 variants
            "cobb 500": "500",
            "cobb500": "500", 
            "cobb-500": "500",
            "c500": "500",
            "500": "500",
            
            # Ross 308 variants  
            "ross 308": "308/308 FF",
            "ross308": "308/308 FF",
            "ross-308": "308/308 FF", 
            "r308": "308/308 FF",
            "308": "308/308 FF",
            
            # Gestion des comparaisons multiples
            "cobb 500, ross 308": ["500", "308/308 FF"],
            "ross 308, cobb 500": ["308/308 FF", "500"],
            "cobb vs ross": ["500", "308/308 FF"],
            "ross vs cobb": ["308/308 FF", "500"],
        }
        
        # Chercher correspondance exacte
        if breed_lower in breed_mappings:
            result = breed_mappings[breed_lower]
            logger.debug(f"Breed DB mapping: '{breed_input}' -> '{result}'")
            return result
        
        # Recherche par mots-clés si pas de correspondance exacte
        if "cobb" in breed_lower and "500" in breed_lower:
            logger.debug(f"Breed keyword match: '{breed_input}' -> '500'")
            return "500"
        elif "ross" in breed_lower and "308" in breed_lower:
            logger.debug(f"Breed keyword match: '{breed_input}' -> '308/308 FF'")
            return "308/308 FF"
        
        # Fallback: chercher dans les aliases intents.json
        for canonical_line, aliases in self.line_aliases.items():
            canonical_clean = re.sub(r"[\s\-_]+", "", canonical_line.lower())
            breed_clean = re.sub(r"[\s\-_]+", "", breed_lower)
            
            if breed_clean == canonical_clean:
                # Mapper vers les noms de BD si possible
                if "cobb" in canonical_line.lower():
                    return "500"
                elif "ross" in canonical_line.lower():
                    return "308/308 FF"
            
            for alias in aliases:
                alias_clean = re.sub(r"[\s\-_]+", "", alias.lower())
                if breed_clean == alias_clean:
                    if "cobb" in alias.lower():
                        return "500"
                    elif "ross" in alias.lower():
                        return "308/308 FF"
        
        logger.warning(f"Souche non reconnue: '{breed_input}'")
        return None

    def _extract_age_from_query(self, query: str) -> Optional[int]:
        """Extraction d'âge robuste avec gestion phase alimentaire - VERSION AMÉLIORÉE"""
        
        # Patterns d'âge existants (qui marchent bien)
        age_patterns = [
            r"à\s+(\d+)\s+jours?",           # "à 42 jours" - PRIORITÉ 1
            r"(\d+)\s+jours?",               # "42 jours"
            r"de\s+(\d+)\s+jours?",          # "de 42 jours"  
            r"(\d+)\s*j\b",                  # "42j"
            r"(\d+)-?jours?",                # "42-jours"
            r"day\s+(\d+)",                  # "day 42"
            r"(\d+)\s+days?",                # "42 days"
            r"at\s+(\d+)\s+days?",           # "at 42 days"
            r"of\s+(\d+)\s+days?",           # "of 42 days"
            r"(\d+)\s+semaines?",            # "6 semaines"
        ]
        
        # NOUVEAUX patterns pour phases alimentaires
        phase_patterns = {
            "starter": 10,      # ~10 jours
            "grower": 28,       # ~28 jours  
            "grower 1": 21,     # ~21 jours
            "grower 2": 35,     # ~35 jours
            "finisher": 42,     # ~42 jours
            "finisher 1": 42,   # ~42 jours
            "finisher 2": 49,   # ~49 jours
            "croissance": 28,   # Phase croissance français
            "finition": 42,     # Phase finition français
            "démarrage": 10,    # Phase démarrage français
        }
        
        query_lower = query.lower()
        
        # 1. Chercher âge explicite d'abord (priorité haute)
        for i, pattern in enumerate(age_patterns):
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    
                    # Conversion semaines → jours
                    if "semaine" in pattern:
                        age = age * 7
                    
                    # Validation range
                    if 0 <= age <= 150:
                        logger.debug(f"Age detected: {age} days via pattern '{pattern}' (priority {i+1})")
                        return age
                        
                except ValueError:
                    continue
        
        # 2. Si pas d'âge explicite, chercher phase alimentaire
        for phase, default_age in phase_patterns.items():
            if phase in query_lower:
                logger.debug(f"Phase détectée: {phase} → {default_age} jours")
                return default_age

        logger.debug("Aucun âge ou phase détecté dans la requête")
        return None

    def _normalize_entities(self, entities: Dict[str, str]) -> Dict[str, str]:
        """Normalise les entités pour la BD"""
        if not entities:
            return {}
        
        normalized = {}
        
        # Normaliser breed/line
        if entities.get("breed"):
            normalized["breed"] = self._normalize_breed_for_db(entities["breed"])
        elif entities.get("line"):
            normalized["breed"] = self._normalize_breed_for_db(entities["line"])
        
        # Copier les autres entités
        for key, value in entities.items():
            if key not in ["breed", "line"]:
                normalized[key] = value
        
        return normalized

    def build_sex_aware_sql_query(
        self, 
        query: str, 
        entities: Dict[str, str] = None, 
        top_k: int = 12,
        strict_sex_match: bool = False
    ) -> Tuple[str, List]:
        """Construction SQL avec paramètres alignés - VERSION CORRIGÉE"""
        
        logger.debug(f"Entities: {entities}")
        normalized_entities = self._normalize_entities(entities or {})
        logger.debug(f"Normalized: {normalized_entities}")
        
        # Initialisation
        conditions = ["1=1"]
        params = []
        param_count = 0
        
        # ORDRE FIXE pour éviter les décalages
        
        # 1. Age (toujours en premier si présent)
        age_extracted = self._extract_age_from_query(query)
        if age_extracted:
            param_count += 4  # Réserver 4 paramètres pour l'âge
            age_condition = f"""
            ((m.age_min <= ${param_count-3} AND m.age_max >= ${param_count-2}) 
             OR ABS(COALESCE(m.age_min, 0) - ${param_count-3}) <= ${param_count-1}
             OR ABS(COALESCE(m.age_max, 0) - ${param_count-2}) <= ${param_count})"""
            conditions.append(age_condition)
            params.extend([age_extracted, age_extracted, 3, 3])  # 4 paramètres total
            
            logger.debug(f"Age condition added: {age_extracted} days (params {param_count-3} to {param_count})")
        else:
            # NOUVEAU : Requête sans contrainte d'âge
            logger.debug("Aucun âge spécifié - recherche tous âges")
            # Pas de condition d'âge = recherche plus large
        
        # 2. Breed (toujours après age)
        breed_db = normalized_entities.get("breed")
        if breed_db:
            param_count += 1
            conditions.append(f"s.strain_name = ${param_count}")
            params.append(breed_db)
            logger.debug(f"Adding breed filter: {entities.get('breed') if entities else 'N/A'} -> DB: '{breed_db}' (param ${param_count})")
        
        # 3. Métrique (toujours après breed)
        param_count = self._add_metric_search_conditions(
            query, conditions, params, param_count, age_extracted
        )
        
        # Construction finale
        sql_conditions = " AND ".join(conditions)
        sql_query = f"""
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
            WHERE {sql_conditions}
            ORDER BY 
                CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched') THEN 1
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = 'male' THEN 2
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = 'female' THEN 3
                    ELSE 4
                END
            {f", ABS(COALESCE(m.age_min, 999) - {age_extracted})" if age_extracted else ", m.age_min ASC NULLS LAST"}, m.value_numeric DESC NULLS LAST, m.metric_name 
            LIMIT {top_k}"""
        
        # VALIDATION CRITIQUE des paramètres
        placeholders = re.findall(r'\$(\d+)', sql_query)
        max_placeholder = max([int(p) for p in placeholders]) if placeholders else 0
        
        if len(params) < max_placeholder:
            logger.error(f"MISMATCH: {len(params)} params pour {max_placeholder} placeholders")
            # Combler avec des valeurs par défaut
            while len(params) < max_placeholder:
                params.append('')
                logger.warning(f"Adding empty param to reach {max_placeholder}")
        
        logger.debug(f"Final SQL: {sql_query}")
        logger.debug(f"Final params count: {len(params)}")
        logger.debug(f"Final params: {params}")
        
        return sql_query, params

    def _add_metric_search_conditions(
        self, 
        query: str, 
        conditions: List[str], 
        params: List[Any], 
        param_count: int, 
        age_extracted: Optional[int]
    ) -> int:
        """Ajoute les conditions de recherche de métriques - VERSION CORRIGÉE"""
        
        metric_search_conditions = []
        query_lower = query.lower()

        # Pattern pour FCR/conversion
        if any(term in query_lower for term in ["fcr", "conversion", "indice"]):
            if age_extracted:
                param_count += 1
                metric_search_conditions.append(f"LOWER(m.metric_name) LIKE ${param_count}")
                params.append(f"%feed_conversion_ratio for {age_extracted}%")
                logger.debug(f"Searching for: feed_conversion_ratio for {age_extracted} (param ${param_count})")

            param_count += 1
            metric_search_conditions.append(f"LOWER(m.metric_name) LIKE ${param_count}")
            params.append("%feed_conversion_ratio%")
            logger.debug(f"Searching for: feed_conversion_ratio (param ${param_count})")

        # Pattern pour poids/weight
        elif any(term in query_lower for term in ["poids", "weight", "body"]):
            if age_extracted:
                param_count += 1
                metric_search_conditions.append(f"LOWER(m.metric_name) LIKE ${param_count}")
                params.append(f"%body_weight for {age_extracted}%")
                logger.debug(f"Searching for: body_weight for {age_extracted} (param ${param_count})")

            param_count += 1
            metric_search_conditions.append(f"LOWER(m.metric_name) LIKE ${param_count}")
            params.append("%body_weight%")
            logger.debug(f"Searching for: body_weight (param ${param_count})")

        # Pattern générique si rien de spécifique
        else:
            if age_extracted:
                param_count += 1
                metric_search_conditions.append(f"LOWER(m.metric_name) LIKE ${param_count}")
                params.append(f"% for {age_extracted}%")
                logger.debug(f"Searching for: generic metric for {age_extracted} (param ${param_count})")

        if metric_search_conditions:
            conditions.append(f"({' OR '.join(metric_search_conditions)})")

        return param_count

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

    # ========================================================================
    # MÉTHODES HÉRITÉES CONSERVÉES (pour compatibilité)
    # ========================================================================

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
        CONSERVÉ: Construit la condition SQL pour le sexe (version héritée)
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
        """CONSERVÉ: Ajoute la condition d'âge avec tolérance (version héritée)"""
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
        """CONSERVÉ: Ajoute les filtres basés sur les entités (version héritée)"""

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


# Tests unitaires
if __name__ == "__main__":
    from unittest.mock import Mock

    # Mock normalizer
    mock_normalizer = Mock()
    mock_normalizer.extract_sex_from_query.return_value = "male"

    builder = PostgreSQLQueryBuilder(mock_normalizer)

    print("=" * 80)
    print("TEST 1: Normalisation Cobb 500 -> 500")
    print("=" * 80)
    test_inputs = ["Cobb 500", "cobb 500", "cobb500", "Cobb-500", "c500"]
    for inp in test_inputs:
        result = builder._normalize_breed_for_db(inp)
        print(f"  {inp:20s} -> {result}")

    print("\n" + "=" * 80)
    print("TEST 2: Normalisation Ross 308 -> 308/308 FF")
    print("=" * 80)
    test_inputs = ["Ross 308", "ross 308", "ross308", "Ross-308", "r308"]
    for inp in test_inputs:
        result = builder._normalize_breed_for_db(inp)
        print(f"  {inp:20s} -> {result}")

    print("\n" + "=" * 80)
    print("TEST 3: Extraction d'âge améliorée avec phases alimentaires")
    print("=" * 80)
    test_queries = [
        "poids à 42 jours",
        "conversion de 35 jours", 
        "42j",
        "6 semaines",
        "at 21 days",
        "starter feed",
        "grower phase",
        "finisher performance",
        "grower 1 results",
        "finition feed",
        "croissance performance"
    ]
    for query in test_queries:
        age = builder._extract_age_from_query(query)
        print(f"  {query:25s} -> {age} jours")

    print("\n" + "=" * 80)
    print("TEST 4: Construction requête complète avec paramètres alignés")
    print("=" * 80)
    sql, params = builder.build_sex_aware_sql_query(
        "Quelle est la conversion alimentaire du Cobb 500 mâle à 17 jours ?",
        entities={"breed": "Cobb 500", "sex": "male", "age_days": "17"},
        top_k=10,
        strict_sex_match=True,
    )

    # Compter les placeholders dans la requête
    placeholders = re.findall(r"\$\d+", sql)
    unique_placeholders = set(placeholders)

    print(f"Paramètres fournis: {len(params)}")
    print(f"Placeholders uniques trouvés: {len(unique_placeholders)}")
    print(f"Placeholders: {sorted(unique_placeholders)}")
    print(f"Correspondance: {'✓' if len(params) >= len(unique_placeholders) else '✗'}")

    print("\n" + "=" * 80)
    print("TEST 5: Requête sans âge spécifique")
    print("=" * 80)
    sql_no_age, params_no_age = builder.build_sex_aware_sql_query(
        "conversion alimentaire du Cobb 500",
        entities={"breed": "Cobb 500"},
        top_k=5
    )
    
    placeholders_no_age = re.findall(r"\$\d+", sql_no_age)
    unique_placeholders_no_age = set(placeholders_no_age)
    
    print(f"Paramètres fournis (sans âge): {len(params_no_age)}")
    print(f"Placeholders uniques (sans âge): {len(unique_placeholders_no_age)}")
    print(f"Correspondance sans âge: {'✓' if len(params_no_age) >= len(unique_placeholders_no_age) else '✗'}")
    print(f"ORDER BY adapté: {'age_min ASC' in sql_no_age}")

    if len(params) >= len(unique_placeholders):
        print("\n🎉 CORRECTION RÉUSSIE: Nombre de paramètres >= placeholders")
    else:
        print(
            f"\n❌ PROBLÈME RESTANT: {len(unique_placeholders) - len(params)} paramètres manquants"
        )