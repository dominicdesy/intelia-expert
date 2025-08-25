# -*- coding: utf-8 -*-
"""
Gestion de la mémoire conversationnelle et contexte de session
Extrait de dialogue_manager.py pour modularité
VERSION CORRIGÉE - Conservation du code original avec améliorations
"""

import logging
import os
import time
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Import conditionnel de la mémoire PostgreSQL
try:
    from .postgres_memory import PostgresMemory
    MEMORY_AVAILABLE = True
    logger.info("✅ PostgresMemory importé pour la mémoire conversationnelle")
except ImportError as e:
    logger.warning(f"⚠️ PostgresMemory indisponible: {e}")
    MEMORY_AVAILABLE = False
    # Fallback en mémoire simple
    class MemoryFallback:
        def __init__(self): 
            self.store = {}
        def get(self, session_id): 
            return self.store.get(session_id, {})
        def update(self, session_id, context): 
            self.store[session_id] = context
        def clear(self, session_id): 
            self.store.pop(session_id, None)
    PostgresMemory = MemoryFallback

# Singleton mémoire conversationnelle
_CONVERSATION_MEMORY = None

# ---------------------------------------------------------------------------
# PATTERNS D'EXTRACTION AUTOMATIQUE - VERSION AMÉLIORÉE
# ---------------------------------------------------------------------------

# CORRECTION: Patterns plus robustes et ordonnés par priorité
_AGE_PATTERNS = [
    # Patterns spécifiques d'abord (plus précis)
    r"\bjour\s+(\d{1,2})\b",                                     # jour 14 (priorité haute)
    r"\b(?:J|D)(\d{1,2})\b",                                     # J14, D14 (sans espace)
    r"\b(?:J|D)\s*(\d{1,2})\b",                                  # J 14, D 14 (avec espace)
    r"\b(?:âge|age)\s*[:=]?\s*(\d{1,2})\s*(?:j|jours|d|days)\b", # âge: 21 jours / age=21d
    r"\b(?:day|jour)\s+(\d{1,2})\b",                             # day 21 / jour 14
    r"\bage_days\s*[:=]\s*(\d{1,2})\b",                          # age_days=21
    # Patterns génériques en dernier (moins précis)
    r"\b(\d{1,2})\s*(?:j|jours|d|days)\b",                       # 21 j / 21d
]

def extract_age_days_from_text(text: str) -> Optional[int]:
    """
    Extraction automatique de l'âge depuis le texte
    CORRECTION: Logs détaillés et gestion améliorée des patterns
    """
    if not text:
        logger.debug("🔍 [AGE_EXTRACT] Texte vide")
        return None
    
    logger.debug(f"🔍 [AGE_EXTRACT] Analyse du texte: '{text}'")
    
    for i, pat in enumerate(_AGE_PATTERNS):
        m = re.search(pat, text, flags=re.I)
        if m:
            try:
                val = int(m.group(1))
                logger.info(f"✅ [AGE_EXTRACT] Pattern {i} trouvé: '{pat}' -> âge={val}")
                if 0 <= val <= 70:
                    return val
                else:
                    logger.warning(f"⚠️ [AGE_EXTRACT] Âge hors limites: {val}")
            except Exception as e:
                logger.warning(f"⚠️ [AGE_EXTRACT] Erreur conversion: {e}")
                continue
    
    logger.warning(f"❌ [AGE_EXTRACT] Aucun âge détecté dans: '{text}'")
    return None

def normalize_sex_from_text(text: str) -> Optional[str]:
    """Normalisation du sexe depuis le texte"""
    if not text:
        return None
    
    t = text.lower()
    logger.debug(f"🔍 [SEX_EXTRACT] Analyse: '{t}'")
    
    if any(k in t for k in ["as hatched", "as-hatched", "as_hatched", "mixte", "mixed", " ah "]):
        logger.info("✅ [SEX_EXTRACT] Sexe détecté: as_hatched")
        return "as_hatched"
    if any(k in t for k in ["mâle", " male ", "male"]):
        logger.info("✅ [SEX_EXTRACT] Sexe détecté: male")
        return "male"
    if any(k in t for k in ["femelle", " female ", "female"]):
        logger.info("✅ [SEX_EXTRACT] Sexe détecté: female")
        return "female"
    
    logger.debug("❌ [SEX_EXTRACT] Aucun sexe détecté")
    return None

def extract_line_from_text(text: str) -> Optional[str]:
    """Extraction de lignée depuis le texte"""
    if not text:
        return None
    
    t = text.lower()
    logger.debug(f"🔍 [LINE_EXTRACT] Analyse: '{t}'")
    
    if any(k in t for k in ["cobb", "cobb500", "cobb 500", "cobb-500"]):
        logger.info("✅ [LINE_EXTRACT] Lignée détectée: cobb500")
        return "cobb500"
    if any(k in t for k in ["ross", "ross308", "ross 308", "ross-308"]):
        logger.info("✅ [LINE_EXTRACT] Lignée détectée: ross308")
        return "ross308"
    if any(k in t for k in ["hubbard"]):
        logger.info("✅ [LINE_EXTRACT] Lignée détectée: hubbard")
        return "hubbard"
    
    logger.debug("❌ [LINE_EXTRACT] Aucune lignée détectée")
    return None

