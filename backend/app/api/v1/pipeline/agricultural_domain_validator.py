"""
app/api/v1/agricultural_domain_validator.py

Module spécialisé pour la validation des questions dans le domaine agricole.
Garantit que les questions sont liées à l'élevage, la santé animale et la nutrition.
Intégré avec le système de configuration Intelia.

CORRECTIONS APPORTÉES:
- Import logging corrigé avec fallback
- Gestion d'erreurs renforcée pour les imports optionnels
- Validation des paramètres d'entrée
- Thread safety pour l'instance singleton
- Gestion d'erreurs pour le logger de rejets
- Validation des types et valeurs par défaut
- Optimisation des performances
"""

import re
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import json
import os
import threading
from pathlib import Path

# Configuration du logging avec fallback
try:
    import logging.handlers
    LOGGING_HANDLERS_AVAILABLE = True
except ImportError:
    LOGGING_HANDLERS_AVAILABLE = False

# Import des settings Intelia avec gestion d'erreur robuste
try:
    from app.config.settings import settings
    SETTINGS_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ [AgriculturalValidator] Settings Intelia chargés avec succès")
except ImportError as e:
    SETTINGS_AVAILABLE = False
    settings = None
    # Fallback logger configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ [AgriculturalValidator] Settings Intelia non disponibles: {e}")
except Exception as e:
    SETTINGS_AVAILABLE = False
    settings = None
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"❌ [AgriculturalValidator] Erreur lors du chargement des settings: {e}")

@dataclass
class ValidationResult:
    """Résultat de la validation d'une question agricole"""
    is_valid: bool
    confidence: float
    reason: Optional[str] = None
    suggested_topics: Optional[List[str]] = None
    detected_keywords: Optional[List[str]] = None
    rejected_keywords: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validation des données après initialisation"""
        # Validation de la confiance
        if not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence doit être un nombre")
        
        if not 0 <= self.confidence <= 100:
            raise ValueError("confidence doit être entre 0 et 100")
        
        # Initialisation des listes si None
        if self.suggested_topics is None:
            self.suggested_topics = []
        if self.detected_keywords is None:
            self.detected_keywords = []
        if self.rejected_keywords is None:
            self.rejected_keywords = []
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour les logs"""
        return {
            "is_valid": self.is_valid,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "suggested_topics": self.suggested_topics,
            "detected_keywords": self.detected_keywords,
            "rejected_keywords": self.rejected_keywords
        }

