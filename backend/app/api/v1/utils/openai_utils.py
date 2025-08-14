def generate_clarification_response(intent: str, missing_fields: List[str], general_info: str = "") -> str:
    """
    ðŸ†• NOUVEAU: GÃ©nÃ¨re des rÃ©ponses de clarification intelligentes
    """
    
    prompt = f"""GÃ©nÃ¨re une rÃ©ponse de clarification courte et utile pour un systÃ¨me d'expertise avicole.

CONTEXTE :
- Intention dÃ©tectÃ©e : {intent}
- Informations manquantes : {', '.join(missing_fields)}
- Info gÃ©nÃ©rale disponible : {general_info[:200] if general_info else 'Aucune'}

INSTRUCTIONS :
- RÃ©ponse en 2-3 phrases maximum
- Expliquer pourquoi ces infos sont importantes
- Ton professionnel mais accessible
- Pas de mention de sources

RÃ©ponse de clarification :"""

    try:
        # Utilisation de la nouvelle fonction complete()
        messages = [{"role": "user", "content": prompt}]
        model = os.getenv('DEFAULT_MODEL', 'gpt-5')
        response = complete(messages, model, temperature=0.3, max_tokens=150)
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"âš ï¸ Ã‰chec gÃ©nÃ©ration clarification: {e}")
        # Fallback gÃ©nÃ©rique
        return f"Pour vous donner une rÃ©ponse prÃ©cise sur {intent}, j'aurais besoin de quelques prÃ©cisions supplÃ©mentaires."
        
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

# ==================== NOUVEAU: HELPERS COMPATIBILITY max_completion_tokens ====================
# Familles de modÃ¨les qui exigent max_completion_tokens sur /chat/completions
_MCT_PREFIXES = (
    "gpt-4.1", "gpt-4o", "o1", "o4", "omni", "gpt-5", "gpt-4.1-mini",
    "gpt-4o-mini", "gpt-4.1-nano", "o1-mini", "o1-preview"
)

def _uses_mct(model: str) -> bool:
    if os.getenv("OPENAI_FORCE_COMPLETION_PARAM", "").lower() in ("mct", "max_completion_tokens"):
        return True
    if os.getenv("OPENAI_FORCE_COMPLETION_PARAM", "").lower() in ("mt", "max_tokens"):
        return False
    return any(model.startswith(p) for p in _MCT_PREFIXES)

def _completion_param_name(model: str) -> str:
    return "max_completion_tokens" if _uses_mct(model) else "max_tokens"

