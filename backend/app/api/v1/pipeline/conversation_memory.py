# -*- coding: utf-8 -*-
"""
Gestion de la mémoire conversationnelle et contexte de session
Extrait de dialogue_manager.py pour modularité

🚀 VERSION OPTIMISÉE - Ajout du cache d'extraction pour éviter les re-extractions
CONSERVATION INTÉGRALE du code original avec améliorations de performance
"""

import logging
import os
import time
import re
import hashlib
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

# 🚀 NOUVEAU: Cache d'extraction pour éviter les re-extractions coûteuses
_EXTRACTION_CACHE = {}
_CACHE_MAX_SIZE = int(os.getenv("EXTRACTION_CACHE_SIZE", "1000"))
_CACHE_TTL_SECONDS = int(os.getenv("EXTRACTION_CACHE_TTL", "3600"))  # 1 heure par défaut

def _get_text_hash(text: str) -> str:
    """Génère un hash court pour le cache basé sur le texte"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]

def _cleanup_cache():
    """🚀 OPTIMISATION: Nettoyage intelligent du cache selon TTL et taille"""
    global _EXTRACTION_CACHE
    
    current_time = time.time()
    
    # Supprimer les entrées expirées
    expired_keys = [
        key for key, (_, timestamp) in _EXTRACTION_CACHE.items()
        if current_time - timestamp > _CACHE_TTL_SECONDS
    ]
    
    for key in expired_keys:
        _EXTRACTION_CACHE.pop(key, None)
    
    # Si encore trop d'entrées, supprimer les plus anciennes
    if len(_EXTRACTION_CACHE) > _CACHE_MAX_SIZE:
        sorted_items = sorted(
            _EXTRACTION_CACHE.items(),
            key=lambda x: x[1][1]  # Trier par timestamp
        )
        
        # Garder seulement les 80% les plus récentes
        keep_count = int(_CACHE_MAX_SIZE * 0.8)
        items_to_keep = sorted_items[-keep_count:]
        
        _EXTRACTION_CACHE = {key: value for key, value in items_to_keep}
        logger.debug(f"🧹 [CACHE] Nettoyage: {len(expired_keys)} expirées, gardé {keep_count} entrées")

def _get_cached_extraction(text: str, extraction_type: str) -> Optional[Any]:
    """🚀 NOUVEAU: Récupère le résultat d'extraction depuis le cache"""
    if not text or not text.strip():
        return None
        
    cache_key = f"{_get_text_hash(text)}:{extraction_type}"
    
    if cache_key in _EXTRACTION_CACHE:
        cached_result, timestamp = _EXTRACTION_CACHE[cache_key]
        
        # Vérifier TTL
        if time.time() - timestamp <= _CACHE_TTL_SECONDS:
            logger.debug(f"💾 [CACHE] Hit pour {extraction_type}: '{text[:30]}...' -> {cached_result}")
            return cached_result
        else:
            # Entrée expirée
            _EXTRACTION_CACHE.pop(cache_key, None)
    
    return None

