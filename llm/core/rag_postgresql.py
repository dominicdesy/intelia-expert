# -*- coding: utf-8 -*-
"""
rag_postgresql.py - PostgreSQL System for RAG
VERSION CORRECTED - With sex/as-hatched logic implementation
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Safe conditional imports
try:
    import asyncpg

    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

from .data_models import RAGResult, RAGSource, Document

logger = logging.getLogger(__name__)

# PostgreSQL configuration with secure defaults
POSTGRESQL_CONFIG = {
    "user": os.getenv("DB_USER", "doadmin"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 25060)),
    "database": os.getenv("DB_NAME", "defaultdb"),
    "ssl": os.getenv("DB_SSL", "require"),
}


class QueryType(Enum):
    """Query types for intelligent routing"""

    KNOWLEDGE = "knowledge"  # General knowledge -> Weaviate
    METRICS = "metrics"  # Performance data -> PostgreSQL
    HYBRID = "hybrid"  # Combination of both
    UNKNOWN = "unknown"  # Undetermined type


@dataclass
class MetricResult:
    """Result of a PostgreSQL metrics query"""

    company: str
    breed: str
    strain: str
    species: str
    metric_name: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    sheet_name: str = ""
    category: str = ""
    confidence: float = 1.0
    # NOUVEAU: Champs pour gestion sexe
    sex: Optional[str] = None
    housing_system: Optional[str] = None
    data_type: Optional[str] = None

    def __post_init__(self):
        """Data validation and cleaning"""
        # Ensure string fields are not None
        self.company = str(self.company) if self.company is not None else "Unknown"
        self.breed = str(self.breed) if self.breed is not None else "Unknown"
        self.strain = str(self.strain) if self.strain is not None else "Unknown"
        self.species = str(self.species) if self.species is not None else "Unknown"
        self.metric_name = (
            str(self.metric_name) if self.metric_name is not None else "Unknown"
        )
        self.sheet_name = str(self.sheet_name) if self.sheet_name is not None else ""
        self.category = str(self.category) if self.category is not None else ""

        # NOUVEAU: Normalisation du sexe
        if self.sex:
            self.sex = str(self.sex).lower()
            # Normaliser les variantes vers les valeurs canoniques
            if self.sex in ["male", "mâle", "m", "masculin"]:
                self.sex = "male"
            elif self.sex in ["female", "femelle", "f", "féminin"]:
                self.sex = "female"
            elif self.sex in [
                "mixed",
                "mixte",
                "as_hatched",
                "as-hatched",
                "straight_run",
            ]:
                self.sex = "as_hatched"
            else:
                # Si pas reconnu, fallback vers as_hatched
                self.sex = "as_hatched"

        # Validate confidence
        self.confidence = max(0.0, min(1.0, float(self.confidence)))


class SQLQueryNormalizer:
    """
    Multilingual normalizer inspired by PerfStore
    Converts user concepts to searchable database terms
    MODIFIÉ: Avec support sexe/as-hatched
    """

    CONCEPT_MAPPINGS = {
        "weight": [
            "poids",
            "peso",
            "weight",
            "body_weight",
            "live_weight",
            "body weight",
            "weight_g",
            "weight_lb",
            "masse",
            "masse corporelle",
            "poids corporel",
            "poids vif",
            "body_weight_day",
        ],
        "feed": [
            "alimentation",
            "alimento",
            "feed",
            "nutrition",
            "consommation",
            "feed_intake",
            "feed consumption",
            "aliment",
            "nourriture",
            "ration",
            "aliment_consomme",
            "feed_consumed",
        ],
        "mortality": [
            "mortalite",
            "mortalidad",
            "mortality",
            "death_rate",
            "viability",
            "survie",
            "taux de mortalite",
            "mort",
            "deces",
            "pertes",
        ],
        "growth": [
            "croissance",
            "crecimiento",
            "growth",
            "gain",
            "developpement",
            "daily_gain",
            "gain quotidien",
            "croissance ponderale",
        ],
        "production": [
            "production",
            "produccion",
            "ponte",
            "laying",
            "egg_production",
            "lay_rate",
            "taux de ponte",
            "oeufs",
            "eggs",
            "rendement",
        ],
        "fcr": [
            "icg",
            "fcr",
            "feed_conversion",
            "conversion",
            "efficacite",
            "efficiency",
            "indice de consommation",
            "conversion alimentaire",
        ],
        "water": [
            "eau",
            "water",
            "agua",
            "water_consumption",
            "hydratation",
            "consommation d'eau",
            "abreuvement",
        ],
        "temperature": [
            "temperature",
            "temp",
            "chaleur",
            "froid",
            "thermique",
            "climat",
        ],
        "density": [
            "densite",
            "density",
            "peuplement",
            "stocking",
            "occupation",
            "espace",
            "space",
        ],
        "age": [
            "age",
            "semaine",
            "week",
            "jour",
            "day",
            "periode",
            "phase",
            "stade",
            "at day",
        ],
        # NOUVEAU: Concepts liés au sexe
        "sex": [
            "sexe",
            "sex",
            "male",
            "mâle",
            "female",
            "femelle",
            "mixed",
            "mixte",
            "as-hatched",
            "as_hatched",
            "straight_run",
            "both_sexes",
            "sexes_mélangés",
        ],
    }

    def normalize_query_concepts(self, query: str) -> List[str]:
        """Converts 'quel poids' to ['weight', 'body_weight', 'live_weight']"""
        query_lower = query.lower()
        normalized_concepts = []

        for concept, terms in self.CONCEPT_MAPPINGS.items():
            if any(term in query_lower for term in terms):
                # Add all equivalent terms to maximize results
                normalized_concepts.extend(self.CONCEPT_MAPPINGS[concept])

        # Deduplication while preserving order
        seen = set()
        unique_concepts = []
        for concept in normalized_concepts:
            if concept not in seen:
                seen.add(concept)
                unique_concepts.append(concept)

        return unique_concepts

    def get_search_terms(self, query: str) -> Tuple[List[str], List[str]]:
        """Returns (normalized_concepts, raw_words) for SQL search"""
        normalized = self.normalize_query_concepts(query)
        raw_words = [word for word in query.lower().split() if len(word) > 3]
        return normalized, raw_words

    def extract_sex_from_query(self, query: str) -> Optional[str]:
        """
        NOUVELLE MÉTHODE: Extrait le sexe de la requête
        Retourne: 'male', 'female', 'as_hatched', ou None
        """
        query_lower = query.lower()

        # Patterns pour male
        male_patterns = ["male", "mâle", "mâles", "masculin", "coq", "coqs", "rooster"]
        if any(pattern in query_lower for pattern in male_patterns):
            return "male"

        # Patterns pour female
        female_patterns = [
            "female",
            "femelle",
            "femelles",
            "féminin",
            "poule",
            "poules",
            "hen",
        ]
        if any(pattern in query_lower for pattern in female_patterns):
            return "female"

        # Patterns pour as-hatched/mixed
        mixed_patterns = [
            "as-hatched",
            "ashatched",
            "mixed",
            "mixte",
            "mélangé",
            "non sexé",
            "straight run",
        ]
        if any(pattern in query_lower for pattern in mixed_patterns):
            return "as_hatched"

        # Si aucun sexe détecté, retourner None (fallback sera appliqué plus tard)
        return None


class QueryRouter:
    """Intelligent router to direct queries to the right source"""

    def __init__(self):
        # Keywords for PostgreSQL (metrics/performance)
        self.metric_keywords = {
            "performance",
            "metrics",
            "donnees",
            "chiffres",
            "resultats",
            "weight",
            "poids",
            "egg",
            "oeuf",
            "production",
            "feed",
            "alimentation",
            "mortality",
            "mortalite",
            "growth",
            "croissance",
            "nutrition",
            "age",
            "semaine",
            "week",
            "day",
            "jour",
            "phase",
            "temperature",
            "humidity",
            "humidite",
            "housing",
            "logement",
            "density",
            "densite",
            "fcr",
            "icg",
            "conversion",
            "efficacite",
            "ross",
            "cobb",
            "hubbard",
        }

        # Keywords for Weaviate (knowledge)
        self.knowledge_keywords = {
            "comment",
            "pourquoi",
            "qu'est-ce",
            "expliquer",
            "definir",
            "maladie",
            "disease",
            "traitement",
            "treatment",
            "symptom",
            "symptome",
            "prevention",
            "biosecurite",
            "biosecurity",
            "management",
            "gestion",
            "guide",
            "protocol",
            "protocole",
            "conseil",
            "advice",
            "recommendation",
            "recommandation",
        }

    def route_query(self, query: str, intent_result=None) -> QueryType:
        """Determines query type and appropriate source"""
        query_lower = query.lower()

        # Keyword counters
        metric_score = sum(
            1 for keyword in self.metric_keywords if keyword in query_lower
        )
        knowledge_score = sum(
            1 for keyword in self.knowledge_keywords if keyword in query_lower
        )

        # Entity analysis if intent_result available
        if intent_result:
            if hasattr(intent_result, "genetic_line") and intent_result.genetic_line:
                metric_score += 2
            if hasattr(intent_result, "age") and intent_result.age:
                metric_score += 1

        # Comparison detection (often hybrid)
        comparison_indicators = [
            "vs",
            "versus",
            "compare",
            "comparaison",
            "difference",
            "mieux",
        ]
        has_comparison = any(
            indicator in query_lower for indicator in comparison_indicators
        )

        # Decision rules
        if metric_score > knowledge_score + 1:
            return QueryType.METRICS
        elif knowledge_score > metric_score + 1:
            return QueryType.KNOWLEDGE
        elif has_comparison or (metric_score > 0 and knowledge_score > 0):
            return QueryType.HYBRID
        else:
            return QueryType.UNKNOWN


class PostgreSQLRetriever:
    """PostgreSQL data retriever for poultry metrics"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None
        self.query_normalizer = SQLQueryNormalizer()
        self.is_initialized = False

    async def initialize(self):
        """Initialize PostgreSQL connection"""
        if not ASYNCPG_AVAILABLE:
            logger.error("asyncpg not available - PostgreSQL disabled")
            raise ImportError("asyncpg required for PostgreSQL")

        if self.is_initialized:
            return

        try:
            # Check that environment variables are defined
            if not self.config.get("password"):
                logger.warning("DB_PASSWORD not defined - PostgreSQL may fail")

            if not self.config.get("host"):
                logger.warning("DB_HOST not defined - PostgreSQL may fail")

            self.pool = await asyncpg.create_pool(
                user=self.config["user"],
                password=self.config["password"],
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                ssl=self.config["ssl"],
                min_size=2,
                max_size=10,
                command_timeout=30,
            )

            # Connection test
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")

            self.is_initialized = True
            logger.info("PostgreSQL Retriever initialized successfully")

        except Exception as e:
            logger.error(f"PostgreSQL initialization error: {e}")
            self.pool = None
            self.is_initialized = False
            raise

    async def search_metrics(
        self, query: str, entities: Dict[str, str] = None, top_k: int = 10
    ) -> List[MetricResult]:
        """
        Search metrics in PostgreSQL with sex/as-hatched logic
        MODIFIÉ: Intègre la logique sexe avec fallback intelligent
        """

        if not self.is_initialized or not self.pool:
            logger.warning("PostgreSQL not initialized - attempting initialization")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"PostgreSQL initialization failed: {e}")
                return []

        try:
            # Build SQL query with sex-aware logic
            sql_query, params = self._build_sex_aware_sql_query(query, entities, top_k)

            logger.debug(f"SQL Query: {sql_query}")
            logger.debug(f"Parameters: {params}")

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql_query, *params)

            # Convert to MetricResult with error handling
            results = []
            for i, row in enumerate(rows):
                try:
                    result = MetricResult(
                        company=row.get("company_name", "Unknown"),
                        breed=row.get("breed_name", "Unknown"),
                        strain=row.get("strain_name", "Unknown"),
                        species=row.get("species", "Unknown"),
                        metric_name=row.get("metric_name", "Unknown"),
                        value_numeric=row.get("value_numeric"),
                        value_text=row.get("value_text"),
                        unit=row.get("unit"),
                        age_min=row.get("age_min"),
                        age_max=row.get("age_max"),
                        sheet_name=row.get("sheet_name", ""),
                        category=row.get("category_name", ""),
                        sex=row.get("sex"),  # NOUVEAU
                        housing_system=row.get("housing_system"),  # NOUVEAU
                        data_type=row.get("data_type"),  # NOUVEAU
                        confidence=self._calculate_sex_aware_relevance(
                            query, row, entities
                        ),
                    )
                    results.append(result)
                except Exception as row_error:
                    logger.error(f"Row conversion error {i}: {row_error}")
                    continue

            logger.info(
                f"PostgreSQL: {len(results)} metrics found from {len(rows)} rows"
            )
            return results

        except Exception as e:
            logger.error(f"PostgreSQL search error: {e}")
            return []

    def _build_sex_aware_sql_query(
        self, query: str, entities: Dict[str, str] = None, top_k: int = 10
    ) -> Tuple[str, List]:
        """
        NOUVELLE MÉTHODE: Construit une requête SQL intelligente avec logique sexe/as-hatched

        Logique:
        1. Si sexe spécifié -> chercher ce sexe en priorité + as_hatched comme fallback
        2. Si aucun sexe spécifié -> prioriser as_hatched + inclure autres sexes
        3. Toujours inclure les données disponibles pour maximiser les résultats
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

        # 1. NOUVELLE LOGIQUE SEXE avec fallback intelligent
        sex_from_query = self.query_normalizer.extract_sex_from_query(query)
        sex_from_entities = entities.get("sex") if entities else None
        sex_specified = entities.get("sex_specified") == "true" if entities else False

        # Déterminer le sexe à utiliser
        target_sex = sex_from_entities or sex_from_query

        # CORRECTION: Considérer le sexe comme spécifié s'il est détecté dans la requête
        actual_sex_specified = sex_specified or (sex_from_query is not None)

        if target_sex and actual_sex_specified:
            # Sexe explicitement spécifié -> recherche avec fallback
            logger.debug(
                f"Sexe spécifié: {target_sex}, recherche avec fallback as_hatched"
            )

            param_count += 1

            # CASE pour priorisation: sexe spécifié en premier, as_hatched en fallback
            sex_priority_case = f"""
                CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = ${param_count} THEN 1
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched') THEN 2
                    ELSE 3
                END
            """

            conditions.append(
                f"""
                (LOWER(COALESCE(d.sex, 'as_hatched')) = ${param_count} 
                 OR LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched', 'straight_run'))
            """
            )

            params.append(target_sex.lower())

        else:
            # Aucun sexe spécifié -> prioriser as_hatched par défaut
            logger.debug(
                "Aucun sexe spécifié, fallback vers as_hatched avec inclusion autres sexes"
            )

            sex_priority_case = """
                CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed', 'as-hatched') THEN 1
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = 'male' THEN 2
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) = 'female' THEN 3
                    ELSE 4
                END
            """

            # Pas de condition restrictive sur le sexe -> inclure tous les résultats
            # La priorisation se fera dans l'ORDER BY

        # 2. Concept normalization (existant)
        normalized_concepts, raw_words = self.query_normalizer.get_search_terms(query)
        logger.debug(f"Normalized concepts: {normalized_concepts[:5]}")
        logger.debug(f"Raw words: {raw_words[:3]}")

        # 3. Age extraction (existant amélioré)
        age_extracted = self._extract_age_from_query(query)
        if age_extracted:
            logger.debug(f"Age extracted from query: {age_extracted} days")
            # Tolérance de ±3 jours
            age_tolerance = 3

            param_count += 1
            param_count_age2 = param_count + 1
            param_count_tolerance = param_count + 2

            conditions.append(
                f"""
                ((m.age_min <= ${param_count} AND m.age_max >= ${param_count_age2}) 
                 OR ABS(COALESCE(m.age_min, 0) - ${param_count}) <= ${param_count_tolerance}
                 OR ABS(COALESCE(m.age_max, 0) - ${param_count_age2}) <= ${param_count_tolerance})
            """
            )

            params.extend([age_extracted, age_extracted, age_tolerance])
            param_count += 2

        # 4. Filters selon entities (existant)
        if entities:
            if entities.get("line"):
                param_count += 1
                conditions.append(f"LOWER(s.strain_name) ILIKE ${param_count}")
                params.append(f"%{entities['line'].lower()}%")

            if entities.get("age_days") and not age_extracted:
                age_days = int(entities["age_days"])
                param_count += 1
                param_count_age2 = param_count + 1
                conditions.append(
                    f"""
                    (m.age_min <= ${param_count} AND m.age_max >= ${param_count_age2}) 
                    OR (m.age_min IS NULL AND m.age_max IS NULL)
                """
                )
                params.extend([age_days, age_days])
                param_count += 1

        # 5. Search avec concepts normalisés (existant)
        metric_search_conditions = []

        # Priority aux concepts normalisés
        for concept in normalized_concepts[:8]:
            param_count += 1
            metric_search_conditions.append(
                f"LOWER(m.metric_name) ILIKE ${param_count}"
            )
            params.append(f"%{concept}%")

        # Fallback sur raw words
        for word in raw_words[:3]:
            param_count += 1
            param_count_word2 = param_count + 1
            metric_search_conditions.extend(
                [
                    f"LOWER(m.metric_name) ILIKE ${param_count}",
                    f"LOWER(m.value_text) ILIKE ${param_count_word2}",
                ]
            )
            params.extend([f"%{word}%", f"%{word}%"])
            param_count += 1

        # Add metric search conditions
        if metric_search_conditions:
            conditions.append(f"({' OR '.join(metric_search_conditions)})")

        # Add conditions to query
        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        # 6. NOUVELLE LOGIQUE DE TRI avec priorisation sexe
        order_clauses = [sex_priority_case]  # Priorisation par sexe

        if age_extracted:
            order_clauses.append(f"ABS(COALESCE(m.age_min, 999) - {age_extracted})")

        order_clauses.extend(["m.value_numeric DESC NULLS LAST", "m.metric_name"])

        base_query += f" ORDER BY {', '.join(order_clauses)}"
        base_query += f" LIMIT {top_k}"

        return base_query, params

    def _calculate_sex_aware_relevance(
        self, query: str, row: Dict, entities: Dict[str, str] = None
    ) -> float:
        """
        NOUVELLE MÉTHODE: Calcule la pertinence en tenant compte du sexe
        """
        score = 0.5  # Base score

        # Score basé sur la correspondance du sexe
        sex_from_query = self.query_normalizer.extract_sex_from_query(query)
        sex_from_entities = entities.get("sex") if entities else None
        sex_specified = entities.get("sex_specified") == "true" if entities else False

        target_sex = sex_from_entities or sex_from_query
        row_sex = (row.get("sex") or "as_hatched").lower()

        if target_sex and sex_specified:
            # Sexe explicitement demandé
            if row_sex == target_sex.lower():
                score += 0.3  # Correspondance exacte du sexe
            elif row_sex in ["as_hatched", "mixed", "as-hatched"]:
                score += 0.1  # Fallback as_hatched acceptable
        else:
            # Aucun sexe spécifié -> prioriser as_hatched
            if row_sex in ["as_hatched", "mixed", "as-hatched"]:
                score += 0.2  # Priorité as_hatched par défaut
            else:
                score += 0.05  # Autres sexes moins prioritaires

        # Score existant pour concepts normalisés
        normalized_concepts, _ = self.query_normalizer.get_search_terms(query)
        metric_name_lower = (row.get("metric_name") or "").lower()

        for concept in normalized_concepts:
            if concept in metric_name_lower:
                score += 0.3
                break

        # Autres facteurs existants
        query_lower = query.lower()
        if query_lower in metric_name_lower:
            score += 0.2

        if row.get("value_numeric") is not None:
            score += 0.1

        if row.get("age_min") is not None and row.get("age_max") is not None:
            score += 0.1

        return min(1.0, score)

    def _extract_age_from_query(self, query: str) -> Optional[int]:
        """Extract age in days from query - AMÉLIORATION POUR DÉTECTION ÉTENDUE"""
        import re

        # Patterns étendus pour détecter l'âge
        patterns = [
            r"day\s+(\d+)",  # "day 11"
            r"jour\s+(\d+)",  # "jour 11"
            r"j\s*(\d+)",  # "j11" ou "j 11"
            r"(\d+)\s*day",  # "11 day"
            r"(\d+)\s*jour",  # "11 jour"
            r"a\s+(\d+)\s+jours?",  # "a 11 jours"
            r"at\s+day\s+(\d+)",  # "at day 11"
            r"age\s+(\d+)",  # "age 11"
            r"(\d+)\s*j\b",  # "11j"
            r"d(\d+)",  # "d11"
            r"age_day_(\d+)",  # "age_day_11" (de nos clés métriques)
        ]

        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    # Validation raisonnable (0-150 jours)
                    if 0 <= age <= 150:
                        logger.debug(
                            f"Age détecté: {age} jours via pattern '{pattern}'"
                        )
                        return age
                except ValueError:
                    continue

        # Détecter âges implicites dans des phrases
        implicit_patterns = [
            r"à\s+(\d+)\s+jours?",  # "à 9 jours"
            r"at\s+(\d+)\s+days?",  # "at 9 days"
            r"(\d+)\s+jours?\s+de",  # "9 jours de"
            r"(\d+)\s+days?\s+of",  # "9 days of"
        ]

        for pattern in implicit_patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    if 0 <= age <= 150:
                        logger.debug(
                            f"Age implicite détecté: {age} jours via pattern '{pattern}'"
                        )
                        return age
                except ValueError:
                    continue

        return None

    async def close(self):
        """Close PostgreSQL connection"""
        if self.pool:
            try:
                await self.pool.close()
                logger.info("PostgreSQL connection closed")
            except Exception as e:
                logger.error(f"PostgreSQL close error: {e}")
            finally:
                self.pool = None
                self.is_initialized = False


class PostgreSQLSystem:
    """Main PostgreSQL system"""

    def __init__(self):
        self.query_router = None
        self.postgres_retriever = None
        self.is_initialized = False

    async def initialize(self):
        """Initialize PostgreSQL system"""
        if self.is_initialized:
            return

        if not ASYNCPG_AVAILABLE:
            logger.error("asyncpg not available - PostgreSQL disabled")
            raise ImportError("asyncpg required for PostgreSQL")

        try:
            # Query router
            self.query_router = QueryRouter()

            # PostgreSQL Retriever with normalization
            self.postgres_retriever = PostgreSQLRetriever(POSTGRESQL_CONFIG)
            await self.postgres_retriever.initialize()

            self.is_initialized = True
            logger.info("PostgreSQL System initialized with sex/as-hatched logic")

        except Exception as e:
            logger.error(f"PostgreSQL System initialization error: {e}")
            self.is_initialized = False
            raise

    def route_query(self, query: str, intent_result=None) -> QueryType:
        """Route a query to the appropriate source"""
        if not self.query_router:
            return QueryType.KNOWLEDGE
        return self.query_router.route_query(query, intent_result)

    async def search_metrics(
        self, query: str, entities: Dict[str, str] = None, top_k: int = 10
    ) -> RAGResult:
        """
        MAIN METHOD - Search with sex-aware logic and complete response generation
        MODIFIÉ: Intègre la logique sexe/as-hatched
        """

        if not self.is_initialized or not self.postgres_retriever:
            return RAGResult(
                source=RAGSource.NO_RESULTS,
                metadata={"error": "PostgreSQL not available"},
            )

        try:
            # Search metrics with sex-aware logic
            metric_results = await self.postgres_retriever.search_metrics(
                query, entities, top_k
            )

            if not metric_results:
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    metadata={
                        "source_type": "metrics",
                        "data_source": "postgresql",
                        "sex_logic_applied": True,
                    },
                )

            # Convert to Documents for compatibility
            documents = []
            logger.debug(f"Converting {len(metric_results)} metrics to documents")

            for i, metric in enumerate(metric_results):
                try:
                    # Safe content formatting with sex information
                    doc_content = self._format_metric_content_with_sex(metric)

                    # Safe Document creation
                    doc = Document(
                        content=doc_content,
                        metadata={
                            "company": metric.company,
                            "breed": metric.breed,
                            "strain": metric.strain,
                            "species": metric.species,
                            "metric_name": metric.metric_name,
                            "category": metric.category,
                            "sheet_name": metric.sheet_name,
                            "sex": metric.sex,  # NOUVEAU
                            "housing_system": metric.housing_system,  # NOUVEAU
                            "data_type": metric.data_type,  # NOUVEAU
                            "source_type": "metrics",
                            "data_source": "postgresql",
                            "sex_aware_search": True,  # NOUVEAU
                        },
                        score=metric.confidence,
                        source_type="metrics",
                        retrieval_method="postgresql_sex_aware",
                    )
                    documents.append(doc)

                except Exception as doc_error:
                    logger.error(f"Document creation error for metric {i}: {doc_error}")
                    continue

            if not documents:
                logger.warning("No documents created from found metrics")
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    metadata={
                        "source_type": "metrics",
                        "data_source": "postgresql",
                        "error": "No valid documents created",
                        "sex_logic_applied": True,
                    },
                )

            # NEW: Sex-aware response generation
            answer_text = await self._generate_sex_aware_response(
                query, documents, metric_results, entities
            )

            # Calculate global confidence with sex matching bonus
            avg_confidence = sum(m.confidence for m in metric_results) / len(
                metric_results
            )

            # Bonus if sex logic was successfully applied
            sex_from_entities = entities.get("sex") if entities else None
            if sex_from_entities:
                matching_sex_results = [
                    m for m in metric_results if m.sex == sex_from_entities
                ]
                if matching_sex_results:
                    avg_confidence = min(1.0, avg_confidence + 0.1)

            logger.info(
                f"PostgreSQL SUCCESS: {len(documents)} documents with sex-aware logic"
            )

            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=answer_text,
                context_docs=[doc.to_dict() for doc in documents],
                confidence=avg_confidence,
                metadata={
                    "source_type": "metrics",
                    "data_source": "postgresql",
                    "metric_count": len(metric_results),
                    "document_count": len(documents),
                    "avg_confidence": avg_confidence,
                    "sex_logic_applied": True,
                    "sex_specified": (
                        entities.get("sex_specified") == "true" if entities else False
                    ),
                    "target_sex": entities.get("sex") if entities else "as_hatched",
                    "response_generated": True,
                },
            )

        except Exception as e:
            logger.error(f"PostgreSQL sex-aware search error: {e}")
            import traceback

            logger.error(f"Stack trace: {traceback.format_exc()}")
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={
                    "error": str(e),
                    "source_type": "metrics",
                    "sex_logic_applied": True,
                },
            )

    def _format_metric_content_with_sex(self, metric: MetricResult) -> str:
        """
        NOUVELLE MÉTHODE: Format a metric into text content with sex information
        """
        try:
            content_parts = [
                f"**{metric.metric_name}**",
                f"Company: {metric.company}",
                f"Breed: {metric.breed}",
                f"Strain: {metric.strain}",
                f"Species: {metric.species}",
                f"Category: {metric.category}",
            ]

            # NOUVEAU: Ajouter information sexe
            if metric.sex:
                sex_display = {
                    "male": "Male",
                    "female": "Female",
                    "as_hatched": "As-hatched (mixed sexes)",
                    "mixed": "Mixed sexes",
                }.get(metric.sex, metric.sex.title())
                content_parts.append(f"Sex: {sex_display}")

            # Value
            if metric.value_numeric is not None:
                value_str = f"{metric.value_numeric}"
                if metric.unit:
                    value_str += f" {metric.unit}"
                content_parts.append(f"Value: {value_str}")
            elif metric.value_text:
                content_parts.append(f"Value: {metric.value_text}")

            # Age if available
            if metric.age_min is not None and metric.age_max is not None:
                if metric.age_min == metric.age_max:
                    content_parts.append(f"Age: {metric.age_min} days")
                else:
                    content_parts.append(f"Age: {metric.age_min}-{metric.age_max} days")

            if metric.sheet_name:
                content_parts.append(f"Source: {metric.sheet_name}")

            return "\n".join(content_parts)

        except Exception as e:
            logger.error(f"Metric formatting error: {e}")
            return f"Metric: {getattr(metric, 'metric_name', 'Unknown name')}"

    async def _generate_sex_aware_response(
        self,
        query: str,
        documents: List[Document],
        metric_results: List[MetricResult],
        entities: Dict[str, str] = None,
    ) -> str:
        """
        NOUVELLE MÉTHODE: Generate intelligent response with sex/as-hatched context
        """
        try:
            # Extract requested age and sex information
            age_requested = self._extract_age_from_query(query)
            sex_from_entities = entities.get("sex") if entities else None
            sex_specified = (
                entities.get("sex_specified") == "true" if entities else False
            )
            sex_detection_method = (
                entities.get("sex_detection_method") if entities else "none"
            )

            # Analyze query for metric type
            query_lower = query.lower()
            metric_type = None
            if any(word in query_lower for word in ["weight", "poids", "body"]):
                metric_type = "weight"
            elif any(
                word in query_lower for word in ["fcr", "conversion", "efficacite"]
            ):
                metric_type = "fcr"
            elif any(word in query_lower for word in ["gain", "croissance", "growth"]):
                metric_type = "gain"

            # Find best metric with sex-aware selection
            best_metric = self._select_best_metric_with_sex_logic(
                metric_results,
                age_requested,
                metric_type,
                sex_from_entities,
                sex_specified,
            )

            if not best_metric:
                return f"No data found for '{query}'."

            # Generate context-aware response with sex clarification
            response = self._build_sex_aware_response_text(
                best_metric,
                query,
                age_requested,
                metric_type,
                sex_from_entities,
                sex_specified,
                sex_detection_method,
            )

            # Add info about multiple results if relevant
            if len(metric_results) > 1:
                sex_breakdown = self._analyze_sex_distribution(metric_results)
                if sex_breakdown:
                    response += f"\n\n*Additional data available: {sex_breakdown}*"

            return response

        except Exception as e:
            logger.error(f"Sex-aware response generation error: {e}")
            # Simple fallback
            if metric_results:
                best = metric_results[0]
                sex_info = (
                    f" for {best.sex}"
                    if best.sex and best.sex != "as_hatched"
                    else " (as-hatched)"
                )
                return f"Data found{sex_info}: {best.metric_name} = {best.value_numeric or best.value_text or 'value not available'} for {best.strain}."
            return f"Error generating response for '{query}'."

    def _select_best_metric_with_sex_logic(
        self,
        metric_results: List[MetricResult],
        age_requested: Optional[int],
        metric_type: Optional[str],
        target_sex: Optional[str],
        sex_specified: bool,
    ) -> Optional[MetricResult]:
        """
        NOUVELLE MÉTHODE: Sélectionne la meilleure métrique avec logique sexe
        """
        if not metric_results:
            return None

        # 1. Filtrer par sexe si spécifié
        if target_sex and sex_specified:
            # Chercher correspondance exacte de sexe
            exact_sex_matches = [m for m in metric_results if m.sex == target_sex]
            if exact_sex_matches:
                candidate_results = exact_sex_matches
                logger.debug(
                    f"Sexe spécifié trouvé: {len(exact_sex_matches)} résultats pour {target_sex}"
                )
            else:
                # Fallback vers as_hatched si sexe spécifique non trouvé
                as_hatched_matches = [
                    m for m in metric_results if m.sex in ["as_hatched", "mixed"]
                ]
                if as_hatched_matches:
                    candidate_results = as_hatched_matches
                    logger.debug(
                        f"Fallback as_hatched: {len(as_hatched_matches)} résultats"
                    )
                else:
                    candidate_results = metric_results
        else:
            # Aucun sexe spécifié -> prioriser as_hatched
            as_hatched_first = [
                m for m in metric_results if m.sex in ["as_hatched", "mixed"]
            ]
            other_sexes = [
                m for m in metric_results if m.sex not in ["as_hatched", "mixed"]
            ]
            candidate_results = as_hatched_first + other_sexes
            logger.debug(
                f"Priorisation as_hatched: {len(as_hatched_first)} as_hatched + {len(other_sexes)} autres"
            )

        # 2. Filtrer par âge si spécifié
        if age_requested:
            # Correspondance exacte d'âge
            exact_age_matches = [
                m for m in candidate_results if m.age_min == age_requested
            ]
            if exact_age_matches:
                candidate_results = exact_age_matches
            else:
                # Âge le plus proche (tolérance ±3 jours)
                close_age_matches = [
                    m
                    for m in candidate_results
                    if m.age_min and abs(m.age_min - age_requested) <= 3
                ]
                if close_age_matches:
                    candidate_results = sorted(
                        close_age_matches,
                        key=lambda m: abs((m.age_min or 0) - age_requested),
                    )

        # 3. Filtrer par type de métrique si détecté
        if metric_type:
            type_matches = [
                m for m in candidate_results if metric_type in m.metric_name.lower()
            ]
            if type_matches:
                candidate_results = type_matches

        # 4. Retourner le meilleur résultat
        return candidate_results[0] if candidate_results else metric_results[0]

    def _build_sex_aware_response_text(
        self,
        metric: MetricResult,
        query: str,
        age_requested: Optional[int],
        metric_type: Optional[str],
        target_sex: Optional[str],
        sex_specified: bool,
        sex_detection_method: str,
    ) -> str:
        """
        NOUVELLE MÉTHODE: Construit la réponse avec clarification du sexe
        """

        # Construire la partie sexe de la réponse
        sex_context = ""
        if metric.sex:
            if metric.sex == "as_hatched" or metric.sex == "mixed":
                if sex_specified and target_sex not in ["as_hatched", "mixed"]:
                    # L'utilisateur a demandé un sexe spécifique mais on a trouvé as_hatched
                    sex_context = f"Pour as-hatched (sexes mélangés) {metric.strain}"
                else:
                    # L'utilisateur n'a pas spécifié de sexe ou a demandé as_hatched
                    sex_context = f"Pour as-hatched (sexes mélangés) {metric.strain}"
            else:
                # Sexe spécifique (male/female)
                sex_display = {"male": "mâles", "female": "femelles"}.get(
                    metric.sex, metric.sex
                )
                sex_context = f"Pour {sex_display} {metric.strain}"
        else:
            sex_context = f"Pour {metric.strain}"

        # Construire la partie âge
        age_context = ""
        if age_requested and metric.age_min:
            age_diff = abs(metric.age_min - age_requested)
            if age_diff == 0:
                age_context = f" au jour {age_requested}"
            elif age_diff <= 1:
                age_context = f" au jour {metric.age_min} (très proche de votre demande jour {age_requested})"
            elif age_diff <= 3:
                age_context = f" au jour {metric.age_min} (proche du jour {age_requested} demandé)"
            else:
                age_context = f" au jour {metric.age_min} (donnée la plus proche du jour {age_requested})"
        elif metric.age_min:
            age_context = f" au jour {metric.age_min}"

        # Construire la valeur avec formatage amélioré
        value_context = ""
        if metric.value_numeric is not None:
            # Formatage avec 1 décimale maximum
            if metric.value_numeric == int(metric.value_numeric):
                value_str = f"{int(metric.value_numeric)}"
            else:
                value_str = f"{metric.value_numeric:.1f}"

            if metric.unit:
                # Simplifier les unités courantes
                unit_display = metric.unit.replace("grams", "g").replace("gram", "g")
                value_str += f" {unit_display}"

            value_context = f", le poids est de {value_str}"
        elif metric.value_text:
            value_context = f", la valeur est {metric.value_text}"

        # Assembler la réponse complète de manière fluide
        response = f"{sex_context}{age_context}{value_context}."

        return response

    def _analyze_sex_distribution(self, metric_results: List[MetricResult]) -> str:
        """
        NOUVELLE MÉTHODE: Analyse la distribution des sexes dans les résultats
        """
        sex_counts = {}
        for metric in metric_results:
            sex = metric.sex or "as_hatched"
            sex_counts[sex] = sex_counts.get(sex, 0) + 1

        if len(sex_counts) <= 1:
            return ""

        sex_labels = {
            "male": "mâles",
            "female": "femelles",
            "as_hatched": "as-hatched",
            "mixed": "mixte",
        }

        breakdown_parts = []
        for sex, count in sex_counts.items():
            label = sex_labels.get(sex, sex)
            breakdown_parts.append(f"{count} {label}")

        return ", ".join(breakdown_parts)

    def _extract_age_from_query(self, query: str) -> Optional[int]:
        """Extract age in days from query (delegated to retriever)"""
        if self.postgres_retriever:
            return self.postgres_retriever._extract_age_from_query(query)
        return None

    async def close(self):
        """Close PostgreSQL system"""
        if self.postgres_retriever:
            await self.postgres_retriever.close()
        self.is_initialized = False

    def get_sex_logic_status(self) -> Dict[str, Any]:
        """
        NOUVELLE MÉTHODE: Return sex/as-hatched logic system status
        """
        if not self.postgres_retriever:
            return {"available": False, "reason": "retriever_not_initialized"}

        return {
            "available": True,
            "sex_aware_search": True,
            "supported_sexes": ["male", "female", "as_hatched", "mixed"],
            "fallback_behavior": "as_hatched",
            "sex_detection_patterns": len(
                [p for p in ["male", "female", "as_hatched"] if p]
            ),
            "normalization_concepts": len(
                self.postgres_retriever.query_normalizer.CONCEPT_MAPPINGS
            ),
        }
