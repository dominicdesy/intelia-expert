# Compass Integration - Analysis & Implementation Plan

**Date**: 2025-10-30
**Status**: Planning Phase
**Priority**: Medium

---

## 🎯 Objective

Enable Intelia Cognito users who also use **Compass** (Intelia's farm management software) to connect their barns so the GPT can answer real-time questions about their farm data.

---

## 📋 Use Case

**Example scenario**:
```
User: "Quelle est la température dans mon poulailler 2 ?"

System flow:
1. LLM detects intent → function call get_barn_data(client_barn_number="2", data_type="temperature")
2. Backend:
   - Gets user_id from session
   - Looks up in user_compass_config: client_number="2" → compass_device_id="849"
   - Calls Compass API: get_latest_data(device_id="849", tag_name="Temperature")
   - Returns: {"temperature": 22.5, "unit": "°C"}
3. LLM responds: "La température actuelle dans votre poulailler 2 est de 22.5°C."
```

---

## 🏗️ Architecture

### Overview
```
┌─────────────────┐
│  Frontend       │
│  Statistics →   │
│  Compass Tab    │
└────────┬────────┘
         │
         ↓ HTTP
┌─────────────────┐         ┌──────────────┐
│  Backend API    │ ←─────→ │ Compass API  │
│  /api/v1/       │ Token   │ (External)   │
│  compass        │         └──────────────┘
└────────┬────────┘
         │
         ↓ SQL
┌─────────────────┐
│  Supabase       │
│  user_compass   │
│  _config        │
└─────────────────┘
```

### Key Design Decisions

1. **Authentication**: Single super admin API token for all Compass access
2. **Configuration**: Admin-managed (not self-service)
3. **Data Fetching**: On-demand API calls (no caching)
4. **UI Location**: New "Compass" tab in Statistics page

---

## 🗄️ Database Schema

### Table: `user_compass_config`

```sql
CREATE TABLE user_compass_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    compass_enabled BOOLEAN DEFAULT false,
    barns JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id)
);

-- Barns JSONB structure:
-- [
--   {
--     "compass_device_id": "849",     -- ID in Compass API (1-99999)
--     "client_number": "2",           -- Farmer's custom number
--     "name": "Poulailler Est",       -- Display name
--     "enabled": true                 -- Active/inactive
--   }
-- ]

-- RLS Policies
ALTER TABLE user_compass_config ENABLE ROW LEVEL SECURITY;

-- Admin full access
CREATE POLICY "Admin full access" ON user_compass_config
    FOR ALL USING (auth.jwt() ->> 'role' = 'admin');

-- Users can view their own config (read-only)
CREATE POLICY "Users view own config" ON user_compass_config
    FOR SELECT USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX idx_user_compass_config_user_id ON user_compass_config(user_id);
CREATE INDEX idx_user_compass_config_enabled ON user_compass_config(compass_enabled) WHERE compass_enabled = true;
```

---

## 🔧 Backend Implementation

### 1. Compass API Service

**File**: `backend/app/services/compass_api_service.py`

```python
"""
Compass API Service - Adapter for Intelia Compass platform
Based on: broiler-agent/broiler_agent/core/data/api_client.py
"""

from typing import Dict, List, Optional
import requests
import os
from dataclasses import dataclass

@dataclass
class CompassBarnData:
    """Real-time barn data from Compass"""
    device_id: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    average_weight: Optional[float] = None  # in grams
    age_days: Optional[int] = None
    production_day: Optional[int] = None
    timestamp: Optional[str] = None

class CompassAPIService:
    """Service to interact with Compass API"""

    def __init__(self):
        self.base_url = "https://compass.intelia.com/api/v1"
        self.api_token = os.getenv("COMPASS_API_TOKEN")
        self.headers = {"api_authorization": self.api_token}

    def get_device_list(self, entity_id: Optional[int] = None) -> List[Dict]:
        """Get list of all devices accessible via API"""
        url = f"{self.base_url}/devices"
        params = {"entity_id": entity_id} if entity_id else None

        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()

        return response.json().get("devices", [])

    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """Get device information including name"""
        url = f"{self.base_url}/devices/{device_id}"

        response = requests.get(url, headers=self.headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        return None

    def get_latest_data(self, device_id: str, tag_name: str) -> Optional[Dict]:
        """Get latest sensor data for specific tag"""
        url = f"{self.base_url}/user/devices/{device_id}/sensors/data/latest"
        params = {"tag_names[]": [tag_name]}

        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        sensor_data = data.get("latest_sensors_data", [])

        return sensor_data[0] if sensor_data else None

    def get_barn_realtime_data(self, device_id: str) -> CompassBarnData:
        """Get comprehensive real-time data for a barn"""
        barn_data = CompassBarnData(device_id=device_id)

        # Temperature
        temp_data = self.get_latest_data(device_id, "Temperature")
        if temp_data:
            barn_data.temperature = float(temp_data.get("latest_value", 0))

        # Humidity
        humidity_data = self.get_latest_data(device_id, "Humidity")
        if humidity_data:
            barn_data.humidity = float(humidity_data.get("latest_value", 0))

        # Weight (in kg, convert to grams)
        weight_data = self.get_latest_data(device_id, "AveragePoultryWeight")
        if weight_data:
            weight_kg = float(weight_data.get("latest_value", 0))
            barn_data.average_weight = weight_kg * 1000

        # Age
        age_data = self.get_latest_data(device_id, "ProductionDay")
        if age_data:
            barn_data.age_days = int(float(age_data.get("latest_value", 0)))

        return barn_data
```

### 2. API Endpoints

**File**: `backend/app/api/v1/compass.py`

```python
"""
Compass Integration API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from supabase import Client

from app.core.database import get_supabase_client
from app.services.compass_api_service import CompassAPIService, CompassBarnData
from app.middleware.auth_middleware import require_admin, get_current_user

router = APIRouter()

# --- Models ---

class BarnConfig(BaseModel):
    compass_device_id: str
    client_number: str
    name: str
    enabled: bool = True

class UserCompassConfig(BaseModel):
    user_id: str
    compass_enabled: bool
    barns: List[BarnConfig]

class UpdateCompassConfigRequest(BaseModel):
    compass_enabled: bool
    barns: List[BarnConfig]

class BarnDataResponse(BaseModel):
    device_id: str
    client_number: str
    name: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    average_weight: Optional[float] = None
    age_days: Optional[int] = None
    timestamp: Optional[str] = None

# --- Admin Endpoints ---

@router.get("/admin/users", dependencies=[Depends(require_admin)])
async def get_all_users_compass_config(
    supabase: Client = Depends(get_supabase_client)
) -> List[UserCompassConfig]:
    """Get Compass configuration for all users (admin only)"""

    # Get all users with their config
    result = supabase.table("user_compass_config") \
        .select("*, auth.users(email)") \
        .execute()

    return result.data

@router.get("/admin/users/{user_id}", dependencies=[Depends(require_admin)])
async def get_user_compass_config(
    user_id: str,
    supabase: Client = Depends(get_supabase_client)
) -> Optional[UserCompassConfig]:
    """Get Compass configuration for specific user (admin only)"""

    result = supabase.table("user_compass_config") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    if result.data:
        return result.data[0]
    return None

@router.post("/admin/users/{user_id}", dependencies=[Depends(require_admin)])
async def update_user_compass_config(
    user_id: str,
    config: UpdateCompassConfigRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """Update Compass configuration for user (admin only)"""

    data = {
        "user_id": user_id,
        "compass_enabled": config.compass_enabled,
        "barns": [barn.dict() for barn in config.barns],
        "updated_at": "now()"
    }

    # Upsert (insert or update)
    result = supabase.table("user_compass_config") \
        .upsert(data) \
        .execute()

    return {"success": True, "data": result.data}

@router.get("/admin/compass/devices", dependencies=[Depends(require_admin)])
async def list_compass_devices() -> List[Dict]:
    """List all devices available in Compass API (admin only)"""

    compass_service = CompassAPIService()
    devices = compass_service.get_device_list()

    return devices

# --- User Endpoints ---

@router.get("/me")
async def get_my_compass_config(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Optional[UserCompassConfig]:
    """Get current user's Compass configuration"""

    result = supabase.table("user_compass_config") \
        .select("*") \
        .eq("user_id", current_user["id"]) \
        .execute()

    if result.data:
        return result.data[0]
    return None

@router.get("/me/barns")
async def get_my_barns_data(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> List[BarnDataResponse]:
    """Get real-time data for current user's barns"""

    # Get user config
    config_result = supabase.table("user_compass_config") \
        .select("*") \
        .eq("user_id", current_user["id"]) \
        .execute()

    if not config_result.data or not config_result.data[0]["compass_enabled"]:
        return []

    config = config_result.data[0]
    barns = config.get("barns", [])

    # Fetch real-time data for each barn
    compass_service = CompassAPIService()
    barn_data_list = []

    for barn in barns:
        if not barn.get("enabled", True):
            continue

        device_id = barn["compass_device_id"]
        data = compass_service.get_barn_realtime_data(device_id)

        barn_data_list.append(BarnDataResponse(
            device_id=device_id,
            client_number=barn["client_number"],
            name=barn["name"],
            temperature=data.temperature,
            humidity=data.humidity,
            average_weight=data.average_weight,
            age_days=data.age_days
        ))

    return barn_data_list

@router.get("/me/barns/{client_number}")
async def get_barn_data_by_client_number(
    client_number: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> BarnDataResponse:
    """Get real-time data for specific barn by client number"""

    # Get user config
    config_result = supabase.table("user_compass_config") \
        .select("*") \
        .eq("user_id", current_user["id"]) \
        .execute()

    if not config_result.data or not config_result.data[0]["compass_enabled"]:
        raise HTTPException(status_code=404, detail="Compass not enabled")

    config = config_result.data[0]
    barns = config.get("barns", [])

    # Find barn by client_number
    barn = next((b for b in barns if b["client_number"] == client_number), None)

    if not barn:
        raise HTTPException(status_code=404, detail=f"Barn {client_number} not found")

    if not barn.get("enabled", True):
        raise HTTPException(status_code=403, detail=f"Barn {client_number} is disabled")

    # Fetch real-time data
    compass_service = CompassAPIService()
    device_id = barn["compass_device_id"]
    data = compass_service.get_barn_realtime_data(device_id)

    return BarnDataResponse(
        device_id=device_id,
        client_number=barn["client_number"],
        name=barn["name"],
        temperature=data.temperature,
        humidity=data.humidity,
        average_weight=data.average_weight,
        age_days=data.age_days
    )
```

---

## 🖥️ Frontend Implementation

### Compass Tab in Statistics Page

**File**: `frontend/app/chat/components/CompassTab.tsx`

```typescript
'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

interface Barn {
  compass_device_id: string;
  client_number: string;
  name: string;
  enabled: boolean;
}

interface UserCompassConfig {
  user_id: string;
  email: string;
  compass_enabled: boolean;
  barns: Barn[];
}

export default function CompassTab() {
  const [users, setUsers] = useState<UserCompassConfig[]>([]);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [availableDevices, setAvailableDevices] = useState<any[]>([]);

  useEffect(() => {
    loadUsers();
    loadAvailableDevices();
  }, []);

  const loadUsers = async () => {
    // Fetch all users from auth.users
    const { data: authUsers, error: authError } = await supabase.auth.admin.listUsers();

    if (authError) {
      console.error('Error loading users:', authError);
      return;
    }

    // Fetch Compass configs
    const { data: configs, error: configError } = await supabase
      .from('user_compass_config')
      .select('*');

    if (configError) {
      console.error('Error loading configs:', configError);
      return;
    }

    // Merge data
    const merged = authUsers.users.map(user => {
      const config = configs?.find(c => c.user_id === user.id);
      return {
        user_id: user.id,
        email: user.email!,
        compass_enabled: config?.compass_enabled || false,
        barns: config?.barns || []
      };
    });

    setUsers(merged);
    setLoading(false);
  };

  const loadAvailableDevices = async () => {
    const response = await fetch('/api/v1/compass/admin/compass/devices', {
      headers: {
        'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`
      }
    });

    if (response.ok) {
      const devices = await response.json();
      setAvailableDevices(devices);
    }
  };

  const toggleCompass = async (userId: string, enabled: boolean) => {
    const user = users.find(u => u.user_id === userId);
    if (!user) return;

    const response = await fetch(`/api/v1/compass/admin/users/${userId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`
      },
      body: JSON.stringify({
        compass_enabled: enabled,
        barns: user.barns
      })
    });

    if (response.ok) {
      loadUsers();
    }
  };

  const addBarn = async (userId: string, barn: Barn) => {
    const user = users.find(u => u.user_id === userId);
    if (!user) return;

    const updatedBarns = [...user.barns, barn];

    const response = await fetch(`/api/v1/compass/admin/users/${userId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`
      },
      body: JSON.stringify({
        compass_enabled: user.compass_enabled,
        barns: updatedBarns
      })
    });

    if (response.ok) {
      loadUsers();
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Compass Integration</h2>

      <div className="bg-white rounded-lg shadow">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left">User</th>
              <th className="px-6 py-3 text-left">Compass Enabled</th>
              <th className="px-6 py-3 text-left">Barns</th>
              <th className="px-6 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {users.map(user => (
              <tr key={user.user_id}>
                <td className="px-6 py-4">{user.email}</td>
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={user.compass_enabled}
                    onChange={(e) => toggleCompass(user.user_id, e.target.checked)}
                    className="w-4 h-4"
                  />
                </td>
                <td className="px-6 py-4">
                  {user.barns.length} barn(s)
                </td>
                <td className="px-6 py-4">
                  <button
                    onClick={() => setSelectedUser(user.user_id)}
                    className="text-blue-600 hover:underline"
                  >
                    Configure
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Barn configuration modal would go here */}
    </div>
  );
}
```

---

## 🤖 RAG Integration - Function Calling

### LLM Function Definition

```python
{
  "name": "get_barn_data",
  "description": "Get real-time data from user's barn via Compass. Use when user asks about current conditions in their barn (temperature, weight, age, etc.).",
  "parameters": {
    "type": "object",
    "properties": {
      "client_barn_number": {
        "type": "string",
        "description": "The barn number as referred to by the user (e.g., '2', '3', 'barn 1')"
      },
      "data_type": {
        "type": "string",
        "enum": ["temperature", "humidity", "weight", "age", "all"],
        "description": "Type of data requested"
      }
    },
    "required": ["client_barn_number", "data_type"]
  }
}
```

### Function Implementation

**File**: `rag/tools/compass_tools.py`

```python
"""
Compass integration tools for RAG system
"""

