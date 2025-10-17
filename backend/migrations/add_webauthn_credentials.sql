-- Migration: Add WebAuthn credentials table to SUPABASE
-- Description: Store WebAuthn/Passkey credentials for biometric authentication
-- Date: 2025-10-16
-- Database: Supabase PostgreSQL (auth.users schema)

-- Create webauthn_credentials table in PUBLIC schema (Supabase)
CREATE TABLE IF NOT EXISTS public.webauthn_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    credential_id TEXT NOT NULL UNIQUE,
    public_key TEXT NOT NULL,
    counter BIGINT NOT NULL DEFAULT 0,
    device_type TEXT,
    device_name TEXT,
    transports TEXT[], -- Array of transport types: ["usb", "nfc", "ble", "internal"]
    backup_eligible BOOLEAN DEFAULT false,
    backup_state BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_webauthn_user_id ON public.webauthn_credentials(user_id);
CREATE INDEX IF NOT EXISTS idx_webauthn_credential_id ON public.webauthn_credentials(credential_id);
CREATE INDEX IF NOT EXISTS idx_webauthn_created_at ON public.webauthn_credentials(created_at DESC);

-- Enable Row Level Security (RLS) - REQUIRED for Supabase
ALTER TABLE public.webauthn_credentials ENABLE ROW LEVEL SECURITY;

-- Create policy: Users can only see their own credentials
CREATE POLICY "Users can view own webauthn credentials"
    ON public.webauthn_credentials
    FOR SELECT
    USING (auth.uid() = user_id);

-- Create policy: Users can insert their own credentials
CREATE POLICY "Users can insert own webauthn credentials"
    ON public.webauthn_credentials
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Create policy: Users can update their own credentials
CREATE POLICY "Users can update own webauthn credentials"
    ON public.webauthn_credentials
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Create policy: Users can delete their own credentials
CREATE POLICY "Users can delete own webauthn credentials"
    ON public.webauthn_credentials
    FOR DELETE
    USING (auth.uid() = user_id);

-- Comments for documentation
COMMENT ON TABLE public.webauthn_credentials IS 'Stores WebAuthn/Passkey credentials for biometric authentication (Face ID, Touch ID, fingerprint, etc.)';
COMMENT ON COLUMN public.webauthn_credentials.credential_id IS 'Base64URL-encoded credential ID from WebAuthn';
COMMENT ON COLUMN public.webauthn_credentials.public_key IS 'Base64URL-encoded public key from WebAuthn';
COMMENT ON COLUMN public.webauthn_credentials.counter IS 'Signature counter to prevent credential cloning attacks';
COMMENT ON COLUMN public.webauthn_credentials.device_type IS 'Type of authenticator: platform (built-in) or cross-platform (security key)';
COMMENT ON COLUMN public.webauthn_credentials.device_name IS 'User-friendly name for the device (e.g., "iPhone 15", "MacBook Pro")';
COMMENT ON COLUMN public.webauthn_credentials.transports IS 'Array of supported transport types';
COMMENT ON COLUMN public.webauthn_credentials.backup_eligible IS 'Whether credential is eligible for backup (synced passkeys)';
COMMENT ON COLUMN public.webauthn_credentials.backup_state IS 'Whether credential is currently backed up';
