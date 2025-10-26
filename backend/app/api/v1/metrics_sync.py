"""
LLM Metrics Sync API
Synchronizes Prometheus metrics to PostgreSQL for long-term storage (6+ months)
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
import httpx

from app.core.database import get_pg_connection
from app.api.v1.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Secret pour les cron jobs (même que currency rates)
CRON_SECRET = os.getenv("CRON_SECRET_KEY", "")

PROMETHEUS_URL = "http://intelia-prometheus:9090"


async def query_prometheus(query: str) -> Dict:
    """Query Prometheus API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query}
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                raise ValueError(f"Prometheus query failed: {data}")

            return data.get("data", {})
    except Exception as e:
        logger.error(f"Failed to query Prometheus: {e}")
        raise HTTPException(status_code=502, detail=f"Prometheus unavailable: {str(e)}")


@router.post("/sync-prometheus-metrics-cron")
async def sync_prometheus_to_db_cron(
    secret: str = Query(..., description="Cron secret")
):
    """
    Synchronize current Prometheus metrics to PostgreSQL
    Called by cron-job.org daily
    URL: /api/v1/metrics/sync-prometheus-metrics-cron?secret=xxx
    """
    # Validate secret
    if not CRON_SECRET or secret != CRON_SECRET:
        logger.warning(f"Invalid cron secret attempt")
        raise HTTPException(status_code=403, detail="Invalid secret")

    return await _sync_prometheus_to_db()


@router.post("/sync-prometheus-metrics")
async def sync_prometheus_to_db_admin(
    current_user: dict = Depends(get_current_user)
):
    """
    Synchronize current Prometheus metrics to PostgreSQL
    Admin only - for manual sync
    """
    # Verify admin privileges
    user_role = current_user.get("role", "user")
    is_admin = user_role in ["admin", "superuser"] or current_user.get("is_admin", False)

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    return await _sync_prometheus_to_db()


async def _sync_prometheus_to_db():
    """
    Internal function to sync Prometheus metrics to PostgreSQL
    """
    try:
        recorded_at = datetime.utcnow()
        synced_count = 0

        # Query all current metrics from Prometheus
        queries = {
            "cost_by_model_feature": "sum by (model, provider, feature) (intelia_llm_cost_usd_total)",
            "tokens_by_model_type": "sum by (model, provider, type) (intelia_llm_tokens_total)",
            "requests_by_model": "sum by (model, provider, status) (intelia_llm_requests_total)"
        }

        # Fetch all metrics
        cost_data = await query_prometheus(queries["cost_by_model_feature"])
        tokens_data = await query_prometheus(queries["tokens_by_model_type"])
        requests_data = await query_prometheus(queries["requests_by_model"])

        # Build aggregated records
        metrics_map: Dict[str, Dict] = {}

        # Process costs
        for result in cost_data.get("result", []):
            metric = result.get("metric", {})
            value = float(result.get("value", [0, "0"])[1])

            key = f"{metric.get('model')}|{metric.get('provider')}|{metric.get('feature', 'chat')}"
            if key not in metrics_map:
                metrics_map[key] = {
                    "model": metric.get("model", "unknown"),
                    "provider": metric.get("provider", "unknown"),
                    "feature": metric.get("feature", "chat"),
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost_usd": 0.0,
                    "request_count": 0,
                    "status": "success"
                }
            metrics_map[key]["cost_usd"] = value

        # Process tokens
        for result in tokens_data.get("result", []):
            metric = result.get("metric", {})
            value = int(float(result.get("value", [0, "0"])[1]))
            token_type = metric.get("type", "prompt")

            key = f"{metric.get('model')}|{metric.get('provider')}|chat"
            if key not in metrics_map:
                metrics_map[key] = {
                    "model": metric.get("model", "unknown"),
                    "provider": metric.get("provider", "unknown"),
                    "feature": "chat",
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost_usd": 0.0,
                    "request_count": 0,
                    "status": "success"
                }

            if token_type == "prompt":
                metrics_map[key]["prompt_tokens"] = value
            elif token_type == "completion":
                metrics_map[key]["completion_tokens"] = value

        # Process requests
        for result in requests_data.get("result", []):
            metric = result.get("metric", {})
            value = int(float(result.get("value", [0, "0"])[1]))

            key = f"{metric.get('model')}|{metric.get('provider')}|chat"
            if key not in metrics_map:
                metrics_map[key] = {
                    "model": metric.get("model", "unknown"),
                    "provider": metric.get("provider", "unknown"),
                    "feature": "chat",
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost_usd": 0.0,
                    "request_count": 0,
                    "status": metric.get("status", "success")
                }
            metrics_map[key]["request_count"] = value
            metrics_map[key]["status"] = metric.get("status", "success")

        # Insert all aggregated metrics into PostgreSQL
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                for metric_data in metrics_map.values():
                    insert_metric_query = """
                        INSERT INTO llm_metrics_history (
                            recorded_at, model, provider, feature,
                            prompt_tokens, completion_tokens, total_tokens,
                            cost_usd, request_count, status
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s
                        )
                        ON CONFLICT (recorded_at, model, provider, feature, status)
                        DO UPDATE SET
                            prompt_tokens = llm_metrics_history.prompt_tokens + EXCLUDED.prompt_tokens,
                            completion_tokens = llm_metrics_history.completion_tokens + EXCLUDED.completion_tokens,
                            total_tokens = llm_metrics_history.total_tokens + EXCLUDED.total_tokens,
                            cost_usd = llm_metrics_history.cost_usd + EXCLUDED.cost_usd,
                            request_count = llm_metrics_history.request_count + EXCLUDED.request_count
                    """

                    cur.execute(insert_metric_query, (
                        recorded_at,
                        metric_data["model"],
                        metric_data["provider"],
                        metric_data["feature"],
                        metric_data["prompt_tokens"],
                        metric_data["completion_tokens"],
                        metric_data["prompt_tokens"] + metric_data["completion_tokens"],
                        metric_data["cost_usd"],
                        metric_data["request_count"],
                        metric_data["status"]
                    ))
                    synced_count += 1

        logger.info(f"✅ Synced {synced_count} metrics to PostgreSQL at {recorded_at}")

        return {
            "success": True,
            "synced_count": synced_count,
            "recorded_at": recorded_at.isoformat(),
            "message": f"Successfully synced {synced_count} metric records"
        }

    except Exception as e:
        logger.error(f"❌ Failed to sync metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics-history")
