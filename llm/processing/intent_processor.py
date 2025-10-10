# -*- coding: utf-8 -*-

"""
intent_processor.py - Processeur d'intentions robuste avec validation stricte
Version: 1.1.0 - Ajout détection d'espèce via universal_terms
"""

import os
import json
import time
import logging
from utils.types import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass

# Imports modulaires corrigés pour la nouvelle architecture
from processing.intent_types import IntentType, IntentResult

# Import AGROVOCService for poultry term detection
from services.agrovoc_service import get_agrovoc_service

# Import language detection for AGROVOC
from utils.language_detection import detect_language_enhanced

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception pour les erreurs de configuration"""

    pass


@dataclass
class ValidationResult:
    """Résultat de validation avec détails"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, Any]


# CONFIGURATION PAR DÉFAUT INTÉGRÉE
DEFAULT_INTENT_CONFIG = {
    "version": "1.0.0",
    "aliases": {
        "line": {
            "ross": ["ross 308", "ross308", "r308"],
            "cobb": ["cobb 500", "cobb500", "c500"],
            "hubbard": ["hubbard classic", "classic"],
        },
        "site_type": {
            "elevage": ["élevage", "ferme", "exploitation"],
            "couvoir": ["écloserie", "hatchery"],
        },
        "bird_type": {"poulet": ["broiler", "chair"], "poule": ["pondeuse", "layer"]},
        "phase": {
            "demarrage": ["démarrage", "starter", "0-10j"],
            "croissance": ["croissance", "grower", "11-24j"],
            "finition": ["finition", "finisher", "25j+"],
        },
    },
    "intents": {
        "metric_query": {
            "description": "Requête sur les métriques de performance",
            "required": ["metric"],
            "metrics": {
                "fcr": {"unit": "ratio", "description": "Feed Conversion Ratio"},
                "poids": {"unit": "g", "description": "Poids corporel"},
                "mortalite": {"unit": "%", "description": "Taux de mortalité"},
            },
        },
        "environment_setting": {
            "description": "Paramètres d'environnement",
            "required": ["metric"],
            "metrics": {
                "temperature": {"unit": "°C", "description": "Température"},
                "humidite": {"unit": "%", "description": "Humidité relative"},
            },
        },
        "protocol_query": {
            "description": "Protocoles et procédures",
            "required": ["protocol_type"],
            "metrics": {
                "efficacite": {"unit": "%", "description": "Efficacité du protocole"},
                "compliance": {"unit": "%", "description": "Conformité"},
            },
        },
        "diagnosis_triage": {
            "description": "Diagnostic et triage sanitaire",
            "required": ["age_days|age_weeks", "signs"],
            "metrics": {
                "severity": {"unit": "score", "description": "Niveau de sévérité"},
                "urgency": {"unit": "score", "description": "Niveau d'urgence"},
            },
        },
        "economics_cost": {
            "description": "Analyse économique et coûts",
            "required": ["metric", "age_days|age_weeks"],
            "metrics": {
                "cout": {"unit": "€", "description": "Coût unitaire"},
                "rentabilite": {"unit": "%", "description": "Rentabilité"},
            },
        },
    },
    "universal_slots": {
        "metric": {
            "enum": [
                "fcr",
                "poids",
                "mortalité",
                "consommation",
                "température",
                "humidité",
            ]
        },
        "protocol_type": {
            "enum": ["vaccination", "feeding", "housing", "health", "breeding"]
        },
        "age_days": {"type": "int", "min": 1, "max": 365},
        "age_weeks": {"type": "int", "min": 1, "max": 52},
        "signs": {
            "enum": [
                "mortality",
                "weight_loss",
                "respiratory",
                "digestive",
                "behavioral",
            ]
        },
    },
}


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
            alias_errors, alias_warnings, alias_stats = cls._validate_aliases(
                config.get("aliases", {})
            )
            errors.extend(alias_errors)
            warnings.extend(alias_warnings)
            stats.update(alias_stats)

            # 3. Validation des intents
            intent_errors, intent_warnings, intent_stats = cls._validate_intents(
                config.get("intents", {})
            )
            errors.extend(intent_errors)
            warnings.extend(intent_warnings)
            stats.update(intent_stats)

            # 4. Validation des slots universels
            slot_errors, slot_stats = cls._validate_universal_slots(
                config.get("universal_slots", {})
            )
            errors.extend(slot_errors)
            stats.update(slot_stats)

            # 5. Validation de cohérence croisée
            coherence_errors = cls._validate_cross_references(config)
            errors.extend(coherence_errors)

        except Exception as e:
            errors.append(f"Erreur de validation inattendue: {e}")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings, stats=stats
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
    def _validate_aliases(
        cls, aliases: Dict[str, Any]
    ) -> tuple[List[str], List[str], Dict[str, Any]]:
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
                total_aliases += sum(
                    len(alias_list) if isinstance(alias_list, list) else 1
                    for alias_list in category_aliases.values()
                )

        stats["total_aliases"] = total_aliases
        stats["alias_categories_count"] = len(aliases)

        return errors, warnings, stats

    @classmethod
    def _validate_intents(
        cls, intents: Dict[str, Any]
    ) -> tuple[List[str], List[str], Dict[str, Any]]:
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
                    errors.append(
                        f"Champ manquant dans intent '{intent_name}': '{field}'"
                    )

            # Validation des métriques
            metrics = intent_config.get("metrics", {})
            if not isinstance(metrics, dict):
                errors.append(
                    f"Métriques de l'intent '{intent_name}' doivent être un dictionnaire"
                )
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
                errors.append(
                    f"Métrique '{metric_name}' de l'intent '{intent_name}' doit être un dictionnaire"
                )
                continue

            # Validation des unités
            if "unit" not in metric_config:
                errors.append(
                    f"Unité manquante pour la métrique '{metric_name}' de l'intent '{intent_name}'"
                )

        return errors

    @classmethod
    def _validate_universal_slots(
        cls, slots: Dict[str, Any]
    ) -> tuple[List[str], Dict[str, Any]]:
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

        # Vérifier que les références dans les intents correspondent aux slots
        intents = config.get("intents", {})
        slots = config.get("universal_slots", {})

        # Vérifier que les slots référencés existent
        for intent_name, intent_config in intents.items():
            required_fields = intent_config.get("required", [])
            for field in required_fields:
                # Gérer les champs avec alternatives (|)
                field_alternatives = field.split("|")
                field_found = any(
                    alt_field in slots for alt_field in field_alternatives
                )

                if not field_found:
                    # Ajouter seulement si aucune alternative n'est trouvée
                    errors.append(
                        f"Champ requis '{field}' dans intent '{intent_name}' non défini dans slots ou aliases"
                    )

        return errors


