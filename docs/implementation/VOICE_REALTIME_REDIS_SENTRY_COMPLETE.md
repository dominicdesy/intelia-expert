# Voice Realtime - Redis & Sentry Implementation

**Date**: 2025-10-28
**Status**: ✅ Implémenté
**Version**: 1.0.0
**Tasks**: #3 Voice Redis Migration, #4 Voice Monitoring Sentry, #5 Voice JWT Auth

---

## 📋 Vue d'ensemble

Implémentation complète de:
1. **Redis** pour persistence des sessions Voice & rate limiting
2. **Sentry** pour error tracking et monitoring
3. **Vérification JWT Auth** (déjà implémenté, documenté)

---

## ✅ Ce qui a été implémenté

### 1. Redis Session Storage (#3)

**Problème résolu**:
- ❌ Sessions Voice stockées en mémoire → perdues au redémarrage
- ❌ Rate limiting en mémoire → pas de partage entre instances

**Solution**:
- ✅ Service Redis avec fallback graceful vers in-memory
- ✅ Sessions persistées dans Redis (TTL 1h)
- ✅ Rate limiting partagé entre instances
- ✅ Auto-reconnexion si Redis down

**Fichiers créés/modifiés**:
- ✨ `backend/app/services/redis_session_service.py` (nouveau)
- ✏️ `backend/app/api/v1/voice_realtime.py` (modifié)
- ✏️ `backend/requirements.txt` (+redis>=5.0.0)

**API Redis Service**:
```python
from app.services.redis_session_service import redis_session_service

# Session management
redis_session_service.save_session(session_id, data)
redis_session_service.get_session(session_id)
redis_session_service.delete_session(session_id)

# Rate limiting
redis_session_service.check_rate_limit(user_id, max_sessions=5, window_seconds=3600)
redis_session_service.reset_rate_limit(user_id)

# Health check
redis_session_service.health_check()
```

---

### 2. Sentry Error Tracking (#4)

**Problème résolu**:
- ❌ Pas de monitoring des erreurs Voice en production
- ❌ Difficile de debugger sans logs centralisés

**Solution**:
- ✅ Sentry configuré globalement dans `main.py`
- ✅ Capture automatique des erreurs FastAPI
- ✅ Logging intégré (ERROR+ envoyé à Sentry)
- ✅ Performance monitoring (10% sample rate)
- ✅ Configuration optionnelle via env vars

**Fichiers modifiés**:
- ✏️ `backend/app/main.py` (ajout Sentry init)
- ✏️ `backend/requirements.txt` (+sentry-sdk[fastapi]>=1.40.0)

**Configuration Sentry**:
```python
# Dans main.py (déjà fait)
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        integrations=[FastApiIntegration(), LoggingIntegration()],
        release=os.getenv("APP_VERSION", "1.4.1")
    )
```

---

### 3. JWT Auth Voice WebSocket (#5)

**Status**: ✅ **DÉJÀ IMPLÉMENTÉ** (vérification faite)

**Sécurité en place**:
- ✅ JWT token requis via query param `?token=JWT_HERE`
- ✅ Fonction `get_current_user_from_websocket()` déjà utilisée
- ✅ Plan verification: Voice réservé aux plans **Elite & Intelia**
- ✅ Rate limiting: 5 sessions/heure/utilisateur
- ✅ Session timeout: 10 minutes max

**Code (lignes 656-663 de voice_realtime.py)**:
```python
user = await get_current_user_from_websocket(websocket)
user_id = user.get("user_id")
user_email = user.get("email")
logger.info(f"✅ User authenticated: {user_email} (id: {user_id})")
```

**Flow de sécurité complet**:
```
1. Client ouvre WebSocket avec ?token=JWT
   ↓
2. Backend vérifie JWT (get_current_user_from_websocket)
   ↓
3. Vérif plan (Elite/Intelia requis)
   ↓
4. Rate limiting (Redis ou fallback)
   ↓
5. Session créée (max 10 min)
   ↓
6. Streaming bidirectionnel OpenAI Realtime
```

