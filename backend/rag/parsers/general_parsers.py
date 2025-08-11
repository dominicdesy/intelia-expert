# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Optional
from pathlib import Path
import logging

from .parser_base import BaseParser, ParserCapability, Document, chunk_text

logger = logging.getLogger(__name__)

class GeneralTextLikeParser(BaseParser):
    """
    PDF (text-first, OCR fallback), TXT, MD, HTML → text chunks.
    MD/HTML: si table détectée en amont, laissez TableParser faire le job.
    """

    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="GeneralTextLikeParser",
            supported_extensions=[".pdf", ".txt", ".md", ".html", ".htm"],
            breed_types=["Any"],
            data_types=["text"],
            quality_score="good",
            description="Generic text parser with PDF OCR fallback",
            priority=50,
        )

    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        ext = Path(file_path).suffix.lower()
        return 0.8 if ext in {".pdf", ".txt", ".md", ".html", ".htm"} else 0.0

    # ---- PDF helpers
    def _pdf_text(self, file_path: str) -> str:
        import fitz  # PyMuPDF
        out = []
        with fitz.open(file_path) as doc:
            for page in doc:
                out.append(page.get_text("text") or "")
        return "\n".join(x for x in out if x).strip()

    def _pdf_ocr(self, file_path: str, lang: str = "eng") -> str:
        try:
            import fitz, pytesseract
            from PIL import Image
            import io
        except Exception as e:
            logger.info("OCR deps not available: %s", e)
            return ""
        lines = []
        with fitz.open(file_path) as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=200, alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                txt = pytesseract.image_to_string(img, lang=lang) or ""
                if txt.strip():
                    lines.append(txt.strip())
        return "\n".join(lines).strip()

    def parse(self, file_path: str) -> List[Document]:
        p = Path(file_path)
        ext = p.suffix.lower()
        text = ""

        if ext == ".pdf":
            try:
                text = self._pdf_text(file_path)
            except Exception:
                text = ""
            if not text:
                # fallback OCR (optional)
                text = self._pdf_ocr(file_path, lang="eng+fra")
        else:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                text = ""

        if not text:
            return []

        docs: List[Document] = []
        for i, chunk in enumerate(chunk_text(text, 1400, 120)):
            d = Document(page_content=chunk, metadata={"chunk_type": "text", "chunk_index": i})
            d.metadata.update(self.create_base_metadata(file_path, {"data_type": "text"}))
            docs.append(d)
        return docs
