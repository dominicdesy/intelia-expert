# -*- coding: utf-8 -*-
"""
data_models.py - Classes et structures de données pour RAG Engine
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class RAGSource(Enum):
    RAG_KNOWLEDGE = "rag_knowledge"
    RAG_VERIFIED = "rag_verified"
    OOD_FILTERED = "ood_filtered" 
    FALLBACK_NEEDED = "fallback_needed"
    ERROR = "error"

@dataclass
class RAGResult:
    source: RAGSource
    answer: Optional[str] = None
    confidence: float = 0.0
    context_docs: List[Dict] = None
    processing_time: float = 0.0
    metadata: Dict = None
    verification_status: Optional[Dict] = None
    intent_result: Optional[Any] = None  # IntentResult
    
    def __post_init__(self):
        if self.context_docs is None:
            self.context_docs = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class Document:
    content: str
    metadata: Dict = None
    score: float = 0.0
    original_distance: Optional[float] = None
    explain_score: Optional[Dict] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get(self, key: str, default=None):
        """Méthode get() pour compatibilité avec les guardrails"""
        if key == "content":
            return self.content
        elif key == "metadata":
            return self.metadata
        elif key == "score":
            return self.score
        elif key == "explain_score":
            return self.explain_score
        elif key in self.metadata:
            return self.metadata[key]
        else:
            return getattr(self, key, default)