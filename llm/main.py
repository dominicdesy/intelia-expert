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

# ===== INTENTIONS MÉTIER (agri/aviculture) =====
INTENT_DEFS = {
    "broiler_weight": {
        "required_slots": ["age_days", "line", "sex"],
        "followup_themes": ["water_consumption", "feed_intake", "housing_conditions"],
        "description": "Questions sur le poids et croissance des poulets de chair"
    },
    "water_intake": {
        "required_slots": ["age_days", "line"],
        "followup_themes": ["water_temperature", "drinking_equipment", "water_quality"],
        "description": "Questions sur la consommation d'eau des volailles"
    },
    "feed_consumption": {
        "required_slots": ["age_days", "line"],
        "followup_themes": ["nutritional_composition", "feeding_schedules", "feed_conversion"],
        "description": "Questions sur l'alimentation et consommation d'aliment"
    },
    "temperature_management": {
        "required_slots": ["age_days", "season"],
        "followup_themes": ["ventilation", "humidity_control", "heating_systems"],
        "description": "Questions sur la gestion thermique des bâtiments"
    },
    "disease_prevention": {
        "required_slots": ["pathogen_type", "prevention_method"],
        "followup_themes": ["vaccination_programs", "biosecurity", "treatment_protocols"],
        "description": "Questions sur la prévention et traitement des maladies"
    },
    "ventilation_optimization": {
        "required_slots": ["building_type", "bird_count"],
        "followup_themes": ["air_quality_sensors", "automation", "energy_efficiency"],
        "description": "Questions sur la ventilation et qualité de l'air"
    },
    "economic_analysis": {
        "required_slots": ["analysis_type", "period"],
        "followup_themes": ["comparative_analysis", "cost_optimization", "profitability"],
        "description": "Questions sur l'analyse économique et rentabilité"
    }
}

# -------- Config via variables d'environnement --------
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

# Compatibilité front: transforme clarify/followup en final si besoin
def send_event(obj: Dict[str, Any]) -> bytes:
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

# -------- Normalisation & alias (pour tolérance aux fautes) --------
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
    # Ross
    "ross 308": ["ross308", "r308", "ross-308", "罗斯308", "羅斯308", "ross 308 ap", "ross 308ap", "ross"],
    # Cobb
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

# -------- Génération de messages via GPT (remplace hardcodage) --------
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

