# -*- coding: utf-8 -*-
"""
intent_processor.py - Processeur d'intentions métier pour Intelia Expert
Utilise intents.json pour améliorer la classification et l'expansion de requêtes
"""

import os
import json
import logging
import re
import time
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class IntentType(Enum):
    """Types d'intentions métier"""
    METRIC_QUERY = "metric_query"
    ENVIRONMENT_SETTING = "environment_setting"
    PROTOCOL_QUERY = "protocol_query"
    DIAGNOSIS_TRIAGE = "diagnosis_triage"
    ECONOMICS_COST = "economics_cost"
    GENERAL_POULTRY = "general_poultry"
    OUT_OF_DOMAIN = "out_of_domain"

@dataclass
class IntentResult:
    """Résultat de classification d'intention"""
    intent_type: IntentType
    confidence: float
    detected_entities: Dict[str, str]
    expanded_query: str
    metadata: Dict

class PoultryVocabularyExtractor:
    """Extracteur de vocabulaire spécialisé depuis intents.json"""
    
    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        self.poultry_keywords = self._build_vocabulary()
        self.alias_mappings = self._build_alias_mappings()
        
    def _build_vocabulary(self) -> Set[str]:
        """Construit le vocabulaire complet du domaine avicole"""
        keywords = set()
        
        aliases = self.intents_config.get("aliases", {})
        
        # Lignées de volailles
        for line_type, line_aliases in aliases.get("line", {}).items():
            keywords.add(line_type.lower())
            keywords.update([alias.lower() for alias in line_aliases])
        
        # Types d'élevage et sites
        for site_type, site_aliases in aliases.get("site_type", {}).items():
            keywords.add(site_type.lower())
            keywords.update([alias.lower() for alias in site_aliases])
        
        # Types d'oiseaux
        for bird_type, bird_aliases in aliases.get("bird_type", {}).items():
            keywords.add(bird_type.lower())
            keywords.update([alias.lower() for alias in bird_aliases])
        
        # Phases d'élevage
        for phase, phase_aliases in aliases.get("phase", {}).items():
            keywords.add(phase.lower())
            keywords.update([alias.lower() for alias in phase_aliases])
        
        # Métriques techniques
        for intent_name, intent_config in self.intents_config.get("intents", {}).items():
            metrics = intent_config.get("metrics", {})
            keywords.update([metric.lower() for metric in metrics.keys()])
        
        # Mots-clés additionnels du domaine
        additional_keywords = {
            'poulet', 'poule', 'aviculture', 'élevage', 'volaille', 'poids', 'fcr',
            'aliment', 'vaccination', 'maladie', 'production', 'croissance',
            'chicken', 'poultry', 'broiler', 'layer', 'feed', 'weight', 'growth',
            'température', 'ventilation', 'eau', 'water', 'temperature', 'incubation',
            'couvoir', 'hatchery', 'biosécurité', 'mortalité', 'mortality', 'performance'
        }
        keywords.update(additional_keywords)
        
        logger.info(f"Vocabulaire avicole construit: {len(keywords)} termes")
        return keywords
    
    def _build_alias_mappings(self) -> Dict[str, str]:
        """Construit les mappings alias -> terme canonique"""
        mappings = {}
        
        for category, items in self.intents_config.get("aliases", {}).items():
            for canonical, aliases in items.items():
                mappings[canonical.lower()] = canonical.lower()
                for alias in aliases:
                    mappings[alias.lower()] = canonical.lower()
        
        return mappings
    
    def is_poultry_related(self, text: str) -> Tuple[bool, float]:
        """Détermine si un texte est lié à l'aviculture"""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        # Compter les mots du vocabulaire avicole
        poultry_words = [word for word in words if word in self.poultry_keywords]
        
        if not words:
            return False, 0.0
        
        # Score basé sur la proportion de mots avicoles
        score = len(poultry_words) / len(words)
        
        # Bonus si des termes très spécifiques sont détectés
        specific_terms = ['ross', 'cobb', 'hubbard', 'broiler', 'layer', 'fcr', 'aviculture']
        specific_found = any(term in text_lower for term in specific_terms)
        
        if specific_found:
            score = min(1.0, score + 0.3)
        
        is_poultry = score >= 0.1 or specific_found
        
        logger.debug(f"Classification vocabulaire: '{text[:50]}...' -> {is_poultry} (score: {score:.3f})")
        
        return is_poultry, score

