# app/api/v1/pipeline/rag_engine.py
"""
RAGEngine - Multi-index species routing (broiler/layer/global) + tenant-aware + UI style hints
- Charge 3 index séparés: <RAG_INDEX_ROOT>/<tenant>/<species> (ou <RAG_INDEX_ROOT>/<species> sans tenant)
- Détecte l'espèce à partir du contexte/question
- Sélectionne l'index correspondant; fallback vers 'global' si doute
- Option de mix (espèce + global) si rappel faible
- Fallback OpenAI si aucun doc
- Prend en compte context["ui_style"] pour forcer un rendu (bullets/minimal/weight_only)
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.openai_utils import safe_chat_completion

try:
    from rag.embedder import FastRAGEmbedder, create_optimized_embedder  # type: ignore
except Exception:
    FastRAGEmbedder = None  # type: ignore
    create_optimized_embedder = None  # type: ignore

logger = logging.getLogger(__name__)


class _IndexClient:
    """Wrapper petit mais robuste: charge un index FAISS, expose .search(query, k)."""

    def __init__(self, index_path: str, model_name: str, sim_threshold: float, normalize_queries: bool, debug: bool):
        self.index_path = index_path
        self.embedder: Optional[FastRAGEmbedder] = None
        self.ok = False

        if create_optimized_embedder is not None:
            self.embedder = create_optimized_embedder(
                model_name=model_name,
                similarity_threshold=sim_threshold,
                normalize_queries=normalize_queries,
                debug=debug,
            )
        elif FastRAGEmbedder is not None:
            self.embedder = FastRAGEmbedder(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name=model_name,
                cache_embeddings=True,
                max_workers=int(os.getenv("RAG_MAX_WORKERS", "2")),
                debug=debug,
                similarity_threshold=sim_threshold,
                normalize_queries=normalize_queries,
            )

        if self.embedder is None:
            logger.error("No embedder available.")
            return

        try:
            self.ok = bool(self.embedder.load_index(index_path))
            if self.ok:
                logger.info("📦 Loaded index: %s", index_path)
            else:
                logger.warning("Failed to load index: %s", index_path)
        except Exception as e:
            logger.error("Error loading index %s: %s", index_path, e)
            self.ok = False

    def search(self, query: str, k: int) -> List[Dict[str, Any]]:
        if not self.ok or self.embedder is None:
            return []
        try:
            return self.embedder.search(query, k=k)
        except Exception as e:
            logger.error("Search error on %s: %s", self.index_path, e)
            return []


class RAGEngine:
    def __init__(self, k: int = 6) -> None:
        self.k = int(os.getenv("RAG_TOP_K", str(k)))
        self.model_name = os.getenv("RAG_EMBED_MODEL", "all-MiniLM-L6-v2")
        self.sim_threshold = float(os.getenv("RAG_SIM_THRESHOLD", "0.20"))
        self.normalize_queries = True
        self.debug = True

        self.index_root = Path(os.getenv("RAG_INDEX_ROOT", "rag_index"))
        self.mix_with_global = True  # mélange 70/30 si peu de résultats
        self.mix_min_docs = max(2, self.k // 3)

        # Statut interne (pour /system/status)
        self._ready = True

    # ------------------ Species detection ------------------ #
    def _infer_species(self, question: str, context: Optional[Dict[str, Any]]) -> Optional[str]:
        ctx = context or {}
        sp = (ctx.get("species") or ctx.get("espece") or ctx.get("production_type") or "").lower()
        if any(x in sp for x in ["broiler", "chair"]):
            return "broiler"
        if any(x in sp for x in ["layer", "pondeuse"]):
            return "layer"

        breed = (ctx.get("breed") or ctx.get("race") or "").lower()
        if any(x in breed for x in ["ross", "cobb", "hubbard", "broiler", "308", "500"]):
            return "broiler"
        if any(x in breed for x in ["lohmann", "hy-line", "w36", "w-36", "w80", "w-80", "layer"]):
            return "layer"

        q = (question or "").lower()
        if any(x in q for x in ["pondeuse", "layer", "lohmann", "hy-line", "ponte", "w36", "w80"]):
            return "layer"
        if any(x in q for x in ["broiler", "poulet de chair", "ross 308", "cobb 500"]):
            return "broiler"
        return None

    # ------------------ Index selection ------------------ #
    def _tenant_from_context(self, context: Optional[Dict[str, Any]]) -> Optional[str]:
        ctx = context or {}
        t = ctx.get("tenant_id") or ctx.get("tenant") or ctx.get("organisation")
        return str(t) if t else None

    def _index_path(self, species: str, tenant: Optional[str]) -> Path:
        if tenant:
            return self.index_root / tenant / species
        return self.index_root / species

    def _load_index_client(self, species: str, tenant: Optional[str]) -> _IndexClient:
        idx_path = self._index_path(species, tenant)
        return _IndexClient(
            index_path=str(idx_path),
            model_name=self.model_name,
            sim_threshold=self.sim_threshold,
            normalize_queries=self.normalize_queries,
            debug=self.debug,
        )

    # ------------------ Retrieval ------------------ #
    def _retrieve_from_species(self, question: str, tenant: Optional[str], species: str, k: int) -> List[Dict[str, Any]]:
        client = self._load_index_client(species, tenant)
        return client.search(question, k) if client.ok else []

    def _as_docs(self, hits: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        docs: List[Dict[str, str]] = []
        for h in hits or []:
            md = (h.get("metadata") or {})
            src = md.get("file_path") or md.get("source") or md.get("path") or md.get("filename") or "unknown_source"
            text = (h.get("text") or "").strip()
            docs.append({"content": text, "source": str(src)})
        return docs

    # ------------------ Public API ------------------ #
    def generate_answer(self, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ui = (context or {}).get("ui_style") or {}
        style = str(ui.get("style") or "standard")
        fmt = str(ui.get("format") or "auto")
        weight_only = bool(ui.get("weight_only") or False)

        logger.info("▶️ RAG.generate_answer | style=%s | format=%s | weight_only=%s | Q.len=%s",
                    style, fmt, weight_only, len(question or ""))

        tenant = self._tenant_from_context(context)
        species = self._infer_species(question, context)  # may be None
        primary = species if species in {"broiler", "layer"} else "global"
        logger.info("🧭 Routing | tenant=%s | inferred_species=%s | primary=%s", tenant, species, primary)

        # 1) Try primary index
        primary_hits = self._retrieve_from_species(question, tenant, primary, self.k)
        docs = self._as_docs(primary_hits)
        if primary != "global":
            logger.info("🔎 Retrieved | species=%s | hits=%s", primary, len(primary_hits))

        # 2) Optional mix with global if weak
        if self.mix_with_global and primary != "global" and len(docs) < self.mix_min_docs:
            global_hits = self._retrieve_from_species(question, tenant, "global", max(2, self.k // 2))
            docs = (docs or []) + self._as_docs(global_hits)

        # 3) Hard fallback to global if still empty
        if not docs and primary != "global":
            global_hits2 = self._retrieve_from_species(question, tenant, "global", self.k)
            docs = self._as_docs(global_hits2)

        # 4) If no docs at all -> OpenAI fallback (général)
        if not docs:
            return self._openai_fallback(question, context, style=style, fmt=fmt, weight_only=weight_only)

        # 5) RAG prompt
        prompt = self._build_rag_prompt(question, context, docs, style=style, fmt=fmt, weight_only=weight_only)
        try:
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=900 if style != "minimal" else 500,
            )
            content = (resp.choices[0].message.content or "").strip()
            if not content:
                content = "Aucune réponse exploitable n’a été générée à partir des documents — veuillez reformuler."

            out = {
                "response": content,
                "source": "rag_enhanced",
                "documents_used": len(docs),
                "warning": None,
                # on expose aussi "sources" pour l’API — mêmes infos que citations
                "sources": self._build_citations(docs),
                "citations": self._build_citations(docs),
            }
            logger.info("✅ OpenAI RAG ok | content_len=%s | cites=%s", len(content), len(out["citations"]))
            return out
        except Exception as e:
            logger.error("OpenAI error on RAG: %s", e)
            return {
                "response": f"Documents trouvés ({len(docs)}) mais erreur de génération. Réessayez plus tard.",
                "source": "rag_error",
                "documents_used": len(docs),
                "warning": f"Erreur traitement RAG: {e}",
                "sources": self._build_citations(docs),
                "citations": self._build_citations(docs),
            }

    # ------------------ Fallback & prompts ------------------ #
    def _openai_fallback(self, question: str, context: Optional[Dict[str, Any]],
                         style: str = "standard", fmt: str = "auto", weight_only: bool = False) -> Dict[str, Any]:
        prompt = self._build_fallback_prompt(question, context, style=style, fmt=fmt, weight_only=weight_only)
        try:
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=700 if style != "minimal" else 400,
            )
            content = (resp.choices[0].message.content or "").strip()
            if not content:
                content = "Réponse générale (sans source) indisponible pour le moment. Peux-tu préciser la lignée et l’âge ?"
            out = {
                "response": content,
                "source": "openai_fallback",
                "documents_used": 0,
                "warning": "Réponse générale : aucun document spécialisé pertinent n'a été trouvé.",
                "sources": [],
                "citations": [],
            }
            logger.info("✅ OpenAI fallback ok | content_len=%s", len(content))
            return out
        except Exception as e:
            logger.error("OpenAI fallback error: %s", e)
            return {
                "response": "Je rencontre un problème technique pour répondre. Veuillez réessayer.",
                "source": "error_fallback",
                "documents_used": 0,
                "warning": f"Erreur technique: {e}",
                "sources": [],
                "citations": [],
            }

    # ------------------ Prompt builders ------------------ #
    def _build_rag_prompt(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        docs: List[Dict[str, str]],
        style: str = "standard",
        fmt: str = "auto",
        weight_only: bool = False,
    ) -> str:
        doc_lines: List[str] = []
        for i, d in enumerate(docs, 1):
            content = (d.get("content") or "").strip()
            if len(content) > 600:
                content = content[:600] + "..."
            source = d.get("source") or "unknown_source"
            doc_lines.append(f"[Doc {i} | {source}]\n{content}")
        docs_block = "\n\n".join(doc_lines)

        # Consigne de forme
        form = self._format_preamble(style=style, fmt=fmt, weight_only=weight_only, context=context)

        missing_info = self._identify_missing_context(context)

        return f"""Tu es un expert avicole (broilers & pondeuses). Utilise en priorité les extraits fournis.

