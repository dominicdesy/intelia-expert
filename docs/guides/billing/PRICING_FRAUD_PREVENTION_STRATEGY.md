# 🛡️ Stratégie Anti-Fraude pour les Prix Régionalisés

## 📋 Vue d'Ensemble

Ce document décrit la stratégie complète pour empêcher les utilisateurs de contourner les prix régionalisés via VPN ou manipulation de localisation.

---

## 🎯 Le Problème

**Scénario de fraude :**
1. Utilisateur canadien (devrait payer $18/mois)
2. Utilise un VPN thaïlandais
3. Voit les prix thaïlandais ($5/mois)
4. S'abonne au prix thaïlandais
5. **Fraude : économise $13/mois** ❌

---

## ✅ La Solution : Séparation Pricing Tier / Billing Currency

### **Concept Clé**

```
┌────────────────────────────────────────────────────────┐
│  PRICING TIER (verrouillé)      ≠  BILLING CURRENCY   │
│                                     (choix libre)       │
├────────────────────────────────────────────────────────┤
│                                                         │
│  Tier 1 : $18/mois               →  USD, CAD, EUR...  │
│  (Canada, USA, Europe)                                 │
│                                                         │
│  Tier 2 : $12/mois               →  BRL, MXN, CNY...  │
│  (Brésil, Mexique, Chine)                              │
│                                                         │
│  Tier 3 : $5/mois                →  THB, INR, VND...  │
│  (Thaïlande, Inde, Vietnam)                            │
│                                                         │
└────────────────────────────────────────────────────────┘
```

**Exemple :**
- Canadien → **Tier 1** (verrouillé) → Paie $18 USD **OU** $24 CAD **OU** €16 EUR
- Thaïlandais → **Tier 3** (verrouillé) → Paie $5 USD **OU** 175 THB

---

## 🔒 Système de Sécurité Multi-Niveaux

### **Niveau 1 : Tracking à l'Inscription** 🎯

**Quand ?** Dès que l'utilisateur crée son compte

**Quoi ?**
- Détecte le pays via l'IP
- Enregistre dans `signup_country` (jamais modifié)
- Détermine le `pricing_tier` initial
- **Ce pays devient la référence de base**

```python
# Exemple : Utilisateur s'inscrit depuis le Canada
signup_country = "CA"
pricing_tier = "tier1"  # $18/mois
```

**Implémentation :**
```python
# Dans /register endpoint
await CountryTrackingService.track_signup(user_email, request)
```

---

### **Niveau 2 : Logging de Chaque Connexion** 📊

**Quand ?** À chaque fois qu'un utilisateur se connecte

**Quoi ?**
- IP et pays détecté
- Device (desktop/mobile/tablet)
- Browser & OS
- Détection VPN/Proxy/Tor
- Calcul du **risk_score** (0-100)

**Table `user_login_history` :**
```sql
| login_at            | ip_address    | country_code | is_vpn | risk_score |
|---------------------|---------------|--------------|--------|------------|
| 2025-01-15 10:00    | 142.1.x.x     | CA           | false  | 0          |
| 2025-01-16 14:30    | 142.1.x.x     | CA           | false  | 0          |
| 2025-01-17 08:00    | 101.2.x.x     | TH           | true   | 75         | ⚠️
```

**Implémentation :**
```python
# Dans /login endpoint
await CountryTrackingService.track_login(user_email, request, "password")
```

---

### **Niveau 3 : Verrouillage du Pricing Tier** 🔐

**Quand ?** Au moment du **premier abonnement payant**

**Comment ?**
1. Analyse l'historique :
   - Pays d'inscription (`signup_country`)
   - Pays le plus fréquent dans `user_login_history`
   - Pays actuel
2. Détecte les incohérences :
   ```
   signup_country = CA
   most_common_login_country = CA (90% des connexions)
   current_country = TH (via VPN)

   → SUSPECT ! Verrouiller sur CA (Tier 1)
   ```
