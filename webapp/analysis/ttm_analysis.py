"""
TTM Fundamentals Analysis - Vietnamese Financial Analysis Webapp

Academic motivation:
    Quarterly financial statements unlock time-sensitive fundamentals such as:
    - Trailing Twelve Months (TTM/LTM) revenue and profits
    - Quarterly YoY growth (Q_t / Q_{t-4} - 1)
    - TTM YoY growth (TTM_t / TTM_{t-4} - 1)
    - TTM ROA/ROE using average assets/equity when quarter-end snapshots exist

Design constraints (must stay within DB scope):
    - Quarterly statements exist for a limited set of tickers; degrade gracefully with status contracts.
    - Statement tables contain many duplicated rows where quarter IS NULL; this module ONLY uses
      quarter BETWEEN 1 AND 4 for quarterly/TTM computations.
    - Some quarterly ratios (e.g., P/E) may be TTM-like while EPS is quarter-only; avoid mixing
      semantics unless explicitly labeled as proxy.

Output contract:
    Returns period metadata and per-metric status. Missing inputs do not crash the module.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .data_contract import calculate_free_cash_flow, safe_divide


def _quarter_key(year: int, quarter: int) -> int:
    return year * 4 + quarter


def _as_of_label(year: int, quarter: int) -> str:
    return f"TTM as of Q{quarter} {year}"


def _fetch_latest_quarter(
    conn: Any,
    table: str,
    symbol: str,
    *,
    year_limit: Optional[int] = None,
    quarter_limit: Optional[int] = None,
) -> Optional[Tuple[int, int]]:
    cur = conn.cursor()
    try:
        if year_limit is None:
            cur.execute(
                f"""
                SELECT year, quarter
                FROM {table}
                WHERE symbol = %s AND quarter BETWEEN 1 AND 4
                ORDER BY year DESC, quarter DESC
                LIMIT 1
                """,
                (symbol,),
            )
        elif quarter_limit is None:
            cur.execute(
                f"""
                SELECT year, quarter
                FROM {table}
                WHERE symbol = %s AND quarter BETWEEN 1 AND 4 AND year <= %s
                ORDER BY year DESC, quarter DESC
                LIMIT 1
                """,
                (symbol, int(year_limit)),
            )
        else:
            cur.execute(
                f"""
                SELECT year, quarter
                FROM {table}
                WHERE symbol = %s
                  AND quarter BETWEEN 1 AND 4
                  AND (year < %s OR (year = %s AND quarter <= %s))
                ORDER BY year DESC, quarter DESC
                LIMIT 1
                """,
                (symbol, int(year_limit), int(year_limit), int(quarter_limit)),
            )
    except Exception:
        return None

    row = cur.fetchone()
    if not row:
        return None
    try:
        y = int(row[0])
        q = int(row[1])
    except (TypeError, ValueError):
        return None
    return (y, q) if 1 <= q <= 4 else None


def _fetch_recent_quarters(
    conn: Any,
    table: str,
    symbol: str,
    as_of_year: int,
    as_of_quarter: int,
    columns: List[str],
    limit: int,
) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cols_sql = ", ".join([f'"{c}"' for c in columns])
    try:
        cur.execute(
            f"""
            SELECT year, quarter{(', ' + cols_sql) if cols_sql else ''}
            FROM {table}
            WHERE symbol = %s
              AND quarter BETWEEN 1 AND 4
              AND (year < %s OR (year = %s AND quarter <= %s))
            ORDER BY year DESC, quarter DESC
            LIMIT %s
            """,
            (symbol, int(as_of_year), int(as_of_year), int(as_of_quarter), int(limit)),
        )
    except Exception:
        return []

    rows = [dict(r) for r in cur.fetchall()]
    return rows


@dataclass(frozen=True)
class SeriesWindow:
    rows_desc: List[Dict[str, Any]]  # most recent first
    have: int
    need: int
    consecutive: bool


def _window(rows_desc: List[Dict[str, Any]], need: int) -> SeriesWindow:
    take = rows_desc[:need]
    have = len(take)
    if have < need:
        return SeriesWindow(rows_desc=take, have=have, need=need, consecutive=False)

    keys = []
    for r in take:
        y = r.get("year")
        q = r.get("quarter")
        try:
            y_i = int(y)
            q_i = int(q)
        except (TypeError, ValueError):
            return SeriesWindow(rows_desc=take, have=have, need=need, consecutive=False)
        keys.append(_quarter_key(y_i, q_i))

    consecutive = all((keys[i] - keys[i + 1] == 1) for i in range(len(keys) - 1))
    return SeriesWindow(rows_desc=take, have=have, need=need, consecutive=consecutive)


def _sum_required(rows_desc: List[Dict[str, Any]], column: str) -> Optional[float]:
    values: List[float] = []
    for r in rows_desc:
        v = r.get(column)
        if v is None:
            return None
        try:
            values.append(float(v))
        except (TypeError, ValueError):
            return None
    return sum(values)


def _get_value(row: Optional[Dict[str, Any]], column: str) -> Optional[float]:
    if not row:
        return None
    v = row.get(column)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def analyze_ttm_fundamentals(
    db_path=None,
    symbol: str = "",
    *,
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    lookback_quarters: int = 8,
) -> Dict[str, Any]:
    """
    Analyze quarterly/TTM fundamentals as of a quarter-end.

    Period selection:
        - Default as-of is the latest available quarter in income_statement.
        - If year/quarter are provided, they are used as the as-of quarter.

    Returns:
        Dict with period metadata, TTM sums, growth rates, and optional TTM ROA/ROE.
    """
    symbol = (symbol or "").strip().upper()
    from .. import db as _db
    with _db.connect() as conn:
        # Determine as-of quarter
        if year is None and quarter is None:
            latest = _fetch_latest_quarter(conn, "income_statement", symbol)
        elif year is not None and quarter is None:
            latest = _fetch_latest_quarter(conn, "income_statement", symbol, year_limit=int(year))
        elif year is not None and quarter is not None:
            q = int(quarter)
            if q < 1 or q > 4:
                return {
                    "symbol": symbol,
                    "status": "INVALID",
                    "error": "invalid_quarter",
                    "message": "quarter must be 1..4",
                }
            latest = _fetch_latest_quarter(conn, "income_statement", symbol, year_limit=int(year), quarter_limit=q)
        else:
            # quarter without year
            return {
                "symbol": symbol,
                "status": "INVALID",
                "error": "missing_year",
                "message": "year is required when quarter is provided",
            }

        if not latest:
            return {
                "symbol": symbol,
                "status": "PENDING_QUARTER_DATA",
                "message": "Không có dữ liệu báo cáo quý (income_statement) để tính TTM.",
                "period": {"period_type": "TTM", "year": None, "quarter": None, "as_of_period": None},
            }

        as_of_year, as_of_quarter = latest

        period = {
            "period_type": "TTM",
            "year": as_of_year,
            "quarter": as_of_quarter,
            "as_of_period": _as_of_label(as_of_year, as_of_quarter),
        }

        # Income statement flows (TTM sums)
        is_cols = [
            "net_revenue",
            "revenue",
            "gross_profit",
            "operating_profit",
            "profit_before_tax",
            "corporate_income_tax",
            "net_profit_parent_company",
            "net_profit",
        ]
        is_rows_desc = _fetch_recent_quarters(
            conn,
            "income_statement",
            symbol,
            as_of_year,
            as_of_quarter,
            columns=is_cols,
            limit=max(lookback_quarters, 8),
        )
        w4_is = _window(is_rows_desc, 4)
        w8_is = _window(is_rows_desc, 8)

        # Choose revenue column preference: prefer net_revenue if available for all quarters
        revenue_col = "net_revenue" if _sum_required(w4_is.rows_desc, "net_revenue") is not None else "revenue"

        revenue_ttm = _sum_required(w4_is.rows_desc, revenue_col) if w4_is.consecutive else None
        gross_profit_ttm = _sum_required(w4_is.rows_desc, "gross_profit") if w4_is.consecutive else None
        op_profit_ttm = _sum_required(w4_is.rows_desc, "operating_profit") if w4_is.consecutive else None
        net_profit_ttm = _sum_required(w4_is.rows_desc, "net_profit_parent_company") if w4_is.consecutive else None
        if net_profit_ttm is None and w4_is.consecutive:
            net_profit_ttm = _sum_required(w4_is.rows_desc, "net_profit")

        # Quarterly YoY growth (for revenue and net profit)
        quarter_current = w4_is.rows_desc[0] if w4_is.have >= 1 else None
        quarter_prev_year = w8_is.rows_desc[4] if w8_is.have >= 5 else None

        rev_q = _get_value(quarter_current, revenue_col)
        rev_q_prev = _get_value(quarter_prev_year, revenue_col)
        rev_q_yoy = safe_divide(rev_q, rev_q_prev) - 1 if (rev_q is not None and rev_q_prev not in (None, 0)) else None

        np_q = _get_value(quarter_current, "net_profit_parent_company")
        if np_q is None:
            np_q = _get_value(quarter_current, "net_profit")
        np_q_prev = _get_value(quarter_prev_year, "net_profit_parent_company")
        if np_q_prev is None:
            np_q_prev = _get_value(quarter_prev_year, "net_profit")
        np_q_yoy = safe_divide(np_q, np_q_prev) - 1 if (np_q is not None and np_q_prev not in (None, 0)) else None

        # TTM YoY growth requires 8 consecutive quarters
        revenue_ttm_prev = None
        net_profit_ttm_prev = None
        if w8_is.consecutive:
            prev4 = w8_is.rows_desc[4:8]
            revenue_ttm_prev = _sum_required(prev4, revenue_col)
            net_profit_ttm_prev = _sum_required(prev4, "net_profit_parent_company")
            if net_profit_ttm_prev is None:
                net_profit_ttm_prev = _sum_required(prev4, "net_profit")

        revenue_ttm_yoy = (
            safe_divide(revenue_ttm, revenue_ttm_prev) - 1
            if (revenue_ttm is not None and revenue_ttm_prev not in (None, 0))
            else None
        )
        net_profit_ttm_yoy = (
            safe_divide(net_profit_ttm, net_profit_ttm_prev) - 1
            if (net_profit_ttm is not None and net_profit_ttm_prev not in (None, 0))
            else None
        )

        # Balance sheet snapshots (for TTM ROA/ROE using avg assets/equity)
        bs_cols = ["total_assets", "equity_total", "liabilities_total", "asset_current", "liabilities_current"]
        bs_end_rows = _fetch_recent_quarters(
            conn,
            "balance_sheet",
            symbol,
            as_of_year,
            as_of_quarter,
            columns=bs_cols,
            limit=1,
        )
        bs_end = bs_end_rows[0] if bs_end_rows else None

        # Begin snapshot: quarter t-4 (same quarter previous year)
        begin_year = as_of_year - 1
        begin_quarter = as_of_quarter
        bs_begin_rows = _fetch_recent_quarters(
            conn,
            "balance_sheet",
            symbol,
            begin_year,
            begin_quarter,
            columns=bs_cols,
            limit=1,
        )
        # The query is <= begin_quarter; ensure we actually picked the intended quarter
        bs_begin = None
        if bs_begin_rows:
            r0 = bs_begin_rows[0]
            try:
                if int(r0.get("year")) == begin_year and int(r0.get("quarter")) == begin_quarter:
                    bs_begin = r0
            except (TypeError, ValueError):
                bs_begin = None

        assets_end = _get_value(bs_end, "total_assets")
        equity_end = _get_value(bs_end, "equity_total")
        assets_begin = _get_value(bs_begin, "total_assets")
        equity_begin = _get_value(bs_begin, "equity_total")

        avg_assets = (assets_end + assets_begin) / 2 if (assets_end is not None and assets_begin is not None) else None
        avg_equity = (equity_end + equity_begin) / 2 if (equity_end is not None and equity_begin is not None) else None

        roa_ttm = safe_divide(net_profit_ttm, avg_assets) if (net_profit_ttm is not None and avg_assets not in (None, 0)) else None
        roe_ttm = safe_divide(net_profit_ttm, avg_equity) if (net_profit_ttm is not None and avg_equity not in (None, 0)) else None

        # Cash flow (optional): CFO/CapEx/FCF TTM
        cf_cols = ["net_cash_from_operating_activities", "purchase_purchase_fixed_assets"]
        cf_rows_desc = _fetch_recent_quarters(
            conn,
            "cash_flow_statement",
            symbol,
            as_of_year,
            as_of_quarter,
            columns=cf_cols,
            limit=8,
        )
        w4_cf = _window(cf_rows_desc, 4)
        cfo_ttm = _sum_required(w4_cf.rows_desc, "net_cash_from_operating_activities") if w4_cf.consecutive else None
        capex_ttm = _sum_required(w4_cf.rows_desc, "purchase_purchase_fixed_assets") if w4_cf.consecutive else None
        fcf_ttm = calculate_free_cash_flow(cfo_ttm, capex_ttm) if (cfo_ttm is not None and capex_ttm is not None) else None

        # EPS TTM proxy from financial_ratios (optional)
        fr_cols = ["eps_vnd", "price_to_earnings", "price_to_book", "market_cap_billions"]
        fr_rows_desc = _fetch_recent_quarters(
            conn,
            "financial_ratios",
            symbol,
            as_of_year,
            as_of_quarter,
            columns=fr_cols,
            limit=8,
        )
        w4_fr = _window(fr_rows_desc, 4)
        eps_ttm_proxy = _sum_required(w4_fr.rows_desc, "eps_vnd") if w4_fr.consecutive else None

        pe_snapshot = None
        pb_snapshot = None
        if fr_rows_desc:
            pe_snapshot = _get_value(fr_rows_desc[0], "price_to_earnings")
            pb_snapshot = _get_value(fr_rows_desc[0], "price_to_book")

        # Derived margins
        gross_margin_ttm = safe_divide(gross_profit_ttm, revenue_ttm) if (gross_profit_ttm is not None and revenue_ttm not in (None, 0)) else None
        op_margin_ttm = safe_divide(op_profit_ttm, revenue_ttm) if (op_profit_ttm is not None and revenue_ttm not in (None, 0)) else None
        net_margin_ttm = safe_divide(net_profit_ttm, revenue_ttm) if (net_profit_ttm is not None and revenue_ttm not in (None, 0)) else None
        cfo_margin_ttm = safe_divide(cfo_ttm, revenue_ttm) if (cfo_ttm is not None and revenue_ttm not in (None, 0)) else None

        # Status: require 4 consecutive quarters for income-statement TTM core
        core_ok = w4_is.consecutive and (revenue_ttm is not None) and (net_profit_ttm is not None)
        status = "OK" if core_ok else "PENDING_QUARTER_DATA"

        return {
            "symbol": symbol,
            "status": status,
            "period": period,
            "coverage": {
                "income_statement": {"have": w4_is.have, "need": 4, "consecutive": w4_is.consecutive},
                "income_statement_8q": {"have": w8_is.have, "need": 8, "consecutive": w8_is.consecutive},
                "balance_sheet": {"have": 1 if bs_end else 0, "need": 1, "as_of": "OK" if bs_end else "MISSING"},
                "cash_flow_statement": {"have": w4_cf.have, "need": 4, "consecutive": w4_cf.consecutive},
                "financial_ratios": {"have": w4_fr.have, "need": 4, "consecutive": w4_fr.consecutive},
            },
            "ttm": {
                "revenue": revenue_ttm,
                "gross_profit": gross_profit_ttm,
                "operating_profit": op_profit_ttm,
                "net_profit": net_profit_ttm,
                "cfo": cfo_ttm,
                "capex": capex_ttm,
                "fcf": fcf_ttm,
                "eps_ttm_proxy": eps_ttm_proxy,
            },
            "growth": {
                "quarter_yoy": {"revenue": rev_q_yoy, "net_profit": np_q_yoy},
                "ttm_yoy": {"revenue": revenue_ttm_yoy, "net_profit": net_profit_ttm_yoy},
            },
            "derived": {
                "gross_margin_ttm": gross_margin_ttm,
                "operating_margin_ttm": op_margin_ttm,
                "net_margin_ttm": net_margin_ttm,
                "cfo_margin_ttm": cfo_margin_ttm,
                "roa_ttm": roa_ttm,
                "roe_ttm": roe_ttm,
                "pe_snapshot": pe_snapshot,
                "pb_snapshot": pb_snapshot,
            },
            "notes": [
                f"Revenue source: income_statement.{revenue_col}",
                "EPS TTM is a proxy: sum of quarterly financial_ratios.eps_vnd (may differ from FY EPS due to share count changes).",
            ],
        }


def get_ttm_series(
    db_path=None,
    symbol: str = "",
    *,
    count: int = 12,
    lookback_quarters: int = 40,
) -> Dict[str, Any]:
    """
    Build a rolling TTM time series over recent quarters (income statement + cash flow).

    Each point represents "TTM as of Q{quarter} {year}" and requires 4 consecutive quarters.
    Degrades gracefully when gaps exist.
    """
    symbol = (symbol or "").strip().upper()
    count = max(4, min(int(count), 24))
    lookback_quarters = max(count + 6, min(int(lookback_quarters), 80))

    from .. import db as _db
    with _db.connect() as conn:
        latest = _fetch_latest_quarter(conn, "income_statement", symbol)
        if not latest:
            return {
                "symbol": symbol,
                "status": "PENDING_QUARTER_DATA",
                "message": "Không có dữ liệu báo cáo quý (income_statement) để tạo TTM series.",
                "points": [],
            }

        as_of_year, as_of_quarter = latest

        # Fetch recent quarters (desc)
        is_cols = [
            "net_revenue",
            "revenue",
            "gross_profit",
            "operating_profit",
            "net_profit_parent_company",
            "net_profit",
        ]
        is_rows_desc = _fetch_recent_quarters(
            conn,
            "income_statement",
            symbol,
            as_of_year,
            as_of_quarter,
            columns=is_cols,
            limit=lookback_quarters,
        )

        if not is_rows_desc:
            return {
                "symbol": symbol,
                "status": "PENDING_QUARTER_DATA",
                "message": "Không có quarterly rows để tính TTM series.",
                "points": [],
            }

        # Prefer net_revenue if latest 4 quarters have it fully.
        w4_latest = _window(is_rows_desc, 4)
        revenue_col = "net_revenue" if (w4_latest.consecutive and _sum_required(w4_latest.rows_desc, "net_revenue") is not None) else "revenue"

        # Choose net profit column preference similarly.
        profit_col = "net_profit_parent_company"
        if w4_latest.consecutive and _sum_required(w4_latest.rows_desc, "net_profit_parent_company") is None:
            profit_col = "net_profit"

        # Map for fast lookup
        is_by_key: Dict[int, Dict[str, Any]] = {}
        for r in is_rows_desc:
            try:
                y = int(r.get("year"))
                q = int(r.get("quarter"))
            except (TypeError, ValueError):
                continue
            if q < 1 or q > 4:
                continue
            k = _quarter_key(y, q)
            if k not in is_by_key:
                is_by_key[k] = r

        # Cash flow map (optional series)
        cf_cols = ["net_cash_from_operating_activities", "purchase_purchase_fixed_assets"]
        cf_rows_desc = _fetch_recent_quarters(
            conn,
            "cash_flow_statement",
            symbol,
            as_of_year,
            as_of_quarter,
            columns=cf_cols,
            limit=lookback_quarters,
        )
        cf_by_key: Dict[int, Dict[str, Any]] = {}
        for r in cf_rows_desc:
            try:
                y = int(r.get("year"))
                q = int(r.get("quarter"))
            except (TypeError, ValueError):
                continue
            if q < 1 or q > 4:
                continue
            k = _quarter_key(y, q)
            if k not in cf_by_key:
                cf_by_key[k] = r

        points_desc: List[Dict[str, Any]] = []
        for r in is_rows_desc[:count]:
            try:
                y = int(r.get("year"))
                q = int(r.get("quarter"))
            except (TypeError, ValueError):
                continue
            if q < 1 or q > 4:
                continue

            key = _quarter_key(y, q)
            keys = [key - i for i in range(4)]
            consecutive = all(k in is_by_key for k in keys)

            revenue_ttm = None
            net_profit_ttm = None
            gross_profit_ttm = None
            op_profit_ttm = None
            status = "PENDING_QUARTER_DATA"

            if consecutive:
                win = [is_by_key[k] for k in keys]
                revenue_ttm = _sum_required(win, revenue_col)
                gross_profit_ttm = _sum_required(win, "gross_profit")
                op_profit_ttm = _sum_required(win, "operating_profit")
                net_profit_ttm = _sum_required(win, profit_col)

                if revenue_ttm is not None and net_profit_ttm is not None:
                    status = "OK"

            # Cash flow window (optional)
            cfo_ttm = None
            capex_ttm = None
            fcf_ttm = None
            if consecutive and all(k in cf_by_key for k in keys):
                cf_win = [cf_by_key[k] for k in keys]
                cfo_ttm = _sum_required(cf_win, "net_cash_from_operating_activities")
                capex_ttm = _sum_required(cf_win, "purchase_purchase_fixed_assets")
                fcf_ttm = calculate_free_cash_flow(cfo_ttm, capex_ttm) if (cfo_ttm is not None and capex_ttm is not None) else None

            gross_margin_ttm = safe_divide(gross_profit_ttm, revenue_ttm) if (gross_profit_ttm is not None and revenue_ttm not in (None, 0)) else None
            op_margin_ttm = safe_divide(op_profit_ttm, revenue_ttm) if (op_profit_ttm is not None and revenue_ttm not in (None, 0)) else None
            net_margin_ttm = safe_divide(net_profit_ttm, revenue_ttm) if (net_profit_ttm is not None and revenue_ttm not in (None, 0)) else None
            cfo_margin_ttm = safe_divide(cfo_ttm, revenue_ttm) if (cfo_ttm is not None and revenue_ttm not in (None, 0)) else None

            points_desc.append(
                {
                    "year": y,
                    "quarter": q,
                    "period": f"Q{q} {y}",
                    "as_of_period": _as_of_label(y, q),
                    "status": status,
                    "coverage": {"have": 4 if consecutive else None, "need": 4, "consecutive": bool(consecutive)},
                    "ttm": {
                        "revenue": revenue_ttm,
                        "net_profit": net_profit_ttm,
                        "gross_profit": gross_profit_ttm,
                        "operating_profit": op_profit_ttm,
                        "cfo": cfo_ttm,
                        "capex": capex_ttm,
                        "fcf": fcf_ttm,
                    },
                    "derived": {
                        "gross_margin": gross_margin_ttm,
                        "operating_margin": op_margin_ttm,
                        "net_margin": net_margin_ttm,
                        "cfo_margin": cfo_margin_ttm,
                    },
                }
            )

        points_desc.sort(key=lambda p: (_quarter_key(int(p["year"]), int(p["quarter"]))))

        ok_points = [p for p in points_desc if p.get("status") == "OK"]
        status = "OK" if len(ok_points) >= 2 else "PENDING_QUARTER_DATA"

        return {
            "symbol": symbol,
            "status": status,
            "period": {"as_of_year": as_of_year, "as_of_quarter": as_of_quarter, "as_of_period": _as_of_label(as_of_year, as_of_quarter)},
            "inputs": {"revenue_col": revenue_col, "profit_col": profit_col},
            "points": points_desc,
            "notes": [
                "TTM series requires 4 consecutive quarters for each point.",
                "Cash flow TTM is optional and depends on cash_flow_statement quarterly coverage.",
            ],
        }
