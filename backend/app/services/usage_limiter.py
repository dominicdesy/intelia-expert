# -*- coding: utf-8 -*-
"""
usage_limiter.py - Service de limitation d'usage pour les plans
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
usage_limiter.py - Service de limitation d'usage pour les plans

Gère les quotas mensuels de questions pour le plan Essential:
- Vérifie si l'utilisateur a atteint sa limite mensuelle
- Incrémente le compteur de questions
- Reset automatique le 1er de chaque mois
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from app.core.database import get_pg_connection
from app.core.stripe_mode import is_quota_enforcement_enabled, get_stripe_config
from app.utils.gdpr_helpers import mask_email
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class QuotaExceededException(Exception):
    """Exception levée quand l'utilisateur a dépassé son quota mensuel"""
    def __init__(self, message: str, usage_info: Dict[str, Any]):
        super().__init__(message)
        self.usage_info = usage_info


def get_current_month_year() -> str:
    """Retourne le mois/année actuel au format YYYY-MM"""
    return datetime.utcnow().strftime("%Y-%m")


def get_user_plan_and_quota(user_email: str) -> Tuple[str, int, bool]:
    """
    Récupère le plan de l'utilisateur et son quota mensuel.

    Returns:
        Tuple[plan_name, monthly_quota, quota_enforcement]
    """
    with get_pg_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Vérifier d'abord dans stripe_subscriptions (source de vérité)
            cur.execute(
                """
                SELECT
                    ss.plan_name,
                    bp.monthly_quota,
                    ubi.quota_enforcement
                FROM stripe_subscriptions ss
                JOIN billing_plans bp ON ss.plan_name = bp.plan_name
                LEFT JOIN user_billing_info ubi ON ss.user_email = ubi.user_email
                WHERE ss.user_email = %s
                  AND ss.status IN ('active', 'trialing')
                ORDER BY ss.created_at DESC
                LIMIT 1
                """,
                (user_email,)
            )

            result = cur.fetchone()

            if result:
                return (
                    result['plan_name'],
                    result['monthly_quota'] or 0,
                    result['quota_enforcement'] if result['quota_enforcement'] is not None else True
                )

            # Fallback: vérifier user_billing_info
            cur.execute(
                """
                SELECT
                    ubi.plan_name,
                    COALESCE(ubi.custom_monthly_quota, bp.monthly_quota, 0) as monthly_quota,
                    ubi.quota_enforcement
                FROM user_billing_info ubi
                LEFT JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
                WHERE ubi.user_email = %s
                """,
                (user_email,)
            )

            result = cur.fetchone()

            if result:
                return (
                    result['plan_name'],
                    result['monthly_quota'],
                    result['quota_enforcement'] if result['quota_enforcement'] is not None else True
                )

            # Par défaut: plan gratuit avec quota limité
            logger.warning(f"Aucun plan trouvé pour {mask_email(user_email)}, utilisation du plan par défaut")
            return ('essential', 3, True)  # TEMPORAIRE: 3 pour tests (normalement 50)


