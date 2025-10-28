# -*- coding: utf-8 -*-
"""
Base class for external source fetchers
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Base class for external source fetchers
"""

import logging
import asyncio
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from ..models import ExternalDocument

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """
    Abstract base class for external source fetchers

    All fetchers must implement:
    - search(): Search for documents matching query
    - _parse_response(): Parse API response into ExternalDocument objects
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        rate_limit: float = 1.0,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize fetcher

        Args:
            name: Source name (e.g., "semantic_scholar")
            base_url: API base URL
            rate_limit: Requests per second
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.name = name
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries

        # HTTP client with timeout
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout), follow_redirects=True
        )

        # Rate limiting
        self._last_request_time = 0.0
        self._request_lock = asyncio.Lock()

        logger.info(f"✅ {name} fetcher initialized (rate_limit={rate_limit}/s)")

    async def search(
        self, query: str, max_results: int = 5, min_year: int = 2015
    ) -> List[ExternalDocument]:
        """
        Search for documents matching query

        Args:
            query: Search query
            max_results: Maximum results to return
            min_year: Minimum publication year

        Returns:
            List of ExternalDocument objects
        """
        try:
            logger.info(f"🔍 [{self.name}] Searching for: {query[:60]}...")

            # Rate limiting
            await self._rate_limit()

            # Make API request with retries
            response = await self._request_with_retry(query, max_results, min_year)

            # Parse response
            documents = self._parse_response(response, query)

            # Filter by year
            documents = [doc for doc in documents if doc.year >= min_year]

            # Limit results
            documents = documents[:max_results]

            logger.info(f"✅ [{self.name}] Found {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"❌ [{self.name}] Search failed: {e}")
            return []

    async def _rate_limit(self):
        """Apply rate limiting"""
        async with self._request_lock:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            min_interval = 1.0 / self.rate_limit

            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                await asyncio.sleep(wait_time)

            self._last_request_time = asyncio.get_event_loop().time()

    async def _request_with_retry(
        self, query: str, max_results: int, min_year: int
    ) -> Dict[str, Any]:
        """
        Make API request with exponential backoff retry

        Args:
            query: Search query
            max_results: Maximum results
            min_year: Minimum year

        Returns:
            API response as dict
        """
        for attempt in range(self.max_retries):
            try:
                response = await self._make_request(query, max_results, min_year)
                return response

            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"⚠️ [{self.name}] Timeout, retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt < self.max_retries - 1:
                        wait_time = 5 * (2**attempt)  # Longer wait for rate limits
                        logger.warning(
                            f"⚠️ [{self.name}] Rate limited, waiting {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        raise
                else:
                    raise

        raise Exception(f"Max retries ({self.max_retries}) exceeded")

    @abstractmethod
    async def _make_request(
        self, query: str, max_results: int, min_year: int
    ) -> Dict[str, Any]:
        """
        Make actual API request (must be implemented by subclass)

        Args:
            query: Search query
            max_results: Maximum results
            min_year: Minimum year

        Returns:
            Raw API response
        """
        pass

    @abstractmethod
    def _parse_response(
        self, response: Dict[str, Any], query: str
    ) -> List[ExternalDocument]:
        """
        Parse API response into ExternalDocument objects

        Args:
            response: Raw API response
            query: Original query (for context)

        Returns:
            List of ExternalDocument objects
        """
        pass

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def __del__(self):
        """Cleanup on deletion"""
        try:
            asyncio.create_task(self.close())
        except:
            pass
