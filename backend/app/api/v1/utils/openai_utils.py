import os
import openai
from typing import Any, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai.error import RateLimitError, APIError, Timeout

# Configure OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

@retry(
    retry=retry_if_exception_type((RateLimitError, APIError, Timeout)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def safe_chat_completion(**kwargs: Any) -> Dict[str, Any]:
    """
    Wrapper for openai.ChatCompletion.create with retry/backoff.
    """
    return openai.ChatCompletion.create(**kwargs)

@retry(
    retry=retry_if_exception_type((RateLimitError, APIError, Timeout)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def safe_embedding_create(**kwargs: Any) -> Dict[str, Any]:
    """
    Wrapper for openai.Embedding.create with retry/backoff.
    """
    return openai.Embedding.create(**kwargs)
