# app/api/v1/expert_confidence.py
# -*- coding: utf-8 -*-
"""
Intégration du système de confidence unifié pour expert.py
Fonctions spécialisées pour le calcul et l'application du confidence score
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 🎯 Import système de confidence unifié
try:
    from .pipeline.unified_confidence import (
        calculate_unified_confidence,
        get_confidence_summary,
        get_detailed_confidence,
        test_unified_confidence,
        ConfidenceBreakdown
    )
    CONFIDENCE_SYSTEM_AVAILABLE = True
    logger.info("🎯 Système de confidence unifié importé avec succès")
except ImportError as e:
    CONFIDENCE_SYSTEM_AVAILABLE = False
    logger.warning(f"⚠️ Système de confidence unifié indisponible: {e}")
    
    # Fallback pour éviter les erreurs
    def test_unified_confidence():
        return {"status": "unavailable", "reason": "Module not imported"}
    
    def calculate_unified_confidence(*args, **kwargs):
        return None
    
    # 🛠️ FIX: Fonction fallback corrigée pour gérer les décimaux
    def get_confidence_summary(breakdown):
        if breakdown is None:
            return {"score": 75.0, "level": "medium", "explanation": "Score par défaut"}
        
        # Fix: convertir décimal en pourcentage si nécessaire
        raw_score = getattr(breakdown, 'unified_score', 0.75)
        score = raw_score * 100 if raw_score <= 1.0 else raw_score
        level = getattr(breakdown, 'level', 'medium')
        level_str = level.value if hasattr(level, 'value') else str(level)
        
        return {
            "score": score,
            "level": level_str,
            "explanation": f"Score unifié calculé: {score:.1f}%"
        }

# 🎯 Import système d'analyse des intentions
try:
    from .pipeline.intent_confidence import analyze_intent_confidence
    INTENT_CONFIDENCE_AVAILABLE = True
    logger.info("🎯 Analyseur de confiance des intentions importé")
except ImportError as e:
    INTENT_CONFIDENCE_AVAILABLE = False
    logger.warning(f"⚠️ Analyseur de confiance des intentions indisponible: {e}")
    
    def analyze_intent_confidence(*args, **kwargs):
        return "unknown", 0.7, {"reason": "analyzer_unavailable"}

# ===== Fonctions de préparation pour confidence unifié =====

def prepare_validation_result_for_confidence(validation_result) -> Dict[str, Any]:
    """
    Convertit ValidationResult en format compatible avec unified_confidence
    """
    if not validation_result:
        return {
            "is_valid": True,
            "confidence": 100.0,
            "reason": "Validation non effectuée"
        }
    
    return {
        "is_valid": validation_result.is_valid,
        "confidence": validation_result.confidence,
        "reason": validation_result.reason,
        "suggested_topics": getattr(validation_result, 'suggested_topics', []),
        "detected_keywords": getattr(validation_result, 'detected_keywords', []),
        "rejected_keywords": getattr(validation_result, 'rejected_keywords', [])
    }

def prepare_confidence_inputs(
    classification: Dict[str, Any],
    completeness: Dict[str, Any],
    validation_result: Optional[Dict[str, Any]] = None
) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Prépare les inputs pour le calcul de confidence unifié
    """
    # 1. Analyse des intentions (si disponible)
    intent_analysis = None
    if INTENT_CONFIDENCE_AVAILABLE and classification.get("intent"):
        try:
            intent_str, intent_confidence, intent_details = analyze_intent_confidence(
                question="",  # Pas besoin de re-analyser la question
                context=classification.get("entities", {}),
                intent_candidates={str(classification["intent"]): 0.8}  # Simplifiée
            )
            intent_analysis = {
                "intent": intent_str,
                "confidence": intent_confidence,
                "confidence_factors": intent_details
            }
        except Exception as e:
            logger.warning(f"⚠️ Erreur analyse confiance intentions: {e}")
    
    # 2. Analyse de complétude (déjà calculée)
    completeness_analysis = completeness if completeness else None
    
    # 3. Résultat de validation (passé en paramètre)
    validation_analysis = validation_result
    
    return intent_analysis, completeness_analysis, validation_analysis