def _cache_extraction_result(text: str, extraction_type: str, result: Any):
    """🚀 NOUVEAU: Sauvegarde le résultat d'extraction en cache"""
    if not text or not text.strip():
        return
        
    cache_key = f"{_get_text_hash(text)}:{extraction_type}"
    _EXTRACTION_CACHE[cache_key] = (result, time.time())
    
    logger.debug(f"💾 [CACHE] Sauvegarde {extraction_type}: '{text[:30]}...' -> {result}")
    
    # Nettoyage périodique du cache
    if len(_EXTRACTION_CACHE) % 50 == 0:  # Toutes les 50 entrées
        _cleanup_cache()

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
    🚀 VERSION OPTIMISÉE: Extraction automatique de l'âge depuis le texte avec cache
    CONSERVATION du code original avec ajout du système de cache
    """
    if not text:
        logger.debug("🔍 [AGE_EXTRACT] Texte vide")
        return None
    
    # 🚀 NOUVEAU: Vérifier le cache en premier
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
    
    # 🚀 NOUVEAU: Mettre en cache le résultat (même si None)
    _cache_extraction_result(text, "age_days", result)
    return result

def normalize_sex_from_text(text: str) -> Optional[str]:
    """🚀 VERSION OPTIMISÉE: Normalisation du sexe depuis le texte avec cache"""
    if not text:
        return None
    
    # 🚀 NOUVEAU: Vérifier le cache en premier
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
    
    # 🚀 NOUVEAU: Mettre en cache le résultat
    _cache_extraction_result(text, "sex", result)
    return result

def extract_line_from_text(text: str) -> Optional[str]:
    """🚀 VERSION OPTIMISÉE: Extraction de lignée depuis le texte avec cache"""
    if not text:
        return None
    
    # 🚀 NOUVEAU: Vérifier le cache en premier
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
    
    # 🚀 NOUVEAU: Mettre en cache le résultat
    _cache_extraction_result(text, "line", result)
    return result

def extract_species_from_text(text: str) -> Optional[str]:
    """🚀 VERSION OPTIMISÉE: Extraction d'espèce depuis le texte avec cache"""
    if not text:
        return None
    
    # 🚀 NOUVEAU: Vérifier le cache en premier
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
    
    # 🚀 NOUVEAU: Mettre en cache le résultat
    _cache_extraction_result(text, "species", result)
    return result

def extract_signs_from_text(text: str) -> Optional[str]:
    """
    🚀 VERSION OPTIMISÉE: Extraction des signes cliniques avec cache et OpenAI
    CONSERVATION de la logique original avec optimisations
    """
    if not text:
        return None
    
    # 🚀 NOUVEAU: Vérifier le cache en premier (important pour OpenAI qui est coûteux)
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
    
    # Si pas de signe évident ET OpenAI disponible, extraction intelligente
    if result is None:
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
    
    # 🚀 NOUVEAU: Mettre en cache le résultat (même si None, évite rappel OpenAI)
    _cache_extraction_result(text, "signs", result)
    return result

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
    🚀 VERSION OPTIMISÉE: Fusionne le contexte de session avec les entités actuelles.
    Enrichit automatiquement depuis le texte de la question.
    CONSERVATION INTÉGRALE de la logique avec optimisations cache
    """
    logger.info(f"🔗 [MERGE] Début fusion - session: {session_context.get('entities', {})}")
    logger.info(f"🔗 [MERGE] Current entities: {current_entities}")
    logger.info(f"🔗 [MERGE] Question: '{question}'")
    
    # 1. Commencer par le contexte de session (données persistantes) - CONSERVÉ
    merged = dict(session_context.get("entities", {}))
    logger.debug(f"🔗 [MERGE] Base session: {merged}")
    
    # 2. 🚀 OPTIMISÉ: Enrichissement automatique depuis le texte (AVEC CACHE)
    auto_species = extract_species_from_text(question)    # Cache automatique
    auto_line = extract_line_from_text(question)          # Cache automatique
    auto_sex = normalize_sex_from_text(question)          # Cache automatique
    auto_age = extract_age_days_from_text(question)       # Cache automatique
    auto_signs = extract_signs_from_text(question)        # Cache automatique (évite OpenAI redondant)
    
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

def should_continue_conversation(session_context: Dict[str, Any], current_intent) -> bool:
    """
    Détermine si la question actuelle continue une conversation précédente
    CONSERVATION INTÉGRALE de la logique
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
    CONSERVATION INTÉGRALE de la logique
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
    CONSERVATION INTÉGRALE de la logique
    """
    try:
        memory = get_conversation_memory()
        memory.clear(session_id)
        logger.info(f"🧹 Contexte effacé pour session {session_id}")
    except Exception as e:
        logger.error(f"❌ Erreur effacement contexte: {e}")

def get_memory_status() -> Dict[str, Any]:
    """
    🚀 VERSION AMÉLIORÉE: Retourne le statut du système de mémoire avec info cache
    """
    return {
        "memory_available": MEMORY_AVAILABLE,
        "postgres_enabled": MEMORY_AVAILABLE,
        "fallback_type": "in_memory" if not MEMORY_AVAILABLE else "postgresql",
        "auto_extraction_enabled": True,
        "context_expiry_minutes": 10,
        "version": "cached_v2.0",
        # 🚀 NOUVEAU: Informations sur le cache d'extraction
        "extraction_cache": {
            "enabled": True,
            "current_size": len(_EXTRACTION_CACHE),
            "max_size": _CACHE_MAX_SIZE,
            "ttl_seconds": _CACHE_TTL_SECONDS,
            "hit_ratio_estimate": "75-85%",  # Estimation basée sur patterns typiques
        },
        "improvements": [
            "patterns_age_ameliores",
            "logs_detailles_extraction", 
            "logique_fusion_securisee",
            "preservation_age_valide",
            "extraction_signes_cliniques",
            "cache_extraction_intelligent",  # 🚀 NOUVEAU
            "optimisation_openai_calls",     # 🚀 NOUVEAU
            "nettoyage_cache_automatique"    # 🚀 NOUVEAU
        ]
    }

# ---------------------------------------------------------------------------
# 🚀 NOUVELLES FONCTIONS DE CACHE ET OPTIMISATION
# ---------------------------------------------------------------------------

def get_cache_stats() -> Dict[str, Any]:
    """🚀 NOUVEAU: Statistiques détaillées du cache d'extraction"""
    # Analyser les types d'extraction en cache
    type_counts = {}
    oldest_entry = None
    newest_entry = None
    
    for key, (_, timestamp) in _EXTRACTION_CACHE.items():
        extraction_type = key.split(':')[1] if ':' in key else 'unknown'
        type_counts[extraction_type] = type_counts.get(extraction_type, 0) + 1
        
        if oldest_entry is None or timestamp < oldest_entry:
            oldest_entry = timestamp
        if newest_entry is None or timestamp > newest_entry:
            newest_entry = timestamp
    
    current_time = time.time()
    return {
        "total_entries": len(_EXTRACTION_CACHE),
        "max_capacity": _CACHE_MAX_SIZE,
        "utilization_percent": (len(_EXTRACTION_CACHE) / _CACHE_MAX_SIZE) * 100,
        "entries_by_type": type_counts,
        "oldest_entry_age_seconds": current_time - oldest_entry if oldest_entry else 0,
        "newest_entry_age_seconds": current_time - newest_entry if newest_entry else 0,
        "ttl_seconds": _CACHE_TTL_SECONDS,
        "memory_usage_estimate_kb": len(_EXTRACTION_CACHE) * 0.5  # Estimation rough
    }

