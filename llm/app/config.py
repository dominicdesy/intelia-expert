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

    # ⚡ OPTIMIZATION: Model Routing (Option 3)
    # Enable intelligent routing between 3B (fast) and 8B (accurate)
    enable_model_routing: bool = False  # Set to True to enable
    model_3b_name: str = "meta-llama/Llama-3.2-3B-Instruct"
    model_8b_name: str = "meta-llama/Llama-3.1-8B-Instruct"
    # A/B test ratio for medium complexity queries (0.0-1.0)
    # 0.0 = all medium queries to 8B, 1.0 = all medium queries to 3B
    ab_test_ratio: float = 0.5  # 50% to 3B, 50% to 8B

    # Response Caching (Option 1)
    cache_enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""  # For Redis Cloud authentication
    cache_ttl: int = 3600  # 1 hour

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
