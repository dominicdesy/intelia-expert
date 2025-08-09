# app/api/v1/pipeline/rag_engine.py
"""
RAGEngine - Multi-index species routing (broiler/layer/global) + tenant-aware
- Charge 3 index séparés: <RAG_INDEX_ROOT>/<tenant>/<species> (ou <RAG_INDEX_ROOT>/<species> sans tenant)
- Détecte l'espèce à partir du contexte/question
- Sélectionne l'index correspondant; fallback vers 'global' si doute
- Option de mix (espèce + global) si rappel faible
- Fallback OpenAI si aucun doc

Extensions:
- style: "minimal" | "standard" | "detailed"
- output_format: "auto" | "bullets"  (force la réponse en puces)
- weight_only: True pour ne parler QUE du poids (pas d'autres sujets)
- 🔎 debug: logs détaillés des décisions & tailles de contenu
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
    """Petit wrapper qui charge un index FAISS à un chemin donné et expose .search(query, k)."""

    def __init__(self, index_path: str, model_name: str, sim_threshold: float, normalize_queries: bool, debug: bool):
        self.index_path = index_path
        self.embedder: Optional[FastRAGEmbedder] = None
        self.ok = False

        # Crée un embedder optimisé si dispo; sinon fallback constructeur direct
        if create_optimized_embedder is not None:
            self.embedder = create_optimized_embedder(
                model_name=model_name,
                similarity_threshold=sim_threshold,
                normalize_queries=normalize_queries,
                debug=debug,
            )
            logger.debug("🔧 Embedder=create_optimized | model=%s | thr=%.3f | norm=%s", model_name, sim_threshold, normalize_queries)
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
            logger.debug("🔧 Embedder=FastRAGEmbedder | model=%s | thr=%.3f | norm=%s", model_name, sim_threshold, normalize_queries)

        if self.embedder is None:
            logger.error("❌ No embedder available.")
            return

        try:
            self.ok = bool(self.embedder.load_index(index_path))
            if self.ok:
                logger.info("📦 Loaded index: %s", index_path)
            else:
                logger.warning("⚠️ Failed to load index: %s", index_path)
        except Exception as e:
            logger.error("❌ Error loading index %s: %s", index_path, e)
            self.ok = False

    def search(self, query: str, k: int) -> List[Dict[str, Any]]:
        if not self.ok or self.embedder is None:
            logger.debug("🔎 Search skipped (index not ok) | path=%s", self.index_path)
            return []
        try:
            res = self.embedder.search(query, k=k)
            logger.debug("🔎 Search ok | path=%s | k=%d | hits=%d", self.index_path, k, len(res or []))
            return res
        except Exception as e:
            logger.error("❌ Search error on %s: %s", self.index_path, e)
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
        logger.debug(
            "🧩 RAGEngine init | k=%d | embed_model=%s | thr=%.2f | index_root=%s | mix=%s",
            self.k, self.model_name, self.sim_threshold, self.index_root, self.mix_with_global
        )

    # ------------------ Species detection ------------------ #
    def _infer_species(self, question: str, context: Optional[Dict[str, Any]]) -> Optional[str]:
        ctx = context or {}
        sp = (ctx.get("species") or ctx.get("espece") or "").lower()
        if any(x in sp for x in ["broiler", "chair"]):
            logger.debug("🔮 infer_species via context.species=%s → broiler", sp)
            return "broiler"
        if any(x in sp for x in ["layer", "pondeuse"]):
            logger.debug("🔮 infer_species via context.species=%s → layer", sp)
            return "layer"

        breed = (ctx.get("breed") or ctx.get("race") or "").lower()
        if any(x in breed for x in ["ross", "cobb", "hubbard", "broiler"]):
            logger.debug("🔮 infer_species via context.breed=%s → broiler", breed)
            return "broiler"
        if any(x in breed for x in ["lohmann", "hy-line", "w36", "w-36", "w80", "w-80", "layer"]):
            logger.debug("🔮 infer_species via context.breed=%s → layer", breed)
            return "layer"

        q = (question or "").lower()
        if any(x in q for x in ["pondeuse", "layer", "lohmann", "hy-line", "ponte", "w36", "w80"]):
            logger.debug("🔮 infer_species via question → layer")
            return "layer"
        if any(x in q for x in ["broiler", "poulet de chair", "ross 308", "cobb 500"]):
            logger.debug("🔮 infer_species via question → broiler")
            return "broiler"
        logger.debug("🔮 infer_species → None (default to global)")
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
        logger.debug("📁 Load index client | species=%s | tenant=%s | path=%s", species, tenant, idx_path)
        return _IndexClient(
            index_path=str(idx_path),
            model_name=self.model_name,
            sim_threshold=self.sim_threshold,
            normalize_queries=self.normalize_queries,
            debug=self.debug,
        )

    # ------------------ Retrieval ------------------ #
    def _retrieve_from_species(self, question: str, tenant: Optional[str], species: str, k: int) -> List[Dict[str, Any]]:
        logger.debug("🔎 Retrieve | species=%s | tenant=%s | k=%d", species, tenant, k)
        client = self._load_index_client(species, tenant)
        hits = client.search(question, k) if client.ok else []
        logger.info("🔎 Retrieved | species=%s | hits=%d", species, len(hits or []))
        return hits

    def _as_docs(self, hits: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        docs: List[Dict[str, str]] = []
        for h in hits or []:
            md = (h.get("metadata") or {})
            src = md.get("file_path") or md.get("source") or md.get("path") or md.get("filename") or "unknown_source"
            text = (h.get("text") or "").strip()
            docs.append({"content": text, "source": str(src)})
        logger.debug("📄 as_docs | in=%d | out=%d", len(hits or []), len(docs))
        return docs

    # ------------------ Public API ------------------ #
    def generate_answer(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        *,
        style: str = "standard",
        output_format: str = "auto",   # "bullets" | "auto"
        weight_only: bool = False      # focus exclusif sur le poids
    ) -> Dict[str, Any]:
        """
        style: "minimal" (2–3 phrases), "standard" (3–5 phrases), "detailed" (libre).
        """
        logger.info(
            "▶️ RAG.generate_answer | style=%s | format=%s | weight_only=%s | Q.len=%d",
            style, output_format, weight_only, len(question or "")
        )

        tenant = self._tenant_from_context(context)
        species = self._infer_species(question, context)  # may be None
        primary = species if species in {"broiler", "layer"} else "global"
        logger.info("🧭 Routing | tenant=%s | inferred_species=%s | primary=%s", tenant, species, primary)

        # 1) Try primary index
        primary_hits = self._retrieve_from_species(question, tenant, primary, self.k)
        docs = self._as_docs(primary_hits)
        logger.debug("📊 Primary docs=%d", len(docs))

        # 2) Optional mix with global if weak
        if self.mix_with_global and primary != "global" and len(docs) < self.mix_min_docs:
            logger.info("➕ Mix with global (weak primary: %d < %d)", len(docs), self.mix_min_docs)
            global_hits = self._retrieve_from_species(question, tenant, "global", max(2, self.k // 2))
            docs = (docs or []) + self._as_docs(global_hits)
            logger.debug("📊 After mix docs=%d", len(docs))

        # 3) If still empty, try pure global as hard fallback
        if not docs and primary != "global":
            logger.info("🔁 Hard fallback → global only")
            global_hits2 = self._retrieve_from_species(question, tenant, "global", self.k)
            docs = self._as_docs(global_hits2)
            logger.debug("📊 Global fallback docs=%d", len(docs))

        # 4) If no docs at all -> OpenAI fallback
        if not docs:
            logger.warning("📭 No documents found → OpenAI fallback")
            return self._openai_fallback(
                question, context, style=style, output_format=output_format, weight_only=weight_only
            )

        # 5) RAG prompt (style/format/focus)
        prompt = self._build_rag_prompt(
            question, context, docs, style=style, output_format=output_format, weight_only=weight_only
        )
        logger.debug("✍️ RAG prompt | chars=%d | docs=%d", len(prompt or ""), len(docs))

        try:
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1100 if style == "minimal" else 1300,  # ↑ éviter les réponses tronquées
            )
            content = (resp.choices[0].message.content or "").strip()
            citations = self._build_citations(docs)
            logger.info("✅ OpenAI RAG ok | content_len=%d | cites=%d", len(content or ""), len(citations or []))
            return {
                "response": content,
                "source": "rag_enhanced",
                "sources": citations,          # normalisé pour DialogueManager
                "documents_used": len(docs),
                "warning": None,
                "citations": citations,
            }
        except Exception as e:
            logger.error("❌ OpenAI error on RAG: %s", e)
            citations = self._build_citations(docs)
            return {
                "response": f"Documents trouvés ({len(docs)}) mais erreur de génération. Réessayez plus tard.",
                "source": "rag_error",
                "sources": citations,
                "documents_used": len(docs),
                "warning": f"Erreur traitement RAG: {e}",
                "citations": citations,
            }

    # ------------------ Fallback & prompts ------------------ #
    def _openai_fallback(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        *,
        style: str = "standard",
        output_format: str = "auto",
        weight_only: bool = False
    ) -> Dict[str, Any]:
        prompt = self._build_fallback_prompt(
            question, context, style=style, output_format=output_format, weight_only=weight_only
        )
        logger.debug("✍️ Fallback prompt | chars=%d", len(prompt or ""))
        try:
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=900 if style == "minimal" else 1100,  # ↑ marge de sécurité
            )
            content = (resp.choices[0].message.content or "").strip()
            logger.info("✅ OpenAI fallback ok | content_len=%d", len(content or ""))
            return {
                "response": content,
                "source": "openai_fallback",
                "sources": [],
                "documents_used": 0,
                "warning": "Réponse générale : aucun document spécialisé pertinent n'a été trouvé.",
                "citations": [],
            }
        except Exception as e:
            logger.error("❌ OpenAI fallback error: %s", e)
            return {
                "response": "Je rencontre un problème technique pour répondre. Veuillez réessayer.",
                "source": "error_fallback",
                "sources": [],
                "documents_used": 0,
                "warning": f"Erreur technique: {e}",
                "citations": [],
            }

    def _build_rag_prompt(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        docs: List[Dict[str, str]],
        style: str = "standard",
        output_format: str = "auto",
        weight_only: bool = False
    ) -> str:
        doc_lines: List[str] = []
        for i, d in enumerate(docs, 1):
            content = (d.get("content") or "").strip()
            if len(content) > 600:
                content = content[:600] + "..."
            source = d.get("source") or "unknown_source"
            doc_lines.append(f"[Doc {i} | {source}]\n{content}")
        docs_block = "\n\n".join(doc_lines)
        missing_info = self._identify_missing_context(context)

        style_instruction = {
            "minimal": "Donne une réponse courte (2–3 phrases max), sans titres ni listes, avec une estimation chiffrée si possible. Évite les détails accessoires.",
            "standard": "Donne une réponse compacte (3–5 phrases), claire, sans titres ni listes. Fournis des fourchettes chiffrées et précise les hypothèses si nécessaire.",
            "detailed": "Tu peux utiliser des sous-titres et listes si utile et détailler davantage le contexte et les recommandations.",
        }.get(style, "")

        focus_instruction = (
            "CONCENTRE-TOI EXCLUSIVEMENT sur le poids visé à l’âge demandé. "
            "NE PARLE PAS d’autres sujets (température, éclairage, alimentation, biosécurité, etc.). "
        ) if weight_only else ""
        format_instruction = (
            "Formate la réponse en puces (3 puces max), sans titres ni paragraphes."
        ) if output_format == "bullets" else "Ne crée pas de titres."

        prompt = f"""Tu es un expert avicole (broilers & pondeuses). Utilise en priorité les extraits fournis.

