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
from fastapi import APIRouter, Depends, HTTPException
from enum import Enum

# Import authentification
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger(__name__)


class PlanType(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


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
        self._ensure_billing_tables()
        self._load_plan_configurations()

    def _ensure_billing_tables(self):
        """Crée UNIQUEMENT les tables de facturation et quotas (pas analytics)"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Table des plans de facturation
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS billing_plans (
                            plan_name VARCHAR(50) PRIMARY KEY,
                            display_name VARCHAR(100),
                            monthly_quota INTEGER NOT NULL,
                            price_per_month DECIMAL(10,2) DEFAULT 0.00,
                            price_per_question DECIMAL(6,4) DEFAULT 0.0000,
                            overage_rate DECIMAL(6,4) DEFAULT 0.0100,
                            features JSONB DEFAULT '{}',
                            active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """
                    )

                    # Insérer les plans par défaut
                    cur.execute(
                        """
                        INSERT INTO billing_plans (plan_name, display_name, monthly_quota, price_per_month, overage_rate, features)
                        VALUES 
                            ('free', 'Plan Gratuit', 100, 0.00, 0.02, '{"support": "community", "priority": "low"}'),
                            ('basic', 'Plan Basic', 1000, 29.99, 0.015, '{"support": "email", "priority": "normal"}'),
                            ('premium', 'Plan Premium', 5000, 99.99, 0.01, '{"support": "priority", "priority": "high", "advanced_features": true}'),
                            ('enterprise', 'Plan Enterprise', 50000, 499.99, 0.005, '{"support": "dedicated", "priority": "highest", "custom_features": true}')
                        ON CONFLICT (plan_name) DO NOTHING;
                    """
                    )

                    # Table des utilisateurs avec plans et quotas
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS user_billing_info (
                            user_email VARCHAR(255) PRIMARY KEY,
                            plan_name VARCHAR(50) DEFAULT 'free' REFERENCES billing_plans(plan_name),
                            custom_monthly_quota INTEGER, -- Override du quota si nécessaire
                            billing_enabled BOOLEAN DEFAULT TRUE,
                            quota_enforcement BOOLEAN DEFAULT TRUE, -- Peut désactiver la limitation
                            
                            -- Informations de facturation
                            billing_address JSONB,
                            payment_method JSONB,
                            billing_contact_email VARCHAR(255),
                            
                            -- Métadonnées
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            notes TEXT
                        );
                    """
                    )

                    # Table de tracking d'usage mensuel en temps réel
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS monthly_usage_tracking (
                            id SERIAL PRIMARY KEY,
                            user_email VARCHAR(255) NOT NULL,
                            month_year VARCHAR(7) NOT NULL, -- YYYY-MM
                            
                            -- Compteurs en temps réel
                            questions_used INTEGER DEFAULT 0,
                            questions_successful INTEGER DEFAULT 0,
                            questions_failed INTEGER DEFAULT 0,
                            
                            -- Coûts calculés
                            total_cost_usd DECIMAL(10,6) DEFAULT 0,
                            openai_cost_usd DECIMAL(10,6) DEFAULT 0,
                            
                            -- Quotas et limites
                            monthly_quota INTEGER NOT NULL,
                            quota_exceeded_at TIMESTAMP,
                            
                            -- Status et flags
                            current_status VARCHAR(20) DEFAULT 'available',
                            warning_sent BOOLEAN DEFAULT FALSE,
                            limit_notifications_sent INTEGER DEFAULT 0,
                            
                            -- Timestamps
                            first_question_at TIMESTAMP,
                            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            UNIQUE(user_email, month_year)
                        );
                    """
                    )

                    # Table de factures mensuelles
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS monthly_invoices (
                            id SERIAL PRIMARY KEY,
                            user_email VARCHAR(255) NOT NULL,
                            month_year VARCHAR(7) NOT NULL,
                            
                            -- Détails facturation
                            plan_name VARCHAR(50),
                            questions_included INTEGER,
                            questions_used INTEGER,
                            overage_questions INTEGER DEFAULT 0,
                            
                            -- Montants
                            base_amount DECIMAL(10,2),
                            overage_amount DECIMAL(10,2) DEFAULT 0,
                            total_amount DECIMAL(10,2),
                            currency VARCHAR(3) DEFAULT 'EUR',
                            
                            -- Status facture
                            status VARCHAR(20) DEFAULT 'draft', -- draft, issued, paid, overdue
                            issued_at TIMESTAMP,
                            due_at TIMESTAMP,
                            paid_at TIMESTAMP,
                            
                            -- Détails techniques
                            breakdown JSONB DEFAULT '{}',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            UNIQUE(user_email, month_year)
                        );
                    """
                    )

                    # Table d'audit des actions de quota (simplifié)
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS quota_audit_log (
                            id SERIAL PRIMARY KEY,
                            user_email VARCHAR(255) NOT NULL,
                            action VARCHAR(50) NOT NULL, -- question_allowed, question_blocked, quota_exceeded, quota_reset
                            details JSONB DEFAULT '{}',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """
                    )

                    # Indexes pour performance (uniquement billing)
                    indexes = [
                        "CREATE INDEX IF NOT EXISTS idx_billing_usage_user_month ON monthly_usage_tracking(user_email, month_year);",
                        "CREATE INDEX IF NOT EXISTS idx_billing_usage_status ON monthly_usage_tracking(current_status, last_updated);",
                        "CREATE INDEX IF NOT EXISTS idx_billing_invoices_status ON monthly_invoices(status, due_at);",
                        "CREATE INDEX IF NOT EXISTS idx_billing_audit_user ON quota_audit_log(user_email, created_at);",
                    ]

                    for index_sql in indexes:
                        cur.execute(index_sql)

                    conn.commit()
                    logger.info("✅ Tables de facturation et quotas créées")

        except Exception as e:
            logger.error(f"❌ Erreur création tables facturation: {e}")
            raise

    def _load_plan_configurations(self):
        """Charge les configurations des plans en cache"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM billing_plans WHERE active = true")
                    self.plans = {row["plan_name"]: dict(row) for row in cur.fetchall()}
                    logger.info(f"✅ {len(self.plans)} plans de facturation chargés")
        except Exception as e:
            logger.error(f"❌ Erreur chargement plans: {e}")
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
            logger.error(f"❌ Erreur vérification quota pour {user_email}: {e}")
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
            logger.error(f"❌ Erreur incrémentation usage pour {user_email}: {e}")

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
            logger.error(f"❌ Erreur update quota status: {e}")

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
                        f"✅ Nouvel utilisateur initialisé: {user_email} - Plan: {plan_name}"
                    )
        except Exception as e:
            logger.error(f"❌ Erreur initialisation utilisateur {user_email}: {e}")

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
            logger.error(f"❌ Erreur log quota action: {e}")

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
            logger.error(f"❌ Erreur génération facture pour {user_email}: {e}")
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
            logger.error(f"❌ Erreur changement plan pour {user_email}: {e}")
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
            logger.error(f"❌ Erreur billing summary pour {user_email}: {e}")
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
    """Changement de plan de facturation"""

    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="User email not found")

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
def available_plans() -> Dict[str, Any]:
    """Liste des plans disponibles - ENDPOINT PUBLIC"""
    # ✅ CORRECTION: Suppression de get_current_user = Depends(...)
    # Cet endpoint doit être accessible sans authentification

    billing = get_billing_manager()
    return {
        "plans": billing.plans,
        "currency": "EUR",
        "public": True,
        "description": "Plans de facturation disponibles",
    }


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
        logger.error(f"❌ Erreur quota middleware: {e}")
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
        logger.error(f"❌ Erreur increment quota: {e}")
