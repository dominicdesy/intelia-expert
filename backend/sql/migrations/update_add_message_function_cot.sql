-- ============================================================================
-- MIGRATION: Mettre à jour add_message_to_conversation pour supporter CoT
-- ============================================================================
-- Date: 2025-10-19
-- Description: Ajoute 3 nouveaux paramètres à la fonction pour sauvegarder
--              le raisonnement Chain-of-Thought (thinking, analysis, has_structure)
-- ============================================================================

-- Supprimer l'ancienne version de la fonction
DROP FUNCTION IF EXISTS add_message_to_conversation(UUID, TEXT, TEXT, TEXT, FLOAT, INTEGER);

-- Créer la nouvelle version avec paramètres CoT
CREATE OR REPLACE FUNCTION add_message_to_conversation(
    p_conversation_id UUID,
    p_role TEXT,
    p_content TEXT,
    p_response_source TEXT DEFAULT NULL,
    p_response_confidence FLOAT DEFAULT NULL,
    p_processing_time_ms INTEGER DEFAULT NULL,
    p_cot_thinking TEXT DEFAULT NULL,
    p_cot_analysis TEXT DEFAULT NULL,
    p_has_cot_structure BOOLEAN DEFAULT FALSE
)
RETURNS UUID AS $$
DECLARE
    v_message_id UUID;
    v_next_sequence INTEGER;
BEGIN
    -- Calculer le prochain sequence_number
    SELECT COALESCE(MAX(sequence_number), 0) + 1
    INTO v_next_sequence
    FROM messages
    WHERE conversation_id = p_conversation_id;

    -- Insérer le message avec colonnes CoT
    INSERT INTO messages (
        conversation_id,
        role,
        content,
        sequence_number,
        response_source,
        response_confidence,
        processing_time_ms,
        cot_thinking,
        cot_analysis,
        has_cot_structure
    ) VALUES (
        p_conversation_id,
        p_role,
        p_content,
        v_next_sequence,
        p_response_source,
        p_response_confidence,
        p_processing_time_ms,
        p_cot_thinking,
        p_cot_analysis,
        p_has_cot_structure
    )
    RETURNING id INTO v_message_id;

    RETURN v_message_id;
END;
$$ LANGUAGE plpgsql;

-- Vérifier que la fonction a été créée
SELECT
    routine_name,
    routine_type,
    data_type
FROM information_schema.routines
WHERE routine_name = 'add_message_to_conversation'
  AND routine_schema = 'public';

-- Afficher la signature de la fonction
SELECT
    p.proname AS function_name,
    pg_get_function_arguments(p.oid) AS arguments
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE p.proname = 'add_message_to_conversation'
  AND n.nspname = 'public';
