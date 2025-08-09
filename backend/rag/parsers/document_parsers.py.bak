"""
Document Format Parser Plugins
Standard parsers for PDF, text, and markdown documents
"""

from typing import List, Dict, Optional
import logging

try:
    from langchain_community.document_loaders import PyPDFLoader, TextLoader
except ImportError:
    from langchain.document_loaders import PyPDFLoader, TextLoader

# Import base classes from the correct location
try:
    from .parser_base import BaseParser, ParserCapability, Document
except ImportError:
    try:
        from parser_base import BaseParser, ParserCapability, Document
    except ImportError:
        # Fallback definitions included in the file
        from abc import ABC, abstractmethod
        from dataclasses import dataclass
        from typing import Dict, Any, List, Optional
        from pathlib import Path
        
        @dataclass
        class ParserCapability:
            name: str
            supported_extensions: List[str]
            breed_types: List[str]
            data_types: List[str]
            quality_score: str
            description: str
            priority: int
        
        @dataclass
        class Document:
            page_content: str
            metadata: Dict[str, Any]
            
            def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
                self.page_content = page_content
                self.metadata = metadata or {}
        
        class BaseParser(ABC):
            @property
            @abstractmethod
            def capability(self) -> ParserCapability:
                pass
            
            @abstractmethod
            def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
                pass
            
            @abstractmethod
            def parse(self, file_path: str) -> List[Document]:
                pass
            
            def create_base_metadata(self, file_path: str, additional_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                return self.capability.supported_extensions

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """
    Standard PDF document parser
    
    Handles PDF files using PyPDF loader with basic text extraction.
    Suitable for manuals, reports, and documentation.
    """
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="PDFParser",
            supported_extensions=['.pdf'],
            breed_types=['Any'],
            data_types=['documentation', 'manuals', 'reports', 'guides'],
            quality_score='good',
            description='Standard PDF parser using PyPDF for text extraction',
            priority=40
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """Evaluate capability to parse PDF files"""
        file_ext = file_path.lower().split('.')[-1]
        return 1.0 if file_ext == 'pdf' else 0.0
    
    def parse(self, file_path: str) -> List[Document]:
        """Parse PDF document using PyPDF loader"""
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            # Enrich metadata for each document
            for i, doc in enumerate(documents):
                doc.metadata.update(self.create_base_metadata(file_path, {
                    'page_number': i + 1,
                    'total_pages': len(documents),
                    'document_type': 'pdf_document',
                    'extraction_method': 'pypdf'
                }))
            
            logger.info(f"Extracted {len(documents)} pages from PDF")
            return documents
            
        except Exception as e:
            logger.error(f"Error parsing PDF file {file_path}: {e}")
            return []


class TextParser(BaseParser):
    """
    Standard text document parser
    
    Handles plain text and markdown files with UTF-8 encoding.
    Suitable for notes, guidelines, and documentation.
    """
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="TextParser",
            supported_extensions=['.txt', '.md'],
            breed_types=['Any'],
            data_types=['documentation', 'notes', 'guidelines', 'markdown'],
            quality_score='good',
            description='Standard text parser for plain text and markdown files',
            priority=35
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """Evaluate capability to parse text files"""
        file_ext = file_path.lower().split('.')[-1]
        return 1.0 if file_ext in ['txt', 'md'] else 0.0
    
    def parse(self, file_path: str) -> List[Document]:
        """Parse text document with encoding handling"""
        try:
            # Try UTF-8 first, fallback to other encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    loader = TextLoader(file_path, encoding=encoding)
                    documents = loader.load()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError(f"Could not decode file {file_path} with any supported encoding")
            
            # Enrich metadata
            for doc in documents:
                file_ext = file_path.lower().split('.')[-1]
                doc.metadata.update(self.create_base_metadata(file_path, {
                    'document_type': 'markdown_document' if file_ext == 'md' else 'text_document',
                    'encoding_used': encoding,
                    'file_format': file_ext.upper()
                }))
            
            logger.info(f"Loaded text document with {encoding} encoding")
            return documents
            
        except Exception as e:
            logger.error(f"Error parsing text file {file_path}: {e}")
            return []


class MarkdownParser(BaseParser):
    """
    Enhanced markdown parser with structure awareness
    
    Specialized parser for markdown files that preserves
    document structure and hierarchy.
    """
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="MarkdownParser",
            supported_extensions=['.md', '.markdown'],
            breed_types=['Any'],
            data_types=['documentation', 'structured_text', 'guides'],
            quality_score='high',
            description='Enhanced markdown parser with structure preservation',
            priority=45  # Higher than generic text parser for .md files
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """Evaluate capability to parse markdown files"""
        file_ext = file_path.lower().split('.')[-1]
        
        if file_ext not in ['md', 'markdown']:
            return 0.0
        
        base_score = 0.8
        
        # Check for markdown structure in content
        if content_sample:
            markdown_indicators = ['#', '##', '###', '**', '*', '```', '- ', '1. ']
            found_indicators = sum(1 for indicator in markdown_indicators 
                                 if indicator in content_sample)
            structure_score = min(found_indicators / len(markdown_indicators), 0.2)
            base_score += structure_score
        
        return min(base_score, 1.0)
    
    def parse(self, file_path: str) -> List[Document]:
        """Parse markdown with structure awareness"""
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into logical sections based on headers
            sections = self._split_by_headers(content)
            
            documents = []
            for i, section in enumerate(sections):
                if section['content'].strip():
                    doc = Document(
                        page_content=section['content'],
                        metadata={
                            **self.create_base_metadata(file_path, {
                                'section_title': section['title'],
                                'section_level': section['level'],
                                'section_index': i,
                                'total_sections': len(sections),
                                'document_type': 'structured_markdown',
                                'has_structure': True
                            })
                        }
                    )
                    documents.append(doc)
            
            logger.info(f"Created {len(documents)} structured sections from markdown")
            return documents
            
        except Exception as e:
            logger.error(f"Error parsing markdown file {file_path}: {e}")
            # Fallback to basic text parsing
            return TextParser().parse(file_path)
    
    def _split_by_headers(self, content: str) -> List[dict]:
        """Split markdown content by headers while preserving structure"""
        import re
        
        lines = content.split('\n')
        sections = []
        current_section = {'title': 'Introduction', 'level': 0, 'content': ''}
        
        for line in lines:
            # Check if line is a header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            
            if header_match:
                # Save current section if it has content
                if current_section['content'].strip():
                    sections.append(current_section)
                
                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2)
                current_section = {
                    'title': title,
                    'level': level,
                    'content': line + '\n'
                }
            else:
                # Add line to current section
                current_section['content'] += line + '\n'
        
        # Add the last section
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections


# Export parser classes
DocumentParser = PDFParser  # Alias for backward compatibility
