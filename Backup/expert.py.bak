# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict
from .pipeline.dialogue_manager import handle

router = APIRouter(prefix="", tags=["expert"])

class AskPayload(BaseModel):
    session_id: Optional[str] = "default"
    question: str
    lang: Optional[str] = "fr"

@router.post("/ask")
def ask(payload: AskPayload) -> Dict[str, Any]:
    try:
        res = handle(payload.session_id, payload.question, payload.lang or "fr")
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
