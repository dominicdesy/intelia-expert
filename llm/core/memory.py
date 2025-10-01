# -*- coding: utf-8 -*-
"""
memory.py - Mémoire conversationnelle avec support contextualisation
Version 4.2 - Gestion des clarifications en attente
"""

import logging
import time
import os
from typing import Dict, List, Optional, Any

# Import modulaire depuis config
from config.config import MAX_CONVERSATION_CONTEXT

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Mémoire conversationnelle avec contexte et clarifications"""

    def __init__(self, client):
        self.client = client
        self.memory_store = {}
        # 🆕 Stockage des clarifications en attente
        self.pending_clarifications = {}
        # Utilisation de la configuration centralisée
        self.max_exchanges = int(
            os.getenv("MAX_EXCHANGES", "8")
        )  # Source unique de vérité depuis env

    async def get_contextual_memory(self, tenant_id: str, current_query: str) -> str:
        """Récupère le contexte conversationnel enrichi"""
        if tenant_id not in self.memory_store:
            return ""

        history = self.memory_store[tenant_id]
        if not history:
            return ""

        try:
            # Retourner les 2-3 derniers échanges selon la longueur
            context_parts = []
            total_length = 0

            for exchange in reversed(history[-3:]):  # 3 derniers max
                exchange_text = f"Q: {exchange['question'][:150]}... R: {exchange['answer'][:200]}..."
                if total_length + len(exchange_text) <= MAX_CONVERSATION_CONTEXT:
                    context_parts.insert(0, exchange_text)
                    total_length += len(exchange_text)
                else:
                    break

            return " | ".join(context_parts)

        except Exception as e:
            logger.warning(f"Erreur mémoire: {e}")
            return ""

    def add_exchange(self, tenant_id: str, question: str, answer: str):
        """Ajoute un échange avec métadonnées"""
        if tenant_id not in self.memory_store:
            self.memory_store[tenant_id] = []

        self.memory_store[tenant_id].append(
            {"question": question, "answer": answer, "timestamp": time.time()}
        )

        # Maintenir la limite d'échanges
        if len(self.memory_store[tenant_id]) > self.max_exchanges:
            self.memory_store[tenant_id] = self.memory_store[tenant_id][
                -self.max_exchanges :
            ]

    def clear_memory(self, tenant_id: str):
        """Efface la mémoire pour un tenant"""
        if tenant_id in self.memory_store:
            del self.memory_store[tenant_id]

        # 🆕 Nettoyer aussi les clarifications en attente
        if tenant_id in self.pending_clarifications:
            del self.pending_clarifications[tenant_id]

    def get_memory_stats(self, tenant_id: str) -> dict:
        """Statistiques de la mémoire pour un tenant"""
        if tenant_id not in self.memory_store:
            return {"exchanges": 0, "total_characters": 0}

        history = self.memory_store[tenant_id]
        total_chars = sum(len(ex["question"]) + len(ex["answer"]) for ex in history)

        stats = {
            "exchanges": len(history),
            "total_characters": total_chars,
            "oldest_timestamp": history[0]["timestamp"] if history else None,
            "newest_timestamp": history[-1]["timestamp"] if history else None,
        }

        # 🆕 Ajouter info sur clarifications en attente
        if tenant_id in self.pending_clarifications:
            stats["pending_clarification"] = True
            stats["clarification_timestamp"] = self.pending_clarifications[
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
        self.pending_clarifications[tenant_id] = {
            "original_query": original_query,
            "missing_fields": missing_fields,
            "suggestions": suggestions or {},
            "language": language,
            "timestamp": time.time(),
            "attempts": 0,  # Nombre de tentatives de clarification
        }

        logger.info(
            f"🔔 Clarification marquée en attente pour {tenant_id}: "
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
        return self.pending_clarifications.get(tenant_id)

    def clear_pending_clarification(self, tenant_id: str):
        """
        Efface la clarification en attente après résolution

        Args:
            tenant_id: Identifiant du tenant
        """
        if tenant_id in self.pending_clarifications:
            del self.pending_clarifications[tenant_id]
            logger.info(f"✅ Clarification résolue pour {tenant_id}")

    def increment_clarification_attempt(self, tenant_id: str):
        """
        Incrémente le compteur de tentatives de clarification
        Utile pour éviter les boucles infinies

        Args:
            tenant_id: Identifiant du tenant
        """
        if tenant_id in self.pending_clarifications:
            self.pending_clarifications[tenant_id]["attempts"] += 1
            attempts = self.pending_clarifications[tenant_id]["attempts"]

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

        logger.info(f"📝 Question fusionnée: {merged[:100]}...")
        return merged

    def get_all_pending_clarifications(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère toutes les clarifications en attente (pour monitoring)

        Returns:
            Dictionnaire {tenant_id: clarification_data}
        """
        return self.pending_clarifications.copy()

    def cleanup_old_clarifications(self, max_age_seconds: int = 3600):
        """
        Nettoie les clarifications trop anciennes (> 1h par défaut)
        Évite l'accumulation de contextes abandonnés

        Args:
            max_age_seconds: Âge maximum en secondes (défaut: 3600 = 1h)
        """
        current_time = time.time()
        to_remove = []

        for tenant_id, clarification in self.pending_clarifications.items():
            age = current_time - clarification.get("timestamp", current_time)
            if age > max_age_seconds:
                to_remove.append(tenant_id)

        for tenant_id in to_remove:
            logger.info(
                f"🧹 Nettoyage clarification expirée pour {tenant_id} "
                f"(âge: {age/60:.1f} minutes)"
            )
            del self.pending_clarifications[tenant_id]

        if to_remove:
            logger.info(f"🧹 {len(to_remove)} clarifications expirées nettoyées")

    def get_clarification_stats(self) -> Dict[str, Any]:
        """
        Statistiques sur les clarifications en attente

        Returns:
            Dict avec statistiques globales
        """
        if not self.pending_clarifications:
            return {"total_pending": 0, "avg_age_seconds": 0, "by_missing_field": {}}

        current_time = time.time()
        ages = []
        missing_fields_count = {}

        for clarification in self.pending_clarifications.values():
            # Âge
            age = current_time - clarification.get("timestamp", current_time)
            ages.append(age)

            # Comptage des champs manquants
            for field in clarification.get("missing_fields", []):
                missing_fields_count[field] = missing_fields_count.get(field, 0) + 1

        return {
            "total_pending": len(self.pending_clarifications),
            "avg_age_seconds": sum(ages) / len(ages) if ages else 0,
            "max_age_seconds": max(ages) if ages else 0,
            "by_missing_field": missing_fields_count,
            "total_attempts": sum(
                c.get("attempts", 0) for c in self.pending_clarifications.values()
            ),
        }
