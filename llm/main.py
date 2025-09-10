#
# main.py — Intelia LLM backend (FastAPI + SSE)
#
# Python 3.11+
#

import os, re, json, asyncio
import time
from typing import Any, Dict, AsyncGenerator

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0  # déterminisme

# Charge .env si présent (utile en local)
load_dotenv()

# -------- Config via variables d'environnement --------
BASE_PATH = os.environ.get("BASE_PATH", "/llm").rstrip("/")  # ex: "/llm" ou ""
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")  # asst_... (créé avec tes fichiers)
# Optionnel: timeouts
POLL_INTERVAL_SEC = float(os.environ.get("POLL_INTERVAL_SEC", "0.6"))
STREAM_CHUNK_LEN = int(os.environ.get("STREAM_CHUNK_LEN", "400"))

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
if not ASSISTANT_ID:
    raise RuntimeError("ASSISTANT_ID is required")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------- App & CORS --------
app = FastAPI(title="Intelia LLM Backend")
# CORS permissif par défaut; restreins origin en prod si besoin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

router = APIRouter()

# -------- Utilitaires --------
def sse_event(obj: Dict[str, Any]) -> bytes:
    """Encode un event SSE (Server-Sent Events)."""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")


def parse_accept_language(header: str | None) -> str | None:
    """Parse l'en-tête Accept-Language pour extraire le code langue principal."""
    if not header:
        return None
    # Ex: "fr-CA,fr;q=0.9,en;q=0.8"
    try:
        first = header.split(",")[0].strip()
        code = first.split(";")[0].split("-")[0].lower()
        if 2 <= len(code) <= 3:
            return code
    except Exception:
        pass
    return None


def guess_lang_from_text(text: str) -> str | None:
    """Détecte automatiquement la langue d'un texte."""
    try:
        code = detect(text)  # 'fr', 'en', ...
        return code
    except Exception:
        return None


# -------- Nettoyage des marqueurs de source --------
# Supprime toute séquence entre crochets pleins `【 ... 】`
# Exemple : "", "【turn7file4†L10-L20】", etc.
CITATION_PATTERN = re.compile(r"【[^】]*】")

