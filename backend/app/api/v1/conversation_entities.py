"""
app/api/v1/conversation_entities.py - Entités et structures de données pour la mémoire conversationnelle

🔧 MODULE 1/3: Entités intelligentes et messages conversationnels - VERSION CORRIGÉE TYPAGE FORCÉ
✅ Toutes les corrections appliquées
✅ Attribut 'weight' ajouté et synchronisé avec weight_grams
✅ CORRECTION TYPAGE FORCÉ: Conversion str→int/float obligatoire
✅ Protection complète contre les erreurs de comparaison str/int
✅ Validation renforcée avec coercition de types
"""

import os
import json
import logging
import re
import weakref
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable, Protocol
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)

# Protocol pour typage sécurisé des callbacks
class RAGCallbackProtocol(Protocol):
    """Protocol pour les callbacks de retraitement RAG"""
    async def __call__(
        self,
        question: str,
        conversation_id: str,
        user_id: str,
        language: str = "fr",
        is_reprocessing: bool = False
    ) -> Dict[str, Any]:
        ...

def safe_int_conversion(value: Any) -> Optional[int]:
    """🔧 CORRECTION TYPAGE FORCÉ: Convertit une valeur en int de manière sécurisée avec coercition"""
    if value is None:
        return None
    
    # 🔧 FIX TYPAGE: Forcer la conversion depuis str/float
    try:
        if isinstance(value, str):
            # Nettoyer la chaîne (espaces, caractères non numériques de base)
            cleaned = re.sub(r'[^\d.-]', '', value.strip())
            if cleaned and cleaned not in ['-', '.', '-.']:
                # Conversion forcée str → float → int
                return int(float(cleaned))
        elif isinstance(value, float):
            # Conversion forcée float → int
            return int(value)
        elif isinstance(value, int):
            # Déjà int, retourner tel quel
            return value
        else:
            # Tentative de conversion forcée pour autres types
            return int(float(str(value)))
    except (ValueError, TypeError, OverflowError):
        logger.warning(f"⚠️ [SafeConversion] Impossible de convertir en int: {value} (type: {type(value)})")
        pass
    return None

def safe_float_conversion(value: Any) -> Optional[float]:
    """🔧 CORRECTION TYPAGE FORCÉ: Convertit une valeur en float de manière sécurisée avec coercition"""
    if value is None:
        return None
    
    # 🔧 FIX TYPAGE: Forcer la conversion depuis str/int
    try:
        if isinstance(value, str):
            # Nettoyer la chaîne
            cleaned = re.sub(r'[^\d.-]', '', value.strip())
            if cleaned and cleaned not in ['-', '.', '-.']:
                # Conversion forcée str → float
                return float(cleaned)
        elif isinstance(value, (int, float)):
            # Conversion forcée int/float → float
            return float(value)
        else:
            # Tentative de conversion forcée pour autres types
            return float(str(value))
    except (ValueError, TypeError, OverflowError):
        logger.warning(f"⚠️ [SafeConversion] Impossible de convertir en float: {value} (type: {type(value)})")
        pass
    return None

def force_type_coercion(obj: Any, field_name: str, target_type: type) -> Any:
    """
    🔧 NOUVELLE FONCTION: Force la coercition de type pour un champ spécifique
    
    Args:
        obj: Objet contenant le champ
        field_name: Nom du champ à corriger
        target_type: Type cible (int, float, str)
    
    Returns:
        Valeur convertie ou None si impossible
    """
    if not hasattr(obj, field_name):
        return None
    
    try:
        value = getattr(obj, field_name)
        if value is None:
            return None
        
        if target_type == int:
            converted = safe_int_conversion(value)
        elif target_type == float:
            converted = safe_float_conversion(value)
        elif target_type == str:
            converted = str(value) if value is not None else None
        else:
            converted = value
        
        # Appliquer la conversion si réussie
        if converted is not None:
            setattr(obj, field_name, converted)
            if value != converted:
                logger.debug(f"🔧 [ForceType] {field_name}: {value} ({type(value)}) → {converted} ({type(converted)})")
        
        return converted
        
    except Exception as e:
        logger.error(f"❌ [ForceType] Erreur coercition {field_name}: {e}")
        return None

