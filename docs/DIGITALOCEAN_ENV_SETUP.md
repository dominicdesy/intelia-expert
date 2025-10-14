# Configuration Variables d'Environnement - DigitalOcean App Platform

## Guide de déploiement pour Intelia Expert avec analyse d'images médicales

---

## Architecture DigitalOcean

```
┌─────────────────────────────────────────────────────────────┐
│              DigitalOcean App Platform                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  BACKEND (8001)  │         │   LLM (8000)     │         │
│  │  FastAPI         │         │   FastAPI        │         │
│  │  - Auth          │         │   - Claude       │         │
│  │  - Images S3     │◄────────┤   - RAG          │         │
│  │  - PostgreSQL    │         │   - Vision API   │         │
│  └──────────────────┘         └──────────────────┘         │
│         │                              │                    │
│         ▼                              ▼                    │
│  ┌──────────────┐            ┌──────────────┐              │
│  │ DO Spaces    │            │ Anthropic    │              │
│  │ (S3)         │            │ Claude API   │              │
│  └──────────────┘            └──────────────┘              │
│         │                              │                    │
│  ┌──────────────────────────────────────────────┐          │
│  │         PostgreSQL (Managed Database)        │          │
│  │         - auth.users                         │          │
│  │         - medical_images                     │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Variables Backend (Port 8001)

### 🔐 DigitalOcean Spaces (Stockage images S3-compatible)

```bash
# Clés d'accès Spaces (créées dans DigitalOcean > API > Spaces Access Keys)
DO_SPACES_KEY=your_digitalocean_spaces_access_key
DO_SPACES_SECRET=your_digitalocean_spaces_secret_key

# Configuration bucket
DO_SPACES_BUCKET=intelia-expert-images
DO_SPACES_REGION=nyc3  # ou sfo3, sgp1, ams3, fra1 (choisir région proche)
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
```

**📝 Comment créer les clés Spaces:**
1. DigitalOcean Dashboard → API → Spaces Access Keys
2. Cliquer "Generate New Key"
3. Nommer: "intelia-expert-production"
4. Copier **Key** et **Secret** (le secret ne sera plus affiché!)

---

### 🗄️ PostgreSQL Database

```bash
# URL de connexion PostgreSQL (fournie par DO Managed Database)
DATABASE_URL=postgresql://user:password@db-host:25060/defaultdb?sslmode=require

# Supabase (si vous utilisez Supabase au lieu de DO PostgreSQL)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

**📝 Comment obtenir DATABASE_URL:**
- **DigitalOcean Managed Database:**
  1. Databases → Votre DB → Connection Details
  2. Copier "Connection String"

- **Supabase:**
  1. Project Settings → API → URL
  2. Project Settings → API → anon/service_role keys

---

### 🔑 JWT & Auth

```bash
# Génération JWT (peut être généré via `openssl rand -hex 32`)
JWT_SECRET_KEY=your_super_secret_jwt_key_here_min_32_chars

# Supabase JWT (si Supabase Auth)
SUPABASE_JWT_SECRET=your_supabase_jwt_secret
```

---

### 🌐 CORS & Server

```bash
# Domaines autorisés (séparer par des virgules)
ALLOWED_ORIGINS=https://intelia-expert.com,https://www.intelia-expert.com

# Base path (vide pour racine)
BASE_PATH=

# Niveau de logs
LOG_LEVEL=INFO
```

---

### 📊 Métriques & Monitoring (Optionnel)

```bash
# LangSmith (monitoring des requêtes)
LANGSMITH_ENABLED=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=intelia-backend
LANGSMITH_ENVIRONMENT=production

# Performance monitoring
ENABLE_PERFORMANCE_MONITORING=true
ENABLE_METRICS_LOGGING=true
```

---

## 2. Variables LLM (Port 8000)

### 🤖 Anthropic Claude API (REQUIS pour Vision)

```bash
# Clé API Anthropic (console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxx

# Modèle Vision (ne pas changer)
CLAUDE_VISION_MODEL=claude-3-5-sonnet-20241022
```

**📝 Comment obtenir ANTHROPIC_API_KEY:**
1. Aller sur https://console.anthropic.com/
2. Settings → API Keys
3. Create Key → Copier la clé

**💰 Coûts estimés Claude Vision:**
- Input: $3/1M tokens (~2500 tokens par image + prompt)
- Output: $15/1M tokens (~800 tokens de réponse)
- **Coût par analyse:** ~$0.02-0.04 par image

---

### 🔌 Multi-LLM Routing (Optionnel mais recommandé)

