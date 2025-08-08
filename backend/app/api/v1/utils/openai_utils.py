import openai
import os
import logging
from typing import Any, Dict, List, Optional
from functools import wraps
import time

# Configuration du logging
logger = logging.getLogger(__name__)

# ==================== AMÉLIORATION MAJEURE: Gestion centralisée de l'API key ====================
def _get_api_key() -> str:
    """
    ✅ AMÉLIORATION: Fonction centralisée pour la gestion de la clé API
    
    PROBLÈME RÉSOLU:
    - Code dupliqué dans safe_chat_completion et safe_embedding_create
    - Vérification répétée de OPENAI_API_KEY
    
    SOLUTION:
    - Fonction unique pour récupérer et valider la clé
    - Gestion d'erreurs centralisée
    - Configuration flexible via variables d'environnement
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.error("❌ OPENAI_API_KEY non configurée")
        raise RuntimeError(
            "OPENAI_API_KEY n'est pas configurée dans les variables d'environnement. "
            "Veuillez définir cette variable pour utiliser les services OpenAI."
        )
    
    if len(api_key.strip()) < 10:
        logger.error("❌ OPENAI_API_KEY semble invalide (trop courte)")
        raise RuntimeError("OPENAI_API_KEY semble invalide - vérifiez la configuration")
    
    return api_key.strip()

def _configure_openai_client() -> None:
    """
    ✅ AMÉLIORATION: Configuration centralisée du client OpenAI
    """
    try:
        api_key = _get_api_key()
        openai.api_key = api_key
        logger.debug("✅ Client OpenAI configuré")
    except Exception as e:
        logger.error(f"❌ Erreur configuration OpenAI: {e}")
        raise

# ==================== AMÉLIORATION: Décorateur pour retry et gestion d'erreurs ====================
def openai_retry(max_retries: int = 2, delay: float = 1.0):
    """
    ✅ NOUVEAU: Décorateur pour retry automatique des appels OpenAI
    
    Gère les erreurs temporaires comme:
    - Rate limiting
    - Erreurs réseau temporaires
    - Timeouts
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except openai.RateLimitError as e:
                    logger.warning(f"⚠️ Rate limit atteint (tentative {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        time.sleep(delay * (2 ** attempt))  # Backoff exponentiel
                        continue
                    last_exception = e
                    
                except openai.APITimeoutError as e:
                    logger.warning(f"⚠️ Timeout OpenAI (tentative {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        time.sleep(delay)
                        continue
                    last_exception = e
                    
                except openai.APIConnectionError as e:
                    logger.warning(f"⚠️ Erreur connexion OpenAI (tentative {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        time.sleep(delay)
                        continue
                    last_exception = e
                    
                except Exception as e:
                    # Pour les autres erreurs, pas de retry
                    logger.error(f"❌ Erreur OpenAI non-retry: {type(e).__name__}: {e}")
                    last_exception = e
                    break
            
            # Si on arrive ici, tous les retries ont échoué
            raise RuntimeError(f"Échec après {max_retries + 1} tentatives: {last_exception}")
        
        return wrapper
    return decorator

# ==================== FONCTION AMÉLIORÉE: safe_chat_completion ====================
@openai_retry(max_retries=2, delay=1.0)
def safe_chat_completion(**kwargs) -> Any:
    """
    Wrapper sécurisé pour openai.chat.completions.create
    
    AMÉLIORATIONS APPLIQUÉES:
    - Utilisation de _get_api_key() centralisée (plus de duplication)
    - Retry automatique avec backoff exponentiel
    - Gestion d'erreurs spécialisée par type
    - Validation des paramètres d'entrée
    - Logging détaillé pour debug
    """
    
    # ✅ AMÉLIORATION: Validation des paramètres essentiels
    if 'model' not in kwargs:
        kwargs['model'] = os.getenv('OPENAI_DEFAULT_MODEL', 'gpt-4o')
        logger.debug(f"🔧 Modèle par défaut utilisé: {kwargs['model']}")
    
    if 'messages' not in kwargs or not kwargs['messages']:
        raise ValueError("Le paramètre 'messages' est requis et ne peut pas être vide")
    
    # ✅ AMÉLIORATION: Configuration avec paramètres par défaut intelligents
    default_params = {
        'temperature': float(os.getenv('OPENAI_DEFAULT_TEMPERATURE', '0.7')),
        'max_tokens': int(os.getenv('OPENAI_DEFAULT_MAX_TOKENS', '500')),
        'timeout': int(os.getenv('OPENAI_DEFAULT_TIMEOUT', '30'))
    }
    
    # Appliquer les défauts seulement si non spécifiés
    for key, value in default_params.items():
        if key not in kwargs:
            kwargs[key] = value
    
    logger.debug(f"🤖 Appel OpenAI Chat: model={kwargs.get('model')}, temp={kwargs.get('temperature')}")
    
    try:
        # ✅ AMÉLIORATION: Configuration centralisée
        _configure_openai_client()
        
        # ✅ AMÉLIORATION: Mesure du temps de réponse
        start_time = time.time()
        response = openai.chat.completions.create(**kwargs)
        elapsed_time = time.time() - start_time
        
        logger.debug(f"✅ Réponse OpenAI Chat reçue en {elapsed_time:.2f}s")
        
        # ✅ AMÉLIORATION: Validation de la réponse
        if not response or not response.choices:
            raise RuntimeError("Réponse OpenAI vide ou malformée")
        
        # ✅ AMÉLIORATION: Logging des métriques d'usage
        if hasattr(response, 'usage') and response.usage:
            logger.debug(f"📊 Tokens utilisés: {response.usage.total_tokens} "
                        f"(prompt: {response.usage.prompt_tokens}, "
                        f"completion: {response.usage.completion_tokens})")
        
        return response
        
    except openai.AuthenticationError as e:
        logger.error("❌ Erreur authentification OpenAI - vérifiez votre clé API")
        raise RuntimeError(f"Authentification OpenAI échouée: {e}")
        
    except openai.PermissionDeniedError as e:
        logger.error("❌ Permission refusée OpenAI - vérifiez vos droits d'accès")
        raise RuntimeError(f"Permission OpenAI refusée: {e}")
        
    except openai.BadRequestError as e:
        logger.error(f"❌ Requête OpenAI invalide: {e}")
        raise RuntimeError(f"Requête OpenAI invalide: {e}")
        
    except Exception as e:
        logger.error(f"❌ Erreur inattendue OpenAI Chat: {type(e).__name__}: {e}")
        raise RuntimeError(f"Erreur lors de l'appel à OpenAI ChatCompletion: {e}")

# ==================== FONCTION AMÉLIORÉE: safe_embedding_create ====================
@openai_retry(max_retries=2, delay=0.5)
def safe_embedding_create(input: Any, model: str = "text-embedding-ada-002", **kwargs) -> List[List[float]]:
    """
    Wrapper sécurisé pour openai.embeddings.create
    
    AMÉLIORATIONS APPLIQUÉES:
    - Utilisation de _get_api_key() centralisée (plus de duplication)
    - Retry automatique pour erreurs temporaires
    - Validation et normalisation des inputs
    - Gestion d'erreurs spécialisée
    - Support des embeddings batch
    - Format de retour standardisé
    """
    
    # ✅ AMÉLIORATION: Validation et normalisation des inputs
    if not input:
        raise ValueError("Le paramètre 'input' ne peut pas être vide")
    
    # Normaliser input en liste si nécessaire
    if isinstance(input, str):
        input_list = [input]
        single_input = True
    elif isinstance(input, list):
        input_list = input
        single_input = False
    else:
        raise ValueError("Le paramètre 'input' doit être une string ou une liste de strings")
    
    # Validation du contenu
    for i, text in enumerate(input_list):
        if not isinstance(text, str):
            raise ValueError(f"Élément {i} de input doit être une string")
        if not text.strip():
            logger.warning(f"⚠️ Élément {i} de input est vide")
    
    # ✅ AMÉLIORATION: Filtrer les textes vides
    filtered_input = [text.strip() for text in input_list if text.strip()]
    if not filtered_input:
        raise ValueError("Aucun texte valide après filtrage")
    
    # ✅ AMÉLIORATION: Configuration avec modèle par défaut
    if not model:
        model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002')
    
    logger.debug(f"🔤 Appel OpenAI Embeddings: model={model}, inputs={len(filtered_input)}")
    
    try:
        # ✅ AMÉLIORATION: Configuration centralisée
        _configure_openai_client()
        
        # ✅ AMÉLIORATION: Gestion des grandes listes (batch processing)
        max_batch_size = int(os.getenv('OPENAI_EMBEDDING_BATCH_SIZE', '100'))
        all_embeddings = []
        
        for i in range(0, len(filtered_input), max_batch_size):
            batch = filtered_input[i:i + max_batch_size]
            
            start_time = time.time()
            response = openai.embeddings.create(
                input=batch,
                model=model,
                **kwargs
            )
            elapsed_time = time.time() - start_time
            
            logger.debug(f"✅ Batch embeddings {i//max_batch_size + 1} traité en {elapsed_time:.2f}s")
            
            # ✅ AMÉLIORATION: Extraction robuste des embeddings avec compatibilité
            if hasattr(response, 'data') and response.data:
                batch_embeddings = [item.embedding for item in response.data]
            elif isinstance(response, dict) and 'data' in response:
                batch_embeddings = [
                    item.get('embedding') if isinstance(item, dict) else item.embedding 
                    for item in response['data']
                ]
            else:
                raise RuntimeError("Format de réponse OpenAI Embeddings non reconnu")
            
            all_embeddings.extend(batch_embeddings)
        
        # ✅ AMÉLIORATION: Validation des embeddings retournés
        if len(all_embeddings) != len(filtered_input):
            raise RuntimeError(f"Nombre d'embeddings ({len(all_embeddings)}) "
                             f"ne correspond pas aux inputs ({len(filtered_input)})")
        
        # Vérification de la dimension des embeddings
        if all_embeddings and all_embeddings[0]:
            embedding_dim = len(all_embeddings[0])
            logger.debug(f"📊 Embeddings générés: {len(all_embeddings)} vecteurs de dimension {embedding_dim}")
        
        # ✅ AMÉLIORATION: Retour adapté au format d'entrée
        if single_input:
            return all_embeddings[0] if all_embeddings else []
        else:
            return all_embeddings
        
    except openai.AuthenticationError as e:
        logger.error("❌ Erreur authentification OpenAI Embeddings")
        raise RuntimeError(f"Authentification OpenAI échouée: {e}")
        
    except openai.InvalidRequestError as e:
        logger.error(f"❌ Requête OpenAI Embeddings invalide: {e}")
        raise RuntimeError(f"Requête OpenAI Embeddings invalide: {e}")
        
    except Exception as e:
        logger.error(f"❌ Erreur inattendue OpenAI Embeddings: {type(e).__name__}: {e}")
        raise RuntimeError(f"Erreur lors de l'appel à OpenAI Embedding: {e}")

# ==================== NOUVELLES FONCTIONNALITÉS UTILITAIRES ====================
def test_openai_connection() -> Dict[str, Any]:
    """
    ✅ NOUVELLE FONCTIONNALITÉ: Test de connexion OpenAI
    Utile pour les diagnostics et la validation de configuration
    """
    try:
        logger.info("🔧 Test de connexion OpenAI...")
        
        # Test simple avec un prompt minimal
        response = safe_chat_completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5,
            temperature=0
        )
        
        return {
            "status": "success",
            "message": "Connexion OpenAI fonctionnelle",
            "model_tested": "gpt-3.5-turbo",
            "response_preview": response.choices[0].message.content[:50] if response.choices else "N/A"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Échec connexion OpenAI: {str(e)}",
            "error_type": type(e).__name__
        }

def get_openai_models() -> List[str]:
    """
    ✅ NOUVELLE FONCTIONNALITÉ: Liste des modèles OpenAI disponibles
    """
    try:
        _configure_openai_client()
        models = openai.models.list()
        return [model.id for model in models.data if model.id]
    except Exception as e:
        logger.error(f"❌ Erreur récupération modèles: {e}")
        return []

def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    ✅ NOUVELLE FONCTIONNALITÉ: Estimation approximative du nombre de tokens
    Utile pour éviter les dépassements de limites
    """
    # Estimation grossière : ~4 caractères par token pour l'anglais/français
    # Plus précis avec tiktoken si disponible
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except ImportError:
        # Fallback vers estimation approximative
        return len(text) // 4
    except Exception:
        # Fallback sécurisé
        return len(text) // 4

# ==================== CONFIGURATION ET CONSTANTES ====================
# ✅ AMÉLIORATION: Constantes configurables
DEFAULT_MODELS = {
    "chat": os.getenv('OPENAI_DEFAULT_CHAT_MODEL', 'gpt-4o'),
    "embedding": os.getenv('OPENAI_DEFAULT_EMBEDDING_MODEL', 'text-embedding-ada-002')
}

MAX_TOKENS_LIMITS = {
    "gpt-3.5-turbo": 4096,
    "gpt-4": 8192,
    "gpt-4o": 4096,
    "gpt-4-turbo": 128000
}

def get_model_max_tokens(model: str) -> int:
    """
    ✅ NOUVELLE FONCTIONNALITÉ: Récupère la limite de tokens pour un modèle
    """
    return MAX_TOKENS_LIMITS.get(model, 4096)

# ==================== LOGGING ET DIAGNOSTICS ====================
def get_openai_status() -> Dict[str, Any]:
    """
    ✅ NOUVELLE FONCTIONNALITÉ: Status complet du système OpenAI
    """
    return {
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "default_models": DEFAULT_MODELS,
        "max_tokens_limits": MAX_TOKENS_LIMITS,
        "retry_config": {
            "max_retries": 2,
            "base_delay": 1.0
        },
        "batch_config": {
            "embedding_batch_size": os.getenv('OPENAI_EMBEDDING_BATCH_SIZE', '100')
        }
    }