"""
Gestionnaire de statistiques d'extraction centralisé
"""

from datetime import datetime
from typing import Dict, Any


class ExtractionStatistics:
    """Gestionnaire centralisé des statistiques d'extraction"""

    def __init__(self):
        self.stats = {
            "documents_processed": 0,
            "chunks_created": 0,
            "chunks_injected": 0,
            "validation_failures": 0,
            "corrections_applied": 0,
            "errors": 0,
            "start_time": datetime.now(),
        }

    def increment_documents(self):
        """Incrémente le compteur de documents traités"""
        self.stats["documents_processed"] += 1

    def add_chunks_created(self, count: int):
        """Ajoute au compteur de chunks créés"""
        self.stats["chunks_created"] += count

    def add_chunks_injected(self, count: int):
        """Ajoute au compteur de chunks injectés"""
        self.stats["chunks_injected"] += count

    def increment_validation_failures(self):
        """Incrémente le compteur d'échecs de validation"""
        self.stats["validation_failures"] += 1

    def increment_corrections(self):
        """Incrémente le compteur de corrections appliquées"""
        self.stats["corrections_applied"] += 1

    def increment_errors(self):
        """Incrémente le compteur d'erreurs"""
        self.stats["errors"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de base"""
        return self.stats.copy()

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques détaillées avec calculs"""
        stats = self.stats.copy()

        # Calculs dérivés
        if stats["chunks_created"] > 0:
            stats["injection_rate"] = stats["chunks_injected"] / stats["chunks_created"]
        else:
            stats["injection_rate"] = 0.0

        if stats["documents_processed"] > 0:
            stats["avg_chunks_per_document"] = (
                stats["chunks_created"] / stats["documents_processed"]
            )
        else:
            stats["avg_chunks_per_document"] = 0.0

        # Temps d'exécution
        stats["execution_time_seconds"] = (
            datetime.now() - stats["start_time"]
        ).total_seconds()

        return stats

    def reset(self):
        """Remet à zéro toutes les statistiques"""
        self.__init__()
