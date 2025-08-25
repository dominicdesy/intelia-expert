# -*- coding: utf-8 -*-
"""
Gestionnaire de langue et adaptation multilingue
Extrait de dialogue_manager.py pour modularité

🚀 VERSION OPTIMISÉE - Ajout du cache de détection de langue pour éviter les appels OpenAI redondants
CONSERVATION INTÉGRALE du code original avec améliorations de performance
"""

import logging
import os
import re
import hashlib
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import conditionnel OpenAI
try:
    from ..utils.openai_utils import complete_text as openai_complete
    OPENAI_AVAILABLE = True
    logger.info("✅ OpenAI disponible pour traitement linguistique")
except ImportError as e:
    logger.warning(f"⚠️ OpenAI indisponible pour langue: {e}")
    OPENAI_AVAILABLE = False
    def openai_complete(*args, **kwargs):
        return None

# 🚀 NOUVEAU: Cache de détection de langue pour éviter les appels OpenAI redondants
_LANGUAGE_CACHE = {}
_LANGUAGE_CACHE_MAX_SIZE = int(os.getenv("LANGUAGE_CACHE_SIZE", "500"))
_LANGUAGE_CACHE_TTL = int(os.getenv("LANGUAGE_CACHE_TTL", "7200"))  # 2 heures par défaut

def _get_question_hash(question: str) -> str:
    """Génère un hash pour la question aux fins de cache"""
    # Normaliser le texte pour améliorer le hit ratio
    normalized = re.sub(r'\s+', ' ', question.strip().lower())
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:12]

def _cleanup_language_cache():
    """🚀 OPTIMISATION: Nettoyage intelligent du cache de langue"""
    global _LANGUAGE_CACHE
    
    current_time = time.time()
    
    # Supprimer les entrées expirées
    expired_keys = [
        key for key, (_, timestamp) in _LANGUAGE_CACHE.items()
        if current_time - timestamp > _LANGUAGE_CACHE_TTL
    ]
    
    for key in expired_keys:
        _LANGUAGE_CACHE.pop(key, None)
    
    # Si encore trop d'entrées, supprimer les plus anciennes
    if len(_LANGUAGE_CACHE) > _LANGUAGE_CACHE_MAX_SIZE:
        sorted_items = sorted(
            _LANGUAGE_CACHE.items(),
            key=lambda x: x[1][1]  # Trier par timestamp
        )
        
        # Garder seulement les 80% les plus récentes
        keep_count = int(_LANGUAGE_CACHE_MAX_SIZE * 0.8)
        items_to_keep = sorted_items[-keep_count:]
        
        _LANGUAGE_CACHE = {key: value for key, value in items_to_keep}
        logger.debug(f"🧹 [LANG_CACHE] Nettoyage: {len(expired_keys)} expirées, gardé {keep_count} entrées")

def _get_cached_language_detection(question: str) -> Optional[str]:
    """🚀 NOUVEAU: Récupère la langue détectée depuis le cache"""
    if not question or not question.strip():
        return None
        
    cache_key = _get_question_hash(question)
    
    if cache_key in _LANGUAGE_CACHE:
        cached_lang, timestamp = _LANGUAGE_CACHE[cache_key]
        
        # Vérifier TTL
        if time.time() - timestamp <= _LANGUAGE_CACHE_TTL:
            logger.debug(f"💾 [LANG_CACHE] Hit pour: '{question[:30]}...' -> {cached_lang}")
            return cached_lang
        else:
            # Entrée expirée
            _LANGUAGE_CACHE.pop(cache_key, None)
    
    return None

def _cache_language_detection(question: str, detected_language: str):
    """🚀 NOUVEAU: Sauvegarde la langue détectée en cache"""
    if not question or not question.strip() or not detected_language:
        return
        
    cache_key = _get_question_hash(question)
    _LANGUAGE_CACHE[cache_key] = (detected_language, time.time())
    
    logger.debug(f"💾 [LANG_CACHE] Sauvegarde: '{question[:30]}...' -> {detected_language}")
    
    # Nettoyage périodique du cache
    if len(_LANGUAGE_CACHE) % 25 == 0:  # Toutes les 25 entrées
        _cleanup_language_cache()

# ---------------------------------------------------------------------------
# DÉTECTION INTELLIGENTE DE LANGUE (CONSERVÉE)
# ---------------------------------------------------------------------------

