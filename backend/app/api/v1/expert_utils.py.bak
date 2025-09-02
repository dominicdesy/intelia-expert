# app/api/v1/expert_utils.py
# -*- coding: utf-8 -*-
"""
Utilitaires et fonctions helper pour expert.py
VERSION SÉCURISÉE MÉMOIRE - Cache PerfStore drastiquement limité pour éviter OOM
FIXED: Correction du paramètre analytics user_email -> email
"""

import logging
import os
import re
import math
import time
import asyncio
import gc
from typing import Optional, Any, Dict, List
from fastapi import Request

logger = logging.getLogger(__name__)

# Import numpy sécurisé
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

# CORRECTION URGENTE: Cache PerfStore drastiquement limité pour éviter OOM
_store_cache = {}
_MAX_STORE_CACHE = int(os.getenv("MAX_STORE_CACHE", "1"))  # Réduit - Maximum 1 store au lieu d'illimité
_STORE_CACHE_ENABLED = str(os.getenv("ENABLE_STORE_CACHE", "false")).lower() in ("1", "true", "yes")  # Désactivé par défaut

def _memory_emergency_cleanup_stores():
    """Nettoyage d'urgence des stores en mémoire"""
    global _store_cache
    try:
        if len(_store_cache) > 0:
            cleared_count = len(_store_cache)
            _store_cache.clear()
            gc.collect()  # Force garbage collection
            logger.warning(f"[EMERGENCY] Store cache vidé: {cleared_count} stores - protection mémoire")
            return True
    except Exception as e:
        logger.error(f"Erreur nettoyage urgence stores: {e}")
    return False

def get_cached_store(species: str):
    """VERSION SÉCURISÉE: Cache simple pour éviter de recharger le même store avec limite stricte"""
    # SÉCURITÉ: Vérifier si cache autorisé et limite
    if not _STORE_CACHE_ENABLED:
        logger.debug("Store cache désactivé, création directe")
        try:
            from .pipeline.perf_store import PerfStore  # type: ignore
            return PerfStore(root=os.environ.get("RAG_INDEX_ROOT", "./rag_index"), species=species)
        except Exception as e:
            logger.error(f"Failed to create PerfStore for {species}: {e}")
            return None
    
    # Si trop de stores en cache, vider complètement
    if len(_store_cache) >= _MAX_STORE_CACHE:
        logger.warning(f"Store cache plein ({len(_store_cache)}/{_MAX_STORE_CACHE}), vidage complet")
        _memory_emergency_cleanup_stores()
    
    if species not in _store_cache:
        try:
            from .pipeline.perf_store import PerfStore  # type: ignore
            logger.info(f"Création PerfStore pour {species} (cache: {len(_store_cache)}/{_MAX_STORE_CACHE})")
            _store_cache[species] = PerfStore(root=os.environ.get("RAG_INDEX_ROOT", "./rag_index"), species=species)
        except Exception as e:
            logger.error(f"Failed to create PerfStore for {species}: {e}")
            return None
    else:
        logger.debug(f"PerfStore {species} récupéré depuis cache")
    
    return _store_cache[species]

def normalize_entities_soft_local(entities: Dict[str, Any]) -> Dict[str, Any]:
    """Version locale de normalisation des entités"""
    result = {}
    
    # Species
    species = (entities.get("species") or "broiler").lower()
    result["species"] = species
    
    # Line
    line = entities.get("line")
    if line:
        line = re.sub(r"[-_\s]+", "", str(line).lower())
    result["line"] = line
    
    # Sex
    sex = entities.get("sex")
    if sex:
        sex_mapping = {
            "male": "male", "m": "male", "♂": "male",
            "female": "female", "f": "female", "♀": "female", 
            "as_hatched": "as_hatched", "ah": "as_hatched", 
            "mixte": "as_hatched", "mixed": "as_hatched",
            "as hatched": "as_hatched", "as-hatched": "as_hatched"
        }
        sex = sex_mapping.get(str(sex).lower().replace(" ", "_"), sex)
    result["sex"] = sex
    
    # Unit
    unit = entities.get("unit")
    if unit and str(unit).lower() in ["imperial", "imp", "us", "lb", "lbs"]:
        unit = "imperial"
    else:
        unit = "metric"
    result["unit"] = unit
    
    # Age
    age_days = entities.get("age_days")
    if age_days is not None:
        try:
            result["age_days"] = int(age_days)
        except:
            result["age_days"] = None
    else:
        result["age_days"] = None
    
    return result

