-- ============================================================================
-- STRIPE COUNTRY-SPECIFIC PRICING
-- Gestion des prix arrondis et localisés par pays pour le marketing
-- Version: 2.1
-- Created: 2025-01-16
-- ============================================================================

-- Cette migration ajoute une table pour des prix personnalisés par pays
-- Cela permet d'arrondir les prix de manière marketing-friendly
-- Ex: Au lieu de 14.81 EUR (conversion automatique), afficher 14.99 EUR

-- ============================================================================
-- TABLE: Prix spécifiques par pays
-- ============================================================================

CREATE TABLE IF NOT EXISTS stripe_country_pricing (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(2) NOT NULL,
    plan_name VARCHAR(50) NOT NULL,

    -- Prix affiché (arrondi pour le marketing)
    display_price DECIMAL(10,2) NOT NULL,
    display_currency VARCHAR(3) NOT NULL,
    display_currency_symbol VARCHAR(5),

    -- Prix réel facturé (peut être différent pour arrondir)
    charge_price DECIMAL(10,2),
    charge_currency VARCHAR(3),

    -- Stripe Price ID (créé dans Stripe Dashboard pour ce pays/plan)
    stripe_price_id VARCHAR(255),

    -- Métadonnées
    active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(country_code, plan_name)
);

CREATE INDEX idx_country_pricing_lookup ON stripe_country_pricing(country_code, plan_name, active);


-- ============================================================================
-- INSERTION: Prix arrondis par pays (exemples)
-- ============================================================================

-- ÉTATS-UNIS (Tier 4 - USD)
INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol, charge_price, charge_currency) VALUES
('US', 'essential', 0.00, 'USD', '$', 0.00, 'USD'),
('US', 'pro', 19.99, 'USD', '$', 19.99, 'USD'),
('US', 'elite', 31.99, 'USD', '$', 31.99, 'USD')
ON CONFLICT (country_code, plan_name) DO NOTHING;

-- CANADA (Tier 4 - CAD)
-- Conversion: 19.99 USD = 27.01 CAD → Arrondi à 26.99 CAD
-- Conversion: 31.99 USD = 43.23 CAD → Arrondi à 42.99 CAD
INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol, charge_price, charge_currency) VALUES
('CA', 'essential', 0.00, 'CAD', 'CA$', 0.00, 'CAD'),
('CA', 'pro', 26.99, 'CAD', 'CA$', 26.99, 'CAD'),
('CA', 'elite', 42.99, 'CAD', 'CA$', 42.99, 'CAD')
ON CONFLICT (country_code, plan_name) DO NOTHING;

-- FRANCE (Tier 3 - EUR)
-- Conversion: 15.99 USD = 14.81 EUR → Arrondi à 14.99 EUR
-- Conversion: 23.99 USD = 22.21 EUR → Arrondi à 22.99 EUR
INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol, charge_price, charge_currency) VALUES
('FR', 'essential', 0.00, 'EUR', '€', 0.00, 'EUR'),
('FR', 'pro', 14.99, 'EUR', '€', 14.99, 'EUR'),
('FR', 'elite', 22.99, 'EUR', '€', 22.99, 'EUR')
ON CONFLICT (country_code, plan_name) DO NOTHING;

-- ALLEMAGNE (Tier 3 - EUR)
INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol, charge_price, charge_currency) VALUES
('DE', 'essential', 0.00, 'EUR', '€', 0.00, 'EUR'),
('DE', 'pro', 14.99, 'EUR', '€', 14.99, 'EUR'),
('DE', 'elite', 22.99, 'EUR', '€', 22.99, 'EUR')
ON CONFLICT (country_code, plan_name) DO NOTHING;

-- ROYAUME-UNI (Tier 4 - GBP)
-- Conversion: 19.99 USD = 15.74 GBP → Arrondi à 15.99 GBP
-- Conversion: 31.99 USD = 25.19 GBP → Arrondi à 24.99 GBP
INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol, charge_price, charge_currency) VALUES
('GB', 'essential', 0.00, 'GBP', '£', 0.00, 'GBP'),
('GB', 'pro', 15.99, 'GBP', '£', 15.99, 'GBP'),
('GB', 'elite', 24.99, 'GBP', '£', 24.99, 'GBP')
ON CONFLICT (country_code, plan_name) DO NOTHING;

