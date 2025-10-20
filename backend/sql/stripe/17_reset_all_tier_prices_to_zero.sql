-- Reset tous les prix tier à 0 pour tous les plans

-- Vérifier l'état actuel
SELECT plan_name, tier_level, price_usd
FROM stripe_pricing_tiers
ORDER BY plan_name, tier_level;

-- Reset tous les prix à 0
UPDATE stripe_pricing_tiers
SET price_usd = 0;

-- Vérifier le résultat
SELECT plan_name, tier_level, price_usd
FROM stripe_pricing_tiers
ORDER BY plan_name, tier_level;

-- Info: Maintenant tous les pays afficheront $0.00 dans "Prix par pays"
