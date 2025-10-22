# app/api/v1/billing.py
# -*- coding: utf-8 -*-
"""
Système complet de facturation et quotas - OPTIMISÉ
Évite les redondances avec logging.py en se concentrant uniquement sur le billing
"""
import json
import os
import logging
from typing import Dict, Any, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Depends, HTTPException, Request
from enum import Enum

# Import authentification
from app.api.v1.auth import get_current_user

# Import geo-location service
from app.services.geo_location import GeoLocationService

# Import country tracking service for pricing fraud detection
try:
    from app.services.country_tracking_service import CountryTrackingService
    COUNTRY_TRACKING_AVAILABLE = True
except ImportError:
    COUNTRY_TRACKING_AVAILABLE = False
    logger.warning("Country tracking service not available")

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger(__name__)

# Supported billing currencies (16 currencies covering 87-90% of global poultry production)
SUPPORTED_BILLING_CURRENCIES = [
    "USD",  # United States
    "EUR",  # Eurozone (France, Germany, Spain, Italy, Netherlands, etc.)
    "CNY",  # China
    "INR",  # India
    "BRL",  # Brazil
    "IDR",  # Indonesia
    "MXN",  # Mexico
    "JPY",  # Japan
    "TRY",  # Turkey
    "GBP",  # United Kingdom
    "ZAR",  # South Africa
    "THB",  # Thailand
    "MYR",  # Malaysia
    "PHP",  # Philippines
    "PLN",  # Poland
    "VND",  # Vietnam
]

CURRENCY_NAMES = {
    "USD": "US Dollar ($)",
    "EUR": "Euro (€)",
    "CNY": "Chinese Yuan (¥)",
    "INR": "Indian Rupee (₹)",
    "BRL": "Brazilian Real (R$)",
    "IDR": "Indonesian Rupiah (Rp)",
    "MXN": "Mexican Peso (MX$)",
    "JPY": "Japanese Yen (¥)",
    "TRY": "Turkish Lira (₺)",
    "GBP": "British Pound (£)",
    "ZAR": "South African Rand (R)",
    "THB": "Thai Baht (฿)",
    "MYR": "Malaysian Ringgit (RM)",
    "PHP": "Philippine Peso (₱)",
    "PLN": "Polish Zloty (zł)",
    "VND": "Vietnamese Dong (₫)",
}


class PlanType(str, Enum):
    ESSENTIAL = "essential"
    PRO = "pro"
    ELITE = "elite"
    INTELIA = "intelia"  # Plan employés - gratuit et illimité


class QuotaStatus(str, Enum):
    AVAILABLE = "available"
    WARNING = "warning"  # 80% utilisé
    NEAR_LIMIT = "near_limit"  # 95% utilisé
    EXCEEDED = "exceeded"


