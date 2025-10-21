-- ============================================================================
-- COUNTRY TRACKING & FRAUD DETECTION SYSTEM
-- Track user's country at signup and every login for fraud detection
-- ============================================================================

-- ============================================================================
-- 1. Add country tracking columns to user_billing_info
-- ============================================================================

ALTER TABLE user_billing_info
    ADD COLUMN IF NOT EXISTS signup_country VARCHAR(2),
    ADD COLUMN IF NOT EXISTS signup_ip VARCHAR(45),
    ADD COLUMN IF NOT EXISTS signup_detected_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS pricing_tier VARCHAR(20) DEFAULT 'tier1',
    ADD COLUMN IF NOT EXISTS pricing_country VARCHAR(2),
    ADD COLUMN IF NOT EXISTS pricing_locked_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_login_country VARCHAR(2),
    ADD COLUMN IF NOT EXISTS last_login_ip VARCHAR(45),
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_billing_signup_country
    ON user_billing_info(signup_country);

CREATE INDEX IF NOT EXISTS idx_user_billing_pricing_tier
    ON user_billing_info(pricing_tier);

-- Add comments
COMMENT ON COLUMN user_billing_info.signup_country IS
    'Country detected at user signup (ISO 3166-1 alpha-2). Locked and never changed. Used for fraud detection.';

COMMENT ON COLUMN user_billing_info.pricing_tier IS
    'Pricing tier based on country economic level: tier1 ($18), tier2 ($12), tier3 ($5). Locked at first payment.';

COMMENT ON COLUMN user_billing_info.pricing_country IS
    'Country used to determine pricing tier. Locked at first subscription. Validates against signup_country and login history.';


