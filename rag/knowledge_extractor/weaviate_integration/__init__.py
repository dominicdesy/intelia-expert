"""
Module d'intégration Weaviate avec validation et ingestion corrigées
Résout les erreurs de récupération de chunks lors de la validation
"""

from .ingester import WeaviateIngester
from .validator import ContentValidator

__all__ = [
    "WeaviateIngester",
    "ContentValidator",
]

# Configuration par défaut
DEFAULT_COLLECTION_NAME = "InteliaExpertKnowledge"
DEFAULT_CONFORMITY_THRESHOLD = 0.95
