# 📊 GUIDE DE GESTION DE LA TARIFICATION

## Vue d'ensemble

Le système de tarification Stripe utilise une architecture à **3 niveaux** :

1. **Tiers de tarification** (4 niveaux) → Définit les prix en USD par marché
2. **Mapping pays → tier** → Associe chaque pays à un tier
3. **Prix personnalisés par pays** (optionnel) → Prix arrondis pour le marketing

---

## 🎯 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  NIVEAU 1: TIERS (stripe_pricing_tiers)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Tier 1: Pro $8.99  | Elite $9.99   (Marchés émerg.)  │   │
│  │ Tier 2: Pro $10.99 | Elite $15.99  (Intermédiaire)   │   │
│  │ Tier 3: Pro $15.99 | Elite $23.99  (Développés)      │   │
│  │ Tier 4: Pro $19.99 | Elite $31.99  (Premium)         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  NIVEAU 2: PAYS (stripe_country_tiers)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ FR (France)    → Tier 3 → EUR                         │   │
│  │ US (USA)       → Tier 4 → USD                         │   │
│  │ IN (India)     → Tier 1 → USD                         │   │
│  │ CA (Canada)    → Tier 4 → CAD                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  NIVEAU 3: PRIX PERSONNALISÉS (stripe_country_pricing)      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ FR, Pro  → 14.99 EUR (au lieu de 14.81 EUR calculé)  │   │
│  │ CA, Pro  → 26.99 CAD (au lieu de 27.01 CAD calculé)  │   │
│  │ GB, Elite → 24.99 GBP (au lieu de 25.19 GBP calculé) │   │
│  └──────────────────────────────────────────────────────┘   │
│  📌 OPTIONNEL - Si absent, prix calculé automatiquement      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Cas d'usage courants

### 1️⃣ Changer le prix d'un tier (affecte tous les pays du tier)

```sql
-- Augmenter le prix du Tier 2 pour le plan Pro
UPDATE stripe_pricing_tiers
SET price_usd = 11.99,
    updated_at = CURRENT_TIMESTAMP
WHERE plan_name = 'pro' AND tier_level = 2;

-- Résultat: Tous les pays Tier 2 verront 11.99 USD (ou équivalent en devise locale)
```

### 2️⃣ Déplacer un pays vers un autre tier

```sql
-- Mettre la France en Tier 2 (moins cher) au lieu de Tier 3
UPDATE stripe_country_tiers
SET tier_level = 2,
    updated_at = CURRENT_TIMESTAMP
WHERE country_code = 'FR';

-- Résultat: France passera de 15.99$ à 10.99$ (ou prix personnalisé si défini)
```

### 3️⃣ Définir un prix personnalisé pour un pays (marketing)

```sql
-- Définir un prix arrondi pour l'Italie
INSERT INTO stripe_country_pricing (
    country_code,
    plan_name,
    display_price,
    display_currency,
    display_currency_symbol
) VALUES (
    'IT',
    'pro',
    9.99,
    'EUR',
    '€'
)
ON CONFLICT (country_code, plan_name) DO UPDATE
SET display_price = 9.99,
    updated_at = CURRENT_TIMESTAMP;

-- Résultat: Italie affichera 9.99 EUR même si le tier suggère 10.18 EUR
```

### 4️⃣ Ajouter un nouveau pays

```sql
-- Ajouter le Brésil en Tier 1
INSERT INTO stripe_country_tiers (
    country_code,
    country_name,
    tier_level,
    currency_code,
    currency_symbol
) VALUES (
    'BR',
    'Brazil',
    1,
    'USD',
    '$'
);

-- Le Brésil utilisera automatiquement les prix du Tier 1 (8.99$ / 9.99$)
```

### 5️⃣ Mettre à jour les taux de change

```sql
-- Mettre à jour le taux CAD → USD
UPDATE stripe_currency_rates
SET rate_to_usd = 0.75,
    last_updated = CURRENT_TIMESTAMP
WHERE currency_code = 'CAD';

-- Résultat: Tous les prix en CAD seront recalculés (sauf prix personnalisés)
```

