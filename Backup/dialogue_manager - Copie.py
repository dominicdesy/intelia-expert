# app/api/v1/pipeline/dialogue_manager.py - VERSION AMÉLIORÉE
from __future__ import annotations

import os
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime

try:
    import anyio
except Exception:
    anyio = None  # type: ignore

from ..utils.response_generator import format_response, build_card
from .context_extractor import ContextExtractor
from .clarification_manager import SmartClarificationManager
from .postgres_memory import PostgresMemory as ConversationMemory
from .rag_engine import SmartRAGEngine
from .intent_registry import infer_intent_with_confidence, get_intent_spec, is_urgent_intent, critical_slots

# Compute utils (optionnels)
try:
    from app.api.v1.utils.formulas import (
        estimate_water_intake_l_per_1000,
        min_ventilation_m3h_per_kg,
        iep_broiler,
        cout_aliment_par_kg_vif,
        dimension_mangeoires,
        dimension_abreuvoirs,
        debit_tunnel_m3h,
        chaleur_a_extraire_w,
    )
except Exception:
    def estimate_water_intake_l_per_1000(*args, **kwargs): return (None, {})
    def min_ventilation_m3h_per_kg(*args, **kwargs): return (None, {})
    def iep_broiler(*args, **kwargs): return (None, {})
    def cout_aliment_par_kg_vif(*args, **kwargs): return (None, {})
    def dimension_mangeoires(*args, **kwargs): return (None, {})
    def dimension_abreuvoirs(*args, **kwargs): return (None, {})
    def debit_tunnel_m3h(*args, **kwargs): return (None, {})
    def chaleur_a_extraire_w(*args, **kwargs): return (None, {})

# Safety policy
try:
    from .policy.safety_rules import requires_vet_redirect
except Exception:
    def requires_vet_redirect(text: str) -> Optional[str]: return None

logger = logging.getLogger(__name__)

# Configuration adaptative des seuils
COMPLETENESS_CONFIG = {
    "diagnosis.health_issue": {"clarify": 0.3, "warn": 0.5, "full": 0.7},
    "diagnosis.performance_issue": {"clarify": 0.4, "warn": 0.6, "full": 0.8},
    "performance.weight_target": {"clarify": 0.5, "warn": 0.7, "full": 0.9},
    "performance.fcr_target": {"clarify": 0.5, "warn": 0.7, "full": 0.9},
    "nutrition.protein_requirements": {"clarify": 0.4, "warn": 0.6, "full": 0.8},
    "default": {"clarify": 0.4, "warn": 0.7, "full": 0.9}
}

def _utc_iso() -> str:
    return datetime.utcnow().isoformat()

