"""
app/api/v1/expert_utils.py - FONCTIONS UTILITAIRES EXPERT SYSTEM

Fonctions utilitaires communes pour le système expert
"""

import os
import logging
import uuid
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import Request

logger = logging.getLogger(__name__)

# =============================================================================
# FONCTIONS UTILITAIRES GÉNÉRALES
# =============================================================================

def get_user_id_from_request(fastapi_request: Request) -> str:
    """Extrait l'ID utilisateur de la requête"""
    try:
        user = getattr(fastapi_request.state, "user", None)
        if user:
            return str(user.get("id", user.get("user_id", "authenticated_user")))
        
        client_ip = fastapi_request.client.host if fastapi_request.client else "unknown"
        user_agent = fastapi_request.headers.get("user-agent", "unknown")
        
        anonymous_data = f"{client_ip}_{user_agent}_{datetime.now().strftime('%Y-%m-%d')}"
        anonymous_id = f"anon_{hashlib.md5(anonymous_data.encode()).hexdigest()[:8]}"
        
        return anonymous_id
        
    except Exception as e:
        logger.warning(f"⚠️ [Expert Utils] Erreur génération user_id: {e}")
        return f"anon_{uuid.uuid4().hex[:8]}"

def build_enriched_question_from_clarification(
    original_question: str,
    clarification_response: str,
    conversation_context: str = ""
) -> str:
    """Construit une question enrichie après clarification"""
    
    enriched_parts = [original_question]
    
    if clarification_response.strip():
        enriched_parts.append(f"Information supplémentaire: {clarification_response.strip()}")
    
    if conversation_context.strip():
        enriched_parts.append(f"Contexte: {conversation_context.strip()}")
    
    return "\n\n".join(enriched_parts)

def get_fallback_response_enhanced(question: str, language: str = "fr") -> str:
    """Réponse de fallback améliorée"""
    try:
        safe_question = str(question)[:50] if question else "votre question"
    except:
        safe_question = "votre question"
    
    fallback_responses = {
        "fr": f"Je suis un expert vétérinaire spécialisé en aviculture. Pour votre question '{safe_question}...', je recommande de surveiller attentivement les paramètres de performance et de maintenir des conditions d'élevage optimales. Pour une réponse plus précise, pourriez-vous spécifier la race et l'âge de vos poulets ?",
        "en": f"I am a veterinary expert specialized in poultry. For your question '{safe_question}...', I recommend closely monitoring performance parameters and maintaining optimal breeding conditions. For a more precise answer, could you specify the breed and age of your chickens?",
        "es": f"Soy un experto veterinario especializado en avicultura. Para su pregunta '{safe_question}...', recomiendo monitorear cuidadosamente los parámetros de rendimiento y mantener condiciones óptimas de crianza. Para una respuesta más precisa, ¿podría especificar la raza y edad de sus pollos?"
    }
    return fallback_responses.get(language.lower(), fallback_responses["fr"])

# =============================================================================
# FONCTIONS DE TRAITEMENT OPENAI
# =============================================================================

async def process_question_with_enhanced_prompt(
    question: str, 
    language: str = "fr", 
    speed_mode: str = "balanced",
    extracted_entities: Dict = None,
    conversation_context: str = ""
) -> str:
    """Traite une question avec prompt amélioré pour données numériques"""
    
    try:
        import openai
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return get_fallback_response_enhanced(question, language)
        
        openai.api_key = api_key
        
        # Prompt amélioré avec données numériques
        enhanced_prompts = {
            "fr": f"""Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair. 

CONSIGNES CRITIQUES:
1. Si la question porte sur le poids, la croissance ou des valeurs numériques, donne TOUJOURS une réponse chiffrée précise
2. Utilise le contexte conversationnel fourni pour personnaliser ta réponse
3. Commence par répondre directement à la question, puis donne des conseils complémentaires
4. Utilise tous les caractères français (é, è, à, ç, ù, etc.) et symboles (°C, %, g, kg)

Contexte conversationnel disponible:
{conversation_context}

IMPORTANT: Si des informations spécifiques sont mentionnées (race, âge), utilise-les pour donner une réponse précise et chiffrée.""",

            "en": f"""You are a veterinary expert specialized in animal health and nutrition, particularly for broiler chickens.

CRITICAL INSTRUCTIONS:
1. If the question is about weight, growth or numerical values, ALWAYS provide precise numerical answers
2. Use the provided conversational context to personalize your response  
3. Start by directly answering the question, then provide additional advice
4. Provide industry-standard data and recommendations

Available conversational context:
{conversation_context}

IMPORTANT: If specific information is mentioned (breed, age), use it to provide precise, numerical answers.""",

            "es": f"""Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde.

INSTRUCCIONES CRÍTICAS:
1. Si la pregunta es sobre peso, crecimiento o valores numéricos, da SIEMPRE una respuesta numérica precisa
2. Usa el contexto conversacional proporcionado para personalizar tu respuesta
3. Comienza respondiendo directamente a la pregunta, luego da consejos adicionales  
4. Usa todos los caracteres especiales del español (ñ, ¿, ¡, acentos)

Contexto conversacional disponible:
{conversation_context}

IMPORTANTE: Si se menciona información específica (raza, edad), úsala para dar una respuesta precisa y numérica."""
        }
        
        system_prompt = enhanced_prompts.get(language.lower(), enhanced_prompts["fr"])
        
        # Configuration par mode
        model_config = {
            "fast": {"model": "gpt-3.5-turbo", "max_tokens": 400},
            "balanced": {"model": "gpt-4o-mini", "max_tokens": 600},
            "quality": {"model": "gpt-4o-mini", "max_tokens": 800}
        }
        
        config = model_config.get(speed_mode, model_config["balanced"])
        
        response = openai.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(question)}
            ],
            temperature=0.7,
            max_tokens=config["max_tokens"],
            timeout=20
        )
        
        answer = response.choices[0].message.content
        return str(answer) if answer else get_fallback_response_enhanced(question, language)
        
    except Exception as e:
        logger.error(f"❌ [Expert Utils] Erreur OpenAI: {e}")
        return get_fallback_response_enhanced(question, language)

