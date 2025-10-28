# -*- coding: utf-8 -*-
"""
models.py - Data models for guardrails system
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
models.py - Data models for guardrails system
"""

from dataclasses import dataclass
from enum import Enum
from utils.types import Dict, List, Any
from utils.mixins import SerializableMixin


class VerificationLevel(Enum):
    """Niveaux de vérification avec seuils adaptatifs"""

    MINIMAL = "minimal"  # Vérification basique
    STANDARD = "standard"  # Vérification normale
    STRICT = "strict"  # Vérification rigoureuse
    CRITICAL = "critical"  # Vérification maximale


@dataclass
class GuardrailResult(SerializableMixin):
    """Résultat de la vérification par guardrails"""

    is_valid: bool
    confidence: float
    violations: List[str]
    warnings: List[str]
    evidence_support: float
    hallucination_risk: float
    correction_suggestions: List[str]
    metadata: Dict[str, Any]
    processing_time: float = 0.0


__all__ = ["VerificationLevel", "GuardrailResult"]
