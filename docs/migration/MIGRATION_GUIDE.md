# Guide de Migration: Conversations + Messages Architecture

## 🎯 Objectif

Migrer de l'ancienne architecture (conversations avec colonnes `question`/`response`) vers la nouvelle architecture (conversations + messages en tables séparées).

## ⚠️ Problème Actuel

**ERREUR**: La table `conversations` a une colonne `id` de type `TEXT` au lieu de `UUID`, ce qui empêche la création de la foreign key dans la table `messages`.

```
ERROR: foreign key constraint "messages_conversation_id_fkey" cannot be implemented
Detail: Key columns "conversation_id" and "id" are of incompatible types: uuid and text.
```

## 📋 Ordre d'Exécution des Scripts

### Étape 1: Vérifier la Structure Actuelle

**Fichier**: `check_conversations_structure.sql`

**But**: Comprendre l'état actuel de la table `conversations`

**Exécuter dans**: DigitalOcean PostgreSQL

```bash
# Dans votre client SQL (psql, DBeaver, etc.)
\i check_conversations_structure.sql
```

**Ce que vous devriez voir**:
- Colonne `id` avec type `TEXT` (problème à corriger)
- Colonne `session_id` avec type `TEXT` ou `UUID`
- Nombre de conversations existantes

---

### Étape 2: Corriger le Type de la Colonne ID

**Fichier**: `fix_conversations_id_type.sql`

**But**: Convertir `conversations.id` de `TEXT` vers `UUID`

**Exécuter dans**: DigitalOcean PostgreSQL

```bash
\i fix_conversations_id_type.sql
```

**Ce que fait ce script**:
1. ✅ Crée un backup automatique (`conversations_backup_20251011`)
2. ✅ Vérifie que les IDs existants sont des UUIDs valides
3. ✅ Convertit la colonne `id` en type `UUID`
4. ✅ Convertit la colonne `session_id` en type `UUID` si nécessaire
5. ✅ Vérifie que les données sont intactes

**⚠️ IMPORTANT**:
- Si la table contient des IDs qui ne sont PAS des UUIDs valides, le script échouera
- Dans ce cas, il faudra d'abord nettoyer ou régénérer les IDs invalides

---

### Étape 3: Créer la Table Messages

**Fichier**: `create_messages_table_only.sql`

**But**: Créer la table `messages` avec foreign key vers `conversations`

**Exécuter dans**: DigitalOcean PostgreSQL

```bash
\i create_messages_table_only.sql
```

**Ce que fait ce script**:
1. ✅ Crée la table `messages` avec foreign key vers `conversations(id)`
2. ✅ Crée les index pour optimiser les requêtes
3. ✅ Crée les fonctions helpers:
   - `create_conversation_with_messages()` - Créer conversation + 2 messages
   - `add_message_to_conversation()` - Ajouter un message
   - `get_conversation_messages()` - Récupérer tous les messages
   - `update_conversation_metadata()` - Fonction trigger
4. ✅ Crée le trigger `update_conversation_on_message_insert`
5. ✅ Crée la vue `conversation_stats`

---

### Étape 4: Vérifier que Tout Fonctionne

**Fichier**: `verify_migration_complete.sql`

**But**: Vérifier que toute l'architecture est correctement en place

**Exécuter dans**: DigitalOcean PostgreSQL

```bash
\i verify_migration_complete.sql
```

**Ce que vous devriez voir**:
- ✅ `conversations.id` est de type `uuid`
- ✅ Table `messages` existe
- ✅ Foreign key `messages.conversation_id` → `conversations.id` existe
- ✅ Les 4 fonctions helpers existent
- ✅ Le trigger `update_conversation_on_message_insert` existe
- ✅ La vue `conversation_stats` existe
- ✅ Test fonctionnel réussi

**Résultat attendu**:
```
✅ ✅ ✅ MIGRATION COMPLÈTE ET FONCTIONNELLE ✅ ✅ ✅
```

---

### Étape 5: Nettoyer les Tables Inutiles

**Fichier**: `cleanup_digitalocean_final.sql`

**But**: Supprimer les tables qui n'appartiennent plus à DigitalOcean

**Exécuter dans**: DigitalOcean PostgreSQL

```bash
\i cleanup_digitalocean_final.sql
```

**Ce que fait ce script**:
- ❌ Supprime `invitations` (maintenant dans Supabase)
- ❌ Supprime `invitations_cache` (obsolète)
- ❌ Supprime `questions_cache` (non utilisée)

---

## 🔧 En Cas de Problème

### Problème 1: IDs non-UUID dans conversations

**Symptôme**: `fix_conversations_id_type.sql` échoue avec:
```
❌ ERREUR: Des IDs ne sont pas des UUIDs valides. Migration impossible.
```

