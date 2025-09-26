# -*- coding: utf-8 -*-
"""
rag_weaviate_core.py - Logique Weaviate core avec RRF intelligent
Extrait du fichier principal pour modularité
"""

import os
import asyncio
import logging
import time
import numpy as np
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Imports Weaviate
try:
    import weaviate
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False

# Imports composants existants
from .data_models import RAGResult, RAGSource, Document
from .memory import ConversationMemory
from config.config import *
from utils.utilities import (
    METRICS, build_where_filter, get_out_of_domain_message, 
    validate_intent_result, detect_language_enhanced
)

# Imports retrieval/generation
try:
    from retrieval.embedder import OpenAIEmbedder
    from retrieval.retriever import HybridWeaviateRetriever
    from generation.generators import EnhancedResponseGenerator
    from security.ood_detector import EnhancedOODDetector
    RETRIEVAL_COMPONENTS_AVAILABLE = True
except ImportError as e:
    RETRIEVAL_COMPONENTS_AVAILABLE = False
    logger.warning(f"Composants retrieval non disponibles: {e}")

# RRF Intelligent
try:
    from retrieval.enhanced_rrf_fusion import IntelligentRRFFusion
    INTELLIGENT_RRF_AVAILABLE = True
except ImportError:
    INTELLIGENT_RRF_AVAILABLE = False

# Intent processor
try:
    from processing.intent_processor import create_intent_processor
    INTENT_PROCESSOR_AVAILABLE = True
except ImportError:
    INTENT_PROCESSOR_AVAILABLE = False

# Guardrails
try:
    from security.advanced_guardrails import create_response_guardrails
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False

logger = logging.getLogger(__name__)


