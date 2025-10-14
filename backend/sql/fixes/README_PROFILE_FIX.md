# Fix: Champs de profil vides après inscription

## 🐛 Problème identifié

Quand un utilisateur s'inscrit (ex: John Smith, dominic.desy@icloud.com, USA), après connexion les champs suivants sont vides dans le profil :
- `first_name` (prénom)
- `last_name` (nom de famille)
- `country` (pays)
- `phone` (téléphone)
- `company_name` (entreprise)

## 🔍 Cause racine

Le trigger `handle_new_user()` dans Supabase ne sauvegarde que 3 champs :
```sql
INSERT INTO public.users (id, email, email_verified)
VALUES (NEW.id, NEW.email, NEW.email_confirmed_at IS NOT NULL)
```

Les données `first_name`, `last_name`, `country`, etc. sont bien envoyées par le frontend et sauvegardées dans `auth.users.raw_user_meta_data` (JSON), mais le trigger ne les extrait pas.

Ensuite, le backend essaie d'insérer l'entrée complète mais échoue silencieusement à cause de `ON CONFLICT DO NOTHING`.

## ✅ Solution

### Étape 1: Corriger le trigger (pour les futurs utilisateurs)

Exécuter le fichier :
```
fix_handle_new_user_complete_profile.sql
```

Ce script met à jour le trigger pour qu'il extraie et sauvegarde tous les champs depuis `raw_user_meta_data`.

### Étape 2: Corriger les utilisateurs existants

Exécuter le fichier :
```
migrate_existing_users_metadata.sql
```

Ce script lit les données depuis `auth.users.raw_user_meta_data` et met à jour `public.users` pour tous les utilisateurs déjà créés.

### Étape 3: Script tout-en-un (recommandé)

Pour exécuter les deux étapes d'un coup :
```
EXECUTE_PROFILE_FIX_COMPLETE.sql
```

## 📋 Instructions d'exécution

1. Ouvrir Supabase Dashboard
2. Aller dans **SQL Editor**
3. Créer une nouvelle requête
4. Copier-coller le contenu de `EXECUTE_PROFILE_FIX_COMPLETE.sql`
5. Cliquer sur **Run** (ou F5)
6. Vérifier les résultats affichés

## 🧪 Vérification

Après l'exécution, vérifier qu'un utilisateur existant a bien ses données :

```sql
SELECT
  email,
  first_name,
  last_name,
  country,
  full_name,
  phone,
  company_name,
  language
FROM public.users
WHERE email = 'dominic.desy@icloud.com';
```

Résultat attendu :
- `first_name`: John
- `last_name`: Smith
- `country`: USA
- Tous les autres champs remplis si disponibles

## ⚠️ Note importante

Les utilisateurs doivent **se déconnecter et se reconnecter** pour que le frontend récupère les nouvelles données via l'endpoint `/auth/me`.

## 📁 Fichiers fournis

| Fichier | Description |
|---------|-------------|
| `fix_handle_new_user_complete_profile.sql` | Corrige le trigger pour futurs utilisateurs |
| `migrate_existing_users_metadata.sql` | Corrige les utilisateurs existants |
| `EXECUTE_PROFILE_FIX_COMPLETE.sql` | Script tout-en-un (recommandé) |
| `README_PROFILE_FIX.md` | Ce fichier |

## 🎯 Impact

- ✅ Futurs utilisateurs auront tous leurs champs sauvegardés automatiquement
- ✅ Utilisateurs existants seront corrigés avec leurs données depuis `raw_user_meta_data`
- ✅ Zéro downtime
- ✅ Aucun changement fonctionnel côté frontend/backend
- ✅ Sécurisé - utilise `COALESCE` pour ne pas écraser les données existantes