def clean_text(txt: str) -> str:
    if not txt:
        return txt
    cleaned = CITATION_PATTERN.sub("", txt)
    # Normalise les espaces après suppression
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# -------- Garde-fou permissif (liste NON-AGRI) --------
# Principe: on ACCEPTE par défaut tout ce qui peut toucher directement/indirectement à l'agriculture.
# On REJETTE seulement si on détecte explicitement un domaine manifestement hors-sujet.
NON_AGRI_TERMS = [
    # Divertissement & culture pop
    "cinéma","film","films","séries","serie","séries tv","netflix","hollywood","bollywood","disney",
    "pixar","musique","concert","rap","pop","rock","jazz","opéra","orchestre","télévision","télé",
    "emission","émission","talk-show","talk show","documentaire","jeux vidéo","gaming","playstation",
    "xbox","nintendo","e-sport","esport","fortnite","minecraft","twitch",
    # Sport & loisirs
    "football","soccer","nba","nfl","nhl","hockey","baseball","mlb","tennis","golf","cyclisme",
    "tour de france","formule 1","f1","motogp","boxe","ufc","olympiques","olympics","fitness",
    "musculation","yoga","randonnée","plongée","ski","surf","basketball","rugby","cricket",
    # Politique & société
    "élections","elections","président","president","premier ministre","parlement","sénat","senat",
    "congrès","congres","diplomatie","guerre","armée","armee","conflit","otan","onu","droit humain",
    "droits humains","immigration","lois","justice","criminel","tribunal","révolution","révolte",
    # Finance & économie grand public
    "bourse","actions","nasdaq","wall street","s&p500","dow jones","crypto","bitcoin","ethereum",
    "blockchain","nft","banque","banques","crédit","credits","prêt","pret","hypothèque","hypotheque",
    "assurance","impôt","impots","fiscalité","fiscalite","immobilier","courtage","trading",
    "hedge fund","capital risque","capital-risque","private equity","forex",
    # Tech grand public
    "iphone","android","samsung","apple","google","microsoft","windows","linux","amazon","tesla",
    "réseaux sociaux","reseaux sociaux","facebook","instagram","tiktok","youtube","twitter","x ",
    "snapchat","applications mobiles","app mobile","messagerie","whatsapp","telegram","signal",
    "streaming","spotify","itunes",
    # Santé humaine (hors zoonoses / comparaisons animales)
    "cancer","diabète","diabete","hypertension","grippe saisonnière","grippe saisonniere","covid",
    "hôpital","hopital","clinique","pharmacie","chirurgie esthétique","dentiste","dentisterie",
    "nutrition humaine","régime","regime","keto","végan","vegan","végétarien","vegetarien",
    # Mode, lifestyle & tourisme
    "vêtements","vetements","chaussures","bijoux","luxe","gucci","louis vuitton","zara","nike",
    "coiffure","maquillage","cosmétiques","cosmetiques","parfums","voyage","vacances","tourisme",
    "hôtel","hotel","airbnb","croisière","croisiere","disneyland","gastronomie","recette",
    # Sciences & éducation non agricoles
    "astronomie","physique quantique","astrophysique","fusées","fusees","nasa","spacex","mathématiques",
    "mathematiques","philosophie","histoire","archéologie","archeologie","psychologie","psychanalyse",
    "sociologie",
    # Religion & ésotérisme
    "église","eglise","prière","priere","islam","christianisme","judaïsme","judaisme","bouddhisme",
    "astrologie","horoscope","tarot","voyance","magie","sorcellerie",
    # Autres clairement hors-sujet agri
    "météo urbaine","meteo urbaine","météo de paris","meteo de paris","trafic routier","bouchons",
    "automobile","course automobile","tuning","uber","lyft","relations amoureuses","sexualité",
    "sexualite","mariage","divorce","fashion week","influenceur","influenceuse"
]

# Construit un regex robuste : \b(?:terme1|terme2|...)\b
# (Les espaces à l'intérieur des termes multi-mots sont respectés)
NON_AGRI_PAT = re.compile(
    r"\b(?:"
    + "|".join(re.escape(t) for t in NON_AGRI_TERMS)
    + r")\b",
    re.IGNORECASE,
)

def is_agri_question(text: str) -> bool:
    """
    Filtre permissif : accepte par défaut.
    Rejette seulement si un terme non-agricole explicite est détecté.
    """
    if not text:
        return True
    return not bool(NON_AGRI_PAT.search(text))


# --- Data-only (Assistant v2) : exécution non streamée, on bufferise le texte ---
def run_data_only_assistant(client: OpenAI, assistant_id: str, user_text: str, lang: str) -> str:
    """
    Lance l'assistant 'data-only' (relié à ton Vector Store) et renvoie le texte final.
    S'il n'y a pas de preuve, l'assistant doit répondre exactement :
    "Hors base: information absente de la connaissance Intelia."
    """
    reminder = (
        "RÉPONDS EXCLUSIVEMENT à partir des documents du Vector Store. "
        "Si l'information est absente, réponds exactement: "
        "\"Hors base: information absente de la connaissance Intelia.\" "
        f"Réponds en {lang}. Ne traduis pas dans une autre langue sauf si on te le demande."
    )
    # 1) thread + message
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"{user_text}\n\n{reminder}",
    )
    # 2) run + poll
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)
    while True:
        r = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if r.status in ("completed", "failed", "cancelled", "expired"):
            break
        time.sleep(POLL_INTERVAL_SEC)
    if r.status != "completed":
        return "Hors base: information absente de la connaissance Intelia."
    # 3) récupérer le dernier message assistant
    msgs = client.beta.threads.messages.list(thread_id=thread.id)
    for m in msgs.data:
        if m.role == "assistant":
            for c in m.content:
                if getattr(c, "type", "") == "text":
                    txt = (c.text.value or "").strip()
                    txt = clean_text(txt)  # suppression des marqueurs 【...】
                    return txt if txt else "Hors base: information absente de la connaissance Intelia."
    return "Hors base: information absente de la connaissance Intelia."