def extract_species_from_text(text: str) -> Optional[str]:
    """Extraction d'espèce depuis le texte"""
    if not text:
        return None
    
    t = text.lower()
    logger.debug(f"🔍 [SPECIES_EXTRACT] Analyse: '{t}'")
    
    if any(k in t for k in ["broiler", "poulet de chair", "chair"]):
        logger.info("✅ [SPECIES_EXTRACT] Espèce détectée: broiler")
        return "broiler"
    if any(k in t for k in ["layer", "pondeuse", "ponte"]):
        logger.info("✅ [SPECIES_EXTRACT] Espèce détectée: layer")
        return "layer"
    
    logger.debug("❌ [SPECIES_EXTRACT] Aucune espèce détectée")
    return None

def extract_signs_from_text(text: str) -> Optional[str]:
    """
    NOUVELLE FONCTION: Extraction des signes cliniques depuis le texte via OpenAI
    """
    if not text:
        return None
    
    logger.debug(f"🔍 [SIGNS_EXTRACT] Analyse: '{text}'")
    
    # Fallback rapide pour signes évidents
    obvious_signs = [
        "diarrhée hémorragique", "diarrhée sanglante", "diarrhée", 
        "mortalité", "boiterie", "paralysie", "convulsions", "toux"
    ]
    
    t = text.lower()
    for sign in obvious_signs:
        if sign in t:
            logger.info(f"✅ [SIGNS_EXTRACT] Signe évident détecté: {sign}")
            return sign
    
    # Si OpenAI disponible, extraction intelligente
    try:
        from ..utils.openai_utils import complete_text as openai_complete
        
        extraction_prompt = f"""Tu es un vétérinaire expert. Extrais UNIQUEMENT les signes cliniques mentionnés dans ce texte sur l'aviculture.

Texte: "{text}"

INSTRUCTIONS:
- Extrais SEULEMENT les symptômes/signes cliniques mentionnés
- Si aucun signe clinique n'est mentionné, réponds "AUCUN"
- Donne une réponse courte (maximum 3-4 mots)
- Exemples de signes: diarrhée, boiterie, mortalité, convulsions, toux, etc.

Signes cliniques détectés:"""

        response = openai_complete(
            prompt=extraction_prompt,
            max_tokens=20     # Réponse courte
        )
        
        if response and response.strip().upper() != "AUCUN":
            extracted_sign = response.strip()
            logger.info(f"✅ [SIGNS_EXTRACT] OpenAI détecté: '{extracted_sign}'")
            return extracted_sign
            
    except Exception as e:
        logger.warning(f"⚠️ [SIGNS_EXTRACT] Échec OpenAI: {e}")
    
    logger.debug("❌ [SIGNS_EXTRACT] Aucun signe clinique détecté")
    return None

# ---------------------------------------------------------------------------
# GESTION MÉMOIRE CONVERSATIONNELLE
# ---------------------------------------------------------------------------

def get_conversation_memory():
    """Retourne le singleton de mémoire conversationnelle"""
    global _CONVERSATION_MEMORY
    if _CONVERSATION_MEMORY is None:
        try:
            if MEMORY_AVAILABLE:
                _CONVERSATION_MEMORY = PostgresMemory(dsn=os.getenv("DATABASE_URL"))
            else:
                _CONVERSATION_MEMORY = PostgresMemory()  # Fallback
            logger.info("🧠 Mémoire conversationnelle initialisée")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation mémoire: {e}")
            _CONVERSATION_MEMORY = PostgresMemory()  # Fallback simple
    return _CONVERSATION_MEMORY