async def get_metrics_history(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    model: Optional[str] = Query(None, description="Filter by model"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get historical metrics from PostgreSQL
    Admin only
    """
    # Verify admin privileges
    user_role = current_user.get("role", "user")
    is_admin = user_role in ["admin", "superuser"] or current_user.get("is_admin", False)

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    try:
        # Default to last 30 days if no dates provided
        if not start_date:
            start = datetime.utcnow() - timedelta(days=30)
        else:
            start = datetime.fromisoformat(start_date)

        if not end_date:
            end = datetime.utcnow()
        else:
            end = datetime.fromisoformat(end_date)

        # Build query
        query = """
            SELECT
                recorded_at,
                model,
                provider,
                feature,
                SUM(prompt_tokens) as prompt_tokens,
                SUM(completion_tokens) as completion_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as cost_usd,
                SUM(request_count) as request_count
            FROM llm_metrics_history
            WHERE recorded_at >= %s
              AND recorded_at <= %s
        """

        params = [start, end]

        if model:
            query += " AND model = %s"
            params.append(model)

        if provider:
            query += " AND provider = %s"
            params.append(provider)

        query += """
            GROUP BY recorded_at, model, provider, feature
            ORDER BY recorded_at DESC
            LIMIT 1000
        """

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return {
            "success": True,
            "count": len(rows),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "metrics": [
                {
                    "recorded_at": row[0].isoformat(),
                    "model": row[1],
                    "provider": row[2],
                    "feature": row[3],
                    "prompt_tokens": row[4],
                    "completion_tokens": row[5],
                    "total_tokens": row[6],
                    "cost_usd": float(row[7]),
                    "request_count": row[8]
                }
                for row in rows
            ]
        }

    except Exception as e:
        logger.error(f"Failed to fetch metrics history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics-monthly-summary")
async def get_monthly_summary(
    months: int = Query(6, description="Number of months to retrieve"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get monthly cost summary for the last N months
    Admin only
    """
    # Verify admin privileges
    user_role = current_user.get("role", "user")
    is_admin = user_role in ["admin", "superuser"] or current_user.get("is_admin", False)

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    try:
        query = """
            SELECT
                DATE_TRUNC('month', recorded_at) as month,
                SUM(cost_usd) as total_cost,
                SUM(total_tokens) as total_tokens,
                SUM(request_count) as total_requests,
                COUNT(DISTINCT model) as unique_models
            FROM llm_metrics_history
            WHERE recorded_at >= NOW() - INTERVAL '%s months'
            GROUP BY DATE_TRUNC('month', recorded_at)
            ORDER BY month DESC
        """

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (months,))
                rows = cur.fetchall()

        return {
            "success": True,
            "months": months,
            "summary": [
                {
                    "month": row[0].strftime("%Y-%m"),
                    "total_cost_usd": float(row[1]),
                    "total_tokens": row[2],
                    "total_requests": row[3],
                    "unique_models": row[4]
                }
                for row in rows
            ]
        }

    except Exception as e:
        logger.error(f"Failed to fetch monthly summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
