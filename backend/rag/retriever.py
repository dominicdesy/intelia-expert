"""
RAG Retriever - Enhanced Species-aware, table-first, multi-index with Advanced Detection

Améliorations clés vs. version précédente :
- Enhanced species detection avec scoring de confiance
- Multi-index par espèce (broiler/layer/global) avec détection auto et fallback intelligent
- Priorité table-first (re-ranking quand la requête contient des chiffres/unités)  
- Cache des index FAISS par espèce (évite les rechargements)
- Modèle SentenceTransformer paresseux et réutilisable
- Gestion des ambiguïtés avec fallbacks adaptatifs
- Integration des métadonnées enrichies

ENV pris en charge (si présents) :
- RAG_INDEX_DIR (racine contenant /global, /broiler, /layer)
- RAG_INDEX_GLOBAL, RAG_INDEX_BROILER, RAG_INDEX_LAYER (chemins directs)
- OPENAI_API_KEY (si méthode OpenAI utilisée)
"""

from __future__ import annotations

import os
import re
import pickle
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# -----------------------------
# Enhanced Helpers (espèce & tables)
# -----------------------------

_SPECIES = ("broiler", "layer", "global")

def _enhanced_detect_species_from_query(q: str) -> Tuple[Optional[str], float]:
    """
    Enhanced species detection from query with confidence scoring
    Returns: (species, confidence_score)
    """
    ql = (q or "").lower()
    species_scores = {"broiler": 0.0, "layer": 0.0}
    
    # Enhanced keywords with weights
    species_keywords_weighted = {
        "layer": [
            # High confidence indicators (weight 3)
            ("pondeuse", 3), ("ponte", 3), ("œuf", 3), ("oeuf", 3), ("layer", 3),
            ("lohmann brown", 3), ("hy-line brown", 3), ("w-36", 3), ("w-80", 3),
            ("lsl-lite", 3), ("isa brown", 3),
            # Medium confidence (weight 2)
            ("lohmann", 2), ("hy-line", 2), ("hyline", 2), ("isa", 2), ("laying hen", 2),
            ("poule pondeuse", 2), ("egg production", 2), ("hen day", 2),
            # Lower confidence (weight 1)
            ("w36", 1), ("w80", 1), ("production", 1)
        ],
        "broiler": [
            # High confidence indicators (weight 3)
            ("ross 308", 3), ("ross308", 3), ("cobb 500", 3), ("cobb500", 3),
            ("ross 708", 3), ("poulet de chair", 3), ("broiler", 3), ("hubbard", 3),
            # Medium confidence (weight 2)
            ("ross", 2), ("cobb", 2), ("meat chicken", 2), ("chair", 2),
            ("griller", 2), ("fcr", 2), ("finisher", 2), ("starter", 2),
            # Lower confidence (weight 1)  
            ("croissance", 1), ("poids", 1), ("gain", 1), ("weight", 1)
        ]
    }
    
    # Calculate weighted scores
    for species, keywords in species_keywords_weighted.items():
        for keyword, weight in keywords:
            if keyword in ql:
                species_scores[species] += weight
    
    # Select best species
    max_score = max(species_scores.values())
    if max_score == 0:
        return None, 0.0
    
    best_species = max(species_scores, key=species_scores.get)
    confidence = min(max_score / 10.0, 1.0)  # Normalize to 0-1
    
    # Handle conflicts intelligently
    sorted_scores = sorted(species_scores.values(), reverse=True)
    if len(sorted_scores) > 1 and sorted_scores[0] - sorted_scores[1] < 2:
        # Ambiguous case - reduce confidence but don't eliminate
        return best_species, confidence * 0.6
    
    return best_species, confidence

def _detect_species_from_query(q: str) -> Optional[str]:
    """Legacy compatibility wrapper"""
    species, confidence = _enhanced_detect_species_from_query(q)
    # Only return species if confidence is reasonable
    return species if confidence > 0.3 else None

