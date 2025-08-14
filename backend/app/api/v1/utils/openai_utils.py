# -*- coding: utf-8 -*-
"""
openai_utils.py — GPT‑5 safe, backwards‑compatible utilities

This module preserves original public function names and behavior while fixing:
- Temperature handling for models that only support the default temperature (e.g., GPT‑5 families)
- Auto‑mapping between max_tokens and max_completion_tokens (and retry on API hint)
- HTTPX + SDK paths, both hardened with targeted retries
- More tolerant parsing for Chat Completions output

Public API (kept):
- _get_api_key() -> str
- openai_retry decorator
- _configure_openai_client()
- _completion_param_name(model: str) -> str
- _get_safe_temperature(requested: Optional[float], model: str) -> Optional[float]
- estimate_tokens(text: str, model: str) -> int (heuristic, kept for compatibility)
- get_model_max_tokens(model: str) -> int (heuristic, kept for compatibility)
- complete(messages, model, temperature=..., max_tokens=..., timeout=..., extra=None) -> Dict
- complete_text(prompt, temperature=..., max_tokens=None, model=None) -> str
- safe_chat_completion(**kwargs) -> Any (SDK path)
- complete_with_cot(prompt, temperature=..., max_tokens=None, model=None, parse_cot=True) -> Dict[str, Any]
- safe_embedding_create(input, model=None, **kwargs) -> List[List[float]] | List[float]
- get_openai_models() -> List[str]
- test_openai_connection() -> Dict[str, Any]

Drop‑in: other modules can import unchanged symbols.
"""
from __future__ import annotations

import os
import re
import json
import time
import math
import httpx
import logging
from typing import Any, Dict, List, Optional, Iterable, Tuple
from functools import wraps

# The OpenAI Python SDK (global style preserved for compatibility)
import openai

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Environment & constants
# ----------------------------------------------------------------------------
_DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-5")
_OPENAI_TIMEOUT = float(os.getenv("OPENAI_DEFAULT_TIMEOUT", "30"))
_OPENAI_DEFAULT_MAX_TOKENS = int(os.getenv("OPENAI_DEFAULT_MAX_TOKENS", "1500"))
_OPENAI_EMBED_BATCH = int(os.getenv("OPENAI_EMBEDDING_BATCH_SIZE", "100"))
_RESTRICTED_TEMP_MODELS = set(
    x.strip() for x in os.getenv("OPENAI_RESTRICTED_TEMP_MODELS", "").split(",") if x.strip()
)

