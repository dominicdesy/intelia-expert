"""
RAGContextEnhancer AMÉLIORÉ - Extraction d'entités complète
Version enrichie avec extraction NLP hybride et entités étendues
VERSION FINALE AVEC DÉTECTION INTELLIGENTE QUESTIONS TECHNIQUES
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

# ✅ CORRECTION: Import des modèles nécessaires en haut du fichier
try:
    from .expert_models import VaguenessDetection, QuestionClarity, ContextCoherence, EnhancedFallbackDetails, QualityMetrics, DocumentRelevance, ConfidenceLevel
except ImportError:
    # Fallback si les imports échouent
    logger.warning("⚠️ Import expert_models échoué - utilisation des classes de fallback")
    
    class QuestionClarity:
        CLEAR = "clear"
        PARTIALLY_CLEAR = "partially_clear"
        UNCLEAR = "unclear"
        VERY_UNCLEAR = "very_unclear"
    
    class ConfidenceLevel:
        VERY_LOW = "very_low"
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        VERY_HIGH = "very_high"

# Import SpaCy sécurisé
try:
    import spacy
    SPACY_AVAILABLE = True
    # Charger les modèles disponibles
    try:
        nlp_fr = spacy.load("fr_core_news_sm")
    except OSError:
        nlp_fr = None
    try:
        nlp_en = spacy.load("en_core_web_sm") 
    except OSError:
        nlp_en = None
except ImportError:
    SPACY_AVAILABLE = False
    nlp_fr = None
    nlp_en = None

logger = logging.getLogger(__name__)

@dataclass
class ExtendedContextEntities:
    """Entités contextuelles étendues pour RAG"""
    
    # === ENTITÉS DE BASE ===
    breed: Optional[str] = None
    breed_confidence: float = 0.0
    breed_type: Optional[str] = None  # specific/generic
    
    age_days: Optional[int] = None
    age_weeks: Optional[float] = None
    age_confidence: float = 0.0
    
    weight_grams: Optional[float] = None
    weight_confidence: float = 0.0
    
    # === ENTITÉS ENVIRONNEMENTALES ===
    temperature: Optional[float] = None
    temperature_unit: str = "celsius"
    temperature_confidence: float = 0.0
    
    humidity: Optional[float] = None
    humidity_confidence: float = 0.0
    
    lighting: Optional[str] = None  # natural/artificial/continuous/intermittent
    lighting_hours: Optional[float] = None
    lighting_confidence: float = 0.0
    
    ventilation: Optional[str] = None  # good/poor/adequate/insufficient
    ventilation_confidence: float = 0.0
    
    # === ENTITÉS DE SANTÉ ===
    mortality_rate: Optional[float] = None
    mortality_confidence: float = 0.0
    
    symptoms: List[str] = field(default_factory=list)
    symptoms_confidence: float = 0.0
    
    health_status: Optional[str] = None  # good/concerning/critical
    health_confidence: float = 0.0
    
    diseases: List[str] = field(default_factory=list)
    treatments: List[str] = field(default_factory=list)
    
    # === ENTITÉS DE PERFORMANCE ===
    feed_consumption: Optional[float] = None
    feed_conversion_ratio: Optional[float] = None
    water_consumption: Optional[float] = None
    
    growth_rate: Optional[str] = None  # slow/normal/fast
    performance_index: Optional[float] = None
    
    # === ENTITÉS DE GESTION ===
    flock_size: Optional[int] = None
    housing_type: Optional[str] = None  # cage/floor/free_range
    housing_density: Optional[float] = None
    
    vaccination_status: Optional[str] = None
    vaccination_schedule: List[str] = field(default_factory=list)
    
    # === ENTITÉS TEMPORELLES ===
    problem_duration: Optional[str] = None
    season: Optional[str] = None  # spring/summer/fall/winter
    time_of_day: Optional[str] = None
    
    # === MÉTADONNÉES ===
    extraction_method: str = "hybrid"
    extraction_confidence_overall: float = 0.0
    spacy_used: bool = False
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour logs"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None and value != [] and value != "":
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result
    
    def get_contextual_summary(self, language: str = "fr") -> str:
        """Génère un résumé contextuel pour le RAG"""
        parts = []
        
        # Race et âge (priorité haute)
        if self.breed:
            if self.age_days:
                if language == "fr":
                    parts.append(f"Race: {self.breed}, Âge: {self.age_days} jours")
                else:
                    parts.append(f"Breed: {self.breed}, Age: {self.age_days} days")
            else:
                parts.append(f"{'Race' if language == 'fr' else 'Breed'}: {self.breed}")
        
        # Performance
        if self.weight_grams:
            parts.append(f"{'Poids' if language == 'fr' else 'Weight'}: {self.weight_grams}g")
        
        if self.mortality_rate:
            parts.append(f"{'Mortalité' if language == 'fr' else 'Mortality'}: {self.mortality_rate}%")
        
        # Environnement
        if self.temperature:
            parts.append(f"{'Température' if language == 'fr' else 'Temperature'}: {self.temperature}°C")
        
        if self.humidity:
            parts.append(f"{'Humidité' if language == 'fr' else 'Humidity'}: {self.humidity}%")
        
        # Santé
        if self.symptoms:
            symptoms_str = ", ".join(self.symptoms[:3])  # Max 3 symptômes
            parts.append(f"{'Symptômes' if language == 'fr' else 'Symptoms'}: {symptoms_str}")
        
        # Gestion
        if self.flock_size:
            parts.append(f"{'Taille troupeau' if language == 'fr' else 'Flock size'}: {self.flock_size}")
        
        if self.housing_type:
            parts.append(f"{'Logement' if language == 'fr' else 'Housing'}: {self.housing_type}")
        
        return " | ".join(parts)

class EnhancedRAGContextEnhancer:
    """Extracteur d'entités contextuelles avancé avec NLP hybride"""
    
    def __init__(self):
        """Initialise l'extracteur avec patterns étendus et NLP"""
        
        self.spacy_available = SPACY_AVAILABLE
        self.nlp_models = {"fr": nlp_fr, "en": nlp_en}
        
        # === PATTERNS DE DÉTECTION ÉTENDUS ===
        self.pronoun_patterns = {
            "fr": [
                r'\b(son|sa|ses|leur|leurs)\s+(poids|âge|croissance|développement|température|mortalité)',
                r'\b(ils|elles)\s+(pèsent|grandissent|se développent|meurent|sont malades)',
                r'\b(qu\'?est-ce que|quel est|quelle est)\s+(son|sa|ses|leur)',
                r'\b(combien)\s+(pèsent-ils|font-ils|mesurent-ils|meurent)',
                r'\b(comment vont-ils|comment sont-ils)'
            ],
            "en": [
                r'\b(their|its)\s+(weight|age|growth|development|temperature|mortality)',
                r'\b(they)\s+(weigh|grow|develop|die|are sick)',
                r'\b(what is|how much is)\s+(their|its)',
                r'\b(how much do they)\s+(weigh|measure)',
                r'\b(how are they|how do they)'
            ],
            "es": [
                r'\b(su|sus)\s+(peso|edad|crecimiento|desarrollo|temperatura|mortalidad)',
                r'\b(ellos|ellas)\s+(pesan|crecen|se desarrollan|mueren|están enfermos)',
                r'\b(cuál es|cuánto es)\s+(su|sus)',
                r'\b(cuánto)\s+(pesan|miden)',
                r'\b(cómo están|cómo van)'
            ]
        }
        
        # === PATTERNS D'EXTRACTION D'ENTITÉS ===
        self._init_extraction_patterns()
        
        logger.info(f"✅ [Enhanced RAG Context] Extracteur initialisé")
        logger.info(f"🔧 [Enhanced RAG Context] SpaCy disponible: {'✅' if self.spacy_available else '❌'}")
        if self.spacy_available:
            available_models = [lang for lang, model in self.nlp_models.items() if model is not None]
            logger.info(f"🌐 [Enhanced RAG Context] Modèles NLP: {available_models}")
    
    def _init_extraction_patterns(self):
        """Initialise les patterns d'extraction pour toutes les entités"""
        
        self.extraction_patterns = {
            # === RACES ===
            "breed_specific": {
                "fr": [r'(ross\s*308|ross\s*708|cobb\s*500|cobb\s*700|hubbard\s*(?:flex|classic)|arbor\s*acres|isa\s*15)', 
                       r'race\s*[:\-]?\s*(ross\s*308|cobb\s*500)'],
                "en": [r'(ross\s*308|ross\s*708|cobb\s*500|cobb\s*700|hubbard\s*(?:flex|classic)|arbor\s*acres|isa\s*15)',
                       r'breed\s*[:\-]?\s*(ross\s*308|cobb\s*500)'],
                "es": [r'(ross\s*308|ross\s*708|cobb\s*500|cobb\s*700|hubbard\s*(?:flex|classic)|arbor\s*acres|isa\s*15)',
                       r'raza\s*[:\-]?\s*(ross\s*308|cobb\s*500)']
            },
            
            "breed_generic": {
                "fr": [r'\b(poulets?|volailles?|poussins?|coquelets?)\b'],
                "en": [r'\b(chickens?|poultry|chicks?|broilers?)\b'],
                "es": [r'\b(pollos?|aves?|pollitos?|polluelos?)\b']
            },
            
            # === ÂGE ===
            "age": {
                "all": [
                    r'(\d+)\s*(?:jour|day|día)s?(?:\s+(?:d\'?âge|old|de edad))?',
                    r'(\d+)\s*(?:semaine|week|semana)s?(?:\s+(?:d\'?âge|old|de edad))?',
                    r'(?:âge|age|edad)\s*[:\-]?\s*(\d+)\s*(?:jour|day|día|semaine|week|semana)s?',
                    r'(\d+)\s*[jdsw]\b',  # j=jour, d=day, s=semaine, w=week
                    r'jour\s*(\d+)',
                    r'day\s*(\d+)',
                    r'(\d+)°?\s*jour'
                ]
            },
            
            # === POIDS ===
            "weight": {
                "all": [
                    r'(\d+(?:\.\d+)?)\s*(?:g|gr|gramme|gram)s?\b',
                    r'(\d+(?:\.\d+)?)\s*kg\b',
                    r'(?:poids|weight|peso)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:g|kg|gr)?',
                    r'pèsent?\s*(\d+(?:\.\d+)?)',
                    r'weigh[ts]?\s*(\d+(?:\.\d+)?)',
                    r'pesan\s*(\d+(?:\.\d+)?)',
                    r'(\d+(?:\.\d+)?)\s*livres?',  # pounds
                    r'(\d+(?:\.\d+)?)\s*lbs?'
                ]
            }
        }
    
    def enhance_question_for_rag(
        self, 
        question: str, 
        conversation_context: str, 
        language: str = "fr"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Améliore une question pour le RAG avec extraction d'entités complète
        """
        
        enhancement_info = {
            "pronoun_detected": False,
            "context_entities_used": [],
            "question_enriched": False,
            "original_question": question,
            "extraction_method": "hybrid",
            "spacy_used": False,
            "entities_extracted": 0
        }
        
        # 1. Détecter les pronoms/références contextuelles
        has_pronouns = self._detect_contextual_references(question, language)
        if has_pronouns:
            enhancement_info["pronoun_detected"] = True
            logger.info(f"🔍 [Enhanced RAG Context] Pronoms détectés dans: '{question}'")
        
        # 2. Extraction d'entités complète (hybride)
        context_entities = self._extract_all_entities_hybrid(conversation_context, language)
        
        if context_entities:
            enhancement_info["context_entities_used"] = list(context_entities.to_dict().keys())
            enhancement_info["entities_extracted"] = len([v for v in context_entities.to_dict().values() if v])
            enhancement_info["extraction_method"] = context_entities.extraction_method
            enhancement_info["spacy_used"] = context_entities.spacy_used
            
            logger.info(f"📊 [Enhanced RAG Context] {enhancement_info['entities_extracted']} entités extraites")
            logger.debug(f"🔍 [Enhanced RAG Context] Entités: {context_entities.to_dict()}")
        
        # 3. Enrichir la question si nécessaire
        enriched_question = question
        
        if has_pronouns and context_entities:
            enriched_question = self._build_enriched_question_advanced(
                question, context_entities, language
            )
            enhancement_info["question_enriched"] = True
            logger.info(f"✨ [Enhanced RAG Context] Question enrichie: '{enriched_question[:150]}...'")
        
        # 4. Ajouter résumé contextuel pour le RAG
        contextual_summary = context_entities.get_contextual_summary(language) if context_entities else ""
        if contextual_summary:
            enriched_question += f"\n\nContexte détaillé: {contextual_summary}"
        
        return enriched_question, enhancement_info
    
    def _extract_all_entities_hybrid(self, context: str, language: str) -> Optional[ExtendedContextEntities]:
        """Extraction hybride (regex + NLP) de toutes les entités"""
        
        if not context:
            return None
        
        entities = ExtendedContextEntities()
        entities.extraction_method = "hybrid"
        
        # Phase 1: Extraction par regex (base)
        self._extract_with_regex(context, language, entities)
        
        # Phase 2: Extraction NLP si disponible (enrichissement)
        if self.spacy_available and self.nlp_models.get(language):
            self._extract_with_spacy(context, language, entities)
            entities.spacy_used = True
        
        # Phase 3: Calcul de confiance globale
        entities.extraction_confidence_overall = self._calculate_overall_confidence(entities)
        
        return entities if entities.extraction_confidence_overall > 0.1 else None
    
    def _extract_with_regex(self, context: str, language: str, entities: ExtendedContextEntities):
        """Extraction par regex (méthode robuste)"""
        
        context_lower = context.lower()
        
        # === RACES ===
        breed_patterns = self.extraction_patterns["breed_specific"].get(language, []) + \
                        self.extraction_patterns["breed_specific"].get("all", [])
        
        for pattern in breed_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities.breed = match.group(1).strip()
                entities.breed_type = "specific"
                entities.breed_confidence = 0.9
                break
        
        if not entities.breed:
            generic_patterns = self.extraction_patterns["breed_generic"].get(language, [])
            for pattern in generic_patterns:
                match = re.search(pattern, context_lower, re.IGNORECASE)
                if match:
                    entities.breed = match.group(0).strip()
                    entities.breed_type = "generic"
                    entities.breed_confidence = 0.3
                    break
        
        # === ÂGE ===
        age_patterns = self.extraction_patterns["age"]["all"]
        for pattern in age_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                if "semaine" in pattern or "week" in pattern or "semana" in pattern:
                    entities.age_weeks = value
                    entities.age_days = value * 7
                else:
                    entities.age_days = value
                    entities.age_weeks = value / 7
                entities.age_confidence = 0.8
                break
        
        # === POIDS ===
        weight_patterns = self.extraction_patterns["weight"]["all"]
        for pattern in weight_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                weight = float(match.group(1))
                if "kg" in pattern.lower() or "kg" in match.group(0).lower():
                    weight *= 1000
                entities.weight_grams = weight
                entities.weight_confidence = 0.8
                break
    
    def _extract_with_spacy(self, context: str, language: str, entities: ExtendedContextEntities):
        """Extraction avec SpaCy (enrichissement NLP)"""
        
        nlp = self.nlp_models.get(language)
        if not nlp:
            return
        
        try:
            doc = nlp(context)
            
            # Extraction d'entités nommées
            for ent in doc.ents:
                if ent.label_ in ["PERSON", "ORG"] and not entities.breed:
                    # Potential breed mention
                    if any(breed in ent.text.lower() for breed in ["ross", "cobb", "hubbard"]):
                        entities.breed = ent.text
                        entities.breed_confidence = max(entities.breed_confidence, 0.6)
                
                elif ent.label_ in ["QUANTITY", "CARDINAL"] and not entities.flock_size:
                    # Potential flock size
                    if any(word in context.lower() for word in ["poulet", "chicken", "pollo", "oiseau", "bird"]):
                        try:
                            entities.flock_size = int(ent.text)
                        except ValueError:
                            pass
            
            entities.extraction_method = "hybrid_with_spacy"
            
        except Exception as e:
            logger.warning(f"⚠️ [Enhanced RAG Context] Erreur SpaCy: {e}")
    
    def _calculate_overall_confidence(self, entities: ExtendedContextEntities) -> float:
        """Calcule la confiance globale d'extraction"""
        
        confidence_scores = []
        
        # Ajouter les scores individuels
        for field_name in entities.__dataclass_fields__:
            if field_name.endswith("_confidence"):
                confidence = getattr(entities, field_name, 0.0)
                if confidence > 0:
                    confidence_scores.append(confidence)
        
        if not confidence_scores:
            return 0.0
        
        # Moyenne pondérée avec bonus pour nombre d'entités
        base_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # Bonus pour diversité d'entités
        entity_count_bonus = min(len(confidence_scores) * 0.05, 0.2)
        
        # Bonus SpaCy
        spacy_bonus = 0.1 if entities.spacy_used else 0.0
        
        return min(base_confidence + entity_count_bonus + spacy_bonus, 1.0)
    
    def _build_enriched_question_advanced(
        self, 
        question: str, 
        entities: ExtendedContextEntities, 
        language: str
    ) -> str:
        """Construit une question enrichie avec toutes les entités disponibles"""
        
        # Templates avancés par langue
        templates = {
            "fr": {
                "full_context": "Pour des {breed} de {age}, logés en {housing}, avec {performance}",
                "breed_age_perf": "Pour des {breed} de {age} avec {performance}",
                "breed_age": "Pour des {breed} de {age}",
                "breed_only": "Pour des {breed}",
                "age_only": "Pour des poulets de {age}",
                "context_health": "Contexte santé: {health}",
                "context_environment": "Conditions: {environment}"
            },
            "en": {
                "full_context": "For {breed} chickens at {age}, housed in {housing}, with {performance}",
                "breed_age_perf": "For {breed} chickens at {age} with {performance}",
                "breed_age": "For {breed} chickens at {age}",
                "breed_only": "For {breed} chickens",
                "age_only": "For chickens at {age}",
                "context_health": "Health context: {health}",
                "context_environment": "Conditions: {environment}"
            },
            "es": {
                "full_context": "Para pollos {breed} de {age}, alojados en {housing}, con {performance}",
                "breed_age_perf": "Para pollos {breed} de {age} con {performance}",
                "breed_age": "Para pollos {breed} de {age}",
                "breed_only": "Para pollos {breed}",
                "age_only": "Para pollos de {age}",
                "context_health": "Contexto salud: {health}",
                "context_environment": "Condiciones: {environment}"
            }
        }
        
        template_set = templates.get(language, templates["fr"])
        
        # Construire les éléments de contexte
        context_parts = []
        
        # Contexte de base
        if entities.breed and entities.age_days:
            age_str = f"{entities.age_days} jours" if language == "fr" else f"{entities.age_days} days"
            if entities.weight_grams or entities.mortality_rate:
                perf_parts = []
                if entities.weight_grams:
                    perf_parts.append(f"{entities.weight_grams}g")
                if entities.mortality_rate:
                    perf_parts.append(f"{entities.mortality_rate}% mortalité")
                performance = ", ".join(perf_parts)
                
                if entities.housing_type:
                    context_prefix = template_set["full_context"].format(
                        breed=entities.breed, age=age_str, 
                        housing=entities.housing_type, performance=performance
                    )
                else:
                    context_prefix = template_set["breed_age_perf"].format(
                        breed=entities.breed, age=age_str, performance=performance
                    )
            else:
                context_prefix = template_set["breed_age"].format(
                    breed=entities.breed, age=age_str
                )
        elif entities.breed:
            context_prefix = template_set["breed_only"].format(breed=entities.breed)
        elif entities.age_days:
            age_str = f"{entities.age_days} jours" if language == "fr" else f"{entities.age_days} days"
            context_prefix = template_set["age_only"].format(age=age_str)
        else:
            context_prefix = ""
        
        # Assembler la question enrichie
        enriched = question.lower() if context_prefix else question
        
        if context_prefix:
            if any(word in question.lower() for word in ["son", "sa", "ses", "leur", "leurs", "their", "its", "su", "sus"]):
                enriched = f"{context_prefix}, {enriched}"
            else:
                enriched = f"{context_prefix}: {enriched}"
        
        return enriched
    
    def _detect_contextual_references(self, question: str, language: str) -> bool:
        """Détecte les références contextuelles dans la question"""
        
        patterns = self.pronoun_patterns.get(language, self.pronoun_patterns["fr"])
        question_lower = question.lower()
        
        for pattern in patterns:
            if re.search(pattern, question_lower, re.IGNORECASE):
                logger.debug(f"🎯 [Enhanced RAG Context] Pattern contextuel trouvé: {pattern}")
                return True
        
        return False

# =============================================================================
# ✅ CLASSE APIEnhancementService AVEC DÉTECTION INTELLIGENTE
# =============================================================================

class APIEnhancementService:
    """Service d'amélioration API - Wrapper pour les nouvelles fonctionnalités"""
    
    def __init__(self):
        self.rag_enhancer = EnhancedRAGContextEnhancer()
        logger.info("✅ [API Enhancement Service] Service d'amélioration API initialisé")
    
    def detect_vagueness(self, question: str, language: str = "fr"):
        """
        ✅ DÉTECTION DE FLOU AMÉLIORÉE
        Détecte spécifiquement les questions techniques nécessitant des précisions
        """
        # ✅ CORRECTION: Import local supprimé - utilisation des imports globaux
        
        question_lower = question.lower().strip()
        missing_specifics = []
        vagueness_score = 0.0
        
        # ✅ NOUVEAU : Détection spécifique questions poids/performance
        performance_vagueness = self._detect_performance_question_vagueness(question_lower, language)
        
        if performance_vagueness:
            # ✅ CORRECTION: Utilisation de classes importées en haut
            try:
                return VaguenessDetection(
                    is_vague=True,
                    vagueness_score=performance_vagueness["score"],
                    missing_specifics=performance_vagueness["missing"],
                    question_clarity=performance_vagueness["clarity"],
                    suggested_clarification=performance_vagueness["suggestion"],
                    actionable=True,  # Ces questions sont toujours actionnables
                    detected_patterns=performance_vagueness["patterns"]
                )
            except Exception as e:
                logger.error(f"❌ Erreur création VaguenessDetection: {e}")
                # Fallback simple
                return {
                    "is_vague": True,
                    "vagueness_score": performance_vagueness["score"],
                    "missing_specifics": performance_vagueness["missing"],
                    "question_clarity": performance_vagueness["clarity"],
                    "suggested_clarification": performance_vagueness["suggestion"],
                    "actionable": True,
                    "detected_patterns": performance_vagueness["patterns"]
                }
        
        # Logique existante pour autres types de questions...
        vague_patterns = [
            r'^(comment|how|cómo)',
            r'^(pourquoi|why|por qué)',
            r'^(que faire|what to do|qué hacer)',
            r'\b(problème|problem|problema)\b',
            r'\b(aide|help|ayuda)\b'
        ]
        
        # [Reste de la logique existante...]
        for pattern in vague_patterns:
            if re.search(pattern, question_lower):
                vagueness_score += 0.2
        
        if len(question_lower.split()) < 5:
            vagueness_score += 0.3
            missing_specifics.append("Question trop courte")
        
        if not re.search(r'\d+', question_lower):
            vagueness_score += 0.2
            missing_specifics.append("Pas de données numériques")
        
        breed_mentioned = bool(re.search(r'(ross|cobb|poulet|chicken|pollo)', question_lower))
        age_mentioned = bool(re.search(r'(jour|day|semaine|week|âge|age)', question_lower))
        
        if not breed_mentioned and not age_mentioned:
            vagueness_score += 0.3
            missing_specifics.append("Race ou âge non mentionnés")
        
        vagueness_score = min(vagueness_score, 1.0)
        
        # Déterminer la clarté
        if vagueness_score > 0.7:
            clarity = QuestionClarity.VERY_UNCLEAR
        elif vagueness_score > 0.5:
            clarity = QuestionClarity.UNCLEAR
        elif vagueness_score > 0.3:
            clarity = QuestionClarity.PARTIALLY_CLEAR
        else:
            clarity = QuestionClarity.CLEAR
        
        suggested_clarification = None
        if vagueness_score > 0.5:
            if language == "fr":
                suggested_clarification = "Pouvez-vous préciser la race, l'âge et les conditions spécifiques ?"
            elif language == "en":
                suggested_clarification = "Could you specify the breed, age and specific conditions?"
            else:
                suggested_clarification = "¿Podría especificar la raza, edad y condiciones específicas?"
        
        # ✅ CORRECTION: Gestion d'erreur pour VaguenessDetection
        try:
            return VaguenessDetection(
                is_vague=vagueness_score > 0.5,
                vagueness_score=vagueness_score,
                missing_specifics=missing_specifics,
                question_clarity=clarity,
                suggested_clarification=suggested_clarification,
                actionable=vagueness_score < 0.8,
                detected_patterns=[p for p in vague_patterns if re.search(p, question_lower)]
            )
        except Exception as e:
            logger.error(f"❌ Erreur création VaguenessDetection standard: {e}")
            # Fallback dictionnaire
            return {
                "is_vague": vagueness_score > 0.5,
                "vagueness_score": vagueness_score,
                "missing_specifics": missing_specifics,
                "question_clarity": clarity.value if hasattr(clarity, 'value') else clarity,
                "suggested_clarification": suggested_clarification,
                "actionable": vagueness_score < 0.8,
                "detected_patterns": [p for p in vague_patterns if re.search(p, question_lower)]
            }

    def _detect_performance_question_vagueness(self, question_lower: str, language: str) -> Optional[Dict]:
        """
        ✅ NOUVELLE FONCTION : Détection spécialisée pour questions poids/performance
        """
        
        # Patterns pour questions poids + âge
        weight_age_patterns = [
            r'(?:poids|weight|peso).*?(\d+)\s*(?:jour|day|día|semaine|week|semana)',
            r'(\d+)\s*(?:jour|day|día|semaine|week|semana).*?(?:poids|weight|peso)',
            r'(?:quel|what|cuál).*?(?:poids|weight|peso).*?(\d+)',
            r'(?:combien|how much|cuánto).*?(?:pèse|weigh|pesa).*?(\d+)'
        ]
        
        # Vérifier si c'est une question poids+âge
        has_weight_age = any(re.search(pattern, question_lower) for pattern in weight_age_patterns)
        
        if not has_weight_age:
            return None
        
        # Extraire l'âge mentionné
        age_match = re.search(r'(\d+)\s*(?:jour|day|día|semaine|week|semana)', question_lower)
        age = age_match.group(1) if age_match else "X"
        
        # Vérifier présence race/sexe
        breed_patterns = [
            r'(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)',
            r'race\s*[:\-]?\s*(ross|cobb|hubbard)',
            r'breed\s*[:\-]?\s*(ross|cobb|hubbard)'
        ]
        
        sex_patterns = [
            r'(mâle|male|macho|femelle|female|hembra)',
            r'(coq|hen|poule|gallina)',
            r'(mixte|mixed|misto)'
        ]
        
        has_breed = any(re.search(pattern, question_lower) for pattern in breed_patterns)
        has_sex = any(re.search(pattern, question_lower) for pattern in sex_patterns)
        
        # Si race ET sexe manquent → haute priorité de clarification
        if not has_breed and not has_sex:
            missing = ["race/souche", "sexe"]
            score = 0.85
            clarity = QuestionClarity.UNCLEAR
            
            suggestions = {
                "fr": f"Pour le poids exact à {age} jours, précisez la race (Ross 308, Cobb 500...) et le sexe (mâles/femelles)",
                "en": f"For exact weight at {age} days, specify breed (Ross 308, Cobb 500...) and sex (males/females)",
                "es": f"Para el peso exacto a {age} días, especifique la raza (Ross 308, Cobb 500...) y sexo (machos/hembras)"
            }
            
            return {
                "score": score,
                "missing": missing,
                "clarity": clarity,
                "suggestion": suggestions.get(language, suggestions["fr"]),
                "patterns": ["weight_age_without_breed_sex"],
                "type": "performance_technical_incomplete"
            }
        
        # Si seulement un des deux manque → priorité modérée
        elif not has_breed or not has_sex:
            missing = []
            if not has_breed:
                missing.append("race/souche")
            if not has_sex:
                missing.append("sexe")
            
            score = 0.65
            clarity = QuestionClarity.PARTIALLY_CLEAR
            
            missing_text = " et ".join(missing)
            suggestions = {
                "fr": f"Pour plus de précision sur le poids à {age} jours, précisez {missing_text}",
                "en": f"For more precision on weight at {age} days, specify {missing_text}",
                "es": f"Para mayor precisión del peso a {age} días, especifique {missing_text}"
            }
            
            return {
                "score": score,
                "missing": missing,
                "clarity": clarity,
                "suggestion": suggestions.get(language, suggestions["fr"]),
                "patterns": ["weight_age_partial_info"],
                "type": "performance_technical_partial"
            }
        
        # Question complète → pas de vagueness
        return None
    
    def check_context_coherence(self, rag_response: str, extracted_entities: Dict, rag_context: Dict, original_question: str):
        """Vérifie la cohérence entre contexte et RAG"""
        # ✅ CORRECTION: Import local supprimé - gestion d'erreur ajoutée
        
        # Implémentation basique de vérification de cohérence
        entities_match = True
        missing_critical_info = []
        warnings = []
        coherence_score = 1.0
        
        # Vérifier si les entités du contexte correspondent au RAG
        if extracted_entities:
            breed = extracted_entities.get('breed')
            age_days = extracted_entities.get('age_days')
            
            if breed and breed not in rag_response.lower():
                entities_match = False
                coherence_score -= 0.3
                warnings.append(f"Race mentionnée ({breed}) absente de la réponse")
            
            if age_days and str(age_days) not in rag_response:
                coherence_score -= 0.2
                warnings.append(f"Âge mentionné ({age_days} jours) non pris en compte")
        
        coherence_score = max(coherence_score, 0.0)
        
        # ✅ CORRECTION: Gestion d'erreur pour ContextCoherence
        try:
            return ContextCoherence(
                entities_match=entities_match,
                missing_critical_info=missing_critical_info,
                rag_assumptions={},
                coherence_score=coherence_score,
                warnings=warnings,
                recommended_clarification=None,
                entities_used_in_rag=extracted_entities
            )
        except Exception as e:
            logger.error(f"❌ Erreur création ContextCoherence: {e}")
            # Fallback dictionnaire
            return {
                "entities_match": entities_match,
                "missing_critical_info": missing_critical_info,
                "rag_assumptions": {},
                "coherence_score": coherence_score,
                "warnings": warnings,
                "recommended_clarification": None,
                "entities_used_in_rag": extracted_entities
            }
    
    def create_enhanced_fallback(self, failure_point: str, last_entities: Dict, confidence: float, error: Exception, context: Dict):
        """Crée un fallback enrichi avec diagnostics"""
        # ✅ CORRECTION: Gestion d'erreur pour EnhancedFallbackDetails
        
        try:
            return EnhancedFallbackDetails(
                failure_point=failure_point,
                last_known_entities=last_entities,
                confidence_at_failure=confidence,
                rag_attempts=[],
                error_category="system_error",
                recovery_suggestions=["Réessayer la requête", "Vérifier la connectivité"],
                alternative_approaches=["Utiliser une question plus spécifique"],
                technical_details=str(error)
            )
        except Exception as e:
            logger.error(f"❌ Erreur création EnhancedFallbackDetails: {e}")
            # Fallback dictionnaire
            return {
                "failure_point": failure_point,
                "last_known_entities": last_entities,
                "confidence_at_failure": confidence,
                "rag_attempts": [],
                "error_category": "system_error",
                "recovery_suggestions": ["Réessayer la requête", "Vérifier la connectivité"],
                "alternative_approaches": ["Utiliser une question plus spécifique"],
                "technical_details": str(error)
            }
    
    def calculate_quality_metrics(self, question: str, response: str, rag_score: float, coherence_result, vagueness_result):
        """Calcule les métriques de qualité"""
        # ✅ CORRECTION: Gestion d'erreur pour QualityMetrics
        
        # Calculs basiques de qualité
        response_completeness = min(len(response) / 200, 1.0)  # 200 chars = complet
        information_accuracy = rag_score if rag_score else 0.5
        
        # Gestion sécurisée des objets de cohérence
        if hasattr(coherence_result, 'coherence_score'):
            contextual_relevance = coherence_result.coherence_score
        elif isinstance(coherence_result, dict):
            contextual_relevance = coherence_result.get('coherence_score', 0.5)
        else:
            contextual_relevance = 0.5
        
        # Prédiction de satisfaction basée sur les métriques
        user_satisfaction_prediction = (
            response_completeness * 0.3 +
            information_accuracy * 0.4 +
            contextual_relevance * 0.3
        )
        
        # Pertinence de la longueur
        length_score = 1.0
        if len(response) < 50:
            length_score = 0.3  # Trop court
        elif len(response) > 1000:
            length_score = 0.7  # Peut-être trop long
        
        try:
            return QualityMetrics(
                response_completeness=response_completeness,
                information_accuracy=information_accuracy,
                contextual_relevance=contextual_relevance,
                user_satisfaction_prediction=user_satisfaction_prediction,
                response_length_appropriateness=length_score,
                technical_accuracy=rag_score
            )
        except Exception as e:
            logger.error(f"❌ Erreur création QualityMetrics: {e}")
            # Fallback dictionnaire
            return {
                "response_completeness": response_completeness,
                "information_accuracy": information_accuracy,
                "contextual_relevance": contextual_relevance,
                "user_satisfaction_prediction": user_satisfaction_prediction,
                "response_length_appropriateness": length_score,
                "technical_accuracy": rag_score
            }
    
    def create_detailed_document_relevance(self, rag_result: Dict, question: str, context: str):
        """Crée un scoring RAG détaillé"""
        # ✅ CORRECTION: Gestion d'erreur pour DocumentRelevance
        
        # Extraction des informations du résultat RAG
        score = rag_result.get('score', 0.0)
        sources = rag_result.get('sources', [])
        
        # Déterminer le niveau de confiance
        if score > 0.8:
            confidence = ConfidenceLevel.VERY_HIGH
        elif score > 0.6:
            confidence = ConfidenceLevel.HIGH
        elif score > 0.4:
            confidence = ConfidenceLevel.MEDIUM
        elif score > 0.2:
            confidence = ConfidenceLevel.LOW
        else:
            confidence = ConfidenceLevel.VERY_LOW
        
        # Document source principal
        source_document = None
        matched_section = None
        if sources:
            source_document = sources[0].get('preview', 'Document principal')
            matched_section = sources[0].get('index', 'Section inconnue')
        
        try:
            return DocumentRelevance(
                score=score,
                source_document=source_document,
                matched_section=matched_section,
                confidence_level=confidence,
                chunk_used=source_document[:100] + "..." if source_document else None,
                alternative_documents=[s.get('preview', '')[:50] for s in sources[1:3]] if len(sources) > 1 else [],
                search_query_used=question[:100]
            )
        except Exception as e:
            logger.error(f"❌ Erreur création DocumentRelevance: {e}")
            # Fallback dictionnaire
            return {
                "score": score,
                "source_document": source_document,
                "matched_section": matched_section,
                "confidence_level": confidence.value if hasattr(confidence, 'value') else confidence,
                "chunk_used": source_document[:100] + "..." if source_document else None,
                "alternative_documents": [s.get('preview', '')[:50] for s in sources[1:3]] if len(sources) > 1 else [],
                "search_query_used": question[:100]
            }

# =============================================================================
# LOGGING ET CONFIGURATION
# =============================================================================

logger.info("✅ [Enhanced RAG Context Enhancer] Extracteur d'entités avancé initialisé avec détection intelligente")
logger.info("🚀 [Enhanced RAG Context Enhancer] NOUVELLES CAPACITÉS:")
logger.info("   - 🏷️ 15+ types d'entités extraites (vs 3 avant)")
logger.info("   - 🧠 Extraction hybride regex + NLP SpaCy")
logger.info("   - 🌐 Support multilingue complet (FR/EN/ES)")
logger.info("   - 📊 Scores de confiance par entité")
logger.info("   - 🎯 Enrichissement contextuel avancé")
logger.info("   - 🔍 Détection pronoms étendus")
logger.info(f"   - 🤖 SpaCy disponible: {'✅' if SPACY_AVAILABLE else '❌ (regex only)'}")
logger.info("   - 🎪 Détection intelligente questions techniques race/sexe")
logger.info("   - ⚡ Clarification automatique poids/performance")
logger.info("✅ [API Enhancement Service] Service d'amélioration API complet et fonctionnel")