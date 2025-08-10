"""
Document Format Parser Plugins
Standard parsers for PDF, text, and markdown documents
"""

from typing import List, Dict, Optional
import logging
import re

try:
    from langchain_community.document_loaders import PyPDFLoader, TextLoader
except ImportError:
    from langchain.document_loaders import PyPDFLoader, TextLoader

try:
    from .parser_base import BaseParser, ParserCapability, Document
except ImportError:
    try:
        from parser_base import BaseParser, ParserCapability, Document
    except ImportError:
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

def _detect_table_structure(text: str) -> bool:
    """
    Détection rapide de structure tabulaire pour forcer chunk_type='table'
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    # Markdown
    pipe_lines = [ln for ln in lines if '|' in ln.strip()]
    if len(pipe_lines) >= 2 and any(re.match(r'^\s*\|?[\s:\-\|\+]+\|?\s*$', ln) for ln in pipe_lines):
        return True
    # HTML
    if re.search(r'<\s*table\b', text, flags=re.I):
        return True
    # CSV/TSV
    for delim in [',', ';', '\t']:
        delim_lines = [ln for ln in lines if ln.count(delim) >= 2]
        if len(delim_lines) >= max(2, int(0.3 * len(lines))):
            counts = [ln.count(delim) for ln in delim_lines[:10]]
            if counts and (max(counts) - min(counts) <= 2):
                return True
    # Whitespace aligned
    ws_lines = sum(1 for ln in lines if re.search(r'\S+\s{2,}\S+\s{2,}\S+', ln))
    if ws_lines >= max(2, int(0.3 * len(lines))):
        return True
    return False


class PDFParser(BaseParser):
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
        return 1.0 if file_path.lower().endswith('.pdf') else 0.0
    
    def parse(self, file_path: str) -> List[Document]:
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            for i, doc in enumerate(documents):
                meta = self.create_base_metadata(file_path, {
                    'page_number': i + 1,
                    'total_pages': len(documents),
                    'document_type': 'pdf_document',
                    'extraction_method': 'pypdf'
                })
                # ✅ Forcer table si détecté
                if _detect_table_structure(doc.page_content):
                    meta['chunk_type'] = 'table'
                doc.metadata.update(meta)
            return documents
        except Exception as e:
            logger.error(f"Error parsing PDF file {file_path}: {e}")
            return []


class TextParser(BaseParser):
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
        return 1.0 if file_path.lower().split('.')[-1] in ['txt', 'md'] else 0.0
    
    def parse(self, file_path: str) -> List[Document]:
        try:
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            for encoding in encodings:
                try:
                    loader = TextLoader(file_path, encoding=encoding)
                    documents = loader.load()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError(f"Cannot decode {file_path}")
            for doc in documents:
                file_ext = file_path.lower().split('.')[-1]
                meta = self.create_base_metadata(file_path, {
                    'document_type': 'markdown_document' if file_ext == 'md' else 'text_document',
                    'encoding_used': encoding,
                    'file_format': file_ext.upper()
                })
                if _detect_table_structure(doc.page_content):
                    meta['chunk_type'] = 'table'
                doc.metadata.update(meta)
            return documents
        except Exception as e:
            logger.error(f"Error parsing text file {file_path}: {e}")
            return []


class MarkdownParser(BaseParser):
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="MarkdownParser",
            supported_extensions=['.md', '.markdown'],
            breed_types=['Any'],
            data_types=['documentation', 'structured_text', 'guides'],
            quality_score='high',
            description='Enhanced markdown parser with structure preservation',
            priority=45
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        if file_path.lower().split('.')[-1] not in ['md', 'markdown']:
            return 0.0
        base_score = 0.8
        if content_sample:
            markdown_indicators = ['#', '##', '###', '**', '*', '```', '- ', '1. ']
            found_indicators = sum(1 for indicator in markdown_indicators if indicator in content_sample)
            base_score += min(found_indicators / len(markdown_indicators), 0.2)
        return min(base_score, 1.0)
    
    def parse(self, file_path: str) -> List[Document]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            sections = self._split_by_headers(content)
            documents = []
            for i, section in enumerate(sections):
                if section['content'].strip():
                    meta = self.create_base_metadata(file_path, {
                        'section_title': section['title'],
                        'section_level': section['level'],
                        'section_index': i,
                        'total_sections': len(sections),
                        'document_type': 'structured_markdown',
                        'has_structure': True
                    })
                    if _detect_table_structure(section['content']):
                        meta['chunk_type'] = 'table'
                    documents.append(Document(page_content=section['content'], metadata=meta))
            return documents
        except Exception as e:
            logger.error(f"Error parsing markdown file {file_path}: {e}")
            return TextParser().parse(file_path)
    
    def _split_by_headers(self, content: str) -> List[dict]:
        import re
        lines = content.split('\n')
        sections = []
        current_section = {'title': 'Introduction', 'level': 0, 'content': ''}
        for line in lines:
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if header_match:
                if current_section['content'].strip():
                    sections.append(current_section)
                level = len(header_match.group(1))
                title = header_match.group(2)
                current_section = {'title': title, 'level': level, 'content': line + '\n'}
            else:
                current_section['content'] += line + '\n'
        if current_section['content'].strip():
            sections.append(current_section)
        return sections

DocumentParser = PDFParser
