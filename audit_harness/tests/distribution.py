"""Distribution statistics for biomarkers and patterns."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from audit_harness.classifiers.biomarker import classify_biomarker
from audit_harness.loaders.nhanes import biomarker_series, nhanes_sex


def distribution_for_biomarker(df: pd.DataFrame, code: str) -> dict[str, Any]:
    """Compute distribution + classification prevalence for one biomarker."""
    series = biomarker_series(df, code)
    valid = series.dropna()
    classifications = []
    for idx, val in series.items():
        sex = nhanes_sex(df.loc[idx]) if idx in df.index else "unknown"
        classifications.append(classify_biomarker(code, float(val) if pd.notna(val) else None, sex=sex))

    cls_series = pd.Series(classifications, index=series.index)
    n = int(valid.shape[0])
    prevalence = {
        k: float((cls_series == k).sum() / len(cls_series)) if len(cls_series) else 0.0
        for k in ("low", "normal", "high", "unknown")
    }

    return {
        "biomarker": code.upper(),
        "n_valid": n,
        "n_total": int(len(series)),
        "mean": float(valid.mean()) if n else None,
        "median": float(valid.median()) if n else None,
        "std": float(valid.std()) if n > 1 else None,
        "p25": float(valid.quantile(0.25)) if n else None,
        "p75": float(valid.quantile(0.75)) if n else None,
        "p95": float(valid.quantile(0.95)) if n else None,
        "min": float(valid.min()) if n else None,
        "max": float(valid.max()) if n else None,
        "prevalence": prevalence,
    }


def distribution_for_pattern(df: pd.DataFrame, slug: str, detected_col: str) -> dict[str, Any]:
    """Prevalence of pattern detection in cohort."""
    detected = df[detected_col].astype(bool)
    n = int(detected.shape[0])
    prev = float(detected.sum() / n) if n else 0.0
    return {
        "pattern": slug,
        "n_total": n,
        "n_detected": int(detected.sum()),
        "prevalence_detected": prev,
    }
