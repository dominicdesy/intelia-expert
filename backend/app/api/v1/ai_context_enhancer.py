"""
ai_context_enhancer.py - ENHANCEMENT CONTEXTUEL AVEC IA

🎯 REMPLACE: 200+ lignes de patterns pronominaux rigides par compréhension IA
🚀 CAPACITÉS:
- ✅ Analyse conversationnelle intelligente
- ✅ Résolution des références contextuelles ("leur poids", "ces poulets")
- ✅ Enhancement pour recherche documentaire (RAG)
- ✅ Détection des clarifications implicites
- ✅ Fusion contextuelle automatique
- ✅ Support multilingue natif

Architecture:
- Analyse IA du contexte conversationnel
- Enhancement automatique des questions pour RAG
- Fusion intelligente des entités contextuelles
- Optimisation des requêtes de recherche
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime

from .ai_service_manager import AIServiceType, call_ai, AIResponse

logger = logging.getLogger(__name__)

@dataclass
class ContextAnalysis:
    """Résultat de l'analyse contextuelle"""
    references_detected: bool = False
    enhanced_question: str = ""
    context_entities: Dict[str, Any] = None
    missing_context: List[str] = None
    confidence: float = 0.0
    reasoning: str = ""
    
    def __post_init__(self):
        if self.context_entities is None:
            self.context_entities = {}
        if self.missing_context is None:
            self.missing_context = []

@dataclass  
class EnhancedContext:
    """Contexte enrichi pour la recherche et génération"""
    original_question: str
    enhanced_question: str
    merged_entities: Dict[str, Any]
    rag_optimized_query: str
    context_summary: str
    enhancement_confidence: float
    ai_reasoning: str

