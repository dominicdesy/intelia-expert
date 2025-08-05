"""
app/api/v1/conversation_extraction.py - Extraction d'entités JSON STRICT avec Pydantic + Améliorations Robustesse

🔧 VERSION 3.1 CORRIGÉE: JSON STRICT + Validation Pydantic + Schéma Forcé + AMÉLIORATIONS ROBUSTESSE
✅ Prompt GPT avec JSON strict obligatoire
✅ Validation Pydantic pour garantir les types
✅ Schéma d'extraction unifié et robuste
✅ Fallback intelligent avec types corrects
✅ Parsing sécurisé avec json.loads()
✅ CORRIGÉ: Validation post-extraction exhaustive
✅ CORRIGÉ: Détection JSON vide et fallback automatique
✅ CORRIGÉ: Métriques de qualité extraction avec tous les champs
"""

import os
import json
import logging
import re
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from datetime import datetime
from pydantic import BaseModel, Field, validator, ValidationError

# Import OpenAI sécurisé pour extraction intelligente
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

from .conversation_entities import IntelligentEntities, IntelligentConversationContext, safe_int_conversion, safe_float_conversion, force_type_coercion

logger = logging.getLogger(__name__)

class EntityExtractionSchema(BaseModel):
    """Schéma Pydantic STRICT pour l'extraction d'entités par GPT"""
    
    # Informations race avec validation
    breed: Optional[str] = Field(None, description="Race exacte des poulets (Ross 308, Cobb 500, etc.) ou null")
    breed_type: Optional[str] = Field(None, description="Type de race: 'specific' ou 'generic' ou null")
    breed_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confiance détection race (0.0-1.0)")
    
    # Informations sexe avec validation
    sex: Optional[str] = Field(None, description="Sexe: 'mâles', 'femelles', 'mixte', 'males', 'females', 'mixed' ou null")
    sex_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confiance détection sexe (0.0-1.0)")
    
    # Informations âge avec validation STRICTE
    age_in_days: Optional[int] = Field(None, ge=0, le=365, description="Âge en jours (entier) ou null")
    age_in_weeks: Optional[float] = Field(None, ge=0.0, le=52.0, description="Âge en semaines (décimal) ou null")
    age_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confiance détection âge (0.0-1.0)")
    
    # Informations poids avec validation STRICTE  
    weight_grams: Optional[float] = Field(None, ge=0.0, le=10000.0, description="Poids en grammes (décimal) ou null")
    weight_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confiance détection poids (0.0-1.0)")
    expected_weight_min: Optional[float] = Field(None, ge=0.0, description="Poids minimum attendu en grammes ou null")
    expected_weight_max: Optional[float] = Field(None, ge=0.0, description="Poids maximum attendu en grammes ou null")
    growth_assessment: Optional[str] = Field(None, description="Évaluation croissance: 'normal', 'slow', 'fast' ou null")
    
    # Informations santé avec validation
    mortality_rate: Optional[float] = Field(None, ge=0.0, le=100.0, description="Taux mortalité en pourcentage ou null")
    mortality_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confiance détection mortalité (0.0-1.0)")
    symptoms: Optional[str] = Field(None, description="Symptômes observés (texte libre) ou null")
    health_status: Optional[str] = Field(None, description="État santé: 'good', 'concern', 'poor' ou null")
    
    # Informations environnement avec validation
    temperature_celsius: Optional[float] = Field(None, ge=-10.0, le=60.0, description="Température en Celsius ou null")
    humidity_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Humidité en pourcentage ou null")
    housing_type: Optional[str] = Field(None, description="Type logement ou null")
    
    # Informations troupeau avec validation
    flock_size: Optional[int] = Field(None, ge=1, le=1000000, description="Taille troupeau (entier) ou null")
    feed_type: Optional[str] = Field(None, description="Type alimentation ou null")
    
    # Évaluation problème avec validation
    problem_severity: Optional[str] = Field(None, description="Sévérité: 'low', 'medium', 'high', 'critical' ou null")
    intervention_urgency: Optional[str] = Field(None, description="Urgence: 'none', 'low', 'medium', 'high' ou null")
    
    # Métadonnées extraction
    extraction_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confiance globale extraction (0.0-1.0)")
    
    @validator('age_in_weeks', pre=True)
    def validate_age_weeks(cls, v, values):
        """Calcul automatique semaines depuis jours si manquant"""
        if v is None and 'age_in_days' in values and values['age_in_days'] is not None:
            return round(values['age_in_days'] / 7, 1)
        return v
    
    @validator('age_in_days', pre=True)
    def validate_age_days(cls, v, values):
        """Calcul automatique jours depuis semaines si manquant"""
        if v is None and 'age_in_weeks' in values and values['age_in_weeks'] is not None:
            return int(values['age_in_weeks'] * 7)
        return v

    class Config:
        """Configuration Pydantic pour validation stricte"""
        extra = "forbid"  # Interdire champs supplémentaires
        validate_assignment = True  # Valider lors des assignations


