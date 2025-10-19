-- ============================================================================
-- STRIPE ADMIN TOOLS - History & Management
-- Tables et fonctions pour l'interface admin sécurisée
-- Version: 1.0
-- Created: 2025-01-19
-- ============================================================================

-- ============================================================================
-- TABLE: Historique des modifications admin (DONNÉES NON-SENSIBLES UNIQUEMENT)
-- ============================================================================

CREATE TABLE IF NOT EXISTS billing_admin_history (
    id SERIAL PRIMARY KEY,

    -- Type d'action
    action_type VARCHAR(50) NOT NULL,  -- 'price_change', 'quota_change', 'name_change', 'tier_change'
    target_entity VARCHAR(100),        -- 'CA-pro', 'essential', 'tier-3', etc.

    -- Qui a fait le changement
    admin_email VARCHAR(255) NOT NULL,
    admin_user_id VARCHAR(255),

    -- Changements (JSON non-sensible - PAS de données de paiement)
    old_value JSONB,
    new_value JSONB,

    -- Références Stripe (IDs publics uniquement)
    old_stripe_price_id VARCHAR(255),
    new_stripe_price_id VARCHAR(255),
    stripe_product_id VARCHAR(255),

    -- Contexte de la requête (audit de sécurité)
    ip_address VARCHAR(45),
    user_agent TEXT,

    -- Statut
    status VARCHAR(20) DEFAULT 'completed',  -- 'completed', 'failed', 'rolled_back'
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_admin_history_admin ON billing_admin_history(admin_email);
CREATE INDEX idx_admin_history_action ON billing_admin_history(action_type);
CREATE INDEX idx_admin_history_created ON billing_admin_history(created_at DESC);
CREATE INDEX idx_admin_history_entity ON billing_admin_history(target_entity);


-- ============================================================================
-- FONCTION: Logger une modification admin
-- ============================================================================

CREATE OR REPLACE FUNCTION log_admin_change(
    p_action_type VARCHAR,
    p_target_entity VARCHAR,
    p_admin_email VARCHAR,
    p_old_value JSONB,
    p_new_value JSONB,
    p_old_stripe_id VARCHAR DEFAULT NULL,
    p_new_stripe_id VARCHAR DEFAULT NULL,
    p_ip_address VARCHAR DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_history_id INTEGER;
BEGIN
    INSERT INTO billing_admin_history (
        action_type, target_entity, admin_email,
        old_value, new_value,
        old_stripe_price_id, new_stripe_price_id,
        ip_address, status
    ) VALUES (
        p_action_type, p_target_entity, p_admin_email,
        p_old_value, p_new_value,
        p_old_stripe_id, p_new_stripe_id,
        p_ip_address, 'completed'
    )
    RETURNING id INTO v_history_id;

    RETURN v_history_id;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- VUE: Résumé des changements récents
-- ============================================================================

CREATE OR REPLACE VIEW admin_recent_changes AS
SELECT
    h.id,
    h.action_type,
    h.target_entity,
    h.admin_email,
    h.old_value,
    h.new_value,
    h.created_at,
    h.status,
    -- Format lisible du changement
    CASE h.action_type
        WHEN 'price_change' THEN
            CONCAT(
                old_value->>'price', ' ', old_value->>'currency',
                ' → ',
                new_value->>'price', ' ', new_value->>'currency'
            )
        WHEN 'quota_change' THEN
            CONCAT(
                old_value->>'quota', ' questions',
                ' → ',
                new_value->>'quota', ' questions'
            )
        WHEN 'name_change' THEN
            CONCAT(
                '"', old_value->>'name', '"',
                ' → ',
                '"', new_value->>'name', '"'
            )
        ELSE 'Other change'
    END as change_summary
FROM billing_admin_history h
ORDER BY h.created_at DESC
LIMIT 100;


-- ============================================================================
-- FONCTION: Obtenir l'historique d'une entité spécifique
-- ============================================================================

CREATE OR REPLACE FUNCTION get_entity_history(p_entity VARCHAR)
RETURNS TABLE (
    id INTEGER,
    action_type VARCHAR,
    admin_email VARCHAR,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMP,
    change_summary TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        h.id,
        h.action_type,
        h.admin_email,
        h.old_value,
        h.new_value,
        h.created_at,
        CASE h.action_type
            WHEN 'price_change' THEN
                CONCAT(
                    h.old_value->>'price', ' ', h.old_value->>'currency',
                    ' → ',
                    h.new_value->>'price', ' ', h.new_value->>'currency'
                )
            WHEN 'quota_change' THEN
                CONCAT(
                    h.old_value->>'quota', ' → ', h.new_value->>'quota'
                )
            ELSE 'Change'
        END
    FROM billing_admin_history h
    WHERE h.target_entity = p_entity
    ORDER BY h.created_at DESC;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- TABLE: Configuration globale admin
-- ============================================================================

CREATE TABLE IF NOT EXISTS billing_admin_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,

    -- Audit
    updated_by VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Validation
    is_public BOOLEAN DEFAULT FALSE  -- Si TRUE, peut être exposé au frontend
);

-- Paramètres initiaux (sécurisés)
INSERT INTO billing_admin_settings (key, value, description, is_public) VALUES
('free_plan_default_quota', '100', 'Quota par défaut du plan gratuit (questions/mois)', FALSE),
('enable_regional_pricing', 'true', 'Activer la tarification régionale par pays', FALSE),
('auto_convert_currency', 'true', 'Convertir automatiquement les prix selon les taux de change', FALSE),
('max_quota_free_plan', '1000', 'Quota maximum autorisé pour le plan gratuit', FALSE)
ON CONFLICT (key) DO NOTHING;


-- ============================================================================
-- VUE: Statistiques admin (sécurisée)
-- ============================================================================

CREATE OR REPLACE VIEW admin_pricing_stats AS
SELECT
    -- Statistiques par plan
    pt.plan_name,
    COUNT(DISTINCT ct.country_code) as countries_count,
    COUNT(DISTINCT cp.id) as custom_prices_count,
    MIN(pt.price_usd) as min_price_usd,
    MAX(pt.price_usd) as max_price_usd,

    -- Statistiques par devise
    STRING_AGG(DISTINCT ct.currency_code, ', ' ORDER BY ct.currency_code) as currencies_used,

    -- Dernière mise à jour
    MAX(COALESCE(cp.updated_at, pt.updated_at)) as last_updated
FROM stripe_pricing_tiers pt
LEFT JOIN stripe_country_tiers ct ON TRUE
LEFT JOIN stripe_country_pricing cp ON cp.plan_name = pt.plan_name
WHERE pt.active = TRUE
GROUP BY pt.plan_name;


-- ============================================================================
-- FONCTION: Rollback d'un changement (SI POSSIBLE)
-- ============================================================================

CREATE OR REPLACE FUNCTION rollback_admin_change(p_history_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_record RECORD;
    v_success BOOLEAN := FALSE;
BEGIN
    -- Récupérer l'enregistrement
    SELECT * INTO v_record
    FROM billing_admin_history
    WHERE id = p_history_id
    AND status = 'completed';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Histoire ID % non trouvée ou déjà annulée', p_history_id;
    END IF;

    -- Rollback selon le type
    CASE v_record.action_type
        WHEN 'quota_change' THEN
            -- Restaurer l'ancien quota
            UPDATE billing_plans
            SET monthly_quota = (v_record.old_value->>'quota')::INTEGER
            WHERE plan_name = SPLIT_PART(v_record.target_entity, '-', 1);
            v_success := TRUE;

        WHEN 'name_change' THEN
            -- Restaurer l'ancien nom
            UPDATE billing_plans
            SET display_name = v_record.old_value->>'name'
            WHERE plan_name = SPLIT_PART(v_record.target_entity, '-', 1);
            v_success := TRUE;

        WHEN 'price_change' THEN
            -- Prix: ne pas rollback automatiquement (doit passer par Stripe)
            RAISE NOTICE 'Rollback de prix nécessite une action Stripe manuelle';
            v_success := FALSE;

        ELSE
            RAISE EXCEPTION 'Type de rollback non supporté: %', v_record.action_type;
    END CASE;

    -- Marquer comme rollback si succès
    IF v_success THEN
        UPDATE billing_admin_history
        SET status = 'rolled_back'
        WHERE id = p_history_id;
    END IF;

    RETURN v_success;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- COMMENTAIRES
-- ============================================================================

COMMENT ON TABLE billing_admin_history IS 'Historique sécurisé des modifications admin (ZÉRO donnée de paiement sensible)';
COMMENT ON TABLE billing_admin_settings IS 'Configuration globale du système de facturation (paramètres non-sensibles uniquement)';

COMMENT ON FUNCTION log_admin_change IS 'Enregistre une modification admin avec contexte complet';
COMMENT ON FUNCTION get_entity_history IS 'Retourne l''historique complet d''une entité (pays, plan, etc.)';
COMMENT ON FUNCTION rollback_admin_change IS 'Annule un changement si possible (sauf prix Stripe)';

COMMENT ON VIEW admin_recent_changes IS 'Vue des 100 derniers changements admin avec résumé lisible';
COMMENT ON VIEW admin_pricing_stats IS 'Statistiques de tarification par plan (sécurisé)';


-- ============================================================================
-- EXEMPLES D'UTILISATION
-- ============================================================================

-- Logger un changement de prix
-- SELECT log_admin_change(
--     'price_change',
--     'CA-pro',
--     'admin@intelia.com',
--     '{"price": 26.99, "currency": "CAD"}'::jsonb,
--     '{"price": 29.99, "currency": "CAD"}'::jsonb,
--     'price_old_xxx',
--     'price_new_xxx',
--     '192.168.1.1'
-- );

-- Logger un changement de quota
-- SELECT log_admin_change(
--     'quota_change',
--     'essential',
--     'admin@intelia.com',
--     '{"quota": 100}'::jsonb,
--     '{"quota": 200}'::jsonb
-- );

-- Voir les changements récents
-- SELECT * FROM admin_recent_changes;

-- Voir l'historique d'un pays
-- SELECT * FROM get_entity_history('CA-pro');

-- Voir les statistiques de tarification
-- SELECT * FROM admin_pricing_stats;

-- Rollback un changement (si possible)
-- SELECT rollback_admin_change(123);

-- Voir les paramètres globaux
-- SELECT * FROM billing_admin_settings WHERE is_public = FALSE;