-- ESPAGNE (Tier 2 - EUR)
-- Conversion: 10.99 USD = 10.18 EUR → Arrondi à 9.99 EUR
-- Conversion: 15.99 USD = 14.81 EUR → Arrondi à 14.99 EUR
INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol, charge_price, charge_currency) VALUES
('ES', 'essential', 0.00, 'EUR', '€', 0.00, 'EUR'),
('ES', 'pro', 9.99, 'EUR', '€', 9.99, 'EUR'),
('ES', 'elite', 14.99, 'EUR', '€', 14.99, 'EUR')
ON CONFLICT (country_code, plan_name) DO NOTHING;

-- INDE (Tier 1 - USD)
INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol, charge_price, charge_currency) VALUES
('IN', 'essential', 0.00, 'USD', '$', 0.00, 'USD'),
('IN', 'pro', 8.99, 'USD', '$', 8.99, 'USD'),
('IN', 'elite', 9.99, 'USD', '$', 9.99, 'USD')
ON CONFLICT (country_code, plan_name) DO NOTHING;


-- ============================================================================
-- FONCTION: Obtenir le prix pour un pays (VERSION AMÉLIORÉE)
-- ============================================================================

-- Remplacer la fonction précédente pour utiliser d'abord country_pricing
CREATE OR REPLACE FUNCTION get_price_for_country(
    p_plan_name VARCHAR,
    p_country_code VARCHAR DEFAULT 'US'
)
RETURNS TABLE (
    plan_name VARCHAR,
    tier_level INTEGER,
    price_usd DECIMAL,
    price_local DECIMAL,
    currency_code VARCHAR,
    currency_symbol VARCHAR,
    country_name VARCHAR,
    stripe_price_id VARCHAR
) AS $$
DECLARE
    v_tier_level INTEGER;
    v_currency_code VARCHAR(3);
    v_country_name VARCHAR(100);
BEGIN
    -- PRIORITÉ 1: Prix spécifique défini pour ce pays
    IF EXISTS (
        SELECT 1 FROM stripe_country_pricing
        WHERE country_code = p_country_code
        AND stripe_country_pricing.plan_name = p_plan_name
        AND active = TRUE
    ) THEN
        -- Utiliser le prix personnalisé
        RETURN QUERY
        SELECT
            cp.plan_name,
            ct.tier_level,
            pt.price_usd, -- Prix USD de référence du tier
            cp.display_price as price_local, -- Prix local arrondi
            cp.display_currency,
            cp.display_currency_symbol,
            ct.country_name,
            cp.stripe_price_id
        FROM stripe_country_pricing cp
        JOIN stripe_country_tiers ct ON ct.country_code = cp.country_code
        JOIN stripe_pricing_tiers pt ON pt.plan_name = cp.plan_name AND pt.tier_level = ct.tier_level
        WHERE cp.country_code = p_country_code
          AND cp.plan_name = p_plan_name
          AND cp.active = TRUE
        LIMIT 1;

        RETURN;
    END IF;

    -- PRIORITÉ 2: Calculer depuis tier + conversion automatique
    SELECT ct.tier_level, ct.currency_code, ct.country_name
    INTO v_tier_level, v_currency_code, v_country_name
    FROM stripe_country_tiers ct
    WHERE ct.country_code = p_country_code AND ct.active = TRUE;

    -- Si pays non trouvé, utiliser Tier 4 (USA) par défaut
    IF NOT FOUND THEN
        v_tier_level := 4;
        v_currency_code := 'USD';
        v_country_name := 'Unknown';
    END IF;

    -- Retourner le prix calculé avec conversion automatique
    RETURN QUERY
    SELECT
        pt.plan_name,
        pt.tier_level,
        pt.price_usd,
        ROUND(pt.price_usd / COALESCE(cr.rate_to_usd, 1.0), 2) as price_local,
        v_currency_code,
        ct.currency_symbol,
        v_country_name,
        pt.stripe_price_id
    FROM stripe_pricing_tiers pt
    LEFT JOIN stripe_country_tiers ct ON ct.country_code = p_country_code
    LEFT JOIN stripe_currency_rates cr ON cr.currency_code = v_currency_code
    WHERE pt.plan_name = p_plan_name
      AND pt.tier_level = v_tier_level
      AND pt.active = TRUE
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- VUE: Matrice complète avec prix personnalisés
-- ============================================================================

