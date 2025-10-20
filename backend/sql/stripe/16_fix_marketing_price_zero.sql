-- Fix: calculate_marketing_price devrait retourner 0 si le prix tier est 0

CREATE OR REPLACE FUNCTION calculate_marketing_price(raw_price NUMERIC)
RETURNS NUMERIC AS $$
DECLARE
    rounded_price NUMERIC;
    price_floor INTEGER;
BEGIN
    -- Si le prix est exactement 0, retourner 0 (pas de prix défini)
    IF raw_price = 0 THEN
        RETURN 0;
    END IF;

    -- Si le prix est très petit (< 1 mais > 0), retourner 0.99
    IF raw_price < 1 THEN
        RETURN 0.99;
    END IF;

    -- Trouver le palier inférieur
    price_floor := FLOOR(raw_price);

    -- Appliquer la logique de prix marketing
    IF raw_price >= (price_floor + 0.80) THEN
        rounded_price := price_floor + 0.99;
    ELSE
        IF price_floor > 0 THEN
            rounded_price := (price_floor - 1) + 0.99;
        ELSE
            rounded_price := 0.99;
        END IF;
    END IF;

    -- Paliers marketing spéciaux
    IF rounded_price < 5 THEN
        rounded_price := FLOOR(rounded_price) + 0.99;
    ELSIF rounded_price >= 5 AND rounded_price < 10 THEN
        IF raw_price < 7 THEN
            rounded_price := 4.99;
        ELSE
            rounded_price := 9.99;
        END IF;
    ELSIF rounded_price >= 10 AND rounded_price < 15 THEN
        IF raw_price < 12 THEN
            rounded_price := 9.99;
        ELSE
            rounded_price := 14.99;
        END IF;
    ELSIF rounded_price >= 15 AND rounded_price < 25 THEN
        IF raw_price < 18 THEN
            rounded_price := 14.99;
        ELSIF raw_price < 22 THEN
            rounded_price := 19.99;
        ELSE
            rounded_price := 24.99;
        END IF;
    ELSIF rounded_price >= 25 AND rounded_price < 35 THEN
        IF raw_price < 27 THEN
            rounded_price := 24.99;
        ELSIF raw_price < 32 THEN
            rounded_price := 29.99;
        ELSE
            rounded_price := 34.99;
        END IF;
    ELSIF rounded_price >= 35 AND rounded_price < 60 THEN
        IF raw_price < 45 THEN
            rounded_price := 39.99;
        ELSE
            rounded_price := 49.99;
        END IF;
    ELSIF rounded_price >= 60 AND rounded_price < 100 THEN
        IF raw_price < 70 THEN
            rounded_price := 59.99;
        ELSIF raw_price < 90 THEN
            rounded_price := 79.99;
        ELSE
            rounded_price := 99.99;
        END IF;
    ELSIF rounded_price >= 100 AND rounded_price < 200 THEN
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

-- Test: Vérifier que 0 retourne 0
SELECT
    0 as raw_price,
    calculate_marketing_price(0) as marketing_price,
    'Should be 0.00 (not 0.99)' as expected;

-- Test: Vérifier que 0.50 retourne 0.99
SELECT
    0.50 as raw_price,
    calculate_marketing_price(0.50) as marketing_price,
    'Should be 0.99' as expected;
