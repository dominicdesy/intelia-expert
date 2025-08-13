# -*- coding: utf-8 -*-
"""
Dialogue orchestration - VERSION HYBRIDE AVEC MÉMOIRE CONVERSATIONNELLE + FALLBACK OPENAI + MULTILINGUE UNIVERSEL + COT
- classify -> normalize -> completeness/clarifications
- Route vers compute (si possible) OU table-first (perf targets) OU RAGRetriever
- NOUVEAU: Intégration postgres_memory pour continuité de session
- NOUVEAU: Fallback OpenAI quand RAG insuffisant
- NOUVEAU: Support multilingue universel avec détection automatique
- NOUVEAU: Support Chain-of-Thought pour analyses complexes
- NOUVEAU: Fonctions de synthèse améliorées
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import os
import re
import time

logger = logging.getLogger(__name__)

# ========== IMPORTS AVEC FALLBACKS ==========
from ..utils.question_classifier import classify, Intention
from .context_extractor import normalize
from .clarification_manager import compute_completeness
from ..utils import formulas

# ========== MÉMOIRE CONVERSATIONNELLE ==========
try:
    from .postgres_memory import PostgresMemory
    MEMORY_AVAILABLE = True
    logger.info("✅ PostgresMemory importé pour la mémoire conversationnelle")
except ImportError as e:
    logger.warning(f"⚠️ PostgresMemory indisponible: {e}")
    MEMORY_AVAILABLE = False
    # Fallback en mémoire simple
    class MemoryFallback:
        def __init__(self): self.store = {}
        def get(self, session_id): return self.store.get(session_id, {})
        def update(self, session_id, context): self.store[session_id] = context
        def clear(self, session_id): self.store.pop(session_id, None)
    PostgresMemory = MemoryFallback

# ========== FALLBACK OPENAI AMÉLIORÉ ==========
try:
    from ..utils.openai_utils import (
        complete as openai_complete,
        complete_with_cot,
        synthesize_rag_content,
        generate_clarification_response,
        get_openai_status,
        test_cot_pipeline,
        test_synthesis_pipeline
    )
    OPENAI_FALLBACK_AVAILABLE = True
    OPENAI_COT_AVAILABLE = True
    logger.info("✅ OpenAI fallback + CoT disponible pour réponses avancées")
except ImportError as e:
    logger.warning(f"⚠️ OpenAI fallback avancé indisponible: {e}")
    # Fallback vers fonctions basiques
    try:
        from ..utils.openai_utils import complete as openai_complete
        from ..utils.openai_utils import get_openai_status
        OPENAI_FALLBACK_AVAILABLE = True
        OPENAI_COT_AVAILABLE = False
        logger.info("✅ OpenAI fallback basique disponible")
    except ImportError:
        OPENAI_FALLBACK_AVAILABLE = False
        OPENAI_COT_AVAILABLE = False

# Singleton mémoire conversationnelle
_CONVERSATION_MEMORY = None

def _get_conversation_memory():
    """Retourne le singleton de mémoire conversationnelle"""
    global _CONVERSATION_MEMORY
    if _CONVERSATION_MEMORY is None:
        try:
            if MEMORY_AVAILABLE:
                _CONVERSATION_MEMORY = PostgresMemory(dsn=os.getenv("DATABASE_URL"))
            else:
                _CONVERSATION_MEMORY = PostgresMemory()  # Fallback
            logger.info("🧠 Mémoire conversationnelle initialisée")
        except Exception as e:
            logger.error(f"⌐ Erreur initialisation mémoire: {e}")
            _CONVERSATION_MEMORY = PostgresMemory()  # Fallback simple
    return _CONVERSATION_MEMORY

# ---------------------------------------------------------------------------
# NOUVEAU: Détection de langue universelle et post-processing multilingue AMÉLIORÉ
# ---------------------------------------------------------------------------

def _detect_question_language_openai(question: str) -> str:
    """
    Utilise OpenAI pour détecter automatiquement la langue de la question.
    Supporte toutes les langues sans limitation.
    AMÉLIORÉ: Utilise les nouvelles fonctions optimisées
    """
    if not question or not OPENAI_FALLBACK_AVAILABLE:
        return "fr"  # Fallback par défaut
    
    try:
        detection_prompt = f"""Detect the language of this question and respond with ONLY the 2-letter ISO language code (en, fr, es, de, it, pt, etc.).

Question: "{question}"

Language code:"""

        language_code = openai_complete(
            prompt=detection_prompt,
            temperature=0.1,  # Très déterministe
            max_tokens=5     # Juste le code langue
        )
        
        if language_code:
            detected = language_code.strip().lower()[:2]  # Premier code à 2 lettres
            logger.info(f"🌍 Langue détectée par OpenAI: {detected}")
            return detected
            
    except Exception as e:
        logger.warning(f"⚠️ Erreur détection langue OpenAI: {e}")
    
    # Fallback simple si OpenAI échoue
    return _detect_language_simple_fallback(question)

def _detect_language_simple_fallback(question: str) -> str:
    """
    Fallback simple si OpenAI n'est pas disponible.
    Détection basique français vs non-français.
    """
    if not question:
        return "fr"
        
    text_lower = question.lower()
    
    # Indicateurs français fréquents
    french_indicators = [
        " le ", " la ", " les ", " un ", " une ", " des ", " du ", " de la ",
        "quel", "quelle", "comment", "pourquoi", "combien", " est ", " sont "
    ]
    
    french_score = sum(1 for indicator in french_indicators if indicator in text_lower)
    
    if french_score >= 2:  # Au moins 2 indicateurs français
        return "fr"
    else:
        return "auto"  # Laisse OpenAI gérer dans le post-processing

def _adapt_response_to_language(response_text: str, source_type: str, target_language: str, original_question: str) -> str:
    """
    Adapte la réponse à la langue cible via OpenAI de manière intelligente.
    Supporte TOUTES les langues automatiquement.
    AMÉLIORÉ: Utilise les nouvelles fonctions optimisées
    """
    # Si français, pas de traitement
    if target_language == "fr":
        return response_text
    
    # Si pas d'OpenAI, retourner tel quel
    if not OPENAI_FALLBACK_AVAILABLE:
        logger.warning(f"⚠️ OpenAI indisponible pour adaptation linguistique vers {target_language}")
        return response_text
    
    try:
        # Prompt adaptatif selon le type de source
        adaptation_prompts = {
            "rag_retriever": f"""The user asked this question: "{original_question}"

