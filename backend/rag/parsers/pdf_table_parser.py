# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterable
import pandas as pd
import re

from .parser_base import BaseParser, ParserCapability, Document


class PDFTableParser(BaseParser):
    """
    🆕 ENHANCED: Extraction de tableaux depuis des PDF via pdfplumber avec auto-taggage table_type.
    - Produit des chunks en Markdown avec metadata['chunk_type'] = 'table'
    - 🆕 Auto-détection table_type="perf_targets" pour tables de performance
    - 🆕 Enrichissement métadonnées automatique (species/line/sex)
    - Laisse le texte/OCR au GeneralTextLikeParser (le routeur l'appelle ensuite)
    - Robuste: essaie deux stratégies d'extraction (lattice via 'lines', stream via 'text')

    Dépendances: pdfplumber>=0.11, pandas
    """

    # Limites pour éviter des chunks-table monstrueux
    MAX_ROWS_PER_CHUNK = 80
    MAX_COLS = 30

    # 🆕 Patterns pour détecter les types de tables
    TABLE_TYPE_PATTERNS = {
        "perf_targets": [
            # Patterns dans les en-têtes de colonnes
            r"(?:target|objective|objectif|standard)",
            r"(?:age|week|day|jour|semaine).*(?:weight|poids|bw)",
            r"(?:body.*weight|poids.*vif|live.*weight)",
            r"(?:fcr|feed.*conversion|conversion.*alimentaire)",
            r"(?:growth|croissance|gain).*(?:target|objectif)",
            r"weekly.*(?:weight|poids|gain)",
            # Patterns dans le contenu
            r"\d+.*(?:days?|jours?).*\d+.*(?:g|kg|lbs?)",
            r"(?:ross|cobb).*(?:308|500|708).*(?:target|objective)"
        ],
        "nutrition_specs": [
            r"(?:protein|protéine|lysine|methionine)",
            r"(?:energy|énergie|kcal|mj)",
            r"(?:calcium|phosphorus|sodium)",
            r"(?:nutrition|nutritional).*(?:requirement|specification)",
            r"(?:feed|aliment).*(?:specification|composition)",
            r"amino.*acid.*(?:requirement|profile)"
        ],
        "vaccination_schedule": [
            r"(?:vaccination|vaccine|vaccin)",
            r"(?:immunization|immunisation).*(?:schedule|programme)",
            r"(?:newcastle|gumboro|bronchitis|marek)",
            r"vaccine.*(?:timing|calendar|calendrier)",
            r"(?:day|jour|week|semaine).*(?:vaccine|vaccin)"
        ],
        "feeding_program": [
            r"(?:feeding|feed|alimentation).*(?:program|programme|schedule)",
            r"(?:starter|grower|finisher|pré.*ponte)",
            r"feed.*(?:phase|transition)",
            r"nutritional.*(?:program|phase)",
            r"(?:phase.*1|phase.*2|phase.*3)"
        ]
    }

    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="PDFTableParser",
            supported_extensions=[".pdf"],
            breed_types=["Any"],
            data_types=["table"],
            quality_score="good",
            description="🆕 Enhanced PDF → tables (markdown) via pdfplumber with auto table_type detection",
            priority=65,  # > GeneralTextLikeParser (50) : passer avant le parseur texte
        )

    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        return 0.75 if Path(file_path).suffix.lower() == ".pdf" else 0.0

    # 🆕 ------------------------ Enhanced Detection Methods ------------------------ #
    
    def _detect_table_type(self, df: pd.DataFrame, file_path: str) -> Optional[str]:
        """
        🆕 Détection automatique du type de table basée sur colonnes et contenu
        """
        if df.empty:
            return None
        
        # Analyser les en-têtes de colonnes
        columns_text = " ".join([str(col).lower() for col in df.columns])
        
        # Analyser un échantillon du contenu
        sample_content = ""
        if len(df) > 0:
            # Prendre les 5 premières lignes pour l'analyse
            sample_rows = df.head(5).to_string().lower()
            sample_content = columns_text + " " + sample_rows
        
        # Analyser aussi le nom de fichier
        filename = Path(file_path).name.lower()
        combined_text = filename + " " + sample_content
        
        # Scorer chaque type de table
        type_scores = {}
        for table_type, patterns in self.TABLE_TYPE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, combined_text, re.IGNORECASE))
                score += matches
            
            if score > 0:
                type_scores[table_type] = score
        
        # Retourner le type avec le meilleur score
        if type_scores:
            best_type = max(type_scores.keys(), key=lambda k: type_scores[k])
            # Seuil minimum pour éviter les faux positifs
            if type_scores[best_type] >= 2:
                return best_type
        
        return None

    def _detect_species_from_table(self, df: pd.DataFrame, file_path: str) -> Optional[str]:
        """
        🆕 Détection de l'espèce depuis le contenu de la table
        """
        # Analyser nom de fichier
        filename = Path(file_path).name.lower()
        
        # Analyser contenu de la table
        table_content = ""
        if not df.empty:
            table_content = df.to_string().lower()
        
        combined = filename + " " + table_content
        
        # Patterns d'espèces
        broiler_patterns = ["ross", "cobb", "broiler", "chair", "meat", "griller", "hubbard"]
        layer_patterns = ["layer", "pondeuse", "lohmann", "hy-line", "isa", "laying", "hen", "egg"]
        
        broiler_score = sum(1 for pattern in broiler_patterns if pattern in combined)
        layer_score = sum(1 for pattern in layer_patterns if pattern in combined)
        
        if broiler_score > layer_score and broiler_score > 0:
            return "broiler"
        elif layer_score > 0:
            return "layer"
        
        return None

    def _detect_line_from_table(self, df: pd.DataFrame, file_path: str) -> Optional[str]:
        """
        🆕 Détection de la lignée depuis le contenu de la table
        """
        filename = Path(file_path).name.lower()
        table_content = df.to_string().lower() if not df.empty else ""
        combined = filename + " " + table_content
        
        # Patterns de lignées avec regex
        line_patterns = {
            r"ross\s*308": "Ross 308",
            r"ross\s*708": "Ross 708", 
            r"cobb\s*500": "Cobb 500",
            r"cobb\s*700": "Cobb 700",
            r"lohmann\s*brown": "Lohmann Brown",
            r"lohmann\s*white": "Lohmann White",
            r"hy[-\s]*line\s*brown": "Hy-Line Brown",
            r"hy[-\s]*line\s*white": "Hy-Line White",
            r"hy[-\s]*line\s*w[-\s]*36": "Hy-Line W-36",
            r"isa\s*brown": "ISA Brown",
            r"isa\s*white": "ISA White"
        }
        
        for pattern, line_name in line_patterns.items():
            if re.search(pattern, combined, re.IGNORECASE):
                return line_name
        
        return None

    def _apply_enhanced_metadata(self, base_metadata: Dict[str, Any], df: pd.DataFrame, file_path: str) -> Dict[str, Any]:
        """
        🆕 Application des métadonnées enrichies automatiquement
        """
        enhanced = base_metadata.copy()
        
        # Détecter automatiquement le type de table
        table_type = self._detect_table_type(df, file_path)
        if table_type:
            enhanced["table_type"] = table_type
        
        # Détecter l'espèce
        species = self._detect_species_from_table(df, file_path)
        if species:
            enhanced["species"] = species
        
        # Détecter la lignée
        line = self._detect_line_from_table(df, file_path)
        if line:
            enhanced["line"] = line
        
        # Ajouter des métadonnées contextuelles
        enhanced["domain"] = "performance" if table_type == "perf_targets" else enhanced.get("domain", "general")
        enhanced["document_type"] = "guide"  # PDF = généralement guide
        enhanced["language"] = "fr" if any(french in df.to_string().lower() for french in ["poids", "âge", "semaine", "jour"]) else "en"
        
        # 🆕 Utiliser enhanced_enrich_metadata si disponible
        try:
            from rag.metadata_enrichment import enhanced_enrich_metadata
            
            # Créer un chunk temporaire pour l'enrichissement
            temp_chunk = [{
                "text": df.to_markdown(index=False),
                "metadata": enhanced
            }]
            
            # Enrichir avec le contexte
            additional_context = {
                "species": species,
                "line": line,
                "table_type": table_type,
                "document_type": "guide"
            }
            
            enriched_chunks = enhanced_enrich_metadata(
                temp_chunk,
                species=species,
                additional_context=additional_context
            )
            
            if enriched_chunks:
                enhanced = enriched_chunks[0].get("metadata", enhanced)
                
        except Exception as e:
            # Fallback: garder les métadonnées de base si enrichissement échoue
            print(f"Warning: Enhanced metadata enrichment failed for PDF table: {e}")
        
        return enhanced

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

    # 🆕 --------------------------- Enhanced parse() ------------------------------- #
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

        total_tables_found = 0

        with pdfplumber.open(file_path) as pdf:
            for pidx, page in enumerate(pdf.pages):
                page_tables_found = 0
                for strategy_idx, settings in enumerate(strategies):
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
                            
                            # 🆕 Métadonnées de base
                            base_meta = self.create_base_metadata(
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
                                    "extraction": "pdf_table_parser"
                                },
                            )
                            
                            # 🆕 Appliquer les métadonnées enrichies
                            enhanced_meta = self._apply_enhanced_metadata(base_meta, seg_df, file_path)
                            
                            docs.append(Document(page_content=md, metadata=enhanced_meta))
                            page_tables_found += 1
                            total_tables_found += 1

                # Rien trouvé avec les deux stratégies → page suivante
                _ = page_tables_found

        # 🆕 Log pour debugging
        if total_tables_found > 0:
            # Compter les types détectés
            detected_types = {}
            detected_species = set()
            for doc in docs:
                table_type = doc.metadata.get("table_type")
                if table_type:
                    detected_types[table_type] = detected_types.get(table_type, 0) + 1
                
                species = doc.metadata.get("species")
                if species:
                    detected_species.add(species)
            
            print(f"✅ PDFTableParser processed {file_path}: {total_tables_found} tables extracted")
            if detected_types:
                print(f"   📊 Table types detected: {detected_types}")
            if detected_species:
                print(f"   🐔 Species detected: {list(detected_species)}")

        return docs

    def get_parser_info(self) -> Dict[str, Any]:
        """
        🆕 Informations sur le parser pour debugging
        """
        return {
            "name": "PDFTableParser",
            "description": "Enhanced PDF table extraction with automatic table_type detection",
            "supported_extensions": [".pdf"],
            "output_chunk_type": "table",
            "automatic_table_types": list(self.TABLE_TYPE_PATTERNS.keys()),
            "species_detection": True,
            "line_detection": True,
            "enhanced_metadata": True,
            "max_rows_per_chunk": self.MAX_ROWS_PER_CHUNK,
            "max_cols": self.MAX_COLS,
            "extraction_strategies": ["lines/lines", "text/text"]
        }