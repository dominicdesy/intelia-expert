-- ============================================================================
-- STRIPE TIER-BASED PRICING MIGRATION
-- Migration du système régional vers système par tiers
-- Version: 2.0
-- Created: 2025-01-16
-- ============================================================================

-- ============================================================================
-- ÉTAPE 1: SUPPRIMER L'ANCIEN SYSTÈME (si nécessaire)
-- ============================================================================

-- Supprimer l'ancienne table de tarification régionale
DROP TABLE IF EXISTS stripe_pricing_regions CASCADE;


-- ============================================================================
-- ÉTAPE 2: NOUVEAU SYSTÈME PAR TIERS
-- ============================================================================

-- Table 1: Tiers de tarification
-- Définit les 4 niveaux de prix pour chaque plan
CREATE TABLE IF NOT EXISTS stripe_pricing_tiers (
    id SERIAL PRIMARY KEY,
    plan_name VARCHAR(50) NOT NULL,
    tier_level INTEGER NOT NULL,
    price_usd DECIMAL(10,2) NOT NULL,
    stripe_price_id VARCHAR(255),
    display_name VARCHAR(100),
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(plan_name, tier_level)
);

CREATE INDEX idx_pricing_tiers_plan_tier ON stripe_pricing_tiers(plan_name, tier_level);

-- Insertion des prix par tier
INSERT INTO stripe_pricing_tiers (plan_name, tier_level, price_usd, display_name) VALUES
-- Plan Essential (gratuit partout)
('essential', 1, 0.00, 'Essential - Free'),
('essential', 2, 0.00, 'Essential - Free'),
('essential', 3, 0.00, 'Essential - Free'),
('essential', 4, 0.00, 'Essential - Free'),

-- Plan Pro
('pro', 1, 8.99, 'Pro Tier 1 - Emerging Markets'),
('pro', 2, 10.99, 'Pro Tier 2 - Intermediate Markets'),
('pro', 3, 15.99, 'Pro Tier 3 - Developed Markets'),
('pro', 4, 19.99, 'Pro Tier 4 - Premium Markets'),

-- Plan Elite
('elite', 1, 9.99, 'Elite Tier 1 - Emerging Markets'),
('elite', 2, 15.99, 'Elite Tier 2 - Intermediate Markets'),
('elite', 3, 23.99, 'Elite Tier 3 - Developed Markets'),
('elite', 4, 31.99, 'Elite Tier 4 - Premium Markets')
ON CONFLICT (plan_name, tier_level) DO NOTHING;


