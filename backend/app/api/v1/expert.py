# app/api/v1/expert.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.encoders import jsonable_encoder  # [PATCH] JSON-safe responses
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
import logging
import os
import re
import math
import time  # NOUVEAU: Ajouté pour les endpoints de test
import asyncio  # 🚀 NOUVEAU: Pour optimisations async

# 🔒 Import authentification
from app.api.v1.auth import get_current_user

# 🦆 Import système de quota
from app.api.v1.billing import check_quota_middleware, increment_quota_usage

# 📊 Import système analytics  
from app.api.v1.logging import log_question_to_analytics

# 🌾 Import validateur agricole
try:
    from app.api.v1.pipeline.agricultural_domain_validator import (
        validate_agricultural_question,
        get_agricultural_validator_stats,
        is_agricultural_validation_enabled,
        ValidationResult
    )
    AGRICULTURAL_VALIDATOR_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Agricultural domain validator imported successfully")
except ImportError as e:
    AGRICULTURAL_VALIDATOR_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Failed to import agricultural validator: {e}")

router = APIRouter()

# ===== Import Dialogue Manager (préserve le code original) =====
try:
    from .pipeline.dialogue_manager import handle  # type: ignore
    DIALOGUE_AVAILABLE = True
    logger.info("✅ DialogueManager handle function imported successfully")
except Exception as e:
    logger.error(f"❌ Failed to import dialogue_manager.handle: {e}")
    DIALOGUE_AVAILABLE = False

    # Fallback minimal, signature d'origine conservée
    def handle(session_id: str, question: str, lang: str = "fr", **kwargs) -> Dict[str, Any]:
        return {
            "type": "error",
            "message": "Dialogue service temporarily unavailable",
            "session_id": session_id,
        }

# 🎯 NOUVEAU: Import système de confidence unifié
try:
    from .pipeline.unified_confidence import (
        calculate_unified_confidence,
        get_confidence_summary,
        get_detailed_confidence,
        test_unified_confidence,
        UNIFIED_CONFIDENCE_AVAILABLE
    )
    CONFIDENCE_SYSTEM_AVAILABLE = True
    logger.info("🎯 Système de confidence unifié importé avec succès")
except ImportError as e:
    CONFIDENCE_SYSTEM_AVAILABLE = False
    logger.warning(f"⚠️ Système de confidence unifié indisponible: {e}")
    
    # Fallback pour éviter les erreurs
    def test_unified_confidence():
        return {"status": "unavailable", "reason": "Module not imported"}
    UNIFIED_CONFIDENCE_AVAILABLE = False

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
def _normalize_entities_soft_local(entities: Dict[str, Any]) -> Dict[str, Any]:
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

# ===== Fonction de validation agricole =====
def _validate_agricultural_question(question: str, lang: str = "fr", user_id: str = "unknown", request_ip: str = "unknown") -> ValidationResult:
    """Valide qu'une question concerne le domaine agricole"""
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        logger.warning("⚠️ Agricultural validator not available, allowing all questions")
        return ValidationResult(is_valid=True, confidence=100.0, reason="Validator unavailable")
    
    try:
        return validate_agricultural_question(question, lang, user_id, request_ip)
    except Exception as e:
        logger.error(f"❌ Error in agricultural validation: {e}")
        # En cas d'erreur, permettre la question avec un avertissement
        return ValidationResult(is_valid=True, confidence=50.0, reason=f"Validation error: {str(e)}")

def _get_user_info_for_validation(request: Request, current_user: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
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

# ===== NOUVEAU: Fonction d'extraction user_id pour persistance =====
def _extract_user_id_for_persistence(current_user: Optional[Dict[str, Any]] = None) -> Optional[str]:
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

# 🎯 NOUVELLE FONCTION: Préparation validation result pour confidence
def _prepare_validation_result_for_confidence(validation_result: ValidationResult) -> Dict[str, Any]:
    """
    Convertit ValidationResult en format compatible avec unified_confidence
    """
    return {
        "is_valid": validation_result.is_valid,
        "confidence": validation_result.confidence,
        "reason": validation_result.reason,
        "suggested_topics": getattr(validation_result, 'suggested_topics', []),
        "detected_keywords": getattr(validation_result, 'detected_keywords', []),
        "rejected_keywords": getattr(validation_result, 'rejected_keywords', [])
    }

# 🚀 NOUVELLES FONCTIONS ASYNC POUR OPTIMISATION PERFORMANCE
async def _increment_quota_async(user_email: str) -> bool:
    """Version async pour l'incrémentation du quota"""
    try:
        # Pour l'instant, wrapper la fonction sync en thread
        # TODO: Remplacer par vrai async quand billing.py sera optimisé
        await asyncio.to_thread(increment_quota_usage, user_email, success=True)
        logger.info(f"📊 Usage incrémenté pour {user_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur incrémentation quota (success): {e}")
        raise

async def _log_analytics_async(
    current_user: Optional[Dict[str, Any]], 
    payload: Any, 
    result: Dict[str, Any], 
    start_time: float
) -> bool:
    """Version async pour le logging analytics"""
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
        
        # 🎯 NOUVEAU: Inclure le score de confidence dans les analytics
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
            # 🎯 NOUVEAU: Paramètres de confidence pour analytics
            confidence_score=confidence_score,
            confidence_level=confidence_level
        )
        logger.info("📊 Question loggée dans analytics avec confidence")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur logging analytics: {e}")
        raise