# Known families that often require `max_completion_tokens` on chat/completions
_MAX_COMPLETION_FAMILIES = (
    r"^gpt-5",           # future/generation family (some endpoints)
    r"^gpt-4o",          # Omni family
    r"^o\d",            # reasoning families o3, o4 etc.
)

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _get_api_key() -> str:
    """Return the OpenAI API key or raise a clear error."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment")
    return key


def openai_retry(max_retries: int = 2, delay: float = 1.0):
    """Decorator for targeted retries with linear backoff.

    Retries on network/transient errors, and lets the inner functions perform
    semantic retries (e.g., temperature removal or token param swap).
    """
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    if attempt < max_retries:
                        time.sleep(delay)
                        continue
                    raise last_err
        return wrapper
    return deco


def _configure_openai_client() -> None:
    """Configure global OpenAI client with env API key (backward‑compatible)."""
    key = _get_api_key()
    # Global configuration is preserved for existing code paths
    openai.api_key = key


def _is_temp_unsupported_error(msg: str) -> bool:
    """Detect messages like:
    "Unsupported value: 'temperature' does not support 0.1 with this model. Only the default (1) value is supported."
    """
    if not msg:
        return False
    return bool(re.search(r"temperature.+(unsupported|does\s*not\s*support|only\s*the\s*default)", str(msg), re.I))


def _family_matches(model: str, patterns: Iterable[str]) -> bool:
    for p in patterns:
        if re.search(p, model or "", re.I):
            return True
    return False


def _completion_param_name(model: str) -> str:
    """Return the token param name expected by the API for this model.
    Historically chat/completions used `max_tokens`; some newer families accept
    `max_completion_tokens`. We auto‑choose and still retry on API feedback.
    """
    if _family_matches(model, _MAX_COMPLETION_FAMILIES):
        return "max_completion_tokens"
    return "max_tokens"


def _get_safe_temperature(requested: Optional[float], model: str) -> Optional[float]:
    """Return a temperature value that is safe to send for the model, or None to
    omit the parameter (use model default).

    Rules:
    - If model is in RESTRICTED list or part of strict families, return None.
    - Else clamp to [0.0, 2.0] and return.
    """
    if requested is None:
        return None

    model_id = (model or "").lower()
    if model_id in {m.lower() for m in _RESTRICTED_TEMP_MODELS}:
        return None

    # Some families (e.g., GPT‑5 / certain o* models) enforce default temperature
    if _family_matches(model_id, (r"^gpt-5", r"^o\d")):
        return None  # let the API default apply

    try:
        t = float(requested)
    except Exception:  # noqa: BLE001
        return None
    return max(0.0, min(2.0, t))


# ----------------------------------------------------------------------------
# Token utilities (heuristics kept for compatibility)
# ----------------------------------------------------------------------------

# Very rough token estimate; callers only use it for budgetting
_DEF_TOKENS_PER_CHAR = 0.25  # ~4 chars per token


def estimate_tokens(text: str, model: str = _DEFAULT_MODEL) -> int:
    if not text:
        return 0
    return int(math.ceil(len(text) * _DEF_TOKENS_PER_CHAR))


def get_model_max_tokens(model: str = _DEFAULT_MODEL) -> int:
    mid = (model or "").lower()
    # Conservative maxima; adjust as needed. Keeps old callers happy.
    if mid.startswith("gpt-5"):
        return 128000
    if mid.startswith("gpt-4o"):
        return 128000
    if mid.startswith("gpt-4"):
        return 8192
    if mid.startswith("gpt-3.5"):
        return 4096
    return 8192


# ----------------------------------------------------------------------------
# Core HTTPX call (keeps original signature)
# ----------------------------------------------------------------------------

@openai_retry(max_retries=2, delay=1.0)
def complete(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 800,
    timeout: float = _OPENAI_TIMEOUT,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """HTTP path to POST /v1/chat/completions.

    - Chooses between `max_tokens` and `max_completion_tokens`.
    - Applies safe temperature. If API rejects temperature, retry once without it.
    - Retries once if API says wrong token parameter name.
    """
    _configure_openai_client()

    extra = extra or {}
    param_name = _completion_param_name(model)
    safe_temp = _get_safe_temperature(temperature, model)

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        param_name: max_tokens,
        **{k: v for k, v in (extra or {}).items() if v is not None},
    }
    if safe_temp is not None:
        payload["temperature"] = safe_temp  # try; if refused we retry without

    headers = {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }
    url = "https://api.openai.com/v1/chat/completions"

    # 1st attempt
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers, json=payload)

    if r.status_code == 200:
        return r.json()

    # Decode error message
    try:
        err_obj = r.json()
        err_msg = (err_obj.get("error") or {}).get("message", "") or r.text
    except Exception:  # noqa: BLE001
        err_msg = r.text or ""

    # Retry on wrong token parameter name
    if "unsupported_parameter" in (err_msg or "").lower() and (
        "max_tokens" in err_msg.lower() or "max_completion_tokens" in err_msg.lower()
    ):
        other = "max_tokens" if param_name == "max_completion_tokens" else "max_completion_tokens"
        payload[other] = payload.pop(param_name)
        with httpx.Client(timeout=timeout) as client:
            r2 = client.post(url, headers=headers, json=payload)
        if r2.status_code == 200:
            return r2.json()
        try:
            err_obj2 = r2.json()
            err_msg = (err_obj2.get("error") or {}).get("message", "") or r2.text
        except Exception:  # noqa: BLE001
            err_msg = r2.text or err_msg

    # Retry removing temperature if model refuses custom values
    if _is_temp_unsupported_error(err_msg):
        logger.warning(f"[OpenAI] Température non supportée par {model} → retry sans 'temperature'")
        payload.pop("temperature", None)
        with httpx.Client(timeout=timeout) as client:
            r3 = client.post(url, headers=headers, json=payload)
        if r3.status_code == 200:
            return r3.json()
        try:
            err_obj3 = r3.json()
            err_msg = (err_obj3.get("error") or {}).get("message", "") or r3.text
        except Exception:  # noqa: BLE001
            err_msg = r3.text or err_msg

    # Otherwise raise the original error
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:  # noqa: BLE001
        raise RuntimeError(f"Requête OpenAI invalide: {e.response.text}") from None
    return r.json()


# ----------------------------------------------------------------------------
# High‑level text completion (keeps original signature)
# ----------------------------------------------------------------------------

@openai_retry(max_retries=2, delay=1.0)
def complete_text(
    prompt: str,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
) -> str:
    """Legacy wrapper that builds chat messages and returns text content.
    Applies safe temperature and tolerant output parsing.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Le prompt ne peut pas être vide")

    model = model or os.getenv("OPENAI_SYNTHESIS_MODEL", _DEFAULT_MODEL)
    safe_temp = _get_safe_temperature(temperature, model)

    # Adaptive token budget
    if max_tokens is None:
        plen = len(prompt)
        if plen < 500:
            max_tokens = 500 if model.startswith("gpt-5") else 300
        elif plen < 1500:
            max_tokens = 1000 if model.startswith("gpt-5") else 500
        elif plen < 3000:
            max_tokens = 1500 if model.startswith("gpt-5") else 700
        else:
            max_tokens = 2000 if model.startswith("gpt-5") else 800
        model_limit = get_model_max_tokens(model)
        available = model_limit - estimate_tokens(prompt, model) - 100
        if available > 0:
            max_tokens = min(max_tokens, available)

    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un expert en synthèse de contenu technique avicole. "
                "Réponds de manière concise, précise et professionnelle. "
                "Utilise un français clair et structure ton texte avec du Markdown si approprié."
            ),
        },
        {"role": "user", "content": prompt.strip()},
    ]

    response = complete(
        messages=messages,
        model=model,
        temperature=safe_temp if safe_temp is not None else None,
        max_tokens=max_tokens,
        timeout=_OPENAI_TIMEOUT,
    )

    # Debug logging pour GPT-5
    if model.startswith("gpt-5"):
        logger.info(f"[GPT-5-DEBUG] model={model}, max_tokens={max_tokens}, temp={safe_temp}, prompt_len={len(prompt)}")

    if not response or not response.get("choices"):
        raise RuntimeError("Réponse OpenAI vide")

    choice = (response.get("choices") or [{}])[0]
    content = ((choice.get("message") or {}).get("content")) or choice.get("text") or ""


    if not content:
            finish_reason = choice.get("finish_reason", "unknown")
            logger.error(f"[OpenAI] Réponse sans 'content'. Model: {model}, finish_reason: {finish_reason}, Aperçu: {str(response)[:500]}")
            
            # Retry avec plus de tokens si coupé par la limite
            if finish_reason == "length" and max_tokens < 3000:
                logger.warning(f"[OpenAI] Retry avec max_tokens augmenté: {max_tokens} -> {max_tokens * 2}")
                return complete_text(prompt, temperature, max_tokens * 2, model)
            
            raise RuntimeError(f"Contenu de réponse vide (finish_reason: {finish_reason})")

    return content.strip()


