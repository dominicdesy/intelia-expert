-- Migration: Add Chain-of-Thought fields to qa_quality_checks
-- Date: 2025-10-21
-- Purpose: Store LLM reasoning (thinking + analysis) for quality checks

ALTER TABLE qa_quality_checks
    ADD COLUMN IF NOT EXISTS cot_thinking TEXT,
    ADD COLUMN IF NOT EXISTS cot_analysis TEXT,
    ADD COLUMN IF NOT EXISTS has_cot_structure BOOLEAN DEFAULT false;

-- Index for filtering by CoT availability
CREATE INDEX IF NOT EXISTS idx_qa_quality_has_cot ON qa_quality_checks(has_cot_structure) WHERE has_cot_structure = true;

COMMENT ON COLUMN qa_quality_checks.cot_thinking IS 'LLM initial reasoning about the question (from <thinking> tag)';
COMMENT ON COLUMN qa_quality_checks.cot_analysis IS 'LLM detailed step-by-step analysis (from <analysis> tag)';
COMMENT ON COLUMN qa_quality_checks.has_cot_structure IS 'True if response includes Chain-of-Thought structure';