def merge_conversation_context(current_entities: Dict[str, Any], session_context: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Fusionne le contexte de session avec les entités actuelles.
    Enrichit automatiquement depuis le texte de la question.
    CORRECTION MAJEURE: Logique de fusion simplifiée et sécurisée
    """
    logger.info(f"🔗 [MERGE] Début fusion - session: {session_context.get('entities', {})}")
    logger.info(f"🔗 [MERGE] Current entities: {current_entities}")
    logger.info(f"🔗 [MERGE] Question: '{question}'")
    
    # 1. Commencer par le contexte de session (données persistantes)
    merged = dict(session_context.get("entities", {}))
    logger.debug(f"🔗 [MERGE] Base session: {merged}")
    
    # 2. Enrichissement automatique depuis le texte de la question
    auto_species = extract_species_from_text(question)
    auto_line = extract_line_from_text(question) 
    auto_sex = normalize_sex_from_text(question)
    auto_age = extract_age_days_from_text(question)
    auto_signs = extract_signs_from_text(question)
    
    auto_extracted = {
        "species": auto_species,
        "line": auto_line, 
        "sex": auto_sex,
        "age_days": auto_age,
        "signs": auto_signs
    }
    logger.info(f"🤖 [MERGE] Auto-extraction: {auto_extracted}")
    
    # 3. CORRECTION: Fusion prioritaire - auto-extraction en premier
    for key, value in auto_extracted.items():
        if value is not None:
            merged[key] = value
            logger.debug(f"✅ [MERGE] Auto-ajout: {key}={value}")
    
    # 4. CORRECTION: Current entities en dernier, mais seulement si valeurs valides
    for key, value in current_entities.items():
        if value is not None:  # Seulement les valeurs non-nulles
            # SÉCURITÉ: Ne pas écraser un âge valide par None
            if key == "age_days" and value is None and merged.get("age_days") is not None:
                logger.warning(f"⚠️ [MERGE] Préservation âge existant: {merged.get('age_days')}")
                continue
            merged[key] = value
            logger.debug(f"✅ [MERGE] Current ajout: {key}={value}")
    
    logger.info(f"🎯 [MERGE] Résultat final: {merged}")
    
    return merged

def should_continue_conversation(session_context: Dict[str, Any], current_intent) -> bool:
    """
    Détermine si la question actuelle continue une conversation précédente
    """
    if not session_context:
        return False
        
    # Vérifier si il y a une intention en attente
    pending_intent = session_context.get("pending_intent")
    last_timestamp = session_context.get("timestamp", 0)
    
    # Expiration du contexte après 10 minutes
    if time.time() - last_timestamp > 600:
        return False
        
    # Continuer si même intention ou intention ambiguë avec contexte PerfTargets
    from ..utils.question_classifier import Intention  # Import local pour éviter circulaire
    if pending_intent == "PerfTargets":
        return current_intent in [Intention.PerfTargets, Intention.AmbiguousGeneral]
        
    return False

def save_conversation_context(session_id: str, intent, entities: Dict[str, Any], question: str, missing_fields: List[str]):
    """
    Sauvegarde le contexte conversationnel pour continuité
    """
    try:
        memory = get_conversation_memory()
        context = {
            "pending_intent": intent.name if hasattr(intent, 'name') else str(intent),
            "entities": entities,
            "question": question,
            "missing_fields": missing_fields,
            "timestamp": time.time()
        }
        memory.update(session_id, context)
        logger.info(f"💾 Contexte sauvegardé pour session {session_id}")
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde contexte: {e}")

def clear_conversation_context(session_id: str):
    """
    Efface le contexte conversationnel après réponse complète
    """
    try:
        memory = get_conversation_memory()
        memory.clear(session_id)
        logger.info(f"🧹 Contexte effacé pour session {session_id}")
    except Exception as e:
        logger.error(f"❌ Erreur effacement contexte: {e}")

def get_memory_status() -> Dict[str, Any]:
    """
    Retourne le statut du système de mémoire conversationnelle
    """
    return {
        "memory_available": MEMORY_AVAILABLE,
        "postgres_enabled": MEMORY_AVAILABLE,
        "fallback_type": "in_memory" if not MEMORY_AVAILABLE else "postgresql",
        "auto_extraction_enabled": True,
        "context_expiry_minutes": 10,
        "version": "corrected_v1.1",
        "improvements": [
            "patterns_age_ameliores",
            "logs_detailles_extraction", 
            "logique_fusion_securisee",
            "preservation_age_valide",
            "extraction_signes_cliniques"
        ]
    }

# ---------------------------------------------------------------------------
# FONCTIONS DE DEBUG ET TEST
# ---------------------------------------------------------------------------

def debug_text_extraction(text: str) -> Dict[str, Any]:
    """
    NOUVELLE FONCTION: Debug complet de l'extraction automatique
    """
    logger.info(f"🔬 [DEBUG] Test extraction sur: '{text}'")
    
    results = {
        "text": text,
        "age_days": extract_age_days_from_text(text),
        "species": extract_species_from_text(text),
        "line": extract_line_from_text(text),
        "sex": normalize_sex_from_text(text),
        "signs": extract_signs_from_text(text)
    }
    
    logger.info(f"🔬 [DEBUG] Résultats: {results}")
    return results

def test_merge_logic(question: str, session_entities: Dict = None, current_entities: Dict = None) -> Dict[str, Any]:
    """
    NOUVELLE FONCTION: Test de la logique de fusion
    """
    session_context = {"entities": session_entities or {}}
    current = current_entities or {}
    
    logger.info(f"🧪 [TEST] Question: '{question}'")
    logger.info(f"🧪 [TEST] Session: {session_entities}")
    logger.info(f"🧪 [TEST] Current: {current_entities}")
    
    result = merge_conversation_context(current, session_context, question)
    
    logger.info(f"🧪 [TEST] Résultat: {result}")
    return result