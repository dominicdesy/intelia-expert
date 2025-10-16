-- ============================================================================
-- MIGRATION: Ajout des limites de questions pour le plan Essential
-- Date: 2025-01-16
-- Description: Configure le quota mensuel de 50 questions pour Essential
-- ============================================================================

-- Mise à jour de la table billing_plans pour le plan Essential
UPDATE billing_plans
SET monthly_quota = 50
WHERE plan_name = 'essential';

-- Si le plan n'existe pas encore, l'insérer
INSERT INTO billing_plans (plan_name, display_name, monthly_quota, price_per_month, active)
VALUES ('essential', 'Essential', 50, 0.00, TRUE)
ON CONFLICT (plan_name) DO UPDATE
SET monthly_quota = 50;

-- Vérifier que tous les utilisateurs Essential ont un enregistrement dans monthly_usage_tracking
-- Créer les enregistrements manquants pour le mois en cours
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
    TO_CHAR(CURRENT_DATE, 'YYYY-MM') as month_year,
    0 as questions_used,
    0 as questions_successful,
    0 as questions_failed,
    0.00 as total_cost_usd,
    0.00 as openai_cost_usd,
    50 as monthly_quota,
    'active' as current_status,
    FALSE as warning_sent,
    0 as limit_notifications_sent,
    CURRENT_TIMESTAMP as last_updated
FROM user_billing_info ubi
WHERE ubi.plan_name = 'essential'
  AND NOT EXISTS (
      SELECT 1
      FROM monthly_usage_tracking mut
      WHERE mut.user_email = ubi.user_email
        AND mut.month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
  );

-- Activer l'enforcement des quotas pour tous les utilisateurs Essential
UPDATE user_billing_info
SET quota_enforcement = TRUE
WHERE plan_name = 'essential';

-- Créer un index pour optimiser les requêtes de vérification de quota
CREATE INDEX IF NOT EXISTS idx_monthly_usage_email_month
ON monthly_usage_tracking(user_email, month_year);

CREATE INDEX IF NOT EXISTS idx_monthly_usage_status
ON monthly_usage_tracking(user_email, current_status)
WHERE current_status = 'active';

-- Commentaires pour documentation
COMMENT ON COLUMN billing_plans.monthly_quota IS 'Nombre maximum de questions par mois (Essential: 50, Pro: illimité, Elite: illimité)';
COMMENT ON COLUMN monthly_usage_tracking.monthly_quota IS 'Quota mensuel copié depuis billing_plans au moment de la création';
COMMENT ON COLUMN user_billing_info.quota_enforcement IS 'Si TRUE, le système bloque les questions au-delà du quota';

-- Afficher le résultat
SELECT
    plan_name,
    display_name,
    monthly_quota,
    price_per_month,
    active
FROM billing_plans
ORDER BY price_per_month;
