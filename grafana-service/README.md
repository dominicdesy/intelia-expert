# Grafana Service for Digital Ocean App Platform

Service Grafana auto-hébergé pour le monitoring d'Intelia Expert, configuré pour permettre l'embedding via iframe.

## 🎯 Avantages vs Droplet manuel

- ✅ **Déploiement automatique** - Push to deploy depuis GitHub
- ✅ **SSL/HTTPS automatique** - Certificat Let's Encrypt gratuit
- ✅ **Scaling automatique** - Géré par Digital Ocean
- ✅ **Logs intégrés** - Dans le dashboard App Platform
- ✅ **Monitoring intégré** - Métriques CPU/RAM automatiques
- ✅ **Pas de gestion serveur** - Pas de SSH, updates automatiques

## 📋 Prérequis

- Backend avec endpoint `/api/metrics` déployé (✅ fait)
- Variables d'environnement `METRICS_USERNAME` et `METRICS_PASSWORD` configurées (✅ fait)

## 🚀 Déploiement sur Digital Ocean App Platform

### 1. Créer le Web Service

Dans Digital Ocean App Platform:

1. Aller dans votre App "intelia-expert"
2. Cliquer sur **"Create" → "From Source Code"**
3. Sélectionner le repo GitHub: `dominicdesy/intelia-expert`
4. **Source Directory**: `/grafana-service`
5. **Branch**: `main`
6. **Type**: Web Service
7. **Name**: `grafana`

### 2. Configuration du Build

Digital Ocean détectera automatiquement le Dockerfile.

**Build Command**: (vide, Dockerfile suffit)
**Run Command**: (vide, CMD dans Dockerfile)

### 3. Variables d'environnement

Ajouter ces variables dans l'onglet "Environment Variables":

```
GF_SECURITY_ADMIN_PASSWORD=InteliaGrafana2025!
GF_SECURITY_ALLOW_EMBEDDING=true
GF_AUTH_ANONYMOUS_ENABLED=false
GF_SERVER_ROOT_URL=${APP_URL}
GF_SECURITY_COOKIE_SAMESITE=none
GF_SECURITY_COOKIE_SECURE=true
```

**Note**: `${APP_URL}` sera automatiquement remplacé par l'URL du service (ex: `https://grafana-intelia.ondigitalocean.app`)

### 4. Configuration du Service

- **HTTP Port**: 3000
- **Instance Size**: Basic ($5/mois recommandé)
- **Instance Count**: 1

### 5. Déployer

Cliquer sur **"Create Resources"** - Le déploiement prendra 2-3 minutes.

## 🔐 Accès à Grafana

Une fois déployé:

**URL**: `https://grafana-intelia.ondigitalocean.app` (ou l'URL générée par DO)

**Login**:
- Username: `admin`
- Password: `InteliaGrafana2025!`

## 📊 Configuration du Dashboard

### 1. Vérifier le Datasource

Le datasource "Intelia Backend Metrics" devrait être automatiquement configuré:
- URL: `https://expert.intelia.com/api/metrics`
- Auth: Basic Auth (grafana / password)
- Scrape interval: 60s

### 2. Créer un Dashboard

1. Aller dans **Dashboards → New → New Dashboard**
2. Ajouter des panels avec les métriques disponibles

**Exemple de requêtes Prometheus**:

```promql
# Coût total LLM (dernières 24h)
sum(increase(intelia_llm_cost_usd_total[24h]))

# Tokens consommés par modèle
sum by (model) (intelia_llm_tokens_total)

# Latence moyenne par modèle
rate(intelia_llm_request_duration_seconds_sum[5m]) / rate(intelia_llm_request_duration_seconds_count[5m])

# Requêtes réussies vs erreurs
sum by (status) (intelia_llm_requests_total)
```

### 3. Obtenir l'URL d'embedding

1. Ouvrir le dashboard
2. Cliquer sur **Share** (icône en haut à droite)
3. Onglet **Link** → Copier l'URL
4. Pour embedding: Utiliser l'URL complète du dashboard

**Format**: `https://grafana-intelia.ondigitalocean.app/d/[dashboard-id]/[dashboard-name]?orgId=1&theme=light`

## 🔗 Intégration Frontend

Mettre à jour `frontend/.env.local`:

```bash
NEXT_PUBLIC_GRAFANA_URL=https://grafana-intelia.ondigitalocean.app/d/[dashboard-id]/[dashboard-name]?orgId=1&kiosk=tv&theme=light
```

Le composant `StatisticsPage.tsx` utilisera automatiquement cette URL pour l'iframe.

## 🔧 Maintenance

### Voir les logs

Dans Digital Ocean App Platform:
1. Aller dans l'app → Service "grafana"
2. Onglet "Runtime Logs"

### Redéployer

Deux options:
1. **Auto**: Push vers GitHub `main` → Déploiement automatique
2. **Manuel**: Bouton "Deploy" dans App Platform

### Mettre à jour Grafana

L'image `grafana/grafana:latest` sera automatiquement mise à jour lors des redéploiements.

## 🎨 Configuration CSP Frontend

Le CSP dans `frontend/next.config.js` doit inclure:

```javascript
frame-src https://*.ondigitalocean.app
```

✅ **Déjà configuré** avec `https://*.grafana.net` - Mettre à jour si nécessaire.

## 💰 Coût

**Web Service Basic**: ~$5-6/mois (selon l'instance size)

Comparé au droplet manuel ($6/mois) + temps de maintenance, c'est plus avantageux.

## 📝 Métriques Disponibles

Voir la liste complète dans `/GRAFANA_SETUP.md` à la racine du projet.

**Catégories principales**:
- LLM (coûts, tokens, latence, requêtes)
- API HTTP (requêtes, latence, erreurs)
- Base de données (queries, latence, connections)
- Business (users, sessions, conversations)
- Santé système (uptime, info)

## 🆘 Troubleshooting

### Le datasource ne fonctionne pas

Vérifier que:
1. Backend est accessible: `https://expert.intelia.com/api/metrics`
2. Basic Auth est correct: `grafana` / `I#kmd9$kuZnO!dZXF9z8ZTF8`
3. Variables d'environnement backend sont configurées

### L'iframe ne s'affiche pas

Vérifier:
1. `GF_SECURITY_ALLOW_EMBEDDING=true` est bien défini
2. CSP frontend inclut `frame-src` pour `*.ondigitalocean.app`
3. Dashboard URL est correcte et publique

### Erreur de build

Vérifier:
1. Source Directory est bien `/grafana-service`
2. Dockerfile est présent dans le dossier
3. Logs de build pour détails
