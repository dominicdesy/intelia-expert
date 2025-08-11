# -*- coding: utf-8 -*-
"""
Enhanced RAG Index Builder (CLI) — table-first + metadata enrichment

Presets (exemples) :
  # Dossier Ross 308 complet (toutes pages)
  python -m rag.build_rag `
    --src "C:\\intelia_gpt\\documents\\public\\species\\broiler\\breeds\\ross_308_broiler" `
    --out "C:\\intelia_gpt\\intelia-expert\\backend\\public" `
    --species broiler_ross308_full `
    --exts ".pdf" `
    --pdf-providers "pdftotext,pypdfium2,pymupdf,router" `
    --chunk-size 2000 --min-chunk-length 80 --max-pages 0 `
    --timeout-per-file 120 `
    --enhanced-metadata --enable-quality-filter --scan-pdf `
    --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
import json
import time
import pickle
import shutil
import subprocess
import platform
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional, Iterable

import numpy as np


# ----------------------------- Logging --------------------------------- #
def log(msg: str) -> None:
    print(msg, flush=True)


# ------------------------ Normalisation util --------------------------- #
def _normalize_text(txt: str) -> str:
    # déhyphénation “brood-\n ing” → “brooding”
    txt = re.sub(r"-\s*\n", "", txt)
    # lignes → phrase
    txt = re.sub(r"\s*\n\s*", " ", txt)
    # espaces multiples
    txt = re.sub(r"\s{2,}", " ", txt).strip()
    return txt


# --------------------- Enhanced file iteration ------------------------- #
def _iter_files_local(root: str, allowed_exts: Tuple[str, ...], recursive: bool = True) -> Iterable[str]:
    """Liste les fichiers (triés) en respectant un filtre d'extensions (.pdf, .txt, ...)"""
    p = Path(root)
    allowed = {e.lower() for e in allowed_exts} if allowed_exts else set()

    if p.is_file():
        if not allowed or p.suffix.lower() in allowed:
            yield str(p)
        return
    if not p.exists():
        return

    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}

    def ok_file(fp: Path) -> bool:
        if fp.name.startswith(".") or fp.suffix.lower() == ".tmp":
            return False
        return (not allowed) or (fp.suffix.lower() in allowed)

    results: List[str] = []
    if recursive:
        for dp, dirs, fns in os.walk(p):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fn in fns:
                fp = Path(dp) / fn
                if ok_file(fp):
                    results.append(str(fp))
    else:
        for child in p.iterdir():
            if child.is_file() and ok_file(child):
                results.append(str(child))

    for fp in sorted(results):
        yield fp


# --------- Metadata enrichment (graceful fallback if module absent) ----- #
try:
    from rag.parsers.metadata_enrichment import enhanced_enrich_metadata
except Exception:
    try:
        from rag.metadata_enrichment import enhanced_enrich_metadata  # type: ignore
    except Exception:
        def enhanced_enrich_metadata(chunks: List[Dict[str, Any]], species: str) -> List[Dict[str, Any]]:
            return chunks


