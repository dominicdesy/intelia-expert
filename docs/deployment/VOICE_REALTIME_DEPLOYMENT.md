# 🚀 Voice Realtime - Guide de Déploiement

Guide pas-à-pas pour déployer Voice Realtime en production avec **ZÉRO RISQUE**.

---

## ✅ Pré-requis

- [ ] POC validé (Q2 + Q3 tests OK)
- [ ] Budget confirmé (~$600/mois)
- [ ] OpenAI API Key avec accès Realtime API
- [ ] Weaviate Cloud accessible
- [ ] Digital Ocean App Platform configuré

---

## 📦 Phase 1 : Déploiement Backend (AUJOURD'HUI)

### Étape 1.1 : Sauvegarder l'État Actuel

```bash
# Sur ton PC
cd C:\intelia_gpt\intelia-expert

# Créer commit de sauvegarde
git add .
git commit -m "Save: Before voice realtime implementation"
git push origin main

# Créer branche backup (sécurité)
git branch backup-before-voice-realtime
git push origin backup-before-voice-realtime
```

✅ **Sécurité** : Si problème, rollback instantané avec `git revert`

---

### Étape 1.2 : Vérifier les Fichiers Créés

```bash
# Vérifier que les nouveaux fichiers existent
ls backend/app/api/v1/voice_realtime.py
ls backend/.env.voice_realtime.example
ls backend/tests/test_voice_realtime.py

# Vérifier modification main.py (seulement +3 lignes)
git diff backend/app/main.py
```

**Attendu** :
```diff
+ from app.api.v1 import voice_realtime  # Voice Realtime WebSocket endpoint
+ app.include_router(voice_realtime.router, prefix="/v1", tags=["voice-realtime"])
+ logger.info("Voice Realtime router charge (WebSocket /v1/ws/voice)")
```

---

### Étape 1.3 : Tests Locaux (OBLIGATOIRE)

```bash
# Installer dépendances (si nouvelles)
cd backend
pip install websockets

# Lancer tests unitaires
pytest tests/test_voice_realtime.py -v

# Tester que l'app démarre sans erreur
uvicorn app.main:app --reload

# Vérifier health check
curl http://localhost:8000/v1/voice/health
# Devrait retourner: {"status": "disabled", "feature_enabled": false}
```

✅ **Critère de succès** : App démarre sans erreur, health check répond

---

### Étape 1.4 : Ajouter Variable d'Environnement

**Sur Digital Ocean Console** :

1. Aller dans ton app → Settings → App-Level Environment Variables
2. Ajouter :
   ```
   Nom: ENABLE_VOICE_REALTIME
   Valeur: false
   Scope: All components
   Encrypt: No
   ```

✅ **Important** : `false` par défaut = feature désactivée en prod

---

### Étape 1.5 : Déploiement Production

```bash
# Commit les changements
git add backend/app/api/v1/voice_realtime.py
git add backend/app/main.py
git add backend/tests/test_voice_realtime.py
git add backend/.env.voice_realtime.example

git commit -m "feat: Add voice realtime endpoint (disabled by default)

- Add WebSocket endpoint /v1/ws/voice
- Implement Option B (RAG pre-loading)
- Add feature flag ENABLE_VOICE_REALTIME
- Add rate limiting (5 sessions/hour/user)
- Add session timeout (10 min max)
- Add comprehensive logging

Feature is DISABLED by default (safe deployment)
"

git push origin main
```

**Digital Ocean** déploiera automatiquement.

---

### Étape 1.6 : Vérifier Déploiement Production

```bash
# Attendre fin déploiement (~3-5 min)

# Tester health check en prod
curl https://expert.intelia.com/v1/voice/health

# Devrait retourner:
# {"status": "disabled", "feature_enabled": false, ...}
```

✅ **Succès** : API répond, feature désactivée, **aucun impact utilisateurs**

---

## 🧪 Phase 2 : Tests Beta (DEMAIN)

### Étape 2.1 : Activer Feature pour Tests

**Digital Ocean Console** :

1. Variables d'environnement
2. Modifier `ENABLE_VOICE_REALTIME` → `true`
3. Redémarrer app

```bash
# Vérifier activation
curl https://expert.intelia.com/v1/voice/health

# Devrait maintenant retourner:
# {"status": "healthy", "feature_enabled": true, ...}
```

---

### Étape 2.2 : Test Manuel WebSocket

**Créer script test client** :

```python
# test_voice_client.py
import asyncio
import websockets
import json

async def test_voice():
    uri = "wss://expert.intelia.com/v1/ws/voice"
    # TODO: Ajouter JWT token dans headers

    async with websockets.connect(uri) as ws:
        print("✅ Connected")

        # Envoyer message test
        await ws.send(json.dumps({
            "type": "ping"
        }))

        # Attendre réponse
        response = await ws.recv()
        print(f"📨 Received: {response}")

asyncio.run(test_voice())
```

