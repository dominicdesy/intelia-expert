# Système de Limitation de Quotas Mensuels

## Vue d'ensemble

Le système de quotas mensuels permet de limiter le nombre de questions pour le **plan Essential à 50 questions par mois**, tout en offrant un accès illimité aux plans Pro et Elite.

### Modes de fonctionnement Stripe

Le système supporte 3 modes configurables via `STRIPE_MODE`:

| Mode | Description | Quotas | Facturation |
|------|-------------|--------|-------------|
| **PRODUCTION** | Mode live avec vraie facturation | ✅ Appliqués (Essential: 50/mois) | ✅ Vraie facturation Stripe |
| **TEST** | Mode test Stripe | ✅ Appliqués (pour tester) | ❌ Test seulement |
| **DISABLE** | Développement local | ❌ Désactivés (illimité) | ❌ Stripe désactivé |

---

## Configuration

### 1. Variables d'environnement

Ajoutez à votre `.env`:

```bash
# Mode Stripe (production | test | disable)
STRIPE_MODE=disable

# Clés Stripe PRODUCTION (si STRIPE_MODE=production)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Clés Stripe TEST (si STRIPE_MODE=test)
STRIPE_TEST_SECRET_KEY=sk_test_...
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_...
STRIPE_TEST_WEBHOOK_SECRET=whsec_test_...
```

### 2. Migration SQL

Exécutez le script de migration pour activer les quotas:

```bash
psql $DATABASE_URL < backend/sql/migrations/add_essential_quota_limits.sql
```

**Ce script fait:**
- ✅ Configure `monthly_quota=50` pour le plan Essential dans `billing_plans`
- ✅ Crée les enregistrements `monthly_usage_tracking` pour tous les utilisateurs Essential
- ✅ Active `quota_enforcement=TRUE` pour les utilisateurs Essential
- ✅ Crée les index de performance nécessaires

---

## Architecture du Système

### Tables impliquées

#### 1. `billing_plans`
```sql
plan_name  | monthly_quota | price_per_month
-----------|---------------|----------------
essential  | 50            | 0.00
pro        | 0 (illimité)  | 18.00
elite      | 0 (illimité)  | 28.00
```

#### 2. `stripe_subscriptions`
Lien entre utilisateur et plan actif via Stripe

#### 3. `user_billing_info`
- `plan_name`: Plan de l'utilisateur
- `quota_enforcement`: Si TRUE, les quotas sont appliqués
- `custom_monthly_quota`: Quota personnalisé (override)

#### 4. `monthly_usage_tracking`
Compteurs mensuels par utilisateur:
```sql
- user_email
- month_year (YYYY-MM)
- questions_used
- questions_successful
- questions_failed
- monthly_quota
- quota_exceeded_at
- current_status
```

---

## Flux de Vérification

### Avant chaque question

```python
from app.services.usage_limiter import check_user_quota, QuotaExceededException

try:
    quota_info = check_user_quota(user_email)
    # quota_info = {
    #     'can_ask': True,
    #     'questions_used': 25,
    #     'monthly_quota': 50,
    #     'questions_remaining': 25,
    #     'plan_name': 'essential'
    # }
except QuotaExceededException as e:
    # Utilisateur a dépassé son quota
    return {
        "error": "quota_exceeded",
        "message": str(e),
        "usage_info": e.usage_info
    }
```

### Après chaque question

```python
from app.services.usage_limiter import increment_question_count

# Question réussie
usage = increment_question_count(user_email, success=True, cost_usd=0.02)

# Question échouée
usage = increment_question_count(user_email, success=False)
```

---

## Endpoints API

### GET `/v1/usage/current`
Récupère l'usage actuel de l'utilisateur

**Response:**
```json
{
  "status": "success",
  "usage": {
    "plan_name": "essential",
    "monthly_quota": 50,
    "questions_used": 25,
    "questions_remaining": 25,
    "percentage_used": 50.0,
    "current_status": "active",
    "month_year": "2025-01"
  }
}
```

### GET `/v1/usage/check`
Vérifie si l'utilisateur peut poser une question

**Response (OK):**
```json
{
  "status": "success",
  "quota": {
    "can_ask": true,
    "questions_used": 25,
    "monthly_quota": 50,
    "questions_remaining": 25,
    "warning_threshold_reached": false,
    "usage_percentage": 50.0
  }
}
```

**Response (Quota dépassé):**
```json
{
  "status": "quota_exceeded",
  "quota": {
    "can_ask": false,
    "questions_used": 50,
    "monthly_quota": 50,
    "questions_remaining": 0,
    "plan_name": "essential",
    "month_year": "2025-01"
  },
  "message": "Quota mensuel dépassé pour user@example.com. Plan essential: 50/50 questions utilisées."
}
```

