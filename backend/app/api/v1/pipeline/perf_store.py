# app/api/v1/pipeline/perf_store.py
# -*- coding: utf-8 -*-
"""
PerfStore — lookup déterministe des objectifs de performance par (line, sex, unit, age_days)
Lecture des CSV déposés par build_rag dans: rag_index/<species>/tables/
Un manifest JSON <line>_perf_targets.manifest.json décrit quel CSV charger.

API principale:
    store = PerfStore(root="rag_index", species="broiler")
    rec = store.get(line="cobb500", sex="male", unit="metric", age_days=14)

Conventions:
- sex ∈ {"male","female","as_hatched"} ; alias tolérés: m,f,mixte,mixed,as hatched...
- unit ∈ {"metric","imperial"} (si absent -> "metric")
- line est en minuscules, sans espaces ni tirets (ex: "cobb500","ross308")
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import json
import pandas as pd

# --------- Normalisations légères --------- #
_CANON_SEX = {
    "male": "male", "m": "male",
    "female": "female", "f": "female",
    "as_hatched": "as_hatched", "ashatched": "as_hatched",
    "mixte": "as_hatched", "mixed": "as_hatched",
    "as hatched": "as_hatched"
}
def _canon_sex(s: Optional[str]) -> str:
    s = (s or "").strip().lower().replace(" ", "_")
    return _CANON_SEX.get(s, s or "as_hatched")

def _canon_unit(u: Optional[str]) -> str:
    u = (u or "metric").strip().lower()
    return "imperial" if u in {"imperial","imp","us"} else "metric"

def _canon_line(l: Optional[str]) -> str:
    l = (l or "").strip().lower().replace(" ", "").replace("-", "")
    return l

# --------- Manifest --------- #
@dataclass
class PerfManifest:
    line: str
    csv_name: str
    path_csv: Path

    @staticmethod
    def load(dir_tables: Path, line: str) -> Optional["PerfManifest"]:
        """Lit tables/<line>_perf_targets.manifest.json"""
        mf = dir_tables / f"{line}_perf_targets.manifest.json"
        if not mf.exists():
            return None
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            csv_name = data.get("csv")
            if not csv_name:
                return None
            csv_path = dir_tables / csv_name
            if not csv_path.exists():
                return None
            ln = data.get("line") or line
            return PerfManifest(line=_canon_line(ln), csv_name=csv_name, path_csv=csv_path)
        except Exception:
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
        self.species = species.strip().lower()
        self.dir_tables = self.root / self.species / "tables"
        self._cache_df: Dict[str, pd.DataFrame] = {}
        self._cache_manifest: Dict[str, Optional[PerfManifest]] = {}

    # ——— helpers ——— #
    def _get_manifest(self, line: str) -> Optional[PerfManifest]:
        line = _canon_line(line)
        if line not in self._cache_manifest:
            self._cache_manifest[line] = PerfManifest.load(self.dir_tables, line)
        return self._cache_manifest[line]

    def _load_df(self, line: str) -> Optional[pd.DataFrame]:
        line = _canon_line(line)
        if line in self._cache_df:
            return self._cache_df[line]
        mf = self._get_manifest(line)
        if not mf:
            return None
        try:
            df = pd.read_csv(mf.path_csv)
        except Exception:
            return None
        # normalisation douce
        for col in ("line","sex","unit"):
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.lower()
        if "sex" in df.columns:
            df["sex"] = df["sex"].map(_CANON_SEX).fillna(df["sex"])
        if "age_days" in df.columns:
            df["age_days"] = df["age_days"].astype(int)
        if "unit" in df.columns:
            df["unit"] = df["unit"].map(_canon_unit)
        # si la colonne line est absente, remplir avec le manifest
        if "line" not in df.columns:
            df["line"] = line
        # colonnes attendues mais optionnelles: weight_g, weight_lb, daily_gain_g, cum_fcr, source_doc, page
        self._cache_df[line] = df
        return df

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
        if row is None and sex in ("male","female"):
            row = _query("as_hatched")
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
