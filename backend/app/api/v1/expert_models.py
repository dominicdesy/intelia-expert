"""
app/api/v1/expert_models.py - MODÈLES PYDANTIC POUR EXPERT SYSTEM

Tous les modèles de données pour le système expert
VERSION CORRIGÉE v3.9.7: Ajout champs traçage décisions IA
🔧 CORRECTION v3.9.7: Ajout ai_classification_used, ai_decision, ai_confidence, ai_reasoning, response_generation_method
🔧 CORRECTION v3.9.6: Ajout clarification_details, enhancement_info, conversation_context, pipeline_version, pipeline_improvements
🧨 CORRECTION v3.6.1: Ajout du champ clarification_processing
🚀 NOUVEAU v3.7.0: Support response_versions pour concision backend
🆕 NOUVEAU v3.9.0: Support mode sémantique dynamique avec DynamicClarification
🔧 CORRECTION v3.9.1: Validation améliorée + valeurs par défaut + documentation
🔧 CORRECTION v3.9.2: Ajout du champ contextualization_info manquant + corrections diverses
🔧 CORRECTION v3.9.3: Ajout de ClarificationResult avec missing_entities pour éviter l'erreur
🔧 CORRECTION v3.9.4: Ajout enriched_question dans EnhancedExpertResponse et weight dans IntelligentEntities
🔧 CORRECTION v3.9.5: Ajout mortality dans IntelligentEntities + champs supplémentaires demandés
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from enum import Enum
import logging

# =============================================================================
# NOUVEAUX ENUMS POUR LES AMÉLIORATIONS + CONCISION + SEMANTIC DYNAMIC
# =============================================================================

class ResponseFormat(str, Enum):
    """Formats de réponse attendus pour structurer les réponses de l'IA"""
    TEXT = "text"
    TABLE = "table"  
    SUMMARY = "summary"
    PLAN = "plan"
    COMPARISON = "comparison"
    NUMERICAL_DATA = "numerical_data"

class ConfidenceLevel(str, Enum):
    """Niveaux de confiance pour les réponses et analyses"""
    VERY_LOW = "very_low"      # < 0.2
    LOW = "low"                # 0.2 - 0.4
    MEDIUM = "medium"          # 0.4 - 0.7
    HIGH = "high"              # 0.7 - 0.9
    VERY_HIGH = "very_high"    # > 0.9

class QuestionClarity(str, Enum):
    """Niveaux de clarté des questions pour la détection de flou"""
    CLEAR = "clear"                        # Question précise et complète
    PARTIALLY_CLEAR = "partially_clear"    # Quelques éléments manquants
    UNCLEAR = "unclear"                    # Plusieurs éléments flous
    VERY_UNCLEAR = "very_unclear"          # Question très imprécise

class ConcisionLevel(str, Enum):
    """Niveaux de concision pour les réponses optimisées"""
    ULTRA_CONCISE = "ultra_concise"  # Réponse minimale (ex: "350-400g")
    CONCISE = "concise"              # Réponse courte (1-2 phrases)
    STANDARD = "standard"            # Réponse équilibrée 
    DETAILED = "detailed"            # Réponse complète et détaillée

# =============================================================================
# 🧠 NOUVEAUX ENUMS POUR TRAÇAGE DÉCISIONS IA - v3.9.7
# =============================================================================

class AiDecisionType(str, Enum):
    """Types de décisions prises par l'IA pour traçabilité"""
    CLASSIFICATION = "classification"           # Classification de la question
    RAG_SELECTION = "rag_selection"            # Sélection des documents RAG
    RESPONSE_GENERATION = "response_generation" # Génération de la réponse
    CLARIFICATION = "clarification"            # Demande de clarification
    FALLBACK = "fallback"                      # Utilisation du fallback
    ENHANCEMENT = "enhancement"                # Amélioration de la question

class ResponseGenerationMethod(str, Enum):
    """Méthodes de génération de réponse pour traçabilité"""
    RAG_DIRECT = "rag_direct"                  # RAG direct
    RAG_ENHANCED = "rag_enhanced"              # RAG avec amélioration
    GPT_GENERATION = "gpt_generation"          # Génération GPT pure
    HYBRID = "hybrid"                          # Méthode hybride
    TEMPLATE_BASED = "template_based"          # Basé sur template
    FALLBACK = "fallback"                      # Méthode de fallback

# =============================================================================
# MODÈLES POUR LES AMÉLIORATIONS (CONSERVÉS AVEC CORRECTIONS)
# =============================================================================

class ResponsePreferences(BaseModel):
    """Préférences de formatage de réponse avec valeurs par défaut optimisées"""
    include_ranges: bool = Field(default=True, description="Inclure les fourchettes de valeurs")
    show_male_female_split: bool = Field(default=False, description="Différencier mâles/femelles")
    include_confidence_scores: bool = Field(default=False, description="Afficher les scores de confiance")
    preferred_units: str = Field(default="metric", description="Unités préférées: metric/imperial")
    detail_level: str = Field(default="standard", description="Niveau de détail: minimal/standard/detailed")

    @field_validator('preferred_units')
    @classmethod
    def validate_units(cls, v):
        if v not in ['metric', 'imperial']:
            raise ValueError('preferred_units must be "metric" or "imperial"')
        return v

    @field_validator('detail_level')
    @classmethod
    def validate_detail_level(cls, v):
        if v not in ['minimal', 'standard', 'detailed']:
            raise ValueError('detail_level must be "minimal", "standard", or "detailed"')
        return v

    model_config = ConfigDict(extra="ignore")

class ConcisionPreferences(BaseModel):
    """Préférences de concision pour les réponses avec validation améliorée"""
    level: ConcisionLevel = Field(default=ConcisionLevel.CONCISE, description="Niveau de concision souhaité")
    generate_all_versions: bool = Field(default=True, description="Générer toutes les versions de concision")
    auto_detect_optimal: bool = Field(default=True, description="Détecter automatiquement le niveau optimal")
    cache_versions: bool = Field(default=True, description="Mettre en cache les versions générées")

    model_config = ConfigDict(extra="ignore")

