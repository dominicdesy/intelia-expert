# -*- coding: utf-8 -*-
"""
Gestionnaire de langue et adaptation multilingue
Extrait de dialogue_manager.py pour modularité
"""

import logging
import os
import re
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

# ---------------------------------------------------------------------------
# DÉTECTION DE LANGUE UNIVERSELLE
# ---------------------------------------------------------------------------

def detect_question_language(question: str) -> str:
    """
    Utilise OpenAI pour détecter automatiquement la langue de la question.
    Supporte toutes les langues sans limitation.
    """
    if not question or not OPENAI_AVAILABLE:
        return "fr"  # Fallback par défaut
    
    try:
        detection_prompt = f"""Detect the language of this question and respond with ONLY the 2-letter ISO language code (en, fr, es, de, it, pt, etc.).

Question: "{question}"

Language code:"""

        language_code = openai_complete(
            prompt=detection_prompt,
            max_tokens=5     # Juste le code langue
        )
        
        if language_code:
            detected = language_code.strip().lower()[:2]  # Premier code à 2 lettres
            logger.info(f"🌍 Langue détectée par OpenAI: {detected}")
            return detected
            
    except Exception as e:
        logger.warning(f"⚠️ Erreur détection langue OpenAI: {e}")
    
    # Fallback simple si OpenAI échoue
    return detect_language_simple_fallback(question)

def detect_language_simple_fallback(question: str) -> str:
    """
    Fallback simple si OpenAI n'est pas disponible.
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
# ADAPTATION LINGUISTIQUE
# ---------------------------------------------------------------------------

def adapt_response_to_language(response_text: str, source_type: str, target_language: str, original_question: str) -> str:
    """
    Adapte la réponse à la langue cible via OpenAI de manière intelligente.
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

def finalize_response_with_language(response: Dict[str, Any], question: str, effective_language: str, detected_language: str) -> Dict[str, Any]:
    """
    Helper pour appliquer l'adaptation linguistique à toute réponse finale.
    Utilise cette fonction avant chaque return dans handle().
    """
    # Ajouter les métadonnées de langue pour toutes les réponses
    if response.get("type") == "answer" and "answer" in response:
        response["answer"]["meta"] = response["answer"].get("meta", {})
        response["answer"]["meta"]["detected_language"] = detected_language
        response["answer"]["meta"]["effective_language"] = effective_language
        
        # Si c'est déjà un fallback OpenAI avec la bonne langue, pas besoin d'adaptation
        if response["answer"].get("source") in ["openai_fallback", "cot_analysis"]:
            target_lang_in_meta = response["answer"]["meta"].get("target_language", "fr")
            if target_lang_in_meta == effective_language:
                logger.info(f"✅ Fallback OpenAI déjà généré dans la langue cible: {effective_language}")
                return response
        
    elif response.get("type") == "partial_answer":
        response["language_metadata"] = {
            "detected_language": detected_language,
            "effective_language": effective_language
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
            logger.info("ℹ️ Fallback OpenAI/CoT - adaptation linguistique déjà effectuée")
            return response
        
        adapted_text = adapt_response_to_language(
            response_text=original_text,
            source_type=source_type,
            target_language=effective_language,
            original_question=question
        )
        
        # Mettre à jour la réponse
        response["answer"]["text"] = adapted_text
        
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
    
    return response

def get_language_processing_status() -> Dict[str, Any]:
    """
    Retourne le statut du système de traitement linguistique
    """
    auto_detection_enabled = str(os.getenv("ENABLE_AUTO_LANGUAGE_DETECTION", "true")).lower() in ("1", "true", "yes", "on")
    
    return {
        "openai_available": OPENAI_AVAILABLE,
        "auto_detection_enabled": auto_detection_enabled,
        "supported_fallback_languages": ["en", "es", "de", "it", "pt", "nl", "pl", "ru", "ja", "zh"],
        "default_language": "fr"
    }