QUESTION
{question}

CONTEXTE DISPONIBLE
{context if context else "—"}

DOCUMENTS SPÉCIALISÉS
{docs_block}

CONSIGNE
1) Appuie-toi d'abord sur les documents ci-dessus.
2) Si une info manque, complète prudemment par les bonnes pratiques reconnues et indique clairement ce qui vient des docs.
3) {focus_instruction}{style_instruction}
4) {format_instruction}
5) Mentionne les hypothèses si nécessaire et donne une fourchette chiffrée si possible.

{missing_info}

Réponds en français.
"""
        return prompt

    def _build_fallback_prompt(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        *,
        style: str = "standard",
        output_format: str = "auto",
        weight_only: bool = False
    ) -> str:
        missing_info = self._identify_missing_context(context)
        style_instruction = {
            "minimal": "Réponds en 2–3 phrases max, sans titres, avec une fourchette chiffrée si possible.",
            "standard": "Réponds en 3–5 phrases, sans titres, de manière claire et opérationnelle.",
            "detailed": "Réponds de manière détaillée, avec explications et contexte si utile.",
        }.get(style, "")
        focus_instruction = (
            "CONCENTRE-TOI EXCLUSIVEMENT sur le poids visé à l’âge demandé. "
            "NE PARLE PAS d’autres sujets (température, éclairage, alimentation, biosécurité, etc.). "
        ) if weight_only else ""
        format_instruction = (
            "Formate la réponse en puces (3 puces max), sans titres ni paragraphes."
        ) if output_format == "bullets" else "Ne crée pas de titres."
        prompt = f"""Tu es un expert avicole.