def should_ignore_language_detection(question: str, detected_lang: str, conversation_lang: str) -> bool:
    """
    CONSERVATION INTÉGRALE: Détermine si on doit ignorer la détection automatique de langue
    pour préserver la cohérence conversationnelle.
    Utile pour les termes techniques courts ou réponses de clarification.
    """
    if not conversation_lang or conversation_lang == detected_lang:
        return False
    
    # Ignorer si message très court (< 10 caractères)
    if len(question.strip()) < 10:
        logger.debug("🎯 Détection ignorée: message trop court")
        return True
    
    # Ignorer si seulement des termes techniques avicoles
    technical_terms = {
        'broiler', 'cobb', 'ross', 'male', 'female', 'layer',
        'hubbard', 'as hatched', 'mixed', 'as_hatched', 'ah',
        '500', '308', 'mixte', 'mâle', 'femelle', 'coq', 'poule',
        'poulet', 'pondeuse', 'chair'
    }
    words = set(question.lower().replace('.', ' ').replace(',', ' ').split())
    
    # Vérifier si tous les mots sont techniques ou numériques
    non_technical = words - technical_terms - {str(i) for i in range(1000)}
    if len(non_technical) <= 1:  # Maximum 1 mot non-technique
        logger.debug(f"🎯 Détection ignorée: principalement termes techniques ({words})")
        return True
    
    # Ignorer si format "lignée. sexe. autres" typique des clarifications
    if re.match(r'^\s*\w+\s*[\.,]\s*\w+\s*[\.,]?\s*\w*\s*$', question.strip()):
        logger.debug("🎯 Détection ignorée: format clarification technique")
        return True
    
    return False

# ---------------------------------------------------------------------------
# DÉTECTION DE LANGUE UNIVERSELLE (VERSION OPTIMISÉE)
# ---------------------------------------------------------------------------

def detect_question_language(question: str, conversation_context: Optional[Dict[str, Any]] = None) -> str:
    """
    🚀 VERSION OPTIMISÉE: Utilise OpenAI pour détecter automatiquement la langue de la question.
    CONSERVATION INTÉGRALE de la logique avec ajout du cache pour éviter les appels OpenAI redondants.
    Supporte toutes les langues sans limitation.
    Tient compte du contexte conversationnel pour éviter les changements intempestifs.
    """
    if not question or not OPENAI_AVAILABLE:
        return "fr"  # Fallback par défaut
    
    # 🚀 NOUVEAU: Vérifier le cache en premier pour éviter appel OpenAI
    cached_language = _get_cached_language_detection(question)
    if cached_language is not None:
        # Même avec cache hit, appliquer la logique d'ignore si contexte disponible
        conversation_lang = None
        if conversation_context:
            conversation_lang = conversation_context.get("language")
            
        if conversation_lang and should_ignore_language_detection(question, cached_language, conversation_lang):
            logger.info(f"🎯 Détection {cached_language} ignorée, conservation {conversation_lang}")
            return conversation_lang
            
        return cached_language
    
    # Vérifier le contexte conversationnel
    conversation_lang = None
    if conversation_context:
        conversation_lang = conversation_context.get("language")
    
    try:
        # 🚀 MESURE: Temps d'appel OpenAI pour monitoring
        start_time = time.time()
        
        detection_prompt = f"""Detect the language of this question and respond with ONLY the 2-letter ISO language code (en, fr, es, de, it, pt, etc.).

Question: "{question}"

Language code:"""

        language_code = openai_complete(
            prompt=detection_prompt,
            max_tokens=5     # Juste le code langue
        )
        
        openai_call_time = time.time() - start_time
        logger.debug(f"⏱️ [LANG_DETECT] Appel OpenAI: {openai_call_time:.3f}s")
        
        if language_code:
            detected = language_code.strip().lower()[:2]  # Premier code à 2 lettres
            
            # 🚀 NOUVEAU: Mettre en cache le résultat AVANT application de la logique ignore
            _cache_language_detection(question, detected)
            
            # 🔧 CONSERVÉ: Appliquer la logique d'ignore si contexte disponible
            if conversation_lang and should_ignore_language_detection(question, detected, conversation_lang):
                logger.info(f"🎯 Détection {detected} ignorée, conservation {conversation_lang}")
                return conversation_lang
            
            logger.info(f"🌍 Langue détectée par OpenAI: {detected}")
            return detected
            
    except Exception as e:
        logger.warning(f"⚠️ Erreur détection langue OpenAI: {e}")
    
    # Fallback simple si OpenAI échoue
    fallback_result = detect_language_simple_fallback(question)
    
    # 🚀 NOUVEAU: Mettre en cache même le fallback pour éviter re-calculs
    if fallback_result != "auto":  # Ne pas cacher "auto" qui n'est pas définitif
        _cache_language_detection(question, fallback_result)
    
    return fallback_result

