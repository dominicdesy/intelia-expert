#!/usr/bin/env python3
"""
Enhanced Parser Router with Intelligent Routing
+ Table-first propagation: force metadata['chunk_type']="table" if parser is a table parser
  or content is detected as table.
"""

import os
import sys
import re
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Add project root to path for proper imports
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Initialize parser lists
AVAILABLE_PARSERS = []

# Import document parsers
try:
    from rag.parsers.document_parsers import PDFParser, TextParser, MarkdownParser
    AVAILABLE_PARSERS.extend([PDFParser, TextParser, MarkdownParser])
except ImportError as e:
    logger.warning(f"Document parsers not available: {e}")

# Import general parsers
try:
    from rag.parsers.general_parsers import GeneralCSVParser, GeneralExcelParser
    AVAILABLE_PARSERS.extend([GeneralCSVParser, GeneralExcelParser])
except ImportError as e:
    logger.warning(f"General parsers not available: {e}")

# Import broiler parsers
try:
    from rag.parsers.broiler_parsers import BroilerPerformanceParser, BroilerTemperatureParser
    AVAILABLE_PARSERS.extend([BroilerPerformanceParser, BroilerTemperatureParser])
except ImportError as e:
    logger.warning(f"Broiler parsers not available: {e}")

# Import table parsers (ajout explicite si dispo)
try:
    from rag.parsers.table_parsers import PerformanceTableParser
    AVAILABLE_PARSERS.append(PerformanceTableParser)
except ImportError as e:
    logger.warning(f"Table parsers not available: {e}")

# Import fallback parsers
try:
    from rag.parsers.fallback_parsers import TikaFallbackParser, RawTextFallbackParser, EmptyFileParser
    AVAILABLE_PARSERS.extend([TikaFallbackParser, RawTextFallbackParser, EmptyFileParser])
except ImportError as e:
    logger.warning(f"Fallback parsers not available: {e}")


@dataclass
class ParsingResult:
    documents: List[Dict[str, Any]] = field(default_factory=list)
    parser_used: str = ""
    parsing_time: float = 0.0
    chunk_count: int = 0
    success: bool = False
    error_message: Optional[str] = None
    chunking_strategy: Optional[str] = None


@dataclass
class ParserPerformance:
    parser_name: str
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_time: float = 0.0
    average_time: float = 0.0
    error_rate: float = 0.0


def _detect_table_structure(text: str) -> bool:
    """Détection rapide table (markdown/HTML/CSV/whitespace)"""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    pipe_lines = [ln for ln in lines if '|' in ln]
    if len(pipe_lines) >= 2 and any(re.match(r'^\s*\|?[\s:\-\|\+]+\|?\s*$', ln) for ln in pipe_lines):
        return True
    if re.search(r'<\s*table\b', text, flags=re.I):
        return True
    for delim in [',', ';', '\t']:
        delim_lines = [ln for ln in lines if ln.count(delim) >= 2]
        if len(delim_lines) >= max(2, int(0.3 * len(lines))):
            counts = [ln.count(delim) for ln in delim_lines[:10]]
            if counts and max(counts) - min(counts) <= 2:
                return True
    ws_lines = sum(1 for ln in lines if re.search(r'\S+\s{2,}\S+\s{2,}\S+', ln))
    if ws_lines >= max(2, int(0.3 * len(lines))):
        return True
    return False


