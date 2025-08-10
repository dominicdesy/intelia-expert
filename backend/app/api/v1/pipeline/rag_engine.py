# app/api/v1/pipeline/rag_engine.py - VERSION AMÉLIORÉE
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.openai_utils import safe_chat_completion
from .intent_registry import get_intent_spec, derive_answer_mode, is_urgent_intent

try:
    from rag.embedder import FastRAGEmbedder, create_optimized_embedder  # type: ignore
except Exception:
    FastRAGEmbedder = None  # type: ignore
    create_optimized_embedder = None  # type: ignore

logger = logging.getLogger(__name__)

class _IndexClient:
    """Wrapper pour chargement et recherche dans un index FAISS - AMÉLIORÉ"""

    def __init__(self, index_path: str, model_name: str, sim_threshold: float, 
                 normalize_queries: bool, debug: bool, index_metadata: Dict = None):
        self.index_path = index_path
        self.embedder: Optional[FastRAGEmbedder] = None
        self.ok = False
        self.metadata = index_metadata or {}
        
        # Initialisation de l'embedder
        if create_optimized_embedder is not None:
            self.embedder = create_optimized_embedder(
                model_name=model_name,
                similarity_threshold=sim_threshold,
                normalize_queries=normalize_queries,
                debug=debug,
            )
        elif FastRAGEmbedder is not None:
            self.embedder = FastRAGEmbedder(
                model_name=model_name,
                cache_embeddings=True,
                max_workers=int(os.getenv("RAG_MAX_WORKERS", "2")),
                debug=debug,
                similarity_threshold=sim_threshold,
                normalize_queries=normalize_queries,
            )

        if self.embedder is None:
            logger.error("❌ No embedder available for %s", index_path)
            return {
                "response": content,
                "source": "openai_fallback",
                "documents_used": 0,
                "warning": "Réponse générale : aucun document spécialisé pertinent trouvé.",
                "sources": [],
                "citations": [],
                "inferred_species": self._infer_species(question, context),
                "intent_used": intent
            }
            
        except Exception as e:
            logger.error("❌ Erreur fallback OpenAI: %s", e)
            return {
                "response": "Je rencontre un problème technique. Veuillez reformuler votre question ou préciser le contexte (lignée, âge, type d'élevage).",
                "source": "error_fallback",
                "documents_used": 0,
                "warning": f"Erreur technique: {e}",
                "sources": [],
                "citations": [],
                "inferred_species": None,
                "intent_used": intent
            }

    def _build_general_rag_prompt(self, question: str, context: Optional[Dict[str, Any]], 
                                 docs: List[Dict[str, str]], style: str, fmt: str, weight_only: bool) -> str:
        """Prompt RAG général (fallback pour intentions non spécialisées)"""
        
        doc_lines = self._format_docs_for_prompt(docs)
        form = self._format_preamble(style=style, fmt=fmt, weight_only=weight_only, context=context)
        missing_info = self._identify_missing_context(context)

        return f"""Tu es un expert avicole (broilers & pondeuses). Utilise en priorité les extraits fournis.

QUESTION
{question}

CONTEXTE DISPONIBLE
{context if context else "—"}

DOCUMENTS SPÉCIALISÉS
{doc_lines}

CONSIGNE DE FOND
1) Appuie-toi d'abord sur les documents ci-dessus.
2) Si une info manque, complète prudemment par les bonnes pratiques reconnues et indique clairement ce qui vient des docs.
3) Donne **valeur+unité** en premier quand la question est numérique; si possible **plage** et **conditions** (âge/sexes/génétique).

{missing_info}

CONSIGNE DE FORME
{form}

Réponds en français."""

    def _format_preamble(self, style: str, fmt: str, weight_only: bool, context: Optional[Dict[str, Any]]) -> str:
        """Formate les instructions de forme selon le style demandé"""
        lines = []
        if style == "minimal" or fmt == "bullets":
            lines.append("- Réponds en 2–4 puces maximum.")
        else:
            lines.append("- Réponse courte et structurée.")
        if weight_only:
            age = (context or {}).get("age_jours")
            prefix_age = f" ({age} j)" if age else ""
            lines.append(f"- Si la question concerne le poids: commence par **la fourchette cible{prefix_age}**.")
            lines.append("- Pas de digression.")
            lines.append("- Si lignée/sexes/âge manquent, termine par une courte question de clarification.")
        else:
            lines.append("- Si des infos clés manquent, termine par 1 question de clarification.")
        return "\n".join(lines)

    def _identify_missing_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Identifie les informations manquantes importantes"""
        ctx = context or {}
        missing = []
        if not (ctx.get("race") or ctx.get("breed") or ctx.get("line")):
            missing.append("la lignée (Ross, Cobb, Lohmann, etc.)")
        if not (ctx.get("sexe") or ctx.get("sex_category") or ctx.get("sex")):
            missing.append("le sexe (mâle, femelle, mixte)")
        if not (ctx.get("age_jours") or ctx.get("age_phase") or ctx.get("age_days")):
            missing.append("l'âge précis (jours/semaine)")
        return "INFORMATIONS MANQUANTES\n- " + "\n- ".join(missing) if missing else "CONTEXTE jugé suffisant."

    def _tenant_from_context(self, context: Optional[Dict[str, Any]]) -> Optional[str]:
        """Extrait le tenant depuis le contexte"""
        ctx = context or {}
        t = ctx.get("tenant_id") or ctx.get("tenant") or ctx.get("organisation")
        return str(t) if t else None

    def is_ready(self) -> bool:
        """Vérifie si le RAG engine est prêt"""
        return self._ready

    def get_cache_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur le cache des index"""
        stats = {
            "cached_indexes": len(self._index_cache),
            "cache_details": {}
        }
        
        for cache_key, client in self._index_cache.items():
            stats["cache_details"][cache_key] = {
                "status": "ready" if client.ok else "failed",
                "document_count": client.get_document_count(),
                "metadata_available": bool(client.metadata)
            }
        
        return stats

    def warm_up_cache(self, species_list: List[str] = None) -> Dict[str, bool]:
        """Pré-charge les index les plus utilisés"""
        if species_list is None:
            species_list = ["global", "broiler", "layer"]
        
        results = {}
        for species in species_list:
            try:
                client = self._get_index_client(species)
                results[species] = client is not None and client.ok
                logger.info("🔥 Warm-up %s: %s", species, "✅" if results[species] else "❌")
            except Exception as e:
                logger.warning("⚠️ Warm-up failed for %s: %s", species, e)
                results[species] = False
        
        return results


