# -*- coding: utf-8 -*-
"""
rag/__init__.py - Module principal RAG pour l'expertise avicole
Version 1.0 - Système d'extraction et traitement de données JSON avicoles
"""

from __future__ import annotations
import logging

# Version du module RAG
__version__ = "1.0.0"

# Imports principaux pour faciliter l'usage
from .core.json_processor import (
    JSONProcessor,
    get_json_processor,
    process_single_json,
    process_json_batch,
    validate_and_enrich_json,
)

from .extractors.extractor_factory import (
    ExtractorFactory,
    get_extractor_factory,
    extract_from_json_data,
    auto_extract_from_json_data,
)

from .extractors.base_extractor import BaseExtractor
from .extractors.ross_extractor import RossExtractor

# Modèles principaux
from .models.enums import (
    GeneticLine,
    MetricType,
    Sex,
    Phase,
    DocumentType,
    ExtractionStatus,
    ConfidenceLevel,
)

from .models.json_models import (
    JSONDocument,
    JSONMetadata,
    JSONTable,
    JSONFigure,
    ProcessingResult,
)

from .models.extraction_models import PerformanceRecord, ExtractionSession


def get_version() -> str:
    """Retourne la version du module RAG"""
    return __version__


def get_supported_genetic_lines() -> list[str]:
    """Retourne la liste des lignées génétiques supportées"""
    factory = get_extractor_factory()
    return [gl.value for gl in factory.get_supported_genetic_lines()]


def get_rag_info() -> dict:
    """Retourne les informations sur le système RAG"""
    factory = get_extractor_factory()
    processor = get_json_processor()

    return {
        "version": __version__,
        "description": "Système RAG pour l'expertise avicole",
        "capabilities": [
            "Validation JSON stricte",
            "Enrichissement automatique",
            "Extraction de données de performance",
            "Support multi-lignées génétiques",
            "Traitement par lots",
            "Validation biologique",
        ],
        "supported_genetic_lines": get_supported_genetic_lines(),
        "available_extractors": factory.get_available_extractors(),
        "factory_stats": factory.get_usage_stats(),
        "processor_stats": processor.get_stats(),
    }


def validate_rag_installation() -> dict:
    """Valide que le système RAG est correctement installé"""

    validation_result = {"valid": True, "errors": [], "warnings": [], "components": {}}

    try:
        # Test du processeur JSON
        get_json_processor()
        validation_result["components"]["json_processor"] = "OK"
    except Exception as e:
        validation_result["valid"] = False
        validation_result["errors"].append(f"JSONProcessor: {e}")
        validation_result["components"]["json_processor"] = "ERREUR"

    try:
        # Test du factory d'extracteurs
        factory = get_extractor_factory()
        validation_result["components"]["extractor_factory"] = "OK"
    except Exception as e:
        validation_result["valid"] = False
        validation_result["errors"].append(f"ExtractorFactory: {e}")
        validation_result["components"]["extractor_factory"] = "ERREUR"

    try:
        # Test de création d'extracteur Ross
        factory = get_extractor_factory()
        factory.create_extractor(GeneticLine.ROSS_308)
        validation_result["components"]["ross_extractor"] = "OK"
    except Exception as e:
        validation_result["valid"] = False
        validation_result["errors"].append(f"RossExtractor: {e}")
        validation_result["components"]["ross_extractor"] = "ERREUR"

    try:
        # Test des modèles de données
        JSONDocument(title="Test", text="Contenu test")
        validation_result["components"]["data_models"] = "OK"
    except Exception as e:
        validation_result["valid"] = False
        validation_result["errors"].append(f"DataModels: {e}")
        validation_result["components"]["data_models"] = "ERREUR"

    # Vérifications des dépendances
    missing_deps = []

    try:
        import importlib.util

        # Test des modules critiques
        required_modules = [
            "hashlib",
            "logging",
            "asyncio",
            "re",
            "datetime",
            "typing",
            "dataclasses",
            "enum",
        ]

        for module_name in required_modules:
            if importlib.util.find_spec(module_name) is None:
                missing_deps.append(f"Module manquant: {module_name}")

    except ImportError as e:
        missing_deps.append(str(e))

    if missing_deps:
        validation_result["warnings"].extend(missing_deps)

    return validation_result


