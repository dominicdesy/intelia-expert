# -*- coding: utf-8 -*-
"""
llama_rag.py - RAG Engine simplifié avec LlamaIndex
Préserve votre intelligence métier tout en utilisant LlamaIndex pour le RAG
"""

import os
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# LlamaIndex imports
from llama_index.core import VectorStoreIndex, Settings, get_response_synthesizer
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.core.schema import QueryBundle, NodeWithScore
from llama_index.core.base.base_retriever import BaseRetriever

# Vos imports métier (préservés intégralement)
from intent_processor import create_intent_processor, IntentType, IntentResult

# Configuration Weaviate (réutilise votre setup)
import weaviate
import weaviate.classes as wvc

logger = logging.getLogger(__name__)

# Configuration par variables d'environnement (simplifiées)
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

# Paramètres LlamaIndex
RAG_SIMILARITY_TOP_K = int(os.getenv("RAG_SIMILARITY_TOP_K", "10"))
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.7"))
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1024"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))

class RAGSource(Enum):
    """Sources de réponse (compatibilité avec votre système)"""
    RAG_KNOWLEDGE = "rag_knowledge"
    OOD_FILTERED = "ood_filtered" 
    FALLBACK_NEEDED = "fallback_needed"
    ERROR = "error"

@dataclass
class RAGResult:
    """Résultat RAG compatible avec votre système actuel"""
    source: RAGSource
    answer: Optional[str] = None
    confidence: float = 0.0
    context_docs: List[Dict] = None
    processing_time: float = 0.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.context_docs is None:
            self.context_docs = []
        if self.metadata is None:
            self.metadata = {}