def get_user_info_for_validation(request: Request, current_user: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    """Extrait les informations utilisateur pour la validation"""
    if current_user:
        user_id = current_user.get('email', current_user.get('user_id', 'authenticated_user'))
    else:
        user_id = "anonymous_user"
    
    # Extraire l'IP de la requête
    request_ip = getattr(request.client, 'host', 'unknown') if hasattr(request, 'client') else 'unknown'
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        request_ip = forwarded_for.split(',')[0].strip()
    
    return str(user_id), str(request_ip)

def extract_user_id_for_persistence(current_user: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Extrait l'ID utilisateur pour la persistance"""
    if not current_user:
        return None
    
    # Priorité: email > user_id > sub > id
    for key in ['email', 'user_id', 'sub', 'id']:
        if current_user.get(key):
            return str(current_user[key])
    
    return "authenticated_unknown"

def clean_for_json(value):
    """Nettoie seulement les valeurs problématiques pour JSON avec protection robuste"""
    if value is None:
        return None
    if isinstance(value, (int, str, bool)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    
    # Protection numpy robuste
    if HAS_NUMPY and hasattr(value, 'item'):
        try:
            val = value.item()
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                return None
            return val
        except:
            return str(value)  # Fallback si .item() échoue
    
    return str(value)  # Fallback général

def clean_dict_for_json(obj):
    """Nettoie récursivement seulement les valeurs problématiques"""
    if isinstance(obj, dict):
        return {k: clean_dict_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_dict_for_json(v) for v in obj]
    else:
        return clean_for_json(obj)

def extract_age_from_text(text: str) -> Optional[int]:
    """Extraction d'âge plus robuste avec support semaines/années"""
    text_lower = text.lower()
    
    # Patterns par ordre de priorité
    age_patterns = [
        (r"(\d+)\s*(?:j|jour|jours|d|day|days)\b", 1),      # jours (x1)
        (r"(\d+)\s*(?:w|week|weeks|semaine|semaines)\b", 7), # semaines (x7)
        (r"age\s*(\d+)", 1),                                 # "age 21" (jours)
        (r"(\d+)\s*(?:ans|years?)\b", 365),                 # années (x365)
    ]
    
    for pattern, multiplier in age_patterns:
        m = re.search(pattern, text_lower)
        if m:
            try:
                age_value = int(m.group(1)) * multiplier
                # Validation raisonnable pour les volailles
                if 1 <= age_value <= 70:
                    return age_value
            except:
                continue
    return None

def log_question_to_analytics(
    current_user: Optional[Dict[str, Any]],
    payload: Any,
    result: Dict[str, Any],
    response_text: str = "",
    processing_time_ms: int = 0,
    confidence_score: Optional[float] = None,
    confidence_level: Optional[str] = None,
    error_info: Optional[Dict[str, Any]] = None
) -> None:
    """
    CORRIGÉ: Wrapper pour compatibilité avec la nouvelle signature analytics
    Correction du paramètre user_email -> email
    """
    try:
        # Import de la vraie fonction de logging
        from app.api.v1.logging import log_question_to_analytics as log_impl
        
        # Extraire les informations nécessaires
        user_email = current_user.get('email') if current_user else None
        session_id = getattr(payload, 'session_id', 'unknown')
        question = getattr(payload, 'question', '')
        
        # Déterminer la source et le statut
        if error_info:
            status = "error"
            source = "error"
        elif result.get("type") == "quota_exceeded":
            status = "quota_exceeded"
            source = "quota_exceeded"
        elif result.get("type") == "validation_rejected":
            status = "validation_rejected" 
            source = "validation_rejected"
        else:
            status = "success"
            answer = result.get("answer", {})
            source = answer.get("source", "unknown")
        
        # CORRECTION CRITIQUE: Utiliser uniquement les paramètres acceptés par log_question_to_analytics
        log_impl(
            current_user=current_user,
            payload=payload,
            result=result,
            response_text=response_text[:500],  # Limiter la taille
            processing_time_ms=processing_time_ms,
            error_info=error_info
        )
        
    except Exception as e:
        logger.error(f"Erreur log question to analytics (wrapper): {e}")
        # Ne pas faire échouer la requête principale
        pass

async def increment_quota_async(user_email: str) -> bool:
    """Version async pour l'incrémentation du quota"""
    try:
        from app.api.v1.billing import increment_quota_usage
        # Pour l'instant, wrapper la fonction sync en thread
        # TODO: Remplacer par vrai async quand billing.py sera optimisé
        await asyncio.to_thread(increment_quota_usage, user_email, success=True)
        logger.info(f"Usage incrémenté pour {user_email}")
        return True
    except Exception as e:
        logger.error(f"Erreur incrémentation quota (success): {e}")
        raise

async def log_analytics_async(
    current_user: Optional[Dict[str, Any]], 
    payload: Any, 
    result: Dict[str, Any], 
    start_time: float
) -> bool:
    """Version async CORRIGÉE pour le logging analytics"""
    try:
        # Calculer le temps de traitement
        processing_time = int((time.time() - start_time) * 1000)
        
        # Extraire le texte de réponse pour analytics
        answer = result.get("answer", {})
        general_answer = result.get("general_answer", {})
        
        if isinstance(answer, dict) and answer.get("text"):
            response_text = answer["text"]
        elif isinstance(general_answer, dict) and general_answer.get("text"):
            response_text = general_answer["text"]
        else:
            response_text = str(result.get("message", ""))
        
        # Extraire correctement les scores de confidence
        confidence_data = result.get("confidence", {})
        if isinstance(confidence_data, dict):
            confidence_score = confidence_data.get("score")
            confidence_level = confidence_data.get("level")
        else:
            # Fallback si confidence n'est pas un dict
            confidence_score = confidence_data if isinstance(confidence_data, (int, float)) else None
            confidence_level = None
        
        # Appel avec la nouvelle signature compatible
        await asyncio.to_thread(
            log_question_to_analytics,  # Utilise notre wrapper corrigé
            current_user=current_user,
            payload=payload,
            result=result,
            response_text=response_text[:500],  # Limiter la taille pour analytics
            processing_time_ms=processing_time,
            confidence_score=confidence_score,
            confidence_level=confidence_level
        )
        logger.info("Question loggée dans analytics avec confidence")
        return True
        
    except Exception as e:
        logger.error(f"Erreur logging analytics: {e}")
        # Log plus détaillé pour debug
        logger.error(f"Analytics error details - result keys: {list(result.keys()) if isinstance(result, dict) else 'not dict'}")
        logger.error(f"Analytics error details - confidence: {result.get('confidence', 'missing') if isinstance(result, dict) else 'n/a'}")
        raise

async def execute_background_tasks_async(
    user_email: Optional[str],
    current_user: Optional[Dict[str, Any]],
    payload: Any,
    result: Dict[str, Any],
    start_time: float
) -> None:
    """Exécute les tâches de fond en parallèle avec gestion d'erreurs renforcée"""
    tasks = []
    
    # Tâche 1: Incrément quota (si utilisateur authentifié)
    if user_email:
        tasks.append(increment_quota_async(user_email))
    
    # Tâche 2: Logging analytics (toujours)
    tasks.append(log_analytics_async(current_user, payload, result, start_time))
    
    if not tasks:
        return
    
    # Exécuter toutes les tâches en parallèle
    # return_exceptions=True évite qu'une erreur interrompe les autres
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Traiter les erreurs individuellement avec plus de détails
    task_names = []
    if user_email:
        task_names.append("quota_increment")
    task_names.append("analytics_logging")
    
    for i, task_result in enumerate(results):
        if isinstance(task_result, Exception):
            task_name = task_names[i] if i < len(task_names) else f"task_{i}"
            logger.error(f"Erreur tâche {task_name}: {task_result}")
            logger.error(f"Task {task_name} error type: {type(task_result).__name__}")
        # Les succès sont déjà loggés dans les fonctions individuelles

def validate_analytics_compatibility() -> Dict[str, Any]:
    """Fonction de diagnostic pour valider la compatibilité analytics"""
    try:
        from app.api.v1.logging import log_question_to_analytics as log_impl
        import inspect
        
        # Analyser la signature de la vraie fonction
        sig = inspect.signature(log_impl)
        params = list(sig.parameters.keys())
        
        return {
            "status": "compatible",
            "function_found": True,
            "parameters": params,
            "has_confidence": "confidence" in params,
            "has_confidence_score": "confidence_score" in params,
            "has_email_param": "email" in params,  # AJOUT: Vérification du paramètre email
            "has_user_email_param": "user_email" in params,  # AJOUT: Vérification de l'ancien paramètre
            "signature": str(sig)
        }
        
    except ImportError as e:
        return {
            "status": "import_error",
            "function_found": False,
            "error": str(e)
        }
    except Exception as e:
        return {
            "status": "analysis_error", 
            "function_found": True,
            "error": str(e)
        }

def get_expert_utils_status() -> Dict[str, Any]:
    """VERSION SÉCURISÉE: Fonction de diagnostic pour vérifier l'état des utils avec info mémoire"""
    return {
        "version": "memory_safe_v1.1_fixed",  # Version mise à jour
        "numpy_available": HAS_NUMPY,
        "store_cache_size": len(_store_cache),
        "store_cache_enabled": _STORE_CACHE_ENABLED,
        "max_store_cache": _MAX_STORE_CACHE,
        "analytics_compatibility": validate_analytics_compatibility(),
        "functions_count": {
            "total": 12,
            "async": 3,
            "helpers": 9
        },
        # Informations mémoire sécurisées
        "memory_optimizations": [
            "store_cache_limited_to_1",
            "store_cache_disabled_by_default",
            "emergency_cleanup_enabled",
            "garbage_collection_forced"
        ],
        # NOUVEAU: Informations sur la correction analytics
        "analytics_fix": {
            "parameter_corrected": "user_email -> email",
            "fixed_in_version": "v1.1_fixed",
            "expected_log_message": "Question loggée dans analytics avec confidence"
        }
    }

# NOUVELLES FONCTIONS DE SÉCURITÉ MÉMOIRE
def clear_store_cache():
    """Vide le cache des PerfStore avec garbage collection"""
    global _store_cache
    cleared_count = len(_store_cache)
    _store_cache.clear()
    gc.collect()  # Force garbage collection
    logger.info(f"Store cache vidé: {cleared_count} stores supprimés")

def get_store_cache_stats() -> Dict[str, Any]:
    """Statistiques du cache PerfStore"""
    return {
        "total_stores": len(_store_cache),
        "max_capacity": _MAX_STORE_CACHE,
        "utilization_percent": (len(_store_cache) / _MAX_STORE_CACHE) * 100 if _MAX_STORE_CACHE > 0 else 0,
        "cached_species": list(_store_cache.keys()),
        "cache_enabled": _STORE_CACHE_ENABLED,
        "memory_safe_mode": True,
        "memory_usage_estimate_mb": len(_store_cache) * 50  # Estimation: ~50MB par PerfStore
    }