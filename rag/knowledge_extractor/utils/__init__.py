"""
Utilitaires pour le système d'extraction
Statistiques, logging, et helpers divers
"""

from .statistics import ExtractionStatistics

__all__ = [
    "ExtractionStatistics",
]

# Constantes utiles
DEFAULT_OUTPUT_DIR = "extracted_knowledge"
DEFAULT_LOG_LEVEL = "INFO"