class BillingManager:
    """
    Gestionnaire complet de facturation avec quotas et limitations temps réel
    Se concentre uniquement sur les aspects billing (pas de logging détaillé)
    """

    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        self._load_plan_configurations()

    # NOTE: Les tables de facturation sont gérées via migrations SQL
    # et l'interface admin (/admin/subscriptions).
    # Plus de création automatique de tables ou d'insertion de données par défaut.

    def _load_plan_configurations(self):
        """Charge les configurations des plans en cache"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM billing_plans WHERE active = true")
                    self.plans = {row["plan_name"]: dict(row) for row in cur.fetchall()}
                    logger.info(f"{len(self.plans)} plans de facturation chargés")
        except Exception as e:
            logger.error(f"Erreur chargement plans: {e}")
            self.plans = {}

    def check_quota_before_question(
        self, user_email: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Vérifie si l'utilisateur peut poser une question (quota disponible)
        Retourne (autorisé, détails)
        """
        try:
            current_month = datetime.now().strftime("%Y-%m")

            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Récupérer les infos utilisateur et usage actuel
                    cur.execute(
                        """
                        SELECT 
                            ubi.plan_name,
                            ubi.custom_monthly_quota,
                            ubi.quota_enforcement,
                            bp.monthly_quota as plan_quota,
                            bp.display_name as plan_display_name,
                            mut.questions_used,
                            mut.monthly_quota as current_quota,
                            mut.current_status
                        FROM user_billing_info ubi
                        LEFT JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
                        LEFT JOIN monthly_usage_tracking mut ON ubi.user_email = mut.user_email 
                            AND mut.month_year = %s
                        WHERE ubi.user_email = %s
                    """,
                        (current_month, user_email),
                    )

                    user_info = cur.fetchone()

                    if not user_info:
                        # Nouvel utilisateur - créer avec plan gratuit
                        self._initialize_new_user(user_email)
                        return self.check_quota_before_question(user_email)

                    # Plan Intelia = illimité (employés)
                    if user_info["plan_name"] == "intelia":
                        return True, {
                            "status": "unlimited",
                            "quota": "unlimited",
                            "used": user_info["questions_used"] or 0,
                            "remaining": "unlimited",
                            "plan": "Intelia Team",
                        }

                    # Déterminer le quota effectif
                    quota = (
                        user_info["custom_monthly_quota"]
                        or user_info["plan_quota"]
                        or 100
                    )
                    questions_used = user_info["questions_used"] or 0

                    # Si l'enforcement est désactivé, toujours autoriser
                    if not user_info["quota_enforcement"]:
                        return True, {
                            "status": "unlimited",
                            "quota": quota,
                            "used": questions_used,
                            "remaining": "unlimited",
                        }

                    # Vérifier le quota
                    remaining = quota - questions_used

                    if remaining <= 0:
                        # Quota dépassé
                        self._log_quota_action(
                            user_email,
                            "question_blocked",
                            {
                                "quota": quota,
                                "used": questions_used,
                                "month": current_month,
                            },
                        )

                        return False, {
                            "status": "exceeded",
                            "quota": quota,
                            "used": questions_used,
                            "remaining": 0,
                            "plan": user_info["plan_display_name"],
                            "message": f"Quota mensuel de {quota} questions dépassé. Passez à un plan supérieur ou attendez le mois prochain.",
                        }

                    # Déterminer le statut
                    usage_percent = (questions_used / quota) * 100
                    if usage_percent >= 95:
                        status = QuotaStatus.NEAR_LIMIT
                    elif usage_percent >= 80:
                        status = QuotaStatus.WARNING
                    else:
                        status = QuotaStatus.AVAILABLE

                    return True, {
                        "status": status.value,
                        "quota": quota,
                        "used": questions_used,
                        "remaining": remaining,
                        "usage_percent": round(usage_percent, 1),
                        "plan": user_info["plan_display_name"],
                    }

        except Exception as e:
            logger.error(f"Erreur vérification quota pour {user_email}: {e}")
            # En cas d'erreur, autoriser la question (fail-safe)
            return True, {"status": "error", "message": "Erreur de vérification quota"}

    def increment_usage_after_question(
        self, user_email: str, success: bool = True, cost_usd: float = 0.0
    ) -> None:
        """
        Incrémente l'usage après qu'une question ait été traitée
        OPTIMISÉ: Se contente de mettre à jour les compteurs billing, pas le logging détaillé
        """
        try:
            current_month = datetime.now().strftime("%Y-%m")

            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Récupérer le quota de l'utilisateur
                    cur.execute(
                        """
                        SELECT 
                            COALESCE(ubi.custom_monthly_quota, bp.monthly_quota, 100) as quota
                        FROM user_billing_info ubi
                        LEFT JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
                        WHERE ubi.user_email = %s
                    """,
                        (user_email,),
                    )

                    quota_result = cur.fetchone()
                    quota = quota_result[0] if quota_result else 100

                    # Mettre à jour ou créer l'enregistrement d'usage
                    cur.execute(
                        """
                        INSERT INTO monthly_usage_tracking (
                            user_email, month_year, questions_used, questions_successful, 
                            questions_failed, total_cost_usd, monthly_quota, first_question_at
                        ) VALUES (%s, %s, 1, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_email, month_year) 
                        DO UPDATE SET 
                            questions_used = monthly_usage_tracking.questions_used + 1,
                            questions_successful = monthly_usage_tracking.questions_successful + %s,
                            questions_failed = monthly_usage_tracking.questions_failed + %s,
                            total_cost_usd = monthly_usage_tracking.total_cost_usd + %s,
                            last_updated = CURRENT_TIMESTAMP
                    """,
                        (
                            user_email,
                            current_month,
                            1 if success else 0,
                            0 if success else 1,
                            cost_usd,
                            quota,
                            1 if success else 0,
                            0 if success else 1,
                            cost_usd,
                        ),
                    )

                    # Mettre à jour le statut si nécessaire
                    self._update_quota_status(cur, user_email, current_month)

                    conn.commit()

                    # Log simple de l'action (pas détaillé comme dans logging.py)
                    self._log_quota_action(
                        user_email,
                        "question_allowed",
                        {
                            "success": success,
                            "cost_usd": cost_usd,
                            "month": current_month,
                        },
                    )

        except Exception as e:
            logger.error(f"Erreur incrémentation usage pour {user_email}: {e}")

    def _update_quota_status(self, cur, user_email: str, month_year: str) -> None:
        """Met à jour le statut du quota après usage"""
        try:
            cur.execute(
                """
                SELECT questions_used, monthly_quota 
                FROM monthly_usage_tracking 
                WHERE user_email = %s AND month_year = %s
            """,
                (user_email, month_year),
            )

            result = cur.fetchone()
            if not result:
                return

            questions_used, quota = result
            usage_percent = (questions_used / quota) * 100

            # Déterminer le nouveau statut
            if questions_used >= quota:
                new_status = QuotaStatus.EXCEEDED
                # Marquer le moment où le quota a été dépassé
                cur.execute(
                    """
                    UPDATE monthly_usage_tracking 
                    SET current_status = %s, quota_exceeded_at = CURRENT_TIMESTAMP
                    WHERE user_email = %s AND month_year = %s AND quota_exceeded_at IS NULL
                """,
                    (new_status.value, user_email, month_year),
                )
            elif usage_percent >= 95:
                new_status = QuotaStatus.NEAR_LIMIT
            elif usage_percent >= 80:
                new_status = QuotaStatus.WARNING
            else:
                new_status = QuotaStatus.AVAILABLE

            # Mettre à jour le statut
            cur.execute(
                """
                UPDATE monthly_usage_tracking 
                SET current_status = %s 
                WHERE user_email = %s AND month_year = %s
            """,
                (new_status.value, user_email, month_year),
            )

        except Exception as e:
            logger.error(f"Erreur update quota status: {e}")

    def _initialize_new_user(self, user_email: str, plan_name: str = "free") -> None:
        """Initialise un nouvel utilisateur avec un plan par défaut"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO user_billing_info (user_email, plan_name)
                        VALUES (%s, %s)
                        ON CONFLICT (user_email) DO NOTHING
                    """,
                        (user_email, plan_name),
                    )
                    conn.commit()
                    logger.info(
                        f"Nouvel utilisateur initialisé: {user_email} - Plan: {plan_name}"
                    )
        except Exception as e:
            logger.error(f"Erreur initialisation utilisateur {user_email}: {e}")

    def _log_quota_action(
        self, user_email: str, action: str, details: Dict[str, Any]
    ) -> None:
        """Log des actions liées aux quotas pour audit (simplifié)"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO quota_audit_log (user_email, action, details)
                        VALUES (%s, %s, %s)
                    """,
                        (user_email, action, json.dumps(details)),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Erreur log quota action: {e}")

    def generate_monthly_invoice(
        self, user_email: str, year: int, month: int
    ) -> Dict[str, Any]:
        """Génère une facture mensuelle pour un utilisateur"""
        try:
            month_year = f"{year:04d}-{month:02d}"

            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Récupérer les données de facturation
                    cur.execute(
                        """
                        SELECT 
                            ubi.plan_name,
                            bp.display_name,
                            bp.price_per_month,
                            bp.overage_rate,
                            COALESCE(ubi.custom_monthly_quota, bp.monthly_quota) as quota,
                            mut.questions_used,
                            mut.total_cost_usd
                        FROM user_billing_info ubi
                        LEFT JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
                        LEFT JOIN monthly_usage_tracking mut ON ubi.user_email = mut.user_email 
                            AND mut.month_year = %s
                        WHERE ubi.user_email = %s
                    """,
                        (month_year, user_email),
                    )

                    billing_data = cur.fetchone()

                    if not billing_data:
                        return {
                            "error": f"Aucune donnée de facturation pour {user_email}"
                        }

                    # Calculs de facturation
                    questions_used = billing_data["questions_used"] or 0
                    quota = billing_data["quota"]
                    base_amount = billing_data["price_per_month"]

                    # Calcul des dépassements
                    overage_questions = max(0, questions_used - quota)
                    overage_amount = overage_questions * billing_data["overage_rate"]
                    total_amount = base_amount + overage_amount

                    # Breakdown détaillé
                    breakdown = {
                        "plan": billing_data["display_name"],
                        "quota_included": quota,
                        "questions_used": questions_used,
                        "base_price": float(base_amount),
                        "overage_questions": overage_questions,
                        "overage_rate": float(billing_data["overage_rate"]),
                        "overage_amount": float(overage_amount),
                        "openai_costs": float(billing_data["total_cost_usd"] or 0),
                    }

                    # Insérer ou mettre à jour la facture
                    cur.execute(
                        """
                        INSERT INTO monthly_invoices (
                            user_email, month_year, plan_name, questions_included,
                            questions_used, overage_questions, base_amount, 
                            overage_amount, total_amount, breakdown
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_email, month_year)
                        DO UPDATE SET 
                            questions_used = EXCLUDED.questions_used,
                            overage_questions = EXCLUDED.overage_questions,
                            overage_amount = EXCLUDED.overage_amount,
                            total_amount = EXCLUDED.total_amount,
                            breakdown = EXCLUDED.breakdown
                    """,
                        (
                            user_email,
                            month_year,
                            billing_data["plan_name"],
                            quota,
                            questions_used,
                            overage_questions,
                            base_amount,
                            overage_amount,
                            total_amount,
                            json.dumps(breakdown),
                        ),
                    )

                    conn.commit()

                    return {
                        "user_email": user_email,
                        "month_year": month_year,
                        "invoice_data": breakdown,
                        "total_amount": float(total_amount),
                        "currency": "EUR",
                        "status": "generated",
                    }

        except Exception as e:
            logger.error(f"Erreur génération facture pour {user_email}: {e}")
            return {"error": str(e)}

    def change_user_plan(
        self, user_email: str, new_plan: str, effective_date: datetime = None
    ) -> Dict[str, Any]:
        """Change le plan d'un utilisateur"""
        try:
            if new_plan not in self.plans:
                return {"error": f"Plan '{new_plan}' non trouvé"}

            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Mettre à jour le plan utilisateur
                    cur.execute(
                        """
                        UPDATE user_billing_info 
                        SET plan_name = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_email = %s
                    """,
                        (new_plan, user_email),
                    )

                    if cur.rowcount == 0:
                        # Créer l'utilisateur s'il n'existe pas
                        cur.execute(
                            """
                            INSERT INTO user_billing_info (user_email, plan_name)
                            VALUES (%s, %s)
                        """,
                            (user_email, new_plan),
                        )

                    conn.commit()

                    # Log de l'action
                    self._log_quota_action(
                        user_email,
                        "plan_changed",
                        {
                            "new_plan": new_plan,
                            "effective_date": (
                                effective_date or datetime.now()
                            ).isoformat(),
                        },
                    )

                    return {
                        "user_email": user_email,
                        "new_plan": new_plan,
                        "plan_details": self.plans[new_plan],
                        "status": "updated",
                    }

        except Exception as e:
            logger.error(f"Erreur changement plan pour {user_email}: {e}")
            return {"error": str(e)}

    def get_user_billing_summary(self, user_email: str) -> Dict[str, Any]:
        """Résumé complet de facturation pour un utilisateur"""
        try:
            current_month = datetime.now().strftime("%Y-%m")

            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Informations utilisateur et usage actuel
                    cur.execute(
                        """
                        SELECT 
                            ubi.plan_name,
                            bp.display_name,
                            bp.price_per_month,
                            COALESCE(ubi.custom_monthly_quota, bp.monthly_quota) as quota,
                            mut.questions_used,
                            mut.current_status,
                            mut.total_cost_usd,
                            mut.first_question_at
                        FROM user_billing_info ubi
                        LEFT JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
                        LEFT JOIN monthly_usage_tracking mut ON ubi.user_email = mut.user_email 
                            AND mut.month_year = %s
                        WHERE ubi.user_email = %s
                    """,
                        (current_month, user_email),
                    )

                    current_data = cur.fetchone()

                    if not current_data:
                        return {"error": f"Utilisateur {user_email} non trouvé"}

                    # Historique des factures
                    cur.execute(
                        """
                        SELECT month_year, total_amount, status
                        FROM monthly_invoices 
                        WHERE user_email = %s
                        ORDER BY month_year DESC
                        LIMIT 12
                    """,
                        (user_email,),
                    )

                    invoice_history = [dict(row) for row in cur.fetchall()]

                    return {
                        "user_email": user_email,
                        "current_month": current_month,
                        "plan": {
                            "name": current_data["plan_name"],
                            "display_name": current_data["display_name"],
                            "monthly_price": float(
                                current_data["price_per_month"] or 0
                            ),
                        },
                        "current_usage": {
                            "quota": current_data["quota"],
                            "used": current_data["questions_used"] or 0,
                            "remaining": (current_data["quota"] or 0)
                            - (current_data["questions_used"] or 0),
                            "status": current_data["current_status"] or "available",
                            "costs_usd": float(current_data["total_cost_usd"] or 0),
                        },
                        "invoice_history": invoice_history,
                    }

        except Exception as e:
            logger.error(f"Erreur billing summary pour {user_email}: {e}")
            return {"error": str(e)}