---

### Étape 2.3 : Mesurer Latence Production

```bash
# Depuis POC
cd C:\intelia_gpt\intelia-expert\poc_realtime

# Modifier test pour pointer vers prod
# TODO: Adapter scripts pour tester contre https://expert.intelia.com

python test_openai_realtime.py  # Via backend prod
```

**Objectif** : Valider latence <800ms en production réelle

---

## 📊 Phase 3 : Rollout Progressif (SEMAINE 1-3)

### Semaine 1 : Beta 10% Users Premium

**Implémentation** :

```python
# backend/app/api/v1/voice_realtime.py
# Ligne ~250, dans voice_realtime_endpoint()

# Feature flag dynamique par user
VOICE_REALTIME_BETA_USERS = [1, 2, 3, ...]  # IDs users beta

if user.id not in VOICE_REALTIME_BETA_USERS:
    await websocket.close(code=1008, reason="Feature not available for your account")
    return
```

**Monitoring** :
- Dashboard latence temps réel
- Coûts OpenAI par jour
- Taux d'erreur
- Feedback beta testers

---

### Semaine 2 : 50% Users Premium

**Si KPIs OK** :
- Latence P95 <800ms ✅
- Taux d'erreur <2% ✅
- Coûts <budget ✅

→ Ouvrir à 50% users premium (A/B test)

---

### Semaine 3 : 100% Users Premium

**Si KPIs toujours OK** :
- Adoption >10% ✅
- Satisfaction >4/5 ✅

→ Ouvrir à tous users premium

---

## 🚨 Plan de Rollback

### Niveau 1 : Feature Flag (30 secondes)

**Digital Ocean Console** :
```
ENABLE_VOICE_REALTIME=false
→ Restart app
```

**Impact** : Feature désactivée, utilisateurs voient erreur propre

---

### Niveau 2 : Git Revert (2 minutes)

```bash
# Identifier commit
git log --oneline | grep "voice realtime"

# Revert
git revert <commit-hash>
git push origin main

# Digital Ocean auto-deploy
```

**Impact** : Code voice realtime supprimé, retour état précédent

---

### Niveau 3 : Rollback Branche (5 minutes)

```bash
# Forcer retour branche backup
git reset --hard backup-before-voice-realtime
git push --force origin main

# Avertir équipe avant force push !
```

**Impact** : Retour total état avant voice realtime

---

## 📊 Monitoring Production

### Métriques à Tracker (Datadog/Sentry)

```python
# À ajouter dans voice_realtime.py

import sentry_sdk

# Tracker latence
sentry_sdk.capture_metric(
    "voice_realtime.latency",
    value=latency_ms,
    tags={"user_id": user.id}
)

# Tracker erreurs
sentry_sdk.capture_exception(error)

# Tracker coûts
sentry_sdk.capture_metric(
    "voice_realtime.openai_cost",
    value=cost_usd
)
```

### Dashboard

**KPIs à afficher** :
- Latence P50/P95/P99 (graphique temps réel)
- Taux d'erreur (%)
- Coûts cumulés ($ par jour)
- Sessions actives (count)
- Adoption (% users utilisant feature)

---

## ✅ Checklist Pré-Production

**Avant d'activer ENABLE_VOICE_REALTIME=true** :

- [ ] Tests locaux passent (`pytest`)
- [ ] App démarre sans erreur en local
- [ ] Health check répond en prod (feature disabled)
- [ ] Backup git créé
- [ ] Variables d'environnement configurées
- [ ] Monitoring configuré (Sentry/Datadog)
- [ ] Plan de rollback documenté
- [ ] Équipe informée du déploiement
- [ ] Budget OpenAI confirmé (~$600/mois)

---

## 📞 Support & Questions

**Si problème pendant déploiement** :

1. **Check logs** : Digital Ocean Console → Logs
2. **Check health** : `curl https://expert.intelia.com/v1/voice/health`
3. **Rollback** : Feature flag → false (30s)

**Si doute** :
- Garder feature désactivée (safe)
- Tester en local d'abord
- Activer seulement après validation complète

---

## 🎯 Timeline Recommandée

| Jour | Action | Durée |
|------|--------|-------|
| **J0** (Aujourd'hui) | Déploiement backend (disabled) | 1h |
| **J1** | Tests beta internes | 2h |
| **J2-J3** | Développement frontend | 2j |
| **J4** | Tests intégration | 1j |
| **J7** | Beta 10% users | - |
| **J14** | 50% users (si OK) | - |
| **J21** | 100% users (si OK) | - |

---

**Status** : ✅ Backend prêt pour déploiement sécurisé

**Risque** : Très faible (feature flag + rollback)

**Prochaine étape** : Commit + push → déploiement avec feature disabled