# ----------------------------------------------------------------------------
# SDK path (keeps original signature) — safe_chat_completion
# ----------------------------------------------------------------------------

@openai_retry(max_retries=2, delay=1.0)
def safe_chat_completion(**kwargs) -> Any:
    """Safe wrapper around openai.chat.completions.create
    - Auto‑maps tokens param name
    - Applies safe temperature
    - Retries without temperature if unsupported
    - Retries swapping token param name if API complains
    """
    if "model" not in kwargs:
        kwargs["model"] = _DEFAULT_MODEL
        logger.debug(f"🔧 Modèle par défaut utilisé: {kwargs['model']}")

    if "messages" not in kwargs or not kwargs["messages"]:
        raise ValueError("Le paramètre 'messages' est requis et ne peut pas être vide")

    model = kwargs["model"]

    # Defaults
    kwargs.setdefault("timeout", _OPENAI_TIMEOUT)
    kwargs.setdefault("max_tokens", _OPENAI_DEFAULT_MAX_TOKENS)

    # Harmonize token param name
    param_name = _completion_param_name(model)
    if "max_tokens" in kwargs and param_name == "max_completion_tokens":
        kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
    elif "max_completion_tokens" in kwargs and param_name == "max_tokens":
        kwargs["max_tokens"] = kwargs.pop("max_completion_tokens")

    # Safe temperature
    if "temperature" in kwargs:
        safe = _get_safe_temperature(kwargs["temperature"], model)
        if safe is None:
            kwargs.pop("temperature", None)
        else:
            kwargs["temperature"] = safe

    _configure_openai_client()
    start = time.time()
    try:
        resp = openai.chat.completions.create(**kwargs)
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        # Retry if temp unsupported
        if _is_temp_unsupported_error(msg):
            logger.warning(f"[OpenAI] Température non supportée par {model} → retry sans 'temperature'")
            kwargs.pop("temperature", None)
            resp = openai.chat.completions.create(**kwargs)
        # Retry if wrong token param name
        elif "unsupported_parameter" in msg.lower() and (
            "max_tokens" in msg.lower() or "max_completion_tokens" in msg.lower()
        ):
            if "max_tokens" in kwargs:
                kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
            elif "max_completion_tokens" in kwargs:
                kwargs["max_tokens"] = kwargs.pop("max_completion_tokens")
            resp = openai.chat.completions.create(**kwargs)
        else:
            raise

    elapsed = time.time() - start
    logger.debug(f"✅ Réponse OpenAI Chat reçue en {elapsed:.2f}s")

    if not resp or not getattr(resp, "choices", None):
        raise RuntimeError("Réponse OpenAI vide ou malformée")
    return resp


