# -*- coding: utf-8 -*-
"""
Gestion de la mémoire conversationnelle et contexte de session
🚨 VERSION SÉCURISÉE MÉMOIRE - Cache drastiquement réduit pour éviter OOM
"""

import logging
import os
import time
import re
import hashlib
import gc
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

# 🚨 CORRECTION URGENTE: Cache drastiquement réduit pour éviter OOM
_EXTRACTION_CACHE = {}
_CACHE_MAX_SIZE = int(os.getenv("EXTRACTION_CACHE_SIZE", "25"))  # ⚠️ RÉDUIT de 1000 → 25
_CACHE_TTL_SECONDS = int(os.getenv("EXTRACTION_CACHE_TTL", "300"))  # ⚠️ RÉDUIT de 3600 → 300 (5 min)

# 🚨 PROTECTION MÉMOIRE - Désactivation du cache si pas assez de RAM
CACHE_ENABLED = str(os.getenv("ENABLE_EXTRACTION_CACHE", "true")).lower() in ("1", "true", "yes")

def _memory_emergency_cleanup():
    """🚨 NOUVEAU: Nettoyage d'urgence si mémoire critique"""
    global _EXTRACTION_CACHE
    try:
        # Si plus de 50 entrées en cache ou cache désactivé → vider
        if len(_EXTRACTION_CACHE) > 50 or not CACHE_ENABLED:
            cleared_count = len(_EXTRACTION_CACHE)
            _EXTRACTION_CACHE.clear()
            gc.collect()  # Force garbage collection
            logger.warning(f"🚨 [EMERGENCY] Cache extraction vidé: {cleared_count} entrées - protection mémoire")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur nettoyage urgence: {e}")
    return False

def _get_text_hash(text: str) -> str:
    """Génère un hash pour le cache basé sur le texte"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]  # ⚠️ RÉDUIT de 16 → 8 caractères

def _cleanup_cache():
    """🚨 VERSION SÉCURISÉE: Nettoyage intelligent avec protection mémoire"""
    global _EXTRACTION_CACHE
    
    # Vérification de sécurité mémoire
    if _memory_emergency_cleanup():
        return
    
    current_time = time.time()
    
    # Supprimer les entrées expirées
    expired_keys = [
        key for key, (_, timestamp) in _EXTRACTION_CACHE.items()
        if current_time - timestamp > _CACHE_TTL_SECONDS
    ]
    
    for key in expired_keys:
        _EXTRACTION_CACHE.pop(key, None)
    
    # ⚠️ SÉCURITÉ RENFORCÉE: Si encore trop d'entrées, limiter drastiquement  
    if len(_EXTRACTION_CACHE) > _CACHE_MAX_SIZE:
        # Garder seulement les 50% les plus récentes
        sorted_items = sorted(
            _EXTRACTION_CACHE.items(),
            key=lambda x: x[1][1]  # Trier par timestamp
        )
        
        keep_count = max(5, int(_CACHE_MAX_SIZE * 0.5))  # Minimum 5, max 50% de la limite
        items_to_keep = sorted_items[-keep_count:]
        
        _EXTRACTION_CACHE = {key: value for key, value in items_to_keep}
        logger.warning(f"🚨 [CACHE] Nettoyage sécurisé: {len(expired_keys)} expirées, gardé seulement {keep_count} entrées")

def _get_cached_extraction(text: str, extraction_type: str) -> Optional[Any]:
    """🚨 VERSION SÉCURISÉE: Récupère le résultat d'extraction depuis le cache"""
    # ⚠️ SÉCURITÉ: Si cache désactivé, retourner None
    if not CACHE_ENABLED or not text or not text.strip():
        return None
        
    cache_key = f"{_get_text_hash(text)}:{extraction_type}"
    
    if cache_key in _EXTRACTION_CACHE:
        cached_result, timestamp = _EXTRACTION_CACHE[cache_key]
        
        # Vérifier TTL
        if time.time() - timestamp <= _CACHE_TTL_SECONDS:
            logger.debug(f"💾 [CACHE] Hit pour {extraction_type}: '{text[:20]}...' -> {cached_result}")
            return cached_result
        else:
            # Entrée expirée
            _EXTRACTION_CACHE.pop(cache_key, None)
    
    return None

