# rag/parsers/performance_parser.py
import os
import pandas as pd
import re
from typing import List, Dict, Any
from rag.parsers.parser_base import ParserBase
from rag.metadata_enrichment import enhanced_enrich_metadata

class PerformanceParser(ParserBase):
    name = "performance"

    def supports(self, file_path, mime, hints):
        """
        🆕 Détection élargie pour fichiers de performance
        """
        # Vérification par hints (méthode existante)
        if "performance" in hints.get("domains", []):
            return True
        
        # 🆕 Détection par nom de fichier
        filename = os.path.basename(file_path).lower()
        performance_indicators = [
            "performance", "target", "objective", "objectif", "standard",
            "growth", "croissance", "weight", "poids", "fcr", "conversion",
            "mortality", "mortalité", "viability", "viabilité"
        ]
        
        if any(indicator in filename for indicator in performance_indicators):
            return True
        
        return False

    def _detect_performance_table_type(self, df: pd.DataFrame, content: str) -> str:
        """
        🆕 Détection automatique du type de table de performance
        """
        columns_lower = [str(col).lower() for col in df.columns]
        content_lower = content.lower()
        
        # Patterns pour différents types de tables
        perf_patterns = {
            "perf_targets": [
                # Colonnes typiques objectifs de performance
                any("age" in col and ("weight" in col or "poids" in col) for col in columns_lower),
                any("target" in col or "objective" in col or "objectif" in col for col in columns_lower),
                any("standard" in col for col in columns_lower),
                # Contenu typique
                "target" in content_lower and ("weight" in content_lower or "poids" in content_lower),
                "objective" in content_lower and "performance" in content_lower,
                bool(re.search(r"(?:age|week|day|jour|semaine)\s*(?:weight|poids|bw)", content_lower)),
            ],
            
            "nutrition_specs": [
                any("protein" in col or "lysine" in col or "energy" in col for col in columns_lower),
                any("calcium" in col or "phosphorus" in col for col in columns_lower),
                "nutrition" in content_lower and ("requirement" in content_lower or "specification" in content_lower),
            ],
            
            "feeding_program": [
                any("phase" in col or "starter" in col or "grower" in col or "finisher" in col for col in columns_lower),
                any("feed" in col and ("program" in col or "programme" in col) for col in columns_lower),
                "feeding" in content_lower and ("program" in content_lower or "schedule" in content_lower),
            ]
        }
        
        # Score chaque type
        type_scores = {}
        for table_type, patterns in perf_patterns.items():
            score = sum(1 for pattern in patterns if pattern)
            if score > 0:
                type_scores[table_type] = score
        
        # Retourner le type avec le meilleur score
        if type_scores:
            best_type = max(type_scores.keys(), key=lambda k: type_scores[k])
            # Seuil minimum pour éviter les faux positifs
            if type_scores[best_type] >= 2:
                return best_type
        
        # Fallback par défaut pour parser performance
        return "perf_targets"

    def _clean_performance_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🆕 Nettoyage spécialisé des données de performance
        """
        # Copie pour éviter de modifier l'original
        cleaned_df = df.copy()
        
        # Normaliser les noms de colonnes
        cleaned_df.columns = [str(col).strip() for col in cleaned_df.columns]
        
        # Filtrer les colonnes pertinentes pour la performance (méthode existante améliorée)
        performance_columns = []
        for col in cleaned_df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in [
                "age", "weight", "poids", "fcr", "mortality", "mortalité", 
                "conversion", "gain", "target", "objective", "objectif",
                "standard", "viability", "viabilité", "production",
                "protein", "energy", "lysine", "calcium", "phosphorus"
            ]):
                performance_columns.append(col)
        
        # Garder au minimum les colonnes d'origine si aucune détectée
        if performance_columns:
            cleaned_df = cleaned_df[performance_columns]
        
        # Supprimer les lignes complètement vides
        cleaned_df = cleaned_df.dropna(how='all')
        
        # Supprimer les colonnes complètement vides
        cleaned_df = cleaned_df.dropna(axis=1, how='all')
        
        return cleaned_df

    def _extract_species_from_content(self, df: pd.DataFrame, file_path: str) -> str:
        """
        🆕 Extraction de l'espèce depuis le contenu du fichier
        """
        # Analyser le nom de fichier
        filename = os.path.basename(file_path).lower()
        
        # Analyser le contenu du DataFrame
        content = df.to_string().lower()
        combined = filename + " " + content
        
        # Patterns d'espèces
        if any(pattern in combined for pattern in ["ross", "cobb", "broiler", "chair", "meat"]):
            return "broiler"
        elif any(pattern in combined for pattern in ["layer", "pondeuse", "lohmann", "hy-line", "isa"]):
            return "layer"
        
        return None

    def parse(self, file_path, mime):
        """
        🆕 Parsing amélioré avec taggage automatique table_type et métadonnées enrichies
        """
        chunks = []
        
        try:
            # Essayer Excel d'abord, puis CSV
            try:
                df = pd.read_excel(file_path)
            except:
                try:
                    df = pd.read_csv(file_path)
                except:
                    return []
            
            if df.empty:
                return []
            
            # 🆕 Nettoyage spécialisé
            cleaned_df = self._clean_performance_data(df)
            
            if cleaned_df.empty:
                return []
            
            # Convertir en CSV pour le texte
            csv_content = cleaned_df.to_csv(index=False)
            
            # 🆕 Détecter automatiquement le type de table
            table_type = self._detect_performance_table_type(cleaned_df, csv_content)
            
            # 🆕 Extraire l'espèce du contenu
            detected_species = self._extract_species_from_content(cleaned_df, file_path)
            
            # 🆕 Utiliser enhanced_enrich_metadata avec contexte additionnel
            additional_context = {
                "table_type": table_type,
                "chunk_type": "table",
                "domain": "performance",
                "document_type": "technical_sheet"  # Supposer que les fichiers Excel/CSV sont des fiches techniques
            }
            
            if detected_species:
                additional_context["species"] = detected_species
            
            # Créer un chunk unique avec métadonnées enrichies
            chunk_data = [{
                "text": csv_content,
                "metadata": {
                    "source_file": file_path,
                    "extraction": "performance_parser",
                    "chunk_type": "table",
                    "table_type": table_type,
                    "domain": "performance",
                    "original_format": "excel" if file_path.lower().endswith(('.xlsx', '.xls')) else "csv",
                    "rows_count": len(cleaned_df),
                    "columns_count": len(cleaned_df.columns)
                }
            }]
            
            # Appliquer l'enrichissement des métadonnées
            try:
                enriched_chunks = enhanced_enrich_metadata(
                    chunk_data,
                    species=detected_species,
                    additional_context=additional_context
                )
                chunks.extend(enriched_chunks)
            except Exception as e:
                # Fallback vers les métadonnées de base si enrichissement échoue
                print(f"Warning: Enhanced metadata enrichment failed for {file_path}: {e}")
                
                # Utiliser l'ancienne méthode comme fallback
                from rag.metadata_enrichment import enrich_metadata
                basic_metadata = enrich_metadata(file_path, csv_content, chunk_type="table", domain="performance")
                # Ajouter le table_type manuellement
                basic_metadata["table_type"] = table_type
                chunks.append({"text": csv_content, "metadata": basic_metadata})
            
            # 🆕 Log pour debugging
            if chunks:
                print(f"✅ PerformanceParser processed {file_path}: {len(chunks)} chunks, table_type='{table_type}', species='{detected_species}'")
            
            return chunks
            
        except Exception as e:
            print(f"❌ PerformanceParser failed for {file_path}: {e}")
            return []

    def get_supported_extensions(self) -> List[str]:
        """
        🆕 Extensions supportées par le parser de performance
        """
        return ['.xlsx', '.xls', '.csv']

    def get_parser_info(self) -> Dict[str, Any]:
        """
        🆕 Informations sur le parser pour debugging
        """
        return {
            "name": self.name,
            "description": "Enhanced parser for performance data with automatic table_type detection",
            "supported_extensions": self.get_supported_extensions(),
            "output_chunk_type": "table",
            "automatic_table_types": ["perf_targets", "nutrition_specs", "feeding_program"],
            "species_detection": True,
            "enhanced_metadata": True
        }
