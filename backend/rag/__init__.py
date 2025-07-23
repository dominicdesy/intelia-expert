"""RAG (Retrieval-Augmented Generation) system for broiler management expertise."""

import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Add rag directory to Python path for proper imports
RAG_DIR = Path(__file__).parent
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

# Version info
__version__ = "1.0.0"
__author__ = "Intelia Technologies"

# Module availability flags
EMBEDDER_AVAILABLE = False
RETRIEVER_AVAILABLE = False
PARSER_ROUTER_AVAILABLE = False

# Try to import core modules with proper error handling
try:
    from rag.embedder import RAGEmbedder
    EMBEDDER_AVAILABLE = True
    logger.debug("RAG embedder module loaded successfully")
except ImportError as e:
    logger.warning(f"RAG embedder not available: {e}")
    RAGEmbedder = None

try:
    from rag.retriever import RAGRetriever
    RETRIEVER_AVAILABLE = True
    logger.debug("RAG retriever module loaded successfully")
except ImportError as e:
    logger.warning(f"RAG retriever not available: {e}")
    RAGRetriever = None

try:
    from rag.parser_router import ParserRouter
    PARSER_ROUTER_AVAILABLE = True
    logger.debug("RAG parser router module loaded successfully")
except ImportError as e:
    logger.warning(f"RAG parser router not available: {e}")
    ParserRouter = None

# Export main classes if available
__all__ = []

if EMBEDDER_AVAILABLE:
    __all__.append('RAGEmbedder')

if RETRIEVER_AVAILABLE:
    __all__.append('RAGRetriever')

if PARSER_ROUTER_AVAILABLE:
    __all__.append('ParserRouter')

# System status check
def check_rag_system():
    """Check RAG system availability and return status."""
    status = {
        'embedder_available': EMBEDDER_AVAILABLE,
        'retriever_available': RETRIEVER_AVAILABLE,
        'parser_router_available': PARSER_ROUTER_AVAILABLE,
        'system_ready': EMBEDDER_AVAILABLE and RETRIEVER_AVAILABLE and PARSER_ROUTER_AVAILABLE
    }
    
    logger.info(f"RAG system status: {status}")
    return status

# Initialize logging for RAG system
def setup_rag_logging(level=logging.INFO):
    """Setup logging for RAG system."""
    rag_logger = logging.getLogger('rag')
    rag_logger.setLevel(level)
    
    if not rag_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d | %(levelname)s | %(name)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        rag_logger.addHandler(handler)
    
    return rag_logger

# Auto-setup logging
setup_rag_logging()
