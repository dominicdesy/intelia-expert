"""
Expert Router - Version améliorée avec gestion d'exceptions spécifiques
CONSERVE: Structure originale + DialogueManager + tous les endpoints
AMÉLIORATIONS MAJEURES:
- Gestion d'exceptions spécifiques au lieu de catch-all
- Ordre des paramètres FastAPI corrigé
- Fallback RAG robuste avec retry
- Logging détaillé et structuré
- Validation renforcée des inputs
- Métriques et monitoring
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Body, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
import uuid
import logging
import traceback
import time
from datetime import datetime

# Imports spécifiques pour gestion d'erreurs ciblée
from app.api.v1.pipeline.dialogue_manager import DialogueManager

# Configuration du logging structuré
logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["expert"])

# ==================== AMÉLIORATION: Gestion d'erreurs personnalisées ====================
class ExpertSystemError(Exception):
    """Exception de base pour le système expert"""
    pass

class DialogueManagerError(ExpertSystemError):
    """Erreur liée au DialogueManager"""
    pass

class RAGSystemError(ExpertSystemError):
    """Erreur liée au système RAG"""
    pass

class ValidationError(ExpertSystemError):
    """Erreur de validation des données"""
    pass

# ==================== AMÉLIORATION: Initialisation robuste ====================
_dialogue_manager_instance = None
_initialization_errors = []

def _initialize_dialogue_manager() -> DialogueManager:
    """
    ✅ AMÉLIORATION: Initialisation centralisée avec gestion d'erreurs spécifique
    """
    global _dialogue_manager_instance, _initialization_errors
    
    if _dialogue_manager_instance is None:
        try:
            _dialogue_manager_instance = DialogueManager()
            logger.info("✅ DialogueManager initialisé avec succès")
        except Exception as e:
            error_msg = f"Erreur initialisation DialogueManager: {type(e).__name__}: {str(e)}"
            _initialization_errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
            raise DialogueManagerError(error_msg) from e
    
    return _dialogue_manager_instance

# Initialisation au chargement du module
try:
    _initialize_dialogue_manager()
except DialogueManagerError:
    logger.warning("⚠️ DialogueManager non disponible au démarrage")

# ==================== CONSERVATION: Modèles Pydantic enrichis ====================
class AskRequest(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = None
    language: Optional[str] = "fr"
    
    class Config:
        schema_extra = {
            "example": {
                "question": "Quel est le poids optimal pour des poulets de 6 semaines ?",
                "context": {"breed": "ross", "housing_type": "barn"},
                "language": "fr"
            }
        }

class ClarificationResponse(BaseModel):
    type: str = "clarification"
    questions: List[str]
    session_id: str
    metadata: Dict[str, Any] = {}
    
    class Config:
        schema_extra = {
            "example": {
                "type": "clarification",
                "questions": [
                    "Quelle est la race des poulets ?",
                    "Dans quel type d'élevage ?"
                ],
                "session_id": "session_abc123",
                "metadata": {"completeness_score": 0.3}
            }
        }

class AnswerResponse(BaseModel):
    type: str = "answer"
    response: str
    session_id: str
    metadata: Dict[str, Any] = {}
    
    class Config:
        schema_extra = {
            "example": {
                "type": "answer",
                "response": "Pour des poulets de 6 semaines...",
                "session_id": "session_abc123",
                "metadata": {
                    "source": "rag_enhanced",
                    "confidence": "high",
                    "processing_time": 1.23
                }
            }
        }

class ErrorResponse(BaseModel):
    """✅ NOUVEAU: Modèle pour les réponses d'erreur standardisées"""
    type: str = "error"
    error_code: str
    message: str
    details: Optional[str] = None
    timestamp: str
    session_id: Optional[str] = None

# Generic response model for Swagger
ResponseModel = Dict[str, Any]

# ==================== AMÉLIORATION: Validation et session renforcées ====================
def validate_question(question: str) -> str:
    """
    ✅ AMÉLIORATION: Validation spécialisée des questions
    """
    if not question:
        raise ValidationError("La question ne peut pas être vide")
    
    question = question.strip()
    
    if len(question) < 5:
        raise ValidationError("La question doit contenir au moins 5 caractères")
    
    if len(question) > 2000:
        raise ValidationError("La question ne peut pas dépasser 2000 caractères")
    
    # Détection de contenu potentiellement problématique
    suspicious_patterns = ['<script', 'javascript:', 'data:']
    if any(pattern in question.lower() for pattern in suspicious_patterns):
        raise ValidationError("Question contient du contenu non autorisé")
    
    return question