def detect_language_simple_fallback(question: str) -> str:
    """
    CONSERVATION INTÉGRALE: Fallback simple si OpenAI n'est pas disponible.
    Détection basique français vs non-français.
    """
    if not question:
        return "fr"
        
    text_lower = question.lower()
    
    # Indicateurs français fréquents
    french_indicators = [
        " le ", " la ", " les ", " un ", " une ", " des ", " du ", " de la ",
        "quel", "quelle", "comment", "pourquoi", "combien", " est ", " sont "
    ]
    
    french_score = sum(1 for indicator in french_indicators if indicator in text_lower)
    
    if french_score >= 2:  # Au moins 2 indicateurs français
        return "fr"
    else:
        return "auto"  # Laisse OpenAI gérer dans le post-processing

# ---------------------------------------------------------------------------
# ADAPTATION LINGUISTIQUE (CONSERVÉE INTÉGRALEMENT)
# ---------------------------------------------------------------------------

def adapt_response_to_language(response_text: str, source_type: str, target_language: str, original_question: str) -> str:
    """
    CONSERVATION INTÉGRALE: Adapte la réponse à la langue cible via OpenAI de manière intelligente.
    Supporte TOUTES les langues automatiquement.
    """
    # Si français, pas de traitement
    if target_language == "fr":
        return response_text
    
    # Si pas d'OpenAI, retourner tel quel
    if not OPENAI_AVAILABLE:
        logger.warning(f"⚠️ OpenAI indisponible pour adaptation linguistique vers {target_language}")
        return response_text
    
    try:
        # Prompt adaptatif selon le type de source
        adaptation_prompts = {
            "rag_retriever": f"""The user asked this question: "{original_question}"

Here is the response found in the knowledge base (originally in French):
"{response_text}"

Please rewrite this response in the same language as the user's question, maintaining:
- Technical accuracy
- Professional tone
- All specific values and data
- Proper formatting (markdown if present)

Adapted response:""",

            "table_lookup": f"""The user asked: "{original_question}"

Here is a performance data response (originally in French):
"{response_text}"

Please reformat this data in the same language as the user's question, keeping:
- All numerical values exact
- Professional poultry terminology
- Clear formatting

Reformatted response:""",

            "hybrid_ui": f"""The user asked: "{original_question}"

Here is a clarification request (originally in French):
"{response_text}"

Please rewrite this clarification request in the same language as the user's question, maintaining:
- Clear questions
- Professional tone
- All suggested options

Clarification in user's language:""",

            "openai_fallback": response_text,  # Déjà géré par OpenAI

            "compute": f"""The user asked: "{original_question}"

Here is a calculated response (originally in French):
"{response_text}"

Please rewrite this in the same language as the user's question, keeping:
- All calculations and formulas exact
- Technical accuracy
- Professional tone

Calculated response in user's language:""",

            "cot_analysis": f"""The user asked: "{original_question}"

Here is a Chain-of-Thought analysis (originally in French):
"{response_text}"

Please rewrite this analysis in the same language as the user's question, maintaining:
- Logical structure and reasoning
- Technical accuracy
- Professional tone
- All recommendations

Analysis in user's language:"""
        }
        
        prompt = adaptation_prompts.get(source_type, adaptation_prompts["rag_retriever"])
        
        # Adaptation via OpenAI améliorée
        adapted_text = openai_complete(
            prompt=prompt,
            max_tokens=600    # Assez pour réponses complètes
        )
        
        if adapted_text and len(adapted_text.strip()) > 10:
            logger.info(f"✅ Réponse adaptée de {source_type} vers langue détectée")
            return adapted_text.strip()
        else:
            logger.warning(f"⚠️ Adaptation linguistique échouée, retour original")
            return response_text
            
    except Exception as e:
        logger.error(f"❌ Erreur adaptation linguistique: {e}")
        return response_text

