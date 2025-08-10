#!/usr/bin/env python3
"""
RAG Index Builder — Multi-tenant + Multi-species
Construit 3 index par tenant: global, broiler, layer
- Filtrage par chemin: /species/broiler/ et /species/layer/
- Index root: RAG_INDEX_ROOT (def: rag_index)
- Documents root: DOCUMENTS_ROOT (def: documents)

AMÉLIORATIONS (non-intrusives, compatibles avec la version stable):
- Enrichissement des métadonnées de index.pkl après build (optionnel):
    * species, life_stage, document_type, chunk_type, section
- Contrôlé par ENV: RAG_ENRICH_METADATA=1 (par défaut ON)
- Journalisation accrue et robustesse accrue des erreurs
"""

import os
import sys
import json
import time
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ------------------------- Config ------------------------- #
RAG_INDEX_ROOT = Path(os.getenv("RAG_INDEX_ROOT", "rag_index"))
DOCUMENTS_ROOT = Path(os.getenv("DOCUMENTS_ROOT", "documents"))

SPECIES_DIR_HINTS = {
    "broiler": "/species/broiler/",
    "layer": "/species/layer/",
}
SPECIES_LIST = ["global", "broiler", "layer"]

# Enrichissement des métadonnées post-build (sécurisé, optionnel)
RAG_ENRICH_METADATA = os.getenv("RAG_ENRICH_METADATA", "1").strip() not in {"0", "false", "False", ""}


def setup_environment() -> Path:
    """Ensure we run from project root and sys.path is set."""
    project_root = Path.cwd()
    # Allow running from subfolder (e.g., rag/)
    if (project_root / "app").exists():
        pass
    elif (project_root.parent / "app").exists():
        os.chdir(project_root.parent)
        project_root = Path.cwd()

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    logger.info("Project root: %s", project_root)
    return project_root


def discover_tenants(doc_root: Path) -> List[str]:
    """Discover tenants under DOCUMENTS_ROOT."""
    tenants: List[str] = []
    if not doc_root.exists():
        logger.warning("Documents root not found: %s", doc_root)
        return tenants

    for p in doc_root.iterdir():
        if p.is_dir() and (p.name.startswith("tenant_") or p.name in {"shared", "public"}):
            tenants.append(p.name)
    if not tenants:
        # fallback: consider docs directly under DOCUMENTS_ROOT as "public"
        any_file = any(doc_root.rglob("*"))
        tenants = ["public"] if any_file else []

    logger.info("Discovered %d tenant(s): %s", len(tenants), tenants)
    return tenants


def iter_candidate_files(root: Path) -> List[Path]:
    """List all files under root (non-hidden)."""
    files = [p for p in root.rglob("*") if p.is_file() and not p.name.startswith(".")]
    return files


def filter_by_species(files: List[Path], species: str) -> List[Path]:
    """Filter files by species using path hints. 'global' means no species restriction."""
    if species == "global":
        return files

    hint = SPECIES_DIR_HINTS.get(species)
    if not hint:
        return []

    norm = lambda s: str(s).replace("\\", "/")
    return [f for f in files if hint in norm(f)]


def make_temp_view(filtered_files: List[Path], tmp_dir: Path) -> None:
    """
    Create a temporary "view" of filtered files using hardlinks when possible, else copy.
    Some vector builders expect a folder; this avoids duplicating big trees.
    """
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for src in filtered_files:
        # Structure plate : le parser conserve généralement le chemin source dans les métadonnées
        dst = tmp_dir / src.name
        try:
            os.link(src, dst)  # hardlink (fast, space-efficient on same FS)
        except Exception:
            try:
                shutil.copy2(src, dst)  # fallback copy
            except Exception as e:
                logger.warning("Skip file (cannot link/copy): %s | %s", src, e)


