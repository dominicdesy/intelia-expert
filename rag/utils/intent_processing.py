# -*- coding: utf-8 -*-
"""
utils/intent_processing.py - Module de traitement d'intentions et validation
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
utils/intent_processing.py - Module de traitement d'intentions et validation
Extrait de utilities.py pour modularisation
"""

import os
import json
import time
import logging
from pathlib import Path
from utils.types import Optional, Dict

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
# 🔧 NOUVELLE FONCTION: build_where_filter v2.0 avec nouveaux champs BD
# ============================================================================
# Mapping des entités vers les champs Weaviate:
# - breed → "breed" (TEXT, exact match prioritaire)
# - company → "company" (TEXT, partial match)
# - sex → "sex" (TEXT, exact match)
# - age_days → "age_min_days" + "age_max_days" (INT, range query)
# - species → "species" (TEXT, partial match)
# - unit_system → "unit_system" (TEXT, exact match)
# - data_type → "data_type" (TEXT, partial match)
#
# DEPRECATED: geneticLine, phase, age_band (remplacés par nouveaux champs)
# ============================================================================


def build_where_filter(intent_result) -> Dict:
    """
    Construire where filter par entités avec support des nouveaux champs v2.0

    VERSION 2.0 (2025-01-15):
    - ✅ Utilise les nouveaux champs: breed, sex, age_min_days, age_max_days, company, unit_system
    - ✅ Support filtrage par plage d'âge précise (BETWEEN age_min_days AND age_max_days)
    - ✅ Priorité aux champs structurés vs. champs legacy
    - ⚠️  DEPRECATED: geneticLine, phase, age_band (compatibilité maintenue)

    NOUVEAU: Supporte la variable d'environnement DISABLE_WHERE_FILTER=true pour désactiver
    complètement le filtrage WHERE, utile pour diagnostiquer les problèmes de récupération.

    Voir documentation complète: llm/docs/DATABASE_SCHEMA.md
    """

    # 🔧 Vérifier variable d'environnement pour désactiver le filtre
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

    # Validation intent_result
    if not intent_result:
        return None

    if not validate_intent_result(intent_result):
        logger.debug("Intent result invalide pour build_where_filter")
        return None

    entities = intent_result.detected_entities
    where_conditions = []

    # ============================================================================
    # NOUVEAUX CHAMPS v2.0 (PRIORITAIRES)
    # ============================================================================

    # 1. BREED - Filtrage exact sur la race (HAUTE PRIORITÉ)
    if "breed" in entities:
        breed_value = entities["breed"]
        logger.debug(f"Filtrage par breed: {breed_value}")
        where_conditions.append(
            {
                "path": ["breed"],
                "operator": "Equal",  # Exact match pour précision
                "valueText": breed_value,
            }
        )

    # 2. COMPANY - Filtrage partiel sur la compagnie
    if "company" in entities:
        company_value = entities["company"]
        logger.debug(f"Filtrage par company: {company_value}")
        where_conditions.append(
            {
                "path": ["company"],
                "operator": "Like",
                "valueText": f"*{company_value}*",
            }
        )

    # 3. SEX - Filtrage exact sur le sexe (HAUTE PRIORITÉ)
    if "sex" in entities:
        sex_value = entities["sex"]
        # Normalisation des valeurs
        sex_mapping = {
            "male": "male",
            "female": "female",
            "mixed": "as_hatched",
            "as_hatched": "as_hatched",
            "as-hatched": "as_hatched",
        }
        normalized_sex = sex_mapping.get(sex_value.lower(), sex_value)
        logger.debug(f"Filtrage par sex: {sex_value} → {normalized_sex}")
        where_conditions.append(
            {
                "path": ["sex"],
                "operator": "Equal",
                "valueText": normalized_sex,
            }
        )

    # 4. AGE_DAYS - Filtrage par plage d'âge précise (HAUTE PRIORITÉ)
    # Nouveau: Utilise age_min_days et age_max_days au lieu de age_band
    if "age_days" in entities:
        age_days = entities["age_days"]
        if isinstance(age_days, (int, float)):
            age_int = int(age_days)
            logger.debug(f"Filtrage par age: {age_int} jours")
            # Requête: documents dont la plage d'âge contient age_days
            # Condition: age_min_days <= age_days AND age_max_days >= age_days
            where_conditions.append(
                {
                    "operator": "And",
                    "operands": [
                        {
                            "path": ["age_min_days"],
                            "operator": "LessThanEqual",
                            "valueInt": age_int,
                        },
                        {
                            "path": ["age_max_days"],
                            "operator": "GreaterThanEqual",
                            "valueInt": age_int,
                        },
                    ],
                }
            )

    # 5. UNIT_SYSTEM - Filtrage par système d'unités (si spécifié)
    if "unit_system" in entities:
        unit_value = entities["unit_system"]
        logger.debug(f"Filtrage par unit_system: {unit_value}")
        where_conditions.append(
            {
                "path": ["unit_system"],
                "operator": "Equal",
                "valueText": unit_value,
            }
        )

    # ============================================================================
    # CHAMPS EXISTANTS (compatibilité maintenue)
    # ============================================================================

    # SPECIES - Toujours supporté
    if "species" in entities:
        species_value = entities["species"]
        logger.debug(f"Filtrage par species: {species_value}")
        where_conditions.append(
            {
                "path": ["species"],
                "operator": "Like",
                "valueText": f"*{species_value}*",
            }
        )

    # DATA_TYPE - Filtrage par type de document
    if "data_type" in entities:
        data_type_value = entities["data_type"]
        logger.debug(f"Filtrage par data_type: {data_type_value}")
        where_conditions.append(
            {
                "path": ["data_type"],
                "operator": "Like",
                "valueText": f"*{data_type_value}*",
            }
        )

    # ============================================================================
    # LEGACY FIELDS (DEPRECATED mais maintenus pour compatibilité)
    # ============================================================================

    # Legacy: geneticLine (remplacé par breed)
    if "line" in entities and "breed" not in entities:
        logger.warning(
            "⚠️  Utilisation de 'geneticLine' (deprecated). Utilisez 'breed' à la place."
        )
        where_conditions.append(
            {
                "path": ["geneticLine"],
                "operator": "Like",
                "valueText": f"*{entities['line']}*",
            }
        )

    # Legacy: phase (remplacé par age_min_days/age_max_days)
    if "phase" in entities and "age_days" not in entities:
        logger.warning(
            "⚠️  Utilisation de 'phase' (deprecated). Utilisez 'age_days' à la place."
        )
        where_conditions.append(
            {
                "path": ["phase"],
                "operator": "Like",
                "valueText": f"*{entities['phase']}*",
            }
        )

    # ============================================================================
    # Construction du filtre final
    # ============================================================================

    if not where_conditions:
        logger.debug("Aucun filtre construit (aucune entité pertinente)")
        return None

    if len(where_conditions) == 1:
        filter_result = where_conditions[0]
    else:
        filter_result = {"operator": "And", "operands": where_conditions}

    logger.info(f"✅ WHERE filter construit avec {len(where_conditions)} condition(s)")
    return filter_result


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
