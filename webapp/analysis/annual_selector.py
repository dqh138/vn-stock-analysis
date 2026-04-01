"""
Annual Period Selector - Vietnamese Financial Analysis Webapp

Problem:
    In the current DB, statement tables (income_statement, balance_sheet, cash_flow_statement)
    may contain multiple rows per (symbol, year) with quarter IS NULL. Many of these rows are
    duplicated quarterly snapshots, not a single annual statement row.

Academic requirement:
    - Deterministic selection: same input DB -> same selected annual row
    - Prefer "annual-like" rows using robust heuristics aligned with available data
    - Avoid silent period-mismatch across analyses (Piotroski, Altman, CAGR, reconciliation, etc.)

This module provides a single source of truth for selecting the best annual row per table.

Design goals (within data constraints):
    - Income statement annual row: choose the candidate with the largest absolute net_revenue
      (fallback: absolute revenue), which typically corresponds to the full-year figure.
    - Balance sheet annual row: choose the candidate that best matches annual ratio anchors
      (current_ratio, debt_to_equity) if available; fallback to max total_assets.
    - Cash flow annual row: choose the candidate that best matches balance-sheet cash ending
      if available; fallback to max abs(CFO).

NOTE:
    These are heuristics because the DB currently does not provide a reliable annual marker
    (e.g., quarter=5) and contains duplicated quarter=NULL rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


StatementRow = Dict[str, Any]

CandidateSource = str


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _abs_or_none(value: Optional[float]) -> Optional[float]:
    return abs(value) if value is not None else None


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _get_candidates_tagged(
    conn: Any,
    table: str,
    symbol: str,
    year: int,
) -> Tuple[List[StatementRow], CandidateSource]:
    """
    Fetch "annual-like" statement candidates and return both the rows and the candidate source.

    Candidate selection (in order):
        1) quarter IS NULL (project DB convention for annual candidates)
        2) quarter = 4 (common year-end snapshot fallback)
        3) any row for the year (last resort)

    Returns:
        (rows, source_tag)
        source_tag in {"quarter_null", "quarter_4", "any", "unavailable"}.
    """
    cur = conn.cursor()

    # Primary: quarter IS NULL (DB convention in this project).
    try:
        cur.execute(
            f"""
            SELECT *
            FROM {table}
            WHERE symbol = %s AND year = %s AND quarter IS NULL
            """,
            (symbol, year),
        )
        rows = [dict(r) for r in cur.fetchall()]
        if rows:
            return rows, "quarter_null"
    except Exception:
        # Missing table or quarter column - try fallbacks below.
        rows = []

    # Fallback: Q4 (year-end snapshot)
    try:
        cur.execute(
            f"""
            SELECT *
            FROM {table}
            WHERE symbol = %s AND year = %s AND quarter = 4
            """,
            (symbol, year),
        )
        rows = [dict(r) for r in cur.fetchall()]
        if rows:
            return rows, "quarter_4"
    except Exception:
        pass

    # Last resort: any row for the year
    try:
        cur.execute(
            f"""
            SELECT *
            FROM {table}
            WHERE symbol = %s AND year = %s
            """,
            (symbol, year),
        )
        rows = [dict(r) for r in cur.fetchall()]
        return rows, "any" if rows else "unavailable"
    except Exception:
        return [], "unavailable"


def _get_candidates(
    conn: Any,
    table: str,
    symbol: str,
    year: int,
) -> List[StatementRow]:
    rows, _ = _get_candidates_tagged(conn, table, symbol, year)
    return rows


def _pick_best_by_max_abs(rows: List[StatementRow], field_candidates: List[str]) -> Optional[StatementRow]:
    if not rows:
        return None

    best: Optional[Tuple[float, str, int, StatementRow]] = None
    for row in rows:
        for field in field_candidates:
            val = _to_float(row.get(field))
            if val is None:
                continue
            score = abs(val)
            # Deterministic tie-breakers: updated_at (string), then id
            updated_at = str(row.get("updated_at") or "")
            row_id = int(row.get("id") or 0)
            key = (score, updated_at, row_id)
            if best is None or key > (best[0], best[1], best[2]):
                best = (score, updated_at, row_id, row)
            break  # stop at first available field candidate for this row
    return best[3] if best else rows[0]


def _pick_best_by_max_abs_with_meta(
    rows: List[StatementRow],
    field_candidates: List[str],
) -> Tuple[Optional[StatementRow], Dict[str, Any]]:
    if not rows:
        return None, {"selection_reason": "no_candidates"}

    best: Optional[Tuple[float, str, int, str, float, StatementRow]] = None
    for row in rows:
        for field in field_candidates:
            val = _to_float(row.get(field))
            if val is None:
                continue
            score = abs(val)
            updated_at = str(row.get("updated_at") or "")
            row_id = int(row.get("id") or 0)
            key = (score, updated_at, row_id)
            if best is None or key > (best[0], best[1], best[2]):
                best = (score, updated_at, row_id, field, float(val), row)
            break

    if best is None:
        # Deterministic fallback
        row = rows[0]
        return row, {"selection_reason": "fallback_first_row"}

    return (
        best[5],
        {
            "selection_reason": f"max_abs({best[3]})",
            "selection_field": best[3],
            "selection_value": best[4],
        },
    )


def select_income_statement_annual_with_provenance(
    conn: Any,
    symbol: str,
    year: int,
) -> Tuple[StatementRow, Dict[str, Any]]:
    rows, candidate_source = _get_candidates_tagged(conn, "income_statement", symbol, year)
    picked, meta = _pick_best_by_max_abs_with_meta(
        rows,
        field_candidates=["net_revenue", "revenue", "gross_profit"],
    )
    picked = picked or {}

    out_meta = {
        "table": "income_statement",
        "symbol": symbol,
        "year": int(year),
        "candidate_source": candidate_source,
        "candidate_count": len(rows),
        "selected_row_id": int(picked.get("id")) if picked.get("id") is not None else None,
        **meta,
    }
    return picked, out_meta


def select_income_statement_annual(
    conn: Any,
    symbol: str,
    year: int,
) -> StatementRow:
    """
    Select the best annual-like income statement row for (symbol, year).

    Heuristic: choose the row with the largest absolute net_revenue (fallback: revenue).
    """
    picked, _ = select_income_statement_annual_with_provenance(conn, symbol, year)
    return picked or {}


@dataclass(frozen=True)
class BalanceAnchor:
    current_ratio: Optional[float]
    debt_to_equity: Optional[float]


def _get_balance_anchor(financial_ratios_row: Optional[StatementRow]) -> BalanceAnchor:
    if not financial_ratios_row:
        return BalanceAnchor(current_ratio=None, debt_to_equity=None)
    return BalanceAnchor(
        current_ratio=_to_float(financial_ratios_row.get("current_ratio")),
        debt_to_equity=_to_float(financial_ratios_row.get("debt_to_equity")),
    )


def select_balance_sheet_annual(
    conn: Any,
    symbol: str,
    year: int,
    financial_ratios_row: Optional[StatementRow] = None,
) -> StatementRow:
    """
    Select the best annual-like balance sheet row for (symbol, year).

    Primary heuristic:
        Minimize error vs annual ratio anchors (current_ratio, debt_to_equity) if available.
    Fallback heuristic:
        Maximize total_assets.
    """
    picked, _ = select_balance_sheet_annual_with_provenance(
        conn,
        symbol,
        year,
        financial_ratios_row=financial_ratios_row,
    )
    return picked or {}


def select_balance_sheet_annual_with_provenance(
    conn: Any,
    symbol: str,
    year: int,
    financial_ratios_row: Optional[StatementRow] = None,
) -> Tuple[StatementRow, Dict[str, Any]]:
    rows, candidate_source = _get_candidates_tagged(conn, "balance_sheet", symbol, year)
    if not rows:
        return {}, {
            "table": "balance_sheet",
            "symbol": symbol,
            "year": int(year),
            "candidate_source": candidate_source,
            "candidate_count": 0,
            "selected_row_id": None,
            "selection_reason": "no_candidates",
        }

    anchor = _get_balance_anchor(financial_ratios_row)

    def score_row(row: StatementRow) -> Tuple[float, float, str, int]:
        asset_current = _to_float(row.get("asset_current"))
        liab_current_reported = _to_float(row.get("liabilities_current"))
        liab_total = _to_float(row.get("liabilities_total"))
        liab_non_current = _to_float(row.get("liabilities_non_current"))
        equity_total = _to_float(row.get("equity_total"))
        total_assets = _to_float(row.get("total_assets"))
        total_eq_liab = _to_float(row.get("total_equity_and_liabilities"))

        liab_current_derived = None
        if liab_total is not None and liab_non_current is not None and liab_total > liab_non_current:
            derived = liab_total - liab_non_current
            if derived > 0:
                liab_current_derived = derived

        liab_current_effective = liab_current_reported
        current_ratio_reported = _safe_div(asset_current, liab_current_reported) if (asset_current is not None and liab_current_reported and liab_current_reported > 0) else None
        if current_ratio_reported is None or current_ratio_reported > 20:
            if liab_current_derived is not None:
                liab_current_effective = liab_current_derived

        current_ratio_calc = _safe_div(asset_current, liab_current_effective) if liab_current_effective and liab_current_effective > 0 else None
        debt_to_equity_calc = _safe_div(liab_total, equity_total) if equity_total and equity_total > 0 else None

        error = 0.0
        error_terms = 0

        use_current_ratio_anchor = (
            anchor.current_ratio is not None
            and current_ratio_calc is not None
            and 0 < anchor.current_ratio < 20
            and 0 < current_ratio_calc < 20
        )
        if use_current_ratio_anchor:
            error += 0.50 * abs(current_ratio_calc - anchor.current_ratio)
            error_terms += 1
        use_debt_to_equity_anchor = anchor.debt_to_equity is not None and debt_to_equity_calc is not None
        if use_debt_to_equity_anchor:
            error += abs(debt_to_equity_calc - anchor.debt_to_equity)
            error_terms += 1

        if current_ratio_calc is not None and current_ratio_calc > 20:
            error += min(1000.0, current_ratio_calc - 20)

        identity_penalty = 0.0
        if total_assets and total_assets > 0 and total_eq_liab is not None:
            identity_penalty = abs(total_assets - total_eq_liab) / total_assets
            error += 0.10 * identity_penalty

        if error_terms == 0:
            error = 1e9

        updated_at = str(row.get("updated_at") or "")
        row_id = int(row.get("id") or 0)
        total_assets_abs = abs(total_assets) if total_assets is not None else 0.0
        return (error, -total_assets_abs, updated_at, row_id)

    best_row = min(rows, key=score_row)
    best_key = score_row(best_row)
    best_error = best_key[0]

    fallback_used = False
    fallback_meta: Dict[str, Any] = {}
    picked: StatementRow = best_row
    selection_reason = "anchor_min_error"
    if best_error >= 1e8:
        fallback_used = True
        fallback_row, pick_meta = _pick_best_by_max_abs_with_meta(rows, field_candidates=["total_assets", "equity_total"])
        if fallback_row is not None:
            picked = fallback_row
            fallback_meta = pick_meta
            selection_reason = f"fallback_{pick_meta.get('selection_reason')}"
        else:
            selection_reason = "fallback_best_row"

    # Liquidity provenance (for the selected row only)
    asset_current = _to_float(picked.get("asset_current"))
    liab_current_reported = _to_float(picked.get("liabilities_current"))
    liab_total = _to_float(picked.get("liabilities_total"))
    liab_non_current = _to_float(picked.get("liabilities_non_current"))

    liab_current_derived = None
    if liab_total is not None and liab_non_current is not None and liab_total > liab_non_current:
        derived = liab_total - liab_non_current
        if derived > 0:
            liab_current_derived = derived

    current_ratio_reported = _safe_div(asset_current, liab_current_reported) if (asset_current is not None and liab_current_reported and liab_current_reported > 0) else None
    liab_current_effective = liab_current_reported
    derived_used = False
    if current_ratio_reported is None or current_ratio_reported > 20:
        if liab_current_derived is not None:
            liab_current_effective = liab_current_derived
            derived_used = True
    current_ratio_effective = _safe_div(asset_current, liab_current_effective) if (asset_current is not None and liab_current_effective and liab_current_effective > 0) else None

    use_current_ratio_anchor = (
        anchor.current_ratio is not None
        and current_ratio_effective is not None
        and 0 < anchor.current_ratio < 20
        and 0 < current_ratio_effective < 20
    )
    debt_to_equity_calc = _safe_div(liab_total, _to_float(picked.get("equity_total"))) if _to_float(picked.get("equity_total")) and _to_float(picked.get("equity_total")) > 0 else None
    use_debt_to_equity_anchor = anchor.debt_to_equity is not None and debt_to_equity_calc is not None

    meta: Dict[str, Any] = {
        "table": "balance_sheet",
        "symbol": symbol,
        "year": int(year),
        "candidate_source": candidate_source,
        "candidate_count": len(rows),
        "selected_row_id": int(picked.get("id")) if picked.get("id") is not None else None,
        "selection_reason": selection_reason,
        "fallback_used": fallback_used,
        "anchor": {"current_ratio": anchor.current_ratio, "debt_to_equity": anchor.debt_to_equity},
        "anchor_terms_used": [
            term for term, used in {
                "current_ratio": use_current_ratio_anchor,
                "debt_to_equity": use_debt_to_equity_anchor,
            }.items()
            if used
        ],
        "best_error": float(best_error) if best_error is not None else None,
        "liquidity_semantics": {
            "current_ratio_reported": current_ratio_reported,
            "current_ratio_effective": current_ratio_effective,
            "derived_current_liabilities_available": liab_current_derived is not None,
            "derived_current_liabilities_used": derived_used,
        },
    }

    if fallback_meta:
        meta["fallback_details"] = fallback_meta

    return picked, meta


def select_cash_flow_annual(
    conn: Any,
    symbol: str,
    year: int,
    balance_sheet_row: Optional[StatementRow] = None,
) -> StatementRow:
    """
    Select the best annual-like cash flow statement row for (symbol, year).

    Primary heuristic:
        Minimize |cash_end - balance_sheet.cash_and_equivalents| if balance sheet cash is available.
    Fallback heuristic:
        Maximize abs(net_cash_from_operating_activities).
    """
    picked, _ = select_cash_flow_annual_with_provenance(
        conn,
        symbol,
        year,
        balance_sheet_row=balance_sheet_row,
    )
    return picked or {}


def select_cash_flow_annual_with_provenance(
    conn: Any,
    symbol: str,
    year: int,
    balance_sheet_row: Optional[StatementRow] = None,
) -> Tuple[StatementRow, Dict[str, Any]]:
    rows, candidate_source = _get_candidates_tagged(conn, "cash_flow_statement", symbol, year)
    if not rows:
        return {}, {
            "table": "cash_flow_statement",
            "symbol": symbol,
            "year": int(year),
            "candidate_source": candidate_source,
            "candidate_count": 0,
            "selected_row_id": None,
            "selection_reason": "no_candidates",
        }

    bs_cash = _to_float(balance_sheet_row.get("cash_and_equivalents")) if balance_sheet_row else None

    def score_row(row: StatementRow) -> Tuple[float, float, str, int]:
        cfo = _to_float(row.get("net_cash_from_operating_activities"))
        cash_end = _to_float(row.get("cash_and_cash_equivalents_ending"))

        cash_diff = abs(cash_end - bs_cash) if (bs_cash is not None and cash_end is not None) else 1e18
        cfo_abs = abs(cfo) if cfo is not None else 0.0

        updated_at = str(row.get("updated_at") or "")
        row_id = int(row.get("id") or 0)

        return (cash_diff, -cfo_abs, updated_at, row_id)

    best_row = min(rows, key=score_row)
    best_key = score_row(best_row)

    fallback_used = False
    fallback_meta: Dict[str, Any] = {}
    picked: StatementRow = best_row
    selection_reason = "min_cash_end_diff_vs_balance_sheet"

    # If we couldn't compare cash, fall back to max abs(CFO)
    if best_key[0] >= 1e17:
        fallback_used = True
        selection_reason = "fallback_max_abs(CFO)"
        fallback_row, pick_meta = _pick_best_by_max_abs_with_meta(
            rows,
            field_candidates=["net_cash_from_operating_activities", "profit_before_tax", "net_cash_flow_period"],
        )
        if fallback_row is not None:
            picked = fallback_row
            fallback_meta = pick_meta
            selection_reason = f"fallback_{pick_meta.get('selection_reason')}"

    meta: Dict[str, Any] = {
        "table": "cash_flow_statement",
        "symbol": symbol,
        "year": int(year),
        "candidate_source": candidate_source,
        "candidate_count": len(rows),
        "selected_row_id": int(picked.get("id")) if picked.get("id") is not None else None,
        "selection_reason": selection_reason,
        "fallback_used": fallback_used,
        "cash_anchor": {
            "balance_sheet_cash": bs_cash,
            "cash_end": _to_float(picked.get("cash_and_cash_equivalents_ending")),
        },
        "cash_diff": (
            abs(_to_float(picked.get("cash_and_cash_equivalents_ending")) - bs_cash)
            if (bs_cash is not None and _to_float(picked.get("cash_and_cash_equivalents_ending")) is not None)
            else None
        ),
    }
    if fallback_meta:
        meta["fallback_details"] = fallback_meta
    return picked, meta


def get_latest_year(conn: Any, symbol: str) -> Optional[int]:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT MAX(year) AS latest_year
            FROM financial_ratios
            WHERE symbol = %s AND quarter IS NULL
            """,
            (symbol,),
        )
        row = cur.fetchone()
        if row and row["latest_year"] is not None:
            return int(row["latest_year"])
    except Exception:
        # In tests/minimal DBs the financial_ratios table may not exist.
        pass

    # Fallback: take the latest year from statement tables that exist.
    years: List[int] = []
    for table in ("income_statement", "balance_sheet", "cash_flow_statement"):
        try:
            cur.execute(
                f"SELECT MAX(year) AS y FROM {table} WHERE symbol = %s",
                (symbol,),
            )
            r = cur.fetchone()
            if r and r["y"] is not None:
                years.append(int(r["y"]))
        except Exception:
            continue
    return max(years) if years else None


def get_previous_year(conn: Any, symbol: str, year: int) -> Optional[int]:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT MAX(year) AS prev_year
            FROM financial_ratios
            WHERE symbol = %s AND quarter IS NULL AND year < %s
            """,
            (symbol, year),
        )
        row = cur.fetchone()
        if row and row["prev_year"] is not None:
            return int(row["prev_year"])
    except Exception:
        # In tests/minimal DBs the financial_ratios table may not exist.
        pass

    years: List[int] = []
    for table in ("income_statement", "balance_sheet", "cash_flow_statement"):
        try:
            cur.execute(
                f"SELECT MAX(year) AS y FROM {table} WHERE symbol = %s AND year < %s",
                (symbol, year),
            )
            r = cur.fetchone()
            if r and r["y"] is not None:
                years.append(int(r["y"]))
        except Exception:
            continue
    return max(years) if years else None


def get_financial_ratios_annual(conn: Any, symbol: str, year: int) -> StatementRow:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT *
            FROM financial_ratios
            WHERE symbol = %s AND year = %s AND quarter IS NULL
            """,
            (symbol, year),
        )
        row = cur.fetchone()
        return dict(row) if row else {}
    except Exception:
        # In tests/minimal DBs the financial_ratios table may not exist.
        return {}