CREATE OR REPLACE VIEW complete_pricing_matrix AS
SELECT
    ct.country_code,
    ct.country_name,
    ct.tier_level,
    pt.plan_name,
    pt.price_usd as tier_price_usd,

    -- Utiliser prix personnalisé si disponible, sinon conversion auto
    COALESCE(cp.display_price, ROUND(pt.price_usd / cr.rate_to_usd, 2)) as display_price,
    COALESCE(cp.display_currency, ct.currency_code) as display_currency,
    COALESCE(cp.display_currency_symbol, ct.currency_symbol) as display_symbol,

    -- Indicateur: prix personnalisé ou calculé
    CASE WHEN cp.id IS NOT NULL THEN 'custom' ELSE 'calculated' END as price_type,

    cp.stripe_price_id,
    cp.notes
FROM stripe_country_tiers ct
CROSS JOIN stripe_pricing_tiers pt
JOIN stripe_currency_rates cr ON ct.currency_code = cr.currency_code
LEFT JOIN stripe_country_pricing cp ON cp.country_code = ct.country_code AND cp.plan_name = pt.plan_name AND cp.active = TRUE
WHERE ct.tier_level = pt.tier_level
  AND ct.active = TRUE
  AND pt.active = TRUE
ORDER BY ct.tier_level, ct.country_code, pt.plan_name;


-- ============================================================================
-- FONCTIONS UTILITAIRES
-- ============================================================================

-- Fonction: Générer les prix arrondis pour tous les pays manquants
CREATE OR REPLACE FUNCTION generate_rounded_prices()
RETURNS TABLE (
    country_code VARCHAR,
    plan_name VARCHAR,
    suggested_price DECIMAL,
    currency VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ct.country_code,
        pt.plan_name,
        -- Arrondir à .99 (ex: 14.81 → 14.99, 22.21 → 22.99)
        FLOOR(pt.price_usd / cr.rate_to_usd) + 0.99 as suggested_price,
        ct.currency_code
    FROM stripe_country_tiers ct
    CROSS JOIN stripe_pricing_tiers pt
    JOIN stripe_currency_rates cr ON ct.currency_code = cr.currency_code
    WHERE ct.tier_level = pt.tier_level
      AND ct.active = TRUE
      AND pt.active = TRUE
      AND NOT EXISTS (
          SELECT 1 FROM stripe_country_pricing cp
          WHERE cp.country_code = ct.country_code
          AND cp.plan_name = pt.plan_name
      )
    ORDER BY ct.country_code, pt.plan_name;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- COMMENTAIRES
-- ============================================================================

COMMENT ON TABLE stripe_country_pricing IS 'Prix personnalisés et arrondis par pays pour le marketing (ex: 14.99€ au lieu de 14.81€)';
COMMENT ON FUNCTION get_price_for_country IS 'Retourne le prix pour un pays (priorité: prix personnalisé > calcul automatique)';
COMMENT ON VIEW complete_pricing_matrix IS 'Matrice complète montrant prix personnalisés vs calculés pour chaque pays';


-- ============================================================================
-- EXEMPLES D'UTILISATION
-- ============================================================================

-- Obtenir le prix pour la France (utilisera le prix personnalisé 14.99€)
-- SELECT * FROM get_price_for_country('pro', 'FR');

-- Voir tous les prix (personnalisés + calculés)
-- SELECT * FROM complete_pricing_matrix WHERE plan_name = 'pro';

-- Voir les pays qui n'ont pas de prix personnalisés
-- SELECT * FROM generate_rounded_prices();

-- Ajouter un prix personnalisé pour l'Italie
-- INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol)
-- VALUES ('IT', 'pro', 9.99, 'EUR', '€');

-- Mettre à jour le prix pour le Canada
-- UPDATE stripe_country_pricing
-- SET display_price = 27.99, updated_at = CURRENT_TIMESTAMP
-- WHERE country_code = 'CA' AND plan_name = 'pro';

-- Désactiver un prix personnalisé (retombera sur calcul automatique)
-- UPDATE stripe_country_pricing SET active = FALSE WHERE country_code = 'ES' AND plan_name = 'pro';
