# -*- coding: utf-8 -*-
#
# main.py — Intelia LLM backend (FastAPI + SSE)
# Python 3.11+
#

import os
import re
import json
import asyncio
import time
import unicodedata
import difflib
import logging
import uuid
from typing import Any, Dict, AsyncGenerator, Optional, Tuple, List

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from langdetect import detect, DetectorFactory

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DetectorFactory.seed = 0
load_dotenv()

# -----------------------------------------------------------------------------
# Intent definitions corrigées (CORRECTION A: line requise pour broiler_weight)
# -----------------------------------------------------------------------------
INTENT_DEFS = {
    "broiler_weight": {
        "required_slots": ["age_days", "line"],  # lignée REQUISE, sex optionnel
        "optional_slots": ["sex"],
        "followup_themes": ["water_consumption", "feed_intake", "housing_conditions"],
        "description": "Questions sur le poids et croissance des poulets de chair"
    },
    "water_intake": {
        "required_slots": ["age_days"],  # Simplification similaire
        "optional_slots": ["line", "sex"],
        "followup_themes": ["water_temperature", "drinking_equipment", "water_quality"],
        "description": "Questions sur la consommation d'eau des volailles"
    },
    "feed_consumption": {
        "required_slots": ["age_days"],
        "optional_slots": ["line", "sex"],
        "followup_themes": ["nutritional_composition", "feeding_schedules", "feed_conversion"],
        "description": "Questions sur l'alimentation et consommation d'aliment"
    },
    "temperature_management": {
        "required_slots": ["age_days"],  # Âge plus important que saison
        "optional_slots": ["season"],
        "followup_themes": ["ventilation", "humidity_control", "heating_systems"],
        "description": "Questions sur la gestion thermique des bâtiments"
    },
    "disease_prevention": {
        "required_slots": ["pathogen_type", "prevention_method"],
        "optional_slots": [],
        "followup_themes": ["vaccination_programs", "biosecurity", "treatment_protocols"],
        "description": "Questions sur la prévention et traitement des maladies"
    },
    "ventilation_optimization": {
        "required_slots": ["building_type", "bird_count"],
        "optional_slots": [],
        "followup_themes": ["air_quality_sensors", "automation", "energy_efficiency"],
        "description": "Questions sur la ventilation et qualité de l'air"
    },
    "economic_analysis": {
        "required_slots": ["analysis_type", "period"],
        "optional_slots": [],
        "followup_themes": ["comparative_analysis", "cost_optimization", "profitability"],
        "description": "Questions sur l'analyse économique et rentabilité"
    }
}

# -----------------------------------------------------------------------------
# Env config
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_PATH = os.environ.get("BASE_PATH", "/llm").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
POLL_INTERVAL_SEC = float(os.environ.get("POLL_INTERVAL_SEC", "0.6"))
ASSISTANT_TIMEOUT = int(os.getenv("ASSISTANT_TIMEOUT_SEC", "30"))
ASSISTANT_MAX_POLLS = int(os.getenv("ASSISTANT_MAX_POLLS", "200"))
STREAM_CHUNK_LEN = int(os.environ.get("STREAM_CHUNK_LEN", "400"))
DEBUG_GUARD = os.getenv("DEBUG_GUARD", "0") == "1"
HYBRID_MODE = os.getenv("HYBRID_MODE", "1") == "1"
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-4o")  # Modèle plus stable

# Par défaut = 1.0 (certains modèles n'acceptent QUE la valeur par défaut)
FALLBACK_TEMPERATURE = float(os.getenv("FALLBACK_TEMPERATURE", "0.7"))  # Plus déterministe

# Alias rétro-compat : accepte l'ancienne variable si la nouvelle n'est pas fournie
FALLBACK_MAX_COMPLETION_TOKENS = int(
    os.getenv("FALLBACK_MAX_COMPLETION_TOKENS", os.getenv("FALLBACK_MAX_TOKENS", "600"))
)

FRONTEND_SSE_COMPAT = os.getenv("FRONTEND_SSE_COMPAT", "0") == "1"
LANGUAGE_FILE = os.getenv("LANGUAGE_FILE", os.path.join(BASE_DIR, "languages.json"))

# 1) Ajouter après les constantes de fichiers (près de LANGUAGE_FILE)
INTENTS_FILE = os.getenv("INTENTS_FILE", os.path.join(BASE_DIR, "intents.json"))

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
if not ASSISTANT_ID:
    raise RuntimeError("ASSISTANT_ID is required")