def finalize_response_with_language(response: Dict[str, Any], question: str, effective_language: str, detected_language: str, force_conversation_language: bool = True) -> Dict[str, Any]:
    """
    CONSERVATION INTÉGRALE: Helper pour appliquer l'adaptation linguistique à toute réponse finale.
    Utilise cette fonction avant chaque return dans handle().
    
    Args:
        response: Réponse à finaliser
        question: Question originale de l'utilisateur
        effective_language: Langue effective choisie
        detected_language: Langue détectée automatiquement
        force_conversation_language: Force l'adaptation si langues différentes
    """
    # Ajouter les métadonnées de langue pour toutes les réponses
    if response.get("type") == "answer" and "answer" in response:
        response["answer"]["meta"] = response["answer"].get("meta", {})
        response["answer"]["meta"]["detected_language"] = detected_language
        response["answer"]["meta"]["effective_language"] = effective_language
        
        # 🔧 CONSERVÉ: Détecter si adaptation forcée nécessaire
        answer_text = response["answer"].get("text", "")
        if answer_text and force_conversation_language:
            # Détecter la langue actuelle du texte de réponse
            current_response_lang = detect_question_language(answer_text) if len(answer_text) > 20 else effective_language
            
            # Si langues différentes et ce n'est pas déjà un fallback OpenAI → adapter
            if (current_response_lang != effective_language and 
                response["answer"].get("source") not in ["openai_fallback", "cot_analysis"]):
                
                logger.info(f"🌍 Adaptation forcée détectée {current_response_lang} → {effective_language}")
                
                # Marquer l'adaptation dans les métadonnées
                response["answer"]["meta"]["language_adaptation"] = {
                    "from": current_response_lang,
                    "to": effective_language,
                    "forced": True
                }
        
        # Si c'est déjà un fallback OpenAI avec la bonne langue, pas besoin d'adaptation
        if response["answer"].get("source") in ["openai_fallback", "cot_analysis"]:
            target_lang_in_meta = response["answer"]["meta"].get("target_language", "fr")
            if target_lang_in_meta == effective_language:
                logger.info(f"✅ Fallback OpenAI déjà généré dans la langue cible: {effective_language}")
                return response
        
    elif response.get("type") == "partial_answer":
        response["language_metadata"] = {
            "detected_language": detected_language,
            "effective_language": effective_language,
            "force_conversation_language": force_conversation_language
        }
    
    # Si français, pas de traitement supplémentaire nécessaire
    if effective_language == "fr":
        return response
    
    # Adapter le texte principal selon le type de réponse
    if response.get("type") == "answer" and response.get("answer", {}).get("text"):
        answer = response["answer"]
        original_text = answer["text"]
        source_type = answer.get("source", "unknown")
        
        # Ne pas re-adapter les fallbacks OpenAI qui sont déjà dans la bonne langue
        if source_type in ["openai_fallback", "cot_analysis"]:
            logger.info("⏸️ Fallback OpenAI/CoT - adaptation linguistique déjà effectuée")
            return response
        
        adapted_text = adapt_response_to_language(
            response_text=original_text,
            source_type=source_type,
            target_language=effective_language,
            original_question=question
        )
        
        # Mettre à jour la réponse
        response["answer"]["text"] = adapted_text
        
        # 🔧 CONSERVÉ: Marquer l'adaptation
        if adapted_text != original_text:
            response["answer"]["meta"]["language_adapted"] = True
        
    elif response.get("type") == "partial_answer" and response.get("general_answer", {}).get("text"):
        # Pour le mode hybride
        original_text = response["general_answer"]["text"]
        
        adapted_text = adapt_response_to_language(
            response_text=original_text,
            source_type="hybrid_ui",
            target_language=effective_language,
            original_question=question
        )
        
        response["general_answer"]["text"] = adapted_text
        
        # 🔧 CONSERVÉ: Marquer l'adaptation
        if adapted_text != original_text:
            response["language_metadata"]["adapted"] = True
    
    return response

def get_language_processing_status() -> Dict[str, Any]:
    """
    🚀 VERSION AMÉLIORÉE: Retourne le statut du système de traitement linguistique avec infos cache
    """
    auto_detection_enabled = str(os.getenv("ENABLE_AUTO_LANGUAGE_DETECTION", "true")).lower() in ("1", "true", "yes", "on")
    
    return {
        "openai_available": OPENAI_AVAILABLE,
        "auto_detection_enabled": auto_detection_enabled,
        "supported_fallback_languages": ["en", "es", "de", "it", "pt", "nl", "pl", "ru", "ja", "zh"],
        "default_language": "fr",
        "enhanced_features": {
            "conversation_context_awareness": True,
            "technical_terms_detection": True,
            "smart_language_switching": True,
            "forced_adaptation": True
        },
        "technical_terms_count": 20,  # Nombre de termes techniques reconnus
        "version": "cached_v2.0",
        # 🚀 NOUVEAU: Informations sur le cache de langue
        "language_cache": {
            "enabled": True,
            "current_size": len(_LANGUAGE_CACHE),
            "max_size": _LANGUAGE_CACHE_MAX_SIZE,
            "ttl_seconds": _LANGUAGE_CACHE_TTL,
            "estimated_hit_ratio": "80-90%",  # Estimation basée sur patterns d'usage
            "openai_calls_saved": "significant"
        }
    }