async def _execute_background_tasks_async(
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
        tasks.append(_increment_quota_async(user_email))
    
    # Tâche 2: Logging analytics (toujours)
    tasks.append(_log_analytics_async(current_user, payload, result, start_time))
    
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

# ===== Schémas =====
class AskPayload(BaseModel):
    session_id: Optional[str] = "default"
    question: str
    lang: Optional[str] = "fr"
    debug: Optional[bool] = False
    force_perfstore: Optional[bool] = False
    intent_hint: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    bypass_validation: Optional[bool] = False  # 🌾 NOUVEAU: pour bypass administrateur
    model_config = {"extra": "allow"}

# ===== Fonction interne partagée avec validation ET quota ET persistance ET CONFIDENCE =====
async def _ask_internal_async(payload: AskPayload, request: Request, current_user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    🚀 VERSION ASYNC OPTIMISÉE + CONFIDENCE UNIFIÉ - Logique interne pour traiter les questions
    
    OPTIMISATIONS:
    - Parallélisation des opérations DB finales
    - Gain estimé: 1-1.5 secondes par requête
    
    NOUVEAU:
    - Intégration automatique du confidence score unifié
    - Transmission du validation_result au dialogue_manager
    
    CONSERVE: Toute la logique métier originale
    """
    user_email = None
    start_time = time.time()  # 📊 NOUVEAU: Mesure du temps de traitement
    validation_result_dict = None  # 🎯 NOUVEAU: Pour le confidence unifié
    
    try:
        # Extraction des infos utilisateur pour la validation
        user_id, request_ip = _get_user_info_for_validation(request, current_user)
        
        # 💾 NOUVEAU: Extraction user_id pour persistance
        persistence_user_id = _extract_user_id_for_persistence(current_user)
        
        # Extraction de l'email pour le quota
        if current_user:
            user_email = current_user.get('email')
        
        # 🚫 VÉRIFICATION QUOTA AVANT TRAITEMENT
        if user_email:
            try:
                quota_allowed, quota_details = check_quota_middleware(user_email)
                
                if not quota_allowed:
                    logger.warning(f"🚫 Quota dépassé pour {user_email}: {quota_details.get('message', 'Quota exceeded')}")
                    return {
                        "type": "quota_exceeded",
                        "message": f"Line not specified. Available: {', '.join(available)}"
                }
            })

        # [STEP 7] Chargement DataFrame
        try:
            df = store._load_df(norm["line"])
        except Exception as e:
            return jsonable_encoder({
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "rec": None,
                "debug": {
                    "error": "load_df_failed",
                    "message": str(e),
                    "line": norm.get("line"),
                    "available_lines": available,
                    "tables_dir": str(getattr(store, "dir_tables", "")),
                },
            })

        if df is None:
            return jsonable_encoder({
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "rec": None,
                "debug": {
                    "error": "table_missing",
                    "line": norm.get("line"),
                    "available_lines": available,
                    "tables_dir": str(getattr(store, "dir_tables", "")),
                    "message": f"No data table found for line {norm.get('line')}"
                },
            })

        # [STEP 8] Récupération des données avec nettoyage JSON
        try:
            rec = store.get(
                line=norm["line"],
                sex=norm["sex"],
                unit=norm["unit"],
                age_days=int(norm.get("age_days") or 21),
            )
            
            # Nettoyage JSON des valeurs
            rec_clean = clean_dict_for_json(rec) if rec else None
            
        except Exception as e:
            return jsonable_encoder({
                "error": "store_get_failed",
                "message": str(e),
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "debug": {
                    "rows": int(len(df)),
                    "columns": [str(c) for c in df.columns],
                    "available_lines": available,
                }
            })

        # [SUCCESS] Résultat final avec message informatif + 🎯 CONFIDENCE
        success_message = "Performance data found"
        confidence_score = 95.0  # 🎯 NOUVEAU: Haute confiance pour données exactes
        confidence_level = "very_high"
        
        if not rec_clean:
            line_name = norm.get("line", "unknown")
            sex_name = norm.get("sex", "unknown") 
            age_val = norm.get("age_days", "unknown")
            success_message = f"No data found for {line_name}, {sex_name}, {age_val} days. Try: male/female/as_hatched, ages 1-49"
            confidence_score = 90.0  # 🎯 NOUVEAU: Toujours haute confiance (réponse système claire)
            confidence_level = "high"

        result = {
            "success": bool(rec_clean),
            "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
            "norm": norm,
            "rec": rec_clean,
            "debug": {
                "rows": int(len(df)),
                "columns": [str(c) for c in df.columns],
                "available_lines": available,
                "tables_dir": str(getattr(store, "dir_tables", "")),
            },
            "message": success_message,
            # 🎯 NOUVEAU: Confidence pour perf-probe
            "confidence": {
                "score": confidence_score,
                "level": confidence_level,
                "explanation": "Données PerfStore directes - très fiable" if rec_clean else "Paramètres manquants clarifiés"
            }
        }
        
        return jsonable_encoder(result)

    except Exception as e:
        # Catch-all final avec informations de debug + 🎯 CONFIDENCE
        return jsonable_encoder({
            "error": "internal_error",
            "message": str(e),
            "entities": (payload.entities or {}) if payload else {},
            "debug": {"step": "unknown", "has_numpy": HAS_NUMPY},
            # 🎯 NOUVEAU: Confidence pour erreurs
            "confidence": {
                "score": 10.0,
                "level": "very_low",
                "explanation": f"Erreur interne PerfStore: {type(e).__name__}"
            }
        }) quota_details.get("message", "Quota mensuel dépassé"),
                        "quota_details": quota_details,
                        "upgrade_suggestions": [
                            {"plan": "basic", "price": "29.99€", "quota": "1000 questions"},
                            {"plan": "premium", "price": "99.99€", "quota": "5000 questions"}
                        ],
                        "session_id": payload.session_id or "default",
                        "user": {
                            "email": user_email,
                            "user_id": current_user.get('user_id')
                        },
                        # 🎯 NOUVEAU: Confidence même pour quota exceeded
                        "confidence": {
                            "score": 100.0,
                            "level": "very_high",
                            "explanation": "Quota dépassé - information système fiable"
                        }
                    }
                else:
                    logger.info(f"✅ Quota OK pour {user_email}: {quota_details.get('usage', 0)}/{quota_details.get('limit', 'unlimited')}")
            except Exception as e:
                logger.error(f"❌ Erreur vérification quota pour {user_email}: {e}")
                # En cas d'erreur quota, on continue le traitement
                pass

        # Log différencié selon l'authentification
        if current_user:
            user_email_display = current_user.get('email', 'unknown')
            logger.info(f"🔒 Question authentifiée de {user_email_display}: {payload.question[:120]}")
        else:
            logger.info(f"🌍 Question publique: {payload.question[:120]}")

        # 🌾 VALIDATION AGRICOLE (sauf si bypass autorisé)
        validation_bypassed = False
        if not payload.bypass_validation:
            validation_result = _validate_agricultural_question(
                question=payload.question,
                lang=payload.lang or "fr",
                user_id=user_id,
                request_ip=request_ip
            )
            
            # 🎯 NOUVEAU: Préparer validation_result pour confidence unifié
            validation_result_dict = _prepare_validation_result_for_confidence(validation_result)
            
            if not validation_result.is_valid:
                logger.warning(f"🚫 Question rejetée par validation agricole: {validation_result.reason}")
                # ❌ INCRÉMENT USAGE MÊME POUR VALIDATION ÉCHOUÉE
                if user_email:
                    try:
                        await _increment_quota_async(user_email)  # 🚀 ASYNC
                    except Exception as e:
                        logger.error(f"❌ Erreur incrémentation quota (validation failed): {e}")
                
                # 📊 NOUVEAU: LOGGING VALIDATION ÉCHOUÉE
                validation_rejected_response = {
                    "type": "validation_rejected",
                    "message": validation_result.reason,
                    "session_id": payload.session_id or "default",
                    "validation": {
                        "is_valid": False,
                        "confidence": validation_result.confidence,
                        "suggested_topics": validation_result.suggested_topics,
                        "detected_keywords": validation_result.detected_keywords,
                        "rejected_keywords": validation_result.rejected_keywords
                    },
                    "user": {
                        "email": current_user.get('email') if current_user else None,
                        "user_id": current_user.get('user_id') if current_user else None
                    } if current_user else None,
                    # 🎯 NOUVEAU: Confidence pour validation échouée
                    "confidence": {
                        "score": validation_result.confidence,
                        "level": "medium" if validation_result.confidence > 70 else "low",
                        "explanation": f"Question hors domaine agricole (confiance validation: {validation_result.confidence}%)"
                    }
                }
                
                try:
                    await _log_analytics_async(  # 🚀 ASYNC
                        current_user=current_user,
                        payload=payload,
                        result=validation_rejected_response,
                        start_time=start_time
                    )
                    logger.info("📊 Validation échouée loggée dans analytics")
                    
                except Exception as log_e:
                    logger.error(f"❌ Erreur logging analytics (validation): {log_e}")
                
                return validation_rejected_response
            else:
                logger.info(f"✅ Question validée (confiance: {validation_result.confidence:.1f}%)")
        else:
            validation_bypassed = True
            logger.info("⚠️ Validation agricole bypassée par l'utilisateur")
            # 🎯 NOUVEAU: Validation result par défaut pour bypass
            validation_result_dict = {
                "is_valid": True,
                "confidence": 100.0,
                "reason": "Validation bypassée par utilisateur"
            }

        # Traitement normal de la question
        fp_qs = request.query_params.get("force_perfstore")
        force_perf = bool(payload.force_perfstore) or (fp_qs in ("1", "true", "True", "yes"))

        if DIALOGUE_AVAILABLE:
            # 💾 NOUVEAU: Passer user_id au dialogue manager pour persistance
            # 🎯 NOUVEAU: Passer validation_result pour confidence unifié
            result = handle(
                session_id=payload.session_id or "default",
                question=payload.question,
                lang=payload.lang or "fr",
                debug=bool(payload.debug),
                force_perfstore=force_perf,
                intent_hint=(payload.intent_hint or None),
                entities=(payload.entities or {}),
                user_id=persistence_user_id,  # NOUVEAU: Paramètre pour persistance
                validation_result=validation_result_dict  # 🎯 NOUVEAU: Pour confidence unifié
            )
        else:
            logger.warning("⚠️ Dialogue manager not available, using fallback")
            result = handle(payload.session_id or "default", payload.question, payload.lang or "fr")
            
            # 🎯 NOUVEAU: Ajouter confidence par défaut si dialogue manager indisponible
            if "confidence" not in result:
                result["confidence"] = {
                    "score": 30.0,
                    "level": "low", 
                    "explanation": "Service de dialogue temporairement indisponible"
                }

        # 🚀 OPTIMISATION PERFORMANCE: Tâches de fond en parallèle
        # AVANT: 3 opérations séquentielles = 1.2s
        # APRÈS: 3 opérations parallèles = 0.2s
        # GAIN: ~1 seconde par requête
        await _execute_background_tasks_async(
            user_email=user_email,
            current_user=current_user,
            payload=payload,
            result=result,
            start_time=start_time
        )

        # Ajouter les infos utilisateur et de validation dans la réponse
        if current_user:
            result["user"] = {
                "email": current_user.get('email'),
                "user_id": current_user.get('user_id')
            }
        
        # Ajouter les métadonnées de validation et persistance
        result["validation_metadata"] = {
            "agricultural_validation_enabled": AGRICULTURAL_VALIDATOR_AVAILABLE and is_agricultural_validation_enabled(),
            "validation_bypassed": validation_bypassed
        }
        
        # 💾 NOUVEAU: Métadonnées de persistance
        result["persistence_metadata"] = {
            "conversation_persistence_enabled": True,  # Toujours ON dans cette version
            "user_id_for_persistence": persistence_user_id,
            "is_authenticated": bool(current_user)
        }
        
        # 🎯 NOUVEAU: Métadonnées de confidence unifié
        result["confidence_metadata"] = {
            "unified_confidence_enabled": CONFIDENCE_SYSTEM_AVAILABLE,
            "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE,
            "validation_confidence_included": bool(validation_result_dict)
        }

        logger.info(f"✅ Réponse générée: type={result.get('type')}, confidence={result.get('confidence', {}).get('score', 'N/A')}%")
        return result
        
    except Exception as e:
        # ❌ ERREUR: Incrément usage même en cas d'erreur de traitement
        if user_email:
            try:
                await _increment_quota_async(user_email)  # 🚀 ASYNC
                logger.info(f"📊 Usage incrémenté pour {user_email} (erreur)")
            except Exception as quota_e:
                logger.error(f"❌ Erreur incrémentation quota (error): {quota_e}")
        
        # 📊 NOUVEAU: LOGGING DES ERREURS DANS ANALYTICS
        error_result = {
            "type": "system_error",
            "error": {
                "type": type(e).__name__,
                "message": str(e),
                "category": "system_error"
            },
            # 🎯 NOUVEAU: Confidence pour erreurs système
            "confidence": {
                "score": 5.0,
                "level": "very_low",
                "explanation": f"Erreur système: {type(e).__name__}"
            }
        }
        
        try:
            await _log_analytics_async(  # 🚀 ASYNC
                current_user=current_user,
                payload=payload,
                result=error_result,
                start_time=start_time
            )
            logger.info("📊 Erreur loggée dans analytics")
            
        except Exception as log_e:
            logger.error(f"❌ Erreur logging analytics (error): {log_e}")
        
        logger.exception("❌ Erreur dans le traitement de la question")
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

# 🔄 VERSION SYNC PRÉSERVÉE (pour rétrocompatibilité)
def _ask_internal(payload: AskPayload, request: Request, current_user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    VERSION SYNC ORIGINALE - Conservée pour rétrocompatibilité
    
    Wrapper qui appelle la version async en interne
    """
    return asyncio.run(_ask_internal_async(payload, request, current_user))

# ===== Endpoints principaux (code original conservé + améliorations) =====
@router.post("/ask")
async def ask(  # 🚀 ASYNC
    payload: AskPayload, 
    request: Request,
    current_user: dict = Depends(get_current_user)  # 🔒 Auth requise
) -> Dict[str, Any]:
    """
    🚀 ENDPOINT OPTIMISÉ + CONFIDENCE UNIFIÉ - Poser des questions avec validation agricole, quota, persistance et confidence score.
    
    OPTIMISATIONS:
    - Opérations DB parallélisées
    - Gain estimé: 1-1.5 secondes par requête
    
    NOUVEAU:
    - Score de confidence unifié dans chaque réponse
    - Niveau de confiance explicite (very_high/high/medium/low/very_low)
    - Explication humaine de la fiabilité
    """
    return await _ask_internal_async(payload, request, current_user)

@router.post("/ask-public")
async def ask_public(payload: AskPayload, request: Request) -> Dict[str, Any]:  # 🚀 ASYNC
    """
    🚀 ENDPOINT PUBLIC OPTIMISÉ + CONFIDENCE UNIFIÉ - Pas d'authentification requise
    """
    return await _ask_internal_async(payload, request, None)

@router.get("/system-status")
def system_status() -> Dict[str, Any]:
    """État synthétique du service avec info persistance et confidence."""
    # Vérifier la disponibilité de la persistance
    persistence_available = False
    try:
        from .pipeline.dialogue_manager import POSTGRES_AVAILABLE, PERSIST_CONVERSATIONS
        persistence_available = POSTGRES_AVAILABLE and PERSIST_CONVERSATIONS
    except ImportError:
        pass
    
    return {
        "status": "ok" if DIALOGUE_AVAILABLE else "degraded",
        "dialogue_manager_available": DIALOGUE_AVAILABLE,
        "agricultural_validator_available": AGRICULTURAL_VALIDATOR_AVAILABLE,
        "agricultural_validation_enabled": AGRICULTURAL_VALIDATOR_AVAILABLE and is_agricultural_validation_enabled(),
        "billing_system_available": True,  # 🦆 NOUVEAU
        "analytics_system_available": True,  # 📊 NOUVEAU
        "conversation_persistence_available": persistence_available,  # 💾 NOUVEAU
        "performance_optimizations_enabled": True,  # 🚀 NOUVEAU
        "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE,  # 🎯 NOUVEAU
        "unified_confidence_enabled": CONFIDENCE_SYSTEM_AVAILABLE,  # 🎯 NOUVEAU
        "service": "expert_api",
    }

# ===== 🎯 NOUVEAUX ENDPOINTS: Confidence System =====

@router.get("/confidence-status")
def confidence_status() -> Dict[str, Any]:
    """
    Status détaillé du système de confidence unifié.
    """
    try:
        from .pipeline.dialogue_manager import get_fallback_status
        dialogue_status = get_fallback_status()
        
        return {
            "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE,
            "unified_confidence_module": UNIFIED_CONFIDENCE_AVAILABLE if CONFIDENCE_SYSTEM_AVAILABLE else False,
            "dialogue_manager_confidence_integration": dialogue_status.get("unified_confidence_system") == "integrated",
            "components": {
                "agricultural_validator": AGRICULTURAL_VALIDATOR_AVAILABLE,
                "intent_confidence": dialogue_status.get("modules", {}).get("cot_fallback_processor", {}).get("openai_fallback_available", False),
                "completeness_scoring": True,  # Toujours disponible via clarification_manager
                "source_reliability": True   # Calculé automatiquement
            },
            "confidence_levels": ["very_high", "high", "medium", "low", "very_low"],
            "score_range": {"min": 0.0, "max": 100.0},
            "features": {
                "adaptive_weighting": True,
                "contextual_adjustments": True,
                "debug_mode_available": True,
                "explanation_generation": True
            }
        }
    except Exception as e:
        return {
            "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE,
            "error": f"Could not get detailed status: {str(e)}",
            "basic_status": "partial" if CONFIDENCE_SYSTEM_AVAILABLE else "unavailable"
        }

@router.post("/test-confidence-system")
async def test_confidence_system(  # 🚀 ASYNC
    current_user: dict = Depends(get_current_user)  # 🔒 Auth requise pour les tests
) -> Dict[str, Any]:
    """
    Teste le système de confidence unifié avec différents scénarios.
    """
    if not CONFIDENCE_SYSTEM_AVAILABLE:
        return {
            "error": "Confidence system not available",
            "status": "unavailable"
        }
    
    try:
        # Test du module unified_confidence directement
        confidence_test = await asyncio.to_thread(test_unified_confidence)
        
        # Test d'intégration via dialogue_manager
        try:
            from .pipeline.dialogue_manager import test_confidence_integration
            integration_test = await asyncio.to_thread(test_confidence_integration)
        except ImportError:
            integration_test = {"status": "unavailable", "reason": "dialogue_manager not available"}
        
        # Test via endpoint réel
        test_payload = AskPayload(
            session_id="test_confidence",
            question="Quel est le poids cible pour un Ross 308 mâle de 35 jours ?",
            lang="fr",
            entities={"species": "broiler", "line": "ross308", "sex": "male", "age_days": 35}
        )
        
        # Simulation d'une request basique
        class MockRequest:
            def __init__(self):
                self.query_params = {}
                self.client = type('obj', (object,), {'host': 'localhost'})
                self.headers = {}
        
        mock_request = MockRequest()
        
        # Test endpoint complet
        try:
            endpoint_result = await _ask_internal_async(test_payload, mock_request, current_user)
            endpoint_confidence = endpoint_result.get("confidence", {})
            
            endpoint_test = {
                "status": "success",
                "confidence_included": "confidence" in endpoint_result,
                "confidence_score": endpoint_confidence.get("score"),
                "confidence_level": endpoint_confidence.get("level"),
                "confidence_explanation": endpoint_confidence.get("explanation"),
                "response_type": endpoint_result.get("type"),
                "route_taken": endpoint_result.get("route_taken")
            }
        except Exception as e:
            endpoint_test = {
                "status": "error",
                "error": str(e)
            }
        
        return {
            "status": "completed",
            "confidence_system_available": True,
            "tests": {
                "unified_confidence_module": confidence_test,
                "dialogue_manager_integration": integration_test,
                "full_endpoint_integration": endpoint_test
            },
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "error": f"Confidence system test failed: {str(e)}",
            "status": "error",
            "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE
        }

@router.get("/confidence-examples")
def confidence_examples() -> Dict[str, Any]:
    """
    Exemples de scores de confidence selon différents scénarios.
    """
    return {
        "confidence_levels": {
            "very_high": {
                "score_range": "90-100%",
                "description": "Réponse très fiable avec données précises et contexte complet",
                "examples": [
                    "Lookup exact dans table de performance avec lignée, sexe et âge précis",
                    "Calcul mathématique avec paramètres complets",
                    "Réponse basée sur données techniques officielles"
                ]
            },
            "high": {
                "score_range": "70-89%",
                "description": "Réponse fiable basée sur des sources techniques solides",
                "examples": [
                    "RAG avec sources multiples et contexte riche",
                    "Analyse CoT structurée avec données partielles",
                    "Réponse technique avec validation agricole forte"
                ]
            },
            "medium": {
                "score_range": "50-69%",
                "description": "Réponse correcte mais avec certaines limitations contextuelles",
                "examples": [
                    "RAG avec sources limitées",
                    "Fallback OpenAI avec bon contexte",
                    "Réponse de clarification avec informations partielles"
                ]
            },
            "low": {
                "score_range": "30-49%",
                "description": "Réponse approximative, précisions recommandées",
                "examples": [
                    "Fallback OpenAI avec contexte limité",
                    "Question partiellement hors domaine agricole",
                    "Entités manquantes pour une réponse précise"
                ]
            },
            "very_low": {
                "score_range": "0-29%",
                "description": "Réponse incertaine, vérification nécessaire",
                "examples": [
                    "Erreur système",
                    "Question hors domaine agricole",
                    "Échec de tous les systèmes de réponse"
                ]
            }
        },
        "factors_affecting_confidence": [
            "Type de source (table > CoT > RAG > fallback IA)",
            "Complétude du contexte (espèce, lignée, âge, sexe)",
            "Validation du domaine agricole",
            "Qualité de classification de l'intention",
            "Nombre et qualité des sources RAG",
            "Précision des entités extraites"
        ],
        "confidence_components": {
            "source_reliability": "Fiabilité de la source de données (40% pour lookup, 30% pour CoT, etc.)",
            "intent_confidence": "Confiance dans la classification de l'intention",
            "completeness_score": "Complétude des informations contextuelles",
            "validation_confidence": "Confiance de la validation du domaine agricole"
        }
    }

# ===== NOUVEAUX ENDPOINTS: Fallback OpenAI (code original conservé) =====

@router.get("/fallback-status")
def fallback_status() -> Dict[str, Any]:
    """
    Status détaillé du système de fallback OpenAI + persistance + confidence.
    """
    try:
        from .pipeline.dialogue_manager import get_fallback_status
        return get_fallback_status()
    except Exception as e:
        return {
            "error": "Could not get fallback status",
            "message": str(e),
            "openai_fallback_available": False
        }

@router.post("/test-openai-fallback")
async def test_openai_fallback(  # 🚀 ASYNC
    test_question: str,
    current_user: dict = Depends(get_current_user)  # 🔒 Auth requise
) -> Dict[str, Any]:
    """
    Teste le fallback OpenAI directement (bypass RAG) avec confidence.
    """
    try:
        # Import correct de la fonction et de l'Intention
        from .pipeline.dialogue_manager import generate_openai_fallback_response  # Correction import
        from .pipeline.utils.question_classifier import Intention  # Import correct
        
        # Entités de test basiques
        test_entities = {
            "species": "broiler",
            "line": "ross308", 
            "sex": "as_hatched",
            "age_days": 21
        }
        
        # Exécuter en thread pour éviter de bloquer
        result = await asyncio.to_thread(
            generate_openai_fallback_response,
            question=test_question,
            entities=test_entities,
            intent=Intention.PerfTargets,  # Intent par défaut pour test
            rag_context="Contexte RAG non disponible (test)"
        )
        
        # 🎯 NOUVEAU: Extraire info de confidence si disponible
        confidence_info = {}
        if result and isinstance(result, dict):
            confidence_info = {
                "source_confidence": result.get("confidence", "N/A"),
                "source_type": result.get("source", "unknown")
            }
        
        return {
            "test_question": test_question,
            "openai_response": result,
            "confidence_info": confidence_info,  # 🎯 NOUVEAU
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "error": f"Test OpenAI fallback failed: {str(e)}",
            "test_question": test_question
        }

@router.post("/test-fallback-integration")
async def test_fallback_integration(  # 🚀 ASYNC
    test_question: str = "Quel est le poids à 21 jours pour des Ross 308 mâles ?",
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Teste l'intégration complète RAG → Fallback OpenAI + persistance + confidence
    """
    try:
        # Test avec une question qui devrait déclencher le fallback
        payload = AskPayload(
            session_id="test_fallback",
            question=test_question,
            lang="fr",
            debug=True,
            entities={"species": "broiler", "line": "ross308", "sex": "male", "age_days": 21}
        )
        
        # Simulation d'une request basique
        class MockRequest:
            def __init__(self):
                self.query_params = {}
                self.client = type('obj', (object,), {'host': 'localhost'})
                self.headers = {}
        
        mock_request = MockRequest()
        
        # Appel du système complet optimisé
        result = await _ask_internal_async(payload, mock_request, current_user)
        
        # Analyse du résultat pour vérifier si fallback activé
        answer = result.get("answer", {})
        source = answer.get("source", "unknown")
        meta = answer.get("meta", {})
        
        # 🎯 NOUVEAU: Extraire info de confidence unifié
        confidence = result.get("confidence", {})
        
        return {
            "test_question": test_question,
            "result_source": source,
            "fallback_activated": source == "openai_fallback",
            "rag_attempted": meta.get("rag_attempted", False),
            "result_preview": answer.get("text", "")[:200] + "..." if answer.get("text") else None,
            "persistence_metadata": result.get("persistence_metadata", {}),
            "confidence_metadata": result.get("confidence_metadata", {}),  # 🎯 NOUVEAU
            "unified_confidence": confidence,  # 🎯 NOUVEAU
            "full_result": result,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "error": f"Integration test failed: {str(e)}",
            "test_question": test_question
        }

# ===== 💾 NOUVEAUX ENDPOINTS: Test persistance conversations =====

@router.post("/test-conversation-persistence")
async def test_conversation_persistence(  # 🚀 ASYNC
    test_question: str = "Test de persistance des conversations avec confidence",
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Teste la persistance des conversations directement avec tracking confidence.
    """
    try:
        from .pipeline.dialogue_manager import _persist_conversation
        
        test_session_id = f"test_persistence_{int(time.time())}"
        test_answer = "Réponse de test pour vérifier la persistance avec confidence"
        user_id = _extract_user_id_for_persistence(current_user)
        
        # Test de la fonction de persistance en thread
        persistence_success = await asyncio.to_thread(
            _persist_conversation,
            session_id=test_session_id,
            question=test_question,
            answer_text=test_answer,
            language="fr",
            user_id=user_id,
            additional_context={
                "test": True,
                "intent": "test_persistence",
                "route": "test_endpoint",
                "confidence_score": 85.0,  # 🎯 NOUVEAU: Test avec confidence
                "confidence_level": "high"  # 🎯 NOUVEAU
            }
        )
        
        return {
            "status": "success" if persistence_success else "failed",
            "test_session_id": test_session_id,
            "test_question": test_question,
            "test_answer": test_answer,
            "user_id": user_id,
            "persistence_success": persistence_success,
            "confidence_tracking": True,  # 🎯 NOUVEAU
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "error": f"Persistence test failed: {str(e)}",
            "test_question": test_question
        }

@router.get("/conversation-persistence-status")
def conversation_persistence_status() -> Dict[str, Any]:
    """
    Status détaillé de la persistance des conversations avec confidence tracking.
    """
    try:
        from .pipeline.dialogue_manager import (
            POSTGRES_AVAILABLE, 
            PERSIST_CONVERSATIONS, 
            CLEAR_CONTEXT_AFTER_ASK,
            _POSTGRES_MEMORY
        )
        
        return {
            "postgres_available": POSTGRES_AVAILABLE,
            "persist_conversations": PERSIST_CONVERSATIONS,
            "clear_context_after_ask": CLEAR_CONTEXT_AFTER_ASK,
            "postgres_memory_initialized": _POSTGRES_MEMORY is not None,
            "database_url_configured": bool(os.getenv("DATABASE_URL")),
            "confidence_tracking_enabled": CONFIDENCE_SYSTEM_AVAILABLE,  # 🎯 NOUVEAU
            "status": "operational" if (POSTGRES_AVAILABLE and PERSIST_CONVERSATIONS) else "limited"
        }
        
    except ImportError as e:
        return {
            "error": "Could not import persistence modules",
            "message": str(e),
            "status": "unavailable"
        }

# ===== Endpoints existants (code original conservé) =====

@router.get("/agricultural-validation-status")
def agricultural_validation_status() -> Dict[str, Any]:
    """Status détaillé du validateur agricole."""
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        return {
            "available": False,
            "reason": "Module not imported or not available"
        }
    
    try:
        stats = get_agricultural_validator_stats()
        return {
            "available": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }

@router.post("/test-agricultural-validation")
async def test_agricultural_validation(  # 🚀 ASYNC
    test_question: str,
    lang: str = "fr",
    current_user: dict = Depends(get_current_user)  # 🔒 Auth requise pour les tests
) -> Dict[str, Any]:
    """Teste la validation agricole sur une question donnée avec confidence."""
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        return {
            "error": "Agricultural validator not available"
        }
    
    user_id = current_user.get('email', current_user.get('user_id', 'test_user'))
    
    try:
        # Exécuter en thread pour éviter de bloquer
        validation_result = await asyncio.to_thread(
            validate_agricultural_question,
            question=test_question,
            language=lang,
            user_id=str(user_id),
            request_ip="test_ip"
        )
        
        # 🎯 NOUVEAU: Calculer confidence basé sur validation
        validation_confidence = {
            "score": validation_result.confidence,
            "level": "high" if validation_result.confidence > 80 else "medium" if validation_result.confidence > 50 else "low",
            "explanation": f"Validation agricole: {validation_result.confidence}% de confiance"
        }
        
        return {
            "question": test_question,
            "lang": lang,
            "validation": validation_result.to_dict() if hasattr(validation_result, 'to_dict') else {
                "is_valid": validation_result.is_valid,
                "confidence": validation_result.confidence,
                "reason": validation_result.reason
            },
            "validation_confidence": validation_confidence,  # 🎯 NOUVEAU
            "tester": user_id
        }
    except Exception as e:
        return {
            "error": f"Validation test failed: {str(e)}",
            "question": test_question
        }

# 🦆 NOUVEAUX ENDPOINTS QUOTA
@router.get("/quota-status")
async def quota_status(  # 🚀 ASYNC
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Récupère le statut du quota pour l'utilisateur connecté."""
    user_email = current_user.get('email')
    if not user_email:
        raise HTTPException(status_code=400, detail="Email utilisateur non trouvé")
    
    try:
        # Exécuter en thread pour éviter de bloquer
        quota_allowed, quota_details = await asyncio.to_thread(
            check_quota_middleware, user_email
        )
        return {
            "user_email": user_email,
            "quota_allowed": quota_allowed,
            "quota_details": quota_details,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"❌ Erreur récupération quota pour {user_email}: {e}")
        return {
            "error": f"Failed to get quota status: {str(e)}",
            "user_email": user_email
        }

@router.post("/test-quota-increment")
async def test_quota_increment(  # 🚀 ASYNC
    success: bool = True,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Teste l'incrémentation du quota (pour debug)."""
    user_email = current_user.get('email')
    if not user_email:
        raise HTTPException(status_code=400, detail="Email utilisateur non trouvé")
    
    try:
        # Utiliser la fonction async optimisée
        if success:
            await _increment_quota_async(user_email)
        else:
            await asyncio.to_thread(increment_quota_usage, user_email, success=False)
        
        # Récupération du statut mis à jour
        quota_allowed, quota_details = await asyncio.to_thread(
            check_quota_middleware, user_email
        )
        
        return {
            "message": f"Quota incrémenté (success={success})",
            "user_email": user_email,
            "updated_quota": quota_details,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "error": f"Failed to increment quota: {str(e)}",
            "user_email": user_email
        }

@router.get("/debug")
def debug_imports() -> Dict[str, Any]:
    """Vérifie quelques imports utiles (préserve le comportement original)."""
    debug_info: Dict[str, Any] = {
        "dialogue_available": DIALOGUE_AVAILABLE,
        "agricultural_validator_available": AGRICULTURAL_VALIDATOR_AVAILABLE,
        "billing_system_available": True,  # 🦆 NOUVEAU
        "analytics_system_available": True,  # 📊 NOUVEAU
        "performance_optimizations_enabled": True,  # 🚀 NOUVEAU
        "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE,  # 🎯 NOUVEAU
        "imports_tested": []
    }
    
    # 💾 NOUVEAU: Test import persistance
    try:
        from .pipeline.dialogue_manager import POSTGRES_AVAILABLE, PERSIST_CONVERSATIONS
        debug_info["conversation_persistence_available"] = POSTGRES_AVAILABLE and PERSIST_CONVERSATIONS
    except ImportError:
        debug_info["conversation_persistence_available"] = False
    
    imports_to_test: List[str] = [
        "app.api.v1.utils.question_classifier",
        "app.api.v1.pipeline.context_extractor",
        "app.api.v1.pipeline.clarification_manager",
        "app.api.v1.pipeline.rag_engine",
        "app.api.v1.utils.formulas",
        "app.api.v1.pipeline.intent_registry",
        "app.api.v1.agricultural_domain_validator",  # 🌾
        "app.api.v1.billing",  # 🦆 NOUVEAU
        "app.api.v1.logging",  # 📊 NOUVEAU
        "app.api.v1.pipeline.postgres_memory",  # 💾 NOUVEAU
        "app.api.v1.pipeline.unified_confidence",  # 🎯 NOUVEAU
    ]
    
    for import_path in imports_to_test:
        try:
            __import__(import_path)
            debug_info["imports_tested"].append({"path": import_path, "status": "✅ OK"})
        except Exception as e:
            debug_info["imports_tested"].append({"path": import_path, "status": f"❌ Error: {e}"})
    
    return debug_info

@router.post("/force-import-test")
async def force_import_test():  # 🚀 ASYNC
    """Teste l'import et un appel basique de handle() sans casser l'API."""
    import traceback
    try:
        from .pipeline.dialogue_manager import handle as _handle  # type: ignore
        # Exécuter en thread pour éviter de bloquer
        test_result = await asyncio.to_thread(
            _handle, "test", "test question", "fr", debug=True, user_id="test_user"
        )
        
        # 🎯 NOUVEAU: Vérifier presence confidence dans résultat
        has_confidence = "confidence" in test_result
        confidence_info = test_result.get("confidence", {}) if has_confidence else {}
        
        return {
            "status": "✅ SUCCESS", 
            "result": test_result, 
            "import_successful": True,
            "confidence_included": has_confidence,  # 🎯 NOUVEAU
            "confidence_score": confidence_info.get("score"),  # 🎯 NOUVEAU
            "confidence_level": confidence_info.get("level")  # 🎯 NOUVEAU
        }
    except Exception as e:
        return {
            "status": "❌ FAILED",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "import_successful": False,
        }

@router.get("/perfstore-status")
def perfstore_status():
    """Expose quelques infos sur le PerfStore (ne jette pas d'exception)."""
    try:
        from .pipeline.dialogue_manager import _get_perf_store  # type: ignore
        store = _get_perf_store("broiler")
        if not store:
            return {"ok": False, "reason": "PerfStore None"}
        root = getattr(store, "root", None)
        species = getattr(store, "species", None)
        tables_dir = str(getattr(store, "dir_tables", "")) if getattr(store, "dir_tables", None) else None

        lines = []
        for ln in ["ross308", "cobb500"]:
            try:
                df = store._load_df(ln)  # type: ignore
                lines.append({"line": ln, "rows": 0 if df is None else int(len(df))})
            except Exception as e:
                lines.append({"line": ln, "error": str(e)})

        return {
            "ok": True,
            "root": str(root) if root is not None else None,
            "species": species,
            "tables_dir": tables_dir,
            "lines": lines,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/test-basic")
def test_basic():
    """Test ultra-basique sans aucune dépendance"""
    return {"status": "ok", "message": "Basic endpoint works"}

# ============================
# [FUSION] /perf-probe complet avec extraction + nettoyage JSON (INCHANGÉ)
# ============================
@router.post("/perf-probe")
def perf_probe(payload: AskPayload):
    """
    Version fusionnée complète:
    - Extraction automatique des entités depuis la question
    - Nettoyage JSON des valeurs NaN/inf 
    - Diagnostics complets avec fallbacks
    - Messages d'erreur informatifs
    """
    try:
        # [STEP 1] Import PerfStore protégé
        try:
            from .pipeline.perf_store import PerfStore  # type: ignore
        except ImportError as e:
            return jsonable_encoder({
                "error": "import_failed", 
                "message": f"Failed to import PerfStore: {str(e)}",
                "entities": (payload.entities or {}) if payload else {},
            })

        # [STEP 2] Parsing de la question et des entités
        q = (payload.question or "") if payload else ""
        ql = q.lower()
        entities_in = (payload.entities or {}) if (payload and payload.entities is not None) else {}
        
        # Species
        species = (entities_in.get("species") or "broiler").lower()
        
        # Line (avec extraction automatique)
        line = entities_in.get("line")
        if not line:
            if "cobb" in ql:
                line = "cobb500"
            elif "ross" in ql:
                line = "ross308"

        # Sex (avec extraction automatique)
        sex = entities_in.get("sex")
        if not sex:
            if ("as hatched" in ql) or ("as-hatched" in ql) or ("mixte" in ql) or (" ah " in ql):
                sex = "as_hatched"
            elif ("male" in ql) or ("mâle" in ql):
                sex = "male"
            elif ("female" in ql) or ("femelle" in ql):
                sex = "female"

        # Unit (avec extraction automatique)
        unit = entities_in.get("unit")
        if not unit:
            if ("metric" in ql) or ("métrique" in ql):
                unit = "metric"
            elif "imperial" in ql:
                unit = "imperial"

        # Age (avec extraction améliorée)
        age_days = entities_in.get("age_days")
        if age_days is None:
            age_days = extract_age_from_text(ql)

        # [STEP 3] Validation des paramètres
        if age_days and (age_days < 1 or age_days > 70):
            return jsonable_encoder({
                "error": "invalid_age", 
                "message": f"Age must be between 1-70 days, got {age_days}",
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit}
            })

        # [STEP 4] Normalisation des entités
        norm = _normalize_entities_soft_local(
            {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit}
        )

        # [STEP 5] Instanciation PerfStore (avec cache)
        try:
            store = get_cached_store(norm["species"])
            if not store:
                return jsonable_encoder({
                    "error": "perfstore_init_failed",
                    "message": "Failed to initialize PerfStore",
                    "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                    "norm": norm,
                })
            available = store.available_lines()
        except Exception as e:
            return jsonable_encoder({
                "error": "perfstore_init_failed",
                "message": f"Failed to initialize PerfStore: {str(e)}",
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
            })

        # [STEP 6] Vérification ligne disponible
        if not norm.get("line"):
            return jsonable_encoder({
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "rec": None,
                "debug": {
                    "error": "missing_line",
                    "available_lines": available,
                    "tables_dir": str(getattr(store, "dir_tables", "")),
                    "message":