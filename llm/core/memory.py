# -*- coding: utf-8 -*-
"""
memory.py - Mémoire conversationnelle avec support contextualisation
Version 4.2 - Gestion des clarifications en attente
"""

import logging
import time
import os
from utils.types import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# 🔧 Limite augmentée pour permettre plus de contexte conversationnel
# Import avec fallback si non défini dans config
try:
    from config.config import MAX_CONVERSATION_CONTEXT

    # Si la valeur est trop basse, utiliser 2000
    if MAX_CONVERSATION_CONTEXT < 2000:
        MAX_CONVERSATION_CONTEXT = 2000  # Environ 500 tokens
except (ImportError, AttributeError):
    MAX_CONVERSATION_CONTEXT = 2000  # Environ 500 tokens par défaut


class ConversationMemory:
    """Mémoire conversationnelle avec contexte et clarifications"""

    # 🔄 Stockage partagé entre toutes les instances
    _shared_memory_store = {}
    _shared_pending_clarifications = {}

    def __init__(self, client=None):
        self.client = client
        # Utilisation de la configuration centralisée
        self.max_exchanges = int(
            os.getenv("MAX_EXCHANGES", "8")
        )  # Source unique de vérité depuis env

    async def get_contextual_memory(self, tenant_id: str, current_query: str) -> str:
        """
        Récupère le contexte conversationnel enrichi

        Returns:
            String formatée pour rétrocompatibilité (les autres modules attendent une string)
            Le query_enricher extraira les entités de cette string
        """

        # 🔍 DEBUG CRITIQUE - Logs d'entrée
        logger.info("🔍 MEMORY - get_contextual_memory appelée")
        logger.info(f"🔍 MEMORY - tenant_id: {tenant_id}")
        logger.info(f"🔍 MEMORY - current_query: {current_query[:50]}...")
        logger.info(
            f"🔍 MEMORY - memory_store keys: {list(self._shared_memory_store.keys())}"
        )

        if tenant_id not in self._shared_memory_store:
            logger.info(f"🔍 MEMORY - Aucun historique pour tenant_id: {tenant_id}")
            return ""

        history = self._shared_memory_store[tenant_id]

        # 🔍 DEBUG - État de l'historique
        logger.info(f"🔍 MEMORY - Historique trouvé, longueur: {len(history)}")

        if not history:
            logger.info(f"🔍 MEMORY - Historique vide pour tenant_id: {tenant_id}")
            return ""

        try:
            # Prendre les N derniers échanges
            recent_exchanges = history[-self.max_exchanges :]

            context_parts = []
            total_length = 0

            # 🔍 DEBUG - Traitement des échanges
            logger.info(
                f"🔍 MEMORY - Traitement de {len(recent_exchanges)} échanges récents"
            )

            for i, exchange in enumerate(reversed(recent_exchanges)):
                question = exchange.get("question", "")
                answer = exchange.get("answer", "")

                if not question or not answer:
                    logger.info(
                        f"🔍 MEMORY - Échange {i} ignoré (question ou réponse vide)"
                    )
                    continue

                # Format: Q: ... R: ...
                exchange_text = f"Q: {question[:200]}... R: {answer[:200]}..."
                exchange_length = len(exchange_text)

                logger.info(
                    f"🔍 MEMORY - Échange {i}: Q={question[:50]}... R={answer[:50]}..."
                )
                logger.info(
                    f"🔍 MEMORY - Longueur échange {i}: {exchange_length} caractères"
                )
                logger.info(
                    f"🔍 MEMORY - Longueur actuelle contexte: {total_length} caractères"
                )
                logger.info(
                    f"🔍 MEMORY - Limite MAX_CONVERSATION_CONTEXT: {MAX_CONVERSATION_CONTEXT} caractères"
                )

                if total_length + exchange_length > MAX_CONVERSATION_CONTEXT:
                    logger.info(
                        f"🔍 MEMORY - Limite atteinte, stop à {i} échanges (dépassement: {total_length + exchange_length} > {MAX_CONVERSATION_CONTEXT})"
                    )
                    break

                context_parts.insert(0, exchange_text)
                total_length += exchange_length

                logger.info(
                    f"🔍 MEMORY - Échange {i} ajouté, total_length: {total_length}"
                )

            if not context_parts:
                logger.info("🔍 MEMORY - Aucun échange valide à retourner")
                return ""

            # Formater avec header pour que query_enricher puisse parser
            formatted_context = "\n".join(context_parts)

            # 🔍 DEBUG - Résultat final
            logger.info(
                f"🔍 MEMORY - Contexte formaté (longueur: {len(formatted_context)})"
            )
            logger.info(
                f"🔍 MEMORY - Contexte preview: {formatted_context[:200] if formatted_context else 'VIDE'}..."
            )
            logger.info(f"🔍 MEMORY - Nombre d'échanges inclus: {len(context_parts)}")

            return formatted_context

        except Exception as e:
            logger.error(
                f"❌ MEMORY - Exception dans get_contextual_memory: {e}", exc_info=True
            )
            logger.error(f"❌ MEMORY - Type erreur: {type(e).__name__}")
            logger.error(
                f"❌ MEMORY - État memory_store au moment de l'erreur: {len(self._shared_memory_store)}"
            )
            return ""

    def add_exchange(self, tenant_id: str, question: str, answer: str):
        """Ajoute un échange avec métadonnées dans le store partagé"""
        if tenant_id not in self._shared_memory_store:
            self._shared_memory_store[tenant_id] = []

        self._shared_memory_store[tenant_id].append(
            {"question": question, "answer": answer, "timestamp": time.time()}
        )

        # 🔍 DEBUG - Sauvegarde
        logger.debug(
            f"💾 SAVE - memory_store keys: {list(self._shared_memory_store.keys())}"
        )
        logger.debug(
            f"💾 SAVE - tenant {tenant_id} entries: {len(self._shared_memory_store[tenant_id])}"
        )

        # Maintenir la limite d'échanges
        if len(self._shared_memory_store[tenant_id]) > self.max_exchanges:
            self._shared_memory_store[tenant_id] = self._shared_memory_store[tenant_id][
                -self.max_exchanges :
            ]

    def clear_memory(self, tenant_id: str):
        """Efface la mémoire pour un tenant"""
        if tenant_id in self._shared_memory_store:
            del self._shared_memory_store[tenant_id]

        # 🆕 Nettoyer aussi les clarifications en attente
        if tenant_id in self._shared_pending_clarifications:
            del self._shared_pending_clarifications[tenant_id]

    def get_memory_stats(self, tenant_id: str) -> dict:
        """Statistiques de la mémoire pour un tenant"""
        if tenant_id not in self._shared_memory_store:
            return {"exchanges": 0, "total_characters": 0}

        history = self._shared_memory_store[tenant_id]
        total_chars = sum(len(ex["question"]) + len(ex["answer"]) for ex in history)

        stats = {
            "exchanges": len(history),
            "total_characters": total_chars,
            "oldest_timestamp": history[0]["timestamp"] if history else None,
            "newest_timestamp": history[-1]["timestamp"] if history else None,
        }

        # 🆕 Ajouter info sur clarifications en attente
        if tenant_id in self._shared_pending_clarifications:
            stats["pending_clarification"] = True
            stats["clarification_timestamp"] = self._shared_pending_clarifications[
                tenant_id
            ].get("timestamp")

        return stats

    # 🆕 ================================================================
    # NOUVELLES MÉTHODES POUR GESTION DES CLARIFICATIONS
    # ================================================================

    def mark_pending_clarification(
        self,
        tenant_id: str,
        original_query: str,
        missing_fields: List[str],
        suggestions: Optional[Dict[str, List[str]]] = None,
        language: str = "fr",
    ):
        """
        Marque une conversation comme en attente de clarification

        Args:
            tenant_id: Identifiant du tenant
            original_query: Question originale incomplète
            missing_fields: Liste des champs manquants (breed, age_days, etc.)
            suggestions: Suggestions pour chaque champ manquant
            language: Langue de la conversation
        """
        self._shared_pending_clarifications[tenant_id] = {
            "original_query": original_query,
            "missing_fields": missing_fields,
            "suggestions": suggestions or {},
            "language": language,
            "timestamp": time.time(),
            "attempts": 0,  # Nombre de tentatives de clarification
        }

        logger.info(
            f"🔒 Clarification marquée en attente pour {tenant_id}: "
            f"manquant={missing_fields}"
        )

    def get_pending_clarification(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le contexte de clarification en attente

        Args:
            tenant_id: Identifiant du tenant

        Returns:
            Dict avec original_query, missing_fields, suggestions, language, timestamp
            ou None si pas de clarification en attente
        """
        return self._shared_pending_clarifications.get(tenant_id)

    def clear_pending_clarification(self, tenant_id: str):
        """
        Efface la clarification en attente après résolution

        Args:
            tenant_id: Identifiant du tenant
        """
        if tenant_id in self._shared_pending_clarifications:
            del self._shared_pending_clarifications[tenant_id]
            logger.info(f"✅ Clarification résolue pour {tenant_id}")

    def increment_clarification_attempt(self, tenant_id: str):
        """
        Incrémente le compteur de tentatives de clarification
        Utile pour éviter les boucles infinies

        Args:
            tenant_id: Identifiant du tenant
        """
        if tenant_id in self._shared_pending_clarifications:
            self._shared_pending_clarifications[tenant_id]["attempts"] += 1
            attempts = self._shared_pending_clarifications[tenant_id]["attempts"]

            logger.info(f"🔄 Tentative clarification #{attempts} pour {tenant_id}")

            # Sécurité: effacer après trop de tentatives
            if attempts >= 3:
                logger.warning(
                    f"⚠️ Trop de tentatives de clarification pour {tenant_id}, "
                    f"abandon et reset"
                )
                self.clear_pending_clarification(tenant_id)

    def is_clarification_response(self, message: str, tenant_id: str) -> bool:
        """
        Détecte si un message est une réponse à une demande de clarification

        Args:
            message: Message de l'utilisateur
            tenant_id: Identifiant du tenant

        Returns:
            True si c'est probablement une réponse à la clarification
        """
        pending = self.get_pending_clarification(tenant_id)
        if not pending:
            return False

        missing = pending.get("missing_fields", [])
        message_lower = message.lower()

        # Détection de races/souches communes
        common_breeds = [
            "ross",
            "cobb",
            "hubbard",
            "aviagen",
            "isa",
            "lohmann",
            "308",
            "500",
            "700",
            "classic",
            "flex",
        ]
        if "breed" in missing:
            if any(breed in message_lower for breed in common_breeds):
                return True

        # Détection d'âge en jours
        if "age_days" in missing:
            import re

            # Patterns: "21 jours", "35 days", "42j", "3 semaines"
            age_patterns = [
                r"\d+\s*(jour|day|j\b)",
                r"\d+\s*(semaine|week)",
                r"à\s*\d+",
                r"day\s*\d+",
            ]
            if any(re.search(pattern, message_lower) for pattern in age_patterns):
                return True

        # Détection de sexe
        if "sex" in missing:
            sex_keywords = [
                "mâle",
                "male",
                "femelle",
                "female",
                "mixte",
                "mixed",
                "as hatched",
            ]
            if any(keyword in message_lower for keyword in sex_keywords):
                return True

        # Détection de métriques
        if "metric_type" in missing:
            metric_keywords = [
                "poids",
                "weight",
                "fcr",
                "conversion",
                "mortalité",
                "mortality",
                "consommation",
                "feed",
                "gain",
            ]
            if any(keyword in message_lower for keyword in metric_keywords):
                return True

        return False

    def merge_query_with_clarification(
        self, original_query: str, clarification_response: str
    ) -> str:
        """
        Fusionne la question originale avec la réponse de clarification

        Args:
            original_query: Question originale
            clarification_response: Réponse de l'utilisateur

        Returns:
            Question fusionnée
        """
        # Nettoyage des réponses
        clarification_clean = clarification_response.strip()

        # Fusion intelligente
        # Si la réponse est courte (< 10 mots), l'ajouter directement
        if len(clarification_clean.split()) < 10:
            merged = f"{original_query} {clarification_clean}"
        else:
            # Si c'est une phrase complète, essayer d'extraire l'info clé
            merged = f"{original_query}. Contexte additionnel: {clarification_clean}"

        logger.info(f"🔗 Question fusionnée: {merged[:100]}...")
        return merged

    def get_all_pending_clarifications(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère toutes les clarifications en attente (pour monitoring)

        Returns:
            Dictionnaire {tenant_id: clarification_data}
        """
        return self._shared_pending_clarifications.copy()

    def cleanup_old_clarifications(self, max_age_seconds: int = 3600):
        """
        Nettoie les clarifications trop anciennes (> 1h par défaut)
        Évite l'accumulation de contextes abandonnés

        Args:
            max_age_seconds: Âge maximum en secondes (défaut: 3600 = 1h)
        """
        current_time = time.time()
        to_remove = []

        for tenant_id, clarification in self._shared_pending_clarifications.items():
            age = current_time - clarification.get("timestamp", current_time)
            if age > max_age_seconds:
                to_remove.append(tenant_id)

        for tenant_id in to_remove:
            logger.info(
                f"🧹 Nettoyage clarification expirée pour {tenant_id} "
                f"(âge: {age/60:.1f} minutes)"
            )
            del self._shared_pending_clarifications[tenant_id]

        if to_remove:
            logger.info(f"🧹 {len(to_remove)} clarifications expirées nettoyées")

    def get_clarification_stats(self) -> Dict[str, Any]:
        """
        Statistiques sur les clarifications en attente

        Returns:
            Dict avec statistiques globales
        """
        if not self._shared_pending_clarifications:
            return {"total_pending": 0, "avg_age_seconds": 0, "by_missing_field": {}}

        current_time = time.time()
        ages = []
        missing_fields_count = {}

        for clarification in self._shared_pending_clarifications.values():
            # Âge
            age = current_time - clarification.get("timestamp", current_time)
            ages.append(age)

            # Comptage des champs manquants
            for field in clarification.get("missing_fields", []):
                missing_fields_count[field] = missing_fields_count.get(field, 0) + 1

        return {
            "total_pending": len(self._shared_pending_clarifications),
            "avg_age_seconds": sum(ages) / len(ages) if ages else 0,
            "max_age_seconds": max(ages) if ages else 0,
            "by_missing_field": missing_fields_count,
            "total_attempts": sum(
                c.get("attempts", 0)
                for c in self._shared_pending_clarifications.values()
            ),
        }
