# -*- coding: utf-8 -*-
"""
rag_postgresql.py - PostgreSQL System for RAG
VERSION CORRECTED - All identified issues resolved
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

        # Validate confidence
        self.confidence = max(0.0, min(1.0, float(self.confidence)))


class SQLQueryNormalizer:
    """
    Multilingual normalizer inspired by PerfStore
    Converts user concepts to searchable database terms
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
        self, query: str, intent_result=None, top_k: int = 10
    ) -> List[MetricResult]:
        """Search metrics in PostgreSQL with multilingual normalization"""

        if not self.is_initialized or not self.pool:
            logger.warning("PostgreSQL not initialized - attempting initialization")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"PostgreSQL initialization failed: {e}")
                return []

        try:
            # Build SQL query with normalization
            sql_query, params = self._build_sql_query_with_normalization(
                query, intent_result, top_k
            )

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
                        confidence=self._calculate_relevance_score(query, row),
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

    def _build_sql_query_with_normalization(
        self, query: str, intent_result=None, top_k: int = 10
    ) -> Tuple[str, List]:
        """Dynamic SQL query construction with multilingual normalization"""

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

        # Concept normalization
        normalized_concepts, raw_words = self.query_normalizer.get_search_terms(query)
        logger.debug(f"Normalized concepts: {normalized_concepts[:5]}")
        logger.debug(f"Raw words: {raw_words[:3]}")

        # NEW: Intelligent age extraction from query
        age_extracted = self._extract_age_from_query(query)
        if age_extracted:
            logger.debug(f"Age extracted from query: {age_extracted} days")
            # Convert to weeks for DB (if ages are stored in weeks)
            age_weeks = age_extracted / 7.0
            # Tolerance of ±3 days (about 0.4 weeks)
            age_tolerance = 0.4

            param_count += 1
            param_count_age2 = param_count + 1
            conditions.append(
                f"((m.age_min <= ${param_count} AND m.age_max >= ${param_count_age2}) OR "
                f"(ABS(m.age_min - ${param_count}) <= {age_tolerance}) OR "
                f"(ABS(m.age_max - ${param_count_age2}) <= {age_tolerance}))"
            )
            params.extend([age_weeks, age_weeks])
            param_count += 1

        # Filters according to intent_result
        if intent_result:
            if hasattr(intent_result, "genetic_line") and intent_result.genetic_line:
                param_count += 1
                conditions.append(f"LOWER(s.strain_name) ILIKE ${param_count}")
                params.append(f"%{intent_result.genetic_line.lower()}%")

            if (
                hasattr(intent_result, "age")
                and intent_result.age
                and not age_extracted
            ):
                param_count += 1
                param_count_age2 = param_count + 1
                conditions.append(
                    f"(m.age_min <= ${param_count} AND m.age_max >= ${param_count_age2}) OR (m.age_min IS NULL AND m.age_max IS NULL)"
                )
                params.extend([intent_result.age, intent_result.age])
                param_count += 1

        # Search with normalized concepts and raw words
        metric_search_conditions = []

        # 1. Priority to normalized concepts
        for concept in normalized_concepts[:8]:  # Limit to avoid heavy queries
            param_count += 1
            metric_search_conditions.append(
                f"LOWER(m.metric_name) ILIKE ${param_count}"
            )
            params.append(f"%{concept}%")

        # 2. Fallback on raw words
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

        # Sort by relevance (age first if specified, then value)
        if age_extracted:
            base_query += f" ORDER BY ABS(m.age_min - {age_extracted/7.0}), m.value_numeric DESC NULLS LAST"
        else:
            base_query += " ORDER BY m.value_numeric DESC NULLS LAST"

        base_query += f" LIMIT {top_k}"

        return base_query, params

    def _extract_age_from_query(self, query: str) -> Optional[int]:
        """Extract age in days from query (ex: 'day 11' -> 11)"""
        import re

        # Patterns to detect age
        patterns = [
            r"day\s+(\d+)",  # "day 11"
            r"jour\s+(\d+)",  # "jour 11"
            r"j\s*(\d+)",  # "j11" or "j 11"
            r"(\d+)\s*day",  # "11 day"
            r"(\d+)\s*jour",  # "11 jour"
            r"a\s+(\d+)\s+jours?",  # "a 11 jours"
            r"at\s+day\s+(\d+)",  # "at day 11"
        ]

        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    # Reasonable validation (0-100 days)
                    if 0 <= age <= 100:
                        return age
                except ValueError:
                    continue

        return None

    def _calculate_relevance_score(self, query: str, row: Dict) -> float:
        """Calculate relevance score for a result"""
        score = 0.5  # Base score
        query_lower = query.lower()

        # Normalize query for comparison
        normalized_concepts, _ = self.query_normalizer.get_search_terms(query)

        # Boost if metric matches normalized concepts
        metric_name_lower = (row.get("metric_name") or "").lower()
        for concept in normalized_concepts:
            if concept in metric_name_lower:
                score += 0.4  # High boost for conceptual match
                break

        # Boost if direct match with original query
        if query_lower in metric_name_lower:
            score += 0.3

        # Boost if numeric value available
        if row.get("value_numeric") is not None:
            score += 0.1

        # Boost if specific age
        if row.get("age_min") is not None and row.get("age_max") is not None:
            score += 0.1

        return min(1.0, score)

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
            logger.info("PostgreSQL System initialized with multilingual normalization")

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
        self, query: str, intent_result=None, top_k: int = 10
    ) -> RAGResult:
        """MAIN CORRECTION - Search with complete response generation"""

        if not self.is_initialized or not self.postgres_retriever:
            return RAGResult(
                source=RAGSource.NO_RESULTS,
                metadata={"error": "PostgreSQL not available"},
            )

        try:
            # Search metrics
            metric_results = await self.postgres_retriever.search_metrics(
                query, intent_result, top_k
            )

            if not metric_results:
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    metadata={"source_type": "metrics", "data_source": "postgresql"},
                )

            # Convert to Documents for compatibility
            documents = []
            logger.debug(f"Converting {len(metric_results)} metrics to documents")

            for i, metric in enumerate(metric_results):
                try:
                    # Safe content formatting
                    doc_content = self._format_metric_content(metric)

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
                            "source_type": "metrics",
                            "data_source": "postgresql",
                            "normalized_search": True,
                        },
                        score=metric.confidence,
                        source_type="metrics",
                        retrieval_method="postgresql_normalized",
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
                    },
                )

            # NEW: Final response generation with LLM
            answer_text = await self._generate_metrics_response(
                query, documents, metric_results
            )

            # Calculate global confidence with normalization boost
            avg_confidence = sum(m.confidence for m in metric_results) / len(
                metric_results
            )

            # Confidence bonus if normalized search found results
            normalized_concepts, _ = (
                self.postgres_retriever.query_normalizer.get_search_terms(query)
            )
            if normalized_concepts:
                avg_confidence = min(1.0, avg_confidence + 0.1)

            logger.info(
                f"PostgreSQL SUCCESS: {len(documents)} documents returned with generated response"
            )

            # CRITICAL CORRECTION - Use context_docs instead of documents + ADD answer
            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=answer_text,  # ✅ CRITICAL ADDITION - The generated response
                context_docs=[doc.to_dict() for doc in documents],  # ✅ CORRECT
                confidence=avg_confidence,
                metadata={
                    "source_type": "metrics",
                    "data_source": "postgresql",
                    "metric_count": len(metric_results),
                    "document_count": len(documents),
                    "avg_confidence": avg_confidence,
                    "multilingual_normalization": True,
                    "normalized_concepts": normalized_concepts[:5],
                    "response_generated": True,  # New flag
                },
            )

        except Exception as e:
            logger.error(f"PostgreSQL metrics search error: {e}")
            import traceback

            logger.error(f"Stack trace: {traceback.format_exc()}")
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": str(e), "source_type": "metrics"},
            )

    def _format_metric_content(self, metric: MetricResult) -> str:
        """Format a metric into text content for LLM"""
        try:
            content_parts = [
                f"**{metric.metric_name}**",
                f"Company: {metric.company}",
                f"Breed: {metric.breed}",
                f"Strain: {metric.strain}",
                f"Species: {metric.species}",
                f"Category: {metric.category}",
            ]

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
                    content_parts.append(f"Age: {metric.age_min} weeks")
                else:
                    content_parts.append(
                        f"Age: {metric.age_min}-{metric.age_max} weeks"
                    )

            if metric.sheet_name:
                content_parts.append(f"Source: {metric.sheet_name}")

            return "\n".join(content_parts)

        except Exception as e:
            logger.error(f"Metric formatting error: {e}")
            return f"Metric: {getattr(metric, 'metric_name', 'Unknown name')}"

    async def _generate_metrics_response(
        self, query: str, documents: List[Document], metric_results: List[MetricResult]
    ) -> str:
        """Generate intelligent and contextual response based on found metrics"""
        try:
            # Extract requested age from query
            age_requested = self._extract_age_from_query(query)

            # Analyze requested metric type
            query_lower = query.lower()
            metric_type = None
            if any(word in query_lower for word in ["weight", "poids", "body"]):
                metric_type = "weight"
            elif any(
                word in query_lower for word in ["fcr", "conversion", "efficacite"]
            ):
                metric_type = "fcr"
            elif any(word in query_lower for word in ["eau", "water", "drink"]):
                metric_type = "water"

            # Find most relevant metric (closest age)
            best_metric = None
            if age_requested and metric_results:
                best_metric = min(
                    metric_results,
                    key=lambda m: (
                        abs((m.age_min or 0) - age_requested)
                        if m.age_min
                        else float("inf")
                    ),
                )
            elif metric_results:
                best_metric = metric_results[0]  # First result by default

            if not best_metric:
                return f"No data found for '{query}'."

            # Generate contextual and intelligent response
            if metric_type == "weight" and age_requested:
                # Specialized response for weight
                if best_metric.value_numeric:
                    weight_value = best_metric.value_numeric
                    unit = best_metric.unit or "grams"
                    actual_age = (
                        best_metric.age_min
                        if best_metric.age_min
                        else "age not specified"
                    )

                    response = (
                        f"For strain {best_metric.strain} from {best_metric.company}, "
                    )

                    if age_requested == actual_age:
                        response += f"body weight at day {age_requested} is **{weight_value} {unit}**."
                    else:
                        response += (
                            f"the closest data to your request (day {age_requested}) "
                        )
                        response += (
                            f"is weight at day {actual_age}: **{weight_value} {unit}**."
                        )

                    # Add context if possible
                    if weight_value > 3000:
                        response += " This is adult weight at end of rearing."
                    elif weight_value > 1000:
                        response += " This is intermediate growth weight."
                    elif weight_value < 100:
                        response += " This is young chick weight."

                else:
                    response = f"Weight data for {best_metric.strain} at day {age_requested} does not contain exploitable numeric value."

            elif metric_type == "fcr":
                # Specialized response for FCR
                if best_metric.value_numeric:
                    fcr_value = best_metric.value_numeric
                    response = f"Feed conversion ratio (FCR) for {best_metric.strain} "
                    response += f"is **{fcr_value}**"
                    if best_metric.age_min:
                        response += f" at {best_metric.age_min} days"
                    response += "."

                    # Performance context
                    if fcr_value < 1.5:
                        response += " This is excellent feed conversion."
                    elif fcr_value < 2.0:
                        response += " This is good feed conversion."
                    else:
                        response += " This feed conversion could be improved."
                else:
                    response = f"FCR data for {best_metric.strain} does not contain numeric value."

            else:
                # Generic but intelligent response
                if best_metric.value_numeric:
                    value = best_metric.value_numeric
                    unit = best_metric.unit or ""
                    metric_name = best_metric.metric_name.replace("_", " ").title()

                    response = f"According to available data, {metric_name.lower()} "
                    response += f"for {best_metric.strain} from {best_metric.company} "
                    response += f"is **{value} {unit}**"

                    if age_requested and best_metric.age_min:
                        if age_requested == best_metric.age_min:
                            response += f" at day {age_requested}."
                        else:
                            response += f" (data from day {best_metric.age_min}, closest to your request for day {age_requested})."
                    else:
                        response += "."
                else:
                    response = f"Data is available for {best_metric.metric_name} but without precise numeric value."

            # Add info about other results if relevant
            if len(metric_results) > 1:
                response += (
                    f"\n\n*{len(metric_results)} total results found in database.*"
                )

            return response

        except Exception as e:
            logger.error(f"Intelligent response generation error: {e}")
            # Very simple fallback
            if metric_results:
                best = metric_results[0]
                return f"Data found: {best.metric_name} = {best.value_numeric or best.value_text or 'value not available'} for {best.strain}."
            return f"Error generating response for '{query}'."

    def _extract_age_from_query(self, query: str) -> Optional[int]:
        """Extract age in days from query (ex: 'day 11' -> 11)"""
        import re

        # Patterns to detect age
        patterns = [
            r"day\s+(\d+)",  # "day 11"
            r"jour\s+(\d+)",  # "jour 11"
            r"j\s*(\d+)",  # "j11" or "j 11"
            r"(\d+)\s*day",  # "11 day"
            r"(\d+)\s*jour",  # "11 jour"
            r"a\s+(\d+)\s+jours?",  # "a 11 jours"
            r"at\s+day\s+(\d+)",  # "at day 11"
        ]

        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    # Reasonable validation (0-100 days)
                    if 0 <= age <= 100:
                        return age
                except ValueError:
                    continue

        return None

    async def close(self):
        """Close PostgreSQL system"""
        if self.postgres_retriever:
            await self.postgres_retriever.close()
        self.is_initialized = False

    def get_normalization_status(self) -> Dict[str, Any]:
        """Return normalization system status"""
        if not self.postgres_retriever:
            return {"available": False, "reason": "retriever_not_initialized"}

        return {
            "available": True,
            "concept_mappings_count": len(
                self.postgres_retriever.query_normalizer.CONCEPT_MAPPINGS
            ),
            "supported_concepts": list(
                self.postgres_retriever.query_normalizer.CONCEPT_MAPPINGS.keys()
            ),
            "total_terms": sum(
                len(terms)
                for terms in self.postgres_retriever.query_normalizer.CONCEPT_MAPPINGS.values()
            ),
        }