class SemanticDynamicPreferences(BaseModel):
    """Préférences pour le mode sémantique dynamique avec validation"""
    enabled: bool = Field(default=False, description="Activer le mode sémantique dynamique")
    max_questions: int = Field(default=4, ge=1, le=10, description="Nombre maximum de questions à générer")
    fallback_enabled: bool = Field(default=True, description="Utiliser questions de fallback si génération échoue")
    context_aware: bool = Field(default=True, description="Génération contextuelle intelligente")

    model_config = ConfigDict(extra="ignore")

class DocumentRelevance(BaseModel):
    """Score de pertinence détaillé du document RAG avec métadonnées enrichies"""
    score: float = Field(..., ge=0.0, le=1.0, description="Score de pertinence du document")
    source_document: Optional[str] = Field(default=None, description="Nom du document source")
    matched_section: Optional[str] = Field(default=None, description="Section correspondante")
    confidence_level: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM, description="Niveau de confiance")
    chunk_used: Optional[str] = Field(default=None, description="Extrait utilisé pour la réponse")
    alternative_documents: List[str] = Field(default_factory=list, description="Documents alternatifs considérés")
    search_query_used: Optional[str] = Field(default=None, description="Requête de recherche utilisée")

    model_config = ConfigDict(extra="ignore")

class ContextCoherence(BaseModel):
    """Vérification de cohérence entre contexte et RAG avec diagnostics détaillés"""
    entities_match: bool = Field(..., description="Les entités contextuelles correspondent au RAG")
    missing_critical_info: List[str] = Field(default_factory=list, description="Informations critiques manquantes")
    rag_assumptions: Dict[str, str] = Field(default_factory=dict, description="Hypothèses faites par le RAG")
    coherence_score: float = Field(..., ge=0.0, le=1.0, description="Score de cohérence global")
    warnings: List[str] = Field(default_factory=list, description="Alertes de cohérence")
    recommended_clarification: Optional[str] = Field(default=None, description="Clarification recommandée")
    entities_used_in_rag: Dict[str, Any] = Field(default_factory=dict, description="Entités utilisées par le RAG")

    model_config = ConfigDict(extra="ignore")

class VaguenessDetection(BaseModel):
    """Détection de questions floues ou imprécises avec suggestions d'amélioration"""
    is_vague: bool = Field(..., description="La question est-elle floue")
    vagueness_score: float = Field(..., ge=0.0, le=1.0, description="Score de flou (1.0 = très flou)")
    missing_specifics: List[str] = Field(default_factory=list, description="Éléments manquants")
    question_clarity: QuestionClarity = Field(default=QuestionClarity.UNCLEAR, description="Niveau de clarté")
    suggested_clarification: Optional[str] = Field(default=None, description="Clarification suggérée")
    actionable: bool = Field(default=True, description="La question peut-elle recevoir une réponse actionnable")
    detected_patterns: List[str] = Field(default_factory=list, description="Patterns de flou détectés")

    model_config = ConfigDict(extra="ignore")

class EnhancedFallbackDetails(BaseModel):
    """Détails enrichis pour les fallbacks avec diagnostics techniques"""
    failure_point: str = Field(..., description="Point d'échec dans le pipeline")
    last_known_entities: Dict[str, Any] = Field(default_factory=dict, description="Dernières entités extraites")
    confidence_at_failure: float = Field(..., ge=0.0, le=1.0, description="Confiance au moment de l'échec")
    rag_attempts: List[str] = Field(default_factory=list, description="Tentatives RAG effectuées")
    error_category: str = Field(default="unknown", description="Catégorie d'erreur")
    recovery_suggestions: List[str] = Field(default_factory=list, description="Suggestions de récupération")
    alternative_approaches: List[str] = Field(default_factory=list, description="Approches alternatives")
    technical_details: Optional[str] = Field(default=None, description="Détails techniques de l'erreur")

    model_config = ConfigDict(extra="ignore")

class QualityMetrics(BaseModel):
    """Métriques de qualité détaillées pour l'évaluation des réponses"""
    response_completeness: float = Field(..., ge=0.0, le=1.0, description="Complétude de la réponse")
    information_accuracy: float = Field(..., ge=0.0, le=1.0, description="Précision des informations")
    contextual_relevance: float = Field(..., ge=0.0, le=1.0, description="Pertinence contextuelle")
    user_satisfaction_prediction: float = Field(..., ge=0.0, le=1.0, description="Prédiction de satisfaction")
    response_length_appropriateness: float = Field(..., ge=0.0, le=1.0, description="Pertinence de la longueur")
    technical_accuracy: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Précision technique")

    model_config = ConfigDict(extra="ignore")

class ConcisionMetrics(BaseModel):
    """Métriques pour évaluer la qualité des versions de concision"""
    generation_time_ms: int = Field(..., ge=0, description="Temps de génération des versions en ms")
    versions_generated: int = Field(..., ge=0, le=4, description="Nombre de versions générées")
    cache_hit: bool = Field(default=False, description="Versions récupérées depuis le cache")
    fallback_used: bool = Field(default=False, description="Fallback utilisé pour certaines versions")
    compression_ratios: Dict[str, float] = Field(default_factory=dict, description="Ratios de compression par version")
    quality_scores: Dict[str, float] = Field(default_factory=dict, description="Scores de qualité par version")

    model_config = ConfigDict(extra="ignore")