# Alias pour compatibilité
RAGEngine = SmartRAGEngine

        # Chargement de l'index avec retry
        try:
            self.ok = bool(self.embedder.load_index(index_path))
            if self.ok:
                logger.info("✅ Index chargé: %s", index_path)
                self._load_metadata()
            else:
                logger.warning("⚠️ Échec chargement index: %s", index_path)
        except Exception as e:
            logger.error("❌ Erreur chargement index %s: %s", index_path, e)
            self.ok = False

    def _load_metadata(self):
        """Charge les métadonnées de l'index si disponibles"""
        try:
            meta_path = Path(self.index_path) / "meta.json"
            if meta_path.exists():
                import json
                with open(meta_path, 'r') as f:
                    self.metadata = json.load(f)
                logger.debug("📋 Métadonnées chargées pour %s", self.index_path)
        except Exception as e:
            logger.debug("⚠️ Pas de métadonnées pour %s: %s", self.index_path, e)

    def search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Recherche avec enrichissement des résultats"""
        if not self.ok or self.embedder is None:
            return []
        try:
            results = self.embedder.search(query, k=k)
            # Enrichir avec métadonnées de l'index
            for result in results:
                result.setdefault("index_metadata", self.metadata)
                result.setdefault("index_path", self.index_path)
            return results
        except Exception as e:
            logger.error("❌ Erreur recherche sur %s: %s", self.index_path, e)
            return []

    def get_document_count(self) -> int:
        """Retourne le nombre de documents dans l'index"""
        if not self.ok or not self.embedder:
            return 0
        try:
            if hasattr(self.embedder, 'get_document_count'):
                return self.embedder.get_document_count()
            elif hasattr(self.embedder, 'documents') and self.embedder.documents:
                return len(self.embedder.documents)
        except Exception:
            pass
        return 0


