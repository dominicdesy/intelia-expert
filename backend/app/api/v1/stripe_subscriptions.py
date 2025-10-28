"""
Stripe Subscription Management avec Link Payment
Version: 1.4.1
Last modified: 2025-10-26
"""
# app/api/v1/stripe_subscriptions.py
# -*- coding: utf-8 -*-
"""
Stripe Subscription Management avec Link Payment
Support tarification régionale: Essential $0, Pro $18 USD, Elite $28 USD
Version: 1.0
"""

import os
import logging
import stripe
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel, EmailStr

from app.api.v1.auth import get_current_user
from app.utils.i18n import t

# Import country tracking service for fraud detection
try:
    from app.services.country_tracking_service import CountryTrackingService
    COUNTRY_TRACKING_AVAILABLE = True
except ImportError:
    COUNTRY_TRACKING_AVAILABLE = False
    logger.warning("Country tracking service not available")

router = APIRouter(prefix="/stripe", tags=["stripe-subscriptions"])
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION STRIPE ====================

# Charger les clés Stripe depuis l'environnement
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if not STRIPE_SECRET_KEY:
    logger.warning("STRIPE_SECRET_KEY non configurée - mode développement")
else:
    stripe.api_key = STRIPE_SECRET_KEY
    logger.info("Stripe API configurée")

# URLs frontend pour redirections après paiement
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
SUCCESS_URL = f"{FRONTEND_URL}/billing/success"
CANCEL_URL = f"{FRONTEND_URL}/billing/cancel"

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")


# ==================== MODÈLES PYDANTIC ====================

class CreateCheckoutSessionRequest(BaseModel):
    plan_name: str  # "pro" ou "elite" (essential est gratuit)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    locale: Optional[str] = None  # Code langue pour Stripe (ex: "fr", "en", "es")


class CreateCheckoutSessionResponse(BaseModel):
    success: bool
    checkout_url: Optional[str] = None
    session_id: Optional[str] = None
    error: Optional[str] = None


class SubscriptionStatusResponse(BaseModel):
    has_subscription: bool
    plan_name: Optional[str] = None
    status: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    price_monthly: Optional[float] = None
    currency: Optional[str] = None


class CustomerPortalResponse(BaseModel):
    success: bool
    portal_url: Optional[str] = None
    error: Optional[str] = None


# ==================== HELPER FUNCTIONS ====================

def get_db_connection():
    """Créer une connexion à la base de données"""
    return psycopg2.connect(DATABASE_URL)


def get_or_create_stripe_customer(user_email: str, user_name: Optional[str] = None, country_code: str = "US") -> str:
    """
    Récupère ou crée un Stripe Customer pour un utilisateur

    Args:
        user_email: Email de l'utilisateur
        user_name: Nom de l'utilisateur (optionnel)
        country_code: Code pays ISO (US, CA, FR, etc.)

    Returns:
        stripe_customer_id: ID du customer Stripe
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Vérifier si le customer existe déjà
                cur.execute(
                    "SELECT stripe_customer_id FROM stripe_customers WHERE user_email = %s",
                    (user_email,)
                )
                result = cur.fetchone()

                if result:
                    logger.info(f"Customer Stripe existant trouvé pour {user_email}")
                    return result["stripe_customer_id"]

                # Créer un nouveau customer dans Stripe
                logger.info(f"Création nouveau customer Stripe pour {user_email}")
                stripe_customer = stripe.Customer.create(
                    email=user_email,
                    name=user_name,
                    metadata={
                        "user_email": user_email,
                        "source": "intelia_expert",
                        "country_code": country_code
                    }
                )

                # Sauvegarder dans notre base de données
                cur.execute(
                    """
                    INSERT INTO stripe_customers (user_email, stripe_customer_id, customer_name, country_code)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_email) DO UPDATE
                    SET stripe_customer_id = EXCLUDED.stripe_customer_id,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (user_email, stripe_customer.id, user_name, country_code)
                )
                conn.commit()

                logger.info(f"Customer Stripe créé: {stripe_customer.id}")
                return stripe_customer.id

    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe lors de la création du customer: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur Stripe: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur base de données: {e}")
        raise HTTPException(status_code=500, detail="Erreur création customer")