```bash
# Activer le routing intelligent (économise 70% des coûts)
ENABLE_LLM_ROUTING=true

# Provider par défaut si routing désactivé
DEFAULT_LLM_PROVIDER=claude

# OpenAI GPT-4o ($5/1M tokens) - Pour fallback
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# DeepSeek ($0.55/1M tokens) - Pour requêtes simples
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 🗂️ Vector Database (Weaviate)

```bash
# URL Weaviate (si déployé séparément sur DO)
WEAVIATE_URL=https://weaviate.intelia-expert.com

# Ou si Weaviate local dans le même réseau DO
WEAVIATE_URL=http://weaviate:8080
```

**📝 Options déploiement Weaviate:**
- **Option 1:** Weaviate Cloud (weaviate.cloud) - Gratuit jusqu'à 1GB
- **Option 2:** DO Droplet dédié (1 vCPU, 2GB RAM = $12/mois)
- **Option 3:** PostgreSQL + pgvector (fallback sans Weaviate)

---

### 🔴 Redis Cache (Optionnel)

```bash
# URL Redis (si déployé sur DO Managed Redis)
REDIS_URL=redis://default:password@redis-host:25061

# Configuration cache
CACHE_ENABLED=true
EXTERNAL_CACHE_AVAILABLE=true
```

**📝 Redis sur DigitalOcean:**
- Databases → Create → Redis
- Coût: ~$15/mois (1GB)
- **Alternative gratuite:** Désactiver cache (dégradation performance minime)

---

### 🧠 RAG Configuration

```bash
# RAG Engine
RAG_ENABLED=true
RAG_SIMILARITY_TOP_K=15
RAG_CONFIDENCE_THRESHOLD=0.55

# Hybrid Search (BM25 + Vector)
HYBRID_SEARCH_ENABLED=true
HYBRID_ALPHA=0.6
```

---

### 🌍 Multilingue

```bash
# Langues
DEFAULT_LANGUAGE=fr
FALLBACK_LANGUAGE=en
SUPPORTED_LANGUAGES=fr,en,es,de,it,pt,nl,pl

# Google Translate (optionnel)
GOOGLE_TRANSLATE_API_KEY=your_google_api_key
ENABLE_GOOGLE_TRANSLATE_FALLBACK=false
```

---

### 🛡️ Guardrails & OOD Detection

```bash
# Niveau de strictness
GUARDRAILS_LEVEL=strict

# Out-of-Domain Detection
OOD_MIN_SCORE=0.4
OOD_STRICT_SCORE=0.7
```

---

### 📊 Monitoring LLM (LangSmith)

```bash
LANGSMITH_ENABLED=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=intelia-llm
LANGSMITH_ENVIRONMENT=production
```

---

## 3. Variables Partagées (Backend + LLM)

Ces variables doivent être définies dans **les deux** services:

```bash
# Environnement
ENVIRONMENT=production

# Base path
BASE_PATH=

# CORS
ALLOWED_ORIGINS=https://intelia-expert.com,https://www.intelia-expert.com

# Logs
LOG_LEVEL=INFO
```

---

## 4. Checklist de Déploiement

### ✅ Avant le déploiement

- [ ] Créer un bucket **DigitalOcean Spaces** pour les images
- [ ] Générer les **Spaces Access Keys**
- [ ] Créer une **PostgreSQL Managed Database**
- [ ] Exécuter le script SQL `create_medical_images_table.sql`
- [ ] Obtenir une clé **Anthropic API** (avec crédit)
- [ ] Configurer **Weaviate** (cloud ou Droplet)
- [ ] (Optionnel) Créer un **Redis** Managed Database

### ✅ Configuration App Platform

1. **Backend Service:**
   - Port: 8001
   - Build Command: `pip install -r requirements.txt`
   - Run Command: `uvicorn app.main:app --host 0.0.0.0 --port 8001`
   - Variables: Voir section "Variables Backend"

2. **LLM Service:**
   - Port: 8000
   - Build Command: `pip install -r requirements.txt`
   - Run Command: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
   - Variables: Voir section "Variables LLM"

3. **PostgreSQL Database:**
   - Lier la DB managed aux deux services
   - La variable `DATABASE_URL` sera auto-injectée

### ✅ Post-déploiement

- [ ] Tester endpoint: `GET https://backend.com/api/v1/images/health`
- [ ] Tester endpoint: `GET https://llm.com/llm/vision/health`
- [ ] Uploader une image test: `POST /api/v1/images/upload`
- [ ] Tester analyse: `POST /llm/chat-with-image`
- [ ] Vérifier les logs dans DO Dashboard
- [ ] Monitorer les coûts Anthropic

