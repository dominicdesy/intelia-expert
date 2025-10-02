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
    """Core du RAG Engine avec gestion OpenAI et générateur de réponses"""

    def __init__(self, openai_client: AsyncOpenAI = None):
        """Initialisation du core avec tous les composants nécessaires"""

        # Client OpenAI
        try:
            self.openai_client = openai_client or self._build_openai_client()
        except Exception as e:
            logger.warning(f"Erreur client OpenAI: {e}")
            self.openai_client = None

        # Générateur de réponses - CORRECTION CRITIQUE
        try:
            from generation.generators import EnhancedResponseGenerator

            self.generator = EnhancedResponseGenerator()
            logger.info("✅ Generator initialisé dans RAGEngineCore")
        except Exception as e:
            logger.error(f"❌ Échec initialisation generator: {e}")
            self.generator = None

    def _build_openai_client(self) -> Optional[AsyncOpenAI]:
        """Construction du client OpenAI avec configuration optimisée"""
        if not OPENAI_AVAILABLE or not AsyncOpenAI:
            logger.warning("OpenAI non disponible")
            return None

        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY manquante")
            return None

        try:
            try:
                import httpx

                http_client = httpx.AsyncClient(timeout=30.0)
                client = AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
                logger.info("Client OpenAI créé avec httpx")
                return client
            except ImportError:
                client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                logger.info("Client OpenAI créé sans httpx")
                return client
        except Exception as e:
            logger.error(f"Erreur création client OpenAI: {e}")
            return None

    async def initialize(self):
        """Initialisation asynchrone du core"""
        logger.info("RAG Engine Core initialisé")

        # Vérification des composants critiques
        if not self.openai_client:
            logger.warning("OpenAI client non disponible")

        if not self.generator:
            logger.error("Generator non disponible - les réponses LLM échoueront")

        return self

    async def close(self):
        """Fermeture propre du core et libération des ressources"""
        if self.openai_client and hasattr(self.openai_client, "close"):
            try:
                await self.openai_client.close()
                logger.info("Client OpenAI fermé")
            except Exception as e:
                logger.warning(f"Erreur fermeture OpenAI client: {e}")

        logger.info("RAG Engine Core fermé")