---

## 🔧 Configuration requise

### Variables d'environnement Digital Ocean App Platform

Voici **TOUTES les variables d'environnement** à ajouter:

```bash
# ============================================================================
# REDIS (Nouveau - Task #3)
# ============================================================================

# Option 1: DigitalOcean Managed Redis (RECOMMANDÉ)
REDIS_URL=redis://default:PASSWORD@db-redis-XXXXX.ondigitalocean.com:25061
REDIS_ENABLED=true

# Option 2: Redis externe (AWS ElastiCache, Upstash, etc.)
REDIS_URL=redis://username:password@host:port/0
REDIS_ENABLED=true

# Option 3: Pas de Redis (fallback in-memory) - PAS RECOMMANDÉ
REDIS_ENABLED=false

# ============================================================================
# SENTRY (Nouveau - Task #4)
# ============================================================================

# Option 1: Avec Sentry (RECOMMANDÉ pour production)
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_ENVIRONMENT=production  # ou staging, development

# Option 2: Sans Sentry (développement local)
# (Ne pas définir SENTRY_DSN)

# ============================================================================
# VOICE REALTIME (Déjà existants - Task #5)
# ============================================================================

ENABLE_VOICE_REALTIME=true
OPENAI_API_KEY=sk-proj-...  # Requis pour Voice
WEAVIATE_URL=https://...  # Optionnel pour RAG
WEAVIATE_API_KEY=...  # Si Weaviate activé

# ============================================================================
# AUTRES VARIABLES (Déjà configurées normalement)
# ============================================================================

DATABASE_URL=postgresql://...
STRIPE_SECRET_KEY=sk_live_...
# ... etc (vos variables existantes)
```

---

## 📦 Setup Digital Ocean

### Étape 1: Créer Managed Redis

**Via Dashboard DO**:
1. Databases → Create → Redis
2. Choisir datacenter (même région que votre app)
3. Taille: **Basic** (512MB suffit pour Voice)
4. Nom: `voice-sessions-redis`
5. Créer

**Récupérer connexion**:
```
Connection String → copier
Format: redis://default:PASSWORD@host:25061
```

### Étape 2: Lier Redis à l'app

**Via App Platform**:
1. Votre app → Settings → App-Level Environment Variables
2. Add Variable:
   - Key: `REDIS_URL`
   - Value: `redis://default:PASSWORD@...`
   - Type: Encrypted ✅
3. Add Variable:
   - Key: `REDIS_ENABLED`
   - Value: `true`
   - Type: Plain text
4. Save

### Étape 3: Configurer Sentry (Optionnel)

**Créer projet Sentry**:
1. Aller sur sentry.io
2. Create Project → FastAPI
3. Copier DSN: `https://...@o0.ingest.sentry.io/...`

**Ajouter à DO**:
1. App Platform → Environment Variables
2. Add Variable:
   - Key: `SENTRY_DSN`
   - Value: `https://...`
   - Type: Encrypted ✅
3. Add Variable:
   - Key: `SENTRY_ENVIRONMENT`
   - Value: `production`
   - Type: Plain text

### Étape 4: Redéployer

```bash
# Les changements requirements.txt déclencheront rebuild automatique
# Ou manuellement:
git push origin main

# Sur DO App Platform:
# → Automatic deploy démarrera
# → Installer redis + sentry-sdk
# → Redémarrer app avec nouvelles variables
```

---

## 🧪 Tests

### Test 1: Vérifier Redis

```bash
# Health check
curl https://expert.intelia.com/api/v1/voice/health

# Réponse attendue:
{
  "status": "healthy",
  "feature_enabled": true,
  "openai_configured": true,
  "weaviate_enabled": false,
  "redis": {
    "redis_available": true,
    "redis_enabled": true,
    "using_fallback": false,
    "redis_url": "redis://default:***@host:25061",
    "redis_version": "7.0.12",
    "connected_clients": 1,
    "used_memory_human": "1.23M"
  },
  "timestamp": "2025-10-28T..."
}
```