class DynamicClarification(BaseModel):
    """Clarification générée dynamiquement via mode sémantique avec métadonnées"""
    original_question: str = Field(..., min_length=1, description="Question originale de l'utilisateur")
    clarification_questions: List[str] = Field(..., min_length=1, description="Questions de clarification générées")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confiance dans la génération")
    generation_method: str = Field(default="gpt_semantic", description="Méthode de génération utilisée")
    generation_time_ms: Optional[int] = Field(default=None, ge=0, description="Temps de génération en ms")
    fallback_used: bool = Field(default=False, description="Questions de fallback utilisées")

    @field_validator('clarification_questions')
    @classmethod
    def validate_clarification_questions(cls, v):
        if not v:
            raise ValueError('clarification_questions cannot be empty')
        return v

    model_config = ConfigDict(extra="ignore")

# =============================================================================
# 🧠 NOUVEAUX MODÈLES POUR TRAÇAGE DÉCISIONS IA - v3.9.7
# =============================================================================

class AiDecisionTrace(BaseModel):
    """
    Traçage complet d'une décision IA pour auditabilité
    
    Permet de comprendre pourquoi l'IA a pris une décision spécifique
    """
    decision_type: AiDecisionType = Field(..., description="Type de décision prise")
    decision_value: str = Field(..., description="Décision prise par l'IA")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confiance dans la décision")
    reasoning: str = Field(..., description="Raisonnement détaillé de l'IA")
    alternatives_considered: List[str] = Field(default_factory=list, description="Alternatives considérées")
    decision_time_ms: Optional[int] = Field(default=None, ge=0, description="Temps pour prendre la décision")
    input_factors: Dict[str, Any] = Field(default_factory=dict, description="Facteurs d'entrée influençant la décision")
    model_used: Optional[str] = Field(default=None, description="Modèle IA utilisé pour la décision")

    model_config = ConfigDict(extra="ignore")

class ResponseGenerationTrace(BaseModel):
    """
    Traçage spécifique de la génération de réponse
    
    Détaille comment la réponse finale a été générée
    """
    method_used: ResponseGenerationMethod = Field(..., description="Méthode de génération utilisée")
    primary_sources: List[str] = Field(default_factory=list, description="Sources principales utilisées")
    fallback_triggered: bool = Field(default=False, description="Fallback déclenché")
    enhancement_applied: bool = Field(default=False, description="Amélioration appliquée")
    quality_checks_passed: List[str] = Field(default_factory=list, description="Vérifications qualité réussies")
    generation_steps: List[str] = Field(default_factory=list, description="Étapes de génération")
    final_confidence: float = Field(..., ge=0.0, le=1.0, description="Confiance finale dans la réponse")

    model_config = ConfigDict(extra="ignore")

# =============================================================================
# MODÈLES DE REQUÊTE AMÉLIORÉS AVEC VALIDATION RENFORCÉE
# =============================================================================

class EnhancedQuestionRequest(BaseModel):
    """Request model amélioré avec nouvelles fonctionnalités + validation renforcée"""
    text: str = Field(..., min_length=1, max_length=5000, description="Texte de la question")
    language: str = Field(default="fr", description="Langue de réponse")
    speed_mode: str = Field(default="balanced", description="Mode de vitesse")
    
    # Contexte conversationnel
    conversation_id: Optional[str] = Field(default=None, description="ID de conversation")
    user_id: Optional[str] = Field(default=None, description="ID utilisateur")
    
    # Champs pour clarification (améliorés)
    is_clarification_response: bool = Field(default=False, description="Réponse à une clarification?")
    original_question: Optional[str] = Field(default=None, description="Question originale si clarification")
    clarification_context: Optional[Dict[str, Any]] = Field(default=None, description="Contexte de clarification")
    clarification_entities: Optional[Dict[str, str]] = Field(default=None, description="Entités extraites (race, sexe)")
    force_reprocess: bool = Field(default=False, description="Forcer le retraitement")

    # Champs concision
    concision_level: ConcisionLevel = Field(default=ConcisionLevel.CONCISE, description="Niveau de concision souhaité")
    generate_all_versions: bool = Field(default=True, description="Générer toutes les versions de concision")
    concision_preferences: ConcisionPreferences = Field(default_factory=ConcisionPreferences, description="Préférences avancées de concision")

    # Champs mode sémantique dynamique
    semantic_dynamic_mode: bool = Field(default=False, description="Activer le mode sémantique dynamique")
    semantic_dynamic_preferences: SemanticDynamicPreferences = Field(default_factory=SemanticDynamicPreferences, description="Préférences du mode sémantique dynamique")

    # 🧠 NOUVEAUX CHAMPS TRAÇAGE IA - v3.9.7
    enable_ai_tracing: bool = Field(default=True, description="Activer le traçage des décisions IA")
    trace_level: str = Field(default="standard", description="Niveau de traçage: minimal/standard/detailed")

    # Fonctionnalités existantes
    expected_response_format: ResponseFormat = Field(default=ResponseFormat.TEXT, description="Format de réponse attendu")
    response_preferences: ResponsePreferences = Field(default_factory=ResponsePreferences, description="Préférences de réponse")
    enable_vagueness_detection: bool = Field(default=True, description="Activer la détection de questions floues")
    require_coherence_check: bool = Field(default=True, description="Exiger la vérification de cohérence")
    detailed_rag_scoring: bool = Field(default=False, description="Scoring RAG détaillé")
    enable_quality_metrics: bool = Field(default=False, description="Activer les métriques de qualité")
    debug_mode: bool = Field(default=False, description="Mode debug pour développeurs")

    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        supported_languages = ['fr', 'en', 'es']
        if v not in supported_languages:
            raise ValueError(f'language must be one of {supported_languages}')
        return v

    @field_validator('speed_mode')
    @classmethod
    def validate_speed_mode(cls, v):
        supported_modes = ['fast', 'balanced', 'quality']
        if v not in supported_modes:
            raise ValueError(f'speed_mode must be one of {supported_modes}')
        return v

    @field_validator('trace_level')
    @classmethod
    def validate_trace_level(cls, v):
        supported_levels = ['minimal', 'standard', 'detailed']
        if v not in supported_levels:
            raise ValueError(f'trace_level must be one of {supported_levels}')
        return v

    @model_validator(mode='after')
    def validate_clarification_consistency(self):
        if self.is_clarification_response and not self.original_question:
            raise ValueError('original_question is required when is_clarification_response is True')
        return self

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        extra="ignore"
    )

