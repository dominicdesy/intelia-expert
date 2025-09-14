# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine amélioré avec LlamaIndex
Préserve votre intelligence métier avec améliorations de performance
Version corrigée pour compatibilité et gestion d'erreurs robuste
Fix httpx >= 0.28 pour éviter les crashes de proxy
"""

import os
import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
import httpx  # ⬅️ AJOUT pour fix proxy

# Configuration de logging améliorée
logger = logging.getLogger(__name__)

# Import Weaviate avec gestion des versions et erreurs
try:
    import weaviate
    # Vérifier la version de weaviate
    weaviate_version = getattr(weaviate, '__version__', '4.0.0')
    
    if weaviate_version.startswith('4.'):
        # Version 4.x - nouvelle API
        try:
            import weaviate.classes as wvc
            WEAVIATE_V4 = True
        except ImportError:
            wvc = None
            WEAVIATE_V4 = False
    else:
        # Version 3.x - ancienne API
        WEAVIATE_V4 = False
        wvc = None
    
    WEAVIATE_AVAILABLE = True
    logger.info(f"Weaviate {weaviate_version} détecté (V4: {WEAVIATE_V4})")
    
except ImportError as e:
    WEAVIATE_AVAILABLE = False
    WEAVIATE_V4 = False
    wvc = None
    weaviate = None
    logger.warning(f"Weaviate non disponible: {e}")

# Tentatives d'import LlamaIndex avec fallbacks multiples
LLAMAINDEX_AVAILABLE = False
LLAMAINDEX_WEAVIATE_AVAILABLE = False
LLAMAINDEX_LLM_AVAILABLE = False

# Import LlamaIndex Core
try:
    from llama_index.core import VectorStoreIndex, Settings, get_response_synthesizer
    from llama_index.core.retrievers import VectorIndexRetriever
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.core.postprocessor import SimilarityPostprocessor
    from llama_index.core.schema import QueryBundle, NodeWithScore
    from llama_index.core.base.base_retriever import BaseRetriever
    LLAMAINDEX_AVAILABLE = True
    logger.info("LlamaIndex Core chargé avec succès")
except ImportError as e:
    logger.warning(f"LlamaIndex Core non disponible: {e}")
    # Classes de fallback pour éviter les erreurs
    class VectorStoreIndex:
        pass
    class Settings:
        pass
    class BaseRetriever:
        pass
    class NodeWithScore:
        pass
    class QueryBundle:
        pass

# Import LlamaIndex Embeddings avec fallback
try:
    from llama_index.embeddings.openai import OpenAIEmbedding
    LLAMAINDEX_EMBEDDINGS_AVAILABLE = True
    logger.info("LlamaIndex OpenAI Embeddings chargé")
except ImportError:
    try:
        from llama_index.core.embeddings import OpenAIEmbedding
        LLAMAINDEX_EMBEDDINGS_AVAILABLE = True
        logger.info("LlamaIndex Core Embeddings chargé (fallback)")
    except ImportError as e:
        LLAMAINDEX_EMBEDDINGS_AVAILABLE = False
        logger.warning(f"LlamaIndex Embeddings non disponible: {e}")
        class OpenAIEmbedding:
            def __init__(self, *args, **kwargs):
                pass

# Import LlamaIndex LLM avec fallbacks multiples
try:
    from llama_index.llms.openai import OpenAI as LlamaOpenAI
    LLAMAINDEX_LLM_AVAILABLE = True
    logger.info("LlamaIndex OpenAI LLM chargé")
except ImportError:
    try:
        from llama_index.core.llms.openai import OpenAI as LlamaOpenAI
        LLAMAINDEX_LLM_AVAILABLE = True
        logger.info("LlamaIndex Core OpenAI LLM chargé (fallback)")
    except ImportError:
        try:
            from llama_index.core.llms import OpenAI as LlamaOpenAI
            LLAMAINDEX_LLM_AVAILABLE = True
            logger.info("LlamaIndex Core LLM chargé (fallback 2)")
        except ImportError as e:
            LLAMAINDEX_LLM_AVAILABLE = False
            logger.warning(f"LlamaIndex LLM non disponible: {e}")
            class LlamaOpenAI:
                def __init__(self, *args, **kwargs):
                    pass

# Import LlamaIndex Weaviate avec fallback
try:
    from llama_index.vector_stores.weaviate import WeaviateVectorStore
    LLAMAINDEX_WEAVIATE_AVAILABLE = True
    logger.info("LlamaIndex WeaviateVectorStore chargé avec succès")
except ImportError as e1:
    try:
        # Fallback pour ancienne structure
        from llama_index.vector_stores import WeaviateVectorStore
        LLAMAINDEX_WEAVIATE_AVAILABLE = True
        logger.info("LlamaIndex WeaviateVectorStore chargé (fallback)")
    except ImportError as e2:
        LLAMAINDEX_WEAVIATE_AVAILABLE = False
        WeaviateVectorStore = None
        logger.warning(f"LlamaIndex WeaviateVectorStore non disponible. Erreurs: {e1}, {e2}")

# OpenAI import pour compatibilité
from openai import OpenAI

# VoyageAI pour reranking avancé
try:
    import voyageai
    VOYAGE_AVAILABLE = True
except ImportError:
    VOYAGE_AVAILABLE = False
    logger.warning("VoyageAI not available - using basic reranking")

# Vos imports métier (préservés intégralement)
try:
    from intent_processor import create_intent_processor, IntentType, IntentResult
    INTENT_PROCESSOR_AVAILABLE = True
except ImportError as e:
    INTENT_PROCESSOR_AVAILABLE = False
    logger.warning(f"Intent processor non disponible: {e}")
    # Classes de fallback
    class IntentType:
        METRIC_QUERY = "metric_query"
        OUT_OF_DOMAIN = "out_of_domain"
    class IntentResult:
        def __init__(self):
            self.intent_type = IntentType.METRIC_QUERY
            self.confidence = 0.8
            self.detected_entities = {}
            self.expanded_query = ""
            self.metadata = {}

# Configuration par variables d'environnement (améliorées)
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

# Paramètres RAG optimisés
RAG_SIMILARITY_TOP_K = int(os.getenv("RAG_SIMILARITY_TOP_K", "15"))
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.65"))
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1024"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))

# Nouveaux paramètres pour optimisation
RAG_RERANK_TOP_K = int(os.getenv("RAG_RERANK_TOP_K", "8"))
RAG_HYBRID_ALPHA = float(os.getenv("RAG_HYBRID_ALPHA", "0.7"))
RAG_VERIFICATION_ENABLED = os.getenv("RAG_VERIFICATION_ENABLED", "true").lower() == "true"


def _build_openai_client() -> OpenAI:   # ⬅️ AJOUT pour fix proxy
    """
    Construit un client OpenAI avec un httpx.Client explicite, sans proxies implicites.
    Évite le crash avec httpx >= 0.28 où les proxies par défaut peuvent causer des erreurs.
    
    Si vous devez absolument utiliser un proxy, remplacez la ligne httpx.Client(...) par:
        httpx.Client(proxies=os.getenv("OPENAI_HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY"), timeout=30.0)
    """
    try:
        # Client httpx sans proxies automatiques pour éviter les crashes
        http_client = httpx.Client(timeout=30.0)  # pas d'argument 'proxies' -> évite le crash
        return OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
    except Exception as e:
        logger.warning(f"Erreur création client OpenAI avec httpx personnalisé: {e}")
        # Fallback vers client OpenAI standard
        return OpenAI(api_key=OPENAI_API_KEY)


class RAGSource(Enum):
    """Sources de réponse (compatibilité avec votre système)"""
    RAG_KNOWLEDGE = "rag_knowledge"
    RAG_VERIFIED = "rag_verified"
    OOD_FILTERED = "ood_filtered" 
    FALLBACK_NEEDED = "fallback_needed"
    ERROR = "error"
    DEGRADED_MODE = "degraded_mode"


@dataclass
class RAGResult:
    """Résultat RAG compatible avec votre système actuel - amélioré"""
    source: RAGSource
    answer: Optional[str] = None
    confidence: float = 0.0
    context_docs: List[Dict] = None
    processing_time: float = 0.0
    metadata: Dict = None
    verification_status: Optional[Dict] = None
    intent_result: Optional[IntentResult] = None
    
    def __post_init__(self):
        if self.context_docs is None:
            self.context_docs = []
        if self.metadata is None:
            self.metadata = {}
        if self.verification_status is None:
            self.verification_status = {}


class EnhancedOODDetector:
    """Détecteur hors-domaine amélioré avec scoring multi-facteurs"""
    
    def __init__(self, blocked_terms_path: str = None):
        self.blocked_terms = self._load_blocked_terms(blocked_terms_path)
        self.domain_keywords = {
            'poulet', 'poule', 'aviculture', 'élevage', 'volaille', 'poids', 'fcr',
            'aliment', 'vaccination', 'maladie', 'production', 'croissance',
            'chicken', 'poultry', 'broiler', 'layer', 'feed', 'weight', 'growth',
            'température', 'ventilation', 'eau', 'water', 'temperature', 'incubation',
            'couvoir', 'hatchery', 'biosécurité', 'mortalité', 'mortality', 'performance',
            'ross', 'cobb', 'hubbard', 'isa', 'lohmann'
        }
        
    def _load_blocked_terms(self, path: str = None) -> Dict[str, List[str]]:
        """Charge les termes bloqués depuis blocked_terms.json"""
        if path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, "blocked_terms.json")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur chargement blocked_terms.json: {e}")
            return {}
    
    def calculate_ood_score(self, query: str) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul de score OOD multi-facteurs amélioré"""
        query_lower = query.lower()
        words = query_lower.split()
        
        # Score 1: Vocabulaire du domaine
        domain_words = [word for word in words if word in self.domain_keywords]
        vocab_score = len(domain_words) / len(words) if words else 0.0
        
        # Score 2: Termes bloqués avec pondération par catégorie
        blocked_score = 0.0
        blocked_categories = []
        
        for category, terms in self.blocked_terms.items():
            category_matches = sum(1 for term in terms if term in query_lower)
            if category_matches > 0:
                blocked_categories.append(category)
                category_penalty = min(1.0, category_matches / max(1, len(words) // 2))
                blocked_score = max(blocked_score, category_penalty)
        
        # Score 3: Patterns spécifiques hors-domaine
        ood_patterns = [
            r'\b(film|movie|cinema|série|series)\b',
            r'\b(football|sport|match)\b',
            r'\b(politique|president|élection)\b',
            r'\b(crypto|bitcoin|bourse)\b'
        ]
        
        import re
        pattern_score = 0.0
        for pattern in ood_patterns:
            if re.search(pattern, query_lower):
                pattern_score = 1.0
                break
        
        # Fusion des scores avec logique adaptative
        if blocked_score > 0.5:
            final_score = 0.9
        elif vocab_score > 0.3:
            final_score = max(0.0, vocab_score - blocked_score * 0.5)
        else:
            final_score = (vocab_score * 0.6) - (blocked_score * 0.3) - (pattern_score * 0.1)
        
        is_in_domain = final_score > 0.15
        
        score_details = {
            "vocab_score": vocab_score,
            "blocked_score": blocked_score,
            "pattern_score": pattern_score,
            "blocked_categories": blocked_categories,
            "final_score": final_score
        }
        
        logger.debug(f"OOD Analysis: '{query}' -> in_domain={is_in_domain}, scores={score_details}")
        
        return is_in_domain, final_score, score_details


class MultiStageReranker:
    """Système de reranking multi-étapes pour améliorer la pertinence"""
    
    def __init__(self):
        self.voyage_client = None
        if VOYAGE_AVAILABLE and VOYAGE_API_KEY:
            try:
                self.voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
                logger.info("VoyageAI reranker initialisé")
            except Exception as e:
                logger.warning(f"Erreur init VoyageAI: {e}")
                self.voyage_client = None
    
    async def rerank(self, query: str, results: List, intent_result = None) -> List:
        """Reranking multi-étapes des résultats - version robuste"""
        
        if not results:
            return results
        
        try:
            # Stage 1: VoyageAI semantic reranking (si disponible)
            if self.voyage_client and len(results) > 2:
                results = await self._voyage_rerank(query, results)
            
            # Stage 2: Intent-based boosting (votre logique métier préservée)
            if intent_result:
                results = self._intent_boost(results, intent_result)
            
            # Stage 3: Diversity filtering pour éviter la redondance
            results = self._diversify_results(results)
            
            return results[:RAG_RERANK_TOP_K]
            
        except Exception as e:
            logger.error(f"Erreur reranking: {e}")
            return results[:RAG_RERANK_TOP_K]
    
    async def _voyage_rerank(self, query: str, results: List) -> List:
        """Reranking VoyageAI pour pertinence sémantique"""
        try:
            documents = []
            for node in results:
                if hasattr(node, 'text'):
                    documents.append(node.text)
                elif hasattr(node, 'content'):
                    documents.append(node.content)
                else:
                    documents.append(str(node))
            
            reranked = self.voyage_client.rerank(
                query=query,
                documents=documents,
                model="rerank-1",
                top_k=min(len(results), 12)
            )
            
            # Réorganiser selon les scores VoyageAI
            reranked_results = []
            for item in reranked.results:
                original_node = results[item.index]
                if hasattr(original_node, 'score'):
                    try:
                        original_score = float(original_node.score) if original_node.score is not None else 0.5
                        combined_score = (original_score * 0.3 + item.relevance_score * 0.7)
                        original_node.score = combined_score
                    except (ValueError, TypeError):
                        original_node.score = item.relevance_score
                reranked_results.append(original_node)
            
            logger.debug(f"VoyageAI reranked {len(results)} -> {len(reranked_results)} results")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Erreur VoyageAI reranking: {e}")
            return results
    
    def _intent_boost(self, results: List, intent_result) -> List:
        """Boost basé sur l'intention détectée (votre logique métier)"""
        
        for node in results:
            boost_factor = 1.0
            
            try:
                # Boost pour correspondance de lignée génétique
                if hasattr(intent_result, 'detected_entities') and "line" in intent_result.detected_entities:
                    target_line = intent_result.detected_entities["line"].lower()
                    if hasattr(node, 'metadata'):
                        node_line = node.metadata.get("geneticLine", "").lower()
                        if target_line in node_line or node_line in target_line:
                            boost_factor *= 1.3
                
                # Boost pour correspondance d'âge
                if hasattr(intent_result, 'detected_entities') and "age_days" in intent_result.detected_entities:
                    boost_factor *= 1.2
                
                # Boost pour type d'intention
                if hasattr(intent_result, 'intent_type') and intent_result.intent_type == IntentType.METRIC_QUERY:
                    # Privilégier les documents avec des données chiffrées
                    text_content = getattr(node, 'text', '') or getattr(node, 'content', '')
                    if any(char.isdigit() for char in text_content[:200]):
                        boost_factor *= 1.1
                
                # Appliquer le boost
                if hasattr(node, 'score') and node.score is not None:
                    try:
                        original_score = float(node.score)
                        node.score = min(1.0, original_score * boost_factor)
                    except (ValueError, TypeError):
                        logger.warning(f"Score invalide pour boosting: {node.score}")
                        
            except Exception as e:
                logger.warning(f"Erreur intent boost: {e}")
                continue
        
        # Retrier par score
        try:
            return sorted(results, key=lambda x: getattr(x, 'score', 0.0), reverse=True)
        except Exception as e:
            logger.warning(f"Erreur tri par score: {e}")
            return results
    
    def _diversify_results(self, results: List) -> List:
        """Filtrage de diversité pour éviter la redondance"""
        if len(results) <= 3:
            return results
        
        try:
            diversified = [results[0]]  # Premier résultat toujours inclus
            
            for candidate in results[1:]:
                # Vérifier la similarité avec les résultats déjà sélectionnés
                is_diverse = True
                candidate_text = (getattr(candidate, 'text', '') or getattr(candidate, 'content', '')).lower()
                
                for selected in diversified:
                    selected_text = (getattr(selected, 'text', '') or getattr(selected, 'content', '')).lower()
                    
                    if candidate_text and selected_text:
                        candidate_words = set(candidate_text.split())
                        selected_words = set(selected_text.split())
                        
                        if len(candidate_words) > 0 and len(selected_words) > 0:
                            overlap = len(candidate_words.intersection(selected_words))
                            similarity = overlap / min(len(candidate_words), len(selected_words))
                            
                            if similarity > 0.8:  # Trop similaire
                                is_diverse = False
                                break
                
                if is_diverse:
                    diversified.append(candidate)
            
            return diversified
            
        except Exception as e:
            logger.warning(f"Erreur diversification: {e}")
            return results


class ResponseVerifier:
    """Vérification des réponses pour réduire les hallucinations"""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
    
    async def verify_response(self, query: str, response: str, context_docs: List[Dict]) -> Dict[str, Any]:
        """Chain-of-Verification pour détecter les hallucinations"""
        
        if not RAG_VERIFICATION_ENABLED or not context_docs:
            return {"verified": True, "confidence": 0.8, "corrections": []}
        
        try:
            # Construire le contexte de vérification
            context_text = "\n\n".join([
                f"Document {i+1}: {doc.get('content', '')[:500]}"
                for i, doc in enumerate(context_docs[:3])
            ])
            
            verification_prompt = f"""Tu es un expert en vérification factuelle pour l'aviculture.

TÂCHE: Vérifie si chaque affirmation dans la RÉPONSE est supportée par les DOCUMENTS fournis.

RÉPONSE À VÉRIFIER:
{response}

DOCUMENTS DE RÉFÉRENCE:
{context_text}

INSTRUCTIONS:
1. Identifie chaque affirmation factuelle dans la réponse
2. Vérifie si elle est explicitement supportée par les documents
3. Signale toute information non supportée ou potentiellement incorrecte
4. Propose des corrections si nécessaire

FORMAT DE RÉPONSE:
- STATUT: [VÉRIFIÉ/PARTIELLEMENT_VÉRIFIÉ/NON_VÉRIFIÉ]
- CONFIANCE: [0.0-1.0]
- PROBLÈMES: [liste des problèmes identifiés]
- CORRECTIONS: [corrections suggérées]"""

            verification = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": verification_prompt}],
                temperature=0.0,
                max_tokens=500
            )
            
            verification_text = verification.choices[0].message.content
            
            # Parser la réponse de vérification (simple)
            status = "VÉRIFIÉ"
            confidence = 0.8
            corrections = []
            
            if "NON_VÉRIFIÉ" in verification_text:
                status = "NON_VÉRIFIÉ"
                confidence = 0.3
            elif "PARTIELLEMENT_VÉRIFIÉ" in verification_text:
                status = "PARTIELLEMENT_VÉRIFIÉ"
                confidence = 0.6
            
            # Extraire les corrections si mentionnées
            if "CORRECTIONS:" in verification_text:
                corrections_section = verification_text.split("CORRECTIONS:")[-1].strip()
                if corrections_section and len(corrections_section) > 10:
                    corrections.append(corrections_section)
            
            return {
                "verified": status == "VÉRIFIÉ",
                "status": status,
                "confidence": confidence,
                "corrections": corrections,
                "verification_detail": verification_text,
                "processing_time": time.time()
            }
            
        except Exception as e:
            logger.error(f"Erreur vérification: {e}")
            return {
                "verified": True,  # Fail-safe
                "confidence": 0.7,
                "corrections": [],
                "error": str(e)
            }


class ConversationMemoryEnhanced:
    """Mémoire de conversation améliorée avec résumés contextuels"""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.memory_store = {}
        self.max_exchanges = 5
        self.max_context_length = 2000
    
    async def get_contextual_memory(self, tenant_id: str, current_query: str) -> str:
        """Récupère et résume le contexte pertinent de la conversation"""
        
        if tenant_id not in self.memory_store:
            return ""
        
        history = self.memory_store[tenant_id]
        if not history:
            return ""
        
        # Si l'historique est court, retourner tel quel
        if len(history) <= 2:
            context_parts = []
            for entry in history:
                context_parts.append(f"Q: {entry['question']}\nR: {entry['answer']}")
            return "\n\n".join(context_parts)
        
        # Pour un historique plus long, créer un résumé intelligent
        try:
            history_text = "\n\n".join([
                f"Échange {i+1}:\nQ: {entry['question']}\nR: {entry['answer']}"
                for i, entry in enumerate(history[-4:])  # 4 derniers échanges
            ])
            
            summary_prompt = f"""Résume cette conversation sur l'aviculture en conservant:
1. Les entités importantes (lignées, âges, métriques)
2. Le contexte technique pertinent pour cette nouvelle question
3. Les informations factuelles clés

HISTORIQUE:
{history_text}

NOUVELLE QUESTION: {current_query}

Résumé contextuel (maximum 200 mots):"""

            summary = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.1,
                max_tokens=250
            )
            
            return summary.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erreur résumé conversation: {e}")
            # Fallback vers contexte simple
            return f"Contexte: {history[-1]['question']} -> {history[-1]['answer'][:100]}..."
    
    def add_exchange(self, tenant_id: str, question: str, answer: str):
        """Ajoute un échange à la mémoire"""
        if tenant_id not in self.memory_store:
            self.memory_store[tenant_id] = []
        
        self.memory_store[tenant_id].append({
            "question": question,
            "answer": answer,
            "timestamp": time.time()
        })
        
        # Garder seulement les N derniers échanges
        if len(self.memory_store[tenant_id]) > self.max_exchanges:
            self.memory_store[tenant_id] = self.memory_store[tenant_id][-self.max_exchanges:]