### Test 2: Vérifier Sentry

```bash
# Déclencher une erreur test
# Dans un endpoint temporaire ou logs:
import sentry_sdk
sentry_sdk.capture_message("Test Sentry integration", level="info")

# Aller sur sentry.io → Issues
# → Devrait voir "Test Sentry integration"
```

### Test 3: Tester persistence sessions

**Scénario**:
1. Utilisateur crée session Voice
2. Backend restart (simulate)
3. Session devrait persister dans Redis

**Test**:
```bash
# 1. Créer session Voice depuis frontend
# (Ouvrir assistant vocal)

# 2. Vérifier Redis
curl https://expert.intelia.com/api/v1/voice/health
# → redis.connected_clients > 0

# 3. Restart backend
# (Sur DO: Manual restart ou redeploy)

# 4. Vérifier session toujours là
# (Réouvrir assistant vocal)
# → Devrait reconnecter sans problème
```

### Test 4: Tester rate limiting

```bash
# Créer 6 sessions Voice rapidement
# (Normalement limite = 5/heure)

# 6ème session devrait être refusée:
WebSocket Error 1008: "Rate limit exceeded (5 sessions/hour max)"
```

---

## 🔍 Monitoring & Debugging

### Logs à surveiller

```bash
# Logs backend (DO App Platform → Runtime Logs)

# Succès Redis:
✅ Redis connected successfully: redis://...

# Fallback in-memory:
⚠️ Redis connection failed: [Errno 111] Connection refused
⚠️ Falling back to in-memory session storage

# Sentry init:
✅ Sentry initialized: production

# Rate limiting:
⚠️ Rate limit exceeded for user abc123: 5/5
```

### Dashboard Sentry

**Issues à surveiller**:
- Erreurs WebSocket Voice (ConnectionError, TimeoutError)
- Erreurs OpenAI API (RateLimitError, APIError)
- Erreurs Redis (ConnectionError si down)

**Performance**:
- Latence WebSocket connection
- Durée des sessions Voice
- Taux d'erreur Voice vs total requests

### Métriques Redis (via DO Dashboard)

- **CPU Usage**: Devrait rester < 50%
- **Memory Usage**: Devrait rester < 80%
- **Connections**: Nombre d'instances backend connectées
- **Commands/sec**: Nombre d'opérations Redis

---

## 📊 Architecture finale

```
┌─────────────────────────────────────────────────────┐
│                    USER (Frontend)                  │
│              useVoiceRealtime.ts hook               │
└─────────────────┬───────────────────────────────────┘
                  │ WebSocket ?token=JWT
                  ↓
┌─────────────────────────────────────────────────────┐
│              BACKEND (FastAPI)                      │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  voice_realtime.py                           │  │
│  │  1. Accept WebSocket                         │  │
│  │  2. Verify JWT (get_current_user_from_ws)    │  │
│  │  3. Check plan (Elite/Intelia only)          │  │
│  │  4. Rate limit via Redis ←─────────────┐     │  │
│  │  5. Create VoiceRealtimeSession        │     │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  redis_session_service.py                    │  │
│  │  - save_session()                            │  │
│  │  - get_session()                             │  │
│  │  - check_rate_limit()                        │  │
│  │  - Fallback to in-memory if Redis down      │  │
│  └──────────────┬───────────────────────────────┘  │
│                 │                                   │
└─────────────────┼───────────────────────────────────┘
                  │
      ┌───────────┴──────────┬────────────────────┐
      ↓                      ↓                    ↓
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│   Redis     │    │  OpenAI Realtime │    │   Sentry    │
│  (Sessions) │    │      API         │    │  (Errors)   │
│             │    │                  │    │             │
│ DO Managed  │    │  Streaming       │    │  Dashboard  │
│ Redis DB    │    │  Audio <-> Text  │    │  Alerts     │
└─────────────┘    └──────────────────┘    └─────────────┘
```

---

## 🚨 Troubleshooting

### Problème: Redis connection failed

**Cause**: Redis URL incorrecte ou Redis down

