# rag/retriever.py
import os
from pathlib import Path
from typing import Optional
from langchain_community.vectorstores import FAISS
from rag.metadata_enrichment import detect_species
from rag.embedder import get_embedder

BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = BASE_DIR / "public"

def load_index(species: str):
    dir_path = INDEX_DIR / species
    if not dir_path.exists():
        return None
    return FAISS.load_local(str(dir_path), get_embedder(), allow_dangerous_deserialization=True)

def retrieve(query: str, top_k: int = 5):
    # Détection espèce
    sp = detect_species(query, query) or "global"
    idx = load_index(sp)
    if not idx:
        idx = load_index("global")

    if not idx:
        return []

    # Boost table-first
    boost_table = any(char.isdigit() for char in query) or any(
        u in query.lower() for u in ["kg", "g", "fcr", "%", "m³", "°c"]
    )
    if boost_table:
        results = idx.similarity_search_with_score(query, k=top_k * 2)
        table_results = [r for r in results if r[0].metadata.get("chunk_type") == "table"]
        text_results = [r for r in results if r[0].metadata.get("chunk_type") != "table"]
        return (table_results[:top_k] or text_results[:top_k])
    else:
        return idx.similarity_search_with_score(query, k=top_k)
