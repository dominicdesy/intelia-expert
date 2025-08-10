#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Document Parser & Index Builder (Table-first ready)

Fonctions clés :
- Détection intelligente de la config (secrets.toml, .env, env var)
- Recherche du dossier documents + création d'échantillons facultative
- Construction de l’index via EnhancedDocumentEmbedder
- Vérification explicite que metadata["chunk_type"] = "table" est préservé
- Options CLI : chemins, verbosité, ratio minimal de tables, etc.

Exemples :
  python rag/parse_documents.py --require-table-chunks --min-table-ratio 0.05
  python rag/parse_documents.py -d ./documents -i ./rag_index --verbose
"""

from __future__ import annotations

import os
import re
import sys
import toml
import json
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# --- Chemins d'import (assure import rag.* depuis ce script) ---
CURRENT_DIR = Path(__file__).parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

LOG = logging.getLogger("rag.parse_documents")


# =============== CONFIG & LOGGING ===================

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    # Réduire le bruit
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def load_openai_key() -> Optional[str]:
    """
    Priorité :
      1) ./.streamlit/secrets.toml (clé 'openai_key')
      2) ../.streamlit/secrets.toml
      3) ./.env (ligne OPENAI_API_KEY=...)
      4) os.environ['OPENAI_API_KEY']
    """
    # 1-2) secrets.toml
    for candidate in [Path(".streamlit/secrets.toml"), Path("../.streamlit/secrets.toml")]:
        if candidate.exists():
            try:
                with candidate.open("r", encoding="utf-8") as f:
                    data = toml.load(f)
                key = data.get("openai_key")
                if key:
                    LOG.info("✅ OpenAI key loaded from %s", candidate)
                    return key
                LOG.warning("openai_key not found in %s", candidate)
            except Exception as e:
                LOG.warning("Cannot parse %s: %s", candidate, e)

    # 3) .env
    env_file = Path(".env")
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"\'')
                    if key:
                        LOG.info("✅ OpenAI key loaded from .env")
                        return key
            LOG.warning("OPENAI_API_KEY not found in .env")
        except Exception as e:
            LOG.warning("Cannot read .env: %s", e)

    # 4) ENV
    key = os.getenv("OPENAI_API_KEY")
    if key:
        LOG.info("✅ OpenAI key loaded from environment")
        return key

    LOG.error("❌ No OpenAI API key found (.streamlit/secrets.toml, .env, or env var)")
    return None


# =============== DOCS & INDEX HELPERS ===================

def find_documents_path(explicit: Optional[str] = None) -> Optional[Path]:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        return p if p.exists() else None
    for candidate in [Path("documents"), Path("../documents"), Path("docs"), Path("../docs")]:
        if candidate.exists():
            return candidate.resolve()
    return None


def ensure_sample_documents(docs_path: Path) -> None:
    """
    Crée 2 fichiers d’exemple si le dossier est vide, pour tests rapides.
    """
    docs_path.mkdir(parents=True, exist_ok=True)
    if any(p.is_file() for p in docs_path.rglob("*")):
        return

    LOG.info("📝 Creating sample documents in %s", docs_path)
    sample_csv = """age,weight_g,daily_gain_g,temperature_c,feed_intake_g,fcr,humidity_pct
0,42,0,35.0,0,0.0,65
1,45,3,35.0,4,0.89,65
7,160,16,32.0,35,1.02,60
14,410,36,29.0,75,1.15,58
21,820,58,26.0,125,1.28,55
28,1450,90,23.0,180,1.35,52
35,2100,93,21.0,220,1.42,50
42,2800,100,19.0,260,1.48,50
"""
    sample_md = """# Ross 308 Performance Targets

| Week | Target BW (g) | FCR  |
|-----:|---------------:|:----:|
| 1    | 160            | 1.05 |
| 2    | 410            | 1.25 |
| 3    | 820            | 1.45 |
| 4    | 1450           | 1.62 |

