# -*- coding: utf-8 -*-

"""

rag_postgresql.py - PostgreSQL System for RAG
Version modulaire avec intégration QueryValidator et DataAvailabilityChecker

"""

import os
import json
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

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

from .data_models import RAGResult, RAGSource, Document
from .postgresql_query_builder import PostgreSQLQueryBuilder

# ✅ PHASE 1: Import des nouveaux modules
try:
    from .query_validator import QueryValidator

    QUERY_VALIDATOR_AVAILABLE = True
except ImportError:
    QUERY_VALIDATOR_AVAILABLE = False
    QueryValidator = None
    logging.warning("QueryValidator non disponible")

try:
    from .data_availability_checker import DataAvailabilityChecker

    DATA_CHECKER_AVAILABLE = True
except ImportError:
    DATA_CHECKER_AVAILABLE = False
    DataAvailabilityChecker = None
    logging.warning("DataAvailabilityChecker non disponible")

logger = logging.getLogger(__name__)

# PostgreSQL configuration
POSTGRESQL_CONFIG = {
    "user": os.getenv("DB_USER", "doadmin"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 25060)),
    "database": os.getenv("DB_NAME", "defaultdb"),
    "ssl": os.getenv("DB_SSL", "require"),
}

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"


class QueryType(Enum):
    """Query types for intelligent routing"""

    KNOWLEDGE = "knowledge"
    METRICS = "metrics"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


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
    sex: Optional[str] = None
    housing_system: Optional[str] = None
    data_type: Optional[str] = None

    def __post_init__(self):
        """Data validation and cleaning"""
        self.company = str(self.company) if self.company is not None else "Unknown"
        self.breed = str(self.breed) if self.breed is not None else "Unknown"
        self.strain = str(self.strain) if self.strain is not None else "Unknown"
        self.species = str(self.species) if self.species is not None else "Unknown"
        self.metric_name = (
            str(self.metric_name) if self.metric_name is not None else "Unknown"
        )
        self.sheet_name = str(self.sheet_name) if self.sheet_name is not None else ""
        self.category = str(self.category) if self.category is not None else ""

        # Sex normalization
        if self.sex:
            self.sex = str(self.sex).lower()
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
                self.sex = "as_hatched"

        self.confidence = max(0.0, min(1.0, float(self.confidence)))


class SQLQueryNormalizer:
    """Multilingual normalizer - Conservé du code original"""

    def __init__(self):
        self.terminology = self._load_terminology()
        self.CONCEPT_MAPPINGS = self._build_concept_mappings()
        logger.info(
            f"SQLQueryNormalizer initialized with {len(self.CONCEPT_MAPPINGS)} concept mappings"
        )

    def _load_terminology(self) -> Dict[str, Any]:
        """Load terminology from JSON configuration files"""
        config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
        terms = {}
        supported_languages = ["en", "fr", "es"]

        for lang in supported_languages:
            file_path = os.path.join(config_dir, f"universal_terms_{lang}.json")
            try:
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        terms[lang] = json.load(f)
                        logger.info(
                            f"Terminology loaded successfully for language: {lang}"
                        )
                else:
                    logger.warning(f"Terminology file not found: {file_path}")
                    terms[lang] = {}
            except Exception as e:
                logger.error(f"Error loading terminology for {lang}: {e}")
                terms[lang] = {}

        return terms

    def _build_concept_mappings(self) -> Dict[str, List[str]]:
        """Build concept mappings from loaded terminology"""
        mappings = {}

        for lang, lang_terms in self.terminology.items():
            if "performance_metrics" not in lang_terms:
                continue

            perf_metrics = lang_terms["performance_metrics"]

            for metric_key, metric_terms in perf_metrics.items():
                base_key = metric_key.split("_")[0] if "_" in metric_key else metric_key

                if base_key not in mappings:
                    mappings[base_key] = []

                if isinstance(metric_terms, list):
                    mappings[base_key].extend(metric_terms)

                if metric_key not in mappings:
                    mappings[metric_key] = []
                if isinstance(metric_terms, list):
                    mappings[metric_key].extend(metric_terms)

        for key in mappings:
            mappings[key] = list(set(mappings[key]))

        logger.info(f"Built concept mappings for {len(mappings)} concepts")
        return mappings

    def get_search_terms(self, query: str) -> Tuple[List[str], List[str]]:
        """Returns (normalized_concepts, raw_words) for SQL search"""
        normalized = self.normalize_query_concepts(query)
        raw_words = [word for word in query.lower().split() if len(word) > 3]
        return normalized, raw_words

    def normalize_query_concepts(self, query: str) -> List[str]:
        """Converts user query to normalized concept terms"""
        query_lower = query.lower()
        normalized_concepts = []

        for concept, terms in self.CONCEPT_MAPPINGS.items():
            if any(term.lower() in query_lower for term in terms):
                normalized_concepts.extend(terms)

        seen = set()
        unique_concepts = []
        for concept in normalized_concepts:
            if concept not in seen:
                seen.add(concept)
                unique_concepts.append(concept)

        return unique_concepts

    def extract_sex_from_query(self, query: str) -> Optional[str]:
        """Extract sex from query"""
        query_lower = query.lower()

        male_patterns = ["male", "mâle", "mâles", "masculin", "coq", "coqs", "rooster"]
        if any(pattern in query_lower for pattern in male_patterns):
            return "male"

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

        return None