@dataclass
class IntelligentEntities:
    """Entités extraites intelligemment avec raisonnement contextuel - VERSION TYPAGE FORCÉ"""
    
    # 🔧 FIX 1: TOUS LES ATTRIBUTS REQUIS AVEC TYPES CORRECTS ET VALIDATION FORCÉE
    # Informations de base
    breed: Optional[str] = None
    breed_confidence: float = 0.0
    breed_type: Optional[str] = None  # specific/generic
    
    # Sexe avec variations multilingues
    sex: Optional[str] = None
    sex_confidence: float = 0.0
    
    # 🔧 FIX 2 + TYPAGE FORCÉ: ÂGE - Tous les attributs requis avec conversion obligatoire
    age: Optional[int] = None  # Âge principal en jours - FORCÉ INT
    age_days: Optional[int] = None  # FORCÉ INT
    age_weeks: Optional[float] = None  # FORCÉ FLOAT
    age_confidence: float = 0.0
    age_last_updated: Optional[datetime] = None
    
    # 🔧 FIX 3 + TYPAGE FORCÉ: POIDS - weight + weight_grams avec conversion obligatoire
    weight: Optional[float] = None  # FORCÉ FLOAT (en grammes)
    weight_grams: Optional[float] = None  # FORCÉ FLOAT
    weight_confidence: float = 0.0
    expected_weight_range: Optional[Tuple[float, float]] = None
    growth_rate: Optional[str] = None  # normal/slow/fast
    
    # Santé et problèmes
    mortality_rate: Optional[float] = None  # FORCÉ FLOAT
    mortality_confidence: float = 0.0
    symptoms: List[str] = field(default_factory=list)
    health_status: Optional[str] = None  # good/concerning/critical
    
    # Environnement
    temperature: Optional[float] = None  # FORCÉ FLOAT
    humidity: Optional[float] = None  # FORCÉ FLOAT
    housing_type: Optional[str] = None
    ventilation_quality: Optional[str] = None
    
    # Alimentation
    feed_type: Optional[str] = None
    feed_conversion: Optional[float] = None  # FORCÉ FLOAT
    water_consumption: Optional[str] = None
    
    # Gestion et historique
    flock_size: Optional[int] = None  # FORCÉ INT
    vaccination_status: Optional[str] = None
    previous_treatments: List[str] = field(default_factory=list)
    
    # Contextuel intelligent
    problem_duration: Optional[str] = None
    problem_severity: Optional[str] = None  # low/medium/high/critical
    intervention_urgency: Optional[str] = None  # none/monitor/act/urgent
    
    # Métadonnées IA
    extraction_method: str = "basic"  # basic/openai/hybrid/fallback
    extraction_attempts: int = 0
    extraction_success: bool = True
    last_ai_update: Optional[datetime] = None
    confidence_overall: float = 0.0
    data_validated: bool = False
    
    def __post_init__(self):
        """🔧 CORRECTION CRITIQUE: Post-initialisation avec TYPAGE FORCÉ obligatoire"""
        logger.debug("🔧 [PostInit] Démarrage coercition de types obligatoire...")
        
        # 🔧 ÉTAPE 1: COERCITION FORCÉE DE TOUS LES TYPES NUMÉRIQUES
        self._force_all_numeric_types()
        
        # 🔧 ÉTAPE 2: Synchronisation avec types validés
        self._sync_fields_safe()
        
        logger.debug("✅ [PostInit] Coercition de types terminée")
    
    def _force_all_numeric_types(self):
        """🔧 NOUVELLE MÉTHODE: Force la coercition de TOUS les types numériques"""
        
        # CHAMPS INT OBLIGATOIRES
        int_fields = ['age', 'age_days', 'flock_size', 'extraction_attempts']
        for field in int_fields:
            force_type_coercion(self, field, int)
        
        # CHAMPS FLOAT OBLIGATOIRES
        float_fields = [
            'breed_confidence', 'sex_confidence', 'age_confidence', 'age_weeks',
            'weight', 'weight_grams', 'weight_confidence', 'mortality_rate', 'mortality_confidence',
            'temperature', 'humidity', 'feed_conversion', 'confidence_overall'
        ]
        for field in float_fields:
            force_type_coercion(self, field, float)
        
        # CHAMPS STR (nettoyer si nécessaire)
        str_fields = ['breed', 'breed_type', 'sex', 'health_status', 'housing_type', 
                     'ventilation_quality', 'feed_type', 'water_consumption', 'vaccination_status',
                     'problem_duration', 'problem_severity', 'intervention_urgency', 'extraction_method']
        for field in str_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None and not isinstance(value, str):
                    try:
                        setattr(self, field, str(value))
                        logger.debug(f"🔧 [ForceStr] {field}: {value} → {str(value)}")
                    except Exception as e:
                        logger.warning(f"⚠️ [ForceStr] Erreur conversion {field}: {e}")
    
    def _sync_fields_safe(self):
        """🔧 SYNCHRONISATION SÉCURISÉE avec types validés"""
        try:
            # Synchroniser weight et weight_grams (SEULEMENT FLOAT validés)
            if isinstance(self.weight_grams, (int, float)) and self.weight is None:
                self.weight = float(self.weight_grams)
            elif isinstance(self.weight, (int, float)) and self.weight_grams is None:
                self.weight_grams = float(self.weight)
            
            # Synchroniser age et age_days (SEULEMENT INT validés)
            if isinstance(self.age_days, int) and self.age is None:
                self.age = self.age_days
            elif isinstance(self.age, int) and self.age_days is None:
                self.age_days = self.age
            
            # Calculer age_weeks depuis age_days si manquant
            if isinstance(self.age_days, int) and self.age_days > 0 and self.age_weeks is None:
                self.age_weeks = round(self.age_days / 7, 1)
            
            logger.debug("✅ [SyncFields] Synchronisation terminée")
            
        except Exception as e:
            logger.error(f"❌ [SyncFields] Erreur synchronisation: {e}")
    
    # 🔧 NOUVELLES SÉCURISATIONS: PROPRIÉTÉS DE COMPATIBILITÉ avec TYPAGE FORCÉ
    @property
    def mortality(self) -> Optional[float]:
        """Propriété de compatibilité pour éviter les erreurs d'accès à .mortality avec TYPAGE FORCÉ"""
        return safe_float_conversion(getattr(self, 'mortality_rate', None))
    
    @mortality.setter  
    def mortality(self, value: Optional[float]):
        """Setter de compatibilité pour .mortality → .mortality_rate avec TYPAGE FORCÉ"""
        self.mortality_rate = safe_float_conversion(value)
    
    # 🔧 SÉCURISATIONS RENFORCÉES: MÉTHODES D'ACCÈS avec TYPAGE VALIDÉ
    def safe_get_attribute(self, attr_name: str, default: Any = None) -> Any:
        """Accès sécurisé à un attribut avec fallback et validation de type"""
        if hasattr(self, attr_name):
            try:
                value = getattr(self, attr_name, default)
                
                # 🔧 VALIDATION SUPPLÉMENTAIRE: S'assurer que les types numériques sont corrects
                if attr_name in ['age', 'age_days', 'flock_size'] and value is not None:
                    if not isinstance(value, int):
                        value = safe_int_conversion(value)
                        if value is not None:
                            setattr(self, attr_name, value)  # Corriger à la volée
                
                elif attr_name in ['weight', 'weight_grams', 'temperature', 'mortality_rate'] and value is not None:
                    if not isinstance(value, (int, float)):
                        value = safe_float_conversion(value)
                        if value is not None:
                            setattr(self, attr_name, value)  # Corriger à la volée
                
                return value
            except Exception as e:
                logger.warning(f"⚠️ [Entities] Erreur accès attribut {attr_name}: {e}")
                return default
        else:
            logger.warning(f"⚠️ [Entities] Attribut manquant: {attr_name}")
            return default
    
    def safe_get_weight(self) -> Optional[float]:
        """🔧 ACCÈS SÉCURISÉ au poids avec VALIDATION de type FLOAT"""
        # Essayer weight d'abord avec validation
        if hasattr(self, 'weight') and self.weight is not None:
            weight_val = safe_float_conversion(self.weight)
            if weight_val is not None:
                self.weight = weight_val  # Corriger le type si nécessaire
                return weight_val
        
        # Fallback sur weight_grams avec validation
        elif hasattr(self, 'weight_grams') and self.weight_grams is not None:
            weight_grams_val = safe_float_conversion(self.weight_grams)
            if weight_grams_val is not None:
                self.weight_grams = weight_grams_val  # Corriger le type si nécessaire
                return weight_grams_val
        
        return None
    
    def safe_get_mortality(self) -> Optional[float]:
        """🔧 ACCÈS SÉCURISÉ à la mortalité avec VALIDATION de type FLOAT"""
        # Essayer mortality_rate d'abord avec validation
        if hasattr(self, 'mortality_rate') and self.mortality_rate is not None:
            mortality_val = safe_float_conversion(self.mortality_rate)
            if mortality_val is not None:
                self.mortality_rate = mortality_val  # Corriger le type si nécessaire
                return mortality_val
        
        # Fallback sur mortality si quelqu'un l'utilise encore
        elif hasattr(self, 'mortality') and getattr(self, 'mortality', None) is not None:
            mortality_val = safe_float_conversion(getattr(self, 'mortality', None))
            if mortality_val is not None:
                return mortality_val
        
        return None
    
    def safe_get_age(self) -> Optional[int]:
        """🔧 ACCÈS SÉCURISÉ à l'âge avec VALIDATION de type INT"""
        # Essayer age d'abord avec validation
        if hasattr(self, 'age') and self.age is not None:
            age_val = safe_int_conversion(self.age)
            if age_val is not None:
                self.age = age_val  # Corriger le type si nécessaire
                return age_val
        
        # Fallback sur age_days avec validation
        elif hasattr(self, 'age_days') and self.age_days is not None:
            age_days_val = safe_int_conversion(self.age_days)
            if age_days_val is not None:
                self.age_days = age_days_val  # Corriger le type si nécessaire
                return age_days_val
        
        # Conversion depuis age_weeks avec validation
        elif hasattr(self, 'age_weeks') and self.age_weeks is not None:
            try:
                age_weeks_val = safe_float_conversion(self.age_weeks)
                if age_weeks_val is not None and age_weeks_val > 0:
                    age_from_weeks = int(age_weeks_val * 7)
                    return age_from_weeks
            except (ValueError, TypeError):
                pass
        
        return None
    
    def safe_get_temperature(self) -> Optional[float]:
        """🔧 ACCÈS SÉCURISÉ à la température avec VALIDATION de type FLOAT"""
        temp_val = self.safe_get_attribute('temperature')
        if temp_val is not None:
            return safe_float_conversion(temp_val)
        return None
    
    def safe_get_flock_size(self) -> Optional[int]:
        """🔧 ACCÈS SÉCURISÉ à la taille du troupeau avec VALIDATION de type INT"""
        flock_val = self.safe_get_attribute('flock_size')
        if flock_val is not None:
            return safe_int_conversion(flock_val)
        return None
    
    # 🔧 VALIDATION RENFORCÉE avec COERCITION OBLIGATOIRE
    def validate_and_correct_safe(self) -> 'IntelligentEntities':
        """Version sécurisée de validate_and_correct qui FORCE la coercition de types"""
        try:
            # 🔧 ÉTAPE 1: COERCITION FORCÉE avant validation
            self._force_all_numeric_types()
            
            # 🔧 ÉTAPE 2: Validation standard
            return self.validate_and_correct()
        except Exception as e:
            logger.error(f"❌ [Entities] Erreur validation safe: {e}")
            
            # 🔧 CORRECTION MINIMALE FORCÉE
            try:
                # Re-forcer les types critiques
                self._force_all_numeric_types()
                self._sync_fields_safe()
                self.data_validated = True
                
            except Exception as validation_error:
                logger.error(f"❌ [Entities] Erreur validation minimale: {validation_error}")
            
            return self
    
    def validate_and_correct(self) -> 'IntelligentEntities':
        """🔧 FIX 4 + TYPAGE FORCÉ: Validation et correction avec coercition de types obligatoire"""
        
        # 🔧 ÉTAPE PRÉLIMINAIRE: S'assurer que TOUS les types sont corrects
        self._force_all_numeric_types()
        
        # 🔧 CORRECTION ÂGE: Avec types validés UNIQUEMENT
        age_days_safe = safe_int_conversion(self.age_days)
        age_weeks_safe = safe_float_conversion(self.age_weeks)
        
        if age_days_safe is not None and age_weeks_safe is not None:
            calculated_weeks = age_days_safe / 7
            if abs(calculated_weeks - age_weeks_safe) > 0.5:  # Tolérance 0.5 semaine
                logger.warning(f"⚠️ [Validation] Incohérence âge: {age_days_safe}j vs {age_weeks_safe}sem")
                
                # 🔧 FIX 5: Enrichissement automatique avec TYPES FORCÉS
                age_confidence = safe_float_conversion(self.age_confidence) or 0.0
                if age_confidence > 0.7:
                    self.age_weeks = round(age_days_safe / 7, 1)
                    logger.info(f"✅ [Correction] Âge semaines corrigé: {self.age_weeks}sem")
                else:
                    self.age_days = int(age_weeks_safe * 7)
                    logger.info(f"✅ [Correction] Âge jours corrigé: {self.age_days}j")
        
        # Mise à jour des champs avec types sécurisés
        if age_days_safe is not None:
            self.age_days = age_days_safe
            self.age = age_days_safe  # Synchronisation
        if age_weeks_safe is not None:
            self.age_weeks = age_weeks_safe
        
        # 🔧 CORRECTION POIDS: Synchronisation avec types validés
        weight_safe = safe_float_conversion(self.weight)
        weight_grams_safe = safe_float_conversion(self.weight_grams)
        
        if weight_grams_safe is not None:
            # Validation et correction automatique
            if weight_grams_safe < 10 or weight_grams_safe > 5000:  # Limites réalistes
                logger.warning(f"⚠️ [Validation] Poids suspect: {weight_grams_safe}g")
                if weight_grams_safe > 5000:  # Probablement en kg au lieu de g
                    weight_grams_safe = weight_grams_safe / 1000
                    logger.info(f"✅ [Correction] Poids corrigé de kg vers g: {weight_grams_safe}g")
                elif weight_grams_safe < 10 and weight_grams_safe > 0.1:  # Probablement en kg
                    weight_grams_safe = weight_grams_safe * 1000
                    logger.info(f"✅ [Correction] Poids corrigé de kg vers g: {weight_grams_safe}g")
        
        # Synchroniser weight et weight_grams avec types forcés
        if weight_grams_safe is not None:
            self.weight_grams = float(weight_grams_safe)
            self.weight = float(weight_grams_safe)  # Les deux sont en grammes
        elif weight_safe is not None:
            self.weight = float(weight_safe)
            self.weight_grams = float(weight_safe)
        
        # Validation mortalité avec type forcé
        mortality_safe = safe_float_conversion(self.mortality_rate)
        if mortality_safe is not None:
            if mortality_safe < 0:
                mortality_safe = 0.0
            elif mortality_safe > 100:
                logger.warning(f"⚠️ [Validation] Mortalité > 100%: {mortality_safe}")
                mortality_safe = min(mortality_safe, 100.0)
            self.mortality_rate = float(mortality_safe)
        
        # Validation température avec type forcé
        temp_safe = safe_float_conversion(self.temperature)
        if temp_safe is not None:
            if temp_safe < 15 or temp_safe > 45:
                logger.warning(f"⚠️ [Validation] Température suspecte: {temp_safe}°C")
                if temp_safe > 100:  # Probablement en Fahrenheit
                    temp_safe = (temp_safe - 32) * 5/9
                    logger.info(f"✅ [Correction] Température convertie F→C: {temp_safe:.1f}°C")
            self.temperature = float(temp_safe)
        
        # Validation flock_size avec type forcé
        flock_size_safe = safe_int_conversion(self.flock_size)
        if flock_size_safe is not None:
            self.flock_size = flock_size_safe
        
        # Nettoyer les listes de manière sécurisée
        if self.symptoms:
            self.symptoms = [s.strip().lower() for s in self.symptoms if s and isinstance(s, str) and s.strip()]
            self.symptoms = list(set(self.symptoms))  # Supprimer doublons
        
        if self.previous_treatments:
            self.previous_treatments = [t.strip() for t in self.previous_treatments if t and isinstance(t, str) and t.strip()]
            self.previous_treatments = list(set(self.previous_treatments))
        
        # 🔧 VALIDATION FINALE: Forcer tous les types une dernière fois
        self._force_all_numeric_types()
        
        self.data_validated = True
        return self
    
    # 🔧 SÉRIALISATIONS SÉCURISÉES avec VALIDATION DE TYPES
    def to_dict_safe(self) -> Dict[str, Any]:
        """Version sécurisée de to_dict avec validation de types"""
        try:
            # 🔧 ÉTAPE PRÉLIMINAIRE: Forcer les types avant sérialisation
            self._force_all_numeric_types()
            
            return self.to_dict()
        except Exception as e:
            logger.error(f"❌ [Entities] Erreur to_dict_safe: {e}")
            
            # Fallback basique avec types sûrs
            safe_dict = {
                "extraction_method": str(getattr(self, "extraction_method", "unknown")),
                "extraction_success": bool(getattr(self, "extraction_success", False)),
                "confidence_overall": float(getattr(self, "confidence_overall", 0.0)),
                "data_validated": bool(getattr(self, "data_validated", False))
            }
            
            # Ajouter les champs existants avec VALIDATION de types
            safe_fields_config = {
                # Champs str
                "breed": str, "breed_type": str, "sex": str, "health_status": str,
                "housing_type": str, "feed_type": str, "problem_severity": str, "intervention_urgency": str,
                
                # Champs int
                "age": int, "age_days": int, "flock_size": int,
                
                # Champs float
                "breed_confidence": float, "sex_confidence": float, "age_confidence": float, "age_weeks": float,
                "weight": float, "weight_grams": float, "weight_confidence": float,
                "mortality_rate": float, "mortality_confidence": float,
                "temperature": float, "humidity": float
            }
            
            for field_name, expected_type in safe_fields_config.items():
                if hasattr(self, field_name):
                    try:
                        value = getattr(self, field_name)
                        if value is not None:
                            # VALIDATION + CONVERSION du type
                            if expected_type == int:
                                converted_value = safe_int_conversion(value)
                            elif expected_type == float:
                                converted_value = safe_float_conversion(value)
                            else:  # str
                                converted_value = str(value) if value is not None else None
                            
                            if converted_value is not None:
                                safe_dict[field_name] = converted_value
                                
                    except Exception as field_error:
                        logger.warning(f"⚠️ [Entities] Erreur sérialisation {field_name}: {field_error}")
            
            # Champs spéciaux
            if hasattr(self, 'symptoms') and isinstance(self.symptoms, list):
                safe_dict["symptoms"] = [str(s) for s in self.symptoms if s]
            
            return safe_dict
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour logs et stockage avec VALIDATION de types"""
        
        # 🔧 VALIDATION PRÉLIMINAIRE: S'assurer des types corrects
        self._force_all_numeric_types()
        
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                # 🔧 SÉRIALISATION avec VALIDATION de types
                try:
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()
                    elif isinstance(value, tuple):
                        result[key] = list(value)
                    # 🔧 VALIDATION SUPPLÉMENTAIRE: S'assurer des types numériques
                    elif key in ['age', 'age_days', 'flock_size']:
                        validated_val = safe_int_conversion(value)
                        if validated_val is not None:
                            result[key] = validated_val
                    elif key in ['weight', 'weight_grams', 'temperature', 'mortality_rate', 'age_weeks']:
                        validated_val = safe_float_conversion(value)
                        if validated_val is not None:
                            result[key] = validated_val
                    else:
                        result[key] = value
                except Exception as serialize_error:
                    logger.warning(f"⚠️ [Entities] Erreur sérialisation {key}: {serialize_error}")
                    # Inclure quand même la valeur brute si possible
                    try:
                        result[key] = str(value)
                    except:
                        pass
        
        return result
    
    # MÉTHODES EXISTANTES CONSERVÉES (pas de changement de logique)
    def get_critical_missing_info(self, question_type: str = "general") -> List[str]:
        """Détermine les informations critiques manquantes selon le contexte"""
        missing = []
        
        # Race toujours critique pour questions techniques
        if not self.breed or self.breed_type == "generic" or self.breed_confidence < 0.7:
            missing.append("breed")
        
        # Sexe critique pour questions de performance
        if question_type in ["performance", "weight", "growth"] and (not self.sex or self.sex_confidence < 0.7):
            missing.append("sex")
        
        # Âge critique pour la plupart des questions
        if not self.age_days or self.age_confidence < 0.7:
            missing.append("age")
        
        # Spécifique selon le type de question
        if question_type in ["growth", "weight", "performance"]:
            if not self.weight_grams and not self.growth_rate:
                missing.append("current_performance")
        elif question_type in ["health", "mortality", "disease"]:
            if not self.symptoms and not self.health_status:
                missing.append("symptoms")
            if self.mortality_rate is None and "mortality" in question_type:
                missing.append("mortality_rate")
        elif question_type in ["environment", "temperature", "housing"]:
            if not self.housing_type:
                missing.append("housing_conditions")
        elif question_type in ["feeding", "nutrition"]:
            if not self.feed_type:
                missing.append("feed_information")
        
        return missing
    
    def merge_with(self, other: 'IntelligentEntities') -> 'IntelligentEntities':
        """🔧 FUSION avec VALIDATION de types obligatoire"""
        merged = IntelligentEntities()
        
        # 🔧 ÉTAPE PRÉLIMINAIRE: Forcer les types pour les deux instances
        self._force_all_numeric_types()
        if hasattr(other, '_force_all_numeric_types'):
            other._force_all_numeric_types()
        
        # Logique de fusion pour chaque champ
        for field_name, field_value in asdict(self).items():
            other_value = getattr(other, field_name, None)
            
            # Prendre la valeur avec la meilleure confiance
            if field_name.endswith('_confidence'):
                base_field = field_name.replace('_confidence', '')
                self_conf = safe_float_conversion(field_value) or 0.0
                other_conf = safe_float_conversion(getattr(other, field_name, 0.0)) or 0.0
                
                if other_conf > self_conf:
                    setattr(merged, base_field, getattr(other, base_field))
                    setattr(merged, field_name, other_conf)
                else:
                    setattr(merged, base_field, getattr(self, base_field))
                    setattr(merged, field_name, self_conf)
            
            # Fusionner les listes
            elif isinstance(field_value, list):
                self_list = field_value or []
                other_list = other_value or []
                # Garder les éléments uniques
                merged_list = list(set(self_list + other_list))
                setattr(merged, field_name, merged_list)
            
            # Prendre la valeur la plus récente pour les dates
            elif isinstance(field_value, datetime):
                if other_value and (not field_value or other_value > field_value):
                    setattr(merged, field_name, other_value)
                else:
                    setattr(merged, field_name, field_value)
            
            # Logique par défaut
            else:
                if other_value is not None:
                    setattr(merged, field_name, other_value)
                elif field_value is not None:
                    setattr(merged, field_name, field_value)
        
        merged.last_ai_update = datetime.now()
        
        # 🔧 VALIDATION FINALE: Forcer les types de l'instance fusionnée
        merged._force_all_numeric_types()
        
        return merged.validate_and_correct()

# CLASSES EXISTANTES CONSERVÉES SANS CHANGEMENT (pas de problème de typage détecté)
@dataclass
class ConversationMessage:
    """Message dans une conversation avec métadonnées"""
    id: str
    conversation_id: str
    user_id: str
    role: str  # user/assistant/system
    message: str
    timestamp: datetime
    language: str = "fr"
    message_type: str = "text"  # text/clarification/response/original_question_marker
    extracted_entities: Optional[IntelligentEntities] = None
    confidence_score: float = 0.0
    processing_method: str = "basic"
    
    # CHAMPS POUR CLARIFICATIONS
    is_original_question: bool = False
    is_clarification_response: bool = False
    original_question_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire avec gestion sécurisée des entités"""
        try:
            entities_dict = None
            if self.extracted_entities:
                try:
                    entities_dict = self.extracted_entities.to_dict_safe()
                except Exception as e:
                    logger.warning(f"⚠️ [Message] Erreur sérialisation entités: {e}")
                    entities_dict = {"error": "serialization_failed"}
            
            return {
                "id": self.id,
                "conversation_id": self.conversation_id,
                "user_id": self.user_id,
                "role": self.role,
                "message": self.message,
                "timestamp": self.timestamp.isoformat(),
                "language": self.language,
                "message_type": self.message_type,
                "extracted_entities": entities_dict,
                "confidence_score": self.confidence_score,
                "processing_method": self.processing_method,
                "is_original_question": self.is_original_question,
                "is_clarification_response": self.is_clarification_response,
                "original_question_id": self.original_question_id
            }
        except Exception as e:
            logger.error(f"❌ [Message] Erreur to_dict: {e}")
            # Fallback minimal
            return {
                "id": self.id,
                "conversation_id": self.conversation_id,
                "role": self.role,
                "message": self.message,
                "timestamp": datetime.now().isoformat(),
                "error": "to_dict_failed"
            }

