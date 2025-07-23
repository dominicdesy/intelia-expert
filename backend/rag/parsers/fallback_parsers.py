"""
Fallback Parser Plugins - CORRECTED VERSION
Universal parsers for unsupported formats and emergency fallbacks

CORRECTION: Parsers now return dictionary format instead of Document objects
to match the expected format by the router and embedder system.
"""

from typing import List, Optional, Dict, Any
import logging
import os

from .parser_base import BaseParser, ParserCapability

logger = logging.getLogger(__name__)


class TikaFallbackParser(BaseParser):
    """
    Universal fallback parser using Apache Tika
    
    This parser can handle 1000+ file formats using Apache Tika's
    content extraction capabilities. It serves as the ultimate fallback
    when no specialized parser is available.
    """
    
    def __init__(self):
        self.tika_available = self._check_tika_availability()
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="TikaFallbackParser",
            supported_extensions=['*'],  # Universal - all formats
            breed_types=['Any'],
            data_types=['universal', 'unknown_format'],
            quality_score='good',
            description='Universal fallback parser using Apache Tika (1000+ formats)',
            priority=10  # Lowest priority - used only as fallback
        )
    
    def _check_tika_availability(self) -> bool:
        """Check if Apache Tika is available for use"""
        try:
            import tika
            from tika import parser
            logger.info("✅ Apache Tika available for universal parsing")
            return True
        except ImportError:
            logger.info("ℹ️ Apache Tika not available (pip install tika for universal parsing)")
            return False
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """
        Evaluate capability to parse any file format
        
        Tika can parse almost anything, but has low priority to allow
        specialized parsers to handle files first.
        """
        if not self.tika_available:
            return 0.0
        
        # Low base score to ensure specialized parsers are preferred
        base_score = 0.3
        
        # Slightly higher score for unknown file types
        file_ext = file_path.lower().split('.')[-1]
        unknown_extensions = ['docx', 'doc', 'pptx', 'ppt', 'rtf', 'odt', 'pages']
        if file_ext in unknown_extensions:
            base_score = 0.4
        
        return base_score
    
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse file using Apache Tika universal extraction - CORRECTED TO RETURN DICT"""
        if not self.tika_available:
            logger.error("Apache Tika not available for parsing")
            return []
        
        try:
            from tika import parser
            
            # Extract content using Tika
            parsed_content = parser.from_file(file_path)
            content = parsed_content.get("content", "")
            tika_metadata = parsed_content.get("metadata", {})
            
            if not content or not content.strip():
                logger.warning(f"No content extracted from {file_path} using Tika")
                return []
            
            # Create dictionary document with Tika metadata - CORRECTED FORMAT
            doc_dict = {
                'content': content.strip(),  # ✅ CORRECTED: Use 'content' key
                'source': file_path,
                'metadata': {
                    **self.create_base_metadata(file_path, {
                        'document_type': 'tika_universal',
                        'extraction_method': 'apache_tika',
                        'tika_content_type': tika_metadata.get('Content-Type', 'unknown'),
                        'tika_author': tika_metadata.get('Author', ''),
                        'tika_title': tika_metadata.get('title', ''),
                        'content_length': len(content)
                    }),
                    **{k: str(v) for k, v in tika_metadata.items() if isinstance(v, (str, int, float))}
                }
            }
            
            logger.info(f"✅ Extracted content using Tika: {len(content)} characters")
            return [doc_dict]  # ✅ CORRECTED: Return list of dictionaries
            
        except Exception as e:
            logger.error(f"Tika parsing failed for {file_path}: {e}")
            return []


class RawTextFallbackParser(BaseParser):
    """
    Raw text extraction fallback parser - CORRECTED VERSION
    
    Last resort parser that attempts to extract readable text
    from any file by reading it as binary and converting to text.
    
    CORRECTION: Now returns dictionary format instead of Document objects.
    """
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="RawTextFallbackParser",
            supported_extensions=['*'],  # Universal
            breed_types=['Any'],
            data_types=['raw_text', 'emergency_fallback'],
            quality_score='basic',
            description='Emergency fallback parser with raw text extraction',
            priority=5  # Lowest possible priority
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """
        Can attempt to parse any file, but with very low confidence
        
        Only used when no other parser is available.
        """
        # Very low score - only used as absolute last resort
        return 0.1 if os.path.exists(file_path) else 0.0
    
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Attempt raw text extraction from any file - CORRECTED TO RETURN DICT"""
        try:
            content = self._extract_raw_text(file_path)
            
            if not content or len(content.strip()) < 10:
                logger.warning(f"Insufficient readable content extracted from {file_path}")
                return []
            
            # Create dictionary document - CORRECTED FORMAT
            doc_dict = {
                'content': content,  # ✅ CORRECTED: Use 'content' key instead of 'page_content'
                'source': file_path,
                'metadata': {
                    **self.create_base_metadata(file_path, {
                        'document_type': 'raw_text_extraction',
                        'extraction_method': 'raw_binary_read',
                        'content_length': len(content),
                        'warning': 'Content extracted using raw text fallback - quality may be low'
                    })
                }
            }
            
            logger.info(f"✅ Raw text extraction: {len(content)} characters")
            return [doc_dict]  # ✅ CORRECTED: Return list of dictionaries
            
        except Exception as e:
            logger.error(f"Raw text extraction failed for {file_path}: {e}")
            return []
    
    def _extract_raw_text(self, file_path: str, max_bytes: int = 100000) -> str:
        """
        Extract readable text from binary file content
        
        Attempts multiple encoding strategies to extract meaningful text.
        """
        # First try: UTF-8 text read
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_bytes)
                if self._is_readable_text(content):
                    return content
        except Exception:
            pass
        
        # Second try: Binary read with UTF-8 decode
        try:
            with open(file_path, 'rb') as f:
                raw_content = f.read(max_bytes)
                content = raw_content.decode('utf-8', errors='ignore')
                if self._is_readable_text(content):
                    return content
        except Exception:
            pass
        
        # Third try: Binary read with latin-1 decode
        try:
            with open(file_path, 'rb') as f:
                raw_content = f.read(max_bytes)
                content = raw_content.decode('latin-1', errors='ignore')
                if self._is_readable_text(content):
                    return content
        except Exception:
            pass
        
        # Fourth try: Extract printable ASCII characters
        try:
            with open(file_path, 'rb') as f:
                raw_content = f.read(max_bytes)
                # Extract only printable ASCII characters
                content = ''.join(chr(byte) for byte in raw_content 
                                if 32 <= byte <= 126 or byte in [9, 10, 13])
                if self._is_readable_text(content):
                    return content
        except Exception:
            pass
        
        return ""
    
    def _is_readable_text(self, content: str, min_ratio: float = 0.7) -> bool:
        """
        Check if extracted content appears to be readable text
        
        Uses heuristics to determine if content is meaningful text
        rather than binary garbage.
        """
        if len(content) < 10:
            return False
        
        # Count printable characters
        printable_chars = sum(1 for char in content if char.isprintable() or char.isspace())
        printable_ratio = printable_chars / len(content)
        
        if printable_ratio < min_ratio:
            return False
        
        # Check for reasonable word-like patterns
        words = content.split()
        if len(words) < 3:
            return False
        
        # Check average word length (reasonable range)
        avg_word_length = sum(len(word) for word in words) / len(words)
        if avg_word_length < 2 or avg_word_length > 20:
            return False
        
        return True


