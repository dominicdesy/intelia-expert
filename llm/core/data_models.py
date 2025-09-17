# -*- coding: utf-8 -*-
"""
data_models.py - Classes et structures de données pour RAG Engine
Version corrigée avec tous les RAGSource nécessaires et architecture modulaire
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import time

class RAGSource(Enum):
    """Sources de réponse du système RAG avec codes d'erreur détaillés"""
    
    # Sources de succès
    RAG_SUCCESS = "rag_success"
    RAG_KNOWLEDGE = "rag_knowledge"  # Maintenu pour compatibilité
    RAG_VERIFIED = "rag_verified"
    
    # Sources de fallback/filtrage
    FALLBACK_NEEDED = "fallback_needed"
    OOD_FILTERED = "ood_filtered"
    
    # Erreurs spécifiques par étape
    EMBEDDING_FAILED = "embedding_failed"
    SEARCH_FAILED = "search_failed"
    NO_DOCUMENTS_FOUND = "no_documents_found"
    LOW_CONFIDENCE = "low_confidence"
    GENERATION_FAILED = "generation_failed"
    
    # Erreurs générales
    INTERNAL_ERROR = "internal_error"
    ERROR = "error"  # Maintenu pour compatibilité
    
    @property
    def is_success(self) -> bool:
        """Indique si la source représente un succès"""
        return self in {self.RAG_SUCCESS, self.RAG_KNOWLEDGE, self.RAG_VERIFIED}
    
    @property
    def is_error(self) -> bool:
        """Indique si la source représente une erreur"""
        return self in {
            self.EMBEDDING_FAILED, self.SEARCH_FAILED, self.NO_DOCUMENTS_FOUND,
            self.LOW_CONFIDENCE, self.GENERATION_FAILED, self.INTERNAL_ERROR, self.ERROR
        }
    
    @property
    def is_fallback(self) -> bool:
        """Indique si la source nécessite un fallback"""
        return self in {self.FALLBACK_NEEDED, self.OOD_FILTERED}

@dataclass
class RAGResult:
    """Résultat d'une requête RAG avec métadonnées enrichies"""
    
    source: RAGSource
    answer: Optional[str] = None
    confidence: float = 0.0
    context_docs: List[Dict] = field(default_factory=list)
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    verification_status: Optional[Dict] = None
    intent_result: Optional[Any] = None  # IntentResult
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Post-initialisation avec validation"""
        if self.context_docs is None:
            self.context_docs = []
        if self.metadata is None:
            self.metadata = {}
        
        # Ajout métadonnées système automatiques
        self.metadata.setdefault("result_type", self.source.value)
        self.metadata.setdefault("is_success", self.source.is_success)
        self.metadata.setdefault("is_error", self.source.is_error)
        self.metadata.setdefault("timestamp", self.timestamp)
    
    @property
    def is_valid(self) -> bool:
        """Vérifie si le résultat est valide et utilisable"""
        return (
            self.source.is_success and 
            self.answer is not None and 
            len(self.answer.strip()) > 0 and
            self.confidence > 0
        )
    
    @property
    def should_retry(self) -> bool:
        """Indique si la requête devrait être retentée"""
        return self.source in {
            RAGSource.EMBEDDING_FAILED,
            RAGSource.SEARCH_FAILED,
            RAGSource.INTERNAL_ERROR
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire pour sérialisation"""
        return {
            "source": self.source.value,
            "answer": self.answer,
            "confidence": self.confidence,
            "context_docs": self.context_docs,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
            "verification_status": self.verification_status,
            "timestamp": self.timestamp,
            "is_valid": self.is_valid,
            "should_retry": self.should_retry
        }

@dataclass
class Document:
    """Document avec score et métadonnées enrichies"""
    
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    original_distance: Optional[float] = None
    explain_score: Optional[Dict] = None
    source_type: str = "unknown"
    retrieval_method: str = "hybrid"
    
    def __post_init__(self):
        """Post-initialisation avec validation"""
        if self.metadata is None:
            self.metadata = {}
        
        # Ajout métadonnées automatiques
        self.metadata.setdefault("content_length", len(self.content))
        self.metadata.setdefault("source_type", self.source_type)
        self.metadata.setdefault("retrieval_method", self.retrieval_method)
        
        # Validation du score
        if not 0 <= self.score <= 1:
            self.score = max(0, min(1, self.score))
    
    def get(self, key: str, default=None) -> Any:
        """Méthode get() pour compatibilité avec les guardrails et systèmes externes"""
        if key == "content":
            return self.content
        elif key == "metadata":
            return self.metadata
        elif key == "score":
            return self.score
        elif key == "explain_score":
            return self.explain_score
        elif key == "source_type":
            return self.source_type
        elif key == "retrieval_method":
            return self.retrieval_method
        elif key in self.metadata:
            return self.metadata[key]
        else:
            return getattr(self, key, default)
    
    @property
    def is_relevant(self) -> bool:
        """Indique si le document est considéré comme pertinent"""
        return self.score >= 0.3  # Seuil configurable
    
    @property
    def quality_score(self) -> float:
        """Score de qualité combiné basé sur différents facteurs"""
        base_score = self.score
        
        # Bonus pour contenu substantiel
        length_bonus = min(0.1, len(self.content) / 1000)
        
        # Bonus pour métadonnées riches
        metadata_bonus = min(0.05, len(self.metadata) / 20)
        
        return min(1.0, base_score + length_bonus + metadata_bonus)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le document en dictionnaire"""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score,
            "original_distance": self.original_distance,
            "explain_score": self.explain_score,
            "source_type": self.source_type,
            "retrieval_method": self.retrieval_method,
            "is_relevant": self.is_relevant,
            "quality_score": self.quality_score
        }

@dataclass
class QueryContext:
    """Contexte enrichi pour une requête"""
    
    query: str
    tenant_id: str = "default"
    language: str = "fr"
    conversation_history: List[Dict] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.user_preferences is None:
            self.user_preferences = {}

# Aliases pour compatibilité avec l'ancien code
RAGResponse = RAGResult  # Alias
DocumentResult = Document  # Alias

# Types unions pour flexibilité
DocumentList = List[Document]
ResultMetadata = Dict[str, Any]
ContextDocs = List[Dict[str, Any]]