class QueryExpander:
    """Expanseur de requêtes avec synonymes du domaine"""
    
    def __init__(self, vocabulary_extractor: PoultryVocabularyExtractor):
        self.vocab_extractor = vocabulary_extractor
        self.alias_mappings = vocabulary_extractor.alias_mappings
    
    def expand_query(self, query: str, max_expansions: int = 5) -> str:
        """Enrichit une requête avec des synonymes et termes liés"""
        query_lower = query.lower()
        expansion_terms = set()
        
        # Détecter les alias dans la requête et ajouter les formes canoniques
        for alias, canonical in self.alias_mappings.items():
            if alias in query_lower and alias != canonical:
                expansion_terms.add(canonical)
                
                # Ajouter quelques alias supplémentaires du même groupe
                related_aliases = [k for k, v in self.alias_mappings.items() 
                                 if v == canonical and k != alias][:2]
                expansion_terms.update(related_aliases)
        
        # Limiter le nombre d'expansions pour éviter la pollution
        expansion_terms = list(expansion_terms)[:max_expansions]
        
        if expansion_terms:
            expanded_query = query + " " + " ".join(expansion_terms)
            logger.debug(f"Requête expansée: '{query}' -> '{expanded_query}'")
            return expanded_query
        
        return query

class EntityExtractor:
    """Extracteur d'entités métier (lignées, âges, métriques, etc.)"""
    
    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        self.age_pattern = re.compile(r'\b(\d+)\s*(jour|day|semaine|week|j|sem)\b', re.IGNORECASE)
        self.number_pattern = re.compile(r'\b\d+([.,]\d+)?\b')
        
    def extract_entities(self, text: str) -> Dict[str, str]:
        """Extrait les entités métier d'un texte"""
        entities = {}
        text_lower = text.lower()
        
        # Extraction des lignées
        entities.update(self._extract_lines(text_lower))
        
        # Extraction des âges
        entities.update(self._extract_ages(text))
        
        # Extraction des types de site
        entities.update(self._extract_site_types(text_lower))
        
        # Extraction des métriques
        entities.update(self._extract_metrics(text_lower))
        
        # Extraction des phases
        entities.update(self._extract_phases(text_lower))
        
        return entities
    
    def _extract_lines(self, text: str) -> Dict[str, str]:
        """Extrait les lignées de volailles"""
        for canonical, aliases in self.intents_config.get("aliases", {}).get("line", {}).items():
            if canonical.lower() in text or any(alias.lower() in text for alias in aliases):
                return {"line": canonical}
        return {}
    
    def _extract_ages(self, text: str) -> Dict[str, str]:
        """Extrait les informations d'âge"""
        entities = {}
        
        # Recherche des patterns d'âge
        matches = self.age_pattern.findall(text)
        for number, unit in matches:
            age_value = int(number)
            unit_lower = unit.lower()
            
            if unit_lower in ['jour', 'day', 'j']:
                entities["age_days"] = str(age_value)
                entities["age_weeks"] = str(age_value // 7)
            elif unit_lower in ['semaine', 'week', 'sem']:
                entities["age_weeks"] = str(age_value)
                entities["age_days"] = str(age_value * 7)
        
        return entities
    
    def _extract_site_types(self, text: str) -> Dict[str, str]:
        """Extrait les types de site d'élevage"""
        for canonical, aliases in self.intents_config.get("aliases", {}).get("site_type", {}).items():
            if canonical.lower() in text or any(alias.lower() in text for alias in aliases):
                return {"site_type": canonical}
        return {}
    
    def _extract_metrics(self, text: str) -> Dict[str, str]:
        """Extrait les métriques mentionnées"""
        detected_metrics = []
        
        for intent_config in self.intents_config.get("intents", {}).values():
            metrics = intent_config.get("metrics", {})
            for metric_name in metrics.keys():
                metric_lower = metric_name.lower()
                # Recherche de correspondances approximatives
                if (metric_lower in text or 
                    any(keyword in text for keyword in metric_lower.split('_'))):
                    detected_metrics.append(metric_name)
        
        if detected_metrics:
            return {"metrics": ",".join(detected_metrics[:3])}  # Limite à 3 métriques
        return {}
    
    def _extract_phases(self, text: str) -> Dict[str, str]:
        """Extrait les phases d'élevage"""
        for canonical, aliases in self.intents_config.get("aliases", {}).get("phase", {}).items():
            if canonical.lower() in text or any(alias.lower() in text for alias in aliases):
                return {"phase": canonical}
        return {}

class IntentClassifier:
    """Classificateur d'intentions métier"""
    
    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        self.intent_keywords = self._build_intent_keywords()
    
    def _build_intent_keywords(self) -> Dict[str, Set[str]]:
        """Construit les mots-clés associés à chaque type d'intention"""
        keywords = {}
        
        # Mots-clés pour metric_query
        keywords[IntentType.METRIC_QUERY.value] = {
            'poids', 'weight', 'fcr', 'conversion', 'consommation', 'eau', 'water',
            'performance', 'production', 'croissance', 'growth', 'optimal', 'target',
            'gramme', 'kg', 'litre', 'pourcentage', 'combien', 'how much'
        }
        
        # Mots-clés pour environment_setting
        keywords[IntentType.ENVIRONMENT_SETTING.value] = {
            'température', 'temperature', 'ventilation', 'climatisation', 'chauffage',
            'humidité', 'humidity', 'air', 'climat', 'ambiance', 'réglage', 'setting'
        }
        
        # Mots-clés pour protocol_query
        keywords[IntentType.PROTOCOL_QUERY.value] = {
            'vaccination', 'protocole', 'protocol', 'traitement', 'treatment',
            'biosécurité', 'biosecurity', 'prévention', 'prevention', 'vaccin'
        }
        
        # Mots-clés pour diagnosis_triage
        keywords[IntentType.DIAGNOSIS_TRIAGE.value] = {
            'maladie', 'disease', 'symptôme', 'symptom', 'diagnostic', 'diagnosis',
            'mortalité', 'mortality', 'problème', 'problem', 'signes', 'signs'
        }
        
        # Mots-clés pour economics_cost
        keywords[IntentType.ECONOMICS_COST.value] = {
            'coût', 'cost', 'prix', 'price', 'économique', 'economic', 'rentabilité',
            'profit', 'marge', 'margin', 'budget', 'finance', 'euros', 'dollars'
        }
        
        return keywords
    
    def classify_intent(self, text: str, entities: Dict[str, str]) -> IntentType:
        """Classifie l'intention d'une requête"""
        text_lower = text.lower()
        scores = {}
        
        # Calculer les scores pour chaque intention
        for intent_type, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            
            # Bonus basé sur les entités extraites
            if intent_type == IntentType.METRIC_QUERY.value and "metrics" in entities:
                score += 2
            elif intent_type == IntentType.ENVIRONMENT_SETTING.value and "site_type" in entities:
                score += 1
            elif intent_type == IntentType.ECONOMICS_COST.value and any(word in text_lower for word in ['coût', 'cost', 'prix']):
                score += 2
            
            scores[intent_type] = score
        
        # Retourner l'intention avec le score le plus élevé
        if max(scores.values()) > 0:
            best_intent = max(scores, key=scores.get)
            return IntentType(best_intent)
        
        # Fallback vers intention générale si aucune spécifique détectée
        return IntentType.GENERAL_POULTRY

class IntentProcessor:
    """Processeur principal d'intentions métier"""
    
    def __init__(self, intents_file_path: str):
        self.intents_config = self._load_intents_config(intents_file_path)
        self.vocabulary_extractor = PoultryVocabularyExtractor(self.intents_config)
        self.query_expander = QueryExpander(self.vocabulary_extractor)
        self.entity_extractor = EntityExtractor(self.intents_config)
        self.intent_classifier = IntentClassifier(self.intents_config)
        
        logger.info(f"IntentProcessor initialisé avec {len(self.vocabulary_extractor.poultry_keywords)} termes")
    
    def _load_intents_config(self, file_path: str) -> dict:
        """Charge la configuration des intentions"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Configuration intentions chargée: {file_path}")
            return config
        except Exception as e:
            logger.error(f"Erreur chargement intents.json: {e}")
            return {}
    
    def process_query(self, query: str) -> IntentResult:
        """Traite une requête complètement"""
        start_time = time.time()
        
        # 1. Vérification du domaine avicole
        is_poultry, vocab_confidence = self.vocabulary_extractor.is_poultry_related(query)
        
        if not is_poultry:
            return IntentResult(
                intent_type=IntentType.OUT_OF_DOMAIN,
                confidence=1.0 - vocab_confidence,
                detected_entities={},
                expanded_query=query,
                metadata={
                    "vocab_score": vocab_confidence,
                    "processing_time": time.time() - start_time
                }
            )
        
        # 2. Extraction d'entités
        entities = self.entity_extractor.extract_entities(query)
        
        # 3. Classification d'intention
        intent_type = self.intent_classifier.classify_intent(query, entities)
        
        # 4. Expansion de la requête
        expanded_query = self.query_expander.expand_query(query)
        
        # 5. Calcul de la confiance finale
        confidence = min(0.95, vocab_confidence + 0.2)  # Bonus pour la cohérence
        
        processing_time = time.time() - start_time
        
        result = IntentResult(
            intent_type=intent_type,
            confidence=confidence,
            detected_entities=entities,
            expanded_query=expanded_query,
            metadata={
                "vocab_score": vocab_confidence,
                "processing_time": processing_time,
                "original_query_length": len(query),
                "expansion_added": len(expanded_query) - len(query)
            }
        )
        
        logger.debug(f"Requête traitée: '{query}' -> {intent_type.value} (conf: {confidence:.3f})")
        
        return result
    
    def get_specialized_prompt(self, intent_result: IntentResult) -> Optional[str]:
        """Génère un prompt spécialisé selon le type d'intention"""
        intent_type = intent_result.intent_type
        entities = intent_result.detected_entities
        
        prompts = {
            IntentType.METRIC_QUERY: self._build_metric_prompt(entities),
            IntentType.ENVIRONMENT_SETTING: self._build_environment_prompt(entities),
            IntentType.DIAGNOSIS_TRIAGE: self._build_diagnosis_prompt(entities),
            IntentType.ECONOMICS_COST: self._build_economics_prompt(entities),
            IntentType.PROTOCOL_QUERY: self._build_protocol_prompt(entities)
        }
        
        return prompts.get(intent_type)
    
    def _build_metric_prompt(self, entities: Dict[str, str]) -> str:
        """Construit un prompt spécialisé pour les questions de métriques"""
        context = []
        
        if "line" in entities:
            context.append(f"Lignée détectée: {entities['line']}")
        if "age_days" in entities:
            context.append(f"Âge détecté: {entities['age_days']} jours")
        if "metrics" in entities:
            context.append(f"Métriques mentionnées: {entities['metrics']}")
        
        context_str = " | ".join(context) if context else ""
        
        return f"""Tu es un expert en performances avicoles. 
Contexte détecté: {context_str}

Fournis des données précises et des références aux standards de l'industrie.
Inclus les valeurs cibles, les plages normales et les facteurs d'influence."""
    
    def _build_environment_prompt(self, entities: Dict[str, str]) -> str:
        """Construit un prompt spécialisé pour l'environnement d'élevage"""
        return """Tu es un expert en ambiance et climat d'élevage avicole.
Fournis des paramètres techniques précis, des courbes de température,
et des recommandations de réglage selon l'âge et la saison."""
    
    def _build_diagnosis_prompt(self, entities: Dict[str, str]) -> str:
        """Construit un prompt spécialisé pour le diagnostic"""
        return """Tu es un vétérinaire spécialisé en aviculture.
Utilise une approche méthodique de diagnostic différentiel,
considère l'épidémiologie et propose des examens complémentaires."""
    
    def _build_economics_prompt(self, entities: Dict[str, str]) -> str:
        """Construit un prompt spécialisé pour l'économie"""
        return """Tu es un expert en économie de l'élevage avicole.
Fournis des analyses de coûts détaillées, des calculs de rentabilité
et des comparaisons avec les standards du marché."""
    
    def _build_protocol_prompt(self, entities: Dict[str, str]) -> str:
        """Construit un prompt spécialisé pour les protocoles"""
        return """Tu es un expert en protocoles vétérinaires et biosécurité avicole.
Fournis des protocoles détaillés, des calendriers de vaccination
et des mesures de prévention spécifiques."""

# Fonctions utilitaires pour l'intégration
def create_intent_processor(intents_file_path: str = None) -> IntentProcessor:
    """Factory pour créer un processeur d'intentions"""
    if intents_file_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        intents_file_path = os.path.join(base_dir, "intents.json")
    
    return IntentProcessor(intents_file_path)

def process_query_with_intents(processor: IntentProcessor, query: str) -> IntentResult:
    """Interface simple pour traiter une requête"""
    return processor.process_query(query)