class AgriculturalDomainValidator:
    """
    Validateur pour garantir que les questions concernent le domaine agricole.
    Intégré avec le système de configuration Intelia.
    Thread-safe singleton pattern.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implémentation singleton thread-safe"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialise le validateur avec la configuration Intelia"""
        
        # Éviter la réinitialisation du singleton
        if hasattr(self, '_initialized'):
            return
        
        try:
            self._load_configuration()
            self._init_keywords()
            self._init_rejection_logger()
            self._initialized = True
            
            logger.info(f"🔧 [AgriculturalValidator] Validation agricole: {'✅ Activée' if self.enabled else '❌ Désactivée'}")
            logger.info(f"🔧 [AgriculturalValidator] Seuil de confiance: {self.strictness}%")
            logger.info(f"🔧 [AgriculturalValidator] Settings disponibles: {'✅ Oui' if SETTINGS_AVAILABLE else '❌ Non'}")
            
        except Exception as e:
            logger.error(f"❌ [AgriculturalValidator] Erreur lors de l'initialisation: {e}")
            # Configuration par défaut en cas d'erreur
            self._set_default_configuration()
            self._initialized = True

    def _load_configuration(self):
        """Charge la configuration depuis les settings ou variables d'environnement"""
        
        if SETTINGS_AVAILABLE and settings:
            try:
                self.enabled = getattr(settings, 'agricultural_validation_enabled', True)
                self.strictness = float(getattr(settings, 'agricultural_validation_strictness', 15.0))
                self.allow_override = getattr(settings, 'agricultural_validation_override_allowed', False)
                self.log_all_validations = getattr(settings, 'agricultural_validation_log_all', True)
                self.log_dir = getattr(settings, 'agricultural_validation_log_dir', 'logs')
                self.log_max_size = int(getattr(settings, 'agricultural_validation_log_max_size', 10485760))
                self.log_backup_count = int(getattr(settings, 'agricultural_validation_log_backup_count', 5))
                
                logger.info("✅ [AgriculturalValidator] Configuration chargée depuis les settings Intelia")
                
            except Exception as e:
                logger.warning(f"⚠️ [AgriculturalValidator] Erreur settings Intelia: {e}, utilisation fallback")
                self._load_environment_configuration()
        else:
            self._load_environment_configuration()
    
    def _load_environment_configuration(self):
        """Charge la configuration depuis les variables d'environnement"""
        try:
            self.enabled = os.getenv('ENABLE_AGRICULTURAL_VALIDATION', 'true').lower() == 'true'
            self.strictness = float(os.getenv('VALIDATION_STRICTNESS', '15.0'))
            self.allow_override = os.getenv('ALLOW_VALIDATION_OVERRIDE', 'false').lower() == 'true'
            self.log_all_validations = os.getenv('LOG_ALL_VALIDATIONS', 'true').lower() == 'true'
            self.log_dir = os.getenv('VALIDATION_LOGS_DIR', 'logs')
            self.log_max_size = int(os.getenv('VALIDATION_LOG_MAX_SIZE', '10485760'))
            self.log_backup_count = int(os.getenv('VALIDATION_LOG_BACKUP_COUNT', '5'))
            
            # Validation des valeurs
            if not 0 <= self.strictness <= 100:
                logger.warning(f"⚠️ Strictness invalide: {self.strictness}, utilisation valeur par défaut: 15.0")
                self.strictness = 15.0
            
            if self.log_max_size <= 0:
                logger.warning(f"⚠️ Taille log invalide: {self.log_max_size}, utilisation valeur par défaut")
                self.log_max_size = 10485760
            
            if self.log_backup_count < 0:
                logger.warning(f"⚠️ Nombre backups invalide: {self.log_backup_count}, utilisation valeur par défaut")
                self.log_backup_count = 5
                
            logger.info("✅ [AgriculturalValidator] Configuration chargée depuis les variables d'environnement")
            
        except (ValueError, TypeError) as e:
            logger.error(f"❌ [AgriculturalValidator] Erreur configuration environnement: {e}")
            self._set_default_configuration()
    
    def _set_default_configuration(self):
        """Configuration par défaut en cas d'erreur"""
        self.enabled = True
        self.strictness = 15.0
        self.allow_override = False
        self.log_all_validations = True
        self.log_dir = 'logs'
        self.log_max_size = 10485760
        self.log_backup_count = 5
        logger.info("✅ [AgriculturalValidator] Configuration par défaut appliquée")

    def _init_keywords(self):
        """Initialise tous les dictionnaires de mots-clés"""
        
        self.agricultural_keywords = {
            "fr": [
                # === ANIMAUX D'ÉLEVAGE ===
                "poulet", "poulets", "poule", "poules", "volaille", "volailles", "coq", "coqs",
                "poussin", "poussins", "œuf", "œufs", "oeuf", "oeufs", "aviculture", "aviaire",
                "porc", "porcs", "cochon", "cochons", "truie", "truies", "verrat", "verrats",
                "porcelet", "porcelets", "suidé", "suidés", "porcin", "porcins", "porcherie",
                "vache", "vaches", "taureau", "taureaux", "veau", "veaux", "génisse", "génisses",
                "bovin", "bovins", "bœuf", "bœufs", "boeuf", "boeufs", "étable", "étables",
                "mouton", "moutons", "brebis", "agneau", "agneaux", "chèvre", "chèvres",
                "chevreau", "chevreaux", "caprin", "caprins", "ovin", "ovins", "bergerie",
                "cheval", "chevaux", "jument", "juments", "poulain", "poulains", "équin",
                "équins", "équidé", "équidés", "écurie", "écuries",
                
                # === RACES ET LIGNÉES SPÉCIALISÉES ===
                "ross", "ross 308", "ross 708", "cobb", "cobb 500", "cobb 700", "hybride",
                "lignée", "lignées", "souche", "souches", "race", "races", "breed",
                "hubbard", "arbor acres", "isa", "lohmann", "brown", "white",
                
                # === SANTÉ ANIMALE ===
                "vétérinaire", "vétérinaires", "vaccination", "vaccin", "vaccins", "maladie",
                "maladies", "pathologie", "pathologies", "mortalité", "mort", "morts", "décès",
                "symptôme", "symptômes", "diagnostic", "diagnostics", "diagnostique",
                "traitement", "traitements", "médicament", "médicaments", "antibiotique",
                "antibiotiques", "thérapie", "thérapies", "soin", "soins", "prévention",
                "hygiène", "désinfection", "biosécurité", "quarantaine", "parasite", "parasites",
                "virus", "bactérie", "bactéries", "infection", "infections", "épidémie",
                "épidémies", "enzootie", "enzooties", "zoonose", "zoonoses", "bien-être",
                "stress", "souffrance", "coccidiose", "salmonelle", "gumboro", "newcastle",
                "bronchite", "laryngotrachéite", "marek", "leucose", "influenza",
                
                # === NUTRITION ANIMALE ===
                "nutrition", "alimentation", "aliment", "aliments", "nourriture", "ration",
                "rations", "régime", "régimes", "fourrage", "fourrages", "foin", "paille",
                "grain", "grains", "céréale", "céréales", "maïs", "blé", "orge", "avoine",
                "soja", "tourteau", "tourteaux", "protéine", "protéines", "vitamine",
                "vitamines", "minéral", "minéraux", "complément", "compléments", "additif",
                "additifs", "eau", "abreuvoir", "abreuvoirs", "mangeoire", "mangeoires",
                "distributeur", "distributeurs", "silo", "silos", "conversion", "digestibilité",
                "appétabilité", "starter", "grower", "finisher", "prémix", "concentré",
                
                # === ÉLEVAGE ET PRODUCTION ===
                "élevage", "elevage", "ferme", "fermes", "exploitation", "exploitations",
                "agricole", "agricoles", "agriculture", "production", "producteur",
                "producteurs", "éleveur", "éleveurs", "eleveur", "eleveurs", "agriculteur",
                "agriculteurs", "bâtiment", "bâtiments", "stabulation", "poulailler",
                "poulaillers", "volière", "volières", "nursery", "maternité", "croissance",
                "poids", "gain", "gains", "développement", "performance", "performances",
                "reproduction", "gestation", "mise-bas", "sevrage", "lactation",
                "insémination", "saillie", "saillies", "chaleurs", "œstrus", "estrus",
                "cycle", "cycles", "batch", "bande", "bandes", "lot", "lots",
                
                # === ENVIRONNEMENT D'ÉLEVAGE ===
                "température", "températures", "ventilation", "air", "humidité", "aération",
                "chauffage", "refroidissement", "climat", "ambiance", "microclimat",
                "éclairage", "lumière", "photopériode", "obscurité", "densité", "espace",
                "surface", "logement", "hébergement", "litière", "litières", "paillage",
                "caillebotis", "sol", "sols", "barn", "bâtiment fermé", "plein air",
                
                # === GESTION TECHNIQUE ===
                "protocole", "protocoles", "programme", "programmes", "plan", "plans",
                "conduite", "régie", "management", "surveillance", "monitoring", "contrôle",
                "suivi", "observation", "analyse", "analyses", "mesure", "mesures",
                "indicateur", "indicateurs", "paramètre", "paramètres", "kpi", "optimisation",
                "amélioration", "correction", "ajustement", "rotation", "rotations",
                
                # === ÉCONOMIE AGRICOLE ===
                "coût", "coûts", "prix", "rentabilité", "marge", "marges", "bénéfice",
                "bénéfices", "investissement", "investissements", "amortissement", "charges",
                "produit", "produits", "chiffre", "économie", "économique", "financier",
                
                # === RÉGLEMENTATION ET QUALITÉ ===
                "norme", "normes", "standard", "standards", "certification", "certifications",
                "label", "labels", "qualité", "traçabilité", "sécurité", "haccp", "iso",
                "gmp", "brc", "ifs", "réglementation", "règlement",
                
                # === TERMES TECHNIQUES SPÉCIALISÉS ===
                "zootechnie", "zootechnique", "zootechniques", "cuniculture", "apiculture",
                "pisciculture", "aquaculture", "éthologie", "physiologie", "anatomie",
                "histologie", "immunologie", "endocrinologie", "pharmacologie",
                
                # === ÉQUIPEMENTS ET MATÉRIEL ===
                "équipement", "équipements", "matériel", "machine", "machines", "tracteur",
                "épandeur", "mélangeur", "broyeur", "distributeur automatique", "capteur",
                "capteurs", "sonde", "sondes", "thermomètre", "hygromètre"
            ],
            
            "en": [
                # === LIVESTOCK ANIMALS ===
                "chicken", "chickens", "poultry", "broiler", "broilers", "layer", "layers",
                "rooster", "roosters", "hen", "hens", "chick", "chicks", "egg", "eggs",
                "aviculture", "avian", "pig", "pigs", "swine", "hog", "hogs", "sow", "sows",
                "boar", "boars", "piglet", "piglets", "pork", "cattle", "cow", "cows",
                "bull", "bulls", "calf", "calves", "heifer", "heifers", "beef", "dairy",
                "sheep", "ewe", "ewes", "lamb", "lambs", "goat", "goats", "kid", "kids",
                "horse", "horses", "mare", "mares", "stallion", "stallions", "foal", "foals",
                
                # === BREEDS AND LINES ===
                "ross", "ross 308", "ross 708", "cobb", "cobb 500", "cobb 700", "hybrid",
                "breed", "breeds", "strain", "strains", "line", "lines", "genetic",
                "hubbard", "arbor acres", "isa", "lohmann", "brown", "white",
                
                # === ANIMAL HEALTH ===
                "veterinary", "veterinarian", "vaccination", "vaccine", "vaccines", "disease",
                "diseases", "pathology", "pathologies", "mortality", "death", "deaths",
                "symptom", "symptoms", "diagnosis", "diagnostic", "treatment", "treatments",
                "medicine", "medicines", "antibiotic", "antibiotics", "therapy", "therapies",
                "care", "prevention", "hygiene", "disinfection", "biosecurity", "quarantine",
                "parasite", "parasites", "virus", "bacteria", "infection", "infections",
                "epidemic", "epidemics", "welfare", "stress", "coccidiosis", "salmonella",
                "gumboro", "newcastle", "bronchitis", "laryngotracheitis", "marek",
                
                # === ANIMAL NUTRITION ===
                "nutrition", "feeding", "feed", "feeds", "food", "ration", "rations",
                "diet", "diets", "forage", "forages", "hay", "straw", "grain", "grains",
                "cereal", "cereals", "corn", "wheat", "barley", "oats", "soybean", "soy",
                "meal", "protein", "proteins", "vitamin", "vitamins", "mineral", "minerals",
                "supplement", "supplements", "additive", "additives", "water", "drinker",
                "drinkers", "feeder", "feeders", "silo", "silos", "conversion", "digestibility",
                "palatability", "starter", "grower", "finisher", "premix", "concentrate",
                
                # === LIVESTOCK FARMING ===
                "livestock", "farming", "farm", "farms", "agricultural", "agriculture",
                "production", "producer", "producers", "farmer", "farmers", "building",
                "buildings", "housing", "barn", "barns", "nursery", "growth", "weight",
                "gain", "gains", "development", "performance", "reproduction", "gestation",
                "farrowing", "weaning", "lactation", "insemination", "breeding", "heat",
                "estrus", "cycle", "cycles", "batch", "batches", "flock", "flocks",
                
                # === ENVIRONMENT ===
                "temperature", "temperatures", "ventilation", "air", "humidity", "heating",
                "cooling", "climate", "environment", "lighting", "light", "photoperiod",
                "darkness", "density", "space", "surface", "bedding", "litter", "floor",
                "floors", "outdoor", "indoor", "free-range",
                
                # === TECHNICAL MANAGEMENT ===
                "protocol", "protocols", "program", "programs", "plan", "plans", "management",
                "monitoring", "control", "surveillance", "observation", "analysis", "measure",
                "measures", "indicator", "indicators", "parameter", "parameters", "kpi",
                "optimization", "improvement", "correction", "adjustment", "rotation",
                
                # === AGRICULTURAL ECONOMICS ===
                "cost", "costs", "price", "prices", "profitability", "margin", "margins",
                "profit", "profits", "investment", "investments", "economy", "economic",
                "financial",
                
                # === STANDARDS AND QUALITY ===
                "standard", "standards", "certification", "certifications", "label", "labels",
                "quality", "traceability", "safety", "haccp", "iso", "gmp", "brc", "ifs",
                "regulation", "regulations",
                
                # === SPECIALIZED TERMS ===
                "zootechnics", "animal science", "aquaculture", "ethology", "physiology",
                "anatomy", "histology", "immunology", "endocrinology", "pharmacology",
                
                # === EQUIPMENT ===
                "equipment", "machinery", "machine", "machines", "tractor", "spreader",
                "mixer", "grinder", "automatic feeder", "sensor", "sensors", "probe",
                "probes", "thermometer", "hygrometer"
            ],
            
            "es": [
                # === ANIMALES DE GRANJA ===
                "pollo", "pollos", "gallina", "gallinas", "gallo", "gallos", "pollito",
                "pollitos", "ave", "aves", "huevo", "huevos", "avicultura", "aviar",
                "cerdo", "cerdos", "cochino", "cochinos", "marrana", "marranas", "verraco",
                "verracos", "lechón", "lechones", "porcino", "porcinos", "porqueriza",
                "vaca", "vacas", "toro", "toros", "ternero", "terneros", "novilla", "novillas",
                "bovino", "bovinos", "ganado", "establo", "establos", "oveja", "ovejas",
                "cordero", "corderos", "cabra", "cabras", "cabrito", "cabritos", "caprino",
                "caprinos", "ovino", "ovinos", "redil", "caballo", "caballos", "yegua",
                "yeguas", "potro", "potros", "equino", "equinos",
                
                # === RAZAS Y LÍNEAS ===
                "ross", "ross 308", "ross 708", "cobb", "cobb 500", "cobb 700", "híbrido",
                "línea", "líneas", "cepa", "cepas", "raza", "razas", "hubbard", "arbor acres",
                "isa", "lohmann", "brown", "white",
                
                # === SALUD ANIMAL ===
                "veterinario", "veterinarios", "vacunación", "vacuna", "vacunas", "enfermedad",
                "enfermedades", "patología", "patologías", "mortalidad", "muerte", "muertes",
                "síntoma", "síntomas", "diagnóstico", "diagnósticos", "tratamiento",
                "tratamientos", "medicamento", "medicamentos", "antibiótico", "antibióticos",
                "terapia", "terapias", "cuidado", "cuidados", "prevención", "higiene",
                "desinfección", "bioseguridad", "cuarentena", "parásito", "parásitos",
                "virus", "bacteria", "bacterias", "infección", "infecciones", "epidemia",
                "epidemias", "bienestar", "estrés", "coccidiosis", "salmonela", "gumboro",
                "newcastle", "bronquitis", "laringotraqueítis", "marek",
                
                # === NUTRICIÓN ANIMAL ===
                "nutrición", "alimentación", "alimento", "alimentos", "comida", "ración",
                "raciones", "dieta", "dietas", "forraje", "forrajes", "heno", "paja",
                "grano", "granos", "cereal", "cereales", "maíz", "trigo", "cebada", "avena",
                "soja", "harina", "proteína", "proteínas", "vitamina", "vitaminas", "mineral",
                "minerales", "suplemento", "suplementos", "aditivo", "aditivos", "agua",
                "bebedero", "bebederos", "comedero", "comederos", "silo", "silos", "conversión",
                "digestibilidad", "palatabilidad", "iniciador", "crecimiento", "terminador",
                "premezcla", "concentrado",
                
                # === GANADERÍA Y PRODUCCIÓN ===
                "ganadería", "granja", "granjas", "explotación", "explotaciones", "agrícola",
                "agrícolas", "agricultura", "producción", "productor", "productores",
                "ganadero", "ganaderos", "agricultor", "agricultores", "edificio", "edificios",
                "alojamiento", "gallinero", "gallineros", "vivero", "crecimiento", "peso",
                "ganancia", "ganancias", "desarrollo", "rendimiento", "reproducción",
                "gestación", "parto", "destete", "lactación", "inseminación", "monta",
                "celo", "ciclo", "ciclos", "lote", "lotes", "rebaño", "rebaños",
                
                # === AMBIENTE ===
                "temperatura", "temperaturas", "ventilación", "aire", "humedad", "calefacción",
                "enfriamiento", "clima", "ambiente", "iluminación", "luz", "fotoperíodo",
                "oscuridad", "densidad", "espacio", "superficie", "cama", "yacija", "suelo",
                "suelos", "aire libre", "interior",
                
                # === GESTIÓN TÉCNICA ===
                "protocolo", "protocolos", "programa", "programas", "plan", "planes",
                "manejo", "gestión", "monitoreo", "control", "vigilancia", "observación",
                "análisis", "medida", "medidas", "indicador", "indicadores", "parámetro",
                "parámetros", "optimización", "mejora", "corrección", "ajuste", "rotación",
                
                # === ECONOMÍA AGRÍCOLA ===
                "costo", "costos", "precio", "precios", "rentabilidad", "margen", "márgenes",
                "beneficio", "beneficios", "inversión", "inversiones", "economía", "económico",
                "financiero",
                
                # === ESTÁNDARES Y CALIDAD ===
                "norma", "normas", "estándar", "estándares", "certificación", "certificaciones",
                "etiqueta", "calidad", "trazabilidad", "seguridad", "haccp", "iso", "gmp",
                "brc", "ifs", "reglamento", "reglamentos",
                
                # === TÉRMINOS ESPECIALIZADOS ===
                "zootecnia", "ciencia animal", "acuicultura", "etología", "fisiología",
                "anatomía", "histología", "inmunología", "endocrinología", "farmacología",
                
                # === EQUIPOS ===
                "equipo", "equipos", "maquinaria", "máquina", "máquinas", "tractor",
                "esparcidor", "mezclador", "molino", "alimentador automático", "sensor",
                "sensores", "sonda", "sondas", "termómetro", "higrómetro"
            ]
        }
        
        self.non_agricultural_keywords = {
            "fr": [
                "finance", "finances", "banque", "banques", "investissement", "investissements",
                "bourse", "action", "actions", "crypto", "cryptomonnaie", "bitcoin", "ethereum", 
                "trading", "trader", "beauté", "maquillage", "cosmétique", "cosmétiques", 
                "mode", "vêtement", "vêtements", "fashion", "style", "tendance", "cuisine", 
                "recette", "recettes", "restaurant", "restaurants", "gastronomie", "chef", 
                "cuisinier", "sport", "football", "tennis", "basketball", "athlète", "match", 
                "compétition", "technologie", "informatique", "ordinateur", "ordinateurs", 
                "smartphone", "téléphone", "logiciel", "internet", "web", "site", "voyage", 
                "tourisme", "vacances", "hôtel", "destination", "politique", "élection", 
                "gouvernement", "député", "président", "médecine", "docteur", "hôpital", 
                "patient", "chirurgie", "humain", "humaine", "personne", "automobile", 
                "voiture", "moto", "transport", "carburant", "immobilier", "maison", 
                "appartement", "achat", "vente", "location", "cinéma", "film", "musique", 
                "concert", "art", "peinture", "littérature", "livre", "éducation", "école", 
                "université", "étudiant", "juridique", "droit", "avocat", "tribunal"
            ],
            "en": [
                "finance", "finances", "bank", "banking", "investment", "investments", "stock", 
                "stocks", "crypto", "cryptocurrency", "bitcoin", "ethereum", "trading", "trader", 
                "beauty", "makeup", "cosmetic", "cosmetics", "fashion", "clothing", "style", 
                "trend", "cooking", "recipe", "recipes", "restaurant", "restaurants", "gastronomy", 
                "chef", "culinary", "sport", "sports", "football", "tennis", "basketball", 
                "athlete", "game", "games", "competition", "technology", "computer", "computers", 
                "smartphone", "phone", "software", "internet", "web", "website", "travel", 
                "tourism", "vacation", "hotel", "destination", "politics", "election", "government", 
                "deputy", "president", "medicine", "doctor", "hospital", "patient", "surgery", 
                "human", "person", "people", "automotive", "car", "motorcycle", "transport", 
                "fuel", "real estate", "house", "apartment", "purchase", "sale", "rental", 
                "cinema", "movie", "music", "concert", "art", "painting", "literature", "book", 
                "education", "school", "university", "student", "legal", "law", "lawyer", "court"
            ],
            "es": [
                "finanzas", "banco", "inversión", "bolsa", "acción", "acciones", "crypto", 
                "criptomoneda", "bitcoin", "ethereum", "trading", "comercio", "belleza", 
                "maquillaje", "cosmético", "cosmética", "moda", "ropa", "vestimenta", "estilo", 
                "tendencia", "cocina", "receta", "recetas", "restaurante", "restaurantes", 
                "gastronomía", "chef", "cocinero", "deporte", "deportes", "fútbol", "tenis", 
                "baloncesto", "atleta", "partido", "competición", "tecnología", "computadora", 
                "ordenador", "smartphone", "teléfono", "software", "internet", "web", "sitio", 
                "viaje", "turismo", "vacaciones", "hotel", "destino", "política", "elección", 
                "gobierno", "diputado", "presidente", "medicina", "doctor", "hospital", 
                "paciente", "cirugía", "humano", "humana", "persona", "automóvil", "coche", 
                "moto", "transporte", "combustible", "inmobiliario", "casa", "apartamento", 
                "compra", "venta", "alquiler", "cine", "película", "música", "concierto", 
                "arte", "pintura", "literatura", "libro", "educación", "escuela", "universidad", 
                "estudiante", "jurídico", "derecho", "abogado", "tribunal"
            ]
        }
        
        self.suggested_topics = {
            "fr": [
                "Problèmes de croissance des poulets de chair (Ross 308, Cobb 500)",
                "Protocoles de vaccination pour volailles (Gumboro, Newcastle, Bronchite)",
                "Gestion de la température optimale dans le poulailler (32°C)",
                "Nutrition et programmes d'alimentation starter/grower/finisher",
                "Diagnostic de mortalité élevée en élevage de volailles",
                "Optimisation des performances de production (indice de conversion)",
                "Prévention des maladies aviaires (coccidiose, salmonellose)",
                "Conduite d'élevage en bâtiment fermé et ventilation"
            ],
            "en": [
                "Broiler chicken growth problems (Ross 308, Cobb 500)",
                "Poultry vaccination protocols (Gumboro, Newcastle, Bronchitis)",
                "Optimal temperature management in poultry houses (32°C)",
                "Nutrition and feeding programs starter/grower/finisher",
                "High mortality diagnosis in poultry farming",
                "Production performance optimization (feed conversion ratio)",
                "Avian disease prevention (coccidiosis, salmonellosis)",
                "Intensive housing management and ventilation systems"
            ],
            "es": [
                "Problemas de crecimiento en pollos de engorde (Ross 308, Cobb 500)",
                "Protocolos de vacunación para aves (Gumboro, Newcastle, Bronquitis)",
                "Gestión de temperatura óptima en gallineros (32°C)",
                "Nutrición y programas de alimentación iniciador/crecimiento/terminador",
                "Diagnóstico de mortalidad alta en granjas avícolas",
                "Optimización del rendimiento productivo (índice de conversión)",
                "Prevención de enfermedades aviares (coccidiosis, salmonelosis)",
                "Manejo en alojamiento intensivo y sistemas de ventilación"
            ]
        }
        
        logger.info("✅ [AgriculturalValidator] Mots-clés initialisés avec succès")

    def _init_rejection_logger(self):
        """Initialise le logger spécialisé pour les rejets avec gestion d'erreurs robuste"""
        
        self.rejection_logger = logging.getLogger("agricultural_validation_rejections")
        self.rejection_logger.setLevel(logging.INFO)
        
        # Éviter la duplication des handlers
        if self.rejection_logger.handlers:
            logger.info("✅ [AgriculturalValidator] Logger rejets déjà configuré")
            return
        
        try:
            # Créer le répertoire de logs s'il n'existe pas
            log_dir_path = Path(self.log_dir)
            log_dir_path.mkdir(parents=True, exist_ok=True)
            
            log_file_path = log_dir_path / 'agricultural_rejections.log'
            
            # Vérifier si les handlers rotatifs sont disponibles
            if LOGGING_HANDLERS_AVAILABLE:
                from logging.handlers import RotatingFileHandler
                
                rejection_handler = RotatingFileHandler(
                    str(log_file_path),
                    maxBytes=self.log_max_size,
                    backupCount=self.log_backup_count,
                    encoding='utf-8'
                )
            else:
                # Fallback vers FileHandler basique
                rejection_handler = logging.FileHandler(
                    str(log_file_path),
                    encoding='utf-8'
                )
                logger.warning("⚠️ [AgriculturalValidator] RotatingFileHandler non disponible, utilisation FileHandler")
            
            rejection_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            rejection_handler.setFormatter(rejection_formatter)
            self.rejection_logger.addHandler(rejection_handler)
            
            logger.info(f"✅ [AgriculturalValidator] Logger rejets configuré: {log_file_path}")
            
        except (OSError, PermissionError) as e:
            logger.warning(f"⚠️ [AgriculturalValidator] Impossible de créer le fichier de log rejets: {e}")
            logger.warning("⚠️ [AgriculturalValidator] Les rejets seront loggés dans le logger principal")
        except Exception as e:
            logger.error(f"❌ [AgriculturalValidator] Erreur inattendue lors de la configuration du logger rejets: {e}")

    def validate_question(self, question: str, language: str = "fr", 
                         user_id: str = "unknown", request_ip: str = "unknown") -> ValidationResult:
        """
        Valide qu'une question concerne le domaine agricole
        
        Args:
            question: La question à valider
            language: Langue de la question (fr, en, es)
            user_id: ID de l'utilisateur pour les logs
            request_ip: IP de la requête pour les logs
            
        Returns:
            ValidationResult: Résultat de la validation avec détails
            
        Raises:
            ValueError: Si les paramètres d'entrée sont invalides
        """
        
        # Validation des paramètres d'entrée
        if not isinstance(question, str):
            raise ValueError("question doit être une chaîne de caractères")
        
        if not question.strip():
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                reason=self._get_rejection_message(language, "empty_question"),
                suggested_topics=self.suggested_topics.get(language, self.suggested_topics["fr"])
            )
        
        if not isinstance(language, str) or language not in ["fr", "en", "es"]:
            logger.warning(f"⚠️ [AgriculturalValidator] Langue invalide: {language}, utilisation FR par défaut")
            language = "fr"
        
        if not isinstance(user_id, str):
            user_id = str(user_id)
        
        if not isinstance(request_ip, str):
            request_ip = str(request_ip)
        
        # Si la validation est désactivée, accepter toutes les questions
        if not self.enabled:
            logger.info(f"🔧 [AgriculturalValidator] Validation désactivée - question acceptée")
            return ValidationResult(is_valid=True, confidence=100.0)
        
        # Normalisation de la question avec gestion d'erreur
        try:
            normalized_question = self._normalize_text(question)
        except Exception as e:
            logger.error(f"❌ [AgriculturalValidator] Erreur normalisation: {e}")
            normalized_question = question.lower()
        
        validation_start = datetime.now()
        
        logger.info(f"🔍 [AgriculturalValidator] Validation question: '{question[:50]}...' (langue: {language}, user: {user_id[:8]})")
        
        try:
            # Obtenir les mots-clés pour la langue
            agri_keywords = self.agricultural_keywords.get(language, self.agricultural_keywords["fr"])
            non_agri_keywords = self.non_agricultural_keywords.get(language, self.non_agricultural_keywords["fr"])
            
            # Détecter les mots-clés
            detected_agri = self._find_keywords(normalized_question, agri_keywords)
            detected_non_agri = self._find_keywords(normalized_question, non_agri_keywords)
            
            # Calcul du score de confiance
            confidence = self._calculate_confidence(
                normalized_question, 
                len(detected_agri), 
                len(detected_non_agri)
            )
            
            # Logs détaillés
            if self.log_all_validations:
                logger.info(f"✅ [AgriculturalValidator] Mots-clés agricoles détectés ({len(detected_agri)}): {detected_agri[:5]}")
                logger.info(f"❌ [AgriculturalValidator] Mots-clés non-agricoles détectés ({len(detected_non_agri)}): {detected_non_agri[:5]}")
                logger.info(f"📊 [AgriculturalValidator] Score de confiance: {confidence:.1f}%")
            
            # === DÉCISION DE VALIDATION ===
            
            # Cas 1: Détection explicite de domaines non-agricoles
            if detected_non_agri and not detected_agri:
                result = ValidationResult(
                    is_valid=False,
                    confidence=0.0,
                    reason=self._get_rejection_message(language, "non_agricultural"),
                    suggested_topics=self.suggested_topics.get(language, self.suggested_topics["fr"]),
                    detected_keywords=[],
                    rejected_keywords=detected_non_agri
                )
                self._log_rejection(question, result, language, user_id, request_ip, "non_agricultural_domain")
                return result
            
            # Cas 2: Mots-clés agricoles détectés - validation réussie
            if detected_agri:
                result = ValidationResult(
                    is_valid=True,
                    confidence=max(confidence, 50.0),  # Bonus pour mots-clés explicites
                    detected_keywords=detected_agri
                )
                if self.log_all_validations:
                    logger.info(f"✅ [AgriculturalValidator] Question validée: {len(detected_agri)} mots-clés agricoles")
                return result
            
            # Cas 3: Score de confiance insuffisant
            if confidence < self.strictness:
                result = ValidationResult(
                    is_valid=False,
                    confidence=confidence,
                    reason=self._get_rejection_message(language, "too_general"),
                    suggested_topics=self.suggested_topics.get(language, self.suggested_topics["fr"])
                )
                self._log_rejection(question, result, language, user_id, request_ip, "insufficient_confidence")
                return result
            
            # Cas 4: Accepter avec score minimal
            result = ValidationResult(
                is_valid=True,
                confidence=confidence
            )
            if self.log_all_validations:
                logger.info(f"✅ [AgriculturalValidator] Question acceptée: score confiance {confidence:.1f}%")
            return result
            
        except Exception as e:
            logger.error(f"❌ [AgriculturalValidator] Erreur lors de la validation: {e}")
            # En cas d'erreur, accepter la question par défaut si allowed_override est True
            if self.allow_override:
                logger.warning(f"⚠️ [AgriculturalValidator] Validation échouée, acceptation par défaut (override activé)")
                return ValidationResult(is_valid=True, confidence=50.0, reason="Validation failed, default accept")
            else:
                return ValidationResult(
                    is_valid=False, 
                    confidence=0.0, 
                    reason=self._get_rejection_message(language, "validation_error")
                )

    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour la comparaison (supprime accents, ponctuation)"""
        try:
            import unicodedata
            
            # Validation d'entrée
            if not isinstance(text, str):
                text = str(text)
            
            # Convertir en minuscules
            text = text.lower()
            
            # Supprimer les accents
            text = unicodedata.normalize('NFD', text)
            text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
            
            # Nettoyer la ponctuation et espaces multiples
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"❌ [AgriculturalValidator] Erreur normalisation texte: {e}")
            # Fallback simple
            return text.lower().strip() if isinstance(text, str) else str(text).lower().strip()

    def _find_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """Trouve les mots-clés présents dans le texte avec recherche flexible"""
        if not text or not keywords:
            return []
        
        found = []
        text_words = text.split()
        
        try:
            for keyword in keywords:
                if not isinstance(keyword, str):
                    continue
                    
                keyword_lower = keyword.lower()
                
                # Recherche exacte du mot-clé
                if keyword_lower in text:
                    found.append(keyword)
                    continue
                
                # Recherche de mots similaires (racines communes pour mots > 4 caractères)
                if len(keyword_lower) > 4:
                    keyword_root = keyword_lower[:4]
                    for word in text_words:
                        if len(word) > 4 and word.startswith(keyword_root):
                            found.append(keyword)
                            break
            
            return list(set(found))  # Éliminer les doublons
            
        except Exception as e:
            logger.error(f"❌ [AgriculturalValidator] Erreur recherche mots-clés: {e}")
            return []

    def _calculate_confidence(self, text: str, agri_count: int, non_agri_count: int) -> float:
        """Calcule un score de confiance basé sur les mots-clés détectés"""
        try:
            word_count = len(text.split()) if text else 0
            
            if word_count == 0:
                return 0.0
            
            # Score basé sur la proportion de mots agricoles
            agri_ratio = (agri_count / word_count) * 100
            
            # Bonus pour multiple mots-clés agricoles
            agri_bonus = min(agri_count * 15, 60)  # Max 60% de bonus
            
            # Pénalité pour les mots non-agricoles
            non_agri_penalty = min(non_agri_count * 25, 75)  # Max 75% de pénalité
            
            # Score final
            confidence = agri_ratio + agri_bonus - non_agri_penalty
            
            return max(0.0, min(100.0, confidence))
            
        except Exception as e:
            logger.error(f"❌ [AgriculturalValidator] Erreur calcul confiance: {e}")
            return 0.0

    def _get_rejection_message(self, language: str, reason: str) -> str:
        """Retourne le message de rejet approprié selon la langue et la raison"""
        messages = {
            "fr": {
                "non_agricultural": "Je suis un expert dans le domaine avicole, donc je ne suis pas spécialisé dans la cryptomonnaie. Si vous avez des questions sur le domaine avicole, je serais ravi de vous aider.",
                "too_general": "Cette question semble trop générale ou ne contient pas assez d'éléments spécifiques au domaine avicole. Pouvez-vous la reformuler en précisant l'aspect d'élevage, de santé animale ou de nutrition qui vous intéresse ?",
                "empty_question": "Veuillez poser une question concernant l'élevage, la santé animale ou la nutrition.",
                "validation_error": "Une erreur s'est produite lors de la validation. Veuillez reformuler votre question concernant l'agriculture."
            },
            "en": {
                "non_agricultural": "I am an expert in the poultry field, so I am not specialized in cryptocurrency. If you have questions about the poultry field, I would be happy to help you.",
                "too_general": "This question seems too general or doesn't contain enough elements specific to the poultry domain. Could you rephrase it by specifying the livestock, animal health, or nutrition aspect you're interested in?",
                "empty_question": "Please ask a question about livestock, animal health, or nutrition.",
                "validation_error": "An error occurred during validation. Please rephrase your question about agriculture."
            },
            "es": {
                "non_agricultural": "Soy un experto en el campo avícola, por lo que no me especializo en criptomonedas. Si tienes preguntas sobre el campo avícola, estaría encantado de ayudarte.",
                "too_general": "Esta pregunta parece demasiado general o no contiene suficientes elementos específicos del dominio avícola. ¿Podría reformularla especificando el aspecto ganadero, de salud animal o nutrición que le interesa?",
                "empty_question": "Por favor, haga una pregunta sobre ganadería, salud animal o nutrición.",
                "validation_error": "Se produjo un error durante la validación. Por favor, reformule su pregunta sobre agricultura."
            }
        }
        
        return messages.get(language, messages["fr"]).get(reason, messages["fr"][reason])

    def _log_rejection(self, question: str, result: ValidationResult, language: str, 
                      user_id: str, request_ip: str, rejection_type: str):
        """Log détaillé des questions rejetées pour analyse"""
        
        try:
            rejection_data = {
                "timestamp": datetime.now().isoformat(),
                "question": question[:500],  # Limiter la taille
                "question_length": len(question),
                "language": language,
                "user_id": user_id[:50],  # Limiter la taille
                "request_ip": request_ip[:45],  # IP v6 max
                "rejection_type": rejection_type,
                "confidence": round(result.confidence, 2),
                "reason": result.reason,
                "detected_keywords": result.detected_keywords[:10] if result.detected_keywords else [],  # Limiter
                "rejected_keywords": result.rejected_keywords[:10] if result.rejected_keywords else [],  # Limiter
                "suggested_topics_count": len(result.suggested_topics) if result.suggested_topics else 0,
                "settings_source": "intelia_settings" if SETTINGS_AVAILABLE else "environment_variables"
            }
            
            # Log structuré pour analyse
            self.rejection_logger.info(json.dumps(rejection_data, ensure_ascii=False))
            
            # Log standard pour monitoring
            logger.warning(
                f"❌ [AgriculturalValidator] REJET - Type: {rejection_type} | "
                f"User: {user_id[:8]} | Question: '{question[:100]}...' | "
                f"Confiance: {result.confidence:.1f}% | Mots rejetés: {result.rejected_keywords[:3]}"
            )
            
        except Exception as e:
            logger.error(f"❌ [AgriculturalValidator] Erreur logging rejet: {e}")

    def get_stats(self) -> Dict:
        """Retourne les statistiques de validation pour monitoring"""
        try:
            return {
                "enabled": self.enabled,
                "strictness_threshold": self.strictness,
                "allow_override": self.allow_override,
                "settings_available": SETTINGS_AVAILABLE,
                "log_all_validations": self.log_all_validations,
                "log_directory": self.log_dir,
                "agricultural_keywords_count": {
                    lang: len(keywords) for lang, keywords in self.agricultural_keywords.items()
                },
                "non_agricultural_keywords_count": {
                    lang: len(keywords) for lang, keywords in self.non_agricultural_keywords.items()
                },
                "supported_languages": list(self.agricultural_keywords.keys()),
                "logging_handlers_available": LOGGING_HANDLERS_AVAILABLE,
                "instance_initialized": hasattr(self, '_initialized')
            }
        except Exception as e:
            logger.error(f"❌ [AgriculturalValidator] Erreur get_stats: {e}")
            return {"error": str(e)}

# ==================== INSTANCE GLOBALE ====================

# Instance singleton du validateur avec protection thread-safe
_validator_instance = None
_validator_lock = threading.Lock()

def get_agricultural_validator() -> AgriculturalDomainValidator:
    """Retourne l'instance singleton du validateur de manière thread-safe"""
    global _validator_instance
    if _validator_instance is None:
        with _validator_lock:
            if _validator_instance is None:
                _validator_instance = AgriculturalDomainValidator()
    return _validator_instance

