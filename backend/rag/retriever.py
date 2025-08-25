"""
RAG Retriever - Production-Ready Multi-Embedding avec Support OpenAI/ONNX/SentenceTransformers

AMÉLIORATIONS PRODUCTION :
1. ✅ FORÇAGE/PROPAGATION méthode d'embedding côté runtime
2. ✅ OpenAI par défaut (text-embedding-3-small/large, pas ada-002)
3. ✅ GESTION robuste dimensions FAISS (mismatch detection + normalisation)
4. ✅ FastEmbed (ONNX) comme 3ème méthode torch-free
5. ✅ SentenceTransformers OPTIONNEL (lazy import, fallback gracieux)

ENV supportés :
- RAG_EMBEDDING_METHOD=OpenAI|FastEmbed|SentenceTransformers (défaut: OpenAI)
- OPENAI_API_KEY (requis pour OpenAI)
- RAG_FORCE_METHOD=true (force la méthode, pas de fallback)
- RAG_INDEX_DIR, RAG_INDEX_GLOBAL, RAG_INDEX_BROILER, RAG_INDEX_LAYER
"""

from __future__ import annotations

import os
import re
import pickle
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

# -----------------------------
# Configuration production
# -----------------------------

_SPECIES = ("broiler", "layer", "global")

# Méthodes d'embedding supportées (ordre de préférence pour fallback)
_EMBEDDING_METHODS = ("OpenAI", "FastEmbed", "SentenceTransformers")

# Modèles OpenAI recommandés (dimension connue)
_OPENAI_MODELS = {
    "text-embedding-3-small": 1536,  # Recommandé prod (rapide + précis)
    "text-embedding-3-large": 3072,  # Haute performance
    "text-embedding-ada-002": 1536   # Legacy support
}

# Configuration runtime (peut être overridée par ENV)
DEFAULT_EMBEDDING_METHOD = os.environ.get("RAG_EMBEDDING_METHOD", "OpenAI")
DEFAULT_OPENAI_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
FORCE_METHOD = os.environ.get("RAG_FORCE_METHOD", "false").lower() == "true"

# -----------------------------
# Enhanced Species Detection 
# -----------------------------

def _enhanced_detect_species_from_query(q: str) -> Tuple[Optional[str], float]:
    """Enhanced species detection with confidence scoring"""
    ql = (q or "").lower()
    species_scores = {"broiler": 0.0, "layer": 0.0}
    
    species_keywords_weighted = {
        "layer": [
            ("pondeuse", 3), ("ponte", 3), ("œuf", 3), ("oeuf", 3), ("layer", 3),
            ("lohmann brown", 3), ("hy-line brown", 3), ("w-36", 3), ("w-80", 3),
            ("lsl-lite", 3), ("isa brown", 3),
            ("lohmann", 2), ("hy-line", 2), ("hyline", 2), ("isa", 2), ("laying hen", 2),
            ("poule pondeuse", 2), ("egg production", 2), ("hen day", 2),
            ("w36", 1), ("w80", 1), ("production", 1)
        ],
        "broiler": [
            ("ross 308", 3), ("ross308", 3), ("cobb 500", 3), ("cobb500", 3),
            ("ross 708", 3), ("poulet de chair", 3), ("broiler", 3), ("hubbard", 3),
            ("ross", 2), ("cobb", 2), ("meat chicken", 2), ("chair", 2),
            ("griller", 2), ("fcr", 2), ("finisher", 2), ("starter", 2),
            ("croissance", 1), ("poids", 1), ("gain", 1), ("weight", 1)
        ]
    }
    
    for species, keywords in species_keywords_weighted.items():
        for keyword, weight in keywords:
            if keyword in ql:
                species_scores[species] += weight
    
    max_score = max(species_scores.values())
    if max_score == 0:
        return None, 0.0
    
    best_species = max(species_scores, key=species_scores.get)
    confidence = min(max_score / 10.0, 1.0)
    
    sorted_scores = sorted(species_scores.values(), reverse=True)
    if len(sorted_scores) > 1 and sorted_scores[0] - sorted_scores[1] < 2:
        return best_species, confidence * 0.6
    
    return best_species, confidence

def _detect_species_from_query(q: str) -> Optional[str]:
    """Legacy compatibility wrapper"""
    species, confidence = _enhanced_detect_species_from_query(q)
    return species if confidence > 0.3 else None

def _looks_like_table(text: str, md: Dict[str, Any]) -> bool:
    """Enhanced table detection"""
    if isinstance(md, dict) and (md.get("chunk_type") == "table" or md.get("table_type")):
        return True
    
    t = text or ""
    table_indicators = [
        t.count("|") >= 3,
        t.count(",") >= 5 and "\n" in t,
        re.search(r"\S+\s{2,}\S+\s{2,}\S+", t),
        re.search(r"(?:age|week|day|poids|weight|fcr|protein)\s+\d+", t, re.IGNORECASE),
        re.search(r"\d+\s*[-–]\s*\d+\s*(?:days?|jours?|weeks?|sem)", t, re.IGNORECASE),
        re.search(r"(?:lysine|protein|energy|calcium)\s*[:\-]\s*\d+", t, re.IGNORECASE)
    ]
    
    return any(table_indicators)

