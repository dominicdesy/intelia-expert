# -*- coding: utf-8 -*-
"""
api/chat_handlers.py - Logique de traitement des requêtes de chat
Version 4.4.0 - MÉMOIRE CONVERSATIONNELLE POUR RÉSOLUTION CONTEXTUELLE
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional

from config.config import STREAM_CHUNK_LEN
from utils.utilities import (
    safe_get_attribute,
    safe_dict_get,
    sse_event,
    smart_chunk_text,
    get_aviculture_response,
)
from .endpoints_utils import (
    safe_serialize_for_json,
    add_to_conversation_memory,
)
from .conversation_context import ConversationContextManager

logger = logging.getLogger(__name__)


class ChatHandlers:
    """Gestionnaires de logique métier pour les endpoints de chat"""

    # Limite de tentatives de clarification (Test 8)
    MAX_CLARIFICATION_ATTEMPTS = 3

    def __init__(
        self, context_manager: ConversationContextManager, services: Dict[str, Any]
    ):
        self.context_manager = context_manager
        self.services = services

    def get_rag_engine(self):
        """Helper pour récupérer le RAG Engine"""
        health_monitor = self.services.get("health_monitor")
        if health_monitor:
            return health_monitor.get_service("rag_engine_enhanced")
        return None

    async def handle_clarification_abandonment(
        self,
        message: str,
        tenant_id: str,
        pending_context: Dict,
        language: str,
        total_start_time: float,
    ):
        """
        Gère l'abandon d'une clarification par l'utilisateur
        Retourne une réponse générique appropriée
        """
        logger.info(f"Abandon clarification pour {tenant_id}")

        # Effacer le contexte en attente
        self.context_manager.clear_pending(tenant_id)

        # Extraire contexte partiel
        partial_entities = pending_context.get("partial_entities", {})
        age = partial_entities.get("age_days")

        # Générer réponse générique
        generic_responses = {
            "fr": f"Je comprends. Voici une moyenne générale pour les poulets de chair{' à ' + str(age) + ' jours' if age else ''}: Le poids moyen se situe entre 300-2500g selon la souche et l'âge. L'indice de conversion (FCR) est généralement de 1.5-1.9.",
            "en": f"I understand. Here's a general average for broilers{' at ' + str(age) + ' days' if age else ''}: Average weight ranges from 300-2500g depending on strain and age. Feed conversion ratio (FCR) is typically 1.5-1.9.",
            "es": f"Entiendo. Aquí hay un promedio general para pollos de engorde{' a ' + str(age) + ' días' if age else ''}: El peso promedio varía entre 300-2500g según la cepa y edad. El índice de conversión (FCR) es típicamente 1.5-1.9.",
        }

        generic_answer = generic_responses.get(language, generic_responses["fr"])

        # Créer résultat générique
        class GenericResult:
            def __init__(self, answer):
                self.answer = answer
                self.source = "generic_fallback"
                self.confidence = 0.6
                self.processing_time = time.time() - total_start_time
                self.metadata = {
                    "clarification_abandoned": True,
                    "fallback_used": True,
                }
                self.context_docs = []

        return GenericResult(generic_answer)

    async def handle_ambiguous_response(
        self,
        message: str,
        tenant_id: str,
        pending_context: Dict,
        language: str,
        total_start_time: float,
    ):
        """
        Gère une réponse ambiguë de l'utilisateur

        ✅ Test 8: Limite de tentatives + réponse générique après MAX_CLARIFICATION_ATTEMPTS
        """
        logger.warning(f"⚠️ Réponse ambiguë détectée: {message}")

        # Incrémenter compteur AVANT vérification
        self.context_manager.increment_clarification_attempt(tenant_id)

        # ✅ VÉRIFIER LIMITE DE TENTATIVES (Test 8)
        attempts = pending_context.get("clarification_attempts", 0)

        if attempts >= self.MAX_CLARIFICATION_ATTEMPTS:
            logger.warning(
                f"🛑 Abandon après {attempts} tentatives - réponse générique"
            )

            # Nettoyer contexte
            self.context_manager.clear_pending(tenant_id)

            # Générer réponse générique avec disclaimer
            fallback_messages = {
                "fr": (
                    "Je comprends que vous n'avez pas l'information exacte sous la main. "
                    "Voici des données générales qui pourraient vous aider :\n\n"
                    "**Pour les poulets de chair (broilers) :**\n"
                    "- Poids moyen : 300g (J1) à 2500g (J42) selon la souche\n"
                    "- FCR moyen : 1.5-1.9 selon l'âge et la génétique\n"
                    "- Consommation eau : 1.8-2.2x la consommation d'aliment\n\n"
                    "Pour une réponse plus précise, n'hésitez pas à me donner la race et l'âge exacts."
                ),
                "en": (
                    "I understand you don't have the exact information at hand. "
                    "Here's general data that might help:\n\n"
                    "**For broilers:**\n"
                    "- Average weight: 300g (D1) to 2500g (D42) depending on strain\n"
                    "- Average FCR: 1.5-1.9 depending on age and genetics\n"
                    "- Water consumption: 1.8-2.2x feed consumption\n\n"
                    "For a more precise answer, feel free to provide the exact breed and age."
                ),
                "es": (
                    "Entiendo que no tiene la información exacta a mano. "
                    "Aquí hay datos generales que podrían ayudar:\n\n"
                    "**Para pollos de engorde:**\n"
                    "- Peso promedio: 300g (D1) a 2500g (D42) según la cepa\n"
                    "- FCR promedio: 1.5-1.9 según edad y genética\n"
                    "- Consumo de agua: 1.8-2.2x consumo de alimento\n\n"
                    "Para una respuesta más precisa, proporcione la raza y edad exactas."
                ),
            }

            fallback_message = fallback_messages.get(language, fallback_messages["en"])

            class FallbackResult:
                def __init__(self, answer):
                    self.answer = answer
                    self.source = "clarification_limit_exceeded"
                    self.confidence = 0.7
                    self.processing_time = time.time() - total_start_time
                    self.metadata = {
                        "clarification_abandoned": True,
                        "clarification_attempts": attempts,
                        "fallback_used": True,
                    }
                    self.context_docs = []

            return FallbackResult(fallback_message)

        # Si pas encore à la limite, générer demande plus précise
        missing_fields = pending_context.get("missing_fields", [])
        retry_message = self.context_manager.generate_clarification_retry(
            message,
            missing_fields[0] if missing_fields else "breed",
            language,
        )

        class AmbiguityResult:
            def __init__(self, question):
                self.answer = question
                self.source = "needs_clarification"
                self.confidence = 0.8
                self.processing_time = time.time() - total_start_time
                self.metadata = {
                    "needs_clarification": True,
                    "ambiguous_response_detected": True,
                    "clarification_pending": True,
                    "clarification_attempts": attempts,
                }
                self.context_docs = []

        return AmbiguityResult(retry_message)

    async def handle_clarification_context(
        self, message: str, tenant_id: str, language: str, total_start_time: float
    ) -> Optional[Any]:
        """
        Gère le contexte de clarification et retourne un résultat si nécessaire
        Retourne None si le flux normal doit continuer

        ✅ VERSION 4.3.1 - CORRECTION MAJEURE:
        - Fusion des entités AVANT de retourner pour traitement
        - Flag continue_processing pour reprendre le flux RAG
        - Passage des entités fusionnées au RAG Engine
        """
        pending_context = self.context_manager.get_pending(tenant_id)

        if not pending_context:
            return None

        # ÉTAPE 1: Vérifier abandon
        if self.context_manager.detect_clarification_abandon(message):
            return await self.handle_clarification_abandonment(
                message, tenant_id, pending_context, language, total_start_time
            )

        # ÉTAPE 2: Vérifier si c'est une réponse à la clarification
        if self.context_manager.is_clarification_response(message, pending_context):
            logger.info(f"Détection réponse clarification pour {tenant_id}")

            # ÉTAPE 3: Vérifier ambiguïté AVANT accumulation
            if self.context_manager.detect_ambiguous_response(message):
                return await self.handle_ambiguous_response(
                    message, tenant_id, pending_context, language, total_start_time
                )

            # ✅ ÉTAPE 4: FUSIONNER LES ENTITÉS (correction majeure)
            self.context_manager.update_accumulated_query(tenant_id, message)

            # Récupérer le contexte mis à jour avec les entités fusionnées
            updated_context = self.context_manager.get_pending(tenant_id)
            accumulated_query = updated_context["original_query"]
            partial_entities = updated_context.get("partial_entities", {})

            logger.info(f"🔄 Reprise avec entités fusionnées: {partial_entities}")
            logger.info(f"📝 Requête accumulée: {accumulated_query}")

            # Préserver la langue originale
            original_language = updated_context.get("original_language")
            if original_language:
                language = original_language
                logger.info(f"Langue restaurée depuis contexte: {original_language}")

            # ✅ RETOURNER UN FLAG POUR CONTINUER LE TRAITEMENT
            # Au lieu de retourner directement la requête, on indique qu'il faut
            # continuer le traitement avec les entités fusionnées
            return {
                "continue_processing": True,
                "accumulated_query": accumulated_query,
                "merged_entities": partial_entities,
                "language": language,
            }

        return None

    async def generate_rag_response(
        self,
        query: str,
        tenant_id: str,
        language: str,
        use_json_search: bool = True,
        genetic_line_filter: Optional[str] = None,
        performance_context: Optional[Dict[str, Any]] = None,
    ):
        """
        Génère une réponse via le RAG Engine
        Retourne le résultat ou None si erreur

        ✅ VERSION 4.4.0: Support mémoire conversationnelle
        - Récupération du contexte de la dernière requête réussie
        - Transmission au RAG Engine pour résolution contextuelle
        """
        rag_engine = self.get_rag_engine()

        if not rag_engine or not safe_get_attribute(
            rag_engine, "is_initialized", False
        ):
            return None

        try:
            if not hasattr(rag_engine, "generate_response"):
                return None

            # ✅ NOUVEAU v4.4: Récupérer le contexte conversationnel
            conversation_context = self.context_manager.get_last_context(tenant_id)

            if conversation_context:
                logger.info(f"📖 Utilisation contexte conversationnel pour {tenant_id}")
                logger.debug(
                    f"   Previous: {conversation_context.get('previous_query', 'N/A')[:50]}..."
                )
                logger.debug(
                    f"   Entities: breed={conversation_context.get('breed')}, "
                    f"age={conversation_context.get('age_days')}, "
                    f"sex={conversation_context.get('sex')}"
                )

            logger.info(f"🎯 Appel RAG avec performance_context: {performance_context}")

            rag_result = await rag_engine.generate_response(
                query=query,
                tenant_id=tenant_id,
                language=language,
                use_json_search=use_json_search,
                genetic_line_filter=genetic_line_filter,
                performance_context=performance_context,
                conversation_context=conversation_context,  # ✅ NOUVEAU v4.4
                enable_preprocessing=True,
            )

            return rag_result

        except Exception as e:
            logger.error(f"Erreur generate_response: {e}")
            return None

    async def handle_validation_status(
        self,
        rag_result: Any,
        message: str,
        tenant_id: str,
        language: str,
        total_start_time: float,
    ) -> Optional[Any]:
        """
        Vérifie le statut de validation et retourne un résultat de clarification si nécessaire
        Retourne None si validation OK

        ✅ VERSION 4.4.0 - MÉMOIRE CONVERSATIONNELLE:
        - Stocke le contexte après validation réussie
        - Permet la résolution de références contextuelles ("at the same age", "for females")

        ✅ VERSION 4.3.1 - CORRECTION CRITIQUE:
        - Stocke les entités extraites lors du premier appel à mark_pending()
        - Permet la fusion d'entités dans les échanges suivants
        """
        if not hasattr(rag_result, "metadata"):
            return None

        metadata = rag_result.metadata
        validation_status = metadata.get("validation_status")

        if validation_status != "needs_fallback":
            # Validation réussie: effacer le contexte en attente
            pending_context = self.context_manager.get_pending(tenant_id)
            if pending_context:
                logger.info(f"Requête complète validée pour {tenant_id}")
                self.context_manager.clear_pending(tenant_id)

            # ✅ NOUVEAU v4.4: Stocker le contexte conversationnel après succès
            enhanced_entities = metadata.get("enhanced_entities", {})

            # Ne stocker que si on a les informations essentielles
            if enhanced_entities and enhanced_entities.get("breed"):
                self.context_manager.store_last_successful_query(
                    tenant_id=tenant_id,
                    query=message,
                    entities=enhanced_entities,
                    language=language,
                )
                logger.info(f"💾 Contexte conversationnel stocké pour {tenant_id}")
                logger.debug(
                    f"   Stored: breed={enhanced_entities.get('breed')}, "
                    f"age={enhanced_entities.get('age_days')}, "
                    f"sex={enhanced_entities.get('sex')}, "
                    f"metric={enhanced_entities.get('metric_type')}"
                )

            return None

        # Contexte insuffisant détecté
        logger.warning(f"Contexte insuffisant détecté pour {tenant_id}")

        missing_fields = metadata.get("missing_fields", [])
        suggestions = metadata.get("suggestions", {})

        # ✅ CORRECTION CRITIQUE: Extraire les entités détectées depuis metadata
        detected_entities = metadata.get("detected_entities", {})

        logger.info(f"🔍 Entités détectées par le validator: {detected_entities}")

        # Si pas encore en attente, marquer maintenant AVEC les entités
        pending_context = self.context_manager.get_pending(tenant_id)
        if not pending_context:
            # ✅ PASSER LES ENTITÉS DÉTECTÉES lors de la création du contexte
            self.context_manager.mark_pending(
                tenant_id=tenant_id,
                original_query=message,
                missing_fields=missing_fields,
                suggestions=suggestions,
                language=language,
                partial_entities=detected_entities,  # ✅ AJOUT CRITIQUE
            )
            logger.info(
                f"✅ Contexte créé avec entités partielles: {detected_entities}"
            )
        else:
            # Mettre à jour les champs manquants
            self.context_manager.pending_clarifications[tenant_id][
                "missing_fields"
            ] = missing_fields
            self.context_manager.pending_clarifications[tenant_id][
                "suggestions"
            ] = suggestions

            # ✅ METTRE À JOUR les entités partielles si de nouvelles sont détectées
            existing_entities = self.context_manager.pending_clarifications[
                tenant_id
            ].get("partial_entities", {})
            # Fusionner : nouvelles entités complètent les existantes
            for key, value in detected_entities.items():
                if value is not None and (
                    not existing_entities.get(key) or existing_entities.get(key) is None
                ):
                    existing_entities[key] = value

            self.context_manager.pending_clarifications[tenant_id][
                "partial_entities"
            ] = existing_entities

            logger.info(f"✅ Entités partielles mises à jour: {existing_entities}")

        # Utiliser le message déjà généré par le validator
        clarification_msg = rag_result.answer

        # Fallback si pas de message (sécurité)
        if not clarification_msg:
            from .conversation_context import generate_clarification_question

            clarification_msg = generate_clarification_question(
                missing_fields=missing_fields,
                suggestions=suggestions,
                language=language,
            )

        logger.info(f"Question de clarification: {clarification_msg[:100]}...")

        # Créer un résultat spécial pour la clarification
        class ClarificationResult:
            def __init__(self, question, missing):
                self.answer = question
                self.source = "needs_clarification"
                self.confidence = 0.9
                self.processing_time = time.time() - total_start_time
                self.metadata = {
                    "needs_clarification": True,
                    "missing_fields": missing,
                    "original_query": message,
                    "clarification_pending": True,
                }
                self.context_docs = []

        return ClarificationResult(clarification_msg, missing_fields)

    def create_fallback_result(
        self,
        message: str,
        language: str,
        fallback_reason: str,
        total_start_time: float,
        use_json_search: bool = True,
        genetic_line_filter: Optional[str] = None,
    ):
        """Crée un résultat de fallback avec réponse aviculture"""
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
                }
                self.context_docs = []

        return FallbackResult(aviculture_response, fallback_reason)

    async def generate_streaming_response(
        self,
        rag_result: Any,
        message: str,
        tenant_id: str,
        language: str,
        total_processing_time: float,
    ):
        """
        Génère un flux de réponse SSE
        """
        try:
            metadata = safe_get_attribute(rag_result, "metadata", {}) or {}
            source = safe_get_attribute(rag_result, "source", "unknown")
            confidence = safe_get_attribute(rag_result, "confidence", 0.5)
            processing_time = safe_get_attribute(rag_result, "processing_time", 0)

            if hasattr(source, "value"):
                source = source.value
            else:
                source = str(source)

            # Récupérer le contexte actuel pour les métadonnées
            current_pending = self.context_manager.get_pending(tenant_id)

            start_data = {
                "type": "start",
                "source": source,
                "confidence": float(confidence),
                "processing_time": float(processing_time),
                "fallback_used": safe_dict_get(metadata, "fallback_used", False),
                "architecture": "modular-endpoints-conversational-memory",
                "serialization_version": "optimized_cached",
                "preprocessing_enabled": True,
                "needs_clarification": metadata.get("needs_clarification", False),
                "clarification_count": (
                    current_pending.get("clarification_count", 0)
                    if current_pending
                    else 0
                ),
                "clarification_attempts": (
                    current_pending.get("clarification_attempts", 0)
                    if current_pending
                    else 0
                ),
                "ambiguous_response_detected": metadata.get(
                    "ambiguous_response_detected", False
                ),
                "clarification_abandoned": metadata.get(
                    "clarification_abandoned", False
                ),
                "json_system_used": metadata.get("json_system", {}).get("used", False),
                "json_results_count": metadata.get("json_system", {}).get(
                    "results_count", 0
                ),
                "genetic_line_detected": metadata.get("json_system", {}).get(
                    "genetic_line_filter"
                ),
            }

            yield sse_event(safe_serialize_for_json(start_data))

            answer = safe_get_attribute(rag_result, "answer", "")
            if not answer:
                answer = safe_get_attribute(rag_result, "response", "")
                if not answer:
                    answer = safe_get_attribute(rag_result, "text", "")
                    if not answer:
                        answer = get_aviculture_response(message, language)

            if answer:
                chunks = smart_chunk_text(str(answer), STREAM_CHUNK_LEN)
                for i, chunk in enumerate(chunks):
                    yield sse_event(
                        {"type": "chunk", "content": chunk, "chunk_index": i}
                    )
                    await asyncio.sleep(0.01)

            context_docs = safe_get_attribute(rag_result, "context_docs", [])
            if not isinstance(context_docs, list):
                context_docs = []

            documents_used = 0
            if hasattr(rag_result, "metadata") and rag_result.metadata:
                documents_used = rag_result.metadata.get("documents_used", 0)

            if documents_used == 0:
                documents_used = len(context_docs)

            end_data = {
                "type": "end",
                "total_time": total_processing_time,
                "confidence": float(confidence),
                "documents_used": documents_used,
                "source": source,
                "architecture": "modular-endpoints-conversational-memory",
                "preprocessing_enabled": True,
                "needs_clarification": metadata.get("needs_clarification", False),
                "clarification_pending": metadata.get("clarification_pending", False),
                "clarification_count": (
                    current_pending.get("clarification_count", 0)
                    if current_pending
                    else 0
                ),
                "clarification_attempts": (
                    current_pending.get("clarification_attempts", 0)
                    if current_pending
                    else 0
                ),
                "ambiguous_response_detected": metadata.get(
                    "ambiguous_response_detected", False
                ),
                "clarification_abandoned": metadata.get(
                    "clarification_abandoned", False
                ),
                "json_system_used": metadata.get("json_system", {}).get("used", False),
                "json_results_count": metadata.get("json_system", {}).get(
                    "results_count", 0
                ),
                "genetic_lines_detected": metadata.get("json_system", {}).get(
                    "genetic_lines_detected", []
                ),
                "detection_version": "4.4.0_conversational_memory",
            }

            yield sse_event(safe_serialize_for_json(end_data))

            if answer and source and not metadata.get("needs_clarification"):
                add_to_conversation_memory(
                    tenant_id, message, str(answer), "rag_enhanced_json"
                )

        except Exception as e:
            logger.error(f"Erreur streaming: {e}")
            yield sse_event({"type": "error", "message": str(e)})