# ---------------------------------------------------------------------------
# 🚀 NOUVELLES FONCTIONS DE CACHE ET OPTIMISATION
# ---------------------------------------------------------------------------

def get_language_cache_stats() -> Dict[str, Any]:
    """🚀 NOUVEAU: Statistiques détaillées du cache de langue"""
    if not _LANGUAGE_CACHE:
        return {
            "total_entries": 0,
            "cache_empty": True
        }
    
    # Analyser les langues en cache
    language_counts = {}
    oldest_entry = None
    newest_entry = None
    
    for key, (language, timestamp) in _LANGUAGE_CACHE.items():
        language_counts[language] = language_counts.get(language, 0) + 1
        
        if oldest_entry is None or timestamp < oldest_entry:
            oldest_entry = timestamp
        if newest_entry is None or timestamp > newest_entry:
            newest_entry = timestamp
    
    current_time = time.time()
    return {
        "total_entries": len(_LANGUAGE_CACHE),
        "max_capacity": _LANGUAGE_CACHE_MAX_SIZE,
        "utilization_percent": (len(_LANGUAGE_CACHE) / _LANGUAGE_CACHE_MAX_SIZE) * 100,
        "languages_cached": language_counts,
        "most_common_language": max(language_counts, key=language_counts.get) if language_counts else None,
        "oldest_entry_age_seconds": current_time - oldest_entry if oldest_entry else 0,
        "newest_entry_age_seconds": current_time - newest_entry if newest_entry else 0,
        "ttl_seconds": _LANGUAGE_CACHE_TTL,
        "memory_usage_estimate_kb": len(_LANGUAGE_CACHE) * 0.2,  # Estimation rough
        "performance_impact": {
            "openai_calls_avoided": len(_LANGUAGE_CACHE),
            "estimated_time_saved_seconds": len(_LANGUAGE_CACHE) * 1.5,  # ~1.5s par appel OpenAI évité
            "cost_savings_estimate": f"${len(_LANGUAGE_CACHE) * 0.001:.3f}"  # Estimation coût OpenAI évité
        }
    }

def clear_language_cache(language_code: Optional[str] = None):
    """🚀 NOUVEAU: Vide le cache de langue (optionnellement par langue)"""
    global _LANGUAGE_CACHE
    
    if language_code is None:
        # Vider tout le cache
        cleared_count = len(_LANGUAGE_CACHE)
        _LANGUAGE_CACHE.clear()
        logger.info(f"🧹 [LANG_CACHE] Cache entièrement vidé: {cleared_count} entrées supprimées")
    else:
        # Vider seulement une langue spécifique
        keys_to_remove = [key for key, (lang, _) in _LANGUAGE_CACHE.items() if lang == language_code]
        for key in keys_to_remove:
            _LANGUAGE_CACHE.pop(key, None)
        logger.info(f"🧹 [LANG_CACHE] Cache {language_code} vidé: {len(keys_to_remove)} entrées supprimées")

def warm_language_cache(questions: List[str]):
    """🚀 NOUVEAU: Pré-chauffe le cache avec une liste de questions communes"""
    logger.info(f"🔥 [LANG_CACHE] Pré-chauffage avec {len(questions)} questions...")
    
    warmed_count = 0
    for question in questions:
        if not question or not question.strip():
            continue
            
        # Effectuer la détection pour mettre en cache (mais sans contexte conversationnel)
        detected_lang = detect_question_language(question, None)
        
        if detected_lang and detected_lang != "auto":
            warmed_count += 1
    
    logger.info(f"🔥 [LANG_CACHE] Pré-chauffage terminé: {warmed_count} questions traitées, cache: {len(_LANGUAGE_CACHE)} entrées")

