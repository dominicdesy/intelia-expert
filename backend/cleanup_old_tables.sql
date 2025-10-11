-- ============================================================================
-- CLEANUP: Suppression des tables obsolètes dans Supabase
-- ============================================================================
-- Date: 2025-10-11
-- Description: Supprime les tables qui ne sont plus utilisées après migration
--              vers la nouvelle architecture conversations + messages
-- ============================================================================

-- ATTENTION: Cette opération est IRRÉVERSIBLE
-- Assurez-vous d'avoir une sauvegarde avant d'exécuter ces commandes

-- ============================================================================
-- ÉTAPE 1: Vérification des tables existantes
-- ============================================================================

-- Lister toutes les tables dans le schéma public
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- ============================================================================
-- ÉTAPE 2: Suppression des tables obsolètes
-- ============================================================================

-- IMPORTANT: Les tables suivantes seront supprimées:
-- - feedback: le feedback est maintenant dans la table messages
-- - invitations: si cette table n'est pas utilisée
-- - Toute autre table liée à l'ancienne architecture

-- Supprimer la table feedback (feedback maintenant dans messages.feedback)
DROP TABLE IF EXISTS feedback CASCADE;

-- Supprimer la table invitations si elle existe et n'est pas utilisée
-- ATTENTION: Vérifiez d'abord si cette table est utilisée ailleurs!
-- Décommentez la ligne suivante SEULEMENT si vous êtes sûr:
-- DROP TABLE IF EXISTS invitations CASCADE;

-- ============================================================================
-- ÉTAPE 3: Vérification après suppression
-- ============================================================================

-- Vérifier que les tables restantes sont correctes
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Les tables suivantes DOIVENT exister:
-- - conversations (nouvelle architecture)
-- - messages (nouvelle architecture)
-- - users (profils utilisateurs)
-- - Toute autre table métier nécessaire

-- ============================================================================
-- ÉTAPE 4: Nettoyage des vues et fonctions obsolètes (optionnel)
-- ============================================================================

-- Lister les vues existantes
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'public'
ORDER BY table_name;

-- Si des vues utilisent les anciennes tables, les supprimer:
-- DROP VIEW IF EXISTS ancienne_vue CASCADE;

-- Lister les fonctions existantes
SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_type = 'FUNCTION'
ORDER BY routine_name;

-- Les fonctions suivantes DOIVENT exister (créées par db_schema_conversations_messages.sql):
-- - create_conversation_with_messages()
-- - add_message_to_conversation()
-- - get_conversation_messages()
-- - update_conversation_metadata()

-- ============================================================================
-- RÉSUMÉ DES TABLES À CONSERVER
-- ============================================================================

/*
TABLES À CONSERVER:
==================
1. conversations - Métadonnées des conversations (nouvelle architecture)
2. messages - Messages individuels (nouvelle architecture)
3. users - Profils utilisateurs (Supabase public.users)
4. Toute autre table métier nécessaire (billing, stats, etc.)

TABLES SUPPRIMÉES:
==================
1. feedback - Remplacée par messages.feedback
2. invitations - À vérifier si utilisée ailleurs

VUES À CONSERVER:
================
1. conversation_stats - Statistiques des conversations
2. conversation_details - Vue détaillée avec messages

FONCTIONS À CONSERVER:
=====================
1. create_conversation_with_messages()
2. add_message_to_conversation()
3. get_conversation_messages()
4. update_conversation_metadata()
*/

-- ============================================================================
-- INSTRUCTIONS D'EXÉCUTION
-- ============================================================================

/*
COMMENT EXÉCUTER CE SCRIPT:
===========================

1. Connectez-vous à Supabase SQL Editor:
   https://supabase.com/dashboard/project/YOUR_PROJECT_ID/sql

2. IMPORTANT: Créez d'abord une sauvegarde:
   - Allez dans Database > Backups
   - Créez un backup manuel avant de continuer

3. Exécutez d'abord l'ÉTAPE 1 pour voir les tables existantes

4. Vérifiez que vous voulez vraiment supprimer ces tables

5. Exécutez l'ÉTAPE 2 pour supprimer les tables obsolètes

6. Exécutez l'ÉTAPE 3 pour vérifier que tout est correct

7. (Optionnel) Exécutez l'ÉTAPE 4 pour nettoyer les vues/fonctions

ROLLBACK EN CAS D'ERREUR:
=========================
Si quelque chose ne va pas, restaurez le backup:
- Database > Backups > Restore

VÉRIFICATION POST-SUPPRESSION:
==============================
- Vérifiez que le backend fonctionne: https://expert.intelia.com/api/v1/conversations/health
- Vérifiez que le frontend affiche correctement l'historique
- Testez la création d'une nouvelle conversation
- Testez l'envoi de feedback
*/
