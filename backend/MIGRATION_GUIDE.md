# 🔄 Guide de Migration - Architecture Base de Données

## 📋 Vue d'ensemble

Cette migration sépare clairement les responsabilités entre deux bases de données :

### **PostgreSQL (DigitalOcean)** - Données applicatives
- ✅ `conversations` - Historique complet questions/réponses
- ✅ `feedback` - Retours utilisateurs
- ✅ `invitations` - Système d'invitations
- ✅ `user_questions_complete` (vue) - Analytics

### **Supabase** - Authentification et profils
- ✅ `auth.users` - Authentification (géré automatiquement)
- ✅ `public.users` - Profils utilisateurs étendus

---

## 🚀 Étapes de Migration

### **1. Créer le schéma PostgreSQL**

Exécutez ce script dans PostgreSQL (DigitalOcean) :

```bash
psql $DATABASE_URL < backend/db_schema_postgresql.sql
```

**Vérifie** :
- ✅ Table `conversations` créée
- ✅ Table `feedback` créée
- ✅ Table `invitations` créée
- ✅ Vue `user_questions_complete` créée
- ✅ Index créés

---

### **2. Créer le schéma Supabase**

Exécutez ce script dans l'éditeur SQL de Supabase :

```sql
-- Copier le contenu de backend/db_schema_supabase.sql
```

**Vérifie** :
- ✅ Table `public.users` créée
- ✅ Trigger de synchronisation `auth.users` → `public.users` actif
- ✅ Row Level Security (RLS) activée
- ✅ Politiques RLS créées

---

### **3. Migrer les utilisateurs existants (si nécessaire)**

Si des utilisateurs existent déjà dans `auth.users` mais pas dans `public.users` :

```sql
-- Dans Supabase SQL Editor
INSERT INTO public.users (id, email, email_verified)
SELECT
    id,
    email,
    email_confirmed_at IS NOT NULL
FROM auth.users
ON CONFLICT (id) DO NOTHING;
```

---

### **4. Mettre à jour le backend**

#### **A. Installer les dépendances**

```bash
pip install supabase-py psycopg2-binary
```

#### **B. Variables d'environnement**

Ajouter à `.env` :

```bash
# PostgreSQL (DigitalOcean) - Données applicatives
DATABASE_URL=postgresql://user:password@host:port/database

# Supabase - Auth et profils
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Pour admin
```

#### **C. Remplacer stats_fast.py**

```bash
cd backend/app/api/v1
cp stats_fast.py stats_fast_OLD.py  # Backup
cp stats_fast_fixed.py stats_fast.py
```

#### **D. Initialiser les connexions**

Mettre à jour `backend/app/main.py` :

```python
from app.core.database import init_all_databases, close_all_databases

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting application...")
    init_all_databases()  # Initialise PostgreSQL + Supabase

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🔒 Shutting down...")
    close_all_databases()
```

---

### **5. Mettre à jour l'enregistrement des conversations**

Le frontend doit appeler `/api/v1/conversations/save` après chaque question/réponse.

Vérifier dans `frontend/app/chat/hooks/useChatStore.ts` ou similaire :

```typescript
// Après avoir reçu une réponse
await apiClient.postSecure('conversations/save', {
  conversation_id: sessionId,
  question: question,
  response: response,
  user_id: userId,  // UUID from Supabase auth
  timestamp: new Date().toISOString(),
  source: 'llm_streaming_agent',
  metadata: {}
});
```

---

## 🧪 Tests

### **Test 1: Vérifier PostgreSQL**

```bash
# Se connecter à PostgreSQL
psql $DATABASE_URL

# Vérifier les tables
\dt

# Vérifier la structure de conversations
\d conversations

# Tester la vue
SELECT COUNT(*) FROM user_questions_complete;
```

### **Test 2: Vérifier Supabase**

Dans l'éditeur SQL Supabase :

```sql
-- Vérifier les utilisateurs
SELECT id, email, first_name, last_name, plan FROM public.users LIMIT 5;

-- Vérifier le trigger
SELECT tgname, tgtype FROM pg_trigger WHERE tgname = 'on_auth_user_created';

-- Vérifier RLS
SELECT tablename, policyname FROM pg_policies WHERE tablename = 'users';
```

### **Test 3: Health Check**

```bash
curl http://localhost:8000/api/v1/stats-fast/health
```

Devrait retourner :

```json
{
  "status": "healthy",
  "databases": {
    "postgresql": {"status": "healthy"},
    "supabase": {"status": "healthy"}
  }
}
```

### **Test 4: Sauvegarder une conversation**

```bash
curl -X POST http://localhost:8000/api/v1/conversations/save \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
    "question": "Test question",
    "response": "Test response",
    "user_id": "<user-uuid-from-supabase>",
    "timestamp": "2025-10-11T12:00:00Z"
  }'
```

### **Test 5: Dashboard avec données croisées**

```bash
curl http://localhost:8000/api/v1/stats-fast/dashboard \
  -H "Authorization: Bearer $JWT_TOKEN"
```

Vérifier que `billing_stats.top_users` contient :
- ✅ `email` (depuis Supabase)
- ✅ `first_name` (depuis Supabase)
- ✅ `last_name` (depuis Supabase)
- ✅ `question_count` (depuis PostgreSQL)

---

