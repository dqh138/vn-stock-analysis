"""
Period Contract Helpers - Vietnamese Financial Analysis Webapp

Academic motivation:
    Quarterly and price history data unlocks new analyses (TTM, YoY/QoQ, rolling risk),
    but only if period semantics are explicit and consistent.

This module standardizes:
    - period_type: ANNUAL vs QUARTER
    - as_of_period label formatting
    - deterministic sorting keys for (year, quarter)

Notes on current DB conventions:
    - Statement tables use quarter IS NULL for annual rows, and 1..4 for quarterly rows.
      Annual rows may be duplicated when quarter IS NULL; selection is handled elsewhere.
    - financial_ratios uses quarter IS NULL for annual rows and 1..4 for quarterly rows.
      A small number of quarter=5 rows exist but are incomplete in the current DB; ignore them.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Literal, Tuple

PeriodType = Literal["ANNUAL", "QUARTER"]


def normalize_year(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_quarter(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        q = int(value)
    except (TypeError, ValueError):
        return None
    return q if 1 <= q <= 4 else None


def get_period_type(year: Any, quarter: Any) -> PeriodType:
    _ = normalize_year(year)
    q = normalize_quarter(quarter)
    return "QUARTER" if q is not None else "ANNUAL"


def as_of_period_label(year: Any, quarter: Any) -> Optional[str]:
    y = normalize_year(year)
    if y is None:
        return None
    q = normalize_quarter(quarter)
    return f"Q{q} {y}" if q is not None else f"FY {y}"


def as_of_period_key(year: Any, quarter: Any) -> Optional[int]:
    """
    Deterministic sortable key: FY uses quarter=0, quarters use 1..4.
    """
    y = normalize_year(year)
    if y is None:
        return None
    q = normalize_quarter(quarter) or 0
    return y * 10 + q


def attach_period_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach period fields to a DB row dict without mutating the input.
    """
    year = row.get("year")
    quarter = row.get("quarter")
    period_type = get_period_type(year, quarter)
    return {
        **row,
        "period_type": period_type,
        "as_of_period": as_of_period_label(year, quarter),
    }


def latest_quarter_for_symbol(conn, symbol: str, year_limit: Optional[int] = None) -> Optional[Tuple[int, int]]:
    """
    Return latest (year, quarter) available in financial_ratios for symbol.

    If year_limit is provided, only considers records with year <= year_limit.
    """
    cur = conn.cursor()
    if year_limit is not None:
        cur.execute(
            """
            SELECT year, quarter
            FROM financial_ratios
            WHERE symbol = ? AND quarter IS NOT NULL AND year <= ?
            ORDER BY year DESC, quarter DESC
            LIMIT 1
            """,
            (symbol, int(year_limit)),
        )
    else:
        cur.execute(
            """
            SELECT year, quarter
            FROM financial_ratios
            WHERE symbol = ? AND quarter IS NOT NULL
            ORDER BY year DESC, quarter DESC
            LIMIT 1
            """,
            (symbol,),
        )
    row = cur.fetchone()
    if not row:
        return None
    try:
        y = int(row[0])
        q = int(row[1])
    except (TypeError, ValueError):
        return None
    return (y, q) if 1 <= q <= 4 else None

