﻿from pydantic import BaseModel, Field
from typing import Optional

class ExpertQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User question")
    model: Optional[str] = Field("gpt-4o", description="AI model to use")
    language: Optional[str] = Field("fr", description="Response language")

class FeedbackRequest(BaseModel):
    query: str = Field(..., description="Original query")
    response: str = Field(..., description="AI response")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comment: Optional[str] = Field(None, description="Optional feedback comment")
