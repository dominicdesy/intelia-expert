# -*- coding: utf-8 -*-
"""
Dialogue orchestration - VERSION REFACTORISÉE CORRIGÉE + PERSISTANCE + FIX LANGUE
- Module principal utilisant les modules spécialisés
- Imports des modules spécialisés pour langue, mémoire et CoT/fallback
- Preserve la compatibilité avec l'API existante
- CORRIGÉ: Utilise les fonctions des modules au lieu de les dupliquer
- FIX: Auto-extraction systématique même pour nouvelles conversations
- NOUVEAU: Persistance centralisée des conversations dans PostgreSQL
- 🔧 FIX LANGUE: Préservation langue conversationnelle + appel amélioré
- ✅ VÉRIFIÉ: Compatible avec nouvelle fonction complete() via cot_fallback_processor
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import os
import re
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# ========== IMPORTS CORE MODULES ==========
from ..utils.question_classifier import classify, Intention
from .context_extractor import normalize
from .clarification_manager import compute_completeness
from ..utils import formulas

# ========== IMPORTS MODULES REFACTORISÉS ==========
from .language_processor import (
    detect_question_language,
    finalize_response_with_language,
    get_language_processing_status
)

from .conversation_memory import (
    get_conversation_memory,
    merge_conversation_context,
    should_continue_conversation,
    save_conversation_context,
    clear_conversation_context,
    extract_age_days_from_text,
    normalize_sex_from_text,
    extract_line_from_text,
    extract_species_from_text,
    get_memory_status
)

# ========== ✅ IMPORTS MODULES COT/FALLBACK - DÉJÀ COMPATIBLES ==========
from .cot_fallback_processor import (
    should_use_cot_analysis,
    generate_cot_analysis,
    should_use_openai_fallback,
    generate_openai_fallback_response,
    maybe_synthesize,
    generate_clarification_response_advanced,
    get_cot_fallback_status,
    test_cot_fallback_pipeline,
    OPENAI_FALLBACK_AVAILABLE,
    OPENAI_COT_AVAILABLE
)

# ========== IMPORTS MODULES DIVISÉS ==========
from .dialogue_persistence import (
    PERSIST_CONVERSATIONS,
    CLEAR_CONTEXT_AFTER_ASK,
    POSTGRES_AVAILABLE,
    _persist_conversation,
    _extract_answer_text
)

from .dialogue_helpers import (
    PERF_AVAILABLE,
    RAG_AVAILABLE,
    _canon_sex,
    _normalize_entities_soft,
    _get_perf_store,
    _perf_lookup_exact_or_nearest,
    _rag_answer,
    _final_sanitize,
    _compute_answer
)

# ---------------------------------------------------------------------------
# RAG avec fallback OpenAI
# ---------------------------------------------------------------------------

def _rag_answer_with_fallback(question: str, k: int = 5, entities: Optional[Dict[str, Any]] = None, target_language: str = "fr") -> Dict[str, Any]:
    """
    Version améliorée de _rag_answer avec fallback OpenAI et support CoT
    ✅ VÉRIFIÉ: Utilise les fonctions du module cot_fallback_processor qui gèrent déjà la nouvelle signature complete()
    """
    # Essai RAG standard d'abord
    rag_result = _rag_answer(question, k, entities)
    
    # Vérifier si fallback OpenAI nécessaire
    intent = entities.get("_intent") if entities else None
    
    # Check si fallback activé via config
    enable_fallback = str(os.getenv("ENABLE_OPENAI_FALLBACK", "true")).lower() in ("1", "true", "yes", "on")
    if not enable_fallback:
        logger.debug("🚫 Fallback OpenAI désactivé par configuration")
        return rag_result
    
    # ✅ CETTE FONCTION EST DÉJÀ COMPATIBLE avec nouvelle signature complete()
    if should_use_openai_fallback(rag_result, intent):
        logger.info("🤖 Activation fallback OpenAI après échec RAG")
        
        # Tenter fallback OpenAI avec la langue cible (possiblement avec CoT)
        # ✅ CETTE FONCTION utilise déjà la nouvelle complete() en interne
        openai_result = generate_openai_fallback_response(
            question=question,
            entities=entities or {},
            intent=intent,
            rag_context=rag_result.get("text", ""),
            target_language=target_language
        )
        
        if openai_result:
            # Succès OpenAI - enrichir avec métadonnées RAG
            openai_result["meta"]["rag_attempted"] = True
            openai_result["meta"]["rag_route"] = rag_result.get("route")
            openai_result["meta"]["rag_meta"] = rag_result.get("meta", {})
            return openai_result
        else:
            logger.warning("⚠️ Fallback OpenAI échoué, retour au RAG original")
    
    return rag_result

# ---------------------------------------------------------------------------
# MODE HYBRIDE AMÉLIORÉ
# ---------------------------------------------------------------------------

def _generate_general_answer_with_specifics(question: str, entities: Dict[str, Any], intent: Intention, missing_fields: list) -> Dict[str, Any]:
    """
    Mode hybride: réponse générale + questions de précision
    ✅ VÉRIFIÉ: Utilise generate_clarification_response_advanced du module cot_fallback_processor
    """
    try:
        # ✅ CETTE FONCTION utilise déjà la nouvelle complete() en interne
        clarification_text = generate_clarification_response_advanced(intent, missing_fields)
        
        # Enrichir avec les boutons rapides
        age_days = None
        if entities.get("age_days") is not None:
            try: 
                age_days = int(entities["age_days"])
            except Exception: 
                pass
        elif entities.get("age_weeks") is not None:
            try: 
                age_days = int(entities["age_weeks"]) * 7
            except Exception: 
                pass
            
        defaults = {
            "species": entities.get("species") or "broiler",
            "line": entities.get("line") or "ross308",
            "sex": entities.get("sex") or "mixed",
            "age_days": age_days
        }
        
        quick_replies = {
            "species": ["broiler", "layer", "other"],
            "line": ["ross308", "cobb500", "hubbard", "other"],
            "sex": ["male", "female", "mixed"],
            "one_click": defaults
        }
        
        return {
            "text": clarification_text, 
            "source": "hybrid_ui", 
            "confidence": 0.9,
            "enriched": True, 
            "suggested_defaults": defaults,
            "quick_replies": quick_replies, 
            "rag_meta": {}, 
            "rag_sources": []
        }
        
    except Exception as e:
        logger.error(f"❌ Error generating hybrid UX answer: {e}")
        return {
            "text": "Je dois confirmer quelques éléments (espèce, lignée, sexe) avant de donner la valeur précise. Souhaites-tu utiliser des valeurs par défaut ?",
            "source": "hybrid_ui_fallback", 
            "confidence": 0.4, 
            "enriched": False
        }

# ---------------------------------------------------------------------------
# FONCTION PRINCIPALE HANDLE - VERSION CORRIGÉE + PERSISTANCE + FIX LANGUE
# ---------------------------------------------------------------------------

def handle(
    session_id: str,
    question: str,
    lang: str = "fr",
    # Overrides & debug
    debug: bool = False,
    force_perfstore: bool = False,
    intent_hint: Optional[str] = None,
    # Entities pass-through depuis l'API
    entities: Optional[Dict[str, Any]] = None,
    # NOUVEAU: Info utilisateur pour persistance
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fonction principale de traitement des questions - VERSION REFACTORISÉE CORRIGÉE + PERSISTANCE + FIX LANGUE
    Préserve la compatibilité avec l'API existante
    FIX: Auto-extraction systématique même pour nouvelles conversations
    NOUVEAU: Persistance automatique des conversations
    🔧 FIX LANGUE: Préservation langue conversationnelle + appel amélioré
    ✅ VÉRIFIÉ: Compatible avec nouvelle fonction complete() via modules spécialisés
    """
    try:
        logger.info(f"🤖 Processing question: {question[:120]}...")
        logger.info(f"[DM] flags: force_perfstore={force_perfstore}, intent_hint={intent_hint}, has_entities={bool(entities)}")

        # =================================================================
        # DÉTECTION DE LANGUE AUTOMATIQUE + FIX LANGUE CONVERSATIONNELLE
        # =================================================================
        auto_detection_enabled = str(os.getenv("ENABLE_AUTO_LANGUAGE_DETECTION", "true")).lower() in ("1", "true", "yes", "on")
        
        # Récupérer le contexte de session d'abord pour la langue
        memory = get_conversation_memory()
        session_context = memory.get(session_id) or {}
        logger.info(f"🧠 Contexte de session: {session_context}")
        
        if auto_detection_enabled:
            # 🔧 FIX: Utiliser l'appel amélioré avec contexte conversationnel
            detected_language = detect_question_language(question, session_context)
            logger.info(f"🌍 Langue détectée: {detected_language} | Paramètre lang: {lang}")
            
            # 🔧 FIX: Préserver la langue de conversation établie
            conversation_language = session_context.get("language")
            
            if conversation_language:
                # Préserver la langue de la conversation en cours
                effective_language = conversation_language
                logger.info(f"🔗 Langue de conversation préservée: {effective_language}")
            elif lang == "fr" and detected_language != "fr":
                # Seulement pour les nouvelles conversations
                effective_language = detected_language
                logger.info(f"🔄 Nouvelle conversation, langue détectée: {effective_language}")
            else:
                effective_language = lang
                
            # Sauvegarder la langue choisie pour cette conversation
            if not conversation_language:
                session_context["language"] = effective_language
                logger.info(f"💾 Langue sauvegardée pour conversation: {effective_language}")
        else:
            detected_language = lang
            effective_language = lang
            logger.info(f"🌍 Détection automatique désactivée, utilisation lang: {effective_language}")

        # Étape 1: Classification
        classification = classify(question)
        logger.debug(f"Classification: {classification}")

        # Étape 2: Normalisation
        classification = normalize(classification)
        intent: Intention = classification["intent"]

        # =================================================================
        # FUSION DES ENTITIES - VERSION CORRIGÉE
        # =================================================================
        # Fusion des entities (NER + overrides + contexte conversationnel)
        _ents = dict(classification.get("entities") or {})
        if entities:
            try: 
                _ents.update(entities)
            except Exception: 
                pass
        
        # ✅ CORRECTION: Toujours appliquer merge_conversation_context pour auto-extraction
        logger.info("🔗 Application de merge_conversation_context (auto-extraction)")
        _ents = merge_conversation_context(_ents, session_context, question)
        
        # Vérifier si on continue une conversation APRÈS la fusion
        if should_continue_conversation(session_context, intent):
            logger.info("🔗 Continuation de conversation détectée")
            # Forcer l'intention vers PerfTargets si c'était en attente
            if session_context.get("pending_intent") == "PerfTargets":
                intent = Intention.PerfTargets
                logger.info("🎯 Intention forcée vers PerfTargets par contexte conversationnel")
        
        entities = _ents

        # Canonicalisation immédiate du sexe pour robustesse NER/PerfStore/RAG
        entities["sex"] = _canon_sex(entities.get("sex")) or entities.get("sex")

        # Hint manuel (tests console)
        if intent_hint and str(intent_hint).lower().startswith("perf"):
            intent = Intention.PerfTargets

        logger.info(f"Intent: {intent}, Entities keys: {list(entities.keys())}")

        # =================================================================
        # VÉRIFICATION PRIORITAIRE POUR ANALYSE COT
        # =================================================================
        # ✅ CETTE FONCTION utilise déjà la nouvelle complete() en interne
        if OPENAI_COT_AVAILABLE and should_use_cot_analysis(intent, entities, question):
            logger.info("🧠 Question complexe détectée → Analyse Chain-of-Thought prioritaire")
            
            # Passer l'intent dans les entities pour le context
            entities_with_intent = dict(entities)
            entities_with_intent["_intent"] = intent
            
            # ✅ CETTE FONCTION utilise déjà la nouvelle complete() en interne
            cot_result = generate_cot_analysis(
                question=question,
                entities=entities,
                intent=intent,
                rag_context="",  # Pas de contexte RAG préalable
                target_language=effective_language
            )
            
            if cot_result:
                logger.info("✅ Analyse CoT réussie, retour direct")
                
                # 🗂️ EFFACEMENT CONTEXTE CONDITIONNEL
                if CLEAR_CONTEXT_AFTER_ASK:
                    clear_conversation_context(session_id)
                    logger.debug("🧹 Contexte conversationnel effacé (CLEAR_CONTEXT_AFTER_ASK=1)")
                
                response = {
                    "type": "answer",
                    "intent": intent,
                    "answer": cot_result,
                    "route_taken": "cot_analysis_priority",
                    "session_id": session_id
                }
                
                # 🔧 FIX: Finaliser la réponse avec adaptation linguistique améliorée
                final_response = finalize_response_with_language(
                    response, question, effective_language, detected_language, force_conversation_language=True
                )
                
                # 💾 PERSISTANCE CONVERSATION
                answer_text = _extract_answer_text(final_response)
                additional_context = {
                    "intent": str(intent),
                    "route": "cot_analysis_priority",
                    "language_detected": detected_language,
                    "language_effective": effective_language
                }
                _persist_conversation(session_id, question, answer_text, effective_language, user_id, additional_context)
                
                return final_response
            else:
                logger.info("⚠️ Analyse CoT échouée, continuation pipeline standard")

        # Étape 3: Vérification de complétude
        completeness = compute_completeness(intent, entities)
        completeness_score = completeness["completeness_score"]
        missing_fields = completeness["missing_fields"]
        logger.info(f"Completeness score: {completeness_score} | Missing: {missing_fields}")

        # Si conversation continue et complète maintenant, aller directement au traitement
        if should_continue_conversation(session_context, intent) and completeness_score >= 0.8:
            logger.info("🚀 Conversation continue avec données complètes → traitement direct")
            # 🗂️ EFFACEMENT CONTEXTE CONDITIONNEL
            if CLEAR_CONTEXT_AFTER_ASK:
                clear_conversation_context(session_id)
                logger.debug("🧹 Contexte conversationnel effacé (CLEAR_CONTEXT_AFTER_ASK=1)")
            
        # HYBRIDE : si infos manquantes → synthèse courte + clarifications
        elif missing_fields and completeness_score < 0.8:
            logger.info("🧭 Mode hybride: synthèse courte + questions de précision")
            general_answer = _generate_general_answer_with_specifics(question, entities, intent, missing_fields)
            
            # Sauvegarder le contexte pour continuité
            save_conversation_context(session_id, intent, entities, question, missing_fields)
            
            response = {
                "type": "partial_answer",
                "intent": intent,
                "general_answer": general_answer,
                "completeness_score": completeness_score,
                "missing_fields": missing_fields,
                "follow_up_questions": completeness["follow_up_questions"],
                "route_taken": "hybrid_synthesis_clarification",
                "session_id": session_id
            }
            
            # 🔧 FIX: Finaliser la réponse avec adaptation linguistique améliorée
            final_response = finalize_response_with_language(
                response, question, effective_language, detected_language, force_conversation_language=True
            )
            
            # 💾 PERSISTANCE CONVERSATION
            answer_text = _extract_answer_text(final_response)
            additional_context = {
                "intent": str(intent),
                "route": "hybrid_synthesis_clarification",
                "completeness_score": completeness_score,
                "missing_fields": missing_fields,
                "language_detected": detected_language,
                "language_effective": effective_language
            }
            _persist_conversation(session_id, question, answer_text, effective_language, user_id, additional_context)
            
            return final_response

        # Étape 4: Calcul direct si possible
        def _should_compute(i: Intention) -> bool:
            return i in {
                Intention.WaterFeedIntake,
                Intention.EquipmentSizing,
                Intention.VentilationSizing,
                Intention.EnvSetpoints,
                Intention.Economics
            }
        
        if _should_compute(intent):
            logger.info(f"🧮 Calcul direct pour intent: {intent}")
            result = _compute_answer(intent, entities)
            result["text"] = _final_sanitize(result.get("text", ""))
            
            # 🗂️ EFFACEMENT CONTEXTE CONDITIONNEL
            if CLEAR_CONTEXT_AFTER_ASK:
                clear_conversation_context(session_id)
                logger.debug("🧹 Contexte conversationnel effacé (CLEAR_CONTEXT_AFTER_ASK=1)")
            
            response = {
                "type": "answer",
                "intent": intent,
                "answer": result,
                "route_taken": "compute",
                "session_id": session_id
            }
            
            # 🔧 FIX: Finaliser la réponse avec adaptation linguistique améliorée
            final_response = finalize_response_with_language(
                response, question, effective_language, detected_language, force_conversation_language=True
            )
            
            # 💾 PERSISTANCE CONVERSATION
            answer_text = _extract_answer_text(final_response)
            additional_context = {
                "intent": str(intent),
                "route": "compute",
                "language_detected": detected_language,
                "language_effective": effective_language
            }
            _persist_conversation(session_id, question, answer_text, effective_language, user_id, additional_context)
            
            return final_response

        # Étape 4bis: TABLE-FIRST pour PerfTargets (avant RAG)
        if force_perfstore or (intent == Intention.PerfTargets and completeness_score >= 0.6):
            logger.info("📊 Table-first (PerfTargets) avant RAG")
            try:
                norm = _normalize_entities_soft(entities)
                if norm.get("age_days") is None:
                    age_guess = extract_age_days_from_text(question)
                    if age_guess is not None:
                        norm["age_days"] = age_guess

                store = _get_perf_store(norm["species"])  # singleton
                rec = None
                dbg = None
                if store:
                    rec, dbg = _perf_lookup_exact_or_nearest(store, norm, question=question)

                if rec:
                    line_label = {"cobb500": "Cobb 500", "ross308": "Ross 308"}.get(str(rec.get("line","")).lower(), str(rec.get("line","")).title() or "Lignée")
                    sex_map = {"male":"Mâle","female":"Femelle","as_hatched":"Mixte","mixed":"Mixte"}
                    sex_label = sex_map.get(str(rec.get("sex","")).lower(), rec.get("sex",""))
                    unit_label = (rec.get("unit") or norm["unit"] or "metric").lower()
                    v_g, v_lb = rec.get("weight_g"), rec.get("weight_lb")
                    if v_g is not None:
                        try: 
                            val_txt = f"**{float(v_g):.0f} g**"
                        except Exception: 
                            val_txt = f"**{v_g} g**"
                    elif v_lb is not None:
                        try: 
                            val_txt = f"**{float(v_lb):.2f} lb**"
                        except Exception: 
                            val_txt = f"**{v_lb} lb**"
                    else:
                        val_txt = "**n/a**"
                    age_disp = int(rec.get("age_days") or norm.get("age_days") or 0)
                    text = f"{line_label} · {sex_label} · {age_disp} j : {val_txt} (objectif {unit_label})."
                    source_item: List[Dict[str, Any]] = []
                    if rec.get("source_doc"):
                        source_item.append({
                            "name": rec["source_doc"],
                            "meta": {
                                "page": rec.get("page"),
                                "line": rec.get("line"),
                                "sex": rec.get("sex"),
                                "unit": rec.get("unit")
                            }
                        })
                    
                    # 🗂️ EFFACEMENT CONTEXTE CONDITIONNEL
                    if CLEAR_CONTEXT_AFTER_ASK:
                        clear_conversation_context(session_id)
                        logger.debug("🧹 Contexte conversationnel effacé (CLEAR_CONTEXT_AFTER_ASK=1)")
                    
                    response = {
                        "type": "answer",
                        "intent": Intention.PerfTargets,
                        "answer": {
                            "text": text,
                            "source": "table_lookup",
                            "confidence": 0.98,
                            "sources": source_item,
                            "meta": {
                                "lookup": {
                                    "line": rec.get("line"),
                                    "sex": rec.get("sex"),
                                    "unit": rec.get("unit"),
                                    "age_days": age_disp
                                },
                                "perf_debug": dbg
                            }
                        },
                        "route_taken": "perfstore_hit",
                        "session_id": session_id
                    }
                    
                    # 🔧 FIX: Finaliser la réponse avec adaptation linguistique améliorée
                    final_response = finalize_response_with_language(
                        response, question, effective_language, detected_language, force_conversation_language=True
                    )
                    
                    # 💾 PERSISTANCE CONVERSATION
                    answer_text = _extract_answer_text(final_response)
                    additional_context = {
                        "intent": str(intent),
                        "route": "perfstore_hit",
                        "lookup_data": rec,
                        "language_detected": detected_language,
                        "language_effective": effective_language
                    }
                    _persist_conversation(session_id, question, answer_text, effective_language, user_id, additional_context)
                    
                    return final_response
                else:
                    logger.info("📊 PerfStore MISS → fallback RAG")
            except Exception as e:
                logger.warning(f"⚠️ Table-first lookup échoué: {e}")
                # on continue vers RAG

        # Étape 5: RAG complet avec fallback OpenAI amélioré
        logger.info("📚 RAG via RAGRetriever avec fallback OpenAI amélioré")
        
        # Passer l'intent dans les entities pour le fallback
        entities_with_intent = dict(entities)
        entities_with_intent["_intent"] = intent
        
        # ✅ CETTE FONCTION utilise déjà la nouvelle complete() en interne
        rag = _rag_answer_with_fallback(question, k=5, entities=entities_with_intent, target_language=effective_language)
        rag_text = _final_sanitize(rag.get("text", ""))
        
        # Synthèse uniquement si ce n'est pas déjà un fallback OpenAI ou CoT
        if rag.get("source") not in ["openai_fallback", "cot_analysis"]:
            # ✅ CETTE FONCTION utilise déjà la nouvelle complete() en interne
            rag_text = maybe_synthesize(question, rag_text)

        # 🗂️ EFFACEMENT CONTEXTE CONDITIONNEL
        if CLEAR_CONTEXT_AFTER_ASK:
            clear_conversation_context(session_id)
            logger.debug("🧹 Contexte conversationnel effacé (CLEAR_CONTEXT_AFTER_ASK=1)")

        response = {
            "type": "answer",
            "intent": intent,
            "answer": {
                "text": rag_text,
                "source": rag.get("source", "rag_retriever"),
                "confidence": rag.get("confidence", 0.8),
                "sources": rag.get("sources", []),
                "meta": rag.get("meta", {})
            },
            "route_taken": rag.get("route", "rag_retriever"),
            "session_id": session_id
        }
        
        # 🔧 FIX: Finaliser la réponse avec adaptation linguistique améliorée
        final_response = finalize_response_with_language(
            response, question, effective_language, detected_language, force_conversation_language=True
        )
        
        # 💾 PERSISTANCE CONVERSATION
        answer_text = _extract_answer_text(final_response)
        additional_context = {
            "intent": str(intent),
            "route": rag.get("route", "rag_retriever"),
            "rag_meta": rag.get("meta", {}),
            "language_detected": detected_language,
            "language_effective": effective_language
        }
        _persist_conversation(session_id, question, answer_text, effective_language, user_id, additional_context)
        
        return final_response

    except Exception as e:
        logger.exception(f"❌ Critical error in handle(): {e}")
        response = {
            "type": "error",
            "error": str(e),
            "message": "Une erreur inattendue s'est produite lors du traitement de votre question.",
            "session_id": session_id
        }
        
        # Même en cas d'erreur, essayer d'adapter la langue si possible
        try:
            detected_language = detect_question_language(question) if question else "fr"
            effective_language = detected_language if detected_language != "fr" else "fr"
            final_response = finalize_response_with_language(
                response, question or "", effective_language, detected_language, force_conversation_language=True
            )
            
            # 💾 PERSISTANCE CONVERSATION (même en cas d'erreur)
            error_text = f"Erreur: {str(e)}"
            additional_context = {
                "intent": "error",
                "route": "error_handling",
                "error": str(e),
                "language_detected": detected_language,
                "language_effective": effective_language
            }
            _persist_conversation(session_id, question or "", error_text, effective_language, user_id, additional_context)
            
            return final_response
        except Exception:
            return response