# Configuration par défaut
DEFAULT_CONFIG = {
    "auto_enrichment_enabled": True,
    "validation_strict": True,
    "extraction_enabled": True,
    "min_confidence_threshold": 0.3,
    "max_processing_time_seconds": 300,
    "batch_size": 10,
    "cache_enabled": True,
    "logging_level": "INFO",
}


def configure_rag(config: dict) -> None:
    """Configure le système RAG avec les paramètres fournis"""

    processor = get_json_processor()
    processor.update_config(config)

    # Configuration du logging si spécifié
    if "logging_level" in config:
        import logging

        logging.getLogger("rag").setLevel(getattr(logging, config["logging_level"]))


def reset_rag_stats() -> None:
    """Remet à zéro toutes les statistiques RAG"""

    processor = get_json_processor()
    processor.reset_stats()

    factory = get_extractor_factory()
    factory.clear_cache()


# Fonctions utilitaires d'usage rapide


async def quick_extract(json_data: dict, genetic_line: str = None) -> dict:
    """Extraction rapide avec résultat simplifié"""

    try:
        if genetic_line:
            genetic_line_enum = GeneticLine(genetic_line)
            records = extract_from_json_data(json_data, genetic_line_enum)
        else:
            result = auto_extract_from_json_data(json_data)
            records = result["records"]

        return {
            "success": True,
            "records_count": len(records),
            "records": [record.to_dict() for record in records],
            "genetic_line": genetic_line or "auto_detected",
        }

    except Exception as e:
        return {"success": False, "error": str(e), "records_count": 0, "records": []}


async def quick_validate(json_data: dict) -> dict:
    """Validation rapide avec enrichissement"""

    try:
        document = await validate_and_enrich_json(json_data)

        return {
            "valid": True,
            "enriched_data": document.to_dict(),
            "genetic_line": document.metadata.genetic_line.value,
            "document_type": document.metadata.document_type.value,
            "quality_score": document.metadata.quality_score,
            "auto_enrichments": [
                f"genetic_line:{document.metadata.auto_detected_genetic_line}",
                f"document_type:{document.metadata.auto_detected_document_type}",
                f"language:{document.metadata.auto_detected_language}",
            ],
        }

    except Exception as e:
        return {"valid": False, "error": str(e), "enriched_data": None}


# Exports principaux
__all__ = [
    # Version et info
    "__version__",
    "get_version",
    "get_rag_info",
    "get_supported_genetic_lines",
    "validate_rag_installation",
    # Configuration
    "DEFAULT_CONFIG",
    "configure_rag",
    "reset_rag_stats",
    # Processeur principal
    "JSONProcessor",
    "get_json_processor",
    "process_single_json",
    "process_json_batch",
    "validate_and_enrich_json",
    # Factory d'extracteurs
    "ExtractorFactory",
    "get_extractor_factory",
    "extract_from_json_data",
    "auto_extract_from_json_data",
    # Extracteurs
    "BaseExtractor",
    "RossExtractor",
    # Modèles de données
    "GeneticLine",
    "MetricType",
    "Sex",
    "Phase",
    "DocumentType",
    "ExtractionStatus",
    "ConfidenceLevel",
    "JSONDocument",
    "JSONMetadata",
    "JSONTable",
    "JSONFigure",
    "ProcessingResult",
    "PerformanceRecord",
    "ExtractionSession",
    # Fonctions utilitaires
    "quick_extract",
    "quick_validate",
]


# Message d'information au chargement
logger = logging.getLogger(__name__)
logger.info(f"Module RAG v{__version__} chargé - Système d'expertise avicole prêt")
