# 🔧 Guide de Recréation du Compte Super Admin

**Utilisateur à recréer:**
- Nom: Dominic Désy
- Email: dominic.desy@intelia.com
- Pays: Canada
- Langue: Français (fr)
- Rôle: super_admin

---

## ✅ MÉTHODE RECOMMANDÉE: Via Supabase Dashboard (Plus simple et plus sûre)

### Étape 1: Créer l'utilisateur dans Authentication

1. **Ouvrez Supabase Dashboard** → Votre projet
2. **Allez dans `Authentication` → `Users`**
3. **Cliquez sur `Add User` → `Create new user`**
4. **Remplissez le formulaire:**
   - Email: `dominic.desy@intelia.com`
   - Password: Définissez un mot de passe temporaire fort
   - ✅ Cochez `Auto Confirm User` (pour skip la vérification email)
5. **Cliquez sur `Create user`**
6. **IMPORTANT:** Notez l'UUID de l'utilisateur créé (vous le verrez dans la liste)
   - Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### Étape 2: Créer le profil dans la table users

7. **Allez dans `Table Editor` → Table `users`**
8. **Cliquez sur `Insert` → `Insert row`**
9. **Remplissez les champs:**
   - `id`: Collez l'UUID copié à l'étape 1.6
   - `auth_user_id`: Collez le MÊME UUID
   - `email`: `dominic.desy@intelia.com`
   - `email_verified`: `true`
   - `first_name`: `Dominic`
   - `last_name`: `Désy`
   - `full_name`: `Dominic Désy`
   - `country`: `Canada`
   - `user_type`: `super_admin` ⭐ (C'EST LE PLUS IMPORTANT!)
   - `language`: `fr`
   - Laissez `created_at` et `updated_at` vides (ils se rempliront automatiquement)
10. **Cliquez sur `Save`**

### Étape 3: Vérification

11. **Allez dans `Table Editor` → Table `users`**
12. **Trouvez la ligne avec `dominic.desy@intelia.com`**
13. **Vérifiez que:**
    - ✅ `user_type` = `super_admin`
    - ✅ `email_verified` = `true`
    - ✅ `language` = `fr`
    - ✅ `country` = `Canada`

### Étape 4: Test de connexion

14. **Ouvrez l'application** (https://expert.intelia.com)
15. **Connectez-vous avec:**
    - Email: `dominic.desy@intelia.com`
    - Password: Le mot de passe défini à l'étape 1.4
16. **Vérifiez que vous avez accès aux fonctions admin**

### Étape 5: Sécurité

17. **⚠️ CHANGEZ LE MOT DE PASSE IMMÉDIATEMENT**
    - Allez dans les paramètres du profil
    - Changez le mot de passe temporaire pour un mot de passe sécurisé

---

## 🔄 MÉTHODE ALTERNATIVE: Via SQL (Pour utilisateurs avancés)

Si vous préférez utiliser SQL, suivez ces étapes:

### Étape 1: Créer l'utilisateur via le Dashboard

Même chose que la Méthode Recommandée Étape 1 (c'est plus fiable que de manipuler `auth.users` directement)

### Étape 2: Exécuter le script SQL

1. **Ouvrez Supabase Dashboard → `SQL Editor`**
2. **Ouvrez le fichier** `RECREATE_ADMIN_USER.sql`
3. **Remplacez `YOUR_AUTH_USER_ID`** par l'UUID de l'utilisateur créé (apparaît 2 fois)
4. **Cliquez sur `Run`**

Le script créera automatiquement le profil avec tous les champs corrects.

---

## 📊 Vérification Technique

Pour vérifier que `is_admin` est correctement calculé côté backend:

```sql
-- Cette requête montre le profil
SELECT
  id,
  email,
  user_type,
  first_name,
  last_name,
  country,
  language
FROM public.users
WHERE email = 'dominic.desy@intelia.com';
```

**Note:** Le champ `is_admin` n'est PAS stocké en base de données. Il est calculé automatiquement côté backend avec cette logique:

```python
is_admin = user_type in ["admin", "super_admin"]
```

Donc si `user_type = 'super_admin'`, alors `is_admin = True` automatiquement.

---

## ⚠️ Troubleshooting

### Problème: "User already exists"
- Vérifiez dans `Authentication → Users` si l'email existe déjà
- Si oui, récupérez son UUID et passez directement à l'Étape 2

### Problème: "Duplicate key violation"
- L'entrée existe déjà dans `public.users`
- Utilisez `Table Editor` pour modifier directement la ligne existante
- Changez `user_type` à `super_admin`

### Problème: "Cannot login"
- Vérifiez que `email_verified = true` dans `public.users`
- Vérifiez que l'utilisateur est bien `confirmed` dans `Authentication → Users`
- Réinitialisez le mot de passe via `Authentication → Users → ... → Reset Password`

### Problème: "Pas d'accès admin"
- Vérifiez que `user_type = 'super_admin'` (pas "admin", pas "super admin" avec espace)
- Déconnectez-vous et reconnectez-vous pour rafraîchir le token JWT
- Le backend calcule `is_admin` depuis `user_type`, donc aucune action supplémentaire nécessaire

---

## 🎉 Succès !

Une fois connecté, vous devriez avoir accès à:
- ✅ Toutes les fonctionnalités admin
- ✅ Gestion des utilisateurs
- ✅ Logs système
- ✅ Statistiques avancées
- ✅ Configuration système

**N'oubliez pas de changer le mot de passe temporaire !**
