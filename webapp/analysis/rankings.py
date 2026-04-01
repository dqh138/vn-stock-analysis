from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

import datetime
import time


RankingSort = Literal["overall", "valuation", "growth"]


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percentile_rank(sorted_values: List[float], x: Optional[float]) -> Optional[float]:
    """
    Percentile rank in [0, 1] using an average-rank tie strategy.

    - 0.0 means "smallest"
    - 1.0 means "largest"
    """
    if x is None or not sorted_values:
        return None

    n = len(sorted_values)
    if n == 1:
        return 0.5

    left = bisect_left(sorted_values, x)
    right = bisect_right(sorted_values, x)
    avg_rank = (left + right) / 2.0
    return max(0.0, min(1.0, avg_rank / (n - 1)))


def _weighted_mean(values_and_weights: Iterable[Tuple[Optional[float], float]]) -> Optional[float]:
    total_weight = 0.0
    total = 0.0
    for value, weight in values_and_weights:
        if value is None:
            continue
        if weight <= 0:
            continue
        total_weight += float(weight)
        total += float(value) * float(weight)
    if total_weight <= 0:
        return None
    return total / total_weight


def _score_from_percentile(pct: Optional[float], *, invert: bool = False) -> Optional[float]:
    if pct is None:
        return None
    pct = max(0.0, min(1.0, float(pct)))
    score = (1.0 - pct) * 100.0 if invert else pct * 100.0
    return max(0.0, min(100.0, score))


def _valuation_band(avg_multiple_pct: Optional[float]) -> str:
    if avg_multiple_pct is None:
        return "unknown"
    if avg_multiple_pct <= 0.33:
        return "cheap"
    if avg_multiple_pct >= 0.67:
        return "expensive"
    return "fair"


def _growth_band(growth_score: Optional[float]) -> str:
    if growth_score is None:
        return "unknown"
    if growth_score >= 70:
        return "high"
    if growth_score >= 40:
        return "medium"
    return "low"


def _cache_bucket(interval_seconds: int = 300) -> int:
    """Return a time-bucketed key for lru_cache (refreshes every interval_seconds)."""
    return int(time.time()) // interval_seconds


def _get_available_years(conn: Any) -> List[int]:
    """Get all years with financial data, sorted descending"""
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT year FROM financial_ratios WHERE quarter IS NULL ORDER BY year DESC")
        return [int(row["year"]) for row in cur.fetchall() if row and row["year"] is not None]


def _suggest_default_year(conn: Any) -> Optional[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(year) AS y FROM financial_ratios WHERE quarter IS NULL")
        row = cur.fetchone()
        latest = int(row["y"]) if row and row["y"] is not None else None
        if latest is None:
            return None

        cur.execute(
            """
            SELECT year, COUNT(DISTINCT symbol) AS symbols
            FROM financial_ratios
            WHERE quarter IS NULL AND year IN (%s, %s)
            GROUP BY year
            """,
            (latest, latest - 1),
        )
        counts = {int(r["year"]): int(r["symbols"]) for r in cur.fetchall() if r and r["year"] is not None}
    latest_count = counts.get(latest, 0)
    prev_count = counts.get(latest - 1, 0)
    if prev_count > 0 and latest_count / prev_count < 0.85:
        return latest - 1
    return latest


def _resolve_financial_year_for_rankings(conn: Any, requested_year: int) -> Tuple[int, bool]:
    current_year = datetime.datetime.now().year

    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) as cnt FROM financial_ratios WHERE year = %s AND quarter IS NULL",
            (int(requested_year),)
        )
        has_data = cur.fetchone()["cnt"] > 0

    if has_data:
        use_latest_prices = (int(requested_year) == current_year)
        return int(requested_year), use_latest_prices

    if int(requested_year) == current_year:
        latest_year = _suggest_default_year(conn)
        if latest_year is not None:
            return latest_year, True

    return int(requested_year), False


