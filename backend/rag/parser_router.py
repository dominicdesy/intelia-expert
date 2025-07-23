#!/usr/bin/env python3
"""
Enhanced Parser Router with Intelligent Routing
Clean code compliant version with correct imports
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import time

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
    logger.debug("Document parsers imported successfully")
except ImportError as e:
    logger.warning(f"Document parsers not available: {e}")

# Import general parsers
try:
    from rag.parsers.general_parsers import GeneralCSVParser, GeneralExcelParser
    AVAILABLE_PARSERS.extend([GeneralCSVParser, GeneralExcelParser])
    logger.debug("General parsers imported successfully")
except ImportError as e:
    logger.warning(f"General parsers not available: {e}")

# Import broiler parsers (corrected import)
try:
    from rag.parsers.broiler_parsers import BroilerPerformanceParser, BroilerTemperatureParser
    AVAILABLE_PARSERS.extend([BroilerPerformanceParser, BroilerTemperatureParser])
    logger.debug("Broiler parsers imported successfully")
except ImportError as e:
    logger.warning(f"Broiler parsers not available: {e}")

# Import fallback parsers
try:
    from rag.parsers.fallback_parsers import TikaFallbackParser, RawTextFallbackParser, EmptyFileParser
    AVAILABLE_PARSERS.extend([TikaFallbackParser, RawTextFallbackParser, EmptyFileParser])
    logger.debug("Fallback parsers imported successfully")
except ImportError as e:
    logger.warning(f"Fallback parsers not available: {e}")


@dataclass
class ParsingResult:
    """Enhanced parsing result with performance metrics."""
    documents: List[Dict[str, Any]] = field(default_factory=list)
    parser_used: str = ""
    parsing_time: float = 0.0
    chunk_count: int = 0
    success: bool = False
    error_message: Optional[str] = None
    chunking_strategy: Optional[str] = None


@dataclass
class ParserPerformance:
    """Parser performance tracking."""
    parser_name: str
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_time: float = 0.0
    average_time: float = 0.0
    error_rate: float = 0.0


class ParserRouter:
    """Enhanced parser router with intelligent routing and performance tracking."""
    
    def __init__(self, enable_performance_tracking: bool = True):
        """Initialize parser router."""
        self.enable_performance_tracking = enable_performance_tracking
        self.parsers = self._initialize_parsers()
        self.fallback_parsers = self._get_fallback_parsers()
        
        # Performance tracking
        self.parser_performance = {}
        if self.enable_performance_tracking:
            for parser in self.parsers + self.fallback_parsers:
                parser_name = parser.__class__.__name__
                self.parser_performance[parser_name] = ParserPerformance(parser_name)
        
        # Routing statistics
        self.routing_stats = {
            'total_files': 0,
            'successful_parsings': 0,
            'failed_parsings': 0,
            'total_time': 0.0
        }
        
        logger.info(f"Parser router initialized with {len(self.parsers)} parsers")
        if self.fallback_parsers:
            logger.info(f"{len(self.fallback_parsers)} fallback parsers available")
    
    def _initialize_parsers(self) -> List[Any]:
        """Initialize available parsers sorted by priority."""
        if not AVAILABLE_PARSERS:
            logger.warning("No parsers available")
            return []
        
        # Create instances of available parsers
        parser_instances = []
        for parser_class in AVAILABLE_PARSERS:
            try:
                parser_instance = parser_class()
                parser_instances.append(parser_instance)
                logger.debug(f"Initialized parser: {parser_class.__name__}")
            except Exception as e:
                logger.warning(f"Failed to initialize parser {parser_class.__name__}: {e}")
        
        # Sort by priority if capability property exists
        try:
            parser_instances.sort(key=lambda p: getattr(p.capability, 'priority', 50), reverse=True)
        except:
            logger.debug("Parsers sorted without priority")
        
        return parser_instances
    
    def _get_fallback_parsers(self) -> List[Any]:
        """Get fallback parsers for when primary parsers fail."""
        fallback_parsers = []
        
        # Look for fallback parsers in the available parsers
        for parser in self.parsers:
            parser_name = parser.__class__.__name__
            if 'fallback' in parser_name.lower() or 'raw' in parser_name.lower() or 'empty' in parser_name.lower():
                fallback_parsers.append(parser)
        
        return fallback_parsers
    
    def detect_file_type(self, file_path: str) -> Tuple[Any, float]:
        """
        Detect the best parser for a file.
        
        Returns:
            Tuple of (parser_instance, confidence_score)
        """
        file_path = str(file_path)
        best_parser = None
        best_score = 0.0
        
        # Try to read content sample for better detection
        content_sample = None
        try:
            path_obj = Path(file_path)
            if path_obj.exists() and path_obj.is_file():
                if path_obj.suffix.lower() in ['.txt', '.md']:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content_sample = f.read(1000)
                elif path_obj.suffix.lower() in ['.csv']:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content_sample = f.read(500)
        except Exception as e:
            logger.debug(f"Could not read content sample from {file_path}: {e}")
        
        # Test each parser
        for parser in self.parsers:
            try:
                if hasattr(parser, 'can_parse'):
                    score = parser.can_parse(file_path, content_sample)
                    if score > best_score:
                        best_score = score
                        best_parser = parser
                        logger.debug(f"Parser {parser.__class__.__name__} scored {score:.2f} for {Path(file_path).name}")
            except Exception as e:
                logger.debug(f"Parser {parser.__class__.__name__} failed detection for {file_path}: {e}")
        
        # If no parser found, try fallback parsers
        if best_parser is None and self.fallback_parsers:
            for parser in self.fallback_parsers:
                try:
                    if hasattr(parser, 'can_parse'):
                        score = parser.can_parse(file_path, content_sample)
                        if score > best_score:
                            best_score = score
                            best_parser = parser
                except Exception as e:
                    logger.debug(f"Fallback parser {parser.__class__.__name__} failed: {e}")
        
        return best_parser, best_score
    
    def parse_file(self, file_path: str) -> ParsingResult:
        """
        Parse a file using the most appropriate parser.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            ParsingResult with documents and metadata
        """
        start_time = time.time()
        file_path = str(file_path)
        
        # Update statistics
        self.routing_stats['total_files'] += 1
        
        try:
            # Detect best parser
            parser, confidence = self.detect_file_type(file_path)
            
            if parser is None:
                raise ValueError(f"No suitable parser found for {file_path}")
            
            parser_name = parser.__class__.__name__
            logger.debug(f"Selected parser {parser_name} for {Path(file_path).name} (confidence: {confidence:.2f})")
            
            # Parse the file
            documents = parser.parse(file_path)
            parsing_time = time.time() - start_time
            
            # Update statistics
            self.routing_stats['successful_parsings'] += 1
            self.routing_stats['total_time'] += parsing_time
            
            # Update parser performance
            if self.enable_performance_tracking and parser_name in self.parser_performance:
                perf = self.parser_performance[parser_name]
                perf.total_files += 1
                perf.successful_files += 1
                perf.total_time += parsing_time
                perf.average_time = perf.total_time / perf.total_files
                perf.error_rate = perf.failed_files / perf.total_files
            
            # Determine chunking strategy
            chunking_strategy = self._determine_chunking_strategy(file_path, documents)
            
            # Create result
            result = ParsingResult(
                documents=documents,
                parser_used=parser_name,
                parsing_time=parsing_time,
                chunk_count=len(documents),
                success=True,
                chunking_strategy=chunking_strategy
            )
            
            logger.info(f"Successfully parsed {Path(file_path).name}: {len(documents)} chunks in {parsing_time:.2f}s")
            return result
            
        except Exception as e:
            parsing_time = time.time() - start_time
            error_message = f"Parsing failed for {Path(file_path).name}: {str(e)}"
            
            # Update statistics
            self.routing_stats['failed_parsings'] += 1
            self.routing_stats['total_time'] += parsing_time
            
            # Update parser performance
            if self.enable_performance_tracking and 'parser_name' in locals():
                if parser_name in self.parser_performance:
                    perf = self.parser_performance[parser_name]
                    perf.total_files += 1
                    perf.failed_files += 1
                    perf.total_time += parsing_time
                    perf.average_time = perf.total_time / perf.total_files
                    perf.error_rate = perf.failed_files / perf.total_files
            
            logger.error(error_message)
            
            return ParsingResult(
                documents=[],
                parser_used=parser_name if 'parser_name' in locals() else "unknown",
                parsing_time=parsing_time,
                chunk_count=0,
                success=False,
                error_message=error_message
            )
    
    def _determine_chunking_strategy(self, file_path: str, documents: List[Dict[str, Any]]) -> str:
        """Determine the best chunking strategy based on document content."""
        file_name = Path(file_path).name.lower()
        
        # Analyze content for chunking strategy
        if 'performance' in file_name or 'ross' in file_name or 'cobb' in file_name:
            return "performance_data"
        elif 'temperature' in file_name or 'environment' in file_name:
            return "environmental_data"
        elif 'nutrition' in file_name or 'feed' in file_name:
            return "nutrition_data"
        elif file_name.endswith('.pdf') or 'manual' in file_name or 'guide' in file_name:
            return "technical_manual"
        else:
            return "standard_text"
    
    def get_parser_status(self) -> Dict[str, Any]:
        """Get status of all available parsers."""
        available_parsers = [p.__class__.__name__ for p in self.parsers]
        fallback_parsers = [p.__class__.__name__ for p in self.fallback_parsers]
        
        return {
            'total_parsers': len(self.parsers),
            'available_parsers': available_parsers,
            'fallback_parsers': fallback_parsers,
            'performance_tracking_enabled': self.enable_performance_tracking
        }
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing performance statistics."""
        total_files = self.routing_stats['total_files']
        successful = self.routing_stats['successful_parsings']
        
        return {
            'total_files': total_files,
            'successful_parsings': successful,
            'failed_parsings': self.routing_stats['failed_parsings'],
            'success_rate': (successful / total_files * 100) if total_files > 0 else 0,
            'average_time': self.routing_stats['total_time'] / total_files if total_files > 0 else 0
        }
    
    def get_parser_performance(self) -> Dict[str, ParserPerformance]:
        """Get performance statistics for each parser."""
        return self.parser_performance.copy()
    
    def reset_statistics(self):
        """Reset all performance statistics."""
        self.routing_stats = {
            'total_files': 0,
            'successful_parsings': 0,
            'failed_parsings': 0,
            'total_time': 0.0
        }
        
        for parser_name in self.parser_performance:
            self.parser_performance[parser_name] = ParserPerformance(parser_name)
        
        logger.info("Parser statistics reset")


# Legacy compatibility
class EnhancedParserRouter(ParserRouter):
    """Enhanced parser router - alias for backward compatibility."""
    pass