Here is the response found in the knowledge base (originally in French):
"{response_text}"

Please rewrite this response in the same language as the user's question, maintaining:
- Technical accuracy
- Professional tone
- All specific values and data
- Proper formatting (markdown if present)

Adapted response:""",

            "table_lookup": f"""The user asked: "{original_question}"

Here is a performance data response (originally in French):
"{response_text}"

Please reformat this data in the same language as the user's question, keeping:
- All numerical values exact
- Professional poultry terminology
- Clear formatting

Reformatted response:""",

            "hybrid_ui": f"""The user asked: "{original_question}"

Here is a clarification request (originally in French):
"{response_text}"

Please rewrite this clarification request in the same language as the user's question, maintaining:
- Clear questions
- Professional tone
- All suggested options

Clarification in user's language:""",

            "openai_fallback": response_text,  # Déjà géré par OpenAI

            "compute": f"""The user asked: "{original_question}"

Here is a calculated response (originally in French):
"{response_text}"

Please rewrite this in the same language as the user's question, keeping:
- All calculations and formulas exact
- Technical accuracy
- Professional tone

Calculated response in user's language:""",

            "cot_analysis": f"""The user asked: "{original_question}"

Here is a Chain-of-Thought analysis (originally in French):
"{response_text}"

Please rewrite this analysis in the same language as the user's question, maintaining:
- Logical structure and reasoning
- Technical accuracy
- Professional tone
- All recommendations

Analysis in user's language:"""
        }
        
        prompt = adaptation_prompts.get(source_type, adaptation_prompts["rag_retriever"])
        
        # Adaptation via OpenAI améliorée
        adapted_text = openai_complete(
            prompt=prompt,
            temperature=0.3,  # Légèrement créatif pour naturel
            max_tokens=600    # Assez pour réponses complètes
        )
        
        if adapted_text and len(adapted_text.strip()) > 10:
            logger.info(f"✅ Réponse adaptée de {source_type} vers langue détectée")
            return adapted_text.strip()
        else:
            logger.warning(f"⚠️ Adaptation linguistique échouée, retour original")
            return response_text
            
    except Exception as e:
        logger.error(f"⌐ Erreur adaptation linguistique: {e}")
        return response_text

def _finalize_response_with_language(response: Dict[str, Any], question: str, effective_language: str, detected_language: str) -> Dict[str, Any]:
    """
    Helper pour appliquer l'adaptation linguistique à toute réponse finale.
    Utilise cette fonction avant chaque return dans handle().
    AMÉLIORÉ: Support des réponses CoT
    """
    # Ajouter les métadonnées de langue pour toutes les réponses
    if response.get("type") == "answer" and "answer" in response:
        response["answer"]["meta"] = response["answer"].get("meta", {})
        response["answer"]["meta"]["detected_language"] = detected_language
        response["answer"]["meta"]["effective_language"] = effective_language
        
        # Si c'est déjà un fallback OpenAI avec la bonne langue, pas besoin d'adaptation
        if response["answer"].get("source") in ["openai_fallback", "cot_analysis"]:
            target_lang_in_meta = response["answer"]["meta"].get("target_language", "fr")
            if target_lang_in_meta == effective_language:
                logger.info(f"✅ Fallback OpenAI déjà généré dans la langue cible: {effective_language}")
                return response
        
    elif response.get("type") == "partial_answer":
        response["language_metadata"] = {
            "detected_language": detected_language,
            "effective_language": effective_language
        }
    
    # Si français, pas de traitement supplémentaire nécessaire
    if effective_language == "fr":
        return response
    
    # Adapter le texte principal selon le type de réponse
    if response.get("type") == "answer" and response.get("answer", {}).get("text"):
        answer = response["answer"]
        original_text = answer["text"]
        source_type = answer.get("source", "unknown")
        
        # Ne pas re-adapter les fallbacks OpenAI qui sont déjà dans la bonne langue
        if source_type in ["openai_fallback", "cot_analysis"]:
            logger.info("ℹ️ Fallback OpenAI/CoT - adaptation linguistique déjà effectuée")
            return response
        
        adapted_text = _adapt_response_to_language(
            response_text=original_text,
            source_type=source_type,
            target_language=effective_language,
            original_question=question
        )
        
        # Mettre à jour la réponse
        response["answer"]["text"] = adapted_text
        
    elif response.get("type") == "partial_answer" and response.get("general_answer", {}).get("text"):
        # Pour le mode hybride
        original_text = response["general_answer"]["text"]
        
        adapted_text = _adapt_response_to_language(
            response_text=original_text,
            source_type="hybrid_ui",
            target_language=effective_language,
            original_question=question
        )
        
        response["general_answer"]["text"] = adapted_text
    
    return response

# ---------------------------------------------------------------------------
# NOUVEAU: Fonctions Chain-of-Thought pour analyses complexes
# ---------------------------------------------------------------------------

def _should_use_cot_analysis(intent: Intention, entities: Dict[str, Any], question: str) -> bool:
    """
    Détermine si une analyse Chain-of-Thought serait bénéfique
    """
    if not OPENAI_COT_AVAILABLE:
        return False
    
    # Intentions complexes bénéficiant du CoT
    cot_intents = {
        Intention.HealthDiagnosis,
        Intention.MultiFactor,
        Intention.TroubleshootingMultiple,
        Intention.Economics,
        Intention.OptimizationStrategy,
        Intention.ProductionAnalysis
    }
    
    if intent in cot_intents:
        return True
    
    # Détection de questions complexes dans le texte
    complexity_indicators = [
        "problème", "diagnostic", "analyse", "optimiser", "améliorer",
        "stratégie", "multiple", "plusieurs", "complexe", "comparer",
        "évaluer", "recommandation", "pourquoi", "comment résoudre"
    ]
    
    question_lower = question.lower()
    complexity_score = sum(1 for indicator in complexity_indicators if indicator in question_lower)
    
    # Si 2+ indicateurs de complexité ou question très longue
    return complexity_score >= 2 or len(question) > 200

