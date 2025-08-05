"""
RAG Embedder - VERSION OPTIMISÉE POUR MEILLEURS SCORES
Améliorations pour scores de similarité et normalisation des requêtes
MODIFICATION: Seuils adaptatifs pour éviter "aucun résultat trouvé"
"""

import os
import time
import pickle
import logging
import re
from typing import List, Dict, Any, Optional, Union
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class FastRAGEmbedder:
    """
    RAG Embedder optimisé avec normalisation et meilleurs scores
    NOUVEAU: Seuils adaptatifs pour éviter l'absence de résultats
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
        cache_embeddings: bool = True,
        max_workers: int = 2,
        debug: bool = True,
        similarity_threshold: float = 0.15,  # ✅ MODIFIÉ: Abaissé de 0.25 à 0.15
        normalize_queries: bool = True       # Nouvelle option de normalisation
    ):
        """
        Initialize FastRAGEmbedder with improved scoring and adaptive thresholds
        """
        self.api_key = api_key
        self.model_name = model_name
        self.cache_embeddings = cache_embeddings
        self.max_workers = max_workers
        self.debug = debug
        self.similarity_threshold = similarity_threshold
        self.normalize_queries = normalize_queries
        
        # ✅ NOUVEAU: Configuration des seuils adaptatifs
        self.threshold_config = {
            "strict": 0.25,      # Pour questions très spécifiques
            "normal": 0.15,      # Seuil par défaut (modifié de 0.25 à 0.15)
            "permissive": 0.10,  # Pour questions générales
            "fallback": 0.05     # En dernier recours
        }
        
        # Initialize storage
        self.embedding_cache = {} if cache_embeddings else None
        self.documents = []
        self.embeddings = None
        self.index = None
        self.search_engine_available = False
        
        # Query normalization patterns
        self._init_normalization_patterns()
        
        # Initialize dependencies
        self._init_dependencies()
        
        if self.debug:
            logger.info("🚀 Initializing FastRAGEmbedder (Adaptive Thresholds)...")
            logger.info(f"   Model: {self.model_name}")
            logger.info(f"   Dimension: 384")
            logger.info(f"   Dependencies available: {self._check_dependencies()}")
            logger.info(f"   Cache enabled: {self.cache_embeddings}")
            logger.info(f"   Max workers: {self.max_workers}")
            logger.info(f"   Default similarity threshold: {self.similarity_threshold}")
            logger.info(f"   Adaptive thresholds: {self.threshold_config}")
            logger.info(f"   Query normalization: {self.normalize_queries}")
            logger.info(f"   Debug enabled: {self.debug}")
    
    def _init_normalization_patterns(self):
        """Initialize patterns for query normalization"""
        self.normalization_patterns = {
            # Conversions d'unités temporelles
            'temporal_conversions': [
                (r'(\d+)\s*semaines?', lambda m: f"{int(m.group(1)) * 7} jours"),
                (r'(\d+)\s*mois', lambda m: f"{int(m.group(1)) * 30} jours"),
                (r'(\d+)j\b', r'\1 jours'),
                (r'(\d+)s\b', r'\1 semaines'),
            ],
            
            # Normalisation des termes agricoles
            'agricultural_terms': [
                (r'\bpoulets?\b', 'volaille'),
                (r'\bpoules?\b', 'volaille'),
                (r'\bcoqs?\b', 'volaille'),
                (r'\bgallines?\b', 'volaille'),
                (r'\bRoss\s*308\b', 'poulet de chair Ross 308'),
                (r'\bCobb\s*500\b', 'poulet de chair Cobb 500'),
                (r'\bbroilers?\b', 'poulet de chair'),
            ],
            
            # Normalisation des unités de poids
            'weight_conversions': [
                (r'(\d+)\s*kg\b', lambda m: f"{int(m.group(1)) * 1000} grammes"),
                (r'(\d+)\s*g\b', r'\1 grammes'),
                (r'(\d+)\s*lbs?\b', lambda m: f"{int(float(m.group(1)) * 453.592)} grammes"),
            ],
            
            # Normalisation des températures
            'temperature_conversions': [
                (r'(\d+)°?C\b', r'\1 degrés Celsius'),
                (r'(\d+)°?F\b', lambda m: f"{round((int(m.group(1)) - 32) * 5/9)} degrés Celsius"),
            ],
            
            # Synonymes et termes équivalents
            'synonyms': [
                (r'\bmort[ea]lité\b', 'mortalité taux de mortalité'),
                (r'\bcroissance\b', 'croissance développement poids'),
                (r'\balimentation\b', 'alimentation nutrition nourriture'),
                (r'\bvaccination\b', 'vaccination immunisation vaccin'),
                (r'\benvironnement\b', 'environnement conditions température humidité'),
                (r'\bdiagnostic\b', 'diagnostic symptômes maladie problème'),
            ]
        }
    
    def _normalize_query(self, query: str) -> str:
        """
        Normalize query to improve matching
        """
        if not self.normalize_queries:
            return query
        
        original_query = query
        normalized = query.lower()
        
        try:
            # Apply all normalization patterns
            for category, patterns in self.normalization_patterns.items():
                for pattern, replacement in patterns:
                    if callable(replacement):
                        # Handle lambda functions for complex conversions
                        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
                    else:
                        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
            
            # Clean up extra spaces
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            
            if self.debug and normalized != original_query.lower():
                logger.info(f"🔄 Query normalized:")
                logger.info(f"   Original: {original_query}")
                logger.info(f"   Normalized: {normalized}")
            
            return normalized
            
        except Exception as e:
            logger.error(f"❌ Error normalizing query: {e}")
            return query.lower()
    
    def _improved_similarity_score(self, distance: float) -> float:
        """
        Calculate improved similarity score from distance
        """
        # Nouvelle formule pour de meilleurs scores
        # Utilise une transformation logarithmique pour étaler les scores
        if distance <= 0:
            return 1.0
        
        # Formule améliorée qui donne de meilleurs scores
        # Utilise une courbe exponentielle inverse
        similarity = np.exp(-distance * 1.5)  # Facteur ajustable
        
        # Assure un minimum raisonnable
        similarity = max(0.0, min(1.0, similarity))
        
        return similarity
    
    def _boost_score_for_exact_matches(self, query: str, text: str, base_score: float) -> float:
        """
        Boost score for exact keyword matches
        """
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        
        # Calculate overlap
        overlap = len(query_words.intersection(text_words))
        total_query_words = len(query_words)
        
        if total_query_words == 0:
            return base_score
        
        overlap_ratio = overlap / total_query_words
        
        # Boost based on overlap
        boost_factor = 1.0 + (overlap_ratio * 0.3)  # Jusqu'à 30% de boost
        boosted_score = min(1.0, base_score * boost_factor)
        
        if self.debug and boost_factor > 1.1:
            logger.info(f"   📈 Score boosted: {base_score:.3f} → {boosted_score:.3f} (overlap: {overlap_ratio:.2f})")
        
        return boosted_score
    
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
    
    def _search_with_threshold(self, query: str, k: int, threshold: float) -> List[Dict[str, Any]]:
        """
        ✅ NOUVEAU: Recherche avec un seuil spécifique
        Méthode interne pour la recherche adaptive
        """
        if not self.has_search_engine():
            return []

        try:
            # Normalize query for better matching
            normalized_query = self._normalize_query(query)
            
            # Generate query embedding (use normalized query)
            search_query = normalized_query
            
            if self.cache_embeddings and search_query in self.embedding_cache:
                query_embedding = self.embedding_cache[search_query]
            else:
                query_embedding = self.sentence_model.encode([search_query])
                if self.cache_embeddings:
                    self.embedding_cache[search_query] = query_embedding
            
            # Ensure proper shape for FAISS
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # Search with more candidates to get better results
            k_search = min(k * 3, len(self.documents), self.index.ntotal)
            
            # Perform FAISS search
            distances, indices = self.index.search(
                query_embedding.astype('float32'), 
                k_search
            )
            
            # Process results with specified threshold
            results = []
            
            for i in range(len(distances[0])):
                distance = distances[0][i]
                idx = indices[0][i]
                
                # Validation
                if idx < 0 or idx >= len(self.documents):
                    continue
                
                # Calculate improved similarity score
                base_similarity = self._improved_similarity_score(distance)
                
                # Get document for boosting
                doc = self.documents[idx]
                
                # Boost score for exact matches
                final_similarity = self._boost_score_for_exact_matches(
                    query, doc['text'], base_similarity
                )
                
                # Apply threshold filter (use provided threshold)
                if final_similarity < threshold:
                    continue
                
                result = {
                    'text': doc['text'],
                    'score': round(final_similarity, 4),
                    'index': int(idx),
                    'metadata': doc.get('metadata', {}),
                    'rank': len(results) + 1,
                    'distance': float(distance),
                    'base_score': round(base_similarity, 4),
                    'threshold_used': threshold  # ✅ NOUVEAU: Track du seuil utilisé
                }
                
                results.append(result)
                
                # Stop when we have enough good results
                if len(results) >= k:
                    break
            
            # Sort by score (descending)
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # Update ranks
            for i, result in enumerate(results):
                result['rank'] = i + 1
            
            return results[:k]
            
        except Exception as e:
            logger.error(f"❌ Search error with threshold {threshold}: {e}")
            return []
    
    def search_with_adaptive_threshold(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        ✅ NOUVEAU: Recherche avec seuil adaptatif
        Essaie différents seuils jusqu'à obtenir des résultats
        """
        if not self.has_search_engine():
            logger.error("❌ Search engine not available")
            return []

        start_time = time.time()
        
        logger.info(f"🔍 [Adaptive] Starting adaptive threshold search")
        logger.info(f"   Query: {query[:100]}...")
        logger.info(f"   Requested k: {k}")
        
        # Essayer d'abord avec le seuil normal
        results = self._search_with_threshold(query, k, self.threshold_config["normal"])
        threshold_used = "normal"
        
        if len(results) == 0:
            logger.info("🔍 [Adaptive] Aucun résultat avec seuil normal, essai permissif")
            results = self._search_with_threshold(query, k, self.threshold_config["permissive"])
            threshold_used = "permissive"
        
        if len(results) == 0:
            logger.info("🔍 [Adaptive] Aucun résultat avec seuil permissif, essai fallback")
            results = self._search_with_threshold(query, k, self.threshold_config["fallback"])
            threshold_used = "fallback"
        
        # Si toujours aucun résultat, essayer sans seuil (prendre les meilleurs scores)
        if len(results) == 0:
            logger.info("🔍 [Adaptive] Aucun résultat avec fallback, recherche sans seuil")
            results = self._search_with_threshold(query, k, 0.0)
            threshold_used = "no_threshold"
        
        search_time = time.time() - start_time
        
        logger.info(f"✅ [Adaptive] Search completed in {search_time:.3f}s")
        logger.info(f"   Threshold used: {threshold_used} ({self.threshold_config.get(threshold_used, 0.0)})")
        logger.info(f"   Results found: {len(results)}")
        if results:
            logger.info(f"   Score range: {results[0]['score']:.3f} - {results[-1]['score']:.3f}")
            
            # Log top results
            for i, result in enumerate(results[:3]):
                logger.info(f"   #{i+1}: Score {result['score']:.3f} - {result['text'][:80]}...")
        
        return results
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        ✅ MODIFIÉ: Search for relevant documents avec fallback adaptatif
        Utilise maintenant la recherche adaptive par défaut
        """
        return self.search_with_adaptive_threshold(query, k)
    
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
            'faiss_total': self.index.ntotal if self.index else 0,
            'similarity_threshold': self.similarity_threshold,
            'threshold_config': self.threshold_config,  # ✅ NOUVEAU
            'normalize_queries': self.normalize_queries
        }
    
    def clear_cache(self):
        """Clear embedding cache"""
        if self.embedding_cache:
            cache_size = len(self.embedding_cache)
            self.embedding_cache.clear()
            logger.info(f"🗑️ Cleared {cache_size} cached embeddings")
    
    def adjust_similarity_threshold(self, new_threshold: float):
        """Adjust similarity threshold dynamically"""
        old_threshold = self.similarity_threshold
        self.similarity_threshold = max(0.0, min(1.0, new_threshold))
        # ✅ NOUVEAU: Mise à jour du seuil normal dans la config
        self.threshold_config["normal"] = self.similarity_threshold
        logger.info(f"🎯 Similarity threshold adjusted: {old_threshold:.3f} → {self.similarity_threshold:.3f}")
    
    def update_threshold_config(self, **kwargs):
        """
        ✅ NOUVEAU: Mettre à jour la configuration des seuils
        """
        for threshold_name, value in kwargs.items():
            if threshold_name in self.threshold_config:
                old_value = self.threshold_config[threshold_name]
                self.threshold_config[threshold_name] = max(0.0, min(1.0, value))
                logger.info(f"🎯 {threshold_name} threshold: {old_value:.3f} → {self.threshold_config[threshold_name]:.3f}")
            else:
                logger.warning(f"⚠️ Unknown threshold config: {threshold_name}")
    
    def debug_search(self, query: str) -> Dict[str, Any]:
        """
        Debug method to understand search issues
        """
        debug_info = {
            'query': query,
            'normalized_query': self._normalize_query(query),
            'has_search_engine': self.has_search_engine(),
            'documents_count': len(self.documents),
            'faiss_total': self.index.ntotal if self.index else 0,
            'model_name': self.model_name,
            'cache_enabled': self.cache_embeddings,
            'similarity_threshold': self.similarity_threshold,
            'threshold_config': self.threshold_config,  # ✅ NOUVEAU
            'normalize_queries': self.normalize_queries
        }
        
        if self.has_search_engine():
            try:
                normalized_query = self._normalize_query(query)
                
                # Test embedding generation
                embedding = self.sentence_model.encode([normalized_query])
                debug_info['embedding_shape'] = embedding.shape
                debug_info['embedding_generated'] = True
                
                # Test FAISS search
                if embedding.ndim == 1:
                    embedding = embedding.reshape(1, -1)
                
                distances, indices = self.index.search(embedding.astype('float32'), 5)
                debug_info['faiss_search_success'] = True
                
                # ✅ NOUVEAU: Tester avec tous les seuils
                threshold_results = {}
                for threshold_name, threshold_value in self.threshold_config.items():
                    results = self._search_with_threshold(query, 3, threshold_value)
                    threshold_results[threshold_name] = {
                        'threshold': threshold_value,
                        'results_count': len(results),
                        'top_scores': [r['score'] for r in results[:3]]
                    }
                
                debug_info['threshold_results'] = threshold_results
                
                # Analyze top 5 results without threshold
                top_results = []
                for i in range(min(5, len(distances[0]))):
                    distance = distances[0][i]
                    idx = indices[0][i]
                    
                    if idx >= 0 and idx < len(self.documents):
                        base_score = self._improved_similarity_score(distance)
                        boosted_score = self._boost_score_for_exact_matches(
                            query, self.documents[idx]['text'], base_score
                        )
                        
                        # ✅ NOUVEAU: Check contre tous les seuils
                        threshold_checks = {}
                        for name, value in self.threshold_config.items():
                            threshold_checks[name] = boosted_score >= value
                        
                        top_results.append({
                            'index': int(idx),
                            'distance': float(distance),
                            'base_score': round(base_score, 4),
                            'boosted_score': round(boosted_score, 4),
                            'threshold_checks': threshold_checks,
                            'text_preview': self.documents[idx]['text'][:100]
                        })
                
                debug_info['top_results'] = top_results
                    
            except Exception as e:
                debug_info['error'] = str(e)
        
        return debug_info

# =============================================================================
# COMPATIBILITY FUNCTIONS WITH IMPROVED DEFAULTS
# =============================================================================

def create_optimized_embedder(**kwargs) -> FastRAGEmbedder:
    """Create an optimized embedder instance with better scoring and adaptive thresholds"""
    return FastRAGEmbedder(
        cache_embeddings=True,
        max_workers=2,
        debug=kwargs.get('debug', True),
        similarity_threshold=kwargs.get('similarity_threshold', 0.15),  # ✅ MODIFIÉ: 0.25 → 0.15
        normalize_queries=kwargs.get('normalize_queries', True),
        **kwargs
    )

# Legacy compatibility
def FastRAGEmbedder_v1(*args, **kwargs):
    """Backward compatibility wrapper with improved defaults"""
    # Apply improved defaults if not specified
    if 'similarity_threshold' not in kwargs:
        kwargs['similarity_threshold'] = 0.15  # ✅ MODIFIÉ: 0.25 → 0.15
    if 'normalize_queries' not in kwargs:
        kwargs['normalize_queries'] = True
    
    return FastRAGEmbedder(*args, **kwargs)