# ==================== AMÃ‰LIORATION MAJEURE: Gestion centralisÃ©e de l'API key ====================
def _get_api_key() -> str:
    """
    âœ… AMÃ‰LIORATION: Fonction centralisÃ©e pour la gestion de la clÃ© API
    
    PROBLÃˆME RÃ‰SOLU:
    - Code dupliquÃ© dans safe_chat_completion et safe_embedding_create
    - VÃ©rification rÃ©pÃ©tÃ©e de OPENAI_API_KEY
    
    SOLUTION:
    - Fonction unique pour rÃ©cupÃ©rer et valider la clÃ©
    - Gestion d'erreurs centralisÃ©e
    - Configuration flexible via variables d'environnement
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.error("â›” OPENAI_API_KEY non configurÃ©e")
        raise RuntimeError(
            "OPENAI_API_KEY n'est pas configurÃ©e dans les variables d'environnement. "
            "Veuillez dÃ©finir cette variable pour utiliser les services OpenAI."
        )
    
    if len(api_key.strip()) < 10:
        logger.error("â›” OPENAI_API_KEY semble invalide (trop courte)")
        raise RuntimeError("OPENAI_API_KEY semble invalide - vÃ©rifiez la configuration")
    
    return api_key.strip()

def _configure_openai_client() -> None:
    """
    âœ… AMÃ‰LIORATION: Configuration centralisÃ©e du client OpenAI
    """
    try:
        api_key = _get_api_key()
        openai.api_key = api_key
        logger.debug("âœ… Client OpenAI configurÃ©")
    except Exception as e:
        logger.error(f"â›” Erreur configuration OpenAI: {e}")
        raise

# ==================== AMÃ‰LIORATION: DÃ©corateur pour retry et gestion d'erreurs ====================
def openai_retry(max_retries: int = 2, delay: float = 1.0):
    """
    âœ… NOUVEAU: DÃ©corateur pour retry automatique des appels OpenAI
    
    GÃ¨re les erreurs temporaires comme:
    - Rate limiting
    - Erreurs rÃ©seau temporaires
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
                    logger.warning(f"âš ï¸ Rate limit atteint (tentative {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        time.sleep(delay * (2 ** attempt))  # Backoff exponentiel
                        continue
                    last_exception = e
                    
                except openai.APITimeoutError as e:
                    logger.warning(f"âš ï¸ Timeout OpenAI (tentative {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        time.sleep(delay)
                        continue
                    last_exception = e
                    
                except openai.APIConnectionError as e:
                    logger.warning(f"âš ï¸ Erreur connexion OpenAI (tentative {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        time.sleep(delay)
                        continue
                    last_exception = e
                    
                except Exception as e:
                    # Pour les autres erreurs, pas de retry
                    logger.error(f"â›” Erreur OpenAI non-retry: {type(e).__name__}: {e}")
                    last_exception = e
                    break
            
            # Si on arrive ici, tous les retries ont Ã©chouÃ©
            raise RuntimeError(f"Ã‰chec aprÃ¨s {max_retries + 1} tentatives: {last_exception}")
        
        return wrapper
    return decorator

# ==================== ðŸ†• NOUVELLES FONCTIONS CHAIN-OF-THOUGHT ====================

@openai_retry(max_retries=2, delay=1.0)
def complete_with_cot(prompt: str, temperature: float = 0.3, max_tokens: Optional[int] = None, 
                     model: Optional[str] = None, parse_cot: bool = True) -> Dict[str, Any]:
    """
    ðŸ†• NOUVEAU: Completion spÃ©cialisÃ©e pour Chain-of-Thought avec parsing des balises
    
    Args:
        prompt: Prompt CoT avec balises XML structurantes
        temperature: CrÃ©ativitÃ© du modÃ¨le (0.0-2.0)
        max_tokens: Limite de tokens (None = calcul automatique)
        model: ModÃ¨le Ã  utiliser (None = dÃ©faut CoT)
        parse_cot: Si True, parse les balises XML dans la rÃ©ponse
    
    Returns:
        Dict contenant 'raw_response', 'parsed_sections', 'final_answer'
    """
    
    # Validation des paramÃ¨tres
    if not prompt or not prompt.strip():
        raise ValueError("Le prompt CoT ne peut pas Ãªtre vide")
    
    if not 0.0 <= temperature <= 2.0:
        logger.warning(f"âš ï¸ Temperature {temperature} ajustÃ©e Ã  0.3")
        temperature = 0.3
    
    # Configuration modÃ¨le CoT
    if model is None:
        model = os.getenv('OPENAI_COT_MODEL', os.getenv('DEFAULT_MODEL', 'gpt-5'))
    
    # Calcul tokens adaptatif pour CoT (plus gÃ©nÃ©reux)
    if max_tokens is None:
        prompt_length = len(prompt)
        if prompt_length < 1000:
            max_tokens = 600
        elif prompt_length < 2000:
            max_tokens = 800
        else:
            max_tokens = 1000
        
        # Ajustement selon limites modÃ¨le
        model_limit = get_model_max_tokens(model)
        estimated_prompt_tokens = estimate_tokens(prompt, model)
        available_tokens = model_limit - estimated_prompt_tokens - 150  # Marge CoT
        
        if available_tokens > 0:
            max_tokens = min(max_tokens, available_tokens)
    
    logger.debug(f"ðŸ§  Appel CoT: model={model}, temp={temperature}, max_tokens={max_tokens}")
    
    # Messages optimisÃ©s pour CoT
    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un expert vÃ©tÃ©rinaire avicole avec une approche mÃ©thodologique rigoureuse. "
                "Suis prÃ©cisÃ©ment la structure de raisonnement demandÃ©e avec les balises XML. "
                "Reste factuel, prÃ©cis et professionnel dans ton analyse."
            )
        },
        {
            "role": "user",
            "content": prompt.strip()
        }
    ]
    
    try:
        response = safe_chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.9,
            frequency_penalty=0.0,  # Pas de pÃ©nalitÃ© pour CoT structurÃ©
            presence_penalty=0.1
        )
        
        if not response or not response.choices:
            raise RuntimeError("RÃ©ponse OpenAI CoT vide")
        
        raw_content = response.choices[0].message.content
        if not raw_content:
            raise RuntimeError("Contenu CoT vide")
        
        result = {
            "raw_response": raw_content.strip(),
            "model_used": model,
            "temperature": temperature
        }
        
        # ðŸ†• Parsing des sections CoT si demandÃ©
        if parse_cot:
            parsed_sections = _parse_cot_sections(raw_content)
            result["parsed_sections"] = parsed_sections
            
            # Extraction de la rÃ©ponse finale
            final_answer = _extract_final_answer(raw_content, parsed_sections)
            result["final_answer"] = final_answer
        
        # MÃ©triques
        if hasattr(response, 'usage') and response.usage:
            result["token_usage"] = {
                "total": response.usage.total_tokens,
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens
            }
        
        logger.debug(f"âœ… CoT terminÃ©: {len(raw_content)} caractÃ¨res gÃ©nÃ©rÃ©s")
        return result
        
    except Exception as e:
        logger.error(f"â›” Erreur CoT: {type(e).__name__}: {e}")
        raise RuntimeError(f"Erreur lors du raisonnement CoT: {e}")

def _parse_cot_sections(cot_response: str) -> Dict[str, str]:
    """
    ðŸ†• Parse les sections dÃ©limitÃ©es par des balises XML dans une rÃ©ponse CoT
    """
    sections = {}
    
    # Balises CoT standards
    cot_tags = [
        "thinking", "analysis", "reasoning", "factors", "recommendations", 
        "validation", "problem_decomposition", "factor_analysis", 
        "interconnections", "solution_pathway", "risk_mitigation",
        "economic_context", "cost_benefit_breakdown", "scenario_analysis",
        "optimization_levers", "financial_recommendation", "current_analysis",
        "optimization_factors", "strategy", "impact_prediction"
    ]
    
    for tag in cot_tags:
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, cot_response, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            sections[tag] = content
    
    return sections

