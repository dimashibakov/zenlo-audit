"""NHANES XPT loader — per-cycle subfolders, real file manifests, graceful skips."""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import pandas as pd
import pyreadstat

from config import DATA_DIR

logger = logging.getLogger(__name__)

# NHANES cycle label → public-release file suffix letter.
CYCLE_SUFFIX: dict[str, str] = {
    "2007-2008": "E",
    "2011-2012": "G",
    "2013-2014": "H",
    "2015-2016": "I",
    "2017-2018": "J",
}

# Expected XPT stems per suffix (placed under DATA_DIR/<cycle>/).
# Missing optional files log a warning and are skipped — load does not crash.
CYCLE_XPT_FILES: dict[str, list[str]] = {
    "E": ["DEMO_E", "GLU_E", "INS_E", "GHB_E", "HDL_E", "TRIGLY_E", "TCHOL_E"],
    "G": ["DEMO_G", "GLU_G", "INS_G", "GHB_G", "HDL_G", "TRIGLY_G", "TCHOL_G"],
    "H": ["DEMO_H", "GLU_H", "INS_H", "GHB_H", "HDL_H", "TRIGLY_H", "TCHOL_H"],
    "I": ["DEMO_I", "GLU_I", "INS_I", "GHB_I", "HDL_I", "TRIGLY_I", "TCHOL_I"],
    "J": ["DEMO_J", "GLU_J", "INS_J", "GHB_J", "HDL_J", "TRIGLY_J", "TCHOL_J"],
}

# NHANES laboratory column → harness biomarker code (after merge + insulin normalize).
NHANES_COLUMN_MAP: dict[str, str] = {
    "LBXCRP": "HSCRP",
    "LBXGLU": "GLU",
    "LBXIN": "INSULIN",
    "LBXSCA": "CALCIUM",
    "LBDHDD": "HDL",
    "LBXTR": "TG",
    "LBXGH": "HBA1C",
    "LBXFER": "FERRITIN",
    "LBXESR": "ESR",
    "LBXTC": "TOTAL_CHOL",
    "LBDLDL": "LDL",
}

# Biomarkers not present in cycle-I layout (no CRP/BIOPRO files on DO server).
CYCLE_I_UNAVAILABLE_BIOMARKERS = frozenset({"HSCRP", "CRP", "CALCIUM", "FERRITIN", "ESR", "LDL", "PTH"})

DEMO_COLUMNS = ["SEQN", "RIDAGEYR", "RIAGENDR", "RIDRETH3", "RIDRETH1"]

# pmol/L → µU/mL (NHANES documents LBDINSI conversion factor ≈ 6.945).
INSULIN_SI_TO_UIU_ML = 6.945


def cycle_data_dir(data_dir: Path, cycle: str) -> Path:
    """Resolve DATA_DIR/<cycle>/ (e.g. ./data/nhanes/2015-2016/)."""
    return data_dir / cycle


def _read_xpt(path: Path) -> pd.DataFrame:
    df, _meta = pyreadstat.read_xport(str(path))
    return df


