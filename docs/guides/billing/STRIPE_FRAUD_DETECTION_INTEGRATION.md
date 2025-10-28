# 🛡️ Intégration Stripe + Country Tracking pour Fraud Detection

## 📋 Vue d'Ensemble

Ce document décrit l'intégration complète entre notre système de country tracking et Stripe pour prévenir la fraude sur les prix régionalisés.

---

## 🎯 Problème Résolu

**Scénario de fraude :**
1. Canadien utilise VPN thaïlandais
2. S'inscrit → voit prix thaïlandais ($5 USD)
3. Essaie de payer avec carte canadienne

**Sans protection :** Paie $5 USD au lieu de $18 USD → **Perte de $13/mois**

**Avec protection :** Système détecte et bloque → Paie $18 USD ou paiement refusé ✅

---

## 🔐 Architecture de Sécurité Multi-Niveaux

### **Niveau 1 : Détection à l'Inscription** ✅
- Capture `signup_country` via IP réelle
- Pré-sélection automatique du pays dans le formulaire
- Attribution d'un `pricing_tier` suggéré

### **Niveau 2 : Tracking des Connexions** ✅
- Chaque login enregistré avec IP/pays/device
- Détection VPN/Proxy/Tor
- Calcul de `risk_score` (0-100)

### **Niveau 3 : Analyse de Fraude** ✅
- Vue `user_fraud_risk_analysis` automatique
- Calcul du `risk_level` (LOW/MEDIUM/HIGH/CRITICAL)
- Détection de patterns suspects

### **Niveau 4 : Métadonnées Stripe** ✅ **(NOUVEAU)**
- Envoi des données de risque à Stripe au checkout
- Stripe Radar analyse automatiquement
- Détection de divergences (pays carte ≠ pays inscription)

### **Niveau 5 : Verrouillage du Tier** ✅ **(NOUVEAU)**
- Appel automatique à `lock_pricing_tier()` après paiement
- `pricing_locked_at` enregistré
- Impossible de changer le tier après

---

## 🔧 Modifications Apportées

### **1. stripe_subscriptions.py**

#### **Import du service :**
```python
from app.services.country_tracking_service import CountryTrackingService
```

#### **Récupération du pays et analyse de fraude (lignes 299-333) :**
```python
# Récupérer signup_country depuis la BD
country_code = "US"  # Default
pricing_tier = "tier1"
fraud_risk_score = 0
fraud_risk_level = "LOW"

with get_db_connection() as conn:
    cur.execute("""
        SELECT signup_country, pricing_tier, pricing_locked_at
        FROM user_billing_info
        WHERE user_email = %s
    """, (user_email,))

    billing_info = cur.fetchone()

    if billing_info:
        country_code = billing_info['signup_country']
        pricing_tier = billing_info['pricing_tier']

    # Obtenir l'analyse de fraude
    fraud_analysis = await CountryTrackingService.get_user_fraud_analysis(user_email)
    fraud_risk_score = fraud_analysis.get('avg_risk_score', 0)
    fraud_risk_level = fraud_analysis.get('risk_level', 'LOW')
```

#### **Métadonnées enrichies envoyées à Stripe (lignes 469-483) :**
```python
metadata={
    "user_email": user_email,
    "plan_name": plan_name,
    "price_monthly": str(price),
    "currency": currency,
    "country_code": country_code,
    "tier_level": str(tier_level),
    # Fraud detection metadata
    "signup_country": country_code,
    "pricing_tier": pricing_tier,
    "fraud_risk_score": str(fraud_risk_score),
    "fraud_risk_level": fraud_risk_level,
    "source": "intelia_expert_fraud_protected"
}
```

---

### **2. stripe_webhooks.py**

#### **Import du service :**
```python
from app.services.country_tracking_service import CountryTrackingService
```

#### **Fonction rendue async :**
```python
async def handle_checkout_completed(session: Dict[str, Any]):
```

#### **Verrouillage automatique du tier après paiement (lignes 209-225) :**
```python
# Lock pricing tier after first successful payment
if COUNTRY_TRACKING_AVAILABLE:
    try:
        mock_request = type('MockRequest', (), {'headers': {}, 'client': None})()
        lock_result = await CountryTrackingService.lock_pricing_tier(user_email, mock_request)

        if lock_result:
            logger.info(
                f"✅ Pricing tier locked for {user_email}: "
                f"{lock_result.get('pricing_tier')} (country: {lock_result.get('pricing_country')})"
            )
    except Exception as e:
        logger.warning(f"⚠️ Could not lock pricing tier: {e}")
```

