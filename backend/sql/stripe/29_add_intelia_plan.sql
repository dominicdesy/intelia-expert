-- ============================================================================
-- AJOUT DU PLAN INTELIA (EMPLOYÉS)
-- Plan gratuit et illimité pour les employés d'Intelia
-- Version: 1.0
-- Created: 2025-01-22
-- ============================================================================

-- Insérer le plan Intelia dans billing_plans
INSERT INTO billing_plans (
    plan_name,
    display_name_en,
    display_name_fr,
    monthly_quota,
    price_usd,
    features,
    active
) VALUES (
    'intelia',
    'Intelia Team',
    'Équipe Intelia',
    999999,  -- Quota "illimité" (999999)
    0.00,    -- Gratuit
    '{
        "unlimited_questions": true,
        "voice_realtime": true,
        "priority_support": true,
        "advanced_analytics": true,
        "api_access": true,
        "team_collaboration": true,
        "employee_only": true
    }'::jsonb,
    true
)
ON CONFLICT (plan_name)
DO UPDATE SET
    display_name_en = EXCLUDED.display_name_en,
    display_name_fr = EXCLUDED.display_name_fr,
    monthly_quota = EXCLUDED.monthly_quota,
    price_usd = EXCLUDED.price_usd,
    features = EXCLUDED.features,
    active = EXCLUDED.active,
    updated_at = CURRENT_TIMESTAMP;

-- Ajouter le plan Intelia dans les tiers de tarification (gratuit pour tous les tiers)
INSERT INTO stripe_pricing_tiers (plan_name, tier_level, price_usd, display_name, description, active) VALUES
('intelia', 1, 0.00, 'Intelia Team - Internal', 'Plan illimité pour employés Intelia', true),
('intelia', 2, 0.00, 'Intelia Team - Internal', 'Plan illimité pour employés Intelia', true),
('intelia', 3, 0.00, 'Intelia Team - Internal', 'Plan illimité pour employés Intelia', true),
('intelia', 4, 0.00, 'Intelia Team - Internal', 'Plan illimité pour employés Intelia', true)
ON CONFLICT (plan_name, tier_level)
DO UPDATE SET
    price_usd = EXCLUDED.price_usd,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    active = EXCLUDED.active,
    updated_at = CURRENT_TIMESTAMP;

-- Vérifier que le plan a été créé
SELECT
    plan_name,
    display_name_en,
    monthly_quota,
    price_usd,
    features->>'employee_only' as employee_only,
    active
FROM billing_plans
WHERE plan_name = 'intelia';

-- Note: Pour assigner le plan Intelia à un employé, utiliser:
-- UPDATE user_billing_info
-- SET plan_name = 'intelia', quota_enforcement = false
-- WHERE user_email = 'employee@intelia.com';
