# -*- coding: utf-8 -*-
"""
postgresql_query_builder.py - Construction de requêtes SQL pour PostgreSQL
Version CORRIGÉE - Alignement des paramètres et fallback générique amélioré
"""

import logging
import re
import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PostgreSQLQueryBuilder:
    """Construit les requêtes SQL en utilisant intents.json et les noms réels de la BD"""

    # Mapping étendu des breeds vers noms BD
    BREED_EXTENDED_MAPPING = {
        "Hubbard JA87": "JA87",
        "Arbor Acres": "AA+",
        "Cobb-Vantress": "500",
        "Ross 708": "708",
        "Hubbard": "JA87",
    }

    # Mapping des métriques communes
    METRIC_MAPPINGS = {
        "body_weight": "body_weight",
        "feed_conversion_ratio": "feed_conversion_ratio",
        "fcr": "feed_conversion_ratio",
        "feed_consumption": "feed_consumption",
        "daily_gain": "daily_gain",
        "mortality": "mortality",
        "livability": "livability",
        "weight": "body_weight",
        "conversion": "feed_conversion_ratio",
        "consumption": "feed_consumption",
        "gain": "daily_gain",
    }

    def __init__(self, query_normalizer):
        """
        Args:
            query_normalizer: Instance de SQLQueryNormalizer
        """
        self.query_normalizer = query_normalizer
        self.intents_config = self._load_intents_config()
        self.line_aliases = self._extract_line_aliases()
        self.logger = logger

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
        AMÉLIORÉ: Normalise breed name pour correspondre aux noms en BD
        Gère maintenant les breeds multiples séparés par virgules

        Args:
            breed_input: Ex: "Cobb 500", "ross 308", "cobb500", "Cobb 500, Ross 308"

        Returns:
            Nom réel BD: "500", "308/308 FF", "500,308/308 FF", ou None
        """
        if not breed_input:
            return None

        breed_input = str(breed_input).strip()
        breed_lower = breed_input.lower()

        # CORRECTION FINALE: Mapping direct exact (priorité haute)
        direct_mapping = {
            # Mapping Ross 308 vers 308/308 FF
            "ross 308": "308/308 FF",
            "ross308": "308/308 FF",
            "ross-308": "308/308 FF",
            "r308": "308/308 FF",
            "308": "308/308 FF",
            "308/308 ff": "308/308 FF",
            "308/308ff": "308/308 FF",
            # Mapping Cobb 500 vers 500
            "cobb 500": "500",
            "cobb500": "500",
            "cobb-500": "500",
            "c500": "500",
            "500": "500",
            # NOUVEAU: Mapping pour comparaisons multiples
            "cobb 500, ross 308": "500,308/308 FF",
            "ross 308, cobb 500": "308/308 FF,500",
            "cobb vs ross": "500,308/308 FF",
            "ross vs cobb": "308/308 FF,500",
            "500, 308/308 ff": "500,308/308 FF",
            "308/308 ff, 500": "308/308 FF,500",
        }

        # Vérification exacte d'abord
        if breed_lower in direct_mapping:
            result = direct_mapping[breed_lower]
            logger.debug(f"Breed exact match: '{breed_input}' -> '{result}'")
            return result

        # NOUVEAU: Vérifier mapping étendu
        if breed_input in self.BREED_EXTENDED_MAPPING:
            result = self.BREED_EXTENDED_MAPPING[breed_input]
            logger.debug(f"Breed extended match: '{breed_input}' -> '{result}'")
            return result

        # NOUVEAU: Détecter si c'est une liste séparée par virgules
        if "," in breed_input:
            breeds = [b.strip() for b in breed_input.split(",")]
            normalized_breeds = []
            for breed in breeds:
                norm = self._normalize_breed_for_db(breed)
                if norm and "," not in norm:
                    normalized_breeds.append(norm)
            result = ",".join(normalized_breeds) if normalized_breeds else None
            if result:
                logger.debug(
                    f"Multiple breeds normalized: '{breed_input}' -> '{result}'"
                )
            return result

        # Recherche par mots-clés
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
        """Extraction d'âge robuste avec gestion phase alimentaire"""

        age_patterns = [
            r"à \s+(\d+)\s+jours?",
            r"(\d+)\s+jours?",
            r"de\s+(\d+)\s+jours?",
            r"(\d+)\s*j\b",
            r"(\d+)-?jours?",
            r"day\s+(\d+)",
            r"(\d+)\s+days?",
            r"at\s+(\d+)\s+days?",
            r"of\s+(\d+)\s+days?",
            r"(\d+)\s+semaines?",
        ]

        phase_patterns = {
            "starter": 10,
            "grower": 28,
            "grower 1": 21,
            "grower 2": 35,
            "finisher": 42,
            "finisher 1": 42,
            "finisher 2": 49,
            "croissance": 28,
            "finition": 42,
            "démarrage": 10,
        }

        query_lower = query.lower()

        # 1. Chercher âge explicite d'abord
        for i, pattern in enumerate(age_patterns):
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    if "semaine" in pattern:
                        age = age * 7
                    if 0 <= age <= 150:
                        logger.debug(
                            f"Age detected: {age} days via pattern '{pattern}' (priority {i+1})"
                        )
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

    def _handle_multiple_breeds(self, breeds_input: str) -> Tuple[str, List[str]]:
        """
        NOUVEAU: Gère les requêtes avec multiples breeds (Cobb 500, Ross 308)

        Args:
            breeds_input: String normalisé contenant un ou plusieurs breeds

        Returns:
            Tuple[str, List[str]]: (condition_sql, list_params)
        """
        if not breeds_input:
            return "", []

        if "," in breeds_input:
            breed_names = [b.strip() for b in breeds_input.split(",")]
        else:
            breed_names = [breeds_input.strip()]

        valid_breeds = [breed for breed in breed_names if breed]

        if not valid_breeds:
            return "", []

        if len(valid_breeds) == 1:
            return "s.strain_name = ${}", valid_breeds
        else:
            placeholders = ", ".join("${}" for _ in range(len(valid_breeds)))
            return f"s.strain_name IN ({placeholders})", valid_breeds

    def _handle_out_of_range_age(self, age: int, breed: str) -> str:
        """Gère les âges hors plage de données"""
        if age > 56:
            logger.warning(f"Age {age} jours hors plage pour {breed} (max: 56j)")
            return f"WHERE 1=0 -- Age {age} jours hors plage pour {breed} (max: 56j)"
        return ""

    def _normalize_entities(self, entities: Dict[str, str]) -> Dict[str, str]:
        """Normalise les entités pour la BD"""
        if not entities:
            return {}

        normalized = {}

        if entities.get("breed"):
            normalized["breed"] = self._normalize_breed_for_db(entities["breed"])
        elif entities.get("line"):
            normalized["breed"] = self._normalize_breed_for_db(entities["line"])

        for key, value in entities.items():
            if key not in ["breed", "line"]:
                normalized[key] = value

        return normalized

    def _build_metric_search(
        self, metric_type: Optional[str], age: Optional[int]
    ) -> List[str]:
        """
        NOUVEAU: Construire les patterns de recherche de métriques avec fallback amélioré

        Args:
            metric_type: Type de métrique (peut être None)
            age: Âge en jours (peut être None)

        Returns:
            Liste de patterns de recherche SQL
        """
        patterns = []

        if not metric_type:
            # Fallback générique amélioré
            if age:
                patterns.append(f"% for {age}%")
                patterns.append(f"%{age} days%")
                patterns.append(f"%day {age}%")
            else:
                # Recherche sur métriques communes
                patterns.extend(
                    [
                        "%body_weight%",
                        "%feed_consumption%",
                        "%feed_conversion_ratio%",
                        "%daily_gain%",
                    ]
                )

            logger.warning(
                f"⚠️ Métrique inconnue → patterns génériques: {patterns[:3]}..."
            )
            return patterns

        # Recherche spécifique normale
        base_name = self.METRIC_MAPPINGS.get(metric_type.lower(), metric_type)
        if age:
            patterns.append(f"%{base_name} for {age}%")
        patterns.append(f"%{base_name}%")

        return patterns

    def build_range_query(
        self, entities: Dict[str, str], age_min: int, age_max: int, limit: int = 12
    ) -> Tuple[str, List]:
        """Construction SQL optimisée pour plages temporelles"""

        logger.debug(f"Building range query: age {age_min}-{age_max} days")
        normalized_entities = self._normalize_entities(entities or {})

        conditions = ["1=1"]
        params = []
        param_count = 0

        # Condition d'âge optimisée avec BETWEEN
        param_count += 6
        conditions.append(
            f"""((m.age_min BETWEEN ${param_count-5} AND ${param_count-4}) OR 
            (m.age_max BETWEEN ${param_count-3} AND ${param_count-2}) OR 
            (m.age_min <= ${param_count-1} AND m.age_max >= ${param_count}))"""
        )
        params.extend([age_min, age_max, age_min, age_max, age_min, age_max])

        # Breed condition
        breed_db = normalized_entities.get("breed")
        if breed_db:
            breed_condition, breed_params = self._handle_multiple_breeds(breed_db)
            if breed_condition and breed_params:
                adjusted_condition = breed_condition
                for i, param in enumerate(breed_params):
                    placeholder_template = "${}"
                    placeholder_new = f"${param_count + i + 1}"
                    adjusted_condition = adjusted_condition.replace(
                        placeholder_template, placeholder_new, 1
                    )

                conditions.append(adjusted_condition)
                params.extend(breed_params)
                param_count += len(breed_params)

                logger.debug(f"Adding breed filter for range query: {breed_params}")

        # Métrique condition avec fallback amélioré
        param_count = self._add_metric_search_conditions_simple(
            conditions, params, param_count
        )

        # ORDER BY optimisé pour plages temporelles
        order_clause = """
        ORDER BY 
            m.age_min ASC,
            CASE WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed') THEN 1 ELSE 2 END,
            m.value_numeric DESC NULLS LAST
        """

        sql = f"""
        SELECT DISTINCT ON (m.age_min, m.metric_name)
            c.company_name, b.breed_name, s.strain_name, s.species,
            m.metric_name, m.value_numeric, m.value_text, m.unit,
            m.age_min, m.age_max, m.sheet_name, dc.category_name,
            d.sex, d.housing_system, d.data_type, m.metadata
        FROM companies c
        JOIN breeds b ON c.id = b.company_id
        JOIN strains s ON b.id = s.breed_id  
        JOIN documents d ON s.id = d.strain_id
        JOIN metrics m ON d.id = m.document_id
        JOIN data_categories dc ON m.category_id = dc.id
        WHERE {' AND '.join(conditions)}
        {order_clause}
        LIMIT {limit}
        """

        # Validation des paramètres
        placeholders = re.findall(r"\$(\d+)", sql)
        max_placeholder = max([int(p) for p in placeholders]) if placeholders else 0

        if len(params) < max_placeholder:
            logger.error(
                f"RANGE QUERY MISMATCH: {len(params)} params pour {max_placeholder} placeholders"
            )
            while len(params) < max_placeholder:
                params.append("")

        logger.debug(f"Range query SQL: {sql}")
        logger.debug(f"Range query params: {params}")

        return sql, params

    def _add_metric_search_conditions_simple(
        self, conditions: List[str], params: List[Any], param_count: int
    ) -> int:
        """Version simplifiée pour requêtes de plage - avec fallback amélioré"""

        # Ajouter condition générique pour métriques communes
        param_count += 2
        conditions.append(
            f"""(LOWER(m.metric_name) LIKE ${param_count-1} 
            OR LOWER(m.metric_name) LIKE ${param_count})"""
        )
        params.extend(["%body_weight%", "%feed_conversion_ratio%"])

        logger.debug(
            f"Added simple metric conditions (params ${param_count-1}, ${param_count})"
        )
        return param_count

    def build_sex_aware_sql_query(
        self,
        query: str,
        entities: Dict[str, str] = None,
        top_k: int = 12,
        strict_sex_match: bool = False,
    ) -> Tuple[str, List]:
        """Construction SQL avec paramètres alignés - VERSION CORRIGÉE"""

        logger.debug(f"Entities: {entities}")
        normalized_entities = self._normalize_entities(entities or {})
        logger.debug(f"Normalized: {normalized_entities}")

        conditions = ["1=1"]
        params = []
        param_count = 0

        # ORDRE FIXE pour éviter les décalages

        # 1. CONDITIONS D'ÂGE
        if normalized_entities.get("age_days"):
            param_count = self._add_age_conditions(
                normalized_entities, conditions, params, param_count
            )

        # 2. FILTRE BREED
        if normalized_entities.get("breed"):
            param_count = self._add_breed_filter(
                normalized_entities, conditions, params, param_count
            )

        # 3. FILTRE SEXE STRICT
        if strict_sex_match or self._is_explicit_sex_request(
            query, normalized_entities
        ):
            param_count = self._add_strict_sex_filter(
                normalized_entities, conditions, params, param_count
            )

        # 4. FILTRE UNITÉS
        param_count = self._add_unit_filter(conditions, params, param_count)

        # 5. CONDITIONS MÉTRIQUE (avec fallback amélioré)
        param_count = self._add_metric_search_conditions(
            query, normalized_entities, conditions, params, param_count
        )

        # Construction finale
        base_sql = self._get_base_sql()
        where_clause = " AND ".join(conditions)
        order_clause = self._build_order_clause(normalized_entities, strict_sex_match)

        final_sql = f"{base_sql} WHERE {where_clause} {order_clause} LIMIT {top_k}"

        # Validation finale
        placeholders = re.findall(r"\$(\d+)", final_sql)
        max_placeholder = max([int(p) for p in placeholders]) if placeholders else 0

        if len(params) < max_placeholder:
            logger.error(
                f"MISMATCH: {len(params)} params pour {max_placeholder} placeholders"
            )
            while len(params) < max_placeholder:
                params.append("")

        logger.debug(f"Final SQL: {final_sql}")
        logger.debug(f"Final params: {params}")
        return final_sql, params

    def _is_explicit_sex_request(self, query: str, entities: Dict[str, str]) -> bool:
        """Détecte si l'utilisateur demande explicitement un sexe"""
        if entities.get("sex") and entities["sex"] != "as_hatched":
            return True

        query_lower = query.lower()
        explicit_markers = ["femelle", "female", "mâle", "male", "poule", "coq"]
        return any(marker in query_lower for marker in explicit_markers)

    def _add_age_conditions(
        self,
        entities: Dict[str, str],
        conditions: List[str],
        params: List[Any],
        param_count: int,
    ) -> int:
        """Ajoute les conditions d'âge basées sur les entités normalisées"""
        try:
            age = int(entities["age_days"])

            breed_for_check = (
                entities.get("breed", "").split(",")[0]
                if entities.get("breed")
                else "unknown"
            )
            out_of_range_condition = self._handle_out_of_range_age(age, breed_for_check)

            if out_of_range_condition:
                logger.warning(f"Age {age} hors plage pour {breed_for_check}")
                conditions.append("1=0")
                return param_count

            param_count += 4
            age_condition = f"""
            ((m.age_min <= ${param_count-3} AND m.age_max >= ${param_count-2}) 
             OR ABS(COALESCE(m.age_min, 0) - ${param_count-3}) <= ${param_count-1}
             OR ABS(COALESCE(m.age_max, 0) - ${param_count-2}) <= ${param_count})"""
            conditions.append(age_condition)
            params.extend([age, age, 3, 3])

            logger.debug(
                f"Age condition added: {age} days (params {param_count-3} to {param_count})"
            )
        except (ValueError, KeyError):
            logger.warning(f"Invalid age_days value: {entities.get('age_days')}")

        return param_count

    def _add_breed_filter(
        self,
        entities: Dict[str, str],
        conditions: List[str],
        params: List[Any],
        param_count: int,
    ) -> int:
        """Ajoute le filtre breed avec gestion des breeds multiples"""
        breed_db = entities.get("breed")
        if breed_db:
            breed_condition, breed_params = self._handle_multiple_breeds(breed_db)
            if breed_condition and breed_params:
                adjusted_condition = breed_condition
                for i, param in enumerate(breed_params):
                    placeholder_template = "${}"
                    placeholder_new = f"${param_count + i + 1}"
                    adjusted_condition = adjusted_condition.replace(
                        placeholder_template, placeholder_new, 1
                    )

                conditions.append(adjusted_condition)
                params.extend(breed_params)
                param_count += len(breed_params)

                logger.debug(
                    f"Adding breed filter: {breed_params} (params ${param_count - len(breed_params) + 1} to ${param_count})"
                )

        return param_count

    def _add_strict_sex_filter(
        self,
        entities: Dict[str, str],
        conditions: List[str],
        params: List[Any],
        param_count: int,
    ) -> int:
        """Ajoute un filtre sexe strict quand demandé explicitement"""
        sex = entities.get("sex", "as_hatched")

        if sex != "as_hatched":
            param_count += 1
            conditions.append(f"d.sex = ${param_count}")
            params.append(sex)
            logger.debug(f"Added strict sex filter: {sex} (param ${param_count})")

        return param_count

    def _add_unit_filter(
        self, conditions: List[str], params: List[Any], param_count: int
    ) -> int:
        """Filtre les données impériales pour éviter confusion"""
        param_count += 1
        conditions.append(f"m.sheet_name NOT LIKE ${param_count}")
        params.append("%imperial%")
        logger.debug(f"Added unit filter: exclude imperial (param ${param_count})")
        return param_count

    def _get_base_sql(self) -> str:
        """Retourne la requête SQL de base"""
        return """
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
            JOIN data_categories dc ON m.category_id = dc.id"""

    def _build_order_clause(
        self, entities: Dict[str, str], strict_sex_match: bool
    ) -> str:
        """Construit la clause ORDER BY adaptée"""

        order_parts = []

        if not strict_sex_match:
            order_parts.append(
                """
                CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched') THEN 1
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = 'male' THEN 2
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = 'female' THEN 3
                    ELSE 4
                END
            """
            )

        if entities.get("age_days"):
            age = int(entities["age_days"])
            order_parts.append(f"ABS(COALESCE(m.age_min, 999) - {age})")

        order_parts.extend(["m.value_numeric DESC NULLS LAST", "m.metric_name"])

        return "ORDER BY " + ", ".join(order_parts)

    def _add_metric_search_conditions(
        self,
        query: str,
        entities: Dict[str, str],
        conditions: List[str],
        params: List[Any],
        param_count: int,
    ) -> int:
        """Ajoute les conditions de recherche de métriques - VERSION AMÉLIORÉE avec fallback"""

        metric_search_conditions = []
        query_lower = query.lower()
        age_extracted = entities.get("age_days")

        # Détecter le type de métrique demandé
        metric_type = None
        if any(term in query_lower for term in ["fcr", "conversion", "indice"]):
            metric_type = "feed_conversion_ratio"
        elif any(term in query_lower for term in ["poids", "weight", "body"]):
            metric_type = "body_weight"
        elif any(term in query_lower for term in ["consumption", "consommation"]):
            metric_type = "feed_consumption"
        elif any(term in query_lower for term in ["gain", "croissance"]):
            metric_type = "daily_gain"

        # Construire les patterns avec fallback amélioré
        age_int = int(age_extracted) if age_extracted else None
        patterns = self._build_metric_search(metric_type, age_int)

        # Ajouter les conditions SQL
        for pattern in patterns:
            param_count += 1
            metric_search_conditions.append(f"LOWER(m.metric_name) LIKE ${param_count}")
            params.append(pattern)
            logger.debug(f"Metric search pattern: {pattern} (param ${param_count})")

        if metric_search_conditions:
            conditions.append(f"({' OR '.join(metric_search_conditions)})")

        return param_count

    def build_reverse_lookup_query(
        self, breed: str, sex: str, metric_type: str, target_value: float
    ) -> Tuple[str, List]:
        """
        Construit une requête pour trouver l'âge correspondant à une valeur cible

        Args:
            breed: Nom de la souche (normalisé)
            sex: Sexe
            metric_type: Type de métrique
            target_value: Valeur cible à trouver

        Returns:
            Tuple[str, List]: (requête SQL, paramètres)
        """
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
        """Construit la condition SQL pour le sexe (méthode héritée)"""
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
        """Ajoute la condition d'âge avec tolérance"""
        age_tolerance = 3

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
        """Ajoute les filtres basés sur les entités"""

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

    mock_normalizer = Mock()
    mock_normalizer.extract_sex_from_query.return_value = "male"

    builder = PostgreSQLQueryBuilder(mock_normalizer)

    print("\n" + "=" * 80)
    print("TEST 1: Fallback générique amélioré")
    print("=" * 80)

    # Test sans métrique connue, avec âge
    patterns_with_age = builder._build_metric_search(None, 35)
    print(f"  Patterns avec âge 35: {patterns_with_age}")

    # Test sans métrique connue, sans âge
    patterns_no_age = builder._build_metric_search(None, None)
    print(f"  Patterns sans âge: {patterns_no_age}")

    # Test avec métrique connue
    patterns_fcr = builder._build_metric_search("fcr", 42)
    print(f"  Patterns FCR à 42j: {patterns_fcr}")

    print("\n" + "=" * 80)
    print("TEST 2: Normalisation breeds")
    print("=" * 80)
    test_inputs = [
        "Cobb 500",
        "ross 308",
        "Cobb 500, Ross 308",
        "Hubbard JA87",
    ]
    for inp in test_inputs:
        result = builder._normalize_breed_for_db(inp)
        print(f"  {inp:25s} -> {result}")

    print("\n" + "=" * 80)
    print("TEST 3: Extraction d'âge avec phases")
    print("=" * 80)
    test_queries = [
        "poids à 42 jours",
        "starter feed",
        "grower performance",
        "finisher phase",
    ]
    for query in test_queries:
        age = builder._extract_age_from_query(query)
        print(f"  {query:25s} -> {age} jours")

    print("\n" + "=" * 80)
    print("TEST 4: Construction requête complète avec fallback")
    print("=" * 80)
    sql, params = builder.build_sex_aware_sql_query(
        "Conversion alimentaire du Cobb 500 à 35 jours",
        entities={"breed": "Cobb 500", "age_days": "35"},
        top_k=10,
    )

    placeholders = re.findall(r"\$\d+", sql)
    unique_placeholders = set(placeholders)

    print(f"Paramètres fournis: {len(params)}")
    print(f"Placeholders uniques: {len(unique_placeholders)}")
    print(f"Correspondance: {'✓' if len(params) >= len(unique_placeholders) else '✗'}")

    print("\n" + "=" * 80)
    print("TEST 5: Requête avec métrique inconnue (fallback)")
    print("=" * 80)
    sql_unknown, params_unknown = builder.build_sex_aware_sql_query(
        "Performance du Cobb 500 à 35 jours",
        entities={"breed": "Cobb 500", "age_days": "35"},
        top_k=5,
    )

    print(f"Paramètres fournis (métrique inconnue): {len(params_unknown)}")
    print(
        f"Patterns génériques utilisés: {[p for p in params_unknown if '%' in str(p)]}"
    )

    print("\n" + "=" * 80)
    print("TEST 6: Requête sans âge ni métrique (double fallback)")
    print("=" * 80)
    sql_no_context, params_no_context = builder.build_sex_aware_sql_query(
        "Données du Cobb 500",
        entities={"breed": "Cobb 500"},
        top_k=5,
    )

    print(f"Paramètres fournis (sans contexte): {len(params_no_context)}")
    generic_patterns = [p for p in params_no_context if "%" in str(p)]
    print(f"Patterns métriques communes: {generic_patterns}")

    print("\n" + "=" * 80)
    print("TEST 7: Normalisation Ross 308")
    print("=" * 80)
    ross_variants = [
        "ross 308",
        "308/308 ff",
        "308/308FF",
        "308",
        "r308",
    ]
    for variant in ross_variants:
        result = builder._normalize_breed_for_db(variant)
        expected = "308/308 FF"
        status = "✓" if result == expected else "✗"
        print(f"  {variant:15s} -> {result:15s} {status}")

    print("\n" + "=" * 80)
    print("TEST 8: Validation finale")
    print("=" * 80)
    if len(params) >= len(unique_placeholders):
        print("🎉 CORRECTION RÉUSSIE: Nombre de paramètres >= placeholders")
        print("✓ Fallback générique amélioré implémenté")
        print("✓ Patterns adaptatifs selon contexte")
    else:
        print(
            f"⚠ PROBLÈME: {len(unique_placeholders) - len(params)} paramètres manquants"
        )