class WeaviateCore:
    """Logique Weaviate core avec composants RAG avancés"""

    def __init__(self, openai_client):
        self.openai_client = openai_client
        
        # Composants principaux
        self.weaviate_client = None
        self.cache_manager = None
        self.embedder = None
        self.retriever = None
        self.generator = None
        self.memory = None
        self.intent_processor = None
        self.ood_detector = None
        self.guardrails = None
        
        # RRF Intelligent
        self.intelligent_rrf = None
        
        # État
        self.is_initialized = False
        
        # Statistiques
        self.optimization_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_sets": 0,
            "hybrid_searches": 0,
            "intelligent_rrf_used": 0,
            "ood_detections": 0,
            "intent_coverage_stats": defaultdict(int),
            "weaviate_capabilities": {},
        }

    async def initialize(self):
        """Initialise le système Weaviate Core"""
        
        if not WEAVIATE_AVAILABLE:
            raise ImportError("Weaviate client requis")

        try:
            logger.info("🔧 Initialisation Weaviate Core...")

            # Connexion Weaviate
            await self._connect_weaviate()
            
            if not self.weaviate_client:
                raise Exception("Connexion Weaviate échouée")

            # Composants de base
            await self._initialize_base_components()
            
            # Retriever hybride avec RRF
            await self._initialize_hybrid_retriever()
            
            # Générateur de réponses
            await self._initialize_generator()
            
            # Intent processor
            await self._initialize_intent_processor()
            
            # Guardrails
            if GUARDRAILS_AVAILABLE:
                await self._initialize_guardrails()

            self.is_initialized = True
            logger.info("✅ Weaviate Core initialisé")

        except Exception as e:
            logger.error(f"❌ Erreur initialisation Weaviate Core: {e}")
            raise

    def set_cache_manager(self, cache_manager):
        """Configure le gestionnaire de cache"""
        self.cache_manager = cache_manager
        
        # Connecter RRF Intelligent au cache si disponible
        if (self.cache_manager and INTELLIGENT_RRF_AVAILABLE and 
            ENABLE_INTELLIGENT_RRF and self.cache_manager.enabled):
            try:
                self.intelligent_rrf = IntelligentRRFFusion(
                    redis_client=self.cache_manager.client,
                    intent_processor=self.intent_processor,
                )
                logger.info("✅ RRF Intelligent configuré avec cache")
            except Exception as e:
                logger.error(f"Erreur RRF Intelligent: {e}")

    async def _connect_weaviate(self):
        """Connexion Weaviate avec authentification et configuration OpenAI"""
        
        try:
            # Variables d'environnement Weaviate
            weaviate_url = os.getenv(
                "WEAVIATE_URL",
                "https://xmlc4jvtu6hfw9zrrmnw.c0.us-east1.gcp.weaviate.cloud",
            )
            weaviate_api_key = os.getenv("WEAVIATE_API_KEY", "")
            openai_api_key = os.getenv("OPENAI_API_KEY", "")

            logger.info(f"Tentative de connexion Weaviate: {weaviate_url}")

            # Définir OPENAI_APIKEY pour Weaviate si pas déjà définie
            if openai_api_key and "OPENAI_APIKEY" not in os.environ:
                os.environ["OPENAI_APIKEY"] = openai_api_key
                logger.debug("Variable OPENAI_APIKEY définie pour compatibilité Weaviate")

            # Connexion cloud ou locale
            if "weaviate.cloud" in weaviate_url:
                logger.debug("Utilisation connexion cloud Weaviate avec authentification")

                if weaviate_api_key:
                    try:
                        # Client v4 avec API Key et headers OpenAI
                        import weaviate.classes as wvc_classes

                        headers = {}
                        if openai_api_key:
                            headers["X-OpenAI-Api-Key"] = openai_api_key

                        self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                            cluster_url=weaviate_url,
                            auth_credentials=wvc_classes.init.Auth.api_key(weaviate_api_key),
                            headers=headers,
                        )
                        logger.info("Connexion Weaviate v4 avec API Key réussie")

                    except ImportError:
                        logger.warning("Weaviate v4 non disponible, utilisation v3")
                        # Fallback vers client v3
                        self.weaviate_client = weaviate.Client(
                            url=weaviate_url,
                            auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key),
                            additional_headers=(
                                {"X-OpenAI-Api-Key": openai_api_key}
                                if openai_api_key else {}
                            ),
                        )
                        logger.info("Connexion Weaviate v3 avec API Key réussie")

                    except Exception as auth_error:
                        logger.error(f"Erreur authentification Weaviate: {auth_error}")
                        self.weaviate_client = None
                        return
                else:
                    logger.error("WEAVIATE_API_KEY non configurée pour l'instance cloud")
                    self.weaviate_client = None
                    return
            else:
                # Connexion locale
                host = weaviate_url.replace("http://", "").replace("https://", "")
                self.weaviate_client = weaviate.connect_to_local(host=host)
                logger.info("Connexion Weaviate locale configurée")

            # Test de connexion avec timeout
            if self.weaviate_client:
                try:
                    ready = await asyncio.wait_for(
                        asyncio.to_thread(lambda: self.weaviate_client.is_ready()),
                        timeout=15.0,
                    )

                    if ready:
                        logger.info(f"Connexion Weaviate opérationnelle: {weaviate_url}")

                        # Test de capacités v4
                        try:
                            if hasattr(self.weaviate_client, "collections"):
                                await asyncio.to_thread(
                                    lambda: list(self.weaviate_client.collections.list_all())
                                )
                                logger.info("Permissions Weaviate vérifiées - accès collections OK")
                            else:
                                await asyncio.to_thread(
                                    lambda: self.weaviate_client.schema.get()
                                )
                                logger.info("Permissions Weaviate vérifiées - accès schéma OK")

                        except Exception as perm_error:
                            logger.warning(f"Permissions limitées Weaviate: {perm_error}")

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

    async def _initialize_base_components(self):
        """Initialise les composants de base"""
        
        if not RETRIEVAL_COMPONENTS_AVAILABLE:
            raise ImportError("Composants retrieval requis")

        try:
            self.embedder = OpenAIEmbedder(self.openai_client, self.cache_manager)
            self.memory = ConversationMemory(self.openai_client)
            self.ood_detector = EnhancedOODDetector(
                blocked_terms_path=None, 
                openai_client=self.openai_client
            )
            logger.info("✅ Composants de base initialisés")
        except Exception as e:
            logger.error(f"Erreur composants de base: {e}")
            raise

    async def _initialize_hybrid_retriever(self):
        """Initialise le retriever hybride avec RRF intelligent"""
        
        try:
            self.retriever = HybridWeaviateRetriever(self.weaviate_client)

            # RRF Intelligent
            if (self.intelligent_rrf and hasattr(self.retriever, "set_intelligent_rrf")):
                self.retriever.set_intelligent_rrf(self.intelligent_rrf)
                logger.info("✅ RRF Intelligent lié au retriever")

            # Diagnostic API Weaviate
            if ENABLE_API_DIAGNOSTICS:
                try:
                    await self.retriever.diagnose_weaviate_api()
                    self.optimization_stats["weaviate_capabilities"] = (
                        self.retriever.api_capabilities.copy()
                    )
                except Exception as e:
                    logger.warning(f"Diagnostic Weaviate échoué: {e}")

            logger.info("✅ Retriever hybride initialisé")

        except Exception as e:
            logger.error(f"Erreur retriever hybride: {e}")
            raise

    async def _initialize_generator(self):
        """Initialise le générateur de réponses"""
        
        try:
            self.generator = EnhancedResponseGenerator(
                self.openai_client, self.cache_manager
            )
            logger.info("✅ Générateur initialisé")
        except Exception as e:
            logger.error(f"Erreur générateur: {e}")
            raise

    async def _initialize_intent_processor(self):
        """Initialise l'intent processor"""
        
        if not INTENT_PROCESSOR_AVAILABLE:
            logger.warning("Intent processor non disponible")
            return

        try:
            from pathlib import Path

            # Tentative de résolution du chemin de configuration
            config_paths = [
                "config/intents.json",
                Path(__file__).parent.parent / "config" / "intents.json",
                Path.cwd() / "config" / "intents.json",
                os.path.join(os.path.dirname(__file__), "..", "config", "intents.json"),
            ]

            config_found = None
            for path in config_paths:
                path_obj = Path(path)
                if path_obj.exists():
                    config_found = str(path_obj.resolve())
                    break

            if config_found:
                self.intent_processor = create_intent_processor(config_found)
                logger.info(f"Intent processor initialisé avec: {config_found}")
            else:
                self.intent_processor = create_intent_processor()
                logger.info("Intent processor initialisé avec configuration par défaut")

            # Connecter RRF Intelligent
            if self.intelligent_rrf:
                self.intelligent_rrf.intent_processor = self.intent_processor

        except Exception as e:
            logger.warning(f"Intent processor non disponible: {e}")
            self.intent_processor = None

    async def _initialize_guardrails(self):
        """Initialise les guardrails"""
        
        try:
            self.guardrails = create_response_guardrails(
                self.openai_client, GUARDRAILS_LEVEL
            )
            logger.info("✅ Guardrails initialisés")
        except Exception as e:
            logger.warning(f"Guardrails échoué: {e}")

    async def generate_response(
        self,
        query: str,
        intent_result,
        conversation_context: List[Dict],
        language: str,
        start_time: float,
        tenant_id: str,
    ) -> RAGResult:
        """Génération de réponse Weaviate Core"""

        try:
            # Vérification cache
            cache_key = None
            if self.cache_manager and self.cache_manager.enabled:
                cache_key = await self._generate_cache_key(query, conversation_context, language, tenant_id)
                cached_response = await self._get_cached_response(cache_key, query, language)
                
                if cached_response:
                    self.optimization_stats["cache_hits"] += 1
                    return cached_response

                self.optimization_stats["cache_misses"] += 1

            # Intent processing
            if intent_result is None and self.intent_processor:
                try:
                    intent_result = self.intent_processor.process_query(query)
                    if intent_result:
                        METRICS.intent_detected(
                            intent_result.intent_type,
                            getattr(intent_result, "confidence", 0.8),
                        )
                        self.optimization_stats["intent_coverage_stats"][
                            intent_result.intent_type
                        ] += 1
                except Exception as e:
                    logger.warning(f"Erreur intent processor: {e}")

            # OOD detection
            if self.ood_detector:
                try:
                    is_in_domain, domain_score, score_details = (
                        self.ood_detector.calculate_ood_score_multilingual(
                            query, intent_result, language
                        )
                    )

                    if not is_in_domain:
                        self.optimization_stats["ood_detections"] += 1
                        return RAGResult(
                            source=RAGSource.OOD_FILTERED,
                            answer=get_out_of_domain_message(language),
                            confidence=0.0,
                            metadata={
                                "ood_score": domain_score,
                                "reason": "out_of_domain",
                                "language": language,
                            },
                        )
                except Exception as e:
                    logger.warning(f"Erreur OOD: {e}")

            # Préparation contexte conversation
            conversation_context_str = ""
            if conversation_context and len(conversation_context) > 0:
                recent_context = conversation_context[-MAX_CONVERSATION_CONTEXT:]
                conversation_context_str = "\n".join(
                    [
                        f"Q: {ctx.get('question', '')}\nR: {ctx.get('answer', '')[:200]}..."
                        for ctx in recent_context
                    ]
                )

            # Génération embedding
            if self.embedder:
                search_query = (
                    getattr(intent_result, "expanded_query", query)
                    if intent_result else query
                )
                query_vector = await self.embedder.get_embedding(search_query)
            else:
                query_vector = None

            if not query_vector:
                return RAGResult(
                    source=RAGSource.EMBEDDING_FAILED,
                    metadata={"error": "embedding_failed"},
                )

            # Construction filtres
            where_filter = build_where_filter(intent_result)

            # Recherche de documents
            documents = []
            if self.retriever:
                try:
                    search_alpha = (
                        getattr(intent_result, "preferred_alpha", DEFAULT_ALPHA)
                        if intent_result else DEFAULT_ALPHA
                    )

                    # Utilisation RRF intelligent si disponible
                    if (self.intelligent_rrf and 
                        hasattr(self.intelligent_rrf, "enabled") and
                        self.intelligent_rrf.enabled and ENABLE_INTELLIGENT_RRF):

                        documents = await self._enhanced_hybrid_search_with_rrf(
                            query_vector, search_query, RAG_SIMILARITY_TOP_K,
                            where_filter, search_alpha, query, intent_result,
                        )
                        self.optimization_stats["intelligent_rrf_used"] += 1

                    else:
                        documents = await self.retriever.adaptive_search(
                            query_vector, search_query, RAG_SIMILARITY_TOP_K,
                            where_filter, alpha=search_alpha,
                        )

                    if any(doc.metadata.get("hybrid_used") for doc in documents):
                        self.optimization_stats["hybrid_searches"] += 1

                except Exception as e:
                    logger.error(f"Erreur recherche hybride: {e}")
                    return RAGResult(
                        source=RAGSource.SEARCH_FAILED, 
                        metadata={"error": str(e)}
                    )

            if not documents:
                return RAGResult(source=RAGSource.NO_DOCUMENTS_FOUND)

            # Filtrage par seuil de confiance
            effective_threshold = RAG_CONFIDENCE_THRESHOLD
            filtered_docs = [doc for doc in documents if doc.score >= effective_threshold]

            if not filtered_docs:
                return RAGResult(
                    source=RAGSource.LOW_CONFIDENCE,
                    metadata={
                        "threshold": effective_threshold,
                        "max_score": max([d.score for d in documents]) if documents else 0,
                        "documents_found": len(documents),
                        "reason": "all_documents_below_threshold",
                    },
                )

            # Génération de la réponse
            if self.generator:
                response_text = await self.generator.generate_response(
                    query, filtered_docs, conversation_context_str, language, intent_result,
                )

                if not response_text:
                    return RAGResult(source=RAGSource.GENERATION_FAILED)
            else:
                return RAGResult(source=RAGSource.GENERATION_FAILED)

            # Calcul confiance finale
            final_confidence = self._calculate_confidence(filtered_docs)

            # Construction résultat
            result = RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=response_text,
                confidence=final_confidence,
                metadata={
                    "approach": "weaviate_core_v5.1",
                    "documents_found": len(documents),
                    "documents_used": len(filtered_docs),
                    "effective_threshold": effective_threshold,
                    "processing_time": time.time() - start_time,
                    "language_target": language,
                    "intelligent_rrf_used": bool(
                        self.intelligent_rrf and 
                        self.optimization_stats["intelligent_rrf_used"] > 0
                    ),
                },
            )

            # Mise en cache
            if cache_key and self.cache_manager and self.cache_manager.enabled:
                await self._cache_response(cache_key, query, result, language, conversation_context)

            METRICS.observe_latency(time.time() - start_time)
            return result

        except Exception as e:
            logger.error(f"Erreur génération réponse Weaviate Core: {e}")
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e), "processing_time": time.time() - start_time}
            )

    async def _enhanced_hybrid_search_with_rrf(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int,
        where_filter: Dict,
        alpha: float,
        original_query: str,
        intent_result,
    ) -> List[Document]:
        """Recherche hybride utilisant le RRF intelligent"""

        try:
            # Validation intent_result
            validated_intent = validate_intent_result(intent_result)
            
            is_valid = False
            if isinstance(validated_intent, dict):
                is_valid = validated_intent.get("is_valid", False)
            elif isinstance(validated_intent, bool):
                is_valid = validated_intent
            else:
                is_valid = False

            # Recherche vectorielle et BM25 séparément
            vector_results = await self.retriever._vector_search_fallback(
                query_vector, top_k * 2, where_filter
            )

            bm25_results = await self.retriever._hybrid_search_v4_corrected(
                query_vector, query_text, top_k * 2, where_filter, alpha=0.0
            )

            # Conversion pour RRF intelligent
            vector_dicts = [self._document_to_dict(doc) for doc in vector_results]
            bm25_dicts = [self._document_to_dict(doc) for doc in bm25_results]

            query_context = {
                "query": original_query,
                "alpha": alpha,
                "top_k": top_k,
                "intent_validated": is_valid,
            }

            # RRF intelligent avec gestion d'erreurs
            try:
                fused_results = await self.intelligent_rrf.enhanced_fusion(
                    vector_dicts, bm25_dicts, alpha, top_k, query_context, intent_result
                )
            except Exception as rrf_error:
                logger.error(f"Erreur RRF: {rrf_error}")
                # Fallback vers RRF classique
                fused_results = self._classic_rrf_fallback(
                    vector_dicts, bm25_dicts, alpha, top_k
                )

            # Reconversion en Documents
            final_documents = []
            for result_dict in fused_results:
                try:
                    doc = Document(
                        content=result_dict.get("content", ""),
                        metadata=result_dict.get("metadata", {}),
                        score=result_dict.get("final_score", 0.0),
                        explain_score=result_dict.get("explain_score"),
                    )

                    doc.metadata.update({
                        "intelligent_rrf_used": True,
                        "rrf_method": result_dict.get("metadata", {}).get("rrf_method", "intelligent"),
                        "intent_validated": is_valid,
                    })

                    final_documents.append(doc)

                except Exception as doc_error:
                    logger.warning(f"Erreur conversion document: {doc_error}")
                    continue

            return final_documents

        except Exception as e:
            logger.error(f"Erreur RRF intelligent: {e}")
            # Fallback vers recherche classique
            try:
                return await self.retriever.adaptive_search(
                    query_vector, query_text, top_k, where_filter, alpha=alpha,
                )
            except Exception:
                return []

    def _classic_rrf_fallback(self, vector_dicts, bm25_dicts, alpha, top_k):
        """Fallback RRF classique"""
        
        try:
            all_docs = {}
            rrf_k = 60

            # Traitement vectoriel
            for i, doc_dict in enumerate(vector_dicts):
                content_key = doc_dict.get("content", "")[:50]
                all_docs[content_key] = {
                    "doc": doc_dict,
                    "vector_rank": i + 1,
                    "bm25_rank": None,
                }

            # Traitement BM25
            for i, doc_dict in enumerate(bm25_dicts):
                content_key = doc_dict.get("content", "")[:50]
                if content_key in all_docs:
                    all_docs[content_key]["bm25_rank"] = i + 1
                else:
                    all_docs[content_key] = {
                        "doc": doc_dict,
                        "vector_rank": None,
                        "bm25_rank": i + 1,
                    }

            # Calcul RRF simple
            final_results = []
            for content_key, data in all_docs.items():
                rrf_score = 0.0

                if data["vector_rank"]:
                    rrf_score += alpha / (rrf_k + data["vector_rank"])
                if data["bm25_rank"]:
                    rrf_score += (1 - alpha) / (rrf_k + data["bm25_rank"])

                doc_dict = data["doc"].copy()
                doc_dict["final_score"] = rrf_score * 10
                doc_dict["metadata"] = doc_dict.get("metadata", {})
                doc_dict["metadata"]["rrf_method"] = "classic_fallback"

                final_results.append(doc_dict)

            return sorted(final_results, key=lambda x: x["final_score"], reverse=True)[:top_k]

        except Exception as e:
            logger.error(f"Erreur RRF fallback: {e}")
            return []

    def _document_to_dict(self, doc: Document) -> Dict:
        """Convertit un Document en dictionnaire"""
        return {
            "content": doc.content,
            "metadata": doc.metadata,
            "score": doc.score,
            "explain_score": doc.explain_score,
        }

    def _calculate_confidence(self, documents: List[Document]) -> float:
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

        final_confidence = avg_score * coherence_factor * distribution_factor
        return min(0.95, max(0.1, final_confidence))

    async def _generate_cache_key(self, query: str, conversation_context: List[Dict], language: str, tenant_id: str) -> str:
        """Génère une clé de cache"""
        
        import hashlib
        
        context_hash = ""
        if conversation_context:
            context_str = str(conversation_context)
            context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]

        return f"{tenant_id}:{hashlib.md5(query.encode()).hexdigest()}:{language}:{context_hash}"

    async def _get_cached_response(self, cache_key: str, query: str, language: str) -> Optional[RAGResult]:
        """Récupère une réponse depuis le cache"""
        
        try:
            if hasattr(self.cache_manager, "semantic_cache"):
                context_hash = cache_key.split(":")[-1]
                cached_response = await self.cache_manager.semantic_cache.get_response(
                    query, context_hash, language
                )
            else:
                cached_response = await self.cache_manager.get(cache_key)
                if cached_response and isinstance(cached_response, bytes):
                    cached_response = cached_response.decode("utf-8")

            if cached_response:
                if isinstance(cached_response, str):
                    return RAGResult(
                        source=RAGSource.RAG_SUCCESS,
                        answer=cached_response,
                        confidence=0.85,
                        metadata={"cache_hit": True, "cache_type": "weaviate_core"},
                    )
                elif isinstance(cached_response, dict):
                    return RAGResult(
                        source=RAGSource.RAG_SUCCESS,
                        answer=cached_response.get("answer", ""),
                        confidence=cached_response.get("confidence", 0.85),
                        metadata={
                            "cache_hit": True, 
                            "cache_type": "weaviate_core",
                            **cached_response.get("metadata", {}),
                        },
                    )

        except Exception as e:
            logger.warning(f"Erreur consultation cache: {e}")

        return None

    async def _cache_response(self, cache_key: str, query: str, result: RAGResult, language: str, conversation_context: List[Dict]):
        """Met en cache une réponse"""
        
        try:
            if hasattr(self.cache_manager, "semantic_cache"):
                context_hash = cache_key.split(":")[-1] if conversation_context else ""
                await self.cache_manager.semantic_cache.set_response(
                    query, context_hash, result.answer, language
                )
            else:
                import json
                cache_data = {
                    "answer": result.answer,
                    "confidence": result.confidence,
                    "timestamp": time.time(),
                    "metadata": {"cached_at": time.time(), "cache_version": "weaviate_core_1.0"},
                }
                await self.cache_manager.set(
                    cache_key,
                    json.dumps(cache_data).encode("utf-8"),
                    ttl=3600,
                )

            self.optimization_stats["cache_sets"] += 1

        except Exception as e:
            logger.warning(f"Erreur mise en cache: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques Weaviate Core"""
        
        return {
            "weaviate_core_initialized": self.is_initialized,
            "weaviate_connected": bool(self.weaviate_client),
            "components_loaded": {
                "embedder": bool(self.embedder),
                "retriever": bool(self.retriever),
                "generator": bool(self.generator),
                "memory": bool(self.memory),
                "intent_processor": bool(self.intent_processor),
                "ood_detector": bool(self.ood_detector),
                "guardrails": bool(self.guardrails),
                "intelligent_rrf": bool(self.intelligent_rrf),
            },
            "optimization_stats": self.optimization_stats.copy(),
        }

    async def close(self):
        """Fermeture propre Weaviate Core"""
        
        if hasattr(self.weaviate_client, "close"):
            try:
                await self.weaviate_client.close()
                logger.info("Weaviate client fermé")
            except Exception as e:
                logger.warning(f"Erreur fermeture Weaviate: {e}")

        logger.info("Weaviate Core fermé")