### GET `/v1/usage/history?months=6`
Historique d'usage

**Response:**
```json
{
  "status": "success",
  "history": [
    {
      "month_year": "2025-01",
      "questions_used": 25,
      "monthly_quota": 50,
      "questions_successful": 24,
      "questions_failed": 1,
      "current_status": "active"
    },
    {
      "month_year": "2024-12",
      "questions_used": 48,
      "monthly_quota": 50,
      "questions_successful": 47,
      "questions_failed": 1,
      "current_status": "active"
    }
  ]
}
```

### GET `/v1/usage/health`
Health check du service

---

## Reset Mensuel Automatique

Les compteurs doivent être réinitialisés le **1er de chaque mois à 00:00 UTC**.

### Configuration CRON (cron-job.org)

**Étape 1: Générer une clé secrète**
```bash
openssl rand -hex 32
# Exemple: e1ca01ab5234c3188c5a72abcdbb184d11e95e7743828783c9754fc81ab36dc7
```

**Étape 2: Ajouter la clé dans `.env`**
```bash
# backend/.env
CRON_SECRET_KEY=e1ca01ab5234c3188c5a72abcdbb184d11e95e7743828783c9754fc81ab36dc7
```

**Étape 3: Configurer sur cron-job.org**

1. Créer un compte sur https://cron-job.org (gratuit)
2. Créer un nouveau cronjob avec:
   - **URL**: `https://expert.intelia.com/api/v1/usage/cron/reset-monthly?secret=e1ca01ab5234c3188c5a72abcdbb184d11e95e7743828783c9754fc81ab36dc7`
   - **Méthode**: POST
   - **Schedule**: `0 0 1 * *` (1er du mois à 00:00 UTC)
   - **Titre**: "Reset Quotas Mensuels Intelia"
   - **Notifications**: ✅ Email si échec

**Étape 4: Tester manuellement**
```bash
curl -X POST "https://expert.intelia.com/api/v1/usage/cron/reset-monthly?secret=VOTRE_CLE"
```

**Réponse attendue:**
```json
{
  "status": "success",
  "message": "Reset mensuel effectué avec succès",
  "result": {
    "status": "success",
    "month_year": "2025-02",
    "users_reset": 150,
    "timestamp": "2025-02-01T00:00:00.000000"
  },
  "timestamp": "2025-02-01T00:00:05.123456"
}
```

### Alternative: Fonction Python directe
```python
from app.services.usage_limiter import reset_monthly_usage_for_all_users

# À appeler le 1er de chaque mois
result = reset_monthly_usage_for_all_users()
# result = {
#     'status': 'success',
#     'month_year': '2025-02',
#     'users_reset': 150
# }
```

---

## Intégration Frontend

### Afficher l'usage dans le UI

```typescript
// Récupérer l'usage actuel
const response = await fetch('/v1/usage/current', {
  headers: { 'Authorization': `Bearer ${token}` }
});

const { usage } = await response.json();

// Afficher dans le UI
if (usage.monthly_quota) {
  // Utilisateur avec quota (Essential)
  console.log(`${usage.questions_used} / ${usage.questions_remaining} questions utilisées`);
  console.log(`${usage.percentage_used}% du quota`);

  // Avertissement si > 80%
  if (usage.percentage_used >= 80) {
    showWarning("Vous approchez de votre limite mensuelle");
  }
} else {
  // Utilisateur illimité (Pro/Elite)
  console.log("Questions illimitées");
}
```

### Vérifier avant de soumettre une question

```typescript
// Avant d'envoyer la question
const checkResponse = await fetch('/v1/usage/check', {
  headers: { 'Authorization': `Bearer ${token}` }
});

const { status, quota } = await checkResponse.json();

if (status === 'quota_exceeded') {
  // Afficher modal de mise à niveau
  showUpgradeModal({
    message: "Vous avez atteint votre limite mensuelle de 50 questions",
    plan: "Essential",
    upgradeUrl: "/pricing"
  });
  return; // Bloquer l'envoi
}

// Continuer avec l'envoi de la question
sendQuestion(userQuestion);
```

---

## Intégration LLM Service

Le service LLM (`llm/`) vérifie et incrémente automatiquement les quotas via des appels au backend API.

### Flux de traitement d'une question

```
1. Utilisateur pose une question via le frontend
2. Frontend appel /llm/chat avec { message, user_email } + Authorization header
3. LLM service vérifie le quota:
   - Appelle GET /api/v1/usage/check
   - Si quota dépassé, retourne 429 Too Many Requests
   - Si OK, continue le traitement
4. LLM génère la réponse
5. LLM incrémente le compteur:
   - Appelle POST /api/v1/usage/increment
   - Met à jour monthly_usage_tracking
6. Retourne la réponse au frontend
```

