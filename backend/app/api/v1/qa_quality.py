"""
API Endpoints pour l'analyse de qualité Q&A
Permet de détecter et gérer les réponses problématiques
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from psycopg2.extras import RealDictCursor
import json
import os
import sys

from app.core.database import get_pg_connection, get_user_from_supabase
from app.services.qa_quality_analyzer import qa_analyzer
from app.api.v1.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa-quality", tags=["qa-quality"])


def verify_admin_access(current_user: Dict[str, Any]):
    """Vérifie que l'utilisateur est admin"""
    user_type = current_user.get("user_type", "user")
    if user_type not in ["admin", "super_admin"]:
        logger.warning(
            f"Tentative d'accès non autorisé par {current_user.get('email')} (type: {user_type})"
        )
        raise HTTPException(
            status_code=403,
            detail="Accès refusé. Droits administrateur requis."
        )
    return True


# ============================================================================
# GET PROBLEMATIC Q&A
# ============================================================================

@router.get("/problematic")
async def get_problematic_qa(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    reviewed: Optional[bool] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=10),
    max_score: Optional[float] = Query(None, ge=0, le=10),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Récupère les Q&A problématiques avec pagination et filtres

    Filtres disponibles:
    - category: Type de problème (incorrect, incomplete, off_topic, etc.)
    - reviewed: Statut de révision (true/false)
    - min_score, max_score: Plage de scores de qualité

    Returns:
        Liste paginée des Q&A problématiques avec détails utilisateur
    """
    verify_admin_access(current_user)

    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                offset = (page - 1) * limit

                # Construction de la requête avec filtres
                where_clauses = ["qc.is_problematic = true", "qc.false_positive = false"]
                params = []

                if category:
                    where_clauses.append("qc.problem_category = %s")
                    params.append(category)

                if reviewed is not None:
                    where_clauses.append("qc.reviewed = %s")
                    params.append(reviewed)

                if min_score is not None:
                    where_clauses.append("qc.quality_score >= %s")
                    params.append(min_score)

                if max_score is not None:
                    where_clauses.append("qc.quality_score <= %s")
                    params.append(max_score)

                where_clause = " AND ".join(where_clauses)

                # Compter le total
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM qa_quality_checks qc
                    WHERE {where_clause}
                """
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]

                # Récupérer les Q&A problématiques
                query = f"""
                    SELECT
                        qc.id::text as id,
                        qc.conversation_id::text as conversation_id,
                        qc.message_id::text as message_id,
                        qc.user_id::text as user_id,
                        qc.question,
                        qc.response,
                        qc.response_source,
                        qc.response_confidence,
                        qc.quality_score,
                        qc.problem_category,
                        qc.problems,
                        qc.recommendation,
                        qc.analysis_confidence,
                        qc.analyzed_at,
                        qc.reviewed,
                        qc.reviewed_at,
                        qc.reviewed_by::text as reviewed_by,
                        qc.reviewer_notes,
                        c.language,
                        c.created_at as conversation_created_at
                    FROM qa_quality_checks qc
                    JOIN conversations c ON qc.conversation_id = c.id
                    WHERE {where_clause}
                    ORDER BY qc.analyzed_at DESC
                    LIMIT %s OFFSET %s
                """

                cur.execute(query, params + [limit, offset])
                rows = cur.fetchall()

                # Enrichir avec les données utilisateur
                user_ids = list(set(row["user_id"] for row in rows))
                users_data = {}

                for user_id in user_ids:
                    user_info = get_user_from_supabase(user_id)
                    if user_info:
                        users_data[user_id] = {
                            "email": user_info.get("email", ""),
                            "first_name": user_info.get("first_name", ""),
                            "last_name": user_info.get("last_name", "")
                        }

                # Formater les résultats
                problematic_qa = []
                for row in rows:
                    user_id = row["user_id"]
                    user_info = users_data.get(user_id, {})

                    problematic_qa.append({
                        "id": row["id"],
                        "conversation_id": row["conversation_id"],
                        "message_id": row["message_id"],
                        "user_id": user_id,
                        "user_email": user_info.get("email", ""),
                        "user_name": f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip(),
                        "question": row["question"],
                        "response": row["response"],
                        "response_source": row["response_source"],
                        "response_confidence": float(row["response_confidence"]) if row["response_confidence"] else None,
                        "quality_score": float(row["quality_score"]) if row["quality_score"] else None,
                        "problem_category": row["problem_category"],
                        "problems": row["problems"] if isinstance(row["problems"], list) else json.loads(row["problems"] or "[]"),
                        "recommendation": row["recommendation"],
                        "analysis_confidence": float(row["analysis_confidence"]) if row["analysis_confidence"] else None,
                        "language": row["language"],
                        "analyzed_at": row["analyzed_at"].isoformat() if row["analyzed_at"] else None,
                        "conversation_created_at": row["conversation_created_at"].isoformat() if row["conversation_created_at"] else None,
                        "reviewed": row["reviewed"],
                        "reviewed_at": row["reviewed_at"].isoformat() if row["reviewed_at"] else None,
                        "reviewed_by": row["reviewed_by"],
                        "reviewer_notes": row["reviewer_notes"]
                    })

                pages = (total + limit - 1) // limit

                return {
                    "problematic_qa": problematic_qa,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total,
                        "pages": pages,
                        "has_next": (offset + limit) < total,
                        "has_prev": page > 1
                    },
                    "filters_applied": {
                        "category": category,
                        "reviewed": reviewed,
                        "min_score": min_score,
                        "max_score": max_score
                    }
                }

    except Exception as e:
        logger.error(f"[QA_QUALITY] Error fetching problematic Q&A: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANALYZE BATCH
# ============================================================================

@router.post("/analyze-batch")
async def analyze_batch(
    limit: int = Query(50, ge=1, le=500, description="Nombre de Q&A à analyser"),
    force_recheck: bool = Query(False, description="Forcer la ré-analyse des Q&A déjà vérifiées"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Analyse un batch de Q&A en mode asynchrone

    Stratégie:
    - Priorise les Q&A avec feedback négatif
    - Ensuite les Q&A avec faible confidence
    - Évite les Q&A déjà analysées (sauf si force_recheck=true)

    Returns:
        Statistiques de l'analyse batch
    """
    verify_admin_access(current_user)

    try:
        analyzed_count = 0
        problematic_found = 0
        errors = 0

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Sélectionner les Q&A à analyser
                # Priorité: feedback négatif > faible confidence > anciennes

                exclude_clause = ""
                if not force_recheck:
                    exclude_clause = """
                        AND c.id NOT IN (
                            SELECT conversation_id FROM qa_quality_checks
                        )
                    """

                query = f"""
                    SELECT
                        c.id::text as conversation_id,
                        c.user_id::text as user_id,
                        m_user.id::text as user_message_id,
                        m_user.content as question,
                        m_assistant.id::text as assistant_message_id,
                        m_assistant.content as response,
                        m_assistant.response_source,
                        m_assistant.response_confidence,
                        m_assistant.feedback
                    FROM conversations c
                    JOIN messages m_user ON m_user.conversation_id = c.id AND m_user.role = 'user'
                    JOIN messages m_assistant ON m_assistant.conversation_id = c.id
                        AND m_assistant.role = 'assistant'
                        AND m_assistant.sequence_number = m_user.sequence_number + 1
                    WHERE c.status = 'active'
                        {exclude_clause}
                    ORDER BY
                        CASE WHEN m_assistant.feedback = '-1' THEN 0 ELSE 1 END,
                        COALESCE(m_assistant.response_confidence, 0) ASC,
                        c.created_at DESC
                    LIMIT %s
                """

                cur.execute(query, (limit,))
                qa_to_analyze = cur.fetchall()

                logger.info(f"[QA_QUALITY] Batch analysis: {len(qa_to_analyze)} Q&A to analyze")

                # Analyser chaque Q&A
                for qa in qa_to_analyze:
                    try:
                        # Déterminer le trigger
                        trigger = "batch"
                        confidence = qa.get("response_confidence")
                        if qa["feedback"] == "-1" or qa["feedback"] == -1:
                            trigger = "negative_feedback"
                        elif confidence is not None and confidence < 0.3:
                            trigger = "low_confidence"

                        # Analyser
                        analysis_result = await qa_analyzer.analyze_qa(
                            question=qa["question"],
                            response=qa["response"],
                            response_source=qa.get("response_source"),
                            response_confidence=qa.get("response_confidence"),
                            trigger=trigger
                        )

                        # Sauvegarder les résultats
                        if not analysis_result.get("error"):
                            cur.execute(
                                """
                                INSERT INTO qa_quality_checks (
                                    conversation_id,
                                    message_id,
                                    user_id,
                                    question,
                                    response,
                                    response_source,
                                    response_confidence,
                                    quality_score,
                                    is_problematic,
                                    problem_category,
                                    problems,
                                    recommendation,
                                    analysis_confidence,
                                    analysis_trigger,
                                    analysis_model,
                                    analysis_prompt_version
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    qa["conversation_id"],
                                    qa["assistant_message_id"],
                                    qa["user_id"],
                                    qa["question"],
                                    qa["response"],
                                    qa.get("response_source"),
                                    qa.get("response_confidence"),
                                    analysis_result["quality_score"],
                                    analysis_result["is_problematic"],
                                    analysis_result["problem_category"],
                                    json.dumps(analysis_result["problems"]),
                                    analysis_result["recommendation"],
                                    analysis_result["analysis_confidence"],
                                    analysis_result["analysis_trigger"],
                                    analysis_result["analysis_model"],
                                    analysis_result["analysis_prompt_version"]
                                )
                            )
                            conn.commit()

                            analyzed_count += 1
                            if analysis_result["is_problematic"]:
                                problematic_found += 1
                        else:
                            errors += 1
                            logger.error(f"Analysis error for conversation {qa['conversation_id']}")

                    except Exception as e:
                        errors += 1
                        logger.error(f"Error analyzing Q&A {qa.get('conversation_id')}: {e}")
                        continue

        logger.info(
            f"[QA_QUALITY] Batch analysis complete: "
            f"{analyzed_count} analyzed, {problematic_found} problematic, {errors} errors"
        )

        return {
            "status": "completed",
            "analyzed_count": analyzed_count,
            "problematic_found": problematic_found,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"[QA_QUALITY] Batch analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# REVIEW Q&A
# ============================================================================

@router.patch("/{check_id}/review")
async def review_qa(
    check_id: str,
    reviewed: bool,
    false_positive: bool = False,
    reviewer_notes: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Marquer une Q&A comme reviewée ou comme faux positif

    Args:
        check_id: ID de la vérification
        reviewed: Marquer comme reviewé
        false_positive: Marquer comme faux positif
        reviewer_notes: Notes du revieweur
    """
    verify_admin_access(current_user)

    try:
        user_id = current_user.get("user_id") or current_user.get("sub") or current_user.get("id")

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE qa_quality_checks
                    SET reviewed = %s,
                        reviewed_at = CASE WHEN %s THEN NOW() ELSE reviewed_at END,
                        reviewed_by = %s,
                        false_positive = %s,
                        reviewer_notes = %s
                    WHERE id = %s
                    RETURNING id, reviewed, false_positive
                    """,
                    (reviewed, reviewed, user_id, false_positive, reviewer_notes, check_id)
                )

                result = cur.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="QA check not found")

                conn.commit()

                return {
                    "id": result["id"],
                    "reviewed": result["reviewed"],
                    "false_positive": result["false_positive"],
                    "message": "QA check updated successfully"
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QA_QUALITY] Review error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{check_id}")
async def delete_qa_check(
    check_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Supprimer définitivement une entrée de qa_quality_checks

    Args:
        check_id: ID de la vérification à supprimer

    Returns:
        Message de confirmation de suppression
    """
    verify_admin_access(current_user)

    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Vérifier que l'entrée existe avant de la supprimer
                cur.execute(
                    "SELECT id FROM qa_quality_checks WHERE id = %s",
                    (check_id,)
                )

                result = cur.fetchone()

                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail=f"QA check {check_id} not found"
                    )

                # Supprimer l'entrée
                cur.execute(
                    "DELETE FROM qa_quality_checks WHERE id = %s",
                    (check_id,)
                )

                conn.commit()

                logger.info(f"[QA_QUALITY] Admin {current_user.get('email')} deleted check_id={check_id}")

                return {
                    "id": check_id,
                    "message": "QA check deleted successfully"
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QA_QUALITY] Delete error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS
# ============================================================================

@router.get("/stats")
async def get_qa_quality_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Statistiques globales de qualité Q&A

    Returns:
        - Total Q&A analysées
        - % problématiques
        - Distribution par catégorie
        - Évolution temporelle
        - Top problèmes
    """
    verify_admin_access(current_user)

    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                start_date = datetime.now() - timedelta(days=days)

                # Stats générales
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_analyzed,
                        COUNT(*) FILTER (WHERE is_problematic = true) as total_problematic,
                        COUNT(*) FILTER (WHERE reviewed = true) as total_reviewed,
                        COUNT(*) FILTER (WHERE false_positive = true) as total_false_positives,
                        AVG(quality_score) as avg_quality_score,
                        AVG(analysis_confidence) as avg_confidence
                    FROM qa_quality_checks
                    WHERE analyzed_at >= %s
                    """,
                    (start_date,)
                )

                general_stats = cur.fetchone()

                # Distribution par catégorie
                cur.execute(
                    """
                    SELECT problem_category, COUNT(*) as count
                    FROM qa_quality_checks
                    WHERE analyzed_at >= %s AND is_problematic = true
                    GROUP BY problem_category
                    ORDER BY count DESC
                    """,
                    (start_date,)
                )

                category_distribution = {
                    row["problem_category"]: row["count"]
                    for row in cur.fetchall()
                }

                # Évolution temporelle (par jour)
                cur.execute(
                    """
                    SELECT
                        DATE(analyzed_at) as date,
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE is_problematic = true) as problematic
                    FROM qa_quality_checks
                    WHERE analyzed_at >= %s
                    GROUP BY DATE(analyzed_at)
                    ORDER BY date DESC
                    LIMIT 30
                    """,
                    (start_date,)
                )

                timeline = [
                    {
                        "date": row["date"].isoformat(),
                        "total": row["total"],
                        "problematic": row["problematic"]
                    }
                    for row in cur.fetchall()
                ]

                total = general_stats["total_analyzed"] or 1
                problematic_rate = (general_stats["total_problematic"] or 0) / total * 100

                return {
                    "period_days": days,
                    "total_analyzed": general_stats["total_analyzed"] or 0,
                    "total_problematic": general_stats["total_problematic"] or 0,
                    "problematic_rate": round(problematic_rate, 1),
                    "total_reviewed": general_stats["total_reviewed"] or 0,
                    "total_false_positives": general_stats["total_false_positives"] or 0,
                    "avg_quality_score": round(float(general_stats["avg_quality_score"] or 0), 2),
                    "avg_confidence": round(float(general_stats["avg_confidence"] or 0), 2),
                    "category_distribution": category_distribution,
                    "timeline": timeline
                }

    except Exception as e:
        logger.error(f"[QA_QUALITY] Stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CRON ENDPOINT - AUTOMATIC ANALYSIS
# ============================================================================

@router.post("/cron")
async def cron_analyze_batch(
    cron_secret: str = Query(..., description="Secret pour authentifier le cron job")
) -> Dict[str, Any]:
    """
    Endpoint pour analyse automatique via cron job (2h AM et 2h PM)

    Sécurité: Vérifie le secret CRON_SECRET dans les variables d'environnement

    Stratégie d'analyse:
    - 100 Q&A par exécution
    - Priorité: feedback négatif > faible confidence > récentes
    - Skip les Q&A déjà analysées

    Returns:
        Statistiques de l'analyse automatique
    """
    import os

    # Vérifier le secret du cron
    expected_secret = os.getenv("CRON_SECRET_KEY")
    if not expected_secret:
        logger.error("[QA_QUALITY_CRON] CRON_SECRET_KEY non configuré dans l'environnement")
        raise HTTPException(
            status_code=500,
            detail="CRON_SECRET_KEY not configured on server"
        )

    if cron_secret != expected_secret:
        logger.warning(f"[QA_QUALITY_CRON] Tentative d'accès avec secret invalide")
        raise HTTPException(
            status_code=403,
            detail="Invalid cron secret"
        )

    # Lancer l'analyse automatique
    try:
        logger.info("🤖 [QA_QUALITY_CRON] Démarrage analyse automatique (cron trigger)")

        analyzed_count = 0
        problematic_found = 0
        errors = 0

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Sélectionner 100 Q&A non analysées
                query = """
                    SELECT
                        c.id::text as conversation_id,
                        c.user_id::text as user_id,
                        m_user.id::text as user_message_id,
                        m_user.content as question,
                        m_assistant.id::text as assistant_message_id,
                        m_assistant.content as response,
                        m_assistant.response_source,
                        m_assistant.response_confidence,
                        m_assistant.feedback
                    FROM conversations c
                    JOIN messages m_user ON m_user.conversation_id = c.id AND m_user.role = 'user'
                    JOIN messages m_assistant ON m_assistant.conversation_id = c.id
                        AND m_assistant.role = 'assistant'
                        AND m_assistant.sequence_number = m_user.sequence_number + 1
                    WHERE c.status = 'active'
                        AND c.id NOT IN (
                            SELECT conversation_id FROM qa_quality_checks
                        )
                    ORDER BY
                        CASE WHEN m_assistant.feedback = '-1' THEN 0 ELSE 1 END,
                        COALESCE(m_assistant.response_confidence, 0) ASC,
                        c.created_at DESC
                    LIMIT 100
                """

                cur.execute(query)
                qa_to_analyze = cur.fetchall()

                logger.info(f"[QA_QUALITY_CRON] {len(qa_to_analyze)} Q&A sélectionnées pour analyse")

                # Analyser chaque Q&A
                for qa in qa_to_analyze:
                    try:
                        # Déterminer le trigger
                        trigger = "cron_automatic"
                        confidence = qa.get("response_confidence")
                        if qa["feedback"] == "-1" or qa["feedback"] == -1:
                            trigger = "cron_negative_feedback"
                        elif confidence is not None and confidence < 0.3:
                            trigger = "cron_low_confidence"

                        # Analyser
                        analysis_result = await qa_analyzer.analyze_qa(
                            question=qa["question"],
                            response=qa["response"],
                            response_source=qa.get("response_source"),
                            response_confidence=qa.get("response_confidence"),
                            trigger=trigger
                        )

                        # Sauvegarder les résultats
                        if not analysis_result.get("error"):
                            cur.execute(
                                """
                                INSERT INTO qa_quality_checks (
                                    conversation_id,
                                    message_id,
                                    user_id,
                                    question,
                                    response,
                                    response_source,
                                    response_confidence,
                                    quality_score,
                                    is_problematic,
                                    problem_category,
                                    problems,
                                    recommendation,
                                    analysis_confidence,
                                    analysis_trigger,
                                    analysis_model,
                                    analysis_prompt_version
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    qa["conversation_id"],
                                    qa["assistant_message_id"],
                                    qa["user_id"],
                                    qa["question"],
                                    qa["response"],
                                    qa.get("response_source"),
                                    qa.get("response_confidence"),
                                    analysis_result["quality_score"],
                                    analysis_result["is_problematic"],
                                    analysis_result["problem_category"],
                                    json.dumps(analysis_result["problems"]),
                                    analysis_result["recommendation"],
                                    analysis_result["analysis_confidence"],
                                    analysis_result["analysis_trigger"],
                                    analysis_result["analysis_model"],
                                    analysis_result["analysis_prompt_version"]
                                )
                            )
                            conn.commit()

                            analyzed_count += 1
                            if analysis_result["is_problematic"]:
                                problematic_found += 1
                        else:
                            errors += 1
                            logger.error(f"[QA_QUALITY_CRON] Analysis error for {qa['conversation_id']}")

                    except Exception as e:
                        errors += 1
                        logger.error(f"[QA_QUALITY_CRON] Error analyzing {qa.get('conversation_id')}: {e}")
                        continue

        logger.info(
            f"[QA_QUALITY_CRON] Analyse automatique terminée: "
            f"{analyzed_count} analysées, {problematic_found} anomalies détectées, {errors} erreurs"
        )

        return {
            "status": "completed",
            "trigger": "cron_automatic",
            "analyzed_count": analyzed_count,
            "problematic_found": problematic_found,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"[QA_QUALITY_CRON] Erreur critique: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANALYZE COT - Admin debugging with Claude Extended Thinking
# ============================================================================

@router.post("/analyze-cot/{check_id}")
async def analyze_cot(
    check_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Analyze a specific QA quality check with Claude Extended Thinking.

    This endpoint is ONLY for admin debugging of anomalies.
    It re-generates the response using Claude Extended Thinking to understand
    WHY the system gave a problematic response.

    Args:
        check_id: ID of the qa_quality_checks record to analyze
        current_user: Authenticated admin user

    Returns:
        Dict with CoT analysis results:
            - response: The re-generated response with Claude
            - thinking: Claude's reasoning blocks
            - thinking_tokens: Number of thinking tokens used
            - cost_usd: Cost of this analysis
            - analyzed_at: Timestamp
            - analyzed_by: Admin email
    """
    verify_admin_access(current_user)
    admin_email = current_user.get("email")

    logger.info(f"🧠 [COT_ANALYSIS] Admin {admin_email} requesting CoT for check_id={check_id}")

    # Import LLM dependencies only when needed (avoids breaking module if LLM not available)
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))
        from llm.generation.generators import create_enhanced_generator
        from llm.core.data_models import Document
        from openai import AsyncOpenAI
    except ImportError as e:
        logger.error(f"🧠 [COT_ANALYSIS] Failed to import LLM dependencies: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"CoT analysis unavailable: LLM dependencies not found ({str(e)})"
        )

    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Fetch the QA quality check record
                cur.execute("""
                    SELECT
                        qc.*,
                        m.content as user_message_content,
                        c.user_id,
                        c.language
                    FROM qa_quality_checks qc
                    LEFT JOIN messages m ON m.id = qc.user_message_id
                    LEFT JOIN conversations c ON c.id = qc.conversation_id
                    WHERE qc.id = %s
                """, (check_id,))

                qa_check = cur.fetchone()

                if not qa_check:
                    raise HTTPException(
                        status_code=404,
                        detail=f"QA quality check {check_id} not found"
                    )

                logger.info(f"🧠 [COT_ANALYSIS] Found QA check: conversation_id={qa_check['conversation_id']}")

                # 2. Fetch the original documents/context used
                # We need to retrieve the documents that were used to generate the original response
                # This requires looking at the retrieval logs or reconstructing the search

                # For now, we'll use the question to search again (same as original)
                # In production, you might want to store retrieval_ids in qa_quality_checks
                question = qa_check['question']
                language = qa_check.get('language', 'fr')

                # 3. Reconstruct context documents
                # We'll fetch from messages table to get the context that was used
                cur.execute("""
                    SELECT metadata
                    FROM messages
                    WHERE id = %s
                """, (qa_check['assistant_message_id'],))

                assistant_msg = cur.fetchone()
                context_docs = []

                if assistant_msg and assistant_msg['metadata']:
                    metadata = assistant_msg['metadata']
                    # Check if retrieval data is stored in metadata
                    if isinstance(metadata, dict) and 'retrieved_docs' in metadata:
                        # Convert stored docs to Document objects
                        for doc_data in metadata['retrieved_docs']:
                            context_docs.append(Document(
                                content=doc_data.get('content', ''),
                                metadata=doc_data.get('metadata', {}),
                                score=doc_data.get('score', 0.0)
                            ))

                # If no docs in metadata, create placeholder
                if not context_docs:
                    logger.warning(f"🧠 [COT_ANALYSIS] No context docs found, using response as context")
                    context_docs = [Document(
                        content=f"Original Response: {qa_check['response']}",
                        metadata={"source": "original_response"},
                        score=1.0
                    )]

                logger.info(f"🧠 [COT_ANALYSIS] Reconstructed {len(context_docs)} context documents")

                # 4. Initialize OpenAI client and generator
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    raise HTTPException(
                        status_code=500,
                        detail="OPENAI_API_KEY not configured"
                    )

                openai_client = AsyncOpenAI(api_key=openai_api_key)
                generator = create_enhanced_generator(
                    openai_client=openai_client,
                    cache_manager=None,  # Disable cache for CoT analysis
                    language=language
                )

                # 5. Call Claude Extended Thinking
                logger.info(f"🧠 [COT_ANALYSIS] Calling Claude Extended Thinking...")

                cot_result = await generator.generate_response_with_cot(
                    query=question,
                    context_docs=context_docs,
                    conversation_context="",  # Could fetch from conversation history if needed
                    language=language,
                    intent_result=None,
                    detected_domain=None
                )

                logger.info(f"🧠 [COT_ANALYSIS] CoT complete: {cot_result['thinking_tokens']} thinking tokens, ${cot_result['cost_usd']:.4f}")

                # 6. Store CoT results in database
                cur.execute("""
                    UPDATE qa_quality_checks
                    SET
                        cot_thinking = %s,
                        cot_analyzed_at = NOW(),
                        cot_analyzed_by = %s,
                        cot_token_count = %s,
                        cot_cost_usd = %s
                    WHERE id = %s
                """, (
                    cot_result['thinking'],
                    admin_email,
                    cot_result['thinking_tokens'],
                    cot_result['cost_usd'],
                    check_id
                ))
                conn.commit()

                logger.info(f"🧠 [COT_ANALYSIS] CoT results saved to database")

                # 7. Return results
                return {
                    "check_id": check_id,
                    "response": cot_result['response'],
                    "thinking": cot_result['thinking'],
                    "thinking_tokens": cot_result['thinking_tokens'],
                    "input_tokens": cot_result['input_tokens'],
                    "output_tokens": cot_result['output_tokens'],
                    "cost_usd": cot_result['cost_usd'],
                    "analyzed_at": datetime.now().isoformat(),
                    "analyzed_by": admin_email,
                    "original_question": question,
                    "original_response": qa_check['response']
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🧠 [COT_ANALYSIS] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"CoT analysis failed: {str(e)}"
        )


logger.info("qa_quality.py loaded")
