# -*- coding: utf-8 -*-
"""
utils.py - Fonctions utilitaires robustes pour l'intégration du processeur d'intentions
Version corrigée: Validation stricte, gestion d'erreurs explicite
"""

import time
import logging
import json
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationReport:
    """Rapport de validation détaillé"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, Any]
    recommendations: List[str]

@dataclass
class ProcessingResult:
    """Résultat de traitement d'une requête"""
    success: bool
    result: Optional[Any] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None

# Exemples de requêtes de test améliorés avec variantes métier
COMPREHENSIVE_TEST_QUERIES = [
    # Requêtes métriques de base
    "Quel est le poids cible à 21 jours pour du Ross 308?",
    "FCR optimal pour poulet de chair Cobb 500 à 35 jours",
    "Consommation d'eau à 28 jours pour élevage tunnel",
    
    # Requêtes environnementales
    "Température de démarrage pour poussins en tunnel",
    "Ventilation minimale à 14 jours Ross 308",
    "Humidité optimale phase starter",
    
    # Protocoles et procédures
    "Programme de vaccination pour reproducteur",
    "Protocole biosécurité couvoir",
    "Densité optimale en élevage au sol",
    
    # Diagnostic et santé
    "Mes poulets ont des signes respiratoires",
    "Mortalité élevée à 10 jours que faire",
    "Symptômes Newcastle chez reproducteurs",
    
    # Économie et performance
    "Coût alimentaire par kg de poids vif produit",
    "Performance EPEF Ross 308 standard",
    "Marge bénéficiaire par sujet abattu",
    
    # Tests de normalisation et aliases
    "Ross-308 35j FCR",
    "C-500 poids 42 jours",
    "Hubbard Flex vaccination",
    "ISA Brown ponte pic",
    "R308 démarrage température",
    
    # Tests de domaine et complexité
    "Météo demain",  # Hors domaine
    "Comment élever des chats",  # Hors domaine
    "Performance globale exploitation complète multi-bâtiments",  # Complexe
]

class IntentProcessorFactory:
    """Factory robuste pour créer des processeurs d'intentions"""
    
    @staticmethod
    def create_processor(intents_file_path: Optional[str] = None, 
                        validate_on_creation: bool = True) -> 'IntentProcessor':
        """
        Crée un processeur d'intentions avec validation optionnelle
        
        Args:
            intents_file_path: Chemin vers intents.json
            validate_on_creation: Si True, valide la configuration à la création
        
        Returns:
            IntentProcessor: Instance configurée
            
        Raises:
            FileNotFoundError: Si le fichier de configuration n'existe pas
            ValueError: Si la configuration est invalide
            RuntimeError: Si l'initialisation échoue
        """
        # Import tardif pour éviter les dépendances circulaires
        try:
            from intent_processor import IntentProcessor, ConfigurationError
        except ImportError as e:
            raise RuntimeError(f"Module intent_processor non disponible: {e}")
        
        # Résolution automatique du chemin
        if intents_file_path is None:
            base_dir = Path(__file__).parent.resolve()
            intents_file_path = base_dir / "intents.json"
            logger.info(f"Utilisation du chemin par défaut: {intents_file_path}")
        
        try:
            processor = IntentProcessor(str(intents_file_path))
            
            if validate_on_creation:
                validation_result = processor.validate_current_config()
                if not validation_result.is_valid:
                    raise ValueError(f"Configuration invalide: {validation_result.errors}")
            
            # Vérification de santé après création
            stats = processor.get_processing_stats()
            health = stats.get('health_status', {})
            
            if health.get('status') == 'critical':
                logger.error(f"Processeur créé mais en état critique: {health.get('reason')}")
                raise RuntimeError(f"Processeur en état critique: {health.get('reason')}")
            
            logger.info(f"IntentProcessor créé avec succès - Statut: {health.get('status', 'unknown')}")
            return processor
            
        except ConfigurationError as e:
            logger.error(f"Erreur de configuration: {e}")
            raise ValueError(f"Configuration IntentProcessor invalide: {e}")
        except Exception as e:
            logger.error(f"Erreur création IntentProcessor: {e}")
            raise RuntimeError(f"Impossible de créer IntentProcessor: {e}")