RÉponds uniquement avec la question de clarification, sans autre texte."""

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
        # Fallback générique
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

# -------- Nouvelle fonction de routage GPT --------
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
- need_clarification=true si slots requis manquants
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
        
        # Extraction du JSON (parfois entouré de ```json```)
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

# -------- Intent & Slots (multilingue, tolérant) - LEGACY --------
BROILER_WEIGHT_INTENT_PAT = re.compile(
    r"(?:(poids|weight|peso|体重|體重|標準體重|标准体重|目標體重|目标体重|objectif|target|增重|增重曲線|增重曲线))"
    r".*?(poulet|broiler|ross|cobb|鸡|雞|小鸡|雞雞)?|"
    r"\b(ross|cobb)\b.*?(poids|weight|体重|體重|標準體重|标准体重|objectif|target)",
    re.IGNORECASE
)

# Age (jours) : fr/en/es/zh
AGE_DAYS_PAT = re.compile(
    r"\b(\d{1,2})\s*(j|jour|jours|d|día|dias|días|days)\b|(\d{1,2})\s*天",
    re.IGNORECASE
)

LINE_PAT = re.compile(r"\b(ross|cobb|aviagen|hy-?line)\b", re.IGNORECASE)
MALE_PAT = re.compile(r"\b(mâle|male|masculin|macho|公|雄)\b", re.IGNORECASE)
FEMALE_PAT = re.compile(r"\b(femelle|female|féminin|feminin|hembra|母|雌)\b", re.IGNORECASE)

@dataclass
class BroilerWeightSlots:
    age_days: Optional[int]
    line: Optional[str]      # canonical 'ross 308' / 'cobb 500'
    sex: Optional[str]       # 'male' | 'female'

def detect_broiler_weight_intent(text: str) -> bool:
    """Détecte si la question concerne le poids des broilers"""
    return bool(BROILER_WEIGHT_INTENT_PAT.search(text))

def extract_broiler_weight_slots(text: str) -> BroilerWeightSlots:
    """Extrait les informations de la question sur le poids des broilers"""
    tnorm = normalize(text)

    # Age
    age = None
    m_age = AGE_DAYS_PAT.search(text)
    if m_age:
        age_str = m_age.group(1) or m_age.group(3)
        if age_str:
            try:
                age = int(age_str)
                if age < 0 or age > 70:  # Validation
                    age = None
            except ValueError:
                age = None

    # Line (regex coarse)
    line = None
    m_line = LINE_PAT.search(text)
    if m_line:
        rough = m_line.group(1).lower()
        # Fuzzy enrich (could be 'ross' only → leave as None to clarify)
        line = fuzzy_map(rough, LINE_ALIASES, cutoff=0.6) or (rough if rough in ["ross", "cobb"] else None)

    # Sex
    sex = None
    if MALE_PAT.search(text):
        sex = "male"
    elif FEMALE_PAT.search(text):
        sex = "female"
    else:
        # Fuzzy from whole text (handles typos)
        for k, arr in SEX_ALIASES.items():
            for a in arr:
                if normalize(a) in tnorm:
                    sex = k
                    break
            if sex:
                break

    # Fuzzy correction if user typed model directly like "ross308"
    if not line:
        tokens = tnorm.split()
        for token in tokens:
            hit = fuzzy_map(token, LINE_ALIASES, cutoff=0.8)
            if hit:
                line = hit
                break

    return BroilerWeightSlots(age_days=age, line=line, sex=sex)

# GPT extractor JSON (fallback si extraction regex/fuzzy est pauvre)
def gpt_extract_slots(client: OpenAI, text: str, lang: str) -> BroilerWeightSlots:
    """Extraction des slots via GPT en cas d'échec des regex"""
    system = (
        "Extract broiler target-weight query entities as strict JSON with keys: "
        "age_days (int|null), line (one of ['ross 308','cobb 500', null]), sex (one of ['male','female', null]). "
        "Infer from multilingual text (fr/en/es/zh). If only 'ross' or 'cobb' given, set line=null (needs subline). "
        "Return ONLY JSON."
    )
    
    try:
        resp = client.chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
            temperature=0.0,
            max_tokens=100
        )
        raw = resp.choices[0].message.content.strip()
        
        data = json.loads(raw)
        age = data.get("age_days")
        line = data.get("line")
        sex = data.get("sex")
        
        # Normalize line through aliases if needed
        if isinstance(line, str):
            line = fuzzy_map(line, LINE_ALIASES, cutoff=0.6) or line
        if line and line in ["ross", "cobb"]:
            line = None  # force clarification for subline specificity
            
        if isinstance(sex, str):
            sex = "male" if "male" in sex.lower() else ("female" if "female" in sex.lower() else None)
            
        if isinstance(age, str) and age.isdigit():
            age = int(age)
        if isinstance(age, int) and (age < 0 or age > 70):
            age = None
            
        return BroilerWeightSlots(age_days=age, line=line, sex=sex)
        
    except Exception as e:
        logger.error(f"Erreur GPT extraction slots: {e}")
        return BroilerWeightSlots(age_days=None, line=None, sex=None)

# --- Assistant data-only (Assistant v2) ---
def run_data_only_assistant(client: OpenAI, assistant_id: str, user_text: str, lang: str) -> str:
    """Exécute l'assistant avec les données du Vector Store uniquement"""
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
        timeout = time.time() + 30  # 30 secondes timeout
        while time.time() < timeout:
            r = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if r.status in ("completed", "failed", "cancelled", "expired"):
                break
            time.sleep(POLL_INTERVAL_SEC)
        
        if r.status != "completed":
            logger.error(f"Assistant run failed with status: {r.status}")
            return "Hors base: information absente de la connaissance Intelia."
        
        msgs = client.beta.threads.messages.list(thread_id=thread.id)
        for m in msgs.data:
            if m.role == "assistant":
                for c in m.content:
                    if getattr(c, "type", "") == "text":
                        txt = (c.text.value or "").strip()
                        txt = clean_text(txt)
                        return txt if txt else "Hors base: information absente de la connaissance Intelia."
                        
        return "Hors base: information absente de la connaissance Intelia."
        
    except Exception as e:
        logger.error(f"Erreur assistant data-only: {e}")
        return "Hors base: information absente de la connaissance Intelia."

