"""
Country Tracking & Fraud Detection Service
Tracks user country at signup and every login for pricing fraud detection
"""

import logging
import os
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import Request
import user_agents

from app.services.geo_location import GeoLocationService

logger = logging.getLogger(__name__)


class CountryTrackingService:
    """
    Service for tracking user countries and detecting pricing fraud
    """

    @staticmethod
    async def track_signup(
        user_email: str,
        request: Request
    ) -> Dict[str, Any]:
        """
        Track user's country at signup time.
        This becomes the baseline for fraud detection.

        Args:
            user_email: User's email address
            request: FastAPI Request object for IP detection

        Returns:
            Dict with signup_country, signup_ip, pricing_tier
        """
        try:
            # Detect country from IP
            client_ip = GeoLocationService.get_client_ip(request)
            geo_info = GeoLocationService.get_country_from_ip(client_ip)
            country_code = geo_info.get("country_code", "US")

            # Get pricing tier for this country
            pricing_tier = CountryTrackingService._get_pricing_tier_for_country(country_code)

            # Save to database
            with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        INSERT INTO user_billing_info (
                            user_email, plan_name,
                            signup_country, signup_ip, signup_detected_at
                        )
                        VALUES (%s, 'essential', %s, %s, NOW())
                        ON CONFLICT (user_email) DO UPDATE
                        SET signup_country = EXCLUDED.signup_country,
                            signup_ip = EXCLUDED.signup_ip,
                            signup_detected_at = COALESCE(
                                user_billing_info.signup_detected_at,
                                EXCLUDED.signup_detected_at
                            )
                        RETURNING signup_country, signup_ip
                    """, (user_email, country_code, client_ip))

                    result = cur.fetchone()
                    conn.commit()

            logger.info(
                f"✅ Signup tracked: {user_email} from {country_code} "
                f"(IP: {client_ip}, Tier: {pricing_tier})"
            )

            return {
                "signup_country": country_code,
                "signup_ip": client_ip,
                "pricing_tier": pricing_tier,
                "tracked_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error tracking signup for {user_email}: {e}")
            # Don't fail signup if tracking fails
            return {
                "signup_country": "US",  # Default fallback
                "signup_ip": None,
                "pricing_tier": "tier1",
                "error": str(e)
            }

    @staticmethod
    async def track_login(
        user_email: str,
        request: Request,
        login_method: str = "password",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track every user login with geo-location and device info.

        Args:
            user_email: User's email
            request: FastAPI Request object
            login_method: 'password', 'oauth_linkedin', 'oauth_facebook', 'webauthn'
            session_id: Optional session identifier

        Returns:
            Dict with login tracking info and risk assessment
        """
        try:
            # Extract geo-location data
            client_ip = GeoLocationService.get_client_ip(request)
            geo_info = GeoLocationService.get_country_from_ip(client_ip)

            country_code = geo_info.get("country_code", "US")
            city = geo_info.get("city", "Unknown")
            region = geo_info.get("region", "Unknown")

            # Detect VPN/Proxy (basic detection)
            is_vpn = CountryTrackingService._detect_vpn(client_ip, geo_info)
            is_proxy = geo_info.get("is_proxy", False)
            is_tor = geo_info.get("is_tor", False)

            # Parse User-Agent
            user_agent_string = request.headers.get("user-agent", "")
            ua = user_agents.parse(user_agent_string)

            device_type = "mobile" if ua.is_mobile else ("tablet" if ua.is_tablet else "desktop")
            browser = f"{ua.browser.family} {ua.browser.version_string}"
            os_name = f"{ua.os.family} {ua.os.version_string}"

            # Calculate risk score
            risk_score = CountryTrackingService._calculate_risk_score(
                user_email, country_code, is_vpn, is_proxy, is_tor
            )

            # Insert login record
            with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        INSERT INTO user_login_history (
                            user_email, login_at, login_method,
                            ip_address, country_code, city, region,
                            user_agent, device_type, browser, os,
                            is_vpn, is_proxy, is_tor, risk_score,
                            session_id
                        )
                        VALUES (
                            %s, NOW(), %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s
                        )
                        RETURNING id, login_at, risk_score
                    """, (
                        user_email, login_method,
                        client_ip, country_code, city, region,
                        user_agent_string, device_type, browser, os_name,
                        is_vpn, is_proxy, is_tor, risk_score,
                        session_id
                    ))

                    login_record = cur.fetchone()

                    # Update last_login in user_billing_info
                    cur.execute("""
                        UPDATE user_billing_info
                        SET last_login_country = %s,
                            last_login_ip = %s,
                            last_login_at = NOW()
                        WHERE user_email = %s
                    """, (country_code, client_ip, user_email))

                    conn.commit()

            # Log warnings for high-risk logins
            if risk_score > 50:
                logger.warning(
                    f"⚠️ HIGH RISK LOGIN: {user_email} from {country_code} "
                    f"(IP: {client_ip}, Risk: {risk_score}, VPN: {is_vpn})"
                )

            logger.info(
                f"✅ Login tracked: {user_email} from {country_code} "
                f"(Device: {device_type}, Risk: {risk_score})"
            )

            return {
                "login_id": login_record["id"],
                "login_at": login_record["login_at"].isoformat(),
                "country_code": country_code,
                "city": city,
                "device_type": device_type,
                "risk_score": risk_score,
                "is_vpn": is_vpn,
                "is_suspicious": risk_score > 50
            }

        except Exception as e:
            logger.error(f"Error tracking login for {user_email}: {e}")
            # Don't fail login if tracking fails
            return {
                "error": str(e),
                "risk_score": 0
            }

    @staticmethod
    def _get_pricing_tier_for_country(country_code: str) -> str:
        """
        Get pricing tier for a country.
        Queries pricing_tiers table.
        """
        try:
            with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT tier FROM pricing_tiers
                        WHERE country_code = %s
                    """, (country_code,))

                    result = cur.fetchone()

                    if result:
                        return result["tier"]
                    else:
                        # Default to tier1 for unknown countries
                        return "tier1"

        except Exception as e:
            logger.error(f"Error getting pricing tier for {country_code}: {e}")
            return "tier1"

    @staticmethod
    def _detect_vpn(ip_address: str, geo_info: Dict) -> bool:
        """
        Basic VPN detection.

        TODO: Integrate with commercial VPN detection service for better accuracy
        (e.g., IPQualityScore, IPHub, VPNApi)
        """
        # Check if geo_info indicates VPN
        if geo_info.get("is_vpn"):
            return True

        # Additional heuristics (can be expanded)
        # - Known VPN IP ranges
        # - ASN analysis
        # - Behavioral patterns

        return False

    @staticmethod
    def _calculate_risk_score(
        user_email: str,
        current_country: str,
        is_vpn: bool,
        is_proxy: bool,
        is_tor: bool
    ) -> int:
        """
        Calculate fraud risk score (0-100).
        Higher score = higher risk of pricing fraud.
        """
        score = 0

        # Base risk for VPN/Proxy/Tor
        if is_vpn:
            score += 30
        if is_proxy:
            score += 25
        if is_tor:
            score += 40

        try:
            with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get signup country
                    cur.execute("""
                        SELECT signup_country, pricing_country
                        FROM user_billing_info
                        WHERE user_email = %s
                    """, (user_email,))

                    user_info = cur.fetchone()

                    if user_info:
                        signup_country = user_info.get("signup_country")
                        pricing_country = user_info.get("pricing_country")

                        # Risk if login country != signup country
                        if signup_country and current_country != signup_country:
                            score += 15

                        # Higher risk if pricing tier is set and country differs
                        if pricing_country and current_country != pricing_country:
                            score += 25

                    # Check country switching frequency (last 7 days)
                    cur.execute("""
                        SELECT COUNT(DISTINCT country_code) as unique_countries
                        FROM user_login_history
                        WHERE user_email = %s
                          AND login_at > NOW() - INTERVAL '7 days'
                    """, (user_email,))

                    country_count = cur.fetchone()

                    if country_count and country_count["unique_countries"] > 3:
                        # Multiple countries in short time = suspicious
                        score += 20

        except Exception as e:
            logger.error(f"Error calculating risk score for {user_email}: {e}")

        return min(100, score)  # Cap at 100

    @staticmethod
    async def get_user_fraud_analysis(user_email: str) -> Dict[str, Any]:
        """
        Get comprehensive fraud risk analysis for a user.
        """
        try:
            with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get fraud risk analysis
                    cur.execute("""
                        SELECT * FROM user_fraud_risk_analysis
                        WHERE user_email = %s
                    """, (user_email,))

                    analysis = cur.fetchone()

                    if not analysis:
                        return {
                            "user_email": user_email,
                            "risk_level": "unknown",
                            "message": "No data available"
                        }

                    # Determine risk level
                    # Use .get() with default to handle missing or NULL values
                    risk_score = analysis.get("calculated_risk_score", 0)
                    if risk_score < 30:
                        risk_level = "low"
                    elif risk_score < 60:
                        risk_level = "medium"
                    else:
                        risk_level = "high"

                    return {
                        **dict(analysis),
                        "risk_level": risk_level
                    }

        except Exception as e:
            logger.error(f"Error getting fraud analysis for {user_email}: {e}")
            return {
                "user_email": user_email,
                "error": str(e)
            }

    @staticmethod
    async def lock_pricing_tier(
        user_email: str,
        request: Request = None
    ) -> Dict[str, Any]:
        """
        Lock the pricing tier for a user at their first subscription.
        Uses multi-source country detection for accuracy.
        """
        try:
            with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get user's country history
                    cur.execute("""
                        SELECT
                            ubi.signup_country,
                            ubi.pricing_locked_at,
                            MODE() WITHIN GROUP (ORDER BY ulh.country_code) as most_common_country,
                            COUNT(DISTINCT ulh.country_code) as unique_countries
                        FROM user_billing_info ubi
                        LEFT JOIN user_login_history ulh ON ubi.user_email = ulh.user_email
                        WHERE ubi.user_email = %s
                        GROUP BY ubi.user_email, ubi.signup_country, ubi.pricing_locked_at
                    """, (user_email,))

                    user_data = cur.fetchone()

                    # If already locked, return existing
                    if user_data and user_data.get("pricing_locked_at"):
                        logger.info(f"Pricing tier already locked for {user_email}")
                        return {
                            "status": "already_locked",
                            "pricing_country": user_data.get("signup_country"),
                            "locked_at": user_data["pricing_locked_at"].isoformat()
                        }

                    # Determine pricing country (prioritize signup country)
                    pricing_country = user_data.get("signup_country") or user_data.get("most_common_country") or "US"

                    # Get pricing tier
                    pricing_tier = CountryTrackingService._get_pricing_tier_for_country(pricing_country)

                    # Lock pricing tier
                    cur.execute("""
                        UPDATE user_billing_info
                        SET pricing_country = %s,
                            pricing_tier = %s,
                            pricing_locked_at = NOW()
                        WHERE user_email = %s
                        RETURNING pricing_country, pricing_tier, pricing_locked_at
                    """, (pricing_country, pricing_tier, user_email))

                    result = cur.fetchone()
                    conn.commit()

                    logger.info(
                        f"🔒 Pricing tier locked: {user_email} → {pricing_country} "
                        f"({pricing_tier})"
                    )

                    return {
                        "status": "locked",
                        "pricing_country": result["pricing_country"],
                        "pricing_tier": result["pricing_tier"],
                        "locked_at": result["pricing_locked_at"].isoformat()
                    }

        except Exception as e:
            logger.error(f"Error locking pricing tier for {user_email}: {e}")
            raise
