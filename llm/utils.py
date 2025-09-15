# -*- coding: utf-8 -*-
"""
utils.py - Fonctions utilitaires pour l'intégration du processeur d'intentions
"""

import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Exemples de requêtes de test pour validation avec variantes normalisées
SAMPLE_TEST_QUERIES = [
    "Quel est le poids cible à 21 jours pour du Ross 308?",
    "FCR optimal pour poulet de chair Cobb 500 à 35 jours",
    "Température de démarrage pour poussins en tunnel",
    "Programme de vaccination pour reproducteur",
    "Mes poulets ont des signes respiratoires",
    "Coût alimentaire par kg de poids vif produit",
    "Consommation d'eau à 28 jours",
    "Densité optimale en élevage au sol",
    "Protocole biosécurité couvoir",
    "Performance EPEF Ross 308 standard",
    # Nouveaux: tests normalisation
    "Ross-308 35j FCR",
    "C-500 poids 42 jours",
    "Hubbard Flex vaccination",
    "ISA Brown ponte pic"
]

def create_intent_processor(intents_file_path: Optional[str] = None):
    """
    Factory pour créer un processeur d'intentions avec résolution automatique du chemin.
    
    Args:
        intents_file_path: Chemin vers intents.json (optionnel, résolution auto si None)
    
    Returns:
        IntentProcessor: Instance configurée et prête à l'emploi
        
    Note:
        La factory résout automatiquement le chemin relatif pour éviter les problèmes
        de déploiement Docker (WORKDIR). Si intents.json n'est pas trouvé,
        une configuration de fallback est utilisée.
    """
    from .intent_processor import IntentProcessor
    
    if intents_file_path is None:
        # Résolution automatique du chemin - Compatible Docker
        base_dir = Path(__file__).parent.resolve()
        intents_file_path = base_dir / "intents.json"
        
        logger.info(f"Résolution automatique du chemin: {intents_file_path}")
    
    processor = IntentProcessor(str(intents_file_path))
    
    # Log de vérification pour le déploiement
    stats = processor.get_processing_stats()
    logger.info(f"IntentProcessor créé - Santé: {stats['health_status']['status']}")
    
    return processor

def process_query_with_intents(processor, query: str, 
                              explain_score: Optional[float] = None):
    """
    Interface simple pour traiter une requête avec gestion d'erreurs robuste et intégration explain_score.
    
    Args:
        processor: Instance du processeur d'intentions
        query: Requête utilisateur à traiter
        explain_score: Score d'évidence du retriever pour guardrails (optionnel)
        
    Returns:
        IntentResult: Résultat du traitement avec métriques complètes
    """
    from .intent_types import IntentResult, IntentType
    
    try:
        return processor.process_query(query, explain_score)
    except Exception as e:
        logger.error(f"Erreur critique dans process_query_with_intents: {e}")
        
        # Fallback gracieux
        return IntentResult(
            intent_type=IntentType.GENERAL_POULTRY,
            confidence=0.3,
            detected_entities={},
            expanded_query=query,
            metadata={
                "error": "critical_processing_error",
                "error_details": str(e),
                "fallback_applied": True
            },
            processing_time=0.0
        )

def get_intent_processor_health(processor) -> Dict[str, Any]:
    """
    Retourne l'état de santé du processeur pour monitoring/health-check avec métriques étendues.
    
    Args:
        processor: Instance du processeur d'intentions
        
    Returns:
        Dict: Métriques de santé complètes pour exposition dans get_status()
        
    Usage:
        # Dans votre moteur principal:
        health_data = get_intent_processor_health(intent_processor)
        # Exposer dans l'endpoint /status ou équivalent
    """
    try:
        stats = processor.get_processing_stats()
        coverage = processor.get_coverage_summary()
        
        return {
            "intent_processor": {
                "status": stats["health_status"]["status"],
                "uptime_seconds": stats["processing"]["uptime_seconds"],
                "total_queries": stats["processing"]["total_queries"],
                "error_rate": stats["processing"]["error_rate"],
                "avg_response_time": stats["processing"]["avg_processing_time"],
                "vocabulary_loaded": stats["vocabulary"]["total_keywords"] > 0,
                "config_version": stats["configuration"]["config_version"],
                "coverage_summary": coverage,
                "cache_performance": stats["vocabulary"]["cache_info"],
                "adaptive_thresholds": stats["health_status"]["adaptive_thresholds"],
                "semantic_fallback": stats["health_status"]["fallback_usage"],
                "guardrails_integration": stats["health_status"]["guardrails_integration"],
                "last_health_check": time.time()
            }
        }
    except Exception as e:
        logger.error(f"Erreur health check intent processor: {e}")
        return {
            "intent_processor": {
                "status": "error",
                "error": str(e),
                "last_health_check": time.time()
            }
        }

