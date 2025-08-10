# -*- coding: utf-8 -*-
"""
RAG Engine (Intelia)
- 1) Essaie d'utiliser les 3 RAG chargés par app.main (app.state.rag[_broiler|_layer])
- 2) Fallback: lit des index FAISS sur disque (rag_index/*/index.faiss + index.pkl)
- Table-first: léger boost sur les chunks dont metadata.chunk_type == "table"
- Numeric-first query: ajoute age/phase/sex/line si présents
"""
from typing import Dict, Any, List, Tuple, Optional
import os, json, pickle
import numpy as np

try:
    import faiss  # fallback only
except Exception:
    faiss = None  # on ne casse pas si FAISS n’est pas dispo côté API

# ----------------------------
# Helpers de composition query
# ----------------------------
def _numeric_first_query(question: str, entities: Dict[str, Any]) -> str:
    parts = [question]
    for key in ("line", "sex", "phase"):
        v = entities.get(key)
        if v:
            parts.append(f"{key}:{v}")
    if entities.get("age_days") is not None:
        parts.append(f"age_days:{entities['age_days']}")
    if entities.get("age_weeks") is not None:
        parts.append(f"age_weeks:{entities['age_weeks']}")
    return " | ".join(parts)

def _pick_species_index_name(entities: Dict[str, Any]) -> str:
    sp = entities.get("species")
    return sp if sp in ("broiler", "layer") else "global"

def _rerank_table_first(scored: List[Tuple[int, float]], docstore: List[Dict[str, Any]], table_boost: float = 1.2):
    out = []
    for idx, score in scored:
        md = (docstore[idx].get("metadata") or {})
        if md.get("chunk_type") == "table":
            score *= table_boost
        out.append((idx, score))
    out.sort(key=lambda x: x[1], reverse=True)
    return out

def _format_sources(indices: List[int], docstore: List[Dict[str, Any]], limit=6):
    res = []
    for i in indices[:limit]:
        d = docstore[i]
        md = d.get("metadata") or {}
        res.append({
            "title": md.get("title") or md.get("source_path") or "source",
            "page": md.get("page"),
            "is_table": md.get("chunk_type") == "table"
        })
    return res

def _synthesize_answer(ids: List[int], docstore: List[Dict[str, Any]]) -> str:
    if not ids:
        return "Aucune source pertinente trouvée."
    snippets = []
    for i in ids[:3]:
        txt = (docstore[i].get("text") or docstore[i].get("content") or "")[:700]
        if txt:
            snippets.append(txt.strip())
    return "\n\n---\n".join(snippets) if snippets else "Aucune source pertinente trouvée."

# --------------------------------
# 1) Chemin “in‑memory” via app.state
# --------------------------------
def _get_embedder_from_app(species_name: str):
    """
    Récupère l'embedder préchargé par main.app (si dispo).
    Retourne None si indisponible.
    """
    try:
        from app.main import app  # l’instance FastAPI créée dans main.py
        if species_name == "broiler" and getattr(app.state, "rag_broiler", None):
            return app.state.rag_broiler
        if species_name == "layer" and getattr(app.state, "rag_layer", None):
            return app.state.rag_layer
        # global par défaut
        if getattr(app.state, "rag", None):
            return app.state.rag
    except Exception:
        pass
    return None

def _search_with_embedder(embedder, query: str, k: int = 12):
    """
    Essaie plusieurs API possibles pour ton FastRAGEmbedder.
    Doit retourner (docstore(list[dict]), scored(list[(idx, score)])).
    """
    # 1) API directe .search(query, k) -> liste d'objets {content/text, metadata, score}
    if hasattr(embedder, "search") and callable(embedder.search):
        try:
            results = embedder.search(query, top_k=k)
            # standardiser en (docstore, scored)
            docstore = []
            scored = []
            for r in results:
                # r peut être dict ou objet; on accède prudemment
                text = getattr(r, "text", None) or getattr(r, "content", None) or (r.get("text") if isinstance(r, dict) else None) or (r.get("content") if isinstance(r, dict) else None)
                meta = getattr(r, "metadata", None) or (r.get("metadata") if isinstance(r, dict) else None) or {}
                score = getattr(r, "score", None) or (r.get("score") if isinstance(r, dict) else None) or 0.0
                docstore.append({"text": text, "metadata": meta})
                scored.append((len(docstore)-1, float(score)))
            return docstore, scored
        except Exception:
            pass

    # 2) Si l’embedder expose un retriever avec .search(...)
    retr = getattr(embedder, "retriever", None)
    if retr and hasattr(retr, "search") and callable(retr.search):
        try:
            results = retr.search(query, top_k=k)
            docstore, scored = [], []
            for r in results:
                text = getattr(r, "text", None) or getattr(r, "content", None) or (r.get("text") if isinstance(r, dict) else None) or (r.get("content") if isinstance(r, dict) else None)
                meta = getattr(r, "metadata", None) or (r.get("metadata") if isinstance(r, dict) else None) or {}
                score = getattr(r, "score", None) or (r.get("score") if isinstance(r, dict) else None) or 0.0
                docstore.append({"text": text, "metadata": meta})
                scored.append((len(docstore)-1, float(score)))
            return docstore, scored
        except Exception:
            pass

    # 3) Sinon, pas d’API de recherche → None
    return None, None

