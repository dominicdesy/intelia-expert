"""
RAG Embedder - OPTIMIZED VERSION
Performance improvements for faster responses
"""

import os
import time
import pickle
import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class FastRAGEmbedder:
    """
    Optimized RAG Embedder with performance improvements:
    - Reduced default k for faster search
    - Embedding caching
    - Optimized memory usage
    - Faster vector operations
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
        cache_embeddings: bool = True,
        max_workers: int = 2,
        debug: bool = True
    ):
        """
        Initialize FastRAGEmbedder with performance optimizations
        
        Args:
            api_key: OpenAI API key (optional for local embeddings)
            model_name: Sentence transformer model name
            cache_embeddings: Enable embedding caching for performance
            max_workers: Max concurrent workers (reduced for stability)
            debug: Enable debug logging
        """
        self.api_key = api_key
        self.model_name = model_name
        self.cache_embeddings = cache_embeddings
        self.max_workers = max_workers
        self.debug = debug
        
        # Performance optimization flags
        self.embedding_cache = {} if cache_embeddings else None
        self.documents = []
        self.embeddings = None
        self.index = None
        self.search_engine_available = False
        
        # Initialize components
        self._init_dependencies()
        
        if self.debug:
            logger.info("🚀 Initializing FastRAGEmbedder...")
            logger.info(f"   Model: {self.model_name}")
            logger.info(f"   Dimension: 384")  # MiniLM dimension
            logger.info(f"   Dependencies available: {self._check_dependencies()}")
            logger.info(f"   Cache enabled: {self.cache_embeddings}")
            logger.info(f"   Max workers: {self.max_workers}")
            logger.info(f"   Debug enabled: {self.debug}")
    
    def _init_dependencies(self):
        """Initialize required dependencies with error handling"""
        try:
            # Import sentence transformers
            from sentence_transformers import SentenceTransformer
            self.sentence_model = SentenceTransformer(self.model_name)
            logger.info("✅ sentence-transformers available")
            
            # Import FAISS
            import faiss
            self.faiss = faiss
            logger.info("✅ faiss available")
            
            # Import numpy
            import numpy as np
            self.np = np
            logger.info("✅ numpy available")
            
            self.dependencies_available = True
            
        except ImportError as e:
            logger.error(f"❌ Missing dependencies: {e}")
            self.dependencies_available = False
    
    def _check_dependencies(self) -> bool:
        """Check if all required dependencies are available"""
        return hasattr(self, 'sentence_model') and hasattr(self, 'faiss') and hasattr(self, 'np')
    
    def load_index(self, index_path: str) -> bool:
        """
        Load existing FAISS index and documents - OPTIMIZED
        
        Args:
            index_path: Path to the index directory
            
        Returns:
            bool: True if loaded successfully
        """
        if not self._check_dependencies():
            logger.error("❌ Dependencies not available for loading index")
            return False
        
        try:
            faiss_file = os.path.join(index_path, 'index.faiss')
            pkl_file = os.path.join(index_path, 'index.pkl')
            
            if not os.path.exists(faiss_file) or not os.path.exists(pkl_file):
                logger.error(f"❌ Index files not found in {index_path}")
                return False
            
            # Load FAISS index
            logger.info(f"🔄 Loading FAISS index from {faiss_file}")
            start_time = time.time()
            self.index = self.faiss.read_index(faiss_file)
            load_time = time.time() - start_time
            
            if self.debug:
                logger.info(f"✅ FAISS index loaded in {load_time:.2f}s")
            
            # Load documents
            logger.info(f"🔄 Loading documents from {pkl_file}")
            start_time = time.time()
            with open(pkl_file, 'rb') as f:
                raw_documents = pickle.load(f)
            
            # Normalize documents format - OPTIMIZED
            self.documents = self._normalize_documents_fast(raw_documents)
            doc_load_time = time.time() - start_time
            
            if self.debug:
                logger.info(f"✅ Documents loaded in {doc_load_time:.2f}s")
                logger.info(f"🔍 Total documents: {len(self.documents)}")
            
            self.search_engine_available = True
            logger.info("✅ Index loaded successfully - Search engine ready")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading index: {e}")
            return False
    
    def _normalize_documents_fast(self, raw_documents: Any) -> List[Dict[str, Any]]:
        """
        Fast document normalization - OPTIMIZED
        
        Args:
            raw_documents: Raw document data in various formats
            
        Returns:
            List of normalized document dictionaries
        """
        if self.debug:
            logger.info("🔍 DEBUG: Normalizing documents...")
            logger.info(f"   Raw type: {type(raw_documents)}")
            
        normalized = []
        
        try:
            if isinstance(raw_documents, dict):
                # Dictionary format: convert to list of documents
                logger.info(f"   Raw length/size: {len(raw_documents)}")
                
                for key, value in raw_documents.items():
                    if isinstance(value, dict):
                        # Each value is a document dict
                        doc = {
                            'id': value.get('id', key),
                            'text': value.get('text', value.get('content', str(value))),
                            'metadata': value.get('metadata', {}),
                            'index': len(normalized)
                        }
                        normalized.append(doc)
                    elif isinstance(value, str):
                        # Simple string documents
                        doc = {
                            'id': key,
                            'text': value,
                            'metadata': {},
                            'index': len(normalized)
                        }
                        normalized.append(doc)
                        
            elif isinstance(raw_documents, list):
                # List format: normalize each item
                logger.info(f"   Raw length/size: {len(raw_documents)}")
                
                for i, item in enumerate(raw_documents):
                    if isinstance(item, dict):
                        doc = {
                            'id': item.get('id', f'doc_{i}'),
                            'text': item.get('text', item.get('content', str(item))),
                            'metadata': item.get('metadata', {}),
                            'index': i
                        }
                        normalized.append(doc)
                    elif isinstance(item, str):
                        doc = {
                            'id': f'doc_{i}',
                            'text': item,
                            'metadata': {},
                            'index': i
                        }
                        normalized.append(doc)
            
            else:
                logger.warning(f"⚠️ Unknown document format: {type(raw_documents)}")
                
            if self.debug:
                logger.info(f"🔍 DEBUG: Normalized {len(normalized)} documents")
                if normalized:
                    logger.info(f"   First document preview: {normalized[0]['text'][:100]}...")
                    
        except Exception as e:
            logger.error(f"❌ Error normalizing documents: {e}")
            
        return normalized
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant documents - OPTIMIZED for speed
        
        Args:
            query: Search query
            k: Number of results (REDUCED default from 5 to 3 for speed)
            
        Returns:
            List of relevant documents with scores
        """
        if not self.has_search_engine():
            logger.error("❌ Search engine not available")
            return []
        
        try:
            start_time = time.time()
            
            # Generate query embedding with caching
            if self.cache_embeddings and query in self.embedding_cache:
                query_embedding = self.embedding_cache[query]
                if self.debug:
                    logger.info("🚀 Using cached query embedding")
            else:
                query_embedding = self.sentence_model.encode([query])
                if self.cache_embeddings:
                    self.embedding_cache[query] = query_embedding
            
            # Ensure proper shape for FAISS
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # Search with optimized k
            k_optimized = min(k, len(self.documents), 5)  # Cap at 5 for performance
            distances, indices = self.index.search(
                query_embedding.astype('float32'), 
                k_optimized
            )
            
            # Prepare results - OPTIMIZED processing
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    
                    # Calculate similarity score (higher = better)
                    similarity_score = max(0, 1 - (distance / 2))  # Normalize to 0-1
                    
                    result = {
                        'text': doc['text'],
                        'score': round(similarity_score, 4),
                        'index': int(idx),
                        'metadata': doc.get('metadata', {}),
                        'rank': i + 1
                    }
                    results.append(result)
            
            search_time = time.time() - start_time
            
            if self.debug:
                logger.info(f"🔍 Search completed in {search_time:.3f}s")
                logger.info(f"   Query: {query[:50]}...")
                logger.info(f"   Results: {len(results)}")
                for i, result in enumerate(results[:2]):  # Show top 2
                    logger.info(f"   #{i+1}: Score {result['score']:.3f} - {result['text'][:80]}...")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return []
    
    def has_search_engine(self) -> bool:
        """Check if search engine is available and ready"""
        return (
            self.search_engine_available and 
            self.index is not None and 
            len(self.documents) > 0 and
            self._check_dependencies()
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get embedder statistics - PERFORMANCE INFO"""
        return {
            'documents_loaded': len(self.documents),
            'search_available': self.has_search_engine(),
            'cache_enabled': self.cache_embeddings,
            'cache_size': len(self.embedding_cache) if self.embedding_cache else 0,
            'model': self.model_name,
            'max_workers': self.max_workers,
            'dependencies_ok': self._check_dependencies()
        }
    
    def clear_cache(self):
        """Clear embedding cache to free memory"""
        if self.embedding_cache:
            cache_size = len(self.embedding_cache)
            self.embedding_cache.clear()
            logger.info(f"🗑️ Cleared {cache_size} cached embeddings")
    
    def optimize_for_speed(self):
        """Apply additional speed optimizations"""
        try:
            # Optimize FAISS index if possible
            if self.index and hasattr(self.index, 'nprobe'):
                # For IVF indices, reduce nprobe for speed
                original_nprobe = getattr(self.index, 'nprobe', None)
                if original_nprobe and original_nprobe > 8:
                    self.index.nprobe = min(8, original_nprobe)
                    logger.info(f"⚡ Optimized FAISS nprobe: {original_nprobe} → {self.index.nprobe}")
            
            # Limit cache size to prevent memory issues
            if self.embedding_cache and len(self.embedding_cache) > 100:
                # Keep only recent 50 entries
                recent_items = list(self.embedding_cache.items())[-50:]
                self.embedding_cache = dict(recent_items)
                logger.info("⚡ Optimized embedding cache size")
                
        except Exception as e:
            logger.warning(f"⚠️ Speed optimization error: {e}")

# =============================================================================
# COMPATIBILITY FUNCTIONS
# =============================================================================

def create_optimized_embedder(**kwargs) -> FastRAGEmbedder:
    """Create an optimized embedder instance"""
    return FastRAGEmbedder(
        cache_embeddings=True,
        max_workers=2,  # Reduced for stability
        debug=kwargs.get('debug', True),
        **kwargs
    )

# Legacy compatibility
def FastRAGEmbedder_v1(*args, **kwargs):
    """Backward compatibility wrapper"""
    return FastRAGEmbedder(*args, **kwargs)