from fastapi import APIRouter, Depends, Request, HTTPException
from app.api.v1.pipeline.dialogue_manager import DialogueManager

router = APIRouter()

dlg = DialogueManager()


def get_session_id(request: Request) -> str:
    """
    Retrieves or initializes a session ID from the request headers.
    """
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        # Fallback to client IP or a default
        session_id = request.client.host
    return session_id

@router.post("/ask")
async def ask(request: Request, question: str, session_id: str = Depends(get_session_id)):
    """
    Endpoint to handle user questions via the DialogueManager pipeline.
    Returns either clarification questions or a final answer.
    """
    # Delegate to DialogueManager
    result = dlg.handle(session_id, question)

    if result.get("type") == "clarification":
        return {"type": "clarification", "questions": result["questions"]}
    elif result.get("type") == "answer":
        return {"type": "answer", "response": result["response"]}
    else:
        raise HTTPException(status_code=500, detail="Unexpected response type")
