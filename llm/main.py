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
# Intent definitions (sex optionnel pour broiler_weight)
# -----------------------------------------------------------------------------
INTENT_DEFS = {
    "broiler_weight": {
        "required_slots": ["age_days", "line"],  # sex optionnel
        "optional_slots": ["sex"],
        "followup_themes": ["water_consumption", "feed_intake", "housing_conditions"],
        "description": "Questions sur le poids et croissance des poulets de chair"
    },
    "water_intake": {
        "required_slots": ["age_days", "line"],
        "optional_slots": ["sex"],
        "followup_themes": ["water_temperature", "drinking_equipment", "water_quality"],
        "description": "Questions sur la consommation d'eau des volailles"
    },
    "feed_consumption": {
        "required_slots": ["age_days", "line"],
        "optional_slots": ["sex"],
        "followup_themes": ["nutritional_composition", "feeding_schedules", "feed_conversion"],
        "description": "Questions sur l'alimentation et consommation d'aliment"
    },
    "temperature_management": {
        "required_slots": ["age_days", "season"],
        "optional_slots": [],
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
BASE_PATH = os.environ.get("BASE_PATH", "/llm").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
POLL_INTERVAL_SEC = float(os.environ.get("POLL_INTERVAL_SEC", "0.6"))
STREAM_CHUNK_LEN = int(os.environ.get("STREAM_CHUNK_LEN", "400"))
DEBUG_GUARD = os.getenv("DEBUG_GUARD", "0") == "1"
HYBRID_MODE = os.getenv("HYBRID_MODE", "1") == "1"
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-5")
FALLBACK_TEMPERATURE = float(os.getenv("FALLBACK_TEMPERATURE", "0.2"))
FALLBACK_MAX_TOKENS = int(os.getenv("FALLBACK_MAX_TOKENS", "600"))
FRONTEND_SSE_COMPAT = os.getenv("FRONTEND_SSE_COMPAT", "1") == "1"
LANGUAGE_FILE = os.getenv("LANGUAGE_FILE", "languages.json")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
if not ASSISTANT_ID:
    raise RuntimeError("ASSISTANT_ID is required")

# -----------------------------------------------------------------------------
# Load messages (languages.json)
# -----------------------------------------------------------------------------
def _load_language_messages(path: str) -> Dict[str, str]:
    """
    languages.json structure example:
    {
      "default": "…",
      "fr": "…",
      "en": "…",
      "es": "…",
      ...
    }
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "default" not in data or not isinstance(data["default"], str):
            raise ValueError("languages.json must include a 'default' string.")
        # normalize keys
        return { (k.lower() if isinstance(k, str) else k): v for k, v in data.items() }
    except Exception as e:
        logger.error(f"Unable to load {path}: {e}")
        # hard fallback (English)
        return {
            "default": "Intelia Expert is a poultry-focused application. Questions outside this domain cannot be processed."
        }

OUT_OF_DOMAIN_MESSAGES = _load_language_messages(LANGUAGE_FILE)

def get_out_of_domain_message(lang: str) -> str:
    """
    Returns the out-of-domain message in the question language.
    - Exact hit on 'xx'
    - Fallback tries first two letters (just in case)
    - Then 'default'
    """
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
    "cinéma", "film", "films", "séries", "serie", "séries tv", "netflix", "hollywood", "bollywood", "disney",
    "pixar", "musique", "concert", "rap", "pop", "rock", "jazz", "opéra", "orchestre", "télévision", "télé",
    "emission", "émission", "jeux vidéo", "gaming", "playstation", "xbox", "nintendo", "fortnite", "minecraft",
    "football", "soccer", "nba", "nfl", "nhl", "hockey", "mlb", "tennis", "golf", "cyclisme",
    "tour de france", "formule 1", "f1", "boxe", "ufc", "olympiques",
    "élections", "elections", "président", "premier ministre", "parlement", "guerre", "otan", "onu",
    "bourse", "actions", "nasdaq", "wall street", "crypto",
    "iphone", "android", "samsung", "apple", "google", "microsoft",
    "cancer", "diabète", "covid", "hôpital", "clinique",
    "mode", "vêtements", "voyage", "vacances",
    "astronomie", "physique quantique", "spacex",
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

# -----------------------------------------------------------------------------
# Routing & decision (GPT)
# -----------------------------------------------------------------------------
def gpt_route_and_extract(client: OpenAI, text: str, lang: str) -> dict:
    system_prompt = f"""Tu es un système de classification pour questions avicoles. Analyse le texte et retourne un JSON strict avec :
{{
  "intent_id": "broiler_weight|water_intake|feed_consumption|temperature_management|disease_prevention|ventilation_optimization|economic_analysis|null",
  "confidence": 0.0-1.0,
  "slots": {{}},
  "need_clarification": true/false
}}
Règles :
- line = 'ross 308' ou 'cobb 500' (si 'ross' ou 'cobb' seul => null)
- age_days entier 0..70
- sex optionnel
- Réponds uniquement en JSON
"""
    try:
        resp = client.chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=400
        )
        raw = resp.choices[0].message.content.strip()
        if "```json" in raw:
            a = raw.find("```json") + 7
            b = raw.find("```", a)
            raw = raw[a:b].strip()
        elif "```" in raw:
            a = raw.find("```") + 3
            b = raw.find("```", a)
            raw = raw[a:b].strip()
        data = json.loads(raw)
        intent_id = data.get("intent_id")
        if intent_id == "null":
            intent_id = None
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        slots = data.get("slots", {})
        if "line" in slots and slots["line"] in ["ross", "cobb"]:
            slots["line"] = None
        if "age_days" in slots:
            try:
                age = int(slots["age_days"])
                slots["age_days"] = age if 0 <= age <= 70 else None
            except Exception:
                slots["age_days"] = None
        return {"intent_id": intent_id, "confidence": confidence, "slots": slots,
                "need_clarification": bool(data.get("need_clarification", False))}
    except Exception as e:
        logger.error(f"Erreur routage GPT: {e}")
        return {"intent_id": None, "confidence": 0.0, "slots": {}, "need_clarification": False}

async def gpt_decide_answer_or_clarify(client: OpenAI, lang: str, intent_id: str, slots: Dict, user_text: str) -> Dict[str, Any]:
    intent_desc = INTENT_DEFS.get(intent_id, {}).get("description", "question avicole")
    required_slots = INTENT_DEFS.get(intent_id, {}).get("required_slots", [])
    optional_slots = INTENT_DEFS.get(intent_id, {}).get("optional_slots", [])
    followup_themes = INTENT_DEFS.get(intent_id, {}).get("followup_themes", [])
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
- broiler_weight: direct/partial si age_days ET line présents (sex optionnel)
- Favoriser 'partial' + followup vs 'clarify' abusif
- Question de clarification courte en {lang}
"""
    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=FALLBACK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.1,
            max_tokens=300
        )
        raw = resp.choices[0].message.content.strip()
        if "```json" in raw:
            a = raw.find("```json") + 7
            b = raw.find("```", a)
            raw = raw[a:b].strip()
        elif "```" in raw:
            a = raw.find("```") + 3
            b = raw.find("```", a)
            raw = raw[a:b].strip()
        data = json.loads(raw)
        logger.info(f"[DECISION] intent={intent_id}, mode={data.get('answer_mode')}, missing={data.get('missing')}, slots={slots}")
        return {
            "answer_mode": data.get("answer_mode", "direct"),
            "clarify_question": data.get("clarify_question", ""),
            "missing": data.get("missing", []),
            "followup_suggestion": data.get("followup_suggestion", "")
        }
    except Exception as e:
        logger.error(f"Erreur décision GPT: {e}")
        req = set(required_slots)
        missing = [k for k in req if (slots.get(k) in (None, "", []))]
        if intent_id == "broiler_weight" and missing:
            if (slots.get("age_days") is not None) or (slots.get("line") is not None):
                return {
                    "answer_mode": "partial",
                    "clarify_question": "",
                    "missing": missing,
                    "followup_suggestion": "Souhaitez-vous des informations plus spécifiques selon la lignée ou le sexe ?"
                }
        return {
            "answer_mode": "clarify" if missing else "direct",
            "clarify_question": "Pouvez-vous préciser ces informations pour une réponse optimale ?",
            "missing": missing,
            "followup_suggestion": ""
        }

# Clarify & follow-up text generation
async def generate_clarification_question(client: OpenAI, intent_id: str, missing_slots: List[str], user_text: str) -> Tuple[str, Dict[str, Any]]:
    intent_desc = INTENT_DEFS.get(intent_id, {}).get("description", "question avicole")
    required_slots = INTENT_DEFS.get(intent_id, {}).get("required_slots", [])
    system_prompt = f"""Assistant avicole. Sujet: {intent_desc}
Slots requis: {', '.join(required_slots)}
Manquants: {', '.join(missing_slots)}
Donne UNE question courte (langue de l'utilisateur) demandant UNIQUEMENT les infos manquantes."""
    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=FALLBACK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.1,
            max_tokens=120
        )
        question = (resp.choices[0].message.content or "").strip()
        suggestions = {}
        if "line" in missing_slots:
            suggestions["lines"] = ["Ross 308", "Cobb 500"]
        if "sex" in missing_slots:
            suggestions["sex"] = ["male", "female"]
        if "season" in missing_slots:
            suggestions["season"] = ["summer", "winter", "spring", "autumn"]
        return question, suggestions
    except Exception as e:
        logger.error(f"Erreur génération clarification: {e}")
        return "Pour répondre précisément, merci de préciser les informations manquantes.", {}

