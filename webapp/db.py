from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import psycopg2
import psycopg2.extras
import psycopg2.extensions


# ---------------------------------------------------------------------------
# Compatibility shim: accept an optional db_path argument (ignored).
# All callers that previously passed a SQLite Path can keep their call-site
# unchanged; the connection is always built from the DATABASE_URL env-var.
# ---------------------------------------------------------------------------

def _get_connection_string() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Set it to your Supabase direct PostgreSQL connection string."
        )
    return url


@dataclass(frozen=True)
class TableRow:
    year: int
    quarter: Optional[int]
    period: str
    source: Optional[str]
    updated_at: Optional[str]
    values: Dict[str, Any]
    selected_row_id: Optional[int] = None
    candidate_source: Optional[str] = None
    candidate_count: Optional[int] = None
    selection_reason: Optional[str] = None
    fallback_used: Optional[bool] = None


@contextmanager
def connect(_db_path: Any = None) -> Iterator[psycopg2.extensions.connection]:
    """
    Open a psycopg2 connection to Supabase PostgreSQL.
    The _db_path argument is accepted for backwards-compatibility but ignored.
    """
    conn: Optional[psycopg2.extensions.connection] = None
    try:
        conn = psycopg2.connect(
            _get_connection_string(),
            cursor_factory=psycopg2.extras.RealDictCursor,
            sslmode="require",
            connect_timeout=10,
        )
        conn.autocommit = True
        yield conn
    finally:
        if conn is not None and not conn.closed:
            conn.close()


def fetch_all(conn: psycopg2.extensions.connection, query: str, params: Tuple[Any, ...]) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


