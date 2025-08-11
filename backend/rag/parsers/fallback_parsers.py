# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Optional, Dict, Any
import os
import logging

from .parser_base import BaseParser, ParserCapability, Document

logger = logging.getLogger(__name__)

class TikaFallbackParser(BaseParser):
    def __init__(self):
        try:
            import tika  # noqa
            self._ok = True
        except Exception:
            self._ok = False

    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="TikaFallbackParser",
            supported_extensions=["*"],
            breed_types=["Any"],
            data_types=["universal"],
            quality_score="good",
            description="Apache Tika universal fallback",
            priority=10,
        )

    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        return 0.3 if self._ok else 0.0

    def parse(self, file_path: str) -> List[Document]:
        if not self._ok:
            return []
        try:
            from tika import parser as tparser
            parsed = tparser.from_file(file_path)
            content = (parsed.get("content") or "").strip()
            meta = parsed.get("metadata", {}) or {}
            if not content:
                return []
            d = Document(
                page_content=content,
                metadata=self.create_base_metadata(file_path, {
                    "document_type": "tika_universal",
                    "tika_content_type": meta.get("Content-Type", "unknown"),
                    "chunk_type": "text",
                    "content_length": len(content),
                }),
            )
            # keep some tika meta keys (safe types only)
            for k, v in meta.items():
                if isinstance(v, (str, int, float)):
                    d.metadata[f"tika_{k.lower().replace(' ', '_')}"] = v
            return [d]
        except Exception as e:
            logger.warning("Tika failed: %s", e)
            return []

class RawTextFallbackParser(BaseParser):
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="RawTextFallbackParser",
            supported_extensions=["*"],
            breed_types=["Any"],
            data_types=["raw_text"],
            quality_score="basic",
            description="Read-anything raw text extraction (last resort)",
            priority=5,
        )

    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        return 0.2 if os.path.exists(file_path) else 0.0

    def parse(self, file_path: str) -> List[Document]:
        content = self._extract(file_path)
        if not content or len(content.strip()) < 10:
            return []
        d = Document(
            page_content=content,
            metadata=self.create_base_metadata(file_path, {
                "document_type": "raw_text",
                "chunk_type": "text",
                "content_length": len(content),
                "warning": "Raw binary → text fallback; quality may be low.",
            }),
        )
        return [d]

    def _extract(self, file_path: str, max_bytes: int = 200_000) -> str:
        # 1) utf-8 text
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                s = f.read(max_bytes)
                if self._readable(s): return s
        except Exception:
            pass
        # 2) binary → utf-8
        try:
            with open(file_path, "rb") as f:
                b = f.read(max_bytes)
            s = b.decode("utf-8", errors="ignore")
            if self._readable(s): return s
        except Exception:
            pass
        # 3) latin-1
        try:
            with open(file_path, "rb") as f:
                b = f.read(max_bytes)
            s = b.decode("latin-1", errors="ignore")
            if self._readable(s): return s
        except Exception:
            pass
        # 4) printable ascii
        try:
            with open(file_path, "rb") as f:
                b = f.read(max_bytes)
            s = "".join(chr(x) for x in b if 32 <= x <= 126 or x in (9, 10, 13))
            if self._readable(s): return s
        except Exception:
            pass
        return ""

    def _readable(self, s: str, min_ratio: float = 0.7) -> bool:
        if len(s) < 10: return False
        printable = sum(1 for c in s if c.isprintable() or c.isspace())
        return (printable / len(s)) >= min_ratio