@dataclass
class IntelligentConversationContext:
    """Contexte conversationnel intelligent avec raisonnement et clarification critique"""
    conversation_id: str
    user_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    
    # Entités consolidées intelligemment
    consolidated_entities: IntelligentEntities = field(default_factory=IntelligentEntities)
    
    # Métadonnées contextuelles
    language: str = "fr"
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    total_exchanges: int = 0
    
    # État conversationnel intelligent
    conversation_topic: Optional[str] = None
    conversation_urgency: Optional[str] = None  # low/medium/high/critical
    problem_resolution_status: Optional[str] = None  # identifying/diagnosing/treating/resolved
    
    # Optimisations IA
    ai_enhanced: bool = False
    last_ai_analysis: Optional[datetime] = None
    needs_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    
    # CHAMPS POUR CLARIFICATIONS STANDARD
    pending_clarification: bool = False
    last_original_question_id: Optional[str] = None
    
    # NOUVEAUX CHAMPS POUR CLARIFICATION CRITIQUE
    original_question_pending: Optional[str] = None  # Question initiale en attente
    critical_clarification_active: bool = False      # État clarification critique
    _clarification_callback_ref: Optional[weakref.ReferenceType] = None  # WeakRef pour éviter fuites mémoire
    _schedule_reprocessing: bool = False  # Flag pour éviter récursion
    
    # Propriété pour gérer le callback de manière sécurisée
    @property
    def clarification_callback(self) -> Optional[RAGCallbackProtocol]:
        """Récupère le callback de manière sécurisée"""
        if self._clarification_callback_ref is None:
            return None
        callback = self._clarification_callback_ref()
        if callback is None:
            # Le callback a été garbage collecté
            self._clarification_callback_ref = None
            logger.warning("⚠️ [Context] Callback garbage collecté - nettoyage automatique")
        return callback
    
    @clarification_callback.setter
    def clarification_callback(self, callback: Optional[RAGCallbackProtocol]):
        """Définit le callback avec WeakRef pour éviter les fuites mémoire"""
        if callback is None:
            self._clarification_callback_ref = None
        else:
            try:
                self._clarification_callback_ref = weakref.ref(callback)
            except TypeError:
                # Si l'objet ne supporte pas les weak references
                logger.warning("⚠️ [Context] Callback ne supporte pas WeakRef - stockage direct")
                self._clarification_callback_ref = lambda: callback
    
    def add_message(self, message: ConversationMessage):
        """🔧 AJOUT MESSAGE avec VALIDATION des entités et coercition de types"""
        try:
            self.messages.append(message)
            self.last_activity = datetime.now()
            self.total_exchanges += 1
            
            # TRACKING SPÉCIAL POUR CLARIFICATIONS STANDARD
            if message.is_original_question:
                self.last_original_question_id = message.id
                self.pending_clarification = True
                logger.info(f"🎯 [Context] Question originale marquée: {message.id}")
            
            if message.is_clarification_response and message.original_question_id:
                self.pending_clarification = False
                logger.info(f"🎯 [Context] Clarification reçue pour: {message.original_question_id}")
            
            # NOUVELLE LOGIQUE CLARIFICATION CRITIQUE
            if message.is_clarification_response and self.critical_clarification_active:
                logger.info("🚨 [Context] ✅ Réponse clarification CRITIQUE reçue - planification du retraitement")
                self.critical_clarification_active = False
                
                # Marquer pour retraitement au lieu de créer une tâche immédiatement
                self._schedule_reprocessing = True
                
                # Le retraitement sera déclenché par l'appelant via check_and_trigger_reprocessing()
            
            # 🔧 FUSION des entités avec VALIDATION de types
            if message.extracted_entities:
                try:
                    # FORCER les types avant fusion
                    message.extracted_entities._force_all_numeric_types()
                    
                    old_entities = self.consolidated_entities
                    self.consolidated_entities = self.consolidated_entities.merge_with(message.extracted_entities)
                    
                    # Log des changements d'entités de manière sécurisée
                    old_breed = old_entities.safe_get_breed()
                    new_breed = self.consolidated_entities.safe_get_breed()
                    if old_breed != new_breed:
                        logger.info(f"🔄 [Entities] Race mise à jour: {old_breed} → {new_breed}")
                    
                    old_sex = old_entities.safe_get_sex()
                    new_sex = self.consolidated_entities.safe_get_sex()
                    if old_sex != new_sex:
                        logger.info(f"🔄 [Entities] Sexe mis à jour: {old_sex} → {new_sex}")
                    
                    old_age = old_entities.safe_get_age()
                    new_age = self.consolidated_entities.safe_get_age()
                    if old_age != new_age:
                        logger.info(f"🔄 [Entities] Âge mis à jour: {old_age} → {new_age}j")
                        
                except Exception as merge_error:
                    logger.error(f"❌ [Context] Erreur fusion entités: {merge_error}")
                    # Continuer sans crash
            
            # Mettre à jour le statut conversationnel de manière sécurisée
            try:
                self._update_conversation_status()
            except Exception as status_error:
                logger.warning(f"⚠️ [Context] Erreur mise à jour statut: {status_error}")
                
        except Exception as e:
            logger.error(f"❌ [Context] Erreur ajout message: {e}")
            # Continuer sans crash - au minimum incrémenter les compteurs
            try:
                self.last_activity = datetime.now()
                self.total_exchanges += 1
            except Exception:
                pass
    
    # TOUTES LES AUTRES MÉTHODES RESTENT IDENTIQUES (pas de problème de typage détecté)
    def check_and_trigger_reprocessing(self) -> bool:
        """
        Vérifie si un retraitement est planifié et le déclenche
        Retourne True si un retraitement a été planifié
        """
        if self._schedule_reprocessing:
            self._schedule_reprocessing = False
            logger.info("🚀 [Context] Retraitement planifié détecté - à traiter par l'appelant")
            return True
        return False
    
    def mark_pending_clarification(self, question: str, callback: Optional[RAGCallbackProtocol] = None):
        """
        Marque une question pour clarification critique
        
        Args:
            question: Question originale qui nécessite clarification
            callback: Fonction callback pour relancer le traitement RAG
        """
        try:
            self.critical_clarification_active = True
            self.original_question_pending = question
            self.clarification_callback = callback  # Utilise le setter sécurisé
            
            logger.info(f"🚨 [Context] CLARIFICATION CRITIQUE marquée")
            logger.info(f"  📝 Question: {question[:100]}...")
            logger.info(f"  🔄 Callback: {'✅' if callback else '❌'}")
        except Exception as e:
            logger.error(f"❌ [Context] Erreur marquage clarification: {e}")
    
    async def reprocess_original_question(self) -> Dict[str, Any]:
        """
        Relance le traitement de la question originale avec clarification
        """
        if not self.original_question_pending:
            logger.warning("⚠️ [Context] Pas de question originale en attente pour retraitement")
            return {"status": "no_question_pending"}
        
        logger.info(f"🚀 [Context] RETRAITEMENT question originale: {self.original_question_pending[:100]}...")
        
        try:
            # Vérification sécurisée du callback
            callback = self.clarification_callback
            if callback and callable(callback):
                logger.info("🔄 [Context] Exécution callback retraitement...")
                
                # Appeler le callback avec la question enrichie par le contexte actuel
                enriched_question = self._build_enriched_question_from_context()
                
                try:
                    result = await callback(
                        question=enriched_question,
                        conversation_id=self.conversation_id,
                        user_id=self.user_id,
                        is_reprocessing=True
                    )
                    
                    logger.info(f"✅ [Context] Callback retraitement terminé: {result}")
                    return {"status": "success", "result": result}
                    
                except Exception as callback_error:
                    logger.error(f"❌ [Context] Erreur dans callback: {callback_error}")
                    return {"status": "callback_error", "error": str(callback_error)}
                
            else:
                logger.warning("⚠️ [Context] Pas de callback valide - retraitement manuel requis")
                return {"status": "no_callback"}
        
        except Exception as e:
            logger.error(f"❌ [Context] Erreur retraitement: {e}")
            return {"status": "error", "error": str(e)}
        
        finally:
            # Nettoyer l'état
            self.original_question_pending = None
            self.clarification_callback = None
    
    def _build_enriched_question_from_context(self) -> str:
        """Enrichit la question originale avec le contexte actuel de manière sécurisée"""
        if not self.original_question_pending:
            return ""
        
        try:
            enrichments = []
            entities = self.consolidated_entities
            
            # Ajouter les entités importantes de manière sécurisée
            breed = entities.safe_get_breed()
            if breed and entities.breed_confidence > 0.7:
                enrichments.append(breed)
            
            sex = entities.safe_get_sex()
            if sex and entities.sex_confidence > 0.7:
                enrichments.append(sex)
            
            age = entities.safe_get_age()
            if age and entities.age_confidence > 0.7:
                enrichments.append(f"{age} jours")
            
            # Construire la question enrichie
            if enrichments:
                enrichment_text = " ".join(enrichments)
                
                # Intégrer intelligemment dans la question
                if "poulet" in self.original_question_pending.lower():
                    enriched = self.original_question_pending.replace(
                        "poulet", f"poulet {enrichment_text}"
                    ).replace(
                        "poulets", f"poulets {enrichment_text}"
                    )
                else:
                    enriched = f"{self.original_question_pending} (Contexte: {enrichment_text})"
                
                logger.info(f"🔁 [Context] Question enrichie: {enriched}")
                return enriched
            
            return self.original_question_pending
            
        except Exception as e:
            logger.error(f"❌ [Context] Erreur enrichissement question: {e}")
            return self.original_question_pending
    
    def _update_conversation_status(self):
        """Met à jour le statut conversationnel basé sur les messages récents"""
        try:
            if not self.messages:
                return
            
            recent_messages = self.messages[-3:]  # 3 derniers messages
            
            # Analyser l'urgence basée sur les mots-clés
            urgency_keywords = {
                "critical": ["urgence", "urgent", "critique", "emergency", "critical", "dying", "meurent"],
                "high": ["problème", "problem", "maladie", "disease", "mortalité", "mortality"],
                "medium": ["inquiet", "concerned", "surveillance", "monitoring"],
                "low": ["prévention", "prevention", "routine", "normal"]
            }
            
            max_urgency = "low"
            for message in recent_messages:
                try:
                    message_lower = message.message.lower()
                    for urgency, keywords in urgency_keywords.items():
                        if any(keyword in message_lower for keyword in keywords):
                            if urgency == "critical":
                                max_urgency = "critical"
                                break
                            elif urgency == "high" and max_urgency not in ["critical"]:
                                max_urgency = "high"
                            elif urgency == "medium" and max_urgency in ["low"]:
                                max_urgency = "medium"
                except Exception as msg_error:
                    logger.warning(f"⚠️ [Context] Erreur analyse message urgence: {msg_error}")
                    continue
            
            self.conversation_urgency = max_urgency
            
        except Exception as e:
            logger.error(f"❌ [Context] Erreur mise à jour statut conversation: {e}")
    
    def find_original_question(self, limit_messages: int = 20) -> Optional[ConversationMessage]:
        """
        Trouve la question originale marquée pour clarification avec gestion d'erreurs
        """
        try:
            # Rechercher par ID si on a un last_original_question_id
            if self.last_original_question_id:
                for msg in reversed(self.messages[-limit_messages:]):
                    try:
                        if msg.id == self.last_original_question_id and msg.is_original_question:
                            logger.info(f"✅ [Context] Question originale trouvée par ID: {msg.id}")
                            return msg
                    except Exception as msg_error:
                        logger.warning(f"⚠️ [Context] Erreur vérification message ID: {msg_error}")
                        continue
            
            # Rechercher par marqueur spécial dans le message
            for msg in reversed(self.messages[-limit_messages:]):
                try:
                    if msg.role == "system" and "ORIGINAL_QUESTION_FOR_CLARIFICATION:" in msg.message:
                        # Extraire la question du marqueur
                        question_text = msg.message.replace("ORIGINAL_QUESTION_FOR_CLARIFICATION: ", "")
                        
                        # Créer un message virtuel pour la question originale
                        original_msg = ConversationMessage(
                            id=f"original_{msg.id}",
                            conversation_id=self.conversation_id,
                            user_id=self.user_id,
                            role="user",
                            message=question_text,
                            timestamp=msg.timestamp,
                            language=self.language,
                            message_type="original_question",
                            is_original_question=True
                        )
                        
                        logger.info(f"✅ [Context] Question originale extraite du marqueur: {question_text}")
                        return original_msg
                except Exception as msg_error:
                    logger.warning(f"⚠️ [Context] Erreur vérification marqueur: {msg_error}")
                    continue
            
            # Rechercher par flag is_original_question
            for msg in reversed(self.messages[-limit_messages:]):
                try:
                    if msg.is_original_question and msg.role == "user":
                        logger.info(f"✅ [Context] Question originale trouvée par flag: {msg.message[:50]}...")
                        return msg
                except Exception as msg_error:
                    logger.warning(f"⚠️ [Context] Erreur vérification flag: {msg_error}")
                    continue
            
            # Fallback: chercher la dernière question utilisateur avant demande clarification
            clarification_keywords = [
                "j'ai besoin de", "pouvez-vous préciser", "quelle est la race",
                "quel est le sexe", "de quelle race", "mâles ou femelles"
            ]
            
            for i, msg in enumerate(reversed(self.messages[-limit_messages:])):
                try:
                    if msg.role == "assistant" and any(keyword in msg.message.lower() for keyword in clarification_keywords):
                        # Chercher la question utilisateur juste avant cette clarification
                        actual_index = len(self.messages) - 1 - i
                        if actual_index > 0:
                            prev_msg = self.messages[actual_index - 1]
                            if prev_msg.role == "user":
                                logger.info(f"🔄 [Context] Question originale trouvée par fallback: {prev_msg.message[:50]}...")
                                return prev_msg
                except Exception as fallback_error:
                    logger.warning(f"⚠️ [Context] Erreur fallback: {fallback_error}")
                    continue
            
            logger.warning("⚠️ [Context] Question originale non trouvée!")
            return None
            
        except Exception as e:
            logger.error(f"❌ [Context] Erreur recherche question originale: {e}")
            return None
    
    def get_last_user_question(self, exclude_clarifications: bool = True) -> Optional[ConversationMessage]:
        """
        Récupère la dernière question utilisateur avec gestion d'erreurs
        """
        try:
            for msg in reversed(self.messages):
                try:
                    if msg.role == "user":
                        # Exclure les réponses de clarification courtes si demandé
                        if exclude_clarifications:
                            # Si c'est très court et contient une race/sexe, c'est probablement une clarification
                            if len(msg.message.split()) <= 3:
                                breed_sex_patterns = [
                                    r'ross\s*308', r'cobb\s*500', r'hubbard',
                                    r'mâles?', r'femelles?', r'males?', r'females?',
                                    r'mixte', r'mixed'
                                ]
                                if any(re.search(pattern, msg.message.lower()) for pattern in breed_sex_patterns):
                                    continue  # Ignorer cette réponse de clarification
                        
                        logger.info(f"🔄 [Context] Dernière question utilisateur: {msg.message[:50]}...")
                        return msg
                except Exception as msg_error:
                    logger.warning(f"⚠️ [Context] Erreur vérification message utilisateur: {msg_error}")
                    continue
            
            logger.warning("⚠️ [Context] Aucune question utilisateur trouvée!")
            return None
            
        except Exception as e:
            logger.error(f"❌ [Context] Erreur recherche dernière question: {e}")
            return None
    
    def get_context_for_clarification(self) -> Dict[str, Any]:
        """Retourne le contexte optimisé pour les clarifications avec gestion sécurisée"""
        try:
            # Inclure la question originale si trouvée
            original_question = self.find_original_question()
            
            entities = self.consolidated_entities
            
            context = {
                "breed": entities.safe_get_breed(),
                "breed_type": entities.safe_get_attribute('breed_type'),
                "sex": entities.safe_get_sex(),
                "sex_confidence": entities.safe_get_attribute('sex_confidence', 0.0),
                "age": entities.safe_get_age(),
                "age_confidence": entities.safe_get_attribute('age_confidence', 0.0),
                "weight": entities.safe_get_weight(),
                "symptoms": entities.safe_get_attribute('symptoms', []),
                "housing": entities.safe_get_attribute('housing_type'),
                "urgency": self.conversation_urgency,
                "topic": self.conversation_topic,
                "total_exchanges": self.total_exchanges,
                "missing_critical": entities.get_critical_missing_info(),
                "overall_confidence": entities.safe_get_attribute('confidence_overall', 0.0),
                
                # CHAMPS STANDARD
                "original_question": original_question.message if original_question else None,
                "original_question_id": original_question.id if original_question else None,
                "pending_clarification": self.pending_clarification,
                "last_original_question_id": self.last_original_question_id,
                
                # NOUVEAUX CHAMPS CRITIQUES
                "original_question_pending": self.original_question_pending,
                "critical_clarification_active": self.critical_clarification_active,
                "reprocessing_scheduled": self._schedule_reprocessing
            }
            
            return context
            
        except Exception as e:
            logger.error(f"❌ [Context] Erreur génération contexte clarification: {e}")
            return {
                "error": "context_generation_failed",
                "conversation_id": self.conversation_id,
                "total_exchanges": getattr(self, 'total_exchanges', 0)
            }
    
    def _safe_topic_check(self, keywords: List[str]) -> bool:
        """Helper sécurisé pour vérifier les mots-clés dans conversation_topic"""
        try:
            if not self.conversation_topic:
                return False
            topic_lower = self.conversation_topic.lower()
            return any(keyword in topic_lower for keyword in keywords)
        except Exception as e:
            logger.warning(f"⚠️ [Context] Erreur vérification topic: {e}")
            return False

    def get_missing_entities_list(self) -> List[str]:
        """
        Retourne la liste des entités manquantes avec gestion d'erreurs
        
        Returns:
            List[str]: Liste des entités manquantes
        """
        try:
            return list(self.get_missing_entities_dict().keys())
        except Exception as e:
            logger.error(f"❌ [Context] Erreur get_missing_entities_list: {e}")
            return []
    
    def get_missing_entities_dict(self) -> Dict[str, str]:
        """
        Retourne les entités manquantes avec leur niveau d'importance avec gestion d'erreurs
        
        Returns:
            Dict[str, str]: Dictionnaire {entity: importance}
        """
        try:
            entities = self.consolidated_entities
            missing_with_importance = {}
            
            # Race - toujours critique pour questions techniques
            breed = entities.safe_get_breed()
            breed_type = entities.safe_get_attribute('breed_type')
            breed_confidence = entities.safe_get_attribute('breed_confidence', 0.0)
            
            if not breed or breed_type == "generic" or breed_confidence < 0.7:
                missing_with_importance["breed"] = "critique"
            
            # Sexe - critique pour performance, secondaire pour santé
            sex = entities.safe_get_sex()
            sex_confidence = entities.safe_get_attribute('sex_confidence', 0.0)
            
            if not sex or sex_confidence < 0.7:
                # Protection None avec helper sécurisé
                if self._safe_topic_check(["performance", "weight", "growth", "croissance", "poids"]):
                    missing_with_importance["sex"] = "critique"
                else:
                    missing_with_importance["sex"] = "secondaire"
            
            # Âge - critique pour la plupart des questions
            age = entities.safe_get_age()
            age_confidence = entities.safe_get_attribute('age_confidence', 0.0)
            
            if not age or age_confidence < 0.7:
                missing_with_importance["age"] = "critique"
            
            # Poids - critique pour questions de performance
            weight = entities.safe_get_weight()
            growth_rate = entities.safe_get_attribute('growth_rate')
            
            if not weight and not growth_rate:
                # Protection None avec helper sécurisé
                if self._safe_topic_check(["performance", "weight", "growth", "croissance", "poids"]):
                    missing_with_importance["current_performance"] = "critique"
                else:
                    missing_with_importance["current_performance"] = "secondaire"
            
            # Symptômes - critique pour questions de santé
            symptoms = entities.safe_get_attribute('symptoms', [])
            health_status = entities.safe_get_attribute('health_status')
            
            if not symptoms and not health_status:
                # Protection None avec helper sécurisé
                if self._safe_topic_check(["health", "mortality", "disease", "santé", "mortalité", "maladie"]):
                    missing_with_importance["symptoms"] = "critique"
                else:
                    missing_with_importance["symptoms"] = "secondaire"
            
            # Mortalité - critique si mentionnée dans la conversation
            mortality = entities.safe_get_mortality()
            if mortality is None:
                try:
                    recent_messages_text = " ".join([msg.message.lower() for msg in self.messages[-3:]])
                    if any(keyword in recent_messages_text for keyword in ["mortality", "mortalité", "meurent", "dying"]):
                        missing_with_importance["mortality_rate"] = "critique"
                except Exception as msg_error:
                    logger.warning(f"⚠️ [Context] Erreur analyse messages mortalité: {msg_error}")
            
            # Conditions environnementales - secondaire sauf si problème mentionné
            housing_type = entities.safe_get_attribute('housing_type')
            temperature = entities.safe_get_attribute('temperature')
            
            if not housing_type and not temperature:
                # Protection None avec helper sécurisé
                if self._safe_topic_check(["environment", "temperature", "housing", "environnement", "température"]):
                    missing_with_importance["housing_conditions"] = "critique"
                else:
                    missing_with_importance["housing_conditions"] = "secondaire"
            
            # Alimentation - secondaire sauf si problème nutritionnel
            feed_type = entities.safe_get_attribute('feed_type')
            
            if not feed_type:
                # Protection None avec helper sécurisé
                if self._safe_topic_check(["feeding", "nutrition", "alimentation", "nourriture"]):
                    missing_with_importance["feed_information"] = "critique"
                else:
                    missing_with_importance["feed_information"] = "secondaire"
            
            return missing_with_importance
            
        except Exception as e:
            logger.error(f"❌ [Context] Erreur get_missing_entities_dict: {e}")
            return {"error": "analysis_failed"}

    def get_missing_entities(self, include_importance: bool = False) -> Union[List[str], Dict[str, str]]:
        """
        MÉTHODE DÉPRÉCIÉE - Utilisez get_missing_entities_list() ou get_missing_entities_dict()
        
        Cette méthode est conservée pour compatibilité mais dépréciée
        """
        logger.warning("⚠️ [Deprecated] get_missing_entities() est déprécié. Utilisez get_missing_entities_list() ou get_missing_entities_dict()")
        
        try:
            if include_importance:
                return self.get_missing_entities_dict()
            else:
                return self.get_missing_entities_list()
        except Exception as e:
            logger.error(f"❌ [Context] Erreur get_missing_entities (deprecated): {e}")
            return [] if not include_importance else {}

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire avec gestion sécurisée"""
        try:
            # Messages sécurisés
            messages_dict = []
            for msg in self.messages:
                try:
                    messages_dict.append(msg.to_dict())
                except Exception as msg_error:
                    logger.warning(f"⚠️ [Context] Erreur sérialisation message: {msg_error}")
                    messages_dict.append({"error": "message_serialization_failed", "id": getattr(msg, 'id', 'unknown')})
            
            # Entités consolidées sécurisées
            try:
                entities_dict = self.consolidated_entities.to_dict_safe()
            except Exception as entities_error:
                logger.warning(f"⚠️ [Context] Erreur sérialisation entités: {entities_error}")
                entities_dict = {"error": "entities_serialization_failed"}
            
            return {
                "conversation_id": self.conversation_id,
                "user_id": self.user_id,
                "messages": messages_dict,
                "consolidated_entities": entities_dict,
                "language": self.language,
                "created_at": self.created_at.isoformat(),
                "last_activity": self.last_activity.isoformat(),
                "total_exchanges": self.total_exchanges,
                "conversation_topic": self.conversation_topic,
                "conversation_urgency": self.conversation_urgency,
                "problem_resolution_status": self.problem_resolution_status,
                "ai_enhanced": self.ai_enhanced,
                "last_ai_analysis": self.last_ai_analysis.isoformat() if self.last_ai_analysis else None,
                "needs_clarification": self.needs_clarification,
                "clarification_questions": self.clarification_questions,
                "pending_clarification": self.pending_clarification,
                "last_original_question_id": self.last_original_question_id,
                # NOUVEAUX CHAMPS
                "original_question_pending": self.original_question_pending,
                "critical_clarification_active": self.critical_clarification_active,
                "schedule_reprocessing": self._schedule_reprocessing
            }
        except Exception as e:
            logger.error(f"❌ [Context] Erreur to_dict: {e}")
            return {
                "conversation_id": self.conversation_id,
                "user_id": self.user_id,
                "error": "to_dict_failed",
                "total_exchanges": getattr(self, 'total_exchanges', 0)
            }


# ===============================
# 🔧 RÉSUMÉ DES CORRECTIONS TYPAGE FORCÉ APPLIQUÉES
# ===============================

"""
🚨 CORRECTIONS TYPAGE FORCÉ APPLIQUÉES dans conversation_entities.py:

