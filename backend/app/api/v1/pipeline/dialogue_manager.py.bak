# -*- coding: utf-8 -*-
"""
Dialogue orchestration - VERSION HYBRIDE (RAGRetriever direct)
- classify -> normalize -> completeness/clarifications
- Réponse générale + clarifications pour questions incomplètes
- Route vers compute (si possible) OU vers RAGRetriever (table-first, multi-index)
- Retourne un payload structuré pour le frontend
"""
from typing import Dict, Any, List, Optional
import logging
import os
# >>> AJOUT
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
    # chemin "classique" si le package top-level s'appelle rag
    from rag.retriever import RAGRetriever as _RAGRetrieverImported
    RAGRetrieverCls = _RAGRetrieverImported
    RAG_AVAILABLE = True
    logger.info("✅ RAGRetriever importé depuis rag.retriever")
except Exception as e1:
    try:
        # selon la disposition des dossiers, on tente en relatif
        from ...rag.retriever import RAGRetriever as _RAGRetrieverImported2  # type: ignore
        RAGRetrieverCls = _RAGRetrieverImported2
        RAG_AVAILABLE = True
        logger.info("✅ RAGRetriever importé depuis ...rag.retriever")
    except Exception as e2:
        try:
            # dernier essai: import local voisin (si lancé depuis rag/)
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
                "document_type": (md or {}).get("document_type"),
                "table_type": (md or {}).get("table_type"),
                "page": (md or {}).get("page_number"),
            }
        })
    return formatted

def _rag_answer(question: str, k: int = 5) -> Dict[str, Any]:
    """
    Appelle le RAGRetriever et retourne un dict standardisé:
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
        result = retriever.get_contextual_diagnosis(question, k=k)
        if not result:
            return {
                "text": "Aucune information pertinente trouvée dans la base de connaissances.",
                "sources": [],
                "route": "rag_no_results",
                "meta": {}
            }
        text = result.get("answer") or "Résultats trouvés."
        sources = _format_sources(result.get("source_documents", []))
        meta = {
            "embedding_method": result.get("embedding_method"),
            "species_index_used": result.get("species_index_used"),
            "total_results": result.get("total_results"),
            "tried": result.get("tried", []),
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
            "meta": {"error": str(e)}
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

# ===== AJOUT #1 : Sanitizer final minimaliste =====
def _final_sanitize(text: str) -> str:
    if not text:
        return ""
    # 1) enlever toute mention de sources explicites
    text = re.sub(r'\*\*?source\s*:\s*[^*\n]+(\*\*)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(?(source|src)\s*:\s*[^)\n]+?\)?', '', text, flags=re.IGNORECASE)
    # 2) enlever noms de fichiers PDF probables
    text = re.sub(r'[\w\-\s]+\.(pdf|docx?|xlsx)', '', text, flags=re.IGNORECASE)
    # 3) patterns techniques fréquents à filtrer
    for pat in [
        r'ould be aware of local legislation[^.]+\.',
        r'Apply your knowledge and judgment[^.]+\.',
        r'Please use the .+ as a reference[^.]+\.',
        r'INTRODUCTION AND .+ CHARACTERISTICS',
        r'Age \(days\)\s*Weight \(lb\)\s*Daily Gain[^|]+',
        r'Imperial \(Male\) C500[^|]+',
    ]:
        text = re.sub(pat, '', text, flags=re.IGNORECASE)
    # 4) espaces propres
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

# ===== AJOUT #2 : Prompt de synthèse optionnel (no-op par défaut)
IMPROVED_SYNTHESIS_PROMPT = """
Tu es un expert avicole. Réponds de manière claire et synthétique.

