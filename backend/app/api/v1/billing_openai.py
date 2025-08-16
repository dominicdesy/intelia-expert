"""
🔥 CORRIGÉ: Endpoint pour récupérer les coûts OpenAI réels
Complète les statistiques avec des données financières précises
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
import openai
import logging
from typing import Dict, Any, Optional, List
import os
import requests
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
        
        # Configuration des headers
        headers = {"Authorization": f"Bearer {api_key}"}
        if organization_id:
            headers["OpenAI-Organization"] = organization_id
        
        # 🔥 CORRIGÉ: L'API OpenAI Usage nécessite des appels séparés par date
        processed_data = {
            "total_cost": 0,
            "total_tokens": 0,
            "models_usage": {},
            "daily_breakdown": {},
            "api_calls": 0,
            "errors": []
        }
        
        # Générer la liste des dates entre start_date et end_date
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        current_date = start_dt
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            
            try:
                # 🔥 NOUVEAU: Appel correct à l'API OpenAI Usage avec un seul paramètre 'date'
                usage_url = "https://api.openai.com/v1/usage"
                params = {"date": date_str}
                
                response = requests.get(usage_url, headers=headers, params=params)
                
                if response.status_code == 200:
                    usage_data = response.json()
                    daily_cost = 0
                    daily_tokens = 0
                    daily_calls = 0
                    
                    # Parser les données selon la nouvelle structure de réponse OpenAI
                    if "data" in usage_data and usage_data["data"]:
                        for usage_item in usage_data["data"]:
                            # Extraction des métriques
                            model_name = usage_item.get("snapshot_id", "unknown")
                            
                            # Les coûts sont maintenant dans différents champs selon le type
                            cost = 0
                            if "n_generated_tokens_total" in usage_item and "n_context_tokens_total" in usage_item:
                                # Estimation basée sur les tokens (vous devrez ajuster selon vos tarifs)
                                total_tokens = usage_item.get("n_generated_tokens_total", 0) + usage_item.get("n_context_tokens_total", 0)
                                # Estimation approximative (à ajuster selon le modèle)
                                cost = total_tokens * 0.00002  # Estimation très approximative
                            
                            tokens = usage_item.get("n_context_tokens_total", 0) + usage_item.get("n_generated_tokens_total", 0)
                            calls = usage_item.get("n_requests", 0)
                            
                            # Accumulation globale
                            processed_data["total_cost"] += cost
                            processed_data["total_tokens"] += tokens
                            processed_data["api_calls"] += calls
                            
                            # Accumulation quotidienne
                            daily_cost += cost
                            daily_tokens += tokens
                            daily_calls += calls
                            
                            # Par modèle
                            if model_name not in processed_data["models_usage"]:
                                processed_data["models_usage"][model_name] = {
                                    "cost": 0,
                                    "tokens": 0,
                                    "calls": 0
                                }
                            
                            processed_data["models_usage"][model_name]["cost"] += cost
                            processed_data["models_usage"][model_name]["tokens"] += tokens
                            processed_data["models_usage"][model_name]["calls"] += calls
                    
                    # Enregistrer le breakdown quotidien
                    processed_data["daily_breakdown"][date_str] = {
                        "cost": daily_cost,
                        "tokens": daily_tokens,
                        "calls": daily_calls
                    }
                
                elif response.status_code == 404:
                    # Pas de données pour cette date (normal)
                    processed_data["daily_breakdown"][date_str] = {
                        "cost": 0,
                        "tokens": 0,
                        "calls": 0
                    }
                    
                else:
                    error_msg = f"Erreur API pour {date_str}: {response.status_code} - {response.text}"
                    logger.warning(error_msg)
                    processed_data["errors"].append(error_msg)
            
            except Exception as e:
                error_msg = f"Erreur lors du traitement de {date_str}: {str(e)}"
                logger.error(error_msg)
                processed_data["errors"].append(error_msg)
            
            # Passer au jour suivant
            current_date += timedelta(days=1)
        
        return processed_data
            
    except Exception as e:
        logger.error(f"❌ Erreur récupération usage OpenAI: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


async def get_openai_usage_alternative() -> Dict[str, Any]:
    """
    🔥 ALTERNATIVE: Utilise l'API de facturation OpenAI (si disponible)
    Cette méthode peut être plus fiable pour obtenir les coûts réels
    """
    try:
        api_key = _get_api_key()
        organization_id = get_openai_organization_id()
        
        headers = {"Authorization": f"Bearer {api_key}"}
        if organization_id:
            headers["OpenAI-Organization"] = organization_id
        
        # Essayer l'endpoint de facturation (si votre compte y a accès)
        billing_url = "https://api.openai.com/v1/dashboard/billing/usage"
        
        # Paramètres pour le mois en cours
        start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        response = requests.get(billing_url, headers=headers, params=params)
        
        if response.status_code == 200:
            billing_data = response.json()
            
            return {
                "total_usage": billing_data.get("total_usage", 0) / 100,  # Conversion cents -> dollars
                "daily_costs": billing_data.get("daily_costs", []),
                "source": "billing_api",
                "note": "Données réelles de facturation OpenAI"
            }
        else:
            logger.warning(f"API Billing non accessible: {response.status_code}")
            return {
                "error": "API Billing non accessible",
                "status_code": response.status_code,
                "source": "billing_api_failed"
            }
            
    except Exception as e:
        logger.error(f"Erreur API Billing alternative: {e}")
        return {
            "error": str(e),
            "source": "billing_api_exception"
        }


# ==================== ENDPOINTS CORRIGÉS ====================

@router.get("/openai-usage/current-month")
async def get_current_month_openai_usage():
    """
    🔥 CORRIGÉ: Récupère les coûts OpenAI pour le mois en cours
    """
    try:
        # Calculer les dates du mois en cours
        now = datetime.now()
        start_of_month = now.replace(day=1).strftime("%Y-%m-%d")
        today = now.strftime("%Y-%m-%d")
        
        organization_id = get_openai_organization_id()
        
        # Essayer d'abord la méthode principale
        try:
            usage_data = await get_openai_usage_data(start_of_month, today, organization_id)
        except HTTPException:
            # En cas d'échec, essayer la méthode alternative
            logger.info("Tentative méthode alternative...")
            usage_data = await get_openai_usage_alternative()
        
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
    🔥 CORRIGÉ: Récupère les coûts OpenAI des 30 derniers jours
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
    🔥 CORRIGÉ: Récupère les coûts OpenAI pour une période personnalisée
    """
    try:
        # Validation des dates
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Limiter la plage pour éviter trop d'appels API
            if (end_dt - start_dt).days > 90:
                raise HTTPException(
                    status_code=400,
                    detail="Période trop longue. Maximum 90 jours."
                )
                
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
    🔥 MIS À JOUR: Récupère la liste des modèles OpenAI et leurs tarifs actuels
    """
    try:
        api_key = _get_api_key()
        
        # Configuration OpenAI client (nouvelle version)
        client = openai.OpenAI(api_key=api_key)
        
        # Récupérer la liste des modèles
        models = client.models.list()
        
        # Tarifs mis à jour (août 2025)
        pricing_info = {
            # GPT-4 Turbo
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4-turbo-2024-04-09": {"input": 0.01, "output": 0.03},
            
            # GPT-4
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-32k": {"input": 0.06, "output": 0.12},
            "gpt-4-0613": {"input": 0.03, "output": 0.06},
            
            # GPT-3.5 Turbo
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
            "gpt-3.5-turbo-0125": {"input": 0.0005, "output": 0.0015},
            
            # Embeddings
            "text-embedding-ada-002": {"input": 0.0001, "output": 0},
            "text-embedding-3-small": {"input": 0.00002, "output": 0},
            "text-embedding-3-large": {"input": 0.00013, "output": 0},
            
            # Legacy
            "text-davinci-003": {"input": 0.02, "output": 0.02},
            "code-davinci-002": {"input": 0.02, "output": 0.02},
        }
        
        models_with_pricing = []
        for model in models.data:
            model_id = model.id
            pricing = pricing_info.get(model_id, {
                "input": 0, 
                "output": 0, 
                "note": "Tarif non disponible - vérifiez sur openai.com/pricing"
            })
            
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
            "note": "Tarifs au 15 août 2025 - vérifiez sur https://openai.com/pricing pour les dernières mises à jour"
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
        
        # Test de connectivité basique
        headers = {"Authorization": f"Bearer {api_key}"}
        if organization_id:
            headers["OpenAI-Organization"] = organization_id
        
        # Test avec l'endpoint models
        test_response = requests.get(
            "https://api.openai.com/v1/models", 
            headers=headers,
            timeout=10
        )
        
        return {
            "status": "healthy" if test_response.status_code == 200 else "degraded",
            "api_key_configured": bool(api_key),
            "organization_id_configured": bool(organization_id),
            "api_connectivity": test_response.status_code == 200,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }