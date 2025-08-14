# -*- coding: utf-8 -*-
# ==================== IMPORTS - MUST BE AT THE TOP ====================
import openai
import os
import logging
import re
from typing import Any, Dict, List, Optional
from functools import wraps
import time
import json
import httpx

# Configuration du logging
logger = logging.getLogger(__name__)

# --- Helper de détection d'erreur "temperature non supportée" ---
def _is_temp_unsupported_error(msg: str) -> bool:
    """Détecte les messages style:
    "Unsupported value: 'temperature' does not support 0.1 with this model. Only the default (1) value is supported."
    """
    if not msg:
        return False
    return bool(re.search(r"temperature.+(unsupported|does\s*not\s*support|only\s*the\s*default)", str(msg), re.I))

# ==================== NOUVEAU: HELPERS COMPATIBILITY max_completion_tokens ====================
# Familles de modèles qui exigent max_completion_tokens sur /chat/completions
# NOTE: le fichier original contenait ici les constantes et helpers nécessaires.
# Nous conservons tout le code original en dessous (inchangé),
# puis nous redéfinissons proprement les fonctions clés plus bas pour compatibilité GPT‑5.

# ...
# (Tout votre code original et vos helpers restent ici, inchangés.)
# ...

# ==================== AMÉLIORATION: Décorateur pour retry et gestion d'erreurs ====================
def openai_retry(max_retries: int = 2, delay: float = 1.0):
    """
    Décorateur pour retry automatique des appels OpenAI.
    (Conservé depuis le fichier original.)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay)
                        continue
                    raise
            raise RuntimeError(f"Échec après {max_retries + 1} tentatives: {last_exception}")
        return wrapper
    return decorator

# ==================== PLACEHOLDER des helpers originaux ====================
# (Dans votre fichier réel, ces fonctions existent déjà. Nous laissons ces placeholders
# uniquement pour rendre ce document autoportant dans la preview.)

def _uses_mct(model: str) -> bool:
    prefixes = ("gpt-5", "gpt-4o", "o3", "o4")
    return any(model.startswith(p) for p in prefixes)

def _completion_param_name(model: str) -> str:
    return "max_completion_tokens" if _uses_mct(model) else "max_tokens"

def _get_safe_temperature(temperature: float, model: str = None) -> Optional[float]:
    if temperature is None:
        return None
    if os.getenv("OPENAI_FORCE_DEFAULT_TEMPERATURE", "").lower() == "true":
        return None
    restricted = [m.strip() for m in os.getenv("OPENAI_RESTRICTED_TEMP_MODELS", "").split(",") if m.strip()]
    if model and any(model.startswith(r) for r in restricted):
        return None
    try:
        t = float(temperature)
    except Exception:
        return None
    if t < 0.0 or t > 2.0:
        return None
    return t

def estimate_tokens(text: str, model: str = "") -> int:
    # Approx rapide: ~4 chars/token
    return max(1, int(len(text) / 4))

def get_model_max_tokens(model: str) -> int:
    # Valeurs par défaut raisonnables
    return {
        "gpt-3.5-turbo": 4096,
        "gpt-4": 8192,
        "gpt-4o": 8192,
        "gpt-4o-mini": 4096,
        "gpt-5": 8192,
        "gpt-5-mini": 4096,
    }.get(model, 4096)

# ==================== PATCH GPT‑5: RÉÉCRITURES COMPLÈTES DES FONCTIONS CLÉS ====================

@openai_retry(max_retries=2, delay=1.0)
def complete_with_cot(prompt: str, temperature: float = 0.3, max_tokens: Optional[int] = None, 
                      model: Optional[str] = None, parse_cot: bool = True) -> Dict[str, Any]:
    """
    Completion CoT (Chain‑of‑Thought) robuste et compatible GPT‑5.
    - Respecte la température si supportée, sinon la retire
    - Choix auto de max_tokens / max_completion_tokens
    - Laisse le reste du pipeline inchangé
    """
    if not prompt or not prompt.strip():
        raise ValueError("Le prompt CoT ne peut pas être vide")
    if model is None:
        model = os.getenv('OPENAI_COT_MODEL', os.getenv('DEFAULT_MODEL', 'gpt-5'))

    if max_tokens is None:
        max_tokens = int(os.getenv('OPENAI_COT_MAX_TOKENS', '800'))
        available = get_model_max_tokens(model) - estimate_tokens(prompt, model) - 150
        if available > 0:
            max_tokens = min(max_tokens, available)

    messages = [
        {"role": "system", "content": (
            "Tu es un expert vétérinaire avicole avec une approche méthodologique rigoureuse. "
            "Suis précisément la structure de raisonnement demandée avec les balises XML. "
            "Reste factuel, précis et professionnel dans ton analyse."
        )},
        {"role": "user", "content": prompt.strip()},
    ]

    param_name = _completion_param_name(model)
    call_kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        param_name: max_tokens,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.1,
    }

    safe_temp = _get_safe_temperature(temperature, model)
    if safe_temp is not None:
        call_kwargs["temperature"] = safe_temp

    try:
        response = openai.chat.completions.create(**call_kwargs)
    except Exception as e:
        msg = str(e)
        if _is_temp_unsupported_error(msg):
            logger.warning(f"[OpenAI] Température non supportée par {model} → retry sans 'temperature'")
            call_kwargs.pop("temperature", None)
            response = openai.chat.completions.create(**call_kwargs)
        elif "unsupported_parameter" in msg.lower() and ("max_tokens" in msg.lower() or "max_completion_tokens" in msg.lower()):
            other = "max_tokens" if param_name == "max_completion_tokens" else "max_completion_tokens"
            call_kwargs[other] = call_kwargs.pop(param_name)
            response = openai.chat.completions.create(**call_kwargs)
        else:
            raise

    if not response or not getattr(response, 'choices', None):
        raise RuntimeError("Réponse OpenAI CoT vide")

    raw_content = response.choices[0].message.content if response.choices else None
    if not raw_content:
        raise RuntimeError("Contenu CoT vide")

    result: Dict[str, Any] = {
        "raw_response": raw_content.strip(),
        "model_used": model,
        "temperature": safe_temp if safe_temp is not None else "default",
    }
    if hasattr(response, "usage") and response.usage:
        try:
            result["token_usage"] = {
                "total": response.usage.total_tokens,
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
            }
        except Exception:
            pass
    return result

@openai_retry(max_retries=2, delay=1.0)
def complete(messages, model: str, temperature: Optional[float] = 0.2, max_tokens: int = 800,
             timeout: float = 30.0, extra: Optional[Dict] = None) -> Dict:
    """
    Appel /v1/chat/completions via HTTPX, compatible anciens & nouveaux modèles.
    - Choix auto de la clé tokens (max_tokens vs max_completion_tokens)
    - Température respectée si supportée, sinon retirée
    - Retry si temperature non supportée ou si mauvais paramètre tokens
    """
    extra = extra or {}
    param_name = _completion_param_name(model)
    safe_temp = _get_safe_temperature(temperature, model) if temperature is not None else None

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        param_name: max_tokens,
        **{k: v for k, v in (extra or {}).items() if v is not None},
    }
    if safe_temp is not None:
        payload["temperature"] = safe_temp

    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json",
    }
    url = "https://api.openai.com/v1/chat/completions"

    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers, json=payload)

    if r.status_code == 200:
        return r.json()

    # Décodage erreur
    try:
        err_obj = r.json()
        err_msg = (err_obj.get("error") or {}).get("message", "") or r.text
    except Exception:
        err_obj, err_msg = {}, r.text or ""

    # Retry: mauvais paramètre tokens
    if "unsupported_parameter" in (err_msg or "").lower() and ("max_tokens" in err_msg.lower() or "max_completion_tokens" in err_msg.lower()):
        wrong_param = err_obj.get("error", {}).get("param") if isinstance(err_obj, dict) else None
        other = "max_completion_tokens" if (wrong_param or param_name) == "max_tokens" else "max_tokens"
        if other != param_name:
            payload.pop(param_name, None)
            payload[other] = max_tokens
            logger.warning("⚠️ OpenAI param '%s' non supporté pour %s – retry avec '%s'", wrong_param or param_name, model, other)
            with httpx.Client(timeout=timeout) as client:
                r2 = client.post(url, headers=headers, json=payload)
            if r2.status_code == 200:
                return r2.json()
            try:
                err_msg = (r2.json().get("error") or {}).get("message", "") or r2.text
            except Exception:
                err_msg = r2.text or ""

    # Retry: température non supportée
    if _is_temp_unsupported_error(err_msg):
        logger.warning(f"[OpenAI] Température non supportée par {model} → retry sans 'temperature'")
        payload.pop("temperature", None)
        with httpx.Client(timeout=timeout) as client:
            r3 = client.post(url, headers=headers, json=payload)
        if r3.status_code == 200:
            return r3.json()

    # Sinon, on remonte l'erreur
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Requête OpenAI invalide: {e.response.text}") from None
    return r.json()

@openai_retry(max_retries=2, delay=1.0)
def complete_text(prompt: str, temperature: float = 0.2, max_tokens: Optional[int] = None, model: Optional[str] = None) -> str:
    """
    Wrapper historique: complete(prompt) -> str
    - Passe par complete(...) avec température sécurisée
    - Conserve le reste des comportements
    """
    if not prompt or not prompt.strip():
        raise ValueError("Le prompt ne peut pas être vide")
    if model is None:
        model = os.getenv('OPENAI_SYNTHESIS_MODEL', os.getenv('DEFAULT_MODEL', 'gpt-5'))

    safe_temp = _get_safe_temperature(temperature, model)

    if max_tokens is None:
        plen = len(prompt)
        if plen < 500:
            max_tokens = 300
        elif plen < 1500:
            max_tokens = 500
        elif plen < 3000:
            max_tokens = 700
        else:
            max_tokens = 800
        available = get_model_max_tokens(model) - estimate_tokens(prompt, model) - 100
        if available > 0:
            max_tokens = min(max_tokens, available)

    messages = [
        {"role": "system", "content": (
            "Tu es un expert en synthèse de contenu technique avicole. "
            "Réponds de manière concise, précise et professionnelle. "
            "Utilise un français clair et structure ton texte avec du Markdown si approprié."
        )},
        {"role": "user", "content": prompt.strip()},
    ]

    response = complete(
        messages=messages,
        model=model,
        temperature=safe_temp if safe_temp is not None else None,
        max_tokens=max_tokens,
        timeout=float(os.getenv('OPENAI_DEFAULT_TIMEOUT', '30')),
    )

    if not response or not response.get("choices"):
        raise RuntimeError("Réponse OpenAI vide")

    choice = (response.get("choices") or [{}])[0]
    content = ((choice.get("message") or {}).get("content")) or choice.get("text") or ""
    if not content:
        logger.error(f"[OpenAI] Réponse sans 'content'. Aperçu: {str(response)[:500]}")
        raise RuntimeError("Contenu de réponse vide")
    return content.strip()

@openai_retry(max_retries=2, delay=1.0)
def safe_chat_completion(**kwargs) -> Any:
    """
    Wrapper sécurisé pour openai.chat.completions.create (SDK)
    - Compat GPT‑5: température sécurisée + retry si non supportée
    - Bascule auto max_tokens / max_completion_tokens
    """
    if 'model' not in kwargs:
        kwargs['model'] = os.getenv('DEFAULT_MODEL', 'gpt-5')
        logger.debug(f"🔧 Modèle par défaut utilisé: {kwargs['model']}")
    if 'messages' not in kwargs or not kwargs['messages']:
        raise ValueError("Le paramètre 'messages' est requis et ne peut pas être vide")

    model = kwargs['model']
    kwargs.setdefault('max_tokens', int(os.getenv('OPENAI_DEFAULT_MAX_TOKENS', '500')))
    timeout = int(os.getenv('OPENAI_DEFAULT_TIMEOUT', '30'))

    # Harmonisation des tokens
    param_name = _completion_param_name(model)
    if 'max_tokens' in kwargs and param_name == 'max_completion_tokens':
        kwargs['max_completion_tokens'] = kwargs.pop('max_tokens')
    elif 'max_completion_tokens' in kwargs and param_name == 'max_tokens':
        kwargs['max_tokens'] = kwargs.pop('max_completion_tokens')

    # Température sécurisée
    if 'temperature' in kwargs:
        t = kwargs['temperature']
        safe = _get_safe_temperature(t, model)
        if safe is None:
            kwargs.pop('temperature', None)
        else:
            kwargs['temperature'] = safe

    logger.debug(f"🤖 Appel OpenAI Chat: model={model}, temp={kwargs.get('temperature', 'default')}")

    start = time.time()
    try:
        resp = openai.chat.completions.create(timeout=timeout, **kwargs)
    except Exception as e:
        error_msg = str(e).lower()
        # Retry température non supportée
        if _is_temp_unsupported_error(error_msg):
            logger.warning(f"[OpenAI] Température non supportée par {model} → retry sans 'temperature'")
            kwargs.pop('temperature', None)
            resp = openai.chat.completions.create(timeout=timeout, **kwargs)
        # Retry mauvais paramètre de tokens
        elif "unsupported_parameter" in error_msg and ("max_tokens" in error_msg or "max_completion_tokens" in error_msg):
            if 'max_tokens' in kwargs:
                kwargs['max_completion_tokens'] = kwargs.pop('max_tokens')
            elif 'max_completion_tokens' in kwargs:
                kwargs['max_tokens'] = kwargs.pop('max_completion_tokens')
            resp = openai.chat.completions.create(timeout=timeout, **kwargs)
        else:
            raise

    logger.debug(f"✅ Réponse OpenAI Chat reçue en {time.time() - start:.2f}s")
    if not resp or not getattr(resp, 'choices', None):
        raise RuntimeError("Réponse OpenAI vide ou malformée")
    return resp

# ==================== (Optionnel) Autres wrappers conservés ====================
@openai_retry(max_retries=2, delay=0.5)
def safe_embedding_create(input: Any, model: str = None, **kwargs) -> List[List[float]]:
    """Wrapper embeddings conservé; compatible avec SDK actuel."""
    if not input:
        raise ValueError("Le paramètre 'input' ne peut pas être vide")
    if isinstance(input, str):
        texts, single = [input], True
    elif isinstance(input, list):
        texts, single = input, False
    else:
        raise ValueError("'input' doit être str ou List[str]")
    texts = [t.strip() for t in texts if isinstance(t, str) and t.strip()]
    if not texts:
        raise ValueError("Aucun texte valide après filtrage")
    if not model:
        model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')

    max_batch = int(os.getenv('OPENAI_EMBEDDING_BATCH_SIZE', '100'))
    all_vecs: List[List[float]] = []
    for i in range(0, len(texts), max_batch):
        batch = texts[i:i+max_batch]
        resp = openai.embeddings.create(input=batch, model=model, **kwargs)
        data = resp.data if hasattr(resp, 'data') else (resp.get('data', []) if isinstance(resp, dict) else [])
        vecs = [item.embedding if hasattr(item, 'embedding') else item.get('embedding') for item in data]
        all_vecs.extend(vecs)
    return all_vecs[0] if single else all_vecs

# ==================== Tests rapides / Statuts (conservés) ====================
def test_openai_connection() -> Dict[str, Any]:
    try:
        test_model = os.getenv("OPENAI_TEST_MODEL", "gpt-5")
        try:
            resp = safe_chat_completion(model=test_model, messages=[{"role": "user", "content": "Test"}], max_tokens=5)
        except Exception:
            resp = safe_chat_completion(model="gpt-4o-mini", messages=[{"role": "user", "content": "Test"}], max_tokens=5)
            test_model = "gpt-4o-mini"
        return {
            "status": "success",
            "message": "Connexion OpenAI fonctionnelle",
            "model_tested": test_model,
            "response_preview": resp.choices[0].message.content[:50] if getattr(resp, 'choices', None) else "N/A",
        }
    except Exception as e:
        return {"status": "error", "message": f"Échec connexion OpenAI: {e}", "error_type": type(e).__name__}

def get_openai_models() -> List[str]:
    try:
        models = openai.models.list()
        return [m.id for m in models.data if getattr(m, 'id', None)]
    except Exception as e:
        logger.error(f"⛔ Erreur récupération modèles: {e}")
        return []

def get_openai_status() -> Dict[str, Any]:
    return {
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "temperature_safety": True,
        "default_model": os.getenv('DEFAULT_MODEL', 'gpt-5'),
    }
# -*- coding: utf-8 -*-
# ==================== IMPORTS - MUST BE AT THE TOP ====================
import openai
import os
import logging
import re
from typing import Any, Dict, List, Optional
from functools import wraps
import time
import json
import httpx

# Configuration du logging
logger = logging.getLogger(__name__)

# --- Helper de détection d'erreur "temperature non supportée" ---
def _is_temp_unsupported_error(msg: str) -> bool:
    """Détecte les messages style:
    "Unsupported value: 'temperature' does not support 0.1 with this model. Only the default (1) value is supported."
    """
    if not msg:
        return False
    return bool(re.search(r"temperature.+(unsupported|does\s*not\s*support|only\s*the\s*default)", str(msg), re.I))

# ==================== NOUVEAU: HELPERS COMPATIBILITY max_completion_tokens ====================
# Familles de modèles qui exigent max_completion_tokens sur /chat/completions
# NOTE: le fichier original contenait ici les constantes et helpers nécessaires.
# Nous conservons tout le code original en dessous (inchangé),
# puis nous redéfinissons proprement les fonctions clés plus bas pour compatibilité GPT‑5.

# ...
# (Tout votre code original et vos helpers restent ici, inchangés.)
# ...

# ==================== AMÉLIORATION: Décorateur pour retry et gestion d'erreurs ====================
def openai_retry(max_retries: int = 2, delay: float = 1.0):
    """
    Décorateur pour retry automatique des appels OpenAI.
    (Conservé depuis le fichier original.)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay)
                        continue
                    raise
            raise RuntimeError(f"Échec après {max_retries + 1} tentatives: {last_exception}")
        return wrapper
    return decorator

# ==================== PLACEHOLDER des helpers originaux ====================
# (Dans votre fichier réel, ces fonctions existent déjà. Nous laissons ces placeholders
# uniquement pour rendre ce document autoportant dans la preview.)

def _uses_mct(model: str) -> bool:
    prefixes = ("gpt-5", "gpt-4o", "o3", "o4")
    return any(model.startswith(p) for p in prefixes)

def _completion_param_name(model: str) -> str:
    return "max_completion_tokens" if _uses_mct(model) else "max_tokens"

def _get_safe_temperature(temperature: float, model: str = None) -> Optional[float]:
    if temperature is None:
        return None
    if os.getenv("OPENAI_FORCE_DEFAULT_TEMPERATURE", "").lower() == "true":
        return None
    restricted = [m.strip() for m in os.getenv("OPENAI_RESTRICTED_TEMP_MODELS", "").split(",") if m.strip()]
    if model and any(model.startswith(r) for r in restricted):
        return None
    try:
        t = float(temperature)
    except Exception:
        return None
    if t < 0.0 or t > 2.0:
        return None
    return t

def estimate_tokens(text: str, model: str = "") -> int:
    # Approx rapide: ~4 chars/token
    return max(1, int(len(text) / 4))

def get_model_max_tokens(model: str) -> int:
    # Valeurs par défaut raisonnables
    return {
        "gpt-3.5-turbo": 4096,
        "gpt-4": 8192,
        "gpt-4o": 8192,
        "gpt-4o-mini": 4096,
        "gpt-5": 8192,
        "gpt-5-mini": 4096,
    }.get(model, 4096)

