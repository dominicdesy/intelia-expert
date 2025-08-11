# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterable
import io

from .parser_base import BaseParser, ParserCapability, Document

class OCRTableParser(BaseParser):
    """
    Fallback OCR pour extraire des 'tables' depuis des PDF image (ou tables non détectées).
    Principe : rendu page→image (PyMuPDF) → OCR TSV (pytesseract) → regroupe tokens par ligne → colonnes approximatives.
    Produit des chunks Markdown avec metadata['chunk_type'] = 'table' | data_type='ocr_table'.

    Dépendances : pymupdf (fitz), pillow, pytesseract (+ Tesseract installé), pandas
    """

    MAX_ROWS_PER_CHUNK = 80
    MIN_ROWS_TO_KEEP = 4       # évite de créer des 'pseudo-tables' sur du texte courant
    MIN_TOKENS_PER_LINE = 3    # heuristique lignes tabulaires
    Y_MERGE_PX = 6             # tolérance y pour grouper les tokens en lignes

    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="OCRTableParser",
            supported_extensions=[".pdf"],
            breed_types=["Any"],
            data_types=["table"],
            quality_score="ok",
            description="PDF image → OCR TSV → regroupement en tableau",
            priority=62,  # entre PDFTableParser(65) et GeneralTextLikeParser(50)
        )

    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        return 0.6 if Path(file_path).suffix.lower() == ".pdf" else 0.0

    # --------------------------- utils --------------------------- #
    def _page_image(self, page, dpi: int = 220):
        # rend la page en image PNG (bytes) via PyMuPDF
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        return pix.tobytes("png")

    def _ocr_tsv(self, pil_image, lang: str = "eng+fra"):
        import pytesseract
        return pytesseract.image_to_data(pil_image, lang=lang, output_type=pytesseract.Output.DATAFRAME)

    def _group_lines(self, df):
        """ Regroupe tokens en lignes par proximité verticale. """
        import numpy as np
        rows = []
        if df.empty:
            return rows
        # nettoyer
        df = df[df.conf.astype("float32").fillna(0) > 0]
        df = df[df.text.astype(str).fillna("").str.strip() != ""]
        if df.empty:
            return rows
        # ordonner par y puis x
        df = df.sort_values(["top", "left"]).reset_index(drop=True)

        current_y = None
        line = []
        for _, r in df.iterrows():
            y = float(r["top"])
            if current_y is None:
                current_y = y
                line = [r]
                continue
            if abs(y - current_y) <= self.Y_MERGE_PX:
                line.append(r)
            else:
                if line:
                    rows.append(line)
                current_y = y
                line = [r]
        if line:
            rows.append(line)
        return rows

    def _rows_to_markdown(self, rows: List[list]):
        """
        Transforme des lignes de tokens en un tableau markdown approximatif.
        Heuristique : tokens ordonnés par x; on joint par ' | ' ; la 1ère ligne sert d'entête.
        """
        import pandas as pd
        table_rows: List[List[str]] = []
        for line in rows:
            # garde seulement les tokens texte triés par x
            tokens = sorted(line, key=lambda r: float(r["left"]))
            if len(tokens) < self.MIN_TOKENS_PER_LINE:
                continue
            cols = [str(t["text"]).strip() for t in tokens]
            table_rows.append(cols)

        if len(table_rows) < self.MIN_ROWS_TO_KEEP:
            return []

        # aligner les longueurs
        maxc = max(len(r) for r in table_rows)
        table_rows = [r + [""] * (maxc - len(r)) for r in table_rows]

        # première ligne = header
        header = [c if c else f"C{i+1}" for i, c in enumerate(table_rows[0])]
        body = table_rows[1:]
        df = pd.DataFrame(body, columns=header)

        # découpe en segments pour éviter des très gros chunks
        chunks: List[str] = []
        for start in range(0, len(df), self.MAX_ROWS_PER_CHUNK):
            seg = df.iloc[start:start + self.MAX_ROWS_PER_CHUNK, :]
            chunks.append(seg.to_markdown(index=False))
        return chunks

    # --------------------------- parse --------------------------- #
    def parse(self, file_path: str) -> List[Document]:
        try:
            import fitz, pandas as pd
            from PIL import Image
        except Exception:
            return []

        docs: List[Document] = []
        try:
            with fitz.open(str(file_path)) as doc:
                for pidx, page in enumerate(doc):
                    # heuristique : si la page contient déjà du texte vectoriel, laisse le parseur texte principal faire
                    try:
                        if page.get_text("text").strip():
                            continue
                    except Exception:
                        pass

                    # rendu + OCR TSV
                    try:
                        png = self._page_image(page, dpi=220)
                        img = Image.open(io.BytesIO(png))
                    except Exception:
                        continue

                    try:
                        tsv = self._ocr_tsv(img, lang="eng+fra")
                    except Exception:
                        continue

                    rows = self._group_lines(tsv)
                    md_chunks = self._rows_to_markdown(rows)
                    for seg_idx, md in enumerate(md_chunks):
                        meta = self.create_base_metadata(file_path, {
                            "chunk_type": "table",
                            "data_type": "ocr_table",
                            "page_number": int(pidx + 1),
                            "table_segment": int(seg_idx),
                        })
                        docs.append(Document(page_content=md, metadata=meta))
        except Exception:
            return []

        return docs
