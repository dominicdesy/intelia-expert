# -*- coding: utf-8 -*-
"""
rag_engine_handlers.py - Handlers spécialisés pour différents types de requêtes
VERSION 4.6 - AJOUT FILTRAGE SPECIES:
- ✅ NOUVEAU: Extraction species depuis entities et passage via filters dict
- ✅ NOUVEAU: Filtrage species dans tous les retrievers (PostgreSQL + Weaviate)
- ✅ Compatible avec StandardQueryHandler pour queries métrique et qualitatives
- ✅ Maintien vérification pertinence avant retour résultats PostgreSQL
- ✅ Fallback automatique vers Weaviate si résultats non pertinents
- ✅ Validation PostgreSQLValidator AVANT appel search_metrics()
- Compatible avec la structure harmonisée du comparison_handler
- Mode optimisation pour tri par pertinence
"""

import re
import time
import logging
import traceback
from typing import Dict, Any, Optional, Tuple, List

from config.config import RAG_SIMILARITY_TOP_K
from .data_models import RAGResult, RAGSource

logger = logging.getLogger(__name__)


class BaseQueryHandler:
    """Handler de base avec fonctionnalités communes"""

    def __init__(self):
        self.postgresql_system = None
        self.weaviate_core = None
        self.postgresql_validator = None

    def configure(self, **kwargs):
        """Configure le handler avec les modules nécessaires"""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _should_skip_postgresql_for_age(self, entities: Dict[str, Any]) -> bool:
        """
        Vérifie si l'âge est hors plage broilers typique
        Broilers typiquement <= 56 jours, on élargit à 60j pour sécurité
        """
        age = entities.get("age_days")
        if age and age > 60:
            logger.info(
                f"Age {age}j hors plage broilers -> fallback Weaviate recommande"
            )
            return True
        return False

    def _is_qualitative_query(self, entities: Dict[str, Any]) -> bool:
        """
        Vérifie si la requête est qualitative (sans âge/métrique précis)
        """
        has_age = entities.get("age_days") is not None
        has_metric = entities.get("metric_type") is not None

        return not has_age and not has_metric

    def _is_result_relevant_to_query(
        self, query: str, context_docs: List[Dict], entities: Dict[str, Any]
    ) -> bool:
        """
        ✅ MÉTHODE DE PERTINENCE: Vérifie si les documents retournés sont pertinents pour la query

        Args:
            query: Question originale
            context_docs: Documents retournés par PostgreSQL
            entities: Entités extraites

        Returns:
            True si pertinent, False sinon
        """
        if not context_docs:
            logger.debug("Aucun document à vérifier - non pertinent")
            return False

        # Extraire les mots-clés importants de la query (lowercase)
        query_lower = query.lower()

        # Liste de termes qui indiquent une query qualitative (non métrique)
        qualitative_terms = [
            "traitement",
            "vaccin",
            "maladie",
            "symptôme",
            "diagnostic",
            "prévention",
            "antibiotique",
            "protocole",
            "soins",
            "sanitaire",
            "hygiène",
            "infection",
            "virus",
            "bactérie",
            "pathologie",
            "treatment",
            "vaccine",
            "disease",
            "symptom",
            "prevention",
            "antibiotic",
            "protocol",
            "care",
            "sanitary",
            "hygiene",
            "infection",
            "virus",
            "bacteria",
            "pathology",
            "behandlung",
            "impfstoff",
            "krankheit",
            "symptom",
            "tratamiento",
            "vacuna",
            "enfermedad",
            "síntoma",
            "trattamento",
            "vaccino",
            "malattia",
            "sintomo",
        ]

        # Termes métriques quantitatifs
        metric_terms = [
            "feed intake",
            "weight",
            "fcr",
            "gain",
            "grams",
            "consumption",
            "consommation",
            "poids",
            "gain",
            "grammes",
            "futterverzehr",
            "gewicht",
            "zunahme",
            "consumo",
            "peso",
            "ganancia",
            "consumo",
            "peso",
            "guadagno",
        ]

        # Vérifier si la query a une intention qualitative
        has_qualitative_intent = any(term in query_lower for term in qualitative_terms)

        if has_qualitative_intent:
            # Examiner le contenu des premiers documents
            doc_contents = " ".join(
                [str(doc.get("content", "")) for doc in context_docs[:5]]
            ).lower()

            # Vérifier si les docs contiennent des informations qualitatives
            has_qualitative_content = any(
                term in doc_contents for term in qualitative_terms
            )

            # Vérifier si les docs ne contiennent QUE des métriques
            has_only_metrics = (
                any(term in doc_contents for term in metric_terms)
                and not has_qualitative_content
            )

            if has_only_metrics:
                logger.info(
                    f"🔍 PERTINENCE: Documents contiennent UNIQUEMENT des métriques, "
                    f"mais query cherche info qualitative ('{query[:50]}...') → NON PERTINENT"
                )
                return False

            logger.debug(
                "✅ PERTINENCE: Documents contiennent info qualitative → PERTINENT"
            )
            return True

        # Pour les queries métriques, toujours considérer comme pertinent
        logger.debug("✅ PERTINENCE: Query métrique, documents acceptés → PERTINENT")
        return True

    def _extract_filters_from_entities(
        self, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ✅ NOUVELLE MÉTHODE: Extrait les filtres depuis les entités détectées

        Args:
            entities: Dictionnaire des entités extraites par le preprocessing

        Returns:
            Dict contenant les filtres à appliquer (species, genetic_line, etc.)
        """
        filters = {}

        # Extraire species
        if "species" in entities and entities["species"]:
            filters["species"] = entities["species"]
            logger.info(f"🐔 Species filter extracted: {entities['species']}")

        # Extraire genetic_line si présent
        if "genetic_line" in entities and entities["genetic_line"]:
            filters["genetic_line"] = entities["genetic_line"]
            logger.info(f"🧬 Genetic line filter extracted: {entities['genetic_line']}")

        # Vous pouvez ajouter d'autres filtres ici selon vos besoins
        # if 'country' in entities:
        #     filters['country'] = entities['country']

        return filters


class ComparativeQueryHandler(BaseQueryHandler):
    """Handler pour les requêtes comparatives"""

    def configure(self, **kwargs):
        """Configure avec ComparisonHandler"""
        super().configure(**kwargs)
        self.comparison_handler = kwargs.get("comparison_handler")
        self.weaviate_core = kwargs.get("weaviate_core")
        self.postgresql_system = kwargs.get("postgresql_system")

    async def handle(
        self, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Traite les requêtes comparatives"""

        if not self.comparison_handler:
            logger.warning("ComparisonHandler non disponible, fallback vers standard")
            return await self._fallback_to_standard(preprocessed_data, start_time)

        try:
            logger.info("Executing comparative query via ComparisonHandler")

            comparison_result = await self.comparison_handler.handle_comparison_query(
                preprocessed_data
            )

            if not comparison_result["success"]:
                error_msg = comparison_result.get(
                    "error", "Erreur comparative inconnue"
                )
                logger.warning(f"Comparison failed: {error_msg}")
                return await self._fallback_to_standard(preprocessed_data, start_time)

            answer_text = await self.comparison_handler.generate_comparative_response(
                preprocessed_data.get(
                    "original_query", preprocessed_data["normalized_query"]
                ),
                comparison_result,
                "fr",
            )

            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=answer_text,
                context_docs=self._extract_comparison_documents(comparison_result),
                confidence=0.95,
                metadata={
                    "source_type": "comparative",
                    "comparison_type": comparison_result.get("comparison_type"),
                    "operation": comparison_result.get("operation"),
                    "entities_compared": comparison_result.get("metadata", {}).get(
                        "entities_compared", 2
                    ),
                    "processing_time": time.time() - start_time,
                    "result_count": len(comparison_result.get("results", [])),
                    "preprocessing_applied": comparison_result.get("metadata", {}).get(
                        "preprocessing_applied", False
                    ),
                },
            )

        except ValueError as ve:
            logger.error(f"ValueError in comparative handling: {ve}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            return RAGResult(
                source=RAGSource.ERROR,
                answer=f"Erreur de comparaison: {str(ve)}",
                metadata={
                    "source_type": "comparative_error",
                    "error_type": "ValueError",
                    "error_message": str(ve),
                    "processing_time": time.time() - start_time,
                },
            )

        except ZeroDivisionError as zde:
            logger.error(f"ZeroDivisionError in comparative handling: {zde}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            return RAGResult(
                source=RAGSource.ERROR,
                answer="Erreur de comparaison: division par zéro détectée. Les métriques comparées contiennent des valeurs nulles.",
                metadata={
                    "source_type": "comparative_error",
                    "error_type": "ZeroDivisionError",
                    "error_message": str(zde),
                    "processing_time": time.time() - start_time,
                },
            )

        except Exception as e:
            logger.error("Critical error in comparative handling")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error(f"Error args: {e.args}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            return await self._fallback_to_standard(preprocessed_data, start_time)

    async def _fallback_to_standard(
        self, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Fallback vers traitement standard avec cascade PostgreSQL → Weaviate"""

        entities = preprocessed_data.get("entities", {})
        query = preprocessed_data["normalized_query"]
        language = preprocessed_data.get("language", "fr")

        logger.info(f"🌍 Fallback comparative avec langue: {language}")

        # ✅ NOUVEAU: Extraire filters depuis entities
        filters = self._extract_filters_from_entities(entities)

        availability_metadata = {
            "postgresql_available": self.postgresql_system is not None,
            "weaviate_available": self.weaviate_core is not None,
        }

        # 1. Tentative PostgreSQL
        if self.postgresql_system and entities:
            logger.info(
                f"🔍 Fallback comparative: tentative PostgreSQL (langue={language}, filters={filters})"
            )
            try:
                result = await self.postgresql_system.search_metrics(
                    query=query,
                    entities=entities,
                    top_k=RAG_SIMILARITY_TOP_K,
                    filters=filters,  # ✅ NOUVEAU paramètre
                )

                if result and result.source != RAGSource.NO_RESULTS:
                    result.metadata.update(
                        {
                            "source_type": "comparative_fallback_postgresql",
                            "fallback_applied": True,
                            "processing_time": time.time() - start_time,
                            "language_used": language,
                            "filters_applied": filters,  # ✅ NOUVEAU
                            **availability_metadata,
                        }
                    )
                    logger.info(
                        f"✅ Fallback PostgreSQL ({language}): {len(result.context_docs)} docs"
                    )
                    return result

                logger.info("⚠️ PostgreSQL fallback: 0 résultats")

            except Exception as e:
                logger.error(f"❌ Erreur PostgreSQL fallback: {e}")
                availability_metadata["postgresql_error"] = str(e)

        # 2. Tentative Weaviate
        if self.weaviate_core:
            logger.info(
                f"🔍 Fallback comparative: tentative Weaviate (langue={language}, filters={filters})"
            )
            try:
                weaviate_result = await self.weaviate_core.search(
                    query=query,
                    top_k=RAG_SIMILARITY_TOP_K,
                    language=language,
                    filters=filters,  # ✅ NOUVEAU paramètre
                )

                if weaviate_result and weaviate_result.source == RAGSource.RAG_SUCCESS:
                    weaviate_result.metadata.update(
                        {
                            "source_type": "comparative_fallback_weaviate",
                            "fallback_applied": True,
                            "processing_time": time.time() - start_time,
                            "language_used": language,
                            "filters_applied": filters,  # ✅ NOUVEAU
                            **availability_metadata,
                        }
                    )
                    logger.info(
                        f"✅ Fallback Weaviate ({language}): {len(weaviate_result.context_docs)} docs"
                    )
                    return weaviate_result

                logger.info("⚠️ Weaviate fallback: 0 résultats")

            except Exception as e:
                logger.error(f"❌ Erreur Weaviate fallback: {e}")
                availability_metadata["weaviate_error"] = str(e)

        # 3. Si tout échoue
        logger.warning("❌ Tous les fallbacks comparative ont échoué")
        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Je n'ai pas trouvé suffisamment d'informations pour répondre à cette comparaison.",
            metadata={
                "source_type": "comparative_no_results",
                "processing_time": time.time() - start_time,
                "result_type": "no_results",
                "is_success": False,
                "is_error": True,
                "language_attempted": language,
                "filters_attempted": filters,  # ✅ NOUVEAU
                **availability_metadata,
            },
        )

    def _extract_comparison_documents(self, comparison_result: Dict) -> list:
        """
        Extrait les documents des résultats de comparaison
        Compatible avec la nouvelle structure harmonisée
        """
        try:
            documents = []
            results = comparison_result.get("results", [])

            for result_item in results:
                if isinstance(result_item, dict):
                    if "all_docs" in result_item:
                        documents.extend(result_item["all_docs"])
                    elif "context_docs" in result_item:
                        documents.extend(result_item["context_docs"])

            logger.debug(f"Extracted {len(documents)} comparison documents")
            return documents

        except Exception as e:
            logger.warning(f"Erreur extraction documents comparatifs: {e}")
            return []


class TemporalQueryHandler(BaseQueryHandler):
    """Handler pour les requêtes temporelles (plages d'âges)"""

    async def handle(
        self, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Traite les requêtes de plage temporelle"""

        query = preprocessed_data["normalized_query"]
        entities = preprocessed_data["entities"]
        language = preprocessed_data.get("language", "fr")

        # ✅ NOUVEAU: Extraire filters depuis entities
        filters = self._extract_filters_from_entities(entities)

        age_range = self._extract_age_range_from_query(query)
        if not age_range:
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Impossible d'extraire la plage d'âges de la requête.",
                metadata={"error": "age_range_extraction_failed"},
            )

        try:
            logger.info(
                f"Traitement plage temporelle: {age_range[0]}-{age_range[1]} jours (langue={language}, filters={filters})"
            )

            if hasattr(self.postgresql_system, "search_metrics_range"):
                result = await self.postgresql_system.search_metrics_range(
                    query=query,
                    entities=entities,
                    age_min=age_range[0],
                    age_max=age_range[1],
                    top_k=RAG_SIMILARITY_TOP_K,
                    filters=filters,  # ✅ NOUVEAU paramètre
                )

                if result and result.source != RAGSource.NO_RESULTS:
                    result.metadata.update(
                        {
                            "source_type": "temporal_optimized",
                            "age_range": age_range,
                            "processing_time": time.time() - start_time,
                            "optimization": "single_query_between",
                            "language_used": language,
                            "filters_applied": filters,  # ✅ NOUVEAU
                        }
                    )
                    return result

            return await self._handle_temporal_fallback(
                query, entities, age_range, start_time, language, filters
            )

        except Exception as e:
            logger.error(f"Erreur traitement temporel: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Erreur lors du traitement de la requête temporelle.",
                metadata={"error": str(e)},
            )

    def _extract_age_range_from_query(self, query: str) -> Optional[Tuple[int, int]]:
        """Extrait la plage d'âges d'une requête"""
        patterns = [
            r"entre\s+(\d+)\s+et\s+(\d+)\s+jours?",
            r"de\s+(\d+)\s+à\s+(\d+)\s+jours?",
            r"du\s+jour\s+(\d+)\s+au\s+jour\s+(\d+)",
            r"(\d+)\s*-\s*(\d+)\s+jours?",
            r"between\s+(\d+)\s+and\s+(\d+)\s+days?",
        ]

        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                age_min = int(match.group(1))
                age_max = int(match.group(2))
                return (age_min, age_max)

        return None

    async def _handle_temporal_fallback(
        self,
        query: str,
        entities: Dict[str, Any],
        age_range: Tuple[int, int],
        start_time: float,
        language: str = "fr",
        filters: Dict[str, Any] = None,  # ✅ NOUVEAU paramètre
    ) -> RAGResult:
        """Fallback: requêtes multiples pour plage temporelle"""

        if filters is None:
            filters = {}

        age_min, age_max = age_range
        results = []

        for age in range(age_min, age_max + 1):
            age_entities = entities.copy()
            age_entities["age_days"] = age

            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=age_entities,
                top_k=3,
                filters=filters,  # ✅ NOUVEAU paramètre
            )

            if result and result.context_docs:
                results.extend(result.context_docs)

        if results:
            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                context_docs=results,
                metadata={
                    "source_type": "temporal_multiple_queries",
                    "age_range": age_range,
                    "queries_executed": age_max - age_min + 1,
                    "processing_time": time.time() - start_time,
                    "language_used": language,
                    "filters_applied": filters,  # ✅ NOUVEAU
                },
            )

        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Aucune donnée trouvée pour cette plage temporelle.",
            metadata={
                "age_range": age_range,
                "language_attempted": language,
                "filters_attempted": filters,  # ✅ NOUVEAU
            },
        )


class StandardQueryHandler(BaseQueryHandler):
    """Handler pour les requêtes standard avec routage intelligent"""

    def __init__(self):
        super().__init__()
        self.response_generator = (
            None  # ✅ NOUVEAU: Référence au générateur de réponses
        )

    async def handle(
        self,
        preprocessed_data: Dict[str, Any] = None,
        start_time: float = None,
        query: str = None,
        entities: Dict[str, Any] = None,
        original_query: str = None,
        preprocessing_result: Dict[str, Any] = None,
        language: str = "fr",
    ) -> RAGResult:
        """
        Traite une requête standard avec routage intelligent
        ✅ VERSION 4.6: Extraction filters depuis entities + passage aux retrievers
        ✅ VERSION 4.5: VÉRIFICATION DE PERTINENCE avant retour
        ✅ VERSION 4.4: Validation AVANT appel search_metrics()
        """
        # Extraction des données depuis preprocessed_data si disponible
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

        # ✅ NOUVEAU: Extraire filters depuis entities
        filters = self._extract_filters_from_entities(entities)

        # ✅ EXTRACTION CONTEXTE: Pour logs et transmission
        contextual_history = (
            preprocessed_data.get("contextual_history", "") if preprocessed_data else ""
        )

        logger.info(
            f"🔍 HANDLER - contextual_history présent: {bool(contextual_history)}"
        )
        logger.info(
            f"🔍 HANDLER - contextual_history length: {len(contextual_history) if contextual_history else 0}"
        )

        logger.info(f"🌍 StandardQueryHandler traite requête en langue: {language}")
        logger.info(f"🎯 ROUTING_HINT REÇU: '{routing_hint}'")
        logger.info(f"📊 ENTITIES REÇUES: {entities}")
        logger.info(f"🔍 FILTERS EXTRAITS: {filters}")  # ✅ NOUVEAU log

        # Configuration top_k selon mode
        if is_optimization:
            logger.info("Mode optimisation activé - priorité au tri par pertinence")
            top_k = 5
        else:
            top_k = RAG_SIMILARITY_TOP_K

        # ✅ ÉTAPE 1: Vérifier le routing hint PostgreSQL avec VALIDATION PRÉALABLE
        if routing_hint == "postgresql":
            logger.info("=" * 80)
            logger.info("🎯 ROUTING HINT POSTGRESQL DÉTECTÉ - VALIDATION PUIS APPEL")
            logger.info("=" * 80)

            if self.postgresql_validator:
                logger.info("🔍 Validation des entités avant appel PostgreSQL...")

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

                logger.info(f"📋 Résultat validation: {validation_result['status']}")

                if validation_result["status"] == "needs_fallback":
                    logger.info("⚠️ Clarification nécessaire - retour immédiat")

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
                            "filters_extracted": filters,  # ✅ NOUVEAU
                        },
                    )

                if "enhanced_entities" in validation_result:
                    entities = validation_result["enhanced_entities"]
                    # ✅ NOUVEAU: Re-extraire filters après enrichissement
                    filters = self._extract_filters_from_entities(entities)
                    logger.info(f"✅ Entités enrichies par validation: {entities}")
                    logger.info(f"✅ Filters mis à jour: {filters}")

            else:
                logger.warning("⚠️ PostgreSQLValidator non disponible - skip validation")

            if self.postgresql_system:
                try:
                    logger.info(
                        f"🔍 Appel PostgreSQL search_metrics() avec filters={filters}..."
                    )

                    pg_result = await self.postgresql_system.search_metrics(
                        query=query,
                        entities=entities,
                        top_k=top_k,
                        filters=filters,  # ✅ NOUVEAU paramètre
                    )

                    if pg_result.source == RAGSource.INSUFFICIENT_CONTEXT:
                        logger.warning(
                            "⚠️ INSUFFICIENT_CONTEXT après validation (inattendu)"
                        )
                        pg_result.metadata.update(
                            {
                                "source_type": "postgresql_insufficient_context",
                                "routing_hint": "postgresql",
                                "processing_time": time.time() - start_time,
                                "language_used": language,
                                "filters_applied": filters,  # ✅ NOUVEAU
                            }
                        )
                        return pg_result

                    if pg_result.source == RAGSource.RAG_SUCCESS:
                        logger.info(
                            f"✅ PostgreSQL SUCCESS: {len(pg_result.context_docs or [])} documents"
                        )

                        # ✅ NOUVEAU: Générer réponse avec contexte conversationnel si nécessaire
                        if pg_result.context_docs and not pg_result.answer:
                            logger.info(
                                "📝 Génération réponse PostgreSQL avec contexte conversationnel"
                            )
                            pg_result.answer = (
                                await self._generate_response_with_generator(
                                    context_docs=pg_result.context_docs,
                                    query=query,
                                    language=language,
                                    preprocessed_data=preprocessed_data or {},
                                )
                            )

                        pg_result.metadata.update(
                            {
                                "source_type": "postgresql_routing_hint",
                                "routing_hint": "postgresql",
                                "processing_time": time.time() - start_time,
                                "language_used": language,
                                "validation_applied": True,
                                "filters_applied": filters,  # ✅ NOUVEAU
                            }
                        )
                        return pg_result

                    logger.info("⚠️ PostgreSQL NO_RESULTS - fallback vers Weaviate")

                except Exception as e:
                    logger.error(f"❌ Erreur PostgreSQL: {e}", exc_info=True)
                    logger.info("⚠️ Fallback vers Weaviate après erreur PostgreSQL")
            else:
                logger.warning("⚠️ PostgreSQL non disponible malgré routing hint")

        # 🆕 ÉTAPE 2: Respect du routage suggéré Weaviate par OpenAI
        if routing_hint == "weaviate":
            if self._is_qualitative_query(entities):
                logger.info(
                    "✅ Routage Weaviate (suggestion OpenAI respectée pour requête qualitative)"
                )
                return await self._search_weaviate_direct(
                    query,
                    entities,
                    top_k,
                    is_optimization,
                    start_time,
                    language,
                    filters,  # ✅ NOUVEAU paramètre
                    contextual_history,  # ✅ NOUVEAU paramètre
                )
            else:
                logger.info("⚠️ Suggestion Weaviate ignorée (présence âge/métrique)")

        # Vérification âge hors plage avant PostgreSQL
        if self.postgresql_system and self._should_skip_postgresql_for_age(entities):
            logger.info(
                "🔄 Âge hors plage broilers → Weaviate direct (évite double appel)"
            )
            if self.weaviate_core:
                return await self._search_weaviate_direct(
                    query,
                    entities,
                    top_k,
                    is_optimization,
                    start_time,
                    language,
                    filters,  # ✅ NOUVEAU paramètre
                    contextual_history,  # ✅ NOUVEAU paramètre
                )

        # PostgreSQL standard (UN SEUL APPEL) - seulement si pas déjà tenté avec routing hint
        if self.postgresql_system and routing_hint != "postgresql":
            logger.info(
                f"Recherche PostgreSQL standard (langue={language}, filters={filters})"
            )
            result = await self._search_postgresql_once(
                query,
                entities,
                top_k,
                is_optimization,
                language,
                filters,  # ✅ NOUVEAU paramètre
            )

            if result and result.source != RAGSource.NO_RESULTS:
                # ✅ CORRECTION CRITIQUE: Vérifier pertinence AVANT de retourner
                if self._is_result_relevant_to_query(
                    query, result.context_docs, entities
                ):
                    logger.info(
                        f"✅ Résultats PostgreSQL PERTINENTS pour '{query[:50]}...' - retour direct"
                    )

                    # ✅ NOUVEAU: Générer réponse avec contexte conversationnel si nécessaire
                    if result.context_docs and not result.answer:
                        logger.info(
                            "📝 Génération réponse PostgreSQL standard avec contexte conversationnel"
                        )
                        result.answer = await self._generate_response_with_generator(
                            context_docs=result.context_docs,
                            query=query,
                            language=language,
                            preprocessed_data=preprocessed_data or {},
                        )

                    return result
                else:
                    logger.warning(
                        f"⚠️ PostgreSQL retourné {len(result.context_docs)} docs "
                        f"mais NON PERTINENTS pour '{query[:50]}...' → fallback Weaviate"
                    )
                    # Continue vers Weaviate fallback au lieu de return

            else:
                logger.info("⚠️ PostgreSQL sans résultat → fallback Weaviate direct")

        # 🆕 ÉTAPE 3: Fallback Weaviate (comportement original)
        if self.weaviate_core:
            logger.info(
                f"📚 Recherche Weaviate (top_k={top_k}, langue={language}, filters={filters})"
            )
            return await self._search_weaviate_direct(
                query,
                entities,
                top_k,
                is_optimization,
                start_time,
                language,
                filters,  # ✅ NOUVEAU paramètre
                contextual_history,  # ✅ NOUVEAU paramètre
            )

        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Aucune information trouvée pour cette requête.",
            metadata={
                "query_type": "standard",
                "optimization_mode": is_optimization,
                "routing_hint": routing_hint,
                "language_attempted": language,
                "filters_attempted": filters,  # ✅ NOUVEAU
            },
        )

    async def _search_postgresql_once(
        self,
        query: str,
        entities: Dict[str, Any],
        top_k: int,
        is_optimization: bool,
        language: str = "fr",
        filters: Dict[str, Any] = None,  # ✅ NOUVEAU paramètre
    ) -> Optional[RAGResult]:
        """
        Effectue UNE SEULE recherche PostgreSQL
        Retourne None si aucun résultat (pas de retry)
        ✅ VERSION 4.6: Ajout paramètre filters
        """
        if filters is None:
            filters = {}

        try:
            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=entities,
                top_k=top_k,
                filters=filters,  # ✅ NOUVEAU paramètre
            )

            if result and result.source != RAGSource.NO_RESULTS:
                # Enrichissement métadonnées
                if is_optimization:
                    result.metadata["query_mode"] = "optimization"
                    result.metadata["ranking_applied"] = True
                    result.metadata["top_k_used"] = top_k

                result.metadata["search_attempt"] = "postgresql_single"
                result.metadata["language_used"] = language
                result.metadata["filters_applied"] = filters  # ✅ NOUVEAU
                logger.info(
                    f"✅ PostgreSQL ({language}): {len(result.context_docs)} documents trouvés"
                )
                return result
            else:
                logger.info(f"⚠️ PostgreSQL ({language}): 0 documents (pas de retry)")
                return None

        except Exception as e:
            logger.error(f"Erreur recherche PostgreSQL ({language}): {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return None

    def _filter_documents_by_species(
        self, context_docs: List[Dict], target_species: str = "broilers"
    ) -> List[Dict]:
        """
        ✅ MÉTHODE DE FILTRAGE: Filtre les documents pour ne garder que l'espèce cible
        NOTE: Cette méthode est conservée pour compatibilité mais le filtrage
        devrait maintenant se faire au niveau des retrievers via le paramètre filters

        Args:
            context_docs: Liste de documents
            target_species: Espèce cible (défaut: "broilers" pour poulets de chair)

        Returns:
            Liste filtrée de documents
        """
        if not context_docs:
            return []

        filtered_docs = []
        species_counts = {}

        for doc in context_docs:
            # Extraire l'espèce du document
            if isinstance(doc, dict):
                species = doc.get("metadata", {}).get("species", "")
            else:
                species = getattr(doc, "metadata", {}).get("species", "")

            # Compter les espèces pour logging
            species_counts[species] = species_counts.get(species, 0) + 1

            # Filtrer par espèce cible
            if species == target_species:
                filtered_docs.append(doc)

        logger.info(
            f"📊 Filtrage espèce: {len(context_docs)} docs → {len(filtered_docs)} docs "
            f"({target_species}). Distribution: {species_counts}"
        )

        return filtered_docs

    async def _search_weaviate_direct(
        self,
        query: str,
        entities: Dict[str, Any],
        top_k: int,
        is_optimization: bool,
        start_time: float,
        language: str = "fr",
        filters: Dict[str, Any] = None,  # ✅ NOUVEAU paramètre
        contextual_history: str = "",  # ✅ NOUVEAU paramètre pour historique
    ) -> RAGResult:
        """
        Recherche directe dans Weaviate (fallback ou routage suggéré)
        ✅ VERSION 4.6: Ajout paramètre filters
        """
        if filters is None:
            filters = {}

        try:
            weaviate_top_k = 5 if is_optimization else top_k

            logger.info(
                f"Recherche Weaviate (top_k={weaviate_top_k}, langue={language}, filters={filters})"
            )

            result = await self.weaviate_core.search(
                query=query,
                top_k=weaviate_top_k,
                language=language,
                filters=filters,  # ✅ NOUVEAU paramètre
            )

            if result and result.source != RAGSource.NO_RESULTS:
                # ✅ CORRECTION: Vérifier context_docs correctement
                doc_count = len(result.context_docs) if result.context_docs else 0

                # ✅ NOUVEAU: Générer réponse avec contexte conversationnel si nécessaire
                if result.context_docs and not result.answer:
                    logger.info(
                        "📝 Génération réponse Weaviate avec contexte conversationnel"
                    )

                    # Construire preprocessed_data si nécessaire
                    preprocessed_dict = {
                        "contextual_history": contextual_history,
                        "normalized_query": query,
                        "entities": entities,
                        "language": language,
                    }

                    result.answer = await self._generate_response_with_generator(
                        context_docs=result.context_docs,
                        query=query,
                        language=language,
                        preprocessed_data=preprocessed_dict,
                    )

                # Enrichissement métadonnées
                if is_optimization:
                    result.metadata["query_mode"] = "optimization"
                    result.metadata["source"] = "weaviate_optimized"
                else:
                    result.metadata["source"] = "weaviate_fallback"

                result.metadata["top_k_used"] = weaviate_top_k
                result.metadata["processing_time"] = time.time() - start_time
                result.metadata["language_used"] = language
                result.metadata["filters_applied"] = filters  # ✅ NOUVEAU

                logger.info(f"✅ Weaviate ({language}): {doc_count} documents trouvés")
                return result
            else:
                logger.info(f"⚠️ Weaviate ({language}): 0 documents")
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    answer="Aucune information trouvée dans Weaviate.",
                    metadata={
                        "source": "weaviate_fallback",
                        "processing_time": time.time() - start_time,
                        "language_attempted": language,
                        "filters_attempted": filters,  # ✅ NOUVEAU
                    },
                )

        except Exception as e:
            logger.error(f"Erreur recherche Weaviate ({language}): {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Erreur lors de la recherche Weaviate.",
                metadata={
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                    "language_attempted": language,
                    "filters_attempted": filters,  # ✅ NOUVEAU
                },
            )

    async def _generate_response_with_generator(
        self, context_docs: List, query: str, language: str, preprocessed_data: Dict
    ) -> str:
        """
        ✅ NOUVELLE MÉTHODE: Génère une réponse en utilisant le générateur avec historique

        Args:
            context_docs: Documents de contexte récupérés
            query: Question de l'utilisateur
            language: Langue de la réponse
            preprocessed_data: Données prétraitées contenant l'historique

        Returns:
            Réponse générée en texte
        """
        if not self.response_generator:
            logger.warning("Response generator non disponible, retour contexte brut")
            return self._format_context_as_fallback(context_docs)

        try:
            # ✅ BONNE CLÉ: Récupérer l'historique depuis preprocessed_data
            conversation_history = preprocessed_data.get("contextual_history", "")

            logger.info(
                f"📝 Génération réponse avec historique "
                f"(docs={len(context_docs)}, langue={language}, "
                f"historique={'OUI' if conversation_history else 'NON'})"
            )

            response = await self.response_generator.generate_response(
                query=query,
                context_docs=context_docs,
                language=language,
                conversation_context=conversation_history,  # ✅ PASSER L'HISTORIQUE
            )

            return response

        except Exception as e:
            logger.error(f"Erreur génération réponse avec historique: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return self._format_context_as_fallback(context_docs)

    def _format_context_as_fallback(self, context_docs: List) -> str:
        """
        ✅ NOUVELLE MÉTHODE: Formatage fallback si générateur indisponible

        Args:
            context_docs: Documents de contexte

        Returns:
            Texte formaté des documents
        """
        if not context_docs:
            return "Aucun document de contexte disponible."

        formatted_parts = []
        for i, doc in enumerate(context_docs[:5], 1):  # Limite à 5 docs
            content = doc.get("content", "") if isinstance(doc, dict) else str(doc)
            formatted_parts.append(f"[Doc {i}] {content[:200]}...")

        return "\n\n".join(formatted_parts)
