"""
Fix pour la classe FastRAGEmbedder - Signature compatible
Remplacer dans backend/rag/embedder.py
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache

# Imports optimisés
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

logger = logging.getLogger(__name__)

class FastRAGEmbedder:
    """Version optimisée du RAG Embedder avec signature compatible"""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Constructeur compatible avec l'ancienne signature
        
        Args:
            api_key: Clé API (récupérée automatiquement depuis l'env si non fournie)
            **kwargs: Autres paramètres pour compatibilité
        """
        # Configuration avec variables d'environnement
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model_name = os.getenv('RAG_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        self.dimension = int(os.getenv('RAG_DIMENSION', '384'))
        self.cache_size = int(os.getenv('RAG_EMBEDDING_CACHE_SIZE', '1000'))
        
        # Lazy loading attributes
        self._sentence_model = None
        self._faiss_index = None
        self._documents = []
        self._embeddings_cache = {}
        
        # Configuration performance
        self.lazy_loading = os.getenv('RAG_LAZY_LOADING', 'true').lower() == 'true'
        self.cache_enabled = os.getenv('RAG_CACHE_EMBEDDINGS', 'true').lower() == 'true'
        self.memory_cache = os.getenv('RAG_MEMORY_CACHE', 'true').lower() == 'true'
        
        logger.info("✅ FastRAGEmbedder initialized with compatible signature")
        logger.info(f"   Model: {self.model_name}")
        logger.info(f"   Lazy loading: {self.lazy_loading}")
        logger.info(f"   Cache enabled: {self.cache_enabled}")
    
    @property
    def sentence_model(self) -> SentenceTransformer:
        """Lazy loading du modèle sentence-transformers"""
        if self._sentence_model is None:
            if not self.lazy_loading:
                start_time = time.time()
                logger.info(f"🔄 Loading sentence model: {self.model_name}")
                
                self._sentence_model = SentenceTransformer(self.model_name)
                
                load_time = time.time() - start_time
                logger.info(f"✅ Model loaded in {load_time:.2f}s")
            else:
                logger.info("⚡ Lazy loading enabled - model will load on first use")
                self._sentence_model = SentenceTransformer(self.model_name)
        
        return self._sentence_model
    
    @property
    def faiss_index(self) -> faiss.Index:
        """Lazy loading de l'index FAISS"""
        if self._faiss_index is None:
            logger.info(f"🔄 Creating FAISS index (dimension: {self.dimension})")
            
            # Index simple pour performance
            self._faiss_index = faiss.IndexFlatL2(self.dimension)
            
            logger.info("✅ FAISS index created")
        
        return self._faiss_index
    
    def embed_text(self, text: str) -> np.ndarray:
        """Embedding avec cache optionnel"""
        if not text.strip():
            return np.zeros(self.dimension)
        
        # Cache check si activé
        if self.cache_enabled:
            text_hash = hash(text)
            if text_hash in self._embeddings_cache:
                return self._embeddings_cache[text_hash]
        
        # Generate embedding
        embedding = self.sentence_model.encode([text])[0]
        
        # Cache result si activé
        if self.cache_enabled and len(self._embeddings_cache) < self.cache_size:
            self._embeddings_cache[text_hash] = embedding
        
        return embedding
    
    def add_documents(self, documents: List[str]) -> None:
        """Ajouter des documents à l'index"""
        if not documents:
            return
        
        logger.info(f"🔄 Adding {len(documents)} documents to index")
        start_time = time.time()
        
        # Générer embeddings en batch pour performance
        embeddings = self.sentence_model.encode(documents, show_progress_bar=True)
        
        # Ajouter à l'index FAISS
        self.faiss_index.add(embeddings.astype('float32'))
        
        # Stocker les documents
        self._documents.extend(documents)
        
        process_time = time.time() - start_time
        logger.info(f"✅ Documents added in {process_time:.2f}s")
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Recherche rapide dans l'index"""
        if not query.strip():
            return []
        
        # Embed query
        query_embedding = self.embed_text(query).reshape(1, -1).astype('float32')
        
        # Search FAISS
        scores, indices = self.faiss_index.search(query_embedding, k)
        
        # Format results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx >= 0 and idx < len(self._documents):
                results.append({
                    'text': self._documents[idx],
                    'score': float(score),
                    'rank': i + 1
                })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiques du système"""
        return {
            'model_name': self.model_name,
            'dimension': self.dimension,
            'documents_count': len(self._documents),
            'cache_size': len(self._embeddings_cache),
            'index_size': self.faiss_index.ntotal if self._faiss_index else 0,
            'model_loaded': self._sentence_model is not None,
            'index_created': self._faiss_index is not None,
            'lazy_loading': self.lazy_loading,
            'cache_enabled': self.cache_enabled
        }

# Alias pour compatibilité avec l'ancien code
class EnhancedDocumentEmbedder(FastRAGEmbedder):
    """Wrapper pour compatibilité avec l'ancien nom"""
    pass

# Alias pour compatibilité RAGEmbedder
class RAGEmbedder(FastRAGEmbedder):
    """Wrapper pour compatibilité avec RAGEmbedder"""
    pass

# Instance globale pour réutilisation
_global_embedder: Optional[FastRAGEmbedder] = None

def get_embedder() -> FastRAGEmbedder:
    """Singleton pattern pour l'embedder"""
    global _global_embedder
    if _global_embedder is None:
        _global_embedder = FastRAGEmbedder()
    return _global_embedder