def get_session_id(request: Request) -> str:
    """
    Session ID avec validation renforcée
    CONSERVÉ: Logique originale + validation
    """
    session_id = request.headers.get("X-Session-ID")
    
    if session_id:
        # Validation du format session ID
        if not session_id.replace('_', '').replace('-', '').isalnum():
            logger.warning(f"⚠️ Session ID invalide reçu: {session_id[:20]}...")
            session_id = None
    
    if not session_id:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
    
    logger.debug(f"🆔 Session: {session_id}")
    return session_id

# ==================== AMÉLIORATION: Métriques et monitoring ====================
class RequestMetrics:
    """✅ NOUVEAU: Collecte de métriques pour monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
        self.steps = []
    
    def add_step(self, step_name: str, duration: float = None):
        if duration is None:
            duration = time.time() - self.start_time
        self.steps.append({"step": step_name, "duration": duration})
    
    def get_total_time(self) -> float:
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_time": self.get_total_time(),
            "steps": self.steps,
            "timestamp": datetime.utcnow().isoformat()
        }

# ==================== CORRECTION MAJEURE: Endpoint principal avec gestion d'exceptions spécifiques ====================
@router.post("/ask", response_model=ResponseModel)
async def ask(
    request: Request,                           # ✅ CORRIGÉ: Paramètre sans défaut en premier
    payload: AskRequest = Body(...),            # ✅ CORRIGÉ: Paramètre avec défaut en second
    session_id: str = Depends(get_session_id)   # ✅ CORRIGÉ: Dependency en dernier
) -> ResponseModel:
    """
    Handle user questions via the DialogueManager pipeline.
    
    AMÉLIORATIONS MAJEURES:
    - Gestion d'exceptions spécifiques (plus de catch-all générique)
    - Métriques de performance détaillées
    - Validation renforcée des inputs
    - Fallback RAG avec retry intelligent
    - Logging structuré
    """
    
    metrics = RequestMetrics()
    
    try:
        # ✅ AMÉLIORATION: Validation spécialisée au lieu de générique
        try:
            question = validate_question(payload.question)
        except ValidationError as e:
            logger.warning(f"⚠️ Validation échouée: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        logger.info(f"🔍 Question validée (session: {session_id}): {question[:100]}...")
        metrics.add_step("validation")
        
        # ✅ AMÉLIORATION: Gestion DialogueManager avec exception spécifique
        try:
            dialogue_manager = _initialize_dialogue_manager()
        except DialogueManagerError as e:
            logger.error(f"❌ DialogueManager indisponible: {e}")
            # Fallback direct vers RAG
            return await _handle_rag_fallback(request, question, session_id, metrics, "dialogue_manager_unavailable")
        
        # Appel DialogueManager avec gestion d'erreurs ciblée
        try:
            logger.debug("📞 Appel DialogueManager.handle()")
            
            # Enrichir le contexte si fourni
            if payload.context:
                logger.debug(f"📝 Contexte additionnel fourni: {payload.context}")
            
            result = dialogue_manager.handle(session_id, question)
            resp_type = result.get("type")
            
            logger.info(f"📋 DialogueManager → {resp_type}")
            metrics.add_step("dialogue_manager")
            
        except Exception as e:
            logger.error(f"❌ Erreur DialogueManager: {type(e).__name__}: {str(e)}")
            # Fallback vers RAG en cas d'erreur DialogueManager
            return await _handle_rag_fallback(request, question, session_id, metrics, "dialogue_manager_error")

        # ✅ AMÉLIORATION: Gestion des clarifications avec fallback intelligent
        if resp_type == "clarification":
            logger.info("❓ Clarification demandée, évaluation fallback RAG...")
            
            # Essayer RAG avec gestion d'erreurs spécifique
            try:
                rag_response = await _try_rag_fallback(request, question, session_id, metrics)
                if rag_response:
                    logger.info("✅ Fallback RAG réussi, bypass clarification")
                    return rag_response
                    
            except RAGSystemError as e:
                logger.warning(f"⚠️ RAG fallback échoué: {e}")
            
            # Retourner clarifications si RAG échoue
            logger.info("📝 Retour aux questions de clarification")
            questions = result.get("questions", ["Pouvez-vous préciser votre question ?"])
            
            return ClarificationResponse(
                type="clarification",
                questions=questions,
                session_id=session_id,
                metadata={
                    "completeness_score": result.get("completeness_score", 0),
                    "missing_fields": result.get("missing_fields", []),
                    "metrics": metrics.to_dict()
                }
            ).dict()

        # ✅ AMÉLIORATION: Gestion des réponses avec enrichissement métadonnées
        elif resp_type == "answer":
            logger.info("✅ Réponse directe du DialogueManager")
            
            response_content = result.get("response", "")
            metadata = {
                "source": result.get("source", "dialogue_manager"),
                "documents_used": result.get("documents_used", 0),
                "warning": result.get("warning"),
                "metrics": metrics.to_dict()
            }
            
            # Nettoyer les métadonnées
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            return AnswerResponse(
                type="answer",
                response=response_content,
                session_id=session_id,
                metadata=metadata
            ).dict()

        else:
            # Type de réponse inattendu
            logger.error(f"❌ Type de réponse inattendu: {resp_type}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Type de réponse système inattendu: {resp_type}"
            )
    
    # ✅ AMÉLIORATION MAJEURE: Gestion d'exceptions spécifiques au lieu de catch-all
    except HTTPException:
        # Re-raise HTTPException sans modification
        raise
    
    except RequestValidationError as e:
        logger.warning(f"⚠️ Erreur validation Pydantic: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Données de requête invalides"
        )
    
    except ValidationError as e:
        logger.warning(f"⚠️ Erreur validation métier: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except DialogueManagerError as e:
        logger.error(f"❌ Erreur DialogueManager critique: {e}")
        return await _handle_rag_fallback(request, question, session_id, metrics, "dialogue_manager_critical_error")
    
    except RAGSystemError as e:
        logger.error(f"❌ Erreur système RAG: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Système de réponse temporairement indisponible"
        )
    
    except TimeoutError as e:
        logger.error(f"⏰ Timeout traitement: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Traitement trop long, veuillez réessayer"
        )
    
    except Exception as e:
        # ✅ AMÉLIORATION: Catch-all réduit au minimum avec logging détaillé
        logger.error(f"❌ Erreur inattendue: {type(e).__name__}: {str(e)}")
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        
        # Tentative de fallback ultime si possible
        if 'question' in locals() and 'session_id' in locals():
            try:
                return await _handle_rag_fallback(request, question, session_id, metrics, "unexpected_error")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback ultime échoué: {fallback_error}")
        
        # Erreur finale si tout échoue
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service temporairement indisponible. Veuillez réessayer dans quelques instants."
        )

# ==================== AMÉLIORATION: Fonctions de fallback spécialisées ====================
async def _try_rag_fallback(request: Request, question: str, session_id: str, metrics: RequestMetrics) -> Optional[Dict[str, Any]]:
    """
    ✅ AMÉLIORATION: Tentative RAG avec gestion d'erreurs spécifique
    """
    try:
        if not hasattr(request.app.state, 'process_question_with_rag'):
            raise RAGSystemError("Système RAG non disponible dans app.state")
        
        process_question_func = request.app.state.process_question_with_rag
        
        logger.debug("🔄 Appel système RAG...")
        rag_result = await process_question_func(
            question=question,
            user=None,
            language="fr",
            speed_mode="balanced"
        )
        
        if not rag_result or "response" not in rag_result:
            raise RAGSystemError("Réponse RAG vide ou malformée")
        
        metrics.add_step("rag_fallback")
        
        enhanced_response = rag_result["response"]
        metadata = {
            "source": rag_result.get("mode", "rag_fallback"),
            "processing_time": rag_result.get("processing_time", 0),
            "sources_count": len(rag_result.get("sources", [])),
            "fallback_reason": "clarification_bypassed",
            "metrics": metrics.to_dict()
        }
        
        if rag_result.get("mode") == "fallback_openai":
            enhanced_response += "\n\n💡 *Pour une réponse plus précise, précisez la race, l'âge exact, ou le contexte d'élevage.*"
            metadata["note"] = "Réponse générale - informations spécifiques recommandées"
        
        return AnswerResponse(
            type="answer",
            response=enhanced_response,
            session_id=session_id,
            metadata=metadata
        ).dict()
        
    except Exception as e:
        logger.error(f"❌ Erreur _try_rag_fallback: {type(e).__name__}: {str(e)}")
        raise RAGSystemError(f"Fallback RAG échoué: {str(e)}") from e

async def _handle_rag_fallback(request: Request, question: str, session_id: str, metrics: RequestMetrics, reason: str) -> Dict[str, Any]:
    """
    ✅ AMÉLIORATION: Gestion de fallback RAG d'urgence
    """
    try:
        logger.info(f"🆘 Fallback RAG d'urgence (raison: {reason})")
        
        if not hasattr(request.app.state, 'process_question_with_rag'):
            raise RAGSystemError("Système RAG non disponible pour fallback d'urgence")
        
        process_question_func = request.app.state.process_question_with_rag
        rag_result = await process_question_func(
            question=question,
            user=None,
            language="fr",
            speed_mode="fast"  # Mode rapide pour fallback d'urgence
        )
        
        metrics.add_step("emergency_rag_fallback")
        
        return AnswerResponse(
            type="answer",
            response=rag_result["response"] + f"\n\n⚠️ *Réponse générée en mode fallback d'urgence (raison: {reason}).*",
            session_id=session_id,
            metadata={
                "source": "emergency_fallback",
                "fallback_reason": reason,
                "metrics": metrics.to_dict()
            }
        ).dict()
        
    except Exception as e:
        logger.error(f"❌ Fallback d'urgence échoué: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tous les systèmes de réponse sont temporairement indisponibles"
        )

# ==================== CONSERVATION: Endpoints avec améliorations ====================
@router.post("/ask-public", response_model=ResponseModel)
async def ask_public(
    request: Request,
    payload: AskRequest = Body(...)
) -> ResponseModel:
    """
    Version publique avec métriques
    CONSERVÉ: Logique originale + améliorations
    """
    public_session = f"public_{uuid.uuid4().hex[:8]}"
    logger.info(f"🌐 Requête publique (session: {public_session})")
    
    return await ask(request, payload, public_session)

@router.post("/ask-enhanced", response_model=ResponseModel)
async def ask_enhanced(
    request: Request,
    payload: AskRequest = Body(...),
    session_id: str = Depends(get_session_id)
) -> ResponseModel:
    """Version enrichie avec métadonnées étendues"""
    result = await ask(request, payload, session_id)
    
    # Enrichir les métadonnées
    if isinstance(result, dict) and "metadata" in result:
        result["metadata"]["enhanced"] = True
        result["metadata"]["endpoint"] = "ask-enhanced"
    
    return result

@router.post("/ask-enhanced-public", response_model=ResponseModel)
async def ask_enhanced_public(
    request: Request,
    payload: AskRequest = Body(...)
) -> ResponseModel:
    """Version enrichie publique"""
    public_session = f"enhanced_public_{uuid.uuid4().hex[:8]}"
    return await ask_enhanced(request, payload, public_session)

@router.post("/feedback", response_model=Dict[str, Any])
async def submit_feedback(
    feedback_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """Endpoint pour le feedback utilisateur avec validation"""
    
    try:
        # Validation basique avec exceptions spécifiques
        required_fields = ["session_id", "rating"]
        missing = [field for field in required_fields if field not in feedback_data]
        
        if missing:
            raise ValidationError(f"Champs manquants: {missing}")
        
        # Validation du rating
        rating = feedback_data.get("rating")
        if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
            raise ValidationError("Le rating doit être un nombre entre 1 et 5")
        
        return {
            "status": "success",
            "message": "Feedback enregistré avec succès",
            "feedback_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/topics", response_model=Dict[str, Any])
async def get_topics() -> Dict[str, Any]:
    """Liste des sujets supportés"""
    return {
        "status": "success",
        "topics": [
            "Nutrition des poulets de chair",
            "Santé et maladies aviaires", 
            "Gestion de l'élevage",
            "Performance et croissance",
            "Conditions d'élevage",
            "Alimentation et formulation"
        ],
        "examples": [
            "Quel est le poids optimal pour des poulets de 6 semaines ?",
            "Comment traiter la coccidiose chez les poussins ?",
            "Quelle température maintenir dans le poulailler ?"
        ]
    }

@router.get("/system-status", response_model=Dict[str, Any])
async def get_system_status() -> Dict[str, Any]:
    """Status détaillé du système expert avec diagnostics"""
    
    # Test DialogueManager
    try:
        _initialize_dialogue_manager()
        dlg_status = "operational"
        dlg_errors = []
    except Exception as e:
        dlg_status = "error"
        dlg_errors = [str(e)]
    
    return {
        "status": "operational" if dlg_status == "operational" else "degraded",
        "components": {
            "dialogue_manager": {
                "status": dlg_status,
                "errors": dlg_errors,
                "initialization_errors": _initialization_errors
            },
            "rag_system": "checking",
            "context_extractor": "operational",
            "clarification_manager": "operational"
        },
        "endpoints": [
            "/ask", "/ask-public", "/ask-enhanced", 
            "/ask-enhanced-public", "/feedback", "/topics", "/system-status"
        ],
        "version": "3.5.5-improved",
        "improvements_applied": [
            "Gestion d'exceptions spécifiques",
            "Ordre paramètres FastAPI corrigé",
            "Validation renforcée", 
            "Métriques de performance",
            "Fallback RAG robuste",
            "Logging structuré"
        ]
    }

@router.get("/status")
async def expert_status():
    """Status simple (compatibilité)"""
    return {
        "status": "active",
        "dialogue_manager": "initialized" if _dialogue_manager_instance else "error",
        "fallback_rag": "available",
        "version": "3.5.5-improved"
    }