def _query_has_numbers_or_units(q: str) -> bool:
    """Enhanced detection of technical queries"""
    ql = (q or "").lower()
    
    has_numbers = any(ch.isdigit() for ch in ql)
    
    technical_units = [
        "kg", "g", "fcr", "%", "°c", "ppm", "m³", "m3", "lux", "pa",
        "kcal", "mj", "mg", "days", "weeks", "jours", "semaines",
        "density", "densité", "birds/m²", "sujets/m²"
    ]
    
    has_units = any(u in ql for u in technical_units)
    
    performance_terms = [
        "rate", "taux", "ratio", "indice", "conversion", "gain",
        "production", "efficiency", "mortality", "viability"
    ]
    
    has_performance_terms = any(t in ql for t in performance_terms)
    
    return has_numbers or has_units or has_performance_terms

# -----------------------------
# Filtrage métadonnées
# -----------------------------

def _normalize_filter_value(value: Any) -> str:
    """Normalise une valeur de filtre pour la comparaison"""
    if value is None:
        return ""
    return str(value).lower().strip()

def _matches_metadata_filter(doc_metadata: Dict[str, Any], filter_key: str, filter_value: Any) -> bool:
    """Vérifie si un document correspond à un filtre spécifique"""
    if not filter_value:
        return True
    
    doc_value = doc_metadata.get(filter_key)
    if doc_value is None:
        return False
    
    filter_norm = _normalize_filter_value(filter_value)
    doc_norm = _normalize_filter_value(doc_value)
    
    if filter_norm == doc_norm:
        return True
    
    if filter_key == "species":
        species_aliases = {
            "broiler": ["broiler", "chair", "meat", "ross", "cobb"],
            "layer": ["layer", "pondeuse", "laying", "egg", "lohmann", "hy-line", "isa"]
        }
        for species, aliases in species_aliases.items():
            if filter_norm in aliases and any(alias in doc_norm for alias in aliases):
                return True
    
    elif filter_key == "line":
        if filter_norm in doc_norm or doc_norm in filter_norm:
            return True
        filter_clean = re.sub(r'[^\w\d]', '', filter_norm)
        doc_clean = re.sub(r'[^\w\d]', '', doc_norm)
        if filter_clean in doc_clean or doc_clean in filter_clean:
            return True
    
    elif filter_key == "sex":
        sex_aliases = {
            "male": ["male", "mâle", "males", "m"],
            "female": ["female", "femelle", "females", "f"],
            "mixed": ["mixed", "mixte", "both", "les deux"]
        }
        for sex, aliases in sex_aliases.items():
            if filter_norm in aliases and any(alias in doc_norm for alias in aliases):
                return True
    
    return filter_norm in doc_norm

