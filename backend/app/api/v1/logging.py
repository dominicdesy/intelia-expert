"""
app/api/v1/logging.py - VERSION COMPLÈTE RÉÉCRITE AVEC CORRECTIONS
CORRECTIONS: Méthodes save_conversation, log_conversation, update_feedback
CONSERVATION: Toutes les extensions de commentaires feedback existantes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import sqlite3
import uuid
import json

router = APIRouter()

# ============================================================================
# MODÈLES PYDANTIC EXISTANTS - CONSERVÉS
# ============================================================================

class ConversationCreate(BaseModel):
    conversation_id: str
    user_id: str
    question: str
    response: str
    feedback: Optional[int] = None
    confidence_score: Optional[float] = None
    response_time_ms: Optional[int] = None
    language: Optional[str] = "fr"
    rag_used: Optional[bool] = False
    timestamp: Optional[str] = None

class FeedbackUpdate(BaseModel):
    feedback: int = Field(..., description="Feedback: 1 (positive), -1 (negative), 0 (neutral)")

class FeedbackCommentUpdate(BaseModel):
    comment: str
    timestamp: Optional[str] = None

class FeedbackWithCommentUpdate(BaseModel):
    feedback: int
    comment: Optional[str] = None
    timestamp: Optional[str] = None

# ============================================================================
# CLASSE ConversationLogger - RÉÉCRITE AVEC CORRECTIONS
# ============================================================================

class ConversationLogger:
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données avec toutes les colonnes nécessaires"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        response TEXT NOT NULL,
                        feedback INTEGER,
                        feedback_comment TEXT,
                        confidence_score REAL,
                        response_time_ms INTEGER,
                        language TEXT DEFAULT 'fr',
                        rag_used BOOLEAN DEFAULT 0,
                        timestamp TEXT NOT NULL,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Créer les index pour performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conversation_id ON conversations(conversation_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON conversations(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback ON conversations(feedback)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_comment ON conversations(feedback_comment)")
                
                print("✅ [logging] Base de données conversations initialisée avec succès")
                
        except Exception as e:
            print(f"❌ [logging] Erreur initialisation base: {e}")

    # ✅ MÉTHODE CORRIGÉE: save_conversation
    def save_conversation(self, conversation: ConversationCreate) -> str:
        """
        Sauvegarde une conversation - MÉTHODE PRINCIPALE CORRIGÉE
        Compatible avec l'interface attendue par expert.py
        
        Returns:
            str: L'ID de l'enregistrement créé
        """
        try:
            record_id = str(uuid.uuid4())
            timestamp = conversation.timestamp or datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO conversations (
                        id, conversation_id, user_id, question, response, 
                        feedback, confidence_score, response_time_ms, 
                        language, rag_used, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_id,
                    conversation.conversation_id,
                    conversation.user_id,
                    conversation.question,
                    conversation.response,
                    conversation.feedback,
                    conversation.confidence_score,
                    conversation.response_time_ms,
                    conversation.language or "fr",
                    conversation.rag_used or False,
                    timestamp
                ))
                
                print(f"✅ [logging] Conversation sauvegardée: {conversation.conversation_id}")
                return record_id
                
        except Exception as e:
            print(f"❌ [logging] Erreur sauvegarde conversation: {e}")
            raise

    # ✅ MÉTHODE AJOUTÉE: log_conversation (alias)
    def log_conversation(self, conversation: ConversationCreate) -> str:
        """
        Alias pour save_conversation pour compatibilité
        
        Returns:
            str: L'ID de l'enregistrement créé
        """
        return self.save_conversation(conversation)

    # ✅ MÉTHODE CORRIGÉE: update_feedback
    def update_feedback(self, conversation_id: str, feedback: int) -> bool:
        """
        Met à jour le feedback d'une conversation
        
        Args:
            conversation_id: ID de la conversation
            feedback: Feedback numérique (1=positive, -1=negative, 0=neutral)
            
        Returns:
            bool: True si la mise à jour a réussi
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE conversations 
                    SET feedback = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE conversation_id = ?
                """, (feedback, conversation_id))
                
                success = cursor.rowcount > 0
                if success:
                    print(f"✅ [logging] Feedback mis à jour: {conversation_id} -> {feedback}")
                else:
                    print(f"⚠️ [logging] Conversation non trouvée pour feedback: {conversation_id}")
                    
                return success
                
        except Exception as e:
            print(f"❌ [logging] Erreur mise à jour feedback: {e}")
            return False

    # ✅ MÉTHODE AJOUTÉE: update_feedback_comment
    def update_feedback_comment(self, conversation_id: str, comment: str) -> bool:
        """Met à jour le commentaire feedback d'une conversation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE conversations 
                    SET feedback_comment = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE conversation_id = ?
                """, (comment, conversation_id))
                
                success = cursor.rowcount > 0
                if success:
                    print(f"✅ [logging] Commentaire feedback mis à jour: {conversation_id}")
                else:
                    print(f"⚠️ [logging] Conversation non trouvée pour commentaire: {conversation_id}")
                
                return success
                
        except Exception as e:
            print(f"❌ [logging] Erreur mise à jour commentaire feedback: {e}")
            return False
    
    # ✅ MÉTHODE AJOUTÉE: update_feedback_with_comment
    def update_feedback_with_comment(self, conversation_id: str, feedback: int, comment: str = None) -> bool:
        """Met à jour le feedback ET le commentaire d'une conversation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE conversations 
                    SET feedback = ?, feedback_comment = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE conversation_id = ?
                """, (feedback, comment, conversation_id))
                
                success = cursor.rowcount > 0
                if success:
                    print(f"✅ [logging] Feedback avec commentaire mis à jour: {conversation_id}")
                else:
                    print(f"⚠️ [logging] Conversation non trouvée: {conversation_id}")
                
                return success
                
        except Exception as e:
            print(f"❌ [logging] Erreur mise à jour feedback avec commentaire: {e}")
            return False

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Récupère une conversation par son ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM conversations WHERE conversation_id = ?
                """, (conversation_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            print(f"❌ [logging] Erreur récupération conversation: {e}")
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
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"❌ [logging] Erreur récupération conversations utilisateur: {e}")
            return []

    def get_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Génère des analytics des conversations"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Statistiques générales
                general_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive,
                        COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative,
                        COUNT(CASE WHEN feedback IS NOT NULL THEN 1 END) as total_feedback,
                        COUNT(CASE WHEN feedback_comment IS NOT NULL AND feedback_comment != '' THEN 1 END) as with_comment,
                        AVG(CASE WHEN response_time_ms IS NOT NULL THEN response_time_ms END) as avg_response_time
                    FROM conversations 
                    WHERE datetime(timestamp) >= datetime('now', '-{} days')
                """.format(days)).fetchone()
                
                # Statistiques par langue
                language_stats = conn.execute("""
                    SELECT 
                        language,
                        COUNT(*) as total,
                        COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive,
                        COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative
                    FROM conversations 
                    WHERE datetime(timestamp) >= datetime('now', '-{} days')
                    GROUP BY language
                    ORDER BY total DESC
                """.format(days)).fetchall()
                
                # Calculer les taux
                total_conversations = general_stats[0]
                positive_feedback = general_stats[1]
                negative_feedback = general_stats[2]
                total_feedback = general_stats[3]
                
                satisfaction_rate = round(positive_feedback / total_feedback, 3) if total_feedback > 0 else 0
                feedback_rate = round(total_feedback / total_conversations, 3) if total_conversations > 0 else 0
                
                return {
                    "period_days": days,
                    "total_conversations": total_conversations,
                    "total_feedback": total_feedback,
                    "satisfaction_rate": satisfaction_rate,
                    "feedback_rate": feedback_rate,
                    "avg_response_time_ms": round(general_stats[5], 2) if general_stats[5] else None,
                    "feedback_breakdown": {
                        "positive": positive_feedback,
                        "negative": negative_feedback,
                        "with_comment": general_stats[4]
                    },
                    "language_stats": [
                        {
                            "language": lang[0],
                            "total": lang[1],
                            "positive": lang[2],
                            "negative": lang[3]
                        } for lang in language_stats
                    ],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"❌ [logging] Erreur génération analytics: {e}")
            return {}

    def get_feedback_analytics(self, user_id: str = None, days: int = 7) -> Dict[str, Any]:
        """Génère des analytics détaillées des feedbacks avec commentaires"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Construire la clause WHERE
                where_clause = "WHERE datetime(timestamp) >= datetime('now', '-{} days')".format(days)
                params = []
                
                if user_id:
                    where_clause += " AND user_id = ?"
                    params.append(user_id)
                
                # Statistiques générales
                general_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive,
                        COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative,
                        COUNT(CASE WHEN feedback IS NOT NULL THEN 1 END) as total_feedback,
                        COUNT(CASE WHEN feedback_comment IS NOT NULL AND feedback_comment != '' THEN 1 END) as with_comment,
                        AVG(CASE WHEN response_time_ms IS NOT NULL THEN response_time_ms END) as avg_response_time
                    FROM conversations 
                    {}
                """.format(where_clause), params).fetchone()
                
                # Top commentaires négatifs
                negative_comments = conn.execute("""
                    SELECT question, feedback_comment, timestamp, language
                    FROM conversations 
                    {}
                    AND feedback = -1 
                    AND feedback_comment IS NOT NULL 
                    AND feedback_comment != ''
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """.format(where_clause), params).fetchall()
                
                # Top commentaires positifs
                positive_comments = conn.execute("""
                    SELECT question, feedback_comment, timestamp, language
                    FROM conversations 
                    {}
                    AND feedback = 1 
                    AND feedback_comment IS NOT NULL 
                    AND feedback_comment != ''
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """.format(where_clause), params).fetchall()
                
                # Calculer les taux
                total_conversations = general_stats[0]
                positive_feedback = general_stats[1]
                negative_feedback = general_stats[2]
                total_feedback = general_stats[3]
                with_comment = general_stats[4]
                
                satisfaction_rate = round(positive_feedback / total_feedback, 3) if total_feedback > 0 else 0
                feedback_rate = round(total_feedback / total_conversations, 3) if total_conversations > 0 else 0
                comment_rate = round(with_comment / total_feedback, 3) if total_feedback > 0 else 0
                
                return {
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                    "report": {
                        "period_days": days,
                        "summary": {
                            "total_conversations": total_conversations,
                            "total_feedback": total_feedback,
                            "satisfaction_rate": satisfaction_rate,
                            "feedback_rate": feedback_rate,
                            "comment_rate": comment_rate,
                            "avg_response_time_ms": round(general_stats[5], 2) if general_stats[5] else None
                        },
                        "feedback_breakdown": {
                            "positive": positive_feedback,
                            "negative": negative_feedback,
                            "with_comment": with_comment
                        },
                        "top_negative_feedback": [
                            {
                                "question": comment[0][:100] + "..." if len(comment[0]) > 100 else comment[0],
                                "comment": comment[1],
                                "timestamp": comment[2],
                                "language": comment[3]
                            } for comment in negative_comments
                        ],
                        "top_positive_feedback": [
                            {
                                "question": comment[0][:100] + "..." if len(comment[0]) > 100 else comment[0],
                                "comment": comment[1],
                                "timestamp": comment[2],
                                "language": comment[3]
                            } for comment in positive_comments
                        ]
                    }
                }
                
        except Exception as e:
            print(f"❌ [logging] Erreur génération rapport feedback: {e}")
            return {"status": "error", "error": str(e)}

# ============================================================================
# INSTANCE GLOBALE - CONSERVÉE
# ============================================================================

logger_instance = ConversationLogger()

# ============================================================================
# ENDPOINTS API - EXISTANTS CONSERVÉS + CORRECTIONS
# ============================================================================

@router.post("/conversation")
async def log_conversation_endpoint(conversation: ConversationCreate):
    """Endpoint pour logger une conversation - CORRIGÉ"""
    try:
        print(f"📝 [logging] Réception conversation: {conversation.conversation_id}")
        print(f"📝 [logging] Utilisateur: {conversation.user_id}")
        print(f"📝 [logging] Question: {conversation.question[:50]}...")
        
        record_id = logger_instance.save_conversation(conversation)
        
        print(f"✅ [logging] Conversation enregistrée avec ID: {record_id}")
        
        return {
            "status": "success",
            "message": "Conversation enregistrée avec succès",
            "record_id": record_id,
            "conversation_id": conversation.conversation_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"❌ [logging] Erreur enregistrement conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement: {str(e)}")

@router.patch("/conversation/{conversation_id}/feedback")
async def update_conversation_feedback(conversation_id: str, feedback_data: dict):
    """Endpoint pour mettre à jour le feedback - VERSION FLEXIBLE CORRIGÉE"""
    try:
        print(f"📊 [logging] Réception feedback pour: {conversation_id}")
        print(f"📊 [logging] Données reçues: {feedback_data}")
        print(f"📊 [logging] Type: {type(feedback_data)}")
        
        # Extraire le feedback - support multiple formats
        feedback_value = None
        
        if isinstance(feedback_data, dict):
            # Format 1: {"feedback": 1}
            if "feedback" in feedback_data:
                feedback_value = feedback_data["feedback"]
                print(f"📊 [logging] Format détecté: 'feedback' -> {feedback_value}")
            # Format 2: {"rating": "positive"}
            elif "rating" in feedback_data:
                rating_map = {"positive": 1, "negative": -1, "neutral": 0}
                feedback_value = rating_map.get(feedback_data["rating"], 0)
                print(f"📊 [logging] Format détecté: 'rating' -> {feedback_data['rating']} -> {feedback_value}")
            # Format 3: {"vote": "up"}
            elif "vote" in feedback_data:
                vote_map = {"up": 1, "down": -1, "neutral": 0}
                feedback_value = vote_map.get(feedback_data["vote"], 0

@router.get("/conversation/{conversation_id}")
async def get_conversation_endpoint(conversation_id: str):
    """Récupérer une conversation par ID"""
    try:
        print(f"🔍 [logging] Recherche conversation: {conversation_id}")
        
        conversation = logger_instance.get_conversation(conversation_id)
        
        if conversation:
            print(f"✅ [logging] Conversation trouvée: {conversation_id}")
            return {
                "status": "success",
                "conversation": conversation,
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"❌ [logging] Conversation non trouvée: {conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [logging] Erreur récupération conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur récupération: {str(e)}")

@router.get("/conversations/user/{user_id}")
async def get_user_conversations_endpoint(user_id: str, limit: int = 50):
    """Récupérer les conversations d'un utilisateur"""
    try:
        print(f"🔍 [logging] Récupération conversations pour: {user_id}")
        
        conversations = logger_instance.get_user_conversations(user_id, limit)
        
        print(f"✅ [logging] {len(conversations)} conversations trouvées")
        
        return {
            "status": "success",
            "user_id": user_id,
            "conversations": conversations,
            "count": len(conversations),
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ [logging] Erreur récupération conversations utilisateur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur récupération: {str(e)}")

@router.get("/analytics")
async def get_analytics_endpoint(days: int = 7):
    """Récupérer les analytics des conversations"""
    try:
        print(f"📊 [logging] Récupération analytics pour {days} jours")
        
        analytics = logger_instance.get_analytics(days)
        
        print(f"✅ [logging] Analytics générées")
        
        return {
            "status": "success",
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ [logging] Erreur génération analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur analytics: {str(e)}")

# ============================================================================
# ENDPOINTS COMMENTAIRES FEEDBACK - CONSERVÉS DE L'EXTENSION
# ============================================================================

@router.patch("/conversation/{conversation_id}/comment")
async def update_feedback_comment(conversation_id: str, comment_data: FeedbackCommentUpdate):
    """Mettre à jour le commentaire feedback d'une conversation"""
    try:
        print(f"💬 [logging] Réception commentaire pour: {conversation_id}")
        print(f"💬 [logging] Commentaire: {comment_data.comment[:50]}...")
        
        success = logger_instance.update_feedback_comment(conversation_id, comment_data.comment)
        
        if success:
            print(f"✅ [logging] Commentaire mis à jour: {conversation_id}")
            return {
                "status": "success",
                "message": "Commentaire feedback mis à jour avec succès", 
                "conversation_id": conversation_id,
                "comment": comment_data.comment[:100] + "..." if len(comment_data.comment) > 100 else comment_data.comment,
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"❌ [logging] Conversation non trouvée pour commentaire: {conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [logging] Erreur commentaire feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur commentaire: {str(e)}")

@router.patch("/conversation/{conversation_id}/feedback-with-comment")
async def update_feedback_with_comment(conversation_id: str, feedback_data: FeedbackWithCommentUpdate):
    """Mettre à jour le feedback ET le commentaire d'une conversation"""
    try:
        print(f"📊💬 [logging] Réception feedback avec commentaire pour: {conversation_id}")
        print(f"📊💬 [logging] Feedback: {feedback_data.feedback}")
        print(f"💬 [logging] Commentaire: {feedback_data.comment[:50] + '...' if feedback_data.comment else 'Aucun'}")
        
        success = logger_instance.update_feedback_with_comment(
            conversation_id, 
            feedback_data.feedback,
            feedback_data.comment
        )
        
        if success:
            print(f"✅ [logging] Feedback avec commentaire mis à jour: {conversation_id}")
            return {
                "status": "success",
                "message": "Feedback avec commentaire mis à jour avec succès", 
                "conversation_id": conversation_id,
                "feedback": feedback_data.feedback,
                "comment": feedback_data.comment[:100] + "..." if feedback_data.comment and len(feedback_data.comment) > 100 else feedback_data.comment,
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"❌ [logging] Conversation non trouvée pour feedback avec commentaire: {conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [logging] Erreur feedback avec commentaire: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur feedback avec commentaire: {str(e)}")

@router.get("/analytics/feedback")
async def get_feedback_analytics(user_id: str = None, days: int = 7):
    """Analytics détaillées des feedbacks avec commentaires"""
    try:
        print(f"📊 [logging] Récupération analytics feedback pour: {user_id or 'tous les utilisateurs'}")
        print(f"📊 [logging] Période: {days} jours")
        
        analytics = logger_instance.get_feedback_analytics(user_id, days)
        
        print(f"✅ [logging] Analytics feedback récupérées")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "analytics": analytics,
            "message": f"Analytics feedback pour les {days} derniers jours"
        }
        
    except Exception as e:
        print(f"❌ [logging] Erreur analytics feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur analytics: {str(e)}")

@router.get("/conversations/with-comments")
async def get_conversations_with_comments(limit: int = 20, user_id: str = None):
    """Récupérer les conversations avec commentaires feedback"""
    try:
        print(f"💬 [logging] Récupération conversations avec commentaires")
        print(f"💬 [logging] Limite: {limit}, User: {user_id or 'tous'}")
        
        with sqlite3.connect(logger_instance.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            where_clause = "WHERE feedback_comment IS NOT NULL AND feedback_comment != ''"
            params = []
            
            if user_id:
                where_clause += " AND user_id = ?"
                params.append(user_id)
            
            cursor = conn.execute("""
                SELECT conversation_id, user_id, question, feedback, feedback_comment, timestamp, language
                FROM conversations 
                {} 
                ORDER BY timestamp DESC 
                LIMIT ?
            """.format(where_clause), params + [limit])
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    "conversation_id": row["conversation_id"],
                    "user_id": row["user_id"],
                    "question": row["question"],
                    "feedback": "positive" if row["feedback"] == 1 else "negative",
                    "feedback_comment": row["feedback_comment"],
                    "timestamp": row["timestamp"],
                    "language": row["language"]
                })
        
        print(f"✅ [logging] {len(conversations)} conversations avec commentaires récupérées")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "conversations": conversations,
            "count": len(conversations),
            "message": f"{len(conversations)} conversations avec commentaires trouvées"
        }
        
    except Exception as e:
        print(f"❌ [logging] Erreur récupération conversations avec commentaires: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur récupération: {str(e)}")