def get_or_create_monthly_usage(user_email: str, month_year: str, monthly_quota: int) -> Dict[str, Any]:
    """
    Récupère ou crée l'enregistrement d'usage mensuel pour l'utilisateur.

    Returns:
        Dict contenant: questions_used, monthly_quota, current_status
    """
    with get_pg_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Vérifier si l'enregistrement existe
            cur.execute(
                """
                SELECT
                    id,
                    questions_used,
                    questions_successful,
                    questions_failed,
                    monthly_quota,
                    quota_exceeded_at,
                    current_status,
                    warning_sent,
                    limit_notifications_sent
                FROM monthly_usage_tracking
                WHERE user_email = %s AND month_year = %s
                """,
                (user_email, month_year)
            )

            result = cur.fetchone()

            if result:
                return dict(result)

            # Créer un nouvel enregistrement pour ce mois
            cur.execute(
                """
                INSERT INTO monthly_usage_tracking (
                    user_email,
                    month_year,
                    questions_used,
                    questions_successful,
                    questions_failed,
                    total_cost_usd,
                    openai_cost_usd,
                    monthly_quota,
                    current_status,
                    warning_sent,
                    limit_notifications_sent,
                    first_question_at,
                    last_updated
                )
                VALUES (%s, %s, 0, 0, 0, 0.00, 0.00, %s, 'active', FALSE, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING
                    id,
                    questions_used,
                    questions_successful,
                    questions_failed,
                    monthly_quota,
                    quota_exceeded_at,
                    current_status,
                    warning_sent,
                    limit_notifications_sent
                """,
                (user_email, month_year, monthly_quota)
            )

            result = cur.fetchone()
            logger.info(f"Créé nouvel enregistrement monthly_usage_tracking pour {mask_email(user_email)} - {month_year}")

            return dict(result)


def check_user_quota(user_email: str) -> Dict[str, Any]:
    """
    Vérifie si l'utilisateur peut poser une question (n'a pas dépassé son quota).

    Returns:
        Dict avec: can_ask, questions_used, monthly_quota, questions_remaining, plan_name

    Raises:
        QuotaExceededException: Si l'utilisateur a dépassé son quota mensuel
    """
    try:
        # Vérifier le mode Stripe global
        if not is_quota_enforcement_enabled():
            stripe_config = get_stripe_config()
            logger.info(f"Quota enforcement désactivé (mode: {stripe_config.mode})")
            return {
                'can_ask': True,
                'questions_used': 0,
                'monthly_quota': None,  # Illimité
                'questions_remaining': None,  # Illimité
                'plan_name': 'unlimited',
                'quota_enforcement': False,
                'stripe_mode': stripe_config.mode.value
            }

        # Récupérer le plan et le quota
        plan_name, monthly_quota, quota_enforcement = get_user_plan_and_quota(user_email)

        # Si quota illimité (0 ou None) ou enforcement désactivé, autoriser
        if not quota_enforcement or monthly_quota == 0 or monthly_quota is None:
            return {
                'can_ask': True,
                'questions_used': 0,
                'monthly_quota': None,  # Illimité
                'questions_remaining': None,  # Illimité
                'plan_name': plan_name,
                'quota_enforcement': False
            }

        # Récupérer l'usage du mois en cours
        month_year = get_current_month_year()
        usage = get_or_create_monthly_usage(user_email, month_year, monthly_quota)

        questions_used = usage['questions_used']
        questions_remaining = max(0, monthly_quota - questions_used)

        # Vérifier si le quota est dépassé
        if questions_used >= monthly_quota:
            usage_info = {
                'can_ask': False,
                'questions_used': questions_used,
                'monthly_quota': monthly_quota,
                'questions_remaining': 0,
                'plan_name': plan_name,
                'quota_exceeded_at': usage.get('quota_exceeded_at'),
                'month_year': month_year
            }

            raise QuotaExceededException(
                f"Quota mensuel dépassé pour {user_email}. "
                f"Plan {plan_name}: {questions_used}/{monthly_quota} questions utilisées.",
                usage_info=usage_info
            )

        return {
            'can_ask': True,
            'questions_used': questions_used,
            'monthly_quota': monthly_quota,
            'questions_remaining': questions_remaining,
            'plan_name': plan_name,
            'quota_enforcement': True,
            'month_year': month_year
        }

    except QuotaExceededException:
        raise
    except Exception as e:
        logger.error(f"Erreur vérification quota pour {mask_email(user_email)}: {e}")
        # En cas d'erreur, autoriser par défaut (fail-open pour ne pas bloquer les utilisateurs)
        return {
            'can_ask': True,
            'questions_used': 0,
            'monthly_quota': None,
            'questions_remaining': None,
            'plan_name': 'unknown',
            'quota_enforcement': False,
            'error': str(e)
        }


