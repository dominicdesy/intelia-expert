-- ============================================================================
-- STRIPE SUBSCRIPTION MANAGEMENT TABLES
-- Support for regional pricing (Essential $0, Pro $18, Elite $28)
-- Version: 1.0
-- Created: 2025-01-16
-- ============================================================================

-- Table: stripe_customers
-- Lien entre utilisateurs Intelia et Stripe Customer IDs
CREATE TABLE IF NOT EXISTS stripe_customers (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(255) UNIQUE NOT NULL,

    customer_name VARCHAR(255),
    country_code VARCHAR(2),
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour recherches rapides
CREATE INDEX IF NOT EXISTS idx_stripe_customers_email ON stripe_customers(user_email);
CREATE INDEX IF NOT EXISTS idx_stripe_customers_stripe_id ON stripe_customers(stripe_customer_id);


-- Table: stripe_pricing_regions
-- Configuration des prix par région pour chaque plan
CREATE TABLE IF NOT EXISTS stripe_pricing_regions (
    id SERIAL PRIMARY KEY,

    -- Plan et région
    plan_name VARCHAR(50) NOT NULL, -- essential, pro, elite
    region_code VARCHAR(10) NOT NULL, -- US, CA, EU, UK, ROW (Rest of World)

    -- Tarification
    price_monthly DECIMAL(10,2) NOT NULL, -- Prix mensuel dans la devise
    currency VARCHAR(3) NOT NULL, -- USD, CAD, EUR, GBP

    -- Stripe Price ID (créé dans Stripe Dashboard)
    stripe_price_id VARCHAR(255), -- price_xxxxx from Stripe

    -- Métadonnées
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Contrainte unique: un seul prix par plan/région
    UNIQUE(plan_name, region_code)
);

-- Insérer les prix par défaut (USD - États-Unis)
INSERT INTO stripe_pricing_regions (plan_name, region_code, price_monthly, currency, active)
VALUES
    ('essential', 'US', 0.00, 'USD', TRUE),
    ('pro', 'US', 18.00, 'USD', TRUE),
    ('elite', 'US', 28.00, 'USD', TRUE)
ON CONFLICT (plan_name, region_code) DO NOTHING;

-- Prix Canada (CAD) - Exemple avec conversion ~1.35x
INSERT INTO stripe_pricing_regions (plan_name, region_code, price_monthly, currency, active)
VALUES
    ('essential', 'CA', 0.00, 'CAD', TRUE),
    ('pro', 'CA', 24.00, 'CAD', TRUE),
    ('elite', 'CA', 38.00, 'CAD', TRUE)
ON CONFLICT (plan_name, region_code) DO NOTHING;

-- Prix Europe (EUR) - Exemple avec conversion ~0.92x
INSERT INTO stripe_pricing_regions (plan_name, region_code, price_monthly, currency, active)
VALUES
    ('essential', 'EU', 0.00, 'EUR', TRUE),
    ('pro', 'EU', 17.00, 'EUR', TRUE),
    ('elite', 'EU', 26.00, 'EUR', TRUE)
ON CONFLICT (plan_name, region_code) DO NOTHING;

-- Index pour recherches rapides
CREATE INDEX IF NOT EXISTS idx_pricing_regions_plan ON stripe_pricing_regions(plan_name, region_code);


-- Table: stripe_subscriptions
-- Abonnements actifs synchronisés avec Stripe
CREATE TABLE IF NOT EXISTS stripe_subscriptions (
    id SERIAL PRIMARY KEY,

    -- Identifiants
    user_email VARCHAR(255) NOT NULL,
    stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(255) NOT NULL,

    -- Plan et tarification
    plan_name VARCHAR(50) NOT NULL, -- essential, pro, elite
    region_code VARCHAR(10), -- US, CA, EU, etc.
    price_monthly DECIMAL(10,2), -- Prix payé
    currency VARCHAR(3) DEFAULT 'USD',

    -- Statut Stripe
    status VARCHAR(50) NOT NULL,
    -- active, past_due, canceled, unpaid, trialing, incomplete, incomplete_expired

    -- Périodes de facturation
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    trial_end TIMESTAMP,

    -- Flags
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMP,
    ended_at TIMESTAMP,

    -- Métadonnées Stripe
    stripe_metadata JSONB DEFAULT '{}',

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign keys
    CONSTRAINT fk_subscription_user FOREIGN KEY (user_email)
        REFERENCES user_billing_info(user_email) ON DELETE CASCADE,
    CONSTRAINT fk_subscription_customer FOREIGN KEY (stripe_customer_id)
        REFERENCES stripe_customers(stripe_customer_id) ON DELETE CASCADE
);

-- Index pour recherches rapides
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON stripe_subscriptions(user_email);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_id ON stripe_subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON stripe_subscriptions(status, user_email);


-- Table: stripe_payment_events
-- Audit log de tous les événements de paiement Stripe
CREATE TABLE IF NOT EXISTS stripe_payment_events (
    id SERIAL PRIMARY KEY,

    -- Identifiants Stripe
    stripe_event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    -- checkout.session.completed, invoice.paid, customer.subscription.created, etc.

    -- Données utilisateur
    user_email VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),

    -- Montants
    amount DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',

    -- Statut
    status VARCHAR(50), -- succeeded, failed, pending, etc.

    -- Payload complet de l'événement (pour debugging)
    event_payload JSONB DEFAULT '{}',

    -- Traitement
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    error_message TEXT,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Index
    CONSTRAINT unique_stripe_event UNIQUE(stripe_event_id)
);

