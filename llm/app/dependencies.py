"""
FastAPI Dependencies
Provides shared dependencies like LLM client
"""

from functools import lru_cache
from app.models.llm_client import LLMClient, get_llm_client as create_llm_client
from app.config import settings
import logging

logger = logging.getLogger(__name__)


@lru_cache()
def get_llm_client() -> LLMClient:
    """
    Dependency to get LLM client instance

    Cached to reuse the same client across requests.

    Returns:
        LLMClient instance configured based on settings

    Raises:
        ValueError: If configuration is invalid
    """
    logger.info(f"Initializing LLM client with provider: {settings.llm_provider}")

    if settings.llm_provider == "huggingface":
        if not settings.huggingface_api_key:
            raise ValueError("HUGGINGFACE_API_KEY environment variable is required")

        client = create_llm_client(
            provider="huggingface",
            api_key=settings.huggingface_api_key,
            model=settings.huggingface_model,
        )

    elif settings.llm_provider == "vllm":
        if not settings.vllm_url:
            raise ValueError("VLLM_URL environment variable is required")

        client = create_llm_client(
            provider="vllm",
            base_url=settings.vllm_url,
            model="intelia-llama-3.1-8b-aviculture",
        )

    else:
        raise ValueError(f"Unknown provider: {settings.llm_provider}")

    logger.info(f"LLM client initialized successfully")
    return client
