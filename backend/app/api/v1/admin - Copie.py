from fastapi import APIRouter, HTTPException, Query
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import sqlite3
import json

router = APIRouter(prefix="/admin")
logger = logging.getLogger(__name__)

RAG_INDEX_ROOT = Path(os.getenv("RAG_INDEX_ROOT", "rag_index"))
DB_PATH = os.getenv("CONV_DB_PATH", "conversations.db")

def _rag_index_status() -> Dict[str, Any]:
    species = ["global", "broiler", "layer"]
    status = {}
    for sp in species:
        p = RAG_INDEX_ROOT / sp
        status[sp] = {
            "path": str(p),
            "exists": p.exists(),
            "has_faiss": (p / "index.faiss").exists(),
            "has_meta": (p / "meta.json").exists(),
        }
    status["total_present"] = sum(1 for sp in species if status[sp]["exists"])
    return status

@router.get("/dashboard")
async def get_dashboard() -> Dict[str, Any]:
    try:
        openai_configured = bool(os.getenv("OPENAI_API_KEY"))
        rag_status = _rag_index_status()
        diagnostics = {
            "openai_configured": openai_configured,
            "rag_indexes": rag_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        return {"status": "success", "diagnostics": diagnostics}
    except Exception as e:
        logger.exception("Dashboard error")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboard status: {e}")

@router.get("/users")
async def get_users() -> Dict[str, Any]:
    try:
        users: List[str] = []
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT DISTINCT user_id FROM conversations
                ORDER BY user_id
            """).fetchall()
            users = [r["user_id"] for r in rows]
            sessions = conn.execute("""
                SELECT conversation_id, user_id, timestamp
                FROM conversations
                ORDER BY datetime(timestamp) DESC
                LIMIT 20
            """).fetchall()
        return {
            "status": "success",
            "total_users": len(users),
            "users": users,
            "recent_sessions": [
                {"conversation_id": r["conversation_id"], "user_id": r["user_id"], "timestamp": r["timestamp"]}
                for r in sessions
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.exception("Get users error")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users list: {e}")

@router.get("/rag/diagnostics")
async def get_rag_diagnostics() -> Dict[str, Any]:
    try:
        return {
            "status": "success",
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
            "rag_indexes": _rag_index_status(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.exception("RAG diagnostics error")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve RAG diagnostics: {e}")

@router.get("/rag/test")
async def test_rag_end_to_end() -> Dict[str, Any]:
    try:
        from .pipeline.rag_engine import RAGEngine
        rag = RAGEngine()
        test_question = "Température optimale en démarrage pour Ross 308 ?"
        answer = rag.generate_answer(test_question, {})
        return {
            "status": "success",
            "test_question": test_question,
            "test_answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.exception("RAG test error")
        raise HTTPException(status_code=500, detail=f"RAG end-to-end test failed: {e}")

# -------- NEW: Admin RAG analytics (dates, filters) --------------------------

@router.get("/analytics/rag")
async def admin_rag_analytics(
    days: int = Query(7, ge=1, le=365),
    user_id: Optional[str] = Query(None, description="Filter by user_id")
) -> Dict[str, Any]:
    """
    Aggregated metrics useful for Admin dashboard:
      - fallback_rate
      - avg_completeness_score
      - top_missing_fields (Top-5)
    Filters:
      - days (rolling window)
      - user_id (optional)
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            where = f"datetime(timestamp) >= datetime('now', '-{days} days')"
            params: List[Any] = []
            if user_id:
                where += " AND user_id = ?"
                params.append(user_id)
            rows = conn.execute(f"""
                SELECT inferred_species, fallback_used, completeness_score, missing_fields
                FROM conversations
                WHERE {where}
            """, params).fetchall()

        total = len(rows)
        fallback_cnt = sum(1 for r in rows if r["fallback_used"])
        comp_scores = [r["completeness_score"] for r in rows if r["completeness_score"] is not None]
        avg_comp = round(sum(comp_scores) / len(comp_scores), 3) if comp_scores else None

        # top missing fields
        mf_counter: Dict[str, int] = {}
        for r in rows:
            if r["missing_fields"]:
                try:
                    for f in json.loads(r["missing_fields"]) or []:
                        if f:
                            mf_counter[f] = mf_counter.get(f, 0) + 1
                except Exception:
                    pass
        top5 = [{"field": k, "count": v} for k, v in sorted(mf_counter.items(), key=lambda x: x[1], reverse=True)[:5]]

        # simple species split
        by_species: Dict[str, int] = {}
        for r in rows:
            sp = r["inferred_species"] or "unknown"
            by_species[sp] = by_species.get(sp, 0) + 1

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "period_days": days,
            "filters": {"user_id": user_id},
            "metrics": {
                "total": total,
                "fallback_rate": round(fallback_cnt / total, 3) if total else 0.0,
                "avg_completeness_score": avg_comp,
                "top_missing_fields": top5,
                "by_species": by_species
            }
        }
    except Exception as e:
        logger.exception("Admin RAG analytics error")
        raise HTTPException(status_code=500, detail=f"Failed to compute RAG analytics: {e}")

@router.get("/analytics")
async def get_analytics():
    # Kept for backward compatibility; recommend using /admin/analytics/rag
    return {"status": "deprecated", "use": "/admin/analytics/rag"}
