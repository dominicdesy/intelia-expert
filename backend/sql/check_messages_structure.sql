-- Vérifier la structure de la table messages
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'messages'
ORDER BY ordinal_position;

-- Vérifier quelques messages récents pour voir les valeurs
SELECT
    id,
    role,
    response_source,
    response_confidence,
    has_cot_structure,
    created_at
FROM messages
WHERE role = 'assistant'
ORDER BY created_at DESC
LIMIT 5;
