"""
RAG Embedder Optimisé pour Performance
Version allégée pour développement et déploiement rapide
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache

# Imports optimisés - seulement ce qui est nécessaire
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

logger = logging.getLogger(__name__)

class FastRAGEmbedder:
    """Version optimisée du RAG Embedder avec lazy loading"""
    
    def __init__(self):
        self._sentence_model = None
        self._faiss_index = None
        self._documents = []
        self._embeddings_cache = {}
        
        # Configuration performance
        self.model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        self.dimension = 384  # Dimension du modèle MiniLM
        self.cache_size = int(os.getenv('EMBEDDING_CACHE_SIZE', '1000'))
        
        logger.info("✅ FastRAGEmbedder initialized (lazy loading)")
    
    @property
    def sentence_model(self) -> SentenceTransformer:
        """Lazy loading du modèle sentence-transformers"""
        if self._sentence_model is None:
            start_time = time.time()
            logger.info(f"🔄 Loading sentence model: {self.model_name}")
            
            self._sentence_model = SentenceTransformer(self.model_name)
            
            load_time = time.time() - start_time
            logger.info(f"✅ Model loaded in {load_time:.2f}s")
        
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
    
    @lru_cache(maxsize=1000)
    def embed_text(self, text: str) -> np.ndarray:
        """Embedding avec cache LRU"""
        if not text.strip():
            return np.zeros(self.dimension)
        
        # Cache hit check
        text_hash = hash(text)
        if text_hash in self._embeddings_cache:
            return self._embeddings_cache[text_hash]
        
        # Generate embedding
        embedding = self.sentence_model.encode([text])[0]
        
        # Cache result
        if len(self._embeddings_cache) < self.cache_size:
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
            'index_created': self._faiss_index is not None
        }

# Instance globale pour réutilisation
_global_embedder: Optional[FastRAGEmbedder] = None

def get_embedder() -> FastRAGEmbedder:
    """Singleton pattern pour l'embedder"""
    global _global_embedder
    if _global_embedder is None:
        _global_embedder = FastRAGEmbedder()
    return _global_embedder

# Compatibility avec l'ancien système
class EnhancedDocumentEmbedder(FastRAGEmbedder):
    """Wrapper pour compatibilité"""
    pass