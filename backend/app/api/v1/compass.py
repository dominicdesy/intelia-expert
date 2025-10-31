"""
Compass Integration API endpoints
Version: 1.0.0
Date: 2025-10-30
Description: API endpoints for Compass barn management integration
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

# Import authentication
from .auth import get_current_user
from app.core.database import get_pg_connection, get_user_from_supabase
from app.services.compass_api_service import get_compass_service, CompassBarnData
from psycopg2.extras import RealDictCursor
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/compass", tags=["Compass"])


# ==================== MODELS ====================

class BarnConfig(BaseModel):
    """Barn configuration for a user"""
    compass_device_id: str = Field(..., description="Device ID in Compass (e.g., '849')")
    client_number: str = Field(..., description="User's custom barn number (e.g., '2')")
    name: str = Field(..., description="Display name for the barn (e.g., 'Poulailler Est')")
    enabled: bool = Field(default=True, description="Whether this barn is active")

    class Config:
        json_schema_extra = {
            "example": {
                "compass_device_id": "849",
                "client_number": "2",
                "name": "Poulailler Est",
                "enabled": True
            }
        }


class UserCompassConfig(BaseModel):
    """User Compass configuration"""
    user_id: str
    compass_enabled: bool
    barns: List[BarnConfig]

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "compass_enabled": True,
                "barns": [
                    {
                        "compass_device_id": "849",
                        "client_number": "2",
                        "name": "Poulailler Est",
                        "enabled": True
                    }
                ]
            }
        }


class UpdateCompassConfigRequest(BaseModel):
    """Request to update user Compass configuration"""
    compass_enabled: bool
    barns: List[BarnConfig]


class BarnDataResponse(BaseModel):
    """Real-time barn data response"""
    device_id: str
    client_number: str
    name: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    average_weight: Optional[float] = None  # in grams
    age_days: Optional[int] = None
    timestamp: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "849",
                "client_number": "2",
                "name": "Poulailler Est",
                "temperature": 22.5,
                "humidity": 65.0,
                "average_weight": 2450.0,
                "age_days": 35,
                "timestamp": "2025-10-30T14:30:00Z"
            }
        }


# ==================== HELPER FUNCTIONS ====================

def require_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Dependency to require admin privileges"""
    user_role = current_user.get("role", "user")
    is_admin = user_role in ["admin", "superuser"] or current_user.get("is_admin", False)

    if not is_admin:
        logger.warning(f"Access denied for non-admin user: {current_user.get('email')}")
        raise HTTPException(
            status_code=403,
            detail="Access denied - admin privileges required"
        )

    return current_user


async def get_user_config(user_id: str) -> Optional[Dict]:
    """Get user's Compass configuration from database"""
    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, user_id, compass_enabled, barns, created_at, updated_at
                    FROM user_compass_config
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )
                result = cur.fetchone()

                if result:
                    # Convert to dict and ensure proper JSON handling
                    return dict(result)
                return None
    except Exception as e:
        logger.error(f"Error fetching user config: {e}")
        return None


# ==================== ADMIN ENDPOINTS ====================

@router.get("/admin/users", dependencies=[Depends(require_admin)])
async def get_all_users_compass_config() -> List[Dict]:
    """
    Get Compass configuration for all users (admin only)

    Returns:
        List of user configurations with email and settings
    """
    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get all configs from PostgreSQL
                cur.execute(
                    """
                    SELECT
                        id,
                        user_id,
                        compass_enabled,
                        barns,
                        created_at,
                        updated_at
                    FROM user_compass_config
                    ORDER BY created_at DESC
                    """
                )
                results = cur.fetchall()

                # Convert to list of dicts and enrich with user emails from Supabase
                configs = []
                for row in results:
                    config = dict(row)
                    user_id = config["user_id"]

                    # Get user email from Supabase
                    user_info = get_user_from_supabase(user_id)
                    config["email"] = user_info.get("email", "unknown") if user_info else "unknown"

                    configs.append(config)

                logger.info(f"Retrieved {len(configs)} user Compass configurations")
                return configs

    except Exception as e:
        logger.error(f"Error fetching all user configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/users/{user_id}", dependencies=[Depends(require_admin)])
async def get_user_compass_config_admin(user_id: str) -> Optional[UserCompassConfig]:
    """
    Get Compass configuration for specific user (admin only)

    Args:
        user_id: User ID (UUID)

    Returns:
        User configuration or None
    """
    config = await get_user_config(user_id)

    if not config:
        logger.info(f"No Compass config found for user {user_id}")
        return None

    return UserCompassConfig(**config)


