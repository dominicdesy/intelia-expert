-- Supprimer tous les prix custom pour forcer l'utilisation des prix tier automatiques

-- Vérifier combien de prix custom existent
SELECT COUNT(*) as custom_prices_count
FROM stripe_country_pricing
WHERE active = TRUE;

-- OPTION 1: Soft delete (désactiver) tous les prix custom
UPDATE stripe_country_pricing
SET active = FALSE;

-- OPTION 2: Hard delete (supprimer complètement) tous les prix custom
-- DELETE FROM stripe_country_pricing;

-- Vérifier le résultat
SELECT COUNT(*) as active_custom_prices
FROM stripe_country_pricing
WHERE active = TRUE;

-- Maintenant, la vue complete_pricing_matrix utilisera UNIQUEMENT les prix tier
-- Si les prix tier sont à 0, tous les pays afficheront $0.00

-- Test: Vérifier que les prix sont maintenant calculés depuis les tiers
SELECT country_code, plan_name, display_price, price_type
FROM complete_pricing_matrix
WHERE country_code IN ('CA', 'US', 'AU')
ORDER BY country_code, plan_name
LIMIT 10;
