"""
Optimized RAG Embedder with Config Manager Integration
Clean code compliant version with proper error handling and configuration management
"""

import os
import sys
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import time
import pickle

# Logging configuration
logger = logging.getLogger(__name__)

# Suppress warnings for cleaner output
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sentence_transformers')
warnings.filterwarnings('ignore', category=FutureWarning, module='transformers')

# Path management
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# RAG Config Manager Integration - AJOUT
try:
    from ..config.rag_config_manager import RAGConfigManager
    RAG_CONFIG_MANAGER_AVAILABLE = True
    logger.debug("RAG Config Manager available for embedder")
except ImportError:
    try:
        from core.config.rag_config_manager import RAGConfigManager
        RAG_CONFIG_MANAGER_AVAILABLE = True
        logger.debug("RAG Config Manager available (alternate path)")
    except ImportError:
        RAG_CONFIG_MANAGER_AVAILABLE = False
        logger.debug("RAG Config Manager not available")

# Dependency cache for optimized imports
_DEPENDENCY_CACHE = {}

def _check_and_cache_dependency(module_name: str, import_func) -> bool:
    """Cache dependencies to avoid repeated import checks."""
    if module_name not in _DEPENDENCY_CACHE:
        try:
            import_func()
            _DEPENDENCY_CACHE[module_name] = True
            logger.debug(f"Dependency {module_name} available")
        except ImportError as e:
            _DEPENDENCY_CACHE[module_name] = False
            logger.debug(f"Dependency {module_name} not available: {e}")
    
    return _DEPENDENCY_CACHE[module_name]

# Import functions for lazy loading
def _import_sentence_transformers():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer

def _import_faiss():
    import faiss
    return faiss

def _import_parser_router():
    try:
        from parsers.parser_router import EnhancedParserRouter
        return EnhancedParserRouter
    except ImportError:
        from parser_router import EnhancedParserRouter
        return EnhancedParserRouter

def _import_optimized_vector_store():
    try:
        from rag.optimized_vector_store import OptimizedVectorStore
        return OptimizedVectorStore
    except ImportError:
        from optimized_vector_store import OptimizedVectorStore
        return OptimizedVectorStore

def _import_intelligent_retriever():
    try:
        from rag.intelligent_retrieval import IntelligentRetriever
        return IntelligentRetriever
    except ImportError:
        from intelligent_retrieval import IntelligentRetriever
        return IntelligentRetriever

def _import_tenant_management():
    try:
        from rag.tenant_document_manager import TenantDocumentManager
        from rag.adaptive_structure_manager import AdaptiveStructureManager
        return TenantDocumentManager, AdaptiveStructureManager
    except ImportError:
        from tenant_document_manager import TenantDocumentManager
        from adaptive_structure_manager import AdaptiveStructureManager
        return TenantDocumentManager, AdaptiveStructureManager

def _import_adaptive_chunking():
    try:
        from rag.adaptive_chunking import AdaptiveChunker
        return AdaptiveChunker
    except ImportError:
        from adaptive_chunking import AdaptiveChunker
        return AdaptiveChunker

# Cached dependency checks
SENTENCE_TRANSFORMERS_AVAILABLE = _check_and_cache_dependency('sentence_transformers', _import_sentence_transformers)
FAISS_AVAILABLE = _check_and_cache_dependency('faiss', _import_faiss)
ENHANCED_PARSER_AVAILABLE = _check_and_cache_dependency('enhanced_parser', _import_parser_router)
OPTIMIZED_VECTOR_STORE_AVAILABLE = _check_and_cache_dependency('optimized_vector_store', _import_optimized_vector_store)
INTELLIGENT_RETRIEVAL_AVAILABLE = _check_and_cache_dependency('intelligent_retrieval', _import_intelligent_retriever)
TENANT_MANAGEMENT_AVAILABLE = _check_and_cache_dependency('tenant_management', _import_tenant_management)
ADAPTIVE_CHUNKING_AVAILABLE = _check_and_cache_dependency('adaptive_chunking', _import_adaptive_chunking)


