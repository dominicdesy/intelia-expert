# -*- coding: utf-8 -*-
"""
rag_engine_core.py - RAG Engine core functionalities
"""

import logging
from utils.types import Optional
from .base import InitializableMixin

try:
    from utils.imports_and_dependencies import OPENAI_AVAILABLE, AsyncOpenAI
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

from config.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


class RAGEngineCore(InitializableMixin):
    """RAG Engine core with OpenAI management and response generator"""

    def __init__(self, openai_client: AsyncOpenAI = None):
        """Initialize core with all required components"""
        super().__init__()

        # OpenAI client - MUST be initialized first
        try:
            self.openai_client = openai_client or self._build_openai_client()
            if self.openai_client:
                logger.info("OpenAI client created with httpx")
        except Exception as e:
            logger.warning(f"OpenAI client error: {e}")
            self.openai_client = None

        # Response generator - Critical correction with client passing
        try:
            from generation.generators import EnhancedResponseGenerator

            if self.openai_client:
                self.generator = EnhancedResponseGenerator(client=self.openai_client)
                logger.info(
                    "✅ Generator initialized in RAGEngineCore with OpenAI client"
                )
            else:
                logger.error(
                    "❌ Cannot initialize generator: OpenAI client missing"
                )
                self.generator = None

        except Exception as e:
            logger.error(f"❌ Generator initialization failed: {e}")
            self.generator = None

    def _build_openai_client(self) -> Optional[AsyncOpenAI]:
        """Build OpenAI client with optimized configuration"""
        if not OPENAI_AVAILABLE or not AsyncOpenAI:
            logger.warning("OpenAI not available")
            return None

        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY missing")
            return None

        try:
            try:
                import httpx

                http_client = httpx.AsyncClient(timeout=30.0)
                return AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
            except ImportError:
                return AsyncOpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"Error creating OpenAI client: {e}")
            return None

    async def initialize(self):
        """Async core initialization"""
        logger.info("RAG Engine Core initialized")

        # Verify critical components
        if not self.openai_client:
            logger.warning("OpenAI client not available")

        if not self.generator:
            logger.error("Generator not available - LLM responses will fail")
        else:
            logger.info("✅ All critical components available")

        await super().initialize()
        return self

    async def close(self):
        """Clean core shutdown and resource release"""
        if self.openai_client and hasattr(self.openai_client, "close"):
            try:
                await self.openai_client.close()
                logger.info("OpenAI client closed")
            except Exception as e:
                logger.warning(f"Error closing OpenAI client: {e}")

        await super().close()
        logger.info("RAG Engine Core closed")
