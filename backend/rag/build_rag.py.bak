# -*- coding: utf-8 -*-
"""
RAG Index Builder (CLI) — providers pour gros PDF, scan, auto-clean redactions, timeouts, limites

Providers disponibles (ordre configurable):
  - pdftotext   : Poppler (très rapide, texte brut)
  - pypdfium2   : PDFium (moteur Chrome)
  - pymupdf     : MuPDF (PyMuPDF) extraction blocs
  - router      : ton route_and_parse (avec timeout spawn-safe)

Exemples PowerShell:
  # Broiler: providers rapides + limites, nettoyage auto
  python -m rag.build_rag `
    --src "C:\\intelia_gpt\\documents\\public\\species\\broiler" `
    --out "C:\\intelia_gpt\\intelia-expert\\backend\\rag_index" `
    --species broiler --verbose --auto-clean-redactions `
    --pdf-providers "pdftotext,pypdfium2,pymupdf,router" `
    --chunk-size 3500 --max-pages 60 --timeout-per-file 45 --embed-batch-size 128

  # Global: simple et rapide
  python -m rag.build_rag `
    --src "C:\\intelia_gpt\\documents\\public\\common" `
    --out "C:\\intelia_gpt\\intelia-expert\\backend\\rag_index" `
    --species global --verbose `
    --pdf-providers "pdftotext,pypdfium2"

  # Layer: pas de nettoyage, router en dernier avec timeout
  python -m rag.build_rag `
    --src "C:\\intelia_gpt\\documents\\public\\species\\layer" `
    --out "C:\\intelia_gpt\\intelia-expert\\backend\\rag_index" `
    --species layer --verbose `
    --pdf-providers "pdftotext,pypdfium2,pymupdf,router" --timeout-per-file 60
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import traceback
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Iterable, List, Dict, Any, Tuple, Optional

import numpy as np

# --- Windows: forcer spawn (Python 3.13) -------------------------------- #
import multiprocessing as _mp
if sys.platform == "win32":
    try:
        _mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass  # déjà fixé

# ---------------------------- logging helper ---------------------------- #
def log(msg: str) -> None:
    print(msg, flush=True)

# --------------------- file iteration (robust) -------------------------- #
def _iter_files_local(root: str, allowed_exts: Tuple[str, ...], recursive: bool = True) -> Iterable[str]:
    p = Path(root)
    if p.is_file():
        if not allowed_exts or p.suffix.lower() in {e.lower() for e in allowed_exts}:
            yield str(p)
        return
    if not p.exists():
        return
    allowed = {e.lower() for e in allowed_exts} if allowed_exts else set()
    if recursive:
        for dp, _, fns in os.walk(p):
            for fn in fns:
                ext = os.path.splitext(fn)[1].lower()
                if not allowed or ext in allowed:
                    yield str(Path(dp) / fn)
    else:
        for child in p.iterdir():
            if child.is_file():
                ext = child.suffix.lower()
                if not allowed or ext in allowed:
                    yield str(child)

# ---------------- route_and_parse (new/legacy) -------------------------- #
try:
    from rag.parser_router import route_and_parse  # type: ignore
except Exception as e:
    print(f"❌ Import error (parser_router): {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

def _route_and_parse_file_compat(file_path: str, species: str) -> List[Any]:
    try:
        return route_and_parse(file_path, species=species)  # type: ignore[arg-type]
    except TypeError:
        chunks = route_and_parse(file_path)  # type: ignore[call-arg]
        for c in chunks:
            try:
                c.metadata["inferred_species"] = species  # type: ignore[attr-defined]
            except Exception:
                pass
        return chunks

# ------------------------------ PyMuPDF? -------------------------------- #
def _pdf_available():
    try:
        import fitz  # PyMuPDF
        _ = fitz
        return True
    except Exception:
        return False

# --------------------------- PDF utilities ------------------------------ #
def _page_image_coverage(page):
    rect_page = page.rect
    area_page = getattr(rect_page, "get_area", lambda: rect_page.width * rect_page.height)()
    if area_page <= 0:
        return 0.0, 0.0
    max_cov = 0.0
    areas = []
    try:
        imgs = page.get_images(full=True)
    except Exception:
        imgs = []
    for im in imgs:
        xref = im[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        for r in rects:
            a = getattr(r, "get_area", lambda: r.width * r.height)()
            cov = a / area_page
            areas.append(cov)
            if cov > max_cov:
                max_cov = cov
    avg_cov = sum(areas)/len(areas) if areas else 0.0
    return max_cov, avg_cov

def _has_redaction_annots(page):
    import fitz
    try:
        annots = page.annots(types=[fitz.PDF_ANNOT_REDACT])
        return annots is not None
    except Exception:
        try:
            a = page.annots()
            while a:
                if "Redact" in str(a.type):
                    return True
                a = a.next
        except Exception:
            pass
    return False

def _scan_single_pdf(fp: str) -> Dict[str, Any]:
    import fitz
    info = {
        "status": "OK",
        "file": fp,
        "is_encrypted": None,
        "can_copy": None,
        "pages": 0,
        "text_pages": 0,
        "text_pages_ratio": 0.0,
        "max_image_coverage": 0.0,
        "avg_image_coverage": 0.0,
        "redaction_annots": 0,
    }
    try:
        doc = fitz.open(fp)
    except Exception as e:
        info["status"] = f"OpenError: {e}"
        return info

    info["is_encrypted"] = bool(doc.is_encrypted)
    can_copy = True
    try:
        perm = getattr(doc, "permissions", None)
        if perm is not None:
            can_copy = bool(perm & 16)  # 0x10 = COPY
    except Exception:
        pass
    info["can_copy"] = can_copy

    pages = len(doc)
    info["pages"] = pages
    text_pages = 0
    max_cov_all = 0.0
    covs = []
    redacts = 0

    for i in range(pages):
        try:
            pg = doc[i]
        except Exception:
            continue
        try:
            txt = pg.get_text("text") or ""
        except Exception:
            txt = ""
        if txt.strip():
            text_pages += 1

        mx, av = _page_image_coverage(pg)
        max_cov_all = max(max_cov_all, mx)
        covs.append(av)

        if _has_redaction_annots(pg):
            redacts += 1

    info["text_pages"] = text_pages
    info["text_pages_ratio"] = round((text_pages / pages) if pages else 0.0, 3)
    info["max_image_coverage"] = round(max_cov_all, 3)
    info["avg_image_coverage"] = round(sum(covs)/len(covs) if covs else 0.0, 3)
    info["redaction_annots"] = redacts

    if info["is_encrypted"]:
        info["status"] = "Encrypted"
    elif not info["can_copy"]:
        info["status"] = "CopyRestricted"
    elif redacts > 0:
        info["status"] = "RedactionAnnots"
    elif info["text_pages_ratio"] < 0.1 and info["max_image_coverage"] > 0.85:
        info["status"] = "LikelyScanned"
    else:
        info["status"] = "OK"
    try:
        doc.close()
    except Exception:
        pass
    return info

def _scan_pdfs(files: List[str], out_csv: Path) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    if not _pdf_available():
        log("ℹ️  PDF scan skipped: PyMuPDF (fitz) is not installed. pip install pymupdf")
        return [], {}
    pdfs = [f for f in files if Path(f).suffix.lower() == ".pdf"]
    if not pdfs:
        return [], {}
    rows = []
    for fp in pdfs:
        try:
            rows.append(_scan_single_pdf(fp))
        except Exception as e:
            rows.append({"status": f"ScanError: {e}", "file": fp})

    order = {"Encrypted":0,"CopyRestricted":1,"RedactionAnnots":2,"LikelyScanned":3,"OK":4}
    rows.sort(key=lambda r: (order.get(r.get("status","OK"), 9),
                             1 - float(r.get("text_pages_ratio", 0.0) or 0.0),
                             -float(r.get("max_image_coverage", 0.0) or 0.0),
                             r.get("file","").lower()))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    cols = ["status","file","is_encrypted","can_copy","pages","text_pages","text_pages_ratio","max_image_coverage","avg_image_coverage","redaction_annots"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in cols})

    from collections import Counter as _Counter
    c = _Counter(r["status"] for r in rows)
    log(f"   • PDF scan summary: {dict(c)}")
    for r in rows[:10]:
        tr = r.get("text_pages_ratio", 0.0) or 0.0
        mi = r.get("max_image_coverage", 0.0) or 0.0
        rd = r.get("redaction_annots", 0) or 0
        log(f"     - {r['status']:<16} text_ratio={tr:.2f}  max_img={mi:.2f}  redacts={rd}  {r.get('file','')}")
    log(f"   • PDF scan CSV written to: {out_csv}")
    return rows, dict(c)

def _strip_redactions(src: str, dst: str) -> bool:
    if not _pdf_available():
        return False
    import fitz
    try:
        doc = fitz.open(src)
    except Exception:
        return False
    modified = False
    for page in doc:
        a = page.first_annot
        while a:
            nxt = a.next
            try:
                if "Redact" in str(a.type):
                    try:
                        page.delete_annot(a)
                        modified = True
                    except Exception:
                        pass
            finally:
                a = nxt
    out_dir = Path(dst).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        doc.save(dst, deflate=True, garbage=4)
        doc.close()
        return True
    except Exception:
        try: doc.close()
        except Exception: pass
        return False

# ------------------------ Provider registry ----------------------------- #
def _chunk_text(text: str, size: int, base_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return []
    out = []
    start = 0
    while start < len(text):
        piece = text[start:start+size]
        out.append({"text": piece, "metadata": dict(base_meta)})
        start += size
    return out

def _extract_pdftotext(fp: str, chunk_size: int) -> Optional[List[Dict[str, Any]]]:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    try:
        # -layout garde un ordre de lecture correct pour des guides techniques
        # -enc UTF-8 assure l'encodage
        p = subprocess.run([exe, "-layout", "-enc", "UTF-8", "-q", fp, "-"],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        txt = p.stdout.decode("utf-8", errors="ignore")
        return _chunk_text(txt, chunk_size, {"source_file": fp, "extraction": "pdftotext"})
    except Exception as e:
        log(f"       · pdftotext failed on {fp}: {e}")
        return None

def _extract_pypdfium2(fp: str, chunk_size: int, max_pages: int = 0) -> Optional[List[Dict[str, Any]]]:
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
    limit = total if max_pages <= 0 else min(max_pages, total)
    try:
        for i in range(limit):
            page = doc[i]
            tp = page.get_textpage()
            try:
                txt = tp.get_text_range()
            except Exception:
                # fallback simple si API différente
                txt = tp.get_text_bounded() if hasattr(tp, "get_text_bounded") else ""
            try:
                tp.close()
            except Exception:
                pass
            txt = (txt or "").strip()
            if not txt:
                continue
            chunks.extend(_chunk_text(txt, chunk_size, {
                "source_file": fp, "page": i+1, "extraction": "pypdfium2"}))
    finally:
        try:
            doc.close()
        except Exception:
            pass
    return chunks or []

def _extract_pymupdf(fp: str, chunk_size: int, max_pages: int = 0) -> Optional[List[Dict[str, Any]]]:
    if not _pdf_available():
        return None
    import fitz
    try:
        doc = fitz.open(fp)
    except Exception:
        return None
    chunks: List[Dict[str, Any]] = []
    total = len(doc)
    limit = total if max_pages <= 0 else min(total, max_pages)
    try:
        for i in range(limit):
            page = doc[i]
            try:
                # "blocks" = meilleur ordre de lecture que "text" brut
                blocks = page.get_text("blocks") or []
                block_texts = []
                for b in blocks:
                    # tuple: (x0, y0, x1, y1, text, block_no, block_type)
                    t = b[4] if len(b) >= 5 else ""
                    if t and t.strip():
                        block_texts.append(t.strip())
                txt = "\n".join(block_texts)
            except Exception:
                txt = page.get_text("text") or ""
            txt = txt.strip()
            if not txt:
                continue
            chunks.extend(_chunk_text(txt, chunk_size, {
                "source_file": fp, "page": i+1, "extraction": "pymupdf"}))
    finally:
        try:
            doc.close()
        except Exception:
            pass
    return chunks or []

# ---- router via subprocess spawn (timeout dur, Windows-safe) ----------- #
def _serialize_chunks_for_ipc(out):
    ser = []
    for c in (out or []):
        text = getattr(c, "text", None)
        meta = getattr(c, "metadata", None)
        if text is None:
            if isinstance(c, dict):
                text = c.get("text") or c.get("content") or ""
                meta = c.get("metadata") or {}
            else:
                text, meta = str(c), {}
        ser.append({"text": str(text), "metadata": dict(meta or {})})
    return ser

def _router_worker(path: str, species: str, q):
    try:
        out = _route_and_parse_file_compat(path, species=species)
        q.put(("ok", _serialize_chunks_for_ipc(out)))
    except Exception as e:
        q.put(("err", str(e)))

def _run_router_with_timeout(fp: str, species: str, timeout_s: int) -> Tuple[str, Optional[str], Optional[List[Dict[str, Any]]]]:
    ctx = _mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_router_worker, args=(fp, species, q))
    p.start()
    p.join(timeout_s)
    if p.is_alive():
        try:
            p.terminate()
        except Exception:
            pass
        p.join(5)
        return "timeout", f"parser timeout after {timeout_s}s", None
    try:
        status, payload = q.get_nowait()
    except Exception:
        return "err", "no result from parser", None
    if status == "ok":
        return "ok", None, payload
    else:
        return "err", payload, None

# -------------------- orchestration: try providers ---------------------- #
def _try_providers_for_pdf(fp: str, species: str, providers: List[str],
                           chunk_size: int, max_pages: int, timeout_router: int) -> Tuple[str, Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Retourne (provider_used, chunks|None, error_if_any)
    """
    for prov in providers:
        prov = prov.strip().lower()
        try:
            if prov == "pdftotext":
                chunks = _extract_pdftotext(fp, chunk_size)
                if chunks:
                    return prov, chunks, None
            elif prov == "pypdfium2":
                chunks = _extract_pypdfium2(fp, chunk_size, max_pages=max_pages)
                if chunks:
                    return prov, chunks, None
            elif prov == "pymupdf":
                chunks = _extract_pymupdf(fp, chunk_size, max_pages=max_pages)
                if chunks:
                    return prov, chunks, None
            elif prov == "router":
                status, err, chunks = _run_router_with_timeout(fp, species, timeout_router)
                if status == "ok" and chunks:
                    return prov, chunks, None
                elif status == "ok":
                    # router a rendu 0 chunk → on tente le provider suivant
                    pass
                else:
                    # erreur/timeout : on continue la cascade mais mémorise l'erreur
                    last_err = err or status
            else:
                log(f"       · unknown provider '{prov}', skipping")
        except Exception as e:
            last_err = str(e)
            continue
    return "none", None, locals().get("last_err")