def increment_question_count(user_email: str, success: bool = True, cost_usd: float = 0.0) -> Dict[str, Any]:
    """
    Incrémente le compteur de questions pour l'utilisateur.

    Args:
        user_email: Email de l'utilisateur
        success: True si la question a réussi, False si échec
        cost_usd: Coût de la question en USD (optionnel)

    Returns:
        Dict avec le nouvel état d'usage
    """
    try:
        # Récupérer le plan et le quota
        plan_name, monthly_quota, quota_enforcement = get_user_plan_and_quota(user_email)
        month_year = get_current_month_year()

        # S'assurer que l'enregistrement existe
        get_or_create_monthly_usage(user_email, month_year, monthly_quota)

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Incrémenter le compteur approprié
                if success:
                    cur.execute(
                        """
                        UPDATE monthly_usage_tracking
                        SET
                            questions_used = questions_used + 1,
                            questions_successful = questions_successful + 1,
                            total_cost_usd = total_cost_usd + %s,
                            openai_cost_usd = openai_cost_usd + %s,
                            last_updated = CURRENT_TIMESTAMP,
                            quota_exceeded_at = CASE
                                WHEN questions_used + 1 >= monthly_quota AND quota_exceeded_at IS NULL
                                THEN CURRENT_TIMESTAMP
                                ELSE quota_exceeded_at
                            END,
                            current_status = CASE
                                WHEN questions_used + 1 >= monthly_quota THEN 'quota_exceeded'
                                ELSE current_status
                            END
                        WHERE user_email = %s AND month_year = %s
                        RETURNING questions_used, monthly_quota, current_status, quota_exceeded_at
                        """,
                        (cost_usd, cost_usd, user_email, month_year)
                    )
                else:
                    cur.execute(
                        """
                        UPDATE monthly_usage_tracking
                        SET
                            questions_used = questions_used + 1,
                            questions_failed = questions_failed + 1,
                            last_updated = CURRENT_TIMESTAMP,
                            quota_exceeded_at = CASE
                                WHEN questions_used + 1 >= monthly_quota AND quota_exceeded_at IS NULL
                                THEN CURRENT_TIMESTAMP
                                ELSE quota_exceeded_at
                            END,
                            current_status = CASE
                                WHEN questions_used + 1 >= monthly_quota THEN 'quota_exceeded'
                                ELSE current_status
                            END
                        WHERE user_email = %s AND month_year = %s
                        RETURNING questions_used, monthly_quota, current_status, quota_exceeded_at
                        """,
                        (user_email, month_year)
                    )

                result = cur.fetchone()

                if result:
                    logger.info(
                        f"Question comptée pour {user_email}: "
                        f"{result['questions_used']}/{result['monthly_quota']} "
                        f"(success={success}, cost=${cost_usd:.4f})"
                    )

                    return {
                        'questions_used': result['questions_used'],
                        'monthly_quota': result['monthly_quota'],
                        'questions_remaining': max(0, result['monthly_quota'] - result['questions_used']),
                        'current_status': result['current_status'],
                        'quota_exceeded': result['questions_used'] >= result['monthly_quota'],
                        'quota_exceeded_at': result['quota_exceeded_at']
                    }

                return {'error': 'Failed to update usage'}

    except Exception as e:
        logger.error(f"Erreur incrémentation question pour {mask_email(user_email)}: {e}")
        return {'error': str(e)}


