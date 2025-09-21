# -*- coding: utf-8 -*-
"""
rag/models/__init__.py - Modèles de données pour le système RAG avicole
Version 1.0 - Structures de données et énumérations
"""

# Imports des énumérations
from .enums import (
    GeneticLine,
    MetricType,
    Sex,
    Phase,
    DocumentType,
    ExtractionStatus,
    ConfidenceLevel,
    GENETIC_LINE_PATTERNS,
    METRIC_PATTERNS,
)

# Imports des modèles JSON
from .json_models import (
    JSONMetadata,
    JSONTable,
    JSONFigure,
    JSONDocument,
    ProcessingResult,
    validate_json_structure,
    detect_genetic_line_from_content,
    detect_document_type_from_content,
)

# Imports des modèles d'extraction
from .extraction_models import (
    PerformanceRecord,
    ExtractionSession,
    ExtractionPattern,
    parse_numeric_value,
    detect_metric_from_header,
    detect_age_from_context,
    detect_sex_from_context,
    detect_phase_from_age_and_genetic_line,
    ROSS_EXTRACTION_PATTERNS,
    COBB_EXTRACTION_PATTERNS,
)


def get_all_genetic_lines() -> list[GeneticLine]:
    """Retourne toutes les lignées génétiques disponibles"""
    return list(GeneticLine)


def get_all_metric_types() -> list[MetricType]:
    """Retourne tous les types de métriques disponibles"""
    return list(MetricType)


def get_broiler_genetic_lines() -> list[GeneticLine]:
    """Retourne uniquement les lignées de chair"""
    return [gl for gl in GeneticLine if gl.is_broiler]


def get_layer_genetic_lines() -> list[GeneticLine]:
    """Retourne uniquement les lignées pondeuses"""
    return [gl for gl in GeneticLine if gl.is_layer]


def get_metrics_by_category() -> dict[str, list[MetricType]]:
    """Retourne les métriques groupées par catégorie"""

    categories = {}
    for metric in MetricType:
        category = metric.category
        if category not in categories:
            categories[category] = []
        categories[category].append(metric)

    return categories


def create_sample_json_document() -> JSONDocument:
    """Crée un document JSON d'exemple pour les tests"""

    # Métadonnées d'exemple
    metadata = JSONMetadata(
        genetic_line=GeneticLine.ROSS_308,
        document_type=DocumentType.PERFORMANCE_GUIDE,
        language="fr",
        source="exemple",
        version="1.0",
    )

    # Tableau d'exemple
    sample_table = JSONTable(
        headers=["Âge (jours)", "Poids (g)", "FCR", "Mortalité (%)"],
        rows=[
            ["7", "180", "1.10", "0.5"],
            ["14", "460", "1.25", "1.2"],
            ["21", "845", "1.35", "2.1"],
            ["28", "1335", "1.45", "3.0"],
            ["35", "1895", "1.55", "3.8"],
        ],
        context="Données de performance Ross 308 - Mâles",
        title="Performance Standards Ross 308",
    )

    # Document d'exemple
    document = JSONDocument(
        title="Guide de Performance Ross 308",
        text="Ce document présente les objectifs de performance pour la lignée Ross 308. "
        "Les données incluent le poids vif, l'indice de consommation et la mortalité "
        "par tranche d'âge pour des conditions d'élevage standards.",
        metadata=metadata,
    )

    document.add_table(sample_table)

    return document


def create_sample_performance_record() -> PerformanceRecord:
    """Crée un enregistrement de performance d'exemple"""

    return PerformanceRecord(
        source_document_id="exemple_doc_001",
        genetic_line=GeneticLine.ROSS_308,
        age_days=21,
        sex=Sex.MALE,
        phase=Phase.GROWER,
        metric_type=MetricType.WEIGHT_G,
        value_canonical=845.0,
        unit_canonical="g",
        value_original=845.0,
        unit_original="g",
        table_context="Performance Standards Ross 308 - Mâles",
        column_header="Poids (g)",
        row_context="Row 3: Age 21j",
        extraction_confidence=0.95,
    )


def validate_genetic_line_compatibility(
    genetic_line: GeneticLine, metric_type: MetricType
) -> bool:
    """Valide la compatibilité entre une lignée et un type de métrique"""

    # Métriques pondeuses
    layer_metrics = {
        MetricType.EGG_PRODUCTION,
        MetricType.EGG_WEIGHT,
        MetricType.EGG_MASS,
        MetricType.FEED_PER_DOZEN,
    }

    # Métriques chair
    broiler_metrics = {
        MetricType.WEIGHT_G,
        MetricType.WEIGHT_KG,
        MetricType.WEIGHT_LB,
        MetricType.FCR,
        MetricType.DAILY_GAIN,
        MetricType.BREAST_YIELD,
        MetricType.CARCASS_YIELD,
    }

    # Métriques communes
    common_metrics = {
        MetricType.FEED_INTAKE_G,
        MetricType.FEED_INTAKE_KG,
        MetricType.MORTALITY_RATE,
        MetricType.LIVABILITY,
        MetricType.WATER_INTAKE,
    }

    if genetic_line.is_broiler:
        return metric_type in (broiler_metrics | common_metrics)
    elif genetic_line.is_layer:
        return metric_type in (layer_metrics | common_metrics)
    else:
        return metric_type in common_metrics