def _generate_cot_analysis(question: str, entities: Dict[str, Any], intent: Intention, 
                          rag_context: str = "", target_language: str = "fr") -> Dict[str, Any]:
    """
    Génère une analyse Chain-of-Thought pour questions complexes
    """
    if not OPENAI_COT_AVAILABLE:
        return None
        
    try:
        # Construction du contexte avicole
        system_context = _build_agricultural_context(entities, intent)
        
        # Prompt CoT spécialisé selon l'intention
        cot_prompts = {
            "HealthDiagnosis": f"""Tu es un vétérinaire avicole expert. Analyse cette situation sanitaire avec une approche méthodologique rigoureuse.

{system_context}

Question: {question}

Contexte disponible: {rag_context[:500] if rag_context else 'Contexte limité'}

<thinking>
Identifie les symptômes, signes cliniques et facteurs mentionnés dans la question.
</thinking>

<analysis>
Analyse les causes possibles, facteurs de risque et interconnexions.
</analysis>

<factors>
Évalue l'impact de l'âge, lignée, environnement et gestion sur la situation.
</factors>

<recommendations>
Propose un diagnostic différentiel et plan d'action structuré.
</recommendations>

Diagnostic vétérinaire professionnel:""",

            "Economics": f"""Tu es un expert en économie avicole. Analyse cette situation avec une approche financière structurée.

{system_context}

Question: {question}

Contexte: {rag_context[:500] if rag_context else 'Données limitées'}

<economic_context>
Analyse la situation économique actuelle et les facteurs de coût.
</economic_context>

<cost_benefit_breakdown>
Décompose les coûts et bénéfices identifiables.
</cost_benefit_breakdown>

<scenario_analysis>
Évalue différents scénarios et leur impact financier.
</scenario_analysis>

<optimization_levers>
Identifie les leviers d'optimisation économique.
</optimization_levers>

<financial_recommendation>
Propose une stratégie financière concrète et chiffrée.
</financial_recommendation>

Analyse économique complète:""",

            "default": f"""Tu es un expert avicole. Analyse cette situation avec une approche méthodologique.

{system_context}

Question: {question}

Contexte: {rag_context[:500] if rag_context else 'Contexte partiel'}

<thinking>
Décompose le problème et identifie les éléments clés.
</thinking>

<analysis>
Analyse les facteurs impliqués et leurs interactions.
</analysis>

<recommendations>
Propose des solutions concrètes et priorisées.
</recommendations>

Réponse experte structurée:"""
        }
        
        intent_name = intent.name if hasattr(intent, 'name') else str(intent)
        cot_prompt = cot_prompts.get(intent_name, cot_prompts["default"])
        
        # Adaptation linguistique du prompt si nécessaire
        if target_language != "fr":
            cot_prompt = cot_prompt.replace("Tu es", "You are").replace("Analyse", "Analyze")
            # Adaptation basique - le modèle s'adaptera au contexte
        
        # Analyse CoT avec parsing
        cot_result = complete_with_cot(
            prompt=cot_prompt,
            temperature=0.4,  # Créativité modérée pour expertise
            max_tokens=800,   # Suffisant pour analyse complète
            parse_cot=True
        )
        
        if cot_result:
            return {
                "text": cot_result.get("final_answer", cot_result.get("raw_response", "")),
                "source": "cot_analysis",
                "confidence": 0.85,  # Confiance élevée pour analyse structurée
                "sources": [],
                "meta": {
                    "cot_sections": cot_result.get("parsed_sections", {}),
                    "analysis_type": intent_name,
                    "entities_used": entities,
                    "rag_context_provided": bool(rag_context.strip()),
                    "target_language": target_language,
                    "raw_response_length": len(cot_result.get("raw_response", ""))
                }
            }
            
    except Exception as e:
        logger.error(f"⌐ Erreur analyse CoT: {e}")
        
    return None

# ---------------------------------------------------------------------------
# Helpers PerfTargets (dédupliqués) - CODE ORIGINAL CONSERVÉ
# ---------------------------------------------------------------------------

_AGE_PATTERNS = [
    r"\b(?:âge|age)\s*[:=]?\s*(\d{1,2})\s*(?:j|jours|d|days)\b",  # âge: 21 jours / age=21d
    r"\b(?:J|D)\s*?(\d{1,2})\b",                                 # J21 / D21
    r"\b(?:day|jour)\s*(\d{1,2})\b",                              # day 21 / jour 21
    r"\b(\d{1,2})\s*(?:j|jours|d|days)\b",                        # 21 j / 21d
    r"\bage_days\s*[:=]\s*(\d{1,2})\b",                           # age_days=21
]

def _extract_age_days_from_text(text: str) -> Optional[int]:
    if not text:
        return None
    for pat in _AGE_PATTERNS:
        m = re.search(pat, text, flags=re.I)
        if m:
            try:
                val = int(m.group(1))
                if 0 <= val <= 70:
                    return val
            except Exception:
                continue
    return None

def _normalize_sex_from_text(text: str) -> Optional[str]:
    t = (text or "").lower()
    if any(k in t for k in ["as hatched", "as-hatched", "as_hatched", "mixte", "mixed", " ah "]):
        return "as_hatched"
    if any(k in t for k in ["mâle", " male ", "male"]):
        return "male"
    if any(k in t for k in ["femelle", " female ", "female"]):
        return "female"
    return None

def _extract_line_from_text(text: str) -> Optional[str]:
    """Extraction de lignée depuis le texte"""
    t = (text or "").lower()
    if any(k in t for k in ["cobb", "cobb500", "cobb 500", "cobb-500"]):
        return "cobb500"
    if any(k in t for k in ["ross", "ross308", "ross 308", "ross-308"]):
        return "ross308"
    if any(k in t for k in ["hubbard"]):
        return "hubbard"
    return None

def _extract_species_from_text(text: str) -> Optional[str]:
    """Extraction d'espèce depuis le texte"""
    t = (text or "").lower()
    if any(k in t for k in ["broiler", "poulet de chair", "chair"]):
        return "broiler"
    if any(k in t for k in ["layer", "pondeuse", "ponte"]):
        return "layer"
    return None

