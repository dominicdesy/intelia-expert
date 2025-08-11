# -*- coding: utf-8 -*-
"""
Dialogue orchestration - VERSION HYBRIDE (RAGRetriever direct + TABLE-FIRST)
- classify -> normalize -> completeness/clarifications
- Réponse générale + clarifications pour questions incomplètes
- Route vers compute (si possible) OU vers table-first (perf targets) OU vers RAGRetriever (multi-index)
- Retourne un payload structuré pour le frontend
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
import os
import re

logger = logging.getLogger(__name__)

# ========== IMPORTS AVEC FALLBACKS ==========
from ..utils.question_classifier import classify, Intention
from .context_extractor import normalize
from .clarification_manager import compute_completeness
from ..utils import formulas

# ===== Import robuste du RAGRetriever (code original conservé) =====
RAG_AVAILABLE = False
RAGRetrieverCls = None
try:
    from rag.retriever import RAGRetriever as _RAGRetrieverImported
    RAGRetrieverCls = _RAGRetrieverImported
    RAG_AVAILABLE = True
    logger.info("✅ RAGRetriever importé depuis rag.retriever")
except Exception as e1:
    try:
        from ...rag.retriever import RAGRetriever as _RAGRetrieverImported2  # type: ignore
        RAGRetrieverCls = _RAGRetrieverImported2
        RAG_AVAILABLE = True
        logger.info("✅ RAGRetriever importé depuis ...rag.retriever")
    except Exception as e2:
        try:
            from .retriever import RAGRetriever as _RAGRetrieverImported3  # type: ignore
            RAGRetrieverCls = _RAGRetrieverImported3
            RAG_AVAILABLE = True
            logger.info("✅ RAGRetriever importé depuis .retriever")
        except Exception as e3:
            logger.warning(f"⚠️ Impossible d'importer RAGRetriever ({e1} | {e2} | {e3}). RAG désactivé.")
            RAG_AVAILABLE = False
            RAGRetrieverCls = None

# ===== Singleton RAGRetriever =====
_RAG_SINGLETON = None

def _get_retriever():
    """Retourne un singleton RAGRetriever, ou None si indisponible."""
    global _RAG_SINGLETON
    if not RAG_AVAILABLE or RAGRetrieverCls is None:
        return None
    if _RAG_SINGLETON is None:
        try:
            _RAG_SINGLETON = RAGRetrieverCls(openai_api_key=os.environ.get("OPENAI_API_KEY"))
            logger.info("🔎 RAGRetriever initialisé")
        except Exception as e:
            logger.error(f"❌ Init RAGRetriever échoué: {e}")
            _RAG_SINGLETON = None
    return _RAG_SINGLETON

# ===== Import table-first PerfStore =====
try:
    from .perf_store import PerfStore  # lit rag_index/<species>/tables via manifest
    PERF_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ PerfStore indisponible: {e}")
    PerfStore = None  # type: ignore
    PERF_AVAILABLE = False

# ===== Singleton PerfStore =====
_PERF_STORE: Optional["PerfStore"] = None

def _get_perf_store(species_hint: Optional[str] = None) -> Optional["PerfStore"]:
    """
    Instancie un PerfStore pointant vers ./rag_index/<species>/tables/.
    """
    if not PERF_AVAILABLE or PerfStore is None:
        return None
    global _PERF_STORE
    species = (species_hint or "broiler").strip().lower()
    if _PERF_STORE is None or getattr(_PERF_STORE, "species", "") != species:
        try:
            root = os.environ.get("RAG_INDEX_ROOT", "./rag_index")
            _PERF_STORE = PerfStore(root=root, species=species)  # type: ignore
            logger.info(f"📊 PerfStore initialisé (root={root}, species={species})")
        except Exception as e:
            logger.warning(f"⚠️ PerfStore indisponible: {e}")
            _PERF_STORE = None
    return _PERF_STORE

# ===== Utilitaires RAG (code original conservé) =====
def _format_sources(source_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatted = []
    for doc in source_documents[:5]:
        if not isinstance(doc, dict):
            continue
        src = doc.get("source") or doc.get("file_path") or doc.get("path") or "source inconnue"
        if isinstance(src, str) and ("/" in src or "\\" in src):
            src_name = src.split("/")[-1].split("\\")[-1]
        else:
            src_name = str(src)
        md = doc.get("metadata", {})
        formatted.append({
            "name": src_name,
            "meta": {
                "chunk_type": (md or {}).get("chunk_type"),
                "species": (md or {}).get("species"),
                "line": (md or {}).get("line"),
                "sex": (md or {}).get("sex"),
                "document_type": (md or {}).get("document_type"),
                "table_type": (md or {}).get("table_type"),
                "page": (md or {}).get("page_number"),
            }
        })
    return formatted

def _build_filters_from_entities(entities: Dict[str, Any]) -> Dict[str, Any]:
    filters = {}
    if "species" in entities and entities["species"]:
        filters["species"] = entities["species"]
    if "line" in entities and entities["line"]:
        filters["line"] = entities["line"]
    if "sex" in entities and entities["sex"]:
        filters["sex"] = entities["sex"]
    logger.debug(f"🔍 Filtres RAG construits: {filters}")
    return filters

def _rag_answer(question: str, k: int = 5, entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    retriever = _get_retriever()
    if retriever is None:
        return {
            "text": "Le moteur RAG n'est pas disponible pour le moment.",
            "sources": [],
            "route": "rag_unavailable",
            "meta": {}
        }

    try:
        filters = _build_filters_from_entities(entities or {})
        result = retriever.get_contextual_diagnosis(question, k=k, filters=filters)

        # === NEW: retry sans sex si vide (souvent trop strict)
        if not result and filters and "sex" in filters:
            f2 = dict(filters); f2.pop("sex", None)
            result = retriever.get_contextual_diagnosis(question, k=k, filters=f2)

        if not result:
            return {
                "text": "Aucune information pertinente trouvée dans la base de connaissances.",
                "sources": [],
                "route": "rag_no_results",
                "meta": {"filters_applied": filters}
            }

        text = result.get("answer") or "Résultats trouvés."
        sources = _format_sources(result.get("source_documents", []))
        meta = {
            "embedding_method": result.get("embedding_method"),
            "species_index_used": result.get("species_index_used"),
            "total_results": result.get("total_results"),
            "tried": result.get("tried", []),
            "filters_applied": filters,
        }

        return {
            "text": text,
            "sources": sources,
            "route": "rag_retriever",
            "meta": meta
        }

    except Exception as e:
        logger.error(f"❌ Erreur RAGRetriever: {e}")
        return {
            "text": "Une erreur est survenue lors de la recherche RAG.",
            "sources": [],
            "route": "rag_error",
            "meta": {"error": str(e), "filters_applied": _build_filters_from_entities(entities or {})}
        }

# ===== NETTOYAGE & SYNTHÈSE (code original conservé) =====
def _final_sanitize(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\*\*?source\s*:\s*[^*\n]+(\*\*)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(?(source|src)\s*:\s*[^)\n]+?\)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\w\-\s]+\.(pdf|docx?|xlsx)', '', text, flags=re.IGNORECASE)
    headers_to_remove = [
        r'INTRODUCTION AND .+ CHARACTERISTICS',
        r'INTRODUCTION\s+AND\s+[\w\s]+\s+CHARACTERISTICS',
        r'Cobb\s+MX\s*[\w\s]*',
        r'Ross\s+\d+\s*[\w\s]*(?:Male|Female|Mâle|Femelle)?',
        r'BODY\s+WEIGHT\s+AND\s+FEED\s+CONVERSION',
        r'PERFORMANCE\s+OBJECTIVES',
        r'NUTRITION\s+SPECIFICATIONS?',
        r'MANAGEMENT\s+GUIDE',
        r'BREEDING\s+GUIDE',
        r'PARENT\s+STOCK\s+GUIDE',
    ]
    for pattern in headers_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    table_patterns = [
        r'Age \(days\)\s*Weight \(lb\)\s*Daily Gain[^|]+',
        r'Imperial \(Male\) C500[^|]+',
        r'Age\s+Weight\s+Feed\s+Conversion[^|]+',
        r'\|\s*Age\s*\|\s*Weight\s*\|\s*[^|]+\|',
        r'Days\s+Grams\s+Pounds\s+Feed[^|]+',
        r'Age\s+\(weeks\)\s+Body\s+Weight[^|]+',
        r'\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s*\n',
        r'Week\s+\d+\s+Week\s+\d+\s+Week\s+\d+',
    ]
    for pattern in table_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    technical_phrases = [
        r'should be aware of local legislation[^.]+\.',
        r'Apply your knowledge and judgment[^.]+\.',
        r'Please use the .+ as a reference[^.]+\.',
        r'Consult your veterinarian[^.]+\.',
        r'These are guidelines only[^.]+\.',
        r'Results may vary[^.]+\.',
        r'Contact your technical[^.]+\.',
    ]
    for phrase in technical_phrases:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if len(line) > 10 or line.startswith(('##', '**', '-', '•')):
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines).strip()

def _maybe_synthesize(question: str, context_text: str) -> str:
    try:
        if str(os.getenv("ENABLE_SYNTH_PROMPT", "0")).lower() not in ("1", "true", "yes", "on"):
            return context_text
        try:
            from ..utils.llm import complete
        except ImportError:
            try:
                from ..utils.openai_utils import complete
            except ImportError:
                logger.warning("⚠️ Aucun wrapper LLM trouvé pour la synthèse")
                return context_text
        synthesis_prompt = """Tu es un expert avicole. Synthétise cette information de manière claire et professionnelle.