# ==================== PATCH GPT‑5: RÉÉCRITURES COMPLÈTES DES FONCTIONS CLÉS ====================

@openai_retry(max_retries=2, delay=1.0)
def complete_with_cot(prompt: str, temperature: float = 0.3, max_tokens: Optional[int] = None, 
                      model: Optional[str] = None, parse_cot: bool = True) -> Dict[str, Any]:
    """
    Completion CoT (Chain‑of‑Thought) robuste et compatible GPT‑5.
    - Respecte la température si supportée, sinon la retire
    - Choix auto de max_tokens / max_completion_tokens
    - Laisse le reste du pipeline inchangé
    """
    if not prompt or not prompt.strip():
        raise ValueError("Le prompt CoT ne peut pas être vide")
    if model is None:
        model = os.getenv('OPENAI_COT_MODEL', os.getenv('DEFAULT_MODEL', 'gpt-5'))

    if max_tokens is None:
        max_tokens = int(os.getenv('OPENAI_COT_MAX_TOKENS', '800'))
        available = get_model_max_tokens(model) - estimate_tokens(prompt, model) - 150
        if available > 0:
            max_tokens = min(max_tokens, available)

    messages = [
        {"role": "system", "content": (
            "Tu es un expert vétérinaire avicole avec une approche méthodologique rigoureuse. "
            "Suis précisément la structure de raisonnement demandée avec les balises XML. "
            "Reste factuel, précis et professionnel dans ton analyse."
        )},
        {"role": "user", "content": prompt.strip()},
    ]

    param_name = _completion_param_name(model)
    call_kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        param_name: max_tokens,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.1,
    }

    safe_temp = _get_safe_temperature(temperature, model)
    if safe_temp is not None:
        call_kwargs["temperature"] = safe_temp

    try:
        response = openai.chat.completions.create(**call_kwargs)
    except Exception as e:
        msg = str(e)
        if _is_temp_unsupported_error(msg):
            logger.warning(f"[OpenAI] Température non supportée par {model} → retry sans 'temperature'")
            call_kwargs.pop("temperature", None)
            response = openai.chat.completions.create(**call_kwargs)
        elif "unsupported_parameter" in msg.lower() and ("max_tokens" in msg.lower() or "max_completion_tokens" in msg.lower()):
            other = "max_tokens" if param_name == "max_completion_tokens" else "max_completion_tokens"
            call_kwargs[other] = call_kwargs.pop(param_name)
            response = openai.chat.completions.create(**call_kwargs)
        else:
            raise

    if not response or not getattr(response, 'choices', None):
        raise RuntimeError("Réponse OpenAI CoT vide")

    raw_content = response.choices[0].message.content if response.choices else None
    if not raw_content:
        raise RuntimeError("Contenu CoT vide")

    result: Dict[str, Any] = {
        "raw_response": raw_content.strip(),
        "model_used": model,
        "temperature": safe_temp if safe_temp is not None else "default",
    }
    if hasattr(response, "usage") and response.usage:
        try:
            result["token_usage"] = {
                "total": response.usage.total_tokens,
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
            }
        except Exception:
            pass
    return result

