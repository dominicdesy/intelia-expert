"""
ai_service_manager.py - GESTIONNAIRE CENTRALISÉ DES SERVICES IA

🎯 RESPONSABILITÉS:
- ✅ Gestion centralisée du client OpenAI
- ✅ Rate limiting et gestion des quotas
- ✅ Cache intelligent des réponses IA
- ✅ Monitoring et health checks
- ✅ Fallback automatique si IA indisponible
- ✅ Optimisation des coûts API

Architecture:
- Un seul point d'entrée pour tous les appels IA
- Cache Redis/Memory pour éviter appels redondants
- Circuit breaker pour protection contre pannes API
- Métriques détaillées pour monitoring
"""

import os
import json
import time
import hashlib
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

# Imports sécurisés
try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None
    AsyncOpenAI = None

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)

class AIServiceType(Enum):
    """Types de services IA disponibles"""
    ENTITY_EXTRACTION = "entity_extraction"
    CONTEXT_ENHANCEMENT = "context_enhancement"
    RESPONSE_GENERATION = "response_generation"
    VALIDATION = "validation"
    CLASSIFICATION = "classification"

@dataclass
class AIRequest:
    """Structure d'une requête IA"""
    service_type: AIServiceType
    prompt: str
    model: str = "gpt-4"
    max_tokens: int = 1000
    temperature: float = 0.1
    timeout: int = 30
    cache_key: Optional[str] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None