def fetch_one(conn: psycopg2.extensions.connection, query: str, params: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row is not None else None


def search_symbols(conn: psycopg2.extensions.connection, q: str, limit: int = 20) -> List[Dict[str, Any]]:
    q = (q or "").strip().upper()
    like_ticker = f"{q}%"
    like_name = f"%{q}%"
    return fetch_all(
        conn,
        """
        SELECT
            s.ticker,
            s.organ_name,
            STRING_AGG(DISTINCT se.exchange, ',') AS exchanges
        FROM stocks s
        LEFT JOIN stock_exchange se ON se.ticker = s.ticker
        WHERE LENGTH(s.ticker) = 3
          AND s.ticker ~ '^[A-Z]{3}$'
          AND (
                s.ticker LIKE %s
             OR UPPER(COALESCE(s.organ_name, '')) LIKE %s
          )
        GROUP BY s.ticker
        ORDER BY s.ticker
        LIMIT %s
        """,
        (like_ticker, like_name, limit),
    )


def get_symbol_meta(conn: psycopg2.extensions.connection, symbol: str) -> Optional[Dict[str, Any]]:
    symbol = symbol.strip().upper()
    return fetch_one(
        conn,
        """
        SELECT
            s.ticker,
            s.organ_name,
            MAX(si.icb_code) AS icb_code,
            MAX(si.icb_name3) AS icb_name3,
            MAX(si.icb_name4) AS icb_name4,
            STRING_AGG(DISTINCT se.exchange, ',') AS exchanges
        FROM stocks s
        LEFT JOIN stock_industry si ON si.ticker = s.ticker
        LEFT JOIN stock_exchange se ON se.ticker = s.ticker
        WHERE s.ticker = %s
        GROUP BY s.ticker
        """,
        (symbol,),
    )


def get_available_periods(conn: psycopg2.extensions.connection, symbol: str) -> Dict[str, Any]:
    symbol = symbol.strip().upper()
    rows = fetch_all(
        conn,
        """
        SELECT DISTINCT year, quarter FROM income_statement WHERE symbol = %s
        UNION
        SELECT DISTINCT year, quarter FROM balance_sheet WHERE symbol = %s
        UNION
        SELECT DISTINCT year, quarter FROM cash_flow_statement WHERE symbol = %s
        UNION
        SELECT DISTINCT year, quarter FROM financial_ratios WHERE symbol = %s
        ORDER BY year DESC, quarter DESC NULLS LAST
        """,
        (symbol, symbol, symbol, symbol),
    )

    years: List[int] = []
    yearly_years: List[int] = []
    quarterly_by_year: Dict[int, List[int]] = {}

    for r in rows:
        year = r.get("year")
        quarter = r.get("quarter")
        if year is None:
            continue
        if year not in years:
            years.append(year)
        if quarter is None or quarter == 5:
            if year not in yearly_years:
                yearly_years.append(year)
            continue
        if 1 <= int(quarter) <= 4:
            quarterly_by_year.setdefault(year, [])
            if int(quarter) not in quarterly_by_year[year]:
                quarterly_by_year[year].append(int(quarter))

    for y in quarterly_by_year:
        quarterly_by_year[y].sort()

    return {"years": years, "yearly_years": yearly_years, "quarterly_by_year": quarterly_by_year}


def _yearly_quarter_condition() -> str:
    return "(quarter IS NULL OR quarter = 5)"


def get_latest_row(
    conn: psycopg2.extensions.connection,
    table: str,
    symbol: str,
    metric_ids: Iterable[str],
    *,
    year: Optional[int],
    quarter: Optional[int],
) -> Optional[TableRow]:
    symbol = symbol.strip().upper()
    metric_list = [m for m in metric_ids]
    columns = ", ".join([f'"{c}"' for c in metric_list])

    if quarter is None:
        qcond = _yearly_quarter_condition()
        qparams: Tuple[Any, ...] = ()
    else:
        qcond = "quarter = %s"
        qparams = (quarter,)

    if year is None:
        row = fetch_one(
            conn,
            f"SELECT MAX(year) AS year FROM {table} WHERE symbol = %s AND {qcond}",
            (symbol,) + qparams,
        )
        if not row or row.get("year") is None:
            return None
        year = int(row["year"])

    if quarter is None and table in {"income_statement", "balance_sheet", "cash_flow_statement"}:
        try:
            from .analysis.annual_selector import (
                get_financial_ratios_annual,
                select_balance_sheet_annual,
                select_balance_sheet_annual_with_provenance,
                select_cash_flow_annual,
                select_cash_flow_annual_with_provenance,
                select_income_statement_annual,
                select_income_statement_annual_with_provenance,
            )

            picked: Optional[Dict[str, Any]] = None
            meta: Dict[str, Any] = {}
            if table == "income_statement":
                picked, meta = select_income_statement_annual_with_provenance(conn, symbol, year)
                picked = picked or None
            elif table == "balance_sheet":
                ratios_row = get_financial_ratios_annual(conn, symbol, year) or {}
                picked, meta = select_balance_sheet_annual_with_provenance(conn, symbol, year, financial_ratios_row=ratios_row)
                picked = picked or None
            else:
                ratios_row = get_financial_ratios_annual(conn, symbol, year) or {}
                bs_row = select_balance_sheet_annual(conn, symbol, year, financial_ratios_row=ratios_row) or {}
                picked, meta = select_cash_flow_annual_with_provenance(conn, symbol, year, balance_sheet_row=bs_row)
                picked = picked or None

            if not picked:
                return None

            period = str(picked.get("period") or "")
            row_year = int(picked.get("year") or year)
            row_quarter = picked.get("quarter")
            row_quarter = int(row_quarter) if row_quarter is not None else None
            source = picked.get("source")
            updated_at = picked.get("updated_at")
            values = {m: picked.get(m) for m in metric_list}
            return TableRow(
                year=row_year,
                quarter=row_quarter,
                period=period,
                source=source,
                updated_at=updated_at,
                values=values,
                selected_row_id=meta.get("selected_row_id"),
                candidate_source=meta.get("candidate_source"),
                candidate_count=meta.get("candidate_count"),
                selection_reason=meta.get("selection_reason"),
                fallback_used=meta.get("fallback_used"),
            )
        except Exception:
            pass

    select_cols = f"period, year, quarter, source, updated_at{(', ' + columns) if columns else ''}"
    data = fetch_one(
        conn,
        f"""
        SELECT {select_cols}
        FROM {table}
        WHERE symbol = %s
          AND year = %s
          AND {qcond}
        ORDER BY updated_at DESC NULLS LAST
        LIMIT 1
        """,
        (symbol, year) + qparams,
    )
    if not data:
        return None

    period = str(data.get("period") or "")
    row_year = int(data.get("year") or year)
    row_quarter = data.get("quarter")
    row_quarter = int(row_quarter) if row_quarter is not None else None
    source = data.get("source")
    updated_at = data.get("updated_at")

    values = {m: data.get(m) for m in metric_list}
    return TableRow(year=row_year, quarter=row_quarter, period=period, source=source, updated_at=updated_at, values=values)


def get_metric_series(
    conn: psycopg2.extensions.connection,
    table: str,
    symbol: str,
    metric_id: str,
    *,
    period: str = "yearly",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> List[Dict[str, Any]]:
    symbol = symbol.strip().upper()
    metric_id = metric_id.strip()

    if period == "yearly" and table in {"income_statement", "balance_sheet", "cash_flow_statement"}:
        try:
            where = ["symbol = %s", "(quarter IS NULL OR quarter = 4)"]
            params: List[Any] = [symbol]
            if year_from is not None:
                where.append("year >= %s")
                params.append(int(year_from))
            if year_to is not None:
                where.append("year <= %s")
                params.append(int(year_to))
            where_sql = " AND ".join(where)

            rows = fetch_all(
                conn,
                f"SELECT DISTINCT year FROM {table} WHERE {where_sql} ORDER BY year ASC",
                tuple(params),
            )
            years = [int(r["year"]) for r in rows if r.get("year") is not None]

            from .analysis.annual_selector import (
                get_financial_ratios_annual,
                select_balance_sheet_annual,
                select_cash_flow_annual,
                select_income_statement_annual,
            )

            out: List[Dict[str, Any]] = []
            for y in years:
                picked: Optional[Dict[str, Any]] = None
                if table == "income_statement":
                    picked = select_income_statement_annual(conn, symbol, y) or None
                elif table == "balance_sheet":
                    ratios_row = get_financial_ratios_annual(conn, symbol, y) or {}
                    picked = select_balance_sheet_annual(conn, symbol, y, financial_ratios_row=ratios_row) or None
                else:
                    ratios_row = get_financial_ratios_annual(conn, symbol, y) or {}
                    bs_row = select_balance_sheet_annual(conn, symbol, y, financial_ratios_row=ratios_row) or {}
                    picked = select_cash_flow_annual(conn, symbol, y, balance_sheet_row=bs_row) or None

                value = picked.get(metric_id) if picked else None
                out.append({"year": int(y), "quarter": None, "label": f"{y}", "value": value})
            return out
        except Exception:
            pass

    where = ["symbol = %s"]
    params_list: List[Any] = [symbol]

    if period == "yearly":
        where.append(_yearly_quarter_condition())
    elif period == "quarterly":
        where.append("quarter IS NOT NULL AND quarter BETWEEN 1 AND 4")
    else:
        raise ValueError("period must be 'yearly' or 'quarterly'")

    if year_from is not None:
        where.append("year >= %s")
        params_list.append(int(year_from))
    if year_to is not None:
        where.append("year <= %s")
        params_list.append(int(year_to))

    where_sql = " AND ".join(where)
    rows = fetch_all(
        conn,
        f"""
        SELECT year, quarter, period, "{metric_id}" AS value
        FROM {table}
        WHERE {where_sql}
        ORDER BY year ASC, quarter ASC NULLS FIRST
        """,
        tuple(params_list),
    )

    out_list: List[Dict[str, Any]] = []
    for r in rows:
        y = r.get("year")
        q = r.get("quarter")
        val = r.get("value")
        if y is None:
            continue
        label = f"{y}" if (q is None or int(q) == 5) else f"{y}Q{int(q)}"
        out_list.append({"year": int(y), "quarter": int(q) if q is not None else None, "label": label, "value": val})
    return out_list


def get_price_series(
    conn: psycopg2.extensions.connection,
    symbol: str,
    *,
    days: int = 120,
) -> List[Dict[str, Any]]:
    symbol = symbol.strip().upper()
    days = max(5, min(int(days), 1000))
    rows = fetch_all(
        conn,
        """
        SELECT time, close
        FROM stock_price_history
        WHERE symbol = %s
        ORDER BY time DESC
        LIMIT %s
        """,
        (symbol, days),
    )
    rows.reverse()
    return [{"time": str(r.get("time")), "close": r.get("close")} for r in rows]