class FeedbackRequest(BaseModel):
    """Request model pour feedback avec validation améliorée"""
    rating: str = Field(..., description="Rating: positive, negative, neutral")
    comment: Optional[str] = Field(default=None, max_length=1000, description="Commentaire optionnel")
    conversation_id: Optional[str] = Field(default=None, description="ID de conversation")
    quality_feedback: Optional[Dict[str, float]] = Field(default=None, description="Feedback détaillé sur la qualité")

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        valid_ratings = ['positive', 'negative', 'neutral']
        if v not in valid_ratings:
            raise ValueError(f'rating must be one of {valid_ratings}')
        return v

    @field_validator('quality_feedback')
    @classmethod
    def validate_quality_feedback(cls, v):
        if v is not None:
            for key, value in v.items():
                if not isinstance(value, (int, float)) or not (0.0 <= value <= 1.0):
                    raise ValueError(f'quality_feedback values must be numbers between 0.0 and 1.0')
        return v

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore"
    )

# =============================================================================
# MODÈLES DE RÉPONSE AMÉLIORÉS AVEC DOCUMENTATION ENRICHIE + CHAMPS MANQUANTS + TRAÇAGE IA v3.9.7
# =============================================================================

class EnhancedExpertResponse(BaseModel):
    """
    Response model complet avec toutes les fonctionnalités avancées + traçage IA
    
    🧠 NOUVEAU v3.9.7: Ajout des champs de traçage des décisions IA:
    - ai_classification_used: Bool si classification IA utilisée
    - ai_decision: Décision principale prise par l'IA
    - ai_confidence: Niveau de confiance global de l'IA
    - ai_reasoning: Raisonnement détaillé de l'IA
    - response_generation_method: Méthode de génération utilisée
    
    🔧 CORRECTION v3.9.6: Ajout des champs manquants pour correction complète:
    - clarification_details: Dict des détails de clarification
    - enhancement_info: Dict des informations d'amélioration
    - conversation_context: Dict du contexte conversationnel
    - pipeline_version: Version du pipeline utilisé
    - pipeline_improvements: Liste des améliorations appliquées
    
    Exemple d'utilisation:
    ```python
    response = EnhancedExpertResponse(
        question="Quel est le poids normal d'un poulet à 20 jours?",
        response="Le poids normal est de 350-400g à cet âge.",
        conversation_id="conv_123",
        rag_used=True,
        timestamp="2024-01-01T12:00:00Z",
        language="fr",
        response_time_ms=1500,
        mode="standard",
        enriched_question="Quel est le poids normal d'un poulet de race Ross 308 à 20 jours d'âge?",
        # Nouveaux champs IA v3.9.7
        ai_classification_used=True,
        ai_decision="rag_with_enhancement",
        ai_confidence=0.85,
        ai_reasoning="Question claire sur poids poulet - Race détectée automatiquement comme Ross 308 basé sur contexte standard",
        response_generation_method="rag_enhanced",
        # Champs existants v3.9.6
        clarification_details={"method": "dynamic_gpt", "confidence": 0.9},
        enhancement_info={"rag_enhancer": "applied", "method_used": "contextual"},
        conversation_context={"previous_topics": ["alimentation", "croissance"]},
        pipeline_version="expert_models_aligned_v4.1.0",
        pipeline_improvements=["agents_always_active", "critical_clarification_blocking"],
        response_versions={
            "ultra_concise": "350-400g",
            "concise": "Le poids normal est de 350-400g à cet âge.",
            "standard": "Le poids normal d'un poulet à 20 jours est de 350-400g. Surveillez la croissance.",
            "detailed": "Le poids normal d'un poulet Ross 308 à 20 jours se situe entre 350-400g pour les mâles..."
        }
    )
    ```
    """
    
    # Champs principaux (obligatoires)
    question: str = Field(..., description="Question posée par l'utilisateur")
    response: str = Field(..., description="Réponse générée par l'IA")
    conversation_id: str = Field(..., description="ID unique de conversation")
    rag_used: Optional[bool] = Field(default=None, description="RAG utilisé pour cette réponse")
    timestamp: str = Field(..., description="Timestamp ISO de la réponse")
    language: str = Field(..., description="Langue de la réponse")
    response_time_ms: int = Field(..., ge=0, description="Temps de réponse en millisecondes")
    mode: str = Field(..., description="Mode de traitement utilisé")
    
    # 🔧 CORRECTION v3.9.5: Ajout du champ enriched_question demandé
    enriched_question: Optional[str] = Field(default=None, description="Question enrichie par agent_rag_enhancer")
    
    # 🧠 NOUVEAUX CHAMPS TRAÇAGE IA - v3.9.7
    ai_classification_used: Optional[bool] = Field(default=None, description="Classification IA utilisée")
    ai_decision: Optional[str] = Field(default=None, description="Décision prise par l'IA")
    ai_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confiance de l'IA")
    ai_reasoning: Optional[str] = Field(default=None, description="Raisonnement de l'IA")
    response_generation_method: Optional[str] = Field(default=None, description="Méthode génération réponse")
    
    # 🧠 TRAÇAGE AVANCÉ IA - v3.9.7 (optionnel pour compatibilité)
    ai_decision_traces: Optional[List[AiDecisionTrace]] = Field(default=None, description="Traces détaillées des décisions IA")
    response_generation_trace: Optional[ResponseGenerationTrace] = Field(default=None, description="Trace de génération de réponse")
    
    # 🔧 CORRECTION v3.9.6: AJOUTS OBLIGATOIRES pour correction demandée
    clarification_details: Optional[Dict[str, Any]] = Field(default=None, description="Détails de clarification")
    enhancement_info: Optional[Dict[str, Any]] = Field(default=None, description="Informations d'amélioration")
    
    # 🔧 CORRECTION v3.9.6: CHAMPS OPTIONNELS SUPPLÉMENTAIRES pour correction demandée
    conversation_context: Optional[Dict[str, Any]] = Field(default=None, description="Contexte de conversation")
    pipeline_version: Optional[str] = Field(default=None, description="Version du pipeline")
    pipeline_improvements: Optional[List[str]] = Field(default=None, description="Améliorations appliquées")
    
    # 🔧 CORRECTION v3.9.5: Ajout des champs demandés dans les spécifications
    clarification_required_critical: Optional[bool] = Field(default=None, description="Clarification critique requise")
    missing_critical_entities: Optional[List[str]] = Field(default=None, description="Entités critiques manquantes")
    variants_tested: Optional[List[str]] = Field(default=None, description="Variantes testées par le système")
    
    # Champs optionnels avec valeurs par défaut
    rag_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Score de pertinence RAG")
    user: Optional[str] = Field(default=None, description="Utilisateur ayant posé la question")
    logged: bool = Field(default=False, description="Réponse loggée dans le système")
    validation_passed: Optional[bool] = Field(default=None, description="Validation réussie")
    validation_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confiance dans la validation")
    
    # Versions de concision
    response_versions: Optional[Dict[str, str]] = Field(
        default=None,
        description="Toutes les versions de concision de la réponse",
        example={
            "ultra_concise": "350-400g",
            "concise": "Le poids normal est de 350-400g à cet âge.",
            "standard": "Le poids normal d'un poulet à 20 jours est de 350-400g. Surveillez la croissance régulièrement.",
            "detailed": "Le poids normal d'un poulet Ross 308 à 20 jours se situe entre 350-400g pour les mâles et 320-380g pour les femelles. Il est important de surveiller la croissance hebdomadairement et d'ajuster l'alimentation si nécessaire. Contactez votre vétérinaire si les écarts dépassent 15%."
        }
    )
    
    # Métriques et informations techniques
    concision_metrics: Optional[ConcisionMetrics] = Field(default=None, description="Métriques détaillées sur la génération des versions de concision")
    dynamic_clarification: Optional[DynamicClarification] = Field(default=None, description="Informations sur la clarification sémantique dynamique générée")
    
    # Traitement de clarification
    clarification_result: Optional[Dict[str, Any]] = Field(default=None, description="Résultat du traitement de clarification")
    reprocessed_after_clarification: Optional[bool] = Field(default=None, description="Retraité après clarification")
    conversation_state: Optional[str] = Field(default=None, description="État de la conversation")
    extracted_entities: Optional[Dict[str, Any]] = Field(default=None, description="Entités extraites de la question")
    confidence_overall: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confiance globale dans la réponse")
    processing_steps: List[str] = Field(default_factory=list, description="Étapes de traitement effectuées")
    ai_enhancements_used: List[str] = Field(default_factory=list, description="Améliorations IA utilisées")
    clarification_processing: Optional[Dict[str, Any]] = Field(default=None, description="Métadonnées traitement clarification")
    
    # Ajout du champ manquant contextualization_info
    contextualization_info: Optional[Dict[str, Any]] = Field(default=None, description="Informations de contextualisation")
    
    # Fonctionnalités avancées
    document_relevance: Optional[DocumentRelevance] = Field(default=None, description="Score de pertinence détaillé")
    context_coherence: Optional[ContextCoherence] = Field(default=None, description="Vérification de cohérence")
    vagueness_detection: Optional[VaguenessDetection] = Field(default=None, description="Détection de questions floues")
    fallback_details: Optional[EnhancedFallbackDetails] = Field(default=None, description="Détails de fallback enrichis")
    response_format_applied: Optional[str] = Field(default=None, description="Format appliqué à la réponse")
    quality_metrics: Optional[QualityMetrics] = Field(default=None, description="Métriques de qualité détaillées")
    
    # Debug et développement
    debug_info: Optional[Dict[str, Any]] = Field(default=None, description="Informations de debug")
    rag_debug: Optional[Dict[str, Any]] = Field(default=None, description="Debug détaillé du RAG")
    performance_breakdown: Optional[Dict[str, int]] = Field(default=None, description="Breakdown des temps de traitement")

    # Informations spécifiques nouvelles fonctionnalités
    concision_info: Optional[Dict[str, Any]] = Field(default=None, description="Informations système de concision")
    original_response: Optional[str] = Field(default=None, description="Réponse originale avant concision")
    taxonomy_info: Optional[Dict[str, Any]] = Field(default=None, description="Informations taxonomiques")
    semantic_dynamic_info: Optional[Dict[str, Any]] = Field(default=None, description="Informations mode sémantique dynamique")

    model_config = ConfigDict(extra="ignore")

