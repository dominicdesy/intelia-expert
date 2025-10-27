# -*- coding: utf-8 -*-
"""
utils/data_classes.py - Classes de données et utilitaires de sérialisation
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
utils/data_classes.py - Classes de données et utilitaires de sérialisation
Extrait de utilities.py pour modularisation
REFACTORED: Utilise utils/serialization.py pour éviter duplication
"""

from dataclasses import dataclass
from utils.types import Dict, List, Optional, Any

# Import centralized serialization utility
from utils.serialization import safe_serialize
from utils.mixins import SerializableMixin

# Backward compatibility alias
safe_serialize_for_json = safe_serialize

# ============================================================================
# CLASSES DE DONNÉES - VERSION CORRIGÉE AVEC SÉRIALISATION JSON
# ============================================================================


@dataclass
class ValidationReport(SerializableMixin):
    """Rapport de validation détaillé - CORRIGÉ pour sérialisation JSON"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, Any]
    recommendations: List[str]

    # to_dict() now inherited from SerializableMixin (removed 9 lines)

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
# FONCTION DE SÉRIALISATION - MIGRÉ VERS utils/serialization.py
# ============================================================================
# La fonction safe_serialize_for_json() est maintenant importée depuis utils/serialization.py
# pour éviter la duplication de code (voir ligne 13 ci-dessus)