class EmptyFileParser(BaseParser):
    """
    Parser for handling empty or minimal content files - CORRECTED VERSION
    
    Creates a placeholder document for files that exist but
    contain no meaningful content.
    
    CORRECTION: Now returns dictionary format instead of Document objects.
    """
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="EmptyFileParser",
            supported_extensions=['*'],
            breed_types=['Any'],
            data_types=['empty_file', 'placeholder'],
            quality_score='basic',
            description='Handles empty files and creates placeholder documents',
            priority=1  # Very low priority
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """Detect empty or near-empty files"""
        try:
            file_size = os.path.getsize(file_path)
            
            # Files smaller than 10 bytes are likely empty
            if file_size < 10:
                return 0.8
            
            # Files smaller than 100 bytes with no meaningful content
            if file_size < 100 and content_sample:
                if not content_sample.strip():
                    return 0.8
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Create placeholder document for empty file - CORRECTED TO RETURN DICT"""
        try:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            content = f"""Empty File Placeholder: {file_name}

This file appears to be empty or contains no readable content.

File Information:
- File name: {file_name}
- File size: {file_size} bytes
- File type: {os.path.splitext(file_name)[1] or 'unknown'}

This placeholder document was created to maintain file tracking
in the document processing system."""
            
            # Create dictionary document - CORRECTED FORMAT
            doc_dict = {
                'content': content,  # ✅ CORRECTED: Use 'content' key
                'source': file_path,
                'metadata': {
                    **self.create_base_metadata(file_path, {
                        'document_type': 'empty_file_placeholder',
                        'file_size_bytes': file_size,
                        'is_placeholder': True,
                        'warning': 'This is a placeholder for an empty or unreadable file'
                    })
                }
            }
            
            logger.info(f"Created placeholder for empty file: {file_name}")
            return [doc_dict]  # ✅ CORRECTED: Return list of dictionaries
            
        except Exception as e:
            logger.error(f"Error creating empty file placeholder for {file_path}: {e}")
            return []


# ✅ ADDITIONAL COMPATIBILITY METHOD
def convert_document_to_dict(doc) -> Dict[str, Any]:
    """
    Utility function to convert Document objects to dictionary format
    
    This ensures compatibility between different parser return formats.
    """
    if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
        # Document object format
        return {
            'content': doc.page_content,
            'metadata': doc.metadata if isinstance(doc.metadata, dict) else {},
            'source': doc.metadata.get('source_file', '') if hasattr(doc, 'metadata') else ''
        }
    elif isinstance(doc, dict):
        # Already in dictionary format - ensure it has 'content' key
        content = doc.get('content') or doc.get('page_content') or str(doc)
        return {
            'content': content,
            'metadata': doc.get('metadata', {}),
            'source': doc.get('source', doc.get('source_file', ''))
        }
    else:
        # Unknown format - convert to string
        return {
            'content': str(doc),
            'metadata': {},
            'source': ''
        }