def _looks_like_table(text: str, md: Dict[str, Any]) -> bool:
    """Enhanced table detection"""
    # métadonnée explicite
    if isinstance(md, dict) and (md.get("chunk_type") == "table" or md.get("table_type")):
        return True
    
    t = text or ""
    
    # Enhanced detection patterns
    table_indicators = [
        # Markdown tables
        t.count("|") >= 3,
        # CSV-like content
        t.count(",") >= 5 and "\n" in t,
        # Tabular spacing (multiple columns)
        re.search(r"\S+\s{2,}\S+\s{2,}\S+", t),
        # Headers with numerical data
        re.search(r"(?:age|week|day|poids|weight|fcr|protein)\s+\d+", t, re.IGNORECASE),
        # Performance tables (common patterns)
        re.search(r"\d+\s*[-–]\s*\d+\s*(?:days?|jours?|weeks?|sem)", t, re.IGNORECASE),
        # Nutritional tables
        re.search(r"(?:lysine|protein|energy|calcium)\s*[:\-]\s*\d+", t, re.IGNORECASE)
    ]
    
    return any(table_indicators)

def _query_has_numbers_or_units(q: str) -> bool:
    """Enhanced detection of technical queries needing table-first ranking"""
    ql = (q or "").lower()
    
    # Numbers
    has_numbers = any(ch.isdigit() for ch in ql)
    
    # Technical units (expanded list)
    technical_units = [
        "kg", "g", "fcr", "%", "°c", "ppm", "m³", "m3", "lux", "pa",
        "kcal", "mj", "mg", "days", "weeks", "jours", "semaines",
        "density", "densité", "birds/m²", "sujets/m²"
    ]
    
    has_units = any(u in ql for u in technical_units)
    
    # Performance indicators
    performance_terms = [
        "rate", "taux", "ratio", "indice", "conversion", "gain",
        "production", "efficiency", "mortality", "viability"
    ]
    
    has_performance_terms = any(t in ql for t in performance_terms)
    
    return has_numbers or has_units or has_performance_terms

# =====================================================================
# Enhanced Retriever
# =====================================================================

