# -*- coding: utf-8 -*-
"""
rag/extractors/base_extractor.py - Extracteur de base pour les données avicoles
Version 1.1 - CORRIGÉ: Imports robustes pour compatibilité production
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import hashlib

# CORRECTION MAJEURE: Gestion robuste des imports avec fallbacks
try:
    # Tentative d'import relatif (quand utilisé comme package)
    from ..models.enums import GeneticLine, MetricType, Sex
    from ..models.json_models import JSONDocument, JSONTable
    from ..models.extraction_models import (
        PerformanceRecord,
        ExtractionSession,
        parse_numeric_value,
        detect_metric_from_header,
        detect_age_from_context,
        detect_sex_from_context,
        detect_phase_from_age_and_genetic_line,
    )
    IMPORTS_MODE = "relative"
except ImportError:
    try:
        # Fallback: Import absolu (quand testé directement)
        from models.enums import GeneticLine, MetricType, Sex
        from models.json_models import JSONDocument, JSONTable
        from models.extraction_models import (
            PerformanceRecord,
            ExtractionSession,
            parse_numeric_value,
            detect_metric_from_header,
            detect_age_from_context,
            detect_sex_from_context,
            detect_phase_from_age_and_genetic_line,
        )
        IMPORTS_MODE = "absolute"
    except ImportError:
        # Fallback final: Définitions minimales pour tests
        from enum import Enum
        from dataclasses import dataclass
        from typing import Optional
        from datetime import datetime
        
        class GeneticLine(Enum):
            ROSS_308 = "ross308"
            ROSS_708 = "ross708"
            UNKNOWN = "unknown"
            
        class MetricType(Enum):
            WEIGHT_G = "weight_g"
            WEIGHT_KG = "weight_kg"
            FCR = "fcr"
            FEED_INTAKE_G = "feed_intake_g"
            MORTALITY_RATE = "mortality_rate"
            LIVABILITY = "livability"
            DAILY_GAIN = "daily_gain"
            
        class Sex(Enum):
            MALE = "male"
            FEMALE = "female"
            MIXED = "mixed"
            
        @dataclass
        class JSONDocument:
            title: str = ""
            text: str = ""
            content_hash: str = ""
            metadata: Optional[object] = None
            
            @classmethod
            def from_dict(cls, data: dict):
                return cls(
                    title=data.get("title", ""),
                    text=data.get("text", ""),
                    content_hash=str(hash(str(data))),
                    metadata=type('obj', (object,), {'genetic_line': GeneticLine.UNKNOWN})()
                )
        
        @dataclass        
        class JSONTable:
            headers: List[str]
            rows: List[List[str]]
            context: str = ""
            is_valid: bool = True
            has_performance_data: bool = False
            detected_metrics: List[MetricType] = None
            extraction_confidence: float = 0.0
            
        @dataclass
        class PerformanceRecord:
            source_document_id: str = ""
            genetic_line: GeneticLine = GeneticLine.UNKNOWN
            age_days: int = 0
            sex: Sex = Sex.MIXED
            phase: str = "unknown"
            metric_type: MetricType = MetricType.WEIGHT_G
            value_original: float = 0.0
            unit_original: str = ""
            table_context: str = ""
            column_header: str = ""
            row_context: str = ""
            extraction_confidence: float = 1.0
            value_canonical: float = 0.0
            unit_canonical: str = ""
            validation_passed: bool = True
            
            def normalize_unit(self):
                self.value_canonical = self.value_original
                self.unit_canonical = self.unit_original
                
            @property
            def is_plausible(self):
                return self.value_canonical > 0
        
        @dataclass
        class ExtractionSession:
            session_id: str
            extractor_type: str
            confidence_threshold: float
            
        # Fonctions utilitaires minimales
        def parse_numeric_value(text: str):
            import re
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                return float(match.group(1)), "unknown"
            return 0.0, "unknown"
            
        def detect_metric_from_header(header: str):
            header = header.lower()
            if "weight" in header or "poids" in header:
                return MetricType.WEIGHT_G
            elif "fcr" in header or "conversion" in header:
                return MetricType.FCR
            return None
            
        def detect_age_from_context(context: str, headers: str = ""):
            import re
            text = f"{context} {headers}"
            match = re.search(r'(\d+)\s*(?:day|jour|j|d)', text)
            if match:
                return int(match.group(1))
            return 0
            
        def detect_sex_from_context(context: str, headers: str = ""):
            text = f"{context} {headers}".lower()
            if "male" in text or "mâle" in text:
                return Sex.MALE
            elif "female" in text or "femelle" in text:
                return Sex.FEMALE
            return Sex.MIXED
            
        def detect_phase_from_age_and_genetic_line(age: int, genetic_line):
            if age <= 10:
                return "starter"
            elif age <= 25:
                return "grower"
            elif age <= 42:
                return "finisher"
            return "unknown"
        
        IMPORTS_MODE = "fallback"


class BaseExtractor(ABC):
    """Extracteur de base pour les données de performance avicoles"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # Configuration par défaut
        self.confidence_threshold = 0.5
        self.min_age_days = 0
        self.max_age_days = 500
        self.validation_enabled = True

        # Patterns communs à tous les extracteurs
        self.common_patterns = {
            "age_patterns": [
                r"(\d+)\s*(?:day|jour|día|tag|d|j)\b",
                r"week\s*(\d+)",
                r"(\d+)\s*(?:week|sem|wk|w)\b",
            ],
            "weight_patterns": [
                r"(?:live\s*weight|body\s*weight|weight|poids|bw|lw)",
                r"(?:peso|gewicht|masse)",
            ],
            "fcr_patterns": [
                r"(?:fcr|feed\s*conversion|conversion|ic|indice)",
                r"(?:feed\s*conv|f:g|feed:gain)",
            ],
            "mortality_patterns": [
                r"(?:mortality|mortalité|mort|death|dead)",
                r"(?:mortalidad|muerte|tot)",
            ],
        }

        # Statistiques d'extraction
        self.extraction_stats = {
            "documents_processed": 0,
            "tables_processed": 0,
            "records_extracted": 0,
            "records_validated": 0,
            "errors": 0,
        }

    @abstractmethod
    def get_supported_genetic_lines(self) -> List[GeneticLine]:
        """Retourne les lignées génétiques supportées par cet extracteur"""
        pass

    @abstractmethod
    def extract_performance_data(self, json_document) -> List[PerformanceRecord]:
        """Extrait les données de performance depuis un document JSON"""
        pass

    def extract_from_json_data(self, json_data: Dict[str, Any]) -> List[PerformanceRecord]:
        """Point d'entrée principal pour l'extraction depuis des données JSON brutes"""

        # Conversion en JSONDocument
        if hasattr(JSONDocument, 'from_dict'):
            json_doc = JSONDocument.from_dict(json_data)
        else:
            # Fallback pour les imports minimaux
            json_doc = JSONDocument(
                title=json_data.get("title", ""),
                text=json_data.get("text", ""),
                content_hash=str(hash(str(json_data)))
            )

        # Validation préliminaire
        if not self._is_compatible_document(json_doc):
            self.logger.warning(
                f"Document incompatible avec l'extracteur {self.__class__.__name__}"
            )
            return []

        # Extraction
        self.extraction_stats["documents_processed"] += 1
        return self.extract_performance_data(json_doc)

    def _is_compatible_document(self, json_doc) -> bool:
        """Vérifie si le document est compatible avec cet extracteur"""

        # Vérification lignée génétique
        if hasattr(json_doc, 'metadata') and hasattr(json_doc.metadata, 'genetic_line'):
            if json_doc.metadata.genetic_line != GeneticLine.UNKNOWN:
                return json_doc.metadata.genetic_line in self.get_supported_genetic_lines()

        # Si lignée inconnue, tenter détection depuis le contenu
        detected_line = self._detect_genetic_line_from_content(
            getattr(json_doc, 'title', ''), getattr(json_doc, 'text', '')
        )
        return detected_line in self.get_supported_genetic_lines()

    def _detect_genetic_line_from_content(self, title: str, text: str) -> GeneticLine:
        """Détecte la lignée génétique depuis le contenu"""
        
        content = f"{title} {text}".lower()
        
        # Patterns de base pour les lignées courantes
        patterns = {
            GeneticLine.ROSS_308: ["ross 308", "ross-308", "ross308"],
            GeneticLine.ROSS_708: ["ross 708", "ross-708", "ross708"],
        }
        
        for genetic_line, line_patterns in patterns.items():
            if any(pattern in content for pattern in line_patterns):
                return genetic_line

        return GeneticLine.UNKNOWN

    def log_extraction_progress(self, message: str, level: str = "info") -> None:
        """Log avec formatage standardisé"""

        prefix = f"[{self.__class__.__name__}]"
        formatted_message = f"{prefix} {message}"

        if level == "debug":
            self.logger.debug(formatted_message)
        elif level == "warning":
            self.logger.warning(formatted_message)
        elif level == "error":
            self.logger.error(formatted_message)
        else:
            self.logger.info(formatted_message)

    def get_extraction_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des statistiques d'extraction"""

        stats = self.extraction_stats.copy()

        # Calculs dérivés
        if stats["records_extracted"] > 0:
            stats["validation_rate"] = (
                stats["records_validated"] / stats["records_extracted"]
            )
        else:
            stats["validation_rate"] = 0.0

        if stats["tables_processed"] > 0:
            stats["avg_records_per_table"] = (
                stats["records_extracted"] / stats["tables_processed"]
            )
        else:
            stats["avg_records_per_table"] = 0.0

        stats["extractor_type"] = self.__class__.__name__
        stats["supported_genetic_lines"] = [
            gl.value for gl in self.get_supported_genetic_lines()
        ]
        stats["imports_mode"] = IMPORTS_MODE

        return stats