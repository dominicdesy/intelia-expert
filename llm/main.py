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
from dataclasses import dataclass

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from langdetect import detect, DetectorFactory

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DetectorFactory.seed = 0  # déterminisme
load_dotenv()

# ===== DÉFINITION UNIQUE DES INTENTIONS MÉTIER =====
INTENT_DEFS = {
    "broiler_weight": {
        # sex est OPTIONNEL partout (jamais requis)
        "required_slots": ["age_days", "line"],
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

# -------- Configuration via variables d'environnement --------
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
ALLOWED_DOMAIN_DESC = os.getenv("ALLOWED_DOMAIN_DESC", "agriculture et sujets adjacents uniquement")
FRONTEND_SSE_COMPAT = os.getenv("FRONTEND_SSE_COMPAT", "1") == "1"

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
if not ASSISTANT_ID:
    raise RuntimeError("ASSISTANT_ID is required")

try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    logger.error(f"Erreur initialisation OpenAI client: {e}")
    raise RuntimeError(f"Impossible d'initialiser le client OpenAI: {e}")

# -------- App & CORS --------
app = FastAPI(title="Intelia LLM Backend", debug=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
router = APIRouter()

def sse_event(obj: Dict[str, Any]) -> bytes:
    """Formate un événement SSE correctement"""
    try:
        data = json.dumps(obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")
    except Exception as e:
        logger.error(f"Erreur formatage SSE: {e}")
        return b"data: {\"type\":\"error\",\"message\":\"Erreur formatage\"}\n\n"

def send_event(obj: Dict[str, Any]) -> bytes:
    """Compatibilité front: transforme clarify/followup en final si besoin"""
    etype = obj.get("type")
    if FRONTEND_SSE_COMPAT and etype in {"clarify", "followup"}:
        text = (obj.get("answer") or obj.get("text") or "").strip()
        prefix = "Question de précision : " if etype == "clarify" else "Suggestion : "
        return sse_event({"type": "final", "answer": f"{prefix}{text}"})
    return sse_event(obj)

def parse_accept_language(header: Optional[str]) -> Optional[str]:
    """Parse l'en-tête Accept-Language pour détecter la langue préférée"""
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
    """Devine la langue à partir du texte"""
    try:
        return detect(text)
    except Exception:
        return None

# -------- Nettoyage des marqueurs de source --------
CITATION_PATTERN = re.compile(r"【[^【】]*】")

def clean_text(txt: str) -> str:
    """Nettoie le texte des marqueurs de citation et espaces excessifs"""
    if not txt:
        return txt
    
    # Supprime les citations
    cleaned = CITATION_PATTERN.sub("", txt)
    
    # Nettoie les espaces
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    
    return cleaned.strip()

# -------- Garde-fou permissif (liste NON-AGRI) --------
NON_AGRI_TERMS = [
    "cinéma", "film", "films", "séries", "serie", "séries tv", "netflix", "hollywood", "bollywood", "disney",
    "pixar", "musique", "concert", "rap", "pop", "rock", "jazz", "opéra", "orchestre", "télévision", "télé",
    "emission", "émission", "talk-show", "talk show", "documentaire", "jeux vidéo", "gaming", "playstation",
    "xbox", "nintendo", "e-sport", "esport", "fortnite", "minecraft", "twitch",
    "football", "soccer", "nba", "nfl", "nhl", "hockey", "baseball", "mlb", "tennis", "golf", "cyclisme",
    "tour de france", "formule 1", "f1", "motogp", "boxe", "ufc", "olympiques", "olympics", "fitness",
    "musculation", "yoga", "randonnée", "plongée", "ski", "surf", "basketball", "rugby", "cricket",
    "élections", "elections", "président", "president", "premier ministre", "parlement", "sénat", "senat",
    "congrès", "congres", "diplomatie", "guerre", "armée", "armee", "conflit", "otan", "onu", "droit humain",
    "droits humains", "immigration", "lois", "justice", "criminel", "tribunal", "révolution", "révolte",
    "bourse", "actions", "nasdaq", "wall street", "s&p500", "dow jones", "crypto", "bitcoin", "ethereum",
    "blockchain", "nft", "banque", "banques", "crédit", "credits", "prêt", "pret", "hypothèque", "hypotheque",
    "assurance", "impôt", "impots", "fiscalité", "fiscalite", "immobilier", "courtage", "trading",
    "hedge fund", "capital risque", "capital-risque", "private equity", "forex", "cryptomonnaie",
    "iphone", "android", "samsung", "apple", "google", "microsoft", "windows", "linux", "amazon", "tesla",
    "réseaux sociaux", "reseaux sociaux", "facebook", "instagram", "tiktok", "youtube", "twitter", "x ",
    "snapchat", "applications mobiles", "app mobile", "messagerie", "whatsapp", "telegram", "signal",
    "streaming", "spotify", "itunes",
    "cancer", "diabète", "diabete", "hypertension", "grippe saisonnière", "grippe saisonniere", "covid",
    "hôpital", "hopital", "clinique", "pharmacie", "chirurgie esthétique", "dentiste", "dentisterie",
    "nutrition humaine", "régime", "regime", "keto", "végan", "vegan", "végétarien", "vegetarien",
    "vêtements", "vetements", "chaussures", "bijoux", "luxe", "gucci", "louis vuitton", "zara", "nike",
    "coiffure", "maquillage", "cosmétiques", "cosmetiques", "parfums", "voyage", "vacances", "tourisme",
    "hôtel", "hotel", "airbnb", "croisière", "croisiere", "disneyland", "gastronomie", "recette",
    "astronomie", "physique quantique", "astrophysique", "fusées", "fusees", "nasa", "spacex", "mathématiques",
    "mathematiques", "philosophie", "histoire", "archéologie", "archeologie", "psychologie", "psychanalyse",
    "sociologie",
    "église", "eglise", "prière", "priere", "islam", "christianisme", "judaïsme", "judaisme", "bouddhisme",
    "astrologie", "horoscope", "tarot", "voyance", "magie", "sorcellerie",
    "météo urbaine", "meteo urbaine", "météo de paris", "meteo de paris", "trafic routier", "bouchons",
    "automobile", "course automobile", "tuning", "uber", "lyft", "relations amoureuses", "sexualité",
    "sexualite", "mariage", "divorce", "fashion week", "influenceur", "influenceuse"
]

NON_AGRI_PAT = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in NON_AGRI_TERMS) + r")\b", re.IGNORECASE)

def guard_debug(reason: str, text: str):
    """Log de debug pour le garde-fou"""
    if DEBUG_GUARD:
        logger.info(f"[GUARD] {reason} :: {text[:160]!r}")

def is_agri_question(text: str) -> bool:
    """Vérifie si la question concerne l'agriculture"""
    if not text:
        return True
    
    blocked = NON_AGRI_PAT.search(text) is not None
    if blocked:
        guard_debug("blocked_non_agri_match", text)
    return not blocked

# -------- Normalisation & alias (tolérance aux fautes) --------
def normalize(s: str) -> str:
    """Normalise une chaîne pour la comparaison"""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower().strip()
    s = "".join(ch for ch in s if ch.isalnum() or ch.isspace())
    s = re.sub(r"\s+", " ", s)
    return s

LINE_ALIASES = {
    "ross 308": ["ross308", "r308", "ross-308", "罗斯308", "羅斯308", "ross 308 ap", "ross 308ap", "ross"],
    "cobb 500": ["cobb500", "c500", "cobb-500", "科宝500", "科寶500", "cobb"],
}

SEX_ALIASES = {
    "male": ["mâle", "masculin", "male", "macho", "公", "雄", "boy", "garçon", "garcon"],
    "female": ["femelle", "feminin", "féminin", "female", "hembra", "母", "雌", "girl", "fille"],
}

def fuzzy_map(value: str, choices: Dict[str, List[str]], cutoff: float = 0.75) -> Optional[str]:
    """Map fuzzy une valeur vers une clé canonique"""
    v = normalize(value)
    pool = []
    for key, alias_list in choices.items():
        pool.append(key)
        pool.extend(alias_list)
    
    best = difflib.get_close_matches(v, pool, n=1, cutoff=cutoff)
    if not best:
        return None
    
    hit = best[0]
    # Map alias back to canonical key
    for key, alias_list in choices.items():
        if hit == key or hit in [normalize(a) for a in alias_list]:
            return key
    return None

# -------- Routage et extraction via GPT --------
def gpt_route_and_extract(client: OpenAI, text: str, lang: str) -> dict:
    """Classification intelligente des questions + extraction slots"""
    system_prompt = f"""Tu es un système de classification pour questions avicoles. Analyse le texte et retourne un JSON strict avec :

{{
  "intent_id": "broiler_weight|water_intake|feed_consumption|temperature_management|disease_prevention|ventilation_optimization|economic_analysis|null",
  "confidence": 0.0-1.0,
  "slots": {{}},
  "need_clarification": true/false
}}

Intentions disponibles :
- broiler_weight : poids, courbe de croissance, objectifs pondéraux
- water_intake : consommation d'eau, abreuvement  
- feed_consumption : consommation aliment, nutrition
- temperature_management : température, chauffage, refroidissement
- disease_prevention : maladies, prévention, vaccination
- ventilation_optimization : ventilation, qualité d'air
- economic_analysis : rentabilité, coûts, analyses économiques

Slots possibles :
- age_days (int) : âge en jours
- line (string) : "ross 308" ou "cobb 500" uniquement
- sex (string) : "male" ou "female" uniquement  
- season, pathogen_type, prevention_method, building_type, bird_count, analysis_type, period

Règles :
- Si line="ross" ou "cobb" sans numéro → slot=null (besoin précision)
- confidence faible si intention peu claire
- Réponds uniquement en JSON valide"""

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
        
        # Extraction du JSON
        if "```json" in raw:
            json_start = raw.find("```json") + 7
            json_end = raw.find("```", json_start)
            raw = raw[json_start:json_end].strip()
        elif "```" in raw:
            json_start = raw.find("```") + 3
            json_end = raw.find("```", json_start)
            raw = raw[json_start:json_end].strip()
        
        data = json.loads(raw)
        
        # Validation et nettoyage
        intent_id = data.get("intent_id")
        if intent_id == "null":
            intent_id = None
        
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        
        slots = data.get("slots", {})
        
        # Nettoyage des slots
        if "line" in slots and slots["line"] in ["ross", "cobb"]:
            slots["line"] = None  # Force clarification
        
        if "age_days" in slots:
            try:
                age = int(slots["age_days"])
                if age < 0 or age > 70:
                    slots["age_days"] = None
                else:
                    slots["age_days"] = age
            except (ValueError, TypeError):
                slots["age_days"] = None
        
        return {
            "intent_id": intent_id,
            "confidence": confidence,
            "slots": slots,
            "need_clarification": bool(data.get("need_clarification", False))
        }
        
    except Exception as e:
        logger.error(f"Erreur routage GPT: {e}")
        return {
            "intent_id": None,
            "confidence": 0.0,
            "slots": {},
            "need_clarification": False
        }

# -------- Décision GPT - SOURCE DE VÉRITÉ --------
async def gpt_decide_answer_or_clarify(client: OpenAI, lang: str, intent_id: str, slots: Dict, user_text: str) -> Dict[str, Any]:
    """Décide s'il faut répondre directement, partiellement ou clarifier - SOURCE DE VÉRITÉ"""
    
    intent_desc = INTENT_DEFS.get(intent_id, {}).get("description", "question avicole")
    required_slots = INTENT_DEFS.get(intent_id, {}).get("required_slots", [])
    optional_slots = INTENT_DEFS.get(intent_id, {}).get("optional_slots", [])
    followup_themes = INTENT_DEFS.get(intent_id, {}).get("followup_themes", [])
    
    system_prompt = f"""Tu es un système de décision pour un assistant avicole expert.

INTENTION: {intent_desc}
SLOTS REQUIS: {', '.join(required_slots)}
SLOTS OPTIONNELS: {', '.join(optional_slots)}
SLOTS DÉTECTÉS: {json.dumps(slots)}

Décide la meilleure stratégie et retourne un JSON strict:
{{
  "answer_mode": "direct|partial|clarify",
  "clarify_question": "question si clarify",
  "missing": ["slots manquants"],
  "followup_suggestion": "suggestion de suivi"
}}

MODES:
- "direct": tous les slots requis présents → réponse complète
- "partial": slots principaux présents → réponse partielle avec suggestion d'affinage
- "clarify": slots critiques manquants → demander précisions avant de répondre

RÈGLES STRICTES:
- Pour broiler_weight: si age_days ET line présents → "direct" ou "partial" (sex optionnel)
- Privilégie TOUJOURS "partial" + followup plutôt que "clarify" excessif
- Question clarify courte et naturelle en {lang}
- Followup basé sur: {', '.join(followup_themes)}

Réponds uniquement en JSON valide."""

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
        
        # Extraction du JSON
        if "```json" in raw:
            json_start = raw.find("```json") + 7
            json_end = raw.find("```", json_start)
            raw = raw[json_start:json_end].strip()
        elif "```" in raw:
            json_start = raw.find("```") + 3
            json_end = raw.find("```", json_start)
            raw = raw[json_start:json_end].strip()
        
        data = json.loads(raw)
        
        answer_mode = data.get("answer_mode", "direct")
        clarify_question = data.get("clarify_question", "")
        missing = data.get("missing", [])
        followup_suggestion = data.get("followup_suggestion", "")
        
        # LOG DÉCISION pour debug
        logger.info(f"[DECISION] intent={intent_id}, mode={answer_mode}, missing={missing}, slots={slots}")
        
        return {
            "answer_mode": answer_mode,
            "clarify_question": clarify_question,
            "missing": missing,
            "followup_suggestion": followup_suggestion
        }
        
    except Exception as e:
        logger.error(f"Erreur décision GPT: {e}")
        # Fallback tolérant - privilégie partial over clarify
        req = set(required_slots)
        missing = [k for k in req if (slots.get(k) in (None, "", []))]
        
        # Logique spéciale pour broiler_weight: si age_days OU line présent → partial
        if intent_id == "broiler_weight" and missing:
            has_age = slots.get("age_days") is not None
            has_line = slots.get("line") is not None
            if has_age or has_line:  # Au moins un slot principal présent
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

# -------- Génération de messages via GPT --------
async def generate_clarification_question(client: OpenAI, intent_id: str, missing_slots: List[str], user_text: str) -> Tuple[str, Dict[str, Any]]:
    """Génère une question de clarification contextualisée via GPT"""
    
    intent_desc = INTENT_DEFS.get(intent_id, {}).get("description", "question avicole")
    required_slots = INTENT_DEFS.get(intent_id, {}).get("required_slots", [])
    
    system_prompt = f"""Tu es un assistant avicole expert. L'utilisateur pose une question sur : {intent_desc}

Pour répondre précisément, tu as besoin de ces informations : {', '.join(required_slots)}
Informations manquantes détectées : {', '.join(missing_slots)}

Génère UNE question courte et naturelle pour demander UNIQUEMENT les informations manquantes.

Règles :
- Réponds dans la MÊME langue que la question de l'utilisateur
- Sois concis et professionnel
- Adapte le ton à la culture locale
- Ne demande que ce qui est nécessaire

Réponds uniquement avec la question de clarification, sans autre texte."""

    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=FALLBACK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.1,
            max_tokens=150
        )
        
        question = (resp.choices[0].message.content or "").strip()
        
        # Suggestions basées sur l'intention
        suggestions = {}
        if "line" in missing_slots:
            suggestions["lines"] = ["Ross 308", "Cobb 500"]
        if "sex" in missing_slots:
            suggestions["sex"] = ["male", "female"]
        if "season" in missing_slots:
            suggestions["season"] = ["summer", "winter", "spring", "autumn"]
        
        return question, suggestions
        
    except Exception as e:
        logger.error(f"Erreur génération question clarification: {e}")
        fallback = "Pour répondre précisément, merci de préciser les informations manquantes."
        return fallback, {}

async def generate_followup_suggestion(client: OpenAI, intent_id: str, user_text: str, response_context: str = "") -> Optional[str]:
    """Génère une suggestion de suivi contextualisée via GPT"""
    
    intent_desc = INTENT_DEFS.get(intent_id, {}).get("description", "question avicole")
    followup_themes = INTENT_DEFS.get(intent_id, {}).get("followup_themes", [])
    
    system_prompt = f"""Tu es un assistant avicole expert. L'utilisateur vient de poser une question sur : {intent_desc}

Thèmes de suivi possibles : {', '.join(followup_themes)}

Génère UNE question de suivi pertinente et utile pour approfondir le sujet.

Règles :
- Réponds dans la MÊME langue que la question initiale
- Propose quelque chose de complémentaire et pratique
- Sois naturel et engageant
- Maximum 1 phrase
- Commence par un mot interrogatif approprié

Réponds uniquement avec la question de suivi, sans autre texte."""

    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=FALLBACK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": response_context[:200] if response_context else user_text}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        followup = (resp.choices[0].message.content or "").strip()
        return followup if followup else None
        
    except Exception as e:
        logger.error(f"Erreur génération followup: {e}")
        return None

async def generate_domain_restriction_message(client: OpenAI, user_text: str) -> str:
    """Génère un message de restriction de domaine adapté à la langue"""
    
    system_prompt = f"""Tu es un assistant spécialisé en agriculture et aviculture. L'utilisateur pose une question hors de ton domaine d'expertise.

Génère un message poli et professionnel pour expliquer que tu ne peux répondre qu'aux questions agricoles.

Règles :
- Réponds dans la MÊME langue que la question de l'utilisateur
- Sois poli et professionnel
- Mentionne ton domaine : agriculture, élevage, aviculture
- Encourage à poser une question dans ton domaine
- Maximum 2 phrases

Réponds uniquement avec le message de restriction, sans autre texte."""

    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=FALLBACK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.1,
            max_tokens=100
        )
        
        message = (resp.choices[0].message.content or "").strip()
        return message if message else f"Domaine restreint : {ALLOWED_DOMAIN_DESC}."
        
    except Exception as e:
        logger.error(f"Erreur génération message restriction: {e}")
        return f"Domaine restreint : {ALLOWED_DOMAIN_DESC}."

