# rag/parser_router.py
import os
from typing import List, Dict, Any, Iterable
from rag.parsers.parser_base import ParsedChunk
from rag.parsers.general_parsers import GeneralTextParser
from rag.parsers.table_parsers import TableParser
from rag.parsers.performance_parser import PerformanceParser
from rag.parsers.nutrition_parser import NutritionParser
from rag.parsers.health_protocol_parser import HealthProtocolParser
from rag.parsers.environment_parser import EnvironmentParser
from rag.parsers.biosecurity_parser import BiosecurityParser

ALL_PARSERS = [
    TableParser(),
    PerformanceParser(),
    NutritionParser(),
    HealthProtocolParser(),
    EnvironmentParser(),
    BiosecurityParser(),
    GeneralTextParser(),  # always last as fallback
]

def route_and_parse(file_path: str, mime: str = "", hints: Dict[str, Any] = None) -> Iterable[ParsedChunk]:
    if hints is None:
        hints = {}

    ext = os.path.splitext(file_path)[1].lower()
    for parser in ALL_PARSERS:
        try:
            if parser.supports(file_path, mime, hints):
                for chunk in parser.parse(file_path, mime):
                    yield chunk
        except Exception as e:
            print(f"[parser_router] ❌ Error in parser {parser.name}: {e}")
