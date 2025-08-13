# -*- coding: utf-8 -*-
"""
RAG Engine (Intelia) with Chain-of-Thought enhancements
- 1) Essaie d'utiliser les 3 RAG chargés par app.main (app.state.rag[_broiler|_layer])
- 2) Fallback: lit des index FAISS sur disque (rag_index/*/index.faiss + index.pkl)
- Table-first: léger boost sur les chunks dont metadata.chunk_type == "table"
- Numeric-first query: ajoute age/phase/sex/line si présents
- 🆕 NEW: Multi-hop reasoning pour questions complexes
- 🆕 NEW: Enhanced prompting pour réponses CoT
"""
from typing import Dict, Any, List, Tuple, Optional
import os, json, pickle
import numpy as np
import logging

logger = logging.getLogger(__name__)

try:
    import faiss  # fallback only
except Exception:
    faiss = None  # on ne casse pas si FAISS n'est pas dispo côté API

# ----------------------------
# Helpers de composition query (code original conservé)
# ----------------------------
def _numeric_first_query(question: str, entities: Dict[str, Any]) -> str:
    parts = [question]
    for key in ("line", "sex", "phase"):
        v = entities.get(key)
        if v:
            parts.append(f"{key}:{v}")
    if entities.get("age_days") is not None:
        parts.append(f"age_days:{entities['age_days']}")
    if entities.get("age_weeks") is not None:
        parts.append(f"age_weeks:{entities['age_weeks']}")
    return " | ".join(parts)

def _pick_species_index_name(entities: Dict[str, Any]) -> str:
    sp = entities.get("species")
    return sp if sp in ("broiler", "layer") else "global"

def _rerank_table_first(scored: List[Tuple[int, float]], docstore: List[Dict[str, Any]], table_boost: float = 1.2):
    out = []
    for idx, score in scored:
        md = (docstore[idx].get("metadata") or {})
        if md.get("chunk_type") == "table":
            score *= table_boost
        out.append((idx, score))
    out.sort(key=lambda x: x[1], reverse=True)
    return out

def _format_sources(indices: List[int], docstore: List[Dict[str, Any]], limit=6):
    res = []
    for i in indices[:limit]:
        d = docstore[i]
        md = d.get("metadata") or {}
        res.append({
            "title": md.get("title") or md.get("source_path") or "source",
            "page": md.get("page"),
            "is_table": md.get("chunk_type") == "table"
        })
    return res

def _synthesize_answer(ids: List[int], docstore: List[Dict[str, Any]]) -> str:
    if not ids:
        return "Aucune source pertinente trouvée."
    snippets = []
    for i in ids[:3]:
        txt = (docstore[i].get("text") or docstore[i].get("content") or "")[:700]
        if txt:
            snippets.append(txt.strip())
    return "\n\n---\n".join(snippets) if snippets else "Aucune source pertinente trouvée."

# 🆕 NOUVELLES FONCTIONS POUR MULTI-HOP REASONING

def _should_use_multihop(complexity_info: Dict[str, Any], intent: str) -> bool:
    """
    Détermine si multi-hop reasoning est nécessaire
    """
    if not complexity_info:
        return False
    
    # Intentions qui bénéficient du multi-hop
    multihop_intents = [
        "HealthDiagnosis", "OptimizationStrategy", "TroubleshootingMultiple",
        "ProductionAnalysis", "MultiFactor", "Economics"
    ]
    
    complexity_score = complexity_info.get("score", 0)
    complexity_factors = complexity_info.get("factors", [])
    
    return (
        intent in multihop_intents or
        complexity_score >= 35 or
        "multi_symptoms" in complexity_factors or
        "causal_reasoning" in complexity_factors
    )

