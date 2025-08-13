# -*- coding: utf-8 -*-
"""
Dialogue orchestration - VERSION REFACTORISÉE
- Module principal maintenant plus léger et focalisé sur l'orchestration
- Imports des modules spécialisés pour langue, mémoire et CoT/fallback
- Preserve la compatibilité avec l'API existante
- CORRIGÉ: Toutes les indentations vérifiées et corrigées
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import os
import re
import time

logger = logging.getLogger(__name__)

# ========== IMPORTS CORE MODULES ==========
from ..utils.question_classifier import classify, Intention
from .context_extractor import normalize
from .clarification_manager import compute_completeness
from ..utils import formulas

# ========== IMPORTS MODULES REFACTORISÉS ==========
from .language_processor import (
    detect_question_language,
    finalize_response_with_language,
    get_language_processing_status
)

from .conversation_memory import (
    get_conversation_memory,
    merge_conversation_context,
    should_continue_conversation,
    save_conversation_context,
    clear_conversation_context,
    extract_age_days_from_text,
    get_memory_status
)

from .cot_fallback_processor import (
    should_use_cot_analysis,
    generate_cot_analysis,
    should_use_openai_fallback,
    generate_openai_fallback_response,
    maybe_synthesize,
    generate_clarification_response_advanced,
    get_cot_fallback_status,
    test_cot_fallback_pipeline,
    OPENAI_FALLBACK_AVAILABLE,
    OPENAI_COT_AVAILABLE
)

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

def _rag_answer_with_fallback(question: str, k: int = 5, entities: Optional[Dict[str, Any]] = None, target_language: str = "fr") -> Dict[str, Any]:
    """
    Version améliorée de _rag_answer avec fallback OpenAI et support CoT
    """
    # Essai RAG standard d'abord
    rag_result = _rag_answer(question, k, entities)
    
    # Vérifier si fallback OpenAI nécessaire
    intent = entities.get("_intent") if entities else None
    
    # Check si fallback activé via config
    enable_fallback = str(os.getenv("ENABLE_OPENAI_FALLBACK", "true")).lower() in ("1", "true", "yes", "on")
    if not enable_fallback:
        logger.debug("🚫 Fallback OpenAI désactivé par configuration")
        return rag_result
    
    if should_use_openai_fallback(rag_result, intent):
        logger.info("🤖 Activation fallback OpenAI après échec RAG")
        
        # Tenter fallback OpenAI avec la langue cible (possiblement avec CoT)
        openai_result = generate_openai_fallback_response(
            question=question,
            entities=entities or {},
            intent=intent,
            rag_context=rag_result.get("text", ""),
            target_language=target_language
        )
        
        if openai_result:
            # Succès OpenAI - enrichir avec métadonnées RAG
            openai_result["meta"]["rag_attempted"] = True
            openai_result["meta"]["rag_route"] = rag_result.get("route")
            openai_result["meta"]["rag_meta"] = rag_result.get("meta", {})
            return openai_result
        else:
            logger.warning("⚠️ Fallback OpenAI échoué, retour au RAG original")
    
    return rag_result

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
    text = re.sub(r'^\s+|\s+, '', text, flags=re.MULTILINE)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if len(line) > 10 or line.startswith(('##', '**', '-', '•')):
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines).strip()

# ---------------------------------------------------------------------------
# MODE HYBRIDE AMÉLIORÉ
# ---------------------------------------------------------------------------

def _generate_general_answer_with_specifics(question: str, entities: Dict[str, Any], intent: Intention, missing_fields: list) -> Dict[str, Any]:
    """
    Mode hybride: réponse générale + questions de précision
    """
    try:
        # Essai avec la fonction spécialisée si disponible
        clarification_text = generate_clarification_response_advanced(intent, missing_fields)
        
        # Enrichir avec les boutons rapides
        age_days = None
        if entities.get("age_days") is not None:
            try: 
                age_days = int(entities["age_days"])
            except Exception: 
                pass
        elif entities.get("age_weeks") is not None:
            try: 
                age_days = int(entities["age_weeks"]) * 7
            except Exception: 
                pass
            
        defaults = {
            "species": entities.get("species") or "broiler",
            "line": entities.get("line") or "ross308",
            "sex": entities.get("sex") or "mixed",
            "age_days": age_days
        }
        
        quick_replies = {
            "species": ["broiler", "layer", "other"],
            "line": ["ross308", "cobb500", "hubbard", "other"],
            "sex": ["male", "female", "mixed"],
            "one_click": defaults
        }
        
        return {
            "text": clarification_text, 
            "source": "hybrid_ui", 
            "confidence": 0.9,
            "enriched": True, 
            "suggested_defaults": defaults,
            "quick_replies": quick_replies, 
            "rag_meta": {}, 
            "rag_sources": []
        }
        
    except Exception as e:
        logger.error(f"❌ Error generating hybrid UX answer: {e}")
        return {
            "text": "Je dois confirmer quelques éléments (espèce, lignée, sexe) avant de donner la valeur précise. Souhaites-tu utiliser des valeurs par défaut ?",
            "source": "hybrid_ui_fallback", 
            "confidence": 0.4, 
            "enriched": False
        }

# ---------------------------------------------------------------------------
# FONCTION COMPUTE (PLACEHOLDER)
# ---------------------------------------------------------------------------

def _compute_answer(intent: Intention, entities: Dict[str, Any]) -> Dict[str, Any]:
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

# ---------------------------------------------------------------------------
# FONCTION PRINCIPALE HANDLE - REFACTORISÉE
# ---------------------------------------------------------------------------

def handle(
    session_id: str,
    question: str,
    lang: str = "fr",
    # Overrides & debug
    debug: bool = False,
    force_perfstore: bool = False,
    intent_hint: Optional[str] = None,
    # Entities pass-through depuis l'API
    entities: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fonction principale de traitement des questions - VERSION REFACTORISÉE
    Préserve la compatibilité avec l'API existante
    """
    try:
        logger.info(f"🤖 Processing question: {question[:120]}...")
        logger.info(f"[DM] flags: force_perfstore={force_perfstore}, intent_hint={intent_hint}, has_entities={bool(entities)}")

        # =================================================================
        # DÉTECTION DE LANGUE AUTOMATIQUE
        # =================================================================
        auto_detection_enabled = str(os.getenv("ENABLE_AUTO_LANGUAGE_DETECTION", "true")).lower() in ("1", "true", "yes", "on")
        
        if auto_detection_enabled:
            detected_language = detect_question_language(question)
            logger.info(f"🌍 Langue détectée: {detected_language} | Paramètre lang: {lang}")
            
            # Utiliser la langue détectée si pas spécifiée explicitement ou si détection différente
            if lang == "fr" and detected_language != "fr":
                effective_language = detected_language
                logger.info(f"🔄 Utilisation langue détectée: {effective_language}")
            else:
                effective_language = lang
        else:
            detected_language = lang
            effective_language = lang
            logger.info(f"🌍 Détection automatique désactivée, utilisation lang: {effective_language}")

        # =================================================================
        # RÉCUPÉRATION DU CONTEXTE CONVERSATIONNEL
        # =================================================================
        memory = get_conversation_memory()
        session_context = memory.get(session_id) or {}
        logger.info(f"🧠 Contexte de session: {session_context}")

        # Étape 1: Classification
        classification = classify(question)
        logger.debug(f"Classification: {classification}")

        # Étape 2: Normalisation
        classification = normalize(classification)
        intent: Intention = classification["intent"]

        # Fusion des entities (NER + overrides + contexte conversationnel)
        _ents = dict(classification.get("entities") or {})
        if entities:
            try: 
                _ents.update(entities)
            except Exception: 
                pass
        
        # Vérifier si on continue une conversation
        if should_continue_conversation(session_context, intent):
            logger.info("🔗 Continuation de conversation détectée")
            # Fusionner avec le contexte précédent et enrichir automatiquement
            _ents = merge_conversation_context(_ents, session_context, question)
            # Forcer l'intention vers PerfTargets si c'était en attente
            if session_context.get("pending_intent") == "PerfTargets":
                intent = Intention.PerfTargets
                logger.info("🎯 Intention forcée vers PerfTargets par contexte conversationnel")
        
        entities = _ents

        # Canonicalisation immédiate du sexe pour robustesse NER/PerfStore/RAG
        entities["sex"] = _canon_sex(entities.get("sex")) or entities.get("sex")

        # Hint manuel (tests console)
        if intent_hint and str(intent_hint).lower().startswith("perf"):
            intent = Intention.PerfTargets

        logger.info(f"Intent: {intent}, Entities keys: {list(entities.keys())}")

        # =================================================================
        # VÉRIFICATION PRIORITAIRE POUR ANALYSE COT
        # =================================================================
        if OPENAI_COT_AVAILABLE and should_use_cot_analysis(intent, entities, question):
            logger.info("🧠 Question complexe détectée → Analyse Chain-of-Thought prioritaire")
            
            # Passer l'intent dans les entities pour le context
            entities_with_intent = dict(entities)
            entities_with_intent["_intent"] = intent
            
            # Tentative d'analyse CoT directe
            cot_result = generate_cot_analysis(
                question=question,
                entities=entities,
                intent=intent,
                rag_context="",  # Pas de contexte RAG préalable
                target_language=effective_language
            )
            
            if cot_result:
                logger.info("✅ Analyse CoT réussie, retour direct")
                clear_conversation_context(session_id)
                
                response = {
                    "type": "answer",
                    "intent": intent,
                    "answer": cot_result,
                    "route_taken": "cot_analysis_priority",
                    "session_id": session_id
                }
                
                return finalize_response_with_language(response, question, effective_language, detected_language)
            else:
                logger.info("⚠️ Analyse CoT échouée, continuation pipeline standard")

        # Étape 3: Vérification de complétude
        completeness = compute_completeness(intent, entities)
        completeness_score = completeness["completeness_score"]
        missing_fields = completeness["missing_fields"]
        logger.info(f"Completeness score: {completeness_score} | Missing: {missing_fields}")

        # Si conversation continue et complète maintenant, aller directement au traitement
        if should_continue_conversation(session_context, intent) and completeness_score >= 0.8:
            logger.info("🚀 Conversation continue avec données complètes → traitement direct")
            # Effacer le contexte car on va donner la réponse finale
            clear_conversation_context(session_id)
        # HYBRIDE : si infos manquantes → synthèse courte + clarifications
        elif missing_fields and completeness_score < 0.8:
            logger.info("🧭 Mode hybride: synthèse courte + questions de précision")
            general_answer = _generate_general_answer_with_specifics(question, entities, intent, missing_fields)
            
            # Sauvegarder le contexte pour continuité
            save_conversation_context(session_id, intent, entities, question, missing_fields)
            
            response = {
                "type": "partial_answer",
                "intent": intent,
                "general_answer": general_answer,
                "completeness_score": completeness_score,
                "missing_fields": missing_fields,
                "follow_up_questions": completeness["follow_up_questions"],
                "route_taken": "hybrid_synthesis_clarification",
                "session_id": session_id
            }
            
            # Appliquer adaptation linguistique
            return finalize_response_with_language(response, question, effective_language, detected_language)

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
            
            # Effacer le contexte après réponse finale
            clear_conversation_context(session_id)
            
            response = {
                "type": "answer",
                "intent": intent,
                "answer": result,
                "route_taken": "compute",
                "session_id": session_id
            }
            
            # Appliquer adaptation linguistique
            return finalize_response_with_language(response, question, effective_language, detected_language)

        # Étape 4bis: TABLE-FIRST pour PerfTargets (avant RAG)
        if force_perfstore or (intent == Intention.PerfTargets and completeness_score >= 0.6):
            logger.info("📊 Table-first (PerfTargets) avant RAG")
            try:
                norm = _normalize_entities_soft(entities)
                if norm.get("age_days") is None:
                    age_guess = extract_age_days_from_text(question)
                    if age_guess is not None:
                        norm["age_days"] = age_guess

                store = _get_perf_store(norm["species"])  # singleton
                rec = None
                dbg = None
                if store:
                    rec, dbg = _perf_lookup_exact_or_nearest(store, norm, question=question)

                if rec:
                    line_label = {"cobb500": "Cobb 500", "ross308": "Ross 308"}.get(str(rec.get("line","")).lower(), str(rec.get("line","")).title() or "Lignée")
                    sex_map = {"male":"Mâle","female":"Femelle","as_hatched":"Mixte","mixed":"Mixte"}
                    sex_label = sex_map.get(str(rec.get("sex","")).lower(), rec.get("sex",""))
                    unit_label = (rec.get("unit") or norm["unit"] or "metric").lower()
                    v_g, v_lb = rec.get("weight_g"), rec.get("weight_lb")
                    if v_g is not None:
                        try: 
                            val_txt = f"**{float(v_g):.0f} g**"
                        except Exception: 
                            val_txt = f"**{v_g} g**"
                    elif v_lb is not None:
                        try: 
                            val_txt = f"**{float(v_lb):.2f} lb**"
                        except Exception: 
                            val_txt = f"**{v_lb} lb**"
                    else:
                        val_txt = "**n/a**"
                    age_disp = int(rec.get("age_days") or norm.get("age_days") or 0)
                    text = f"{line_label} · {sex_label} · {age_disp} j : {val_txt} (objectif {unit_label})."
                    source_item: List[Dict[str, Any]] = []
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
                    
                    # Effacer le contexte après réponse finale réussie
                    clear_conversation_context(session_id)
                    
                    response = {
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
                    
                    # Appliquer adaptation linguistique
                    return finalize_response_with_language(response, question, effective_language, detected_language)
                else:
                    logger.info("📊 PerfStore MISS → fallback RAG")
            except Exception as e:
                logger.warning(f"⚠️ Table-first lookup échoué: {e}")
                # on continue vers RAG

        # Étape 5: RAG complet avec fallback OpenAI amélioré
        logger.info("📚 RAG via RAGRetriever avec fallback OpenAI amélioré")
        
        # Passer l'intent dans les entities pour le fallback
        entities_with_intent = dict(entities)
        entities_with_intent["_intent"] = intent
        
        rag = _rag_answer_with_fallback(question, k=5, entities=entities_with_intent, target_language=effective_language)
        rag_text = _final_sanitize(rag.get("text", ""))
        
        # Synthèse uniquement si ce n'est pas déjà un fallback OpenAI ou CoT
        if rag.get("source") not in ["openai_fallback", "cot_analysis"]:
            rag_text = maybe_synthesize(question, rag_text)

        # Effacer le contexte après réponse finale (même si RAG)
        clear_conversation_context(session_id)

        response = {
            "type": "answer",
            "intent": intent,
            "answer": {
                "text": rag_text,
                "source": rag.get("source", "rag_retriever"),
                "confidence": rag.get("confidence", 0.8),
                "sources": rag.get("sources", []),
                "meta": rag.get("meta", {})
            },
            "route_taken": rag.get("route", "rag_retriever"),
            "session_id": session_id
        }
        
        # Appliquer adaptation linguistique
        return finalize_response_with_language(response, question, effective_language, detected_language)

    except Exception as e:
        logger.exception(f"❌ Critical error in handle(): {e}")
        response = {
            "type": "error",
            "error": str(e),
            "message": "Une erreur inattendue s'est produite lors du traitement de votre question.",
            "session_id": session_id
        }
        
        # Même en cas d'erreur, essayer d'adapter la langue si possible
        try:
            detected_language = detect_question_language(question) if question else "fr"
            effective_language = detected_language if detected_language != "fr" else "fr"
            return finalize_response_with_language(response, question or "", effective_language, detected_language)
        except:
            return response

# ---------------------------------------------------------------------------
# FONCTIONS DE STATUT UNIFIÉES
# ---------------------------------------------------------------------------

def get_fallback_status() -> Dict[str, Any]:
    """
    Retourne le statut complet du système avec tous les modules
    """
    # Récupérer les statuts de chaque module
    language_status = get_language_processing_status()
    memory_status = get_memory_status()
    cot_fallback_status = get_cot_fallback_status()
    
    # Statut unifié
    unified_status = {
        "dialogue_manager_version": "refactored",
        "modules": {
            "language_processor": language_status,
            "conversation_memory": memory_status,
            "cot_fallback_processor": cot_fallback_status
        },
        "core_components": {
            "rag_available": RAG_AVAILABLE,
            "perfstore_available": PERF_AVAILABLE,
            "question_classifier_available": True,
            "context_extractor_available": True,
            "clarification_manager_available": True
        },
        "configuration": {
            "rag_index_root": os.environ.get("RAG_INDEX_ROOT", "./rag_index"),
            "database_url": bool(os.getenv("DATABASE_URL")),
            "openai_api_key": bool(os.getenv("OPENAI_API_KEY"))
        }
    }
    
    return unified_status

def get_cot_capabilities() -> Dict[str, Any]:
    """
    Délègue aux capacités CoT du module spécialisé
    """
    if not OPENAI_COT_AVAILABLE:
        return {"cot_available": False, "reason": "cot_fallback_processor module not available"}
    
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
        "complexity_indicators": [
            "problème", "diagnostic", "analyse", "optimiser", "améliorer",
            "stratégie", "multiple", "plusieurs", "complexe", "comparer",
            "évaluer", "recommandation", "pourquoi", "comment résoudre"
        ]
    }

def test_enhanced_pipeline() -> Dict[str, Any]:
    """
    Test complet du pipeline refactorisé
    """
    try:
        results = {}
        
        # Test fonction de base
        results["basic_status"] = {
            "dialogue_manager": "refactored",
            "modules_imported": True,
            "rag_available": RAG_AVAILABLE,
            "perfstore_available": PERF_AVAILABLE
        }
        
        # Test modules spécialisés
        try:
            language_test = get_language_processing_status()
            results["language_processor_test"] = language_test
        except Exception as e:
            results["language_processor_test"] = {"status": "error", "error": str(e)}
        
        try:
            memory_test = get_memory_status()
            results["conversation_memory_test"] = memory_test
        except Exception as e:
            results["conversation_memory_test"] = {"status": "error", "error": str(e)}
        
        try:
            cot_test = test_cot_fallback_pipeline()
            results["cot_fallback_test"] = cot_test
        except Exception as e:
            results["cot_fallback_test"] = {"status": "error", "error": str(e)}
        
        return {
            "status": "success",
            "message": "Pipeline refactorisé testé avec succès",
            "detailed_results": results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Échec test pipeline refactorisé: {str(e)}",
            "error_type": type(e).__name__
        }