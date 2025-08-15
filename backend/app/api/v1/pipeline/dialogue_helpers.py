# -*- coding: utf-8 -*-
"""
Dialogue Helpers - Fonctions utilitaires pour dialogue_manager
Contient: PerfStore, RAG, normalisation et helpers divers
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import os
import re

logger = logging.getLogger(__name__)

# ========== PERF STORE & RAG - CODE ORIGINAL CONSERVÉ ==========
try:
    from .perf_store import PerfStore
    PERF_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ PerfStore indisponible: {e}")
    PerfStore = None
    PERF_AVAILABLE = False

try:
    from rag.retriever import RAGRetriever as _RAGRetrieverImported
    RAGRetrieverCls = _RAGRetrieverImported
    RAG_AVAILABLE = True
    logger.info("✅ RAGRetriever importé depuis rag.retriever")
except Exception as e1:
    try:
        from .rag.retriever import RAGRetriever as _RAGRetrieverImported2
        RAGRetrieverCls = _RAGRetrieverImported2
        RAG_AVAILABLE = True
        logger.info("✅ RAGRetriever importé depuis .rag.retriever")
    except Exception as e2:
        try:
            from .retriever import RAGRetriever as _RAGRetrieverImported3
            RAGRetrieverCls = _RAGRetrieverImported3
            RAG_AVAILABLE = True
            logger.info("✅ RAGRetriever importé depuis .retriever")
        except Exception as e3:
            logger.warning(f"⚠️ Impossible d'importer RAGRetriever ({e1} | {e2} | {e3}). RAG désactivé.")
            RAG_AVAILABLE = False
            RAGRetrieverCls = None

# Singletons
_PERF_STORE: Optional["PerfStore"] = None
_RAG_SINGLETON = None

# ---------------------------------------------------------------------------
# HELPERS PERFSTORE - CODE ORIGINAL CONSERVÉ
# ---------------------------------------------------------------------------

def _canon_sex(s: Optional[str]) -> Optional[str]:
    """Canonisation tolérante du sexe pour NER/PerfStore/RAG"""
    if not s:
        return None
    s = str(s).strip().lower()
    return {
        "as hatched": "as_hatched",
        "as-hatched": "as_hatched", 
        "as_hatched": "as_hatched",
        "ah": "as_hatched",
        "mixte": "as_hatched",
        "mixed": "as_hatched",
        "male": "male", "m": "male", "♂": "male",
        "female": "female", "f": "female", "♀": "female",
    }.get(s, s)

def _slug(s: Optional[str]) -> str:
    return re.sub(r"[-_\s]+", "", (s or "").lower().strip())

def _normalize_entities_soft(entities: Dict[str, Any]) -> Dict[str, Any]:
    """Normalisation des entités pour PerfStore"""
    species = (entities.get("species") or entities.get("production_type") or "broiler").lower().strip()
    line_raw = entities.get("line") or entities.get("breed") or ""
    line = _slug(line_raw)
    if line in {"cobb-500","cobb_500","cobb 500"}: 
        line = "cobb500"
    if line in {"ross-308","ross_308","ross 308"}: 
        line = "ross308"

    sex_raw = (entities.get("sex") or "").lower().strip()
    sex_map = {
        "m":"male","male":"male","f":"female","female":"female",
        "mixte":"as_hatched","as hatched":"as_hatched","as_hatched":"as_hatched","mixed":"as_hatched"
    }
    sex = sex_map.get(sex_raw) or "as_hatched"
    sex = _canon_sex(sex) or sex

    age_days = entities.get("age_days")
    if age_days is None and entities.get("age_weeks") is not None:
        try: 
            age_days = int(entities["age_weeks"]) * 7
        except Exception: 
            age_days = None
    try: 
        age_days = int(age_days) if age_days is not None else None
    except Exception: 
        age_days = None

    unit = (entities.get("unit") or "metric").lower().strip()
    if unit not in ("metric","imperial"): 
        unit = "metric"

    return {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit}

def _get_perf_store(species_hint: Optional[str] = None) -> Optional["PerfStore"]:
    """Instancie un PerfStore pointant vers ./rag_index/<species>/tables/."""
    if not PERF_AVAILABLE or PerfStore is None:
        return None
    global _PERF_STORE
    species = (species_hint or "broiler").strip().lower()
    if _PERF_STORE is None or getattr(_PERF_STORE, "species", "") != species:
        try:
            root = os.environ.get("RAG_INDEX_ROOT", "./rag_index")
            _PERF_STORE = PerfStore(root=root, species=species)
            logger.info(f"📊 PerfStore initialisé (root={root}, species={species})")
        except Exception as e:
            logger.warning(f"⚠️ PerfStore indisponible: {e}")
            _PERF_STORE = None
    return _PERF_STORE

def _perf_lookup_exact_or_nearest(store: "PerfStore", norm: Dict[str, Any], question: str = "") -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Essaie un match exact (line, unit, sex, age_days) puis nearest sur l'âge.
    Retourne (record, debug).
    """
    debug: Dict[str, Any] = {}
    try:
        # Récup du DataFrame
        df = getattr(store, "as_dataframe", None)
        df = df() if callable(df) else getattr(store, "df", None)

        if df is None:
            # Fallback per-line si pas de DF global
            _load_df = getattr(store, "_load_df", None)
            if callable(_load_df):
                try:
                    df = _load_df(norm.get("line"))
                    debug["used_per_line_table"] = True
                except Exception as e:
                    debug["load_df_error"] = str(e)
            
            if df is None:
                return None, {"reason": "no_dataframe", "hint": "per-line table missing", "line": norm.get("line")}

        # Harmonisation colonnes minimales (unit/line)
        if "unit" in df.columns:
            df["unit"] = (
                df["unit"].astype(str).str.lower().str.replace(r"[^a-z]+", "", regex=True)
                .replace({
                    "metrics": "metric", "gram": "metric", "grams": "metric", "g": "metric",
                    "imperial": "imperial", "lb": "imperial", "lbs": "imperial"
                })
            )

        if "line" in df.columns:
            df["line"] = (
                df["line"].astype(str).str.lower().str.replace(r"[-_\s]+", "", regex=True)
                .replace({
                    "cobb-500": "cobb500", "cobb_500": "cobb500", "cobb 500": "cobb500",
                    "ross-308": "ross308", "ross_308": "ross308", "ross 308": "ross308"
                })
            )

        # Harmonisation de la colonne d'âge → age_days
        try:
            lower_map = {str(c).lower(): c for c in df.columns}
            possible = ["age_days", "day", "days", "age", "age(d)", "age_d", "age_days(d)", "age (days)", "jours"]
            found_key = next((lower_map[k] for k in possible if k in lower_map), None)

            if found_key and found_key != "age_days":
                tmp = df[found_key].astype(str).str.extract(r"(\d+)")[0]
                df["age_days"] = tmp.fillna("0").astype(int)
                debug["age_col_harmonized_from"] = str(found_key)
            elif not found_key:
                df["age_days"] = 0
                debug["age_col_harmonized_from"] = None
        except Exception as e:
            debug["age_harmonize_error"] = str(e)
            if "age_days" not in df.columns:
                df["age_days"] = 0

        # Normalisation tolérante de la colonne "sex"
        ds = df
        if "sex" in df.columns:
            _sex_norm = (
                df["sex"].astype(str).str.strip().str.lower()
                .map({
                    "as hatched": "as_hatched", "as-hatched": "as_hatched", "as_hatched": "as_hatched", "ah": "as_hatched",
                    "mixte": "as_hatched", "mixed": "as_hatched",
                    "male": "male", "m": "male", "♂": "male",
                    "female": "female", "f": "female", "♀": "female",
                })
            )
            df["sex"] = _sex_norm.fillna(df["sex"].astype(str).str.strip().str.lower())

        # Filtrage par line / unit / sex (+ fallback sex)
        if "line" in df.columns:
            df = df[df["line"].eq(norm["line"])]
        if "unit" in df.columns:
            df = df[df["unit"].eq(norm["unit"])]

        ds = df
        if "sex" in df.columns:
            ds = df[df["sex"].eq(norm["sex"])]
            if ds.empty and norm["sex"] in ("male", "female"):
                ds = df[df["sex"].eq("as_hatched")]

        if ds is None or len(ds) == 0:
            debug["post_filter_rows"] = 0
            return None, debug
        debug["post_filter_rows"] = int(len(ds))

        # Exact age match
        if norm.get("age_days") is not None and "age_days" in ds.columns:
            try:
                t = int(norm["age_days"])
                ex = ds[ds["age_days"].astype(int) == t]
                if not ex.empty:
                    row = ex.iloc[0].to_dict()
                    debug["nearest_used"] = False
                    return {
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
                    }, debug
            except Exception:
                pass

        # Nearest sur l'âge
        try:
            t = int(norm.get("age_days") or 0)
            ds = ds.copy()
            ds["__d__"] = (ds["age_days"].astype(int) - t).abs()
            row = ds.sort_values(["__d__", "age_days"]).iloc[0].to_dict()
            debug["nearest_used"] = (int(row.get("age_days", -1)) != t)
            debug["nearest_age_days"] = int(row.get("age_days", 0))
            debug["delta"] = abs(int(row.get("age_days", 0)) - t)
            return {
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
            }, debug
        except Exception as e:
            logger.info(f"[PerfStore] nearest lookup failed: {e}")
            debug["nearest_error"] = str(e)
            return None, debug

    except Exception as e:
        return None, {"reason": f"lookup_error: {e}"}