class ParserRouter:
    """Enhanced parser router with table-first propagation"""

    def __init__(self, enable_performance_tracking: bool = True):
        self.enable_performance_tracking = enable_performance_tracking
        self.parsers = self._initialize_parsers()
        self.fallback_parsers = self._get_fallback_parsers()

        self.parser_performance: Dict[str, ParserPerformance] = {}
        if self.enable_performance_tracking:
            for parser in self.parsers + self.fallback_parsers:
                self.parser_performance[parser.__class__.__name__] = ParserPerformance(parser.__class__.__name__)

        self.routing_stats = {
            'total_files': 0,
            'successful_parsings': 0,
            'failed_parsings': 0,
            'total_time': 0.0
        }

    def _initialize_parsers(self) -> List[Any]:
        instances = []
        for parser_cls in AVAILABLE_PARSERS:
            try:
                p = parser_cls()
                instances.append(p)
            except Exception as e:
                logger.warning(f"Failed to init parser {parser_cls.__name__}: {e}")
        try:
            instances.sort(key=lambda p: getattr(p.capability, 'priority', 50), reverse=True)
        except Exception:
            pass
        return instances

    def _get_fallback_parsers(self) -> List[Any]:
        return [p for p in self.parsers if any(k in p.__class__.__name__.lower() for k in ['fallback', 'raw', 'empty'])]

    def detect_file_type(self, file_path: str) -> Tuple[Any, float]:
        content_sample = None
        try:
            ext = Path(file_path).suffix.lower()
            if ext in ['.txt', '.md', '.csv']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content_sample = f.read(1000)
        except Exception:
            pass
        best_parser, best_score = None, 0.0
        for parser in self.parsers:
            try:
                score = parser.can_parse(file_path, content_sample)
                if score > best_score:
                    best_score, best_parser = score, parser
            except Exception:
                continue
        return best_parser, best_score

    def parse_file(self, file_path: str) -> ParsingResult:
        start = time.time()
        self.routing_stats['total_files'] += 1
        parser_name = None
        try:
            parser, conf = self.detect_file_type(file_path)
            if not parser:
                raise ValueError("No parser found")
            parser_name = parser.__class__.__name__
            documents = parser.parse(file_path)

            # ✅ Table-first propagation :
            if 'table' in parser_name.lower():
                for d in documents:
                    d.metadata['chunk_type'] = 'table'
            else:
                # check by content
                for d in documents:
                    if _detect_table_structure(d.page_content):
                        d.metadata['chunk_type'] = 'table'

            elapsed = time.time() - start
            self.routing_stats['successful_parsings'] += 1
            self.routing_stats['total_time'] += elapsed
            if self.enable_performance_tracking:
                perf = self.parser_performance.get(parser_name)
                if perf:
                    perf.total_files += 1
                    perf.successful_files += 1
                    perf.total_time += elapsed
                    perf.average_time = perf.total_time / perf.total_files
                    perf.error_rate = perf.failed_files / perf.total_files

            return ParsingResult(
                documents=documents,
                parser_used=parser_name,
                parsing_time=elapsed,
                chunk_count=len(documents),
                success=True,
                chunking_strategy=self._determine_chunking_strategy(file_path, documents)
            )

        except Exception as e:
            elapsed = time.time() - start
            self.routing_stats['failed_parsings'] += 1
            self.routing_stats['total_time'] += elapsed
            if self.enable_performance_tracking and parser_name:
                perf = self.parser_performance.get(parser_name)
                if perf:
                    perf.total_files += 1
                    perf.failed_files += 1
                    perf.total_time += elapsed
                    perf.average_time = perf.total_time / perf.total_files
                    perf.error_rate = perf.failed_files / perf.total_files
            return ParsingResult(
                documents=[],
                parser_used=parser_name or "unknown",
                parsing_time=elapsed,
                chunk_count=0,
                success=False,
                error_message=str(e)
            )

    def _determine_chunking_strategy(self, file_path: str, docs: List[Dict[str, Any]]) -> str:
        name = Path(file_path).name.lower()
        if 'performance' in name or 'ross' in name or 'cobb' in name:
            return "performance_data"
        if 'temperature' in name or 'environment' in name:
            return "environmental_data"
        if 'nutrition' in name or 'feed' in name:
            return "nutrition_data"
        if name.endswith('.pdf') or 'manual' in name or 'guide' in name:
            return "technical_manual"
        return "standard_text"


class EnhancedParserRouter(ParserRouter):
    pass