def _cache_extraction_result(text: str, extraction_type: str, result: Any):
    """🚨 VERSION SÉCURISÉE: Sauvegarde le résultat d'extraction en cache"""
    # ⚠️ SÉCURITÉ: Si cache désactivé ou limite atteinte, ne pas sauvegarder
    if not CACHE_ENABLED or not text or not text.strip():
        return
        
    if len(_EXTRACTION_CACHE) >= _CACHE_MAX_SIZE:
        logger.debug(f"⚠️ [CACHE] Limite atteinte ({_CACHE_MAX_SIZE}), nettoyage...")
        _cleanup_cache()
        
        # Si toujours plein après nettoyage, ne pas ajouter
        if len(_EXTRACTION_CACHE) >= _CACHE_MAX_SIZE:
            logger.warning("⚠️ [CACHE] Cache plein après nettoyage, skip sauvegarde")
            return
        
    cache_key = f"{_get_text_hash(text)}:{extraction_type}"
    _EXTRACTION_CACHE[cache_key] = (result, time.time())
    
    logger.debug(f"💾 [CACHE] Sauvegarde {extraction_type}: '{text[:20]}...' -> {result}")
    
    # ⚠️ SÉCURITÉ: Nettoyage plus fréquent  
    if len(_EXTRACTION_CACHE) % 10 == 0:  # Toutes les 10 entrées au lieu de 50
        _cleanup_cache()

# Singleton mémoire conversationnelle
_CONVERSATION_MEMORY = None

# ---------------------------------------------------------------------------
# PATTERNS D'EXTRACTION AUTOMATIQUE - VERSION AMÉLIORÉE (CONSERVÉ)
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
    """🚨 VERSION SÉCURISÉE: Extraction automatique de l'âge depuis le texte avec cache limité"""
    if not text:
        logger.debug("🔍 [AGE_EXTRACT] Texte vide")
        return None
    
    # 🚨 SÉCURITÉ: Vérifier le cache seulement si activé et sûr
    if CACHE_ENABLED:
        cached_result = _get_cached_extraction(text, "age_days")
        if cached_result is not None:
            return cached_result
    
    logger.debug(f"🔍 [AGE_EXTRACT] Analyse du texte: '{text}'")
    
    result = None
    for i, pat in enumerate(_AGE_PATTERNS):
        m = re.search(pat, text, flags=re.I)
        if m:
            try:
                val = int(m.group(1))
                logger.info(f"✅ [AGE_EXTRACT] Pattern {i} trouvé: '{pat}' -> âge={val}")
                if 0 <= val <= 70:
                    result = val
                    break
                else:
                    logger.warning(f"⚠️ [AGE_EXTRACT] Âge hors limites: {val}")
            except Exception as e:
                logger.warning(f"⚠️ [AGE_EXTRACT] Erreur conversion: {e}")
                continue
    
    if result is None:
        logger.warning(f"❌ [AGE_EXTRACT] Aucun âge détecté dans: '{text}'")
    
    # 🚨 SÉCURITÉ: Mettre en cache seulement si sûr
    if CACHE_ENABLED:
        _cache_extraction_result(text, "age_days", result)
    return result