# ----------------------- embeddings & FAISS I/O ------------------------- #
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

def _save_meta(out_dir: Path, species: str, model_name: str,
               n_files: int, n_chunks: int, files_sample: List[str],
               pdf_scan_summary: Dict[str, int] | None = None) -> None:
    meta = {
        "species": species,
        "model": model_name,
        "build_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "num_files": n_files,
        "num_chunks": n_chunks,
        "files_sample": files_sample[:10],
        "pdf_scan_summary": pdf_scan_summary or {},
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

# ------------------------------ CLI parsing ----------------------------- #
def _parse_args():
    p = argparse.ArgumentParser(description="Build RAG vector index from a folder or a single file.")
    p.add_argument("--src", required=True, help="Document file or directory")
    p.add_argument("--out", required=True, help="Output root directory (indexes saved under <out>/<species>/)")
    p.add_argument("--species", required=True, help="global|broiler|layer|... (free text)")
    p.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2",
                   help="Sentence-Transformers model name")
    p.add_argument("--exts", default=".pdf,.txt,.md,.html,.htm,.csv,.xlsx,.xls",
                   help="Comma-separated list of extensions to include")
    p.add_argument("--recursive", action="store_true", default=True,
                   help="Recursively traverse subfolders (default: True)")
    p.add_argument("--verbose", action="store_true", default=False,
                   help="Print per-file extraction details")

    # Scan/clean
    p.add_argument("--scan-pdf", dest="scan_pdf", action=argparse.BooleanOptionalAction, default=True,
                   help="Scan PDF health and write <out>/<species>/pdf_status.csv (default: True)")
    p.add_argument("--auto-clean-redactions", action="store_true", default=False,
                   help="Supprimer les annotations 'Redact' dans des copies (dossier _clean)")

    # Providers
    p.add_argument("--pdf-providers", default="pdftotext,pypdfium2,pymupdf,router",
                   help="Ordre des providers pour PDF (ex: 'pdftotext,pypdfium2,pymupdf,router')")
    p.add_argument("--chunk-size", type=int, default=1500,
                   help="Taille des chunks texte (défaut 1500)")
    p.add_argument("--max-pages", type=int, default=0,
                   help="Limiter le nombre de pages lues par provider (0 = no limit)")
    p.add_argument("--timeout-per-file", type=int, default=60,
                   help="Timeout en secondes pour le provider 'router' (défaut 60)")

    # Embeddings
    p.add_argument("--embed-batch-size", type=int, default=64,
                   help="Batch size pour l'embedding (défaut 64)")
    return p.parse_args()

