"""
app/services/expert_service.py - Version Corrigée pour DigitalOcean
Suppression de la dépendance secrets.toml et adaptation aux variables d'environnement
CORRIGÉ: Erreur F401 résolue avec importlib.util
"""

import os
import sys
import logging
import importlib.util
from ..api.v1.utils.openai_utils import complete
from typing import Optional, Dict, Any
from datetime import datetime

# Add parent directory to path for core imports
from pathlib import Path

current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class DigitalOceanSecretsLoader:
    """Load secrets from DigitalOcean environment variables."""

    def __init__(self):
        self.secrets = {}
        self._load_secrets()

    def _load_secrets(self):
        """Load secrets from environment variables."""
        try:
            # Map DigitalOcean environment variables to expected format
            self.secrets = {
                "openai_key": os.getenv("OPENAI_API_KEY"),
                "supabase_url": os.getenv("SUPABASE_URL"),
                "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY"),
                "rag": {
                    "embedding_method": os.getenv("RAG_EMBEDDING_MODEL", "OpenAI"),
                    "lazy_loading": os.getenv("RAG_LAZY_LOADING", "true").lower()
                    == "true",
                    "cache_embeddings": os.getenv(
                        "RAG_CACHE_EMBEDDINGS", "true"
                    ).lower()
                    == "true",
                    "memory_cache": os.getenv("RAG_MEMORY_CACHE", "true").lower()
                    == "true",
                },
            }

            # Count configured variables
            configured_vars = sum(
                1
                for v in [
                    self.secrets["openai_key"],
                    self.secrets["supabase_url"],
                    self.secrets["supabase_anon_key"],
                ]
                if v
            )

            logger.info(
                f"✅ Secrets loaded from DigitalOcean environment ({configured_vars}/3 variables configured)"
            )

        except Exception as e:
            logger.error(f"⛔ Error loading environment variables: {e}")
            self.secrets = {}

    def get(self, key: str, default=None):
        """Get secret value from environment variables."""
        # Direct environment variable lookup first
        env_value = os.getenv(key, None)
        if env_value:
            return env_value

        # Then check mapped secrets
        if key in self.secrets:
            return self.secrets[key]

        return default


