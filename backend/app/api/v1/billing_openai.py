"""
🔥 NOUVEAU: Endpoint pour récupérer les coûts OpenAI réels
Complète les statistiques avec des données financières précises
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
import openai
import logging
from typing import Dict, Any, Optional
import os
from app.api.v1.utils.openai_utils import _get_api_key

router = APIRouter()
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION OPENAI BILLING ====================

def get_openai_organization_id() -> Optional[str]:
    """Récupère l'ID d'organisation OpenAI depuis les variables d'environnement"""
    return os.getenv("OPENAI_ORG_ID")

async def get_openai_usage_data(
    start_date: str, 
    end_date: str, 
    organization_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Récupère les données d'utilisation OpenAI via leur API
    
    Args:
        start_date: Format YYYY-MM-DD
        end_date: Format YYYY-MM-DD
        organization_id: ID d'organisation OpenAI (optionnel)
    
    Returns:
        Dict contenant les métriques d'utilisation et coûts
    """
    try:
        api_key = _get_api_key()
        openai.api_key = api_key
        
        # Configuration de l'organisation si disponible
        headers = {"Authorization": f"Bearer {api_key}"}
        if organization_id:
            headers["OpenAI-Organization"] = organization_id
        
        # 🔥 NOUVEAU: Appel à l'API OpenAI Usage
        # Note: OpenAI a récemment changé cette API, adaptez selon la version
        import requests
        
        # Endpoint pour récupérer l'utilisation
        usage_url = "https://api.openai.com/v1/usage"
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        response = requests.get(usage_url, headers=headers, params=params)
        
        if response.status_code == 200:
            usage_data = response.json()
            
            # Traitement des données
            processed_data = {
                "total_cost": 0,
                "total_tokens": 0,
                "models_usage": {},
                "daily_breakdown": {},
                "api_calls": 0
            }
            
            # Parser les données selon la structure de réponse OpenAI
            if "data" in usage_data:
                for daily_usage in usage_data["data"]:
                    date = daily_usage.get("aggregation_timestamp", "unknown")
                    
                    # Accumulation des coûts
                    for usage_item in daily_usage.get("line_items", []):
                        model_name = usage_item.get("name", "unknown")
                        cost = usage_item.get("cost", 0) / 100  # OpenAI retourne en cents
                        tokens = usage_item.get("n_context_tokens_total", 0) + usage_item.get("n_generated_tokens_total", 0)
                        
                        processed_data["total_cost"] += cost
                        processed_data["total_tokens"] += tokens
                        
                        # Par modèle
                        if model_name not in processed_data["models_usage"]:
                            processed_data["models_usage"][model_name] = {
                                "cost": 0,
                                "tokens": 0,
                                "calls": 0
                            }
                        
                        processed_data["models_usage"][model_name]["cost"] += cost
                        processed_data["models_usage"][model_name]["tokens"] += tokens
                        processed_data["models_usage"][model_name]["calls"] += usage_item.get("n_requests", 0)
                        
                        # Par jour
                        if date not in processed_data["daily_breakdown"]:
                            processed_data["daily_breakdown"][date] = 0
                        processed_data["daily_breakdown"][date] += cost
                        
                        processed_data["api_calls"] += usage_item.get("n_requests", 0)
            
            return processed_data
            
        else:
            logger.error(f"❌ Erreur API OpenAI Usage: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=500, 
                detail=f"Erreur lors de la récupération des données OpenAI: {response.status_code}"
            )
            
    except Exception as e:
        logger.error(f"❌ Erreur récupération usage OpenAI: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


# ==================== ENDPOINTS ====================

@router.get("/openai-usage/current-month")
async def get_current_month_openai_usage():
    """
    🔥 NOUVEAU: Récupère les coûts OpenAI pour le mois en cours
    """
    try:
        # Calculer les dates du mois en cours
        now = datetime.now()
        start_of_month = now.replace(day=1).strftime("%Y-%m-%d")
        today = now.strftime("%Y-%m-%d")
        
        organization_id = get_openai_organization_id()
        usage_data = await get_openai_usage_data(start_of_month, today, organization_id)
        
        return {
            "status": "success",
            "period": {
                "start": start_of_month,
                "end": today,
                "type": "current_month"
            },
            "organization_id": organization_id,
            **usage_data
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur endpoint current-month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openai-usage/last-30-days")
async def get_last_30_days_openai_usage():
    """
    🔥 NOUVEAU: Récupère les coûts OpenAI des 30 derniers jours
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        organization_id = get_openai_organization_id()
        usage_data = await get_openai_usage_data(start_str, end_str, organization_id)
        
        return {
            "status": "success",
            "period": {
                "start": start_str,
                "end": end_str,
                "type": "last_30_days"
            },
            "organization_id": organization_id,
            **usage_data
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur endpoint last-30-days: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openai-usage/custom")
async def get_custom_period_openai_usage(
    start_date: str,
    end_date: str,
    organization_id: Optional[str] = None
):
    """
    🔥 NOUVEAU: Récupère les coûts OpenAI pour une période personnalisée
    
    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        organization_id: ID d'organisation OpenAI (optionnel)
    """
    try:
        # Validation des dates
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Format de date invalide. Utilisez YYYY-MM-DD"
            )
        
        org_id = organization_id or get_openai_organization_id()
        usage_data = await get_openai_usage_data(start_date, end_date, org_id)
        
        return {
            "status": "success",
            "period": {
                "start": start_date,
                "end": end_date,
                "type": "custom"
            },
            "organization_id": org_id,
            **usage_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur endpoint custom: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openai-models-pricing")
async def get_openai_models_pricing():
    """
    🔥 NOUVEAU: Récupère la liste des modèles OpenAI et leurs tarifs
    Utile pour calculer des estimations de coûts
    """
    try:
        api_key = _get_api_key()
        openai.api_key = api_key
        
        # Récupérer la liste des modèles
        models = openai.Model.list()
        
        # Tarifs approximatifs (à mettre à jour selon OpenAI)
        pricing_info = {
            "gpt-4": {"input": 0.03, "output": 0.06},  # par 1K tokens
            "gpt-4-32k": {"input": 0.06, "output": 0.12},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
            "text-embedding-ada-002": {"input": 0.0001, "output": 0},
            "text-davinci-003": {"input": 0.02, "output": 0.02},
        }
        
        models_with_pricing = []
        for model in models.data:
            model_id = model.id
            pricing = pricing_info.get(model_id, {"input": 0, "output": 0, "note": "Tarif non disponible"})
            
            models_with_pricing.append({
                "id": model_id,
                "created": model.created,
                "owned_by": model.owned_by,
                "pricing_per_1k_tokens": pricing
            })
        
        return {
            "status": "success",
            "models": models_with_pricing,
            "last_updated": datetime.now().isoformat(),
            "note": "Tarifs approximatifs - vérifiez sur https://openai.com/pricing"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération modèles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Test de connectivité avec l'API OpenAI"""
    try:
        api_key = _get_api_key()
        organization_id = get_openai_organization_id()
        
        return {
            "status": "healthy",
            "api_key_configured": bool(api_key),
            "organization_id_configured": bool(organization_id),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }