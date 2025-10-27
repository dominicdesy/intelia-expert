"""
LLM Client - Provider Abstraction Layer
Supports HuggingFace Inference API and vLLM (self-hosted)
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from huggingface_hub import InferenceClient
import httpx

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 1.0,
        stop: List[str] | None = None,
    ) -> Tuple[str, int, int]:
        """
        Generate completion from messages

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stop: Stop sequences

        Returns:
            Tuple of (generated_text, prompt_tokens, completion_tokens)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass


class HuggingFaceProvider(LLMClient):
    """
    HuggingFace Inference API Provider (Serverless)
    Phase 1: Pay-per-use, no dedicated infrastructure
    """

    def __init__(self, api_key: str, model: str):
        """
        Initialize HuggingFace provider

        Args:
            api_key: HuggingFace API token (starts with hf_)
            model: Model ID (e.g., meta-llama/Llama-3.1-8B-Instruct)
        """
        if not api_key:
            raise ValueError("HuggingFace API key is required")

        self.api_key = api_key
        self.model = model
        self.client = InferenceClient(token=api_key)

        logger.info(f"HuggingFace provider initialized with model: {model}")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 1.0,
        stop: List[str] | None = None,
    ) -> Tuple[str, int, int]:
        """
        Generate completion using HuggingFace Inference API

        Note: Token counting is estimated (HF API doesn't return exact counts)
        """
        try:
            logger.info(f"Calling HuggingFace API for model: {self.model}")

            # Call HuggingFace Inference API (updated API method)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stop=stop if stop else [],
            )

            # Extract generated text
            generated_text = response.choices[0].message.content

            # Estimate token counts (HF API doesn't provide exact counts)
            prompt_tokens = self._estimate_tokens(messages)
            completion_tokens = self._estimate_tokens([{"role": "assistant", "content": generated_text}])

            logger.info(f"Generation successful. Tokens: ~{prompt_tokens}+{completion_tokens}")

            return generated_text, prompt_tokens, completion_tokens

        except Exception as e:
            logger.error(f"HuggingFace API error: {e}", exc_info=True)
            raise Exception(f"HuggingFace generation failed: {str(e)}")

    def is_available(self) -> bool:
        """Check if HuggingFace API is available"""
        try:
            # Simple test call (updated API method)
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
            )
            return True
        except Exception as e:
            logger.warning(f"HuggingFace availability check failed: {e}")
            return False

    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate token count (rough approximation)
        Rule of thumb: 1 token ≈ 4 characters for English
        """
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return int(total_chars / 4)


class vLLMProvider(LLMClient):
    """
    vLLM Provider (Self-hosted)
    Phase 2: For cost optimization and full control
    """

    def __init__(self, base_url: str, model_name: str = "intelia-llama-3.1-8b-aviculture"):
        """
        Initialize vLLM provider

        Args:
            base_url: vLLM server URL (e.g., http://localhost:8000)
            model_name: Model identifier
        """
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.client = httpx.AsyncClient(timeout=60.0)

        logger.info(f"vLLM provider initialized: {base_url}")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 1.0,
        stop: List[str] | None = None,
    ) -> Tuple[str, int, int]:
        """
        Generate completion using vLLM server (OpenAI-compatible API)
        """
        try:
            logger.info(f"Calling vLLM server: {self.base_url}")

            # vLLM exposes OpenAI-compatible API
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "stop": stop if stop else [],
                },
            )

            response.raise_for_status()
            data = response.json()

            # Extract response
            generated_text = data["choices"][0]["message"]["content"]
            prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0)
            completion_tokens = data.get("usage", {}).get("completion_tokens", 0)

            logger.info(f"vLLM generation successful. Tokens: {prompt_tokens}+{completion_tokens}")

            return generated_text, prompt_tokens, completion_tokens

        except httpx.HTTPError as e:
            logger.error(f"vLLM HTTP error: {e}", exc_info=True)
            raise Exception(f"vLLM generation failed: {str(e)}")
        except Exception as e:
            logger.error(f"vLLM error: {e}", exc_info=True)
            raise Exception(f"vLLM generation failed: {str(e)}")

    def is_available(self) -> bool:
        """Check if vLLM server is available"""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"vLLM availability check failed: {e}")
            return False


# ============================================
# FACTORY
# ============================================

def get_llm_client(
    provider: str,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> LLMClient:
    """
    Factory function to create LLM client

    Args:
        provider: "huggingface" or "vllm"
        api_key: API key for HuggingFace
        model: Model ID for HuggingFace
        base_url: Base URL for vLLM

    Returns:
        LLMClient instance

    Raises:
        ValueError: If provider is unknown or config is invalid
    """
    if provider == "huggingface":
        if not api_key:
            raise ValueError("HuggingFace API key is required")
        if not model:
            raise ValueError("HuggingFace model ID is required")
        return HuggingFaceProvider(api_key=api_key, model=model)

    elif provider == "vllm":
        if not base_url:
            raise ValueError("vLLM base URL is required")
        return vLLMProvider(base_url=base_url, model_name=model or "intelia-llama")

    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'huggingface' or 'vllm'")
