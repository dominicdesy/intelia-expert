# -*- coding: utf-8 -*-
"""
models.py - Data models for response generation
"""

from dataclasses import dataclass
from utils.types import List
from utils.mixins import SerializableMixin


@dataclass
class ContextEnrichment(SerializableMixin):
    """Enrichissement du contexte basé sur les entités détectées"""

    entity_context: str
    metric_focus: str
    temporal_context: str
    species_focus: str
    performance_indicators: List[str]
    confidence_boosters: List[str]


__all__ = ["ContextEnrichment"]
