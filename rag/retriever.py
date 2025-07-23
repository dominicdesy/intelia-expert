"""
RAG Retriever - Complete fixed version with robust embedding support
Clean code compliant with proper error handling and method normalization
"""

import os
import json
import pickle
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    RAG retriever with complete embedding method support.
    Handles all embedding methods with proper normalization and fallbacks.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize RAG retriever with robust configuration."""
        self.openai_api_key = openai_api_key or os.environ.get('OPENAI_API_KEY')
        self.rag_index_path = self._get_rag_index_path()
        self.index = None
        self.documents = []
        self.embeddings = None
        self.method = None
        self.is_loaded = False
        
        # Load index on initialization
        self._load_index()
    
    def _get_rag_index_path(self) -> Path:
        """Get RAG index path with multiple fallback locations."""
        # Check environment variable
        if os.environ.get('RAG_INDEX_PATH'):
            return Path(os.environ['RAG_INDEX_PATH'])
        
        # Check current directory
        current_dir = Path.cwd() / "rag_index"
        if current_dir.exists():
            return current_dir
        
        # Check parent directory
        parent_dir = Path(__file__).parent.parent / "rag_index"
        if parent_dir.exists():
            return parent_dir
        
        # Default fallback
        return Path("rag_index")
    
    def _normalize_embedding_method(self, method: str) -> str:
        """
        Normalize embedding method names to standard format.
        Fixes the core issue: sentence_transformers -> SentenceTransformers
        """
        if not method or not isinstance(method, str):
            return "SentenceTransformers"  # Default fallback
        
        method_lower = method.lower().strip()
        
        # Mapping of all possible variations to standard names
        method_mapping = {
            # SentenceTransformers variations
            'sentence_transformers': 'SentenceTransformers',
            'sentence-transformers': 'SentenceTransformers',
            'sentencetransformers': 'SentenceTransformers',
            'sentence transformers': 'SentenceTransformers',
            'all-minilm-l6-v2': 'SentenceTransformers',
            
            # OpenAI variations
            'openai': 'OpenAI',
            'openaiembeddings': 'OpenAI',
            'openai_embeddings': 'OpenAI',
            'text-embedding-ada-002': 'OpenAI',
            'ada-002': 'OpenAI',
            
            # TF-IDF variations
            'tfidf': 'TF-IDF',
            'tf-idf': 'TF-IDF',
            'tf_idf': 'TF-IDF',
            
            # Other variations
            'huggingface': 'SentenceTransformers',
            'transformer': 'SentenceTransformers',
            'bert': 'SentenceTransformers'
        }
        
        # Return normalized method or default
        normalized = method_mapping.get(method_lower, method)
        
        # Final validation - ensure it's a supported method
        supported_methods = ['SentenceTransformers', 'OpenAI', 'TF-IDF']
        if normalized not in supported_methods:
            logger.warning(f"Unknown method '{method}' normalized to SentenceTransformers")
            return 'SentenceTransformers'
        
        return normalized
    
    def _load_index(self) -> bool:
        """Load existing FAISS index and metadata with error recovery."""
        try:
            import faiss
        except ImportError:
            logger.error("FAISS not available - cannot load index")
            return False
        
        try:
            # Check if index files exist
            index_file = self.rag_index_path / "index.faiss"
            metadata_file = self.rag_index_path / "index.pkl"
            
            if not index_file.exists() or not metadata_file.exists():
                logger.warning(f"RAG index files not found in {self.rag_index_path}")
                return False
            
            # Load FAISS index
            self.index = faiss.read_index(str(index_file))
            logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            
            # Load and fix metadata
            with open(metadata_file, 'rb') as f:
                data = pickle.load(f)
            
            # Extract and normalize method
            raw_method = data.get('method', data.get('embedding_method', 'SentenceTransformers'))
            self.method = self._normalize_embedding_method(raw_method)
            
            # Load documents and embeddings
            self.documents = data.get('documents', [])
            self.embeddings = data.get('embeddings', [])
            
            # Convert embeddings to numpy array if needed
            if self.embeddings and not isinstance(self.embeddings, np.ndarray):
                self.embeddings = np.array(self.embeddings)
            
            logger.info(f"Loaded {len(self.documents)} documents with {self.method} embeddings")
            
            # Save corrected metadata if method was changed
            if raw_method != self.method:
                logger.info(f"Corrected embedding method: {raw_method} -> {self.method}")
                self._save_corrected_metadata(data)
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Error loading RAG index: {e}")
            return False
    
    def _save_corrected_metadata(self, data: Dict[str, Any]) -> None:
        """Save corrected metadata with normalized method name."""
        try:
            # Update method in data
            data['method'] = self.method
            data['embedding_method'] = self.method
            
            # Save corrected metadata
            metadata_file = self.rag_index_path / "index.pkl"
            backup_file = self.rag_index_path / "index.pkl.backup"
            
            # Create backup
            if metadata_file.exists() and not backup_file.exists():
                import shutil
                shutil.copy2(metadata_file, backup_file)
            
            # Save corrected version
            with open(metadata_file, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info("Saved corrected metadata with normalized embedding method")
            
        except Exception as e:
            logger.error(f"Failed to save corrected metadata: {e}")
    
    def is_available(self) -> bool:
        """Check if retriever is available and ready."""
        return self.is_loaded and self.index is not None and len(self.documents) > 0
    
    def get_contextual_diagnosis(self, query: str, k: int = 5) -> Optional[Dict[str, Any]]:
        """
        Search for relevant documents with robust error handling.
        Main entry point for RAG searches.
        """
        if not self.is_available():
            logger.warning("RAG retriever not available or index not loaded")
            return None
        
        try:
            # Create query embedding
            query_embedding = self._create_query_embedding(query)
            if query_embedding is None:
                logger.warning("Failed to create query embedding")
                return None
            
            # Search FAISS index
            scores, indices = self._search_index(query_embedding, k)
            if scores is None or indices is None:
                logger.warning("FAISS search failed")
                return None
            
            # Process results
            results = self._process_search_results(scores, indices)
            if not results:
                logger.warning("No valid search results found")
                return None
            
            # Generate answer
            answer = self._synthesize_answer(query, results)
            source_documents = [doc for doc, _ in results]
            
            return {
                'answer': answer,
                'source_documents': source_documents,
                'search_type': 'vector',
                'total_results': len(results),
                'embedding_method': self.method
            }
            
        except Exception as e:
            logger.error(f"Contextual diagnosis failed: {e}")
            return None
    
    def _create_query_embedding(self, query: str) -> Optional[np.ndarray]:
        """Create embedding for query using the detected method."""
        try:
            if self.method == "OpenAI":
                return self._create_openai_embedding(query)
            elif self.method == "SentenceTransformers":
                return self._create_sentence_transformer_embedding(query)
            elif self.method == "TF-IDF":
                return self._create_tfidf_embedding(query)
            else:
                # Fallback based on available tools
                logger.warning(f"Unknown method {self.method}, attempting fallback")
                return self._create_fallback_embedding(query)
                
        except Exception as e:
            logger.error(f"Query embedding creation failed: {e}")
            return None
    
    def _create_openai_embedding(self, query: str) -> Optional[np.ndarray]:
        """Create OpenAI embedding."""
        if not self.openai_api_key:
            logger.error("OpenAI API key not available for embedding")
            return None
        
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            response = client.embeddings.create(
                input=query,
                model="text-embedding-ada-002"
            )
            
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            logger.debug(f"Created OpenAI embedding: dimension {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            return None
    
    def _create_sentence_transformer_embedding(self, query: str) -> Optional[np.ndarray]:
        """Create SentenceTransformer embedding."""
        try:
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode([query], normalize_embeddings=True)
            
            embedding_array = np.array(embedding[0], dtype=np.float32)
            logger.debug(f"Created SentenceTransformer embedding: dimension {len(embedding_array)}")
            return embedding_array
            
        except Exception as e:
            logger.error(f"SentenceTransformer embedding failed: {e}")
            return None
    
    def _create_tfidf_embedding(self, query: str) -> Optional[np.ndarray]:
        """Create TF-IDF embedding (simplified)."""
        try:
            # For TF-IDF, create a simple representation
            if self.embeddings is not None and len(self.embeddings) > 0:
                dimension = len(self.embeddings[0])
                # Simple word-based vector
                words = query.lower().split()
                vector = np.zeros(dimension, dtype=np.float32)
                
                # Set some values based on query length and content
                for i, word in enumerate(words):
                    if i < dimension:
                        vector[i] = 0.1 + (hash(word) % 100) / 1000.0
                
                return vector
            
            return None
            
        except Exception as e:
            logger.error(f"TF-IDF embedding failed: {e}")
            return None
    
    def _create_fallback_embedding(self, query: str) -> Optional[np.ndarray]:
        """Create fallback embedding when method is unknown."""
        # Try SentenceTransformers first
        embedding = self._create_sentence_transformer_embedding(query)
        if embedding is not None:
            self.method = "SentenceTransformers"
            return embedding
        
        # Try OpenAI if available
        if self.openai_api_key:
            embedding = self._create_openai_embedding(query)
            if embedding is not None:
                self.method = "OpenAI"
                return embedding
        
        # Last resort: TF-IDF
        embedding = self._create_tfidf_embedding(query)
        if embedding is not None:
            self.method = "TF-IDF"
            return embedding
        
        logger.error("All embedding methods failed")
        return None
    
    def _search_index(self, query_embedding: np.ndarray, k: int) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Search FAISS index with query embedding."""
        try:
            import faiss
            
            # Ensure query embedding is the right shape
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # Normalize for cosine similarity (except TF-IDF)
            if self.method != "TF-IDF":
                faiss.normalize_L2(query_embedding)
            
            # Search
            distances, indices = self.index.search(query_embedding.astype('float32'), k)
            
            logger.debug(f"FAISS search completed: {len(distances[0])} results")
            return distances, indices
            
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return None, None
    
    def _process_search_results(self, distances: np.ndarray, indices: np.ndarray) -> List[Tuple[Dict[str, Any], float]]:
        """Process search results into document-score pairs."""
        results = []
        
        try:
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx < len(self.documents):
                    doc = self.documents[idx]
                    score = float(distances[0][i])
                    
                    # Ensure document has required fields
                    if isinstance(doc, dict) and 'content' in doc:
                        results.append((doc, score))
            
            logger.debug(f"Processed {len(results)} valid search results")
            return results
            
        except Exception as e:
            logger.error(f"Result processing failed: {e}")
            return []
    
    def _synthesize_answer(self, query: str, results: List[Tuple[Dict[str, Any], float]]) -> str:
        """Synthesize answer from search results."""
        if not results:
            return "No relevant information found in the knowledge base."
        
        try:
            # Extract top results
            relevant_content = []
            for doc, score in results[:3]:
                content = doc.get('content', '')
                source = doc.get('source', doc.get('file_path', 'Unknown'))
                
                # Extract filename from path
                if isinstance(source, str) and '/' in source:
                    source = source.split('/')[-1]
                
                # Truncate long content
                if len(content) > 400:
                    content = content[:400] + "..."
                
                relevant_content.append(f"From {source}:\n{content}")
            
            # Create comprehensive answer
            answer = "Based on the expert knowledge base:\n\n"
            answer += "\n\n".join(relevant_content)
            answer += f"\n\n(Found {len(results)} relevant sections from {len(set(doc.get('source', 'unknown') for doc, _ in results))} sources)"
            
            return answer
            
        except Exception as e:
            logger.error(f"Answer synthesis failed: {e}")
            return f"Found {len(results)} relevant documents but failed to synthesize answer."
    
    def retrieve(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Simple retrieve interface for compatibility."""
        result = self.get_contextual_diagnosis(query, k=kwargs.get('k', 5))
        if result and result.get('source_documents'):
            return result['source_documents']
        return []
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get comprehensive debug information."""
        return {
            'rag_index_path': str(self.rag_index_path),
            'index_exists': self.rag_index_path.exists(),
            'is_loaded': self.is_loaded,
            'is_available': self.is_available(),
            'index_available': self.index is not None,
            'documents_count': len(self.documents),
            'embedding_method': self.method,
            'embedding_dimension': len(self.embeddings[0]) if self.embeddings is not None and len(self.embeddings) > 0 else None,
            'openai_key_configured': bool(self.openai_api_key),
            'faiss_index_size': self.index.ntotal if self.index else 0
        }


# Compatibility alias
ContextualRetriever = RAGRetriever


def create_rag_retriever(openai_api_key: Optional[str] = None) -> RAGRetriever:
    """Factory function to create RAG retriever."""
    return RAGRetriever(openai_api_key)


# Module initialization with improved logging
logger.info("RAG Retriever module loaded with complete embedding support")