# =============================================================================
# MODÈLES UTILITAIRES AVEC VALIDATION AMÉLIORÉE
# =============================================================================

class ClarificationResult(BaseModel):
    """Résultat de clarification avec entités manquantes détaillées"""
    missing_entities: Optional[List[str]] = Field(default=None, description="Entités manquantes identifiées")
    missing_critical_entities: Optional[List[str]] = Field(default=None, description="Entités critiques manquantes")
    clarification_required_critical: Optional[bool] = Field(default=None, description="Clarification critique requise")
    critical_entities_for_type: Optional[List[str]] = Field(default=None, description="Entités critiques pour ce type")
    clarification_needed: bool = Field(default=False, description="Clarification nécessaire")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Score de confiance")
    suggested_questions: List[str] = Field(default_factory=list, description="Questions suggérées")

    model_config = ConfigDict(extra="ignore")

class ValidationResult(BaseModel):
    """Résultat de validation avec diagnostics détaillés"""
    is_valid: bool = Field(..., description="La validation a-t-elle réussi")
    rejection_message: str = Field(default="", description="Message d'erreur en cas de rejet")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confiance dans la validation")
    validation_details: Optional[Dict[str, Any]] = Field(default=None, description="Détails de validation")

    model_config = ConfigDict(extra="ignore")