class ExtractionQualityMetrics(BaseModel):
    """🔧 CORRIGÉE: Métriques de qualité d'extraction avec tous les champs obligatoires"""
    
    # Champs de base TOUJOURS requis
    total_fields: int = Field(description="Nombre total de champs dans le schéma")
    populated_fields: int = Field(description="Nombre de champs avec des valeurs non-null")
    empty_fields: int = Field(description="Nombre de champs avec des valeurs null")
    confidence_scores: List[float] = Field(default_factory=list, description="Scores de confiance collectés")
    
    # Métriques calculées AVEC VALEURS PAR DÉFAUT
    completion_rate: float = Field(default=0.0, description="Taux de completion (populated/total)")
    average_confidence: float = Field(default=0.0, description="Confiance moyenne des champs peuplés")
    quality_score: float = Field(default=0.0, description="Score qualité global (0.0-1.0)")
    
    # Indicateurs de qualité AVEC VALEURS PAR DÉFAUT
    is_empty_extraction: bool = Field(default=True, description="True si extraction complètement vide")
    is_high_quality: bool = Field(default=False, description="True si extraction de haute qualité")
    needs_fallback: bool = Field(default=True, description="True si fallback recommandé")
    
    @validator('completion_rate', pre=True, always=True)
    def calculate_completion_rate(cls, v, values):
        """Calcul automatique du taux de completion"""
        total = values.get('total_fields', 1)
        populated = values.get('populated_fields', 0)
        return round(populated / max(total, 1), 3)
    
    @validator('average_confidence', pre=True, always=True)
    def calculate_average_confidence(cls, v, values):
        """Calcul automatique de la confiance moyenne"""
        scores = values.get('confidence_scores', [])
        if scores:
            return round(sum(scores) / len(scores), 3)
        return 0.0
    
    @validator('quality_score', pre=True, always=True)
    def calculate_quality_score(cls, v, values):
        """Calcul du score qualité global"""
        completion = values.get('completion_rate', 0.0)
        confidence = values.get('average_confidence', 0.0)
        # Score pondéré: 60% completion + 40% confidence
        return round((completion * 0.6) + (confidence * 0.4), 3)
    
    @validator('is_empty_extraction', pre=True, always=True)
    def detect_empty_extraction(cls, v, values):
        """Détection extraction vide"""
        populated = values.get('populated_fields', 0)
        confidence = values.get('average_confidence', 0.0)
        return populated == 0 or confidence < 0.05
    
    @validator('is_high_quality', pre=True, always=True)
    def detect_high_quality(cls, v, values):
        """Détection haute qualité"""
        quality = values.get('quality_score', 0.0)
        return quality >= 0.7
    
    @validator('needs_fallback', pre=True, always=True)
    def detect_needs_fallback(cls, v, values):
        """Détection besoin de fallback"""
        quality = values.get('quality_score', 0.0)
        is_empty = values.get('is_empty_extraction', True)
        return is_empty or quality < 0.3


class ValidationResult(BaseModel):
    """🔧 NOUVEAU: Résultat de validation post-extraction"""
    
    is_valid: bool = Field(description="True si validation réussie")
    issues: List[str] = Field(default_factory=list, description="Liste des problèmes détectés")


