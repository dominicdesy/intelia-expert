# -*- coding: utf-8 -*-
"""
Gestionnaire de langue et adaptation multilingue
Extrait de dialogue_manager.py pour modularitÃ©
VERSION AMÉLIORÉE : Détection intelligente + préservation contexte conversationnel
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
    logger.info("âœ… OpenAI disponible pour traitement linguistique")
except ImportError as e:
    logger.warning(f"âš ï¸ OpenAI indisponible pour langue: {e}")
    OPENAI_AVAILABLE = False
    def openai_complete(*args, **kwargs):
        return None

# ---------------------------------------------------------------------------
# DÉTECTION INTELLIGENTE DE LANGUE (NOUVEAU)
# ---------------------------------------------------------------------------

def should_ignore_language_detection(question: str, detected_lang: str, conversation_lang: str) -> bool:
    """
    Détermine si on doit ignorer la détection automatique de langue
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
# DÃ‰TECTION DE LANGUE UNIVERSELLE (AMÉLIORÉE)
# ---------------------------------------------------------------------------

def detect_question_language(question: str, conversation_context: Optional[Dict[str, Any]] = None) -> str:
    """
    VERSION AMÉLIORÉE : Utilise OpenAI pour détecter automatiquement la langue de la question.
    Supporte toutes les langues sans limitation.
    Tient compte du contexte conversationnel pour éviter les changements intempestifs.
    """
    if not question or not OPENAI_AVAILABLE:
        return "fr"  # Fallback par dÃ©faut
    
    # Vérifier le contexte conversationnel
    conversation_lang = None
    if conversation_context:
        conversation_lang = conversation_context.get("language")
    
    try:
        detection_prompt = f"""Detect the language of this question and respond with ONLY the 2-letter ISO language code (en, fr, es, de, it, pt, etc.).

Question: "{question}"

Language code:"""

        language_code = openai_complete(
            prompt=detection_prompt,
            max_tokens=5     # Juste le code langue
        )
        
        if language_code:
            detected = language_code.strip().lower()[:2]  # Premier code Ã  2 lettres
            
            # 🔧 NOUVEAU: Appliquer la logique d'ignore si contexte disponible
            if conversation_lang and should_ignore_language_detection(question, detected, conversation_lang):
                logger.info(f"🎯 Détection {detected} ignorée, conservation {conversation_lang}")
                return conversation_lang
            
            logger.info(f"ðŸŒ Langue dÃ©tectÃ©e par OpenAI: {detected}")
            return detected
            
    except Exception as e:
        logger.warning(f"âš ï¸ Erreur dÃ©tection langue OpenAI: {e}")
    
    # Fallback simple si OpenAI Ã©choue
    return detect_language_simple_fallback(question)

def detect_language_simple_fallback(question: str) -> str:
    """
    Fallback simple si OpenAI n'est pas disponible.
    DÃ©tection basique franÃ§ais vs non-franÃ§ais.
    """
    if not question:
        return "fr"
        
    text_lower = question.lower()
    
    # Indicateurs franÃ§ais frÃ©quents
    french_indicators = [
        " le ", " la ", " les ", " un ", " une ", " des ", " du ", " de la ",
        "quel", "quelle", "comment", "pourquoi", "combien", " est ", " sont "
    ]
    
    french_score = sum(1 for indicator in french_indicators if indicator in text_lower)
    
    if french_score >= 2:  # Au moins 2 indicateurs franÃ§ais
        return "fr"
    else:
        return "auto"  # Laisse OpenAI gÃ©rer dans le post-processing

# ---------------------------------------------------------------------------
# ADAPTATION LINGUISTIQUE
# ---------------------------------------------------------------------------

def adapt_response_to_language(response_text: str, source_type: str, target_language: str, original_question: str) -> str:
    """
    Adapte la rÃ©ponse Ã  la langue cible via OpenAI de maniÃ¨re intelligente.
    Supporte TOUTES les langues automatiquement.
    """
    # Si franÃ§ais, pas de traitement
    if target_language == "fr":
        return response_text
    
    # Si pas d'OpenAI, retourner tel quel
    if not OPENAI_AVAILABLE:
        logger.warning(f"âš ï¸ OpenAI indisponible pour adaptation linguistique vers {target_language}")
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

            "openai_fallback": response_text,  # DÃ©jÃ  gÃ©rÃ© par OpenAI

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
        
        # Adaptation via OpenAI amÃ©liorÃ©e
        adapted_text = openai_complete(
            prompt=prompt,
            max_tokens=600    # Assez pour rÃ©ponses complÃ¨tes
        )
        
        if adapted_text and len(adapted_text.strip()) > 10:
            logger.info(f"âœ… RÃ©ponse adaptÃ©e de {source_type} vers langue dÃ©tectÃ©e")
            return adapted_text.strip()
        else:
            logger.warning(f"âš ï¸ Adaptation linguistique Ã©chouÃ©e, retour original")
            return response_text
            
    except Exception as e:
        logger.error(f"âŒ Erreur adaptation linguistique: {e}")
        return response_text

