# rag/parsers/performance_parser.py
import os
import pandas as pd
from rag.parsers.parser_base import ParserBase
from rag.metadata_enrichment import enrich_metadata

class PerformanceParser(ParserBase):
    name = "performance"

    def supports(self, file_path, mime, hints):
        return "performance" in hints.get("domains", [])

    def parse(self, file_path, mime):
        try:
            df = pd.read_excel(file_path)
        except:
            return []
        df.columns = [c.strip().lower() for c in df.columns]
        df = df[[c for c in df.columns if "age" in c or "weight" in c or "fcr" in c or "mortality" in c]]
        metadata = enrich_metadata(file_path, df.to_csv(index=False), chunk_type="table", domain="performance")
        yield {"text": df.to_csv(index=False), "metadata": metadata}