def _get_latest_prices(conn: Any) -> Dict[str, float]:
    """Get the latest closing price for each stock from stock_price_history (in VND)"""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (symbol) symbol, close
            FROM stock_price_history
            WHERE symbol IN (SELECT DISTINCT symbol FROM financial_ratios WHERE quarter IS NULL)
            ORDER BY symbol, time DESC
            """
        )
        rows = cur.fetchall()

    prices = {}
    for row in rows:
        symbol = str(row["symbol"] or "").strip().upper()
        close = _to_float(row["close"])
        if symbol and close is not None and close > 0:
            prices[symbol] = float(close)
    return prices


def _compute_eps_cagr_by_symbol(
    conn: Any,
    *,
    end_year: int,
    lookback_years: int,
) -> Dict[str, float]:
    start_year = int(end_year) - int(lookback_years)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT symbol, year, eps_vnd
            FROM financial_ratios
            WHERE quarter IS NULL
              AND year BETWEEN %s AND %s
              AND eps_vnd IS NOT NULL
              AND eps_vnd > 0
            ORDER BY symbol, year ASC
            """,
            (start_year, int(end_year)),
        )
        rows = cur.fetchall()

    series_by_symbol: Dict[str, List[Tuple[int, float]]] = {}
    for r in rows:
        symbol = str(r["symbol"] or "").strip().upper()
        year = int(r["year"]) if r["year"] is not None else None
        eps = _to_float(r["eps_vnd"])
        if not symbol or year is None or eps is None or eps <= 0:
            continue
        series_by_symbol.setdefault(symbol, []).append((year, eps))

    out: Dict[str, float] = {}
    for symbol, series in series_by_symbol.items():
        if len(series) < 2:
            continue
        first_year, first_eps = series[0]
        last_year, last_eps = series[-1]
        years_span = last_year - first_year
        if years_span <= 0 or first_eps <= 0 or last_eps <= 0:
            continue
        try:
            cagr = (last_eps / first_eps) ** (1.0 / float(years_span)) - 1.0
        except (OverflowError, ZeroDivisionError, ValueError):
            continue
        if cagr == cagr:  # not NaN
            out[symbol] = float(cagr)
    return out


@dataclass(frozen=True)
class _RankingRow:
    ticker: str
    name: Optional[str]
    industry: Optional[str]
    exchanges: Optional[str]
    pe: Optional[float]
    pb: Optional[float]
    ev_ebitda: Optional[float]
    eps_vnd: Optional[float]
    bvps_vnd: Optional[float]
    roe: Optional[float]
    net_margin: Optional[float]
    latest_price: Optional[float] = None


