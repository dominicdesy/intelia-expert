"""
entities_extractor.py - EXTRACTION D'ENTITÉS SIMPLIFIÉE

🎯 REMPLACE: clarification_entities.py et tous les autres extracteurs complexes
🚀 PRINCIPE: Extraction simple et efficace des informations clés
✨ SIMPLE: Patterns regex clairs et maintenables
🔧 NOUVEAU: Intégration avec EntityNormalizer pour normalisation systématique

Entités extraites:
- age_days: Âge en jours (converti automatiquement)
- breed_specific: Race spécifique (Ross 308, Cobb 500...)
- breed_generic: Race générique (ross, cobb, poulet...)
- sex: Sexe (mâle, femelle, mixte)
- weight_mentioned: Poids mentionné dans la question
- weight_grams: Valeur de poids en grammes
- symptoms: Symptômes de santé détectés
- context_type: Type de contexte (performance, santé, alimentation...)
"""

import logging
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# 🔧 NOUVEAU: Import du normalizer pour normalisation systématique
try:
    from .entity_normalizer import EntityNormalizer
    NORMALIZER_AVAILABLE = True
except ImportError:
    NORMALIZER_AVAILABLE = False
    logging.warning("EntityNormalizer non disponible - normalisation de base utilisée")

logger = logging.getLogger(__name__)

@dataclass
class ExtractedEntities:
    """Structure pour les entités extraites"""
    age_days: Optional[int] = None
    age_weeks: Optional[int] = None
    age: Optional[str] = None
    breed_specific: Optional[str] = None
    breed_generic: Optional[str] = None
    sex: Optional[str] = None
    weight_mentioned: bool = False
    weight_grams: Optional[float] = None
    weight_unit: Optional[str] = None
    symptoms: List[str] = None
    context_type: Optional[str] = None
    housing_conditions: Optional[str] = None
    feeding_context: Optional[str] = None
    
    def __post_init__(self):
        if self.symptoms is None:
            self.symptoms = []