def _generate_followup_queries(question: str, entities: Dict[str, Any], intent: str) -> List[str]:
    """
    Génère des requêtes de suivi pour multi-hop reasoning
    """
    base_context = []
    if entities.get("species"):
        base_context.append(entities["species"])
    if entities.get("line"):
        base_context.append(entities["line"])
    if entities.get("age_days"):
        base_context.append(f"{entities['age_days']} jours")
    
    context_str = " ".join(base_context)
    
    # Templates de requêtes selon l'intention
    followup_templates = {
        "HealthDiagnosis": [
            f"symptômes normaux {context_str}",
            f"causes fréquentes {context_str}",
            f"diagnostic différentiel {context_str}"
        ],
        "OptimizationStrategy": [
            f"standards performance {context_str}",
            f"facteurs amélioration {context_str}",
            f"bonnes pratiques {context_str}"
        ],
        "Economics": [
            f"coûts production {context_str}",
            f"rentabilité {context_str}",
            f"facteurs économiques {context_str}"
        ],
        "TroubleshootingMultiple": [
            f"causes multiples {context_str}",
            f"interactions facteurs {context_str}",
            f"solutions intégrées {context_str}"
        ]
    }
    
    # Requêtes génériques si intention non spécifiée
    generic_followups = [
        f"références techniques {context_str}",
        f"standards {context_str}",
        f"recommandations {context_str}"
    ]
    
    return followup_templates.get(intent, generic_followups)

def _multihop_search(question: str, entities: Dict[str, Any], intent: str, 
                    search_function, max_hops: int = 3) -> Dict[str, Any]:
    """
    Effectue une recherche multi-hop pour collecter des informations complémentaires
    """
    all_results = []
    search_log = []
    
    # Recherche principale
    primary_query = _numeric_first_query(question, entities)
    primary_result = search_function(primary_query)
    
    if primary_result:
        all_results.append({
            "query": primary_query,
            "result": primary_result,
            "hop": 0,
            "type": "primary"
        })
        search_log.append(f"Primary: {primary_query}")
    
    # Recherches de suivi
    followup_queries = _generate_followup_queries(question, entities, intent)
    
    for i, followup_query in enumerate(followup_queries[:max_hops]):
        try:
            followup_result = search_function(followup_query)
            if followup_result:
                all_results.append({
                    "query": followup_query,
                    "result": followup_result,
                    "hop": i + 1,
                    "type": "followup"
                })
                search_log.append(f"Hop {i+1}: {followup_query}")
        except Exception as e:
            logger.warning(f"Multi-hop search failed for query '{followup_query}': {e}")
            continue
    
    return {
        "results": all_results,
        "search_log": search_log,
        "total_hops": len(all_results)
    }