---

## 📊 Requêtes utiles

### Voir tous les prix pour un plan

```sql
-- Voir tous les prix du plan Pro par pays
SELECT * FROM complete_pricing_matrix
WHERE plan_name = 'pro'
ORDER BY tier_level, country_code;
```

### Voir le prix pour un pays spécifique

```sql
-- Voir le prix pour la France
SELECT * FROM get_price_for_country('pro', 'FR');

-- Résultat:
-- plan_name | tier_level | price_usd | price_local | currency | symbol | country | stripe_price_id
-- pro       | 3          | 15.99     | 14.99       | EUR      | €      | France  | price_xxxxx
```

### Lister les pays qui n'ont pas de prix personnalisés

```sql
-- Voir les prix qui seraient générés automatiquement
SELECT * FROM generate_rounded_prices()
WHERE plan_name = 'pro';
```

### Voir le résumé des tiers

```sql
-- Combien de pays par tier
SELECT * FROM tier_summary;

-- Résultat:
-- tier_level | countries_count | currencies     | example_country
-- 1          | 22              | USD, EUR       | India
-- 2          | 18              | EUR, USD       | Spain
-- 3          | 14              | EUR, USD       | France
-- 4          | 11              | USD, CAD, GBP  | United States
```

---

## 💡 Stratégies de tarification

### Stratégie A: Tarification simple (1 prix par tier)

✅ **Avantages**: Simple, cohérent, facile à gérer
❌ **Inconvénients**: Moins optimisé pour chaque pays

**Mise en œuvre**:
- Ne PAS utiliser `stripe_country_pricing`
- Laisser le système calculer automatiquement depuis les tiers

### Stratégie B: Tarification optimisée (prix par pays)

✅ **Avantages**: Prix optimaux pour chaque marché
❌ **Inconvénients**: Plus de maintenance

**Mise en œuvre**:
- Définir des prix dans `stripe_country_pricing` pour chaque pays important
- Les autres pays utilisent le calcul automatique

### Stratégie C: Mixte (recommandé)

✅ **Avantages**: Équilibre optimal
❌ **Inconvénients**: -

**Mise en œuvre**:
- Prix personnalisés pour les 10-20 pays principaux
- Calcul automatique pour les autres

```sql
-- Définir les prix personnalisés pour les pays top 10
INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol) VALUES
('US', 'pro', 19.99, 'USD', '$'),
('CA', 'pro', 26.99, 'CAD', 'CA$'),
('GB', 'pro', 15.99, 'GBP', '£'),
('FR', 'pro', 14.99, 'EUR', '€'),
('DE', 'pro', 14.99, 'EUR', '€'),
('ES', 'pro', 9.99, 'EUR', '€'),
('IT', 'pro', 9.99, 'EUR', '€'),
('AU', 'pro', 29.99, 'AUD', 'A$'),
('IN', 'pro', 8.99, 'USD', '$'),
('BR', 'pro', 8.99, 'USD', '$')
ON CONFLICT (country_code, plan_name) DO UPDATE
SET display_price = EXCLUDED.display_price,
    updated_at = CURRENT_TIMESTAMP;
```

---

## 🎨 Exemples de prix arrondis

### Règles d'arrondi populaires

```sql
-- Arrondi à .99
14.81 EUR → 14.99 EUR
22.21 EUR → 22.99 EUR
27.01 CAD → 26.99 CAD

-- Arrondi à .95
14.81 EUR → 14.95 EUR
22.21 EUR → 22.95 EUR

-- Arrondi entier
14.81 EUR → 15.00 EUR
22.21 EUR → 22.00 EUR
```

### Fonction SQL pour générer les prix arrondis .99

