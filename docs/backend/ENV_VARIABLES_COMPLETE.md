# Variables d'environnement complètes - Intelia Expert Backend

Guide complet de toutes les variables d'environnement nécessaires pour le backend.

---

## 📋 Table des matières

1. [Variables essentielles (REQUIS)](#1-variables-essentielles-requis)
2. [Base de données PostgreSQL](#2-base-de-données-postgresql)
3. [Supabase (Auth & Storage)](#3-supabase-auth--storage)
4. [OpenAI API](#4-openai-api)
5. [Stripe (Paiements)](#5-stripe-paiements)
6. [Twilio WhatsApp](#6-twilio-whatsapp)
7. [DigitalOcean Spaces](#7-digitalocean-spaces)
8. [Email (SMTP)](#8-email-smtp)
9. [Configuration système](#9-configuration-système)
10. [Features optionnelles](#10-features-optionnelles)

---

## 1. Variables essentielles (REQUIS)

Ces variables sont **obligatoires** pour que le backend démarre:

```bash
# === CORE ===
ENV=production                          # Environnement: development, staging, production
HOST=0.0.0.0                           # Host pour uvicorn
PORT=8080                              # Port du backend
LOG_LEVEL=INFO                         # Niveau de logs: DEBUG, INFO, WARNING, ERROR

# === FRONTEND URL ===
FRONTEND_URL=https://expert.intelia.com  # URL du frontend (pour CORS et redirections)

# === JWT SECRET ===
JWT_SECRET=your-super-secret-jwt-key-min-32-chars  # Clé pour signer les JWT tokens
```

---

## 2. Base de données PostgreSQL

**Obligatoire** - Stockage des conversations, utilisateurs, analytics:

```bash
# === DATABASE (format URL complète) ===
DATABASE_URL=postgresql://user:password@host:port/database

# Exemple DigitalOcean Managed Database:
# DATABASE_URL=postgresql://doadmin:xxxxx@db-postgresql-nyc3-12345.ondigitalocean.com:25060/intelia?sslmode=require

# OU format composantes séparées (optionnel):
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=intelia_expert
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
```

---

## 3. Supabase (Auth & Storage)

**Obligatoire** - Authentification et gestion utilisateurs:

```bash
# === SUPABASE CORE ===
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...XXXXX  # Clé publique (obtenir depuis Dashboard)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...XXXXX  # Clé admin (PRIVÉE!)

# === JWT (même secret que dans Supabase Dashboard → Settings → API → JWT Secret) ===
SUPABASE_JWT_SECRET=your-supabase-jwt-secret-from-dashboard

# === WEBHOOKS (optionnel - pour sync auth events) ===
SUPABASE_WEBHOOK_SECRET=your-webhook-secret-for-auth-events
```

**Obtenir les clés**:
1. Aller sur https://supabase.com/dashboard
2. Sélectionner votre projet
3. Settings → API
4. Copier les clés

---

## 4. OpenAI API

**Obligatoire** - LLM, embeddings, Whisper, vision:

```bash
# === OPENAI ===
OPENAI_API_KEY=sk-proj-XXXXXX...XXXXXX  # Votre clé OpenAI

# === OPENAI ORGANIZATION (optionnel) ===
OPENAI_ORG_ID=org-XXXXXX...XXXXXX  # Si vous avez une organization
```

**Obtenir la clé**:
1. Aller sur https://platform.openai.com/api-keys
2. Créer une nouvelle clé secrète
3. Copier immédiatement (ne sera plus visible)

---

## 5. Stripe (Paiements)

**Obligatoire** pour les abonnements Pro/Elite:

```bash
# === STRIPE MODE (test ou production) ===
STRIPE_MODE=test  # Valeurs: test, live, disable

# === STRIPE TEST KEYS ===
STRIPE_TEST_SECRET_KEY=sk_test_51XXXXXX...XXXXXX  # Remplacer par votre clé test
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_51XXXXXX...XXXXXX
STRIPE_TEST_WEBHOOK_SECRET=whsec_XXXXXX...XXXXXX

# === STRIPE LIVE KEYS (production uniquement) ===
STRIPE_SECRET_KEY=sk_live_51XXXXXX...XXXXXX  # Remplacer par votre clé live
STRIPE_PUBLISHABLE_KEY=pk_live_51XXXXXX...XXXXXX
STRIPE_WEBHOOK_SECRET=whsec_XXXXXX...XXXXXX
```

**Configuration**:
- Voir fichier détaillé: `backend/.env.stripe.example`
- Dashboard: https://dashboard.stripe.com

**Note**: Le système utilise `STRIPE_MODE` pour basculer automatiquement entre test et live.

---

## 6. Twilio WhatsApp

**Optionnel** - Support WhatsApp:

```bash
# === TWILIO ===
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+15075195932  # Votre numéro Twilio WhatsApp

# === LLM SERVICE (pour traiter messages WhatsApp) ===
LLM_SERVICE_URL=http://localhost:8000  # URL du service LLM (peut être même backend)
```

**Configuration**:
1. Créer compte Twilio: https://www.twilio.com/console
2. Activer WhatsApp Sandbox ou acheter numéro
3. Configurer webhook: `https://votre-backend.com/api/v1/whatsapp/webhook`

---

## 7. DigitalOcean Spaces

**Optionnel** (mais recommandé) - Stockage permanent images et audio:

```bash
# === DIGITALOCEAN SPACES (compatible S3) ===
DO_SPACES_KEY=DO00ABCDEFGHIJ1234567
DO_SPACES_SECRET=abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx
DO_SPACES_BUCKET=intelia-expert-media
DO_SPACES_REGION=nyc3  # Régions: nyc3, sfo3, sgp1, ams3, fra1
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
```

**Configuration**:
- Voir guide complet: `backend/AUDIO_STORAGE_SETUP.md`
- Dashboard: https://cloud.digitalocean.com/spaces

**Impact si absent**: Les URLs audio/images Twilio expirent après quelques jours.

---

## 8. Email (SMTP)

**Optionnel** - Envoi d'emails (invitations, notifications):

```bash
# === SMTP CONFIGURATION ===
SMTP_HOST=smtp.gmail.com              # Serveur SMTP
SMTP_PORT=587                         # Port (587=TLS, 465=SSL)
SMTP_USER=your-email@gmail.com        # Email expéditeur
SMTP_PASSWORD=your-app-password       # Mot de passe d'application
SMTP_FROM_EMAIL=noreply@intelia.com   # Email "De" affiché
SMTP_FROM_NAME=Intelia Expert         # Nom expéditeur
```

**Configuration Gmail**:
1. Activer 2FA sur votre compte Google
2. Générer un mot de passe d'application: https://myaccount.google.com/apppasswords
3. Utiliser ce mot de passe (pas votre mot de passe Gmail)

---

## 9. Configuration système

Variables de configuration générale:

```bash
# === URLS & ENDPOINTS ===
BACKEND_URL=https://expert-app-xxxxx.ondigitalocean.app  # URL du backend
INTERNAL_API_BASE_URL=http://localhost:8080             # URL interne backend
NEXT_PUBLIC_API_BASE_URL=https://expert.intelia.com     # URL publique API

# === SECURITY ===
ALLOWED_ORIGINS=https://expert.intelia.com,http://localhost:3000  # CORS origins (séparés par virgule)

# === ANALYTICS & LOGGING ===
ANALYTICS_TABLES_READY=true          # Active les analytics PostgreSQL
ANALYTICS_CACHE_TTL=300              # Durée cache analytics (secondes)
ENABLE_STATS_CACHE=true              # Active le cache stats

# === ADMIN ===
SUPER_ADMIN_EMAILS=admin@intelia.com,dominic@intelia.com  # Admins séparés par virgule

# === CRON JOBS ===
CRON_SECRET_KEY=your-secret-for-cron-endpoints  # Secret pour protéger endpoints cron

# === API VERSIONS ===
API_VERSION=1.0
DEFAULT_MODEL=gpt-4o                 # Modèle LLM par défaut
```

---

## 10. Features optionnelles

Features à activer/désactiver:

```bash
# === VOICE REALTIME (conversations vocales temps réel) ===
ENABLE_VOICE_REALTIME=false          # true pour activer

# Nécessite aussi:
WEAVIATE_URL=https://your-weaviate-instance.weaviate.network
WEAVIATE_API_KEY=your-weaviate-api-key

# === WEBAUTHN (authentification biométrique) ===
WEBAUTHN_RP_ID=expert.intelia.com    # Votre domaine
WEBAUTHN_RP_NAME=Intelia Expert      # Nom affiché
WEBAUTHN_ORIGIN=https://expert.intelia.com  # URL origine

# === ACCESS TOKEN ===
ACCESS_TOKEN_EXPIRE_MINUTES=60       # Durée validité JWT (minutes)

# === INVITATIONS ===
MIN_RESEND_DELAY_HOURS=24           # Délai minimum entre renvois d'invitation
```

---

## 📝 Exemple de fichier `.env` complet

```bash
# ============================================================================
# INTELIA EXPERT - BACKEND ENVIRONMENT VARIABLES
# ============================================================================

# === CORE ===
ENV=production
HOST=0.0.0.0
PORT=8080
LOG_LEVEL=INFO
FRONTEND_URL=https://expert.intelia.com
JWT_SECRET=your-super-secret-jwt-key-min-32-chars-change-this

# === DATABASE ===
DATABASE_URL=postgresql://user:password@host:port/database

# === SUPABASE ===
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...XXXXX
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...XXXXX
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# === OPENAI ===
OPENAI_API_KEY=sk-proj-XXXXXX...XXXXXX

# === STRIPE (MODE TEST) ===
STRIPE_MODE=test
STRIPE_TEST_SECRET_KEY=sk_test_XXXXXX...XXXXXX
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_XXXXXX...XXXXXX
STRIPE_TEST_WEBHOOK_SECRET=whsec_XXXXXX...XXXXXX

# === TWILIO WHATSAPP (optionnel) ===
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+15075195932
LLM_SERVICE_URL=http://localhost:8000

# === DIGITALOCEAN SPACES (optionnel mais recommandé) ===
DO_SPACES_KEY=DO00ABCDEFGHIJ1234567
DO_SPACES_SECRET=abcd1234efgh5678
DO_SPACES_BUCKET=intelia-expert-media
DO_SPACES_REGION=nyc3
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

# === SMTP EMAIL (optionnel) ===
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@intelia.com
SMTP_FROM_NAME=Intelia Expert

# === SYSTEM ===
BACKEND_URL=https://expert-app-xxxxx.ondigitalocean.app
ALLOWED_ORIGINS=https://expert.intelia.com,http://localhost:3000
SUPER_ADMIN_EMAILS=admin@intelia.com
CRON_SECRET_KEY=your-cron-secret

# === FEATURES ===
ENABLE_VOICE_REALTIME=false
ANALYTICS_TABLES_READY=true
```

---

## ⚠️ Sécurité

**IMPORTANT**:
- ✅ Ajouter `.env` au `.gitignore` (ne JAMAIS commiter)
- ✅ Utiliser des secrets différents en dev/staging/production
- ✅ Régénérer les secrets régulièrement
- ✅ Limiter l'accès aux clés Supabase Service Role
- ✅ Activer restrictions IP pour Stripe webhooks
- ✅ Utiliser HTTPS en production

---

## 🔍 Vérifier la configuration

Pour vérifier quelles variables sont configurées:

```bash
# Tester la connexion
curl https://votre-backend.com/health

# Vérifier la configuration (admin uniquement)
curl https://votre-backend.com/api/v1/system/check
```

Ou dans le code Python:

```python
from app.main import app

# Après démarrage, vérifier logs de startup
# Toutes les variables manquantes seront listées
```

---

## 📚 Ressources

- [DigitalOcean Spaces Setup](./AUDIO_STORAGE_SETUP.md)
- [Stripe Configuration](./.env.stripe.example)
- [Voice Realtime Setup](./.env.voice_realtime.example)

---

## ✅ Checklist de déploiement

- [ ] Toutes les variables **REQUIS** sont définies
- [ ] `DATABASE_URL` pointe vers PostgreSQL production
- [ ] `SUPABASE_*` configuré avec projet production
- [ ] `OPENAI_API_KEY` valide avec quota suffisant
- [ ] `STRIPE_MODE=live` et clés live configurées
- [ ] `FRONTEND_URL` pointe vers production
- [ ] `ALLOWED_ORIGINS` inclut seulement domaines légitimes
- [ ] `.env` ajouté au `.gitignore`
- [ ] Secrets changés depuis valeurs par défaut
- [ ] HTTPS activé sur tous les endpoints publics
- [ ] Webhooks Stripe configurés avec URL production
- [ ] DigitalOcean Spaces créé et clés configurées (si stockage audio)
- [ ] SMTP configuré (si envoi emails)
- [ ] Variables testées en staging avant production
