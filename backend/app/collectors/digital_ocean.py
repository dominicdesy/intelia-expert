"""
Digital Ocean Metrics Collector
Collects costs and usage data from Digital Ocean API
"""

import logging
import os
from datetime import datetime
from typing import Dict, Optional
import httpx

logger = logging.getLogger(__name__)

DO_API_TOKEN = os.getenv("DO_API_TOKEN", "")
DO_API_BASE = "https://api.digitalocean.com/v2"


async def collect_do_metrics() -> Optional[Dict]:
    """
    Collect Digital Ocean infrastructure metrics
    Returns dict with costs and usage data
    """
    if not DO_API_TOKEN:
        logger.warning("DO_API_TOKEN not configured, skipping Digital Ocean metrics")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {DO_API_TOKEN}",
            "Content-Type": "application/json"
        }

        metrics = {
            "recorded_at": datetime.utcnow(),
            "app_platform_cost_usd": 0.0,
            "app_platform_apps": 0,
            "db_cost_usd": 0.0,
            "db_size_gb": 0.0,
            "registry_cost_usd": 0.0,
            "registry_size_gb": 0.0,
            "registry_bandwidth_gb": 0.0,
            "spaces_cost_usd": 0.0,
            "spaces_size_gb": 0.0,
            "total_cost_usd": 0.0
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get billing information
            billing_data = await _get_billing_history(client, headers)
            if billing_data:
                metrics.update(billing_data)

            # Get App Platform info
            app_data = await _get_app_platform_metrics(client, headers)
            if app_data:
                metrics.update(app_data)

            # Get Database info
            db_data = await _get_database_metrics(client, headers)
            if db_data:
                metrics.update(db_data)

            # Get Container Registry info
            registry_data = await _get_registry_metrics(client, headers)
            if registry_data:
                metrics.update(registry_data)

            # Get Spaces info
            spaces_data = await _get_spaces_metrics(client, headers)
            if spaces_data:
                metrics.update(spaces_data)

        # Calculate total cost
        metrics["total_cost_usd"] = (
            metrics["app_platform_cost_usd"] +
            metrics["db_cost_usd"] +
            metrics["registry_cost_usd"] +
            metrics["spaces_cost_usd"]
        )

        logger.info(f"✅ Collected Digital Ocean metrics: ${metrics['total_cost_usd']:.2f} total")
        return metrics

    except Exception as e:
        logger.error(f"❌ Failed to collect Digital Ocean metrics: {e}", exc_info=True)
        return None


async def _get_billing_history(client: httpx.AsyncClient, headers: Dict) -> Optional[Dict]:
    """Get current month billing data"""
    try:
        response = await client.get(
            f"{DO_API_BASE}/customers/my/billing_history",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        # Get most recent invoice
        if data.get("billing_history") and len(data["billing_history"]) > 0:
            latest = data["billing_history"][0]
            return {
                "total_cost_usd": float(latest.get("amount", 0.0))
            }

        return None

    except Exception as e:
        logger.debug(f"Failed to get billing history: {e}")
        return None


async def _get_app_platform_metrics(client: httpx.AsyncClient, headers: Dict) -> Optional[Dict]:
    """Get App Platform metrics"""
    try:
        response = await client.get(
            f"{DO_API_BASE}/apps",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        apps = data.get("apps", [])
        app_count = len(apps)

        # Estimate cost based on tier (rough estimation)
        # Basic: $5/month, Professional: $12/month, etc.
        estimated_cost = 0.0
        for app in apps:
            tier = app.get("tier_slug", "basic")
            if tier == "basic":
                estimated_cost += 5.0
            elif tier == "professional":
                estimated_cost += 12.0
            elif tier == "starter":
                estimated_cost += 0.0  # Free tier

        return {
            "app_platform_apps": app_count,
            "app_platform_cost_usd": estimated_cost
        }

    except Exception as e:
        logger.debug(f"Failed to get app platform metrics: {e}")
        return None


async def _get_database_metrics(client: httpx.AsyncClient, headers: Dict) -> Optional[Dict]:
    """Get managed database metrics"""
    try:
        response = await client.get(
            f"{DO_API_BASE}/databases",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        databases = data.get("databases", [])
        total_cost = 0.0
        total_size_gb = 0.0

        for db in databases:
            # Get DB size
            size_slug = db.get("size", "")
            # Parse size and estimate cost
            # db-s-1vcpu-1gb: $15/month
            # db-s-2vcpu-4gb: $60/month
            # etc.
            if "1vcpu-1gb" in size_slug:
                total_cost += 15.0
            elif "2vcpu-4gb" in size_slug:
                total_cost += 60.0
            elif "4vcpu-8gb" in size_slug:
                total_cost += 120.0

            # Estimate size
            if "1gb" in size_slug:
                total_size_gb += 10.0  # 10GB disk
            elif "4gb" in size_slug:
                total_size_gb += 25.0  # 25GB disk
            elif "8gb" in size_slug:
                total_size_gb += 38.0  # 38GB disk

        return {
            "db_cost_usd": total_cost,
            "db_size_gb": total_size_gb
        }

    except Exception as e:
        logger.debug(f"Failed to get database metrics: {e}")
        return None


async def _get_registry_metrics(client: httpx.AsyncClient, headers: Dict) -> Optional[Dict]:
    """Get container registry metrics"""
    try:
        response = await client.get(
            f"{DO_API_BASE}/registry",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        registry = data.get("registry", {})
        storage_bytes = registry.get("storage_usage_bytes", 0)
        storage_gb = storage_bytes / (1024 ** 3)

        # DO Container Registry pricing:
        # $5/month base + $0.02/GB over 500GB
        base_cost = 5.0
        overage_cost = 0.0
        if storage_gb > 500:
            overage_cost = (storage_gb - 500) * 0.02

        return {
            "registry_cost_usd": base_cost + overage_cost,
            "registry_size_gb": storage_gb,
            "registry_bandwidth_gb": 0.0  # Not easily available via API
        }

    except Exception as e:
        logger.debug(f"Failed to get registry metrics: {e}")
        return None


async def _get_spaces_metrics(client: httpx.AsyncClient, headers: Dict) -> Optional[Dict]:
    """Get Spaces (S3-compatible) metrics"""
    try:
        # Spaces pricing: $5/month for 250GB + $0.02/GB overage
        # Note: Detailed usage requires S3 API, not REST API
        # For now, return estimated baseline
        return {
            "spaces_cost_usd": 5.0,  # Baseline estimate
            "spaces_size_gb": 0.0    # Would need S3 API
        }

    except Exception as e:
        logger.debug(f"Failed to get spaces metrics: {e}")
        return None
