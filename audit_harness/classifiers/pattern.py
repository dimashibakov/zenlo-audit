"""Pattern detection — dispatches to independent spec/pattern_rules implementations."""

from __future__ import annotations

import pandas as pd

from audit_harness.loaders.nhanes import nhanes_sex
from audit_harness.spec.pattern_rules import PATTERN_DETECTORS, PatternResult


def _row_value(row: pd.Series, code: str) -> float | None:
    key = code.upper()
    if key not in row.index:
        return None
    val = row[key]
    if pd.isna(val):
        return None
    return float(val)


def detect_pattern_on_row(row: pd.Series, slug: str) -> PatternResult:
    """Run a pattern detector on one NHANES/respondent row."""
    slug = slug.lower()
    if slug not in PATTERN_DETECTORS:
        raise ValueError(f"Unknown pattern {slug!r}. Known: {list(PATTERN_DETECTORS)}")

    sex = nhanes_sex(row)

    if slug == "inflammation":
        return PATTERN_DETECTORS[slug](
            hscrp=_row_value(row, "HSCRP"),
            esr=_row_value(row, "ESR"),
            ferritin=_row_value(row, "FERRITIN"),
            sex=sex,
        )
    if slug == "insulin_resistance":
        return PATTERN_DETECTORS[slug](
            glucose=_row_value(row, "GLU"),
            insulin=_row_value(row, "INSULIN"),
            triglycerides=_row_value(row, "TG"),
            hdl=_row_value(row, "HDL"),
            sex=sex,
        )
    if slug == "metabolic_syndrome":
        return PATTERN_DETECTORS[slug](
            glucose=_row_value(row, "GLU"),
            insulin=_row_value(row, "INSULIN"),
            triglycerides=_row_value(row, "TG"),
            hdl=_row_value(row, "HDL"),
            hba1c=_row_value(row, "HBA1C"),
            sex=sex,
        )
    raise ValueError(f"Pattern {slug} not wired in row dispatcher")


def detect_pattern_cohort(df: pd.DataFrame, slug: str) -> pd.DataFrame:
    """Apply pattern detection to every row; returns summary columns."""
    results = [detect_pattern_on_row(row, slug) for _, row in df.iterrows()]
    out = df.copy()
    out[f"pattern_{slug}_detected"] = [r.detected for r in results]
    out[f"pattern_{slug}_triggers"] = ["+".join(r.triggers) if r.triggers else "" for r in results]
    return out
