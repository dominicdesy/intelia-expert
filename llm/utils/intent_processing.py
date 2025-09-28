# -*- coding: utf-8 -*-
"""
utils/intent_processing.py - Module de traitement d'intentions et validation
Extrait de utilities.py pour modularisation
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict

from utils.data_classes import ValidationReport, ProcessingResult

logger = logging.getLogger(__name__)

# ============================================================================
# VALIDATION D'INTENTIONS - CORRECTION CRITIQUE: FONCTION MANQUANTE
# ============================================================================


def validate_intent_result(intent_result) -> bool:
    """
    Valide qu'un résultat d'intention est conforme aux attentes

    Args:
        intent_result: Résultat d'une classification d'intention

    Returns:
        bool: True si valide, False sinon
    """
    if intent_result is None:
        return False

    # Validation basique de la structure
    try:
        # Vérifier attributs requis
        required_attrs = ["intent_type", "confidence", "detected_entities"]

        for attr in required_attrs:
            if not hasattr(intent_result, attr):
                logger.debug(f"Attribut manquant dans intent_result: {attr}")
                return False

        # Validation de la confiance
        if not (0.0 <= intent_result.confidence <= 1.0):
            logger.debug(f"Confiance invalide: {intent_result.confidence}")
            return False

        # Validation du type d'intention
        if intent_result.intent_type is None:
            logger.debug("Type d'intention null")
            return False

        # Validation des entités (doit être une liste)
        if not isinstance(intent_result.detected_entities, list):
            logger.debug("detected_entities n'est pas une liste")
            return False

        return True

    except Exception as e:
        logger.debug(f"Erreur validation intent_result: {e}")
        return False


# ============================================================================
# 🔧 NOUVELLE FONCTION: build_where_filter avec support variable d'environnement
# ============================================================================


def build_where_filter(intent_result) -> Dict:
    """
    Construire where filter par entités avec support désactivation via variable d'environnement

    NOUVEAU: Supporte la variable d'environnement DISABLE_WHERE_FILTER=true pour désactiver
    complètement le filtrage WHERE, utile pour diagnostiquer les problèmes de récupération.
    CORRECTION: Utilise validate_intent_result pour une validation améliorée.
    """

    # 🔧 NOUVEAU: Vérifier variable d'environnement pour désactiver le filtre
    disable_where_filter = os.getenv("DISABLE_WHERE_FILTER", "false").lower() in [
        "true",
        "1",
        "yes",
        "on",
    ]

    if disable_where_filter:
        logger.debug(
            "WHERE filter désactivé par variable d'environnement DISABLE_WHERE_FILTER"
        )
        return None

    # CORRECTION: Validation intent_result améliorée
    if not intent_result:
        return None

    # Utiliser validate_intent_result pour vérifier la structure
    if not validate_intent_result(intent_result):
        logger.debug("Intent result invalide pour build_where_filter")
        return None

    entities = intent_result.detected_entities
    where_conditions = []

    # Logique existante inchangée
    if "line" in entities:
        where_conditions.append(
            {
                "path": ["geneticLine"],
                "operator": "Like",
                "valueText": f"*{entities['line']}*",
            }
        )

    if "species" in entities:
        where_conditions.append(
            {
                "path": ["species"],
                "operator": "Like",
                "valueText": f"*{entities['species']}*",
            }
        )

    if "phase" in entities:
        where_conditions.append(
            {
                "path": ["phase"],
                "operator": "Like",
                "valueText": f"*{entities['phase']}*",
            }
        )

    if "age_days" in entities:
        age_days = entities["age_days"]
        if isinstance(age_days, (int, float)):
            if age_days <= 7:
                age_band = "0-7j"
            elif age_days <= 21:
                age_band = "8-21j"
            elif age_days <= 35:
                age_band = "22-35j"
            else:
                age_band = "36j+"

            where_conditions.append(
                {"path": ["age_band"], "operator": "Equal", "valueText": age_band}
            )

    if not where_conditions:
        return None

    if len(where_conditions) == 1:
        return where_conditions[0]
    else:
        return {"operator": "And", "operands": where_conditions}


# ============================================================================
# FACTORY ET PROCESSUS D'INTENTION
# ============================================================================


class IntentProcessorFactory:
    """Factory robuste pour créer des processeurs d'intentions"""

    @staticmethod
    def create_processor(
        intents_file_path: Optional[str] = None, validate_on_creation: bool = True
    ):
        try:
            from processing.intent_processor import IntentProcessor
        except ImportError as e:
            raise RuntimeError(f"Module intent_processor non disponible: {e}")

        if intents_file_path is None:
            base_dir = Path(__file__).parent.resolve()
            intents_file_path = base_dir.parent / "config" / "intents.json"

        processor = IntentProcessor(str(intents_file_path))
        if validate_on_creation:
            validation_result = processor.validate_current_config()
            if not validation_result.is_valid:
                raise ValueError(f"Configuration invalide: {validation_result.errors}")

        return processor