# Singleton
_billing_manager = None


def get_billing_manager() -> BillingManager:
    global _billing_manager
    if _billing_manager is None:
        _billing_manager = BillingManager()
    return _billing_manager


# ========== ENDPOINTS DE FACTURATION ==========


@router.get("/quota-check/{user_email}")
def check_user_quota(
    user_email: str, current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Vérification du quota utilisateur"""

    # Sécurité
    if current_user.get("email") != user_email and not current_user.get(
        "is_admin", False
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    billing = get_billing_manager()
    allowed, details = billing.check_quota_before_question(user_email)

    return {"user_email": user_email, "quota_available": allowed, "details": details}


@router.get("/my-billing")
def my_billing_info(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Informations de facturation personnelles"""

    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="User email not found")

    billing = get_billing_manager()
    return billing.get_user_billing_summary(user_email)


@router.post("/change-plan")
def change_user_plan(
    new_plan: str, current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Changement de plan de facturation

    Vérifie que l'utilisateur a choisi sa devise de facturation
    avant de permettre l'upgrade vers un plan payant
    """

    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="User email not found")

    # Bloquer le changement vers le plan Intelia (réservé aux employés)
    if new_plan == "intelia":
        raise HTTPException(
            status_code=403,
            detail="Le plan Intelia est réservé aux employés. Veuillez contacter l'équipe."
        )

    # Si upgrade vers un plan payant, vérifier que la devise est définie
    if new_plan != "essential":
        try:
            with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT billing_currency
                        FROM user_billing_info
                        WHERE user_email = %s
                    """, (user_email,))

                    result = cur.fetchone()
                    billing_currency = result["billing_currency"] if result else None

                    if not billing_currency:
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": "billing_currency_required",
                                "message": "Please select your billing currency before upgrading to a paid plan",
                                "action_required": "set_billing_currency",
                                "available_currencies": SUPPORTED_BILLING_CURRENCIES
                            }
                        )

                    logger.info(f"Billing currency verified for {user_email}: {billing_currency}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking billing currency: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    billing = get_billing_manager()
    return billing.change_user_plan(user_email, new_plan)


@router.post("/generate-invoice/{user_email}/{year}/{month}")
def generate_invoice(
    user_email: str,
    year: int,
    month: int,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Génération de facture mensuelle"""

    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    billing = get_billing_manager()
    return billing.generate_monthly_invoice(user_email, year, month)


@router.get("/plans")
def available_plans(request: Request, country: str = None, current_user: dict = None) -> Dict[str, Any]:
    """
    Liste des plans disponibles avec prix localisés - ENDPOINT PUBLIC

    Détecte automatiquement le pays de l'utilisateur via son IP
    et retourne les prix dans la devise locale

    Args:
        request: FastAPI Request object (pour extraire l'IP)
        country: Code pays optionnel (2 lettres) pour forcer un pays spécifique
        current_user: Utilisateur connecté (optionnel)

    Returns:
        Plans avec prix localisés selon le pays détecté
        + billing_currency si utilisateur connecté
    """

    # Essayer de récupérer l'utilisateur connecté (optionnel)
    user_billing_currency = None
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from fastapi.security import HTTPAuthorizationCredentials
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=auth_header.replace("Bearer ", "")
            )
            from app.api.v1.auth import get_current_user
            import asyncio
            current_user = asyncio.run(get_current_user(credentials))

            # Si l'utilisateur est authentifié, récupérer sa devise de facturation
            if current_user:
                try:
                    with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
                        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                            cur.execute("""
                                SELECT billing_currency
                                FROM user_billing_info
                                WHERE user_email = %s
                            """, (current_user.get("email"),))
                            billing_row = cur.fetchone()
                            if billing_row:
                                user_billing_currency = billing_row.get("billing_currency")
                                logger.debug(f"User {current_user.get('email')} billing_currency: {user_billing_currency}")
                except Exception as e:
                    logger.warning(f"Could not fetch billing_currency for user: {e}")
    except:
        # Pas grave si l'auth échoue, endpoint reste public
        current_user = None

    # Étape 1: Déterminer le pays
    detected_country = None
    detection_method = "default"

    if country:
        # Pays spécifié manuellement
        detected_country = country.upper()
        detection_method = "manual"
        logger.info(f"Using manually specified country: {detected_country}")
    else:
        # Détecter automatiquement via IP
        client_ip = GeoLocationService.get_client_ip(request)
        geo_info = GeoLocationService.get_country_from_ip(client_ip)

        if geo_info:
            detected_country = geo_info["country_code"]
            detection_method = "auto_ip"
            logger.info(f"Auto-detected country for {client_ip}: {detected_country} ({geo_info['country_name']})")
        else:
            logger.warning(f"Could not detect country for IP {client_ip}, using default (US)")

    # Fallback to USA if detection failed
    if not detected_country:
        detected_country = "US"
        detection_method = "fallback"

    # Étape 2: Récupérer les prix depuis complete_pricing_matrix
    try:
        with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Récupérer les prix pour ce pays (exclure le plan Intelia - employés seulement)
                cur.execute("""
                    SELECT
                        plan_name,
                        tier_price_usd,
                        display_price,
                        display_currency,
                        display_currency_symbol,
                        price_type,
                        country_name,
                        tier_level
                    FROM complete_pricing_matrix
                    WHERE country_code = %s
                      AND plan_name != 'intelia'
                    ORDER BY
                        CASE plan_name
                            WHEN 'essential' THEN 1
                            WHEN 'pro' THEN 2
                            WHEN 'elite' THEN 3
                            ELSE 4
                        END
                """, (detected_country,))

                pricing_data = cur.fetchall()

                # Si le pays n'existe pas dans notre base, fallback vers USA
                if not pricing_data:
                    logger.warning(f"Country {detected_country} not found in pricing matrix, falling back to US")
                    detected_country = "US"
                    detection_method = "fallback_not_found"

                    cur.execute("""
                        SELECT
                            plan_name,
                            tier_price_usd,
                            display_price,
                            display_currency,
                            display_currency_symbol,
                            price_type,
                            country_name,
                            tier_level
                        FROM complete_pricing_matrix
                        WHERE country_code = 'US'
                          AND plan_name != 'intelia'
                        ORDER BY
                            CASE plan_name
                                WHEN 'essential' THEN 1
                                WHEN 'pro' THEN 2
                                WHEN 'elite' THEN 3
                                ELSE 4
                            END
                    """)
                    pricing_data = cur.fetchall()

                # Formater les données des plans
                plans = {}
                currency = "USD"
                currency_symbol = "$"
                country_name = "United States"

                for row in pricing_data:
                    plan_name = row["plan_name"]
                    currency = row["display_currency"]
                    currency_symbol = row["display_currency_symbol"]
                    country_name = row["country_name"]

                    plans[plan_name] = {
                        "name": plan_name,
                        "display_name": plan_name.capitalize(),
                        "price": float(row["display_price"]),
                        "price_usd": float(row["tier_price_usd"]),
                        "currency": currency,
                        "currency_symbol": currency_symbol,
                        "price_type": row["price_type"],  # "auto_marketing" or "custom"
                        "tier_level": row["tier_level"],
                        "formatted_price": f"{currency_symbol}{row['display_price']:.2f}"
                    }

                logger.info(f"Returning {len(plans)} plans for {detected_country} ({country_name}) in {currency}")

                response_data = {
                    "plans": plans,
                    "currency": currency,
                    "currency_symbol": currency_symbol,
                    "country_code": detected_country,
                    "country_name": country_name,
                    "detection_method": detection_method,
                    "public": True,
                    "description": f"Plans de facturation pour {country_name}",
                }

                # Ajouter billing_currency si utilisateur authentifié
                if user_billing_currency:
                    response_data["billing_currency"] = user_billing_currency
                    response_data["billing_currency_set"] = True
                elif current_user:
                    # Utilisateur connecté mais pas de billing_currency définie
                    response_data["billing_currency"] = None
                    response_data["billing_currency_set"] = False

                return response_data

    except Exception as e:
        logger.error(f"Error fetching localized plans: {e}")
        # En cas d'erreur, retourner les plans de base
        billing = get_billing_manager()
        return {
            "plans": billing.plans,
            "currency": "USD",
            "currency_symbol": "$",
            "country_code": "US",
            "country_name": "United States",
            "detection_method": "error_fallback",
            "public": True,
            "description": "Plans de facturation (fallback)",
            "error": str(e)
        }


@router.get("/currency-preference")
async def get_currency_preference(
    current_user: dict = Depends(get_current_user),
    request: Request = None
) -> Dict[str, Any]:
    """
    Récupère la devise de facturation choisie par l'utilisateur
    Avec suggestion intelligente selon le pays détecté
    """
    user_email = current_user.get("email")

    try:
        with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Récupérer la devise actuelle
                cur.execute("""
                    SELECT billing_currency
                    FROM user_billing_info
                    WHERE user_email = %s
                """, (user_email,))

                result = cur.fetchone()
                current_currency = result["billing_currency"] if result else None

                # Détection du pays pour suggestion
                client_ip = GeoLocationService.get_client_ip(request) if request else None
                geo_info = GeoLocationService.get_country_from_ip(client_ip) if client_ip else None
                detected_country = geo_info["country_code"] if geo_info else "US"

                # Suggestion basée sur le pays
                cur.execute("""
                    SELECT suggest_billing_currency(%s) as suggested_currency
                """, (detected_country,))

                suggestion = cur.fetchone()
                suggested_currency = suggestion["suggested_currency"]

                return {
                    "billing_currency": current_currency,
                    "is_set": current_currency is not None,
                    "suggested_currency": suggested_currency,
                    "detected_country": detected_country,
                    "available_currencies": SUPPORTED_BILLING_CURRENCIES,
                    "currency_names": CURRENCY_NAMES
                }

    except Exception as e:
        logger.error(f"Error fetching currency preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set-currency")
async def set_currency_preference(
    currency: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Définit la devise de facturation préférée de l'utilisateur

    Args:
        currency: Code devise (USD, EUR, ou CAD)
    """
    user_email = current_user.get("email")

    # Validation
    if currency not in SUPPORTED_BILLING_CURRENCIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid currency. Must be one of: {', '.join(SUPPORTED_BILLING_CURRENCIES)}. Got: {currency}"
        )

    try:
        with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Mettre à jour la devise
                cur.execute("""
                    UPDATE user_billing_info
                    SET billing_currency = %s
                    WHERE user_email = %s
                    RETURNING billing_currency
                """, (currency, user_email))

                result = cur.fetchone()

                # Si l'utilisateur n'existe pas encore dans user_billing_info
                if not result:
                    cur.execute("""
                        INSERT INTO user_billing_info (user_email, plan_name, billing_currency)
                        VALUES (%s, 'essential', %s)
                        ON CONFLICT (user_email) DO UPDATE
                        SET billing_currency = EXCLUDED.billing_currency
                        RETURNING billing_currency
                    """, (user_email, currency))
                    result = cur.fetchone()

                conn.commit()

                logger.info(f"Billing currency set for {user_email}: {currency}")

                return {
                    "success": True,
                    "billing_currency": currency,
                    "message": f"Billing currency set to {currency}"
                }

    except Exception as e:
        logger.error(f"Error setting currency preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PRICING FRAUD PREVENTION ENDPOINTS
# ============================================================================

@router.get("/pricing-info")
async def get_pricing_info(
    current_user: dict = Depends(get_current_user),
    request: Request = None
) -> Dict[str, Any]:
    """
    Get user's pricing tier and regionalized prices
    Returns the pricing tier (locked or suggested) and converted prices
    """
    if not COUNTRY_TRACKING_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Country tracking service not available"
        )

    user_email = current_user.get("email")

    try:
        billing = get_billing_manager()

        with psycopg2.connect(billing.dsn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get user's billing info
                cur.execute("""
                    SELECT
                        pricing_tier,
                        pricing_country,
                        signup_country,
                        pricing_locked_at,
                        billing_currency
                    FROM user_billing_info
                    WHERE user_email = %s
                """, (user_email,))

                billing_info = cur.fetchone()

                if not billing_info or not billing_info.get('pricing_tier'):
                    # First time - detect country and suggest tier
                    country_info = await CountryTrackingService.get_user_country(user_email, request)
                    country_code = country_info.get('country_code', 'US')

                    # Get suggested pricing tier
                    cur.execute("""
                        SELECT tier, base_price_usd
                        FROM pricing_tiers
                        WHERE country_code = %s
                    """, (country_code,))

                    tier_info = cur.fetchone()

                    if not tier_info:
                        # Default to tier1 if country not found
                        tier_info = {'tier': 'tier1', 'base_price_usd': 18.00}

                    return {
                        "pricing_tier": tier_info['tier'],
                        "pricing_country": country_code,
                        "signup_country": billing_info.get('signup_country') if billing_info else country_code,
                        "is_locked": False,
                        "base_price_usd": float(tier_info['base_price_usd']),
                        "billing_currency": billing_info.get('billing_currency') if billing_info else "USD",
                        "available_currencies": SUPPORTED_BILLING_CURRENCIES
                    }

                # Get base price for tier
                cur.execute("""
                    SELECT base_price_usd
                    FROM pricing_tiers
                    WHERE country_code = %s
                """, (billing_info['pricing_country'],))

                tier_price = cur.fetchone()
                base_price = float(tier_price['base_price_usd']) if tier_price else 18.00

                return {
                    "pricing_tier": billing_info['pricing_tier'],
                    "pricing_country": billing_info['pricing_country'],
                    "signup_country": billing_info['signup_country'],
                    "is_locked": billing_info['pricing_locked_at'] is not None,
                    "locked_at": billing_info['pricing_locked_at'].isoformat() if billing_info['pricing_locked_at'] else None,
                    "base_price_usd": base_price,
                    "billing_currency": billing_info['billing_currency'] or "USD",
                    "available_currencies": SUPPORTED_BILLING_CURRENCIES
                }

    except Exception as e:
        logger.error(f"Error getting pricing info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fraud-analysis")
async def get_fraud_analysis(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get fraud risk analysis for current user
    Admin or user themselves can access this
    """
    if not COUNTRY_TRACKING_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Country tracking service not available"
        )

    user_email = current_user.get("email")

    try:
        analysis = await CountryTrackingService.get_user_fraud_analysis(user_email)

        return {
            "success": True,
            "fraud_analysis": analysis
        }

    except Exception as e:
        logger.error(f"Error getting fraud analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lock-pricing-tier")
async def lock_pricing_tier(
    current_user: dict = Depends(get_current_user),
    request: Request = None
) -> Dict[str, Any]:
    """
    Lock the pricing tier for a user (called when they subscribe)
    This prevents them from changing their pricing tier later
    """
    if not COUNTRY_TRACKING_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Country tracking service not available"
        )

    user_email = current_user.get("email")

    try:
        lock_info = await CountryTrackingService.lock_pricing_tier(user_email, request)

        logger.info(
            f"[Pricing] Tier locked for {user_email}: "
            f"{lock_info['pricing_tier']} (country: {lock_info['pricing_country']})"
        )

        return {
            "success": True,
            "pricing_tier": lock_info['pricing_tier'],
            "pricing_country": lock_info['pricing_country'],
            "base_price_usd": lock_info['base_price_usd'],
            "message": "Pricing tier locked successfully"
        }

    except Exception as e:
        logger.error(f"Error locking pricing tier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin")
async def billing_admin_dashboard(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Dashboard administrateur pour la facturation
    Statistiques globales de billing et gestion des plans
    """

    # Vérification des permissions admin
    if (
        not current_user.get("is_admin", False)
        and current_user.get("user_type") != "super_admin"
    ):
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        billing = get_billing_manager()
        current_month = datetime.now().strftime("%Y-%m")

        with psycopg2.connect(billing.dsn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # 1. Statistiques générales de facturation
                cur.execute(
                    """
                    SELECT 
                        COUNT(DISTINCT user_email) as total_billing_users,
                        COUNT(DISTINCT user_email) FILTER (WHERE plan_name != 'free') as paid_users,
                        COUNT(DISTINCT user_email) FILTER (WHERE plan_name = 'free') as free_users
                    FROM user_billing_info
                """
                )
                user_stats = dict(cur.fetchone() or {})

                # 2. Répartition par plans
                cur.execute(
                    """
                    SELECT 
                        ubi.plan_name,
                        bp.display_name,
                        bp.price_per_month,
                        COUNT(ubi.user_email) as user_count,
                        ROUND(COUNT(ubi.user_email) * 100.0 / SUM(COUNT(ubi.user_email)) OVER (), 2) as percentage
                    FROM user_billing_info ubi
                    LEFT JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
                    GROUP BY ubi.plan_name, bp.display_name, bp.price_per_month
                    ORDER BY user_count DESC
                """
                )
                plan_distribution = [dict(row) for row in cur.fetchall()]

                # 3. Usage du mois en cours
                cur.execute(
                    """
                    SELECT 
                        COUNT(DISTINCT user_email) as active_users_this_month,
                        SUM(questions_used) as total_questions_this_month,
                        SUM(total_cost_usd) as total_openai_costs,
                        AVG(questions_used) as avg_questions_per_user,
                        COUNT(*) FILTER (WHERE current_status = 'exceeded') as users_over_quota
                    FROM monthly_usage_tracking
                    WHERE month_year = %s
                """,
                    (current_month,),
                )
                usage_stats = dict(cur.fetchone() or {})

                # 4. Top consommateurs ce mois
                cur.execute(
                    """
                    SELECT 
                        mut.user_email,
                        ubi.plan_name,
                        mut.questions_used,
                        mut.monthly_quota,
                        mut.current_status,
                        ROUND(mut.questions_used * 100.0 / mut.monthly_quota, 1) as usage_percent
                    FROM monthly_usage_tracking mut
                    LEFT JOIN user_billing_info ubi ON mut.user_email = ubi.user_email
                    WHERE mut.month_year = %s
                    ORDER BY mut.questions_used DESC
                    LIMIT 10
                """,
                    (current_month,),
                )
                top_consumers = [dict(row) for row in cur.fetchall()]

                # 5. Revenus potentiels (estimés)
                cur.execute(
                    """
                    SELECT 
                        SUM(bp.price_per_month) as monthly_recurring_revenue,
                        SUM(CASE 
                            WHEN mut.questions_used > mut.monthly_quota 
                            THEN (mut.questions_used - mut.monthly_quota) * bp.overage_rate 
                            ELSE 0 
                        END) as overage_revenue_this_month
                    FROM user_billing_info ubi
                    LEFT JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
                    LEFT JOIN monthly_usage_tracking mut ON ubi.user_email = mut.user_email 
                        AND mut.month_year = %s
                """,
                    (current_month,),
                )
                revenue_stats = dict(cur.fetchone() or {})

                # 6. Alertes et actions requises
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) FILTER (WHERE current_status = 'exceeded') as quota_exceeded_users,
                        COUNT(*) FILTER (WHERE current_status = 'near_limit') as near_limit_users,
                        COUNT(*) FILTER (WHERE current_status = 'warning') as warning_users
                    FROM monthly_usage_tracking
                    WHERE month_year = %s
                """,
                    (current_month,),
                )
                alerts = dict(cur.fetchone() or {})

                # 7. Activité des derniers 7 jours
                cur.execute(
                    """
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as billing_actions
                    FROM quota_audit_log
                    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """
                )
                recent_activity = [dict(row) for row in cur.fetchall()]

                return {
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                    "current_month": current_month,
                    "user_overview": {
                        "total_billing_users": user_stats.get("total_billing_users", 0),
                        "paid_users": user_stats.get("paid_users", 0),
                        "free_users": user_stats.get("free_users", 0),
                        "conversion_rate": round(
                            (
                                user_stats.get("paid_users", 0)
                                / max(user_stats.get("total_billing_users", 1), 1)
                            )
                            * 100,
                            2,
                        ),
                    },
                    "plan_distribution": plan_distribution,
                    "usage_this_month": {
                        "active_users": usage_stats.get("active_users_this_month", 0),
                        "total_questions": usage_stats.get(
                            "total_questions_this_month", 0
                        ),
                        "avg_questions_per_user": float(
                            usage_stats.get("avg_questions_per_user", 0) or 0
                        ),
                        "users_over_quota": usage_stats.get("users_over_quota", 0),
                        "total_openai_costs_usd": float(
                            usage_stats.get("total_openai_costs", 0) or 0
                        ),
                    },
                    "revenue_metrics": {
                        "monthly_recurring_revenue": float(
                            revenue_stats.get("monthly_recurring_revenue", 0) or 0
                        ),
                        "overage_revenue_this_month": float(
                            revenue_stats.get("overage_revenue_this_month", 0) or 0
                        ),
                        "currency": "EUR",
                    },
                    "alerts": {
                        "quota_exceeded_users": alerts.get("quota_exceeded_users", 0),
                        "near_limit_users": alerts.get("near_limit_users", 0),
                        "warning_users": alerts.get("warning_users", 0),
                    },
                    "top_consumers": top_consumers,
                    "recent_activity": recent_activity,
                    "available_plans": billing.plans,
                    "admin_capabilities": [
                        "view_all_user_billing",
                        "change_user_plans",
                        "generate_invoices",
                        "manage_quotas",
                        "view_revenue_metrics",
                        "export_billing_data",
                    ],
                }

    except Exception as e:
        logger.error(f"Erreur dashboard admin billing: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ========== MIDDLEWARE POUR EXPERT.PY ==========


def check_quota_middleware(user_email: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Middleware à appeler AVANT le traitement de chaque question
    Retourne (autorisé, détails_quota)
    """
    try:
        billing = get_billing_manager()
        return billing.check_quota_before_question(user_email)
    except Exception as e:
        logger.error(f"Erreur quota middleware: {e}")
        # En cas d'erreur, autoriser (fail-safe)
        return True, {"status": "error", "message": "Erreur système"}


def increment_quota_usage(
    user_email: str, success: bool = True, cost_usd: float = 0.0
) -> None:
    """
    Middleware à appeler APRÈS le traitement de chaque question
    """
    try:
        billing = get_billing_manager()
        billing.increment_usage_after_question(user_email, success, cost_usd)
    except Exception as e:
        logger.error(f"Erreur increment quota: {e}")
