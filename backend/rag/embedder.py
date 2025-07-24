"""
RAG Embedder Complet - Version Finale Robuste
Corrige tous les problèmes de recherche et ajoute debug détaillé
"""

import os
import time
import logging
import pickle
import traceback
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Vérification des dépendances avec fallback gracieux
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    logger.info("✅ sentence-transformers available")
except ImportError as e:
    logger.warning(f"⚠️ sentence-transformers not available: {e}")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

try:
    import faiss
    FAISS_AVAILABLE = True
    logger.info("✅ faiss available")
except ImportError as e:
    logger.warning(f"⚠️ faiss not available: {e}")
    FAISS_AVAILABLE = False
    faiss = None

try:
    import numpy as np
    NUMPY_AVAILABLE = True
    logger.info("✅ numpy available")
except ImportError as e:
    logger.warning(f"⚠️ numpy not available: {e}")
    NUMPY_AVAILABLE = False
    np = None

class FastRAGEmbedder:
    """Version finale robuste du RAG Embedder avec debug complet"""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Constructeur avec vérifications complètes
        
        Args:
            api_key: Clé API (pour compatibilité)
            **kwargs: Autres paramètres
        """
        logger.info("🚀 Initializing FastRAGEmbedder...")
        
        # Configuration avec variables d'environnement
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        # Configuration modèle avec auto-détection
        model_name = os.getenv('RAG_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        self.model_name = model_name
        
        # Auto-détection dimension selon le modèle
        if 'text-embedding-3-small' in model_name:
            self.dimension = 1536
        elif 'text-embedding-ada-002' in model_name:
            self.dimension = 1536
        elif 'all-MiniLM-L6-v2' in model_name:
            self.dimension = 384
        elif 'all-mpnet-base-v2' in model_name:
            self.dimension = 768
        else:
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
        self.debug_enabled = os.getenv('RAG_DEBUG_SEARCH', 'false').lower() == 'true'
        
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
        logger.info(f"   Debug enabled: {self.debug_enabled}")
        
        if not self.dependencies_available:
            logger.warning("⚠️ Some dependencies missing - limited functionality")
    
    @property
    def sentence_model(self):
        """Lazy loading du modèle sentence-transformers avec vérifications complètes"""
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
                
                # Vérification dimension avec test embedding
                try:
                    test_embedding = self._sentence_model.encode(["test"])
                    actual_dim = test_embedding.shape[1]
                    
                    if actual_dim != self.dimension:
                        logger.warning(f"⚠️ Dimension mismatch: expected {self.dimension}, got {actual_dim}")
                        logger.info("🔄 Auto-correcting dimension...")
                        self.dimension = actual_dim
                        logger.info(f"✅ Dimension corrected to: {self.dimension}")
                        
                except Exception as dim_error:
                    logger.error(f"❌ Error checking dimension: {dim_error}")
                    
            except Exception as e:
                logger.error(f"❌ Error loading model: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
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
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None
        
        return self._faiss_index
    
    def load_index(self, index_path: str) -> bool:
        """Charger un index FAISS existant avec vérifications complètes"""
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
            
            # Vérifier et corriger dimension si nécessaire
            if self._faiss_index.d != self.dimension:
                logger.warning(f"⚠️ Index dimension {self._faiss_index.d} != expected {self.dimension}")
                logger.info("🔄 Auto-correcting dimension to match index...")
                self.dimension = self._faiss_index.d
                logger.info(f"✅ Dimension corrected to: {self.dimension}")
            
            # Charger les documents
            logger.info(f"🔄 Loading documents from {pkl_file}")
            with open(pkl_file, 'rb') as f:
                self._documents = pickle.load(f)
            
            # Vérifications post-chargement
            vectors_count = self._faiss_index.ntotal
            docs_count = len(self._documents)
            
            logger.info(f"✅ Index loaded successfully:")
            logger.info(f"   📊 {vectors_count} vectors")
            logger.info(f"   📚 {docs_count} documents")
            logger.info(f"   🔢 Dimension: {self._faiss_index.d}")
            
            # Vérifier cohérence
            if vectors_count == 0:
                logger.warning("⚠️ Index has 0 vectors!")
                return False
            
            if docs_count == 0:
                logger.warning("⚠️ No documents loaded!")
                return False
            
            # Test de recherche basique
            try:
                test_vector = np.random.random((1, self.dimension)).astype('float32')
                test_scores, test_indices = self._faiss_index.search(test_vector, 1)
                logger.info(f"✅ Index search test passed: found {len(test_indices[0])} results")
            except Exception as test_error:
                logger.error(f"❌ Index search test failed: {test_error}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading index from {index_path}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def has_search_engine(self) -> bool:
        """Vérifier si le moteur de recherche est disponible"""
        has_deps = self.dependencies_available
        has_index = self._faiss_index is not None
        has_vectors = has_index and self._faiss_index.ntotal > 0
        has_docs = len(self._documents) > 0
        
        if self.debug_enabled:
            logger.info(f"🔍 DEBUG: Search engine check:")
            logger.info(f"   Dependencies: {has_deps}")
            logger.info(f"   Index: {has_index}")
            logger.info(f"   Vectors: {has_vectors}")
            logger.info(f"   Documents: {has_docs}")
        
        return has_deps and has_index and has_vectors and has_docs
    
    @property
    def search_engine(self) -> bool:
        """Propriété pour compatibilité avec l'ancien code"""
        return self.has_search_engine()
    
    def embed_text(self, text: str):
        """Embedding avec gestion d'erreurs complète"""
        if self.debug_enabled:
            logger.info(f"🔍 DEBUG: Embedding text: '{text[:50]}...'")
            
        if not NUMPY_AVAILABLE:
            logger.error("❌ numpy not available for embedding")
            return None
            
        if not text.strip():
            logger.warning("⚠️ Empty text, returning zero vector")
            return np.zeros(self.dimension)
        
        model = self.sentence_model
        if model is None:
            logger.error("❌ Sentence model not available")
            return None
            
        try:
            # Cache check si activé
            if self.cache_enabled:
                text_hash = hash(text)
                if text_hash in self._embeddings_cache:
                    if self.debug_enabled:
                        logger.info("🔍 DEBUG: Using cached embedding")
                    return self._embeddings_cache[text_hash]
            
            # Generate embedding
            if self.debug_enabled:
                logger.info("🔍 DEBUG: Generating new embedding...")
                
            embedding = model.encode([text])[0]
            
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Generated embedding shape: {embedding.shape}")
            
            # Cache result si activé
            if self.cache_enabled and len(self._embeddings_cache) < self.cache_size:
                self._embeddings_cache[text_hash] = embedding
                if self.debug_enabled:
                    logger.info("🔍 DEBUG: Embedding cached")
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Error embedding text: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Recherche robuste avec debug complet"""
        if self.debug_enabled:
            logger.info(f"🔍 DEBUG: Starting search for query: '{query}' with k={k}")
        
        if not query.strip():
            if self.debug_enabled:
                logger.info("🔍 DEBUG: Empty query, returning empty results")
            return []
        
        if not self.has_search_engine():
            logger.warning("❌ Search engine not available - no documents indexed")
            return []
        
        try:
            # Debug info about index
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Index has {self._faiss_index.ntotal} vectors and {len(self._documents)} documents")
            
            # Embed query
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Embedding query...")
                
            query_embedding = self.embed_text(query)
            if query_embedding is None:
                logger.error("❌ Failed to embed query")
                return []
                
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Query embedding shape: {query_embedding.shape}")
                
            # Préparer pour FAISS
            query_embedding = query_embedding.reshape(1, -1).astype('float32')
            
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Reshaped query embedding: {query_embedding.shape}")
            
            # Search FAISS
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Performing FAISS search...")
                
            scores, indices = self._faiss_index.search(query_embedding, k)
            
            # Debug FAISS results
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: FAISS returned {len(scores[0])} results")
                logger.info(f"🔍 DEBUG: Raw scores: {scores[0].tolist()}")
                logger.info(f"🔍 DEBUG: Raw indices: {indices[0].tolist()}")
            
            # Traiter les résultats
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if self.debug_enabled:
                    logger.info(f"🔍 DEBUG: Processing result {i}: score={score}, idx={idx}")
                
                # Vérifier validité de l'index
                if idx < 0:
                    if self.debug_enabled:
                        logger.warning(f"🔍 DEBUG: Skipping invalid index {idx} (negative)")
                    continue
                    
                if idx >= len(self._documents):
                    if self.debug_enabled:
                        logger.warning(f"🔍 DEBUG: Skipping invalid index {idx} (>= {len(self._documents)})")
                    continue
                
                # Récupérer le document
                try:
                    doc_text = self._documents[idx]
                    
                    if self.debug_enabled:
                        logger.info(f"🔍 DEBUG: Valid result {i}: idx={idx}, score={score}")
                        logger.info(f"🔍 DEBUG: Document preview: '{doc_text[:100]}...'")
                    
                    results.append({
                        'text': doc_text,
                        'score': float(score),
                        'rank': i + 1,
                        'index': int(idx)
                    })
                    
                except Exception as doc_error:
                    logger.error(f"❌ Error accessing document {idx}: {doc_error}")
                    continue
            
            # Log résultats finaux
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Final results count: {len(results)}")
                for i, result in enumerate(results[:3]):  # Log premiers résultats
                    logger.info(f"🔍 DEBUG: Result {i}: score={result['score']:.4f}, text='{result['text'][:80]}...'")
            
            if len(results) == 0:
                logger.warning("⚠️ No valid results found after filtering")
            else:
                logger.info(f"✅ Found {len(results)} valid results")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during search: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiques complètes du système"""
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
            'cache_enabled': self.cache_enabled,
            'debug_enabled': self.debug_enabled
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