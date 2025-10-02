#!/usr/bin/env python3
"""
Modèles de données pour le convertisseur Excel vers PostgreSQL
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class TaxonomyInfo:
    """Information taxonomique extraite du fichier"""

    company: str
    breed: str
    strain: str
    species: str  # layer/broiler
    housing_system: Optional[str] = None
    feather_color: Optional[str] = None
    sex: Optional[str] = None
    data_type: Optional[str] = None  # performance/pharmaceutical/nutrition/carcass


@dataclass
class MetricData:
    """Données de métrique extraites"""

    sheet_name: str
    category: str
    metric_key: str
    metric_name: str
    value_text: Optional[str] = None
    value_numeric: Optional[float] = None
    unit: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    metadata: Optional[Dict] = None
