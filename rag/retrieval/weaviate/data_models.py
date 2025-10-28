# -*- coding: utf-8 -*-
"""
data_models.py - Weaviate Data Models for Intelia Expert
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
data_models.py - Weaviate Data Models for Intelia Expert
Defines the schema and data classes for Weaviate collections
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class WeaviateDocument:
    """Document stored in Weaviate"""

    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    vector: Optional[List[float]] = None
    uuid: Optional[str] = None

    # Poultry-specific fields
    species: Optional[str] = None
    breed: Optional[str] = None
    age_days: Optional[int] = None
    metric: Optional[str] = None
    domain: Optional[str] = None
    language: Optional[str] = "fr"

    # Document metadata
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class WeaviateQueryResult:
    """Result from Weaviate query"""

    documents: List[WeaviateDocument]
    total_count: int
    query_time_ms: float
    certainty_scores: List[float] = field(default_factory=list)
    distances: List[float] = field(default_factory=list)


class WeaviateSchema:
    """Weaviate collection schema definition"""

    @staticmethod
    def get_collection_config(
        collection_name: str = "InteliaExpertKnowledge",
    ) -> Dict[str, Any]:
        """
        Returns Weaviate v4 collection configuration

        Compatible with:
        - Weaviate Cloud
        - text2vec-openai vectorizer
        - 1536 dimensions (OpenAI text-embedding-3-small)
        """
        return {
            "name": collection_name,
            "description": "Intelia Expert poultry knowledge base with multilingual support",
            "vectorizer": "text2vec-openai",
            "moduleConfig": {
                "text2vec-openai": {
                    "model": "text-embedding-3-small",
                    "dimensions": 1536,
                    "type": "text",
                }
            },
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Main document content (multilingual)",
                    "indexFilterable": True,
                    "indexSearchable": True,
                },
                {
                    "name": "species",
                    "dataType": ["text"],
                    "description": "Poultry species (chicken, turkey, duck, etc.)",
                    "indexFilterable": True,
                },
                {
                    "name": "breed",
                    "dataType": ["text"],
                    "description": "Breed name (Ross 308, Cobb 500, etc.)",
                    "indexFilterable": True,
                },
                {
                    "name": "age_days",
                    "dataType": ["int"],
                    "description": "Age in days",
                    "indexFilterable": True,
                    "indexRangeFilters": True,
                },
                {
                    "name": "metric",
                    "dataType": ["text"],
                    "description": "Performance metric (weight, FCR, mortality, etc.)",
                    "indexFilterable": True,
                },
                {
                    "name": "domain",
                    "dataType": ["text"],
                    "description": "Knowledge domain (production, health, nutrition, etc.)",
                    "indexFilterable": True,
                },
                {
                    "name": "language",
                    "dataType": ["text"],
                    "description": "Document language (ISO 639-1 code)",
                    "indexFilterable": True,
                },
                {
                    "name": "source",
                    "dataType": ["text"],
                    "description": "Source of the document",
                    "indexFilterable": True,
                },
                {
                    "name": "metadata",
                    "dataType": ["object"],
                    "description": "Additional metadata as JSON object",
                },
                {
                    "name": "created_at",
                    "dataType": ["date"],
                    "description": "Document creation timestamp",
                },
                {
                    "name": "updated_at",
                    "dataType": ["date"],
                    "description": "Last update timestamp",
                },
            ],
            "vectorIndexConfig": {"distance": "cosine"},
        }

    @staticmethod
    def validate_document(doc: WeaviateDocument) -> bool:
        """Validate document before insertion"""
        if not doc.content or len(doc.content.strip()) == 0:
            return False

        if doc.language and doc.language not in [
            "fr",
            "en",
            "es",
            "de",
            "it",
            "pt",
            "pl",
            "nl",
            "id",
            "hi",
            "zh",
            "th",
        ]:
            return False

        return True


# Export public API
__all__ = ["WeaviateDocument", "WeaviateQueryResult", "WeaviateSchema"]