import requests
from typing import Dict, Optional

def get_barn_data(
    user_id: str,
    client_barn_number: str,
    data_type: str,
    backend_url: str = "http://localhost:8000"
) -> Dict:
    """
    Get real-time barn data from Compass

    Args:
        user_id: Current user's ID
        client_barn_number: Barn number (user's custom number)
        data_type: Type of data (temperature, humidity, weight, age, all)
        backend_url: Backend API URL

    Returns:
        Dict with barn data
    """

    # Call backend API
    url = f"{backend_url}/api/v1/compass/me/barns/{client_barn_number}"

    try:
        response = requests.get(url, headers={
            "Authorization": f"Bearer {get_user_token(user_id)}"
        })

        if response.status_code == 404:
            return {
                "error": f"Barn {client_barn_number} not found or Compass not enabled"
            }

        response.raise_for_status()
        data = response.json()

        # Format response based on data_type
        if data_type == "all":
            return data

        elif data_type == "temperature":
            return {
                "barn": data["name"],
                "temperature": data["temperature"],
                "unit": "°C"
            }

        elif data_type == "humidity":
            return {
                "barn": data["name"],
                "humidity": data["humidity"],
                "unit": "%"
            }

        elif data_type == "weight":
            return {
                "barn": data["name"],
                "average_weight": data["average_weight"],
                "unit": "grams"
            }

        elif data_type == "age":
            return {
                "barn": data["name"],
                "age_days": data["age_days"],
                "unit": "days"
            }

        return data

    except Exception as e:
        return {"error": str(e)}
