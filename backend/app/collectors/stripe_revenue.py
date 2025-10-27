"""
Stripe Revenue Metrics Collector
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Stripe Revenue Metrics Collector
Collects revenue, MRR, subscriptions, and churn data from Stripe API
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import stripe

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


async def collect_stripe_metrics() -> Optional[Dict]:
    """
    Collect Stripe revenue and subscription metrics
    Returns dict with MRR, ARR, churn, subscription counts
    """
    if not stripe.api_key:
        logger.warning("STRIPE_SECRET_KEY not configured, skipping Stripe metrics")
        return None

    try:
        metrics = {
            "recorded_at": datetime.utcnow(),
            "mrr_usd": 0.0,
            "arr_usd": 0.0,
            "active_subscriptions": 0,
            "new_subscriptions": 0,
            "cancelled_subscriptions": 0,
            "churn_rate_percent": 0.0,
            "essential_subs": 0,
            "pro_subs": 0,
            "elite_subs": 0,
            "essential_mrr": 0.0,
            "pro_mrr": 0.0,
            "elite_mrr": 0.0
        }

        # Get all active subscriptions
        active_subs = stripe.Subscription.list(
            status="active",
            limit=100,
            expand=["data.plan.product"]
        )

        # Calculate MRR and plan breakdown
        for sub in active_subs.auto_paging_iter():
            amount = sub.plan.amount / 100  # Convert cents to dollars
            interval = sub.plan.interval

            # Normalize to monthly recurring revenue
            if interval == "month":
                mrr_contribution = amount
            elif interval == "year":
                mrr_contribution = amount / 12
            else:
                mrr_contribution = 0.0

            metrics["mrr_usd"] += mrr_contribution
            metrics["active_subscriptions"] += 1

            # Plan breakdown
            plan_name = sub.plan.nickname or sub.plan.product or ""
            plan_name_lower = plan_name.lower()

            if "essential" in plan_name_lower:
                metrics["essential_subs"] += 1
                metrics["essential_mrr"] += mrr_contribution
            elif "pro" in plan_name_lower:
                metrics["pro_subs"] += 1
                metrics["pro_mrr"] += mrr_contribution
            elif "elite" in plan_name_lower:
                metrics["elite_subs"] += 1
                metrics["elite_mrr"] += mrr_contribution

        # Calculate ARR
        metrics["arr_usd"] = metrics["mrr_usd"] * 12

        # Get subscriptions created in last 30 days (new subscriptions)
        thirty_days_ago = int((datetime.utcnow() - timedelta(days=30)).timestamp())
        new_subs = stripe.Subscription.list(
            status="all",
            created={"gte": thirty_days_ago},
            limit=100
        )

        for sub in new_subs.auto_paging_iter():
            if sub.status in ["active", "trialing"]:
                metrics["new_subscriptions"] += 1
            elif sub.status == "canceled":
                metrics["cancelled_subscriptions"] += 1

        # Calculate churn rate (cancelled / total in period)
        total_subs_in_period = metrics["new_subscriptions"] + metrics["cancelled_subscriptions"]
        if total_subs_in_period > 0:
            metrics["churn_rate_percent"] = (
                metrics["cancelled_subscriptions"] / total_subs_in_period
            ) * 100

        logger.info(
            f"✅ Collected Stripe metrics: "
            f"MRR=${metrics['mrr_usd']:.2f}, "
            f"{metrics['active_subscriptions']} active subs, "
            f"{metrics['churn_rate_percent']:.1f}% churn"
        )
        return metrics

    except Exception as e:
        logger.error(f"❌ Failed to collect Stripe metrics: {e}", exc_info=True)
        return None
