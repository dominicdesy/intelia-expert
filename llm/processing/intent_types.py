# -*- coding: utf-8 -*-
"""
intent_types.py - Types et structures de données pour le processeur d'intentions
"""

from typing import Dict, List, Any
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
    semantic_fallback_candidates: List[str] = field(
        default_factory=list
    )  # Nouveau: fallback sémantique


# CORRECTION CRITIQUE: Ajout de la classe manquante IntentValidationResult
@dataclass
class IntentValidationResult:
    """Résultat de validation d'intention pour les générateurs"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    validation_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        """True si des erreurs sont présentes"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """True si des avertissements sont présents"""
        return len(self.warnings) > 0

    @property
    def summary(self) -> str:
        """Résumé textuel du résultat de validation"""
        if self.is_valid:
            return f"Validation réussie ({len(self.warnings)} avertissements)"
        else:
            return f"Validation échouée ({len(self.errors)} erreurs, {len(self.warnings)} avertissements)"
