# backend/rag/embedder.py
from __future__ import annotations

import os
import io
import json
import pickle
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Any, Dict

import numpy as np  # numpy est requis en runtime

logger = logging.getLogger(__name__)


# ------------------------------ Helpers généraux ------------------------------

def _norm_method(m: Optional[str]) -> str:
    """Normalise le nom du provider."""
    v = (m or "").strip().lower().replace("_", "-")
    if v in {"openai", "oai"}:
        return "OpenAI"
    if v in {"fastembed", "fast-embed", "onnx"}:
        return "FastEmbed"
    if v in {"sentence-transformers", "sentencetransformers", "st"}:
        return "SentenceTransformers"
    if v in {"tfidf", "tf-idf"}:
        return "TF-IDF"
    # défaut sûr et torch-free
    return "OpenAI"


def _read_pickle(p: Path) -> Any:
    with p.open("rb") as f:
        return pickle.load(f)


def _read_json(p: Path) -> Any:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _try_read_manifest(index_dir: Path) -> Dict[str, Any]:
    """
    Tente de lire un manifeste (index.pkl prioritaire, sinon meta.json).
    Retourne {} si rien trouvé.
    """
    # format "pickle" (souvent plus riche)
    pkl = index_dir / "index.pkl"
    if pkl.exists():
        try:
            data = _read_pickle(pkl)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning("⚠️ Échec lecture index.pkl: %s", e)

    # format json allégé
    meta = index_dir / "meta.json"
    if meta.exists():
        try:
            data = _read_json(meta)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning("⚠️ Échec lecture meta.json: %s", e)

    return {}


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(key)
    return v if v not in {None, ""} else default


# ------------------------------ Classe principale ------------------------------

