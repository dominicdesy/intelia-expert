# app/api/v1/pipeline/rag_engine.py
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.openai_utils import safe_chat_completion
from .intent_registry import get_intent_spec, derive_answer_mode, looks_numeric_first

try:
    from rag.embedder import FastRAGEmbedder, create_optimized_embedder  # type: ignore
except Exception:
    FastRAGEmbedder = None  # type: ignore
    create_optimized_embedder = None  # type: ignore

logger = logging.getLogger(__name__)

class _IndexClient:
    def __init__(self, index_path: str, model_name: str, sim_threshold: float, normalize_queries: bool, debug: bool):
        self.index_path = index_path
        self.embedder: Optional[FastRAGEmbedder] = None
        self.ok = False

        factory = create_optimized_embedder or (lambda **kw: FastRAGEmbedder(**kw))
        if factory is None:
            logger.error("No embedder factory available")
            return
        self.embedder = factory(
            model_name=model_name,
            similarity_threshold=sim_threshold,
            normalize_queries=normalize_queries,
            debug=debug,
            cache_embeddings=True,
            max_workers=int(os.getenv("RAG_MAX_WORKERS", "2")),
        )

        try:
            self.ok = bool(self.embedder.load_index(index_path)) if self.embedder else False
            if self.ok:
                logger.info("📦 Loaded index: %s", index_path)
        except Exception as e:
            logger.error("Error loading index %s: %s", index_path, e)
            self.ok = False

    def search(self, query: str, k: int) -> List[Dict[str, Any]]:
        if not self.ok or self.embedder is None:
            return []
        return self.embedder.search(query, k=k)  # type: ignore