@openai_retry(max_retries=2, delay=1.0)
def complete(messages, model: str, temperature: Optional[float] = 0.2, max_tokens: int = 800,
             timeout: float = 30.0, extra: Optional[Dict] = None) -> Dict:
    """
    Appel /v1/chat/completions via HTTPX, compatible anciens & nouveaux modèles.
    - Choix auto de la clé tokens (max_tokens vs max_completion_tokens)
    - Température respectée si supportée, sinon retirée
    - Retry si temperature non supportée ou si mauvais paramètre tokens
    """
    extra = extra or {}
    param_name = _completion_param_name(model)
    safe_temp = _get_safe_temperature(temperature, model) if temperature is not None else None

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        param_name: max_tokens,
        **{k: v for k, v in (extra or {}).items() if v is not None},
    }
    if safe_temp is not None:
        payload["temperature"] = safe_temp

    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json",
    }
    url = "https://api.openai.com/v1/chat/completions"

    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers, json=payload)

    if r.status_code == 200:
        return r.json()

    # Décodage erreur
    try:
        err_obj = r.json()
        err_msg = (err_obj.get("error") or {}).get("message", "") or r.text
    except Exception:
        err_obj, err_msg = {}, r.text or ""

    # Retry: mauvais paramètre tokens
    if "unsupported_parameter" in (err_msg or "").lower() and ("max_tokens" in err_msg.lower() or "max_completion_tokens" in err_msg.lower()):
        wrong_param = err_obj.get("error", {}).get("param") if isinstance(err_obj, dict) else None
        other = "max_completion_tokens" if (wrong_param or param_name) == "max_tokens" else "max_tokens"
        if other != param_name:
            payload.pop(param_name, None)
            payload[other] = max_tokens
            logger.warning("⚠️ OpenAI param '%s' non supporté pour %s – retry avec '%s'", wrong_param or param_name, model, other)
            with httpx.Client(timeout=timeout) as client:
                r2 = client.post(url, headers=headers, json=payload)
            if r2.status_code == 200:
                return r2.json()
            try:
                err_msg = (r2.json().get("error") or {}).get("message", "") or r2.text
            except Exception:
                err_msg = r2.text or ""

    # Retry: température non supportée
    if _is_temp_unsupported_error(err_msg):
        logger.warning(f"[OpenAI] Température non supportée par {model} → retry sans 'temperature'")
        payload.pop("temperature", None)
        with httpx.Client(timeout=timeout) as client:
            r3 = client.post(url, headers=headers, json=payload)
        if r3.status_code == 200:
            return r3.json()

    # Sinon, on remonte l'erreur
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Requête OpenAI invalide: {e.response.text}") from None
    return r.json()

