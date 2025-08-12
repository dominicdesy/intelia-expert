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
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import os
import json
import re
import logging
import pandas as pd

logger = logging.getLogger(__name__)

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
    # [PATCH] mapping tolérant
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
            csv_name = data.get("csv") or data.get("file") or data.get("path")
            if not csv_name:
                return None
            csv_path = dir_tables / csv_name
            if not csv_path.exists():
                return None
            ln = data.get("line") or line
            return PerfManifest(line=_canon_line(ln), csv_name=csv_name, path_csv=csv_path)
        except Exception as e:
            logger.debug(f"[PerfManifest] load failed for line={line}: {e}")
            return None

# --------- Store principal --------- #
class PerfStore:
    """
    root: racine du dossier rag_index (par défaut "./rag_index")
    species: sous-dossier (ex: "broiler", "layer", "global", ...)
    Cache: un DataFrame par lignée (line)
    """
    def __init__(self, root: str = "./rag_index", species: str = "broiler"):
        self.root = Path(root)
        self.species = (species or "broiler").strip().lower()

        # [PATCH] autodétection du dossier "tables"
        candidates = [
            self.root / self.species / "tables",             # .../rag_index/broiler/tables
            self.root / "tables" / self.species,             # .../rag_index/tables/broiler
            self.root / "tables",                            # .../rag_index/tables
            Path(os.environ.get(f"RAG_INDEX_{self.species.upper()}", "")).resolve() / "tables",
        ]
        self.dir_tables = next((p for p in candidates if p and p.exists() and p.is_dir()),
                               self.root / self.species / "tables")
        logger.info(f"[PerfStore] tables_dir={self.dir_tables}")

        # caches
        self._cache_df: Dict[str, pd.DataFrame] = {}
        self._cache_manifest: Dict[str, Optional[PerfManifest]] = {}
        self._df_all: Optional[pd.DataFrame] = None  # [PATCH] DF global (compat as_dataframe/df)

    # ——— helpers ——— #
    def _get_manifest(self, line: str) -> Optional[PerfManifest]:
        line = _canon_line(line)
        if line not in self._cache_manifest:
            self._cache_manifest[line] = PerfManifest.load(self.dir_tables, line)
        return self._cache_manifest[line]

    # [PATCH] lecture multi-format (csv/parquet/feather)
    def _read_any(self, path: Path) -> Optional[pd.DataFrame]:
        try:
            ext = path.suffix.lower()
            if ext == ".csv":
                return pd.read_csv(path)
            if ext == ".parquet":
                return pd.read_parquet(path)
            if ext == ".feather":
                return pd.read_feather(path)
            return None
        except Exception as e:
            logger.warning(f"[PerfStore] read failed for {path}: {e}")
            return None

    # [PATCH] normalisation centralisée des colonnes (line/sex/unit/age_days)
    def _normalize_columns(self, df: pd.DataFrame, fallback_line: Optional[str] = None) -> pd.DataFrame:
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

        # sex
        if "sex" in df.columns:
            df["sex"] = (
                df["sex"].astype(str).str.strip().str.lower()
                  .map(_CANON_SEX).fillna(df["sex"].astype(str).str.lower())
            )

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

    # [PATCH] fallback sans manifest: retrouver le fichier correspondant à la lignée
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

    # API déjà utilisée par le dialogue_manager (compat)
    def _load_df(self, line: str) -> Optional[pd.DataFrame]:
        """
        Chargement d'une table pour la lignée.
        1) via manifest si présent ; 2) sinon via scan du dossier tables/
        Normalisation systématique des colonnes.
        """
        line = _canon_line(line)
        if not line:
            return None
        if line in self._cache_df:
            return self._cache_df[line]

        # 1) Manifest
        mf = self._get_manifest(line)
        path = mf.path_csv if mf and mf.path_csv.exists() else None

        # 2) Fallback scan si pas de manifest ou fichier manquant
        if path is None:
            path = self._find_table_for_line(line)

        if path is None:
            logger.info(f"[PerfStore] no table found for line={line} in {self.dir_tables}")
            return None

        df = self._read_any(path)
        if df is None:
            return None

        df = self._normalize_columns(df, fallback_line=line)
        self._cache_df[line] = df
        # invalide le DF global car une nouvelle lignée vient d’être chargée
        self._df_all = None
        return df

    # [PATCH] DF global (compat: as_dataframe + propriété df)
    def as_dataframe(self) -> Optional[pd.DataFrame]:
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

    # ——— API publique ——— #
    def get(self, line: str, sex: str, unit: str, age_days: int) -> Optional[Dict[str, Any]]:
        """
        Retourne un dict standardisé ou None si introuvable.
        Fallback: si (male/female) introuvable, on tente "as_hatched".
        """
        line = _canon_line(line)
        sex = _canon_sex(sex)
        unit = _canon_unit(unit)
        age_days = int(age_days)

        df = self._load_df(line)
        if df is None:
            return None

        def _query(_sex: str):
            q = (
                (df["line"].eq(line)) &
                (df["sex"].eq(_sex)) &
                (df["unit"].eq(unit)) &
                (df["age_days"].eq(age_days))
            )
            hit = df[q]
            return hit.iloc[0].to_dict() if not hit.empty else None

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
                    row = tmp.sort_values(["__d__", "age_days"]).iloc[0].to_dict()
            except Exception:
                row = None
        if row is None:
            return None

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

    # [PATCH] utilitaire debug pratique
    def available_lines(self) -> List[str]:
        if not self.dir_tables.exists():
            return []
        slugs = set()
        for p in self.dir_tables.iterdir():
            if p.is_file() and p.suffix.lower() in (".csv", ".parquet", ".feather"):
                slugs.add(_canon_line(p.stem))
        return sorted(slugs)
