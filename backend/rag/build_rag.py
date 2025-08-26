# -*- coding: utf-8 -*-
"""
Enhanced RAG Index Builder (CLI)
v1.5 - Perfect CSV Integration + Enhanced Performance Targets Detection
- All CSV files are properly indexed in RAG while maintaining tables/ structure
- Improved performance targets detection with multiple heuristics
- Enhanced metadata guarantees with complete species/line/sex inference
- Comprehensive table detection with auto-tagging
- Quality filtering and validation

Exemple (Ross 308, avec OCR):
  python -m rag.build_rag `
    --src "C:\\intelia_gpt\\documents\\public\\species\\broiler\\breeds\\ross_308_broiler" `
    --out "C:\\intelia_gpt\\intelia-expert\\backend\\rag_index" `
    --species broiler_ross308 `
    --exts ".pdf" `
    --pdf-providers "pdftotext,pymupdf,pypdfium2,ocr" `
    --enable-ocr --ocr-dpi 220 --ocr-lang eng `
    --chunk-size 2000 --min-chunk-length 80 --timeout-per-file 120 `
    --max-table-lines 40 `
    --enhanced-metadata --enable-quality-filter --scan-pdf --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
import json
import pickle
import shutil
import subprocess
import platform
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional, Iterable

import numpy as np
import csv

# ----------------------------- Logging --------------------------------- #
def log(msg: str) -> None:
    print(msg, flush=True)

# ------------------------ Normalisation util --------------------------- #
def _normalize_text(txt: str) -> str:
    # déhyphénation "brood-\n ing" -> "brooding"
    txt = re.sub(r"-\s*\n", "", txt)
    # lignes -> phrase
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

# --------- Enhanced Metadata enrichment with validation ------------- #
try:
    from rag.metadata_enrichment import enhanced_enrich_metadata, validate_required_metadata, analyze_table_detection
    ENHANCED_METADATA_AVAILABLE = True
    log("Enhanced metadata enrichment available")
except Exception:
    try:
        from rag.parsers.metadata_enrichment import enhanced_enrich_metadata, validate_required_metadata, analyze_table_detection
        ENHANCED_METADATA_AVAILABLE = True
        log("Enhanced metadata enrichment available (from parsers)")
    except Exception:
        ENHANCED_METADATA_AVAILABLE = False
        log("Enhanced metadata enrichment not available, using fallbacks")
        def enhanced_enrich_metadata(chunks: List[Dict[str, Any]], species: str = None, additional_context: Dict = None) -> List[Dict[str, Any]]:
            return chunks
        def validate_required_metadata(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
            return {"total_chunks": len(chunks), "coverage": {}, "critical_coverage": 0}
        def analyze_table_detection(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
            return {"tables_detected": 0, "total_chunks": len(chunks), "perf_targets_tables": 0}

# --------------------- Enhanced Table-first chunker -------------------- #
def _enhanced_chunk_text_with_metadata_guarantee(
    txt: str,
    chunk_size: int,
    base_meta: Dict[str, Any],
    min_chunk_length: int = 80,
    species: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Table-first (heuristique fallback sur texte brut) avec garantie métadonnées:
      - Détecte les blocs tabulaires (≥3 colonnes sur ≥40% des lignes via 2+ espaces, tab, ou pipes)
      - Détection avancée tables de performance avec auto-taggage table_type="perf_targets"
      - Si table → conserve la mise en page (retours ligne, espaces multiples), CHUNK UNIQUE, meta['chunk_type']="table"
      - Sinon → normalisation légère puis découpe par ~chunk_size mots
      - Garantie métadonnées species/line/sex si détectable
    """
    raw = txt or ""
    if not raw.strip():
        return []

    # --- DÉTECTION AVANCÉE DE TABLEAU AVANT NORMALISATION ---
    lines = [L.rstrip() for L in raw.splitlines() if L.strip()]
    is_table = False
    table_type = None
    
    if lines:
        import re as _re
        
        # Méthode 1: Colonnes multiples (méthode existante)
        col_counts = [len([p for p in _re.split(r"\s{2,}|\t", L) if p]) for L in lines]
        multi_col_lines = sum(1 for c in col_counts if c >= 3)
        if multi_col_lines >= max(3, int(0.4 * len(lines))):
            is_table = True
        
        # Méthode 2: Pipes (méthode existante)
        if not is_table:
            pipe_lines = sum(1 for L in lines if "|" in L)
            if pipe_lines >= max(2, len(lines) // 3):
                is_table = True
        
        # Méthode 3: CSV structure detection
        if not is_table:
            # Detect CSV-like structure (commas as separators)
            comma_lines = sum(1 for L in lines if L.count(',') >= 2)
            if comma_lines >= max(3, int(0.6 * len(lines))):
                is_table = True
        
        # Méthode 4: Patterns spécifiques aux tables de performance
        if not is_table:
            text_lower = raw.lower()
            perf_patterns = [
                r"(?:target|objective|objectif)\s*(?:weight|poids|bw|performance)",
                r"(?:age|week|day|jour|semaine)\s*(?:weight|poids|bw)",
                r"(?:fcr|conversion)\s*(?:target|objective|standard)",
                r"(?:growth|croissance)\s*(?:curve|courbe|target|standard)",
                r"body\s*weight\s*(?:target|objective|standard)",
                r"weekly\s*(?:weight|gain|poids)",
                r"\d+\s*(?:days?|jours?|weeks?|semaines?)\s*\d+",
                r"(?:daily|cum)_(?:gain|fcr|feed)",
                r"age_days.*weight_[gl]",
            ]
            pattern_matches = sum(1 for pattern in perf_patterns 
                                if _re.search(pattern, text_lower, _re.IGNORECASE))
            if pattern_matches >= 2 and (multi_col_lines >= 2 or pipe_lines >= 1 or comma_lines >= 3):
                is_table = True
                table_type = "perf_targets"

        # Enhanced performance target detection for CSV content
        if base_meta.get("extraction") == "csv" or base_meta.get("source_file", "").endswith('.csv'):
            # For CSV files, always consider as table and check for performance indicators
            is_table = True
            text_lower = raw.lower()
            
            # Enhanced CSV performance detection
            csv_perf_indicators = [
                "age_days", "weight_g", "weight_lb", "daily_gain", "cum_fcr", 
                "feed_intake", "line", "sex", "unit", "performance", "target",
                "broiler", "layer", "cobb", "ross", "hubbard"
            ]
            
            csv_matches = sum(1 for indicator in csv_perf_indicators 
                            if indicator in text_lower)
            
            if csv_matches >= 4:  # Strong indicator of performance CSV
                table_type = "perf_targets"

    if is_table:
        import re as _re
        table_txt = _re.sub(r"-\s*\n", "", raw).strip()
        meta = dict(base_meta)
        meta["chunk_type"] = "table"
        if table_type:
            meta["table_type"] = table_type
        if species:
            meta["species"] = species
        
        # Enhanced metadata extraction for CSV tables
        if table_type == "perf_targets":
            # Try to extract line information from content
            line_match = _re.search(r"(cobb\s*\d+|ross\s*\d+|hubbard\s*\w+)", table_txt, _re.IGNORECASE)
            if line_match:
                meta["line"] = line_match.group(1).lower().replace(" ", "")
            
            # Try to extract sex information
            if _re.search(r"\b(?:male|female|mixed|as\s*hatched)\b", table_txt, _re.IGNORECASE):
                meta["contains_sex_data"] = True
        
        return [{"text": table_txt, "metadata": meta}]
    else:
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
                    meta = dict(base_meta)
                    if species:
                        meta["species"] = species
                    chunks.append({"text": piece, "metadata": meta})
                buf, cur_len = [], 0
        if buf:
            piece = " ".join(buf).strip()
            if len(piece) >= min_chunk_length:
                meta = dict(base_meta)
                if species:
                    meta["species"] = species
                chunks.append({"text": piece, "metadata": meta})
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
def _extract_pdftotext(fp: str, chunk_size: int, min_chunk_length: int, timeout_per_file: int = 60, species: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
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
        return _enhanced_chunk_text_with_metadata_guarantee(txt, chunk_size, {
            "source_file": fp,
            "extraction": "pdftotext",
        }, min_chunk_length, species)
    except Exception as e:
        log(f"       · pdftotext failed on {fp}: {e}")
        return None

# ---------------------- Provider: pypdfium2 (PDFium) -------------------- #
def _extract_pypdfium2(fp: str, chunk_size: int, max_pages: int = 0, min_chunk_length: int = 80, species: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
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
                    "page_number": i + 1,
                    "total_pages": len(doc),
                    "extraction": "pypdfium2"
                }
                chunks.extend(_enhanced_chunk_text_with_metadata_guarantee(txt, chunk_size, page_meta, min_chunk_length, species))
            except Exception:
                continue
    except Exception:
        pass
    try:
        doc.close()
    except Exception:
        pass
    return chunks or []

# ---------------------- Enhanced Provider: pymupdf (words-based) ----------------- #
def _extract_pymupdf_with_enhanced_table_detection(fp: str, chunk_size: int, max_pages: int = 0,
                     min_chunk_length: int = 80, max_table_lines: int = 0, species: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Détection de tableaux basée sur les mots (x,y) avec auto-taggage table_type="perf_targets".
    Si table ⇒ texte tabulé (un ou plusieurs chunks si split), sinon texte brut (blocks/text) + chunker.
    """
    if not _pdf_available():
        return None
    import fitz, math, re

    Y_LINE_TOL = 3.5
    X_COL_TOL  = 7.5
    MIN_COLS   = 3

    PERF_TABLE_INDICATORS = [
        r"(?:target|objective|objectif)\s*(?:weight|poids|performance)",
        r"(?:age|week|day|jour|semaine)\s*(?:weight|poids|bw)",
        r"(?:fcr|conversion)\s*(?:target|objective|standard)",
        r"(?:growth|croissance)\s*(?:curve|courbe|standard)",
        r"body\s*weight.*(?:target|objective|standard)",
        r"weekly\s*(?:weight|gain|poids)",
        r"performance\s*(?:standard|objective|target)",
        r"daily.*gain",
        r"cum.*fcr",
    ]

    def _group_words_into_lines(words, y_tol=Y_LINE_TOL):
        words = sorted(words, key=lambda w: (w[1], w[0]))
        lines, cur, cur_y = [], [], None
        for w in words:
            y = w[1]
            if cur_y is None or abs(y - cur_y) <= y_tol:
                cur.append(w)
                cur_y = y if cur_y is None else (cur_y + (y-cur_y)/2.0)
            else:
                if cur: lines.append(cur)
                cur, cur_y = [w], y
        if cur: lines.append(cur)
        out = []
        for L in lines:
            L = sorted(L, key=lambda w: w[0])
            out.append([(w[0], (w[4] or "")) for w in L if (w[4] or "").strip()])
        return [l for l in out if l]

    def _cluster_x(xs, tol=X_COL_TOL):
        xs = sorted(xs)
        if not xs: return []
        clusters, cur = [], [xs[0]]
        for x in xs[1:]:
            if abs(x - cur[-1]) <= tol:
                cur.append(x)
            else:
                clusters.append(sum(cur)/len(cur))
                cur = [x]
        clusters.append(sum(cur)/len(cur))
        return clusters

    def _assign_row_to_cols(row, centers, tol=X_COL_TOL):
        assign = []
        for (x, t) in row:
            j = min(range(len(centers)), key=lambda k: abs(x - centers[k]))
            if abs(x - centers[j]) <= tol:
                assign.append((j, t))
        assign.sort(key=lambda z: z[0])
        out, last, buf = [], None, []
        for j, t in assign:
            if last is None or j == last:
                buf.append(t)
            else:
                out.append((last, " ".join(buf)))
                buf = [t]
            last = j
        if buf: out.append((last, " ".join(buf)))
        return out

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
                words = page.get_text("words")
                page_meta = {
                    "source_file": fp, 
                    "page_number": i + 1,
                    "total_pages": doc.page_count, 
                    "extraction": "pymupdf"
                }

                if not words:
                    txt = page.get_text("text") or ""
                    chunks.extend(_enhanced_chunk_text_with_metadata_guarantee(txt, chunk_size, page_meta, min_chunk_length, species))
                    continue

                lines = _group_words_into_lines(words)
                all_x = [x for row in lines for (x, _) in row]
                centers = _cluster_x(all_x, X_COL_TOL)
                ncols = len(centers)
                assigned = [_assign_row_to_cols(row, centers, X_COL_TOL) for row in lines]
                multi = sum(1 for r in assigned if len(r) >= MIN_COLS)
                ratio = multi / max(1, len(lines))

                is_table = (ncols >= MIN_COLS) and (multi >= 10 or ratio >= 0.25)

                if is_table:
                    order = list(range(ncols))
                    lines_out = []
                    for mapped in assigned:
                        cols = {j: t for (j, t) in mapped}
                        lines_out.append("\t".join((cols.get(j, "").strip() for j in order)))

                    table_text = "\n".join(lines_out).strip()
                    
                    table_type = None
                    if table_text:
                        text_lower = table_text.lower()
                        perf_matches = sum(1 for pattern in PERF_TABLE_INDICATORS 
                                         if re.search(pattern, text_lower, re.IGNORECASE))
                        if perf_matches >= 2:
                            table_type = "perf_targets"

                    if max_table_lines and len(lines_out) > max_table_lines:
                        import math
                        parts = int(math.ceil(len(lines_out) / max_table_lines))
                        for k in range(parts):
                            part = "\n".join(lines_out[k * max_table_lines:(k + 1) * max_table_lines]).strip()
                            if part:
                                meta = dict(page_meta)
                                meta["chunk_type"] = "table"
                                if table_type:
                                    meta["table_type"] = table_type
                                if species:
                                    meta["species"] = species
                                chunks.append({"text": part, "metadata": meta})
                    else:
                        if table_text:
                            meta = dict(page_meta)
                            meta["chunk_type"] = "table"
                            if table_type:
                                meta["table_type"] = table_type
                            if species:
                                meta["species"] = species
                            chunks.append({"text": table_text, "metadata": meta})
                        else:
                            try:
                                blocks = page.get_text("blocks") or []
                                blocks.sort(key=lambda b: (b[1], b[0]))
                                parts_txt = [text for (x0, y0, x1, y1, text, block_no, block_type) in blocks if text]
                                plain = "\n".join(parts_txt).strip()
                            except Exception:
                                plain = page.get_text("text") or ""
                            chunks.extend(_enhanced_chunk_text_with_metadata_guarantee(plain, chunk_size, page_meta, min_chunk_length, species))
                else:
                    try:
                        blocks = page.get_text("blocks") or []
                        blocks.sort(key=lambda b: (b[1], b[0]))
                        parts_txt = [text for (x0, y0, x1, y1, text, block_no, block_type) in blocks if text]
                        plain = "\n".join(parts_txt).strip()
                    except Exception:
                        plain = page.get_text("text") or ""
                    chunks.extend(_enhanced_chunk_text_with_metadata_guarantee(plain, chunk_size, page_meta, min_chunk_length, species))

            except Exception:
                continue
    except Exception:
        pass
    try:
        doc.close()
    except Exception:
        pass
    return chunks or []

# ---------------------- Provider: OCR (PyMuPDF + Tesseract) ------------ #
def _extract_pdf_ocr(
    fp: str,
    chunk_size: int,
    min_chunk_length: int = 80,
    dpi: int = 220,
    lang: str = "eng",
    max_pages: int = 0,
    tesseract_cmd: Optional[str] = None,
    species: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    OCR fallback : rend chaque page en image (PyMuPDF) puis applique Tesseract.
    Passe le texte RAW au chunker (table-first).
    """
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
        import io
    except Exception as e:
        log(f"       · OCR not available (imports failed): {e}")
        return None

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    else:
        cmd_env = os.environ.get("TESSERACT_CMD") or os.environ.get("TESSERACT_PATH")
        if cmd_env:
            pytesseract.pytesseract.tesseract_cmd = cmd_env

    try:
        doc = fitz.open(fp)
    except Exception:
        return None

    chunks: List[Dict[str, Any]] = []
    total = doc.page_count
    if max_pages and total > max_pages:
        total = max_pages

    zoom = max(1.0, float(dpi) / 72.0)

    try:
        for i in range(total):
            try:
                page = doc.load_page(i)
                pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                img = Image.open(io.BytesIO(pm.tobytes("png")))
                txt = ""
                try:
                    txt = pytesseract.image_to_string(img, lang=lang) or ""
                except Exception as e:
                    log(f"       · OCR page {i+1} failed: {e}")
                if not txt.strip():
                    continue
                page_meta = {
                    "source_file": fp,
                    "page_number": i + 1,
                    "total_pages": doc.page_count,
                    "extraction": "ocr",
                    "ocr_dpi": dpi,
                    "ocr_lang": lang,
                }
                chunks.extend(_enhanced_chunk_text_with_metadata_guarantee(txt, chunk_size, page_meta, min_chunk_length, species))
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
    enhanced_metadata: bool = True, min_chunk_length: int = 80,
    max_table_lines: int = 0,
    enable_ocr: bool = False, ocr_dpi: int = 220, ocr_lang: str = "eng",
    tesseract_cmd: Optional[str] = None
) -> Tuple[str, Optional[List[Dict[str, Any]]], Optional[str]]:
    last_err: Optional[str] = None
    for prov in providers:
        prov = prov.strip().lower()
        try:
            if prov == "pdftotext":
                chunks = _extract_pdftotext(fp, chunk_size, min_chunk_length, timeout_router, species)
                if chunks:
                    return prov, chunks, None
            elif prov == "pymupdf":
                chunks = _extract_pymupdf_with_enhanced_table_detection(
                    fp, chunk_size,
                    max_pages=max_pages,
                    min_chunk_length=min_chunk_length,
                    max_table_lines=max_table_lines,
                    species=species
                )
                if chunks:
                    return prov, chunks, None
            elif prov == "pypdfium2":
                chunks = _extract_pypdfium2(fp, chunk_size, max_pages=max_pages, min_chunk_length=min_chunk_length, species=species)
                if chunks:
                    return prov, chunks, None
            elif prov == "ocr":
                if enable_ocr:
                    chunks = _extract_pdf_ocr(
                        fp, chunk_size,
                        min_chunk_length=min_chunk_length,
                        dpi=ocr_dpi, lang=ocr_lang,
                        max_pages=max_pages,
                        tesseract_cmd=tesseract_cmd,
                        species=species
                    )
                    if chunks:
                        return prov, chunks, None
                else:
                    log("       · OCR provider skipped (enable_ocr=False)")
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
        log(f"Cannot load embedding model '{name}': {e}")
        sys.exit(1)

def _have_faiss() -> bool:
    try:
        import faiss  # noqa: F401
        return True
    except Exception:
        return False

# ---- OpenAI (API) ----
def _embed_openai(texts: List[str], model_name: str) -> np.ndarray:
    from openai import OpenAI
    client = OpenAI()
    embs: List[List[float]] = []
    B = 512
    for i in range(0, len(texts), B):
        chunk = texts[i:i+B]
        resp = client.embeddings.create(model=model_name, input=chunk)
        embs.extend([d.embedding for d in resp.data])
    return np.asarray(embs, dtype="float32")

# ---- FastEmbed (ONNX, torch-free) ----
def _embed_fastembed(texts: List[str], model_name: str, batch_size: int = 64) -> np.ndarray:
    from fastembed import TextEmbedding
    emb = TextEmbedding(model_name=model_name)
    vectors = list(emb.embed(texts, batch_size=batch_size))
    return np.asarray(vectors, dtype="float32")

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
    tables_found: int = 0,
    perf_tables_found: int = 0,
    metadata_coverage: float = 0.0,
    embedding_dim: int = 0,
    n_docs: int = 0,
    csv_files_processed: int = 0
) -> None:
    """
    Ajout d'un manifest riche, lisible par le loader:
    - n_chunks (total d'items/chunks)
    - n_docs (nombre de fichiers sources distincts)
    - embedding_dim
    - model_name
    - csv_files_processed
    """
    meta = {
        "species": species,
        "model_name": model_name,
        "embedding_dim": embedding_dim,
        "files_indexed": n_files,
        "n_docs": n_docs,
        "chunks_indexed": n_chunks,
        "csv_files_processed": csv_files_processed,
        "files_sample": files_sample,
        "pdf_scan_summary": pdf_scan_summary or {},
        "quality_stats": quality_stats or {},
        "enhanced_features": enhanced_features,
        "tables_found": tables_found,
        "perf_targets_tables": perf_tables_found,
        "metadata_coverage": metadata_coverage,
        "version": "1.5",
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

# --------------------------- Enhanced CSV utils ---------------------- #
def _is_perf_targets_csv(path: Path) -> bool:
    """
    Enhanced heuristics to detect performance target CSV files:
    1. Direct naming patterns (perf + target/performance)
    2. Path-based detection (breeds folder + known breed names)
    3. Content-based sampling for CSV structure
    """
    if path.suffix.lower() != ".csv":
        return False
    
    name = path.name.lower()
    path_str = str(path).lower()
    
    # Method 1: Direct naming patterns
    if "perf" in name and ("target" in name or "targets" in name or "performance" in name):
        return True
    
    # Method 2: Path-based detection
    if "breeds" in path_str and any(breed in path_str for breed in ["cobb", "ross", "hubbard"]):
        return True
    
    # Method 3: Generic performance indicators in path or name
    perf_indicators = ["performance", "targets", "objectives", "standards", "spec", "specification"]
    if any(indicator in path_str for indicator in perf_indicators):
        return True
    
    # Method 4: Content sampling (peek at first few lines)
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read(1024).lower()  # First 1KB
            csv_perf_headers = [
                "age_days", "weight_g", "weight_lb", "daily_gain", "cum_fcr", 
                "feed_intake", "line", "sex", "unit", "target", "performance"
            ]
            matches = sum(1 for header in csv_perf_headers if header in sample)
            if matches >= 4:  # Strong indication of performance data
                return True
    except Exception:
        pass
    
    return False

def _infer_line_from_path_and_content(path: Path, content_sample: str = "") -> str:
    """
    Enhanced line inference from both path and content
    """
    full_path = str(path).lower()
    name = path.name.lower()
    content = content_sample.lower()
    
    # Known breed patterns
    breed_patterns = {
        r"cobb\s*500": "cobb500",
        r"cobb\s*700": "cobb700", 
        r"ross\s*308": "ross308",
        r"ross\s*708": "ross708",
        r"hubbard\s*flex": "hubbardflex",
        r"isa\s*brown": "isabrown",
        r"lohmann\s*brown": "lohmannbrown"
    }
    
    # Search in path first
    for pattern, breed in breed_patterns.items():
        if re.search(pattern, full_path):
            return breed
    
    # Search in content sample
    for pattern, breed in breed_patterns.items():
        if re.search(pattern, content):
            return breed
    
    # Fallback: extract first alphanumeric token from filename
    match = re.search(r"([a-z0-9]+)", name)
    return match.group(1) if match else "unknown"

def _read_csv_header_enhanced(csv_path: Path) -> Tuple[List[str], str]:
    """
    Read CSV headers and a content sample for analysis
    Returns (headers, content_sample)
    """
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            content = f.read(2048)  # Read first 2KB for analysis
            f.seek(0)
            
            dialect = csv.Sniffer().sniff(content[:1024])
            f.seek(0)
            reader = csv.reader(f, dialect)
            headers = next(reader, [])
            clean_headers = [h.strip() for h in headers if h is not None]
            
            return clean_headers, content
    except Exception:
        # Fallback: simple split
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                content = f.read(2048)
                first_line = content.split('\n')[0] if content else ""
                headers = [h.strip() for h in first_line.split(",")]
                return headers, content
        except Exception:
            return [], ""

def _ensure_tables_dir(out_dir: Path) -> Path:
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    return tables_dir

def _copy_perf_csv_and_manifest(src_csv: Path, tables_dir: Path, species: str) -> None:
    """
    Enhanced CSV copy with better manifest generation
    """
    dst_csv = tables_dir / src_csv.name
    try:
        shutil.copy2(src_csv, dst_csv)
    except Exception as e:
        log(f"   · Warning: Copy failed for {src_csv}: {e}")
        return

    headers, content_sample = _read_csv_header_enhanced(src_csv)
    line = _infer_line_from_path_and_content(src_csv, content_sample)
    
    # Enhanced manifest with better metadata
    manifest = {
        "type": "perf_targets",
        "species": species,
        "line": line,
        "csv": dst_csv.name,
        "source_path": str(src_csv),
        "columns": headers or ["line","sex","unit","age_days","weight_g","weight_lb","daily_gain_g","cum_fcr","source_doc","page"],
        "total_columns": len(headers) if headers else 10,
        "inferred_from": "path_and_content" if line != "unknown" else "filename"
    }
    
    manifest_path = tables_dir / f"{line}_perf_targets.manifest.json"
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"   · Warning: Manifest write failed for {manifest_path}: {e}")

# ------------------------------ CLI parse ------------------------------ #
def _parse_args():
    p = argparse.ArgumentParser(description="Enhanced RAG vector index builder v1.5 with perfect CSV integration.")
    p.add_argument("--src", required=True, help="Document file or directory")
    p.add_argument("--out", required=True, help="Output root directory (indexes saved under <out>/<species>/)")
    p.add_argument("--species", required=True, help="global|broiler|layer|... (free text)")
    p.add_argument("--embeddings", choices=["openai","fastembed","sentencetransformers"], default="openai", help="Embedding provider")
    p.add_argument("--embed-model", default="text-embedding-3-small",
                   help="Embedding model name (OpenAI: text-embedding-3-small/-3-large; FastEmbed: BAAI/bge-small-en-v1.5; ST: sentence-transformers/all-MiniLM-L6-v2)")
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
    p.add_argument("--pdf-providers", default="pdftotext,pymupdf,pypdfium2,router",
                   help="Provider order for PDF processing")
    p.add_argument("--chunk-size", type=int, default=2000,
                   help="Text chunk size (default: 2000)")
    p.add_argument("--max-pages", type=int, default=0,
                   help="Max pages per PDF (0 = no limit)")

    # Table split option (0 = off)
    p.add_argument("--max-table-lines", type=int, default=0,
                   help="Split detected table pages every N lines (0=off)")

    # OCR options
    p.add_argument("--enable-ocr", action=argparse.BooleanOptionalAction, default=False,
                   help="Enable OCR fallback provider (requires Tesseract). Default: False")
    p.add_argument("--ocr-dpi", type=int, default=220,
                   help="Rendering DPI for OCR images. Default: 220")
    p.add_argument("--ocr-lang", default="eng",
                   help="Tesseract language(s), e.g. 'eng' or 'eng+fra'. Default: eng")
    p.add_argument("--tesseract-cmd", default=None,
                   help="Absolute path to tesseract.exe (overrides PATH). Optional.")

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
    provider = getattr(args, "embeddings", "openai").lower()
    model_name = args.embed_model

    exts = tuple((e if e.startswith(".") else f".{e}").lower().strip()
                 for e in args.exts.split(",") if e.strip())

    out_dir = (out_root / species)
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"Enhanced RAG Index Builder v1.5 - Perfect CSV Integration")
    log(f"Source root: {src}")
    log(f"Output root: {out_root}")
    log(f"Species to build: {species}")
    log(f"Embeddings provider: {provider}")
    log(f"Embedding model: {model_name}")
    log(f"Enhanced metadata: {args.enhanced_metadata}")
    log(f"Quality filtering: {args.enable_quality_filter}")
    log(f"Providers order: {args.pdf_providers}")
    if args.enable_ocr:
        log(f"OCR: enabled (dpi={args.ocr_dpi}, lang={args.ocr_lang})")
    log(f"\n--- Building enhanced '{species}' index with perfect CSV integration")
    log(f"   · src: {src}")
    log(f"   · out: {out_dir}")

    if not src.exists():
        log(f"ERROR: Source path not found: {src}")
        return 1

    files = sorted(_iter_files_local(str(src), exts, recursive=args.recursive))
    if not files:
        log("   · no files detected")
        log("\nBuild completed. Total chunks indexed: 0")
        return 0

    # === ENHANCED CSV PROCESSING: Both table structure AND RAG indexing ===
    tables_dir = _ensure_tables_dir(out_dir)
    perf_csvs = [Path(f) for f in files if _is_perf_targets_csv(Path(f))]
    all_csvs = [Path(f) for f in files if Path(f).suffix.lower() == ".csv"]
    
    csv_chunks_for_indexing: List[Dict[str, Any]] = []
    csv_files_processed = 0
    
    log(f"\nProcessing CSV files: {len(all_csvs)} total, {len(perf_csvs)} detected as performance targets")
    
    # Process performance target CSV files (dual processing)
    if perf_csvs:
        log(f"Preparing perf_targets tables -> {tables_dir}")
        for csv_fp in perf_csvs:
            # 1. Copy to tables/ directory (existing functionality)
            _copy_perf_csv_and_manifest(csv_fp, tables_dir, species)
            
            # 2. ALSO index in RAG for searchability
            try:
                with open(csv_fp, "r", encoding="utf-8", errors="ignore") as f:
                    csv_content = f.read()
                
                if csv_content.strip():
                    # Create enhanced chunks with performance target metadata
                    base_meta = {
                        "source_file": str(csv_fp),
                        "extraction": "csv",
                        "file_type": "csv_perf_targets",
                        "table_type": "perf_targets",
                        "chunk_type": "table"
                    }
                    
                    csv_chunks = _enhanced_chunk_text_with_metadata_guarantee(
                        csv_content, args.chunk_size, base_meta, args.min_chunk_length, species
                    )
                    
                    csv_chunks_for_indexing.extend(csv_chunks)
                    csv_files_processed += 1
                    
                    if args.verbose:
                        log(f"   · {csv_fp.name}: copied to tables/ + indexed {len(csv_chunks)} chunks")
                
            except Exception as e:
                log(f"   · Warning: Error processing perf CSV {csv_fp.name}: {e}")
    
    # Process other CSV files (RAG indexing only)
    other_csvs = [csv for csv in all_csvs if csv not in perf_csvs]
    if other_csvs:
        log(f"Processing other CSV files: {len(other_csvs)}")
        for csv_fp in other_csvs:
            try:
                with open(csv_fp, "r", encoding="utf-8", errors="ignore") as f:
                    csv_content = f.read()
                
                if csv_content.strip():
                    base_meta = {
                        "source_file": str(csv_fp),
                        "extraction": "csv",
                        "file_type": "csv_data"
                    }
                    
                    csv_chunks = _enhanced_chunk_text_with_metadata_guarantee(
                        csv_content, args.chunk_size, base_meta, args.min_chunk_length, species
                    )
                    
                    csv_chunks_for_indexing.extend(csv_chunks)
                    csv_files_processed += 1
                    
                    if args.verbose:
                        log(f"   · {csv_fp.name}: indexed {len(csv_chunks)} chunks")
            
            except Exception as e:
                log(f"   · Warning: Error processing CSV {csv_fp.name}: {e}")
    
    log(f"CSV processing complete: {csv_files_processed} files, {len(csv_chunks_for_indexing)} chunks for indexing")

    # Optional PDF health scan
    scan_summary: Dict[str, int] = {"scanned": 0, "copy_restricted": 0, "redactions": 0}
    pdf_health_rows: List[Dict[str, Any]] = []
    if args.scan_pdf:
        pdf_files = [f for f in files if Path(f).suffix.lower() == ".pdf"]
        log(f"\nScanning PDF health: {len(pdf_files)} files")
        for f in pdf_files:
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
                with open(out_dir / "pdf_health.csv", "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(pdf_health_rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(pdf_health_rows)
                log(f"   · PDF health report saved: {len(pdf_health_rows)} entries")
            except Exception:
                pass

    # Process non-CSV files
    log(f"\nProcessing non-CSV files...")
    items: List[Dict[str, Any]] = []
    n_chunks = 0
    providers = [p.strip().lower() for p in (args.pdf_providers or "").split(",") if p.strip()]
    
    # Add CSV chunks first
    items.extend(csv_chunks_for_indexing)
    n_chunks += len(csv_chunks_for_indexing)

    qstats: Dict[str, Any] = {}
    non_csv_files = [f for f in files if Path(f).suffix.lower() != ".csv"]

    for i, fp in enumerate(non_csv_files, start=1):
        suf = Path(fp).suffix.lower()
        if args.verbose:
            log(f"   · [{i}/{len(non_csv_files)}] {fp}")

        if suf == ".pdf":
            if args.auto_clean_redactions and args.scan_pdf:
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
            prov, out_chunks, last_err = _try_enhanced_providers_for_pdf(
                fp=fp, species=species, providers=providers,
                chunk_size=args.chunk_size, max_pages=args.max_pages,
                timeout_router=args.timeout_per_file,
                enhanced_metadata=args.enhanced_metadata,
                min_chunk_length=args.min_chunk_length,
                max_table_lines=args.max_table_lines,
                enable_ocr=args.enable_ocr, ocr_dpi=args.ocr_dpi, ocr_lang=args.ocr_lang,
                tesseract_cmd=args.tesseract_cmd
            )
            if out_chunks:
                chunks = out_chunks
            if args.verbose:
                log(f"       · provider={prov} status={'ok' if chunks else 'fail'}")
                if last_err and not chunks:
                    log(f"       · last_error={last_err}")
        else:
            # Other text files: .txt, .md, .html, etc.
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                chunks = _enhanced_chunk_text_with_metadata_guarantee(txt, args.chunk_size, {
                    "source_file": fp,
                    "extraction": "plaintext"
                }, args.min_chunk_length, species)
            except Exception as e:
                last_err = str(e)
                chunks = []

        # Enhanced metadata enrichment
        if chunks and ENHANCED_METADATA_AVAILABLE:
            try:
                additional_context = {"species": species}
                chunks = enhanced_enrich_metadata(
                    chunks, 
                    species=species, 
                    additional_context=additional_context
                )
                if args.verbose:
                    log(f"       · metadata enriched: {len(chunks)} chunks")
            except Exception as e:
                if args.verbose:
                    log(f"       · metadata enrichment failed: {e}")

        # Quality filtering
        if args.enable_quality_filter and chunks:
            chunks, file_qstats = _quality_filter(chunks, min_len=args.min_chunk_length)
            if not qstats:
                qstats = file_qstats
            else:
                qstats["removed"] = qstats.get("removed", 0) + file_qstats.get("removed", 0)
                qstats["kept"] = qstats.get("kept", 0) + file_qstats.get("kept", 0)

        # Add chunks to items
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
                perf_tables = sum(1 for ch in chunks 
                                if ch.get("metadata", {}).get("table_type") == "perf_targets")
                if perf_tables > 0:
                    log(f"       · perf_targets tables: {perf_tables}")
            else:
                log(f"       · no chunks extracted")

    log(f"\nProcessing summary:")
    log(f"   · Total files detected: {len(files)}")
    log(f"   · CSV files processed: {csv_files_processed}")
    log(f"   · Non-CSV files processed: {len(non_csv_files)}")
    log(f"   · Total chunks indexed: {n_chunks}")

    if not items:
        log("\nBuild completed. Total chunks indexed: 0")
        return 0

    # Enhanced validation & statistics
    metadata_coverage = 0.0
    if items and ENHANCED_METADATA_AVAILABLE:
        log(f"\nValidating metadata coverage...")
        metadata_stats = validate_required_metadata(items)
        log(f"   · Metadata coverage:")
        for field, stats in metadata_stats["coverage"].items():
            log(f"     - {field}: {stats['count']}/{metadata_stats['total_chunks']} ({stats['percentage']:.1f}%)")
        metadata_coverage = metadata_stats["critical_coverage"]
        if metadata_coverage < 90:
            log(f"   Warning: Critical metadata coverage only {metadata_coverage:.1f}%")
        else:
            log(f"   Critical metadata coverage: {metadata_coverage:.1f}%")
        
        table_stats = analyze_table_detection(items)
        log(f"   · Table detection:")
        log(f"     - Tables detected: {table_stats['tables_detected']}/{table_stats['total_chunks']} ({table_stats['table_percentage']:.1f}%)")
        log(f"     - Performance tables: {table_stats['perf_targets_tables']}")
        qstats.update({
            "metadata_coverage": metadata_stats["critical_coverage"],
            "tables_detected": table_stats["tables_detected"],
            "perf_targets_tables": table_stats["perf_targets_tables"]
        })

    # Generate embeddings
    texts = [it["text"] for it in items]
    log(f"\nGenerating embeddings with provider={provider} model={model_name} (batch={args.embed_batch_size})")
    log(f"   · Processing {len(texts)} text chunks...")
    
    if provider == "openai":
        embs = _embed_openai(texts, model_name)
        embedding_method = "OpenAI"
    elif provider == "fastembed":
        embs = _embed_fastembed(texts, model_name, batch_size=args.embed_batch_size)
        embedding_method = "FastEmbed"
    else:
        model = _load_model(model_name)
        embs = _embed(model, texts, batch_size=args.embed_batch_size)
        embedding_method = "SentenceTransformers"

    if not _have_faiss():
        log("ERROR: FAISS not available (pip install faiss-cpu).")
        return 1

    # Save index
    log(f"Saving FAISS index and embeddings...")
    _write_faiss(embs, out_dir / "index.faiss")
    np.save(out_dir / "embeddings.npy", embs)

    # Calculate final statistics
    tables_found = sum(1 for it in items if (it.get("metadata", {}).get("chunk_type") == "table"))
    perf_tables_found = sum(1 for it in items if (it.get("metadata", {}).get("table_type") == "perf_targets"))

    # Enhanced index.pkl with complete data
    log(f"Saving enhanced index data...")
    with open(out_dir / "index.pkl", "wb") as f:
        index_data = {
            "documents": items,
            "method": embedding_method,
            "embedding_method": embedding_method,
            "model_name": model_name,
            "embedding_dim": int(embs.shape[1]),
            "enhanced_version": "v1.5",
            "processing_stats": {
                "total_files": len(files),
                "csv_files_processed": csv_files_processed,
                "tables_found": tables_found,
                "perf_targets_tables": perf_tables_found,
                "metadata_coverage": metadata_coverage,
                "quality_stats": qstats
            }
        }
        pickle.dump(index_data, f)

    # Enhanced manifest
    _enhanced_save_meta(
        out_dir, species, model_name,
        n_files=len(files),
        n_chunks=n_chunks,
        files_sample=files[:5],
        pdf_scan_summary=scan_summary,
        quality_stats=qstats,
        enhanced_features=True, 
        tables_found=tables_found,
        perf_tables_found=perf_tables_found,
        metadata_coverage=metadata_coverage,
        embedding_dim=int(embs.shape[1]),
        n_docs=len(files),
        csv_files_processed=csv_files_processed
    )

    # Final summary
    log(f"\n" + "="*60)
    log(f"BUILD COMPLETED SUCCESSFULLY")
    log(f"="*60)
    log(f"Final statistics:")
    log(f"   · Total files processed: {len(files)}")
    log(f"   · CSV files processed: {csv_files_processed}")
    log(f"   · Total chunks indexed: {n_chunks}")
    log(f"   · Tables detected: {tables_found}")
    log(f"   · Performance tables: {perf_tables_found}")
    log(f"   · Embedding dimensions: {embs.shape[1]}")
    log(f"   · Embedding method: {embedding_method}")
    if ENHANCED_METADATA_AVAILABLE:
        log(f"   · Metadata coverage: {metadata_coverage:.1f}%")
    if qstats:
        total_processed = qstats.get('kept', 0) + qstats.get('removed', 0)
        if total_processed > 0:
            log(f"   · Quality filter: {qstats.get('kept', 0)}/{total_processed} chunks kept ({100 * qstats.get('kept', 0) / total_processed:.1f}%)")
    
    log(f"\nGenerated files:")
    log(f"   · {out_dir}/index.faiss (FAISS vector index)")
    log(f"   · {out_dir}/embeddings.npy (NumPy embeddings array)")
    log(f"   · {out_dir}/index.pkl (complete index with documents + metadata)")
    log(f"   · {out_dir}/meta.json (build manifest with statistics)")
    if perf_csvs:
        log(f"   · {out_dir}/tables/ (performance CSV files + JSON manifests)")
    if pdf_health_rows:
        log(f"   · {out_dir}/pdf_health.csv (PDF health analysis)")

    log(f"\n" + "="*60)
    log(f"Enhanced RAG index for '{species}' is ready for queries!")
    log(f"Index location: {out_dir}")
    log(f"="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())