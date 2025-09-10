#
# main.py — Intelia LLM backend (FastAPI + SSE)
# Python 3.11+
#

import os, re, json, asyncio, time, unicodedata, difflib
from typing import Any, Dict, AsyncGenerator, Optional, Tuple, List
from dataclasses import dataclass

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0  # déterminisme
load_dotenv()

# -------- Config via variables d'environnement --------
BASE_PATH = os.environ.get("BASE_PATH", "/llm").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
POLL_INTERVAL_SEC = float(os.environ.get("POLL_INTERVAL_SEC", "0.6"))
STREAM_CHUNK_LEN = int(os.environ.get("STREAM_CHUNK_LEN", "400"))
DEBUG_GUARD = os.getenv("DEBUG_GUARD", "0") == "1"

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
if not ASSISTANT_ID:
    raise RuntimeError("ASSISTANT_ID is required")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------- App & CORS --------
app = FastAPI(title="Intelia LLM Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
router = APIRouter()

def sse_event(obj: Dict[str, Any]) -> bytes:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")

def parse_accept_language(header: Optional[str]) -> Optional[str]:
    if not header: return None
    try:
        first = header.split(",")[0].strip()
        code = first.split(";")[0].split("-")[0].lower()
        if 2 <= len(code) <= 3: return code
    except Exception:
        pass
    return None

def guess_lang_from_text(text: str) -> Optional[str]:
    try:
        return detect(text)
    except Exception:
        return None

# -------- Nettoyage des marqueurs de source --------
CITATION_PATTERN = re.compile(r"【[^】]*】")
def clean_text(txt: str) -> str:
    if not txt: return txt
    cleaned = CITATION_PATTERN.sub("", txt)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

# -------- Garde-fou permissif (liste NON-AGRI) --------
NON_AGRI_TERMS = [
    "cinéma","film","films","séries","serie","séries tv","netflix","hollywood","bollywood","disney",
    "pixar","musique","concert","rap","pop","rock","jazz","opéra","orchestre","télévision","télé",
    "emission","émission","talk-show","talk show","documentaire","jeux vidéo","gaming","playstation",
    "xbox","nintendo","e-sport","esport","fortnite","minecraft","twitch",
    "football","soccer","nba","nfl","nhl","hockey","baseball","mlb","tennis","golf","cyclisme",
    "tour de france","formule 1","f1","motogp","boxe","ufc","olympiques","olympics","fitness",
    "musculation","yoga","randonnée","plongée","ski","surf","basketball","rugby","cricket",
    "élections","elections","président","president","premier ministre","parlement","sénat","senat",
    "congrès","congres","diplomatie","guerre","armée","armee","conflit","otan","onu","droit humain",
    "droits humains","immigration","lois","justice","criminel","tribunal","révolution","révolte",
    "bourse","actions","nasdaq","wall street","s&p500","dow jones","crypto","bitcoin","ethereum",
    "blockchain","nft","banque","banques","crédit","credits","prêt","pret","hypothèque","hypotheque",
    "assurance","impôt","impots","fiscalité","fiscalite","immobilier","courtage","trading",
    "hedge fund","capital risque","capital-risque","private equity","forex",
    "iphone","android","samsung","apple","google","microsoft","windows","linux","amazon","tesla",
    "réseaux sociaux","reseaux sociaux","facebook","instagram","tiktok","youtube","twitter","x ",
    "snapchat","applications mobiles","app mobile","messagerie","whatsapp","telegram","signal",
    "streaming","spotify","itunes",
    "cancer","diabète","diabete","hypertension","grippe saisonnière","grippe saisonniere","covid",
    "hôpital","hopital","clinique","pharmacie","chirurgie esthétique","dentiste","dentisterie",
    "nutrition humaine","régime","regime","keto","végan","vegan","végétarien","vegetarien",
    "vêtements","vetements","chaussures","bijoux","luxe","gucci","louis vuitton","zara","nike",
    "coiffure","maquillage","cosmétiques","cosmetiques","parfums","voyage","vacances","tourisme",
    "hôtel","hotel","airbnb","croisière","croisiere","disneyland","gastronomie","recette",
    "astronomie","physique quantique","astrophysique","fusées","fusees","nasa","spacex","mathématiques",
    "mathematiques","philosophie","histoire","archéologie","archeologie","psychologie","psychanalyse",
    "sociologie",
    "église","eglise","prière","priere","islam","christianisme","judaïsme","judaisme","bouddhisme",
    "astrologie","horoscope","tarot","voyance","magie","sorcellerie",
    "météo urbaine","meteo urbaine","météo de paris","meteo de paris","trafic routier","bouchons",
    "automobile","course automobile","tuning","uber","lyft","relations amoureuses","sexualité",
    "sexualite","mariage","divorce","fashion week","influenceur","influenceuse"
]
NON_AGRI_PAT = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in NON_AGRI_TERMS) + r")\b", re.IGNORECASE)

