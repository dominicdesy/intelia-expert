"""
Geo-location service to detect user country from IP address
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Geo-location service to detect user country from IP address
Uses ip-api.com (free, no API key required, 45 requests/minute)
"""

import logging
import requests
from typing import Optional, Dict
from functools import lru_cache

logger = logging.getLogger(__name__)


class GeoLocationService:
    """Service to detect country from IP address"""

    # Free API, no key required, 45 req/min limit
    IP_API_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode"

    # Fallback API if primary fails
    IPINFO_URL = "https://ipinfo.io/{ip}/json"

    @staticmethod
    @lru_cache(maxsize=1000)  # Cache results to avoid hitting API limits
    def get_country_from_ip(ip_address: str) -> Optional[Dict[str, str]]:
        """
        Detect country from IP address

        Args:
            ip_address: IPv4 or IPv6 address

        Returns:
            Dict with country_code and country_name, or None if detection failed
        """
        # Skip localhost and private IPs
        if ip_address in ["127.0.0.1", "::1", "localhost"] or ip_address.startswith("192.168.") or ip_address.startswith("10."):
            logger.debug(f"Skipping geo-location for local/private IP: {ip_address}")
            return None

        # Try primary API (ip-api.com)
        try:
            logger.debug(f"Detecting country for IP: {ip_address}")
            response = requests.get(
                GeoLocationService.IP_API_URL.format(ip=ip_address),
                timeout=3
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                country_code = data.get("countryCode", "").upper()
                country_name = data.get("country", "")

                if country_code:
                    logger.info(f"Country detected for {ip_address}: {country_code} ({country_name})")
                    return {
                        "country_code": country_code,
                        "country_name": country_name,
                        "source": "ip-api.com"
                    }

            logger.warning(f"IP API returned non-success status: {data.get('message', 'Unknown')}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Primary IP API failed for {ip_address}: {e}")

        # Try fallback API (ipinfo.io)
        try:
            logger.debug(f"Trying fallback API for {ip_address}")
            response = requests.get(
                GeoLocationService.IPINFO_URL.format(ip=ip_address),
                timeout=3
            )
            response.raise_for_status()
            data = response.json()

            country_code = data.get("country", "").upper()
            if country_code:
                logger.info(f"Country detected (fallback) for {ip_address}: {country_code}")
                return {
                    "country_code": country_code,
                    "country_name": data.get("country", country_code),
                    "source": "ipinfo.io"
                }

        except requests.exceptions.RequestException as e:
            logger.warning(f"Fallback IP API also failed for {ip_address}: {e}")

        logger.error(f"Could not detect country for IP: {ip_address}")
        return None

    @staticmethod
    def get_client_ip(request) -> str:
        """
        Extract real client IP from request headers
        Handles proxies, load balancers, and Cloudflare

        Args:
            request: FastAPI Request object

        Returns:
            Client IP address
        """
        # Check Cloudflare header
        cf_connecting_ip = request.headers.get("CF-Connecting-IP")
        if cf_connecting_ip:
            logger.debug(f"Using Cloudflare IP: {cf_connecting_ip}")
            return cf_connecting_ip

        # Check X-Forwarded-For (proxy/load balancer)
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            ip = x_forwarded_for.split(",")[0].strip()
            logger.debug(f"Using X-Forwarded-For IP: {ip}")
            return ip

        # Check X-Real-IP
        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            logger.debug(f"Using X-Real-IP: {x_real_ip}")
            return x_real_ip

        # Fallback to request.client.host
        client_ip = request.client.host if request.client else "127.0.0.1"
        logger.debug(f"Using client.host IP: {client_ip}")
        return client_ip

    @staticmethod
    def clear_cache():
        """Clear the IP geocoding cache"""
        GeoLocationService.get_country_from_ip.cache_clear()
        logger.info("Geo-location cache cleared")
