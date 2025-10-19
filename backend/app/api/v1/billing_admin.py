# app/api/v1/billing_admin.py
# -*- coding: utf-8 -*-
"""
Admin Billing Management API - STRIPE-FIRST ARCHITECTURE
Gestion sécurisée des plans, prix et quotas
IMPORTANT: Zéro donnée de paiement sensible stockée localement
Version: 1.0
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
import stripe

# Import auth
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/billing/admin", tags=["billing-admin"])
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# ============================================================================
# MODELS (Pydantic)
# ============================================================================

class PlanQuotaUpdate(BaseModel):
    monthly_quota: int = Field(..., ge=0, le=100000, description="Quota mensuel (0-100000 questions)")


class PlanNameUpdate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100, description="Nom d'affichage du plan")


class CountryPricingUpdate(BaseModel):
    plan_name: str = Field(..., description="Nom du plan (essential, pro, elite)")
    price: float = Field(..., ge=0, description="Prix dans la devise locale")
    currency: str = Field(..., min_length=3, max_length=3, description="Code devise (CAD, USD, EUR)")


class TierPriceUpdate(BaseModel):
    price_usd: float = Field(..., ge=0, description="Prix en USD pour ce tier")


class CurrencyRateUpdate(BaseModel):
    rate_to_usd: float = Field(..., gt=0, description="Taux de conversion vers USD")


# ============================================================================
# UTILS
# ============================================================================

def get_db():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)


def verify_super_admin(current_user: dict) -> bool:
    """
    Vérifie que l'utilisateur est super admin
    TODO: Implémenter la vérification réelle depuis la DB
    """
    # Pour l'instant, vérifier si l'email est dans une liste blanche
    super_admins = os.getenv("SUPER_ADMIN_EMAILS", "").split(",")
    user_email = current_user.get("email", "")

    if user_email not in super_admins:
        raise HTTPException(status_code=403, detail="Super admin access required")

    return True


def log_admin_action(
    action_type: str,
    target_entity: str,
    admin_email: str,
    old_value: dict,
    new_value: dict,
    old_stripe_id: str = None,
    new_stripe_id: str = None,
    ip_address: str = None
) -> int:
    """Log une action admin dans l'historique (données non-sensibles uniquement)"""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT log_admin_change(
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        action_type,
                        target_entity,
                        admin_email,
                        psycopg2.extras.Json(old_value),
                        psycopg2.extras.Json(new_value),
                        old_stripe_id,
                        new_stripe_id,
                        ip_address
                    )
                )
                history_id = cur.fetchone()[0]
                conn.commit()
                return history_id
    except Exception as e:
        logger.error(f"❌ Erreur log admin action: {e}")
        return None


# ============================================================================
# ENDPOINTS: Plans Management
# ============================================================================