# -----------------------------------------------------------------------------
# 2) Ajouter un petit loader générique (près du loader languages.json)
# -----------------------------------------------------------------------------
def load_json(path: str, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Unable to load {path}: {e}")
        return fallback

# -----------------------------------------------------------------------------
# Load messages (languages.json)
# -----------------------------------------------------------------------------
def _load_language_messages(path: str) -> Dict[str, str]:
    """
    languages.json structure:
    {
      "default": "...",
      "fr": "...",
      "en": "...",
      ...
    }
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "default" not in data or not isinstance(data["default"], str):
            raise ValueError("languages.json must include a 'default' string.")
        return {(k.lower() if isinstance(k, str) else k): v for k, v in data.items()}
    except Exception as e:
        logger.error(f"Unable to load {path}: {e}")
        return {
            "default": "Intelia Expert is a poultry-focused application. Questions outside this domain cannot be processed."
        }

OUT_OF_DOMAIN_MESSAGES = _load_language_messages(LANGUAGE_FILE)

# 3) Charger la config si présente
INTENTS = load_json(INTENTS_FILE, {})

# Modification 5 : Logs de démarrage (diagnostic déploiement)
logger.info(f"LANGUAGE_FILE={LANGUAGE_FILE} exists={os.path.exists(LANGUAGE_FILE)}")
logger.info(f"INTENTS_FILE={INTENTS_FILE} exists={os.path.exists(INTENTS_FILE)}")
logger.info(f"FALLBACK_MODEL={FALLBACK_MODEL}")

def get_out_of_domain_message(lang: str) -> str:
    if not lang:
        return OUT_OF_DOMAIN_MESSAGES.get("default")
    code = (lang or "").lower()
    msg = OUT_OF_DOMAIN_MESSAGES.get(code)
    if msg:
        return msg
    short = code.split("-")[0]
    return OUT_OF_DOMAIN_MESSAGES.get(short, OUT_OF_DOMAIN_MESSAGES["default"])

# -----------------------------------------------------------------------------
# OpenAI client
# -----------------------------------------------------------------------------
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    # Test rapide de connectivité
    test_models = client.models.list()
    logger.info(f"OpenAI client initialized successfully. Available models: {len(test_models.data)}")
except Exception as e:
    logger.error(f"Erreur initialisation OpenAI client: {e}")
    raise RuntimeError(f"Impossible d'initialiser le client OpenAI: {e}")

# -----------------------------------------------------------------------------
# FastAPI
# -----------------------------------------------------------------------------
app = FastAPI(title="Intelia LLM Backend", debug=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
router = APIRouter()

# -----------------------------------------------------------------------------
# SSE helpers
# -----------------------------------------------------------------------------
def sse_event(obj: Dict[str, Any]) -> bytes:
    try:
        data = json.dumps(obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")
    except Exception as e:
        logger.error(f"Erreur formatage SSE: {e}")
        return b"data: {\"type\":\"error\",\"message\":\"Erreur formatage\"}\n\n"

def send_event(obj: Dict[str, Any]) -> bytes:
    # Schéma minimal de sécurité
    if "type" not in obj:
        obj = {"type": "final", "answer": "Désolé, une erreur de format interne est survenue."}
    if obj.get("type") == "final" and not obj.get("answer"):
        obj["answer"] = "Désolé, aucune réponse n'a pu être générée."

    # Compat front : clarifications/suivis convertis si nécessaire
    etype = obj.get("type")
    if FRONTEND_SSE_COMPAT and etype in {"clarify", "followup"}:
        text = (obj.get("answer") or obj.get("text") or "").strip()
        prefix = "Question de précision : " if etype == "clarify" else "Suggestion : "
        return sse_event({"type": "final", "answer": f"{prefix}{text}"})
    return sse_event(obj)

# -----------------------------------------------------------------------------
# Language detection
# -----------------------------------------------------------------------------
def parse_accept_language(header: Optional[str]) -> Optional[str]:
    if not header:
        return None
    try:
        first = header.split(",")[0].strip()
        code = first.split(";")[0].split("-")[0].lower()
        if 2 <= len(code) <= 3:
            return code
    except Exception:
        pass
    return None

def guess_lang_from_text(text: str) -> Optional[str]:
    try:
        return detect(text)
    except Exception:
        return None

# -----------------------------------------------------------------------------
# Text helpers
# -----------------------------------------------------------------------------
CITATION_PATTERN = re.compile(r"【[^【】]*】")

def clean_text(txt: str) -> str:
    if not txt:
        return txt
    cleaned = CITATION_PATTERN.sub("", txt)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

# -----------------------------------------------------------------------------
# Domain guard (permissif: bloque évidents hors-agri)
# -----------------------------------------------------------------------------
NON_AGRI_TERMS = [
    # médias / divertissement
    "cinéma", "film", "films", "séries", "serie", "séries tv", "netflix", "hollywood", "bollywood", "disney",
    "pixar", "musique", "concert", "rap", "pop", "rock", "jazz", "opéra", "orchestre", "télévision", "télé",
    "emission", "émission", "jeux vidéo", "gaming", "playstation", "xbox", "nintendo", "fortnite", "minecraft",
    # sports
    "football", "soccer", "nba", "nfl", "nhl", "hockey", "mlb", "tennis", "golf", "cyclisme",
    "tour de france", "formule 1", "f1", "boxe", "ufc", "olympiques",
    # politique / géopolitique
    "élections", "elections", "président", "premier ministre", "parlement", "guerre", "otan", "onu",
    # finance / crypto
    "bourse", "actions", "nasdaq", "wall street",
    "crypto", "cryptomonnaie", "cryptomonnaies", "cryptocurrency", "cryptocurrencies",
    "blockchain", "bitcoin", "ethereum",
    # tech grand public
    "iphone", "android", "samsung", "apple", "google", "microsoft",
    # santé humaine
    "cancer", "diabète", "covid", "hôpital", "clinique",
    # lifestyle
    "mode", "vêtements", "voyage", "vacances",
    # sciences hors-sujet
    "astronomie", "physique quantique", "spacex",
    # religion / ésotérisme
    "religion", "église", "astrologie", "horoscope",
]
NON_AGRI_PAT = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in NON_AGRI_TERMS) + r")\b", re.IGNORECASE)

def guard_debug(reason: str, text: str):
    if DEBUG_GUARD:
        logger.info(f"[GUARD] {reason} :: {text[:160]!r}")

def is_agri_question(text: str) -> bool:
    if not text:
        return True
    blocked = NON_AGRI_PAT.search(text) is not None
    if blocked:
        guard_debug("blocked_non_agri_match", text)
    return not blocked

# -----------------------------------------------------------------------------
# Normalization & fuzzy mapping
# -----------------------------------------------------------------------------
def normalize(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s).lower().strip()
    s = "".join(ch for ch in s if ch.isalnum() or ch.isspace())
    return re.sub(r"\s+", " ", s)

LINE_ALIASES = {
    "ross 308": ["ross308", "r308", "ross-308", "ross"],
    "cobb 500": ["cobb500", "c500", "cobb-500", "cobb"],
}
SEX_ALIASES = {
    "male": ["mâle", "masculin", "male", "garçon", "garcon"],
    "female": ["femelle", "féminin", "feminin", "female"],
}

def fuzzy_map(value: str, choices: Dict[str, List[str]], cutoff: float = 0.75) -> Optional[str]:
    v = normalize(value)
    pool = []
    for key, alias_list in choices.items():
        pool.append(key)
        pool.extend(alias_list)
    best = difflib.get_close_matches(v, pool, n=1, cutoff=cutoff)
    if not best:
        return None
    hit = best[0]
    for key, alias_list in choices.items():
        if hit == key or hit in [normalize(a) for a in alias_list]:
            return key
    return None

def guess_line_from_text(text: str) -> Optional[str]:
    """CORRECTION 2: Détection automatique de lignée dans le texte"""
    t = normalize(text or "")
    for canon, aliases in LINE_ALIASES.items():
        # match sur canon
        if normalize(canon) in t:
            return canon
        # match sur alias
        for a in aliases:
            if normalize(a) in t:
                return canon
    return None

# -----------------------------------------------------------------------------
# Chat Completions helpers (temp compat + retry)
# -----------------------------------------------------------------------------
UNSUPPORTED_TEMP_MSG = "Only the default (1) value is supported"

def _chat_args(messages, max_completion_tokens, stream=False, temperature=None):
    """
    Construit les kwargs pour client.chat.completions.create en évitant d'envoyer
    'temperature' si le modèle ne le supporte pas (ou si != 1).
    - Safe par défaut: n'envoie pas 'temperature' sauf activation explicite.
    - Permet de forcer via env FORCE_TEMPERATURE_PARAM=1 (à utiliser si ton modèle accepte la temp).
    """
    args = dict(messages=messages, max_completion_tokens=max_completion_tokens, stream=stream)
    force_temp = os.getenv("FORCE_TEMPERATURE_PARAM", "0") == "1"  # Désactivé par défaut
    if force_temp and temperature is not None:
        args["temperature"] = float(temperature)
    return args

def create_chat_completion_safe(client, model, messages, max_completion_tokens, stream=False, temperature=None):
    """
    Fait l'appel en appliquant _chat_args. Si 400 à cause de 'temperature',
    on retente immédiatement SANS 'temperature'.
    """
    try:
        kwargs = _chat_args(messages, max_completion_tokens, stream=stream, temperature=temperature)
        return client.chat.completions.create(model=model, **kwargs)
    except Exception as e:
        emsg = str(e)
        if ("Unsupported value: 'temperature'" in emsg) or ("does not support" in emsg and "temperature" in emsg):
            # retry sans temperature
            kwargs = _chat_args(messages, max_completion_tokens, stream=stream, temperature=None)
            return client.chat.completions.create(model=model, **kwargs)
        raise

# -----------------------------------------------------------------------------
# Routing & decision (GPT) - VERSION AMÉLIORÉE
# -----------------------------------------------------------------------------
def gpt_route_and_extract(client: OpenAI, text: str, lang: str) -> dict:
    """Version améliorée du routage avec prompts plus robustes"""
    system_prompt = f"""Tu es un expert en classification de questions avicoles. Analyse le texte et retourne un JSON strict.

INTENTIONS DISPONIBLES:
- broiler_weight: questions sur poids/croissance poulets de chair
- water_intake: consommation d'eau volailles  
- feed_consumption: alimentation/consommation aliment
- temperature_management: gestion thermique bâtiments
- disease_prevention: prévention/traitement maladies
- ventilation_optimization: ventilation/qualité air
- economic_analysis: analyse économique/rentabilité

EXTRACTION SLOTS:
- age_days: âge en jours (0-120), REQUIS pour questions métriques
- line: lignée (ross 308, cobb 500, etc.) - REQUIS pour broiler_weight
- sex: sexe (male/female) - OPTIONNEL
- season: saison si mentionnée - OPTIONNEL

RÈGLES:
1. Pour "poulet de X jours" → intent="broiler_weight", age_days=X
2. Si lignée incomplète ("ross", "cobb") → line=null
3. Privilégier la détection d'âge même approximatif
4. Confidence élevée si intention claire même sans tous les détails

FORMAT STRICT:
{{
  "intent_id": "broiler_weight|water_intake|feed_consumption|temperature_management|disease_prevention|ventilation_optimization|economic_analysis|null",
  "confidence": 0.0-1.0,
  "slots": {{}},
  "need_clarification": true/false
}}

Exemples:
- "Quel est le poids d'un poulet de 12 jours ?" → intent="broiler_weight", age_days=12, confidence=0.9
- "Combien pèse un ross de 3 semaines ?" → intent="broiler_weight", age_days=21, line="ross 308", confidence=0.8
"""

    try:
        resp = create_chat_completion_safe(
            client,
            model=FALLBACK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            max_completion_tokens=400,
            stream=False,
            temperature=FALLBACK_TEMPERATURE
        )
        
        raw = (resp.choices[0].message.content or "").strip()
        logger.info(f"[ROUTE] Question: {text}")
        logger.info(f"[ROUTE] Réponse GPT brute: '{raw}'")
        
        # Si réponse vide, utiliser directement le fallback
        if not raw:
            logger.warning("[ROUTE] Réponse GPT vide, utilisation du fallback")
            return _extract_intent_fallback(text)
        elif "```json" in raw:
            a = raw.find("```json") + 7
            b = raw.find("```", a)
            raw = raw[a:b].strip()
        elif "```" in raw:
            a = raw.find("```") + 3
            b = raw.find("```", a)
            raw = raw[a:b].strip()
        
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError as e:
            logger.warning(f"JSON invalide (route) [{FALLBACK_MODEL}]: {str(e)} | payload={raw[:200]}")
            # Fallback: tentative d'extraction manuelle
            data = _extract_intent_fallback(text)
            
        intent_id = data.get("intent_id") if isinstance(data, dict) else None
        if intent_id == "null":
            intent_id = None
            
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0)))) if isinstance(data, dict) else 0.0
        slots = data.get("slots", {}) if isinstance(data, dict) else {}
        
        # Post-traitement des slots
        if "line" in slots and slots["line"] in ["ross", "cobb"]:
            slots["line"] = None
            
        # CORRECTION 2: Si la lignée n'a pas été extraite, essaye de l'inférer depuis le texte
        if not slots.get("line"):
            guessed = guess_line_from_text(text)
            if guessed:
                slots["line"] = guessed
                
        if "age_days" in slots:
            try:
                age = int(slots["age_days"])
                slots["age_days"] = age if 0 <= age <= 120 else None
            except Exception:
                slots["age_days"] = None
                
        # Conversion semaines en jours si nécessaire
        if "age_weeks" in slots and not slots.get("age_days"):
            try:
                weeks = int(slots["age_weeks"])
                slots["age_days"] = weeks * 7 if 0 <= weeks <= 17 else None
                del slots["age_weeks"]
            except Exception:
                pass
                
        result = {
            "intent_id": intent_id,
            "confidence": confidence,
            "slots": slots,
            "need_clarification": bool(data.get("need_clarification", False)) if isinstance(data, dict) else False
        }
        
        logger.info(f"[ROUTE] Résultat: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Erreur routage GPT: {e}")
        # Fallback: tentative d'extraction basique
        return _extract_intent_fallback(text)

def _extract_intent_fallback(text: str) -> dict:
    """Extraction d'intention en fallback si GPT échoue"""
    text_lower = text.lower()
    
    # Détection d'âge basique
    age_days = None
    age_match = re.search(r'(\d+)\s*(?:jours?|days?|j)', text_lower)
    if age_match:
        age_days = int(age_match.group(1))
    else:
        # Tentative semaines
        week_match = re.search(r'(\d+)\s*(?:semaines?|weeks?|s)', text_lower)
        if week_match:
            age_days = int(week_match.group(1)) * 7
    
    # Détection d'intention basique
    intent_id = None
    confidence = 0.3  # Faible car extraction basique
    
    if any(word in text_lower for word in ['poids', 'weight', 'gramme', 'kg', 'croissance', 'growth']):
        intent_id = "broiler_weight"
        confidence = 0.7 if age_days else 0.5
    elif any(word in text_lower for word in ['eau', 'water', 'boisson', 'drink']):
        intent_id = "water_intake"
        confidence = 0.6 if age_days else 0.4
    elif any(word in text_lower for word in ['aliment', 'feed', 'nutrition', 'mange']):
        intent_id = "feed_consumption"
        confidence = 0.6 if age_days else 0.4
    
    slots = {}
    if age_days is not None:
        slots["age_days"] = age_days
        
    # CORRECTION 2: Deviner la lignée si possible dans le fallback
    gl = guess_line_from_text(text)
    if gl:
        slots["line"] = gl
        
    return {
        "intent_id": intent_id,
        "confidence": confidence,
        "slots": slots,
        "need_clarification": False
    }

async def gpt_decide_answer_or_clarify(client: OpenAI, lang: str, intent_id: str, slots: Dict, user_text: str) -> Dict[str, Any]:
    """CORRECTION B: Logique stricte pour forcer la clarification quand line manque"""
    intent_cfg = (INTENTS.get("intents", {}).get(intent_id) 
                  if isinstance(INTENTS.get("intents"), dict) else {})
    if not intent_cfg:  # fallback sur les defs locales si fichier absent
        intent_cfg = INTENT_DEFS.get(intent_id, {})
        
    intent_desc = intent_cfg.get("description", "question avicole")
    required_slots = intent_cfg.get("required_slots", [])
    optional_slots = intent_cfg.get("optional_slots", [])
    followup_themes = intent_cfg.get("followup_themes", [])
    
    # CORRECTION B: Logique spéciale pour broiler_weight (stricte pour lignée)
    if intent_id == "broiler_weight":
        has_age = slots.get("age_days") is not None
        has_line = slots.get("line") is not None
        if not has_age:
            return {
                "answer_mode": "clarify",
                "clarify_question": "Quel âge ont les poulets (en jours) ?",
                "missing": ["age_days"],
                "followup_suggestion": ""
            }
        if not has_line:
            # Comportement attendu : clarifier la lignée AVANT de répondre
            return {
                "answer_mode": "clarify",
                "clarify_question": "Pour préciser la réponse, de quelle lignée s'agit-il (Ross 308, Cobb 500, ...) ?",
                "missing": ["line"],
                "followup_suggestion": ""
            }
        # âge + lignée présents → on peut répondre
        return {
            "answer_mode": "direct",
            "clarify_question": "",
            "missing": [],
            "followup_suggestion": "Souhaitez-vous aussi la courbe de croissance standard ?"
        }
    
    # Logique générique pour autres intents
    system_prompt = f"""Tu es un système de décision pour un assistant avicole.
INTENTION: {intent_desc}
SLOTS REQUIS: {', '.join(required_slots)}
SLOTS OPTIONNELS: {', '.join(optional_slots)}
SLOTS DÉTECTÉS: {json.dumps(slots)}

Réponds avec un JSON:
{{
  "answer_mode": "direct|partial|clarify",
  "clarify_question": "…",
  "missing": ["…"],
  "followup_suggestion": "…"
}}

Règles:
- Si slots essentiels présents → "direct"
- Si certains slots présents → "partial" + followup
- Si aucun slot critique → "clarify"
- Favoriser 'partial' vs 'clarify' excessif
- Question courte en {lang}
"""
    
    try:
        resp = await asyncio.to_thread(
            create_chat_completion_safe,
            client,
            FALLBACK_MODEL,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            300,
            False,
            FALLBACK_TEMPERATURE
        )
        
        raw = (resp.choices[0].message.content or "").strip()
        if "```json" in raw:
            a = raw.find("```json") + 7
            b = raw.find("```", a)
            raw = raw[a:b].strip()
        elif "```" in raw:
            a = raw.find("```") + 3
            b = raw.find("```", a)
            raw = raw[a:b].strip()
            
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError as e:
            logger.warning(f"JSON invalide (decision) [{FALLBACK_MODEL}]: {str(e)} | payload={raw[:200]}")
            data = {}
            
        result = {
            "answer_mode": (data.get("answer_mode", "direct") if isinstance(data, dict) else "direct"),
            "clarify_question": (data.get("clarify_question", "") if isinstance(data, dict) else ""),
            "missing": (data.get("missing", []) if isinstance(data, dict) else []),
            "followup_suggestion": (data.get("followup_suggestion", "") if isinstance(data, dict) else "")
        }
        
        logger.info(f"[DECISION] intent={intent_id}, mode={result['answer_mode']}, "
                    f"missing={result['missing']}, slots={slots}")
        return result
        
    except Exception as e:
        logger.error(f"Erreur décision GPT: {e}")
        
        # Fallback basé sur les slots requis
        req = set(required_slots)
        missing = [k for k in req if (slots.get(k) in (None, "", []))]
        
        if missing:
            return {
                "answer_mode": "clarify",
                "clarify_question": "Pouvez-vous préciser ces informations pour une réponse optimale ?",
                "missing": missing,
                "followup_suggestion": ""
            }
        else:
            return {
                "answer_mode": "direct",
                "clarify_question": "",
                "missing": [],
                "followup_suggestion": ""
            }

# Clarify & follow-up text generation
async def generate_clarification_question(client: OpenAI, intent_id: str, missing_slots: List[str], user_text: str) -> Tuple[str, Dict[str, Any]]:
    """CORRECTION C: Suggestions de lignée cohérentes dans le clarify"""
    intent_cfg = (INTENTS.get("intents", {}).get(intent_id) 
                  if isinstance(INTENTS.get("intents"), dict) else {})
    if not intent_cfg:  # fallback sur les defs locales si fichier absent
        intent_cfg = INTENT_DEFS.get(intent_id, {})
    intent_desc = intent_cfg.get("description", "question avicole")
    
    # Questions par défaut selon les slots manquants
    questions_map = {
        "line": "De quelle lignée s'agit-il ?",
        "age_days": "Quel âge ont les animaux (en jours) ?",
        "age_weeks": "Quel âge ont les animaux (en semaines) ?",
        "bird_type": "Quel type d'animal : poulet de chair, pondeuse, poulette ?",
        "site_type": "Quel type d'élevage : broiler, pondeuse, couvoir ?",
        "metric": "Quelle information recherchez-vous précisément ?",
        "sex": "Sexe des animaux : mâle, femelle ou mixte ?",
        "season": "À quelle saison : été, hiver, printemps, automne ?"
    }
    
    # CORRECTION 3: Construire la question avec suggestions systématiques
    if len(missing_slots) == 1:
        question = questions_map.get(missing_slots[0], f"Précisez: {missing_slots[0]}")
    else:
        question = f"Pour préciser, indiquez: {', '.join(missing_slots)}"
    
    # CORRECTION C: Suggestions par slot avec valeurs cohérentes
    suggestions = {}
    for slot in missing_slots:
        if slot == "line":
            if "layer" in user_text.lower() or "pondeuse" in user_text.lower():
                suggestions["line"] = ["ISA Brown","Lohmann Brown","Lohmann White","Hy-Line Brown"]
            else:
                suggestions["line"] = ["Ross 308","Cobb 500","Ross 708","Hubbard JA757"]
        elif slot == "sex":
            suggestions["sex"] = ["male", "female", "mixed"]
        elif slot == "season":
            suggestions["season"] = ["summer", "winter", "spring", "autumn"]
        elif slot == "bird_type":
            suggestions["bird_type"] = ["broiler", "layer", "pullet", "breeder"]
        elif slot == "site_type":
            suggestions["site_type"] = ["broiler_farm", "layer_farm", "rearing_farm", "breeding_farm"]
        elif slot == "phase":
            suggestions["phase"] = ["starter", "grower", "finisher"]
    
    return question, suggestions

async def generate_followup_suggestion(client: OpenAI, intent_id: str, user_text: str, response_context: str = "") -> Optional[str]:
    intent_cfg = (INTENTS.get("intents", {}).get(intent_id) 
                  if isinstance(INTENTS.get("intents"), dict) else {})
    if not intent_cfg:  # fallback sur les defs locales si fichier absent
        intent_cfg = INTENT_DEFS.get(intent_id, {})
    intent_desc = intent_cfg.get("description", "question avicole")
    followup_themes = intent_cfg.get("followup_themes", [])
    system_prompt = f"""Assistant avicole. Sujet: {intent_desc}
Thèmes: {', '.join(followup_themes)}
Donne UNE question de suivi pertinente, en une phrase, même langue que l'utilisateur."""
    try:
        resp = await asyncio.to_thread(
            create_chat_completion_safe,
            client,
            FALLBACK_MODEL,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": response_context[:200] if response_context else user_text}
            ],
            100,
            False,
            FALLBACK_TEMPERATURE
        )
        return (resp.choices[0].message.content or "").strip() or None
    except Exception as e:
        logger.error(f"Erreur génération followup: {e}")
        return None

