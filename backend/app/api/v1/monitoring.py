"""
Monitoring API
Version: 1.0.0
Last modified: 2025-10-28

Endpoints for system monitoring and health checks
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os
import psutil
import asyncio
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# ============================================================================
# SCHEMAS
# ============================================================================

class SystemMetrics(BaseModel):
    """System resource metrics"""
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    memory_used_gb: float = Field(..., description="Memory used in GB")
    memory_total_gb: float = Field(..., description="Total memory in GB")
    disk_percent: float = Field(..., description="Disk usage percentage")
    disk_used_gb: float = Field(..., description="Disk used in GB")
    disk_total_gb: float = Field(..., description="Total disk in GB")


class ServiceStatus(BaseModel):
    """Service health status"""
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Status: healthy, unhealthy, unknown")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional service details")


class MonitoringSummary(BaseModel):
    """Overall monitoring summary"""
    timestamp: str = Field(..., description="Current timestamp")
    system: SystemMetrics = Field(..., description="System metrics")
    services: List[ServiceStatus] = Field(..., description="Service statuses")
    overall_status: str = Field(..., description="Overall system status: healthy, degraded, unhealthy")


class LogEntry(BaseModel):
    """Application log entry"""
    timestamp: str = Field(..., description="Log timestamp")
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    source: Optional[str] = Field(None, description="Log source/module")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_system_metrics() -> SystemMetrics:
    """Collect system resource metrics"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024 ** 3)
        memory_total_gb = memory.total / (1024 ** 3)

        # Disk usage
        disk = psutil.disk_usage('/')
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)

        return SystemMetrics(
            cpu_percent=round(cpu_percent, 2),
            memory_percent=round(memory.percent, 2),
            memory_used_gb=round(memory_used_gb, 2),
            memory_total_gb=round(memory_total_gb, 2),
            disk_percent=round(disk.percent, 2),
            disk_used_gb=round(disk_used_gb, 2),
            disk_total_gb=round(disk_total_gb, 2)
        )
    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}")
        # Return default metrics on error
        return SystemMetrics(
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_gb=0.0,
            memory_total_gb=0.0,
            disk_percent=0.0,
            disk_used_gb=0.0,
            disk_total_gb=0.0
        )


async def check_database_health() -> ServiceStatus:
    """Check PostgreSQL database health"""
    start_time = datetime.utcnow()

    try:
        from app.core.database import get_pg_connection

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return ServiceStatus(
            name="PostgreSQL",
            status="healthy",
            response_time_ms=round(response_time, 2)
        )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(f"PostgreSQL health check failed: {e}")
        return ServiceStatus(
            name="PostgreSQL",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            error=str(e)
        )


async def check_supabase_health() -> ServiceStatus:
    """Check Supabase health"""
    start_time = datetime.utcnow()

    try:
        from app.core.database import get_supabase_client

        supabase = get_supabase_client()
        # Simple query to test connection
        supabase.table("users").select("id").limit(1).execute()

        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return ServiceStatus(
            name="Supabase",
            status="healthy",
            response_time_ms=round(response_time, 2)
        )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(f"Supabase health check failed: {e}")
        return ServiceStatus(
            name="Supabase",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            error=str(e)
        )


async def check_llm_service_health() -> ServiceStatus:
    """Check LLM service health"""
    start_time = datetime.utcnow()

    # Use internal Kubernetes URL if available, fallback to localhost
    llm_service_url = os.getenv("LLM_SERVICE_INTERNAL_URL") or os.getenv("LLM_SERVICE_URL", "http://localhost:8081")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{llm_service_url}/health")
            response.raise_for_status()

        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return ServiceStatus(
            name="LLM Service",
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={"url": llm_service_url}
        )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(f"LLM service health check failed: {e}")
        return ServiceStatus(
            name="LLM Service",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            error=str(e),
            details={"url": llm_service_url}
        )


async def check_ai_service_health() -> ServiceStatus:
    """Check AI service health"""
    start_time = datetime.utcnow()

    # Use internal Kubernetes URL if available, fallback to localhost
    ai_service_url = os.getenv("AI_SERVICE_INTERNAL_URL") or os.getenv("AI_SERVICE_URL", "http://localhost:8000")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ai_service_url}/health")
            response.raise_for_status()

        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return ServiceStatus(
            name="AI Service",
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={"url": ai_service_url}
        )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(f"AI service health check failed: {e}")
        return ServiceStatus(
            name="AI Service",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            error=str(e),
            details={"url": ai_service_url}
        )


