# -*- coding: utf-8 -*-
#
# main.py — Intelia LLM backend (FastAPI + SSE + RAG)
# Python 3.11+
#

import os
import re
import json
import asyncio
import time
import logging
import uuid
import urllib.parse
from typing import Any, Dict, AsyncGenerator, Optional

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from langdetect import detect, DetectorFactory

# Import du module RAG
from rag_engine import create_rag_engine, process_question_with_rag, RAGSource, RAGResult

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DetectorFactory.seed = 0
load_dotenv()

# Variable globale pour l'instance RAG
rag_engine = None

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
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-4o-2024-11-20")  # ou "o1-preview" selon disponibilité
FALLBACK_TEMPERATURE = float(os.getenv("FALLBACK_TEMPERATURE", "0.7"))
FALLBACK_MAX_COMPLETION_TOKENS = int(
    os.getenv("FALLBACK_MAX_COMPLETION_TOKENS", os.getenv("FALLBACK_MAX_TOKENS", "600"))
)

# Configuration RAG
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.7"))

LANGUAGE_FILE = os.getenv("LANGUAGE_FILE", os.path.join(BASE_DIR, "languages.json"))
BLOCKED_TERMS_FILE = os.getenv("BLOCKED_TERMS_FILE", os.path.join(BASE_DIR, "blocked_terms.json"))
INTENTS_FILE = os.getenv("INTENTS_FILE", os.path.join(BASE_DIR, "intents.json"))

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
if not ASSISTANT_ID:
    raise RuntimeError("ASSISTANT_ID is required")

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

