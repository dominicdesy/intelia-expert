# -*- coding: utf-8 -*-
"""
parser_router.py — sélection et orchestration des parseurs de documents.

- Fichier OU dossier (itération récursive avec filtre d'extensions).
- Cascade: table-first (CSV/XLSX + PDF tables + OCR tables) → texte (PDF/TXT/MD/HTML, OCR fallback) → fallbacks.
- Agrégation sur PDF: combine les chunks 'table' (pdfplumber + OCR) ET 'text' quand possible.
- Tika désactivable via RAG_DISABLE_TIKA=1.
- Sortie legacy-compatible: route_and_parse(...) renvoie List[ParsedChunk] (text + metadata).
"""

from __future__ import annotations

import importlib
import inspect
import logging
import os
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Type, Set

# Modèle unifié + shim legacy
from .parsers.parser_base import (
    BaseParser,
    Document,
    ParsedChunk,       # shim legacy
    to_parsed_chunk,   # shim legacy
)

# Parseurs "core"
from .parsers.table_parsers import (
    GeneralCSVTableParser,
    GeneralExcelTableParser,
)
from .parsers.general_parsers import GeneralTextLikeParser
from .parsers.fallback_parsers import (
    TikaFallbackParser,
    RawTextFallbackParser,
)

# Tables depuis PDF (pdfplumber) — optionnel
try:
    from .parsers.pdf_table_parser import PDFTableParser
    _HAS_PDF_TABLE = True
except Exception:
    PDFTableParser = None  # type: ignore
    _HAS_PDF_TABLE = False

# Tables via OCR (pytesseract) — optionnel
try:
    from .parsers.ocr_table_parser import OCRTableParser
    _HAS_OCR_TABLE = True
except Exception:
    OCRTableParser = None  # type: ignore
    _HAS_OCR_TABLE = False

logger = logging.getLogger(__name__)


