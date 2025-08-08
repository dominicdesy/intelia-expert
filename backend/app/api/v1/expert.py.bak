from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from pydantic import BaseModel
import uuid
from app.api.v1.pipeline.dialogue_manager import DialogueManager

router = APIRouter(prefix="", tags=["expert"])

dlg = DialogueManager()

class AskRequest(BaseModel):
    question: str

class ClarificationResponse(BaseModel):
    type: str
    questions: List[str]

class AnswerResponse(BaseModel):
    type: str
    response: str

# Generic response model for Swagger
ResponseModel = Dict[str, Any]

def get_session_id(request: Request) -> str:
    """
    Retrieves or initializes a session ID from the request headers.
    """
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        session_id = f"session_{uuid.uuid4().hex[:12]}"  # ← MODIFIÉ
    return session_id

@router.post("/ask", response_model=ResponseModel)
async def ask(
    payload: AskRequest = Body(...),
    session_id: str = Depends(get_session_id)
) -> ResponseModel:
    """
    Handle user questions via the DialogueManager pipeline.
    Returns either clarification questions or a final answer.
    """
    result = dlg.handle(session_id, payload.question)
    resp_type = result.get("type")

    if resp_type == "clarification":
        return ClarificationResponse(
            type="clarification",
            questions=result.get("questions", [])
        ).dict()

    if resp_type == "answer":
        return AnswerResponse(
            type="answer",
            response=result.get("response", "")
        ).dict()

    raise HTTPException(status_code=500, detail="Unexpected response type")
