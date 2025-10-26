-- Migration: Create infrastructure metrics tables
-- Date: 2025-10-26
-- Purpose: Store external infrastructure costs and usage metrics

-- ============================================================
-- DIGITAL OCEAN METRICS
-- ============================================================
CREATE TABLE IF NOT EXISTS do_metrics (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- App Platform
    app_platform_cost_usd DECIMAL(10, 2) DEFAULT 0.00,
    app_platform_apps INTEGER DEFAULT 0,

    -- Database
    db_cost_usd DECIMAL(10, 2) DEFAULT 0.00,
    db_size_gb DECIMAL(10, 2) DEFAULT 0.00,

    -- Container Registry
    registry_cost_usd DECIMAL(10, 2) DEFAULT 0.00,
    registry_size_gb DECIMAL(10, 2) DEFAULT 0.00,
    registry_bandwidth_gb DECIMAL(10, 2) DEFAULT 0.00,

    -- Spaces (Object Storage)
    spaces_cost_usd DECIMAL(10, 2) DEFAULT 0.00,
    spaces_size_gb DECIMAL(10, 2) DEFAULT 0.00,

    -- Total
    total_cost_usd DECIMAL(10, 2) DEFAULT 0.00,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_do_metric_record UNIQUE (recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_do_metrics_recorded_at ON do_metrics(recorded_at DESC);

-- ============================================================
-- STRIPE METRICS (Revenue)
-- ============================================================
CREATE TABLE IF NOT EXISTS stripe_metrics (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Revenue
    mrr_usd DECIMAL(10, 2) DEFAULT 0.00,  -- Monthly Recurring Revenue
    arr_usd DECIMAL(10, 2) DEFAULT 0.00,  -- Annual Recurring Revenue

    -- Customers
    active_subscriptions INTEGER DEFAULT 0,
    new_subscriptions INTEGER DEFAULT 0,
    cancelled_subscriptions INTEGER DEFAULT 0,
    churn_rate_percent DECIMAL(5, 2) DEFAULT 0.00,

    -- Plans breakdown
    essential_subs INTEGER DEFAULT 0,
    pro_subs INTEGER DEFAULT 0,
    elite_subs INTEGER DEFAULT 0,

    -- Revenue by plan
    essential_mrr DECIMAL(10, 2) DEFAULT 0.00,
    pro_mrr DECIMAL(10, 2) DEFAULT 0.00,
    elite_mrr DECIMAL(10, 2) DEFAULT 0.00,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_stripe_metric_record UNIQUE (recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_stripe_metrics_recorded_at ON stripe_metrics(recorded_at DESC);

-- ============================================================
-- WEAVIATE METRICS
-- ============================================================
CREATE TABLE IF NOT EXISTS weaviate_metrics (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Storage
    total_objects INTEGER DEFAULT 0,
    storage_size_mb DECIMAL(10, 2) DEFAULT 0.00,

    -- Usage
    queries_count INTEGER DEFAULT 0,
    avg_query_time_ms DECIMAL(10, 2) DEFAULT 0.00,

    -- Cost estimate (if applicable)
    estimated_cost_usd DECIMAL(10, 2) DEFAULT 0.00,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_weaviate_metric_record UNIQUE (recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_weaviate_metrics_recorded_at ON weaviate_metrics(recorded_at DESC);

-- ============================================================
-- SUPABASE METRICS
-- ============================================================
CREATE TABLE IF NOT EXISTS supabase_metrics (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Auth
    total_users INTEGER DEFAULT 0,
    active_users_7d INTEGER DEFAULT 0,
    active_users_30d INTEGER DEFAULT 0,

    -- Storage
    storage_size_gb DECIMAL(10, 2) DEFAULT 0.00,
    storage_objects INTEGER DEFAULT 0,

    -- Database
    db_size_mb DECIMAL(10, 2) DEFAULT 0.00,

    -- Cost
    total_cost_usd DECIMAL(10, 2) DEFAULT 0.00,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_supabase_metric_record UNIQUE (recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_supabase_metrics_recorded_at ON supabase_metrics(recorded_at DESC);

-- ============================================================
-- TWILIO METRICS
-- ============================================================
CREATE TABLE IF NOT EXISTS twilio_metrics (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- SMS
    sms_sent INTEGER DEFAULT 0,
    sms_cost_usd DECIMAL(10, 2) DEFAULT 0.00,

    -- WhatsApp
    whatsapp_sent INTEGER DEFAULT 0,
    whatsapp_cost_usd DECIMAL(10, 2) DEFAULT 0.00,

    -- Voice (if used)
    voice_minutes INTEGER DEFAULT 0,
    voice_cost_usd DECIMAL(10, 2) DEFAULT 0.00,

    -- Total
    total_cost_usd DECIMAL(10, 2) DEFAULT 0.00,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_twilio_metric_record UNIQUE (recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_twilio_metrics_recorded_at ON twilio_metrics(recorded_at DESC);

-- ============================================================
-- AGGREGATED COSTS VIEW
-- ============================================================
CREATE OR REPLACE VIEW infrastructure_costs_summary AS
SELECT
    date_trunc('day', recorded_at) as date,

    -- LLM costs
    COALESCE(SUM(llm.cost_usd), 0) as llm_cost_usd,

    -- Infrastructure costs
    COALESCE(AVG(do.total_cost_usd), 0) as do_cost_usd,
    COALESCE(AVG(wv.estimated_cost_usd), 0) as weaviate_cost_usd,
    COALESCE(AVG(sb.total_cost_usd), 0) as supabase_cost_usd,
    COALESCE(AVG(tw.total_cost_usd), 0) as twilio_cost_usd,

    -- Revenue
    COALESCE(AVG(st.mrr_usd), 0) as mrr_usd,

    -- Total costs
    COALESCE(SUM(llm.cost_usd), 0) +
    COALESCE(AVG(do.total_cost_usd), 0) +
    COALESCE(AVG(wv.estimated_cost_usd), 0) +
    COALESCE(AVG(sb.total_cost_usd), 0) +
    COALESCE(AVG(tw.total_cost_usd), 0) as total_cost_usd,

    -- Margin
    COALESCE(AVG(st.mrr_usd), 0) - (
        COALESCE(SUM(llm.cost_usd), 0) +
        COALESCE(AVG(do.total_cost_usd), 0) +
        COALESCE(AVG(wv.estimated_cost_usd), 0) +
        COALESCE(AVG(sb.total_cost_usd), 0) +
        COALESCE(AVG(tw.total_cost_usd), 0)
    ) as margin_usd

FROM generate_series(
    current_date - interval '90 days',
    current_date,
    interval '1 day'
) as recorded_at

LEFT JOIN llm_metrics_history llm ON date_trunc('day', llm.recorded_at) = date_trunc('day', recorded_at)
LEFT JOIN do_metrics do ON date_trunc('day', do.recorded_at) = date_trunc('day', recorded_at)
LEFT JOIN weaviate_metrics wv ON date_trunc('day', wv.recorded_at) = date_trunc('day', recorded_at)
LEFT JOIN supabase_metrics sb ON date_trunc('day', sb.recorded_at) = date_trunc('day', recorded_at)
LEFT JOIN twilio_metrics tw ON date_trunc('day', tw.recorded_at) = date_trunc('day', recorded_at)
LEFT JOIN stripe_metrics st ON date_trunc('day', st.recorded_at) = date_trunc('day', recorded_at)

GROUP BY date
ORDER BY date DESC;

COMMENT ON TABLE do_metrics IS 'Digital Ocean infrastructure costs and usage metrics';
COMMENT ON TABLE stripe_metrics IS 'Stripe revenue and subscription metrics (MRR, churn, etc)';
COMMENT ON TABLE weaviate_metrics IS 'Weaviate vector database usage and performance';
COMMENT ON TABLE supabase_metrics IS 'Supabase auth and storage metrics';
COMMENT ON TABLE twilio_metrics IS 'Twilio SMS/WhatsApp communication costs';
COMMENT ON VIEW infrastructure_costs_summary IS 'Aggregated view of all costs vs revenue with daily granularity';
