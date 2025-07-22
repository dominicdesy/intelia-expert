#!/usr/bin/env python3
"""
Configuration Loader Module
Loads and manages system configuration and API keys.
"""

import os
import json
import toml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Loads and manages system configuration."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.secrets_file = self.project_root / ".streamlit" / "secrets.toml"
        self.config_file = self.project_root / "data" / "config.json"
        self._secrets = None
        self._config = None
    
    def _load_secrets(self) -> Dict[str, Any]:
        """Load secrets from streamlit config."""
        if self._secrets is not None:
            return self._secrets
        
        if not self.secrets_file.exists():
            print(f"Warning: Secrets file not found: {self.secrets_file}")
            self._secrets = {}
            return self._secrets
        
        try:
            self._secrets = toml.load(self.secrets_file)
        except Exception as e:
            print(f"Error loading secrets: {e}")
            self._secrets = {}
        
        return self._secrets
    
    def _load_config(self) -> Dict[str, Any]:
        """Load main configuration."""
        if self._config is not None:
            return self._config
        
        if not self.config_file.exists():
            print(f"Warning: Config file not found: {self.config_file}")
            self._config = {}
            return self._config
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            self._config = {}
        
        return self._config
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for a service."""
        secrets = self._load_secrets()
        
        key_mapping = {
            'openai': 'openai_key',
            'claude': 'claude_key',
            'compass': 'compass_token',
            'weather': 'weather_api_key'
        }
        
        key_name = key_mapping.get(service)
        if key_name and key_name in secrets:
            return secrets[key_name]
        
        # Fallback to environment variables
        env_name = f"{service.upper()}_API_KEY"
        return os.environ.get(env_name)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting."""
        config = self._load_config()
        
        # Support nested keys like "email_service.provider"
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def validate_config(self) -> Dict[str, Dict[str, Any]]:
        """Validate configuration and API keys."""
        secrets = self._load_secrets()
        
        required_keys = [
            'compass_token',
            'openai_key',
            'claude_key',
            'microsoft_graph_tenant_id',
            'microsoft_graph_client_id',
            'microsoft_graph_client_secret',
            'microsoft_graph_from_email',
            'weather_api_key'
        ]
        
        validation = {}
        
        for key in required_keys:
            result = {
                'present': key in secrets,
                'required': True,
                'value_length': len(str(secrets.get(key, ''))) if key in secrets else 0
            }
            
            if result['present'] and result['value_length'] > 5:
                result['status'] = 'ok'
            elif result['present']:
                result['status'] = 'too_short'
            else:
                result['status'] = 'missing'
            
            validation[key] = result
        
        return validation
    
    def get_config(self) -> 'ConfigLoader':
        """Get the config loader instance (for compatibility)."""
        return self


# Global configuration instance
_config_loader = None

def get_config() -> ConfigLoader:
    """Get global configuration loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader

def get_api_key(service: str) -> Optional[str]:
    """Get API key for a service."""
    return get_config().get_api_key(service)

def get_setting(key: str, default: Any = None) -> Any:
    """Get a configuration setting."""
    return get_config().get_setting(key, default)

def validate_config() -> Dict[str, Dict[str, Any]]:
    """Validate configuration and API keys."""
    return get_config().validate_config()


if __name__ == "__main__":
    # Test the module
    config = get_config()
    
    # Test API key retrieval
    openai_key = config.get_api_key('openai')
    print(f"OpenAI key available: {'Yes' if openai_key else 'No'}")
    
    # Test configuration validation
    validation = config.validate_config()
    print(f"Configuration validation: {len(validation)} keys checked")
    
    # Test settings
    email_provider = config.get_setting('email_service.provider', 'unknown')
    print(f"Email provider: {email_provider}")