# =============================================================================
# FONCTIONS DE TOPICS
# =============================================================================

def get_enhanced_topics_by_language():
    """Retourne les topics enrichis par langue"""
    return {
        "fr": [
            "Poids normal Ross 308 de 12 jours (340-370g attendu)",
            "Température optimale poulailler (32°C démarrage)",
            "Mortalité élevée diagnostic (>5% problématique)", 
            "Problèmes de croissance retard développement",
            "Protocoles vaccination Gumboro + Newcastle",
            "Indice de conversion alimentaire optimal (1.6-1.8)",
            "Ventilation et qualité d'air bâtiment fermé",
            "Densité élevage optimale (15-20 poulets/m²)"
        ],
        "en": [
            "Normal weight Ross 308 at 12 days (340-370g expected)",
            "Optimal broiler house temperature (32°C starter)",
            "High mortality diagnosis (>5% problematic)",
            "Growth problems development delays",
            "Vaccination protocols Gumboro + Newcastle", 
            "Optimal feed conversion ratio (1.6-1.8)",
            "Ventilation and air quality closed buildings",
            "Optimal stocking density (15-20 birds/m²)"
        ],
        "es": [
            "Peso normal Ross 308 a los 12 días (340-370g esperado)",
            "Temperatura óptima galpón (32°C iniciador)",
            "Diagnóstico mortalidad alta (>5% problemático)",
            "Problemas crecimiento retrasos desarrollo",
            "Protocolos vacunación Gumboro + Newcastle",
            "Índice conversión alimentaria óptimo (1.6-1.8)",
            "Ventilación y calidad aire edificios cerrados", 
            "Densidad crianza óptima (15-20 pollos/m²)"
        ]
    }

# =============================================================================
# FONCTIONS DE SAUVEGARDE
# =============================================================================

async def save_conversation_auto_enhanced(
    conversation_id: str,
    question: str, 
    response: str,
    user_id: str = "anonymous",
    language: str = "fr",
    rag_used: bool = False,
    rag_score: float = None,
    response_time_ms: int = 0
) -> bool:
    """Sauvegarde automatique enhanced - Compatible avec logging existant"""
    
    try:
        from app.api.v1.logging import logger_instance, ConversationCreate
        
        if not logger_instance:
            logger.warning("⚠️ [Expert Utils] Logging non disponible pour sauvegarde")
            return False
        
        # Créer l'objet conversation
        conversation = ConversationCreate(
            user_id=str(user_id),
            question=str(question),
            response=str(response),
            conversation_id=conversation_id,
            confidence_score=rag_score,
            response_time_ms=response_time_ms,
            language=language,
            rag_used=rag_used
        )
        
        # Essayer différentes méthodes de sauvegarde
        if hasattr(logger_instance, 'log_conversation'):
            logger_instance.log_conversation(conversation)
            logger.info(f"✅ [Expert Utils] Conversation sauvegardée: {conversation_id}")
            return True
        elif hasattr(logger_instance, 'save_conversation'):
            logger_instance.save_conversation(conversation)
            logger.info(f"✅ [Expert Utils] Conversation sauvegardée: {conversation_id}")
            return True
        else:
            logger.warning("⚠️ [Expert Utils] Aucune méthode de sauvegarde disponible")
            return False
        
    except ImportError:
        logger.warning("⚠️ [Expert Utils] Module logging non disponible")
        return False
    except Exception as e:
        logger.error(f"❌ [Expert Utils] Erreur sauvegarde: {e}")
        return False

# =============================================================================
# CONFIGURATION
# =============================================================================

logger.info("✅ [Expert Utils] Fonctions utilitaires initialisées")
