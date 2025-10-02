# -*- coding: utf-8 -*-
"""
api/chat_models.py - Modèles Pydantic pour les endpoints de chat
Version 4.2.3 - DÉTECTION AMÉLIORÉE + GESTION AMBIGUÏTÉ + ABANDON
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class JSONValidationRequest(BaseModel):
    """Requête de validation JSON avicole"""

    json_data: Dict[str, Any] = Field(..., description="Données JSON à valider")
    strict_mode: bool = Field(False, description="Mode de validation strict")
    auto_enrich: bool = Field(
        True, description="Enrichissement automatique des métadonnées"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "json_data": {
                    "title": "Ross 308 Performance Guide",
                    "text": "Performance objectives for Ross 308 broilers...",
                    "metadata": {"genetic_line": "ross308"},
                    "tables": [],
                },
                "strict_mode": False,
                "auto_enrich": True,
            }
        }
    }


class IngestionRequest(BaseModel):
    """Requête d'ingestion de fichiers JSON"""

    json_files: List[Dict[str, Any]] = Field(..., description="Liste des fichiers JSON")
    batch_size: int = Field(5, ge=1, le=20, description="Taille des lots de traitement")
    force_reprocess: bool = Field(
        False, description="Forcer le retraitement des fichiers existants"
    )

    @field_validator("json_files")
    @classmethod
    def validate_json_files(cls, v):
        if len(v) > 100:
            raise ValueError("Maximum 100 fichiers par lot")
        return v


class ExpertQueryRequest(BaseModel):
    """Requête d'expertise avicole avec support JSON"""

    question: str = Field(
        ..., min_length=5, max_length=500, description="Question de l'utilisateur"
    )
    language: str = Field(
        "fr", pattern="^(fr|en|es|zh|ar)$", description="Langue de la réponse"
    )
    genetic_line: Optional[str] = Field(None, description="Lignée génétique spécifique")
    user_id: Optional[str] = Field(None, description="Identifiant utilisateur")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexte additionnel")
    response_format: str = Field(
        "detailed", pattern="^(ultra_concise|concise|standard|detailed)$"
    )
    use_json_search: bool = Field(
        True, description="Utiliser la recherche JSON prioritaire"
    )
    performance_metrics: Optional[List[str]] = Field(
        None, description="Métriques de performance à filtrer"
    )
    age_range: Optional[Dict[str, int]] = Field(
        None, description="Plage d'âge en jours"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Quel est le poids cible à 35 jours pour du Ross 308 mâle?",
                "language": "fr",
                "genetic_line": "ross308",
                "use_json_search": True,
                "performance_metrics": ["poids", "fcr"],
                "age_range": {"min": 30, "max": 40},
            }
        }
    }


class ChatRequest(BaseModel):
    """Requête de chat étendue avec support JSON"""

    message: str = Field(
        ..., min_length=1, max_length=2000, description="Message utilisateur"
    )
    language: Optional[str] = Field(None, description="Langue de la réponse")
    tenant_id: Optional[str] = Field(None, description="Identifiant du tenant")
    genetic_line_filter: Optional[str] = Field(
        None, description="Filtre lignée génétique"
    )
    use_json_search: bool = Field(True, description="Utiliser le système JSON")
    performance_context: Optional[Dict[str, Any]] = Field(
        None, description="Contexte performance"
    )
