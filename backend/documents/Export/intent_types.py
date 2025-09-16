# -*- coding: utf-8 -*-
"""
intent_types.py - Types et structures de données pour le processeur d'intentions
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

class IntentType(Enum):
    """Types d'intentions métier - Étendu"""
    METRIC_QUERY = "metric_query"
    ENVIRONMENT_SETTING = "environment_setting"
    PROTOCOL_QUERY = "protocol_query"
    DIAGNOSIS_TRIAGE = "diagnosis_triage"
    ECONOMICS_COST = "economics_cost"
    GENERAL_POULTRY = "general_poultry"
    OUT_OF_DOMAIN = "out_of_domain"

@dataclass
class IntentResult:
    """Résultat de classification d'intention - Version améliorée avec métriques intégration"""
    intent_type: IntentType
    confidence: float
    detected_entities: Dict[str, str]
    expanded_query: str
    metadata: Dict[str, Any]
    processing_time: float = 0.0
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    vocabulary_coverage: Dict[str, Any] = field(default_factory=dict)
    expansion_quality: Dict[str, Any] = field(default_factory=dict)
    cache_key_normalized: str = ""  # Nouveau: clé normalisée pour Redis
    semantic_fallback_candidates: List[str] = field(default_factory=list)  # Nouveau: fallback sémantique
