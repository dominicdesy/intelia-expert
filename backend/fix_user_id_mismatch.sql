-- ============================================================================
-- FIX USER_ID MISMATCH - Script de correction
-- ============================================================================
-- Date: 2025-10-10
--
-- PROBLÈME IDENTIFIÉ:
-- L'auth token utilise user_id = 843d440a-a7a7-45ee-96df-3568c37384b9
-- Mais ce user n'existe pas dans Supabase public.users
-- Les vrais users sont: 3cd5b63b-e244-435c-97ac-557b2d32e981 et 237838e5-985c-4201-a05b-11c464d0d9eb
--
-- SOLUTION:
-- 1. Créer l'utilisateur manquant dans Supabase OU
-- 2. Mettre à jour le user_id dans PostgreSQL pour correspondre à un utilisateur existant
--
-- Ce script implémente l'option 2 (plus simple si c'est le même utilisateur)
-- ============================================================================

-- ============================================================================
-- ÉTAPE 1: DIAGNOSTIC - Identifier les user_ids problématiques
-- ============================================================================

-- Voir tous les user_ids dans conversations
SELECT
    user_id,
    COUNT(*) as conversation_count,
    MIN(created_at) as first_conversation,
    MAX(created_at) as last_conversation
FROM conversations
GROUP BY user_id
ORDER BY conversation_count DESC;

-- ============================================================================
-- ÉTAPE 2: CORRECTION - Mettre à jour le user_id
-- ============================================================================

-- ATTENTION: Remplacez 'NEW_USER_ID' par l'UUID correct de l'utilisateur
-- Exemple: 3cd5b63b-e244-435c-97ac-557b2d32e981 (Lydia)

-- Voir d'abord ce qui sera modifié (DRY RUN)
SELECT
    id,
    user_id as old_user_id,
    '3cd5b63b-e244-435c-97ac-557b2d32e981'::uuid as new_user_id,
    question,
    created_at
FROM conversations
WHERE user_id = '843d440a-a7a7-45ee-96df-3568c37384b9'::uuid;

-- IMPORTANT: Décommentez la ligne suivante SEULEMENT après avoir vérifié le DRY RUN
-- UPDATE conversations
-- SET user_id = '3cd5b63b-e244-435c-97ac-557b2d32e981'::uuid
-- WHERE user_id = '843d440a-a7a7-45ee-96df-3568c37384b9'::uuid;

-- ============================================================================
-- ÉTAPE 3: VÉRIFICATION
-- ============================================================================

-- Compter les conversations par user_id après la mise à jour
SELECT
    user_id,
    COUNT(*) as conversation_count
FROM conversations
GROUP BY user_id;

-- Vérifier qu'il n'y a plus de user_id orphelins
-- (Cette requête devrait retourner 0 lignes si tous les user_ids existent dans Supabase)
SELECT DISTINCT user_id
FROM conversations
WHERE user_id NOT IN (
    -- Remplacez par les user_ids qui existent réellement dans Supabase
    '3cd5b63b-e244-435c-97ac-557b2d32e981'::uuid,
    '237838e5-985c-4201-a05b-11c464d0d9eb'::uuid
);

-- ============================================================================
-- NOTES IMPORTANTES
-- ============================================================================
--
-- OPTION A: Si 843d440a-a7a7-45ee-96df-3568c37384b9 est Lydia (lydia@intelia.com)
-- Utilisez: UPDATE ... SET user_id = '3cd5b63b-e244-435c-97ac-557b2d32e981'
--
-- OPTION B: Si c'est un nouvel utilisateur légitime
-- Vous devez d'abord créer ce user dans Supabase avec le même UUID
--
-- OPTION C: Si c'est Dominic (dominic.bard@groupeintelia.com)
-- Utilisez: UPDATE ... SET user_id = '237838e5-985c-4201-a05b-11c464d0d9eb'
--
-- ============================================================================
