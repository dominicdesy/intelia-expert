"""
Redis Session Service for Voice Realtime
Version: 1.0.0
Date: 2025-10-28

Gère le stockage des sessions Voice Realtime et rate limiting dans Redis.
Fallback graceful vers in-memory si Redis indisponible.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

try:
    import redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    RedisError = Exception
    RedisConnectionError = Exception

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

# TTL (Time To Live) pour les clés Redis
SESSION_TTL = 3600  # 1 heure
RATE_LIMIT_TTL = 3600  # 1 heure

# Préfixes pour les clés Redis
KEY_PREFIX_SESSION = "voice:session:"
KEY_PREFIX_RATE_LIMIT = "voice:ratelimit:"

# ============================================================================
# REDIS SESSION SERVICE
# ============================================================================

class RedisSessionService:
    """
    Service de gestion des sessions Voice avec Redis.

    Features:
    - Stockage persistant des sessions Voice
    - Rate limiting par utilisateur
    - Fallback graceful vers in-memory si Redis down
    - Auto-reconnexion Redis

    Usage:
        service = RedisSessionService()
        service.save_session(session_id, session_data)
        session = service.get_session(session_id)
    """

    def __init__(self):
        self.redis_client: Optional[Any] = None
        self.redis_available = False
        self.use_fallback = False

        # Fallback in-memory storage (si Redis indisponible)
        self._memory_sessions: Dict[str, Dict] = {}
        self._memory_rate_limits: Dict[str, List[datetime]] = defaultdict(list)

        # Tenter connexion Redis
        if REDIS_AVAILABLE and REDIS_ENABLED:
            self._connect_redis()
        else:
            if not REDIS_AVAILABLE:
                logger.warning("⚠️ redis-py not installed. Using in-memory fallback.")
            else:
                logger.warning("⚠️ Redis disabled via REDIS_ENABLED=false. Using in-memory fallback.")
            self.use_fallback = True

    def _connect_redis(self) -> bool:
        """Établit connexion à Redis avec gestion d'erreurs"""
        try:
            self.redis_client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Test de connexion
            self.redis_client.ping()

            self.redis_available = True
            self.use_fallback = False
            logger.info(f"✅ Redis connected successfully: {REDIS_URL}")
            return True

        except (RedisError, RedisConnectionError, Exception) as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.warning("⚠️ Falling back to in-memory session storage")
            self.redis_available = False
            self.use_fallback = True
            self.redis_client = None
            return False

    def _ensure_redis(self) -> bool:
        """Vérifie connexion Redis et tente reconnexion si nécessaire"""
        if self.use_fallback:
            return False

        if not self.redis_available or not self.redis_client:
            return self._connect_redis()

        try:
            self.redis_client.ping()
            return True
        except (RedisError, RedisConnectionError):
            logger.warning("⚠️ Redis connection lost, attempting reconnection...")
            return self._connect_redis()

    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Sauvegarde une session Voice dans Redis (ou mémoire si fallback).

        Args:
            session_id: ID unique de la session
            session_data: Données de la session (dict)

        Returns:
            True si succès, False sinon
        """
        if self._ensure_redis():
            # Mode Redis
            try:
                key = f"{KEY_PREFIX_SESSION}{session_id}"
                value = json.dumps(session_data)
                self.redis_client.setex(key, SESSION_TTL, value)
                logger.debug(f"✅ Session saved to Redis: {session_id}")
                return True
            except (RedisError, Exception) as e:
                logger.error(f"❌ Redis save failed: {e}")
                # Fallback to memory
                self._memory_sessions[session_id] = session_data
                return False
        else:
            # Mode in-memory
            self._memory_sessions[session_id] = session_data
            logger.debug(f"✅ Session saved to memory: {session_id}")
            return True

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une session Voice depuis Redis (ou mémoire si fallback).

        Args:
            session_id: ID unique de la session

        Returns:
            Session data ou None si pas trouvée
        """
        if self._ensure_redis():
            # Mode Redis
            try:
                key = f"{KEY_PREFIX_SESSION}{session_id}"
                value = self.redis_client.get(key)
                if value:
                    session_data = json.loads(value)
                    logger.debug(f"✅ Session retrieved from Redis: {session_id}")
                    return session_data
                return None
            except (RedisError, Exception) as e:
                logger.error(f"❌ Redis get failed: {e}")
                # Fallback to memory
                return self._memory_sessions.get(session_id)
        else:
            # Mode in-memory
            return self._memory_sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """
        Supprime une session Voice.

        Args:
            session_id: ID unique de la session

        Returns:
            True si succès
        """
        if self._ensure_redis():
            # Mode Redis
            try:
                key = f"{KEY_PREFIX_SESSION}{session_id}"
                self.redis_client.delete(key)
                logger.debug(f"✅ Session deleted from Redis: {session_id}")
                return True
            except (RedisError, Exception) as e:
                logger.error(f"❌ Redis delete failed: {e}")
                # Fallback to memory
                self._memory_sessions.pop(session_id, None)
                return False
        else:
            # Mode in-memory
            self._memory_sessions.pop(session_id, None)
            logger.debug(f"✅ Session deleted from memory: {session_id}")
            return True

    def list_sessions(self) -> List[str]:
        """
        Liste tous les session IDs actifs.

        Returns:
            Liste des session IDs
        """
        if self._ensure_redis():
            # Mode Redis
            try:
                pattern = f"{KEY_PREFIX_SESSION}*"
                keys = self.redis_client.keys(pattern)
                session_ids = [key.replace(KEY_PREFIX_SESSION, "") for key in keys]
                return session_ids
            except (RedisError, Exception) as e:
                logger.error(f"❌ Redis list failed: {e}")
                # Fallback to memory
                return list(self._memory_sessions.keys())
        else:
            # Mode in-memory
            return list(self._memory_sessions.keys())

    # ========================================================================
    # RATE LIMITING
    # ========================================================================

    def check_rate_limit(
        self,
        user_id: str,
        max_sessions: int = 5,
        window_seconds: int = 3600
    ) -> bool:
        """
        Vérifie si l'utilisateur peut créer une nouvelle session.

        Args:
            user_id: ID utilisateur
            max_sessions: Nombre max de sessions dans la fenêtre
            window_seconds: Fenêtre de temps en secondes

        Returns:
            True si OK, False si rate limit atteint
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=window_seconds)

        if self._ensure_redis():
            # Mode Redis avec sorted sets
            try:
                key = f"{KEY_PREFIX_RATE_LIMIT}{user_id}"

                # Supprimer timestamps expirés
                self.redis_client.zremrangebyscore(key, 0, cutoff.timestamp())

                # Compter sessions récentes
                count = self.redis_client.zcard(key)

                if count >= max_sessions:
                    logger.warning(f"⚠️ Rate limit exceeded for user {user_id}: {count}/{max_sessions}")
                    return False

                # Ajouter timestamp actuel
                self.redis_client.zadd(key, {str(now.timestamp()): now.timestamp()})

                # Définir TTL sur la clé
                self.redis_client.expire(key, RATE_LIMIT_TTL)

                return True

            except (RedisError, Exception) as e:
                logger.error(f"❌ Redis rate limit check failed: {e}")
                # Fallback to memory
                pass

        # Mode in-memory fallback
        timestamps = self._memory_rate_limits[user_id]

        # Nettoyer anciens timestamps
        timestamps = [ts for ts in timestamps if ts > cutoff]
        self._memory_rate_limits[user_id] = timestamps

        if len(timestamps) >= max_sessions:
            logger.warning(f"⚠️ Rate limit exceeded (memory) for user {user_id}: {len(timestamps)}/{max_sessions}")
            return False

        # Ajouter timestamp actuel
        timestamps.append(now)
        return True

    def reset_rate_limit(self, user_id: str) -> bool:
        """
        Reset le rate limit pour un utilisateur (admin use).

        Args:
            user_id: ID utilisateur

        Returns:
            True si succès
        """
        if self._ensure_redis():
            try:
                key = f"{KEY_PREFIX_RATE_LIMIT}{user_id}"
                self.redis_client.delete(key)
                return True
            except (RedisError, Exception) as e:
                logger.error(f"❌ Redis reset rate limit failed: {e}")

        # Fallback
        self._memory_rate_limits.pop(user_id, None)
        return True

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    def health_check(self) -> Dict[str, Any]:
        """
        Vérifie l'état du service Redis.

        Returns:
            Dictionnaire avec status, mode, etc.
        """
        status = {
            "redis_available": self.redis_available,
            "redis_enabled": REDIS_ENABLED,
            "using_fallback": self.use_fallback,
            "redis_url": REDIS_URL if not self.use_fallback else None,
        }

        if self.redis_available and self._ensure_redis():
            try:
                info = self.redis_client.info()
                status["redis_version"] = info.get("redis_version")
                status["connected_clients"] = info.get("connected_clients")
                status["used_memory_human"] = info.get("used_memory_human")
            except (RedisError, Exception) as e:
                status["redis_error"] = str(e)

        return status

# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Instance globale partagée
redis_session_service = RedisSessionService()
