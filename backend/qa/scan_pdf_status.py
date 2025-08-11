import sys, os, json, math
from pathlib import Path
import fitz  # PyMuPDF

ROOTS = [
    r"C:\intelia_gpt\documents\public\common",
    r"C:\intelia_gpt\documents\public\species\broiler",
    r"C:\intelia_gpt\documents\public\species\layer",
]

ALLOWED = {".pdf"}

def iter_pdfs(root):
    p = Path(root)
    if p.is_file() and p.suffix.lower() == ".pdf":
        yield p
        return
    if not p.exists():
        return
    for dp, _, fns in os.walk(p):
        for fn in fns:
            fp = Path(dp) / fn
            if fp.suffix.lower() in ALLOWED:
                yield fp

def page_image_coverage(page):
    """Approx aire max image / aire page, et moyenne simple."""
    rect_page = page.rect
    area_page = rect_page.get_area() if hasattr(rect_page, "get_area") else (rect_page.width * rect_page.height)
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
            a = (r.get_area() if hasattr(r, "get_area") else (r.width * r.height))
            cov = a / area_page
            areas.append(cov)
            if cov > max_cov:
                max_cov = cov
    avg_cov = sum(areas)/len(areas) if areas else 0.0
    return max_cov, avg_cov

def has_redaction_annots(page):
    try:
        annots = page.annots(types=[fitz.PDF_ANNOT_REDACT])
        return annots is not None
    except Exception:
        # fallback: inspect all annots and look for 'Redact'
        try:
            a = page.annots()
            while a:
                if "Redact" in str(a.type):
                    return True
                a = a.next
        except Exception:
            pass
    return False

def scan_pdf(fp: Path):
    info = {
        "file": str(fp),
        "is_encrypted": None,
        "can_copy": None,
        "pages": 0,
        "text_pages": 0,
        "text_pages_ratio": 0.0,
        "max_image_coverage": 0.0,
        "avg_image_coverage": 0.0,
        "redaction_annots": 0,
        "status": "OK",
    }
    try:
        doc = fitz.open(str(fp))
    except Exception as e:
        info["status"] = f"OpenError: {e}"
        return info

    info["is_encrypted"] = bool(doc.is_encrypted)
    # permissions (si non chiffré)
    can_copy = True
    try:
        # PDF permission bits: 0x10 = copy (PDF 2.0 : fitz.PDF_PERM_COPY)
        perm = getattr(doc, "permissions", None)
        if perm is not None:
            # si le bit COPY (16) n'est pas présent, copie interdite
            can_copy = bool(perm & 16)
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
        txt = ""
        try:
            txt = pg.get_text("text") or ""
        except Exception:
            txt = ""
        if txt.strip():
            text_pages += 1

        mx, av = page_image_coverage(pg)
        max_cov_all = max(max_cov_all, mx)
        covs.append(av)

        if has_redaction_annots(pg):
            redacts += 1

    info["text_pages"] = text_pages
    info["text_pages_ratio"] = round((text_pages / pages) if pages else 0.0, 3)
    info["max_image_coverage"] = round(max_cov_all, 3)
    info["avg_image_coverage"] = round(sum(covs)/len(covs) if covs else 0.0, 3)
    info["redaction_annots"] = redacts

    # heuristique de statut
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
    doc.close()
    return info

def main():
    roots = ROOTS
    if len(sys.argv) > 1:
        roots = sys.argv[1:]
    rows = []
    for root in roots:
        for pdf in iter_pdfs(root):
            rows.append(scan_pdf(pdf))

    # tri: problèmes d'abord
    order = {"Encrypted":0,"CopyRestricted":1,"RedactionAnnots":2,"LikelyScanned":3,"OK":4}
    rows.sort(key=lambda r: (order.get(r["status"], 9), 1 - r["text_pages_ratio"], -r["max_image_coverage"], r["file"].lower()))

    # sortie lisible
    import csv
    out = Path("qa") / "pdf_status.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["status","file","is_encrypted","can_copy","pages","text_pages","text_pages_ratio","max_image_coverage","avg_image_coverage","redaction_annots"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote: {out}  (rows={len(rows)})")

    # affiche un petit résumé
    from collections import Counter
    c = Counter(r["status"] for r in rows)
    print("Summary:", dict(c))
    # et les 10 pires cas
    for r in rows[:10]:
        print(f"- {r['status']:16s}  text_ratio={r['text_pages_ratio']:.2f}  max_img={r['max_image_coverage']:.2f}  redacts={r['redaction_annots']}  {r['file']}")

if __name__ == "__main__":
    main()