-- Index pour recherches rapides
CREATE INDEX IF NOT EXISTS idx_payment_events_user ON stripe_payment_events(user_email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payment_events_type ON stripe_payment_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payment_events_processed ON stripe_payment_events(processed, created_at);


-- Table: stripe_webhook_logs
-- Log de tous les webhooks reçus de Stripe (sécurité et debugging)
CREATE TABLE IF NOT EXISTS stripe_webhook_logs (
    id SERIAL PRIMARY KEY,

    -- Webhook signature verification
    signature_verified BOOLEAN DEFAULT FALSE,
    signature_header VARCHAR(500),

    -- Event details
    stripe_event_id VARCHAR(255),
    event_type VARCHAR(100),

    -- Raw payload
    raw_payload JSONB,

    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'pending', -- pending, success, failed
    processing_error TEXT,

    -- Timestamps
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Index pour debugging
CREATE INDEX IF NOT EXISTS idx_webhook_logs_event_id ON stripe_webhook_logs(stripe_event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_received ON stripe_webhook_logs(received_at DESC);


-- ============================================================================
-- VIEWS UTILES
-- ============================================================================

-- Vue: active_subscriptions
-- Liste des abonnements actifs avec toutes les infos
CREATE OR REPLACE VIEW active_subscriptions AS
SELECT
    ss.user_email,
    ss.plan_name,
    ss.status,
    ss.price_monthly,
    ss.currency,
    ss.current_period_start,
    ss.current_period_end,
    ss.cancel_at_period_end,
    sc.stripe_customer_id,
    sc.country_code,
    ubi.billing_enabled,
    ubi.quota_enforcement
FROM stripe_subscriptions ss
JOIN stripe_customers sc ON ss.stripe_customer_id = sc.stripe_customer_id
LEFT JOIN user_billing_info ubi ON ss.user_email = ubi.user_email
WHERE ss.status IN ('active', 'trialing');


-- Vue: subscription_revenue_summary
-- Résumé des revenus par plan
CREATE OR REPLACE VIEW subscription_revenue_summary AS
SELECT
    plan_name,
    currency,
    COUNT(*) as active_subscribers,
    SUM(price_monthly) as monthly_revenue,
    AVG(price_monthly) as avg_price
FROM stripe_subscriptions
WHERE status = 'active'
GROUP BY plan_name, currency
ORDER BY monthly_revenue DESC;


-- ============================================================================
-- FONCTIONS UTILES
-- ============================================================================

-- Fonction: get_user_subscription_status
-- Retourne le statut d'abonnement d'un utilisateur
CREATE OR REPLACE FUNCTION get_user_subscription_status(p_user_email VARCHAR)
RETURNS TABLE (
    plan_name VARCHAR,
    status VARCHAR,
    is_active BOOLEAN,
    expires_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ss.plan_name,
        ss.status,
        (ss.status IN ('active', 'trialing')) as is_active,
        ss.current_period_end as expires_at
    FROM stripe_subscriptions ss
    WHERE ss.user_email = p_user_email
    ORDER BY ss.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;


-- Fonction: get_regional_pricing
-- Retourne le prix d'un plan pour une région donnée
CREATE OR REPLACE FUNCTION get_regional_pricing(
    p_plan_name VARCHAR,
    p_country_code VARCHAR DEFAULT 'US'
)
RETURNS TABLE (
    plan_name VARCHAR,
    price DECIMAL,
    currency VARCHAR,
    stripe_price_id VARCHAR
) AS $$
DECLARE
    v_region_code VARCHAR(10);
BEGIN
    -- Mapping pays → région
    v_region_code := CASE
        WHEN p_country_code IN ('US', 'USA') THEN 'US'
        WHEN p_country_code IN ('CA', 'CAN') THEN 'CA'
        WHEN p_country_code IN ('FR', 'DE', 'IT', 'ES', 'NL', 'BE') THEN 'EU'
        WHEN p_country_code IN ('GB', 'UK') THEN 'UK'
        ELSE 'US' -- Default: prix US
    END;

    RETURN QUERY
    SELECT
        spr.plan_name,
        spr.price_monthly,
        spr.currency,
        spr.stripe_price_id
    FROM stripe_pricing_regions spr
    WHERE spr.plan_name = p_plan_name
      AND spr.region_code = v_region_code
      AND spr.active = TRUE
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- PERMISSIONS (à adapter selon votre setup)
-- ============================================================================

-- Accorder permissions à l'utilisateur backend (si nécessaire)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_backend_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_backend_user;


-- ============================================================================
-- COMMENTAIRES
-- ============================================================================

COMMENT ON TABLE stripe_customers IS 'Lien entre utilisateurs Intelia et Stripe Customer IDs';
COMMENT ON TABLE stripe_pricing_regions IS 'Configuration des prix par région (Essential $0, Pro $18, Elite $28)';
COMMENT ON TABLE stripe_subscriptions IS 'Abonnements actifs synchronisés avec Stripe';
COMMENT ON TABLE stripe_payment_events IS 'Audit log de tous les événements de paiement Stripe';
COMMENT ON TABLE stripe_webhook_logs IS 'Log de tous les webhooks reçus de Stripe';

COMMENT ON FUNCTION get_user_subscription_status IS 'Retourne le statut d''abonnement actuel d''un utilisateur';
COMMENT ON FUNCTION get_regional_pricing IS 'Retourne le prix d''un plan adapté à la région de l''utilisateur';
