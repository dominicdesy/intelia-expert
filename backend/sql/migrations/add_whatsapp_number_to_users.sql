-- Add whatsapp_number column to users table
-- This allows users to link their WhatsApp number to their profile

ALTER TABLE users
ADD COLUMN IF NOT EXISTS whatsapp_number VARCHAR(50);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_whatsapp_number
ON users(whatsapp_number)
WHERE whatsapp_number IS NOT NULL;

-- Add comment
COMMENT ON COLUMN users.whatsapp_number IS 'WhatsApp number for chat integration (format: +1234567890)';
