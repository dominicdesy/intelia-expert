"""
🔥 SOLUTION FINALE: Rate limiting + Cache + Fallback
Corrige définitivement les timeouts et rate limiting OpenAI
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional
import os
import requests
import asyncio
from app.api.v1.utils.openai_utils import _get_api_key

router = APIRouter()
logger = logging.getLogger(__name__)

# ==================== CACHE GLOBAL ====================
USAGE_CACHE = {}
CACHE_EXPIRY = {}
CACHE_DURATION = 3600  # 1 heure en secondes


def is_cache_valid(date_str: str) -> bool:
    """Vérifie si le cache est encore valide pour une date"""
    if date_str not in CACHE_EXPIRY:
        return False
    return datetime.now().timestamp() < CACHE_EXPIRY[date_str]


def get_cached_usage(date_str: str) -> Optional[Dict]:
    """Récupère les données depuis le cache si valides"""
    if date_str in USAGE_CACHE and is_cache_valid(date_str):
        logger.info(f"📦 Cache HIT pour {date_str}")
        return USAGE_CACHE[date_str]
    return None


def set_cache_usage(date_str: str, data: Dict):
    """Met en cache les données d'utilisation"""
    USAGE_CACHE[date_str] = data
    CACHE_EXPIRY[date_str] = datetime.now().timestamp() + CACHE_DURATION
    logger.info(f"💾 Cache SET pour {date_str}")


# ==================== RATE LIMITING SAFE ====================


