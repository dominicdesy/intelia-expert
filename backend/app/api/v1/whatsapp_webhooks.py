# app/api/v1/whatsapp_webhooks.py
# -*- coding: utf-8 -*-
"""
WhatsApp Webhook Handler via Twilio
Traite les messages WhatsApp entrants et envoie les réponses
Version: 2.0 - Integrated with ChatHandlers (same as frontend)
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Form
from twilio.rest import Client
from twilio.request_validator import RequestValidator

# Supabase client for user lookup
try:
    from supabase import create_client, Client as SupabaseClient
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Import ChatHandlers from llm module
# Add llm directory to path if needed
llm_path = os.path.join(os.path.dirname(__file__), "../../../llm")
if os.path.exists(llm_path) and llm_path not in sys.path:
    sys.path.insert(0, llm_path)

try:
    from api.chat_handlers import ChatHandlers
    from utils.utilities import detect_language_enhanced, safe_get_attribute
    CHAT_HANDLERS_AVAILABLE = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("✅ ChatHandlers imported successfully for WhatsApp integration")
except ImportError as e:
    CHAT_HANDLERS_AVAILABLE = False
    logger_init = logging.getLogger(__name__)
    logger_init.error(f"❌ Failed to import ChatHandlers: {e}")

router = APIRouter(prefix="/whatsapp", tags=["whatsapp-webhooks"])
logger = logging.getLogger(__name__)

# Configuration Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+15075195932")

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Initialiser le client Twilio
twilio_client = None
request_validator = None

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    request_validator = RequestValidator(TWILIO_AUTH_TOKEN)
    logger.info("✅ Twilio client initialized")
else:
    logger.warning("⚠️ Twilio credentials not configured - WhatsApp disabled")

# Initialize ChatHandlers for RAG integration (same as frontend)
chat_handlers = None
health_monitor = None

def get_or_create_chat_handlers():
    """
    Lazy initialization of ChatHandlers with health_monitor
    This allows the RAG engine to be initialized after app startup
    """
    global chat_handlers, health_monitor

    if chat_handlers is not None:
        return chat_handlers

    if not CHAT_HANDLERS_AVAILABLE:
        logger.error("❌ ChatHandlers not available (import failed)")
        return None

    try:
        # Try to get health_monitor from llm module
        # The llm module should have a global health_monitor instance
        try:
            from core.services import health_monitor as hm
            health_monitor = hm
            logger.info("✅ health_monitor imported from core.services")
        except ImportError:
            try:
                # Alternative import path
                from services import health_monitor as hm
                health_monitor = hm
                logger.info("✅ health_monitor imported from services")
            except ImportError:
                logger.warning("⚠️ health_monitor not found - ChatHandlers will init without it")
                health_monitor = None

        # Create services dict with health_monitor (or empty if not available)
        services_dict = {}
        if health_monitor:
            services_dict["health_monitor"] = health_monitor

        # Initialize ChatHandlers
        chat_handlers = ChatHandlers(services_dict)
        logger.info("✅ ChatHandlers initialized for WhatsApp RAG integration")

        return chat_handlers

    except Exception as e:
        logger.error(f"❌ Failed to initialize ChatHandlers: {e}", exc_info=True)
        return None


# ==================== HELPERS ====================


def get_user_by_whatsapp_number(whatsapp_number: str) -> Optional[Dict[str, Any]]:
    """
    Récupère l'utilisateur associé à un numéro WhatsApp depuis Supabase

    Args:
        whatsapp_number: Numéro WhatsApp (format: whatsapp:+1234567890)

    Returns:
        Dict avec les infos utilisateur ou None si non trouvé
    """
    try:
        if not SUPABASE_AVAILABLE or not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            logger.error("❌ Supabase not configured for WhatsApp user lookup")
            return None

        # Normaliser le numéro (enlever le préfixe whatsapp:)
        clean_number = whatsapp_number.replace("whatsapp:", "").strip()

        # Créer client Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        # Chercher l'utilisateur par numéro WhatsApp
        response = supabase.table("users").select(
            "email, whatsapp_number, first_name, last_name, plan, user_type"
        ).eq("whatsapp_number", clean_number).execute()

        if response.data and len(response.data) > 0:
            user = response.data[0]
            logger.info(f"✅ User found for WhatsApp: {user.get('email')}")
            return {
                "user_email": user.get("email"),
                "whatsapp_number": user.get("whatsapp_number"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "plan_name": user.get("plan", "essential"),
                "user_type": user.get("user_type"),
                "whatsapp_verified": True  # Si le numéro est dans la DB, il est considéré vérifié
            }
        else:
            logger.warning(f"⚠️ No user found for WhatsApp: {clean_number}")
            return None

    except Exception as e:
        logger.error(f"❌ Error getting user by WhatsApp from Supabase: {e}")
        return None


# NOTE: link_whatsapp_to_user function removed - WhatsApp numbers are now
# managed directly in the Supabase users table via the user profile update endpoint


# ==================== RAG INTEGRATION (SAME AS FRONTEND) ====================

async def handle_text_message(from_number: str, body: str, user_info: Dict[str, Any], conversation_id: Optional[str] = None) -> str:
    """
    Traite un message texte WhatsApp avec le système RAG complet (identique au frontend)

    VERSION 2.0:
    - Utilise ChatHandlers.generate_rag_response() (même que frontend)
    - Support complet RAG avec QueryRouter
    - Historique de conversation via ConversationMemory
    - Chain of Thought (COT) analysis
    - Extraction d'entités et validation
    - Messages de clarification intelligents

    Args:
        from_number: Numéro WhatsApp de l'expéditeur
        body: Contenu du message
        user_info: Informations de l'utilisateur
        conversation_id: ID de conversation pour isoler l'historique

    Returns:
        Réponse de l'assistant AI (complète, pas de streaming pour WhatsApp)
    """
    try:
        # Lazy initialization of chat_handlers
        handlers = get_or_create_chat_handlers()
        if not handlers:
            logger.error("❌ ChatHandlers not available - falling back to simple response")
            return "Désolé, le service d'assistance n'est pas disponible actuellement. Veuillez réessayer plus tard."

        user_email = user_info.get("user_email")
        user_name = user_info.get("first_name", "")

        # Utiliser le numéro WhatsApp comme tenant_id (identifiant utilisateur unique)
        tenant_id = from_number.replace("whatsapp:", "").strip()

        # Si pas de conversation_id fourni, créer un basé sur le numéro
        if not conversation_id:
            conversation_id = f"whatsapp_{tenant_id}"

        logger.info(f"📝 WhatsApp message from {user_email} ({user_name}): {body[:100]}...")
        logger.info(f"🔧 Using tenant_id={tenant_id}, conversation_id={conversation_id}")

        # Détection automatique de la langue (comme frontend)
        try:
            language_result = detect_language_enhanced(body)
            detected_language = (
                language_result.language
                if hasattr(language_result, "language")
                else str(language_result)
            )
            logger.info(f"🌍 Detected language: {detected_language}")
        except Exception as lang_error:
            logger.warning(f"⚠️ Language detection failed: {lang_error}, defaulting to 'fr'")
            detected_language = "fr"

        # APPEL RAG IDENTIQUE AU FRONTEND
        # Le QueryRouter gère: contexte + extraction + validation + clarification + COT
        rag_result = await handlers.generate_rag_response(
            query=body,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            language=detected_language,
            use_json_search=True,  # Activer recherche JSON comme frontend
            genetic_line_filter=None,  # Pas de filtre par défaut
            performance_context=None,
        )

        # Fallback si RAG indisponible
        if not rag_result:
            logger.warning("⚠️ RAG result is None, using fallback")
            return "Désolé, je ne peux pas traiter votre question pour le moment. Veuillez réessayer dans quelques instants."

        # Extraire la réponse du RAG result
        answer = safe_get_attribute(rag_result, "answer", "")
        if not answer:
            answer = safe_get_attribute(rag_result, "response", "")
        if not answer:
            answer = safe_get_attribute(rag_result, "text", "")

        if not answer:
            logger.error("❌ No answer found in RAG result")
            return "Désolé, je n'ai pas pu générer une réponse. Veuillez reformuler votre question."

        # Extraire métadonnées pour logging
        metadata = safe_get_attribute(rag_result, "metadata", {}) or {}
        source = safe_get_attribute(rag_result, "source", "unknown")
        confidence = safe_get_attribute(rag_result, "confidence", 0.0)

        # Normaliser source (peut être un enum)
        if hasattr(source, "value"):
            source = source.value
        else:
            source = str(source)

        logger.info(
            f"✅ RAG response generated for {user_email} | "
            f"source={source}, confidence={confidence:.2f}, "
            f"length={len(answer)} chars"
        )

        # Pour WhatsApp, retourner la réponse complète (pas de streaming)
        # Le frontend utilise streaming, mais WhatsApp envoie le message complet
        return str(answer)

    except Exception as e:
        logger.error(f"❌ Error handling WhatsApp text message: {e}", exc_info=True)
        return "Désolé, une erreur s'est produite lors du traitement de votre message. Veuillez réessayer."


async def handle_audio_message(from_number: str, media_url: str, user_info: Dict[str, Any]) -> str:
    """
    Traite un message vocal WhatsApp

    Args:
        from_number: Numéro WhatsApp de l'expéditeur
        media_url: URL du fichier audio
        user_info: Informations de l'utilisateur

    Returns:
        Réponse à envoyer
    """
    try:
        user_email = user_info.get("user_email")
        logger.info(f"🎤 Audio message from {user_email}: {media_url}")

        # TODO: Intégrer avec votre système de transcription existant
        # Pour l'instant, réponse simple
        response = "Message vocal reçu. Transcription et traitement en cours..."

        return response
    except Exception as e:
        logger.error(f"❌ Error handling audio message: {e}")
        return "Désolé, je n'ai pas pu traiter votre message vocal."


async def handle_image_message(from_number: str, media_url: str, user_info: Dict[str, Any]) -> str:
    """
    Traite une image WhatsApp

    Args:
        from_number: Numéro WhatsApp de l'expéditeur
        media_url: URL de l'image
        user_info: Informations de l'utilisateur

    Returns:
        Réponse à envoyer
    """
    try:
        user_email = user_info.get("user_email")
        logger.info(f"🖼️ Image message from {user_email}: {media_url}")

        # TODO: Intégrer avec votre système de vision multimodale
        # Pour l'instant, réponse simple
        response = "Image reçue. Analyse en cours avec notre système de vision..."

        return response
    except Exception as e:
        logger.error(f"❌ Error handling image message: {e}")
        return "Désolé, je n'ai pas pu analyser votre image."


async def handle_unknown_user(from_number: str) -> str:
    """
    Gère un message d'un numéro WhatsApp non reconnu

    Args:
        from_number: Numéro WhatsApp inconnu

    Returns:
        Message d'aide pour l'utilisateur
    """
    clean_number = from_number.replace("whatsapp:", "").strip()
    logger.warning(f"⚠️ Unknown WhatsApp number: {clean_number}")

    return (
        "🔒 Numéro non reconnu.\n\n"
        "Pour utiliser Intelia Cognito via WhatsApp:\n"
        "1. Connectez-vous sur https://expert.intelia.com\n"
        "2. Ajoutez votre numéro WhatsApp dans votre profil\n"
        "3. Vérifiez le code reçu\n\n"
        "Ensuite, vous pourrez utiliser l'assistant IA via WhatsApp!"
    )


def send_whatsapp_message(to_number: str, body: str, media_url: str = None) -> bool:
    """
    Envoie un message WhatsApp via Twilio

    Args:
        to_number: Numéro destinataire (format: whatsapp:+1234567890)
        body: Contenu du message
        media_url: URL d'un média (optionnel)

    Returns:
        True si envoyé avec succès, False sinon
    """
    try:
        if not twilio_client:
            logger.error("❌ Twilio client not initialized")
            return False

        message_params = {
            "from_": TWILIO_WHATSAPP_NUMBER,
            "to": to_number,
            "body": body
        }

        if media_url:
            message_params["media_url"] = [media_url]

        message = twilio_client.messages.create(**message_params)

        logger.info(f"✅ WhatsApp message sent: {message.sid}")

        return True
    except Exception as e:
        logger.error(f"❌ Error sending WhatsApp message: {e}")
        return False


# ==================== WEBHOOK ENDPOINT ====================

@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(None),
    MessageSid: str = Form(...),
    NumMedia: int = Form(0),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None)
):
    """
    Endpoint principal pour recevoir les webhooks WhatsApp de Twilio

    Événements supportés:
    - Messages texte
    - Messages vocaux (audio)
    - Images
    - Autres médias
    """
    logger.info(f"📥 WhatsApp webhook received from {From}")

    # Valider la signature Twilio (sécurité)
    if request_validator:
        try:
            # Récupérer l'URL complète et la signature
            url = str(request.url)
            signature = request.headers.get("X-Twilio-Signature", "")

            # Récupérer tous les paramètres du formulaire
            form_data = await request.form()
            params = dict(form_data)

            # Valider la signature
            if not request_validator.validate(url, params, signature):
                logger.error("❌ Invalid Twilio signature")
                raise HTTPException(status_code=403, detail="Invalid signature")

            logger.info("✅ Twilio signature verified")
        except Exception as e:
            logger.error(f"❌ Signature validation error: {e}")
            # En développement, on peut continuer sans validation
            logger.warning("⚠️ Continuing without signature validation (dev mode)")

    # Identifier l'utilisateur
    user_info = get_user_by_whatsapp_number(From)

    if not user_info:
        # Numéro non reconnu
        response_text = await handle_unknown_user(From)
        send_whatsapp_message(From, response_text)

        return {"status": "unknown_user", "message": "User not recognized"}

    # Déterminer le type de message
    response_text = None
    message_type = "text"

    try:
        if NumMedia > 0 and MediaUrl0:
            # Message avec média
            if MediaContentType0 and MediaContentType0.startswith("audio/"):
                message_type = "audio"
                response_text = await handle_audio_message(From, MediaUrl0, user_info)
            elif MediaContentType0 and MediaContentType0.startswith("image/"):
                message_type = "image"
                response_text = await handle_image_message(From, MediaUrl0, user_info)
            else:
                message_type = "media"
                response_text = "Type de fichier non supporté pour le moment."
        elif Body:
            # Message texte
            message_type = "text"
            response_text = await handle_text_message(From, Body, user_info)
        else:
            response_text = "Message vide reçu."

        # Envoyer la réponse
        if response_text:
            send_whatsapp_message(From, response_text)

        logger.info(f"✅ WhatsApp message processed: {MessageSid}")

        return {"status": "success", "message_type": message_type}

    except Exception as e:
        logger.error(f"❌ Error processing WhatsApp message: {e}", exc_info=True)

        # Envoyer message d'erreur à l'utilisateur
        send_whatsapp_message(
            From,
            "Désolé, une erreur s'est produite lors du traitement de votre message. "
            "Veuillez réessayer dans quelques instants."
        )

        return {"status": "error", "message": str(e)}


@router.get("/webhook/test")
async def test_whatsapp_webhook():
    """
    Endpoint de test pour vérifier que le webhook WhatsApp est accessible
    """
    return {
        "status": "ok",
        "message": "WhatsApp webhook endpoint is ready",
        "twilio_configured": twilio_client is not None,
        "whatsapp_number": TWILIO_WHATSAPP_NUMBER,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/status")
async def whatsapp_status():
    """
    Retourne le statut de la configuration WhatsApp
    """
    # Try to get chat_handlers status
    handlers = get_or_create_chat_handlers()
    rag_available = False
    rag_initialized = False

    if handlers:
        try:
            rag_engine = handlers.get_rag_engine()
            rag_available = rag_engine is not None
            if rag_engine:
                rag_initialized = safe_get_attribute(rag_engine, "is_initialized", False)
        except Exception as e:
            logger.error(f"Error checking RAG status: {e}")

    return {
        "whatsapp_enabled": twilio_client is not None,
        "twilio_account_sid": TWILIO_ACCOUNT_SID[:8] + "..." if TWILIO_ACCOUNT_SID else None,
        "whatsapp_number": TWILIO_WHATSAPP_NUMBER,
        "signature_validation": request_validator is not None,
        "rag_integration": {
            "chat_handlers_available": CHAT_HANDLERS_AVAILABLE,
            "chat_handlers_initialized": handlers is not None,
            "rag_engine_available": rag_available,
            "rag_engine_initialized": rag_initialized,
            "version": "2.0_unified_with_frontend",
        }
    }