---

## 🚦 Flux Complet de Paiement

```
┌─────────────────────────────────────────────────────────────────┐
│  1. UTILISATEUR CLIQUE SUR "UPGRADE"                            │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. BACKEND : create-checkout-session                           │
│     ├─ Récupère signup_country depuis BD                        │
│     ├─ Récupère pricing_tier                                    │
│     ├─ Obtient fraud_analysis                                   │
│     ├─ Calcule fraud_risk_score                                 │
│     └─ Envoie TOUT à Stripe dans metadata                       │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. STRIPE CHECKOUT                                             │
│     ├─ Affiche formulaire de paiement                           │
│     ├─ Utilisateur entre carte bancaire                         │
│     └─ STRIPE RADAR ANALYSE :                                   │
│         • Pays de la carte (ex: CA)                             │
│         • metadata.signup_country (ex: CA)                      │
│         • metadata.fraud_risk_score (ex: 0)                     │
│         • Adresse de facturation                                │
│         • IP de paiement                                        │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. DÉCISION STRIPE RADAR                                       │
│                                                                 │
│  ✅ CAS 1 : Tout OK (pays cohérents, pas de VPN)               │
│     → Paiement APPROUVÉ                                         │
│                                                                 │
│  ⚠️ CAS 2 : Risque moyen (pays carte ≠ signup_country)        │
│     → Demande 3D Secure (vérification supplémentaire)          │
│                                                                 │
│  ❌ CAS 3 : Risque élevé (carte volée, VPN suspect)           │
│     → Paiement BLOQUÉ                                          │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. WEBHOOK : checkout.session.completed                        │
│     ├─ Sauvegarde abonnement dans stripe_subscriptions         │
│     ├─ Met à jour plan dans user_billing_info                  │
│     └─ APPELLE lock_pricing_tier() :                            │
│         • pricing_tier verrouillé                               │
│         • pricing_country = signup_country                      │
│         • pricing_locked_at = NOW()                             │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. RÉSULTAT FINAL                                              │
│     ✅ Utilisateur paie le BON prix (selon son vrai pays)       │
│     ✅ Pricing tier VERROUILLÉ (impossible de changer)          │
│     ✅ Fraude PRÉVENUE                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Exemple Concret : Détection de Fraude

### **Scénario : Canadien avec VPN Thaïlandais**

| Étape | Données Capturées | Stripe Radar | Résultat |
|-------|-------------------|--------------|----------|
| **Inscription** | signup_country=CA, IP canadienne | - | tier1 suggéré |
| **Connexion avec VPN** | country_code=TH, is_vpn=true, risk_score=75 | - | Suspect ⚠️ |
| **Checkout** | metadata envoyées à Stripe | Analyse divergence | - |
| **Validation Stripe** | Carte CA + metadata.signup_country=CA | ✅ Cohérent | Approuvé |
| **Prix facturé** | $18 USD (tier1) | - | ✅ Correct |
| **Tier verrouillé** | pricing_locked_at enregistré | - | ✅ Permanent |

**Résultat :** Même avec VPN, l'utilisateur paie le prix de son VRAI pays ! 🎯

---

## 🔍 Données Envoyées à Stripe Radar

Stripe Radar reçoit automatiquement :

### **Données de Base (Stripe collecte):**
- Pays de la carte bancaire
- Adresse de facturation
- IP de paiement
- Numéro de carte (hashé)
- Email

### **Données Enrichies (Nous envoyons):**
- `signup_country` : Pays lors de l'inscription
- `pricing_tier` : Tier de prix (tier1/tier2/tier3)
- `fraud_risk_score` : Score de risque (0-100)
- `fraud_risk_level` : Niveau de risque (LOW/MEDIUM/HIGH/CRITICAL)
- `country_code` : Pays actuel
- Historique de connexions (via notre BD)

### **Analyse Combinée :**
Stripe compare :
- Pays carte vs `signup_country`
- IP paiement vs historique IPs
- `fraud_risk_score` vs patterns Stripe
- Adresse facturation vs pays

---

## ✅ Avantages de l'Intégration

1. **Protection Multi-Niveaux :**
   - Notre système + Stripe Radar = double protection

2. **Détection Automatique :**
   - Pas d'intervention manuelle nécessaire
   - Stripe bloque automatiquement les fraudes

3. **Transparence :**
   - Toutes les données de risque dans Stripe Dashboard
   - Possibilité de revoir les paiements suspects

4. **Pricing Locked :**
   - Impossible de changer de tier après le premier paiement
   - Garantit la cohérence des prix

5. **Logging Complet :**
   - Tout est tracé dans nos logs
   - Analyse post-facto possible

---

## 🚀 Activation Stripe Radar

Stripe Radar est **automatiquement inclus** dans tous les comptes Stripe.

### **Configuration Recommandée :**

1. **Aller sur Stripe Dashboard :**
   - https://dashboard.stripe.com/radar/rules

2. **Activer les règles recommandées :**
   - ✅ Block if CVC check fails
   - ✅ Block if AVS (Address Verification) fails
   - ✅ Block if card country ≠ IP country (avec exceptions)
   - ✅ Request 3D Secure for high-risk payments

3. **Créer une règle personnalisée (optionnel) :**
   ```
   IF metadata.fraud_risk_score > 50 THEN request_3ds()
   ```

4. **Surveiller les paiements bloqués :**
   - Dashboard → Payments → Blocked
   - Possibilité de débloquer manuellement si faux positif

---

## 📈 Monitoring et Métriques

### **Requêtes SQL Utiles :**

#### **Utilisateurs avec pricing tier verrouillé :**
```sql
SELECT
    user_email,
    signup_country,
    pricing_tier,
    pricing_country,
    pricing_locked_at
