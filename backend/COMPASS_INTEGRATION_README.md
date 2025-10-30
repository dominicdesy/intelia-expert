# Compass Integration - Implementation Guide

**Status**: Backend Complete ✅
**Date**: 2025-10-30
**Version**: 1.0.0

## Overview

The Compass integration enables Intelia Cognito users who also use **Compass** (Intelia's farm management software) to connect their barns so the GPT can answer real-time questions about their farm data.

## Architecture

```
┌─────────────────┐
│  Frontend UI    │  → Admin configures user barn mappings
│  Statistics →   │
│  Compass Tab    │
└────────┬────────┘
         │
         ↓ HTTP (JWT Auth)
┌─────────────────┐         ┌──────────────┐
│  Backend API    │ ←─────→ │ Compass API  │
│  /api/v1/       │  Token  │ (External)   │
│  compass/*      │         └──────────────┘
└────────┬────────┘
         │
         ↓ SQL
┌─────────────────┐
│  Supabase       │
│  user_compass   │  → Stores barn mappings per user
│  _config        │
└─────────────────┘
```

## Implementation Status

### ✅ Phase 1: Backend Foundation (COMPLETE)

1. **Database Migration** ✅
   - File: `backend/sql/migrations/create_user_compass_config.sql`
   - Table: `user_compass_config`
   - RLS Policies: Admin full access, Users read-only
   - Status: Ready to run

2. **Compass API Service** ✅
   - File: `backend/app/services/compass_api_service.py`
   - Adapted from: `broiler-agent/broiler_agent/core/data/api_client.py`
   - Features:
     - Device list and info
     - Real-time sensor data (temperature, humidity, weight, age)
     - Connection testing
     - Singleton pattern

3. **API Endpoints** ✅
   - File: `backend/app/api/v1/compass.py`
   - Admin Endpoints:
     - `GET /api/v1/compass/admin/users` - List all user configs
     - `GET /api/v1/compass/admin/users/{user_id}` - Get user config
     - `POST /api/v1/compass/admin/users/{user_id}` - Update user config
     - `GET /api/v1/compass/admin/compass/devices` - List Compass devices
     - `GET /api/v1/compass/admin/compass/test-connection` - Test API connection
   - User Endpoints:
     - `GET /api/v1/compass/me` - Get my config
     - `GET /api/v1/compass/me/barns` - Get all my barns data
     - `GET /api/v1/compass/me/barns/{client_number}` - Get specific barn data
   - Health:
     - `GET /api/v1/compass/health` - Service health check

4. **Router Integration** ✅
   - File: `backend/app/api/v1/__init__.py`
   - Router mounted at `/api/v1/compass`
   - Auto-loaded with other API routers

5. **Environment Configuration** ✅
   - File: `backend/.env.compass.example`
   - Required: `COMPASS_API_TOKEN`
   - Optional: `COMPASS_BASE_URL` (defaults to https://compass.intelia.com/api/v1)

### 🚧 Phase 2: Frontend Admin UI (PENDING)

**Files to create:**
- `frontend/app/statistics/components/CompassTab.tsx`
- `frontend/app/statistics/components/BarnConfigModal.tsx`

**Features:**
- Admin UI in Statistics page
- List users with Compass toggle
- Configure barn mappings (device_id → client_number)
- Test connection button
- Real-time data preview

### 🚧 Phase 3: RAG Integration (PENDING)

**Files to create:**
- `rag/tools/compass_tools.py`

**Features:**
- LLM function: `get_barn_data(client_barn_number, data_type)`
- Integration with RAG pipeline
- Support for queries like "Quelle est la température dans mon poulailler 2?"

### 🚧 Phase 4: Testing & Deployment (PENDING)

**Tasks:**
- Run database migration
- Set COMPASS_API_TOKEN in production
- Integration testing with real Compass API
- Load testing for concurrent requests
- User documentation

## Setup Instructions

### 1. Database Setup

Run the migration in Supabase SQL Editor:

```bash
# Open Supabase Dashboard → SQL Editor
# Copy and run: backend/sql/migrations/create_user_compass_config.sql
```

### 2. Environment Configuration

Create `.env` file or add to existing:

```bash
# Copy example config
cp backend/.env.compass.example backend/.env.compass

# Edit and add your Compass API token
nano backend/.env

# Add:
COMPASS_API_TOKEN=your_compass_api_token_here
```

### 3. Start Backend

```bash
cd backend
uvicorn app.main:app --reload
```

### 4. Test Endpoints

**Health Check (Public):**
```bash
curl http://localhost:8000/api/v1/compass/health
```

**Test Connection (Admin only):**
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_JWT" \
     http://localhost:8000/api/v1/compass/admin/compass/test-connection
```

**List Devices (Admin only):**
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_JWT" \
     http://localhost:8000/api/v1/compass/admin/compass/devices
```

## Usage Example

### Admin: Configure User Barns

```bash
POST /api/v1/compass/admin/users/{user_id}
Authorization: Bearer {admin_jwt}

{
  "compass_enabled": true,
  "barns": [
    {
      "compass_device_id": "849",
      "client_number": "2",
      "name": "Poulailler Est",
      "enabled": true
    },
    {
      "compass_device_id": "850",
      "client_number": "3",
      "name": "Poulailler Ouest",
      "enabled": true
    }
  ]
}
```

### User: Get Barn Data

```bash
GET /api/v1/compass/me/barns/2
Authorization: Bearer {user_jwt}

Response:
{
  "device_id": "849",
  "client_number": "2",
  "name": "Poulailler Est",
  "temperature": 22.5,
  "humidity": 65.0,
  "average_weight": 2450.0,
  "age_days": 35,
  "timestamp": "2025-10-30T14:30:00Z"
}
```

### RAG: Function Calling (Future)

```python
# User asks: "Quelle est la température dans mon poulailler 2 ?"

# LLM detects intent and calls:
get_barn_data(
    user_id="123e4567-e89b-12d3-a456-426614174000",
    client_barn_number="2",
    data_type="temperature"
)

# Backend:
# 1. Gets user config from user_compass_config
# 2. Maps client_number="2" → device_id="849"
# 3. Calls Compass API: get_latest_data(849, "Temperature")
# 4. Returns: {"temperature": 22.5, "unit": "°C"}

# LLM responds: "La température dans votre Poulailler Est (poulailler 2) est de 22.5°C."
```

## Security Considerations

1. **API Token Storage**
   - Store `COMPASS_API_TOKEN` in environment variables
   - Never commit to version control
   - Use secrets manager in production

2. **Access Control**
   - Only admins can configure Compass settings
   - Users can only read their own barn data
   - RLS policies enforce user isolation

3. **Rate Limiting**
   - Consider implementing rate limits for Compass API calls
   - Cache device list (refresh hourly)

4. **Error Handling**
   - Graceful degradation if Compass API is unavailable
   - Clear error messages for users
   - Logging for debugging

## Data Model

### user_compass_config Table

```sql
{
  id: UUID (primary key),
  user_id: UUID (foreign key → auth.users),
  compass_enabled: BOOLEAN,
  barns: JSONB [
    {
      compass_device_id: STRING,  // Compass internal ID
      client_number: STRING,      // User's custom number
      name: STRING,               // Display name
      enabled: BOOLEAN            // Active/inactive
    }
  ],
  created_at: TIMESTAMPTZ,
  updated_at: TIMESTAMPTZ
}
```

### Barn Data Response

```typescript
{
  device_id: string;
  client_number: string;
  name: string;
  temperature?: number;      // Celsius
  humidity?: number;         // Percentage
  average_weight?: number;   // Grams
  age_days?: number;         // Days
  timestamp?: string;        // ISO 8601
}
```

## API Reference

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/users` | List all user Compass configs |
| GET | `/admin/users/{user_id}` | Get user config |
| POST | `/admin/users/{user_id}` | Update user config |
| GET | `/admin/compass/devices` | List Compass devices |
| GET | `/admin/compass/test-connection` | Test API connection |

### User Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/me` | Get my Compass config |
| GET | `/me/barns` | Get all my barns data |
| GET | `/me/barns/{client_number}` | Get specific barn data |

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |

## Troubleshooting

### API Connection Failed

```bash
# Check environment variable
echo $COMPASS_API_TOKEN

# Test connection manually
curl -H "api_authorization: $COMPASS_API_TOKEN" \
     https://compass.intelia.com/api/v1/devices
```

### No Data Returned

1. Check if user has Compass enabled: `compass_enabled = true`
2. Verify barn is enabled: `barn.enabled = true`
3. Check device_id is valid in Compass
4. Review logs for API errors

### RLS Policy Issues

```sql
-- Check if user can access their config
SELECT * FROM user_compass_config WHERE user_id = 'YOUR_USER_ID';

-- Check if admin policies exist
SELECT * FROM pg_policies WHERE tablename = 'user_compass_config';
```

## Next Steps

1. **Complete Frontend**
   - Build CompassTab component
   - Add barn configuration UI
   - Integrate with Statistics page

2. **RAG Integration**
   - Implement `get_barn_data` function
   - Add to LLM function definitions
   - Test with various queries

3. **Testing**
   - Unit tests for CompassAPIService
   - Integration tests with mock API
   - E2E tests with real Compass data

4. **Documentation**
   - User guide for farmers
   - Admin guide for configuration
   - API documentation (OpenAPI/Swagger)

## Support

For issues or questions:
- Backend: Check `backend/app/services/compass_api_service.py`
- API: Check `backend/app/api/v1/compass.py`
- Database: Check `backend/sql/migrations/create_user_compass_config.sql`
- Logs: Check application logs for errors

## References

- Compass API: Internal Intelia documentation
- Source: `C:\Software_Development\broiler-agent\broiler_agent\core\data\api_client.py`
- Analysis: `docs/COMPASS_INTEGRATION_ANALYSIS.md`