# --------------------- Table-first enhanced chunker -------------------- #
def _enhanced_chunk_text(
    txt: str,
    chunk_size: int,
    base_meta: Dict[str, Any],
    min_chunk_length: int = 80
) -> List[Dict[str, Any]]:
    """
    Table-first:
      - Détecte les blocs sous forme de tableau (≥3 colonnes sur ≥40% des lignes, colonnes séparées par 2+ espaces ou tab ; ou marqué par '|')
      - Si table → on conserve la mise en page (retours ligne, espaces multiples), CHUNK UNIQUE, meta['chunk_type']="table"
      - Sinon → normalisation légère puis découpe par ~chunk_size mots
    """
    raw = txt or ""
    if not raw.strip():
        return []

    # --- Détection de tableau AVANT toute normalisation ---
    lines = [L.rstrip() for L in raw.splitlines() if L.strip()]
    is_table = False
    if lines:
        import re as _re
        col_counts = [len([p for p in _re.split(r"\s{2,}|\t", L) if p]) for L in lines]
        multi_col_lines = sum(1 for c in col_counts if c >= 3)
        if multi_col_lines >= max(3, int(0.4 * len(lines))):
            is_table = True
        if not is_table:
            pipe_lines = sum(1 for L in lines if "|" in L)
            if pipe_lines >= max(2, len(lines) // 3):
                is_table = True

    if is_table:
        import re as _re
        table_txt = _re.sub(r"-\s*\n", "", raw).strip()  # déhyphénation uniquement
        meta = dict(base_meta)
        meta.setdefault("chunk_type", "table")
        return [{"text": table_txt, "metadata": meta}]

    # --- Texte normal : normalisation complète + découpe ---
    norm = _normalize_text(raw)
    if not norm:
        return []

    chunks: List[Dict[str, Any]] = []
    words = norm.split(" ")
    buf: List[str] = []
    cur_len = 0

    for w in words:
        if not w:
            continue
        buf.append(w)
        cur_len += 1 + len(w)
        if cur_len >= chunk_size:
            piece = " ".join(buf).strip()
            if len(piece) >= min_chunk_length:
                chunks.append({"text": piece, "metadata": dict(base_meta)})
            buf = []
            cur_len = 0

    if buf:
        piece = " ".join(buf).strip()
        if len(piece) >= min_chunk_length:
            chunks.append({"text": piece, "metadata": dict(base_meta)})

    return chunks


# ---------------------- PDF health scan (optional) --------------------- #
@dataclass
class PdfScanResult:
    path: str
    copy_restricted: bool
    redaction_annots: int
    text_ratio: float
    max_image_ratio: float


def _scan_pdf_health(fp: str) -> Optional[PdfScanResult]:
    try:
        import fitz  # PyMuPDF
    except Exception:
        return None
    try:
        doc = fitz.open(fp)
    except Exception:
        return None

    redactions = 0
    text_chars = 0
    image_area_max = 0.0
    page_area_sum = 0.0

    for page in doc:
        try:
            annots = page.annots()
            if annots:
                for a in annots:
                    if a.type[0] == 17:  # redaction
                        redactions += 1
        except Exception:
            pass
        try:
            textpage = page.get_text("text")
            text_chars += len(textpage or "")
        except Exception:
            pass
        try:
            w, h = page.rect.width, page.rect.height
            page_area_sum += (w * h)
            imgs = page.get_images(full=True) or []
            image_area_max = max(image_area_max, min(1.0, len(imgs) * 0.1))
        except Exception:
            pass

    copy_restricted = False
    try:
        perms = doc.permissions
        if perms is not None:
            copy_restricted = (perms & 4) == 0  # 4 = copy allowed
    except Exception:
        pass

    try:
        doc.close()
    except Exception:
        pass

    text_ratio = float(text_chars) / max(1.0, page_area_sum) if page_area_sum > 0 else 0.0
    return PdfScanResult(
        path=fp,
        copy_restricted=copy_restricted,
        redaction_annots=redactions,
        text_ratio=text_ratio,
        max_image_ratio=image_area_max
    )


# --------------------- Auto-clean redaction (optional) ----------------- #
def _auto_clean_if_needed(fp: str, scan: Optional[PdfScanResult], out_dir: Path) -> str:
    if not scan or scan.redaction_annots <= 0:
        return fp
    try:
        import fitz
    except Exception:
        return fp
    try:
        doc = fitz.open(fp)
    except Exception:
        return fp
    try:
        for page in doc:
            try:
                page.apply_redactions()
            except Exception:
                pass
        clean_path = str(out_dir / (Path(fp).stem + ".clean.pdf"))
        doc.save(clean_path)
        try:
            doc.close()
        except Exception:
            pass
        return clean_path
    except Exception:
        try:
            doc.close()
        except Exception:
            pass
        return fp


# ---------------------- Providers availability helper ------------------ #
def _pdf_available() -> bool:
    try:
        import fitz  # noqa
        return True
    except Exception:
        return False


# ---------------------- Provider: pdftotext (Poppler) ------------------- #
def _extract_pdftotext(fp: str, chunk_size: int, min_chunk_length: int, timeout_per_file: int = 60) -> Optional[List[Dict[str, Any]]]:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    try:
        p = subprocess.run(
            [exe, "-layout", "-enc", "UTF-8", "-q", fp, "-"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout_per_file
        )
        txt = p.stdout.decode("utf-8", errors="ignore")
        # IMPORTANT : on passe le RAW au chunker (table-first); la normalisation se fera si non-table
        return _enhanced_chunk_text(txt, chunk_size, {
            "source_file": fp,
            "extraction": "pdftotext",
        }, min_chunk_length)
    except Exception as e:
        log(f"       · pdftotext failed on {fp}: {e}")
        return None


# ---------------------- Provider: pypdfium2 (PDFium) -------------------- #
def _extract_pypdfium2(fp: str, chunk_size: int, max_pages: int = 0, min_chunk_length: int = 80) -> Optional[List[Dict[str, Any]]]:
    try:
        import pypdfium2 as pdfium
    except Exception:
        return None
    try:
        doc = pdfium.PdfDocument(fp)
    except Exception:
        return None

    chunks: List[Dict[str, Any]] = []
    total = len(doc)
    if max_pages and total > max_pages:
        total = max_pages

    try:
        for i in range(total):
            try:
                page = doc[i]
                txtpage = page.get_textpage()
                txt = txtpage.get_text_bounded() or ""
                if not txt.strip():
                    continue
                page_meta = {
                    "source_file": fp,
                    "page": i + 1,
                    "total_pages": len(doc),
                    "extraction": "pypdfium2"
                }
                # IMPORTANT : passer le RAW au chunker (table-first)
                chunks.extend(_enhanced_chunk_text(txt, chunk_size, page_meta, min_chunk_length))
            except Exception:
                continue
    except Exception:
        pass
    try:
        doc.close()
    except Exception:
        pass
    return chunks or []


# ---------------------- Provider: pymupdf (MuPDF) ----------------------- #
def _extract_pymupdf(fp: str, chunk_size: int, max_pages: int = 0, min_chunk_length: int = 80) -> Optional[List[Dict[str, Any]]]:
    if not _pdf_available():
        return None
    import fitz
    try:
        doc = fitz.open(fp)
    except Exception:
        return None

    chunks: List[Dict[str, Any]] = []
    total = doc.page_count
    if max_pages and total > max_pages:
        total = max_pages

    try:
        for i in range(total):
            try:
                page = doc.load_page(i)
                # blocks pour garder un minimum de structure (colonnes → espaces multiples)
                try:
                    blocks = page.get_text("blocks") or []
                    blocks.sort(key=lambda b: (b[1], b[0]))  # tri vertical
                    parts = []
                    for (x0, y0, x1, y1, text, block_no, block_type) in blocks:
                        if text:
                            parts.append(text)
                    txt = "\n".join(parts).strip()
                except Exception:
                    txt = page.get_text("text") or ""

                if not txt:
                    continue
                page_meta = {
                    "source_file": fp,
                    "page": i + 1,
                    "total_pages": doc.page_count,
                    "extraction": "pymupdf"
                }
                # IMPORTANT : passer le RAW au chunker (table-first)
                chunks.extend(_enhanced_chunk_text(txt, chunk_size, page_meta, min_chunk_length))
            except Exception:
                continue
    except Exception:
        pass
    try:
        doc.close()
    except Exception:
        pass
    return chunks or []


# ---------------------- Router (external enhanced) ---------------------- #
def _run_enhanced_router_with_timeout(
    fp: str, species: str, timeout_sec: int, enhanced_metadata: bool
) -> Tuple[str, Optional[str], Optional[List[Dict[str, Any]]]]:
    cmd = [sys.executable, "-m", "rag.parse_documents", "--file", fp, "--species", species]
    if enhanced_metadata:
        cmd.append("--enhanced")
    try:
        p = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec
        )
        if p.returncode != 0:
            return "error", f"router non-zero exit ({p.returncode}): {p.stderr[:200].decode('utf-8', 'ignore')}", None
        try:
            data = json.loads(p.stdout.decode("utf-8", "ignore") or "{}")
        except Exception as e:
            return "error", f"router JSON decode error: {e}", None
        if isinstance(data, dict) and data.get("status") == "ok":
            chunks = data.get("chunks") or []
            fixed: List[Dict[str, Any]] = []
            for ch in chunks:
                t = str(ch.get("text", "") or "")
                if not t.strip():
                    continue
                meta = dict(ch.get("metadata", {}) or {})
                # NE PAS normaliser ici : laisser la table-first décider
                fixed.append({"text": t, "metadata": meta})
            return "ok", None, fixed
        else:
            return data.get("status", "error"), data.get("error") or None, None
    except subprocess.TimeoutExpired:
        return "timeout", "router timeout", None
    except Exception as e:
        return "error", str(e), None


# --------------- Provider cascade & quality assessment ----------------- #
def _try_enhanced_providers_for_pdf(
    fp: str, species: str, providers: List[str],
    chunk_size: int, max_pages: int, timeout_router: int,
    enhanced_metadata: bool = True, min_chunk_length: int = 80
) -> Tuple[str, Optional[List[Dict[str, Any]]], Optional[str]]:
    last_err: Optional[str] = None
    for prov in providers:
        prov = prov.strip().lower()
        try:
            if prov == "pdftotext":
                chunks = _extract_pdftotext(fp, chunk_size, min_chunk_length, timeout_router)
                if chunks:
                    return prov, chunks, None
            elif prov == "pypdfium2":
                chunks = _extract_pypdfium2(fp, chunk_size, max_pages=max_pages, min_chunk_length=min_chunk_length)
                if chunks:
                    return prov, chunks, None
            elif prov == "pymupdf":
                chunks = _extract_pymupdf(fp, chunk_size, max_pages=max_pages, min_chunk_length=min_chunk_length)
                if chunks:
                    return prov, chunks, None
            elif prov == "router":
                status, err, chunks = _run_enhanced_router_with_timeout(
                    fp, species, timeout_router, enhanced_metadata
                )
                if status == "ok" and chunks:
                    return prov, chunks, None
                elif status != "ok":
                    last_err = err or status
            else:
                log(f"       · unknown provider '{prov}', skipping")
        except Exception as e:
            last_err = str(e)
            continue

    return "none", None, last_err


# ----------------------- Embeddings & FAISS I/O ------------------------ #
def _load_model(name: str):
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(name, device="cpu")
    except Exception as e:
        log(f"❌ Cannot load embedding model '{name}': {e}")
        sys.exit(1)


def _have_faiss() -> bool:
    try:
        import faiss  # noqa: F401
        return True
    except Exception:
        return False


def _embed(model, texts: List[str], batch_size: int = 64) -> np.ndarray:
    embs = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embs.astype("float32", copy=False)


def _write_faiss(embs: np.ndarray, out_path: Path) -> None:
    import faiss
    dim = int(embs.shape[1])
    index = faiss.IndexFlatIP(dim)  # cosine sur vecteurs normalisés
    index.add(embs)
    faiss.write_index(index, str(out_path))


def _enhanced_save_meta(
    out_dir: Path, species: str, model_name: str,
    n_files: int, n_chunks: int, files_sample: List[str],
    pdf_scan_summary: Dict[str, int] | None = None,
    quality_stats: Dict[str, Any] | None = None,
    enhanced_features: bool = True,
    tables_found: int = 0
) -> None:
    meta = {
        "species": species,
        "model_name": model_name,
        "files_indexed": n_files,
        "chunks_indexed": n_chunks,
        "files_sample": files_sample,
        "pdf_scan_summary": pdf_scan_summary or {},
        "quality_stats": quality_stats or {},
        "enhanced_features": enhanced_features,
        "tables_found": tables_found,
        "version": "1.1",
    }
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# --------------------------- Quality filter ---------------------------- #
def _quality_filter(chunks: List[Dict[str, Any]], min_len: int = 80) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    kept: List[Dict[str, Any]] = []
    removed = 0
    for ch in chunks:
        t = (ch.get("text") or "").strip()
        if len(t) >= min_len:
            kept.append(ch)
        else:
            removed += 1
    stats = {"removed": removed, "kept": len(kept)}
    return kept, stats


# ------------------------------ CLI parse ------------------------------ #
def _parse_args():
    p = argparse.ArgumentParser(description="Enhanced RAG vector index builder with table-first parsing and metadata.")
    p.add_argument("--src", required=True, help="Document file or directory")
    p.add_argument("--out", required=True, help="Output root directory (indexes saved under <out>/<species>/)")
    p.add_argument("--species", required=True, help="global|broiler|layer|... (free text)")
    p.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2",
                   help="Sentence-Transformers model name")
    p.add_argument("--exts", default=".pdf,.txt,.md,.html,.htm,.csv,.xlsx,.xls",
                   help="Comma-separated list of extensions to include")
    p.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True,
                   help="Recursively traverse subfolders (default: True)")
    p.add_argument("--verbose", action="store_true", default=False,
                   help="Print per-file extraction details")

    # Scans & cleaning
    p.add_argument("--scan-pdf", dest="scan_pdf", action=argparse.BooleanOptionalAction, default=True,
                   help="Enhanced PDF health scan and write analysis CSV (default: True)")
    p.add_argument("--auto-clean-redactions", action="store_true", default=False,
                   help="Apply redactions and save a clean copy if redaction annotations are detected")

    # Processing options
    p.add_argument("--enhanced-metadata", action=argparse.BooleanOptionalAction, default=True,
                   help="Enable advanced metadata enrichment (default: True)")
    p.add_argument("--enable-quality-filter", action=argparse.BooleanOptionalAction, default=True,
                   help="Enable quality filtering of chunks (default: True)")
    p.add_argument("--min-chunk-length", type=int, default=80,
                   help="Minimum chunk length to include (default: 80)")

    # Provider options
    p.add_argument("--pdf-providers", default="pdftotext,pypdfium2,pymupdf,router",
                   help="Provider order for PDF processing")
    p.add_argument("--chunk-size", type=int, default=2000,
                   help="Text chunk size (default: 2000)")
    p.add_argument("--max-pages", type=int, default=0,
                   help="Max pages per PDF (0 = no limit)")

    default_timeout = 120 if platform.system().lower().startswith("win") else 60
    p.add_argument("--timeout-per-file", type=int, default=default_timeout,
                   help=f"Timeout per provider/router (default: {default_timeout}s)")

    # Embedding
    p.add_argument("--embed-batch-size", type=int, default=64,
                   help="Embedding batch size (default: 64)")
    return p.parse_args()


