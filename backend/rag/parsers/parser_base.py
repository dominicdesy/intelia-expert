# rag/parsers/parser_base.py
from typing import Iterable, Dict, Any, TypedDict
from rag.metadata_schema import ChunkMeta

class ParsedChunk(TypedDict):
    text: str
    metadata: ChunkMeta

class ParserBase:
    name = "base"

    def supports(self, file_path: str, mime: str, hints: Dict[str, Any]) -> bool:
        """Retourne True si ce parser peut traiter ce fichier"""
        return False

    def parse(self, file_path: str, mime: str) -> Iterable[ParsedChunk]:
        """Analyse et renvoie une liste de chunks"""
        raise NotImplementedError