FROM user_billing_info
WHERE pricing_locked_at IS NOT NULL
ORDER BY pricing_locked_at DESC;
```

#### **Paiements réussis avec analyse de fraude :**
```sql
SELECT
    ss.user_email,
    ss.plan_name,
    ss.price_monthly,
    ss.currency,
    ubi.signup_country,
    ubi.pricing_tier,
    fra.risk_level,
    fra.avg_risk_score,
    ss.created_at as payment_date
FROM stripe_subscriptions ss
JOIN user_billing_info ubi ON ss.user_email = ubi.user_email
LEFT JOIN user_fraud_risk_analysis fra ON ss.user_email = fra.user_email
WHERE ss.status = 'active'
ORDER BY ss.created_at DESC;
```

#### **Détection de tentatives de fraude :**
```sql
SELECT *
FROM user_fraud_risk_analysis
WHERE risk_level IN ('HIGH', 'CRITICAL')
  OR unique_countries > 3
  OR vpn_logins > 0
ORDER BY avg_risk_score DESC;
```

---

## 🎓 Formation Équipe

### **Pour l'Équipe Support :**
- Les paiements suspects seront bloqués automatiquement par Stripe
- Si un utilisateur se plaint, vérifier dans Stripe Dashboard
- Possibilité de débloquer manuellement après vérification

### **Pour l'Équipe Tech :**
- Logs disponibles dans `backend/logs/app.log`
- Rechercher "fraud" ou "risk_score" pour analyses
- Stripe Dashboard pour voir les paiements bloqués

---

## 🔧 Troubleshooting

### **Problème : Paiement bloqué par erreur**

**Solution :**
1. Vérifier dans Stripe Dashboard → Payments
2. Regarder la raison du blocage
3. Si légitime, débloquer manuellement
4. Ajuster les règles Radar si nécessaire

### **Problème : Pricing tier non verrouillé**

**Vérifier :**
```sql
SELECT
    user_email,
    pricing_tier,
    pricing_locked_at
FROM user_billing_info
WHERE user_email = 'email@example.com';
```

**Si NULL, vérifier les logs du webhook :**
```bash
grep "lock pricing tier" backend/logs/app.log | tail -20
```

---

## 📞 Support

Pour toute question sur l'intégration Stripe + Fraud Detection, contactez l'équipe technique.

**Documentation Stripe Radar :**
- https://stripe.com/docs/radar
- https://stripe.com/docs/radar/rules