def normalize_sex_from_text(text: str) -> Optional[str]:
    """🚨 VERSION SÉCURISÉE: Normalisation du sexe depuis le texte avec cache limité"""
    if not text:
        return None
    
    # 🚨 SÉCURITÉ: Cache conditionnel
    if CACHE_ENABLED:
        cached_result = _get_cached_extraction(text, "sex")
        if cached_result is not None:
            return cached_result
    
    t = text.lower()
    logger.debug(f"🔍 [SEX_EXTRACT] Analyse: '{t}'")
    
    result = None
    if any(k in t for k in ["as hatched", "as-hatched", "as_hatched", "mixte", "mixed", " ah "]):
        logger.info("✅ [SEX_EXTRACT] Sexe détecté: as_hatched")
        result = "as_hatched"
    elif any(k in t for k in ["mâle", " male ", "male"]):
        logger.info("✅ [SEX_EXTRACT] Sexe détecté: male")
        result = "male"
    elif any(k in t for k in ["femelle", " female ", "female"]):
        logger.info("✅ [SEX_EXTRACT] Sexe détecté: female")
        result = "female"
    else:
        logger.debug("❌ [SEX_EXTRACT] Aucun sexe détecté")
    
    # 🚨 SÉCURITÉ: Cache conditionnel
    if CACHE_ENABLED:
        _cache_extraction_result(text, "sex", result)
    return result

def extract_line_from_text(text: str) -> Optional[str]:
    """🚨 VERSION SÉCURISÉE: Extraction de lignée depuis le texte avec cache limité"""
    if not text:
        return None
    
    if CACHE_ENABLED:
        cached_result = _get_cached_extraction(text, "line")
        if cached_result is not None:
            return cached_result
    
    t = text.lower()
    logger.debug(f"🔍 [LINE_EXTRACT] Analyse: '{t}'")
    
    result = None
    if any(k in t for k in ["cobb", "cobb500", "cobb 500", "cobb-500"]):
        logger.info("✅ [LINE_EXTRACT] Lignée détectée: cobb500")
        result = "cobb500"
    elif any(k in t for k in ["ross", "ross308", "ross 308", "ross-308"]):
        logger.info("✅ [LINE_EXTRACT] Lignée détectée: ross308")
        result = "ross308"
    elif any(k in t for k in ["hubbard"]):
        logger.info("✅ [LINE_EXTRACT] Lignée détectée: hubbard")
        result = "hubbard"
    else:
        logger.debug("❌ [LINE_EXTRACT] Aucune lignée détectée")
    
    if CACHE_ENABLED:
        _cache_extraction_result(text, "line", result)
    return result

def extract_species_from_text(text: str) -> Optional[str]:
    """🚨 VERSION SÉCURISÉE: Extraction d'espèce depuis le texte avec cache limité"""
    if not text:
        return None
    
    if CACHE_ENABLED:
        cached_result = _get_cached_extraction(text, "species")
        if cached_result is not None:
            return cached_result
    
    t = text.lower()
    logger.debug(f"🔍 [SPECIES_EXTRACT] Analyse: '{t}'")
    
    result = None
    if any(k in t for k in ["broiler", "poulet de chair", "chair"]):
        logger.info("✅ [SPECIES_EXTRACT] Espèce détectée: broiler")
        result = "broiler"
    elif any(k in t for k in ["layer", "pondeuse", "ponte"]):
        logger.info("✅ [SPECIES_EXTRACT] Espèce détectée: layer")
        result = "layer"
    else:
        logger.debug("❌ [SPECIES_EXTRACT] Aucune espèce détectée")
    
    if CACHE_ENABLED:
        _cache_extraction_result(text, "species", result)
    return result