def apply_unified_confidence(
    response: Dict[str, Any],
    intent_analysis: Optional[Dict[str, Any]] = None,
    completeness_analysis: Optional[Dict[str, Any]] = None,
    validation_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Applique le système de confidence unifié à une réponse
    Retourne la réponse enrichie avec le score de confiance
    """
    if not CONFIDENCE_SYSTEM_AVAILABLE:
        # Fallback simple si système indisponible
        response["confidence"] = {
            "score": 75.0,
            "level": "medium", 
            "explanation": "Score par défaut (système unifié indisponible)"
        }
        return response
    
    try:
        # Calculer le confidence unifié
        confidence_breakdown = calculate_unified_confidence(
            result=response,
            intent_analysis=intent_analysis,
            completeness_analysis=completeness_analysis,
            validation_result=validation_result
        )
        
        # Ajouter le résumé à la réponse
        response["confidence"] = get_confidence_summary(confidence_breakdown)
        
        # Ajouter les détails complets en mode debug si activé
        import os
        debug_confidence = str(os.getenv("DEBUG_CONFIDENCE", "false")).lower() in ("1", "true", "yes", "on")
        if debug_confidence:
            response["confidence_debug"] = get_detailed_confidence(confidence_breakdown)
        
        # 🛠️ FIX: Log corrigé pour afficher le pourcentage correct
        if confidence_breakdown:
            raw_score = getattr(confidence_breakdown, 'unified_score', 0)
            display_score = raw_score * 100 if raw_score <= 1.0 else raw_score
            level_value = getattr(confidence_breakdown.level, 'value', str(confidence_breakdown.level)) if hasattr(confidence_breakdown, 'level') else 'unknown'
            logger.info(f"🎯 Confidence unifié calculé: {display_score:.1f}% ({level_value})")
        else:
            logger.warning("⚠️ confidence_breakdown est None")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Erreur calcul confidence unifié: {e}")
        # Fallback en cas d'erreur
        response["confidence"] = {
            "score": 50.0,
            "level": "medium",
            "explanation": f"Erreur calcul confidence: {str(e)}"
        }
        return response

# ===== Fonctions de confidence prédéfinies pour cas spéciaux =====

def get_quota_exceeded_confidence() -> Dict[str, Any]:
    """Confidence pour quota dépassé"""
    return {
        "score": 100.0,
        "level": "very_high",
        "explanation": "Quota dépassé - information système fiable"
    }

def get_validation_rejected_confidence(validation_confidence: float) -> Dict[str, Any]:
    """Confidence pour validation agricole échouée"""
    level = "medium" if validation_confidence > 70 else "low"
    return {
        "score": validation_confidence,
        "level": level,
        "explanation": f"Question hors domaine agricole (confiance validation: {validation_confidence}%)"
    }

def get_system_error_confidence(error_type: str) -> Dict[str, Any]:
    """Confidence pour erreurs système"""
    return {
        "score": 5.0,
        "level": "very_low",
        "explanation": f"Erreur système: {error_type}"
    }

def get_perfstore_confidence(has_data: bool) -> Dict[str, Any]:
    """Confidence pour PerfStore probe"""
    if has_data:
        return {
            "score": 95.0,
            "level": "very_high",
            "explanation": "Données PerfStore directes - très fiable"
        }
    else:
        return {
            "score": 90.0,
            "level": "high",
            "explanation": "Paramètres manquants clarifiés"
        }

def get_dialogue_unavailable_confidence() -> Dict[str, Any]:
    """Confidence pour dialogue manager indisponible"""
    return {
        "score": 30.0,
        "level": "low", 
        "explanation": "Service de dialogue temporairement indisponible"
    }

# ===== Fonctions de test et monitoring =====

def get_confidence_system_status() -> Dict[str, Any]:
    """Retourne le status du système de confidence"""
    return {
        "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE,
        "intent_confidence_available": INTENT_CONFIDENCE_AVAILABLE,
        "test_function_available": CONFIDENCE_SYSTEM_AVAILABLE,
        "debug_mode_env_var": "DEBUG_CONFIDENCE"
    }

async def test_confidence_system_async() -> Dict[str, Any]:
    """Test async du système de confidence"""
    import asyncio
    
    if not CONFIDENCE_SYSTEM_AVAILABLE:
        return {
            "error": "Confidence system not available",
            "status": "unavailable"
        }
    
    try:
        # Test du module unified_confidence directement
        confidence_test = await asyncio.to_thread(test_unified_confidence)
        
        return {
            "status": "completed",
            "confidence_system_available": True,
            "module_test": confidence_test,
            "integration_available": True
        }
        
    except Exception as e:
        return {
            "error": f"Confidence system test failed: {str(e)}",
            "status": "error",
            "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE
        }

def get_confidence_examples() -> Dict[str, Any]:
    """Exemples de scores de confidence selon différents scénarios"""
    return {
        "confidence_levels": {
            "very_high": {
                "score_range": "90-100%",
                "description": "Réponse très fiable avec données précises et contexte complet",
                "examples": [
                    "Lookup exact dans table de performance avec lignée, sexe et âge précis",
                    "Calcul mathématique avec paramètres complets",
                    "Réponse basée sur données techniques officielles"
                ]
            },
            "high": {
                "score_range": "70-89%",
                "description": "Réponse fiable basée sur des sources techniques solides",
                "examples": [
                    "RAG avec sources multiples et contexte riche",
                    "Analyse CoT structurée avec données partielles",
                    "Réponse technique avec validation agricole forte"
                ]
            },
            "medium": {
                "score_range": "50-69%",
                "description": "Réponse correcte mais avec certaines limitations contextuelles",
                "examples": [
                    "RAG avec sources limitées",
                    "Fallback OpenAI avec bon contexte",
                    "Réponse de clarification avec informations partielles"
                ]
            },
            "low": {
                "score_range": "30-49%",
                "description": "Réponse approximative, précisions recommandées",
                "examples": [
                    "Fallback OpenAI avec contexte limité",
                    "Question partiellement hors domaine agricole",
                    "Entités manquantes pour une réponse précise"
                ]
            },
            "very_low": {
                "score_range": "0-29%",
                "description": "Réponse incertaine, vérification nécessaire",
                "examples": [
                    "Erreur système",
                    "Question hors domaine agricole",
                    "Échec de tous les systèmes de réponse"
                ]
            }
        },
        "factors_affecting_confidence": [
            "Type de source (table > CoT > RAG > fallback IA)",
            "Complétude du contexte (espèce, lignée, âge, sexe)",
            "Validation du domaine agricole",
            "Qualité de classification de l'intention",
            "Nombre et qualité des sources RAG",
            "Précision des entités extraites"
        ],
        "confidence_components": {
            "source_reliability": "Fiabilité de la source de données (40% pour lookup, 30% pour CoT, etc.)",
            "intent_confidence": "Confiance dans la classification de l'intention",
            "completeness_score": "Complétude des informations contextuelles",
            "validation_confidence": "Confiance de la validation du domaine agricole"
        }
    }