@router.post("/admin/users/{user_id}", dependencies=[Depends(require_admin)])
async def update_user_compass_config(
    user_id: str,
    config: UpdateCompassConfigRequest
) -> Dict[str, Any]:
    """
    Update Compass configuration for user (admin only)

    Args:
        user_id: User ID (UUID)
        config: Configuration to update

    Returns:
        Success response with updated data
    """
    try:
        # Convert barns to dict format
        barns_data = [barn.dict() for barn in config.barns]
        barns_json = json.dumps(barns_data)

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Upsert (insert or update) using ON CONFLICT
                cur.execute(
                    """
                    INSERT INTO user_compass_config (user_id, compass_enabled, barns, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        compass_enabled = EXCLUDED.compass_enabled,
                        barns = EXCLUDED.barns,
                        updated_at = NOW()
                    RETURNING id, user_id, compass_enabled, barns, created_at, updated_at
                    """,
                    (user_id, config.compass_enabled, barns_json)
                )
                result = cur.fetchone()
                conn.commit()

                logger.info(f"Updated Compass config for user {user_id}: {len(barns_data)} barns, "
                           f"enabled={config.compass_enabled}")

                return {
                    "success": True,
                    "data": dict(result) if result else None
                }

    except Exception as e:
        logger.error(f"Error updating user config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/compass/devices", dependencies=[Depends(require_admin)])
async def list_compass_devices() -> List[Dict]:
    """
    List all devices available in Compass API (admin only)

    Returns:
        List of devices with their IDs and names
    """
    try:
        compass_service = get_compass_service()
        devices = compass_service.get_device_list()

        logger.info(f"Retrieved {len(devices)} devices from Compass")
        return devices

    except Exception as e:
        logger.error(f"Error listing Compass devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/compass/test-connection", dependencies=[Depends(require_admin)])