@router.get("/admin/feedback-report")
async def get_admin_feedback_report(days: int = 30):
    """Rapport administrateur des feedbacks avec commentaires"""
    try:
        print(f"📋 [logging] Génération rapport admin feedback pour {days} jours")
        
        with sqlite3.connect(logger_instance.db_path) as conn:
            # Statistiques générales
            general_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_conversations,
                    COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive_feedback,
                    COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative_feedback,
                    COUNT(CASE WHEN feedback_comment IS NOT NULL AND feedback_comment != '' THEN 1 END) as with_comment
                FROM conversations 
                WHERE datetime(timestamp) >= datetime('now', '-{} days')
            """.format(days)).fetchone()
            
            # Commentaires récents
            recent_comments = conn.execute("""
                SELECT conversation_id, feedback, feedback_comment, timestamp, question
                FROM conversations 
                WHERE datetime(timestamp) >= datetime('now', '-{} days')
                AND feedback_comment IS NOT NULL 
                AND feedback_comment != ''
                ORDER BY timestamp DESC 
                LIMIT 10
            """.format(days)).fetchall()
            
            # Satisfaction rate
            total_feedback = general_stats[1] + general_stats[2]
            satisfaction_rate = None
            if total_feedback > 0:
                satisfaction_rate = round(general_stats[1] / total_feedback, 3)
            
            report = {
                "period_days": days,
                "general_stats": {
                    "total_conversations": general_stats[0],
                    "positive_feedback": general_stats[1],
                    "negative_feedback": general_stats[2],
                    "total_feedback": total_feedback,
                    "with_comment": general_stats[3]
                },
                "satisfaction_rate": satisfaction_rate,
                "comment_rate": round(general_stats[3] / total_feedback, 3) if total_feedback > 0 else 0,
                "recent_comments": [
                    {
                        "conversation_id": comment[0],
                        "feedback": "positive" if comment[1] == 1 else "negative",
                        "comment": comment[2],
                        "timestamp": comment[3],
                        "question_preview": comment[4][:100] + "..." if len(comment[4]) > 100 else comment[4]
                    } for comment in recent_comments
                ]
            }
        
        print(f"✅ [logging] Rapport admin feedback généré")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "report": report,
            "message": f"Rapport feedback pour les {days} derniers jours généré"
        }
        
    except Exception as e:
        print(f"❌ [logging] Erreur génération rapport admin: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur rapport: {str(e)}")

@router.post("/admin/export-feedback")
async def export_feedback_data(days: int = 30, format: str = "json"):
    """Export des données de feedback pour analyse externe"""
    try:
        print(f"📤 [logging] Export données feedback format {format} pour {days} jours")
        
        with sqlite3.connect(logger_instance.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT 
                    conversation_id,
                    user_id,
                    question,
                    feedback,
                    feedback_comment,
                    confidence_score,
                    response_time_ms,
                    language,
                    rag_used,
                    timestamp,
                    updated_at
                FROM conversations 
                WHERE datetime(timestamp) >= datetime('now', '-{} days')
                AND feedback IS NOT NULL
                ORDER BY timestamp DESC
            """.format(days))
            
            data = []
            for row in cursor.fetchall():
                data.append({
                    "conversation_id": row["conversation_id"],
                    "user_id": row["user_id"][:8] + "..." if len(row["user_id"]) > 12 else row["user_id"],  # Anonymisation
                    "question_length": len(row["question"]),
                    "question_preview": row["question"][:50] + "..." if len(row["question"]) > 50 else row["question"],
                    "feedback": "positive" if row["feedback"] == 1 else "negative",
                    "has_comment": bool(row["feedback_comment"]),
                    "comment_length": len(row["feedback_comment"]) if row["feedback_comment"] else 0,
                    "comment_preview": row["feedback_comment"][:100] + "..." if row["feedback_comment"] and len(row["feedback_comment"]) > 100 else row["feedback_comment"],
                    "confidence_score": row["confidence_score"],
                    "response_time_ms": row["response_time_ms"],
                    "language": row["language"],
                    "rag_used": row["rag_used"],
                    "timestamp": row["timestamp"]
                })
        
        print(f"✅ [logging] {len(data)} enregistrements exportés")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "export_format": format,
            "period_days": days,
            "total_records": len(data),
            "data": data,
            "message": f"{len(data)} enregistrements feedback exportés"
        }
        
    except Exception as e:
        print(f"❌ [logging] Erreur export feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur export: {str(e)}")