class EntitiesExtractor:
    """Extracteur d'entités simple et efficace avec normalisation intégrée"""
    
    def __init__(self):
        # 🔧 NOUVEAU: Intégration du normalizer
        if NORMALIZER_AVAILABLE:
            self.normalizer = EntityNormalizer()
            logger.info("✅ [Entities Extractor] EntityNormalizer initialisé")
        else:
            self.normalizer = None
            logger.warning("⚠️ [Entities Extractor] Fonctionnement sans EntityNormalizer")
            
        # Races spécifiques reconnues (nom complet)
        self.specific_breeds = {
            # Poulets de chair
            'ross 308': 'Ross 308',
            'ross308': 'Ross 308',
            'cobb 500': 'Cobb 500', 
            'cobb500': 'Cobb 500',
            'hubbard': 'Hubbard',
            'arbor acres': 'Arbor Acres',
            'arbor': 'Arbor Acres',
            
            # Pondeuses
            'isa brown': 'ISA Brown',
            'lohmann brown': 'Lohmann Brown',
            'lohmann': 'Lohmann Brown',
            'hy-line': 'Hy-Line',
            'hyline': 'Hy-Line', 
            'bovans': 'Bovans',
            'shaver': 'Shaver',
            'hissex': 'Hissex',
            'novogen': 'Novogen'
        }
        
        # Races génériques (mentions partielles)
        self.generic_breeds = [
            'ross', 'cobb', 'broiler', 'poulet', 'poule', 'poussin',
            'chicken', 'hen', 'rooster', 'cockerel', 'pullet'
        ]
        
        # Symptômes de santé
        self.health_symptoms = {
            'digestifs': ['diarrhée', 'fientes', 'liquide', 'verdâtre', 'sanguinolente'],
            'respiratoires': ['toux', 'râle', 'dyspnée', 'essoufflement', 'respiration'],
            'comportementaux': ['apathique', 'abattu', 'isolé', 'prostré', 'faiblesse'],
            'locomoteurs': ['boiterie', 'paralysie', 'difficulté', 'marcher', 'claudication'],
            'généraux': ['fièvre', 'perte', 'appétit', 'amaigrissement', 'mortalité']
        }

    def extract(self, question: str) -> ExtractedEntities:
        """
        POINT D'ENTRÉE PRINCIPAL - Extrait toutes les entités de la question
        🔧 NOUVEAU: Avec normalisation systématique via EntityNormalizer
        
        Args:
            question: Texte de la question à analyser
            
        Returns:
            ExtractedEntities avec toutes les informations extraites et normalisées
        """
        try:
            logger.info(f"🔍 [Entities Extractor] Analyse: '{question[:50]}...'")
            
            question_lower = question.lower().strip()
            
            # 🔧 NOUVEAU: Extraction brute puis normalisation
            raw_entities = self._raw_extract(question_lower)
            
            # 🔧 NOUVEAU: Normalisation systématique si disponible
            if self.normalizer:
                logger.debug("🔄 [Entities Extractor] Application de la normalisation...")
                normalized_entities = self.normalizer.normalize(raw_entities)
                logger.info(f"✅ [Entities Extractor] Entités normalisées: {self._entities_summary(normalized_entities)}")
                return normalized_entities
            else:
                # Fallback: normalisation de base
                self._normalize_extracted_data(raw_entities)
                logger.info(f"✅ [Entities Extractor] Entités extraites (normalisation de base): {self._entities_summary(raw_entities)}")
                return raw_entities
            
        except Exception as e:
            logger.error(f"❌ [Entities Extractor] Erreur extraction: {e}")
            return ExtractedEntities()  # Retourner entités vides en cas d'erreur

    def _raw_extract(self, question: str) -> ExtractedEntities:
        """
        🔧 NOUVEAU: Extraction brute sans normalisation
        Sépare l'extraction de la normalisation pour flexibilité
        """
        entities = ExtractedEntities()
        
        # Extraction par type d'information
        entities.age_days = self._extract_age_days(question)
        entities.age_weeks = self._extract_age_weeks(question)
        entities.age = self._extract_age_text(question)
        
        entities.breed_specific = self._extract_breed_specific(question)
        entities.breed_generic = self._extract_breed_generic(question)
        
        entities.sex = self._extract_sex(question)
        
        entities.weight_mentioned = self._has_weight_mention(question)
        entities.weight_grams, entities.weight_unit = self._extract_weight_value(question)
        
        entities.symptoms = self._extract_symptoms(question)
        entities.context_type = self._determine_context_type(question)
        
        entities.housing_conditions = self._extract_housing_context(question)
        entities.feeding_context = self._extract_feeding_context(question)
        
        return entities

    def _extract_age_days(self, question: str) -> Optional[int]:
        """Extrait l'âge en jours"""
        
        # Patterns pour jours
        day_patterns = [
            r'(\d+)\s*jours?',
            r'(\d+)\s*j\b',
            r'(\d+)\s*days?',
            r'jour\s*(\d+)',
            r'day\s*(\d+)',
            r'j(\d+)',
            r'(\d+)j\b'
        ]
        
        for pattern in day_patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                try:
                    days = int(match.group(1))
                    if 1 <= days <= 500:  # Validation plausible
                        logger.debug(f"🗓️ Âge en jours détecté: {days}")
                        return days
                except ValueError:
                    continue
        
        return None

    def _extract_age_weeks(self, question: str) -> Optional[int]:
        """Extrait l'âge en semaines"""
        
        # Patterns pour semaines
        week_patterns = [
            r'(\d+)\s*semaines?',
            r'(\d+)\s*sem\b',
            r'(\d+)\s*weeks?',
            r'(\d+)\s*wks?',
            r'semaine\s*(\d+)',
            r'week\s*(\d+)',
            r's(\d+)',
            r'(\d+)s\b'
        ]
        
        for pattern in week_patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                try:
                    weeks = int(match.group(1))
                    if 1 <= weeks <= 80:  # Validation plausible
                        logger.debug(f"📅 Âge en semaines détecté: {weeks}")
                        return weeks
                except ValueError:
                    continue
        
        return None

    def _extract_age_text(self, question: str) -> Optional[str]:
        """Extrait les mentions d'âge textuelles"""
        
        # Stades de développement
        age_stages = [
            'poussin', 'poussins', 'démarrage', 'démarreur',
            'croissance', 'finition', 'finisseur',
            'jeune', 'jeunes', 'adulte', 'adultes',
            'ponte', 'production', 'réforme'
        ]
        
        for stage in age_stages:
            if stage in question:
                logger.debug(f"📈 Stade d'âge détecté: {stage}")
                return stage
        
        return None

    def _extract_breed_specific(self, question: str) -> Optional[str]:
        """Extrait les races spécifiques (noms complets)"""
        
        # Recherche des races spécifiques
        for breed_key, breed_name in self.specific_breeds.items():
            if breed_key in question:
                logger.debug(f"🐔 Race spécifique détectée: {breed_name}")
                return breed_name
        
        # Patterns pour races avec numéros
        breed_number_patterns = [
            r'ross\s*(\d+)',
            r'cobb\s*(\d+)',
            r'hy[-\s]*line\s*(\w+)',
            r'lohmann\s*(\w+)'
        ]
        
        for pattern in breed_number_patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                breed_full = match.group(0).strip()
                logger.debug(f"🐔 Race avec numéro détectée: {breed_full}")
                return breed_full.title()
        
        return None

    def _extract_breed_generic(self, question: str) -> Optional[str]:
        """Extrait les mentions de races génériques"""
        
        for breed in self.generic_breeds:
            if breed in question:
                logger.debug(f"🐓 Race générique détectée: {breed}")
                return breed
        
        return None

    def _extract_sex(self, question: str) -> Optional[str]:
        """Extrait le sexe des animaux"""
        
        # Patterns pour mâles
        male_patterns = [
            r'\bmâles?\b', r'\bmale\b', r'\bcoqs?\b', r'\brooster\b',
            r'\bcockerel\b', r'\bmasculin\b'
        ]
        
        # Patterns pour femelles  
        female_patterns = [
            r'\bfemelles?\b', r'\bfemale\b', r'\bpoules?\b', r'\bhens?\b',
            r'\bpoulettes?\b', r'\bpullets?\b', r'\bféminin\b'
        ]
        
        # Patterns pour mixte
        mixed_patterns = [
            r'\bmixte\b', r'\bmixed\b', r'\bmélangé\b', r'\bensemble\b',
            r'\btroupeau\b', r'\bflock\b'
        ]
        
        # Vérification dans l'ordre de priorité
        for pattern in male_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                logger.debug("♂️ Sexe détecté: mâle")
                return "mâle"
        
        for pattern in female_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                logger.debug("♀️ Sexe détecté: femelle") 
                return "femelle"
        
        for pattern in mixed_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                logger.debug("⚥ Sexe détecté: mixte")
                return "mixte"
        
        return None

    def _has_weight_mention(self, question: str) -> bool:
        """Détecte si la question mentionne le poids"""
        
        weight_keywords = [
            'poids', 'weight', 'gramme', 'gram', 'kg', 'kilo',
            'pesé', 'peser', 'pesée', 'weigh', 'weighs', 'weighing',
            'lourd', 'heavy', 'léger', 'light', 'masse', 'mass'
        ]
        
        for keyword in weight_keywords:
            if keyword in question:
                logger.debug(f"⚖️ Mention de poids détectée: {keyword}")
                return True
        
        return False

    def _extract_weight_value(self, question: str) -> tuple[Optional[float], Optional[str]]:
        """Extrait une valeur de poids avec son unité"""
        
        # Patterns pour poids avec unités
        weight_patterns = [
            r'(\d+(?:\.\d+)?)\s*(kg|kilo|kilogram)',
            r'(\d+(?:\.\d+)?)\s*(g|gr|gram|gramme)',
            r'(\d+(?:\.\d+)?)\s*(lbs?|pound)',
            r'pèse\s*(\d+(?:\.\d+)?)\s*(kg|g|gram|gramme)?',
            r'weighs?\s*(\d+(?:\.\d+)?)\s*(kg|g|gram|lbs?)?'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    unit = match.group(2).lower() if len(match.groups()) > 1 and match.group(2) else 'g'
                    
                    # Conversion en grammes
                    if unit in ['kg', 'kilo', 'kilogram']:
                        weight_grams = value * 1000
                    elif unit in ['lbs', 'lb', 'pound']:
                        weight_grams = value * 453.592
                    else:  # grammes par défaut
                        weight_grams = value
                    
                    if 1 <= weight_grams <= 10000:  # Validation plausible
                        logger.debug(f"⚖️ Poids détecté: {weight_grams}g ({value}{unit})")
                        return weight_grams, unit
                        
                except ValueError:
                    continue
        
        return None, None

    def _extract_symptoms(self, question: str) -> List[str]:
        """Extrait les symptômes de santé mentionnés"""
        
        detected_symptoms = []
        
        for category, symptoms in self.health_symptoms.items():
            for symptom in symptoms:
                if symptom in question:
                    detected_symptoms.append(symptom)
                    logger.debug(f"🩺 Symptôme détecté ({category}): {symptom}")
        
        # Supprimer les doublons
        return list(set(detected_symptoms))

    def _determine_context_type(self, question: str) -> Optional[str]:
        """Détermine le type de contexte de la question"""
        
        # Contextes de performance
        performance_keywords = ['poids', 'croissance', 'performance', 'gain', 'développement']
        if any(keyword in question for keyword in performance_keywords):
            return 'performance'
        
        # Contextes de santé
        health_keywords = ['malade', 'symptôme', 'problème', 'mort', 'santé', 'traitement']
        if any(keyword in question for keyword in health_keywords):
            return 'santé'
        
        # Contextes d'alimentation
        feeding_keywords = ['alimentation', 'nourrir', 'aliment', 'nutrition', 'manger']
        if any(keyword in question for keyword in feeding_keywords):
            return 'alimentation'
        
        # Contextes d'élevage
        housing_keywords = ['élevage', 'conditions', 'température', 'ventilation', 'densité']
        if any(keyword in question for keyword in housing_keywords):
            return 'élevage'
        
        return 'général'

    def _extract_housing_context(self, question: str) -> Optional[str]:
        """Extrait le contexte des conditions d'élevage"""
        
        housing_conditions = [
            'température', 'chaleur', 'froid', 'ventilation', 'humidité',
            'densité', 'espace', 'litière', 'éclairage', 'bâtiment'
        ]
        
        for condition in housing_conditions:
            if condition in question:
                logger.debug(f"🏠 Condition d'élevage détectée: {condition}")
                return condition
        
        return None

    def _extract_feeding_context(self, question: str) -> Optional[str]:
        """Extrait le contexte alimentaire"""
        
        feeding_contexts = [
            'démarrage', 'croissance', 'finition', 'ponte', 'préparation',
            'starter', 'grower', 'finisher', 'layer', 'maintenance'
        ]
        
        for context in feeding_contexts:
            if context in question:
                logger.debug(f"🌾 Contexte alimentaire détecté: {context}")
                return context
        
        return None

    def _normalize_extracted_data(self, entities: ExtractedEntities):
        """
        Normalise et enrichit les données extraites (version de base)
        🔧 MODIFICATION: Fallback quand EntityNormalizer n'est pas disponible
        """
        
        # Conversion semaines -> jours si manquant
        if entities.age_weeks and not entities.age_days:
            entities.age_days = entities.age_weeks * 7
            logger.debug(f"🔄 Conversion: {entities.age_weeks} semaines → {entities.age_days} jours")
        
        # Conversion jours -> semaines si manquant
        if entities.age_days and not entities.age_weeks:
            entities.age_weeks = entities.age_days // 7
            logger.debug(f"🔄 Conversion: {entities.age_days} jours → {entities.age_weeks} semaines")
        
        # Normalisation du sexe
        if entities.sex:
            sex_normalization = {
                'mâle': 'mâle', 'male': 'mâle', 'coq': 'mâle', 'masculin': 'mâle',
                'femelle': 'femelle', 'female': 'femelle', 'poule': 'femelle', 'féminin': 'femelle',
                'mixte': 'mixte', 'mixed': 'mixte', 'mélangé': 'mixte', 'troupeau': 'mixte'
            }
            entities.sex = sex_normalization.get(entities.sex.lower(), entities.sex)
        
        # Enrichissement du contexte si symptômes détectés
        if entities.symptoms and not entities.context_type:
            entities.context_type = 'santé'
        
        # Enrichissement poids si valeur mais pas de mention
        if entities.weight_grams and not entities.weight_mentioned:
            entities.weight_mentioned = True

    def _entities_summary(self, entities) -> str:
        """Crée un résumé des entités pour le logging"""
        
        summary_parts = []
        
        # Gérer les deux types d'entités (ExtractedEntities et NormalizedEntities)
        if hasattr(entities, 'age_days') and entities.age_days:
            summary_parts.append(f"âge={entities.age_days}j")
        
        if hasattr(entities, 'breed_specific') and entities.breed_specific:
            summary_parts.append(f"race={entities.breed_specific}")
        elif hasattr(entities, 'breed') and entities.breed:
            summary_parts.append(f"race={entities.breed}")
        elif hasattr(entities, 'breed_generic') and entities.breed_generic:
            summary_parts.append(f"race_gen={entities.breed_generic}")
        
        if hasattr(entities, 'sex') and entities.sex:
            summary_parts.append(f"sexe={entities.sex}")
        
        if hasattr(entities, 'weight_grams') and entities.weight_grams:
            summary_parts.append(f"poids={entities.weight_grams}g")
        elif hasattr(entities, 'weight_mentioned') and entities.weight_mentioned:
            summary_parts.append("poids_mentionné")
        
        if hasattr(entities, 'symptoms') and entities.symptoms:
            summary_parts.append(f"symptômes={len(entities.symptoms)}")
        
        if hasattr(entities, 'context_type') and entities.context_type:
            summary_parts.append(f"contexte={entities.context_type}")
        
        return ", ".join(summary_parts) if summary_parts else "aucune"

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de l'extracteur pour debugging"""
        stats = {
            "extractor_version": "1.1.0",  # 🔧 NOUVEAU: Version mise à jour
            "normalizer_enabled": NORMALIZER_AVAILABLE,  # 🔧 NOUVEAU: Status normalizer
            "specific_breeds_count": len(self.specific_breeds),
            "generic_breeds_count": len(self.generic_breeds),
            "health_symptoms_categories": len(self.health_symptoms),
            "total_symptoms": sum(len(symptoms) for symptoms in self.health_symptoms.values())
        }
        
        # 🔧 FIX: Stats du normalizer si disponible - utilise la méthode correcte
        if self.normalizer:
            try:
                stats["normalizer_stats"] = self.normalizer.get_stats()  # 🔧 FIX: Utilise get_stats() au lieu de get_normalization_stats()
            except AttributeError:
                # Si la méthode n'existe pas, essayer l'alias
                try:
                    stats["normalizer_stats"] = self.normalizer.get_normalization_stats()
                except AttributeError:
                    stats["normalizer_stats"] = {"error": "Méthode de statistiques non disponible"}
        
        return stats

# =============================================================================
# FONCTIONS UTILITAIRES - MISES À JOUR
# =============================================================================

def quick_extract(question: str) -> Dict[str, Any]:
    """
    Extraction rapide pour usage simple
    🔧 NOUVEAU: Retourne les entités normalisées
    
    Returns:
        Dict avec les entités principales extraites et normalisées
    """
    extractor = EntitiesExtractor()
    entities = extractor.extract(question)
    
    return {
        'age_days': getattr(entities, 'age_days', None),
        'breed_specific': getattr(entities, 'breed_specific', None),
        'breed_generic': getattr(entities, 'breed_generic', None),
        'sex': getattr(entities, 'sex', None),
        'weight_mentioned': getattr(entities, 'weight_mentioned', False),
        'weight_grams': getattr(entities, 'weight_grams', None),
        'symptoms': getattr(entities, 'symptoms', []),
        'context_type': getattr(entities, 'context_type', None),
        # 🔧 NOUVEAU: Champs additionnels normalisés
        'age_weeks': getattr(entities, 'age_weeks', None),
        'weight_unit': getattr(entities, 'weight_unit', None),
        'housing_conditions': getattr(entities, 'housing_conditions', None),
        'feeding_context': getattr(entities, 'feeding_context', None)
    }

def extract_age_only(question: str) -> Optional[int]:
    """Extrait seulement l'âge en jours (normalisé)"""
    extractor = EntitiesExtractor()
    entities = extractor.extract(question)  # 🔧 NOUVEAU: Utilise extract() pour normalisation
    return getattr(entities, 'age_days', None)

def extract_breed_only(question: str) -> Optional[str]:
    """Extrait seulement la race spécifique (normalisée)"""
    extractor = EntitiesExtractor()
    entities = extractor.extract(question)  # 🔧 NOUVEAU: Utilise extract() pour normalisation
    return getattr(entities, 'breed_specific', None) or getattr(entities, 'breed', None)

def has_health_context(question: str) -> bool:
    """Détermine rapidement si c'est un contexte de santé"""
    extractor = EntitiesExtractor()
    entities = extractor.extract(question)
    context_type = getattr(entities, 'context_type', None)
    symptoms = getattr(entities, 'symptoms', [])
    return context_type == 'santé' or len(symptoms) > 0

# 🔧 NOUVELLES FONCTIONS UTILITAIRES

def extract_normalized_entities(question: str):
    """
    🔧 NOUVEAU: Extraction complète avec normalisation garantie
    
    Returns:
        ExtractedEntities ou NormalizedEntities complètement normalisées
    """
    extractor = EntitiesExtractor()
    return extractor.extract(question)

def get_normalization_status() -> Dict[str, Any]:
    """
    🔧 NOUVEAU: Retourne le statut de la normalisation
    
    Returns:
        Dict avec le statut du système de normalisation
    """
    return {
        "normalizer_available": NORMALIZER_AVAILABLE,
        "extractor_version": "1.1.0",
        "normalization_enabled": True,
        "fallback_normalization": not NORMALIZER_AVAILABLE
    }

# =============================================================================
# TESTS INTÉGRÉS - MISE À JOUR
# =============================================================================

def test_extractor():
    """Tests rapides de l'extracteur avec normalisation"""
    extractor = EntitiesExtractor()
    
    test_cases = [
        "Quel est le poids d'un poulet Ross 308 mâle de 21 jours ?",
        "Mes poules Cobb 500 de 3 semaines ont des problèmes de diarrhée",
        "Comment nourrir des poussins en démarrage ?",
        "La température est trop élevée dans mon bâtiment d'élevage"
    ]
    
    print("🧪 Tests de l'extracteur d'entités avec normalisation:")
    print("=" * 60)
    print(f"🔧 Normalizer disponible: {NORMALIZER_AVAILABLE}")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case}")
        entities = extractor.extract(test_case)
        
        age_days = getattr(entities, 'age_days', None)
        age_weeks = getattr(entities, 'age_weeks', None)
        breed_specific = getattr(entities, 'breed_specific', None) or getattr(entities, 'breed', None)
        breed_generic = getattr(entities, 'breed_generic', None)
        sex = getattr(entities, 'sex', None)
        weight_mentioned = getattr(entities, 'weight_mentioned', False)
        weight_grams = getattr(entities, 'weight_grams', None)
        symptoms = getattr(entities, 'symptoms', [])
        context_type = getattr(entities, 'context_type', None)
        
        print(f"   ✅ Âge: {age_days} jours ({age_weeks} semaines)")
        print(f"   ✅ Race spécifique: {breed_specific}")
        print(f"   ✅ Race générique: {breed_generic}")
        print(f"   ✅ Sexe: {sex}")
        print(f"   ✅ Poids mentionné: {weight_mentioned}")
        print(f"   ✅ Poids valeur: {weight_grams}g")
        print(f"   ✅ Symptômes: {symptoms}")
        print(f"   ✅ Contexte: {context_type}")
        
        # 🔧 NOUVEAU: Affichage statut normalisation
        if extractor.normalizer:
            print(f"   🔄 Normalisation: ✅ Appliquée")
        else:
            print(f"   🔄 Normalisation: ⚠️ Fallback de base")
    
    print(f"\n📊 Statistiques extracteur:")
    stats = extractor.get_extraction_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Tests terminés!")

if __name__ == "__main__":
    test_extractor()