**Solution**:
```bash
# 1. Vérifier Redis est running (DO Dashboard)
# 2. Vérifier REDIS_URL correcte
# 3. Vérifier firewall/network (Redis doit être accessible)

# Test connexion:
redis-cli -u $REDIS_URL ping
# → Devrait retourner PONG
```

### Problème: Sentry events not showing

**Cause**: SENTRY_DSN invalide ou environnement filtré

**Solution**:
```bash
# 1. Vérifier SENTRY_DSN correcte
# 2. Vérifier projet Sentry existe
# 3. Check environment filters dans Sentry settings

# Test manuel:
import sentry_sdk
sentry_sdk.capture_exception(Exception("Test error"))
```

### Problème: Rate limit pas partagé entre instances

**Cause**: Redis pas utilisé (fallback in-memory)

**Solution**:
```bash
# Vérifier logs backend:
# Si "Falling back to in-memory" → Redis connection issue
# Fix Redis connection, redeploy
```

### Problème: Sessions perdues après restart

**Cause**: Redis désactivé ou sessions TTL expiré

**Solution**:
```bash
# 1. Vérifier REDIS_ENABLED=true
# 2. Vérifier Redis accessible
# 3. Sessions ont TTL 1h (normal qu'elles expirent)
```

---

## 📝 Maintenance

### Mise à jour exchange rates

Non applicable pour Voice (pas de pricing)

### Mise à jour Redis version

```bash
# Sur DO Managed Redis:
# 1. Dashboard → Redis DB → Settings
# 2. Upgrade to latest version
# 3. Scheduled maintenance window
# 4. Auto-upgrade avec minimal downtime
```

### Rotation Sentry DSN

```bash
# Si DSN compromise:
# 1. Sentry Dashboard → Project Settings → Client Keys
# 2. Revoke old DSN
# 3. Create new DSN
# 4. Update DO env var SENTRY_DSN
# 5. Redeploy
```

---

## 🎯 Next Steps (Optionnel)

### Court terme

1. **Datadog metrics** (si budget)
   - Voice session duration metrics
   - OpenAI API latency tracking
   - Redis performance metrics

2. **Structured logging**
   - Remplacer logging standard par structlog
   - Logs JSON pour parsing automatique
   - Better query dans Sentry/Datadog

### Moyen terme

3. **Session replay Sentry**
   - Voir ce que l'utilisateur faisait avant erreur
   - Frontend integration required

4. **Redis Cluster** (si scaling)
   - Passer de Basic à Professional
   - High availability + auto-failover

### Long terme

5. **Multi-region Redis**
   - Redis global pour latence minimale
   - Geo-replication

---

## 📚 Références

- [Redis Python Client](https://redis-py.readthedocs.io/)
- [Sentry FastAPI Integration](https://docs.sentry.io/platforms/python/guides/fastapi/)
- [DigitalOcean Managed Redis](https://docs.digitalocean.com/products/databases/redis/)
- [Voice Realtime Phase 1](../reports/VOICE_REALTIME_PHASE1_COMPLETE.md)

---

## ✅ Checklist déploiement

- [ ] `requirements.txt` mis à jour (redis + sentry-sdk)
- [ ] Code Redis service créé
- [ ] Code Sentry init ajouté à main.py
- [ ] Variables env Digital Ocean configurées:
  - [ ] `REDIS_URL`
  - [ ] `REDIS_ENABLED=true`
  - [ ] `SENTRY_DSN` (optionnel)
  - [ ] `SENTRY_ENVIRONMENT=production`
- [ ] Managed Redis DB créé sur DO
- [ ] Projet Sentry créé (si utilisé)
- [ ] App redéployée
- [ ] Tests health check passent
- [ ] Test session Voice fonctionne
- [ ] Test rate limiting fonctionne
- [ ] Logs backend vérifiés (Redis connected, Sentry initialized)
- [ ] Dashboard Sentry vérifié (events arrivent)

---

**Implementation complète! Toutes les tâches #3, #4, #5 sont terminées. 🎉**
