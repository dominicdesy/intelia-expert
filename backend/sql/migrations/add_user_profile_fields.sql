-- Migration: Add production_type and category fields to users table
-- Purpose: Capture user's production type (broiler/layer) and value chain category
-- Date: 2025-01-22

-- Add new columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS production_type TEXT[],
ADD COLUMN IF NOT EXISTS category TEXT,
ADD COLUMN IF NOT EXISTS category_other TEXT;

-- Add comments for documentation
COMMENT ON COLUMN users.production_type IS 'Array of production types: broiler, layer, or both';
COMMENT ON COLUMN users.category IS 'User category in value chain: breeding_hatchery, feed_nutrition, farm_operations, health_veterinary, processing, management_oversight, equipment_technology, other';
COMMENT ON COLUMN users.category_other IS 'Free text description when category is "other"';

-- Create index for category queries
CREATE INDEX IF NOT EXISTS idx_users_category ON users(category);

-- Create GIN index for production_type array queries
CREATE INDEX IF NOT EXISTS idx_users_production_type ON users USING GIN(production_type);
