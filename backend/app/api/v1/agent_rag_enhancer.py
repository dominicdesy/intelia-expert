# app/api/v1/agent_rag_enhancer.py
"""
Agent RAG Enhancer - Amélioration des réponses après RAG

🎯 FONCTIONNALITÉS:
- Adapte les réponses RAG selon le contexte utilisateur
- Vérifie la cohérence entre question enrichie et réponse RAG
- Ajoute des avertissements si informations manquantes
- Propose des clarifications optionnelles
- Améliore la lisibilité et la pertinence
"""

import os
import logging
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import OpenAI sécurisé
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

logger = logging.getLogger(__name__)

class AgentRAGEnhancer:
    """Agent intelligent pour améliorer les réponses RAG"""
    
    def __init__(self):
        self.openai_available = OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('RAG_ENHANCER_MODEL', 'gpt-4o-mini')
        self.timeout = int(os.getenv('RAG_ENHANCER_TIMEOUT', '15'))
        self.max_retries = int(os.getenv('RAG_ENHANCER_RETRIES', '2'))
        
        # Statistiques
        self.stats = {
            "total_requests": 0,
            "openai_success": 0,
            "openai_failures": 0,
            "fallback_used": 0,
            "answers_enhanced": 0,
            "clarifications_generated": 0,
            "coherence_checks": 0,
            "coherence_issues_detected": 0
        }
        
        logger.info(f"🔧 [AgentRAGEnhancer] Initialisé")
        logger.info(f"   OpenAI disponible: {'✅' if self.openai_available else '❌'}")
        logger.info(f"   Modèle: {self.model}")
    
    async def enhance_rag_answer(
        self,
        rag_answer: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        conversation_context: str,
        original_question: str = "",
        enriched_question: str = "",  # 🆕 Question enrichie par le pré-RAG
        language: str = "fr"
    ) -> Dict[str, Any]:
        """
        Améliore une réponse RAG avec le contexte utilisateur et vérifie la cohérence
        
        Args:
            rag_answer: Réponse brute du système RAG
            entities: Entités extraites du contexte
            missing_entities: Entités manquantes critiques
            conversation_context: Contexte conversationnel
            original_question: Question originale posée
            enriched_question: Question enrichie par le pré-RAG 🆕
            language: Langue de la conversation
            
        Returns:
            {
                "enhanced_answer": "réponse améliorée",
                "optional_clarifications": ["question1", "question2"],
                "warnings": ["avertissement1"],
                "confidence_impact": "low/medium/high",
                "coherence_check": "good/partial/poor",  🆕
                "coherence_notes": "détails sur la cohérence",  🆕
                "method_used": "openai/fallback"
            }
        """
        
        self.stats["total_requests"] += 1
        self.stats["coherence_checks"] += 1
        
        try:
            # Tentative OpenAI si disponible
            if self.openai_available:
                result = await self._enhance_with_openai(
                    rag_answer, entities, missing_entities, conversation_context, 
                    original_question, enriched_question, language
                )
                if result["success"]:
                    self.stats["openai_success"] += 1
                    if result["enhanced_answer"] != rag_answer:
                        self.stats["answers_enhanced"] += 1
                    if result.get("optional_clarifications"):
                        self.stats["clarifications_generated"] += 1
                    if result.get("coherence_check") in ["partial", "poor"]:
                        self.stats["coherence_issues_detected"] += 1
                    return result
                else:
                    self.stats["openai_failures"] += 1
            
            # Fallback: Amélioration basique
            logger.info("🔄 [AgentRAGEnhancer] Utilisation fallback basique")
            result = self._enhance_fallback(
                rag_answer, entities, missing_entities, 
                original_question, enriched_question, language
            )
            self.stats["fallback_used"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [AgentRAGEnhancer] Erreur critique: {e}")
            return {
                "enhanced_answer": rag_answer,
                "optional_clarifications": [],
                "warnings": [f"Erreur amélioration: {str(e)}"],
                "confidence_impact": "unknown",
                "coherence_check": "unknown",
                "coherence_notes": "Impossible de vérifier la cohérence en raison d'une erreur",
                "method_used": "error_fallback",
                "success": False
            }
    
    async def _enhance_with_openai(
        self,
        rag_answer: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        conversation_context: str,
        original_question: str,
        enriched_question: str,  # 🆕
        language: str
    ) -> Dict[str, Any]:
        """Amélioration avec OpenAI GPT"""
        
        try:
            # Préparer le contexte pour GPT
            entities_summary = self._format_entities_for_gpt(entities)
            missing_summary = ", ".join(missing_entities) if missing_entities else "Aucune"
            
            # Prompt spécialisé selon la langue
            system_prompt = self._get_system_prompt(language)
            user_prompt = self._build_enhancement_prompt(
                rag_answer, entities_summary, missing_summary, conversation_context,
                original_question, enriched_question, language  # 🆕
            )
            
            # Appel OpenAI
            client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,  # Augmenté pour inclure la vérification de cohérence
                timeout=self.timeout
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Parser la réponse JSON
            result = self._parse_gpt_response(answer, rag_answer, entities, missing_entities)
            result["success"] = True
            result["method_used"] = "openai"
            
            logger.info(f"✅ [AgentRAGEnhancer] Amélioration OpenAI réussie")
            logger.debug(f"   Clarifications générées: {len(result.get('optional_clarifications', []))}")
            logger.debug(f"   Cohérence: {result.get('coherence_check', 'unknown')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [AgentRAGEnhancer] Erreur OpenAI: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_system_prompt(self, language: str) -> str:
        """Retourne le prompt système selon la langue"""
        
        system_prompts = {
            "fr": """Tu es un expert vétérinaire en aviculture spécialisé dans l'adaptation de réponses techniques.

Ta mission:
1. Vérifier la cohérence entre la question enrichie et la réponse RAG
2. Adapter la réponse RAG pour qu'elle soit pertinente malgré les informations manquantes
3. Ajouter des avertissements si l'absence de données affecte la précision
4. Proposer 1-3 questions de clarification pour améliorer le conseil
5. Garder un ton professionnel mais accessible
6. Prioriser la sécurité des animaux

VÉRIFICATION DE COHÉRENCE:
- "good": La réponse RAG correspond parfaitement à la question enrichie
- "partial": La réponse RAG est pertinente mais incomplète ou tangentielle
- "poor": La réponse RAG ne correspond pas bien à la question enrichie

IMPORTANT: 
- Si des informations critiques manquent, le mentionner clairement
- Si la réponse RAG semble hors-sujet, l'adapter ou le signaler
- Proposer des questions de clarification utiles, pas évidentes
- Éviter les conseils dangereux sans contexte complet
- Répondre UNIQUEMENT en JSON avec la structure exacte demandée""",
            
            "en": """You are a poultry veterinary expert specialized in adapting technical responses.

Your mission:
1. Verify coherence between enriched question and RAG response
2. Adapt the RAG response to be relevant despite missing information
3. Add warnings if missing data affects accuracy
4. Propose 1-3 clarification questions to improve advice
5. Keep professional but accessible tone
6. Prioritize animal safety

COHERENCE CHECK:
- "good": RAG response perfectly matches the enriched question
- "partial": RAG response is relevant but incomplete or tangential
- "poor": RAG response doesn't match well with the enriched question

IMPORTANT:
- If critical information is missing, mention it clearly
- If RAG response seems off-topic, adapt it or flag it
- Propose useful clarification questions, not obvious ones
- Avoid dangerous advice without complete context
- Respond ONLY in JSON with the exact requested structure""",
            
            "es": """Eres un experto veterinario en avicultura especializado en adaptar respuestas técnicas.

Tu misión:
1. Verificar la coherencia entre la pregunta enriquecida y la respuesta RAG
2. Adaptar la respuesta RAG para que sea relevante a pesar de la información faltante
3. Agregar advertencias si los datos faltantes afectan la precisión
4. Proponer 1-3 preguntas de aclaración para mejorar el consejo
5. Mantener tono profesional pero accesible
6. Priorizar la seguridad de los animales

VERIFICACIÓN DE COHERENCIA:
- "good": La respuesta RAG coincide perfectamente con la pregunta enriquecida
- "partial": La respuesta RAG es relevante pero incompleta o tangencial
- "poor": La respuesta RAG no coincide bien con la pregunta enriquecida

IMPORTANTE:
- Si falta información crítica, mencionarlo claramente
- Si la respuesta RAG parece fuera de tema, adaptarla o señalarlo
- Proponer preguntas de aclaración útiles, no obvias
- Evitar consejos peligrosos sin contexto completo
- Responder SOLO en JSON con la estructura exacta solicitada"""
        }
        
        return system_prompts.get(language, system_prompts["fr"])
    
    def _build_enhancement_prompt(
        self,
        rag_answer: str,
        entities_summary: str,
        missing_summary: str,
        conversation_context: str,
        original_question: str,
        enriched_question: str,  # 🆕
        language: str
    ) -> str:
        """Construit le prompt d'amélioration avec vérification de cohérence"""
        
        if language == "fr":
            return f"""QUESTION ORIGINALE: "{original_question}"

QUESTION ENRICHIE (générée par le pré-RAG): "{enriched_question}"

RÉPONSE RAG BRUTE:
"{rag_answer}"

ENTITÉS CONNUES:
{entities_summary}

ENTITÉS MANQUANTES CRITIQUES: {missing_summary}

CONTEXTE CONVERSATIONNEL:
{conversation_context}

INSTRUCTIONS:
1. COHÉRENCE: Compare la question enrichie avec la réponse RAG. La réponse traite-t-elle bien le sujet de la question enrichie ?
2. Adapte la réponse pour le contexte spécifique de l'utilisateur
3. Si des informations critiques manquent, ajoute un avertissement et explique l'impact
4. Si la réponse RAG ne correspond pas bien à la question enrichie, corrige ou signale le problème
5. Améliore la lisibilité et la structure de la réponse
6. Propose 1-3 questions de clarification pertinentes (pas évidentes)
7. Garde la précision technique mais rends accessible

EXEMPLE VÉRIFICATION COHÉRENCE:
Question enrichie: "Évaluation poids poulet Ross 308, 21 jours, croissance normale ?"
Réponse RAG: "Les poulets doivent peser 800g à 3 semaines"
Cohérence: "partial" - répond au poids mais ignore la race spécifique et l'évaluation de normalité

Réponds en JSON:
{{
  "enhanced_answer": "réponse adaptée et améliorée",
  "optional_clarifications": ["Question précise 1?", "Question précise 2?"],
  "warnings": ["Avertissement si info manquante impacte conseil"],
  "confidence_impact": "low/medium/high selon impact infos manquantes",
  "coherence_check": "good/partial/poor",
  "coherence_notes": "explication détaillée de la cohérence entre question enrichie et réponse RAG",
  "improvement_notes": "explications des améliorations apportées"
}}"""
        
        elif language == "en":
            return f"""ORIGINAL QUESTION: "{original_question}"

ENRICHED QUESTION (generated by pre-RAG): "{enriched_question}"

RAW RAG RESPONSE:
"{rag_answer}"

KNOWN ENTITIES:
{entities_summary}

MISSING CRITICAL ENTITIES: {missing_summary}

CONVERSATIONAL CONTEXT:
{conversation_context}

INSTRUCTIONS:
1. COHERENCE: Compare enriched question with RAG response. Does the response properly address the enriched question's topic?
2. Adapt response for user's specific context
3. If critical information missing, add warning and explain impact
4. If RAG response doesn't match well with enriched question, correct or flag the issue
5. Improve readability and structure of response
6. Propose 1-3 relevant clarification questions (not obvious ones)
7. Keep technical accuracy but make accessible

EXAMPLE COHERENCE CHECK:
Enriched question: "Ross 308 chicken weight evaluation, 21 days, normal growth?"
RAG response: "Chickens should weigh 800g at 3 weeks"
Coherence: "partial" - addresses weight but ignores specific breed and normality evaluation

Respond in JSON:
{{
  "enhanced_answer": "adapted and improved response",
  "optional_clarifications": ["Specific question 1?", "Specific question 2?"],
  "warnings": ["Warning if missing info impacts advice"],
  "confidence_impact": "low/medium/high based on missing info impact",
  "coherence_check": "good/partial/poor",
  "coherence_notes": "detailed explanation of coherence between enriched question and RAG response",
  "improvement_notes": "explanations of improvements made"
}}"""
        
        else:  # Spanish
            return f"""PREGUNTA ORIGINAL: "{original_question}"

PREGUNTA ENRIQUECIDA (generada por pre-RAG): "{enriched_question}"

RESPUESTA RAG BRUTA:
"{rag_answer}"

ENTIDADES CONOCIDAS:
{entities_summary}

ENTIDADES CRÍTICAS FALTANTES: {missing_summary}

CONTEXTO CONVERSACIONAL:
{conversation_context}

INSTRUCCIONES:
1. COHERENCIA: Compara la pregunta enriquecida con la respuesta RAG. ¿La respuesta aborda adecuadamente el tema de la pregunta enriquecida?
2. Adapta la respuesta para el contexto específico del usuario
3. Si falta información crítica, agrega advertencia y explica el impacto
4. Si la respuesta RAG no coincide bien con la pregunta enriquecida, corrige o señala el problema
5. Mejora la legibilidad y estructura de la respuesta
6. Propone 1-3 preguntas de aclaración relevantes (no obvias)
7. Mantén precisión técnica pero hazla accesible

EJEMPLO VERIFICACIÓN COHERENCIA:
Pregunta enriquecida: "Evaluación peso pollo Ross 308, 21 días, crecimiento normal?"
Respuesta RAG: "Los pollos deben pesar 800g a las 3 semanas"
Coherencia: "partial" - aborda el peso pero ignora la raza específica y evaluación de normalidad

Responde en JSON:
{{
  "enhanced_answer": "respuesta adaptada y mejorada",
  "optional_clarifications": ["Pregunta específica 1?", "Pregunta específica 2?"],
  "warnings": ["Advertencia si info faltante impacta consejo"],
  "confidence_impact": "low/medium/high según impacto info faltante",
  "coherence_check": "good/partial/poor",
  "coherence_notes": "explicación detallada de la coherencia entre pregunta enriquecida y respuesta RAG",
  "improvement_notes": "explicaciones de mejoras realizadas"
}}"""
    
    def _format_entities_for_gpt(self, entities: Dict[str, Any]) -> str:
        """Formate les entités pour le prompt GPT"""
        
        formatted_parts = []
        
        # Informations de base avec niveaux de confiance
        if entities.get("breed"):
            confidence = entities.get("breed_confidence", 0.0)
            status = "✅" if confidence > 0.7 else "⚠️" if confidence > 0.4 else "❌"
            formatted_parts.append(f"{status} Race: {entities['breed']} (confiance: {confidence:.1f})")
        else:
            formatted_parts.append("❌ Race: inconnue")
        
        if entities.get("sex"):
            confidence = entities.get("sex_confidence", 0.0)
            status = "✅" if confidence > 0.7 else "⚠️" if confidence > 0.4 else "❌"
            formatted_parts.append(f"{status} Sexe: {entities['sex']} (confiance: {confidence:.1f})")
        else:
            formatted_parts.append("❌ Sexe: inconnu")
        
        if entities.get("age_days"):
            confidence = entities.get("age_confidence", 0.0)
            status = "✅" if confidence > 0.7 else "⚠️" if confidence > 0.4 else "❌"
            weeks = entities.get("age_weeks", entities["age_days"] / 7)
            formatted_parts.append(f"{status} Âge: {entities['age_days']} jours ({weeks:.1f} semaines)")
        else:
            formatted_parts.append("❌ Âge: inconnu")
        
        # Performance et santé
        if entities.get("weight_grams"):
            confidence = entities.get("weight_confidence", 0.0)
            status = "✅" if confidence > 0.6 else "⚠️"
            formatted_parts.append(f"{status} Poids actuel: {entities['weight_grams']}g")
        
        if entities.get("symptoms"):
            symptoms = ", ".join(entities["symptoms"])
            formatted_parts.append(f"🚨 Symptômes observés: {symptoms}")
        
        if entities.get("mortality_rate") is not None:
            rate = entities["mortality_rate"]
            status = "🚨" if rate > 5 else "⚠️" if rate > 2 else "✅"
            formatted_parts.append(f"{status} Mortalité: {rate}%")
        
        # Environnement
        if entities.get("temperature"):
            temp = entities["temperature"]
            status = "🚨" if temp < 18 or temp > 30 else "✅"
            formatted_parts.append(f"{status} Température: {temp}°C")
        
        if entities.get("housing_type"):
            formatted_parts.append(f"🏠 Logement: {entities['housing_type']}")
        
        if entities.get("flock_size"):
            formatted_parts.append(f"👥 Taille troupeau: {entities['flock_size']}")
        
        return "\n".join(formatted_parts) if formatted_parts else "Aucune information contextuelle disponible"
    
    def _parse_gpt_response(
        self, 
        response: str, 
        original_answer: str, 
        entities: Dict[str, Any], 
        missing_entities: List[str]
    ) -> Dict[str, Any]:
        """Parse la réponse JSON de GPT avec vérification de cohérence"""
        
        try:
            # Extraire le JSON de la réponse
            json_match = None
            
            # Chercher JSON dans des blocs code
            import re
            json_patterns = [
                r'```json\s*(\{.*?\})\s*```',
                r'```\s*(\{.*?\})\s*```',
                r'(\{.*?\})'
            ]
            
            for pattern in json_patterns:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    json_match = match.group(1)
                    break
            
            if not json_match:
                raise ValueError("Pas de JSON trouvé dans la réponse")
            
            # Parser le JSON
            data = json.loads(json_match)
            
            # Valider et enrichir la réponse
            enhanced_answer = data.get("enhanced_answer", original_answer)
            optional_clarifications = data.get("optional_clarifications", [])
            warnings = data.get("warnings", [])
            
            # 🆕 Validation de la cohérence
            coherence_check = data.get("coherence_check", "unknown")
            if coherence_check not in ["good", "partial", "poor"]:
                coherence_check = "unknown"
            
            coherence_notes = data.get("coherence_notes", "")
            if not coherence_notes:
                coherence_notes = f"Cohérence évaluée comme: {coherence_check}"
            
            # Validation des clarifications (max 3, non vides)
            if isinstance(optional_clarifications, list):
                optional_clarifications = [q.strip() for q in optional_clarifications if q and q.strip()]
                optional_clarifications = optional_clarifications[:3]
            else:
                optional_clarifications = []
            
            # Validation des avertissements
            if isinstance(warnings, list):
                warnings = [w.strip() for w in warnings if w and w.strip()]
                warnings = warnings[:2]  # Max 2 avertissements
            else:
                warnings = []
            
            # Déterminer l'impact sur la confiance
            confidence_impact = data.get("confidence_impact", "medium")
            if confidence_impact not in ["low", "medium", "high"]:
                confidence_impact = "medium"
            
            result = {
                "enhanced_answer": enhanced_answer,
                "optional_clarifications": optional_clarifications,
                "warnings": warnings,
                "confidence_impact": confidence_impact,
                "coherence_check": coherence_check,  # 🆕
                "coherence_notes": coherence_notes,  # 🆕
                "improvement_notes": data.get("improvement_notes", "Améliorations appliquées"),
                "method_used": "openai",
                "processing_time": datetime.now().isoformat(),
                "entities_considered": len([k for k, v in entities.items() if v is not None]),
                "missing_entities_count": len(missing_entities)
            }
            
            return result
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"❌ [AgentRAGEnhancer] Erreur parsing JSON: {e}")
            logger.debug(f"   Réponse GPT: {response}")
            
            # Fallback: chercher des améliorations dans le texte brut
            if len(response) > len(original_answer) and response != original_answer:
                # Extraire des clarifications potentielles du texte
                clarifications = []
                question_patterns = [r'([^.!?]*\?)', r'pourriez-vous[^.!?]*\?', r'pouvez-vous[^.!?]*\?']
                
                for pattern in question_patterns:
                    matches = re.findall(pattern, response, re.IGNORECASE)
                    for match in matches[:2]:  # Max 2
                        if len(match.strip()) > 10:
                            clarifications.append(match.strip())
                
                return {
                    "enhanced_answer": response.strip(),
                    "optional_clarifications": clarifications,
                    "warnings": ["Réponse générée automatiquement - vérifiez la pertinence"],
                    "confidence_impact": "medium",
                    "coherence_check": "unknown",
                    "coherence_notes": "Impossible de vérifier la cohérence - JSON parsing échoué",
                    "improvement_notes": "JSON parsing failed, used raw GPT response",
                    "method_used": "openai_fallback"
                }
            else:
                # Fallback complet
                return self._enhance_fallback(original_answer, entities, missing_entities, "", "", "fr")
    
    def _enhance_fallback(
        self,
        rag_answer: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        original_question: str,
        enriched_question: str,  # 🆕
        language: str
    ) -> Dict[str, Any]:
        """Amélioration fallback sans OpenAI avec vérification basique de cohérence"""
        
        enhanced_answer = rag_answer
        warnings = []
        clarifications = []
        
        # 🆕 Vérification basique de cohérence
        coherence_check = "unknown"
        coherence_notes = "Vérification automatique basique"
        
        if enriched_question and original_question:
            # Vérification très basique par mots-clés
            enriched_words = set(enriched_question.lower().split())
            answer_words = set(rag_answer.lower().split())
            
            # Mots-clés importants communs
            important_words = enriched_words.intersection(answer_words)
            important_words = {w for w in important_words if len(w) > 3}  # Ignorer mots courts
            
            if len(important_words) >= 3:
                coherence_check = "good"
                coherence_notes = f"Réponse semble cohérente (mots-clés communs: {', '.join(list(important_words)[:3])})"
            elif len(important_words) >= 1:
                coherence_check = "partial"
                coherence_notes = f"Cohérence partielle (quelques mots-clés communs: {', '.join(important_words)})"
            else:
                coherence_check = "poor"
                coherence_notes = "Peu de mots-clés communs entre question enrichie et réponse"
        
        # Ajouter des avertissements selon les entités manquantes
        if "breed" in missing_entities:
            if language == "fr":
                warnings.append("⚠️ Sans connaître la race exacte, cette réponse est générale. Les performances varient selon la souche.")
                clarifications.append("Quelle est la race/souche de vos volailles ?")
            elif language == "en":
                warnings.append("⚠️ Without knowing the exact breed, this response is general. Performance varies by strain.")
                clarifications.append("What is the breed/strain of your poultry?")
            else:  # Spanish
                warnings.append("⚠️ Sin conocer la raza exacta, esta respuesta es general. El rendimiento varía según la cepa.")
                clarifications.append("¿Cuál es la raza/cepa de sus aves?")
        
        if "age" in missing_entities:
            if language == "fr":
                warnings.append("⚠️ L'âge est crucial pour évaluer la normalité des paramètres.")
                clarifications.append("Quel est l'âge de vos volailles (en jours ou semaines) ?")
            elif language == "en":
                warnings.append("⚠️ Age is crucial for evaluating parameter normality.")
                clarifications.append("What is the age of your poultry (in days or weeks)?")
            else:  # Spanish
                warnings.append("⚠️ La edad es crucial para evaluar la normalidad de los parámetros.")
                clarifications.append("¿Cuál es la edad de sus aves (en días o semanas)?")
        
        if "sex" in missing_entities and any(word in rag_answer.lower() for word in ["poids", "weight", "peso", "croissance", "growth"]):
            if language == "fr":
                clarifications.append("S'agit-il de mâles, femelles, ou d'un troupeau mixte ?")
            elif language == "en":
                clarifications.append("Are these males, females, or a mixed flock?")
            else:  # Spanish
                clarifications.append("¿Son machos, hembras, o un lote mixto?")
        
        # Déterminer l'impact sur la confiance
        confidence_impact = "low"
        if len(missing_entities) >= 2:
            confidence_impact = "high"
        elif len(missing_entities) == 1:
            confidence_impact = "medium"
        
        # Ajouter un contexte si des entités sont connues
        context_additions = []
        if entities.get("breed") and entities.get("breed_confidence", 0) > 0.6:
            context_additions.append(f"race {entities['breed']}")
        
        if entities.get("age_days") and entities.get("age_confidence", 0) > 0.6:
            context_additions.append(f"âge {entities['age_days']} jours")
        
        if context_additions:
            context_text = " et ".join(context_additions)
            if language == "fr":
                enhanced_answer += f"\n\n💡 Cette réponse considère votre contexte : {context_text}."
            elif language == "en":
                enhanced_answer += f"\n\n💡 This response considers your context: {context_text}."
            else:  # Spanish
                enhanced_answer += f"\n\n💡 Esta respuesta considera su contexto: {context_text}."
        
        # Ajouter les avertissements à la réponse si critiques
        if warnings and confidence_impact in ["medium", "high"]:
            enhanced_answer += f"\n\n{' '.join(warnings)}"
        
        return {
            "enhanced_answer": enhanced_answer,
            "optional_clarifications": clarifications[:3],
            "warnings": warnings,
            "confidence_impact": confidence_impact,
            "coherence_check": coherence_check,  # 🆕
            "coherence_notes": coherence_notes,  # 🆕
            "improvement_notes": "Amélioration basique appliquée",
            "method_used": "fallback"
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de l'agent"""
        
        total = self.stats["total_requests"]
        success_rate = (self.stats["openai_success"] / total * 100) if total > 0 else 0
        enhancement_rate = (self.stats["answers_enhanced"] / total * 100) if total > 0 else 0
        clarification_rate = (self.stats["clarifications_generated"] / total * 100) if total > 0 else 0
        coherence_issue_rate = (self.stats["coherence_issues_detected"] / total * 100) if total > 0 else 0
        
        return {
            "agent_type": "rag_enhancer",
            "total_requests": total,
            "openai_success_rate": f"{success_rate:.1f}%",
            "answer_enhancement_rate": f"{enhancement_rate:.1f}%",
            "clarification_generation_rate": f"{clarification_rate:.1f}%",
            "coherence_issue_detection_rate": f"{coherence_issue_rate:.1f}%",  # 🆕
            "openai_available": self.openai_available,
            "model_used": self.model,
            "detailed_stats": self.stats.copy()
        }

# Instance globale
agent_rag_enhancer = AgentRAGEnhancer()

# Fonction utilitaire pour usage externe
async def enhance_rag_answer(
    rag_answer: str,
    entities: Dict[str, Any],
    missing_entities: List[str],
    conversation_context: str,
    original_question: str = "",
    enriched_question: str = "",  # 🆕 Paramètre ajouté
    language: str = "fr"
) -> Dict[str, Any]:
    """Fonction utilitaire pour améliorer une réponse RAG avec vérification de cohérence"""
    return await agent_rag_enhancer.enhance_rag_answer(
        rag_answer, entities, missing_entities, conversation_context, 
        original_question, enriched_question, language
    )