class FastRAGEmbedder:
    """
    Loader d'index FAISS + générateur d'embeddings requête.
    Supporte 3 providers:
      - OpenAI (par défaut)  -> torch-free
      - FastEmbed (ONNX)     -> torch-free
      - SentenceTransformers -> nécessite sentence-transformers + torch (optionnel)

    Interface stable (utilisée ailleurs):
      - __init__(index_dir, method_override=None, model_name=None, ...)
      - embed_query(text) -> np.ndarray[1, D]
      - embed_texts(list[str]) -> np.ndarray[N, D]
    """

    # -------------------------- construction --------------------------

    def __init__(
        self,
        index_dir: str | Path,
        method_override: Optional[str] = None,
        model_name: Optional[str] = None,
        enhanced_query_normalization: bool = True,
        debug: bool = True,
    ) -> None:
        self.index_dir = Path(index_dir)
        self.debug = bool(debug)
        self.enhanced_query_normalization = bool(enhanced_query_normalization)

        # Flags & handles
        self._dependencies_ok: bool = False  # FAISS + numpy OK ?
        self._st_available: bool = False     # sentence-transformers dispo ?
        self.faiss = None                    # module faiss
        self.np = np                         # alias numpy
        self._st_model = None                # SentenceTransformers model
        self._fe_model = None                # FastEmbed model
        self._oai_client = None              # OpenAI client
        self._embed = None                   # callable d'embedding

        # Méthode & modèle (manifest + ENV + override)
        manifest = _try_read_manifest(self.index_dir)
        man_method = manifest.get("embedding_method") or manifest.get("method")
        man_model = manifest.get("model_name")

        env_method = _env("EMBEDDINGS_PROVIDER") or _env("EMBEDDING_METHOD")
        env_oai_model = _env("OPENAI_EMBEDDING_MODEL")

        # Ordre de priorité : override > ENV > manifest > défaut
        self.method: str = _norm_method(
            method_override or env_method or man_method or "OpenAI"
        )
        self.model_name: str = (
            model_name
            or (env_oai_model if self.method == "OpenAI" else None)
            or man_model
            or (
                "text-embedding-3-small"
                if self.method == "OpenAI"
                else "BAAI/bge-small-en-v1.5" if self.method == "FastEmbed"
                else "sentence-transformers/all-MiniLM-L6-v2"
            )
        )

        # Dimension (si absente du manifest, dérive par défaut)
        man_dim = manifest.get("embedding_dim")
        self.embedding_dim: int = int(
            man_dim
            if man_dim
            else (1536 if self.method == "OpenAI" else 384)  # défauts usuels
        )

        # Initialisation dépendances
        self._init_dependencies()

        logger.info(
            "🚀 Initializing Enhanced FastRAGEmbedder...\n   Method: %s\n   Model: %s\n   Dim: %s\n   Enhanced normalization: %s\n   Debug: %s",
            self.method, self.model_name, self.embedding_dim, self.enhanced_query_normalization, self.debug,
        )

        # Prépare le provider choisi (sans import lourd si inutile)
        self._prepare_provider()

        # Charge FAISS (obligatoire)
        self.index = self._load_faiss_index(self.index_dir)

    # -------------------------- dépendances --------------------------

    def _init_dependencies(self) -> None:
        """FAISS+NumPy obligatoires ; ST optionnel (ne bloque pas OpenAI/FastEmbed)."""
        # FAISS
        try:
            import faiss  # type: ignore
            self.faiss = faiss
            self._dependencies_ok = True
            logger.info("✅ faiss disponible")
        except Exception as e:
            self._dependencies_ok = False
            logger.error("❌ FAISS manquant: %s", e)
            return

        # SentenceTransformers (optionnel)
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self.SentenceTransformer = SentenceTransformer
            self._st_available = True
            logger.info("ℹ️ sentence-transformers disponible (optionnel)")
        except Exception as e:
            self._st_available = False
            logger.info("ℹ️ sentence-transformers indisponible (OK pour OpenAI/FastEmbed): %s", e)

    # -------------------------- provider setup --------------------------

    def _prepare_provider(self) -> None:
        """Construit le client/modèle pour la méthode choisie, sans charger ST si inutile."""
        method = self.method

        if method == "SentenceTransformers":
            if not self._st_available:
                raise RuntimeError(
                    "SentenceTransformers requis par le manifeste/ENV, mais non installé. "
                    "Installez 'sentence-transformers' et 'torch' OU reconstruisez les index avec OpenAI/FastEmbed."
                )
            # Chargement lazy du modèle ST
            self._st_model = self.SentenceTransformer(self.model_name, device="cpu")
            self._embed = self._embed_st
            # Si la dimension n'est pas fournie, tente de l'inférer
            try:
                test = self._st_model.encode(["dim"], convert_to_numpy=True)
                self.embedding_dim = int(test.shape[1])
            except Exception:
                pass
            return

        if method == "FastEmbed":
            try:
                from fastembed import TextEmbedding  # type: ignore
            except Exception as e:
                raise RuntimeError(
                    "FastEmbed sélectionné mais 'fastembed' n'est pas installé."
                ) from e
            self._fe_model = TextEmbedding(model_name=self.model_name)
            self._embed = self._embed_fastembed
            # infère dimension si manquante
            try:
                vecs = list(self._fe_model.embed(["dim"]))
                if vecs:
                    self.embedding_dim = int(len(vecs[0]))
            except Exception:
                pass
            return

        # OpenAI par défaut
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "OpenAI sélectionné mais paquet 'openai' indisponible."
            ) from e
        api_key = _env("OPENAI_API_KEY")
        if not api_key:
            # le client v1 peut lire depuis l'env, mais on informe clairement
            logger.warning("⚠️ OPENAI_API_KEY non défini dans l'environnement.")
        self._oai_client = OpenAI(api_key=api_key) if api_key else OpenAI()
        self._embed = self._embed_openai
        # dimension par défaut 1536 (text-embedding-3-small/-large)
        if not self.embedding_dim:
            self.embedding_dim = 1536

    # -------------------------- IO index FAISS --------------------------

    def _load_faiss_index(self, index_dir: Path):
        if not self._dependencies_ok:
            raise RuntimeError("FAISS indisponible — impossible de charger l'index.")

        idx = index_dir / "index.faiss"
        if not idx.exists():
            # Compat : certains projets nomment différemment
            alt = index_dir / "faiss.index"
            if alt.exists():
                idx = alt
            else:
                raise FileNotFoundError(f"Index FAISS introuvable: {idx}")

        index = self.faiss.read_index(str(idx))
        # Optionnel: check dimension cohérente
        d = int(index.d)
        if d != int(self.embedding_dim):
            logger.warning(
                "⚠️ Mismatch dimension: index.d=%s vs manifest/ENV dim=%s. "
                "Je conserve index.d comme source de vérité.",
                d, self.embedding_dim
            )
            self.embedding_dim = d
        logger.info("✅ Index FAISS chargé (%s), dim=%s", idx.name, self.embedding_dim)
        return index

    # -------------------------- embeddings --------------------------

    def _normalize_queries(self, texts: List[str]) -> List[str]:
        if not self.enhanced_query_normalization:
            return texts
        # Normalisation légère (minuscule/strip). Ajoute ici stemming/accents si besoin.
        return [t.strip() for t in texts]

    # --- OpenAI ---
    def _embed_openai(self, texts: List[str]) -> np.ndarray:
        # API v1 : limite large, on segmente quand même prudemment
        B = 512
        out: List[List[float]] = []
        for i in range(0, len(texts), B):
            chunk = texts[i:i+B]
            resp = self._oai_client.embeddings.create(
                model=self.model_name,
                input=chunk
            )
            out.extend([d.embedding for d in resp.data])
        arr = np.asarray(out, dtype="float32")
        # normalisation L2 pour compat IP si l'index l'attend
        self._maybe_normalize(arr)
        return arr

    # --- FastEmbed (ONNX) ---
    def _embed_fastembed(self, texts: List[str]) -> np.ndarray:
        vectors = list(self._fe_model.embed(texts))
        arr = np.asarray(vectors, dtype="float32")
        self._maybe_normalize(arr)
        return arr

    # --- SentenceTransformers ---
    def _embed_st(self, texts: List[str]) -> np.ndarray:
        arr = self._st_model.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # souvent utilisé avec IndexFlatIP
        ).astype("float32", copy=False)
        # déjà normalisé
        return arr

    def _maybe_normalize(self, arr: np.ndarray) -> None:
        """
        Normalise L2 in-place si l'index FAISS est de type IP et que les vecteurs
        n'ont pas déjà été normalisés. Ici on normalise systématiquement côté
        requête pour la compatibilité.
        """
        try:
            self.faiss.normalize_L2(arr)
        except Exception:
            # en cas d'index non-IP, la normalisation ne nuit pas mais on peut
            # ignorer silencieusement
            pass

    # -------------------------- API publique --------------------------

    def embed_query(self, text: str) -> np.ndarray:
        """
        Retourne un vecteur (1, D).
        """
        texts = self._normalize_queries([text])
        vecs = self._embed(texts)
        if vecs.ndim == 1:
            vecs = vecs.reshape(1, -1)
        return vecs

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Retourne un tableau (N, D).
        """
        texts = self._normalize_queries(texts)
        vecs = self._embed(texts)
        return vecs

    # Compat : certaines implémentations attendent un "load_index"
    def load_index(self) -> bool:
        """
        Pour compatibilité — l'index est déjà chargé en __init__.
        Retourne True si tout est OK.
        """
        return bool(self.index)

    def close(self) -> None:
        """Libère les ressources éventuelles (actuellement no-op)."""
        self._st_model = None
        self._fe_model = None
        self._oai_client = None


# ------------------------------ Exports ------------------------------

__all__ = ["FastRAGEmbedder"]
