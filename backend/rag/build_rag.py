# -*- coding: utf-8 -*-
"""
Enhanced RAG Index Builder (CLI) - With Advanced Metadata Enrichment

Enhanced features:
- Advanced metadata enrichment with species/strain/domain detection
- Enhanced PDF analysis with comprehensive health scoring
- Improved provider cascade with timeout management
- Better chunking strategies based on content type
- Quality assessment and filtering

Providers disponibles (ordre configurable):
  - pdftotext   : Poppler (très rapide, texte brut)
  - pypdfium2   : PDFium (moteur Chrome)
  - pymupdf     : MuPDF (PyMuPDF) extraction blocs
  - router      : Enhanced parser router (avec timeout spawn-safe)

Presets (exemples):
  # Broiler handbook unique
  python -m rag.build_rag `
    --src "C:\\intelia_gpt\\documents\\public\\species\\broiler\\breeds\\ross_308_broiler\\Aviagen-ROSS-Broiler-Handbook-EN.pdf" `
    --out "C:\\intelia_gpt\\intelia-expert\\backend\\rag_index" `
    --species broiler --verbose `
    --pdf-providers "pdftotext,pypdfium2,pymupdf,router" `
    --chunk-size 2000 --max-pages 0 --timeout-per-file 120 `
    --enable-quality-filter --min-chunk-length 80

  # Dossier complet (recursif) avec filtres qualité + métadonnées
  python -m rag.build_rag `
    --src "C:\\intelia_gpt\\documents\\public\\common" `
    --out "C:\\intelia_gpt\\intelia-expert\\backend\\rag_index" `
    --species global --verbose --enhanced-metadata `
    --pdf-providers "pdftotext,pypdfium2,pymupdf,router" `
    --chunk-size 2000 --max-pages 60 --timeout-per-file 120 --embed-batch-size 128 `
    --enable-quality-filter --min-chunk-length 80

  # Global: enhanced with metadata enrichment
  python -m rag.build_rag `
    --src "C:\\intelia_gpt\\documents\\public\\common" `
    --out "C:\\intelia_gpt\\intelia-expert\\backend\\rag_index" `
    --species global --verbose --enhanced-metadata --scan-pdf `
    --pdf-providers "pdftotext,pypdfium2,pymupdf,router" `
    --chunk-size 2000 --min-chunk-length 80 --timeout-per-file 120
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

# Numpy is used for embeddings / FAISS build
import numpy as np

# ----------------------------- Logging --------------------------------- #
def log(msg: str) -> None:
    print(msg, flush=True)

# ------------------------ Normalisation util --------------------------- #
def _normalize_text(txt: str) -> str:
    # déhyphénation “brood-\n ing” → “brooding”
    txt = re.sub(r'-\s*\n', '', txt)
    # jonction lignes → phrase
    txt = re.sub(r'\s*\n\s*', ' ', txt)
    # espaces multiples
    txt = re.sub(r'\s{2,}', ' ', txt).strip()
    return txt

# --------------------- Enhanced file iteration --------------------------- #
def _iter_files_local(root: str, allowed_exts: Tuple[str, ...], recursive: bool = True) -> Iterable[str]:
    """Enhanced file iteration with better filtering"""
    p = Path(root)
    if p.is_file():
        if not allowed_exts or p.suffix.lower() in {e.lower() for e in allowed_exts}:
            yield str(p)
        return
    if not p.exists():
        return
    
    allowed = {e.lower() for e in allowed_exts} if allowed_exts else set()
    
    # Skip hidden and system directories
    skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
    
    if recursive:
        for dp, dirs, fns in os.walk(p):
            # Filter out unwanted directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for fn in fns:
                # Skip hidden files and temporary files
                if fn.startswith('.') or fn.endswith('.tmp'):
                    continue
                    
                ext = os.path.splitext(fn)[1].lower()
                if not allowed or ext in allowed:
                    yield str(Path(dp) / fn)
    else:
        for child in p.iterdir():
            if child.is_file():
                if child.name.startswith('.') or child.name.endswith('.tmp'):
                    continue
                ext = child.suffix.lower()
                if not allowed or ext in allowed:
                    yield str(child)

# ---------------- Enhanced route_and_parse with metadata ----------------- #
try:
    from rag.parsers.metadata_enrichment import enhanced_enrich_metadata
except Exception:
    # fallback si l'arborescence diffère
    try:
        from rag.metadata_enrichment import enhanced_enrich_metadata  # type: ignore
    except Exception:
        def enhanced_enrich_metadata(chunks: List[Dict[str, Any]], species: str) -> List[Dict[str, Any]]:
            # no-op fallback
            return chunks

# --------------------- Chunking (enhanced strategy) --------------------- #
def _enhanced_chunk_text(
    txt: str,
    chunk_size: int,
    base_meta: Dict[str, Any],
    min_chunk_length: int = 80
) -> List[Dict[str, Any]]:
    """
    Enhanced chunker:
      - preserve table-like blocks as single chunks
      - otherwise split on paragraphs/sentences without breaking mid-figure
    """
    txt = txt.strip()
    if not txt:
        return []
    
    # Heuristic: treat markdown/pipe tables or lines with many columns as single unit
    is_table = False
    if "|" in txt:
        # Many pipes likely indicate table-like content
        lines = txt.split("\n")
        pipe_lines = sum(1 for L in lines if "|" in L)
        if pipe_lines >= max(2, len(lines) // 3):
            is_table = True
    
    # preserve whole block for tables
    if is_table:
        meta = dict(base_meta)
        meta.setdefault("chunk_type", "table")
        return [{"text": txt, "metadata": meta}]
    
    # Standard paragraph-first split
    # Prefer splitting on double newlines or sentence boundaries if present in text
    # Since _normalize_text removed newlines, we reconstruct light paragraph splitting
    # by splitting on ". " but keep chunk_size constraint
    chunks: List[Dict[str, Any]] = []
    words = txt.split(" ")
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

# ---------------------- PDF health scan (optional) ---------------------- #
@dataclass
class PdfScanResult:
    path: str
    copy_restricted: bool
    redaction_annots: int
    text_ratio: float
    max_image_ratio: float

def _scan_pdf_health(fp: str) -> Optional[PdfScanResult]:
    """
    Light-weight scan to detect copy restrictions, redactions, and text/image ratios.
    """
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
            # redaction annotations
            annots = page.annots()
            if annots:
                for a in annots:
                    if a.type[0] == 17:  # 17 is redaction
                        redactions += 1
        except Exception:
            pass
        try:
            textpage = page.get_text("text")
            text_chars += len(textpage or "")
        except Exception:
            pass
        try:
            # image area approx from image list
            w, h = page.rect.width, page.rect.height
            page_area_sum += (w * h)
            imgs = page.get_images(full=True) or []
            # rough heuristic: if many images, push ratio up
            image_area_max = max(image_area_max, min(1.0, len(imgs) * 0.1))
        except Exception:
            pass
    
    copy_restricted = False
    try:
        perms = doc.permissions
        # if copy text is not allowed -> 1 bit in permissions. PyMuPDF doc: 4=copy
        if perms is not None:
            copy_restricted = (perms & 4) == 0
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

# --------------------- Auto-clean redaction (optional) ------------------ #
def _auto_clean_if_needed(fp: str, scan: Optional[PdfScanResult], out_dir: Path) -> str:
    """
    If redaction annotations are detected, try to write a flattened copy.
    Otherwise, return original path.
    """
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
        try: doc.close()
        except: pass
        return clean_path
    except Exception:
        try: doc.close()
        except: pass
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
        p = subprocess.run([exe, "-layout", "-enc", "UTF-8", "-q", fp, "-"],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_per_file)
        txt = p.stdout.decode("utf-8", errors="ignore")
        txt = _normalize_text(txt)
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
                txt = _normalize_text(txt)
                if not txt.strip():
                    continue
                page_meta = {
                    "source_file": fp,
                    "page": i + 1,
                    "total_pages": len(doc),
                    "extraction": "pypdfium2"
                }
                chunks.extend(_enhanced_chunk_text(txt, chunk_size, page_meta, min_chunk_length))
            except Exception:
                continue
    except Exception:
        pass
    try: doc.close()
    except Exception: pass
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
                # prefer block text to keep layout-ish structure; fallback to raw text
                try:
                    blocks = page.get_text("blocks")
                    blocks = blocks or []
                    # sort by vertical position (y0)
                    blocks.sort(key=lambda b: (b[1], b[0]))
                    parts = []
                    for (x0, y0, x1, y1, text, block_no, block_type) in blocks:
                        if text:
                            parts.append(text)
                    txt = "\n".join(parts).strip()
                except Exception:
                    txt = page.get_text("text") or ""
                txt = _normalize_text(txt)
                if not txt:
                    continue
                page_meta = {
                    "source_file": fp,
                    "page": i + 1,
                    "total_pages": doc.page_count,
                    "extraction": "pymupdf"
                }
                chunks.extend(_enhanced_chunk_text(txt, chunk_size, page_meta, min_chunk_length))
            except Exception:
                continue
    except Exception:
        pass
    try: doc.close()
    except Exception: pass
    return chunks or []

# ---------------------- Router (external enhanced) ---------------------- #
def _run_enhanced_router_with_timeout(
    fp: str, species: str, timeout_sec: int, enhanced_metadata: bool
) -> Tuple[str, Optional[str], Optional[List[Dict[str, Any]]]]:
    """
    Spawn a subprocess to run advanced router to avoid hangs/crashes,
    and capture stdout/json result (status, error, chunks).
    """
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
            # ensure normalization minimal
            fixed_chunks: List[Dict[str, Any]] = []
            for ch in chunks:
                t = _normalize_text(str(ch.get("text", "") or ""))
                if not t:
                    continue
                meta = dict(ch.get("metadata", {}) or {})
                fixed_chunks.append({"text": t, "metadata": meta})
            return "ok", None, fixed_chunks
        else:
            return data.get("status", "error"), data.get("error") or None, None
    except subprocess.TimeoutExpired:
        return "timeout", "router timeout", None
    except Exception as e:
        return "error", str(e), None

# -------------------- Provider cascade & quality filter ----------------- #
def _try_enhanced_providers_for_pdf(
    fp: str, species: str, providers: List[str],
    chunk_size: int, max_pages: int, timeout_router: int,
    enhanced_metadata: bool = True, min_chunk_length: int = 80
) -> Tuple[str, Optional[List[Dict[str, Any]]], Optional[str]]:
    """Enhanced provider cascade with quality assessment"""
    
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
                elif status == "ok":
                    pass  # Continue to next provider
                else:
                    last_err = err or status
            else:
                log(f"       · unknown provider '{prov}', skipping")
        except Exception as e:
            last_err = str(e)
            continue
    
    return "none", None, locals().get("last_err")

# ----------------------- Enhanced embeddings & FAISS ------------------- #
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
    enhanced_features: bool = True
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
        "version": "1.0",
    }
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

# --------------------------- Quality filter ----------------------------- #
def _quality_filter(chunks: List[Dict[str, Any]], min_len: int = 80) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Basic quality filter: remove very short chunks and collect stats
    """
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