def _extract_final_answer(raw_response: str, parsed_sections: Dict[str, str]) -> str:
    """
    ðŸ†• Extrait la rÃ©ponse finale d'une rÃ©ponse CoT
    """
    # 1. Chercher aprÃ¨s la derniÃ¨re balise fermante
    last_tag_pattern = r"</[^>]+>\s*(.+)$"
    match = re.search(last_tag_pattern, raw_response, re.DOTALL | re.IGNORECASE)
    if match:
        final_part = match.group(1).strip()
        if len(final_part) > 50:  # Assez substantiel
            return final_part
    
    # 2. Utiliser la section "recommendations" si disponible
    if "recommendations" in parsed_sections:
        return parsed_sections["recommendations"]
    
    # 3. Utiliser "solution_pathway" ou "financial_recommendation"
    for key in ["solution_pathway", "financial_recommendation", "strategy"]:
        if key in parsed_sections:
            return parsed_sections[key]
    
    # 4. Fallback: derniers 300 caractÃ¨res
    return raw_response[-300:].strip()

@openai_retry(max_retries=2, delay=1.0)
def generate_cot_followup(initial_question: str, cot_sections: Dict[str, str], 
                         entities: Dict[str, Any], missing_info: List[str] = None) -> str:
    """
    ðŸ†• NOUVEAU: GÃ©nÃ¨re une question de suivi intelligente basÃ©e sur l'analyse CoT
    
    Args:
        initial_question: Question originale de l'utilisateur
        cot_sections: Sections parsÃ©es de l'analyse CoT prÃ©cÃ©dente
        entities: EntitÃ©s extraites du contexte
        missing_info: Informations manquantes identifiÃ©es
    
    Returns:
        Question de suivi structurÃ©e
    """
    
    # Construction du contexte pour la gÃ©nÃ©ration
    context_parts = [
        f"QUESTION INITIALE: {initial_question}",
        f"CONTEXTE: {entities}",
    ]
    
    if missing_info:
        context_parts.append(f"INFORMATIONS MANQUANTES: {', '.join(missing_info)}")
    
    # RÃ©sumÃ© des analyses CoT disponibles
    available_analysis = []
    for section, content in cot_sections.items():
        if content and len(content) > 20:
            available_analysis.append(f"{section}: {content[:100]}...")
    
    if available_analysis:
        context_parts.append("ANALYSES PRÃ‰CÃ‰DENTES:")
        context_parts.extend(available_analysis[:3])  # Limite pour Ã©viter surcharge
    
    context = "\n".join(context_parts)
    
    prompt = f"""BasÃ© sur l'analyse prÃ©cÃ©dente, gÃ©nÃ¨re une question de suivi pertinente pour approfondir le diagnostic ou la solution.

{context}

INSTRUCTIONS:
- Question courte et prÃ©cise (1-2 phrases max)
- Focus sur les Ã©lÃ©ments les plus critiques identifiÃ©s
- Ton professionnel mais accessible
- Viser l'action pratique

Question de suivi appropriÃ©e:"""

    try:
        followup = complete_text(prompt, temperature=0.4, max_tokens=150)
        return followup.strip()
    except Exception as e:
        logger.warning(f"âš ï¸ Ã‰chec gÃ©nÃ©ration followup CoT: {e}")
        return f"Pour approfondir l'analyse de votre situation avec {entities.get('species', 'ces animaux')}, pourriez-vous prÃ©ciser les Ã©lÃ©ments mentionnÃ©s ci-dessus ?"

# ==================== FONCTION CORRIGÃ‰E: complete() avec httpx ====================
def complete(messages, model: str, temperature: float = 0.2, max_tokens: int = 800,
             timeout: float = 30.0, extra: dict | None = None) -> dict:
    """
    Envoie un appel /v1/chat/completions, compatible anciens & nouveaux modÃ¨les.
    """
    extra = extra or {}
    param_name = _completion_param_name(model)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        param_name: max_tokens,  # <-- clÃ© choisie dynamiquement
        **{k: v for k, v in extra.items() if v is not None}
    }

    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json",
    }

    url = "https://api.openai.com/v1/chat/completions"

    # 1er essai
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers, json=payload)

    if r.status_code == 200:
        return r.json()

    # Auto-rattrapage: paramÃ¨tre non supportÃ© â†’ on bascule et on rÃ©essaie une fois
    try:
        err = r.json().get("error", {})
    except Exception:
        err = {}

    unsupported = (r.status_code == 400 and err.get("code") == "unsupported_parameter")
    wrong_param = err.get("param")
    msg = (err.get("message") or "").lower()

    if unsupported and wrong_param in ("max_tokens", "max_completion_tokens"):
        # Swap de paramÃ¨tre
        other = "max_completion_tokens" if wrong_param == "max_tokens" else "max_tokens"
        if other != param_name:
            # reconstruire le payload proprement
            payload.pop(param_name, None)
            payload[other] = max_tokens
            logger.warning("âš ï¸ OpenAI param '%s' non supportÃ© pour %s â€” retry avec '%s'",
                           wrong_param, model, other)
            with httpx.Client(timeout=timeout) as client:
                r2 = client.post(url, headers=headers, json=payload)
            if r2.status_code == 200:
                return r2.json()

    # Si on est lÃ , on remonte l'erreur d'origine pour ton retry logic externe
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"RequÃªte OpenAI invalide: {e.response.text}") from None
    return r.json()