def get_default_followup_by_intent(intent_id: str) -> Optional[str]:
    defaults = {
        "broiler_weight": "Souhaitez-vous connaître les facteurs qui influencent cette croissance ?",
        "water_intake": "Voulez-vous des conseils sur l'optimisation de l'abreuvement ?",
        "feed_consumption": "Aimeriez-vous des informations sur l'optimisation nutritionnelle ?",
        "temperature_management": "Désirez-vous des conseils sur la ventilation associée ?",
        "disease_prevention": "Souhaitez-vous des informations sur les programmes de vaccination ?",
        "ventilation_optimization": "Voulez-vous des détails sur les systèmes de contrôle automatisés ?",
        "economic_analysis": "Aimeriez-vous une analyse comparative avec les standards du secteur ?"
    }
    return defaults.get(intent_id)

async def ensure_followup_suggestion(client: OpenAI, intent_id: str, user_text: str, response_context: str, confidence: float) -> Optional[str]:
    intent_cfg = (INTENTS.get("intents", {}).get(intent_id) 
                  if isinstance(INTENTS.get("intents"), dict) else {})
    if not intent_cfg:
        return None
    followup = await generate_followup_suggestion(client, intent_id, user_text, response_context)
    return followup or get_default_followup_by_intent(intent_id)

