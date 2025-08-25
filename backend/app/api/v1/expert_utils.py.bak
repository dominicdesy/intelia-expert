# app/api/v1/expert_utils.py
# -*- coding: utf-8 -*-
"""
Utilitaires et fonctions helper pour expert.py
Extraction des fonctions de support technique
"""

import logging
import os
import re
import math
import time
import asyncio
from typing import Optional, Any, Dict, List
from fastapi import Request

logger = logging.getLogger(__name__)

# ===== Import numpy sécurisé =====
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

# ===== Cache simple pour PerfStore =====
_store_cache = {}

def get_cached_store(species: str):
    """Cache simple pour éviter de recharger le même store"""
    if species not in _store_cache:
        try:
            from .pipeline.perf_store import PerfStore  # type: ignore
            _store_cache[species] = PerfStore(root=os.environ.get("RAG_INDEX_ROOT", "./rag_index"), species=species)
        except Exception as e:
            logger.error(f"Failed to create PerfStore for {species}: {e}")
            return None
    return _store_cache[species]

# ===== Fonction locale pour normalisation des entités =====
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

# ===== Extraction user info =====
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
    """
    Extrait l'user_id pour la persistance des conversations
    Retourne None pour les utilisateurs non authentifiés (publics)
    """
    if not current_user:
        return None
    
    # Priorité: email > user_id > sub > id
    for key in ['email', 'user_id', 'sub', 'id']:
        if current_user.get(key):
            return str(current_user[key])
    
    return "authenticated_unknown"

# ===== Fonction de nettoyage JSON améliorée =====
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

# ===== Parsing d'âge amélioré =====
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

# ===== Fonctions async optimisées =====
async def increment_quota_async(user_email: str) -> bool:
    """Version async pour l'incrémentation du quota"""
    try:
        from app.api.v1.billing import increment_quota_usage
        # Pour l'instant, wrapper la fonction sync en thread
        # TODO: Remplacer par vrai async quand billing.py sera optimisé
        await asyncio.to_thread(increment_quota_usage, user_email, success=True)
        logger.info(f"📊 Usage incrémenté pour {user_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur incrémentation quota (success): {e}")
        raise

async def log_analytics_async(
    current_user: Optional[Dict[str, Any]], 
    payload: Any, 
    result: Dict[str, Any], 
    start_time: float
) -> bool:
    """Version async pour le logging analytics"""
    try:
        from app.api.v1.logging import log_question_to_analytics
        
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
        
        # Extraire le score de confidence dans les analytics
        confidence_score = result.get("confidence", {}).get("score")
        confidence_level = result.get("confidence", {}).get("level")
        
        # Pour l'instant, wrapper la fonction sync en thread
        # TODO: Remplacer par vrai async quand logging.py sera optimisé
        await asyncio.to_thread(
            log_question_to_analytics,
            current_user=current_user,
            payload=payload,
            result=result,
            response_text=response_text[:500],  # Limiter la taille pour analytics
            processing_time_ms=processing_time,
            # Paramètres de confidence pour analytics
            confidence_score=confidence_score,
            confidence_level=confidence_level
        )
        logger.info("📊 Question loggée dans analytics avec confidence")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur logging analytics: {e}")
        raise

async def execute_background_tasks_async(
    user_email: Optional[str],
    current_user: Optional[Dict[str, Any]],
    payload: Any,
    result: Dict[str, Any],
    start_time: float
) -> None:
    """
    🚀 OPTIMISATION PERFORMANCE: Exécute les tâches de fond en parallèle
    
    Gain estimé: 1-1.5 secondes par requête
    """
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
    
    # Traiter les erreurs individuellement (ne pas faire échouer la requête)
    task_names = []
    if user_email:
        task_names.append("quota_increment")
    task_names.append("analytics_logging")
    
    for i, task_result in enumerate(results):
        if isinstance(task_result, Exception):
            task_name = task_names[i] if i < len(task_names) else f"task_{i}"
            logger.error(f"❌ Erreur tâche {task_name}: {task_result}")
        # Les succès sont déjà loggés dans les fonctions individuelles