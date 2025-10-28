"""
Generation API Schemas
Schemas for intelligent LLM generation endpoints
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


# ============================================
# GENERATE REQUEST/RESPONSE
# ============================================

class GenerateRequest(BaseModel):
    """Request for intelligent LLM generation with domain configuration"""
    query: str = Field(..., description="User query")
    messages: Optional[List[Dict[str, str]]] = Field(None, description="Pre-formatted messages (overrides query)")
    domain: str = Field(default="aviculture", description="Domain for configuration")
    language: str = Field(default="en", description="Response language")

    # Optional context
    entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities")
    query_type: Optional[str] = Field(None, description="Query type (standard, comparative, etc.)")
    context_docs: Optional[List[Dict]] = Field(None, description="Context documents")
    user_category: Optional[str] = Field(None, description="User expertise level (health_veterinary, farm_operations, etc.)")

    # Generation parameters (optional, will use domain defaults)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, le=8000, description="Max tokens (auto-calculated if not provided)")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling")

    # Processing options
    post_process: bool = Field(default=True, description="Apply post-processing")
    add_disclaimer: bool = Field(default=True, description="Add veterinary disclaimer if applicable")


class GenerateResponse(BaseModel):
    """Response from intelligent generation"""
    generated_text: str = Field(..., description="Generated response")
    provider: str = Field(..., description="Provider used (intelia_llama, gpt4o, etc.)")
    model: str = Field(..., description="Model used")

    # Token usage
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    # Metadata
    complexity: Optional[str] = Field(None, description="Query complexity level")
    calculated_max_tokens: Optional[int] = Field(None, description="Auto-calculated max_tokens")
    post_processed: bool = Field(default=False, description="Whether post-processing was applied")
    disclaimer_added: bool = Field(default=False, description="Whether disclaimer was added")
    cached: bool = Field(default=False, description="Whether response was served from cache")


# ============================================
# ROUTE REQUEST/RESPONSE
# ============================================

class RouteRequest(BaseModel):
    """Request to determine optimal LLM provider"""
    query: str = Field(..., description="User query")
    domain: str = Field(default="aviculture", description="Domain")
    entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities")
    intent_result: Optional[Dict[str, Any]] = Field(None, description="Intent classification result")


class RouteResponse(BaseModel):
    """Response with routing decision"""
    provider: str = Field(..., description="Selected provider")
    model: str = Field(..., description="Model to use")
    reason: str = Field(..., description="Routing reason")
    is_aviculture: bool = Field(..., description="Whether query is aviculture-related")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Routing confidence")


# ============================================
# CALCULATE TOKENS REQUEST/RESPONSE
# ============================================

class CalculateTokensRequest(BaseModel):
    """Request to calculate optimal max_tokens"""
    query: str = Field(..., description="User query")
    entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities")
    query_type: Optional[str] = Field(None, description="Query type")
    context_docs: Optional[List[Dict]] = Field(None, description="Context documents")
    domain: Optional[str] = Field(None, description="Domain")


class CalculateTokensResponse(BaseModel):
    """Response with token calculation"""
    max_tokens: int = Field(..., description="Calculated max_tokens")
    complexity: str = Field(..., description="Query complexity level")
    token_range: tuple[int, int] = Field(..., description="Token range for complexity")
    factors: Dict[str, Any] = Field(..., description="Complexity factors")


# ============================================
# POST-PROCESS REQUEST/RESPONSE
# ============================================

class PostProcessRequest(BaseModel):
    """Request to post-process LLM response"""
    response: str = Field(..., description="Raw LLM response")
    query: str = Field(default="", description="Original query")
    language: str = Field(default="en", description="Response language")
    domain: str = Field(default="aviculture", description="Domain")
    context_docs: Optional[List[Dict]] = Field(None, description="Context documents")
    user_category: Optional[str] = Field(None, description="User expertise level (health_veterinary, farm_operations, etc.)")
    add_disclaimer: bool = Field(default=True, description="Add disclaimer if applicable")


class PostProcessResponse(BaseModel):
    """Response with post-processed text"""
    processed_text: str = Field(..., description="Post-processed response")
    disclaimer_added: bool = Field(default=False, description="Whether disclaimer was added")
    is_veterinary: bool = Field(default=False, description="Whether query was veterinary-related")