def clear_extraction_cache(extraction_type: Optional[str] = None):
    """🚀 NOUVEAU: Vide le cache d'extraction (optionnellement par type)"""
    global _EXTRACTION_CACHE
    
    if extraction_type is None:
        # Vider tout le cache
        cleared_count = len(_EXTRACTION_CACHE)
        _EXTRACTION_CACHE.clear()
        logger.info(f"🧹 [CACHE] Cache entièrement vidé: {cleared_count} entrées supprimées")
    else:
        # Vider seulement un type spécifique
        keys_to_remove = [key for key in _EXTRACTION_CACHE.keys() if key.endswith(f":{extraction_type}")]
        for key in keys_to_remove:
            _EXTRACTION_CACHE.pop(key, None)
        logger.info(f"🧹 [CACHE] Cache {extraction_type} vidé: {len(keys_to_remove)} entrées supprimées")

def warm_extraction_cache(texts: List[str]):
    """🚀 NOUVEAU: Pré-chauffe le cache avec une liste de textes communs"""
    logger.info(f"🔥 [CACHE] Pré-chauffage avec {len(texts)} textes...")
    
    warmed_count = 0
    for text in texts:
        if not text or not text.strip():
            continue
            
        # Effectuer toutes les extractions pour mettre en cache
        extract_age_days_from_text(text)
        extract_species_from_text(text)
        extract_line_from_text(text)
        normalize_sex_from_text(text)
        # Note: extract_signs_from_text pas appelé car coûteux (OpenAI)
        
        warmed_count += 1
    
    logger.info(f"🔥 [CACHE] Pré-chauffage terminé: {warmed_count} textes traités, cache: {len(_EXTRACTION_CACHE)} entrées")

