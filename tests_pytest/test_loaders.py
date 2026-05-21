"""Unit tests for NHANES loader helpers (synthetic DataFrames — no XPT required)."""

import pandas as pd
import pytest

from audit_harness.loaders.nhanes import (
    NHANES_COLUMN_MAP,
    biomarker_available,
    biomarker_unavailable_reason,
    cycle_data_dir,
    filter_cohort,
    normalize_insulin_columns,
    nhanes_sex,
    pattern_available,
)
from config import DATA_DIR


@pytest.fixture
def sample_demo_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SEQN": [1, 2, 3, 4],
            "RIDAGEYR": [15, 25, 45, 65],
            "RIAGENDR": [1, 2, 1, 2],
            "RIDRETH3": [3, 3, 4, 1],
            "HSCRP": [0.5, 2.0, 5.0, 1.2],
            "GLU": [90, 105, 88, 110],
            "INSULIN": [8.0, 12.0, 15.0, 20.0],
            "TG": [100, 160, 90, 140],
            "HDL": [55, 45, 60, 48],
        }
    )


class TestNhanesLoaderHelpers:
    def test_column_map_has_hscrp(self):
        assert NHANES_COLUMN_MAP["LBXCRP"] == "HSCRP"
        assert NHANES_COLUMN_MAP["LBXTC"] == "TOTAL_CHOL"
        assert NHANES_COLUMN_MAP["LBXGH"] == "HBA1C"

    def test_cycle_data_dir_subfolder(self):
        path = cycle_data_dir(DATA_DIR, "2015-2016")
        assert path.name == "2015-2016"
        assert path.parent == DATA_DIR

    def test_normalize_insulin_lbxin(self):
        df = pd.DataFrame({"SEQN": [1], "LBXIN": [10.0]})
        out = normalize_insulin_columns(df)
        assert out["INSULIN"].iloc[0] == 10.0

    def test_normalize_insulin_lbdinsi_conversion(self):
        df = pd.DataFrame({"SEQN": [1], "LBDINSI": [69.45]})
        out = normalize_insulin_columns(df)
        assert abs(out["INSULIN"].iloc[0] - 10.0) < 0.01

    def test_biomarker_available(self, sample_demo_df):
        assert biomarker_available(sample_demo_df, "GLU") is True
        assert biomarker_available(sample_demo_df, "CALCIUM") is False

    def test_biomarker_unavailable_reason_cycle_i(self):
        assert "hs-CRP" in biomarker_unavailable_reason("HSCRP", "2015-2016")

    def test_pattern_available_inflammation_missing(self):
        df = pd.DataFrame({"GLU": [90], "INSULIN": [10]})
        ok, msg = pattern_available(df, "inflammation", "2015-2016")
        assert ok is False
        assert "hs-CRP" in (msg or "")

    def test_pattern_available_metabolic_syndrome_ok(self, sample_demo_df):
        ok, msg = pattern_available(sample_demo_df, "metabolic_syndrome", "2015-2016")
        assert ok is True
        assert msg is None

    def test_nhanes_sex_mapping(self):
        assert nhanes_sex(pd.Series({"RIAGENDR": 1})) == "male"
        assert nhanes_sex(pd.Series({"RIAGENDR": 2})) == "female"

    def test_filter_cohort_age(self, sample_demo_df):
        out = filter_cohort(sample_demo_df, min_age=18)
        assert len(out) == 3

    def test_filter_cohort_sex_female(self, sample_demo_df):
        out = filter_cohort(sample_demo_df, sex="female")
        assert len(out) == 2
        assert (out["RIAGENDR"] == 2).all()

    def test_filter_cohort_race(self, sample_demo_df):
        out = filter_cohort(sample_demo_df, race_ethnicity=3)
        assert len(out) == 2
