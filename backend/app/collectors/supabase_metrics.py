"""
Supabase Metrics Collector
Collects auth, storage, and database usage from Supabase
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from app.core.database import get_supabase_admin_client

logger = logging.getLogger(__name__)


async def collect_supabase_metrics() -> Optional[Dict]:
    """
    Collect Supabase metrics (auth, storage, database)
    Returns dict with user counts, storage size, costs
    """
    try:
        supabase = get_supabase_admin_client()

        metrics = {
            "recorded_at": datetime.utcnow(),
            "total_users": 0,
            "active_users_7d": 0,
            "active_users_30d": 0,
            "storage_size_gb": 0.0,
            "storage_objects": 0,
            "db_size_mb": 0.0,
            "total_cost_usd": 0.0
        }

        # Get total users count
        users_response = supabase.auth.admin.list_users()
        if hasattr(users_response, 'users'):
            metrics["total_users"] = len(users_response.users)

            # Count active users in last 7 and 30 days
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            for user in users_response.users:
                last_sign_in = user.last_sign_in_at
                if last_sign_in:
                    last_sign_in_dt = datetime.fromisoformat(last_sign_in.replace('Z', '+00:00'))
                    if last_sign_in_dt >= seven_days_ago:
                        metrics["active_users_7d"] += 1
                    if last_sign_in_dt >= thirty_days_ago:
                        metrics["active_users_30d"] += 1

        # Get storage metrics (if using Supabase storage)
        try:
            buckets = supabase.storage.list_buckets()
            total_size_bytes = 0
            total_objects = 0

            for bucket in buckets:
                bucket_id = bucket.get("id", "")
                try:
                    files = supabase.storage.from_(bucket_id).list()
                    for file in files:
                        metadata = file.get("metadata", {})
                        size = metadata.get("size", 0)
                        total_size_bytes += size
                        total_objects += 1
                except Exception as e:
                    logger.debug(f"Failed to list files in bucket {bucket_id}: {e}")

            metrics["storage_size_gb"] = total_size_bytes / (1024 ** 3)
            metrics["storage_objects"] = total_objects

        except Exception as e:
            logger.debug(f"Failed to get storage metrics: {e}")

        # Supabase pricing estimation
        # Free tier: 50k MAU, 1GB storage, 500MB database
        # Pro: $25/month + overages
        base_cost = 0.0

        if metrics["active_users_30d"] > 50000:
            base_cost = 25.0
            # $0.00325 per additional MAU
            overage_users = metrics["active_users_30d"] - 50000
            base_cost += overage_users * 0.00325

        # Storage overage: $0.021/GB over 100GB
        if metrics["storage_size_gb"] > 100:
            base_cost += (metrics["storage_size_gb"] - 100) * 0.021

        metrics["total_cost_usd"] = base_cost

        logger.info(
            f"✅ Collected Supabase metrics: "
            f"{metrics['total_users']} total users, "
            f"{metrics['active_users_30d']} active (30d), "
            f"${metrics['total_cost_usd']:.2f}"
        )
        return metrics

    except Exception as e:
        logger.error(f"❌ Failed to collect Supabase metrics: {e}", exc_info=True)
        return None
