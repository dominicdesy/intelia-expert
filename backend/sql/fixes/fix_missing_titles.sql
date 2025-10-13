-- ============================================================================
-- FIX: Générer automatiquement les titres manquants pour les conversations
-- ============================================================================
-- Problème: Les conversations créées n'ont pas de titre (NULL)
-- Solution: 1) Mettre à jour le trigger pour générer les titres automatiquement
--           2) Générer les titres pour les conversations existantes
-- ============================================================================

-- ===== ÉTAPE 1: Modifier le trigger pour générer le titre automatiquement =====

CREATE OR REPLACE FUNCTION update_conversation_metadata()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET
        message_count = (
            SELECT COUNT(*)
            FROM messages
            WHERE conversation_id = NEW.conversation_id
        ),
        last_message_preview = SUBSTRING(NEW.content, 1, 200),
        last_activity_at = NOW(),
        updated_at = NOW()
    WHERE id = NEW.conversation_id;

    -- Mettre à jour first_message_preview si c'est le premier message
    UPDATE conversations
    SET first_message_preview = SUBSTRING(NEW.content, 1, 200)
    WHERE id = NEW.conversation_id
      AND first_message_preview IS NULL;

    -- 🆕 NOUVEAU: Générer le titre automatiquement basé sur le premier message user
    UPDATE conversations
    SET title = CASE
        WHEN LENGTH(NEW.content) <= 60 THEN NEW.content
        ELSE SUBSTRING(NEW.content, 1, 60) || '...'
    END
    WHERE id = NEW.conversation_id
      AND title IS NULL
      AND NEW.role = 'user'
      AND NEW.sequence_number = 1;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Re-créer le trigger avec la nouvelle fonction
DROP TRIGGER IF EXISTS update_conversation_on_message_insert ON messages;
CREATE TRIGGER update_conversation_on_message_insert
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_metadata();


-- ===== ÉTAPE 2: Générer les titres pour les conversations existantes =====

-- Mettre à jour toutes les conversations sans titre en utilisant le premier message user
UPDATE conversations c
SET
    title = CASE
        WHEN LENGTH(m.content) <= 60 THEN m.content
        ELSE SUBSTRING(m.content, 1, 60) || '...'
    END,
    updated_at = NOW()
FROM messages m
WHERE c.id = m.conversation_id
  AND m.role = 'user'
  AND m.sequence_number = 1
  AND c.title IS NULL;

-- Afficher le résultat
SELECT
    COUNT(*) as total_updated,
    COUNT(*) FILTER (WHERE title IS NOT NULL) as with_title,
    COUNT(*) FILTER (WHERE title IS NULL) as without_title
FROM conversations
WHERE status = 'active';

-- ===== VÉRIFICATION =====

-- Lister quelques conversations avec leurs titres
SELECT
    id::text,
    title,
    message_count,
    created_at,
    language
FROM conversations
WHERE status = 'active'
ORDER BY created_at DESC
LIMIT 10;

-- Afficher les statistiques
DO $$
DECLARE
    v_total INT;
    v_with_title INT;
    v_without_title INT;
BEGIN
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE title IS NOT NULL),
        COUNT(*) FILTER (WHERE title IS NULL)
    INTO v_total, v_with_title, v_without_title
    FROM conversations
    WHERE status = 'active';

    RAISE NOTICE '=== RÉSULTAT ===';
    RAISE NOTICE 'Total conversations actives: %', v_total;
    RAISE NOTICE 'Avec titre: % (%.1f%%)', v_with_title, (v_with_title::FLOAT / NULLIF(v_total, 0) * 100);
    RAISE NOTICE 'Sans titre: % (%.1f%%)', v_without_title, (v_without_title::FLOAT / NULLIF(v_total, 0) * 100);

    IF v_without_title > 0 THEN
        RAISE WARNING '⚠️  Il reste % conversations sans titre!', v_without_title;
    ELSE
        RAISE NOTICE '✅ Toutes les conversations ont un titre!';
    END IF;
END $$;