def process_query_with_intents(processor, query: str, 
                              explain_score: Optional[float] = None,
                              timeout: float = 5.0) -> ProcessingResult:
    """
    Interface robuste pour traiter une requête avec gestion d'erreurs complète
    
    Args:
        processor: Instance IntentProcessor
        query: Requête à traiter
        explain_score: Score d'explication optionnel
        timeout: Timeout en secondes
    
    Returns:
        ProcessingResult: Résultat avec gestion d'erreurs
    """
    start_time = time.time()
    
    # Validation des paramètres d'entrée
    if not processor:
        return ProcessingResult(
            success=False,
            error_message="Processeur non fourni",
            processing_time=0.0
        )
    
    if not query or not query.strip():
        return ProcessingResult(
            success=False,
            error_message="Requête vide ou invalide",
            processing_time=0.0
        )
    
    # Vérification de l'état du processeur
    if not getattr(processor, 'is_initialized', False):
        return ProcessingResult(
            success=False,
            error_message="Processeur non initialisé",
            processing_time=0.0
        )
    
    try:
        # Traitement avec timeout simulé (pour les futures implémentations async)
        result = processor.process_query(query.strip(), explain_score)
        processing_time = time.time() - start_time
        
        # Validation du résultat
        if not result:
            return ProcessingResult(
                success=False,
                error_message="Aucun résultat retourné par le processeur",
                processing_time=processing_time
            )
        
        # Vérification de la cohérence du résultat
        if result.confidence < 0.0 or result.confidence > 1.0:
            logger.warning(f"Confidence invalide: {result.confidence}")
            result.confidence = max(0.0, min(1.0, result.confidence))
        
        return ProcessingResult(
            success=True,
            result=result,
            processing_time=processing_time,
            metadata={
                "query_length": len(query),
                "entities_detected": len(result.detected_entities),
                "intent_type": result.intent_type.value if hasattr(result.intent_type, 'value') else str(result.intent_type),
                "confidence_level": "high" if result.confidence > 0.8 else "medium" if result.confidence > 0.5 else "low"
            }
        )
        
    except TimeoutError:
        return ProcessingResult(
            success=False,
            error_message=f"Timeout après {timeout}s",
            processing_time=time.time() - start_time
        )
    except Exception as e:
        logger.error(f"Erreur traitement requête '{query[:50]}...': {e}")
        return ProcessingResult(
            success=False,
            error_message=f"Erreur de traitement: {str(e)}",
            processing_time=time.time() - start_time,
            metadata={"exception_type": type(e).__name__}
        )

def validate_intents_config(config_path: str, strict_mode: bool = True) -> ValidationReport:
    """
    Valide rigoureusement un fichier de configuration intents.json
    
    Args:
        config_path: Chemin vers le fichier de configuration
        strict_mode: Si True, applique des validations strictes
        
    Returns:
        ValidationReport: Rapport de validation détaillé
    """
    errors = []
    warnings = []
    recommendations = []
    stats = {}
    
    try:
        # Vérification de l'existence du fichier
        config_file = Path(config_path)
        if not config_file.exists():
            return ValidationReport(
                is_valid=False,
                errors=[f"Fichier non trouvé: {config_path}"],
                warnings=[],
                stats={},
                recommendations=["Vérifiez le chemin du fichier de configuration"]
            )
        
        # Lecture et parsing JSON
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            return ValidationReport(
                is_valid=False,
                errors=[f"Erreur JSON: {e}"],
                warnings=[],
                stats={},
                recommendations=["Vérifiez la syntaxe JSON avec un validateur"]
            )
        
        # Validation de structure avec le validateur intégré
        try:
            from intent_processor import ConfigurationValidator
            validation_result = ConfigurationValidator.validate_configuration(config)
            errors.extend(validation_result.errors)
            warnings.extend(validation_result.warnings)
            stats.update(validation_result.stats)
        except ImportError:
            # Validation de base si le module n'est pas disponible
            errors.extend(_basic_validation(config))
        
        # Validations étendues en mode strict
        if strict_mode:
            strict_errors, strict_warnings, strict_recommendations = _strict_validation(config)
            errors.extend(strict_errors)
            warnings.extend(strict_warnings)
            recommendations.extend(strict_recommendations)
        
        # Statistiques finales
        stats.update({
            "file_size_bytes": config_file.stat().st_size,
            "validation_timestamp": time.time(),
            "strict_mode": strict_mode
        })
        
        # Recommandations basées sur les statistiques
        if stats.get("total_aliases", 0) < 50:
            recommendations.append("Considérez l'ajout de plus d'aliases pour améliorer la couverture")
        
        if stats.get("total_metrics", 0) < 20:
            recommendations.append("Ajoutez plus de métriques pour une meilleure richesse fonctionnelle")
        
        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats,
            recommendations=recommendations
        )
        
    except Exception as e:
        return ValidationReport(
            is_valid=False,
            errors=[f"Erreur validation inattendue: {e}"],
            warnings=[],
            stats={},
            recommendations=["Contactez le support technique"]
        )

def _basic_validation(config: Dict[str, Any]) -> List[str]:
    """Validation de base sans dépendances externes"""
    errors = []
    
    required_sections = ["aliases", "intents", "universal_slots"]
    for section in required_sections:
        if section not in config:
            errors.append(f"Section manquante: {section}")
        elif not isinstance(config[section], dict):
            errors.append(f"Section {section} doit être un dictionnaire")
    
    return errors