def finalize_response_with_language(response: Dict[str, Any], question: str, effective_language: str, detected_language: str, force_conversation_language: bool = True) -> Dict[str, Any]:
    """
    VERSION AMÉLIORÉE : Helper pour appliquer l'adaptation linguistique Ã  toute rÃ©ponse finale.
    Utilise cette fonction avant chaque return dans handle().
    
    Args:
        response: Réponse à finaliser
        question: Question originale de l'utilisateur
        effective_language: Langue effective choisie
        detected_language: Langue détectée automatiquement
        force_conversation_language: Force l'adaptation si langues différentes
    """
    # Ajouter les mÃ©tadonnÃ©es de langue pour toutes les rÃ©ponses
    if response.get("type") == "answer" and "answer" in response:
        response["answer"]["meta"] = response["answer"].get("meta", {})
        response["answer"]["meta"]["detected_language"] = detected_language
        response["answer"]["meta"]["effective_language"] = effective_language
        
        # 🔧 NOUVEAU: Détecter si adaptation forcée nécessaire
        answer_text = response["answer"].get("text", "")
        if answer_text and force_conversation_language:
            # Détecter la langue actuelle du texte de réponse
            current_response_lang = detect_question_language(answer_text) if len(answer_text) > 20 else effective_language
            
            # Si langues différentes et ce n'est pas déjà un fallback OpenAI → adapter
            if (current_response_lang != effective_language and 
                response["answer"].get("source") not in ["openai_fallback", "cot_analysis"]):
                
                logger.info(f"🌐 Adaptation forcée détectée {current_response_lang} → {effective_language}")
                
                # Marquer l'adaptation dans les métadonnées
                response["answer"]["meta"]["language_adaptation"] = {
                    "from": current_response_lang,
                    "to": effective_language,
                    "forced": True
                }
        
        # Si c'est dÃ©jÃ  un fallback OpenAI avec la bonne langue, pas besoin d'adaptation
        if response["answer"].get("source") in ["openai_fallback", "cot_analysis"]:
            target_lang_in_meta = response["answer"]["meta"].get("target_language", "fr")
            if target_lang_in_meta == effective_language:
                logger.info(f"âœ… Fallback OpenAI dÃ©jÃ  gÃ©nÃ©rÃ© dans la langue cible: {effective_language}")
                return response
        
    elif response.get("type") == "partial_answer":
        response["language_metadata"] = {
            "detected_language": detected_language,
            "effective_language": effective_language,
            "force_conversation_language": force_conversation_language
        }
    
    # Si franÃ§ais, pas de traitement supplÃ©mentaire nÃ©cessaire
    if effective_language == "fr":
        return response
    
    # Adapter le texte principal selon le type de rÃ©ponse
    if response.get("type") == "answer" and response.get("answer", {}).get("text"):
        answer = response["answer"]
        original_text = answer["text"]
        source_type = answer.get("source", "unknown")
        
        # Ne pas re-adapter les fallbacks OpenAI qui sont dÃ©jÃ  dans la bonne langue
        if source_type in ["openai_fallback", "cot_analysis"]:
            logger.info("â„¹ï¸ Fallback OpenAI/CoT - adaptation linguistique dÃ©jÃ  effectuÃ©e")
            return response
        
        adapted_text = adapt_response_to_language(
            response_text=original_text,
            source_type=source_type,
            target_language=effective_language,
            original_question=question
        )
        
        # Mettre Ã  jour la rÃ©ponse
        response["answer"]["text"] = adapted_text
        
        # 🔧 NOUVEAU: Marquer l'adaptation
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
        
        # 🔧 NOUVEAU: Marquer l'adaptation
        if adapted_text != original_text:
            response["language_metadata"]["adapted"] = True
    
    return response

def get_language_processing_status() -> Dict[str, Any]:
    """
    Retourne le statut du systÃ¨me de traitement linguistique
    VERSION AMÉLIORÉE avec nouvelles fonctionnalités
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
        "version": "enhanced_with_context_preservation"
    }