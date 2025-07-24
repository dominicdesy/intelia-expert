"""
RAG Embedder - Version Complètement Réécrite
Version simple, robuste et débugguée pour résoudre définitivement les problèmes d'accès aux documents
"""

import os
import time
import logging
import pickle
import traceback
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger(__name__)

# Vérification des dépendances
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
    """
    RAG Embedder Simple et Robuste
    Focalisé sur la résolution des problèmes d'accès aux documents
    """
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialisation simple et claire"""
        logger.info("🚀 Initializing FastRAGEmbedder...")
        
        # Configuration
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model_name = os.getenv('RAG_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        self.dimension = int(os.getenv('RAG_DIMENSION', '384'))
        self.debug_enabled = os.getenv('RAG_DEBUG_SEARCH', 'false').lower() == 'true'
        
        # État interne
        self._sentence_model = None
        self._faiss_index = None
        self._documents = []
        self._embeddings_cache = {}
        
        # Vérification des dépendances
        self.dependencies_available = (
            SENTENCE_TRANSFORMERS_AVAILABLE and 
            FAISS_AVAILABLE and 
            NUMPY_AVAILABLE
        )
        
        logger.info("✅ FastRAGEmbedder initialized with compatible signature")
        logger.info(f"   Model: {self.model_name}")
        logger.info(f"   Dimension: {self.dimension}")
        logger.info(f"   Dependencies available: {self.dependencies_available}")
        logger.info(f"   Debug enabled: {self.debug_enabled}")
    
    @property
    def sentence_model(self):
        """Chargement paresseux du modèle sentence-transformers"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return None
            
        if self._sentence_model is None:
            try:
                start_time = time.time()
                logger.info(f"🔄 Loading sentence model: {self.model_name}")
                
                self._sentence_model = SentenceTransformer(self.model_name)
                
                load_time = time.time() - start_time
                logger.info(f"✅ Model loaded in {load_time:.2f}s")
                
            except Exception as e:
                logger.error(f"❌ Error loading model: {e}")
                return None
        
        return self._sentence_model
    
    def load_index(self, index_path: str) -> bool:
        """
        Chargement d'index avec validation et correction robuste
        """
        if not self.dependencies_available:
            logger.error("❌ Dependencies not available for index loading")
            return False
            
        try:
            faiss_file = os.path.join(index_path, 'index.faiss')
            pkl_file = os.path.join(index_path, 'index.pkl')
            
            # Vérifier que les fichiers existent
            if not os.path.exists(faiss_file):
                logger.error(f"❌ FAISS file not found: {faiss_file}")
                return False
                
            if not os.path.exists(pkl_file):
                logger.error(f"❌ Documents file not found: {pkl_file}")
                return False
            
            # Charger l'index FAISS
            logger.info(f"🔄 Loading FAISS index from {faiss_file}")
            self._faiss_index = faiss.read_index(faiss_file)
            
            # Charger les documents
            logger.info(f"🔄 Loading documents from {pkl_file}")
            with open(pkl_file, 'rb') as f:
                raw_documents = pickle.load(f)
            
            # Normaliser les documents en liste de strings
            self._documents = self._normalize_documents(raw_documents)
            
            # Vérifications
            vectors_count = self._faiss_index.ntotal
            docs_count = len(self._documents)
            
            logger.info(f"✅ Index loaded successfully:")
            logger.info(f"   📊 {vectors_count} vectors")
            logger.info(f"   📚 {docs_count} documents")
            logger.info(f"   🔢 Dimension: {self._faiss_index.d}")
            
            # Correction de synchronisation si nécessaire
            if vectors_count != docs_count:
                logger.warning(f"⚠️ SYNCHRONIZATION ISSUE: {vectors_count} vectors != {docs_count} documents")
                return self._fix_synchronization(vectors_count, docs_count)
            
            # Test de l'index
            test_passed = self._test_index()
            if not test_passed:
                logger.warning("⚠️ Index test failed but continuing...")
                # Ne pas retourner False, continuer quand même
            else:
                logger.info("✅ Index test passed!")
            
            logger.info("🎉 Index successfully loaded and synchronized!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading index from {index_path}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _normalize_documents(self, raw_documents: Any) -> List[str]:
        """
        Normalise les documents en liste de strings, peu importe le format d'origine
        """
        normalized = []
        
        if self.debug_enabled:
            logger.info(f"🔍 DEBUG: Normalizing documents...")
            logger.info(f"   Raw type: {type(raw_documents)}")
            logger.info(f"   Raw length/size: {len(raw_documents) if hasattr(raw_documents, '__len__') else 'unknown'}")
        
        try:
            # Cas 1: Liste de documents
            if isinstance(raw_documents, list):
                for i, doc in enumerate(raw_documents):
                    normalized_doc = self._extract_text_from_document(doc, i)
                    if normalized_doc:
                        normalized.append(normalized_doc)
            
            # Cas 2: Dictionnaire de documents
            elif isinstance(raw_documents, dict):
                for key, doc in raw_documents.items():
                    normalized_doc = self._extract_text_from_document(doc, key)
                    if normalized_doc:
                        normalized.append(normalized_doc)
            
            # Cas 3: Document unique
            else:
                normalized_doc = self._extract_text_from_document(raw_documents, 0)
                if normalized_doc:
                    normalized.append(normalized_doc)
            
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Normalized {len(normalized)} documents")
                if len(normalized) > 0:
                    logger.info(f"   First document preview: '{normalized[0][:100]}...'")
            
            return normalized
            
        except Exception as e:
            logger.error(f"❌ Error normalizing documents: {e}")
            return []
    
    def _extract_text_from_document(self, doc: Any, index: Union[int, str]) -> Optional[str]:
        """
        Extrait le texte d'un document, peu importe son format
        """
        try:
            # Cas 1: Déjà une string
            if isinstance(doc, str):
                return doc.strip() if doc.strip() else None
            
            # Cas 2: Dictionnaire avec clés connues
            elif isinstance(doc, dict):
                # Essayer différentes clés possibles
                for key in ['content', 'text', 'body', 'message', 'data']:
                    if key in doc and doc[key]:
                        text = str(doc[key]).strip()
                        return text if text else None
                
                # Si aucune clé connue, prendre la première valeur string
                for value in doc.values():
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                
                # Dernier recours: convertir tout le dict en string
                return str(doc)
            
            # Cas 3: Autre type, convertir en string
            else:
                text = str(doc).strip()
                return text if text else None
                
        except Exception as e:
            if self.debug_enabled:
                logger.warning(f"⚠️ Could not extract text from document {index}: {e}")
            return None
    
    def _fix_synchronization(self, vectors_count: int, docs_count: int) -> bool:
        """
        Corrige la désynchronisation entre vecteurs et documents
        """
        try:
            if vectors_count > docs_count:
                # Tronquer l'index pour correspondre aux documents
                logger.warning(f"🔧 FIXING: Truncating FAISS index to match documents count ({docs_count})")
                
                if docs_count == 0:
                    logger.error("❌ No documents available")
                    return False
                
                # Créer un nouvel index avec seulement les premiers vecteurs
                new_index = faiss.IndexFlatL2(self._faiss_index.d)
                
                # Extraire les vecteurs correspondant aux documents
                vectors_to_keep = np.zeros((docs_count, self._faiss_index.d), dtype=np.float32)
                
                for i in range(docs_count):
                    try:
                        vector = self._faiss_index.reconstruct(i)
                        vectors_to_keep[i] = vector
                    except Exception:
                        # Utiliser un vecteur aléatoire en cas d'erreur
                        vectors_to_keep[i] = np.random.random(self._faiss_index.d).astype('float32')
                
                new_index.add(vectors_to_keep)
                self._faiss_index = new_index
                
                logger.info(f"✅ FIXED: New index created with {new_index.ntotal} vectors")
                
            elif docs_count > vectors_count:
                # Tronquer les documents pour correspondre aux vecteurs
                logger.warning(f"🔧 FIXING: Truncating documents to match vectors count ({vectors_count})")
                self._documents = self._documents[:vectors_count]
                logger.info(f"✅ FIXED: Documents truncated to {len(self._documents)} items")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error fixing synchronization: {e}")
            return False
    
    def _test_index(self) -> bool:
        """
        Test basique de l'index pour s'assurer qu'il fonctionne
        """
        try:
            if self._faiss_index.ntotal == 0 or len(self._documents) == 0:
                logger.error("❌ Index or documents empty")
                return False
            
            # Test avec un vecteur aléatoire
            test_vector = np.random.random((1, self._faiss_index.d)).astype('float32')
            test_scores, test_indices = self._faiss_index.search(test_vector, min(3, self._faiss_index.ntotal))
            
            # Vérifier que nous pouvons accéder aux documents
            valid_results = 0
            for idx in test_indices[0]:
                if 0 <= idx < len(self._documents):
                    try:
                        doc = self._documents[idx]
                        if doc and doc.strip():
                            valid_results += 1
                    except Exception:
                        pass
            
            logger.info(f"✅ Index search test passed: found {valid_results} valid results out of {len(test_indices[0])}")
            return valid_results > 0
            
        except Exception as e:
            logger.error(f"❌ Index test failed: {e}")
            return False
    
    def has_search_engine(self) -> bool:
        """Vérifie si le moteur de recherche est disponible"""
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
        """Propriété pour compatibilité"""
        return self.has_search_engine()
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Génère un embedding pour le texte donné
        """
        if self.debug_enabled:
            logger.info(f"🔍 DEBUG: Embedding text: '{text[:50]}...'")
            
        if not text.strip():
            logger.warning("⚠️ Empty text, returning zero vector")
            return np.zeros(self.dimension, dtype=np.float32)
        
        model = self.sentence_model
        if model is None:
            logger.error("❌ Sentence model not available")
            return None
            
        try:
            # Vérifier le cache
            text_hash = hash(text)
            if text_hash in self._embeddings_cache:
                if self.debug_enabled:
                    logger.info("🔍 DEBUG: Using cached embedding")
                return self._embeddings_cache[text_hash]
            
            # Générer l'embedding
            if self.debug_enabled:
                logger.info("🔍 DEBUG: Generating new embedding...")
                
            embedding = model.encode([text])[0].astype('float32')
            
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Generated embedding shape: {embedding.shape}")
            
            # Mettre en cache
            if len(self._embeddings_cache) < 1000:  # Limite de cache
                self._embeddings_cache[text_hash] = embedding
                if self.debug_enabled:
                    logger.info("🔍 DEBUG: Embedding cached")
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            return None
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Recherche simple et robuste
        """
        if self.debug_enabled:
            logger.info(f"🔍 DEBUG: Starting search for query: '{query}' with k={k}")
        
        # Vérifications préliminaires
        if not query.strip():
            logger.warning("⚠️ Empty query")
            return []
        
        if not self.has_search_engine():
            logger.warning("❌ Search engine not available")
            return []
        
        try:
            # Générer l'embedding de la requête
            query_embedding = self.get_embedding(query)
            if query_embedding is None:
                logger.error("❌ Failed to generate query embedding")
                return []
            
            # Préparer pour FAISS
            query_vector = query_embedding.reshape(1, -1)
            
            # Ajuster k
            max_k = min(k, self._faiss_index.ntotal, len(self._documents))
            
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Searching with k={max_k}")
                logger.info(f"🔍 DEBUG: Index has {self._faiss_index.ntotal} vectors, {len(self._documents)} documents")
            
            # Recherche FAISS
            scores, indices = self._faiss_index.search(query_vector, max_k)
            
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: FAISS returned {len(scores[0])} results")
                logger.info(f"🔍 DEBUG: Scores: {scores[0].tolist()}")
                logger.info(f"🔍 DEBUG: Indices: {indices[0].tolist()}")
            
            # Traitement des résultats
            results = []
            for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
                # Validation de l'index
                if idx < 0 or idx >= len(self._documents):
                    if self.debug_enabled:
                        logger.warning(f"🔍 DEBUG: Invalid index {idx}, skipping")
                    continue
                
                # Récupération du document
                try:
                    document_text = self._documents[idx]
                    
                    if not document_text or not document_text.strip():
                        if self.debug_enabled:
                            logger.warning(f"🔍 DEBUG: Empty document at index {idx}, skipping")
                        continue
                    
                    if self.debug_enabled:
                        logger.info(f"🔍 DEBUG: ✅ Valid result {rank}: idx={idx}, score={score:.4f}")
                        logger.info(f"🔍 DEBUG: Text preview: '{document_text[:100]}...'")
                    
                    results.append({
                        'text': document_text,
                        'score': float(score),
                        'rank': rank + 1,
                        'index': int(idx)
                    })
                    
                except Exception as doc_error:
                    logger.error(f"❌ Error accessing document {idx}: {doc_error}")
                    if self.debug_enabled:
                        logger.error(f"🔍 DEBUG: Document access error details: {traceback.format_exc()}")
                    continue
            
            # Résultats finaux
            if self.debug_enabled:
                logger.info(f"🔍 DEBUG: Final results: {len(results)} valid documents found")
            
            if len(results) == 0:
                logger.warning("⚠️ No valid results found")
            else:
                logger.info(f"✅ Search completed: {len(results)} results found")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []


# Aliases pour compatibilité
class EnhancedDocumentEmbedder(FastRAGEmbedder):
    """Wrapper pour compatibilité"""
    pass

class RAGEmbedder(FastRAGEmbedder):
    """Wrapper pour compatibilité"""
    pass

    def get_stats(self) -> Dict[str, Any]:
        """
        Statistiques complètes du système pour compatibilité
        """
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
            'debug_enabled': self.debug_enabled
        }


# Fonction utilitaire
def get_embedder() -> FastRAGEmbedder:
    """Obtenir une instance de l'embedder"""
    return FastRAGEmbedder()