def _combine_multihop_results(multihop_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine les résultats multi-hop en une réponse cohérente
    """
    if not multihop_data or not multihop_data.get("results"):
        return {
            "text": "Aucune information trouvée via recherche multi-hop.",
            "documents_used": [],
            "multihop_summary": {"hops": 0, "queries": []}
        }
    
    # Collecte tous les documents trouvés
    all_docs = []
    all_texts = []
    
    for result_data in multihop_data["results"]:
        result = result_data.get("result", {})
        
        # Texte principal
        text = result.get("text", "")
        if text and text not in all_texts:
            all_texts.append(text)
        
        # Documents sources
        docs = result.get("documents_used", [])
        for doc in docs:
            if doc not in all_docs:
                all_docs.append(doc)
    
    # Synthèse des textes
    combined_text = "\n\n".join(all_texts) if all_texts else "Informations limitées disponibles."
    
    # Métadonnées multi-hop
    multihop_summary = {
        "hops": multihop_data["total_hops"],
        "queries": multihop_data["search_log"],
        "primary_result": bool(any(r["type"] == "primary" for r in multihop_data["results"])),
        "followup_results": sum(1 for r in multihop_data["results"] if r["type"] == "followup")
    }
    
    return {
        "text": combined_text,
        "documents_used": all_docs[:8],  # Limite pour éviter surcharge
        "multihop_summary": multihop_summary
    }

# 🆕 ENHANCED RAG PROMPTING POUR COT

def _build_enhanced_rag_context(question: str, rag_content: str, entities: Dict[str, Any], 
                               complexity_info: Dict[str, Any]) -> str:
    """
    Construit un contexte RAG enrichi pour questions complexes
    """
    context_parts = []
    
    # Contexte de base
    context_parts.append(f"QUESTION UTILISATEUR: {question}")
    
    # Entités extraites
    if entities:
        entity_summary = []
        for key, value in entities.items():
            if value is not None:
                entity_summary.append(f"{key}: {value}")
        if entity_summary:
            context_parts.append(f"CONTEXTE TECHNIQUE: {', '.join(entity_summary)}")
    
    # Niveau de complexité
    if complexity_info:
        complexity_level = complexity_info.get("level", "simple")
        complexity_factors = complexity_info.get("factors", [])
        context_parts.append(f"COMPLEXITÉ DÉTECTÉE: {complexity_level}")
        if complexity_factors:
            context_parts.append(f"FACTEURS: {', '.join(complexity_factors)}")
    
    # Contenu RAG
    context_parts.append(f"INFORMATIONS TECHNIQUES DISPONIBLES:\n{rag_content}")
    
    return "\n\n".join(context_parts)

def _get_enhanced_rag_instruction(intent: str, complexity_level: str) -> str:
    """
    Retourne des instructions spécialisées selon l'intention et la complexité
    """
    base_instruction = "Réponds de manière professionnelle en utilisant les informations techniques fournies."
    
    if complexity_level == "simple":
        return base_instruction
    
    # Instructions pour questions complexes
    complex_instructions = {
        "HealthDiagnosis": (
            "Analyse les symptômes étape par étape. "
            "Propose un diagnostic différentiel avec 2-3 hypothèses prioritaires. "
            "Recommande les actions immédiates les plus sûres."
        ),
        "OptimizationStrategy": (
            "Évalue la situation actuelle vs les standards. "
            "Identifie les 3 leviers d'amélioration prioritaires par impact/faisabilité. "
            "Propose un plan d'action avec timeline réaliste."
        ),
        "Economics": (
            "Analyse coûts/bénéfices avec chiffres quand disponibles. "
            "Propose 2-3 scénarios (conservateur/réaliste/optimiste). "
            "Donne des recommandations économiques concrètes."
        ),
        "TroubleshootingMultiple": (
            "Identifie les liens entre les différents problèmes. "
            "Hiérarchise les actions par urgence et impact. "
            "Propose une approche systémique pour résoudre l'ensemble."
        )
    }
    
    return complex_instructions.get(intent, 
        "Analyse la question de manière structurée. "
        "Considère les multiples facteurs en jeu. "
        "Propose des solutions hiérarchisées et justifiées."
    )

# --------------------------------
# 1) Chemin "in-memory" via app.state (code original conservé)
# --------------------------------
def _get_embedder_from_app(species_name: str):
    """
    Récupère l'embedder préchargé par main.app (si dispo).
    Retourne None si indisponible.
    """
    try:
        from app.main import app  # l'instance FastAPI créée dans main.py
        if species_name == "broiler" and getattr(app.state, "rag_broiler", None):
            return app.state.rag_broiler
        if species_name == "layer" and getattr(app.state, "rag_layer", None):
            return app.state.rag_layer
        # global par défaut
        if getattr(app.state, "rag", None):
            return app.state.rag
    except Exception:
        pass
    return None

def _search_with_embedder(embedder, query: str, k: int = 12):
    """
    Essaie plusieurs API possibles pour ton FastRAGEmbedder.
    Doit retourner (docstore(list[dict]), scored(list[(idx, score)])).
    """
    # 1) API directe .search(query, k) -> liste d'objets {content/text, metadata, score}
    if hasattr(embedder, "search") and callable(embedder.search):
        try:
            results = embedder.search(query, top_k=k)
            # standardiser en (docstore, scored)
            docstore = []
            scored = []
            for r in results:
                # r peut être dict ou objet; on accède prudemment
                text = getattr(r, "text", None) or getattr(r, "content", None) or (r.get("text") if isinstance(r, dict) else None) or (r.get("content") if isinstance(r, dict) else None)
                meta = getattr(r, "metadata", None) or (r.get("metadata") if isinstance(r, dict) else None) or {}
                score = getattr(r, "score", None) or (r.get("score") if isinstance(r, dict) else None) or 0.0
                docstore.append({"text": text, "metadata": meta})
                scored.append((len(docstore)-1, float(score)))
            return docstore, scored
        except Exception:
            pass

    # 2) Si l'embedder expose un retriever avec .search(...)
    retr = getattr(embedder, "retriever", None)
    if retr and hasattr(retr, "search") and callable(retr.search):
        try:
            results = retr.search(query, top_k=k)
            docstore, scored = [], []
            for r in results:
                text = getattr(r, "text", None) or getattr(r, "content", None) or (r.get("text") if isinstance(r, dict) else None) or (r.get("content") if isinstance(r, dict) else None)
                meta = getattr(r, "metadata", None) or (r.get("metadata") if isinstance(r, dict) else None) or {}
                score = getattr(r, "score", None) or (r.get("score") if isinstance(r, dict) else None) or 0.0
                docstore.append({"text": text, "metadata": meta})
                scored.append((len(docstore)-1, float(score)))
            return docstore, scored
        except Exception:
            pass

    # 3) Sinon, pas d'API de recherche → None
    return None, None

# --------------------------------
# 2) Fallback FAISS sur disque (code original conservé)
# --------------------------------
def _faiss_paths(index_name: str) -> Dict[str, str]:
    """
    Résout les chemins disque. On essaie d'abord les variables ENV spécifiques,
    sinon RAG_INDEX_ROOT (défaut: ./rag_index), puis ./rag_index/<index_name>.
    """
    # Overrides explicites
    env_map = {
        "global": os.getenv("RAG_INDEX_GLOBAL"),
        "broiler": os.getenv("RAG_INDEX_BROILER"),
        "layer": os.getenv("RAG_INDEX_LAYER"),
    }
    base = env_map.get(index_name)
    if base and os.path.isdir(base):
        return {
            "faiss": os.path.join(base, "index.faiss"),
            "pkl": os.path.join(base, "index.pkl"),
            "meta": os.path.join(base, "meta.json"),
        }

    root = os.getenv("RAG_INDEX_ROOT", "rag_index")
    folder = os.path.join(root, index_name)
    return {
        "faiss": os.path.join(folder, "index.faiss"),
        "pkl": os.path.join(folder, "index.pkl"),
        "meta": os.path.join(folder, "meta.json"),
    }

def _faiss_load(index_name: str):
    if faiss is None:
        raise RuntimeError("FAISS n'est pas disponible sur cette instance API.")
    paths = _faiss_paths(index_name)
    if not (os.path.exists(paths["faiss"]) and os.path.exists(paths["pkl"])):
        raise FileNotFoundError(f"Index FAISS introuvable pour {index_name}: {paths}")
    index = faiss.read_index(paths["faiss"])
    with open(paths["pkl"], "rb") as f:
        docstore = pickle.load(f)
    manifest = {}
    if os.path.exists(paths["meta"]):
        try:
            with open(paths["meta"], "r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception:
            pass
    return index, docstore, manifest

def _faiss_search(index, query_vec: np.ndarray, k: int = 12):
    D, I = index.search(query_vec.reshape(1, -1), k)
    # L2 → on convertit en score = -distance (plus haut = mieux)
    return [(int(i), -float(d)) for i, d in zip(I[0], D[0]) if i >= 0]

# --------------------------------
# 🆕 ENHANCED MAIN FUNCTION
# --------------------------------
def answer_with_rag(question: str, entities: Dict[str, Any], intent=None, 
                   complexity_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    🆕 Version enrichie avec support Chain-of-Thought et Multi-Hop Reasoning
    """
    idx_name = _pick_species_index_name(entities)
    query = _numeric_first_query(question, entities)
    
    # 🆕 Déterminer si multi-hop est nécessaire
    use_multihop = _should_use_multihop(complexity_info or {}, intent or "")
    logger.info(f"🔍 RAG mode: {'multi-hop' if use_multihop else 'standard'} for intent={intent}")
    
    # 1) Essai via app.state.* (embedder déjà chargé par main.py)
    embedder = _get_embedder_from_app(idx_name)
    if embedder is not None and getattr(embedder, "has_search_engine", lambda: False)():
        
        if use_multihop:
            # 🆕 Multi-hop reasoning avec embedder
            def search_fn(q):
                docstore, scored = _search_with_embedder(embedder, q, k=8)
                if docstore and scored:
                    scored = _rerank_table_first(scored, docstore, table_boost=1.2)
                    top_ids = [i for i, _ in scored[:3]]
                    sources = _format_sources(top_ids, docstore)
                    answer_text = _synthesize_answer(top_ids, docstore)
                    return {
                        "text": answer_text,
                        "documents_used": sources
                    }
                return None
            
            multihop_data = _multihop_search(question, entities, intent or "", search_fn)
            result = _combine_multihop_results(multihop_data)
            
            # 🆕 Contexte enrichi pour CoT
            if complexity_info and complexity_info.get("needs_cot", False):
                enhanced_context = _build_enhanced_rag_context(
                    question, result["text"], entities, complexity_info
                )
                result["enhanced_context"] = enhanced_context
                result["rag_instruction"] = _get_enhanced_rag_instruction(
                    intent or "", complexity_info.get("level", "simple")
                )
            
            result.update({
                "index_used": idx_name,
                "manifest": {"provider": "app.state.multihop", "multihop": True},
                "search_strategy": "multihop"
            })
            return result
        
        else:
            # Mode standard (code original adapté)
            docstore, scored = _search_with_embedder(embedder, query, k=12)
            if docstore is not None and scored is not None and len(docstore) > 0:
                scored = _rerank_table_first(scored, docstore, table_boost=1.2)
                top_ids = [i for i, _ in scored[:5]]
                sources = _format_sources(top_ids, docstore)
                answer_text = _synthesize_answer(top_ids, docstore)
                
                result = {
                    "text": answer_text,
                    "documents_used": sources,
                    "index_used": idx_name,
                    "manifest": {"provider": "app.state", "documents": len(docstore)},
                    "search_strategy": "standard"
                }
                
                # 🆕 Enrichissement pour CoT
                if complexity_info and complexity_info.get("needs_cot", False):
                    result["enhanced_context"] = _build_enhanced_rag_context(
                        question, answer_text, entities, complexity_info
                    )
                    result["rag_instruction"] = _get_enhanced_rag_instruction(
                        intent or "", complexity_info.get("level", "simple")
                    )
                
                return result

    # 2) Fallback FAISS disque (code original adapté)
    try:
        index, docstore, manifest = _faiss_load(idx_name)
    except Exception as e:
        return {
            "text": f"Aucune source disponible pour l'index '{idx_name}' ({e}).",
            "documents_used": [],
            "index_used": idx_name,
            "manifest": {"provider": "disk", "error": str(e)},
            "search_strategy": "error"
        }

    # Embedding de la requête : on essaye d'utiliser l'embedder global si dispo
    qvec: Optional[np.ndarray] = None
    if embedder is not None and hasattr(embedder, "embed"):
        try:
            vec = embedder.embed(query)
            qvec = np.asarray(vec, dtype="float32")
            qvec = qvec / (np.linalg.norm(qvec) + 1e-8)
        except Exception:
            qvec = None

    if qvec is None:
        # dernier recours : on ne sait pas encoder ici
        return {
            "text": "RAG non disponible: aucun encoder configuré pour la requête (fallback FAISS impossible).",
            "documents_used": [],
            "index_used": idx_name,
            "manifest": {"provider": "disk", "note": "embed_query_missing"},
            "search_strategy": "error"
        }

    if use_multihop:
        # 🆕 Multi-hop avec FAISS
        def search_fn(q):
            try:
                vec = embedder.embed(q)
                qvec_local = np.asarray(vec, dtype="float32")
                qvec_local = qvec_local / (np.linalg.norm(qvec_local) + 1e-8)
                scored_local = _faiss_search(index, qvec_local, k=8)
                scored_local = _rerank_table_first(scored_local, docstore, table_boost=1.2)
                top_ids = [i for i, _ in scored_local[:3]]
                sources = _format_sources(top_ids, docstore)
                answer_text = _synthesize_answer(top_ids, docstore)
                return {
                    "text": answer_text,
                    "documents_used": sources
                }
            except Exception:
                return None
        
        multihop_data = _multihop_search(question, entities, intent or "", search_fn)
        result = _combine_multihop_results(multihop_data)
        
        # 🆕 Enrichissement CoT
        if complexity_info and complexity_info.get("needs_cot", False):
            result["enhanced_context"] = _build_enhanced_rag_context(
                question, result["text"], entities, complexity_info
            )
            result["rag_instruction"] = _get_enhanced_rag_instruction(
                intent or "", complexity_info.get("level", "simple")
            )
        
        result.update({
            "index_used": idx_name,
            "manifest": {"provider": "disk.multihop", **manifest},
            "search_strategy": "multihop"
        })
        return result
    
    else:
        # Mode standard FAISS
        scored = _faiss_search(index, qvec, k=12)
        scored = _rerank_table_first(scored, docstore, table_boost=1.2)
        top_ids = [i for i, _ in scored[:5]]
        sources = _format_sources(top_ids, docstore)
        answer_text = _synthesize_answer(top_ids, docstore)

        result = {
            "text": answer_text,
            "documents_used": sources,
            "index_used": idx_name,
            "manifest": {"provider": "disk", **manifest},
            "search_strategy": "standard"
        }
        
        # 🆕 Enrichissement CoT
        if complexity_info and complexity_info.get("needs_cot", False):
            result["enhanced_context"] = _build_enhanced_rag_context(
                question, answer_text, entities, complexity_info
            )
            result["rag_instruction"] = _get_enhanced_rag_instruction(
                intent or "", complexity_info.get("level", "simple")
            )
        
        return result

# 🆕 NOUVELLES FONCTIONS UTILITAIRES

def get_rag_capabilities() -> Dict[str, Any]:
    """
    Retourne les capacités disponibles du moteur RAG
    """
    return {
        "multihop_reasoning": True,
        "enhanced_prompting": True,
        "table_boost": True,
        "complexity_aware": True,
        "supported_strategies": ["standard", "multihop"],
        "max_hops": 3,
        "supported_intents": [
            "HealthDiagnosis", "OptimizationStrategy", "TroubleshootingMultiple",
            "ProductionAnalysis", "MultiFactor", "Economics"
        ]
    }

def test_rag_multihop(question: str = "Test multihop", entities: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Test rapide des capacités multi-hop
    """
    test_entities = entities or {"species": "broiler", "line": "ross308", "age_days": 21}
    test_complexity = {"score": 40, "level": "medium", "needs_cot": True, "factors": ["causal_reasoning"]}
    
    try:
        result = answer_with_rag(
            question=question,
            entities=test_entities,
            intent="HealthDiagnosis",
            complexity_info=test_complexity
        )
        
        return {
            "status": "success",
            "strategy_used": result.get("search_strategy"),
            "multihop_summary": result.get("multihop_summary"),
            "enhanced_context_generated": "enhanced_context" in result,
            "instruction_generated": "rag_instruction" in result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }