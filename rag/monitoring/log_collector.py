"""
Log Collector - Collecte et agrège les logs des services pour le monitoring
Version: 1.0.0

Ce module collecte les logs en temps réel des services et les expose via API
pour affichage dans le frontend.
"""

import asyncio
import httpx
import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """Entrée de log"""

    timestamp: str
    service: str
    level: str
    message: str
    context: Optional[Dict] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class ServiceHealth:
    """État de santé d'un service"""

    service: str
    status: str  # "healthy", "degraded", "unhealthy", "unknown"
    last_check: str
    response_time_ms: Optional[float]
    error_message: Optional[str] = None


class LogCollector:
    """
    Collecteur de logs centralisé pour le monitoring

    Conserve les derniers logs en mémoire pour affichage rapide
    dans le frontend.
    """

    def __init__(self, max_logs: int = 500):
        """
        Args:
            max_logs: Nombre maximum de logs à conserver en mémoire
        """
        self.max_logs = max_logs
        self.logs: deque[LogEntry] = deque(maxlen=max_logs)
        self.services: Dict[str, ServiceHealth] = {}
        self._lock = asyncio.Lock()

    def add_log(
        self, service: str, level: str, message: str, context: Optional[Dict] = None
    ):
        """Ajoute un log"""
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            service=service,
            level=level,
            message=message,
            context=context,
        )
        self.logs.append(entry)

    async def check_service_health(
        self, service_name: str, base_url: str, endpoint: str = "/health"
    ):
        """Vérifie la santé d'un service"""
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}{endpoint}")
                response_time = (time.time() - start) * 1000

                if response.status_code == 200:
                    status = "healthy"
                    error_msg = None
                else:
                    status = "degraded"
                    error_msg = f"HTTP {response.status_code}"

                health = ServiceHealth(
                    service=service_name,
                    status=status,
                    last_check=datetime.now().isoformat(),
                    response_time_ms=response_time,
                    error_message=error_msg,
                )

                async with self._lock:
                    self.services[service_name] = health

                # Log le résultat
                self.add_log(
                    service=service_name,
                    level="INFO" if status == "healthy" else "WARNING",
                    message=f"Health check: {status} ({response_time:.0f}ms)",
                    context={"response_time_ms": response_time},
                )

                return health

        except httpx.ConnectError:
            health = ServiceHealth(
                service=service_name,
                status="unhealthy",
                last_check=datetime.now().isoformat(),
                response_time_ms=None,
                error_message="Connection failed",
            )

            async with self._lock:
                self.services[service_name] = health

            self.add_log(
                service=service_name,
                level="ERROR",
                message="Health check failed: Connection refused",
                context={},
            )

            return health

        except httpx.TimeoutException:
            health = ServiceHealth(
                service=service_name,
                status="degraded",
                last_check=datetime.now().isoformat(),
                response_time_ms=None,
                error_message="Timeout",
            )

            async with self._lock:
                self.services[service_name] = health

            self.add_log(
                service=service_name,
                level="WARNING",
                message="Health check timeout",
                context={},
            )

            return health

        except Exception as e:
            health = ServiceHealth(
                service=service_name,
                status="unknown",
                last_check=datetime.now().isoformat(),
                response_time_ms=None,
                error_message=str(e),
            )

            async with self._lock:
                self.services[service_name] = health

            self.add_log(
                service=service_name,
                level="ERROR",
                message=f"Health check error: {e}",
                context={},
            )

            return health

    def get_logs(
        self,
        limit: Optional[int] = None,
        service: Optional[str] = None,
        level: Optional[str] = None,
    ) -> List[Dict]:
        """
        Récupère les logs filtrés

        Args:
            limit: Nombre maximum de logs à retourner
            service: Filtrer par service
            level: Filtrer par niveau (INFO, WARNING, ERROR)

        Returns:
            Liste de logs au format dict
        """
        logs = list(self.logs)

        # Filtrer par service
        if service:
            logs = [log for log in logs if log.service == service]

        # Filtrer par niveau
        if level:
            logs = [log for log in logs if log.level == level]

        # Limiter le nombre
        if limit:
            logs = logs[-limit:]

        # Trier par timestamp décroissant (plus récents en premier)
        logs.reverse()

        return [log.to_dict() for log in logs]

    def get_services_health(self) -> List[Dict]:
        """Retourne l'état de santé de tous les services"""
        return [asdict(health) for health in self.services.values()]

    def get_summary(self) -> Dict:
        """Retourne un résumé du monitoring"""
        total_logs = len(self.logs)
        errors = sum(1 for log in self.logs if log.level == "ERROR")
        warnings = sum(1 for log in self.logs if log.level == "WARNING")

        healthy_services = sum(
            1 for s in self.services.values() if s.status == "healthy"
        )
        total_services = len(self.services)

        return {
            "total_logs": total_logs,
            "errors": errors,
            "warnings": warnings,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "last_update": datetime.now().isoformat(),
        }


# Instance globale du collecteur
_log_collector = None


def get_log_collector() -> LogCollector:
    """Retourne l'instance globale du collecteur de logs"""
    global _log_collector
    if _log_collector is None:
        _log_collector = LogCollector(max_logs=500)
    return _log_collector