# ----------------------------------------------------------------------------
# CoT path (keeps signature) — complete_with_cot
# ----------------------------------------------------------------------------

def _parse_cot_sections(raw: str) -> Dict[str, str]:
    """Very light XML‑ish sections parser for CoT content."""
    out: Dict[str, str] = {}
    if not raw:
        return out
    for tag in ("<analysis>", "<plan>", "<answer>"):
        name = tag.strip("<>")
        m = re.search(rf"{re.escape(tag)}(.*?){re.escape('</' + name + '>')}", raw, re.S | re.I)
        if m:
            out[name] = m.group(1).strip()
    return out


def _extract_final_answer(raw: str, sections: Dict[str, str]) -> str:
    return sections.get("answer") or raw.strip()


@openai_retry(max_retries=2, delay=1.0)
def complete_with_cot(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
    parse_cot: bool = True,
) -> Dict[str, Any]:
    """Chain‑of‑Thought helper. Preserves signature; GPT‑5‑safe temperature.
    Returns dict with raw_response, parsed_sections, final_answer, model_used.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Le prompt CoT ne peut pas être vide")

    model = model or os.getenv("OPENAI_COT_MODEL", _DEFAULT_MODEL)

    # Token budget
    if max_tokens is None:
        max_tokens = int(os.getenv("OPENAI_COT_MAX_TOKENS", "800"))
        model_limit = get_model_max_tokens(model)
        available = model_limit - estimate_tokens(prompt, model) - 150
        if available > 0:
            max_tokens = min(max_tokens, available)

    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un expert vétérinaire avicole avec une approche méthodologique rigoureuse. "
                "Suis précisément la structure de raisonnement demandée avec les balises XML. "
                "Reste factuel, précis et professionnel dans ton analyse."
            ),
        },
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

    _configure_openai_client()
    try:
        response = openai.chat.completions.create(**call_kwargs)
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if _is_temp_unsupported_error(msg):
            logger.warning(f"[OpenAI] Température non supportée par {model} → retry sans 'temperature'")
            call_kwargs.pop("temperature", None)
            response = openai.chat.completions.create(**call_kwargs)
        elif "unsupported_parameter" in msg.lower() and (
            "max_tokens" in msg.lower() or "max_completion_tokens" in msg.lower()
        ):
            # Swap token parameter and retry
            other = "max_tokens" if param_name == "max_completion_tokens" else "max_completion_tokens"
            call_kwargs[other] = call_kwargs.pop(param_name)
            response = openai.chat.completions.create(**call_kwargs)
        else:
            raise

    if not response or not response.choices:
        raise RuntimeError("Réponse OpenAI CoT vide")

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise RuntimeError("Contenu CoT vide")

    result: Dict[str, Any] = {
        "raw_response": raw_content.strip(),
        "model_used": model,
        "temperature": safe_temp if safe_temp is not None else "default",
    }

    if hasattr(response, "usage"):
        try:
            result["token_usage"] = {
                "total": response.usage.total_tokens,
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
            }
        except Exception:  # noqa: BLE001
            pass

    if parse_cot:
        parsed_sections = _parse_cot_sections(raw_content)
        result["parsed_sections"] = parsed_sections
        result["final_answer"] = _extract_final_answer(raw_content, parsed_sections)

    return result


# ----------------------------------------------------------------------------
# Embeddings (kept; batching + compatibility)
# ----------------------------------------------------------------------------

@openai_retry(max_retries=2, delay=0.5)
def safe_embedding_create(input: Any, model: str | None = None, **kwargs) -> List[List[float]] | List[float]:
    """Create embeddings with batching; returns list(s) of vectors.
    Accepts str or list[str]. Preserves existing signature.
    """
    if input is None:
        raise ValueError("Le paramètre 'input' ne peut pas être vide")

    if isinstance(input, str):
        inputs = [input]
        single = True
    elif isinstance(input, list):
        inputs = input
        single = False
    else:
        raise ValueError("'input' doit être une string ou une liste de strings")

    inputs = [s.strip() for s in inputs if isinstance(s, str) and s.strip()]
    if not inputs:
        raise ValueError("Aucun texte valide après filtrage")

    model = model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    _configure_openai_client()

    all_vecs: List[List[float]] = []
    for i in range(0, len(inputs), _OPENAI_EMBED_BATCH):
        batch = inputs[i : i + _OPENAI_EMBED_BATCH]
        resp = openai.embeddings.create(input=batch, model=model, **kwargs)
        data = resp.data if hasattr(resp, "data") else (resp.get("data", []))
        batch_vecs = [item.embedding for item in data]
        all_vecs.extend(batch_vecs)

    if single:
        return all_vecs[0] if all_vecs else []
    return all_vecs


# ----------------------------------------------------------------------------
# Models listing (kept)
# ----------------------------------------------------------------------------

def get_openai_models() -> List[str]:
    try:
        _configure_openai_client()
        models = openai.models.list()
        return [m.id for m in models.data if getattr(m, "id", None)]
    except Exception as e:  # noqa: BLE001
        logger.error(f"⛔ Erreur récupération modèles: {e}")
        return []


# ----------------------------------------------------------------------------
# Connection test (kept)
# ----------------------------------------------------------------------------

def test_openai_connection() -> Dict[str, Any]:
    try:
        logger.info("🔧 Test de connexion OpenAI…")
        test_model = os.getenv("OPENAI_TEST_MODEL", _DEFAULT_MODEL)
        try:
            resp = safe_chat_completion(
                model=test_model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5,
            )
        except Exception:
            # fallback léger
            resp = safe_chat_completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5,
            )
            test_model = "gpt-4o-mini"

        preview = ""
        try:
            preview = resp.choices[0].message.content[:50] if resp.choices else "N/A"
        except Exception:  # noqa: BLE001
            preview = "N/A"

        return {
            "status": "success",
            "message": "Connexion OpenAI fonctionnelle",
            "model_tested": test_model,
            "response_preview": preview,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "status": "error",
            "message": f"Échec connexion OpenAI: {e}",
            "error_type": type(e).__name__,
        }