# --- Fallback général (GPT) ---
async def stream_fallback_general(client: OpenAI, text: str, user_text: str):
    """Fallback streaming avec GPT pour les questions hors base"""
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

            # === ROUTAGE GPT : intention & slots ===
            route = await asyncio.to_thread(gpt_route_and_extract, _client, message, lang)
            intent_id = route.get("intent_id")
            confidence = float(route.get("confidence") or 0.0)
            slots = route.get("slots") or {}
            need_clar = bool(route.get("need_clarification"))

            # Si l'intention est reconnue et nécessite des précisions → on clarifie avant de répondre
            if intent_id in INTENT_DEFS and (need_clar or confidence < 0.55):
                # ne demander QUE ce qui est requis pour cette intention
                req = set(INTENT_DEFS[intent_id]["required_slots"])
                missing = [k for k in req if (slots.get(k) in (None, "", []))]
                if missing:
                    clarify_q, suggestions = await generate_clarification_question(_client, intent_id, missing, message)
                    clarify_q = clean_text(clarify_q)
                    payload = {"type": "clarify", "answer": clarify_q}
                    if suggestions: 
                        payload["suggestions"] = suggestions
                    yield send_event(payload)
                    return

            # 2) CONTEXTUALISATION LEGACY — Intent poids broiler (pour compatibilité)
            if detect_broiler_weight_intent(message) and not intent_id:
                slots_legacy = extract_broiler_weight_slots(message)

                # Si extraction regex/fuzzy trop pauvre, tenter extraction GPT JSON
                if slots_legacy.age_days is None or slots_legacy.line is None or slots_legacy.sex is None:
                    gslots = await asyncio.to_thread(gpt_extract_slots, _client, message, lang)
                    # Merge préférant infos "certaines"
                    slots_legacy = BroilerWeightSlots(
                        age_days=slots_legacy.age_days or gslots.age_days,
                        line=slots_legacy.line or gslots.line,
                        sex=slots_legacy.sex or gslots.sex
                    )

                # Hook : si line vaut 'ross' ou 'cobb' (trop vague), forcer clarification
                if slots_legacy.line in ("ross", "cobb"):
                    slots_legacy = BroilerWeightSlots(age_days=slots_legacy.age_days, line=None, sex=slots_legacy.sex)

                # Si slots manquants → question ciblée + suggestions
                if (slots_legacy.line is None) or (slots_legacy.sex is None) or (slots_legacy.age_days is None):
                    missing_legacy = []
                    if slots_legacy.line is None:
                        missing_legacy.append("line")
                    if slots_legacy.sex is None:
                        missing_legacy.append("sex")
                    if slots_legacy.age_days is None:
                        missing_legacy.append("age_days")
                    
                    clarify, suggestions_legacy = await generate_clarification_question(_client, "broiler_weight", missing_legacy, message)
                    clarify = clean_text(clarify)
                    yield send_event({"type": "clarify", "answer": clarify, "suggestions": suggestions_legacy})
                    return

            # 3) Essai data-only (Assistant v2)
            text = await asyncio.to_thread(run_data_only_assistant, _client, ASSISTANT_ID, message, lang)
            text = clean_text(text)

            # 4) Fallback GPT si hors base
            if text.lower().startswith("hors base"):
                if HYBRID_MODE and allow_fallback:
                    async for sse in stream_fallback_general(_client, message, message):
                        yield sse
                    # --- Smart Follow-up contextuel ---
                    if followup_hint:
                        yield send_event({"type":"followup","answer": followup_hint})
                    elif intent_id in INTENT_DEFS and confidence >= 0.55:
                        fup = await generate_followup_suggestion(_client, intent_id, message, "")
                        if fup:
                            yield send_event({"type": "followup", "answer": fup})
                    return
                else:
                    yield send_event({"type": "final", "answer": text})
                    return

            # 5) Sinon, réponse data-only stream simulé
            for i in range(0, len(text), STREAM_CHUNK_LEN):
                chunk = clean_text(text[i:i + STREAM_CHUNK_LEN])
                yield send_event({"type": "delta", "text": chunk})
                await asyncio.sleep(0.02)
                
            yield send_event({"type": "final", "answer": text})
            
            # --- Smart Follow-up contextuel ---
            if followup_hint:
                yield send_event({"type":"followup","answer": followup_hint})
            elif intent_id in INTENT_DEFS and confidence >= 0.55:
                fup = await generate_followup_suggestion(_client, intent_id, message, text[:200])
                if fup:
                    yield send_event({"type": "followup", "answer": fup})

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