# Charger les termes bloqués depuis le fichier JSON
def _load_blocked_terms(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Fusionner toutes les catégories en une seule liste
        all_terms = []
        for category, terms in data.items():
            if isinstance(terms, list):
                all_terms.extend(terms)
        return all_terms
    except Exception as e:
        logger.error(f"Unable to load blocked terms from {path}: {e}")
        # Fallback minimal
        return ["crypto", "cryptocurrency", "bitcoin", "ethereum", "blockchain"]

BLOCKED_TERMS = _load_blocked_terms(BLOCKED_TERMS_FILE)

# Charger la configuration des intentions pour les relances contextuelles
def _load_intents_config(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Unable to load intents config from {path}: {e}")
        return {}

INTENTS_CONFIG = _load_intents_config(INTENTS_FILE)

# Templates de relances par métrique spécifique
METRIC_FOLLOWUP_TEMPLATES = {
    "body_weight_target": "Souhaitez-vous que je vérifie si vos résultats actuels sont dans la norme, ou analyser les causes d'un éventuel écart (nutrition, climat, densité) ?",
    "fcr_target": "Souhaitez-vous comparer ce FCR avec vos performances actuelles ou identifier les leviers d'optimisation ?",
    "water_intake_daily": "Voulez-vous que j'analyse la cohérence avec votre consommation d'aliment ou les facteurs climatiques ?",
    "feed_intake_daily": "Voulez-vous comparer cette consommation avec vos objectifs de croissance ou optimiser votre formulation ?",
    "ambient_temp_target": "Voulez-vous que je calcule la courbe de température optimale pour votre bâtiment ?",
    "feed_cost_per_bird": "Souhaitez-vous que j'analyse les leviers de réduction de ce coût ou compare avec vos marges ?",
}

logger.info(f"LANGUAGE_FILE={LANGUAGE_FILE} exists={os.path.exists(LANGUAGE_FILE)}")
logger.info(f"BLOCKED_TERMS_FILE={BLOCKED_TERMS_FILE} exists={os.path.exists(BLOCKED_TERMS_FILE)}")
logger.info(f"INTENTS_FILE={INTENTS_FILE} exists={os.path.exists(INTENTS_FILE)}")
logger.info(f"FALLBACK_MODEL={FALLBACK_MODEL}")
logger.info(f"RAG_CONFIDENCE_THRESHOLD={RAG_CONFIDENCE_THRESHOLD}")
logger.info(f"Loaded {len(BLOCKED_TERMS)} blocked terms")
logger.info(f"Loaded {len(METRIC_FOLLOWUP_TEMPLATES)} metric followup templates")
logger.info(f"Intents config loaded: {bool(INTENTS_CONFIG)}")

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
    test_models = client.models.list()
    logger.info(f"OpenAI client initialized successfully. Available models: {len(test_models.data)}")
except Exception as e:
    logger.error(f"Erreur initialisation OpenAI client: {e}")
    raise RuntimeError(f"Impossible d'initialiser le client OpenAI: {e}")

# -----------------------------------------------------------------------------
# Initialisation RAG
# -----------------------------------------------------------------------------
async def initialize_rag_engine():
    """Initialise le moteur RAG au démarrage"""
    global rag_engine
    if rag_engine is not None:
        return rag_engine
    
    try:
        logger.info("Initialisation du moteur RAG...")
        rag_engine = await create_rag_engine(client)
        rag_status = rag_engine.get_status()
        logger.info(f"Moteur RAG initialisé: {rag_status}")
        return rag_engine
    except Exception as e:
        logger.error(f"Erreur initialisation RAG: {e}")
        return None

# Initialiser RAG au démarrage
async def startup_event():
    """Événement de démarrage pour initialiser les services"""
    await initialize_rag_engine()

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

# Ajouter l'événement de démarrage à FastAPI
@app.on_event("startup")
async def startup():
    await startup_event()

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
    if "type" not in obj:
        obj = {"type": "final", "answer": "Désolé, une erreur de format interne est survenue."}
    if obj.get("type") == "final" and not obj.get("answer"):
        obj["answer"] = "Désolé, aucune réponse n'a pu être générée."
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
        detected = detect(text)
        # Normaliser les codes de langue
        if detected in ['de', 'ger']:
            return 'de'
        elif detected in ['fr', 'fra']:
            return 'fr'
        elif detected in ['en', 'eng']:
            return 'en'
        elif detected in ['es', 'spa']:
            return 'es'
        else:
            return detected
    except Exception:
        # Fallback basique si langdetect échoue
        text_lower = text.lower()
        if any(word in text_lower for word in ['was', 'ist', 'wie', 'wo', 'wann', 'warum', 'kryptowährung', 'deutschland']):
            return 'de'
        elif any(word in text_lower for word in ['what', 'is', 'how', 'where', 'when', 'why', 'cryptocurrency']):
            return 'en'
        elif any(word in text_lower for word in ['qué', 'es', 'cómo', 'dónde', 'cuándo', 'por qué']):
            return 'es'
        elif any(word in text_lower for word in ['qu\'est', 'comment', 'où', 'quand', 'pourquoi', 'cryptomonnaie']):
            return 'fr'
        return None

# -----------------------------------------------------------------------------
# Text helpers
# -----------------------------------------------------------------------------
CITATION_PATTERN = re.compile(r"【[^【】']*】")

def clean_text(txt: str) -> str:
    if not txt:
        return txt
    cleaned = CITATION_PATTERN.sub("", txt)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

# -----------------------------------------------------------------------------
# Streaming intelligent
# -----------------------------------------------------------------------------
def smart_chunk_text(text: str, max_chunk_size: int = 400) -> list:
    """
    Découpe le texte en chunks sans casser les mots.
    Respecte aussi les retours à la ligne et la ponctuation.
    """
    if not text or len(text) <= max_chunk_size:
        return [text] if text else []
    
    chunks = []
    remaining_text = text
    
    while remaining_text:
        if len(remaining_text) <= max_chunk_size:
            chunks.append(remaining_text)
            break
        
        # Trouver le point de coupe optimal
        cut_point = max_chunk_size
        
        # Chercher le dernier espace avant max_chunk_size
        while cut_point > 0 and remaining_text[cut_point] != ' ':
            cut_point -= 1
        
        # Si aucun espace trouvé, chercher la prochaine ponctuation
        if cut_point == 0:
            cut_point = max_chunk_size
            while cut_point < len(remaining_text) and remaining_text[cut_point] not in ' .,;:!?\n':
                cut_point += 1
        
        # Si toujours rien, couper au maximum (cas extrême : mot très long)
        if cut_point == 0 or cut_point > len(remaining_text):
            cut_point = min(max_chunk_size, len(remaining_text))
        
        # Extraire le chunk
        chunk = remaining_text[:cut_point].rstrip()
        if chunk:
            chunks.append(chunk)
        
        # Préparer le texte restant (supprimer les espaces de début)
        remaining_text = remaining_text[cut_point:].lstrip()
    
    return [chunk for chunk in chunks if chunk.strip()]

def smart_chunk_with_natural_breaks(text: str, max_chunk_size: int = 400) -> list:
    """
    Version avancée qui respecte les paragraphes et listes.
    Idéal pour le contenu markdown de l'assistant.
    """
    if not text or len(text) <= max_chunk_size:
        return [text] if text else []
    
    chunks = []
    
    # Séparer par paragraphes d'abord
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        
        # Si le paragraphe entier tient dans le chunk actuel
        if len(current_chunk + paragraph) <= max_chunk_size:
            if current_chunk:
                current_chunk += '\n\n' + paragraph
            else:
                current_chunk = paragraph
        else:
            # Envoyer le chunk actuel s'il existe
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # Si le paragraphe est trop long, le découper
            if len(paragraph) > max_chunk_size:
                sub_chunks = smart_chunk_text(paragraph, max_chunk_size)
                chunks.extend(sub_chunks)
            else:
                current_chunk = paragraph
    
    # Ajouter le dernier chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return [chunk for chunk in chunks if chunk.strip()]

# -----------------------------------------------------------------------------
# Proactive Followup System - VERSION CORRIGÉE
# -----------------------------------------------------------------------------

def extract_intent_from_question(question: str) -> dict:
    """Extraction basique d'intent à partir de la question pour les relances"""
    question_lower = question.lower()
    
    detected_metric = None
    detected_line = None
    has_specific_context = False
    
    # Détection de métriques (plus permissive)
    if any(word in question_lower for word in ['poids', 'weight', 'gramme', 'kg', 'g']):
        detected_metric = "body_weight_target"
        has_specific_context = True
    elif any(word in question_lower for word in ['fcr', 'conversion', 'indice']):
        detected_metric = "fcr_target"
        has_specific_context = True
    elif any(word in question_lower for word in ['eau', 'water', 'abreuv']):
        detected_metric = "water_intake_daily"
        has_specific_context = True
    elif any(word in question_lower for word in ['aliment', 'feed', 'consommation']):
        detected_metric = "feed_intake_daily"
        has_specific_context = True
    elif any(word in question_lower for word in ['température', 'temperature', 'temp', 'climat']):
        detected_metric = "ambient_temp_target"
        has_specific_context = True
    elif any(word in question_lower for word in ['coût', 'cost', 'prix', 'économ']):
        detected_metric = "feed_cost_per_bird"
        has_specific_context = True
    
    # Détection de lignées (élargie)
    line_patterns = {
        'ross': ['ross', 'ross 308', 'ross308'],
        'cobb': ['cobb', 'cobb 500', 'cobb500'],
        'hubbard': ['hubbard'],
        'arbor': ['arbor'],
        'isa': ['isa', 'isa brown'],
        'lohmann': ['lohmann'],
        'novogen': ['novogen']
    }
    
    for canonical_line, patterns in line_patterns.items():
        for pattern in patterns:
            if pattern in question_lower:
                detected_line = canonical_line
                has_specific_context = True
                break
        if detected_line:
            break
    
    # Détection d'âge (nouveau)
    age_detected = bool(re.search(r'\b\d+\s*(jour|day|semaine|week|j|sem)\b', question_lower))
    if age_detected:
        has_specific_context = True
    
    # Détection de nombres spécifiques (nouveau)
    numbers_detected = bool(re.search(r'\b\d+\b', question_lower))
    if numbers_detected:
        has_specific_context = True
    
    return {
        "metric": detected_metric,
        "line": detected_line,
        "has_age": age_detected,
        "has_numbers": numbers_detected,
        "has_specific_context": has_specific_context
    }

def should_generate_proactive_followup(question: str, answer: str, intent_data: dict) -> bool:
    """Détermine si une relance proactive doit être générée - VERSION PLUS PERMISSIVE"""
    
    # Conditions d'exclusion (plus restrictives)
    if len(answer) < 30:  # Réponse trop courte
        return False
    if any(word in answer.lower() for word in ['désolé', 'ne sais pas', 'erreur', 'impossible']):
        return False
    if any(word in question.lower() for word in ['pourquoi', 'comment', 'expliquer']):  # Questions déjà détaillées
        return False
    
    # Conditions d'inclusion (plus permissives)
    if intent_data.get("has_specific_context", False):
        return True
    if intent_data.get("metric") is not None:
        return True
    if intent_data.get("line") is not None:
        return True
    if intent_data.get("has_age", False):
        return True
    
    # Fallback: questions techniques probables
    technical_indicators = ['poids', 'consommation', 'température', 'mortalité', 'production']
    if any(indicator in question.lower() for indicator in technical_indicators):
        return True
    
    return False

def generate_proactive_followup(question: str, answer: str, lang: str = "fr") -> Optional[str]:
    """Génère une relance proactive contextuelle - VERSION AMÉLIORÉE"""
    try:
        intent_data = extract_intent_from_question(question)
        
        if not should_generate_proactive_followup(question, answer, intent_data):
            return None
        
        # Template par métrique détectée
        detected_metric = intent_data.get("metric")
        if detected_metric and detected_metric in METRIC_FOLLOWUP_TEMPLATES:
            return METRIC_FOLLOWUP_TEMPLATES[detected_metric]
        
        # Templates génériques par contexte
        if intent_data.get("line"):
            return "Voulez-vous que je compare ces données avec d'autres lignées ou que j'analyse l'évolution dans le temps ?"
        
        if intent_data.get("has_age"):
            return "Souhaitez-vous connaître l'évolution de cette métrique sur d'autres âges, ou les objectifs cibles pour cette période ?"
        
        # Template générique pour questions techniques
        return "Avez-vous besoin d'informations complémentaires sur ce sujet, ou souhaitez-vous analyser d'autres paramètres liés ?"
        
    except Exception as e:
        logger.error(f"Erreur génération relance proactive: {e}")
        return None

# -----------------------------------------------------------------------------
# Conversation Memory
# -----------------------------------------------------------------------------
conversation_memory = {}
MAX_MEMORY_ITEMS = 3

def needs_context(question: str) -> bool:
    ambiguous_terms = ["cette maladie", "ce traitement", "cette méthode", "il", "elle", "ça"]
    return any(term in question.lower() for term in ambiguous_terms)

def add_to_conversation_memory(tenant_id: str, question: str, answer: str):
    if tenant_id not in conversation_memory:
        conversation_memory[tenant_id] = []
    conversation_memory[tenant_id].append({"question": question, "answer": answer, "timestamp": time.time()})
    if len(conversation_memory[tenant_id]) > MAX_MEMORY_ITEMS:
        conversation_memory[tenant_id] = conversation_memory[tenant_id][-MAX_MEMORY_ITEMS:]

def build_context_prompt(tenant_id: str, current_question: str) -> str:
    if not needs_context(current_question):
        return current_question
    history = conversation_memory.get(tenant_id, [])
    if not history:
        return current_question
    context_parts = ["CONTEXTE:"]
    for item in history[-2:]:
        context_parts.append(f"Q: {item['question']}")
        context_parts.append(f"R: {item['answer'][:150]}...")
    context_parts.append(f"QUESTION ACTUELLE: {current_question}")
    return "\n".join(context_parts)

# -----------------------------------------------------------------------------
# Domain guard (permissif: bloque évidents hors-agri)
# -----------------------------------------------------------------------------
def create_blocked_pattern(terms_list: list) -> re.Pattern:
    """Crée le pattern regex à partir de la liste de termes bloqués"""
    return re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms_list) + r")\b", re.IGNORECASE)