@openai_retry(max_retries=2, delay=1.0)
def complete_text(prompt: str, temperature: float = 0.2, max_tokens: Optional[int] = None, model: Optional[str] = None) -> str:
    """
    Wrapper historique: complete(prompt) -> str
    - Passe par complete(...) avec température sécurisée
    - Conserve le reste des comportements
    """
    if not prompt or not prompt.strip():
        raise ValueError("Le prompt ne peut pas être vide")
    if model is None:
        model = os.getenv('OPENAI_SYNTHESIS_MODEL', os.getenv('DEFAULT_MODEL', 'gpt-5'))

    safe_temp = _get_safe_temperature(temperature, model)

    if max_tokens is None:
        plen = len(prompt)
        if plen < 500:
            max_tokens = 300
        elif plen < 1500:
            max_tokens = 500
        elif plen < 3000:
            max_tokens = 700
        else:
            max_tokens = 800
        available = get_model_max_tokens(model) - estimate_tokens(prompt, model) - 100
        if available > 0:
            max_tokens = min(max_tokens, available)

    messages = [
        {"role": "system", "content": (
            "Tu es un expert en synthèse de contenu technique avicole. "
            "Réponds de manière concise, précise et professionnelle. "
            "Utilise un français clair et structure ton texte avec du Markdown si approprié."
        )},
        {"role": "user", "content": prompt.strip()},
    ]

    response = complete(
        messages=messages,
        model=model,
        temperature=safe_temp if safe_temp is not None else None,
        max_tokens=max_tokens,
        timeout=float(os.getenv('OPENAI_DEFAULT_TIMEOUT', '30')),
    )

    if not response or not response.get("choices"):
        raise RuntimeError("Réponse OpenAI vide")

    choice = (response.get("choices") or [{}])[0]
    content = ((choice.get("message") or {}).get("content")) or choice.get("text") or ""
    if not content:
        logger.error(f"[OpenAI] Réponse sans 'content'. Aperçu: {str(response)[:500]}")
        raise RuntimeError("Contenu de réponse vide")
    return content.strip()