class OptimizedRAGManager:
    """Optimized RAG manager for DigitalOcean deployment."""

    def __init__(self, secrets_loader):
        self.secrets = secrets_loader
        self.rag_available = False
        self.rag_configured = False
        self.rag_method = "none"
        self.diagnostic_info = {}
        self._attempt_rag_setup()

    def _attempt_rag_setup(self):
        """Attempt to setup RAG system with DigitalOcean paths."""
        diagnostics = {
            "environment": "digitalocean",
            "rag_index_path_exists": False,
            "embedding_method": "OpenAI",
            "openai_key_available": bool(self.secrets.get("OPENAI_API_KEY")),
            "rag_directory_structure": [],
            "errors": [],
        }

        try:
            # Check DigitalOcean workspace paths
            possible_rag_paths = [
                "/workspace/backend/rag_index",
                "/workspace/rag_index",
                "./rag_index",
                "../rag_index",
            ]

            rag_path_found = None
            for path in possible_rag_paths:
                if Path(path).exists():
                    rag_path_found = path
                    diagnostics["rag_index_path_exists"] = True

                    # List directory contents
                    try:
                        contents = list(Path(path).iterdir())
                        diagnostics["rag_directory_structure"] = [
                            f.name for f in contents
                        ]
                        logger.info(
                            f"✅ RAG index found at {path} with {len(contents)} files"
                        )
                    except Exception as e:
                        diagnostics["errors"].append(
                            f"Error reading RAG directory: {e}"
                        )

                    break

            if rag_path_found:
                # Check for required RAG files
                required_files = ["index.faiss", "index.pkl", "embeddings.npy"]
                existing_files = [
                    f
                    for f in diagnostics["rag_directory_structure"]
                    if any(req in f for req in required_files)
                ]

                if existing_files:
                    self.rag_available = True
                    self.rag_configured = True
                    self.rag_method = "FAISS_local"
                    diagnostics["rag_files_found"] = existing_files
                    logger.info(f"✅ RAG fully configured with files: {existing_files}")
                else:
                    diagnostics["errors"].append(
                        "RAG directory exists but missing required files"
                    )
                    logger.warning("⚠️ RAG directory exists but missing required files")
            else:
                diagnostics["errors"].append(
                    "No RAG index directory found in expected paths"
                )
                logger.warning("⚠️ No RAG index directory found")

            # CORRECTION F401: Utiliser importlib.util pour tester la disponibilité
            try:
                if importlib.util.find_spec("app.core.expert_engine") is not None:
                    diagnostics["expert_engine_available"] = True
                    logger.info("✅ Expert engine available as fallback")
                else:
                    diagnostics["expert_engine_available"] = False
                    diagnostics["errors"].append("Expert engine module not found")
            except (ImportError, ModuleNotFoundError):
                diagnostics["expert_engine_available"] = False
                diagnostics["errors"].append("Expert engine not available")

        except Exception as e:
            diagnostics["errors"].append(f"RAG setup error: {e}")
            logger.error(f"⛔ RAG setup error: {e}")

        self.diagnostic_info = diagnostics

    def force_configure_rag(self):
        """Force RAG reconfiguration."""
        try:
            logger.info("🔄 Forcing RAG reconfiguration...")
            self._attempt_rag_setup()

            if self.rag_configured:
                return {
                    "success": True,
                    "message": "RAG reconfigured successfully",
                    "method": self.rag_method,
                    "diagnostics": self.diagnostic_info,
                }
            else:
                return {
                    "success": False,
                    "message": "RAG reconfiguration failed",
                    "diagnostics": self.diagnostic_info,
                }

        except Exception as e:
            logger.error(f"⛔ Force RAG configuration error: {e}")
            return {
                "success": False,
                "error": str(e),
                "diagnostics": self.diagnostic_info,
            }

    def get_rag_context(self, question: str) -> Optional[str]:
        """Get RAG context for a question if available."""
        if not self.rag_configured:
            return None

        try:
            # CORRECTION F401: Import seulement si nécessaire et utiliser directement
            if importlib.util.find_spec("app.core.expert_engine") is not None:
                from app.core.expert_engine import InteliaExpertEngine

                engine = InteliaExpertEngine()

                if engine.rag_configured:
                    return f"[RAG Context Available - Method: {engine.rag_status}]"
                else:
                    return f"[RAG Index Available - Method: {self.rag_method}]"
            else:
                return f"[RAG Available - Method: {self.rag_method}]"

        except Exception as e:
            logger.warning(f"RAG context lookup failed: {e}")
            return f"[RAG Available - Method: {self.rag_method}]"

    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed RAG status with diagnostics."""
        return {
            "rag_available": self.rag_available,
            "rag_configured": self.rag_configured,
            "rag_method": self.rag_method,
            "diagnostics": self.diagnostic_info,
            "secrets_loaded": bool(self.secrets.secrets),
            "openai_key_available": bool(self.secrets.get("OPENAI_API_KEY")),
        }


class ExpertService:
    """Production-ready expert service for DigitalOcean."""

    def __init__(self):
        self.secrets = DigitalOceanSecretsLoader()
        self.openai_client = None
        self.rag_manager = OptimizedRAGManager(self.secrets)
        self.expert_engine = None

        # Initialize services
        self._initialize_openai()
        self._initialize_expert_engine()

    def _initialize_openai(self):
        """Initialize OpenAI client with environment variables."""
        try:
            import openai

            openai_key = self.secrets.get("OPENAI_API_KEY")

            if openai_key:
                self.openai_client = openai.OpenAI(api_key=openai_key)
                logger.info("✅ OpenAI client initialized from environment")
            else:
                logger.error("⛔ OPENAI_API_KEY not found in environment variables")

        except ImportError:
            logger.error("⛔ OpenAI package not available")
        except Exception as e:
            logger.error(f"⛔ OpenAI initialization error: {e}")

    def _initialize_expert_engine(self):
        """Initialize expert engine if available."""
        try:
            # CORRECTION F401: Import conditionnel avec vérification
            if importlib.util.find_spec("app.core.expert_engine") is not None:
                from app.core.expert_engine import InteliaExpertEngine

                self.expert_engine = InteliaExpertEngine()
                logger.info("✅ Expert engine initialized")
            else:
                logger.warning("⚠️ Expert engine module not found, using direct OpenAI")
        except ImportError:
            logger.warning("⚠️ Expert engine not available, using direct OpenAI")
        except Exception as e:
            logger.error(f"⛔ Expert engine initialization error: {e}")

    async def ask_expert(self, question: str, language: str = "en") -> Dict[str, Any]:
        """Ask question to expert with enhanced capabilities."""
        try:
            start_time = datetime.now()

            # Try expert engine first
            if self.expert_engine:
                try:
                    result = await self.expert_engine.process_query(
                        question, os.getenv("DEFAULT_MODEL", "gpt-5")
                    )

                    return {
                        "success": True,
                        "response": result.get("response", "No response generated"),
                        "rag_used": result.get("rag_configured", False),
                        "rag_available": self.rag_manager.rag_available,
                        "rag_configured": result.get("rag_configured", False),
                        "method": "expert_engine_enhanced",
                        "processing_time": result.get("processing_time", 0),
                        "timestamp": self._get_timestamp(),
                    }
                except Exception as e:
                    logger.warning(
                        f"Expert engine failed, falling back to direct OpenAI: {e}"
                    )

            # Fallback to direct OpenAI
            rag_context = self.rag_manager.get_rag_context(question)
            rag_used = bool(rag_context)

            response = await self._get_enhanced_response(
                question, language, rag_context
            )
            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "response": response,
                "rag_used": rag_used,
                "rag_available": self.rag_manager.rag_available,
                "rag_configured": self.rag_manager.rag_configured,
                "method": "direct_openai_with_rag" if rag_used else "direct_openai",
                "processing_time": processing_time,
                "timestamp": self._get_timestamp(),
            }

        except Exception as e:
            logger.error(f"Expert service error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp(),
            }

    async def _get_enhanced_response(
        self, question: str, language: str, rag_context: Optional[str]
    ) -> str:
        """Get enhanced response with optional RAG context."""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")

        # Build enhanced system prompt
        system_prompt = self._build_system_prompt(language, bool(rag_context))

        # Build user message with optional RAG context
        user_message = question
        if rag_context:
            user_message = f"{rag_context}\n\nQuestion: {question}"

        try:
            response_dict = complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                model=os.getenv("DEFAULT_MODEL", "gpt-5"),
                temperature=0.3,
                max_tokens=150,
            )
            return response_dict["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"Failed to get AI response: {str(e)}")

    def _build_system_prompt(self, language: str, has_rag: bool) -> str:
        """Build enhanced system prompt."""
        if language == "fr":
            base_prompt = """Vous êtes un expert spécialisé en gestion de poulets de chair Ross 308.

