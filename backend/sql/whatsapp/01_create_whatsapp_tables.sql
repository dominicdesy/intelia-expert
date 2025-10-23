-- WhatsApp Integration Tables
-- Version: 1.0
-- Description: Tables pour gérer l'intégration WhatsApp via Twilio

-- =====================================================
-- TABLE 1: user_whatsapp_info
-- Lie les numéros WhatsApp aux comptes utilisateurs
-- =====================================================

CREATE TABLE IF NOT EXISTS user_whatsapp_info (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) UNIQUE NOT NULL,
    whatsapp_number VARCHAR(50) NOT NULL,
    whatsapp_verified BOOLEAN DEFAULT FALSE,
    verification_code VARCHAR(10),
    verification_sent_at TIMESTAMP,
    verified_at TIMESTAMP,
    plan_name VARCHAR(50) DEFAULT 'essential',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Index pour recherche rapide par numéro
    CONSTRAINT unique_whatsapp_number UNIQUE (whatsapp_number)
);

CREATE INDEX idx_whatsapp_number ON user_whatsapp_info(whatsapp_number);
CREATE INDEX idx_user_email_whatsapp ON user_whatsapp_info(user_email);


-- =====================================================
-- TABLE 2: whatsapp_message_logs
-- Log tous les messages WhatsApp (audit et debug)
-- =====================================================

CREATE TABLE IF NOT EXISTS whatsapp_message_logs (
    id SERIAL PRIMARY KEY,
    from_number VARCHAR(50) NOT NULL,
    to_number VARCHAR(50) NOT NULL,
    message_sid VARCHAR(100) UNIQUE NOT NULL,
    message_type VARCHAR(50) NOT NULL, -- text, audio, image, video, etc.
    body TEXT,
    media_url TEXT,
    status VARCHAR(50) NOT NULL, -- received, sent, processed, error, rejected
    user_email VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE INDEX idx_message_sid ON whatsapp_message_logs(message_sid);
CREATE INDEX idx_from_number ON whatsapp_message_logs(from_number);
CREATE INDEX idx_user_email_messages ON whatsapp_message_logs(user_email);
CREATE INDEX idx_created_at_messages ON whatsapp_message_logs(created_at DESC);


-- =====================================================
-- TABLE 3: whatsapp_conversations
-- Stocke les conversations WhatsApp (similaire aux conversations web)
-- =====================================================

CREATE TABLE IF NOT EXISTS whatsapp_conversations (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    whatsapp_number VARCHAR(50) NOT NULL,
    conversation_id VARCHAR(100) UNIQUE NOT NULL,
    messages JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    -- Métadonnées
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_conversation_id ON whatsapp_conversations(conversation_id);
CREATE INDEX idx_user_whatsapp_conv ON whatsapp_conversations(user_email);
CREATE INDEX idx_last_message ON whatsapp_conversations(last_message_at DESC);


-- =====================================================
-- FONCTIONS UTILITAIRES
-- =====================================================

-- Fonction pour obtenir ou créer une conversation WhatsApp
CREATE OR REPLACE FUNCTION get_or_create_whatsapp_conversation(
    p_user_email VARCHAR(255),
    p_whatsapp_number VARCHAR(50)
) RETURNS VARCHAR(100) AS $$
DECLARE
    v_conversation_id VARCHAR(100);
BEGIN
    -- Chercher une conversation active
    SELECT conversation_id INTO v_conversation_id
    FROM whatsapp_conversations
    WHERE user_email = p_user_email
      AND whatsapp_number = p_whatsapp_number
      AND is_active = TRUE
    ORDER BY last_message_at DESC
    LIMIT 1;

    -- Si aucune conversation active, en créer une
    IF v_conversation_id IS NULL THEN
        v_conversation_id := 'whatsapp_' || p_user_email || '_' || EXTRACT(EPOCH FROM NOW())::BIGINT;

        INSERT INTO whatsapp_conversations (
            user_email, whatsapp_number, conversation_id
        ) VALUES (
            p_user_email, p_whatsapp_number, v_conversation_id
        );
    END IF;

    RETURN v_conversation_id;
END;
$$ LANGUAGE plpgsql;


-- Fonction pour ajouter un message à une conversation WhatsApp
CREATE OR REPLACE FUNCTION add_message_to_whatsapp_conversation(
    p_conversation_id VARCHAR(100),
    p_message JSONB
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE whatsapp_conversations
    SET messages = messages || p_message,
        message_count = message_count + 1,
        last_message_at = CURRENT_TIMESTAMP
    WHERE conversation_id = p_conversation_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;


-- =====================================================
-- VUES UTILES
-- =====================================================

-- Vue: Statistiques WhatsApp par utilisateur
CREATE OR REPLACE VIEW whatsapp_user_stats AS
SELECT
    uwi.user_email,
    uwi.whatsapp_number,
    uwi.whatsapp_verified,
    uwi.plan_name,
    COUNT(wml.id) as total_messages,
    COUNT(CASE WHEN wml.message_type = 'text' THEN 1 END) as text_messages,
    COUNT(CASE WHEN wml.message_type = 'audio' THEN 1 END) as audio_messages,
    COUNT(CASE WHEN wml.message_type = 'image' THEN 1 END) as image_messages,
    MAX(wml.created_at) as last_message_at,
    uwi.created_at as registered_at
FROM user_whatsapp_info uwi
LEFT JOIN whatsapp_message_logs wml ON uwi.user_email = wml.user_email
GROUP BY uwi.user_email, uwi.whatsapp_number, uwi.whatsapp_verified,
         uwi.plan_name, uwi.created_at;


-- Vue: Messages WhatsApp récents
CREATE OR REPLACE VIEW recent_whatsapp_messages AS
SELECT
    wml.id,
    wml.from_number,
    wml.to_number,
    wml.message_type,
    wml.body,
    wml.status,
    wml.user_email,
    uwi.plan_name,
    wml.created_at
FROM whatsapp_message_logs wml
LEFT JOIN user_whatsapp_info uwi ON wml.user_email = uwi.user_email
ORDER BY wml.created_at DESC
LIMIT 100;


-- =====================================================
-- COMMENTAIRES
-- =====================================================

COMMENT ON TABLE user_whatsapp_info IS 'Lie les numéros WhatsApp aux comptes utilisateurs Intelia';
COMMENT ON TABLE whatsapp_message_logs IS 'Log de tous les messages WhatsApp pour audit et debug';
COMMENT ON TABLE whatsapp_conversations IS 'Stocke les conversations WhatsApp complètes';

COMMENT ON FUNCTION get_or_create_whatsapp_conversation IS 'Récupère ou crée une conversation WhatsApp active';
COMMENT ON FUNCTION add_message_to_whatsapp_conversation IS 'Ajoute un message à une conversation WhatsApp existante';