def get_metric_validation_range(
    metric_type: MetricType, genetic_line: GeneticLine, age_days: int
) -> tuple[float, float]:
    """Retourne la plage de valeurs valides pour une métrique"""

    if metric_type == MetricType.WEIGHT_G:
        if genetic_line.is_broiler:
            # Estimation basée sur l'âge pour broilers
            min_weight = max(30, age_days * 15)  # Croissance minimale
            max_weight = min(4000, age_days * 80)  # Croissance maximale
            return (min_weight, max_weight)
        else:
            return (30, 2500)  # Plage générale

    elif metric_type == MetricType.FCR:
        if age_days <= 7:
            return (0.8, 1.6)
        elif age_days <= 21:
            return (1.0, 1.8)
        elif age_days <= 35:
            return (1.2, 2.2)
        else:
            return (1.4, 2.8)

    elif metric_type == MetricType.MORTALITY_RATE:
        # Mortalité cumulative acceptable
        max_mortality = min(20, age_days * 0.2)  # Max 0.2% par jour
        return (0, max_mortality)

    elif metric_type == MetricType.EGG_PRODUCTION:
        return (0, 100)  # Pourcentage

    elif metric_type == MetricType.EGG_WEIGHT:
        return (45, 85)  # Grammes

    else:
        return (0, float("inf"))  # Plage générique


def create_extraction_session_example() -> ExtractionSession:
    """Crée une session d'extraction d'exemple"""

    session = ExtractionSession(
        session_id="exemple_session_001",
        extractor_type="RossExtractor",
        confidence_threshold=0.5,
    )

    # Ajouter quelques résultats d'exemple
    for i in range(3):
        record = create_sample_performance_record()
        record.age_days = 7 + (i * 7)  # 7, 14, 21 jours
        record.value_canonical = 180 + (i * 300)  # Progression de poids
        session.add_result(record)

    session.finalize()

    return session


def get_models_info() -> dict:
    """Retourne des informations sur les modèles disponibles"""

    return {
        "enums": {
            "genetic_lines": len(GeneticLine),
            "metric_types": len(MetricType),
            "sexes": len(Sex),
            "phases": len(Phase),
            "document_types": len(DocumentType),
            "extraction_statuses": len(ExtractionStatus),
            "confidence_levels": len(ConfidenceLevel),
        },
        "patterns": {
            "genetic_line_patterns": len(GENETIC_LINE_PATTERNS),
            "metric_patterns": len(METRIC_PATTERNS),
            "ross_extraction_patterns": len(ROSS_EXTRACTION_PATTERNS),
            "cobb_extraction_patterns": len(COBB_EXTRACTION_PATTERNS),
        },
        "models": {
            "json_document": "Structure principale pour documents JSON",
            "performance_record": "Enregistrement de performance extrait",
            "extraction_session": "Session de traitement par lots",
            "processing_result": "Résultat de traitement complet",
        },
        "utilities": {
            "validation_functions": [
                "validate_json_structure",
                "detect_genetic_line_from_content",
                "detect_document_type_from_content",
            ],
            "extraction_functions": [
                "parse_numeric_value",
                "detect_metric_from_header",
                "detect_age_from_context",
                "detect_sex_from_context",
            ],
        },
    }


# Exports principaux
__all__ = [
    # Énumérations
    "GeneticLine",
    "MetricType",
    "Sex",
    "Phase",
    "DocumentType",
    "ExtractionStatus",
    "ConfidenceLevel",
    "GENETIC_LINE_PATTERNS",
    "METRIC_PATTERNS",
    # Modèles JSON
    "JSONMetadata",
    "JSONTable",
    "JSONFigure",
    "JSONDocument",
    "ProcessingResult",
    "validate_json_structure",
    "detect_genetic_line_from_content",
    "detect_document_type_from_content",
    # Modèles d'extraction
    "PerformanceRecord",
    "ExtractionSession",
    "ExtractionPattern",
    "parse_numeric_value",
    "detect_metric_from_header",
    "detect_age_from_context",
    "detect_sex_from_context",
    "detect_phase_from_age_and_genetic_line",
    "ROSS_EXTRACTION_PATTERNS",
    "COBB_EXTRACTION_PATTERNS",
    # Fonctions utilitaires
    "get_all_genetic_lines",
    "get_all_metric_types",
    "get_broiler_genetic_lines",
    "get_layer_genetic_lines",
    "get_metrics_by_category",
    "validate_genetic_line_compatibility",
    "get_metric_validation_range",
    # Créateurs d'exemples
    "create_sample_json_document",
    "create_sample_performance_record",
    "create_extraction_session_example",
    # Informations
    "get_models_info",
]
