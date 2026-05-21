"""Cited biomarker reference ranges for independent classification.

Each entry documents the clinical/laboratory source used by this harness.
Values are NOT copied from the Zenlo Labs TypeScript implementation — they are
seeded from published lab reference conventions and NHANES documentation, then
maintained here as the harness specification of record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Sex = Literal["male", "female", "unknown"]


@dataclass(frozen=True)
class ReferenceRange:
    """Inclusive laboratory reference interval for classification."""

    min_value: float
    max_value: float
    unit: str
    citation: str
    # When True, values below min are "low" and above max are "high".
    # Some markers (e.g. HDL) use low_is_abnormal only via classify logic.
    low_is_abnormal: bool = True
    high_is_abnormal: bool = True


# --- Inflammation / CVD / metabolic (NHANES-compatible) ---

# Source: NHANES laboratory methods — hs-CRP reported as mg/L; clinical
# high-sensitivity CRP risk stratification commonly uses >3 mg/L as elevated
# (Ridker PMID 11434520; AHA/CDC hs-CRP statement).
HSCRP = ReferenceRange(
    min_value=0.0,
    max_value=3.0,
    unit="mg/L",
    citation="NHANES LBXCRP (mg/L); elevated threshold >3 mg/L per hs-CRP CVD risk literature",
)

# Source: Standard clinical lab reference 0–20 mm/hr (M/F) — Westergren ESR.
ESR = ReferenceRange(
    min_value=0.0,
    max_value=20.0,
    unit="mm/hr",
    citation="Standard clinical ESR reference 0–20 mm/hr (Westergren)",
)

# Source: Ferritin — sex-specific upper reference for elevated acute-phase/stores.
# Male >400 ng/mL, female >150 ng/mL (Mayo Clinic / common lab references).
FERRITIN_MALE = ReferenceRange(
    min_value=12.0,
    max_value=400.0,
    unit="ng/mL",
    citation="Ferritin male reference; elevated if >400 ng/mL (Mayo/lab conventions)",
)
FERRITIN_FEMALE = ReferenceRange(
    min_value=12.0,
    max_value=150.0,
    unit="ng/mL",
    citation="Ferritin female reference; elevated if >150 ng/mL (Mayo/lab conventions)",
)

# Source: NHANES LBXGLU — fasting glucose mg/dL; ADA prediabetes threshold ≥100.
GLU = ReferenceRange(
    min_value=70.0,
    max_value=100.0,
    unit="mg/dL",
    citation="NHANES fasting glucose (LBXGLU); ADA fasting glucose reference 70–100 mg/dL",
)

# Source: NHANES LBXIN — fasting insulin uIU/mL; common lab ref ~2.6–24.9.
INSULIN = ReferenceRange(
    min_value=2.6,
    max_value=24.9,
    unit="uIU/mL",
    citation="NHANES fasting insulin (LBXIN); standard lab reference interval",
)

# Source: ATP III / NHANES — triglycerides ≥150 mg/dL elevated.
TG = ReferenceRange(
    min_value=0.0,
    max_value=150.0,
    unit="mg/dL",
    citation="ATP III metabolic syndrome criterion: TG ≥150 mg/dL",
)

# Source: ATP III — HDL <40 mg/dL (M) or <50 mg/dL (F) is low.
HDL_MALE = ReferenceRange(
    min_value=40.0,
    max_value=999.0,
    unit="mg/dL",
    citation="ATP III: HDL low if <40 mg/dL (male)",
    high_is_abnormal=False,
)
HDL_FEMALE = ReferenceRange(
    min_value=50.0,
    max_value=999.0,
    unit="mg/dL",
    citation="ATP III: HDL low if <50 mg/dL (female)",
    high_is_abnormal=False,
)

# Source: ADA — HbA1c ≥5.7% prediabetes threshold.
HBA1C = ReferenceRange(
    min_value=4.0,
    max_value=5.6,
    unit="%",
    citation="ADA HbA1c reference; dysglycemia if ≥5.7%",
)

# Source: NHANES/standard chemistry — total calcium 8.5–10.5 mg/dL.
CALCIUM = ReferenceRange(
    min_value=8.5,
    max_value=10.5,
    unit="mg/dL",
    citation="Standard serum calcium reference 8.5–10.5 mg/dL (clinical chemistry)",
)

# Source: Intact PTH reference 15–65 pg/mL (common lab interval).
PTH = ReferenceRange(
    min_value=15.0,
    max_value=65.0,
    unit="pg/mL",
    citation="Intact PTH reference 15–65 pg/mL (endocrine lab conventions)",
)

# Source: LDL — clinical treatment targets; elevated if >130 mg/dL (ATP III risk).
LDL = ReferenceRange(
    min_value=0.0,
    max_value=130.0,
    unit="mg/dL",
    citation="LDL elevated if >130 mg/dL (ATP III / common clinical cutoff)",
)

BIOMARKER_RANGES: dict[str, ReferenceRange | tuple[ReferenceRange, ReferenceRange]] = {
    "HSCRP": HSCRP,
    "CRP": HSCRP,
    "ESR": ESR,
    "FERRITIN": (FERRITIN_MALE, FERRITIN_FEMALE),
    "GLU": GLU,
    "GLUCOSE": GLU,
    "INSULIN": INSULIN,
    "TG": TG,
    "TRIGLYCERIDES": TG,
    "HDL": (HDL_MALE, HDL_FEMALE),
    "HBA1C": HBA1C,
    "CALCIUM": CALCIUM,
    "PTH": PTH,
    "LDL": LDL,
}


def get_reference_range(code: str, sex: Sex = "unknown") -> ReferenceRange | None:
    """Resolve a biomarker code to the sex-appropriate reference range."""
    key = code.upper()
    spec = BIOMARKER_RANGES.get(key)
    if spec is None:
        return None
    if isinstance(spec, tuple):
        if sex == "male":
            return spec[0]
        if sex == "female":
            return spec[1]
        # Conservative default for unknown sex: use stricter female ferritin / male HDL thresholds
        return spec[1] if key == "FERRITIN" else spec[0]
    return spec