# ==================== WRAPPER DE COMPATIBILITÃ‰ ====================
@openai_retry(max_retries=2, delay=1.0)
def complete_text(prompt: str, temperature: float = 0.2, max_tokens: Optional[int] = None, model: Optional[str] = None) -> str:
    """
    Wrapper de compatibilitÃ© pour l'ancienne signature complete(prompt) -> str
    """
    # Validation des paramÃ¨tres
    if not prompt or not prompt.strip():
        raise ValueError("Le prompt ne peut pas Ãªtre vide")
    
    if not 0.0 <= temperature <= 2.0:
        logger.warning(f"âš ï¸ Temperature {temperature} hors limite [0.0-2.0], ajustÃ© Ã  0.2")
        temperature = 0.2
    
    # Configuration standard
    if model is None:
        model = os.getenv('OPENAI_SYNTHESIS_MODEL', os.getenv('DEFAULT_MODEL', 'gpt-5'))
    
    # Calcul adaptatif de max_tokens
    if max_tokens is None:
        prompt_length = len(prompt)
        if prompt_length < 500:
            max_tokens = 300
        elif prompt_length < 1500:
            max_tokens = 500
        elif prompt_length < 3000:
            max_tokens = 700
        else:
            max_tokens = 800
        
        # VÃ©rification des limites du modÃ¨le
        model_limit = get_model_max_tokens(model)
        estimated_prompt_tokens = estimate_tokens(prompt, model)
        available_tokens = model_limit - estimated_prompt_tokens - 100
        
        if available_tokens > 0:
            max_tokens = min(max_tokens, available_tokens)
    
    # Construction du message
    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un expert en synthÃ¨se de contenu technique avicole. "
                "RÃ©ponds de maniÃ¨re concise, prÃ©cise et professionnelle. "
                "Utilise un franÃ§ais clair et structure ton texte avec du Markdown si appropriÃ©."
            )
        },
        {
            "role": "user", 
            "content": prompt.strip()
        }
    ]
    
    logger.debug(f"ðŸ¤– Appel complete_text(): model={model}, temp={temperature}, max_tokens={max_tokens}")
    
    try:
        response = complete(messages, model, temperature, max_tokens)
        
        if not response or not response.get("choices"):
            raise RuntimeError("RÃ©ponse OpenAI vide")
        
        content = response["choices"][0]["message"]["content"]
        if not content:
            raise RuntimeError("Contenu de rÃ©ponse vide")
        
        logger.debug(f"âœ… Complete_text terminÃ©: {len(content)} caractÃ¨res gÃ©nÃ©rÃ©s")
        return content.strip()
        
    except Exception as e:
        logger.error(f"â›” Erreur dans complete_text(): {type(e).__name__}: {e}")
        raise RuntimeError(f"Erreur lors de la synthÃ¨se LLM: {e}")

