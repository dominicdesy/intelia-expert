# Guide de Déploiement Production - Intelia Expert

## Vue d'ensemble

Ce guide documente les étapes nécessaires pour déployer et configurer l'application Intelia Expert en production sur DigitalOcean App Platform.

## Architecture des Bases de Données

L'application utilise une architecture à double base de données:

- **PostgreSQL (DigitalOcean)**: Stocke les données applicatives (conversations, feedback, invitations)
- **Supabase**: Gère l'authentification et les profils utilisateurs

## Variables d'Environnement Requises

### 1. PostgreSQL (DigitalOcean)

```bash
POSTGRES_HOST=<your-digitalocean-db-host>
POSTGRES_PORT=25060
POSTGRES_DB=defaultdb
POSTGRES_USER=<your-db-user>
POSTGRES_PASSWORD=<your-db-password>
POSTGRES_SSLMODE=require
```

### 2. Supabase

```bash
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_KEY=<your-supabase-anon-key>
SUPABASE_SERVICE_KEY=<your-supabase-service-role-key>
```

**IMPORTANT**: Les variables `SUPABASE_URL` et `SUPABASE_KEY` sont **OBLIGATOIRES**. Sans elles, l'application ne pourra pas:
- Enrichir les données utilisateurs dans les statistiques
- Afficher les noms/prénoms dans le tableau "Utilisateurs les plus actifs"
- Récupérer l'historique des questions dans l'onglet Q&A

### 3. OpenAI

```bash
OPENAI_API_KEY=<your-openai-key>
```

### 4. Autres Variables

```bash
# Environnement
ENVIRONMENT=production

# CORS
ALLOWED_ORIGINS=https://expert.intelia.com,https://www.expert.intelia.com

# Sécurité
SECRET_KEY=<your-secret-key>
JWT_SECRET=<your-jwt-secret>
```

## Configuration dans DigitalOcean App Platform

### Étape 1: Accéder aux Settings

1. Connectez-vous à DigitalOcean
2. Naviguez vers votre application `intelia-expert`
3. Cliquez sur **Settings** > **App-Level Environment Variables**

### Étape 2: Ajouter les Variables Manquantes

Ajoutez les variables suivantes si elles ne sont pas déjà configurées:

```
SUPABASE_URL = https://<your-project>.supabase.co
SUPABASE_KEY = <your-anon-key>
SUPABASE_SERVICE_KEY = <your-service-role-key>
```

### Étape 3: Redéployer l'Application

Après avoir ajouté les variables:
1. Cliquez sur **Save**
2. L'application se redéploiera automatiquement
3. Attendez que le déploiement se termine (environ 5-10 minutes)

## Mise à Jour du Schéma de Base de Données

### PostgreSQL (DigitalOcean)

Si la base de données PostgreSQL existe déjà mais manque certaines colonnes:

1. **Connexion à la base**:
   ```bash
   psql postgresql://<user>:<password>@<host>:25060/defaultdb?sslmode=require
   ```

2. **Exécuter le script de migration**:
   ```bash
   \i /path/to/backend/production_migration.sql
   ```

   OU copier-coller le contenu du fichier `backend/production_migration.sql` dans le terminal psql.

3. **Vérifier les colonnes**:
   ```sql
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name = 'conversations'
   ORDER BY ordinal_position;
   ```

### Supabase

Si la table `public.users` n'existe pas encore:

1. **Accéder à Supabase Dashboard**:
   - Connectez-vous à https://app.supabase.com
   - Sélectionnez votre projet

2. **Ouvrir SQL Editor**:
   - Naviguez vers **SQL Editor**
   - Créez une nouvelle requête

3. **Exécuter le schéma**:
   - Copiez le contenu de `backend/db_schema_supabase.sql`
   - Exécutez la requête

## Correction du Problème user_id

Les logs ont révélé un décalage entre les `user_id` dans:
- **Auth token**: `843d440a-a7a7-45ee-96df-3568c37384b9`
- **Supabase users**: `3cd5b63b-e244-435c-97ac-557b2d32e981` (Lydia) et `237838e5-985c-4201-a05b-11c464d0d9eb` (Dominic)

### Option A: Mettre à jour PostgreSQL

Si l'utilisateur avec le token `843d440a...` est en réalité Lydia:

```sql
UPDATE conversations
SET user_id = '3cd5b63b-e244-435c-97ac-557b2d32e981'::uuid
WHERE user_id = '843d440a-a7a7-45ee-96df-3568c37384b9'::uuid;
```

### Option B: Créer l'Utilisateur dans Supabase

Si c'est un nouvel utilisateur légitime, créez-le dans Supabase avec le même UUID.

