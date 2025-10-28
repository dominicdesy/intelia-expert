# 🚀 Guide de Déploiement - Country Tracking & Pricing Fraud Prevention

## ✅ Changements Implémentés

### 1. Fichiers SQL
- `backend/sql/stripe/27_add_country_tracking.sql` - Migration complète

### 2. Services Python
- `backend/app/services/country_tracking_service.py` - Service de tracking et analyse

### 3. Endpoints API Modifiés
- `POST /auth/register` - Tracker le pays à l'inscription
- `POST /auth/login` - Logger chaque connexion avec pays/IP/device

### 4. Nouveaux Endpoints API
- `GET /billing/pricing-info` - Obtenir tier de prix et pays
- `GET /billing/fraud-analysis` - Analyse de risque de fraude
- `POST /billing/lock-pricing-tier` - Verrouiller le tier lors du paiement

### 5. Documentation
- `PRICING_FRAUD_PREVENTION_STRATEGY.md` - Stratégie complète

---

## 📋 Étapes de Déploiement

### Étape 1: Exécuter la Migration SQL

**Option A: Via psql en ligne de commande**
```bash
# Depuis votre machine locale
psql $DATABASE_URL -f backend/sql/stripe/27_add_country_tracking.sql
```

**Option B: Via Digital Ocean Dashboard**
1. Aller sur https://cloud.digitalocean.com/databases
2. Sélectionner votre base de données PostgreSQL
3. Onglet "Users & Databases" → "Connection Details"
4. Copier la "Connection String"
5. Utiliser un client PostgreSQL (pgAdmin, DBeaver, etc.)
6. Coller et exécuter le contenu de `27_add_country_tracking.sql`

**Option C: Via Python (recommandé pour vérification)**
```bash
cd backend
python -c "
import os
import psycopg2

# Lire le fichier SQL
with open('sql/stripe/27_add_country_tracking.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

# Se connecter et exécuter
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

try:
    cur.execute(sql)
    conn.commit()
    print('✅ Migration exécutée avec succès!')
except Exception as e:
    print(f'❌ Erreur: {e}')
    conn.rollback()
finally:
    cur.close()
    conn.close()
"
```

### Étape 2: Vérifier la Migration

```sql
-- Vérifier les nouvelles colonnes
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'user_billing_info'
  AND column_name IN ('signup_country', 'pricing_tier', 'pricing_country', 'pricing_locked_at');

-- Vérifier la table user_login_history
SELECT COUNT(*) FROM user_login_history;

-- Vérifier la table pricing_tiers
SELECT country_code, tier, base_price_usd
FROM pricing_tiers
ORDER BY tier, country_code
LIMIT 10;

-- Vérifier la vue de fraude
SELECT * FROM user_fraud_risk_analysis LIMIT 1;
```

### Étape 3: Redémarrer le Backend

```bash
# Si vous utilisez uvicorn directement
cd backend
uvicorn app.main:app --reload

# Si vous utilisez Docker
docker-compose restart backend

# Si vous utilisez systemd (production)
sudo systemctl restart intelia-backend
```

### Étape 4: Tester les Endpoints

**Test 1: Vérifier que le service charge correctement**
```bash
# Les logs ne devraient PAS afficher "Country tracking service not available"
tail -f backend/logs/app.log | grep -i "country tracking"
```

**Test 2: Tester l'inscription (crée un nouveau compte test)**
```bash
curl -X POST https://api.intelia.com/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-country@example.com",
    "password": "TestPassword123!",
    "first_name": "Test",
    "last_name": "User"
  }'
```

Vérifier dans les logs:
```
[Register] Country tracked: test-country@example.com from CA (tier: tier1)
```

**Test 3: Tester la connexion**
```bash
# D'abord se connecter
curl -X POST https://api.intelia.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-country@example.com",
    "password": "TestPassword123!"
  }'
```

Vérifier dans les logs:
```
[Login] Country tracked: test-country@example.com from CA (risk_score: 0)
```

**Test 4: Tester l'endpoint pricing-info**
```bash
# Récupérer le token JWT de la connexion précédente
TOKEN="votre_jwt_token_ici"

curl -X GET https://api.intelia.com/v1/billing/pricing-info \
  -H "Authorization: Bearer $TOKEN"
```

