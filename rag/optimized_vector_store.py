#!/usr/bin/env python3
"""
Optimized Vector Store with FAISS integration
High-performance vector storage and retrieval for RAG system
"""

import os
import sys
import logging
import time
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
    logger.debug("FAISS available for vector operations")
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available - vector operations will be limited")


@dataclass
class VectorStoreConfig:
    """Configuration for vector store."""
    index_type: str = "IVF"  # IVF, HNSW, Flat
    nlist: int = 100  # Number of clusters for IVF
    m: int = 16  # Number of connections for HNSW
    ef_construction: int = 200  # Construction parameter for HNSW
    ef_search: int = 64  # Search parameter for HNSW
    dimension: int = 384  # Vector dimension
    metric: str = "L2"  # L2, IP (Inner Product)
    use_gpu: bool = False
    normalize_vectors: bool = True
    enable_compression: bool = False


@dataclass
class SearchResult:
    """Result from vector search."""
    document_id: int
    score: float
    document: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexInfo:
    """Information about the vector index."""
    total_vectors: int
    index_type: str
    dimension: int
    is_trained: bool
    created_at: str
    last_updated: str
    size_mb: float


class OptimizedVectorStore:
    """Optimized vector store with FAISS backend."""
    
    def __init__(self, config: Optional[VectorStoreConfig] = None):
        """Initialize optimized vector store."""
        self.config = config or VectorStoreConfig()
        self.index = None
        self.documents = []
        self.metadata = []
        self.id_to_index = {}
        self.index_to_id = {}
        self.is_trained = False
        self.created_at = datetime.now().isoformat()
        self.last_updated = None
        
        # Performance tracking
        self.performance_stats = {
            'total_searches': 0,
            'total_search_time': 0.0,
            'avg_search_time': 0.0,
            'total_additions': 0,
            'total_add_time': 0.0,
            'avg_add_time': 0.0,
            'index_builds': 0,
            'total_build_time': 0.0
        }
        
        # Check availability
        if not FAISS_AVAILABLE:
            logger.warning("FAISS not available - vector store will have limited functionality")
    
    def create_optimized_index(self, embeddings: np.ndarray, train_data: Optional[np.ndarray] = None) -> bool:
        """Create an optimized FAISS index."""
        if not FAISS_AVAILABLE:
            logger.error("FAISS not available - cannot create index")
            return False
        
        try:
            start_time = time.time()
            
            # Validate embeddings
            if embeddings.dtype != np.float32:
                embeddings = embeddings.astype('float32')
            
            # Normalize vectors if requested
            if self.config.normalize_vectors:
                embeddings = self._normalize_vectors(embeddings)
            
            # Update dimension from embeddings
            self.config.dimension = embeddings.shape[1]
            
            # Create index based on configuration
            self.index = self._create_index_by_type(embeddings)
            
            # Train the index if necessary
            if self._needs_training():
                train_data = train_data if train_data is not None else embeddings
                logger.info(f"Training index with {len(train_data)} vectors...")
                self.index.train(train_data)
                self.is_trained = True
            
            # Add vectors to index
            self.index.add(embeddings)
            
            # Update performance stats
            build_time = time.time() - start_time
            self.performance_stats['index_builds'] += 1
            self.performance_stats['total_build_time'] += build_time
            self.last_updated = datetime.now().isoformat()
            
            logger.info(f"Created optimized {self.config.index_type} index with {embeddings.shape[0]} vectors in {build_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create optimized index: {e}")
            return False
    
    def _create_index_by_type(self, embeddings: np.ndarray) -> Any:
        """Create FAISS index based on type."""
        dimension = embeddings.shape[1]
        
        if self.config.index_type == "Flat":
            # Flat index for small datasets
            if self.config.metric == "L2":
                return faiss.IndexFlatL2(dimension)
            else:
                return faiss.IndexFlatIP(dimension)
        
        elif self.config.index_type == "IVF":
            # IVF index for medium datasets
            if self.config.metric == "L2":
                quantizer = faiss.IndexFlatL2(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, self.config.nlist)
            else:
                quantizer = faiss.IndexFlatIP(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, self.config.nlist)
            
            return index
        
        elif self.config.index_type == "HNSW":
            # HNSW index for large datasets
            index = faiss.IndexHNSWFlat(dimension, self.config.m)
            index.hnsw.efConstruction = self.config.ef_construction
            index.hnsw.efSearch = self.config.ef_search
            return index
        
        else:
            logger.warning(f"Unknown index type: {self.config.index_type}, using Flat")
            return faiss.IndexFlatL2(dimension)
    
    def _needs_training(self) -> bool:
        """Check if the index needs training."""
        return hasattr(self.index, 'is_trained') and not self.index.is_trained
    
    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """Normalize vectors to unit length."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        return vectors / norms
    
    def add_documents(self, documents: List[Dict[str, Any]], 
                     embeddings: np.ndarray, 
                     metadata: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Add documents with their embeddings to the store."""
        if not FAISS_AVAILABLE or self.index is None:
            logger.error("Index not available or not created")
            return False
        
        try:
            start_time = time.time()
            
            # Validate inputs
            if len(documents) != len(embeddings):
                raise ValueError("Number of documents must match number of embeddings")
            
            # Normalize embeddings if configured
            if self.config.normalize_vectors:
                embeddings = self._normalize_vectors(embeddings)
            
            # Convert to float32 if needed
            if embeddings.dtype != np.float32:
                embeddings = embeddings.astype('float32')
            
            # Add to index
            start_idx = len(self.documents)
            self.index.add(embeddings)
            
            # Update document storage
            for i, doc in enumerate(documents):
                doc_id = doc.get('id', start_idx + i)
                self.documents.append(doc)
                self.id_to_index[doc_id] = start_idx + i
                self.index_to_id[start_idx + i] = doc_id
            
            # Update metadata
            if metadata:
                self.metadata.extend(metadata)
            else:
                self.metadata.extend([{}] * len(documents))
            
            # Update performance stats
            add_time = time.time() - start_time
            self.performance_stats['total_additions'] += len(documents)
            self.performance_stats['total_add_time'] += add_time
            self.performance_stats['avg_add_time'] = (
                self.performance_stats['total_add_time'] / self.performance_stats['total_additions']
            )
            
            self.last_updated = datetime.now().isoformat()
            
            logger.info(f"Added {len(documents)} documents in {add_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False
    
    def search_with_filters(self, query_vector: np.ndarray, 
                          k: int = 10, 
                          filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search with optional metadata filters."""
        if not FAISS_AVAILABLE or self.index is None:
            logger.error("Index not available")
            return []
        
        try:
            start_time = time.time()
            
            # Normalize query vector if configured
            if self.config.normalize_vectors:
                query_vector = self._normalize_vectors(query_vector.reshape(1, -1))[0]
            
            # Convert to float32 if needed
            if query_vector.dtype != np.float32:
                query_vector = query_vector.astype('float32')
            
            # Perform search
            query_vector = query_vector.reshape(1, -1)
            
            # Search more results if we need to filter
            search_k = k * 10 if filters else k
            scores, indices = self.index.search(query_vector, search_k)
            
            # Convert results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for missing results
                    continue
                
                if idx >= len(self.documents):
                    logger.warning(f"Index {idx} out of range for documents")
                    continue
                
                document = self.documents[idx]
                metadata = self.metadata[idx] if idx < len(self.metadata) else {}
                
                # Apply filters if provided
                if filters and not self._matches_filters(document, metadata, filters):
                    continue
                
                results.append(SearchResult(
                    document_id=self.index_to_id.get(idx, idx),
                    score=float(score),
                    document=document,
                    metadata=metadata
                ))
                
                # Stop if we have enough results
                if len(results) >= k:
                    break
            
            # Update performance stats
            search_time = time.time() - start_time
            self.performance_stats['total_searches'] += 1
            self.performance_stats['total_search_time'] += search_time
            self.performance_stats['avg_search_time'] = (
                self.performance_stats['total_search_time'] / self.performance_stats['total_searches']
            )
            
            logger.debug(f"Search completed in {search_time:.4f}s, found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _matches_filters(self, document: Dict[str, Any], 
                        metadata: Dict[str, Any], 
                        filters: Dict[str, Any]) -> bool:
        """Check if document matches filters."""
        for key, value in filters.items():
            # Check in document
            if key in document:
                if document[key] != value:
                    return False
            # Check in metadata
            elif key in metadata:
                if metadata[key] != value:
                    return False
            else:
                return False
        
        return True
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        if doc_id in self.id_to_index:
            idx = self.id_to_index[doc_id]
            if idx < len(self.documents):
                return self.documents[idx]
        return None
    
    def get_index_info(self) -> IndexInfo:
        """Get information about the index."""
        if self.index is None:
            return IndexInfo(
                total_vectors=0,
                index_type="None",
                dimension=0,
                is_trained=False,
                created_at=self.created_at,
                last_updated=self.last_updated or self.created_at,
                size_mb=0.0
            )
        
        return IndexInfo(
            total_vectors=self.index.ntotal,
            index_type=self.config.index_type,
            dimension=self.config.dimension,
            is_trained=self.is_trained,
            created_at=self.created_at,
            last_updated=self.last_updated or self.created_at,
            size_mb=self._estimate_index_size()
        )
    
    def _estimate_index_size(self) -> float:
        """Estimate index size in MB."""
        if self.index is None:
            return 0.0
        
        # Rough estimation based on vectors and dimension
        vector_size = self.index.ntotal * self.config.dimension * 4  # 4 bytes per float32
        overhead = vector_size * 0.1  # 10% overhead estimation
        return (vector_size + overhead) / (1024 * 1024)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()
    
    def save_index(self, index_path: str, metadata_path: str) -> bool:
        """Save index and metadata to files."""
        try:
            if self.index is not None and FAISS_AVAILABLE:
                # Save FAISS index
                faiss.write_index(self.index, index_path)
                logger.info(f"Saved FAISS index to {index_path}")
            
            # Save metadata
            metadata_dict = {
                'documents': self.documents,
                'metadata': self.metadata,
                'id_to_index': self.id_to_index,
                'index_to_id': self.index_to_id,
                'config': self.config,
                'performance_stats': self.performance_stats,
                'created_at': self.created_at,
                'last_updated': self.last_updated,
                'is_trained': self.is_trained
            }
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata_dict, f)
            
            logger.info(f"Saved metadata to {metadata_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False
    
    def load_index(self, index_path: str, metadata_path: str) -> bool:
        """Load index and metadata from files."""
        try:
            # Load FAISS index
            if FAISS_AVAILABLE and Path(index_path).exists():
                self.index = faiss.read_index(index_path)
                logger.info(f"Loaded FAISS index from {index_path}")
            
            # Load metadata
            if Path(metadata_path).exists():
                with open(metadata_path, 'rb') as f:
                    metadata_dict = pickle.load(f)
                
                self.documents = metadata_dict.get('documents', [])
                self.metadata = metadata_dict.get('metadata', [])
                self.id_to_index = metadata_dict.get('id_to_index', {})
                self.index_to_id = metadata_dict.get('index_to_id', {})
                self.performance_stats = metadata_dict.get('performance_stats', {})
                self.created_at = metadata_dict.get('created_at', self.created_at)
                self.last_updated = metadata_dict.get('last_updated', None)
                self.is_trained = metadata_dict.get('is_trained', False)
                
                # Update config if available
                if 'config' in metadata_dict:
                    saved_config = metadata_dict['config']
                    if isinstance(saved_config, dict):
                        # Convert dict to VectorStoreConfig
                        for key, value in saved_config.items():
                            if hasattr(self.config, key):
                                setattr(self.config, key, value)
                
                logger.info(f"Loaded metadata from {metadata_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False
    
    def reset_index(self):
        """Reset the index and all data."""
        self.index = None
        self.documents = []
        self.metadata = []
        self.id_to_index = {}
        self.index_to_id = {}
        self.is_trained = False
        self.performance_stats = {
            'total_searches': 0,
            'total_search_time': 0.0,
            'avg_search_time': 0.0,
            'total_additions': 0,
            'total_add_time': 0.0,
            'avg_add_time': 0.0,
            'index_builds': 0,
            'total_build_time': 0.0
        }
        self.last_updated = None
        
        logger.info("Index reset successfully")


if __name__ == "__main__":
    # Test the optimized vector store
    print("🧪 TESTING OPTIMIZED VECTOR STORE")
    print("=" * 40)
    
    if not FAISS_AVAILABLE:
        print("❌ FAISS not available - cannot test vector store")
        exit(1)
    
    # Create test configuration
    config = VectorStoreConfig(
        index_type="Flat",
        dimension=128,
        normalize_vectors=True
    )
    
    # Create vector store
    store = OptimizedVectorStore(config)
    
    # Generate test data
    np.random.seed(42)  # For reproducible results
    test_embeddings = np.random.random((100, 128)).astype('float32')
    test_documents = [
        {'id': i, 'content': f'Document {i}', 'type': 'test'}
        for i in range(100)
    ]
    test_metadata = [
        {'doc_id': i, 'category': 'test', 'created_at': '2025-01-01'}
        for i in range(100)
    ]
    
    # Test index creation
    print("\n🏗️ Creating optimized index...")
    success = store.create_optimized_index(test_embeddings)
    print(f"   Index creation: {'✅ Success' if success else '❌ Failed'}")
    
    # Test document addition
    print("\n📄 Adding documents...")
    success = store.add_documents(test_documents, test_embeddings, test_metadata)
    print(f"   Document addition: {'✅ Success' if success else '❌ Failed'}")
    
    # Test search
    print("\n🔍 Testing search...")
    query_vector = np.random.random((128,)).astype('float32')
    results = store.search_with_filters(query_vector, k=5)
    print(f"   Search results: {len(results)} documents found")
    
    for i, result in enumerate(results[:3]):
        print(f"   Result {i+1}: Doc {result.document_id}, Score: {result.score:.4f}")
    
    # Test filtered search
    print("\n🎯 Testing filtered search...")
    filtered_results = store.search_with_filters(
        query_vector, k=5, filters={'type': 'test'}
    )
    print(f"   Filtered search results: {len(filtered_results)} documents found")
    
    # Show index info
    print("\n📊 Index Information:")
    info = store.get_index_info()
    print(f"   Total vectors: {info.total_vectors}")
    print(f"   Index type: {info.index_type}")
    print(f"   Dimension: {info.dimension}")
    print(f"   Is trained: {info.is_trained}")
    print(f"   Size: {info.size_mb:.2f} MB")
    
    # Show performance stats
    print("\n⚡ Performance Statistics:")
    stats = store.get_performance_stats()
    print(f"   Total searches: {stats['total_searches']}")
    print(f"   Average search time: {stats['avg_search_time']:.4f}s")
    print(f"   Total additions: {stats['total_additions']}")
    print(f"   Average add time: {stats['avg_add_time']:.4f}s")
    
    print("\n✅ Optimized vector store test completed")