3. Verrouille le `pricing_tier` et `pricing_country`
4. **Une fois verrouillé, ne peut plus être changé** (sauf support client)

**Implémentation :**
```python
# Avant de créer une Stripe Checkout Session
await CountryTrackingService.lock_pricing_tier(user_email, request)
```

---

### **Niveau 4 : Validation au Checkout** ✅

**Quand ?** Juste avant la redirection vers Stripe

**Vérifications :**
1. Le `pricing_tier` est-il verrouillé ?
2. Le pays actuel correspond-il au `pricing_country` ?
3. Y a-t-il des signaux de fraude (VPN, changements de pays fréquents) ?

**Si incohérence détectée :**
```python
if current_country != pricing_country and risk_score > 50:
    raise HTTPException(
        status_code=403,
        detail="Location verification failed. Please contact support."
    )
```

---

### **Niveau 5 : Stripe Radar (Automatique)** 🤖

Stripe détecte automatiquement :
- Pays de la carte bancaire ≠ pays de facturation
- Patterns de fraude connus
- VPN/Proxy suspects
- Achats inhabituels

**Action :** Stripe peut bloquer ou demander une vérification 3D Secure

---

## 📊 Analyse de Fraude

### **Vue SQL : `user_fraud_risk_analysis`**

Détecte automatiquement les utilisateurs suspects :

```sql
SELECT * FROM user_fraud_risk_analysis
WHERE calculated_risk_score > 50
ORDER BY calculated_risk_score DESC;
```

**Indicateurs de risque :**
- ✅ **0-30 :** Faible risque (normal)
- ⚠️ **31-60 :** Risque moyen (surveiller)
- 🚨 **61-100 :** Risque élevé (potentielle fraude)

**Facteurs de risque :**
| Facteur | Points |
|---------|--------|
| Utilisation VPN | +30 |
| Utilisation Proxy | +25 |
| Utilisation Tor | +40 |
| signup_country ≠ pricing_country | +30 |
| Connexion pays ≠ signup | +15 |
| > 3 pays différents en 7 jours | +20 |

---

## 🚀 Implémentation

### **1. Exécuter la migration SQL**

```bash
psql $DATABASE_URL -f backend/sql/stripe/27_add_country_tracking.sql
```

### **2. Modifier les endpoints**

**a) /register (Inscription)**
```python
# auth.py
from app.services.country_tracking_service import CountryTrackingService

@router.post("/register")
async def register_user(user_data: UserRegister, request: Request):
    # ... existing code ...

    # Track signup country
    signup_info = await CountryTrackingService.track_signup(
        user.email,
        request
    )

    logger.info(f"User registered from {signup_info['signup_country']}")
```

**b) /login (Connexion)**
```python
@router.post("/login")
async def login(request: LoginRequest, http_request: Request):
    # ... existing authentication ...

    # Track login
    login_info = await CountryTrackingService.track_login(
        user_email,
        http_request,
        login_method="password"
    )

    if login_info.get("is_suspicious"):
        logger.warning(f"Suspicious login for {user_email}")
```

**c) /create-checkout (Stripe)**
```python
@router.post("/create-checkout")
async def create_stripe_checkout(
    plan: str,
    current_user: dict,
    request: Request
):
    # Lock pricing tier before first subscription
    pricing_info = await CountryTrackingService.lock_pricing_tier(
        current_user["email"],
        request
    )

    # Get price for locked tier
    price_id = get_stripe_price_id(pricing_info["pricing_tier"], plan)

    # Create Stripe session with correct price
    session = stripe.checkout.Session.create(
        price=price_id,
        ...
    )
```

### **3. Créer les endpoints d'analyse**

```python
# billing.py

@router.get("/fraud-analysis")
async def get_fraud_analysis(
    current_user: dict = Depends(get_current_user)
):
    """Get fraud risk analysis for current user"""
    return await CountryTrackingService.get_user_fraud_analysis(
        current_user["email"]
    )

@router.get("/admin/fraud-report")
async def get_fraud_report(
    current_user: dict = Depends(get_current_super_admin)
):
    """Get list of high-risk users (admin only)"""
    # Query user_fraud_risk_analysis view
    # Return users with risk_score > 50
```

