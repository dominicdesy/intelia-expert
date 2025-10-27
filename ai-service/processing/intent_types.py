# -*- coding: utf-8 -*-
"""
intent_types.py - Types et structures de données pour le processeur d'intentions
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
intent_types.py - Types et structures de données pour le processeur d'intentions
"""

from utils.types import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class IntentType(Enum):
    """Types d'intentions métier - Étendu"""

    METRIC_QUERY = "metric_query"
    ENVIRONMENT_SETTING = "environment_setting"
    PROTOCOL_QUERY = "protocol_query"
    DIAGNOSIS_TRIAGE = "diagnosis_triage"
    ECONOMICS_COST = "economics_cost"
    GENERAL_POULTRY = "general_poultry"
    OUT_OF_DOMAIN = "out_of_domain"


@dataclass
class IntentResult:
    """Résultat de classification d'intention - Version améliorée avec métriques intégration"""

    intent_type: IntentType
    confidence: float
    detected_entities: Dict[str, str]
    expanded_query: str
    metadata: Dict[str, Any]
    processing_time: float = 0.0
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    vocabulary_coverage: Dict[str, Any] = field(default_factory=dict)
    expansion_quality: Dict[str, Any] = field(default_factory=dict)
    cache_key_normalized: str = ""  # Nouveau: clé normalisée pour Redis
    semantic_fallback_candidates: List[str] = field(
        default_factory=list
    )  # Nouveau: fallback sémantique


@dataclass
class IntentValidationResult:
    """Résultat de validation d'intention pour les générateurs"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    validation_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        """True si des erreurs sont présentes"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """True si des avertissements sont présents"""
        return len(self.warnings) > 0

    @property
    def summary(self) -> str:
        """Résumé textuel du résultat de validation"""
        if self.is_valid:
            return f"Validation réussie ({len(self.warnings)} avertissements)"
        else:
            return f"Validation échouée ({len(self.errors)} erreurs, {len(self.warnings)} avertissements)"


# CORRECTION CRITIQUE: Ajout de la classe ConfigurationValidator avec méthode de classe
@dataclass
class ConfigurationValidator:
    """Validateur de configuration pour les générateurs et processeurs d'intention"""

    strict_mode: bool = False
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    error_tolerance: float = 0.1
    warning_threshold: float = 0.3

    def __post_init__(self):
        """Initialisation post-création"""
        if not self.validation_rules:
            self.validation_rules = {
                "intent_confidence_min": 0.1,
                "intent_confidence_max": 1.0,
                "entity_coverage_min": 0.0,
                "expansion_quality_min": 0.5,
                "processing_time_max": 5.0,
                "required_fields": ["intent_type", "confidence", "expanded_query"],
                "optional_fields": ["detected_entities", "metadata"],
            }

    def validate_intent_result(
        self, intent_result: IntentResult
    ) -> IntentValidationResult:
        """Valide un résultat d'intention"""
        errors = []
        warnings = []
        stats = {}

        try:
            # Validation des champs requis
            for field in self.validation_rules.get("required_fields", []):
                if not hasattr(intent_result, field):
                    errors.append(f"Champ requis manquant: {field}")
                elif getattr(intent_result, field) is None:
                    errors.append(f"Champ requis vide: {field}")

            # Validation de la confiance
            confidence = intent_result.confidence
            min_conf = self.validation_rules.get("intent_confidence_min", 0.1)
            max_conf = self.validation_rules.get("intent_confidence_max", 1.0)

            if confidence < min_conf:
                if self.strict_mode:
                    errors.append(f"Confiance trop faible: {confidence} < {min_conf}")
                else:
                    warnings.append(f"Confiance faible: {confidence}")
            elif confidence > max_conf:
                errors.append(f"Confiance invalide: {confidence} > {max_conf}")

            # Validation du temps de traitement
            max_time = self.validation_rules.get("processing_time_max", 5.0)
            if intent_result.processing_time > max_time:
                warnings.append(
                    f"Temps de traitement élevé: {intent_result.processing_time}s"
                )

            # Validation de la qualité d'expansion
            expansion_quality = intent_result.expansion_quality
            if expansion_quality:
                quality_score = expansion_quality.get("quality_score", 0.0)
                min_quality = self.validation_rules.get("expansion_quality_min", 0.5)
                if quality_score < min_quality:
                    warnings.append(f"Qualité d'expansion faible: {quality_score}")

            # Statistiques
            stats = {
                "confidence_score": confidence,
                "processing_time": intent_result.processing_time,
                "entities_count": len(intent_result.detected_entities),
                "expansion_applied": intent_result.expanded_query
                != intent_result.metadata.get("original_query", ""),
                "metadata_fields": len(intent_result.metadata),
            }

            # Déterminer la validité
            is_valid = len(errors) == 0
            if self.strict_mode:
                is_valid = is_valid and len(warnings) == 0

            return IntentValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                stats=stats,
                validation_metadata={
                    "validator_mode": "strict" if self.strict_mode else "lenient",
                    "rules_applied": list(self.validation_rules.keys()),
                    "validation_timestamp": (
                        time.time() if "time" in globals() else None
                    ),
                },
            )

        except Exception as e:
            return IntentValidationResult(
                is_valid=False,
                errors=[f"Erreur validation: {str(e)}"],
                warnings=[],
                stats={},
                validation_metadata={"error": str(e)},
            )

    @classmethod  # ✅ CORRECTION: Méthode de classe au lieu de méthode d'instance
    def validate_configuration(cls, config: Dict[str, Any]) -> IntentValidationResult:
        """Valide une configuration générale"""
        errors = []
        warnings = []
        stats = {}

        try:
            # Validation des clés requises
            required_keys = ["intent_processor", "embedder", "retriever"]
            for key in required_keys:
                if key not in config:
                    errors.append(f"Configuration manquante: {key}")
                elif config[key] is None:
                    warnings.append(f"Configuration vide: {key}")

            # Validation des seuils
            thresholds = config.get("thresholds", {})
            for threshold_name, value in thresholds.items():
                if not isinstance(value, (int, float)):
                    errors.append(
                        f"Seuil invalide {threshold_name}: doit être numérique"
                    )
                elif value < 0 or value > 1:
                    warnings.append(f"Seuil inhabituel {threshold_name}: {value}")

            stats = {
                "config_keys": len(config),
                "thresholds_count": len(thresholds),
                "required_keys_present": sum(1 for k in required_keys if k in config),
            }

            return IntentValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                stats=stats,
                validation_metadata={
                    "config_type": "general",
                    "validator_version": "1.0",
                },
            )

        except Exception as e:
            return IntentValidationResult(
                is_valid=False,
                errors=[f"Erreur validation configuration: {str(e)}"],
                warnings=[],
                stats={},
                validation_metadata={"error": str(e)},
            )


