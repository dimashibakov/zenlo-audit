"""Fairness / subgroup analysis by age, sex, and race-ethnicity."""

from __future__ import annotations

from typing import Any

import pandas as pd

from audit_harness.classifiers.biomarker import classify_biomarker
from audit_harness.loaders.nhanes import biomarker_series, nhanes_sex


def _age_band(age: float) -> str:
    if pd.isna(age):
        return "unknown"
    age = int(age)
    if age < 18:
        return "under_18"
    if age < 40:
        return "18_39"
    if age < 60:
        return "40_59"
    return "60_plus"


RIDRETH3_LABELS: dict[int, str] = {
    1: "mexican_american",
    2: "other_hispanic",
    3: "non_hispanic_white",
    4: "non_hispanic_black",
    6: "non_hispanic_asian",
    7: "other_race_including_multiracial",
}


def fairness_for_biomarker(df: pd.DataFrame, code: str) -> dict[str, Any]:
    """Subgroup prevalence of high/low classifications."""
    series = biomarker_series(df, code)
    rows: list[dict[str, Any]] = []

    work = df.copy()
    work["_classification"] = [
        classify_biomarker(
            code,
            float(series.loc[i]) if pd.notna(series.loc[i]) else None,
            sex=nhanes_sex(work.loc[i]),
        )
        for i in work.index
    ]
    work["_sex"] = work.apply(nhanes_sex, axis=1)
    work["_age_band"] = work["RIDAGEYR"].apply(_age_band) if "RIDAGEYR" in work.columns else "unknown"
    if "RIDRETH3" in work.columns:
        work["_race"] = work["RIDRETH3"].map(lambda x: RIDRETH3_LABELS.get(int(x), "unknown") if pd.notna(x) else "unknown")
    else:
        work["_race"] = "unknown"

    for dimension, col in (("sex", "_sex"), ("age_band", "_age_band"), ("race_ethnicity", "_race")):
        for subgroup, grp in work.groupby(col):
            n = len(grp)
            if n == 0:
                continue
            rows.append(
                {
                    "dimension": dimension,
                    "subgroup": str(subgroup),
                    "n": n,
                    "pct_high": float((grp["_classification"] == "high").mean()),
                    "pct_low": float((grp["_classification"] == "low").mean()),
                    "pct_normal": float((grp["_classification"] == "normal").mean()),
                }
            )

    return {"biomarker": code.upper(), "subgroups": rows}


def fairness_for_pattern(df: pd.DataFrame, slug: str, detected_col: str) -> dict[str, Any]:
    """Subgroup pattern detection prevalence."""
    work = df.copy()
    work["_detected"] = df[detected_col].astype(bool)
    work["_sex"] = work.apply(nhanes_sex, axis=1)
    work["_age_band"] = work["RIDAGEYR"].apply(_age_band) if "RIDAGEYR" in work.columns else "unknown"
    if "RIDRETH3" in work.columns:
        work["_race"] = work["RIDRETH3"].map(lambda x: RIDRETH3_LABELS.get(int(x), "unknown") if pd.notna(x) else "unknown")
    else:
        work["_race"] = "unknown"

    rows: list[dict[str, Any]] = []
    for dimension, col in (("sex", "_sex"), ("age_band", "_age_band"), ("race_ethnicity", "_race")):
        for subgroup, grp in work.groupby(col):
            n = len(grp)
            rows.append(
                {
                    "dimension": dimension,
                    "subgroup": str(subgroup),
                    "n": n,
                    "prevalence_detected": float(grp["_detected"].mean()) if n else 0.0,
                }
            )
    return {"pattern": slug, "subgroups": rows}