def extract_signs_from_text(text: str) -> Optional[str]:
    """🚨 VERSION SÉCURISÉE: Extraction des signes cliniques avec cache TRÈS limité (OpenAI coûteux)"""
    if not text:
        return None
    
    # 🚨 CRITIQUE: Cache très important ici car OpenAI est coûteux !
    if CACHE_ENABLED:
        cached_result = _get_cached_extraction(text, "signs")
        if cached_result is not None:
            return cached_result
    
    logger.debug(f"🔍 [SIGNS_EXTRACT] Analyse: '{text}'")
    
    result = None
    
    # Fallback rapide pour signes évidents (CONSERVÉ)
    obvious_signs = [
        "diarrhée hémorragique", "diarrhée sanglante", "diarrhée", 
        "mortalité", "boiterie", "paralysie", "convulsions", "toux"
    ]
    
    t = text.lower()
    for sign in obvious_signs:
        if sign in t:
            logger.info(f"✅ [SIGNS_EXTRACT] Signe évident détecté: {sign}")
            result = sign
            break
    
    # 🚨 LIMITATION: OpenAI désactivé si cache désactivé (économie mémoire + coût)
    if result is None and CACHE_ENABLED:
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
                result = response.strip()
                logger.info(f"✅ [SIGNS_EXTRACT] OpenAI détecté: '{result}'")
            else:
                logger.debug("❌ [SIGNS_EXTRACT] Aucun signe clinique détecté")
                
        except Exception as e:
            logger.warning(f"⚠️ [SIGNS_EXTRACT] Échec OpenAI: {e}")
    
    if result is None:
        logger.debug("❌ [SIGNS_EXTRACT] Aucun signe clinique détecté")
    
    # 🚨 CRITIQUE: Toujours mettre en cache les résultats OpenAI pour éviter re-appels coûteux
    if CACHE_ENABLED:
        _cache_extraction_result(text, "signs", result)
    return result

# ---------------------------------------------------------------------------
# GESTION MÉMOIRE CONVERSATIONNELLE (CONSERVÉ)
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
    """CONSERVATION INTÉGRALE: Fusionne le contexte de session avec les entités actuelles."""
    logger.info(f"🔗 [MERGE] Début fusion - session: {session_context.get('entities', {})}")
    logger.info(f"🔗 [MERGE] Current entities: {current_entities}")
    logger.info(f"🔗 [MERGE] Question: '{question}'")
    
    # 1. Commencer par le contexte de session (données persistantes) - CONSERVÉ
    merged = dict(session_context.get("entities", {}))
    logger.debug(f"🔗 [MERGE] Base session: {merged}")
    
    # 2. 🚨 SÉCURISÉ: Enrichissement automatique depuis le texte (AVEC CACHE LIMITÉ)
    auto_species = extract_species_from_text(question)    # Cache conditionnel
    auto_line = extract_line_from_text(question)          # Cache conditionnel
    auto_sex = normalize_sex_from_text(question)          # Cache conditionnel
    auto_age = extract_age_days_from_text(question)       # Cache conditionnel
    auto_signs = extract_signs_from_text(question)        # Cache conditionnel (évite OpenAI redondant)
    
    auto_extracted = {
        "species": auto_species,
        "line": auto_line, 
        "sex": auto_sex,
        "age_days": auto_age,
        "signs": auto_signs
    }
    logger.info(f"🤖 [MERGE] Auto-extraction: {auto_extracted}")
    
    # 3. CORRECTION: Fusion prioritaire - auto-extraction en premier - CONSERVÉ
    for key, value in auto_extracted.items():
        if value is not None:
            merged[key] = value
            logger.debug(f"✅ [MERGE] Auto-ajout: {key}={value}")
    
    # 4. CORRECTION: Current entities en dernier, mais seulement si valeurs valides - CONSERVÉ
    for key, value in current_entities.items():
        if value is not None:  # Seulement les valeurs non-nulles
            # SÉCURITÉ: Ne pas écraser un âge valide par None - CONSERVÉ
            if key == "age_days" and value is None and merged.get("age_days") is not None:
                logger.warning(f"⚠️ [MERGE] Préservation âge existant: {merged.get('age_days')}")
                continue
            merged[key] = value
            logger.debug(f"✅ [MERGE] Current ajout: {key}={value}")
    
    logger.info(f"🎯 [MERGE] Résultat final: {merged}")
    
    return merged

# Les autres fonctions conservées intégralement...
def should_continue_conversation(session_context: Dict[str, Any], current_intent) -> bool:
    """CONSERVATION INTÉGRALE"""
    if not session_context:
        return False
        
    pending_intent = session_context.get("pending_intent")
    last_timestamp = session_context.get("timestamp", 0)
    
    if time.time() - last_timestamp > 600:
        return False
        
    from ..utils.question_classifier import Intention  # Import local pour éviter circulaire
    if pending_intent == "PerfTargets":
        return current_intent in [Intention.PerfTargets, Intention.AmbiguousGeneral]
        
    return False