def determine_overall_status(services: List[ServiceStatus]) -> str:
    """Determine overall system status based on service statuses"""
    unhealthy_count = sum(1 for s in services if s.status == "unhealthy")

    if unhealthy_count == 0:
        return "healthy"
    elif unhealthy_count >= len(services) / 2:
        return "unhealthy"
    else:
        return "degraded"


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/summary", response_model=MonitoringSummary)
async def get_monitoring_summary():
    """
    Get comprehensive monitoring summary including system metrics and service health.

    Returns:
        MonitoringSummary: Complete monitoring overview
    """
    try:
        # Collect system metrics
        system_metrics = get_system_metrics()

        # Check all services concurrently
        services = await asyncio.gather(
            check_database_health(),
            check_supabase_health(),
            check_llm_service_health(),
            check_ai_service_health(),
            return_exceptions=True
        )

        # Filter out exceptions and convert to ServiceStatus list
        valid_services = []
        for i, service in enumerate(services):
            if isinstance(service, ServiceStatus):
                valid_services.append(service)
            else:
                # If service check raised exception, create error status
                service_names = ["PostgreSQL", "Supabase", "LLM Service", "AI Service"]
                valid_services.append(ServiceStatus(
                    name=service_names[i],
                    status="unhealthy",
                    error=str(service) if isinstance(service, Exception) else "Unknown error"
                ))

        # Determine overall status
        overall_status = determine_overall_status(valid_services)

        return MonitoringSummary(
            timestamp=datetime.utcnow().isoformat(),
            system=system_metrics,
            services=valid_services,
            overall_status=overall_status
        )
    except Exception as e:
        logger.error(f"Error generating monitoring summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate monitoring summary: {str(e)}")


@router.get("/services", response_model=List[ServiceStatus])
async def get_services_status():
    """
    Get health status of all services.

    Returns:
        List[ServiceStatus]: List of service health statuses
    """
    try:
        # Check all services concurrently
        services = await asyncio.gather(
            check_database_health(),
            check_supabase_health(),
            check_llm_service_health(),
            check_ai_service_health(),
            return_exceptions=True
        )

        # Filter out exceptions and convert to ServiceStatus list
        valid_services = []
        for i, service in enumerate(services):
            if isinstance(service, ServiceStatus):
                valid_services.append(service)
            else:
                # If service check raised exception, create error status
                service_names = ["PostgreSQL", "Supabase", "LLM Service", "AI Service"]
                valid_services.append(ServiceStatus(
                    name=service_names[i],
                    status="unhealthy",
                    error=str(service) if isinstance(service, Exception) else "Unknown error"
                ))

        return valid_services
    except Exception as e:
        logger.error(f"Error checking services: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check services: {str(e)}")


@router.get("/logs", response_model=List[LogEntry])
async def get_application_logs(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of logs to return"),
    level: Optional[str] = Query(None, description="Filter by log level (INFO, WARNING, ERROR, etc.)")
):
    """
    Get recent application logs.

    Args:
        limit: Maximum number of logs to return (1-1000)
        level: Optional log level filter

    Returns:
        List[LogEntry]: List of log entries
    """
    try:
        # For now, return mock logs
        # TODO: Implement actual log retrieval from log files or logging system

        mock_logs = [
            LogEntry(
                timestamp=datetime.utcnow().isoformat(),
                level="INFO",
                message="Monitoring endpoint accessed",
                source="monitoring.api"
            ),
            LogEntry(
                timestamp=datetime.utcnow().isoformat(),
                level="INFO",
                message="System health check completed",
                source="monitoring.health"
            )
        ]

        # Filter by level if provided
        if level:
            mock_logs = [log for log in mock_logs if log.level.upper() == level.upper()]

        return mock_logs[:limit]
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")


@router.get("/system", response_model=SystemMetrics)
async def get_system_metrics_endpoint():
    """
    Get current system resource metrics.

    Returns:
        SystemMetrics: System resource usage metrics
    """
    try:
        return get_system_metrics()
    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect system metrics: {str(e)}")