@openai_retry(max_retries=2, delay=1.0)
def safe_chat_completion(**kwargs) -> Any:
    """
    Wrapper sécurisé pour openai.chat.completions.create (SDK)
    - Compat GPT‑5: température sécurisée + retry si non supportée
    - Bascule auto max_tokens / max_completion_tokens
    """
    if 'model' not in kwargs:
        kwargs['model'] = os.getenv('DEFAULT_MODEL', 'gpt-5')
        logger.debug(f"🔧 Modèle par défaut utilisé: {kwargs['model']}")
    if 'messages' not in kwargs or not kwargs['messages']:
        raise ValueError("Le paramètre 'messages' est requis et ne peut pas être vide")

    model = kwargs['model']
    kwargs.setdefault('max_tokens', int(os.getenv('OPENAI_DEFAULT_MAX_TOKENS', '500')))
    timeout = int(os.getenv('OPENAI_DEFAULT_TIMEOUT', '30'))

    # Harmonisation des tokens
    param_name = _completion_param_name(model)
    if 'max_tokens' in kwargs and param_name == 'max_completion_tokens':
        kwargs['max_completion_tokens'] = kwargs.pop('max_tokens')
    elif 'max_completion_tokens' in kwargs and param_name == 'max_tokens':
        kwargs['max_tokens'] = kwargs.pop('max_completion_tokens')

    # Température sécurisée
    if 'temperature' in kwargs:
        t = kwargs['temperature']
        safe = _get_safe_temperature(t, model)
        if safe is None:
            kwargs.pop('temperature', None)
        else:
            kwargs['temperature'] = safe

    logger.debug(f"🤖 Appel OpenAI Chat: model={model}, temp={kwargs.get('temperature', 'default')}")

    start = time.time()
    try:
        resp = openai.chat.completions.create(timeout=timeout, **kwargs)
    except Exception as e:
        error_msg = str(e).lower()
        # Retry température non supportée
        if _is_temp_unsupported_error(error_msg):
            logger.warning(f"[OpenAI] Température non supportée par {model} → retry sans 'temperature'")
            kwargs.pop('temperature', None)
            resp = openai.chat.completions.create(timeout=timeout, **kwargs)
        # Retry mauvais paramètre de tokens
        elif "unsupported_parameter" in error_msg and ("max_tokens" in error_msg or "max_completion_tokens" in error_msg):
            if 'max_tokens' in kwargs:
                kwargs['max_completion_tokens'] = kwargs.pop('max_tokens')
            elif 'max_completion_tokens' in kwargs:
                kwargs['max_tokens'] = kwargs.pop('max_completion_tokens')
            resp = openai.chat.completions.create(timeout=timeout, **kwargs)
        else:
            raise

    logger.debug(f"✅ Réponse OpenAI Chat reçue en {time.time() - start:.2f}s")
    if not resp or not getattr(resp, 'choices', None):
        raise RuntimeError("Réponse OpenAI vide ou malformée")
    return resp

