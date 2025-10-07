# -*- coding: utf-8 -*-
"""
rag_postgresql_models.py - Modèles de données pour PostgreSQL
"""

from dataclasses import dataclass
from enum import Enum
from utils.types import Optional


class QueryType(Enum):
    """Types de requêtes pour le routage intelligent"""

    KNOWLEDGE = "knowledge"
    METRICS = "metrics"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


@dataclass
class MetricResult:
    """Résultat d'une requête de métriques PostgreSQL"""

    company: str
    breed: str
    strain: str
    species: str
    metric_name: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    sheet_name: str = ""
    category: str = ""
    confidence: float = 1.0
    sex: Optional[str] = None
    housing_system: Optional[str] = None
    data_type: Optional[str] = None
    unit_system: Optional[str] = None  # metric/imperial/mixed

    def __post_init__(self):
        """Validation et nettoyage des données"""
        self.company = str(self.company) if self.company is not None else "Unknown"
        self.breed = str(self.breed) if self.breed is not None else "Unknown"
        self.strain = str(self.strain) if self.strain is not None else "Unknown"
        self.species = str(self.species) if self.species is not None else "Unknown"
        self.metric_name = (
            str(self.metric_name) if self.metric_name is not None else "Unknown"
        )
        self.sheet_name = str(self.sheet_name) if self.sheet_name is not None else ""
        self.category = str(self.category) if self.category is not None else ""

        # Normalisation du sexe
        if self.sex:
            self.sex = str(self.sex).lower()
            if self.sex in ["male", "mâle", "m", "masculin"]:
                self.sex = "male"
            elif self.sex in ["female", "femelle", "f", "féminin"]:
                self.sex = "female"
            elif self.sex in [
                "mixed",
                "mixte",
                "as_hatched",
                "as-hatched",
                "straight_run",
            ]:
                self.sex = "as_hatched"
            else:
                self.sex = "as_hatched"

        self.confidence = max(0.0, min(1.0, float(self.confidence)))
