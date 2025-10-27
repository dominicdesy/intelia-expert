"""
OpenAI-compatible API Schemas
Based on OpenAI API specification for chat completions
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime


# ============================================
# REQUEST MODELS
# ============================================

class ChatMessage(BaseModel):
    """Single message in a conversation"""
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""
    model: str = Field(default="intelia-llama-3.1-8b-aviculture")
    messages: List[ChatMessage]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=1, le=8000)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    stream: bool = False
    stop: Optional[List[str]] = None
    n: int = Field(default=1, ge=1, le=1)  # Only 1 for now


# ============================================
# RESPONSE MODELS
# ============================================

class ChatCompletionMessage(BaseModel):
    """Message in completion response"""
    role: Literal["assistant"]
    content: str


class ChatCompletionChoice(BaseModel):
    """Single choice in completion response"""
    index: int
    message: ChatCompletionMessage
    finish_reason: Literal["stop", "length", "content_filter"] = "stop"


class UsageInfo(BaseModel):
    """Token usage information"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response"""
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo


# ============================================
# MODELS LIST
# ============================================

class ModelInfo(BaseModel):
    """Information about a model"""
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "intelia"


class ModelsResponse(BaseModel):
    """List of available models"""
    object: Literal["list"] = "list"
    data: List[ModelInfo]


# ============================================
# HEALTH & STATUS
# ============================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: Literal["healthy", "unhealthy"]
    service: str
    version: str
    provider: str
    model_loaded: bool
    timestamp: str

    model_config = {"protected_namespaces": ()}


# ============================================
# ERROR RESPONSE
# ============================================

class ErrorDetail(BaseModel):
    """Error details"""
    message: str
    type: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: ErrorDetail
