# -*- coding: utf-8 -*-
"""
Ensure table chunks carry metadata["chunk_type"]="table".
Integrate with your actual table parsing implementation.
"""
def make_table_chunk(content, metadata: dict):
    metadata = dict(metadata or {})
    metadata["chunk_type"] = "table"
    return {"content": content, "metadata": metadata}
