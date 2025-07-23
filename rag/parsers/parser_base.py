"""Base classes for document parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParserCapability:
    """Parser capability definition."""
    name: str
    supported_extensions: List[str]
    breed_types: List[str]
    data_types: List[str]
    quality_score: str
    description: str
    priority: int


@dataclass
class Document:
    """Document representation with metadata."""
    page_content: str
    metadata: Dict[str, Any]
    
    def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
        self.page_content = page_content
        self.metadata = metadata or {}


class BaseParser(ABC):
    """Base parser interface for all document parsers."""
    
    @property
    @abstractmethod
    def capability(self) -> ParserCapability:
        """Get parser capability information."""
        pass
    
    @abstractmethod
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """
        Check if parser can handle the given file.
        
        Args:
            file_path: Path to the file
            content_sample: Optional content sample for content-based detection
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass
    
    @abstractmethod
    def parse(self, file_path: str) -> List[Document]:
        """
        Parse file into list of documents.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            List of Document objects
        """
        pass
    
    def create_base_metadata(self, file_path: str, additional_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create base metadata for document.
        
        Args:
            file_path: Path to the source file
            additional_metadata: Additional metadata to include
            
        Returns:
            Dictionary containing metadata
        """
        path = Path(file_path)
        base_metadata = {
            'source_file': str(path),
            'file_name': path.name,
            'file_extension': path.suffix,
            'file_size': path.stat().st_size if path.exists() else 0,
            'parser_name': self.capability.name,
            'parser_priority': self.capability.priority
        }
        if additional_metadata:
            base_metadata.update(additional_metadata)
        return base_metadata
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return self.capability.supported_extensions
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Chunk text into smaller pieces with overlap.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            
            # Find a good breaking point (end of sentence, paragraph, etc.)
            if end < text_length:
                # Look for sentence end
                for sep in ['. ', '.\n', '\n\n', '\n', ' ']:
                    pos = text.rfind(sep, start + overlap, end)
                    if pos > start:
                        end = pos + len(sep) - 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position
            start = end - overlap if end < text_length else text_length
            
            # Prevent infinite loop
            if start <= 0 and chunks:
                break
        
        return chunks
    
    def __repr__(self) -> str:
        """String representation of parser."""
        return f"{self.__class__.__name__}(name='{self.capability.name}', extensions={self.capability.supported_extensions})"
