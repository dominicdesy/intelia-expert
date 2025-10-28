# -*- coding: utf-8 -*-
"""
LLM Service HTTP Client
Client to communicate with the LLM service for intelligent generation
"""

import logging
import httpx
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator
import os
import json

logger = logging.getLogger(__name__)


class LLMServiceClient:
    """
    HTTP client for LLM service intelligent generation endpoints

    This client provides methods to call the LLM service API endpoints:
    - /v1/generate - Intelligent generation with domain configuration
    - /v1/route - Provider routing
    - /v1/calculate-tokens - Token calculation
    - /v1/post-process - Response post-processing
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 120.0):
        """
        Initialize LLM service client

        Args:
            base_url: Base URL of LLM service (defaults to env var or localhost:8081)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv(
            "LLM_SERVICE_URL", "http://localhost:8081"
        )
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

        logger.info(f"LLM Service client initialized: {self.base_url}")

    async def generate(
        self,
        query: str,
        domain: str = "aviculture",
        language: str = "en",
        entities: Optional[Dict[str, Any]] = None,
        query_type: Optional[str] = None,
        context_docs: Optional[List[Dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        post_process: bool = True,
        add_disclaimer: bool = True,
    ) -> Tuple[str, int, int, Dict[str, Any]]:
        """
        Generate intelligent LLM response

        Args:
            query: User query
            domain: Domain for configuration
            language: Response language
            entities: Extracted entities
            query_type: Query type (standard, comparative, etc.)
            context_docs: Context documents
            temperature: Sampling temperature (optional, uses domain default)
            max_tokens: Max tokens (optional, auto-calculated if not provided)
            top_p: Nucleus sampling (optional)
            post_process: Apply post-processing
            add_disclaimer: Add veterinary disclaimer if applicable

        Returns:
            Tuple of (generated_text, prompt_tokens, completion_tokens, metadata)
        """
        try:
            request_data = {
                "query": query,
                "domain": domain,
                "language": language,
                "post_process": post_process,
                "add_disclaimer": add_disclaimer,
            }

            # Add optional parameters
            if entities:
                request_data["entities"] = entities
            if query_type:
                request_data["query_type"] = query_type
            if context_docs:
                request_data["context_docs"] = context_docs
            if temperature is not None:
                request_data["temperature"] = temperature
            if max_tokens is not None:
                request_data["max_tokens"] = max_tokens
            if top_p is not None:
                request_data["top_p"] = top_p

            logger.info(f"🔗 Calling LLM service /v1/generate for domain={domain}")

            response = await self.client.post(
                f"{self.base_url}/v1/generate", json=request_data
            )
            response.raise_for_status()
            data = response.json()

            metadata = {
                "provider": data.get("provider"),
                "model": data.get("model"),
                "complexity": data.get("complexity"),
                "calculated_max_tokens": data.get("calculated_max_tokens"),
                "post_processed": data.get("post_processed"),
                "disclaimer_added": data.get("disclaimer_added"),
            }

            logger.info(
                f"✓ LLM service response: {data['total_tokens']} tokens, "
                f"provider={metadata['provider']}, complexity={metadata['complexity']}"
            )

            return (
                data["generated_text"],
                data["prompt_tokens"],
                data["completion_tokens"],
                metadata,
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ LLM service HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"LLM service error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"❌ LLM service connection error: {e}")
            raise Exception(f"Cannot connect to LLM service at {self.base_url}")
        except Exception as e:
            logger.error(f"❌ LLM service client error: {e}", exc_info=True)
            raise

    async def generate_stream(
        self,
        query: str,
        domain: str = "aviculture",
        language: str = "en",
        entities: Optional[Dict[str, Any]] = None,
        query_type: Optional[str] = None,
        context_docs: Optional[List[Dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        post_process: bool = True,
        add_disclaimer: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate intelligent LLM response with streaming (Server-Sent Events)

        This method streams the response chunks as they are generated,
        providing a better user experience with reduced perceived latency.

        Args:
            query: User query
            domain: Domain for configuration
            language: Response language
            entities: Extracted entities
            query_type: Query type (standard, comparative, etc.)
            context_docs: Context documents
            temperature: Sampling temperature (optional, uses domain default)
            max_tokens: Max tokens (optional, auto-calculated if not provided)
            top_p: Nucleus sampling (optional)
            post_process: Apply post-processing
            add_disclaimer: Add veterinary disclaimer if applicable

        Yields:
            Dictionary with event data:
            - event="start": {"status": "generating", "complexity": "simple", ...}
            - event="chunk": {"content": "text chunk..."}
            - event="end": {"prompt_tokens": 100, "completion_tokens": 50, ...}
            - event="error": {"error": "error message"}
        """
        try:
            request_data = {
                "query": query,
                "domain": domain,
                "language": language,
                "post_process": post_process,
                "add_disclaimer": add_disclaimer,
            }

            # Add optional parameters
            if entities:
                request_data["entities"] = entities
            if query_type:
                request_data["query_type"] = query_type
            if context_docs:
                request_data["context_docs"] = context_docs
            if temperature is not None:
                request_data["temperature"] = temperature
            if max_tokens is not None:
                request_data["max_tokens"] = max_tokens
            if top_p is not None:
                request_data["top_p"] = top_p

            logger.info(
                f"[STREAM] Calling LLM service /v1/generate-stream for domain={domain}"
            )

            async with self.client.stream(
                "POST",
                f"{self.base_url}/v1/generate-stream",
                json=request_data,
                timeout=120.0,
            ) as response:
                response.raise_for_status()

                current_event = None
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue

                    # Parse SSE format
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()

                    elif line.startswith("data:"):
                        data_str = line.split(":", 1)[1].strip()

                        try:
                            event_data = json.loads(data_str)
                            event_data["event"] = current_event or "chunk"
                            yield event_data

                        except json.JSONDecodeError:
                            logger.warning(f"[STREAM] Invalid JSON in SSE: {data_str}")
                            continue

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[ERROR] LLM service streaming HTTP error: {e.response.status_code}"
            )
            yield {
                "event": "error",
                "error": f"LLM service error: {e.response.status_code}",
            }
        except httpx.RequestError as e:
            logger.error(f"[ERROR] LLM service streaming connection error: {e}")
            yield {
                "event": "error",
                "error": f"Cannot connect to LLM service at {self.base_url}",
            }
        except Exception as e:
            logger.error(
                f"[ERROR] LLM service streaming client error: {e}", exc_info=True
            )
            yield {"event": "error", "error": str(e)}

    async def route(
        self,
        query: str,
        domain: str = "aviculture",
        entities: Optional[Dict[str, Any]] = None,
        intent_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get provider routing recommendation

        Args:
            query: User query
            domain: Domain
            entities: Extracted entities
            intent_result: Intent classification result

        Returns:
            Dictionary with routing decision:
            {
                "provider": "intelia_llama",
                "model": "meta-llama/Llama-3.1-8B-Instruct",
                "reason": "Domain-specific query detected",
                "is_aviculture": True,
                "confidence": 0.9
            }
        """
        try:
            request_data = {
                "query": query,
                "domain": domain,
            }

            if entities:
                request_data["entities"] = entities
            if intent_result:
                request_data["intent_result"] = intent_result

            logger.debug("🔗 Calling LLM service /v1/route")

            response = await self.client.post(
                f"{self.base_url}/v1/route", json=request_data
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"❌ LLM service routing error: {e}")
            raise

    async def calculate_tokens(
        self,
        query: str,
        entities: Optional[Dict[str, Any]] = None,
        query_type: Optional[str] = None,
        context_docs: Optional[List[Dict]] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate optimal max_tokens

        Args:
            query: User query
            entities: Extracted entities
            query_type: Query type
            context_docs: Context documents
            domain: Domain

        Returns:
            Dictionary with token calculation:
            {
                "max_tokens": 750,
                "complexity": "moderate",
                "token_range": [600, 900],
                "factors": {...}
            }
        """
        try:
            request_data = {"query": query}

            if entities:
                request_data["entities"] = entities
            if query_type:
                request_data["query_type"] = query_type
            if context_docs:
                request_data["context_docs"] = context_docs
            if domain:
                request_data["domain"] = domain

            logger.debug("🔗 Calling LLM service /v1/calculate-tokens")

            response = await self.client.post(
                f"{self.base_url}/v1/calculate-tokens", json=request_data
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"❌ LLM service token calculation error: {e}")
            raise

    async def post_process(
        self,
        response: str,
        query: str = "",
        language: str = "en",
        domain: str = "aviculture",
        context_docs: Optional[List[Dict]] = None,
        add_disclaimer: bool = True,
    ) -> Tuple[str, bool, bool]:
        """
        Post-process LLM response

        Args:
            response: Raw LLM response
            query: Original query
            language: Response language
            domain: Domain
            context_docs: Context documents
            add_disclaimer: Add disclaimer if applicable

        Returns:
            Tuple of (processed_text, disclaimer_added, is_veterinary)
        """
        try:
            request_data = {
                "response": response,
                "query": query,
                "language": language,
                "domain": domain,
                "add_disclaimer": add_disclaimer,
            }

            if context_docs:
                request_data["context_docs"] = context_docs

            logger.debug("🔗 Calling LLM service /v1/post-process")

            response = await self.client.post(
                f"{self.base_url}/v1/post-process", json=request_data
            )
            response.raise_for_status()
            data = response.json()

            return (
                data["processed_text"],
                data["disclaimer_added"],
                data["is_veterinary"],
            )

        except Exception as e:
            logger.error(f"❌ LLM service post-processing error: {e}")
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Singleton instance
_llm_service_client = None


def get_llm_service_client(base_url: Optional[str] = None) -> LLMServiceClient:
    """
    Get or create LLM service client singleton

    Args:
        base_url: Base URL of LLM service

    Returns:
        LLMServiceClient instance
    """
    global _llm_service_client

    if _llm_service_client is None:
        _llm_service_client = LLMServiceClient(base_url=base_url)

    return _llm_service_client
