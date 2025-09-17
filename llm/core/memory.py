# -*- coding: utf-8 -*-
"""
memory.py - Mémoire conversationnelle avec plus de contexte
Version corrigée pour architecture modulaire
"""

import logging
import time
import os

# CORRECTION: Import modulaire depuis config
from config.config import MAX_CONVERSATION_CONTEXT

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Mémoire conversationnelle avec plus de contexte"""

    def __init__(self, client):
        self.client = client
        self.memory_store = {}
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

    def get_memory_stats(self, tenant_id: str) -> dict:
        """Statistiques de la mémoire pour un tenant"""
        if tenant_id not in self.memory_store:
            return {"exchanges": 0, "total_characters": 0}

        history = self.memory_store[tenant_id]
        total_chars = sum(len(ex["question"]) + len(ex["answer"]) for ex in history)

        return {
            "exchanges": len(history),
            "total_characters": total_chars,
            "oldest_timestamp": history[0]["timestamp"] if history else None,
            "newest_timestamp": history[-1]["timestamp"] if history else None,
        }