# -------- Assistant data-only avec tri garanti --------
def run_data_only_assistant(client: OpenAI, assistant_id: str, user_text: str, lang: str) -> str:
    """Exécute l'assistant avec les données du Vector Store uniquement - tri garanti"""
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
            thread_id=thread.id,
            role="user",
            content=f"{user_text}\n\n{reminder}",
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        
        # Polling avec timeout
        timeout = time.time() + 30
        while time.time() < timeout:
            r = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if r.status in ("completed", "failed", "cancelled", "expired"):
                break
            time.sleep(POLL_INTERVAL_SEC)
        
        if r.status != "completed":
            logger.error(f"Assistant run failed with status: {r.status}")
            return "Hors base: information absente de la connaissance Intelia."
        
        # TRI GARANTI : récupération du dernier message assistant par created_at
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

# -------- Fallback général - signature unifiée --------
async def stream_fallback_general(client: OpenAI, text: str):
    """Fallback streaming avec GPT pour les questions hors base - signature unifiée"""
    system = f"""Tu es un assistant spécialisé en agriculture et aviculture. Tu réponds UNIQUEMENT aux questions dans ce domaine :
- Élevage (volailles, bovins, porcins, etc.)
- Aviculture (poulets de chair, pondeuses, etc.)
- Nutrition animale
- Environnement d'élevage
- Biosécurité
- Ventilation
- Maladies animales
- Économie agricole directement liée aux exploitations

Si la question sort clairement de ce cadre, refuse poliment.

Réponds dans la MÊME langue que la question de l'utilisateur. Sois naturel et adapte ton ton à la culture locale."""
    
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
                    chunk = delta.content
                    cleaned_chunk = clean_text(chunk)
                    final_buf.append(cleaned_chunk)
                    yield send_event({"type": "delta", "text": cleaned_chunk})
                    
        final_text = clean_text("".join(final_buf).strip())
        yield send_event({"type": "final", "answer": final_text})
        
    except Exception as e:
        logger.error(f"Erreur fallback streaming: {e}")
        error_msg = f"Erreur technique: {str(e)}"
        yield send_event({"type": "error", "message": error_msg})