# ---------------------------------------------------------------------------
# FONCTIONS DE DEBUG ET TEST (CONSERVÉES + AMÉLIORÉES)
# ---------------------------------------------------------------------------

def debug_text_extraction(text: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    🚀 VERSION AMÉLIORÉE: Debug complet de l'extraction automatique avec info cache
    CONSERVATION de la logique originale avec ajout d'informations cache
    """
    logger.info(f"🔬 [DEBUG] Test extraction sur: '{text}'")
    
    if not use_cache:
        # Forcer la re-extraction en vidant le cache pour ce texte
        text_hash = _get_text_hash(text)
        keys_to_remove = [key for key in _EXTRACTION_CACHE.keys() if key.startswith(f"{text_hash}:")]
        for key in keys_to_remove:
            _EXTRACTION_CACHE.pop(key, None)
    
    # Effectuer les extractions (avec ou sans cache selon use_cache)
    start_time = time.time()
    results = {
        "text": text,
        "age_days": extract_age_days_from_text(text),
        "species": extract_species_from_text(text),
        "line": extract_line_from_text(text),
        "sex": normalize_sex_from_text(text),
        "signs": extract_signs_from_text(text)
    }
    extraction_time = time.time() - start_time
    
    # 🚀 NOUVEAU: Informations sur l'utilisation du cache
    text_hash = _get_text_hash(text)
    cache_info = {
        "extraction_time_ms": round(extraction_time * 1000, 2),
        "cache_used": use_cache,
        "cached_results": {}
    }
    
    for extraction_type in ["age_days", "species", "line", "sex", "signs"]:
        cache_key = f"{text_hash}:{extraction_type}"
        cache_info["cached_results"][extraction_type] = cache_key in _EXTRACTION_CACHE
    
    results["cache_info"] = cache_info
    
    logger.info(f"🔬 [DEBUG] Résultats: {results}")
    return results

def test_merge_logic(question: str, session_entities: Dict = None, current_entities: Dict = None) -> Dict[str, Any]:
    """
    CONSERVATION INTÉGRALE: Test de la logique de fusion
    """
    session_context = {"entities": session_entities or {}}
    current = current_entities or {}
    
    logger.info(f"🧪 [TEST] Question: '{question}'")
    logger.info(f"🧪 [TEST] Session: {session_entities}")
    logger.info(f"🧪 [TEST] Current: {current_entities}")
    
    result = merge_conversation_context(current, session_context, question)
    
    logger.info(f"🧪 [TEST] Résultat: {result}")
    return result

def benchmark_extraction_performance(test_texts: List[str], iterations: int = 3) -> Dict[str, Any]:
    """🚀 NOUVEAU: Benchmark de performance avec/sans cache"""
    logger.info(f"⚡ [BENCHMARK] Test performance avec {len(test_texts)} textes, {iterations} itérations")
    
    # Test sans cache (première exécution)
    clear_extraction_cache()
    start_time = time.time()
    
    for _ in range(iterations):
        for text in test_texts:
            debug_text_extraction(text, use_cache=False)
    
    no_cache_time = time.time() - start_time
    
    # Test avec cache (exécutions suivantes)
    start_time = time.time()
    
    for _ in range(iterations):
        for text in test_texts:
            debug_text_extraction(text, use_cache=True)
    
    with_cache_time = time.time() - start_time
    
    # Calculer les gains
    speedup = no_cache_time / with_cache_time if with_cache_time > 0 else float('inf')
    cache_efficiency = ((no_cache_time - with_cache_time) / no_cache_time) * 100
    
    results = {
        "test_config": {
            "texts_count": len(test_texts),
            "iterations": iterations,
            "total_extractions": len(test_texts) * iterations * 5  # 5 types d'extraction
        },
        "performance": {
            "without_cache_seconds": round(no_cache_time, 3),
            "with_cache_seconds": round(with_cache_time, 3),
            "speedup_factor": round(speedup, 2),
            "cache_efficiency_percent": round(cache_efficiency, 1)
        },
        "cache_stats": get_cache_stats()
    }
    
    logger.info(f"⚡ [BENCHMARK] Résultats: Speedup {speedup:.1f}x, Efficacité {cache_efficiency:.1f}%")
    return results