# -*- coding: utf-8 -*-
"""
Dialogue orchestration - CORRECTIONS FINALES
- classify -> normalize -> completeness/clarifications
- route to compute (when possible) OR to RAG (table-first)
- returns a structured payload for the frontend
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# ========== IMPORTS CORRIGÉS ==========
# 1. question_classifier: fonction classify (pas classify_question)
from ..utils.question_classifier import classify, Intention, REQUIRED_FIELDS_BY_TYPE

# 2. context_extractor: OK
from .context_extractor import normalize

# 3. clarification_manager: doit utiliser REQUIRED_FIELDS_BY_TYPE d'ici
from .clarification_manager import compute_completeness

# 4. rag_engine: dans le même dossier pipeline
try:
    from .rag_engine import answer_with_rag
    RAG_AVAILABLE = True
    logger.info("✅ RAG engine imported from pipeline")
except ImportError:
    logger.warning("⚠️ RAG engine not found in pipeline, using fallback")
    RAG_AVAILABLE = False
    
    def answer_with_rag(question: str, entities: Dict[str, Any], intent=None) -> Dict[str, Any]:
        return {
            "text": f"Réponse RAG pour: {question[:50]}...",
            "source": "fallback_rag",
            "confidence": 0.8
        }

# 5. formulas: import avec fallback
try:
    from ..utils import formulas
    FORMULAS_AVAILABLE = True
    logger.info("✅ Formulas imported")
except ImportError:
    logger.warning("⚠️ Formulas not available, using fallback")
    FORMULAS_AVAILABLE = False
    
    # Fallback formulas simples
    class formulas:
        @staticmethod
        def conso_eau_j(eff, age, temp):
            return eff * (0.5 + age * 0.1)  # Approximation
        
        @staticmethod
        def dimension_mangeoires(eff, age, type_):
            return eff * (2.5 + age * 0.1)  # Approximation
        
        @staticmethod
        def dimension_abreuvoirs(eff, age, type_):
            return eff // 10  # Approximation
        
        @staticmethod
        def vent_min_m3h_par_kg(age, saison):
            return 0.8 if saison == "hiver" else 1.2
        
        @staticmethod
        def vent_min_total_m3h(poids, eff, age, saison):
            return poids * eff * 0.8
        
        @staticmethod
        def setpoint_temp_C_broiler(age):
            return max(18, 35 - age * 0.4)
        
        @staticmethod
        def setpoint_hr_pct(age):
            return 65
        
        @staticmethod
        def co2_max_ppm():
            return 3000
        
        @staticmethod
        def nh3_max_ppm():
            return 20
        
        @staticmethod
        def lux_program_broiler(age):
            return 20 if age > 7 else 40
        
        @staticmethod
        def cout_total_aliment(eff, poids, fcr, prix, survie):
            return eff * poids * fcr * (prix / 1000) * (survie / 100)
        
        @staticmethod
        def cout_aliment_par_kg_vif(prix, fcr):
            return (prix / 1000) * fcr

def _should_compute(intent: Intention) -> bool:
    return intent in {
        Intention.WaterFeedIntake,
        Intention.EquipmentSizing,
        Intention.VentilationSizing,
        Intention.EnvSetpoints,
        Intention.Economics
    }

def _compute_answer(intent: Intention, entities: Dict[str, Any]) -> Dict[str, Any]:
    ans = {"text": "", "values": {}}
    
    try:
        if intent == Intention.WaterFeedIntake:
            eff = entities.get("flock_size") or 1000
            age = entities.get("age_days") or (entities.get("age_weeks", 0) * 7)
            ans["values"]["water_L_per_day"] = formulas.conso_eau_j(eff, age or 0, 20.0)
            ans["text"] = "Estimation de la consommation d'eau quotidienne (flock)."
        elif intent == Intention.EquipmentSizing:
            eff = entities.get("flock_size") or 1000
            age = entities.get("age_days") or (entities.get("age_weeks", 0) * 7)
            ans["values"]["feeder_space_cm"] = formulas.dimension_mangeoires(eff, age or 0, 'chaîne')
            ans["values"]["drinkers"] = formulas.dimension_abreuvoirs(eff, age or 0, 'nipple')
            ans["text"] = "Dimensionnement mangeoires/abreuvoirs (ordre de grandeur)."
        elif intent == Intention.VentilationSizing:
            eff = entities.get("flock_size") or 1000
            age = entities.get("age_days") or (entities.get("age_weeks", 0) * 7)
            poids_moy = entities.get("avg_weight_kg") or 1.5
            saison = entities.get("season") or "hiver"
            ans["values"]["vent_min_m3h_per_kg"] = formulas.vent_min_m3h_par_kg(age or 0, saison)
            ans["values"]["vent_min_total_m3h"] = formulas.vent_min_total_m3h(poids_moy, eff, age or 0, saison)
            ans["text"] = "Ventilation minimale recommandée (m³/h)."
        elif intent == Intention.EnvSetpoints:
            age = entities.get("age_days") or (entities.get("age_weeks", 0) * 7)
            ans["values"]["temp_C"] = formulas.setpoint_temp_C_broiler(age or 0)
            ans["values"]["rh_pct"] = formulas.setpoint_hr_pct(age or 0)
            ans["values"]["co2_max_ppm"] = formulas.co2_max_ppm()
            ans["values"]["nh3_max_ppm"] = formulas.nh3_max_ppm()
            ans["values"]["lux"] = formulas.lux_program_broiler(age or 0)
            ans["text"] = "Consignes environnementales génériques."
        elif intent == Intention.Economics:
            eff = entities.get("flock_size") or 1000
            prix = entities.get("feed_price") or 450.0
            fcr = entities.get("FCR") or 1.7
            poids = entities.get("target_weight") or 2.2
            ans["values"]["feed_cost_total"] = formulas.cout_total_aliment(eff, poids, fcr, prix, 95.0)
            ans["values"]["feed_cost_per_kg"] = formulas.cout_aliment_par_kg_vif(prix, fcr)
            ans["text"] = "Estimation des coûts d'aliment."
        else:
            ans["text"] = "Calcul effectué."
    except Exception as e:
        logger.error(f"❌ Error in _compute_answer: {e}")
        ans["text"] = f"Erreur dans le calcul pour {intent}"
        ans["error"] = str(e)
    
    return ans

def handle(session_id: str, question: str, lang: str="fr") -> Dict[str, Any]:
    """
    Fonction principale de traitement des questions
    """
    try:
        logger.info(f"🤖 Processing question: {question[:50]}...")
        
        # Étape 1: Classification
        classification = classify(question)
        logger.debug(f"Classification: {classification}")
        
        # Étape 2: Normalisation
        classification = normalize(classification)
        intent: Intention = classification["intent"]
        entities = classification["entities"]
        
        logger.info(f"Intent: {intent}, Entities: {list(entities.keys())}")

        # Étape 3: Vérification de complétude
        completeness = compute_completeness(intent, entities)
        if completeness["missing_fields"] and completeness["completeness_score"] < 0.8:
            logger.info(f"Need clarification, score: {completeness['completeness_score']}")
            return {
                "type": "clarification",
                "intent": intent,
                "completeness_score": completeness["completeness_score"],
                "missing_fields": completeness["missing_fields"],
                "follow_up_questions": completeness["follow_up_questions"]
            }

        # Étape 4: Calcul direct si possible
        if _should_compute(intent):
            logger.info(f"Computing answer for intent: {intent}")
            result = _compute_answer(intent, entities)
            return {
                "type": "answer",
                "intent": intent,
                "answer": result,
                "route_taken": "compute"
            }

        # Étape 5: RAG comme fallback
        logger.info(f"Using RAG for intent: {intent}")
        try:
            rag = answer_with_rag(question, entities, intent=intent)
            return {
                "type": "answer",
                "intent": intent,
                "answer": rag,
                "route_taken": "rag"
            }
        except Exception as e:
            logger.error(f"❌ RAG error: {e}")
            # Fallback ultime
            return {
                "type": "answer",
                "intent": intent,
                "answer": {
                    "text": f"Je traite votre question sur {intent}. Le système RAG rencontre un problème temporaire.",
                    "source": "fallback"
                },
                "route_taken": "fallback"
            }
    
    except Exception as e:
        logger.exception(f"❌ Critical error in handle(): {e}")
        return {
            "type": "error",
            "error": str(e),
            "message": "Une erreur inattendue s'est produite lors du traitement de votre question."
        }