-- ============================================================================
-- 2. Create user_login_history table for tracking all logins
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_login_history (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,

    -- Login details
    login_at TIMESTAMP NOT NULL DEFAULT NOW(),
    login_method VARCHAR(50),                           -- 'password', 'oauth_linkedin', 'oauth_facebook', 'webauthn'

    -- Geo-location data
    ip_address VARCHAR(45),                             -- IPv4 or IPv6
    country_code VARCHAR(2),                            -- ISO 3166-1 alpha-2
    city VARCHAR(100),
    region VARCHAR(100),

    -- Device & Browser info
    user_agent TEXT,
    device_type VARCHAR(50),                            -- 'desktop', 'mobile', 'tablet'
    browser VARCHAR(100),
    os VARCHAR(100),

    -- Fraud detection flags
    is_vpn BOOLEAN DEFAULT FALSE,
    is_proxy BOOLEAN DEFAULT FALSE,
    is_tor BOOLEAN DEFAULT FALSE,
    risk_score INTEGER DEFAULT 0,                       -- 0-100, higher = more risky

    -- Session info
    session_id VARCHAR(255),

    CONSTRAINT fk_user_login_user_email
        FOREIGN KEY (user_email)
        REFERENCES auth.users(email)
        ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_login_history_user_email
    ON user_login_history(user_email);

CREATE INDEX IF NOT EXISTS idx_login_history_login_at
    ON user_login_history(login_at DESC);

CREATE INDEX IF NOT EXISTS idx_login_history_country
    ON user_login_history(country_code);

CREATE INDEX IF NOT EXISTS idx_login_history_risk
    ON user_login_history(risk_score DESC)
    WHERE risk_score > 50;

-- Composite index for user analysis
CREATE INDEX IF NOT EXISTS idx_login_history_user_country_date
    ON user_login_history(user_email, country_code, login_at DESC);

COMMENT ON TABLE user_login_history IS
    'Logs every user login with geo-location and device info for fraud detection and analytics.';


-- ============================================================================
-- 3. Create pricing_tiers reference table
-- ============================================================================

CREATE TABLE IF NOT EXISTS pricing_tiers (
    country_code VARCHAR(2) PRIMARY KEY,
    tier VARCHAR(20) NOT NULL,                          -- tier1, tier2, tier3
    base_price_usd DECIMAL(10,2) NOT NULL,
    ppp_multiplier DECIMAL(4,2) DEFAULT 1.00,          -- Purchasing Power Parity adjustment
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE pricing_tiers IS
    'Defines pricing tier for each country based on economic level and purchasing power parity.';

-- Insert pricing tiers for all major countries
-- Tier 1: High-income countries ($18/month)
INSERT INTO pricing_tiers (country_code, tier, base_price_usd, ppp_multiplier) VALUES
    -- North America
    ('US', 'tier1', 18.00, 1.00),
    ('CA', 'tier1', 18.00, 1.05),

    -- Western Europe
    ('FR', 'tier1', 18.00, 0.95),
    ('DE', 'tier1', 18.00, 0.93),
    ('ES', 'tier1', 18.00, 0.88),
    ('IT', 'tier1', 18.00, 0.90),
    ('NL', 'tier1', 18.00, 0.96),
    ('BE', 'tier1', 18.00, 0.94),
    ('AT', 'tier1', 18.00, 0.94),
    ('GB', 'tier1', 18.00, 0.92),
    ('IE', 'tier1', 18.00, 0.98),
    ('CH', 'tier1', 18.00, 1.15),
    ('NO', 'tier1', 18.00, 1.12),
    ('SE', 'tier1', 18.00, 1.08),
    ('DK', 'tier1', 18.00, 1.10),
    ('FI', 'tier1', 18.00, 1.02),

    -- Oceania
    ('AU', 'tier1', 18.00, 1.03),
    ('NZ', 'tier1', 18.00, 1.01),

    -- Asia (High-income)
    ('JP', 'tier1', 18.00, 0.85),
    ('KR', 'tier1', 18.00, 0.78),
    ('SG', 'tier1', 18.00, 0.88)
ON CONFLICT (country_code) DO NOTHING;

-- Tier 2: Middle-income countries ($12/month)
INSERT INTO pricing_tiers (country_code, tier, base_price_usd, ppp_multiplier) VALUES
    -- Latin America
    ('MX', 'tier2', 12.00, 0.55),
    ('BR', 'tier2', 12.00, 0.48),
    ('AR', 'tier2', 12.00, 0.42),
    ('CL', 'tier2', 12.00, 0.60),
    ('CO', 'tier2', 12.00, 0.45),
    ('PE', 'tier2', 12.00, 0.43),

    -- Eastern Europe
    ('PL', 'tier2', 12.00, 0.62),
    ('CZ', 'tier2', 12.00, 0.70),
    ('HU', 'tier2', 12.00, 0.65),
    ('RO', 'tier2', 12.00, 0.55),

    -- Asia (Middle-income)
    ('CN', 'tier2', 12.00, 0.52),
    ('MY', 'tier2', 12.00, 0.48),
    ('TR', 'tier2', 12.00, 0.50),

    -- Middle East
    ('SA', 'tier2', 12.00, 0.65),
    ('AE', 'tier2', 12.00, 0.75)
ON CONFLICT (country_code) DO NOTHING;

-- Tier 3: Low-income countries ($5/month)
INSERT INTO pricing_tiers (country_code, tier, base_price_usd, ppp_multiplier) VALUES
    -- South Asia
    ('IN', 'tier3', 5.00, 0.25),
    ('PK', 'tier3', 5.00, 0.22),
    ('BD', 'tier3', 5.00, 0.20),
    ('LK', 'tier3', 5.00, 0.28),

    -- Southeast Asia
    ('TH', 'tier3', 5.00, 0.35),
    ('VN', 'tier3', 5.00, 0.28),
    ('ID', 'tier3', 5.00, 0.32),
    ('PH', 'tier3', 5.00, 0.30),

    -- Africa
    ('ZA', 'tier3', 5.00, 0.38),
    ('NG', 'tier3', 5.00, 0.25),
    ('KE', 'tier3', 5.00, 0.28),
    ('EG', 'tier3', 5.00, 0.30)
ON CONFLICT (country_code) DO NOTHING;


-- ============================================================================
-- 4. Create fraud detection view
-- ============================================================================

CREATE OR REPLACE VIEW user_fraud_risk_analysis AS
SELECT
    ubi.user_email,
    ubi.signup_country,
    ubi.pricing_country,
    ubi.pricing_tier,

    -- Login country diversity
    COUNT(DISTINCT ulh.country_code) as unique_login_countries,

    -- Most common login country
    MODE() WITHIN GROUP (ORDER BY ulh.country_code) as most_common_login_country,

    -- Suspicious: signup country != pricing country
    CASE
        WHEN ubi.signup_country != ubi.pricing_country THEN TRUE
        ELSE FALSE
    END as country_mismatch,

    -- Suspicious: VPN usage
    SUM(CASE WHEN ulh.is_vpn THEN 1 ELSE 0 END) as vpn_login_count,

    -- Suspicious: Multiple countries in short time
    CASE
        WHEN COUNT(DISTINCT ulh.country_code) FILTER (
            WHERE ulh.login_at > NOW() - INTERVAL '7 days'
        ) > 3 THEN TRUE
        ELSE FALSE
    END as rapid_country_switching,

    -- Risk score (0-100)
    LEAST(100,
        (COUNT(DISTINCT ulh.country_code) * 10) +
        (SUM(CASE WHEN ulh.is_vpn THEN 1 ELSE 0 END) * 15) +
        (CASE WHEN ubi.signup_country != ubi.pricing_country THEN 30 ELSE 0 END)
    ) as calculated_risk_score,

    -- Latest login info
    MAX(ulh.login_at) as last_login,
    MAX(ulh.country_code) as last_login_country

FROM user_billing_info ubi
LEFT JOIN user_login_history ulh ON ubi.user_email = ulh.user_email
WHERE ubi.pricing_tier IS NOT NULL
GROUP BY ubi.user_email, ubi.signup_country, ubi.pricing_country, ubi.pricing_tier;

COMMENT ON VIEW user_fraud_risk_analysis IS
    'Analyzes user login patterns to detect potential pricing fraud (e.g., VPN to get lower prices).';


-- ============================================================================
-- 5. Function to get pricing tier for country
-- ============================================================================

CREATE OR REPLACE FUNCTION get_pricing_tier_for_country(p_country_code VARCHAR(2))
RETURNS TABLE(tier VARCHAR(20), base_price_usd DECIMAL(10,2), ppp_multiplier DECIMAL(4,2)) AS $$
BEGIN
    RETURN QUERY
    SELECT pt.tier, pt.base_price_usd, pt.ppp_multiplier
    FROM pricing_tiers pt
    WHERE pt.country_code = p_country_code

    UNION ALL

    -- Default to tier1 if country not found
    SELECT 'tier1'::VARCHAR(20), 18.00::DECIMAL(10,2), 1.00::DECIMAL(4,2)
    WHERE NOT EXISTS (
        SELECT 1 FROM pricing_tiers WHERE country_code = p_country_code
    )
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_pricing_tier_for_country IS
    'Returns pricing tier info for a country. Defaults to tier1 if country not in table.';


-- ============================================================================
-- 6. Test queries (run manually)
-- ============================================================================

-- Test pricing tier lookup
/*
SELECT * FROM get_pricing_tier_for_country('US');  -- Should return tier1, $18
SELECT * FROM get_pricing_tier_for_country('TH');  -- Should return tier3, $5
SELECT * FROM get_pricing_tier_for_country('XX');  -- Should return tier1, $18 (default)
*/

-- View fraud risk for all users (after data is populated)
/*
SELECT * FROM user_fraud_risk_analysis
WHERE calculated_risk_score > 30
ORDER BY calculated_risk_score DESC;
*/
