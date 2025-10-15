# Migration complète: Extraction automatique du profil Facebook

## Vue d'ensemble

Ce système extrait automatiquement l'URL du profil Facebook depuis les données OAuth lorsqu'un utilisateur se connecte avec Facebook.

**Format de l'URL extraite:** `https://facebook.com/{user_id}`
**Source des données:** `auth.users.raw_user_meta_data.avatar_url` (paramètre `asid=`)

---

## Architecture

```
Connexion Facebook OAuth
         ↓
Supabase auth.users (raw_user_meta_data)
         ↓
Trigger handle_new_user() ← Extraction automatique
         ↓
public.users.facebook_profile ← URL sauvegardée
```

---

## Étapes d'installation

### Étape 1: Ajouter la colonne facebook_profile

**Fichier:** `add_facebook_profile_to_users.sql`

**Que fait ce script:**
- Ajoute la colonne `facebook_profile` (type TEXT) à la table `public.users`
- Ajoute un commentaire explicatif sur la colonne

**Comment l'exécuter:**

1. Allez sur https://supabase.com/dashboard
2. Sélectionnez votre projet: **Intelia Expert**
3. Allez dans **SQL Editor** (barre latérale gauche)
4. Cliquez sur **New Query**
5. Copiez-collez le contenu de `add_facebook_profile_to_users.sql`
6. Cliquez sur **Run** (ou Ctrl+Enter)
7. Vérifiez le succès: "Success. No rows returned"

**Vérification:**
```sql
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'facebook_profile';
```

Résultat attendu:
```
column_name      | data_type | column_default
facebook_profile | text      | null
```

---

### Étape 2: Mettre à jour le trigger pour extraction automatique

**Fichier:** `update_handle_new_user_facebook_extraction.sql`

**Que fait ce script:**
- Modifie le trigger `handle_new_user()` pour extraire automatiquement l'ID Facebook
- Parse le paramètre `asid=` depuis `avatar_url`
- Construit l'URL du profil Facebook
- Sauvegarde dans `facebook_profile` lors de la création du profil

**Comment l'exécuter:**

1. Même processus que l'Étape 1
2. Copiez-collez le contenu de `update_handle_new_user_facebook_extraction.sql`
3. Cliquez sur **Run**
4. Le trigger est remplacé atomiquement (zéro downtime)

**Vérification:**
```sql
SELECT proname AS "Fonction", prosrc AS "Code SQL"
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname = 'handle_new_user';
```

Le code doit contenir `v_facebook_profile` et `substring(v_avatar_url from 'asid=([0-9]+)')`.

---

### Étape 3: Backfill pour les utilisateurs existants (OPTIONNEL)

**Fichier:** `backfill_facebook_profiles.sql`

