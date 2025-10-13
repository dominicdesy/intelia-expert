-- ============================================================================
-- FIX: Générer automatiquement les titres manquants pour les conversations
-- VERSION 2 - Gestion robuste du trigger existant
-- ============================================================================

-- ===== ÉTAPE 1: Modifier la fonction de trigger =====

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

-- Note: Le trigger existe déjà, la fonction a été mise à jour
-- Le trigger utilisera automatiquement la nouvelle version de la fonction


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


-- ===== VÉRIFICATION ET STATISTIQUES =====

DO $$
DECLARE
    v_total INT;
    v_with_title INT;
    v_without_title INT;
    v_updated INT;
BEGIN
    -- Compter avant/après
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE title IS NOT NULL),
        COUNT(*) FILTER (WHERE title IS NULL)
    INTO v_total, v_with_title, v_without_title
    FROM conversations
    WHERE status = 'active';

    RAISE NOTICE '';
    RAISE NOTICE '=== RÉSULTAT DE LA MISE À JOUR ===';
    RAISE NOTICE 'Total conversations actives: %', v_total;
    RAISE NOTICE 'Avec titre: % (%.1f%%)', v_with_title, (v_with_title::FLOAT / NULLIF(v_total, 0) * 100);
    RAISE NOTICE 'Sans titre: % (%.1f%%)', v_without_title, (v_without_title::FLOAT / NULLIF(v_total, 0) * 100);
    RAISE NOTICE '';

    IF v_without_title > 0 THEN
        RAISE WARNING '⚠️  Il reste % conversations sans titre! Vérifier les données.', v_without_title;
    ELSE
        RAISE NOTICE '✅ Toutes les conversations ont un titre!';
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE '📌 Le trigger a été mis à jour avec succès.';
    RAISE NOTICE '   Les nouvelles conversations auront automatiquement un titre.';
    RAISE NOTICE '';
END $$;


-- ===== EXEMPLES DE VÉRIFICATION =====

-- Lister quelques conversations avec leurs titres
SELECT
    LEFT(id::text, 8) as id_prefix,
    title,
    message_count,
    created_at::date,
    language
FROM conversations
WHERE status = 'active'
ORDER BY created_at DESC
LIMIT 10;
