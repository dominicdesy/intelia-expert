"""
Weaviate Metrics Collector
Collects vector database usage and performance metrics
"""

import logging
import os
from datetime import datetime
from typing import Dict, Optional
import httpx

logger = logging.getLogger(__name__)

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")


async def collect_weaviate_metrics() -> Optional[Dict]:
    """
    Collect Weaviate vector database metrics
    Returns dict with storage, objects count, query performance
    """
    try:
        headers = {}
        if WEAVIATE_API_KEY:
            headers["Authorization"] = f"Bearer {WEAVIATE_API_KEY}"

        metrics = {
            "recorded_at": datetime.utcnow(),
            "total_objects": 0,
            "storage_size_mb": 0.0,
            "queries_count": 0,
            "avg_query_time_ms": 0.0,
            "estimated_cost_usd": 0.0
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get schema to count classes
            schema_response = await client.get(
                f"{WEAVIATE_URL}/v1/schema",
                headers=headers
            )
            schema_response.raise_for_status()
            schema = schema_response.json()

            classes = schema.get("classes", [])
            total_objects = 0

            # Get object count for each class
            for cls in classes:
                class_name = cls.get("class", "")
                try:
                    agg_response = await client.post(
                        f"{WEAVIATE_URL}/v1/graphql",
                        json={
                            "query": f"""
                            {{
                                Aggregate {{
                                    {class_name} {{
                                        meta {{
                                            count
                                        }}
                                    }}
                                }}
                            }}
                            """
                        },
                        headers=headers
                    )
                    agg_response.raise_for_status()
                    agg_data = agg_response.json()

                    count = (
                        agg_data.get("data", {})
                        .get("Aggregate", {})
                        .get(class_name, [{}])[0]
                        .get("meta", {})
                        .get("count", 0)
                    )
                    total_objects += count

                except Exception as e:
                    logger.debug(f"Failed to get count for class {class_name}: {e}")

            metrics["total_objects"] = total_objects

            # Estimate storage size (rough: ~1KB per object on average)
            metrics["storage_size_mb"] = (total_objects * 1) / 1024  # KB to MB

            # Weaviate Cloud pricing estimation (if using cloud)
            # Free tier: up to 100k objects
            # Paid: starts at $25/month for 100k-1M objects
            if total_objects > 100000:
                metrics["estimated_cost_usd"] = 25.0
            else:
                metrics["estimated_cost_usd"] = 0.0  # Free tier or self-hosted

        logger.info(
            f"✅ Collected Weaviate metrics: "
            f"{metrics['total_objects']} objects, "
            f"{metrics['storage_size_mb']:.2f} MB"
        )
        return metrics

    except Exception as e:
        logger.error(f"❌ Failed to collect Weaviate metrics: {e}", exc_info=True)
        return None