# --- Fallback général (GPT-5) : streaming réel limité au domaine agricole ---
async def stream_fallback_general(client: OpenAI, text: str, lang: str):
    """
    Stream GPT-5 via Chat Completions, en limitant explicitement le domaine
    (agriculture/aviculture). Répond dans la langue détectée.
    """
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
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )

    final_buf = []
    for event in stream:
        if hasattr(event, "choices") and event.choices:
            delta = event.choices[0].delta
            if delta and getattr(delta, "content", None):
                chunk = delta.content
                # Nettoie à la volée les éventuels marqueurs dans le flux
                cleaned_chunk = clean_text(chunk)
                final_buf.append(cleaned_chunk)
                yield f'data: {json.dumps({"type":"delta","text": cleaned_chunk}, ensure_ascii=False)}\n\n'
    final_text = clean_text("".join(final_buf).strip())
    yield f'data: {json.dumps({"type":"final","answer": final_text}, ensure_ascii=False)}\n\n'


@router.get("/health")
def health():
    return {"ok": True, "assistant_id": ASSISTANT_ID}


@router.post("/chat/stream")
async def chat_stream(request: Request):
    """
    Body attendu (JSON):
      { "tenant_id": "ten_123", "message": "...", "allow_fallback": true }

    Réponse: flux SSE hybride
      - Essaie d'abord l'assistant data-only
      - Si "Hors base" et fallback activé → GPT-5 streaming
      - Sinon → réponse data-only streamée

    Logique:
      1. Garde-fou permissif (rejette seulement les domaines non-agri explicites)
      2. Assistant data-only (non streamé, bufferisé)
      3. Fallback GPT-5 conditionnel (streamé)
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    tenant_id = (payload.get("tenant_id") or "").strip()
    message = (payload.get("message") or "").strip()
    allow_fallback = bool(payload.get("allow_fallback", True))  # par défaut ON

    if not tenant_id or not message:
        raise HTTPException(status_code=400, detail="missing_fields")

    # Détection automatique de langue
    accept_lang = request.headers.get("accept-language")
    lang = parse_accept_language(accept_lang)
    if not lang:
        lang = guess_lang_from_text(message) or "fr"
    lang = (lang or "fr")[:5].split("-")[0].lower()

    async def event_source() -> AsyncGenerator[str, None]:
        # 0) garde-fou permissif
        if not is_agri_question(message):
            answer = f"Domaine restreint : {os.getenv('ALLOWED_DOMAIN_DESC') or 'agriculture et sujets adjacents uniquement'}."
            answer = clean_text(answer)
            yield f'data: {json.dumps({"type":"final","answer": answer})}\n\n'
            return

        _client = OpenAI(api_key=OPENAI_API_KEY)
        
        # 1) essayer data-only (Assistant v2)
        text = await asyncio.to_thread(
            run_data_only_assistant, _client, ASSISTANT_ID, message, lang
        )
        text = clean_text(text)

        # 2) si "Hors base" → fallback (si autorisé)
        if text.lower().startswith("hors base"):
            if os.getenv("HYBRID_MODE") and allow_fallback:
                async for sse in stream_fallback_general(_client, message, lang):
                    yield sse
                return
            else:
                yield f'data: {json.dumps({"type":"final","answer": text})}\n\n'
                return

        # 3) Sinon (réponse data-only) — on envoie delta + final (avec nettoyage)
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


# Monte toutes les routes sous BASE_PATH (ex: /llm)
app.include_router(router, prefix=BASE_PATH)


@app.get("/")
def root():
    # Petit ping pour vérifier le service
    return JSONResponse({"service": "intelia-llm", "sse": f"{BASE_PATH}/chat/stream"})


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow: /\n"
