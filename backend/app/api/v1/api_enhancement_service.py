"""
RAGContextEnhancer AMÉLIORÉ - Extraction d'entités complète
Version enrichie avec extraction NLP hybride et entités étendues
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

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
            },
            
            # === TEMPÉRATURE ===
            "temperature": {
                "all": [
                    r'(\d+(?:\.\d+)?)\s*°?[cC]\b',
                    r'(\d+(?:\.\d+)?)\s*(?:degrés?|degrees?|grados?)\s*(?:celsius|c)?',
                    r'(?:température|temperature|temperatura)\s*[:\-]?\s*(\d+(?:\.\d+)?)',
                    r'(\d+(?:\.\d+)?)\s*°?[fF]\b',  # Fahrenheit
                    r'(?:chaud|hot|caliente)\s*[:\-]?\s*(\d+(?:\.\d+)?)',
                    r'(?:froid|cold|frío)\s*[:\-]?\s*(\d+(?:\.\d+)?)'
                ]
            },
            
            # === HUMIDITÉ ===
            "humidity": {
                "all": [
                    r'(\d+(?:\.\d+)?)\s*%\s*(?:humidité|humidity|humedad)',
                    r'(?:humidité|humidity|humedad)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%?',
                    r'RH\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%?',
                    r'(?:hygrométrie|hygrometry)\s*[:\-]?\s*(\d+(?:\.\d+)?)'
                ]
            },
            
            # === MORTALITÉ ===
            "mortality": {
                "all": [
                    r'(\d+(?:\.\d+)?)\s*%?\s*(?:mortalité|mortality|mortalidad)',
                    r'(?:mortalité|mortality|mortalidad)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%?',
                    r'(\d+(?:\.\d+)?)\s*%?\s*(?:morts?|dead|muertos?)',
                    r'taux\s*(?:de\s*)?mortalité\s*[:\-]?\s*(\d+(?:\.\d+)?)',
                    r'mortality\s*rate\s*[:\-]?\s*(\d+(?:\.\d+)?)',
                    r'(\d+)\s*(?:sur|of|de)\s*(\d+)\s*(?:morts?|dead|muertos?)'
                ]
            },
            
            # === ÉCLAIRAGE ===
            "lighting": {
                "fr": [r'(?:éclairage|lumière)\s*[:\-]?\s*(naturel|artificiel|continu|intermittent)',
                       r'(\d+)\s*(?:heures?|h)\s*(?:de\s*)?(?:lumière|éclairage)',
                       r'(?:photopériode|cycle\s*lumineux)\s*[:\-]?\s*(\d+)\s*(?:heures?|h)'],
                "en": [r'(?:lighting|light)\s*[:\-]?\s*(natural|artificial|continuous|intermittent)',
                       r'(\d+)\s*(?:hours?|h)\s*(?:of\s*)?light',
                       r'(?:photoperiod|light\s*cycle)\s*[:\-]?\s*(\d+)\s*(?:hours?|h)'],
                "es": [r'(?:iluminación|luz)\s*[:\-]?\s*(natural|artificial|continua|intermitente)',
                       r'(\d+)\s*(?:horas?|h)\s*(?:de\s*)?luz',
                       r'(?:fotoperíodo|ciclo\s*de\s*luz)\s*[:\-]?\s*(\d+)\s*(?:horas?|h)']
            },
            
            # === VENTILATION ===
            "ventilation": {
                "fr": [r'ventilation\s*[:\-]?\s*(bonne|mauvaise|adequate|insuffisante|excessive)',
                       r'(?:aération|circulation\s*air)\s*[:\-]?\s*(bonne|mauvaise)'],
                "en": [r'ventilation\s*[:\-]?\s*(good|poor|adequate|insufficient|excessive)',
                       r'(?:air\s*flow|circulation)\s*[:\-]?\s*(good|poor)'],
                "es": [r'ventilación\s*[:\-]?\s*(buena|mala|adecuada|insuficiente|excesiva)',
                       r'(?:aireación|circulación\s*aire)\s*[:\-]?\s*(buena|mala)']
            },
            
            # === SYMPTÔMES ===
            "symptoms": {
                "fr": [r'\b(diarrhée|boiterie|toux|éternuements|léthargie|perte\s*appétit|fièvre|convulsions)',
                       r'\b(plumes\s*ébouriffées|crete\s*pâle|respiration\s*difficile)',
                       r'\b(soif\s*excessive|tremblements|paralysie|saignements)'],
                "en": [r'\b(diarrhea|lameness|cough|sneezing|lethargy|loss\s*appetite|fever|convulsions)',
                       r'\b(ruffled\s*feathers|pale\s*comb|difficult\s*breathing)',
                       r'\b(excessive\s*thirst|trembling|paralysis|bleeding)'],
                "es": [r'\b(diarrea|cojera|tos|estornudos|letargo|pérdida\s*apetito|fiebre|convulsiones)',
                       r'\b(plumas\s*erizadas|cresta\s*pálida|respiración\s*difícil)',
                       r'\b(sed\s*excesiva|temblores|parálisis|sangrado)']
            },
            
            # === LOGEMENT ===
            "housing": {
                "fr": [r'(?:logement|hébergement|bâtiment)\s*[:\-]?\s*(cage|sol|plein\s*air|volière)',
                       r'\b(élevage\s*en\s*(?:cage|batterie|sol|plein\s*air))',
                       r'(?:densité|superficie)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:kg/m²|oiseaux/m²)'],
                "en": [r'(?:housing|accommodation|building)\s*[:\-]?\s*(cage|floor|free\s*range|aviary)',
                       r'\b((?:cage|battery|floor|free\s*range)\s*system)',
                       r'(?:density|space)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:kg/m²|birds/m²)'],
                "es": [r'(?:alojamiento|edificio)\s*[:\-]?\s*(jaula|suelo|campo\s*libre|aviario)',
                       r'\b(sistema\s*(?:de\s*)?(?:jaula|suelo|campo\s*libre))',
                       r'(?:densidad|espacio)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:kg/m²|aves/m²)']
            },
            
            # === ALIMENTATION ===
            "feed": {
                "all": [
                    r'(?:consommation|consumption|consumo)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:g|kg)',
                    r'(?:conversion|ratio)\s*[:\-]?\s*(\d+(?:\.\d+)?)',
                    r'FCR\s*[:\-]?\s*(\d+(?:\.\d+)?)',
                    r'IC\s*[:\-]?\s*(\d+(?:\.\d+)?)',  # Indice de conversion
                    r'(?:aliment|feed|pienso)\s*[:\-]?\s*(starter|grower|finisher|démarrage|croissance|finition)'
                ]
            },
            
            # === TAILLE TROUPEAU ===
            "flock_size": {
                "all": [
                    r'(\d+)\s*(?:poulets?|chickens?|pollos?|oiseaux|birds|aves)',
                    r'(?:troupeau|flock|lote)\s*(?:de\s*)?(\d+)',
                    r'(\d+)\s*têtes?',
                    r'lot\s*(?:de\s*)?(\d+)'
                ]
            },
            
            # === VACCINATION ===
            "vaccination": {
                "fr": [r'vaccin\w*\s*[:\-]?\s*(fait|ok|complet|retard|manquant)',
                       r'vaccination\s*[:\-]?\s*(à\s*jour|en\s*retard|complète)',
                       r'\b(marek|gumboro|newcastle|bronchite|salmonelle)'],
                "en": [r'vaccin\w*\s*[:\-]?\s*(done|ok|complete|delayed|missing)',
                       r'vaccination\s*[:\-]?\s*(up\s*to\s*date|delayed|complete)',
                       r'\b(marek|gumboro|newcastle|bronchitis|salmonella)'],
                "es": [r'vacun\w*\s*[:\-]?\s*(hecha|ok|completa|retrasada|faltante)',
                       r'vacunación\s*[:\-]?\s*(al\s*día|retrasada|completa)',
                       r'\b(marek|gumboro|newcastle|bronquitis|salmonela)']
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
        
        # === TEMPÉRATURE ===
        temp_patterns = self.extraction_patterns["temperature"]["all"]
        for pattern in temp_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                temp = float(match.group(1))
                if "f" in pattern.lower() or "fahrenheit" in context_lower:
                    temp = (temp - 32) * 5/9  # Conversion F -> C
                    entities.temperature_unit = "fahrenheit_converted"
                entities.temperature = temp
                entities.temperature_confidence = 0.8
                break
        
        # === HUMIDITÉ ===
        humidity_patterns = self.extraction_patterns["humidity"]["all"]
        for pattern in humidity_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities.humidity = float(match.group(1))
                entities.humidity_confidence = 0.8
                break
        
        # === MORTALITÉ ===
        mortality_patterns = self.extraction_patterns["mortality"]["all"]
        for pattern in mortality_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:  # Format "X sur Y morts"
                    dead = int(match.group(1))
                    total = int(match.group(2))
                    entities.mortality_rate = (dead / total) * 100
                else:
                    entities.mortality_rate = float(match.group(1))
                entities.mortality_confidence = 0.8
                break
        
        # === SYMPTÔMES ===
        symptom_patterns = self.extraction_patterns["symptoms"].get(language, [])
        detected_symptoms = []
        for pattern in symptom_patterns:
            matches = re.findall(pattern, context_lower, re.IGNORECASE)
            detected_symptoms.extend(matches)
        
        if detected_symptoms:
            entities.symptoms = list(set(detected_symptoms))  # Dédoublonnage
            entities.symptoms_confidence = 0.7
        
        # === ÉCLAIRAGE ===
        lighting_patterns = self.extraction_patterns["lighting"].get(language, [])
        for pattern in lighting_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                if match.group(1).isdigit():
                    entities.lighting_hours = float(match.group(1))
                    entities.lighting = "measured"
                else:
                    entities.lighting = match.group(1)
                entities.lighting_confidence = 0.7
                break
        
        # === VENTILATION ===
        ventilation_patterns = self.extraction_patterns["ventilation"].get(language, [])
        for pattern in ventilation_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities.ventilation = match.group(1)
                entities.ventilation_confidence = 0.7
                break
        
        # === LOGEMENT ===
        housing_patterns = self.extraction_patterns["housing"].get(language, [])
        for pattern in housing_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                if match.group(1).replace(".", "").isdigit():
                    entities.housing_density = float(match.group(1))
                else:
                    entities.housing_type = match.group(1)
                break
        
        # === TAILLE TROUPEAU ===
        flock_patterns = self.extraction_patterns["flock_size"]["all"]
        for pattern in flock_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities.flock_size = int(match.group(1))
                break
        
        # === ALIMENTATION ===
        feed_patterns = self.extraction_patterns["feed"]["all"]
        for pattern in feed_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                if match.group(1).replace(".", "").isdigit():
                    if "conversion" in pattern or "fcr" in pattern or "ic" in pattern:
                        entities.feed_conversion_ratio = float(match.group(1))
                    else:
                        entities.feed_consumption = float(match.group(1))
                break
        
        # === VACCINATION ===
        vacc_patterns = self.extraction_patterns["vaccination"].get(language, [])
        detected_vaccines = []
        for pattern in vacc_patterns:
            matches = re.findall(pattern, context_lower, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], str) and matches[0] not in ["fait", "ok", "done", "hecha"]:
                    detected_vaccines.extend(matches)
                else:
                    entities.vaccination_status = matches[0]
        
        if detected_vaccines:
            entities.vaccination_schedule = list(set(detected_vaccines))
    
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
            
            # Extraction de patterns sémantiques
            for token in doc:
                # Recherche de relations sémantiques
                if token.pos_ == "NUM":
                    # Nombre suivi d'une unité
                    next_tokens = doc[token.i:token.i+3] if token.i < len(doc)-2 else []
                    next_text = " ".join([t.text for t in next_tokens]).lower()
                    
                    if any(unit in next_text for unit in ["jour", "day", "día"]) and not entities.age_days:
                        try:
                            entities.age_days = int(token.text)
                            entities.age_confidence = max(entities.age_confidence, 0.6)
                        except ValueError:
                            pass
                    
                    elif any(unit in next_text for unit in ["gramme", "gram", "g"]) and not entities.weight_grams:
                        try:
                            entities.weight_grams = float(token.text)
                            entities.weight_confidence = max(entities.weight_confidence, 0.6)
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
        
        # Contexte environnemental
        env_parts = []
        if entities.temperature:
            env_parts.append(f"{entities.temperature}°C")
        if entities.humidity:
            env_parts.append(f"{entities.humidity}% HR")
        if entities.ventilation:
            env_parts.append(f"ventilation {entities.ventilation}")
        
        if env_parts:
            context_parts.append(template_set["context_environment"].format(
                environment=", ".join(env_parts)
            ))
        
        # Contexte santé
        if entities.symptoms:
            symptoms_str = ", ".join(entities.symptoms[:3])
            context_parts.append(template_set["context_health"].format(
                health=f"symptômes: {symptoms_str}"
            ))
        
        # Assembler la question enrichie
        enriched = question.lower() if context_prefix else question
        
        if context_prefix:
            if any(word in question.lower() for word in ["son", "sa", "ses", "leur", "leurs", "their", "its", "su", "sus"]):
                enriched = f"{context_prefix}, {enriched}"
            else:
                enriched = f"{context_prefix}: {enriched}"
        
        # Ajouter contextes additionnels
        if context_parts:
            enriched += "\n" + " | ".join(context_parts)
        
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
# ✅ NOUVELLE CLASSE APIEnhancementService AJOUTÉE
# =============================================================================

class APIEnhancementService:
    """Service d'amélioration API - Wrapper pour les nouvelles fonctionnalités"""
    
    def __init__(self):
        self.rag_enhancer = EnhancedRAGContextEnhancer()
        logger.info("✅ [API Enhancement Service] Service d'amélioration API initialisé")
    
    def detect_vagueness(self, question: str, language: str = "fr"):
        """Détecte les questions floues"""
        from .expert_models import VaguenessDetection, QuestionClarity
        
        # Implémentation basique de détection de flou
        question_lower = question.lower().strip()
        
        # Patterns de questions floues
        vague_patterns = [
            r'^(comment|how|cómo)',
            r'^(pourquoi|why|por qué)',
            r'^(que faire|what to do|qué hacer)',
            r'\b(problème|problem|problema)\b',
            r'\b(aide|help|ayuda)\b'
        ]
        
        missing_specifics = []
        vagueness_score = 0.0
        
        # Vérifier les patterns flous
        for pattern in vague_patterns:
            if re.search(pattern, question_lower):
                vagueness_score += 0.2
        
        # Vérifier la longueur
        if len(question_lower.split()) < 5:
            vagueness_score += 0.3
            missing_specifics.append("Question trop courte")
        
        # Vérifier les détails manquants
        if not re.search(r'\d+', question_lower):
            vagueness_score += 0.2
            missing_specifics.append("Pas de données numériques")
        
        # Vérifier les mentions de race/âge
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
        
        # Suggestion de clarification
        suggested_clarification = None
        if vagueness_score > 0.5:
            if language == "fr":
                suggested_clarification = "Pouvez-vous préciser la race, l'âge et les conditions spécifiques ?"
            elif language == "en":
                suggested_clarification = "Could you specify the breed, age and specific conditions?"
            else:
                suggested_clarification = "¿Podría especificar la raza, edad y condiciones específicas?"
        
        return VaguenessDetection(
            is_vague=vagueness_score > 0.5,
            vagueness_score=vagueness_score,
            missing_specifics=missing_specifics,
            question_clarity=clarity,
            suggested_clarification=suggested_clarification,
            actionable=vagueness_score < 0.8,
            detected_patterns=[p for p in vague_patterns if re.search(p, question_lower)]
        )
    
    def check_context_coherence(self, rag_response: str, extracted_entities: Dict, rag_context: Dict, original_question: str):
        """Vérifie la cohérence entre contexte et RAG"""
        from .expert_models import ContextCoherence
        
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
        
        return ContextCoherence(
            entities_match=entities_match,
            missing_critical_info=missing_critical_info,
            rag_assumptions={},
            coherence_score=coherence_score,
            warnings=warnings,
            recommended_clarification=None,
            entities_used_in_rag=extracted_entities
        )
    
    def create_enhanced_fallback(self, failure_point: str, last_entities: Dict, confidence: float, error: Exception, context: Dict):
        """Crée un fallback enrichi avec diagnostics"""
        from .expert_models import EnhancedFallbackDetails
        
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
    
    def calculate_quality_metrics(self, question: str, response: str, rag_score: float, coherence_result, vagueness_result):
        """Calcule les métriques de qualité"""
        from .expert_models import QualityMetrics
        
        # Calculs basiques de qualité
        response_completeness = min(len(response) / 200, 1.0)  # 200 chars = complet
        information_accuracy = rag_score if rag_score else 0.5
        contextual_relevance = coherence_result.coherence_score if coherence_result else 0.5
        
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
        
        return QualityMetrics(
            response_completeness=response_completeness,
            information_accuracy=information_accuracy,
            contextual_relevance=contextual_relevance,
            user_satisfaction_prediction=user_satisfaction_prediction,
            response_length_appropriateness=length_score,
            technical_accuracy=rag_score
        )
    
    def create_detailed_document_relevance(self, rag_result: Dict, question: str, context: str):
        """Crée un scoring RAG détaillé"""
        from .expert_models import DocumentRelevance, ConfidenceLevel
        
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
        
        return DocumentRelevance(
            score=score,
            source_document=source_document,
            matched_section=matched_section,
            confidence_level=confidence,
            chunk_used=source_document[:100] + "..." if source_document else None,
            alternative_documents=[s.get('preview', '')[:50] for s in sources[1:3]] if len(sources) > 1 else [],
            search_query_used=question[:100]
        )

