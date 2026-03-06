#!/usr/bin/env python3
"""
cost_dashboard.py — Cloudflare billing CSV analysis tool.

Produces three summary tables from a billing CSV export:
  1. Daily totals with day-over-day change
  2. Spend by dimensions (Organization Plan, Entity Name, Entity Type,
     CSP, Region, Warehouse ID, Service ID)
  3. Cost-component breakdown

Usage:
    python scripts/cost_dashboard.py --csv <path-to-billing.csv>
    python scripts/cost_dashboard.py --csv data/sample_billing.csv --out-dir out/
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

DATE_COL = "Date"

DIMENSION_COLS = [
    "Organization Plan",
    "Entity Name",
    "Entity Type",
    "CSP",
    "Region",
    "Warehouse ID",
    "Service ID",
]

COST_COLS = [
    "Compute Cost",
    "Storage Cost",
    "Network Cost",
    "Request Cost",
    "Other Cost",
    "Total Cost",
]

TOTAL_COL = "Total Cost"


# ---------------------------------------------------------------------------
# Data loading & cleaning
# ---------------------------------------------------------------------------

def load_csv(csv_path: str | Path) -> pd.DataFrame:
    """Load and clean the billing CSV.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if required columns are missing or the file cannot be parsed.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    try:
        df = pd.read_csv(path, dtype=str)
    except (pd.errors.ParserError, UnicodeDecodeError, PermissionError, OSError) as exc:
        raise ValueError(f"Failed to parse CSV '{path}': {exc}") from exc

    if df.empty:
        raise ValueError(f"CSV file is empty: {path}")

    # Validate required columns
    missing = [c for c in [DATE_COL] + DIMENSION_COLS + COST_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}\n"
            f"Found columns: {list(df.columns)}"
        )

    # Parse Date
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce").dt.date
    bad_dates = df[DATE_COL].isna().sum()
    if bad_dates > 0:
        print(f"Warning: {bad_dates} row(s) had unparseable dates and were dropped.", file=sys.stderr)
        df = df.dropna(subset=[DATE_COL])

    # Coerce money columns: blanks / non-numeric → 0
    for col in COST_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------

def daily_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Table 1: daily total spend with day-over-day change."""
    daily = (
        df.groupby(DATE_COL, as_index=False)[TOTAL_COL]
        .sum()
        .rename(columns={TOTAL_COL: "total_usd"})
        .sort_values(DATE_COL)
    )
    daily["dod_change"] = daily["total_usd"].diff()
    daily["dod_change"] = daily["dod_change"].round(4)
    daily["total_usd"] = daily["total_usd"].round(4)
    return daily.reset_index(drop=True)


def spend_by_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    """Table 2: spend grouped by all dimension columns."""
    available_dims = [c for c in DIMENSION_COLS if c in df.columns]
    grouped = (
        df.groupby(available_dims, as_index=False)[TOTAL_COL]
        .sum()
        .rename(columns={TOTAL_COL: "total_usd"})
        .sort_values("total_usd", ascending=False)
    )
    grouped["total_usd"] = grouped["total_usd"].round(4)
    return grouped.reset_index(drop=True)


def cost_component_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Table 3: sum of each cost component column."""
    available_costs = [c for c in COST_COLS if c in df.columns]
    totals = df[available_costs].sum().reset_index()
    totals.columns = pd.Index(["cost_component", "total_usd"])
    totals["total_usd"] = totals["total_usd"].round(4)
    return totals.sort_values("total_usd", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print_table(title: str, df: pd.DataFrame) -> None:
    """Pretty-print a DataFrame to stdout."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")
    print(df.to_string(index=False))
    print()


def save_csv(df: pd.DataFrame, out_dir: Path, filename: str) -> None:
    """Save a DataFrame as a CSV inside out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    df.to_csv(out_path, index=False)
    print(f"Saved: {out_path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a billing CSV and produce cost summary tables.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", required=True, help="Path to the billing CSV file.")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory to write output CSVs (e.g. out/). Skipped if not provided.",
    )
    args = parser.parse_args(argv)

    # Load data
    try:
        df = load_csv(args.csv)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Loaded {len(df)} rows from '{args.csv}'.", file=sys.stderr)

    # Build tables
    t1 = daily_totals(df)
    t2 = spend_by_dimensions(df)
    t3 = cost_component_breakdown(df)

    # Print to stdout
    print_table("Table 1: Daily Totals", t1)
    print_table("Table 2: Spend by Dimensions", t2)
    print_table("Table 3: Cost-Component Breakdown", t3)

    # Optionally save CSVs
    if args.out_dir:
        out_dir = Path(args.out_dir)
        save_csv(t1, out_dir, "daily_totals.csv")
        save_csv(t2, out_dir, "spend_by_dimensions.csv")
        save_csv(t3, out_dir, "cost_component_breakdown.csv")

    return 0


if __name__ == "__main__":
    sys.exit(main())