class ProcessingContext(BaseModel):
    """Contexte de traitement avec suivi détaillé"""
    user_id: str = Field(..., description="ID utilisateur")
    conversation_id: str = Field(..., description="ID conversation")
    request_ip: str = Field(..., description="IP de la requête")
    processing_steps: List[str] = Field(default_factory=list, description="Étapes de traitement")
    ai_enhancements_used: List[str] = Field(default_factory=list, description="Améliorations IA utilisées")
    start_time: Optional[float] = Field(default=None, description="Timestamp de début")
    enhancement_flags: Dict[str, bool] = Field(default_factory=dict, description="Flags d'amélioration")

    model_config = ConfigDict(extra="ignore")

# =============================================================================
# MODÈLES POUR AMÉLIORER LA MÉMOIRE CONVERSATIONNELLE - CORRECTIONS v3.9.5
# =============================================================================

class IntelligentEntities(BaseModel):
    """
    Entités intelligentes pour améliorer la mémoire conversationnelle
    🔧 CORRECTION v3.9.5: Ajout des champs weight et mortality demandés
    """
    # Attributs existants conservés
    age: Optional[str] = Field(default=None, description="Age de l'animal")
    breed: Optional[str] = Field(default=None, description="Race de l'animal")
    sex: Optional[str] = Field(default=None, description="Sexe de l'animal")
    species: Optional[str] = Field(default=None, description="Espèce de l'animal")
    production_type: Optional[str] = Field(default=None, description="Type de production")
    housing_system: Optional[str] = Field(default=None, description="Système d'élevage")
    feed_type: Optional[str] = Field(default=None, description="Type d'alimentation")
    health_status: Optional[str] = Field(default=None, description="État de santé")
    environment_conditions: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Conditions environnementales")
    
    # 🔧 CORRECTION v3.9.5: Ajout des champs demandés dans les spécifications
    age_in_days: Optional[int] = Field(default=None, description="Age en jours")
    age_in_weeks: Optional[int] = Field(default=None, description="Age en semaines")
    weight: Optional[float] = Field(default=None, description="Poids de l'animal en grammes")
    mortality: Optional[float] = Field(default=None, description="Taux de mortalité observé")
    
    # Champs supplémentaires pour compatibilité avec conversation_memory
    temperature: Optional[float] = Field(default=None, description="Température ambiante")
    humidity: Optional[float] = Field(default=None, description="Humidité relative")
    density: Optional[float] = Field(default=None, description="Densité d'élevage")
    mortality_rate: Optional[float] = Field(default=None, description="Taux de mortalité (alias de mortality)")
    growth_rate: Optional[float] = Field(default=None, description="Taux de croissance")
    feed_conversion_ratio: Optional[float] = Field(default=None, description="Indice de consommation")
    
    # Métadonnées de confiance
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Scores de confiance par entité")
    extraction_method: str = Field(default="nlp", description="Méthode d'extraction utilisée")
    last_updated: Optional[str] = Field(default=None, description="Dernière mise à jour")
    
    model_config = ConfigDict(extra="ignore")

# =============================================================================
# MODÈLES DE STATS ET CONFIGURATION SYSTÈME
# =============================================================================

class SystemStats(BaseModel):
    """Statistiques système avec état complet des fonctionnalités"""
    system_available: bool = Field(..., description="Système disponible")
    timestamp: str = Field(..., description="Timestamp de l'état")
    components: Dict[str, bool] = Field(..., description="État des composants")
    enhanced_capabilities: List[str] = Field(default_factory=list, description="Capacités améliorées")
    enhanced_endpoints: List[str] = Field(default_factory=list, description="Endpoints améliorés")
    quality_metrics_enabled: bool = Field(default=False, description="Métriques de qualité activées")
    debug_mode_available: bool = Field(default=False, description="Mode debug disponible")
    concision_system_enabled: bool = Field(default=True, description="Système de concision activé")
    semantic_dynamic_enabled: bool = Field(default=True, description="Mode sémantique dynamique activé")
    # 🧠 NOUVEAU v3.9.7
    ai_tracing_enabled: bool = Field(default=True, description="Traçage IA activé")

    model_config = ConfigDict(extra="ignore")

class TestResult(BaseModel):
    """Résultat de test complet avec diagnostics"""
    question: str = Field(..., description="Question testée")
    conversation_id: str = Field(..., description="ID conversation de test")
    user_id: str = Field(..., description="ID utilisateur de test")
    timestamp: str = Field(..., description="Timestamp du test")
    components_tested: Dict[str, Any] = Field(..., description="Composants testés")
    test_successful: bool = Field(..., description="Test réussi")
    errors: List[str] = Field(default_factory=list, description="Erreurs rencontrées")
    enhancement_results: Optional[Dict[str, Any]] = Field(default=None, description="Résultats des améliorations")
    concision_test_results: Optional[Dict[str, Any]] = Field(default=None, description="Résultats test concision")
    semantic_dynamic_test_results: Optional[Dict[str, Any]] = Field(default=None, description="Résultats test mode sémantique dynamique")
    # 🧠 NOUVEAU v3.9.7
    ai_tracing_test_results: Optional[Dict[str, Any]] = Field(default=None, description="Résultats test traçage IA")

    model_config = ConfigDict(extra="ignore")