class RAGRetriever:
    """
    Enhanced RAG retriever avec :
    - Méthodes d'embedding multiples (SentenceTransformers / OpenAI / TF-IDF)
    - Multi-index par espèce (broiler/layer/global) avec auto-détection améliorée
    - Table-first re-ranking intelligent
    - Chargements FAISS robustes + métadonnées normalisées
    - Gestion avancée des ambiguïtés et fallbacks adaptatifs
    """

    # Cache modèle SentenceTransformer partagé (par worker)
    _st_model = None
    _st_lock = threading.Lock()

    def __init__(self, openai_api_key: Optional[str] = None) -> None:
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")

        # États par espèce
        self.index_by_species: Dict[str, Any] = {}
        self.documents_by_species: Dict[str, List[Dict[str, Any]]] = {}
        self.method_by_species: Dict[str, str] = {}
        self.emb_dim_by_species: Dict[str, Optional[int]] = {}
        self.is_loaded_by_species: Dict[str, bool] = {s: False for s in _SPECIES}

        # Chargement eager de "global" (optionnel)
        self._load_index_for_species("global")

    # -----------------------------
    # Résolution chemins index - Enhanced
    # -----------------------------

    def _get_rag_index_path(self, species: str) -> Path:
        """
        Enhanced path resolution with better backend support
        """
        sp = (species or "global").lower()
        env_key = f"RAG_INDEX_{sp.upper()}"
        if os.environ.get(env_key):
            return Path(os.environ[env_key])

        root = os.environ.get("RAG_INDEX_DIR")
        if root:
            p = Path(root) / sp
            if p.exists():
                return p

        # Enhanced priority paths
        search_paths = [
            Path.cwd() / "backend" / "rag_index" / sp,  # Backend priority
            Path.cwd() / "rag_index" / sp,
            Path(__file__).parent.parent / "backend" / "rag_index" / sp,
            Path(__file__).parent.parent / "rag_index" / sp,
        ]
        
        for path in search_paths:
            if path.exists():
                logger.info("✅ Index trouvé pour %s: %s", sp, path)
                return path

        # Fallback paths
        fallback_paths = [
            Path.cwd() / "backend" / "rag_index",
            Path.cwd() / "rag_index"
        ]
        
        for path in fallback_paths:
            if path.exists():
                logger.info("✅ Fallback index pour %s: %s", sp, path)
                return path

        # Ultimate fallback
        return Path.cwd() / "rag_index"

    # -----------------------------
    # Normalisation méthode embeddings
    # -----------------------------

    def _normalize_embedding_method(self, method: str) -> str:
        if not method or not isinstance(method, str):
            return "SentenceTransformers"
        m = method.lower().strip()
        mapping = {
            # SentenceTransformers variations
            "sentence_transformers": "SentenceTransformers",
            "sentence-transformers": "SentenceTransformers",
            "sentencetransformers": "SentenceTransformers",
            "sentence transformers": "SentenceTransformers",
            "all-minilm-l6-v2": "SentenceTransformers",
            "huggingface": "SentenceTransformers",
            "transformer": "SentenceTransformers",
            "bert": "SentenceTransformers",
            # OpenAI variations
            "openai": "OpenAI",
            "openaiembeddings": "OpenAI",
            "openai_embeddings": "OpenAI",
            "text-embedding-ada-002": "OpenAI",
            "ada-002": "OpenAI",
            # TF-IDF variations
            "tfidf": "TF-IDF",
            "tf-idf": "TF-IDF",
            "tf_idf": "TF-IDF",
        }
        out = mapping.get(m, method)
        if out not in {"SentenceTransformers", "OpenAI", "TF-IDF"}:
            logger.warning("Unknown embedding method '%s' → fallback SentenceTransformers", method)
            return "SentenceTransformers"
        return out

    # -----------------------------
    # 🔧 CORRECTION CRITIQUE : Normalisation robuste des documents
    # -----------------------------

    def _normalize_documents_format(self, raw_docs: Any) -> List[Dict[str, Any]]:
        """
        🔧 CORRECTION : Normalise différents formats de documents pour éviter l'erreur 'list' object has no attribute 'get'
        """
        normalized = []
        
        try:
            if isinstance(raw_docs, list):
                for i, doc in enumerate(raw_docs):
                    if isinstance(doc, dict):
                        # Format déjà correct
                        if "content" in doc:
                            normalized.append(doc)
                        elif "text" in doc:
                            # Conversion text -> content
                            normalized.append({
                                "content": doc["text"],
                                "metadata": doc.get("metadata", {}),
                                "source": doc.get("source", f"doc_{i}")
                            })
                        else:
                            # Dictionnaire avec clés inconnues - prendre la première valeur string
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
                        # Format string simple
                        normalized.append({
                            "content": doc,
                            "metadata": {"original_format": "string"},
                            "source": f"doc_{i}"
                        })
                    else:
                        # Autres formats - conversion en string
                        normalized.append({
                            "content": str(doc),
                            "metadata": {"original_format": type(doc).__name__},
                            "source": f"doc_{i}"
                        })
            
            elif isinstance(raw_docs, dict):
                # Format dictionnaire avec clés comme IDs
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
                            # Dictionnaire sans 'content' ni 'text'
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
                # Format inconnu - essayer de le convertir
                logger.warning("Format de documents inconnu: %s", type(raw_docs).__name__)
                normalized.append({
                    "content": str(raw_docs),
                    "metadata": {"original_format": type(raw_docs).__name__},
                    "source": "unknown_format"
                })
        
        except Exception as e:
            logger.error("Erreur lors de la normalisation des documents: %s", e)
            # Fallback de sécurité
            normalized = [{
                "content": "Erreur de chargement du document",
                "metadata": {"error": str(e)},
                "source": "error_fallback"
            }]
        
        logger.info("✅ Documents normalisés: %d documents convertis au format standard", len(normalized))
        return normalized

    # -----------------------------
    # Chargement index (par espèce) - Enhanced avec correction
    # -----------------------------

    def _load_index_for_species(self, species: str) -> bool:
        """Enhanced index loading with ultra-robust document format handling"""
        sp = (species or "global").lower()
        if sp not in _SPECIES:
            sp = "global"
        if self.is_loaded_by_species.get(sp):
            return True

        try:
            import faiss  # noqa: F401
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
            
            # 🔧 CORRECTION ULTIME : Gestion robuste du fichier pickle
            with open(pkl_file, "rb") as f:
                raw_data = pickle.load(f)
            
            # Normaliser le format des données pickled AVANT tout accès
            if isinstance(raw_data, list):
                # Si c'est une liste, créer un dictionnaire avec les documents
                logger.info("Format pickle détecté: liste de %d éléments pour %s", len(raw_data), sp)
                data = {
                    "documents": raw_data,
                    "method": "SentenceTransformers",
                    "embedding_method": "SentenceTransformers",
                    "embeddings": None
                }
            elif isinstance(raw_data, dict):
                # Format dictionnaire - vérifier la structure
                data = raw_data
                logger.info("Format pickle détecté: dictionnaire avec clés %s pour %s", list(data.keys()), sp)
            else:
                # Format inconnu - essayer de le convertir
                logger.warning("Format pickle inconnu pour %s: %s", sp, type(raw_data).__name__)
                data = {
                    "documents": [str(raw_data)],
                    "method": "SentenceTransformers",
                    "embedding_method": "SentenceTransformers",
                    "embeddings": None
                }

            # Maintenant on peut utiliser .get() en sécurité
            raw_method = data.get("method", data.get("embedding_method", "SentenceTransformers"))
            method = self._normalize_embedding_method(raw_method)
            
            # 🔧 CORRECTION CRITIQUE : Normalisation robuste des documents
            raw_docs = data.get("documents", [])
            docs = self._normalize_documents_format(raw_docs)
            
            embeddings = data.get("embeddings", None)
            emb_dim = (len(embeddings[0]) if isinstance(embeddings, list) and embeddings else None)

            # Mémoriser
            self.index_by_species[sp] = idx
            self.documents_by_species[sp] = docs
            self.method_by_species[sp] = method
            self.emb_dim_by_species[sp] = emb_dim
            self.is_loaded_by_species[sp] = True

            # Enhanced metadata correction
            if raw_method != method:
                try:
                    data["method"] = method
                    data["embedding_method"] = method
                    backup = pkl_file.with_suffix(".pkl.backup")
                    if pkl_file.exists() and not backup.exists():
                        import shutil
                        shutil.copy2(pkl_file, backup)
                    with open(pkl_file, "wb") as wf:
                        pickle.dump(data, wf)
                    logger.info("Métadonnées corrigées (méthode embeddings normalisée) pour %s", sp)
                except Exception as e:
                    logger.warning("Impossible d'enregistrer les métadonnées corrigées (%s): %s", sp, e)

            logger.info("✅ Index %s chargé | ntotal=%s | docs=%d | method=%s",
                        sp, getattr(idx, "ntotal", "n/a"), len(docs), method)
            return True
        except Exception as e:
            logger.error("Erreur de chargement index %s: %s", sp, e)
            return False

    # -----------------------------
    # Disponibilité
    # -----------------------------

    def is_available(self) -> bool:
        """Vrai si au moins un index espèce est chargé et non vide."""
        for sp in _SPECIES:
            if self.is_loaded_by_species.get(sp) and self.index_by_species.get(sp) is not None:
                if getattr(self.index_by_species[sp], "ntotal", 0) > 0:
                    return True
        return False

    # -----------------------------
    # Embeddings
    # -----------------------------

    def _ensure_st_model(self):
        """Singleton SentenceTransformer (lazy)."""
        if self._st_model is not None:
            return self._st_model
        with self._st_lock:
            if self._st_model is None:
                from sentence_transformers import SentenceTransformer
                self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._st_model

    def _create_openai_embedding(self, query: str) -> Optional[np.ndarray]:
        if not self.openai_api_key:
            logger.error("OPENAI_API_KEY manquant pour embeddings OpenAI")
            return None
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            resp = client.embeddings.create(input=query, model="text-embedding-ada-002")
            vec = np.array(resp.data[0].embedding, dtype=np.float32)
            return vec
        except Exception as e:
            logger.error("Echec embedding OpenAI: %s", e)
            return None

    def _create_sentence_transformer_embedding(self, query: str) -> Optional[np.ndarray]:
        try:
            model = self._ensure_st_model()
            emb = model.encode([query], normalize_embeddings=True)
            return np.array(emb[0], dtype=np.float32)
        except Exception as e:
            logger.error("Echec embedding SentenceTransformer: %s", e)
            return None

    def _create_tfidf_embedding(self, query: str, species: str) -> Optional[np.ndarray]:
        dim = self.emb_dim_by_species.get(species) or 0
        if not dim:
            return None
        words = (query or "").lower().split()
        vec = np.zeros(dim, dtype=np.float32)
        for i, w in enumerate(words[:dim]):
            vec[i] = 0.1 + (hash(w) % 100) / 1000.0
        return vec

    def _create_query_embedding(self, query: str, method: str, species: str) -> Optional[np.ndarray]:
        try:
            if method == "OpenAI":
                return self._create_openai_embedding(query)
            if method == "SentenceTransformers":
                return self._create_sentence_transformer_embedding(query)
            if method == "TF-IDF":
                return self._create_tfidf_embedding(query, species)
            # fallback cascade
            emb = self._create_sentence_transformer_embedding(query)
            if emb is not None:
                return emb
            if self.openai_api_key:
                emb = self._create_openai_embedding(query)
                if emb is not None:
                    return emb
            return self._create_tfidf_embedding(query, species)
        except Exception as e:
            logger.error("Echec création embedding requête: %s", e)
            return None

    # -----------------------------
    # FAISS search
    # -----------------------------

    def _search_index(self, species: str, query_embedding: np.ndarray, k: int) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        try:
            import faiss
            idx = self.index_by_species.get(species)
            if idx is None:
                return None, None

            qe = query_embedding
            if qe.ndim == 1:
                qe = qe.reshape(1, -1)
            # normalisation L2 sauf TF-IDF
            if self.method_by_species.get(species) != "TF-IDF":
                faiss.normalize_L2(qe)
            distances, indices = idx.search(qe.astype("float32"), k)
            return distances, indices
        except Exception as e:
            logger.error("Echec recherche FAISS (%s): %s", species, e)
            return None, None

    def _process_search_results(self, species: str, distances: np.ndarray, indices: np.ndarray) -> List[Tuple[Dict[str, Any], float]]:
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
            logger.error("Echec traitement résultats: %s", e)
            return []

    # -----------------------------
    # Enhanced Table-first re-ranking
    # -----------------------------

    @staticmethod
    def _score_from_distance(distance: float) -> float:
        if distance <= 0:
            return 1.0
        return float(max(0.0, min(1.0, np.exp(-distance * 1.5))))

    @staticmethod
    def _token_overlap_boost(q: str, t: str) -> float:
        qw = set((q or "").lower().split())
        if not qw:
            return 0.0
        tw = set((t or "").lower().split())
        overlap = len(qw & tw) / max(1, len(qw))
        return min(0.15, overlap * 0.15)  # Enhanced bonus

    def _enhanced_table_first_rerank(self, query: str, pairs: List[Tuple[Dict[str, Any], float]]) -> List[Tuple[Dict[str, Any], float]]:
        """Enhanced table-first ranking with better detection"""
        if not pairs or not _query_has_numbers_or_units(query):
            return pairs
        
        boosted: List[Tuple[Dict[str, Any], float, float]] = []
        
        for doc, raw in pairs:
            text = doc.get("content", "")
            md = doc.get("metadata", {}) or {}
            base = self._score_from_distance(raw)
            bonus = 0.0
            
            # Enhanced table detection bonus
            if _looks_like_table(text, md):
                bonus += 0.2  # Increased bonus for tables
            
            # Metadata-based bonuses
            if md.get("chunk_type") == "table":
                bonus += 0.15
            
            if md.get("domain") in ["performance", "nutrition"]:
                bonus += 0.1
            
            # Technical content bonus
            technical_patterns = [
                r"\d+\s*(?:kg|g|%|°c|days?|weeks?|fcr)",
                r"(?:protein|lysine|calcium|energy)\s*[:=]\s*\d+",
                r"(?:mortality|growth|conversion)\s*[:=]\s*\d+"
            ]
            
            for pattern in technical_patterns:
                if re.search(pattern, text.lower()):
                    bonus += 0.05
                    break
            
            # Token overlap bonus
            bonus += self._token_overlap_boost(query, text)
            
            # Apply bonus with ceiling
            final_score = min(1.0, base + bonus)
            boosted.append((doc, raw, final_score))
        
        # Sort by enhanced score
        boosted.sort(key=lambda r: r[2], reverse=True)
        return [(d, s) for (d, s, _) in boosted]

    # -----------------------------
    # Enhanced API publique
    # -----------------------------

    def get_contextual_diagnosis(self, query: str, k: int = 5) -> Optional[Dict[str, Any]]:
        """
        Enhanced recherche species-aware + table-first with adaptive fallbacks.
        Retourne une réponse synthétisée + documents sources avec métadonnées enrichies.
        """
        # Enhanced species detection with confidence
        species_hint, confidence = _enhanced_detect_species_from_query(query)
        
        if not species_hint:
            species_hint = "global"
        
        tried: List[str] = []
        best_results = None
        best_species = None

        # Adaptive search strategy based on confidence
        if confidence > 0.7:
            # High confidence - try detected species first
            candidates = [species_hint] + [s for s in _SPECIES if s != species_hint]
        elif confidence > 0.3:
            # Medium confidence - try detected + global
            candidates = [species_hint, "global"] + [s for s in _SPECIES if s not in [species_hint, "global"]]
        else:
            # Low confidence - start with global
            candidates = ["global"] + [s for s in _SPECIES if s != "global"]

        for sp in candidates:
            tried.append(sp)
            if not self._load_index_for_species(sp):
                continue

            method = self.method_by_species.get(sp, "SentenceTransformers")
            emb = self._create_query_embedding(query, method, sp)
            if emb is None:
                continue

            # Adaptive search width based on species confidence
            search_multiplier = 3 if confidence > 0.5 else 2
            scores, indices = self._search_index(sp, emb, max(k * search_multiplier, 10))
            if scores is None or indices is None:
                continue

            pairs = self._process_search_results(sp, scores, indices)
            if not pairs:
                continue

            # Enhanced table-first re-ranking
            pairs = self._enhanced_table_first_rerank(query, pairs)
            pairs = pairs[:k]

            # Store best results for potential fallback
            if not best_results or len(pairs) > len(best_results[0]):
                best_results = (pairs, sp, method)
                best_species = sp

            # Success criteria: good results or high confidence match
            if pairs and (len(pairs) >= k // 2 or sp == species_hint):
                answer = self._enhanced_synthesize_answer(query, pairs)
                source_documents = [doc for doc, _ in pairs]

                return {
                    "answer": answer,
                    "source_documents": source_documents,
                    "search_type": "enhanced_vector",
                    "total_results": len(pairs),
                    "embedding_method": method,
                    "species_index_used": sp,
                    "species_detected": species_hint,
                    "species_confidence": confidence,
                    "tried": tried,
                    "enhanced_features": True,
                }

        # Fallback to best results if available
        if best_results:
            pairs, sp, method = best_results
            answer = self._enhanced_synthesize_answer(query, pairs)
            source_documents = [doc for doc, _ in pairs]

            return {
                "answer": answer,
                "source_documents": source_documents,
                "search_type": "enhanced_vector_fallback",
                "total_results": len(pairs),
                "embedding_method": method,
                "species_index_used": sp,
                "species_detected": species_hint,
                "species_confidence": confidence,
                "tried": tried,
                "enhanced_features": True,
            }

        logger.warning("Aucun résultat valide sur les espèces testées: %s", "→".join(tried))
        return None

    def _enhanced_synthesize_answer(self, query: str, results: List[Tuple[Dict[str, Any], float]]) -> str:
        """Enhanced answer synthesis with better formatting and metadata awareness"""
        if not results:
            return "Aucune information pertinente trouvée dans la base de connaissances."

        try:
            parts: List[str] = []
            
            # Group results by source type for better organization
            table_results = []
            text_results = []
            
            for doc, score in results[:5]:  # Consider more results for synthesis
                content = doc.get("content", "") or ""
                metadata = doc.get("metadata", {}) or {}
                
                if _looks_like_table(content, metadata) or metadata.get("chunk_type") == "table":
                    table_results.append((doc, score))
                else:
                    text_results.append((doc, score))
            
            # Prioritize tables for technical queries
            if _query_has_numbers_or_units(query) and table_results:
                primary_results = table_results[:2] + text_results[:1]
            else:
                primary_results = (table_results + text_results)[:3]
            
            for doc, score in primary_results:
                content = doc.get("content", "") or ""
                metadata = doc.get("metadata", {}) or {}
                
                # Enhanced source identification
                src = self._get_enhanced_source_info(doc)
                
                # Content preprocessing for better readability
                if len(content) > 600:
                    content = content[:600] + "..."
                
                # Add metadata context if relevant
                context_info = self._extract_context_info(metadata)
                if context_info:
                    content = f"[{context_info}]\n{content}"
                
                parts.append(f"**Source: {src}**\n{content}")

            # Enhanced header based on query type
            if _query_has_numbers_or_units(query):
                header = "Données techniques trouvées :"
            else:
                header = "Informations pertinentes :"
            
            return header + "\n\n" + "\n\n---\n\n".join(parts)

        except Exception as e:
            logger.error("Echec synthèse réponse améliorée: %s", e)
            return f"{len(results)} documents pertinents trouvés, mais la synthèse a échoué."

    def _get_enhanced_source_info(self, doc: Dict[str, Any]) -> str:
        """Extract enhanced source information from document"""
        metadata = doc.get("metadata", {}) or {}
        
        # Try multiple source fields
        source_candidates = [
            metadata.get("source"),
            metadata.get("file_path"),
            metadata.get("source_file"),
            doc.get("source")
        ]
        
        source = next((s for s in source_candidates if s), "source inconnue")
        
        # Clean up file path
        if isinstance(source, str) and ("/" in source or "\\" in source):
            source = source.split("/")[-1].split("\\")[-1]
        
        # Add metadata context
        enhancements = []
        
        if metadata.get("strain"):
            enhancements.append(f"Souche: {metadata['strain']}")
        
        if metadata.get("production_phase"):
            enhancements.append(f"Phase: {metadata['production_phase']}")
        
        if metadata.get("domain"):
            enhancements.append(f"Domaine: {metadata['domain']}")
        
        if enhancements:
            return f"{source} ({', '.join(enhancements)})"
        
        return source

    def _extract_context_info(self, metadata: Dict[str, Any]) -> str:
        """Extract contextual information from metadata"""
        context_parts = []
        
        if metadata.get("chunk_type") == "table":
            context_parts.append("Tableau")
        
        if metadata.get("age_range"):
            context_parts.append(f"Âge: {metadata['age_range']}")
        
        if metadata.get("technical_level") == "advanced":
            context_parts.append("Niveau avancé")
        
        return " - ".join(context_parts)

    # Interface compacte de compatibilité (améliorée)
    def retrieve(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Enhanced retrieve method with backward compatibility"""
        result = self.get_contextual_diagnosis(query, k=kwargs.get("k", 5))
        if result and result.get("source_documents"):
            # Add enhanced metadata to results
            documents = result["source_documents"]
            for doc in documents:
                doc["_retrieval_metadata"] = {
                    "species_detected": result.get("species_detected"),
                    "species_confidence": result.get("species_confidence"),
                    "search_type": result.get("search_type"),
                    "enhanced": True
                }
            return documents
        return []

    # Enhanced Debug Information
    def get_debug_info(self) -> Dict[str, Any]:
        """Enhanced debug information with more detailed insights"""
        info: Dict[str, Any] = {
            "is_available": self.is_available(),
            "loaded_species": {sp: self.is_loaded_by_species.get(sp, False) for sp in _SPECIES},
            "faiss_ntotal": {sp: getattr(self.index_by_species.get(sp), "ntotal", 0) if self.index_by_species.get(sp) else 0 for sp in _SPECIES},
            "documents_count": {sp: len(self.documents_by_species.get(sp, [])) for sp in _SPECIES},
            "embedding_method": {sp: self.method_by_species.get(sp) for sp in _SPECIES},
            "embedding_dimension": {sp: self.emb_dim_by_species.get(sp) for sp in _SPECIES},
            "enhanced_features": True,
        }
        
        # Enhanced path resolution info
        try:
            info["index_paths"] = {sp: str(self._get_rag_index_path(sp)) for sp in _SPECIES}
            info["path_exists"] = {sp: self._get_rag_index_path(sp).exists() for sp in _SPECIES}
        except Exception as e:
            info["path_resolution_error"] = str(e)
        
        # Performance stats
        total_docs = sum(len(self.documents_by_species.get(sp, [])) for sp in _SPECIES)
        info["performance_stats"] = {
            "total_documents": total_docs,
            "average_docs_per_species": total_docs / len(_SPECIES) if total_docs > 0 else 0,
            "species_with_data": [sp for sp in _SPECIES if len(self.documents_by_species.get(sp, [])) > 0]
        }
        
        return info

    def test_species_detection(self, test_queries: List[str]) -> Dict[str, Any]:
        """Test species detection on multiple queries"""
        results = {}
        for query in test_queries:
            species, confidence = _enhanced_detect_species_from_query(query)
            results[query] = {
                "detected_species": species,
                "confidence": confidence,
                "classification": "high" if confidence > 0.7 else "medium" if confidence > 0.3 else "low"
            }
        return results


# =====================================================================
# Compatibility Aliases & Factory Functions
# =====================================================================

ContextualRetriever = RAGRetriever

def create_rag_retriever(openai_api_key: Optional[str] = None) -> RAGRetriever:
    """Factory function for creating enhanced RAG retriever"""
    return RAGRetriever(openai_api_key=openai_api_key)

def create_enhanced_retriever(openai_api_key: Optional[str] = None, **kwargs) -> RAGRetriever:
    """Factory function with explicit enhanced features mention"""
    retriever = RAGRetriever(openai_api_key=openai_api_key)
    
    # Log enhancement status
    logger.info("✅ Enhanced RAG Retriever created with features:")
    logger.info("   - Advanced species detection with confidence scoring")
    logger.info("   - Intelligent table-first ranking")
    logger.info("   - Adaptive fallback strategies")
    logger.info("   - Enhanced metadata awareness")
    logger.info("   - 🔧 Robust document format handling")
    
    return retriever