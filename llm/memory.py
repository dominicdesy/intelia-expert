# -*- coding: utf-8 -*-
"""
memory.py - Mémoire conversationnelle avec plus de contexte
"""

import logging
import time
from config import MAX_CONVERSATION_CONTEXT

logger = logging.getLogger(__name__)

class ConversationMemory:
    """MODIFICATION: Mémoire conversationnelle avec plus de contexte"""
    
    def __init__(self, client):
        self.client = client
        self.memory_store = {}
        self.max_exchanges = 8  # MODIFICATION: 3 → 8 tours
    
    async def get_contextual_memory(self, tenant_id: str, current_query: str) -> str:
        """Récupère le contexte conversationnel enrichi"""
        if tenant_id not in self.memory_store:
            return ""
        
        history = self.memory_store[tenant_id]
        if not history:
            return ""
        
        try:
            # MODIFICATION: Retourner les 2-3 derniers échanges selon la longueur
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
        
        self.memory_store[tenant_id].append({
            "question": question,
            "answer": answer,
            "timestamp": time.time()
        })
        
        if len(self.memory_store[tenant_id]) > self.max_exchanges:
            self.memory_store[tenant_id] = self.memory_store[tenant_id][-self.max_exchanges:]