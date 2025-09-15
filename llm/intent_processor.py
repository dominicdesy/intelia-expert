# -*- coding: utf-8 -*-
"""
intent_processor.py - Processeur d'intentions robuste avec validation stricte
Version corrigée: Élimination des fallbacks silencieux, validation explicite des configurations
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Exception pour les erreurs de configuration"""
    pass

class IntentType(Enum):
    """Types d'intentions supportés"""
    METRIC_QUERY = "metric_query"
    ENVIRONMENT_SETTING = "environment_setting"
    PROTOCOL_QUERY = "protocol_query"
    DIAGNOSIS_TRIAGE = "diagnosis_triage"
    OUT_OF_DOMAIN = "out_of_domain"

@dataclass
class ValidationResult:
    """Résultat de validation avec détails"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, Any]

@dataclass
class IntentResult:
    """Résultat du traitement d'intention"""
    intent_type: IntentType
    confidence: float
    detected_entities: Dict[str, Any]
    expanded_query: str
    metadata: Dict[str, Any]
    confidence_breakdown: Dict[str, float]
    processing_time: float
    fallback_candidates: int = 0
    explain_score: Optional[float] = None

class ConfigurationValidator:
    """Validateur strict de configuration intents.json"""
    
    REQUIRED_SECTIONS = ["aliases", "intents", "universal_slots"]
    REQUIRED_ALIAS_CATEGORIES = ["line", "site_type", "bird_type", "phase"]
    REQUIRED_INTENT_FIELDS = ["description", "required", "metrics"]
    
    @classmethod
    def validate_configuration(cls, config: Dict[str, Any]) -> ValidationResult:
        """Validation stricte de la configuration"""
        errors = []
        warnings = []
        stats = {}
        
        try:
            # 1. Validation structure de base
            errors.extend(cls._validate_structure(config))
            
            # 2. Validation des aliases
            alias_errors, alias_warnings, alias_stats = cls._validate_aliases(config.get("aliases", {}))
            errors.extend(alias_errors)
            warnings.extend(alias_warnings)
            stats.update(alias_stats)
            
            # 3. Validation des intents
            intent_errors, intent_warnings, intent_stats = cls._validate_intents(config.get("intents", {}))
            errors.extend(intent_errors)
            warnings.extend(intent_warnings)
            stats.update(intent_stats)
            
            # 4. Validation des slots universels
            slot_errors, slot_stats = cls._validate_universal_slots(config.get("universal_slots", {}))
            errors.extend(slot_errors)
            stats.update(slot_stats)
            
            # 5. Validation de cohérence croisée
            coherence_errors = cls._validate_cross_references(config)
            errors.extend(coherence_errors)
            
        except Exception as e:
            errors.append(f"Erreur de validation inattendue: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats
        )
    
    @classmethod
    def _validate_structure(cls, config: Dict[str, Any]) -> List[str]:
        """Validation de la structure de base"""
        errors = []
        
        for section in cls.REQUIRED_SECTIONS:
            if section not in config:
                errors.append(f"Section manquante: '{section}'")
            elif not isinstance(config[section], dict):
                errors.append(f"Section '{section}' doit être un dictionnaire")
        
        return errors
    
    @classmethod
    def _validate_aliases(cls, aliases: Dict[str, Any]) -> tuple[List[str], List[str], Dict[str, Any]]:
        """Validation des aliases"""
        errors = []
        warnings = []
        stats = {}
        
        if not aliases:
            errors.append("Section aliases vide")
            return errors, warnings, stats
        
        # Vérification des catégories requises
        for category in cls.REQUIRED_ALIAS_CATEGORIES:
            if category not in aliases:
                errors.append(f"Catégorie alias manquante: '{category}'")
            elif not isinstance(aliases[category], dict):
                errors.append(f"Catégorie alias '{category}' doit être un dictionnaire")
            elif not aliases[category]:
                warnings.append(f"Catégorie alias '{category}' est vide")
        
        # Statistiques
        total_aliases = 0
        for category, category_aliases in aliases.items():
            if isinstance(category_aliases, dict):
                total_aliases += sum(len(alias_list) if isinstance(alias_list, list) else 1 
                                   for alias_list in category_aliases.values())
        
        stats["total_aliases"] = total_aliases
        stats["alias_categories_count"] = len(aliases)
        
        return errors, warnings, stats
    
    @classmethod
    def _validate_intents(cls, intents: Dict[str, Any]) -> tuple[List[str], List[str], Dict[str, Any]]:
        """Validation des intents"""
        errors = []
        warnings = []
        stats = {}
        
        if not intents:
            errors.append("Section intents vide")
            return errors, warnings, stats
        
        total_metrics = 0
        intent_count = len(intents)
        
        for intent_name, intent_config in intents.items():
            if not isinstance(intent_config, dict):
                errors.append(f"Intent '{intent_name}' doit être un dictionnaire")
                continue
            
            # Vérification des champs requis
            for field in cls.REQUIRED_INTENT_FIELDS:
                if field not in intent_config:
                    errors.append(f"Champ manquant dans intent '{intent_name}': '{field}'")
            
            # Validation des métriques
            metrics = intent_config.get("metrics", {})
            if not isinstance(metrics, dict):
                errors.append(f"Métriques de l'intent '{intent_name}' doivent être un dictionnaire")
            elif not metrics:
                warnings.append(f"Intent '{intent_name}' n'a pas de métriques définies")
            else:
                metric_errors = cls._validate_metrics(intent_name, metrics)
                errors.extend(metric_errors)
                total_metrics += len(metrics)
        
        stats["total_intents"] = intent_count
        stats["total_metrics"] = total_metrics
        stats["avg_metrics_per_intent"] = total_metrics / max(1, intent_count)
        
        return errors, warnings, stats
    
    @classmethod
    def _validate_metrics(cls, intent_name: str, metrics: Dict[str, Any]) -> List[str]:
        """Validation des métriques d'un intent"""
        errors = []
        
        for metric_name, metric_config in metrics.items():
            if not isinstance(metric_config, dict):
                errors.append(f"Métrique '{metric_name}' de l'intent '{intent_name}' doit être un dictionnaire")
                continue
            
            # Validation des unités
            if "unit" not in metric_config:
                errors.append(f"Unité manquante pour la métrique '{metric_name}' de l'intent '{intent_name}'")
            
            # Validation des contraintes
            if "requires_one_of" in metric_config:
                requires = metric_config["requires_one_of"]
                if not isinstance(requires, list) or not all(isinstance(r, list) for r in requires):
                    errors.append(f"Format 'requires_one_of' invalide pour '{metric_name}' dans '{intent_name}'")
        
        return errors
    
    @classmethod
    def _validate_universal_slots(cls, slots: Dict[str, Any]) -> tuple[List[str], Dict[str, Any]]:
        """Validation des slots universels"""
        errors = []
        stats = {}
        
        if not slots:
            errors.append("Section universal_slots vide")
            return errors, stats
        
        enum_slots = 0
        numeric_slots = 0
        
        for slot_name, slot_config in slots.items():
            if not isinstance(slot_config, dict):
                errors.append(f"Slot '{slot_name}' doit être un dictionnaire")
                continue
            
            # Classification des types de slots
            if "enum" in slot_config:
                enum_slots += 1
                if not isinstance(slot_config["enum"], list):
                    errors.append(f"Enum du slot '{slot_name}' doit être une liste")
            elif "type" in slot_config:
                if slot_config["type"] in ["int", "number"]:
                    numeric_slots += 1
        
        stats["total_slots"] = len(slots)
        stats["enum_slots"] = enum_slots
        stats["numeric_slots"] = numeric_slots
        
        return errors, stats
    
    @classmethod
    def _validate_cross_references(cls, config: Dict[str, Any]) -> List[str]:
        """Validation de cohérence entre sections"""
        errors = []
        
        # Vérifier que les références dans les intents correspondent aux aliases
        aliases = config.get("aliases", {})
        intents = config.get("intents", {})
        slots = config.get("universal_slots", {})
        
        # Vérifier que les slots référencés existent
        for intent_name, intent_config in intents.items():
            required_fields = intent_config.get("required", [])
            for field in required_fields:
                if field not in slots and field not in aliases:
                    errors.append(f"Champ requis '{field}' dans intent '{intent_name}' non défini dans slots ou aliases")
        
        return errors

