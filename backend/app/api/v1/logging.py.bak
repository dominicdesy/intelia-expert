"""
Module de logging pour Intelia Expert
Gestion des conversations et feedback utilisateurs
Version complète avec analytics, administration et suppression
CORRECTION: Validation assouplie pour résoudre les erreurs 400
"""
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
import json
import os

# Configuration
DB_PATH = "conversations.db"

# =============================================================================
# MODÈLES PYDANTIC AVEC VALIDATION ASSOUPLIE (CORRECTION)
# =============================================================================

class ConversationCreate(BaseModel):
    """Request model avec validation assouplie - CORRIGÉ pour erreur 400"""
    user_id: str
    question: str
    response: str
    conversation_id: str
    confidence_score: Optional[float] = None
    response_time_ms: Optional[int] = None
    language: str = "fr"
    rag_used: Optional[bool] = True

    # =========================================================================
    # CORRECTION: VALIDATION ASSOUPLIE POUR RÉSOUDRE LES ERREURS 400
    # =========================================================================

    @validator('user_id', pre=True)
    def validate_user_id(cls, v):
        """Validation user_id assouplie"""
        if not v:
            return f"anonymous_{uuid.uuid4().hex[:8]}"
        return str(v).strip()

    @validator('question', 'response', pre=True)
    def validate_text_fields(cls, v):
        """Validation texte assouplie"""
        if not v:
            return ""
        try:
            return str(v).strip()
        except:
            return ""

    @validator('conversation_id', pre=True)
    def validate_conversation_id(cls, v):
        """Validation conversation_id avec fallback"""
        if not v:
            return str(uuid.uuid4())
        return str(v).strip()

    @validator('language', pre=True)
    def validate_language(cls, v):
        """Validation langue avec fallback"""
        if not v:
            return "fr"
        lang = str(v).lower().strip()[:2]
        return lang if lang in ["fr", "en", "es"] else "fr"

    @validator('confidence_score', pre=True)
    def validate_confidence_score(cls, v):
        """Validation score avec gestion des erreurs"""
        if v is None or v == "":
            return None
        try:
            score = float(v)
            return max(0.0, min(1.0, score))  # Clamp entre 0 et 1
        except (ValueError, TypeError):
            return None

    @validator('response_time_ms', pre=True)
    def validate_response_time(cls, v):
        """Validation temps de réponse avec gestion des erreurs"""
        if v is None or v == "":
            return None
        try:
            time_ms = int(float(v))
            return max(0, time_ms)  # Pas de temps négatif
        except (ValueError, TypeError):
            return None

    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        # CORRECTION: Permettre des champs supplémentaires au lieu de les rejeter
        extra = "ignore"  # Au lieu de "forbid"

class FeedbackUpdate(BaseModel):
    feedback: int  # 1 pour 👍, -1 pour 👎

class ConversationResponse(BaseModel):
    conversation_id: str
    timestamp: datetime
    message: str

class DeleteResponse(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    deleted_count: int
    timestamp: datetime

class AnalyticsResponse(BaseModel):
    total_conversations: int
    satisfaction_rate: Optional[float]
    avg_response_time: Optional[float]
    feedback_distribution: Dict[str, int]
    period_days: int

class DetailedStatsResponse(BaseModel):
    frequent_patterns: List[Dict[str, Any]]
    language_distribution: List[Dict[str, Any]]
    daily_evolution: List[Dict[str, Any]]

# ==================== CLASSE LOGGER PRINCIPAL ====================

class ConversationLogger:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données SQLite avec toutes les tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Table principale des conversations
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT UNIQUE NOT NULL,
                        user_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        response TEXT NOT NULL,
                        feedback INTEGER, -- NULL, 1 (👍), -1 (👎)
                        confidence_score REAL,
                        response_time_ms INTEGER,
                        language TEXT DEFAULT 'fr',
                        rag_used BOOLEAN DEFAULT TRUE,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Index pour les requêtes fréquentes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conversation_id ON conversations(conversation_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON conversations(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback ON conversations(feedback)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_language ON conversations(language)")
                
                # Table pour les analytics pré-calculées (optionnel)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS analytics_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        metric_value TEXT NOT NULL,
                        period_days INTEGER,
                        calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                print("✅ Base de données conversations initialisée avec succès")
                
        except Exception as e:
            print(f"❌ Erreur initialisation base de données: {e}")
            raise e
    
    def save_conversation(self, conversation: ConversationCreate) -> str:
        """Sauvegarde une nouvelle conversation"""
        try:
            record_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO conversations (
                        id, conversation_id, user_id, question, response, 
                        confidence_score, response_time_ms, language, rag_used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_id,
                    conversation.conversation_id,
                    conversation.user_id,
                    conversation.question,
                    conversation.response,
                    conversation.confidence_score,
                    conversation.response_time_ms,
                    conversation.language,
                    conversation.rag_used
                ))
            
            print(f"✅ Conversation sauvegardée: {conversation.conversation_id}")
            return record_id
            
        except sqlite3.IntegrityError as e:
            print(f"❌ Conversation ID déjà existant: {conversation.conversation_id}")
            # CORRECTION: Ne pas lever d'exception pour l'ID dupliqué, juste retourner l'ID existant
            try:
                with sqlite3.connect(self.db_path) as conn:
                    existing_id = conn.execute("""
                        SELECT id FROM conversations WHERE conversation_id = ?
                    """, (conversation.conversation_id,)).fetchone()
                    if existing_id:
                        return existing_id[0]
                    else:
                        # Si pas trouvé, générer un nouvel ID unique
                        new_conversation_id = f"{conversation.conversation_id}_{uuid.uuid4().hex[:8]}"
                        new_record_id = str(uuid.uuid4())
                        conn.execute("""
                            INSERT INTO conversations (
                                id, conversation_id, user_id, question, response, 
                                confidence_score, response_time_ms, language, rag_used
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            new_record_id,
                            new_conversation_id,
                            conversation.user_id,
                            conversation.question,
                            conversation.response,
                            conversation.confidence_score,
                            conversation.response_time_ms,
                            conversation.language,
                            conversation.rag_used
                        ))
                        return new_record_id
            except Exception as fallback_error:
                print(f"❌ Erreur fallback sauvegarde: {fallback_error}")
                return str(uuid.uuid4())  # Retourner au moins un ID