## 📊 Schéma d'Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│                     (Next.js / React)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─── Auth Requests ───────────┐
                              │                             │
                              ├─── Conversation Requests ───┤
                              │                             │
                              └─── Analytics Requests ──────┤
                                                            │
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                      │
│                                                             │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │   app/core/      │         │   app/api/v1/           │  │
│  │   database.py    │────────▶│   stats_fast.py         │  │
│  │                  │         │   conversations.py      │  │
│  │ - get_pg_conn()  │         │   auth.py               │  │
│  │ - get_supabase() │         └─────────────────────────┘  │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
           │                              │
           │                              │
┌──────────▼──────────────┐    ┌──────────▼─────────────────┐
│   PostgreSQL            │    │   Supabase PostgreSQL      │
│   (DigitalOcean)        │    │   (Cloud)                  │
│                         │    │                            │
│  📊 conversations       │    │  🔐 auth.users (auto)      │
│  💬 feedback            │    │  👤 public.users           │
│  📧 invitations         │    │                            │
│  📈 user_questions_*    │    │  🛡️  Row Level Security    │
└─────────────────────────┘    └────────────────────────────┘
```

---

## ⚠️ Points d'attention

### **1. Pas de JOIN direct entre les bases**

❌ **Incorrect** :
```sql
SELECT c.*, u.email
FROM conversations c
JOIN users u ON u.id = c.user_id  -- users n'est PAS dans PostgreSQL
```

✅ **Correct** :
```python
# 1. Récupérer les conversations depuis PostgreSQL
conversations = pg_query("SELECT * FROM conversations WHERE user_id = %s", [user_id])

# 2. Récupérer l'utilisateur depuis Supabase
user = get_user_from_supabase(user_id)

# 3. Combiner les données
result = {
    "user": user,
    "conversations": conversations
}
```

### **2. user_id est un UUID**

Toujours utiliser le format UUID :
```python
user_id = "843d440a-a7a7-45ee-96df-3568c37384b9"  # ✅
user_id = "dominic@intelia.com"  # ❌
```

### **3. status = 'active'**

Toujours filtrer les conversations actives :
```sql
SELECT * FROM conversations WHERE status = 'active'
```

### **4. Gestion des erreurs**

Toujours gérer les cas où l'utilisateur n'existe pas dans Supabase :
```python
user = get_user_from_supabase(user_id)
if not user:
    user = {
        "email": user_id,  # Fallback
        "first_name": "",
        "last_name": "",
        "plan": "free"
    }
```

---

## 🔍 Troubleshooting

### Problème : "relation public.users does not exist"

**Cause** : Tentative de JOIN avec `users` dans PostgreSQL

**Solution** : Utiliser `get_user_from_supabase()` au lieu d'un JOIN

---

### Problème : "Table conversations is empty"

**Cause** : Le frontend ne sauvegarde pas les conversations

**Solution** : Vérifier que `/api/v1/conversations/save` est appelé après chaque Q&R

---

### Problème : "Top users table is empty"

**Cause 1** : Aucune conversation dans PostgreSQL
**Cause 2** : Le JOIN essaie d'accéder à `users` dans PostgreSQL

**Solution** :
1. Vérifier `SELECT COUNT(*) FROM conversations`
2. Utiliser `stats_fast_fixed.py` au lieu de `stats_fast.py`

---

## 📝 Checklist de Migration

- [ ] PostgreSQL : Schéma créé (`db_schema_postgresql.sql`)
- [ ] PostgreSQL : Tables `conversations`, `feedback`, `invitations` créées
- [ ] PostgreSQL : Vue `user_questions_complete` créée
- [ ] Supabase : Table `public.users` créée
- [ ] Supabase : Trigger de synchronisation activé
- [ ] Supabase : RLS activée et politiques créées
- [ ] Backend : `app/core/database.py` importé
- [ ] Backend : `stats_fast.py` remplacé par `stats_fast_fixed.py`
- [ ] Backend : `main.py` initialise les connexions
- [ ] Frontend : Appel à `/conversations/save` implémenté
- [ ] Tests : Health check OK
- [ ] Tests : Sauvegarde conversation OK
- [ ] Tests : Dashboard affiche top users avec noms

---

## 🚀 Déploiement

### **Environnement de dev**

```bash
# 1. Appliquer les schémas
psql $DATABASE_URL < backend/db_schema_postgresql.sql

# 2. Copier les fichiers
cp backend/app/api/v1/stats_fast_fixed.py backend/app/api/v1/stats_fast.py

# 3. Redémarrer le backend
uvicorn app.main:app --reload
```

### **Production (DigitalOcean)**

```bash
# 1. Appliquer PostgreSQL via DigitalOcean console ou script
# 2. Appliquer Supabase via SQL Editor
# 3. Déployer le backend via git push
git add .
git commit -m "feat: Migrate to PostgreSQL + Supabase architecture"
git push origin main
```

---

## 📚 Documentation Supplémentaire

- `db_schema_postgresql.sql` - Schéma complet PostgreSQL
- `db_schema_supabase.sql` - Schéma complet Supabase
- `app/core/database.py` - Module de connexion aux bases
- `stats_fast_fixed.py` - Exemple d'utilisation cross-database

---

**Date de création** : 2025-10-11
**Version** : 1.0
**Auteur** : Claude Code
