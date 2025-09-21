# -*- coding: utf-8 -*-
"""
rag/extractors/__init__.py - Extracteurs de données pour le système RAG avicole
Version 1.0 - Classes d'extraction spécialisées par lignée génétique
"""

# Imports des extracteurs
from .base_extractor import BaseExtractor
from .ross_extractor import RossExtractor
from .extractor_factory import (
    ExtractorFactory,
    get_extractor_factory,
    extract_from_json_data,
    auto_extract_from_json_data,
)

# Imports des modèles nécessaires
from ..models.enums import GeneticLine, MetricType
from ..models.json_models import JSONDocument


def get_available_extractors() -> dict[str, type[BaseExtractor]]:
    """Retourne tous les extracteurs disponibles"""

    # Import dynamique pour éviter les dépendances circulaires
    from .extractor_factory import CobbExtractor, HubbardExtractor

    return {
        "RossExtractor": RossExtractor,
        "CobbExtractor": CobbExtractor,
        "HubbardExtractor": HubbardExtractor,
    }


def get_extractor_for_genetic_line(
    genetic_line: GeneticLine,
) -> type[BaseExtractor] | None:
    """Retourne la classe d'extracteur appropriée pour une lignée"""

    extractor_mapping = {
        GeneticLine.ROSS_308: RossExtractor,
        GeneticLine.ROSS_708: RossExtractor,
        # GeneticLine.COBB_500: CobbExtractor,  # À implémenter
        # GeneticLine.COBB_700: CobbExtractor,  # À implémenter
        # GeneticLine.HUBBARD_CLASSIC: HubbardExtractor,  # À implémenter
        # GeneticLine.HUBBARD_FLEX: HubbardExtractor,  # À implémenter
    }

    return extractor_mapping.get(genetic_line)


def create_extractor_for_genetic_line(
    genetic_line: GeneticLine,
) -> BaseExtractor | None:
    """Crée une instance d'extracteur pour une lignée"""

    extractor_class = get_extractor_for_genetic_line(genetic_line)
    if extractor_class:
        return extractor_class(genetic_line)
    return None


def list_supported_genetic_lines() -> list[GeneticLine]:
    """Liste toutes les lignées génétiques supportées par les extracteurs"""

    factory = get_extractor_factory()
    return factory.get_supported_genetic_lines()


def validate_extractor_compatibility(
    genetic_line: GeneticLine, document: JSONDocument
) -> dict:
    """Valide la compatibilité d'un extracteur avec un document"""

    factory = get_extractor_factory()
    return factory.validate_extractor_compatibility(genetic_line, document)


def get_extraction_recommendations(document: JSONDocument) -> dict:
    """Obtient des recommandations d'extraction pour un document"""

    factory = get_extractor_factory()
    return factory.get_extraction_recommendations(document)


async def quick_extract_with_auto_detection(json_data: dict) -> dict:
    """Extraction rapide avec auto-détection de lignée"""

    try:
        result = auto_extract_from_json_data(json_data)
        return {
            "success": True,
            "auto_detected": True,
            "genetic_line": result["document_info"]["genetic_line"],
            "records_count": result["extraction_info"]["records_count"],
            "records": [record.to_dict() for record in result["records"]],
            "recommendations": result["recommendations"],
        }
    except Exception as e:
        return {"success": False, "error": str(e), "auto_detected": False}


async def extract_with_specific_extractor(json_data: dict, genetic_line: str) -> dict:
    """Extraction avec un extracteur spécifique"""

    try:
        genetic_line_enum = GeneticLine(genetic_line)
        records = extract_from_json_data(json_data, genetic_line_enum)

        return {
            "success": True,
            "genetic_line": genetic_line,
            "records_count": len(records),
            "records": [record.to_dict() for record in records],
            "extractor_used": get_extractor_for_genetic_line(
                genetic_line_enum
            ).__name__,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "genetic_line": genetic_line}


def compare_extractors_performance(json_data: dict) -> dict:
    """Compare les performances de différents extracteurs sur le même document"""

    results = {}
    supported_lines = list_supported_genetic_lines()

    for genetic_line in supported_lines:
        try:
            records = extract_from_json_data(json_data, genetic_line)
            extractor_class = get_extractor_for_genetic_line(genetic_line)

            results[genetic_line.value] = {
                "success": True,
                "records_count": len(records),
                "extractor": extractor_class.__name__ if extractor_class else "Unknown",
                "avg_confidence": (
                    sum(r.extraction_confidence for r in records) / len(records)
                    if records
                    else 0
                ),
                "metrics_found": list(set(r.metric_type.value for r in records)),
            }
        except Exception as e:
            results[genetic_line.value] = {"success": False, "error": str(e)}

    # Déterminer le meilleur extracteur
    best_extractor = None
    best_score = 0

    for line, result in results.items():
        if result["success"]:
            # Score basé sur le nombre d'enregistrements et la confiance moyenne
            score = result["records_count"] * result["avg_confidence"]
            if score > best_score:
                best_score = score
                best_extractor = line

    return {
        "comparison": results,
        "best_extractor": best_extractor,
        "best_score": best_score,
    }


def get_extractor_statistics() -> dict:
    """Retourne les statistiques d'utilisation des extracteurs"""

    factory = get_extractor_factory()
    return {
        "factory_stats": factory.get_usage_stats(),
        "available_extractors": factory.get_available_extractors(),
        "supported_genetic_lines": [
            gl.value for gl in factory.get_supported_genetic_lines()
        ],
        "extractor_report": factory.generate_extractor_report(),
    }


