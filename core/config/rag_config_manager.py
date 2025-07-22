#!/usr/bin/env python3
"""
RAG Configuration Manager for Compass Project
Manages RAG system configuration using existing project keys.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class RAGConfigManager:
    """RAG configuration manager integrated with existing Compass project."""
    
    def __init__(self):
        self.project_root = Path.cwd()
    
    def detect_existing_configuration(self) -> Dict[str, Any]:
        """Detect existing project configuration."""
        config = {
            "openai_key": None,
            "compass_token": None,
            "secrets_file_exists": False,
            "rag_section_exists": False
        }
        
        secrets_file = self.project_root / ".streamlit" / "secrets.toml"
        if secrets_file.exists():
            config["secrets_file_exists"] = True
            
            try:
                import toml
                secrets = toml.load(secrets_file)
                config["openai_key"] = secrets.get("openai_key")
                config["compass_token"] = secrets.get("compass_token")
                config["rag_section_exists"] = "rag" in secrets
                logger.info("Configuration detected successfully")
            except ImportError:
                config = self._parse_secrets_manually(secrets_file)
        
        return config
    
    def _parse_secrets_manually(self, secrets_file: Path) -> Dict[str, Any]:
        """Manual parsing of secrets.toml if toml module unavailable."""
        config = {
            "openai_key": None,
            "compass_token": None,
            "secrets_file_exists": True,
            "rag_section_exists": False
        }
        
        try:
            with open(secrets_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'openai_key' in content and '=' in content:
                config["openai_key"] = "detected"
            if 'compass_token' in content and '=' in content:
                config["compass_token"] = "detected"
            if '[rag]' in content:
                config["rag_section_exists"] = True
                
        except Exception as e:
            logger.error(f"Manual parsing failed: {e}")
        
        return config
    
    def detect_optimal_rag_method(self, existing_config: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Detect optimal RAG method based on existing configuration."""
        
        # Priority 1: OpenAI if key available
        if existing_config.get("openai_key"):
            config = {
                "embedding_method": "OpenAI",
                "model_name": "text-embedding-ada-002",
                "use_existing_key": True,
                "dimension": 1536,
                "source": "existing_secrets"
            }
            logger.info("RAG Config: Using existing OpenAI key")
            return "OpenAI", config
        
        # Priority 2: Check environment variable
        if os.environ.get("OPENAI_API_KEY"):
            config = {
                "embedding_method": "OpenAI",
                "model_name": "text-embedding-ada-002",
                "use_existing_key": False,
                "dimension": 1536,
                "source": "environment"
            }
            logger.info("RAG Config: Using OpenAI key from environment")
            return "OpenAI", config
        
        # Priority 3: SentenceTransformers fallback
        if self._check_sentence_transformers():
            config = {
                "embedding_method": "SentenceTransformers",
                "model_name": "all-MiniLM-L6-v2",
                "use_local_embeddings": True,
                "dimension": 384,
                "source": "local_model"
            }
            logger.info("RAG Config: Using local SentenceTransformers")
            return "SentenceTransformers", config
        
        # Fallback: Disable RAG
        config = {
            "embedding_method": "disabled",
            "use_rag": False,
            "fallback_mode": True,
            "source": "none_available"
        }
        logger.warning("RAG Config: Disabled - no suitable method available")
        return "disabled", config
    
    def _check_sentence_transformers(self) -> bool:
        """Check if sentence-transformers is installed."""
        try:
            import sentence_transformers
            return True
        except ImportError:
            return False
    
    def update_secrets_with_rag_config(self, rag_config: Dict[str, Any]) -> bool:
        """Update secrets.toml with optimal RAG configuration."""
        secrets_file = self.project_root / ".streamlit" / "secrets.toml"
        
        if not secrets_file.exists():
            logger.error("secrets.toml file not found")
            return False
        
        try:
            with open(secrets_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if '[rag]' in content:
                logger.info("RAG section already exists in secrets.toml")
                return True
            
            rag_section = f"""

# RAG Configuration (Auto-generated)
[rag]
embedding_method = "{rag_config.get('embedding_method', 'OpenAI')}"
model_name = "{rag_config.get('model_name', 'text-embedding-ada-002')}"
enabled = true
chunk_size = 256
overlap = 64
max_results = 5
dimension = {rag_config.get('dimension', 1536)}
"""
            
            # Backup and update
            backup_file = secrets_file.with_suffix('.toml.backup')
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            with open(secrets_file, 'w', encoding='utf-8') as f:
                f.write(content + rag_section)
            
            logger.info("RAG configuration added to secrets.toml")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update secrets.toml: {e}")
            return False
    
    def apply_rag_environment_variables(self, method: str, config: Dict[str, Any]) -> None:
        """Apply environment variables for RAG system."""
        if method == "OpenAI":
            os.environ["RAG_EMBEDDING_METHOD"] = "OpenAI"
            os.environ["RAG_MODEL_NAME"] = "text-embedding-ada-002"
            os.environ["RAG_ENABLED"] = "true"
            
            if config.get("use_existing_key"):
                existing_key = self._get_openai_key_from_secrets()
                if existing_key:
                    os.environ["OPENAI_API_KEY"] = existing_key
        
        elif method == "SentenceTransformers":
            os.environ["RAG_EMBEDDING_METHOD"] = "SentenceTransformers"
            os.environ["RAG_MODEL_NAME"] = "all-MiniLM-L6-v2"
            os.environ["RAG_ENABLED"] = "true"
        
        else:
            os.environ["RAG_ENABLED"] = "false"
            os.environ["USE_RAG"] = "false"
    
    def _get_openai_key_from_secrets(self) -> Optional[str]:
        """Get OpenAI key from existing secrets file."""
        try:
            import streamlit as st
            return st.secrets.get("openai_key")
        except:
            pass
        
        try:
            import toml
            secrets_file = self.project_root / ".streamlit" / "secrets.toml"
            if secrets_file.exists():
                secrets = toml.load(secrets_file)
                return secrets.get("openai_key")
        except:
            pass
        
        return None
    
    def configure_project_rag(self) -> Dict[str, Any]:
        """Complete RAG configuration for Compass project."""
        logger.info("Configuring RAG for Compass project...")
        
        # Detect existing configuration
        existing_config = self.detect_existing_configuration()
        
        # Detect optimal RAG method
        method, rag_config = self.detect_optimal_rag_method(existing_config)
        
        # Update secrets.toml if necessary
        if not existing_config["rag_section_exists"] and method != "disabled":
            self.update_secrets_with_rag_config(rag_config)
        
        # Apply environment variables
        self.apply_rag_environment_variables(method, rag_config)
        
        # Generate configuration report
        report = {
            "rag_method": method,
            "rag_config": rag_config,
            "existing_config": existing_config,
            "environment_configured": True,
            "integration_status": "success" if method != "disabled" else "disabled"
        }
        
        logger.info(f"RAG configuration applied: {method}")
        return report


def configure_compass_rag() -> Dict[str, Any]:
    """Entry point for Compass RAG configuration."""
    manager = RAGConfigManager()
    return manager.configure_project_rag()


def print_compass_rag_status():
    """Display RAG configuration status for Compass."""
    manager = RAGConfigManager()
    existing_config = manager.detect_existing_configuration()
    method, rag_config = manager.detect_optimal_rag_method(existing_config)
    
    print("\n" + "="*60)
    print("RAG CONFIGURATION STATUS - COMPASS PROJECT")
    print("="*60)
    
    print(f"Secrets file: {'Found' if existing_config['secrets_file_exists'] else 'Missing'}")
    print(f"OpenAI key: {'Configured' if existing_config['openai_key'] else 'Missing'}")
    print(f"RAG section: {'Present' if existing_config['rag_section_exists'] else 'To be added'}")
    
    print(f"\nOptimal RAG method: {method}")
    print(f"Source: {rag_config.get('source', 'unknown')}")
    
    if method == "disabled":
        print(f"\nRECOMMENDATIONS:")
        print(f"  • Configure OpenAI key in secrets.toml")
        print(f"  • Or install: pip install sentence-transformers")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    print("Configuring RAG for Compass project...")
    report = configure_compass_rag()
    
    print_compass_rag_status()
    
    if report["integration_status"] == "success":
        print("\nRAG CONFIGURATION SUCCESSFUL!")
        print("The error 'Unknown embedding method: sentence_transformers' should be resolved.")
        print("Restart the application to apply changes.")
    else:
        print("\nRAG DISABLED - API key configuration recommended")
    
    print("="*60)
