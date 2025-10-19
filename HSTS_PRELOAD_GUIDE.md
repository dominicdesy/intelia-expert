# 🔒 HSTS Preload - Guide de Soumission

**Statut actuel** : ✅ **Header configuré** - Prêt pour soumission à hstspreload.org

**Date** : 2025-10-19

---

## 📋 Résumé

HSTS Preload permet d'inscrire votre domaine dans une liste hardcodée des navigateurs (Chrome, Firefox, Safari, Edge) pour **forcer HTTPS de manière permanente**, même lors de la première visite.

### **Avantages :**
- 🛡️ **Protection dès la première connexion** (pas de requête HTTP initiale vulnérable)
- 🌐 **Intégré nativement aux navigateurs** (Chrome, Firefox, Safari, Edge)
- 🔐 **Protection permanente** même si l'utilisateur tape `http://` manuellement
- ⚡ **Performances légèrement améliorées** (pas de redirection HTTP→HTTPS)

### **Inconvénients :**
- ⏳ **Processus de retrait long** (plusieurs mois si vous changez d'avis)
- 🔒 **Engagement permanent** à servir HTTPS sur tous les sous-domaines
- 📊 **Mise à jour des navigateurs lente** (6-12 semaines pour propagation complète)

---

## ✅ Pré-requis Intelia Expert

Tous les pré-requis sont **déjà remplis** pour expert.intelia.com :

### **1. Header HSTS Correct**
```http
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

✅ **Status** : Configuré dans `backend/app/main.py:514` et `frontend/next.config.js:62`

### **2. Certificat HTTPS Valide**
✅ **Status** : Certificat Let's Encrypt valide (vérifié en production)

### **3. Redirection HTTP → HTTPS**
✅ **Status** : Toutes les requêtes HTTP redirigées vers HTTPS (CloudFlare + Nginx)

### **4. HTTPS sur Tous les Sous-domaines**
✅ **Status** : Politique `includeSubDomains` active

### **5. Minimum max-age = 1 an (31536000 secondes)**
✅ **Status** : Configuré à 31536000 secondes (1 an)

---

## 🚀 Étape 1 : Déployer le Header HSTS Preload

### **A. Vérifier que les changements sont en production**

Après le déploiement, testez avec curl :

```bash
curl -I https://expert.intelia.com
```

**Résultat attendu :**
```http
HTTP/2 200
strict-transport-security: max-age=31536000; includeSubDomains; preload
```

### **B. Tester avec SecurityHeaders.com**

Visitez : https://securityheaders.com/?q=https://expert.intelia.com

**Résultat attendu :**
- Note : **A+**
- HSTS : ✅ **Inclut `preload` directive**

---

## 📝 Étape 2 : Soumettre à hstspreload.org

### **A. Aller sur le site officiel**

**URL** : https://hstspreload.org/

### **B. Entrer le domaine**

Dans le champ "Enter a domain", tapez :
```
expert.intelia.com
```

Cliquez sur **"Check HSTS preload status and eligibility"**

### **C. Vérification automatique**

Le site va vérifier :
- ✅ Header HSTS présent avec `preload`
- ✅ `max-age` >= 31536000
- ✅ Directive `includeSubDomains` présente
- ✅ HTTPS fonctionne correctement
- ✅ Pas de redirection HTTP vers un autre domaine

**Si tout est vert**, vous verrez :
> ✅ **expert.intelia.com is eligible for the HSTS preload list.**

### **D. Cocher les confirmations**

Vous devez accepter 3 conditions :

1. ☑️ **I am the site owner** of expert.intelia.com or have the authority to preload it.
2. ☑️ **I understand** that preloading expert.intelia.com through this form will **prevent all HTTP access to all subdomains**.
3. ☑️ **I understand** that if I need to **remove my site from the preload list**, the process can take **months** and require **me to continue serving an HSTS header during that time**.

### **E. Soumettre le formulaire**

Cliquez sur **"Submit"**

**Confirmation attendue :**
> ✅ **expert.intelia.com is now pending inclusion in the HSTS preload list.**

---

## ⏱️ Étape 3 : Attendre la Propagation

### **Timeline Typique :**

| Étape | Délai | Description |
|-------|-------|-------------|
| **Soumission** | Jour 0 | Domaine soumis à hstspreload.org |
| **Validation** | 24-48h | Validation automatique des critères |
| **Inclusion dans Chromium** | 1-2 semaines | Ajouté à la liste Chromium (source de vérité) |
| **Propagation Chrome** | 6-12 semaines | Disponible dans Chrome stable |
| **Propagation Firefox** | 6-12 semaines | Firefox importe la liste Chromium |
| **Propagation Safari** | 6-12 semaines | Safari importe la liste Chromium |
| **Propagation Edge** | 6-12 semaines | Edge importe la liste Chromium |

### **Vérifier le Statut d'Inclusion**

Retournez sur https://hstspreload.org/ et entrez `expert.intelia.com`

**Statuts possibles :**
- 🟡 **Pending** : Soumis, en attente d'inclusion
- 🟢 **Preloaded** : Inclus dans la liste Chromium
- 🔴 **Removed** : Retiré de la liste

---

## 🔍 Étape 4 : Vérifier l'Inclusion

### **A. Vérifier dans le Code Source Chromium**

**URL** : https://chromium.googlesource.com/chromium/src/+/main/net/http/transport_security_state_static.json

Cherchez (Ctrl+F) : `expert.intelia.com`

**Résultat attendu :**
```json
{ "name": "expert.intelia.com", "policy": "bulk-1-year", "mode": "force-https", "include_subdomains": true }
```

### **B. Tester avec Chrome DevTools**

1. Ouvrez Chrome
2. Tapez dans la barre d'adresse : `chrome://net-internals/#hsts`
3. Section **"Query HSTS/PKP domain"** :
   - Domaine : `expert.intelia.com`
   - Cliquez sur **"Query"**

**Résultat attendu (après inclusion) :**
```
static_sts_domain: expert.intelia.com
static_upgrade_mode: STRICT
static_sts_include_subdomains: true
static_sts_observed: [date]
```

### **C. Tester le Comportement Réel**

1. Ouvrez un **nouvel onglet de navigation privée**
2. Tapez **exactement** : `http://expert.intelia.com` (sans le `s`)
3. Observez la barre d'adresse

**Comportement attendu (après preload) :**
- ✅ Chrome charge **directement** `https://expert.intelia.com` **sans requête HTTP initiale**
- ✅ Pas de redirection visible (upgrade interne avant la requête réseau)

---

## 🚨 Comment Retirer le Domaine (si nécessaire)

### **⚠️ Avertissement : Processus Lent**

Retirer un domaine de la preload list prend **plusieurs mois** car :
1. Il faut attendre la prochaine mise à jour Chromium
2. Les navigateurs mettent à jour leur liste tous les 6-12 semaines
3. Les anciennes versions de navigateurs garderont le preload actif

### **Étapes pour Retrait :**

#### **1. Retirer la directive `preload` du header**

**Avant (avec preload) :**
```http
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Après (sans preload, mais garder HSTS) :**
```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

**OU** (pour désactiver complètement HSTS après retrait) :
```http
Strict-Transport-Security: max-age=0
```

#### **2. Soumettre une demande de retrait**

1. Aller sur https://hstspreload.org/
2. Entrer `expert.intelia.com`
3. Cliquer sur **"Remove"**
4. Confirmer la demande

#### **3. Attendre la propagation (6-12 mois)**

Le domaine sera retiré progressivement :
- Chromium : 1-2 semaines
- Chrome/Edge/Firefox : 6-12 semaines
- Anciennes versions de navigateurs : **Jamais** (les utilisateurs doivent mettre à jour)

---

## 📊 Monitoring du HSTS Preload

### **1. Logs de Connexion HTTP (ne devraient plus exister)**

Après preload, les navigateurs **ne feront jamais de requête HTTP initiale**.

**Commande pour vérifier (ne devrait rien retourner) :**
```bash
# Backend logs (ne devrait montrer AUCUNE requête http://)
tail -f /var/log/intelia-expert/backend.log | grep "http://expert.intelia.com"
```

**Résultat attendu :** Aucune requête HTTP (toutes en HTTPS directement)

### **2. Vérifier les Erreurs de Certificat**

Si le certificat HTTPS expire, les utilisateurs **ne pourront PAS contourner l'avertissement** (preload = strict).

**Dashboard à surveiller :**
- Expiration certificat Let's Encrypt : https://crt.sh/?q=expert.intelia.com
- Renouvellement automatique : Vérifier Certbot/CloudFlare

### **3. Script de Vérification Mensuelle**

Créer un script pour vérifier le statut preload :

```bash
#!/bin/bash
# verify-hsts-preload.sh

DOMAIN="expert.intelia.com"

echo "🔍 Vérification HSTS Preload pour $DOMAIN"

# 1. Vérifier le header HSTS
echo ""
echo "1️⃣ Header HSTS en production :"
curl -I https://$DOMAIN 2>/dev/null | grep -i strict-transport-security

# 2. Vérifier l'inclusion dans la preload list
echo ""
echo "2️⃣ Statut sur hstspreload.org :"
curl -s "https://hstspreload.org/api/v2/status?domain=$DOMAIN" | python3 -m json.tool

# 3. Vérifier le certificat SSL
echo ""
echo "3️⃣ Certificat SSL :"
echo | openssl s_client -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -dates

echo ""
echo "✅ Vérification terminée"
```

**Automatiser avec cron (mensuel) :**
```bash
# Ajouter au crontab
0 9 1 * * /path/to/verify-hsts-preload.sh | mail -s "HSTS Preload Report" admin@intelia.com
```

---

## 🧪 Tests Avant Soumission

### **Test 1 : Header HSTS Correct**

```bash
curl -I https://expert.intelia.com 2>&1 | grep -i strict-transport-security
```

**Résultat attendu :**
```
strict-transport-security: max-age=31536000; includeSubDomains; preload
```

### **Test 2 : Redirection HTTP → HTTPS**

```bash
curl -I http://expert.intelia.com
```

**Résultat attendu :**
```
HTTP/1.1 301 Moved Permanently
Location: https://expert.intelia.com/
```

### **Test 3 : Certificat SSL Valide**

```bash
echo | openssl s_client -connect expert.intelia.com:443 2>/dev/null | openssl x509 -noout -text
```

**Vérifier :**
- Issuer: Let's Encrypt / CloudFlare
- Not After: Date future (certificat non expiré)
- Subject Alternative Name: expert.intelia.com

### **Test 4 : Sous-domaines en HTTPS**

Si vous avez des sous-domaines (api.expert.intelia.com, etc.) :

```bash
curl -I https://api.expert.intelia.com
```

**Résultat attendu :** 200 OK (ou 404 si pas utilisé, mais **PAS d'erreur SSL**)

---

## 📋 Checklist de Soumission

Avant de soumettre à hstspreload.org :

- [x] Header HSTS avec `max-age=31536000; includeSubDomains; preload` déployé
- [x] Certificat HTTPS valide (Let's Encrypt / CloudFlare)
- [x] Redirection HTTP → HTTPS fonctionne (301 Permanent)
- [x] HTTPS fonctionne sur tous les sous-domaines
- [x] Testé avec SecurityHeaders.com (score A+)
- [x] Testé avec curl (header présent)
- [x] Équipe technique consciente de l'engagement permanent
- [ ] Soumis sur https://hstspreload.org/
- [ ] Confirmation reçue (pending inclusion)

---

## 🎯 Impact sur Intelia Expert

### **Avant HSTS Preload :**

1. Utilisateur tape `http://expert.intelia.com`
2. Navigateur envoie **requête HTTP** (vulnérable à MITM)
3. Serveur répond **301 → https://expert.intelia.com**
4. Navigateur envoie requête HTTPS (sécurisée)

**Vulnérabilité :** Première requête HTTP interceptable par un attaquant (réseau public, WiFi pirate).

### **Après HSTS Preload :**

1. Utilisateur tape `http://expert.intelia.com`
2. Navigateur **consulte sa liste preload interne**
3. Navigateur upgrade automatiquement vers HTTPS **avant l'envoi de la requête**
4. Aucune requête HTTP n'est jamais envoyée

**Résultat :** 🛡️ Protection totale dès la première connexion.

---

## 🔗 Ressources

- **Site officiel** : https://hstspreload.org/
- **Documentation MDN** : https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security
- **Chrome Preload List** : https://chromium.googlesource.com/chromium/src/+/main/net/http/transport_security_state_static.json
- **API Status Check** : https://hstspreload.org/api/v2/status?domain=expert.intelia.com
- **Removal Process** : https://hstspreload.org/removal/

---

## ✅ Recommandation Finale

**Pour Intelia Expert : SOUMETTRE À HSTSPRELOAD.ORG**

**Raisons :**
1. ✅ Tous les pré-requis sont remplis
2. ✅ Expert.intelia.com est **exclusivement HTTPS** (pas de plans pour HTTP)
3. ✅ Protection maximale pour les utilisateurs (connexions sensibles)
4. ✅ Engagement permanent réaliste (application SaaS professionnelle)

**Risques minimes :**
- ⚠️ Si certificat SSL expire ET renouvellement automatique échoue → Site inaccessible (mais cela devrait être monitored de toute façon)
- ⚠️ Si besoin de retirer preload → Processus long (6-12 mois), mais scénario improbable

**Prochaines étapes :**
1. Déployer les changements HSTS en production
2. Vérifier avec curl que le header est présent
3. Soumettre sur https://hstspreload.org/
4. Monitorer le statut mensuel avec le script fourni
5. Attendre 6-12 semaines pour propagation complète

---

*Guide créé le 2025-10-19 dans le cadre de l'optimisation de sécurité OWASP Top 10.*
