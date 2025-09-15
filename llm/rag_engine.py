# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Enhanced avec Cache Redis externe optimisé
Version Production Intégrée pour Intelia Expert Aviculture
Version corrigée pour Weaviate 4.16.9 - Septembre 2025
CORRECTIONS APPLIQUÉES: 
- OpenAI init sans proxies
- Guardrails uniques (suppression doublons)
- Intégration HybridRetriever paramétrable
- Optimisations cache sémantique + intent processor + diagnostics enrichis
"""

import os
import asyncio
import logging
import time
import numpy as np
import httpx
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Imports des modules refactorisés
from config import *
from imports_and_dependencies import *
from data_models import RAGResult, RAGSource, Document
from utilities import METRICS, detect_language_enhanced, build_where_filter
from embedder import OpenAIEmbedder
from retriever import HybridWeaviateRetriever
from generators import EnhancedResponseGenerator
from ood_detector import EnhancedOODDetector
from memory import ConversationMemory

# MODIFICATION: Import guardrails unique + HybridRetriever paramétrable
from advanced_guardrails import AdvancedResponseGuardrails  # garder une seule implémentation
from hybrid_retriever import hybrid_search
DEFAULT_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.6"))

# Configuration logging
logger = logging.getLogger(__name__)

class InteliaRAGEngine:
    """RAG Engine principal avec cache externe optimisé et corrections appliquées"""
    
    def __init__(self, openai_client: AsyncOpenAI = None):
        self.openai_client = openai_client or self._build_openai_client()
        
        # Composants principaux
        self.cache_manager = None
        self.embedder = None
        self.retriever = None
        self.generator = None
        self.verifier = None
        self.memory = None
        self.intent_processor = None
        self.ood_detector = None
        self.guardrails = None
        self.weaviate_client = None
        
        # État
        self.is_initialized = False
        self.degraded_mode = False
        
        # MODIFICATION: Stats étendues avec nouvelles métriques
        self.optimization_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "semantic_cache_hits": 0,
            "fallback_cache_hits": 0,
            "hybrid_searches": 0,
            "guardrail_violations": 0,
            "entity_enrichments": 0,
            "api_corrections": 0,
            "external_cache_used": False,
            "semantic_debug_requests": 0,
            "explain_score_extractions": 0,
            "cache_semantic_reasoning_failures": 0,
            "intent_coverage_stats": defaultdict(int),
            "weaviate_capabilities": {},
            "dynamic_ood_threshold_adjustments": 0,
            "conversation_context_usage": 0
        }
    
    def _build_openai_client(self) -> AsyncOpenAI:
        """MODIFICATION: Construit le client OpenAI sans proxies"""
        try:
            http_client = httpx.AsyncClient(timeout=30.0)
            # NE PAS passer proxies au client (erreur observée)
            return AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
        except Exception as e:
            logger.warning(f"Erreur client OpenAI: {e}")
            # Fallback sans http_client personnalisé
            return AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def initialize(self):
        """MODIFICATION: Initialisation avec await cache manager + orchestration corrigée"""
        if self.is_initialized:
            return
            
        logger.info("Initialisation RAG Engine Enhanced avec cache externe")
        
        if not OPENAI_AVAILABLE or not WEAVIATE_AVAILABLE:
            self.degraded_mode = True
            logger.warning("Mode dégradé activé")
            self.is_initialized = True
            return
        
        try:
            # MODIFICATION: 1. Cache Redis externe avec await obligatoire
            if CACHE_ENABLED and EXTERNAL_CACHE_AVAILABLE:
                self.cache_manager = RAGCacheManager()
                # CRITICAL: Assurer que l'initialisation est awaited
                await self.cache_manager.initialize()
                if self.cache_manager.enabled:
                    self.optimization_stats["external_cache_used"] = True
                    logger.info("✅ Cache Redis externe activé et initialisé")
                else:
                    logger.warning("⚠️ Cache Redis externe désactivé après initialisation")
            
            # 2. Connexion Weaviate
            await self._connect_weaviate()
            
            # 3. Composants de base avec ordre corrigé
            self.embedder = OpenAIEmbedder(self.openai_client, self.cache_manager)
            self.memory = ConversationMemory(self.openai_client)
            self.ood_detector = EnhancedOODDetector()
            
            # 4. Retriever hybride avec diagnostic intégré
            if self.weaviate_client:
                self.retriever = HybridWeaviateRetriever(self.weaviate_client)
                # Exécuter diagnostic au démarrage si activé
                if ENABLE_API_DIAGNOSTICS:
                    logger.info("🔍 Exécution diagnostic API Weaviate...")
                    await self.retriever.diagnose_weaviate_api()
                    # MODIFICATION: Stocker les capacités dans les stats
                    self.optimization_stats["weaviate_capabilities"] = self.retriever.api_capabilities.copy()
            
            # 5. Générateur enrichi
            if ENTITY_ENRICHMENT_ENABLED:
                self.generator = EnhancedResponseGenerator(self.openai_client, self.cache_manager)
            
            # 6. MODIFICATION: Guardrails uniques (suppression doublons)
            if GUARDRAILS_AVAILABLE:
                self.guardrails = self._create_response_guardrails(self.openai_client, GUARDRAILS_LEVEL)
            
            # 7. Intent processor
            if INTENT_PROCESSOR_AVAILABLE:
                self.intent_processor = create_intent_processor()
            
            self.is_initialized = True
            logger.info("✅ RAG Engine Enhanced initialisé avec succès")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            self.degraded_mode = True
            self.is_initialized = True
    
    def _create_response_guardrails(self, openai_client, level: str):
        """MODIFICATION: Factory pour guardrails uniques"""
        try:
            return AdvancedResponseGuardrails(openai_client, level)
        except Exception as e:
            logger.warning(f"Erreur création guardrails: {e}")
            return None
    
    async def _connect_weaviate(self):
        """Connexion Weaviate corrigée pour v4.16.9"""
        if WEAVIATE_V4:
            try:
                if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                    self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                        cluster_url=WEAVIATE_URL,
                        auth_credentials=wvc.init.Auth.api_key(WEAVIATE_API_KEY),
                        headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                    )
                else:
                    if WEAVIATE_API_KEY:
                        self.weaviate_client = weaviate.connect_to_local(
                            host=WEAVIATE_URL.replace("http://", "").replace("https://", "").split(":")[0],
                            port=int(WEAVIATE_URL.split(":")[-1]) if ":" in WEAVIATE_URL else 8080,
                            auth_credentials=wvc.init.Auth.api_key(WEAVIATE_API_KEY),
                            headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                        )
                    else:
                        self.weaviate_client = weaviate.connect_to_local(
                            host=WEAVIATE_URL.replace("http://", "").replace("https://", "").split(":")[0],
                            port=int(WEAVIATE_URL.split(":")[-1]) if ":" in WEAVIATE_URL else 8080,
                            headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                        )
                
                def _test_connection():
                    return self.weaviate_client.is_ready()
                
                is_ready = await anyio.to_thread.run_sync(_test_connection)
                
                if not is_ready:
                    raise Exception("Weaviate not ready")
                    
            except Exception as e:
                logger.error(f"Erreur connexion Weaviate v4: {e}")
                try:
                    if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                        auth_config = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
                        self.weaviate_client = weaviate.Client(
                            url=WEAVIATE_URL,
                            auth_client_secret=auth_config,
                            additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                        )
                    else:
                        self.weaviate_client = weaviate.Client(
                            url=WEAVIATE_URL,
                            additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                        )
                    
                    def _check_fallback():
                        return self.weaviate_client.is_ready()
                    
                    is_ready = await anyio.to_thread.run_sync(_check_fallback)
                    
                    if not is_ready:
                        raise Exception("Weaviate fallback failed")
                        
                    logger.info("Fallback vers Weaviate v3 réussi")
                    
                except Exception as fallback_error:
                    logger.error(f"Erreur fallback Weaviate: {fallback_error}")
                    raise
        else:
            if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                auth_config = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
                self.weaviate_client = weaviate.Client(
                    url=WEAVIATE_URL,
                    auth_client_secret=auth_config,
                    additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
            else:
                self.weaviate_client = weaviate.Client(
                    url=WEAVIATE_URL,
                    additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
            
            def _check_connection():
                return self.weaviate_client.is_ready()
            
            is_ready = await anyio.to_thread.run_sync(_check_connection)
            
            if not is_ready:
                raise Exception("Weaviate not ready")
    
    async def process_query(self, query: str, language: str = "fr", tenant_id: str = "") -> RAGResult:
        """MODIFICATION: Traitement avec toutes les optimisations appliquées + HybridRetriever"""
        if not RAG_ENABLED:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "rag_disabled"})
        
        if not self.is_initialized:
            await self.initialize()
        
        if self.degraded_mode:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "degraded_mode"})
        
        start_time = time.time()
        METRICS.inc("requests_total")
        
        try:
            # MODIFICATION: Détection langue optimisée
            if not language:
                language = detect_language_enhanced(query, default="fr")
            
            # Intent processing avec métriques
            intent_result = None
            if self.intent_processor:
                try:
                    intent_result = self.intent_processor.process_query(query)
                    if intent_result:
                        METRICS.intent_detected(
                            intent_result.intent_type, 
                            getattr(intent_result, 'confidence', 0.8)
                        )
                        self.optimization_stats["intent_coverage_stats"][intent_result.intent_type] += 1
                except Exception as e:
                    logger.warning(f"Erreur intent processor: {e}")
            
            # MODIFICATION: OOD detection avec seuil dynamique
            if self.ood_detector:
                is_in_domain, domain_score, score_details = self.ood_detector.calculate_ood_score(query, intent_result)
                
                # Tracer ajustements de seuil
                if score_details.get("genetic_metric_present") or score_details.get("generic_vocab_only"):
                    self.optimization_stats["dynamic_ood_threshold_adjustments"] += 1
                
                if not is_in_domain:
                    METRICS.inc("requests_ood")
                    METRICS.observe_latency(time.time() - start_time)
                    return RAGResult(
                        source=RAGSource.OOD_FILTERED,
                        answer="Désolé, cette question sort du domaine avicole. Pose-moi une question sur l'aviculture.",
                        confidence=1.0 - domain_score,
                        processing_time=time.time() - start_time,
                        metadata={
                            "domain_score": domain_score,
                            "score_details": score_details,
                            "optimization_stats": self.optimization_stats.copy()
                        },
                        intent_result=intent_result
                    )
            
            # MODIFICATION: Contexte conversationnel enrichi
            conversation_context = ""
            if tenant_id and self.memory:
                try:
                    conversation_context = await self.memory.get_contextual_memory(tenant_id, query)
                    if conversation_context:
                        self.optimization_stats["conversation_context_usage"] += 1
                except Exception as e:
                    logger.warning(f"Erreur mémoire conversationnelle: {e}")
            
            # Embedding de la requête
            search_query = query
            if intent_result and hasattr(intent_result, 'expanded_query') and intent_result.expanded_query:
                search_query = intent_result.expanded_query
            
            query_vector = await self.embedder.embed_query(search_query)
            if not query_vector:
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.ERROR,
                    metadata={"error": "embedding_failed", "optimization_stats": self.optimization_stats.copy()}
                )
            
            # Construire where filter
            where_filter = build_where_filter(intent_result)
            
            # MODIFICATION: Recherche hybride paramétrable avec instrumentation
            documents = []
            if self.retriever:
                try:
                    # Utiliser alpha paramétrable pour hybrid search
                    search_alpha = getattr(intent_result, 'preferred_alpha', DEFAULT_ALPHA) if intent_result else DEFAULT_ALPHA
                    
                    documents = await self.retriever.adaptive_search(
                        query_vector, search_query, RAG_SIMILARITY_TOP_K, where_filter, alpha=search_alpha
                    )
                    if any(doc.metadata.get("hybrid_used") for doc in documents):
                        self.optimization_stats["hybrid_searches"] += 1
                    
                    # Compter corrections API
                    runtime_corrections = sum(doc.metadata.get("runtime_corrections", 0) for doc in documents)
                    if runtime_corrections > 0:
                        self.optimization_stats["api_corrections"] += runtime_corrections
                    
                    # Compter explain_score extraits
                    explain_scores_found = sum(1 for doc in documents if doc.explain_score is not None)
                    if explain_scores_found > 0:
                        self.optimization_stats["explain_score_extractions"] += explain_scores_found
                        
                except Exception as e:
                    logger.error(f"Erreur recherche hybride: {e}")
            
            if not documents:
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={
                        "reason": "no_documents_found", 
                        "where_filter_used": where_filter is not None,
                        "optimization_stats": self.optimization_stats.copy()
                    }
                )
            
            # Filtrage par confiance avec seuil dynamique
            effective_threshold = RAG_CONFIDENCE_THRESHOLD
            if documents:
                top1 = max(d.score for d in documents)
                if top1 >= 0.85:
                    effective_threshold = max(RAG_CONFIDENCE_THRESHOLD, 0.60)
                elif any(d.metadata.get("bm25_used") for d in documents) and top1 < 0.70:
                    effective_threshold = min(effective_threshold, 0.50)
            
            filtered_docs = [doc for doc in documents if doc.score >= effective_threshold]
            
            if not filtered_docs:
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={
                        "reason": "low_confidence_documents", 
                        "min_score": min(doc.score for doc in documents) if documents else 0,
                        "effective_threshold": effective_threshold,
                        "optimization_stats": self.optimization_stats.copy()
                    }
                )
            
            # Génération de réponse enrichie avec cache sémantique
            response_text = ""
            cache_semantic_details = {}
            if self.generator and ENTITY_ENRICHMENT_ENABLED:
                try:
                    response_text = await self.generator.generate_response(
                        query, filtered_docs, conversation_context, language, intent_result
                    )
                    self.optimization_stats["entity_enrichments"] += 1
                    
                    # Récupérer détails cache sémantique
                    if (self.cache_manager and hasattr(self.cache_manager, 'get_last_semantic_details')):
                        try:
                            cache_semantic_details = await self.cache_manager.get_last_semantic_details()
                        except Exception as e:
                            logger.debug(f"Impossible de récupérer détails cache sémantique: {e}")
                            self.optimization_stats["cache_semantic_reasoning_failures"] += 1
                    
                except Exception as e:
                    logger.error(f"Erreur génération enrichie: {e}")
            
            # Fallback génération basique
            if not response_text:
                try:
                    context_text = "\n\n".join([
                        f"Document {i+1}:\n{doc.content[:1000]}"
                        for i, doc in enumerate(filtered_docs[:5])
                    ])
                    
                    system_prompt = f"""Tu es un expert en aviculture. Réponds UNIQUEMENT basé sur les documents fournis.