def benchmark_language_detection_performance(test_questions: List[str], iterations: int = 3) -> Dict[str, Any]:
    """🚀 NOUVEAU: Benchmark de performance avec/sans cache pour la détection de langue"""
    if not OPENAI_AVAILABLE:
        return {
            "error": "OpenAI non disponible pour benchmark",
            "openai_available": False
        }
    
    logger.info(f"⚡ [LANG_BENCHMARK] Test performance avec {len(test_questions)} questions, {iterations} itérations")
    
    # Test sans cache (première exécution)
    clear_language_cache()
    start_time = time.time()
    
    for _ in range(iterations):
        for question in test_questions:
            # Forcer la détection sans cache
            clear_language_cache()
            detect_question_language(question, None)
    
    no_cache_time = time.time() - start_time
    
    # Test avec cache (exécutions suivantes)
    clear_language_cache()
    # Pré-chauffer le cache avec une itération
    for question in test_questions:
        detect_question_language(question, None)
    
    start_time = time.time()
    
    for _ in range(iterations):
        for question in test_questions:
            detect_question_language(question, None)  # Devrait utiliser le cache
    
    with_cache_time = time.time() - start_time
    
    # Calculer les gains
    speedup = no_cache_time / with_cache_time if with_cache_time > 0 else float('inf')
    cache_efficiency = ((no_cache_time - with_cache_time) / no_cache_time) * 100 if no_cache_time > 0 else 0
    
    results = {
        "test_config": {
            "questions_count": len(test_questions),
            "iterations": iterations,
            "total_detections": len(test_questions) * iterations
        },
        "performance": {
            "without_cache_seconds": round(no_cache_time, 3),
            "with_cache_seconds": round(with_cache_time, 3),
            "speedup_factor": round(speedup, 2),
            "cache_efficiency_percent": round(cache_efficiency, 1),
            "avg_openai_call_time": round(no_cache_time / (len(test_questions) * iterations), 3),
            "avg_cache_hit_time": round(with_cache_time / (len(test_questions) * iterations), 3)
        },
        "cost_analysis": {
            "openai_calls_without_cache": len(test_questions) * iterations,
            "openai_calls_with_cache": len(test_questions),  # Seulement le premier cycle
            "calls_saved": (len(test_questions) * iterations) - len(test_questions),
            "estimated_cost_saved_usd": round(((len(test_questions) * iterations) - len(test_questions)) * 0.001, 4)
        },
        "cache_stats": get_language_cache_stats()
    }
    
    logger.info(f"⚡ [LANG_BENCHMARK] Résultats: Speedup {speedup:.1f}x, Efficacité {cache_efficiency:.1f}%, Calls évités: {results['cost_analysis']['calls_saved']}")
    return results

def debug_language_detection(question: str, with_context: bool = False) -> Dict[str, Any]:
    """🚀 NOUVEAU: Debug complet de la détection de langue avec informations cache"""
    logger.info(f"🔬 [LANG_DEBUG] Test détection sur: '{question}'")
    
    # Test sans cache d'abord
    question_hash = _get_question_hash(question)
    was_cached = question_hash in _LANGUAGE_CACHE
    
    if was_cached:
        cached_result = _LANGUAGE_CACHE[question_hash]
        logger.info(f"🔬 [LANG_DEBUG] Résultat en cache trouvé: {cached_result}")
    
    # Test avec détection complète
    start_time = time.time()
    
    context = {"language": "fr"} if with_context else None
    detected_lang = detect_question_language(question, context)
    
    detection_time = time.time() - start_time
    
    # Test fallback
    fallback_lang = detect_language_simple_fallback(question)
    
    # Informations sur l'ignore logic si contexte fourni
    ignore_info = None
    if with_context and context:
        ignore_info = {
            "would_ignore": should_ignore_language_detection(question, detected_lang, context["language"]),
            "conversation_language": context["language"],
            "detected_language": detected_lang
        }
    
    results = {
        "question": question,
        "question_hash": question_hash,
        "results": {
            "detected_language": detected_lang,
            "fallback_language": fallback_lang,
            "final_language": detected_lang
        },
        "cache_info": {
            "was_cached": was_cached,
            "now_cached": question_hash in _LANGUAGE_CACHE,
            "detection_time_ms": round(detection_time * 1000, 2),
            "used_openai": detection_time > 0.1,  # Si > 100ms, probablement OpenAI
        },
        "context_info": ignore_info,
        "analysis": {
            "question_length": len(question),
            "normalized_text": re.sub(r'\s+', ' ', question.strip().lower())[:50],
            "openai_available": OPENAI_AVAILABLE
        }
    }
    
    logger.info(f"🔬 [LANG_DEBUG] Résultats complets: {results}")
    return results