# =============================================================================
# INTÉGRATION DANS EXPERT SERVICES
# =============================================================================

def update_expert_services_with_enhanced_context():
    """Instructions pour intégrer dans expert_services.py"""
    
    integration_code = '''
    # Dans expert_services.py, remplacer:
    # self.rag_enhancer = RAGContextEnhancer()
    
    # Par:
    from .api_enhancement_service import EnhancedRAGContextEnhancer, APIEnhancementService
    
    def __init__(self):
        self.integrations = IntegrationsManager()
        self.rag_enhancer = EnhancedRAGContextEnhancer()  # ← Version améliorée
        self.enhancement_service = APIEnhancementService()  # ← Nouveau service
    
    # Le reste du code reste identique - compatibilité totale
    '''
    
    return integration_code

# =============================================================================
# LOGGING ET CONFIGURATION
# =============================================================================

logger.info("✅ [Enhanced RAG Context Enhancer] Extracteur d'entités avancé initialisé")
logger.info("🚀 [Enhanced RAG Context Enhancer] NOUVELLES CAPACITÉS:")
logger.info("   - 🏷️ 15+ types d'entités extraites (vs 3 avant)")
logger.info("   - 🧠 Extraction hybride regex + NLP SpaCy")
logger.info("   - 🌐 Support multilingue complet (FR/EN/ES)")
logger.info("   - 📊 Scores de confiance par entité")
logger.info("   - 🎯 Enrichissement contextuel avancé")
logger.info("   - 🔍 Détection pronoms étendus")
logger.info(f"   - 🤖 SpaCy disponible: {'✅' if SPACY_AVAILABLE else '❌ (regex only)'}")
logger.info("✅ [API Enhancement Service] Service d'amélioration API ajouté et fonctionnel")