QUESTION
{question}

CONTEXTE DISPONIBLE
{context if context else "—"}

DOCUMENTS SPÉCIALISÉS
{docs_block}

CONSIGNE DE FOND
1) Appuie-toi d'abord sur les documents ci-dessus.
2) Si une info manque, complète prudemment par les bonnes pratiques reconnues et indique clairement ce qui vient des docs.
3) Sois clair, précis, opérationnel. Mentionne les hypothèses si nécessaire.

{missing_info}

CONSIGNE DE FORME
{form}

Réponds en français.
"""

    def _build_fallback_prompt(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        style: str = "standard",
        fmt: str = "auto",
        weight_only: bool = False,
    ) -> str:
        form = self._format_preamble(style=style, fmt=fmt, weight_only=weight_only, context=context)
        missing_info = self._identify_missing_context(context)
        return f"""Tu es un expert avicole.

QUESTION
{question}

CONTEXTE DISPONIBLE
{context if context else "—"}

SITUATION
Aucun document spécialisé n'a été retrouvé par le RAG.

CONSIGNE DE FOND
1) Donne une réponse générale prudente (bonnes pratiques).
2) Explique les variations possibles (lignée, sexe, âge, etc.).
3) Propose 1–2 questions de clarification si pertinent.

{missing_info}

