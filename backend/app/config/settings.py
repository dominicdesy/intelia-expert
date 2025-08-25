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
    
    # ✅ FIX: Database config avec environment variables
    @property
    def database_url(self) -> Optional[str]:
        """Get database URL from environment."""
        return self._get_secret("DATABASE_URL")
    
    @property 
    def supabase_url(self) -> Optional[str]:
        """Get Supabase URL from environment."""
        return self._get_secret("SUPABASE_URL")
    
    @property
    def supabase_anon_key(self) -> Optional[str]:
        """Get Supabase anon key from environment."""
        return self._get_secret("SUPABASE_ANON_KEY")
    
    @property
    def supabase_jwt_secret(self) -> Optional[str]:
        """Get Supabase JWT secret from environment."""
        return self._get_secret("SUPABASE_JWT_SECRET")
    
    # CORS config
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://intelia-expert.com"
    ]
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from secrets."""
        return self._get_secret("openai_key") or self._get_secret("OPENAI_API_KEY")
    
    @property
    def is_openai_configured(self) -> bool:
        """Check if OpenAI is configured."""
        key = self.openai_api_key
        return bool(key and len(key) > 10)
    
    @property
    def is_supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.supabase_url and self.supabase_anon_key)
    
    # ==================== CONFIGURATION MODÈLES OPENAI ====================
    
    @property
    def default_model(self) -> str:
        """Get default OpenAI model."""
        return self._get_secret("DEFAULT_MODEL", "gpt-5")
    
    @property
    def clarification_model(self) -> str:
        """Get clarification model."""
        return self._get_secret("CLARIFICATION_MODEL", "gpt-5-mini")
    
    @property
    def cot_model(self) -> str:
        """Get Chain-of-Thought model."""
        return self._get_secret("OPENAI_COT_MODEL", self.default_model)
    
    @property
    def synthesis_model(self) -> str:
        """Get synthesis model."""
        return self._get_secret("OPENAI_SYNTHESIS_MODEL", self.default_model)
    
    @property
    def chat_model(self) -> str:
        """Get chat model."""
        return self._get_secret("OPENAI_CHAT_MODEL", self.default_model)
    
    @property
    def embedding_model(self) -> str:
        """Get embedding model."""
        return self._get_secret("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    @property
    def fallback_model(self) -> str:
        """Get fallback model."""
        return self._get_secret("OPENAI_FALLBACK_MODEL", "gpt-4o")
    
    # ==================== CONFIGURATION VALIDATION AGRICOLE ====================
    
    @property
    def agricultural_validation_enabled(self) -> bool:
        """Check if agricultural domain validation is enabled."""
        return self._get_secret("ENABLE_AGRICULTURAL_VALIDATION", "true").lower() == "true"
    
    @property
    def agricultural_validation_strictness(self) -> float:
        """Get agricultural validation strictness threshold (0-100)."""
        try:
            return float(self._get_secret("VALIDATION_STRICTNESS", "15.0"))
        except (ValueError, TypeError):
            return 15.0
    
    @property
    def agricultural_validation_override_allowed(self) -> bool:
        """Check if users can override agricultural validation."""
        return self._get_secret("ALLOW_VALIDATION_OVERRIDE", "false").lower() == "true"
    
    @property
    def agricultural_validation_log_all(self) -> bool:
        """Check if all validations should be logged."""
        return self._get_secret("LOG_ALL_VALIDATIONS", "true").lower() == "true"
    
    @property
    def agricultural_validation_log_dir(self) -> str:
        """Get directory for agricultural validation logs."""
        return self._get_secret("VALIDATION_LOGS_DIR", "logs")
    
    @property
    def agricultural_validation_log_max_size(self) -> int:
        """Get max size for validation log files in bytes."""
        try:
            return int(self._get_secret("VALIDATION_LOG_MAX_SIZE", "10485760"))  # 10MB
        except (ValueError, TypeError):
            return 10485760
    
    @property
    def agricultural_validation_log_backup_count(self) -> int:
        """Get number of backup log files to keep."""
        try:
            return int(self._get_secret("VALIDATION_LOG_BACKUP_COUNT", "5"))
        except (ValueError, TypeError):
            return 5
    
    @property
    def is_agricultural_validation_configured(self) -> bool:
        """Check if agricultural validation is properly configured."""
        return (
            self.agricultural_validation_enabled and
            0 <= self.agricultural_validation_strictness <= 100
        )

    # ==================== CONFIGURATION SYSTÈME DE CLARIFICATION ====================
    
    @property
    def clarification_system_enabled(self) -> bool:
        """Check if question clarification system is enabled."""
        return self._get_secret("ENABLE_CLARIFICATION_SYSTEM", "true").lower() == "true"
    
    @property
    def clarification_timeout(self) -> int:
        """Get timeout for clarification analysis in seconds."""
        try:
            return int(self._get_secret("CLARIFICATION_TIMEOUT", "20"))
        except (ValueError, TypeError):
            return 20
    
    @property
    def clarification_max_questions(self) -> int:
        """Get maximum number of clarification questions to generate."""
        try:
            return int(self._get_secret("CLARIFICATION_MAX_QUESTIONS", "3"))
        except (ValueError, TypeError):
            return 3
    
    @property
    def clarification_min_length(self) -> int:
        """Get minimum question length to trigger clarification analysis."""
        try:
            return int(self._get_secret("CLARIFICATION_MIN_LENGTH", "15"))
        except (ValueError, TypeError):
            return 15
    
    @property
    def clarification_confidence_threshold(self) -> float:
        """Get confidence threshold for clarification decisions (0.0-1.0)."""
        try:
            return float(self._get_secret("CLARIFICATION_CONFIDENCE_THRESHOLD", "0.7"))
        except (ValueError, TypeError):
            return 0.7
    
    @property
    def clarification_log_all(self) -> bool:
        """Check if all clarification decisions should be logged."""
        return self._get_secret("LOG_ALL_CLARIFICATIONS", "true").lower() == "true"
    
    @property
    def is_clarification_system_configured(self) -> bool:
        """Check if clarification system is properly configured."""
        return (
            self.clarification_system_enabled and
            self.is_openai_configured and
            0.0 <= self.clarification_confidence_threshold <= 1.0
        )

    # ==================== CONFIGURATION MÉMOIRE CONVERSATIONNELLE ====================
    
    @property
    def conversation_memory_enabled(self) -> bool:
        """Check if conversational memory system is enabled."""
        return self._get_secret("ENABLE_CONVERSATION_MEMORY", "true").lower() == "true"
    
    @property
    def conversation_max_messages(self) -> int:
        """Get maximum messages to keep in conversation memory."""
        try:
            return int(self._get_secret("CONVERSATION_MAX_MESSAGES", "20"))
        except (ValueError, TypeError):
            return 20
    
    @property
    def conversation_expiry_hours(self) -> int:
        """Get conversation expiry time in hours."""
        try:
            return int(self._get_secret("CONVERSATION_EXPIRY_HOURS", "24"))
        except (ValueError, TypeError):
            return 24
    
    @property
    def entity_extraction_enabled(self) -> bool:
        """Check if entity extraction is enabled."""
        return self._get_secret("ENABLE_ENTITY_EXTRACTION", "true").lower() == "true"
    
    @property
    def memory_db_path(self) -> str:
        """Get path for conversation memory database."""
        return self._get_secret("MEMORY_DB_PATH", "data/conversation_memory.db")
    
    @property
    def is_conversation_memory_configured(self) -> bool:
        """Check if conversation memory is properly configured."""
        return (
            self.conversation_memory_enabled and
            self.conversation_max_messages > 0 and
            self.conversation_expiry_hours > 0
        )

    # ==================== CONFIGURATION GÉNÉRALE SYSTÈME ====================
    
    @property
    def system_name(self) -> str:
        """Get system display name."""
        return self._get_secret("SYSTEM_NAME", "Intelia Expert")
    
    @property
    def system_version(self) -> str:
        """Get system version."""
        return self._get_secret("SYSTEM_VERSION", "2.0.0")
    
    @property
    def environment(self) -> str:
        """Get deployment environment."""
        return self._get_secret("ENVIRONMENT", "development")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._get_secret("LOG_LEVEL", "INFO")
    
    # ==================== MÉTHODES UTILITAIRES ====================
    
    def get_system_status(self) -> dict:
        """Get complete system configuration status."""
        return {
            "system": {
                "name": self.system_name,
                "version": self.system_version,
                "environment": self.environment,
                "is_production": self.is_production
            },
            "openai": {
                "configured": self.is_openai_configured,
                "api_key_present": bool(self.openai_api_key),
                "models": {
                    "default": self.default_model,
                    "clarification": self.clarification_model,
                    "cot": self.cot_model,
                    "synthesis": self.synthesis_model,
                    "chat": self.chat_model,
                    "embedding": self.embedding_model,
                    "fallback": self.fallback_model
                }
            },
            "supabase": {
                "configured": self.is_supabase_configured,
                "url_present": bool(self.supabase_url),
                "key_present": bool(self.supabase_anon_key)
            },
            "agricultural_validation": {
                "enabled": self.agricultural_validation_enabled,
                "configured": self.is_agricultural_validation_configured,
                "strictness": self.agricultural_validation_strictness
            },
            "clarification_system": {
                "enabled": self.clarification_system_enabled,
                "configured": self.is_clarification_system_configured,
                "model": self.clarification_model,
                "confidence_threshold": self.clarification_confidence_threshold
            },
            "conversation_memory": {
                "enabled": self.conversation_memory_enabled,
                "configured": self.is_conversation_memory_configured,
                "max_messages": self.conversation_max_messages,
                "expiry_hours": self.conversation_expiry_hours
            }
        }
    
    def validate_configuration(self) -> tuple[bool, list]:
        """Validate all system configuration and return status and issues."""
        issues = []
        
        # Vérifications critiques
        if not self.is_openai_configured:
            issues.append("OpenAI API key missing or invalid")
        
        if not self.is_supabase_configured:
            issues.append("Supabase configuration incomplete")
        
        if self.agricultural_validation_enabled and not self.is_agricultural_validation_configured:
            issues.append("Agricultural validation enabled but misconfigured")
        
        if self.clarification_system_enabled and not self.is_clarification_system_configured:
            issues.append("Clarification system enabled but misconfigured")
        
        if self.conversation_memory_enabled and not self.is_conversation_memory_configured:
            issues.append("Conversation memory enabled but misconfigured")
        
        # Vérifications de cohérence
        if self.clarification_confidence_threshold < 0.1 or self.clarification_confidence_threshold > 0.95:
            issues.append(f"Clarification confidence threshold unusual: {self.clarification_confidence_threshold}")
        
        if self.agricultural_validation_strictness < 5.0 or self.agricultural_validation_strictness > 50.0:
            issues.append(f"Agricultural validation strictness unusual: {self.agricultural_validation_strictness}")
        
        return len(issues) == 0, issues

# Instance globale
settings = Settings()