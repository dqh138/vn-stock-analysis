"""
Valuation visualization helpers (research-grade, within data limits).

Provides:
  - Year-end valuation time series (P/E, P/B) computed from:
      year_end_close (stock_price_history) × 1000 / (eps_vnd, bvps_vnd)
    rather than relying on potentially ambiguous stored multiples.
  - Fair-price overlays using simple, data-limited heuristics:
      - Historical P/E/P/B percentiles (P25/P50/P75) over the selected window
      - Graham Number: sqrt(22.5 × EPS × BVPS)
  - Return decomposition in log space:
      log(price_end/price_start) = log(EPS_end/EPS_start) + log(PE_end/PE_start)
      log(total_return_factor) = above + log(1 + dividends / price_end)

Notes / data limits:
  - Prices are unadjusted for split/rights/bonus (only cash dividends are available here).
  - EPS/BVPS are taken from financial_ratios (annual, quarter IS NULL).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional

from .valuation_analysis import calculate_percentiles
from .. import db as _db


@dataclass(frozen=True)
class YearEndClose:
    year: int
    time: str
    close: float  # quoted in "thousand VND" in this DB convention


def _fetch_latest_financial_ratios_year(conn: Any, symbol: str) -> Optional[int]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT MAX(year) AS y
        FROM financial_ratios
        WHERE symbol = %s AND quarter IS NULL
        """,
        (symbol,),
    )
    row = cur.fetchone()
    if not row or row["y"] is None:
        return None
    try:
        return int(row["y"])
    except (TypeError, ValueError):
        return None


def _fetch_year_end_closes(
    conn: Any,
    symbol: str,
    *,
    year_from: int,
    year_to: int,
) -> Dict[int, YearEndClose]:
    """
    Return year -> (last trading date, close) for each calendar year in [year_from, year_to].
    """
    symbol = (symbol or "").strip().upper()
    start_date = f"{int(year_from)}-01-01"
    end_date = f"{int(year_to)}-12-31"

    cur = conn.cursor()
    cur.execute(
        """
        WITH last AS (
            SELECT substr(time, 1, 4) AS y, MAX(time) AS t
            FROM stock_price_history
            WHERE symbol = %s AND time >= %s AND time <= %s
            GROUP BY substr(time, 1, 4)
        )
        SELECT CAST(last.y AS INT) AS year, last.t AS time, p.close AS close
        FROM last
        JOIN stock_price_history p
          ON p.symbol = %s AND p.time = last.t
        ORDER BY year ASC
        """,
        (symbol, start_date, end_date, symbol),
    )
    out: Dict[int, YearEndClose] = {}
    for row in cur.fetchall():
        try:
            y = int(row["year"])
        except (TypeError, ValueError):
            continue
        try:
            close_f = float(row["close"]) if row["close"] is not None else None
        except (TypeError, ValueError):
            close_f = None
        if close_f is None:
            continue
        time_val = row["time"]
        if hasattr(time_val, "strftime"):
            time_val = time_val.strftime("%Y-%m-%d")
        out[y] = YearEndClose(year=y, time=str(time_val), close=close_f)
    return out


def _fetch_annual_per_share_fundamentals(
    conn: Any,
    symbol: str,
    *,
    year_from: int,
    year_to: int,
) -> Dict[int, Dict[str, Optional[float]]]:
    """
    Annual per-share inputs from `financial_ratios` (quarter IS NULL).
    """
    symbol = (symbol or "").strip().upper()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT year, eps_vnd, bvps_vnd
        FROM financial_ratios
        WHERE symbol = %s AND quarter IS NULL
          AND year >= %s AND year <= %s
        ORDER BY year ASC
        """,
        (symbol, int(year_from), int(year_to)),
    )
    out: Dict[int, Dict[str, Optional[float]]] = {}
    for row in cur.fetchall():
        try:
            y = int(row["year"])
        except (TypeError, ValueError):
            continue
        eps = None
        bvps = None
        try:
            eps = float(row["eps_vnd"]) if row["eps_vnd"] is not None else None
        except (TypeError, ValueError):
            eps = None
        try:
            bvps = float(row["bvps_vnd"]) if row["bvps_vnd"] is not None else None
        except (TypeError, ValueError):
            bvps = None
        out[y] = {"eps_vnd": eps, "bvps_vnd": bvps}
    return out


def _fetch_cash_dividends_by_year(conn: Any, symbol: str) -> Dict[int, float]:
    """
    Cash dividends per share (VND) by calendar year (exright_date preferred).
    """
    symbol = (symbol or "").strip().upper()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            CAST(substr(COALESCE(exright_date, record_date, public_date), 1, 4) AS INT) AS year,
            SUM(value) AS cash_dividend_vnd
        FROM events
        WHERE symbol = %s
          AND event_list_code = 'DIV'
          AND value IS NOT NULL AND value > 0
          AND COALESCE(exright_date, record_date, public_date) IS NOT NULL
        GROUP BY year
        """,
        (symbol,),
    )
    out: Dict[int, float] = {}
    for row in cur.fetchall():
        try:
            y = int(row["year"])
        except (TypeError, ValueError):
            continue
        try:
            v = float(row["cash_dividend_vnd"]) if row["cash_dividend_vnd"] is not None else 0.0
        except (TypeError, ValueError):
            v = 0.0
        if v > 0:
            out[y] = v
    return out