# ==================== (Optionnel) Autres wrappers conservés ====================
@openai_retry(max_retries=2, delay=0.5)
def safe_embedding_create(input: Any, model: str = None, **kwargs) -> List[List[float]]:
    """Wrapper embeddings conservé; compatible avec SDK actuel."""
    if not input:
        raise ValueError("Le paramètre 'input' ne peut pas être vide")
    if isinstance(input, str):
        texts, single = [input], True
    elif isinstance(input, list):
        texts, single = input, False
    else:
        raise ValueError("'input' doit être str ou List[str]")
    texts = [t.strip() for t in texts if isinstance(t, str) and t.strip()]
    if not texts:
        raise ValueError("Aucun texte valide après filtrage")
    if not model:
        model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')

    max_batch = int(os.getenv('OPENAI_EMBEDDING_BATCH_SIZE', '100'))
    all_vecs: List[List[float]] = []
    for i in range(0, len(texts), max_batch):
        batch = texts[i:i+max_batch]
        resp = openai.embeddings.create(input=batch, model=model, **kwargs)
        data = resp.data if hasattr(resp, 'data') else (resp.get('data', []) if isinstance(resp, dict) else [])
        vecs = [item.embedding if hasattr(item, 'embedding') else item.get('embedding') for item in data]
        all_vecs.extend(vecs)
    return all_vecs[0] if single else all_vecs