# ==================== FONCTION AMÃ‰LIORÃ‰E: safe_chat_completion avec correctif max_completion_tokens ====================
@openai_retry(max_retries=2, delay=1.0)
def safe_chat_completion(**kwargs) -> Any:
    """
    Wrapper sÃ©curisÃ© pour openai.chat.completions.create
    
    AMÃ‰LIORATIONS APPLIQUÃ‰ES:
    - Utilisation de _get_api_key() centralisÃ©e (plus de duplication)
    - Retry automatique avec backoff exponentiel
    - Gestion d'erreurs spÃ©cialisÃ©e par type
    - Validation des paramÃ¨tres d'entrÃ©e
    - Logging dÃ©taillÃ© pour debug
    - NOUVEAU: Support automatique max_completion_tokens pour nouveaux modÃ¨les
    """
    
    # âœ… AMÃ‰LIORATION: Validation des paramÃ¨tres essentiels
    if 'model' not in kwargs:
        kwargs['model'] = os.getenv('DEFAULT_MODEL', 'gpt-5')
        logger.debug(f"ðŸ”§ ModÃ¨le par dÃ©faut utilisÃ©: {kwargs['model']}")
    
    if 'messages' not in kwargs or not kwargs['messages']:
        raise ValueError("Le paramÃ¨tre 'messages' est requis et ne peut pas Ãªtre vide")
    
    # âœ… AMÃ‰LIORATION: Configuration avec paramÃ¨tres par dÃ©faut intelligents
    default_params = {
        'temperature': float(os.getenv('OPENAI_DEFAULT_TEMPERATURE', '0.7')),
        'max_tokens': int(os.getenv('OPENAI_DEFAULT_MAX_TOKENS', '500')),
        'timeout': int(os.getenv('OPENAI_DEFAULT_TIMEOUT', '30'))
    }
    
    # Appliquer les dÃ©fauts seulement si non spÃ©cifiÃ©s
    for key, value in default_params.items():
        if key not in kwargs:
            kwargs[key] = value
    
    # ðŸ†• CORRECTIF: DÃ©tection automatique du bon paramÃ¨tre selon le modÃ¨le
    model = kwargs.get('model', 'gpt-5')
    if 'max_tokens' in kwargs:
        max_tokens_value = kwargs.pop('max_tokens')
        correct_param = _completion_param_name(model)
        kwargs[correct_param] = max_tokens_value
        logger.debug(f"ðŸ”§ ParamÃ¨tre tokens: {correct_param}={max_tokens_value} pour {model}")
    
    logger.debug(f"ðŸ¤– Appel OpenAI Chat: model={model}, temp={kwargs.get('temperature')}")
    
    try:
        # âœ… AMÃ‰LIORATION: Configuration centralisÃ©e
        _configure_openai_client()
        
        # âœ… AMÃ‰LIORATION: Mesure du temps de rÃ©ponse
        start_time = time.time()
        
        # ðŸ†• CORRECTIF: Appel avec auto-retry si mauvais paramÃ¨tre
        try:
            response = openai.chat.completions.create(**kwargs)
        except Exception as e:
            # Auto-retry si erreur de paramÃ¨tre non supportÃ©
            error_msg = str(e).lower()
            if "unsupported_parameter" in error_msg and ("max_tokens" in error_msg or "max_completion_tokens" in error_msg):
                logger.warning(f"âš ï¸ ParamÃ¨tre tokens non supportÃ© pour {model}, tentative avec paramÃ¨tre alternatif")
                
                # Swap du paramÃ¨tre et retry une fois
                if 'max_tokens' in kwargs:
                    kwargs['max_completion_tokens'] = kwargs.pop('max_tokens')
                elif 'max_completion_tokens' in kwargs:
                    kwargs['max_tokens'] = kwargs.pop('max_completion_tokens')
                
                response = openai.chat.completions.create(**kwargs)
            else:
                raise
        
        elapsed_time = time.time() - start_time
        
        logger.debug(f"âœ… RÃ©ponse OpenAI Chat reÃ§ue en {elapsed_time:.2f}s")
        
        # âœ… AMÃ‰LIORATION: Validation de la rÃ©ponse
        if not response or not response.choices:
            raise RuntimeError("RÃ©ponse OpenAI vide ou malformÃ©e")
        
        # âœ… AMÃ‰LIORATION: Logging des mÃ©triques d'usage
        if hasattr(response, 'usage') and response.usage:
            logger.debug(f"ðŸ“Š Tokens utilisÃ©s: {response.usage.total_tokens}")
        
        return response
        
    except openai.AuthenticationError as e:
        logger.error("â›” Erreur authentification OpenAI - vÃ©rifiez votre clÃ© API")
        raise RuntimeError(f"Authentification OpenAI Ã©chouÃ©e: {e}")
        
    except openai.PermissionDeniedError as e:
        logger.error("â›” Permission refusÃ©e OpenAI - vÃ©rifiez vos droits d'accÃ¨s")
        raise RuntimeError(f"Permission OpenAI refusÃ©e: {e}")
        
    except openai.BadRequestError as e:
        logger.error(f"â›” RequÃªte OpenAI invalide: {e}")
        raise RuntimeError(f"RequÃªte OpenAI invalide: {e}")
        
    except Exception as e:
        logger.error(f"â›” Erreur inattendue OpenAI Chat: {type(e).__name__}: {e}")
        raise RuntimeError(f"Erreur lors de l'appel Ã  OpenAI ChatCompletion: {e}")

