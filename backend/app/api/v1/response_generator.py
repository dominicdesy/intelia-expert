"""
app/api/v1/general_response_generator.py - GÉNÉRATEUR DE RÉPONSES GÉNÉRALES IA

🤖 SERVICE DE GÉNÉRATION DE RÉPONSES GÉNÉRALES AVEC IA
✅ Utilise GPT-4o pour génération de qualité professionnelle
✅ Génère réponses avec fourchettes et standards selon contexte
✅ Support multilingue avec adaptation culturelle
✅ Intégration données techniques avicoles
✅ Gestion robuste des erreurs avec fallbacks intelligents
✅ Optimisé pour réponses utiles même avec informations partielles

🆕 MODIFICATIONS - INTÉGRATION IA + FALLBACK:
- ✅ Intégration AIResponseGenerator en priorité
- ✅ Fallback robuste vers templates classiques conservés
- ✅ Gestion d'erreurs centralisée avec monitoring
- ✅ Pipeline unifié avec le nouveau système IA
- ✅ Conservation complète du code original comme backup
"""

import logging
import os
import re
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

# 🆕 NOUVEAU: Import des services IA avec fallback
try:
    from .ai_response_generator import AIResponseGenerator, ResponseData
    AI_RESPONSE_GENERATOR_AVAILABLE = True
except ImportError:
    AI_RESPONSE_GENERATOR_AVAILABLE = False
    logging.warning("AIResponseGenerator non disponible - utilisation templates classiques")

logger = logging.getLogger(__name__)