# Factory function pour créer un validateur
def create_configuration_validator(
    strict_mode: bool = False, custom_rules: Optional[Dict[str, Any]] = None
) -> ConfigurationValidator:
    """Factory pour créer un validateur de configuration"""
    validator = ConfigurationValidator(strict_mode=strict_mode)
    if custom_rules:
        validator.validation_rules.update(custom_rules)
    return validator


# Classes manquantes référencées dans __init__.py
@dataclass
class ValidationResult:
    """Alias pour IntentValidationResult pour compatibilité"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_intent_validation(
        cls, intent_validation: IntentValidationResult
    ) -> "ValidationResult":
        """Convertit IntentValidationResult en ValidationResult"""
        return cls(
            is_valid=intent_validation.is_valid,
            errors=intent_validation.errors,
            warnings=intent_validation.warnings,
            stats=intent_validation.stats,
        )


class IntentCategory(Enum):
    """Catégories d'intentions pour classification"""

    PERFORMANCE = "performance"
    HEALTH = "health"
    NUTRITION = "nutrition"
    ENVIRONMENT = "environment"
    GENETICS = "genetics"
    ECONOMICS = "economics"
    GENERAL = "general"


class EntityType(Enum):
    """Types d'entités reconnues"""

    GENETIC_LINE = "genetic_line"
    SPECIES = "species"
    AGE = "age"
    WEIGHT = "weight"
    METRIC = "metric"
    PHASE = "phase"
    LOCATION = "location"
    DATE = "date"
    NUMBER = "number"


# Configuration par défaut des intentions
DEFAULT_INTENTS_CONFIG = {
    "metric_query": {
        "category": IntentCategory.PERFORMANCE,
        "keywords": ["fcr", "poids", "gain", "croissance", "performance"],
        "entities": [EntityType.METRIC, EntityType.AGE, EntityType.GENETIC_LINE],
        "confidence_threshold": 0.7,
    },
    "environment_setting": {
        "category": IntentCategory.ENVIRONMENT,
        "keywords": ["température", "ventilation", "éclairage", "densité"],
        "entities": [EntityType.AGE, EntityType.PHASE],
        "confidence_threshold": 0.6,
    },
    "protocol_query": {
        "category": IntentCategory.HEALTH,
        "keywords": ["protocole", "vaccination", "traitement", "prophylaxie"],
        "entities": [EntityType.AGE, EntityType.SPECIES],
        "confidence_threshold": 0.8,
    },
    "diagnosis_triage": {
        "category": IntentCategory.HEALTH,
        "keywords": ["symptômes", "diagnostic", "maladie", "problème"],
        "entities": [EntityType.AGE, EntityType.SPECIES],
        "confidence_threshold": 0.75,
    },
    "economics_cost": {
        "category": IntentCategory.ECONOMICS,
        "keywords": ["coût", "prix", "rentabilité", "marge", "économique"],
        "entities": [EntityType.METRIC, EntityType.AGE],
        "confidence_threshold": 0.6,
    },
    "general_poultry": {
        "category": IntentCategory.GENERAL,
        "keywords": ["aviculture", "élevage", "poulet", "ponte"],
        "entities": [EntityType.SPECIES, EntityType.GENETIC_LINE],
        "confidence_threshold": 0.5,
    },
}

# Import time si nécessaire pour les timestamps
try:
    import time
except ImportError:
    pass