# --------------------------------- Main -------------------------------- #
def main() -> int:
    args = _parse_args()
    src = Path(args.src)
    out_root = Path(args.out)
    species = args.species.strip().lower()
    model_name = args.embed_model

    # Normalise exts (ajoute le point si manquant)
    exts = tuple((e if e.startswith(".") else f".{e}").lower().strip()
                 for e in args.exts.split(",") if e.strip())

    out_dir = (out_root / species)
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"🔎 Enhanced RAG Index Builder v1.0")
    log(f"🔎 Source root: {src}")
    log(f"💾 Output root: {out_root}")
    log(f"🐔 Species to build: {species}")
    log(f"🧠 Embedding model: {model_name}")
    log(f"⚡ Enhanced metadata: {args.enhanced_metadata}")
    log(f"🔍 Quality filtering: {args.enable_quality_filter}")
    log(f"\n— Building enhanced '{species}' index")
    log(f"   • src: {src}")
    log(f"   • out: {out_dir}")

    if not src.exists():
        log(f"❌ Source path not found: {src}")
        return 1

    files = sorted(_iter_files_local(str(src), exts, recursive=args.recursive))
    if not files:
        log("   • no files detected")
        log("\n✅ Build completed. Total chunks indexed: 0")
        return 0

    # Optional PDF health scan
    scan_summary: Dict[str, int] = {"scanned": 0, "copy_restricted": 0, "redactions": 0}
    pdf_health_rows: List[Dict[str, Any]] = []
    if args.scan_pdf:
        for f in files:
            if Path(f).suffix.lower() != ".pdf":
                continue
            scan = _scan_pdf_health(f)
            if not scan:
                continue
            scan_summary["scanned"] += 1
            if scan.copy_restricted:
                scan_summary["copy_restricted"] += 1
            if scan.redaction_annots > 0:
                scan_summary["redactions"] += scan.redaction_annots
            pdf_health_rows.append({
                "path": scan.path,
                "copy_restricted": scan.copy_restricted,
                "redaction_annots": scan.redaction_annots,
                "text_ratio": scan.text_ratio,
                "max_image_ratio": scan.max_image_ratio
            })
        if pdf_health_rows:
            try:
                import csv
                with open(out_dir / "pdf_health.csv", "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(pdf_health_rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(pdf_health_rows)
            except Exception:
                pass

    # Process files
    items: List[Dict[str, Any]] = []
    n_chunks = 0
    providers = [p.strip().lower() for p in (args.pdf_providers or "").split(",") if p.strip()]

    for i, fp in enumerate(files, start=1):
        suf = Path(fp).suffix.lower()
        if args.verbose:
            log(f"   • [{i}/{len(files)}] {fp}")

        # Clean if requested and redactions detected
        if suf == ".pdf" and args.auto_clean_redactions and args.scan_pdf:
            scan = next((row for row in pdf_health_rows if row["path"] == fp), None)
            if scan and (scan.get("redaction_annots", 0) > 0):
                fp = _auto_clean_if_needed(fp, PdfScanResult(
                    path=scan["path"],
                    copy_restricted=bool(scan["copy_restricted"]),
                    redaction_annots=int(scan["redaction_annots"]),
                    text_ratio=float(scan["text_ratio"]),
                    max_image_ratio=float(scan["max_image_ratio"])
                ), out_dir)

        chunks: List[Dict[str, Any]] = []
        last_err: Optional[str] = None

        if suf == ".pdf":
            prov, out_chunks, last_err = _try_enhanced_providers_for_pdf(
                fp=fp, species=species, providers=providers,
                chunk_size=args.chunk_size, max_pages=args.max_pages,
                timeout_router=args.timeout_per_file,
                enhanced_metadata=args.enhanced_metadata,
                min_chunk_length=args.min_chunk_length
            )
            if out_chunks:
                chunks = out_chunks
            if args.verbose:
                log(f"       · provider={prov} status={'ok' if chunks else 'fail'}")
                if last_err and not chunks:
                    log(f"       · last_error={last_err}")
        else:
            # Non-PDF : lire le texte brut et laisser le chunker décider (table-first)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                chunks = _enhanced_chunk_text(txt, args.chunk_size, {
                    "source_file": fp,
                    "extraction": "plaintext"
                }, args.min_chunk_length)
            except Exception as e:
                last_err = str(e)
                chunks = []

        # Metadata enrichment
        if args.enhanced_metadata and chunks:
            try:
                chunks = enhanced_enrich_metadata(chunks, species=species)
            except Exception:
                pass

        # Quality filter
        if args.enable_quality_filter and chunks:
            chunks, qstats = _quality_filter(chunks, min_len=args.min_chunk_length)
        else:
            qstats = {}

        # Collect
        for ch in chunks:
            text = (ch.get("text") or "").strip()
            meta = dict(ch.get("metadata", {}) or {})
            if not text:
                continue
            items.append({"text": text, "metadata": meta})
        n_chunks += len(chunks)

        if args.verbose:
            if chunks:
                log(f"       · chunks={len(chunks)}")
            else:
                log(f"       · no chunks extracted ({last_err or 'no detail'})")

    log(f"   • files detected: {len(files)}")
    log(f"   • chunks indexed: {n_chunks}")

    if not items:
        log("\n✅ Build completed. Total chunks indexed: 0")
        return 0

    # Embeddings
    texts = [it["text"] for it in items]
    log(f"\n🧠 Generating embeddings with {model_name} (batch={args.embed_batch_size})")
    model = _load_model(model_name)
    embs = _embed(model, texts, batch_size=args.embed_batch_size)

    if not _have_faiss():
        log("❌ FAISS not available (pip install faiss-cpu).")
        return 1

    # Save index
    _write_faiss(embs, out_dir / "index.faiss")
    np.save(out_dir / "embeddings.npy", embs)

    # Petit compteur de tables pour reporting
    tables_found = sum(1 for it in items if (it.get("metadata", {}).get("chunk_type") == "table"))

    with open(out_dir / "index.pkl", "wb") as f:
        index_data = {
            "documents": items,                    # sans duplication des embeddings
            "method": "SentenceTransformers",
            "embedding_method": "SentenceTransformers",
            "model_name": model_name,
            "enhanced_version": "v1.1",
            "processing_stats": {"tables_found": tables_found}
        }
        pickle.dump(index_data, f)

    _enhanced_save_meta(
        out_dir, species, model_name,
        n_files=len(files), n_chunks=n_chunks, files_sample=files[:5],
        pdf_scan_summary=scan_summary, quality_stats=qstats,
        enhanced_features=True, tables_found=tables_found
    )

    log(f"\n🧾 Tables detected: {tables_found}")
    log("\n✅ Build completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
