# app/api/v1/stripe_webhooks.py
# -*- coding: utf-8 -*-
"""
Stripe Webhook Handler
Traite les événements de paiement et synchronise avec la base de données
Version: 1.0
"""

import os
import logging
import stripe
import psycopg2
import json
from psycopg2.extras import RealDictCursor
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Header

router = APIRouter(tags=["stripe-webhooks"])
logger = logging.getLogger(__name__)

# Configuration
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    """Créer une connexion à la base de données"""
    return psycopg2.connect(DATABASE_URL)


def log_webhook_event(
    signature: str,
    signature_verified: bool,
    event_id: str,
    event_type: str,
    payload: Dict[str, Any],
    processing_status: str = "pending",
    error: str = None
):
    """
    Log tous les webhooks reçus pour audit et debugging
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO stripe_webhook_logs (
                        signature_header, signature_verified, stripe_event_id,
                        event_type, raw_payload, processing_status, processing_error
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        signature[:500] if signature else None,
                        signature_verified,
                        event_id,
                        event_type,
                        psycopg2.extras.Json(payload),
                        processing_status,
                        error
                    )
                )
                conn.commit()
    except Exception as e:
        logger.error(f"❌ Erreur log webhook: {e}")


def save_payment_event(
    event_id: str,
    event_type: str,
    user_email: str,
    customer_id: str,
    subscription_id: str = None,
    amount: float = 0.0,
    currency: str = "USD",
    status: str = "succeeded",
    payload: Dict[str, Any] = None
):
    """
    Sauvegarde un événement de paiement dans la table d'audit
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO stripe_payment_events (
                        stripe_event_id, event_type, user_email, stripe_customer_id,
                        stripe_subscription_id, amount, currency, status,
                        event_payload, processed, processed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (stripe_event_id) DO NOTHING
                    """,
                    (
                        event_id,
                        event_type,
                        user_email,
                        customer_id,
                        subscription_id,
                        amount,
                        currency.upper(),
                        status,
                        psycopg2.extras.Json(payload or {}),
                        True,
                        datetime.utcnow()
                    )
                )
                conn.commit()
                logger.info(f"✅ Payment event sauvegardé: {event_type} - {event_id}")
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde payment event: {e}")


def get_user_email_from_customer_id(customer_id: str) -> str:
    """
    Récupère l'email utilisateur depuis le Stripe customer ID
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT user_email FROM stripe_customers WHERE stripe_customer_id = %s",
                    (customer_id,)
                )
                result = cur.fetchone()
                return result["user_email"] if result else None
    except Exception as e:
        logger.error(f"❌ Erreur récupération user email: {e}")
        return None


