#!/usr/bin/env python3
"""
Standalone script to update currency exchange rates
Can be run as a CRON job for daily updates

Usage:
    python scripts/update_currency_rates.py

CRON example (daily at 2:00 AM):
    0 2 * * * cd /path/to/backend && python scripts/update_currency_rates.py >> logs/currency_updates.log 2>&1
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.currency_rates_updater import CurrencyRatesUpdater

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to update currency rates"""
    logger.info("="*80)
    logger.info("Starting daily currency rates update")
    logger.info("="*80)

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    try:
        # Create updater and run update
        with CurrencyRatesUpdater(database_url) as updater:
            result = updater.update_all_rates()

            if result["success"]:
                logger.info("-"*80)
                logger.info("UPDATE SUCCESSFUL")
                logger.info("-"*80)
                logger.info(f"Rates date: {result['rates_date']}")
                logger.info(f"Currencies fetched: {result['currencies_fetched']}")
                logger.info(f"Database updates: {result['database_stats']['updated']} updated, {result['database_stats']['new']} new")
                if result['database_stats']['failed'] > 0:
                    logger.warning(f"Failed currencies: {result['database_stats']['failed_currencies']}")
                logger.info(f"Timestamp: {result['timestamp']}")
                logger.info("="*80)
                return 0
            else:
                logger.error("-"*80)
                logger.error("UPDATE FAILED")
                logger.error("-"*80)
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
                logger.error(f"Timestamp: {result['timestamp']}")
                logger.error("="*80)
                return 1

    except Exception as e:
        logger.error("-"*80)
        logger.error("UNEXPECTED ERROR")
        logger.error("-"*80)
        logger.error(f"Exception: {str(e)}", exc_info=True)
        logger.error("="*80)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