def build_species_index_for_tenant(tenant_id: str, tenant_docs_dir: Path, species: str, embedder) -> Dict[str, Any]:
    """
    Build an index for a single tenant + species.
    Uses FastRAGEmbedder.build_vector_store(documents_path=<tmp_view>, index_path=<target_dir>).
    """
    all_files = iter_candidate_files(tenant_docs_dir)
    species_files = filter_by_species(all_files, species)

    # For 'global', we EXCLUDE species-tagged files to keep it truly generic (optional but cleaner):
    if species == "global":
        bro_hint = SPECIES_DIR_HINTS["broiler"]
        lay_hint = SPECIES_DIR_HINTS["layer"]
        norm = lambda s: str(s).replace("\\", "/")
        species_files = [f for f in all_files if (bro_hint not in norm(f) and lay_hint not in norm(f))]

    logger.info("Tenant '%s' — species '%s': %d files", tenant_id, species, len(species_files))
    if not species_files:
        return {"success": False, "tenant": tenant_id, "species": species, "error": "No files for species."}

    # Create a temp view folder to feed the builder
    tmp_view = Path(".rag_build_tmp") / tenant_id / species
    make_temp_view(species_files, tmp_view)

    # Target index dir: rag_index/<tenant>/<species>
    index_dir = RAG_INDEX_ROOT / tenant_id / species
    index_dir.mkdir(parents=True, exist_ok=True)

    # Try preferred API(s)
    try:
        if hasattr(embedder, "build_vector_store"):
            result = embedder.build_vector_store(
                documents_path=str(tmp_view),
                index_path=str(index_dir),
            )
        elif hasattr(embedder, "process_documents"):
            # Some implementations accept a tenant_id and infer paths internally; store under our index_dir
            result = embedder.process_documents(
                documents_path=str(tmp_view),
                tenant_id=f"{tenant_id}:{species}",
                force_rebuild=True,
                index_path=str(index_dir),
            )
        else:
            # Fallback: try a generic ingest->save
            if hasattr(embedder, "ingest_folder") and hasattr(embedder, "save_index"):
                embedder.ingest_folder(str(tmp_view))
                embedder.save_index(str(index_dir))
                result = {"status": "success", "documents_processed": len(species_files), "total_chunks": None, "processing_time": 0}
            else:
                raise RuntimeError("Embedder has no supported build method (build_vector_store/process_documents/ingest_folder).")

        status_ok = (result or {}).get("status") == "success"
        if status_ok:
            # Enrichissement post-build (optionnel et sécurisé)
            if RAG_ENRICH_METADATA:
                maybe_enrich_index_metadata(index_dir)

            return {
                "success": True,
                "tenant": tenant_id,
                "species": species,
                "documents_processed": result.get("documents_processed", len(species_files)),
                "total_chunks": result.get("total_chunks", None),
                "processing_time": result.get("processing_time", None),
                "index_path": str(index_dir),
            }
        else:
            return {"success": False, "tenant": tenant_id, "species": species, "error": (result or {}).get("message", "Unknown error")}
    finally:
        # Clean temp view
        try:
            shutil.rmtree(tmp_view, ignore_errors=True)
        except Exception:
            pass


def verify_index(index_path: Path) -> bool:
    """Basic verification: existence of a FAISS/PKL pair or embedder-reported availability."""
    faiss_file = index_path / "index.faiss"
    pkl_file = index_path / "index.pkl"
    ok = faiss_file.exists() or pkl_file.exists() or any(index_path.glob("*.faiss")) or any(index_path.glob("*.pkl"))
    if ok:
        logger.info("Index looks present: %s", index_path)
    else:
        logger.warning("Index missing/invalid: %s", index_path)
    return ok


def create_build_summary(results: List[Dict[str, Any]], started_at: float, outfile: Path) -> Dict[str, Any]:
    summary = {
        "build_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_duration_s": round(time.time() - started_at, 2),
        "total_jobs": len(results),
        "successes": len([r for r in results if r.get("success")]),
        "failures": len([r for r in results if not r.get("success")]),
        "details": results,
    }
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Build summary -> %s", outfile)
    return summary


# ----------------------- Nouvel enrichisseur ----------------------- #
def _load_index_pkl(index_dir: Path) -> Optional[List[Dict[str, Any]]]:
    pkl = index_dir / "index.pkl"
    if not pkl.exists():
        return None
    try:
        import pickle  # local import pour minimiser l’empreinte
        with open(pkl, "rb") as f:
            data = pickle.load(f)
        if isinstance(data, list):
            return data
        # cas dict {id: {text, metadata}}
        if isinstance(data, dict):
            out: List[Dict[str, Any]] = []
            for key, val in data.items():
                if isinstance(val, dict):
                    out.append({"id": val.get("id", key), "text": val.get("text") or val.get("content", ""), "metadata": val.get("metadata", {})})
                elif isinstance(val, str):
                    out.append({"id": key, "text": val, "metadata": {}})
            return out
    except Exception as e:
        logger.warning("Cannot load index.pkl for enrichment: %s", e)
    return None


def _save_index_pkl(index_dir: Path, docs: List[Dict[str, Any]]) -> bool:
    pkl = index_dir / "index.pkl"
    try:
        import pickle
        with open(pkl, "wb") as f:
            pickle.dump(docs, f)
        return True
    except Exception as e:
        logger.warning("Cannot save enriched index.pkl: %s", e)
        return False