STYLE DE RÉPONSE OBLIGATOIRE:
- Réponse COURTE et DIRECTE (maximum 2-3 phrases)
- Aller droit au but, sans explication de logique
- Donner la réponse concrète immédiatement
- PAS de citations de documents
- PAS d'explications sur "comment j'ai déterminé"
- Ton professionnel mais concis

Répondez en français de manière:
- Précise et scientifiquement fondée
- Pratique et actionnable
- Avec des recommandations spécifiques COURTES"""

            if has_rag:
                base_prompt += (
                    "\n\nVous avez accès à une base de connaissances spécialisée."
                )
        else:
            base_prompt = """You are a specialized expert in Ross 308 broiler management.

MANDATORY RESPONSE STYLE:
- SHORT and DIRECT answers (maximum 2-3 sentences)
- Get straight to the point, no logic explanation
- Give the concrete answer immediately
- NO document citations
- NO explanations about "how I determined"
- Professional but concise tone

Respond in English in a way that is:
- Precise and scientifically grounded
- Practical and actionable
- With specific SHORT recommendations"""

            if has_rag:
                base_prompt += "\n\nYou have access to a specialized knowledge base."

        return base_prompt

    def get_suggested_topics(self, language: str = "en") -> list:
        """Get comprehensive suggested topics."""
        if self.expert_engine:
            try:
                return self.expert_engine.get_examples()
            except Exception:
                pass

        # Fallback topics
        if language == "fr":
            return [
                "Température optimale pour Ross 308 de 21 jours",
                "Gestion du stress thermique",
                "Protocoles d'alimentation par phase",
                "Ventilation et qualité d'air",
                "Gestion sanitaire et prévention",
            ]
        else:
            return [
                "Optimal temperature for 21-day Ross 308",
                "Heat stress management",
                "Phase feeding protocols",
                "Ventilation and air quality",
                "Health management and prevention",
            ]

    def get_rag_diagnostics(self) -> Dict[str, Any]:
        """Get comprehensive RAG diagnostics."""
        base_diagnostics = self.rag_manager.get_detailed_status()

        # Add expert engine diagnostics if available
        if self.expert_engine:
            try:
                engine_status = self.expert_engine.get_system_status()
                base_diagnostics.update(
                    {
                        "expert_engine_available": True,
                        "expert_engine_status": engine_status,
                    }
                )
            except Exception as e:
                base_diagnostics.update(
                    {"expert_engine_available": False, "expert_engine_error": str(e)}
                )
        else:
            base_diagnostics.update({"expert_engine_available": False})

        return base_diagnostics

    def force_configure_rag(self):
        """Force RAG reconfiguration."""
        result = self.rag_manager.force_configure_rag()

        # Also try to reinitialize expert engine
        if result.get("success"):
            try:
                self._initialize_expert_engine()
                result["expert_engine_reinitialized"] = True
            except Exception as e:
                result["expert_engine_reinitialization_error"] = str(e)

        return result

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        return datetime.now().isoformat()

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        return {
            "openai_configured": bool(self.openai_client),
            "secrets_loaded": bool(self.secrets.secrets),
            "rag_available": self.rag_manager.rag_available,
            "rag_configured": self.rag_manager.rag_configured,
            "expert_engine_available": self.expert_engine is not None,
            "method": "digitalocean_optimized",
            "environment_variables": {
                "openai_key": bool(os.getenv("OPENAI_API_KEY")),
                "supabase_url": bool(os.getenv("SUPABASE_URL")),
                "supabase_key": bool(os.getenv("SUPABASE_ANON_KEY")),
            },
        }


# Global service instance
expert_service = ExpertService()