def get_valuation_timeseries(
    db_path=None,
    symbol: str = "",
    *,
    years: int = 10,
) -> Dict[str, Any]:
    """
    Year-end valuation time series for a symbol over a window of annual data.
    """
    years = max(3, min(int(years), 15))
    symbol = (symbol or "").strip().upper()
    close_scale_vnd = 1000.0

    with _db.connect() as conn:
        end_year = _fetch_latest_financial_ratios_year(conn, symbol)
        if end_year is None:
            return {"symbol": symbol, "error": "No annual financial_ratios data", "series": [], "years": []}

        start_year = end_year - years + 1

        year_closes = _fetch_year_end_closes(conn, symbol, year_from=start_year, year_to=end_year)
        fundamentals = _fetch_annual_per_share_fundamentals(conn, symbol, year_from=start_year, year_to=end_year)

        years_list = sorted(fundamentals.keys())
        series: List[Dict[str, Any]] = []
        pe_values: List[float] = []
        pb_values: List[float] = []

        for y in years_list:
            eps = fundamentals.get(y, {}).get("eps_vnd")
            bvps = fundamentals.get(y, {}).get("bvps_vnd")

            close_obj = year_closes.get(y)
            close_k = close_obj.close if close_obj else None
            close_as_of = close_obj.time if close_obj else None
            close_vnd = (float(close_k) * close_scale_vnd) if close_k is not None else None

            pe = None
            pb = None
            if close_vnd is not None and eps is not None and eps > 0:
                pe = close_vnd / float(eps)
                if pe > 0:
                    pe_values.append(pe)
            if close_vnd is not None and bvps is not None and bvps > 0:
                pb = close_vnd / float(bvps)
                if pb > 0:
                    pb_values.append(pb)

            series.append(
                {
                    "year": y,
                    "price_end": {"as_of": close_as_of, "close": close_k, "close_scale_vnd": close_scale_vnd},
                    "fundamentals": {"eps_vnd": eps, "bvps_vnd": bvps},
                    "valuation": {"pe_end": pe, "pb_end": pb},
                }
            )

        pe_pct = calculate_percentiles(pe_values)
        pb_pct = calculate_percentiles(pb_values)
        pe_pct["n"] = len(pe_values)
        pb_pct["n"] = len(pb_values)

        def _fair_close(per_share_vnd: Optional[float], multiple: Optional[float]) -> Optional[float]:
            if per_share_vnd is None or multiple is None:
                return None
            try:
                per_share = float(per_share_vnd)
                mult = float(multiple)
            except (TypeError, ValueError):
                return None
            if per_share <= 0 or mult <= 0:
                return None
            return (per_share * mult) / close_scale_vnd

        fair_lines: List[Dict[str, Any]] = []
        for pt in series:
            y = int(pt["year"])
            eps = pt["fundamentals"]["eps_vnd"]
            bvps = pt["fundamentals"]["bvps_vnd"]
            fair_lines.append(
                {
                    "year": y,
                    "fair_close": {
                        "pe_p25": _fair_close(eps, pe_pct.get("p25")),
                        "pe_p50": _fair_close(eps, pe_pct.get("p50")),
                        "pe_p75": _fair_close(eps, pe_pct.get("p75")),
                        "pb_p25": _fair_close(bvps, pb_pct.get("p25")),
                        "pb_p50": _fair_close(bvps, pb_pct.get("p50")),
                        "pb_p75": _fair_close(bvps, pb_pct.get("p75")),
                        "graham": (
                            (math.sqrt(22.5 * float(eps) * float(bvps)) / close_scale_vnd)
                            if (eps is not None and bvps is not None and eps > 0 and bvps > 0)
                            else None
                        ),
                    },
                }
            )

        return {
            "symbol": symbol,
            "period": {"start_year": start_year, "end_year": end_year},
            "years": [pt["year"] for pt in series],
            "series": series,
            "bands": {
                "pe_end": pe_pct,
                "pb_end": pb_pct,
            },
            "fair_lines": fair_lines,
            "notes": [
                "P/E, P/B are computed from year-end close × 1000 / (EPS, BVPS).",
                "Prices are unadjusted for split/rights/bonus (data limits).",
                "Cash dividends are not included in year-end multiples (use decomposition chart for dividends).",
            ],
        }


