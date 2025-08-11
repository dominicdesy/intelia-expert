# rag/metadata_schema.py
from __future__ import annotations
from typing import TypedDict, Literal, NotRequired, Dict, Any, List

ChunkType = Literal["text", "table", "image", "figure", "code", "other"]

class ChunkMeta(TypedDict, total=False):
    doc_id: str
    source: str                 # chemin/URL du document source
    section: NotRequired[str]
    page: NotRequired[int]
    species: NotRequired[Literal["broiler", "layer", "global"]]
    role_hint: NotRequired[str] # ex: vet, grower, nutritionist
    chunk_type: NotRequired[ChunkType]
    tags: NotRequired[List[str]]
    extra: NotRequired[Dict[str, Any]]

def ensure_chunk_type(meta: Dict[str, Any], default: ChunkType = "text") -> Dict[str, Any]:
    if "chunk_type" not in meta:
        meta["chunk_type"] = default
    return meta