async def get_openai_usage_data_safe(
    start_date: str,
    end_date: str,
    organization_id: Optional[str] = None,
    max_days: int = 7,  # 🚀 LIMITE par défaut à 7 jours
) -> Dict[str, Any]:
    """
    🚀 VERSION RATE-LIMITED SAFE
    Récupère les données OpenAI avec protection rate limiting
    """
    try:
        api_key = _get_api_key()

        headers = {"Authorization": f"Bearer {api_key}"}
        if organization_id:
            headers["OpenAI-Organization"] = organization_id

        # Initialisation des données
        processed_data = {
            "total_cost": 0,
            "total_tokens": 0,
            "models_usage": {},
            "daily_breakdown": {},
            "api_calls": 0,
            "errors": [],
            "cached_days": 0,
            "api_calls_made": 0,
        }

        # Génération de la plage de dates LIMITÉE
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # 🚨 PROTECTION: Limiter le nombre de jours
        days_diff = (end_dt - start_dt).days + 1
        if days_diff > max_days:
            logger.warning(
                f"⚠️ Plage trop longue ({days_diff} jours), limitation à {max_days} jours"
            )
            start_dt = end_dt - timedelta(days=max_days - 1)

        current_date = start_dt
        request_count = 0

        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")

            # 📦 VÉRIFIER LE CACHE D'ABORD
            cached_data = get_cached_usage(date_str)
            if cached_data:
                processed_data["cached_days"] += 1
                # Ajouter les données cachées
                processed_data["total_cost"] += cached_data.get("cost", 0)
                processed_data["total_tokens"] += cached_data.get("tokens", 0)
                processed_data["api_calls"] += cached_data.get("calls", 0)
                processed_data["daily_breakdown"][date_str] = cached_data

                current_date += timedelta(days=1)
                continue

            # 🚀 RATE LIMITING: Attendre entre les requêtes
            if request_count > 0:
                logger.info("⏳ Rate limiting: attente 12 secondes...")
                await asyncio.sleep(12)  # 12 secondes = 5 req/min max

            try:
                usage_url = "https://api.openai.com/v1/usage"
                params = {"date": date_str}

                logger.info(f"🌐 API Call {request_count + 1} pour {date_str}")
                response = requests.get(
                    usage_url, headers=headers, params=params, timeout=10
                )
                request_count += 1
                processed_data["api_calls_made"] += 1

                daily_data = {"cost": 0, "tokens": 0, "calls": 0}

                if response.status_code == 200:
                    usage_data = response.json()

                    if "data" in usage_data and usage_data["data"]:
                        for usage_item in usage_data["data"]:
                            model_name = usage_item.get("snapshot_id", "unknown")

                            # Estimation des coûts (à ajuster selon vos modèles)
                            tokens = usage_item.get(
                                "n_context_tokens_total", 0
                            ) + usage_item.get("n_generated_tokens_total", 0)
                            calls = usage_item.get("n_requests", 0)

                            # Estimation du coût selon le modèle
                            cost = estimate_cost_by_model(model_name, tokens)

                            daily_data["cost"] += cost
                            daily_data["tokens"] += tokens
                            daily_data["calls"] += calls

                            # Accumulation par modèle
                            if model_name not in processed_data["models_usage"]:
                                processed_data["models_usage"][model_name] = {
                                    "cost": 0,
                                    "tokens": 0,
                                    "calls": 0,
                                }

                            processed_data["models_usage"][model_name]["cost"] += cost
                            processed_data["models_usage"][model_name][
                                "tokens"
                            ] += tokens
                            processed_data["models_usage"][model_name]["calls"] += calls

                elif response.status_code == 404:
                    logger.info(f"📭 Pas de données pour {date_str}")
                    daily_data = {"cost": 0, "tokens": 0, "calls": 0}

                elif response.status_code == 429:
                    error_msg = f"🚨 Rate limit atteint pour {date_str}, arrêt de la récupération"
                    logger.error(error_msg)
                    processed_data["errors"].append(error_msg)
                    break  # Arrêter la boucle en cas de rate limit

                else:
                    error_msg = f"❌ Erreur API {response.status_code} pour {date_str}"
                    logger.warning(error_msg)
                    processed_data["errors"].append(error_msg)
                    daily_data = {"cost": 0, "tokens": 0, "calls": 0}

                # Mise en cache des données récupérées
                set_cache_usage(date_str, daily_data)

                # Accumulation des totaux
                processed_data["total_cost"] += daily_data["cost"]
                processed_data["total_tokens"] += daily_data["tokens"]
                processed_data["api_calls"] += daily_data["calls"]
                processed_data["daily_breakdown"][date_str] = daily_data

            except requests.exceptions.Timeout:
                error_msg = f"⏰ Timeout pour {date_str}"
                logger.error(error_msg)
                processed_data["errors"].append(error_msg)
                processed_data["daily_breakdown"][date_str] = {
                    "cost": 0,
                    "tokens": 0,
                    "calls": 0,
                }

            except Exception as e:
                error_msg = f"❌ Erreur pour {date_str}: {str(e)}"
                logger.error(error_msg)
                processed_data["errors"].append(error_msg)
                processed_data["daily_breakdown"][date_str] = {
                    "cost": 0,
                    "tokens": 0,
                    "calls": 0,
                }

            current_date += timedelta(days=1)

        logger.info(
            f"✅ Récupération terminée: {processed_data['api_calls_made']} appels API, {processed_data['cached_days']} jours en cache"
        )
        return processed_data

    except Exception as e:
        logger.error(f"❌ Erreur générale récupération usage OpenAI: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


def estimate_cost_by_model(model_name: str, tokens: int) -> float:
    """
    Estime le coût basé sur le modèle et le nombre de tokens
    """
    # Tarifs approximatifs par 1K tokens (input + output moyenné)
    pricing = {
        "gpt-4": 0.045,  # Moyenne entre input/output
        "gpt-4-turbo": 0.02,
        "gpt-3.5-turbo": 0.001,
        "text-embedding-ada-002": 0.0001,
        "text-embedding-3-small": 0.00002,
        "text-embedding-3-large": 0.00013,
    }

    # Estimation basée sur le nom du modèle
    rate = 0.01  # Tarif par défaut
    for model_key, model_rate in pricing.items():
        if model_key in model_name.lower():
            rate = model_rate
            break

    return (tokens / 1000) * rate


# ==================== ENDPOINTS OPTIMISÉS ====================


@router.get("/openai-usage/last-week")
async def get_last_week_openai_usage():
    """
    🚀 NOUVEAU: Récupère les coûts des 7 derniers jours (RAPIDE)
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        organization_id = get_openai_organization_id()
        usage_data = await get_openai_usage_data_safe(
            start_str, end_str, organization_id, max_days=7
        )

        return {
            "status": "success",
            "period": {"start": start_str, "end": end_str, "type": "last_week"},
            "organization_id": organization_id,
            **usage_data,
        }

    except Exception as e:
        logger.error(f"❌ Erreur endpoint last-week: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openai-usage/current-month-light")
async def get_current_month_openai_usage_light():
    """
    🚀 VERSION LÉGÈRE: Seulement les 10 derniers jours du mois
    """
    try:
        now = datetime.now()
        # Prendre seulement les 10 derniers jours pour éviter rate limiting
        start_date = max(
            now.replace(day=1),  # Début du mois
            now - timedelta(days=10),  # Ou 10 jours max
        )

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = now.strftime("%Y-%m-%d")

        organization_id = get_openai_organization_id()
        usage_data = await get_openai_usage_data_safe(
            start_str, end_str, organization_id, max_days=10
        )

        return {
            "status": "success",
            "period": {
                "start": start_str,
                "end": end_str,
                "type": "current_month_light",
                "note": "Limité aux 10 derniers jours pour éviter rate limiting",
            },
            "organization_id": organization_id,
            **usage_data,
        }

    except Exception as e:
        logger.error(f"❌ Erreur endpoint current-month-light: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openai-usage/fallback")
async def get_openai_usage_fallback():
    """
    🚀 FALLBACK: Retourne des données simulées en cas de problème API
    """
    try:
        # Simuler des données basées sur votre usage typique
        fallback_data = {
            "total_cost": 6.30,  # Votre dernière valeur connue
            "total_tokens": 450000,
            "models_usage": {
                "gpt-4": {"cost": 4.20, "tokens": 140000, "calls": 85},
                "gpt-3.5-turbo": {"cost": 1.80, "tokens": 240000, "calls": 120},
                "text-embedding-ada-002": {"cost": 0.30, "tokens": 70000, "calls": 35},
            },
            "daily_breakdown": {
                (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"): {
                    "cost": 0.35 + (i * 0.1),
                    "tokens": 20000 + (i * 2000),
                    "calls": 10 + i,
                }
                for i in range(7)
            },
            "api_calls": 250,
            "source": "fallback",
            "note": "Données simulées - API OpenAI non disponible",
        }

        return {
            "status": "success",
            "period": {
                "start": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d"),
                "type": "fallback",
            },
            **fallback_data,
        }

    except Exception as e:
        logger.error(f"❌ Erreur fallback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/openai-usage/clear-cache")
async def clear_openai_cache():
    """🗑️ Vide le cache OpenAI (utile pour les tests)"""
    global USAGE_CACHE, CACHE_EXPIRY

    cache_size = len(USAGE_CACHE)
    USAGE_CACHE.clear()
    CACHE_EXPIRY.clear()

    return {
        "status": "success",
        "message": f"Cache vidé ({cache_size} entrées supprimées)",
        "timestamp": datetime.now().isoformat(),
    }


def get_openai_organization_id() -> Optional[str]:
    """Récupère l'ID d'organisation OpenAI depuis les variables d'environnement"""
    return os.getenv("OPENAI_ORG_ID")


@router.get("/health")
async def health_check():
    """Test de connectivité avec informations de cache"""
    try:
        api_key = _get_api_key()
        organization_id = get_openai_organization_id()

        return {
            "status": "healthy",
            "api_key_configured": bool(api_key),
            "organization_id_configured": bool(organization_id),
            "cache_entries": len(USAGE_CACHE),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