```

---

## 🔐 Security Considerations

1. **API Token Storage**:
   - Store COMPASS_API_TOKEN in environment variables
   - Never expose in frontend or logs

2. **Access Control**:
   - Only admins can configure Compass settings
   - Users can only read their own barn data
   - RLS policies enforce user isolation

3. **Rate Limiting**:
   - Consider implementing rate limits for Compass API calls
   - Cache device list (refreshed hourly)

4. **Error Handling**:
   - Graceful degradation if Compass API is unavailable
   - Clear error messages for users

---

## 📊 Data Flow

### Admin Configuration Flow
```
Admin UI → POST /api/v1/compass/admin/users/{id}
         → Supabase: user_compass_config (upsert)
         → Success response
```

### User Query Flow
```
User: "Température poulailler 2?"
  ↓
LLM: function_call(get_barn_data, client_barn_number="2", data_type="temperature")
  ↓
RAG: calls backend GET /api/v1/compass/me/barns/2
  ↓
Backend:
  - Gets user_id from JWT
  - Looks up client_number="2" → device_id="849"
  - Calls Compass API: get_latest_data(849, "Temperature")
  ↓
Response: {"barn": "Poulailler Est", "temperature": 22.5, "unit": "°C"}
  ↓
LLM: "La température dans votre Poulailler Est (poulailler 2) est de 22.5°C."
```

---

## 🚀 Implementation Steps

### Phase 1: Backend Foundation
1. ✅ Create database migration for `user_compass_config`
2. ✅ Implement `CompassAPIService` (adapt from broiler-agent)
3. ✅ Create `/api/v1/compass` endpoints
4. ✅ Add COMPASS_API_TOKEN to environment

### Phase 2: Frontend Admin UI
1. ✅ Create `CompassTab.tsx` component
2. ✅ Integrate into Statistics page
3. ✅ Admin list of users with Compass toggle
4. ✅ Barn configuration UI (add/edit/remove)
5. ✅ Test connection button

### Phase 3: RAG Integration
1. ✅ Add `get_barn_data` function to LLM tools
2. ✅ Implement function handler in RAG
3. ✅ Test with various queries
4. ✅ Handle edge cases (barn not found, Compass disabled, etc.)

### Phase 4: Testing & Deployment
1. ✅ Integration testing with real Compass API
2. ✅ Load testing for concurrent requests
3. ✅ Documentation for admin users
4. ✅ Production deployment

---

## ⚠️ Known Limitations

1. **No historical data**: Only real-time/latest values (can be extended)
2. **No alerts**: System is query-based, not proactive
3. **Single token**: All users share same API access (consider per-user tokens later)
4. **No caching**: Every query hits Compass API (consider adding cache layer)

---

## 🔮 Future Enhancements

### Phase 2 Features
1. **Alerts & Notifications**: Proactive alerts when values exceed thresholds
2. **Historical Charts**: Graph temperature/weight trends
3. **Predictive Analytics**: Use Compass predictions in responses
4. **Multi-device Aggregation**: "What's the average temperature across all my barns?"
5. **Custom Dashboards**: Embedded Compass widgets in Cognito UI

---

## 📚 References

- **Compass API Docs**: Internal Intelia documentation
- **Source Code**: `C:\Software_Development\broiler-agent\broiler_agent\core\data\`
  - `api_client.py` - Full API implementation
  - `barn_list_parser.py` - Barn configuration management
- **Related**: HybridOODDetector integration (2025-10-30)

---

## 📝 Notes

- This integration requires COMPASS_API_TOKEN with super admin privileges
- Configuration is admin-only (not self-service for users)
- Data fetching is on-demand (no pre-caching or background sync)
- Current focus is on real-time sensor data (temperature, humidity, weight, age)

---

**Last Updated**: 2025-10-30
**Next Steps**: Debug Nano question issue, then resume implementation