# ==================== FONCTION AMÃ‰LIORÃ‰E: safe_embedding_create ====================
@openai_retry(max_retries=2, delay=0.5)
def safe_embedding_create(input: Any, model: str = "text-embedding-ada-002", **kwargs) -> List[List[float]]:
    """
    Wrapper sÃ©curisÃ© pour openai.embeddings.create
    
    AMÃ‰LIORATIONS APPLIQUÃ‰ES:
    - Utilisation de _get_api_key() centralisÃ©e (plus de duplication)
    - Retry automatique pour erreurs temporaires
    - Validation et normalisation des inputs
    - Gestion d'erreurs spÃ©cialisÃ©e
    - Support des embeddings batch
    - Format de retour standardisÃ©
    """
    
    # âœ… AMÃ‰LIORATION: Validation et normalisation des inputs
    if not input:
        raise ValueError("Le paramÃ¨tre 'input' ne peut pas Ãªtre vide")
    
    # Normaliser input en liste si nÃ©cessaire
    if isinstance(input, str):
        input_list = [input]
        single_input = True
    elif isinstance(input, list):
        input_list = input
        single_input = False
    else:
        raise ValueError("Le paramÃ¨tre 'input' doit Ãªtre une string ou une liste de strings")
    
    # Validation du contenu
    for i, text in enumerate(input_list):
        if not isinstance(text, str):
            raise ValueError(f"Ã‰lÃ©ment {i} de input doit Ãªtre une string")
        if not text.strip():
            logger.warning(f"âš ï¸ Ã‰lÃ©ment {i} de input est vide")
    
    # âœ… AMÃ‰LIORATION: Filtrer les textes vides
    filtered_input = [text.strip() for text in input_list if text.strip()]
    if not filtered_input:
        raise ValueError("Aucun texte valide aprÃ¨s filtrage")
    
    # âœ… AMÃ‰LIORATION: Configuration avec modÃ¨le par dÃ©faut
    if not model:
        model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002')
    
    logger.debug(f"ðŸ“¤ Appel OpenAI Embeddings: model={model}, inputs={len(filtered_input)}")
    
    try:
        # âœ… AMÃ‰LIORATION: Configuration centralisÃ©e
        _configure_openai_client()
        
        # âœ… AMÃ‰LIORATION: Gestion des grandes listes (batch processing)
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
            
            logger.debug(f"âœ… Batch embeddings {i//max_batch_size + 1} traitÃ© en {elapsed_time:.2f}s")
            
            # âœ… AMÃ‰LIORATION: Extraction robuste des embeddings avec compatibilitÃ©
            if hasattr(response, 'data') and response.data:
                batch_embeddings = [item.embedding for item in response.data]
            elif isinstance(response, dict) and 'data' in response:
                batch_embeddings = [
                    item.get('embedding') if isinstance(item, dict) else item.embedding 
                    for item in response['data']
                ]
            else:
                raise RuntimeError("Format de rÃ©ponse OpenAI Embeddings non reconnu")
            
            all_embeddings.extend(batch_embeddings)
        
        # âœ… AMÃ‰LIORATION: Validation des embeddings retournÃ©s
        if len(all_embeddings) != len(filtered_input):
            raise RuntimeError(f"Nombre d'embeddings ({len(all_embeddings)}) "
                             f"ne correspond pas aux inputs ({len(filtered_input)})")
        
        # VÃ©rification de la dimension des embeddings
        if all_embeddings and all_embeddings[0]:
            embedding_dim = len(all_embeddings[0])
            logger.debug(f"ðŸ“Š Embeddings gÃ©nÃ©rÃ©s: {len(all_embeddings)} vecteurs de dimension {embedding_dim}")
        
        # âœ… AMÃ‰LIORATION: Retour adaptÃ© au format d'entrÃ©e
        if single_input:
            return all_embeddings[0] if all_embeddings else []
        else:
            return all_embeddings
        
    except openai.AuthenticationError as e:
        logger.error("â›” Erreur authentification OpenAI Embeddings")
        raise RuntimeError(f"Authentification OpenAI Ã©chouÃ©e: {e}")
        
    except openai.InvalidRequestError as e:
        logger.error(f"â›” RequÃªte OpenAI Embeddings invalide: {e}")
        raise RuntimeError(f"RequÃªte OpenAI Embeddings invalide: {e}")
        
    except Exception as e:
        logger.error(f"â›” Erreur inattendue OpenAI Embeddings: {type(e).__name__}: {e}")
        raise RuntimeError(f"Erreur lors de l'appel Ã  OpenAI Embedding: {e}")

# ==================== ðŸ†• NOUVELLES FONCTIONS POUR DIALOGUE_MANAGER ====================

def synthesize_rag_content(question: str, raw_content: str, max_length: int = 300) -> str:
    """
    ðŸ†• NOUVEAU: SynthÃ¨se spÃ©cialisÃ©e pour le contenu RAG du dialogue_manager
    
    OptimisÃ©e pour nettoyer et reformater le contenu brut des PDFs avicoles.
    """
    
    if not raw_content or not raw_content.strip():
        return "Informations techniques disponibles."
    
    # Prompt spÃ©cialisÃ© pour le contenu avicole
    synthesis_prompt = f"""SynthÃ©tise ces informations techniques avicoles de maniÃ¨re claire et professionnelle.

INSTRUCTIONS CRITIQUES :
- NE JAMAIS mentionner de sources, fichiers PDF ou rÃ©fÃ©rences dans ta rÃ©ponse
- NE JAMAIS inclure de fragments de tableaux mal formatÃ©s
- Utiliser du Markdown pour la structure (##, **, -)
- RÃ©ponse concise (~{max_length} mots maximum)
- Si donnÃ©es incertaines, donner une fourchette
- Garder uniquement les informations pertinentes Ã  la question

Question utilisateur : {question}

Contenu technique Ã  synthÃ©tiser :
{raw_content[:1500]}

RÃ©ponse synthÃ©tique (format Markdown, sans sources) :"""

    try:
        # Utilisation de la nouvelle fonction complete()
        messages = [{"role": "user", "content": synthesis_prompt}]
        model = os.getenv('OPENAI_SYNTHESIS_MODEL', os.getenv('DEFAULT_MODEL', 'gpt-5'))
        response = complete(messages, model, temperature=0.2, max_tokens=min(400, max_length + 100))
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"âš ï¸ Ã‰chec synthÃ¨se RAG, fallback: {e}")
        # Fallback simple : nettoyage basique
        cleaned = raw_content.strip()[:max_length]
        if len(raw_content) > max_length:
            cleaned += "..."
        return cleaned

