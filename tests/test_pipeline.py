"""
test_pipeline.py
=================
Unit tests for the GHG emissions pipeline.

The reconciliation tests check the pandas pipeline's output against the
independently-built Excel model's published results (see the "Key results"
table in this repo's Corporate-GHG-Inventory-model README), to prove the two
implementations of the same GHG Protocol method agree.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ghg_pipeline import (  # noqa: E402
    load_activity_data,
    calculate_emissions,
    summarise_by_scope,
    summarise_by_category,
    add_intensity,
)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "activity_data.csv"

# Published results from the Excel model (Corporate-GHG-Inventory-model README)
EXPECTED_TOTAL = 1755.0
EXPECTED_SCOPE1 = 189.9
EXPECTED_SCOPE2 = 350.7
EXPECTED_SCOPE3 = 1214.5
EXPECTED_INTENSITY = 8.8


@pytest.fixture(scope="module")
def detail_df():
    raw = load_activity_data(DATA_PATH)
    return calculate_emissions(raw)


def test_load_activity_data_has_expected_rows(detail_df):
    assert len(detail_df) == 17  # 4 Scope 1 + 2 Scope 2 + 11 Scope 3 lines


def test_single_line_calculation(detail_df):
    # 1.1 Natural gas: 480,000 kWh x 0.18254 kgCO2e/kWh / 1000
    row = detail_df.loc[detail_df["ref"] == "1.1"].iloc[0]
    assert row["emissions_tco2e"] == pytest.approx(87.619, abs=0.01)


def test_scope1_reconciles_to_excel_model(detail_df):
    by_scope = summarise_by_scope(detail_df)
    scope1 = by_scope.loc[by_scope["scope"] == "Scope 1", "emissions_tco2e"].iloc[0]
    assert scope1 == pytest.approx(EXPECTED_SCOPE1, abs=0.1)


def test_scope2_reconciles_to_excel_model(detail_df):
    by_scope = summarise_by_scope(detail_df)
    scope2 = by_scope.loc[by_scope["scope"] == "Scope 2", "emissions_tco2e"].iloc[0]
    assert scope2 == pytest.approx(EXPECTED_SCOPE2, abs=0.1)


def test_scope3_reconciles_to_excel_model(detail_df):
    by_scope = summarise_by_scope(detail_df)
    scope3 = by_scope.loc[by_scope["scope"] == "Scope 3", "emissions_tco2e"].iloc[0]
    assert scope3 == pytest.approx(EXPECTED_SCOPE3, abs=0.1)


def test_total_reconciles_to_excel_model(detail_df):
    by_scope = summarise_by_scope(detail_df)
    total = by_scope["emissions_tco2e"].sum()
    assert total == pytest.approx(EXPECTED_TOTAL, abs=0.1)


def test_intensity_reconciles_to_excel_model(detail_df):
    by_scope = summarise_by_scope(detail_df)
    headline = add_intensity(by_scope, fte_count=200)
    assert headline["intensity_tco2e_per_fte"] == pytest.approx(EXPECTED_INTENSITY, abs=0.05)


def test_category_summary_covers_all_scope3_categories(detail_df):
    by_category = summarise_by_category(detail_df)
    scope3_categories = set(by_category.loc[by_category["scope"] == "Scope 3", "category"])
    assert len(scope3_categories) == 8  # GHG Protocol Scope 3 categories 1,2,3,4,5,6,7,8


def test_percentages_sum_to_100(detail_df):
    by_scope = summarise_by_scope(detail_df)
    assert by_scope["pct_of_total"].sum() == pytest.approx(100.0, abs=0.2)