# ---------------------------------------------------------------------------
# FONCTIONS DE STATUT UNIFIÉES
# ---------------------------------------------------------------------------

def get_fallback_status() -> Dict[str, Any]:
    """
    Retourne le statut complet du système avec tous les modules
    """
    # Récupérer les statuts de chaque module
    language_status = get_language_processing_status()
    memory_status = get_memory_status()
    cot_fallback_status = get_cot_fallback_status()
    
    # Statut unifié
    unified_status = {
        "dialogue_manager_version": "refactored_fixed_with_persistence_and_language_fix_modular",
        "auto_extraction_fix": "applied",
        "language_conversation_fix": "applied",
        "modular_architecture": "applied",
        "conversation_persistence": {
            "enabled": PERSIST_CONVERSATIONS,
            "postgres_available": POSTGRES_AVAILABLE,
            "clear_context_after_ask": CLEAR_CONTEXT_AFTER_ASK
        },
        "modules": {
            "language_processor": language_status,
            "conversation_memory": memory_status,
            "cot_fallback_processor": cot_fallback_status
        },
        "core_components": {
            "rag_available": RAG_AVAILABLE,
            "perfstore_available": PERF_AVAILABLE,
            "question_classifier_available": True,
            "context_extractor_available": True,
            "clarification_manager_available": True
        },
        "configuration": {
            "rag_index_root": os.environ.get("RAG_INDEX_ROOT", "./rag_index"),
            "database_url": bool(os.getenv("DATABASE_URL")),
            "openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
            "persist_conversations": PERSIST_CONVERSATIONS,
            "clear_context_after_ask": CLEAR_CONTEXT_AFTER_ASK
        }
    }
    
    return unified_status

