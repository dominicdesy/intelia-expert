"""
Headway Tracking API endpoints
Version: 1.0.0
Date: 2025-10-31
Description: API endpoints for tracking Headway articles viewed by users
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
import logging

from .auth import get_current_user
from app.core.database import get_pg_connection
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/headway", tags=["Headway"])


# ==================== MODELS ====================

class MarkAsViewedRequest(BaseModel):
    """Request to mark article as viewed"""
    article_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "article_id": "headway_article_123"
            }
        }


class ViewedArticlesResponse(BaseModel):
    """Response with list of viewed article IDs"""
    article_ids: List[str]
    count: int


# ==================== ENDPOINTS ====================

@router.get("/viewed", response_model=ViewedArticlesResponse)
async def get_viewed_articles(
    current_user: Dict = Depends(get_current_user)
) -> ViewedArticlesResponse:
    """
    Get list of article IDs viewed by current user

    Returns:
        List of article IDs that user has viewed
    """
    try:
        user_id = current_user.get("auth_user_id")

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT article_id
                    FROM user_headway_tracking
                    WHERE user_id = %s
                    ORDER BY viewed_at DESC
                    """,
                    (user_id,)
                )
                results = cur.fetchall()

                article_ids = [row["article_id"] for row in results]

                logger.info(f"Retrieved {len(article_ids)} viewed articles for user {user_id}")

                return ViewedArticlesResponse(
                    article_ids=article_ids,
                    count=len(article_ids)
                )

    except Exception as e:
        logger.error(f"Error retrieving viewed articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-viewed")
async def mark_article_as_viewed(
    request: MarkAsViewedRequest,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Mark an article as viewed by current user

    Args:
        request: Article ID to mark as viewed

    Returns:
        Success response
    """
    try:
        user_id = current_user.get("auth_user_id")

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Insert or update (upsert)
                cur.execute(
                    """
                    INSERT INTO user_headway_tracking (user_id, article_id, viewed_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (user_id, article_id)
                    DO UPDATE SET viewed_at = NOW()
                    RETURNING id, article_id, viewed_at
                    """,
                    (user_id, request.article_id)
                )
                result = cur.fetchone()
                conn.commit()

                logger.info(f"Marked article {request.article_id} as viewed for user {user_id}")

                return {
                    "success": True,
                    "article_id": result["article_id"],
                    "viewed_at": result["viewed_at"].isoformat() if result["viewed_at"] else None
                }

    except Exception as e:
        logger.error(f"Error marking article as viewed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-multiple-viewed")
async def mark_multiple_articles_as_viewed(
    article_ids: List[str],
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Mark multiple articles as viewed by current user

    Args:
        article_ids: List of article IDs to mark as viewed

    Returns:
        Success response with count
    """
    try:
        user_id = current_user.get("auth_user_id")

        if not article_ids:
            return {"success": True, "count": 0}

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Batch insert
                values = [(user_id, article_id) for article_id in article_ids]

                cur.executemany(
                    """
                    INSERT INTO user_headway_tracking (user_id, article_id, viewed_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (user_id, article_id)
                    DO UPDATE SET viewed_at = NOW()
                    """,
                    values
                )
                conn.commit()

                logger.info(f"Marked {len(article_ids)} articles as viewed for user {user_id}")

                return {
                    "success": True,
                    "count": len(article_ids)
                }

    except Exception as e:
        logger.error(f"Error marking multiple articles as viewed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