def _strict_validation(config: Dict[str, Any]) -> tuple[List[str], List[str], List[str]]:
    """Validations strictes supplémentaires"""
    errors = []
    warnings = []
    recommendations = []
    
    # Validation des versions
    if "version" not in config:
        warnings.append("Pas de numéro de version défini")
        recommendations.append("Ajoutez un champ 'version' pour le suivi des configurations")
    
    # Validation de la completeness des aliases
    aliases = config.get("aliases", {})
    critical_categories = ["line", "site_type", "bird_type"]
    
    for category in critical_categories:
        if category not in aliases or not aliases[category]:
            errors.append(f"Catégorie d'alias critique manquante ou vide: {category}")
    
    # Validation de la cohérence des métriques
    intents = config.get("intents", {})
    for intent_name, intent_config in intents.items():
        metrics = intent_config.get("metrics", {})
        if not metrics:
            warnings.append(f"Intent {intent_name} sans métriques")
        
        for metric_name, metric_config in metrics.items():
            if not isinstance(metric_config, dict):
                errors.append(f"Configuration métrique invalide: {intent_name}.{metric_name}")
            elif "unit" not in metric_config:
                errors.append(f"Unité manquante pour {intent_name}.{metric_name}")
    
    return errors, warnings, recommendations

def run_comprehensive_validation_suite(processor, test_queries: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Suite de validation complète pour un processeur d'intentions
    
    Args:
        processor: Instance IntentProcessor à tester
        test_queries: Requêtes de test (optionnel, utilise les requêtes par défaut)
    
    Returns:
        Dict: Rapport complet de validation
    """
    if test_queries is None:
        test_queries = COMPREHENSIVE_TEST_QUERIES
    
    start_time = time.time()
    results = []
    errors = []
    
    # Tests de traitement
    for i, query in enumerate(test_queries):
        try:
            result = process_query_with_intents(processor, query)
            results.append({
                "query": query,
                "success": result.success,
                "confidence": result.result.confidence if result.result else 0.0,
                "intent": result.result.intent_type.value if result.result and hasattr(result.result.intent_type, 'value') else None,
                "processing_time": result.processing_time,
                "entities_count": len(result.result.detected_entities) if result.result else 0,
                "error": result.error_message
            })
        except Exception as e:
            errors.append(f"Erreur requête {i+1} '{query[:30]}...': {e}")
            results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })
    
    # Calcul des métriques agrégées
    successful_results = [r for r in results if r["success"]]
    total_time = time.time() - start_time
    
    if successful_results:
        avg_confidence = sum(r["confidence"] for r in successful_results) / len(successful_results)
        avg_processing_time = sum(r["processing_time"] for r in successful_results) / len(successful_results)
        avg_entities = sum(r["entities_count"] for r in successful_results) / len(successful_results)
    else:
        avg_confidence = avg_processing_time = avg_entities = 0.0
    
    # Analyse de distribution des intents
    intent_distribution = {}
    for result in successful_results:
        intent = result.get("intent", "unknown")
        intent_distribution[intent] = intent_distribution.get(intent, 0) + 1
    
    return {
        "summary": {
            "total_queries": len(test_queries),
            "successful_queries": len(successful_results),
            "success_rate": len(successful_results) / len(test_queries) if test_queries else 0,
            "total_validation_time": total_time,
            "avg_confidence": avg_confidence,
            "avg_processing_time": avg_processing_time,
            "avg_entities_detected": avg_entities
        },
        "intent_distribution": intent_distribution,
        "performance_metrics": {
            "queries_per_second": len(test_queries) / max(0.001, total_time),
            "high_confidence_rate": len([r for r in successful_results if r["confidence"] > 0.8]) / max(1, len(successful_results))
        },
        "detailed_results": results,
        "errors": errors,
        "recommendations": _generate_recommendations(results, successful_results)
    }

def _generate_recommendations(all_results: List[Dict], successful_results: List[Dict]) -> List[str]:
    """Génère des recommandations basées sur les résultats de validation"""
    recommendations = []
    
    success_rate = len(successful_results) / max(1, len(all_results))
    
    if success_rate < 0.8:
        recommendations.append(f"Taux de succès faible ({success_rate:.1%}) - vérifiez la configuration")
    
    if successful_results:
        avg_confidence = sum(r["confidence"] for r in successful_results) / len(successful_results)
        if avg_confidence < 0.6:
            recommendations.append(f"Confiance moyenne faible ({avg_confidence:.1%}) - enrichissez les aliases")
        
        low_entity_queries = [r for r in successful_results if r["entities_count"] == 0]
        if len(low_entity_queries) > len(successful_results) * 0.3:
            recommendations.append("Beaucoup de requêtes sans entités détectées - améliorez la couverture du vocabulaire")
    
    return recommendations

# Fonction principale de création (pour compatibilité)
def create_intent_processor(intents_file_path: Optional[str] = None) -> 'IntentProcessor':
    """
    Factory principale pour créer un processeur d'intentions
    
    Args:
        intents_file_path: Chemin vers intents.json (optionnel)
    
    Returns:
        IntentProcessor: Instance configurée et validée
    """
    return IntentProcessorFactory.create_processor(intents_file_path, validate_on_creation=True)

# Export des fonctions principales pour l'API publique
__all__ = [
    'create_intent_processor',
    'process_query_with_intents', 
    'validate_intents_config',
    'run_comprehensive_validation_suite',
    'ValidationReport',
    'ProcessingResult',
    'COMPREHENSIVE_TEST_QUERIES'
]