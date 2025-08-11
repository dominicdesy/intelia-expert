# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Optional, Tuple
from pathlib import Path

from .parser_base import Document, to_docdict
from .table_parsers import GeneralCSVTableParser, GeneralExcelTableParser
from .general_parsers import GeneralTextLikeParser
from .fallback_parsers import TikaFallbackParser, RawTextFallbackParser

PARSERS = [
    # table-first first
    GeneralCSVTableParser(),
    GeneralExcelTableParser(),
    # generic text-like (PDF/TXT/MD/HTML with OCR fallback)
    GeneralTextLikeParser(),
    # fallbacks
    TikaFallbackParser(),
    RawTextFallbackParser(),
]

def _best_parser(file_path: str) -> Tuple[Optional[object], float]:
    best, score = None, 0.0
    for p in PARSERS:
        s = p.can_parse(file_path)
        if s > score:
            best, score = p, s
    return best, score

def parse_document(file_path: str) -> List[dict]:
    parser, score = _best_parser(file_path)
    if not parser:
        return []
    docs: List[Document] = parser.parse(file_path)
    # normalize to dict format expected by writer/indexer
    return [to_docdict(d, default_source=file_path) for d in docs]