def guard_debug(reason: str, text: str):
    if DEBUG_GUARD:
        print(f"[GUARD] {reason} :: {text[:160]!r}")

def is_agri_question(text: str) -> bool:
    if not text: return True
    blocked = NON_AGRI_PAT.search(text) is not None
    if blocked: guard_debug("blocked_non_agri_match", text)
    return not blocked

# -------- Normalisation & alias (pour tolérance aux fautes) --------
def normalize(s: str) -> str:
    if s is None: return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower().strip()
    s = "".join(ch for ch in s if ch.isalnum() or ch.isspace())
    s = re.sub(r"\s+", " ", s)
    return s

LINE_ALIASES = {
    # Ross
    "ross 308": ["ross308","r308","ross-308","罗斯308","羅斯308","ross 308 ap","ross 308ap","ross"],
    # Cobb
    "cobb 500": ["cobb500","c500","cobb-500","科寶500","科博500","cobb"],
}
SEX_ALIASES = {
    "male": ["mâle","masculin","male","macho","公","雄","boy","garçon","garcon"],
    "female": ["femelle","feminin","féminin","female","hembra","母","雌","girl","fille"],
}

def fuzzy_map(value: str, choices: Dict[str, List[str]], cutoff: float = 0.75) -> Optional[str]:
    v = normalize(value)
    pool = []
    for key, alias_list in choices.items():
        pool.append(key)
        pool.extend(alias_list)
    best = difflib.get_close_matches(v, pool, n=1, cutoff=cutoff)
    if not best: return None
    hit = best[0]
    # Map alias back to canonical key
    for key, alias_list in choices.items():
        if hit == key or hit in [normalize(a) for a in alias_list]:
            return key
    return None

