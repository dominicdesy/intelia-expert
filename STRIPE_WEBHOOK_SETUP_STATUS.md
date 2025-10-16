# 🔧 État de la configuration Stripe Webhook - Intelia Expert

**Date** : 2025-10-16
**Statut** : ⏸️ EN ATTENTE - Configuration réseau Cloudflare requise

---

## 📋 Résumé de la situation

Nous sommes en train de configurer les webhooks Stripe pour gérer les paiements automatiquement (abonnements Pro et Elite).

**Tout le code backend et frontend est prêt et déployé**, mais nous avons un **problème d'accès réseau** : **Cloudflare bloque les requêtes de Stripe vers notre endpoint webhook**.

---

## ✅ Ce qui est terminé

### 1. **Backend - API Stripe complète**
- ✅ Endpoints de création de checkout session
- ✅ Endpoints de gestion d'abonnements
- ✅ Webhook handler avec 6 événements supportés
- ✅ Authentification middleware configurée (webhook dans la whitelist)
- ✅ Base de données avec tables pour logs et événements
- ✅ Support de la localisation (14 langues Stripe)

**Fichiers modifiés** :
- `backend/app/api/v1/stripe_subscriptions.py` - Endpoints de paiement
- `backend/app/api/v1/stripe_webhooks.py` - Handler des webhooks
- `backend/app/middleware/auth_middleware.py` - Whitelist des webhooks
- `backend/app/api/v1/__init__.py` - Routing des webhooks

### 2. **Frontend - Interface de paiement complète**
- ✅ Modal d'upgrade de plan (UpgradePlanModal)
- ✅ Modal de gestion de compte (AccountModal)
- ✅ Pages de succès et d'annulation
- ✅ Support multilingue complet (16 langues)
- ✅ Passage de la langue utilisateur à Stripe

**Fichiers modifiés** :
- `frontend/app/chat/components/modals/UpgradePlanModal.tsx`
- `frontend/app/chat/components/modals/AccountModal.tsx`
- `frontend/app/billing/success/page.tsx`
- `frontend/app/billing/cancel/page.tsx`
- `frontend/lib/api/stripe.ts`

### 3. **Déploiement**
- ✅ Backend déployé sur Digital Ocean
- ✅ Frontend déployé
- ✅ Tous les commits pushés sur la branche `main`

---

## ❌ Problème actuel : Cloudflare bloque Stripe

### **Symptôme**
Impossible de créer le webhook dans le Stripe Dashboard car l'URL n'est pas accessible :
```
https://expert.intelia.com/v1/stripe/webhook
```

### **Cause**
Test effectué avec `curl` :
```bash
curl https://expert.intelia.com/v1/stripe/webhook/test
```

**Résultat** : Page Cloudflare "Sorry, you have been blocked"
**Cloudflare Ray ID** : `98fa019288f1a2a6`

Cloudflare considère que les requêtes vers `/v1/stripe/webhook` sont suspectes et les bloque.

---

## 🔧 Solutions possibles pour l'administrateur réseau

### **Option 1 : Page Rules Cloudflare (RECOMMANDÉE)**

Créer une **Page Rule** pour autoriser l'accès à l'endpoint webhook :

1. **Cloudflare Dashboard** → Sélectionner le domaine `intelia.com`
2. **Rules → Page Rules** → **Create Page Rule**
3. Configurer :
   - **URL Pattern** : `expert.intelia.com/v1/stripe/webhook*`
   - **Settings** :
     - ✅ **Security Level** : `Essentially Off`
     - ✅ **Browser Integrity Check** : `Off`
     - ✅ **Disable Apps** (si disponible)
   - **Save and Deploy**

**Avantage** : Gratuit, disponible sur tous les plans Cloudflare (3 règles gratuites)

---

### **Option 2 : Firewall Rules (si disponible)**

Si votre plan Cloudflare inclut les Firewall Rules :

1. **Cloudflare Dashboard** → `intelia.com`
2. **Security → Firewall Rules**
3. **Create a Firewall rule** :
   - **Name** : `Allow Stripe Webhooks`
   - **Expression** :
     ```
     (http.request.uri.path contains "/v1/stripe/webhook")
     ```
   - **Action** : `Allow`
   - **Deploy**

---

### **Option 3 : WAF Custom Rules (Plans Pro/Business)**

