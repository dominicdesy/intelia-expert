import os
import threading
import time
import logging
from typing import Dict, Any
from app.api.v1.pipeline.context_extractor import ContextExtractor
from app.api.v1.pipeline.clarification_manager import ClarificationManager
from app.api.v1.pipeline.postgres_memory import PostgresMemory as ConversationMemory
from app.api.v1.pipeline.rag_engine import RAGEngine
from app.api.v1.utils.config import COMPLETENESS_THRESHOLD
from app.api.v1.utils.response_generator import format_response

class DialogueManager:
    """
    Simplified orchestration:
      1. Extract context
      2. Clarify missing info
      3. Retrieve & generate answer via RAG
    """
    def __init__(self):
        self.extractor = ContextExtractor()
        self.clarifier = ClarificationManager()
        # Use managed Postgres for session memory
        self.memory = ConversationMemory(dsn=os.getenv("DATABASE_URL"))
        self.rag = RAGEngine()
        
        # ✅ AJOUTÉ : Démarrage automatique nettoyage
        self._start_cleanup_task()

    def handle(self, session_id: str, question: str) -> Dict[str, Any]:
        # 1. Load and update context
        context = self.memory.get(session_id) or {}
        extracted, score, missing = self.extractor.extract(question)
        context.update(extracted)

        # 2. If incomplete, ask for clarification
        if score < COMPLETENESS_THRESHOLD:
            questions = self.clarifier.generate(missing)
            # ✅ AJOUTÉ : Timestamp pour persistance
            context['last_interaction'] = time.time()
            self.memory.update(session_id, context)
            return {"type": "clarification", "questions": questions}

        # 3. Otherwise, generate final answer
        answer_data = self.rag.generate_answer(question, context)  # ← MODIFIÉ : maintenant un dict
        
        # ✅ AJOUTÉ : Extraire la réponse du dict
        if isinstance(answer_data, dict):
            response = format_response(answer_data.get("response", ""))
            source_info = {
                "source": answer_data.get("source"),
                "documents_used": answer_data.get("documents_used", 0),
                "warning": answer_data.get("warning")
            }
        else:
            # Fallback si ancien format
            response = format_response(answer_data)
            source_info = {}
        
        # ✅ MODIFIÉ : NE PAS effacer, marquer comme complété
        context['completed_at'] = time.time()
        context['last_interaction'] = time.time()
        self.memory.update(session_id, context)
        
        # ✅ MODIFIÉ : Retourner info source
        result = {"type": "answer", "response": response}
        result.update(source_info)
        return result

    # ✅ AJOUTÉ : Méthodes de nettoyage
    def _start_cleanup_task(self):
        """Démarre le nettoyage en arrière-plan (POC)"""
        def cleanup_sessions():
            while True:
                try:
                    self._manual_cleanup()
                except Exception as e:
                    logging.error(f"Erreur nettoyage sessions: {e}")
                
                time.sleep(1800)  # 30 minutes
        
        cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
        cleanup_thread.start()
        logging.info("✅ Nettoyage sessions activé (POC)")

    def _manual_cleanup(self):
        """Nettoyage manuel pour POC"""
        try:
            import psycopg2
            with psycopg2.connect(self.memory.dsn) as conn:
                with conn.cursor() as cur:
                    # Supprimer sessions > 2 heures
                    cutoff_time = time.time() - 7200  # 2 heures
                    cur.execute("""
                        DELETE FROM conversation_memory 
                        WHERE context->>'last_interaction' < %s
                        OR (context->>'completed_at' IS NOT NULL 
                            AND context->>'completed_at' < %s)
                    """, (str(cutoff_time), str(cutoff_time)))
                    
                    deleted = cur.rowcount
                    if deleted > 0:
                        logging.info(f"🧹 {deleted} sessions nettoyées")
        except Exception as e:
            logging.warning(f"Nettoyage manuel échoué: {e}")