# ==================== Tests rapides / Statuts (conservés) ====================
def test_openai_connection() -> Dict[str, Any]:
    try:
        test_model = os.getenv("OPENAI_TEST_MODEL", "gpt-5")
        try:
            resp = safe_chat_completion(model=test_model, messages=[{"role": "user", "content": "Test"}], max_tokens=5)
        except Exception:
            resp = safe_chat_completion(model="gpt-4o-mini", messages=[{"role": "user", "content": "Test"}], max_tokens=5)
            test_model = "gpt-4o-mini"
        return {
            "status": "success",
            "message": "Connexion OpenAI fonctionnelle",
            "model_tested": test_model,
            "response_preview": resp.choices[0].message.content[:50] if getattr(resp, 'choices', None) else "N/A",
        }
    except Exception as e:
        return {"status": "error", "message": f"Échec connexion OpenAI: {e}", "error_type": type(e).__name__}

def get_openai_models() -> List[str]:
    try:
        models = openai.models.list()
        return [m.id for m in models.data if getattr(m, 'id', None)]
    except Exception as e:
        logger.error(f"⛔ Erreur récupération modèles: {e}")
        return []

def get_openai_status() -> Dict[str, Any]:
    return {
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "temperature_safety": True,
        "default_model": os.getenv('DEFAULT_MODEL', 'gpt-5'),
    }