# Pattern créé dynamiquement à partir du fichier JSON
NON_AGRI_PAT = create_blocked_pattern(BLOCKED_TERMS)

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
# Chat Completions helpers
# -----------------------------------------------------------------------------
def _chat_args(messages, max_completion_tokens, stream=False, temperature=None):
    args = dict(messages=messages, max_completion_tokens=max_completion_tokens, stream=stream)
    force_temp = os.getenv("FORCE_TEMPERATURE_PARAM", "0") == "1"
    if force_temp and temperature is not None:
        args["temperature"] = float(temperature)
    return args

def create_chat_completion_safe(client, model, messages, max_completion_tokens, stream=False, temperature=None):
    try:
        kwargs = _chat_args(messages, max_completion_tokens, stream=stream, temperature=temperature)
        return client.chat.completions.create(model=model, **kwargs)
    except Exception as e:
        emsg = str(e)
        if ("Unsupported value: 'temperature'" in emsg) or ("does not support" in emsg and "temperature" in emsg):
            kwargs = _chat_args(messages, max_completion_tokens, stream=stream, temperature=None)
            return client.chat.completions.create(model=model, **kwargs)
        raise

# -----------------------------------------------------------------------------
# Data-only (Assistant v2)
# -----------------------------------------------------------------------------
def run_data_only_assistant(client: OpenAI, assistant_id: str, user_text: str, lang: str, tenant_id: str = "") -> str:
    contextual_prompt = build_context_prompt(tenant_id, user_text)
    reminder = (
        f"Tu es un expert en aviculture. Réponds aux questions en utilisant tes connaissances.\n"
        f"Si tu ne connais pas la réponse précise, dis-le clairement.\n"
        f"Réponds dans la langue de la question: {lang}\n\n"
        f"Question: {contextual_prompt}"
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
# Fallback general (stream) - VERSION CORRIGÉE
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
                    chunk = delta.content  # Laissez OpenAI gérer le streaming naturel
                    final_buf.append(chunk)
                    yield send_event({"type": "delta", "text": chunk})
        
        final_text = clean_text("".join(final_buf).strip())
        if not final_text:
            final_text = "Désolé, aucune réponse n'a pu être générée. Pouvez-vous reformuler ou préciser votre question ?"
        
        # Streaming intelligent pour les réponses complètes
        chunks = smart_chunk_with_natural_breaks(final_text, STREAM_CHUNK_LEN)
        for chunk in chunks:
            if chunk.strip():
                yield send_event({"type": "delta", "text": chunk})
                await asyncio.sleep(0.02)
        yield send_event({"type": "final", "answer": final_text})

    except Exception as e:
        if "must be verified to stream" in str(e).lower() or "param': 'stream'" in str(e).lower():
            resp = create_chat_completion_safe(
                client, model=FALLBACK_MODEL,
                messages=[{"role":"system","content":system},{"role":"user","content":text}],
                max_completion_tokens=FALLBACK_MAX_COMPLETION_TOKENS, stream=False, temperature=FALLBACK_TEMPERATURE
            )
            final_text = clean_text(resp.choices[0].message.content or "") or "Désolé, aucune réponse n'a pu être générée."
            yield send_event({"type":"final","answer":final_text})
            return
        logger.error(f"Erreur fallback streaming: {e}")
        yield send_event({"type": "final", "answer": "Désolé, une erreur est survenue et la réponse n'a pas pu être générée."})

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.get("/health")
def health():
    global rag_engine
    
    # Stats mémoire de conversation (existant)
    memory_stats = {
        "active_conversations": len(conversation_memory),
        "total_exchanges": sum(len(history) for history in conversation_memory.values()),
        "memory_size_kb": len(str(conversation_memory)) // 1024
    }
    
    # Stats RAG (nouveau)
    rag_stats = {
        "rag_enabled": os.getenv("RAG_ENABLED", "true").lower() == "true",
        "rag_engine_loaded": rag_engine is not None,
        "rag_status": rag_engine.get_status() if rag_engine else {}
    }
    
    return {
        "ok": True,
        "assistant_id": ASSISTANT_ID,
        "guard_mode": "permissive_non_agri",
        "debug_guard": DEBUG_GUARD,
        "hybrid_mode": HYBRID_MODE,
        "language_file": LANGUAGE_FILE,
        "blocked_terms_file": BLOCKED_TERMS_FILE,
        "fallback_model": FALLBACK_MODEL,
        "languages_loaded": list(OUT_OF_DOMAIN_MESSAGES.keys())[:10] + (["…"] if len(OUT_OF_DOMAIN_MESSAGES) > 10 else []),
        "blocked_terms_count": len(BLOCKED_TERMS),
        "blocked_terms_sample": BLOCKED_TERMS[:10],
        "conversation_memory": memory_stats,
        "max_memory_items": MAX_MEMORY_ITEMS,
        "rag": rag_stats  # Nouveau
    }

@router.get("/debug/intent/{question}")
def debug_intent_endpoint(question: str):
    """Endpoint pour tester la détection d'intentions"""
    try:
        # Décoder l'URL
        decoded_question = urllib.parse.unquote(question)
        
        # Analyser la question
        intent_data = extract_intent_from_question(decoded_question)
        
        # Simuler une réponse
        mock_answer = "Le poids d'un poulet Ross 308 à 19 jours est d'environ 860 grammes."
        
        # Tester la génération de relance
        should_generate = should_generate_proactive_followup(decoded_question, mock_answer, intent_data)
        followup = None
        if should_generate:
            followup = generate_proactive_followup(decoded_question, mock_answer, "fr")
        
        return {
            "question": decoded_question,
            "intent_data": intent_data,
            "should_generate_followup": should_generate,
            "proactive_followup": followup,
            "mock_answer_length": len(mock_answer),
            "debug_notes": {
                "metric_templates_count": len(METRIC_FOLLOWUP_TEMPLATES),
                "intents_config_loaded": bool(INTENTS_CONFIG)
            }
        }
    except Exception as e:
        return {"error": str(e), "question": question}

@router.post("/debug/test-followup")
async def test_followup_endpoint(request: Request):
    """Endpoint pour tester le système de relances avec une vraie question/réponse"""
    try:
        payload = await request.json()
        question = payload.get("question", "")
        answer = payload.get("answer", "")
        lang = payload.get("lang", "fr")
        
        if not question or not answer:
            raise HTTPException(status_code=400, detail="question and answer required")
        
        intent_data = extract_intent_from_question(question)
        should_generate = should_generate_proactive_followup(question, answer, intent_data)
        followup = None
        
        if should_generate:
            followup = generate_proactive_followup(question, answer, lang)
        
        return {
            "question": question,
            "answer": answer[:100] + "..." if len(answer) > 100 else answer,
            "intent_data": intent_data,
            "should_generate_followup": should_generate,
            "proactive_followup": followup,
            "answer_length": len(answer)
        }
        
    except Exception as e:
        logger.error(f"Erreur test followup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/nli")
async def debug_nli():
    """Route de diagnostic pour tester le classificateur NLI"""
    global rag_engine
    if rag_engine and rag_engine.classifier:
        try:
            await rag_engine.classifier.load_model()
            is_loaded = rag_engine.classifier.is_loaded
            return {
                "nli_status": "loaded" if is_loaded else "failed",
                "model_path": os.getenv("NLI_MODEL_PATH", "MoritzLaurer/deberta-v3-base-zeroshot-v2"),
                "error": None
            }
        except Exception as e:
            return {
                "nli_status": "error",
                "error": str(e),
                "model_path": os.getenv("NLI_MODEL_PATH", "MoritzLaurer/deberta-v3-base-zeroshot-v2")
            }
    return {"nli_status": "engine_not_available"}

@router.get("/debug/nli-detailed")
async def debug_nli_detailed():
    """Diagnostic détaillé du classificateur NLI"""
    import traceback
    
    try:
        # Test direct d'import
        from transformers import pipeline
        model_path = os.getenv("NLI_MODEL_PATH", "MoritzLaurer/deberta-v3-base-zeroshot-v2")
        
        # Test de chargement du modèle avec timeout
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Model loading timeout")
        
        # Timeout de 30 secondes
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        try:
            classifier = pipeline(
                "zero-shot-classification",
                model=model_path,
                device=-1  # Forcer CPU
            )
            signal.alarm(0)  # Annuler timeout
            
            # Test rapide du modèle
            test_result = classifier("test agriculture question", ["agriculture", "technologie"])
            
            return {
                "nli_status": "success",
                "model_path": model_path,
                "test_classification": test_result['labels'][0],
                "confidence": test_result['scores'][0]
            }
            
        except TimeoutError:
            return {
                "nli_status": "timeout",
                "error": "Model loading timeout after 30 seconds",
                "model_path": model_path
            }
            
    except ImportError as e:
        return {
            "nli_status": "import_error",
            "error": f"Import failed: {str(e)}",
            "missing_package": str(e)
        }
    except Exception as e:
        return {
            "nli_status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/rag/status")
def rag_status():
    """Status détaillé du système RAG"""
    global rag_engine
    
    base_status = {
        "rag_enabled": os.getenv("RAG_ENABLED", "true").lower() == "true",
        "rag_engine_loaded": rag_engine is not None
    }
    
    if rag_engine:
        detailed_status = rag_engine.get_status()
        base_status.update(detailed_status)
    
    return base_status

@router.post("/rag/add-documents")
async def add_documents_to_rag(request: Request):
    """Ajouter des documents à la base de connaissances RAG"""
    global rag_engine
    
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine not available")
    
    try:
        payload = await request.json()
        documents = payload.get("documents", [])
        
        if not documents:
            raise HTTPException(status_code=400, detail="No documents provided")
        
        # Validation des documents
        for i, doc in enumerate(documents):
            if not isinstance(doc, dict) or "content" not in doc:
                raise HTTPException(status_code=400, detail=f"Document {i} missing 'content' field")
        
        success = await rag_engine.add_knowledge(documents)
        
        return {
            "success": success,
            "documents_added": len(documents) if success else 0,
            "message": "Documents ajoutés avec succès" if success else "Erreur lors de l'ajout"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur ajout documents RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag/test-query")
async def test_rag_query(request: Request):
    """Test direct du pipeline RAG pour debug"""
    global rag_engine
    
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine not available")
    
    try:
        payload = await request.json()
        query = payload.get("query", "").strip()
        language = payload.get("language", "fr")
        
        if not query:
            raise HTTPException(status_code=400, detail="Query required")
        
        result = await process_question_with_rag(rag_engine, query, language)
        
        return {
            "query": query,
            "language": language,
            "result": {
                "source": result.source.value,
                "answer": result.answer,
                "confidence": result.confidence,
                "processing_time": result.processing_time,
                "context_docs": result.context_docs,
                "metadata": result.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur test RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream(request: Request):
    """
    JSON attendu: { "tenant_id": "ten_123", "message": "...", "allow_fallback": true }
    Version avec intégration RAG complète
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

    async def event_source() -> AsyncGenerator[bytes, None]:
        sent_final = False
        final_response = ""
        
        try:
            # Initialiser RAG si nécessaire
            global rag_engine
            if rag_engine is None:
                rag_engine = await initialize_rag_engine()
            
            # === NOUVEAU PIPELINE RAG ===
            if rag_engine:
                logger.info(f"[REQ {request_id}] Traitement via pipeline RAG")
                
                # Traitement RAG complet
                rag_result = await process_question_with_rag(
                    rag_engine, message, lang, tenant_id
                )
                
                logger.info(f"[REQ {request_id}] RAG result: {rag_result.source.value}, confidence: {rag_result.confidence:.3f}")
                
                # Cas 1: Question hors domaine (filtrée par NLI)
                if rag_result.source == RAGSource.OOD_FILTERED:
                    answer = clean_text(get_out_of_domain_message(lang))
                    yield send_event({"type": "final", "answer": answer})
                    sent_final = True
                    return
                
                # Cas 2: Réponse RAG de qualité trouvée
                if (rag_result.source == RAGSource.RAG_KNOWLEDGE and 
                    rag_result.answer and 
                    rag_result.confidence >= RAG_CONFIDENCE_THRESHOLD):
                    
                    final_response = clean_text(rag_result.answer)
                    
                    # Streaming intelligent de la réponse RAG
                    chunks = smart_chunk_with_natural_breaks(final_response, STREAM_CHUNK_LEN)
                    for chunk in chunks:
                        if chunk.strip():
                            yield send_event({"type": "delta", "text": chunk})
                            await asyncio.sleep(0.02)
                    
                    # Métadonnées RAG dans la réponse finale
                    yield send_event({
                        "type": "final", 
                        "answer": final_response,
                        "metadata": {
                            "source": "rag",
                            "confidence": rag_result.confidence,
                            "processing_time": rag_result.processing_time,
                            "context_docs": len(rag_result.context_docs),
                            **rag_result.metadata
                        }
                    })
                    sent_final = True
                    
                    # Ajouter à la mémoire et générer relance proactive
                    add_to_conversation_memory(tenant_id, message, final_response)
                    proactive_followup = generate_proactive_followup(message, final_response, lang)
                    if proactive_followup:
                        logger.info(f"[REQ {request_id}] Sending RAG proactive followup")
                        yield send_event({"type": "proactive_followup", "answer": proactive_followup})
                    
                    return
                
                # Cas 3: RAG insuffisant mais pas d'erreur -> fallback
                logger.info(f"[REQ {request_id}] RAG insuffisant, fallback vers système existant")
            else:
                logger.warning(f"[REQ {request_id}] RAG Engine non disponible, fallback immédiat")
            
            # === FALLBACK VERS SYSTÈME EXISTANT ===
            
            # 1) Garde-fou classique (conservé pour compatibilité)
            if not is_agri_question(message):
                answer = clean_text(get_out_of_domain_message(lang))
                yield send_event({"type": "final", "answer": answer})
                sent_final = True
                return

            _client = client

            # 2) Tentative data-only (Assistant v2) avec contexte
            text = await asyncio.to_thread(run_data_only_assistant, _client, ASSISTANT_ID, message, lang, tenant_id)
            text = clean_text(text)
            logger.info(f"[REQ {request_id}] Assistant response: {text[:100]}...")

            # 3) Fallback GPT si hors base
            if text.lower().startswith("hors base"):
                if HYBRID_MODE and allow_fallback:
                    logger.info(f"[REQ {request_id}] Basculement vers fallback GPT")
                    async for sse in stream_fallback_general(_client, message):
                        yield sse
                        # Collecter pour la mémoire
                        try:
                            sse_data = json.loads(sse.decode('utf-8').replace('data: ', ''))
                            if sse_data.get('type') == 'final':
                                final_response = sse_data.get('answer', '')
                        except:
                            pass
                    sent_final = True
                else:
                    final_response = text
                    yield send_event({
                        "type": "final", 
                        "answer": text,
                        "metadata": {"source": "assistant_ood"}
                    })
                    sent_final = True
            else:
                # 4) Réponse data-only (stream intelligent)
                if not text:
                    text = "Désolé, aucune réponse n'a pu être générée."
                
                # Streaming intelligent
                chunks = smart_chunk_with_natural_breaks(text, STREAM_CHUNK_LEN)
                for chunk in chunks:
                    if chunk.strip():
                        yield send_event({"type": "delta", "text": chunk})
                        await asyncio.sleep(0.02)
                
                final_response = text
                yield send_event({
                    "type": "final", 
                    "answer": text,
                    "metadata": {"source": "assistant_knowledge"}
                })
                sent_final = True

            # 5) Ajouter à la mémoire et générer relance pour fallback
            if final_response:
                add_to_conversation_memory(tenant_id, message, final_response)
                proactive_followup = generate_proactive_followup(message, final_response, lang)
                if proactive_followup:
                    logger.info(f"[REQ {request_id}] Sending fallback proactive followup")
                    yield send_event({"type": "proactive_followup", "answer": proactive_followup})

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[REQ {request_id}] Erreur dans event_source: {e}")
            if not sent_final:
                yield send_event({
                    "type": "final", 
                    "answer": "Désolé, une erreur est survenue et la réponse n'a pas pu être générée.",
                    "metadata": {"source": "error", "error": str(e)}
                })
                sent_final = True
            else:
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
    return JSONResponse({"service": "intelia-llm", "sse": f"{BASE_PATH}/chat/stream", "version": "simplified-rag"})

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