def get_return_decomposition(
    db_path=None,
    symbol: str = "",
    *,
    horizon_years: int = 5,
) -> Dict[str, Any]:
    """
    Decompose total return (cash-dividend adjusted) into:
      - EPS growth (log)
      - P/E re-rating (log)
      - Cash dividends (log, treated as end-of-year receipt)

    Output uses log-returns so components add exactly.
    """
    horizon_years = max(2, min(int(horizon_years), 10))
    symbol = (symbol or "").strip().upper()
    close_scale_vnd = 1000.0

    with _db.connect() as conn:
        end_year = _fetch_latest_financial_ratios_year(conn, symbol)
        if end_year is None:
            return {"symbol": symbol, "error": "No annual financial_ratios data"}

        requested_start = end_year - horizon_years

        year_closes = _fetch_year_end_closes(conn, symbol, year_from=requested_start, year_to=end_year)
        fundamentals = _fetch_annual_per_share_fundamentals(conn, symbol, year_from=requested_start, year_to=end_year)
        dividends = _fetch_cash_dividends_by_year(conn, symbol)

        years_range = [y for y in sorted(fundamentals.keys()) if requested_start <= y <= end_year]
        if len(years_range) < 2:
            return {"symbol": symbol, "error": "Insufficient annual fundamentals for decomposition"}

        # Ensure we have year-end prices for the boundary years
        # Use a contiguous block ending at end_year (walk backwards).
        usable: List[int] = []
        for y in reversed(years_range):
            eps = fundamentals.get(y, {}).get("eps_vnd")
            close = year_closes.get(y)
            if eps is None or eps <= 0 or close is None or close.close <= 0:
                break
            usable.append(y)
        usable.reverse()

        if len(usable) < 2:
            return {"symbol": symbol, "error": "Missing year-end price/EPS for requested window"}

        # If we ended up with a shorter horizon than requested, report it.
        start_year = usable[0]
        end_year_used = usable[-1]

        eps_log = 0.0
        pe_log = 0.0
        div_log = 0.0
        intervals_used = 0
        missing_intervals: List[Dict[str, Any]] = []

        def _pe_end(year: int) -> Optional[float]:
            eps = fundamentals.get(year, {}).get("eps_vnd")
            close = year_closes.get(year)
            if eps is None or eps <= 0 or close is None:
                return None
            price_vnd = float(close.close) * close_scale_vnd
            return (price_vnd / float(eps)) if price_vnd > 0 else None

        for y in range(start_year + 1, end_year_used + 1):
            y0 = y - 1
            eps0 = fundamentals.get(y0, {}).get("eps_vnd")
            eps1 = fundamentals.get(y, {}).get("eps_vnd")
            if eps0 is None or eps1 is None or eps0 <= 0 or eps1 <= 0:
                missing_intervals.append({"from": y0, "to": y, "reason": "missing_or_nonpositive_eps"})
                break

            close0 = year_closes.get(y0)
            close1 = year_closes.get(y)
            if close0 is None or close1 is None or close0.close <= 0 or close1.close <= 0:
                missing_intervals.append({"from": y0, "to": y, "reason": "missing_year_end_price"})
                break

            pe0 = _pe_end(y0)
            pe1 = _pe_end(y)
            if pe0 is None or pe1 is None or pe0 <= 0 or pe1 <= 0:
                missing_intervals.append({"from": y0, "to": y, "reason": "invalid_pe"})
                break

            d_vnd = float(dividends.get(y, 0.0) or 0.0)
            d_k = d_vnd / close_scale_vnd

            eps_log += math.log(float(eps1) / float(eps0))
            pe_log += math.log(float(pe1) / float(pe0))

            # dividend factor: (P_end + D) / P_end = 1 + D / P_end
            div_factor = 1.0 + (d_k / float(close1.close)) if d_k > 0 else 1.0
            if div_factor > 0:
                div_log += math.log(div_factor)

            intervals_used += 1

        total_log = eps_log + pe_log + div_log
        total_factor = math.exp(total_log) if total_log is not None else None

        return {
            "symbol": symbol,
            "period": {
                "requested_horizon_years": horizon_years,
                "start_year": start_year,
                "end_year": end_year_used,
                "intervals_used": intervals_used,
            },
            "components_log_pct": {
                "eps_growth": round(eps_log * 100.0, 2),
                "pe_rerating": round(pe_log * 100.0, 2),
                "cash_dividends": round(div_log * 100.0, 2),
                "total": round(total_log * 100.0, 2),
            },
            "components_factor": {
                "eps_growth": round(math.exp(eps_log), 4),
                "pe_rerating": round(math.exp(pe_log), 4),
                "cash_dividends": round(math.exp(div_log), 4),
                "total": round(total_factor, 4) if total_factor is not None else None,
            },
            "total_return": round((total_factor - 1.0) if total_factor is not None else 0.0, 4),
            "missing_intervals": missing_intervals,
            "notes": [
                "Decomposition uses log-returns so components add exactly.",
                "Dividends are cash only (events.DIV). Split/rights/bonus are not adjusted (data limits).",
            ],
        }
