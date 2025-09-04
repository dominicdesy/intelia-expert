# app/api/v1/pipeline/perf_store.py
# -*- coding: utf-8 -*-
"""
PerfStore — lookup déterministe des objectifs de performance par (line, sex, unit, age_days)
Lecture des tableaux déposés par build_rag dans: rag_index/<species>/tables/
Un manifest JSON <line>_perf_targets.manifest.json peut décrire quel fichier charger.

API principale:
    store = PerfStore(root="rag_index", species="broiler")
    rec = store.get(line="cobb500", sex="male", unit="metric", age_days=14)

Conventions:
- sex ∈ {"male","female","as_hatched"} ; alias tolérés: m,f,ah,♂,♀,mixte,mixed,"as hatched"…
- unit ∈ {"metric","imperial"} (si absent -> "metric")
- line est en minuscules, sans espaces ni tirets (ex: "cobb500","ross308")
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import os
import json
import re
import logging
import time

logger = logging.getLogger(__name__)

# [FIX] Import pandas avec gestion d'erreur robuste
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    logger.debug("✅ pandas available for PerfStore")
except ImportError as e:
    logger.error(f"❌ Failed to import pandas: {e}")
    PANDAS_AVAILABLE = False
    # Fallback minimal pour éviter les crashes
    class pd:  # type: ignore
        class DataFrame:
            pass
        @staticmethod
        def read_csv(*args, **kwargs):
            raise ImportError("pandas not available")
        @staticmethod
        def read_parquet(*args, **kwargs):
            raise ImportError("pandas not available")
        @staticmethod
        def read_feather(*args, **kwargs):
            raise ImportError("pandas not available")
        @staticmethod
        def concat(*args, **kwargs):
            raise ImportError("pandas not available")
        @staticmethod
        def isna(value):
            return value is None or (isinstance(value, float) and str(value).lower() == 'nan')

# --------- Normalisations légères --------- #
_CANON_SEX = {
    # canons
    "male": "male", "female": "female", "as_hatched": "as_hatched",
    # alias fréquents
    "m": "male", "f": "female", "ah": "as_hatched",
    "mixte": "as_hatched", "mixed": "as_hatched",
    "as hatched": "as_hatched", "as-hatched": "as_hatched", "ashatched": "as_hatched",
    # symboles
    "♂": "male", "♀": "female",
}

def _canon_sex(s: Optional[str]) -> str:
    s = (s or "").strip().lower().replace(" ", "_")
    return _CANON_SEX.get(s, s or "as_hatched")

def _canon_unit(u: Optional[str]) -> str:
    u = (u or "metric").strip().lower()
    # mapping tolérant
    if u in {"imperial", "imp", "us", "lb", "lbs"}:
        return "imperial"
    if u in {"metric", "si", "g", "gram", "grams", "metrics"}:
        return "metric"
    return "metric"

def _canon_line(l: Optional[str]) -> str:
    l = (l or "").strip().lower()
    return re.sub(r"[-_\s]+", "", l)

# --------- Manifest --------- #
@dataclass
class PerfManifest:
    line: str
    csv_name: str
    path_csv: Path

    @staticmethod
    def load(dir_tables: Path, line: str) -> Optional["PerfManifest"]:
        """Lit tables/<line>_perf_targets.manifest.json si présent."""
        try:
            mf = dir_tables / f"{line}_perf_targets.manifest.json"
            if not mf.exists():
                return None
            data = json.loads(mf.read_text(encoding="utf-8"))

            # résout 'csv' | 'file' | 'path' + logs + normalisation
            csv_name = None
            for key in ("csv", "file", "path"):
                val = data.get(key)
                if val:
                    csv_name = str(val).strip()
                    break
            if not csv_name:
                logger.warning(f"[PerfManifest] missing 'csv|file|path' for line={line}")
                return None

            # supporte chemin relatif/absolu + case-insensitive fallback
            csv_path = Path(csv_name)
            if not csv_path.is_absolute():
                csv_path = (dir_tables / csv_path)
            csv_path = csv_path.resolve()

            if not csv_path.exists():
                # tentative case-insensitive dans dir_tables
                try:
                    lower_target = csv_path.name.lower()
                    csv_path = next(
                        p for p in dir_tables.iterdir()
                        if p.is_file() and p.name.lower() == lower_target
                    )
                except Exception:
                    logger.warning(f"[PerfManifest] file not found at {csv_path} (line={line})")
                    return None

            ln = data.get("line") or line
            return PerfManifest(line=_canon_line(ln), csv_name=csv_name, path_csv=csv_path)
        except Exception as e:
            logger.debug(f"[PerfManifest] load failed for line={line}: {e}")
            return None

# --------- Store principal amélioré --------- #
class PerfStore:
    """
    root: racine du dossier rag_index (par défaut "./rag_index")
    species: sous-dossier (ex: "broiler", "layer", "global", ...)
    Cache: un DataFrame par lignée (line) avec TTL
    """
    def __init__(self, root: str = "./rag_index", species: str = "broiler", cache_ttl: int = 3600):
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for PerfStore but not available")
            
        self.root = Path(root)
        self.species = (species or "broiler").strip().lower()
        self.cache_ttl = cache_ttl  # TTL en secondes (1h par défaut)

        # [FIX] Gestion robuste des variables d'environnement
        env_var = f"RAG_INDEX_{self.species.upper()}"
        env_path = os.environ.get(env_var, "")
        
        # autodétection du dossier "tables"
        candidates = [
            self.root / self.species / "tables",             # .../rag_index/broiler/tables
            self.root / "tables" / self.species,             # .../rag_index/tables/broiler
            self.root / "tables",                            # .../rag_index/tables
        ]
        
        # [FIX] Ajouter le chemin d'environnement seulement s'il n'est pas vide
        if env_path.strip():
            try:
                env_tables_path = Path(env_path).resolve() / "tables"
                candidates.insert(0, env_tables_path)
            except Exception as e:
                logger.warning(f"[PerfStore] Invalid environment path {env_var}={env_path}: {e}")
        
        self.dir_tables = next((p for p in candidates if p and p.exists() and p.is_dir()),
                               self.root / self.species / "tables")
        logger.info(f"[PerfStore] tables_dir={self.dir_tables}")

        # [AMÉLIORATION] Caches avec TTL
        self._cache_df: Dict[str, Tuple[pd.DataFrame, float]] = {}  # (df, timestamp)
        self._cache_manifest: Dict[str, Optional[PerfManifest]] = {}
        self._df_all: Optional[pd.DataFrame] = None  # DF global (compat as_dataframe/df)

    # ——— [NOUVELLE] Conversion sûre pandas vers dict ——— #
    def _safe_to_dict(self, row) -> Dict[str, Any]:
        """Conversion sûre pandas row vers dict avec nettoyage des types numpy/pandas"""
        if not PANDAS_AVAILABLE:
            return {}
            
        result = {}
        try:
            for key, value in row.items():
                if pd.isna(value):
                    result[key] = None
                elif hasattr(value, 'item'):  # numpy scalar
                    try:
                        result[key] = value.item()
                    except:
                        result[key] = str(value)
                else:
                    result[key] = value
            return result
        except Exception as e:
            logger.warning(f"[PerfStore] _safe_to_dict failed: {e}")
            return {}

    # ——— [NOUVELLE] Validation des DataFrames ——— #
    def _validate_df(self, df: pd.DataFrame, line: str) -> bool:
        """Validation basique du DataFrame chargé"""
        if not PANDAS_AVAILABLE or df is None:
            return False
            
        required_cols = {"line", "sex", "unit", "age_days"}
        missing = required_cols - set(df.columns)
        if missing:
            logger.warning(f"[PerfStore] Missing required columns {missing} in table for line={line}")
            return False
            
        if len(df) == 0:
            logger.warning(f"[PerfStore] Empty table for line={line}")
            return False
            
        return True

    # ——— [AMÉLIORATION] Cache avec TTL ——— #
    def _is_cache_valid(self, line: str) -> bool:
        """Vérifie si le cache est encore valide"""
        if line not in self._cache_df:
            return False
        _, timestamp = self._cache_df[line]
        return (time.time() - timestamp) < self.cache_ttl

    def _get_cached_df(self, line: str) -> Optional[pd.DataFrame]:
        """Récupère le DataFrame depuis le cache si valide"""
        if self._is_cache_valid(line):
            df, _ = self._cache_df[line]
            return df
        return None

    def _set_cache_df(self, line: str, df: pd.DataFrame):
        """Met en cache le DataFrame avec timestamp"""
        self._cache_df[line] = (df, time.time())

    # ——— helpers ——— #
    def _get_manifest(self, line: str) -> Optional[PerfManifest]:
        line = _canon_line(line)
        if line not in self._cache_manifest:
            self._cache_manifest[line] = PerfManifest.load(self.dir_tables, line)
        return self._cache_manifest[line]

    # lecture multi-format (csv/parquet/feather)
    def _read_any(self, path: Path) -> Optional[pd.DataFrame]:
        if not PANDAS_AVAILABLE:
            logger.error("[PerfStore] pandas not available for reading files")
            return None
            
        try:
            ext = path.suffix.lower()
            if ext == ".csv":
                return pd.read_csv(path)
            if ext == ".parquet":
                return pd.read_parquet(path)
            if ext == ".feather":
                return pd.read_feather(path)
            logger.warning(f"[PerfStore] unsupported file extension: {ext}")
            return None
        except Exception as e:
            logger.warning(f"[PerfStore] read failed for {path}: {e}")
            return None

    # [FIX CRITIQUE] normalisation centralisée des colonnes (line/sex/unit/age_days)
    def _normalize_columns(self, df: pd.DataFrame, fallback_line: Optional[str] = None) -> pd.DataFrame:
        if not PANDAS_AVAILABLE:
            return df
            
        try:
            # line
            if "line" in df.columns:
                df["line"] = (
                    df["line"].astype(str).str.lower().str.strip()
                      .str.replace(r"[-_\s]+", "", regex=True)
                )
            elif fallback_line:
                df["line"] = _canon_line(fallback_line)

            # unit
            if "unit" in df.columns:
                df["unit"] = df["unit"].astype(str).str.lower().map(_canon_unit)
            else:
                df["unit"] = "metric"

            # [FIX CRITIQUE] sex - évite le problème .fillna() circulaire
            if "sex" in df.columns:
                sex_series = df["sex"].astype(str).str.strip().str.lower()
                sex_mapped = sex_series.map(_CANON_SEX)
                df["sex"] = sex_mapped.fillna("as_hatched")  # Fallback sûr au lieu de la référence circulaire
            else:
                df["sex"] = "as_hatched"

            # age → age_days (tolère "day", "Age (d)", "jours", etc.)
            lower = {str(c).lower(): c for c in df.columns}
            age_src = None
            for key in ["age_days", "day", "days", "age", "age(d)", "age_d", "age (days)", "jours"]:
                if key in lower:
                    age_src = lower[key]
                    break
            if age_src and age_src != "age_days":
                try:
                    df["age_days"] = df[age_src].astype(str).str.extract(r"(\d+)")[0].fillna("0").astype(int)
                except Exception:
                    df["age_days"] = (
                        df[age_src].apply(lambda x: re.sub(r"[^\d]", "", str(x)) if x is not None else "")
                                   .replace("", "0").astype(int)
                    )
            if "age_days" not in df.columns:
                df["age_days"] = 0

            return df
        except Exception as e:
            logger.error(f"[PerfStore] column normalization failed: {e}")
            return df

    # fallback sans manifest: retrouver le fichier correspondant à la lignée
    def _find_table_for_line(self, line: str) -> Optional[Path]:
        if not self.dir_tables.exists():
            return None
        want = _canon_line(line)
        candidates: List[Path] = []
        try:
            for p in self.dir_tables.iterdir():
                if not p.is_file():
                    continue
                if p.suffix.lower() not in (".csv", ".parquet", ".feather"):
                    continue
                base_slug = _canon_line(p.stem)
                if want in base_slug:
                    candidates.append(p)
        except Exception as e:
            logger.warning(f"[PerfStore] listdir failed in {self.dir_tables}: {e}")
            return None

        if not candidates:
            return None
        # priorité: parquet > feather > csv
        def _prio(path: Path) -> int:
            return {".parquet": 0, ".feather": 1, ".csv": 2}.get(path.suffix.lower(), 9)
        candidates.sort(key=_prio)
        return candidates[0]

    # [AMÉLIORATION] API avec cache TTL
    def _load_df(self, line: str) -> Optional[pd.DataFrame]:
        """
        Chargement d'une table pour la lignée avec cache TTL.
        1) cache si valide ; 2) via manifest si présent ; 3) sinon via scan du dossier tables/
        Normalisation systématique des colonnes.
        """
        if not PANDAS_AVAILABLE:
            logger.error("[PerfStore] pandas not available for loading dataframes")
            return None
            
        line = _canon_line(line)
        if not line:
            return None

        # 1) Cache TTL
        cached_df = self._get_cached_df(line)
        if cached_df is not None:
            return cached_df

        # 2) Manifest
        mf = self._get_manifest(line)
        path = mf.path_csv if mf and mf.path_csv.exists() else None

        # 3) Fallback scan si pas de manifest ou fichier manquant
        if path is None:
            path = self._find_table_for_line(line)

        if path is None:
            logger.info(f"[PerfStore] no table found for line={line} in {self.dir_tables}")
            return None

        df = self._read_any(path)
        if df is None:
            return None

        df = self._normalize_columns(df, fallback_line=line)
        
        # [NOUVELLE] Validation
        if not self._validate_df(df, line):
            logger.error(f"[PerfStore] DataFrame validation failed for line={line}")
            return None

        # Cache avec TTL
        self._set_cache_df(line, df)
        
        # invalide le DF global car une nouvelle lignée vient d'être chargée
        self._df_all = None
        return df

    # DF global (compat: as_dataframe + propriété df)
    def as_dataframe(self) -> Optional[pd.DataFrame]:
        if not PANDAS_AVAILABLE:
            logger.error("[PerfStore] pandas not available for dataframe operations")
            return None
            
        if self._df_all is not None:
            return self._df_all
        if not self.dir_tables.exists():
            return None
        frames: List[pd.DataFrame] = []
        # concatène toutes les lignes disponibles
        try:
            for p in self.dir_tables.iterdir():
                if p.is_file() and p.suffix.lower() in (".csv", ".parquet", ".feather"):
                    df = self._read_any(p)
                    if df is None:
                        continue
                    # déduis la lignée depuis le nom de fichier si la colonne line manque
                    fallback_line = _canon_line(p.stem)
                    df = self._normalize_columns(df, fallback_line=fallback_line)
                    if self._validate_df(df, fallback_line):
                        frames.append(df)
        except Exception as e:
            logger.warning(f"[PerfStore] building global DF failed: {e}")
            return None

        if not frames:
            return None
        try:
            self._df_all = pd.concat(frames, ignore_index=True)
            return self._df_all
        except Exception as e:
            logger.warning(f"[PerfStore] concat failed: {e}")
            return None

    @property
    def df(self) -> Optional[pd.DataFrame]:
        return self.as_dataframe()

    # ——— [NOUVELLE] Méthode de diagnostic complète ——— #
    def get_diagnostic_info(self, line: str) -> Dict[str, Any]:
        """Informations complètes pour debugging d'une lignée"""
        line = _canon_line(line)
        df = self._load_df(line)
        
        if df is None:
            return {
                "line": line,
                "error": "table_not_found",
                "available_lines": self.available_lines(),
                "tables_dir": str(self.dir_tables)
            }
        
        try:
            age_values = df["age_days"].dropna().astype(int)
            return {
                "line": line,
                "status": "ok",
                "total_rows": len(df),
                "age_range": [int(age_values.min()), int(age_values.max())] if len(age_values) > 0 else [0, 0],
                "available_sexes": sorted(df["sex"].unique().tolist()),
                "available_units": sorted(df["unit"].unique().tolist()),
                "sample_ages": sorted(age_values.unique()[:10].tolist()),
                "columns": df.columns.tolist(),
                "cache_status": "cached" if self._is_cache_valid(line) else "fresh_load"
            }
        except Exception as e:
            return {
                "line": line,
                "error": "analysis_failed",
                "message": str(e),
                "total_rows": len(df),
                "columns": df.columns.tolist() if hasattr(df, 'columns') else []
            }

    # ——— [AMÉLIORATION] API publique avec conversion sûre ——— #
    def get(self, line: str, sex: str, unit: str, age_days: int) -> Optional[Dict[str, Any]]:
        """
        Retourne un dict standardisé ou None si introuvable.
        Fallback: si (male/female) introuvable, on tente "as_hatched".
        [FIX] Utilise _safe_to_dict pour éviter les problèmes de sérialisation JSON.
        """
        if not PANDAS_AVAILABLE:
            logger.error("[PerfStore] pandas not available for get operations")
            return None
            
        line = _canon_line(line)
        sex = _canon_sex(sex)
        unit = _canon_unit(unit)
        age_days = int(age_days)

        df = self._load_df(line)
        if df is None:
            return None

        def _query(_sex: str):
            try:
                q = (
                    (df["line"].eq(line)) &
                    (df["sex"].eq(_sex)) &
                    (df["unit"].eq(unit)) &
                    (df["age_days"].eq(age_days))
                )
                hit = df[q]
                if not hit.empty:
                    return self._safe_to_dict(hit.iloc[0])  # [FIX] Conversion sûre
                return None
            except Exception as e:
                logger.warning(f"[PerfStore] query failed for {line}/{_sex}/{unit}/{age_days}: {e}")
                return None

        row = _query(sex)
        if row is None and sex in ("male", "female"):
            row = _query("as_hatched")
        if row is None:
            # nearest sur l'âge (fallback utile si âge exact absent)
            try:
                t = int(age_days)
                tmp = df[(df["line"].eq(line)) & (df["unit"].eq(unit))]
                if "sex" in tmp.columns:
                    tmp = tmp[tmp["sex"].isin([sex, "as_hatched"])]
                tmp = tmp.copy()
                tmp["__d__"] = (tmp["age_days"].astype(int) - t).abs()
                if not tmp.empty:
                    row = self._safe_to_dict(tmp.sort_values(["__d__", "age_days"]).iloc[0])
            except Exception as e:
                logger.warning(f"[PerfStore] nearest age lookup failed: {e}")
                row = None
        
        if row is None:
            return None

        # [AMÉLIORATION] Structure de retour standardisée avec nettoyage
        return {
            "line": row.get("line", line),
            "sex": row.get("sex", sex),
            "unit": row.get("unit", unit),
            "age_days": row.get("age_days", age_days),
            "weight_g": row.get("weight_g"),
            "weight_lb": row.get("weight_lb"),
            "daily_gain_g": row.get("daily_gain_g"),
            "cum_fcr": row.get("cum_fcr"),
            "source_doc": row.get("source_doc"),
            "page": row.get("page"),
        }

    # ——— [NOUVELLE] Méthode de requête par plage d'âges ——— #
    def get_range(self, line: str, sex: str, unit: str, age_start: int, age_end: int) -> List[Dict[str, Any]]:
        """Récupère les données sur une plage d'âges"""
        if not PANDAS_AVAILABLE:
            return []
            
        line = _canon_line(line)
        sex = _canon_sex(sex)
        unit = _canon_unit(unit)

        df = self._load_df(line)
        if df is None:
            return []

        try:
            q = (
                (df["line"].eq(line)) &
                (df["sex"].eq(sex)) &
                (df["unit"].eq(unit)) &
                (df["age_days"] >= age_start) &
                (df["age_days"] <= age_end)
            )
            hits = df[q].sort_values("age_days")
            return [self._safe_to_dict(row) for _, row in hits.iterrows()]
        except Exception as e:
            logger.warning(f"[PerfStore] get_range failed: {e}")
            return []

    # utilitaire debug pratique
    def available_lines(self) -> List[str]:
        if not self.dir_tables.exists():
            return []
        slugs = set()
        try:
            for p in self.dir_tables.iterdir():
                if p.is_file() and p.suffix.lower() in (".csv", ".parquet", ".feather"):
                    slugs.add(_canon_line(p.stem))
            return sorted(slugs)
        except Exception as e:
            logger.warning(f"[PerfStore] available_lines failed: {e}")
            return []

    # ——— [NOUVELLE] Nettoyage du cache ——— #
    def clear_cache(self):
        """Vide le cache (utile pour les tests ou rechargement forcé)"""
        self._cache_df.clear()
        self._cache_manifest.clear()
        self._df_all = None
        logger.info("[PerfStore] Cache cleared")

    def cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        current_time = time.time()
        valid_entries = sum(1 for _, (_, ts) in self._cache_df.items() 
                          if (current_time - ts) < self.cache_ttl)
        return {
            "total_cached_lines": len(self._cache_df),
            "valid_cached_lines": valid_entries,
            "cache_ttl_seconds": self.cache_ttl,
            "manifest_cache_size": len(self._cache_manifest)
        }