QUESTION
{question}

CONTEXTE DISPONIBLE
{context if context else "—"}

SITUATION
Aucun document spécialisé n'a été retrouvé par le RAG.

CONSIGNE
1) Donne une réponse générale prudente.
2) {focus_instruction}Explique uniquement les variations de poids possibles (lignée, sexe, âge).
3) {style_instruction}
4) {format_instruction}

{missing_info}

Réponds en français et indique clairement qu'il s'agit d'une réponse générale (sans source documentaire)."""
        return prompt

    # ------------------ Utils ------------------ #
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
            msg = "INFORMATIONS MANQUANTES\n- " + "\n- ".join(missing)
        else:
            msg = "CONTEXTE jugé suffisant."
        logger.debug("ℹ️ MissingContext | %s", msg.replace("\n", " | "))
        return msg

    def _build_citations(self, docs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        cites: List[Dict[str, str]] = []
        for d in docs:
            source = d.get("source") or "unknown_source"
            snippet = (d.get("content") or "").replace("\n", " ")[:120]
            cites.append({"source": source, "snippet": snippet})
        logger.debug("🔗 Citations built | %d", len(cites))
        return cites

    def get_status(self) -> Dict[str, Any]:
        status = {
            "index_root": str(self.index_root),
            "k": self.k,
            "embed_model": self.model_name,
            "mix_with_global": self.mix_with_global,
        }
        logger.debug("📈 RAG status | %s", status)
        return status

    def is_ready(self) -> bool:
        # simple indicateur (les index sont chargés à la volée)
        return True
