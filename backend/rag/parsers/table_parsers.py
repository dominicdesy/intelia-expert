# rag/parsers/table_parsers.py
import os
import pandas as pd
from langchain_community.document_loaders import UnstructuredExcelLoader
from rag.parsers.parser_base import ParserBase
from rag.metadata_enrichment import enrich_metadata

class TableParser(ParserBase):
    name = "table"

    def supports(self, file_path, mime, hints):
        ext = os.path.splitext(file_path)[1].lower()
        return ext in [".xlsx", ".xls", ".csv"]

    def parse(self, file_path, mime):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".xlsx", ".xls"]:
            loader = UnstructuredExcelLoader(file_path)
            docs = loader.load()
            for d in docs:
                try:
                    df = pd.read_excel(file_path)
                except:
                    continue
                df.columns = [str(c).strip().lower() for c in df.columns]
                metadata = enrich_metadata(file_path, df.to_csv(index=False), chunk_type="table")
                yield {"text": df.to_csv(index=False), "metadata": metadata}

        elif ext == ".csv":
            df = pd.read_csv(file_path)
            df.columns = [str(c).strip().lower() for c in df.columns]
            metadata = enrich_metadata(file_path, df.to_csv(index=False), chunk_type="table")
            yield {"text": df.to_csv(index=False), "metadata": metadata}
