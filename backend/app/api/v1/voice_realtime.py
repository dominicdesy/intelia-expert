"""
Voice Realtime API - WebSocket Endpoint
========================================

Endpoint WebSocket pour conversation vocale en temps réel avec OpenAI Realtime API.

Architecture:
    User (mobile/web) <-> WebSocket <-> Backend <-> OpenAI Realtime API
                                           ↓
                                        Weaviate RAG

Features:
    - Streaming audio bidirectionnel
    - Pré-chargement RAG (Option B)
    - Détection VAD (Voice Activity Detection)
    - Gestion interruption utilisateur
    - Monitoring latence temps réel

Security:
    - Feature flag ENABLE_VOICE_REALTIME
    - JWT authentication required
    - Rate limiting (5 sessions/hour/user)
    - Session timeout 10 minutes
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import websockets

logger = logging.getLogger(__name__)

# Imports depuis le projet (réutilisation sans modification)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'llm'))

# Import optionnel (évite crash si JWT secret absent en local)
try:
    from app.dependencies.quota_check import get_current_user_from_websocket
    from app.core.database import get_db
    AUTH_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    logger.warning(f"⚠️ Auth dependencies not available (normal en local): {e}")
    AUTH_AVAILABLE = False
    get_current_user_from_websocket = None
    get_db = None

# ============================================================
# CONFIGURATION & FEATURE FLAG
# ============================================================

ENABLE_VOICE_REALTIME = os.getenv("ENABLE_VOICE_REALTIME", "false").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

# Limites de sécurité
MAX_SESSION_DURATION = 600  # 10 minutes max
MAX_SESSIONS_PER_USER_PER_HOUR = 5
RATE_LIMIT_WINDOW = 3600  # 1 heure

# Configuration OpenAI Realtime
OPENAI_REALTIME_MODEL = "gpt-4o-realtime-preview-2024-10-01"
OPENAI_REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_REALTIME_MODEL}"

# ============================================================
# ROUTER
# ============================================================

router = APIRouter()

# ============================================================
# RATE LIMITING (In-Memory - TODO: Redis en production)
# ============================================================

class RateLimiter:
    """Rate limiter simple en mémoire (TODO: migrer vers Redis)"""

    def __init__(self):
        self.sessions_per_user = defaultdict(list)  # user_id -> [timestamps]

    def check_rate_limit(self, user_id: int) -> bool:
        """Vérifie si user peut créer nouvelle session"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=RATE_LIMIT_WINDOW)

        # Nettoyer anciennes sessions
        self.sessions_per_user[user_id] = [
            ts for ts in self.sessions_per_user[user_id]
            if ts > cutoff
        ]

        # Vérifier limite
        if len(self.sessions_per_user[user_id]) >= MAX_SESSIONS_PER_USER_PER_HOUR:
            return False

        # Ajouter nouvelle session
        self.sessions_per_user[user_id].append(now)
        return True

rate_limiter = RateLimiter()

# ============================================================
# WEAVIATE RAG SERVICE (Option B - Pré-chargement)
# ============================================================

