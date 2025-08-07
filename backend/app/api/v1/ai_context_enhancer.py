"""
ai_context_enhancer.py - ENHANCEMENT CONTEXTUEL AVEC IA - VERSION CORRIGÉE

🎯 CORRECTIONS APPLIQUÉES:
- ✅ FUSION STRICTE: Empêche l'héritage non justifié d'entités contextuelles
- ✅ DÉTECTION AUTONOME: Identifie les questions sans références contextuelles
- ✅ VALIDATION POST-FUSION: Vérifie la cohérence des fusions
- ✅ OPTIMISATION PERFORMANCE: Bypass intelligent pour questions simples
- ✅ GESTION D'ERREURS ROBUSTE: Fallbacks conservateurs
- ✅ LOGGING DÉTAILLÉ: Traçabilité complète des décisions

🚀 PRINCIPE CORRIGÉ: "Ross 308 male" ne doit PAS hériter l'âge du contexte précédent
🔧 LOGIQUE: Fusion uniquement sur références contextuelles explicites
✨ PERFORMANCE: Bypass automatique pour questions autonomes
💡 ROBUSTESSE: Validation systématique des résultats IA

Architecture:
- Analyse contextuelle stricte avec pré-filtrage
- Fusion d'entités avec règles de priorité claires
- Optimisation RAG avec validation
- Fallbacks conservateurs sur toutes les étapes
"""

import json
import logging
import re
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
    is_standalone: bool = False  # ✅ NOUVEAU: Flag pour questions autonomes
    
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
    fusion_applied: bool = False  # ✅ NOUVEAU: Indique si fusion contextuelle appliquée
    inheritance_log: List[str] = None  # ✅ NOUVEAU: Log des héritages appliqués
    
    def __post_init__(self):
        if self.inheritance_log is None:
            self.inheritance_log = []

