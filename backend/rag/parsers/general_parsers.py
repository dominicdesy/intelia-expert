# rag/parsers/general_parsers.py
import os
from langchain_community.document_loaders import TextLoader, UnstructuredPDFLoader, Docx2txtLoader
from rag.parsers.parser_base import ParserBase, ParsedChunk
from rag.metadata_enrichment import enrich_metadata

class GeneralTextParser(ParserBase):
    name = "general"

    def supports(self, file_path, mime, hints):
        ext = os.path.splitext(file_path)[1].lower()
        return ext in [".txt", ".pdf", ".docx"]

    def parse(self, file_path, mime):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".txt":
            loader = TextLoader(file_path)
        elif ext == ".pdf":
            loader = UnstructuredPDFLoader(file_path)
        elif ext == ".docx":
            loader = Docx2txtLoader(file_path)
        else:
            return []

        docs = loader.load()
        for d in docs:
            metadata = enrich_metadata(file_path, d.page_content, chunk_type="text")
            yield {"text": d.page_content, "metadata": metadata}
