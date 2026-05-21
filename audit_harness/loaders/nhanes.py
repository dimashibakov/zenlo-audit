"""NHANES XPT loader — merges cycle files on SEQN with demographic filters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pyreadstat

from config import DATA_DIR

# NHANES cycle label → file suffix letter (public-release convention).
CYCLE_SUFFIX: dict[str, str] = {
    "2011-2012": "G",
    "2013-2014": "H",
    "2015-2016": "I",
    "2017-2018": "J",
    "2019-2020": "P",  # pre-pandemic partial release uses P in some files
}

# Expected XPT stems per cycle suffix — operator places these in DATA_DIR.
# Each tuple: (filename_stem, required_for_merge)
CYCLE_XPT_FILES: dict[str, list[str]] = {
    "G": ["DEMO_G", "CRP_G", "GLU_G", "BIOPRO_G", "HDL_G", "TRIGLY_G"],
    "H": ["DEMO_H", "CRP_H", "GLU_H", "BIOPRO_H", "HDL_H", "TRIGLY_H"],
    "I": ["DEMO_I", "CRP_I", "GLU_I", "BIOPRO_I", "HDL_I", "TRIGLY_I"],
    "J": ["DEMO_J", "CRP_J", "GLU_J", "BIOPRO_J", "HDL_J", "TRIGLY_J"],
}

# NHANES column → harness biomarker code.
NHANES_COLUMN_MAP: dict[str, str] = {
    "LBXCRP": "HSCRP",
    "LBXGLU": "GLU",
    "LBXIN": "INSULIN",
    "LBXSCA": "CALCIUM",
    "LBDHDD": "HDL",  # HDL cholesterol
    "LBXTR": "TG",
    "LBXGH": "HBA1C",
    "LBXFER": "FERRITIN",
    "LBXESR": "ESR",
    "LBXTC": "TOTAL_CHOL",
    "LBDLDL": "LDL",
}

# Demographics columns retained for cohort / fairness analysis.
DEMO_COLUMNS = ["SEQN", "RIDAGEYR", "RIAGENDR", "RIDRETH3", "RIDRETH1"]


def _read_xpt(path: Path) -> pd.DataFrame:
    df, _meta = pyreadstat.read_xport(str(path))
    return df


def _resolve_xpt_path(data_dir: Path, stem: str) -> Path:
    for ext in (".XPT", ".xpt"):
        candidate = data_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Missing NHANES file: {stem}.XPT in {data_dir}")


def load_xpt_file(data_dir: Path, stem: str) -> pd.DataFrame:
    """Load a single NHANES XPT file by stem (e.g. CRP_J)."""
    return _read_xpt(_resolve_xpt_path(data_dir, stem))


def expected_files_for_cycle(cycle: str) -> list[str]:
    """Return expected XPT stems for a cycle label."""
    suffix = CYCLE_SUFFIX.get(cycle)
    if suffix is None:
        raise ValueError(f"Unknown cycle {cycle!r}. Known: {list(CYCLE_SUFFIX)}")
    return CYCLE_XPT_FILES[suffix]


def load_nhanes_cycle(cycle: str, data_dir: Path | None = None) -> pd.DataFrame:
    """Load and merge NHANES XPT files for a cycle on SEQN.

    Returns a wide DataFrame with demographic fields and mapped biomarker columns
    (harness codes as column names where mapped).
    """
    data_dir = data_dir or DATA_DIR
    suffix = CYCLE_SUFFIX.get(cycle)
    if suffix is None:
        raise ValueError(f"Unknown cycle {cycle!r}. Known: {list(CYCLE_SUFFIX)}")

    stems = CYCLE_XPT_FILES[suffix]
    merged: pd.DataFrame | None = None

    for stem in stems:
        df = load_xpt_file(data_dir, stem)
        if merged is None:
            merged = df
        else:
            merged = merged.merge(df, on="SEQN", how="outer", suffixes=("", "_dup"))
            dup_cols = [c for c in merged.columns if c.endswith("_dup")]
            merged = merged.drop(columns=dup_cols)

    if merged is None:
        raise RuntimeError("No NHANES files loaded")

    # Rename biomarker columns to harness codes.
    rename = {k: v for k, v in NHANES_COLUMN_MAP.items() if k in merged.columns}
    merged = merged.rename(columns=rename)

    merged["cycle"] = cycle
    return merged


def nhanes_sex(row: pd.Series) -> str:
    """Map RIAGENDR (1=M, 2=F) to harness sex label."""
    val = row.get("RIAGENDR")
    if pd.isna(val):
        return "unknown"
    if int(val) == 1:
        return "male"
    if int(val) == 2:
        return "female"
    return "unknown"


def filter_cohort(
    df: pd.DataFrame,
    *,
    min_age: int | None = None,
    max_age: int | None = None,
    sex: str | None = None,
    race_ethnicity: int | None = None,
) -> pd.DataFrame:
    """Filter NHANES cohort by age, sex (RIAGENDR), and RIDRETH3 code."""
    out = df.copy()
    if min_age is not None:
        out = out[out["RIDAGEYR"] >= min_age]
    if max_age is not None:
        out = out[out["RIDAGEYR"] <= max_age]
    if sex == "male":
        out = out[out["RIAGENDR"] == 1]
    elif sex == "female":
        out = out[out["RIAGENDR"] == 2]
    if race_ethnicity is not None and "RIDRETH3" in out.columns:
        out = out[out["RIDRETH3"] == race_ethnicity]
    return out.reset_index(drop=True)


def list_available_files(data_dir: Path | None = None) -> list[str]:
    """List XPT files present in DATA_DIR."""
    data_dir = data_dir or DATA_DIR
    return sorted(p.name for p in data_dir.glob("*.XPT")) + sorted(
        p.name for p in data_dir.glob("*.xpt")
    )


def biomarker_series(df: pd.DataFrame, code: str) -> pd.Series:
    """Get biomarker values by harness code (already renamed) or NHANES column."""
    key = code.upper()
    if key in df.columns:
        return pd.to_numeric(df[key], errors="coerce")
    # Reverse lookup
    for nhanes_col, harness_code in NHANES_COLUMN_MAP.items():
        if harness_code == key and nhanes_col in df.columns:
            return pd.to_numeric(df[nhanes_col], errors="coerce")
    raise KeyError(f"Biomarker {code} not found in DataFrame columns: {list(df.columns)[:20]}...")