# Créer l'instance au chargement du module
agricultural_validator = get_agricultural_validator()

# ==================== FONCTIONS UTILITAIRES ====================

def validate_agricultural_question(question: str, language: str = "fr", 
                                 user_id: str = "unknown", request_ip: str = "unknown") -> ValidationResult:
    """
    Fonction utilitaire pour valider les questions agricoles
    
    Args:
        question: La question à valider
        language: Langue de la question
        user_id: ID utilisateur pour les logs
        request_ip: IP pour les logs
        
    Returns:
        ValidationResult: Résultat de la validation
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """
    try:
        validator = get_agricultural_validator()
        return validator.validate_question(question, language, user_id, request_ip)
    except Exception as e:
        logger.error(f"❌ [AgriculturalValidator] Erreur fonction utilitaire: {e}")
        # Retourner un résultat d'erreur plutôt que de lever l'exception
        return ValidationResult(
            is_valid=False,
            confidence=0.0,
            reason=f"Erreur de validation: {str(e)}"
        )

def get_agricultural_validator_stats() -> Dict:
    """Retourne les statistiques du validateur"""
    try:
        validator = get_agricultural_validator()
        return validator.get_stats()
    except Exception as e:
        logger.error(f"❌ [AgriculturalValidator] Erreur stats: {e}")
        return {"error": str(e)}

def is_agricultural_validation_enabled() -> bool:
    """Vérifie si la validation agricole est activée"""
    try:
        validator = get_agricultural_validator()
        return validator.enabled
    except Exception as e:
        logger.error(f"❌ [AgriculturalValidator] Erreur vérification activation: {e}")
        return False

# ==================== LOGGING DE DÉMARRAGE ====================

try:
    logger.info("🌾 [AgriculturalDomainValidator] Module de validation agricole initialisé")
    logger.info(f"📊 [AgriculturalDomainValidator] Statistiques: {get_agricultural_validator_stats()}")
except Exception as e:
    logger.error(f"❌ [AgriculturalDomainValidator] Erreur logging démarrage: {e}")