def get_price_by_currency(plan_name: str, currency: str, billing_cycle: str = "month") -> Optional[str]:
    """
    Récupère le Stripe Price ID pour une devise et un cycle de facturation spécifiques.

    Cette fonction recherche dans Stripe les price IDs créés par le script multi-currency.

    Args:
        plan_name: Nom du plan ("pro" ou "elite")
        currency: Code devise ISO ("USD", "EUR", etc.)
        billing_cycle: "month" ou "year"

    Returns:
        Stripe Price ID ou None si pas trouvé
    """
    try:
        # Liste tous les produits pour trouver celui qui correspond au plan
        products = stripe.Product.list(limit=100)
        target_product_id = None

        plan_display_names = {
            "pro": "Pro Plan",
            "elite": "Elite Plan"
        }

        for product in products.auto_paging_iter():
            if product.name == plan_display_names.get(plan_name):
                target_product_id = product.id
                break

        if not target_product_id:
            logger.warning(f"Product not found for plan: {plan_name}")
            return None

        # Rechercher le price correspondant
        prices = stripe.Price.list(
            product=target_product_id,
            currency=currency.lower(),
            active=True,
            limit=100
        )

        for price in prices.data:
            if (price.recurring and
                price.recurring.interval == billing_cycle):
                logger.info(f"Found price for {plan_name}/{currency}/{billing_cycle}: {price.id}")
                return price.id

        logger.warning(f"No price found for {plan_name}/{currency}/{billing_cycle}")
        return None

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error getting price: {e}")
        return None


