# rag/embedder.py
"""
FastRAGEmbedder
- Lazy, thread-safe init of SentenceTransformer + FAISS
- Adaptive thresholds; conservative defaults to reduce false positives
- Query normalization (non-destructive intent), species inference/filtering
- Single-API search(query, k=5, species=None)
- ENV-aware loader: load_from_env() reads RAG_INDEX_* paths
- Legacy alias: RAGEmbedder = FastRAGEmbedder
"""

from __future__ import annotations

import os
import time
import pickle
import logging
import re
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class FastRAGEmbedder:
    def __init__(
        self,
        *,
        model_name: str = "all-MiniLM-L6-v2",
        cache_embeddings: bool = True,
        max_workers: int = 2,   # reserved for future parallel encodes
        debug: bool = True,
        similarity_threshold: float = 0.20,
        normalize_queries: bool = True,
    ) -> None:
        self.model_name = model_name
        self.cache_embeddings = cache_embeddings
        self.max_workers = max_workers
        self.debug = debug
        self.normalize_queries = normalize_queries

        # thresholds (slightly stricter than permissive setups)
        self.threshold_config = {
            "strict": 0.25,
            "normal": float(max(0.0, min(1.0, similarity_threshold))),  # default 0.20
            "permissive": 0.15,
            "fallback": 0.10,
        }

        # state
        self._st_model = None           # SentenceTransformer instance
        self._st_lock = threading.Lock()
        self._index = None              # faiss.Index
        self._index_lock = threading.Lock()
        self._documents: List[Dict[str, Any]] = []
        self._ready = False
        self._dependencies_ok = False

        # caches
        self.embedding_cache: Dict[str, np.ndarray] = {} if cache_embeddings else {}

        # normalization
        self._init_normalization_patterns()

        # deps
        self._init_dependencies()

        if self.debug:
            logger.info("🚀 Initializing FastRAGEmbedder (Adaptive Thresholds)...")
            logger.info("   Model: %s", self.model_name)
            logger.info("   Dimension: 384 (expected for %s)", self.model_name)
            logger.info("   Dependencies available: %s", self._dependencies_ok)
            logger.info("   Cache enabled: %s", self.cache_embeddings)
            logger.info("   Max workers: %s", self.max_workers)
            logger.info("   Thresholds: %s", self.threshold_config)
            logger.info("   Query normalization: %s", self.normalize_queries)
            logger.info("   Debug enabled: %s", self.debug)

    # -------------------------
    # Dependencies / model init
    # -------------------------
    def _init_dependencies(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            import faiss  # noqa: F401
            self.SentenceTransformer = SentenceTransformer
            self.faiss = faiss
            self.np = np
            self._dependencies_ok = True
            logger.info("✅ sentence-transformers available")
            logger.info("✅ faiss available")
            logger.info("✅ numpy available")
        except Exception as e:
            self._dependencies_ok = False
            logger.error("❌ Missing dependencies: %s", e)

    def _ensure_model(self):
        if self._st_model is not None:
            return self._st_model
        if not self._dependencies_ok:
            raise RuntimeError("Dependencies not available (sentence-transformers / faiss)")
        with self._st_lock:
            if self._st_model is None:
                if self.debug:
                    logger.info("🔧 Loading SentenceTransformer model: %s", self.model_name)
                self._st_model = self.SentenceTransformer(self.model_name)  # CPU by default
        return self._st_model

    # -------------------------
    # Normalization / species
    # -------------------------
    def _init_normalization_patterns(self) -> None:
        self.normalization_patterns = {
            "temporal_conversions": [
                (r"(\d+)\s*semaines?", lambda m: f"{int(m.group(1)) * 7} jours"),
                (r"(\d+)\s*mois", lambda m: f"{int(m.group(1)) * 30} jours"),
                (r"(\d+)j\b", r"\1 jours"),
                (r"(\d+)s\b", r"\1 semaines"),
            ],
            "agricultural_terms": [
                (r"\bbroilers?\b", "poulet de chair"),
                (r"\bpoulets?\b", "poulet de chair"),
                (r"\bpoules?\b", "poule pondeuse"),
                (r"\bcoqs?\b", "poule pondeuse"),
                (r"\bgallines?\b", "poule pondeuse"),
                (r"\bRoss\s*308\b", "poulet de chair Ross 308"),
                (r"\bCobb\s*500\b", "poulet de chair Cobb 500"),
            ],
            "weight_conversions": [
                (r"(\d+)\s*kg\b", lambda m: f"{int(m.group(1)) * 1000} grammes"),
                (r"(\d+)\s*g\b", r"\1 grammes"),
                (r"(\d+)\s*lbs?\b", lambda m: f"{int(float(m.group(1)) * 453.592)} grammes"),
            ],
            "temperature_conversions": [
                (r"(\d+)°?C\b", r"\1 degrés Celsius"),
                (r"(\d+)°?F\b", lambda m: f"{round((int(m.group(1)) - 32) * 5/9)} degrés Celsius"),
            ],
            "synonyms": [
                (r"\bmort[ea]lité\b", "mortalité taux de mortalité"),
                (r"\bcroissance\b", "croissance développement poids"),
                (r"\balimentation\b", "alimentation nutrition nourriture"),
                (r"\bvaccination\b", "vaccination immunisation vaccin"),
                (r"\benvironnement\b", "environnement conditions température humidité"),
                (r"\bdiagnostic\b", "diagnostic symptômes maladie problème"),
            ],
        }

    def _normalize_query(self, query: str) -> str:
        if not self.normalize_queries:
            return query
        original = query
        normalized = query.lower()
        try:
            for _, patterns in self.normalization_patterns.items():
                for pattern, repl in patterns:
                    normalized = re.sub(pattern, repl, normalized, flags=re.IGNORECASE)
            normalized = re.sub(r"\s+", " ", normalized).strip()
            if self.debug and normalized != original.lower():
                logger.info("🔄 Query normalized:\n   Original: %s\n   Normalized: %s", original, normalized)
            return normalized
        except Exception as e:
            logger.error("❌ Error normalizing query: %s", e)
            return query.lower()

    def _infer_species(self, query: str) -> Optional[str]:
        q = query.lower()
        if any(w in q for w in ["pondeuse", "layer", "lohmann", "hy-line", "w36", "w-36", "w80", "w-80", "ponte", "œuf", "oeuf"]):
            return "layer"
        if any(w in q for w in ["broiler", "poulet de chair", "ross 308", "cobb 500", "croissance", "poids"]):
            if any(w in q for w in ["pondeuse", "layer", "œuf", "oeuf", "ponte", "lohmann", "hy-line"]):
                return None
            return "broiler"
        return None

    def _doc_matches_species(self, doc: Dict[str, Any], species: str) -> bool:
        if not species:
            return True
        species = species.lower()
        md = doc.get("metadata", {}) or {}
        candidates = [
            md.get("source", ""),
            md.get("file_path", ""),
            md.get("path", ""),
            doc.get("id", ""),
        ]
        joined = " ".join([c for c in candidates if isinstance(c, str)]).lower()
        if f"/species/{species}/" in joined or f"\\species\\{species}\\" in joined:
            return True
        if species == "broiler" and any(w in joined for w in ["broiler", "ross", "cobb"]):
            return True
        if species == "layer" and any(w in joined for w in ["layer", "lohmann", "hy-line"]):
            return True
        return False

    # -------------------------
    # Index loading
    # -------------------------
    def load_index(self, index_path: str) -> bool:
        """
        Load FAISS index + documents (index.pkl). Idempotent.
        """
        if not self._dependencies_ok:
            logger.error("❌ Dependencies not available for loading index")
            return False
        try:
            base = Path(index_path).resolve()
            faiss_file = base / "index.faiss"
            pkl_file = base / "index.pkl"

            if not faiss_file.exists() or not pkl_file.exists():
                logger.error("❌ Index files not found in %s", base)
                return False

            with self._index_lock:
                t0 = time.time()
                logger.info("🔄 Loading FAISS index from %s", faiss_file)
                idx = self.faiss.read_index(str(faiss_file))
                logger.info("✅ FAISS index loaded in %.2fs", time.time() - t0)
                logger.info("🔍 FAISS index info: ntotal=%s, d=%s", idx.ntotal, getattr(idx, "d", "n/a"))

                logger.info("🔄 Loading documents from %s", pkl_file)
                t1 = time.time()
                with open(pkl_file, "rb") as f:
                    raw_documents = pickle.load(f)
                docs = self._normalize_documents(raw_documents)
                logger.info("✅ Documents loaded in %.2fs", time.time() - t1)
                logger.info("🔍 Total documents: %d", len(docs))

                if idx.ntotal != len(docs):
                    logger.warning("⚠️ Index mismatch: FAISS has %d vectors, docs=%d", idx.ntotal, len(docs))

                # commit
                self._index = idx
                self._documents = docs
                self._ready = True

            logger.info("✅ Index loaded successfully - Search engine ready")
            return True
        except Exception as e:
            logger.error("❌ Error loading index: %s", e)
            return False

    def load_from_env(self) -> bool:
        """
        Tries, in order: RAG_INDEX_GLOBAL, RAG_INDEX_DIR/global, RAG_INDEX_DIR, defaults.
        Returns True on success.
        """
        # explicit global
        p = os.getenv("RAG_INDEX_GLOBAL")
        if p and self.load_index(p):
            return True

        root = os.getenv("RAG_INDEX_DIR")
        if root:
            # prefer /global under root
            g = Path(root) / "global"
            if g.exists() and self.load_index(str(g)):
                return True
            if Path(root).exists() and self.load_index(root):
                return True

        # fallback to conventional path used in Dockerfile
        default = "/app/public/global" if Path("/app/public/global").exists() else "/app/rag_index/global"
        return self.load_index(default)

    def _normalize_documents(self, raw_documents: Any) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        try:
            if isinstance(raw_documents, dict):
                for key, value in raw_documents.items():
                    if isinstance(value, dict):
                        doc = {
                            "id": value.get("id", key),
                            "text": value.get("text", value.get("content", str(value))),
                            "metadata": value.get("metadata", {}),
                        }
                        normalized.append(doc)
                    elif isinstance(value, str):
                        normalized.append({"id": key, "text": value, "metadata": {}})
            elif isinstance(raw_documents, list):
                for i, item in enumerate(raw_documents):
                    if isinstance(item, dict):
                        doc = {
                            "id": item.get("id", f"doc_{i}"),
                            "text": item.get("text", item.get("content", str(item))),
                            "metadata": item.get("metadata", {}),
                        }
                        normalized.append(doc)
                    elif isinstance(item, str):
                        normalized.append({"id": f"doc_{i}", "text": item, "metadata": {}})
        except Exception as e:
            logger.error("❌ Error normalizing documents: %s", e)

        if self.debug:
            logger.info("🔍 Normalized %d documents", len(normalized))
            if normalized:
                preview = normalized[0]["text"][:100].replace("\n", " ")
                logger.info("   First document preview: %s...", preview)
        return normalized

    # -------------------------
    # Similarity / scoring
    # -------------------------
    @staticmethod
    def _improved_similarity_score(distance: float) -> float:
        if distance <= 0:
            return 1.0
        return float(max(0.0, min(1.0, np.exp(-distance * 1.5))))

    def _boost_score_for_exact_matches(self, query: str, text: str, base_score: float) -> float:
        qw = set(query.lower().split())
        if not qw:
            return base_score
        tw = set(text.lower().split())
        overlap_ratio = len(qw.intersection(tw)) / max(1, len(qw))
        boosted = min(1.0, base_score * (1.0 + overlap_ratio * 0.3))
        if self.debug and boosted > base_score * 1.1:
            logger.info("   📈 Score boosted: %.3f → %.3f (overlap: %.2f)", base_score, boosted, overlap_ratio)
        return boosted

    # -------------------------
    # Readiness
    # -------------------------
    def has_search_engine(self) -> bool:
        ok = self._dependencies_ok and (self._index is not None) and (len(self._documents) > 0)
        if not ok and self.debug:
            logger.warning("🔍 Search engine not ready:")
            logger.warning("   dependencies_ok: %s", self._dependencies_ok)
            logger.warning("   index is not None: %s", self._index is not None)
            logger.warning("   documents > 0: %s", len(self._documents) > 0)
        return ok

    def is_ready(self) -> bool:
        return self.has_search_engine() and self._ready

    # -------------------------
    # Search
    # -------------------------
    def _embed_query(self, normalized_query: str, species_hint: Optional[str]) -> np.ndarray:
        key = f"{normalized_query}|{species_hint or 'any'}"
        if self.cache_embeddings and key in self.embedding_cache:
            return self.embedding_cache[key]
        model = self._ensure_model()
        emb = model.encode([normalized_query])  # shape (1, d), float32/64
        if isinstance(emb, np.ndarray) and emb.ndim == 1:
            emb = emb.reshape(1, -1)
        # ensure float32 for FAISS
        emb32 = emb.astype("float32", copy=False)
        if self.cache_embeddings:
            self.embedding_cache[key] = emb32
        return emb32

    def _search_with_threshold(
        self, query: str, k: int, threshold: float, species: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.has_search_engine():
            return []

        try:
            normalized_query = self._normalize_query(query)
            species_hint = species or self._infer_species(query)
            q_emb = self._embed_query(normalized_query, species_hint)

            # search a bit wider; FAISS returns distances (IP/L2 depending on build)
            k_search = int(min(max(k * 3, k), len(self._documents)))
            if k_search <= 0:
                return []

            distances, indices = self._index.search(q_emb, k_search)  # type: ignore

            results: List[Dict[str, Any]] = []
            dists = distances[0]
            idxs = indices[0]
            for i in range(len(dists)):
                idx = int(idxs[i])
                if idx < 0 or idx >= len(self._documents):
                    continue
                doc = self._documents[idx]

                if species_hint and not self._doc_matches_species(doc, species_hint):
                    continue

                dist = float(dists[i])
                base = self._improved_similarity_score(dist)
                final = self._boost_score_for_exact_matches(query, doc.get("text", ""), base)
                if final < threshold:
                    continue

                results.append(
                    {
                        "text": doc.get("text", ""),
                        "score": round(final, 4),
                        "index": idx,
                        "metadata": doc.get("metadata", {}),
                        "distance": dist,
                        "base_score": round(base, 4),
                        "threshold_used": threshold,
                    }
                )
                if len(results) >= k:
                    break

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:k]
        except Exception as e:
            logger.error("❌ Search error @threshold %.3f: %s", threshold, e)
            return []

    def search_with_adaptive_threshold(self, query: str, k: int = 5, species: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.has_search_engine():
            logger.error("❌ Search engine not available")
            return []

        t0 = time.time()
        if self.debug:
            logger.info("🔍 [Adaptive] query=%r k=%d species=%s", query[:120], k, species or "auto")

        tried: List[str] = []

        # normal
        tried.append("normal")
        results = self._search_with_threshold(query, k, self.threshold_config["normal"], species)
        threshold_used = "normal"

        # permissive
        if not results:
            tried.append("permissive")
            if self.debug:
                logger.info("🔍 [Adaptive] No hits @normal → permissive")
            results = self._search_with_threshold(query, k, self.threshold_config["permissive"], species)
            threshold_used = "permissive"

        # fallback
        if not results:
            tried.append("fallback")
            if self.debug:
                logger.info("🔍 [Adaptive] No hits @permissive → fallback")
            results = self._search_with_threshold(query, k, self.threshold_config["fallback"], species)
            threshold_used = "fallback"

        # no threshold
        if not results:
            tried.append("no_threshold")
            if self.debug:
                logger.info("🔍 [Adaptive] No hits @fallback → no_threshold")
            results = self._search_with_threshold(query, k, 0.0, species)
            threshold_used = "no_threshold"

        if self.debug:
            dt = time.time() - t0
            logger.info("✅ [Adaptive] done in %.3fs | used=%s | tried=%s | hits=%d",
                        dt, threshold_used, "→".join(tried), len(results))
            if results:
                logger.info("   Score range: %.3f - %.3f", results[0]["score"], results[-1]["score"])

        return results

    def search(self, query: str, k: int = 5, species: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.search_with_adaptive_threshold(query, k, species)

    # -------------------------
    # Utils
    # -------------------------
    def get_stats(self) -> Dict[str, Any]:
        return {
            "documents_loaded": len(self._documents),
            "search_available": self.has_search_engine(),
            "cache_enabled": bool(self.embedding_cache) if self.cache_embeddings else False,
            "cache_size": len(self.embedding_cache) if self.embedding_cache is not None else 0,
            "model": self.model_name,
            "max_workers": self.max_workers,
            "dependencies_ok": self._dependencies_ok,
            "faiss_total": int(getattr(self._index, "ntotal", 0)) if self._index is not None else 0,
            "similarity_threshold": self.threshold_config["normal"],
            "threshold_config": dict(self.threshold_config),
            "normalize_queries": self.normalize_queries,
            "ready": self.is_ready(),
        }

    def clear_cache(self) -> None:
        if self.embedding_cache is not None:
            n = len(self.embedding_cache)
            self.embedding_cache.clear()
            logger.info("🗑️ Cleared %d cached embeddings", n)

    def adjust_similarity_threshold(self, new_threshold: float) -> None:
        old = self.threshold_config["normal"]
        self.threshold_config["normal"] = float(max(0.0, min(1.0, new_threshold)))
        logger.info("🎯 Similarity threshold adjusted: %.3f → %.3f", old, self.threshold_config["normal"])

    def update_threshold_config(self, **kwargs: float) -> None:
        for name, value in kwargs.items():
            if name in self.threshold_config:
                old = self.threshold_config[name]
                self.threshold_config[name] = float(max(0.0, min(1.0, value)))
                logger.info("🎯 %s threshold: %.3f → %.3f", name, old, self.threshold_config[name])
            else:
                logger.warning("⚠️ Unknown threshold config: %s", name)

    def debug_search(self, query: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "query": query,
            "normalized_query": self._normalize_query(query),
            "has_search_engine": self.has_search_engine(),
            "documents_count": len(self._documents),
            "faiss_total": int(getattr(self._index, "ntotal", 0)) if self._index is not None else 0,
            "model_name": self.model_name,
            "cache_enabled": bool(self.embedding_cache) if self.cache_embeddings else False,
            "threshold_config": dict(self.threshold_config),
            "normalize_queries": self.normalize_queries,
        }
        try:
            if self.has_search_engine():
                norm = self._normalize_query(query)
                emb = self._embed_query(norm, None)
                distances, indices = self._index.search(emb, min(5, len(self._documents)))  # type: ignore
                info["faiss_search_success"] = True

                # threshold sampling
                thr_results = {}
                for name, val in self.threshold_config.items():
                    res = self._search_with_threshold(query, 3, val)
                    thr_results[name] = {
                        "threshold": val,
                        "results_count": len(res),
                        "top_scores": [r["score"] for r in res[:3]],
                    }
                info["threshold_results"] = thr_results

                # raw top
                top = []
                dists = distances[0]
                idxs = indices[0]
                for i in range(min(5, len(dists))):
                    idx = int(idxs[i])
                    if idx < 0 or idx >= len(self._documents):
                        continue
                    d = float(dists[i])
                    doc = self._documents[idx]
                    base = self._improved_similarity_score(d)
                    boosted = self._boost_score_for_exact_matches(query, doc.get("text", ""), base)
                    top.append(
                        {
                            "index": idx,
                            "distance": d,
                            "base_score": round(base, 4),
                            "boosted_score": round(boosted, 4),
                            "text_preview": doc.get("text", "")[:100],
                        }
                    )
                info["top_results"] = top
        except Exception as e:
            info["error"] = str(e)
        return info


# ---------------------------------------------------------------------
# Factories / Back-compat
# ---------------------------------------------------------------------
def create_optimized_embedder(**kwargs) -> FastRAGEmbedder:
    return FastRAGEmbedder(
        model_name=kwargs.get("model_name", "all-MiniLM-L6-v2"),
        cache_embeddings=kwargs.get("cache_embeddings", True),
        max_workers=kwargs.get("max_workers", 2),
        debug=kwargs.get("debug", True),
        similarity_threshold=kwargs.get("similarity_threshold", 0.20),
        normalize_queries=kwargs.get("normalize_queries", True),
    )

# Backward-compat alias to silence legacy imports:
RAGEmbedder = FastRAGEmbedder
