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

Exemples PowerShell:
  # Broiler: enhanced processing with quality filtering
  python -m rag.build_rag `
    --src "C:\\intelia_gpt\\documents\\public\\species\\broiler" `
    --out "C:\\intelia_gpt\\intelia-expert\\backend\\rag_index" `
    --species broiler --verbose --auto-clean-redactions `
    --pdf-providers "pdftotext,pypdfium2,pymupdf,router" `
    --chunk-size 3500 --max-pages 60 --timeout-per-file 45 --embed-batch-size 128 `
    --enable-quality-filter --min-chunk-length 50

  # Global: enhanced with metadata enrichment
  python -m rag.build_rag `
    --src "C:\\intelia_gpt\\documents\\public\\common" `
    --out "C:\\intelia_gpt\\intelia-expert\\backend\\rag_index" `
    --species global --verbose --enhanced-metadata `
    --pdf-providers "pdftotext,pypdfium2"
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
    from rag.parser_router import route_and_parse  # type: ignore
    from rag.metadata_enrichment import enhanced_enrich_metadata  # type: ignore
except Exception as e:
    print(f"❌ Import error: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

def _enhanced_route_and_parse_file(file_path: str, species: str, enhanced_metadata: bool = True) -> List[Any]:
    """Enhanced parsing with metadata enrichment"""
    try:
        # Get base chunks from router
        chunks = route_and_parse(file_path, species=species)  # type: ignore[arg-type]
        
        if not enhanced_metadata or not chunks:
            return chunks
        
        # Enhance metadata for each chunk
        enhanced_chunks = []
        for i, chunk in enumerate(chunks):
            try:
                # Extract text and existing metadata
                if hasattr(chunk, 'text'):
                    text = chunk.text
                    existing_meta = getattr(chunk, 'metadata', {}) or {}
                elif isinstance(chunk, dict):
                    text = chunk.get('text') or chunk.get('content') or ''
                    existing_meta = chunk.get('metadata', {}) or {}
                else:
                    text = str(chunk)
                    existing_meta = {}
                
                # Enhance metadata
                enhanced_meta = enhanced_enrich_metadata(
                    file_path=file_path,
                    text=text,
                    chunk_type=existing_meta.get('chunk_type', 'text'),
                    domain=existing_meta.get('domain'),
                    additional_context={
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                        'inferred_species': species,
                        **existing_meta  # Preserve existing metadata
                    }
                )
                
                # Create enhanced chunk
                if hasattr(chunk, 'text'):
                    chunk.metadata = enhanced_meta
                    enhanced_chunks.append(chunk)
                else:
                    enhanced_chunks.append({
                        'text': text,
                        'metadata': enhanced_meta
                    })
                    
            except Exception as e:
                log(f"     ⚠ Warning: metadata enrichment failed for chunk {i}: {e}")
                enhanced_chunks.append(chunk)  # Fallback to original
        
        return enhanced_chunks
        
    except TypeError:
        # Fallback for legacy router
        chunks = route_and_parse(file_path)  # type: ignore[call-arg]
        for c in chunks:
            try:
                if hasattr(c, 'metadata'):
                    c.metadata = c.metadata or {}
                    c.metadata["inferred_species"] = species
                elif isinstance(c, dict):
                    c.setdefault('metadata', {})["inferred_species"] = species
            except Exception:
                pass
        return chunks

# ------------------------------ Enhanced PDF utilities ------------------- #
def _pdf_available():
    try:
        import fitz  # PyMuPDF
        _ = fitz
        return True
    except Exception:
        return False

def _enhanced_page_image_coverage(page):
    """Enhanced image coverage analysis"""
    rect_page = page.rect
    area_page = getattr(rect_page, "get_area", lambda: rect_page.width * rect_page.height)()
    if area_page <= 0:
        return 0.0, 0.0, 0
    
    max_cov = 0.0
    areas = []
    image_count = 0
    
    try:
        imgs = page.get_images(full=True)
        image_count = len(imgs)
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
    return max_cov, avg_cov, image_count

def _enhanced_scan_single_pdf(fp: str) -> Dict[str, Any]:
    """Enhanced PDF analysis with comprehensive health scoring"""
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
        "total_images": 0,
        "redaction_annots": 0,
        "avg_text_length": 0,
        "quality_score": 0.0,  # New comprehensive quality score
        "processing_recommendation": "unknown"  # New processing recommendation
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
    text_lengths = []
    total_images = 0

    # Enhanced page analysis
    for i in range(pages):
        try:
            pg = doc[i]
        except Exception:
            continue
        
        # Text analysis
        try:
            txt = pg.get_text("text") or ""
            text_length = len(txt.strip())
            if text_length > 50:  # Meaningful text threshold
                text_pages += 1
                text_lengths.append(text_length)
        except Exception:
            txt = ""

        # Enhanced image analysis
        mx, av, img_count = _enhanced_page_image_coverage(pg)
        max_cov_all = max(max_cov_all, mx)
        covs.append(av)
        total_images += img_count

        # Redaction detection
        if _has_redaction_annots(pg):
            redacts += 1

    # Calculate enhanced metrics
    info["text_pages"] = text_pages
    info["text_pages_ratio"] = round((text_pages / pages) if pages else 0.0, 3)
    info["max_image_coverage"] = round(max_cov_all, 3)
    info["avg_image_coverage"] = round(sum(covs)/len(covs) if covs else 0.0, 3)
    info["redaction_annots"] = redacts
    info["total_images"] = total_images
    info["avg_text_length"] = round(sum(text_lengths)/len(text_lengths) if text_lengths else 0, 1)

    # Enhanced quality scoring (0-1 scale)
    quality_factors = []
    
    # Text coverage factor (0-1)
    text_factor = min(info["text_pages_ratio"] * 1.2, 1.0)
    quality_factors.append(("text_coverage", text_factor, 0.4))  # 40% weight
    
    # Text quality factor (based on average text length)
    text_quality_factor = min(info["avg_text_length"] / 1000, 1.0) if info["avg_text_length"] > 0 else 0
    quality_factors.append(("text_quality", text_quality_factor, 0.3))  # 30% weight
    
    # Image balance factor (not too many images overwhelming text)
    image_factor = max(0, 1.0 - info["max_image_coverage"]) if info["max_image_coverage"] > 0.5 else 1.0
    quality_factors.append(("image_balance", image_factor, 0.2))  # 20% weight
    
    # Technical factors
    technical_factor = 1.0
    if info["is_encrypted"]: technical_factor -= 0.5
    if not info["can_copy"]: technical_factor -= 0.3
    if redacts > 0: technical_factor -= 0.2
    technical_factor = max(0, technical_factor)
    quality_factors.append(("technical", technical_factor, 0.1))  # 10% weight
    
    # Calculate weighted quality score
    quality_score = sum(score * weight for _, score, weight in quality_factors)
    info["quality_score"] = round(quality_score, 3)

    # Enhanced status classification
    if info["is_encrypted"]:
        info["status"] = "Encrypted"
        info["processing_recommendation"] = "decrypt_required"
    elif not info["can_copy"]:
        info["status"] = "CopyRestricted"
        info["processing_recommendation"] = "ocr_required"
    elif redacts > 0:
        info["status"] = "RedactionAnnots"
        info["processing_recommendation"] = "clean_and_process"
    elif info["text_pages_ratio"] < 0.1 and info["max_image_coverage"] > 0.85:
        info["status"] = "LikelyScanned"
        info["processing_recommendation"] = "ocr_required"
    elif info["quality_score"] < 0.3:
        info["status"] = "LowQuality"
        info["processing_recommendation"] = "review_manual"
    elif info["quality_score"] > 0.8:
        info["status"] = "HighQuality"
        info["processing_recommendation"] = "standard_processing"
    else:
        info["status"] = "OK"
        info["processing_recommendation"] = "standard_processing"
    
    try:
        doc.close()
    except Exception:
        pass
    return info

def _has_redaction_annots(page):
    """Enhanced redaction detection"""
    import fitz
    try:
        annots = page.annots(types=[fitz.PDF_ANNOT_REDACT])
        return annots is not None
    except Exception:
        try:
            a = page.first_annot
            while a:
                if "Redact" in str(a.type):
                    return True
                a = a.next
        except Exception:
            pass
    return False

def _scan_pdfs(files: List[str], out_csv: Path) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Enhanced PDF scanning with comprehensive analysis"""
    if not _pdf_available():
        log("ℹ️  PDF scan skipped: PyMuPDF (fitz) is not installed. pip install pymupdf")
        return [], {}
    
    pdfs = [f for f in files if Path(f).suffix.lower() == ".pdf"]
    if not pdfs:
        return [], {}
    
    log(f"   • Scanning {len(pdfs)} PDF files with enhanced analysis...")
    rows = []
    
    for i, fp in enumerate(pdfs):
        if i % 10 == 0:
            log(f"     Scanning PDF {i+1}/{len(pdfs)}...")
        
        try:
            rows.append(_enhanced_scan_single_pdf(fp))
        except Exception as e:
            rows.append({"status": f"ScanError: {e}", "file": fp})

    # Enhanced sorting by quality score and status
    status_priority = {
        "HighQuality": 0, "OK": 1, "LowQuality": 2, 
        "LikelyScanned": 3, "RedactionAnnots": 4, 
        "CopyRestricted": 5, "Encrypted": 6
    }
    
    rows.sort(key=lambda r: (
        status_priority.get(r.get("status", "OK"), 99),
        -float(r.get("quality_score", 0.0) or 0.0),
        -float(r.get("text_pages_ratio", 0.0) or 0.0),
        r.get("file", "").lower()
    ))
    
    # Save enhanced CSV
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "status", "file", "quality_score", "processing_recommendation",
        "is_encrypted", "can_copy", "pages", "text_pages", "text_pages_ratio",
        "max_image_coverage", "avg_image_coverage", "total_images",
        "redaction_annots", "avg_text_length"
    ]
    
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in cols})

    # Enhanced summary with quality distribution
    from collections import Counter as _Counter
    status_counter = _Counter(r["status"] for r in rows)
    quality_distribution = _Counter()
    
    for r in rows:
        score = r.get("quality_score", 0.0) or 0.0
        if score >= 0.8:
            quality_distribution["high"] += 1
        elif score >= 0.5:
            quality_distribution["medium"] += 1
        else:
            quality_distribution["low"] += 1
    
    log(f"   • PDF analysis summary:")
    log(f"     Status distribution: {dict(status_counter)}")
    log(f"     Quality distribution: {dict(quality_distribution)}")
    
    # Show top quality files
    high_quality = [r for r in rows if r.get("quality_score", 0) > 0.8][:5]
    if high_quality:
        log(f"   • Top quality files:")
        for r in high_quality:
            qs = r.get("quality_score", 0.0)
            tr = r.get("text_pages_ratio", 0.0)
            log(f"     - {r['status']:<12} quality={qs:.2f} text_ratio={tr:.2f} {r.get('file','')}")
    
    log(f"   • Enhanced PDF analysis saved to: {out_csv}")
    return rows, dict(status_counter)

def _strip_redactions(src: str, dst: str) -> bool:
    """
    Version corrigée de la fonction de nettoyage des redactions
    """
    if not _pdf_available():
        return False
    
    import fitz
    
    try:
        doc = fitz.open(src)
    except Exception as e:
        log(f"       ✗ Failed to open PDF: {e}")
        return False
    
    modified = False
    redactions_removed = 0
    
    try:
        # Vérifier si le document peut être modifié
        if doc.is_encrypted:
            log(f"       ✗ PDF is encrypted, cannot clean: {src}")
            doc.close()
            return False
        
        # Parcourir toutes les pages
        for page_num, page in enumerate(doc):
            try:
                # Méthode 1: Chercher les annotations de redaction par type
                redact_annots = []
                try:
                    # Essayer la méthode moderne
                    redact_annots = page.annots(types=[fitz.PDF_ANNOT_REDACT])
                    if redact_annots:
                        for annot in redact_annots:
                            try:
                                page.delete_annot(annot)
                                modified = True
                                redactions_removed += 1
                            except Exception as e:
                                log(f"       ⚠ Failed to delete annotation: {e}")
                except Exception:
                    # Fallback: méthode manuelle
                    pass
                
                # Méthode 2: Parcours manuel de toutes les annotations
                annot = page.first_annot
                while annot:
                    next_annot = annot.next
                    try:
                        # Vérifier si c'est une redaction par type d'annotation
                        annot_type_str = str(annot.type)
                        annot_type_num = getattr(annot, 'type', None)
                        
                        # Types de redaction possibles
                        is_redaction = (
                            "Redact" in annot_type_str or 
                            "redact" in annot_type_str.lower() or
                            annot_type_num == fitz.PDF_ANNOT_REDACT or
                            (hasattr(annot, 'info') and "redact" in annot.info.get('title', '').lower())
                        )
                        
                        if is_redaction:
                            try:
                                page.delete_annot(annot)
                                modified = True
                                redactions_removed += 1
                            except Exception as e:
                                log(f"       ⚠ Failed to delete redaction annotation: {e}")
                    except Exception as e:
                        log(f"       ⚠ Error processing annotation: {e}")
                    
                    annot = next_annot
                    
            except Exception as e:
                log(f"       ⚠ Error processing page {page_num}: {e}")
                continue
        
        # Si aucune modification, pas besoin de sauvegarder
        if not modified:
            log(f"       ℹ No redactions found to clean in: {src}")
            doc.close()
            return False
        
        # Créer le dossier de destination
        out_dir = Path(dst).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder le document nettoyé
        try:
            # Options de sauvegarde optimisées
            doc.save(dst, 
                    deflate=True,           # Compression
                    garbage=4,              # Nettoyage maximal
                    clean=True,             # Nettoyage supplémentaire
                    sanitize=True,          # Suppression de métadonnées sensibles
                    incremental=False,      # Réécriture complète
                    expand=0,               # Pas d'expansion
                    linear=False)           # Pas d'optimisation linéaire
            
            log(f"       ✓ Removed {redactions_removed} redaction annotation(s)")
            doc.close()
            
            # Vérifier que le fichier a été créé et a une taille raisonnable
            if Path(dst).exists() and Path(dst).stat().st_size > 1000:
                return True
            else:
                log(f"       ✗ Output file too small or missing: {dst}")
                return False
                
        except Exception as e:
            log(f"       ✗ Failed to save cleaned PDF: {e}")
            doc.close()
            return False
            
    except Exception as e:
        log(f"       ✗ Unexpected error during cleaning: {e}")
        try:
            doc.close()
        except:
            pass
        return False


def _has_redaction_annots(page) -> bool:
    """
    Version améliorée de la détection des redactions
    """
    import fitz
    
    try:
        # Méthode 1: API moderne
        try:
            redact_annots = page.annots(types=[fitz.PDF_ANNOT_REDACT])
            if redact_annots and len(redact_annots) > 0:
                return True
        except Exception:
            pass
        
        # Méthode 2: Parcours manuel
        annot = page.first_annot
        while annot:
            try:
                annot_type_str = str(annot.type)
                annot_type_num = getattr(annot, 'type', None)
                
                # Vérifications multiples pour la redaction
                if (
                    "Redact" in annot_type_str or 
                    "redact" in annot_type_str.lower() or
                    annot_type_num == fitz.PDF_ANNOT_REDACT or
                    (hasattr(annot, 'info') and annot.info and 
                     "redact" in str(annot.info.get('title', '')).lower())
                ):
                    return True
                    
            except Exception:
                pass
            
            annot = annot.next
            
    except Exception:
        pass
    
    return False









# ------------------------ Enhanced Provider registry -------------------- #
def _enhanced_chunk_text(text: str, size: int, base_meta: Dict[str, Any], min_length: int = 50) -> List[Dict[str, Any]]:
    """Enhanced chunking with quality filtering"""
    text = (text or "").strip()
    if not text or len(text) < min_length:
        return []
    
    # Intelligent chunking based on content type
    is_table = base_meta.get("chunk_type") == "table" or "|" in text[:200]
    
    if is_table:
        # For tables, try to keep them whole if possible
        if len(text) <= size * 1.5:
            return [{"text": text, "metadata": dict(base_meta)}]
    
    out = []
    start = 0
    chunk_index = 0
    
    while start < len(text):
        # Smart boundary detection for better chunking
        end = start + size
        if end < len(text):
            # Look for natural break points
            for boundary in [". ", ".\n", "\n\n", "\n", " "]:
                boundary_pos = text.rfind(boundary, start + size//2, end)
                if boundary_pos > start:
                    end = boundary_pos + len(boundary)
                    break
        
        piece = text[start:end].strip()
        if len(piece) >= min_length:
            chunk_meta = dict(base_meta)
            chunk_meta["chunk_index"] = chunk_index
            chunk_meta["chunk_start"] = start
            chunk_meta["chunk_end"] = end
            chunk_meta["chunk_length"] = len(piece)
            out.append({"text": piece, "metadata": chunk_meta})
            chunk_index += 1
        
        start = end
    
    return out

# Enhanced provider functions with better error handling and metadata
def _extract_pdftotext(fp: str, chunk_size: int, min_chunk_length: int = 50) -> Optional[List[Dict[str, Any]]]:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    try:
        p = subprocess.run([exe, "-layout", "-enc", "UTF-8", "-q", fp, "-"],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        txt = p.stdout.decode("utf-8", errors="ignore")
        return _enhanced_chunk_text(txt, chunk_size, {
            "source_file": fp, 
            "extraction": "pdftotext",
            "extraction_quality": "high" if len(txt) > 1000 else "medium"
        }, min_chunk_length)
    except Exception as e:
        log(f"       · pdftotext failed on {fp}: {e}")
        return None

def _extract_pypdfium2(fp: str, chunk_size: int, max_pages: int = 0, min_chunk_length: int = 50) -> Optional[List[Dict[str, Any]]]:
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
                txt = tp.get_text_bounded() if hasattr(tp, "get_text_bounded") else ""
            try:
                tp.close()
            except Exception:
                pass
            
            txt = (txt or "").strip()
            if not txt:
                continue
                
            chunks.extend(_enhanced_chunk_text(txt, chunk_size, {
                "source_file": fp, 
                "page": i+1, 
                "extraction": "pypdfium2",
                "extraction_quality": "high" if len(txt) > 500 else "medium"
            }, min_chunk_length))
    finally:
        try:
            doc.close()
        except Exception:
            pass
    return chunks or []

def _extract_pymupdf(fp: str, chunk_size: int, max_pages: int = 0, min_chunk_length: int = 50) -> Optional[List[Dict[str, Any]]]:
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
                blocks = page.get_text("blocks") or []
                block_texts = []
                for b in blocks:
                    t = b[4] if len(b) >= 5 else ""
                    if t and t.strip():
                        block_texts.append(t.strip())
                txt = "\n".join(block_texts)
            except Exception:
                txt = page.get_text("text") or ""
            
            txt = txt.strip()
            if not txt:
                continue
                
            chunks.extend(_enhanced_chunk_text(txt, chunk_size, {
                "source_file": fp, 
                "page": i+1, 
                "extraction": "pymupdf",
                "extraction_quality": "high" if len(txt) > 500 else "medium"
            }, min_chunk_length))
    finally:
        try:
            doc.close()
        except Exception:
            pass
    return chunks or []

# ---- Enhanced router with metadata ------------------------------------ #
def _serialize_enhanced_chunks_for_ipc(out):
    """Enhanced serialization preserving metadata"""
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
        
        # Ensure metadata is serializable
        if meta and isinstance(meta, dict):
            clean_meta = {}
            for k, v in meta.items():
                try:
                    json.dumps(v)  # Test serializability
                    clean_meta[k] = v
                except (TypeError, ValueError):
                    clean_meta[k] = str(v)
            meta = clean_meta
        
        ser.append({"text": str(text), "metadata": dict(meta or {})})
    return ser

def _enhanced_router_worker(path: str, species: str, enhanced_metadata: bool, q):
    """Enhanced router worker with metadata enrichment"""
    try:
        out = _enhanced_route_and_parse_file(path, species, enhanced_metadata)
        q.put(("ok", _serialize_enhanced_chunks_for_ipc(out)))
    except Exception as e:
        q.put(("err", str(e)))

def _run_enhanced_router_with_timeout(fp: str, species: str, timeout_s: int, enhanced_metadata: bool = True) -> Tuple[str, Optional[str], Optional[List[Dict[str, Any]]]]:
    """Enhanced router execution with metadata"""
    ctx = _mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_enhanced_router_worker, args=(fp, species, enhanced_metadata, q))
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

# -------------------- Enhanced orchestration ---------------------------- #
def _try_enhanced_providers_for_pdf(
    fp: str, species: str, providers: List[str],
    chunk_size: int, max_pages: int, timeout_router: int,
    enhanced_metadata: bool = True, min_chunk_length: int = 50
) -> Tuple[str, Optional[List[Dict[str, Any]]], Optional[str]]:
    """Enhanced provider cascade with quality assessment"""
    
    for prov in providers:
        prov = prov.strip().lower()
        try:
            if prov == "pdftotext":
                chunks = _extract_pdftotext(fp, chunk_size, min_chunk_length)
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
    """Enhanced metadata saving with quality statistics"""
    meta = {
        "species": species,
        "model": model_name,
        "build_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "num_files": n_files,
        "num_chunks": n_chunks,
        "files_sample": files_sample[:10],
        "pdf_scan_summary": pdf_scan_summary or {},
        "quality_statistics": quality_stats or {},
        "enhanced_features": enhanced_features,
        "version": "enhanced_v1.0"
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

# ------------------------------ Enhanced CLI parsing ------------------- #
def _parse_args():
    p = argparse.ArgumentParser(description="Enhanced RAG vector index builder with advanced metadata.")
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

    # Enhanced scanning and cleaning
    p.add_argument("--scan-pdf", dest="scan_pdf", action=argparse.BooleanOptionalAction, default=True,
                   help="Enhanced PDF health scan and write analysis CSV (default: True)")
    p.add_argument("--auto-clean-redactions", action="store_true", default=False,
                   help="Automatically remove redaction annotations and create clean copies")

    # Enhanced processing options
    p.add_argument("--enhanced-metadata", action="store_true", default=True,
                   help="Enable advanced metadata enrichment (default: True)")
    p.add_argument("--enable-quality-filter", action="store_true", default=False,
                   help="Enable quality filtering of chunks")
    p.add_argument("--min-chunk-length", type=int, default=50,
                   help="Minimum chunk length to include (default: 50)")

    # Provider options
    p.add_argument("--pdf-providers", default="pdftotext,pypdfium2,pymupdf,router",
                   help="Provider order for PDF processing")
    p.add_argument("--chunk-size", type=int, default=1500,
                   help="Text chunk size (default: 1500)")
    p.add_argument("--max-pages", type=int, default=0,
                   help="Max pages per PDF (0 = no limit)")
    p.add_argument("--timeout-per-file", type=int, default=60,
                   help="Timeout for router provider (default: 60s)")

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
    exts = tuple(e.strip().lower() for e in args.exts.split(",") if e.strip())
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
        return 2

    files = list(_iter_files_local(str(src), allowed_exts=exts, recursive=args.recursive))
    log(f"   • files detected: {len(files)}")
    if not files:
        log("⚠️  No files detected. Check --exts or path.")
        return 0

    # 1) Enhanced PDF Scan
    pdf_rows: List[Dict[str, Any]] = []
    pdf_scan_summary: Dict[str, int] | None = None
    if args.scan_pdf:
        try:
            pdf_csv = out_dir / "pdf_analysis.csv"
            pdf_rows, pdf_scan_summary = _scan_pdfs(files, pdf_csv)
        except Exception as e:
            log(f"⚠️  Enhanced PDF scan failed: {e}")

    # 2) Enhanced Auto-clean with validation
    replacement_map: Dict[str, str] = {}
    if args.auto_clean_redactions and pdf_rows:
        if not _pdf_available():
            log("⚠️  auto-clean redactions requires PyMuPDF (pip install pymupdf)")
        else:
            clean_dir = out_dir / "_clean"
            clean_dir.mkdir(parents=True, exist_ok=True)
            targets = [r for r in pdf_rows if r.get("status") == "RedactionAnnots" and r.get("redaction_annots", 0) > 0]
            if targets:
                log(f"   • Enhanced auto-clean: {len(targets)} PDF(s) with redactions")
            for r in targets:
                src_pdf = r["file"]
                dst_pdf = str(clean_dir / (Path(src_pdf).stem + "_clean.pdf"))
                ok = _strip_redactions(src_pdf, dst_pdf)
                if ok:
                    replacement_map[src_pdf] = dst_pdf
                    if args.verbose:
                        log(f"     ✓ cleaned: {src_pdf} → {dst_pdf}")

    # 3) Enhanced Extraction with comprehensive processing
    provider_order = [p.strip() for p in (args.pdf_providers or "").split(",") if p.strip()]
    chunks: List[Dict[str, Any]] = []
    per_ext_counts = Counter()
    per_ext_chunks = Counter()
    errors_by_file: Dict[str, str] = {}
    provider_used_count = Counter()
    quality_stats = {"total_processed": 0, "quality_filtered": 0, "average_chunk_length": 0}

    for fp in files:
        ext = Path(fp).suffix.lower()
        per_ext_counts[ext] += 1
        quality_stats["total_processed"] += 1

        if ext == ".pdf":
            parse_path = replacement_map.get(fp, fp)
            prov, file_chunks, err = _try_enhanced_providers_for_pdf(
                parse_path, species, provider_order,
                chunk_size=args.chunk_size, max_pages=args.max_pages,
                timeout_router=args.timeout_per_file,
                enhanced_metadata=args.enhanced_metadata,
                min_chunk_length=args.min_chunk_length
            )
            if file_chunks:
                # Quality filtering if enabled
                if args.enable_quality_filter:
                    before_count = len(file_chunks)
                    file_chunks = [c for c in file_chunks if len(c.get("text", "")) >= args.min_chunk_length]
                    quality_stats["quality_filtered"] += before_count - len(file_chunks)
                
                if file_chunks:  # Still have chunks after filtering
                    provider_used_count[prov] += 1
                    per_ext_chunks[ext] += len(file_chunks)
                    chunks.extend(file_chunks)
                    if args.verbose:
                        log(f"     ✓ {parse_path}  via {prov} → {len(file_chunks)} chunks")
                else:
                    errors_by_file[fp] = "all chunks filtered out by quality filter"
            else:
                errors_by_file[fp] = err or f"no provider produced chunks (order={provider_order})"
                log(f"     ✗ {parse_path}  → {errors_by_file[fp]}")
        else:
            # Non-PDF → enhanced router
            status, err, file_chunks = _run_enhanced_router_with_timeout(
                fp, species, args.timeout_per_file, args.enhanced_metadata
            )
            if status == "ok" and file_chunks:
                # Quality filtering if enabled
                if args.enable_quality_filter:
                    before_count = len(file_chunks)
                    file_chunks = [c for c in file_chunks if len(c.get("text", "")) >= args.min_chunk_length]
                    quality_stats["quality_filtered"] += before_count - len(file_chunks)
                
                if file_chunks:
                    provider_used_count["router"] += 1
                    per_ext_chunks[ext] += len(file_chunks)
                    chunks.extend(file_chunks)
                    if args.verbose:
                        log(f"     ✓ {fp}  via enhanced router → {len(file_chunks)} chunks")
                else:
                    errors_by_file[fp] = "all chunks filtered out by quality filter"
            else:
                errors_by_file[fp] = err or status
                log(f"     ✗ {fp}  → {errors_by_file[fp]}")

    # 4) Enhanced processing summary
    by_ext = sorted(per_ext_counts.items(), key=lambda x: x[0])
    log("   • Enhanced processing summary by extension:")
    for ext, n in by_ext:
        log(f"       {ext or '(none)'}: files={n}, chunks={per_ext_chunks.get(ext,0)}")
    if provider_used_count:
        log(f"   • providers used: {dict(provider_used_count)}")
    if args.enable_quality_filter:
        log(f"   • quality filtering: {quality_stats['quality_filtered']} chunks filtered")
    if errors_by_file:
        log(f"   • files with errors: {len(errors_by_file)} (showing up to 5)")
        for i, (f, err) in enumerate(errors_by_file.items()):
            if i >= 5: break
            log(f"       - {f}: {err}")

    # 5) Enhanced embeddings + index creation
    n_chunks = len(chunks)
    if n_chunks == 0:
        log("⚠️  0 chunks extracted after processing and filtering.")
        log("   → Consider: reducing quality filters, checking file formats, or increasing timeouts.")
        _enhanced_save_meta(out_dir, species, model_name, n_files=len(files), n_chunks=0, 
                          files_sample=files[:5], pdf_scan_summary=pdf_scan_summary,
                          quality_stats=quality_stats, enhanced_features=True)
        return 0

    # Enhanced normalization and final metadata enrichment
    texts: List[str] = []
    items: List[Dict[str, Any]] = []
    chunk_lengths = []
    
    for i, c in enumerate(chunks):
        text = c.get("text") if isinstance(c, dict) else getattr(c, "text", "")
        meta = c.get("metadata") if isinstance(c, dict) else getattr(c, "metadata", {}) or {}
        meta = dict(meta or {})
        
        # Enhanced metadata finalization
        meta.setdefault("chunk_index", i)
        meta.setdefault("chunk_type", meta.get("chunk_type", "text"))
        meta.setdefault("inferred_species", species)
        meta.setdefault("processing_version", "enhanced_v1.0")
        meta.setdefault("build_timestamp", time.time())
        
        text_str = str(text)
        chunk_lengths.append(len(text_str))
        texts.append(text_str)
        items.append({"text": text_str, "metadata": meta})

    # Update quality statistics
    quality_stats["average_chunk_length"] = sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0

    log(f"   • Enhanced embedding generation for {n_chunks} chunks...")
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
        # Enhanced index data with metadata versioning
        index_data = {
            "documents": items,
            "embeddings": embs.tolist(),  # For compatibility
            "method": "SentenceTransformers",
            "embedding_method": "SentenceTransformers",
            "model_name": model_name,
            "enhanced_version": "v1.0",
            "processing_stats": quality_stats
        }
        pickle.dump(index_data, f)
    
    _enhanced_save_meta(out_dir, species, model_name, n_files=len(files), n_chunks=n_chunks, 
                      files_sample=files[:5], pdf_scan_summary=pdf_scan_summary,
                      quality_stats=quality_stats, enhanced_features=True)

    log(f"\n✅ Enhanced build completed successfully!")
    log(f"   → Total chunks indexed: {n_chunks}")
    log(f"   → Average chunk length: {quality_stats['average_chunk_length']:.1f} chars")
    log(f"   → Index files:")
    log(f"     • {out_dir / 'index.faiss'}")
    log(f"     • {out_dir / 'index.pkl'}")
    log(f"     • {out_dir / 'embeddings.npy'}")
    log(f"     • {out_dir / 'meta.json'}")
    if args.scan_pdf:
        log(f"     • {out_dir / 'pdf_analysis.csv'}")
    if args.auto_clean_redactions:
        log(f"   → Clean copies (if any): {out_dir / '_clean'}")
    
    return 0

if __name__ == "__main__":
    try:
        _mp.freeze_support()
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Fatal error: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)