# -------- Intent & Slots (multilingue, tolérant) --------
# Intent: poids/weight/体重/體重/目标体重/標準體重/目标/target/objectif/增重
BROILER_WEIGHT_INTENT_PAT = re.compile(
    r"(?:(poids|weight|peso|体重|體重|標準體重|标准体重|目標體重|目标体重|objectif|target|增重|增重曲線|增重曲线))"
    r".*?(poulet|broiler|ross|cobb|鸡|雞|小鸡|雛雞)?|"
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
    return bool(BROILER_WEIGHT_INTENT_PAT.search(text))

def extract_broiler_weight_slots(text: str) -> BroilerWeightSlots:
    tnorm = normalize(text)

    # Age
    age = None
    m_age = AGE_DAYS_PAT.search(text)
    if m_age:
        age = m_age.group(1) or m_age.group(3)
        age = int(age) if age is not None else None

    # Line (regex coarse)
    line = None
    m_line = LINE_PAT.search(text)
    if m_line:
        rough = m_line.group(1).lower()
        # Fuzzy enrich (could be 'ross' only → leave as None to clarify)
        line = fuzzy_map(rough, LINE_ALIASES, cutoff=0.6) or (rough if rough in ["ross","cobb"] else None)

    # Sex
    sex = None
    if MALE_PAT.search(text):
        sex = "male"
    elif FEMALE_PAT.search(text):
        sex = "female"
    else:
        # Fuzzy from whole text (handles typos)
        # check presence of any alias token
        for k, arr in SEX_ALIASES.items():
            for a in arr:
                if normalize(a) in tnorm:
                    sex = k
                    break
            if sex: break

    # Fuzzy correction if user typed model directly like "ross308"
    if not line:
        # grab any token ~ line
        tokens = tnorm.split()
        for token in tokens:
            hit = fuzzy_map(token, LINE_ALIASES, cutoff=0.8)
            if hit:
                line = hit
                break

    return BroilerWeightSlots(age_days=age, line=line, sex=sex)

# GPT extractor JSON (fallback si extraction regex/fuzzy est pauvre)
def gpt_extract_slots(client: OpenAI, text: str, lang: str) -> BroilerWeightSlots:
    system = (
        "Extract broiler target-weight query entities as strict JSON with keys: "
        "age_days (int|null), line (one of ['ross 308','cobb 500', null]), sex (one of ['male','female', null]). "
        "Infer from multilingual text (fr/en/es/zh). If only 'ross' or 'cobb' given, set line=null (needs subline). "
        "Return ONLY JSON."
    )
    user = text
    resp = client.chat.completions.create(
        model=os.getenv("FALLBACK_MODEL", "gpt-5"),
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.0, max_tokens=100
    )
    raw = resp.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
        age = data.get("age_days")
        line = data.get("line")
        sex  = data.get("sex")
        # Normalize line through aliases if needed
        if isinstance(line, str):
            line = fuzzy_map(line, LINE_ALIASES, cutoff=0.6) or line
        if line and line in ["ross","cobb"]:
            line = None  # force clarification for subline specificity
        if isinstance(sex, str):
            sex = "male" if "male" in sex.lower() else ("female" if "female" in sex.lower() else None)
        if isinstance(age, str) and age.isdigit():
            age = int(age)
        if isinstance(age, int) and (age < 0 or age > 70):
            age = None
        return BroilerWeightSlots(age_days=age, line=line, sex=sex)
    except Exception:
        return BroilerWeightSlots(age_days=None, line=None, sex=None)

async def ask_for_missing_slots_with_gpt(client: OpenAI, lang: str, slots: BroilerWeightSlots) -> Tuple[str, Dict[str, Any]]:
    missing = []
    if slots.line is None: missing.append("lignée (ex. Ross 308, Cobb 500)")
    if slots.sex is None:  missing.append("sexe (mâle ou femelle)")
    if slots.age_days is None: missing.append("âge (en jours)")
    # default minimal prompts
    default_map = {
        "fr": "Pour répondre précisément, précise la lignée (ex. Ross 308, Cobb 500) et le sexe (mâle ou femelle), ainsi que l’âge en jours si absent.",
        "en": "To answer precisely, please specify the line (e.g., Ross 308, Cobb 500), the sex (male or female), and age in days if missing.",
        "zh": "为准确回答，请补充：品系（如 Ross 308、Cobb 500）、性别（公或母），以及（若缺少）日龄。",
        "es": "Para responder con precisión, indica la línea (p. ej., Ross 308, Cobb 500), el sexo (macho o hembra) y la edad en días si falta."
    }
    default = default_map.get(lang, default_map["en"])

    # Chips de suggestion (UI côté client)
    suggestions = {
        "lines": ["Ross 308", "Cobb 500"],
        "sex": ["male", "female"]
    }

    if not missing:
        return default, suggestions

    system = (
        "You write one short clarifying question for a poultry production context. "
        "Ask ONLY for the missing entities to lookup broiler target weight tables: "
        "line (Ross 308/Cobb 500), sex (male/female), and/or age in days. "
        "Be concise, one sentence, no extra commentary."
    )
    user = f"Missing entities: {', '.join(missing)}. Write the question in language code: {lang}."
    resp = client.chat.completions.create(
        model=os.getenv("FALLBACK_MODEL", "gpt-5"),
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.1, max_tokens=80
    )
    q = (resp.choices[0].message.content or "").strip() or default
    return q, suggestions

# --- Assistant data-only (Assistant v2) ---
def run_data_only_assistant(client: OpenAI, assistant_id: str, user_text: str, lang: str) -> str:
    reminder = (
        "RÉPONDS EXCLUSIVEMENT à partir des documents du Vector Store. "
        "Si l'information est absente, réponds exactement: "
        "\"Hors base: information absente de la connaissance Intelia.\" "
        f"Réponds en {lang}. Ne traduis pas dans une autre langue sauf si on te le demande."
    )
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=f"{user_text}\n\n{reminder}",
    )
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)
    while True:
        r = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if r.status in ("completed", "failed", "cancelled", "expired"): break
        time.sleep(POLL_INTERVAL_SEC)
    if r.status != "completed":
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

# --- Fallback général (GPT-5) ---
async def stream_fallback_general(client: OpenAI, text: str, lang: str):
    system = (
        "You are an agricultural domain assistant. Answer ONLY within agriculture "
        "(including livestock, poultry, broilers/layers, animal nutrition, farm environment, "
        "biosecurity, ventilation, poultry diseases, agricultural economics directly related to farms, "
        "and adjacent topics that clearly relate to agriculture). If the user asks anything clearly "
        "outside this scope, politely refuse.\n"
        f"Reply in {lang}."
    )
    model = os.getenv("FALLBACK_MODEL", "gpt-5")
    temperature = float(os.getenv("FALLBACK_TEMPERATURE", "0.2"))
    max_tokens = int(os.getenv("FALLBACK_MAX_TOKENS", "600"))

    stream = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system},{"role":"user","content":text}],
        temperature=temperature, max_tokens=max_tokens, stream=True,
    )

    final_buf = []
    for event in stream:
        if hasattr(event, "choices") and event.choices:
            delta = event.choices[0].delta
            if delta and getattr(delta, "content", None):
                chunk = delta.content
                cleaned_chunk = clean_text(chunk)
                final_buf.append(cleaned_chunk)
                yield f'data: {json.dumps({"type":"delta","text": cleaned_chunk}, ensure_ascii=False)}\n\n'
    final_text = clean_text("".join(final_buf).strip())
    yield f'data: {json.dumps({"type":"final","answer": final_text}, ensure_ascii=False)}\n\n'