**Que fait ce script:**
- Extrait l'URL du profil Facebook pour les utilisateurs qui se sont connectés AVANT l'Étape 2
- Ne modifie que les utilisateurs avec `facebook_profile IS NULL`
- Ne touche pas aux nouvelles inscriptions (elles ont déjà l'URL via le trigger)

**Quand l'exécuter:**
- Seulement si vous avez des utilisateurs Facebook existants
- Après avoir appliqué les Étapes 1 et 2

**Comment l'exécuter:**

1. Même processus que ci-dessus
2. Copiez-collez le contenu de `backfill_facebook_profiles.sql`
3. Cliquez sur **Run**

**Vérification:**
```sql
SELECT
  COUNT(*) FILTER (WHERE facebook_profile IS NOT NULL) AS users_with_facebook,
  COUNT(*) FILTER (WHERE facebook_profile IS NULL) AS users_without_facebook,
  COUNT(*) AS total_users
FROM public.users;
```

---

## Résultat final

### Pour les nouveaux utilisateurs (après migration)

Lorsqu'un utilisateur se connecte avec Facebook:
1. Supabase OAuth redirige vers votre app avec un token
2. `auth.users` est créé avec `raw_user_meta_data.avatar_url`
3. Le trigger `handle_new_user()` s'exécute automatiquement
4. L'ID Facebook est extrait: `asid=10161563757712721`
5. L'URL est construite: `https://facebook.com/10161563757712721`
6. L'URL est sauvegardée dans `public.users.facebook_profile`

**Aucune action requise côté code backend/frontend!**

### Pour les utilisateurs existants (après backfill)

Les utilisateurs qui se sont connectés avant la migration auront leur profil Facebook extrait rétroactivement.

---

## Accéder aux données

### Depuis le backend (Python)

Le champ `facebook_profile` est déjà retourné par `/auth/me`:

```python
# backend/app/api/v1/auth.py ligne 2275
"facebook_profile": profile_data.get("facebook_profile"),
```

### Depuis le frontend (TypeScript)

Ajoutez le champ à l'interface `BackendUserData`:

```typescript
// frontend/lib/stores/auth.ts
interface BackendUserData {
  // ... champs existants
  facebook_profile?: string;
}
```

Puis mappez vers `AppUser`:

```typescript
const appUser: AppUser = {
  // ... champs existants
  facebookProfile: userData.facebook_profile || "",
};
```

---

## Exemple de données extraites

### Données OAuth brutes (Supabase)
```json
{
  "iss": "https://auth.intelia.com/auth/v1",
  "sub": "110572043738466610605",
  "name": "Dominic Desy",
  "email": "dominic.desy@intelia.com",
  "avatar_url": "https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10161563757712721&height=200&width=200&ext=1736976526&hash=Abal4BkZTfgdWmNhQA",
  "provider_id": "10161563757712721",
  "email_verified": true
}
```

### Résultat dans public.users
```json
{
  "id": "uuid-here",
  "email": "dominic.desy@intelia.com",
  "full_name": "Dominic Desy",
  "facebook_profile": "https://facebook.com/10161563757712721"
}
```

---

## Rollback (si nécessaire)

### Supprimer la colonne
```sql
ALTER TABLE public.users DROP COLUMN IF EXISTS facebook_profile;
```

### Restaurer l'ancien trigger
```sql
-- Réexécuter fix_handle_new_user_complete_profile.sql
-- (version sans extraction Facebook)
```

---

## Tests

### Test 1: Nouvelle inscription Facebook

1. Déconnectez-vous de l'app
2. Cliquez sur "Se connecter avec Facebook"
3. Autorisez l'application
4. Vérifiez dans Supabase:

```sql
SELECT id, email, facebook_profile, created_at
FROM public.users
WHERE email = 'votre-email@example.com';
```

Vous devriez voir: `facebook_profile: "https://facebook.com/{user_id}"`

### Test 2: Backfill utilisateurs existants

Avant:
```sql
SELECT COUNT(*) FROM public.users WHERE facebook_profile IS NOT NULL;
-- Résultat: 0
```

Après backfill:
```sql
SELECT COUNT(*) FROM public.users WHERE facebook_profile IS NOT NULL;
-- Résultat: N (nombre d'utilisateurs Facebook)
```

---

## Questions fréquentes

### Q: Pourquoi extraire seulement Facebook et pas LinkedIn?

**R:** L'API LinkedIn OIDC ne fournit pas d'URL de profil public dans les métadonnées OAuth. Pour obtenir le `vanityName` (username LinkedIn), il faudrait:
- Demander l'accès à LinkedIn Partner Program (difficile à obtenir)
- Faire des appels API supplémentaires après OAuth

Facebook, en revanche, inclut l'ID utilisateur dans l'URL de l'avatar (`asid=`), ce qui permet une extraction simple et fiable.

### Q: Est-ce que ça fonctionne pour les utilisateurs en navigation privée?

**R:** Oui! L'extraction se fait côté serveur (Supabase) via le trigger PostgreSQL, indépendamment du mode de navigation du navigateur.

### Q: Que se passe-t-il si l'utilisateur change de photo de profil Facebook?

**R:** L'URL du profil Facebook reste la même (c'est juste l'ID). Seule l'URL de l'avatar peut changer, mais nous n'utilisons l'avatar que pour *extraire* l'ID lors de la première connexion.

### Q: Peut-on forcer une mise à jour du facebook_profile?

**R:** Oui, via une requête UPDATE manuelle:

```sql
UPDATE public.users
SET facebook_profile = 'https://facebook.com/NEW_ID'
WHERE email = 'user@example.com';
```

Ou via une API backend si vous ajoutez un endpoint pour ça.

---

## Fichiers de migration

1. ✅ `add_facebook_profile_to_users.sql` - Ajouter la colonne
2. ✅ `update_handle_new_user_facebook_extraction.sql` - Modifier le trigger
3. ✅ `backfill_facebook_profiles.sql` - Backfill existants (optionnel)
4. ✅ `README_FACEBOOK_PROFILE_COMPLETE.md` - Ce fichier

---

## Support

Si vous rencontrez des problèmes:

1. Vérifiez que les 3 migrations ont été exécutées dans l'ordre
2. Consultez les logs Supabase: **Dashboard → Logs → Postgres**
3. Testez avec un nouveau compte Facebook de test
4. Vérifiez que la colonne `facebook_profile` existe bien

---

🎉 **Migration complète!** Tous les nouveaux utilisateurs Facebook auront leur profil extrait automatiquement.