# -----------------------------------------------------------------------------
# Data-only (Assistant v2) - CORRECTION D: Prompt durci pour éviter réponses génériques
# -----------------------------------------------------------------------------
def run_data_only_assistant(client: OpenAI, assistant_id: str, user_text: str, lang: str) -> str:
    """CORRECTION D: Version avec prompt durci contre les réponses génériques"""
    reminder = (
        f"INSTRUCTIONS STRICTES:\n"
        f"1. RÉPONDS EXCLUSIVEMENT à partir des documents du Vector Store\n"
        f"2. Si des informations essentielles manquent (ex. lignée ou âge pour une valeur cible), NE RÉPONDS PAS et POSE UNE SEULE question de clarification courte\n"
        f"3. Si l'information est totalement absente, réponds: \"Hors base: information absente de la connaissance Intelia.\"\n"
        f"4. TOUJOURS répondre dans la langue de la question: {lang}\n"
        f"5. N'utilise PAS de valeurs 'génériques' si la lignée conditionne la réponse\n\n"
        f"Question utilisateur: {user_text}"
    )
    
    try:
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id, 
            role="user", 
            content=reminder
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread.id, 
            assistant_id=assistant_id
        )
        
        timeout = time.time() + ASSISTANT_TIMEOUT
        polls = 0
        
        while time.time() < timeout and polls < ASSISTANT_MAX_POLLS:
            r = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if r.status in ("completed", "failed", "cancelled", "expired"):
                break
            time.sleep(POLL_INTERVAL_SEC)
            polls += 1
        
        logger.info(f"[ASSISTANT] Status: {r.status} après {polls} polls")
        
        if r.status != "completed":
            logger.error(f"Assistant run failed with status: {r.status}")
            return "Hors base: information absente de la connaissance Intelia."
        
        msgs = client.beta.threads.messages.list(thread_id=thread.id)
        msgs_data = msgs.data
        
        if len(msgs_data) == 1:
            latest = msgs_data[0] if msgs_data[0].role == "assistant" else None
        else:
            latest = next(
                (m for m in sorted(msgs_data, key=lambda x: x.created_at, reverse=True) if m.role == "assistant"),
                None
            )
        
        if latest:
            for c in latest.content:
                if getattr(c, "type", "") == "text":
                    txt = clean_text((c.text.value or "").strip())
                    if txt:
                        logger.info(f"[ASSISTANT] Réponse: {txt[:100]}...")
                        return txt
        
        return "Hors base: information absente de la connaissance Intelia."
        
    except Exception as e:
        logger.error(f"Erreur assistant data-only: {e}")
        return "Hors base: information absente de la connaissance Intelia."