class LazyImporter:
    """Lazy importer for optional dependencies."""
    
    def __init__(self, import_func, available: bool):
        self._import_func = import_func
        self._available = available
        self._module = None
    
    @property
    def available(self) -> bool:
        return self._available
    
    def get(self):
        if not self._available:
            return None
        if self._module is None:
            self._module = self._import_func()
        return self._module

# Lazy loaders for all modules
_sentence_transformers = LazyImporter(_import_sentence_transformers, SENTENCE_TRANSFORMERS_AVAILABLE)
_faiss = LazyImporter(_import_faiss, FAISS_AVAILABLE)
_parser_router = LazyImporter(_import_parser_router, ENHANCED_PARSER_AVAILABLE)
_optimized_vector_store = LazyImporter(_import_optimized_vector_store, OPTIMIZED_VECTOR_STORE_AVAILABLE)
_intelligent_retrieval = LazyImporter(_import_intelligent_retriever, INTELLIGENT_RETRIEVAL_AVAILABLE)
_tenant_management = LazyImporter(_import_tenant_management, TENANT_MANAGEMENT_AVAILABLE)
_adaptive_chunking = LazyImporter(_import_adaptive_chunking, ADAPTIVE_CHUNKING_AVAILABLE)


class OptimizedRAGEmbedder:
    """
    Optimized RAG embedder with perfect import management and config integration.
    Clean code compliant version with lazy loading and configuration management.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, openai_api_key: Optional[str] = None):
        """Initialize optimized RAG embedder with dependency management."""
        
        # Configuration with defaults
        self.config = {
            'model_name': 'all-MiniLM-L6-v2',
            'chunk_size': 256,
            'overlap': 64,
            'documents_path': 'documents',
            'index_path': 'rag_index/index.faiss',
            'metadata_path': 'rag_index/index.pkl',
            'use_optimized_vector_store': True,
            'use_intelligent_retrieval': True,
            'use_adaptive_chunking': True,
            'tenant_isolation': False,
            'enable_intelligent_routing': True,
            'enable_adaptive_chunking': True,
            'enable_hybrid_search': True
        }
        
        if config:
            self.config.update(config)
        
        # Set OpenAI API key if provided
        if openai_api_key:
            os.environ['OPENAI_API_KEY'] = openai_api_key
        
        # NOUVEAU : Auto-détection configuration RAG si aucune config fournie
        if RAG_CONFIG_MANAGER_AVAILABLE and not config and not openai_api_key:
            try:
                rag_manager = RAGConfigManager()
                existing_config = rag_manager.detect_existing_configuration()
                method, rag_config = rag_manager.detect_optimal_rag_method(existing_config)
                
                # Adapter la configuration selon la méthode détectée
                if method == "OpenAI":
                    self.config['embedding_method'] = 'OpenAI'
                    self.config['model_name'] = rag_config.get('model_name', 'text-embedding-ada-002')
                    # Récupérer la clé OpenAI depuis les secrets
                    if rag_config.get('use_existing_key'):
                        existing_key = rag_manager._get_openai_key_from_secrets()
                        if existing_key:
                            os.environ['OPENAI_API_KEY'] = existing_key
                            logger.info("Using existing OpenAI key from configuration")
                
                elif method == "SentenceTransformers":
                    self.config['embedding_method'] = 'SentenceTransformers'
                    self.config['model_name'] = rag_config.get('model_name', 'all-MiniLM-L6-v2')
                    logger.info("Using SentenceTransformers with auto-detected configuration")
                
                elif method == "disabled":
                    logger.warning("RAG system disabled - no suitable embedding method found")
                
                logger.info(f"Auto-configured RAG embedder with method: {method}")
                
            except Exception as e:
                logger.warning(f"RAG auto-configuration failed: {e}")
        
        # Initialize components lazily
        self.available = False
        self._model = None
        self._parser_router = None
        self._vector_store = None
        self._retriever = None
        self._search_engine = None
        self._adaptive_chunker = None
        self._tenant_manager = None
        
        # Index and documents storage
        self.index = None
        self.documents = []
        self.embeddings = None
        
        # Processing statistics
        self.processing_stats = {
            'documents_processed': 0,
            'total_chunks': 0,
            'processing_time': 0.0,
            'last_build_time': None,
            'errors': 0
        }
        
        # Feature availability based on cache
        self.available_features = {
            'sentence_transformers': SENTENCE_TRANSFORMERS_AVAILABLE,
            'faiss': FAISS_AVAILABLE,
            'enhanced_parser': ENHANCED_PARSER_AVAILABLE,
            'optimized_vector_store': OPTIMIZED_VECTOR_STORE_AVAILABLE,
            'intelligent_retrieval': INTELLIGENT_RETRIEVAL_AVAILABLE,
            'tenant_management': TENANT_MANAGEMENT_AVAILABLE,
            'adaptive_chunking': ADAPTIVE_CHUNKING_AVAILABLE
        }
        
        # Check dependencies and initialize
        if self._check_core_dependencies():
            self._initialize_components()
        else:
            self._initialize_minimal_components()
    
    @property
    def system_ready(self) -> bool:
        """Check if the system is ready for use."""
        return self.available
    
    @property
    def model(self):
        """Lazy loading of embedding model."""
        if self._model is None:
            # Vérifier si on doit utiliser OpenAI ou SentenceTransformers
            embedding_method = self.config.get('embedding_method', 'SentenceTransformers')
            
            if embedding_method == 'OpenAI' and os.environ.get('OPENAI_API_KEY'):
                try:
                    import openai
                    self._model = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])
                    logger.debug("OpenAI embedding model loaded")
                except ImportError:
                    logger.warning("OpenAI not available, falling back to SentenceTransformers")
                    embedding_method = 'SentenceTransformers'
            
            if embedding_method == 'SentenceTransformers' and _sentence_transformers.available:
                SentenceTransformer = _sentence_transformers.get()
                if SentenceTransformer:
                    try:
                        self._model = SentenceTransformer(self.config['model_name'])
                        logger.debug(f"SentenceTransformer model loaded: {self.config['model_name']}")
                    except Exception as e:
                        logger.error(f"Failed to load SentenceTransformer model: {e}")
        
        return self._model
    
    @property
    def parser_router(self):
        """Lazy loading of parser router."""
        if self._parser_router is None and _parser_router.available:
            EnhancedParserRouter = _parser_router.get()
            if EnhancedParserRouter:
                self._parser_router = EnhancedParserRouter()
                logger.debug("Parser router loaded")
        return self._parser_router
    
    @property
    def vector_store(self):
        """Lazy loading of vector store."""
        if self._vector_store is None and _optimized_vector_store.available:
            OptimizedVectorStore = _optimized_vector_store.get()
            if OptimizedVectorStore:
                self._vector_store = OptimizedVectorStore()
                logger.debug("Vector store loaded")
        return self._vector_store
    
    @property
    def retriever(self):
        """Lazy loading of intelligent retriever."""
        if self._retriever is None and _intelligent_retrieval.available:
            IntelligentRetriever = _intelligent_retrieval.get()
            if IntelligentRetriever:
                self._retriever = IntelligentRetriever()
                logger.debug("Intelligent retriever loaded")
        return self._retriever
    
    @property
    def adaptive_chunker(self):
        """Lazy loading of adaptive chunker."""
        if self._adaptive_chunker is None and _adaptive_chunking.available:
            AdaptiveChunker = _adaptive_chunking.get()
            if AdaptiveChunker:
                self._adaptive_chunker = AdaptiveChunker()
                logger.debug("Adaptive chunker loaded")
        return self._adaptive_chunker
    
    @property
    def tenant_manager(self):
        """Lazy loading of tenant manager."""
        if self._tenant_manager is None and _tenant_management.available:
            tenant_classes = _tenant_management.get()
            if tenant_classes:
                TenantDocumentManager, _ = tenant_classes
                self._tenant_manager = TenantDocumentManager()
                logger.debug("Tenant manager loaded")
        return self._tenant_manager
    
    def _check_core_dependencies(self) -> bool:
        """Check if main dependencies are available."""
        return SENTENCE_TRANSFORMERS_AVAILABLE and FAISS_AVAILABLE
    
    def _initialize_components(self):
        """Initialize components with lazy loading."""
        try:
            # No immediate initialization - everything is lazy loaded
            self.available = True
            logger.debug("Optimized RAG embedder initialized with lazy loading")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            self._initialize_minimal_components()
    
    def _initialize_minimal_components(self):
        """Initialize minimal components as fallback."""
        try:
            # At minimum, try to have basic components
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.available = True
                logger.debug("Minimal RAG embedder initialized")
            else:
                logger.warning("RAG embedder initialization failed - missing core dependencies")
                
        except Exception as e:
            logger.error(f"Failed to initialize minimal components: {e}")
            self.available = False
    
    def process_documents(self, documents_path: Optional[str] = None, 
                         tenant_id: Optional[str] = None,
                         force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Process documents and create embeddings.
        Uses lazy loading and configuration management for optimal performance.
        """
        if not self.available:
            return {
                'status': 'error',
                'message': 'RAG embedder not available',
                'processed_documents': 0,
                'processing_time': 0.0
            }
        
        start_time = time.time()
        documents_path = documents_path or self.config['documents_path']
        
        # Check if index exists and rebuild is not forced
        if not force_rebuild and self._index_exists():
            if self._load_existing_index():
                processing_time = time.time() - start_time
                return {
                    'status': 'loaded_existing',
                    'message': 'Loaded existing index',
                    'processed_documents': len(self.documents),
                    'processing_time': processing_time
                }
        
        try:
            # Load model on demand
            if not self.model:
                return {
                    'status': 'error',
                    'message': 'Failed to load embedding model',
                    'processed_documents': 0,
                    'processing_time': time.time() - start_time
                }
            
            # Process documents
            processed_count = self._process_documents_internal(documents_path, tenant_id)
            
            # Build index
            if processed_count > 0:
                self._build_faiss_index()
                self._save_index()
            
            processing_time = time.time() - start_time
            
            # Update stats
            self.processing_stats.update({
                'documents_processed': processed_count,
                'total_chunks': len(self.documents),
                'processing_time': processing_time,
                'last_build_time': datetime.now().isoformat()
            })
            
            logger.info(f"Processed {processed_count} documents in {processing_time:.2f}s")
            
            return {
                'status': 'success',
                'message': f'Successfully processed {processed_count} documents',
                'processed_documents': processed_count,
                'total_chunks': len(self.documents),
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            self.processing_stats['errors'] += 1
            
            return {
                'status': 'error',
                'message': f'Document processing failed: {str(e)}',
                'processed_documents': 0,
                'processing_time': time.time() - start_time
            }
    
    def _process_documents_internal(self, documents_path: str, tenant_id: Optional[str]) -> int:
        """Internal document processing with optimized routing."""
        documents_dir = Path(documents_path)
        if not documents_dir.exists():
            logger.warning(f"Documents path does not exist: {documents_path}")
            return 0
        
        self.documents = []
        processed_count = 0
        
        for file_path in documents_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                try:
                    # Use parser router if available
                    if self.parser_router:
                        parsed_content = self.parser_router.parse_document(str(file_path))
                        chunks = parsed_content.get('chunks', [])
                    else:
                        # Basic text processing
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        chunks = self._basic_chunk_text(content)
                    
                    # Process chunks
                    for chunk in chunks:
                        if len(chunk.strip()) > 50:  # Skip very short chunks
                            doc_metadata = {
                                'file_path': str(file_path),
                                'tenant_id': tenant_id,
                                'chunk_index': len(self.documents),
                                'content': chunk.strip()
                            }
                            self.documents.append(doc_metadata)
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process file {file_path}: {e}")
        
        return processed_count
    
    def _basic_chunk_text(self, text: str) -> List[str]:
        """Basic text chunking as fallback."""
        chunk_size = self.config['chunk_size']
        overlap = self.config['overlap']
        
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    def _build_faiss_index(self):
        """Build FAISS index from documents."""
        if not self.documents or not self.model:
            return
        
        try:
            import faiss
            
            # Extract content for embedding
            texts = [doc['content'] for doc in self.documents]
            
            # Generate embeddings
            embedding_method = self.config.get('embedding_method', 'SentenceTransformers')
            
            if embedding_method == 'OpenAI':
                self.embeddings = self._generate_openai_embeddings(texts)
            else:
                self.embeddings = self.model.encode(texts, show_progress_bar=True)
            
            # Create FAISS index
            dimension = self.embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(self.embeddings)
            self.index.add(self.embeddings.astype('float32'))
            
            logger.info(f"Built FAISS index with {len(self.documents)} documents (dim: {dimension})")
            
        except Exception as e:
            logger.error(f"Failed to build FAISS index: {e}")
            raise
    
    def _generate_openai_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using OpenAI API."""
        try:
            import openai
            
            client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])
            model_name = self.config.get('model_name', 'text-embedding-ada-002')
            
            embeddings = []
            batch_size = 100  # Process in batches to avoid rate limits
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = client.embeddings.create(
                    input=batch,
                    model=model_name
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            return np.array(embeddings)
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise
    
    def _save_index(self):
        """Save index and metadata to disk."""
        try:
            import faiss
            
            # Create directories
            index_path = Path(self.config['index_path'])
            metadata_path = Path(self.config['metadata_path'])
            
            index_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, str(index_path))
            
            # Save metadata
            metadata = {
                'documents': self.documents,
                'embeddings': self.embeddings.tolist() if self.embeddings is not None else [],
                'config': self.config,
                'processing_stats': self.processing_stats
            }
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Index saved to {index_path}")
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def _index_exists(self) -> bool:
        """Check if index files exist."""
        try:
            index_path = Path(self.config['index_path'])
            metadata_path = Path(self.config['metadata_path'])
            return index_path.exists() and metadata_path.exists()
        except Exception:
            return False
    
    def _load_existing_index(self) -> bool:
        """Load existing index and metadata."""
        try:
            import faiss
            
            # Load FAISS index
            index_path = Path(self.config['index_path'])
            self.index = faiss.read_index(str(index_path))
            
            # Load metadata
            metadata_path = Path(self.config['metadata_path'])
            with open(metadata_path, 'rb') as f:
                data = pickle.load(f)
                self.documents = data.get('documents', [])
                self.embeddings = np.array(data.get('embeddings', []))
            
            logger.info(f"Loaded existing index with {len(self.documents)} documents")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load existing index: {e}")
            return False
    
    def search(self, query: str, k: int = 5, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for relevant documents."""
        if not self.available or not self.index or not self.model:
            return []
        
        try:
            # Generate query embedding
            embedding_method = self.config.get('embedding_method', 'SentenceTransformers')
            
            if embedding_method == 'OpenAI':
                query_embedding = self._generate_openai_embeddings([query])[0]
            else:
                query_embedding = self.model.encode([query])[0]
            
            # Normalize for cosine similarity
            import faiss
            query_embedding = query_embedding.reshape(1, -1).astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.index.search(query_embedding, k)
            
            # Format results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.documents):
                    doc = self.documents[idx].copy()
                    doc['score'] = float(score)
                    doc['rank'] = i + 1
                    
                    # Filter by tenant if specified
                    if tenant_id is None or doc.get('tenant_id') == tenant_id:
                        results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status including configuration."""
        return {
            'system_ready': self.available,
            'available_features': self.available_features,
            'processing_stats': self.processing_stats,
            'configuration': self.config,
            'rag_config_manager': RAG_CONFIG_MANAGER_AVAILABLE,
            'embedding_method': self.config.get('embedding_method', 'SentenceTransformers'),
            'model_loaded': self._model is not None,
            'index_built': self.index is not None,
            'documents_count': len(self.documents) if self.documents else 0
        }


# Backward compatibility aliases
RAGEmbedder = OptimizedRAGEmbedder
EnhancedDocumentEmbedder = OptimizedRAGEmbedder


def create_optimized_embedder(config: Optional[Dict[str, Any]] = None, 
                             openai_api_key: Optional[str] = None) -> OptimizedRAGEmbedder:
    """Factory function to create optimized RAG embedder."""
    return OptimizedRAGEmbedder(config, openai_api_key)


if __name__ == "__main__":
    # Test the embedder
    print("Testing Optimized RAG Embedder with Config Manager...")
    
    embedder = OptimizedRAGEmbedder()
    status = embedder.get_system_status()
    
    print("System Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    if embedder.available:
        print("✅ Embedder is ready for use")
    else:
        print("❌ Embedder is not available")
    
    print("Test completed!")