def get_user_usage_stats(user_email: str) -> Dict[str, Any]:
    """
    Récupère les statistiques d'usage pour un utilisateur.
    Utilisé pour afficher dans le frontend.

    Returns:
        Dict avec toutes les infos d'usage du mois en cours
    """
    try:
        plan_name, monthly_quota, quota_enforcement = get_user_plan_and_quota(user_email)
        month_year = get_current_month_year()

        if not quota_enforcement or monthly_quota == 0:
            return {
                'plan_name': plan_name,
                'monthly_quota': None,
                'questions_used': 0,
                'questions_remaining': None,
                'quota_enforcement': False,
                'current_status': 'unlimited',
                'month_year': month_year
            }

        usage = get_or_create_monthly_usage(user_email, month_year, monthly_quota)

        return {
            'plan_name': plan_name,
            'monthly_quota': usage['monthly_quota'],
            'questions_used': usage['questions_used'],
            'questions_remaining': max(0, usage['monthly_quota'] - usage['questions_used']),
            'questions_successful': usage['questions_successful'],
            'questions_failed': usage['questions_failed'],
            'quota_enforcement': quota_enforcement,
            'current_status': usage['current_status'],
            'quota_exceeded_at': usage.get('quota_exceeded_at'),
            'warning_sent': usage.get('warning_sent'),
            'month_year': month_year,
            'percentage_used': round((usage['questions_used'] / usage['monthly_quota']) * 100, 1) if usage['monthly_quota'] > 0 else 0
        }

    except Exception as e:
        logger.error(f"Erreur récupération stats usage pour {mask_email(user_email)}: {e}")
        return {
            'error': str(e),
            'plan_name': 'unknown',
            'monthly_quota': None,
            'questions_used': 0,
            'questions_remaining': None
        }


def reset_monthly_usage_for_all_users() -> Dict[str, Any]:
    """
    Réinitialise les compteurs mensuels pour tous les utilisateurs.
    À appeler automatiquement le 1er de chaque mois via CRON.

    Returns:
        Dict avec le nombre d'utilisateurs réinitialisés
    """
    try:
        month_year = get_current_month_year()

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # ÉTAPE 1: Réinitialiser les enregistrements existants pour le mois actuel
                cur.execute(
                    """
                    UPDATE monthly_usage_tracking
                    SET
                        questions_used = 0,
                        questions_successful = 0,
                        questions_failed = 0,
                        total_cost_usd = 0.00,
                        openai_cost_usd = 0.00,
                        current_status = 'active',
                        warning_sent = FALSE,
                        limit_notifications_sent = 0,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE month_year = %s
                    """,
                    (month_year,)
                )

                updated_count = cur.rowcount

                # ÉTAPE 2: Créer de nouveaux enregistrements pour les utilisateurs
                # qui n'ont pas encore d'enregistrement pour ce mois
                cur.execute(
                    """
                    INSERT INTO monthly_usage_tracking (
                        user_email,
                        month_year,
                        questions_used,
                        questions_successful,
                        questions_failed,
                        total_cost_usd,
                        openai_cost_usd,
                        monthly_quota,
                        current_status,
                        warning_sent,
                        limit_notifications_sent,
                        last_updated
                    )
                    SELECT
                        ubi.user_email,
                        %s as month_year,
                        0 as questions_used,
                        0 as questions_successful,
                        0 as questions_failed,
                        0.00 as total_cost_usd,
                        0.00 as openai_cost_usd,
                        COALESCE(ubi.custom_monthly_quota, bp.monthly_quota, 50) as monthly_quota,
                        'active' as current_status,
                        FALSE as warning_sent,
                        0 as limit_notifications_sent,
                        CURRENT_TIMESTAMP as last_updated
                    FROM user_billing_info ubi
                    LEFT JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM monthly_usage_tracking mut
                        WHERE mut.user_email = ubi.user_email
                          AND mut.month_year = %s
                    )
                    """,
                    (month_year, month_year)
                )

                created_count = cur.rowcount

                logger.info(f"Reset mensuel: {updated_count} enregistrements réinitialisés, {created_count} nouveaux créés pour {month_year}")

                return {
                    'status': 'success',
                    'month_year': month_year,
                    'users_updated': updated_count,
                    'users_created': created_count,
                    'users_reset': updated_count + created_count,
                    'timestamp': datetime.utcnow().isoformat()
                }

    except Exception as e:
        logger.error(f"Erreur reset mensuel: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
