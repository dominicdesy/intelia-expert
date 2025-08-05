"""
app/api/v1/intelligent_clarification_classifier.py - CLASSIFICATION IA INTELLIGENTE

🧠 SERVICE DE CLASSIFICATION IA POUR DÉCISIONS DE CLARIFICATION
✅ Utilise GPT-4o-mini pour décisions économiques et rapides
✅ Remplace les règles hardcodées par intelligence adaptative
✅ Gestion robuste des erreurs avec fallback sécurisé
✅ Support multilingue (français, anglais, espagnol)
✅ Logging détaillé pour monitoring et debugging
"""

import logging
import json
import os
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

# Import OpenAI sécurisé
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None
    OpenAI = None

logger = logging.getLogger(__name__)

class IntelligentClarificationClassifier:
    """
    Classificateur IA intelligent pour décisions de clarification
    
    Décide intelligemment si une question peut être répondue directement,
    nécessite une réponse générale, ou demande vraiment clarification.
    """
    
    def __init__(self):
        self.model = "gpt-4o-mini"  # Économique et rapide pour classification
        self.client = None
        self.available = False
        
        # Statistiques pour monitoring
        self.stats = {
            "total_classifications": 0,
            "direct_answers": 0,
            "general_answers": 0,
            "clarifications_needed": 0,
            "errors": 0,
            "average_confidence": 0.0
        }
        
        # Initialiser le client OpenAI
        self._initialize_openai()
        
        logger.info(f"🧠 [AI Classifier] Initialisé - Disponible: {self.available}")
    
    def _initialize_openai(self) -> bool:
        """Initialise le client OpenAI avec gestion d'erreurs robuste"""
        try:
            if not OPENAI_AVAILABLE:
                logger.warning("⚠️ [AI Classifier] OpenAI non disponible - module non importé")
                return False
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("⚠️ [AI Classifier] OPENAI_API_KEY non configuré")
                return False
            
            self.client = OpenAI(api_key=api_key)
            self.available = True
            logger.info("✅ [AI Classifier] Client OpenAI initialisé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ [AI Classifier] Erreur initialisation OpenAI: {e}")
            self.available = False
            return False
    
    async def classify_question(self, question: str, extracted_entities: Dict[str, Any], language: str = "fr") -> Dict[str, Any]:
        """
        Classification intelligente IA : peut-on répondre ou faut-il clarifier ?
        
        Args:
            question: Question de l'utilisateur
            extracted_entities: Entités extraites (breed, age, sex, etc.)
            language: Langue de traitement
            
        Returns:
            {
                "decision": "direct_answer" | "general_answer" | "needs_clarification",
                "confidence": float (0.0-1.0),
                "reasoning": str,
                "missing_for_precision": List[str],
                "suggested_general_response": str (si general_answer),
                "processing_time_ms": int,
                "model_used": str
            }
        """
        
        start_time = datetime.now()
        self.stats["total_classifications"] += 1
        
        try:
            if not self.available:
                logger.warning("⚠️ [AI Classifier] Service non disponible - fallback")
                return self._create_fallback_classification(question, "service_unavailable")
            
            # Construire le prompt de classification
            prompt = self._build_classification_prompt(question, extracted_entities, language)
            
            # Appel OpenAI pour classification
            response = await self._call_openai_classification(prompt, language)
            
            if not response:
                return self._create_fallback_classification(question, "openai_error")
            
            # Parser et valider la réponse
            classification = self._parse_and_validate_response(response, question)
            
            # Mise à jour statistiques
            self._update_stats(classification)
            
            # Ajouter métadonnées
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            classification.update({
                "processing_time_ms": int(processing_time),
                "model_used": self.model,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"🧠 [AI Classification] {classification['decision']} - Confiance: {classification['confidence']:.2f} - Temps: {processing_time:.0f}ms")
            
            return classification
            
        except Exception as e:
            logger.error(f"❌ [AI Classification] Erreur: {e}")
            self.stats["errors"] += 1
            return self._create_fallback_classification(question, f"error: {str(e)}")
    
    def _build_classification_prompt(self, question: str, entities: Dict[str, Any], language: str) -> str:
        """Construit le prompt de classification selon la langue"""
        
        entities_context = self._format_entities(entities, language)
        
        prompts = {
            "fr": f"""Tu es un expert vétérinaire avicole. Analyse cette question et détermine la meilleure approche de réponse.

QUESTION: "{question}"

ENTITÉS DÉTECTÉES:
{entities_context}

DÉCISIONS POSSIBLES:
1. **direct_answer**: Assez d'informations pour une réponse précise et spécifique
   - Ex: "Ross 308 mâles 21 jours" → réponse précise avec données exactes
   
2. **general_answer**: Question mérite une réponse générale utile avec fourchettes/standards
   - Ex: "poids poulet 19 jours" → réponse avec fourchettes selon race/sexe
   - Ex: "croissance normale poulets" → standards généraux de croissance
   
3. **needs_clarification**: Vraiment trop vague pour donner une réponse utile
   - Ex: "mes animaux vont mal" → impossible de conseiller sans détails

RÈGLES IMPORTANTES:
- FAVORISE les réponses utiles (direct ou general) plutôt que clarification
- Questions de poids/croissance avec âge → TOUJOURS general_answer
- Questions avec race spécifique (Ross, Cobb, etc.) → direct_answer
- Seulement needs_clarification si VRAIMENT impossible de donner info utile
- Une réponse générale avec fourchettes est TOUJOURS mieux qu'une clarification

EXEMPLES:
- "Poids poulet 19 jours" → general_answer (peut donner fourchettes 300-450g)
- "Ross 308 mâles performance" → direct_answer (assez spécifique)
- "Problème avec animaux" → needs_clarification (trop vague)

Réponds UNIQUEMENT en JSON valide:""",

            "en": f"""You are a poultry veterinary expert. Analyze this question and determine the best response approach.

QUESTION: "{question}"

DETECTED ENTITIES:
{entities_context}

POSSIBLE DECISIONS:
1. **direct_answer**: Enough information for precise, specific response
2. **general_answer**: Question deserves useful general response with ranges/standards
3. **needs_clarification**: Really too vague to provide useful information

IMPORTANT RULES:
- FAVOR useful responses (direct or general) over clarification
- Weight/growth questions with age → ALWAYS general_answer
- Questions with specific breed → direct_answer
- Only needs_clarification if REALLY impossible to give useful info

Respond ONLY in valid JSON:""",

            "es": f"""Eres un experto veterinario avícola. Analiza esta pregunta y determina el mejor enfoque de respuesta.

PREGUNTA: "{question}"

ENTIDADES DETECTADAS:
{entities_context}

DECISIONES POSIBLES:
1. **direct_answer**: Suficiente información para respuesta precisa
2. **general_answer**: Pregunta merece respuesta general útil con rangos
3. **needs_clarification**: Realmente muy vaga para dar información útil

REGLAS IMPORTANTES:
- FAVORECER respuestas útiles sobre clarificación
- Preguntas de peso/crecimiento con edad → SIEMPRE general_answer

Responde SOLO en JSON válido:"""
        }
        
        base_prompt = prompts.get(language, prompts["fr"])
        
        # Ajouter le format JSON attendu
        json_format = """{
  "decision": "general_answer",
  "confidence": 0.9,
  "reasoning": "Question sur poids avec âge précis, peut donner fourchettes utiles selon race et sexe",
  "missing_for_precision": ["breed", "sex"],
  "suggested_general_response": "Le poids normal d'un poulet à 19 jours varie de 300-450g selon la race et le sexe. Les Ross 308 mâles pèsent généralement 380-420g, les femelles 320-380g à cet âge."
}"""
        
        return f"{base_prompt}\n\n{json_format}"
    
    async def _call_openai_classification(self, prompt: str, language: str) -> Optional[str]:
        """Appel OpenAI avec gestion d'erreurs et retry"""
        
        system_messages = {
            "fr": "Tu es un classificateur expert qui optimise les réponses aux questions d'aviculture. Tu favorises toujours les réponses utiles plutôt que les clarifications.",
            "en": "You are an expert classifier that optimizes responses to poultry questions. You always favor useful responses over clarifications.",
            "es": "Eres un clasificador experto que optimiza respuestas a preguntas avícolas. Siempre favoreces respuestas útiles sobre clarificaciones."
        }
        
        system_message = system_messages.get(language, system_messages["fr"])
        
        try:
            response = await self.client.chat.completions.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Faible pour cohérence
                max_tokens=600,   # Suffisant pour réponse complète
                timeout=10        # Timeout rapide
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ [AI Classification] Erreur appel OpenAI: {e}")
            return None
    
    def _parse_and_validate_response(self, response_text: str, question: str) -> Dict[str, Any]:
        """Parse et valide la réponse JSON de l'IA"""
        
        try:
            # Tenter de parser le JSON
            classification = json.loads(response_text)
            
            # Validation des champs obligatoires
            required_fields = ["decision", "confidence", "reasoning"]
            for field in required_fields:
                if field not in classification:
                    raise ValueError(f"Champ obligatoire manquant: {field}")
            
            # Validation des valeurs
            valid_decisions = ["direct_answer", "general_answer", "needs_clarification"]
            if classification["decision"] not in valid_decisions:
                raise ValueError(f"Décision invalide: {classification['decision']}")
            
            # Normaliser confidence
            confidence = float(classification["confidence"])
            classification["confidence"] = max(0.0, min(1.0, confidence))
            
            # Ajouter champs manquants avec valeurs par défaut
            classification.setdefault("missing_for_precision", [])
            classification.setdefault("suggested_general_response", "")
            
            return classification
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ [AI Classification] JSON invalide: {e}")
            return self._create_fallback_classification(question, "invalid_json")
            
        except Exception as e:
            logger.error(f"❌ [AI Classification] Erreur validation: {e}")
            return self._create_fallback_classification(question, f"validation_error: {str(e)}")
    
    def _create_fallback_classification(self, question: str, reason: str) -> Dict[str, Any]:
        """Crée une classification fallback sécurisée"""
        
        # Logique fallback simple basée sur mots-clés
        question_lower = question.lower()
        
        # Si question contient poids + nombre (âge) → général
        if any(word in question_lower for word in ["poids", "weight", "peso"]) and any(char.isdigit() for char in question):
            decision = "general_answer"
            suggested_response = "Je peux vous donner des fourchettes de poids standard selon l'âge, mais la race et le sexe influencent ces valeurs."
        # Si race spécifique → direct
        elif any(breed in question_lower for breed in ["ross", "cobb", "hubbard", "aviagen"]):
            decision = "direct_answer"
            suggested_response = ""
        # Sinon clarification
        else:
            decision = "needs_clarification"
            suggested_response = ""
        
        return {
            "decision": decision,
            "confidence": 0.3,  # Faible confiance pour fallback
            "reasoning": f"Fallback utilisé - Raison: {reason}",
            "missing_for_precision": ["breed", "age", "sex"],
            "suggested_general_response": suggested_response,
            "fallback_used": True,
            "fallback_reason": reason
        }
    
    def _format_entities(self, entities: Dict[str, Any], language: str = "fr") -> str:
        """Formate les entités pour le prompt selon la langue"""
        
        if not entities:
            labels = {
                "fr": "Aucune entité spécifique détectée",
                "en": "No specific entities detected", 
                "es": "No se detectaron entidades específicas"
            }
            return labels.get(language, labels["fr"])
            
        parts = []
        
        # Race/Breed
        if entities.get('breed'):
            labels = {"fr": "Race", "en": "Breed", "es": "Raza"}
            parts.append(f"{labels.get(language, 'Race')}: {entities['breed']}")
        
        # Âge/Age
        if entities.get('age_in_days'):
            labels = {"fr": "Âge", "en": "Age", "es": "Edad"}
            parts.append(f"{labels.get(language, 'Âge')}: {entities['age_in_days']} jours")
        elif entities.get('age'):
            labels = {"fr": "Âge", "en": "Age", "es": "Edad"}
            parts.append(f"{labels.get(language, 'Âge')}: {entities['age']}")
        
        # Sexe/Sex
        if entities.get('sex'):
            labels = {"fr": "Sexe", "en": "Sex", "es": "Sexo"}
            parts.append(f"{labels.get(language, 'Sexe')}: {entities['sex']}")
        
        # Poids/Weight
        if entities.get('weight_in_grams'):
            labels = {"fr": "Poids", "en": "Weight", "es": "Peso"}
            parts.append(f"{labels.get(language, 'Poids')}: {entities['weight_in_grams']}g")
        
        if not parts:
            labels = {
                "fr": "Entités partielles détectées",
                "en": "Partial entities detected",
                "es": "Entidades parciales detectadas"
            }
            return labels.get(language, labels["fr"])
            
        return "\n".join(parts)
    
    def _update_stats(self, classification: Dict[str, Any]) -> None:
        """Met à jour les statistiques de classification"""
        
        decision = classification.get("decision", "unknown")
        confidence = classification.get("confidence", 0.0)
        
        if decision == "direct_answer":
            self.stats["direct_answers"] += 1
        elif decision == "general_answer":
            self.stats["general_answers"] += 1
        elif decision == "needs_clarification":
            self.stats["clarifications_needed"] += 1
        
        # Mise à jour confiance moyenne
        total = self.stats["total_classifications"]
        current_avg = self.stats["average_confidence"]
        self.stats["average_confidence"] = ((current_avg * (total - 1)) + confidence) / total
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de classification"""
        return {
            **self.stats,
            "availability": self.available,
            "model": self.model,
            "success_rate": (self.stats["total_classifications"] - self.stats["errors"]) / max(1, self.stats["total_classifications"])
        }
    
    def reset_stats(self) -> None:
        """Remet à zéro les statistiques"""
        self.stats = {
            "total_classifications": 0,
            "direct_answers": 0,
            "general_answers": 0,
            "clarifications_needed": 0,
            "errors": 0,
            "average_confidence": 0.0
        }
        logger.info("📊 [AI Classifier] Statistiques remises à zéro")

# Instance globale pour réutilisation
ai_classifier = IntelligentClarificationClassifier()

# Fonction utilitaire pour usage externe
async def classify_question_intelligently(question: str, entities: Dict[str, Any], language: str = "fr") -> Dict[str, Any]:
    """
    Fonction utilitaire pour classification intelligente
    
    Usage:
        result = await classify_question_intelligently("Poids poulet 19 jours", entities)
        if result["decision"] == "general_answer":
            # Générer réponse générale
    """
    return await ai_classifier.classify_question(question, entities, language)

logger.info("🧠 [AI Classifier] Module de classification intelligente chargé")
