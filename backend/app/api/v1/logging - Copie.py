"""
app/api/v1/logging.py - EXTENDED METRICS + RAG ANALYTICS
- New columns (with live migrations): inferred_species, documents_used, tables_used,
  fallback_used, completeness_score, missing_fields (JSON), follow_ups_count
- New endpoint: GET /logging/analytics/rag
- Backward compatible with existing endpoints and data
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import sqlite3
import uuid
import json
import math

router = APIRouter()

# ============================================================================
# Pydantic models
# ============================================================================

class ConversationCreate(BaseModel):
    conversation_id: str
    user_id: str
    question: str
    response: str
    # existing
    feedback: Optional[int] = None
    confidence_score: Optional[float] = None
    response_time_ms: Optional[int] = None
    language: Optional[str] = "fr"
    rag_used: Optional[bool] = False
    timestamp: Optional[str] = None
    # NEW monitoring fields
    inferred_species: Optional[str] = None
    documents_used: Optional[int] = None
    tables_used: Optional[int] = None
    fallback_used: Optional[bool] = None
    completeness_score: Optional[float] = None
    missing_fields: Optional[List[str]] = None
    follow_ups_count: Optional[int] = None


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
# ConversationLogger
# ============================================================================

NEW_COLUMNS = {
    "inferred_species": "TEXT",
    "documents_used": "INTEGER",
    "tables_used": "INTEGER",
    "fallback_used": "BOOLEAN",
    "completeness_score": "REAL",
    "missing_fields": "TEXT",  # JSON array as TEXT
    "follow_ups_count": "INTEGER",
}

class ConversationLogger:
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = db_path
        self.init_database()

    def _column_exists(self, conn: sqlite3.Connection, col: str) -> bool:
        info = conn.execute("PRAGMA table_info(conversations)").fetchall()
        cols = {c[1] for c in info}
        return col in cols

    def init_database(self):
        """Create table if missing + add new columns via live migrations."""
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
                # add new columns if absent
                for col, sqltype in NEW_COLUMNS.items():
                    if not self._column_exists(conn, col):
                        conn.execute(f"ALTER TABLE conversations ADD COLUMN {col} {sqltype}")
                # helpful indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conversation_id ON conversations(conversation_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON conversations(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback ON conversations(feedback)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_species ON conversations(inferred_species)")
                print("✅ [logging] DB initialized / migrated")
        except Exception as e:
            print(f"❌ [logging] init_database error: {e}")

    def _merge_missing(self, prev_json: Optional[str], new_list: Optional[List[str]]) -> Optional[str]:
        if new_list is None:
            return prev_json
        prev = set()
        if prev_json:
            try:
                prev = set(json.loads(prev_json) or [])
            except Exception:
                prev = set()
        merged = sorted({*prev, *[x for x in new_list if x]})
        return json.dumps(merged, ensure_ascii=False)

    def save_conversation(self, conversation: ConversationCreate) -> str:
        """
        Save a conversation.
        If conversation_id exists, append Q/A and update monitoring stats.
        """
        try:
            timestamp = conversation.timestamp or datetime.now().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                existing = conn.execute("""
                    SELECT id, question, response,
                           inferred_species, documents_used, tables_used, fallback_used,
                           completeness_score, missing_fields, follow_ups_count,
                           rag_used, confidence_score, response_time_ms
                    FROM conversations
                    WHERE conversation_id = ?
                    ORDER BY datetime(timestamp) DESC
                    LIMIT 1
                """, (conversation.conversation_id,)).fetchone()

                if existing:
                    print(f"🔄 [logging] Update existing conversation: {conversation.conversation_id}")
                    combined_question = f"{existing['question']}\n--- Question suivante ---\n{conversation.question}"
                    combined_response = f"{existing['response']}\n--- Réponse suivante ---\n{conversation.response}"

                    # merge stats (simple strategy)
                    documents_used = (existing["documents_used"] or 0) + (conversation.documents_used or 0)
                    tables_used = (existing["tables_used"] or 0) + (conversation.tables_used or 0)
                    follow_ups_count = (existing["follow_ups_count"] or 0) + (conversation.follow_ups_count or 0)
                    fallback_used = bool(existing["fallback_used"]) or bool(conversation.fallback_used)
                    rag_used = bool(existing["rag_used"]) or bool(conversation.rag_used)
                    inferred_species = conversation.inferred_species or existing["inferred_species"]
                    # keep last completeness_score if provided, else previous
                    completeness_score = conversation.completeness_score if conversation.completeness_score is not None else existing["completeness_score"]
                    # merge missing_fields
                    missing_fields = self._merge_missing(existing["missing_fields"], conversation.missing_fields)

                    conn.execute("""
                        UPDATE conversations SET
                            question = ?,
                            response = ?,
                            inferred_species = ?,
                            documents_used = ?,
                            tables_used = ?,
                            fallback_used = ?,
                            completeness_score = ?,
                            missing_fields = ?,
                            follow_ups_count = ?,
                            rag_used = ?,
                            confidence_score = COALESCE(?, confidence_score),
                            response_time_ms = COALESCE(?, response_time_ms),
                            updated_at = CURRENT_TIMESTAMP,
                            timestamp = ?
                        WHERE id = ?
                    """, (
                        combined_question,
                        combined_response,
                        inferred_species,
                        documents_used,
                        tables_used,
                        int(fallback_used),
                        completeness_score,
                        missing_fields,
                        follow_ups_count,
                        int(rag_used),
                        conversation.confidence_score,
                        conversation.response_time_ms,
                        timestamp,
                        existing["id"]
                    ))
                    return existing["id"]

                # New conversation
                record_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO conversations (
                        id, conversation_id, user_id, question, response,
                        feedback, confidence_score, response_time_ms,
                        language, rag_used, timestamp,
                        inferred_species, documents_used, tables_used, fallback_used,
                        completeness_score, missing_fields, follow_ups_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    int(bool(conversation.rag_used)),
                    timestamp,
                    conversation.inferred_species,
                    conversation.documents_used,
                    conversation.tables_used,
                    int(bool(conversation.fallback_used)) if conversation.fallback_used is not None else None,
                    conversation.completeness_score,
                    json.dumps(conversation.missing_fields or [], ensure_ascii=False) if conversation.missing_fields is not None else None,
                    conversation.follow_ups_count
                ))
                print(f"🆕 [logging] New conversation saved: {conversation.conversation_id}")
                return record_id

        except Exception as e:
            print(f"❌ [logging] save_conversation error: {e}")
            raise

    # Back-compat alias
    def log_conversation(self, conversation: ConversationCreate) -> str:
        return self.save_conversation(conversation)

    # Feedback updaters (unchanged)
    def update_feedback(self, conversation_id: str, feedback: int) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("""
                    UPDATE conversations SET feedback = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE conversation_id = ?
                """, (feedback, conversation_id))
                return cur.rowcount > 0
        except Exception as e:
            print(f"❌ [logging] update_feedback error: {e}")
            return False

    def update_feedback_comment(self, conversation_id: str, comment: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("""
                    UPDATE conversations SET feedback_comment = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE conversation_id = ?
                """, (comment, conversation_id))
                return cur.rowcount > 0
        except Exception as e:
            print(f"❌ [logging] update_feedback_comment error: {e}")
            return False

    def update_feedback_with_comment(self, conversation_id: str, feedback: int, comment: str = None) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("""
                    UPDATE conversations
                    SET feedback = ?, feedback_comment = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE conversation_id = ?
                """, (feedback, comment, conversation_id))
                return cur.rowcount > 0
        except Exception as e:
            print(f"❌ [logging] update_feedback_with_comment error: {e}")
            return False

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,)).fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"❌ [logging] get_conversation error: {e}")
            return None

    def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT conversation_id, user_id, question, response, feedback, feedback_comment,
                           confidence_score, response_time_ms, language, rag_used, timestamp, updated_at,
                           inferred_species, documents_used, tables_used, fallback_used,
                           completeness_score, missing_fields, follow_ups_count,
                           (LENGTH(question) - LENGTH(REPLACE(question, '--- Question suivante ---', ''))) / LENGTH('--- Question suivante ---') + 1 as message_count
                    FROM conversations
                    WHERE user_id = ?
                    ORDER BY datetime(timestamp) DESC
                    LIMIT ?
                """, (user_id, limit))
                out = []
                for r in cursor.fetchall():
                    out.append({
                        "id": str(uuid.uuid4()),
                        "conversation_id": r["conversation_id"],
                        "user_id": r["user_id"],
                        "question": r["question"],
                        "response": r["response"],
                        "message_count": r["message_count"],
                        "timestamp": r["timestamp"],
                        "updated_at": r["updated_at"] or r["timestamp"],
                        "feedback": r["feedback"],
                        "feedback_comment": r["feedback_comment"],
                        "confidence_score": r["confidence_score"],
                        "response_time_ms": r["response_time_ms"],
                        "language": r["language"],
                        "rag_used": r["rag_used"],
                        # new fields
                        "inferred_species": r["inferred_species"],
                        "documents_used": r["documents_used"],
                        "tables_used": r["tables_used"],
                        "fallback_used": r["fallback_used"],
                        "completeness_score": r["completeness_score"],
                        "missing_fields": json.loads(r["missing_fields"]) if r["missing_fields"] else None,
                        "follow_ups_count": r["follow_ups_count"],
                    })
                return out
        except Exception as e:
            print(f"❌ [logging] get_user_conversations error: {e}")
            return []

    # existing analytics (kept) --------------------------
    def get_analytics(self, days: int = 7) -> Dict[str, Any]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                general = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive,
                        COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative,
                        COUNT(CASE WHEN feedback IS NOT NULL THEN 1 END) as total_feedback,
                        COUNT(CASE WHEN feedback_comment IS NOT NULL AND feedback_comment != '' THEN 1 END) as with_comment,
                        AVG(CASE WHEN response_time_ms IS NOT NULL THEN response_time_ms END) as avg_response_time
                    FROM conversations
                    WHERE datetime(timestamp) >= datetime('now', '-{days} days')
                """).fetchone()

                language_stats = conn.execute(f"""
                    SELECT language,
                           COUNT(*) as total,
                           COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive,
                           COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative
                    FROM conversations 
                    WHERE datetime(timestamp) >= datetime('now', '-{days} days')
                    GROUP BY language
                    ORDER BY total DESC
                """).fetchall()

            total, pos, neg, tot_fb, with_comment, avg_rt = general
            satisfaction = round(pos / tot_fb, 3) if tot_fb else 0
            fb_rate = round(tot_fb / total, 3) if total else 0
            return {
                "period_days": days,
                "total_conversations": total,
                "total_feedback": tot_fb,
                "satisfaction_rate": satisfaction,
                "feedback_rate": fb_rate,
                "avg_response_time_ms": round(avg_rt, 2) if avg_rt else None,
                "feedback_breakdown": {"positive": pos, "negative": neg, "with_comment": with_comment},
                "language_stats": [
                    {"language": r[0], "total": r[1], "positive": r[2], "negative": r[3]} for r in language_stats
                ],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ [logging] get_analytics error: {e}")
            return {}

    def get_feedback_analytics(self, user_id: str = None, days: int = 7) -> Dict[str, Any]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                where = f"WHERE datetime(timestamp) >= datetime('now', '-{days} days')"
                params: List[Any] = []
                if user_id:
                    where += " AND user_id = ?"
                    params.append(user_id)

                general = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive,
                        COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative,
                        COUNT(CASE WHEN feedback IS NOT NULL THEN 1 END) as total_feedback,
                        COUNT(CASE WHEN feedback_comment IS NOT NULL AND feedback_comment != '' THEN 1 END) as with_comment,
                        AVG(CASE WHEN response_time_ms IS NOT NULL THEN response_time_ms END) as avg_response_time
                    FROM conversations 
                    {where}
                """, params).fetchone()

                neg_rows = conn.execute(f"""
                    SELECT question, feedback_comment, timestamp, language
                    FROM conversations 
                    {where}
                    AND feedback = -1
                    AND feedback_comment IS NOT NULL AND feedback_comment != ''
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, params).fetchall()
                pos_rows = conn.execute(f"""
                    SELECT question, feedback_comment, timestamp, language
                    FROM conversations 
                    {where}
                    AND feedback = 1
                    AND feedback_comment IS NOT NULL AND feedback_comment != ''
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, params).fetchall()

            total, pos, neg, tot_fb, with_comment, avg_rt = general
            satisfaction = round(pos / tot_fb, 3) if tot_fb else 0
            fb_rate = round(tot_fb / total, 3) if total else 0
            comment_rate = round(with_comment / tot_fb, 3) if tot_fb else 0

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "report": {
                    "period_days": days,
                    "summary": {
                        "total_conversations": total,
                        "total_feedback": tot_fb,
                        "satisfaction_rate": satisfaction,
                        "feedback_rate": fb_rate,
                        "comment_rate": comment_rate,
                        "avg_response_time_ms": round(avg_rt, 2) if avg_rt else None
                    },
                    "feedback_breakdown": {"positive": pos, "negative": neg, "with_comment": with_comment},
                    "top_negative_feedback": [
                        {"question": (r[0][:100] + "...") if len(r[0]) > 100 else r[0], "comment": r[1], "timestamp": r[2], "language": r[3]}
                        for r in neg_rows
                    ],
                    "top_positive_feedback": [
                        {"question": (r[0][:100] + "...") if len(r[0]) > 100 else r[0], "comment": r[1], "timestamp": r[2], "language": r[3]}
                        for r in pos_rows
                    ],
                }
            }
        except Exception as e:
            print(f"❌ [logging] get_feedback_analytics error: {e}")
            return {"status": "error", "error": str(e)}

    # NEW: RAG analytics ------------------------------------------------------
    def get_rag_analytics(self, days: int = 7, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Compute fallback %, top-5 missing_fields, avg completeness_score."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                where = f"datetime(timestamp) >= datetime('now', '-{days} days')"
                params: List[Any] = []
                if user_id:
                    where += " AND user_id = ?"
                    params.append(user_id)

                rows = conn.execute(f"""
                    SELECT fallback_used, completeness_score, missing_fields
                    FROM conversations
                    WHERE {where}
                """, params).fetchall()

            total = len(rows)
            if total == 0:
                return {
                    "period_days": days, "total": 0,
                    "fallback_rate": 0.0, "avg_completeness_score": None,
                    "top_missing_fields": []
                }

            fallback_cnt = sum(1 for r in rows if r["fallback_used"])
            comp_scores = [r["completeness_score"] for r in rows if r["completeness_score"] is not None]
            avg_comp = round(sum(comp_scores) / len(comp_scores), 3) if comp_scores else None

            # aggregate missing_fields
            counter: Dict[str, int] = {}
            for r in rows:
                if not r["missing_fields"]:
                    continue
                try:
                    lst = json.loads(r["missing_fields"]) or []
                    for f in lst:
                        if not f:
                            continue
                        counter[f] = counter.get(f, 0) + 1
                except Exception:
                    pass
            top5 = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:5]
            top_list = [{"field": k, "count": v} for k, v in top5]

            return {
                "period_days": days,
                "total": total,
                "fallback_rate": round(fallback_cnt / total, 3),
                "avg_completeness_score": avg_comp,
                "top_missing_fields": top_list
            }
        except Exception as e:
            print(f"❌ [logging] get_rag_analytics error: {e}")
            return {}

