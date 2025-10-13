# Guide de Correction des Warnings de Sécurité Supabase

## ⚠️ Vue d'ensemble

Ce guide explique comment corriger 4 warnings de sécurité détectés par le linter Supabase.

---

## 🔴 Priorité HAUTE: Corriger les search_path mutables

### Problème
Trois fonctions n'ont pas de `search_path` fixe :
- `handle_new_user`
- `notify_user_created`
- `update_updated_at_column`

### Risque de sécurité
**Search Path Injection Attack**: Un attaquant pourrait créer des objets malveillants (tables, fonctions) dans un schéma qu'il contrôle, et faire en sorte que vos fonctions les utilisent au lieu des vrais objets.

**Exemple d'attaque:**
```sql
-- L'attaquant crée un schéma malveillant
CREATE SCHEMA attacker_schema;
CREATE TABLE attacker_schema.user_profiles AS SELECT * FROM public.user_profiles;

-- Il modifie son search_path
SET search_path = 'attacker_schema, public';

-- Maintenant, quand handle_new_user() s'exécute, il insère dans la table de l'attaquant
-- au lieu de la vraie table public.user_profiles
```

### Solution

#### Étape 1: Vérifier les fonctions actuelles

Avant d'appliquer les correctifs, vérifiez d'abord les définitions actuelles dans Supabase:

```sql
-- Obtenir les définitions complètes des fonctions
SELECT
  proname AS function_name,
  pg_get_functiondef(oid) AS function_definition
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname IN ('handle_new_user', 'notify_user_created', 'update_updated_at_column');
```

#### Étape 2: Comparer avec le script de correction

Ouvrez le fichier `fix_search_path_security.sql` et **comparez la logique avec vos fonctions actuelles**.

Les implémentations dans le script sont des **exemples typiques**. Vous devrez peut-être les adapter.

#### Étape 3: Exécuter le script

Dans le SQL Editor de Supabase:

1. Allez dans **SQL Editor**
2. Ouvrez `fix_search_path_security.sql`
3. **ADAPTEZ** les fonctions si nécessaire
4. Exécutez le script

#### Étape 4: Vérifier que c'est corrigé

```sql
-- Cette requête doit montrer "SET search_path = ''" pour chaque fonction
SELECT
  proname AS function_name,
  proconfig AS settings
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname IN ('handle_new_user', 'notify_user_created', 'update_updated_at_column');
```

---

## 🟡 Priorité MOYENNE: Activer la protection des mots de passe compromis

### Problème
La protection contre les mots de passe compromis est désactivée.

### Bénéfice
Empêche les utilisateurs d'utiliser des mots de passe qui ont été exposés dans des fuites de données connues (via HaveIBeenPwned.org).

### Solution

#### Via Supabase Dashboard:

1. Allez dans **Authentication** → **Policies**
2. Trouvez la section **Password Security**
3. Activez **"Check passwords against breach databases"**
4. Sauvegardez

#### Via Supabase CLI (alternative):

```bash
# Dans votre projet
supabase settings update --enable-password-breach-detection true
```

#### Via l'API Supabase (alternative):

```bash
curl -X PATCH https://api.supabase.com/v1/projects/{project-ref}/config/auth \
  -H "Authorization: Bearer YOUR_SUPABASE_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "SECURITY_PASSWORD_BREACH_PROTECTION": true
  }'
```

---

## ✅ Vérification finale

Après avoir appliqué tous les correctifs:

1. Allez dans **Database** → **Linter** dans Supabase
2. Re-exécutez le linter
3. Les 4 warnings doivent avoir disparu

---

## 📝 Impact utilisateur

### search_path fixes
- **Impact**: Aucun pour les utilisateurs normaux
- **Temps d'arrêt**: Aucun (les fonctions sont remplacées atomiquement)

### Protection des mots de passe compromis
- **Impact**: Les nouveaux utilisateurs ne pourront pas utiliser de mots de passe compromis
- **Utilisateurs existants**: Non affectés (seulement au prochain changement de mot de passe)

---

## 🔍 Références

- [Supabase: Function Search Path Security](https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable)
- [Supabase: Password Security](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection)
- [PostgreSQL: SET search_path](https://www.postgresql.org/docs/current/sql-set.html)
- [OWASP: Search Path Injection](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

---

## 🆘 En cas de problème

Si après avoir exécuté les correctifs vous rencontrez des erreurs:

1. **Erreur de syntaxe**: Vérifiez que votre logique de fonction correspond au script
2. **Fonctions qui ne fonctionnent plus**: Restaurez la version précédente et contactez l'équipe
3. **Permissions**: Assurez-vous d'exécuter le script avec les permissions appropriées (généralement le rôle `postgres`)

### Rollback d'urgence

Si vous devez annuler les changements:

```sql
-- Exemple pour handle_new_user (adaptez selon votre logique originale)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
-- PAS de SET search_path (version originale)
AS $$
BEGIN
  -- Votre logique originale ici
  RETURN NEW;
END;
$$;
```

---

**Créé**: 2025-01-13
**Auteur**: Claude Code
**Priorité**: HAUTE (correctifs recommandés dès que possible)