def get_regional_price(plan_name: str, country_code: str = "US") -> Tuple[float, str, Optional[str], int]:
    """
    Récupère le prix d'un plan selon le pays de l'utilisateur
    Utilise d'abord les prix personnalisés, sinon calcul automatique par tier

    Args:
        plan_name: Nom du plan (essential, pro, elite)
        country_code: Code pays ISO (US, CA, FR, etc.)

    Returns:
        Tuple (price, currency, stripe_price_id, tier_level)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Utiliser la fonction SQL qui gère la priorité: custom > calculated
                cur.execute(
                    "SELECT * FROM get_price_for_country(%s, %s)",
                    (plan_name, country_code)
                )
                result = cur.fetchone()

                if result:
                    # result = (plan_name, tier_level, price_usd, price_local, currency_code, currency_symbol, country_name, stripe_price_id)
                    tier_level = result[1]
                    price_local = float(result[3])
                    currency = result[4]
                    stripe_price_id = result[7]

                    logger.info(f"Prix pour {plan_name} ({country_code}): {price_local} {currency} (Tier {tier_level})")
                    return price_local, currency, stripe_price_id, tier_level

                # Fallback: prix US Tier 4 par défaut
                logger.warning(f"Pas de prix pour {plan_name}/{country_code}, fallback USA Tier 4")
                cur.execute(
                    "SELECT * FROM get_price_for_country(%s, 'US')",
                    (plan_name,)
                )
                result = cur.fetchone()
                if result:
                    return float(result[3]), result[4], result[7], result[1]

                # Dernier fallback: prix hardcodés
                raise Exception("No pricing found in database")

    except Exception as e:
        logger.error(f"Erreur récupération prix: {e}")
        # Fallback hardcodé (Tier 4 USA)
        default_prices = {
            "essential": (0.0, "USD", None, 4),
            "pro": (19.99, "USD", None, 4),
            "elite": (31.99, "USD", None, 4),
        }
        return default_prices.get(plan_name, (0.0, "USD", None, 4))


def save_subscription_to_db(subscription_data: Dict[str, Any], user_email: str) -> None:
    """
    Sauvegarde ou met à jour un abonnement dans la base de données

    Args:
        subscription_data: Données de l'abonnement depuis Stripe
        user_email: Email de l'utilisateur
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Extraire les métadonnées
                metadata = subscription_data.get("metadata", {})
                plan_name = metadata.get("plan_name", "pro")
                tier_level = metadata.get("tier_level")

                cur.execute(
                    """
                    INSERT INTO stripe_subscriptions (
                        user_email, stripe_subscription_id, stripe_customer_id,
                        plan_name, tier_level, price_monthly, currency, status,
                        current_period_start, current_period_end,
                        cancel_at_period_end, stripe_metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (stripe_subscription_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        tier_level = EXCLUDED.tier_level,
                        current_period_start = EXCLUDED.current_period_start,
                        current_period_end = EXCLUDED.current_period_end,
                        cancel_at_period_end = EXCLUDED.cancel_at_period_end,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        user_email,
                        subscription_data["id"],
                        subscription_data["customer"],
                        plan_name,
                        tier_level,
                        metadata.get("price_monthly", 0),
                        subscription_data.get("currency", "usd").upper(),
                        subscription_data["status"],
                        datetime.fromtimestamp(subscription_data["current_period_start"]),
                        datetime.fromtimestamp(subscription_data["current_period_end"]),
                        subscription_data.get("cancel_at_period_end", False),
                        psycopg2.extras.Json(metadata)
                    )
                )
                conn.commit()
                logger.info(f"Abonnement sauvegardé pour {user_email}")

                # Mettre à jour aussi user_billing_info pour compatibilité
                cur.execute(
                    """
                    UPDATE user_billing_info
                    SET plan_name = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_email = %s
                    """,
                    (plan_name, user_email)
                )
                conn.commit()

    except Exception as e:
        logger.error(f"Erreur sauvegarde abonnement: {e}")
        raise


# ==================== ENDPOINTS ====================

@router.post("/create-checkout-session", response_model=CreateCheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    http_request: Request = None
):
    """
    Crée une Stripe Checkout Session pour un upgrade de plan

    Supports:
    - Stripe Link (paiement 1-click)
    - Paiement par carte
    - Tarification régionale automatique
    - Fraud detection avec country tracking
    """
    try:
        user_email = current_user.get("email")
        user_name = current_user.get("full_name") or current_user.get("email", "").split("@")[0]

        # Récupérer le pays de l'utilisateur depuis la BD (signup_country) + fraud analysis
        country_code = "US"  # Default
        pricing_tier = "tier1"  # Default
        fraud_risk_score = 0
        fraud_risk_level = "LOW"

        # Get user's billing currency preference
        user_billing_currency = None
        billing_cycle = "month"  # Default to monthly

        # Extract billing cycle from plan_name (e.g., "pro_yearly" -> "year")
        if "_yearly" in plan_name:
            billing_cycle = "year"
            plan_name = plan_name.replace("_yearly", "")

        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Récupérer signup_country, pricing_tier ET billing_currency
                    cur.execute("""
                        SELECT signup_country, pricing_tier, pricing_locked_at, billing_currency
                        FROM user_billing_info
                        WHERE user_email = %s
                    """, (user_email,))

                    billing_info = cur.fetchone()

                    if billing_info:
                        if billing_info.get('signup_country'):
                            country_code = billing_info['signup_country']
                            pricing_tier = billing_info.get('pricing_tier', 'tier1')
                            logger.info(f"Country from DB: {country_code}, Tier: {pricing_tier}")

                        # Get billing currency
                        user_billing_currency = billing_info.get('billing_currency')
                        if user_billing_currency:
                            logger.info(f"User billing currency: {user_billing_currency}")

                    # Obtenir l'analyse de fraude
                    if COUNTRY_TRACKING_AVAILABLE:
                        try:
                            fraud_analysis = await CountryTrackingService.get_user_fraud_analysis(user_email)
                            fraud_risk_score = fraud_analysis.get('avg_risk_score', 0)
                            fraud_risk_level = fraud_analysis.get('risk_level', 'LOW')
                            logger.info(f"Fraud analysis: score={fraud_risk_score}, level={fraud_risk_level}")
                        except Exception as e:
                            logger.warning(f"Could not get fraud analysis: {e}")

        except Exception as e:
            logger.warning(f"Could not get user country from DB: {e}, using default US")

        plan_name = request.plan_name.lower()

        # Validation: essential est gratuit, pas besoin de checkout
        if plan_name == "essential":
            raise HTTPException(
                status_code=400,
                detail="Le plan Essential est gratuit, pas besoin de paiement"
            )

        if plan_name not in ["pro", "elite"]:
            raise HTTPException(
                status_code=400,
                detail="Plan invalide. Choix: 'pro' ou 'elite'"
            )

        # Récupérer ou créer le customer Stripe
        stripe_customer_id = get_or_create_stripe_customer(user_email, user_name, country_code)

        # Use currency-based pricing if billing_currency is set, otherwise use regional pricing
        stripe_price_id = None
        currency = "USD"
        price = 0.0
        tier_level = 4

        if user_billing_currency:
            # Multi-currency mode: Use currency-specific Stripe Price
            logger.info(f"Using multi-currency pricing: {user_billing_currency}/{billing_cycle}")
            stripe_price_id = get_price_by_currency(plan_name, user_billing_currency, billing_cycle)

            if stripe_price_id:
                currency = user_billing_currency
                # Get price amount from Stripe Price object
                try:
                    price_obj = stripe.Price.retrieve(stripe_price_id)
                    price = price_obj.unit_amount / 100  # Convert cents to dollars
                    logger.info(f"Using Stripe Price: {stripe_price_id} ({price} {currency})")
                except stripe.error.StripeError as e:
                    logger.error(f"Error retrieving Stripe Price: {e}")
                    # Fallback to regional pricing
                    stripe_price_id = None
            else:
                logger.warning(f"No multi-currency price found for {plan_name}/{user_billing_currency}")
                # Fallback to regional pricing below

        if not stripe_price_id:
            # Fallback: Regional pricing (legacy system)
            logger.info(f"Using regional pricing for country: {country_code}")
            price, currency, stripe_price_id, tier_level = get_regional_price(plan_name, country_code)

        logger.info(f"Création checkout session pour {user_email}: {plan_name} @ {price} {currency} (billing_cycle: {billing_cycle})")

        # Récupérer la locale demandée (avant mapping Stripe)
        user_locale = request.locale or "en"

        # Utiliser le système i18n pour les traductions de plans
        plan_name_key = f"stripe.{plan_name}PlanName"
        plan_desc_key = f"stripe.{plan_name}PlanDescription"

        plan_info = {
            "name": t(plan_name_key, user_locale, fallback=f"Plan {plan_name.capitalize()}"),
            "description": t(plan_desc_key, user_locale, fallback=f"Intelia Expert - {plan_name.upper()}")
        }

        # Si stripe_price_id existe dans la DB, l'utiliser (produit Stripe configuré)
        # Sinon, créer un paiement dynamique
        if stripe_price_id:
            # Mode: Prix prédéfini dans Stripe
            line_items = [{
                "price": stripe_price_id,
                "quantity": 1,
            }]
        else:
            # Mode: Prix dynamique (pour développement)
            line_items = [{
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {
                        "name": plan_info["name"],
                        "description": plan_info["description"],
                        "metadata": {
                            "plan_name": plan_name,
                            "source": "intelia_expert"
                        }
                    },
                    "unit_amount": int(price * 100),  # Stripe utilise les centimes
                    "recurring": {
                        "interval": "month"
                    }
                },
                "quantity": 1,
            }]

        # Mapper le code langue de l'app vers les locales Stripe supportées
        # Stripe supporte: auto, da, de, en, es, fi, fr, it, ja, nb, nl, pl, pt, sv, zh
        locale_mapping = {
            "fr": "fr",
            "en": "en",
            "es": "es",
            "de": "de",
            "it": "it",
            "pt": "pt",
            "nl": "nl",
            "pl": "pl",
            "ja": "ja",
            "zh": "zh",
            "da": "da",
            "fi": "fi",
            "nb": "nb",
            "sv": "sv"
        }

        stripe_locale = locale_mapping.get(request.locale, "auto") if request.locale else "auto"
        logger.info(f"Stripe locale utilisée: {stripe_locale} (demandée: {request.locale})")

        # Créer la Checkout Session avec Stripe Link activé
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            line_items=line_items,
            mode="subscription",

            # 🔥 STRIPE LINK ACTIVÉ
            payment_method_types=["card", "link"],

            # Sauvegarder automatiquement les infos de paiement
            payment_method_collection="always",

            # 🌍 LOCALISATION STRIPE
            locale=stripe_locale,

            # URLs de redirection
            success_url=request.success_url or SUCCESS_URL,
            cancel_url=request.cancel_url or CANCEL_URL,

            # Métadonnées pour tracking ET fraud detection
            metadata={
                "user_email": user_email,
                "plan_name": plan_name,
                "price_monthly": str(price),
                "currency": currency,
                "country_code": country_code,
                "tier_level": str(tier_level),
                # Fraud detection metadata
                "signup_country": country_code,
                "pricing_tier": pricing_tier,
                "fraud_risk_score": str(fraud_risk_score),
                "fraud_risk_level": fraud_risk_level,
                "source": "intelia_expert_fraud_protected"
            },

            # Remplir automatiquement l'email
            customer_email=user_email if not stripe_customer_id else None,

            # Configuration additionnelle
            allow_promotion_codes=True,  # Permettre codes promo
            billing_address_collection="auto",
        )

        logger.info(f"Checkout session créée: {checkout_session.id}")

        return CreateCheckoutSessionResponse(
            success=True,
            checkout_url=checkout_session.url,
            session_id=checkout_session.id
        )

    except HTTPException:
        raise
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe: {e}")
        return CreateCheckoutSessionResponse(
            success=False,
            error=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur création checkout: {e}")
        return CreateCheckoutSessionResponse(
            success=False,
            error="Erreur lors de la création de la session de paiement"
        )


@router.get("/subscription-status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Récupère le statut d'abonnement actuel de l'utilisateur
    """
    try:
        user_email = current_user.get("email")

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM get_user_subscription_status(%s)
                    """,
                    (user_email,)
                )
                result = cur.fetchone()

                if not result or not result.get("is_active"):
                    return SubscriptionStatusResponse(
                        has_subscription=False
                    )

                # Récupérer les détails complets de l'abonnement
                cur.execute(
                    """
                    SELECT * FROM stripe_subscriptions
                    WHERE user_email = %s AND status IN ('active', 'trialing')
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (user_email,)
                )
                subscription = cur.fetchone()

                if not subscription:
                    return SubscriptionStatusResponse(has_subscription=False)

                return SubscriptionStatusResponse(
                    has_subscription=True,
                    plan_name=subscription["plan_name"],
                    status=subscription["status"],
                    current_period_end=subscription["current_period_end"].isoformat() if subscription["current_period_end"] else None,
                    cancel_at_period_end=subscription["cancel_at_period_end"],
                    price_monthly=float(subscription["price_monthly"]) if subscription["price_monthly"] else None,
                    currency=subscription["currency"]
                )

    except Exception as e:
        logger.error(f"Erreur récupération statut: {e}")
        return SubscriptionStatusResponse(has_subscription=False)


@router.post("/customer-portal", response_model=CustomerPortalResponse)
async def create_customer_portal_session(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Crée une session Stripe Customer Portal pour gérer l'abonnement
    (annuler, mettre à jour carte, voir factures)
    """
    try:
        user_email = current_user.get("email")

        # Récupérer le Stripe customer ID
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT stripe_customer_id FROM stripe_customers WHERE user_email = %s",
                    (user_email,)
                )
                result = cur.fetchone()

                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Aucun abonnement trouvé. Veuillez d'abord souscrire à un plan."
                    )

                stripe_customer_id = result["stripe_customer_id"]

        # Créer la session du portail client
        portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{FRONTEND_URL}/chat",  # Retour vers l'app après modifications
        )

        logger.info(f"Portail client créé pour {user_email}")

        return CustomerPortalResponse(
            success=True,
            portal_url=portal_session.url
        )

    except HTTPException:
        raise
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe portal: {e}")
        return CustomerPortalResponse(
            success=False,
            error=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur création portal: {e}")
        return CustomerPortalResponse(
            success=False,
            error="Erreur lors de la création du portail client"
        )


# ==================== ENDPOINT WEBHOOK ====================
# (Suite dans le prochain fichier pour la gestion des webhooks)
