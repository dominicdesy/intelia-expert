-- Vérifier la structure de user_billing_info
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'user_billing_info'
ORDER BY ordinal_position;

-- Vérifier les contraintes
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'user_billing_info'
ORDER BY tc.constraint_type, kcu.column_name;

-- Vérifier si l'utilisateur existe déjà
SELECT * FROM user_billing_info WHERE user_email = 'dominic.desy@icloud.com';

-- Compter tous les utilisateurs
SELECT COUNT(*) as total_users FROM user_billing_info;