async def test_compass_connection() -> Dict[str, Any]:
    """
    Test Compass API connection (admin only)

    Returns:
        Connection status and details
    """
    try:
        compass_service = get_compass_service()
        is_connected = compass_service.test_connection()

        return {
            "connected": is_connected,
            "base_url": compass_service.base_url,
            "has_token": bool(compass_service.api_token),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error testing Compass connection: {e}")
        return {
            "connected": False,
            "error": str(e)
        }


@router.get("/admin/available-users", dependencies=[Depends(require_admin)])
async def get_available_users() -> List[Dict]:
    """
    Get list of all users available for Compass configuration (admin only)

    Returns:
        List of users with their IDs, emails, and Compass config status
    """
    try:
        # Get all users from Supabase
        from app.core.database import get_supabase_client
        supabase = get_supabase_client()

        users_response = supabase.table("users").select("auth_user_id, email, full_name").execute()

        if not users_response.data:
            return []

        # Get existing Compass configs from PostgreSQL
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT user_id, compass_enabled
                    FROM user_compass_config
                    """
                )
                configs = cur.fetchall()

                # Create a map of user_id -> has_config
                config_map = {
                    str(config["user_id"]): config["compass_enabled"]
                    for config in configs
                }

        # Build response with config status
        available_users = []
        for user in users_response.data:
            user_id = user.get("auth_user_id")
            if not user_id:
                continue

            available_users.append({
                "user_id": user_id,
                "email": user.get("email", ""),
                "full_name": user.get("full_name"),
                "has_compass_config": user_id in config_map,
                "compass_enabled": config_map.get(user_id, False)
            })

        # Sort: users without config first, then by email
        available_users.sort(key=lambda u: (u["has_compass_config"], u["email"].lower()))

        logger.info(f"Retrieved {len(available_users)} available users for Compass configuration")
        return available_users

    except Exception as e:
        logger.error(f"Error fetching available users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== USER ENDPOINTS ====================

@router.get("/me")
async def get_my_compass_config(
    current_user: Dict = Depends(get_current_user)
) -> Optional[UserCompassConfig]:
    """
    Get current user's Compass configuration

    Returns:
        User configuration or None if not configured
    """
    user_id = current_user["id"]
    config = await get_user_config(user_id)

    if not config:
        logger.debug(f"No Compass config for user {user_id}")
        return None

    return UserCompassConfig(**config)


@router.get("/me/barns")
async def get_my_barns_data(
    current_user: Dict = Depends(get_current_user)
) -> List[BarnDataResponse]:
    """
    Get real-time data for current user's barns

    Returns:
        List of barn data with sensor readings
    """
    user_id = current_user["id"]
    config = await get_user_config(user_id)

    if not config or not config.get("compass_enabled", False):
        logger.info(f"Compass not enabled for user {user_id}")
        return []

    barns = config.get("barns", [])
    compass_service = get_compass_service()
    barn_data_list = []

    for barn in barns:
        if not barn.get("enabled", True):
            continue

        try:
            device_id = barn["compass_device_id"]
            data = compass_service.get_barn_realtime_data(device_id)

            barn_data_list.append(BarnDataResponse(
                device_id=device_id,
                client_number=barn["client_number"],
                name=barn["name"],
                temperature=data.temperature,
                humidity=data.humidity,
                average_weight=data.average_weight,
                age_days=data.age_days,
                timestamp=data.timestamp
            ))

        except Exception as e:
            logger.error(f"Error fetching data for device {device_id}: {e}")
            # Continue with next barn even if one fails

    logger.info(f"Retrieved data for {len(barn_data_list)} barns for user {user_id}")
    return barn_data_list


@router.get("/internal/user/{user_id}/barns/{client_number}")
async def get_barn_data_internal(
    user_id: str,
    client_number: str
) -> BarnDataResponse:
    """
    Get real-time data for specific barn by client number (internal service-to-service call)

    This endpoint is for internal use by RAG engine - no JWT authentication required.

    Args:
        user_id: User ID (tenant_id from RAG)
        client_number: User's custom barn number (e.g., "2")

    Returns:
        Barn data with sensor readings

    Raises:
        HTTPException: If barn not found or Compass not enabled
    """
    config = await get_user_config(user_id)

    if not config or not config.get("compass_enabled", False):
        raise HTTPException(
            status_code=404,
            detail="Compass not enabled for this user"
        )

    barns = config.get("barns", [])

    # Find barn by client_number
    barn = next((b for b in barns if b["client_number"] == client_number), None)

    if not barn:
        raise HTTPException(
            status_code=404,
            detail=f"Barn '{client_number}' not found in user configuration"
        )

    if not barn.get("enabled", True):
        raise HTTPException(
            status_code=403,
            detail=f"Barn '{client_number}' is disabled"
        )

    # Fetch real-time data
    try:
        compass_service = get_compass_service()
        device_id = barn["compass_device_id"]
        data = compass_service.get_barn_realtime_data(device_id)

        logger.info(f"[INTERNAL] Retrieved barn data for user {user_id}, barn {client_number}")

        return BarnDataResponse(
            device_id=device_id,
            client_number=barn["client_number"],
            name=barn["name"],
            temperature=data.temperature,
            humidity=data.humidity,
            average_weight=data.average_weight,
            age_days=data.age_days,
            timestamp=data.timestamp
        )

    except Exception as e:
        logger.error(f"Error fetching barn data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me/barns/{client_number}")
async def get_barn_data_by_client_number(
    client_number: str,
    current_user: Dict = Depends(get_current_user)
) -> BarnDataResponse:
    """
    Get real-time data for specific barn by client number

    Args:
        client_number: User's custom barn number (e.g., "2")

    Returns:
        Barn data with sensor readings

    Raises:
        HTTPException: If barn not found or Compass not enabled
    """
    user_id = current_user["id"]
    config = await get_user_config(user_id)

    if not config or not config.get("compass_enabled", False):
        raise HTTPException(
            status_code=404,
            detail="Compass not enabled for this user"
        )

    barns = config.get("barns", [])

    # Find barn by client_number
    barn = next((b for b in barns if b["client_number"] == client_number), None)

    if not barn:
        raise HTTPException(
            status_code=404,
            detail=f"Barn '{client_number}' not found in user configuration"
        )

    if not barn.get("enabled", True):
        raise HTTPException(
            status_code=403,
            detail=f"Barn '{client_number}' is disabled"
        )

    # Fetch real-time data
    try:
        compass_service = get_compass_service()
        device_id = barn["compass_device_id"]
        data = compass_service.get_barn_realtime_data(device_id)

        logger.info(f"Retrieved barn data for user {user_id}, barn {client_number}")

        return BarnDataResponse(
            device_id=device_id,
            client_number=barn["client_number"],
            name=barn["name"],
            temperature=data.temperature,
            humidity=data.humidity,
            average_weight=data.average_weight,
            age_days=data.age_days,
            timestamp=data.timestamp
        )

    except Exception as e:
        logger.error(f"Error fetching barn data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def compass_health() -> Dict[str, Any]:
    """
    Check Compass integration health (public endpoint)

    Returns:
        Health status and configuration info
    """
    try:
        compass_service = get_compass_service()

        return {
            "status": "healthy",
            "service": "compass",
            "base_url": compass_service.base_url,
            "configured": bool(compass_service.api_token),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
