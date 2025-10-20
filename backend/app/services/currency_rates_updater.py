"""
Currency Rates Updater Service
Fetches live exchange rates from Frankfurter API and updates the database
"""

import logging
import requests
import psycopg2
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CurrencyRatesUpdater:
    """Service to fetch and update currency exchange rates"""

    FRANKFURTER_API_URL = "https://api.frankfurter.app/latest"
    BASE_CURRENCY = "USD"

    def __init__(self, db_connection):
        """
        Initialize updater with database connection
        Args:
            db_connection: psycopg2 connection object or connection string
        """
        if isinstance(db_connection, str):
            self.conn = psycopg2.connect(db_connection)
            self.should_close = True
        else:
            self.conn = db_connection
            self.should_close = False

    def fetch_live_rates(self) -> Optional[Dict]:
        """
        Fetch live exchange rates from Frankfurter API
        Returns dict with rates or None if failed
        """
        try:
            logger.info(f"Fetching live exchange rates from Frankfurter API (base: {self.BASE_CURRENCY})")

            response = requests.get(
                self.FRANKFURTER_API_URL,
                params={"from": self.BASE_CURRENCY},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            rates_date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
            raw_rates = data.get("rates", {})

            # Convert from USD->XXX to XXX->USD (invert the rates)
            converted_rates = {self.BASE_CURRENCY: 1.0}
            for currency, rate in raw_rates.items():
                # If 1 USD = 1.35 CAD, then 1 CAD = 1/1.35 USD = 0.74 USD
                converted_rates[currency] = round(1.0 / rate, 8)

            logger.info(f"Successfully fetched {len(converted_rates)} exchange rates (date: {rates_date})")
            logger.debug(f"Sample rates: CAD={converted_rates.get('CAD')}, EUR={converted_rates.get('EUR')}, GBP={converted_rates.get('GBP')}")

            return {
                "rates": converted_rates,
                "date": rates_date,
                "count": len(converted_rates)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch exchange rates from Frankfurter API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching exchange rates: {e}")
            return None

    def update_database_rates(self, rates: Dict[str, float]) -> Dict:
        """
        Update currency rates in the database
        Returns dict with update statistics
        """
        try:
            updated_count = 0
            new_count = 0
            failed = []

            with self.conn.cursor() as cur:
                for currency_code, rate in rates.items():
                    try:
                        # Get friendly currency name
                        currency_name = self._get_currency_name(currency_code)

                        # Use PostgreSQL's ON CONFLICT to update or insert
                        cur.execute("""
                            INSERT INTO stripe_currency_rates (currency_code, currency_name, rate_to_usd, last_updated)
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (currency_code)
                            DO UPDATE SET
                                rate_to_usd = EXCLUDED.rate_to_usd,
                                last_updated = CURRENT_TIMESTAMP
                            RETURNING (xmax = 0) as inserted
                        """, (currency_code, currency_name, rate))

                        row = cur.fetchone()
                        if row and row[0]:  # inserted = True
                            new_count += 1
                        else:
                            updated_count += 1

                    except Exception as e:
                        logger.error(f"Failed to update rate for {currency_code}: {e}")
                        failed.append(currency_code)

                self.conn.commit()

            stats = {
                "updated": updated_count,
                "new": new_count,
                "failed": len(failed),
                "total": updated_count + new_count,
                "failed_currencies": failed
            }

            logger.info(f"Database update complete: {stats['updated']} updated, {stats['new']} new, {stats['failed']} failed")

            return stats

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Database update failed: {e}")
            raise

    def update_all_rates(self) -> Dict:
        """
        Main method: Fetch live rates and update database
        Returns dict with complete update information
        """
        logger.info("Starting currency rates update process")

        # Fetch live rates
        rates_data = self.fetch_live_rates()
        if not rates_data:
            return {
                "success": False,
                "error": "Failed to fetch live rates from API",
                "timestamp": datetime.now().isoformat()
            }

        # Update database
        try:
            stats = self.update_database_rates(rates_data["rates"])

            return {
                "success": True,
                "rates_date": rates_data["date"],
                "currencies_fetched": rates_data["count"],
                "database_stats": stats,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Update process failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def close(self):
        """Close database connection if we created it"""
        if self.should_close and self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    @staticmethod
    def _get_currency_name(currency_code: str) -> str:
        """Get friendly name for currency code"""
        CURRENCY_NAMES = {
            'USD': 'US Dollar',
            'EUR': 'Euro',
            'GBP': 'British Pound',
            'CAD': 'Canadian Dollar',
            'AUD': 'Australian Dollar',
            'CHF': 'Swiss Franc',
            'JPY': 'Japanese Yen',
            'CNY': 'Chinese Yuan',
            'INR': 'Indian Rupee',
            'BRL': 'Brazilian Real',
            'MXN': 'Mexican Peso',
            'ZAR': 'South African Rand',
            'RUB': 'Russian Ruble',
            'TRY': 'Turkish Lira',
            'KRW': 'South Korean Won',
            'IDR': 'Indonesian Rupiah',
            'THB': 'Thai Baht',
            'MYR': 'Malaysian Ringgit',
            'SGD': 'Singapore Dollar',
            'HKD': 'Hong Kong Dollar',
            'NOK': 'Norwegian Krone',
            'SEK': 'Swedish Krona',
            'DKK': 'Danish Krone',
            'PLN': 'Polish Zloty',
            'CZK': 'Czech Koruna',
            'HUF': 'Hungarian Forint',
            'ILS': 'Israeli Shekel',
            'PHP': 'Philippine Peso',
            'VND': 'Vietnamese Dong',
            'AED': 'UAE Dirham',
            'SAR': 'Saudi Riyal',
            'QAR': 'Qatari Riyal',
            'KWD': 'Kuwaiti Dinar',
            'ARS': 'Argentine Peso',
            'CLP': 'Chilean Peso',
            'COP': 'Colombian Peso',
            'PEN': 'Peruvian Sol',
            'NZD': 'New Zealand Dollar',
        }
        return CURRENCY_NAMES.get(currency_code, currency_code)
