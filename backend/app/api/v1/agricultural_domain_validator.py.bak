"""
app/api/v1/agricultural_domain_validator.py

Module spécialisé pour la validation des questions dans le domaine agricole.
Garantit que les questions sont liées à l'élevage, la santé animale et la nutrition.
Intégré avec le système de configuration Intelia.


"""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

# Import des settings Intelia
try:
    from app.config.settings import settings
    SETTINGS_AVAILABLE = True
except ImportError:
    SETTINGS_AVAILABLE = False
    settings = None

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Résultat de la validation d'une question agricole"""
    is_valid: bool
    confidence: float
    reason: Optional[str] = None
    suggested_topics: Optional[List[str]] = None
    detected_keywords: Optional[List[str]] = None
    rejected_keywords: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour les logs"""
        return {
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "reason": self.reason,
            "suggested_topics": self.suggested_topics,
            "detected_keywords": self.detected_keywords,
            "rejected_keywords": self.rejected_keywords
        }

class AgriculturalDomainValidator:
    """
    Validateur pour garantir que les questions concernent le domaine agricole.
    Intégré avec le système de configuration Intelia.
    """
    
    def __init__(self):
        """Initialise le validateur avec la configuration Intelia"""
        
        # Configuration depuis les settings Intelia
        if SETTINGS_AVAILABLE and settings:
            self.enabled = settings.agricultural_validation_enabled
            self.strictness = settings.agricultural_validation_strictness
            self.allow_override = settings.agricultural_validation_override_allowed
            self.log_all_validations = settings.agricultural_validation_log_all
            self.log_dir = settings.agricultural_validation_log_dir
            self.log_max_size = settings.agricultural_validation_log_max_size
            self.log_backup_count = settings.agricultural_validation_log_backup_count
        else:
            # Fallback configuration
            import os
            self.enabled = os.getenv('ENABLE_AGRICULTURAL_VALIDATION', 'true').lower() == 'true'
            self.strictness = float(os.getenv('VALIDATION_STRICTNESS', '15.0'))
            self.allow_override = os.getenv('ALLOW_VALIDATION_OVERRIDE', 'false').lower() == 'true'
            self.log_all_validations = os.getenv('LOG_ALL_VALIDATIONS', 'true').lower() == 'true'
            self.log_dir = os.getenv('VALIDATION_LOGS_DIR', 'logs')
            self.log_max_size = int(os.getenv('VALIDATION_LOG_MAX_SIZE', '10485760'))
            self.log_backup_count = int(os.getenv('VALIDATION_LOG_BACKUP_COUNT', '5'))
        
        logger.info(f"🔧 [AgriculturalValidator] Validation agricole: {'✅ Activée' if self.enabled else '❌ Désactivée'}")
        logger.info(f"🔧 [AgriculturalValidator] Seuil de confiance: {self.strictness}%")
        logger.info(f"🔧 [AgriculturalValidator] Settings disponibles: {'✅ Oui' if SETTINGS_AVAILABLE else '❌ Non'}")
        
        self._init_keywords()
        self._init_rejection_logger()

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
                # Même structure pour l'anglais (raccourci pour l'exemple)
                "chicken", "chickens", "poultry", "broiler", "broilers", "layer", "layers",
                "rooster", "roosters", "hen", "hens", "chick", "chicks", "egg", "eggs",
                "aviculture", "avian", "pig", "pigs", "swine", "hog", "hogs", "sow", "sows",
                "boar", "boars", "piglet", "piglets", "pork", "cattle", "cow", "cows",
                "ross", "ross 308", "ross 708", "cobb", "cobb 500", "cobb 700", "hybrid",
                "veterinary", "vaccination", "vaccine", "disease", "mortality", "nutrition",
                "feeding", "farming", "agriculture", "livestock", "temperature", "ventilation"
                # ... (liste complète dans le fichier final)
            ],
            
            "es": [
                # Même structure pour l'espagnol (raccourci pour l'exemple)
                "pollo", "pollos", "gallina", "gallinas", "gallo", "gallos", "pollito",
                "pollitos", "ave", "aves", "huevo", "huevos", "avicultura", "aviar",
                "cerdo", "cerdos", "cochino", "cochinos", "ross", "cobb", "veterinario",
                "vacunación", "enfermedad", "mortalidad", "nutrición", "alimentación",
                "ganadería", "granja", "agricultura", "temperatura", "ventilación"
                # ... (liste complète dans le fichier final)
            ]
        }
        
        self.non_agricultural_keywords = {
            "fr": [
                "finance", "finances", "banque", "banques", "investissement", "investissements",
                "bourse", "action", "actions", "crypto", "bitcoin", "ethereum", "trading",
                "beauté", "maquillage", "cosmétique", "cosmétiques", "mode", "vêtement",
                "vêtements", "fashion", "style", "tendance", "cuisine", "recette", "recettes",
                "restaurant", "restaurants", "gastronomie", "chef", "cuisinier", "sport",
                "football", "tennis", "basketball", "athlète", "match", "compétition",
                "technologie", "informatique", "ordinateur", "ordinateurs", "smartphone",
                "logiciel", "internet", "web", "voyage", "tourisme", "vacances", "hôtel",
                "destination", "politique", "élection", "gouvernement", "député", "président",
                "médecine", "docteur", "hôpital", "patient", "chirurgie", "humain", "humaine",
                "automobile", "voiture", "moto", "transport", "carburant", "immobilier",
                "maison", "appartement", "achat", "vente", "location", "cinéma", "film",
                "musique", "concert", "art", "peinture", "littérature", "livre"
            ],
            "en": [
                "finance", "bank", "banking", "investment", "stock", "stocks", "crypto",
                "bitcoin", "ethereum", "trading", "money", "beauty", "makeup", "cosmetic",
                "cosmetics", "fashion", "clothing", "style", "trend", "cooking", "recipe",
                "recipes", "restaurant", "gastronomy", "chef", "culinary", "sport", "sports",
                "football", "tennis", "basketball", "athlete", "game", "competition",
                "technology", "computer", "smartphone", "software", "internet", "web"
            ],
            "es": [
                "finanzas", "banco", "inversión", "bolsa", "acción", "acciones", "crypto",
                "bitcoin", "ethereum", "trading", "dinero", "belleza", "maquillaje",
                "cosmético", "cosmética", "moda", "ropa", "vestimenta", "estilo", "tendencia",
                "cocina", "receta", "recetas", "restaurante", "gastronomía", "chef",
                "cocinero", "deporte", "deportes", "fútbol", "tenis", "baloncesto", "atleta"
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

    def _init_rejection_logger(self):
        """Initialise le logger spécialisé pour les rejets"""
        self.rejection_logger = logging.getLogger("agricultural_validation_rejections")
        self.rejection_logger.setLevel(logging.INFO)
        
        # Handler pour fichier de rejets si pas déjà configuré
        if not self.rejection_logger.handlers:
            try:
                import os
                from logging.handlers import RotatingFileHandler
                
                # Créer le répertoire de logs s'il n'existe pas
                os.makedirs(self.log_dir, exist_ok=True)
                
                log_file_path = os.path.join(self.log_dir, 'agricultural_rejections.log')
                rejection_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=self.log_max_size,
                    backupCount=self.log_backup_count
                )
                rejection_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                rejection_handler.setFormatter(rejection_formatter)
                self.rejection_logger.addHandler(rejection_handler)
                
                logger.info(f"✅ [AgriculturalValidator] Logger rejets configuré: {log_file_path}")
                
            except Exception as e:
                logger.warning(f"⚠️ [AgriculturalValidator] Impossible de créer le fichier de log rejets: {e}")

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
        """
        
        # Si la validation est désactivée, accepter toutes les questions
        if not self.enabled:
            logger.info(f"🔧 [AgriculturalValidator] Validation désactivée - question acceptée")
            return ValidationResult(is_valid=True, confidence=100.0)
        
        # Normalisation de la question
        normalized_question = self._normalize_text(question)
        validation_start = datetime.now()
        
        logger.info(f"🔍 [AgriculturalValidator] Validation question: '{question[:50]}...' (langue: {language}, user: {user_id[:8]})")
        
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
                confidence=0,
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

    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour la comparaison (supprime accents, ponctuation)"""
        import unicodedata
        
        # Convertir en minuscules
        text = text.lower()
        
        # Supprimer les accents
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # Nettoyer la ponctuation et espaces multiples
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _find_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """Trouve les mots-clés présents dans le texte avec recherche flexible"""
        found = []
        text_words = text.split()
        
        for keyword in keywords:
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

    def _calculate_confidence(self, text: str, agri_count: int, non_agri_count: int) -> float:
        """Calcule un score de confiance basé sur les mots-clés détectés"""
        word_count = len(text.split())
        
        if word_count == 0:
            return 0
        
        # Score basé sur la proportion de mots agricoles
        agri_ratio = (agri_count / word_count) * 100
        
        # Bonus pour multiple mots-clés agricoles
        agri_bonus = min(agri_count * 15, 60)  # Max 60% de bonus
        
        # Pénalité pour les mots non-agricoles
        non_agri_penalty = min(non_agri_count * 25, 75)  # Max 75% de pénalité
        
        # Score final
        confidence = agri_ratio + agri_bonus - non_agri_penalty
        
        return max(0, min(100, confidence))

    def _get_rejection_message(self, language: str, reason: str) -> str:
        """Retourne le message de rejet approprié selon la langue et la raison"""
        messages = {
            "fr": {
                "non_agricultural": "Je suis un expert dans le domaine avicole, donc je ne suis pas spécialisé dans la cryptomonnaie. Si vous avez des questions sur le domaine avicole, je serais ravi de vous aider.",
                "too_general": "Cette question semble trop générale ou ne contient pas assez d'éléments spécifiques au domaine avicole. Pouvez-vous la reformuler en précisant l'aspect d'élevage, de santé animale ou de nutrition qui vous intéresse ?"
            },
            "en": {
                "non_agricultural": "I am an expert in the poultry field, so I am not specialized in cryptocurrency. If you have questions about the poultry field, I would be happy to help you.",
                "too_general": "This question seems too general or doesn't contain enough elements specific to the poultry domain. Could you rephrase it by specifying the livestock, animal health, or nutrition aspect you're interested in?"
            },
            "es": {
                "non_agricultural": "Soy un experto en el campo avícola, por lo que no me especializo en criptomonedas. Si tienes preguntas sobre el campo avícola, estaría encantado de ayudarte.",
                "too_general": "Esta pregunta parece demasiado general o no contiene suficientes elementos específicos del dominio avícola. ¿Podría reformularla especificando el aspecto ganadero, de salud animal o nutrición que le interesa?"
            }
        }
        
        return messages.get(language, messages["fr"]).get(reason, messages["fr"][reason])

    def _log_rejection(self, question: str, result: ValidationResult, language: str, 
                      user_id: str, request_ip: str, rejection_type: str):
        """Log détaillé des questions rejetées pour analyse"""
        
        rejection_data = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "question_length": len(question),
            "language": language,
            "user_id": user_id,
            "request_ip": request_ip,
            "rejection_type": rejection_type,
            "confidence": result.confidence,
            "reason": result.reason,
            "detected_keywords": result.detected_keywords,
            "rejected_keywords": result.rejected_keywords,
            "suggested_topics_count": len(result.suggested_topics) if result.suggested_topics else 0,
            "settings_source": "intelia_settings" if SETTINGS_AVAILABLE else "environment_variables"
        }
        
        # Log structuré pour analyse
        self.rejection_logger.info(json.dumps(rejection_data, ensure_ascii=False))
        
        # Log standard pour monitoring
        logger.warning(
            f"❌ [AgriculturalValidator] REJET - Type: {rejection_type} | "
            f"User: {user_id[:8]} | Question: '{question[:100]}...' | "
            f"Confiance: {result.confidence:.1f}% | Mots rejetés: {result.rejected_keywords}"
        )

    def get_stats(self) -> Dict:
        """Retourne les statistiques de validation pour monitoring"""
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
            "supported_languages": list(self.agricultural_keywords.keys())
        }

# ==================== INSTANCE GLOBALE ====================

# Instance singleton du validateur
agricultural_validator = AgriculturalDomainValidator()

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
    """
    return agricultural_validator.validate_question(question, language, user_id, request_ip)

def get_agricultural_validator_stats() -> Dict:
    """Retourne les statistiques du validateur"""
    return agricultural_validator.get_stats()

def is_agricultural_validation_enabled() -> bool:
    """Vérifie si la validation agricole est activée"""
    return agricultural_validator.enabled

# ==================== LOGGING DE DÉMARRAGE ====================

logger.info("🌾 [AgriculturalDomainValidator] Module de validation agricole initialisé")
logger.info(f"📊 [AgriculturalDomainValidator] Statistiques: {agricultural_validator.get_stats()}")