# =============================================================================
# MODÈLES POUR RÉPONSES SPÉCIALISÉES
# =============================================================================

class VaguenessResponse(BaseModel):
    """Réponse spécialisée pour questions floues avec suggestions"""
    question: str = Field(..., description="Question analysée")
    response: str = Field(..., description="Réponse générée")
    conversation_id: str = Field(..., description="ID conversation")
    vagueness_detection: VaguenessDetection = Field(..., description="Détection de flou")
    suggested_improvements: List[str] = Field(default_factory=list, description="Améliorations suggérées")
    example_questions: List[str] = Field(default_factory=list, description="Exemples de questions")
    timestamp: str = Field(..., description="Timestamp")
    language: str = Field(..., description="Langue")
    response_time_ms: int = Field(..., ge=0, description="Temps de réponse")

    model_config = ConfigDict(extra="ignore")

class CoherenceWarningResponse(BaseModel):
    """Réponse avec avertissements de cohérence détaillés"""
    original_response: str = Field(..., description="Réponse originale")
    coherence_warnings: List[str] = Field(default_factory=list, description="Avertissements de cohérence")
    suggested_clarifications: List[str] = Field(default_factory=list, description="Clarifications suggérées")
    confidence_impact: float = Field(..., ge=0.0, le=1.0, description="Impact sur la confiance")
    should_ask_clarification: bool = Field(..., description="Demander une clarification")

    model_config = ConfigDict(extra="ignore")

class ConcisionResponse(BaseModel):
    """Réponse spécialisée avec focus sur les versions de concision"""
    question: str = Field(..., description="Question posée")
    selected_response: str = Field(..., description="Réponse sélectionnée")
    selected_level: ConcisionLevel = Field(..., description="Niveau de concision sélectionné")
    all_versions: Dict[str, str] = Field(..., description="Toutes les versions générées")
    conversation_id: str = Field(..., description="ID conversation")
    generation_details: ConcisionMetrics = Field(..., description="Détails de génération")
    timestamp: str = Field(..., description="Timestamp")
    language: str = Field(..., description="Langue")
    response_time_ms: int = Field(..., ge=0, description="Temps de réponse")

    model_config = ConfigDict(extra="ignore")

class SemanticDynamicResponse(BaseModel):
    """Réponse spécialisée pour clarification sémantique dynamique"""
    question: str = Field(..., description="Question originale")
    clarification_questions: List[str] = Field(..., min_length=1, description="Questions de clarification")
    conversation_id: str = Field(..., description="ID conversation")
    dynamic_clarification: DynamicClarification = Field(..., description="Détails clarification dynamique")
    generation_method: str = Field(..., description="Méthode de génération")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Score de confiance")
    timestamp: str = Field(..., description="Timestamp")
    language: str = Field(..., description="Langue")
    response_time_ms: int = Field(..., ge=0, description="Temps de réponse")

    model_config = ConfigDict(extra="ignore")

# =============================================================================
# MODÈLES DE CONFIGURATION SYSTÈME
# =============================================================================

class SemanticDynamicConfig(BaseModel):
    """Configuration du système sémantique dynamique avec validation"""
    enabled: bool = Field(default=True, description="Système activé")
    max_questions: int = Field(default=4, ge=1, le=10, description="Nombre max de questions")
    supported_languages: List[str] = Field(default=["fr", "en", "es"], description="Langues supportées")
    gpt_model: str = Field(default="gpt-4o-mini", description="Modèle GPT utilisé")
    fallback_enabled: bool = Field(default=True, description="Fallback activé")
    context_aware: bool = Field(default=True, description="Prise en compte du contexte")
    timeout_seconds: int = Field(default=25, ge=5, le=60, description="Timeout en secondes")

    model_config = ConfigDict(extra="ignore")

class TaxonomicFilteringConfig(BaseModel):
    """Configuration du filtrage taxonomique avec validation"""
    enabled: bool = Field(default=True, description="Filtrage activé")
    supported_taxonomies: List[str] = Field(
        default=["broiler", "layer", "swine", "dairy", "general"], 
        description="Taxonomies supportées"
    )
    auto_detection: bool = Field(default=True, description="Détection automatique")
    filter_fallback: bool = Field(default=True, description="Fallback de filtrage")
    question_enhancement: bool = Field(default=True, description="Amélioration des questions")

    model_config = ConfigDict(extra="ignore")

# =============================================================================
# 🧠 NOUVEAU: CONFIGURATION TRAÇAGE IA - v3.9.7
# =============================================================================

class AiTracingConfig(BaseModel):
    """Configuration du système de traçage des décisions IA"""
    enabled: bool = Field(default=True, description="Traçage IA activé")
    trace_level: str = Field(default="standard", description="Niveau de traçage: minimal/standard/detailed")
    store_traces: bool = Field(default=True, description="Stocker les traces pour audit")
    trace_timeout_ms: int = Field(default=1000, ge=100, le=5000, description="Timeout pour génération des traces")
    include_alternatives: bool = Field(default=True, description="Inclure les alternatives considérées")
    include_reasoning: bool = Field(default=True, description="Inclure le raisonnement détaillé")
    
    @field_validator('trace_level')
    @classmethod
    def validate_trace_level(cls, v):
        supported_levels = ['minimal', 'standard', 'detailed']
        if v not in supported_levels:
            raise ValueError(f'trace_level must be one of {supported_levels}')
        return v

    model_config = ConfigDict(extra="ignore")

