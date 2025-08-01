"""
app/api/v1/expert_models.py - MODÈLES PYDANTIC POUR EXPERT SYSTEM

Tous les modèles de données pour le système expert
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

# =============================================================================
# MODÈLES DE REQUÊTE
# =============================================================================

class EnhancedQuestionRequest(BaseModel):
    """Request model amélioré avec support état conversationnel"""
    text: str = Field(..., min_length=1, max_length=5000)
    language: Optional[str] = Field("fr", description="Response language")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode")
    
    # Contexte conversationnel
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    user_id: Optional[str] = Field(None, description="User ID")
    
    # Nouveaux champs pour clarification
    is_clarification_response: Optional[bool] = Field(False, description="Is this a response to clarification?")
    original_question: Optional[str] = Field(None, description="Original question if this is clarification response")
    clarification_context: Optional[Dict[str, Any]] = Field(None, description="Clarification context")
    force_reprocess: Optional[bool] = Field(False, description="Force reprocessing even if no clarification needed")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        extra="ignore"
    )

class FeedbackRequest(BaseModel):
    """Feedback model standard"""
    rating: str = Field(..., description="Rating: positive, negative, neutral")
    comment: Optional[str] = Field(None, description="Optional comment")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore"
    )

    def model_post_init(self, __context) -> None:
        if self.rating not in ['positive', 'negative', 'neutral']:
            self.rating = 'neutral'

# =============================================================================
# MODÈLES DE RÉPONSE
# =============================================================================

class EnhancedExpertResponse(BaseModel):
    """Response model amélioré avec état conversationnel"""
    question: str
    response: str
    conversation_id: str
    rag_used: bool
    rag_score: Optional[float] = None
    timestamp: str
    language: str
    response_time_ms: int
    mode: str
    user: Optional[str] = None
    logged: bool = False
    validation_passed: Optional[bool] = None
    validation_confidence: Optional[float] = None
    
    # Nouveaux champs pour fonctionnalités améliorées
    clarification_result: Optional[Dict[str, Any]] = None
    reprocessed_after_clarification: Optional[bool] = None
    conversation_state: Optional[str] = None
    extracted_entities: Optional[Dict[str, Any]] = None
    confidence_overall: Optional[float] = None
    
    # Métriques avancées
    processing_steps: Optional[List[str]] = None
    ai_enhancements_used: Optional[List[str]] = None

# =============================================================================
# MODÈLES UTILITAIRES
# =============================================================================

class ValidationResult(BaseModel):
    """Résultat de validation"""
    is_valid: bool
    rejection_message: str = ""
    confidence: float = 0.0

class ProcessingContext(BaseModel):
    """Contexte de traitement"""
    user_id: str
    conversation_id: str
    request_ip: str
    processing_steps: List[str] = Field(default_factory=list)
    ai_enhancements_used: List[str] = Field(default_factory=list)

# =============================================================================
# MODÈLES DE STATS
# =============================================================================

class SystemStats(BaseModel):
    """Statistiques système"""
    system_available: bool
    timestamp: str
    components: Dict[str, bool]
    enhanced_capabilities: List[str]
    enhanced_endpoints: List[str]

class TestResult(BaseModel):
    """Résultat de test"""
    question: str
    conversation_id: str
    user_id: str
    timestamp: str
    components_tested: Dict[str, Any]
    test_successful: bool
    errors: List[str]