# ------------------------------ CLI parse ------------------------------- #
def _parse_args():
    p = argparse.ArgumentParser(description="Enhanced RAG vector index builder with advanced metadata.")
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

    # Enhanced scanning and cleaning
    p.add_argument("--scan-pdf", dest="scan_pdf", action=argparse.BooleanOptionalAction, default=True,
                   help="Enhanced PDF health scan and write analysis CSV (default: True)")
    p.add_argument("--auto-clean-redactions", action="store_true", default=False,
                   help="Automatically remove redaction annotations and create clean copies")

    # Enhanced processing options
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
    
    # Timeout par défaut adapté selon la plateforme
    default_timeout = 120 if sys.platform == "win32" else 60
    p.add_argument("--timeout-per-file", type=int, default=default_timeout,
                   help=f"Timeout for router provider (default: {default_timeout}s)")

    # Embedding options
    p.add_argument("--embed-batch-size", type=int, default=64,
                   help="Embedding batch size (default: 64)")
    return p.parse_args()

# --------------------------------- Enhanced main -------------------- #
def main() -> int:
    args = _parse_args()
    src = Path(args.src)
    out_root = Path(args.out)
    species = args.species.strip().lower()
    model_name = args.embed_model
    
    # Normalisation des extensions pour être tolérant aux formats avec/sans point
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

    # Collect files
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
        # write CSV summary
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
        
        # If PDF and cleaning is requested and redactions detected, clean first
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

        # route by type
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
            # simple text loader for non-PDF
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                txt = _normalize_text(txt)
                chunks = _enhanced_chunk_text(txt, args.chunk_size, {
                    "source_file": fp,
                    "extraction": "plaintext"
                }, args.min_chunk_length)
            except Exception as e:
                last_err = str(e)
                chunks = []

        # metadata enrichment
        if args.enhanced_metadata and chunks:
            try:
                chunks = enhanced_enrich_metadata(chunks, species=species)  # add domain/species/strain if possible
            except Exception:
                # best-effort
                pass
        
        # quality filter
        if args.enable_quality_filter and chunks:
            chunks, qstats = _quality_filter(chunks, min_len=args.min_chunk_length)
        else:
            qstats = {}

        # append results
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

    # Build embeddings
    texts = [it["text"] for it in items]
    log(f"\n🧠 Generating embeddings with {model_name} (batch={args.embed_batch_size})")
    model = _load_model(model_name)
    embs = _embed(model, texts, batch_size=args.embed_batch_size)

    if not _have_faiss():
        log("❌ FAISS not available (pip install faiss-cpu).")
        return 1
    
    # Save enhanced index
    _write_faiss(embs, out_dir / "index.faiss")

    import pickle
    np.save(out_dir / "embeddings.npy", embs)
    with open(out_dir / "index.pkl", "wb") as f:
        # Index data sans duplication des embeddings
        index_data = {
            "documents": items,
            "method": "SentenceTransformers",
            "embedding_method": "SentenceTransformers",
            "model_name": model_name,
            "enhanced_version": "v1.0",
            "processing_stats": qstats if isinstance(qstats, dict) else {}
        }
        pickle.dump(index_data, f)
    
    _enhanced_save_meta(out_dir, species, model_name, n_files=len(files), n_chunks=n_chunks, 
                        files_sample=files[:5], pdf_scan_summary=scan_summary, 
                        quality_stats=qstats, enhanced_features=True)

    log("\n✅ Build completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
