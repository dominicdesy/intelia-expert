# -*- coding: utf-8 -*-
"""
Système de Confidence Score Unifié
Combine tous les scores partiels en un score global cohérent pour l'API Expert
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ConfidenceLevel(str, Enum):
    """Niveaux de confiance standardisés"""
    VERY_HIGH = "very_high"      # 90-100%
    HIGH = "high"                # 70-89%
    MEDIUM = "medium"            # 50-69%
    LOW = "low"                  # 30-49%
    VERY_LOW = "very_low"        # 0-29%

@dataclass
class ConfidenceBreakdown:
    """Détail des composants du score unifié"""
    unified_score: float
    level: ConfidenceLevel
    components: Dict[str, float]
    factors: Dict[str, Any]
    explanation: str

# ===== POIDS DES COMPOSANTS SELON LE TYPE DE RÉPONSE =====

COMPONENT_WEIGHTS = {
    # Type de réponse: {composant: poids}
    "table_lookup": {
        "source_reliability": 0.4,      # Données précises = haute fiabilité
        "completeness_score": 0.3,      # Entités complètes importantes
        "validation_confidence": 0.2,   # Validation agricole
        "intent_confidence": 0.1        # Intention moins critique
    },
    "cot_analysis": {
        "source_reliability": 0.3,      # Analyse structurée
        "intent_confidence": 0.3,       # Classification critique
        "completeness_score": 0.2,      # Contexte important
        "validation_confidence": 0.2    # Domaine agricole
    },
    "openai_fallback": {
        "intent_confidence": 0.4,       # Classification critique pour fallback
        "validation_confidence": 0.3,   # Domaine agricole essentiel
        "completeness_score": 0.2,      # Contexte utile
        "source_reliability": 0.1       # Source AI moins fiable
    },
    "rag_retriever": {
        "source_reliability": 0.35,     # Qualité documents RAG
        "intent_confidence": 0.25,      # Classification importante
        "completeness_score": 0.25,     # Contexte pour recherche
        "validation_confidence": 0.15   # Domaine agricole
    },
    "hybrid_ui": {
        "intent_confidence": 0.4,       # Classification essentielle
        "validation_confidence": 0.3,   # Domaine agricole
        "completeness_score": 0.2,      # Par définition incomplet
        "source_reliability": 0.1       # Interface, pas données
    },
    "compute": {
        "completeness_score": 0.4,      # Paramètres de calcul cruciaux
        "source_reliability": 0.3,      # Formules fiables
        "validation_confidence": 0.2,   # Domaine agricole
        "intent_confidence": 0.1        # Calcul = intention claire
    }
}

# ===== SOURCES DE FIABILITÉ =====

SOURCE_RELIABILITY_SCORES = {
    "table_lookup": 0.95,        # Données tabulaires précises
    "cot_analysis": 0.85,        # Analyse structurée
    "rag_retriever": 0.75,       # Documents techniques
    "compute": 0.90,             # Calculs mathématiques
    "openai_fallback": 0.65,     # IA générative
    "hybrid_ui": 0.80,           # Interface guidée
    "perf_store": 0.95,          # Données performance
    "formulas": 0.90             # Formules validées
}

# ===== FONCTION PRINCIPALE =====

def calculate_unified_confidence(
    result: Dict[str, Any],
    intent_analysis: Optional[Dict[str, Any]] = None,
    completeness_analysis: Optional[Dict[str, Any]] = None,
    validation_result: Optional[Dict[str, Any]] = None
) -> ConfidenceBreakdown:
    """
    Calcule le score de confiance unifié pour une réponse
    
    Args:
        result: Résultat du dialogue_manager
        intent_analysis: Analyse de confiance des intentions
        completeness_analysis: Analyse de complétude
        validation_result: Résultat validation agricole
        
    Returns:
        ConfidenceBreakdown avec score unifié et détails
    """
    
    # 1. Déterminer le type de réponse
    response_type = _determine_response_type(result)
    logger.debug(f"🎯 Type de réponse détecté: {response_type}")
    
    # 2. Extraire les scores des composants
    components = _extract_component_scores(
        result, intent_analysis, completeness_analysis, validation_result
    )
    
    # 3. Obtenir les poids pour ce type de réponse
    weights = COMPONENT_WEIGHTS.get(response_type, COMPONENT_WEIGHTS["rag_retriever"])
    
    # 4. Calculer le score pondéré
    unified_score = _calculate_weighted_score(components, weights)
    
    # 5. Appliquer les ajustements contextuels
    adjusted_score = _apply_contextual_adjustments(unified_score, result, components)
    
    # 6. Déterminer le niveau de confiance
    confidence_level = _categorize_confidence_level(adjusted_score)
    
    # 7. Générer l'explication
    explanation = _generate_explanation(adjusted_score, confidence_level, response_type, components)
    
    # 8. Facteurs additionnels pour debug
    factors = _extract_confidence_factors(result, components, weights)
    
    return ConfidenceBreakdown(
        unified_score=round(adjusted_score, 1),
        level=confidence_level,
        components=components,
        factors=factors,
        explanation=explanation
    )

# ===== FONCTIONS UTILITAIRES =====

def _determine_response_type(result: Dict[str, Any]) -> str:
    """Détermine le type de réponse basé sur la structure du résultat"""
    
    # Vérifier le type explicite
    if result.get("type") == "partial_answer":
        return "hybrid_ui"
    
    # Vérifier la route prise
    route = result.get("route_taken", "")
    if route in ["perfstore_hit", "table_lookup"]:
        return "table_lookup"
    elif route in ["cot_analysis_priority", "cot_analysis"]:
        return "cot_analysis"
    elif route == "compute":
        return "compute"
    elif route == "hybrid_synthesis_clarification":
        return "hybrid_ui"
    
    # Vérifier la source de la réponse
    answer = result.get("answer", {})
    if isinstance(answer, dict):
        source = answer.get("source", "")
        if source == "table_lookup":
            return "table_lookup"
        elif source == "cot_analysis":
            return "cot_analysis"
        elif source == "openai_fallback":
            return "openai_fallback"
        elif source in ["rag_retriever", "rag"]:
            return "rag_retriever"
        elif source == "computation":
            return "compute"
        elif source in ["hybrid_ui", "clarification"]:
            return "hybrid_ui"
    
    # Fallback par défaut
    return "rag_retriever"

def _extract_component_scores(
    result: Dict[str, Any],
    intent_analysis: Optional[Dict[str, Any]],
    completeness_analysis: Optional[Dict[str, Any]],
    validation_result: Optional[Dict[str, Any]]
) -> Dict[str, float]:
    """Extrait les scores des différents composants"""
    
    components = {}
    
    # 1. Source Reliability (basé sur le type de source)
    response_type = _determine_response_type(result)
    components["source_reliability"] = SOURCE_RELIABILITY_SCORES.get(response_type, 0.7)
    
    # Ajustement selon la qualité des sources RAG
    if response_type == "rag_retriever":
        answer = result.get("answer", {})
        sources = answer.get("sources", []) if isinstance(answer, dict) else []
        if len(sources) >= 3:
            components["source_reliability"] += 0.1  # Bonus sources multiples
        elif len(sources) == 0:
            components["source_reliability"] -= 0.2  # Malus pas de sources
    
    # 2. Intent Confidence
    if intent_analysis and isinstance(intent_analysis, dict):
        # Depuis intent_confidence.py
        intent_conf = intent_analysis.get("confidence_factors", {}).get("confidence_level", "medium")
        components["intent_confidence"] = _convert_level_to_score(intent_conf)
    else:
        # Estimation basée sur le type de réponse
        components["intent_confidence"] = 0.7  # Défaut moyen
    
    # 3. Completeness Score
    if completeness_analysis and isinstance(completeness_analysis, dict):
        # Depuis clarification_manager.py
        components["completeness_score"] = completeness_analysis.get("completeness_score", 0.5)
    else:
        # Estimation basée sur la présence d'entités dans result
        entities = result.get("entities", {})
        if entities:
            filled_entities = sum(1 for v in entities.values() if v is not None and v != "")
            total_entities = len(entities)
            components["completeness_score"] = filled_entities / total_entities if total_entities > 0 else 0.5
        else:
            components["completeness_score"] = 0.5
    
    # 4. Validation Confidence
    if validation_result and isinstance(validation_result, dict):
        # Depuis agricultural_domain_validator
        if validation_result.get("is_valid", False):
            components["validation_confidence"] = validation_result.get("confidence", 100.0) / 100.0
        else:
            components["validation_confidence"] = 0.3  # Question rejetée mais pas bloquée
    else:
        # Pas de validation = supposer valide avec confiance moyenne
        components["validation_confidence"] = 0.75
    
    # Normaliser tous les scores entre 0 et 1
    for key, value in components.items():
        components[key] = max(0.0, min(1.0, float(value)))
    
    return components

def _convert_level_to_score(level: str) -> float:
    """Convertit un niveau textuel en score numérique"""
    level_mapping = {
        "very_high": 0.9,
        "high": 0.75,
        "medium": 0.6,
        "low": 0.4,
        "very_low": 0.2
    }
    return level_mapping.get(level, 0.6)

def _calculate_weighted_score(components: Dict[str, float], weights: Dict[str, float]) -> float:
    """Calcule le score pondéré des composants"""
    
    weighted_sum = 0.0
    total_weight = 0.0
    
    for component, weight in weights.items():
        if component in components:
            weighted_sum += components[component] * weight
            total_weight += weight
        else:
            logger.warning(f"⚠️ Composant manquant: {component}")
    
    # Normaliser si poids total différent de 1.0
    if total_weight > 0:
        return weighted_sum / total_weight
    else:
        return 0.5  # Fallback si aucun composant

def _apply_contextual_adjustments(
    base_score: float, 
    result: Dict[str, Any], 
    components: Dict[str, float]
) -> float:
    """Applique des ajustements contextuels au score"""
    
    adjusted_score = base_score
    
    # 1. Bonus pour réponses avec données exactes
    answer = result.get("answer", {})
    if isinstance(answer, dict):
        if answer.get("source") == "table_lookup":
            meta = answer.get("meta", {})
            if meta.get("lookup") and "line" in str(meta.get("lookup", {})):
                adjusted_score += 0.05  # Bonus données précises
    
    # 2. Malus pour réponses de clarification
    if result.get("type") == "partial_answer":
        adjusted_score -= 0.1  # Réponse incomplète
    
    # 3. Bonus pour haute complétude avec bonne source
    if (components.get("completeness_score", 0) > 0.8 and 
        components.get("source_reliability", 0) > 0.85):
        adjusted_score += 0.08  # Synergie complétude + source fiable
    
    # 4. Malus pour faible validation agricole
    if components.get("validation_confidence", 1.0) < 0.5:
        adjusted_score -= 0.15  # Question hors domaine
    
    # 5. Bonus pour sources multiples (RAG)
    if isinstance(answer, dict):
        sources = answer.get("sources", [])
        if len(sources) >= 4:
            adjusted_score += 0.05
    
    # 6. Malus pour fallback après échec
    route = result.get("route_taken", "")
    if "fallback" in route.lower():
        adjusted_score -= 0.1
    
    return max(0.0, min(1.0, adjusted_score))

def _categorize_confidence_level(score: float) -> ConfidenceLevel:
    """Convertit un score numérique en niveau de confiance"""
    
    if score >= 0.9:
        return ConfidenceLevel.VERY_HIGH
    elif score >= 0.7:
        return ConfidenceLevel.HIGH
    elif score >= 0.5:
        return ConfidenceLevel.MEDIUM
    elif score >= 0.3:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.VERY_LOW

def _generate_explanation(
    score: float, 
    level: ConfidenceLevel, 
    response_type: str, 
    components: Dict[str, float]
) -> str:
    """Génère une explication humaine du score de confiance"""
    
    explanations = {
        ConfidenceLevel.VERY_HIGH: "Réponse très fiable avec données précises et contexte complet",
        ConfidenceLevel.HIGH: "Réponse fiable basée sur des sources techniques solides",
        ConfidenceLevel.MEDIUM: "Réponse correcte mais avec certaines limitations contextuelles",
        ConfidenceLevel.LOW: "Réponse approximative, précisions recommandées",
        ConfidenceLevel.VERY_LOW: "Réponse incertaine, vérification nécessaire"
    }
    
    base_explanation = explanations.get(level, "Niveau de confiance indéterminé")
    
    # Enrichir avec des détails spécifiques
    details = []
    
    if response_type == "table_lookup":
        details.append("données tabulaires exactes")
    elif response_type == "cot_analysis":
        details.append("analyse structurée")
    elif response_type == "compute":
        details.append("calculs mathématiques")
    elif response_type == "openai_fallback":
        details.append("réponse générée par IA")
    
    if components.get("completeness_score", 0) > 0.8:
        details.append("contexte complet")
    elif components.get("completeness_score", 0) < 0.4:
        details.append("informations manquantes")
    
    if components.get("validation_confidence", 1) < 0.5:
        details.append("domaine non validé")
    
    if details:
        return f"{base_explanation} ({', '.join(details)})"
    else:
        return base_explanation

def _extract_confidence_factors(
    result: Dict[str, Any], 
    components: Dict[str, float], 
    weights: Dict[str, float]
) -> Dict[str, Any]:
    """Extrait les facteurs pour debugging et monitoring"""
    
    return {
        "response_type": _determine_response_type(result),
        "component_weights": weights,
        "top_component": max(components.items(), key=lambda x: x[1])[0] if components else None,
        "lowest_component": min(components.items(), key=lambda x: x[1])[0] if components else None,
        "has_sources": bool(result.get("answer", {}).get("sources")) if isinstance(result.get("answer"), dict) else False,
        "route_taken": result.get("route_taken", "unknown"),
        "intent": str(result.get("intent", "unknown"))
    }

# ===== FONCTIONS UTILITAIRES PUBLIQUES =====

def get_confidence_summary(confidence_breakdown: ConfidenceBreakdown) -> Dict[str, Any]:
    """Retourne un résumé simple pour l'API"""
    
    return {
        "score": confidence_breakdown.unified_score,
        "level": confidence_breakdown.level.value,
        "explanation": confidence_breakdown.explanation
    }