```sql
-- Voir les suggestions de prix .99 pour tous les pays
SELECT
    country_code,
    plan_name,
    FLOOR(calculated_price) + 0.99 as suggested_price,
    currency
FROM (
    SELECT
        ct.country_code,
        pt.plan_name,
        pt.price_usd / cr.rate_to_usd as calculated_price,
        ct.currency_code as currency
    FROM stripe_country_tiers ct
    CROSS JOIN stripe_pricing_tiers pt
    JOIN stripe_currency_rates cr ON ct.currency_code = cr.currency_code
    WHERE ct.tier_level = pt.tier_level
      AND pt.plan_name = 'pro'
) as prices
ORDER BY country_code;
```

---

## 🔄 Workflow de changement de prix

### Scénario: Augmenter tous les prix de 10%

```sql
-- Étape 1: Mettre à jour les tiers (base)
UPDATE stripe_pricing_tiers
SET price_usd = ROUND(price_usd * 1.10, 2),
    updated_at = CURRENT_TIMESTAMP
WHERE plan_name IN ('pro', 'elite');

-- Étape 2: Mettre à jour les prix personnalisés (si utilisés)
UPDATE stripe_country_pricing
SET display_price = ROUND(display_price * 1.10, 2),
    updated_at = CURRENT_TIMESTAMP
WHERE plan_name IN ('pro', 'elite');

-- Étape 3: Vérifier les nouveaux prix
SELECT * FROM complete_pricing_matrix WHERE plan_name = 'pro';
```

### Scénario: Créer une promotion pour un pays

```sql
-- Promotion: -20% en France pendant 1 mois
INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol, notes)
VALUES ('FR', 'pro', 11.99, 'EUR', '€', 'Promotion -20% jusqu''au 2025-02-16')
ON CONFLICT (country_code, plan_name) DO UPDATE
SET display_price = 11.99,
    notes = 'Promotion -20% jusqu''au 2025-02-16',
    updated_at = CURRENT_TIMESTAMP;

-- Après la promo: Revenir au prix normal
UPDATE stripe_country_pricing
SET display_price = 14.99,
    notes = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE country_code = 'FR' AND plan_name = 'pro';
```

---

## 🛡️ Bonnes pratiques

### ✅ À FAIRE

1. **Toujours vérifier avant de changer un tier**
   ```sql
   -- Voir combien de pays seront affectés
   SELECT COUNT(*) FROM stripe_country_tiers WHERE tier_level = 2;
   ```

2. **Tester avec un seul pays d'abord**
   ```sql
   -- Test: Mettre juste la France à 9.99 EUR
   INSERT INTO stripe_country_pricing (country_code, plan_name, display_price, display_currency, display_currency_symbol)
   VALUES ('FR', 'pro', 9.99, 'EUR', '€');
   ```

3. **Documenter les changements**
   ```sql
   -- Utiliser la colonne notes
   UPDATE stripe_country_pricing
   SET notes = 'Prix ajusté suite à feedback marketing - 2025-01-16'
   WHERE country_code = 'FR' AND plan_name = 'pro';
   ```

4. **Mettre à jour les taux de change régulièrement**
   ```sql
   -- Script à exécuter chaque semaine
   UPDATE stripe_currency_rates SET rate_to_usd = 0.74, last_updated = NOW() WHERE currency_code = 'CAD';
   UPDATE stripe_currency_rates SET rate_to_usd = 1.08, last_updated = NOW() WHERE currency_code = 'EUR';
   UPDATE stripe_currency_rates SET rate_to_usd = 1.27, last_updated = NOW() WHERE currency_code = 'GBP';
   ```

### ❌ À ÉVITER

1. ❌ Changer directement un tier sans vérifier l'impact
2. ❌ Oublier de mettre à jour `updated_at`
3. ❌ Créer des prix trop différents entre pays voisins
4. ❌ Utiliser des taux de change obsolètes (>1 mois)

---

## 📞 Support

Pour toute question sur la tarification:
- Consulter la vue `complete_pricing_matrix`
- Utiliser la fonction `get_price_for_country('pro', 'FR')`
- Vérifier les logs backend: Rechercher "Prix pour"

---

**Dernière mise à jour**: 2025-01-16
