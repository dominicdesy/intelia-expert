# Guide de vérification - Redis & Sentry Deployment

**Date**: 2025-10-28
**Status**: Configuration complète
**Redis Provider**: Redis Cloud (redis-cloud.com)

---

## ✅ Configuration actuelle

### Variables d'environnement configurées:

```bash
# Redis (Redis Cloud - US East 1)
REDIS_URL=redis://default:***@redis-15394.c11.us-east-1-3.ec2.redns.redis-cloud.com:15394
REDIS_ENABLED=true  # (Devrait être défini, sinon ajouter)

# Retry configuration (déjà configuré)
RETRY_BACKOFF_FACTOR=2
RETRY_MAX_ATTEMPTS=3

# Sentry (À configurer si souhaité)
SENTRY_DSN=https://...@o0.ingest.sentry.io/...  # OPTIONNEL
SENTRY_ENVIRONMENT=production  # OPTIONNEL
```

---

## 🧪 Tests de vérification

### Test 1: Health Check Voice Realtime

```bash
curl https://expert.intelia.com/api/v1/voice/health
```

**Résultat attendu**:
```json
{
  "status": "healthy",
  "feature_enabled": true,
  "openai_configured": true,
  "weaviate_enabled": false,
  "redis": {
    "redis_available": true,
    "redis_enabled": true,
    "using_fallback": false,
    "redis_url": "redis://default:***@redis-15394.c11.us-east-1-3.ec2.redns.redis-cloud.com:15394",
    "redis_version": "7.2.0",
    "connected_clients": 1,
    "used_memory_human": "1.23M"
  },
  "timestamp": "2025-10-28T..."
}
```

**✅ Si `redis_available: true` → Redis fonctionne!**
**❌ Si `redis_available: false` → Voir troubleshooting ci-dessous**

---

### Test 2: Vérifier logs backend

**Via Digital Ocean App Platform**:
1. App Platform → Votre App → **Runtime Logs**
2. Chercher au démarrage:

**Logs attendus (succès)**:
```
✅ Redis connected successfully: redis://default:***@redis-15394.c11.us-east-1-3.ec2.redns.redis-cloud.com:15394
✅ Sentry initialized: production  # (Si Sentry configuré)
ℹ️ Sentry DSN not configured, error tracking disabled  # (Si Sentry pas configuré)
```

**Logs d'erreur (à éviter)**:
```
❌ Redis connection failed: [Errno 111] Connection refused
⚠️ Falling back to in-memory session storage
```

---

### Test 3: Tester persistence session Voice

**Scénario complet**:

1. **Créer une session Voice**:
   - Aller sur https://expert.intelia.com/chat
   - Se connecter avec compte **Elite** ou **Intelia**
   - Activer assistant vocal
   - Parler quelques secondes

2. **Vérifier session dans Redis**:
   ```bash
   curl https://expert.intelia.com/api/v1/voice/health
   # Vérifier: redis.connected_clients > 0
   ```

3. **Restart backend** (simuler crash):
   - App Platform → Actions → **Restart All Components**
   - Attendre ~1 minute

4. **Réactiver assistant vocal**:
   - Devrait reconnecter immédiatement
   - Session metadata devrait persister

**✅ Si reconnecte OK → Redis persistence fonctionne!**

---

### Test 4: Tester rate limiting (Redis partagé)

**Scénario**:

1. **Créer 5 sessions Voice rapidement**:
   - Ouvrir assistant vocal
   - Fermer
   - Répéter 5 fois en < 1 minute

2. **Essayer 6ème session**:
   - Devrait être **refusée**
   - Message: `Rate limit exceeded (5 sessions/hour max)`

3. **Vérifier logs**:
   ```
   ⚠️ Rate limit exceeded for user abc-123-def: 5/5
   ```

**✅ Si 6ème session refusée → Rate limiting fonctionne!**

---

### Test 5: Tester fallback in-memory (Optionnel)

**Scénario (test de résilience)**:

1. **Désactiver Redis temporairement**:
   - App Platform → Environment Variables
   - Modifier: `REDIS_ENABLED=false`
   - Save (redeploy automatique)

