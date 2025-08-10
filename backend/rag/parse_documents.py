# -*- coding: utf-8 -*-
"""
Ensure index writer preserves metadata["chunk_type"].
"""
from .parsers.document_parsers import parse_document

def parse_documents(paths):
    for p in paths:
        for chunk in parse_document(p):
            yield chunk
