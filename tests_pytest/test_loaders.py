"""Unit tests for NHANES loader helpers (synthetic DataFrames — no XPT required)."""

import pandas as pd
import pytest

from audit_harness.loaders.nhanes import (
    NHANES_COLUMN_MAP,
    filter_cohort,
    nhanes_sex,
)


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
        }
    )


class TestNhanesLoaderHelpers:
    def test_column_map_has_hscrp(self):
        assert NHANES_COLUMN_MAP["LBXCRP"] == "HSCRP"

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
