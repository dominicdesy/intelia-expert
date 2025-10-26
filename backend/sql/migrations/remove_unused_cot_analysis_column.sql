-- Migration: Remove unused cot_analysis column from qa_quality_checks table
-- Purpose: Clean up unused column (we use cot_thinking instead)
-- Created: 2025-10-22

-- Remove the unused cot_analysis column
ALTER TABLE qa_quality_checks
DROP COLUMN IF EXISTS cot_analysis;