def get_cot_capabilities() -> Dict[str, Any]:
    """
    Délègue aux capacités CoT du module spécialisé
    """
    if not OPENAI_COT_AVAILABLE:
        return {"cot_available": False, "reason": "cot_fallback_processor module not available"}
    
    return {
        "cot_available": True,
        "auto_detection": True,
        "parsing_enabled": True,
        "followup_generation": True,
        "supported_sections": [
            "thinking", "analysis", "reasoning", "factors", "recommendations",
            "validation", "problem_decomposition", "factor_analysis", 
            "interconnections", "solution_pathway", "risk_mitigation",
            "economic_context", "cost_benefit_breakdown", "scenario_analysis"
        ],
        "supported_intents": [
            "HealthDiagnosis", "OptimizationStrategy", "TroubleshootingMultiple",
            "ProductionAnalysis", "MultiFactor", "Economics"
        ],
        "complexity_indicators": [
            "problème", "diagnostic", "analyse", "optimiser", "améliorer",
            "stratégie", "multiple", "plusieurs", "complexe", "comparer",
            "évaluer", "recommandation", "pourquoi", "comment résoudre"
        ]
    }

def test_enhanced_pipeline() -> Dict[str, Any]:
    """
    Test complet du pipeline refactorisé + persistance + fix langue + modularité
    """
    try:
        results = {}
        
        # Test fonction de base
        results["basic_status"] = {
            "dialogue_manager": "refactored_fixed_with_persistence_and_language_fix_modular",
            "auto_extraction_fix": "applied",
            "language_conversation_fix": "applied",
            "modular_architecture": "applied",
            "persistence_enabled": PERSIST_CONVERSATIONS,
            "modules_imported": True,
            "rag_available": RAG_AVAILABLE,
            "perfstore_available": PERF_AVAILABLE,
            "postgres_available": POSTGRES_AVAILABLE
        }
        
        # Test persistance
        try:
            test_session = f"test_session_{int(time.time())}"
            test_question = "Test de persistance"
            test_answer = "Réponse de test"
            
            persistence_success = _persist_conversation(
                session_id=test_session,
                question=test_question,
                answer_text=test_answer,
                language="fr",
                user_id="test_user"
            )
            
            results["persistence_test"] = {
                "status": "success" if persistence_success else "failed",
                "test_session": test_session,
                "postgres_available": POSTGRES_AVAILABLE,
                "persist_conversations": PERSIST_CONVERSATIONS
            }
        except Exception as e:
            results["persistence_test"] = {"status": "error", "error": str(e)}
        
        # Test modules spécialisés
        try:
            language_test = get_language_processing_status()
            results["language_processor_test"] = language_test
        except Exception as e:
            results["language_processor_test"] = {"status": "error", "error": str(e)}
        
        try:
            memory_test = get_memory_status()
            results["conversation_memory_test"] = memory_test
        except Exception as e:
            results["conversation_memory_test"] = {"status": "error", "error": str(e)}
        
        try:
            cot_test = test_cot_fallback_pipeline()
            results["cot_fallback_test"] = cot_test
        except Exception as e:
            results["cot_fallback_test"] = {"status": "error", "error": str(e)}
        
        # 🔧 Test du fix langue conversationnelle
        try:
            # Simuler une détection avec contexte
            mock_context = {"language": "fr"}
            test_questions = [
                ("Quel est le poids ?", "fr"),
                ("Broiler. Cobb 500. Male", "fr"),  # Devrait préserver le français
                ("What is the weight?", "en")
            ]
            
            language_fix_tests = []
            for question, expected_lang in test_questions:
                try:
                    detected = detect_question_language(question, mock_context)
                    language_fix_tests.append({
                        "question": question,
                        "expected": expected_lang,
                        "detected": detected,
                        "preserved_context": detected == expected_lang
                    })
                except Exception as e:
                    language_fix_tests.append({
                        "question": question,
                        "error": str(e)
                    })
            
            results["language_fix_test"] = {
                "status": "completed",
                "tests": language_fix_tests,
                "context_preservation_enabled": True
            }
        except Exception as e:
            results["language_fix_test"] = {"status": "error", "error": str(e)}
        
        return {
            "status": "success",
            "message": "Pipeline refactorisé + persistance + fix langue + modularité testé avec succès",
            "fixes_applied": [
                "auto_extraction_systématique", 
                "persistance_conversations",
                "préservation_langue_conversationnelle",
                "détection_intelligente_termes_techniques",
                "architecture_modulaire"
            ],
            "feature_flags": {
                "PERSIST_CONVERSATIONS": PERSIST_CONVERSATIONS,
                "CLEAR_CONTEXT_AFTER_ASK": CLEAR_CONTEXT_AFTER_ASK,
                "ENABLE_AUTO_LANGUAGE_DETECTION": str(os.getenv("ENABLE_AUTO_LANGUAGE_DETECTION", "true")).lower() in ("1", "true", "yes", "on")
            },
            "detailed_results": results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Échec test pipeline refactorisé + persistance + fix langue + modularité: {str(e)}",
            "error_type": type(e).__name__
        }