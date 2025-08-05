"""
RAG Embedder - VERSION CORRIGÉE COMPLÈTE
Fix pour le problème de recherche qui retourne 0 résultats
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
    RAG Embedder corrigé avec debug approfondi
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
        Initialize FastRAGEmbedder
        """
        self.api_key = api_key
        self.model_name = model_name
        self.cache_embeddings = cache_embeddings
        self.max_workers = max_workers
        self.debug = debug
        
        # Initialize storage
        self.embedding_cache = {} if cache_embeddings else None
        self.documents = []
        self.embeddings = None
        self.index = None
        self.search_engine_available = False
        
        # Initialize dependencies
        self._init_dependencies()
        
        if self.debug:
            logger.info("🚀 Initializing FastRAGEmbedder...")
            logger.info(f"   Model: {self.model_name}")
            logger.info(f"   Dimension: 384")
            logger.info(f"   Dependencies available: {self._check_dependencies()}")
            logger.info(f"   Cache enabled: {self.cache_embeddings}")
            logger.info(f"   Max workers: {self.max_workers}")
            logger.info(f"   Debug enabled: {self.debug}")
    
    def _init_dependencies(self):
        """Initialize required dependencies"""
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
        Load existing FAISS index and documents
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
            
            logger.info(f"✅ FAISS index loaded in {load_time:.2f}s")
            logger.info(f"🔍 FAISS index info: ntotal={self.index.ntotal}, d={self.index.d}")
            
            # Load documents
            logger.info(f"🔄 Loading documents from {pkl_file}")
            start_time = time.time()
            with open(pkl_file, 'rb') as f:
                raw_documents = pickle.load(f)
            
            # Normalize documents
            self.documents = self._normalize_documents(raw_documents)
            doc_load_time = time.time() - start_time
            
            logger.info(f"✅ Documents loaded in {doc_load_time:.2f}s")
            logger.info(f"🔍 Total documents: {len(self.documents)}")
            
            # Validate consistency
            if self.index.ntotal != len(self.documents):
                logger.warning(f"⚠️ Index mismatch: FAISS has {self.index.ntotal} vectors, but {len(self.documents)} documents")
            
            self.search_engine_available = True
            logger.info("✅ Index loaded successfully - Search engine ready")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading index: {e}")
            return False
    
    def _normalize_documents(self, raw_documents: Any) -> List[Dict[str, Any]]:
        """
        Normalize documents to consistent format
        """
        if self.debug:
            logger.info("🔍 DEBUG: Normalizing documents...")
            logger.info(f"   Raw type: {type(raw_documents)}")
            
        normalized = []
        
        try:
            if isinstance(raw_documents, dict):
                logger.info(f"   Raw length/size: {len(raw_documents)}")
                
                for key, value in raw_documents.items():
                    if isinstance(value, dict):
                        doc = {
                            'id': value.get('id', key),
                            'text': value.get('text', value.get('content', str(value))),
                            'metadata': value.get('metadata', {}),
                            'index': len(normalized)
                        }
                        normalized.append(doc)
                    elif isinstance(value, str):
                        doc = {
                            'id': key,
                            'text': value,
                            'metadata': {},
                            'index': len(normalized)
                        }
                        normalized.append(doc)
                        
            elif isinstance(raw_documents, list):
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
            
            if self.debug:
                logger.info(f"🔍 DEBUG: Normalized {len(normalized)} documents")
                if normalized:
                    logger.info(f"   First document preview: {normalized[0]['text'][:100]}...")
                    
        except Exception as e:
            logger.error(f"❌ Error normalizing documents: {e}")
            
        return normalized
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant documents - VERSION CORRIGÉE
        """
        if not self.has_search_engine():
            logger.error("❌ Search engine not available")
            return []

        try:
            start_time = time.time()
            
            logger.info(f"🔍 DEBUG: Starting search")
            logger.info(f"   Query: {query[:100]}...")
            logger.info(f"   Requested k: {k}")
            logger.info(f"   Available documents: {len(self.documents)}")
            logger.info(f"   FAISS index total: {self.index.ntotal}")
            
            # Generate query embedding
            if self.cache_embeddings and query in self.embedding_cache:
                query_embedding = self.embedding_cache[query]
                logger.info("🚀 Using cached query embedding")
            else:
                logger.info("🔄 Generating new query embedding...")
                query_embedding = self.sentence_model.encode([query])
                if self.cache_embeddings:
                    self.embedding_cache[query] = query_embedding
                logger.info(f"✅ Query embedding generated: shape={query_embedding.shape}")
            
            # Ensure proper shape for FAISS
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # Determine search k
            k_search = min(k, len(self.documents), self.index.ntotal)
            logger.info(f"🔍 Searching with k_search={k_search}")
            
            # Perform FAISS search
            logger.info("🔄 Performing FAISS search...")
            distances, indices = self.index.search(
                query_embedding.astype('float32'), 
                k_search
            )
            
            logger.info(f"✅ FAISS search completed")
            logger.info(f"   Distances shape: {distances.shape}")
            logger.info(f"   Indices shape: {indices.shape}")
            logger.info(f"   Distances[0]: {distances[0]}")
            logger.info(f"   Indices[0]: {indices[0]}")
            
            # Process results
            results = []
            valid_results = 0
            
            for i in range(len(distances[0])):
                distance = distances[0][i]
                idx = indices[0][i]
                
                logger.info(f"🔍 Processing result {i}: distance={distance}, idx={idx}")
                
                # Validation
                if idx < 0:
                    logger.warning(f"   ⚠️ Skipping negative index: {idx}")
                    continue
                    
                if idx >= len(self.documents):
                    logger.warning(f"   ⚠️ Skipping out-of-range index: {idx} >= {len(self.documents)}")
                    continue
                
                # Calculate similarity score
                similarity_score = max(0.0, 1.0 - (distance / 2.0))
                
                logger.info(f"   ✅ Valid result: similarity={similarity_score:.4f}")
                
                # Get document
                doc = self.documents[idx]
                
                result = {
                    'text': doc['text'],
                    'score': round(similarity_score, 4),
                    'index': int(idx),
                    'metadata': doc.get('metadata', {}),
                    'rank': valid_results + 1,
                    'distance': float(distance)
                }
                
                results.append(result)
                valid_results += 1
                
                logger.info(f"   📄 Document preview: {doc['text'][:100]}...")
            
            search_time = time.time() - start_time
            
            logger.info(f"🔍 Search completed in {search_time:.3f}s")
            logger.info(f"   Query: {query[:50]}...")
            logger.info(f"   Results: {len(results)}")
            
            # Log top results
            for i, result in enumerate(results[:3]):
                logger.info(f"   #{i+1}: Score {result['score']:.3f} (dist: {result['distance']:.3f}) - {result['text'][:80]}...")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return []
    
    def has_search_engine(self) -> bool:
        """Check if search engine is available and ready"""
        available = (
            self.search_engine_available and 
            self.index is not None and 
            len(self.documents) > 0 and
            self._check_dependencies()
        )
        
        if not available:
            logger.warning(f"🔍 Search engine not ready:")
            logger.warning(f"   search_engine_available: {self.search_engine_available}")
            logger.warning(f"   index is not None: {self.index is not None}")
            logger.warning(f"   documents > 0: {len(self.documents) > 0}")
            logger.warning(f"   dependencies_ok: {self._check_dependencies()}")
        
        return available
    
    def get_stats(self) -> Dict[str, Any]:
        """Get embedder statistics"""
        return {
            'documents_loaded': len(self.documents),
            'search_available': self.has_search_engine(),
            'cache_enabled': self.cache_embeddings,
            'cache_size': len(self.embedding_cache) if self.embedding_cache else 0,
            'model': self.model_name,
            'max_workers': self.max_workers,
            'dependencies_ok': self._check_dependencies(),
            'faiss_total': self.index.ntotal if self.index else 0
        }
    
    def clear_cache(self):
        """Clear embedding cache"""
        if self.embedding_cache:
            cache_size = len(self.embedding_cache)
            self.embedding_cache.clear()
            logger.info(f"🗑️ Cleared {cache_size} cached embeddings")
    
    def debug_search(self, query: str) -> Dict[str, Any]:
        """
        Debug method to understand search issues
        """
        debug_info = {
            'query': query,
            'has_search_engine': self.has_search_engine(),
            'documents_count': len(self.documents),
            'faiss_total': self.index.ntotal if self.index else 0,
            'model_name': self.model_name,
            'cache_enabled': self.cache_embeddings
        }
        
        if self.has_search_engine():
            try:
                # Test embedding generation
                embedding = self.sentence_model.encode([query])
                debug_info['embedding_shape'] = embedding.shape
                debug_info['embedding_generated'] = True
                
                # Test FAISS search
                if embedding.ndim == 1:
                    embedding = embedding.reshape(1, -1)
                
                distances, indices = self.index.search(embedding.astype('float32'), 1)
                debug_info['faiss_search_success'] = True
                debug_info['top_distance'] = float(distances[0][0])
                debug_info['top_index'] = int(indices[0][0])
                
                if indices[0][0] >= 0 and indices[0][0] < len(self.documents):
                    debug_info['document_accessible'] = True
                    debug_info['document_preview'] = self.documents[indices[0][0]]['text'][:100]
                else:
                    debug_info['document_accessible'] = False
                    
            except Exception as e:
                debug_info['error'] = str(e)
        
        return debug_info

# =============================================================================
# COMPATIBILITY FUNCTIONS
# =============================================================================

def create_optimized_embedder(**kwargs) -> FastRAGEmbedder:
    """Create an optimized embedder instance"""
    return FastRAGEmbedder(
        cache_embeddings=True,
        max_workers=2,
        debug=kwargs.get('debug', True),
        **kwargs
    )

# Legacy compatibility
def FastRAGEmbedder_v1(*args, **kwargs):
    """Backward compatibility wrapper"""
    return FastRAGEmbedder(*args, **kwargs)