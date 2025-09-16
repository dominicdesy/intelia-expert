# -*- coding: utf-8 -*-
"""

rag_engine.py - RAG Engine Enhanced avec LangSmith et RRF Intelligent
Version avec intégration LangSmith pour monitoring LLM aviculture

"""

import os
import asyncio
import logging
import time
import numpy as np
import httpx
from typing import Dict, List, Optional, Any
from collections import defaultdict

# CORRECTION CRITIQUE: Définir logger AVANT toute utilisation
logger = logging.getLogger(__name__)

# CORRECTION: Imports avec gestion d'erreurs détaillée
try:
    from config import *
    logger.debug("Config importé avec succès")
except Exception as e:
    logger.error(f"Erreur import config: {e}")
    raise

try:
    from imports_and_dependencies import *
    logger.debug("Imports_and_dependencies importé avec succès")
except Exception as e:
    logger.error(f"Erreur import imports_and_dependencies: {e}")
    raise

try:
    from data_models import RAGResult, RAGSource, Document
    logger.debug("Data_models importé avec succès")
except Exception as e:
    logger.error(f"Erreur import data_models: {e}")
    raise

try:
    from utilities import METRICS, detect_language_enhanced, build_where_filter
    logger.debug("Utilities importé avec succès")
except Exception as e:
    logger.error(f"Erreur import utilities: {e}")
    raise

try:
    from embedder import OpenAIEmbedder
    logger.debug("Embedder importé avec succès")
except Exception as e:
    logger.error(f"Erreur import embedder: {e}")
    raise

try:
    from retriever import HybridWeaviateRetriever
    logger.debug("Retriever importé avec succès")
except Exception as e:
    logger.error(f"Erreur import retriever: {e}")
    raise

try:
    from generators import EnhancedResponseGenerator
    logger.debug("Generators importé avec succès")
except Exception as e:
    logger.error(f"Erreur import generators: {e}")
    raise

try:
    from ood_detector import EnhancedOODDetector
    logger.debug("OOD_detector importé avec succès")
except Exception as e:
    logger.error(f"Erreur import ood_detector: {e}")
    raise

try:
    from memory import ConversationMemory
    logger.debug("Memory importé avec succès")
except Exception as e:
    logger.error(f"Erreur import memory: {e}")
    raise

try:
    from advanced_guardrails import AdvancedResponseGuardrails
    logger.debug("Advanced_guardrails importé avec succès")
except Exception as e:
    logger.error(f"Erreur import advanced_guardrails: {e}")
    raise

try:
    from hybrid_retriever import hybrid_search
    logger.debug("Hybrid_retriever importé avec succès")
except Exception as e:
    logger.error(f"Erreur import hybrid_retriever: {e}")
    raise

# CORRECTION: Import explicite d'AsyncOpenAI
try:
    from imports_and_dependencies import AsyncOpenAI
    logger.debug("AsyncOpenAI importé avec succès")
except Exception as e:
    logger.error(f"Erreur import AsyncOpenAI: {e}")
    raise

# === NOUVEAU: IMPORTS LANGSMITH ===
if LANGSMITH_ENABLED:
    try:
        from langsmith import Client
        from langsmith.run_helpers import traceable
        LANGSMITH_AVAILABLE = True
        logger.info("LangSmith importé avec succès")
    except ImportError as e:
        LANGSMITH_AVAILABLE = False
        logger.warning(f"LangSmith non disponible: {e}")
else:
    LANGSMITH_AVAILABLE = False

# === NOUVEAU: IMPORT RRF INTELLIGENT ===
try:
    from enhanced_rrf_fusion import IntelligentRRFFusion
    INTELLIGENT_RRF_AVAILABLE = True
    logger.info("RRF Intelligent importé avec succès")
except ImportError as e:
    INTELLIGENT_RRF_AVAILABLE = False
    logger.warning(f"RRF Intelligent non disponible: {e}")

DEFAULT_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.6"))