CONSIGNE DE FORME
{form}

Réponds en français et indique clairement qu'il s'agit d'une réponse générale (sans source documentaire).
"""

    # ------------------ Utils ------------------ #
    def _format_preamble(self, style: str, fmt: str, weight_only: bool, context: Optional[Dict[str, Any]]) -> str:
        """
        Contraint la forme de la réponse (bullets/minimal, poids d’abord…)
        """
        bullets = (fmt == "bullets")
        lines: List[str] = []
        if style == "minimal" or bullets:
            lines.append("- Réponds en 2–4 puces maximum.")
        else:
            lines.append("- Réponse courte et structurée.")
        if weight_only:
            # Si on cherche un poids, mettre la cible en premier
            age = (context or {}).get("age_jours")
            prefix_age = f" ({age} j)" if age else ""
            lines.append(f"- Si la question concerne le poids: commence par **la fourchette cible{prefix_age}**.")
            lines.append("- Pas de digression (température, lumière, repro, etc.).")
            lines.append("- Si lignée/sexes/âge manquent, termine par une courte question de clarification.")
        else:
            lines.append("- Si des infos clés manquent, termine par 1 question de clarification.")
        return "\n".join(lines)

    def _identify_missing_context(self, context: Optional[Dict[str, Any]]) -> str:
        ctx = context or {}
        missing = []
        if not (ctx.get("race") or ctx.get("breed")):
            missing.append("la lignée (Ross, Cobb, Lohmann, etc.)")
        if not (ctx.get("sexe") or ctx.get("sex_category")):
            missing.append("le sexe (mâle, femelle, mixte)")
        if not (ctx.get("age_jours") or ctx.get("age_phase")):
            missing.append("l'âge précis (jours/semaine)")
        if missing:
            return "INFORMATIONS MANQUANTES\n- " + "\n- ".join(missing)
        return "CONTEXTE jugé suffisant."

    def _build_citations(self, docs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        cites: List[Dict[str, str]] = []
        for d in docs:
            source = d.get("source") or "unknown_source"
            snippet = (d.get("content") or "").replace("\n", " ")[:120]
            cites.append({"source": source, "snippet": snippet})
        return cites

    # Pour /system/status
    def is_ready(self) -> bool:
        return self._ready