def get_cache_key_from_intent(intent_result) -> str:
    """
    Extrait la clé de cache normalisée d'un résultat d'intention pour Redis.
    
    Args:
        intent_result: Résultat du traitement d'intention
        
    Returns:
        str: Clé de cache normalisée pour Redis
        
    Usage:
        # Dans redis_cache_manager.py ou rag_engine.py:
        cache_key = get_cache_key_from_intent(intent_result)
        # Utiliser pour lookup Redis avec fallback sémantique
    """
    return intent_result.cache_key_normalized or "general"

def get_semantic_fallback_keys(intent_result) -> List[str]:
    """
    Extrait les clés de fallback sémantique pour cache Redis en mode STRICT.
    
    Args:
        intent_result: Résultat du traitement d'intention
        
    Returns:
        List[str]: Liste des clés de fallback sémantique
        
    Usage:
        # Dans redis_cache_manager.py pour mode STRICT:
        fallback_keys = get_semantic_fallback_keys(intent_result)
        for key in fallback_keys:
            if cache_hit := await redis.get(key):
                return cache_hit  # avec TTL plus court
    """
    return intent_result.semantic_fallback_candidates

def should_use_strict_threshold(intent_result) -> bool:
    """
    Détermine si un seuil strict doit être appliqué pour le filtre OOD.
    
    Args:
        intent_result: Résultat du traitement d'intention
        
    Returns:
        bool: True si seuil strict recommandé, False sinon
        
    Usage:
        # Dans rag_engine.py pour filtrage OOD adaptatif:
        if should_use_strict_threshold(intent_result):
            ood_threshold = 0.85  # Seuil plus strict
        else:
            ood_threshold = 0.70  # Seuil normal
    """
    adaptive_factors = intent_result.vocabulary_coverage.get("adaptive_factors", {})
    
    # Seuil strict si pas de patterns haute confiance
    if not adaptive_factors.get("high_confidence", False):
        if not adaptive_factors.get("genetics_present", False):
            if len(intent_result.detected_entities) <= 1:
                return True
    
    return False

def get_guardrails_context(intent_result) -> Dict[str, Any]:
    """
    Génère le contexte pour les guardrails basé sur l'analyse d'intention.
    
    Args:
        intent_result: Résultat du traitement d'intention
        
    Returns:
        Dict: Contexte enrichi pour guardrails
        
    Usage:
        # Dans rag_engine.py pour guardrails:
        guardrails_context = get_guardrails_context(intent_result)
        # Passer à evaluate_guardrails() pour améliorer evidence_support
    """
    return {
        "intent_confidence": intent_result.confidence,
        "intent_type": intent_result.intent_type.value,
        "entities_detected": len(intent_result.detected_entities),
        "technical_context": intent_result.vocabulary_coverage.get("adaptive_factors", {}),
        "domain_coverage": intent_result.vocabulary_coverage.get("domain_coverage", {}),
        "explain_score_used": intent_result.metadata.get("explain_score_used"),
        "high_confidence_indicators": {
            "genetics_present": intent_result.vocabulary_coverage.get("adaptive_factors", {}).get("genetics_present", False),
            "technical_metrics": intent_result.vocabulary_coverage.get("adaptive_factors", {}).get("technical_metrics", False),
            "specific_entities": "line" in intent_result.detected_entities and "metrics" in intent_result.detected_entities
        }
    }

