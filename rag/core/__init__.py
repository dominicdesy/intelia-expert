# -*- coding: utf-8 -*-
"""
rag/core/__init__.py - Module central pour le traitement RAG avicole
Version 1.0 - Pipeline principal de traitement et validation JSON
"""

# Imports du processeur principal
from .json_processor import (
    JSONProcessor,
    get_json_processor,
    process_single_json,
    process_json_batch,
    validate_and_enrich_json,
)

# Imports des modèles nécessaires
from ..models.json_models import ProcessingResult
from ..models.enums import GeneticLine


async def quick_process(json_data: dict, config: dict = None) -> ProcessingResult:
    """Traitement rapide d'un document JSON avec configuration optionnelle"""

    processor = get_json_processor()

    # Appliquer la configuration temporaire si fournie
    if config:
        original_config = processor.config.copy()
        processor.update_config(config)

        try:
            result = await processor.process_json_document(json_data)
            return result
        finally:
            processor.config = original_config
    else:
        return await processor.process_json_document(json_data)


async def validate_only(json_data: dict) -> dict:
    """Validation pure sans extraction ni enrichissement"""

    # Configuration pour validation seule
    validation_config = {
        "auto_enrichment_enabled": False,
        "extraction_enabled": False,
        "validation_strict": True,
    }

    result = await quick_process(json_data, validation_config)

    return {
        "valid": result.success,
        "errors": result.errors,
        "warnings": result.warnings,
        "processing_time_ms": result.processing_time_ms,
        "document_info": {
            "title": result.document.title,
            "tables_count": len(result.document.tables),
            "figures_count": len(result.document.figures),
            "content_length": len(result.document.text),
        },
    }


async def enrich_only(json_data: dict) -> dict:
    """Enrichissement sans extraction"""

    # Configuration pour enrichissement seul
    enrichment_config = {
        "auto_enrichment_enabled": True,
        "extraction_enabled": False,
        "validation_strict": False,
    }

    result = await quick_process(json_data, enrichment_config)

    return {
        "success": result.success,
        "enriched_document": result.document.to_dict(),
        "enrichments_applied": result.enrichments_applied,
        "quality_score": result.document.metadata.quality_score,
        "auto_detections": {
            "genetic_line": {
                "value": result.document.metadata.genetic_line.value,
                "auto_detected": result.document.metadata.auto_detected_genetic_line,
            },
            "document_type": {
                "value": result.document.metadata.document_type.value,
                "auto_detected": result.document.metadata.auto_detected_document_type,
            },
            "language": {
                "value": result.document.metadata.language,
                "auto_detected": result.document.metadata.auto_detected_language,
            },
        },
    }


async def extract_only(json_data: dict, genetic_line: str = None) -> dict:
    """Extraction pure avec validation minimale"""

    from ..extractors import extract_from_json_data, auto_extract_from_json_data

    try:
        if genetic_line:
            genetic_line_enum = GeneticLine(genetic_line)
            records = extract_from_json_data(json_data, genetic_line_enum)
            used_genetic_line = genetic_line
            auto_detected = False
        else:
            result = auto_extract_from_json_data(json_data)
            records = result["records"]
            used_genetic_line = result["document_info"]["genetic_line"]
            auto_detected = result["document_info"]["auto_detected"]

        return {
            "success": True,
            "records_count": len(records),
            "records": [record.to_dict() for record in records],
            "genetic_line": used_genetic_line,
            "auto_detected": auto_detected,
            "extraction_summary": {
                "metrics_found": list(set(r.metric_type.value for r in records)),
                "age_range": (
                    [min(r.age_days for r in records), max(r.age_days for r in records)]
                    if records
                    else []
                ),
                "avg_confidence": (
                    sum(r.extraction_confidence for r in records) / len(records)
                    if records
                    else 0
                ),
            },
        }

    except Exception as e:
        return {"success": False, "error": str(e), "records_count": 0, "records": []}


