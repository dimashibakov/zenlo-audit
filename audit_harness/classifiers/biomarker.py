"""Biomarker classification against cited reference ranges."""

from __future__ import annotations

from typing import Literal

from audit_harness.spec.biomarker_ranges import ReferenceRange, Sex, get_reference_range

Classification = Literal["low", "normal", "high", "unknown"]


def classify_biomarker(
    code: str,
    value: float | None,
    *,
    sex: Sex = "unknown",
    age: float | None = None,
) -> Classification:
    """Classify a single biomarker value vs the harness reference spec.

    Age is accepted for future age-stratified ranges; not used in v1 ranges.
    """
    _ = age  # reserved for future pediatric/geriatric specs
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return "unknown"

    ref = get_reference_range(code, sex)
    if ref is None:
        return "unknown"

    return _classify_against_ref(value, ref)


def _classify_against_ref(value: float, ref: ReferenceRange) -> Classification:
    if ref.low_is_abnormal and value < ref.min_value:
        return "low"
    if ref.high_is_abnormal and value > ref.max_value:
        return "high"
    # HDL-style: only low is abnormal; high values are normal/protective.
    if not ref.high_is_abnormal and value >= ref.min_value:
        return "normal"
    if ref.min_value <= value <= ref.max_value:
        return "normal"
    return "normal"
