# Compass Integration - Online Testing Checklist

**Date**: 2025-10-30
**Status**: Ready for Testing
**Environment**: Production/Staging

---

## 🚀 Push Status

✅ **6 commits pushed to main**:
- `d9a7438b` - Initial analysis document
- `34dd27ab` - RAG integration (Phase 3)
- `938c3c10` - Frontend UI (Phase 2)
- `48bf2404` - Backend API (Phase 1)
- `bc4cc843` - Documentation organization
- `d3838bfc` - Middleware support

---

## 📋 Pre-Testing Setup

### 1. Environment Variables (Backend)

Vérifier que ces variables sont configurées sur le serveur :

```bash
# Required
COMPASS_API_URL=https://compass.intelia.com/api/v1
COMPASS_API_TOKEN=your_token_here

# Optional (defaults shown)
COMPASS_REQUEST_TIMEOUT=10
COMPASS_CACHE_ENABLED=true
COMPASS_CACHE_TTL=300
```

**Vérification** :
```bash
# SSH into server
ssh user@your-server.com

# Check environment
env | grep COMPASS

# Or check .env file
cat /path/to/backend/.env | grep COMPASS
```

### 2. Database Migration

La table `user_compass_config` doit être créée (déjà fait via DBeaver) :

```sql
-- Verify table exists
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'user_compass_config'
ORDER BY ordinal_position;

-- Expected: 6 columns (id, user_id, compass_enabled, barns, created_at, updated_at)
```

### 3. Backend Deployment

**Option A - Auto Deploy (si CI/CD configuré)** :
- Le push devrait déclencher le déploiement automatique
- Vérifier le statut du build/deploy pipeline

**Option B - Manuel Deploy** :
```bash
# SSH into server
ssh user@your-server.com

# Pull latest changes
cd /path/to/intelia-cognito
git pull origin main

# Restart backend
pm2 restart backend
# OR
systemctl restart intelia-backend

# Check logs
pm2 logs backend --lines 100
# OR
journalctl -u intelia-backend -f
```

### 4. Frontend Deployment

**Option A - Auto Deploy (Vercel/Netlify)** :
- Le push devrait déclencher le build automatique
- Vérifier le statut du deployment

**Option B - Manuel Build** :
```bash
# SSH into server OR locally
cd frontend
npm install
npm run build

# Deploy (method depends on hosting)
# Vercel: vercel deploy --prod
# Netlify: netlify deploy --prod
# Manual: rsync -avz .next/ user@server:/app/frontend/
```

---

## ✅ Backend Testing

### Test 1: Backend Startup

**Objectif** : Vérifier que le backend démarre sans erreurs

**Étapes** :
```bash
# Check logs for Compass initialization
pm2 logs backend | grep -i compass
```

**Résultat attendu** :
```
✅ Compass router imported with 9 routes
✅ Compass router mounted
✅ Compass Integration enabled!
✅ Compass API service initialized
```

**Statut** : ⬜ Passed / ⬜ Failed

---

### Test 2: Connection Status (Admin)

**Objectif** : Vérifier la connexion à l'API Compass

