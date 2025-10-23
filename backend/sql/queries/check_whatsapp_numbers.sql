-- Vérifier les numéros WhatsApp dans la table users
-- Exécutez cette requête dans Supabase SQL Editor

-- 1. Voir tous les utilisateurs avec leur numéro WhatsApp
SELECT
    email,
    full_name,
    whatsapp_number,
    user_type,
    updated_at
FROM users
WHERE whatsapp_number IS NOT NULL
ORDER BY updated_at DESC;

-- 2. Voir un utilisateur spécifique (remplacez l'email)
SELECT
    email,
    full_name,
    whatsapp_number,
    phone_number,
    user_type,
    created_at,
    updated_at
FROM users
WHERE email = 'dominic.desy@icloud.com';

-- 3. Compter combien d'utilisateurs ont un numéro WhatsApp
SELECT
    COUNT(*) as total_users,
    COUNT(whatsapp_number) as users_with_whatsapp,
    COUNT(*) - COUNT(whatsapp_number) as users_without_whatsapp
FROM users;

-- 4. Voir les dernières mises à jour de numéros WhatsApp
SELECT
    email,
    whatsapp_number,
    updated_at,
    updated_at::timestamp - created_at::timestamp as account_age
FROM users
WHERE whatsapp_number IS NOT NULL
ORDER BY updated_at DESC
LIMIT 10;
