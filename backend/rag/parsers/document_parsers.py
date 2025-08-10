# -*- coding: utf-8 -*-
"""
Router for document parsers; propagate table flag when appropriate.
Replace with your real parsing pipeline.
"""
from .table_parsers import make_table_chunk
from .metadata_enrichment import enrich

def parse_document(doc_path: str):
    # Example: pretend we found a markdown table
    content = "| Age | Poids |\n|---|---|\n| 35j | 1.9kg |"
    md = enrich({"source_path": doc_path}, is_table=True)
    yield make_table_chunk(content, md)
