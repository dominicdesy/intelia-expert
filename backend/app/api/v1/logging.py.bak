"""
Module de logging pour Intelia Expert
Gestion des conversations et feedback utilisateurs
Version complète avec analytics et administration
"""
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os

# Configuration
DB_PATH = "conversations.db"

# ==================== MODÈLES PYDANTIC ====================

class ConversationCreate(BaseModel):
    user_id: str
    question: str
    response: str
    conversation_id: str
    confidence_score: Optional[float] = None
    response_time_ms: Optional[int] = None
    language: str = "fr"
    rag_used: Optional[bool] = True

class FeedbackUpdate(BaseModel):
    feedback: int  # 1 pour 👍, -1 pour 👎

class ConversationResponse(BaseModel):
    conversation_id: str
    timestamp: datetime
    message: str

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
            raise HTTPException(status_code=409, detail="Conversation ID already exists")
        except Exception as e:
            print(f"❌ Erreur sauvegarde conversation: {e}")
            raise e
    
    def update_feedback(self, conversation_id: str, feedback: int) -> bool:
        """Met à jour le feedback d'une conversation"""
        try:
            if feedback not in [-1, 1]:
                raise ValueError("Feedback doit être 1 (👍) ou -1 (👎)")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE conversations 
                    SET feedback = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE conversation_id = ?
                """, (feedback, conversation_id))
                
                if cursor.rowcount > 0:
                    print(f"✅ Feedback mis à jour: {conversation_id} = {feedback}")
                    return True
                else:
                    print(f"⚠️ Conversation non trouvée: {conversation_id}")
                    return False
                    
        except Exception as e:
            print(f"❌ Erreur mise à jour feedback: {e}")
            raise e
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Récupère une conversation par ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM conversations WHERE conversation_id = ?
                """, (conversation_id,))
                
                row = cursor.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            print(f"❌ Erreur récupération conversation: {e}")
            return None
    
    def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Récupère les conversations d'un utilisateur"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM conversations 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, limit))
                
                conversations = [dict(row) for row in cursor.fetchall()]
                print(f"✅ {len(conversations)} conversations récupérées pour {user_id}")
                return conversations
                
        except Exception as e:
            print(f"❌ Erreur récupération conversations utilisateur: {e}")
            return []
    
    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Récupère les analytics des conversations"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total conversations
                total = conn.execute("""
                    SELECT COUNT(*) FROM conversations
                    WHERE timestamp >= datetime('now', '-{} days')
                """.format(days)).fetchone()[0]
                
                # Taux de satisfaction
                satisfaction_data = conn.execute("""
                    SELECT 
                        COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive,
                        COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative,
                        COUNT(CASE WHEN feedback IS NOT NULL THEN 1 END) as total_feedback
                    FROM conversations
                    WHERE timestamp >= datetime('now', '-{} days')
                """.format(days)).fetchone()
                
                satisfaction_rate = None
                if satisfaction_data[2] > 0:  # total_feedback > 0
                    satisfaction_rate = round((satisfaction_data[0] / satisfaction_data[2]) * 100, 2)
                
                # Temps de réponse moyen
                avg_response_time = conn.execute("""
                    SELECT AVG(response_time_ms) FROM conversations
                    WHERE response_time_ms IS NOT NULL
                    AND timestamp >= datetime('now', '-{} days')
                """.format(days)).fetchone()[0]
                
                if avg_response_time:
                    avg_response_time = round(avg_response_time, 2)
                
                # Distribution feedback
                feedback_dist = {
                    'positive': satisfaction_data[0],
                    'negative': satisfaction_data[1],
                    'no_feedback': total - satisfaction_data[2]
                }
                
                analytics = {
                    'total_conversations': total,
                    'satisfaction_rate': satisfaction_rate,
                    'avg_response_time': avg_response_time,
                    'feedback_distribution': feedback_dist,
                    'period_days': days
                }
                
                print(f"✅ Analytics calculées pour {days} jours: {total} conversations")
                return analytics
                
        except Exception as e:
            print(f"❌ Erreur analytics: {e}")
            return {
                'total_conversations': 0,
                'satisfaction_rate': None,
                'avg_response_time': None,
                'feedback_distribution': {'positive': 0, 'negative': 0, 'no_feedback': 0},
                'period_days': days
            }
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Récupère des statistiques détaillées pour l'administration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Questions les plus fréquentes (patterns)
                frequent_patterns = conn.execute("""
                    SELECT 
                        substr(question, 1, 50) as question_preview,
                        COUNT(*) as frequency,
                        AVG(CASE WHEN feedback = 1 THEN 1.0 WHEN feedback = -1 THEN 0.0 END) as avg_satisfaction,
                        AVG(response_time_ms) as avg_response_time
                    FROM conversations
                    GROUP BY substr(question, 1, 50)
                    HAVING COUNT(*) > 1
                    ORDER BY frequency DESC
                    LIMIT 10
                """).fetchall()
                
                # Distribution par langue
                language_dist = conn.execute("""
                    SELECT 
                        language, 
                        COUNT(*) as count,
                        AVG(CASE WHEN feedback = 1 THEN 1.0 WHEN feedback = -1 THEN 0.0 END) as satisfaction
                    FROM conversations
                    GROUP BY language
                    ORDER BY count DESC
                """).fetchall()
                
                # Évolution quotidienne (7 derniers jours)
                daily_evolution = conn.execute("""
                    SELECT 
                        date(timestamp) as day,
                        COUNT(*) as conversations,
                        AVG(CASE WHEN feedback = 1 THEN 1.0 WHEN feedback = -1 THEN 0.0 END) as satisfaction,
                        AVG(response_time_ms) as avg_response_time
                    FROM conversations
                    WHERE timestamp >= datetime('now', '-7 days')
                    GROUP BY date(timestamp)
                    ORDER BY day DESC
                """).fetchall()
                
                # Utilisateurs les plus actifs
                top_users = conn.execute("""
                    SELECT 
                        user_id,
                        COUNT(*) as question_count,
                        AVG(CASE WHEN feedback = 1 THEN 1.0 WHEN feedback = -1 THEN 0.0 END) as satisfaction,
                        MAX(timestamp) as last_activity
                    FROM conversations
                    GROUP BY user_id
                    ORDER BY question_count DESC
                    LIMIT 10
                """).fetchall()
                
                return {
                    'frequent_patterns': [
                        {
                            'question_preview': row[0], 
                            'frequency': row[1], 
                            'avg_satisfaction': round(row[2], 3) if row[2] else None,
                            'avg_response_time': round(row[3], 2) if row[3] else None
                        } for row in frequent_patterns
                    ],
                    'language_distribution': [
                        {
                            'language': row[0], 
                            'count': row[1],
                            'satisfaction': round(row[2], 3) if row[2] else None
                        } for row in language_dist
                    ],
                    'daily_evolution': [
                        {
                            'day': row[0], 
                            'conversations': row[1], 
                            'satisfaction': round(row[2], 3) if row[2] else None,
                            'avg_response_time': round(row[3], 2) if row[3] else None
                        } for row in daily_evolution
                    ],
                    'top_users': [
                        {
                            'user_id': row[0][:8] + '...',  # Anonymiser partiellement
                            'question_count': row[1],
                            'satisfaction': round(row[2], 3) if row[2] else None,
                            'last_activity': row[3]
                        } for row in top_users
                    ]
                }
                
        except Exception as e:
            print(f"❌ Erreur stats détaillées: {e}")
            return {
                'frequent_patterns': [],
                'language_distribution': [],
                'daily_evolution': [],
                'top_users': []
            }
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Supprime les données anciennes selon la politique de rétention"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM conversations 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days_to_keep))
                
                deleted_count = cursor.rowcount
                print(f"🧹 {deleted_count} conversations supprimées (>{days_to_keep} jours)")
                return deleted_count
                
        except Exception as e:
            print(f"❌ Erreur nettoyage données: {e}")
            return 0
    
    def export_data_csv(self, output_file: str = None) -> str:
        """Exporte les conversations en CSV"""
        import csv
        
        if not output_file:
            output_file = f"conversations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT conversation_id, user_id, question, response, feedback,
                           confidence_score, response_time_ms, language, rag_used,
                           timestamp, updated_at
                    FROM conversations 
                    ORDER BY timestamp DESC
                """)
                
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    if cursor.description:
                        fieldnames = [col[0] for col in cursor.description]
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        for row in cursor:
                            writer.writerow(dict(row))
            
            print(f"✅ Export CSV créé: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Erreur export CSV: {e}")
            raise e

# ==================== INSTANCE GLOBALE ====================
logger_instance = ConversationLogger()

# ==================== ROUTER FASTAPI ====================
router = APIRouter(prefix="/logging", tags=["logging"])

# ==================== ENDPOINTS PRINCIPAUX ====================

@router.post("/conversation", response_model=ConversationResponse)
async def save_conversation(conversation: ConversationCreate):
    """Sauvegarde une nouvelle conversation"""
    try:
        record_id = logger_instance.save_conversation(conversation)
        return ConversationResponse(
            conversation_id=conversation.conversation_id,
            timestamp=datetime.now(),
            message="Conversation sauvegardée avec succès"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la sauvegarde: {str(e)}")

@router.patch("/conversation/{conversation_id}/feedback")
async def update_feedback(conversation_id: str, feedback: FeedbackUpdate):
    """Met à jour le feedback d'une conversation"""
    try:
        success = logger_instance.update_feedback(conversation_id, feedback.feedback)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
        return {
            "message": "Feedback mis à jour avec succès",
            "conversation_id": conversation_id,
            "feedback": feedback.feedback,
            "timestamp": datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour: {str(e)}")

@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Récupère une conversation par ID"""
    conversation = logger_instance.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    return conversation

@router.get("/user/{user_id}/conversations")
async def get_user_conversations(user_id: str, limit: int = 50):
    """Récupère les conversations d'un utilisateur"""
    try:
        conversations = logger_instance.get_user_conversations(user_id, limit)
        return {
            "conversations": conversations, 
            "count": len(conversations),
            "user_id": user_id,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(days: int = 30):
    """Récupère les analytics des conversations"""
    try:
        analytics = logger_instance.get_analytics(days)
        return AnalyticsResponse(**analytics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")

# ==================== ENDPOINTS ADMIN ====================

@router.get("/admin/stats", response_model=DetailedStatsResponse)
async def get_detailed_stats():
    """Stats détaillées pour l'administration"""
    try:
        stats = logger_instance.get_detailed_stats()
        return DetailedStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")

@router.get("/admin/database-info")
async def get_database_info():
    """Informations sur la base de données"""
    try:
        with sqlite3.connect(logger_instance.db_path) as conn:
            # Taille de la base
            file_size = os.path.getsize(logger_instance.db_path) if os.path.exists(logger_instance.db_path) else 0
            
            # Nombre total d'enregistrements
            total_records = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            
            # Date de la première et dernière conversation
            date_range = conn.execute("""
                SELECT MIN(timestamp) as first_conversation, MAX(timestamp) as last_conversation
                FROM conversations
            """).fetchone()
            
            # Informations sur les index
            indexes = conn.execute("""
                SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'conversations'
            """).fetchall()
            
            return {
                "database_file": logger_instance.db_path,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "total_records": total_records,
                "first_conversation": date_range[0],
                "last_conversation": date_range[1],
                "indexes": [idx[0] for idx in indexes],
                "status": "healthy"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur base de données: {str(e)}")

@router.post("/admin/cleanup")
async def cleanup_old_data(days_to_keep: int = 30):
    """Supprime les conversations anciennes"""
    try:
        deleted_count = logger_instance.cleanup_old_data(days_to_keep)
        return {
            "message": f"Nettoyage effectué avec succès",
            "deleted_records": deleted_count,
            "days_kept": days_to_keep,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du nettoyage: {str(e)}")

@router.get("/admin/export-csv")
async def export_conversations_csv():
    """Exporte les conversations en CSV"""
    try:
        filename = logger_instance.export_data_csv()
        return {
            "message": "Export CSV créé avec succès",
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'export: {str(e)}")

# ==================== ENDPOINTS DE TEST ====================

@router.get("/health")
async def health_check():
    """Health check du système de logging"""
    try:
        # Test de connexion à la base
        with sqlite3.connect(logger_instance.db_path) as conn:
            test_query = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_conversations": test_query,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/test/create-sample")
async def create_sample_conversation():
    """Crée une conversation de test (dev seulement)"""
    try:
        sample_conversation = ConversationCreate(
            user_id="test-user-123",
            question="Question de test du système de logging",
            response="Réponse de test générée automatiquement",
            conversation_id=str(uuid.uuid4()),
            confidence_score=0.95,
            response_time_ms=1500,
            language="fr",
            rag_used=True
        )
        
        record_id = logger_instance.save_conversation(sample_conversation)
        
        return {
            "message": "Conversation de test créée",
            "conversation_id": sample_conversation.conversation_id,
            "record_id": record_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur création test: {str(e)}")