class IntentProcessor:
    """Processeur d'intentions robuste avec validation stricte"""
    
    def __init__(self, intents_file_path: str):
        self.intents_file_path = intents_file_path
        self.intents_config = {}
        self.is_initialized = False
        self.initialization_error = None
        
        # Métriques de traitement
        self.processing_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "errors_count": 0,
            "avg_processing_time": 0.0,
            "last_reset": time.time()
        }
        
        # Initialisation avec validation stricte
        try:
            self._load_and_validate_config()
            self.is_initialized = True
            logger.info(f"IntentProcessor initialisé avec succès: {self._get_config_summary()}")
        except Exception as e:
            self.initialization_error = e
            logger.error(f"Échec d'initialisation IntentProcessor: {e}")
            raise ConfigurationError(f"Impossible d'initialiser IntentProcessor: {e}")
    
    def _load_and_validate_config(self):
        """Charge et valide la configuration de manière stricte"""
        
        # 1. Résolution du chemin
        config_path = self._resolve_config_path()
        
        # 2. Lecture du fichier
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            raise ConfigurationError(f"Fichier de configuration introuvable: {config_path}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Erreur JSON dans {config_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Erreur lecture {config_path}: {e}")
        
        # 3. Validation stricte
        validation_result = ConfigurationValidator.validate_configuration(config)
        
        if not validation_result.is_valid:
            error_msg = f"Configuration invalide:\n" + "\n".join(f"  - {error}" for error in validation_result.errors)
            raise ConfigurationError(error_msg)
        
        # 4. Logging des warnings
        if validation_result.warnings:
            for warning in validation_result.warnings:
                logger.warning(f"Configuration: {warning}")
        
        # 5. Stockage de la configuration validée
        self.intents_config = config
        self.validation_stats = validation_result.stats
        
        logger.info(f"Configuration validée: {validation_result.stats}")
    
    def _resolve_config_path(self) -> Path:
        """Résolution robuste du chemin de configuration"""
        
        if os.path.isabs(self.intents_file_path):
            config_path = Path(self.intents_file_path)
        else:
            # Chemin relatif - résolution à partir du fichier courant
            base_dir = Path(__file__).parent.resolve()
            config_path = base_dir / self.intents_file_path
        
        if not config_path.exists():
            # Tentative de résolution alternative
            alternative_paths = [
                Path.cwd() / self.intents_file_path,
                Path.cwd() / "config" / self.intents_file_path,
                Path(__file__).parent / "config" / self.intents_file_path
            ]
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    config_path = alt_path
                    logger.info(f"Configuration trouvée via chemin alternatif: {config_path}")
                    break
            else:
                raise ConfigurationError(
                    f"Fichier de configuration introuvable: {config_path}\n"
                    f"Chemins testés: {[str(p) for p in [config_path] + alternative_paths]}"
                )
        
        return config_path.resolve()
    
    def _get_config_summary(self) -> str:
        """Résumé de la configuration chargée"""
        stats = getattr(self, 'validation_stats', {})
        return (f"v{self.intents_config.get('version', 'unknown')} - "
                f"{stats.get('total_intents', 0)} intents, "
                f"{stats.get('total_metrics', 0)} métriques, "
                f"{stats.get('total_aliases', 0)} aliases")
    
    def process_query(self, query: str, explain_score: Optional[float] = None) -> IntentResult:
        """Traite une requête avec gestion d'erreurs robuste"""
        
        if not self.is_initialized:
            raise RuntimeError(f"IntentProcessor non initialisé: {self.initialization_error}")
        
        start_time = time.time()
        self.processing_stats["total_queries"] += 1
        
        try:
            # Traitement de la requête (implémentation simplifiée pour l'exemple)
            result = self._process_query_internal(query, explain_score)
            
            # Mise à jour des statistiques
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            
            self.processing_stats["successful_queries"] += 1
            self._update_avg_processing_time(processing_time)
            
            return result
            
        except Exception as e:
            self.processing_stats["errors_count"] += 1
            logger.error(f"Erreur traitement requête '{query}': {e}")
            
            # Retour d'un résultat d'erreur au lieu d'un fallback silencieux
            return IntentResult(
                intent_type=IntentType.OUT_OF_DOMAIN,
                confidence=0.0,
                detected_entities={},
                expanded_query=query,
                metadata={"error": str(e), "original_query": query},
                confidence_breakdown={"error": 1.0},
                processing_time=time.time() - start_time,
                explain_score=explain_score
            )
    
    def _process_query_internal(self, query: str, explain_score: Optional[float]) -> IntentResult:
        """Traitement interne de la requête (version simplifiée)"""
        
        # Implémentation simplifiée - à remplacer par la logique métier réelle
        detected_entities = {}
        confidence = 0.8
        intent_type = IntentType.METRIC_QUERY
        
        # Simulation de détection d'entités basée sur les aliases
        for category, aliases in self.intents_config.get("aliases", {}).items():
            for main_term, alias_list in aliases.items():
                if isinstance(alias_list, list):
                    all_terms = [main_term] + alias_list
                else:
                    all_terms = [main_term]
                
                for term in all_terms:
                    if term.lower() in query.lower():
                        detected_entities[category] = main_term
                        break
        
        # Calcul de confiance basé sur les entités détectées
        if detected_entities:
            confidence = min(0.95, 0.5 + len(detected_entities) * 0.15)
        else:
            confidence = 0.3
            intent_type = IntentType.OUT_OF_DOMAIN
        
        return IntentResult(
            intent_type=intent_type,
            confidence=confidence,
            detected_entities=detected_entities,
            expanded_query=query,  # À enrichir avec la logique d'expansion
            metadata={
                "config_version": self.intents_config.get("version", "unknown"),
                "entities_found": len(detected_entities)
            },
            confidence_breakdown={
                "entity_match": confidence,
                "domain_relevance": confidence * 0.9
            },
            processing_time=0.0,  # Sera mis à jour par le caller
            explain_score=explain_score
        )
    
    def _update_avg_processing_time(self, processing_time: float):
        """Met à jour le temps de traitement moyen"""
        current_avg = self.processing_stats["avg_processing_time"]
        total_queries = self.processing_stats["total_queries"]
        
        if total_queries == 1:
            self.processing_stats["avg_processing_time"] = processing_time
        else:
            # Moyenne mobile pondérée
            self.processing_stats["avg_processing_time"] = (
                (current_avg * (total_queries - 1) + processing_time) / total_queries
            )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Statistiques de traitement"""
        uptime = time.time() - self.processing_stats["last_reset"]
        error_rate = (self.processing_stats["errors_count"] / 
                     max(1, self.processing_stats["total_queries"]))
        
        return {
            **self.processing_stats,
            "uptime_seconds": uptime,
            "error_rate": error_rate,
            "queries_per_minute": self.processing_stats["total_queries"] / max(1, uptime / 60),
            "health_status": self._get_health_status(error_rate),
            "configuration": self.validation_stats if hasattr(self, 'validation_stats') else {}
        }
    
    def _get_health_status(self, error_rate: float) -> Dict[str, str]:
        """Évaluation de l'état de santé"""
        if not self.is_initialized:
            return {"status": "critical", "reason": "Non initialisé"}
        
        if error_rate > 0.1:
            return {"status": "critical", "reason": f"Taux d'erreur élevé: {error_rate:.1%}"}
        elif error_rate > 0.05:
            return {"status": "warning", "reason": f"Taux d'erreur modéré: {error_rate:.1%}"}
        else:
            return {"status": "healthy", "reason": "Fonctionnement normal"}
    
    def validate_current_config(self) -> ValidationResult:
        """Re-valide la configuration actuelle"""
        if not self.is_initialized:
            return ValidationResult(
                is_valid=False,
                errors=["Processeur non initialisé"],
                warnings=[],
                stats={}
            )
        
        return ConfigurationValidator.validate_configuration(self.intents_config)
    
    def reload_configuration(self):
        """Recharge la configuration (utile pour le développement)"""
        try:
            old_stats = self.processing_stats.copy()
            self._load_and_validate_config()
            self.processing_stats = old_stats  # Préservation des stats
            logger.info(f"Configuration rechargée: {self._get_config_summary()}")
        except Exception as e:
            logger.error(f"Échec rechargement configuration: {e}")
            raise

# Fonction utilitaire pour créer un processeur
def create_intent_processor(intents_file_path: Optional[str] = None) -> IntentProcessor:
    """
    Factory pour créer un processeur d'intentions avec validation stricte
    
    Args:
        intents_file_path: Chemin vers intents.json (optionnel, défaut: intents.json)
    
    Returns:
        IntentProcessor: Instance configurée et validée
        
    Raises:
        ConfigurationError: Si la configuration est invalide
    """
    if intents_file_path is None:
        intents_file_path = "intents.json"
    
    return IntentProcessor(intents_file_path)