# ============================================================================
# Global instance
# ============================================================================

logger_instance = ConversationLogger()

# ============================================================================
# API endpoints
# ============================================================================

@router.post("/conversation")
async def log_conversation_endpoint(conversation: ConversationCreate):
    try:
        rec_id = logger_instance.save_conversation(conversation)
        return {
            "status": "success",
            "message": "Conversation enregistrée",
            "record_id": rec_id,
            "conversation_id": conversation.conversation_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement: {str(e)}")

@router.patch("/conversation/{conversation_id}/feedback")
async def update_conversation_feedback(conversation_id: str, feedback_data: dict):
    try:
        feedback_value = None
        if isinstance(feedback_data, dict):
            if "feedback" in feedback_data:
                feedback_value = feedback_data["feedback"]
            elif "rating" in feedback_data:
                feedback_value = {"positive": 1, "negative": -1, "neutral": 0}.get(feedback_data["rating"], 0)
            elif "vote" in feedback_data:
                feedback_value = {"up": 1, "down": -1, "neutral": 0}.get(feedback_data["vote"], 0)

        if feedback_value is None or feedback_value not in (-1, 0, 1):
            raise HTTPException(status_code=400, detail="Valeur feedback invalide")

        ok = logger_instance.update_feedback(conversation_id, feedback_value)
        if not ok:
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
        return {"status": "success", "conversation_id": conversation_id, "feedback": feedback_value, "timestamp": datetime.now().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur feedback: {str(e)}")

@router.get("/conversation/{conversation_id}")
async def get_conversation_endpoint(conversation_id: str):
    conv = logger_instance.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    return {"status": "success", "conversation": conv, "timestamp": datetime.now().isoformat()}

@router.get("/conversations/user/{user_id}")
async def get_user_conversations_endpoint(user_id: str, limit: int = 50):
    conversations = logger_instance.get_user_conversations(user_id, limit)
    return {
        "status": "success",
        "user_id": user_id,
        "conversations": conversations,
        "count": len(conversations),
        "limit": limit,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/analytics")
async def get_analytics_endpoint(days: int = 7):
    analytics = logger_instance.get_analytics(days)
    return {"status": "success", "analytics": analytics, "timestamp": datetime.now().isoformat()}

# NEW
@router.get("/analytics/rag")
async def get_rag_analytics_endpoint(days: int = 7, user_id: Optional[str] = None):
    """
    Returns:
      - fallback_rate: nb réponses fallback / total
      - avg_completeness_score
      - top_missing_fields (Top-5)
    """
    analytics = logger_instance.get_rag_analytics(days=days, user_id=user_id)
    return {"status": "success", "analytics": analytics, "timestamp": datetime.now().isoformat()}

# feedback comment endpoints (kept) ------------------------------------------

@router.patch("/conversation/{conversation_id}/comment")
async def update_feedback_comment(conversation_id: str, comment_data: FeedbackCommentUpdate):
    ok = logger_instance.update_feedback_comment(conversation_id, comment_data.comment)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    return {
        "status": "success",
        "message": "Commentaire feedback mis à jour",
        "conversation_id": conversation_id,
        "comment": comment_data.comment[:100] + "..." if len(comment_data.comment) > 100 else comment_data.comment,
        "timestamp": datetime.now().isoformat()
    }

@router.patch("/conversation/{conversation_id}/feedback-with-comment")
async def update_feedback_with_comment(conversation_id: str, feedback_data: FeedbackWithCommentUpdate):
    ok = logger_instance.update_feedback_with_comment(conversation_id, feedback_data.feedback, feedback_data.comment)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    return {
        "status": "success",
        "message": "Feedback avec commentaire mis à jour",
        "conversation_id": conversation_id,
        "feedback": feedback_data.feedback,
        "comment": feedback_data.comment[:100] + "..." if feedback_data.comment and len(feedback_data.comment) > 100 else feedback_data.comment,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/conversations/with-comments")
async def get_conversations_with_comments(limit: int = 20, user_id: str = None):
    try:
        with sqlite3.connect(logger_instance.db_path) as conn:
            conn.row_factory = sqlite3.Row
            where = "WHERE feedback_comment IS NOT NULL AND feedback_comment != ''"
            params: List[Any] = []
            if user_id:
                where += " AND user_id = ?"
                params.append(user_id)
            cur = conn.execute(f"""
                SELECT conversation_id, user_id, question, feedback, feedback_comment, timestamp, language
                FROM conversations
                {where}
                ORDER BY datetime(timestamp) DESC
                LIMIT ?
            """, params + [limit])
            out = []
            for r in cur.fetchall():
                out.append({
                    "conversation_id": r["conversation_id"],
                    "user_id": r["user_id"],
                    "question": r["question"],
                    "feedback": "positive" if r["feedback"] == 1 else "negative",
                    "feedback_comment": r["feedback_comment"],
                    "timestamp": r["timestamp"],
                    "language": r["language"]
                })
        return {"status": "success", "timestamp": datetime.now().isoformat(), "conversations": out, "count": len(out)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération: {str(e)}")

@router.get("/admin/feedback-report")
async def get_admin_feedback_report(days: int = 30):
    try:
        with sqlite3.connect(logger_instance.db_path) as conn:
            general = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_conversations,
                    COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive_feedback,
                    COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative_feedback,
                    COUNT(CASE WHEN feedback_comment IS NOT NULL AND feedback_comment != '' THEN 1 END) as with_comment
                FROM conversations 
                WHERE datetime(timestamp) >= datetime('now', '-{days} days')
            """).fetchone()
            recent = conn.execute(f"""
                SELECT conversation_id, feedback, feedback_comment, timestamp, question
                FROM conversations
                WHERE datetime(timestamp) >= datetime('now', '-{days} days')
                AND feedback_comment IS NOT NULL AND feedback_comment != ''
                ORDER BY datetime(timestamp) DESC LIMIT 10
            """).fetchall()
        tfb = (general[1] or 0) + (general[2] or 0)
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "report": {
                "period_days": days,
                "general_stats": {
                    "total_conversations": general[0],
                    "positive_feedback": general[1],
                    "negative_feedback": general[2],
                    "total_feedback": tfb,
                    "with_comment": general[3]
                },
                "satisfaction_rate": round(general[1] / tfb, 3) if tfb else None,
                "comment_rate": round((general[3] or 0) / tfb, 3) if tfb else 0,
                "recent_comments": [
                    {
                        "conversation_id": r[0],
                        "feedback": "positive" if r[1] == 1 else "negative",
                        "comment": r[2],
                        "timestamp": r[3],
                        "question_preview": r[4][:100] + "..." if len(r[4]) > 100 else r[4]
                    } for r in recent
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur rapport: {str(e)}")

@router.post("/admin/export-feedback")
async def export_feedback_data(days: int = 30, format: str = "json"):
    try:
        with sqlite3.connect(logger_instance.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(f"""
                SELECT 
                    conversation_id, user_id, question, feedback, feedback_comment,
                    confidence_score, response_time_ms, language, rag_used, timestamp, updated_at,
                    inferred_species, documents_used, tables_used, fallback_used,
                    completeness_score, missing_fields, follow_ups_count
                FROM conversations
                WHERE datetime(timestamp) >= datetime('now', '-{days} days')
                AND feedback IS NOT NULL
                ORDER BY datetime(timestamp) DESC
            """)
            data = []
            for r in cur.fetchall():
                data.append({
                    "conversation_id": r["conversation_id"],
                    "user_id": (r["user_id"][:8] + "...") if len(r["user_id"]) > 12 else r["user_id"],
                    "question_length": len(r["question"]),
                    "question_preview": r["question"][:50] + "..." if len(r["question"]) > 50 else r["question"],
                    "feedback": "positive" if r["feedback"] == 1 else "negative",
                    "has_comment": bool(r["feedback_comment"]),
                    "comment_length": len(r["feedback_comment"]) if r["feedback_comment"] else 0,
                    "comment_preview": r["feedback_comment"][:100] + "..." if r["feedback_comment"] and len(r["feedback_comment"]) > 100 else r["feedback_comment"],
                    "confidence_score": r["confidence_score"],
                    "response_time_ms": r["response_time_ms"],
                    "language": r["language"],
                    "rag_used": r["rag_used"],
                    "timestamp": r["timestamp"],
                    # NEW
                    "inferred_species": r["inferred_species"],
                    "documents_used": r["documents_used"],
                    "tables_used": r["tables_used"],
                    "fallback_used": r["fallback_used"],
                    "completeness_score": r["completeness_score"],
                    "missing_fields": json.loads(r["missing_fields"]) if r["missing_fields"] else None,
                    "follow_ups_count": r["follow_ups_count"],
                })
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "export_format": format,
            "period_days": days,
            "total_records": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur export: {str(e)}")

print("✅ logging.py loaded: extended metrics + /logging/analytics/rag ready")
