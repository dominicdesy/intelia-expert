# Nouveau module: rag_context_enhancer.py
# Améliore le contexte conversationnel pour le RAG

import re
import logging
from typing import Dict, List, Optional, Tuple

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
        self.key_entities = ["breed", "age", "weight", "housing", "symptoms"]
    
    def enhance_question_for_rag(
        self, 
        question: str, 
        conversation_context: str, 
        language: str = "fr"
    ) -> Tuple[str, Dict[str, any]]:
        """
        Améliore une question pour le RAG en utilisant le contexte conversationnel
        
        Returns:
            - question_enrichie: Question optimisée pour RAG
            - enhancement_info: Informations sur les améliorations appliquées
        """
        
        enhancement_info = {
            "pronoun_detected": False,
            "context_entities_used": [],
            "question_enriched": False,
            "original_question": question
        }
        
        # 1. Détecter les pronoms/références contextuelles
        has_pronouns = self._detect_contextual_references(question, language)
        if has_pronouns:
            enhancement_info["pronoun_detected"] = True
            logger.info(f"🔍 [RAG Context] Pronoms détectés dans: '{question}'")
        
        # 2. Extraire entités du contexte
        context_entities = self._extract_context_entities(conversation_context)
        if context_entities:
            enhancement_info["context_entities_used"] = list(context_entities.keys())
            logger.info(f"📊 [RAG Context] Entités contextuelles: {context_entities}")
        
        # 3. Enrichir la question si nécessaire
        enriched_question = question
        
        if has_pronouns and context_entities:
            enriched_question = self._build_enriched_question(
                question, context_entities, language
            )
            enhancement_info["question_enriched"] = True
            logger.info(f"✨ [RAG Context] Question enrichie: '{enriched_question}'")
        
        # 4. Ajouter contexte technique si pertinent
        if context_entities or has_pronouns:
            technical_context = self._build_technical_context(context_entities, language)
            if technical_context:
                enriched_question += f"\n\nContexte technique: {technical_context}"
        
        return enriched_question, enhancement_info
    
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
        
        return entities
    
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
                "age_only": "Pour des poulets de {age}"
            },
            "en": {
                "breed_age": "For {breed} chickens at {age}",
                "breed_only": "For {breed} chickens", 
                "age_only": "For chickens at {age}"
            },
            "es": {
                "breed_age": "Para pollos {breed} de {age}",
                "breed_only": "Para pollos {breed}",
                "age_only": "Para pollos de {age}"
            }
        }
        
        template_set = templates.get(language, templates["fr"])
        
        # Construire le préfixe contextuel
        context_prefix = ""
        if "breed" in context_entities and "age" in context_entities:
            context_prefix = template_set["breed_age"].format(
                breed=context_entities["breed"],
                age=context_entities["age"]
            )
        elif "breed" in context_entities:
            context_prefix = template_set["breed_only"].format(
                breed=context_entities["breed"]
            )
        elif "age" in context_entities:
            context_prefix = template_set["age_only"].format(
                age=context_entities["age"]
            )
        
        if context_prefix:
            # Remplacer ou préfixer selon la structure de la question
            if any(word in question.lower() for word in ["son", "sa", "ses", "leur", "leurs", "their", "its", "su", "sus"]):
                enriched = f"{context_prefix}, {question.lower()}"
            else:
                enriched = f"{context_prefix}: {question}"
        
        return enriched
    
    def _build_technical_context(self, entities: Dict[str, str], language: str) -> str:
        """Construit un contexte technique pour aider le RAG"""
        
        if not entities:
            return ""
        
        context_parts = []
        
        if "breed" in entities:
            context_parts.append(f"Race: {entities['breed']}")
        
        if "age" in entities:
            context_parts.append(f"Âge: {entities['age']}")
        
        if "weight" in entities:
            context_parts.append(f"Poids: {entities['weight']}")
        
        return " | ".join(context_parts)

# Instance globale
rag_context_enhancer = RAGContextEnhancer()

def enhance_question_for_rag(
    question: str, 
    conversation_context: str, 
    language: str = "fr"
) -> Tuple[str, Dict[str, any]]:
    """Fonction utilitaire pour améliorer une question pour le RAG"""
    return rag_context_enhancer.enhance_question_for_rag(
        question, conversation_context, language
    )