RÈGLES IMPORTANTES :
- NE JAMAIS mentionner les sources dans ta réponse
- NE JAMAIS inclure de fragments de texte brut des PDFs
- NE JAMAIS copier-coller des tableaux mal formatés
- Utiliser du Markdown (##, ###, -, **)
- Si l'info est incertaine, donne une fourchette et dis-le.

Exemple de bonne réponse :
## Poids idéal Ross 308 mâle à 17 jours
**Objectifs :**
- Ross 308 mâle : 450-500 g
**Facteurs clés :**
- Alimentation 22–23% protéines; Température 24–26°C
**Surveillance :**
- Pesées hebdo, viser CV < 10%

Contexte (extraits nettoyés) :
{context}

Question :
{question}

Réponse synthétique :
""".strip()

def _maybe_synthesize(question: str, context_text: str) -> str:
    """
    Si ENABLE_SYNTH_PROMPT=1, tente d'appeler un client LLM interne (facultatif).
    En cas d'échec ou si non configuré, retourne le texte tel quel (no-op).
    """
    try:
        if str(os.getenv("ENABLE_SYNTH_PROMPT", "0")).lower() not in ("1", "true", "yes", "on"):
            return context_text
        # Import paresseux pour ne rien casser si le module n'existe pas
        from app.api.v1.utils import llm  # attendu: llm.complete(prompt, temperature=0.2) -> str
        cleaned_ctx = _final_sanitize((context_text or ""))[:2000]
        prompt = IMPROVED_SYNTHESIS_PROMPT.format(context=cleaned_ctx, question=question or "")
        out = llm.complete(prompt, temperature=0.2)
        return _final_sanitize(out or context_text) or context_text
    except Exception as _:
        # Sécurité maximale: ne rien casser si le LLM n'est pas dispo
        return context_text

# ===== Hybride : réponse générale + clarifications =====
def _generate_general_answer_with_specifics(question: str, entities: Dict[str, Any], intent: Intention, missing_fields: list) -> Dict[str, Any]:
    """
    Génère une réponse générale via RAGRetriever + ajoute des précisions selon l'intention.
    """
    try:
        rag = _rag_answer(question, k=5)
        base_text = rag.get("text", "")

        # Exemples de petites enrichissements thématiques
        qlower = question.lower()
        if intent == Intention.PerfTargets and ("poids" in qlower or "weight" in qlower):
            age_detected = entities.get("age_days") or (entities.get("age_weeks", 0) * 7) or 14
            specific_examples = f"""

**Repères typiques à ~{age_detected} jours (ordre de grandeur):**
• Ross 308 mâle: ~400–450 g  • femelle: ~350–400 g
• Cobb 500 mâle: ~420–470 g  • femelle: ~370–420 g
*À confirmer selon programme alimentaire et conditions.*
"""
            enhanced_text = base_text + specific_examples
        elif intent == Intention.WaterFeedIntake:
            enhanced_text = base_text + "\n\n**Facteurs clés :** température ambiante, type d'abreuvoirs, qualité de l'eau, état sanitaire."
        elif intent == Intention.NutritionSpecs:
            enhanced_text = base_text + "\n\n**Variables :** phase (starter/grower/finisher), objectifs de performance, climat."
        else:
            enhanced_text = base_text

        # >>> AJOUT : Sanitize + (optionnel) synthèse
        enhanced_text = _final_sanitize(enhanced_text)
        enhanced_text = _maybe_synthesize(question, enhanced_text)

        return {
            "text": enhanced_text,
            "source": "rag_retriever",
            "confidence": 0.7,
            "enriched": True,
            "rag_meta": rag.get("meta", {}),
            "rag_sources": rag.get("sources", [])
        }
    except Exception as e:
        logger.error(f"❌ Error generating general answer: {e}")
        return {
            "text": f"Voici des informations générales sur {intent}. Pour une réponse précise, merci de compléter les détails demandés.",
            "source": "fallback",
            "confidence": 0.5,
            "enriched": False
        }

# ===== Entrée principale =====
def handle(session_id: str, question: str, lang: str="fr") -> Dict[str, Any]:
    """
    Fonction principale de traitement des questions - VERSION HYBRIDE (RAGRetriever direct)
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

        # HYBRIDE : si infos manquantes → réponse générale + clarifications
        if missing_fields and completeness_score < 0.8:
            logger.info("🧭 Mode hybride: réponse générale + questions de précision")
            general_answer = _generate_general_answer_with_specifics(question, entities, intent, missing_fields)
            return {
                "type": "partial_answer",
                "intent": intent,
                "general_answer": general_answer,
                "completeness_score": completeness_score,
                "missing_fields": missing_fields,
                "follow_up_questions": completeness["follow_up_questions"],
                "route_taken": "hybrid_rag_clarification",
                "session_id": session_id
            }

        # Étape 4: Calcul direct si possible
        if _should_compute(intent):
            logger.info(f"🧮 Calcul direct pour intent: {intent}")
            result = _compute_answer(intent, entities)
            # >>> AJOUT : sanitize final sur texte de calcul (par sûreté)
            result["text"] = _final_sanitize(result.get("text", ""))
            return {
                "type": "answer",
                "intent": intent,
                "answer": result,
                "route_taken": "compute",
                "session_id": session_id
            }

        # Étape 5: RAG complet via RAGRetriever
        logger.info("📚 RAG via RAGRetriever")
        rag = _rag_answer(question, k=5)
        rag_text = _final_sanitize(rag.get("text", ""))
        rag_text = _maybe_synthesize(question, rag_text)
        return {
            "type": "answer",
            "intent": intent,
            "answer": {
                "text": rag_text,
                "source": "rag_retriever",
                "confidence": 0.8,  # valeur générique; on peut ajouter un scoring plus tard
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
