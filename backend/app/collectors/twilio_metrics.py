"""
Twilio Metrics Collector
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Twilio Metrics Collector
Collects SMS and WhatsApp usage and costs from Twilio API
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from twilio.rest import Client

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")


async def collect_twilio_metrics() -> Optional[Dict]:
    """
    Collect Twilio communication metrics (SMS, WhatsApp, Voice)
    Returns dict with message counts and costs
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials not configured, skipping Twilio metrics")
        return None

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        metrics = {
            "recorded_at": datetime.utcnow(),
            "sms_sent": 0,
            "sms_cost_usd": 0.0,
            "whatsapp_sent": 0,
            "whatsapp_cost_usd": 0.0,
            "voice_minutes": 0,
            "voice_cost_usd": 0.0,
            "total_cost_usd": 0.0
        }

        # Get messages from last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)

        # Get SMS messages
        sms_messages = client.messages.list(
            date_sent_after=yesterday,
            limit=1000
        )

        for msg in sms_messages:
            # Check if it's WhatsApp or regular SMS
            if msg.from_ and "whatsapp:" in msg.from_:
                metrics["whatsapp_sent"] += 1
                # WhatsApp: ~$0.005 per message (varies by country)
                metrics["whatsapp_cost_usd"] += 0.005
            else:
                metrics["sms_sent"] += 1
                # SMS: ~$0.0075 per message (US average)
                metrics["sms_cost_usd"] += 0.0075

        # Get voice calls (if used)
        try:
            calls = client.calls.list(
                start_time_after=yesterday,
                limit=1000
            )

            for call in calls:
                duration_seconds = int(call.duration or 0)
                duration_minutes = duration_seconds / 60
                metrics["voice_minutes"] += duration_minutes
                # Voice: ~$0.013/minute (US)
                metrics["voice_cost_usd"] += duration_minutes * 0.013

        except Exception as e:
            logger.debug(f"Failed to get voice calls: {e}")

        # Calculate total
        metrics["total_cost_usd"] = (
            metrics["sms_cost_usd"] +
            metrics["whatsapp_cost_usd"] +
            metrics["voice_cost_usd"]
        )

        logger.info(
            f"✅ Collected Twilio metrics: "
            f"{metrics['sms_sent']} SMS, "
            f"{metrics['whatsapp_sent']} WhatsApp, "
            f"${metrics['total_cost_usd']:.4f}"
        )
        return metrics

    except Exception as e:
        logger.error(f"❌ Failed to collect Twilio metrics: {e}", exc_info=True)
        return None