### Configuration LLM Service

Le service LLM nécessite la variable d'environnement suivante:

```bash
# URL du backend API pour quota checking
BACKEND_API_URL=https://expert.intelia.com/api
```

### Appel depuis le frontend vers LLM

Le frontend doit passer `user_email` et le token d'authentification:

```typescript
// Frontend: app/api/chat/stream/route.ts
const response = await fetch('https://expert.intelia.com/llm/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${userToken}`,  // 🔑 Token JWT
  },
  body: JSON.stringify({
    message: userQuestion,
    user_email: userEmail,  // 🔑 Email pour quota check
    conversation_id: sessionId,
    // ... autres paramètres
  })
});

// Gestion des erreurs de quota
if (response.status === 429) {
  const error = await response.json();
  // error.quota contient: questions_used, monthly_quota, etc.
  showQuotaExceededModal(error.quota);
}
```

### Endpoints utilisés par le LLM

**GET /v1/usage/check** (appelé avant traitement)
- Vérifie si l'utilisateur peut poser une question
- Retourne `can_ask: false` si quota dépassé

**POST /v1/usage/increment** (appelé après réponse)
- Body: `{ "success": true, "cost_usd": 0.0 }`
- Incrémente `questions_used` dans `monthly_usage_tracking`
- Marque `quota_exceeded_at` si limite atteinte

---

## Tests

### Mode DISABLE (développement)

```bash
# .env
STRIPE_MODE=disable

# Résultat: Aucune limite, développement libre
```

### Mode TEST (tester les quotas)

```bash
# .env
STRIPE_MODE=test
STRIPE_TEST_SECRET_KEY=sk_test_...
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_...

# Les quotas sont appliqués mais pas de vraie facturation
```

### Tester le dépassement de quota

```python
# Simuler 51 questions pour un utilisateur Essential
for i in range(51):
    try:
        check_user_quota("test@example.com")
        increment_question_count("test@example.com", success=True)
    except QuotaExceededException as e:
        print(f"Quota dépassé à la question {i+1}")
        print(e.usage_info)
        break
```

---

## Troubleshooting

### Problème: Les quotas ne sont pas appliqués

**Solution:**
1. Vérifiez `STRIPE_MODE` dans `.env`
   ```bash
   echo $STRIPE_MODE  # Doit être "production" ou "test"
   ```

2. Vérifiez `quota_enforcement` dans la base
   ```sql
   SELECT user_email, plan_name, quota_enforcement
   FROM user_billing_info
   WHERE plan_name = 'essential';
   ```

3. Vérifiez les logs
   ```bash
   # Le système log le mode au démarrage
   grep "MODE" logs/app.log
   ```

### Problème: Compteur ne s'incrémente pas

**Solution:**
1. Vérifiez que `monthly_usage_tracking` existe pour l'utilisateur
   ```sql
   SELECT * FROM monthly_usage_tracking
   WHERE user_email = 'user@example.com'
     AND month_year = '2025-01';
   ```

2. Si absent, créez manuellement ou relancez la migration

### Problème: Reset mensuel ne fonctionne pas

**Solution:**
1. Vérifiez que le CRON s'exécute
2. Testez manuellement:
   ```python
   from app.services.usage_limiter import reset_monthly_usage_for_all_users
   result = reset_monthly_usage_for_all_users()
   print(result)
   ```

---

## Monitoring

### Requêtes SQL utiles

```sql
-- Utilisateurs proches de leur limite (>80%)
SELECT
  user_email,
  questions_used,
  monthly_quota,
  ROUND((questions_used::float / monthly_quota) * 100, 1) as percentage
FROM monthly_usage_tracking
WHERE month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
  AND monthly_quota > 0
  AND questions_used >= (monthly_quota * 0.8)
ORDER BY percentage DESC;

-- Utilisateurs ayant dépassé leur quota
SELECT
  user_email,
  questions_used,
  monthly_quota,
  quota_exceeded_at
FROM monthly_usage_tracking
WHERE current_status = 'quota_exceeded'
  AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

-- Statistiques globales
SELECT
  COUNT(*) as total_users,
  SUM(questions_used) as total_questions,
  AVG(questions_used) as avg_per_user,
  COUNT(CASE WHEN current_status = 'quota_exceeded' THEN 1 END) as users_exceeded
FROM monthly_usage_tracking
WHERE month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');
```

---

## Résumé

✅ **Système complet de quotas mensuels**
- Essential: 50 questions/mois
- Pro/Elite: Illimité

✅ **3 modes Stripe** (Production/Test/Disable)

✅ **Endpoints API** pour le frontend

✅ **Reset automatique** le 1er de chaque mois

✅ **Monitoring** et statistiques

✅ **Documentation** complète
