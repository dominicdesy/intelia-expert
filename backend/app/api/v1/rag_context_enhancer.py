# Nouveau module: rag_context_enhancer.py
# Améliore le contexte conversationnel pour le RAG - Version Structurée

import re
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class RAGContextEnhancer:
    """Améliore le contexte conversationnel pour optimiser les requêtes RAG"""
    
    def __init__(self):
        # Patterns pour détecter les références contextuelles
        self.pronoun_patterns = {
            "fr": [
                r'\b(son|sa|ses|leur|leurs)\s+(poids|âge|croissance|développement)',
                r'\b(ils|elles)\s+(pèsent|grandissent|se développent)',
                r'\b(qu\'?est-ce que|quel est)\s+(son|sa|ses|leur)',
                r'\b(combien)\s+(pèsent-ils|font-ils|mesurent-ils)'
            ],
            "en": [
                r'\b(their|its)\s+(weight|age|growth|development)',
                r'\b(they)\s+(weigh|grow|develop)',
                r'\b(what is|how much is)\s+(their|its)',
                r'\b(how much do they)\s+(weigh|measure)'
            ],
            "es": [
                r'\b(su|sus)\s+(peso|edad|crecimiento|desarrollo)',
                r'\b(ellos|ellas)\s+(pesan|crecen|se desarrollan)',
                r'\b(cuál es|cuánto es)\s+(su|sus)',
                r'\b(cuánto)\s+(pesan|miden)'
            ]
        }
        
        # Entités importantes à extraire du contexte
        self.key_entities = ["breed", "age", "weight", "housing", "symptoms", "feed", "environment"]
    
    def enhance_question_for_rag(
        self, 
        question: str, 
        conversation_context: str, 
        language: str = "fr",
        missing_entities: List[str] = None
    ) -> Dict[str, Any]:
        """
        Améliore une question pour le RAG en utilisant le contexte conversationnel
        
        Args:
            question: Question originale
            conversation_context: Contexte conversationnel
            language: Langue
            missing_entities: Liste des entités manquantes (optionnel)
        
        Returns:
            Dict contenant:
            - question: Question optimisée pour RAG
            - missing_entities: Liste des entités manquantes identifiées
            - context_entities: Dictionnaire des entités extraites du contexte
            - enhancement_info: Métadonnées sur les améliorations appliquées
        """
        
        # Initialiser le résultat structuré
        result = {
            "question": question,  # Question enrichie (sera modifiée si nécessaire)
            "missing_entities": missing_entities or [],
            "context_entities": {},
            "enhancement_info": {
                "pronoun_detected": False,
                "question_enriched": False,
                "original_question": question,
                "technical_context_added": False,
                "missing_context_added": False
            }
        }
        
        # 1. Détecter les pronoms/références contextuelles
        has_pronouns = self._detect_contextual_references(question, language)
        if has_pronouns:
            result["enhancement_info"]["pronoun_detected"] = True
            logger.info(f"🔍 [RAG Context] Pronoms détectés dans: '{question}'")
        
        # 2. Extraire entités du contexte
        context_entities = self._extract_context_entities(conversation_context)
        result["context_entities"] = context_entities
        
        if context_entities:
            logger.info(f"📊 [RAG Context] Entités contextuelles: {context_entities}")
        
        # 3. Identifier entités manquantes automatiquement si non spécifiées
        if not result["missing_entities"]:
            result["missing_entities"] = self._identify_missing_entities(
                question, context_entities, language
            )
        
        # 4. Enrichir la question si nécessaire
        enriched_question = question
        
        if has_pronouns and context_entities:
            enriched_question = self._build_enriched_question(
                question, context_entities, language
            )
            result["enhancement_info"]["question_enriched"] = True
            logger.info(f"✨ [RAG Context] Question enrichie: '{enriched_question}'")
        
        # 5. Ajouter contexte technique si pertinent
        if context_entities or has_pronouns:
            technical_context = self._build_technical_context(context_entities, language)
            if technical_context:
                enriched_question += f"\n\nContexte technique: {technical_context}"
                result["enhancement_info"]["technical_context_added"] = True
        
        # 6. Ajouter information sur les entités manquantes
        if result["missing_entities"]:
            missing_context = self._build_missing_entities_context(
                result["missing_entities"], language
            )
            if missing_context:
                enriched_question += f"\n\n{missing_context}"
                result["enhancement_info"]["missing_context_added"] = True
                logger.info(f"ℹ️ [RAG Context] Entités manquantes ajoutées: {result['missing_entities']}")
        
        # 7. Mettre à jour la question finale
        result["question"] = enriched_question
        
        return result
    
    def _detect_contextual_references(self, question: str, language: str) -> bool:
        """Détecte si la question contient des pronoms/références contextuelles"""
        
        patterns = self.pronoun_patterns.get(language, self.pronoun_patterns["fr"])
        question_lower = question.lower()
        
        for pattern in patterns:
            if re.search(pattern, question_lower, re.IGNORECASE):
                logger.debug(f"🎯 [RAG Context] Pattern trouvé: {pattern}")
                return True
        
        return False
    
    def _extract_context_entities(self, context: str) -> Dict[str, str]:
        """Extrait les entités importantes du contexte conversationnel"""
        
        if not context:
            return {}
        
        entities = {}
        context_lower = context.lower()
        
        # Extraire race
        breed_patterns = [
            r'race[:\s]+([a-zA-Z0-9\s]+?)(?:\n|,|\.|\s|$)',
            r'breed[:\s]+([a-zA-Z0-9\s]+?)(?:\n|,|\.|\s|$)', 
            r'(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)',
            r'poulets?\s+(ross\s*308|cobb\s*500)',
            r'chickens?\s+(ross\s*308|cobb\s*500)'
        ]
        
        for pattern in breed_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["breed"] = match.group(1).strip()
                break
        
        # Extraire âge
        age_patterns = [
            r'âge[:\s]+(\d+\s*(?:jour|semaine|day|week)s?)',
            r'age[:\s]+(\d+\s*(?:jour|semaine|day|week)s?)',
            r'(\d+)\s*(?:jour|day)s?',
            r'(\d+)\s*(?:semaine|week)s?'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["age"] = match.group(1).strip()
                break
        
        # Extraire poids
        weight_patterns = [
            r'poids[:\s]+(\d+(?:\.\d+)?\s*[gk]?g?)',
            r'weight[:\s]+(\d+(?:\.\d+)?\s*[gk]?g?)',
            r'(\d+(?:\.\d+)?)\s*(?:gramme|gram|kg)s?'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["weight"] = match.group(1).strip()
                break
        
        # Extraire conditions d'hébergement
        housing_patterns = [
            r'hébergement[:\s]+([^.\n]+)',
            r'housing[:\s]+([^.\n]+)',
            r'logement[:\s]+([^.\n]+)',
            r'barn[:\s]+([^.\n]+)'
        ]
        
        for pattern in housing_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["housing"] = match.group(1).strip()
                break
        
        # Extraire symptômes
        symptoms_patterns = [
            r'symptômes?[:\s]+([^.\n]+)',
            r'symptoms?[:\s]+([^.\n]+)',
            r'problème[:\s]+([^.\n]+)',
            r'problem[:\s]+([^.\n]+)'
        ]
        
        for pattern in symptoms_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["symptoms"] = match.group(1).strip()
                break
        
        return entities
    
    def _identify_missing_entities(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str
    ) -> List[str]:
        """Identifie automatiquement les entités manquantes pertinentes pour la question"""
        
        missing = []
        question_lower = question.lower()
        
        # Mots-clés qui suggèrent le besoin de certaines entités
        entity_keywords = {
            "breed": ["race", "breed", "poulet", "chicken", "pollo", "type"],
            "age": ["âge", "age", "edad", "jour", "day", "semaine", "week", "old"],
            "weight": ["poids", "weight", "peso", "gram", "kg", "lourd", "heavy"],
            "housing": ["barn", "hébergement", "logement", "housing", "condition"],
            "symptoms": ["problème", "problem", "symptôme", "symptom", "malade", "sick"],
            "feed": ["alimentation", "feed", "alimento", "nutrition", "nourriture"],
            "environment": ["température", "temperature", "humidité", "humidity", "climat"]
        }
        
        # Vérifier quelles entités sont mentionnées dans la question mais absentes du contexte
        for entity, keywords in entity_keywords.items():
            if entity not in context_entities:  # Entité absente du contexte
                # Vérifier si des mots-clés relatifs sont dans la question
                if any(keyword in question_lower for keyword in keywords):
                    missing.append(entity)
        
        # Entités toujours utiles pour certains types de questions
        diagnostic_keywords = ["problème", "problem", "malade", "sick", "diagnostic", "symptom"]
        if any(keyword in question_lower for keyword in diagnostic_keywords):
            # Pour les questions de diagnostic, ces entités sont souvent importantes
            for entity in ["breed", "age", "symptoms"]:
                if entity not in context_entities and entity not in missing:
                    missing.append(entity)
        
        performance_keywords = ["croissance", "growth", "poids", "weight", "développement", "development"]
        if any(keyword in question_lower for keyword in performance_keywords):
            # Pour les questions de performance, ces entités sont importantes
            for entity in ["breed", "age", "feed"]:
                if entity not in context_entities and entity not in missing:
                    missing.append(entity)
        
        return missing
    
    def _build_enriched_question(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str
    ) -> str:
        """Construit une question enrichie en remplaçant les pronoms par les entités contextuelles"""
        
        enriched = question
        
        # Templates par langue
        templates = {
            "fr": {
                "breed_age": "Pour des {breed} de {age}",
                "breed_only": "Pour des {breed}",
                "age_only": "Pour des poulets de {age}",
                "full_context": "Pour des {breed} de {age} pesant {weight}"
            },
            "en": {
                "breed_age": "For {breed} chickens at {age}",
                "breed_only": "For {breed} chickens", 
                "age_only": "For chickens at {age}",
                "full_context": "For {breed} chickens at {age} weighing {weight}"
            },
            "es": {
                "breed_age": "Para pollos {breed} de {age}",
                "breed_only": "Para pollos {breed}",
                "age_only": "Para pollos de {age}",
                "full_context": "Para pollos {breed} de {age} pesando {weight}"
            }
        }
        
        template_set = templates.get(language, templates["fr"])
        
        # Construire le préfixe contextuel (priorité au template le plus complet)
        context_prefix = ""
        if all(k in context_entities for k in ["breed", "age", "weight"]):
            context_prefix = template_set["full_context"].format(**context_entities)
        elif "breed" in context_entities and "age" in context_entities:
            context_prefix = template_set["breed_age"].format(**context_entities)
        elif "breed" in context_entities:
            context_prefix = template_set["breed_only"].format(breed=context_entities["breed"])
        elif "age" in context_entities:
            context_prefix = template_set["age_only"].format(age=context_entities["age"])
        
        if context_prefix:
            # Remplacer ou préfixer selon la structure de la question
            pronoun_words = ["son", "sa", "ses", "leur", "leurs", "their", "its", "su", "sus"]
            if any(word in question.lower() for word in pronoun_words):
                enriched = f"{context_prefix}, {question.lower()}"
            else:
                enriched = f"{context_prefix}: {question}"
        
        return enriched
    
    def _build_technical_context(self, entities: Dict[str, str], language: str) -> str:
        """Construit un contexte technique pour aider le RAG"""
        
        if not entities:
            return ""
        
        context_parts = []
        
        # Ordre de priorité pour l'affichage
        entity_order = ["breed", "age", "weight", "housing", "symptoms", "feed", "environment"]
        
        entity_labels = {
            "fr": {
                "breed": "Race", "age": "Âge", "weight": "Poids",
                "housing": "Hébergement", "symptoms": "Symptômes", 
                "feed": "Alimentation", "environment": "Environnement"
            },
            "en": {
                "breed": "Breed", "age": "Age", "weight": "Weight",
                "housing": "Housing", "symptoms": "Symptoms",
                "feed": "Feed", "environment": "Environment"
            },
            "es": {
                "breed": "Raza", "age": "Edad", "weight": "Peso",
                "housing": "Alojamiento", "symptoms": "Síntomas",
                "feed": "Alimentación", "environment": "Ambiente"
            }
        }
        
        labels = entity_labels.get(language, entity_labels["fr"])
        
        for entity in entity_order:
            if entity in entities:
                label = labels.get(entity, entity.capitalize())
                context_parts.append(f"{label}: {entities[entity]}")
        
        return " | ".join(context_parts)
    
    def _build_missing_entities_context(self, missing_entities: List[str], language: str) -> str:
        """Construit un contexte indiquant les entités manquantes pour guider le RAG"""
        
        if not missing_entities:
            return ""
        
        # Templates par langue pour indiquer les informations manquantes
        templates = {
            "fr": {
                "prefix": "Informations manquantes qui pourraient être pertinentes:",
                "entities": {
                    "breed": "race des animaux",
                    "age": "âge des animaux", 
                    "weight": "poids des animaux",
                    "housing": "conditions d'hébergement",
                    "symptoms": "symptômes observés",
                    "feed": "type d'alimentation",
                    "environment": "conditions environnementales"
                }
            },
            "en": {
                "prefix": "Missing information that could be relevant:",
                "entities": {
                    "breed": "animal breed",
                    "age": "animal age",
                    "weight": "animal weight", 
                    "housing": "housing conditions",
                    "symptoms": "observed symptoms",
                    "feed": "feed type",
                    "environment": "environmental conditions"
                }
            },
            "es": {
                "prefix": "Información faltante que podría ser relevante:",
                "entities": {
                    "breed": "raza de los animales",
                    "age": "edad de los animales",
                    "weight": "peso de los animales",
                    "housing": "condiciones de alojamiento", 
                    "symptoms": "síntomas observados",
                    "feed": "tipo de alimentación",
                    "environment": "condiciones ambientales"
                }
            }
        }
        
        template_set = templates.get(language, templates["fr"])
        prefix = template_set["prefix"]
        entity_names = template_set["entities"]
        
        # Construire la liste des entités manquantes
        missing_list = []
        for entity in missing_entities:
            if entity in entity_names:
                missing_list.append(entity_names[entity])
            else:
                missing_list.append(entity)  # Fallback au nom original
        
        if missing_list:
            return f"{prefix} {', '.join(missing_list)}"
        
        return ""

# Instance globale
rag_context_enhancer = RAGContextEnhancer()

def enhance_question_for_rag(
    question: str, 
    conversation_context: str, 
    language: str = "fr",
    missing_entities: List[str] = None
) -> Dict[str, Any]:
    """
    Fonction utilitaire pour améliorer une question pour le RAG
    
    Returns:
        Dict contenant:
        - question: Question optimisée pour RAG
        - missing_entities: Liste des entités manquantes identifiées
        - context_entities: Dictionnaire des entités extraites du contexte
        - enhancement_info: Métadonnées sur les améliorations appliquées
    """
    return rag_context_enhancer.enhance_question_for_rag(
        question, conversation_context, language, missing_entities
    )