---

## 🎨 Expérience Utilisateur

### **Scénario Normal (Pas de fraude)**

1. Utilisateur canadien s'inscrit → **Tier 1** détecté
2. Se connecte toujours du Canada → **Risk: 0**
3. Choisit **Billing Currency = CAD**
4. Voit le prix **$24 CAD/mois** (équivalent $18 USD)
5. S'abonne → **Pricing Tier verrouillé sur Tier 1**
6. ✅ **Expérience fluide**

### **Scénario Voyageur Légitime**

1. Utilisateur canadien s'inscrit → **Tier 1**
2. Voyage en Thaïlande → Connexion depuis TH
3. Risk score augmente légèrement (+15)
4. Mais historique montre 90% connexions depuis CA
5. Au checkout → **Tier 1 maintenu** (basé sur signup_country)
6. ✅ **Pas de blocage pour les voyageurs**

### **Scénario Fraude (VPN)**

1. Utilisateur canadien s'inscrit depuis CA → **Tier 1**
2. Utilise VPN thaïlandais pour se connecter
3. **is_vpn=true** détecté → Risk +30
4. Pays change de CA → TH → Risk +15
5. Total: **Risk = 45** (moyen)
6. Au checkout :
   - Système détecte incohérence
   - Verrouille sur **Tier 1** (pays d'inscription)
   - Affiche prix **$18 USD**
7. ❌ **Fraude empêchée !**

---

## 📈 Monitoring

### **Métriques à Surveiller**

1. **Nombre d'utilisateurs par tier**
   ```sql
   SELECT pricing_tier, COUNT(*)
   FROM user_billing_info
   WHERE pricing_locked_at IS NOT NULL
   GROUP BY pricing_tier;
   ```

2. **Utilisateurs à risque élevé**
   ```sql
   SELECT COUNT(*)
   FROM user_fraud_risk_analysis
   WHERE calculated_risk_score > 60;
   ```

3. **Patterns de connexion suspects**
   ```sql
   SELECT user_email, COUNT(DISTINCT country_code) as countries
   FROM user_login_history
   WHERE login_at > NOW() - INTERVAL '30 days'
   GROUP BY user_email
   HAVING COUNT(DISTINCT country_code) > 5;
   ```

---

## 🎯 Résultat Final

### **Protection Complète**

✅ **Détection précoce** : Pays capturé dès l'inscription
✅ **Tracking continu** : Chaque connexion loguée
✅ **Verrouillage sécurisé** : Pricing tier basé sur historique, pas IP actuelle
✅ **Multi-sources** : Signup + Login history + Stripe card country
✅ **Monitoring** : Alertes automatiques pour cas suspects

### **Sans Faille**

🚫 **VPN simple** → Détecté et bloqué
🚫 **Changement de pays fréquent** → Risk score élevé
🚫 **Inscription VPN + Connexions normales** → Historique révèle le vrai pays
🚫 **Carte bancaire d'un autre pays** → Stripe Radar alerte

### **UX Préservée**

✅ **Voyageurs légitimes** → Pas de blocage
✅ **Expatriés** → Tier basé sur signup_country
✅ **Choix de devise libre** → Utilisateur choisit CAD, USD, EUR, etc.
✅ **Transparent** → Utilisateur ne voit pas la complexité

---

## 🔧 Prochaines Étapes

1. ✅ Exécuter migration SQL (27_add_country_tracking.sql)
2. ⏳ Modifier /register pour tracker signup
3. ⏳ Modifier /login pour logger chaque connexion
4. ⏳ Modifier /create-checkout pour verrouiller pricing tier
5. ⏳ Créer endpoints d'analyse de fraude
6. ⏳ Tester en staging
7. ⏳ Déployer en production
8. ⏳ Monitorer les premiers jours

---

**Questions ?** Ce système vous semble-t-il complet et sécurisé ?