class PoultryFilteredRetriever:
    """Retriever personnalisé utilisant votre intelligence métier - version robuste"""
    
    def __init__(self, base_retriever, intent_processor, reranker: MultiStageReranker):
        self.base_retriever = base_retriever
        self.intent_processor = intent_processor
        self.reranker = reranker
        
    async def retrieve(self, query_bundle) -> List:
        """Retrieval avec filtrage intelligent - version robuste"""
        
        try:
            # Analyse avec votre processeur d'intentions
            intent_result = None
            if self.intent_processor:
                try:
                    intent_result = self.intent_processor.process_query(
                        query_bundle.query_str if hasattr(query_bundle, 'query_str') else str(query_bundle)
                    )
                except Exception as e:
                    logger.warning(f"Erreur intent processor: {e}")
                    intent_result = None
            
            # Recherche de base avec paramètres adaptatifs selon l'intention
            if intent_result and hasattr(intent_result, 'intent_type') and intent_result.intent_type == IntentType.METRIC_QUERY:
                # Plus de résultats pour les questions métriques
                if hasattr(self.base_retriever, '_similarity_top_k'):
                    self.base_retriever._similarity_top_k = min(20, RAG_SIMILARITY_TOP_K + 5)
            else:
                if hasattr(self.base_retriever, '_similarity_top_k'):
                    self.base_retriever._similarity_top_k = RAG_SIMILARITY_TOP_K
            
            # Exécuter la recherche de base
            try:
                if hasattr(self.base_retriever, 'retrieve'):
                    nodes = self.base_retriever.retrieve(query_bundle)
                else:
                    nodes = []
            except Exception as e:
                logger.error(f"Erreur base retrieval: {e}")
                nodes = []
            
            # Filtrage post-retrieval basé sur vos critères métier
            filtered_nodes = []
            for node in nodes:
                if self._matches_domain_criteria(node, intent_result):
                    # Enrichir avec métadonnées métier
                    if intent_result and hasattr(node, 'metadata'):
                        if hasattr(intent_result, 'intent_type'):
                            node.metadata["intent_type"] = intent_result.intent_type.value if hasattr(intent_result.intent_type, 'value') else str(intent_result.intent_type)
                        if hasattr(intent_result, 'detected_entities'):
                            node.metadata["detected_entities"] = intent_result.detected_entities
                    filtered_nodes.append(node)
            
            # Reranking multi-étapes
            if len(filtered_nodes) > 1:
                query_str = query_bundle.query_str if hasattr(query_bundle, 'query_str') else str(query_bundle)
                filtered_nodes = await self.reranker.rerank(
                    query_str, 
                    filtered_nodes, 
                    intent_result
                )
            
            logger.debug(f"Enhanced retrieval: {len(filtered_nodes)}/{len(nodes)} nodes after filtering and reranking")
            return filtered_nodes
            
        except Exception as e:
            logger.error(f"Erreur dans retrieve: {e}")
            return []
    
    def _matches_domain_criteria(self, node, intent_result) -> bool:
        """Vérification des critères de domaine - logique préservée et robuste"""
        
        try:
            # Vérification domaine avicole (votre logique préservée)
            if intent_result and hasattr(intent_result, 'intent_type') and intent_result.intent_type == IntentType.OUT_OF_DOMAIN:
                return False
            
            # Filtrage par score de confiance amélioré
            try:
                node_score = float(node.score) if hasattr(node, 'score') and node.score is not None else 0.0
                if node_score < RAG_CONFIDENCE_THRESHOLD:
                    return False
            except (ValueError, TypeError):
                logger.warning(f"Score invalide ignoré: {getattr(node, 'score', None)}")
                return True  # Garder par défaut si score invalide
            
            # Filtrage par lignée génétique si spécifiée (votre logique préservée)
            if (intent_result and hasattr(intent_result, 'detected_entities') and 
                "line" in intent_result.detected_entities and hasattr(node, 'metadata')):
                node_line = node.metadata.get("geneticLine", "").lower()
                target_line = intent_result.detected_entities["line"].lower()
                if node_line and target_line not in node_line and node_line not in target_line:
                    logger.debug(f"Filtered out node: genetic line mismatch ({node_line} vs {target_line})")
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Erreur domain criteria: {e}")
            return True  # Fail-safe