def _safe_enrich_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Version inline de l'enrichisseur (copie sans dépendance externe).
    Ajoute species, life_stage, document_type, chunk_type, section quand possible.
    """
    try:
        m = dict(meta or {})
        path = " ".join(str(m.get(k, "")) for k in ("file_path", "path", "source", "filename")).lower()

        # species
        if not m.get("species"):
            if any(x in path for x in ("broiler", "ross", "cobb", "hubbard")):
                m["species"] = "broiler"
            elif any(x in path for x in ("layer", "lohmann", "hy-line", "isa")):
                m["species"] = "layer"

        # life_stage
        if not m.get("life_stage"):
            if "parent stock" in path or "breeder" in path:
                m["life_stage"] = "parent_stock"
            elif any(x in path for x in ("broiler", "growout", "fattening")):
                m["life_stage"] = "broiler"

        # document_type
        if not m.get("document_type"):
            if any(x in path for x in ("performance objectives", "performance_objectives", "objectifs de performance")):
                m["document_type"] = "performance_objectives"
            elif "handbook" in path or "guide" in path or "manual" in path:
                # heuristique selon espèce
                m["document_type"] = "broiler_handbook" if m.get("species") == "broiler" else "layer_handbook"
            elif "regulation" in path or "reglement" in path or "cahier des charges" in path:
                m["document_type"] = "regulations"

        # chunk_type
        if not m.get("chunk_type"):
            m["chunk_type"] = "table" if "table" in path else "paragraph"

        # section
        if not m.get("section"):
            import re
            sec = re.findall(r"(section\s+\d+(?:\.\d+)?)", path)
            if sec:
                m["section"] = sec[0]

        return m
    except Exception:
        return dict(meta or {})


def maybe_enrich_index_metadata(index_dir: Path) -> None:
    """
    Post-traitement sans risque: si index.pkl existe, enrichit chaque chunk.metadata.
    N'affecte pas FAISS; le RAG lira ces champs pour filtrer/réordonner.
    """
    docs = _load_index_pkl(index_dir)
    if not docs:
        logger.info("No index.pkl to enrich at %s (skipping).", index_dir)
        return

    changed = 0
    for d in docs:
        md = d.get("metadata") or {}
        new_md = _safe_enrich_metadata(md)
        if new_md != md:
            d["metadata"] = new_md
            changed += 1

    if changed:
        ok = _save_index_pkl(index_dir, docs)
        if ok:
            logger.info("Metadata enriched for %s: %d/%d chunks updated.", index_dir, changed, len(docs))
        else:
            logger.warning("Failed to persist enriched metadata for %s.", index_dir)
    else:
        logger.info("Metadata enrichment: nothing to change in %s.", index_dir)


# ------------------------------ Main ------------------------------ #
def main() -> bool:
    start = time.time()
    project_root = setup_environment()

    # Import embedder
    try:
        from rag.embedder import FastRAGEmbedder
    except Exception as e:
        logger.error("Cannot import FastRAGEmbedder: %s", e)
        return False

    embedder = FastRAGEmbedder(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name=os.getenv("RAG_EMBED_MODEL", "all-MiniLM-L6-v2"),
        cache_embeddings=True,
        max_workers=int(os.getenv("RAG_MAX_WORKERS", "2")),
        debug=True,
        similarity_threshold=float(os.getenv("RAG_SIM_THRESHOLD", "0.20")),
        normalize_queries=True,
    )

    # Compat: certaines implémentations exposent _check_dependencies()
    if hasattr(embedder, "_check_dependencies") and not embedder._check_dependencies():  # type: ignore[attr-defined]
        logger.error("Missing dependencies. Try: pip install sentence-transformers faiss-cpu numpy")
        return False

    tenants = discover_tenants(DOCUMENTS_ROOT)
    if not tenants:
        logger.error("No tenants discovered under %s", DOCUMENTS_ROOT)
        return False

    jobs: List[Dict[str, Any]] = []
    for tenant in tenants:
        tenant_docs = DOCUMENTS_ROOT / tenant
        if not tenant_docs.exists():
            logger.warning("Skip tenant %s (no docs dir)", tenant)
            continue

        for species in SPECIES_LIST:
            res = build_species_index_for_tenant(tenant, tenant_docs, species, embedder)
            jobs.append(res)
            if res.get("success"):
                verify_index(Path(res["index_path"]))

    # Write summary (one file for whole build)
    summary_path = RAG_INDEX_ROOT / "build_summary.json"
    create_build_summary(jobs, start, summary_path)

    ok = any(r.get("success") for r in jobs)
    logger.info("Build completed. Success=%s", ok)
    return ok


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
