# -*- coding: utf-8 -*-
from __future__ import annotations
import io
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd

from .parser_base import BaseParser, ParserCapability, Document

class TableUtils:
    @staticmethod
    def df_to_markdown(df: pd.DataFrame, max_rows: int = 50) -> str:
        if len(df) > max_rows:
            df = df.head(max_rows)
        return df.to_markdown(index=False)

    @staticmethod
    def as_table_doc(df: pd.DataFrame, file_path: str, extra_meta: Optional[Dict[str, Any]] = None) -> Document:
        md = TableUtils.df_to_markdown(df)
        meta = {"chunk_type": "table", "rows": int(df.shape[0]), "cols": int(df.shape[1])}
        if extra_meta:
            meta.update(extra_meta)
        return Document(page_content=md, metadata=meta)

class GeneralCSVTableParser(BaseParser):
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="GeneralCSVTableParser",
            supported_extensions=[".csv"],
            breed_types=["Any"],
            data_types=["table", "structured_csv"],
            quality_score="high",
            description="CSV → table-first (markdown) + metadata['chunk_type']='table'",
            priority=60,
        )

    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        return 0.9 if file_path.lower().endswith(".csv") else 0.0

    def parse(self, file_path: str) -> List[Document]:
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
        df = df.dropna(how="all").reset_index(drop=True)
        if df.empty:
            return []
        docs: List[Document] = []
        # 1) table chunk (table-first)
        table_doc = TableUtils.as_table_doc(df, file_path)
        table_doc.metadata.update(self.create_base_metadata(file_path, {"data_type": "structured_csv"}))
        docs.append(table_doc)
        # 2) optional overview
        overview = f"Poultry data table: {len(df)} rows × {len(df.columns)} columns. Columns: {', '.join(df.columns[:20])}"
        ov_doc = Document(page_content=overview, metadata={"chunk_type": "text"})
        ov_doc.metadata.update(self.create_base_metadata(file_path, {"data_type": "csv_overview"}))
        docs.append(ov_doc)
        return docs

class GeneralExcelTableParser(BaseParser):
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="GeneralExcelTableParser",
            supported_extensions=[".xlsx", ".xls"],
            breed_types=["Any"],
            data_types=["table", "structured_excel"],
            quality_score="high",
            description="Excel (multi-sheet) → table-first + sheet metadata",
            priority=58,
        )

    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        return 0.85 if file_path.lower().endswith((".xlsx", ".xls")) else 0.0

    def parse(self, file_path: str) -> List[Document]:
        xls = pd.ExcelFile(file_path)
        docs: List[Document] = []
        for idx, sheet in enumerate(xls.sheet_names):
            df = pd.read_excel(file_path, sheet_name=sheet)
            df = df.dropna(how="all").reset_index(drop=True)
            if df.empty:
                continue
            tdoc = TableUtils.as_table_doc(df, file_path, {"sheet_name": sheet, "sheet_index": idx})
            tdoc.metadata.update(self.create_base_metadata(file_path, {"data_type": "structured_excel"}))
            docs.append(tdoc)

            ov = f"Sheet '{sheet}': {len(df)} rows × {len(df.columns)} columns. Columns: {', '.join(df.columns[:20])}"
            o = Document(page_content=ov, metadata={"chunk_type": "text"})
            o.metadata.update(self.create_base_metadata(file_path, {"data_type": "excel_overview", "sheet_name": sheet}))
            docs.append(o)
        return docs