# -----------------------------------------------------------------------------
# Fallback general (stream)
# -----------------------------------------------------------------------------
async def stream_fallback_general(client: OpenAI, text: str):
    system = (
        "Tu es un assistant spécialisé en agriculture et aviculture. "
        "Tu remponds UNIQUEMENT aux questions dans ce domaine. "
        "Si la question sort du cadre, refuse poliment. "
        "Réponds dans la MÊME langue que la question de l'utilisateur. "
        "Sois précis et technique quand approprié."
    )
    try:
        stream = create_chat_completion_safe(
            client,
            model=FALLBACK_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
            max_completion_tokens=FALLBACK_MAX_COMPLETION_TOKENS,
            stream=True,
            temperature=FALLBACK_TEMPERATURE
        )
        final_buf = []
        for event in stream:
            if hasattr(event, "choices") and event.choices:
                delta = event.choices[0].delta
                if delta and getattr(delta, "content", None):
                    chunk = clean_text(delta.content)
                    final_buf.append(chunk)
                    yield send_event({"type": "delta", "text": chunk})
        final_text = clean_text("".join(final_buf).strip())
        if not final_text:
            final_text = "Désolé, aucune réponse n'a pu être générée. Pouvez-vous reformuler ou préciser votre question ?"
        yield send_event({"type": "final", "answer": final_text})
    except Exception as e:
        # Modification 3 : Fallback non-stream si le modèle refuse le streaming
        if "must be verified to stream" in str(e).lower() or "param': 'stream'" in str(e).lower():
            resp = create_chat_completion_safe(
                client, model=FALLBACK_MODEL,
                messages=[{"role":"system","content":system},{"role":"user","content":text}],
                max_completion_tokens=FALLBACK_MAX_COMPLETION_TOKENS, stream=False, temperature=FALLBACK_TEMPERATURE
            )
            final_text = clean_text(resp.choices[0].message.content or "") or "Désolé, aucune réponse n'a pu être générée."
            yield send_event({"type":"final","answer":final_text})
            return
        # sinon, erreur générique
        logger.error(f"Erreur fallback streaming: {e}")
        yield send_event({"type": "final", "answer": "Désolé, une erreur est survenue et la réponse n'a pas pu être générée."})

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.get("/health")
def health():
    return {
        "ok": True,
        "assistant_id": ASSISTANT_ID,
        "guard_mode": "permissive_non_agri",
        "debug_guard": DEBUG_GUARD,
        "hybrid_mode": HYBRID_MODE,
        "frontend_sse_compat": FRONTEND_SSE_COMPAT,
        "language_file": LANGUAGE_FILE,
        "intents_file": INTENTS_FILE,
        "fallback_model": FALLBACK_MODEL,
        "languages_loaded": list(OUT_OF_DOMAIN_MESSAGES.keys())[:10] + (["…"] if len(OUT_OF_DOMAIN_MESSAGES) > 10 else []),
        "intents_loaded": list(INTENTS.get("intents", {}).keys()) if isinstance(INTENTS.get("intents"), dict) else []
    }