def test_query_processing(processor, test_queries: List[str]) -> Dict[str, Any]:
    """
    Teste le processeur sur une liste de requêtes pour validation avec métriques intégration.
    
    Args:
        processor: Instance du processeur
        test_queries: Liste de requêtes de test
        
    Returns:
        Dict: Résultats des tests avec métriques
    """
    results = []
    
    for i, query in enumerate(test_queries):
        start_time = time.time()
        # Test avec explain_score simulé
        explain_score = 0.8 if i % 2 == 0 else None
        result = processor.process_query(query, explain_score)
        
        results.append({
            "query": query,
            "intent": result.intent_type.value,
            "confidence": result.confidence,
            "entities_count": len(result.detected_entities),
            "expanded": result.expanded_query != query,
            "cache_key": result.cache_key_normalized,
            "fallback_candidates": len(result.semantic_fallback_candidates),
            "explain_score": explain_score,
            "processing_time": time.time() - start_time
        })
    
    # Statistiques globales
    avg_confidence = sum(r["confidence"] for r in results) / len(results)
    avg_processing_time = sum(r["processing_time"] for r in results) / len(results)
    expansion_rate = sum(1 for r in results if r["expanded"]) / len(results)
    cache_key_diversity = len(set(r["cache_key"] for r in results)) / len(results)
    
    return {
        "results": results,
        "summary": {
            "total_queries": len(test_queries),
            "avg_confidence": avg_confidence,
            "avg_processing_time": avg_processing_time,
            "expansion_rate": expansion_rate,
            "cache_key_diversity": cache_key_diversity,
            "intent_distribution": {
                intent: sum(1 for r in results if r["intent"] == intent)
                for intent in set(r["intent"] for r in results)
            },
            "integration_metrics": {
                "fallback_candidates_avg": sum(r["fallback_candidates"] for r in results) / len(results),
                "explain_score_usage": sum(1 for r in results if r["explain_score"] is not None) / len(results)
            }
        }
    }

def validate_intents_config(config_path: str) -> Dict[str, Any]:
    """
    Valide un fichier de configuration intents.json
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        Dict: Résultat de la validation avec erreurs et warnings
    """
    import json
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        errors = []
        warnings = []
        
        # Validation structure de base
        required_keys = ["aliases", "intents", "universal_slots"]
        for key in required_keys:
            if key not in config:
                errors.append(f"Clé manquante: {key}")
        
        # Validation aliases
        if "aliases" in config:
            expected_categories = ["line", "site_type", "bird_type", "phase", "sex"]
            for category in expected_categories:
                if category not in config["aliases"]:
                    warnings.append(f"Catégorie alias manquante: {category}")
        
        # Validation intents
        if "intents" in config:
            for intent_name, intent_config in config["intents"].items():
                if "metrics" not in intent_config:
                    errors.append(f"Métriques manquantes pour intent: {intent_name}")
                
                # Vérification cohérence métriques
                metrics = intent_config.get("metrics", {})
                for metric_name, metric_config in metrics.items():
                    if not isinstance(metric_config, dict):
                        errors.append(f"Configuration métrique invalide: {intent_name}.{metric_name}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "total_aliases": sum(len(aliases) for aliases in config.get("aliases", {}).values()),
                "total_intents": len(config.get("intents", {})),
                "total_metrics": sum(
                    len(intent.get("metrics", {})) 
                    for intent in config.get("intents", {}).values()
                )
            }
        }
        
    except FileNotFoundError:
        return {
            "valid": False,
            "errors": [f"Fichier non trouvé: {config_path}"],
            "warnings": [],
            "stats": {}
        }
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "errors": [f"Erreur JSON: {e}"],
            "warnings": [],
            "stats": {}
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Erreur validation: {e}"],
            "warnings": [],
            "stats": {}
        }