# ============================================================================
# ENDPOINT DE TEST
# ============================================================================

@router.get("/test-comments")
async def test_comment_support():
    """Test du support des commentaires feedback"""
    try:
        with sqlite3.connect(logger_instance.db_path) as conn:
            # Vérifier le schéma
            schema_info = conn.execute("PRAGMA table_info(conversations)").fetchall()
            columns = [col[1] for col in schema_info]
            
            # Compter les commentaires existants
            comment_count = conn.execute("""
                SELECT COUNT(*) FROM conversations 
                WHERE feedback_comment IS NOT NULL AND feedback_comment != ''
            """).fetchone()[0]
            
            # Test d'insertion (rollback)
            conn.execute("BEGIN")
            try:
                test_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO conversations (id, conversation_id, user_id, question, response, feedback, feedback_comment, timestamp)
                    VALUES (?, ?, 'test_user', 'Test question', 'Test response', 1, 'Test comment', ?)
                """, (str(uuid.uuid4()), test_id, datetime.now().isoformat()))
                
                # Vérifier l'insertion
                result = conn.execute("SELECT feedback_comment FROM conversations WHERE conversation_id = ?", (test_id,)).fetchone()
                test_success = result and result[0] == 'Test comment'
                
                conn.execute("ROLLBACK")  # Annuler le test
                
            except Exception as e:
                conn.execute("ROLLBACK")
                test_success = False
                print(f"❌ Test insertion échoué: {e}")
        
        return {
            "status": "success" if test_success else "error",
            "timestamp": datetime.now().isoformat(),
            "schema_info": {
                "has_feedback_comment_column": "feedback_comment" in columns,
                "total_columns": len(columns),
                "columns": columns
            },
            "comment_stats": {
                "existing_comments": comment_count,
                "insertion_test": "passed" if test_success else "failed"
            },
            "endpoints_available": [
                "/logging/conversation/{id}/comment [PATCH]",
                "/logging/conversation/{id}/feedback-with-comment [PATCH]",
                "/logging/analytics/feedback [GET]",
                "/logging/conversations/with-comments [GET]",
                "/logging/admin/feedback-report [GET]",
                "/logging/admin/export-feedback [POST]"
            ],
            "methods_available": {
                "save_conversation": hasattr(logger_instance, 'save_conversation'),
                "log_conversation": hasattr(logger_instance, 'log_conversation'),
                "update_feedback": hasattr(logger_instance, 'update_feedback'),
                "update_feedback_comment": hasattr(logger_instance, 'update_feedback_comment'),
                "update_feedback_with_comment": hasattr(logger_instance, 'update_feedback_with_comment')
            },
            "message": "Support commentaires feedback " + ("opérationnel" if test_success else "non fonctionnel")
        }
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "message": "Erreur test support commentaires"
        }

print("✅ LOGGING.PY RÉÉCRIT AVEC CORRECTIONS COMPLÈTES")
print("🔧 MÉTHODES CORRIGÉES:")
print("   - save_conversation() : ✅ Implémentée")
print("   - log_conversation() : ✅ Alias ajouté")
print("   - update_feedback() : ✅ Corrigée")
print("   - update_feedback_comment() : ✅ Conservée")
print("   - update_feedback_with_comment() : ✅ Conservée")
print("🆕 ENDPOINTS CONSERVÉS:")
print("   - POST /logging/conversation")
print("   - PATCH /logging/conversation/{id}/feedback")
print("   - PATCH /logging/conversation/{id}/comment")
print("   - PATCH /logging/conversation/{id}/feedback-with-comment")
print("   - GET /logging/analytics/feedback")
print("   - GET /logging/conversations/with-comments")
print("   - GET /logging/admin/feedback-report")
print("   - POST /logging/admin/export-feedback")
print("   - GET /logging/test-comments")