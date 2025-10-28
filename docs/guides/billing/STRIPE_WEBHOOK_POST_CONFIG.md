# ✅ Étapes après configuration Cloudflare - Stripe Webhook

**Date** : 2025-10-16
**Prérequis** : Cloudflare configuré et webhook accessible

---

## 🎯 Checklist rapide

Une fois que l'administrateur réseau a configuré Cloudflare :

- [ ] Vérifier l'accessibilité du webhook
- [ ] Créer le webhook dans Stripe Dashboard
- [ ] Copier le secret de signature
- [ ] Ajouter le secret dans Digital Ocean
- [ ] Tester le webhook avec un événement test
- [ ] Tester un paiement complet

---

## 📝 Étapes détaillées

### Étape 1 : Vérifier l'accessibilité du webhook ✅

**Commande à exécuter** :
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

❌ **Si ça ne fonctionne pas** : Retourner voir l'administrateur réseau

✅ **Si ça fonctionne** : Passer à l'étape 2

---

### Étape 2 : Créer le webhook dans Stripe Dashboard 🔧

1. **Aller sur** : [Stripe Dashboard - Webhooks](https://dashboard.stripe.com/webhooks)

2. **Cliquer sur** : "Ajouter une destination" (ou "Add endpoint")

3. **Remplir le formulaire** :

   **URL du point de terminaison** :
   ```
   https://expert.intelia.com/v1/stripe/webhook
   ```

   **Description** (optionnel) :
   ```
   Intelia Expert - Production Webhook
   ```

4. **Sélectionner les comptes** :
   - ✅ **Votre compte** (cocher)
   - ❌ Comptes Connectés et v2 (ne PAS cocher)

5. **Version de l'API** :
   - Garder la version la plus récente affichée (ex: `2025-09-30.clover`)

6. **Sélectionner les événements** :

   Cliquer sur **"Sélectionner des événements"** et cocher :

   - ✅ `checkout.session.completed` - Paiement initial réussi
   - ✅ `customer.subscription.created` - Abonnement créé
   - ✅ `customer.subscription.updated` - Abonnement modifié
   - ✅ `customer.subscription.deleted` - Abonnement annulé
   - ✅ `invoice.payment_succeeded` - Paiement mensuel réussi
   - ✅ `invoice.payment_failed` - Échec de paiement

   **Total** : 6 événements

7. **Cliquer sur** : "Ajouter un point de terminaison" (ou "Add endpoint")

---

### Étape 3 : Copier le secret de signature 🔑

Une fois le webhook créé, Stripe affiche un **"Secret de signature"** (Signing secret).

**Format** : `whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

⚠️ **IMPORTANT** :
- Copier ce secret immédiatement
- Ne pas le partager publiquement
- Il sera nécessaire pour l'étape suivante

---

### Étape 4 : Ajouter le secret dans Digital Ocean 🌊

1. **Aller sur** : [Digital Ocean Apps](https://cloud.digitalocean.com/apps)

2. **Sélectionner** : `intelia-expert-backend` (ou le nom de votre app backend)

3. **Aller dans** : **Settings → App-Level Environment Variables**

4. **Cliquer sur** : "Edit" ou "Add Variable"

5. **Ajouter la variable** :
   - **Name** : `STRIPE_WEBHOOK_SECRET`
   - **Value** : `whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (le secret copié à l'étape 3)
   - **Scope** : `All components` (ou sélectionner le backend uniquement)
   - **Encrypt** : ✅ (cocher si disponible)

6. **Cliquer sur** : "Save"

7. **Redéployer l'application** :
   - Digital Ocean devrait proposer de redéployer automatiquement
   - Si ce n'est pas le cas, cliquer sur "Redeploy" manuellement

8. **Attendre la fin du déploiement** (~3-5 minutes)

---

### Étape 5 : Tester le webhook avec un événement test 🧪

1. **Retourner sur Stripe Dashboard** : [Webhooks](https://dashboard.stripe.com/webhooks)

2. **Cliquer sur le webhook** que vous venez de créer

3. **Onglet** : "Send test webhook"

4. **Sélectionner l'événement** : `checkout.session.completed`

5. **Cliquer sur** : "Send test webhook"

**Résultat attendu** :
- ✅ Statut : `200 OK`
- ✅ Réponse : `{"status": "success", "event_type": "checkout.session.completed"}`

**Logs à vérifier** (optionnel) :
- L'événement devrait apparaître dans les logs Digital Ocean du backend
- Rechercher : `📥 Webhook Stripe reçu`

❌ **Si ça échoue** :
- Vérifier que le `STRIPE_WEBHOOK_SECRET` est bien ajouté dans Digital Ocean
- Vérifier que le backend a bien été redéployé
- Vérifier les logs Digital Ocean pour voir l'erreur

---

### Étape 6 : Tester un paiement complet 💳

**Test avec une carte Stripe test** :

1. **Se connecter** à Intelia Expert : [https://expert.intelia.com](https://expert.intelia.com)

2. **Utiliser un compte de test** (ou créer un nouveau compte)

3. **Cliquer sur le menu utilisateur** → "Account Settings" (ou icône utilisateur)

4. **Cliquer sur** : "Upgrade to Pro" ou "Upgrade to Elite"

5. **Remplir le formulaire Stripe Checkout** :

   **Carte de test Stripe** :
   - **Numéro** : `4242 4242 4242 4242`
   - **Date d'expiration** : N'importe quelle date future (ex: `12/28`)
   - **CVC** : N'importe quel 3 chiffres (ex: `123`)
   - **Code postal** : N'importe quel code postal (ex: `12345`)

6. **Cliquer sur** : "Pay" ou "Payer"

**Vérifications à faire** :

- ✅ **Stripe Checkout s'affiche dans la bonne langue** (français si votre profil est en français)
- ✅ **Redirection après paiement** vers `/billing/success`
- ✅ **Message de succès** affiché avec compte à rebours
- ✅ **Redirection automatique** vers le chat après 5 secondes

7. **Vérifier le plan dans l'interface** :
   - Menu utilisateur → "Account Settings"
   - Le plan devrait être mis à jour : **Pro** ou **Elite**
   - Badge coloré visible avec le nom du plan

8. **Vérifier dans Stripe Dashboard** :
   - [Stripe Payments](https://dashboard.stripe.com/payments)
   - Le paiement test devrait apparaître
   - Statut : `Succeeded`

9. **Vérifier le webhook** :
   - [Stripe Webhooks](https://dashboard.stripe.com/webhooks)
   - Cliquer sur le webhook créé
   - Onglet "Events"
   - Vous devriez voir l'événement `checkout.session.completed` avec statut `200`

---

## 🎉 Félicitations !

Si toutes les étapes ci-dessus fonctionnent, **votre intégration Stripe est complète et opérationnelle** ! 🚀

---

## 🐛 Dépannage

### Problème : Le webhook retourne 401 Unauthorized

**Cause** : Le middleware d'authentification bloque encore le webhook

**Solution** : Vérifier que `/api/v1/stripe/webhook` est bien dans la whitelist `PUBLIC_ENDPOINTS` du fichier `backend/app/middleware/auth_middleware.py`

---

### Problème : Le webhook retourne 400 Invalid signature

**Cause** : Le `STRIPE_WEBHOOK_SECRET` est incorrect ou manquant

**Solution** :
1. Vérifier que la variable d'environnement est bien configurée dans Digital Ocean
2. Vérifier que le backend a été redéployé après l'ajout de la variable
3. Copier à nouveau le secret depuis Stripe Dashboard et le réajouter

---

### Problème : Le plan utilisateur n'est pas mis à jour après paiement

**Cause** : Le webhook est reçu mais la logique de traitement échoue

**Solution** :
1. Vérifier les logs Digital Ocean du backend
2. Rechercher les erreurs après `📥 Webhook Stripe reçu`
3. Vérifier que la base de données est accessible
4. Vérifier que les tables `stripe_subscriptions` et `user_billing_info` existent

---

### Problème : Stripe Checkout n'est pas dans la bonne langue

**Cause** : La locale n'est pas passée correctement

**Solution** :
1. Vérifier que l'utilisateur a bien sélectionné une langue dans les paramètres
2. La langue devrait être sauvegardée dans Supabase (`user_profile.language`)
3. Vérifier les logs frontend dans la console du navigateur

---

## 📚 Ressources utiles

- [Documentation Stripe Webhooks](https://docs.stripe.com/webhooks)
- [Stripe Testing Cards](https://docs.stripe.com/testing)
- [Stripe Checkout Localization](https://docs.stripe.com/payments/checkout/localizations)
- [Digital Ocean App Platform](https://docs.digitalocean.com/products/app-platform/)

---

## 📞 Contact

**Développeur** : Claude (AI Assistant)
**Repository** : `C:\intelia_gpt\intelia-expert`
**Branch** : `main`

**Dernier commit** :
```
5eb20bc6 - feat: Complete Stripe internationalization and add webhook setup guide
```

---

**Fin du document** - Bonne chance ! 🍀
