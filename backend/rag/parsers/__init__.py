"""Document parsers for RAG system - Enhanced Version."""

import logging

logger = logging.getLogger(__name__)

# Import base classes first
try:
    from .parser_base import BaseParser, ParserCapability, Document
    BASE_CLASSES_AVAILABLE = True
    logger.debug("Base parser classes loaded")
except ImportError as e:
    logger.warning(f"Base parser classes not available: {e}")
    BASE_CLASSES_AVAILABLE = False

# Try to import metadata enrichment
try:
    from .metadata_enrichment import MetadataEnricher, extract_hierarchical_metadata, infer_tags_from_text
    METADATA_ENRICHMENT_AVAILABLE = True
    logger.debug("Metadata enrichment loaded")
except ImportError as e:
    logger.warning(f"Metadata enrichment not available: {e}")
    MetadataEnricher = None
    extract_hierarchical_metadata = None
    infer_tags_from_text = None
    METADATA_ENRICHMENT_AVAILABLE = False

# Try to import table parsers (NEW)
try:
    from .table_parsers import PerformanceTableParser
    TABLE_PARSER_AVAILABLE = True
    logger.debug("Table parsers loaded")
except ImportError as e:
    logger.warning(f"Table parser not available: {e}")
    PerformanceTableParser = None
    TABLE_PARSER_AVAILABLE = False

# Try to import document parsers
try:
    from .document_parsers import PDFParser, TextParser, MarkdownParser, DocumentParser
    DOCUMENT_PARSER_AVAILABLE = True
    logger.debug("Document parsers loaded")
except ImportError as e:
    logger.warning(f"Document parser not available: {e}")
    PDFParser = None
    TextParser = None
    MarkdownParser = None
    DocumentParser = None
    DOCUMENT_PARSER_AVAILABLE = False

# Try to import general parsers
try:
    from .general_parsers import GeneralCSVParser, GeneralExcelParser
    GENERAL_PARSER_AVAILABLE = True
    logger.debug("General parsers loaded")
except ImportError as e:
    logger.warning(f"General parsers not available: {e}")
    GeneralCSVParser = None
    GeneralExcelParser = None
    GENERAL_PARSER_AVAILABLE = False

# Try to import broiler parsers (ENHANCED)
try:
    from .broiler_parsers import BroilerPerformanceParser, BroilerTemperatureParser
    BROILER_PARSER_AVAILABLE = True
    logger.debug("Broiler parsers loaded")
except ImportError as e:
    logger.warning(f"Broiler parsers not available: {e}")
    BroilerPerformanceParser = None
    BroilerTemperatureParser = None
    BROILER_PARSER_AVAILABLE = False

# Try to import fallback parsers
try:
    from .fallback_parsers import TikaFallbackParser, RawTextFallbackParser, EmptyFileParser
    FALLBACK_PARSER_AVAILABLE = True
    logger.debug("Fallback parsers loaded")
except ImportError as e:
    logger.warning(f"Fallback parsers not available: {e}")
    TikaFallbackParser = None
    RawTextFallbackParser = None
    EmptyFileParser = None
    FALLBACK_PARSER_AVAILABLE = False

# Export available classes
__all__ = []

if BASE_CLASSES_AVAILABLE:
    __all__.extend(['BaseParser', 'ParserCapability', 'Document'])

if METADATA_ENRICHMENT_AVAILABLE:
    __all__.extend(['MetadataEnricher', 'extract_hierarchical_metadata', 'infer_tags_from_text'])

if TABLE_PARSER_AVAILABLE:
    __all__.append('PerformanceTableParser')

if DOCUMENT_PARSER_AVAILABLE:
    __all__.extend(['PDFParser', 'TextParser', 'MarkdownParser', 'DocumentParser'])

if GENERAL_PARSER_AVAILABLE:
    __all__.extend(['GeneralCSVParser', 'GeneralExcelParser'])

if BROILER_PARSER_AVAILABLE:
    __all__.extend(['BroilerPerformanceParser', 'BroilerTemperatureParser'])

if FALLBACK_PARSER_AVAILABLE:
    __all__.extend(['TikaFallbackParser', 'RawTextFallbackParser', 'EmptyFileParser'])