def reset_extractor_statistics() -> None:
    """Remet à zéro les statistiques des extracteurs"""

    factory = get_extractor_factory()
    factory.clear_cache()

    # Reset des stats des extracteurs individuels
    for genetic_line in factory.get_supported_genetic_lines():
        try:
            extractor = factory.create_extractor(genetic_line, use_cache=False)
            extractor.reset_stats()
        except Exception:
            pass  # Ignorer les erreurs de reset


def create_custom_extraction_pattern(
    name: str,
    genetic_line: GeneticLine,
    metric_type: MetricType,
    header_patterns: list[str],
    context_patterns: list[str] = None,
) -> dict:
    """Crée un pattern d'extraction personnalisé"""

    from ..models.extraction_models import ExtractionPattern

    pattern = ExtractionPattern(
        name=name,
        genetic_line=genetic_line,
        metric_type=metric_type,
        header_patterns=header_patterns,
        context_patterns=context_patterns or [],
    )

    return {
        "pattern": pattern,
        "info": {
            "name": name,
            "genetic_line": genetic_line.value,
            "metric_type": metric_type.value,
            "header_patterns_count": len(header_patterns),
            "context_patterns_count": len(context_patterns or []),
        },
    }


def test_extractor_on_sample_data() -> dict:
    """Teste les extracteurs sur des données d'exemple"""

    from ..models import create_sample_json_document

    # Créer un document d'exemple
    sample_doc = create_sample_json_document()
    sample_data = sample_doc.to_dict()

    # Tester avec auto-détection
    auto_result = auto_extract_from_json_data(sample_data)

    # Tester avec extracteur spécifique
    ross_result = extract_from_json_data(sample_data, GeneticLine.ROSS_308)

    return {
        "sample_document": {
            "title": sample_doc.title,
            "genetic_line": sample_doc.metadata.genetic_line.value,
            "tables_count": len(sample_doc.tables),
            "total_data_points": sum(
                len(table.headers) * len(table.rows) for table in sample_doc.tables
            ),
        },
        "auto_detection_result": {
            "success": auto_result["extraction_info"]["success"],
            "records_count": auto_result["extraction_info"]["records_count"],
            "detected_line": auto_result["document_info"]["genetic_line"],
        },
        "ross_extractor_result": {
            "records_count": len(ross_result),
            "avg_confidence": (
                sum(r.extraction_confidence for r in ross_result) / len(ross_result)
                if ross_result
                else 0
            ),
            "metrics_extracted": list(set(r.metric_type.value for r in ross_result)),
        },
    }


def get_extractors_documentation() -> dict:
    """Retourne la documentation des extracteurs"""

    return {
        "overview": "Système d'extracteurs spécialisés pour données avicoles",
        "architecture": {
            "base_extractor": "Classe abstraite définissant l'interface commune",
            "specialized_extractors": "Extracteurs optimisés par lignée génétique",
            "factory_pattern": "Gestionnaire centralisé pour création et cache",
        },
        "available_extractors": {
            "RossExtractor": {
                "description": "Extracteur spécialisé pour lignées Ross 308/708",
                "status": "Complet et optimisé",
                "supported_lines": ["ross_308", "ross_708"],
                "features": [
                    "Validation biologique spécifique Ross",
                    "Patterns de détection optimisés",
                    "Gestion des variantes d'en-têtes",
                    "Calcul de confiance adaptatif",
                ],
            },
            "CobbExtractor": {
                "description": "Extracteur pour lignées Cobb 500/700",
                "status": "Structure créée, implémentation à compléter",
                "supported_lines": ["cobb_500", "cobb_700"],
            },
            "HubbardExtractor": {
                "description": "Extracteur pour lignées Hubbard",
                "status": "Structure créée, implémentation à compléter",
                "supported_lines": ["hubbard_classic", "hubbard_flex"],
            },
        },
        "usage_examples": {
            "auto_detection": "auto_extract_from_json_data(json_data)",
            "specific_extractor": "extract_from_json_data(json_data, GeneticLine.ROSS_308)",
            "factory_usage": "get_extractor_factory().extract_from_document(document)",
            "recommendations": "get_extraction_recommendations(document)",
        },
        "development_notes": {
            "adding_extractors": "Hériter de BaseExtractor et enregistrer dans le factory",
            "pattern_creation": "Utiliser ExtractionPattern pour définir des règles",
            "validation": "Implémenter _validate_record pour contrôles spécifiques",
            "testing": "Utiliser test_extractor_on_sample_data pour validation",
        },
    }


# Exports principaux
__all__ = [
    # Classes principales
    "BaseExtractor",
    "RossExtractor",
    "ExtractorFactory",
    # Factory et fonctions utilitaires
    "get_extractor_factory",
    "extract_from_json_data",
    "auto_extract_from_json_data",
    # Gestion des extracteurs
    "get_available_extractors",
    "get_extractor_for_genetic_line",
    "create_extractor_for_genetic_line",
    "list_supported_genetic_lines",
    # Validation et recommandations
    "validate_extractor_compatibility",
    "get_extraction_recommendations",
    # Fonctions d'extraction
    "quick_extract_with_auto_detection",
    "extract_with_specific_extractor",
    "compare_extractors_performance",
    # Statistiques et monitoring
    "get_extractor_statistics",
    "reset_extractor_statistics",
    # Utilitaires avancés
    "create_custom_extraction_pattern",
    "test_extractor_on_sample_data",
    "get_extractors_documentation",
]