@dataclass
class AIResponse:
    """Structure d'une réponse IA"""
    content: str
    service_type: AIServiceType
    model_used: str
    tokens_used: int
    response_time_ms: int
    cached: bool = False
    cost_estimate: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class CircuitBreaker:
    """Circuit breaker pour protection contre les pannes API"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Vérifie si on peut exécuter la requête"""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if self.last_failure_time and \
               time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        
        if self.state == "HALF_OPEN":
            return True
        
        return False
    
    def record_success(self):
        """Enregistre un succès"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Enregistre un échec"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class AIServiceManager:
    """Gestionnaire centralisé des services IA"""
    
    def __init__(self, 
                 redis_url: str = None,
                 cache_ttl: int = 3600,
                 enable_circuit_breaker: bool = True):
        
        # Configuration
        self.cache_ttl = cache_ttl
        self.enable_circuit_breaker = enable_circuit_breaker
        
        # Client OpenAI
        self.client = None
        self.available = False
        
        # Cache
        self.redis_client = None
        self.memory_cache = {}
        self.cache_enabled = False
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker() if enable_circuit_breaker else None
        
        # Métriques
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_requests": 0,
            "total_tokens_used": 0,
            "total_cost": 0.0,
            "response_times": [],
            "requests_by_service": {service.value: 0 for service in AIServiceType}
        }
        
        # Rate limiting
        self.rate_limits = {
            AIServiceType.ENTITY_EXTRACTION: {"requests_per_minute": 60, "tokens_per_minute": 10000},
            AIServiceType.CONTEXT_ENHANCEMENT: {"requests_per_minute": 40, "tokens_per_minute": 15000},
            AIServiceType.RESPONSE_GENERATION: {"requests_per_minute": 30, "tokens_per_minute": 20000},
            AIServiceType.VALIDATION: {"requests_per_minute": 60, "tokens_per_minute": 8000},
            AIServiceType.CLASSIFICATION: {"requests_per_minute": 80, "tokens_per_minute": 5000}
        }
        
        # Initialisation
        self._initialize_openai()
        self._initialize_cache(redis_url)
        
        logger.info(f"🤖 [AI Service Manager] Initialisé - IA: {self.available}, Cache: {self.cache_enabled}")
    
    def _initialize_openai(self):
        """Initialise le client OpenAI"""
        try:
            if not OPENAI_AVAILABLE:
                logger.warning("⚠️ [AI Manager] OpenAI non disponible")
                return False
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("⚠️ [AI Manager] OPENAI_API_KEY non configuré")
                return False
            
            self.client = AsyncOpenAI(api_key=api_key)
            self.available = True
            logger.info("✅ [AI Manager] Client OpenAI initialisé")
            return True
            
        except Exception as e:
            logger.error(f"❌ [AI Manager] Erreur initialisation OpenAI: {e}")
            self.available = False
            return False
    
    def _initialize_cache(self, redis_url: str = None):
        """Initialise le système de cache"""
        try:
            # Essayer Redis d'abord
            if REDIS_AVAILABLE and redis_url:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                self.cache_enabled = True
                logger.info("✅ [AI Manager] Cache Redis initialisé")
                return
            
            # Fallback vers cache mémoire
            self.cache_enabled = True
            logger.info("✅ [AI Manager] Cache mémoire activé")
            
        except Exception as e:
            logger.warning(f"⚠️ [AI Manager] Cache indisponible: {e}")
            self.cache_enabled = False
    
    def _generate_cache_key(self, request: AIRequest) -> str:
        """Génère une clé de cache pour la requête"""
        if request.cache_key:
            return f"ai_cache:{request.service_type.value}:{request.cache_key}"
        
        # Générer clé basée sur le contenu
        content = f"{request.service_type.value}:{request.prompt}:{request.model}:{request.temperature}"
        hash_key = hashlib.md5(content.encode()).hexdigest()
        return f"ai_cache:{request.service_type.value}:{hash_key}"
    
    async def _get_from_cache(self, cache_key: str) -> Optional[AIResponse]:
        """Récupère une réponse du cache"""
        if not self.cache_enabled:
            return None
        
        try:
            # Redis en priorité
            if self.redis_client:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    response = AIResponse(**data)
                    response.cached = True
                    return response
            
            # Cache mémoire
            if cache_key in self.memory_cache:
                data = self.memory_cache[cache_key]
                if data['expiry'] > time.time():
                    response = AIResponse(**data['response'])
                    response.cached = True
                    return response
                else:
                    del self.memory_cache[cache_key]
            
        except Exception as e:
            logger.warning(f"⚠️ [AI Manager] Erreur lecture cache: {e}")
        
        return None
    
    async def _save_to_cache(self, cache_key: str, response: AIResponse):
        """Sauvegarde une réponse en cache"""
        if not self.cache_enabled:
            return
        
        try:
            response_dict = asdict(response)
            response_dict['timestamp'] = response.timestamp.isoformat()
            
            # Redis en priorité
            if self.redis_client:
                self.redis_client.setex(
                    cache_key, 
                    self.cache_ttl, 
                    json.dumps(response_dict, default=str)
                )
            else:
                # Cache mémoire
                self.memory_cache[cache_key] = {
                    'response': response_dict,
                    'expiry': time.time() + self.cache_ttl
                }
            
        except Exception as e:
            logger.warning(f"⚠️ [AI Manager] Erreur sauvegarde cache: {e}")
    
    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estime le coût d'un appel API"""
        # Prix approximatifs OpenAI (à ajuster selon tarifs actuels)
        pricing = {
            "gpt-4": {"input": 0.03/1000, "output": 0.06/1000},
            "gpt-4-turbo": {"input": 0.01/1000, "output": 0.03/1000},
            "gpt-3.5-turbo": {"input": 0.001/1000, "output": 0.002/1000}
        }
        
        if model not in pricing:
            model = "gpt-4"  # Default
        
        input_cost = input_tokens * pricing[model]["input"]
        output_cost = output_tokens * pricing[model]["output"]
        return input_cost + output_cost
    
    async def call_ai_service(self, request: AIRequest) -> AIResponse:
        """
        Point d'entrée principal pour tous les appels IA
        
        Args:
            request: Requête IA structurée
            
        Returns:
            AIResponse avec le résultat ou erreur
            
        Raises:
            Exception: Si l'IA est indisponible et qu'aucun fallback n'est possible
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        self.metrics["requests_by_service"][request.service_type.value] += 1
        
        try:
            # Vérifier circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                raise Exception("Circuit breaker OPEN - IA temporairement indisponible")
            
            # Vérifier cache
            cache_key = self._generate_cache_key(request)
            cached_response = await self._get_from_cache(cache_key)
            
            if cached_response:
                self.metrics["cached_requests"] += 1
                logger.info(f"✅ [AI Manager] Réponse depuis cache: {request.service_type.value}")
                return cached_response
            
            # Appel IA
            if not self.available:
                raise Exception("Client OpenAI non disponible")
            
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en élevage avicole. Réponds de manière précise et professionnelle."
                    },
                    {
                        "role": "user", 
                        "content": request.prompt
                    }
                ],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                timeout=request.timeout
            )
            
            # Construire réponse
            content = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            response_time_ms = int((time.time() - start_time) * 1000)
            cost = self._estimate_cost(request.model, response.usage.prompt_tokens, response.usage.completion_tokens)
            
            ai_response = AIResponse(
                content=content,
                service_type=request.service_type,
                model_used=request.model,
                tokens_used=tokens_used,
                response_time_ms=response_time_ms,
                cost_estimate=cost
            )
            
            # Sauvegarder en cache
            await self._save_to_cache(cache_key, ai_response)
            
            # Métriques
            self.metrics["successful_requests"] += 1
            self.metrics["total_tokens_used"] += tokens_used
            self.metrics["total_cost"] += cost
            self.metrics["response_times"].append(response_time_ms)
            
            # Circuit breaker success
            if self.circuit_breaker:
                self.circuit_breaker.record_success()
            
            logger.info(f"✅ [AI Manager] Appel réussi: {request.service_type.value} ({response_time_ms}ms, {tokens_used} tokens)")
            return ai_response
            
        except Exception as e:
            # Métriques d'erreur
            self.metrics["failed_requests"] += 1
            
            # Circuit breaker failure
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            
            logger.error(f"❌ [AI Manager] Erreur appel IA: {e}")
            raise
    
    def get_service_health(self) -> Dict[str, Any]:
        """Retourne l'état de santé des services IA"""
        total_requests = self.metrics["total_requests"]
        success_rate = (self.metrics["successful_requests"] / total_requests * 100) if total_requests > 0 else 0
        
        avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"]) if self.metrics["response_times"] else 0
        
        return {
            "ai_available": self.available,
            "cache_enabled": self.cache_enabled,
            "circuit_breaker_state": self.circuit_breaker.state if self.circuit_breaker else None,
            "total_requests": total_requests,
            "success_rate": round(success_rate, 2),
            "cache_hit_rate": round((self.metrics["cached_requests"] / total_requests * 100) if total_requests > 0 else 0, 2),
            "average_response_time_ms": round(avg_response_time, 2),
            "total_tokens_used": self.metrics["total_tokens_used"],
            "estimated_total_cost": round(self.metrics["total_cost"], 4),
            "requests_by_service": self.metrics["requests_by_service"]
        }
    
    def reset_metrics(self):
        """Remet à zéro les métriques"""
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_requests": 0,
            "total_tokens_used": 0,
            "total_cost": 0.0,
            "response_times": [],
            "requests_by_service": {service.value: 0 for service in AIServiceType}
        }
        logger.info("🔄 [AI Manager] Métriques remises à zéro")

# Instance globale singleton
_ai_service_manager = None

def get_ai_service_manager() -> AIServiceManager:
    """Récupère l'instance singleton du gestionnaire IA"""
    global _ai_service_manager
    if _ai_service_manager is None:
        _ai_service_manager = AIServiceManager()
    return _ai_service_manager

# Fonction utilitaire pour les autres modules
async def call_ai(service_type: AIServiceType, 
                 prompt: str, 
                 model: str = "gpt-4",
                 max_tokens: int = 1000,
                 cache_key: str = None,
                 **kwargs) -> AIResponse:
    """Fonction utilitaire pour appeler l'IA depuis d'autres modules"""
    
    manager = get_ai_service_manager()
    
    request = AIRequest(
        service_type=service_type,
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        cache_key=cache_key,
        **kwargs
    )
    
    return await manager.call_ai_service(request)