def save_conversation_context(session_id: str, intent, entities: Dict[str, Any], question: str, missing_fields: List[str]):
    """CONSERVATION INTÉGRALE"""
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
    """CONSERVATION INTÉGRALE"""
    try:
        memory = get_conversation_memory()
        memory.clear(session_id)
        logger.info(f"🧹 Contexte effacé pour session {session_id}")
    except Exception as e:
        logger.error(f"❌ Erreur effacement contexte: {e}")

def get_memory_status() -> Dict[str, Any]:
    """🚨 VERSION SÉCURISÉE: Retourne le statut du système de mémoire avec info cache sécurisé"""
    return {
        "memory_available": MEMORY_AVAILABLE,
        "postgres_enabled": MEMORY_AVAILABLE,
        "fallback_type": "in_memory" if not MEMORY_AVAILABLE else "postgresql",
        "auto_extraction_enabled": True,
        "context_expiry_minutes": 10,
        "version": "memory_safe_v1.0",
        # 🚨 SÉCURISÉ: Informations sur le cache d'extraction limitées
        "extraction_cache": {
            "enabled": CACHE_ENABLED,
            "current_size": len(_EXTRACTION_CACHE),
            "max_size": _CACHE_MAX_SIZE,
            "ttl_seconds": _CACHE_TTL_SECONDS,
            "memory_safe": True,  # 🚨 NOUVEAU
            "emergency_cleanup": True,  # 🚨 NOUVEAU
        },
        "memory_optimizations": [
            "cache_size_limited_to_25",
            "ttl_reduced_to_5min", 
            "emergency_cleanup_enabled",
            "conditional_cache_activation",
            "frequent_garbage_collection"
        ]
    }

# 🚨 NOUVELLES FONCTIONS DE SÉCURITÉ MÉMOIRE
def clear_extraction_cache(extraction_type: Optional[str] = None):
    """🚨 VERSION SÉCURISÉE: Vide le cache d'extraction avec garbage collection"""
    global _EXTRACTION_CACHE
    
    if extraction_type is None:
        cleared_count = len(_EXTRACTION_CACHE)
        _EXTRACTION_CACHE.clear()
        gc.collect()  # Force garbage collection
        logger.info(f"🧹 [CACHE] Cache entièrement vidé: {cleared_count} entrées supprimées")
    else:
        keys_to_remove = [key for key in _EXTRACTION_CACHE.keys() if key.endswith(f":{extraction_type}")]
        for key in keys_to_remove:
            _EXTRACTION_CACHE.pop(key, None)
        gc.collect()
        logger.info(f"🧹 [CACHE] Cache {extraction_type} vidé: {len(keys_to_remove)} entrées supprimées")

def get_cache_stats() -> Dict[str, Any]:
    """🚨 VERSION SÉCURISÉE: Statistiques de cache avec informations mémoire"""
    type_counts = {}
    for key in _EXTRACTION_CACHE.keys():
        extraction_type = key.split(':')[1] if ':' in key else 'unknown'
        type_counts[extraction_type] = type_counts.get(extraction_type, 0) + 1
    
    return {
        "total_entries": len(_EXTRACTION_CACHE),
        "max_capacity": _CACHE_MAX_SIZE,
        "utilization_percent": (len(_EXTRACTION_CACHE) / _CACHE_MAX_SIZE) * 100 if _CACHE_MAX_SIZE > 0 else 0,
        "entries_by_type": type_counts,
        "ttl_seconds": _CACHE_TTL_SECONDS,
        "cache_enabled": CACHE_ENABLED,
        "memory_safe_mode": True,  # 🚨 NOUVEAU
        "emergency_threshold": 50,  # 🚨 NOUVEAU
        "memory_usage_estimate_kb": len(_EXTRACTION_CACHE) * 0.1  # Estimation très conservative
    }

# Les fonctions de debug conservées mais simplifiées pour éviter surcharge mémoire...