**Étapes** :
1. Ouvrir un terminal
2. Obtenir un JWT token admin (connexion à l'app)
3. Exécuter :

```bash
curl -H "Authorization: Bearer YOUR_ADMIN_JWT" \
     https://api.intelia.com/api/v1/compass/admin/connection-status
```

**Résultat attendu** :
```json
{
  "status": "connected",
  "api_url": "https://compass.intelia.com/api/v1",
  "has_token": true,
  "device_count": 5
}
```

**Statut** : ⬜ Passed / ⬜ Failed
**Notes** : _______________________________________________

---

### Test 3: Device List (Admin)

**Objectif** : Lister les appareils Compass disponibles

**Étapes** :
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_JWT" \
     https://api.intelia.com/api/v1/compass/admin/devices
```

**Résultat attendu** :
```json
{
  "success": true,
  "data": [
    {
      "id": "849",
      "name": "Poulailler A",
      "entity_id": 123
    },
    {
      "id": "850",
      "name": "Poulailler B",
      "entity_id": 123
    }
  ]
}
```

**Statut** : ⬜ Passed / ⬜ Failed
**Device Count** : _______

---

### Test 4: User Configs List (Admin)

**Objectif** : Lister toutes les configurations utilisateur

**Étapes** :
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_JWT" \
     https://api.intelia.com/api/v1/compass/admin/users
```

**Résultat attendu** :
```json
{
  "success": true,
  "data": []
}
```
*(Vide au début - normal)*

**Statut** : ⬜ Passed / ⬜ Failed

---

### Test 5: Unauthorized Access (Security)

**Objectif** : Vérifier que les endpoints admin sont protégés

**Étapes** :
```bash
# Sans token
curl https://api.intelia.com/api/v1/compass/admin/devices

# Avec token utilisateur normal (non-admin)
curl -H "Authorization: Bearer USER_JWT" \
     https://api.intelia.com/api/v1/compass/admin/devices
```

**Résultat attendu** :
```json
{
  "detail": "Access denied - admin privileges required",
  "error": "insufficient_privileges"
}
```

**Statut** : ⬜ Passed / ⬜ Failed

---

## ✅ Frontend Testing

### Test 6: Statistics Page Access

**Objectif** : Vérifier l'accès à la page Statistics (admin uniquement)

**Étapes** :
1. Ouvrir https://expert.intelia.com
2. Se connecter avec un compte admin
3. Naviguer vers Statistics page
4. Chercher l'onglet "Compass"

**Résultat attendu** :
- ✅ Onglet "Compass" visible dans la navigation
- ✅ Autres onglets : Dashboard, Questions, Invitations, etc.

**Statut** : ⬜ Passed / ⬜ Failed

---

### Test 7: Compass Tab UI

**Objectif** : Vérifier l'interface Compass Tab

**Étapes** :
1. Cliquer sur l'onglet "Compass"
2. Vérifier les éléments affichés

**Résultat attendu** :
- ✅ Header avec titre "Compass Integration"
- ✅ Bouton "Actualiser"
- ✅ Connection Status Card (vert si connecté)
- ✅ API URL affiché
- ✅ Device count affiché
- ✅ User configurations table (vide au début)

**Statut** : ⬜ Passed / ⬜ Failed
**Screenshot** : _______________________

---

### Test 8: Connection Status Display

**Objectif** : Vérifier l'affichage du statut de connexion

**Étapes** :
1. Dans Compass Tab, regarder la "Connection Status Card"
2. Noter les informations affichées

**Résultat attendu** :
- ✅ Badge vert "Connecté" ou rouge "Déconnecté"
- ✅ URL de l'API Compass
- ✅ "Token configuré : Oui"
- ✅ Nombre d'appareils disponibles

**Statut** : ⬜ Passed / ⬜ Failed
**Device Count** : _______

---

### Test 9: Configure User Modal

**Objectif** : Tester l'ouverture du modal de configuration

**Étapes** :
1. Cliquer sur "Configurer" pour un utilisateur
2. Vérifier que le modal s'ouvre

**Résultat attendu** :
- ✅ Modal s'ouvre avec titre "Configuration Compass"
- ✅ Email utilisateur affiché
- ✅ Toggle "Activer Compass" visible
- ✅ Section "Poulaillers configurés" visible
- ✅ Bouton "Ajouter un poulailler" visible
- ✅ Boutons "Annuler" et "Sauvegarder" visible

**Statut** : ⬜ Passed / ⬜ Failed

---

### Test 10: Add Barn Configuration

**Objectif** : Ajouter une configuration de poulailler

**Étapes** :
1. Dans le modal, activer "Activer Compass" (toggle ON)
2. Cliquer sur "Ajouter un poulailler"
3. Remplir :
   - Appareil Compass : Sélectionner un device (ex: "Poulailler A #849")
   - Numéro client : "2"
   - Nom du poulailler : "Poulailler Test"
4. Cliquer "Sauvegarder"

**Résultat attendu** :
- ✅ Poulailler ajouté avec succès
- ✅ Modal se ferme
- ✅ User table se met à jour
- ✅ Badge "Activé" vert visible

**Statut** : ⬜ Passed / ⬜ Failed

---

### Test 11: Preview Real-Time Data

**Objectif** : Prévisualiser les données temps réel

**Étapes** :
1. Dans la table, cliquer "Prévisualiser" pour l'utilisateur configuré
2. Vérifier l'affichage des données

**Résultat attendu** :
- ✅ Modal "Données Temps Réel Compass" s'ouvre
- ✅ Carte(s) de poulailler affichée(s)
- ✅ Données visibles :
  - Température (°C)
  - Humidité (%)
  - Poids moyen (g)
  - Âge du troupeau (jours)
- ✅ Timestamp "Dernière mise à jour"
- ✅ Bouton "Actualiser" fonctionne

**Statut** : ⬜ Passed / ⬜ Failed
**Data Displayed** : ⬜ Yes / ⬜ No / ⬜ N/A (empty)

---

### Test 12: Responsive Design

**Objectif** : Vérifier le responsive design

**Étapes** :
1. Ouvrir Chrome DevTools (F12)
2. Tester différentes tailles d'écran :
   - Desktop (1920x1080)
   - Tablet (768x1024)
   - Mobile (375x667)

**Résultat attendu** :
- ✅ Desktop : Layout normal, 2 colonnes pour preview
- ✅ Tablet : Layout adapté, navigation OK
- ✅ Mobile : Cards en colonne unique, buttons adaptés

**Statut** : ⬜ Passed / ⬜ Failed

---

## ✅ Integration Testing (End-to-End)

### Test 13: User Query Flow

**Objectif** : Tester une requête utilisateur complète

**Prérequis** :
- Utilisateur configuré avec au moins 1 poulailler

**Étapes** :
1. Se connecter avec le compte utilisateur (non-admin)
2. Ouvrir le chat
3. Poser la question : "Quelle est la température dans mon poulailler 2?"
4. Vérifier la réponse

**Résultat attendu** :
- ✅ Réponse contient la température actuelle
- ✅ Réponse mentionne le nom du poulailler
- ✅ Données sont à jour (timestamp récent)
- ✅ Format de réponse professionnel

**Exemple de réponse** :
```
La température actuelle dans votre Poulailler Test (poulailler 2) est de 22.5°C.

Dernière mise à jour : 30 octobre 2025 à 13:45
```

**Statut** : ⬜ Passed / ⬜ Failed
**Response Time** : _______ ms

---

### Test 14: Multiple Barns Query

**Objectif** : Requête pour plusieurs poulaillers

**Étapes** :
1. Poser : "Quelles sont les températures de tous mes poulaillers?"

**Résultat attendu** :
- ✅ Liste de tous les poulaillers configurés
- ✅ Température pour chaque poulailler
- ✅ Formatage clair (liste à puces ou tableau)

**Statut** : ⬜ Passed / ⬜ Failed

---

### Test 15: Data Type Queries

**Objectif** : Tester différents types de données

**Étapes** :
Poser ces questions successivement :
1. "Quelle est l'humidité dans mon poulailler 2?"
2. "Quel est le poids moyen de mes poulets dans le poulailler 2?"
3. "Quel est l'âge du troupeau dans le poulailler 2?"

**Résultat attendu** :
- ✅ Humidité affichée en %
- ✅ Poids affiché en grammes
- ✅ Âge affiché en jours

**Statut** : ⬜ Passed / ⬜ Failed

---

## ❌ Error Handling Tests

### Test 16: Invalid Barn Number

**Objectif** : Gérer un numéro de poulailler invalide

**Étapes** :
1. Poser : "Quelle est la température dans mon poulailler 999?"

**Résultat attendu** :
- ✅ Message d'erreur clair
- ✅ Suggestion des poulaillers disponibles

**Statut** : ⬜ Passed / ⬜ Failed

---

### Test 17: Compass API Down

**Objectif** : Gérer l'indisponibilité de Compass

**Étapes** :
1. Temporairement invalider le COMPASS_API_TOKEN
2. Redémarrer le backend
3. Tester la connexion dans l'UI

**Résultat attendu** :
- ✅ Badge rouge "Déconnecté"
- ✅ Message d'erreur explicite
- ✅ Pas de crash de l'application

**Statut** : ⬜ Passed / ⬜ Failed

---

### Test 18: User Without Config

**Objectif** : Gérer un utilisateur sans configuration

**Étapes** :
1. Se connecter avec un utilisateur non configuré
2. Poser : "Quelle est la température dans mon poulailler?"

**Résultat attendu** :
- ✅ Message indiquant l'absence de configuration
- ✅ Suggestion de contacter l'admin

**Statut** : ⬜ Passed / ⬜ Failed

---

## 🔒 Security Tests

### Test 19: Admin-Only Access

**Objectif** : Vérifier que seuls les admins accèdent à la config

**Étapes** :
1. Se connecter avec un compte utilisateur normal
2. Naviguer vers Statistics
3. Vérifier que l'onglet Compass n'est PAS visible

**Résultat attendu** :
- ✅ Onglet Compass invisible pour utilisateurs normaux
- ✅ Tentative d'accès direct redirige ou erreur 403

**Statut** : ⬜ Passed / ⬜ Failed

---

### Test 20: User Data Isolation

**Objectif** : Vérifier que les users ne voient que leurs données

**Étapes** :
1. Configurer User A avec poulailler #849
2. Configurer User B avec poulailler #850
3. Se connecter comme User A
4. Tenter d'accéder aux données du poulailler #850

**Résultat attendu** :
- ✅ User A ne peut accéder qu'à son poulailler #849
- ✅ Erreur si tentative d'accès au poulailler d'un autre user

**Statut** : ⬜ Passed / ⬜ Failed

---

## 📊 Performance Tests

### Test 21: Load Time

**Objectif** : Mesurer les temps de chargement

**Étapes** :
1. Ouvrir Chrome DevTools > Network
2. Naviguer vers Compass Tab
3. Noter les temps de chargement

**Résultat attendu** :
- ✅ Connection status : < 500ms
- ✅ Device list : < 1s
- ✅ User configs : < 1s
- ✅ Preview data : < 2s

**Statut** : ⬜ Passed / ⬜ Failed
**Actual Times** : ___________________________

---

### Test 22: Concurrent Users

**Objectif** : Tester avec plusieurs utilisateurs simultanés

**Étapes** :
1. Ouvrir 3-5 navigateurs/sessions
2. Faire des requêtes simultanées

**Résultat attendu** :
- ✅ Toutes les requêtes répondent correctement
- ✅ Pas de timeouts
- ✅ Pas d'erreurs serveur

**Statut** : ⬜ Passed / ⬜ Failed

---

## 📝 Summary

### Overall Status
- ⬜ All Tests Passed (Production Ready)
- ⬜ Minor Issues (Deploy with monitoring)
- ⬜ Major Issues (Do not deploy)

### Test Results Summary
- **Backend Tests** : ___/5 passed
- **Frontend Tests** : ___/7 passed
- **Integration Tests** : ___/3 passed
- **Error Handling** : ___/3 passed
- **Security Tests** : ___/2 passed
- **Performance Tests** : ___/2 passed

**Total** : ___/22 tests passed

### Issues Found
1. _________________________________________________
2. _________________________________________________
3. _________________________________________________

### Action Items
- [ ] _________________________________________________
- [ ] _________________________________________________
- [ ] _________________________________________________

### Sign-Off
- **Tester** : _____________________
- **Date** : _____________________
- **Approved for Production** : ⬜ Yes / ⬜ No

---

**Last Updated**: 2025-10-30
**Document Version**: 1.0.0