Si vous avez un plan payant avec WAF :

1. **Security → WAF → Custom rules**
2. **Create rule** :
   - **Name** : `Allow Stripe Webhooks`
   - **Expression** :
     ```
     (http.request.uri.path contains "/v1/stripe/webhook")
     ```
   - **Action** : `Allow`
   - **Deploy**

---

### **Option 4 : Whitelist des IPs Stripe**

Autoriser les plages IP de Stripe dans Cloudflare :

**IPs Stripe à whitelister** :
```
3.18.12.0/23
3.130.192.0/25
13.235.14.237/32
13.235.122.149/32
18.211.135.69/32
35.154.171.200/32
52.15.183.38/32
54.88.130.119/32
54.88.130.237/32
54.187.174.169/32
54.187.205.235/32
54.187.216.72/32
```

Créer une **IP Access Rule** :
1. **Security → WAF → Tools → IP Access Rules**
2. Ajouter chaque plage IP avec **Action** : `Allow`

---

### **Option 5 : Sous-domaine dédié sans proxy (TEMPORAIRE)**

Créer un sous-domaine spécifique pour les webhooks, sans protection Cloudflare :

1. **DNS → Add record**
   - **Type** : `A`
   - **Name** : `webhooks` (ou `api-stripe`)
   - **Content** : `[IP du serveur Digital Ocean]`
   - **Proxy status** : ⚪ **DNS only** (gris, pas orange)
   - **TTL** : `Auto`

2. Modifier l'URL du webhook dans le code backend (si nécessaire)

3. Utiliser l'URL : `https://webhooks.intelia.com/v1/stripe/webhook`

---

### **Option 6 : Désactiver temporairement le proxy Cloudflare**

**⚠️ SOLUTION TEMPORAIRE** (pas recommandée en production) :

1. **Cloudflare Dashboard** → DNS
2. Trouver l'enregistrement `expert.intelia.com`
3. Cliquer sur le **nuage orange** 🟠 pour le rendre **gris** ⚪
4. **Save**

**Impact** : Le serveur sera exposé directement sans protection Cloudflare

---

## 📝 Prochaines étapes (après résolution Cloudflare)

### 1. **Vérifier l'accès au webhook**

Une fois Cloudflare configuré, tester l'accessibilité :

```bash
curl -X GET https://expert.intelia.com/v1/stripe/webhook/test
```

**Résultat attendu** :
```json
{
  "status": "ok",
  "message": "Stripe webhook endpoint is ready",
  "signature_verification": "enabled",
  "timestamp": "2025-10-16T12:34:56.789012"
}
```

---

### 2. **Créer le webhook dans Stripe Dashboard**

1. **Stripe Dashboard** → **Developers → Webhooks**
2. **Ajouter une destination** (ou "Add endpoint")

**Configuration** :
- **URL du point de terminaison** : `https://expert.intelia.com/v1/stripe/webhook`
- **Description** : `Intelia Expert - Webhook production`
- **Événements de** : ✅ Votre compte
- **Version de l'API** : Dernière version (ex: 2025-09-30.clover)

**Événements à sélectionner** (6 événements) :
- ✅ `checkout.session.completed` - Paiement initial réussi
- ✅ `customer.subscription.created` - Abonnement créé
- ✅ `customer.subscription.updated` - Abonnement modifié
- ✅ `customer.subscription.deleted` - Abonnement annulé
- ✅ `invoice.payment_succeeded` - Paiement mensuel réussi
- ✅ `invoice.payment_failed` - Échec de paiement

3. **Enregistrer** et **copier le Secret de signature**

---

### 3. **Ajouter le secret webhook dans Digital Ocean**

Le secret commence par `whsec_...`