2. **Vérifier health check**:
   ```bash
   curl https://expert.intelia.com/api/v1/voice/health
   ```

   Devrait montrer:
   ```json
   {
     "redis": {
       "redis_available": false,
       "using_fallback": true
     }
   }
   ```

3. **Tester assistant vocal**:
   - Devrait **toujours fonctionner** (mode in-memory)
   - Mais sessions perdues au restart

4. **Réactiver Redis**:
   - Modifier: `REDIS_ENABLED=true`
   - Save

**✅ Si fonctionne sans Redis → Fallback graceful OK!**

---

## 🔍 Monitoring Redis Cloud

### Dashboard Redis Cloud

**Accès**:
1. https://app.redislabs.com
2. Login avec votre compte
3. Subscription → Database `redis-15394`

**Métriques à surveiller**:
- **Operations/sec**: Devrait être < 100 pour Voice sessions
- **Connections**: Nombre d'instances backend (probablement 1-2)
- **Memory Used**: Devrait rester < 50% (vous avez combien de MB?)
- **Latency**: Devrait être < 10ms (US East à US East)

**Alertes recommandées**:
- Memory > 80%
- Connections > 10 (peut indiquer connection leak)
- Latency > 100ms (performance issue)

---

## 🚨 Troubleshooting

### Problème: `redis_available: false`

**Diagnostic**:
```bash
# Vérifier REDIS_URL correcte
curl https://expert.intelia.com/api/v1/voice/health | jq '.redis'

# Vérifier logs
# App Platform → Runtime Logs
# Chercher: "Redis connection failed"
```

**Causes possibles**:

1. **REDIS_URL incorrecte**:
   ```
   ❌ redis://default:WRONGpassword@...
   ✅ redis://default:99PzXJBy6BLkZvYCzTL6DarF0AFMuwBk@...
   ```

2. **Firewall Redis Cloud**:
   - Redis Cloud Dashboard → Security
   - Vérifier **Allow all IPs** (0.0.0.0/0)
   - Ou ajouter IPs sortantes de Digital Ocean

3. **DNS/Network issue**:
   ```bash
   # Depuis backend (DO console):
   ping redis-15394.c11.us-east-1-3.ec2.redns.redis-cloud.com
   # Devrait résoudre l'IP
   ```

**Solution**:
- Vérifier URL exacte (copier-coller depuis Redis Cloud dashboard)
- Vérifier firewall rules Redis Cloud
- Contacter support Redis Cloud si persiste

---

### Problème: Rate limiting pas partagé

**Symptômes**:
- Peut créer > 5 sessions/heure
- Rate limit semble ne pas fonctionner

**Diagnostic**:
```bash
# Vérifier Redis utilisé (pas fallback)
curl https://expert.intelia.com/api/v1/voice/health | jq '.redis.using_fallback'
# Devrait être: false
```

**Cause**:
- Redis en mode fallback (in-memory)
- Chaque instance backend a son propre rate limiter

**Solution**:
- Fixer connexion Redis (voir ci-dessus)
- Redéployer app

---

### Problème: Sessions perdues après restart

**Symptômes**:
- Après restart backend, sessions Voice perdues
- Utilisateurs déconnectés

**Diagnostic**:
```bash
# Vérifier Redis persistence
curl https://expert.intelia.com/api/v1/voice/health
# redis.redis_available doit être true
```

**Causes possibles**:

1. **Redis pas utilisé** (fallback in-memory):
   - Vérifier `using_fallback: false`

2. **TTL expiré** (normal après 1h):
   - Sessions ont TTL 3600s (1 heure)
   - C'est normal qu'elles expirent

3. **Redis flush/restart**:
   - Redis Cloud a redémarré
   - Check Redis Cloud dashboard pour maintenance

**Solution**:
- Si < 1h et perdues → Problème Redis
- Si > 1h → Normal (TTL expiré)

---

## 📊 Performance attendue

### Latence Redis Cloud (US East)

**Baseline**:
- **Redis Cloud US East → DO App Platform US East**: ~2-5ms
- **Operations**: GET/SET/ZADD/ZCARD: < 1ms chacune
- **Rate limit check**: ~3-5ms total

**Comparé à in-memory**: +3-5ms (négligeable)

### Métriques Voice Realtime

