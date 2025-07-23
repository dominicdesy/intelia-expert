#!/usr/bin/env python3
"""
Adaptive Chunking Configuration
Clean code compliant version with infinite loop fix
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ChunkType(Enum):
    """Types of chunks based on content."""
    PERFORMANCE_DATA = "performance_data"
    ENVIRONMENTAL_DATA = "environmental_data"
    NUTRITION_DATA = "nutrition_data"
    STRUCTURED_DATA = "structured_data"
    TECHNICAL_MANUAL = "technical_manual"
    STANDARD_TEXT = "standard_text"
    LARGE_DOCUMENT = "large_document"


@dataclass
class ChunkingStrategy:
    """Chunking strategy configuration."""
    chunk_type: ChunkType
    chunk_size: int
    overlap: int
    context_window: int
    delimiter_patterns: List[str]
    preserve_structure: bool = True
    semantic_splitting: bool = False


class AdaptiveChunkingConfig:
    """Adaptive chunking configuration manager."""
    
    # Predefined chunking strategies
    CHUNKING_STRATEGIES = {
        ChunkType.PERFORMANCE_DATA: ChunkingStrategy(
            chunk_type=ChunkType.PERFORMANCE_DATA,
            chunk_size=200,
            overlap=40,
            context_window=100,
            delimiter_patterns=[r'\n\n', r'\n', r'[,;]', r'Week \d+', r'Day \d+'],
            preserve_structure=True
        ),
        ChunkType.ENVIRONMENTAL_DATA: ChunkingStrategy(
            chunk_type=ChunkType.ENVIRONMENTAL_DATA,
            chunk_size=180,
            overlap=50,
            context_window=80,
            delimiter_patterns=[r'\n\n', r'\n', r'Temperature:', r'Humidity:', r'Ventilation:'],
            preserve_structure=True
        ),
        ChunkType.NUTRITION_DATA: ChunkingStrategy(
            chunk_type=ChunkType.NUTRITION_DATA,
            chunk_size=250,
            overlap=60,
            context_window=120,
            delimiter_patterns=[r'\n\n', r'\n', r'Phase:', r'Crude protein:', r'Energy:'],
            preserve_structure=True
        ),
        ChunkType.STRUCTURED_DATA: ChunkingStrategy(
            chunk_type=ChunkType.STRUCTURED_DATA,
            chunk_size=150,
            overlap=30,
            context_window=50,
            delimiter_patterns=[r'\n', r',', r';', r'\t'],
            preserve_structure=True
        ),
        ChunkType.TECHNICAL_MANUAL: ChunkingStrategy(
            chunk_type=ChunkType.TECHNICAL_MANUAL,
            chunk_size=400,
            overlap=80,
            context_window=150,
            delimiter_patterns=[r'\n\n\n', r'\n\n', r'\n#', r'\n##', r'\n###'],
            preserve_structure=True,
            semantic_splitting=True
        ),
        ChunkType.STANDARD_TEXT: ChunkingStrategy(
            chunk_type=ChunkType.STANDARD_TEXT,
            chunk_size=300,
            overlap=50,
            context_window=100,
            delimiter_patterns=[r'\n\n', r'\n', r'\.', r'!', r'\?'],
            preserve_structure=True
        ),
        ChunkType.LARGE_DOCUMENT: ChunkingStrategy(
            chunk_type=ChunkType.LARGE_DOCUMENT,
            chunk_size=800,
            overlap=100,
            context_window=200,
            delimiter_patterns=[r'\n\n\n', r'\n\n', r'\n#', r'Chapter \d+', r'Section \d+'],
            preserve_structure=True,
            semantic_splitting=True
        )
    }
    
    @classmethod
    def detect_content_type(cls, text: str) -> ChunkType:
        """Detect content type based on text patterns."""
        text_lower = text.lower()
        
        # Performance data patterns
        performance_patterns = [
            r'week \d+', r'day \d+', r'weight.*g', r'fcr', r'gain', r'mortality',
            r'ross.*308', r'cobb.*500', r'performance.*data'
        ]
        
        # Environmental data patterns
        environmental_patterns = [
            r'temperature.*°c', r'humidity.*%', r'ventilation', r'heating',
            r'cooling', r'environment', r'climate'
        ]
        
        # Nutrition data patterns
        nutrition_patterns = [
            r'protein.*%', r'energy.*kcal', r'crude.*protein', r'lysine',
            r'methionine', r'nutrition', r'feed', r'starter.*phase'
        ]
        
        # Technical manual patterns
        manual_patterns = [
            r'management.*guide', r'protocol', r'procedure', r'chapter',
            r'section', r'introduction', r'manual'
        ]
        
        # Structured data patterns
        structured_patterns = [
            r'\d+[,;\t]', r'table.*\d+', r'data.*table', r'values:'
        ]
        
        # Count pattern matches
        performance_score = sum(1 for pattern in performance_patterns if re.search(pattern, text_lower))
        environmental_score = sum(1 for pattern in environmental_patterns if re.search(pattern, text_lower))
        nutrition_score = sum(1 for pattern in nutrition_patterns if re.search(pattern, text_lower))
        manual_score = sum(1 for pattern in manual_patterns if re.search(pattern, text_lower))
        structured_score = sum(1 for pattern in structured_patterns if re.search(pattern, text_lower))
        
        # Determine content type based on highest score
        scores = {
            ChunkType.PERFORMANCE_DATA: performance_score,
            ChunkType.ENVIRONMENTAL_DATA: environmental_score,
            ChunkType.NUTRITION_DATA: nutrition_score,
            ChunkType.TECHNICAL_MANUAL: manual_score,
            ChunkType.STRUCTURED_DATA: structured_score
        }
        
        # Get the type with highest score
        max_score = max(scores.values())
        if max_score > 0:
            for chunk_type, score in scores.items():
                if score == max_score:
                    return chunk_type
        
        # Check document length for large document classification
        if len(text) > 5000:
            return ChunkType.LARGE_DOCUMENT
        
        # Default to standard text
        return ChunkType.STANDARD_TEXT
    
    @classmethod
    def get_chunking_strategy(cls, text: str) -> ChunkingStrategy:
        """Get the appropriate chunking strategy for text."""
        content_type = cls.detect_content_type(text)
        return cls.CHUNKING_STRATEGIES.get(content_type, cls.CHUNKING_STRATEGIES[ChunkType.STANDARD_TEXT])
    
    @classmethod
    def adaptive_chunk_text(cls, text: str, strategy: Optional[ChunkingStrategy] = None) -> List[str]:
        """
        Adaptively chunk text based on content type.
        
        Args:
            text: Text to chunk
            strategy: Optional specific strategy to use
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        if strategy is None:
            strategy = cls.get_chunking_strategy(text)
        
        logger.debug(f"Using chunking strategy: {strategy.chunk_type.value}")
        
        # Apply intelligent chunking based on strategy
        if strategy.semantic_splitting:
            chunks = cls._semantic_chunk_text(text, strategy)
        else:
            chunks = cls._simple_chunk_text(text, strategy)
        
        # Post-process chunks for quality
        chunks = cls._post_process_chunks(chunks, strategy)
        
        logger.debug(f"Created {len(chunks)} chunks from {len(text)} characters")
        return chunks
    
    @classmethod
    def _semantic_chunk_text(cls, text: str, strategy: ChunkingStrategy) -> List[str]:
        """Semantic chunking using delimiters and content patterns."""
        chunks = []
        
        # Try delimiter-based splitting first
        primary_delimiter = strategy.delimiter_patterns[0] if strategy.delimiter_patterns else r'\n\n'
        
        sections = re.split(primary_delimiter, text)
        current_chunk = ""
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # Check if adding this section would exceed chunk size
            potential_chunk = current_chunk + ("\n\n" if current_chunk else "") + section
            
            if len(potential_chunk) <= strategy.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it exists
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Handle section that's too large
                if len(section) > strategy.chunk_size:
                    # Split large section
                    sub_chunks = cls._simple_chunk_text(section, strategy)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = section
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    @classmethod
    def _simple_chunk_text(cls, text: str, strategy: ChunkingStrategy) -> List[str]:
        """Simple sliding window chunking with infinite loop protection."""
        chunks = []
        chunk_size = strategy.chunk_size
        overlap = strategy.overlap
        text_length = len(text)
        
        # Ensure valid parameters to prevent infinite loops
        if chunk_size <= 0:
            chunk_size = 300
        if overlap >= chunk_size:
            overlap = max(0, chunk_size // 4)  # Limit overlap to 25% of chunk_size
        
        start = 0
        iteration_count = 0
        max_iterations = (text_length // (chunk_size - overlap)) + 10  # Safety limit
        
        while start < text_length and iteration_count < max_iterations:
            iteration_count += 1
            
            end = min(start + chunk_size, text_length)
            
            # Try to find a good breaking point
            if end < text_length and strategy.preserve_structure:
                # Look for natural breaks within overlap distance
                for delimiter in ['. ', '.\n', '\n\n', '\n', '. ', '! ', '? ']:
                    delimiter_length = len(delimiter)
                    search_start = max(end - overlap, start + chunk_size // 2)
                    search_end = min(end + overlap, text_length)
                    
                    for i in range(search_start, search_end - delimiter_length + 1):
                        if text[i:i + delimiter_length] == delimiter:
                            end = i + delimiter_length
                            break
                    else:
                        continue
                    break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # FIXED: Proper advancement to prevent infinite loops
            new_start = end - overlap
            
            # Ensure we always make progress
            if new_start <= start:
                new_start = start + max(1, chunk_size // 2)
            
            start = new_start
            
            # Additional safety check
            if start >= text_length:
                break
        
        # Log warning if we hit iteration limit
        if iteration_count >= max_iterations:
            logger.warning(f"Chunking iteration limit reached for text of length {text_length}")
        
        return chunks
    
    @classmethod
    def _post_process_chunks(cls, chunks: List[str], strategy: ChunkingStrategy) -> List[str]:
        """Post-process chunks to ensure quality."""
        processed_chunks = []
        
        for chunk in chunks:
            chunk = chunk.strip()
            
            # Skip empty chunks
            if not chunk:
                continue
            
            # Skip very short chunks (unless they contain important keywords)
            if len(chunk) < 20:
                important_keywords = ['ross', 'cobb', 'temperature', 'weight', 'fcr', 'week', 'day']
                if not any(keyword in chunk.lower() for keyword in important_keywords):
                    continue
            
            processed_chunks.append(chunk)
        
        logger.debug(f"Post-processed {len(chunks)} chunks into {len(processed_chunks)} final chunks")
        return processed_chunks
    
    @classmethod
    def get_chunk_metadata(cls, chunk: str, chunk_index: int, strategy: ChunkingStrategy) -> Dict[str, Any]:
        """Generate metadata for a chunk."""
        return {
            'chunk_index': chunk_index,
            'chunk_type': strategy.chunk_type.value,
            'chunk_size': len(chunk),
            'chunking_strategy': strategy.chunk_type.value,
            'word_count': len(chunk.split()),
            'has_performance_data': any(keyword in chunk.lower() for keyword in ['weight', 'gain', 'fcr', 'performance']),
            'has_environmental_data': any(keyword in chunk.lower() for keyword in ['temperature', 'humidity', 'ventilation']),
            'has_nutrition_data': any(keyword in chunk.lower() for keyword in ['protein', 'energy', 'feed', 'nutrition']),
            'has_structured_data': any(keyword in chunk.lower() for keyword in ['week', 'day', 'phase', 'values'])
        }


class AdaptiveChunker:
    """
    Adaptive chunker wrapper compatible with embedder.
    Clean code compliant version with infinite loop protection.
    """
    
    def __init__(self):
        self.config = AdaptiveChunkingConfig()
    
    def chunk_text(self, text: str, content_type: Optional[str] = None) -> List[str]:
        """
        Chunk text using adaptive strategy with safety checks.
        
        Args:
            text: Text to chunk
            content_type: Optional content type hint
            
        Returns:
            List of text chunks
        """
        try:
            # Add length check for very large documents
            if len(text) > 100000:  # 100KB limit for safety
                logger.warning(f"Text very large ({len(text)} chars), applying size limit")
                text = text[:100000]
            
            return AdaptiveChunkingConfig.adaptive_chunk_text(text)
        except Exception as e:
            logger.error(f"Adaptive chunking failed: {e}")
            # Fallback to simple splitting
            return cls._fallback_chunk(text)
    
    @classmethod
    def _fallback_chunk(cls, text: str, chunk_size: int = 1000) -> List[str]:
        """Simple fallback chunking method."""
        if not text:
            return []
        
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size].strip()
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def get_chunking_strategy(self, text: str) -> ChunkingStrategy:
        """Get the chunking strategy for given text."""
        return AdaptiveChunkingConfig.get_chunking_strategy(text)
    
    def detect_content_type(self, text: str) -> ChunkType:
        """Detect content type of text."""
        return AdaptiveChunkingConfig.detect_content_type(text)


if __name__ == "__main__":
    # Test adaptive chunking
    print("🧪 TESTING ADAPTIVE CHUNKING")
    print("=" * 40)
    
    # Test content type detection
    test_contents = {
        "Performance Data": "Ross 308 Week 3 performance data: target weight 920g, daily gain 69g, FCR 1.37. Week 4 shows continued improvement.",
        "Environmental Data": "Temperature management Week 1: 32-35°C, humidity 60-70%, ventilation minimal. Heating systems operational.",
        "Nutrition Data": "Starter phase nutrition: crude protein 23%, ME 3000 kcal/kg, lysine 1.35%, methionine 0.52%. Grower phase follows.",
        "Technical Manual": "Broiler Management Manual: This comprehensive guide covers all aspects of broiler production. Chapter 1: Introduction to broiler management.",
        "Standard Text": "This is a general document about broiler management practices and protocols for optimal production."
    }
    
    for content_name, content in test_contents.items():
        detected_type = AdaptiveChunkingConfig.detect_content_type(content)
        strategy = AdaptiveChunkingConfig.get_chunking_strategy(content)
        
        print(f"\n📄 {content_name}:")
        print(f"   Detected type: {detected_type.value}")
        print(f"   Strategy: {strategy.chunk_type.value}")
        print(f"   Chunk size: {strategy.chunk_size}")
        print(f"   Overlap: {strategy.overlap}")
        
        # Test chunking
        chunks = AdaptiveChunkingConfig.adaptive_chunk_text(content * 5)  # Make it longer
        print(f"   Chunks created: {len(chunks)}")
        
        if chunks:
            print(f"   First chunk: {chunks[0][:100]}...")
    
    print("\n✅ Adaptive chunking test completed")