def get_detailed_confidence(confidence_breakdown: ConfidenceBreakdown) -> Dict[str, Any]:
    """Retourne les détails complets pour debugging"""
    
    return {
        "unified_score": confidence_breakdown.unified_score,
        "level": confidence_breakdown.level.value,
        "explanation": confidence_breakdown.explanation,
        "components": confidence_breakdown.components,
        "factors": confidence_breakdown.factors
    }

def analyze_confidence_trends(confidence_history: List[ConfidenceBreakdown]) -> Dict[str, Any]:
    """Analyse les tendances de confiance pour monitoring"""
    
    if not confidence_history:
        return {"status": "no_data"}
    
    scores = [cb.unified_score for cb in confidence_history]
    levels = [cb.level.value for cb in confidence_history]
    
    return {
        "average_score": round(sum(scores) / len(scores), 2),
        "score_trend": "improving" if scores[-1] > scores[0] else "declining" if scores[-1] < scores[0] else "stable",
        "most_common_level": max(set(levels), key=levels.count),
        "total_responses": len(confidence_history),
        "high_confidence_rate": sum(1 for s in scores if s >= 0.7) / len(scores)
    }

# ===== TESTS ET VALIDATION =====

def test_unified_confidence() -> Dict[str, Any]:
    """Test rapide du système de confidence unifié"""
    
    # Test case 1: Table lookup haute confiance
    test1 = {
        "type": "answer",
        "route_taken": "perfstore_hit",
        "answer": {
            "source": "table_lookup",
            "sources": [{"title": "Ross 308 Guide"}],
            "meta": {"lookup": {"line": "ross308", "sex": "male"}}
        }
    }
    
    confidence1 = calculate_unified_confidence(
        result=test1,
        completeness_analysis={"completeness_score": 0.9},
        validation_result={"is_valid": True, "confidence": 95.0}
    )
    
    # Test case 2: Fallback OpenAI
    test2 = {
        "type": "answer",
        "route_taken": "openai_fallback",
        "answer": {"source": "openai_fallback", "sources": []}
    }
    
    confidence2 = calculate_unified_confidence(
        result=test2,
        completeness_analysis={"completeness_score": 0.4},
        validation_result={"is_valid": True, "confidence": 80.0}
    )
    
    return {
        "status": "success",
        "test_cases": [
            {
                "name": "table_lookup_high_confidence",
                "score": confidence1.unified_score,
                "level": confidence1.level.value,
                "explanation": confidence1.explanation
            },
            {
                "name": "openai_fallback_medium_confidence", 
                "score": confidence2.unified_score,
                "level": confidence2.level.value,
                "explanation": confidence2.explanation
            }
        ],
        "system_ready": True
    }
