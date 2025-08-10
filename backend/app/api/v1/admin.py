# -*- coding: utf-8 -*-
from fastapi import APIRouter
from typing import Any, Dict

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/kpis")
def kpis() -> Dict[str, Any]:
    return {"status": "ok", "version": "ready-patch"}
