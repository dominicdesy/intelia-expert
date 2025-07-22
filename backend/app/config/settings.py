import os
import toml
from pathlib import Path
from typing import Optional

class Settings:
    """Application configuration settings with secrets.toml support."""
    
    def __init__(self):
        self.secrets = self._load_secrets()
    
    def _load_secrets(self):
        """Load secrets from .streamlit/secrets.toml."""
        try:
            # Try multiple paths for secrets.toml
            possible_paths = [
                Path(".streamlit/secrets.toml"),
                Path("../.streamlit/secrets.toml"),
                Path("../../.streamlit/secrets.toml"),
                Path("../../../.streamlit/secrets.toml")
            ]
            
            for path in possible_paths:
                if path.exists():
                    return toml.load(path)
            
            return {}
        except Exception:
            return {}
    
    def _get_secret(self, key: str, default=None):
        """Get value from secrets or environment."""
        if key in self.secrets:
            return self.secrets[key]
        return os.getenv(key, default)
    
    # App config
    PROJECT_NAME: str = "Intelia Expert API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API config
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "intelia-expert-dev-key"
    
    # Database config
    DATABASE_URL: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    
    # CORS config
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://intelia-expert.com"
    ]
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from secrets."""
        return self._get_secret("openai_key")
    
    @property
    def is_openai_configured(self) -> bool:
        """Check if OpenAI is configured."""
        key = self.openai_api_key
        return bool(key and len(key) > 10)

settings = Settings()