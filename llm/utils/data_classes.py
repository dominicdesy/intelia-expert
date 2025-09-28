# -*- coding: utf-8 -*-
"""
utils/data_classes.py - Classes de données et utilitaires de sérialisation
Extrait de utilities.py pour modularisation
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

# ============================================================================
# CLASSES DE DONNÉES - VERSION CORRIGÉE AVEC SÉRIALISATION JSON
# ============================================================================


@dataclass
class ValidationReport:
    """Rapport de validation détaillé - CORRIGÉ pour sérialisation JSON"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, Any]
    recommendations: List[str]

    def to_dict(self) -> dict:
        """Conversion en dictionnaire pour sérialisation JSON"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": self.stats,
            "recommendations": self.recommendations,
        }

    def __hash__(self):
        """Rendre hashable pour utilisation comme clé de cache"""
        return hash(
            (
                self.is_valid,
                tuple(self.errors),
                tuple(self.warnings),
                tuple(self.recommendations),
                # Ne pas inclure stats car peut contenir des types non-hashable
            )
        )


@dataclass
class ProcessingResult:
    """Résultat de traitement d'une requête - CORRIGÉ pour sérialisation JSON"""

    success: bool
    result: Optional[Any] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        """Conversion en dictionnaire pour sérialisation JSON"""
        return {
            "success": self.success,
            "result": safe_serialize_for_json(self.result),
            "error_message": self.error_message,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
        }

    def __hash__(self):
        """Rendre hashable pour utilisation comme clé de cache"""
        return hash(
            (
                self.success,
                self.error_message,
                self.processing_time,
                # Ne pas inclure result et metadata car peuvent contenir des types non-hashable
            )
        )


# ============================================================================
# FONCTION DE SÉRIALISATION CORRIGÉE - SUPPORT DATACLASSES
# ============================================================================


def safe_serialize_for_json(obj: Any) -> Any:
    """Convertit récursivement les objets en types JSON-safe"""
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, Enum):
        return obj.value

    # NOUVEAU: Gestion spéciale pour LanguageDetectionResult
    elif (
        hasattr(obj, "language")
        and hasattr(obj, "confidence")
        and hasattr(obj, "source")
    ):
        return {
            "language": obj.language,
            "confidence": float(obj.confidence),
            "source": obj.source,
            "processing_time_ms": getattr(obj, "processing_time_ms", 0),
        }

    elif isinstance(obj, dict):
        return {k: safe_serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [safe_serialize_for_json(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return safe_serialize_for_json(obj.__dict__)
    else:
        return str(obj)
