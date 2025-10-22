-- Migration: Add CoT (Chain of Thought) columns to qa_quality_checks table
-- Purpose: Store Claude Extended Thinking analysis for debugging anomalies
-- Created: 2025-10-22

-- Add columns for CoT analysis
ALTER TABLE qa_quality_checks
ADD COLUMN IF NOT EXISTS cot_thinking TEXT,           -- Claude's reasoning/thinking blocks
ADD COLUMN IF NOT EXISTS cot_analyzed_at TIMESTAMP,   -- When CoT analysis was performed
ADD COLUMN IF NOT EXISTS cot_analyzed_by VARCHAR(255),-- Admin who triggered the analysis
ADD COLUMN IF NOT EXISTS cot_token_count INTEGER,     -- Number of thinking tokens used
ADD COLUMN IF NOT EXISTS cot_cost_usd DECIMAL(10, 6); -- Cost of the CoT analysis in USD

-- Add index for queries filtering by CoT analysis
CREATE INDEX IF NOT EXISTS idx_qa_quality_checks_cot_analyzed
ON qa_quality_checks(cot_analyzed_at)
WHERE cot_analyzed_at IS NOT NULL;

-- Add comment explaining the columns
COMMENT ON COLUMN qa_quality_checks.cot_thinking IS 'Claude Extended Thinking reasoning blocks - used for admin debugging of anomalies';
COMMENT ON COLUMN qa_quality_checks.cot_analyzed_at IS 'Timestamp when admin manually triggered CoT analysis';
COMMENT ON COLUMN qa_quality_checks.cot_analyzed_by IS 'Email of admin who triggered the analysis';
COMMENT ON COLUMN qa_quality_checks.cot_token_count IS 'Number of thinking tokens used in the analysis (budget: 4000)';
COMMENT ON COLUMN qa_quality_checks.cot_cost_usd IS 'Cost of the CoT analysis in USD (thinking: $3/1M, output: $15/1M)';