def _fetch_base_rows(conn: Any, *, year: int, latest_prices: Optional[Dict[str, float]] = None) -> List[_RankingRow]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                s.ticker AS ticker,
                s.organ_name AS organ_name,
                MAX(si.icb_name3) AS industry,
                STRING_AGG(DISTINCT se.exchange, ',') AS exchanges,
                fr.price_to_earnings AS pe,
                fr.price_to_book AS pb,
                fr.ev_to_ebitda AS ev_ebitda,
                fr.eps_vnd AS eps_vnd,
                fr.bvps_vnd AS bvps_vnd,
                fr.roe AS roe,
                fr.net_profit_margin AS net_profit_margin
            FROM stocks s
            LEFT JOIN stock_industry si ON si.ticker = s.ticker
            LEFT JOIN stock_exchange se ON se.ticker = s.ticker
            LEFT JOIN financial_ratios fr
                   ON fr.symbol = s.ticker AND fr.year = %s AND fr.quarter IS NULL
            WHERE LENGTH(s.ticker) = 3
              AND s.ticker ~ '^[A-Z]{3}$'
            GROUP BY s.ticker, s.organ_name, fr.price_to_earnings, fr.price_to_book,
                     fr.ev_to_ebitda, fr.eps_vnd, fr.bvps_vnd, fr.roe, fr.net_profit_margin
            ORDER BY s.ticker
            """,
            (int(year),),
        )
        raw_rows = cur.fetchall()

    rows: List[_RankingRow] = []
    latest_prices = latest_prices or {}

    for r in raw_rows:
        ticker = str(r["ticker"] or "").strip().upper()
        if not ticker:
            continue
        rows.append(
            _RankingRow(
                ticker=ticker,
                name=str(r["organ_name"]) if r["organ_name"] is not None else None,
                industry=str(r["industry"]).strip() if r["industry"] is not None else None,
                exchanges=str(r["exchanges"]).strip() if r["exchanges"] is not None else None,
                pe=_to_float(r["pe"]),
                pb=_to_float(r["pb"]),
                ev_ebitda=_to_float(r["ev_ebitda"]),
                eps_vnd=_to_float(r["eps_vnd"]),
                bvps_vnd=_to_float(r["bvps_vnd"]),
                roe=_to_float(r["roe"]),
                net_margin=_to_float(r["net_profit_margin"]),
                latest_price=latest_prices.get(ticker),
            )
        )
    return rows


def _build_peer_distributions(
    rows: List[_RankingRow],
    *,
    min_peers_for_industry: int = 10,
) -> Dict[str, Any]:
    pe_by_industry: Dict[str, List[float]] = {}
    pb_by_industry: Dict[str, List[float]] = {}
    ev_by_industry: Dict[str, List[float]] = {}

    pe_market: List[float] = []
    pb_market: List[float] = []
    ev_market: List[float] = []

    roe_market: List[float] = []
    margin_market: List[float] = []

    for row in rows:
        industry = (row.industry or "").strip()

        if row.roe is not None:
            roe_market.append(float(row.roe))
        if row.net_margin is not None:
            margin_market.append(float(row.net_margin))

        if row.pe is not None and row.pe > 0 and row.eps_vnd is not None and row.eps_vnd > 0:
            pe_market.append(float(row.pe))
            if industry:
                pe_by_industry.setdefault(industry, []).append(float(row.pe))

        if row.pb is not None and row.pb > 0 and row.bvps_vnd is not None and row.bvps_vnd > 0:
            pb_market.append(float(row.pb))
            if industry:
                pb_by_industry.setdefault(industry, []).append(float(row.pb))

        if row.ev_ebitda is not None and row.ev_ebitda > 0:
            ev_market.append(float(row.ev_ebitda))
            if industry:
                ev_by_industry.setdefault(industry, []).append(float(row.ev_ebitda))

    for d in (pe_by_industry, pb_by_industry, ev_by_industry):
        for k in list(d.keys()):
            d[k].sort()

    pe_market.sort()
    pb_market.sort()
    ev_market.sort()
    roe_market.sort()
    margin_market.sort()

    return {
        "min_peers_for_industry": int(min_peers_for_industry),
        "pe_by_industry": pe_by_industry,
        "pb_by_industry": pb_by_industry,
        "ev_by_industry": ev_by_industry,
        "pe_market": pe_market,
        "pb_market": pb_market,
        "ev_market": ev_market,
        "roe_market": roe_market,
        "margin_market": margin_market,
    }


def _pick_distribution(
    distributions: Dict[str, Any],
    industry: Optional[str],
    metric: Literal["pe", "pb", "ev"],
) -> Tuple[List[float], str]:
    industry = (industry or "").strip()
    min_peers = int(distributions.get("min_peers_for_industry", 10))

    by_industry_key = {"pe": "pe_by_industry", "pb": "pb_by_industry", "ev": "ev_by_industry"}[metric]
    market_key = {"pe": "pe_market", "pb": "pb_market", "ev": "ev_market"}[metric]

    by_industry: Dict[str, List[float]] = distributions.get(by_industry_key, {}) or {}
    market: List[float] = distributions.get(market_key, []) or []

    if industry and len(by_industry.get(industry, [])) >= min_peers:
        return by_industry[industry], "industry"
    return market, "market"


@lru_cache(maxsize=8)
def _compute_rankings_items_cached(
    cache_bucket: int,
    year: int,
    use_latest_prices_flag: bool = False,
) -> Tuple[Dict[str, Any], ...]:
    from .. import db
    with db.connect() as conn:
        latest_prices = None
        if use_latest_prices_flag:
            latest_prices = _get_latest_prices(conn)
        base_rows = _fetch_base_rows(conn, year=year, latest_prices=latest_prices)
        distributions = _build_peer_distributions(base_rows)
        eps_cagr_by_symbol = _compute_eps_cagr_by_symbol(conn, end_year=year, lookback_years=5)

    eps_cagr_values = sorted(eps_cagr_by_symbol.values())

    items: List[Dict[str, Any]] = []
    for row in base_rows:
        pe_pct = pb_pct = ev_pct = None
        pe_basis = pb_basis = ev_basis = "unknown"

        pe_latest = None
        pb_latest = None
        if latest_prices and row.latest_price is not None and row.latest_price > 0:
            if row.eps_vnd is not None and row.eps_vnd > 0:
                pe_latest = row.latest_price / row.eps_vnd
            if row.bvps_vnd is not None and row.bvps_vnd > 0:
                pb_latest = row.latest_price / row.bvps_vnd

        if pe_latest is not None and pe_latest > 0:
            dist, basis = _pick_distribution(distributions, row.industry, "pe")
            pe_pct = _percentile_rank(dist, pe_latest) if dist else None
            pe_basis = basis if pe_pct is not None else "unknown"
        elif row.pe is not None and row.pe > 0 and row.eps_vnd is not None and row.eps_vnd > 0:
            dist, basis = _pick_distribution(distributions, row.industry, "pe")
            pe_pct = _percentile_rank(dist, row.pe) if dist else None
            pe_basis = basis if pe_pct is not None else "unknown"

        if pb_latest is not None and pb_latest > 0:
            dist, basis = _pick_distribution(distributions, row.industry, "pb")
            pb_pct = _percentile_rank(dist, pb_latest) if dist else None
            pb_basis = basis if pb_pct is not None else "unknown"
        elif row.pb is not None and row.pb > 0 and row.bvps_vnd is not None and row.bvps_vnd > 0:
            dist, basis = _pick_distribution(distributions, row.industry, "pb")
            pb_pct = _percentile_rank(dist, row.pb) if dist else None
            pb_basis = basis if pb_pct is not None else "unknown"

        if row.ev_ebitda is not None and row.ev_ebitda > 0:
            dist, basis = _pick_distribution(distributions, row.industry, "ev")
            ev_pct = _percentile_rank(dist, row.ev_ebitda) if dist else None
            ev_basis = basis if ev_pct is not None else "unknown"

        pe_score = _score_from_percentile(pe_pct, invert=True)
        pb_score = _score_from_percentile(pb_pct, invert=True)
        ev_score = _score_from_percentile(ev_pct, invert=True)

        valuation_score = _weighted_mean([(pe_score, 0.40), (pb_score, 0.30), (ev_score, 0.30)])
        valuation_pct_avg = _weighted_mean([(pe_pct, 0.40), (pb_pct, 0.30), (ev_pct, 0.30)])
        valuation_band = _valuation_band(valuation_pct_avg)

        eps_cagr = eps_cagr_by_symbol.get(row.ticker)
        eps_cagr_pct = _percentile_rank(eps_cagr_values, eps_cagr) if eps_cagr_values else None
        eps_growth_score = _score_from_percentile(eps_cagr_pct)

        if eps_growth_score is None:
            growth_score = None
            growth_band = "unknown"
        else:
            roe_pct = _percentile_rank(distributions["roe_market"], row.roe) if distributions["roe_market"] else None
            margin_pct = _percentile_rank(distributions["margin_market"], row.net_margin) if distributions["margin_market"] else None
            roe_score = _score_from_percentile(roe_pct)
            margin_score = _score_from_percentile(margin_pct)
            growth_score = _weighted_mean([(eps_growth_score, 0.60), (roe_score, 0.20), (margin_score, 0.20)])
            growth_band = _growth_band(growth_score)

        overall_score = None
        if valuation_score is not None and growth_score is not None:
            overall_score = _weighted_mean([(valuation_score, 0.50), (growth_score, 0.50)])

        display_pe = pe_latest if pe_latest is not None else row.pe
        display_pb = pb_latest if pb_latest is not None else row.pb

        items.append({
            "ticker": row.ticker,
            "name": row.name,
            "industry": row.industry,
            "exchanges": row.exchanges,
            "scores": {
                "valuation": round(valuation_score, 2) if valuation_score is not None else None,
                "growth": round(growth_score, 2) if growth_score is not None else None,
                "overall": round(overall_score, 2) if overall_score is not None else None,
            },
            "valuation": {
                "band": valuation_band,
                "pe": round(display_pe, 2) if display_pe is not None else None,
                "pb": round(display_pb, 2) if display_pb is not None else None,
                "ev_ebitda": round(row.ev_ebitda, 2) if row.ev_ebitda is not None else None,
                "pe_percentile": round(pe_pct, 4) if pe_pct is not None else None,
                "pb_percentile": round(pb_pct, 4) if pb_pct is not None else None,
                "ev_percentile": round(ev_pct, 4) if ev_pct is not None else None,
                "pe_basis": pe_basis,
                "pb_basis": pb_basis,
                "ev_basis": ev_basis,
            },
            "growth": {
                "band": growth_band,
                "eps_cagr_5y": round(eps_cagr, 6) if eps_cagr is not None else None,
                "roe": round(row.roe, 6) if row.roe is not None else None,
                "net_margin": round(row.net_margin, 6) if row.net_margin is not None else None,
            },
        })

    return tuple(items)


def get_stock_rankings(
    *,
    db_path: Optional[Path] = None,  # kept for backwards-compat, ignored
    year: Optional[int] = None,
    sort_by: RankingSort = "overall",
    limit: int = 50,
    industry: Optional[str] = None,
    exchange: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a "valuation vs growth" ranking table using Supabase PostgreSQL.
    """
    from .. import db as _db
    with _db.connect() as conn:
        requested_year = int(year) if year is not None else _suggest_default_year(conn)
        if requested_year is None:
            return {"error": "No annual financial_ratios data found."}
        financial_year, use_latest_prices = _resolve_financial_year_for_rankings(conn, requested_year)

    bucket = _cache_bucket(300)
    all_items = list(_compute_rankings_items_cached(bucket, int(financial_year), use_latest_prices_flag=use_latest_prices))

    industry_filter = (industry or "").strip()
    if industry_filter:
        all_items = [it for it in all_items if (it.get("industry") or "").strip() == industry_filter]

    exchange_filter = (exchange or "").strip()
    if exchange_filter:
        all_items = [it for it in all_items if exchange_filter.upper() in (it.get("exchanges") or "").upper()]

    def is_eligible(item: Dict[str, Any]) -> bool:
        scores = item.get("scores") or {}
        if sort_by == "valuation":
            return scores.get("valuation") is not None
        if sort_by == "growth":
            return scores.get("growth") is not None
        return scores.get("overall") is not None

    eligible_items = [it for it in all_items if is_eligible(it)]
    sort_key = {"overall": "overall", "valuation": "valuation", "growth": "growth"}[sort_by]
    eligible_items.sort(key=lambda it: (it.get("scores") or {}).get(sort_key) or -1e18, reverse=True)

    limit = max(1, min(500, int(limit)))
    top = eligible_items[:limit]

    for i, it in enumerate(top, start=1):
        it["rank"] = i

    return {
        "year": int(requested_year),
        "used_latest_price": use_latest_prices,
        "sort_by": sort_by,
        "filters": {
            "industry": industry_filter or None,
            "exchange": exchange_filter or None,
        },
        "counts": {
            "universe": len(all_items),
            "eligible": len(eligible_items),
            "returned": len(top),
        },
        "items": top,
        "notes": [
            "Valuation score uses industry percentiles when possible; otherwise falls back to market percentiles.",
            "Growth score requires EPS CAGR (5y) and is combined with ROE + net profit margin.",
            "This ranking is for research/education; not investment advice.",
        ],
    }