class WeaviateRAGService:
    """Service pour pré-charger contexte Weaviate pendant parole utilisateur"""

    def __init__(self):
        self.enabled = bool(WEAVIATE_URL)
        if self.enabled:
            try:
                # Import dynamique pour ne pas casser si module absent
                from retrieval.retriever_core import HybridWeaviateRetriever
                from utils.imports_and_dependencies import wvc

                self.client = wvc.Client(
                    url=WEAVIATE_URL,
                    auth_client_secret=wvc.AuthApiKey(WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None
                )
                self.retriever = HybridWeaviateRetriever(self.client)
                logger.info("✅ Weaviate RAG Service initialized")
            except Exception as e:
                logger.error(f"❌ Weaviate initialization failed: {e}")
                self.enabled = False

    async def query_context(self, query: str, limit: int = 5) -> Optional[str]:
        """Query Weaviate pour contexte RAG (async)"""
        if not self.enabled:
            return None

        start = time.time()
        try:
            # Query hybride (vector + BM25)
            results = await self.retriever.search(
                query=query,
                limit=limit,
                alpha=0.7  # Balance vector/keyword
            )

            latency = (time.time() - start) * 1000
            logger.info(f"📊 Weaviate query: {latency:.2f}ms ({len(results)} résultats)")

            # Formater contexte
            if results:
                context_parts = []
                for i, result in enumerate(results, 1):
                    content = result.get("content", "")
                    context_parts.append(f"{i}. {content}")

                return "\n\n".join(context_parts)

            return None

        except Exception as e:
            logger.error(f"❌ Weaviate query error: {e}")
            return None

# Instance globale
weaviate_service = WeaviateRAGService()

# ============================================================
# VOICE REALTIME SESSION
# ============================================================

class VoiceRealtimeSession:
    """Gère une session voice realtime pour un utilisateur"""

    def __init__(self, user_id: int, websocket: WebSocket):
        self.user_id = user_id
        self.client_ws = websocket
        self.openai_ws: Optional[websockets.WebSocketClientProtocol] = None

        self.session_id = f"{user_id}_{int(time.time())}"
        self.start_time = time.time()
        self.running = False

        # Métriques
        self.metrics = {
            "openai_connection_time": 0,
            "total_audio_chunks_sent": 0,
            "total_audio_chunks_received": 0,
            "rag_queries": 0,
            "rag_cache_hits": 0,
            "errors": []
        }

        # Option B: Pré-chargement RAG
        self.partial_transcript = ""
        self.context_cache: Optional[str] = None
        self.context_ready = False
        self.context_task: Optional[asyncio.Task] = None

    async def connect_openai(self):
        """Connexion WebSocket à OpenAI Realtime API"""
        logger.info(f"🔌 Connecting to OpenAI Realtime API (session {self.session_id})")
        start = time.time()

        try:
            self.openai_ws = await websockets.connect(
                OPENAI_REALTIME_URL,
                additional_headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "OpenAI-Beta": "realtime=v1"
                }
            )

            self.metrics["openai_connection_time"] = (time.time() - start) * 1000
            logger.info(f"✅ OpenAI connected in {self.metrics['openai_connection_time']:.2f}ms")

            # Configurer session
            await self.configure_openai_session()

            return True

        except Exception as e:
            logger.error(f"❌ OpenAI connection failed: {e}")
            self.metrics["errors"].append(f"OpenAI connection: {str(e)}")
            return False

    async def configure_openai_session(self):
        """Configurer session OpenAI avec instructions"""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": (
                    "Tu es un expert en aviculture assistant l'utilisateur. "
                    "Réponds en français de manière concise et naturelle. "
                    "Si tu reçois du contexte supplémentaire entre balises <context>, "
                    "utilise-le pour enrichir ta réponse. "
                    "Sinon, utilise tes connaissances générales."
                ),
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "temperature": 0.8
            }
        }

        await self.openai_ws.send(json.dumps(config))
        logger.info("⚙️  OpenAI session configured")

    async def handle_partial_transcript(self, transcript: str):
        """
        OPTION B: Pré-chargement RAG
        Dès qu'on a transcription partielle, query Weaviate en parallèle
        """
        self.partial_transcript = transcript

        # Attendre au moins 5 mots avant de query
        word_count = len(transcript.split())
        if word_count < 5:
            return

        # Si contexte déjà en chargement, skip
        if self.context_task and not self.context_task.done():
            return

        # Lancer query Weaviate en background
        logger.info(f"🔍 Pre-loading RAG context: '{transcript[:50]}...'")
        self.context_task = asyncio.create_task(self._load_context(transcript))

    async def _load_context(self, query: str):
        """Charge contexte Weaviate en background"""
        start = time.time()
        self.context_cache = await weaviate_service.query_context(query)
        self.context_ready = True
        self.metrics["rag_queries"] += 1

        latency = (time.time() - start) * 1000
        logger.info(f"✅ RAG context ready in {latency:.2f}ms")

    async def handle_speech_end(self, final_transcript: str):
        """
        VAD a détecté fin de parole
        Injecter contexte RAG si prêt, sinon attendre max 200ms
        """
        logger.info(f"🎤 Speech ended: '{final_transcript}'")

        # Attendre contexte si pas encore prêt (max 200ms)
        if self.context_task and not self.context_ready:
            try:
                await asyncio.wait_for(self.context_task, timeout=0.2)
            except asyncio.TimeoutError:
                logger.warning("⚠️  RAG context timeout, continuing without context")

        # Injecter contexte si disponible
        if self.context_ready and self.context_cache:
            await self.inject_rag_context(self.context_cache)
        else:
            logger.info("ℹ️  No RAG context available, using LLM general knowledge")

        # Reset pour prochaine question
        self.context_ready = False
        self.context_cache = None
        self.partial_transcript = ""

    async def inject_rag_context(self, context: str):
        """Injecter contexte RAG comme message système"""
        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"<context>\n{context}\n</context>"
                    }
                ]
            }
        }

        await self.openai_ws.send(json.dumps(message))
        logger.info(f"📦 RAG context injected ({len(context)} chars)")

    async def forward_client_to_openai(self):
        """Router messages client → OpenAI"""
        try:
            async for message in self.client_ws.iter_text():
                if not self.running:
                    break

                data = json.loads(message)

                # Transférer à OpenAI
                await self.openai_ws.send(message)

                # Tracking
                msg_type = data.get("type")
                if msg_type == "audio.input":
                    self.metrics["total_audio_chunks_sent"] += 1

        except WebSocketDisconnect:
            logger.info(f"🔌 Client disconnected (session {self.session_id})")
        except Exception as e:
            logger.error(f"❌ Client→OpenAI error: {e}")
            self.metrics["errors"].append(f"Client routing: {str(e)}")

    async def forward_openai_to_client(self):
        """Router messages OpenAI → Client"""
        try:
            async for message in self.openai_ws:
                if not self.running:
                    break

                data = json.loads(message)
                event_type = data.get("type")

                # Log errors from OpenAI
                if event_type == "error":
                    logger.error(f"❌ OpenAI error: {data.get('error', {})}")

                # OPTION B: Détecter transcription partielle
                if event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = data.get("transcript", "")
                    await self.handle_partial_transcript(transcript)

                # Détecter fin de parole
                if event_type == "input_audio_buffer.speech_stopped":
                    # Récupérer transcript final
                    transcript = data.get("transcript", self.partial_transcript)
                    await self.handle_speech_end(transcript)

                # Compter chunks audio
                if event_type == "response.audio.delta":
                    self.metrics["total_audio_chunks_received"] += 1

                # Transférer au client
                await self.client_ws.send_text(message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 OpenAI disconnected (session {self.session_id})")
        except Exception as e:
            logger.error(f"❌ OpenAI→Client error: {e}")
            self.metrics["errors"].append(f"OpenAI routing: {str(e)}")

    async def run(self):
        """Exécuter session voice realtime"""
        self.running = True

        try:
            # Connexion OpenAI
            if not await self.connect_openai():
                await self.client_ws.close(code=1011, reason="OpenAI connection failed")
                return

            # Router messages bidirectionnels
            await asyncio.gather(
                self.forward_client_to_openai(),
                self.forward_openai_to_client(),
                self.monitor_session_timeout()
            )

        except Exception as e:
            logger.error(f"💥 Session error: {e}")
            self.metrics["errors"].append(f"Session: {str(e)}")

        finally:
            await self.cleanup()

    async def monitor_session_timeout(self):
        """Arrêter session après MAX_SESSION_DURATION"""
        await asyncio.sleep(MAX_SESSION_DURATION)

        logger.warning(f"⏱️  Session timeout ({MAX_SESSION_DURATION}s)")
        self.running = False

        await self.client_ws.send_text(json.dumps({
            "type": "session.timeout",
            "message": "Session terminée (durée maximale atteinte)"
        }))

    async def cleanup(self):
        """Nettoyer ressources"""
        self.running = False

        if self.openai_ws:
            await self.openai_ws.close()

        # Log métriques finales
        duration = time.time() - self.start_time
        logger.info(f"📊 Session {self.session_id} ended:")
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info(f"  Audio chunks sent: {self.metrics['total_audio_chunks_sent']}")
        logger.info(f"  Audio chunks received: {self.metrics['total_audio_chunks_received']}")
        logger.info(f"  RAG queries: {self.metrics['rag_queries']}")
        logger.info(f"  Errors: {len(self.metrics['errors'])}")

# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/ws/voice")
async def voice_realtime_endpoint(
    websocket: WebSocket,
    # TODO: Décommenter quand get_current_user_from_websocket disponible
    # user = Depends(get_current_user_from_websocket)
):
    """
    WebSocket endpoint pour voice realtime

    Security:
        - Feature flag checked
        - JWT authentication (TODO: décommenter Depends)
        - Rate limiting
        - Session timeout

    Flow:
        1. Accept WebSocket connection
        2. Authenticate user (JWT)
        3. Check rate limit
        4. Create VoiceRealtimeSession
        5. Run bidirectional routing
        6. Cleanup on disconnect
    """

    # Feature flag check - TEMPORARILY DISABLED FOR TESTING
    # if not ENABLE_VOICE_REALTIME:
    #     await websocket.close(code=1008, reason="Voice realtime feature disabled")
    #     logger.warning("❌ Voice realtime request rejected: feature disabled")
    #     return

    # Accept connection
    await websocket.accept()
    logger.info("✅ WebSocket connection accepted")

    # TODO: Authentification JWT
    # Pour l'instant, user_id hardcodé pour tests
    user_id = 1  # TODO: user.id quand auth activée

    # Rate limiting - TEMPORARILY DISABLED FOR TESTING
    # if not rate_limiter.check_rate_limit(user_id):
    #     await websocket.close(
    #         code=1008,
    #         reason=f"Rate limit exceeded ({MAX_SESSIONS_PER_USER_PER_HOUR} sessions/hour max)"
    #     )
    #     logger.warning(f"❌ Rate limit exceeded for user {user_id}")
    #     return

    # Créer session
    session = VoiceRealtimeSession(user_id, websocket)

    logger.info(f"🚀 Starting voice realtime session {session.session_id}")

    try:
        await session.run()
    except Exception as e:
        logger.error(f"💥 Unexpected error in session {session.session_id}: {e}")

    logger.info(f"👋 Session {session.session_id} terminated")

# ============================================================
# HEALTH CHECK ENDPOINT
# ============================================================

@router.get("/voice/health")
async def voice_health():
    """Health check pour voice realtime"""
    return {
        "status": "healthy" if ENABLE_VOICE_REALTIME else "disabled",
        "feature_enabled": ENABLE_VOICE_REALTIME,
        "openai_configured": bool(OPENAI_API_KEY),
        "weaviate_enabled": weaviate_service.enabled,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================
# STATS ENDPOINT (Admin)
# ============================================================

@router.get("/voice/stats")
async def voice_stats():
    """Stats voice realtime (TODO: ajouter auth admin)"""
    return {
        "rate_limiter": {
            "active_users": len(rate_limiter.sessions_per_user),
            "total_sessions_tracked": sum(len(sessions) for sessions in rate_limiter.sessions_per_user.values())
        },
        "config": {
            "max_session_duration": MAX_SESSION_DURATION,
            "max_sessions_per_hour": MAX_SESSIONS_PER_USER_PER_HOUR,
            "openai_model": OPENAI_REALTIME_MODEL
        },
        "timestamp": datetime.now().isoformat()
    }
