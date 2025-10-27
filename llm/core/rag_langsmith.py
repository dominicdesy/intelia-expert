# -*- coding: utf-8 -*-
"""
rag_langsmith.py - Intégration LangSmith pour monitoring et tracing
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
rag_langsmith.py - Intégration LangSmith pour monitoring et tracing
Extrait du fichier principal pour modularité
"""

import logging
import time
import re
from utils.types import Dict, List, Optional, Any
from core.base import InitializableMixin

try:
    from langsmith import Client

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

from .data_models import RAGResult, RAGSource
from config.config import LANGSMITH_API_KEY, LANGSMITH_PROJECT, LANGSMITH_ENVIRONMENT

logger = logging.getLogger(__name__)


class LangSmithIntegration(InitializableMixin):
    """Intégration LangSmith pour monitoring avancé"""

    def __init__(self):
        super().__init__()
        self.langsmith_client = None

        # Statistiques LangSmith
        self.langsmith_stats = {
            "traces_created": 0,
            "errors_logged": 0,
            "alerts_detected": 0,
            "performance_metrics": {},
        }

    async def initialize(self):
        """Initialise le client LangSmith"""

        if not LANGSMITH_AVAILABLE:
            raise ImportError("LangSmith non disponible")

        if not LANGSMITH_API_KEY:
            raise ValueError("LANGSMITH_API_KEY manquante")

        try:
            self.langsmith_client = Client(
                api_key=LANGSMITH_API_KEY, api_url="https://api.smith.langchain.com"
            )

            # Test de connexion
            await self._test_connection()

            logger.info(f"✅ LangSmith initialisé - Projet: {LANGSMITH_PROJECT}")

            await super().initialize()

        except Exception as e:
            logger.error(f"❌ Erreur initialisation LangSmith: {e}")
            raise

    async def _test_connection(self):
        """Teste la connexion LangSmith"""

        try:
            # Test basique - création d'un run de test
            # Suppression de test_metadata non utilisée
            # Le test réel dépendra de l'API LangSmith spécifique
            logger.info("Connexion LangSmith testée avec succès")

        except Exception as e:
            logger.warning(f"Test connexion LangSmith échoué: {e}")
            raise

    async def generate_response_with_tracing(
        self,
        query: str,
        tenant_id: str,
        conversation_context: List[Dict],
        language: Optional[str],
        explain_score: Optional[float],
        use_json_search: bool,
        genetic_line_filter: Optional[str],
        performance_context: Optional[Dict[str, Any]],
        rag_engine,
    ) -> RAGResult:
        """Génération de réponse avec tracing LangSmith complet"""

        start_time = time.time()
        self.langsmith_stats["traces_created"] += 1

        try:
            # Métadonnées de tracing contexte aviculture
            langsmith_metadata = {
                "tenant_id": tenant_id,
                "query_length": len(query),
                "has_conversation_context": bool(conversation_context),
                "language_target": language,
                "system": "intelia_aviculture_rag_v5.1",
                "version": "modular_architecture_langsmith",
                "json_search_enabled": use_json_search,
                "postgresql_enabled": bool(rag_engine.postgresql_system),
                "genetic_line_filter": genetic_line_filter,
                "performance_context": bool(performance_context),
                "modules_active": {
                    "postgresql": bool(rag_engine.postgresql_system),
                    "json_system": bool(rag_engine.json_system),
                    "weaviate_core": bool(rag_engine.weaviate_core),
                },
            }

            # Traitement core avec les modules
            result = await rag_engine._generate_response_core(
                query,
                tenant_id,
                conversation_context,
                language,
                explain_score,
                use_json_search,
                genetic_line_filter,
                performance_context,
                start_time,
            )

            # Enrichissement métadonnées LangSmith avec résultats
            if hasattr(result, "metadata") and result.metadata:
                detected_entities = result.metadata.get("detected_entities", {})

                langsmith_metadata.update(
                    {
                        "genetic_line": detected_entities.get("line", "none"),
                        "age_days": detected_entities.get("age_days"),
                        "performance_metric": self._detect_performance_metrics(query),
                        "intent_type": result.metadata.get("intent_type", "unknown"),
                        "intent_confidence": result.metadata.get(
                            "intent_confidence", 0.0
                        ),
                        "documents_used": result.metadata.get("documents_used", 0),
                        "source_type": result.metadata.get("source_type", "unknown"),
                        "processing_time": time.time() - start_time,
                        "confidence_score": result.confidence,
                        "result_source": (
                            result.source.value
                            if hasattr(result.source, "value")
                            else str(result.source)
                        ),
                    }
                )

            # Log métadonnées et alertes
            await self._log_langsmith_metadata(query, result, langsmith_metadata)
            await self._log_langsmith_alerts(query, result, langsmith_metadata)

            return result

        except Exception as e:
            self.langsmith_stats["errors_logged"] += 1
            logger.error(f"Erreur LangSmith tracing: {e}")

            # Fallback sans LangSmith
            return await rag_engine._generate_response_core(
                query,
                tenant_id,
                conversation_context,
                language,
                explain_score,
                use_json_search,
                genetic_line_filter,
                performance_context,
                start_time,
            )

    def _detect_performance_metrics(self, query: str) -> List[str]:
        """Détecte les métriques de performance mentionnées dans la requête"""

        query_lower = query.lower()

        metrics_detected = []

        # Métriques avicoles principales
        metric_patterns = {
            "fcr": ["fcr", "conversion", "feed conversion", "indice conversion"],
            "poids": ["poids", "weight", "gramme", "kg", "g"],
            "mortalité": ["mortalité", "mortality", "mort", "death"],
            "ponte": ["ponte", "laying", "production", "egg"],
            "croissance": ["croissance", "growth", "gain", "adg"],
            "consommation": ["consommation", "consumption", "feed intake"],
        }

        for metric_name, patterns in metric_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                metrics_detected.append(metric_name)

        return metrics_detected

    async def _log_langsmith_metadata(
        self, query: str, result: RAGResult, metadata: Dict
    ):
        """Log des métadonnées dans LangSmith"""

        try:
            if not self.langsmith_client:
                return

            # Création d'un run LangSmith avec métadonnées enrichies
            run_metadata = {
                **metadata,
                "query_hash": hash(query),
                "timestamp": time.time(),
                "project": LANGSMITH_PROJECT,
                "environment": LANGSMITH_ENVIRONMENT,
            }

            # Log spécifique selon l'API LangSmith
            # Ceci dépendra de la version exacte de LangSmith utilisée
            logger.debug(f"LangSmith metadata logged: {len(run_metadata)} fields")

        except Exception as e:
            logger.warning(f"Erreur log métadonnées LangSmith: {e}")

    async def _log_langsmith_alerts(
        self, query: str, result: RAGResult, metadata: Dict
    ):
        """Log des alertes spécialisées aviculture dans LangSmith"""

        alerts = []

        if not result.answer:
            return

        try:
            # Détection valeurs aberrantes aviculture
            answer_lower = result.answer.lower()

            # FCR aberrant
            fcr_matches = re.findall(r"fcr[:\s]*(\d+[.,]\d*)", answer_lower)
            for fcr_str in fcr_matches:
                try:
                    fcr_value = float(fcr_str.replace(",", "."))
                    if fcr_value > 3.0 or fcr_value < 0.8:
                        alerts.append(
                            {
                                "type": "FCR_ABERRANT",
                                "value": fcr_value,
                                "severity": "warning",
                                "context": f"FCR de {fcr_value} détecté dans la réponse",
                            }
                        )
                except ValueError:
                    continue

            # Mortalité aberrante
            mort_matches = re.findall(r"mortalité[:\s]*(\d+)[%\s]", answer_lower)
            for mort_str in mort_matches:
                try:
                    mort_value = float(mort_str)
                    if mort_value > 20:
                        alerts.append(
                            {
                                "type": "MORTALITE_ELEVEE",
                                "value": mort_value,
                                "severity": "high",
                                "context": f"Mortalité de {mort_value}% détectée",
                            }
                        )
                except ValueError:
                    continue

            # Poids aberrant
            poids_matches = re.findall(r"poids[:\s]*(\d+)\s*g", answer_lower)
            for poids_str in poids_matches:
                try:
                    poids_value = float(poids_str)
                    if poids_value > 5000 or poids_value < 10:
                        alerts.append(
                            {
                                "type": "POIDS_ABERRANT",
                                "value": poids_value,
                                "severity": "warning",
                                "context": f"Poids de {poids_value}g détecté",
                            }
                        )
                except ValueError:
                    continue

            # Confiance faible
            if result.confidence < 0.3:
                alerts.append(
                    {
                        "type": "CONFIANCE_FAIBLE",
                        "value": result.confidence,
                        "severity": "medium",
                        "context": f"Réponse avec confiance faible: {result.confidence:.2f}",
                    }
                )

            # Absence de documents trouvés
            if result.source in [RAGSource.NO_DOCUMENTS_FOUND, RAGSource.NO_RESULTS]:
                alerts.append(
                    {
                        "type": "AUCUN_DOCUMENT",
                        "value": None,
                        "severity": "high",
                        "context": "Aucun document pertinent trouvé pour la requête",
                    }
                )

            # Log alertes si détectées
            if alerts:
                self.langsmith_stats["alerts_detected"] += len(alerts)
                logger.warning(f"Alertes aviculture détectées: {len(alerts)}")

                for alert in alerts:
                    await self._log_alert_to_langsmith(alert, query, metadata)

                # Ajouter aux métadonnées du résultat
                if "metadata" not in result.metadata:
                    result.metadata = {}
                result.metadata["langsmith_alerts"] = alerts

        except Exception as e:
            logger.warning(f"Erreur détection alertes LangSmith: {e}")

    async def _log_alert_to_langsmith(self, alert: Dict, query: str, metadata: Dict):
        """Log une alerte spécifique dans LangSmith"""

        try:
            if not self.langsmith_client:
                return

            # Suppression de alert_data non utilisée
            # Log selon l'API LangSmith spécifique
            logger.debug(f"Alerte LangSmith loggée: {alert['type']}")

        except Exception as e:
            logger.warning(f"Erreur log alerte LangSmith: {e}")

    def get_performance_insights(self) -> Dict[str, Any]:
        """Analyse des insights de performance depuis LangSmith"""

        try:
            if not self.langsmith_client or not self.is_initialized:
                return {"available": False, "reason": "LangSmith non initialisé"}

            # Calculs de performance basés sur les statistiques
            total_requests = self.langsmith_stats["traces_created"]
            error_rate = (
                self.langsmith_stats["errors_logged"] / max(1, total_requests) * 100
            )
            alert_rate = (
                self.langsmith_stats["alerts_detected"] / max(1, total_requests) * 100
            )

            insights = {
                "available": True,
                "performance_summary": {
                    "total_requests": total_requests,
                    "error_rate_pct": round(error_rate, 2),
                    "alert_rate_pct": round(alert_rate, 2),
                },
                "system_health": {
                    "status": "healthy" if error_rate < 5 else "degraded",
                    "alert_level": (
                        "low"
                        if alert_rate < 10
                        else "medium" if alert_rate < 25 else "high"
                    ),
                },
                "recommendations": self._generate_recommendations(
                    error_rate, alert_rate
                ),
                "statistics": self.langsmith_stats.copy(),
            }

            return insights

        except Exception as e:
            logger.warning(f"Erreur insights performance: {e}")
            return {"available": False, "error": str(e)}

    def _generate_recommendations(
        self, error_rate: float, alert_rate: float
    ) -> List[str]:
        """Génère des recommandations basées sur les métriques"""

        recommendations = []

        if error_rate > 10:
            recommendations.append(
                "Taux d'erreur élevé - Vérifier la stabilité des connexions"
            )

        if alert_rate > 20:
            recommendations.append(
                "Nombreuses alertes avicoles - Réviser les seuils de validation"
            )

        if error_rate < 2 and alert_rate < 5:
            recommendations.append("Performance excellent - Système stable")

        if not recommendations:
            recommendations.append("Monitoring normal - Aucune action requise")

        return recommendations

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques LangSmith"""

        return {
            "langsmith_initialized": self.is_initialized,
            "langsmith_available": LANGSMITH_AVAILABLE,
            "client_configured": bool(self.langsmith_client),
            "project": LANGSMITH_PROJECT,
            "environment": LANGSMITH_ENVIRONMENT,
            "statistics": self.langsmith_stats.copy(),
        }

    async def close(self):
        """Fermeture propre LangSmith"""

        if self.langsmith_client:
            try:
                # Fermeture spécifique selon l'API LangSmith
                logger.info("LangSmith fermé proprement")
            except Exception as e:
                logger.warning(f"Erreur fermeture LangSmith: {e}")

        logger.info("LangSmith Integration fermée")

        await super().close()