class EnhancedSystemConfig(BaseModel):
    """Configuration système complète avec tous les modules"""
    concision_config: Optional[Dict[str, Any]] = Field(default=None, description="Configuration concision")
    semantic_dynamic_config: SemanticDynamicConfig = Field(default_factory=SemanticDynamicConfig, description="Config sémantique dynamique")
    taxonomic_filtering_config: TaxonomicFilteringConfig = Field(default_factory=TaxonomicFilteringConfig, description="Config filtrage taxonomique")
    # 🧠 NOUVEAU v3.9.7
    ai_tracing_config: AiTracingConfig = Field(default_factory=AiTracingConfig, description="Config traçage IA")
    
    response_versions_enabled: bool = Field(default=True, description="Versions de réponses activées")
    advanced_clarification_enabled: bool = Field(default=True, description="Clarification avancée activée")

    model_config = ConfigDict(extra="ignore")

# =============================================================================
# CONFIGURATION ET LOGGING
# =============================================================================

logger = logging.getLogger(__name__)

logger.info("✅ [Expert Models] Modèles Pydantic chargés avec corrections complètes v3.9.7")
logger.info("🧠 [Expert Models] NOUVEAUTÉS v3.9.7 - TRAÇAGE DÉCISIONS IA:")
logger.info("   - ✅ ai_classification_used: Optional[bool] dans EnhancedExpertResponse")
logger.info("   - ✅ ai_decision: Optional[str] dans EnhancedExpertResponse")
logger.info("   - ✅ ai_confidence: Optional[float] dans EnhancedExpertResponse")
logger.info("   - ✅ ai_reasoning: Optional[str] dans EnhancedExpertResponse")
logger.info("   - ✅ response_generation_method: Optional[str] dans EnhancedExpertResponse")
logger.info("   - ✅ AiDecisionTrace: Nouveau modèle pour traçage détaillé")
logger.info("   - ✅ ResponseGenerationTrace: Nouveau modèle pour traçage génération")
logger.info("   - ✅ AiDecisionType: Enum pour types de décisions")
logger.info("   - ✅ ResponseGenerationMethod: Enum pour méthodes de génération")
logger.info("   - ✅ AiTracingConfig: Configuration du traçage IA")
logger.info("   - ✅ enable_ai_tracing: Paramètre dans EnhancedQuestionRequest")
logger.info("🔧 [Expert Models] CORRECTIONS v3.9.6 conservées (selon demande spécifique):")
logger.info("   - ✅ clarification_details: Optional[Dict[str, Any]] dans EnhancedExpertResponse")
logger.info("   - ✅ enhancement_info: Optional[Dict[str, Any]] dans EnhancedExpertResponse")
logger.info("   - ✅ conversation_context: Optional[Dict[str, Any]] dans EnhancedExpertResponse")
logger.info("   - ✅ pipeline_version: Optional[str] dans EnhancedExpertResponse")
logger.info("   - ✅ pipeline_improvements: Optional[List[str]] dans EnhancedExpertResponse")
logger.info("🔧 [Expert Models] CORRECTIONS PRÉCÉDENTES conservées:")
logger.info("   - ✅ enriched_question: Optional[str] dans EnhancedExpertResponse")
logger.info("   - ✅ clarification_required_critical: Optional[bool] dans EnhancedExpertResponse")
logger.info("   - ✅ missing_critical_entities: Optional[List[str]] dans EnhancedExpertResponse")
logger.info("   - ✅ variants_tested: Optional[List[str]] dans EnhancedExpertResponse")
logger.info("   - ✅ age_in_days, age_in_weeks, weight, mortality dans IntelligentEntities")
logger.info("   - ✅ ClarificationResult avec missing_entities pour éviter l'erreur")
logger.info("   - ✅ contextualization_info ajouté à EnhancedExpertResponse")
logger.info("   - ✅ clarification_processing ajouté pour métadonnées")
logger.info("   - ✅ Validation robuste pour tous les modèles")
logger.info("🆕 [Expert Models] Fonctionnalités complètes:")
logger.info("   - 📊 DocumentRelevance: Scoring RAG détaillé")
logger.info("   - 🔍 ContextCoherence: Vérification de cohérence")
logger.info("   - 🎯 VaguenessDetection: Détection de questions floues")
logger.info("   - 🔧 EnhancedFallbackDetails: Fallback enrichi")
logger.info("   - 📈 QualityMetrics: Métriques de qualité")
logger.info("   - 🐛 Debug mode: Support pour développeurs")
logger.info("🚀 [Expert Models] FONCTIONNALITÉS RESPONSE VERSIONS:")
logger.info("   - 📝 ConcisionLevel: 4 niveaux validés")
logger.info("   - 🎛️ response_versions: Toutes les versions dans la réponse")
logger.info("   - 📊 ConcisionMetrics: Métriques génération validées")
logger.info("🆕 [Expert Models] FONCTIONNALITÉS SEMANTIC DYNAMIC:")
logger.info("   - 🎭 DynamicClarification: Modèle validé")
logger.info("   - 🤖 semantic_dynamic_mode: Paramètre validé")
logger.info("   - ⚙️ SemanticDynamicConfig: Configuration validée")
logger.info("🧠 [Expert Models] AVANTAGES TRAÇAGE IA v3.9.7:")
logger.info("   - 🔍 Auditabilité complète des décisions IA")
logger.info("   - 📊 Métriques de confiance détaillées")
logger.info("   - 🎯 Traçage des méthodes de génération")
logger.info("   - 🔧 Debug avancé pour les développeurs")
logger.info("   - 📋 Compatibilité ascendante 100%")
logger.info("✨ [Expert Models] RÉSULTAT v3.9.7: Traçage IA complet ajouté avec succès!")
logger.info("🎯 [Expert Models] UTILISATION TRAÇAGE IA:")
logger.info("   → Activer: enable_ai_tracing=True dans la requête")
logger.info("   → Niveau: trace_level='standard/detailed' pour plus de détails")
logger.info("   → Accès: Champs ai_* dans EnhancedExpertResponse")
logger.info("   → Debug: ai_decision_traces pour traçage complet")
logger.info("🚀 [Expert Models] PRÊT POUR PRODUCTION AVEC TRAÇAGE IA COMPLET!")