# [PATCH] – Canonisation tolérante du sexe pour NER/PerfStore/RAG
def _canon_sex(s: Optional[str]) -> Optional[str]:
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
    # [PATCH] – canonise la valeur normalisée
    sex = _canon_sex(sex) or sex

    age_days = entities.get("age_days")
    if age_days is None and entities.get("age_weeks") is not None:
        try: age_days = int(entities["age_weeks"]) * 7
        except Exception: age_days = None
    try: age_days = int(age_days) if age_days is not None else None
    except Exception: age_days = None

    unit = (entities.get("unit") or "metric").lower().strip()
    if unit not in ("metric","imperial"): unit = "metric"

    return {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit}

# ---------------------------------------------------------------------------
# NOUVEAU: Gestion du contexte conversationnel - CODE ORIGINAL CONSERVÉ
# ---------------------------------------------------------------------------

def _merge_conversation_context(current_entities: Dict[str, Any], session_context: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Fusionne le contexte de session avec les entités actuelles.
    Enrichit automatiquement depuis le texte de la question.
    CORRECTION: Préserve l'âge du contexte précédent si non présent dans la nouvelle question.
    """
    # CORRECTION: Commencer par le contexte de session (qui contient l'âge)
    merged = dict(session_context.get("entities", {}))
    
    # Enrichissement automatique depuis le texte
    auto_species = _extract_species_from_text(question)
    auto_line = _extract_line_from_text(question) 
    auto_sex = _normalize_sex_from_text(question)
    auto_age = _extract_age_days_from_text(question)
    
    # CORRECTION: Seulement remplacer si la nouvelle valeur existe
    if auto_species: merged["species"] = auto_species
    if auto_line: merged["line"] = auto_line
    if auto_sex: merged["sex"] = auto_sex
    if auto_age: merged["age_days"] = auto_age  # Seulement si nouvel âge détecté
    
    # CORRECTION: Fusion sélective - ne pas écraser l'âge s'il n'est pas dans current_entities
    for key, value in current_entities.items():
        if key == "age_days" and value is None and merged.get("age_days") is not None:
            # Garder l'âge du contexte précédent si la nouvelle valeur est None
            continue
        merged[key] = value
    
    logger.info(f"🔗 Contexte fusionné: session={session_context.get('entities', {})} + auto={{'species':{auto_species}, 'line':{auto_line}, 'sex':{auto_sex}, 'age':{auto_age}}} + current={current_entities} → {merged}")
    
    return merged

def _should_continue_conversation(session_context: Dict[str, Any], current_intent: Intention) -> bool:
    """
    Détermine si la question actuelle continue une conversation précédente
    """
    if not session_context:
        return False
        
    # Vérifier si il y a une intention en attente
    pending_intent = session_context.get("pending_intent")
    last_timestamp = session_context.get("timestamp", 0)
    
    # Expiration du contexte après 10 minutes
    if time.time() - last_timestamp > 600:
        return False
        
    # Continuer si même intention ou intention ambiguë avec contexte PerfTargets
    if pending_intent == "PerfTargets":
        return current_intent in [Intention.PerfTargets, Intention.AmbiguousGeneral]
        
    return False

def _save_conversation_context(session_id: str, intent: Intention, entities: Dict[str, Any], question: str, missing_fields: List[str]):
    """
    Sauvegarde le contexte conversationnel pour continuité
    """
    try:
        memory = _get_conversation_memory()
        context = {
            "pending_intent": intent.name if hasattr(intent, 'name') else str(intent),
            "entities": entities,
            "question": question,
            "missing_fields": missing_fields,
            "timestamp": time.time()
        }
        memory.update(session_id, context)
        logger.info(f"💾 Contexte sauvegardé pour session {session_id}")
    except Exception as e:
        logger.error(f"⌐ Erreur sauvegarde contexte: {e}")

def _clear_conversation_context(session_id: str):
    """
    Efface le contexte conversationnel après réponse complète
    """
    try:
        memory = _get_conversation_memory()
        memory.clear(session_id)
        logger.info(f"🧹 Contexte effacé pour session {session_id}")
    except Exception as e:
        logger.error(f"⌐ Erreur effacement contexte: {e}")

# ---------------------------------------------------------------------------
# NOUVEAU: Fonctions de fallback OpenAI améliorées
# ---------------------------------------------------------------------------

def _should_use_openai_fallback(rag_result: Dict[str, Any], intent: Intention) -> bool:
    """
    Détermine si OpenAI fallback doit être utilisé après échec RAG
    AMÉLIORÉ: Considère aussi les cas CoT
    """
    # Cas où le RAG n'a pas trouvé de résultats
    if rag_result.get("route") in ["rag_no_results", "rag_error", "rag_unavailable"]:
        return True
    
    # Cas où le RAG a trouvé très peu de contenu pertinent
    text = rag_result.get("text", "")
    if len(text.strip()) < 50:  # Réponse trop courte
        return True
        
    # NOUVEAU: Détecter les fragments de tableaux non pertinents
    text_lower = text.lower()
    table_indicators = [
        "[tableau]", "table", "0.08", "0.10", "0.12", "0.15", "0.17", "0.20",
        "distance air", "ceiling", "width", "pressure drop", "pa (0.01",
        "post-mortem", "examination", "subdermal", "thoracic coelomic"
    ]
    table_matches = sum(1 for indicator in table_indicators if indicator in text_lower)
    
    # Si plus de 3 indicateurs de tableau détectés, probable fragment non pertinent
    if table_matches >= 3:
        logger.info(f"🔍 Fragment de tableau détecté ({table_matches} indicateurs) - activation fallback")
        return True
        
    # Cas où le RAG retourne un message d'erreur générique
    error_indicators = [
        "aucune information", "non disponible", "n'est pas disponible",
        "une erreur est survenue", "moteur rag", "base de connaissances"
    ]
    if any(indicator in text_lower for indicator in error_indicators):
        return True
        
    return False

def _build_agricultural_context(entities: Dict[str, Any], intent: Intention) -> str:
    """
    Construit un contexte agricole pour orienter la réponse OpenAI
    AMÉLIORÉ: Support des nouvelles intentions CoT
    """
    context_parts = []
    
    # Contexte espèce
    species = entities.get("species", "").lower()
    if species == "broiler":
        context_parts.append("Contexte : Poulets de chair (broilers)")
    elif species == "layer":
        context_parts.append("Contexte : Poules pondeuses")
    else:
        context_parts.append("Contexte : Élevage de volailles")
    
    # Contexte lignée si disponible
    line = entities.get("line")
    if line:
        line_map = {
            "ross308": "lignée Ross 308",
            "cobb500": "lignée Cobb 500",
            "hubbard": "lignée Hubbard"
        }
        line_name = line_map.get(line.lower(), f"lignée {line}")
        context_parts.append(f"Lignée : {line_name}")
    
    # Contexte âge si disponible
    age_days = entities.get("age_days")
    if age_days:
        context_parts.append(f"Âge : {age_days} jours")
    
    # Contexte sexe si disponible
    sex = entities.get("sex")
    if sex:
        sex_map = {
            "male": "mâles",
            "female": "femelles", 
            "as_hatched": "sexes mélangés"
        }
        sex_name = sex_map.get(sex.lower(), sex)
        context_parts.append(f"Sexe : {sex_name}")
    
    # Contexte intention AMÉLIORÉ
    intent_context = {
        "PerfTargets": "Focus sur les objectifs de performance (poids, croissance)",
        "HealthDiagnosis": "Focus sur la santé et diagnostic vétérinaire",
        "NutritionAdvice": "Focus sur l'alimentation et la nutrition",
        "HousingEnvironment": "Focus sur le logement et l'environnement d'élevage",
        "ManagementPractices": "Focus sur les pratiques de gestion d'élevage",
        "WaterFeedIntake": "Focus sur la consommation d'eau et d'aliment",
        "EquipmentSizing": "Focus sur le dimensionnement des équipements",
        "VentilationSizing": "Focus sur la ventilation et l'ambiance",
        "EnvSetpoints": "Focus sur les consignes environnementales",
        "Economics": "Focus sur les aspects économiques de l'élevage",
        "MultiFactor": "Analyse multi-factorielle complexe",
        "TroubleshootingMultiple": "Résolution de problèmes multiples",
        "OptimizationStrategy": "Stratégie d'optimisation globale",
        "ProductionAnalysis": "Analyse de performance de production"
    }
    
    intent_name = intent.name if hasattr(intent, 'name') else str(intent)
    if intent_name in intent_context:
        context_parts.append(intent_context[intent_name])
    
    return "\n".join(context_parts)

def _generate_openai_fallback_response(question: str, entities: Dict[str, Any], intent: Intention, rag_context: str = "", target_language: str = "fr") -> Dict[str, Any]:
    """
    Génère une réponse via OpenAI quand le RAG échoue
    AMÉLIORÉ: Intégration avec CoT si approprié et nouvelles fonctions
    """
    if not OPENAI_FALLBACK_AVAILABLE:
        return None
    
    try:
        # NOUVEAU: Vérifier si CoT serait approprié
        if OPENAI_COT_AVAILABLE and _should_use_cot_analysis(intent, entities, question):
            logger.info("🧠 Fallback avec analyse CoT pour question complexe")
            cot_result = _generate_cot_analysis(
                question=question,
                entities=entities,
                intent=intent,
                rag_context=rag_context,
                target_language=target_language
            )
            
            if cot_result:
                cot_result["meta"]["fallback_reason"] = "rag_insufficient_cot_analysis"
                return cot_result
        
        # Fallback standard si CoT non disponible/approprié
        system_context = _build_agricultural_context(entities, intent)
        
        # NOUVEAU: Prompt ultra-explicite pour forcer la langue
        if target_language == "fr":
            fallback_prompt = f"""Tu es un expert en aviculture et zootechnie. Un utilisateur pose une question sur l'élevage de volailles.

{system_context}

Question de l'utilisateur : {question}

Contexte partiel disponible (si pertinent) : {rag_context}

INSTRUCTIONS IMPORTANTES :
- Réponds EXCLUSIVEMENT en français
- Donne une réponse basée sur tes connaissances en aviculture
- Sois précis et technique quand approprié  
- Si tu mentionnes des valeurs, indique qu'elles sont approximatives
- Structure ta réponse en Markdown si pertinent
- Mentionne que pour des données spécifiques à une lignée/âge précis, une consultation des guides techniques est recommandée

Réponse professionnelle EN FRANÇAIS :"""

        else:
            # Pour toutes les autres langues (surtout anglais)
            fallback_prompt = f"""You are an expert in poultry farming and zootechnics. A user is asking a question about poultry farming.

{system_context}

User's question: {question}

Partial available context (if relevant): {rag_context}

CRITICAL INSTRUCTIONS:
- You MUST respond ONLY in English
- DO NOT use any French words or phrases
- Provide an answer based on your poultry farming knowledge  
- Be precise and technical when appropriate
- If you mention values, indicate they are approximate
- Structure your response in Markdown if relevant
- Mention that for specific data related to a precise breed/age, consulting technical guides is recommended

Professional response IN ENGLISH ONLY:"""

        # AMÉLIORÉ: Utilisation de la fonction complete optimisée
        response = openai_complete(
            prompt=fallback_prompt,
            temperature=0.3,  # Légèrement créatif mais précis
            max_tokens=400
        )
        
        if response:
            return {
                "text": response,
                "source": "openai_fallback",
                "confidence": 0.75,  # Confiance modérée
                "sources": [],
                "meta": {
                    "fallback_reason": "rag_insufficient",
                    "entities_used": entities,
                    "intent": intent.name if hasattr(intent, 'name') else str(intent),
                    "rag_context_provided": bool(rag_context.strip()),
                    "target_language": target_language,
                    "prompt_language": "french" if target_language == "fr" else "english",
                    "cot_attempted": False
                }
            }
            
    except Exception as e:
        logger.error(f"⌐ OpenAI fallback échoué: {e}")
        
    return None

# ---------------------------------------------------------------------------
# PerfStore singletons & lookup - CODE ORIGINAL CONSERVÉ
# ---------------------------------------------------------------------------

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

def _perf_lookup_exact_or_nearest(store: "PerfStore", norm: Dict[str, Any], question: str = "") -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Essaie un match exact (line, unit, sex, age_days) puis nearest sur l'âge.
    Retourne (record, debug).
    """
    debug: Dict[str, Any] = {}
    try:
        # -----------------------
        # 0) Récup du DataFrame
        # -----------------------
        df = getattr(store, "as_dataframe", None)
        df = df() if callable(df) else getattr(store, "df", None)

        if df is None:
            # [PATCH] fallback per-line si pas de DF global
            _load_df = getattr(store, "_load_df", None)
            if callable(_load_df):
                try:
                    df = _load_df(norm.get("line"))
                    debug["used_per_line_table"] = True  # [PATCH]
                except Exception as e:
                logger.warning(f"⚠️ Échec clarification spécialisée, fallback standard: {e}")
        
        # Fallback vers méthode standard si fonction spécialisée échoue
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
        sex_map = {"male": "Mâle", "female": "Femelle", "mixed": "Mixte", "as_hatched": "Mixte"}
        sex_label = sex_map.get(str(defaults["sex"]).lower(), "Mixte")
        age_label = f"{age_days} jours" if age_days is not None else "l'âge indiqué"
        header = f"Le **poids cible à {age_label}** dépend de la **lignée** et du **sexe**."
        sub = "Pour te donner la valeur précise, j'ai besoin de confirmer ces points :"
        q1 = "• **Espèce** : Poulet de chair (broiler) ?"
        q2 = "• **Lignée** : Ross 308, Cobb 500 ou autre ?"
        q3 = "• **Sexe** : Mâle, Femelle ou Mixte ?"
        defaults_line = f"**Broiler · {line_label} · {sex_label}" + (f" · {age_days} jours**" if age_days is not None else "**")
        cta = f"👉 Si tu veux aller plus vite, je peux répondre avec l'hypothèse par défaut suivante et tu corriges si besoin :\n{defaults_line}. **Tu valides ?**"
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
        logger.error(f"⌐ Error generating hybrid UX answer: {e}")
        return {"text": "Je dois confirmer quelques éléments (espèce, lignée, sexe) avant de donner la valeur précise. Souhaites-tu utiliser des valeurs par défaut ?",
                "source": "hybrid_ui_fallback", "confidence": 0.4, "enriched": False}

# ---------------------------------------------------------------------------
# Fonction de statut pour monitoring AMÉLIORÉE
# ---------------------------------------------------------------------------

def get_fallback_status() -> Dict[str, Any]:
    """
    Retourne le statut du système de fallback OpenAI avec support CoT
    AMÉLIORÉ: Inclut les nouvelles capacités
    """
    status = {
        "openai_fallback_available": OPENAI_FALLBACK_AVAILABLE,
        "openai_cot_available": OPENAI_COT_AVAILABLE,
        "rag_available": RAG_AVAILABLE,
        "perfstore_available": PERF_AVAILABLE,
        "memory_available": MEMORY_AVAILABLE
    }
    
    if OPENAI_FALLBACK_AVAILABLE:
        try:
            openai_status = get_openai_status()
            status["openai_status"] = openai_status
        except Exception as e:
            status["openai_error"] = str(e)
    
    # Configuration fallback
    status["fallback_enabled"] = str(os.getenv("ENABLE_OPENAI_FALLBACK", "true")).lower() in ("1", "true", "yes", "on")
    status["synthesis_enabled"] = str(os.getenv("ENABLE_SYNTH_PROMPT", "0")).lower() in ("1", "true", "yes", "on")
    status["auto_language_detection"] = str(os.getenv("ENABLE_AUTO_LANGUAGE_DETECTION", "true")).lower() in ("1", "true", "yes", "on")
    
    # NOUVEAU: Statut CoT
    if OPENAI_COT_AVAILABLE:
        status["cot_config"] = {
            "auto_detection_enabled": True,
            "supported_intents": [
                "HealthDiagnosis", "MultiFactor", "TroubleshootingMultiple", 
                "Economics", "OptimizationStrategy", "ProductionAnalysis"
            ],
            "complexity_threshold": 2
        }
    
    return status

def get_cot_capabilities() -> Dict[str, Any]:
    """
    NOUVEAU: Retourne les capacités Chain-of-Thought disponibles dans dialogue_manager
    """
    if not OPENAI_COT_AVAILABLE:
        return {"cot_available": False, "reason": "openai_utils CoT functions not available"}
    
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
    NOUVEAU: Test complet du pipeline amélioré avec CoT et synthèse
    """
    try:
        results = {}
        
        # Test fonction de base
        results["basic_status"] = {
            "openai_fallback": OPENAI_FALLBACK_AVAILABLE,
            "cot_available": OPENAI_COT_AVAILABLE,
            "rag_available": RAG_AVAILABLE,
            "memory_available": MEMORY_AVAILABLE
        }
        
        # Test CoT si disponible
        if OPENAI_COT_AVAILABLE:
            try:
                cot_test = test_cot_pipeline()
                results["cot_test"] = cot_test
            except Exception as e:
                results["cot_test"] = {"status": "error", "error": str(e)}
        
        # Test synthèse si disponible
        if OPENAI_FALLBACK_AVAILABLE:
            try:
                synthesis_test = test_synthesis_pipeline()
                results["synthesis_test"] = synthesis_test
            except Exception as e:
                results["synthesis_test"] = {"status": "error", "error": str(e)}
        
        # Test détection de langue
        try:
            lang_test = _detect_question_language_openai("What is the optimal weight for broilers?")
            results["language_detection"] = {
                "status": "success",
                "detected": lang_test,
                "expected": "en"
            }
        except Exception as e:
            results["language_detection"] = {"status": "error", "error": str(e)}
        
        return {
            "status": "success",
            "message": "Pipeline amélioré testé avec succès",
            "detailed_results": results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Échec test pipeline amélioré: {str(e)}",
            "error_type": type(e).__name__
        }

# ---------------------------------------------------------------------------
# Entrée principale AVEC MÉMOIRE CONVERSATIONNELLE + FALLBACK OPENAI + MULTILINGUE + COT
# ---------------------------------------------------------------------------

def handle(
    session_id: str,
    question: str,
    lang: str = "fr",
    # Overrides & debug
    debug: bool = False,
    force_perfstore: bool = False,
    intent_hint: Optional[str] = None,
    # [PATCH] NEW: entities pass-through depuis l'API
    entities: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fonction principale de traitement des questions - VERSION HYBRIDE AVEC MÉMOIRE CONVERSATIONNELLE + FALLBACK OPENAI + MULTILINGUE UNIVERSEL + COT
    
    AMÉLIORATIONS APPLIQUÉES:
    - Support Chain-of-Thought pour analyses complexes
    - Nouvelles fonctions de synthèse et clarification
    - Pipeline de fallback optimisé
    - Détection automatique de complexité pour CoT
    """
    try:
        logger.info(f"🤖 Processing question: {question[:120]}...")
        logger.info(f"[DM] flags: force_perfstore={force_perfstore}, intent_hint={intent_hint}, has_entities={bool(entities)}")

        # =================================================================
        # NOUVEAU: DÉTECTION DE LANGUE AUTOMATIQUE AMÉLIORÉE
        # =================================================================
        auto_detection_enabled = str(os.getenv("ENABLE_AUTO_LANGUAGE_DETECTION", "true")).lower() in ("1", "true", "yes", "on")
        
        if auto_detection_enabled:
            detected_language = _detect_question_language_openai(question)
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
        # NOUVEAU: RÉCUPÉRATION DU CONTEXTE CONVERSATIONNEL
        # =================================================================
        memory = _get_conversation_memory()
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
            try: _ents.update(entities)
            except Exception: pass
        
        # NOUVEAU: Vérifier si on continue une conversation
        if _should_continue_conversation(session_context, intent):
            logger.info("🔗 Continuation de conversation détectée")
            # Fusionner avec le contexte précédent et enrichir automatiquement
            _ents = _merge_conversation_context(_ents, session_context, question)
            # Forcer l'intention vers PerfTargets si c'était en attente
            if session_context.get("pending_intent") == "PerfTargets":
                intent = Intention.PerfTargets
                logger.info("🎯 Intention forcée vers PerfTargets par contexte conversationnel")
        
        entities = _ents

        # [PATCH] – Canonicalisation immédiate du sexe pour robustesse NER/PerfStore/RAG
        entities["sex"] = _canon_sex(entities.get("sex")) or entities.get("sex")

        # Hint manuel (tests console)
        if intent_hint and str(intent_hint).lower().startswith("perf"):
            intent = Intention.PerfTargets

        logger.info(f"Intent: {intent}, Entities keys: {list(entities.keys())}")

        # =================================================================
        # NOUVEAU: VÉRIFICATION PRIORITAIRE POUR ANALYSE COT
        # =================================================================
        if OPENAI_COT_AVAILABLE and _should_use_cot_analysis(intent, entities, question):
            logger.info("🧠 Question complexe détectée → Analyse Chain-of-Thought prioritaire")
            
            # Passer l'intent dans les entities pour le context
            entities_with_intent = dict(entities)
            entities_with_intent["_intent"] = intent
            
            # Tentative d'analyse CoT directe
            cot_result = _generate_cot_analysis(
                question=question,
                entities=entities,
                intent=intent,
                rag_context="",  # Pas de contexte RAG préalable
                target_language=effective_language
            )
            
            if cot_result:
                logger.info("✅ Analyse CoT réussie, retour direct")
                _clear_conversation_context(session_id)
                
                response = {
                    "type": "answer",
                    "intent": intent,
                    "answer": cot_result,
                    "route_taken": "cot_analysis_priority",
                    "session_id": session_id
                }
                
                return _finalize_response_with_language(response, question, effective_language, detected_language)
            else:
                logger.info("⚠️ Analyse CoT échouée, continuation pipeline standard")

        # Étape 3: Vérification de complétude
        completeness = compute_completeness(intent, entities)
        completeness_score = completeness["completeness_score"]
        missing_fields = completeness["missing_fields"]
        logger.info(f"Completeness score: {completeness_score} | Missing: {missing_fields}")

        # NOUVEAU: Si conversation continue et complète maintenant, aller directement au traitement
        if _should_continue_conversation(session_context, intent) and completeness_score >= 0.8:
            logger.info("🚀 Conversation continue avec données complètes → traitement direct")
            # Effacer le contexte car on va donner la réponse finale
            _clear_conversation_context(session_id)
        # HYBRIDE : si infos manquantes → synthèse courte + clarifications
        elif missing_fields and completeness_score < 0.8:
            logger.info("🧭 Mode hybride: synthèse courte + questions de précision")
            general_answer = _generate_general_answer_with_specifics(question, entities, intent, missing_fields)
            
            # NOUVEAU: Sauvegarder le contexte pour continuité
            _save_conversation_context(session_id, intent, entities, question, missing_fields)
            
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
            
            # NOUVEAU: Appliquer adaptation linguistique
            return _finalize_response_with_language(response, question, effective_language, detected_language)

        # Étape 4: Calcul direct si possible (code original)
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
            result = _compute_answer(intent, entities)  # défini ailleurs dans le projet
            result["text"] = _final_sanitize(result.get("text", ""))
            
            # NOUVEAU: Effacer le contexte après réponse finale
            _clear_conversation_context(session_id)
            
            response = {
                "type": "answer",
                "intent": intent,
                "answer": result,
                "route_taken": "compute",
                "session_id": session_id
            }
            
            # NOUVEAU: Appliquer adaptation linguistique
            return _finalize_response_with_language(response, question, effective_language, detected_language)

        # Étape 4bis: TABLE-FIRST pour PerfTargets (avant RAG)
        if force_perfstore or (intent == Intention.PerfTargets and completeness_score >= 0.6):
            logger.info("📊 Table-first (PerfTargets) avant RAG")
            try:
                norm = _normalize_entities_soft(entities)
                if norm.get("age_days") is None:
                    age_guess = _extract_age_days_from_text(question)
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
                        try: val_txt = f"**{float(v_g):.0f} g**"
                        except Exception: val_txt = f"**{v_g} g**"
                    elif v_lb is not None:
                        try: val_txt = f"**{float(v_lb):.2f} lb**"
                        except Exception: val_txt = f"**{v_lb} lb**"
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
                    
                    # NOUVEAU: Effacer le contexte après réponse finale réussie
                    _clear_conversation_context(session_id)
                    
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
                    
                    # NOUVEAU: Appliquer adaptation linguistique
                    return _finalize_response_with_language(response, question, effective_language, detected_language)
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
            rag_text = _maybe_synthesize(question, rag_text)

        # NOUVEAU: Effacer le contexte après réponse finale (même si RAG)
        _clear_conversation_context(session_id)

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
        
        # NOUVEAU: Appliquer adaptation linguistique
        return _finalize_response_with_language(response, question, effective_language, detected_language)

    except Exception as e:
        logger.exception(f"⌐ Critical error in handle(): {e}")
        response = {
            "type": "error",
            "error": str(e),
            "message": "Une erreur inattendue s'est produite lors du traitement de votre question.",
            "session_id": session_id
        }
        
        # Même en cas d'erreur, essayer d'adapter la langue si possible
        try:
            detected_language = _detect_question_language_openai(question) if question else "fr"
            effective_language = detected_language if detected_language != "fr" else "fr"
            return _finalize_response_with_language(response, question or "", effective_language, detected_language)
        except:
            return response

# ---------------------------------------------------------------------------
# Fonction manquante _compute_answer (placeholder pour la compatibilité)
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
                    debug["load_df_error"] = str(e)

        if df is None:
            return None, {"reason": "no_dataframe", "hint": "per-line table missing", "line": norm.get("line")}

        # ---------------------------------------------
        # 1) Harmonisation colonnes minimales (unit/line)
        # ---------------------------------------------
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

        # ---------------------------------------------------------
        # [PATCH] 1bis) Harmonisation de la colonne d'âge → age_days
        # ---------------------------------------------------------
        try:
            # on cherche en insensitive parmi les colonnes existantes
            lower_map = {str(c).lower(): c for c in df.columns}
            possible = ["age_days", "day", "days", "age", "age(d)", "age_d", "age_days(d)", "age (days)", "jours"]
            found_key = next((lower_map[k] for k in possible if k in lower_map), None)

            if found_key and found_key != "age_days":
                # extrait le nombre (ex: "21 d" → 21)
                tmp = df[found_key].astype(str).str.extract(r"(\d+)")[0]
                df["age_days"] = tmp.fillna("0").astype(int)
                debug["age_col_harmonized_from"] = str(found_key)
            elif not found_key:
                # aucune colonne d'âge → crée une colonne neutre pour éviter KeyError
                df["age_days"] = 0
                debug["age_col_harmonized_from"] = None
        except Exception as e:
            # en cas de souci, garde une colonne par défaut
            debug["age_harmonize_error"] = str(e)
            if "age_days" not in df.columns:
                df["age_days"] = 0

        # ------------------------------------------------
        # 2) Normalisation tolérante de la colonne "sex"
        # ------------------------------------------------
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

        # ------------------------------------------------
        # 3) Filtrage par line / unit / sex (+ fallback sex)
        # ------------------------------------------------
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

        # --------------------------
        # 4) Exact age match (si t)
        # --------------------------
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

        # --------------------------
        # 5) Nearest sur l'âge
        # --------------------------
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
# RAG Retriever - CODE ORIGINAL CONSERVÉ
# ---------------------------------------------------------------------------

RAG_AVAILABLE = False
RAGRetrieverCls = None
try:
    from rag.retriever import RAGRetriever as _RAGRetrieverImported
    RAGRetrieverCls = _RAGRetrieverImported
    RAG_AVAILABLE = True
    logger.info("✅ RAGRetriever importé depuis rag.retriever")
except Exception as e1:
    try:
        from .rag.retriever import RAGRetriever as _RAGRetrieverImported2  # type: ignore
        RAGRetrieverCls = _RAGRetrieverImported2
        RAG_AVAILABLE = True
        logger.info("✅ RAGRetriever importé depuis .rag.retriever")
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
            logger.error(f"⌐ Init RAGRetriever échoué: {e}")
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

        # NEW: retry sans sex si vide (souvent trop strict)
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
        logger.error(f"⌐ Erreur RAGRetriever: {e}")
        return {
            "text": "Une erreur est survenue lors de la recherche RAG.",
            "sources": [],
            "route": "rag_error",
            "meta": {"error": str(e), "filters_applied": _build_filters_from_entities(entities or {})}
        }

# ---------------------------------------------------------------------------
# RAG avec fallback OpenAI amélioré
# ---------------------------------------------------------------------------

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
    
    if _should_use_openai_fallback(rag_result, intent):
        logger.info("🤖 Activation fallback OpenAI après échec RAG")
        
        # Tenter fallback OpenAI avec la langue cible (possiblement avec CoT)
        openai_result = _generate_openai_fallback_response(
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
# NETTOYAGE & SYNTHÈSE AMÉLIORÉS
# ---------------------------------------------------------------------------

def _final_sanitize(text: str) -> str:
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

def _maybe_synthesize(question: str, context_text: str) -> str:
    """
    AMÉLIORÉ: Utilise les nouvelles fonctions de synthèse si disponibles
    """
    try:
        if str(os.getenv("ENABLE_SYNTH_PROMPT", "0")).lower() not in ("1", "true", "yes", "on"):
            return context_text
        
        # NOUVEAU: Essai d'abord avec la fonction spécialisée si disponible
        if OPENAI_FALLBACK_AVAILABLE:
            try:
                # Vérifier si synthesize_rag_content est disponible
                if 'synthesize_rag_content' in globals():
                    return synthesize_rag_content(question, context_text, max_length=300)
            except Exception as e:
                logger.warning(f"⚠️ Échec synthèse spécialisée, fallback standard: {e}")
        
        # Fallback vers méthode standard
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

# ===== Mode hybride amélioré =====
def _generate_general_answer_with_specifics(question: str, entities: Dict[str, Any], intent: Intention, missing_fields: list) -> Dict[str, Any]:
    """
    AMÉLIORÉ: Utilise generate_clarification_response si disponible
    """
    try:
        # NOUVEAU: Essai avec la fonction spécialisée si disponible
        if OPENAI_FALLBACK_AVAILABLE and 'generate_clarification_response' in globals():
            try:
                clarification_text = generate_clarification_response(
                    intent=intent.name if hasattr(intent, 'name') else str(intent),
                    missing_fields=missing_fields,
                    general_info=""
                )
                
                # Enrichir avec les boutons rapides
                age_days = None
                if entities.get("age_days") is not None:
                    try: age_days = int(entities["age_days"])
                    except Exception: pass
                elif entities.get("age_weeks") is not None:
                    try: age_days = int(entities["age_weeks"]) * 7
                    except Exception: pass
                    
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