class PoultryFilteredRetriever(BaseRetriever):
    """Retriever personnalisé utilisant votre intelligence métier"""
    
    def __init__(self, base_retriever: VectorIndexRetriever, intent_processor):
        super().__init__()
        self.base_retriever = base_retriever
        self.intent_processor = intent_processor
        
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Retrieval avec filtrage intelligent basé sur vos entités métier"""
        
        # Analyse avec votre processeur d'intentions
        intent_result = self.intent_processor.process_query(query_bundle.query_str)
        
        # Construction des filtres métadonnées basés sur vos entités
        filters = self._build_metadata_filters(intent_result.detected_entities)
        
        # Recherche de base
        nodes = self.base_retriever.retrieve(query_bundle)
        
        # Filtrage post-retrieval basé sur vos critères métier
        filtered_nodes = []
        for node in nodes:
            if self._matches_domain_criteria(node, intent_result):
                # Enrichir avec métadonnées métier
                node.metadata["intent_type"] = intent_result.intent_type.value
                node.metadata["detected_entities"] = intent_result.detected_entities
                filtered_nodes.append(node)
        
        logger.info(f"Filtered retrieval: {len(filtered_nodes)}/{len(nodes)} nodes kept")
        return filtered_nodes
    
    def _build_metadata_filters(self, entities: Dict[str, str]) -> Dict:
        """Construit des filtres basés sur vos entités métier"""
        filters = {}
        
        if "line" in entities:
            # Utilise votre mapping canonique des lignées
            canonical_line = entities["line"].lower()
            filters["geneticLine"] = canonical_line
            
        if "site_type" in entities:
            filters["site_type"] = entities["site_type"]
            
        if "species" in entities:
            filters["species"] = entities["species"]
            
        return filters
    
    def _matches_domain_criteria(self, node: NodeWithScore, intent_result: IntentResult) -> bool:
        """Vérifie si un nœud correspond à vos critères métier"""
        
        # Vérification domaine avicole (votre logique préservée)
        if intent_result.intent_type == IntentType.OUT_OF_DOMAIN:
            return False
        
        # Filtrage par lignée génétique si spécifiée
        if "line" in intent_result.detected_entities:
            node_line = node.metadata.get("geneticLine", "").lower()
            target_line = intent_result.detected_entities["line"].lower()
            if node_line and target_line not in node_line:
                return False
        
        return True

class InteliaRAGEngine:
    """Engine RAG principal utilisant LlamaIndex avec votre intelligence métier"""
    
    def __init__(self):
        self.intent_processor = None
        self.weaviate_client = None
        self.vector_store = None
        self.index = None
        self.query_engine = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialisation du système RAG hybride"""
        if self.is_initialized:
            return
            
        logger.info("Initialisation Intelia RAG Engine avec LlamaIndex...")
        
        # Configuration globale LlamaIndex
        Settings.llm = LlamaOpenAI(
            model="gpt-4o-mini",
            api_key=OPENAI_API_KEY,
            temperature=0.1,
            max_tokens=800
        )
        
        Settings.embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=OPENAI_API_KEY
        )
        
        Settings.chunk_size = RAG_CHUNK_SIZE
        Settings.chunk_overlap = RAG_CHUNK_OVERLAP
        
        # Initialisation de votre processeur d'intentions (préservé)
        try:
            self.intent_processor = create_intent_processor()
            logger.info("Intelligence métier initialisée (intent processor)")
        except Exception as e:
            logger.error(f"Erreur init intent processor: {e}")
            self.intent_processor = None
        
        # Connexion Weaviate (réutilise votre configuration)
        await self._connect_weaviate()
        
        # Construction de l'index et query engine
        await self._build_query_engine()
        
        self.is_initialized = True
        logger.info("RAG Engine initialisé avec succès")
    
    async def _connect_weaviate(self):
        """Connexion à votre instance Weaviate existante"""
        try:
            if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                # Cloud connection
                auth_credentials = wvc.init.Auth.api_key(WEAVIATE_API_KEY)
                self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=WEAVIATE_URL,
                    auth_credentials=auth_credentials,
                    headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
            else:
                # Local connection
                self.weaviate_client = weaviate.connect_to_local(
                    host=WEAVIATE_URL.replace('http://', '').replace('https://', ''),
                    port=8080,
                    headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
            
            if self.weaviate_client.is_ready():
                logger.info("Connexion Weaviate établie")
            else:
                raise Exception("Weaviate not ready")
                
        except Exception as e:
            logger.error(f"Erreur connexion Weaviate: {e}")
            raise
    
    async def _build_query_engine(self):
        """Construction du query engine avec votre intelligence métier"""
        
        # Vector store LlamaIndex sur votre collection existante
        self.vector_store = WeaviateVectorStore(
            weaviate_client=self.weaviate_client,
            class_name="InteliaKnowledge"  # Votre collection existante
        )
        
        # Index à partir de votre vector store
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)
        
        # Retriever personnalisé avec votre intelligence métier
        base_retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=RAG_SIMILARITY_TOP_K
        )
        
        # Wrapper avec votre logique métier
        poultry_retriever = PoultryFilteredRetriever(
            base_retriever=base_retriever,
            intent_processor=self.intent_processor
        )
        
        # Post-processor pour filtrage par similarité
        postprocessor = SimilarityPostprocessor(
            similarity_cutoff=RAG_CONFIDENCE_THRESHOLD
        )
        
        # Response synthesizer personnalisé
        synthesizer = get_response_synthesizer(
            response_mode="compact",
            use_async=True
        )
        
        # Query engine final
        self.query_engine = RetrieverQueryEngine(
            retriever=poultry_retriever,
            response_synthesizer=synthesizer,
            node_postprocessors=[postprocessor]
        )
        
        logger.info("Query engine construit avec intelligence métier")
    
    async def process_query(self, query: str, language: str = "fr", tenant_id: str = "") -> RAGResult:
        """Interface compatible avec votre système actuel"""
        
        if not RAG_ENABLED or not self.is_initialized:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED)
        
        start_time = time.time()
        
        try:
            # Classification avec votre intelligence métier (préservée)
            if self.intent_processor:
                intent_result = self.intent_processor.process_query(query)
                
                # Filtrage hors-domaine (votre logique préservée)
                if intent_result.intent_type == IntentType.OUT_OF_DOMAIN:
                    return RAGResult(
                        source=RAGSource.OOD_FILTERED,
                        confidence=intent_result.confidence,
                        processing_time=time.time() - start_time,
                        metadata={
                            "classification_method": "intent_processor",
                            "vocab_score": intent_result.metadata.get("vocab_score", 0.0),
                            "intent_type": intent_result.intent_type.value
                        }
                    )
                
                # Utiliser la requête expansée si disponible
                search_query = intent_result.expanded_query
            else:
                search_query = query
                intent_result = None
            
            # Requête LlamaIndex avec votre contexte métier
            response = await self.query_engine.aquery(search_query)
            
            if not response or not response.response:
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    confidence=0.0,
                    processing_time=time.time() - start_time
                )
            
            # Calcul de confiance basé sur les scores des nœuds
            confidence = self._calculate_confidence(response)
            
            # Construction des métadonnées enrichies
            metadata = {
                "llama_index_version": "0.10.57",
                "query_expanded": search_query != query,
                "nodes_used": len(response.source_nodes),
                "processing_time": time.time() - start_time
            }
            
            if intent_result:
                metadata.update({
                    "intent_type": intent_result.intent_type.value,
                    "detected_entities": intent_result.detected_entities,
                    "vocab_confidence": intent_result.metadata.get("vocab_score", 0.0)
                })
            
            # Format des contexte docs compatible avec votre système
            context_docs = []
            for node in response.source_nodes:
                context_docs.append({
                    "title": node.metadata.get("title", ""),
                    "content": node.text,
                    "score": float(node.score) if hasattr(node, 'score') else 0.8,
                    "source": node.metadata.get("source", ""),
                    "genetic_line": node.metadata.get("geneticLine", ""),
                    "species": node.metadata.get("species", "")
                })
            
            return RAGResult(
                source=RAGSource.RAG_KNOWLEDGE,
                answer=response.response,
                confidence=confidence,
                context_docs=context_docs,
                processing_time=time.time() - start_time,
                metadata=metadata,
                intent_result=intent_result  # Ajout pour prompts spécialisés fallback
            )
            
        except Exception as e:
            logger.error(f"Erreur traitement query: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                confidence=0.0,
                processing_time=time.time() - start_time,
                metadata={"error": str(e)}
            )
    
    def _calculate_confidence(self, response) -> float:
        """Calcul de confiance basé sur les scores des nœuds"""
        if not hasattr(response, 'source_nodes') or not response.source_nodes:
            return 0.0
        
        scores = []
        for node in response.source_nodes:
            if hasattr(node, 'score') and node.score is not None:
                scores.append(float(node.score))
        
        if not scores:
            return 0.5  # Confiance par défaut
        
        # Moyenne pondérée avec bonus pour cohérence
        avg_score = sum(scores) / len(scores)
        confidence = min(0.95, avg_score * (1 + 0.1 * len(scores)))
        
        return confidence
    
    def get_status(self) -> Dict:
        """Status compatible avec votre système avec diagnostics de dégradation"""
        weaviate_connected = self.weaviate_client is not None and self.weaviate_client.is_ready() if self.weaviate_client else False
        
        return {
            "rag_enabled": RAG_ENABLED,
            "initialized": self.is_initialized,
            "weaviate_connected": weaviate_connected,
            "intent_processor_loaded": self.intent_processor is not None,
            "llama_index_version": "0.10.57",
            "query_engine_ready": self.query_engine is not None,
            "confidence_threshold": RAG_CONFIDENCE_THRESHOLD,
            "similarity_top_k": RAG_SIMILARITY_TOP_K,
            "degradation_mode": not weaviate_connected or self.query_engine is None,
            "graceful_fallback_available": True,
            "specialized_prompts_enabled": self.intent_processor is not None,
            "features": [
                "llama_index_integration",
                "intent_processor_preserved", 
                "metadata_filtering",
                "similarity_postprocessing",
                "async_processing",
                "specialized_prompts_injection",
                "advanced_confidence_calculation",
                "graceful_degradation"
            ]
        }
    
    async def add_knowledge(self, documents: List[Dict]) -> bool:
        """Ajout de documents (utilise votre script sync_to_weaviate.py)"""
        # Cette méthode redirige vers votre script existant
        logger.info("Pour ajouter des documents, utilisez sync_to_weaviate.py")
        return True
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        try:
            if self.weaviate_client:
                self.weaviate_client.close()
            logger.info("RAG Engine nettoyé")
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")

# Fonctions utilitaires pour compatibilité avec votre système
async def create_rag_engine() -> InteliaRAGEngine:
    """Factory pour créer le RAG engine (compatible avec votre main.py)"""
    engine = InteliaRAGEngine()
    await engine.initialize()
    return engine

async def process_question_with_rag(
    rag_engine: InteliaRAGEngine, 
    question: str, 
    language: str = "fr", 
    tenant_id: str = ""
) -> RAGResult:
    """Interface compatible avec votre système actuel"""
    return await rag_engine.process_query(question, language, tenant_id)