RÈGLE: Réponds strictement en {language}."""
                    
                    user_prompt = f"""DOCUMENTS:\n{context_text}\n\nQUESTION:\n{query}\n\nRÉPONSE:"""
                    
                    response = await self.openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=800
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                except Exception as e:
                    logger.error(f"Erreur génération fallback: {e}")
                    response_text = "Désolé, je ne peux pas générer une réponse."
            
            if not response_text or "ne peux pas" in response_text.lower():
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={
                        "reason": "generation_failed",
                        "optimization_stats": self.optimization_stats.copy()
                    }
                )
            
            # MODIFICATION: Vérification avec guardrails uniques + explain_score
            verification_result = None
            if self.guardrails:
                try:
                    # Vérification smart: skip si haute confiance
                    do_verify = True
                    if RAG_VERIFICATION_SMART:
                        top_scores = [d.score for d in filtered_docs[:3]]
                        if top_scores and top_scores[0] >= 0.80 and (len(top_scores) <= 1 or np.std(top_scores) <= 0.05):
                            do_verify = False
                    
                    if do_verify:
                        # MODIFICATION: Enrichir les métadonnées avec explain_score
                        docs_with_explain = []
                        for doc in filtered_docs:
                            doc_dict = doc.__dict__.copy()
                            if doc.explain_score:
                                doc_dict["explain_score"] = doc.explain_score
                            docs_with_explain.append(doc_dict)
                        
                        verification_result = await self.guardrails.verify_response(
                            query, response_text, docs_with_explain, intent_result
                        )
                        
                        if not verification_result.is_valid:
                            self.optimization_stats["guardrail_violations"] += 1
                            logger.warning(f"Violation guardrails: {verification_result.violations}")
                            
                            if verification_result.confidence < 0.3:
                                METRICS.observe_latency(time.time() - start_time)
                                return RAGResult(
                                    source=RAGSource.FALLBACK_NEEDED,
                                    metadata={
                                        "reason": "guardrail_violation",
                                        "violations": verification_result.violations,
                                        "optimization_stats": self.optimization_stats.copy()
                                    }
                                )
                    
                except Exception as e:
                    logger.warning(f"Erreur guardrails: {e}")
            
            # Calcul de confiance finale
            confidence = self._calculate_confidence(filtered_docs, verification_result)
            
            # Source du résultat
            result_source = RAGSource.RAG_KNOWLEDGE
            if verification_result and verification_result.is_valid:
                result_source = RAGSource.RAG_VERIFIED
                confidence = min(confidence * 1.1, 0.95)
            
            # Construire context_docs pour le résultat
            context_docs = []
            for doc in filtered_docs:
                doc_dict = {
                    "title": doc.metadata.get("title", ""),
                    "content": doc.content,
                    "score": doc.score,
                    "source": doc.metadata.get("source", ""),
                    "genetic_line": doc.metadata.get("geneticLine", ""),
                    "species": doc.metadata.get("species", ""),
                    "phase": doc.metadata.get("phase", ""),
                    "age_band": doc.metadata.get("age_band", ""),
                    "hybrid_used": doc.metadata.get("hybrid_used", False),
                    "bm25_used": doc.metadata.get("bm25_used", False),
                    "vector_format_used": doc.metadata.get("vector_format_used", ""),
                    "fallback_search": doc.metadata.get("fallback_search", False),
                    "minimal_api_used": doc.metadata.get("minimal_api_used", False),
                    "runtime_corrections": doc.metadata.get("runtime_corrections", 0),
                    "search_type": getattr(doc, 'search_type', 'unknown'),
                    "hybrid_alpha_used": getattr(doc, 'hybrid_alpha_used', DEFAULT_ALPHA)
                }
                
                if doc.explain_score is not None:
                    doc_dict["explain_score"] = doc.explain_score
                
                context_docs.append(doc_dict)
            
            # MODIFICATION: Métadonnées complètes avec nouvelles infos
            dependencies_status = get_dependencies_status()
            metadata = {
                "approach": "enhanced_rag_external_cache_optimized_v4_16_9_corrected_unified",
                "optimizations_enabled": {
                    "external_redis_cache": self.optimization_stats["external_cache_used"],
                    "semantic_cache": getattr(self.cache_manager, 'ENABLE_SEMANTIC_CACHE', False),
                    "hybrid_search": HYBRID_SEARCH_ENABLED,
                    "hybrid_search_parameterized": True,
                    "entity_enrichment": ENTITY_ENRICHMENT_ENABLED,
                    "advanced_guardrails": GUARDRAILS_AVAILABLE,
                    "guardrails_unified": True,
                    "api_diagnostics": ENABLE_API_DIAGNOSTICS,
                    "dynamic_ood_thresholds": True,
                    "enhanced_conversation_memory": True,
                    "explain_score_extraction": self.optimization_stats["explain_score_extractions"] > 0,
                    "openai_simplified_init": True
                },
                "weaviate_version": dependencies_status.get("weaviate_version", "N/A"),
                "weaviate_v4": WEAVIATE_V4,
                "documents_found": len(documents) if documents else 0,
                "documents_used": len(filtered_docs),
                "effective_threshold": effective_threshold,
                "query_expanded": search_query != query,
                "conversation_context_used": bool(conversation_context),
                "where_filter_applied": where_filter is not None,
                "verification_enabled": RAG_VERIFICATION_ENABLED,
                "verification_smart": RAG_VERIFICATION_SMART,
                "language_target": language,
                "language_detected": detect_language_enhanced(query),
                "hybrid_alpha_used": search_alpha if 'search_alpha' in locals() else DEFAULT_ALPHA,
                "optimization_stats": self.optimization_stats.copy(),
                "api_capabilities": self.retriever.api_capabilities if self.retriever else {},
                "api_corrections_applied": self.optimization_stats.get("api_corrections", 0) > 0,
                "cache_semantic_details": cache_semantic_details
            }
            
            if cache_semantic_details.get("semantic_keywords_used"):
                metadata["semantic_keywords_used"] = cache_semantic_details["semantic_keywords_used"]
            
            if intent_result:
                metadata.update({
                    "intent_type": getattr(intent_result, 'intent_type', 'unknown'),
                    "detected_entities": getattr(intent_result, 'detected_entities', {}),
                    "confidence_breakdown": getattr(intent_result, 'confidence_breakdown', {}),
                    "preferred_alpha": getattr(intent_result, 'preferred_alpha', None)
                })
            
            # Sauvegarde mémoire
            if tenant_id and self.memory:
                try:
                    self.memory.add_exchange(tenant_id, query, response_text)
                except Exception as e:
                    logger.warning(f"Erreur sauvegarde mémoire: {e}")
            
            METRICS.observe_latency(time.time() - start_time)
            
            return RAGResult(
                source=result_source,
                answer=response_text,
                confidence=confidence,
                context_docs=context_docs,
                processing_time=time.time() - start_time,
                metadata=metadata,
                verification_status=verification_result.__dict__ if verification_result else None,
                intent_result=intent_result
            )
            
        except Exception as e:
            logger.error(f"Erreur traitement query: {e}")
            METRICS.observe_latency(time.time() - start_time)
            return RAGResult(
                source=RAGSource.ERROR,
                confidence=0.0,
                processing_time=time.time() - start_time,
                metadata={
                    "error": str(e),
                    "optimization_stats": self.optimization_stats.copy()
                },
                intent_result=intent_result if 'intent_result' in locals() else None
            )
    
    def _calculate_confidence(self, documents: List[Document], verification_result=None) -> float:
        """Calcul de confiance optimisé"""
        if not documents:
            return 0.0
        
        scores = [doc.score for doc in documents if doc.score > 0]
        if not scores:
            return 0.5
        
        avg_score = sum(scores) / len(scores)
        coherence_factor = min(1.2, 1 + (len(scores) - 1) * 0.05)
        
        if len(scores) > 1:
            score_std = np.std(scores)
            distribution_factor = max(0.9, 1 - score_std * 0.5)
        else:
            distribution_factor = 1.0
        
        verification_factor = 1.0
        if verification_result and verification_result.is_valid:
            verification_factor = 1.1
        
        final_confidence = avg_score * coherence_factor * distribution_factor * verification_factor
        return min(0.95, max(0.1, final_confidence))
    
    def get_status(self) -> Dict:
        """MODIFICATION: Status riche avec toutes les nouvelles métriques"""
        try:
            weaviate_connected = False
            api_capabilities = {}
            
            if self.weaviate_client:
                try:
                    def _check():
                        return self.weaviate_client.is_ready()
                    weaviate_connected = _check()
                except:
                    weaviate_connected = False
            
            if self.retriever and hasattr(self.retriever, 'api_capabilities'):
                api_capabilities = self.retriever.api_capabilities
            
            dependencies_status = get_dependencies_status()
            
            status = {
                "rag_enabled": RAG_ENABLED,
                "initialized": self.is_initialized,
                "degraded_mode": self.degraded_mode,
                "approach": "enhanced_rag_external_cache_optimized_v4_16_9_corrected_unified",
                "optimizations": {
                    "external_cache_enabled": self.cache_manager.enabled if self.cache_manager else False,
                    "hybrid_search_enabled": HYBRID_SEARCH_ENABLED,
                    "hybrid_search_parameterized": True,
                    "semantic_cache_enabled": getattr(self.cache_manager, 'ENABLE_SEMANTIC_CACHE', False),
                    "entity_enrichment_enabled": ENTITY_ENRICHMENT_ENABLED,
                    "guardrails_level": GUARDRAILS_LEVEL,
                    "guardrails_unified": True,
                    "verification_smart": RAG_VERIFICATION_SMART,
                    "api_diagnostics_enabled": ENABLE_API_DIAGNOSTICS,
                    "dynamic_ood_thresholds": True,
                    "enhanced_conversation_memory": True,
                    "explain_score_extraction_enabled": api_capabilities.get("explain_score_available", False),
                    "openai_simplified_init": True
                },
                "components": dependencies_status,
                "components_extended": {
                    "weaviate_connected": weaviate_connected,
                },
                "configuration": {
                    "similarity_top_k": RAG_SIMILARITY_TOP_K,
                    "confidence_threshold": RAG_CONFIDENCE_THRESHOLD,
                    "rerank_top_k": RAG_RERANK_TOP_K,
                    "max_conversation_context": MAX_CONVERSATION_CONTEXT,
                    "ood_min_score": OOD_MIN_SCORE,
                    "ood_strict_score": OOD_STRICT_SCORE,
                    "lang_detection_min_length": LANG_DETECTION_MIN_LENGTH,
                    "redis_url": REDIS_URL,
                    "weaviate_url": WEAVIATE_URL,
                    "hybrid_default_alpha": DEFAULT_ALPHA
                },
                "optimization_stats": self.optimization_stats.copy(),
                "weaviate_capabilities": api_capabilities,
                "intent_coverage_stats": dict(self.optimization_stats["intent_coverage_stats"]),
                "metrics": METRICS.snapshot()
            }
            
            # Stats cache externe
            if self.cache_manager and self.cache_manager.enabled:
                status["cache_stats"] = {
                    "enabled": True,
                    "external_cache_used": True,
                    "semantic_cache_enabled": getattr(self.cache_manager, 'ENABLE_SEMANTIC_CACHE', False),
                    "note": "Stats détaillées disponibles via cache externe"
                }
            else:
                status["cache_stats"] = {"enabled": False, "external_cache_used": False}
            
            return status
            
        except Exception as e:
            logger.error(f"Erreur get_status: {e}")
            return {
                "error": str(e),
                "rag_enabled": RAG_ENABLED,
                "initialized": False,
                "degraded_mode": True
            }
    
    async def cleanup(self):
        """Nettoyage complet des ressources"""
        try:
            if self.cache_manager:
                await self.cache_manager.cleanup()
            
            if self.weaviate_client and hasattr(self.weaviate_client, 'close'):
                self.weaviate_client.close()
            
            if self.memory:
                self.memory.memory_store.clear()
            
            if hasattr(self.openai_client, 'http_client'):
                await self.openai_client.http_client.aclose()
            
            logger.info("Enhanced RAG Engine avec cache externe nettoyé")
            
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")


# === FONCTIONS UTILITAIRES POUR COMPATIBILITÉ ===
async def create_rag_engine(openai_client: AsyncOpenAI = None) -> InteliaRAGEngine:
    """MODIFICATION: Factory avec initialisation Redis asynchrone garantie"""
    try:
        engine = InteliaRAGEngine(openai_client)
        # CRITICAL: S'assurer que l'initialisation complète est awaited
        await engine.initialize()
        
        # Vérifier que le cache est bien initialisé
        if engine.cache_manager and not engine.cache_manager.enabled:
            logger.warning("⚠️ Cache manager créé mais pas enabled - vérifier configuration Redis")
        
        return engine
    except Exception as e:
        logger.error(f"Erreur création RAG engine: {e}")
        engine = InteliaRAGEngine(openai_client)
        engine.degraded_mode = True
        engine.is_initialized = True
        return engine

async def process_question_with_rag(
    rag_engine: InteliaRAGEngine, 
    question: str, 
    language: str = "fr", 
    tenant_id: str = ""
) -> RAGResult:
    """Interface compatible pour traitement des questions"""
    try:
        return await rag_engine.process_query(question, language, tenant_id)
    except Exception as e:
        logger.error(f"Erreur process_question_with_rag: {e}")
        return RAGResult(
            source=RAGSource.ERROR,
            confidence=0.0,
            metadata={"error": str(e)}
        )