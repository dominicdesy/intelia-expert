# -*- coding: utf-8 -*-
"""
Standard query handler for processing regular requests with intelligent routing
"""

import time
import logging
import traceback
import os
from utils.types import Dict, Any, Optional

from config.config import RAG_SIMILARITY_TOP_K
from ..data_models import RAGResult, RAGSource
from .base_handler import BaseQueryHandler
from .standard_handler_helpers import (
    parse_contextual_history,
    generate_response_with_generator,
)
from retrieval.semantic_reranker import get_reranker
from retrieval.cohere_reranker import get_cohere_reranker

logger = logging.getLogger(__name__)


class StandardQueryHandler(BaseQueryHandler):
    """Handler for standard queries with intelligent routing"""

    def __init__(self):
        super().__init__()
        self.response_generator = None
        self.semantic_reranker = None  # Lazy load

    @property
    def reranker(self):
        """Lazy load re-ranker (Cohere or cross-encoder based on RERANKER_TYPE env var)"""
        if self.semantic_reranker is None:
            try:
                reranker_type = os.getenv("RERANKER_TYPE", "cross-encoder")  # "cross-encoder" or "cohere"

                if reranker_type == "cohere":
                    logger.info("🔧 Initializing Cohere re-ranker (rerank-multilingual-v3.0)...")
                    self.semantic_reranker = get_cohere_reranker(
                        model='rerank-multilingual-v3.0'
                    )
                    logger.info("✅ Cohere re-ranker initialized (multilingual, production-grade)")
                else:
                    logger.info("🔧 Initializing cross-encoder re-ranker (ms-marco-MiniLM)...")
                    self.semantic_reranker = get_reranker(
                        model_name='cross-encoder/ms-marco-MiniLM-L-6-v2',
                        score_threshold=0.3  # Balanced threshold
                    )
                    logger.info("✅ Cross-encoder re-ranker initialized (threshold=0.3)")

            except Exception as e:
                logger.warning(f"⚠️ Re-ranker init failed: {e}. Continuing without re-ranking.")
                self.semantic_reranker = False  # Flag to avoid retry
        return self.semantic_reranker if self.semantic_reranker is not False else None

    def _detect_poultry_type(self, query: str) -> str:
        """
        Detect poultry type (broiler vs layer) from query for RAG filtering.

        Args:
            query: User query

        Returns:
            'layers' or 'broilers' (Weaviate species field values)
        """
        query_lower = query.lower()

        # Layer keywords (same as generators.py)
        layer_keywords = [
            'pondeuse', 'poule', 'poules pondeuses', 'layer', 'hen', 'hens',
            'œuf', 'egg', 'ponte', 'laying', 'production d\'œufs', 'egg production',
            'coquille', 'shell', 'jaune', 'yolk', 'blanc d\'œuf', 'egg white',
            'albumine', 'albumen', 'poulailler', 'hen house', 'pondoir', 'nid',
            'nest', 'perchoir', 'perch', 'calcaire', 'calcium', 'picage', 'pecking',
            'plumage', 'feathering', 'ovulation', 'oviducte', 'oviduct', 'clutch',
            'photopériode', 'photoperiod', 'lumière', 'lighting',
            'isa brown', 'lohmann', 'hy-line', 'bovans'
        ]

        # Detect layer (priority)
        if any(keyword in query_lower for keyword in layer_keywords):
            logger.info("🐔 Poultry type detected: LAYER (filtering Weaviate by species=layers)")
            return 'layers'

        # Default: broiler
        logger.info("🐔 Poultry type detected: BROILER (filtering Weaviate by species=broilers)")
        return 'broilers'

    def configure(
        self,
        postgresql_system=None,
        weaviate_core=None,
        postgresql_validator=None,
        response_generator=None,
        **kwargs,
    ):
        """Configure handler with required systems"""
        self.postgresql_system = postgresql_system
        self.weaviate_core = weaviate_core
        self.postgresql_validator = postgresql_validator
        self.response_generator = response_generator
        super().configure(**kwargs)

    async def handle(
        self,
        preprocessed_data: Optional[Dict[str, Any]] = None,
        start_time: Optional[float] = None,
        query: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        original_query: Optional[str] = None,
        preprocessing_result: Optional[Dict[str, Any]] = None,
        language: str = "fr",
    ) -> RAGResult:
        """Process standard query with intelligent routing"""
        # Extract data from preprocessed_data if available
        if preprocessed_data:
            query = preprocessed_data.get("normalized_query", query)
            entities = preprocessed_data.get("entities", entities)
            routing_hint = preprocessed_data.get("routing_hint")
            is_optimization = preprocessed_data.get("is_optimization", False)
            language = preprocessed_data.get("language", language)
            if original_query is None:
                original_query = preprocessed_data.get("original_query", query)
        elif preprocessing_result:
            routing_hint = preprocessing_result.get("routing_hint")
            is_optimization = False
        else:
            routing_hint = None
            is_optimization = False

        if start_time is None:
            start_time = time.time()

        if entities is None:
            entities = {}

        # Ensure query is never None (should always be provided or extracted from preprocessed_data)
        if query is None:
            query = ""

        filters = self._extract_filters_from_entities(entities)
        (preprocessed_data.get("contextual_history", "") if preprocessed_data else "")

        logger.info(f"StandardQueryHandler processing query in language: {language}")
        logger.info(f"Routing hint: '{routing_hint}'")
        logger.info(f"Entities received: {entities}")
        logger.info(f"Filters extracted: {filters}")

        top_k = 5 if is_optimization else RAG_SIMILARITY_TOP_K

        # STEP 1: Handle PostgreSQL routing with validation
        if routing_hint == "postgresql":
            result = await self._handle_postgresql_routing(
                query, entities, filters, top_k, language, preprocessed_data, start_time
            )
            if result:
                return result

        # STEP 2: Handle Weaviate routing
        if routing_hint == "weaviate":
            if self._is_qualitative_query(entities):
                logger.info("Weaviate routing for qualitative query")
                return await self._search_weaviate_direct(
                    query,
                    entities,
                    top_k,
                    is_optimization,
                    start_time,
                    language,
                    filters,
                    preprocessed_data,
                )
            else:
                logger.info("Weaviate suggestion ignored (age/metric present)")

        # STEP 3: Age check for broilers
        if self.postgresql_system and self._should_skip_postgresql_for_age(entities):
            logger.info("Age out of range → direct Weaviate")
            if self.weaviate_core:
                return await self._search_weaviate_direct(
                    query,
                    entities,
                    top_k,
                    is_optimization,
                    start_time,
                    language,
                    filters,
                    preprocessed_data,
                )

        # STEP 4: Standard PostgreSQL search
        if self.postgresql_system and routing_hint != "postgresql":
            logger.info(
                f"Standard PostgreSQL search (language={language}, filters={filters})"
            )
            result = await self._search_postgresql_once(
                query, entities, top_k, is_optimization, language, filters
            )

            if result and result.source != RAGSource.NO_RESULTS:
                if self._is_result_relevant_to_query(
                    query, result.context_docs, entities
                ):
                    logger.info(f"PostgreSQL results relevant for '{query[:50]}...'")

                    if result.context_docs and not result.answer:
                        result.answer = await generate_response_with_generator(
                            self.response_generator,
                            result.context_docs,
                            query,
                            language,
                            preprocessed_data or {},
                        )

                    return result
                else:
                    logger.warning(
                        f"PostgreSQL returned {len(result.context_docs)} docs "
                        f"but NOT relevant for '{query[:50]}...' → Weaviate fallback"
                    )
            else:
                logger.info("PostgreSQL no results → Weaviate fallback")

        # STEP 5: Weaviate fallback
        if self.weaviate_core:
            logger.info(
                f"Weaviate search (top_k={top_k}, language={language}, filters={filters})"
            )
            return await self._search_weaviate_direct(
                query,
                entities,
                top_k,
                is_optimization,
                start_time,
                language,
                filters,
                preprocessed_data,
            )

        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Aucune information trouvée pour cette requête.",
            metadata={
                "query_type": "standard",
                "optimization_mode": is_optimization,
                "routing_hint": routing_hint,
                "language_attempted": language,
                "filters_attempted": filters,
            },
        )

    async def _handle_postgresql_routing(
        self,
        query: str,
        entities: Dict[str, Any],
        filters: Dict[str, Any],
        top_k: int,
        language: str,
        preprocessed_data: Optional[Dict[str, Any]],
        start_time: float,
    ) -> Optional[RAGResult]:
        """Handle PostgreSQL routing with validation"""
        logger.info("=" * 80)
        logger.info("PostgreSQL routing detected - validation then call")
        logger.info("=" * 80)

        if self.postgresql_validator:
            logger.info("Validating entities before PostgreSQL call...")

            conversation_context = (
                preprocessed_data.get("conversation_context")
                if preprocessed_data
                else None
            )

            validation_result = (
                await self.postgresql_validator.flexible_query_validation(
                    query=query,
                    entities=entities,
                    language=language,
                    conversation_context=conversation_context,
                )
            )

            logger.info(f"Validation result: {validation_result['status']}")

            if validation_result["status"] == "needs_fallback":
                logger.info("Clarification needed - immediate return")

                helpful_message = validation_result.get(
                    "helpful_message",
                    "Informations manquantes pour traiter votre requête.",
                )

                return RAGResult(
                    source=RAGSource.INSUFFICIENT_CONTEXT,
                    answer=helpful_message,
                    metadata={
                        "source_type": "postgresql_validation_clarification",
                        "routing_hint": "postgresql",
                        "missing_fields": validation_result.get("missing", []),
                        "detected_entities": validation_result.get(
                            "detected_entities", {}
                        ),
                        "validation_status": "needs_fallback",
                        "processing_time": time.time() - start_time,
                        "language_used": language,
                        "filters_extracted": filters,
                    },
                )

            if "enhanced_entities" in validation_result:
                entities = validation_result["enhanced_entities"]
                filters = self._extract_filters_from_entities(entities)
                logger.info(f"Entities enhanced by validation: {entities}")
                logger.info(f"Filters updated: {filters}")

        else:
            logger.warning("PostgreSQLValidator not available - skip validation")

        if self.postgresql_system:
            try:
                logger.info(
                    f"Calling PostgreSQL search_metrics() with filters={filters}..."
                )

                pg_result = await self.postgresql_system.search_metrics(
                    query=query,
                    entities=entities,
                    top_k=top_k,
                    filters=filters,
                )

                if pg_result.source == RAGSource.INSUFFICIENT_CONTEXT:
                    logger.warning("INSUFFICIENT_CONTEXT after validation (unexpected)")
                    pg_result.metadata.update(
                        {
                            "source_type": "postgresql_insufficient_context",
                            "routing_hint": "postgresql",
                            "processing_time": time.time() - start_time,
                            "language_used": language,
                            "filters_applied": filters,
                        }
                    )
                    return pg_result

                if pg_result.source == RAGSource.RAG_SUCCESS:
                    logger.info(
                        f"PostgreSQL SUCCESS: {len(pg_result.context_docs or [])} documents"
                    )

                    if pg_result.context_docs and not pg_result.answer:
                        logger.info("Generating PostgreSQL response with context")
                        pg_result.answer = await generate_response_with_generator(
                            self.response_generator,
                            pg_result.context_docs,
                            query,
                            language,
                            preprocessed_data or {},
                        )

                    pg_result.metadata.update(
                        {
                            "source_type": "postgresql_routing_hint",
                            "routing_hint": "postgresql",
                            "processing_time": time.time() - start_time,
                            "language_used": language,
                            "validation_applied": True,
                            "filters_applied": filters,
                        }
                    )
                    return pg_result

                logger.info("PostgreSQL NO_RESULTS - fallback to Weaviate")

            except Exception as e:
                logger.error(f"PostgreSQL error: {e}", exc_info=True)
                logger.info("Fallback to Weaviate after PostgreSQL error")
        else:
            logger.warning("PostgreSQL not available despite routing hint")

        return None

    async def _search_postgresql_once(
        self,
        query: str,
        entities: Dict[str, Any],
        top_k: int,
        is_optimization: bool,
        language: str = "fr",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[RAGResult]:
        """Execute single PostgreSQL search"""
        if filters is None:
            filters = {}

        try:
            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=entities,
                top_k=top_k,
                filters=filters,
            )

            if result and result.source != RAGSource.NO_RESULTS:
                if is_optimization:
                    result.metadata["query_mode"] = "optimization"
                    result.metadata["ranking_applied"] = True
                    result.metadata["top_k_used"] = top_k

                result.metadata["search_attempt"] = "postgresql_single"
                result.metadata["language_used"] = language
                result.metadata["filters_applied"] = filters
                logger.info(
                    f"PostgreSQL ({language}): {len(result.context_docs)} documents found"
                )
                return result
            else:
                logger.info(f"PostgreSQL ({language}): 0 documents (no retry)")
                return None

        except Exception as e:
            logger.error(f"PostgreSQL search error ({language}): {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return None

    async def _search_weaviate_direct(
        self,
        query: str,
        entities: Dict[str, Any],
        top_k: int,
        is_optimization: bool,
        start_time: float,
        language: str = "fr",
        filters: Optional[Dict[str, Any]] = None,
        preprocessed_data: Optional[Dict[str, Any]] = None,
    ) -> RAGResult:
        """Direct Weaviate search"""
        if filters is None:
            filters = {}

        if preprocessed_data is None:
            preprocessed_data = {}

        try:
            # 🐔 OPTION 3: Detect poultry type and filter Weaviate by species
            poultry_species = self._detect_poultry_type(query)
            filters['species'] = poultry_species

            # Use top_k directly (no reduction for optimization)
            # The 10x multiplier + re-ranker will handle filtering
            weaviate_top_k = top_k

            logger.info(
                f"Weaviate search (top_k={weaviate_top_k}, language={language}, species={poultry_species}, filters={filters})"
            )

            conversation_context_list = parse_contextual_history(preprocessed_data)

            # Retrieve more documents to compensate for Weaviate granular chunks
            weaviate_initial_k = weaviate_top_k * 10  # 50-120 docs instead of 5-12

            result = await self.weaviate_core.search(
                query=query,
                top_k=weaviate_initial_k,  # Plus de docs
                language=language,
                filters=filters,
                conversation_context=conversation_context_list,
            )

            # Handle result based on source
            if result and result.source not in (RAGSource.NO_RESULTS, RAGSource.LOW_CONFIDENCE):
                doc_count_before = len(result.context_docs) if result.context_docs else 0
                logger.info(f"Weaviate ({language}): {doc_count_before} documents retrieved (before re-ranking)")

                # Re-ranking with balanced threshold
                if result.context_docs and self.reranker:
                    try:
                        # Extract document texts
                        doc_texts = [
                            doc.get('content', '') if isinstance(doc, dict)
                            else getattr(doc, 'content', '')
                            for doc in result.context_docs
                        ]

                        logger.info(f"🔍 Re-ranking {len(doc_texts)} docs with threshold 0.3...")

                        # Re-ranker with cross-encoder OR Cohere
                        # Always filter to 5 docs max for Context Precision
                        final_top_k = 5  # Fixed: always filter to 5 relevant docs

                        reranked_texts = self.reranker.rerank(
                            query=query,
                            documents=doc_texts,
                            top_k=final_top_k,  # Always 5 docs max
                            return_scores=False
                        )

                        # Rebuild docs with only relevant ones
                        if reranked_texts:
                            # Map texts to original docs
                            text_to_doc = {
                                (doc.get('content', '') if isinstance(doc, dict) else getattr(doc, 'content', '')): doc
                                for doc in result.context_docs
                            }

                            result.context_docs = [text_to_doc[text] for text in reranked_texts if text in text_to_doc]

                            doc_count_after = len(result.context_docs)
                            logger.info(
                                f"✅ Re-ranking: {doc_count_before} docs → {doc_count_after} relevant docs "
                                f"(filtered {doc_count_before - doc_count_after})"
                            )
                        else:
                            logger.warning("⚠️ Re-ranking returned 0 docs - keeping original")

                    except Exception as e:
                        logger.error(f"❌ Re-ranking error: {e}. Using original documents.", exc_info=True)
                        # Continue with original documents on error


                # Generate answer if documents exist but no answer yet
                if result.context_docs and not result.answer:
                    logger.info("Generating Weaviate response with context")

                    # Ensure required keys exist
                    if "normalized_query" not in preprocessed_data:
                        preprocessed_data["normalized_query"] = query
                    if "entities" not in preprocessed_data:
                        preprocessed_data["entities"] = entities
                    if "language" not in preprocessed_data:
                        preprocessed_data["language"] = language

                    result.answer = await generate_response_with_generator(
                        self.response_generator,
                        result.context_docs,
                        query,
                        language,
                        preprocessed_data,
                    )

                # Enrich metadata
                if is_optimization:
                    result.metadata["query_mode"] = "optimization"
                    result.metadata["source"] = "weaviate_optimized"
                else:
                    result.metadata["source"] = "weaviate_fallback"

                result.metadata["top_k_used"] = weaviate_top_k
                result.metadata["processing_time"] = time.time() - start_time
                result.metadata["language_used"] = language
                result.metadata["filters_applied"] = filters

                return result
            elif result:
                # LOW_CONFIDENCE or NO_RESULTS - return with empty message
                # rag_engine will handle fallback to welcome message or LLM
                logger.info(f"Weaviate ({language}): 0 documents (source={result.source})")

                # Ensure answer is initialized to empty string (not None)
                if result.answer is None:
                    result.answer = ""

                return result
            else:
                logger.info(f"Weaviate ({language}): No result object returned")
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    context_docs=[],
                    answer="Erreur: Aucun résultat retourné par Weaviate.",
                    metadata={
                        "source": "weaviate_error",
                        "processing_time": time.time() - start_time,
                        "language_attempted": language,
                        "filters_attempted": filters,
                    },
                )

        except Exception as e:
            logger.error(f"Weaviate search error ({language}): {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Erreur lors de la recherche Weaviate.",
                metadata={
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                    "language_attempted": language,
                    "filters_attempted": filters,
                },
            )
