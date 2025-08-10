# rag/parsers/nutrition_parser.py
import os
import pandas as pd
from rag.parsers.parser_base import ParserBase
from rag.metadata_enrichment import enrich_metadata

class NutritionParser(ParserBase):
    name = "nutrition"

    def supports(self, file_path, mime, hints):
        return "nutrition" in hints.get("domains", [])

    def parse(self, file_path, mime):
        try:
            df = pd.read_excel(file_path)
        except:
            return []
        df.columns = [c.strip().lower() for c in df.columns]
        df = df[[c for c in df.columns if any(k in c for k in ["phase", "protein", "energy", "lysine", "calcium", "phosphorus"])]]
        metadata = enrich_metadata(file_path, df.to_csv(index=False), chunk_type="table", domain="nutrition")
        yield {"text": df.to_csv(index=False), "metadata": metadata}
