# rag/embedder.py
"""
FastRAGEmbedder - Version corrigée et renforcée
- Normalisation non-destructive (ne remplace plus "poulet" par "volaille")
- Détection d'espèce (broiler/layer) et filtrage des résultats par métadonnées/chemin
- Seuils adaptatifs légèrement plus stricts pour réduire les faux positifs
- API compatible : search(query, k=5, species: Optional[str] = None)
"""

from __future__ import annotations

import os
import time
import pickle
import logging
import re
from typing import List, Dict, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class FastRAGEmbedder:
    """
    Moteur RAG basé FAISS + sentence-transformers
    - Chargement d'un index FAISS + documents normalisés
    - Recherche vectorielle avec score amélioré et boosting exact-match
    - Seuils adaptatifs (strict/normal/permissive/fallback)
    - Détection et filtrage d'espèce (broiler/layer)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
        cache_embeddings: bool = True,
        max_workers: int = 2,
        debug: bool = True,
        similarity_threshold: float = 0.20,  # normal
        normalize_queries: bool = True,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.cache_embeddings = cache_embeddings
        self.max_workers = max_workers
        self.debug = debug
        self.similarity_threshold = similarity_threshold
        self.normalize_queries = normalize_queries

        # Seuils adaptatifs (un peu plus stricts que la version précédente)
        self.threshold_config = {
            "strict": 0.25,
            "normal": max(0.0, min(1.0, similarity_threshold)),  # par défaut 0.20
            "permissive": 0.15,
            "fallback": 0.10,
        }

        # État
        self.embedding_cache: Dict[str, np.ndarray] = {} if cache_embeddings else {}
        self.documents: List[Dict[str, Any]] = []
        self.index = None
        self.search_engine_available = False

        # Normalisation
        self._init_normalization_patterns()

        # Dépendances
        self._init_dependencies()

        if self.debug:
            logger.info("🚀 Initializing FastRAGEmbedder (Adaptive Thresholds)...")
            logger.info(f"   Model: {self.model_name}")
            logger.info("   Dimension: 384")
            logger.info(f"   Dependencies available: {self._check_dependencies()}")
            logger.info(f"   Cache enabled: {self.cache_embeddings}")
            logger.info(f"   Max workers: {self.max_workers}")
            logger.info(f"   Thresholds: {self.threshold_config}")
            logger.info(f"   Query normalization: {self.normalize_queries}")
            logger.info(f"   Debug enabled: {self.debug}")

    # -------------------------------------------------------------------------
    # Initialisation / dépendances
    # -------------------------------------------------------------------------
    def _init_dependencies(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            self.SentenceTransformer = SentenceTransformer
            import faiss  # noqa: F401
            self.faiss = faiss
            self.np = np
            logger.info("✅ sentence-transformers available")
            logger.info("✅ faiss available")
            logger.info("✅ numpy available")
            self.dependencies_available = True
        except Exception as e:
            logger.error("❌ Missing dependencies: %s", e)
            self.dependencies_available = False

    def _check_dependencies(self) -> bool:
        return hasattr(self, "SentenceTransformer") and hasattr(self, "faiss") and hasattr(self, "np")

    # -------------------------------------------------------------------------
    # Normalisation / heuristiques
    # -------------------------------------------------------------------------
    def _init_normalization_patterns(self) -> None:
        self.normalization_patterns = {
            # Conversions temporelles
            "temporal_conversions": [
                (r"(\d+)\s*semaines?", lambda m: f"{int(m.group(1)) * 7} jours"),
                (r"(\d+)\s*mois", lambda m: f"{int(m.group(1)) * 30} jours"),
                (r"(\d+)j\b", r"\1 jours"),
                (r"(\d+)s\b", r"\1 semaines"),
            ],
            # Termes agro — **conserver** l'intention d'espèce !
            "agricultural_terms": [
                (r"\bbroilers?\b", "poulet de chair"),
                (r"\bpoulets?\b", "poulet de chair"),
                (r"\bpoules?\b", "poule pondeuse"),
                (r"\bcoqs?\b", "poule pondeuse"),
                (r"\bgallines?\b", "poule pondeuse"),
                (r"\bRoss\s*308\b", "poulet de chair Ross 308"),
                (r"\bCobb\s*500\b", "poulet de chair Cobb 500"),
            ],
            # Poids
            "weight_conversions": [
                (r"(\d+)\s*kg\b", lambda m: f"{int(m.group(1)) * 1000} grammes"),
                (r"(\d+)\s*g\b", r"\1 grammes"),
                (r"(\d+)\s*lbs?\b", lambda m: f"{int(float(m.group(1)) * 453.592)} grammes"),
            ],
            # Températures
            "temperature_conversions": [
                (r"(\d+)°?C\b", r"\1 degrés Celsius"),
                (r"(\d+)°?F\b", lambda m: f"{round((int(m.group(1)) - 32) * 5/9)} degrés Celsius"),
            ],
            # Synonymes
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
                logger.info("🔄 Query normalized:")
                logger.info(f"   Original: {original}")
                logger.info(f"   Normalized: {normalized}")
            return normalized
        except Exception as e:
            logger.error("❌ Error normalizing query: %s", e)
            return query.lower()

    def _infer_species(self, query: str) -> Optional[str]:
        """
        Essaye de deviner 'broiler' ou 'layer' à partir de la requête.
        Retourne None si indéterminé / ambigu.
        """
        q = query.lower()
        # indices layer
        if any(w in q for w in ["pondeuse", "layer", "lohmann", "hy-line", "w36", "w-36", "w80", "w-80", "ponte"]):
            return "layer"
        # indices broiler (éviter si la requête parle explicitement d'œufs/pondeuse)
        if any(w in q for w in ["broiler", "poulet de chair", "ross 308", "cobb 500", "croissance", "poids"]):
            if any(w in q for w in ["pondeuse", "layer", "œuf", "oeuf", "ponte", "lohmann", "hy-line"]):
                return None
            return "broiler"
        return None

    def _doc_matches_species(self, doc: Dict[str, Any], species: str) -> bool:
        """
        Vérifie si un doc correspond à l'espèce (via metadata/chemin).
        """
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

        # Arborescence connue : /species/broiler/ ou /species/layer/
        if f"/species/{species}/" in joined or f"\\species\\{species}\\" in joined:
            return True

        # Heuristiques
        if species == "broiler" and any(w in joined for w in ["broiler", "ross", "cobb"]):
            return True
        if species == "layer" and any(w in joined for w in ["layer", "lohmann", "hy-line"]):
            return True
        return False

    # -------------------------------------------------------------------------
    # Chargement index
    # -------------------------------------------------------------------------
    def load_index(self, index_path: str) -> bool:
        if not self._check_dependencies():
            logger.error("❌ Dependencies not available for loading index")
            return False
        try:
            faiss_file = os.path.join(index_path, "index.faiss")
            pkl_file = os.path.join(index_path, "index.pkl")

            if not os.path.exists(faiss_file) or not os.path.exists(pkl_file):
                logger.error("❌ Index files not found in %s", index_path)
                return False

            logger.info("🔄 Loading FAISS index from %s", faiss_file)
            t0 = time.time()
            self.index = self.faiss.read_index(faiss_file)
            logger.info("✅ FAISS index loaded in %.2fs", time.time() - t0)
            logger.info("🔍 FAISS index info: ntotal=%s, d=%s", self.index.ntotal, self.index.d)

            logger.info("🔄 Loading documents from %s", pkl_file)
            t1 = time.time()
            with open(pkl_file, "rb") as f:
                raw_documents = pickle.load(f)
            self.documents = self._normalize_documents(raw_documents)
            logger.info("✅ Documents loaded in %.2fs", time.time() - t1)
            logger.info("🔍 Total documents: %d", len(self.documents))

            if self.index.ntotal != len(self.documents):
                logger.warning(
                    "⚠️ Index mismatch: FAISS has %d vectors, but %d documents",
                    self.index.ntotal,
                    len(self.documents),
                )

            self.search_engine_available = True
            logger.info("✅ Index loaded successfully - Search engine ready")
            return True
        except Exception as e:
            logger.error("❌ Error loading index: %s", e)
            return False

    def _normalize_documents(self, raw_documents: Any) -> List[Dict[str, Any]]:
        if self.debug:
            logger.info("🔍 DEBUG: Normalizing documents...")
            logger.info("   Raw type: %s", type(raw_documents))

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

            if self.debug:
                logger.info("🔍 DEBUG: Normalized %d documents", len(normalized))
                if normalized:
                    preview = normalized[0]["text"][:100].replace("\n", " ")
                    logger.info("   First document preview: %s...", preview)
        except Exception as e:
            logger.error("❌ Error normalizing documents: %s", e)

        return normalized

    # -------------------------------------------------------------------------
    # Similarité / scoring
    # -------------------------------------------------------------------------
    def _improved_similarity_score(self, distance: float) -> float:
        if distance <= 0:
            return 1.0
        # courbe exponentielle inverse
        similarity = float(np.exp(-distance * 1.5))
        return max(0.0, min(1.0, similarity))

    def _boost_score_for_exact_matches(self, query: str, text: str, base_score: float) -> float:
        qw = set(query.lower().split())
        tw = set(text.lower().split())
        if not qw:
            return base_score
        overlap_ratio = len(qw.intersection(tw)) / len(qw)
        boosted = min(1.0, base_score * (1.0 + overlap_ratio * 0.3))
        if self.debug and boosted > base_score * 1.1:
            logger.info("   📈 Score boosted: %.3f → %.3f (overlap: %.2f)", base_score, boosted, overlap_ratio)
        return boosted

    # -------------------------------------------------------------------------
    # Recherche
    # -------------------------------------------------------------------------
    def has_search_engine(self) -> bool:
        ok = self.search_engine_available and self.index is not None and len(self.documents) > 0 and self._check_dependencies()
        if not ok and self.debug:
            logger.warning("🔍 Search engine not ready:")
            logger.warning("   search_engine_available: %s", self.search_engine_available)
            logger.warning("   index is not None: %s", self.index is not None)
            logger.warning("   documents > 0: %s", len(self.documents) > 0)
            logger.warning("   dependencies_ok: %s", self._check_dependencies())
        return ok

    def _search_with_threshold(
        self,
        query: str,
        k: int,
        threshold: float,
        species: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self.has_search_engine():
            return []

        try:
            normalized_query = self._normalize_query(query)
            species_hint = species or self._infer_species(query)

            # Embedding requête (avec cache)
            key = f"{normalized_query}|{species_hint or 'any'}"
            if self.cache_embeddings and key in self.embedding_cache:
                q_emb = self.embedding_cache[key]
            else:
                model = self.SentenceTransformer(self.model_name)
                q_emb = model.encode([normalized_query])  # shape (1, d)
                if self.cache_embeddings:
                    self.embedding_cache[key] = q_emb

            if q_emb.ndim == 1:
                q_emb = q_emb.reshape(1, -1)

            # Chercher plus large puis filtrer
            k_search = min(max(k * 3, k), len(self.documents), self.index.ntotal)
            distances, indices = self.index.search(q_emb.astype("float32"), k_search)

            results: List[Dict[str, Any]] = []
            for i in range(len(distances[0])):
                idx = int(indices[0][i])
                if idx < 0 or idx >= len(self.documents):
                    continue

                doc = self.documents[idx]

                # Filtre d'espèce (si déduite/forcée)
                if species_hint and not self._doc_matches_species(doc, species_hint):
                    continue

                dist = float(distances[0][i])
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
            logger.error("❌ Search error with threshold %.3f: %s", threshold, e)
            return []

    def search_with_adaptive_threshold(
        self, query: str, k: int = 5, species: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.has_search_engine():
            logger.error("❌ Search engine not available")
            return []

        t0 = time.time()
        if self.debug:
            logger.info("🔍 [Adaptive] Starting adaptive threshold search")
            logger.info("   Query: %s...", query[:120])
            logger.info("   Requested k: %d", k)
            if species:
                logger.info("   Species (forced): %s", species)

        tried = []
        # 1) normal
        tried.append("normal")
        results = self._search_with_threshold(query, k, self.threshold_config["normal"], species)
        threshold_used = "normal"

        # 2) permissive
        if not results:
            tried.append("permissive")
            if self.debug:
                logger.info("🔍 [Adaptive] Aucun résultat avec seuil normal, essai permissif")
            results = self._search_with_threshold(query, k, self.threshold_config["permissive"], species)
            threshold_used = "permissive"

        # 3) fallback
        if not results:
            tried.append("fallback")
            if self.debug:
                logger.info("🔍 [Adaptive] Aucun résultat avec seuil permissif, essai fallback")
            results = self._search_with_threshold(query, k, self.threshold_config["fallback"], species)
            threshold_used = "fallback"

        # 4) sans seuil (dernier recours, tri par score)
        if not results:
            tried.append("no_threshold")
            if self.debug:
                logger.info("🔍 [Adaptive] Aucun résultat avec fallback, recherche sans seuil")
            results = self._search_with_threshold(query, k, 0.0, species)
            threshold_used = "no_threshold"

        if self.debug:
            dt = time.time() - t0
            logger.info("✅ [Adaptive] Search completed in %.3fs", dt)
            logger.info("   Threshold used: %s (tried: %s)", threshold_used, " → ".join(tried))
            logger.info("   Results found: %d", len(results))
            if results:
                logger.info("   Score range: %.3f - %.3f", results[0]["score"], results[-1]["score"])
                for i, r in enumerate(results[:3], 1):
                    preview = r["text"][:80].replace("\n", " ")
                    logger.info("   #%d: Score %.3f - %s...", i, r["score"], preview)

        return results

    def search(self, query: str, k: int = 5, species: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recherche publique (compatible). Ajout d'un paramètre optionnel species:
        - None (auto) | "broiler" | "layer"
        """
        return self.search_with_adaptive_threshold(query, k, species)

    # -------------------------------------------------------------------------
    # Utilitaires
    # -------------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        return {
            "documents_loaded": len(self.documents),
            "search_available": self.has_search_engine(),
            "cache_enabled": bool(self.embedding_cache),
            "cache_size": len(self.embedding_cache) if self.embedding_cache is not None else 0,
            "model": self.model_name,
            "max_workers": self.max_workers,
            "dependencies_ok": self._check_dependencies(),
            "faiss_total": self.index.ntotal if self.index is not None else 0,
            "similarity_threshold": self.similarity_threshold,
            "threshold_config": self.threshold_config,
            "normalize_queries": self.normalize_queries,
        }

    def clear_cache(self) -> None:
        if self.embedding_cache is not None:
            n = len(self.embedding_cache)
            self.embedding_cache.clear()
            logger.info("🗑️ Cleared %d cached embeddings", n)

    def adjust_similarity_threshold(self, new_threshold: float) -> None:
        old = self.similarity_threshold
        self.similarity_threshold = max(0.0, min(1.0, new_threshold))
        self.threshold_config["normal"] = self.similarity_threshold
        logger.info("🎯 Similarity threshold adjusted: %.3f → %.3f", old, self.similarity_threshold)

    def update_threshold_config(self, **kwargs: float) -> None:
        for name, value in kwargs.items():
            if name in self.threshold_config:
                old = self.threshold_config[name]
                self.threshold_config[name] = max(0.0, min(1.0, float(value)))
                logger.info("🎯 %s threshold: %.3f → %.3f", name, old, self.threshold_config[name])
            else:
                logger.warning("⚠️ Unknown threshold config: %s", name)

    def debug_search(self, query: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "query": query,
            "normalized_query": self._normalize_query(query),
            "has_search_engine": self.has_search_engine(),
            "documents_count": len(self.documents),
            "faiss_total": self.index.ntotal if self.index is not None else 0,
            "model_name": self.model_name,
            "cache_enabled": bool(self.embedding_cache),
            "threshold_config": self.threshold_config,
            "normalize_queries": self.normalize_queries,
        }
        if self.has_search_engine():
            try:
                norm = self._normalize_query(query)
                model = self.SentenceTransformer(self.model_name)
                emb = model.encode([norm])
                info["embedding_shape"] = getattr(emb, "shape", None)
                if emb.ndim == 1:
                    emb = emb.reshape(1, -1)
                distances, indices = self.index.search(emb.astype("float32"), 5)
                info["faiss_search_success"] = True

                # Tester tous les seuils
                thr_results = {}
                for name, val in self.threshold_config.items():
                    res = self._search_with_threshold(query, 3, val)
                    thr_results[name] = {
                        "threshold": val,
                        "results_count": len(res),
                        "top_scores": [r["score"] for r in res[:3]],
                    }
                info["threshold_results"] = thr_results

                # Top bruts sans filtrage (5)
                top = []
                for i in range(min(5, len(distances[0]))):
                    idx = int(indices[0][i])
                    if idx < 0 or idx >= len(self.documents):
                        continue
                    d = float(distances[0][i])
                    doc = self.documents[idx]
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


# =============================================================================
# Factories / compat
# =============================================================================

def create_optimized_embedder(**kwargs) -> FastRAGEmbedder:
    """
    Factory avec bons défauts.
    """
    return FastRAGEmbedder(
        cache_embeddings=True,
        max_workers=2,
        debug=kwargs.get("debug", True),
        similarity_threshold=kwargs.get("similarity_threshold", 0.20),
        normalize_queries=kwargs.get("normalize_queries", True),
        model_name=kwargs.get("model_name", "all-MiniLM-L6-v2"),
        api_key=kwargs.get("api_key"),
    )


def FastRAGEmbedder_v1(*args, **kwargs) -> FastRAGEmbedder:
    """
    Alias compatibilité avec defaults améliorés.
    """
    kwargs.setdefault("similarity_threshold", 0.20)
    kwargs.setdefault("normalize_queries", True)
    kwargs.setdefault("model_name", "all-MiniLM-L6-v2")
    return FastRAGEmbedder(*args, **kwargs)