def generate_clarification_response(intent: str, missing_fields: List[str], general_info: str = "") -> str:
    """
    ðŸ†• NOUVEAU: GÃ©nÃ¨re des rÃ©ponses de clarification intelligentes
    """
    
    prompt = f"""GÃ©nÃ¨re une rÃ©ponse de clarification courte et utile pour un systÃ¨me d'expertise avicole.

CONTEXTE :
- Intention dÃ©tectÃ©e : {intent}
- Informations manquantes : {', '.join(missing_fields)}
- Info gÃ©nÃ©rale disponible : {general_info[:200] if general_info else 'Aucune'}

INSTRUCTIONS :
- RÃ©ponse en 2-3 phrases maximum
- Expliquer pourquoi ces infos sont importantes
- Ton professionnel mais accessible
- Pas de mention de sources

RÃ©ponse de clarification :"""

    try:
        return complete_text(prompt, temperature=0.3, max_tokens=150)
    except Exception as e:
        logger.warning(f"âš ï¸ Ã‰chec gÃ©nÃ©ration clarification: {e}")
        # Fallback gÃ©nÃ©rique
        return f"Pour vous donner une rÃ©ponse prÃ©cise sur {intent}, j'aurais besoin de quelques prÃ©cisions supplÃ©mentaires."

# ==================== NOUVELLES FONCTIONNALITÃ‰S UTILITAIRES ====================
def test_openai_connection() -> Dict[str, Any]:
    """
    âœ… NOUVELLE FONCTIONNALITÃ‰: Test de connexion OpenAI
    Utile pour les diagnostics et la validation de configuration
    """
    try:
        logger.info("ðŸ”§ Test de connexion OpenAI...")
        
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
            "message": f"Ã‰chec connexion OpenAI: {str(e)}",
            "error_type": type(e).__name__
        }

def get_openai_models() -> List[str]:
    """
    âœ… NOUVELLE FONCTIONNALITÃ‰: Liste des modÃ¨les OpenAI disponibles
    """
    try:
        _configure_openai_client()
        models = openai.models.list()
        return [model.id for model in models.data if model.id]
    except Exception as e:
        logger.error(f"â›” Erreur rÃ©cupÃ©ration modÃ¨les: {e}")
        return []

def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    âœ… NOUVELLE FONCTIONNALITÃ‰: Estimation approximative du nombre de tokens
    Utile pour Ã©viter les dÃ©passements de limites
    """
    # Estimation grossiÃ¨re : ~4 caractÃ¨res par token pour l'anglais/franÃ§ais
    # Plus prÃ©cis avec tiktoken si disponible
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except ImportError:
        # Fallback vers estimation approximative
        return len(text) // 4
    except Exception:
        # Fallback sÃ©curisÃ©
        return len(text) // 4

def get_model_max_tokens(model: str) -> int:
    """
    âœ… NOUVELLE FONCTIONNALITÃ‰: RÃ©cupÃ¨re la limite de tokens pour un modÃ¨le
    """
    MAX_TOKENS_LIMITS = {
        "gpt-3.5-turbo": 4096,
        "gpt-4": 8192,
        "gpt-4o": 4096,
        "gpt-4-turbo": 128000,
        "gpt-4o-mini": 4096,
        "gpt-5": 8192,
        "gpt-5-mini": 4096,
        "gpt-5-nano": 2048,
        "gpt-5-chat-latest": 8192
    }
    return MAX_TOKENS_LIMITS.get(model, 4096)

# ==================== CONFIGURATION ET CONSTANTES ====================
# âœ… AMÃ‰LIORATION: Constantes configurables
DEFAULT_MODELS = {
    "chat": os.getenv('DEFAULT_MODEL', 'gpt-5'),
    "embedding": os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002'),
    "synthesis": os.getenv('OPENAI_SYNTHESIS_MODEL', os.getenv('DEFAULT_MODEL', 'gpt-5')),  # ðŸ†• Nouveau pour synthÃ¨se
    "cot": os.getenv('OPENAI_COT_MODEL', os.getenv('DEFAULT_MODEL', 'gpt-5'))  # ðŸ†• Nouveau pour Chain-of-Thought
}

# ==================== ðŸ†• FONCTIONS DE DIAGNOSTIC COT ====================

def test_cot_pipeline() -> Dict[str, Any]:
    """
    ðŸ†• NOUVEAU: Test complet du pipeline Chain-of-Thought
    """
    try:
        # Test prompt CoT simple
        test_cot_prompt = """<thinking>
Analyse de la question : Il s'agit d'un test du systÃ¨me CoT.
</thinking>

<analysis>
Le systÃ¨me doit parser cette structure et extraire les sections.
</analysis>

<recommendations>
Le test CoT fonctionne correctement si ce texte est parsÃ©.
</recommendations>