1. **Digital Ocean** → **Apps** → `intelia-expert-backend`
2. **Settings → App-Level Environment Variables**
3. **Add Variable** :
   - **Name** : `STRIPE_WEBHOOK_SECRET`
   - **Value** : `whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (copié depuis Stripe)
4. **Save** et **redéployer l'application**

---

### 4. **Tester le webhook**

Une fois le secret configuré et redéployé :

1. Dans **Stripe Dashboard → Webhooks**, sélectionner le webhook créé
2. Onglet **Send test webhook**
3. Choisir `checkout.session.completed`
4. **Send test webhook**

**Résultat attendu** : Statut `200 OK` et événement loggé dans la base de données.

---

### 5. **Test de paiement complet**

1. Se connecter à Intelia Expert avec un compte test
2. Cliquer sur "Upgrade to Pro" ou "Upgrade to Elite"
3. Utiliser une carte de test Stripe :
   - **Numéro** : `4242 4242 4242 4242`
   - **Date** : N'importe quelle date future
   - **CVC** : N'importe quel 3 chiffres
   - **ZIP** : N'importe quel code postal

**Vérifications** :
- ✅ Redirection vers Stripe Checkout dans la bonne langue
- ✅ Paiement réussi
- ✅ Redirection vers `/billing/success`
- ✅ Webhook reçu et traité
- ✅ Plan utilisateur mis à jour dans la base de données
- ✅ Accès aux fonctionnalités Pro/Elite débloqué

---

## 🔍 Détails techniques pour l'administrateur

### **Endpoint webhook détails**

- **URL complète** : `https://expert.intelia.com/v1/stripe/webhook`
- **Méthode HTTP** : `POST` (pour recevoir les événements)
- **Endpoint de test** : `GET https://expert.intelia.com/v1/stripe/webhook/test`
- **Authentification** : Signature Stripe (pas de JWT - bypass dans le middleware)
- **Headers Stripe** :
  - `stripe-signature` : Signature HMAC pour vérifier l'authenticité
  - `content-type: application/json`

### **Sécurité**

Le webhook est **déjà sécurisé** côté application :
- ✅ Vérification de signature Stripe via `STRIPE_WEBHOOK_SECRET`
- ✅ Whitelist dans le middleware d'authentification
- ✅ Logs de tous les événements reçus (table `stripe_webhook_logs`)
- ✅ Gestion des erreurs et retry automatique côté Stripe

**Le blocage Cloudflare est donc un surplus de sécurité non nécessaire pour cet endpoint.**

---

## 📞 Contact développeur

**Développeur** : Claude (AI Assistant)
**Utilisateur** : desy.dominic (Intelia Technologies)

**Dépôt Git** : `C:\intelia_gpt\intelia-expert`
**Branche** : `main`

**Derniers commits** :
```
0c804680 - fix: Prioritize Supabase language over localStorage on login
e8fde719 - fix: Force UserMenuButton re-render on language change
da42b476 - refactor: Remove date display from chat interface
8138265e - fix: Close user menu when language changes
```

---

## 📚 Documentation Stripe pertinente

- [Webhooks Stripe](https://docs.stripe.com/webhooks)
- [Testing Webhooks](https://docs.stripe.com/webhooks/test)
- [Webhook Endpoints](https://docs.stripe.com/webhooks/signatures)
- [Stripe IP Addresses](https://stripe.com/docs/ips)

---

## ✅ Checklist pour l'administrateur réseau

- [ ] Configurer Cloudflare pour autoriser `/v1/stripe/webhook*`
- [ ] Tester l'accessibilité : `curl https://expert.intelia.com/v1/stripe/webhook/test`
- [ ] Confirmer que le statut HTTP est `200 OK`
- [ ] Notifier l'équipe de développement

---

## 💬 Message pour l'administrateur réseau

Bonjour,

Nous intégrons les paiements Stripe dans notre application **Intelia Expert**. Le code backend et frontend est prêt et déployé, mais **Cloudflare bloque actuellement l'accès à notre endpoint webhook** nécessaire pour recevoir les notifications de paiement de Stripe.

**Pourriez-vous autoriser l'accès à l'URL suivante ?**
```
https://expert.intelia.com/v1/stripe/webhook
```

**Solutions recommandées** (par ordre de préférence) :
1. **Page Rule Cloudflare** pour désactiver la sécurité sur ce path spécifique
2. **Firewall Rule** pour whitelister l'endpoint
3. **Whitelist des IPs Stripe** (liste fournie ci-dessus)

L'endpoint est **déjà sécurisé** côté application avec vérification de signature cryptographique Stripe.

**Test de validation** :
```bash
curl -X GET https://expert.intelia.com/v1/stripe/webhook/test
```

Devrait retourner un JSON avec `"status": "ok"`.

Merci de votre aide !

---

**Fin du document** - Mise à jour : 2025-10-16
