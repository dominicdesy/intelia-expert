# -*- coding: utf-8 -*-
"""
Dialogue orchestration - VERSION HYBRIDE (RAGRetriever direct + TABLE-FIRST)
- classify -> normalize -> completeness/clarifications
- Réponse générale + clarifications pour questions incomplètes
- Route vers compute (si possible) OU vers table-first (perf targets) OU vers RAGRetriever (multi-index)
- Retourne un payload structuré pour le frontend
"""
from typing import Dict, Any, List, Optional
import logging
import os
import re

logger = logging.getLogger(__name__)

# ========== IMPORTS AVEC FALLBACKS ==========
from ..utils.question_classifier import classify, Intention
from .context_extractor import normalize
from .clarification_manager import compute_completeness
from ..utils import formulas

# ===== Import robuste du RAGRetriever =====
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
    # lit rag_index/<species>/tables/<line>*.csv via manifest généré par build_rag
    from .perf_store import PerfStore  # type: ignore
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
    species_hint: 'broiler' | 'layer' | 'global' ... (déduit des entités sinon)
    """
    if not PERF_AVAILABLE or PerfStore is None:
        return None
    global _PERF_STORE
    species = (species_hint or "broiler").strip().lower()
    # si singleton déjà créé mais pour une autre espèce, on réinstancie
    if _PERF_STORE is None or getattr(_PERF_STORE, "species", "") != species:
        try:
            root = os.environ.get("RAG_INDEX_ROOT", "./rag_index")
            _PERF_STORE = PerfStore(root=root, species=species)  # type: ignore
            logger.info(f"📊 PerfStore initialisé (root={root}, species={species})")
        except Exception as e:
            logger.warning(f"⚠️ PerfStore indisponible: {e}")
            _PERF_STORE = None
    return _PERF_STORE

# ===== Utilitaires RAG =====
def _format_sources(source_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compacte les infos sources (nom lisible + méta utiles).
    """
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
    """
    Construit un dict de filtres pour le RAGRetriever à partir des entités détectées.
    """
    filters = {}
    if "species" in entities and entities["species"]:
        filters["species"] = entities["species"]
    if "line" in entities and entities["line"]:
        filters["line"] = entities["line"]
    if "sex" in entities and entities["sex"]:
        filters["sex"] = entities["sex"]
    # Age éventuellement exploitable plus tard (tranches)
    logger.debug(f"🔍 Filtres RAG construits: {filters}")
    return filters

