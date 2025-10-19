-- Fonction pour calculer un prix marketing arrondi
-- Convertit un prix brut en prix "marketing" (ex: 20.34 → 19.99)

CREATE OR REPLACE FUNCTION calculate_marketing_price(raw_price NUMERIC)
RETURNS NUMERIC AS $$
DECLARE
    rounded_price NUMERIC;
    price_floor INTEGER;
BEGIN
    -- Si le prix est très petit (< 1), retourner 0.99
    IF raw_price < 1 THEN
        RETURN 0.99;
    END IF;

    -- Trouver le palier inférieur
    price_floor := FLOOR(raw_price);

    -- Appliquer la logique de prix marketing
    -- Si le prix brut est proche du palier supérieur (ex: 19.50), monter à X9.99
    -- Sinon, rester à X9.99 du palier inférieur

    IF raw_price >= (price_floor + 0.80) THEN
        -- Prix proche du palier supérieur, monter
        rounded_price := price_floor + 0.99;
    ELSE
        -- Prix plus bas, utiliser le palier inférieur
        IF price_floor > 0 THEN
            rounded_price := (price_floor - 1) + 0.99;
        ELSE
            rounded_price := 0.99;
        END IF;
    END IF;

    -- Paliers marketing spéciaux
    -- 0-5: X.99
    -- 5-15: X.99 ou X4.99
    -- 15-30: X9.99
    -- 30-60: X9.99
    -- 60+: X9.99

    IF rounded_price < 5 THEN
        rounded_price := FLOOR(rounded_price) + 0.99;
    ELSIF rounded_price >= 5 AND rounded_price < 10 THEN
        -- 5-10 range: soit 4.99, soit 9.99
        IF raw_price < 7 THEN
            rounded_price := 4.99;
        ELSE
            rounded_price := 9.99;
        END IF;
    ELSIF rounded_price >= 10 AND rounded_price < 15 THEN
        -- 10-15 range: soit 9.99, soit 14.99
        IF raw_price < 12 THEN
            rounded_price := 9.99;
        ELSE
            rounded_price := 14.99;
        END IF;
    ELSIF rounded_price >= 15 AND rounded_price < 25 THEN
        -- 15-25 range: soit 14.99, 19.99, ou 24.99
        IF raw_price < 18 THEN
            rounded_price := 14.99;
        ELSIF raw_price < 22 THEN
            rounded_price := 19.99;
        ELSE
            rounded_price := 24.99;
        END IF;
    ELSIF rounded_price >= 25 AND rounded_price < 35 THEN
        -- 25-35 range: soit 24.99, 29.99, ou 34.99
        IF raw_price < 27 THEN
            rounded_price := 24.99;
        ELSIF raw_price < 32 THEN
            rounded_price := 29.99;
        ELSE
            rounded_price := 34.99;
        END IF;
    ELSIF rounded_price >= 35 AND rounded_price < 60 THEN
        -- 35-60 range: 39.99, 49.99
        IF raw_price < 45 THEN
            rounded_price := 39.99;
        ELSE
            rounded_price := 49.99;
        END IF;
    ELSIF rounded_price >= 60 AND rounded_price < 100 THEN
        -- 60-100 range: 59.99, 79.99, 99.99
        IF raw_price < 70 THEN
            rounded_price := 59.99;
        ELSIF raw_price < 90 THEN
            rounded_price := 79.99;
        ELSE
            rounded_price := 99.99;
        END IF;
    ELSIF rounded_price >= 100 AND rounded_price < 200 THEN
        -- 100-200 range: 99.99, 149.99, 199.99
        IF raw_price < 120 THEN
            rounded_price := 99.99;
        ELSIF raw_price < 170 THEN
            rounded_price := 149.99;
        ELSE
            rounded_price := 199.99;
        END IF;
    ELSE
        -- 200+: arrondir au X99.99
        rounded_price := FLOOR(raw_price / 100) * 100 + 99.99;
    END IF;

    RETURN rounded_price;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- Recréer la vue complete_pricing_matrix avec prix marketing automatiques
DROP VIEW IF EXISTS complete_pricing_matrix CASCADE;

CREATE VIEW complete_pricing_matrix AS
SELECT
    ct.country_code,
    ct.country_name,
    ct.tier_level,
    pt.plan_name,
    pt.price_usd as tier_price_usd,

    -- Si prix custom existe, l'utiliser, sinon calculer avec prix marketing
    COALESCE(
        cp.display_price,
        calculate_marketing_price(ROUND(pt.price_usd / cr.rate_to_usd, 2))
    ) as display_price,

    COALESCE(cp.display_currency, ct.currency_code) as display_currency,
    COALESCE(cp.display_currency_symbol, ct.currency_symbol) as display_currency_symbol,

    CASE
        WHEN cp.id IS NOT NULL THEN 'custom'
        ELSE 'auto_marketing'
    END as price_type,

    cp.stripe_price_id,
    cp.notes
FROM stripe_country_tiers ct
CROSS JOIN stripe_pricing_tiers pt
JOIN stripe_currency_rates cr ON ct.currency_code = cr.currency_code
LEFT JOIN stripe_country_pricing cp
    ON cp.country_code = ct.country_code
    AND cp.plan_name = pt.plan_name
    AND cp.active = TRUE
WHERE ct.tier_level = pt.tier_level
  AND ct.active = TRUE
  AND pt.active = TRUE
ORDER BY ct.tier_level, ct.country_code, pt.plan_name;


-- Commentaire explicatif
COMMENT ON VIEW complete_pricing_matrix IS
'Vue des prix pour tous les pays et plans.
- Utilise les prix custom si définis (price_type=custom)
- Sinon calcule automatiquement depuis le tier avec ajustement marketing (price_type=auto_marketing)
- Les prix sont arrondis aux paliers marketing: 4.99, 9.99, 14.99, 19.99, 24.99, 29.99, 49.99, 99.99, etc.';

COMMENT ON FUNCTION calculate_marketing_price IS
'Convertit un prix brut en prix marketing arrondi.
Exemples:
- 20.34 → 19.99
- 15.67 → 14.99
- 51.23 → 49.99
Utilise des paliers marketing standards pour maximiser les conversions.';