# ---------------------------------------------------------------------------
# RAG RETRIEVER - CODE ORIGINAL CONSERVÉ
# ---------------------------------------------------------------------------

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

        # Retry sans sex si vide (souvent trop strict)
        if not result and filters and "sex" in filters:
            f2 = dict(filters)
            f2.pop("sex", None)
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

# ---------------------------------------------------------------------------
# NETTOYAGE & SYNTHÈSE
# ---------------------------------------------------------------------------

def _final_sanitize(text: str) -> str:
    """Nettoyage final du texte de réponse"""
    if not text:
        return ""
    text = re.sub(r'\*\*?source\s*:\s*[^*\n]+(\*\*)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(?(source|src)\s*:\s*[^)\n]+?\)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\w\-\s]+\.\s*(All rights reserved|Confidential)[^.\n]*\.', '', text, flags=re.IGNORECASE)
    technical_phrases = [
        r'\bFigure\s+\d+[:.]',
        r'\bTable\s+\d+[:.]',
        r'\b(For more information|See also)[^.\n]+\.',
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

def _compute_answer(intent, entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder pour les calculs directs (WaterFeedIntake, EquipmentSizing, etc.)
    Cette fonction doit être implémentée selon vos besoins spécifiques.
    """
    logger.warning(f"⚠️ _compute_answer not implemented for intent: {intent}")
    return {
        "text": f"Calcul pour {intent} non encore implémenté.",
        "source": "compute_placeholder",
        "confidence": 0.1
    }