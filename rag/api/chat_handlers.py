# -*- coding: utf-8 -*-
"""
api/chat_handlers.py - Logique de traitement des requêtes de chat
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
api/chat_handlers.py - Logique de traitement des requêtes de chat
Version 5.1.0 - INTÉGRATION ConversationMemory
Le contexte conversationnel est maintenant géré par QueryRouter + ConversationMemory
"""

import time
import asyncio
import logging
from utils.types import Dict, Any, Optional

from config.config import STREAM_CHUNK_LEN
from utils.utilities import (
    safe_get_attribute,
    safe_dict_get,
    sse_event,
    smart_chunk_text,
    get_aviculture_response,
)

# CORRECTION: Import depuis utils au lieu de endpoints_utils
from .utils import (
    safe_serialize_for_json,
)

logger = logging.getLogger(__name__)


class ChatHandlers:
    """
    Gestionnaires de logique métier pour les endpoints de chat

    VERSION 5.1.0 - INTÉGRATION CONVERSATION MEMORY:
    - Double sauvegarde: ConversationMemory + ancien système
    - Initialisation lazy de ConversationMemory
    - QueryRouter dans RAGEngine gère TOUT le routing
    - Cette classe fait l'interface entre endpoints et RAG
    """

    def __init__(self, services: Dict[str, Any]):
        """
        Initialisation simplifiée

        Args:
            services: Services disponibles (health_monitor, etc.)

        Note: context_manager supprimé - le router gère le contexte
        """
        self.services = services
        self._conversation_memory = None  # Lazy initialization

    @property
    def conversation_memory(self):
        """
        Lazy initialization de ConversationMemory

        Returns:
            Instance de ConversationMemory
        """
        if self._conversation_memory is None:
            try:
                from core.memory import ConversationMemory

                # Client Weaviate peut être None pour l'instant
                # ConversationMemory utilisera Redis si disponible
                self._conversation_memory = ConversationMemory(client=None)
                logger.info("✅ ConversationMemory initialisé")
            except Exception as e:
                logger.warning(f"⚠️ Impossible d'initialiser ConversationMemory: {e}")
                self._conversation_memory = None
        return self._conversation_memory

    def get_rag_engine(self):
        """Helper pour récupérer le RAG Engine"""
        health_monitor = self.services.get("health_monitor")
        if health_monitor:
            return health_monitor.get_service("rag_engine_enhanced")
        return None

    async def generate_rag_response(
        self,
        query: str,
        tenant_id: str,
        conversation_id: Optional[str] = None,  # 🆕 ID de session/conversation
        language: str = "fr",
        use_json_search: bool = True,
        genetic_line_filter: Optional[str] = None,
        performance_context: Optional[Dict[str, Any]] = None,
    ):
        """
        Génère une réponse via le RAG Engine

        VERSION 5.1.0:
        - Appel direct au RAG sans pré-traitement
        - Le QueryRouter dans RAGEngine gère:
          * Extraction d'entités
          * Contexte conversationnel (via ConversationMemory)
          * Validation
          * Routing

        Args:
            query: Requête utilisateur
            tenant_id: ID utilisateur/organisation (identifie l'utilisateur)
            conversation_id: ID de conversation (isole les sessions mémoire)
            language: Langue détectée
            use_json_search: Activer recherche JSON
            genetic_line_filter: Filtre lignée génétique
            performance_context: Contexte performance

        Returns:
            RAGResult ou None si erreur
        """
        rag_engine = self.get_rag_engine()

        if not rag_engine or not safe_get_attribute(
            rag_engine, "is_initialized", False
        ):
            logger.error("RAG Engine non disponible ou non initialisé")
            return None

        try:
            if not hasattr(rag_engine, "generate_response"):
                logger.error("RAG Engine sans méthode generate_response")
                return None

            logger.info(
                f"🎯 Appel RAG pour tenant={tenant_id}, "
                f"conversation={conversation_id or 'none'}, lang={language}"
            )

            # Appel RAG - tenant_id identifie l'utilisateur, conversation_id isole la mémoire
            rag_result = await rag_engine.generate_response(
                query=query,
                tenant_id=tenant_id,
                conversation_id=conversation_id,  # 🆕 Passer conversation_id
                language=language,
                use_json_search=use_json_search,
                genetic_line_filter=genetic_line_filter,
                performance_context=performance_context,
                enable_preprocessing=True,
            )

            # Le router a géré la validation et le contexte
            # Vérifier si clarification nécessaire
            if hasattr(rag_result, "metadata"):
                metadata = rag_result.metadata or {}
                if metadata.get("needs_clarification"):
                    logger.info("⚠️ Clarification nécessaire détectée par le router")
                    # Le message de clarification est dans rag_result.answer
                    return rag_result

            return rag_result

        except Exception as e:
            logger.error(f"Erreur generate_response: {e}", exc_info=True)
            return None

    def create_fallback_result(
        self,
        message: str,
        language: str,
        fallback_reason: str,
        total_start_time: float,
        use_json_search: bool = True,
        genetic_line_filter: Optional[str] = None,
    ):
        """
        Crée un résultat de fallback avec réponse aviculture générique

        Args:
            message: Message original
            language: Langue
            fallback_reason: Raison du fallback
            total_start_time: Timestamp de début
            use_json_search: Flag JSON search
            genetic_line_filter: Filtre lignée

        Returns:
            FallbackResult avec réponse générique
        """
        aviculture_response = get_aviculture_response(message, language)

        class FallbackResult:
            def __init__(self, answer, reason):
                self.answer = answer
                self.source = "aviculture_fallback"
                self.confidence = 0.8
                self.processing_time = time.time() - total_start_time
                self.metadata = {
                    "fallback_used": True,
                    "fallback_reason": reason,
                    "source_type": "integrated_knowledge",
                    "json_system_attempted": use_json_search,
                    "genetic_line_filter": genetic_line_filter,
                    "preprocessing_enabled": True,
                    "router_version": "5.1.0",
                }
                self.context_docs = []

        return FallbackResult(aviculture_response, fallback_reason)

    # 🗑️ DEPRECATED - Méthode remplacée par sauvegarde inline avec follow-up support
    # async def _save_to_memory(
    #     self,
    #     tenant_id: str,
    #     message: str,
    #     answer: str,
    #     metadata: Optional[Dict[str, Any]] = None,
    # ) -> None:
    #     """
    #     Sauvegarde dans ConversationMemory (système unique)
    #
    #     Args:
    #         tenant_id: ID utilisateur
    #         message: Question de l'utilisateur
    #         answer: Réponse générée
    #         metadata: Métadonnées optionnelles
    #     """
    #     # Sauvegarde dans ConversationMemory
    #     if self.conversation_memory:
    #         try:
    #             self.conversation_memory.add_exchange(
    #                 tenant_id=tenant_id, question=message, answer=answer
    #             )
    #             logger.debug(f"✅ Sauvegarde ConversationMemory OK pour {tenant_id}")
    #         except Exception as e:
    #             logger.error(f"❌ Erreur sauvegarde ConversationMemory: {e}")
    #     else:
    #         logger.warning(f"⚠️ ConversationMemory non disponible pour {tenant_id}")

    async def generate_streaming_response(
        self,
        rag_result: Any,
        message: str,
        tenant_id: str,
        language: str,
        total_processing_time: float,
        conversation_id: Optional[str] = None,  # 🆕 ID de conversation pour mémoire
    ):
        """
        Génère un flux de réponse SSE (Server-Sent Events)

        VERSION 5.1.0:
        - Double sauvegarde mémoire (ConversationMemory + ancien)
        - Métadonnées enrichies
        - Plus de gestion de clarification ici
        - Le router a déjà géré tout le contexte

        Args:
            rag_result: Résultat du RAG Engine
            message: Message original
            tenant_id: ID utilisateur
            language: Langue
            total_processing_time: Temps total de traitement
            conversation_id: ID de conversation (pour isolation mémoire)

        Yields:
            Events SSE formatés
        """
        try:
            # Extraction métadonnées
            metadata = safe_get_attribute(rag_result, "metadata", {}) or {}
            source = safe_get_attribute(rag_result, "source", "unknown")
            confidence = safe_get_attribute(rag_result, "confidence", 0.5)
            processing_time = safe_get_attribute(rag_result, "processing_time", 0)

            # Normaliser source (peut être un enum)
            if hasattr(source, "value"):
                source = source.value
            else:
                source = str(source)

            # Event START
            logger.info(
                f"📤 Sending START event with source='{source}', confidence={confidence}"
            )
            start_data = {
                "type": "start",
                "source": source,
                "confidence": float(confidence),
                "processing_time": float(processing_time),
                "fallback_used": safe_dict_get(metadata, "fallback_used", False),
                "architecture": "query-router-v5.1",
                "serialization_version": "optimized_cached",
                "preprocessing_enabled": True,
                "router_managed": True,
                "memory_enabled": self.conversation_memory is not None,
                "needs_clarification": metadata.get("needs_clarification", False),
                "missing_fields": metadata.get("missing_fields", []),
                "json_system_used": metadata.get("json_system", {}).get("used", False),
                "json_results_count": metadata.get("json_system", {}).get(
                    "results_count", 0
                ),
                "genetic_line_detected": metadata.get("json_system", {}).get(
                    "genetic_line_filter"
                ),
            }

            yield sse_event(safe_serialize_for_json(start_data))

            # Extraction de la réponse (avec fallbacks)
            answer = safe_get_attribute(rag_result, "answer", "")
            if not answer:
                answer = safe_get_attribute(rag_result, "response", "")
                if not answer:
                    answer = safe_get_attribute(rag_result, "text", "")
                    if not answer:
                        # Dernier fallback: réponse aviculture
                        answer = get_aviculture_response(message, language)

            # Streaming de la réponse par chunks
            if answer:
                chunks = smart_chunk_text(str(answer), STREAM_CHUNK_LEN)
                for i, chunk in enumerate(chunks):
                    yield sse_event(
                        {"type": "chunk", "content": chunk, "chunk_index": i}
                    )
                    await asyncio.sleep(0.01)  # Petit délai pour fluidité

            # Envoyer follow-up proactif si disponible (message séparé)
            proactive_followup = metadata.get("proactive_followup")
            followup_to_save = None  # 🆕 Variable pour sauvegarder le follow-up
            if proactive_followup and isinstance(proactive_followup, str):
                logger.info(
                    f"📤 Envoi follow-up proactif: {proactive_followup[:80]}..."
                )
                followup_to_save = proactive_followup  # 🆕 Capturer pour sauvegarde
                yield sse_event(
                    {
                        "type": "proactive_followup",
                        "suggestion": proactive_followup,
                    }
                )
                await asyncio.sleep(0.01)

            # Extraction documents utilisés
            context_docs = safe_get_attribute(rag_result, "context_docs", [])
            if not isinstance(context_docs, list):
                context_docs = []

            documents_used = 0
            if hasattr(rag_result, "metadata") and rag_result.metadata:
                documents_used = rag_result.metadata.get("documents_used", 0)

            if documents_used == 0:
                documents_used = len(context_docs)

            # 🖼️ Extraction des images associées
            images = safe_get_attribute(rag_result, "images", [])
            if not isinstance(images, list):
                images = []
            logger.info(f"🖼️ Retrieved {len(images)} images for response")

            # Event END
            # 🔍 DEBUG: Extract CoT fields before building end_data
            cot_thinking = safe_get_attribute(rag_result, "cot_thinking", None)
            cot_analysis = safe_get_attribute(rag_result, "cot_analysis", None)
            has_cot_structure = safe_get_attribute(
                rag_result, "has_cot_structure", False
            )

            logger.info(
                f"🧠 END event CoT fields - has_cot: {has_cot_structure}, thinking: {len(cot_thinking or '') } chars, analysis: {len(cot_analysis or '')} chars"
            )

            end_data = {
                "type": "end",
                "total_time": total_processing_time,
                "confidence": float(confidence),
                "documents_used": documents_used,
                "source": source,
                "architecture": "query-router-v5.1",
                "preprocessing_enabled": True,
                "router_managed": True,
                "memory_enabled": self.conversation_memory is not None,
                "needs_clarification": metadata.get("needs_clarification", False),
                "is_contextual": metadata.get("is_contextual", False),
                "json_system_used": metadata.get("json_system", {}).get("used", False),
                "json_results_count": metadata.get("json_system", {}).get(
                    "results_count", 0
                ),
                "genetic_lines_detected": metadata.get("json_system", {}).get(
                    "genetic_lines_detected", []
                ),
                "detection_version": "5.1.0_conversation_memory",
                # 🧠 Chain-of-Thought sections for PostgreSQL storage
                "cot_thinking": cot_thinking,
                "cot_analysis": cot_analysis,
                "has_cot_structure": has_cot_structure,
                # 🖼️ Associated images
                "images": images,
            }

            serialized_data = safe_serialize_for_json(end_data)
            logger.info(f"🔍 END event full data: {str(serialized_data)[:500]}")
            yield sse_event(serialized_data)

            # Sauvegarder dans les deux systèmes de mémoire
            # Seulement si c'est une vraie réponse (pas une clarification)
            if answer and source and not metadata.get("needs_clarification"):
                # 🆕 Utiliser conversation_id comme clé mémoire (fallback to tenant_id)
                memory_key = conversation_id or tenant_id
                logger.debug(f"💾 Saving to memory with key: {memory_key}")

                # 🆕 Sauvegarder avec le follow-up si présent
                if self.conversation_memory:
                    try:
                        self.conversation_memory.add_exchange(
                            tenant_id=memory_key,
                            question=message,
                            answer=str(answer),
                            followup=followup_to_save,  # 🆕 Inclure le follow-up
                        )
                        logger.debug(
                            f"✅ Sauvegarde ConversationMemory OK pour {memory_key} (with followup: {followup_to_save is not None})"
                        )
                    except Exception as e:
                        logger.error(f"❌ Erreur sauvegarde ConversationMemory: {e}")
                else:
                    logger.warning(
                        f"⚠️ ConversationMemory non disponible pour {memory_key}"
                    )

        except Exception as e:
            logger.error(f"Erreur streaming: {e}", exc_info=True)
            yield sse_event({"type": "error", "message": str(e)})

    def get_status(self) -> Dict[str, Any]:
        """
        Status des handlers

        Returns:
            Dict avec informations de status
        """
        rag_engine = self.get_rag_engine()

        return {
            "version": "5.1.0",
            "architecture": "query-router-integrated",
            "rag_engine_available": rag_engine is not None,
            "rag_engine_initialized": (
                safe_get_attribute(rag_engine, "is_initialized", False)
                if rag_engine
                else False
            ),
            "context_management": "router_managed",
            "clarification_management": "router_managed",
            "conversation_memory_enabled": self.conversation_memory is not None,
            "dual_memory_system": True,  # Nouveau + ancien
        }