**Solution**: Deux options:

#### Option A: Supprimer les conversations invalides
```sql
-- Voir les IDs invalides
SELECT id, session_id, user_id, created_at
FROM conversations
WHERE id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- Les supprimer (⚠️ PERTE DE DONNÉES)
DELETE FROM conversations
WHERE id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
```

#### Option B: Régénérer les IDs
```sql
-- Créer une nouvelle table avec UUIDs
CREATE TABLE conversations_new AS
SELECT
    gen_random_uuid() as id,  -- Nouveau UUID
    session_id,
    user_id,
    -- ... autres colonnes
FROM conversations;

-- Remplacer l'ancienne table
DROP TABLE conversations CASCADE;
ALTER TABLE conversations_new RENAME TO conversations;
```

---

### Problème 2: Foreign Key échoue encore

**Symptôme**: `create_messages_table_only.sql` échoue avec erreur de type

**Vérification**:
```sql
-- Vérifier le type exact de conversations.id
SELECT data_type
FROM information_schema.columns
WHERE table_name = 'conversations' AND column_name = 'id';
```

**Solution**: Relancer `fix_conversations_id_type.sql`

---

### Problème 3: Données existantes à migrer

Si vous avez des données dans l'ancienne structure (colonnes `question`/`response`), il faudra créer un script de migration des données.

**Vérifier si nécessaire**:
```sql
-- Vérifier si les anciennes colonnes existent
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'conversations'
  AND column_name IN ('question', 'response', 'preview');
```

---

## 📊 Architecture Finale Attendue

### DigitalOcean PostgreSQL

**Tables**:
- ✅ `conversations` - Métadonnées des conversations
- ✅ `messages` - Messages individuels (Q&R)
- ✅ `analytics_cache` - Cache des analytics
- ✅ `billing_plans` - Plans de facturation
- ✅ `daily_openai_summary` - Résumés OpenAI
- ✅ `dashboard_stats_lite` - Stats dashboard légères
- ✅ `dashboard_stats_snapshot` - Snapshots stats
- ✅ `monthly_invoices` - Factures mensuelles
- ✅ `monthly_usage_tracking` - Suivi usage mensuel
- ✅ `openai_api_calls` - Appels API OpenAI
- ✅ `openai_costs_cache` - Cache des coûts OpenAI
- ✅ `openai_usage` - Usage OpenAI
- ✅ `quota_audit_log` - Logs audit quotas
- ✅ `server_performance_metrics` - Métriques de performance
- ✅ `statistics_cache` - Cache des statistiques
- ✅ `system_errors` - Erreurs système
- ✅ `user_billing_info` - Infos facturation utilisateur
- ✅ `user_sessions` - Sessions utilisateur

**Fonctions**:
- ✅ `create_conversation_with_messages()`
- ✅ `add_message_to_conversation()`
- ✅ `get_conversation_messages()`
- ✅ `update_conversation_metadata()`

**Vues**:
- ✅ `conversation_stats`

---

### Supabase PostgreSQL

**Tables**:
- ✅ `auth.users` - Authentification Supabase
- ✅ `public.users` - Profils utilisateurs
- ✅ `public.invitations` - Système d'invitation

---

## 🚀 Backend Déjà Mis à Jour

Les fichiers backend suivants ont **déjà été mis à jour** pour utiliser la nouvelle architecture:

- ✅ `backend/app/api/v1/conversations.py` - Utilise `conversation_service`
- ✅ `backend/app/services/conversation_service.py` - Service principal
- ✅ `backend/app/core/database.py` - Connexions aux deux BDs
- ✅ `backend/app/api/v1/stats_fast.py` - Stats optimisées

**Commit**: `40a074a5` - "fix: Update conversations.py to use new conversations+messages architecture"

---

## ✅ Checklist Finale

- [ ] Exécuter `check_conversations_structure.sql`
- [ ] Exécuter `fix_conversations_id_type.sql`
- [ ] Exécuter `create_messages_table_only.sql`
- [ ] Exécuter `verify_migration_complete.sql`
- [ ] Vérifier que le résultat est "MIGRATION COMPLÈTE ET FONCTIONNELLE"
- [ ] Exécuter `cleanup_digitalocean_final.sql`
- [ ] Tester l'application (créer une conversation)
- [ ] Vérifier le menu Historique (HistoryMenu)
- [ ] Tester le feedback sur une conversation

---

## 📞 Support

Si vous rencontrez des problèmes:
1. Vérifier les logs du backend (`docker logs` ou console)
2. Vérifier les logs PostgreSQL
3. Relancer `verify_migration_complete.sql` pour voir ce qui manque
4. Consulter ce guide pour les solutions aux problèmes courants
