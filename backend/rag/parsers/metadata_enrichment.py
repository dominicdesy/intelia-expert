# -*- coding: utf-8 -*-
"""
If a chunk is recognized as a table (pandas/markdown/html), force chunk_type="table".
"""
def enrich(metadata: dict, is_table: bool=False) -> dict:
    md = dict(metadata or {})
    if is_table:
        md["chunk_type"] = "table"
    return md