-- Table 2: Mapping Pays → Tier
-- Associe chaque pays à un tier de tarification
CREATE TABLE IF NOT EXISTS stripe_country_tiers (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(2) NOT NULL UNIQUE,
    country_name VARCHAR(100),
    tier_level INTEGER NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    currency_symbol VARCHAR(5),
    active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_country_tiers_code ON stripe_country_tiers(country_code);
CREATE INDEX idx_country_tiers_tier ON stripe_country_tiers(tier_level);

-- TIER 1 - Marchés émergents (8.99$ Pro / 9.99$ Elite)
INSERT INTO stripe_country_tiers (country_code, country_name, tier_level, currency_code, currency_symbol) VALUES
('IN', 'India', 1, 'USD', '$'),
('BR', 'Brazil', 1, 'USD', '$'),
('MX', 'Mexico', 1, 'USD', '$'),
('AR', 'Argentina', 1, 'USD', '$'),
('CO', 'Colombia', 1, 'USD', '$'),
('PE', 'Peru', 1, 'USD', '$'),
('PH', 'Philippines', 1, 'USD', '$'),
('ID', 'Indonesia', 1, 'USD', '$'),
('VN', 'Vietnam', 1, 'USD', '$'),
('TH', 'Thailand', 1, 'USD', '$'),
('MY', 'Malaysia', 1, 'USD', '$'),
('PL', 'Poland', 1, 'EUR', '€'),
('RO', 'Romania', 1, 'EUR', '€'),
('BG', 'Bulgaria', 1, 'EUR', '€'),
('HR', 'Croatia', 1, 'EUR', '€'),
('RS', 'Serbia', 1, 'USD', '$'),
('UA', 'Ukraine', 1, 'USD', '$'),
('EG', 'Egypt', 1, 'USD', '$'),
('NG', 'Nigeria', 1, 'USD', '$'),
('KE', 'Kenya', 1, 'USD', '$'),
('PK', 'Pakistan', 1, 'USD', '$'),
('BD', 'Bangladesh', 1, 'USD', '$')
ON CONFLICT (country_code) DO NOTHING;

-- TIER 2 - Marchés intermédiaires (10.99$ Pro / 15.99$ Elite)
INSERT INTO stripe_country_tiers (country_code, country_name, tier_level, currency_code, currency_symbol) VALUES
('ES', 'Spain', 2, 'EUR', '€'),
('IT', 'Italy', 2, 'EUR', '€'),
('PT', 'Portugal', 2, 'EUR', '€'),
('GR', 'Greece', 2, 'EUR', '€'),
('CZ', 'Czech Republic', 2, 'EUR', '€'),
('HU', 'Hungary', 2, 'EUR', '€'),
('SK', 'Slovakia', 2, 'EUR', '€'),
('SI', 'Slovenia', 2, 'EUR', '€'),
('EE', 'Estonia', 2, 'EUR', '€'),
('LV', 'Latvia', 2, 'EUR', '€'),
('LT', 'Lithuania', 2, 'EUR', '€'),
('CL', 'Chile', 2, 'USD', '$'),
('ZA', 'South Africa', 2, 'USD', '$'),
('TR', 'Turkey', 2, 'USD', '$'),
('RU', 'Russia', 2, 'USD', '$'),
('SA', 'Saudi Arabia', 2, 'USD', '$'),
('AE', 'United Arab Emirates', 2, 'USD', '$'),
('IL', 'Israel', 2, 'USD', '$')
ON CONFLICT (country_code) DO NOTHING;

-- TIER 3 - Marchés développés (15.99$ Pro / 23.99$ Elite)
INSERT INTO stripe_country_tiers (country_code, country_name, tier_level, currency_code, currency_symbol) VALUES
('FR', 'France', 3, 'EUR', '€'),
('DE', 'Germany', 3, 'EUR', '€'),
('NL', 'Netherlands', 3, 'EUR', '€'),
('BE', 'Belgium', 3, 'EUR', '€'),
('AT', 'Austria', 3, 'EUR', '€'),
('SE', 'Sweden', 3, 'EUR', '€'),
('DK', 'Denmark', 3, 'EUR', '€'),
('FI', 'Finland', 3, 'EUR', '€'),
('JP', 'Japan', 3, 'USD', '$'),
('KR', 'South Korea', 3, 'USD', '$'),
('SG', 'Singapore', 3, 'USD', '$'),
('NZ', 'New Zealand', 3, 'USD', '$'),
('HK', 'Hong Kong', 3, 'USD', '$'),
('TW', 'Taiwan', 3, 'USD', '$')
ON CONFLICT (country_code) DO NOTHING;

-- TIER 4 - Marchés premium (19.99$ Pro / 31.99$ Elite)
INSERT INTO stripe_country_tiers (country_code, country_name, tier_level, currency_code, currency_symbol) VALUES
('US', 'United States', 4, 'USD', '$'),
('CA', 'Canada', 4, 'CAD', 'CA$'),
('GB', 'United Kingdom', 4, 'GBP', '£'),
('AU', 'Australia', 4, 'AUD', 'A$'),
('CH', 'Switzerland', 4, 'CHF', 'CHF'),
('NO', 'Norway', 4, 'NOK', 'kr'),
('LU', 'Luxembourg', 4, 'EUR', '€'),
('IE', 'Ireland', 4, 'EUR', '€'),
('IS', 'Iceland', 4, 'USD', '$'),
('QA', 'Qatar', 4, 'USD', '$'),
('KW', 'Kuwait', 4, 'USD', '$')
ON CONFLICT (country_code) DO NOTHING;


-- Table 3: Taux de conversion des devises
-- Pour afficher les prix dans la devise locale
CREATE TABLE IF NOT EXISTS stripe_currency_rates (
    id SERIAL PRIMARY KEY,
    currency_code VARCHAR(3) NOT NULL UNIQUE,
    currency_name VARCHAR(50),
    rate_to_usd DECIMAL(10,6) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Taux de conversion (à mettre à jour régulièrement)
INSERT INTO stripe_currency_rates (currency_code, currency_name, rate_to_usd) VALUES
('USD', 'US Dollar', 1.000000),
('CAD', 'Canadian Dollar', 0.740000),
('EUR', 'Euro', 1.080000),
('GBP', 'British Pound', 1.270000),
('AUD', 'Australian Dollar', 0.660000),
('CHF', 'Swiss Franc', 1.150000),
('NOK', 'Norwegian Krone', 0.095000)
ON CONFLICT (currency_code) DO UPDATE SET
    rate_to_usd = EXCLUDED.rate_to_usd,
    last_updated = CURRENT_TIMESTAMP;


-- ============================================================================
-- ÉTAPE 3: METTRE À JOUR LA TABLE stripe_subscriptions
-- ============================================================================

-- Ajouter colonne tier_level si elle n'existe pas
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'stripe_subscriptions'
        AND column_name = 'tier_level'
    ) THEN
        ALTER TABLE stripe_subscriptions
        ADD COLUMN tier_level INTEGER;
    END IF;
END $$;

-- Supprimer l'ancienne colonne region_code si elle existe
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'stripe_subscriptions'
        AND column_name = 'region_code'
    ) THEN
        ALTER TABLE stripe_subscriptions
        DROP COLUMN region_code;
    END IF;