class ConversationEntityExtractor:
    """Extracteur d'entités JSON STRICT avec validation Pydantic + Améliorations Robustesse"""
    
    def __init__(self):
        self.ai_enhancement_enabled = os.getenv('AI_ENHANCEMENT_ENABLED', 'true').lower() == 'true'
        self.ai_enhancement_model = os.getenv('AI_ENHANCEMENT_MODEL', 'gpt-4o-mini')
        self.ai_enhancement_timeout = int(os.getenv('AI_ENHANCEMENT_TIMEOUT', '15'))
        
        # 🔧 NOUVEAU: Seuils de qualité configurables
        self.quality_threshold_ai = float(os.getenv('EXTRACTION_QUALITY_THRESHOLD', '0.3'))
        self.empty_extraction_threshold = float(os.getenv('EMPTY_EXTRACTION_THRESHOLD', '0.05'))
        
        logger.info(f"🤖 [ExtractorV3.1] Initialisé - JSON STRICT + Pydantic + Robustesse - IA: {'✅' if self.ai_enhancement_enabled else '❌'}")
        logger.info(f"🔧 [ExtractorV3.1] Seuils qualité: AI={self.quality_threshold_ai}, Empty={self.empty_extraction_threshold}")

    async def extract_entities_ai_enhanced(
        self, 
        message: str, 
        language: str = "fr",
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> IntelligentEntities:
        """🔧 EXTRACTION JSON STRICT avec validation Pydantic + Robustesse améliorée"""
        
        # Tentative IA JSON strict si disponible
        if self.ai_enhancement_enabled and OPENAI_AVAILABLE and openai:
            try:
                entities = await self._extract_entities_openai_json_strict_v31(message, language, conversation_context)
                
                # 🔧 CORRIGÉ: Validation post-extraction avec métriques
                quality_metrics = self._analyze_extraction_quality(entities)
                
                logger.info(f"📊 [AI Quality] Métriques - Completion: {quality_metrics.completion_rate}, "
                          f"Confiance: {quality_metrics.average_confidence}, "
                          f"Score: {quality_metrics.quality_score}")
                
                # Décision basée sur les métriques de qualité
                if not quality_metrics.needs_fallback and quality_metrics.quality_score >= self.quality_threshold_ai:
                    logger.info(f"✅ [AI JSON Strict] Extraction acceptée - Score qualité: {quality_metrics.quality_score}")
                    entities.extraction_quality_score = quality_metrics.quality_score
                    return entities.validate_and_correct_safe()
                else:
                    logger.warning(f"⚠️ [AI JSON Strict] Qualité insuffisante - Score: {quality_metrics.quality_score}, "
                                 f"Fallback requis: {quality_metrics.needs_fallback}")
                    
            except Exception as e:
                logger.warning(f"⚠️ [AI JSON Strict] Échec IA: {e}")
        
        # Fallback robuste avec types corrects
        logger.info("🔄 [Fallback] Utilisation extraction basique robuste")
        try:
            entities = await self._extract_entities_basic_robust_safe(message, language)
            entities.extraction_method = "fallback_robust"
            
            # Analyse qualité du fallback aussi
            fallback_quality = self._analyze_extraction_quality(entities)
            entities.extraction_quality_score = fallback_quality.quality_score
            
            logger.info(f"📊 [Fallback Quality] Score: {fallback_quality.quality_score}")
            
            return entities.validate_and_correct_safe()
        except Exception as fallback_error:
            logger.error(f"❌ [Fallback] Échec fallback: {fallback_error}")
            # Fallback ultime: entités vides mais valides
            return self._create_empty_entities_safe("fallback_failed")

    async def _extract_entities_openai_json_strict_v31(
        self, 
        message: str, 
        language: str = "fr",
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> IntelligentEntities:
        """🔧 EXTRACTION OpenAI avec JSON STRICT + Validation post-extraction améliorée"""
        
        try:
            # Contexte pour l'IA (sécurisé)
            context_info = ""
            if conversation_context and conversation_context.consolidated_entities:
                try:
                    existing_entities = conversation_context.consolidated_entities.to_dict_safe()
                    if existing_entities and not existing_entities.get('error'):
                        context_info = f"\n\nEntités déjà connues:\n{json.dumps(existing_entities, ensure_ascii=False, indent=2)}"
                except Exception as context_error:
                    logger.warning(f"⚠️ [OpenAI JSON] Erreur génération contexte: {context_error}")
                    context_info = ""
            
            # 🔧 PROMPT JSON STRICT OBLIGATOIRE amélioré
            extraction_prompt = self._build_json_strict_prompt_v31(message, context_info, language)
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise Exception("Clé API OpenAI manquante")
            
            # Appel OpenAI avec JSON strict
            try:
                client = openai.AsyncOpenAI(api_key=api_key)
                
                response = await client.chat.completions.create(
                    model=self.ai_enhancement_model,
                    messages=[
                        {
                            "role": "system", 
                            "content": "Tu es un extracteur d'entités expert en aviculture. Tu retournes UNIQUEMENT du JSON valide et complet conforme au schéma demandé. JAMAIS de JSON vide {}. Aucun texte additionnel."
                        },
                        {"role": "user", "content": extraction_prompt}
                    ],
                    temperature=0.0,  # Température 0 pour cohérence maximale
                    max_tokens=800,
                    timeout=self.ai_enhancement_timeout,
                    response_format={"type": "json_object"}  # Forcer JSON strict
                )
                
                json_response = response.choices[0].message.content.strip()
                
            except asyncio.TimeoutError:
                raise Exception("Timeout lors de l'appel OpenAI")
            except Exception as e:
                raise Exception(f"Erreur OpenAI: {e}")
            
            # 🔧 PARSING JSON STRICT + Validations améliorées
            try:
                raw_data = json.loads(json_response)
                logger.debug(f"🔍 [OpenAI JSON] Raw data reçue: {raw_data}")
                
                # 🔧 NOUVEAU: Détection JSON vide ou quasi-vide
                if self._is_empty_or_minimal_json(raw_data):
                    logger.warning(f"⚠️ [OpenAI JSON] JSON vide ou minimal détecté: {raw_data}")
                    raise Exception("JSON vide ou minimal retourné par GPT - Fallback requis")
                
                # Validation avec Pydantic
                validated_schema = EntityExtractionSchema(**raw_data)
                logger.debug(f"✅ [OpenAI JSON] Validation Pydantic réussie")
                
                # 🔧 NOUVEAU: Validation post-extraction exhaustive
                validation_result = self._validate_extraction_completeness(validated_schema, raw_data)
                if not validation_result.is_valid:
                    logger.warning(f"⚠️ [OpenAI JSON] Validation post-extraction échouée: {validation_result.issues}")
                    # Continuer mais marquer comme qualité réduite
                
                # Conversion vers IntelligentEntities
                entities = self._convert_schema_to_entities(validated_schema)
                
                # 🔧 NOUVEAU: Ajout métadonnées de validation
                entities.extraction_validation_issues = validation_result.issues if not validation_result.is_valid else []
                entities.extraction_raw_fields_count = len([k for k, v in raw_data.items() if v is not None])
                
                logger.info(f"✅ [OpenAI JSON] Entités créées avec succès - Confiance: {entities.confidence_overall}")
                return entities
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ [OpenAI JSON] Erreur parsing JSON: {e}")
                logger.debug(f"📄 [OpenAI JSON] Réponse reçue: {json_response}")
                raise Exception(f"JSON invalide reçu de GPT: {e}")
                
            except ValidationError as e:
                logger.error(f"❌ [OpenAI JSON] Erreur validation Pydantic: {e}")
                logger.debug(f"📄 [OpenAI JSON] Données invalidées: {raw_data}")
                raise Exception(f"Schéma JSON invalide: {e}")
                
        except Exception as e:
            logger.error(f"❌ [OpenAI JSON] Erreur extraction: {e}")
            return self._create_empty_entities_safe("openai_json_failed")

    def _build_json_strict_prompt_v31(self, message: str, context_info: str, language: str) -> str:
        """🔧 Construction du prompt JSON STRICT avec schéma explicite - VERSION AMÉLIORÉE"""
        
        # Instructions selon la langue
        language_instructions = {
            "fr": {
                "intro": "Analyse ce message agricole en français et extrait les informations sur les poulets.",
                "rules": [
                    "Races courantes: Ross 308, Ross 708, Cobb 500, Cobb 700, Hubbard Flex",
                    "Sexes: 'mâles', 'femelles', 'mixte'",
                    "Convertir automatiquement: semaines → jours (×7), kg → grammes (×1000)",
                    "Âges réalistes: 0-365 jours, 0-52 semaines",
                    "Poids réalistes: 0-10000 grammes",
                    "Mortalité: 0-100%",
                    "JAMAIS de JSON vide {} - toujours remplir au moins extraction_confidence"
                ]
            },
            "en": {
                "intro": "Analyze this agricultural message in English and extract chicken information.",
                "rules": [
                    "Common breeds: Ross 308, Ross 708, Cobb 500, Cobb 700, Hubbard Flex", 
                    "Sexes: 'males', 'females', 'mixed'",
                    "Auto-convert: weeks → days (×7), kg → grams (×1000)",
                    "Realistic ages: 0-365 days, 0-52 weeks",
                    "Realistic weights: 0-10000 grams",
                    "Mortality: 0-100%",
                    "NEVER empty JSON {} - always fill at least extraction_confidence"
                ]
            },
            "es": {
                "intro": "Analiza este mensaje agrícola en español y extrae información sobre pollos.",
                "rules": [
                    "Razas comunes: Ross 308, Ross 708, Cobb 500, Cobb 700, Hubbard Flex",
                    "Sexos: 'machos', 'hembras', 'mixto'", 
                    "Auto-convertir: semanas → días (×7), kg → gramos (×1000)",
                    "Edades realistas: 0-365 días, 0-52 semanas",
                    "Pesos realistas: 0-10000 gramos",
                    "Mortalidad: 0-100%",
                    "NUNCA JSON vacío {} - siempre llenar al menos extraction_confidence"
                ]
            }
        }
        
        lang_config = language_instructions.get(language, language_instructions["fr"])
        
        # 🔧 SCHÉMA JSON EXPLICITE avec validation obligatoire
        json_schema = {
            "breed": "string ou null",
            "breed_type": "'specific' ou 'generic' ou null", 
            "breed_confidence": "float 0.0-1.0 OBLIGATOIRE",
            "sex": "string ou null",
            "sex_confidence": "float 0.0-1.0 OBLIGATOIRE",
            "age_in_days": "int ou null",
            "age_in_weeks": "float ou null",
            "age_confidence": "float 0.0-1.0 OBLIGATOIRE",
            "weight_grams": "float ou null",
            "weight_confidence": "float 0.0-1.0 OBLIGATOIRE",
            "expected_weight_min": "float ou null",
            "expected_weight_max": "float ou null",
            "growth_assessment": "'normal', 'slow', 'fast' ou null",
            "mortality_rate": "float 0.0-100.0 ou null",
            "mortality_confidence": "float 0.0-1.0 OBLIGATOIRE",
            "symptoms": "string ou null",
            "health_status": "'good', 'concern', 'poor' ou null",
            "temperature_celsius": "float ou null",
            "humidity_percent": "float 0.0-100.0 ou null",
            "housing_type": "string ou null",
            "flock_size": "int ou null",
            "feed_type": "string ou null",
            "problem_severity": "'low', 'medium', 'high', 'critical' ou null",
            "intervention_urgency": "'none', 'low', 'medium', 'high' ou null",
            "extraction_confidence": "float 0.0-1.0 OBLIGATOIRE - JAMAIS 0.0"
        }
        
        prompt = f"""
{lang_config['intro']}

MESSAGE À ANALYSER: "{message}"{context_info}

RÈGLES D'EXTRACTION CRITIQUES:
{chr(10).join([f"• {rule}" for rule in lang_config['rules']])}

SCHÉMA JSON OBLIGATOIRE (tous les champs requis):
{json.dumps(json_schema, ensure_ascii=False, indent=2)}

INSTRUCTIONS ULTRA-CRITIQUES:
1. Retourne UNIQUEMENT du JSON valide et COMPLET conforme au schéma
2. TOUS les champs doivent être présents (même avec valeur null)
3. JAMAIS de JSON vide {{}} ou partiel
4. Tous les champs *_confidence sont OBLIGATOIRES (0.1 minimum si info trouvée)
5. extraction_confidence JAMAIS à 0.0 (minimum 0.1 même sans info)
6. Utilise null pour informations manquantes, pas pour champs manquants
7. Respecte les types: int pour entiers, float pour décimaux, string pour texte
8. Si aucune info détectée, garde confidence à 0.1-0.2 mais REMPLIS le schéma complet
9. AUCUN texte additionnel - SEULEMENT le JSON COMPLET

EXEMPLE RÉPONSE MINIMALE VALIDE (si peu d'infos):
{{
  "breed": null,
  "breed_type": null, 
  "breed_confidence": 0.1,
  "sex": null,
  "sex_confidence": 0.1,
  "age_in_days": null,
  "age_in_weeks": null,
  "age_confidence": 0.1,
  "weight_grams": null,
  "weight_confidence": 0.1,
  "expected_weight_min": null,
  "expected_weight_max": null,
  "growth_assessment": null,
  "mortality_rate": null,
  "mortality_confidence": 0.1,
  "symptoms": null,
  "health_status": null,
  "temperature_celsius": null,
  "humidity_percent": null,
  "housing_type": null,
  "flock_size": null,
  "feed_type": null,
  "problem_severity": null,
  "intervention_urgency": null,
  "extraction_confidence": 0.2
}}
"""
        
        return prompt.strip()

    def _is_empty_or_minimal_json(self, data: dict) -> bool:
        """🔧 NOUVEAU: Détecte si le JSON est vide ou quasi-vide"""
        
        try:
            # JSON complètement vide
            if not data or len(data) == 0:
                logger.debug("🔍 [Empty JSON] JSON complètement vide détecté")
                return True
            
            # Compte les champs avec valeurs significatives
            significant_fields = 0
            total_confidence = 0.0
            
            for key, value in data.items():
                if value is not None:
                    if key.endswith('_confidence'):
                        confidence_value = float(value) if value else 0.0
                        total_confidence += confidence_value
                    elif key != 'extraction_confidence':  # Exclure le score global
                        significant_fields += 1
            
            # Seuils de détection
            min_significant_fields = 1
            min_total_confidence = self.empty_extraction_threshold * 10  # Au moins 0.5 si seuil à 0.05
            
            is_empty = (significant_fields < min_significant_fields and total_confidence < min_total_confidence)
            
            if is_empty:
                logger.debug(f"🔍 [Empty JSON] JSON minimal détecté - Champs: {significant_fields}, Confiance totale: {total_confidence}")
            
            return is_empty
            
        except Exception as e:
            logger.warning(f"⚠️ [Empty JSON] Erreur détection JSON vide: {e}")
            return True  # En cas d'erreur, considérer comme vide par sécurité

    def _validate_extraction_completeness(self, schema: EntityExtractionSchema, raw_data: dict) -> ValidationResult:
        """🔧 NOUVEAU: Validation post-extraction exhaustive"""
        
        try:
            issues = []
            expected_fields = set(EntityExtractionSchema.__fields__.keys())
            received_fields = set(raw_data.keys())
            
            # Vérification champs manquants
            missing_fields = expected_fields - received_fields
            if missing_fields:
                issues.append(f"Champs manquants: {missing_fields}")
            
            # Vérification champs supplémentaires (normalement bloqué par Pydantic)
            extra_fields = received_fields - expected_fields
            if extra_fields:
                issues.append(f"Champs supplémentaires non autorisés: {extra_fields}")
            
            # Vérification cohérence âge
            if schema.age_in_days is not None and schema.age_in_weeks is not None:
                calculated_weeks = round(schema.age_in_days / 7, 1)
                if abs(calculated_weeks - schema.age_in_weeks) > 0.2:  # Tolérance 0.2 semaines
                    issues.append(f"Incohérence âge: {schema.age_in_days} jours ≠ {schema.age_in_weeks} semaines")
            
            # Vérification plages de poids attendues
            if (schema.expected_weight_min is not None and 
                schema.expected_weight_max is not None and 
                schema.expected_weight_min > schema.expected_weight_max):
                issues.append(f"Plage poids invalide: min {schema.expected_weight_min} > max {schema.expected_weight_max}")
            
            # Vérification scores de confiance
            confidence_fields = [
                'breed_confidence', 'sex_confidence', 'age_confidence', 
                'weight_confidence', 'mortality_confidence', 'extraction_confidence'
            ]
            
            for field in confidence_fields:
                value = getattr(schema, field)
                if not (0.0 <= value <= 1.0):
                    issues.append(f"Score confiance {field} hors limites: {value}")
            
            # Validation réussie si pas d'issues critiques
            is_valid = len(issues) == 0
            
            return ValidationResult(is_valid=is_valid, issues=issues)
            
        except Exception as e:
            logger.error(f"❌ [Validation] Erreur validation post-extraction: {e}")
            return ValidationResult(is_valid=False, issues=[f"Erreur validation: {e}"])

    def _analyze_extraction_quality(self, entities: IntelligentEntities) -> ExtractionQualityMetrics:
        """🔧 CORRIGÉ: Analyse de la qualité d'extraction avec métriques détaillées"""
        
        try:
            # Collecte des champs et valeurs
            entity_dict = entities.to_dict_safe()
            
            # Exclusion des champs métadonnées pour l'analyse
            metadata_fields = {
                'extraction_method', 'last_ai_update', 'extraction_success', 
                'extraction_quality_score', 'extraction_validation_issues', 'extraction_raw_fields_count'
            }
            
            content_fields = {k: v for k, v in entity_dict.items() 
                            if k not in metadata_fields and not k.startswith('_')}
            
            # Comptage champs peuplés
            total_fields = len(content_fields)
            populated_fields = len([v for v in content_fields.values() if v is not None and v != [] and v != ""])
            empty_fields = total_fields - populated_fields
            
            # Collecte scores de confiance
            confidence_fields = ['breed_confidence', 'sex_confidence', 'age_confidence', 
                               'weight_confidence', 'mortality_confidence', 'confidence_overall']
            
            confidence_scores = []
            for field in confidence_fields:
                try:
                    value = getattr(entities, field, 0.0)
                    if value and value > 0:
                        confidence_scores.append(float(value))
                except (AttributeError, TypeError, ValueError):
                    continue
            
            # 🔧 CORRIGÉ: Création avec TOUS les champs obligatoires
            metrics = ExtractionQualityMetrics(
                total_fields=total_fields,
                populated_fields=populated_fields,
                empty_fields=empty_fields,
                confidence_scores=confidence_scores,
                # Les champs calculés seront remplis par les validators
            )
            
            logger.debug(f"📊 [Quality Analysis] Métriques calculées - "
                        f"Champs: {populated_fields}/{total_fields}, "
                        f"Confiance moyenne: {metrics.average_confidence}, "
                        f"Score qualité: {metrics.quality_score}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ [Quality Analysis] Erreur analyse qualité: {e}")
            # 🔧 CORRIGÉ: Métriques par défaut avec TOUS les champs
            return ExtractionQualityMetrics(
                total_fields=20,
                populated_fields=0,
                empty_fields=20,
                confidence_scores=[],
                completion_rate=0.0,
                average_confidence=0.0,
                quality_score=0.0,
                is_empty_extraction=True,
                is_high_quality=False,
                needs_fallback=True
            )

    def _convert_schema_to_entities(self, schema: EntityExtractionSchema) -> IntelligentEntities:
        """🔧 Conversion schéma Pydantic validé → IntelligentEntities - Version conservée"""
        
        try:
            # Calcul des plages de poids attendues
            expected_weight_range = None
            if schema.expected_weight_min is not None and schema.expected_weight_max is not None:
                expected_weight_range = (schema.expected_weight_min, schema.expected_weight_max)
            
            # Construction des entités avec types garantis par Pydantic
            entities = IntelligentEntities(
                # Race
                breed=schema.breed,
                breed_confidence=schema.breed_confidence,
                breed_type=schema.breed_type,
                
                # Sexe
                sex=schema.sex,
                sex_confidence=schema.sex_confidence,
                
                # Âge (avec synchronisation automatique)
                age=schema.age_in_days,
                age_days=schema.age_in_days,
                age_weeks=schema.age_in_weeks,
                age_confidence=schema.age_confidence,
                age_last_updated=datetime.now(),
                
                # Poids (synchronisé weight et weight_grams)
                weight=schema.weight_grams,
                weight_grams=schema.weight_grams,
                weight_confidence=schema.weight_confidence,
                expected_weight_range=expected_weight_range,
                growth_rate=schema.growth_assessment,
                
                # Santé
                mortality_rate=schema.mortality_rate,
                mortality_confidence=schema.mortality_confidence,
                symptoms=[schema.symptoms] if schema.symptoms else [],
                health_status=schema.health_status,
                
                # Environnement
                temperature=schema.temperature_celsius,
                humidity=schema.humidity_percent,
                housing_type=schema.housing_type,
                
                # Troupeau
                feed_type=schema.feed_type,
                flock_size=schema.flock_size,
                
                # Évaluation
                problem_severity=schema.problem_severity,
                intervention_urgency=schema.intervention_urgency,
                
                # Métadonnées
                extraction_method="openai_json_strict_v31",
                last_ai_update=datetime.now(),
                confidence_overall=schema.extraction_confidence,
                extraction_success=True
            )
            
            logger.debug(f"✅ [Schema Convert] Conversion réussie - Confiance: {entities.confidence_overall}")
            return entities
            
        except Exception as e:
            logger.error(f"❌ [Schema Convert] Erreur conversion: {e}")
            return self._create_empty_entities_safe("conversion_failed")

    async def _extract_entities_basic_robust_safe(self, message: str, language: str) -> IntelligentEntities:
        """🔧 EXTRACTION BASIQUE SÉCURISÉE avec types corrects - Version conservée"""
        
        try:
            entities = await self._extract_entities_basic_robust(message, language)
            entities._force_all_numeric_types()
            return entities
        except Exception as e:
            logger.error(f"❌ [Basic Safe] Erreur extraction basique: {e}")
            return self._create_empty_entities_safe("basic_failed")

    async def _extract_entities_basic_robust(self, message: str, language: str) -> IntelligentEntities:
        """🔧 EXTRACTION BASIQUE avec patterns regex - Version conservée de v3.0"""
        
        try:
            entities = IntelligentEntities(extraction_method="basic_robust")
            message_lower = message.lower()
            
            # Race spécifique
            specific_breeds = [
                r'ross\s*308', r'ross\s*708', r'cobb\s*500', r'cobb\s*700',
                r'hubbard\s*flex', r'arbor\s*acres'
            ]
            
            for pattern in specific_breeds:
                try:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        breed_found = match.group(0).strip().replace(' ', ' ').title()
                        entities.breed = str(breed_found)
                        entities.breed_type = str("specific")
                        entities.breed_confidence = float(0.9)
                        break
                except Exception as breed_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur détection race: {breed_error}")
                    continue
            
            # Sexe
            sex_patterns = {
                "fr": [
                    (r'\bmâles?\b', 'mâles'),
                    (r'\bmales?\b', 'mâles'),
                    (r'\bcoqs?\b', 'mâles'),
                    (r'\bfemelles?\b', 'femelles'),
                    (r'\bfemales?\b', 'femelles'),
                    (r'\bpoules?\b', 'femelles'),
                    (r'\bmixte\b', 'mixte')
                ],
                "en": [
                    (r'\bmales?\b', 'males'),
                    (r'\brooster\b', 'males'),
                    (r'\bfemales?\b', 'females'),
                    (r'\bhens?\b', 'females'),
                    (r'\bmixed?\b', 'mixed')
                ],
                "es": [
                    (r'\bmachos?\b', 'machos'),
                    (r'\bgallos?\b', 'machos'),
                    (r'\bhembras?\b', 'hembras'),
                    (r'\bgallinas?\b', 'hembras'),
                    (r'\bmixto\b', 'mixto')
                ]
            }
            
            patterns = sex_patterns.get(language, sex_patterns["fr"])
            
            for pattern, sex_name in patterns:
                try:
                    if re.search(pattern, message_lower, re.IGNORECASE):
                        entities.sex = str(sex_name)
                        entities.sex_confidence = float(0.8)
                        break
                except Exception as sex_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur détection sexe: {sex_error}")
                    continue
            
            # Âge
            age_patterns = [
                (r'(\d+)\s*jours?', 1, "days"),
                (r'(\d+)\s*semaines?', 7, "weeks"),
                (r'(\d+)\s*days?', 1, "days"),
                (r'(\d+)\s*weeks?', 7, "weeks")
            ]
            
            for pattern, multiplier, unit in age_patterns:
                try:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        value = safe_int_conversion(match.group(1))
                        if value is None:
                            continue
                        
                        if unit == "weeks":
                            age_weeks = float(value)
                            age_days = int(value * 7)
                        else:
                            age_days = int(value)
                            age_weeks = round(value / 7, 1)
                        
                        entities.age_weeks = float(age_weeks)
                        entities.age_days = int(age_days)
                        entities.age = int(age_days)
                        
                        if 0 < age_days <= 365:
                            entities.age_confidence = float(0.8)
                        else:
                            entities.age_confidence = float(0.3)
                        
                        entities.age_last_updated = datetime.now()
                        break
                        
                except Exception as age_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur âge: {age_error}")
                    continue
            
            # Poids
            weight_patterns = [
                (r'(\d+(?:\.\d+)?)\s*g\b', 1, "grams"),
                (r'(\d+(?:\.\d+)?)\s*kg', 1000, "kg"),
                (r'pèsent?\s+(\d+(?:\.\d+)?)', 1, "grams"),
                (r'weigh\s+(\d+(?:\.\d+)?)', 1, "grams")
            ]
            
            for pattern, multiplier, unit in weight_patterns:
                try:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        weight_value = safe_float_conversion(match.group(1))
                        if weight_value is None:
                            continue
                        
                        weight = float(weight_value * multiplier)
                        
                        if weight < 10:
                            weight = float(weight * 1000)
                            weight_confidence = float(0.7)
                        elif weight > 10000:
                            weight_confidence = float(0.3)
                        else:
                            weight_confidence = float(0.8)
                        
                        entities.weight = float(weight)
                        entities.weight_grams = float(weight)
                        entities.weight_confidence = float(weight_confidence)
                        break
                        
                except Exception as weight_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur poids: {weight_error}")
                    continue
            
            # Calcul confiance globale
            confidence_scores = []
            
            if entities.breed_confidence > 0:
                confidence_scores.append(float(entities.breed_confidence))
            if entities.sex_confidence > 0:
                confidence_scores.append(float(entities.sex_confidence))
            if entities.age_confidence > 0:
                confidence_scores.append(float(entities.age_confidence))
            if entities.weight_confidence > 0:
                confidence_scores.append(float(entities.weight_confidence))
            
            if confidence_scores:
                overall_confidence = float(sum(confidence_scores) / len(confidence_scores))
            else:
                overall_confidence = float(0.0)
            
            entities.confidence_overall = float(overall_confidence)
            entities.extraction_success = bool(overall_confidence > 0.1)
            
            logger.info(f"✅ [BasicRobust] Extraction terminée - Confiance: {overall_confidence}")
            
            return entities
            
        except Exception as e:
            logger.error(f"❌ [BasicRobust] Erreur globale: {e}")
            return self._create_empty_entities_safe("basic_robust_failed")

    def _create_empty_entities_safe(self, method: str) -> IntelligentEntities:
        """🔧 Création d'entités vides sécurisées avec types corrects - Version conservée"""
        
        try:
            empty_entities = IntelligentEntities(
                extraction_method=method,
                extraction_success=False,
                confidence_overall=0.0
            )
            empty_entities._force_all_numeric_types()
            return empty_entities
        except Exception as e:
            logger.error(f"❌ [Empty Entities] Erreur création entités vides: {e}")
            # Fallback ultime
            return IntelligentEntities()


class ConversationClarificationHandler:
    """Gestionnaire de clarifications conversationnelles - VERSION JSON STRICT (conservée)"""
    
    def __init__(self):
        logger.info("🔄 [ClarificationHandlerV3.1] Système clarification JSON strict + robustesse initialisé")
    
    def build_enriched_question_from_clarification(
        self,
        original_question: str,
        clarification_response: str,
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> str:
        """Enrichit la question avec clarification - VERSION SÉCURISÉE (conservée)"""
        
        try:
            clarification_lower = clarification_response.lower().strip()
            
            breed_info = self._extract_breed_from_clarification_safe(clarification_lower)
            sex_info = self._extract_sex_from_clarification_safe(clarification_lower)
            
            enrichments = []
            
            if breed_info:
                enrichments.append(str(breed_info))
            
            if sex_info:
                enrichments.append(str(sex_info))
            
            if enrichments:
                enriched_question = self._integrate_enrichments_into_question_safe(
                    original_question, 
                    enrichments
                )
                
                logger.info(f"✅ [Clarification] Question enrichie: {enriched_question}")
                return str(enriched_question)
            else:
                fallback_question = f"{str(original_question)} Contexte: {str(clarification_response)}"
                return str(fallback_question)
                
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur enrichissement: {e}")
            return str(original_question)
    
    def _extract_breed_from_clarification_safe(self, clarification: str) -> Optional[str]:
        """Extraction race sécurisée"""
        try:
            breed = self._extract_breed_from_clarification(clarification)
            return str(breed) if breed else None
        except Exception as e:
            logger.warning(f"⚠️ [Clarification] Erreur extraction race: {e}")
            return None
    
    def _extract_breed_from_clarification(self, clarification: str) -> Optional[str]:
        """Extrait la race de la réponse"""
        breed_patterns = [
            r'ross\s*308', r'ross\s*708', r'cobb\s*500', r'cobb\s*700',
            r'hubbard\s*flex', r'arbor\s*acres'
        ]
        
        for pattern in breed_patterns:
            try:
                match = re.search(pattern, clarification, re.IGNORECASE)
                if match:
                    breed = str(match.group(0).strip().replace(' ', ' ').title())
                    return breed
            except Exception:
                continue
        
        return None
    
    def _extract_sex_from_clarification_safe(self, clarification: str) -> Optional[str]:
        """Extraction sexe sécurisée"""
        try:
            sex = self._extract_sex_from_clarification(clarification)
            return str(sex) if sex else None
        except Exception as e:
            logger.warning(f"⚠️ [Clarification] Erreur extraction sexe: {e}")
            return None
    
    def _extract_sex_from_clarification(self, clarification: str) -> Optional[str]:
        """Extrait le sexe de la réponse"""
        sex_patterns = [
            (r'\bmâles?\b', 'mâles'),
            (r'\bmales?\b', 'mâles'),
            (r'\bcoqs?\b', 'mâles'),
            (r'\bfemelles?\b', 'femelles'),
            (r'\bfemales?\b', 'femelles'),
            (r'\bpoules?\b', 'femelles'),
            (r'\bmixte\b', 'mixte')
        ]
        
        for pattern, sex_name in sex_patterns:
            try:
                if re.search(pattern, clarification, re.IGNORECASE):
                    return str(sex_name)
            except Exception:
                continue
        
        return None
    
    def _integrate_enrichments_into_question_safe(
        self, 
        original_question: str, 
        enrichments: list
    ) -> str:
        """Intégration enrichissements sécurisée"""
        
        try:
            result = self._integrate_enrichments_into_question(original_question, enrichments)
            return str(result)
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur intégration: {e}")
            enrichment_text = ' '.join([str(e) for e in enrichments])
            return str(f"{original_question} (Contexte: {enrichment_text})")
    
    def _integrate_enrichments_into_question(
        self, 
        original_question: str, 
        enrichments: list
    ) -> str:
        """Intègre intelligemment les enrichissements"""
        
        question_patterns = [
            (r'(quel\s+est\s+le\s+poids\s+d.un\s+)poulet(\s+de\s+\d+\s+jours?)',
             r'\1{} \2'),
            (r'(mes\s+)poulets?(\s+de\s+\d+\s+jours?)',
             r'\1{} \2'),
            (r'\bpoulets?\b', '{}')
        ]
        
        enrichment_text = ' '.join([str(e) for e in enrichments])
        
        for pattern, replacement in question_patterns:
            try:
                if re.search(pattern, original_question, re.IGNORECASE):
                    enriched = re.sub(
                        pattern, 
                        replacement.format(enrichment_text),
                        original_question, 
                        flags=re.IGNORECASE
                    )
                    return str(re.sub(r'\s+', ' ', enriched).strip())
            except Exception:
                continue
        
        return str(f"{original_question} (Contexte: {enrichment_text})")
    
    def detect_clarification_state(
        self, 
        conversation_context: IntelligentConversationContext
    ) -> Tuple[bool, Optional[str]]:
        """Détecte l'état de clarification"""
        
        try:
            if hasattr(conversation_context, 'pending_clarification') and conversation_context.pending_clarification:
                try:
                    original_question_msg = conversation_context.find_original_question()
                    if original_question_msg:
                        return bool(True), str(original_question_msg.message)
                except Exception:
                    pass
            
            if (hasattr(conversation_context, 'critical_clarification_active') and 
                conversation_context.critical_clarification_active and 
                hasattr(conversation_context, 'original_question_pending') and
                conversation_context.original_question_pending):
                
                return bool(True), str(conversation_context.original_question_pending)
            
            return bool(False), None
            
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur détection état: {e}")
            return bool(False), None

    def check_if_clarification_needed(
        self,
        question: str,
        rag_response: Any,
        context: Optional[IntelligentConversationContext],
        language: str = "fr"
    ) -> Tuple[bool, List[str]]:
        """Détermine si clarification nécessaire"""
        
        try:
            if not context or not hasattr(context, 'consolidated_entities'):
                return bool(False), []
            
            entities = context.consolidated_entities
            
            try:
                missing_info = entities.get_critical_missing_info()
            except Exception:
                missing_info = []
            
            clarification_questions = []
            
            clarification_messages = {
                "fr": {
                    "breed": "De quelle race de poulets s'agit-il ? (ex: Ross 308, Cobb 500)",
                    "sex": "S'agit-il de mâles, femelles, ou d'un troupeau mixte ?",
                    "age": "Quel est l'âge de vos poulets ?"
                },
                "en": {
                    "breed": "What breed of chickens are we talking about? (e.g., Ross 308, Cobb 500)",
                    "sex": "Are these males, females, or a mixed flock?",
                    "age": "How old are your chickens?"
                },
                "es": {
                    "breed": "¿De qué raza de pollos estamos hablando? (ej: Ross 308, Cobb 500)",
                    "sex": "¿Son machos, hembras, o un lote mixto?",
                    "age": "¿Qué edad tienen sus pollos?"
                }
            }
            
            messages = clarification_messages.get(language, clarification_messages["fr"])
            
            if "breed" in missing_info:
                clarification_questions.append(str(messages["breed"]))
            
            if "sex" in missing_info:
                clarification_questions.append(str(messages["sex"]))
            
            if "age" in missing_info:
                clarification_questions.append(str(messages["age"]))
            
            needs_clarification = bool(len(clarification_questions) > 0 and len(clarification_questions) <= 2)
            clarification_questions_safe = [str(q) for q in clarification_questions[:2]]
            
            return needs_clarification, clarification_questions_safe
            
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur check_if_clarification_needed: {e}")
            return bool(False), []

    def generate_clarification_request(
        self, 
        clarification_questions: List[str], 
        language: str = "fr"
    ) -> str:
        """Génère demande de clarification"""
        
        try:
            if not clarification_questions:
                fallback_messages = {
                    "fr": "Pouvez-vous me donner plus de détails ?",
                    "en": "Can you give me more details?",
                    "es": "¿Puede darme más detalles?"
                }
                return str(fallback_messages.get(language, fallback_messages["fr"]))
            
            intro_messages = {
                "fr": "Pour vous donner une réponse plus précise, j'ai besoin de quelques informations supplémentaires :",
                "en": "To give you a more accurate answer, I need some additional information:",
                "es": "Para darle una respuesta más precisa, necesito información adicional:"
            }
            
            intro = str(intro_messages.get(language, intro_messages["fr"]))
            questions_text = str("\n".join([f"• {q}" for q in clarification_questions]))
            
            return str(f"{intro}\n\n{questions_text}")
            
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur generate_clarification_request: {e}")
            return str("Pouvez-vous me donner plus de détails ?")


# ===============================
# 🔧 RÉSUMÉ DES CORRECTIONS V3.1 APPLIQUÉES
# ===============================

"""
🚀 CORRECTIONS V3.1 appliquées dans conversation_extraction.py:

🔧 PROBLÈME RÉSOLU: "6 validation errors for ExtractionQualityMetrics"

1. CLASSE ExtractionQualityMetrics CORRIGÉE:
   ✅ Tous les champs avec Field() et valeurs par défaut appropriées
   ✅ Champs calculés (completion_rate, average_confidence, quality_score) avec default=0.0
   ✅ Indicateurs booléens (is_empty_extraction, is_high_quality, needs_fallback) avec valeurs par défaut
   ✅ Validators conservés pour calculs automatiques
   ✅ confidence_scores avec default_factory=list

2. FONCTION _analyze_extraction_quality CORRIGÉE:
   ✅ Création ExtractionQualityMetrics avec tous les champs obligatoires fournis
   ✅ Validators Pydantic se chargent des calculs automatiques  
   ✅ Fallback d'erreur avec tous les champs explicites
   ✅ Gestion d'exception robuste avec métriques complètes

3. VALIDATION POST-EXTRACTION CONSERVÉE:
   ✅ ValidationResult classe ajoutée avec is_valid et issues
   ✅ _validate_extraction_completeness fonctionnelle
   ✅ Vérifications cohérence âge, poids, et scores confiance
   ✅ Détection champs manquants/supplémentaires

4. DÉTECTION JSON VIDE CONSERVÉE:
   ✅ _is_empty_or_minimal_json avec seuils configurables
   ✅ Comptage champs significatifs et confiance totale
   ✅ Fallback automatique si JSON quasi-vide détecté

MÉCANISMES DE ROBUSTESSE CONSERVÉS:

✅ Validation exhaustive post-Pydantic 
✅ Métriques quantifiables de qualité
✅ Fallback intelligent basé sur scores
✅ Configuration flexible via variables environnement
✅ Logging détaillé des décisions qualité

PROBLÈMES RÉSOLUS:

❌ Plus d'erreurs "validation errors for ExtractionQualityMetrics"
❌ Plus de champs manquants dans la classe Pydantic
❌ Plus d'échecs de création des métriques de qualité
❌ Plus d'erreurs lors de l'analyse post-extraction

✅ Tous les champs ExtractionQualityMetrics correctement définis
✅ Validators Pydantic fonctionnels pour calculs automatiques
✅ Gestion d'erreur robuste avec fallbacks complets
✅ Métriques de qualité fiables pour décisions IA vs fallback

Cette version corrigée devrait éliminer complètement les erreurs de validation
Pydantic tout en conservant toutes les améliorations de robustesse v3.1.
"""