# --------------------------------
# 2) Fallback FAISS sur disque
# --------------------------------
def _faiss_paths(index_name: str) -> Dict[str, str]:
    """
    Résout les chemins disque. On essaie d'abord les variables ENV spécifiques,
    sinon RAG_INDEX_ROOT (défaut: ./rag_index), puis ./rag_index/<index_name>.
    """
    # Overrides explicites
    env_map = {
        "global": os.getenv("RAG_INDEX_GLOBAL"),
        "broiler": os.getenv("RAG_INDEX_BROILER"),
        "layer": os.getenv("RAG_INDEX_LAYER"),
    }
    base = env_map.get(index_name)
    if base and os.path.isdir(base):
        return {
            "faiss": os.path.join(base, "index.faiss"),
            "pkl": os.path.join(base, "index.pkl"),
            "meta": os.path.join(base, "meta.json"),
        }

    root = os.getenv("RAG_INDEX_ROOT", "rag_index")
    folder = os.path.join(root, index_name)
    return {
        "faiss": os.path.join(folder, "index.faiss"),
        "pkl": os.path.join(folder, "index.pkl"),
        "meta": os.path.join(folder, "meta.json"),
    }

def _faiss_load(index_name: str):
    if faiss is None:
        raise RuntimeError("FAISS n'est pas disponible sur cette instance API.")
    paths = _faiss_paths(index_name)
    if not (os.path.exists(paths["faiss"]) and os.path.exists(paths["pkl"])):
        raise FileNotFoundError(f"Index FAISS introuvable pour {index_name}: {paths}")
    index = faiss.read_index(paths["faiss"])
    with open(paths["pkl"], "rb") as f:
        docstore = pickle.load(f)
    manifest = {}
    if os.path.exists(paths["meta"]):
        try:
            with open(paths["meta"], "r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception:
            pass
    return index, docstore, manifest

def _faiss_search(index, query_vec: np.ndarray, k: int = 12):
    D, I = index.search(query_vec.reshape(1, -1), k)
    # L2 → on convertit en score = -distance (plus haut = mieux)
    return [(int(i), -float(d)) for i, d in zip(I[0], D[0]) if i >= 0]

# --------------------------------
# Entrée principale
# --------------------------------
def answer_with_rag(question: str, entities: Dict[str, Any], intent=None) -> Dict[str, Any]:
    idx_name = _pick_species_index_name(entities)
    query = _numeric_first_query(question, entities)

    # 1) Essai via app.state.* (embedder déjà chargé par main.py)
    embedder = _get_embedder_from_app(idx_name)
    if embedder is not None and getattr(embedder, "has_search_engine", lambda: False)():
        docstore, scored = _search_with_embedder(embedder, query, k=12)
        if docstore is not None and scored is not None and len(docstore) > 0:
            # Si l’embedder ne fournit pas de score croissant, on garde tel quel.
            # On applique tout de même un petit rerank table-first si possible.
            scored = _rerank_table_first(scored, docstore, table_boost=1.2)
            top_ids = [i for i, _ in scored[:5]]
            sources = _format_sources(top_ids, docstore)
            answer_text = _synthesize_answer(top_ids, docstore)
            return {
                "text": answer_text,
                "documents_used": sources,
                "index_used": idx_name,
                "manifest": {"provider": "app.state", "documents": len(docstore)}
            }

    # 2) Fallback FAISS disque
    try:
        index, docstore, manifest = _faiss_load(idx_name)
    except Exception as e:
        return {
            "text": f"Aucune source disponible pour l’index '{idx_name}' ({e}).",
            "documents_used": [],
            "index_used": idx_name,
            "manifest": {"provider": "disk", "error": str(e)}
        }

    # Embedding de la requête : on essaye d’utiliser l’embedder global si dispo
    qvec: Optional[np.ndarray] = None
    if embedder is not None and hasattr(embedder, "embed"):
        try:
            vec = embedder.embed(query)
            qvec = np.asarray(vec, dtype="float32")
            qvec = qvec / (np.linalg.norm(qvec) + 1e-8)
        except Exception:
            qvec = None

    if qvec is None:
        # dernier recours : on ne sait pas encoder ici
        return {
            "text": "RAG non disponible: aucun encoder configuré pour la requête (fallback FAISS impossible).",
            "documents_used": [],
            "index_used": idx_name,
            "manifest": {"provider": "disk", "note": "embed_query_missing"}
        }

    scored = _faiss_search(index, qvec, k=12)
    scored = _rerank_table_first(scored, docstore, table_boost=1.2)

    top_ids = [i for i, _ in scored[:5]]
    sources = _format_sources(top_ids, docstore)
    answer_text = _synthesize_answer(top_ids, docstore)

    return {
        "text": answer_text,
        "documents_used": sources,
        "index_used": idx_name,
        "manifest": {"provider": "disk", **manifest}
    }
