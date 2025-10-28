# Résumé du Renommage: ai-service → rag

**Date:** 2025-10-28
**Statut:** ✅ Modifications terminées (sans push)

---

## ✅ FICHIERS MODIFIÉS

### 1. GitHub Actions Workflow
**Fichier:** `.github/workflows/deploy.yml`

**Modifications:**
- Ligne 15: Output `ai-service-changed` → `rag-changed`
- Ligne 31-32: Filtre `ai-service:` → `rag:`
- Ligne 191: Job `build-ai-service` → `build-rag`
- Ligne 193: Condition `ai-service-changed` → `rag-changed`
- Ligne 238: Context `./ai-service` → `./rag`
- Lignes 241-247: Tags Docker `ai-service:*` → `rag:*`
- Ligne 390: Needs `build-ai-service` → `build-rag`
- Cleanup job: Références `ai-service` → `rag`

### 2. Backend - Widget API
**Fichier:** `backend/app/api/v1/widget.py`

**Modifications:**
- Ligne 35-36: Commentaire et variable `AI_SERVICE_URL` → `RAG_URL`
- Variable d'env: `AI_SERVICE_INTERNAL_URL` → `RAG_INTERNAL_URL`
- Fallback: `"http://ai-service:8080"` → `"http://rag:8080"`
- Toutes les références à `AI_SERVICE_URL` → `RAG_URL`

### 3. Backend - WhatsApp Webhooks
**Fichier:** `backend/app/api/v1/whatsapp_webhooks.py`

**Modifications:**
- Ligne 67: Commentaire "AI Service" → "RAG Service"
- Ligne 70: `AI_SERVICE_URL` → `RAG_URL`
- Variable d'env: `AI_SERVICE_INTERNAL_URL` → `RAG_INTERNAL_URL`
- Fallback simplifié: `"http://rag:8080"`
- Ligne 71: `AI_CHAT_ENDPOINT` → `RAG_CHAT_ENDPOINT`
- Toutes les références dans le fichier

### 4. Frontend - Chat Stream
**Fichier:** `frontend/app/api/chat/stream/route.ts`

**Modifications:**
- Ligne 22: Commentaire `AI_SERVICE_INTERNAL_URL` → `RAG_INTERNAL_URL`
- Ligne 27: `AI_SERVICE_BACKEND_URL` → `RAG_BACKEND_URL`
- Variable d'env: `AI_SERVICE_INTERNAL_URL` → `RAG_INTERNAL_URL`
- Fallback simplifié: `"http://rag:8080"`
- Ligne 28: `AI_SERVICE_STREAM_URL` → `RAG_STREAM_URL`
- Toutes les références dans le fichier

### 5. Prometheus Configuration
**Fichier:** `prometheus-service/prometheus.yml`

**Modifications:**
- Ligne 22: Job name `intelia-ai-service` → `intelia-rag`
- Ligne 26: Target `ai-service:8080` → `rag:8080`

---

## 📝 VARIABLES D'ENVIRONNEMENT

### Sur DigitalOcean App Platform (DÉJÀ CONFIGURÉ):
```bash
RAG_INTERNAL_URL=http://rag:8080
```

### À supprimer après validation:
```bash
AI_SERVICE_INTERNAL_URL  # Ancienne variable
```

---

## ⏭️ PROCHAINES ÉTAPES

### Avant le push:
1. **Renommer le répertoire:** `git mv ai-service rag`
   - Actuellement impossible car des processus tournent dans ai-service
   - Arrêter tous les shells/serveurs en background
   - Puis exécuter la commande

### Après le push:
1. **Vérifier le déploiement GitHub Actions**
   - Le workflow créera automatiquement le repository `rag` dans Container Registry
   - Vérifier que les images sont bien taguées `rag:main`, `rag:latest`

2. **Vérifier DigitalOcean App Platform**
   - Le service devrait redémarrer avec le nouveau nom
   - DNS interne: `http://rag:8080` devrait fonctionner
   - Prometheus devrait scraper les métriques

3. **Tester les fonctionnalités**
   - Chat frontend
   - WhatsApp webhook
   - Widget externe

4. **Cleanup (après validation)**
   - Supprimer la variable `AI_SERVICE_INTERNAL_URL`
   - Nettoyer l'ancien repository `ai-service` du Container Registry

---

## 🔍 VERIFICATION RAPIDE

```bash
# Vérifier les modifications
git diff --stat

# Voir les fichiers modifiés
git status --short

# Vérifier deploy.yml
grep "rag" .github/workflows/deploy.yml | head -5

# Vérifier backend
grep "RAG_URL" backend/app/api/v1/widget.py
grep "RAG_URL" backend/app/api/v1/whatsapp_webhooks.py

# Vérifier frontend
grep "RAG_BACKEND_URL" frontend/app/api/chat/stream/route.ts

# Vérifier prometheus
grep "rag" prometheus-service/prometheus.yml
```

---

## ⚠️ IMPORTANT

**Le répertoire `ai-service` n'a PAS été renommé en `rag` car:**
- Des processus Python/uvicorn tournent actuellement dans ce répertoire
- Le renommage doit être fait quand aucun processus n'utilise le répertoire
- Commande à exécuter: `git mv ai-service rag`

**Toutes les autres modifications sont prêtes pour le push!**