async def full_pipeline(
    json_data: dict, genetic_line: str = None, config: dict = None
) -> dict:
    """Pipeline complet: validation + enrichissement + extraction"""

    # Configuration par défaut pour pipeline complet
    default_config = {
        "auto_enrichment_enabled": True,
        "validation_strict": True,
        "extraction_enabled": True,
        "min_confidence_threshold": 0.3,
    }

    if config:
        default_config.update(config)

    result = await quick_process(json_data, default_config)

    # Extraction supplémentaire si lignée spécifiée
    additional_records = []
    if genetic_line and result.success:
        try:
            from ..extractors import extract_from_json_data

            genetic_line_enum = GeneticLine(genetic_line)
            additional_records = extract_from_json_data(json_data, genetic_line_enum)
        except Exception:
            pass  # Ignorer les erreurs d'extraction supplémentaire

    return {
        "success": result.success,
        "processing_result": result.to_dict(),
        "pipeline_summary": {
            "validation": {
                "passed": result.success,
                "errors_count": len(result.errors),
                "warnings_count": len(result.warnings),
            },
            "enrichment": {
                "applied": len(result.enrichments_applied),
                "genetic_line_detected": result.document.metadata.auto_detected_genetic_line,
                "document_type_detected": result.document.metadata.auto_detected_document_type,
                "quality_score": result.document.metadata.quality_score,
            },
            "extraction": {
                "records_found": result.performance_records_found,
                "tables_processed": result.tables_processed,
                "tables_with_data": result.tables_with_data,
                "additional_records": len(additional_records),
            },
        },
        "recommendations": await _generate_processing_recommendations(result),
    }


async def _generate_processing_recommendations(result: ProcessingResult) -> list[str]:
    """Génère des recommandations basées sur le résultat de traitement"""

    recommendations = []

    # Recommandations basées sur la qualité
    if result.document.metadata.quality_score < 0.5:
        recommendations.append(
            "Améliorer la qualité des données source (métadonnées, structure)"
        )

    # Recommandations basées sur l'extraction
    if result.tables_processed > 0 and result.tables_with_data == 0:
        recommendations.append(
            "Vérifier la structure des tableaux et les en-têtes de colonnes"
        )

    if result.performance_records_found == 0 and result.tables_with_data > 0:
        recommendations.append(
            "Ajuster les seuils de confiance ou vérifier les patterns d'extraction"
        )

    # Recommandations basées sur les erreurs
    if result.errors:
        if any("validation" in error.lower() for error in result.errors):
            recommendations.append(
                "Corriger les erreurs de validation avant traitement"
            )

        if any("genetic" in error.lower() for error in result.errors):
            recommendations.append(
                "Spécifier explicitement la lignée génétique dans les métadonnées"
            )

    # Recommandations d'optimisation
    if result.processing_time_ms > 5000:  # Plus de 5 secondes
        recommendations.append(
            "Optimiser la taille du document ou diviser en lots plus petits"
        )

    if len(result.enrichments_applied) == 0:
        recommendations.append(
            "Activer l'enrichissement automatique pour améliorer la détection"
        )

    return recommendations


def get_processor_capabilities() -> dict:
    """Retourne les capacités du processeur JSON"""

    processor = get_json_processor()

    return {
        "version": "1.0.0",
        "capabilities": [
            "Validation JSON stricte avec contraintes métier",
            "Enrichissement automatique multi-niveau",
            "Extraction de données de performance par lignée",
            "Traitement par lots parallélisé",
            "Génération de recommandations intelligentes",
            "Calcul de scores de qualité",
            "Gestion d'erreurs et récupération gracieuse",
        ],
        "supported_formats": [
            "Documents JSON avec structure libre",
            "Tableaux avec en-têtes variables",
            "Métadonnées optionnelles ou automatiques",
            "Figures et contenus multimédia",
        ],
        "processing_modes": [
            "Validation seule",
            "Enrichissement seul",
            "Extraction seule",
            "Pipeline complet",
        ],
        "current_config": processor.config,
        "current_stats": processor.get_stats(),
    }


