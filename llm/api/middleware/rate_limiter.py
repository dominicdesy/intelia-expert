# -*- coding: utf-8 -*-
"""
Rate limiting middleware pour FastAPI
Limite: 10 requêtes/minute par utilisateur
"""

import time
import logging
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter(BaseHTTPMiddleware):
    """
    Rate limiting middleware basé sur Redis ou mémoire

    Limite: 10 requêtes par minute par user_id
    """

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self._redis_client = redis_client

        # Fallback en mémoire si Redis indisponible
        self.memory_store: Dict[str, Tuple[int, float]] = defaultdict(
            lambda: (0, time.time())
        )

        # Configuration
        self.max_requests = 10  # Requêtes par fenêtre
        self.window_seconds = 60  # Fenêtre de 1 minute

    @property
    def redis_client(self):
        """Get Redis client (may be set after initialization)"""
        return self._redis_client

    @redis_client.setter
    def redis_client(self, client):
        """Set Redis client after initialization"""
        self._redis_client = client
        if client:
            logger.info("✅ Rate limiting Redis client configured")

    async def dispatch(self, request: Request, call_next):
        """
        Vérifie le rate limit avant chaque requête
        """
        # Extraire user_id ou IP
        user_id = self._get_user_identifier(request)

        # Vérifier le rate limit
        is_allowed, remaining = await self._check_rate_limit(user_id)

        if not is_allowed:
            logger.warning(f"⚠️ Rate limit exceeded for user {user_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.max_requests} requests per minute allowed",
                    "retry_after": 60,
                },
            )

        # Ajouter headers de rate limit
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + self.window_seconds
        )

        return response

    def _get_user_identifier(self, request: Request) -> str:
        """
        Extrait l'identifiant utilisateur (user_id ou IP)
        """
        # Essayer d'extraire user_id du token JWT ou session
        user_id = request.headers.get("X-User-ID")

        if not user_id:
            # Essayer le body pour /chat et /question
            try:
                if hasattr(request.state, "body"):
                    body = request.state.body
                    if isinstance(body, dict):
                        user_id = body.get("user_id") or body.get("tenant_id")
            except (ValueError, AttributeError):
                pass

        # Fallback sur IP si pas de user_id
        if not user_id:
            user_id = request.client.host if request.client else "unknown"

        return user_id

    async def _check_rate_limit(self, user_id: str) -> Tuple[bool, int]:
        """
        Vérifie si l'utilisateur est dans les limites

        Returns:
            (is_allowed, remaining_requests)
        """
        current_time = time.time()

        if self.redis_client:
            return await self._check_redis(user_id, current_time)
        else:
            return self._check_memory(user_id, current_time)

    async def _check_redis(self, user_id: str, current_time: float) -> Tuple[bool, int]:
        """
        Rate limiting avec Redis (recommandé en production)
        """
        try:
            key = f"ratelimit:{user_id}"

            # Incrémenter le compteur
            count = await self.redis_client.incr(key)

            # Définir l'expiration si c'est la première requête
            if count == 1:
                await self.redis_client.expire(key, self.window_seconds)

            # Vérifier la limite
            remaining = max(0, self.max_requests - count)
            is_allowed = count <= self.max_requests

            return is_allowed, remaining

        except Exception as e:
            logger.error(f"❌ Redis error in rate limiter: {e}, using memory fallback")
            return self._check_memory(user_id, current_time)

    def _check_memory(self, user_id: str, current_time: float) -> Tuple[bool, int]:
        """
        Rate limiting en mémoire (fallback)
        """
        count, window_start = self.memory_store[user_id]

        # Reset si fenêtre expirée
        if current_time - window_start > self.window_seconds:
            count = 0
            window_start = current_time

        # Incrémenter
        count += 1
        self.memory_store[user_id] = (count, window_start)

        # Vérifier limite
        remaining = max(0, self.max_requests - count)
        is_allowed = count <= self.max_requests

        return is_allowed, remaining