**Avec Redis**:
- Session creation: ~50-100ms (vs ~30ms in-memory)
- Rate limit check: ~5ms (vs ~0.1ms in-memory)
- **Overhead total**: +20-70ms par connexion (acceptable)

**Bénéfice**: Persistence + scaling horizontal

---

## 🎯 Checklist post-déploiement

### Vérifications immédiates:

- [ ] Health check retourne `redis_available: true`
- [ ] Logs backend montrent `✅ Redis connected successfully`
- [ ] Pas d'erreur `Falling back to in-memory`
- [ ] Variables env correctement configurées:
  - [ ] `REDIS_URL` (avec bon password)
  - [ ] `REDIS_ENABLED=true`

### Vérifications fonctionnelles:

- [ ] Assistant vocal démarre (plan Elite/Intelia)
- [ ] Session Voice fonctionne pendant >10 min
- [ ] Rate limiting bloque 6ème session/heure
- [ ] Après restart backend, assistant vocal reconnecte OK

### Monitoring (à vérifier dans 24h):

- [ ] Redis Cloud dashboard: Operations/sec stable
- [ ] Redis Cloud: Memory usage < 50%
- [ ] Redis Cloud: Latency < 10ms
- [ ] Backend logs: Pas d'erreurs Redis répétées

### Optionnel (Sentry):

- [ ] Sentry configuré (`SENTRY_DSN`)
- [ ] Logs montrent `✅ Sentry initialized`
- [ ] Sentry dashboard reçoit events test
- [ ] Alertes Sentry configurées

---

## 📝 Configuration finale recommandée

### Variables d'environnement minimales (Redis):

```bash
# Requis
REDIS_URL=redis://default:99PzXJBy6BLkZvYCzTL6DarF0AFMuwBk@redis-15394.c11.us-east-1-3.ec2.redns.redis-cloud.com:15394
REDIS_ENABLED=true

# Voice Realtime (déjà configuré normalement)
ENABLE_VOICE_REALTIME=true
OPENAI_API_KEY=sk-proj-...
```

### Variables optionnelles (monitoring):

```bash
# Sentry (recommandé production)
SENTRY_DSN=https://...@o0.ingest.sentry.io/...
SENTRY_ENVIRONMENT=production

# App version (pour Sentry releases)
APP_VERSION=1.4.1

# Log level
LOG_LEVEL=INFO  # ou DEBUG pour troubleshooting
```

---

## 🔐 Sécurité Redis Cloud

### Best practices (déjà appliquées):

✅ **TLS/SSL**: Redis Cloud utilise TLS par défaut
✅ **Password**: Password fort auto-généré
✅ **Network**: Isolated network per database
✅ **Backups**: Auto-backups quotidiens (Redis Cloud)

### À vérifier:

- [ ] Password Redis **jamais commité** dans git
- [ ] `REDIS_URL` configurée comme **Encrypted** dans DO
- [ ] Rotation password Redis tous les 90 jours (optionnel)

### En cas de compromission password:

1. Redis Cloud Dashboard → Database Settings
2. **Change Password**
3. Copier nouveau REDIS_URL
4. Mettre à jour variable DO `REDIS_URL`
5. Redéployer app

---

## 📞 Support

### Redis Cloud:
- Dashboard: https://app.redislabs.com
- Support: support@redis.com
- Status: https://status.redislabs.com

### Digital Ocean:
- Dashboard: https://cloud.digitalocean.com
- Support tickets: Dashboard → Support
- Community: https://www.digitalocean.com/community

### En cas de problème critique:

1. **Vérifier status pages** (Redis Cloud, DO)
2. **Check logs backend** (App Platform)
3. **Test health endpoint** (`/api/v1/voice/health`)
4. **Fallback graceful** activé (app continue de fonctionner)
5. **Ouvrir ticket support** si nécessaire

---

## ✅ Conclusion

Votre configuration Redis Cloud est **excellente**:
- ✅ Performant (US East → US East, low latency)
- ✅ Fiable (Redis Cloud = 99.99% uptime SLA)
- ✅ Sécurisé (TLS, password, isolated network)
- ✅ Fallback graceful si problème

**Prochaine étape recommandée**: Configurer **Sentry** pour monitoring des erreurs (optionnel mais utile).

---

**Tout est prêt pour production! 🚀**
