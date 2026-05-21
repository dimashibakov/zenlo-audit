"""Agreement analysis — harness vs reference labels / spec sanity."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from audit_harness.classifiers.biomarker import classify_biomarker
from audit_harness.loaders.nhanes import biomarker_series, nhanes_sex
from audit_harness.spec.biomarker_ranges import get_reference_range


def cohens_kappa(y1: pd.Series, y2: pd.Series) -> float | None:
    """Cohen's kappa for two categorical series (excluding unknown)."""
    mask = (y1 != "unknown") & (y2 != "unknown")
    a = y1[mask]
    b = y2[mask]
    if len(a) == 0:
        return None
    labels = sorted(set(a) | set(b))
    n = len(a)
    conf = pd.crosstab(a, b, dropna=False)
    po = conf.values.diagonal().sum() / n
    pe = sum((conf.sum(axis=1)[lbl] / n) * (conf.sum(axis=0)[lbl] / n) for lbl in conf.index if lbl in conf.columns)
    if pe == 1.0:
        return 1.0
    return float((po - pe) / (1 - pe))


def _threshold_reference_label(code: str, value: float, sex: str) -> str:
    """Independent re-apply of spec thresholds (sanity reference for agreement)."""
    return classify_biomarker(code, value, sex=sex)


def agreement_for_biomarker(df: pd.DataFrame, code: str) -> dict[str, Any]:
    """Compare harness classification to a duplicated spec pass (sanity / self-consistency).

    Structure supports plugging production-output labels later via `reference_col`.
    """
    series = biomarker_series(df, code)
    harness_labels = []
    reference_labels = []
    for idx, val in series.items():
        if pd.isna(val):
            harness_labels.append("unknown")
            reference_labels.append("unknown")
            continue
        sex = nhanes_sex(df.loc[idx])
        v = float(val)
        h = classify_biomarker(code, v, sex=sex)
        r = _threshold_reference_label(code, v, sex)
        harness_labels.append(h)
        reference_labels.append(r)

    h_s = pd.Series(harness_labels, index=series.index)
    r_s = pd.Series(reference_labels, index=series.index)
    comparable = (h_s != "unknown") & (r_s != "unknown")
    n_comp = int(comparable.sum())
    pct_agreement = float((h_s[comparable] == r_s[comparable]).mean()) if n_comp else None
    kappa = cohens_kappa(h_s, r_s)

    ref = get_reference_range(code, "unknown")
    citation = "sex-specific spec"
    if ref is not None and not isinstance(ref, tuple):
        citation = ref.citation
    return {
        "biomarker": code.upper(),
        "n_comparable": n_comp,
        "pct_agreement": pct_agreement,
        "cohens_kappa": kappa,
        "spec_citation": citation,
        "note": "Self-consistency vs spec re-pass; production label column can replace reference_labels later.",
    }
