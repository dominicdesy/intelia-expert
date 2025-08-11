# -*- coding: utf-8 -*-
"""
parser_base.py — base classes & helpers for RAG parsers

- Unified data model:
    * Document(page_content: str, metadata: dict)
    * ParserCapability (metadata about a parser)
    * BaseParser (abstract interface)

- Helpers:
    * chunk_text(text, chunk_size=1200, overlap=120) -> List[str]
    * to_docdict(Document|dict|str) -> {'content','metadata','source'}

- Compatibility shim for legacy build pipeline:
    * ParsedChunk(text: str, metadata: dict)
    * to_parsed_chunk(Document|dict|str) -> ParsedChunk

Notes:
- Optional metadata enrichment (safe to miss): metadata_enrichment.py may define
  MetadataEnricher.enrich_metadata(text, meta) and extract_hierarchical_metadata(path)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional enrichment import (safe if absent)
# ---------------------------------------------------------------------------
try:
    from .metadata_enrichment import MetadataEnricher, extract_hierarchical_metadata
except Exception:
    def extract_hierarchical_metadata(_: str) -> Dict[str, str]:
        return {}

    class MetadataEnricher:  # type: ignore
        @staticmethod
        def enrich_metadata(text: str, existing_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            return existing_metadata or {}

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ParserCapability:
    """
    Describes what a parser can handle.
    - supported_extensions: e.g. ['.pdf', '.txt']
    - breed_types: domain facets (e.g. ['broiler','layer','Any'])
    - data_types: e.g. ['text','table','structured_csv']
    - quality_score: 'basic' | 'good' | 'high'
    - priority: selection precedence (higher wins)
    """
    name: str
    supported_extensions: List[str]
    breed_types: List[str]
    data_types: List[str]
    quality_score: str
    description: str
    priority: int = 50


@dataclass
class Document:
    """
    Standard unit returned by parsers before normalization.
    """
    page_content: str
    metadata: Dict[str, Any]


class BaseParser:
    """
    Base class for all parsers.
    Implement:
        - capability (property)
        - can_parse(file_path, content_sample=None) -> float (0..1)
        - parse(file_path) -> List[Document]
    """

    # --- required API --------------------------------------------------------
    @property
    def capability(self) -> ParserCapability:
        raise NotImplementedError

    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        raise NotImplementedError

    def parse(self, file_path: str) -> List[Document]:
        raise NotImplementedError

    # --- helpers -------------------------------------------------------------
    def create_base_metadata(self, file_path: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build a consistent metadata dict for a chunk.
        """
        p = Path(file_path)
        base = {
            "source_file": str(p),
            "file_name": p.name,
            "file_stem": p.stem,
            "file_extension": p.suffix.lower(),
            "parser_name": self.capability.name,
            "parser_priority": self.capability.priority,
            **extract_hierarchical_metadata(str(p)),
        }
        if extra:
            base.update(extra)
        return base

    def enrich_with_content_metadata(self, text: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        (Optional) apply metadata enrichment based on text content.
        Safe no-op if enrichment module isn't available.
        """
        try:
            return MetadataEnricher.enrich_metadata(text, meta)
        except Exception as e:
            logger.debug("Metadata enrichment skipped: %s", e)
            return meta

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DocLike = Union[Document, Dict[str, Any], str]

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 120) -> List[str]:
    """
    Greedy chunker with boundary awareness.
    """
    if not text:
        return []
    n = len(text)
    start = 0
    chunks: List[str] = []

    # Reasonable guards
    chunk_size = max(200, int(chunk_size))
    overlap = max(0, min(int(overlap), chunk_size // 2))

    while start < n:
        end = min(start + chunk_size, n)

        # Try to end at a natural boundary within [start+overlap, end]
        boundary_end = end
        window_start = min(max(start + overlap, start), end)
        best = -1
        for sep in (".\n", ". ", "\n\n", "\n", " "):
            pos = text.rfind(sep, window_start, end)
            if pos > best:
                best = pos
                boundary_end = pos + len(sep) if pos != -1 else boundary_end

        end = boundary_end
        if end <= start:
            end = min(start + chunk_size, n)

        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= n:
            break
        # step forward with overlap
        start = max(end - overlap, start + 1)

    return chunks


def to_docdict(x: DocLike, default_source: str = "") -> Dict[str, Any]:
    """
    Normalize Document|dict|string -> {'content','metadata','source'}
    """
    if isinstance(x, Document):
        meta = x.metadata or {}
        src = meta.get("source_file", default_source) or default_source
        return {"content": x.page_content, "metadata": meta, "source": src}

    if isinstance(x, dict):
        content = x.get("content") or x.get("page_content") or ""
        meta = x.get("metadata") or {}
        src = x.get("source") or meta.get("source_file", default_source) or default_source
        return {"content": str(content), "metadata": meta, "source": src}

    # plain string
    return {"content": str(x), "metadata": {"source_file": default_source}, "source": default_source}

# ---------------------------------------------------------------------------
# Legacy compatibility shim
# ---------------------------------------------------------------------------

@dataclass
class ParsedChunk:
    """
    Legacy unit expected by older build_rag/parser_router.
    Keep fields name-compatible with the old pipeline.
    """
    text: str
    metadata: Dict[str, Any]


def to_parsed_chunk(obj: DocLike, default_source: str = "") -> ParsedChunk:
    """
    Adapt Document|dict|str into ParsedChunk for the legacy build.
    """
    if isinstance(obj, Document):
        return ParsedChunk(text=obj.page_content or "", metadata=obj.metadata or {})
    if isinstance(obj, dict):
        content = obj.get("content") or obj.get("page_content") or ""
        meta = obj.get("metadata") or {}
        if default_source and "source_file" not in meta:
            meta["source_file"] = default_source
        return ParsedChunk(text=str(content), metadata=meta)
    # string
    return ParsedChunk(text=str(obj), metadata={"source_file": default_source})

# ---------------------------------------------------------------------------

__all__ = [
    "ParserCapability",
    "Document",
    "BaseParser",
    "chunk_text",
    "to_docdict",
    # legacy
    "ParsedChunk",
    "to_parsed_chunk",
]