class QueryRouter:
    """Intelligent router - Conservé du code original"""

    def __init__(self):
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
            "fcr",
            "icg",
            "conversion",
            "ross",
            "cobb",
            "hubbard",
        }

        self.knowledge_keywords = {
            "comment",
            "pourquoi",
            "qu'est-ce",
            "expliquer",
            "definir",
            "maladie",
            "disease",
            "traitement",
            "prevention",
            "biosecurite",
        }

    def route_query(self, query: str, intent_result=None) -> QueryType:
        """Determines query type"""
        query_lower = query.lower()

        metric_score = sum(
            1 for keyword in self.metric_keywords if keyword in query_lower
        )
        knowledge_score = sum(
            1 for keyword in self.knowledge_keywords if keyword in query_lower
        )

        if metric_score > knowledge_score + 1:
            return QueryType.METRICS
        elif knowledge_score > metric_score + 1:
            return QueryType.KNOWLEDGE
        else:
            return QueryType.HYBRID


class PostgreSQLRetriever:
    """PostgreSQL data retriever - Simplifié avec QueryBuilder"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None
        self.query_normalizer = SQLQueryNormalizer()
        self.query_builder = PostgreSQLQueryBuilder(self.query_normalizer)
        self.is_initialized = False

    async def initialize(self):
        """Initialize PostgreSQL connection"""
        if not ASYNCPG_AVAILABLE:
            logger.error("asyncpg not available")
            raise ImportError("asyncpg required")

        if self.is_initialized:
            return

        try:
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

            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")

            self.is_initialized = True
            logger.info("PostgreSQL Retriever initialized")

        except Exception as e:
            logger.error(f"PostgreSQL initialization error: {e}")
            self.pool = None
            self.is_initialized = False
            raise

    def _normalize_entities(self, entities: Dict[str, Any] = None) -> Dict[str, str]:
        """Normalize entities to simple string dict"""
        if not entities:
            return {}

        normalized = {}

        for key, value in entities.items():
            if value is None:
                continue

            if isinstance(value, str):
                normalized[key] = value
            elif isinstance(value, bool):
                normalized[key] = "true" if value else "false"
            elif isinstance(value, (int, float)):
                normalized[key] = str(value)
            elif hasattr(value, "value"):
                normalized[key] = str(value.value)
            else:
                normalized[key] = str(value)

        return normalized

    async def search_metrics(
        self,
        query: str,
        entities: Dict[str, Any] = None,
        top_k: int = 10,
        strict_sex_match: bool = False,
    ) -> List[MetricResult]:
        """
        Search metrics with optional strict sex matching

        Args:
            strict_sex_match: If True, only exact sex match (for comparisons)
        """

        if not self.is_initialized or not self.pool:
            logger.warning("PostgreSQL not initialized")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Initialization failed: {e}")
                return []

        try:
            normalized_entities = self._normalize_entities(entities)
            logger.debug(f"Entities: {entities}")
            logger.debug(f"Normalized: {normalized_entities}")

            sql_query, params = self.query_builder.build_sex_aware_sql_query(
                query, normalized_entities, top_k, strict_sex_match
            )

            logger.debug(f"SQL Query: {sql_query}")
            logger.debug(f"Parameters: {params}")

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql_query, *params)

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
                        sex=row.get("sex"),
                        housing_system=row.get("housing_system"),
                        data_type=row.get("data_type"),
                        confidence=self._calculate_relevance(
                            query, row, normalized_entities
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

    def _calculate_relevance(
        self, query: str, row: Dict, entities: Dict[str, str] = None
    ) -> float:
        """Calculate relevance score"""
        score = 0.5

        sex_from_entities = entities.get("sex") if entities else None
        row_sex = (row.get("sex") or "as_hatched").lower()

        if sex_from_entities and sex_from_entities != "as_hatched":
            if row_sex == sex_from_entities.lower():
                score += 0.3
            elif row_sex in ["as_hatched", "mixed"]:
                score += 0.1
        else:
            if row_sex in ["as_hatched", "mixed"]:
                score += 0.2

        normalized_concepts, _ = self.query_normalizer.get_search_terms(query)
        metric_name_lower = (row.get("metric_name") or "").lower()

        for concept in normalized_concepts:
            if concept in metric_name_lower:
                score += 0.3
                break

        if row.get("value_numeric") is not None:
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
    """Main PostgreSQL system - Interface simplifiée + Phase 1 modules"""

    def __init__(self):
        self.query_router = None
        self.postgres_retriever = None
        self.is_initialized = False
        self.openai_client = None

        # ✅ PHASE 1: Initialisation des nouveaux modules
        self.query_validator = None
        self.data_availability_checker = None

    async def initialize(self):
        """Initialize PostgreSQL system + Phase 1 modules"""
        if self.is_initialized:
            return

        if not ASYNCPG_AVAILABLE:
            logger.error("asyncpg not available")
            raise ImportError("asyncpg required")

        try:
            self.query_router = QueryRouter()
            self.postgres_retriever = PostgreSQLRetriever(POSTGRESQL_CONFIG)
            await self.postgres_retriever.initialize()

            if OPENAI_AVAILABLE and OPENAI_API_KEY:
                self.openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("OpenAI not available")

            # ✅ PHASE 1: Initialisation QueryValidator
            if QUERY_VALIDATOR_AVAILABLE and QueryValidator:
                try:
                    self.query_validator = QueryValidator()
                    logger.info("✅ QueryValidator initialisé (Phase 1)")
                except Exception as e:
                    logger.warning(f"QueryValidator init failed: {e}")
                    self.query_validator = None

            # ✅ PHASE 1: Initialisation DataAvailabilityChecker
            if DATA_CHECKER_AVAILABLE and DataAvailabilityChecker:
                try:
                    self.data_availability_checker = DataAvailabilityChecker()
                    logger.info("✅ DataAvailabilityChecker initialisé (Phase 1)")
                except Exception as e:
                    logger.warning(f"DataAvailabilityChecker init failed: {e}")
                    self.data_availability_checker = None

            self.is_initialized = True
            logger.info("PostgreSQL System initialized with Phase 1 modules")

        except Exception as e:
            logger.error(f"PostgreSQL System initialization error: {e}")
            self.is_initialized = False
            raise

    def route_query(self, query: str, intent_result=None) -> QueryType:
        """Route a query"""
        if not self.query_router:
            return QueryType.KNOWLEDGE
        return self.query_router.route_query(query, intent_result)

    async def search_metrics(
        self,
        query: str,
        intent_result=None,
        top_k: int = 10,
        entities: Dict[str, Any] = None,
        strict_sex_match: bool = False,
    ) -> RAGResult:
        """
        Main search method with Phase 1 validation

        Args:
            strict_sex_match: Mode strict pour comparaisons (pas de fallback as_hatched)
        """

        if not self.is_initialized or not self.postgres_retriever:
            return RAGResult(
                source=RAGSource.NO_RESULTS,
                metadata={"error": "PostgreSQL not available"},
            )

        # ✅ PHASE 1: Validation de la complétude de la requête
        if self.query_validator:
            try:
                validation_result = self.query_validator.validate_query_completeness(
                    query, entities or {}
                )

                if not validation_result.get("is_complete", True):
                    missing_entities = validation_result.get("missing_entities", [])
                    clarification_prompt = (
                        self.query_validator.generate_clarification_prompt(
                            missing_entities, query
                        )
                    )

                    logger.info(
                        f"Query validation: incomplete - missing {missing_entities}"
                    )

                    return RAGResult(
                        source=RAGSource.NO_RESULTS,
                        answer=clarification_prompt,
                        metadata={
                            "validation_status": "incomplete",
                            "missing_entities": missing_entities,
                            "requires_clarification": True,
                            "phase": "1_validation",
                        },
                    )
            except Exception as e:
                logger.warning(f"Query validation failed: {e}")

        # ✅ PHASE 1: Vérification de la disponibilité des données avec CORRECTION as_hatched
        if self.data_availability_checker:
            try:
                # 🔧 CORRECTION CRITIQUE: Traiter as_hatched correctement
                availability_check = self._check_data_availability_with_as_hatched_fix(
                    query, entities or {}
                )

                if not availability_check.get("data_available", True):
                    unavailable_reason = availability_check.get("reason", "unknown")
                    unavailable_message = (
                        self.data_availability_checker.generate_unavailable_message(
                            unavailable_reason, query
                        )
                    )

                    logger.info(f"Data availability check: {unavailable_reason}")

                    return RAGResult(
                        source=RAGSource.NO_RESULTS,
                        answer=unavailable_message,
                        metadata={
                            "availability_status": "unavailable",
                            "reason": unavailable_reason,
                            "data_type_requested": availability_check.get("data_type"),
                            "phase": "1_availability",
                        },
                    )
            except Exception as e:
                logger.warning(f"Data availability check failed: {e}")

        # Recherche normale si validations OK
        try:
            metric_results = await self.postgres_retriever.search_metrics(
                query=query,
                entities=entities,
                top_k=top_k,
                strict_sex_match=strict_sex_match,
            )

            if not metric_results:
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    metadata={
                        "source_type": "metrics",
                        "data_source": "postgresql",
                        "strict_sex_match": strict_sex_match,
                        "validation_passed": True,
                        "availability_passed": True,
                    },
                )

            documents = self._convert_metrics_to_documents(metric_results)

            if not documents:
                logger.warning("No documents created")
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    metadata={"error": "No valid documents"},
                )

            answer_text = await self._generate_response(
                query, documents, metric_results, entities
            )

            avg_confidence = sum(m.confidence for m in metric_results) / len(
                metric_results
            )

            logger.info(f"PostgreSQL SUCCESS: {len(documents)} documents")

            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=answer_text,
                context_docs=[doc.to_dict() for doc in documents],
                confidence=avg_confidence,
                metadata={
                    "source_type": "metrics",
                    "data_source": "postgresql",
                    "metric_count": len(metric_results),
                    "strict_sex_match": strict_sex_match,
                    "openai_model": OPENAI_MODEL,
                    "validation_passed": True,
                    "availability_passed": True,
                    "phase": "1_complete",
                },
            )

        except Exception as e:
            logger.error(f"PostgreSQL search error: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": str(e)},
            )

    def _check_data_availability_with_as_hatched_fix(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        🔧 CORRECTION CRITIQUE: Gestion correcte de as_hatched dans la validation des âges
        
        Cette méthode corrige le problème où 'as_hatched' était traité comme un âge invalide
        """
        # Obtenir la validation originale
        original_check = self.data_availability_checker.check_data_availability(
            query, entities
        )
        
        # Si la validation a échoué à cause d'un "âge invalide"
        if not original_check.get("data_available", True):
            reason = original_check.get("reason", "")
            
            # 🔧 CORRECTION: Vérifier si l'erreur concerne "as_hatched"
            if "invalide" in reason.lower() and "as_hatched" in str(entities.get("age_days", "")):
                logger.info("🔧 Correction as_hatched: Autoriser la requête sans âge spécifique")
                return {
                    "data_available": True,
                    "reason": "Age non spécifié (as_hatched) - recherche générale autorisée",
                    "data_type": "metrics",
                    "corrected_as_hatched": True
                }
            
            # 🔧 CORRECTION: Aussi pour les valeurs None ou "None"
            age_days = entities.get("age_days")
            if "invalide" in reason.lower() and (age_days is None or str(age_days).lower() in ["none", "null"]):
                logger.info("🔧 Correction: Autoriser la requête sans âge spécifique")
                return {
                    "data_available": True,
                    "reason": "Age non spécifié - recherche générale autorisée",
                    "data_type": "metrics",
                    "corrected_none_age": True
                }
        
        # Retourner la validation originale si pas de problème as_hatched
        return original_check

    def _convert_metrics_to_documents(
        self, metric_results: List[MetricResult]
    ) -> List[Document]:
        """Convert metrics to documents"""
        documents = []

        for metric in metric_results:
            try:
                content = self._format_metric_content(metric)
                doc = Document(
                    content=content,
                    metadata={
                        "strain": metric.strain,
                        "metric_name": metric.metric_name,
                        "sex": metric.sex,
                        "source_type": "metrics",
                    },
                    score=metric.confidence,
                    source_type="metrics",
                    retrieval_method="postgresql",
                )
                documents.append(doc)
            except Exception as e:
                logger.error(f"Document creation error: {e}")
                continue

        return documents

    def _format_metric_content(self, metric: MetricResult) -> str:
        """Format metric as text"""
        parts = [
            f"**{metric.metric_name}**",
            f"Strain: {metric.strain}",
        ]

        if metric.sex:
            parts.append(f"Sex: {metric.sex}")

        if metric.value_numeric is not None:
            parts.append(f"Value: {metric.value_numeric} {metric.unit or ''}")

        if metric.age_min is not None:
            if metric.age_min == metric.age_max:
                parts.append(f"Age: {metric.age_min} days")
            else:
                parts.append(f"Age: {metric.age_min}-{metric.age_max} days")

        return "\n".join(parts)

    async def _generate_response(
        self,
        query: str,
        documents: List[Document],
        metric_results: List[MetricResult],
        entities: Dict,
    ) -> str:
        """Generate response with OpenAI or fallback"""

        if not metric_results:
            return f"Aucune donnée trouvée pour '{query}'."

        best_metric = metric_results[0]

        sex_info = (
            f" pour {best_metric.sex}"
            if best_metric.sex and best_metric.sex != "as_hatched"
            else ""
        )
        return f"Données trouvées{sex_info}: {best_metric.metric_name} = {best_metric.value_numeric or best_metric.value_text} pour {best_metric.strain}."

    async def close(self):
        """Close system"""
        if self.postgres_retriever:
            await self.postgres_retriever.close()
        self.is_initialized = False

    def get_normalization_status(self) -> Dict[str, Any]:
        """Return normalization status + Phase 1 modules"""
        if not self.postgres_retriever:
            return {"available": False}

        return {
            "available": True,
            "sex_aware_search": True,
            "openai_enabled": self.openai_client is not None,
            "strict_sex_match_supported": True,
            # ✅ PHASE 1: Status des nouveaux modules
            "phase_1_modules": {
                "query_validator": {
                    "available": self.query_validator is not None,
                    "status": "initialized" if self.query_validator else "unavailable",
                },
                "data_availability_checker": {
                    "available": self.data_availability_checker is not None,
                    "status": (
                        "initialized"
                        if self.data_availability_checker
                        else "unavailable"
                    ),
                },
            },
            "implementation_phase": "1_validation_availability",
            # 🔧 NOUVELLE INFO: Statut de la correction as_hatched
            "as_hatched_fix": {
                "applied": True,
                "description": "Correction pour traiter as_hatched comme âge non spécifié",
                "status": "active"
            }
        }