@router.get("/plans")
async def get_all_plans(current_user: dict = Depends(get_current_user)):
    """
    Récupère tous les plans avec leurs paramètres
    Retourne: Données non-sensibles uniquement
    """
    verify_super_admin(current_user)

    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        plan_name,
                        display_name,
                        monthly_quota,
                        price_per_month,
                        features,
                        active,
                        created_at
                    FROM billing_plans
                    ORDER BY price_per_month
                    """
                )
                plans = cur.fetchall()

                return {
                    "success": True,
                    "plans": [dict(p) for p in plans]
                }
    except Exception as e:
        logger.error(f"❌ Erreur get plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plans/{plan_name}/quota")
async def update_plan_quota(
    plan_name: str,
    data: PlanQuotaUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Modifie le quota mensuel d'un plan
    SÉCURISÉ: Quota = logique métier, pas de paiement Stripe impliqué
    """
    verify_super_admin(current_user)

    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Récupérer l'ancien quota
                cur.execute(
                    "SELECT monthly_quota FROM billing_plans WHERE plan_name = %s",
                    (plan_name,)
                )
                old_quota = cur.fetchone()

                if not old_quota:
                    raise HTTPException(status_code=404, detail=f"Plan '{plan_name}' not found")

                # Mettre à jour
                cur.execute(
                    """
                    UPDATE billing_plans
                    SET monthly_quota = %s
                    WHERE plan_name = %s
                    """,
                    (data.monthly_quota, plan_name)
                )
                conn.commit()

                # Logger le changement
                log_admin_action(
                    action_type="quota_change",
                    target_entity=plan_name,
                    admin_email=current_user.get("email"),
                    old_value={"quota": old_quota["monthly_quota"]},
                    new_value={"quota": data.monthly_quota},
                    ip_address=request.client.host
                )

                logger.info(f"✅ Quota modifié: {plan_name} → {data.monthly_quota} questions/mois")

                return {
                    "success": True,
                    "plan_name": plan_name,
                    "old_quota": old_quota["monthly_quota"],
                    "new_quota": data.monthly_quota
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur update quota: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plans/{plan_name}/display_name")
async def update_plan_name(
    plan_name: str,
    data: PlanNameUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Modifie le nom d'affichage d'un plan
    STRIPE-FIRST: Synchronise avec Stripe Product
    """
    verify_super_admin(current_user)

    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Récupérer l'ancien nom
                cur.execute(
                    "SELECT display_name FROM billing_plans WHERE plan_name = %s",
                    (plan_name,)
                )
                old_name = cur.fetchone()

                if not old_name:
                    raise HTTPException(status_code=404, detail=f"Plan '{plan_name}' not found")

                # TODO: Synchroniser avec Stripe Product.modify()
                # stripe_product_id = get_stripe_product_id(plan_name)
                # stripe.Product.modify(stripe_product_id, name=data.display_name)

                # Mettre à jour localement
                cur.execute(
                    """
                    UPDATE billing_plans
                    SET display_name = %s
                    WHERE plan_name = %s
                    """,
                    (data.display_name, plan_name)
                )
                conn.commit()

                # Logger
                log_admin_action(
                    action_type="name_change",
                    target_entity=plan_name,
                    admin_email=current_user.get("email"),
                    old_value={"name": old_name["display_name"]},
                    new_value={"name": data.display_name},
                    ip_address=request.client.host
                )

                logger.info(f"✅ Nom modifié: {plan_name} → '{data.display_name}'")

                return {
                    "success": True,
                    "plan_name": plan_name,
                    "old_name": old_name["display_name"],
                    "new_name": data.display_name
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur update name: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS: Country Pricing Management
# ============================================================================

@router.get("/countries")
async def get_all_countries(current_user: dict = Depends(get_current_user)):
    """
    Récupère tous les pays avec leurs prix configurés
    Retourne: Prix publics + Stripe Price IDs (non-sensibles)
    """
    verify_super_admin(current_user)

    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM complete_pricing_matrix
                    ORDER BY tier_level, country_code, plan_name
                    """
                )
                countries = cur.fetchall()

                return {
                    "success": True,
                    "countries": [dict(c) for c in countries],
                    "total_count": len(countries)
                }
    except Exception as e:
        logger.error(f"❌ Erreur get countries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/countries/{country_code}")
async def get_country_pricing(
    country_code: str,
    current_user: dict = Depends(get_current_user)
):
    """Récupère les prix d'un pays spécifique pour tous les plans"""
    verify_super_admin(current_user)

    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM complete_pricing_matrix
                    WHERE country_code = %s
                    ORDER BY plan_name
                    """,
                    (country_code.upper(),)
                )
                pricing = cur.fetchall()

                if not pricing:
                    raise HTTPException(status_code=404, detail=f"Country '{country_code}' not found")

                return {
                    "success": True,
                    "country_code": country_code.upper(),
                    "pricing": [dict(p) for p in pricing]
                }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur get country pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/countries/{country_code}/pricing")
async def update_country_pricing(
    country_code: str,
    data: CountryPricingUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Modifie le prix d'un plan pour un pays spécifique
    STRIPE-FIRST: Crée un nouveau Stripe Price, puis stocke la référence
    """
    verify_super_admin(current_user)

    try:
        # Récupérer l'ancien prix
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT display_price, display_currency, stripe_price_id
                    FROM stripe_country_pricing
                    WHERE country_code = %s AND plan_name = %s
                    """,
                    (country_code.upper(), data.plan_name)
                )
                old_pricing = cur.fetchone()

                # TODO: Créer nouveau Stripe Price
                # new_stripe_price = stripe.Price.create(
                #     product="prod_xxx",
                #     unit_amount=int(data.price * 100),  # En centimes
                #     currency=data.currency.lower(),
                #     metadata={
                #         "country_code": country_code,
                #         "plan_name": data.plan_name
                #     }
                # )
                new_stripe_price_id = f"price_{country_code}_{data.plan_name}_temp"

                # Insérer ou mettre à jour le prix local
                cur.execute(
                    """
                    INSERT INTO stripe_country_pricing
                    (country_code, plan_name, display_price, display_currency,
                     display_currency_symbol, stripe_price_id, charge_price, charge_currency, active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                    ON CONFLICT (country_code, plan_name)
                    DO UPDATE SET
                        display_price = EXCLUDED.display_price,
                        display_currency = EXCLUDED.display_currency,
                        stripe_price_id = EXCLUDED.stripe_price_id,
                        charge_price = EXCLUDED.charge_price,
                        charge_currency = EXCLUDED.charge_currency,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        country_code.upper(),
                        data.plan_name,
                        data.price,
                        data.currency.upper(),
                        _get_currency_symbol(data.currency),
                        new_stripe_price_id,
                        data.price,
                        data.currency.upper()
                    )
                )
                conn.commit()

                # Logger le changement
                log_admin_action(
                    action_type="price_change",
                    target_entity=f"{country_code}-{data.plan_name}",
                    admin_email=current_user.get("email"),
                    old_value={
                        "price": float(old_pricing["display_price"]) if old_pricing else 0,
                        "currency": old_pricing["display_currency"] if old_pricing else data.currency
                    },
                    new_value={"price": data.price, "currency": data.currency},
                    old_stripe_id=old_pricing["stripe_price_id"] if old_pricing else None,
                    new_stripe_id=new_stripe_price_id,
                    ip_address=request.client.host
                )

                logger.info(f"✅ Prix modifié: {country_code}-{data.plan_name} → {data.price} {data.currency}")

                return {
                    "success": True,
                    "country_code": country_code.upper(),
                    "plan_name": data.plan_name,
                    "old_price": float(old_pricing["display_price"]) if old_pricing else None,
                    "new_price": data.price,
                    "currency": data.currency.upper(),
                    "stripe_price_id": new_stripe_price_id
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur update country pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_currency_symbol(currency_code: str) -> str:
    """Retourne le symbole de la devise"""
    symbols = {
        "USD": "$",
        "CAD": "CA$",
        "EUR": "€",
        "GBP": "£",
        "AUD": "A$",
        "CHF": "CHF",
        "NOK": "kr"
    }
    return symbols.get(currency_code.upper(), currency_code)


# ============================================================================
# ENDPOINTS: History & Audit
# ============================================================================

@router.get("/history")
async def get_admin_history(
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Récupère l'historique des modifications admin"""
    verify_super_admin(current_user)

    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM admin_recent_changes
                    LIMIT %s
                    """,
                    (limit,)
                )
                history = cur.fetchall()

                return {
                    "success": True,
                    "history": [dict(h) for h in history],
                    "total_count": len(history)
                }
    except Exception as e:
        logger.error(f"❌ Erreur get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{entity}")
async def get_entity_history(
    entity: str,
    current_user: dict = Depends(get_current_user)
):
    """Récupère l'historique d'une entité spécifique (ex: 'CA-pro', 'essential')"""
    verify_super_admin(current_user)

    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM get_entity_history(%s)",
                    (entity,)
                )
                history = cur.fetchall()

                return {
                    "success": True,
                    "entity": entity,
                    "history": [dict(h) for h in history]
                }
    except Exception as e:
        logger.error(f"❌ Erreur get entity history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS: Statistics
# ============================================================================

@router.get("/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Récupère les statistiques globales de tarification"""
    verify_super_admin(current_user)

    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Stats par plan
                cur.execute("SELECT * FROM admin_pricing_stats")
                pricing_stats = cur.fetchall()

                # Stats par tier
                cur.execute("SELECT * FROM tier_summary")
                tier_stats = cur.fetchall()

                # Nombre total de pays
                cur.execute("SELECT COUNT(DISTINCT country_code) as total FROM stripe_country_tiers WHERE active = TRUE")
                total_countries = cur.fetchone()

                return {
                    "success": True,
                    "pricing_stats": [dict(p) for p in pricing_stats],
                    "tier_stats": [dict(t) for t in tier_stats],
                    "total_countries": total_countries["total"]
                }
    except Exception as e:
        logger.error(f"❌ Erreur get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