class GeneralResponseGenerator:
    """
    Générateur de réponses générales avec IA
    
    🆕 NOUVEAU: Pipeline IA + fallback intelligent
    - Priorité: AIResponseGenerator pour génération intelligente
    - Fallback: Templates classiques conservés intacts
    - Robustesse: Gestion complète des erreurs
    
    Crée des réponses utiles avec fourchettes et standards
    pour questions qui n'ont pas besoin de clarification.
    """
    
    def __init__(self):
        self.model = "gpt-4o"  # Qualité maximale pour génération
        self.client = None
        self.available = False
        
        # 🆕 NOUVEAU: Intégration du générateur IA
        self.ai_generator = None
        self.ai_available = False
        self._initialize_ai_generator()
        
        # Statistiques pour monitoring (enrichies)
        self.stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "ai_generations": 0,        # 🆕 NOUVEAU: Compteur IA
            "fallback_used": 0,
            "emergency_fallback": 0,    # 🆕 NOUVEAU: Compteur urgence
            "average_response_length": 0,
            "topics_covered": {},
            "ai_success_rate": 0.0,     # 🆕 NOUVEAU: Taux succès IA
            "generation_methods": {}    # 🆕 NOUVEAU: Méthodes utilisées
        }
        
        # Templates de fallback par sujet (CONSERVÉS intacts)
        self.fallback_templates = self._initialize_fallback_templates()
        
        # Initialiser OpenAI (CONSERVÉ pour backward compatibility)
        self._initialize_openai()
        
        logger.info(f"🤖 [General Response Generator] Initialisé - IA: {self.ai_available}, OpenAI: {self.available}")
    
    def _initialize_ai_generator(self) -> bool:
        """🆕 NOUVEAU: Initialise le générateur IA"""
        try:
            if not AI_RESPONSE_GENERATOR_AVAILABLE:
                logger.warning("⚠️ [General Response] AIResponseGenerator non disponible")
                return False
            
            self.ai_generator = AIResponseGenerator()
            self.ai_available = True
            logger.info("✅ [General Response] AIResponseGenerator initialisé")
            return True
            
        except Exception as e:
            logger.error(f"❌ [General Response] Erreur initialisation IA: {e}")
            self.ai_available = False
            return False
    
    def _initialize_openai(self) -> bool:
        """CONSERVÉ: Initialise le client OpenAI (pour backward compatibility)"""
        try:
            if not OPENAI_AVAILABLE:
                logger.warning("⚠️ [General Response] OpenAI non disponible")
                return False
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("⚠️ [General Response] OPENAI_API_KEY non configuré")
                return False
            
            self.client = OpenAI(api_key=api_key)
            self.available = True
            logger.info("✅ [General Response] Client OpenAI initialisé")
            return True
            
        except Exception as e:
            logger.error(f"❌ [General Response] Erreur initialisation OpenAI: {e}")
            self.available = False
            return False
    
    async def generate_general_response(self, question: str, entities: Dict[str, Any], classification: Dict[str, Any], language: str = "fr") -> str:
        """
        Génère une réponse générale basée sur la classification IA
        
        🆕 NOUVEAU: Pipeline IA intégré avec fallback robuste
        1. Priorité: Nouveau AIResponseGenerator
        2. Fallback 1: Code original avec améliorations IA
        3. Fallback 2: Templates classiques
        4. Fallback 3: Réponse d'urgence
        
        Args:
            question: Question originale de l'utilisateur
            entities: Entités extraites (breed, age, sex, etc.)
            classification: Résultat de la classification IA
            language: Langue de génération
            
        Returns:
            str: Réponse générale complète et utile
        """
        
        start_time = datetime.now()
        self.stats["total_generations"] += 1
        
        try:
            # 🆕 PRIORITÉ 1: Nouveau générateur IA
            if self.ai_available:
                try:
                    logger.info("🤖 [General Response] Tentative génération avec AIResponseGenerator")
                    
                    ai_response = await self.ai_generator.generate_general_response(
                        question=question,
                        merged_entities=entities,
                        conversation_context=classification.get("context", ""),
                        language=language
                    )
                    
                    if ai_response and isinstance(ai_response, ResponseData) and len(ai_response.content) > 50:
                        self.stats["ai_generations"] += 1
                        self.stats["successful_generations"] += 1
                        self._update_stats(ai_response.content, "ai_generated")
                        logger.info("✅ [General Response] Réponse générée par IA")
                        return ai_response.content
                    
                except Exception as e:
                    logger.warning(f"⚠️ [General Response] Échec AIResponseGenerator: {e}")
            
            # 🔄 FALLBACK 1: Code original avec améliorations IA (CONSERVÉ)
            # Si l'IA de classification a déjà suggéré une réponse, la valider et potentiellement l'améliorer
            if classification.get("suggested_general_response") and len(classification["suggested_general_response"]) > 50:
                logger.info("🤖 [General Response] Utilisation réponse suggérée par classificateur")
                suggested_response = classification["suggested_general_response"]
                
                # Améliorer la réponse suggérée si nécessaire
                if self.available:
                    enhanced_response = await self._enhance_suggested_response(suggested_response, question, entities, language)
                    if enhanced_response:
                        self._update_stats(enhanced_response, "enhanced_suggested")
                        return enhanced_response
                
                # Sinon utiliser la réponse suggérée telle quelle
                self._update_stats(suggested_response, "suggested_direct")
                return suggested_response
            
            # 🔄 FALLBACK 2: Génération classique avec IA (CONSERVÉ)
            if self.available:
                generated_response = await self._generate_with_ai(question, entities, classification, language)
                if generated_response:
                    self._update_stats(generated_response, "ai_generated_legacy")
                    return generated_response
            
            # 🔄 FALLBACK 3: Templates intelligents (CONSERVÉ)
            fallback_response = self._generate_fallback_response(question, entities, language)
            self._update_stats(fallback_response, "fallback")
            return fallback_response
            
        except Exception as e:
            logger.error(f"❌ [General Response] Erreur génération: {e}")
            self.stats["fallback_used"] += 1
            self.stats["emergency_fallback"] += 1
            return self._generate_emergency_fallback(question, language)
    
    # 🆕 NOUVEAU: Méthode pour réponse générale simple (compatible avec AIResponseGenerator)
    async def generate_simple_response(self, question: str, entities: Dict[str, Any], language: str = "fr") -> str:
        """
        🆕 NOUVEAU: Interface simplifiée pour le nouveau pipeline IA
        
        Args:
            question: Question de l'utilisateur
            entities: Entités extraites
            language: Langue de génération
            
        Returns:
            str: Réponse générée
        """
        # Créer une classification minimale pour compatibilité
        minimal_classification = {
            "decision": "general_answer",
            "confidence": 0.8,
            "missing_for_precision": [],
            "context": ""
        }
        
        return await self.generate_general_response(question, entities, minimal_classification, language)
    
    # =====================================================================
    # MÉTHODES CONSERVÉES INTACTES (pour backward compatibility)
    # =====================================================================
    
    async def _enhance_suggested_response(self, suggested_response: str, question: str, entities: Dict[str, Any], language: str) -> Optional[str]:
        """CONSERVÉ: Améliore une réponse suggérée par le classificateur"""
        
        prompt = self._build_enhancement_prompt(suggested_response, question, entities, language)
        
        try:
            response = await self.client.chat.completions.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_message(language)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                timeout=15
            )
            
            enhanced = response.choices[0].message.content.strip()
            
            # Valider que l'amélioration est significative
            if len(enhanced) > len(suggested_response) * 1.2:  # Au moins 20% plus long
                logger.info("✨ [General Response] Réponse améliorée avec succès")
                return enhanced
            
            return None  # Pas d'amélioration significative
            
        except Exception as e:
            logger.warning(f"⚠️ [General Response] Erreur amélioration: {e}")
            return None
    
    async def _generate_with_ai(self, question: str, entities: Dict[str, Any], classification: Dict[str, Any], language: str = "fr") -> Optional[str]:
        """CONSERVÉ: Génère une réponse complète avec IA"""
        
        prompt = self._build_generation_prompt(question, entities, classification, language)
        
        try:
            response = await self.client.chat.completions.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_message(language)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Équilibre créativité/cohérence
                max_tokens=600,   # Permet réponses détaillées
                timeout=20        # Timeout généreux pour qualité
            )
            
            generated_response = response.choices[0].message.content.strip()
            
            # Validation de base
            if len(generated_response) < 50:
                logger.warning("⚠️ [General Response] Réponse générée trop courte")
                return None
            
            logger.info(f"✅ [General Response] Réponse générée ({len(generated_response)} chars)")
            return generated_response
            
        except Exception as e:
            logger.error(f"❌ [General Response] Erreur génération IA: {e}")
            return None
    
    def _build_generation_prompt(self, question: str, entities: Dict[str, Any], classification: Dict[str, Any], language: str) -> str:
        """CONSERVÉ: Construit le prompt de génération selon la langue et le contexte"""
        
        entities_text = self._format_entities_for_prompt(entities, language)
        missing_info = ", ".join(classification.get("missing_for_precision", []))
        topic = self._detect_topic(question, language)
        
        prompts = {
            "fr": f"""Tu es un vétérinaire avicole expert. Génère une réponse générale professionnelle et utile.

QUESTION: "{question}"
SUJET DÉTECTÉ: {topic}
ENTITÉS DISPONIBLES: {entities_text}
INFORMATIONS MANQUANTES POUR PRÉCISION MAXIMALE: {missing_info}

INSTRUCTIONS DE GÉNÉRATION:
1. **Réponse directe**: Commence par répondre directement à la question
2. **Fourchettes et standards**: Donne des valeurs/fourchettes standard avec contexte
3. **Variations importantes**: Mentionne les variations selon race, sexe, âge si pertinent
4. **Conseils pratiques**: Ajoute 1-2 conseils de surveillance ou d'action
5. **Référence experte**: Indique quand consulter pour cas spécifique

EXEMPLES DE STRUCTURE:
- Question poids → "Le poids normal à X jours varie de Y-Z grammes selon la race et le sexe. Les races lourdes comme Ross 308 atteignent généralement... Surveillez la croissance hebdomadairement et consultez si écart >15%."
- Question croissance → "La croissance normale présente ces caractéristiques... Les variations dépendent de... Signes d'alerte à surveiller..."
- Question alimentation → "Les besoins nutritionnels à ce stade sont... Adaptez selon... Consultez un nutritionniste si..."

STYLE:
- Professionnel mais accessible
- Précis avec chiffres/fourchettes
- Pratique et actionnable
- 150-300 mots idéalement

Génère la réponse maintenant:""",

            "en": f"""You are a poultry veterinary expert. Generate a professional and useful general response.

QUESTION: "{question}"
TOPIC DETECTED: {topic}
AVAILABLE ENTITIES: {entities_text}
MISSING INFO FOR MAX PRECISION: {missing_info}

GENERATION INSTRUCTIONS:
1. **Direct answer**: Start by directly answering the question
2. **Ranges and standards**: Provide standard values/ranges with context
3. **Important variations**: Mention variations by breed, sex, age if relevant
4. **Practical advice**: Add 1-2 monitoring or action tips
5. **Expert reference**: Indicate when to consult for specific cases

Generate the response now:""",

            "es": f"""Eres un veterinario avícola experto. Genera una respuesta general profesional y útil.

PREGUNTA: "{question}"
TEMA DETECTADO: {topic}
ENTIDADES DISPONIBLES: {entities_text}
INFO FALTANTE PARA MÁXIMA PRECISIÓN: {missing_info}

Genera la respuesta ahora:"""
        }
        
        return prompts.get(language, prompts["fr"])
    
    def _build_enhancement_prompt(self, suggested_response: str, question: str, entities: Dict[str, Any], language: str) -> str:
        """CONSERVÉ: Construit prompt pour améliorer une réponse suggérée"""
        
        prompts = {
            "fr": f"""Améliore cette réponse en la rendant plus complète et professionnelle:

QUESTION ORIGINALE: "{question}"
RÉPONSE À AMÉLIORER: "{suggested_response}"
ENTITÉS DISPONIBLES: {self._format_entities_for_prompt(entities, language)}

AMÉLIORATIONS À APPORTER:
1. Ajouter des fourchettes plus précises si possible
2. Inclure des conseils pratiques de surveillance
3. Mentionner les variations selon race/sexe/âge
4. Ajouter quand consulter un expert
5. Améliorer la structure et la clarté

Garde le même ton professionnel mais rend la réponse plus complète et utile (200-350 mots):""",

            "en": f"""Improve this response by making it more complete and professional:

ORIGINAL QUESTION: "{question}"
RESPONSE TO IMPROVE: "{suggested_response}"

Make it more complete and useful (200-350 words):""",

            "es": f"""Mejora esta respuesta haciéndola más completa y profesional:

PREGUNTA ORIGINAL: "{question}"
RESPUESTA A MEJORAR: "{suggested_response}"

Hazla más completa y útil (200-350 palabras):"""
        }
        
        return prompts.get(language, prompts["fr"])
    
    def _get_system_message(self, language: str) -> str:
        """CONSERVÉ: Messages système selon la langue"""
        
        messages = {
            "fr": "Tu es un vétérinaire avicole expert qui génère des réponses générales précises, utiles et professionnelles. Tu donnes toujours des informations pratiques avec des fourchettes de valeurs standard et des conseils concrets.",
            
            "en": "You are a poultry veterinary expert who generates accurate, useful and professional general responses. You always provide practical information with standard value ranges and concrete advice.",
            
            "es": "Eres un veterinario avícola experto que genera respuestas generales precisas, útiles y profesionales. Siempre proporcionas información práctica con rangos de valores estándar y consejos concretos."
        }
        
        return messages.get(language, messages["fr"])
    
    def _generate_fallback_response(self, question: str, entities: Dict[str, Any], language: str = "fr") -> str:
        """CONSERVÉ: Génère une réponse fallback intelligente basée sur le sujet"""
        
        topic = self._detect_topic(question, language)
        template = self.fallback_templates[language].get(topic, self.fallback_templates[language]["general"])
        
        # Personnaliser le template avec les entités disponibles
        context = {
            "age": entities.get('age_in_days', entities.get('age', 'X')),
            "breed": entities.get('breed', 'race non spécifiée'),
            "sex": entities.get('sex', 'sexe non spécifié')
        }
        
        try:
            personalized_response = template.format(**context)
            logger.info(f"📝 [General Response] Fallback généré pour sujet: {topic}")
            return personalized_response
        except Exception as e:
            logger.warning(f"⚠️ [General Response] Erreur personnalisation fallback: {e}")
            return template
    
    def _generate_emergency_fallback(self, question: str, language: str = "fr") -> str:
        """CONSERVÉ: Fallback d'urgence minimal"""
        
        emergency_responses = {
            "fr": f"Je comprends votre question sur '{question}'. Pour vous donner la réponse la plus précise possible, j'aurais besoin de connaître la race, l'âge et le sexe de vos animaux. Cependant, je peux vous dire que les standards varient généralement selon ces paramètres. N'hésitez pas à consulter un vétérinaire pour des conseils personnalisés.",
            
            "en": f"I understand your question about '{question}'. To give you the most accurate answer, I would need to know the breed, age and sex of your animals. However, I can tell you that standards generally vary according to these parameters. Don't hesitate to consult a veterinarian for personalized advice.",
            
            "es": f"Entiendo su pregunta sobre '{question}'. Para darle la respuesta más precisa, necesitaría conocer la raza, edad y sexo de sus animales. Sin embargo, puedo decirle que los estándares generalmente varían según estos parámetros. No dude en consultar a un veterinario para consejos personalizados."
        }
        
        return emergency_responses.get(language, emergency_responses["fr"])
    
    def _detect_topic(self, question: str, language: str = "fr") -> str:
        """CONSERVÉ: Détecte le sujet principal de la question"""
        
        question_lower = question.lower()
        
        topic_keywords = {
            "poids": ["poids", "weight", "peso", "gramme", "kg", "masse"],
            "croissance": ["croissance", "growth", "crecimiento", "développement", "development"],
            "alimentation": ["alimentation", "feed", "nutrition", "alimento", "ration"],
            "santé": ["maladie", "disease", "enfermedad", "symptom", "mort", "death"],
            "reproduction": ["ponte", "laying", "puesta", "œuf", "egg", "huevo"],
            "environnement": ["température", "temperature", "ventilation", "litière"],
            "vaccination": ["vaccin", "vaccine", "vacuna", "immunité", "immunity"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return topic
        
        return "général"
    
    def _format_entities_for_prompt(self, entities: Dict[str, Any], language: str = "fr") -> str:
        """CONSERVÉ: Formate les entités pour les prompts"""
        
        if not entities:
            return {"fr": "Aucune", "en": "None", "es": "Ninguna"}.get(language, "Aucune")
        
        parts = []
        if entities.get('breed'):
            parts.append(f"race: {entities['breed']}")
        if entities.get('age_in_days'):
            parts.append(f"âge: {entities['age_in_days']}j")
        elif entities.get('age'):
            parts.append(f"âge: {entities['age']}")
        if entities.get('sex'):
            parts.append(f"sexe: {entities['sex']}")
        if entities.get('weight_in_grams'):
            parts.append(f"poids: {entities['weight_in_grams']}g")
            
        return ", ".join(parts) if parts else "Partielles"
    
    def _initialize_fallback_templates(self) -> Dict[str, Dict[str, str]]:
        """CONSERVÉ: Initialise les templates de fallback par sujet et langue"""
        
        return {
            "fr": {
                "poids": "Le poids d'un poulet à {age} jours varie considérablement selon la race et le sexe. En général, les fourchettes sont de 250-500g à cet âge. Les races de chair comme Ross 308 ou Cobb 500 sont plus lourdes que les races pondeuses. Les mâles sont généralement 10-15% plus lourds que les femelles. Surveillez la croissance hebdomadairement et consultez si vous observez des écarts importants.",
                
                "croissance": "La croissance normale des poulets présente des phases distinctes. À {age} jours, vous devriez observer une activité normale, un appétit régulier et une prise de poids progressive. Les signes d'alerte incluent: apathie, refus alimentaire, retard de croissance. La race {breed} a ses propres standards de croissance qu'il convient de respecter.",
                
                "alimentation": "Les besoins nutritionnels des poulets évoluent avec l'âge. À {age} jours, l'alimentation doit être adaptée au stade de croissance. Assurez-vous d'un accès constant à une eau propre et à un aliment de qualité. Les besoins varient selon la race et l'objectif d'élevage (chair vs ponte).",
                
                "santé": "La santé des poulets nécessite une surveillance constante. Les signes à surveiller incluent: comportement, appétit, aspect des fientes, respiration. En cas de symptômes anormaux, consultez rapidement un vétérinaire. La prévention reste le meilleur traitement.",
                
                "général": "Pour votre question concernant vos poulets, les standards varient selon la race, l'âge et le sexe des animaux. Je recommande de consulter un vétérinaire avicole ou un technicien spécialisé pour des conseils personnalisés à votre situation spécifique."
            },
            
            "en": {
                "poids": "Chicken weight at {age} days varies considerably by breed and sex. Generally, ranges are 250-500g at this age. Broiler breeds like Ross 308 or Cobb 500 are heavier than layer breeds. Males are typically 10-15% heavier than females. Monitor growth weekly and consult if you observe significant deviations.",
                
                "général": "For your question about chickens, standards vary by breed, age and sex. I recommend consulting a poultry veterinarian or specialized technician for advice tailored to your specific situation."
            },
            
            "es": {
                "poids": "El peso del pollo a los {age} días varía considerablemente según la raza y el sexo. Generalmente, los rangos son de 250-500g a esta edad. Las razas de engorde como Ross 308 o Cobb 500 son más pesadas que las razas ponedoras.",
                
                "general": "Para su pregunta sobre pollos, los estándares varían según la raza, edad y sexo. Recomiendo consultar a un veterinario avícola para consejos adaptados a su situación específica."
            }
        }
    
    def _update_stats(self, response: str, method: str) -> None:
        """🆕 AMÉLIORÉ: Met à jour les statistiques avec nouvelles métriques"""
        
        if method not in ["fallback", "emergency_fallback"]:
            self.stats["successful_generations"] += 1
        else:
            self.stats["fallback_used"] += 1
        
        # Compter les méthodes utilisées
        if method in self.stats["generation_methods"]:
            self.stats["generation_methods"][method] += 1
        else:
            self.stats["generation_methods"][method] = 1
        
        # Longueur moyenne
        current_avg = self.stats["average_response_length"]
        total = self.stats["total_generations"]
        new_length = len(response)
        self.stats["average_response_length"] = ((current_avg * (total - 1)) + new_length) / total
        
        # 🆕 NOUVEAU: Taux de succès IA
        if self.stats["total_generations"] > 0:
            self.stats["ai_success_rate"] = self.stats["ai_generations"] / self.stats["total_generations"]
    
    def get_stats(self) -> Dict[str, Any]:
        """🆕 AMÉLIORÉ: Retourne les statistiques enrichies"""
        return {
            **self.stats,
            "availability": {
                "ai_generator": self.ai_available,
                "openai_direct": self.available
            },
            "model": self.model,
            "success_rate": self.stats["successful_generations"] / max(1, self.stats["total_generations"]),
            "generation_pipeline": {
                "ai_generator_priority": self.ai_available,
                "fallback_levels": ["ai_generator", "openai_enhancement", "openai_direct", "templates", "emergency"],
                "current_primary": "ai_generator" if self.ai_available else "openai_direct" if self.available else "templates"
            }
        }

# Instance globale (CONSERVÉE)
general_response_generator = GeneralResponseGenerator()

# Fonction utilitaire (CONSERVÉE + améliorée)
async def generate_general_response(question: str, entities: Dict[str, Any], classification: Dict[str, Any], language: str = "fr") -> str:
    """
    Fonction utilitaire pour génération de réponse générale
    
    🆕 AMÉLIORÉ: Support du nouveau pipeline IA avec fallback robuste
    
    Usage:
        response = await generate_general_response(
            "Poids poulet 19 jours", 
            {"age_in_days": 19}, 
            {"decision": "general_answer", "missing_for_precision": ["breed", "sex"]}
        )
    """
    return await general_response_generator.generate_general_response(question, entities, classification, language)

# 🆕 NOUVELLE fonction utilitaire simplifiée pour le pipeline IA
async def generate_simple_general_response(question: str, entities: Dict[str, Any], language: str = "fr") -> str:
    """
    🆕 NOUVEAU: Interface simplifiée pour le nouveau pipeline IA
    
    Usage:
        response = await generate_simple_general_response(
            "Poids poulet Ross 308 mâle 19 jours",
            {"breed": "Ross 308", "age_in_days": 19, "sex": "mâle"}
        )
    """
    return await general_response_generator.generate_simple_response(question, entities, language)

logger.info("🤖 [General Response Generator] Module de génération de réponses générales chargé avec intégration IA")