class ParserRouter:
    """
    Routeur de parseurs:
      - score via .can_parse(file_path)
      - essaie dans l'ordre décroissant de score
      - sur PDF: agrège PDFTableParser (si présent) + OCRTableParser (si présent) + GeneralTextLikeParser
      - sinon: arrêt au premier parseur qui retourne des documents
    """

    def __init__(
        self,
        enable_performance_tracking: bool = False,
        include_optional_domain_parsers: bool = True,
    ) -> None:
        self.enable_perf = enable_performance_tracking
        self.parsers: List[BaseParser] = []
        self._load_core_parsers()
        if include_optional_domain_parsers:
            self._load_optional_domain_parsers()
        # trier par priorité (desc) pour égalité de can_parse
        self.parsers.sort(key=lambda p: getattr(p.capability, "priority", 50), reverse=True)
        logger.debug("Parsers loaded: %s", [getattr(p.capability, "name", p.__class__.__name__) for p in self.parsers])

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #
    def _load_core_parsers(self) -> None:
        core: List[BaseParser] = [
            # Table-first
            GeneralCSVTableParser(),
            GeneralExcelTableParser(),
        ]
        if _HAS_PDF_TABLE and PDFTableParser is not None:
            try:
                core.append(PDFTableParser())  # tables via pdfplumber
            except Exception:
                logger.debug("PDFTableParser present but could not be instantiated.", exc_info=True)

        if _HAS_OCR_TABLE and OCRTableParser is not None:
            try:
                core.append(OCRTableParser())  # tables via OCR (scannés)
            except Exception:
                logger.debug("OCRTableParser present but could not be instantiated.", exc_info=True)

        # Texte (PDF/TXT/MD/HTML) avec fallback OCR plein texte
        core.append(GeneralTextLikeParser())

        # Fallbacks universels
        if os.environ.get("RAG_DISABLE_TIKA", "0") != "1":
            core.append(TikaFallbackParser())
        core.append(RawTextFallbackParser())

        self.parsers.extend(core)

    def _load_optional_domain_parsers(self) -> None:
        """Charge les parseurs de domaine si disponibles, sans casser si absents."""
        optional_modules = [
            "rag.parsers.nutrition_parser",
            "rag.parsers.performance_parser",
            "rag.parsers.environment_parser",
            "rag.parsers.health_protocol_parser",
            "rag.parsers.biosecurity_parser",
            # anciens modules possibles
            "rag.parsers.broiler_parsers",
        ]
        seen_classnames = {p.__class__.__name__ for p in self.parsers}

        for modname in optional_modules:
            try:
                mod = importlib.import_module(modname)
            except Exception as e:
                logger.debug("Optional parser module not available: %s (%s)", modname, e)
                continue

            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if not issubclass(obj, BaseParser) or obj is BaseParser:
                    continue
                cls: Type[BaseParser] = obj
                if cls.__name__ in seen_classnames:
                    continue
                try:
                    parser = cls()  # type: ignore[call-arg]
                except Exception:
                    try:
                        parser = cls(**{})  # type: ignore[call-arg]
                    except Exception as e:
                        logger.debug("Skip parser %s from %s (no default ctor): %s", cls.__name__, modname, e)
                        continue
                self.parsers.append(parser)
                seen_classnames.add(cls.__name__)
                logger.debug("Loaded optional parser: %s from %s", cls.__name__, modname)

    # ------------------------------------------------------------------ #
    # Scoring & selection
    # ------------------------------------------------------------------ #
    def _rank_parsers(self, file_path: str) -> List[Tuple[BaseParser, float]]:
        ranked: List[Tuple[BaseParser, float]] = []
        for p in self.parsers:
            try:
                score = float(p.can_parse(file_path))
            except Exception as e:
                logger.debug("can_parse failed for %s: %s", getattr(p.capability, "name", p.__class__.__name__), e)
                score = 0.0
            if score > 0.0:
                ranked.append((p, score))
        ranked.sort(key=lambda t: (t[1], getattr(t[0].capability, "priority", 50)), reverse=True)
        return ranked

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def parse_file(self, file_path: str) -> List[Document]:
        """
        Essaie les parseurs classés; sur PDF, agrège tables(pdfplumber)+tables(OCR)+texte.
        Si tous échouent, renvoie [].
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            logger.warning("Not a file or not found: %s", file_path)
            return []

        ranked = self._rank_parsers(file_path)
        if not ranked:
            logger.debug("No parser claims file: %s", file_path)
            return []

        # Agrégation spécifique PDF
        if path.suffix.lower() == ".pdf":
            out: List[Document] = []

            # 1) Tables via pdfplumber
            if _HAS_PDF_TABLE and PDFTableParser is not None:
                for parser, score in ranked:
                    if isinstance(parser, PDFTableParser):
                        try:
                            docs = parser.parse(file_path)
                            if docs:
                                out.extend(docs)
                                logger.info("Parsed (pdf tables) by %s (%.2f): %s", parser.capability.name, score, file_path)
                        except Exception as e:
                            logger.debug("PDFTableParser failed on %s: %s", file_path, e)
                        break

            # 2) Tables via OCR (utile pour PDF scannés)
            if _HAS_OCR_TABLE and OCRTableParser is not None:
                for parser, score in ranked:
                    if isinstance(parser, OCRTableParser):
                        try:
                            docs = parser.parse(file_path)
                            if docs:
                                out.extend(docs)
                                logger.info("Parsed (ocr tables) by %s (%.2f): %s", parser.capability.name, score, file_path)
                        except Exception as e:
                            logger.debug("OCRTableParser failed on %s: %s", file_path, e)
                        break

            # 3) Texte (inclut fallback OCR plein-texte)
            for parser, score in ranked:
                if isinstance(parser, GeneralTextLikeParser):
                    try:
                        docs = parser.parse(file_path)
                        if docs:
                            out.extend(docs)
                            logger.info("Parsed (text) by %s (%.2f): %s", parser.capability.name, score, file_path)
                    except Exception as e:
                        logger.debug("GeneralTextLikeParser failed on %s: %s", file_path, e)
                    break

            if out:
                return out

            # Sinon, cascade normale (autres parseurs) jusqu'au 1er succès
            for parser, score in ranked:
                # sauter ceux déjà tentés
                skip = False
                if _HAS_PDF_TABLE and PDFTableParser is not None and isinstance(parser, PDFTableParser):
                    skip = True
                if _HAS_OCR_TABLE and OCRTableParser is not None and isinstance(parser, OCRTableParser):
                    skip = True
                if isinstance(parser, GeneralTextLikeParser):
                    skip = True
                if skip:
                    continue
                try:
                    docs = parser.parse(file_path)
                    if docs:
                        logger.info("Parsed by %s (%.2f): %s", getattr(parser.capability, "name", parser.__class__.__name__), score, file_path)
                        return docs
                except Exception as e:
                    logger.debug("Parser %s failed on %s: %s", getattr(parser.capability, "name", parser.__class__.__name__), file_path, e)
            return []

        # Non-PDF: cascade standard
        last_error: Optional[Exception] = None
        for parser, score in ranked:
            try:
                docs = parser.parse(file_path)
                if docs:
                    logger.info("Parsed by %s (%.2f): %s", parser.capability.name, score, file_path)
                    return docs
            except Exception as e:
                last_error = e
                logger.debug("Parser %s failed on %s: %s", parser.capability.name, file_path, e)

        if last_error:
            logger.warning("All parsers failed for %s (last error: %s)", file_path, last_error)
        else:
            logger.info("No content extracted for %s", file_path)
        return []


# ---------------------------------------------------------------------- #
# Helpers dossier/fichiers
# ---------------------------------------------------------------------- #

_DEFAULT_EXTS: Set[str] = {
    ".pdf", ".txt", ".md", ".html", ".htm",
    ".csv", ".xlsx", ".xls",
    ".docx",
}

def _iter_files(root: str, allowed_exts: Optional[Iterable[str]] = None, recursive: bool = True) -> Iterable[str]:
    """Itère sur les fichiers d'un dossier (ou renvoie le fichier si 'root' est un fichier)."""
    p = Path(root)
    if p.is_file():
        yield str(p); return
    if not p.exists():
        return

    allowed = {e.lower() for e in (allowed_exts or _DEFAULT_EXTS)}
    if recursive:
        for dirpath, _, filenames in os.walk(p):
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if not allowed or ext in allowed:
                    yield str(Path(dirpath) / fn)
    else:
        for fn in p.iterdir():
            if fn.is_file():
                ext = fn.suffix.lower()
                if not allowed or ext in allowed:
                    yield str(fn)


# ---------------------------------------------------------------------- #
# Legacy compatibility
# ---------------------------------------------------------------------- #
def route_and_parse(
    path: str,
    *,
    species: Optional[str] = None,
    allowed_exts: Optional[Iterable[str]] = None,
    recursive: bool = True,
) -> List[ParsedChunk]:
    """
    - Accepte un fichier OU un dossier
    - Convertit les Documents en ParsedChunk (text + metadata)
    - Ajoute metadata['inferred_species']=species si fourni
    """
    router = ParserRouter(enable_performance_tracking=False, include_optional_domain_parsers=True)

    p = Path(path)
    file_list: Iterable[str]
    if p.is_file():
        file_list = [str(p)]
    else:
        file_list = _iter_files(path, allowed_exts=allowed_exts, recursive=recursive)

    all_chunks: List[ParsedChunk] = []
    for file_path in file_list:
        docs = router.parse_file(file_path)
        if not docs:
            continue
        for d in docs:
            pc = to_parsed_chunk(d, default_source=str(Path(file_path)))
            if species:
                try:
                    pc.metadata["inferred_species"] = species
                except Exception:
                    pass
            all_chunks.append(pc)

    return all_chunks


__all__ = ["ParserRouter", "route_and_parse", "_iter_files"]
