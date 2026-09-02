"""
ghg_pipeline.py
================
A GHG Protocol Scope 1-3 emissions calculation pipeline built in pandas.

This is a Python/pandas re-implementation of the calculation engine behind
my Excel-based "Corporate GHG Emissions Inventory Model" project
(github.com/rachnasingh1012/Corporate-GHG-Inventory-model). The Excel model
proves the accounting method with live formulas; this script proves the same
method as reusable, testable code that can be re-run against a new activity
data file in seconds.

Method
------
For every emission source:  emissions (tCO2e) = activity_data x emission_factor / 1000
(emission factors are supplied in kg CO2e per unit of activity; dividing by
1,000 converts kg to tonnes.) This is the standard GHG Protocol Corporate
Accounting and Reporting Standard approach, using activity-data-based factors
for Scope 1/2 and a spend-based (EEIO) approach for Scope 3 categories 1-2.

Usage
-----
    python ghg_pipeline.py
    python ghg_pipeline.py --input data/activity_data.csv --outdir outputs

Outputs (written to --outdir):
    emissions_detail.csv    - every source, with calculated emissions
    emissions_by_scope.csv  - Scope 1/2/3 subtotals and % of total
    emissions_by_category.csv - GHG Protocol category subtotals
    scope_breakdown.png     - donut chart, emissions by scope
    category_breakdown.png  - bar chart, Scope 3 by category
"""

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

KGCO2E_PER_TCO2E = 1000


def load_activity_data(path: Path) -> pd.DataFrame:
    """Load raw activity data and emission factors from CSV."""
    df = pd.read_csv(path)
    required = {"ref", "scope", "category", "emission_source", "activity_data",
                "unit", "emission_factor", "ef_unit", "factor_source"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input file is missing required columns: {missing}")
    return df


def calculate_emissions(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the GHG Protocol calculation: activity x factor / 1000 -> tCO2e."""
    df = df.copy()
    df["emissions_tco2e"] = (df["activity_data"] * df["emission_factor"]) / KGCO2E_PER_TCO2E
    df["emissions_tco2e"] = df["emissions_tco2e"].round(3)
    return df


def summarise_by_scope(df: pd.DataFrame) -> pd.DataFrame:
    summary = df.groupby("scope", as_index=False)["emissions_tco2e"].sum()
    summary["emissions_tco2e"] = summary["emissions_tco2e"].round(3)
    total = summary["emissions_tco2e"].sum()
    summary["pct_of_total"] = (summary["emissions_tco2e"] / total * 100).round(1)
    summary = summary.sort_values("scope").reset_index(drop=True)
    return summary


def summarise_by_category(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["scope", "category"], as_index=False)["emissions_tco2e"]
        .sum()
        .sort_values(["scope", "emissions_tco2e"], ascending=[True, False])
        .reset_index(drop=True)
    )
    summary["emissions_tco2e"] = summary["emissions_tco2e"].round(3)
    return summary


def add_intensity(scope_summary: pd.DataFrame, fte_count: int) -> dict:
    total = scope_summary["emissions_tco2e"].sum()
    return {
        "total_tco2e": round(total, 1),
        "fte_count": fte_count,
        "intensity_tco2e_per_fte": round(total / fte_count, 2),
    }


def plot_scope_breakdown(scope_summary: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 5))
    colors = ["#2E7D32", "#66BB6A", "#A5D6A7"]
    ax.pie(
        scope_summary["emissions_tco2e"],
        labels=[f'{s}\n{v:,.0f} tCO2e' for s, v in
                zip(scope_summary["scope"], scope_summary["emissions_tco2e"])],
        autopct="%1.1f%%",
        colors=colors,
        wedgeprops=dict(width=0.45, edgecolor="white"),
        pctdistance=0.78,
    )
    ax.set_title("Gross Emissions by Scope (tCO2e)")
    fig.tight_layout()
    fig.savefig(outdir / "scope_breakdown.png", dpi=150)
    plt.close(fig)


def plot_category_breakdown(category_summary: pd.DataFrame, outdir: Path) -> None:
    scope3 = category_summary[category_summary["scope"] == "Scope 3"].sort_values(
        "emissions_tco2e"
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(scope3["category"], scope3["emissions_tco2e"], color="#2E7D32")
    ax.set_xlabel("tCO2e")
    ax.set_title("Scope 3 Emissions by GHG Protocol Category")
    fig.tight_layout()
    fig.savefig(outdir / "category_breakdown.png", dpi=150)
    plt.close(fig)


def run_pipeline(input_path: Path, outdir: Path, fte_count: int = 200) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)

    raw = load_activity_data(input_path)
    detail = calculate_emissions(raw)
    by_scope = summarise_by_scope(detail)
    by_category = summarise_by_category(detail)
    headline = add_intensity(by_scope, fte_count)

    detail.to_csv(outdir / "emissions_detail.csv", index=False)
    by_scope.to_csv(outdir / "emissions_by_scope.csv", index=False)
    by_category.to_csv(outdir / "emissions_by_category.csv", index=False)

    plot_scope_breakdown(by_scope, outdir)
    plot_category_breakdown(by_category, outdir)

    return {
        "detail": detail,
        "by_scope": by_scope,
        "by_category": by_category,
        "headline": headline,
    }


def main():
    parser = argparse.ArgumentParser(description="GHG Protocol Scope 1-3 emissions pipeline")
    parser.add_argument("--input", default="data/activity_data.csv", type=Path)
    parser.add_argument("--outdir", default="outputs", type=Path)
    parser.add_argument("--fte", default=200, type=int, help="Headcount for intensity metric")
    args = parser.parse_args()

    results = run_pipeline(args.input, args.outdir, args.fte)

    print("\n=== GHG Emissions Summary ===")
    print(results["by_scope"].to_string(index=False))
    print(f"\nTotal gross emissions : {results['headline']['total_tco2e']:,.1f} tCO2e")
    print(f"Intensity             : {results['headline']['intensity_tco2e_per_fte']} tCO2e / FTE")
    print(f"\nDetailed outputs written to: {args.outdir}/")


if __name__ == "__main__":
    main()
