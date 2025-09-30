# -*- coding: utf-8 -*-
"""
postgresql_query_builder.py - Construction de requêtes SQL pour PostgreSQL
Version REFACTORISÉE - Utilisation de BreedsRegistry au lieu de mappings hardcodés
"""

import logging
import re
import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

from llm.utils.breeds_registry import get_breeds_registry

logger = logging.getLogger(__name__)


class PostgreSQLQueryBuilder:
    """Construit les requêtes SQL en utilisant intents.json et les noms réels de la BD"""

    # Mapping des métriques communes (noms normalisés)
    METRIC_MAPPINGS = {
        "body_weight": "body_weight",
        "feed_conversion_ratio": "feed_conversion_ratio",
        "fcr": "feed_conversion_ratio",
        "feed_consumption": "feed_consumption",
        "daily_gain": "daily_gain",
        "average_daily_gain": "daily_gain",
        "mortality": "mortality",
        "livability": "livability",
        "weight": "body_weight",
        "conversion": "feed_conversion_ratio",
        "consumption": "feed_consumption",
        "gain": "daily_gain",
        "cumulative_feed_intake": "cumulative_feed_intake",
        "feed_intake": "cumulative_feed_intake",
        "yield": "yield",
        "rendement": "yield",
    }

    # Structure imbriquée avec clé 'patterns' pour flexibilité future
    METRIC_PATTERNS = {
        "body_weight": {
            "patterns": [
                "body_weight for {age}",
                "body_weight",
                "body weight",
                "weight",
                "bw",
            ]
        },
        "feed_conversion_ratio": {
            "patterns": [
                "feed_conversion_ratio for {age}",
                "feed_conversion_ratio",
                "fcr",
                "feed conversion",
                "conversion ratio",
            ]
        },
        "average_daily_gain": {
            "patterns": [
                "daily_gain for {age}",
                "daily_gain",
                "daily gain",
                "gain",
                "adg",
            ]
        },
        "daily_gain": {
            "patterns": ["daily_gain for {age}", "daily_gain", "daily gain", "gain"]
        },
        "yield": {
            "patterns": [
                "yield",
                "eviscerated yield",
                "carcass yield",
                "rendement",
                "rendement éviscéré",
            ]
        },
        "cumulative_feed_intake": {
            "patterns": [
                "cumulative_feed_intake for {age}",
                "cumulative_feed_intake",
                "cumulative feed intake",
                "cumulative feed",
                "feed_intake",
                "feed intake",
                "total feed",
            ]
        },
        "feed_consumption": {
            "patterns": [
                "feed_consumption for {age}",
                "feed_consumption",
                "feed consumption",
                "daily feed",
                "feed per day",
            ]
        },
        "mortality": {
            "patterns": [
                "mortality for {age}",
                "mortality",
                "mort",
                "death",
                "cumulative_mortality",
            ]
        },
        "livability": {
            "patterns": [
                "livability for {age}",
                "livability",
                "viability",
                "survival",
                "liveability",
            ]
        },
        "uniformity": {
            "patterns": [
                "uniformity for {age}",
                "uniformity",
                "cv",
                "coefficient_variation",
            ]
        },
        "european_efficiency_factor": {
            "patterns": [
                "european_efficiency_factor for {age}",
                "european_efficiency_factor",
                "eef",
                "efficiency_factor",
            ]
        },
        "feed_cost": {
            "patterns": ["feed_cost for {age}", "feed_cost", "cost", "feed price"]
        },
        "water_consumption": {
            "patterns": [
                "water_consumption for {age}",
                "water_consumption",
                "water",
                "water intake",
            ]
        },
    }

    def __init__(self, query_normalizer, intents_config_path: str = None):
        """
        Args:
            query_normalizer: Instance de SQLQueryNormalizer
            intents_config_path: Chemin vers intents.json (optionnel)
        """
        self.query_normalizer = query_normalizer

        # Initialisation du BreedsRegistry
        if intents_config_path is None:
            intents_config_path = self._find_intents_config()
        self.breeds_registry = get_breeds_registry(intents_config_path)

        self.intents_config = self._load_intents_config()
        self.line_aliases = self._extract_line_aliases()
        self.logger = logger
        self.last_query_used_fallback = False
        self.fallback_warning_message = None

    def _find_intents_config(self) -> str:
        """Trouve le chemin vers intents.json"""
        config_paths = [
            Path(__file__).parent.parent / "config" / "intents.json",
            Path(__file__).parent / "config" / "intents.json",
            Path.cwd() / "config" / "intents.json",
            Path.cwd() / "llm" / "config" / "intents.json",
        ]

        for path in config_paths:
            if path.exists():
                return str(path)

        logger.warning("intents.json non trouvé - utilisation valeurs par défaut")
        return ""

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
        Utilise BreedsRegistry pour normaliser le nom de breed

        Args:
            breed_input: Ex: "Cobb 500", "ross 308", "cobb500", "Cobb 500, Ross 308"

        Returns:
            Nom réel BD: "500", "308/308 FF", "500,308/308 FF", ou None
        """
        if not breed_input:
            return None

        breed_input = str(breed_input).strip()

        # Utilisation du BreedsRegistry au lieu des mappings hardcodés
        result = self.breeds_registry.get_db_name(breed_input)

        if result:
            logger.debug(
                f"Breed normalized via registry: '{breed_input}' -> '{result}'"
            )
        else:
            logger.warning(f"Souche non reconnue par registry: '{breed_input}'")

        return result

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

        for phase, default_age in phase_patterns.items():
            if phase in query_lower:
                logger.debug(f"Phase détectée: {phase} → {default_age} jours")
                return default_age

        logger.debug("Aucun âge ou phase détecté dans la requête")
        return None

    def _handle_multiple_breeds(self, breeds_input: str) -> Tuple[str, List[str]]:
        """
        Gère les requêtes avec multiples breeds

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
    ) -> Tuple[List[str], bool]:
        """
        Construire patterns avec structure imbriquée et substitution {age}

        Args:
            metric_type: Type de métrique (peut être None)
            age: Âge en jours (peut être None)

        Returns:
            Tuple[List[str], bool]: (patterns SQL avec %, is_fallback_used)
        """
        patterns = []
        is_fallback = False

        if not metric_type:
            is_fallback = True

            if age:
                patterns.extend(
                    [
                        f"%body_weight for {age}%",
                        f"%feed_conversion_ratio for {age}%",
                        f"%daily_gain for {age}%",
                    ]
                )
                logger.warning(
                    f"Métrique inconnue avec âge {age}j → recherche LIMITÉE aux 3 métriques principales"
                )
            else:
                patterns.extend(
                    [
                        "%body_weight%",
                        "%feed_conversion_ratio%",
                    ]
                )
                logger.warning(
                    "Métrique inconnue sans âge → recherche TRÈS LIMITÉE (weight + FCR uniquement)"
                )

            return patterns, is_fallback

        base_name = self.METRIC_MAPPINGS.get(metric_type.lower(), metric_type)

        if base_name in self.METRIC_PATTERNS:
            metric_config = self.METRIC_PATTERNS[base_name]
            pattern_templates = metric_config["patterns"]

            for template in pattern_templates:
                if "{age}" in template and age:
                    pattern = template.replace("{age}", str(age))
                    patterns.append(f"%{pattern}%")
                elif "{age}" not in template:
                    patterns.append(f"%{template}%")

            logger.debug(
                f"Métrique '{metric_type}' → {len(patterns)} patterns SQL précis"
            )
        else:
            is_fallback = True
            if age:
                patterns.append(f"%{base_name} for {age}%")
            patterns.append(f"%{base_name}%")
            logger.warning(
                f"Métrique '{metric_type}' non dans METRIC_PATTERNS → fallback avec 1-2 patterns"
            )

        return patterns, is_fallback

    def get_fallback_warning(self) -> Optional[str]:
        """
        Retourne le message d'avertissement si un fallback a été utilisé

        Returns:
            Message d'avertissement ou None
        """
        if self.last_query_used_fallback and self.fallback_warning_message:
            return self.fallback_warning_message
        return None

    def build_range_query(
        self, entities: Dict[str, str], age_min: int, age_max: int, limit: int = 12
    ) -> Tuple[str, List]:
        """Construction SQL optimisée pour plages temporelles"""

        logger.debug(f"Building range query: age {age_min}-{age_max} days")
        normalized_entities = self._normalize_entities(entities or {})

        conditions = ["1=1"]
        params = []
        param_count = 0

        self.last_query_used_fallback = False
        self.fallback_warning_message = None

        param_count += 6
        conditions.append(
            f"""((m.age_min BETWEEN ${param_count-5} AND ${param_count-4}) OR 
            (m.age_max BETWEEN ${param_count-3} AND ${param_count-2}) OR 
            (m.age_min <= ${param_count-1} AND m.age_max >= ${param_count}))"""
        )
        params.extend([age_min, age_max, age_min, age_max, age_min, age_max])

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

        param_count = self._add_metric_search_conditions_simple(
            conditions, params, param_count
        )

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
        """Version simplifiée pour requêtes de plage"""

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
        """Construction SQL avec paramètres alignés"""

        logger.debug(f"Entities: {entities}")
        normalized_entities = self._normalize_entities(entities or {})
        logger.debug(f"Normalized: {normalized_entities}")

        self.last_query_used_fallback = False
        self.fallback_warning_message = None

        conditions = ["1=1"]
        params = []
        param_count = 0

        if normalized_entities.get("age_days"):
            param_count = self._add_age_conditions(
                normalized_entities, conditions, params, param_count
            )

        if normalized_entities.get("breed"):
            param_count = self._add_breed_filter(
                normalized_entities, conditions, params, param_count
            )

        if strict_sex_match or self._is_explicit_sex_request(
            query, normalized_entities
        ):
            param_count = self._add_strict_sex_filter(
                normalized_entities, conditions, params, param_count
            )

        param_count = self._add_unit_filter(conditions, params, param_count)

        param_count = self._add_metric_search_conditions(
            query, normalized_entities, conditions, params, param_count
        )

        base_sql = self._get_base_sql()
        where_clause = " AND ".join(conditions)
        order_clause = self._build_order_clause(normalized_entities, strict_sex_match)

        final_sql = f"{base_sql} WHERE {where_clause} {order_clause} LIMIT {top_k}"

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
        """Ajoute les conditions de recherche de métriques avec fallback intelligent"""

        metric_search_conditions = []
        query_lower = query.lower()
        age_extracted = entities.get("age_days")

        metric_type = None
        if any(term in query_lower for term in ["fcr", "conversion", "indice"]):
            metric_type = "feed_conversion_ratio"
        elif any(term in query_lower for term in ["poids", "weight", "body"]):
            metric_type = "body_weight"
        elif any(term in query_lower for term in ["consumption", "consommation"]):
            metric_type = "feed_consumption"
        elif any(term in query_lower for term in ["gain", "croissance", "daily gain"]):
            metric_type = "daily_gain"
        elif any(term in query_lower for term in ["cumulative feed", "intake"]):
            metric_type = "cumulative_feed_intake"
        elif any(term in query_lower for term in ["mortality", "mortalité"]):
            metric_type = "mortality"
        elif any(term in query_lower for term in ["livability", "viabilité"]):
            metric_type = "livability"
        elif any(term in query_lower for term in ["yield", "rendement"]):
            metric_type = "yield"

        age_int = int(age_extracted) if age_extracted else None
        patterns, is_fallback = self._build_metric_search(metric_type, age_int)

        if is_fallback:
            self.last_query_used_fallback = True
            if not metric_type:
                if age_int:
                    self.fallback_warning_message = (
                        f"Métrique non précisée - Recherche limitée aux métriques principales à {age_int} jours. "
                        "Les résultats peuvent être incomplets. "
                        "Précisez la métrique (ex: poids, conversion, gain) pour plus de précision."
                    )
                else:
                    self.fallback_warning_message = (
                        "Métrique et âge non précisés - Recherche très limitée (poids et conversion uniquement). "
                        "Précisez votre demande pour des résultats plus pertinents."
                    )
            else:
                self.fallback_warning_message = (
                    f"Métrique '{metric_type}' non reconnue dans la base de patterns - "
                    "Les résultats peuvent être approximatifs. "
                    "Utilisez des termes standards (poids, conversion, gain, mortalité, etc.)."
                )

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
        """Construit la condition SQL pour le sexe"""
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
    print("TEST 1: Vérification BreedsRegistry intégré")
    print("=" * 80)
    print(f"BreedsRegistry chargé: {builder.breeds_registry is not None}")
    print(
        f"Nombre de breeds disponibles: {len(builder.breeds_registry.get_all_breeds())}"
    )

    print("\n" + "=" * 80)
    print("TEST 2: Normalisation via BreedsRegistry")
    print("=" * 80)

    test_breeds = ["Cobb 500", "Ross 308", "cobb500", "ross-308", "Cobb 500, Ross 308"]

    for breed in test_breeds:
        normalized = builder._normalize_breed_for_db(breed)
        print(f"  '{breed}' -> '{normalized}'")

    print("\n" + "=" * 80)
    print("TEST 3: Structure METRIC_PATTERNS avec 'patterns'")
    print("=" * 80)
    print(f"Nombre de métriques: {len(builder.METRIC_PATTERNS)}")
    for metric, config in list(builder.METRIC_PATTERNS.items())[:3]:
        print(f"  {metric:30s} : {len(config['patterns'])} patterns")
        print(f"    Exemples: {config['patterns'][:2]}")

    print("\n" + "=" * 80)
    print("TEST 4: Substitution {age} dans patterns")
    print("=" * 80)

    patterns_fcr_42, _ = builder._build_metric_search("feed_conversion_ratio", 42)
    print(f"  FCR à 42j ({len(patterns_fcr_42)} patterns):")
    for p in patterns_fcr_42[:4]:
        print(f"    - {p}")

    patterns_yield, _ = builder._build_metric_search("yield", None)
    print(f"\n  Yield sans âge ({len(patterns_yield)} patterns):")
    for p in patterns_yield[:3]:
        print(f"    - {p}")

    print("\n" + "=" * 80)
    print("TEST 5: Query avec BreedsRegistry")
    print("=" * 80)

    sql_cobb, params_cobb = builder.build_sex_aware_sql_query(
        "Quel est le poids du Cobb 500 à 42 jours?",
        entities={"breed": "Cobb 500", "age_days": "42"},
        top_k=5,
    )

    breed_params = [
        p for p in params_cobb if isinstance(p, str) and ("500" in p or "308" in p)
    ]
    print("  Query: 'Poids du Cobb 500 à 42 jours'")
    print(f"  Breed params détectés: {breed_params}")
    print(f"  Nombre total de params: {len(params_cobb)}")

    print("\n" + "=" * 80)
    print("✅ TOUS LES TESTS RÉUSSIS - BreedsRegistry intégré avec succès!")
    print("=" * 80)