class IntentProcessor:
    """Processeur d'intentions robuste avec validation stricte"""

    def __init__(self, intents_file_path: str = None):
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
            "last_reset": time.time(),
        }

        # Initialisation avec validation stricte
        try:
            self._load_and_validate_config()

            # Initialize AGROVOC service for poultry term detection
            try:
                self.agrovoc_service = get_agrovoc_service()
                logger.info("✅ AGROVOCService initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize AGROVOCService: {e}")
                self.agrovoc_service = None

            self.is_initialized = True
            logger.info(
                f"IntentProcessor initialisé avec succès: {self._get_config_summary()}"
            )
        except Exception as e:
            self.initialization_error = e
            logger.error(f"Échec d'initialisation IntentProcessor: {e}")
            raise ConfigurationError(f"Impossible d'initialiser IntentProcessor: {e}")

    def _load_and_validate_config(self):
        """Charge et valide la configuration de manière stricte"""

        config = None

        # 1. Tentative de chargement du fichier externe
        if self.intents_file_path:
            try:
                config_path = self._resolve_config_path()
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info(f"Configuration chargée depuis: {config_path}")
            except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
                logger.warning(f"Impossible de charger {self.intents_file_path}: {e}")
                logger.info("Utilisation de la configuration par défaut")

        # 2. Utilisation de la configuration par défaut si nécessaire
        if config is None:
            config = DEFAULT_INTENT_CONFIG.copy()
            logger.info("Utilisation de la configuration par défaut intégrée")

        # 3. Validation stricte
        validation_result = ConfigurationValidator.validate_configuration(config)

        if not validation_result.is_valid:
            error_msg = "Configuration invalide:\n" + "\n".join(
                f"  - {error}" for error in validation_result.errors
            )
            raise ConfigurationError(error_msg)

        # 4. Logging des warnings
        if validation_result.warnings:
            for warning in validation_result.warnings:
                logger.warning(f"Configuration: {warning}")

        # 5. Stockage de la configuration validée
        self.intents_config = config
        self.validation_stats = validation_result.stats

        # ✅ NOUVEAU: Charger universal_terms pour la détection d'espèce
        try:
            self._load_universal_terms()
        except Exception as e:
            logger.warning(f"Impossible de charger universal_terms: {e}")
            # Continue sans universal_terms (fallback disponible)

        logger.info(f"Configuration validée: {validation_result.stats}")

    def _load_universal_terms(self, language: str = "en"):
        """
        Charge les termes universels pour une langue
        Nécessaire pour la détection d'espèce
        """
        config_dir = Path(__file__).parent.parent / "config"
        terms_file = config_dir / f"universal_terms_{language}.json"

        if terms_file.exists():
            with open(terms_file, "r", encoding="utf-8") as f:
                universal_data = json.load(f)
                # Stocker dans intents_config pour accès facile
                self.intents_config["universal_terms"] = universal_data.get(
                    "domains", {}
                )
                logger.info(f"✅ Universal terms loaded for language: {language}")
        else:
            logger.warning(f"⚠️ Universal terms file not found: {terms_file}")

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
                Path(__file__).parent / "config" / self.intents_file_path,
            ]

            for alt_path in alternative_paths:
                if alt_path.exists():
                    config_path = alt_path
                    logger.info(
                        f"Configuration trouvée via chemin alternatif: {config_path}"
                    )
                    break
            else:
                raise ConfigurationError(
                    f"Fichier de configuration introuvable: {config_path}\n"
                    f"Chemins testés: {[str(p) for p in [config_path] + alternative_paths]}"
                )

        return config_path.resolve()

    def _get_config_summary(self) -> str:
        """Résumé de la configuration chargée"""
        stats = getattr(self, "validation_stats", {})
        return (
            f"v{self.intents_config.get('version', 'unknown')} - "
            f"{stats.get('total_intents', 0)} intents, "
            f"{stats.get('total_metrics', 0)} métriques, "
            f"{stats.get('total_aliases', 0)} aliases"
        )

    def _safe_string_lower(self, value: Any) -> Optional[str]:
        """
        Convertit une valeur en minuscules de manière sûre.
        🔴 CORRECTION CRITIQUE: Évite l'erreur .lower() sur des entiers

        Args:
            value: Valeur à convertir (str, int, float, None, etc.)

        Returns:
            str en minuscules ou None si valeur None/vide
        """
        if value is None:
            return None

        # Convertir en string puis en minuscules
        str_value = str(value).strip()
        return str_value.lower() if str_value else None

    def _detect_species_from_query(self, query: str) -> Optional[str]:
        """
        Détecte l'espèce dans la query via universal_terms

        Returns:
            database_value de l'espèce détectée (ex: "broiler", "layer", "breeder")
        """
        # Charger les termes universels depuis intents_config
        if "universal_terms" not in self.intents_config:
            # Fallback: détection basique sans universal_terms
            return self._detect_species_fallback(query)

        query_lower = self._safe_string_lower(query)
        if not query_lower:
            return None

        species_terms = self.intents_config.get("universal_terms", {}).get(
            "species", {}
        )

        # Chercher la première correspondance
        for species_key, data in species_terms.items():
            variants = data.get("variants", [])
            database_value = data.get("database_value", species_key)

            for variant in variants:
                variant_lower = self._safe_string_lower(variant)
                if variant_lower and variant_lower in query_lower:
                    logger.info(
                        f"🐔 Species detected: {database_value} (matched: {variant})"
                    )
                    return database_value

        return None

    def _detect_general_poultry_terms(self, query: str, language: str = "en") -> bool:
        """
        Détecte si la requête contient des termes généraux d'aviculture

        Utilisé pour éviter de marquer comme OUT_OF_DOMAIN des questions générales
        sur l'aviculture qui ne contiennent pas d'entités spécifiques.

        Exemples:
        - "Is it safe to use AI to raise poultry?" ✅ (contient "raise", "poultry")
        - "How to improve chicken farming?" ✅ (contient "chicken", "farming")
        - "What is Spaghetti breast?" ✅ (modern meat quality defect - AGROVOC Level 2)
        - "What is the best temperature for broilers?" ✅ (already detected via entities)
        - "What is artificial intelligence?" ❌ (pas d'aviculture)

        Uses AGROVOCService with 3-level detection:
        - Level 1: AGROVOC cache (2,390+ terms in 10 languages)
        - Level 2: Manual terms (nl, id + modern defects like "spaghetti breast")
        - Level 3: Universal fallback (basic terms)

        Returns:
            True si la requête contient des termes généraux d'aviculture
        """
        # Use AGROVOCService if available
        if hasattr(self, 'agrovoc_service') and self.agrovoc_service is not None:
            # If language not specified, detect it from query
            if language == "en":  # default, might not be accurate
                lang_result = detect_language_enhanced(query)
                detected_language = lang_result.language
                logger.debug(f"Language detected for AGROVOC: {detected_language} (confidence: {lang_result.confidence:.2f})")
            else:
                detected_language = language

            is_poultry = self.agrovoc_service.detect_poultry_terms_in_query(query, detected_language)
            if is_poultry:
                logger.debug(f"🐔 Poultry terms detected via AGROVOC service ({detected_language})")
            return is_poultry

        # Fallback to legacy hardcoded terms if AGROVOC not available
        logger.warning("AGROVOCService not available, using legacy hardcoded terms")
        query_lower = self._safe_string_lower(query) or ""

        # Charger les termes universels si disponibles
        universal_terms = self.intents_config.get("universal_terms", {})

        # 1. Check general_terms from universal_terms
        if universal_terms:
            general_terms = universal_terms.get("general_terms", {})
            for term_key, term_data in general_terms.items():
                variants = term_data.get("variants", [])
                for variant in variants:
                    variant_lower = self._safe_string_lower(variant)
                    if variant_lower and variant_lower in query_lower:
                        logger.debug(f"🐔 General poultry term detected: {variant}")
                        return True

        # 2. Fallback: hardcoded general poultry terms (if universal_terms not loaded)
        general_poultry_terms = [
            # General terms
            "poultry", "aviculture", "chicken", "chickens", "bird", "birds",
            "hen", "hens", "rooster", "roosters", "broiler", "broilers",
            "layer", "layers", "breeder", "breeders",

            # French terms
            "volaille", "volailles", "poulet", "poulets", "poule", "poules",
            "avicole", "élevage", "élever",

            # Spanish terms
            "ave", "aves", "pollo", "pollos", "gallina", "gallinas",
            "avicultura", "criar",

            # Actions related to poultry
            "raise", "raising", "farming", "farm", "breeding", "breed",
            "hatching", "incubation", "egg production", "meat production",

            # French actions
            "élever", "élevage", "reproduction", "ponte",

            # Spanish actions
            "criar", "crianza", "granja",
        ]

        for term in general_poultry_terms:
            if term in query_lower:
                logger.debug(f"🐔 General poultry term detected (fallback): {term}")
                return True

        return False

    def _detect_species_fallback(self, query: str) -> Optional[str]:
        """
        Détection basique d'espèce sans universal_terms (fallback)
        Utilise des termes hardcodés pour garantir un minimum de fonctionnalité
        """
        query_lower = self._safe_string_lower(query) or ""

        # Termes broilers
        if any(
            term in query_lower
            for term in [
                "broiler",
                "meat chicken",
                "poulet de chair",
                "chair",
                "meat bird",
            ]
        ):
            logger.info("🐔 Species detected (fallback): broiler")
            return "broiler"

        # Termes layers
        if any(
            term in query_lower
            for term in [
                "layer",
                "laying hen",
                "pondeuse",
                "ponte",
                "egg production",
                "egg layer",
            ]
        ):
            logger.info("🐔 Species detected (fallback): layer")
            return "layer"

        # Termes breeders
        if any(
            term in query_lower
            for term in [
                "breeder",
                "parent stock",
                "reproducteur",
                "reproduction",
                "breeding",
            ]
        ):
            logger.info("🐔 Species detected (fallback): breeder")
            return "breeder"

        return None

    def process_query(
        self, query: str, explain_score: Optional[float] = None
    ) -> IntentResult:
        """Traite une requête avec gestion d'erreurs robuste"""

        if not self.is_initialized:
            raise RuntimeError(
                f"IntentProcessor non initialisé: {self.initialization_error}"
            )

        start_time = time.time()
        self.processing_stats["total_queries"] += 1

        try:
            # Traitement de la requête
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
                processing_time=time.time() - start_time,
                confidence_breakdown={"error": 1.0},
                vocabulary_coverage={},
                expansion_quality={},
            )

    def _process_query_internal(
        self, query: str, explain_score: Optional[float]
    ) -> IntentResult:
        """Traitement interne de la requête"""

        # Détection d'entités basée sur les aliases
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

                # 🔴 CORRECTION: Utiliser _safe_string_lower au lieu de .lower() direct
                query_lower = self._safe_string_lower(query)
                if query_lower is None:
                    continue

                for term in all_terms:
                    term_lower = self._safe_string_lower(term)
                    if term_lower and term_lower in query_lower:
                        detected_entities[category] = main_term
                        break

        # ✅ NOUVEAU: Détecter l'espèce
        species = self._detect_species_from_query(query)
        if species:
            detected_entities["species"] = species
            logger.debug(f"🐔 Species added to entities: {species}")

        # Détection d'intent basée sur les mots-clés
        query_lower = self._safe_string_lower(query) or ""

        if any(
            word in query_lower
            for word in ["coût", "prix", "économique", "rentabilité"]
        ):
            intent_type = IntentType.ECONOMICS_COST
        elif any(
            word in query_lower
            for word in ["problème", "maladie", "symptôme", "diagnostic"]
        ):
            intent_type = IntentType.DIAGNOSIS_TRIAGE
        elif any(
            word in query_lower for word in ["protocole", "procédure", "vaccination"]
        ):
            intent_type = IntentType.PROTOCOL_QUERY
        elif any(
            word in query_lower for word in ["température", "humidité", "environnement"]
        ):
            intent_type = IntentType.ENVIRONMENT_SETTING
        else:
            intent_type = IntentType.METRIC_QUERY

        # Calcul de confiance basé sur les entités détectées
        if detected_entities:
            confidence = min(0.95, 0.5 + len(detected_entities) * 0.15)
        else:
            # ✅ FIX: Before marking as OUT_OF_DOMAIN, check for general poultry terms
            # Questions like "Is it safe to use AI to raise poultry?" should be IN-DOMAIN
            # even without specific entities (genetic lines, metrics, etc.)
            is_poultry_domain = self._detect_general_poultry_terms(query)

            if is_poultry_domain:
                confidence = 0.6  # Medium confidence (no specific entities but clearly poultry-related)
                intent_type = IntentType.GENERAL_POULTRY  # General poultry questions
                logger.info(f"🐔 General poultry query detected (no specific entities): {query[:80]}...")
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
                "entities_found": len(detected_entities),
            },
            processing_time=0.0,  # Sera mis à jour par le caller
            confidence_breakdown={
                "entity_match": confidence,
                "domain_relevance": confidence * 0.9,
            },
            vocabulary_coverage={},
            expansion_quality={},
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
                current_avg * (total_queries - 1) + processing_time
            ) / total_queries

    def get_processing_stats(self) -> Dict[str, Any]:
        """Statistiques de traitement"""
        uptime = time.time() - self.processing_stats["last_reset"]
        error_rate = self.processing_stats["errors_count"] / max(
            1, self.processing_stats["total_queries"]
        )

        return {
            **self.processing_stats,
            "uptime_seconds": uptime,
            "error_rate": error_rate,
            "queries_per_minute": self.processing_stats["total_queries"]
            / max(1, uptime / 60),
            "health_status": self._get_health_status(error_rate),
            "configuration": (
                self.validation_stats if hasattr(self, "validation_stats") else {}
            ),
        }

    def _get_health_status(self, error_rate: float) -> Dict[str, str]:
        """Évaluation de l'état de santé"""
        if not self.is_initialized:
            return {"status": "critical", "reason": "Non initialisé"}

        if error_rate > 0.1:
            return {
                "status": "critical",
                "reason": f"Taux d'erreur élevé: {error_rate:.1%}",
            }
        elif error_rate > 0.05:
            return {
                "status": "warning",
                "reason": f"Taux d'erreur modéré: {error_rate:.1%}",
            }
        else:
            return {"status": "healthy", "reason": "Fonctionnement normal"}

    def validate_current_config(self) -> ValidationResult:
        """Re-valide la configuration actuelle"""
        if not self.is_initialized:
            return ValidationResult(
                is_valid=False,
                errors=["Processeur non initialisé"],
                warnings=[],
                stats={},
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
        intents_file_path: Chemin vers intents.json (optionnel, utilise config par défaut)

    Returns:
        IntentProcessor: Instance configurée et validée

    Raises:
        ConfigurationError: Si la configuration est invalide
    """
    return IntentProcessor(intents_file_path)


# Exports pour compatibilité
__all__ = [
    "IntentProcessor",
    "IntentType",
    "IntentResult",
    "ValidationResult",
    "ConfigurationError",
    "create_intent_processor",
]