# --------------------------------- main --------------------------------- #
def main() -> int:
    args = _parse_args()
    src = Path(args.src)
    out_root = Path(args.out)
    species = args.species.strip().lower()
    model_name = args.embed_model
    exts = tuple(e.strip().lower() for e in args.exts.split(",") if e.strip())
    out_dir = (out_root / species)
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"🔎 Source root: {src}")
    log(f"💾 Output root: {out_root}")
    log(f"🐔 Species to build: {species}")
    log(f"🧠 Embedding model: {model_name}")
    log(f"\n— Building '{species}' index")
    log(f"   • src: {src}")
    log(f"   • out: {out_dir}")

    if not src.exists():
        log(f"❌ Source path not found: {src}")
        return 2

    files = list(_iter_files_local(str(src), allowed_exts=exts, recursive=args.recursive))
    log(f"   • files detected: {len(files)}")
    if not files:
        log("⚠️  No files detected. Check --exts or path.")
        return 0

    # 1) Scan PDF
    pdf_rows: List[Dict[str, Any]] = []
    pdf_scan_summary: Dict[str, int] | None = None
    if args.scan_pdf:
        try:
            pdf_csv = out_dir / "pdf_status.csv"
            pdf_rows, pdf_scan_summary = _scan_pdfs(files, pdf_csv)
        except Exception as e:
            log(f"⚠️  PDF scan failed: {e}")

    # 2) Auto-clean copies for redactions
    replacement_map: Dict[str, str] = {}
    if args.auto_clean_redactions and pdf_rows:
        if not _pdf_available():
            log("⚠️  auto-clean redactions demandé mais PyMuPDF absent (pip install pymupdf).")
        else:
            clean_dir = out_dir / "_clean"
            clean_dir.mkdir(parents=True, exist_ok=True)
            targets = [r for r in pdf_rows if r.get("status") == "RedactionAnnots" and r.get("redaction_annots", 0) > 0]
            if targets:
                log(f"   • Auto-clean: {len(targets)} PDF(s) avec redactions → copies nettoyées dans {clean_dir}")
            for r in targets:
                src_pdf = r["file"]
                dst_pdf = str(clean_dir / (Path(src_pdf).stem + "_clean.pdf"))
                ok = _strip_redactions(src_pdf, dst_pdf)
                if ok:
                    replacement_map[src_pdf] = dst_pdf
                    if args.verbose:
                        log(f"     ✓ cleaned: {src_pdf} → {dst_pdf}")
                else:
                    if args.verbose:
                        log(f"     ✗ clean failed: {src_pdf}")

    # 3) Extraction avec providers
    provider_order = [p.strip() for p in (args.pdf_providers or "").split(",") if p.strip()]
    chunks: List[Dict[str, Any]] = []
    per_ext_counts = Counter()
    per_ext_chunks = Counter()
    errors_by_file: Dict[str, str] = {}
    provider_used_count = Counter()

    for fp in files:
        ext = Path(fp).suffix.lower()
        per_ext_counts[ext] += 1

        if ext == ".pdf":
            parse_path = replacement_map.get(fp, fp)
            prov, file_chunks, err = _try_providers_for_pdf(
                parse_path, species, provider_order,
                chunk_size=args.chunk_size, max_pages=args.max_pages,
                timeout_router=args.timeout_per_file
            )
            if file_chunks:
                provider_used_count[prov] += 1
                per_ext_chunks[ext] += len(file_chunks)
                # enrichir la meta avec species + chunk_index sera fait plus bas
                chunks.extend(file_chunks)
                if args.verbose:
                    log(f"     ✓ {parse_path}  via {prov} → {len(file_chunks)} chunks")
            else:
                errors_by_file[fp] = err or f"no provider produced chunks (order={provider_order})"
                log(f"     ✗ {parse_path}  → {errors_by_file[fp]}")
        else:
            # non-PDF → router direct (avec timeout)
            status, err, file_chunks = _run_router_with_timeout(fp, species, args.timeout_per_file)
            if status == "ok" and file_chunks:
                provider_used_count["router"] += 1
                per_ext_chunks[ext] += len(file_chunks)
                chunks.extend(file_chunks)
                if args.verbose:
                    log(f"     ✓ {fp}  via router → {len(file_chunks)} chunks")
            else:
                errors_by_file[fp] = err or status
                log(f"     ✗ {fp}  → {errors_by_file[fp]}")

    # 4) Résumé extraction
    by_ext = sorted(per_ext_counts.items(), key=lambda x: x[0])
    log("   • summary by extension:")
    for ext, n in by_ext:
        log(f"       {ext or '(none)'}: files={n}, chunks={per_ext_chunks.get(ext,0)}")
    if provider_used_count:
        log(f"   • providers used: {dict(provider_used_count)}")
    if errors_by_file:
        log(f"   • files with errors: {len(errors_by_file)} (showing up to 5)")
        for i, (f, err) in enumerate(errors_by_file.items()):
            if i >= 5: break
            log(f"       - {f}: {err}")

    # 5) Embeddings + index
    n_chunks = len(chunks)
    if n_chunks == 0:
        log("⚠️  0 chunk extracted. Causes probables: PDF scannés (OCR), formats non supportés, timeouts.")
        log("   → Pour OCR batch: installer OCRmyPDF/Tesseract et ajouter un pré-pass.")
        _save_meta(out_dir, species, model_name, n_files=len(files), n_chunks=0, files_sample=files[:5],
                   pdf_scan_summary=pdf_scan_summary)
        return 0

    # normalisation finale + enrichissement meta
    texts: List[str] = []
    items: List[Dict[str, Any]] = []
    for i, c in enumerate(chunks):
        text = c.get("text") if isinstance(c, dict) else getattr(c, "text", "")
        meta = c.get("metadata") if isinstance(c, dict) else getattr(c, "metadata", {}) or {}
        meta = dict(meta or {})
        meta.setdefault("chunk_index", i)
        meta.setdefault("chunk_type", meta.get("chunk_type", "text"))
        meta.setdefault("inferred_species", species)
        texts.append(str(text))
        items.append({"text": str(text), "metadata": meta})

    model = _load_model(model_name)
    embs = _embed(model, texts, batch_size=args.embed_batch_size)

    if not _have_faiss():
        log("❌ FAISS not available (pip install faiss-cpu).")
        return 1
    _write_faiss(embs, out_dir / "index.faiss")

    import pickle
    np.save(out_dir / "embeddings.npy", embs)
    with open(out_dir / "index.pkl", "wb") as f:
        pickle.dump(items, f)
    _save_meta(out_dir, species, model_name, n_files=len(files), n_chunks=n_chunks, files_sample=files[:5],
               pdf_scan_summary=pdf_scan_summary)

    log(f"\n✅ Build completed. Total chunks indexed: {n_chunks}")
    log(f"   → {out_dir / 'index.faiss'}")
    log(f"   → {out_dir / 'index.pkl'}")
    log(f"   → {out_dir / 'embeddings.npy'}")
    log(f"   → {out_dir / 'meta.json'}")
    if args.scan_pdf:
        log(f"   → {out_dir / 'pdf_status.csv'}")
    if args.auto_clean_redactions:
        log(f"   • cleaned copies (if any) are under: {out_dir / '_clean'}")
    return 0

if __name__ == "__main__":
    try:
        _mp.freeze_support()
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Fatal error: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