END $$;


-- ============================================================================
-- ÉTAPE 4: FONCTIONS UTILES
-- ============================================================================

-- Fonction: Obtenir le prix pour un pays donné
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
    v_rate DECIMAL(10,6);
    v_country_name VARCHAR(100);
BEGIN
    -- Obtenir le tier et la devise du pays
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

    -- Obtenir le taux de conversion
    SELECT rate_to_usd INTO v_rate
    FROM stripe_currency_rates
    WHERE stripe_currency_rates.currency_code = v_currency_code;

    IF NOT FOUND THEN
        v_rate := 1.0;
    END IF;

    -- Retourner le prix
    RETURN QUERY
    SELECT
        pt.plan_name,
        pt.tier_level,
        pt.price_usd,
        ROUND(pt.price_usd / v_rate, 2) as price_local,
        v_currency_code,
        ct.currency_symbol,
        v_country_name,
        pt.stripe_price_id
    FROM stripe_pricing_tiers pt
    LEFT JOIN stripe_country_tiers ct ON ct.country_code = p_country_code
    WHERE pt.plan_name = p_plan_name
      AND pt.tier_level = v_tier_level
      AND pt.active = TRUE
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;


-- Fonction: Obtenir tous les prix pour un plan
CREATE OR REPLACE FUNCTION get_all_prices_for_plan(p_plan_name VARCHAR)
RETURNS TABLE (
    tier_level INTEGER,
    price_usd DECIMAL,
    display_name VARCHAR,
    countries_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pt.tier_level,
        pt.price_usd,
        pt.display_name,
        COUNT(ct.country_code) as countries_count
    FROM stripe_pricing_tiers pt
    LEFT JOIN stripe_country_tiers ct ON ct.tier_level = pt.tier_level
    WHERE pt.plan_name = p_plan_name
      AND pt.active = TRUE
    GROUP BY pt.tier_level, pt.price_usd, pt.display_name
    ORDER BY pt.tier_level;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- ÉTAPE 5: VUES UTILES
-- ============================================================================

-- Vue: Matrice complète des prix par pays
CREATE OR REPLACE VIEW pricing_matrix AS
SELECT
    ct.country_code,
    ct.country_name,
    ct.tier_level,
    pt.plan_name,
    pt.price_usd,
    ROUND(pt.price_usd / cr.rate_to_usd, 2) as price_local,
    ct.currency_code,
    ct.currency_symbol,
    CONCAT(ct.currency_symbol, ROUND(pt.price_usd / cr.rate_to_usd, 2)) as formatted_price
FROM stripe_country_tiers ct
CROSS JOIN stripe_pricing_tiers pt
JOIN stripe_currency_rates cr ON ct.currency_code = cr.currency_code
WHERE ct.tier_level = pt.tier_level
  AND ct.active = TRUE
  AND pt.active = TRUE
ORDER BY ct.tier_level, ct.country_code, pt.plan_name;


-- Vue: Résumé des tiers
CREATE OR REPLACE VIEW tier_summary AS
SELECT
    tier_level,
    COUNT(DISTINCT country_code) as countries_count,
    STRING_AGG(DISTINCT currency_code, ', ' ORDER BY currency_code) as currencies,
    MIN(country_name) as example_country
FROM stripe_country_tiers
WHERE active = TRUE
GROUP BY tier_level
ORDER BY tier_level;


-- ============================================================================
-- COMMENTAIRES
-- ============================================================================

COMMENT ON TABLE stripe_pricing_tiers IS 'Définit les 4 niveaux de prix pour chaque plan (Essential $0, Pro $8.99-$19.99, Elite $9.99-$31.99)';
COMMENT ON TABLE stripe_country_tiers IS 'Mapping pays → tier de tarification avec devise locale';
COMMENT ON TABLE stripe_currency_rates IS 'Taux de conversion des devises vers USD';

COMMENT ON FUNCTION get_price_for_country IS 'Retourne le prix adapté pour un pays donné (tier + conversion devise)';
COMMENT ON FUNCTION get_all_prices_for_plan IS 'Retourne tous les prix disponibles pour un plan donné';


-- ============================================================================
-- EXEMPLES D'UTILISATION
-- ============================================================================

-- Obtenir le prix pour la France (Tier 3)
-- SELECT * FROM get_price_for_country('pro', 'FR');
-- Résultat: 15.99 USD = 14.81 EUR

-- Obtenir le prix pour le Canada (Tier 4)
-- SELECT * FROM get_price_for_country('elite', 'CA');
-- Résultat: 31.99 USD = 43.23 CAD

-- Obtenir le prix pour l'Inde (Tier 1)
-- SELECT * FROM get_price_for_country('pro', 'IN');
-- Résultat: 8.99 USD = 8.99 USD

-- Voir tous les prix pour tous les pays
-- SELECT * FROM pricing_matrix WHERE plan_name = 'pro';

-- Voir le résumé des tiers
-- SELECT * FROM tier_summary;

-- Changer le prix du Tier 2 pour Pro
-- UPDATE stripe_pricing_tiers SET price_usd = 11.99 WHERE plan_name = 'pro' AND tier_level = 2;

-- Déplacer la France du Tier 3 au Tier 2
-- UPDATE stripe_country_tiers SET tier_level = 2 WHERE country_code = 'FR';

-- Mettre à jour les taux de change
-- UPDATE stripe_currency_rates SET rate_to_usd = 0.75, last_updated = NOW() WHERE currency_code = 'CAD';

-- Ajouter un nouveau pays
-- INSERT INTO stripe_country_tiers (country_code, country_name, tier_level, currency_code, currency_symbol)
-- VALUES ('XX', 'New Country', 2, 'USD', '$');