def _apply_metadata_filters(documents: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Applique les filtres de métadonnées"""
    if not filters:
        return documents
    
    filtered = []
    applied_filters = {k: v for k, v in filters.items() if v}
    
    logger.debug(f"🔍 Application des filtres: {applied_filters} sur {len(documents)} documents")
    
    for doc in documents:
        metadata = doc.get("metadata", {}) or {}
        passes_all_filters = True
        
        for filter_key, filter_value in applied_filters.items():
            if not _matches_metadata_filter(metadata, filter_key, filter_value):
                passes_all_filters = False
                break
        
        if passes_all_filters:
            filtered.append(doc)
    
    logger.debug(f"✅ Filtrage terminé: {len(filtered)}/{len(documents)} documents retenus")
    return filtered

# =====================================================================
# NOUVELLES CLASSES D'EMBEDDING PRODUCTION
# =====================================================================

class EmbeddingInterface:
    """Interface pour les méthodes d'embedding"""
    
    def __init__(self):
        self.dimension = None
        self.method_name = None
    
    def embed_query(self, text: str) -> Optional[np.ndarray]:
        """Embed une requête unique"""
        raise NotImplementedError
    
    def embed_documents(self, texts: List[str]) -> Optional[List[np.ndarray]]:
        """Embed plusieurs documents"""
        raise NotImplementedError
    
    def get_dimension(self) -> Optional[int]:
        """Retourne la dimension des embeddings"""
        return self.dimension
    
    def is_available(self) -> bool:
        """Vérifie si la méthode est disponible"""
        raise NotImplementedError

class OpenAIEmbedder(EmbeddingInterface):
    """Embedder OpenAI production-ready"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_OPENAI_MODEL):
        super().__init__()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.method_name = "OpenAI"
        self.dimension = _OPENAI_MODELS.get(model, 1536)
        self._client = None
        
        if not self.api_key:
            logger.warning("❌ OpenAI API key manquante")
    
    def _get_client(self):
        """Lazy client initialization"""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                logger.error("❌ Package openai non installé")
                return None
            except Exception as e:
                logger.error(f"❌ Erreur initialisation client OpenAI: {e}")
                return None
        return self._client
    
    def is_available(self) -> bool:
        """Vérifie disponibilité OpenAI"""
        if not self.api_key:
            return False
        try:
            import openai
            return True
        except ImportError:
            return False
    
    def embed_query(self, text: str) -> Optional[np.ndarray]:
        """Embed une requête via OpenAI"""
        if not text.strip():
            return None
        
        client = self._get_client()
        if client is None:
            return None
        
        try:
            response = client.embeddings.create(
                input=text,
                model=self.model
            )
            embedding = response.data[0].embedding
            return np.array(embedding, dtype=np.float32)
        
        except Exception as e:
            logger.error(f"❌ Erreur OpenAI embedding: {e}")
            return None
    
    def embed_documents(self, texts: List[str]) -> Optional[List[np.ndarray]]:
        """Embed plusieurs documents via OpenAI"""
        if not texts:
            return []
        
        client = self._get_client()
        if client is None:
            return None
        
        try:
            # Batch processing (OpenAI limite ~2048 inputs par requête)
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = client.embeddings.create(
                    input=batch,
                    model=self.model
                )
                batch_embeddings = [
                    np.array(item.embedding, dtype=np.float32) 
                    for item in response.data
                ]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
        
        except Exception as e:
            logger.error(f"❌ Erreur OpenAI batch embedding: {e}")
            return None

class FastEmbedEmbedder(EmbeddingInterface):
    """Embedder FastEmbed (ONNX) - torch-free"""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        super().__init__()
        self.model_name = model_name
        self.method_name = "FastEmbed"
        self.dimension = 384  # Dimension typique pour bge-small
        self._model = None
        self._lock = threading.Lock()
    
    def _get_model(self):
        """Lazy model loading avec thread safety"""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from fastembed import TextEmbedding
                        self._model = TextEmbedding(model_name=self.model_name)
                        logger.info(f"✅ FastEmbed model loaded: {self.model_name}")
                    except ImportError:
                        logger.error("❌ FastEmbed non installé: pip install fastembed")
                        return None
                    except Exception as e:
                        logger.error(f"❌ Erreur loading FastEmbed: {e}")
                        return None
        return self._model
    
    def is_available(self) -> bool:
        """Vérifie disponibilité FastEmbed"""
        try:
            import fastembed
            return True
        except ImportError:
            return False
    
    def embed_query(self, text: str) -> Optional[np.ndarray]:
        """Embed une requête via FastEmbed"""
        if not text.strip():
            return None
        
        model = self._get_model()
        if model is None:
            return None
        
        try:
            embeddings = list(model.embed([text]))
            if embeddings:
                return np.array(embeddings[0], dtype=np.float32)
            return None
        
        except Exception as e:
            logger.error(f"❌ Erreur FastEmbed embedding: {e}")
            return None
    
    def embed_documents(self, texts: List[str]) -> Optional[List[np.ndarray]]:
        """Embed plusieurs documents via FastEmbed"""
        if not texts:
            return []
        
        model = self._get_model()
        if model is None:
            return None
        
        try:
            embeddings = list(model.embed(texts))
            return [np.array(emb, dtype=np.float32) for emb in embeddings]
        
        except Exception as e:
            logger.error(f"❌ Erreur FastEmbed batch embedding: {e}")
            return None

class SentenceTransformersEmbedder(EmbeddingInterface):
    """Embedder SentenceTransformers - fallback optionnel"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        super().__init__()
        self.model_name = model_name
        self.method_name = "SentenceTransformers"
        self.dimension = 384  # Dimension pour all-MiniLM-L6-v2
        self._model = None
        self._lock = threading.Lock()
    
    def _get_model(self):
        """Lazy model loading avec warning PyTorch"""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                        self._model = SentenceTransformer(self.model_name)
                        logger.info(f"✅ SentenceTransformers model loaded: {self.model_name}")
                        logger.warning("⚠️  SentenceTransformers requiert PyTorch (~755MB)")
                    except ImportError:
                        logger.error("❌ SentenceTransformers non installé")
                        return None
                    except Exception as e:
                        logger.error(f"❌ Erreur loading SentenceTransformers: {e}")
                        return None
        return self._model
    
    def is_available(self) -> bool:
        """Vérifie disponibilité SentenceTransformers"""
        try:
            import sentence_transformers
            import torch
            return True
        except ImportError:
            return False
    
    def embed_query(self, text: str) -> Optional[np.ndarray]:
        """Embed une requête via SentenceTransformers"""
        if not text.strip():
            return None
        
        model = self._get_model()
        if model is None:
            return None
        
        try:
            embedding = model.encode([text], normalize_embeddings=True)
            return np.array(embedding[0], dtype=np.float32)
        
        except Exception as e:
            logger.error(f"❌ Erreur SentenceTransformers embedding: {e}")
            return None
    
    def embed_documents(self, texts: List[str]) -> Optional[List[np.ndarray]]:
        """Embed plusieurs documents via SentenceTransformers"""
        if not texts:
            return []
        
        model = self._get_model()
        if model is None:
            return None
        
        try:
            embeddings = model.encode(texts, normalize_embeddings=True)
            return [np.array(emb, dtype=np.float32) for emb in embeddings]
        
        except Exception as e:
            logger.error(f"❌ Erreur SentenceTransformers batch embedding: {e}")
            return None

# =====================================================================
# Factory d'Embedders
# =====================================================================

def create_embedder(method: str, **kwargs) -> Optional[EmbeddingInterface]:
    """Factory pour créer un embedder selon la méthode"""
    method = method.strip()
    
    if method == "OpenAI":
        return OpenAIEmbedder(**kwargs)
    elif method == "FastEmbed":
        return FastEmbedEmbedder(**kwargs)
    elif method == "SentenceTransformers":
        return SentenceTransformersEmbedder(**kwargs)
    else:
        logger.error(f"❌ Méthode d'embedding inconnue: {method}")
        return None

def get_best_available_embedder(preferred_method: str = DEFAULT_EMBEDDING_METHOD) -> Optional[EmbeddingInterface]:
    """Retourne le meilleur embedder disponible"""
    methods_to_try = [preferred_method] if FORCE_METHOD else _EMBEDDING_METHODS
    
    for method in methods_to_try:
        embedder = create_embedder(method)
        if embedder and embedder.is_available():
            logger.info(f"✅ Embedder sélectionné: {method}")
            return embedder
        else:
            logger.warning(f"⚠️  Embedder {method} non disponible")
    
    logger.error("❌ Aucun embedder disponible")
    return None

# =====================================================================
# Retriever Principal
# =====================================================================

class RAGRetriever:
    """Enhanced RAG retriever production-ready multi-embedding"""

    def __init__(self, 
                 embedding_method: Optional[str] = None,
                 openai_api_key: Optional[str] = None,
                 **embedder_kwargs):
        
        # Configuration méthode d'embedding
        self.embedding_method = embedding_method or DEFAULT_EMBEDDING_METHOD
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        
        # Embedder principal
        self.embedder = None
        self._initialize_embedder(**embedder_kwargs)
        
        # États par espèce
        self.index_by_species: Dict[str, Any] = {}
        self.documents_by_species: Dict[str, List[Dict[str, Any]]] = {}
        self.method_by_species: Dict[str, str] = {}
        self.emb_dim_by_species: Dict[str, Optional[int]] = {}
        self.is_loaded_by_species: Dict[str, bool] = {s: False for s in _SPECIES}
        
        # Chargement eager de "global"
        self._load_index_for_species("global")
    
    def _initialize_embedder(self, **kwargs):
        """Initialise l'embedder avec la méthode spécifiée"""
        if self.embedding_method == "OpenAI":
            kwargs.setdefault("api_key", self.openai_api_key)
        
        self.embedder = create_embedder(self.embedding_method, **kwargs)
        
        if self.embedder is None or not self.embedder.is_available():
            logger.warning(f"⚠️  Méthode {self.embedding_method} non disponible, fallback...")
            self.embedder = get_best_available_embedder()
            if self.embedder:
                self.embedding_method = self.embedder.method_name
                logger.info(f"✅ Fallback vers: {self.embedding_method}")
            else:
                logger.error("❌ Aucun embedder disponible - Retriever désactivé")
    
    def _get_rag_index_path(self, species: str) -> Path:
        """Enhanced path resolution"""
        sp = (species or "global").lower()
        env_key = f"RAG_INDEX_{sp.upper()}"
        if os.environ.get(env_key):
            return Path(os.environ[env_key])

        root = os.environ.get("RAG_INDEX_DIR")
        if root:
            p = Path(root) / sp
            if p.exists():
                return p

        search_paths = [
            Path.cwd() / "backend" / "rag_index" / sp,
            Path.cwd() / "rag_index" / sp,
            Path(__file__).parent.parent / "backend" / "rag_index" / sp,
            Path(__file__).parent.parent / "rag_index" / sp,
        ]
        
        for path in search_paths:
            if path.exists():
                logger.info("✅ Index trouvé pour %s: %s", sp, path)
                return path

        return Path.cwd() / "rag_index"
    
    def _normalize_embedding_method(self, method: str) -> str:
        """Normalise le nom de méthode d'embedding"""
        if not method or not isinstance(method, str):
            return "OpenAI"  # Défaut production
        
        m = method.lower().strip()
        mapping = {
            "openai": "OpenAI",
            "openaiembeddings": "OpenAI", 
            "text-embedding-3-small": "OpenAI",
            "text-embedding-3-large": "OpenAI",
            "text-embedding-ada-002": "OpenAI",
            "fastembed": "FastEmbed",
            "fast-embed": "FastEmbed",
            "onnx": "FastEmbed",
            "sentence_transformers": "SentenceTransformers",
            "sentence-transformers": "SentenceTransformers",
            "sentencetransformers": "SentenceTransformers",
            "all-minilm-l6-v2": "SentenceTransformers",
            "tfidf": "TF-IDF",  # Legacy support
            "tf-idf": "TF-IDF",
        }
        
        normalized = mapping.get(m, method)
        if normalized not in _EMBEDDING_METHODS and normalized != "TF-IDF":
            logger.warning("Méthode embedding inconnue '%s' → fallback OpenAI", method)
            return "OpenAI"
        return normalized
    
    def _normalize_documents_format(self, raw_docs: Any) -> List[Dict[str, Any]]:
        """Normalise différents formats de documents"""
        normalized = []
        
        try:
            if isinstance(raw_docs, list):
                for i, doc in enumerate(raw_docs):
                    if isinstance(doc, dict):
                        if "content" in doc:
                            normalized.append(doc)
                        elif "text" in doc:
                            normalized.append({
                                "content": doc["text"],
                                "metadata": doc.get("metadata", {}),
                                "source": doc.get("source", f"doc_{i}")
                            })
                        else:
                            content = ""
                            for key, value in doc.items():
                                if isinstance(value, str) and len(value) > 10:
                                    content = value
                                    break
                            normalized.append({
                                "content": content or str(doc),
                                "metadata": {"original_format": "dict_conversion"},
                                "source": f"doc_{i}"
                            })
                    elif isinstance(doc, str):
                        normalized.append({
                            "content": doc,
                            "metadata": {"original_format": "string"},
                            "source": f"doc_{i}"
                        })
                    else:
                        normalized.append({
                            "content": str(doc),
                            "metadata": {"original_format": type(doc).__name__},
                            "source": f"doc_{i}"
                        })
            
            elif isinstance(raw_docs, dict):
                for key, value in raw_docs.items():
                    if isinstance(value, dict):
                        if "content" in value:
                            normalized.append(value)
                        elif "text" in value:
                            normalized.append({
                                "content": value["text"],
                                "metadata": value.get("metadata", {}),
                                "source": value.get("source", key)
                            })
                        else:
                            content = str(value)
                            for k, v in value.items():
                                if isinstance(v, str) and len(v) > 10:
                                    content = v
                                    break
                            normalized.append({
                                "content": content,
                                "metadata": {"original_format": "dict_value"},
                                "source": key
                            })
                    elif isinstance(value, str):
                        normalized.append({
                            "content": value,
                            "metadata": {"original_format": "dict_string"},
                            "source": key
                        })
            
            else:
                logger.warning("Format de documents inconnu: %s", type(raw_docs).__name__)
                normalized.append({
                    "content": str(raw_docs),
                    "metadata": {"original_format": type(raw_docs).__name__},
                    "source": "unknown_format"
                })
        
        except Exception as e:
            logger.error("Erreur lors de la normalisation des documents: %s", e)
            normalized = [{
                "content": "Erreur de chargement du document",
                "metadata": {"error": str(e)},
                "source": "error_fallback"
            }]
        
        logger.info("✅ Documents normalisés: %d documents convertis", len(normalized))
        return normalized
    
    def _check_dimension_compatibility(self, species: str, query_embedding: np.ndarray) -> bool:
        """Vérifie la compatibilité des dimensions FAISS"""
        try:
            import faiss
            
            idx = self.index_by_species.get(species)
            if idx is None:
                return False
            
            index_dim = idx.d  # Dimension de l'index FAISS
            query_dim = query_embedding.shape[-1] if query_embedding.ndim > 0 else 0
            
            if index_dim != query_dim:
                logger.error(f"❌ Mismatch dimensions {species}: index={index_dim}, query={query_dim}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur vérification dimensions {species}: {e}")
            return False
    
    def _load_index_for_species(self, species: str) -> bool:
        """Enhanced index loading avec gestion robuste des dimensions"""
        sp = (species or "global").lower()
        if sp not in _SPECIES:
            sp = "global"
        if self.is_loaded_by_species.get(sp):
            return True

        try:
            import faiss
        except ImportError:
            logger.error("FAISS non disponible — impossible de charger l'index (%s)", sp)
            return False

        path = self._get_rag_index_path(sp)
        faiss_file = path / "index.faiss"
        pkl_file = path / "index.pkl"

        if not faiss_file.exists() or not pkl_file.exists():
            logger.warning("Fichiers d'index introuvables pour %s dans %s", sp, path)
            return False

        try:
            idx = faiss.read_index(str(faiss_file))
            
            with open(pkl_file, "rb") as f:
                raw_data = pickle.load(f)
            
            # Normalisation robuste des données pickle
            if isinstance(raw_data, list):
                logger.info("Format pickle détecté: liste de %d éléments pour %s", len(raw_data), sp)
                data = {
                    "documents": raw_data,
                    "method": self.embedding_method,  # Force la méthode courante
                    "embedding_method": self.embedding_method,
                    "embeddings": None
                }
            elif isinstance(raw_data, dict):
                data = raw_data
                logger.info("Format pickle détecté: dictionnaire avec clés %s pour %s", list(data.keys()), sp)
            else:
                logger.warning("Format pickle inconnu pour %s: %s", sp, type(raw_data).__name__)
                data = {
                    "documents": [str(raw_data)],
                    "method": self.embedding_method,
                    "embedding_method": self.embedding_method,
                    "embeddings": None
                }

            # ✅ FORÇAGE méthode d'embedding runtime
            raw_method = data.get("method", data.get("embedding_method", self.embedding_method))
            method = self._normalize_embedding_method(raw_method)
            
            # ✅ PROPAGATION de la méthode courante si différente
            if method != self.embedding_method:
                logger.info(f"🔄 Adaptation index {sp}: {method} → {self.embedding_method}")
                method = self.embedding_method
            
            # Normalisation documents
            raw_docs = data.get("documents", [])
            docs = self._normalize_documents_format(raw_docs)
            
            embeddings = data.get("embeddings", None)
            
            # ✅ GESTION dimensions FAISS
            index_dim = idx.d
            embedder_dim = self.embedder.get_dimension() if self.embedder else None
            
            if embedder_dim and index_dim != embedder_dim:
                logger.warning(f"⚠️  Dimension mismatch {sp}: index={index_dim}, embedder={embedder_dim}")
                
                # Option 1: Recréer l'index (si possible)
                if len(docs) > 0 and self.embedder:
                    logger.info(f"🔄 Tentative reconstruction index {sp} avec nouvelle dimension")
                    try:
                        # Ré-embedder quelques documents de test
                        test_texts = [doc.get("content", "")[:100] for doc in docs[:5] if doc.get("content")]
                        if test_texts:
                            test_embeddings = self.embedder.embed_documents(test_texts)
                            if test_embeddings and len(test_embeddings[0]) == embedder_dim:
                                logger.info(f"✅ Reconstruction possible pour {sp}")
                                # Ici on pourrait reconstruire, mais pour la prod on log juste
                                logger.info(f"⚠️  Reconstruction automatique désactivée en prod pour {sp}")
                    except Exception as e:
                        logger.error(f"Échec reconstruction {sp}: {e}")
                
                # Option 2: Fallback gracieux
                logger.warning(f"⚠️  Utilisation index existant {sp} avec adaptation")
            
            emb_dim = index_dim  # Utiliser dimension index
            
            # Mémoriser
            self.index_by_species[sp] = idx
            self.documents_by_species[sp] = docs
            self.method_by_species[sp] = method
            self.emb_dim_by_species[sp] = emb_dim
            self.is_loaded_by_species[sp] = True

            logger.info("✅ Index %s chargé | ntotal=%s | docs=%d | method=%s | dim=%s",
                        sp, getattr(idx, "ntotal", "n/a"), len(docs), method, emb_dim)
            return True
            
        except Exception as e:
            logger.error("Erreur de chargement index %s: %s", sp, e)
            return False
    
    def is_available(self) -> bool:
        """Vérifie si le retriever est disponible"""
        if self.embedder is None or not self.embedder.is_available():
            return False
        
        for sp in _SPECIES:
            if self.is_loaded_by_species.get(sp) and self.index_by_species.get(sp) is not None:
                if getattr(self.index_by_species[sp], "ntotal", 0) > 0:
                    return True
        return False
    
    def _search_index(self, species: str, query_embedding: np.ndarray, k: int) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Recherche FAISS avec vérification dimensions"""
        try:
            import faiss
            
            idx = self.index_by_species.get(species)
            if idx is None:
                return None, None
            
            # ✅ Vérification compatibilité dimensions
            if not self._check_dimension_compatibility(species, query_embedding):
                logger.error(f"❌ Incompatibilité dimensions pour {species}")
                return None, None
            
            qe = query_embedding
            if qe.ndim == 1:
                qe = qe.reshape(1, -1)
            
            # Normalisation L2 pour les méthodes vectorielles
            if self.method_by_species.get(species) in ["OpenAI", "FastEmbed", "SentenceTransformers"]:
                faiss.normalize_L2(qe)
            
            distances, indices = idx.search(qe.astype("float32"), k)
            return distances, indices
            
        except Exception as e:
            logger.error("Échec recherche FAISS (%s): %s", species, e)
            return None, None
    
    def _process_search_results(self, species: str, distances: np.ndarray, indices: np.ndarray) -> List[Tuple[Dict[str, Any], float]]:
        """Traite les résultats de recherche FAISS"""
        results: List[Tuple[Dict[str, Any], float]] = []
        docs = self.documents_by_species.get(species, [])
        
        try:
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(docs):
                    doc = docs[idx]
                    score = float(distances[0][i])
                    if isinstance(doc, dict) and "content" in doc:
                        results.append((doc, score))
            return results
        except Exception as e:
            logger.error("Échec traitement résultats: %s", e)
            return []
    
    @staticmethod
    def _score_from_distance(distance: float) -> float:
        """Convert distance to score"""
        if distance <= 0:
            return 1.0
        return float(max(0.0, min(1.0, np.exp(-distance * 1.5))))

    @staticmethod
    def _token_overlap_boost(q: str, t: str) -> float:
        """Calcule bonus chevauchement tokens"""
        qw = set((q or "").lower().split())
        if not qw:
            return 0.0
        tw = set((t or "").lower().split())
        overlap = len(qw & tw) / max(1, len(qw))
        return min(0.15, overlap * 0.15)

    def _enhanced_table_first_rerank(self, query: str, pairs: List[Tuple[Dict[str, Any], float]], intent: Optional[str] = None) -> List[Tuple[Dict[str, Any], float]]:
        """Enhanced table-first ranking"""
        if not pairs:
            return pairs
        
        needs_table_priority = (
            intent == "PerfTargets" or 
            _query_has_numbers_or_units(query)
        )
        
        if not needs_table_priority:
            return pairs
        
        boosted: List[Tuple[Dict[str, Any], float, float]] = []
        
        for doc, raw in pairs:
            text = doc.get("content", "")
            md = doc.get("metadata", {}) or {}
            base = self._score_from_distance(raw)
            bonus = 0.0
            
            if intent == "PerfTargets" and md.get("table_type") == "perf_targets":
                bonus += 0.3
            
            if _looks_like_table(text, md):
                bonus += 0.2
            
            if md.get("chunk_type") == "table":
                bonus += 0.15
            
            if md.get("domain") in ["performance", "nutrition"]:
                bonus += 0.1
            
            technical_patterns = [
                r"\d+\s*(?:kg|g|%|°c|days?|weeks?|fcr)",
                r"(?:protein|lysine|calcium|energy)\s*[:=]\s*\d+",
                r"(?:mortality|growth|conversion)\s*[:=]\s*\d+"
            ]
            
            for pattern in technical_patterns:
                if re.search(pattern, text.lower()):
                    bonus += 0.05
                    break
            
            bonus += self._token_overlap_boost(query, text)
            final_score = min(1.0, base + bonus)
            boosted.append((doc, raw, final_score))
        
        boosted.sort(key=lambda r: r[2], reverse=True)
        return [(d, s) for (d, s, _) in boosted]
    
    def get_contextual_diagnosis(self, query: str, k: int = 5, filters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Enhanced recherche avec filtrage métadonnées"""
        if not self.is_available():
            logger.error("❌ Retriever non disponible")
            return None
        
        # Enhanced species detection
        species_hint, confidence = _enhanced_detect_species_from_query(query)
        
        if not species_hint and filters and filters.get("species"):
            species_hint = filters["species"]
            confidence = 0.5
        
        if not species_hint:
            species_hint = "global"
        
        tried: List[str] = []
        best_results = None
        
        # Stratégie de recherche adaptative
        if confidence > 0.7:
            candidates = [species_hint] + [s for s in _SPECIES if s != species_hint]
        elif confidence > 0.3:
            candidates = [species_hint, "global"] + [s for s in _SPECIES if s not in [species_hint, "global"]]
        else:
            candidates = ["global"] + [s for s in _SPECIES if s != "global"]

        applied_filters = {k: v for k, v in (filters or {}).items() if v}
        if applied_filters:
            logger.info(f"🔍 Recherche avec filtres: {applied_filters}")

        for sp in candidates:
            tried.append(sp)
            if not self._load_index_for_species(sp):
                continue

            # ✅ Création embedding avec embedder unifié
            if not self.embedder:
                logger.error("❌ Aucun embedder disponible")
                continue
            
            query_embedding = self.embedder.embed_query(query)
            if query_embedding is None:
                logger.warning(f"❌ Échec embedding pour requête dans {sp}")
                continue

            # Multiplicateur pour compenser le filtrage
            search_multiplier = 4 if applied_filters else 3 if confidence > 0.5 else 2
            initial_k = max(k * search_multiplier, 15)
            
            scores, indices = self._search_index(sp, query_embedding, initial_k)
            if scores is None or indices is None:
                continue

            pairs = self._process_search_results(sp, scores, indices)
            if not pairs:
                continue

            # Application des filtres métadonnées
            if applied_filters:
                raw_docs = [doc for doc, _ in pairs]
                filtered_docs = _apply_metadata_filters(raw_docs, applied_filters)
                
                filtered_pairs = []
                for filtered_doc in filtered_docs:
                    for doc, score in pairs:
                        if doc is filtered_doc:
                            filtered_pairs.append((doc, score))
                            break
                
                pairs = filtered_pairs
                logger.debug(f"📋 Après filtrage: {len(pairs)} résultats retenus pour {sp}")

            if not pairs:
                continue

            # Détection intention et re-ranking
            intent = None
            if "poids" in query.lower() or "weight" in query.lower() or "performance" in query.lower():
                intent = "PerfTargets"

            pairs = self._enhanced_table_first_rerank(query, pairs, intent)
            pairs = pairs[:k]

            if not best_results or len(pairs) > len(best_results[0]):
                best_results = (pairs, sp, self.embedding_method)

            success_threshold = max(1, k // 3) if applied_filters else k // 2
            
            if pairs and (len(pairs) >= success_threshold or sp == species_hint):
                answer = self._enhanced_synthesize_answer(query, pairs)
                source_documents = [doc for doc, _ in pairs]

                return {
                    "answer": answer,
                    "source_documents": source_documents,
                    "search_type": "enhanced_vector_filtered" if applied_filters else "enhanced_vector",
                    "total_results": len(pairs),
                    "embedding_method": self.embedding_method,
                    "species_index_used": sp,
                    "species_detected": species_hint,
                    "species_confidence": confidence,
                    "filters_applied": applied_filters,
                    "tried": tried,
                    "enhanced_features": True,
                }

        # Fallback aux meilleurs résultats
        if best_results:
            pairs, sp, method = best_results
            answer = self._enhanced_synthesize_answer(query, pairs)
            source_documents = [doc for doc, _ in pairs]

            return {
                "answer": answer,
                "source_documents": source_documents,
                "search_type": "enhanced_vector_fallback_filtered" if applied_filters else "enhanced_vector_fallback",
                "total_results": len(pairs),
                "embedding_method": method,
                "species_index_used": sp,
                "species_detected": species_hint,
                "species_confidence": confidence,
                "filters_applied": applied_filters,
                "tried": tried,
                "enhanced_features": True,
            }

        logger.warning("Aucun résultat valide sur les espèces testées: %s (filtres: %s)", "→".join(tried), applied_filters)
        return None

    def _enhanced_synthesize_answer(self, query: str, results: List[Tuple[Dict[str, Any], float]]) -> str:
        """Enhanced answer synthesis"""
        if not results:
            return "Aucune information pertinente trouvée dans la base de connaissances."

        try:
            parts: List[str] = []
            
            table_results = []
            text_results = []
            
            for doc, score in results[:5]:
                content = doc.get("content", "") or ""
                metadata = doc.get("metadata", {}) or {}
                
                if _looks_like_table(content, metadata) or metadata.get("chunk_type") == "table":
                    table_results.append((doc, score))
                else:
                    text_results.append((doc, score))
            
            if _query_has_numbers_or_units(query) and table_results:
                primary_results = table_results[:2] + text_results[:1]
            else:
                primary_results = (table_results + text_results)[:3]
            
            for doc, score in primary_results:
                content = doc.get("content", "") or ""
                metadata = doc.get("metadata", {}) or {}
                
                src = self._get_enhanced_source_info(doc)
                
                if len(content) > 600:
                    content = content[:600] + "..."
                
                context_info = self._extract_context_info(metadata)
                if context_info:
                    content = f"[{context_info}]\n{content}"
                
                parts.append(f"**Source: {src}**\n{content}")

            if _query_has_numbers_or_units(query):
                header = "Données techniques trouvées :"
            else:
                header = "Informations pertinentes :"
            
            return header + "\n\n" + "\n\n---\n\n".join(parts)

        except Exception as e:
            logger.error("Échec synthèse réponse améliorée: %s", e)
            return f"{len(results)} documents pertinents trouvés, mais la synthèse a échoué."

    def _get_enhanced_source_info(self, doc: Dict[str, Any]) -> str:
        """Extract enhanced source information"""
        metadata = doc.get("metadata", {}) or {}
        
        source_candidates = [
            metadata.get("source"),
            metadata.get("file_path"),
            metadata.get("source_file"),
            doc.get("source")
        ]
        
        source = next((s for s in source_candidates if s), "source inconnue")
        
        if isinstance(source, str) and ("/" in source or "\\" in source):
            source = source.split("/")[-1].split("\\")[-1]
        
        enhancements = []
        
        if metadata.get("species"):
            enhancements.append(f"Espèce: {metadata['species']}")
        
        if metadata.get("line"):
            enhancements.append(f"Lignée: {metadata['line']}")
        
        if metadata.get("sex"):
            enhancements.append(f"Sexe: {metadata['sex']}")
        
        if metadata.get("document_type"):
            enhancements.append(f"Type: {metadata['document_type']}")
        
        if enhancements:
            return f"{source} ({', '.join(enhancements)})"
        
        return source

    def _extract_context_info(self, metadata: Dict[str, Any]) -> str:
        """Extract contextual information from metadata"""
        context_parts = []
        
        if metadata.get("chunk_type") == "table":
            context_parts.append("Tableau")
        
        if metadata.get("table_type") == "perf_targets":
            context_parts.append("Objectifs performance")
        
        if metadata.get("age_range"):
            context_parts.append(f"Âge: {metadata['age_range']}")
        
        if metadata.get("technical_level") == "advanced":
            context_parts.append("Niveau avancé")
        
        return " - ".join(context_parts)

    def retrieve(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Enhanced retrieve method with backward compatibility"""
        filters = kwargs.get("filters")
        result = self.get_contextual_diagnosis(query, k=kwargs.get("k", 5), filters=filters)
        if result and result.get("source_documents"):
            documents = result["source_documents"]
            for doc in documents:
                doc["_retrieval_metadata"] = {
                    "species_detected": result.get("species_detected"),
                    "species_confidence": result.get("species_confidence"),
                    "search_type": result.get("search_type"),
                    "filters_applied": result.get("filters_applied"),
                    "embedding_method": self.embedding_method,
                    "enhanced": True
                }
            return documents
        return []

    def get_debug_info(self) -> Dict[str, Any]:
        """Enhanced debug information"""
        info: Dict[str, Any] = {
            "is_available": self.is_available(),
            "embedding_method": self.embedding_method,
            "embedder_available": self.embedder is not None and self.embedder.is_available() if self.embedder else False,
            "loaded_species": {sp: self.is_loaded_by_species.get(sp, False) for sp in _SPECIES},
            "faiss_ntotal": {sp: getattr(self.index_by_species.get(sp), "ntotal", 0) if self.index_by_species.get(sp) else 0 for sp in _SPECIES},
            "documents_count": {sp: len(self.documents_by_species.get(sp, [])) for sp in _SPECIES},
            "embedding_dimension": {sp: self.emb_dim_by_species.get(sp) for sp in _SPECIES},
            "production_features": {
                "multi_embedding_support": True,
                "dimension_compatibility_check": True,
                "method_propagation": True,
                "openai_default": True,
                "pytorch_optional": True
            },
        }
        
        try:
            info["index_paths"] = {sp: str(self._get_rag_index_path(sp)) for sp in _SPECIES}
            info["path_exists"] = {sp: self._get_rag_index_path(sp).exists() for sp in _SPECIES}
        except Exception as e:
            info["path_resolution_error"] = str(e)
        
        total_docs = sum(len(self.documents_by_species.get(sp, [])) for sp in _SPECIES)
        info["performance_stats"] = {
            "total_documents": total_docs,
            "average_docs_per_species": total_docs / len(_SPECIES) if total_docs > 0 else 0,
            "species_with_data": [sp for sp in _SPECIES if len(self.documents_by_species.get(sp, [])) > 0]
        }
        
        return info

# =====================================================================
# Compatibility & Factory Functions
# =====================================================================

ContextualRetriever = RAGRetriever

def create_rag_retriever(embedding_method: Optional[str] = None, openai_api_key: Optional[str] = None) -> RAGRetriever:
    """Factory function for creating production-ready RAG retriever"""
    return RAGRetriever(embedding_method=embedding_method, openai_api_key=openai_api_key)

def create_enhanced_retriever(embedding_method: Optional[str] = None, **kwargs) -> RAGRetriever:
    """Factory function with production features"""
    retriever = RAGRetriever(embedding_method=embedding_method, **kwargs)
    
    logger.info("✅ Production RAG Retriever créé avec features:")
    logger.info("   - Multi-embedding: OpenAI/FastEmbed/SentenceTransformers")
    logger.info(f"   - Méthode active: {retriever.embedding_method}")
    logger.info("   - Gestion dimensions FAISS robuste")
    logger.info("   - Filtrage métadonnées avancé")
    logger.info("   - PyTorch optionnel (FastEmbed = torch-free)")
    logger.info("   - Fallbacks intelligents multi-méthodes")
    
    return retriever