RÈGLES IMPORTANTES :
- NE JAMAIS mentionner les sources dans ta réponse
- NE JAMAIS inclure de fragments de texte brut des PDFs
- NE JAMAIS copier-coller des tableaux mal formatés
- Utiliser du Markdown (##, ###, -, **)
- Si l'info est incertaine, donne une fourchette et dis-le
- Réponse concise mais complète

Question : {question}

Informations à synthétiser :
{context}

Réponse synthétique :""".format(question=question, context=_final_sanitize(context_text)[:2000])
        synthesized = complete(synthesis_prompt, temperature=0.2)
        return _final_sanitize(synthesized) if synthesized else context_text
    except Exception as e:
        logger.warning(f"⚠️ Erreur lors de la synthèse LLM: {e}")
        return context_text

# ===== Mode hybride (code original conservé) =====
def _generate_general_answer_with_specifics(question: str, entities: Dict[str, Any], intent: Intention, missing_fields: list) -> Dict[str, Any]:
    try:
        age_days = None
        if entities.get("age_days") is not None:
            try: age_days = int(entities["age_days"])
            except Exception: pass
        elif entities.get("age_weeks") is not None:
            try: age_days = int(entities["age_weeks"]) * 7
            except Exception: pass
        defaults = {"species": entities.get("species") or "broiler",
                    "line": entities.get("line") or "ross308",
                    "sex": entities.get("sex") or "mixed",
                    "age_days": age_days}
        species_label = "Poulet de chair (broiler)" if defaults["species"] == "broiler" else "Pondeuse" if defaults["species"] == "layer" else "Poulet"
        line_label = {"ross308": "Ross 308", "cobb500": "Cobb 500"}.get(str(defaults["line"]).lower(), str(defaults["line"]).title() if defaults["line"] else "—")
        sex_map = {"male": "Mâle", "female": "Femelle", "mixed": "Mixte"}
        sex_label = sex_map.get(str(defaults["sex"]).lower(), "Mixte")
        age_label = f"{age_days} jours" if age_days is not None else "l’âge indiqué"
        header = f"Le **poids cible à {age_label}** dépend de la **lignée** et du **sexe**."
        sub = "Pour te donner la valeur précise, j’ai besoin de confirmer ces points :"
        q1 = "• **Espèce** : Poulet de chair (broiler) ?"
        q2 = "• **Lignée** : Ross 308, Cobb 500 ou autre ?"
        q3 = "• **Sexe** : Mâle, Femelle ou Mixte ?"
        defaults_line = f"**Broiler · {line_label} · {sex_label}" + (f" · {age_days} jours**" if age_days is not None else "**")
        cta = f"👉 Si tu veux aller plus vite, je peux répondre avec l’hypothèse par défaut suivante et tu corriges si besoin :\n{defaults_line}. **Tu valides ?**"
        text = "\n".join([header, sub, "", q1, q2, q3, "", cta]).strip()
        quick_replies = {
            "species": ["broiler", "layer", "other"],
            "line": ["ross308", "cobb500", "hubbard", "other"],
            "sex": ["male", "female", "mixed"],
            "one_click": defaults
        }
        return {"text": text, "source": "hybrid_ui", "confidence": 0.9,
                "enriched": True, "suggested_defaults": defaults,
                "quick_replies": quick_replies, "rag_meta": {}, "rag_sources": []}
    except Exception as e:
        logger.error(f"❌ Error generating hybrid UX answer: {e}")
        return {"text": "Je dois confirmer quelques éléments (espèce, lignée, sexe) avant de donner la valeur précise. Souhaites-tu utiliser des valeurs par défaut ?",
                "source": "hybrid_ui_fallback", "confidence": 0.4, "enriched": False}

# === NEW: normalisation douce pour table-first ===
def _slug(s: Optional[str]) -> str:
    return re.sub(r"[-_\s]+", "", (s or "").lower().strip())

def _normalize_entities_soft(entities: Dict[str, Any]) -> Dict[str, Any]:
    species = (entities.get("species") or entities.get("production_type") or "broiler").lower().strip()
    line_raw = entities.get("line") or entities.get("breed") or ""
    line = _slug(line_raw)
    if line in {"cobb-500","cobb_500","cobb 500"}: line = "cobb500"
    if line in {"ross-308","ross_308","ross 308"}: line = "ross308"
    sex_raw = (entities.get("sex") or "").lower().strip()
    sex_map = {
        "m":"male","male":"male","f":"female","female":"female",
        "mixte":"as_hatched","as hatched":"as_hatched","as_hatched":"as_hatched","mixed":"as_hatched"
    }
    sex = sex_map.get(sex_raw) or "as_hatched"
    age_days = entities.get("age_days")
    if age_days is None and entities.get("age_weeks") is not None:
        try: age_days = int(entities["age_weeks"]) * 7
        except Exception: age_days = None
    try: age_days = int(age_days) if age_days is not None else None
    except Exception: age_days = None
    unit = (entities.get("unit") or "metric").lower().strip()
    if unit not in ("metric","imperial"): unit = "metric"
    return {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit}

# === NEW: exact ou nearest (sans modifier perf_store.py) ===
def _perf_lookup_exact_or_nearest(store: "PerfStore", norm: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    debug = {"strategy": "exact_then_nearest", "norm": dict(norm), "nearest_used": False}
    # exact
    if norm.get("age_days") is not None:
        rec = store.get(line=norm["line"], sex=norm["sex"], unit=norm["unit"], age_days=int(norm["age_days"]))
        if rec:
            return rec, debug
    # nearest
    try:
        df = store._load_df(norm["line"])  # type: ignore (accès interne)
        if df is None or "age_days" not in df.columns:
            return None, debug
        df_unit = df[df["unit"].eq(norm["unit"])]
        df_sex = df_unit[df_unit["sex"].eq(norm["sex"])]
        if df_sex.empty and norm["sex"] in ("male","female"):
            df_sex = df_unit[df_unit["sex"].eq("as_hatched")]
        if df_sex.empty:
            return None, debug
        target = int(norm.get("age_days") or 0)
        df_sex = df_sex.copy()
        df_sex["__delta__"] = (df_sex["age_days"] - target).abs()
        row = df_sex.sort_values(["__delta__", "age_days"]).iloc[0].to_dict()
        debug["nearest_used"] = True
        debug["nearest_age_days"] = int(row.get("age_days"))
        debug["delta"] = abs(int(row.get("age_days")) - target)
        rec = {
            "line": row.get("line", norm["line"]),
            "sex": row.get("sex", norm["sex"]),
            "unit": row.get("unit", norm["unit"]),
            "age_days": row.get("age_days", norm.get("age_days")),
            "weight_g": row.get("weight_g"),
            "weight_lb": row.get("weight_lb"),
            "daily_gain_g": row.get("daily_gain_g"),
            "cum_fcr": row.get("cum_fcr"),
            "source_doc": row.get("source_doc"),
            "page": row.get("page"),
        }
        return rec, debug
    except Exception as e:
        logger.info(f"[PerfStore] nearest lookup failed: {e}")
        return None, debug

# ===== Entrée principale (ajouts balisés) =====
def handle(
    session_id: str,
    question: str,
    lang: str = "fr",
    # === NEW: overrides & debug provenant de expert.py ===
    debug: bool = False,
    force_perfstore: bool = False,
    intent_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fonction principale de traitement des questions - VERSION HYBRIDE (RAGRetriever direct + TABLE-FIRST)
    """
    try:
        logger.info(f"🤖 Processing question: {question[:120]}...")

        # Étape 1: Classification
        classification = classify(question)
        logger.debug(f"Classification: {classification}")

        # Étape 2: Normalisation
        classification = normalize(classification)
        intent: Intention = classification["intent"]
        entities = classification["entities"]

        # === NEW: hint manuel (tests console)
        if intent_hint and str(intent_hint).lower().startswith("perf"):
            intent = Intention.PerfTargets

        logger.info(f"Intent: {intent}, Entities: {list(entities.keys())}")

        # Étape 3: Vérification de complétude
        completeness = compute_completeness(intent, entities)
        completeness_score = completeness["completeness_score"]
        missing_fields = completeness["missing_fields"]
        logger.info(f"Completeness score: {completeness_score} | Missing: {missing_fields}")

        # HYBRIDE : si infos manquantes → synthèse courte + clarifications
        if missing_fields and completeness_score < 0.8:
            logger.info("🧭 Mode hybride: synthèse courte + questions de précision")
            general_answer = _generate_general_answer_with_specifics(question, entities, intent, missing_fields)
            return {
                "type": "partial_answer",
                "intent": intent,
                "general_answer": general_answer,
                "completeness_score": completeness_score,
                "missing_fields": missing_fields,
                "follow_up_questions": completeness["follow_up_questions"],
                "route_taken": "hybrid_synthesis_clarification",
                "session_id": session_id
            }

        # Étape 4: Calcul direct si possible
        def _should_compute(i: Intention) -> bool:
            return i in {
                Intention.WaterFeedIntake,
                Intention.EquipmentSizing,
                Intention.VentilationSizing,
                Intention.EnvSetpoints,
                Intention.Economics
            }
        if _should_compute(intent):
            logger.info(f"🧮 Calcul direct pour intent: {intent}")
            result = _compute_answer(intent, entities)
            result["text"] = _final_sanitize(result.get("text", ""))
            return {
                "type": "answer",
                "intent": intent,
                "answer": result,
                "route_taken": "compute",
                "session_id": session_id
            }

        # ===== Étape 4bis: TABLE-FIRST pour PerfTargets =====
        # === NEW: guard RELAXÉ + override + normalisation robuste ===
        if force_perfstore or (intent == Intention.PerfTargets and completeness_score >= 0.6):
            logger.info("📊 Table-first (PerfTargets) avant RAG")
            try:
                norm = _normalize_entities_soft(entities)
                store = _get_perf_store(norm["species"])  # singleton
                rec = None
                dbg = None
                if store and norm.get("age_days") is not None:
                    rec, dbg = _perf_lookup_exact_or_nearest(store, norm)

                if rec:
                    line_label = {"cobb500": "Cobb 500", "ross308": "Ross 308"}.get(str(rec.get("line","")).lower(), str(rec.get("line","")).title() or "Lignée")
                    sex_map = {"male":"Mâle","female":"Femelle","as_hatched":"Mixte","mixed":"Mixte"}
                    sex_label = sex_map.get(str(rec.get("sex","")).lower(), rec.get("sex",""))
                    unit_label = (rec.get("unit") or norm["unit"] or "metric").lower()
                    v_g, v_lb = rec.get("weight_g"), rec.get("weight_lb")
                    if v_g is not None:
                        try: val_txt = f"**{float(v_g):.0f} g**"
                        except Exception: val_txt = f"**{v_g} g**"
                    elif v_lb is not None:
                        try: val_txt = f"**{float(v_lb):.2f} lb**"
                        except Exception: val_txt = f"**{v_lb} lb**"
                    else:
                        val_txt = "**n/a**"
                    age_disp = int(rec.get("age_days") or norm.get("age_days") or 0)
                    text = f"{line_label} · {sex_label} · {age_disp} j : {val_txt} (objectif {unit_label})."
                    source_item = []
                    if rec.get("source_doc"):
                        source_item.append({
                            "name": rec["source_doc"],
                            "meta": {
                                "page": rec.get("page"),
                                "line": rec.get("line"),
                                "sex": rec.get("sex"),
                                "unit": rec.get("unit")
                            }
                        })
                    return {
                        "type": "answer",
                        "intent": Intention.PerfTargets,
                        "answer": {
                            "text": text,
                            "source": "table_lookup",
                            "confidence": 0.98,
                            "sources": source_item,
                            "meta": {
                                "lookup": {
                                    "line": rec.get("line"),
                                    "sex": rec.get("sex"),
                                    "unit": rec.get("unit"),
                                    "age_days": age_disp
                                },
                                "perf_debug": dbg
                            }
                        },
                        "route_taken": "perfstore_hit",
                        "session_id": session_id
                    }
                else:
                    logger.info("📊 PerfStore MISS → fallback RAG")
            except Exception as e:
                logger.warning(f"⚠️ Table-first lookup échoué: {e}")
                # on continue vers RAG

        # Étape 5: RAG complet via RAGRetriever avec filtres (code original)
        logger.info("📚 RAG via RAGRetriever avec filtres")
        rag = _rag_answer(question, k=5, entities=entities)
        rag_text = _final_sanitize(rag.get("text", ""))
        rag_text = _maybe_synthesize(question, rag_text)

        return {
            "type": "answer",
            "intent": intent,
            "answer": {
                "text": rag_text,
                "source": "rag_retriever",
                "confidence": 0.8,
                "sources": rag.get("sources", []),
                "meta": rag.get("meta", {})
            },
            "route_taken": rag.get("route", "rag_retriever"),
            "session_id": session_id
        }

    except Exception as e:
        logger.exception(f"❌ Critical error in handle(): {e}")
        return {
            "type": "error",
            "error": str(e),
            "message": "Une erreur inattendue s'est produite lors du traitement de votre question.",
            "session_id": session_id
        }
