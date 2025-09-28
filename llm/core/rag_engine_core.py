# -*- coding: utf-8 -*-
"""
rag_engine_core.py - Core fonctionnalités du RAG Engine
"""

import logging
from typing import Optional

try:
    from utils.imports_and_dependencies import OPENAI_AVAILABLE, AsyncOpenAI
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

from config.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


class RAGEngineCore:
    """Core du RAG Engine avec gestion OpenAI"""

    def __init__(self, openai_client: AsyncOpenAI = None):
        """Initialisation"""
        try:
            self.openai_client = openai_client or self._build_openai_client()
        except Exception as e:
            logger.warning(f"Erreur client OpenAI: {e}")
            self.openai_client = None

    def _build_openai_client(self) -> Optional[AsyncOpenAI]:
        """Client OpenAI"""
        if not OPENAI_AVAILABLE or not AsyncOpenAI:
            return None

        if not OPENAI_API_KEY:
            return None

        try:
            try:
                import httpx

                http_client = httpx.AsyncClient(timeout=30.0)
                return AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
            except ImportError:
                return AsyncOpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"Erreur création client OpenAI: {e}")
            return None

    async def initialize(self):
        """Initialisation du core"""
        logger.info("RAG Engine Core initialisé")

    async def close(self):
        """Fermeture du core"""
        logger.info("RAG Engine Core fermé")
