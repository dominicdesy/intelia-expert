"""
Modèles de données centralisés pour l'extracteur de connaissances
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class DocumentContext:
    """Contexte d'un document analysé par LLM"""

    genetic_line: str
    document_type: str
    species: str
    measurement_units: str
    target_audience: str
    table_types_expected: List[str]
    confidence_score: float = 0.0
    raw_analysis: str = ""


@dataclass
class ChunkMetadata:
    """Métadonnées enrichies d'un chunk analysé"""

    intent_category: str
    content_type: str
    technical_level: str
    age_applicability: List[str]
    applicable_metrics: List[str]
    actionable_recommendations: List[str]
    followup_themes: List[str]
    detected_phase: Optional[str]
    detected_bird_type: Optional[str]
    detected_site_type: Optional[str]
    confidence_score: float = 0.0
    reasoning: str = ""


@dataclass
class KnowledgeChunk:
    """Chunk de connaissance complet"""

    chunk_id: str
    content: str
    word_count: int
    document_context: DocumentContext
    metadata: ChunkMetadata
    source_file: str
    extraction_timestamp: str

    def to_weaviate_object(self) -> Dict[str, Any]:
        """Convertit en objet Weaviate avec format de date RFC3339"""
        try:
            # Conversion timestamp ISO vers RFC3339
            timestamp_dt = datetime.fromisoformat(self.extraction_timestamp)
            rfc3339_timestamp = timestamp_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        except Exception:
            rfc3339_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return {
            "content": self.content,
            "genetic_line": self.document_context.genetic_line,
            "document_type": self.document_context.document_type,
            "species": self.document_context.species,
            "target_audience": self.document_context.target_audience,
            "intent_category": self.metadata.intent_category,
            "content_type": self.metadata.content_type,
            "technical_level": self.metadata.technical_level,
            "detected_phase": self.metadata.detected_phase,
            "detected_bird_type": self.metadata.detected_bird_type,
            "detected_site_type": self.metadata.detected_site_type,
            "age_applicability": self.metadata.age_applicability,
            "applicable_metrics": self.metadata.applicable_metrics,
            "actionable_recommendations": self.metadata.actionable_recommendations,
            "followup_themes": self.metadata.followup_themes,
            "confidence_score": self.metadata.confidence_score,
            "word_count": self.word_count,
            "source_file": self.source_file,
            "extraction_timestamp": rfc3339_timestamp,
            "chunk_id": self.chunk_id,
        }


@dataclass
class ValidationResult:
    """Résultat de validation"""

    conformity_score: float
    requires_correction: bool
    validation_details: Dict[str, Any]
    error: Optional[str] = None
    corrections_applied: Optional[Dict[str, Any]] = None


@dataclass
class ProcessingResult:
    """Résultat de traitement de document"""

    document_name: str
    segments_created: int
    chunks_validated: int
    injection_success: int
    injection_errors: int
    final_conformity_score: float
    corrections_applied: bool
    report_path: str
    error: Optional[str] = None