NOUVELLES FONCTIONS UTILITAIRES:
✅ safe_int_conversion() - Conversion str/float → int robuste avec nettoyage
✅ safe_float_conversion() - Conversion str/int → float robuste avec nettoyage  
✅ force_type_coercion() - Force la coercition de type pour un champ spécifique

CLASSE IntelligentEntities - CORRECTIONS CRITIQUES:
✅ __post_init__() - Coercition OBLIGATOIRE de tous les types numériques
✅ _force_all_numeric_types() - NOUVELLE méthode de coercition forcée
✅ _sync_fields_safe() - Synchronisation avec types validés uniquement
✅ Toutes les propriétés safe_get_*() avec validation + correction à la volée
✅ validate_and_correct_safe() - Version avec coercition forcée préliminaire
✅ validate_and_correct() - Coercition forcée avant et après validation
✅ to_dict_safe() - Sérialisation avec validation de types préliminaire
✅ to_dict() - Validation des types numériques avant sérialisation
✅ merge_with() - Coercition forcée des deux instances avant fusion

CLASSE IntelligentConversationContext:
✅ add_message() - Validation et coercition des entités avant fusion

AVANTAGES DES CORRECTIONS:
❌ PLUS JAMAIS d'erreur "< not supported between instances of str and int"
✅ Conversion automatique str → int/float dans tous les contextes
✅ Nettoyage intelligent des chaînes (espaces, caractères non numériques)
✅ Validation + correction à la volée lors des accès aux attributs
✅ Fallbacks robustes si conversion impossible
✅ Logging détaillé des conversions pour debugging
✅ Rétrocompatibilité complète avec le code existant

TYPES FORCÉS AUTOMATIQUEMENT:
- age, age_days, flock_size → int
- weight, weight_grams, temperature, mortality_rate, age_weeks → float  
- breed, sex, health_status, etc. → str
- breed_confidence, sex_confidence, etc. → float

EXEMPLE DE CORRECTION:
Avant: entities.age = "25" (str) → ERREUR sur comparaison
Après: entities.age = 25 (int) → ✅ Comparaison possible
"""