def get_processing_pipeline_info() -> dict:
    """Retourne des informations sur le pipeline de traitement"""

    return {
        "pipeline_stages": {
            "1_validation": {
                "description": "Validation de structure JSON et contraintes métier",
                "functions": ["validate_json_structure", "business_rules_check"],
                "configurable": True,
            },
            "2_conversion": {
                "description": "Conversion en modèles de données internes",
                "functions": [
                    "JSONDocument creation",
                    "hash generation",
                    "metadata setup",
                ],
                "configurable": False,
            },
            "3_enrichment": {
                "description": "Enrichissement automatique des données",
                "functions": [
                    "genetic_line_detection",
                    "document_type_detection",
                    "language_detection",
                    "quality_scoring",
                ],
                "configurable": True,
            },
            "4_extraction": {
                "description": "Extraction de données de performance via extracteurs",
                "functions": ["extractor_selection", "data_extraction", "validation"],
                "configurable": True,
            },
            "5_finalization": {
                "description": "Finalisation et génération du résultat",
                "functions": ["statistics_update", "result_compilation"],
                "configurable": False,
            },
        },
        "error_handling": {
            "validation_errors": "Collectés et reportés, traitement peut continuer",
            "conversion_errors": "Arrêt du traitement, erreur critique",
            "enrichment_errors": "Logged, enrichissement partiel possible",
            "extraction_errors": "Par extracteur, n'affecte pas les autres",
            "timeout_handling": "Configuration max_processing_time_seconds",
        },
        "parallel_processing": {
            "batch_processing": "Traitement parallèle par groupes configurables",
            "async_operations": "Toutes les opérations I/O sont asynchrones",
            "resource_management": "Limitation automatique selon batch_size",
        },
    }


async def run_processor_diagnostics() -> dict:
    """Exécute des diagnostics complets du processeur"""

    processor = get_json_processor()

    # Test avec document d'exemple
    from ..models import create_sample_json_document

    sample_doc = create_sample_json_document()
    sample_data = sample_doc.to_dict()

    diagnostics = {
        "timestamp": processor.stats.get("last_run", "never"),
        "processor_health": "healthy",
        "issues": [],
    }

    try:
        # Test de validation
        validation_result = await validate_only(sample_data)
        diagnostics["validation_test"] = {
            "status": "pass" if validation_result["valid"] else "fail",
            "time_ms": validation_result["processing_time_ms"],
        }

        # Test d'enrichissement
        enrichment_result = await enrich_only(sample_data)
        diagnostics["enrichment_test"] = {
            "status": "pass" if enrichment_result["success"] else "fail",
            "enrichments_count": len(enrichment_result["enrichments_applied"]),
        }

        # Test d'extraction
        extraction_result = await extract_only(sample_data)
        diagnostics["extraction_test"] = {
            "status": "pass" if extraction_result["success"] else "fail",
            "records_extracted": extraction_result["records_count"],
        }

        # Test pipeline complet
        pipeline_result = await full_pipeline(sample_data)
        diagnostics["full_pipeline_test"] = {
            "status": "pass" if pipeline_result["success"] else "fail",
            "total_time_ms": pipeline_result["processing_result"]["processing_time_ms"],
        }

    except Exception as e:
        diagnostics["processor_health"] = "degraded"
        diagnostics["issues"].append(f"Test diagnostic failed: {str(e)}")

    # Statistiques du processeur
    diagnostics["processor_stats"] = processor.get_stats()

    # Recommandations de maintenance
    stats = processor.get_stats()
    if stats.get("documents_failed", 0) > stats.get("documents_successful", 1):
        diagnostics["issues"].append("Taux d'échec élevé - Vérifier la configuration")

    if stats.get("avg_processing_time", 0) > 10:
        diagnostics["issues"].append(
            "Temps de traitement élevé - Optimisation recommandée"
        )

    return diagnostics


__all__ = [
    # Processeur principal
    "JSONProcessor",
    "get_json_processor",
    "process_single_json",
    "process_json_batch",
    "validate_and_enrich_json",
    # Fonctions de traitement spécialisées
    "quick_process",
    "validate_only",
    "enrich_only",
    "extract_only",
    "full_pipeline",
    # Informations et diagnostics
    "get_processor_capabilities",
    "get_processing_pipeline_info",
    "run_processor_diagnostics",
]
