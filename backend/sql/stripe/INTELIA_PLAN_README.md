# Plan Intelia - Guide d'utilisation

## Description

Le **plan Intelia** est un plan spécial réservé aux employés d'Intelia avec les caractéristiques suivantes :

- ✅ **Gratuit** (0.00$)
- ✅ **Illimité** (999,999 questions/mois)
- ✅ **Toutes les fonctionnalités** (Voice Realtime, analytics, API, etc.)
- 🔒 **Non visible publiquement** (caché des endpoints publics)
- 🔒 **Non assignable via l'interface** (protection contre l'auto-attribution)

## Installation

### 1. Créer le plan dans la base de données

Exécuter le script SQL :

```bash
psql "$DATABASE_URL" -f backend/sql/stripe/29_add_intelia_plan.sql
```

### 2. Vérifier la création

```sql
SELECT
    plan_name,
    display_name_en,
    monthly_quota,
    price_usd,
    features->>'employee_only' as employee_only,
    active
FROM billing_plans
WHERE plan_name = 'intelia';
```

Résultat attendu :
```
 plan_name | display_name_en | monthly_quota | price_usd | employee_only | active
-----------+-----------------+---------------+-----------+---------------+--------
 intelia   | Intelia Team    |        999999 |      0.00 | true          | t
```

## Assigner le plan à un employé

### Option 1 : SQL direct (recommandé)

```sql
-- Assigner le plan Intelia à un employé
UPDATE user_billing_info
SET
    plan_name = 'intelia',
    quota_enforcement = false,  -- Désactiver l'enforcement pour plus de sécurité
    updated_at = CURRENT_TIMESTAMP
WHERE user_email = 'employee@intelia.com';

-- Vérifier l'assignation
SELECT
    user_email,
    plan_name,
    custom_monthly_quota,
    quota_enforcement
FROM user_billing_info
WHERE user_email = 'employee@intelia.com';
```

### Option 2 : Via l'interface admin (future feature)

Créer un endpoint admin protégé pour assigner le plan :

```python
@router.post("/admin/assign-intelia-plan")
def assign_intelia_plan(
    user_email: str,
    current_user: dict = Depends(get_current_user)
):
    # Vérifier que current_user est super admin
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    # Assigner le plan
    with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE user_billing_info
                SET plan_name = 'intelia', quota_enforcement = false
                WHERE user_email = %s
            """, (user_email,))
            conn.commit()

    return {"success": True, "message": f"Plan Intelia assigné à {user_email}"}
```

## Comportement du plan

### 1. Vérification des quotas

Le code dans `billing.py` vérifie spécifiquement le plan Intelia :

```python
# Plan Intelia = illimité (employés)
if user_info["plan_name"] == "intelia":
    return True, {
        "status": "unlimited",
        "quota": "unlimited",
        "used": user_info["questions_used"] or 0,
        "remaining": "unlimited",
        "plan": "Intelia Team",
    }
```

Résultat : **Toutes les questions sont autorisées**, aucune limite appliquée.

### 2. Endpoints publics

Le plan Intelia est **caché** de l'endpoint `/api/v1/billing/plans` :

```sql
WHERE country_code = %s
  AND plan_name != 'intelia'  -- ✅ Filtré
```

Résultat : Les utilisateurs ne voient que Essential, Pro, Elite.

### 3. Changement de plan

Les utilisateurs **ne peuvent pas** s'auto-assigner le plan Intelia via `/api/v1/billing/change-plan` :

```python
if new_plan == "intelia":
    raise HTTPException(
        status_code=403,
        detail="Le plan Intelia est réservé aux employés."
    )
```

Résultat : Protection contre l'auto-attribution.

## Retirer le plan d'un employé

```sql
-- Rétrograder vers Essential
UPDATE user_billing_info
SET
    plan_name = 'essential',
    quota_enforcement = true,
    updated_at = CURRENT_TIMESTAMP
WHERE user_email = 'ex-employee@intelia.com';
```

## Liste des employés avec plan Intelia

```sql
SELECT
    user_email,
    plan_name,
    quota_enforcement,
    created_at,
    updated_at
FROM user_billing_info
WHERE plan_name = 'intelia'
ORDER BY updated_at DESC;
```

## Statistiques d'usage

```sql
-- Usage des employés Intelia ce mois-ci
SELECT
    ubi.user_email,
    mut.questions_used,
    mut.total_cost_usd,
    mut.month_year
FROM user_billing_info ubi
LEFT JOIN monthly_usage_tracking mut ON ubi.user_email = mut.user_email
WHERE ubi.plan_name = 'intelia'
  AND mut.month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
ORDER BY mut.questions_used DESC;
```

## Sécurité

✅ **Protection multicouche** :

1. ✅ Caché des endpoints publics (`/plans`)
2. ✅ Bloqué dans l'endpoint de changement de plan (`/change-plan`)
3. ✅ Assignation uniquement par SQL direct ou admin endpoint
4. ✅ Flag `employee_only: true` dans les features
5. ✅ Quota enforcement désactivé par défaut

## Notes importantes

⚠️ **Le plan Intelia est GRATUIT mais génère des coûts OpenAI**

- Les questions des employés consomment toujours des tokens OpenAI
- Monitorer les coûts via `monthly_usage_tracking.total_cost_usd`
- Si usage excessif, contacter l'employé

⚠️ **Pas de limite technique**

- 999,999 questions/mois = pratiquement illimité
- Mais chaque question coûte de l'argent (OpenAI)
- Usage responsable attendu des employés

## Support

Pour toute question sur le plan Intelia :
- Email: admin@intelia.com
- Documentation: /backend/sql/stripe/INTELIA_PLAN_README.md
