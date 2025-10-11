-- ============================================================================
-- SCHÉMA SUPABASE - Authentification et Profils Utilisateurs
-- ============================================================================
-- Base de données: Supabase PostgreSQL (Cloud)
-- Date: 2025-10-11
-- ============================================================================

-- ============================================================================
-- NOTES IMPORTANTES
-- ============================================================================

/*
ARCHITECTURE SUPABASE:
---------------------
Supabase gère automatiquement la table auth.users.
Nous créons seulement la table public.users pour les profils.

auth.users (géré par Supabase):
  - id (UUID, PK)
  - email
  - encrypted_password
  - email_confirmed_at
  - created_at
  - updated_at
  - etc.

public.users (à créer):
  - Profil utilisateur étendu
  - Synchronisé avec auth.users via triggers
*/

-- ============================================================================
-- TABLE: public.users
-- Profils utilisateurs étendus
-- ============================================================================

-- Supprimer la table existante si nécessaire (ATTENTION: perte de données)
-- DROP TABLE IF EXISTS public.users CASCADE;

CREATE TABLE IF NOT EXISTS public.users (
    -- ID synchronisé avec auth.users
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Informations personnelles
    email TEXT UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT GENERATED ALWAYS AS (
        COALESCE(first_name || ' ' || last_name, first_name, last_name, email)
    ) STORED,

    -- Type et plan
    user_type TEXT DEFAULT 'user',  -- user, admin, super_admin
    plan TEXT DEFAULT 'free',  -- free, professional, enterprise

    -- Préférences
    language TEXT DEFAULT 'fr',
    timezone TEXT DEFAULT 'America/Montreal',

    -- Métadonnées
    avatar_url TEXT,
    phone TEXT,
    company TEXT,

    -- Statut
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_user_type ON public.users(user_type);
CREATE INDEX IF NOT EXISTS idx_users_plan ON public.users(plan);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON public.users(is_active) WHERE is_active = true;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Activer RLS sur la table users
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Politique: Les utilisateurs peuvent voir leur propre profil
CREATE POLICY "Users can view own profile"
    ON public.users
    FOR SELECT
    USING (auth.uid() = id);

-- Politique: Les utilisateurs peuvent mettre à jour leur propre profil
CREATE POLICY "Users can update own profile"
    ON public.users
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Politique: Les admins peuvent voir tous les profils
CREATE POLICY "Admins can view all profiles"
    ON public.users
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.users
            WHERE id = auth.uid()
            AND user_type IN ('admin', 'super_admin')
        )
    );

-- Politique: Seuls les super_admins peuvent modifier user_type et plan
CREATE POLICY "Super admins can modify user type and plan"
    ON public.users
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.users
            WHERE id = auth.uid()
            AND user_type = 'super_admin'
        )
    );

-- ============================================================================
-- TRIGGER: Synchronisation auth.users → public.users
-- ============================================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, email_verified)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.email_confirmed_at IS NOT NULL
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger lors de la création d'un user dans auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- TRIGGER: update_updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================================
-- FONCTION: get_user_by_email
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_user_by_email(p_email TEXT)
RETURNS TABLE(
    id UUID,
    email TEXT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    user_type TEXT,
    plan TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.id,
        u.email,
        u.first_name,
        u.last_name,
        u.full_name,
        u.user_type,
        u.plan
    FROM public.users u
    WHERE u.email = p_email
    AND u.is_active = true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- FONCTION: update_last_login
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_last_login(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE public.users
    SET last_login_at = NOW()
    WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- VÉRIFICATIONS
-- ============================================================================

-- Vérifier la structure de la table users
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'users'
ORDER BY ordinal_position;

-- Vérifier les politiques RLS
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename = 'users';

-- Compter les utilisateurs
SELECT
    COUNT(*) as total_users,
    COUNT(*) FILTER (WHERE is_active = true) as active_users,
    COUNT(*) FILTER (WHERE user_type = 'admin') as admins
FROM public.users;

-- ============================================================================
-- DONNÉES DE TEST (OPTIONNEL - À SUPPRIMER EN PRODUCTION)
-- ============================================================================

-- Créer un admin de test (remplacer par vos vraies données)
-- INSERT INTO public.users (id, email, first_name, last_name, user_type, plan)
-- VALUES (
--     gen_random_uuid(),
--     'admin@intelia.com',
--     'Admin',
--     'System',
--     'super_admin',
--     'enterprise'
-- )
-- ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- NOTES D'UTILISATION
-- ============================================================================

/*
CONNEXION:
----------
Cette base Supabase est accessible via:
- Variable d'env: SUPABASE_URL et SUPABASE_KEY
- SDK Supabase pour auth automatique

SÉPARATION DES RESPONSABILITÉS:
-------------------------------
Supabase (ici):
  ✅ auth.users - Authentification (géré par Supabase)
  ✅ public.users - Profils utilisateurs
  ✅ RLS pour sécurité

PostgreSQL (DigitalOcean):
  ✅ conversations
  ✅ feedback
  ✅ invitations

AUTHENTIFICATION:
-----------------
1. L'utilisateur s'inscrit → Supabase crée auth.users
2. Trigger crée automatiquement public.users
3. JWT contient user.id pour requêtes vers PostgreSQL

ACCÈS CROSS-DATABASE:
--------------------
Le backend doit:
1. Récupérer user.id depuis JWT (Supabase)
2. Utiliser ce user.id pour requêtes PostgreSQL (conversations)

Exemple:
  const { data: { user } } = await supabase.auth.getUser(jwt);
  const conversations = await pgClient.query(
    'SELECT * FROM conversations WHERE user_id = $1',
    [user.id]
  );

SÉCURITÉ:
---------
- RLS activé sur public.users
- Les utilisateurs ne voient que leur propre profil
- Les admins peuvent voir tous les profils
- Les super_admins peuvent modifier les types/plans

MIGRATION:
----------
Si des utilisateurs existent déjà dans auth.users:
  INSERT INTO public.users (id, email)
  SELECT id, email FROM auth.users
  ON CONFLICT (id) DO NOTHING;
*/