class AIContextEnhancer:
    """Enhancer contextuel avec IA - Version corrigée avec fusion stricte"""
    
    def __init__(self):
        # Configuration des modèles
        self.models = {
            "context_analysis": "gpt-4o-mini",     # ✅ OPTIMISÉ: gpt-4 → gpt-4o-mini pour performance
            "question_enhancement": "gpt-4o-mini", # ✅ OPTIMISÉ: Performance/coût
            "entity_fusion": "gpt-4o-mini",        # ✅ OPTIMISÉ: Suffisant pour fusion
            "rag_optimization": "gpt-4o-mini"      # ✅ OPTIMISÉ: Performance
        }
        
        # ✅ NOUVEAU: Configuration des timeouts par service
        self.timeouts = {
            "context_analysis": 8,     # 8s pour analyse contextuelle
            "question_enhancement": 6, # 6s pour enhancement
            "entity_fusion": 5,        # 5s pour fusion
            "rag_optimization": 4      # 4s pour optimisation RAG
        }
        
        # ✅ NOUVEAU: Patterns pour détection automatique
        self.standalone_patterns = [
            r"^(Ross|Cobb|Hubbard)\s*\d+\s+(male|female|mâle|femelle|mixte?)$",  # "Ross 308 male"
            r"^(Ross|Cobb|Hubbard)\s*\d+$",  # "Ross 308"
            r"^\w+\s+(poulet|chicken|broiler|poule)\s+(de\s+)?\d+\s+(jour|day|semaine|week)",  # "poulet de 21 jours"
            r"^(Quel|What)\s+(est|is)\s+le\s+poids",  # Questions complètes de poids
        ]
        
        # ✅ NOUVEAU: Mots-clés contextuels pour détection références
        self.contextual_indicators = {
            "pronouns": ["leur", "son", "sa", "ses", "ces", "cette", "cet", "ils", "elles"],
            "references": ["aussi", "également", "comme", "suite", "précédemment", "déjà", "encore"],
            "temporal": ["maintenant", "à présent", "à cet âge", "dans ce cas", "pour eux"],
            "implicit": ["et pour", "qu'en est-il", "et alors", "et si", "même chose"]
        }
        
        # Prompts spécialisés
        self.prompts = self._initialize_prompts()
        
        # ✅ NOUVEAU: Statistiques pour monitoring
        self.stats = {
            "total_enhancements": 0,
            "standalone_bypassed": 0,
            "context_fusions": 0,
            "inheritance_applied": 0,
            "inheritance_rejected": 0,
            "errors": 0
        }
        
        logger.info("🤖 [AI Context Enhancer] Initialisé avec fusion stricte et détection autonome")
    
    def _initialize_prompts(self) -> Dict[str, str]:
        """Initialise les prompts spécialisés - VERSION CORRIGÉE"""
        return {
            "context_analysis": """Analyse cette question dans son contexte conversationnel pour détecter les références implicites EXPLICITES.

QUESTION ACTUELLE: "{current_question}"

CONTEXTE CONVERSATIONNEL:
{conversation_context}

⚠️ RÈGLES STRICTES DE DÉTECTION:
1. **RÉFÉRENCES EXPLICITES SEULEMENT**: Cherche des pronoms, références temporelles, ou liens directs
2. **PAS D'INFÉRENCE**: Ne pas déduire de références qui n'existent pas
3. **AUTONOMIE D'ABORD**: Si la question est complète et autonome, pas de références

🔍 RECHERCHE SPÉCIFIQUE:
- **PRONOMS**: "leur", "son", "ces", "ils", "elles"
- **RÉFÉRENCES TEMPORELLES**: "à cet âge", "comme précédemment", "maintenant"
- **RÉFÉRENCES IMPLICITES**: "et pour", "aussi", "également", "même chose"
- **CONTINUATIONS**: "et alors", "qu'en est-il de", "et si"

❌ NE PAS DÉTECTER COMME RÉFÉRENCE:
- Questions complètes avec race/âge/sexe explicites: "Ross 308 male", "poulet 21 jours"
- Questions techniques autonomes: "Quel est le poids normal..."
- Informations factuelles: "Hubbard femelle", "Cobb 500"

✅ DÉTECTER COMME RÉFÉRENCE:
- "Leur poids ?" → référence à une race/groupe mentionné
- "Et les femelles ?" → référence au sexe opposé
- "À cet âge ?" → référence à un âge mentionné
- "Même chose pour..." → référence à une situation précédente

Réponds en JSON:
```json
{{
  "references_detected": true|false,
  "reference_types": ["pronoms"|"implicite"|"temporel"|"continuation"],
  "specific_references": {{
    "pronouns_found": ["pronoms détectés"],
    "temporal_references": ["références temporelles"],
    "implicit_references": ["références implicites"]
  }},
  "referenced_entities": {{
    "breed": "race référencée du contexte"|null,
    "age": "âge référencé du contexte"|null,
    "sex": "sexe référencé du contexte"|null,
    "previous_topic": "sujet précédent"|null
  }},
  "is_standalone_question": true|false,
  "confidence": 0.0-1.0,
  "analysis_reasoning": "explication DÉTAILLÉE de la présence/absence de références"
}}
```""",

            "question_enhancement": """Enrichis cette question UNIQUEMENT si des références contextuelles explicites ont été détectées.

QUESTION ORIGINALE: "{original_question}"

CONTEXTE IDENTIFIÉ:
{context_entities}

RÉFÉRENCES DÉTECTÉES: {references_detected}

⚠️ RÈGLES STRICTES D'ENHANCEMENT:
1. **SEULEMENT SI RÉFÉRENCES**: N'enrichis QUE si references_detected = true
2. **REMPLACEMENT EXPLICITE**: Remplace les pronoms/références par les entités concrètes
3. **CONSERVATION INTENTION**: Conserve exactement l'intention originale
4. **PAS DE SURINTERPRÉTATION**: Si pas de références claires, retourne la question originale

✅ EXEMPLES VALIDES:
- "Leur poids ?" + Contexte[Ross 308] → "Quel est le poids des Ross 308 ?"
- "Et les femelles ?" + Contexte[Cobb 500, mâles] → "Et les Cobb 500 femelles ?"
- "À cet âge ?" + Contexte[21 jours] → "À 21 jours ?"

❌ EXEMPLES INVALIDES (PAS D'ENHANCEMENT):
- "Ross 308 male" → PAS de références → retourner tel quel
- "Poulet 21 jours" → Question autonome → retourner tel quel

Réponds en JSON:
```json
{{
  "enhanced_question": "question reformulée OU originale si pas de références",
  "enhancement_applied": true|false,
  "entities_added": ["entités ajoutées du contexte"],
  "enhancement_confidence": 0.0-1.0,
  "enhancement_reasoning": "explication des modifications ou pourquoi pas de modifications"
}}
```""",

            "entity_fusion": """Fusionne les entités UNIQUEMENT si la question actuelle contient des références contextuelles explicites.

ENTITÉS ACTUELLES (QUESTION ACTUELLE):
{current_entities}

ENTITÉS CONTEXTUELLES (CONVERSATION PRÉCÉDENTE):
{context_entities}

RÉFÉRENCES DÉTECTÉES: {references_detected}

⚠️ RÈGLES DE FUSION ULTRA-STRICTES:
1. **PAS DE FUSION SI PAS DE RÉFÉRENCES**: Si references_detected = false, retourner entités actuelles inchangées
2. **PRIORITÉ ABSOLUE AUX ENTITÉS ACTUELLES**: Toujours garder les entités de la question actuelle
3. **HÉRITAGE CONDITIONNEL**: Hériter du contexte SEULEMENT si:
   - L'entité actuelle est null/vide ET
   - Il y a une référence contextuelle explicite ET  
   - L'héritage est logiquement cohérent

⛔ INTERDICTIONS ABSOLUES:
- ❌ "Ross 308 male" + Contexte[age: 11] → N'ajouter AUCUN âge
- ❌ "Poulet 21 jours" + Contexte[breed: Cobb] → N'ajouter AUCUNE race
- ❌ Question autonome → AUCUNE fusion contextuelle

✅ CAS VALIDES POUR HÉRITAGE:
- "Leur poids ?" + Contexte[Ross 308, 21j] → Hérite race ET âge (référence "leur")
- "Et les femelles ?" + Contexte[Cobb 500] → Hérite race (référence explicite sexe opposé)
- "À cet âge ?" + Contexte[age: 14] → Hérite âge (référence temporelle explicite)

LOGIQUE DE DÉCISION:
```
SI references_detected == false:
    RETOURNER entités_actuelles inchangées
SINON:
    POUR chaque entité:
        SI entité_actuelle présente:
            GARDER entité_actuelle
        SINON SI entité_actuelle vide ET référence_contextuelle_explicite:
            HÉRITER du contexte
        SINON:
            LAISSER null
```

Réponds en JSON:
```json
{{
  "fusion_decision": "no_fusion"|"inheritance_applied"|"entities_preserved",
  "merged_entities": {{
    "age_days": number|null,
    "breed_specific": "breed"|null,
    "sex": "male"|"female"|"mixed"|null,
    "context_type": "performance"|"santé"|"alimentation",
    "weight_mentioned": true|false
  }},
  "inherited_from_context": ["liste des entités héritées avec justification"],
  "fusion_confidence": 0.0-1.0,
  "fusion_reasoning": "explication DÉTAILLÉE de chaque décision de fusion/non-fusion"
}}
```""",

            "rag_optimization": """Optimise cette question pour la recherche documentaire RAG dans une base avicole.

QUESTION ENHANCED: "{enhanced_question}"
ENTITÉS FUSIONNÉES: {merged_entities}

TÂCHE: Crée une requête de recherche optimisée en conservant la précision.

OPTIMISATIONS STANDARD:
1. **TERMINOLOGIE TECHNIQUE**: Utilise les termes spécialisés avicoles
2. **SYNONYMES PERTINENTS**: Ajoute variations courantes
3. **ÉQUILIBRE**: Balance spécificité et couverture de recherche
4. **STRUCTURE SÉMANTIQUE**: Organise pour matching optimal

⚡ OPTIMISATION PERFORMANCE:
- Limiter à 20-30 mots maximum
- Privilégier les termes les plus discriminants
- Éviter les mots vides ("le", "la", "des", "pour")

EXEMPLES:
- "Poids Ross 308 mâles 21 jours" → "poids standard broilers Ross 308 mâles trois semaines 21 jours croissance"
- "Diarrhée poules pondeuses" → "diarrhée troubles digestifs poules pondeuses santé intestinale symptômes"
- "Alimentation Cobb 500 démarrage" → "alimentation nutrition Cobb 500 démarrage starter feed première semaine"

Réponds en JSON:
```json
{{
  "rag_query": "requête optimisée concise",
  "key_terms": ["termes", "clés", "essentiels"],
  "synonyms_added": ["synonymes", "ajoutés"],
  "optimization_confidence": 0.0-1.0,
  "optimization_notes": "explication concise des optimisations"
}}
```""",

            "context_summary": """Crée un résumé concis du contexte conversationnel.

HISTORIQUE CONVERSATION:
{conversation_history}

ENTITÉS ÉTABLIES:
{established_entities}

TÂCHE: Résume l'essentiel en maximum 100 mots.

ÉLÉMENTS À INCLURE:
1. **SUJET PRINCIPAL**: Thème dominant de la conversation
2. **ENTITÉS RÉCURRENTES**: Race, âge, sexe mentionnés fréquemment
3. **TYPE DE QUESTIONS**: Pattern des demandes utilisateur
4. **NIVEAU TECHNIQUE**: Expertise apparente de l'utilisateur

Réponds en JSON:
```json
{{
  "conversation_topic": "sujet principal en 1-2 mots",
  "dominant_entities": {{
    "breed": "race principale discutée"|null,
    "typical_age": "âge typique"|null,
    "sex": "sexe typique"|null,
    "context_type": "type de questions dominant"
  }},
  "user_profile": {{
    "technical_level": "débutant"|"intermédiaire"|"expert",
    "focus_areas": ["domaines principaux"]
  }},
  "summary_confidence": 0.0-1.0
}}
```"""
        }
    
    def _is_standalone_question(self, question: str) -> bool:
        """✅ NOUVEAU: Détecte si une question est autonome (sans références contextuelles)"""
        
        question_stripped = question.strip()
        
        # 1. Vérification par patterns de questions autonomes
        for pattern in self.standalone_patterns:
            if re.match(pattern, question_stripped, re.IGNORECASE):
                logger.debug(f"🎯 [Standalone Detection] Pattern match: '{question_stripped}'")
                return True
        
        # 2. Vérification absence de mots contextuels
        question_lower = question_stripped.lower()
        
        # Recherche de tous les indicateurs contextuels
        contextual_found = []
        for category, words in self.contextual_indicators.items():
            for word in words:
                if word in question_lower:
                    contextual_found.append(f"{category}:{word}")
        
        # Si aucun mot contextuel trouvé, probablement autonome
        is_standalone = len(contextual_found) == 0
        
        # 3. Vérification longueur et complexité
        word_count = len(question_stripped.split())
        if word_count >= 6:  # Questions longues souvent autonomes
            is_standalone = is_standalone or True
        
        logger.debug(f"🔍 [Standalone Detection] '{question_stripped}': contextual={contextual_found}, standalone={is_standalone}")
        
        return is_standalone
    
    async def analyze_conversational_context(self, 
                                           current_question: str, 
                                           conversation_history: str,
                                           language: str = "fr") -> ContextAnalysis:
        """
        ✅ CORRIGÉ: Analyse contextuelle avec pré-filtrage strict
        """
        try:
            self.stats["total_enhancements"] += 1
            
            logger.info(f"🤖 [AI Context Enhancer] Analyse contextuelle: '{current_question[:50]}...'")
            
            # ✅ NOUVEAU: Pré-filtrage pour questions autonomes
            if self._is_standalone_question(current_question):
                self.stats["standalone_bypassed"] += 1
                logger.info("🚀 [Context Enhancer] Question autonome détectée - bypass analyse contextuelle")
                return ContextAnalysis(
                    references_detected=False,
                    enhanced_question=current_question,
                    confidence=0.95,
                    reasoning="Question autonome sans références contextuelles - analyse bypassed",
                    is_standalone=True
                )
            
            # ✅ NOUVEAU: Vérification contexte minimal requis
            if not conversation_history or len(conversation_history.strip()) < 20:
                logger.info("📭 [Context Enhancer] Contexte conversationnel insuffisant")
                return ContextAnalysis(
                    references_detected=False,
                    enhanced_question=current_question,
                    confidence=0.8,
                    reasoning="Contexte conversationnel insuffisant pour détecter des références"
                )
            
            # Analyse IA du contexte
            context_prompt = self.prompts["context_analysis"].format(
                current_question=current_question,
                conversation_context=conversation_history[-1500:]  # ✅ OPTIMISÉ: 2000 → 1500 pour performance
            )
            
            ai_response = await call_ai(
                service_type=AIServiceType.CONTEXT_ENHANCEMENT,
                prompt=context_prompt,
                model=self.models["context_analysis"],
                max_tokens=500,  # ✅ OPTIMISÉ: 600 → 500
                temperature=0.0,  # ✅ OPTIMISÉ: 0.1 → 0.0 pour maximum précision
                timeout=self.timeouts["context_analysis"]
            )
            
            # Parser le résultat avec validation
            analysis_data = self._parse_json_response(ai_response.content, "context_analysis")
            
            # ✅ NOUVEAU: Validation de cohérence
            references_detected = analysis_data.get("references_detected", False)
            is_standalone = analysis_data.get("is_standalone_question", False)
            
            # Cohérence logique
            if references_detected and is_standalone:
                logger.warning("⚠️ [Context Analysis] Incohérence détectée - question autonome avec références")
                references_detected = False  # Privilégier autonome
            
            # Construire ContextAnalysis
            analysis = ContextAnalysis(
                references_detected=references_detected,
                enhanced_question=current_question,  # Sera enrichie plus tard si nécessaire
                context_entities=analysis_data.get("referenced_entities", {}),
                missing_context=analysis_data.get("missing_context", []),
                confidence=analysis_data.get("confidence", 0.0),
                reasoning=analysis_data.get("analysis_reasoning", ""),
                is_standalone=is_standalone
            )
            
            logger.info(f"✅ [AI Context Enhancer] Analyse terminée: références={analysis.references_detected}, autonome={analysis.is_standalone}, confiance={analysis.confidence:.2f}")
            
            return analysis
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ [AI Context Enhancer] Erreur analyse contextuelle: {e}")
            # Fallback conservateur
            return ContextAnalysis(
                references_detected=False,
                enhanced_question=current_question,
                confidence=0.0,
                reasoning=f"Erreur analyse: {e}"
            )
    
    async def enhance_question_for_rag(self, 
                                     original_question: str,
                                     conversation_context: str = "",
                                     current_entities: Dict[str, Any] = None,
                                     language: str = "fr") -> EnhancedContext:
        """
        ✅ CORRIGÉ: Point d'entrée principal avec logique de fusion stricte
        """
        try:
            logger.info(f"🤖 [AI Context Enhancer] Enhancement complet: '{original_question[:50]}...'")
            
            if current_entities is None:
                current_entities = {}
            
            # 1. Analyser le contexte conversationnel avec pré-filtrage
            context_analysis = await self.analyze_conversational_context(
                original_question, conversation_context, language
            )
            
            # 2. Initialisation avec valeurs par défaut (pas de fusion)
            enhanced_question = original_question
            merged_entities = current_entities.copy()
            fusion_applied = False
            inheritance_log = []
            
            # 3. Enhancement ET fusion SEULEMENT si références détectées
            if context_analysis.references_detected and not context_analysis.is_standalone:
                
                # Enhancement de la question
                try:
                    enhanced_question = await self._enhance_question_with_context(
                        original_question, context_analysis.context_entities, True
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [Question Enhancement] Erreur: {e} - question originale conservée")
                    enhanced_question = original_question
                
                # Fusion des entités avec validation stricte
                try:
                    fusion_result = await self._merge_entities_with_context_strict(
                        current_entities, 
                        context_analysis.context_entities, 
                        context_analysis.references_detected
                    )
                    merged_entities = fusion_result["merged_entities"]
                    fusion_applied = fusion_result["fusion_applied"]
                    inheritance_log = fusion_result["inheritance_log"]
                    
                    if fusion_applied:
                        self.stats["context_fusions"] += 1
                        self.stats["inheritance_applied"] += len(inheritance_log)
                    
                except Exception as e:
                    logger.warning(f"⚠️ [Entity Fusion] Erreur: {e} - entités actuelles conservées")
                    merged_entities = current_entities.copy()
            
            else:
                logger.info(f"🚫 [Enhancement] Pas de références contextuelles - pas de fusion appliquée")
            
            # 4. Optimiser pour RAG
            rag_query = original_question  # Défaut sûr
            try:
                rag_query = await self._optimize_for_rag(enhanced_question, merged_entities)
            except Exception as e:
                logger.warning(f"⚠️ [RAG Optimization] Erreur: {e} - question originale utilisée")
            
            # 5. Créer le résumé contextuel
            context_summary = "Pas de contexte conversationnel"
            try:
                context_summary = await self._create_context_summary(
                    conversation_context, merged_entities
                )
            except Exception as e:
                logger.warning(f"⚠️ [Context Summary] Erreur: {e}")
            
            # 6. Construire résultat final avec logs détaillés
            enhanced_context = EnhancedContext(
                original_question=original_question,
                enhanced_question=enhanced_question,
                merged_entities=merged_entities,
                rag_optimized_query=rag_query,
                context_summary=context_summary,
                enhancement_confidence=context_analysis.confidence,
                ai_reasoning=context_analysis.reasoning,
                fusion_applied=fusion_applied,
                inheritance_log=inheritance_log
            )
            
            # Logging détaillé pour debugging
            logger.info(f"✅ [AI Context Enhancer] Enhancement terminé:")
            logger.info(f"   📝 Question enrichie: '{enhanced_question}'")
            logger.info(f"   🔗 Fusion appliquée: {fusion_applied}")
            logger.info(f"   📊 Entités finales: {len(merged_entities)} champs")
            if inheritance_log:
                logger.info(f"   🏷️ Héritages: {inheritance_log}")
            
            return enhanced_context
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ [AI Context Enhancer] Erreur enhancement: {e}")
            
            # Fallback ultra-conservateur
            return EnhancedContext(
                original_question=original_question,
                enhanced_question=original_question,
                merged_entities=current_entities or {},
                rag_optimized_query=original_question,
                context_summary="Erreur enhancement contextuel",
                enhancement_confidence=0.0,
                ai_reasoning=f"Erreur: {e}",
                fusion_applied=False,
                inheritance_log=[]
            )
    
    async def _enhance_question_with_context(self, 
                                           original_question: str, 
                                           context_entities: Dict[str, Any],
                                           references_detected: bool) -> str:
        """✅ CORRIGÉ: Enhancement conditionnel de la question"""
        
        try:
            # Si pas de références, pas d'enhancement
            if not references_detected:
                logger.debug("🚫 [Question Enhancement] Pas de références - pas d'enhancement")
                return original_question
            
            prompt = self.prompts["question_enhancement"].format(
                original_question=original_question,
                context_entities=json.dumps(context_entities, ensure_ascii=False),
                references_detected=references_detected
            )
            
            ai_response = await call_ai(
                service_type=AIServiceType.CONTEXT_ENHANCEMENT,
                prompt=prompt,
                model=self.models["question_enhancement"],
                max_tokens=300,  # ✅ OPTIMISÉ: 400 → 300
                temperature=0.0,  # ✅ OPTIMISÉ: 0.1 → 0.0
                timeout=self.timeouts["question_enhancement"]
            )
            
            result = self._parse_json_response(ai_response.content, "question_enhancement")
            enhancement_applied = result.get("enhancement_applied", False)
            enhanced = result.get("enhanced_question", original_question)
            
            # Validation: ne pas accepter d'enhancement si pas justifié
            if not enhancement_applied:
                enhanced = original_question
                logger.debug("🚫 [Question Enhancement] IA indique pas d'enhancement nécessaire")
            
            logger.info(f"✅ [Question Enhancement] '{original_question}' → '{enhanced}' (applied: {enhancement_applied})")
            return enhanced
            
        except Exception as e:
            logger.warning(f"⚠️ [Question Enhancement] Erreur: {e}")
            return original_question
    
    async def _merge_entities_with_context_strict(self, 
                                                current_entities: Dict[str, Any], 
                                                context_entities: Dict[str, Any],
                                                references_detected: bool) -> Dict[str, Any]:
        """✅ NOUVEAU: Fusion stricte avec validation et logging détaillé"""
        
        try:
            # Si pas de références détectées, pas de fusion
            if not references_detected:
                logger.info("🚫 [Entity Fusion] Pas de références contextuelles - pas de fusion")
                return {
                    "merged_entities": current_entities.copy(),
                    "fusion_applied": False,
                    "inheritance_log": []
                }
            
            prompt = self.prompts["entity_fusion"].format(
                current_entities=json.dumps(current_entities, ensure_ascii=False),
                context_entities=json.dumps(context_entities, ensure_ascii=False),
                references_detected=references_detected
            )
            
            ai_response = await call_ai(
                service_type=AIServiceType.CONTEXT_ENHANCEMENT,
                prompt=prompt,
                model=self.models["entity_fusion"],
                max_tokens=400,  # ✅ OPTIMISÉ: 500 → 400
                temperature=0.0,  # ✅ OPTIMISÉ: Maximum précision
                timeout=self.timeouts["entity_fusion"]
            )
            
            result = self._parse_json_response(ai_response.content, "entity_fusion")
            
            # Extraction des résultats
            fusion_decision = result.get("fusion_decision", "no_fusion")
            merged_entities = result.get("merged_entities", current_entities)
            inherited_list = result.get("inherited_from_context", [])
            fusion_reasoning = result.get("fusion_reasoning", "")
            
            # ✅ NOUVEAU: Validation post-fusion stricte
            validated_result = self._validate_entity_fusion_strict(
                original_current=current_entities,
                merged_result=merged_entities,
                inherited_list=inherited_list,
                fusion_reasoning=fusion_reasoning,
                references_detected=references_detected
            )
            
            fusion_applied = validated_result["validation_passed"]
            final_entities = validated_result["final_entities"]
            inheritance_log = validated_result["inheritance_log"]
            
            # Statistiques
            if fusion_applied:
                logger.info(f"✅ [Entity Fusion] Fusion appliquée avec {len(inheritance_log)} héritages")
            else:
                self.stats["inheritance_rejected"] += len(inherited_list)
                logger.info(f"🚫 [Entity Fusion] Fusion rejetée par validation stricte")
            
            return {
                "merged_entities": final_entities,
                "fusion_applied": fusion_applied,
                "inheritance_log": inheritance_log
            }
            
        except Exception as e:
            logger.warning(f"⚠️ [Entity Fusion] Erreur: {e}")
            # Fallback ultra-conservateur
            return {
                "merged_entities": current_entities.copy(),
                "fusion_applied": False,
                "inheritance_log": []
            }
    
    def _validate_entity_fusion_strict(self, 
                                     original_current: Dict[str, Any],
                                     merged_result: Dict[str, Any],
                                     inherited_list: List[str],
                                     fusion_reasoning: str,
                                     references_detected: bool) -> Dict[str, Any]:
        """✅ NOUVEAU: Validation ultra-stricte de la fusion d'entités"""
        
        # Si pas de références, refuse toute fusion
        if not references_detected:
            return {
                "validation_passed": False,
                "final_entities": original_current.copy(),
                "inheritance_log": [],
                "rejection_reason": "Pas de références contextuelles détectées"
            }
        
        validated_entities = original_current.copy()
        valid_inheritances = []
        rejected_inheritances = []
        
        # Valider chaque entité potentiellement héritée
        for inheritance_claim in inherited_list:
            if ":" in inheritance_claim:
                entity_key = inheritance_claim.split(":")[0].strip()
            else:
                entity_key = inheritance_claim.strip()
            
            # Vérifier si l'héritage est justifié
            is_valid = self._is_inheritance_justified_strict(
                entity_key, 
                merged_result.get(entity_key), 
                fusion_reasoning,
                original_current
            )
            
            if is_valid:
                validated_entities[entity_key] = merged_result.get(entity_key)
                valid_inheritances.append(f"{entity_key}: {merged_result.get(entity_key)}")
                logger.debug(f"✅ [Inheritance Validation] Accepté: {entity_key}")
            else:
                # Conserver la valeur originale (ou null)
                validated_entities[entity_key] = original_current.get(entity_key)
                rejected_inheritances.append(f"{entity_key}: rejeté")
                logger.debug(f"❌ [Inheritance Validation] Rejeté: {entity_key}")
        
        validation_passed = len(valid_inheritances) > 0
        
        # Log détaillé des décisions
        if valid_inheritances:
            logger.info(f"✅ [Fusion Validation] Héritages acceptés: {valid_inheritances}")
        if rejected_inheritances:
            logger.info(f"❌ [Fusion Validation] Héritages rejetés: {rejected_inheritances}")
        
        return {
            "validation_passed": validation_passed,
            "final_entities": validated_entities,
            "inheritance_log": valid_inheritances,
            "rejection_reason": f"Validations: {len(valid_inheritances)}/{len(inherited_list)}"
        }
    
    def _is_inheritance_justified_strict(self, 
                                       entity_key: str, 
                                       inherited_value: Any, 
                                       reasoning: str,
                                       original_entities: Dict[str, Any]) -> bool:
        """✅ NOUVEAU: Validation ultra-stricte de justification d'héritage"""
        
        # L'entité originale doit être vide pour justifier l'héritage
        original_value = original_entities.get(entity_key)
        if original_value is not None and original_value != "":
            logger.debug(f"❌ [Inheritance Check] {entity_key}: entité originale présente, pas d'héritage")
            return False
        
        # La valeur héritée doit être valide
        if inherited_value is None or inherited_value == "":
            logger.debug(f"❌ [Inheritance Check] {entity_key}: valeur héritée invalide")
            return False
        
        # Le raisonnement doit contenir des justifications contextuelles explicites
        reasoning_lower = reasoning.lower()
        
        # Indicateurs spécifiques par type d'entité
        justification_patterns = {
            "age": ["âge", "temporel", "à cet âge", "même âge", "age", "temporal"],
            "age_days": ["âge", "temporel", "jours", "à cet âge", "days", "temporal"],
            "breed": ["race", "breed", "leur", "ces animaux", "cette race", "même race"],
            "breed_specific": ["race", "breed", "leur", "ces animaux", "cette race", "souche"],
            "sex": ["sexe", "mâle", "femelle", "leur", "sex", "male", "female", "opposé"],
        }
        
        patterns = justification_patterns.get(entity_key, ["référence", "contextuel", "leur", "ces"])
        
        # Vérifier présence de justifications
        justifications_found = [pattern for pattern in patterns if pattern in reasoning_lower]
        
        # Au moins une justification requise
        is_justified = len(justifications_found) > 0
        
        logger.debug(f"🔍 [Inheritance Check] {entity_key}={inherited_value}: justifications={justifications_found}, valide={is_justified}")
        
        return is_justified
    
    async def _optimize_for_rag(self, enhanced_question: str, merged_entities: Dict[str, Any]) -> str:
        """✅ OPTIMISÉ: Optimisation RAG avec performance améliorée"""
        
        try:
            prompt = self.prompts["rag_optimization"].format(
                enhanced_question=enhanced_question,
                merged_entities=json.dumps(merged_entities, ensure_ascii=False, indent=None)  # ✅ OPTIMISÉ: Pas d'indentation
            )
            
            ai_response = await call_ai(
                service_type=AIServiceType.CONTEXT_ENHANCEMENT,
                prompt=prompt,
                model=self.models["rag_optimization"],
                max_tokens=200,  # ✅ OPTIMISÉ: 300 → 200
                temperature=0.1,
                timeout=self.timeouts["rag_optimization"]
            )
            
            result = self._parse_json_response(ai_response.content, "rag_optimization")
            rag_query = result.get("rag_query", enhanced_question)
            
            # ✅ NOUVEAU: Validation longueur
            if len(rag_query.split()) > 25:  # Limite pour performance
                rag_query = " ".join(rag_query.split()[:25]) + "..."
                logger.debug("✂️ [RAG Optimization] Query tronquée pour performance")
            
            logger.info(f"✅ [RAG Optimization] Query optimisée: '{rag_query}'")
            return rag_query
            
        except Exception as e:
            logger.warning(f"⚠️ [RAG Optimization] Erreur: {e}")
            return enhanced_question
    
    async def _create_context_summary(self, conversation_history: str, entities: Dict[str, Any]) -> str:
        """✅ OPTIMISÉ: Résumé contextuel avec bypass intelligent"""
        
        try:
            # ✅ NOUVEAU: Bypass si contexte minimal
            if not conversation_history or len(conversation_history.strip()) < 30:
                return "Nouvelle conversation - pas d'historique établi"
            
            # Limiter la taille pour performance
            history_limited = conversation_history[-800:]  # ✅ OPTIMISÉ: 1000 → 800
            
            prompt = self.prompts["context_summary"].format(
                conversation_history=history_limited,
                established_entities=json.dumps(entities, ensure_ascii=False, indent=None)
            )
            
            ai_response = await call_ai(
                service_type=AIServiceType.CONTEXT_ENHANCEMENT,
                prompt=prompt,
                model="gpt-3.5-turbo",  # ✅ OPTIMISÉ: Suffisant pour résumé
                max_tokens=150,  # ✅ OPTIMISÉ: 300 → 150
                temperature=0.2,
                timeout=5  # ✅ OPTIMISÉ: Timeout court
            )
            
            result = self._parse_json_response(ai_response.content, "context_summary")
            topic = result.get("conversation_topic", "Discussion générale")
            dominant_entities = result.get("dominant_entities", {})
            
            # Format concis
            summary_parts = [f"Sujet: {topic}"]
            if dominant_entities.get("breed"):
                summary_parts.append(f"Race: {dominant_entities['breed']}")
            if dominant_entities.get("typical_age"):
                summary_parts.append(f"Âge: {dominant_entities['typical_age']}")
            
            summary = " | ".join(summary_parts)
            return summary
            
        except Exception as e:
            logger.warning(f"⚠️ [Context Summary] Erreur: {e}")
            return "Résumé contextuel indisponible"
    
    def _parse_json_response(self, content: str, operation: str = "unknown") -> Dict[str, Any]:
        """✅ AMÉLIORÉ: Parse JSON avec gestion d'erreurs et fallbacks par opération"""
        
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
            logger.warning(f"⚠️ [AI Context Enhancer] Erreur parsing JSON ({operation}): {e}")
            
            # Fallbacks spécifiques par opération
            fallback_responses = {
                "context_analysis": {
                    "references_detected": False,
                    "is_standalone_question": True,
                    "confidence": 0.0,
                    "analysis_reasoning": "Erreur parsing - fallback conservateur"
                },
                "question_enhancement": {
                    "enhanced_question": "",  # Sera remplacé par question originale
                    "enhancement_applied": False,
                    "enhancement_confidence": 0.0
                },
                "entity_fusion": {
                    "fusion_decision": "no_fusion",
                    "merged_entities": {},  # Sera remplacé par entités actuelles
                    "inherited_from_context": [],
                    "fusion_confidence": 0.0
                },
                "rag_optimization": {
                    "rag_query": "",  # Sera remplacé par question originale
                    "optimization_confidence": 0.0
                },
                "context_summary": {
                    "conversation_topic": "Erreur parsing",
                    "summary_confidence": 0.0
                }
            }
            
            return fallback_responses.get(operation, {})
            
        except Exception as e:
            logger.error(f"❌ [AI Context Enhancer] Erreur parsing ({operation}): {e}")
            return {}
    
    async def enhance_for_classification(self, 
                                       question: str, 
                                       conversation_context: str = "") -> Dict[str, Any]:
        """✅ OPTIMISÉ: Enhancement spécialisé pour classification"""
        
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
                "fusion_applied": enhanced_context.fusion_applied,
                "classification_hints": {
                    "likely_contextual": enhanced_context.enhancement_confidence > 0.7,
                    "needs_clarification": enhanced_context.enhancement_confidence < 0.3 and not enhanced_context.fusion_applied,
                    "has_sufficient_context": len(enhanced_context.merged_entities) >= 2,
                    "is_standalone": enhanced_context.enhancement_confidence == 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [AI Context Enhancer] Erreur classification enhancement: {e}")
            return {
                "enhanced_question": question,
                "context_confidence": 0.0,
                "has_references": False,
                "merged_entities": {},
                "fusion_applied": False,
                "classification_hints": {
                    "likely_contextual": False,
                    "needs_clarification": True,
                    "has_sufficient_context": False,
                    "is_standalone": True
                }
            }
    
    def get_enhancement_stats(self) -> Dict[str, Any]:
        """✅ NOUVEAU: Statistiques de performance pour monitoring"""
        
        total = self.stats["total_enhancements"]
        bypass_rate = (self.stats["standalone_bypassed"] / total * 100) if total > 0 else 0
        fusion_rate = (self.stats["context_fusions"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "bypass_rate_percent": round(bypass_rate, 1),
            "fusion_rate_percent": round(fusion_rate, 1),
            "error_rate_percent": round((self.stats["errors"] / total * 100) if total > 0 else 0, 1)
        }

# =============================================================================
# INSTANCES GLOBALES ET FACTORY FUNCTIONS
# =============================================================================

# Instance globale pour réutilisation
_ai_context_enhancer_instance = None

def get_ai_context_enhancer() -> AIContextEnhancer:
    """Factory function pour récupérer l'instance singleton"""
    global _ai_context_enhancer_instance
    
    if _ai_context_enhancer_instance is None:
        _ai_context_enhancer_instance = AIContextEnhancer()
        logger.info("🤖 [AI Context Enhancer] Instance singleton créée")
    
    return _ai_context_enhancer_instance

# =============================================================================
# FONCTIONS DE COMPATIBILITÉ AVEC L'ANCIEN SYSTÈME  
# =============================================================================

async def enhance_question_for_rag_legacy(question: str, context: str = "") -> str:
    """
    ✅ MAINTENU: Fonction de compatibilité avec l'ancien système RAG
    """
    try:
        enhancer = get_ai_context_enhancer()
        enhanced_context = await enhancer.enhance_question_for_rag(
            original_question=question,
            conversation_context=context
        )
        return enhanced_context.rag_optimized_query
        
    except Exception as e:
        logger.warning(f"⚠️ [Legacy RAG Enhancement] Erreur: {e}")
        return question

async def analyze_contextual_references_legacy(question: str, history: str = "") -> Dict[str, Any]:
    """
    ✅ MAINTENU: Fonction de compatibilité pour l'analyse des références contextuelles
    """
    try:
        enhancer = get_ai_context_enhancer()
        analysis = await enhancer.analyze_conversational_context(
            current_question=question,
            conversation_history=history
        )
        
        return {
            "has_references": analysis.references_detected,
            "referenced_entities": analysis.context_entities,
            "confidence": analysis.confidence,
            "missing_context": analysis.missing_context,
            "reasoning": analysis.reasoning,
            "is_standalone": analysis.is_standalone  # ✅ NOUVEAU
        }
        
    except Exception as e:
        logger.warning(f"⚠️ [Legacy Context Analysis] Erreur: {e}")
        return {
            "has_references": False,
            "referenced_entities": {},
            "confidence": 0.0,
            "missing_context": [],
            "reasoning": f"Erreur: {e}",
            "is_standalone": True
        }

# =============================================================================
# TESTS ET VALIDATION
# =============================================================================

async def test_ai_context_enhancer():
    """✅ AMÉLIORÉ: Tests intégrés pour valider le fonctionnement"""
    
    logger.info("🧪 Tests AI Context Enhancer - Version Corrigée")
    logger.info("=" * 60)
    
    enhancer = get_ai_context_enhancer()
    
    test_cases = [
        {
            "name": "Question autonome - pas de fusion",
            "question": "Ross 308 male",
            "context": "Conversation précédente: poulet 11 jours, poids",
            "expected_fusion": False,
            "expected_standalone": True
        },
        {
            "name": "Question avec références - fusion attendue",
            "question": "Leur poids à 21 jours ?",
            "context": "Conversation précédente: Ross 308 mâles, problèmes de croissance",
            "expected_fusion": True,
            "expected_standalone": False
        },
        {
            "name": "Question complète - pas de fusion",
            "question": "Quel est le poids normal des Cobb 500 à 14 jours ?",
            "context": "Discussion précédente sur Ross 308",
            "expected_fusion": False,
            "expected_standalone": True
        },
        {
            "name": "Référence explicite - fusion attendue",
            "question": "Et pour les femelles ?",
            "context": "Discussion sur les mâles Cobb 500 de 14 jours",
            "expected_fusion": True,
            "expected_standalone": False
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        try:
            logger.info(f"\n🧪 Test {i}: {case['name']}")
            logger.info(f"   📝 Question: '{case['question']}'")
            
            enhanced_context = await enhancer.enhance_question_for_rag(
                original_question=case["question"],
                conversation_context=case["context"]
            )
            
            # Vérifications
            fusion_applied = enhanced_context.fusion_applied
            is_standalone = case["question"] == enhanced_context.enhanced_question and not fusion_applied
            
            # Résultats
            fusion_correct = fusion_applied == case["expected_fusion"]
            standalone_correct = is_standalone == case["expected_standalone"]
            
            result = {
                "test": case["name"],
                "fusion_applied": fusion_applied,
                "fusion_correct": fusion_correct,
                "standalone_detected": is_standalone,
                "standalone_correct": standalone_correct,
                "success": fusion_correct and standalone_correct
            }
            
            results.append(result)
            
            # Logs détaillés
            logger.info(f"   ✅ Question enrichie: '{enhanced_context.enhanced_question}'")
            logger.info(f"   ✅ Fusion appliquée: {fusion_applied} (attendu: {case['expected_fusion']}) {'✅' if fusion_correct else '❌'}")
            logger.info(f"   ✅ Autonome détecté: {is_standalone} (attendu: {case['expected_standalone']}) {'✅' if standalone_correct else '❌'}")
            logger.info(f"   ✅ Confiance: {enhanced_context.enhancement_confidence:.2f}")
            logger.info(f"   ✅ Entités finales: {len(enhanced_context.merged_entities)} champs")
            if enhanced_context.inheritance_log:
                logger.info(f"   🏷️ Héritages: {enhanced_context.inheritance_log}")
            
            logger.info(f"   {'✅ SUCCÈS' if result['success'] else '❌ ÉCHEC'}")
            
        except Exception as e:
            logger.error(f"   ❌ Erreur test {i}: {e}")
            results.append({"test": case["name"], "success": False, "error": str(e)})
    
    # Résumé des tests
    logger.info(f"\n📊 Résumé des tests:")
    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    logger.info(f"   ✅ Réussis: {successful}/{total}")
    
    if successful == total:
        logger.info("   🎉 TOUS LES TESTS RÉUSSIS - Corrections validées!")
    else:
        logger.warning("   ⚠️ Certains tests ont échoué - Révision nécessaire")
    
    # Statistiques de performance
    stats = enhancer.get_enhancement_stats()
    logger.info(f"\n📈 Statistiques performance:")
    for key, value in stats.items():
        logger.info(f"   {key}: {value}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_context_enhancer())