Devrait retourner:
```json
{
  "pricing_tier": "tier1",
  "pricing_country": "CA",
  "signup_country": "CA",
  "is_locked": false,
  "base_price_usd": 18.00,
  "billing_currency": "USD",
  "available_currencies": ["USD", "CAD", "EUR", ...]
}
```

**Test 5: Tester l'analyse de fraude**
```bash
curl -X GET https://api.intelia.com/v1/billing/fraud-analysis \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔍 Monitoring Post-Déploiement

### Vérifier les Inscriptions
```sql
SELECT
    user_email,
    signup_country,
    pricing_tier,
    created_at
FROM user_billing_info
WHERE signup_country IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

### Vérifier les Connexions Loggées
```sql
SELECT
    user_email,
    country_code,
    is_vpn,
    is_proxy,
    risk_score,
    login_timestamp
FROM user_login_history
ORDER BY login_timestamp DESC
LIMIT 20;
```

### Détecter les Connexions Suspectes
```sql
SELECT * FROM user_fraud_risk_analysis
WHERE risk_score > 50
ORDER BY risk_score DESC;
```

---

## ⚠️ Troubleshooting

### Erreur: "Country tracking service not available"

**Cause**: Le service n'a pas pu être importé

**Solutions**:
1. Vérifier que le fichier existe:
   ```bash
   ls -la backend/app/services/country_tracking_service.py
   ```

2. Vérifier les dépendances Python:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Vérifier les imports dans le service:
   ```bash
   python -c "from app.services.country_tracking_service import CountryTrackingService"
   ```

### Erreur: "relation 'user_login_history' does not exist"

**Cause**: La migration SQL n'a pas été exécutée

**Solution**: Exécuter la migration (Étape 1)

### Erreur: "column 'signup_country' does not exist"

**Cause**: Migration incomplète

**Solution**:
```sql
-- Vérifier les colonnes manquantes
ALTER TABLE user_billing_info ADD COLUMN IF NOT EXISTS signup_country VARCHAR(2);
ALTER TABLE user_billing_info ADD COLUMN IF NOT EXISTS pricing_tier VARCHAR(20);
ALTER TABLE user_billing_info ADD COLUMN IF NOT EXISTS pricing_country VARCHAR(2);
ALTER TABLE user_billing_info ADD COLUMN IF NOT EXISTS pricing_locked_at TIMESTAMP;
```

---

## 📊 Statistiques Utiles

### Dashboard de Fraude
```sql
SELECT
    risk_level,
    COUNT(*) as user_count,
    ROUND(AVG(risk_score)::numeric, 2) as avg_risk_score
FROM user_fraud_risk_analysis
GROUP BY risk_level
ORDER BY
    CASE risk_level
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
    END;
```

### Top Pays par Tier
```sql
SELECT
    tier,
    COUNT(*) as country_count,
    ROUND(AVG(base_price_usd)::numeric, 2) as avg_price
FROM pricing_tiers
GROUP BY tier
ORDER BY tier;
```

---

## ✅ Checklist de Déploiement

- [ ] Migration SQL exécutée sans erreurs
- [ ] Tables créées (user_login_history, pricing_tiers)
- [ ] Colonnes ajoutées à user_billing_info
- [ ] Service Python charge correctement (pas de warnings)
- [ ] Backend redémarré
- [ ] Endpoint /register tracker le pays
- [ ] Endpoint /login logger les connexions
- [ ] Endpoint /billing/pricing-info retourne les bonnes données
- [ ] Monitoring configuré (vérifier les logs régulièrement)

---

## 🎯 Prochaines Étapes

Après le déploiement, vous devriez:

1. **Collecter des données** pendant 1-2 semaines
2. **Analyser les patterns** de connexion
3. **Ajuster les seuils** de détection de fraude si nécessaire
4. **Implémenter le frontend** pour afficher les prix régionalisés
5. **Intégrer avec Stripe** pour valider le pays de la carte

---

Besoin d'aide ? Contactez l'équipe de support technique.