async def generate_followup_suggestion(client: OpenAI, intent_id: str, user_text: str, response_context: str = "") -> Optional[str]:
    intent_desc = INTENT_DEFS.get(intent_id, {}).get("description", "question avicole")
    followup_themes = INTENT_DEFS.get(intent_id, {}).get("followup_themes", [])
    system_prompt = f"""Assistant avicole. Sujet: {intent_desc}
Thèmes: {', '.join(followup_themes)}
Donne UNE question de suivi pertinente, en une phrase, même langue que l'utilisateur."""
    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=FALLBACK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": response_context[:200] if response_context else user_text}
            ],
            temperature=0.3,
            max_tokens=80
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
    if intent_id not in INTENT_DEFS:
        return None
    followup = await generate_followup_suggestion(client, intent_id, user_text, response_context)
    return followup or get_default_followup_by_intent(intent_id)

# -----------------------------------------------------------------------------
# Data-only (Assistant v2)
# -----------------------------------------------------------------------------
def run_data_only_assistant(client: OpenAI, assistant_id: str, user_text: str, lang: str) -> str:
    reminder = (
        "RÉPONDS EXCLUSIVEMENT à partir des documents du Vector Store. "
        "SI DES INFORMATIONS ESSENTIELLES MANQUENT POUR RÉPONDRE PRÉCISÉMENT "
        "(ex. lignée, sexe, âge en jours, période), POSE D'ABORD UNE QUESTION DE CLARIFICATION "
        "courte listant uniquement les éléments manquants, puis attends la réponse. "
        "Si l'information est absente de la base, réponds exactement : "
        "\"Hors base: information absente de la connaissance Intelia.\" "
        f"Réponds dans la même langue que la question de l'utilisateur."
    )
    try:
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=f"{user_text}\n\n{reminder}"
        )
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)
        timeout = time.time() + 30
        while time.time() < timeout:
            r = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if r.status in ("completed", "failed", "cancelled", "expired"):
                break
            time.sleep(POLL_INTERVAL_SEC)
        if r.status != "completed":
            logger.error(f"Assistant run failed with status: {r.status}")
            return "Hors base: information absente de la connaissance Intelia."
        msgs = client.beta.threads.messages.list(thread_id=thread.id)
        latest = next((m for m in sorted(msgs.data, key=lambda x: x.created_at, reverse=True) if m.role == "assistant"), None)
        if latest:
            for c in latest.content:
                if getattr(c, "type", "") == "text":
                    txt = clean_text((c.text.value or "").strip())
                    return txt if txt else "Hors base: information absente de la connaissance Intelia."
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
        "Tu réponds UNIQUEMENT aux questions dans ce domaine. "
        "Si la question sort du cadre, refuse poliment. "
        "Réponds dans la MÊME langue que la question de l'utilisateur."
    )
    try:
        stream = client.chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
            temperature=FALLBACK_TEMPERATURE,
            max_tokens=FALLBACK_MAX_TOKENS,
            stream=True,
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
        yield send_event({"type": "final", "answer": final_text})
    except Exception as e:
        logger.error(f"Erreur fallback streaming: {e}")
        yield send_event({"type": "error", "message": f"Erreur technique: {str(e)}"})

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
        "languages_loaded": list(OUT_OF_DOMAIN_MESSAGES.keys())[:10] + (["…"] if len(OUT_OF_DOMAIN_MESSAGES) > 10 else [])
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

    # Langue = celle de la question (prioritaire). On garde Accept-Language en secours.
    accept_lang = request.headers.get("accept-language")
    lang = guess_lang_from_text(message) or parse_accept_language(accept_lang) or "fr"
    lang = (lang or "fr")[:5].split("-")[0].lower()

    async def event_source() -> AsyncGenerator[str, None]:
        try:
            # 1) Garde-fou: hors-domaine => message fixe depuis languages.json
            if not is_agri_question(message):
                answer = clean_text(get_out_of_domain_message(lang))
                yield send_event({"type": "final", "answer": answer})
                return

            _client = OpenAI(api_key=OPENAI_API_KEY)

            # 2) Routage intention & slots
            route = await asyncio.to_thread(gpt_route_and_extract, _client, message, lang)
            intent_id = route.get("intent_id")
            confidence = float(route.get("confidence") or 0.0)
            slots = route.get("slots") or {}
            logger.info(f"[ROUTE] intent={intent_id}, confidence={confidence:.2f}, slots={slots}")

            # 3) Décision clarifier / répondre
            followup_hint = None
            if intent_id in INTENT_DEFS:
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
                            suggestions["lines"] = ["Ross 308", "Cobb 500"]
                        if "sex" in missing:
                            suggestions["sex"] = ["male", "female"]
                        if "season" in missing:
                            suggestions["season"] = ["summer", "winter", "spring", "autumn"]
                    payload_clarify = {"type": "clarify", "answer": clarify_q}
                    if suggestions:
                        payload_clarify["suggestions"] = suggestions
                    yield send_event(payload_clarify)
                    return

            # 4) Tentative data-only (Assistant v2)
            text = await asyncio.to_thread(run_data_only_assistant, _client, ASSISTANT_ID, message, lang)
            text = clean_text(text)

            # 5) Fallback GPT si hors base
            if text.lower().startswith("hors base"):
                if HYBRID_MODE and allow_fallback:
                    async for sse in stream_fallback_general(_client, message):
                        yield sse
                    final_followup = followup_hint or await ensure_followup_suggestion(_client, intent_id, message, "", confidence)
                    if final_followup:
                        yield send_event({"type": "followup", "answer": final_followup})
                    return
                else:
                    yield send_event({"type": "final", "answer": text})
                    return

            # 6) Réponse data-only (stream simulé)
            for i in range(0, len(text), STREAM_CHUNK_LEN):
                chunk = clean_text(text[i:i + STREAM_CHUNK_LEN])
                yield send_event({"type": "delta", "text": chunk})
                await asyncio.sleep(0.02)
            yield send_event({"type": "final", "answer": text})

            # 7) Follow-up systématique
            final_followup = followup_hint or await ensure_followup_suggestion(_client, intent_id, message, text[:200], confidence)
            if final_followup:
                yield send_event({"type": "followup", "answer": final_followup})

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur dans event_source: {e}")
            yield send_event({"type": "error", "message": f"Erreur interne: {str(e)}"})

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
    return JSONResponse({"service": "intelia-llm", "sse": f"{BASE_PATH}/chat/stream"})

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow: /\n"

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {exc}")
    return JSONResponse(status_code=500, content={"detail": f"Erreur interne du serveur: {str(exc)}"})
