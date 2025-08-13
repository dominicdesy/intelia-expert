# -*- coding: utf-8 -*-
"""
Gestion de la mémoire conversationnelle et contexte de session
Extrait de dialogue_manager.py pour modularité
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
# PATTERNS D'EXTRACTION AUTOMATIQUE
# ---------------------------------------------------------------------------

_AGE_PATTERNS = [
    r"\b(?:âge|age)\s*[:=]?\s*(\d{1,2})\s*(?:j|jours|d|days)\b",  # âge: 21 jours / age=21d
    r"\b(?:J|D)\s*?(\d{1,2})\b",                                 # J21 / D21
    r"\b(?:day|jour)\s*(\d{1,2})\b",                              # day 21 / jour 21
    r"\b(\d{1,2})\s*(?:j|jours|d|days)\b",                        # 21 j / 21d
    r"\bage_days\s*[:=]\s*(\d{1,2})\b",                           # age_days=21
]

def extract_age_days_from_text(text: str) -> Optional[int]:
    """Extraction automatique de l'âge depuis le texte"""
    if not text:
        return None
    for pat in _AGE_PATTERNS:
        m = re.search(pat, text, flags=re.I)
        if m:
            try:
                val = int(m.group(1))
                if 0 <= val <= 70:
                    return val
            except Exception:
                continue
    return None

def normalize_sex_from_text(text: str) -> Optional[str]:
    """Normalisation du sexe depuis le texte"""
    t = (text or "").lower()
    if any(k in t for k in ["as hatched", "as-hatched", "as_hatched", "mixte", "mixed", " ah "]):
        return "as_hatched"
    if any(k in t for k in ["mâle", " male ", "male"]):
        return "male"
    if any(k in t for k in ["femelle", " female ", "female"]):
        return "female"
    return None

def extract_line_from_text(text: str) -> Optional[str]:
    """Extraction de lignée depuis le texte"""
    t = (text or "").lower()
    if any(k in t for k in ["cobb", "cobb500", "cobb 500", "cobb-500"]):
        return "cobb500"
    if any(k in t for k in ["ross", "ross308", "ross 308", "ross-308"]):
        return "ross308"
    if any(k in t for k in ["hubbard"]):
        return "hubbard"
    return None

def extract_species_from_text(text: str) -> Optional[str]:
    """Extraction d'espèce depuis le texte"""
    t = (text or "").lower()
    if any(k in t for k in ["broiler", "poulet de chair", "chair"]):
        return "broiler"
    if any(k in t for k in ["layer", "pondeuse", "ponte"]):
        return "layer"
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
    CORRECTION: Préserve l'âge du contexte précédent si non présent dans la nouvelle question.
    """
    # CORRECTION: Commencer par le contexte de session (qui contient l'âge)
    merged = dict(session_context.get("entities", {}))
    
    # Enrichissement automatique depuis le texte
    auto_species = extract_species_from_text(question)
    auto_line = extract_line_from_text(question) 
    auto_sex = normalize_sex_from_text(question)
    auto_age = extract_age_days_from_text(question)
    
    # CORRECTION: Seulement remplacer si la nouvelle valeur existe
    if auto_species: 
        merged["species"] = auto_species
    if auto_line: 
        merged["line"] = auto_line
    if auto_sex: 
        merged["sex"] = auto_sex
    if auto_age: 
        merged["age_days"] = auto_age  # Seulement si nouvel âge détecté
    
    # CORRECTION: Fusion sélective - ne pas écraser l'âge s'il n'est pas dans current_entities
    for key, value in current_entities.items():
        if key == "age_days" and value is None and merged.get("age_days") is not None:
            # Garder l'âge du contexte précédent si la nouvelle valeur est None
            continue
        merged[key] = value
    
    logger.info(f"🔗 Contexte fusionné: session={session_context.get('entities', {})} + auto={{'species':{auto_species}, 'line':{auto_line}, 'sex':{auto_sex}, 'age':{auto_age}}} + current={current_entities} → {merged}")
    
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
        "context_expiry_minutes": 10
    }