class RAGEngine:
    def __init__(self, k: int = 6) -> None:
        self.k = int(os.getenv("RAG_TOP_K", str(k)))
        self.model_name = os.getenv("RAG_EMBED_MODEL", "all-MiniLM-L6-v2")
        self.sim_threshold = float(os.getenv("RAG_SIM_THRESHOLD", "0.20"))
        self.normalize_queries = True
        self.debug = True

        self.index_root = Path(os.getenv("RAG_INDEX_ROOT", "rag_index"))
        self._ready = True

    # ------------- helpers ------------- #
    def _tenant_from_context(self, context: Optional[Dict[str, Any]]) -> Optional[str]:
        ctx = context or {}
        t = ctx.get("tenant_id") or ctx.get("tenant") or ctx.get("organisation")
        return str(t) if t else None

    def _infer_species(self, question: str, context: Optional[Dict[str, Any]]) -> Optional[str]:
        ctx = context or {}
        sp = (ctx.get("species") or ctx.get("production_type") or ctx.get("espece") or "").lower()
        if any(x in sp for x in ["broiler", "chair"]):
            return "broiler"
        if any(x in sp for x in ["layer", "pondeuse"]):
            return "layer"
        breed = (ctx.get("line") or ctx.get("breed") or ctx.get("race") or "").lower()
        if any(x in breed for x in ["ross", "cobb", "hubbard", "broiler", "308", "500", "708"]):
            return "broiler"
        if any(x in breed for x in ["lohmann", "hy-line", "isa"]):
            return "layer"
        q = (question or "").lower()
        if any(x in q for x in ["pondeuse", "layer", "lohmann", "hy-line", "ponte", "isa"]):
            return "layer"
        if any(x in q for x in ["broiler", "poulet de chair", "ross 308", "cobb 500"]):
            return "broiler"
        return None

    def _index_path(self, species: str, tenant: Optional[str]) -> Path:
        return (self.index_root / tenant / species) if tenant else (self.index_root / species)

    def _load_index_client(self, species: str, tenant: Optional[str]) -> _IndexClient:
        return _IndexClient(
            index_path=str(self._index_path(species, tenant)),
            model_name=self.model_name,
            sim_threshold=self.sim_threshold,
            normalize_queries=self.normalize_queries,
            debug=self.debug,
        )

    # ------------- filtering ------------- #
    def _filter_hits(
        self,
        hits: List[Dict[str, Any]],
        *,
        intent: str,
        prefer_tables: bool,
        species: Optional[str],
    ) -> List[Dict[str, str]]:
        """
        Filtrage universel par métadonnées: document_type, life_stage, chunk_type(table/paragraph)
        + priorisation tables si demandé.
        """
        spec = get_intent_spec(intent)
        prefer_types: List[str] = list(spec.get("preferred_sources") or [])

        def keep(md: Dict[str, Any]) -> bool:
            life = (md.get("life_stage") or "").lower()
            doc_type = (md.get("document_type") or "").lower()
            # si chair et intent != breeders: exclure parent stock
            if species == "broiler" and "parent" in (life or doc_type):
                return False
            # si layer: garder layer docs en priorité, mais on ne filtre pas dur si vide
            return True

        tables, texts = [], []
        for h in hits or []:
            md = (h.get("metadata") or {})
            if not keep(md):
                continue
            src = md.get("file_path") or md.get("source") or md.get("path") or md.get("filename") or "unknown_source"
            text = (h.get("text") or "").strip()
            if not text:
                continue
            kind = (md.get("chunk_type") or md.get("section_type") or "").lower()
            doc_type = (md.get("document_type") or "").lower()

            item = {"content": text, "source": str(src), "kind": kind or "text", "document_type": doc_type}
            # priorité 1: sources préférées
            score_bias = 1 if (doc_type and doc_type in prefer_types) else 0
            item["__bias"] = score_bias

            if prefer_tables and "table" in kind:
                tables.append(item)
            else:
                texts.append(item)

        # Re-rank: preferred_sources → tables/texts
        ranked = sorted(tables + texts, key=lambda d: d.get("__bias", 0), reverse=True)
        for d in ranked:
            d.pop("__bias", None)
        return ranked

    # ------------- prompt builders ------------- #
    def _format_preamble(self, *, answer_mode: str, numeric_first: bool) -> str:
        lines: List[str] = []
        if any(x in answer_mode for x in ["numeric", "numbers", "table"]):
            lines.append("- Donne la valeur + unité en premier (puis plage/conditions si dispo).")
        if "procedure" in answer_mode:
            lines.append("- Donne une procédure courte (≤ 6 étapes) + paramètres clés.")
        if "table" in answer_mode:
            lines.append("- Si un tableau est disponible dans les documents, synthétise les valeurs clés.")
        if "rules" in answer_mode:
            lines.append("- Résume la règle principale en tête, puis exceptions/détails.")
        if not lines:
            lines.append("- Réponse concise, structurée.")
        if numeric_first:
            lines.append("- Évite les digressions avant le chiffre attendu.")
        return "\n".join(lines)

    def _build_rag_prompt(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        docs: List[Dict[str, str]],
        *,
        intent: str,
        answer_mode: str,
    ) -> str:
        doc_lines: List[str] = []
        for i, d in enumerate(docs, 1):
            content = (d.get("content") or "").strip()
            if len(content) > 800:
                content = content[:800] + "..."
            source = d.get("source") or "unknown_source"
            kind = (d.get("kind") or "text")
            doc_lines.append(f"[Doc {i} | {source} | {kind}]\n{content}")
        docs_block = "\n\n".join(doc_lines)

        preamble = self._format_preamble(answer_mode=answer_mode, numeric_first=looks_numeric_first(intent))
        return f"""Tu es un expert avicole. Utilise **en priorité** les extraits ci-dessous.

QUESTION
{question}

CONTEXTE
{context if context else "—"}

DOCUMENTS
{docs_block}

CONSIGNE
{preamble}

Réponds en français. Indique clairement **ce qui vient des documents** vs **bonnes pratiques** si tu extrapoles.
"""

    def _build_fallback_prompt(self, question: str, context: Optional[Dict[str, Any]], *, intent: str, answer_mode: str) -> str:
        preamble = self._format_preamble(answer_mode=answer_mode, numeric_first=looks_numeric_first(intent))
        return f"""Tu es un expert avicole. Aucun document pertinent n'a été retrouvé.

QUESTION
{question}

CONTEXTE
{context if context else "—"}

CONSIGNE
1) Donne une réponse générale prudente (bonnes pratiques reconnues).
2) Explique les variations possibles (lignée, sexe, âge, climat, équipements).
3) Propose 1 courte clarification si besoin.

FORME
{preamble}

Réponds en français et précise que **la réponse est générale (sans source)**.
"""

    # ------------- public ------------- #
    def generate_answer(self, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        intent = (context or {}).get("last_intent") or "general"
        answer_mode = derive_answer_mode(intent)

        tenant = self._tenant_from_context(context)
        species = self._infer_species(question, context)  # peut être None

        k_search = max(self.k * 3, self.k + 4)  # récupérer large puis filtrer
        prefer_tables = any(x in answer_mode for x in ["numeric", "numbers", "table"])

        logger.info(
            "▶️ RAG.generate_answer | intent=%s | answer_mode=%s | prefer_tables=%s | k=%s",
            intent, answer_mode, prefer_tables, k_search
        )

        # 1) Sélection index primaire
        primary = species if species in {"broiler", "layer"} else "global"

        def _retrieve(species_name: str, k: int) -> List[Dict[str, Any]]:
            client = self._load_index_client(species_name, tenant)
            return client.search(question, k) if client.ok else []

        hits: List[Dict[str, Any]] = []
        tried: List[str] = []

        # a) primaire
        hits = _retrieve(primary, k_search)
        tried.append(primary)

        # b) si rien ou trop peu → cross-index
        if len(hits) < self.k and primary != "global":
            hits += _retrieve("global", k_search // 2)
            tried.append("global")
        if len(hits) < self.k and species and primary != species:
            hits += _retrieve(species, k_search // 2)
            tried.append(species)

        # 2) Filtrage universel
        docs = self._filter_hits(hits, intent=intent, prefer_tables=prefer_tables, species=species)
        docs = docs[: max(self.k, 6)]

        # 3) Fallback complet
        if not docs:
            prompt = self._build_fallback_prompt(question, context, intent=intent, answer_mode=answer_mode)
            try:
                resp = safe_chat_completion(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=700,
                )
                content = (resp.choices[0].message.content or "").strip() or "Réponse générale non disponible."
                return {
                    "response": content,
                    "source": "openai_fallback",
                    "documents_used": 0,
                    "warning": "Réponse générale : aucun document filtré n'a été trouvé.",
                    "sources": [],
                    "citations": [],
                    "inferred_species": species,
                }
            except Exception as e:
                logger.error("OpenAI fallback error: %s", e)
                return {
                    "response": "Je rencontre un problème technique pour répondre. Veuillez réessayer.",
                    "source": "error_fallback",
                    "documents_used": 0,
                    "warning": f"Erreur technique: {e}",
                    "sources": [],
                    "citations": [],
                    "inferred_species": species,
                }

        # 4) Génération avec documents
        prompt = self._build_rag_prompt(question, context, docs, intent=intent, answer_mode=answer_mode)
        try:
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=900,
            )
            content = (resp.choices[0].message.content or "").strip()
            if not content:
                content = "Aucune réponse exploitable n’a été générée à partir des documents."

            cites = self._build_citations(docs)
            return {
                "response": content,
                "source": "rag_enhanced",
                "documents_used": len(docs),
                "warning": None,
                "sources": cites,
                "citations": cites,
                "inferred_species": species,
            }
        except Exception as e:
            logger.error("OpenAI error on RAG: %s", e)
            cites = self._build_citations(docs)
            return {
                "response": f"Documents trouvés ({len(docs)}) mais erreur de génération.",
                "source": "rag_error",
                "documents_used": len(docs),
                "warning": f"Erreur traitement RAG: {e}",
                "sources": cites,
                "citations": cites,
                "inferred_species": species,
            }

    def _build_citations(self, docs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        cites: List[Dict[str, str]] = []
        for d in docs:
            source = d.get("source") or "unknown_source"
            snippet = (d.get("content") or "").replace("\n", " ")[:140]
            kind = d.get("kind") or "text"
            cites.append({"source": source, "snippet": snippet, "kind": kind})
        return cites

    def is_ready(self) -> bool:
        return self._ready
