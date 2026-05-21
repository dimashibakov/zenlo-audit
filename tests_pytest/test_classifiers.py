"""Unit tests for biomarker and pattern classifiers (synthetic — no XPT required)."""

import pandas as pd
import pytest

from audit_harness.classifiers.biomarker import classify_biomarker
from audit_harness.classifiers.pattern import detect_pattern_on_row
from audit_harness.spec.pattern_rules import (
    detect_inflammation,
    detect_insulin_resistance,
    detect_metabolic_syndrome,
)


class TestBiomarkerClassifier:
    def test_hscrp_high(self):
        assert classify_biomarker("HSCRP", 5.0) == "high"

    def test_hscrp_normal(self):
        assert classify_biomarker("HSCRP", 1.5) == "normal"

    def test_calcium_normal(self):
        assert classify_biomarker("CALCIUM", 9.5) == "normal"

    def test_calcium_high(self):
        assert classify_biomarker("CALCIUM", 11.0) == "high"

    def test_calcium_low(self):
        assert classify_biomarker("CALCIUM", 8.0) == "low"

    def test_hdl_low_male(self):
        assert classify_biomarker("HDL", 35.0, sex="male") == "low"

    def test_hdl_normal_female(self):
        assert classify_biomarker("HDL", 55.0, sex="female") == "normal"

    def test_unknown_biomarker(self):
        assert classify_biomarker("NOTREAL", 10.0) == "unknown"

    def test_none_value(self):
        assert classify_biomarker("HSCRP", None) == "unknown"


class TestPatternRules:
    def test_inflammation_hscrp_only(self):
        r = detect_inflammation(hscrp=4.0, esr=None, ferritin=None)
        assert r.detected is True
        assert "hscrp_elevated" in r.triggers

    def test_inflammation_not_detected(self):
        r = detect_inflammation(hscrp=1.0, esr=10.0, ferritin=80.0, sex="female")
        assert r.detected is False

    def test_insulin_resistance_homa(self):
        # glucose 110, insulin 20 -> HOMA ~5.4
        r = detect_insulin_resistance(glucose=110.0, insulin=20.0, triglycerides=None, hdl=None)
        assert r.detected is True
        assert "homa_ir_elevated" in r.triggers

    def test_metabolic_syndrome_three_criteria(self):
        r = detect_metabolic_syndrome(
            glucose=110.0,
            insulin=20.0,
            triglycerides=180.0,
            hdl=35.0,
            hba1c=None,
            sex="male",
        )
        assert r.detected is True
        assert r.computed_metrics["criteria_met_count"] >= 3


class TestPatternOnRow:
    def test_inflammation_row(self):
        row = pd.Series({"HSCRP": 4.5, "RIAGENDR": 1})
        r = detect_pattern_on_row(row, "inflammation")
        assert r.detected is True
