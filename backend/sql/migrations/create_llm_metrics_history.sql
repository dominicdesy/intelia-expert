-- Migration: Create LLM metrics history table
-- Date: 2025-10-26
-- Purpose: Store historical LLM metrics from Prometheus for long-term analysis (6+ months)

CREATE TABLE IF NOT EXISTS llm_metrics_history (
    id SERIAL PRIMARY KEY,

    -- Timestamp
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Model info
    model VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,  -- openai, anthropic, deepseek
    feature VARCHAR(50),  -- chat, cot, etc.

    -- Metrics
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0.00,
    request_count INTEGER DEFAULT 1,

    -- Duration (in seconds)
    avg_duration_seconds DECIMAL(10, 3),

    -- Status
    status VARCHAR(20) DEFAULT 'success',  -- success, error, timeout

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes for efficient queries
    CONSTRAINT unique_metric_record UNIQUE (recorded_at, model, provider, feature, status)
);

-- Index for date range queries (monthly reports)
CREATE INDEX idx_llm_metrics_recorded_at ON llm_metrics_history(recorded_at DESC);

-- Index for model analysis
CREATE INDEX idx_llm_metrics_model ON llm_metrics_history(model);

-- Index for provider analysis
CREATE INDEX idx_llm_metrics_provider ON llm_metrics_history(provider);

-- Index for cost analysis
CREATE INDEX idx_llm_metrics_cost ON llm_metrics_history(cost_usd DESC);

COMMENT ON TABLE llm_metrics_history IS 'Historical LLM metrics synced from Prometheus for long-term analysis and monthly cost tracking';
COMMENT ON COLUMN llm_metrics_history.recorded_at IS 'Timestamp when the metric was recorded (from Prometheus scrape time)';
COMMENT ON COLUMN llm_metrics_history.cost_usd IS 'Cost in USD for this metric record';
COMMENT ON COLUMN llm_metrics_history.total_tokens IS 'Total tokens (prompt + completion)';
