# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterable
import pandas as pd

from .parser_base import BaseParser, ParserCapability, Document


class PDFTableParser(BaseParser):
    """
    Extraction de tableaux depuis des PDF via pdfplumber.
    - Produit des chunks en Markdown avec metadata['chunk_type'] = 'table'
    - Laisse le texte/OCR au GeneralTextLikeParser (le routeur l’appelle ensuite)
    - Robuste: essaie deux stratégies d’extraction (lattice via 'lines', stream via 'text')

    Dépendances: pdfplumber>=0.11, pandas
    """

    # Limites pour éviter des chunks-table monstrueux
    MAX_ROWS_PER_CHUNK = 80
    MAX_COLS = 30

    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="PDFTableParser",
            supported_extensions=[".pdf"],
            breed_types=["Any"],
            data_types=["table"],
            quality_score="good",
            description="PDF → tables (markdown) via pdfplumber",
            priority=65,  # > GeneralTextLikeParser (50) : passer avant le parseur texte
        )

    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        return 0.75 if Path(file_path).suffix.lower() == ".pdf" else 0.0

    # ---------------------------- utils -------------------------------- #
    def _rows_to_df(self, rows: List[List[str]]) -> Optional[pd.DataFrame]:
        if not rows:
            return None
        # drop lignes 100% vides
        rows = [[(c or "").strip() for c in r] for r in rows]
        rows = [r for r in rows if any(c for c in r)]
        if not rows:
            return None

        # Heuristique header + body
        header = rows[0]
        body = rows[1:] if len(rows) > 1 else []

        # Aligner les longueurs
        ncols = max(len(header), *(len(r) for r in body)) if body else len(header)
        header = (header + [""] * (ncols - len(header)))[:ncols]
        body = [(r + [""] * (ncols - len(r)))[:ncols] for r in body]

        # Construit DataFrame
        cols = [h if h else f"C{i+1}" for i, h in enumerate(header)]
        df = pd.DataFrame(body, columns=cols)

        # Nettoyage basique
        # - drop colonnes complètement vides
        df = df.replace({"": None}).dropna(axis=1, how="all").fillna("")
        if df.empty:
            return None

        # Renommer les colonnes 'Unnamed: n' éventuelles
        df.columns = [c if str(c).strip() else f"C{i+1}" for i, c in enumerate(df.columns)]
        # Limiter le nb de colonnes
        if df.shape[1] > self.MAX_COLS:
            df = df.iloc[:, : self.MAX_COLS]
        return df

    def _df_to_markdown_chunks(self, df: pd.DataFrame) -> Iterable[pd.DataFrame]:
        """Découpe verticalement les très gros tableaux pour rester lisibles en RAG."""
        if df.shape[0] <= self.MAX_ROWS_PER_CHUNK:
            yield df
            return
        for start in range(0, df.shape[0], self.MAX_ROWS_PER_CHUNK):
            yield df.iloc[start : start + self.MAX_ROWS_PER_CHUNK, :]

    # --------------------------- parse() ------------------------------- #
    def parse(self, file_path: str) -> List[Document]:
        try:
            import pdfplumber  # type: ignore
        except Exception:
            # pdfplumber absent -> pas de tables (le routeur passera au parseur texte)
            return []

        docs: List[Document] = []

        # Deux stratégies: 'lines' (grilles nettes / lattice) puis 'text' (colonnes à l'espacement / stream)
        strategies = (
            {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
            {"vertical_strategy": "text",  "horizontal_strategy": "text"},
        )

        with pdfplumber.open(file_path) as pdf:
            for pidx, page in enumerate(pdf.pages):
                page_tables_found = 0
                for settings in strategies:
                    try:
                        tables = page.extract_tables(table_settings=settings) or []
                    except Exception:
                        # fallback: API par défaut si settings non supportés
                        try:
                            tables = page.extract_tables() or []
                        except Exception:
                            tables = []

                    for tidx, rows in enumerate(tables):
                        df = self._rows_to_df(rows)
                        if df is None or df.empty:
                            continue

                        for seg_idx, seg_df in enumerate(self._df_to_markdown_chunks(df)):
                            md = seg_df.to_markdown(index=False)
                            meta = self.create_base_metadata(
                                file_path,
                                {
                                    "chunk_type": "table",
                                    "data_type": "pdf_table",
                                    "page_number": int(pidx + 1),
                                    "table_index": int(tidx),
                                    "table_segment": int(seg_idx),
                                    "rows": int(seg_df.shape[0]),
                                    "cols": int(seg_df.shape[1]),
                                    "pdfplumber_strategy": f"{settings.get('vertical_strategy')}/{settings.get('horizontal_strategy')}",
                                },
                            )
                            docs.append(Document(page_content=md, metadata=meta))
                            page_tables_found += 1

                # Rien trouvé avec les deux stratégies → page suivante
                _ = page_tables_found

        return docs
