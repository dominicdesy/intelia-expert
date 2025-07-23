"""Script to fix RAG structure and imports."""

import os
import shutil
from pathlib import Path

def fix_rag_structure():
    """Fix RAG directory structure and file names."""
    
    print("🔧 Fixing RAG structure...")
    
    # Get project root
    project_root = Path.cwd()
    rag_dir = project_root / "rag"
    parsers_dir = rag_dir / "parsers"
    
    print(f"Working in: {project_root}")
    print(f"RAG directory: {rag_dir}")
    print(f"Parsers directory: {parsers_dir}")
    
    # Step 1: Fix _init_.py → __init__.py in rag/
    rag_init_old = rag_dir / "_init_.py"
    rag_init_new = rag_dir / "__init__.py"
    
    if rag_init_old.exists():
        print(f"✅ Renaming {rag_init_old} → {rag_init_new}")
        shutil.move(str(rag_init_old), str(rag_init_new))
    else:
        print(f"⚠️ {rag_init_old} not found")
    
    # Step 2: Fix _init_.py → __init__.py in rag/parsers/
    parsers_init_old = parsers_dir / "_init_.py"
    parsers_init_new = parsers_dir / "__init__.py"
    
    if parsers_init_old.exists():
        print(f"✅ Renaming {parsers_init_old} → {parsers_init_new}")
        shutil.move(str(parsers_init_old), str(parsers_init_new))
    else:
        print(f"⚠️ {parsers_init_old} not found")
    
    # Step 3: Create proper __init__.py for rag/ if it doesn't exist
    if not rag_init_new.exists():
        print("📝 Creating rag/__init__.py")
        with open(rag_init_new, 'w', encoding='utf-8') as f:
            f.write(RAG_INIT_CONTENT)
    
    # Step 4: Create proper __init__.py for rag/parsers/ if it doesn't exist
    if not parsers_init_new.exists():
        print("📝 Creating rag/parsers/__init__.py")
        with open(parsers_init_new, 'w', encoding='utf-8') as f:
            f.write(PARSERS_INIT_CONTENT)
    
    # Step 5: List current files
    print("\n📂 Current RAG structure:")
    for file_path in sorted(rag_dir.rglob("*.py")):
        relative_path = file_path.relative_to(project_root)
        print(f"   {relative_path}")
    
    print("\n✅ RAG structure fix completed!")

# Content for rag/__init__.py
RAG_INIT_CONTENT = '''"""RAG (Retrieval-Augmented Generation) system for broiler management expertise."""

import logging

logger = logging.getLogger(__name__)

# Try to import main classes
try:
    from .embedder import RAGEmbedder, EnhancedDocumentEmbedder
    EMBEDDER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RAG embedder not available: {e}")
    RAGEmbedder = None
    EnhancedDocumentEmbedder = None
    EMBEDDER_AVAILABLE = False

try:
    from .retriever import RAGRetriever
    RETRIEVER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RAG retriever not available: {e}")
    RAGRetriever = None
    RETRIEVER_AVAILABLE = False

try:
    from .parser_router import ParserRouter
    PARSER_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Parser router not available: {e}")
    ParserRouter = None
    PARSER_ROUTER_AVAILABLE = False

# Export available classes
__all__ = []
if EMBEDDER_AVAILABLE:
    __all__.extend(['RAGEmbedder', 'EnhancedDocumentEmbedder'])
if RETRIEVER_AVAILABLE:
    __all__.append('RAGRetriever')
if PARSER_ROUTER_AVAILABLE:
    __all__.append('ParserRouter')

def get_rag_status():
    """Get RAG system status."""
    return {
        'embedder_available': EMBEDDER_AVAILABLE,
        'retriever_available': RETRIEVER_AVAILABLE,
        'parser_router_available': PARSER_ROUTER_AVAILABLE,
        'system_ready': all([EMBEDDER_AVAILABLE, RETRIEVER_AVAILABLE, PARSER_ROUTER_AVAILABLE])
    }
'''

# Content for rag/parsers/__init__.py
PARSERS_INIT_CONTENT = '''"""Document parsers for RAG system."""

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

# Try to import parsers
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

try:
    from .general_parsers import GeneralParser
    GENERAL_PARSER_AVAILABLE = True
    logger.debug("General parser loaded")
except ImportError as e:
    logger.warning(f"General parser not available: {e}")
    GeneralParser = None
    GENERAL_PARSER_AVAILABLE = False

try:
    from .ross308_parsers import Ross308Parser
    ROSS308_PARSER_AVAILABLE = True
    logger.debug("Ross308 parser loaded")
except ImportError as e:
    logger.warning(f"Ross308 parser not available: {e}")
    Ross308Parser = None
    ROSS308_PARSER_AVAILABLE = False

try:
    from .fallback_parsers import FallbackParser
    FALLBACK_PARSER_AVAILABLE = True
    logger.debug("Fallback parser loaded")
except ImportError as e:
    logger.warning(f"Fallback parser not available: {e}")
    FallbackParser = None
    FALLBACK_PARSER_AVAILABLE = False

# Export available parsers
__all__ = []

if BASE_CLASSES_AVAILABLE:
    __all__.extend(['BaseParser', 'ParserCapability', 'Document'])

if DOCUMENT_PARSER_AVAILABLE:
    __all__.extend(['PDFParser', 'TextParser', 'MarkdownParser', 'DocumentParser'])

if GENERAL_PARSER_AVAILABLE:
    __all__.append('GeneralParser')

if ROSS308_PARSER_AVAILABLE:
    __all__.append('Ross308Parser')

if FALLBACK_PARSER_AVAILABLE:
    __all__.append('FallbackParser')

def get_parsers_status():
    """Get parsers status."""
    return {
        'base_classes': BASE_CLASSES_AVAILABLE,
        'document_parser': DOCUMENT_PARSER_AVAILABLE,
        'general_parser': GENERAL_PARSER_AVAILABLE,
        'ross308_parser': ROSS308_PARSER_AVAILABLE,
        'fallback_parser': FALLBACK_PARSER_AVAILABLE,
        'any_available': any([
            DOCUMENT_PARSER_AVAILABLE,
            GENERAL_PARSER_AVAILABLE,
            ROSS308_PARSER_AVAILABLE,
            FALLBACK_PARSER_AVAILABLE
        ])
    }
'''

if __name__ == "__main__":
    fix_rag_structure()
