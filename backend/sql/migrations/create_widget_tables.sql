-- ============================================
-- Widget Integration Tables
-- VERSION 1.0.0
-- ============================================

-- Table: widget_clients
-- Stocke les informations des clients (entreprises) qui utilisent le widget
CREATE TABLE IF NOT EXISTS widget_clients (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(255) UNIQUE NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),  -- Domaine autorisé pour CORS
    is_active BOOLEAN DEFAULT TRUE,
    monthly_limit INTEGER DEFAULT 1000,  -- Nombre de requêtes par mois
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb  -- Infos additionnelles (plan, contact, etc.)
);

CREATE INDEX IF NOT EXISTS idx_widget_clients_client_id ON widget_clients(client_id);
CREATE INDEX IF NOT EXISTS idx_widget_clients_is_active ON widget_clients(is_active);

-- Table: widget_usage
-- Enregistre chaque utilisation du widget pour comptabilisation
CREATE TABLE IF NOT EXISTS widget_usage (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),  -- ID utilisateur dans le système du client (optionnel)
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    request_type VARCHAR(50) DEFAULT 'chat',  -- 'chat', 'feedback', etc.
    conversation_id VARCHAR(255),
    message_length INTEGER,
    response_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_widget_usage_client_id ON widget_usage(client_id);
CREATE INDEX IF NOT EXISTS idx_widget_usage_timestamp ON widget_usage(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_widget_usage_client_timestamp ON widget_usage(client_id, timestamp DESC);

-- Table: widget_conversations
-- Stocke les conversations pour historique et analytics
CREATE TABLE IF NOT EXISTS widget_conversations (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) UNIQUE NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_widget_conversations_conversation_id ON widget_conversations(conversation_id);
CREATE INDEX IF NOT EXISTS idx_widget_conversations_client_id ON widget_conversations(client_id);
CREATE INDEX IF NOT EXISTS idx_widget_conversations_started_at ON widget_conversations(started_at DESC);

-- Table: widget_messages
-- Stocke les messages individuels des conversations widget
CREATE TABLE IF NOT EXISTS widget_messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user' ou 'assistant'
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    FOREIGN KEY (conversation_id) REFERENCES widget_conversations(conversation_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_widget_messages_conversation_id ON widget_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_widget_messages_timestamp ON widget_messages(timestamp DESC);

-- Vue: widget_monthly_usage
-- Agrégation mensuelle de l'utilisation par client
CREATE OR REPLACE VIEW widget_monthly_usage AS
SELECT
    client_id,
    DATE_TRUNC('month', timestamp) AS month,
    COUNT(*) AS total_requests,
    COUNT(*) FILTER (WHERE success = TRUE) AS successful_requests,
    COUNT(*) FILTER (WHERE success = FALSE) AS failed_requests,
    AVG(response_time_ms) AS avg_response_time_ms,
    COUNT(DISTINCT user_id) AS unique_users,
    COUNT(DISTINCT conversation_id) AS unique_conversations
FROM widget_usage
GROUP BY client_id, DATE_TRUNC('month', timestamp)
ORDER BY month DESC, client_id;

-- Commentaires pour documentation
COMMENT ON TABLE widget_clients IS 'Clients (entreprises) utilisant le widget Intelia';
COMMENT ON TABLE widget_usage IS 'Historique d''utilisation du widget par client';
COMMENT ON TABLE widget_conversations IS 'Conversations widget pour historique';
COMMENT ON TABLE widget_messages IS 'Messages individuels des conversations widget';
COMMENT ON VIEW widget_monthly_usage IS 'Statistiques mensuelles d''utilisation du widget';

-- Insertion d'un client de test (optionnel)
-- INSERT INTO widget_clients (client_id, client_name, domain, monthly_limit)
-- VALUES ('test-client-001', 'Test Client', 'localhost', 10000)
-- ON CONFLICT (client_id) DO NOTHING;