class SmartRAGEngine:
    """
    RAG Engine amélioré avec :
    - Sélection intelligente d'index multi-critères
    - Re-ranking contextuel des résultats  
    - Prompts spécialisés selon l'intention
    - Fusion optimisée de sources multiples
    - Fallback graduel et cache intelligent
    """
    
    def __init__(self, k: int = 6) -> None:
        self.k = int(os.getenv("RAG_TOP_K", str(k)))
        self.model_name = os.getenv("RAG_EMBED_MODEL", "all-MiniLM-L6-v2")
        self.sim_threshold = float(os.getenv("RAG_SIM_THRESHOLD", "0.20"))
        self.normalize_queries = True
        self.debug = True

        self.index_root = Path(os.getenv("RAG_INDEX_ROOT", "rag_index"))
        self.mix_with_global = True
        self.mix_min_docs = max(2, self.k // 3)
        
        # Cache des clients d'index chargés
        self._index_cache: Dict[str, _IndexClient] = {}
        
        # Configuration des stratégies par intention
        self._intent_strategies = {
            "performance": {
                "preferred_indexes": ["species_specific", "performance_objectives"],
                "prefer_tables": True,
                "re_rank_boost": {"table": 0.15, "recent": 0.10},
                "fallback_global": True
            },
            "nutrition": {
                "preferred_indexes": ["species_specific", "nutrition_specs"],
                "prefer_tables": True,
                "re_rank_boost": {"table": 0.20, "nutrition": 0.15},
                "fallback_global": True
            },
            "diagnosis": {
                "preferred_indexes": ["global", "veterinary_guides"],
                "prefer_tables": False,
                "re_rank_boost": {"recent": 0.20, "symptoms": 0.15},
                "fallback_global": False,
                "urgency_boost": True
            },
            "equipment": {
                "preferred_indexes": ["species_specific", "equipment_manuals"],
                "prefer_tables": True,
                "re_rank_boost": {"table": 0.15, "manual": 0.10},
                "fallback_global": True
            }
        }

        self._ready = True

    # ------------------ Sélection d'index intelligente ------------------ #
    
    def _select_optimal_indexes(self, question: str, context: Optional[Dict[str, Any]], 
                               intent: str) -> List[Tuple[str, float]]:
        """
        Sélectionne les index optimaux avec scores de priorité
        
        Returns:
            List[(index_name, priority_score), ...]
        """
        indexes_with_scores = []
        
        # Stratégie selon intention
        domain = intent.split('.')[0] if '.' in intent else intent
        strategy = self._intent_strategies.get(domain, self._intent_strategies["performance"])
        
        # 1. Index spécifique à l'espèce (priorité haute)
        species = context.get("species") if context else None
        if not species:
            species = self._infer_species(question, context)
            
        if species and species in ["broiler", "layer"]:
            indexes_with_scores.append((species, 1.0))
            
        # 2. Index global (fallback ou complément)
        if strategy.get("fallback_global", True):
            # Score plus faible si espèce spécifique disponible
            global_score = 0.7 if species else 0.9
            indexes_with_scores.append(("global", global_score))
        
        # 3. Index spécialisés selon intention
        if domain == "diagnosis" and is_urgent_intent(intent):
            # Pour diagnostic urgent, prioriser global et vétérinaire
            indexes_with_scores = [("global", 1.0)]
            
        elif domain == "performance":
            # Pour performance, prioriser espèce puis global
            if not species:
                # Essayer les deux espèces principales
                indexes_with_scores.extend([
                    ("broiler", 0.8),
                    ("layer", 0.8),
                    ("global", 0.6)
                ])
        
        # 4. Tri par score décroissant
        indexes_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug("🎯 Index sélectionnés: %s pour intent=%s", 
                    [f"{idx}({score:.2f})" for idx, score in indexes_with_scores], intent)
        
        return indexes_with_scores

    def _infer_species(self, question: str, context: Optional[Dict[str, Any]]) -> Optional[str]:
        """Inférence d'espèce améliorée avec plus de patterns"""
        ctx = context or {}
        
        # 1. Depuis contexte explicite
        sp = (ctx.get("species") or ctx.get("espece") or ctx.get("production_type") or "").lower()
        if any(x in sp for x in ["broiler", "chair"]):
            return "broiler"
        if any(x in sp for x in ["layer", "pondeuse"]):
            return "layer"

        # 2. Depuis lignée
        breed = (ctx.get("breed") or ctx.get("race") or ctx.get("line") or "").lower()
        if any(x in breed for x in ["ross", "cobb", "hubbard", "broiler", "308", "500", "708"]):
            return "broiler"
        if any(x in breed for x in ["lohmann", "hy-line", "w36", "w-36", "w80", "w-80", "isa"]):
            return "layer"

        # 3. Depuis question avec patterns étendus
        q = (question or "").lower()
        
        # Patterns poulets de chair
        broiler_patterns = [
            r"\b(?:poulets?|poussins?|poussin)\b(?!.*(?:pondeuse|layer|œuf|oeuf|ponte))",
            r"\b(?:chair|broilers?|abattage)\b",
            r"\b(?:ross|cobb|hubbard)\b",
            r"\b(?:fcr|conversion|indice)\b",
            r"\bpoids\s+(?:cible|vif|abattage)\b"
        ]
        
        # Patterns pondeuses
        layer_patterns = [
            r"\b(?:pondeuses?|poules?\s+pondeuses?)\b",
            r"\b(?:ponte|œufs?|oeufs?|laying)\b",
            r"\b(?:isa|lohmann|hy-?line)\b",
            r"\btaux\s+de\s+ponte\b",
            r"\bproduction\s+(?:d['\'])?œufs?\b"
        ]
        
        import re
        broiler_score = sum(1 for p in broiler_patterns if re.search(p, q))
        layer_score = sum(1 for p in layer_patterns if re.search(p, q))
        
        if broiler_score > layer_score and broiler_score > 0:
            return "broiler"
        elif layer_score > broiler_score and layer_score > 0:
            return "layer"
        
        return None

    # ------------------ Gestion des index avec cache ------------------ #
    
    def _get_index_client(self, index_name: str, tenant: Optional[str] = None) -> Optional[_IndexClient]:
        """Récupère un client d'index avec cache"""
        cache_key = f"{tenant or 'default'}:{index_name}"
        
        if cache_key in self._index_cache:
            client = self._index_cache[cache_key]
            if client.ok:
                return client
            else:
                # Nettoyer cache si client défaillant
                del self._index_cache[cache_key]
        
        # Créer nouveau client
        index_path = self._index_path(index_name, tenant)
        if not index_path.exists():
            logger.debug("📁 Index inexistant: %s", index_path)
            return None
            
        client = _IndexClient(
            index_path=str(index_path),
            model_name=self.model_name,
            sim_threshold=self.sim_threshold,
            normalize_queries=self.normalize_queries,
            debug=self.debug
        )
        
        if client.ok:
            self._index_cache[cache_key] = client
            return client
        
        return None

    def _index_path(self, index_name: str, tenant: Optional[str]) -> Path:
        """Calcule le chemin d'un index"""
        if tenant:
            return self.index_root / tenant / index_name
        return self.index_root / index_name

    # ------------------ Retrieval avec fusion intelligente ------------------ #
    
    def _retrieve_and_fuse(self, question: str, context: Optional[Dict[str, Any]], 
                          intent: str) -> List[Dict[str, Any]]:
        """Récupération avec fusion intelligente de sources multiples"""
        
        tenant = self._tenant_from_context(context)
        selected_indexes = self._select_optimal_indexes(question, context, intent)
        
        all_results = []
        results_by_index = {}
        
        # Récupération depuis chaque index sélectionné
        for index_name, priority_score in selected_indexes:
            client = self._get_index_client(index_name, tenant)
            if not client:
                continue
                
            # Adapter k selon priorité
            k_adjusted = max(2, int(self.k * priority_score))
            results = client.search(question, k_adjusted)
            
            if results:
                # Enrichir avec score de priorité d'index
                for result in results:
                    result["index_priority"] = priority_score
                    result["source_index"] = index_name
                
                results_by_index[index_name] = results
                all_results.extend(results)
                
                logger.debug("📊 Index %s: %d résultats trouvés", index_name, len(results))
        
        if not all_results:
            logger.warning("⚠️ Aucun résultat trouvé dans tous les index pour: %s", question[:50])
            return []
        
        # Re-ranking contextuel
        ranked_results = self._rerank_results(all_results, question, intent, context)
        
        # Déduplication intelligente
        deduped_results = self._deduplicate_results(ranked_results)
        
        # Limiter au top-k final
        final_results = deduped_results[:self.k]
        
        logger.info("🔍 Fusion complète: %d résultats de %d index → %d finaux", 
                   len(all_results), len(results_by_index), len(final_results))
        
        return final_results

    def _rerank_results(self, results: List[Dict[str, Any]], question: str, 
                       intent: str, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Re-ranking contextuel avancé des résultats"""
        
        domain = intent.split('.')[0] if '.' in intent else intent
        strategy = self._intent_strategies.get(domain, {})
        boost_config = strategy.get("re_rank_boost", {})
        
        def calculate_final_score(result: Dict[str, Any]) -> float:
            base_score = float(result.get("score", 0.0))
            
            # Bonus priorité d'index
            index_bonus = float(result.get("index_priority", 0.5)) * 0.1
            base_score += index_bonus
            
            # Bonus type de contenu
            kind = result.get("metadata", {}).get("chunk_type", "").lower()
            if "table" in kind and boost_config.get("table", 0) > 0:
                base_score += boost_config["table"]
            
            # Bonus contenu récent
            source = result.get("metadata", {}).get("file_path", "").lower()
            if any(year in source for year in ["2023", "2024"]) and boost_config.get("recent", 0) > 0:
                base_score += boost_config["recent"]
            
            # Bonus contenu spécialisé
            if domain == "nutrition" and any(term in source for term in ["nutrition", "feeding", "aliment"]):
                base_score += boost_config.get("nutrition", 0)
            elif domain == "diagnosis" and any(term in source for term in ["health", "veterinary", "pathology"]):
                base_score += boost_config.get("symptoms", 0)
            
            # Malus contenu trop générique
            if "general" in source or "overview" in source:
                base_score -= 0.05
            
            # Bonus urgence pour diagnostic
            if is_urgent_intent(intent) and strategy.get("urgency_boost", False):
                base_score += 0.10
            
            # Bonus correspondance espèce
            if context and context.get("species"):
                species = context["species"]
                if species in source or species in result.get("text", "").lower():
                    base_score += 0.08
            
            return max(0.0, min(1.0, base_score))
        
        # Appliquer le scoring et trier
        for result in results:
            result["final_score"] = calculate_final_score(result)
        
        return sorted(results, key=lambda x: x["final_score"], reverse=True)

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Déduplication intelligente basée sur contenu et source"""
        if len(results) <= 1:
            return results
        
        deduped = []
        seen_contents = set()
        seen_sources = set()
        
        for result in results:
            text = result.get("text", "").strip()
            source = result.get("metadata", {}).get("file_path", "")
            
            # Hash du contenu pour détecter doublons exacts
            content_hash = hash(text[:200])  # Premiers 200 caractères
            
            # Skip si contenu identique
            if content_hash in seen_contents:
                continue
            
            # Skip si même source ET scores similaires
            source_key = f"{source}:{len(text)//100}"  # Grouper par source et taille approximative
            if source_key in seen_sources:
                # Garder seulement si score significativement meilleur
                existing_score = max(r["final_score"] for r in deduped 
                                   if r.get("metadata", {}).get("file_path") == source)
                if result["final_score"] <= existing_score + 0.1:
                    continue
            
            seen_contents.add(content_hash)
            seen_sources.add(source_key)
            deduped.append(result)
        
        logger.debug("🔄 Déduplication: %d → %d résultats", len(results), len(deduped))
        return deduped

    # ------------------ Génération de réponse spécialisée ------------------ #
    
    def generate_answer(self, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Point d'entrée principal - génération de réponse adaptative"""
        
        # Récupération du contexte UI et intention
        ui = (context or {}).get("ui_style") or {}
        style = str(ui.get("style") or "standard")
        fmt = str(ui.get("format") or "auto")
        weight_only = bool(ui.get("weight_only") or False)
        prefer_tables = bool((context or {}).get("prefer_tables") or False)
        
        # Déduction d'intention si pas fournie
        intent = (context or {}).get("last_intent") or "general"
        
        logger.info("🚀 RAG.generate_answer | intent=%s | style=%s | Q.len=%s", 
                   intent, style, len(question or ""))

        tenant = self._tenant_from_context(context)
        species = self._infer_species(question, context)
        
        logger.info("🧭 Routing | tenant=%s | species=%s | intent=%s", tenant, species, intent)

        # 1) Récupération documents avec stratégie adaptée
        docs = self._retrieve_and_fuse(question, context, intent)
        documents = self._as_docs(docs, prefer_tables=prefer_tables)

        # 2) Fallback si pas de documents
        if not documents:
            logger.warning("⚠️ Aucun document trouvé - fallback OpenAI")
            return self._openai_fallback(question, context, intent, style=style, fmt=fmt, weight_only=weight_only)

        # 3) Génération avec prompt spécialisé
        prompt = self._build_specialized_prompt(question, context, documents, intent, style, fmt, weight_only)
        
        try:
            # Adapter modèle selon urgence
            model = "gpt-4o" if is_urgent_intent(intent) else os.getenv("OPENAI_MODEL", "gpt-4o")
            max_tokens = 1200 if intent.startswith("diagnosis") else 900
            
            resp = safe_chat_completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=max_tokens,
            )
            content = (resp.choices[0].message.content or "").strip()
            
            if not content:
                content = "Aucune réponse exploitable générée — veuillez reformuler votre question."

            result = {
                "response": content,
                "source": "rag_enhanced",
                "documents_used": len(documents),
                "warning": None,
                "sources": self._build_enhanced_citations(documents),
                "citations": self._build_enhanced_citations(documents),
                "inferred_species": species,
                "intent_used": intent,
                "indexes_searched": list(set(d.get("source_index", "unknown") for d in docs))
            }
            
            # Métadonnées étendues
            result["metadata"] = {
                "retrieval_strategy": "multi_index_fusion",
                "total_candidates": len(docs),
                "final_documents": len(documents),
                "re_ranking_applied": True,
                "intent_strategy": intent.split('.')[0] if '.' in intent else intent
            }
            
            logger.info("✅ RAG complet | contenu=%d chars | sources=%d | intent=%s", 
                       len(content), len(result["citations"]), intent)
            return result
            
        except Exception as e:
            logger.error("❌ Erreur génération OpenAI: %s", e)
            return {
                "response": f"Documents trouvés ({len(documents)}) mais erreur de génération: {str(e)}",
                "source": "rag_error",
                "documents_used": len(documents),
                "warning": f"Erreur traitement RAG: {e}",
                "sources": self._build_enhanced_citations(documents),
                "citations": self._build_enhanced_citations(documents),
                "inferred_species": species,
                "intent_used": intent
            }

    def _build_specialized_prompt(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        docs: List[Dict[str, str]],
        intent: str,
        style: str = "standard",
        fmt: str = "auto", 
        weight_only: bool = False,
    ) -> str:
        """Construction de prompt spécialisé selon l'intention"""
        
        domain = intent.split('.')[0] if '.' in intent else intent
        
        if domain == "performance":
            return self._build_performance_prompt(question, context, docs, intent)
        elif domain == "diagnosis":
            return self._build_diagnosis_prompt(question, context, docs, intent)
        elif domain == "nutrition":
            return self._build_nutrition_prompt(question, context, docs, intent)
        elif domain == "equipment":
            return self._build_equipment_prompt(question, context, docs, intent)
        else:
            return self._build_general_rag_prompt(question, context, docs, style, fmt, weight_only)

    def _build_performance_prompt(self, question: str, context: Optional[Dict[str, Any]], 
                                 docs: List[Dict[str, str]], intent: str) -> str:
        """Prompt spécialisé pour questions de performance"""
        
        doc_lines = self._format_docs_for_prompt(docs, prioritize_tables=True)
        context_str = self._format_context_for_prompt(context)
        
        return f"""Tu es un expert en performances avicoles. Réponds avec des VALEURS NUMÉRIQUES PRÉCISES en priorité.

QUESTION: {question}

CONTEXTE:
{context_str}

DOCUMENTS SPÉCIALISÉS (tables en priorité):
{doc_lines}

INSTRUCTIONS SPÉCIFIQUES PERFORMANCE:
1. **COMMENCE TOUJOURS par la valeur cible avec unité** (ex: "2350g à 35 jours")
2. Donne la plage normale (min-max) si disponible
3. Précise les conditions critiques (lignée, sexe, âge, conditions d'élevage)
4. Cite les sources avec [Doc X]
5. Si plusieurs valeurs selon conditions, présente un tableau simple

FORMAT ATTENDU:
**Valeur cible: [NOMBRE] [UNITÉ]**
- Plage normale: [MIN] - [MAX] [UNITÉ]
- Conditions: [lignée], [sexe], [conditions]
- Variabilité: [facteurs d'influence]
- Source: [Doc X, Y]

FOCUS SELON INTENTION:
- Poids: donner courbe de croissance si pertinent
- FCR: donner évolution par phase
- Production: donner persistance et pic

Réponds en français, sois précis et factuel."""

    def _build_diagnosis_prompt(self, question: str, context: Optional[Dict[str, Any]], 
                               docs: List[Dict[str, str]], intent: str) -> str:
        """Prompt spécialisé pour diagnostic"""
        
        doc_lines = self._format_docs_for_prompt(docs, prioritize_recent=True)
        context_str = self._format_context_for_prompt(context)
        urgency = "URGENT" if is_urgent_intent(intent) else "NORMAL"
        
        return f"""Tu es un expert vétérinaire avicole. Priorité: diagnostic rapide et sûr.

URGENCE: {urgency}

QUESTION: {question}

CONTEXTE OBSERVÉ:
{context_str}

DOCUMENTATION VÉTÉRINAIRE:
{doc_lines}

PROTOCOLE DIAGNOSTIC:
1. **Hypothèses principales** (3 max, ordre de probabilité)
2. **Actions immédiates** à prendre (sécurité d'abord)
3. **Examens complémentaires** si nécessaires
4. **Signes d'alerte** pour surveillance

FORMAT PRIORITAIRE:
**🎯 Diagnostic le plus probable:** [nom]
**⚡ Action immédiate:** [que faire maintenant]
**🔍 Vérifications:** [quoi observer]
**⚠️ Alerte si:** [quand appeler vétérinaire]

IMPORTANTE: Si symptômes graves ou multiples, RECOMMANDER consultation vétérinaire rapide.

Sources: [Doc X]"""

    def _build_nutrition_prompt(self, question: str, context: Optional[Dict[str, Any]], 
                               docs: List[Dict[str, str]], intent: str) -> str:
        """Prompt spécialisé pour nutrition"""
        
        doc_lines = self._format_docs_for_prompt(docs, prioritize_tables=True)
        context_str = self._format_context_for_prompt(context)
        
        return f"""Tu es un expert en nutrition avicole. Donne des spécifications précises et applicables.

QUESTION: {question}

CONTEXTE NUTRITIONNEL:
{context_str}

RÉFÉRENCES NUTRITIONNELLES:
{doc_lines}

STRUCTURE RÉPONSE NUTRITION:
1. **Spécification principale** avec valeur précise
2. **Tableau des besoins** par phase si pertinent
3. **Conditions d'application** (lignée, objectif, environnement)
4. **Variations possibles** selon contexte
5. **Points d'attention** (interactions, contraintes)

FORMAT TABLEAU (si applicable):
| Phase | Protéine % | Énergie kcal/kg | Lysine % | Autres |
|-------|------------|-----------------|-----------|--------|
| Start | XX.X | XXXX | X.XX | ... |

**💡 Conseil pratique:** [application concrète]
**⚠️ Attention:** [points critiques]

Sources: [Doc X]"""

    def _build_equipment_prompt(self, question: str, context: Optional[Dict[str, Any]], 
                               docs: List[Dict[str, str]], intent: str) -> str:
        """Prompt spécialisé pour équipements"""
        
        doc_lines = self._format_docs_for_prompt(docs, prioritize_manuals=True)
        context_str = self._format_context_for_prompt(context)
        
        return f"""Tu es un expert en équipements avicoles. Donne des spécifications techniques précises.

QUESTION: {question}

CONTEXTE TECHNIQUE:
{context_str}

MANUELS ET SPÉCIFICATIONS:
{doc_lines}

STRUCTURE RÉPONSE ÉQUIPEMENT:
1. **Spécification technique** avec calculs
2. **Installation/réglage** étape par étape
3. **Calculs de dimensionnement** avec formules
4. **Recommandations pratiques**
5. **Maintenance** et points de contrôle

FORMAT CALCUL:
**Résultat: [VALEUR] [UNITÉ]**
**Calcul:** [formule utilisée]
**Pour:** [effectif] oiseaux de [âge] jours

**📐 Dimensionnement:**
- Quantité nécessaire: [nombre]
- Espacement recommandé: [distance]
- Hauteur d'installation: [hauteur]

**🔧 Réglages:**
[étapes de réglage numérotées]

Sources: [Doc X]"""

    # ------------------ Helpers et utilitaires ------------------ #
    
    def _format_docs_for_prompt(self, docs: List[Dict[str, str]], 
                               prioritize_tables: bool = False,
                               prioritize_recent: bool = False,
                               prioritize_manuals: bool = False) -> str:
        """Formate les documents pour inclusion dans le prompt"""
        
        if not docs:
            return "Aucun document spécialisé trouvé."
        
        # Tri selon priorités
        sorted_docs = docs.copy()
        
        if prioritize_tables:
            sorted_docs.sort(key=lambda d: ("table" in d.get("kind", "").lower()), reverse=True)
        elif prioritize_recent:
            sorted_docs.sort(key=lambda d: any(year in d.get("source", "") for year in ["2023", "2024"]), reverse=True)
        elif prioritize_manuals:
            sorted_docs.sort(key=lambda d: ("manual" in d.get("source", "").lower()), reverse=True)
        
        doc_lines = []
        for i, d in enumerate(sorted_docs, 1):
            content = (d.get("content") or "").strip()
            if len(content) > 800:  # Limiter longueur
                content = content[:800] + "..."
            source = d.get("source") or "source_inconnue"
            kind = d.get("kind") or "text"
            
            doc_lines.append(f"[Doc {i} | {source} | {kind}]\n{content}")
            
            if i >= 6:  # Limiter nombre de docs
                break
        
        return "\n\n".join(doc_lines)

    def _format_context_for_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Formate le contexte pour inclusion lisible dans le prompt"""
        if not context:
            return "Contexte non disponible"
        
        # Sélectionner champs les plus pertinents
        key_fields = [
            ("species", "Espèce"),
            ("line", "Lignée"), 
            ("age_days", "Âge (jours)"),
            ("sex", "Sexe"),
            ("phase", "Phase"),
            ("effectif", "Effectif"),
            ("problem_type", "Type de problème"),
            ("symptoms", "Symptômes")
        ]
        
        context_lines = []
        for field, label in key_fields:
            value = context.get(field)
            if value:
                context_lines.append(f"- {label}: {value}")
        
        return "\n".join(context_lines) if context_lines else "Contexte minimal disponible"

    def _as_docs(self, hits: List[Dict[str, Any]], prefer_tables: bool = True) -> List[Dict[str, str]]:
        """Convertit les hits de recherche en format document unifié"""
        tables, texts = [], []
        
        for h in hits or []:
            md = (h.get("metadata") or {})
            source = md.get("file_path") or md.get("source") or md.get("path") or md.get("filename") or "unknown_source"
            text = (h.get("text") or "").strip()
            kind = (md.get("chunk_type") or md.get("section_type") or "").lower()
            
            # Enrichir avec métadonnées de recherche
            item = {
                "content": text, 
                "source": str(source), 
                "kind": kind or "text",
                "score": h.get("final_score", h.get("score", 0)),
                "index_source": h.get("source_index", "unknown")
            }
            
            if prefer_tables and "table" in kind:
                tables.append(item)
            else:
                texts.append(item)
        
        # Retourner tables en premier si préférence
        return tables + texts

    def _build_enhanced_citations(self, docs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Construit des citations enrichies avec métadonnées"""
        citations = []
        
        for i, d in enumerate(docs, 1):
            source = d.get("source") or "source_inconnue"
            snippet = (d.get("content") or "").replace("\n", " ")[:150]
            kind = d.get("kind") or "text"
            score = d.get("score", 0)
            index_source = d.get("index_source", "unknown")
            
            citations.append({
                "id": str(i),
                "source": source,
                "snippet": snippet,
                "kind": kind,
                "relevance_score": f"{score:.3f}",
                "index": index_source
            })
        
        return citations

    def _openai_fallback(self, question: str, context: Optional[Dict[str, Any]], intent: str,
                         style: str = "standard", fmt: str = "auto", weight_only: bool = False) -> Dict[str, Any]:
        """Fallback OpenAI avec prompt adapté à l'intention"""
        
        prompt = f"""Tu es un expert avicole. Aucun document spécialisé n'a été trouvé.

QUESTION: {question}
CONTEXTE: {context if context else "—"}
INTENTION DÉTECTÉE: {intent}

CONSIGNE:
1. Donne une réponse générale prudente basée sur les bonnes pratiques
2. Explique les variations possibles (lignée, sexe, âge, conditions)
3. Suggère 1-2 questions de clarification si pertinent
4. INDIQUE CLAIREMENT qu'il s'agit d'une réponse générale

Si diagnostic/santé: RECOMMANDE consultation vétérinaire.
Si performance: DONNE des ordres de grandeur avec réserves.

Réponds en français."""

        try:
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=600,
            )
            content = (resp.choices[0].message.content or "").strip()
            
            if not content:
                content = "Réponse générale indisponible. Veuillez préciser votre question avec plus de détails (lignée, âge, etc.)."
            
            return