Notes:
- Verify temperature ramp (32–35°C week 1).
- Increase water points if heat stress indicators appear.
"""

    (docs_path / "ross308_sample_data.csv").write_text(sample_csv, encoding="utf-8")
    (docs_path / "ross_308_targets.md").write_text(sample_md, encoding="utf-8")
    LOG.info("✅ Sample docs created: ross308_sample_data.csv, ross_308_targets.md")


def determine_index_path(explicit: Optional[str] = None) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    # Préfère ./rag_index
    for candidate in [Path("rag_index"), Path("../rag_index"), Path("index"), Path("../index")]:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate.resolve()
        except Exception:
            continue
    # Dernier recours
    return Path("rag_index").resolve()


# =============== TABLE-FIRST VERIFICATION ===================

def summarize_chunk_types(docs: List[Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for d in docs or []:
        ct = (d.metadata or {}).get("chunk_type", "unset")
        counts[ct] = counts.get(ct, 0) + 1
    return counts


def try_load_all_documents(embedder: Any, index_path: Path) -> List[Any]:
    """
    Tente plusieurs approches pour récupérer les documents indexés afin d’inspecter metadata.
    - embedder.load_all_documents(index_path)
    - embedder.vector_store.get_all() (si dispo)
    - embedder.search_documents('*', k=N) (fallback limité)
    """
    docs: List[Any] = []

    # 1) API directe
    for fn_name in ("load_all_documents", "load_documents"):
        fn = getattr(embedder, fn_name, None)
        if callable(fn):
            try:
                loaded = fn(str(index_path))
                if isinstance(loaded, list) and loaded:
                    LOG.debug("Loaded %d docs via %s()", len(loaded), fn_name)
                    return loaded
            except Exception as e:
                LOG.debug("Failure on %s(): %s", fn_name, e)

    # 2) vector_store.get_all()
    try:
        vs = getattr(embedder, "vector_store", None)
        if vs is not None:
            get_all = getattr(vs, "get_all", None)
            if callable(get_all):
                loaded = get_all()
                if isinstance(loaded, list) and loaded:
                    LOG.debug("Loaded %d docs via vector_store.get_all()", len(loaded))
                    return loaded
    except Exception as e:
        LOG.debug("vector_store.get_all() failed: %s", e)

    # 3) Fallback : effectue quelques recherches pour ramener des docs (limité)
    try:
        search = getattr(embedder, "search_documents", None)
        if callable(search):
            seen_ids = set()
            for q in ["table", "weight", "FCR", "Ross 308"]:
                try:
                    results = search(q, k=10) or []
                    for res in results:
                        # compat : (doc, score) ou dict
                        if isinstance(res, tuple) and len(res) == 2:
                            doc = res[0]
                        elif isinstance(res, dict):
                            doc = res.get("document") or res.get("doc")
                        else:
                            doc = None
                        if doc is None:
                            continue
                        doc_id = (getattr(doc, "metadata", {}) or {}).get("source_file") or id(doc)
                        if doc_id in seen_ids:
                            continue
                        seen_ids.add(doc_id)
                        docs.append(doc)
                except Exception:
                    continue
            if docs:
                LOG.debug("Collected %d docs via search fallback", len(docs))
                return docs
    except Exception as e:
        LOG.debug("Search fallback failed: %s", e)

    return docs


def check_table_flag_preserved(
    embedder: Any,
    index_path: Path,
    require: bool = False,
    min_ratio: float = 0.0
) -> Tuple[int, int, Dict[str, int]]:
    """
    Charge les documents indexés et vérifie la conservation de chunk_type='table'.
    - require=True : échoue si aucun doc 'table' détecté
    - min_ratio : avertit/échoue si le ratio de 'table' < min_ratio
    Retourne (total_docs, table_docs, counts_par_type)
    """
    docs = try_load_all_documents(embedder, index_path)
    total = len(docs)
    counts = summarize_chunk_types(docs)
    table_count = counts.get("table", 0)

    LOG.info("🔍 Table-first check → %s", json.dumps(counts, ensure_ascii=False))
    LOG.info("   %d/%d documents ont chunk_type='table'", table_count, total)

    if require and table_count == 0:
        raise RuntimeError(
            "Aucun document avec chunk_type='table'. "
            "Vérifier table_parsers, metadata_enrichment et document_parsers."
        )

    if min_ratio > 0 and total > 0:
        ratio = table_count / float(total)
        if ratio < min_ratio:
            msg = (
                f"Ratio de documents 'table' {ratio:.2%} < seuil {min_ratio:.2%}. "
                "Vérifiez que la détection table-first est bien active."
            )
            if require:
                raise RuntimeError(msg)
            else:
                LOG.warning(msg)

    return total, table_count, counts


# =============== MAIN PIPELINE ===================

def build_and_check(
    documents_path: Path,
    index_path: Path,
    openai_key: str,
    require_table_chunks: bool,
    min_table_ratio: float,
    chunk_size: int,
    chunk_overlap: int,
    hybrid: bool,
    intelligent_routing: bool,
) -> None:
    LOG.info("🚀 Initializing EnhancedDocumentEmbedder")
    try:
        from rag.embedder import EnhancedDocumentEmbedder  # type: ignore
    except Exception as e:
        LOG.error("❌ Cannot import rag.embedder.EnhancedDocumentEmbedder: %s", e)
        LOG.error("   Current working dir: %s", Path.cwd())
        LOG.error("   Ensure you run from project root or adjust PYTHONPATH.")
        sys.exit(1)

    try:
        embedder = EnhancedDocumentEmbedder(
            openai_api_key=openai_key,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            use_hybrid_search=hybrid,
            use_intelligent_routing=intelligent_routing,
        )
    except Exception as e:
        LOG.error("❌ Error initializing EnhancedDocumentEmbedder: %s", e)
        sys.exit(1)

    LOG.info("📚 Documents: %s", documents_path)
    LOG.info("💾 Index path: %s", index_path)

    try:
        success = embedder.build_vector_store(
            documents_path=str(documents_path),
            index_path=str(index_path),
        )
    except Exception as e:
        LOG.error("❌ build_vector_store failed: %s", e)
        sys.exit(1)

    if not success:
        LOG.error("❌ Document processing failed (build_vector_store returned False)")
        sys.exit(1)

    LOG.info("✅ Documents processed and index created at %s", index_path)

    # Vérif table-first (conservation du champ dans l’index)
    try:
        total, table_count, _ = check_table_flag_preserved(
            embedder=embedder,
            index_path=index_path,
            require=require_table_chunks,
            min_ratio=min_table_ratio,
        )
        if total == 0:
            LOG.warning("Aucun document détecté après indexation (total=0).")
    except Exception as e:
        LOG.error("❌ Table-first verification failed: %s", e)
        sys.exit(1)

    # Petits tests de recherche
    LOG.info("🔎 Running smoke-test queries…")
    for q in ["Ross 308 weight targets", "temperature management", "feed conversion ratio", "table"]:
        try:
            results = embedder.search_documents(q, k=2)
            if results:
                # compat : (doc, score) or dict
                if isinstance(results[0], tuple) and len(results[0]) == 2:
                    doc, score = results[0]
                elif isinstance(results[0], dict):
                    doc, score = results[0].get("document") or results[0].get("doc"), results[0].get("score", 0.0)
                else:
                    doc, score = None, 0.0
                src = (getattr(doc, "metadata", {}) or {}).get("source_file", "unknown") if doc else "unknown"
                LOG.info("   • '%s' → best: %s (score=%.3f)", q, src, float(score or 0.0))
            else:
                LOG.info("   • '%s' → no results", q)
        except Exception as e:
            LOG.debug("Search error on '%s': %s", q, e)

    LOG.info("🎉 Success. RAG index ready.")


# =============== CLI ===================

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Parse documents and build RAG index (Table-first).")
    p.add_argument("-d", "--documents", type=str, default=None, help="Path to documents folder.")
    p.add_argument("-i", "--index", type=str, default=None, help="Path to index folder.")
    p.add_argument("--create-samples", action="store_true", help="Create sample docs if none found.")
    p.add_argument("--require-table-chunks", action="store_true",
                   help="Fail if no chunk has metadata['chunk_type']=='table'.")
    p.add_argument("--min-table-ratio", type=float, default=float(os.getenv("MIN_TABLE_RATIO", "0.0")),
                   help="Warn/fail if table chunks ratio < this threshold (0.0..1.0).")
    p.add_argument("--chunk-size", type=int, default=500, help="Chunk size for embedder.")
    p.add_argument("--chunk-overlap", type=int, default=50, help="Chunk overlap for embedder.")
    p.add_argument("--no-hybrid", action="store_true", help="Disable hybrid search.")
    p.add_argument("--no-intelligent-routing", action="store_true", help="Disable intelligent routing.")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    setup_logging(args.verbose)

    print("=" * 64)
    print("📦 RAG DOCUMENT PARSER — Table-first")
    print("=" * 64)

    openai_key = load_openai_key()
    if not openai_key:
        print("\n💡 Configure your OpenAI key via .streamlit/secrets.toml, .env, or env var.")
        sys.exit(1)

    docs_path = find_documents_path(args.documents)
    if not docs_path:
        if args.create_samples:
            # crée le dossier local ./documents
            docs_path = Path("documents").resolve()
            ensure_sample_documents(docs_path)
        else:
            print("❌ Documents folder not found. Use --documents or --create-samples.")
            sys.exit(1)
    else:
        if args.create_samples:
            ensure_sample_documents(docs_path)

    index_path = determine_index_path(args.index)

    build_and_check(
        documents_path=docs_path,
        index_path=index_path,
        openai_key=openai_key,
        require_table_chunks=args.require_table_chunks,
        min_table_ratio=max(0.0, min(1.0, args.min_table_ratio)),
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        hybrid=not args.no_hybrid,
        intelligent_routing=not args.no_intelligent_routing,
    )


if __name__ == "__main__":
    main()