class InteliaRAGEngine:
    """Engine RAG principal utilisant LlamaIndex avec votre intelligence métier - Version robuste avec fix httpx"""
    
    def __init__(self, openai_client: OpenAI = None):
        # ⬇️ Remplace l'appel direct par la fabrique qui neutralise les proxies implicites
        self.openai_client = openai_client or _build_openai_client()
        self.intent_processor = None
        self.ood_detector = None
        self.reranker = None
        self.verifier = None
        self.conversation_memory = None
        self.weaviate_client = None
        self.vector_store = None
        self.index = None
        self.query_engine = None
        self.is_initialized = False
        self.degraded_mode = False
        
    async def initialize(self):
        """Initialisation du système RAG hybride amélioré - Version robuste"""
        if self.is_initialized:
            return
            
        logger.info("Initialisation Intelia RAG Engine Enhanced avec LlamaIndex...")
        
        # Vérifier les dépendances critiques
        if not WEAVIATE_AVAILABLE or not LLAMAINDEX_WEAVIATE_AVAILABLE:
            logger.warning(f"Weaviate non disponible - Mode dégradé activé. WEAVIATE_AVAILABLE: {WEAVIATE_AVAILABLE}, LLAMAINDEX_WEAVIATE_AVAILABLE: {LLAMAINDEX_WEAVIATE_AVAILABLE}")
            self.degraded_mode = True
        
        # Configuration globale LlamaIndex avec gestion d'erreurs robuste
        try:
            if LLAMAINDEX_AVAILABLE and LLAMAINDEX_LLM_AVAILABLE:
                try:
                    Settings.llm = LlamaOpenAI(
                        model="gpt-4o-mini",
                        api_key=OPENAI_API_KEY,
                        temperature=0.1,
                        max_tokens=800
                    )
                    logger.info("LlamaIndex LLM configuré avec succès")
                except Exception as e:
                    logger.warning(f"Erreur configuration LlamaIndex LLM: {e}")
                    # Continuer sans LLM configuré
                    pass
            
            if LLAMAINDEX_AVAILABLE and LLAMAINDEX_EMBEDDINGS_AVAILABLE:
                try:
                    Settings.embed_model = OpenAIEmbedding(
                        model="text-embedding-3-small",
                        api_key=OPENAI_API_KEY
                    )
                    logger.info("LlamaIndex Embeddings configuré avec succès")
                except Exception as e:
                    logger.warning(f"Erreur configuration LlamaIndex Embeddings: {e}")
                    # Continuer sans embeddings configurés
                    pass
            
            if LLAMAINDEX_AVAILABLE:
                Settings.chunk_size = RAG_CHUNK_SIZE
                Settings.chunk_overlap = RAG_CHUNK_OVERLAP
                
        except Exception as e:
            logger.error(f"Erreur configuration LlamaIndex: {e}")
            self.degraded_mode = True
        
        # Initialisation des composants améliorés
        try:
            if INTENT_PROCESSOR_AVAILABLE:
                self.intent_processor = create_intent_processor()
            else:
                logger.warning("Intent processor non disponible - fonctionnalité désactivée")
                
            self.ood_detector = EnhancedOODDetector()
            self.reranker = MultiStageReranker()
            self.verifier = ResponseVerifier(self.openai_client)
            self.conversation_memory = ConversationMemoryEnhanced(self.openai_client)
            logger.info("Composants d'intelligence métier initialisés")
        except Exception as e:
            logger.error(f"Erreur init composants métier: {e}")
            # Continuer avec composants par défaut
            self.ood_detector = EnhancedOODDetector()
            self.reranker = MultiStageReranker()
            self.verifier = ResponseVerifier(self.openai_client)
            self.conversation_memory = ConversationMemoryEnhanced(self.openai_client)
        
        # Connexion Weaviate (votre configuration préservée)
        if not self.degraded_mode:
            try:
                await self._connect_weaviate()
                # Construction de l'index et query engine améliorés
                await self._build_enhanced_query_engine()
            except Exception as e:
                logger.error(f"Erreur Weaviate/Query Engine: {e}")
                self.degraded_mode = True
        
        self.is_initialized = True
        status_msg = "RAG Engine Enhanced initialisé avec succès"
        if self.degraded_mode:
            status_msg += " (Mode dégradé - certaines fonctionnalités limitées)"
        logger.info(status_msg)
    
    async def _connect_weaviate(self):
        """Connexion à votre instance Weaviate existante - version robuste"""
        
        # Vérifier si Weaviate est disponible
        if not WEAVIATE_AVAILABLE or not LLAMAINDEX_WEAVIATE_AVAILABLE:
            raise Exception(
                f"Weaviate non disponible. WEAVIATE_AVAILABLE: {WEAVIATE_AVAILABLE}, "
                f"LLAMAINDEX_WEAVIATE_AVAILABLE: {LLAMAINDEX_WEAVIATE_AVAILABLE}"
            )
        
        try:
            if WEAVIATE_V4:
                # Version 4.x - nouvelle API
                if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                    # Cloud connection
                    if wvc:
                        auth_credentials = wvc.init.Auth.api_key(WEAVIATE_API_KEY)
                        self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                            cluster_url=WEAVIATE_URL,
                            auth_credentials=auth_credentials,
                            headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                        )
                    else:
                        raise Exception("weaviate.classes (wvc) non disponible pour connexion cloud")
                else:
                    # Local connection v4
                    host = WEAVIATE_URL.replace('http://', '').replace('https://', '')
                    port = 8080
                    if ':' in host:
                        host, port = host.split(':')
                        port = int(port)
                    
                    self.weaviate_client = weaviate.connect_to_local(
                        host=host,
                        port=port,
                        headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                    )
            else:
                # Version 3.x - ancienne API (compatibilité)
                if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                    # Cloud connection v3
                    auth_config = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
                    
                    self.weaviate_client = weaviate.Client(
                        url=WEAVIATE_URL,
                        auth_client_secret=auth_config,
                        additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                    )
                else:
                    # Local connection v3
                    self.weaviate_client = weaviate.Client(
                        url=WEAVIATE_URL,
                        additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                    )
            
            # Vérifier la connexion
            if hasattr(self.weaviate_client, 'is_ready'):
                if self.weaviate_client.is_ready():
                    logger.info(f"Connexion Weaviate établie (Version {weaviate_version})")
                else:
                    raise Exception("Weaviate not ready")
            else:
                # Pour v3, pas de méthode is_ready(), tester avec schema
                try:
                    self.weaviate_client.schema.get()
                    logger.info(f"Connexion Weaviate v3 établie")
                except Exception:
                    raise Exception("Weaviate v3 connection failed")
                    
        except Exception as e:
            logger.error(f"Erreur connexion Weaviate: {e}")
            self.weaviate_client = None
            raise
    
    async def _build_enhanced_query_engine(self):
        """Construction du query engine avec intelligence métier améliorée - version robuste"""
        
        # Vérifier que Weaviate est disponible
        if not self.weaviate_client or not LLAMAINDEX_WEAVIATE_AVAILABLE:
            logger.warning("Weaviate non disponible - Query engine désactivé")
            self.query_engine = None
            return
        
        # Vector store LlamaIndex avec votre collection
        try:
            if WEAVIATE_V4:
                # Version 4.x - nouvelle API
                try:
                    collection = self.weaviate_client.collections.get("InteliaKnowledge")
                    logger.info("Collection InteliaKnowledge trouvée - utilisation des données existantes")
                except Exception as e:
                    logger.warning(f"Collection InteliaKnowledge non accessible (v4): {e}")
            else:
                # Version 3.x - vérifier avec schema
                try:
                    schema = self.weaviate_client.schema.get()
                    classes = [cls['class'] for cls in schema.get('classes', [])]
                    if "InteliaKnowledge" in classes:
                        logger.info("Collection InteliaKnowledge trouvée (v3) - utilisation des données existantes")
                    else:
                        logger.warning("Collection InteliaKnowledge non trouvée dans le schéma v3")
                except Exception as e:
                    logger.warning(f"Erreur accès schéma v3: {e}")
        
            # Créer le vector store avec la classe appropriée
            if WEAVIATE_V4:
                self.vector_store = WeaviateVectorStore(
                    weaviate_client=self.weaviate_client,
                    index_name="InteliaKnowledge"  # v4 utilise index_name
                )
            else:
                self.vector_store = WeaviateVectorStore(
                    weaviate_client=self.weaviate_client,
                    class_name="InteliaKnowledge"  # v3 utilise class_name
                )
        
        except Exception as e:
            logger.error(f"Erreur création vector store: {e}")
            # Créer un vector store par défaut
            try:
                if WEAVIATE_V4:
                    self.vector_store = WeaviateVectorStore(
                        weaviate_client=self.weaviate_client,
                        index_name="InteliaKnowledge"
                    )
                else:
                    self.vector_store = WeaviateVectorStore(
                        weaviate_client=self.weaviate_client,
                        class_name="InteliaKnowledge"
                    )
            except Exception as e2:
                logger.error(f"Impossible de créer vector store: {e2}")
                self.query_engine = None
                return

        # Index avec recherche hybride activée
        try:
            self.index = VectorStoreIndex.from_vector_store(
                self.vector_store,
                show_progress=False
            )

            # Retriever personnalisé avec reranking amélioré
            try:
                base_retriever = VectorIndexRetriever(
                    index=self.index,
                    similarity_top_k=RAG_SIMILARITY_TOP_K
                )
                
                # Wrapper avec votre logique métier améliorée
                enhanced_retriever = PoultryFilteredRetriever(
                    base_retriever=base_retriever,
                    intent_processor=self.intent_processor,
                    reranker=self.reranker
                )
                
                # Post-processor adaptatif
                postprocessor = SimilarityPostprocessor(
                    similarity_cutoff=RAG_CONFIDENCE_THRESHOLD
                )
                
                # Response synthesizer avec prompts améliorés
                synthesizer = get_response_synthesizer(
                    response_mode="compact",
                    use_async=True,
                    streaming=False
                )
                
                # Query engine final amélioré
                self.query_engine = RetrieverQueryEngine(
                    retriever=enhanced_retriever,
                    response_synthesizer=synthesizer,
                    node_postprocessors=[postprocessor]
                )
                
                logger.info("Query engine amélioré construit avec intelligence métier")
                
            except Exception as e:
                logger.error(f"Erreur construction retriever/query engine: {e}")
                self.query_engine = None
            
        except Exception as e:
            logger.error(f"Erreur construction index: {e}")
            self.query_engine = None
    
    async def process_query(self, query: str, language: str = "fr", tenant_id: str = "") -> RAGResult:
        """Interface compatible avec votre système actuel - version robuste"""
        
        if not RAG_ENABLED:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "rag_disabled"})
        
        # Mode dégradé si pas initialisé
        if not self.is_initialized:
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Erreur initialisation tardive: {e}")
                return RAGResult(source=RAGSource.ERROR, metadata={"error": str(e)})
        
        # Si pas de query engine (Weaviate indisponible), fallback
        if not self.query_engine or self.degraded_mode:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED,
                metadata={"reason": "weaviate_unavailable", "degraded_mode": self.degraded_mode}
            )
        
        start_time = time.time()
        
        try:
            # Récupération du contexte conversationnel
            conversation_context = ""
            if tenant_id and self.conversation_memory:
                try:
                    conversation_context = await self.conversation_memory.get_contextual_memory(tenant_id, query)
                except Exception as e:
                    logger.warning(f"Erreur mémoire conversationnelle: {e}")
            
            # Classification améliorée avec votre intelligence métier
            intent_result = None
            if self.intent_processor:
                try:
                    intent_result = self.intent_processor.process_query(query)
                except Exception as e:
                    logger.warning(f"Erreur intent processor: {e}")
            
            # Détection hors-domaine améliorée
            if self.ood_detector:
                try:
                    is_in_domain, domain_score, score_details = self.ood_detector.calculate_ood_score(query)
                    
                    if not is_in_domain:
                        return RAGResult(
                            source=RAGSource.OOD_FILTERED,
                            confidence=1.0 - domain_score,
                            processing_time=time.time() - start_time,
                            metadata={
                                "classification_method": "enhanced_ood_detector",
                                "domain_score": domain_score,
                                "score_details": score_details,
                                "intent_type": intent_result.intent_type.value if intent_result and hasattr(intent_result, 'intent_type') else "unknown"
                            },
                            intent_result=intent_result
                        )
                except Exception as e:
                    logger.warning(f"Erreur OOD detector: {e}")
            
            # Construction de la requête enrichie
            search_query = query
            if intent_result and hasattr(intent_result, 'expanded_query') and intent_result.expanded_query:
                search_query = intent_result.expanded_query
            
            # Ajout du contexte conversationnel si pertinent
            if conversation_context:
                search_query = f"Contexte: {conversation_context}\n\nQuestion: {search_query}"
            
            # Requête LlamaIndex avec votre contexte métier
            try:
                response = await self.query_engine.aquery(search_query)
            except Exception as e:
                logger.error(f"Erreur query engine: {e}")
                return RAGResult(
                    source=RAGSource.ERROR,
                    confidence=0.0,
                    processing_time=time.time() - start_time,
                    metadata={"error": str(e)},
                    intent_result=intent_result
                )
            
            if not response or not response.response:
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    confidence=0.0,
                    processing_time=time.time() - start_time,
                    intent_result=intent_result,
                    metadata={"reason": "empty_response"}
                )
            
            # Calcul de confiance amélioré
            confidence = self._calculate_enhanced_confidence(response, intent_result)
            
            # Construction des context docs
            context_docs = []
            if hasattr(response, 'source_nodes') and response.source_nodes:
                for node in response.source_nodes:
                    try:
                        score = float(node.score) if hasattr(node, 'score') and node.score is not None else 0.8
                    except (ValueError, TypeError):
                        score = 0.8
                    
                    metadata = getattr(node, 'metadata', {})
                    context_docs.append({
                        "title": metadata.get("title", ""),
                        "content": getattr(node, 'text', ''),
                        "score": score,
                        "source": metadata.get("source", ""),
                        "genetic_line": metadata.get("geneticLine", ""),
                        "species": metadata.get("species", ""),
                        "intent_type": metadata.get("intent_type", ""),
                        "detected_entities": metadata.get("detected_entities", {})
                    })
            
            # Vérification des réponses (Chain-of-Verification)
            verification_result = None
            if self.verifier and confidence > 0.7:
                try:
                    verification_result = await self.verifier.verify_response(
                        query, response.response, context_docs
                    )
                except Exception as e:
                    logger.warning(f"Erreur vérification: {e}")
            
            # Ajustement de la source selon la vérification
            result_source = RAGSource.RAG_KNOWLEDGE
            if verification_result and verification_result.get("verified", True):
                result_source = RAGSource.RAG_VERIFIED
                confidence = min(confidence * 1.1, 0.95)  # Boost pour réponse vérifiée
            
            # Construction des métadonnées enrichies
            metadata = {
                "llama_index_available": LLAMAINDEX_AVAILABLE,
                "weaviate_version": weaviate_version if WEAVIATE_AVAILABLE else "N/A",
                "weaviate_v4": WEAVIATE_V4,
                "degraded_mode": self.degraded_mode,
                "query_expanded": search_query != query,
                "conversation_context_used": bool(conversation_context),
                "nodes_used": len(response.source_nodes) if hasattr(response, 'source_nodes') else 0,
                "processing_time": time.time() - start_time,
                "reranking_applied": len(context_docs) > 1,
                "verification_enabled": RAG_VERIFICATION_ENABLED,
                "httpx_proxy_fix_applied": True  # ⬅️ Indicateur du fix
            }
            
            if intent_result:
                metadata.update({
                    "intent_type": intent_result.intent_type.value if hasattr(intent_result, 'intent_type') and hasattr(intent_result.intent_type, 'value') else str(getattr(intent_result, 'intent_type', 'unknown')),
                    "detected_entities": getattr(intent_result, 'detected_entities', {}),
                    "vocab_confidence": getattr(intent_result, 'metadata', {}).get("vocab_score", 0.0),
                    "query_expansion_applied": hasattr(intent_result, 'expanded_query') and intent_result.expanded_query != query
                })
            
            if self.ood_detector and 'score_details' in locals():
                metadata["domain_analysis"] = score_details
            
            # Sauvegarde dans la mémoire conversationnelle
            if tenant_id and self.conversation_memory:
                try:
                    self.conversation_memory.add_exchange(tenant_id, query, response.response)
                except Exception as e:
                    logger.warning(f"Erreur sauvegarde mémoire: {e}")
            
            return RAGResult(
                source=result_source,
                answer=response.response,
                confidence=confidence,
                context_docs=context_docs,
                processing_time=time.time() - start_time,
                metadata=metadata,
                verification_status=verification_result,
                intent_result=intent_result
            )
            
        except Exception as e:
            logger.error(f"Erreur traitement query amélioré: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                confidence=0.0,
                processing_time=time.time() - start_time,
                metadata={"error": str(e), "degraded_mode": self.degraded_mode},
                intent_result=intent_result if 'intent_result' in locals() else None
            )
    
    def _calculate_enhanced_confidence(self, response, intent_result) -> float:
        """Calcul de confiance amélioré avec facteurs multiples - version robuste"""
        try:
            if not hasattr(response, 'source_nodes') or not response.source_nodes:
                return 0.0
            
            scores = []
            for node in response.source_nodes:
                try:
                    if hasattr(node, 'score') and node.score is not None:
                        scores.append(float(node.score))
                except (ValueError, TypeError):
                    continue
            
            if not scores:
                return 0.5  # Confiance par défaut
            
            # Score de base: moyenne pondérée
            avg_score = sum(scores) / len(scores)
            
            # Facteur de cohérence: plus de documents = plus de confiance
            coherence_factor = min(1.2, 1 + (len(scores) - 1) * 0.05)
            
            # Facteur d'intention: bonus si l'intention est bien détectée
            intent_factor = 1.0
            if intent_result and hasattr(intent_result, 'confidence') and intent_result.confidence > 0.8:
                intent_factor = 1.1
            
            # Facteur de distribution des scores: pénaliser si trop dispersé
            if len(scores) > 1:
                score_std = np.std(scores)
                distribution_factor = max(0.9, 1 - score_std * 0.5)
            else:
                distribution_factor = 1.0
            
            # Calcul final
            final_confidence = avg_score * coherence_factor * intent_factor * distribution_factor
            
            return min(0.95, max(0.1, final_confidence))
            
        except Exception as e:
            logger.error(f"Erreur calcul confiance: {e}")
            return 0.5
    
    def get_status(self) -> Dict:
        """Status amélioré avec diagnostics détaillés - version robuste"""
        try:
            weaviate_connected = (
                self.weaviate_client is not None and 
                (self.weaviate_client.is_ready() if hasattr(self.weaviate_client, 'is_ready') else True)
            )
            
            return {
                "rag_enabled": RAG_ENABLED,
                "initialized": self.is_initialized,
                "degraded_mode": self.degraded_mode,
                "weaviate_available": WEAVIATE_AVAILABLE,
                "weaviate_version": weaviate_version if WEAVIATE_AVAILABLE else "N/A",
                "weaviate_v4": WEAVIATE_V4,
                "llamaindex_available": LLAMAINDEX_AVAILABLE,
                "llamaindex_llm_available": LLAMAINDEX_LLM_AVAILABLE,
                "llamaindex_embeddings_available": LLAMAINDEX_EMBEDDINGS_AVAILABLE,
                "llamaindex_weaviate_available": LLAMAINDEX_WEAVIATE_AVAILABLE,
                "weaviate_connected": weaviate_connected,
                "intent_processor_available": INTENT_PROCESSOR_AVAILABLE,
                "intent_processor_loaded": self.intent_processor is not None,
                "ood_detector_loaded": self.ood_detector is not None,
                "reranker_available": self.reranker is not None,
                "voyage_reranking": VOYAGE_AVAILABLE and VOYAGE_API_KEY is not None,
                "verification_enabled": RAG_VERIFICATION_ENABLED,
                "conversation_memory_active": self.conversation_memory is not None,
                "query_engine_ready": self.query_engine is not None,
                "confidence_threshold": RAG_CONFIDENCE_THRESHOLD,
                "similarity_top_k": RAG_SIMILARITY_TOP_K,
                "rerank_top_k": RAG_RERANK_TOP_K,
                "hybrid_alpha": RAG_HYBRID_ALPHA,
                "graceful_fallback_available": True,
                "httpx_proxy_fix_applied": True,  # ⬅️ Indicateur du fix
                "features": [
                    "enhanced_ood_detection",
                    "multi_stage_reranking", 
                    "voyage_ai_integration",
                    "chain_of_verification",
                    "enhanced_conversation_memory",
                    "intent_based_boosting",
                    "adaptive_confidence_scoring",
                    "diversity_filtering",
                    "contextual_query_expansion",
                    "real_time_verification",
                    "weaviate_version_compatibility",
                    "robust_error_handling",
                    "graceful_degradation",
                    "httpx_proxy_crash_protection"  # ⬅️ Nouvelle feature
                ]
            }
        except Exception as e:
            logger.error(f"Erreur get_status: {e}")
            return {
                "error": str(e),
                "rag_enabled": RAG_ENABLED,
                "initialized": False,
                "degraded_mode": True
            }
    
    async def cleanup(self):
        """Nettoyage des ressources amélioré - version robuste"""
        try:
            if self.weaviate_client:
                try:
                    if hasattr(self.weaviate_client, 'close'):
                        self.weaviate_client.close()
                except Exception as e:
                    logger.warning(f"Erreur fermeture Weaviate: {e}")
            
            if self.conversation_memory:
                try:
                    self.conversation_memory.memory_store.clear()
                except Exception as e:
                    logger.warning(f"Erreur nettoyage mémoire: {e}")
            
            # Fermer le client httpx si nécessaire
            try:
                if hasattr(self.openai_client, 'http_client') and hasattr(self.openai_client.http_client, 'close'):
                    await self.openai_client.http_client.aclose()
            except Exception as e:
                logger.warning(f"Erreur fermeture httpx client: {e}")
            
            logger.info("RAG Engine Enhanced nettoyé")
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")


# Fonctions utilitaires pour compatibilité avec votre système (préservées)
async def create_rag_engine(openai_client: OpenAI = None) -> InteliaRAGEngine:
    """Factory pour créer le RAG engine amélioré - version robuste"""
    try:
        engine = InteliaRAGEngine(openai_client)
        await engine.initialize()
        return engine
    except Exception as e:
        logger.error(f"Erreur création RAG engine: {e}")
        # Retourner un engine en mode dégradé
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
    """Interface compatible avec votre système actuel - version robuste"""
    try:
        return await rag_engine.process_query(question, language, tenant_id)
    except Exception as e:
        logger.error(f"Erreur process_question_with_rag: {e}")
        return RAGResult(
            source=RAGSource.ERROR,
            confidence=0.0,
            metadata={"error": str(e)}
        )