Voir le fichier `backend/fix_user_id_mismatch.sql` pour plus de détails.

## Vérification Post-Déploiement

### 1. Health Check

Vérifiez que l'application est en santé:

```bash
curl https://expert.intelia.com/api/v1/health
curl https://expert.intelia.com/api/v1/stats-fast/health
```

Résultat attendu:
```json
{
  "status": "healthy",
  "databases": {
    "postgresql": {"status": "healthy"},
    "supabase": {"status": "healthy"}
  }
}
```

### 2. Dashboard

Vérifiez que le dashboard charge:

```bash
curl -H "Authorization: Bearer <token>" \
  https://expert.intelia.com/api/v1/stats-fast/dashboard
```

### 3. Questions Endpoint

Vérifiez que l'endpoint `/questions` fonctionne:

```bash
curl -H "Authorization: Bearer <token>" \
  https://expert.intelia.com/api/v1/stats-fast/questions?page=1&limit=20
```

## Problèmes Identifiés et Solutions

### Problème 1: SUPABASE_URL et SUPABASE_KEY manquants

**Symptôme**:
```
ERROR:app.core.database:❌ Failed to initialize databases:
SUPABASE_URL and SUPABASE_KEY environment variables must be set
```

**Solution**: Ajouter les variables d'environnement dans DigitalOcean (voir ci-dessus)

### Problème 2: Colonnes manquantes dans PostgreSQL

**Symptôme**:
```
ERROR:app.core.database:PostgreSQL transaction error:
column "response_source" does not exist
```

**Solution**: Exécuter `backend/production_migration.sql` sur la base PostgreSQL

### Problème 3: Endpoint /questions retourne 404

**Symptôme**:
```
GET /v1/stats-fast/questions?page=1&limit=20 HTTP/1.1 404 Not Found
```

**Solution**: Déployer la version mise à jour de `stats_fast.py` qui inclut l'endpoint `/questions`

### Problème 4: UUID affiché au lieu du nom dans "Utilisateurs les plus actifs"

**Symptôme**: Le tableau affiche `843d440a-a7a7-45ee-96df-3568c37384b9` au lieu de "Lydia"

**Solutions**:
1. Configurer SUPABASE_URL et SUPABASE_KEY
2. Corriger le user_id dans PostgreSQL (voir `fix_user_id_mismatch.sql`)

## Ordre d'Exécution Recommandé

Pour résoudre tous les problèmes en production:

1. ✅ **Ajouter variables Supabase** dans DigitalOcean
2. ✅ **Exécuter production_migration.sql** sur PostgreSQL
3. ✅ **Vérifier le schéma Supabase** (db_schema_supabase.sql)
4. ✅ **Corriger user_id** avec fix_user_id_mismatch.sql
5. ✅ **Déployer le code** (git push origin main)
6. ✅ **Vérifier les health checks**
7. ✅ **Tester le dashboard** et l'onglet Q&A

## Scripts de Migration Disponibles

- `backend/db_schema_postgresql.sql` - Schéma complet PostgreSQL
- `backend/db_schema_supabase.sql` - Schéma complet Supabase
- `backend/production_migration.sql` - Migration pour ajouter colonnes manquantes
- `backend/fix_user_id_mismatch.sql` - Correction du problème de user_id
- `backend/MIGRATION_GUIDE.md` - Guide détaillé de migration

## Support

En cas de problème:

1. **Consulter les logs** dans DigitalOcean:
   - Runtime Logs
   - Build Logs

2. **Vérifier les health checks**:
   ```bash
   curl https://expert.intelia.com/api/health
   curl https://expert.intelia.com/api/v1/stats-fast/health
   ```

3. **Tester les connexions DB** localement avec les mêmes credentials

4. **Comparer avec les logs** dans `backend/logs/` si disponibles

## Notes Importantes

- **TOUJOURS faire un backup** avant d'exécuter des migrations en production
- **Tester les scripts SQL** en local ou dans un environnement de staging d'abord
- **Les variables d'environnement** prennent effet après redéploiement
- **Les modifications de schéma** nécessitent un accès direct à la base de données

## Changelog des Déploiements

### 2025-10-10 - Correction Architecture Dual Database

- ✅ Ajout endpoint `/stats-fast/questions`
- ✅ Création de `production_migration.sql` pour colonnes manquantes
- ✅ Documentation des variables SUPABASE requises
- ✅ Script de correction user_id mismatch
- ✅ Mise à jour de stats_fast.py avec enrichissement Supabase

---

**Dernière mise à jour**: 2025-10-10
**Version**: 2.0
**Auteur**: Claude Code
