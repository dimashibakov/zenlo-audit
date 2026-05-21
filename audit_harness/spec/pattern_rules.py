"""Independent clinical pattern definitions for the audit harness.

Pattern logic is re-implemented from published clinical criteria and the Zenlo
Labs *clinical specification* (trigger semantics), NOT from production TypeScript.
Each rule cites its clinical source in docstrings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Sex = Literal["male", "female", "unknown"]


@dataclass
class PatternResult:
    slug: str
    detected: bool
    triggers: list[str]
    computed_metrics: dict[str, float | str | int]


def compute_homa_ir(glucose_mg_dl: float, insulin_uiu_ml: float) -> float:
    """HOMA-IR = (fasting glucose mg/dL × fasting insulin μU/mL) / 405.

    Source: Matthews DR et al., Diabetologia 1985 (HOMA model).
    """
    return (glucose_mg_dl * insulin_uiu_ml) / 405.0


def detect_inflammation(
    *,
    hscrp: float | None,
    esr: float | None,
    ferritin: float | None,
    sex: Sex = "unknown",
) -> PatternResult:
    """Systemic inflammation — ANY elevated marker fires (clinical screening logic).

    Criteria (independent clinical re-implementation):
    - hs-CRP > 3.0 mg/L (elevated cardiovascular/inflammatory risk band)
    - ESR > 20 mm/hr (above standard lab upper reference)
    - Ferritin above sex-specific upper limit (>400 M, >150 F)

    Sources: Ridker hs-CRP; standard ESR reference; ferritin as acute-phase reactant.
    """
    triggers: list[str] = []
    if hscrp is not None and hscrp > 3.0:
        triggers.append("hscrp_elevated")
    if esr is not None and esr > 20.0:
        triggers.append("esr_elevated")
    if ferritin is not None:
        ferritin_high = ferritin > 400.0 if sex == "male" else ferritin > 150.0
        if sex == "unknown" and ferritin > 150.0:
            ferritin_high = True
        if ferritin_high:
            triggers.append("ferritin_elevated")

    return PatternResult(
        slug="inflammation",
        detected=len(triggers) > 0,
        triggers=triggers,
        computed_metrics={
            "hscrp_value": hscrp if hscrp is not None else "unavailable",
            "esr_value": esr if esr is not None else "unavailable",
            "ferritin_value": ferritin if ferritin is not None else "unavailable",
            "triggers_fired_count": len(triggers),
        },
    )


def detect_insulin_resistance(
    *,
    glucose: float | None,
    insulin: float | None,
    triglycerides: float | None,
    hdl: float | None,
    sex: Sex = "unknown",
) -> PatternResult:
    """Insulin resistance — ANY of three independent triggers fires.

    Clinical re-implementation:
    1. HOMA-IR > 2.6 (insulin resistance threshold; Matthews HOMA + ATP III literature)
    2. Fasting insulin >25 μU/mL AND fasting glucose >100 mg/dL
    3. TG/HDL ratio >3.0 (M) or >2.5 (F) — lipoprotein insulin-resistance surrogate

    Sources: Matthews HOMA 1985; fasting hyperinsulinemia + dysglycemia criteria;
    TG/HDL ratio literature (McLaughlin et al.).
    """
    triggers: list[str] = []
    homa_value: float | str = "unavailable"

    if glucose is not None and insulin is not None:
        homa_value = round(compute_homa_ir(glucose, insulin), 3)
        if homa_value > 2.6:
            triggers.append("homa_ir_elevated")

    if (
        insulin is not None
        and insulin > 25.0
        and glucose is not None
        and glucose > 100.0
    ):
        triggers.append("insulin_glucose_combined")

    if triglycerides is not None and hdl is not None and hdl > 0:
        ratio = triglycerides / hdl
        threshold = 3.0 if sex == "male" else 2.5
        if sex == "unknown":
            threshold = 2.5
        if ratio > threshold:
            triggers.append("tg_hdl_ratio_elevated")

    return PatternResult(
        slug="insulin_resistance",
        detected=len(triggers) > 0,
        triggers=triggers,
        computed_metrics={
            "homa_ir_value": homa_value,
            "glucose_value": glucose if glucose is not None else "unavailable",
            "insulin_value": insulin if insulin is not None else "unavailable",
            "triggers_fired_count": len(triggers),
        },
    )


def detect_metabolic_syndrome(
    *,
    glucose: float | None,
    insulin: float | None,
    triglycerides: float | None,
    hdl: float | None,
    hba1c: float | None,
    sex: Sex = "unknown",
) -> PatternResult:
    """Metabolic syndrome — ≥3 of 4 ATP III–style lab criteria (NHANES surrogate).

    Criteria (NCEP ATP III adapted for available labs):
    1. HOMA-IR > 2.6 (insulin-resistance surrogate for hyperinsulinemia criterion)
    2. Triglycerides ≥150 mg/dL
    3. HDL low: <40 mg/dL (M) or <50 mg/dL (F)
    4. Dysglycemia: fasting glucose ≥100 mg/dL OR HbA1c ≥5.7%

    Source: NCEP ATP III (2005); ADA dysglycemia thresholds.
    """
    criteria: list[str] = []

    if glucose is not None and insulin is not None:
        if compute_homa_ir(glucose, insulin) > 2.6:
            criteria.append("homa_ir")

    if triglycerides is not None and triglycerides >= 150.0:
        criteria.append("triglycerides")

    if hdl is not None:
        hdl_low = hdl < 40.0 if sex == "male" else hdl < 50.0
        if sex == "unknown" and hdl < 50.0:
            hdl_low = True
        if hdl_low:
            criteria.append("hdl_low")

    dysglycemia = False
    if glucose is not None and glucose >= 100.0:
        dysglycemia = True
    if hba1c is not None and hba1c >= 5.7:
        dysglycemia = True
    if dysglycemia:
        criteria.append("dysglycemia")

    detected = len(criteria) >= 3
    return PatternResult(
        slug="metabolic_syndrome",
        detected=detected,
        triggers=criteria,
        computed_metrics={
            "criteria_met_count": len(criteria),
            "criteria_fired": "+".join(criteria) if criteria else "none",
        },
    )


PATTERN_DETECTORS = {
    "inflammation": detect_inflammation,
    "insulin_resistance": detect_insulin_resistance,
    "metabolic_syndrome": detect_metabolic_syndrome,
}