@router.get("/health")
def health():
    return {
        "ok": True,
        "assistant_id": ASSISTANT_ID,
        "guard_mode": "permissive_non_agri",
        "debug_guard": DEBUG_GUARD
    }

@router.post("/chat/stream")
async def chat_stream(request: Request):
    """
    JSON attendu: { "tenant_id": "ten_123", "message": "...", "allow_fallback": true }
    Flux SSE:
      - Garde-fou permissif (rejette seulement non-agri explicite)
      - Contextualisation poids broiler (intent+slots). Si slots manquants -> question de clarification
      - Data-only Assistant (RAG). Si "Hors base" et fallback autorisé -> GPT-5 streaming.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    tenant_id = (payload.get("tenant_id") or "").strip()
    message = (payload.get("message") or "").strip()
    allow_fallback = bool(payload.get("allow_fallback", True))

    if not tenant_id or not message:
        raise HTTPException(status_code=400, detail="missing_fields")

    # langue
    accept_lang = request.headers.get("accept-language")
    lang = parse_accept_language(accept_lang) or guess_lang_from_text(message) or "fr"
    lang = (lang or "fr")[:5].split("-")[0].lower()

    async def event_source() -> AsyncGenerator[str, None]:
        # 0) garde-fou permissif
        if not is_agri_question(message):
            answer = f"Domaine restreint : {os.getenv('ALLOWED_DOMAIN_DESC') or 'agriculture et sujets adjacents uniquement'}."
            answer = clean_text(answer)
            yield f'data: {json.dumps({"type":"final","answer": answer})}\n\n'
            return

        _client = OpenAI(api_key=OPENAI_API_KEY)

        # 0-bis) CONTEXTUALISATION — Intent poids broiler
        if detect_broiler_weight_intent(message):
            slots = extract_broiler_weight_slots(message)

            # Si extraction regex/fuzzy trop pauvre, tenter extraction GPT JSON
            if slots.age_days is None or slots.line is None or slots.sex is None:
                gslots = await asyncio.to_thread(gpt_extract_slots, _client, message, lang)
                # Merge préférant infos “certaines”
                slots = BroilerWeightSlots(
                    age_days = slots.age_days or gslots.age_days,
                    line     = slots.line or gslots.line,
                    sex      = slots.sex or gslots.sex
                )

            # Hook (extension future) : si line vaut 'ross' ou 'cobb' (trop vague), forcer clarification
            if slots.line in ("ross","cobb"):
                slots = BroilerWeightSlots(age_days=slots.age_days, line=None, sex=slots.sex)

            # (Option) Normaliser semaines → jours (non implémenté: prévoir conversion 1 sem ~ 7 jours)

            # Si slots manquants → question ciblée + suggestions
            if (slots.line is None) or (slots.sex is None) or (slots.age_days is None):
                clarify, suggestions = await asyncio.to_thread(ask_for_missing_slots_with_gpt, _client, lang, slots)
                clarify = clean_text(clarify)
                # Envoie une réponse de clarification avec suggestions (si le front les exploite)
                yield f'data: {json.dumps({"type":"clarify","answer": clarify, "suggestions": suggestions}, ensure_ascii=False)}\n\n'
                return
            # Sinon → laisser continuer le flux normal (RAG data-only d’abord)

        # 1) Essai data-only (Assistant v2)
        text = await asyncio.to_thread(run_data_only_assistant, _client, ASSISTANT_ID, message, lang)
        text = clean_text(text)

        # 2) Fallback GPT-5 si hors base
        if text.lower().startswith("hors base"):
            if os.getenv("HYBRID_MODE") and allow_fallback:
                async for sse in stream_fallback_general(_client, message, lang):
                    yield sse
                return
            else:
                yield f'data: {json.dumps({"type":"final","answer": text})}\n\n'
                return

        # 3) Sinon, réponse data-only stream simulé
        for i in range(0, len(text), STREAM_CHUNK_LEN):
            chunk = clean_text(text[i:i + STREAM_CHUNK_LEN])
            yield f'data: {json.dumps({"type":"delta","text": chunk})}\n\n'
            await asyncio.sleep(0.02)
        yield f'data: {json.dumps({"type":"final","answer": text})}\n\n'

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
    }
    return StreamingResponse(event_source(), headers=headers)

# Monte les routes
app.include_router(router, prefix=BASE_PATH)

@app.get("/")
def root():
    return JSONResponse({"service": "intelia-llm", "sse": f"{BASE_PATH}/chat/stream"})

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow: /\n"