class AIContextEnhancer:
    """Enhancer contextuel avec IA - Remplace les patterns pronominaux"""
    
    def __init__(self):
        # Configuration des modèles
        self.models = {
            "context_analysis": "gpt-4",      # Analyse contextuelle complexe
            "question_enhancement": "gpt-4",   # Enhancement de questions
            "entity_fusion": "gpt-3.5-turbo", # Fusion d'entités
            "rag_optimization": "gpt-4"        # Optimisation pour RAG
        }
        
        # Prompts spécialisés
        self.prompts = self._initialize_prompts()
        
        logger.info("🤖 [AI Context Enhancer] Initialisé avec analyse IA contextuelle")
    
    def _initialize_prompts(self) -> Dict[str, str]:
        """Initialise les prompts spécialisés pour l'enhancement contextuel"""
        return {
            "context_analysis": """Analyse cette question dans son contexte conversationnel pour détecter les références implicites.

QUESTION ACTUELLE: "{current_question}"

CONTEXTE CONVERSATIONNEL:
{conversation_context}

TÂCHE: Détermine si la question fait référence à des éléments du contexte précédent.

Recherche:
1. **PRONOMS/RÉFÉRENCES**: "leur", "son", "ces", "ils", "elles", etc.
2. **RÉFÉRENCES IMPLICITES**: "à cet âge", "pour cette race", "dans ce cas"
3. **CONTEXTE MANQUANT**: éléments nécessaires non explicites

Réponds en JSON:
```json
{{
  "references_detected": true|false,
  "reference_types": ["pronoms", "implicite", "contextuel"],
  "referenced_entities": {{
    "breed": "race référencée du contexte",
    "age": "âge référencé du contexte", 
    "sex": "sexe référencé du contexte",
    "previous_topic": "sujet précédent"
  }},
  "missing_context": ["éléments manquants pour comprendre"],
  "confidence": 0.0-1.0,
  "analysis_reasoning": "explication de l'analyse"
}}
```

EXEMPLES:
- "Leur poids à 21 jours ?" → références à une race mentionnée précédemment
- "Et pour les femelles ?" → référence au sexe opposé d'une discussion précédente
- "À cet âge, c'est normal ?" → référence à un âge mentionné précédemment""",

            "question_enhancement": """Enrichis cette question en rendant explicites toutes les références contextuelles.

QUESTION ORIGINALE: "{original_question}"

CONTEXTE IDENTIFIÉ:
{context_entities}

RÉFÉRENCES DÉTECTÉES:
{references_detected}

TÂCHE: Reformule la question en rendant tout explicite et auto-suffisant.

RÈGLES:
1. Remplace les pronoms par les entités concrètes
2. Explicite les références implicites  
3. Conserve l'intention originale
4. Rends la question optimale pour recherche documentaire
5. Garde un langage naturel

EXEMPLES:
- "Leur poids normal ?" + Contexte[Ross 308, 21 jours] → "Quel est le poids normal des poulets Ross 308 à 21 jours ?"
- "Et les femelles ?" + Contexte[Cobb 500, mâles, poids] → "Quel est le poids normal des Cobb 500 femelles ?"
- "C'est normal à cet âge ?" + Contexte[croissance, 14 jours] → "La croissance est-elle normale pour des poulets de 14 jours ?"

Réponds en JSON:
```json
{{
  "enhanced_question": "question reformulée explicite",
  "entities_added": ["entités ajoutées du contexte"],
  "enhancement_confidence": 0.0-1.0,
  "enhancement_reasoning": "explication des modifications"
}}
```""",

            "entity_fusion": """Fusionne intelligemment les entités actuelles avec le contexte conversationnel.

ENTITÉS ACTUELLES:
{current_entities}

CONTEXTE CONVERSATIONNEL:
{context_entities}

TÂCHE: Combine les entités pour créer une vue complète et cohérente.

RÈGLES DE FUSION:
1. **PRIORITÉ**: Entités actuelles > contexte (sauf si actuelles vides)
2. **HÉRITAGE**: Hérite du contexte si entités actuelles incomplètes
3. **COHÉRENCE**: Vérifie compatibilité des combinaisons
4. **COMPLÉTION**: Comble les manques avec le contexte

LOGIQUE:
- Si breed actuel vide et breed contexte présent → hérite
- Si age actuel vide et age contexte présent → hérite  
- Si sex actuel vide et sex contexte présent → hérite
- Si context_type actuel vague et contexte précis → hérite

Réponds en JSON:
```json
{{
  "merged_entities": {{
    "age_days": number|null,
    "breed_specific": "breed"|null,
    "sex": "male"|"female"|"mixed"|null,
    "context_type": "performance"|"santé"|"alimentation",
    "weight_mentioned": true|false,
    "inherited_from_context": ["liste des champs hérités"]
  }},
  "fusion_confidence": 0.0-1.0,
  "fusion_notes": "explication de la fusion"
}}
```""",

            "rag_optimization": """Optimise cette question pour la recherche documentaire (RAG) dans une base de connaissances avicoles.

QUESTION ENHANCED: "{enhanced_question}"
ENTITÉS FUSIONNÉES: {merged_entities}

TÂCHE: Crée une requête optimale pour récupérer les documents les plus pertinents.

OPTIMISATIONS:
1. **MOTS-CLÉS TECHNIQUES**: Utilise terminologie spécialisée avicole
2. **SYNONYMES**: Inclus variations (croissance/développement, poids/masse)
3. **SPÉCIFICITÉ**: Balance spécificité et couverture
4. **STRUCTURE**: Organise pour matching sémantique optimal

EXEMPLES:
- "Poids normal Ross 308 mâles 21 jours" → "poids standard poulets broilers Ross 308 mâles trois semaines 21 jours croissance normale"
- "Symptômes diarrhée poules pondeuses" → "diarrhée troubles digestifs poules pondeuses symptômes santé intestinale"

Réponds en JSON:
```json
{{
  "rag_query": "requête optimisée pour recherche",
  "key_terms": ["termes", "clés", "importants"],
  "synonyms_included": ["variations", "ajoutées"],
  "optimization_confidence": 0.0-1.0,
  "optimization_notes": "explication des optimisations"
}}
```""",

            "context_summary": """Crée un résumé du contexte conversationnel pour mémoire à long terme.

HISTORIQUE CONVERSATION:
{conversation_history}

ENTITÉS ÉTABLIES:
{established_entities}

TÂCHE: Résume l'essentiel pour maintenir la cohérence conversationnelle.

RÉSUMÉ DOIT INCLURE:
1. **SUJET PRINCIPAL**: Thème de la conversation
2. **ENTITÉS ÉTABLIES**: Race, âge, sexe, contexte récurrents
3. **PATTERN QUESTIONS**: Type de questions posées
4. **CONTEXTE TECHNIQUE**: Niveau technique de l'utilisateur

Réponds en JSON:
```json
{{
  "conversation_topic": "sujet principal",
  "established_entities": {{
    "breed": "race établie",
    "typical_age": "âge typique discuté", 
    "sex": "sexe typique",
    "context_type": "type de questions"
  }},
  "user_profile": {{
    "technical_level": "débutant|intermédiaire|expert",
    "focus_areas": ["domaines d'intérêt"],
    "question_patterns": ["types de questions récurrentes"]
  }},
  "summary_confidence": 0.0-1.0
}}
```"""
        }
    
    async def analyze_conversational_context(self, 
                                           current_question: str, 
                                           conversation_history: str,
                                           language: str = "fr") -> ContextAnalysis:
        """
        Analyse le contexte conversationnel pour détecter les références
        
        Args:
            current_question: Question actuelle de l'utilisateur
            conversation_history: Historique de la conversation  
            language: Langue détectée
            
        Returns:
            ContextAnalysis avec les références détectées
        """
        try:
            logger.info(f"🤖 [AI Context Enhancer] Analyse contextuelle: '{current_question[:50]}...'")
            
            # Préparer le contexte pour analyse
            context_prompt = self.prompts["context_analysis"].format(
                current_question=current_question,
                conversation_context=conversation_history[:2000]  # Limiter pour token efficiency
            )
            
            # Analyse IA du contexte
            ai_response = await call_ai(
                service_type=AIServiceType.CONTEXT_ENHANCEMENT,
                prompt=context_prompt,
                model=self.models["context_analysis"],
                max_tokens=600,
                temperature=0.1,
                cache_key=f"context_analysis_{hash(current_question + conversation_history[:500])}"
            )
            
            # Parser le résultat
            analysis_data = self._parse_json_response(ai_response.content)
            
            # Construire ContextAnalysis
            analysis = ContextAnalysis(
                references_detected=analysis_data.get("references_detected", False),
                context_entities=analysis_data.get("referenced_entities", {}),
                missing_context=analysis_data.get("missing_context", []),
                confidence=analysis_data.get("confidence", 0.0),
                reasoning=analysis_data.get("analysis_reasoning", "")
            )
            
            logger.info(f"✅ [AI Context Enhancer] Analyse terminée: références={analysis.references_detected}, confiance={analysis.confidence}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ [AI Context Enhancer] Erreur analyse contextuelle: {e}")
            return ContextAnalysis(reasoning=f"Erreur: {e}")
    
    async def enhance_question_for_rag(self, 
                                     original_question: str,
                                     conversation_context: str = "",
                                     current_entities: Dict[str, Any] = None,
                                     language: str = "fr") -> EnhancedContext:
        """
        Point d'entrée principal - Enhancement complet pour RAG
        
        Args:
            original_question: Question originale
            conversation_context: Contexte conversationnel
            current_entities: Entités extraites de la question actuelle
            language: Langue
            
        Returns:
            EnhancedContext avec question optimisée et contexte fusionné
        """
        try:
            logger.info(f"🤖 [AI Context Enhancer] Enhancement complet: '{original_question[:50]}...'")
            
            if current_entities is None:
                current_entities = {}
            
            # 1. Analyser le contexte conversationnel
            context_analysis = await self.analyze_conversational_context(
                original_question, conversation_context, language
            )
            
            # 2. Enhancer la question si références détectées
            enhanced_question = original_question
            if context_analysis.references_detected:
                enhanced_question = await self._enhance_question_with_context(
                    original_question, context_analysis.context_entities
                )
            
            # 3. Fusionner les entités
            merged_entities = await self._merge_entities_with_context(
                current_entities, context_analysis.context_entities
            )
            
            # 4. Optimiser pour RAG
            rag_query = await self._optimize_for_rag(enhanced_question, merged_entities)
            
            # 5. Créer le résumé contextuel
            context_summary = await self._create_context_summary(
                conversation_context, merged_entities
            )
            
            # Construire résultat final
            enhanced_context = EnhancedContext(
                original_question=original_question,
                enhanced_question=enhanced_question,
                merged_entities=merged_entities,
                rag_optimized_query=rag_query,
                context_summary=context_summary,
                enhancement_confidence=context_analysis.confidence,
                ai_reasoning=context_analysis.reasoning
            )
            
            logger.info(f"✅ [AI Context Enhancer] Enhancement terminé: '{enhanced_question}'")
            
            return enhanced_context
            
        except Exception as e:
            logger.error(f"❌ [AI Context Enhancer] Erreur enhancement: {e}")
            # Retour fallback
            return EnhancedContext(
                original_question=original_question,
                enhanced_question=original_question,
                merged_entities=current_entities or {},
                rag_optimized_query=original_question,
                context_summary="Erreur enhancement contextuel",
                enhancement_confidence=0.0,
                ai_reasoning=f"Erreur: {e}"
            )
    
    async def _enhance_question_with_context(self, 
                                           original_question: str, 
                                           context_entities: Dict[str, Any]) -> str:
        """Enhancement de la question avec contexte"""
        
        try:
            prompt = self.prompts["question_enhancement"].format(
                original_question=original_question,
                context_entities=json.dumps(context_entities, ensure_ascii=False),
                references_detected=True
            )
            
            ai_response = await call_ai(
                service_type=AIServiceType.CONTEXT_ENHANCEMENT,
                prompt=prompt,
                model=self.models["question_enhancement"],
                max_tokens=400,
                temperature=0.1
            )
            
            result = self._parse_json_response(ai_response.content)
            enhanced = result.get("enhanced_question", original_question)
            
            logger.info(f"✅ [Question Enhancement] '{original_question}' → '{enhanced}'")
            return enhanced
            
        except Exception as e:
            logger.warning(f"⚠️ [Question Enhancement] Erreur: {e}")
            return original_question
    
    async def _merge_entities_with_context(self, 
                                         current_entities: Dict[str, Any], 
                                         context_entities: Dict[str, Any]) -> Dict[str, Any]:
        """Fusion intelligente des entités"""
        
        try:
            prompt = self.prompts["entity_fusion"].format(
                current_entities=json.dumps(current_entities, ensure_ascii=False),
                context_entities=json.dumps(context_entities, ensure_ascii=False)
            )
            
            ai_response = await call_ai(
                service_type=AIServiceType.CONTEXT_ENHANCEMENT,
                prompt=prompt,
                model=self.models["entity_fusion"],
                max_tokens=500,
                temperature=0.05
            )
            
            result = self._parse_json_response(ai_response.content)
            merged = result.get("merged_entities", current_entities)
            
            logger.info(f"✅ [Entity Fusion] Entités fusionnées: {len(merged)} champs")
            return merged
            
        except Exception as e:
            logger.warning(f"⚠️ [Entity Fusion] Erreur: {e}")
            # Fusion simple en fallback
            return {**context_entities, **current_entities}
    
    async def _optimize_for_rag(self, enhanced_question: str, merged_entities: Dict[str, Any]) -> str:
        """Optimise la question pour la recherche RAG"""
        
        try:
            prompt = self.prompts["rag_optimization"].format(
                enhanced_question=enhanced_question,
                merged_entities=json.dumps(merged_entities, ensure_ascii=False)
            )
            
            ai_response = await call_ai(
                service_type=AIServiceType.CONTEXT_ENHANCEMENT,
                prompt=prompt,
                model=self.models["rag_optimization"],
                max_tokens=300,
                temperature=0.1
            )
            
            result = self._parse_json_response(ai_response.content)
            rag_query = result.get("rag_query", enhanced_question)
            
            logger.info(f"✅ [RAG Optimization] Query optimisée: '{rag_query}'")
            return rag_query
            
        except Exception as e:
            logger.warning(f"⚠️ [RAG Optimization] Erreur: {e}")
            return enhanced_question
    
    async def _create_context_summary(self, conversation_history: str, entities: Dict[str, Any]) -> str:
        """Crée un résumé du contexte pour mémoire"""
        
        try:
            if not conversation_history or len(conversation_history) < 50:
                return "Conversation nouvelle - pas d'historique"
            
            prompt = self.prompts["context_summary"].format(
                conversation_history=conversation_history[-1000:],  # Derniers éléments
                established_entities=json.dumps(entities, ensure_ascii=False)
            )
            
            ai_response = await call_ai(
                service_type=AIServiceType.CONTEXT_ENHANCEMENT,
                prompt=prompt,
                model="gpt-3.5-turbo",  # Suffisant pour résumé
                max_tokens=300,
                temperature=0.2
            )
            
            result = self._parse_json_response(ai_response.content)
            topic = result.get("conversation_topic", "Discussion générale")
            
            return f"Sujet: {topic} | Entités: {result.get('established_entities', {})}"
            
        except Exception as e:
            logger.warning(f"⚠️ [Context Summary] Erreur: {e}")
            return "Résumé contextuel indisponible"
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse une réponse JSON de l'IA avec gestion d'erreurs"""
        
        try:
            # Nettoyer le contenu
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ [AI Context Enhancer] Erreur parsing JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ [AI Context Enhancer] Erreur parsing: {e}")
            return {}
    
    async def enhance_for_classification(self, 
                                       question: str, 
                                       conversation_context: str = "") -> Dict[str, Any]:
        """Enhancement spécialisé pour améliorer la classification"""
        
        try:
            # Analyse rapide pour la classification
            enhanced_context = await self.enhance_question_for_rag(
                question, conversation_context
            )
            
            return {
                "enhanced_question": enhanced_context.enhanced_question,
                "context_confidence": enhanced_context.enhancement_confidence,
                "has_references": enhanced_context.enhanced_question != question,
                "merged_entities": enhanced_context.merged_entities,
                "classification_hints": {
                    "likely_contextual": enhanced_context.enhancement_confidence > 0.7,
                    "needs_clarification": enhanced_context.enhancement_confidence < 0.3,
                    "has_sufficient_context": len(enhanced_context.merged_entities) >= 2
                }
            }
            
        