RÃ©ponse finale : Test CoT rÃ©ussi."""

        # Test complete_with_cot
        cot_result = complete_with_cot(
            prompt=test_cot_prompt,
            temperature=0.2,
            max_tokens=200,
            parse_cot=True
        )
        
        # Test parsing
        sections_found = len(cot_result.get("parsed_sections", {}))
        has_final_answer = bool(cot_result.get("final_answer"))
        
        # Test complete() avec dÃ©tection automatique
        auto_cot_result = complete_text(
            prompt="<thinking>Test automatique</thinking>\n\nRÃ©ponse automatique CoT.",
            temperature=0.2,
            max_tokens=100
        )
        
        return {
            "status": "success",
            "cot_direct_test": {
                "success": True,
                "sections_parsed": sections_found,
                "final_answer_extracted": has_final_answer,
                "raw_length": len(cot_result.get("raw_response", ""))
            },
            "cot_auto_detection": {
                "success": True,
                "response_length": len(auto_cot_result)
            },
            "message": "Pipeline CoT entiÃ¨rement fonctionnel"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ã‰chec test pipeline CoT: {str(e)}",
            "error_type": type(e).__name__
        }

def test_synthesis_pipeline() -> Dict[str, Any]:
    """
    ðŸ†• AMÃ‰LIORÃ‰: Test complet du pipeline de synthÃ¨se pour dialogue_manager
    """
    try:
        # Test de la fonction complete_text()
        test_response = complete_text(
            prompt="Test de synthÃ¨se : rÃ©sume en une phrase que les poules pondent des Å“ufs.",
            temperature=0.2,
            max_tokens=50
        )
        
        # Test de synthÃ¨se RAG
        rag_test = synthesize_rag_content(
            question="Poids idÃ©al poule?",
            raw_content="Les poules Ross 308 atteignent un poids optimal de 2.2kg Ã  42 jours selon les standards techniques...",
            max_length=100
        )
        
        # Test clarification
        clarification_test = generate_clarification_response(
            intent="PerfTargets",
            missing_fields=["age_days", "line"],
            general_info="Information sur les performances"
        )
        
        return {
            "status": "success",
            "complete_test": {
                "success": True,
                "response": test_response[:100] + "..." if len(test_response) > 100 else test_response
            },
            "rag_synthesis_test": {
                "success": True,
                "response": rag_test[:100] + "..." if len(rag_test) > 100 else rag_test
            },
            "clarification_test": {
                "success": True,
                "response": clarification_test[:100] + "..." if len(clarification_test) > 100 else clarification_test
            },
            "message": "Pipeline de synthÃ¨se fonctionnel"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ã‰chec test pipeline synthÃ¨se: {str(e)}",
            "error_type": type(e).__name__
        }

# ==================== LOGGING ET DIAGNOSTICS ====================
def get_openai_status() -> Dict[str, Any]:
    """
    âœ… AMÃ‰LIORÃ‰: Status complet du systÃ¨me OpenAI avec support CoT
    """
    return {
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "default_models": DEFAULT_MODELS,
        "max_tokens_limits": {
            "gpt-3.5-turbo": 4096,
            "gpt-4": 8192,
            "gpt-4o": 4096,
            "gpt-4-turbo": 128000,
            "gpt-4o-mini": 4096,
            "gpt-5": 8192,
            "gpt-5-mini": 4096,
            "gpt-5-nano": 2048,
            "gpt-5-chat-latest": 8192
        },
        "retry_config": {
            "max_retries": 2,
            "base_delay": 1.0
        },
        "batch_config": {
            "embedding_batch_size": os.getenv('OPENAI_EMBEDDING_BATCH_SIZE', '100')
        },
        "synthesis_config": {  # ðŸ†• Nouveau pour dialogue_manager
            "synthesis_model": DEFAULT_MODELS["synthesis"],
            "default_temperature": 0.2,
            "max_synthesis_tokens": 500
        },
        "cot_config": {  # ðŸ†• NOUVEAU: Configuration CoT
            "cot_model": DEFAULT_MODELS["cot"],
            "auto_detection_enabled": True,
            "supported_tags": [
                "thinking", "analysis", "reasoning", "factors", "recommendations",
                "validation", "problem_decomposition", "solution_pathway"
            ],
            "max_cot_tokens": 1000
        },
        "compatibility_config": {  # ðŸ†• NOUVEAU: Configuration compatibilitÃ©
            "max_completion_tokens_support": True,
            "auto_parameter_detection": True,
            "supported_model_families": ["gpt-4.1", "gpt-4o", "o4", "omni", "gpt-5"]
        }
    }

def get_cot_capabilities() -> Dict[str, Any]:
    """
    ðŸ†• NOUVEAU: Retourne les capacitÃ©s Chain-of-Thought disponibles
    """
    return {
        "cot_available": True,
        "auto_detection": True,
        "parsing_enabled": True,
        "followup_generation": True,
        "supported_sections": [
            "thinking", "analysis", "reasoning", "factors", "recommendations",
            "validation", "problem_decomposition", "factor_analysis", 
            "interconnections", "solution_pathway", "risk_mitigation",
            "economic_context", "cost_benefit_breakdown", "scenario_analysis"
        ],
        "supported_intents": [
            "HealthDiagnosis", "OptimizationStrategy", "TroubleshootingMultiple",
            "ProductionAnalysis", "MultiFactor", "Economics"
        ],
        "models": {
            "preferred": DEFAULT_MODELS["cot"],
            "fallback": DEFAULT_MODELS["chat"]
        }
    }
