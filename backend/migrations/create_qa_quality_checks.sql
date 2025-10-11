-- Migration: Create qa_quality_checks table for AI-powered quality monitoring
-- Date: 2025-10-11
-- Purpose: Track and flag potentially problematic Q&A responses

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS qa_quality_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,

    -- Q&A Content
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    response_source VARCHAR(50),
    response_confidence DECIMAL(3,2),

    -- Quality Analysis Results
    quality_score DECIMAL(3,1) CHECK (quality_score >= 0 AND quality_score <= 10),
    is_problematic BOOLEAN DEFAULT false,
    problem_category VARCHAR(50),
    problems JSONB DEFAULT '[]'::jsonb,
    recommendation TEXT,
    analysis_confidence DECIMAL(3,2) CHECK (analysis_confidence >= 0 AND analysis_confidence <= 1),

    -- Analysis Details
    analysis_trigger VARCHAR(50) DEFAULT 'manual',
    analysis_model VARCHAR(50) DEFAULT 'gpt-3.5-turbo',
    analysis_prompt_version VARCHAR(20) DEFAULT 'v1.0',

    -- Review Workflow
    analyzed_at TIMESTAMP DEFAULT NOW(),
    reviewed BOOLEAN DEFAULT false,
    reviewed_at TIMESTAMP,
    reviewed_by UUID,
    reviewer_notes TEXT,
    false_positive BOOLEAN DEFAULT false,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_qa_quality_conversation ON qa_quality_checks(conversation_id);
CREATE INDEX idx_qa_quality_user ON qa_quality_checks(user_id);
CREATE INDEX idx_qa_quality_problematic ON qa_quality_checks(is_problematic, analyzed_at DESC);
CREATE INDEX idx_qa_quality_reviewed ON qa_quality_checks(reviewed, is_problematic);
CREATE INDEX idx_qa_quality_category ON qa_quality_checks(problem_category) WHERE is_problematic = true;
CREATE INDEX idx_qa_quality_score ON qa_quality_checks(quality_score) WHERE quality_score < 5;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_qa_quality_checks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
CREATE TRIGGER qa_quality_checks_updated_at
    BEFORE UPDATE ON qa_quality_checks
    FOR EACH ROW
    EXECUTE FUNCTION update_qa_quality_checks_updated_at();

-- View for problematic Q&A with user info
CREATE OR REPLACE VIEW problematic_qa_with_users AS
SELECT
    qc.id,
    qc.conversation_id,
    qc.message_id,
    qc.user_id,
    qc.question,
    qc.response,
    qc.response_source,
    qc.response_confidence,
    qc.quality_score,
    qc.problem_category,
    qc.problems,
    qc.recommendation,
    qc.analysis_confidence,
    qc.analyzed_at,
    qc.reviewed,
    qc.reviewed_at,
    qc.false_positive,
    c.language,
    c.created_at as conversation_created_at
FROM qa_quality_checks qc
JOIN conversations c ON qc.conversation_id = c.id
WHERE qc.is_problematic = true
  AND qc.false_positive = false
ORDER BY qc.analyzed_at DESC;

COMMENT ON TABLE qa_quality_checks IS 'AI-powered quality monitoring for Q&A responses';
COMMENT ON COLUMN qa_quality_checks.quality_score IS 'Overall quality score from 0 to 10';
COMMENT ON COLUMN qa_quality_checks.is_problematic IS 'True if quality_score < 5 or critical issues detected';
COMMENT ON COLUMN qa_quality_checks.problem_category IS 'incorrect|incomplete|off_topic|generic|contradictory|hallucination';
COMMENT ON COLUMN qa_quality_checks.problems IS 'Array of specific detected problems';
COMMENT ON COLUMN qa_quality_checks.analysis_trigger IS 'manual|batch|realtime|negative_feedback';
COMMENT ON COLUMN qa_quality_checks.false_positive IS 'Mark as false positive if analysis was incorrect';