def _resolve_xpt_path(cycle_dir: Path, stem: str) -> Path | None:
    for ext in (".XPT", ".xpt"):
        candidate = cycle_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def normalize_insulin_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Prefer LBXIN (µU/mL); convert LBDINSI (pmol/L) if SI column only."""
    out = df.copy()
    if "LBXIN" in out.columns:
        out["INSULIN"] = pd.to_numeric(out["LBXIN"], errors="coerce")
    elif "LBDINSI" in out.columns:
        out["INSULIN"] = pd.to_numeric(out["LBDINSI"], errors="coerce") / INSULIN_SI_TO_UIU_ML
    return out


def load_xpt_file(cycle_dir: Path, stem: str) -> pd.DataFrame:
    """Load a single NHANES XPT file by stem from a cycle directory."""
    path = _resolve_xpt_path(cycle_dir, stem)
    if path is None:
        raise FileNotFoundError(f"Missing NHANES file: {stem}.XPT in {cycle_dir}")
    df = _read_xpt(path)
    if stem.startswith("INS_"):
        df = normalize_insulin_columns(df)
    return df


def expected_files_for_cycle(cycle: str) -> list[str]:
    suffix = CYCLE_SUFFIX.get(cycle)
    if suffix is None:
        raise ValueError(f"Unknown cycle {cycle!r}. Known: {list(CYCLE_SUFFIX)}")
    return CYCLE_XPT_FILES[suffix]


def load_nhanes_cycle(cycle: str, data_dir: Path | None = None) -> pd.DataFrame:
    """Load and merge NHANES XPT files for a cycle on SEQN.

    Files are read from ``DATA_DIR/<cycle>/``. Missing optional files produce
    warnings and are skipped. DEMO_{suffix} is required; if absent, raises.
    """
    data_dir = data_dir or DATA_DIR
    suffix = CYCLE_SUFFIX.get(cycle)
    if suffix is None:
        raise ValueError(f"Unknown cycle {cycle!r}. Known: {list(CYCLE_SUFFIX)}")

    cycle_dir = cycle_data_dir(data_dir, cycle)
    stems = CYCLE_XPT_FILES[suffix]
    load_warnings: list[str] = []
    loaded_files: list[str] = []
    merged: pd.DataFrame | None = None

    for stem in stems:
        path = _resolve_xpt_path(cycle_dir, stem)
        if path is None:
            msg = f"Missing optional NHANES file {stem}.XPT in {cycle_dir} — skipping"
            load_warnings.append(msg)
            warnings.warn(msg, stacklevel=2)
            logger.warning(msg)
            continue

        df = _read_xpt(path)
        if stem.startswith("INS_"):
            df = normalize_insulin_columns(df)
        loaded_files.append(path.name)

        if merged is None:
            merged = df
        else:
            merged = merged.merge(df, on="SEQN", how="outer", suffixes=("", "_dup"))
            dup_cols = [c for c in merged.columns if c.endswith("_dup")]
            merged = merged.drop(columns=dup_cols)

    demo_stem = f"DEMO_{suffix}"
    if merged is None or demo_stem not in loaded_files:
        raise FileNotFoundError(
            f"Required demographics file {demo_stem}.XPT not found in {cycle_dir}. "
            f"Loaded: {loaded_files or 'none'}"
        )

    rename = {k: v for k, v in NHANES_COLUMN_MAP.items() if k in merged.columns}
    merged = merged.rename(columns=rename)

    merged["cycle"] = cycle
    merged.attrs["load_warnings"] = load_warnings
    merged.attrs["loaded_files"] = loaded_files
    merged.attrs["cycle_dir"] = str(cycle_dir)
    return merged


def nhanes_sex(row: pd.Series) -> str:
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


def list_available_files(data_dir: Path | None = None, cycle: str | None = None) -> list[str]:
    data_dir = data_dir or DATA_DIR
    if cycle:
        search = cycle_data_dir(data_dir, cycle)
    else:
        search = data_dir
    names: list[str] = []
    if search.is_dir():
        names.extend(p.name for p in search.glob("*.XPT"))
        names.extend(p.name for p in search.glob("*.xpt"))
    return sorted(names)


def biomarker_available(df: pd.DataFrame, code: str) -> bool:
    """True if the biomarker column exists and has at least one non-null value."""
    key = code.upper()
    col: pd.Series | None = None
    if key in df.columns:
        col = df[key]
    else:
        for nhanes_col, harness_code in NHANES_COLUMN_MAP.items():
            if harness_code == key and nhanes_col in df.columns:
                col = df[nhanes_col]
                break
    if col is None:
        return False
    return bool(pd.to_numeric(col, errors="coerce").notna().any())


def biomarker_unavailable_reason(code: str, cycle: str) -> str | None:
    """Human-readable reason when a biomarker cannot be audited on this cycle layout."""
    key = code.upper()
    if cycle == "2015-2016" and key in CYCLE_I_UNAVAILABLE_BIOMARKERS:
        if key in ("HSCRP", "CRP"):
            return "hs-CRP data unavailable in current dataset (no CRP_I.XPT on server)"
        if key == "CALCIUM":
            return "Calcium data unavailable in current dataset (no BIOPRO_I.XPT on server)"
        if key == "FERRITIN":
            return "Ferritin data unavailable in current dataset (no BIOPRO_I.XPT on server)"
        if key == "ESR":
            return "ESR data unavailable in current dataset"
        if key == "LDL":
            return "LDL data unavailable in current dataset (direct LDL not in cycle-I file set)"
    return None


def pattern_available(df: pd.DataFrame, slug: str, cycle: str) -> tuple[bool, str | None]:
    """Check whether a pattern can be evaluated on the loaded cohort."""
    slug = slug.lower()
    if slug == "inflammation":
        if any(biomarker_available(df, m) for m in ("HSCRP", "ESR", "FERRITIN")):
            return True, None
        return False, (
            "Cannot evaluate inflammation pattern: hs-CRP, ESR, and ferritin "
            "data unavailable in current dataset"
        )
    if slug == "insulin_resistance":
        if biomarker_available(df, "GLU") and biomarker_available(df, "INSULIN"):
            return True, None
        return False, "Cannot evaluate insulin_resistance: GLU and/or INSULIN unavailable"
    if slug == "metabolic_syndrome":
        needed = ("GLU", "TG", "HDL")
        missing = [m for m in needed if not biomarker_available(df, m)]
        if missing:
            return False, f"Cannot evaluate metabolic_syndrome: missing {', '.join(missing)}"
        return True, None
    return True, None


def biomarker_series(df: pd.DataFrame, code: str) -> pd.Series:
    key = code.upper()
    if key in df.columns:
        return pd.to_numeric(df[key], errors="coerce")
    for nhanes_col, harness_code in NHANES_COLUMN_MAP.items():
        if harness_code == key and nhanes_col in df.columns:
            return pd.to_numeric(df[nhanes_col], errors="coerce")
    raise KeyError(
        f"Biomarker {code} not found in DataFrame columns. "
        f"Available harness columns: {[c for c in df.columns if c.isupper()][:20]}"
    )