class SmartDialogueManager:
    """
    Dialogue Manager amélioré avec :
    - Classification d'intentions avec confiance
    - Seuils adaptatifs selon l'intention
    - Clarifications contextuelles intelligentes
    - Stratégies de réponse hybrides
    - Mémoire conversationnelle enrichie
    """
    
    _instance: Optional["SmartDialogueManager"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SmartDialogueManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.extractor = ContextExtractor()
        self.clarifier = SmartClarificationManager()
        self.memory = ConversationMemory(dsn=os.getenv("DATABASE_URL"))
        self.rag = SmartRAGEngine()
        
        # Métriques et tracking
        self.conversation_metrics = {}
        
        try:
            self._maybe_start_cleanup()
        except Exception as e:
            logger.debug("Cleanup not started: %s", e)

    # ---------------- PUBLIC API ---------------- #
    
    async def handle(
        self,
        session_id: Optional[str],
        question: str,
        language: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Point d'entrée principal avec gestion intelligente du dialogue"""
        
        sid = session_id or str(uuid4())
        logger.info("🟦 DM.handle | sid=%s | Q=%s", sid, (question or "")[:160])

        # 1. Récupération du contexte avec enrichissement
        try:
            context: Dict[str, Any] = self.memory.get(sid) or {}
            context = self._enrich_context_from_history(context, question)
        except Exception as e:
            logger.warning("⚠️ Erreur mémoire: %s", e)
            context = {}

        if language:
            context.setdefault("language", language)
        if user_id:
            context.setdefault("user_id", user_id)

        # 2. Vérification des règles de sécurité
        vet_msg = requires_vet_redirect(question)
        if vet_msg:
            logger.info("🚨 Redirection vétérinaire déclenchée")
            return {
                "type": "policy_redirect",
                "response": format_response(vet_msg),
                "session_id": sid,
                "completeness_score": 1.0,
                "missing_fields": [],
                "metadata": {"policy": "veterinary_redirect"}
            }

        # 3. Extraction de contexte avec scoring
        extracted, extraction_score, missing = self.extractor.extract(question)
        context.update(extracted)
        
        # 4. Classification d'intention avec confiance
        intent, intent_confidence, intent_metadata = infer_intent_with_confidence(question, context)
        context["last_intent"] = intent
        context["intent_confidence"] = intent_confidence
        
        logger.info("🎯 Intent: %s (conf=%.2f) | Extract: score=%.2f, missing=%s", 
                   intent, intent_confidence, extraction_score, missing)

        # 5. Scoring de complétude adaptatif
        completeness_score, final_missing = self._calculate_adaptive_completeness(
            context, intent, missing, extraction_score, intent_confidence
        )
        
        # 6. Configuration UI selon intention
        self._configure_ui_hints(context, intent)

        # 7. Stratégie de réponse selon complétude et urgence
        strategy = self._determine_response_strategy(
            completeness_score, intent, intent_confidence, context
        )
        
        logger.info("📊 Complétude: %.2f | Stratégie: %s | Intent: %s", 
                   completeness_score, strategy, intent)

        # 8. Exécution de la stratégie
        if strategy == "clarification":
            return await self._handle_clarification_strategy(
                sid, intent, final_missing, context, completeness_score
            )
        elif strategy == "hybrid":
            return await self._handle_hybrid_strategy(
                sid, question, intent, context, final_missing, completeness_score
            )
        elif strategy == "answer":
            return await self._handle_answer_strategy(
                sid, question, intent, context, completeness_score, final_missing
            )
        else:
            # Fallback
            return await self._handle_answer_strategy(
                sid, question, intent, context, completeness_score, final_missing
            )

    # ---------------- Stratégies de réponse ---------------- #
    
    async def _handle_clarification_strategy(
        self, 
        session_id: str, 
        intent: str, 
        missing_fields: List[str], 
        context: Dict[str, Any],
        completeness_score: float
    ) -> Dict[str, Any]:
        """Stratégie de clarification pure"""
        
        # Adapter les clarifications selon l'urgence
        if is_urgent_intent(intent):
            # Pour urgences: clarifications minimales et ciblées
            contextual_questions = self.clarifier.generate_contextual_questions(
                missing_fields[:2], intent, context, use_multiple_choice=True
            )
        else:
            # Clarifications complètes
            contextual_questions = self.clarifier.generate_contextual_questions(
                missing_fields, intent, context, use_multiple_choice=True
            )
        
        # Simplifier en format texte si nécessaire
        questions = [q["question"] for q in contextual_questions] if contextual_questions else [
            "Pouvez-vous préciser quelques détails supplémentaires pour vous donner une réponse précise ?"
        ]
        
        # Ajouter contexte de progression
        round_number = context.get("clarification_round", 0) + 1
        context["clarification_round"] = round_number
        
        self._persist_context(session_id, context)
        
        return {
            "type": "clarification",
            "questions": questions,
            "session_id": session_id,
            "completeness_score": completeness_score,
            "missing_fields": missing_fields,
            "metadata": {
                "intent": intent,
                "clarification_round": round_number,
                "urgency": "high" if is_urgent_intent(intent) else "normal",
                "contextual_questions": len(contextual_questions)
            }
        }

    async def _handle_hybrid_strategy(
        self,
        session_id: str,
        question: str,
        intent: str,
        context: Dict[str, Any],
        missing_fields: List[str],
        completeness_score: float
    ) -> Dict[str, Any]:
        """Stratégie hybride : réponse partielle + clarifications ciblées"""
        
        # 1. Générer réponse avec contexte partiel
        answer_text, sources, metrics = await self._generate_answer(question, context, intent)
        
        # 2. Générer clarifications ciblées pour améliorer la précision
        follow_up_questions = self.clarifier.generate_contextual_questions(
            missing_fields[:2], intent, context, use_multiple_choice=False
        )
        
        follow_ups = [q["question"] for q in follow_up_questions]
        
        # 3. Enrichir la réponse avec suggestions d'amélioration
        if follow_ups and answer_text:
            improvement_note = "\n\n💡 **Pour une réponse plus précise:**\n" + "\n".join(f"- {q}" for q in follow_ups)
            answer_text = answer_text + improvement_note
        
        self._persist_context(session_id, context)
        
        return {
            "type": "answer",
            "response": {"answer": format_response(answer_text), "sources": sources},
            "session_id": session_id,
            "completeness_score": completeness_score,
            "missing_fields": missing_fields,
            "follow_up_questions": follow_ups,
            "metadata": {
                **metrics,
                "strategy": "hybrid",
                "intent": intent,
                "warning": "Réponse générale — informations partielles disponibles"
            },
        }

    async def _handle_answer_strategy(
        self,
        session_id: str,
        question: str,
        intent: str,
        context: Dict[str, Any],
        completeness_score: float,
        missing_fields: List[str]
    ) -> Dict[str, Any]:
        """Stratégie de réponse complète"""
        
        # Générer la réponse optimale
        answer_text, sources, metrics = await self._generate_answer(question, context, intent)
        
        # Ajouter suggestions connexes si contexte riche
        suggestions = []
        if completeness_score > 0.8:
            suggestions = self._generate_related_suggestions(intent, context)
        
        self._persist_context(session_id, context)
        
        response_data = {
            "type": "answer",
            "response": {"answer": format_response(answer_text), "sources": sources},
            "session_id": session_id,
            "completeness_score": completeness_score,
            "missing_fields": missing_fields,
            "metadata": {
                **metrics,
                "strategy": "complete_answer",
                "intent": intent,
                "suggestions": suggestions
            },
        }
        
        # Ajouter questions de suivi si pertinent
        if suggestions:
            response_data["follow_up_suggestions"] = suggestions
        
        return response_data

    # ---------------- Génération de réponse ---------------- #
    
    async def _generate_answer(self, question: str, context: Dict[str, Any], intent: str) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """Génération de réponse avec compute-first intelligent"""
        
        # 1. Compute-first pour intentions calculables
        compute_result = await self._try_compute_first(question, context, intent)
        if compute_result:
            return compute_result

        # 2. RAG avec configuration selon intention
        def _call_rag() -> Any:
            return self.rag.generate_answer(question, context)

        try:
            # Appel RAG asynchrone si possible
            if anyio:
                raw = await anyio.to_thread.run_sync(_call_rag)
            else:
                raw = _call_rag()
        except Exception as e:
            logger.exception("❌ Erreur RAG generate_answer: %s", e)
            return ("Désolé, une erreur est survenue lors de la recherche d'informations.", [], {"documents_used": 0})

        # 3. Extraction et formatage de la réponse
        if isinstance(raw, dict):
            answer_text = (raw.get("response") or "").strip() or "Désolé, je n'ai pas pu formater la réponse."
            sources = self._normalize_sources(raw.get("sources") or raw.get("citations") or raw.get("source"))
            meta = {
                "documents_used": int(raw.get("documents_used") or 0),
                "inferred_species": raw.get("inferred_species"),
                "intent_used": raw.get("intent_used", intent),
                "indexes_searched": raw.get("indexes_searched", []),
                "source": raw.get("source", "rag")
            }
        else:
            answer_text = str(raw).strip() or "Désolé, je n'ai pas pu formater la réponse."
            sources, meta = [], {"documents_used": 0, "source": "fallback"}

        return (answer_text, sources, meta)

    async def _try_compute_first(self, question: str, context: Dict[str, Any], intent: str) -> Optional[Tuple[str, List[Dict[str, Any]], Dict[str, Any]]]:
        """Tentative de calcul direct pour intentions appropriées"""
        
        try:
            # IEP calculation
            if intent == "economics.iep_calculation":
                age = context.get("age_days") or context.get("age_jours")
                livability = context.get("livability_pct")
                bw_kg = context.get("avg_weight_kg") or (context.get("poids_moyen_g", 0) / 1000.0 if context.get("poids_moyen_g") else None)
                fcr = context.get("fcr")
                
                if all([age, livability, bw_kg, fcr]):
                    val, calc_details = iep_broiler(livability_pct=livability, avg_weight_kg=bw_kg, fcr=fcr, age_days=age)
                    if val is not None:
                        answer = f"""**IEP = {val:.2f}**

**Détail du calcul:**
- Âge: {age} jours
- Poids vif moyen: {bw_kg:.2f} kg
- FCR: {fcr}
- Viabilité: {livability}%

**Formule:** IEP = (Viabilité% × Poids(kg) × 100) / (FCR × Âge)

**Interprétation:**
- IEP > 400: Excellent
- IEP 350-400: Très bon  
- IEP 300-350: Bon
- IEP < 300: À améliorer"""
                        
                        return (answer, [], {"documents_used": 0, "source": "computation", "calculation": calc_details})

            # Water intake
            elif intent == "nutrition.feed_consumption" and "eau" in question.lower():
                age = context.get("age_days") or context.get("age_jours")
                temp = context.get("ambient_c") or context.get("temperature") or 20
                
                if age:
                    val, calc_details = estimate_water_intake_l_per_1000(age_days=age, ambient_c=temp)
                    if val is not None:
                        answer = f"""**Consommation d'eau: ~{int(round(val))} L/jour/1000 oiseaux**

**Conditions:**
- Âge: {age} jours
- Température ambiante: {temp}°C

**Variation selon température:**
- +20°C: facteur ×1.0 (base)
- +25°C: facteur ×1.15
- +30°C: facteur ×1.30
- +35°C: facteur ×1.50

**À surveiller:** Qualité de l'eau, pression, propreté des abreuvoirs"""
                        
                        return (answer, [], {"documents_used": 0, "source": "computation", "calculation": calc_details})

            # Equipment dimensioning
            elif intent == "equipment.feeders":
                effectif = context.get("effectif")
                age = context.get("age_days") or context.get("age_jours")
                
                if effectif and age:
                    res, calc_details = dimension_mangeoires(effectif=effectif, age_days=age, type_="chaine")
                    if res:
                        answer = f"""**Dimensionnement mangeoires chaîne:**

**Résultat: {res['cm_per_bird']} cm/oiseau**
- Total requis: ~{int(round(res['total_cm_required']))} cm
- Pour {effectif} oiseaux à {age} jours

**Répartition recommandée:**
- Répartir sur 2-4 lignes selon bâtiment
- Hauteur: ajuster selon croissance
- Contrôler espacement régulièrement

**Alternative assiettes:** ~{effectif//15} assiettes seraient nécessaires"""
                        
                        return (answer, [], {"documents_used": 0, "source": "computation", "calculation": calc_details})

        except Exception as e:
            logger.debug("⚠️ Compute-first error for %s: %s", intent, e)
        
        return None

    # ---------------- Logique adaptative ---------------- #
    
    def _calculate_adaptive_completeness(
        self, 
        context: Dict[str, Any], 
        intent: str, 
        missing_fields: List[str],
        extraction_score: float,
        intent_confidence: float
    ) -> Tuple[float, List[str]]:
        """Calcul de complétude adaptatif selon l'intention"""
        
        # Récupérer champs requis pour cette intention
        required_fields = set(get_intent_spec(intent).get("required_context", []))
        critical_fields = set(critical_slots(intent))
        
        if not required_fields:
            # Si pas d'exigences spécifiques, utiliser extraction brute
            return extraction_score, missing_fields
        
        # Calculer score pondéré
        total_weight = 0
        present_weight = 0
        final_missing = []
        
        # Pondération : critiques = 3, requis = 2, optionnels = 1
        for field in required_fields:
            weight = 3 if field in critical_fields else 2
            total_weight += weight
            
            if field in context and context[field]:
                present_weight += weight
            else:
                final_missing.append(field)
        
        # Ajouter champs universellement utiles
        universal_fields = {"species", "line", "age_days"}
        for field in universal_fields:
            if field not in required_fields:
                weight = 1
                total_weight += weight
                if field in context and context[field]:
                    present_weight += weight
                elif field not in final_missing:
                    final_missing.append(field)
        
        # Score final avec bonus confiance intention
        base_score = present_weight / total_weight if total_weight > 0 else extraction_score
        confidence_bonus = min(0.1, intent_confidence * 0.1)
        final_score = min(1.0, base_score + confidence_bonus)
        
        logger.debug("📊 Complétude adaptative: base=%.2f, bonus=%.2f, final=%.2f", 
                    base_score, confidence_bonus, final_score)
        
        return final_score, final_missing

    def _determine_response_strategy(
        self,
        completeness_score: float,
        intent: str,
        intent_confidence: float,
        context: Dict[str, Any]
    ) -> str:
        """Détermine la stratégie de réponse optimale"""
        
        # Récupérer seuils pour cette intention
        thresholds = COMPLETENESS_CONFIG.get(intent, COMPLETENESS_CONFIG["default"])
        
        # Ajustements selon confiance intention
        if intent_confidence < 0.5:
            # Si intention incertaine, être plus conservateur
            thresholds = {k: v + 0.1 for k, v in thresholds.items()}
        
        # Ajustements selon urgence
        if is_urgent_intent(intent):
            # Pour urgences, réduire seuils (répondre plus vite)
            thresholds = {k: v - 0.2 for k, v in thresholds.items()}
        
        # Ajustements selon historique conversationnel
        clarification_round = context.get("clarification_round", 0)
        if clarification_round >= 2:
            # Après 2 tours, forcer une réponse même partielle
            thresholds["clarify"] = max(0.2, thresholds["clarify"] - 0.3)
        
        # Décision finale
        if completeness_score < thresholds["clarify"]:
            return "clarification"
        elif completeness_score < thresholds["warn"]:
            return "hybrid"
        else:
            return "answer"

    def _configure_ui_hints(self, context: Dict[str, Any], intent: str) -> None:
        """Configure les hints UI selon l'intention"""
        
        ui_style = context.setdefault("ui_style", {})
        answer_mode = get_intent_spec(intent).get("answer_mode", "standard")
        
        # Configuration selon mode de réponse
        if "numeric" in answer_mode:
            ui_style.update({
                "style": "minimal",
                "format": "numeric_first",
                "weight_only": intent.endswith("weight_target")
            })
        elif answer_mode == "diagnostic_steps":
            ui_style.update({
                "style": "structured",
                "format": "steps",
                "urgency_mode": True
            })
        elif "table" in answer_mode:
            ui_style.update({
                "style": "standard",
                "format": "table_preferred"
            })
        else:
            ui_style.update({
                "style": "standard",
                "format": "auto"
            })
        
        # Préférence pour tables selon intention
        if intent.startswith(("nutrition", "performance")):
            context["prefer_tables"] = True

    # ---------------- Helpers ---------------- #
    
    def _normalize_sources(self, raw: Any) -> List[Dict[str, Any]]:
        """Normalise les sources dans un format standard"""
        if raw is None:
            return []
        if isinstance(raw, list):
            return [s if isinstance(s, dict) else {"source": str(s)} for s in raw]
        if isinstance(raw, dict):
            return [raw]
        return [{"source": str(raw)}]

    def _enrich_context_from_history(self, context: Dict[str, Any], question: str) -> Dict[str, Any]:
        """Enrichit le contexte avec l'historique de conversation"""
        
        # Incrémenter compteur de questions
        context["question_count"] = context.get("question_count", 0) + 1
        context["last_question"] = question
        context["last_update"] = _utc_iso()
        
        # Détecter changement de sujet
        previous_intent = context.get("last_intent")
        if previous_intent and context.get("question_count", 0) > 1:
            # Simple détection de changement basée sur mots-clés
            if self._topic_changed(question, previous_intent):
                context["topic_changed"] = True
                logger.info("🔄 Changement de sujet détecté: %s → nouveau", previous_intent)
        
        return context

    def _topic_changed(self, question: str, previous_intent: str) -> bool:
        """Détection simple de changement de sujet"""
        current_domain = previous_intent.split('.')[0] if '.' in previous_intent else previous_intent
        
        # Mots-clés par domaine
        domain_keywords = {
            "performance": ["poids", "fcr", "conversion", "croissance", "performance"],
            "nutrition": ["protéine", "aliment", "nutrition", "énergie", "calcium"],
            "diagnosis": ["problème", "maladie", "symptôme", "mortalité", "diagnostic"],
            "equipment": ["mangeoire", "abreuvoir", "équipement", "installation"]
        }
        
        current_keywords = domain_keywords.get(current_domain, [])
        question_lower = question.lower()
        
        # Si aucun mot-clé du domaine précédent trouvé, probable changement
        return not any(kw in question_lower for kw in current_keywords)

    def _generate_related_suggestions(self, intent: str, context: Dict[str, Any]) -> List[str]:
        """Génère des suggestions de questions connexes"""
        
        suggestions = []
        species = context.get("species")
        
        if intent.startswith("performance.weight"):
            suggestions.extend([
                "Quel est le FCR recommandé pour ce même âge ?",
                "Quelles sont les recommandations nutritionnelles correspondantes ?"
            ])
        elif intent.startswith("performance.fcr"):
            suggestions.extend([
                "Quel est le poids cible correspondant ?",
                "Comment optimiser l'indice de consommation ?"
            ])
        elif intent.startswith("nutrition"):
            if species == "broiler":
                suggestions.extend([
                    "Quelle est la consommation d'aliment attendue ?",
                    "Comment adapter selon les conditions d'élevage ?"
                ])
        
        return suggestions[:2]

    def _persist_context(self, sid: str, ctx: Dict[str, Any]) -> None:
        """Persiste le contexte avec gestion d'erreurs"""
        try:
            ctx["last_interaction"] = _utc_iso()
            self.memory.update(sid, ctx)
        except Exception as e:
            logger.debug("⚠️ Erreur persistence mémoire: %s", e)

    def _maybe_start_cleanup(self) -> None:
        """Lance le nettoyage de mémoire si disponible"""
        cleanup_fn = getattr(self.memory, "cleanup_expired", None)
        if not callable(cleanup_fn):
            return
        
        import time
        def _cleanup_loop():
            while True:
                try:
                    cleanup_fn()
                except Exception as e:
                    logger.debug("⚠️ Cleanup mémoire: %s", e)
                time.sleep(max(300, int(os.getenv("CLEANUP_INTERVAL_MINUTES", "30")) * 60))
        
        threading.Thread(target=_cleanup_loop, daemon=True).start()
        logger.info("🧹 Cleanup mémoire démarré")

    # ---------------- Status et debugging ---------------- #
    
    async def system_status(self) -> Dict[str, Any]:
        """Status système complet"""
        try:
            rag_ready = self.rag.is_ready() if hasattr(self.rag, "is_ready") else True
            memory_stats = {}
            
            if hasattr(self.memory, "get_stats"):
                try:
                    memory_stats = self.memory.get_stats()
                except Exception:
                    pass
            
            cache_stats = {}
            if hasattr(self.rag, "get_cache_stats"):
                try:
                    cache_stats = self.rag.get_cache_stats()
                except Exception:
                    pass
            
            return {
                "status": "operational",
                "rag_ready": rag_ready,
                "components": {
                    "context_extractor": "ready",
                    "clarification_manager": "ready", 
                    "rag_engine": "ready" if rag_ready else "limited",
                    "memory": "ready" if self.memory else "unavailable"
                },
                "memory_stats": memory_stats,
                "cache_stats": cache_stats,
                "conversation_metrics": self.conversation_metrics,
                "config": {
                    "adaptive_thresholds": True,
                    "intent_classification": "hierarchical",
                    "clarification_mode": "contextual"
                }
            }
        except Exception as e:
            logger.exception("❌ Erreur system_status: %s", e)
            return {"status": "error", "rag_ready": False, "details": {"error": str(e)}}


# Alias pour compatibilité
DialogueManager = SmartDialogueManager