def create_intent_processor(intents_file_path: Optional[str] = None):
    """Factory principale pour créer un processeur d'intentions"""
    return IntentProcessorFactory.create_processor(
        intents_file_path, validate_on_creation=True
    )


def process_query_with_intents(
    processor, query: str, explain_score: Optional[float] = None, timeout: float = 5.0
) -> ProcessingResult:
    """Traite une requête avec le processeur d'intentions"""
    start_time = time.time()

    if not processor:
        return ProcessingResult(
            success=False, error_message="Processeur non fourni", processing_time=0.0
        )

    if not query or not query.strip():
        return ProcessingResult(
            success=False, error_message="Requête vide ou invalide", processing_time=0.0
        )

    try:
        result = processor.process_query(query.strip(), explain_score)
        processing_time = time.time() - start_time

        if not result:
            return ProcessingResult(
                success=False,
                error_message="Aucun résultat retourné par le processeur",
                processing_time=processing_time,
            )

        return ProcessingResult(
            success=True,
            result=result,
            processing_time=processing_time,
            metadata={
                "query_length": len(query),
                "entities_detected": len(result.detected_entities),
                "intent_type": (
                    result.intent_type.value
                    if hasattr(result.intent_type, "value")
                    else str(result.intent_type)
                ),
                "confidence_level": (
                    "high"
                    if result.confidence > 0.8
                    else "medium" if result.confidence > 0.5 else "low"
                ),
            },
        )

    except Exception as e:
        logger.error(f"Erreur traitement requête '{query[:50]}...': {e}")
        return ProcessingResult(
            success=False,
            error_message=f"Erreur de traitement: {str(e)}",
            processing_time=time.time() - start_time,
            metadata={"exception_type": type(e).__name__},
        )


def validate_intents_config(
    config_path: str, strict_mode: bool = True
) -> ValidationReport:
    """Valide rigoureusement un fichier de configuration intents.json"""
    errors = []
    warnings = []
    recommendations = []
    stats = {}

    try:
        config_file = Path(config_path)
        if not config_file.exists():
            return ValidationReport(
                is_valid=False,
                errors=[f"Fichier non trouvé: {config_path}"],
                warnings=[],
                stats={},
                recommendations=["Vérifiez le chemin du fichier de configuration"],
            )

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Validation basique
        required_sections = ["aliases", "intents", "universal_slots"]
        for section in required_sections:
            if section not in config:
                errors.append(f"Section manquante: {section}")
            elif not isinstance(config[section], dict):
                errors.append(f"Section {section} doit être un dictionnaire")

        stats.update(
            {
                "file_size_bytes": config_file.stat().st_size,
                "validation_timestamp": time.time(),
                "strict_mode": strict_mode,
            }
        )

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats,
            recommendations=recommendations,
        )

    except Exception as e:
        return ValidationReport(
            is_valid=False,
            errors=[f"Erreur validation inattendue: {e}"],
            warnings=[],
            stats={},
            recommendations=["Contactez le support technique"],
        )
