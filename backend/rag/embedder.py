"""
RAG Embedder Corrigé - Version Sécurisée
Fix des problèmes de dimension et dépendances
"""

import os
import time
import logging
import pickle
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Vérification des dépendances avec fallback gracieux
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ sentence-transformers not available")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ faiss not available")
    FAISS_AVAILABLE = False
    faiss = None

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ numpy not available")
    NUMPY_AVAILABLE = False
    np = None

class FastRAGEmbedder:
    """Version sécurisée du RAG Embedder avec vérifications"""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Constructeur avec vérifications de sécurité
        """
        # Configuration avec variables d'environnement
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        # CORRECTION: Mapping correct modèle → dimension
        model_name = os.getenv('RAG_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        self.model_name = model_name
        
        # Auto-détection dimension selon le modèle
        if 'text-embedding-3-small' in model_name:
            self.dimension = 1536
        elif 'text-embedding-ada-002' in model_name:
            self.dimension = 1536
        elif 'all-MiniLM-L6-v2' in model_name:
            self.dimension = 384
        else:
            # Fallback sur variable d'environnement
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
        
        # Vérification disponibilité
        self.dependencies_available = (
            SENTENCE_TRANSFORMERS_AVAILABLE and 
            FAISS_AVAILABLE and 
            NUMPY_AVAILABLE
        )
        
        logger.info("✅ FastRAGEmbedder initialized with compatible signature")
        logger.info(f"   Model: {self.model_name}")
        logger.info(f"   Dimension: {self.dimension}")
        logger.info(f"   Dependencies available: {self.dependencies_available}")
        logger.info(f"   Lazy loading: {self.lazy_loading}")
        logger.info(f"   Cache enabled: {self.cache_enabled}")
        
        if not self.dependencies_available:
            logger.warning("⚠️ Some dependencies missing - limited functionality")
    
    @property
    def sentence_model(self):
        """Lazy loading du modèle sentence-transformers avec vérifications"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error("❌ sentence-transformers not available")
            return None
            
        if self._sentence_model is None:
            try:
                start_time = time.time()
                logger.info(f"🔄 Loading sentence model: {self.model_name}")
                
                self._sentence_model = SentenceTransformer(self.model_name)
                
                load_time = time.time() - start_time
                logger.info(f"✅ Model loaded in {load_time:.2f}s")
                
                # Vérification dimension
                test_embedding = self._sentence_model.encode(["test"])
                actual_dim = test_embedding.shape[1]
                
                if actual_dim != self.dimension:
                    logger.warning(f"⚠️ Dimension mismatch: expected {self.dimension}, got {actual_dim}")
                    self.dimension = actual_dim  # Correction automatique
                    
            except Exception as e:
                logger.error(f"❌ Error loading model: {e}")
                return None
        
        return self._sentence_model
    
    @property
    def faiss_index(self):
        """Lazy loading de l'index FAISS avec vérifications"""
        if not FAISS_AVAILABLE:
            logger.error("❌ faiss not available")
            return None
            
        if self._faiss_index is None:
            try:
                logger.info(f"🔄 Creating FAISS index (dimension: {self.dimension})")
                
                # Index simple pour performance
                self._faiss_index = faiss.IndexFlatL2(self.dimension)
                
                logger.info("✅ FAISS index created")
                
            except Exception as e:
                logger.error(f"❌ Error creating FAISS index: {e}")
                return None
        
        return self._faiss_index
    
    def load_index(self, index_path: str) -> bool:
        """Charger un index FAISS existant avec vérifications"""
        if not self.dependencies_available:
            logger.error("❌ Dependencies not available for index loading")
            return False
            
        try:
            faiss_file = os.path.join(index_path, 'index.faiss')
            pkl_file = os.path.join(index_path, 'index.pkl')
            
            if not os.path.exists(faiss_file) or not os.path.exists(pkl_file):
                logger.warning(f"❌ Index files missing in {index_path}")
                return False
            
            # Charger l'index FAISS
            logger.info(f"🔄 Loading FAISS index from {faiss_file}")
            self._faiss_index = faiss.read_index(faiss_file)
            
            # Vérifier dimension
            if self._faiss_index.d != self.dimension:
                logger.warning(f"⚠️ Index dimension {self._faiss_index.d} != expected {self.dimension}")
                self.dimension = self._faiss_index.d  # Correction automatique
            
            # Charger les documents
            logger.info(f"🔄 Loading documents from {pkl_file}")
            with open(pkl_file, 'rb') as f:
                self._documents = pickle.load(f)
            
            logger.info(f"✅ Index loaded successfully:")
            logger.info(f"   📊 {self._faiss_index.ntotal} vectors")
            logger.info(f"   📚 {len(self._documents)} documents")
            logger.info(f"   🔢 Dimension: {self._faiss_index.d}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading index from {index_path}: {e}")
            return False
    
    def has_search_engine(self) -> bool:
        """Vérifier si le moteur de recherche est disponible"""
        return (self.dependencies_available and
                self._faiss_index is not None and 
                self._faiss_index.ntotal > 0 and 
                len(self._documents) > 0)
    
    @property
    def search_engine(self) -> bool:
        """Propriété pour compatibilité avec l'ancien code"""
        return self.has_search_engine()
    
    def embed_text(self, text: str):
        """Embedding avec gestion d'erreurs"""
        if not NUMPY_AVAILABLE:
            return None
            
        if not text.strip():
            return np.zeros(self.dimension)
        
        model = self.sentence_model
        if model is None:
            return None
            
        try:
            # Cache check si activé
            if self.cache_enabled:
                text_hash = hash(text)
                if text_hash in self._embeddings_cache:
                    return self._embeddings_cache[text_hash]
            
            # Generate embedding
            embedding = model.encode([text])[0]
            
            # Cache result si activé
            if self.cache_enabled and len(self._embeddings_cache) < self.cache_size:
                self._embeddings_cache[text_hash] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Error embedding text: {e}")
            return None
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Recherche avec gestion d'erreurs"""
        if not query.strip():
            return []
        
        if not self.has_search_engine():
            logger.warning("❌ Search engine not available - no documents indexed")
            return []
        
        try:
            # Embed query
            query_embedding = self.embed_text(query)
            if query_embedding is None:
                return []
                
            query_embedding = query_embedding.reshape(1, -1).astype('float32')
            
            # Search FAISS
            scores, indices = self._faiss_index.search(query_embedding, k)
            
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
            
        except Exception as e:
            logger.error(f"❌ Error during search: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiques du système avec état des dépendances"""
        return {
            'model_name': self.model_name,
            'dimension': self.dimension,
            'documents_count': len(self._documents),
            'cache_size': len(self._embeddings_cache),
            'index_size': self._faiss_index.ntotal if self._faiss_index else 0,
            'model_loaded': self._sentence_model is not None,
            'index_created': self._faiss_index is not None,
            'search_engine_available': self.has_search_engine(),
            'dependencies_available': self.dependencies_available,
            'sentence_transformers': SENTENCE_TRANSFORMERS_AVAILABLE,
            'faiss': FAISS_AVAILABLE,
            'numpy': NUMPY_AVAILABLE,
            'lazy_loading': self.lazy_loading,
            'cache_enabled': self.cache_enabled
        }

# Alias pour compatibilité
class EnhancedDocumentEmbedder(FastRAGEmbedder):
    """Wrapper pour compatibilité avec l'ancien nom"""
    pass

class RAGEmbedder(FastRAGEmbedder):
    """Wrapper pour compatibilité avec RAGEmbedder"""
    pass

# Instance globale
_global_embedder: Optional[FastRAGEmbedder] = None

def get_embedder() -> FastRAGEmbedder:
    """Singleton pattern pour l'embedder"""
    global _global_embedder
    if _global_embedder is None:
        _global_embedder = FastRAGEmbedder()
    return _global_embedder