# -------- Fonctions helper pour follow-up systématique --------
def get_default_followup_by_intent(intent_id: str) -> Optional[str]:
    """Retourne un follow-up par défaut selon l'intention"""
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
    """
    Assure qu'un follow-up soit généré.
    1) On tente une génération contextuelle via GPT
    2) Si rien n'est proposé, on retombe SYSTÉMATIQUEMENT sur le mapping par intention
    """
    if intent_id not in INTENT_DEFS:
        return None
        
    followup = await generate_followup_suggestion(client, intent_id, user_text, response_context)
    if followup:
        return followup

    # Fallback par intention (sans seuil de confiance)
    return get_default_followup_by_intent(intent_id)

@router.get("/health")
def health():
    """Point de santé de l'API"""
    return {
        "ok": True,
        "assistant_id": ASSISTANT_ID,
        "guard_mode": "permissive_non_agri",
        "debug_guard": DEBUG_GUARD,
        "hybrid_mode": HYBRID_MODE,
        "frontend_sse_compat": FRONTEND_SSE_COMPAT
    }

@router.post("/chat/stream")
async def chat_stream(request: Request):
    """
    Endpoint principal pour le chat streaming
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

    # Détection de langue
    accept_lang = request.headers.get("accept-language")
    lang = parse_accept_language(accept_lang) or guess_lang_from_text(message) or "fr"
    lang = (lang or "fr")[:5].split("-")[0].lower()

    async def event_source() -> AsyncGenerator[str, None]:
        try:
            # 1) Garde-fou permissif
            if not is_agri_question(message):
                _client = OpenAI(api_key=OPENAI_API_KEY)
                answer = await generate_domain_restriction_message(_client, message)
                answer = clean_text(answer)
                yield send_event({"type": "final", "answer": answer})
                return

            _client = OpenAI(api_key=OPENAI_API_KEY)

            # 2) ROUTAGE GPT : intention & slots
            route = await asyncio.to_thread(gpt_route_and_extract, _client, message, lang)
            intent_id = route.get("intent_id")
            confidence = float(route.get("confidence") or 0.0)
            slots = route.get("slots") or {}
            
            logger.info(f"[ROUTE] intent={intent_id}, confidence={confidence:.2f}, slots={slots}")

            # 3) DÉCISION GPT - SOURCE DE VÉRITÉ UNIQUE
            followup_hint = None
            
            if intent_id in INTENT_DEFS:
                decision = await gpt_decide_answer_or_clarify(_client, lang, intent_id, slots, message)
                answer_mode = decision.get("answer_mode", "direct")
                followup_hint = decision.get("followup_suggestion") or followup_hint

                # SEULE condition pour clarify : decision GPT == "clarify"
                if answer_mode == "clarify":
                    clarify_q = clean_text(decision.get("clarify_question") or "")
                    if not clarify_q:  # Fallback si GPT n'a pas généré de question
                        missing = decision.get("missing", [])
                        clarify_q, suggestions = await generate_clarification_question(_client, intent_id, missing, message)
                    else:
                        # Générer suggestions basées sur les slots manquants
                        missing = decision.get("missing", [])
                        suggestions = {}
                        if "line" in missing:
                            suggestions["lines"] = ["Ross 308", "Cobb 500"]
                        if "sex" in missing:
                            suggestions["sex"] = ["male", "female"]
                        if "season" in missing:
                            suggestions["season"] = ["summer", "winter", "spring", "autumn"]
                    
                    clarify_q = clean_text(clarify_q)
                    payload_clarify = {"type": "clarify", "answer": clarify_q}
                    if suggestions:
                        payload_clarify["suggestions"] = suggestions
                    yield send_event(payload_clarify)
                    return

            # 4) Essai data-only (Assistant v2)
            text = await asyncio.to_thread(run_data_only_assistant, _client, ASSISTANT_ID, message, lang)
            text = clean_text(text)

            # 5) Fallback GPT si hors base
            if text.lower().startswith("hors base"):
                if HYBRID_MODE and allow_fallback:
                    async for sse in stream_fallback_general(_client, message):
                        yield sse
                    
                    # Follow-up après fallback
                    final_followup = followup_hint or await ensure_followup_suggestion(_client, intent_id, message, "", confidence)
                    if final_followup:
                        yield send_event({"type": "followup", "answer": final_followup})
                    return
                else:
                    yield send_event({"type": "final", "answer": text})
                    return

            # 6) Réponse data-only stream simulé
            for i in range(0, len(text), STREAM_CHUNK_LEN):
                chunk = clean_text(text[i:i + STREAM_CHUNK_LEN])
                yield send_event({"type": "delta", "text": chunk})
                await asyncio.sleep(0.02)
                
            yield send_event({"type": "final", "answer": text})
            
            # 7) FOLLOW-UP SYSTÉMATIQUE POST-RÉPONSE
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

# Monte les routes
app.include_router(router, prefix=BASE_PATH)

@app.get("/")
def root():
    """Point d'entrée racine"""
    return JSONResponse({"service": "intelia-llm", "sse": f"{BASE_PATH}/chat/stream"})

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    """Fichier robots.txt"""
    return "User-agent: *\nDisallow: /\n"

# Gestion globale des erreurs
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erreur interne du serveur: {str(exc)}"}
    )