class InteliaRAGEngine:
    """RAG Engine principal avec LangSmith et RRF Intelligent"""
    
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
        
        # === NOUVEAU: LANGSMITH CLIENT ===
        self.langsmith_client = None
        if LANGSMITH_AVAILABLE and LANGSMITH_ENABLED and LANGSMITH_API_KEY:
            try:
                self.langsmith_client = Client(
                    api_key=LANGSMITH_API_KEY,
                    api_url="https://api.smith.langchain.com"
                )
                logger.info(f"LangSmith initialisé - Projet: {LANGSMITH_PROJECT}")
            except Exception as e:
                logger.error(f"Erreur initialisation LangSmith: {e}")
                self.langsmith_client = None
        
        # === NOUVEAU: RRF INTELLIGENT ===
        self.intelligent_rrf = None
        
        # État
        self.is_initialized = False
        self.degraded_mode = False
        
        # Stats étendues avec LangSmith et RRF
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
            # NOUVEAU: Stats LangSmith
            "langsmith_traces": 0,
            "langsmith_errors": 0,
            "prompt_optimizations": 0,
            # NOUVEAU: Stats RRF Intelligent
            "intelligent_rrf_used": 0,
            "genetic_boosts_applied": 0,
            "rrf_learning_updates": 0,
            "semantic_reasoning_failures": 0,
            "intent_coverage_stats": defaultdict(int),
            "weaviate_capabilities": {},
            "dynamic_ood_threshold_adjustments": 0,
            "conversation_context_usage": 0
        }
    
    def _build_openai_client(self) -> AsyncOpenAI:
        """Construit le client OpenAI"""
        try:
            http_client = httpx.AsyncClient(timeout=30.0)
            return AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
        except Exception as e:
            logger.warning(f"Erreur client OpenAI: {e}")
            return AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def initialize(self):
        """Initialisation avec LangSmith et RRF Intelligent"""
        if self.is_initialized:
            return
            
        logger.info("Initialisation RAG Engine Enhanced avec LangSmith + RRF Intelligent")
        
        if not OPENAI_AVAILABLE or not WEAVIATE_AVAILABLE:
            self.degraded_mode = True
            logger.warning("Mode dégradé activé")
            self.is_initialized = True
            return
        
        try:
            logger.debug("Étape 1: Initialisation Cache Redis externe...")
            
            # 1. Cache Redis externe avec protection renforcée
            if CACHE_ENABLED and EXTERNAL_CACHE_AVAILABLE:
                try:
                    from redis_cache_manager import RAGCacheManager
                    # CORRECTION: Utiliser la factory function au lieu du constructeur direct
                    self.cache_manager = RAGCacheManager()
                    await self.cache_manager.initialize()
                    if self.cache_manager.enabled:
                        self.optimization_stats["external_cache_used"] = True
                        logger.info("Cache Redis externe activé")
                except ImportError as e:
                    logger.warning(f"RAGCacheManager non disponible: {e}")
                    self.cache_manager = None
                except Exception as e:
                    logger.warning(f"Cache Redis externe échoué: {e}")
                    self.cache_manager = None
            
            logger.debug("Étape 2: Connexion Weaviate...")
            
            # 2. Connexion Weaviate CORRIGÉE
            try:
                await self._connect_weaviate()
            except Exception as e:
                logger.warning(f"Connexion Weaviate échouée: {e}")
            
            logger.debug("Étape 3: Composants de base...")
            
            # 3. Composants de base
            try:
                self.embedder = OpenAIEmbedder(self.openai_client, self.cache_manager)
                self.memory = ConversationMemory(self.openai_client)
                self.ood_detector = EnhancedOODDetector()
                logger.debug("Composants de base initialisés")
            except Exception as e:
                logger.error(f"Erreur composants de base: {e}")
                raise
            
            logger.debug("Étape 4: Retriever hybride...")
            
            # 4. Retriever hybride avec RRF intelligent
            if self.weaviate_client:
                try:
                    self.retriever = HybridWeaviateRetriever(self.weaviate_client)
                    
                    # === NOUVEAU: Initialisation RRF Intelligent ===
                    if (INTELLIGENT_RRF_AVAILABLE and ENABLE_INTELLIGENT_RRF and 
                        self.cache_manager and self.cache_manager.enabled):
                        try:
                            self.intelligent_rrf = IntelligentRRFFusion(
                                redis_client=self.cache_manager.client,
                                intent_processor=None  # Sera défini plus tard
                            )
                            logger.info("RRF Intelligent initialisé")
                        except Exception as e:
                            logger.error(f"Erreur RRF Intelligent: {e}")
                    
                    # Diagnostic API Weaviate
                    if ENABLE_API_DIAGNOSTICS:
                        try:
                            await self.retriever.diagnose_weaviate_api()
                            self.optimization_stats["weaviate_capabilities"] = self.retriever.api_capabilities.copy()
                        except Exception as e:
                            logger.warning(f"Diagnostic Weaviate échoué: {e}")
                            
                except Exception as e:
                    logger.warning(f"Retriever hybride échoué: {e}")
            
            logger.debug("Étape 5: Générateur de réponses...")
            
            # 5. Générateur de réponses
            try:
                self.generator = EnhancedResponseGenerator(self.openai_client, self.cache_manager)
            except Exception as e:
                logger.error(f"Erreur générateur: {e}")
                raise
            
            logger.debug("Étape 6: Intent processor...")
            
            # 6. Intent processor avec gestion d'erreurs améliorée
            try:
                from intent_processor import create_intent_processor
                self.intent_processor = create_intent_processor()
                
                # Connecter RRF Intelligent à Intent Processor
                if self.intelligent_rrf:
                    self.intelligent_rrf.intent_processor = self.intent_processor
                
                logger.info("Intent processor initialisé avec succès")
                    
            except Exception as e:
                logger.warning(f"Intent processor non disponible: {e}")
                # Continuer sans intent processor
                self.intent_processor = None
            
            logger.debug("Étape 7: Guardrails...")
            
            # 7. Guardrails
            if GUARDRAILS_AVAILABLE:
                try:
                    from advanced_guardrails import create_response_guardrails
                    self.guardrails = create_response_guardrails(self.openai_client, GUARDRAILS_LEVEL)
                except Exception as e:
                    logger.warning(f"Guardrails échoué: {e}")
            
            self.is_initialized = True
            logger.info("RAG Engine Enhanced initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur initialisation RAG Engine: {e}")
            logger.error(f"Type d'erreur: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.degraded_mode = True
            self.is_initialized = True
    
    # === CORRECTION: CONNEXION WEAVIATE POUR CLOUD ===
    

    async def _connect_weaviate(self):
        """Connexion Weaviate corrigée avec authentification et configuration OpenAI"""
        try:
            import weaviate
            
            # Variables d'environnement Weaviate
            weaviate_url = os.getenv("WEAVIATE_URL", "https://xmlc4jvtu6hfw9zrrmnw.c0.us-east1.gcp.weaviate.cloud")
            weaviate_api_key = os.getenv("WEAVIATE_API_KEY", "")
            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            
            logger.info(f"Tentative de connexion Weaviate: {weaviate_url}")
            logger.debug(f"Weaviate API Key configurée: {'Oui' if weaviate_api_key else 'Non'}")
            logger.debug(f"OpenAI API Key configurée: {'Oui' if openai_api_key else 'Non'}")
            
            # CORRECTION CRITIQUE: Définir OPENAI_APIKEY pour Weaviate si pas déjà définie
            if openai_api_key and 'OPENAI_APIKEY' not in os.environ:
                os.environ['OPENAI_APIKEY'] = openai_api_key
                logger.debug("Variable OPENAI_APIKEY définie pour compatibilité Weaviate")
            
            # Pour une URL cloud Weaviate, utiliser connect_to_weaviate_cloud avec authentification
            if "weaviate.cloud" in weaviate_url:
                logger.debug("Utilisation connexion cloud Weaviate avec authentification")
                
                if weaviate_api_key:
                    try:
                        # NOUVEAU: Client v4 avec API Key et headers OpenAI
                        import weaviate.classes as wvc
                        
                        # Headers personnalisés pour OpenAI
                        headers = {}
                        if openai_api_key:
                            headers['X-OpenAI-Api-Key'] = openai_api_key
                        
                        self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                            cluster_url=weaviate_url,
                            auth_credentials=wvc.init.Auth.api_key(weaviate_api_key),
                            headers=headers
                        )
                        logger.info("Connexion Weaviate v4 avec API Key réussie")
                        
                    except ImportError:
                        logger.warning("Weaviate v4 non disponible, utilisation v3")
                        # Fallback vers client v3 avec authentification
                        self.weaviate_client = weaviate.Client(
                            url=weaviate_url,
                            auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key),
                            additional_headers={'X-OpenAI-Api-Key': openai_api_key} if openai_api_key else {}
                        )
                        logger.info("Connexion Weaviate v3 avec API Key réussie")
                        
                    except Exception as auth_error:
                        logger.error(f"Erreur authentification Weaviate: {auth_error}")
                        # Tentative fallback v3
                        try:
                            self.weaviate_client = weaviate.Client(
                                url=weaviate_url,
                                auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key),
                                additional_headers={'X-OpenAI-Api-Key': openai_api_key} if openai_api_key else {}
                            )
                            logger.info("Fallback Weaviate v3 avec API Key réussi")
                        except Exception as fallback_error:
                            logger.error(f"Fallback v3 également échoué: {fallback_error}")
                            self.weaviate_client = None
                            return
                else:
                    logger.error("WEAVIATE_API_KEY non configurée pour l'instance cloud")
                    self.weaviate_client = None
                    return
            else:
                # Connexion locale sans authentification
                host = weaviate_url.replace("http://", "").replace("https://", "")
                self.weaviate_client = weaviate.connect_to_local(host=host)
                logger.info("Connexion Weaviate locale configurée")
            
            # Test de connexion avec timeout
            if self.weaviate_client:
                try:
                    # Test asynchrone de la connexion
                    ready = await asyncio.wait_for(
                        asyncio.to_thread(lambda: self.weaviate_client.is_ready()),
                        timeout=15.0
                    )
                    
                    if ready:
                        logger.info(f"Connexion Weaviate opérationnelle: {weaviate_url}")
                        
                        # CORRECTION: Test de capacités v4 compatible
                        try:
                            # Pour client v4, utiliser .collections au lieu de .schema
                            if hasattr(self.weaviate_client, 'collections'):
                                await asyncio.to_thread(lambda: list(self.weaviate_client.collections.list_all()))
                                logger.info("Permissions Weaviate vérifiées - accès collections OK")
                            else:
                                # Fallback pour client v3
                                await asyncio.to_thread(lambda: self.weaviate_client.schema.get())
                                logger.info("Permissions Weaviate vérifiées - accès schéma OK")
                                
                        except Exception as perm_error:
                            logger.warning(f"Permissions limitées Weaviate: {perm_error}")
                            # Continue quand même, certaines opérations peuvent fonctionner
                            
                    else:
                        logger.error("Weaviate connecté mais pas prêt")
                        self.weaviate_client = None
                        
                except asyncio.TimeoutError:
                    logger.error("Timeout lors du test de connexion Weaviate (15s)")
                    self.weaviate_client = None
                except Exception as test_error:
                    logger.error(f"Erreur test connexion Weaviate: {test_error}")
                    self.weaviate_client = None
                
        except Exception as e:
            logger.error(f"Erreur générale connexion Weaviate: {e}")
            self.weaviate_client = None

    
    # === MÉTHODES PRINCIPALES AVEC LANGSMITH ===
    
    async def generate_response(self, query: str, tenant_id: str = "default", 
                              conversation_context: List[Dict] = None,
                              language: Optional[str] = None,
                              explain_score: Optional[float] = None) -> RAGResult:
        """
        Point d'entrée principal avec tracing LangSmith automatique
        """
        
        if LANGSMITH_AVAILABLE and self.langsmith_client and LANGSMITH_ENABLED:
            return await self._generate_response_with_langsmith(
                query, tenant_id, conversation_context, language, explain_score
            )
        else:
            return await self._generate_response_core(
                query, tenant_id, conversation_context, language, explain_score
            )
    
    async def _generate_response_with_langsmith(self, query: str, tenant_id: str,
                                              conversation_context: List[Dict],
                                              language: Optional[str],
                                              explain_score: Optional[float]) -> RAGResult:
        """Génération de réponse avec tracing LangSmith complet"""
        
        start_time = time.time()
        self.optimization_stats["langsmith_traces"] += 1
        
        try:
            # Traçage contexte aviculture
            langsmith_metadata = {
                "tenant_id": tenant_id,
                "query_length": len(query),
                "has_conversation_context": bool(conversation_context),
                "language_target": language,
                "system": "intelia_aviculture_rag",
                "version": "enhanced_with_langsmith"
            }
            
            # Traitement core
            result = await self._generate_response_core(
                query, tenant_id, conversation_context, language, explain_score
            )
            
            # Enrichissement métadonnées LangSmith avec données aviculture
            if hasattr(result, 'metadata') and result.metadata:
                detected_entities = result.metadata.get('detected_entities', {})
                
                langsmith_metadata.update({
                    "genetic_line": detected_entities.get('line', 'none'),
                    "age_days": detected_entities.get('age_days'),
                    "performance_metric": any(metric in query.lower() 
                                            for metric in ['fcr', 'poids', 'mortalité', 'ponte']),
                    "intent_type": result.metadata.get('intent_type', 'unknown'),
                    "intent_confidence": result.metadata.get('intent_confidence', 0.0),
                    "documents_used": result.metadata.get('documents_used', 0),
                    "hybrid_search_used": result.metadata.get('hybrid_search_used', False),
                    "intelligent_rrf_used": result.metadata.get('intelligent_rrf_used', False),
                    "processing_time": time.time() - start_time,
                    "confidence_score": result.confidence
                })
            
            # Log métadonnées dans LangSmith
            if self.langsmith_client:
                try:
                    # Log spécialisé pour alertes
                    await self._log_langsmith_alerts(query, result, langsmith_metadata)
                    
                except Exception as e:
                    logger.warning(f"Erreur logging LangSmith: {e}")
                    self.optimization_stats["langsmith_errors"] += 1
            
            return result
            
        except Exception as e:
            self.optimization_stats["langsmith_errors"] += 1
            logger.error(f"Erreur LangSmith tracing: {e}")
            # Fallback sans LangSmith
            return await self._generate_response_core(
                query, tenant_id, conversation_context, language, explain_score
            )
    
    async def _log_langsmith_alerts(self, query: str, result: RAGResult, metadata: Dict):
        """Log des alertes spécialisées aviculture dans LangSmith"""
        
        alerts = []
        
        if not result.answer:
            return
            
        # Détection valeurs aberrantes aviculture
        answer_lower = result.answer.lower()
        
        # FCR aberrant
        import re
        fcr_matches = re.findall(r'fcr[:\s]*(\d+[.,]\d*)', answer_lower)
        for fcr_str in fcr_matches:
            try:
                fcr_value = float(fcr_str.replace(',', '.'))
                if fcr_value > 3.0 or fcr_value < 0.8:
                    alerts.append(f"FCR_ABERRANT: {fcr_value}")
            except ValueError:
                continue
        
        # Mortalité aberrante  
        mort_matches = re.findall(r'mortalité[:\s]*(\d+)[%\s]', answer_lower)
        for mort_str in mort_matches:
            try:
                mort_value = float(mort_str)
                if mort_value > 20:
                    alerts.append(f"MORTALITE_ELEVEE: {mort_value}%")
            except ValueError:
                continue
        
        # Poids aberrant
        poids_matches = re.findall(r'poids[:\s]*(\d+)\s*g', answer_lower)
        for poids_str in poids_matches:
            try:
                poids_value = float(poids_str)
                if poids_value > 5000 or poids_value < 10:
                    alerts.append(f"POIDS_ABERRANT: {poids_value}g")
            except ValueError:
                continue
        
        # Log alertes si détectées
        if alerts:
            logger.warning(f"Alertes aviculture détectées: {alerts}")
            metadata["alerts_aviculture"] = alerts
            
        # Confiance faible
        if result.confidence < 0.3:
            alerts.append(f"CONFIANCE_FAIBLE: {result.confidence:.2f}")
    
    async def _generate_response_core(self, query: str, tenant_id: str,
                                    conversation_context: List[Dict],
                                    language: Optional[str],
                                    explain_score: Optional[float]) -> RAGResult:
        """Méthode core de génération"""
        
        if self.degraded_mode:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "degraded_mode"})
        
        start_time = time.time()
        METRICS.inc("requests_total")
        
        try:
            # Détection langue
            if not language:
                language = detect_language_enhanced(query, default="fr")
            
            # Intent processing avec gestion d'erreurs robuste
            intent_result = None
            if self.intent_processor:
                try:
                    intent_result = self.intent_processor.process_query(query)
                    if intent_result:
                        METRICS.intent_detected(intent_result.intent_type, 
                                              getattr(intent_result, 'confidence', 0.8))
                        self.optimization_stats["intent_coverage_stats"][intent_result.intent_type] += 1
                except Exception as e:
                    logger.warning(f"Erreur intent processor: {e}")
                    intent_result = None
            
            # OOD detection avec seuil dynamique
            if self.ood_detector:
                try:
                    is_in_domain, domain_score, score_details = self.ood_detector.calculate_ood_score(query, intent_result)
                    
                    if score_details.get("genetic_metric_present") or score_details.get("generic_vocab_only"):
                        self.optimization_stats["dynamic_ood_threshold_adjustments"] += 1
                    
                    if not is_in_domain:
                        METRICS.inc("requests_ood")
                        METRICS.observe_latency(time.time() - start_time)
                        return RAGResult(
                            source=RAGSource.OOD_FILTERED,
                            answer="Désolé, cette question sort du domaine avicole. Pose-moi une question sur l'aviculture.",
                            confidence=0.0,
                            metadata={"ood_score": domain_score, "reason": "out_of_domain"}
                        )
                except Exception as e:
                    logger.warning(f"Erreur OOD detector: {e}")
            
            # Préparation contexte conversation
            conversation_context_str = ""
            if conversation_context and len(conversation_context) > 0:
                self.optimization_stats["conversation_context_usage"] += 1
                recent_context = conversation_context[-MAX_CONVERSATION_CONTEXT:]
                conversation_context_str = "\n".join([
                    f"Q: {ctx.get('question', '')}\nR: {ctx.get('answer', '')[:200]}..."
                    for ctx in recent_context
                ])
            
            # Génération embedding
            search_query = getattr(intent_result, 'expanded_query', query) if intent_result else query
            query_vector = await self.embedder.get_embedding(search_query)
            
            if not query_vector:
                return RAGResult(source=RAGSource.EMBEDDING_FAILED)
            
            # Construction filtres Weaviate
            where_filter = build_where_filter(intent_result)
            
            # Recherche de documents
            documents = []
            if self.retriever:
                try:
                    search_alpha = getattr(intent_result, 'preferred_alpha', DEFAULT_ALPHA) if intent_result else DEFAULT_ALPHA
                    
                    # Utilisation RRF intelligent si disponible
                    if (self.intelligent_rrf and hasattr(self.intelligent_rrf, 'enabled') and 
                        self.intelligent_rrf.enabled and ENABLE_INTELLIGENT_RRF):
                        
                        documents = await self._enhanced_hybrid_search_with_rrf(
                            query_vector, search_query, RAG_SIMILARITY_TOP_K, where_filter,
                            search_alpha, query, intent_result
                        )
                        self.optimization_stats["intelligent_rrf_used"] += 1
                        
                    else:
                        # Recherche hybride classique
                        documents = await self.retriever.adaptive_search(
                            query_vector, search_query, RAG_SIMILARITY_TOP_K, where_filter, alpha=search_alpha
                        )
                    
                    # Statistiques recherche
                    if any(doc.metadata.get("hybrid_used") for doc in documents):
                        self.optimization_stats["hybrid_searches"] += 1
                        
                except Exception as e:
                    logger.error(f"Erreur recherche hybride: {e}")
                    return RAGResult(source=RAGSource.SEARCH_FAILED, metadata={"error": str(e)})
            
            if not documents:
                return RAGResult(source=RAGSource.NO_DOCUMENTS_FOUND)
            
            # Filtrage par seuil de confiance
            effective_threshold = RAG_CONFIDENCE_THRESHOLD
            filtered_docs = [doc for doc in documents if doc.score >= effective_threshold]
            
            if not filtered_docs:
                return RAGResult(
                    source=RAGSource.LOW_CONFIDENCE,
                    metadata={"threshold": effective_threshold, "max_score": max([d.score for d in documents])}
                )
            
            # Génération de la réponse
            try:
                response_result = await self.generator.generate_response(
                    query, filtered_docs, intent_result, conversation_context_str, language
                )
                
                if not response_result or not response_result.answer:
                    return RAGResult(source=RAGSource.GENERATION_FAILED)
                
            except Exception as e:
                logger.error(f"Erreur génération réponse: {e}")
                return RAGResult(source=RAGSource.GENERATION_FAILED, metadata={"error": str(e)})
            
            # Calcul confiance finale
            final_confidence = self._calculate_confidence(filtered_docs)
            
            # Construction métadonnées complètes
            dependencies_status = dependency_manager.get_legacy_status()
            metadata = {
                "approach": "enhanced_rag_langsmith_intelligent_rrf",
                "optimizations_enabled": {
                    "external_redis_cache": self.optimization_stats["external_cache_used"],
                    "semantic_cache": getattr(self.cache_manager, 'ENABLE_SEMANTIC_CACHE', False) if self.cache_manager else False,
                    "hybrid_search": HYBRID_SEARCH_ENABLED,
                    "intelligent_rrf": ENABLE_INTELLIGENT_RRF and bool(self.intelligent_rrf),
                    "langsmith_monitoring": LANGSMITH_ENABLED and bool(self.langsmith_client),
                    "entity_enrichment": ENTITY_ENRICHMENT_ENABLED,
                    "advanced_guardrails": GUARDRAILS_AVAILABLE,
                    "api_diagnostics": ENABLE_API_DIAGNOSTICS,
                    "dynamic_ood_thresholds": True
                },
                "langsmith": {
                    "enabled": LANGSMITH_ENABLED,
                    "project": LANGSMITH_PROJECT,
                    "traced": bool(self.langsmith_client)
                },
                "weaviate_version": dependencies_status.get("weaviate", False),
                "documents_found": len(documents),
                "documents_used": len(filtered_docs),
                "effective_threshold": effective_threshold,
                "query_expanded": search_query != query,
                "conversation_context_used": bool(conversation_context),
                "where_filter_applied": where_filter is not None,
                "verification_enabled": RAG_VERIFICATION_ENABLED,
                "language_target": language,
                "language_detected": detect_language_enhanced(query),
                "processing_time": time.time() - start_time,
                "optimization_stats": self.optimization_stats.copy()
            }
            
            # Ajout entités détectées si disponibles
            if intent_result and hasattr(intent_result, 'detected_entities'):
                metadata["detected_entities"] = intent_result.detected_entities
                metadata["intent_type"] = intent_result.intent_type.value if hasattr(intent_result.intent_type, 'value') else str(intent_result.intent_type)
                metadata["intent_confidence"] = intent_result.confidence
            
            METRICS.observe_latency(time.time() - start_time)
            
            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=response_result.answer,
                confidence=final_confidence,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Erreur génération réponse core: {e}")
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e), "processing_time": time.time() - start_time}
            )
    
    # === RRF INTELLIGENT ===
    
    async def _enhanced_hybrid_search_with_rrf(self, query_vector: List[float], query_text: str,
                                             top_k: int, where_filter: Dict, alpha: float,
                                             original_query: str, intent_result) -> List[Document]:
        """Recherche hybride utilisant le RRF intelligent"""
        
        try:
            # Recherche vectorielle et BM25 séparément pour RRF intelligent
            vector_results = await self.retriever._vector_search_v4_corrected(
                query_vector, top_k * 2, where_filter
            )
            
            # Pour BM25, recherche hybride avec alpha=0 (BM25 pur)
            bm25_results = await self.retriever._hybrid_search_v4_corrected(
                query_vector, query_text, top_k * 2, where_filter, alpha=0.0
            )
            
            # Conversion en format Dict pour RRF intelligent
            vector_dicts = [self._document_to_dict(doc) for doc in vector_results]
            bm25_dicts = [self._document_to_dict(doc) for doc in bm25_results]
            
            # Contexte pour RRF intelligent
            query_context = {
                "query": original_query,
                "alpha": alpha,
                "top_k": top_k
            }
            
            # Fusion RRF intelligente
            fused_results = await self.intelligent_rrf.enhanced_fusion(
                vector_dicts, bm25_dicts, alpha, top_k, query_context, intent_result
            )
            
            # Reconversion en Documents
            final_documents = []
            for result_dict in fused_results:
                doc = Document(
                    content=result_dict.get("content", ""),
                    metadata=result_dict.get("metadata", {}),
                    score=result_dict.get("final_score", 0.0),
                    explain_score=result_dict.get("explain_score")
                )
                
                # Ajout métadonnées RRF intelligent
                doc.metadata["intelligent_rrf_used"] = True
                doc.metadata["rrf_method"] = result_dict.get("metadata", {}).get("rrf_method", "intelligent")
                
                final_documents.append(doc)
            
            return final_documents
            
        except Exception as e:
            logger.error(f"Erreur RRF intelligent: {e}")
            # Fallback vers recherche classique
            return await self.retriever.adaptive_search(
                query_vector, query_text, top_k, where_filter, alpha=alpha
            )
    
    def _document_to_dict(self, doc: Document) -> Dict:
        """Convertit un Document en dictionnaire pour RRF intelligent"""
        return {
            "content": doc.content,
            "metadata": doc.metadata,
            "score": doc.score,
            "explain_score": doc.explain_score
        }
    
    def _calculate_confidence(self, documents: List[Document], verification_result=None) -> float:
        """Calcule la confiance finale"""
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
        if verification_result and hasattr(verification_result, 'is_valid') and verification_result.is_valid:
            verification_factor = 1.1
        
        final_confidence = avg_score * coherence_factor * distribution_factor * verification_factor
        return min(0.95, max(0.1, final_confidence))
    
    def get_status(self) -> Dict:
        """Status enrichi avec LangSmith et RRF intelligent"""
        try:
            weaviate_connected = False
            api_capabilities = {}
            
            if self.weaviate_client:
                try:
                    weaviate_connected = self.weaviate_client.is_ready()
                except:
                    weaviate_connected = False
            
            if self.retriever and hasattr(self.retriever, 'api_capabilities'):
                api_capabilities = self.retriever.api_capabilities
            
            # Import local de dependency_manager pour éviter NameError
            from imports_and_dependencies import dependency_manager
            dependencies_status = dependency_manager.get_legacy_status()
            
            status = {
                "rag_enabled": RAG_ENABLED,
                "initialized": self.is_initialized,
                "degraded_mode": self.degraded_mode,
                "approach": "enhanced_rag_langsmith_intelligent_rrf",
                "optimizations": {
                    "external_cache_enabled": self.cache_manager.enabled if self.cache_manager else False,
                    "hybrid_search_enabled": HYBRID_SEARCH_ENABLED,
                    "intelligent_rrf_enabled": ENABLE_INTELLIGENT_RRF,
                    "langsmith_enabled": LANGSMITH_ENABLED,
                    "semantic_cache_enabled": getattr(self.cache_manager, 'ENABLE_SEMANTIC_CACHE', False) if self.cache_manager else False,
                    "entity_enrichment_enabled": ENTITY_ENRICHMENT_ENABLED,
                    "guardrails_level": GUARDRAILS_LEVEL,
                    "api_diagnostics_enabled": ENABLE_API_DIAGNOSTICS
                },
                "langsmith": {
                    "available": LANGSMITH_AVAILABLE,
                    "enabled": LANGSMITH_ENABLED,
                    "configured": bool(self.langsmith_client),
                    "project": LANGSMITH_PROJECT,
                    "traces_count": self.optimization_stats["langsmith_traces"],
                    "errors_count": self.optimization_stats["langsmith_errors"]
                },
                "intelligent_rrf": {
                    "available": INTELLIGENT_RRF_AVAILABLE,
                    "enabled": ENABLE_INTELLIGENT_RRF,
                    "configured": bool(self.intelligent_rrf),
                    "learning_mode": getattr(self, 'RRF_LEARNING_MODE', False),
                    "genetic_boost": getattr(self, 'RRF_GENETIC_BOOST', False),
                    "usage_count": self.optimization_stats["intelligent_rrf_used"],
                    "performance_stats": self.intelligent_rrf.get_performance_stats() if self.intelligent_rrf else {}
                },
                "components": dependencies_status,
                "weaviate_connected": weaviate_connected,
                "configuration": {
                    "similarity_top_k": RAG_SIMILARITY_TOP_K,
                    "confidence_threshold": RAG_CONFIDENCE_THRESHOLD,
                    "hybrid_default_alpha": DEFAULT_ALPHA,
                    "rrf_base_k": getattr(self, 'RRF_BASE_K', 60),
                    "max_conversation_context": MAX_CONVERSATION_CONTEXT
                },
                "optimization_stats": self.optimization_stats.copy(),
                "api_capabilities": api_capabilities,
                "metrics": METRICS.snapshot()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Erreur get_status: {e}")
            return {"error": str(e), "initialized": self.is_initialized}


# Factory function pour compatibilité
def create_rag_engine(openai_client=None) -> InteliaRAGEngine:
    """Factory pour créer une instance RAG Engine"""
    return InteliaRAGEngine(openai_client)