def _rag_answer(question: str, k: int = 5, entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Appelle le RAGRetriever avec filtres et retourne un dict standardisé:
    { text, sources[], route, meta }
    """
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
        # 1er essai avec filtres complets
        result = retriever.get_contextual_diagnosis(question, k=k, filters=filters)

        # NEW: si rien, on retente sans filtre 'sex' (souvent trop strict)
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

# ===== Règles compute =====
def _should_compute(intent: Intention) -> bool:
    return intent in {
        Intention.WaterFeedIntake,
        Intention.EquipmentSizing,
        Intention.VentilationSizing,
        Intention.EnvSetpoints,
        Intention.Economics
    }

def _compute_answer(intent: Intention, entities: Dict[str, Any]) -> Dict[str, Any]:
    ans = {"text": "", "values": {}}
    try:
        if intent == Intention.WaterFeedIntake:
            eff = entities.get("flock_size") or 1000
            age = entities.get("age_days") or (entities.get("age_weeks", 0) * 7)
            ans["values"]["water_L_per_day"] = formulas.conso_eau_j(eff, age or 0, 20.0)
            ans["text"] = "Estimation de la consommation d'eau quotidienne (flock)."
        elif intent == Intention.EquipmentSizing:
            eff = entities.get("flock_size") or 1000
            age = entities.get("age_days") or (entities.get("age_weeks", 0) * 7)
            ans["values"]["feeder_space_cm"] = formulas.dimension_mangeoires(eff, age or 0, 'chaîne')
            ans["values"]["drinkers"] = formulas.dimension_abreuvoirs(eff, age or 0, 'nipple')
            ans["text"] = "Dimensionnement mangeoires/abreuvoirs (ordre de grandeur)."
        elif intent == Intention.VentilationSizing:
            eff = entities.get("flock_size") or 1000
            age = entities.get("age_days") or (entities.get("age_weeks", 0) * 7)
            poids_moy = entities.get("avg_weight_kg") or 1.5
            saison = entities.get("season") or "hiver"
            ans["values"]["vent_min_m3h_per_kg"] = formulas.vent_min_m3h_par_kg(age or 0, saison)
            ans["values"]["vent_min_total_m3h"] = formulas.vent_min_total_m3h(poids_moy, eff, age or 0, saison)
            ans["text"] = "Ventilation minimale recommandée (m³/h)."
        elif intent == Intention.EnvSetpoints:
            age = entities.get("age_days") or (entities.get("age_weeks", 0) * 7)
            ans["values"]["temp_C"] = formulas.setpoint_temp_C_broiler(age or 0)
            ans["values"]["rh_pct"] = formulas.setpoint_hr_pct(age or 0)
            ans["values"]["co2_max_ppm"] = formulas.co2_max_ppm()
            ans["values"]["nh3_max_ppm"] = formulas.nh3_max_ppm()
            ans["values"]["lux"] = formulas.lux_program_broiler(age or 0)
            ans["text"] = "Consignes environnementales génériques."
        elif intent == Intention.Economics:
            eff = entities.get("flock_size") or 1000
            prix = entities.get("feed_price") or 450.0
            fcr = entities.get("FCR") or 1.7
            poids = entities.get("target_weight") or 2.2
            ans["values"]["feed_cost_total"] = formulas.cout_total_aliment(eff, poids, fcr, prix, 95.0)
            ans["values"]["feed_cost_per_kg"] = formulas.cout_aliment_par_kg_vif(prix, fcr)
            ans["text"] = "Estimation des coûts d'aliment."
        else:
            ans["text"] = "Calcul effectué."
    except Exception as e:
        logger.error(f"❌ Error in _compute_answer: {e}")
        ans["text"] = f"Erreur dans le calcul pour {intent}"
        ans["error"] = str(e)
    return ans

# ===== NETTOYAGE RENFORCÉ =====
def _final_sanitize(text: str) -> str:
    """
    Sanitisation renforcée pour éliminer les fragments indésirables des PDFs.
    """
    if not text:
        return ""
    
    # 1) Enlever toute mention de sources explicites
    text = re.sub(r'\*\*?source\s*:\s*[^*\n]+(\*\*)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(?(source|src)\s*:\s*[^)\n]+?\)?', '', text, flags=re.IGNORECASE)
    
    # 2) Enlever noms de fichiers PDF/documents
    text = re.sub(r'[\w\-\s]+\.(pdf|docx?|xlsx)', '', text, flags=re.IGNORECASE)
    
    # 3) Patterns d'en-têtes à supprimer (étendus)
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
    
    # 4) Tableaux mal formatés (patterns étendus)
    table_patterns = [
        r'Age \(days\)\s*Weight \(lb\)\s*Daily Gain[^|]+',
        r'Imperial \(Male\) C500[^|]+',
        r'Age\s+Weight\s+Feed\s+Conversion[^|]+',
        r'\|\s*Age\s*\|\s*Weight\s*\|\s*[^|]+\|',
        r'Days\s+Grams\s+Pounds\s+Feed[^|]+',
        r'Age\s+\(weeks\)\s+Body\s+Weight[^|]+',
        # Patterns de tableaux avec colonnes mal alignées
        r'\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s*\n',
        r'Week\s+\d+\s+Week\s+\d+\s+Week\s+\d+',
    ]
    
    for pattern in table_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # 5) Phrases techniques récurrentes à filtrer
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
    
    # 6) Nettoyage des espaces et formatage
    text = re.sub(r'[ \t]+', ' ', text)  # Multiples espaces
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiples retours ligne
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)  # Espaces début/fin de ligne
    
    # 7) Suppression des lignes très courtes (probablement des fragments)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if len(line) > 10 or line.startswith(('##', '**', '-', '•')):  # Garder le markdown
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()

# ===== WRAPPER LLM =====
def _maybe_synthesize(question: str, context_text: str) -> str:
    """
    Si ENABLE_SYNTH_PROMPT=1, tente d'appeler un wrapper LLM interne.
    En cas d'échec ou si non configuré, retourne le texte tel quel (no-op).
    """
    try:
        if str(os.getenv("ENABLE_SYNTH_PROMPT", "0")).lower() not in ("1", "true", "yes", "on"):
            return context_text
            
        # Import paresseux du wrapper LLM
        try:
            from ..utils.llm import complete  # Nouveau wrapper standardisé
        except ImportError:
            try:
                from ..utils.openai_utils import complete  # Fallback
            except ImportError:
                logger.warning("⚠️ Aucun wrapper LLM trouvé pour la synthèse")
                return context_text
        
        # Prompt de synthèse optimisé
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

# ===== MODE HYBRIDE AMÉLIORÉ =====
def _generate_general_answer_with_specifics(question: str, entities: Dict[str, Any], intent: Intention, missing_fields: list) -> Dict[str, Any]:
    """
    Mode hybride UX-first : message court + questions ciblées + defaults + quick replies.
    Ne concatène aucun texte RAG. Pas de dépendance au wrapper LLM.
    """
    try:
        # 1) Normaliser l'âge en jours
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

        # 2) Defaults intelligents (modifiables)
        defaults = {
            "species": entities.get("species") or "broiler",
            "line": entities.get("line") or "ross308",
            "sex": entities.get("sex") or "mixed",
            "age_days": age_days,
        }

        # 3) Libellés conviviaux
        species_label = "Poulet de chair (broiler)" if defaults["species"] == "broiler" else "Pondeuse" if defaults["species"] == "layer" else "Poulet"
        line_label = {"ross308": "Ross 308", "cobb500": "Cobb 500"}.get(str(defaults["line"]).lower(), str(defaults["line"]).title() if defaults["line"] else "—")
        sex_map = {"male": "Mâle", "female": "Femelle", "mixed": "Mixte"}
        sex_label = sex_map.get(str(defaults["sex"]).lower(), "Mixte")
        age_label = f"{age_days} jours" if age_days is not None else "l’âge indiqué"

        # 4) Message EXACT demandé
        header = f"Le **poids cible à {age_label}** dépend de la **lignée** et du **sexe**."
        sub = "Pour te donner la valeur précise, j’ai besoin de confirmer ces points :"
        q1 = "• **Espèce** : Poulet de chair (broiler) ?"
        q2 = "• **Lignée** : Ross 308, Cobb 500 ou autre ?"
        q3 = "• **Sexe** : Mâle, Femelle ou Mixte ?"
        defaults_line = f"**Broiler · {line_label} · {sex_label}" + (f" · {age_days} jours**" if age_days is not None else "**")
        cta = f"👉 Si tu veux aller plus vite, je peux répondre avec l’hypothèse par défaut suivante et tu corriges si besoin :\n{defaults_line}. **Tu valides ?**"
        text = "\n".join([header, sub, "", q1, q2, q3, "", cta]).strip()

        # 5) Quick replies pour le frontend
        quick_replies = {
            "species": ["broiler", "layer", "other"],
            "line": ["ross308", "cobb500", "hubbard", "other"],
            "sex": ["male", "female", "mixed"],
            "one_click": {
                "species": defaults["species"],
                "line": defaults["line"],
                "sex": defaults["sex"],
                "age_days": defaults["age_days"],
            }
        }

        return {
            "text": text,
            "source": "hybrid_ui",
            "confidence": 0.9,
            "enriched": True,
            "suggested_defaults": defaults,
            "quick_replies": quick_replies,
            "rag_meta": {},          # volontairement vide (pas de concat RAG)
            "rag_sources": []        # aucune source en mode clarification
        }

    except Exception as e:
        logger.error(f"❌ Error generating hybrid UX answer: {e}")
        return {
            "text": "Je dois confirmer quelques éléments (espèce, lignée, sexe) avant de donner la valeur précise. Souhaites-tu utiliser des valeurs par défaut ?",
            "source": "hybrid_ui_fallback",
            "confidence": 0.4,
            "enriched": False
        }


# ===== Entrée principale =====
def handle(session_id: str, question: str, lang: str="fr") -> Dict[str, Any]:
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
        if intent == Intention.PerfTargets and completeness_score >= 0.8:
            logger.info("📊 Table-first (PerfTargets) avant RAG")
            try:
                # species → choisit le bon sous-dossier de rag_index
                species_hint = (entities.get("species") or entities.get("production_type") or "broiler")
                store = _get_perf_store(species_hint)

                # Normalisations / défauts
                age_days = entities.get("age_days")
                if age_days is None and entities.get("age_weeks") is not None:
                    try:
                        age_days = int(entities.get("age_weeks")) * 7
                    except Exception:
                        age_days = None

                unit = (entities.get("unit") or "metric")
                line = (entities.get("line") or "cobb500")
                sex  = (entities.get("sex") or "as_hatched")

                rec = None
                if store and age_days is not None:
                    rec = store.get(line=line, sex=sex, unit=unit, age_days=int(age_days))

                if rec:
                    # Libellés conviviaux + rendu court
                    line_label = {"cobb500": "Cobb 500", "ross308": "Ross 308"}.get(str(rec.get("line","")).lower(), str(rec.get("line","")).title() or "Lignée")
                    sex_map = {"male":"Mâle","female":"Femelle","as_hatched":"As Hatched","mixed":"Mixte"}
                    sex_label = sex_map.get(str(rec.get("sex","")).lower(), rec.get("sex",""))
                    unit_label = (rec.get("unit") or unit or "metric").lower()
                    v_g = rec.get("weight_g")
                    v_lb = rec.get("weight_lb")
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

                    text = f"{line_label} · {sex_label} · {int(rec.get('age_days', age_days))} j : {val_txt} (objectif {unit_label})."

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
                        "intent": intent,
                        "answer": {
                            "text": text,
                            "source": "table_lookup",
                            "confidence": 0.98,
                            "sources": source_item,
                            "meta": {"lookup": {
                                "line": rec.get("line") or line,
                                "sex": rec.get("sex") or sex,
                                "unit": rec.get("unit") or unit_label,
                                "age_days": rec.get("age_days") or int(age_days)
                            }}
                        },
                        "route_taken": "table_lookup",
                        "session_id": session_id
                    }
            except Exception as e:
                logger.warning(f"⚠️ Table-first lookup échoué: {e}")
                # on continue vers RAG

        # Étape 5: RAG complet via RAGRetriever avec filtres
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