def get_all_available_parsers():
    """
    Get list of all available parser instances, ordered by priority.
    
    Returns:
        List of parser instances, ordered from highest to lowest priority
    """
    parsers = []
    
    # High priority: Specialized parsers (90-100)
    if TABLE_PARSER_AVAILABLE and PerformanceTableParser:
        parsers.append(PerformanceTableParser())
    
    if BROILER_PARSER_AVAILABLE:
        if BroilerPerformanceParser:
            parsers.append(BroilerPerformanceParser())
        if BroilerTemperatureParser:
            parsers.append(BroilerTemperatureParser())
    
    # Medium-high priority: General purpose parsers (40-60)
    if GENERAL_PARSER_AVAILABLE:
        if GeneralCSVParser:
            parsers.append(GeneralCSVParser())
        if GeneralExcelParser:
            parsers.append(GeneralExcelParser())
    
    # Medium priority: Document parsers (35-45)
    if DOCUMENT_PARSER_AVAILABLE:
        if MarkdownParser:
            parsers.append(MarkdownParser())
        if PDFParser:
            parsers.append(PDFParser())
        if TextParser:
            parsers.append(TextParser())
    
    # Low priority: Fallback parsers (1-10)
    if FALLBACK_PARSER_AVAILABLE:
        if TikaFallbackParser:
            parsers.append(TikaFallbackParser())
        if RawTextFallbackParser:
            parsers.append(RawTextFallbackParser())
        if EmptyFileParser:
            parsers.append(EmptyFileParser())
    
    # Sort by priority (highest first)
    parsers.sort(key=lambda p: p.capability.priority, reverse=True)
    
    logger.info(f"Loaded {len(parsers)} parsers")
    return parsers


def get_parsers_by_extension(file_extension: str):
    """
    Get parsers that support a specific file extension.
    
    Args:
        file_extension: File extension (e.g., '.pdf', '.xlsx')
        
    Returns:
        List of parser instances that support the extension
    """
    all_parsers = get_all_available_parsers()
    matching_parsers = [
        parser for parser in all_parsers 
        if file_extension.lower() in [ext.lower() for ext in parser.get_supported_extensions()]
        or '*' in parser.get_supported_extensions()  # Universal parsers
    ]
    
    return matching_parsers


def get_parsers_status():
    """Get detailed parsers status."""
    status = {
        'base_classes': BASE_CLASSES_AVAILABLE,
        'metadata_enrichment': METADATA_ENRICHMENT_AVAILABLE,
        'table_parser': TABLE_PARSER_AVAILABLE,
        'document_parser': DOCUMENT_PARSER_AVAILABLE,
        'general_parser': GENERAL_PARSER_AVAILABLE,
        'broiler_parser': BROILER_PARSER_AVAILABLE,
        'fallback_parser': FALLBACK_PARSER_AVAILABLE,
        'any_available': any([
            TABLE_PARSER_AVAILABLE,
            DOCUMENT_PARSER_AVAILABLE,
            GENERAL_PARSER_AVAILABLE,
            BROILER_PARSER_AVAILABLE,
            FALLBACK_PARSER_AVAILABLE
        ])
    }
    
    # Add parser counts
    if status['any_available']:
        all_parsers = get_all_available_parsers()
        status['total_parsers'] = len(all_parsers)
        status['parser_priorities'] = [p.capability.priority for p in all_parsers]
        status['supported_extensions'] = list(set(
            ext for parser in all_parsers 
            for ext in parser.get_supported_extensions()
            if ext != '*'
        ))
    else:
        status['total_parsers'] = 0
        status['parser_priorities'] = []
        status['supported_extensions'] = []
    
    return status


def create_parser_router():
    """
    Create a parser router with all available parsers.
    
    Returns:
        ParserRouter instance or None if not available
    """
    try:
        # Try to import parser router
        from ..parser_router import ParserRouter
        
        # Get all available parsers
        parsers = get_all_available_parsers()
        
        if not parsers:
            logger.warning("No parsers available for router")
            return None
        
        # Create router with parsers
        router = ParserRouter(parsers)
        logger.info(f"Created parser router with {len(parsers)} parsers")
        return router
        
    except ImportError as e:
        logger.warning(f"ParserRouter not available: {e}")
        return None


# Legacy compatibility - maintain existing interface
ALL_PARSERS = get_all_available_parsers()

# Add legacy names for backward compatibility
try:
    # Map old names to new ones if needed
    if DOCUMENT_PARSER_AVAILABLE and DocumentParser:
        GenericPDFParser = DocumentParser  # Alias
    if GENERAL_PARSER_AVAILABLE and GeneralCSVParser:
        GeneralParser = GeneralCSVParser  # Alias
    if FALLBACK_PARSER_AVAILABLE and TikaFallbackParser:
        FallbackParser = TikaFallbackParser  # Alias
        
except Exception as e:
    logger.debug(f"Legacy compatibility mapping failed: {e}")


# Add to exports for legacy support
if 'GenericPDFParser' in locals():
    __all__.append('GenericPDFParser')
if 'GeneralParser' in locals():
    __all__.append('GeneralParser')
if 'FallbackParser' in locals():
    __all__.append('FallbackParser')

__all__.extend(['get_all_available_parsers', 'get_parsers_by_extension', 'get_parsers_status', 'create_parser_router', 'ALL_PARSERS'])