def handle_checkout_completed(session: Dict[str, Any]):
    """
    Traite l'événement checkout.session.completed
    Déclenché quand un paiement est réussi
    """
    try:
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        metadata = session.get("metadata", {})

        user_email = metadata.get("user_email") or get_user_email_from_customer_id(customer_id)

        if not user_email:
            logger.error("❌ Impossible de trouver l'email utilisateur")
            return

        logger.info(f"✅ Checkout complété pour {user_email}")

        # Récupérer les détails de l'abonnement depuis Stripe
        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)

            # Sauvegarder l'abonnement dans la DB
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO stripe_subscriptions (
                            user_email, stripe_subscription_id, stripe_customer_id,
                            plan_name, price_monthly, currency, status,
                            current_period_start, current_period_end,
                            cancel_at_period_end, stripe_metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (stripe_subscription_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (
                            user_email,
                            subscription.id,
                            customer_id,
                            metadata.get("plan_name", "pro"),
                            float(metadata.get("price_monthly", 0)),
                            metadata.get("currency", "USD").upper(),
                            subscription.status,
                            datetime.fromtimestamp(subscription.current_period_start),
                            datetime.fromtimestamp(subscription.current_period_end),
                            subscription.cancel_at_period_end,
                            psycopg2.extras.Json(metadata)
                        )
                    )

                    # Mettre à jour user_billing_info
                    cur.execute(
                        """
                        UPDATE user_billing_info
                        SET plan_name = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_email = %s
                        """,
                        (metadata.get("plan_name", "pro"), user_email)
                    )

                    conn.commit()

            logger.info(f"✅ Abonnement activé pour {user_email}: {metadata.get('plan_name')}")

            # TODO: Envoyer email de confirmation

    except Exception as e:
        logger.error(f"❌ Erreur traitement checkout: {e}")
        raise


def handle_subscription_updated(subscription: Dict[str, Any]):
    """
    Traite customer.subscription.updated
    Déclenché quand l'abonnement est modifié
    """
    try:
        customer_id = subscription.get("customer")
        user_email = get_user_email_from_customer_id(customer_id)

        if not user_email:
            logger.error("❌ Impossible de trouver l'email utilisateur")
            return

        logger.info(f"Mise à jour abonnement pour {user_email}")

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE stripe_subscriptions
                    SET status = %s,
                        current_period_start = %s,
                        current_period_end = %s,
                        cancel_at_period_end = %s,
                        canceled_at = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE stripe_subscription_id = %s
                    """,
                    (
                        subscription["status"],
                        datetime.fromtimestamp(subscription["current_period_start"]),
                        datetime.fromtimestamp(subscription["current_period_end"]),
                        subscription.get("cancel_at_period_end", False),
                        datetime.fromtimestamp(subscription["canceled_at"]) if subscription.get("canceled_at") else None,
                        subscription["id"]
                    )
                )
                conn.commit()

        logger.info(f"✅ Abonnement mis à jour: {subscription['status']}")

    except Exception as e:
        logger.error(f"❌ Erreur mise à jour subscription: {e}")
        raise


def handle_subscription_deleted(subscription: Dict[str, Any]):
    """
    Traite customer.subscription.deleted
    Déclenché quand l'abonnement est annulé
    """
    try:
        customer_id = subscription.get("customer")
        user_email = get_user_email_from_customer_id(customer_id)

        if not user_email:
            logger.error("❌ Impossible de trouver l'email utilisateur")
            return

        logger.info(f"Annulation abonnement pour {user_email}")

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Marquer l'abonnement comme annulé
                cur.execute(
                    """
                    UPDATE stripe_subscriptions
                    SET status = 'canceled',
                        ended_at = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE stripe_subscription_id = %s
                    """,
                    (
                        datetime.utcnow(),
                        subscription["id"]
                    )
                )

                # Downgrade vers plan gratuit
                cur.execute(
                    """
                    UPDATE user_billing_info
                    SET plan_name = 'essential', updated_at = CURRENT_TIMESTAMP
                    WHERE user_email = %s
                    """,
                    (user_email,)
                )

                conn.commit()

        logger.info(f"✅ Utilisateur {user_email} downgrade vers Essential")

        # TODO: Envoyer email de confirmation d'annulation

    except Exception as e:
        logger.error(f"❌ Erreur annulation subscription: {e}")
        raise


def handle_invoice_payment_succeeded(invoice: Dict[str, Any]):
    """
    Traite invoice.payment_succeeded
    Déclenché à chaque paiement mensuel réussi
    """
    try:
        customer_id = invoice.get("customer")
        user_email = get_user_email_from_customer_id(customer_id)

        if not user_email:
            logger.error("❌ Impossible de trouver l'email utilisateur")
            return

        amount = invoice.get("amount_paid", 0) / 100  # Stripe utilise les centimes
        currency = invoice.get("currency", "usd").upper()

        logger.info(f"💰 Paiement réussi pour {user_email}: {amount} {currency}")

        # TODO: Envoyer facture par email
        # TODO: Mettre à jour compteurs de facturation

    except Exception as e:
        logger.error(f"❌ Erreur traitement invoice: {e}")


def handle_invoice_payment_failed(invoice: Dict[str, Any]):
    """
    Traite invoice.payment_failed
    Déclenché quand un paiement échoue
    """
    try:
        customer_id = invoice.get("customer")
        user_email = get_user_email_from_customer_id(customer_id)

        if not user_email:
            logger.error("❌ Impossible de trouver l'email utilisateur")
            return

        logger.warning(f"⚠️ Échec paiement pour {user_email}")

        # TODO: Envoyer email d'alerte
        # TODO: Suspendre l'abonnement si plusieurs échecs

    except Exception as e:
        logger.error(f"❌ Erreur traitement invoice failed: {e}")


# ==================== ENDPOINT WEBHOOK ====================

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature")
):
    """
    Endpoint principal pour recevoir les webhooks Stripe

    Événements supportés:
    - checkout.session.completed: Paiement initial réussi
    - customer.subscription.created: Abonnement créé
    - customer.subscription.updated: Abonnement modifié
    - customer.subscription.deleted: Abonnement annulé
    - invoice.payment_succeeded: Paiement mensuel réussi
    - invoice.payment_failed: Échec de paiement
    """
    logger.info("📥 Webhook Stripe reçu")

    # Récupérer le body brut
    payload = await request.body()
    payload_str = payload.decode("utf-8")

    # Vérifier la signature
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload_str, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
            logger.info("✅ Signature webhook vérifiée")
            signature_verified = True
        else:
            # Mode développement sans vérification
            logger.warning("⚠️ Webhook signature non vérifiée (STRIPE_WEBHOOK_SECRET manquant)")
            event = json.loads(payload_str)
            signature_verified = False

    except stripe.error.SignatureVerificationError as e:
        logger.error(f"❌ Signature invalide: {e}")
        log_webhook_event(stripe_signature, False, None, None, {}, "failed", str(e))
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"❌ Erreur parsing webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Extraire les données
    event_id = event.get("id")
    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})

    logger.info(f"📋 Event: {event_type} (ID: {event_id})")

    # Log du webhook
    log_webhook_event(
        stripe_signature,
        signature_verified,
        event_id,
        event_type,
        event,
        "processing"
    )

    # Router vers le bon handler
    try:
        if event_type == "checkout.session.completed":
            handle_checkout_completed(event_data)

        elif event_type == "customer.subscription.created":
            logger.info("✅ Abonnement créé (déjà géré dans checkout.completed)")

        elif event_type == "customer.subscription.updated":
            handle_subscription_updated(event_data)

        elif event_type == "customer.subscription.deleted":
            handle_subscription_deleted(event_data)

        elif event_type == "invoice.payment_succeeded":
            handle_invoice_payment_succeeded(event_data)

        elif event_type == "invoice.payment_failed":
            handle_invoice_payment_failed(event_data)

        else:
            logger.info(f"ℹ️ Event non géré: {event_type}")

        # Sauvegarder l'événement de paiement
        customer_id = event_data.get("customer")
        if customer_id:
            user_email = get_user_email_from_customer_id(customer_id)
            if user_email:
                save_payment_event(
                    event_id,
                    event_type,
                    user_email,
                    customer_id,
                    event_data.get("id"),
                    event_data.get("amount_paid", 0) / 100 if "amount_paid" in event_data else 0,
                    event_data.get("currency", "usd"),
                    event_data.get("status", "unknown"),
                    event
                )

        # Mettre à jour le log comme traité avec succès
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE stripe_webhook_logs
                    SET processing_status = 'success', processed_at = CURRENT_TIMESTAMP
                    WHERE stripe_event_id = %s
                    """,
                    (event_id,)
                )
                conn.commit()

        logger.info(f"✅ Webhook traité avec succès: {event_type}")

        return {"status": "success", "event_type": event_type}

    except Exception as e:
        logger.error(f"❌ Erreur traitement webhook: {e}")

        # Marquer comme failed dans les logs
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE stripe_webhook_logs
                    SET processing_status = 'failed',
                        processing_error = %s,
                        processed_at = CURRENT_TIMESTAMP
                    WHERE stripe_event_id = %s
                    """,
                    (str(e), event_id)
                )
                conn.commit()

        # Ne pas faire échouer le webhook (Stripe va retry)
        return {"status": "error", "message": str(e)}


@router.get("/webhook/test")
async def test_webhook_endpoint():
    """
    Endpoint de test pour vérifier que le webhook est accessible
    """
    return {
        "status": "ok",
        "message": "Stripe webhook endpoint is ready",
        "signature_verification": "enabled" if STRIPE_WEBHOOK_SECRET else "disabled",
        "timestamp": datetime.utcnow().isoformat()
    }