---

## 5. Exemple: Configuration minimale (Production)

### Backend (8001) - Variables minimales

```bash
# Spaces (REQUIS pour images)
DO_SPACES_KEY=xxxxxxxxxxxxx
DO_SPACES_SECRET=xxxxxxxxxxxxx
DO_SPACES_BUCKET=intelia-expert-images
DO_SPACES_REGION=nyc3
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

# Database (auto-injectée par DO si DB liée)
DATABASE_URL=${db.DATABASE_URL}

# Auth (REQUIS)
JWT_SECRET_KEY=your_generated_secret_key_here

# CORS (REQUIS)
ALLOWED_ORIGINS=https://intelia-expert.com

# Logs
LOG_LEVEL=INFO
```

### LLM (8000) - Variables minimales

```bash
# Claude Vision (REQUIS)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx

# Weaviate (REQUIS pour RAG)
WEAVIATE_URL=https://weaviate-cluster.weaviate.cloud

# Database (pour fallback RAG sans Weaviate)
DATABASE_URL=${db.DATABASE_URL}

# RAG
RAG_ENABLED=true
RAG_SIMILARITY_TOP_K=15

# CORS
ALLOWED_ORIGINS=https://intelia-expert.com

# Logs
LOG_LEVEL=INFO
```

---

## 6. Sécurité & Best Practices

### 🔒 Secrets sensibles

**NE JAMAIS commiter:**
- `DO_SPACES_SECRET`
- `ANTHROPIC_API_KEY`
- `JWT_SECRET_KEY`
- `DATABASE_URL`

**Utiliser les "Encrypted Variables" de DigitalOcean:**
1. App Platform → Settings → Environment Variables
2. Cocher "Encrypt" pour les secrets

### 💰 Gestion des coûts

**Limites recommandées (Anthropic Console):**
- Budget mensuel: $50-100
- Rate limit: 50 requêtes/min
- Hard limit: $200/mois

**Alertes:**
- Configurer alerts sur DO Spaces (>1000 requêtes/jour suspect)
- Monitorer tokens Anthropic (>100K tokens/jour = $3-15/jour)

### 📈 Monitoring

**Logs à surveiller:**
- `[VISION] Analysis failed` → Problème API Anthropic
- `Error upload DigitalOcean Spaces` → Problème Spaces
- `DB non disponible` → Problème PostgreSQL

**Dashboards utiles:**
- DigitalOcean → App → Insights (CPU, RAM, requêtes)
- Anthropic Console → Usage (tokens, coûts)
- LangSmith (si activé) → Traces (latence, erreurs)

---

## 7. Troubleshooting

### Problème: "Images router non monté"

**Cause:** `python-multipart` manquant

**Solution:**
```bash
pip install python-multipart
```

Ajouter dans `backend/requirements.txt`:
```
python-multipart>=0.0.20
```

### Problème: "ANTHROPIC_API_KEY non trouvé"

**Cause:** Variable non définie dans LLM service

**Solution:**
1. App Platform → LLM Service → Settings → Environment Variables
2. Ajouter `ANTHROPIC_API_KEY=sk-ant-api03-xxx...`

### Problème: "Erreur upload DigitalOcean Spaces"

**Causes possibles:**
- Mauvaises clés (`DO_SPACES_KEY`/`DO_SPACES_SECRET`)
- Bucket inexistant
- Région incorrecte

**Solution:**
1. Vérifier que le bucket existe: DigitalOcean → Spaces
2. Vérifier région du bucket (doit matcher `DO_SPACES_REGION`)
3. Régénérer les Spaces Access Keys si doute

### Problème: "Table medical_images n'existe pas"

**Cause:** Migration SQL non exécutée

**Solution:**
```bash
# Se connecter à la DB PostgreSQL
psql $DATABASE_URL

# Exécuter le script
\i backend/sql/schema/create_medical_images_table.sql

# Vérifier
\dt medical_images
```

---

## 8. Support

**Documentation:**
- Guide complet: `/docs/MEDICAL_IMAGE_ANALYSIS_GUIDE.md`
- Tests: `/llm/tests/test_vision_integration.py`
- Schéma DB: `/backend/sql/schema/create_medical_images_table.sql`

**Coûts estimés (Production):**
- DigitalOcean Spaces: $5/mois (250GB)
- PostgreSQL Managed: $15/mois (1GB)
- Anthropic Claude Vision: $20-50/mois (500-1000 analyses)
- **Total:** ~$40-70/mois

---

**Dernière mise à jour:** 2025-10-14
**Version:** 1.0.0
**Contact:** Intelia Expert Team
