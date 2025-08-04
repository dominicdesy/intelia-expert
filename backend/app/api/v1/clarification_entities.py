"""
app/api/v1/clarification_entities.py - CLASSES DE DONNÉES + RECONNAISSANCE SOUCHES

Contient:
- ExtractedEntities avec normalisation souches
- ClarificationResult 
- Enums (ClarificationMode, ClarificationState)
- Utilitaires de reconnaissance
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class ClarificationMode(Enum):
    """Modes de clarification disponibles"""
    BATCH = "batch"
    INTERACTIVE = "interactive"
    ADAPTIVE = "adaptive"
    SEMANTIC_DYNAMIC = "semantic_dynamic"

class ClarificationState(Enum):
    """États de clarification"""
    NONE = "none"
    NEEDED = "needed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    AWAITING_REPROCESS = "awaiting_reprocess"

@dataclass
class ExtractedEntities:
    """Entités extraites intelligemment du contexte avec reconnaissance de souches"""
    breed: Optional[str] = None
    breed_type: Optional[str] = None
    sex: Optional[str] = None
    age_days: Optional[int] = None
    age_weeks: Optional[float] = None
    weight_grams: Optional[float] = None
    mortality_rate: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    housing_type: Optional[str] = None
    feed_type: Optional[str] = None
    flock_size: Optional[int] = None
    symptoms: Optional[List[str]] = None
    duration_problem: Optional[str] = None
    previous_treatments: Optional[List[str]] = None
    
    # 🆕 NOUVEAUX CHAMPS: Métadonnées d'inférence
    sex_inferred: Optional[bool] = None  # True si sexe inféré automatiquement
    breed_normalized: Optional[bool] = None  # True si race normalisée automatiquement
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour logs"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def get_missing_critical_info(self, question_type: str) -> List[str]:
        """Détermine les informations critiques manquantes selon le type de question"""
        missing = []
        
        if not self.breed or self.breed_type == "generic":
            missing.append("breed")
        
        if question_type in ["growth", "weight", "performance"]:
            if not self.age_days and not self.age_weeks:
                missing.append("age")
        elif question_type in ["health", "mortality", "disease"]:
            if not self.age_days and not self.age_weeks:
                missing.append("age")
            if not self.symptoms:
                missing.append("symptoms")
        elif question_type in ["environment", "temperature", "housing"]:
            if not self.age_days and not self.age_weeks:
                missing.append("age")
        elif question_type in ["feeding", "nutrition"]:
            if not self.age_days and not self.age_weeks:
                missing.append("age")
        
        return missing
    
    def normalize_breed_name(self, raw_breed: str) -> Tuple[str, bool]:
        """
        🆕 NOUVEAU: Normalise le nom de la souche selon les patterns connus
        
        Args:
            raw_breed: Nom brut de la souche
            
        Returns:
            Tuple[str, bool]: (nom_normalisé, a_été_normalisé)
        """
        
        if not raw_breed:
            return raw_breed, False
        
        raw_lower = raw_breed.lower().strip()
        
        # Dictionnaire de normalisation des souches
        breed_normalization = {
            # Poules pondeuses
            "lohmann": "Lohmann LSL-Lite",
            "lohmann lsl": "Lohmann LSL-Lite", 
            "lohmann lsl-lite": "Lohmann LSL-Lite",
            "lohmann lsl lite": "Lohmann LSL-Lite",
            "lsl": "Lohmann LSL-Lite",
            "lsl-lite": "Lohmann LSL-Lite",
            "lsl lite": "Lohmann LSL-Lite",
            
            "bovans": "Bovans Brown",
            "bovans brown": "Bovans Brown",
            "bovans blanc": "Bovans White",
            "bovans white": "Bovans White",
            
            "hisex": "Hisex Brown",
            "hisex brown": "Hisex Brown",
            "hisex blanc": "Hisex White",
            "hisex white": "Hisex White",
            
            "isa": "ISA Brown",
            "isa brown": "ISA Brown",
            "isa blanc": "ISA White",
            "isa white": "ISA White",
            
            "hyline": "Hyline Brown",
            "hyline brown": "Hyline Brown",
            "hyline white": "Hyline White",
            
            # Poulets de chair
            "ross": "Ross 308",
            "ross308": "Ross 308",
            "ross 308": "Ross 308",
            "ross708": "Ross 708",
            "ross 708": "Ross 708",
            "ross ap95": "Ross AP95",
            "ross pm3": "Ross PM3",
            
            "cobb": "Cobb 500",
            "cobb500": "Cobb 500",
            "cobb 500": "Cobb 500",
            "cobb700": "Cobb 700",
            "cobb 700": "Cobb 700",
            "cobb sasso": "Cobb Sasso",
            
            "hubbard": "Hubbard Flex",
            "hubbard flex": "Hubbard Flex",
            "hubbard classic": "Hubbard Classic",
            
            "arbor acres": "Arbor Acres",
            "arbor": "Arbor Acres",
            
            # Autres
            "red bro": "Red Bro",
            "redbro": "Red Bro"
        }
        
        # Recherche exacte d'abord
        if raw_lower in breed_normalization:
            normalized = breed_normalization[raw_lower]
            logger.info(f"🔄 [Breed Normalization] '{raw_breed}' → '{normalized}' (exact match)")
            return normalized, True
        
        # Recherche par mots-clés
        for pattern, normalized_name in breed_normalization.items():
            if pattern in raw_lower:
                logger.info(f"🔄 [Breed Normalization] '{raw_breed}' → '{normalized_name}' (keyword match: '{pattern}')")
                return normalized_name, True
        
        # Aucune normalisation trouvée
        return raw_breed, False
    
    def infer_sex_from_breed(self, breed: str) -> Tuple[Optional[str], bool]:
        """
        🆕 NOUVEAU: Infère automatiquement le sexe selon la souche
        
        Args:
            breed: Nom de la souche (normalisé)
            
        Returns:
            Tuple[Optional[str], bool]: (sexe_inféré, a_été_inféré)
        """
        
        if not breed:
            return None, False
        
        breed_lower = breed.lower()
        
        # Lignées femelles (poules pondeuses)
        female_breeds = [
            "lohmann lsl-lite",
            "bovans brown", 
            "bovans white",
            "hisex brown",
            "hisex white", 
            "isa brown",
            "isa white",
            "hyline brown",
            "hyline white"
        ]
        
        # Lignées mixtes (poulets de chair) - pas d'inférence automatique
        mixed_breeds = [
            "ross 308",
            "ross 708", 
            "ross ap95",
            "ross pm3",
            "cobb 500",
            "cobb 700",
            "cobb sasso",
            "hubbard flex",
            "hubbard classic",
            "arbor acres",
            "red bro"
        ]
        
        # Vérifier si c'est une lignée femelle
        for female_breed in female_breeds:
            if female_breed in breed_lower:
                logger.info(f"🚺 [Sex Inference] '{breed}' → 'femelle' (lignée pondeuse)")
                return "femelle", True
        
        # Pour les lignées mixtes, pas d'inférence (retourner None)
        for mixed_breed in mixed_breeds:
            if mixed_breed in breed_lower:
                logger.info(f"🔄 [Sex Inference] '{breed}' → None (lignée mixte - pas d'inférence)")
                return None, False
        
        # Breed non reconnu
        logger.info(f"❓ [Sex Inference] '{breed}' → None (souche non reconnue)")
        return None, False
    
    def normalize_and_infer(self):
        """
        🆕 NOUVEAU: Applique la normalisation de souche et l'inférence de sexe
        Modifie l'objet en place
        """
        
        # 1. Normaliser la souche si présente
        if self.breed:
            normalized_breed, was_normalized = self.normalize_breed_name(self.breed)
            if was_normalized:
                self.breed = normalized_breed
                self.breed_normalized = True
                self.breed_type = "specific"  # Les souches normalisées sont spécifiques
        
        # 2. Inférer le sexe si pas déjà spécifié et si souche présente
        if not self.sex and self.breed:
            inferred_sex, was_inferred = self.infer_sex_from_breed(self.breed)
            if was_inferred and inferred_sex:
                self.sex = inferred_sex
                self.sex_inferred = True
                logger.info(f"✅ [Auto Inference] Sexe inféré automatiquement: {inferred_sex} pour {self.breed}")

@dataclass
class ClarificationResult:
    """Résultat de l'analyse de clarification amélioré"""
    needs_clarification: bool
    questions: Optional[List[str]] = None
    confidence_score: float = 0.0
    processing_time_ms: int = 0
    reason: Optional[str] = None
    model_used: Optional[str] = None
    extracted_entities: Optional[ExtractedEntities] = None
    question_type: Optional[str] = None
    clarification_mode: Optional[ClarificationMode] = None
    clarification_state: Optional[ClarificationState] = None
    missing_critical_info: Optional[List[str]] = None
    should_reprocess: bool = False
    original_question: Optional[str] = None
    validation_score: Optional[float] = None  # 🔧 NOUVEAU: Score de validation des questions
    validation_details: Optional[Dict[str, Any]] = None  # 🔧 NOUVEAU: Détails validation
    fallback_used: bool = False  # 🔧 NOUVEAU: Indicateur si fallback utilisé
    gpt_failed: bool = False  # 🔧 NOUVEAU: Indicateur si GPT a échoué
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour les logs"""
        return {
            "needs_clarification": self.needs_clarification,
            "questions": self.questions,
            "questions_count": len(self.questions) if self.questions else 0,
            "confidence_score": self.confidence_score,
            "processing_time_ms": self.processing_time_ms,
            "reason": self.reason,
            "model_used": self.model_used,
            "extracted_entities": self.extracted_entities.to_dict() if self.extracted_entities else None,
            "question_type": self.question_type,
            "clarification_mode": self.clarification_mode.value if self.clarification_mode else None,
            "clarification_state": self.clarification_state.value if self.clarification_state else None,
            "missing_critical_info": self.missing_critical_info,
            "should_reprocess": self.should_reprocess,
            "original_question": self.original_question,
            "validation_score": self.validation_score,
            "validation_details": self.validation_details,
            "fallback_used": self.fallback_used,
            "gpt_failed": self.gpt_failed
        }

# ==================== FONCTIONS UTILITAIRES ====================

def normalize_breed_name(raw_breed: str) -> Tuple[str, bool]:
    """Normalise le nom d'une souche selon les patterns connus"""
    dummy_entity = ExtractedEntities()
    return dummy_entity.normalize_breed_name(raw_breed)

def infer_sex_from_breed(breed: str) -> Tuple[Optional[str], bool]:
    """Infère le sexe automatiquement selon la souche"""
    dummy_entity = ExtractedEntities()
    return dummy_entity.infer_sex_from_breed(breed)

def get_supported_breeds() -> Dict[str, List[str]]:
    """Retourne la liste des souches supportées par catégorie"""
    return {
        "laying": [
            "Lohmann LSL-Lite", "Bovans Brown", "Bovans White", 
            "Hisex Brown", "Hisex White", "ISA Brown", "ISA White",
            "Hyline Brown", "Hyline White"
        ],
        "broiler": [
            "Ross 308", "Ross 708", "Ross AP95", "Ross PM3",
            "Cobb 500", "Cobb 700", "Cobb Sasso",
            "Hubbard Flex", "Hubbard Classic", "Arbor Acres", "Red Bro"
        ]
    }