@router.post("/chat/stream")
async def chat_stream(request: Request):
    """
    JSON attendu: { "tenant_id": "ten_123", "message": "...", "allow_fallback": true }
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Erreur parsing JSON: {e}")
        raise HTTPException(status_code=400, detail="invalid_json")

    tenant_id = (payload.get("tenant_id") or "").strip()
    message = (payload.get("message") or "").strip()
    allow_fallback = bool(payload.get("allow_fallback", True))

    if not tenant_id or not message:
        raise HTTPException(status_code=400, detail="missing_fields")
    if len(message) > 10000:
        raise HTTPException(status_code=400, detail="message_too_long")
    if len(message) < 2:
        raise HTTPException(status_code=400, detail="message_too_short")
    if "\x00" in message:
        raise HTTPException(status_code=400, detail="message_invalid_chars")

    # Langue = celle de la question (prioritaire). Accept-Language en secours.
    accept_lang = request.headers.get("accept-language")
    lang = guess_lang_from_text(message) or parse_accept_language(accept_lang) or "fr"
    lang = (lang or "fr")[:5].split("-")[0].lower()

    request_id = str(uuid.uuid4())
    logger.info(f"[REQ {request_id}] tenant={tenant_id}, lang={lang}, message='{message[:50]}...'")

    # Modification 1 : Type du générateur SSE (AsyncGenerator[bytes, None] au lieu de str)
    async def event_source() -> AsyncGenerator[bytes, None]:
        sent_final = False
        try:
            # 1) Garde-fou: hors-domaine => message fixe depuis languages.json
            if not is_agri_question(message):
                answer = clean_text(get_out_of_domain_message(lang))
                yield send_event({"type": "final", "answer": answer})
                sent_final = True
                return

            # Modification 6 : Éviter un client OpenAI par requête (réutilise le client global)
            _client = client

            # 2) Routage intention & slots AMÉLIORÉ
            route = await asyncio.to_thread(gpt_route_and_extract, _client, message, lang)
            intent_id = route.get("intent_id")
            confidence = float(route.get("confidence") or 0.0)
            slots = route.get("slots") or {}
            logger.info(f"[REQ {request_id}] ROUTE intent={intent_id}, conf={confidence:.2f}, slots={slots}")

            # 3) Décision clarifier / répondre AMÉLIORÉE
            followup_hint = None
            if intent_id:
                intent_cfg = (INTENTS.get("intents", {}).get(intent_id) 
                              if isinstance(INTENTS.get("intents"), dict) else {})
                if not intent_cfg:  # fallback sur les defs locales si fichier absent
                    intent_cfg = INTENT_DEFS.get(intent_id, {})
                    
                if intent_cfg:  # on a une configuration pour cette intention
                    decision = await gpt_decide_answer_or_clarify(_client, lang, intent_id, slots, message)
                    answer_mode = decision.get("answer_mode", "direct")
                    followup_hint = decision.get("followup_suggestion") or followup_hint
                    
                    if answer_mode == "clarify":
                        clarify_q = clean_text(decision.get("clarify_question") or "")
                        if not clarify_q:
                            missing = decision.get("missing", [])
                            clarify_q, suggestions = await generate_clarification_question(_client, intent_id, missing, message)
                        else:
                            missing = decision.get("missing", [])
                            suggestions = {}
                            if "line" in missing:
                                suggestions["line"] = ["Ross 308", "Cobb 500"]
                            if "sex" in missing:
                                suggestions["sex"] = ["male", "female"]
                            if "season" in missing:
                                suggestions["season"] = ["summer", "winter", "spring", "autumn"]
                        if not clarify_q:
                            clarify_q = "Pour répondre précisément, merci de préciser les informations manquantes."
                        payload_clarify = {"type": "clarify", "answer": clarify_q}
                        if suggestions:
                            payload_clarify["suggestions"] = suggestions
                        yield send_event(payload_clarify)
                        # CORRECTION 1: IMPORTANT : éviter que le 'finally' envoie un final d'excuse
                        sent_final = True
                        return

            # 4) Tentative data-only (Assistant v2) AMÉLIORÉE
            text = await asyncio.to_thread(run_data_only_assistant, _client, ASSISTANT_ID, message, lang)
            text = clean_text(text)
            logger.info(f"[REQ {request_id}] Assistant response: {text[:100]}...")

            # 5) Fallback GPT si hors base
            if text.lower().startswith("hors base"):
                if HYBRID_MODE and allow_fallback:
                    logger.info(f"[REQ {request_id}] Basculement vers fallback GPT")
                    async for sse in stream_fallback_general(_client, message):
                        yield sse  # le fallback stream envoie un final non-vide
                    # Follow-up après fallback
                    final_followup = followup_hint or await ensure_followup_suggestion(_client, intent_id, message, "", confidence)
                    if final_followup:
                        yield send_event({"type": "followup", "answer": final_followup})
                    return
                else:
                    yield send_event({"type": "final", "answer": text})
                    sent_final = True
                    return

            # 6) Réponse data-only (stream simulé) AMÉLIORÉE
            if not text:
                text = "Désolé, aucune réponse n'a pu être générée."
                
            for i in range(0, len(text), STREAM_CHUNK_LEN):
                chunk = clean_text(text[i:i + STREAM_CHUNK_LEN])
                if chunk:
                    yield send_event({"type": "delta", "text": chunk})
                    await asyncio.sleep(0.02)
                    
            final_answer = text
            yield send_event({"type": "final", "answer": final_answer})
            sent_final = True

            # 7) Follow-up systématique
            final_followup = followup_hint or await ensure_followup_suggestion(_client, intent_id, message, text[:200], confidence)
            if final_followup:
                yield send_event({"type": "followup", "answer": final_followup})

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[REQ {request_id}] Erreur dans event_source: {e}")
            if not sent_final:
                yield send_event({"type": "final", "answer": "Désolé, une erreur est survenue et la réponse n'a pas pu être générée."})
            else:
                yield send_event({"type": "error", "message": f"Erreur interne: {str(e)}"})
        finally:
            if not sent_final:
                yield send_event({"type": "final", "answer": "Désolé, aucune réponse n'a pu être générée."})

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
    }
    return StreamingResponse(event_source(), headers=headers)

# -----------------------------------------------------------------------------
# Mount router & misc
# -----------------------------------------------------------------------------
app.include_router(router, prefix=BASE_PATH)

@app.get("/")
def root():
    return JSONResponse({"service": "intelia-llm", "sse": f"{BASE_PATH}/chat/stream", "version": "corrected"})

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow: /\n"

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {exc}")
    return JSONResponse(status_code=500, content={"detail": f"Erreur interne du serveur: {str(exc)}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)