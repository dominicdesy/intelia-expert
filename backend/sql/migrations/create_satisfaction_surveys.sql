-- ============================================================================
-- MIGRATION: Satisfaction Surveys
-- ============================================================================
-- Description: Table pour stocker les sondages de satisfaction globaux
--              par conversation (différent du feedback sur messages individuels)
-- Date: 2025-10-23
-- ============================================================================

-- Table: conversation_satisfaction_surveys
-- Stocke les évaluations de satisfaction globale de l'expérience utilisateur
CREATE TABLE IF NOT EXISTS conversation_satisfaction_surveys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('satisfied', 'neutral', 'unsatisfied')),
    comment TEXT,
    message_count_at_survey INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Index pour recherche et analytics
    CONSTRAINT unique_survey_per_conversation UNIQUE (conversation_id, created_at)
);

-- Index pour analytics et recherche rapide
CREATE INDEX IF NOT EXISTS idx_satisfaction_surveys_user_id ON conversation_satisfaction_surveys(user_id);
CREATE INDEX IF NOT EXISTS idx_satisfaction_surveys_rating ON conversation_satisfaction_surveys(rating);
CREATE INDEX IF NOT EXISTS idx_satisfaction_surveys_created_at ON conversation_satisfaction_surveys(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_satisfaction_surveys_conversation_id ON conversation_satisfaction_surveys(conversation_id);

-- ============================================================================
-- ANALYTICS HELPERS
-- ============================================================================

-- Vue: Stats de satisfaction par période
CREATE OR REPLACE VIEW satisfaction_stats AS
SELECT
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as total_surveys,
    COUNT(*) FILTER (WHERE rating = 'satisfied') as satisfied_count,
    COUNT(*) FILTER (WHERE rating = 'neutral') as neutral_count,
    COUNT(*) FILTER (WHERE rating = 'unsatisfied') as unsatisfied_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE rating = 'satisfied') / COUNT(*), 2) as satisfaction_rate,
    ROUND(100.0 * COUNT(*) FILTER (WHERE rating = 'unsatisfied') / COUNT(*), 2) as dissatisfaction_rate
FROM conversation_satisfaction_surveys
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- Fonction: Récupérer les statistiques de satisfaction
CREATE OR REPLACE FUNCTION get_satisfaction_stats(
    days_back INTEGER DEFAULT 30
)
RETURNS TABLE (
    period TEXT,
    total_surveys BIGINT,
    satisfied_count BIGINT,
    neutral_count BIGINT,
    unsatisfied_count BIGINT,
    satisfaction_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        TO_CHAR(DATE_TRUNC('day', created_at), 'YYYY-MM-DD') as period,
        COUNT(*) as total_surveys,
        COUNT(*) FILTER (WHERE rating = 'satisfied') as satisfied_count,
        COUNT(*) FILTER (WHERE rating = 'neutral') as neutral_count,
        COUNT(*) FILTER (WHERE rating = 'unsatisfied') as unsatisfied_count,
        ROUND(100.0 * COUNT(*) FILTER (WHERE rating = 'satisfied') / NULLIF(COUNT(*), 0), 2) as satisfaction_rate
    FROM conversation_satisfaction_surveys
    WHERE created_at >= NOW() - INTERVAL '1 day' * days_back
    GROUP BY DATE_TRUNC('day', created_at)
    ORDER BY period DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Vérifier que la table a été créée
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'conversation_satisfaction_surveys'
ORDER BY ordinal_position;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. Un sondage peut avoir plusieurs entrées par conversation (ex: tous les 40 messages)
-- 2. La contrainte UNIQUE empêche les doublons accidentels à la même seconde
-- 3. message_count_at_survey permet de tracker l'évolution de satisfaction dans le temps
-- 4. Le rating est différent du feedback sur messages individuels (thumbs up/down)
-- 5. Vue satisfaction_stats pour analytics rapides
