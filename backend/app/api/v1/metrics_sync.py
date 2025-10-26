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

        # Enrich metrics with user_id from messages table
        enriched_count = await _enrich_metrics_with_user_id()

        return {
            "success": True,
            "synced_count": synced_count,
            "enriched_count": enriched_count,
            "recorded_at": recorded_at.isoformat(),
            "message": f"Successfully synced {synced_count} metric records, enriched {enriched_count} with user_id"
        }

    except Exception as e:
        logger.error(f"❌ Failed to sync metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _enrich_metrics_with_user_id():
    """
    Enrich metrics with user_id by correlating with messages table
    Matches based on timestamp proximity (within 5 seconds)
    """
    try:
        enriched_count = 0

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                # Update metrics with user_id from messages table
                # Match by timestamp (within 5 seconds window)
                enrich_query = """
                    UPDATE llm_metrics_history AS m
                    SET user_id = msg.user_id
                    FROM (
                        SELECT DISTINCT ON (created_at)
                            user_id,
                            created_at
                        FROM messages
                        WHERE role = 'assistant'
                          AND created_at >= NOW() - INTERVAL '24 hours'
                          AND user_id IS NOT NULL
                        ORDER BY created_at DESC
                    ) AS msg
                    WHERE m.user_id IS NULL
                      AND m.recorded_at BETWEEN msg.created_at - INTERVAL '5 seconds'
                                            AND msg.created_at + INTERVAL '5 seconds'
                      AND m.recorded_at >= NOW() - INTERVAL '24 hours'
                """

                cur.execute(enrich_query)
                enriched_count = cur.rowcount

        logger.info(f"✅ Enriched {enriched_count} metrics with user_id")
        return enriched_count

    except Exception as e:
        logger.error(f"⚠️ Failed to enrich metrics with user_id: {e}")
        return 0


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


@router.get("/cost-by-user")
async def get_cost_by_user(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, description="Number of top users to return"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get LLM cost breakdown by user
    Admin only
    """
    # Verify admin privileges
    user_role = current_user.get("role", "user")
    is_admin = user_role in ["admin", "superuser"] or current_user.get("is_admin", False)

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Default to last 30 days
        if not start_date:
            start = datetime.utcnow() - timedelta(days=30)
        else:
            start = datetime.fromisoformat(start_date)

        if not end_date:
            end = datetime.utcnow()
        else:
            end = datetime.fromisoformat(end_date)

        query = """
            SELECT
                m.user_id,
                u.email,
                SUM(m.cost_usd) as total_cost_usd,
                SUM(m.total_tokens) as total_tokens,
                SUM(m.request_count) as total_requests,
                COUNT(DISTINCT m.model) as models_used
            FROM llm_metrics_history m
            LEFT JOIN auth.users u ON m.user_id = u.id
            WHERE m.recorded_at >= %s
              AND m.recorded_at <= %s
              AND m.user_id IS NOT NULL
            GROUP BY m.user_id, u.email
            ORDER BY total_cost_usd DESC
            LIMIT %s
        """

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (start, end, limit))
                rows = cur.fetchall()

        return {
            "success": True,
            "count": len(rows),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "users": [
                {
                    "user_id": str(row[0]) if row[0] else None,
                    "email": row[1],
                    "total_cost_usd": float(row[2]) if row[2] else 0.0,
                    "total_tokens": row[3] if row[3] else 0,
                    "total_requests": row[4] if row[4] else 0,
                    "models_used": row[5] if row[5] else 0
                }
                for row in rows
            ]
        }

    except Exception as e:
        logger.error(f"Failed to fetch cost by user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/token-ratios")
async def get_token_ratios(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get prompt vs completion token ratios by model
    Admin only
    """
    # Verify admin privileges
    user_role = current_user.get("role", "user")
    is_admin = user_role in ["admin", "superuser"] or current_user.get("is_admin", False)

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Default to last 30 days
        if not start_date:
            start = datetime.utcnow() - timedelta(days=30)
        else:
            start = datetime.fromisoformat(start_date)

        if not end_date:
            end = datetime.utcnow()
        else:
            end = datetime.fromisoformat(end_date)

        query = """
            SELECT
                model,
                provider,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens,
                CASE
                    WHEN SUM(prompt_tokens) > 0
                    THEN ROUND((SUM(completion_tokens)::numeric / SUM(prompt_tokens)::numeric), 2)
                    ELSE 0
                END as completion_to_prompt_ratio
            FROM llm_metrics_history
            WHERE recorded_at >= %s
              AND recorded_at <= %s
            GROUP BY model, provider
            ORDER BY total_tokens DESC
        """

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (start, end))
                rows = cur.fetchall()

        return {
            "success": True,
            "count": len(rows),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "ratios": [
                {
                    "model": row[0],
                    "provider": row[1],
                    "prompt_tokens": row[2] if row[2] else 0,
                    "completion_tokens": row[3] if row[3] else 0,
                    "total_tokens": row[4] if row[4] else 0,
                    "completion_to_prompt_ratio": float(row[5]) if row[5] else 0.0
                }
                for row in rows
            ]
        }

    except Exception as e:
        logger.error(f"Failed to fetch token ratios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/error-rates")
async def get_error_rates(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get error rates by provider
    Admin only
    """
    # Verify admin privileges
    user_role = current_user.get("role", "user")
    is_admin = user_role in ["admin", "superuser"] or current_user.get("is_admin", False)

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Default to last 7 days for error analysis
        if not start_date:
            start = datetime.utcnow() - timedelta(days=7)
        else:
            start = datetime.fromisoformat(start_date)

        if not end_date:
            end = datetime.utcnow()
        else:
            end = datetime.fromisoformat(end_date)

        query = """
            SELECT
                provider,
                model,
                status,
                SUM(request_count) as request_count,
                SUM(cost_usd) as cost_usd
            FROM llm_metrics_history
            WHERE recorded_at >= %s
              AND recorded_at <= %s
            GROUP BY provider, model, status
            ORDER BY provider, model, status
        """

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (start, end))
                rows = cur.fetchall()

        # Calculate error rates by provider
        provider_stats = {}
        for row in rows:
            provider = row[0]
            model = row[1]
            status = row[2]
            request_count = row[3] or 0
            cost_usd = row[4] or 0.0

            if provider not in provider_stats:
                provider_stats[provider] = {
                    "total_requests": 0,
                    "success_requests": 0,
                    "error_requests": 0,
                    "total_cost": 0.0,
                    "models": {}
                }

            provider_stats[provider]["total_requests"] += request_count
            provider_stats[provider]["total_cost"] += float(cost_usd)

            if status == "success":
                provider_stats[provider]["success_requests"] += request_count
            else:
                provider_stats[provider]["error_requests"] += request_count

            if model not in provider_stats[provider]["models"]:
                provider_stats[provider]["models"][model] = {
                    "total": 0,
                    "success": 0,
                    "error": 0
                }

            provider_stats[provider]["models"][model]["total"] += request_count
            if status == "success":
                provider_stats[provider]["models"][model]["success"] += request_count
            else:
                provider_stats[provider]["models"][model]["error"] += request_count

        # Calculate percentages
        results = []
        for provider, stats in provider_stats.items():
            error_rate = 0.0
            if stats["total_requests"] > 0:
                error_rate = (stats["error_requests"] / stats["total_requests"]) * 100

            results.append({
                "provider": provider,
                "total_requests": stats["total_requests"],
                "success_requests": stats["success_requests"],
                "error_requests": stats["error_requests"],
                "error_rate_percent": round(error_rate, 2),
                "total_cost_usd": round(stats["total_cost"], 4),
                "models": stats["models"]
            })

        return {
            "success": True,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "providers": results
        }

    except Exception as e:
        logger.error(f"Failed to fetch error rates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
