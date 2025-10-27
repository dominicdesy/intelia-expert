"""
Configuration Management
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Service info
    service_name: str = "llm"
    version: str = "1.0.0"

    # Server
    port: int = 8081
    host: str = "0.0.0.0"
    log_level: str = "INFO"

    # LLM Provider
    llm_provider: Literal["huggingface", "vllm"] = "huggingface"

    # HuggingFace (Phase 1)
    huggingface_api_key: str = ""
    huggingface_model: str = "meta-llama/Llama-3.1-8B-Instruct"

    # vLLM (Phase 2 - Self-hosted)
    vllm_url: str = "http://localhost:8000"

    # Monitoring
    enable_metrics: bool = True

    # Optional: Langfuse tracing
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
