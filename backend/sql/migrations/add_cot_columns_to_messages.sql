-- ============================================================================
-- MIGRATION: Ajouter colonnes Chain-of-Thought à la table messages
-- ============================================================================
-- Date: 2025-10-19
-- Description: Ajoute cot_thinking et cot_analysis pour sauvegarder le
--              raisonnement LLM (analytics/debugging) sans l'afficher au frontend
-- ============================================================================

-- Ajouter colonnes CoT à la table messages
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS cot_thinking TEXT,
ADD COLUMN IF NOT EXISTS cot_analysis TEXT,
ADD COLUMN IF NOT EXISTS has_cot_structure BOOLEAN DEFAULT FALSE;

-- Index pour recherche analytique sur messages avec CoT
CREATE INDEX IF NOT EXISTS idx_messages_has_cot ON messages(has_cot_structure) WHERE has_cot_structure = TRUE;

-- Commentaires pour documentation
COMMENT ON COLUMN messages.cot_thinking IS 'Contenu de la section <thinking> - raisonnement initial du LLM';
COMMENT ON COLUMN messages.cot_analysis IS 'Contenu de la section <analysis> - analyse détaillée étape par étape';
COMMENT ON COLUMN messages.has_cot_structure IS 'Indicateur si le message contient une structure CoT (pour analytics)';

-- Vérification
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'messages'
  AND column_name IN ('cot_thinking', 'cot_analysis', 'has_cot_structure')
ORDER BY column_name;
