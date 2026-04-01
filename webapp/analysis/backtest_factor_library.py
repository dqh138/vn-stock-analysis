"""
Factor Backtest (P2) — investable, audit-friendly research under data limits.

Adds on top of `backtest_harness.py`:
  - Cash-dividend-adjusted "total return" (partial total return)
  - Liquidity + price-staleness constraints (formation-year, look-ahead safe)
  - Transaction cost model via turnover approximation
  - Factor library (quality, value, momentum, low-vol, quality+value)
  - IC/IR, regime (bull/bear, vol), and industry attribution

Key data limits (explicit):
  - Only cash dividends from `events` (DIV). No split/bonus/rights adjustments.
  - Price `close` appears in *thousand VND* (scale configurable).
  - No publication dates for fundamentals → look-ahead control uses signal_year = hold_year - 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd
import sqlite3

from .return_engine import (
    DEFAULT_CLOSE_SCALE_VND,
    attach_cash_dividends_to_returns,
    compute_year_price_stats,
    query_cash_dividends_year,
    query_price_history_year,
)

ReturnMode = Literal["price", "total_return_cash_div"]
SignalRobustMethod = Literal["none", "winsorize", "mad_clip"]
PortfolioAggMethod = Literal["mean", "median", "trimmed_mean"]
SelectionMethod = Literal["top_n", "industry_cap"]


@dataclass(frozen=True)
class InvestabilityFilters:
    min_trading_days: int = 120
    max_start_gap_days: int = 10
    max_end_gap_days: int = 10
    min_avg_dollar_volume_vnd: Optional[float] = 200_000_000.0  # 200m VND/day (approx; unit depends on close_scale)
    max_zero_volume_frac: float = 0.05
    max_stale_close_frac: float = 0.20


@dataclass(frozen=True)
class TransactionCostModel:
    enabled: bool = True
    cost_bps_per_side: float = 10.0  # 10 bps per side (0.10%)


@dataclass(frozen=True)
class SignalRobustness:
    """
    Robustness options for cross-sectional signal inputs.

    - winsorize: clip to [p, 100-p] percentile.
    - mad_clip: drop (set NaN) values with |robust_z| > mad_z using median/MAD.
    """

    method: SignalRobustMethod = "none"
    winsorize_pct: float = 1.0
    mad_z: float = 6.0


@dataclass(frozen=True)
class PortfolioAggregation:
    method: PortfolioAggMethod = "mean"
    trimmed_mean_pct: float = 0.10


@dataclass(frozen=True)
class SelectionConstraints:
    method: SelectionMethod = "top_n"
    industry_max_weight: float = 0.30


@dataclass(frozen=True)
class FactorBacktestConfig:
    start_hold_year: int
    end_hold_year: int
    formation_lag_years: int = 1
    top_n: int = 30
    benchmark_symbol: Optional[str] = "VNINDEX"
    return_mode: ReturnMode = "total_return_cash_div"
    min_signal_coverage: int = 3
    close_scale_vnd: float = DEFAULT_CLOSE_SCALE_VND
    signal_robustness: SignalRobustness = SignalRobustness()
    portfolio_aggregation: PortfolioAggregation = PortfolioAggregation()
    selection_constraints: SelectionConstraints = SelectionConstraints()
    investability_signal_year: InvestabilityFilters = InvestabilityFilters()
    # Hold-year filters should avoid look-ahead where possible. Default only enforces
    # basic return-quality constraints (enough trading days + not-too-stale year endpoints),
    # and does NOT filter by hold-year liquidity/staleness fractions.
    investability_hold_year: InvestabilityFilters = InvestabilityFilters(
        min_trading_days=120,
        max_start_gap_days=10,
        max_end_gap_days=10,
        min_avg_dollar_volume_vnd=None,
        max_zero_volume_frac=1.0,
        max_stale_close_frac=1.0,
    )
    transaction_costs: TransactionCostModel = TransactionCostModel()
    min_universe_for_ic: int = 50


@dataclass(frozen=True)
class FactorSpec:
    id: str
    label: str
    description: str
    components: Tuple[Tuple[str, Literal["higher", "lower"], Optional[str]], ...]
    # component tuple: (column, direction, validity_rule_id)


DEFAULT_FACTOR_LIBRARY: Tuple[FactorSpec, ...] = (
    FactorSpec(
        id="quality_value",
        label="Quality + Value",
        description="Composite rank: ROE↑, Net margin↑, D/E↓, P/E↓, P/B↓.",
        components=(
            ("roe", "higher", None),
            ("net_profit_margin", "higher", None),
            ("debt_to_equity", "lower", "positive_only"),
            ("price_to_earnings", "lower", "positive_only"),
            ("price_to_book", "lower", "positive_only"),
        ),
    ),
    FactorSpec(
        id="quality",
        label="Quality",
        description="Composite rank: ROE↑, Net margin↑, Interest coverage↑, D/E↓.",
        components=(
            ("roe", "higher", None),
            ("net_profit_margin", "higher", None),
            ("interest_coverage_ratio", "higher", "positive_only"),
            ("debt_to_equity", "lower", "positive_only"),
        ),
    ),
    FactorSpec(
        id="value",
        label="Value",
        description="Composite rank: P/E↓, P/B↓, EV/EBITDA↓ (valid only when >0).",
        components=(
            ("price_to_earnings", "lower", "positive_only"),
            ("price_to_book", "lower", "positive_only"),
            ("ev_to_ebitda", "lower", "positive_only"),
        ),
    ),
    FactorSpec(
        id="momentum",
        label="Momentum (12m proxy)",
        description="Formation-year price return↑ as a simple momentum proxy under data limits.",
        components=(("price_return_signal", "higher", None),),
    ),
    FactorSpec(
        id="low_vol",
        label="Low Volatility",
        description="Formation-year annualized volatility↓ (log returns).",
        components=(("vol_annualized_signal", "lower", "positive_only"),),
    ),
)


def _spearman_rank_correlation(x: Iterable[float], y: Iterable[float]) -> Optional[float]:
    xs = pd.Series(list(x), dtype="float64")
    ys = pd.Series(list(y), dtype="float64")
    mask = xs.notna() & ys.notna()
    xs = xs[mask]
    ys = ys[mask]
    if len(xs) < 3:
        return None
    rx = xs.rank(method="average")
    ry = ys.rank(method="average")
    corr = np.corrcoef(rx.to_numpy(), ry.to_numpy())[0, 1]
    if np.isnan(corr):
        return None
    return float(corr)


def _max_drawdown(yearly_returns: List[float]) -> Optional[float]:
    if not yearly_returns:
        return None
    curve = np.cumprod(1.0 + np.asarray(yearly_returns, dtype="float64"))
    if len(curve) < 2:
        return 0.0
    peak = np.maximum.accumulate(curve)
    dd = curve / peak - 1.0
    return float(np.min(dd))


def _query_annual_ratios(conn: sqlite3.Connection, year: int) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT
          symbol,
          year,
          roe,
          net_profit_margin,
          debt_to_equity,
          interest_coverage_ratio,
          price_to_earnings,
          price_to_book,
          ev_to_ebitda,
          market_cap_billions
        FROM financial_ratios
        WHERE quarter IS NULL
          AND year = ?
        """,
        conn,
        params=(int(year),),
    )
    if not df.empty:
        df["symbol"] = df["symbol"].astype(str)
    return df


def _query_symbol_industries(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT ticker AS symbol, icb_name3, icb_code3
        FROM stock_industry
        """,
        conn,
    )
    if not df.empty:
        df["symbol"] = df["symbol"].astype(str)
    return df


def _apply_validity_rule(series: pd.Series, rule_id: Optional[str]) -> pd.Series:
    if rule_id is None:
        return series
    if rule_id == "positive_only":
        out = series.copy()
        out.loc[out <= 0] = np.nan
        return out
    return series


def _winsorize_series(series: pd.Series, pct: float) -> pd.Series:
    pct = float(pct)
    if pct <= 0:
        return series
    s = pd.to_numeric(series, errors="coerce")
    vals = s.dropna()
    if len(vals) < 20:
        return s
    lo = float(vals.quantile(pct / 100.0))
    hi = float(vals.quantile(1.0 - pct / 100.0))
    return s.clip(lower=lo, upper=hi)


def _mad_clip_series(series: pd.Series, z: float) -> pd.Series:
    z = float(z)
    if z <= 0:
        return series
    s = pd.to_numeric(series, errors="coerce")
    vals = s.dropna()
    if len(vals) < 20:
        return s
    med = float(np.median(vals.to_numpy(dtype="float64", copy=False)))
    mad = float(np.median(np.abs(vals.to_numpy(dtype="float64", copy=False) - med)))
    if mad <= 0:
        return s
    # Robust z-score using median/MAD (0.6745 factor matches std under normality).
    rz = 0.6745 * (s.astype("float64") - med) / mad
    out = s.copy()
    out.loc[rz.abs() > z] = np.nan
    return out


def _apply_signal_robustness(series: pd.Series, robustness: SignalRobustness) -> pd.Series:
    if robustness is None or robustness.method == "none":
        return series
    if robustness.method == "winsorize":
        return _winsorize_series(series, robustness.winsorize_pct)
    if robustness.method == "mad_clip":
        return _mad_clip_series(series, robustness.mad_z)
    return series


def _compute_composite_signal(
    df: pd.DataFrame,
    spec: FactorSpec,
    *,
    min_coverage: int,
    robustness: SignalRobustness,
) -> pd.DataFrame:
    working = df.copy()
    components: List[pd.Series] = []
    used_cols: List[str] = []

    for col, direction, validity in spec.components:
        if col not in working.columns:
            continue
        s = pd.to_numeric(working[col], errors="coerce")
        s = _apply_validity_rule(s, validity)
        s = _apply_signal_robustness(s, robustness)
        ascending = True if direction == "higher" else False
        components.append(s.rank(pct=True, ascending=ascending))
        used_cols.append(col)

    if not components:
        working["signal"] = np.nan
        working["signal_coverage"] = 0
        working["signal_used_components"] = ""
        return working

    comp_df = pd.concat(components, axis=1)
    working["signal_coverage"] = comp_df.notna().sum(axis=1).astype(int)
    working["signal"] = comp_df.mean(axis=1, skipna=True)
    working["signal_used_components"] = ",".join(used_cols)

    working.loc[working["signal_coverage"] < int(min_coverage), "signal"] = np.nan
    return working


def _apply_investability_filters(df: pd.DataFrame, filters: InvestabilityFilters, *, prefix: str) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Apply investability filters to a DataFrame that contains columns from year stats.

    prefix: "" for hold year, or "_signal" for signal-year stats (e.g. avg_dollar_volume_vnd_signal).
    """
    drop: Dict[str, int] = {}
    out = df.copy()

    def _mask(col: str) -> pd.Series:
        if col not in out.columns:
            return pd.Series([True] * len(out), index=out.index)
        return out[col].notna()

    # Trading days
    col_td = f"trading_days{prefix}"
    if col_td in out.columns:
        before = len(out)
        out = out.loc[_mask(col_td) & (out[col_td] >= int(filters.min_trading_days))]
        drop["min_trading_days"] = before - len(out)

    # Start/end gaps (IPO / stale end)
    col_sg = f"start_gap_days{prefix}"
    if col_sg in out.columns:
        before = len(out)
        out = out.loc[_mask(col_sg) & (out[col_sg] <= int(filters.max_start_gap_days))]
        drop["max_start_gap_days"] = before - len(out)

    col_eg = f"end_gap_days{prefix}"
    if col_eg in out.columns:
        before = len(out)
        out = out.loc[_mask(col_eg) & (out[col_eg] <= int(filters.max_end_gap_days))]
        drop["max_end_gap_days"] = before - len(out)

    # Liquidity
    if filters.min_avg_dollar_volume_vnd is not None:
        col_adv = f"avg_dollar_volume_vnd{prefix}"
        if col_adv in out.columns:
            before = len(out)
            out = out.loc[_mask(col_adv) & (out[col_adv] >= float(filters.min_avg_dollar_volume_vnd))]
            drop["min_avg_dollar_volume_vnd"] = before - len(out)

    col_zv = f"zero_volume_frac{prefix}"
    if col_zv in out.columns:
        before = len(out)
        out = out.loc[_mask(col_zv) & (out[col_zv] <= float(filters.max_zero_volume_frac))]
        drop["max_zero_volume_frac"] = before - len(out)

    col_sc = f"stale_close_frac{prefix}"
    if col_sc in out.columns:
        before = len(out)
        out = out.loc[_mask(col_sc) & (out[col_sc] <= float(filters.max_stale_close_frac))]
        drop["max_stale_close_frac"] = before - len(out)

    return out, drop


def _compute_turnover(prev: Optional[List[str]], curr: List[str]) -> Tuple[Optional[float], Optional[int]]:
    if not curr:
        return None, None
    if prev is None:
        return 1.0, 0
    prev_set = set(prev)
    curr_set = set(curr)
    overlap = len(prev_set & curr_set)
    n = len(curr_set)
    if n == 0:
        return None, None
    turnover_one_way = 1.0 - overlap / n
    return float(turnover_one_way), int(overlap)


def _apply_transaction_cost(portfolio_return: Optional[float], turnover_one_way: Optional[float], model: TransactionCostModel) -> Tuple[Optional[float], Optional[float]]:
    if portfolio_return is None or turnover_one_way is None:
        return portfolio_return, None
    if not model.enabled:
        return portfolio_return, 0.0
    c = float(model.cost_bps_per_side) / 10_000.0
    # Initial year: turnover=1.0 means "buy from cash"; only buy side cost
    if turnover_one_way >= 0.999:
        cost = c * 1.0
    else:
        cost = c * 2.0 * float(turnover_one_way)
    return float(portfolio_return - cost), float(cost)


def _aggregate_portfolio_return(returns: pd.Series, agg: PortfolioAggregation) -> Optional[float]:
    s = pd.to_numeric(returns, errors="coerce").dropna()
    if s.empty:
        return None

    if agg is None or agg.method == "mean":
        return float(s.mean())
    if agg.method == "median":
        return float(s.median())
    if agg.method == "trimmed_mean":
        vals = np.sort(s.to_numpy(dtype="float64", copy=False))
        n = int(len(vals))
        trim = max(0, int(np.floor(float(agg.trimmed_mean_pct) * n)))
        if 2 * trim >= n:
            return float(np.mean(vals))
        trimmed = vals[trim : n - trim]
        return float(np.mean(trimmed)) if len(trimmed) else None
    return float(s.mean())


def _select_portfolio(
    merged: pd.DataFrame,
    *,
    top_n: int,
    constraints: SelectionConstraints,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Select a portfolio from a merged universe sorted by signal descending.

    Returns:
        selected_df, meta
    """
    if merged.empty:
        return merged, {"method": "none", "selected_n": 0}

    sorted_df = merged.sort_values("signal", ascending=False)
    top_n = int(top_n)
    if top_n <= 0:
        return sorted_df.head(0), {"method": "none", "selected_n": 0}

    if constraints is None or constraints.method == "top_n":
        sel = sorted_df.head(top_n)
        return sel, {"method": "top_n", "selected_n": int(len(sel))}

    if constraints.method == "industry_cap":
        cap = float(constraints.industry_max_weight)
        cap = max(0.05, min(1.0, cap))
        max_per_industry = max(1, int(np.floor(cap * top_n)))

        selected_idx: List[Any] = []
        counts: Dict[str, int] = {}

        for idx, row in sorted_df.iterrows():
            industry = "Unknown"
            if "icb_name3" in sorted_df.columns:
                v = row.get("icb_name3")
                if v is not None and str(v).strip():
                    industry = str(v)
            if counts.get(industry, 0) >= max_per_industry:
                continue
            selected_idx.append(idx)
            counts[industry] = counts.get(industry, 0) + 1
            if len(selected_idx) >= top_n:
                break

        selected = sorted_df.loc[selected_idx] if selected_idx else sorted_df.head(0)

        relaxed = False
        relaxed_fill_n = 0
        if len(selected) < top_n:
            relaxed = True
            remaining = sorted_df.drop(index=selected_idx, errors="ignore")
            fill = remaining.head(top_n - len(selected))
            relaxed_fill_n = int(len(fill))
            selected = pd.concat([selected, fill], axis=0)

        # Ensure deterministic order
        selected = selected.sort_values("signal", ascending=False).head(top_n)

        return selected, {
            "method": "industry_cap",
            "industry_max_weight": cap,
            "max_per_industry": max_per_industry,
            "cap_relaxed": relaxed,
            "cap_relaxed_fill_n": relaxed_fill_n,
            "selected_n": int(len(selected)),
        }

    # Fallback
    sel = sorted_df.head(top_n)
    return sel, {"method": "top_n", "selected_n": int(len(sel))}


def _industry_concentration(selected: pd.DataFrame) -> Dict[str, Any]:
    if selected.empty or "icb_name3" not in selected.columns:
        return {"industry_count": 0, "max_weight": None, "hhi": None}
    counts = selected["icb_name3"].fillna("Unknown").astype(str).value_counts(dropna=False)
    n = int(len(selected))
    if n <= 0:
        return {"industry_count": 0, "max_weight": None, "hhi": None}
    weights = (counts / float(n)).to_numpy(dtype="float64", copy=False)
    hhi = float(np.sum(weights**2)) if len(weights) else None
    max_w = float(np.max(weights)) if len(weights) else None
    return {"industry_count": int(len(counts)), "max_weight": max_w, "hhi": hhi}


def _summarize_performance(yearly_returns: List[float]) -> Dict[str, Any]:
    rets = np.asarray(yearly_returns, dtype="float64")
    years = int(len(rets))
    mean_ret = float(np.mean(rets)) if years else None
    vol = float(np.std(rets, ddof=1)) if years >= 2 else None
    sharpe = float(mean_ret / vol) if (mean_ret is not None and vol is not None and vol > 0) else None
    cagr = None
    if years >= 2:
        cagr = float(np.prod(1.0 + rets) ** (1.0 / years) - 1.0)
    mdd = _max_drawdown(list(rets)) if years else None
    return {"years": years, "mean_return": mean_ret, "volatility": vol, "sharpe": sharpe, "cagr": cagr, "max_drawdown": mdd}


def _summarize_active_vs_benchmark(port: List[Optional[float]], bench: List[Optional[float]]) -> Dict[str, Any]:
    aligned = [(p, b) for p, b in zip(port, bench) if p is not None and b is not None]
    if not aligned:
        return {
            "n_years": 0,
            "mean_active": None,
            "tracking_error": None,
            "information_ratio": None,
            "alpha": None,
            "beta": None,
            "corr": None,
        }

    ps = np.asarray([p for p, _ in aligned], dtype="float64")
    bs = np.asarray([b for _, b in aligned], dtype="float64")
    active = ps - bs

    mean_active = float(np.mean(active))
    te = float(np.std(active, ddof=1)) if len(active) >= 2 else None
    ir = float(mean_active / te) if (te is not None and te > 0) else None

    beta = None
    alpha = None
    corr = None
    if len(ps) >= 2 and float(np.var(bs, ddof=1)) > 0:
        cov = float(np.cov(ps, bs, ddof=1)[0, 1])
        var_b = float(np.var(bs, ddof=1))
        beta = cov / var_b
        alpha = float(np.mean(ps) - beta * np.mean(bs))
        corr = float(np.corrcoef(ps, bs)[0, 1])

    return {
        "n_years": int(len(active)),
        "mean_active": mean_active,
        "tracking_error": te,
        "information_ratio": ir,
        "alpha": alpha,
        "beta": beta,
        "corr": corr,
    }


def _summarize_ic(ic_values: List[float]) -> Dict[str, Any]:
    if not ic_values:
        return {"ic_mean": None, "ic_std": None, "ic_ir": None, "ic_t_stat": None, "n_years": 0}
    vals = np.asarray(ic_values, dtype="float64")
    mean = float(np.mean(vals))
    std = float(np.std(vals, ddof=1)) if len(vals) >= 2 else None
    ir = float(mean / std) if (std is not None and std > 0) else None
    t_stat = float(mean / (std / np.sqrt(len(vals)))) if (std is not None and std > 0 and len(vals) >= 2) else None
    return {"ic_mean": mean, "ic_std": std, "ic_ir": ir, "ic_t_stat": t_stat, "n_years": int(len(vals))}


def _classify_regime(benchmark_return: Optional[float], benchmark_vol: Optional[float], *, vol_threshold: Optional[float]) -> Dict[str, Optional[str]]:
    market = None
    if benchmark_return is not None:
        market = "BULL" if benchmark_return > 0 else "BEAR"
    vol_regime = None
    if benchmark_vol is not None and vol_threshold is not None:
        vol_regime = "HIGH_VOL" if benchmark_vol >= vol_threshold else "LOW_VOL"
    return {"market": market, "volatility": vol_regime}


def _stress_summaries(yearly_rows: List[Dict[str, Any]], *, k: int = 2) -> Dict[str, Any]:
    """
    Very small, audit-friendly stress summaries using benchmark as the proxy.
    """
    rows = [r for r in yearly_rows if r.get("benchmark_return") is not None and r.get("portfolio_return_net") is not None]
    if not rows:
        return {"worst_benchmark_years": [], "best_benchmark_years": [], "high_vol_years": []}

    worst = sorted(rows, key=lambda r: float(r["benchmark_return"]))[:k]
    best = sorted(rows, key=lambda r: float(r["benchmark_return"]), reverse=True)[:k]

    rows_vol = [r for r in rows if r.get("benchmark_vol_annualized") is not None]
    high_vol = sorted(rows_vol, key=lambda r: float(r["benchmark_vol_annualized"]), reverse=True)[:k] if rows_vol else []

    def pack(rs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "hold_year": int(r["hold_year"]),
                "benchmark_return": float(r["benchmark_return"]),
                "portfolio_return_net": float(r["portfolio_return_net"]),
                "benchmark_vol_annualized": (float(r["benchmark_vol_annualized"]) if r.get("benchmark_vol_annualized") is not None else None),
            }
            for r in rs
        ]

    return {"worst_benchmark_years": pack(worst), "best_benchmark_years": pack(best), "high_vol_years": pack(high_vol)}


def _leave_one_year_out(hold_years: List[int], returns: List[Optional[float]]) -> List[Dict[str, Any]]:
    available = [(int(y), float(r)) for y, r in zip(hold_years, returns) if r is not None]
    if len(available) < 3:
        return []
    out: List[Dict[str, Any]] = []
    for y_excl, _ in available:
        rets = [r for y, r in available if y != y_excl]
        out.append({"excluded_year": y_excl, "summary": _summarize_performance(rets)})
    return out


def _rolling_windows(hold_years: List[int], returns: List[Optional[float]], *, window: int = 3) -> List[Dict[str, Any]]:
    window = int(window)
    if window < 2:
        return []
    series = {int(y): float(r) for y, r in zip(hold_years, returns) if r is not None}
    if len(series) < window:
        return []

    years_sorted = sorted(series.keys())
    out: List[Dict[str, Any]] = []
    for start in years_sorted:
        ys = [start + i for i in range(window)]
        if any(y not in series for y in ys):
            continue
        rets = [series[y] for y in ys]
        out.append({"start_year": start, "end_year": start + window - 1, "summary": _summarize_performance(rets)})
    return out


@dataclass(frozen=True)
class PreparedFactorBacktestData:
    industries_df: pd.DataFrame
    ratios_by_year: Dict[int, pd.DataFrame]
    price_stats_by_year: Dict[int, pd.DataFrame]
    returns_by_year: Dict[int, pd.DataFrame]
    vol_threshold: Optional[float]
    close_scale_vnd: float
    benchmark_symbol: Optional[str]


def prepare_factor_backtest_data(
    db_path: Path,
    *,
    start_hold_year: int,
    end_hold_year: int,
    close_scale_vnd: float,
    benchmark_symbol: Optional[str],
    max_formation_lag_years: int = 2,
) -> PreparedFactorBacktestData:
    """
    Precompute yearly aggregates once for multi-run robustness/sensitivity experiments.
    """
    db_path = Path(db_path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    start_hold_year = int(start_hold_year)
    end_hold_year = int(end_hold_year)
    max_formation_lag_years = max(1, int(max_formation_lag_years))

    hold_years = list(range(start_hold_year, end_hold_year + 1))
    formation_years = list(range(start_hold_year - max_formation_lag_years, end_hold_year - max_formation_lag_years + 1))
    years_for_price_stats = sorted(set(hold_years + formation_years))

    ratios_by_year: Dict[int, pd.DataFrame] = {}
    price_stats_by_year: Dict[int, pd.DataFrame] = {}
    returns_by_year: Dict[int, pd.DataFrame] = {}

    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        industries_df = _query_symbol_industries(conn)

        for y in formation_years:
            ratios_by_year[int(y)] = _query_annual_ratios(conn, int(y))

        for y in years_for_price_stats:
            yp = query_price_history_year(conn, int(y))
            price_stats_by_year[int(y)] = compute_year_price_stats(yp, year=int(y), close_scale_vnd=float(close_scale_vnd))

        for y in hold_years:
            div = query_cash_dividends_year(conn, int(y))
            ps = price_stats_by_year.get(int(y), pd.DataFrame())
            returns_by_year[int(y)] = attach_cash_dividends_to_returns(ps, div, close_scale_vnd=float(close_scale_vnd))

    bench_vols: List[float] = []
    if benchmark_symbol:
        for y in hold_years:
            r = returns_by_year.get(int(y), pd.DataFrame())
            if r.empty:
                continue
            b = r.loc[r["symbol"] == str(benchmark_symbol)]
            if not b.empty and b["vol_annualized"].notna().any():
                bench_vols.append(float(b["vol_annualized"].iloc[0]))
    vol_threshold = float(np.median(bench_vols)) if bench_vols else None

    return PreparedFactorBacktestData(
        industries_df=industries_df,
        ratios_by_year=ratios_by_year,
        price_stats_by_year=price_stats_by_year,
        returns_by_year=returns_by_year,
        vol_threshold=vol_threshold,
        close_scale_vnd=float(close_scale_vnd),
        benchmark_symbol=benchmark_symbol,
    )


def _run_factor_library_backtest_core(
    *,
    config: FactorBacktestConfig,
    factor_library: Tuple[FactorSpec, ...],
    industries_df: pd.DataFrame,
    get_ratios: Callable[[int], pd.DataFrame],
    get_price_stats: Callable[[int], pd.DataFrame],
    get_returns: Callable[[int], pd.DataFrame],
    vol_threshold: Optional[float],
    include_yearly: bool = True,
) -> Dict[str, Any]:
    strategy_reports: Dict[str, Any] = {}

    for spec in factor_library:
        yearly_rows: List[Dict[str, Any]] = []
        prev_selected: Optional[List[str]] = None
        ic_vals: List[float] = []
        gross_returns: List[float] = []
        net_returns: List[float] = []
        bench_returns: List[Optional[float]] = []
        gross_yearly: List[Optional[float]] = []
        net_yearly: List[Optional[float]] = []

        for hold_year in range(int(config.start_hold_year), int(config.end_hold_year) + 1):
            formation_year = hold_year - int(config.formation_lag_years)

            fundamentals = get_ratios(int(formation_year))
            if fundamentals is None or fundamentals.empty:
                yearly_rows.append(
                    {
                        "formation_year": formation_year,
                        "hold_year": hold_year,
                        "universe_n": 0,
                        "selected_n": 0,
                        "portfolio_return_gross": None,
                        "portfolio_return_net": None,
                        "transaction_cost": None,
                        "turnover_one_way": None,
                        "overlap_n": None,
                        "benchmark_return": None,
                        "benchmark_vol_annualized": None,
                        "ic_spearman": None,
                        "drops": {"no_fundamentals": 0},
                        "regime": {"market": None, "volatility": None},
                        "industry": {"selected_weights": {}, "selected_n": 0, "concentration": {"industry_count": 0, "max_weight": None, "hhi": None}},
                        "selection": {"method": "none", "selected_n": 0},
                    }
                )
                prev_selected = None
                bench_returns.append(None)
                gross_yearly.append(None)
                net_yearly.append(None)
                continue

            ps_signal = get_price_stats(int(formation_year))
            ps_signal = ps_signal.rename(
                columns={
                    "price_return": "price_return_signal",
                    "vol_annualized": "vol_annualized_signal",
                    "trading_days": "trading_days_signal",
                    "avg_dollar_volume_vnd": "avg_dollar_volume_vnd_signal",
                    "zero_volume_frac": "zero_volume_frac_signal",
                    "stale_close_frac": "stale_close_frac_signal",
                    "start_gap_days": "start_gap_days_signal",
                    "end_gap_days": "end_gap_days_signal",
                }
            )

            base = fundamentals.merge(ps_signal, on=["symbol"], how="inner")
            base = base.merge(industries_df, on="symbol", how="left")
            base_filt, drops_signal = _apply_investability_filters(base, config.investability_signal_year, prefix="_signal")

            with_signal = _compute_composite_signal(
                base_filt,
                spec,
                min_coverage=config.min_signal_coverage,
                robustness=config.signal_robustness,
            ).dropna(subset=["signal"])

            r_hold = get_returns(int(hold_year))
            ret_col = "total_return" if config.return_mode == "total_return_cash_div" else "price_return"

            return_cols = [
                "symbol",
                ret_col,
                "price_return",
                "total_return",
                "cash_dividend_vnd",
                "dividend_events",
                "vol_annualized",
                "trading_days",
                "avg_dollar_volume_vnd",
                "zero_volume_frac",
                "stale_close_frac",
                "start_gap_days",
                "end_gap_days",
            ]
            return_cols_unique: List[str] = []
            for c in return_cols:
                if c not in return_cols_unique:
                    return_cols_unique.append(c)

            merged = with_signal.merge(r_hold[return_cols_unique], on="symbol", how="inner")
            merged["ret"] = pd.to_numeric(merged.get(ret_col), errors="coerce")

            merged, drops_hold = _apply_investability_filters(merged, config.investability_hold_year, prefix="")
            merged = merged.dropna(subset=["ret"])

            universe_n = int(len(merged))

            benchmark_return = None
            benchmark_vol = None
            if config.benchmark_symbol:
                bench_row = r_hold.loc[r_hold["symbol"] == str(config.benchmark_symbol)]
                if not bench_row.empty:
                    if bench_row["price_return"].notna().any():
                        benchmark_return = float(bench_row["price_return"].iloc[0])
                    if bench_row["vol_annualized"].notna().any():
                        benchmark_vol = float(bench_row["vol_annualized"].iloc[0])
            bench_returns.append(benchmark_return)

            if universe_n == 0:
                yearly_rows.append(
                    {
                        "formation_year": formation_year,
                        "hold_year": hold_year,
                        "universe_n": 0,
                        "selected_n": 0,
                        "portfolio_return_gross": None,
                        "portfolio_return_net": None,
                        "transaction_cost": None,
                        "turnover_one_way": None,
                        "overlap_n": None,
                        "benchmark_return": benchmark_return,
                        "benchmark_vol_annualized": benchmark_vol,
                        "ic_spearman": None,
                        "ic_by_industry": {},
                        "selection": {"method": "none", "selected_n": 0},
                        "drops": {"signal_year": drops_signal, "hold_year": drops_hold},
                        "regime": _classify_regime(benchmark_return, benchmark_vol, vol_threshold=vol_threshold),
                        "industry": {"selected_weights": {}, "selected_n": 0, "concentration": {"industry_count": 0, "max_weight": None, "hhi": None}},
                    }
                )
                prev_selected = None
                gross_yearly.append(None)
                net_yearly.append(None)
                continue

            selected, selection_meta = _select_portfolio(
                merged,
                top_n=int(config.top_n),
                constraints=config.selection_constraints,
            )
            selected_symbols = selected["symbol"].astype(str).tolist()

            portfolio_ret = _aggregate_portfolio_return(selected["ret"], config.portfolio_aggregation) if len(selected) else None
            ic = _spearman_rank_correlation(merged["signal"], merged["ret"]) if universe_n >= int(config.min_universe_for_ic) else None
            if ic is not None:
                ic_vals.append(ic)

            turnover_one_way, overlap_n = _compute_turnover(prev_selected, selected_symbols)
            ret_net, cost = _apply_transaction_cost(portfolio_ret, turnover_one_way, config.transaction_costs)

            if portfolio_ret is not None:
                gross_returns.append(portfolio_ret)
            gross_yearly.append(portfolio_ret)
            if ret_net is not None:
                net_returns.append(ret_net)
            net_yearly.append(ret_net)

            weights: Dict[str, float] = {}
            if "icb_name3" in selected.columns:
                counts = selected["icb_name3"].fillna("Unknown").value_counts(dropna=False)
                for k, v in counts.to_dict().items():
                    weights[str(k)] = float(v) / float(len(selected)) if len(selected) else 0.0
            conc = _industry_concentration(selected)

            ic_by_industry: Dict[str, float] = {}
            if "icb_name3" in merged.columns and universe_n >= int(config.min_universe_for_ic):
                for name, g in merged.groupby(merged["icb_name3"].fillna("Unknown")):
                    if len(g) < 30:
                        continue
                    ic_g = _spearman_rank_correlation(g["signal"], g["ret"])
                    if ic_g is not None:
                        ic_by_industry[str(name)] = float(ic_g)

            yearly_rows.append(
                {
                    "formation_year": formation_year,
                    "hold_year": hold_year,
                    "universe_n": universe_n,
                    "selected_n": int(len(selected)),
                    "portfolio_return_gross": portfolio_ret,
                    "portfolio_return_net": ret_net,
                    "transaction_cost": cost,
                    "turnover_one_way": turnover_one_way,
                    "overlap_n": overlap_n,
                    "benchmark_return": benchmark_return,
                    "benchmark_vol_annualized": benchmark_vol,
                    "ic_spearman": ic,
                    "ic_by_industry": ic_by_industry,
                    "selection": selection_meta,
                    "drops": {"signal_year": drops_signal, "hold_year": drops_hold},
                    "regime": _classify_regime(benchmark_return, benchmark_vol, vol_threshold=vol_threshold),
                    "industry": {"selected_weights": weights, "selected_n": int(len(selected)), "concentration": conc},
                }
            )

            prev_selected = selected_symbols

        by_market: Dict[str, List[float]] = {"BULL": [], "BEAR": []}
        by_vol: Dict[str, List[float]] = {"HIGH_VOL": [], "LOW_VOL": []}
        for row in yearly_rows:
            rnet = row.get("portfolio_return_net")
            if rnet is None:
                continue
            reg = row.get("regime") or {}
            m = reg.get("market")
            v = reg.get("volatility")
            if m in by_market:
                by_market[m].append(float(rnet))
            if v in by_vol:
                by_vol[v].append(float(rnet))

        summary = {
            "gross": _summarize_performance(gross_returns),
            "net": _summarize_performance(net_returns),
            "ic": _summarize_ic(ic_vals),
            "benchmark": _summarize_performance([b for b in bench_returns if b is not None]),
            "active_vs_benchmark": {
                "gross": _summarize_active_vs_benchmark(gross_yearly, bench_returns),
                "net": _summarize_active_vs_benchmark(net_yearly, bench_returns),
            },
            "regimes": {
                "market": {k: _summarize_performance(v) for k, v in by_market.items() if v},
                "volatility": {k: _summarize_performance(v) for k, v in by_vol.items() if v},
                "vol_threshold": vol_threshold,
            },
            "stress_tests": _stress_summaries(yearly_rows, k=2),
            "robustness": {
                "leave_one_year_out_net": _leave_one_year_out(
                    list(range(int(config.start_hold_year), int(config.end_hold_year) + 1)),
                    net_yearly,
                ),
                "rolling_3y_net": _rolling_windows(
                    list(range(int(config.start_hold_year), int(config.end_hold_year) + 1)),
                    net_yearly,
                    window=3,
                ),
            },
        }

        strategy_reports[spec.id] = {
            "spec": {"id": spec.id, "label": spec.label, "description": spec.description, "components": list(spec.components)},
            "summary": summary,
            "yearly": (yearly_rows if include_yearly else []),
        }

    return strategy_reports


def run_factor_library_backtest_prepared(
    prepared: PreparedFactorBacktestData,
    config: FactorBacktestConfig,
    *,
    factor_library: Tuple[FactorSpec, ...] = DEFAULT_FACTOR_LIBRARY,
    include_yearly: bool = True,
) -> Dict[str, Any]:
    """
    Run backtests using precomputed aggregates (for robustness/sensitivity suites).
    """
    strategy_reports = _run_factor_library_backtest_core(
        config=config,
        factor_library=factor_library,
        industries_df=prepared.industries_df,
        get_ratios=lambda y: prepared.ratios_by_year.get(int(y), pd.DataFrame()),
        get_price_stats=lambda y: prepared.price_stats_by_year.get(int(y), pd.DataFrame()),
        get_returns=lambda y: prepared.returns_by_year.get(int(y), pd.DataFrame()),
        vol_threshold=prepared.vol_threshold,
        include_yearly=include_yearly,
    )

    return {
        "config": {
            "start_hold_year": config.start_hold_year,
            "end_hold_year": config.end_hold_year,
            "formation_lag_years": config.formation_lag_years,
            "top_n": config.top_n,
            "benchmark_symbol": config.benchmark_symbol,
            "return_mode": config.return_mode,
            "min_signal_coverage": config.min_signal_coverage,
            "close_scale_vnd": config.close_scale_vnd,
            "signal_robustness": config.signal_robustness.__dict__,
            "portfolio_aggregation": config.portfolio_aggregation.__dict__,
            "selection_constraints": config.selection_constraints.__dict__,
            "investability_signal_year": config.investability_signal_year.__dict__,
            "investability_hold_year": config.investability_hold_year.__dict__,
            "transaction_costs": config.transaction_costs.__dict__,
            "min_universe_for_ic": config.min_universe_for_ic,
            "prepared_data": {
                "close_scale_vnd": prepared.close_scale_vnd,
                "benchmark_symbol": prepared.benchmark_symbol,
            },
        },
        "data_limits": {
            "look_ahead_control": f"signal_year = hold_year - {int(config.formation_lag_years)} (no publication dates)",
            "price_close_unit": f"close * {config.close_scale_vnd} ~ VND (assumed)",
            "total_return": "cash dividends only (events.DIV); no splits/rights adjustments",
            "survivorship_bias": "DB does not provide delisted_date/status reliably; results may be survivorship-biased if delisted tickers are missing.",
        },
        "strategies": strategy_reports,
    }


def run_factor_library_backtest(
    db_path: Path,
    config: FactorBacktestConfig,
    *,
    factor_library: Tuple[FactorSpec, ...] = DEFAULT_FACTOR_LIBRARY,
    include_yearly: bool = True,
) -> Dict[str, Any]:
    db_path = Path(db_path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    # Cache small tables and yearly aggregates to avoid repeated heavy queries.
    ratios_cache: Dict[int, pd.DataFrame] = {}
    price_stats_cache: Dict[int, pd.DataFrame] = {}
    dividends_cache: Dict[int, pd.DataFrame] = {}
    returns_cache: Dict[int, pd.DataFrame] = {}

    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row

        industries_df = _query_symbol_industries(conn)

        def _ratios(year: int) -> pd.DataFrame:
            if year not in ratios_cache:
                ratios_cache[year] = _query_annual_ratios(conn, year)
            return ratios_cache[year]

        def _price_stats(year: int) -> pd.DataFrame:
            if year not in price_stats_cache:
                yp = query_price_history_year(conn, year)
                price_stats_cache[year] = compute_year_price_stats(yp, year=year, close_scale_vnd=config.close_scale_vnd)
            return price_stats_cache[year]

        def _dividends(year: int) -> pd.DataFrame:
            if year not in dividends_cache:
                dividends_cache[year] = query_cash_dividends_year(conn, year)
            return dividends_cache[year]

        def _returns(year: int) -> pd.DataFrame:
            if year not in returns_cache:
                ps = _price_stats(year)
                div = _dividends(year)
                returns_cache[year] = attach_cash_dividends_to_returns(ps, div, close_scale_vnd=config.close_scale_vnd)
            return returns_cache[year]

        # Precompute benchmark vol threshold for regime classification (median over years where available)
        bench_vols: List[float] = []
        if config.benchmark_symbol:
            for y in range(int(config.start_hold_year), int(config.end_hold_year) + 1):
                r = _returns(y)
                b = r.loc[r["symbol"] == str(config.benchmark_symbol)]
                if not b.empty and b["vol_annualized"].notna().any():
                    bench_vols.append(float(b["vol_annualized"].iloc[0]))
        vol_threshold = float(np.median(bench_vols)) if bench_vols else None

        strategy_reports: Dict[str, Any] = {}

        for spec in factor_library:
            yearly_rows: List[Dict[str, Any]] = []
            prev_selected: Optional[List[str]] = None
            ic_vals: List[float] = []
            gross_returns: List[float] = []
            net_returns: List[float] = []
            bench_returns: List[Optional[float]] = []
            gross_yearly: List[Optional[float]] = []
            net_yearly: List[Optional[float]] = []

            for hold_year in range(int(config.start_hold_year), int(config.end_hold_year) + 1):
                formation_year = hold_year - int(config.formation_lag_years)

                fundamentals = _ratios(formation_year)
                if fundamentals.empty:
                    yearly_rows.append(
                        {
                            "formation_year": formation_year,
                            "hold_year": hold_year,
                            "universe_n": 0,
                            "selected_n": 0,
                            "portfolio_return_gross": None,
                            "portfolio_return_net": None,
                            "transaction_cost": None,
                            "turnover_one_way": None,
                            "overlap_n": None,
                            "benchmark_return": None,
                            "benchmark_vol_annualized": None,
                            "ic_spearman": None,
                            "drops": {"no_fundamentals": 0},
                            "regime": {"market": None, "volatility": None},
                            "industry": {"selected_weights": {}, "selected_n": 0},
                        }
                    )
                    prev_selected = None
                    continue

                # Signal-year price stats (liquidity, momentum, vol proxy)
                ps_signal = _price_stats(formation_year)
                ps_signal = ps_signal.rename(
                    columns={
                        "price_return": "price_return_signal",
                        "vol_annualized": "vol_annualized_signal",
                        "trading_days": "trading_days_signal",
                        "avg_dollar_volume_vnd": "avg_dollar_volume_vnd_signal",
                        "zero_volume_frac": "zero_volume_frac_signal",
                        "stale_close_frac": "stale_close_frac_signal",
                        "start_gap_days": "start_gap_days_signal",
                        "end_gap_days": "end_gap_days_signal",
                    }
                )

                base = fundamentals.merge(ps_signal, on=["symbol"], how="inner")
                base = base.merge(industries_df, on="symbol", how="left")

                # Apply investability filters on SIGNAL year (look-ahead safe)
                base_filt, drops_signal = _apply_investability_filters(base, config.investability_signal_year, prefix="_signal")

                # Compute factor signal
                with_signal = _compute_composite_signal(
                    base_filt,
                    spec,
                    min_coverage=config.min_signal_coverage,
                    robustness=config.signal_robustness,
                )
                with_signal = with_signal.dropna(subset=["signal"])

                # Holding year returns (+ hold-year investability)
                r_hold = _returns(hold_year)
                if config.return_mode == "total_return_cash_div":
                    ret_col = "total_return"
                else:
                    ret_col = "price_return"

                return_cols = [
                    "symbol",
                    ret_col,  # source return for strategy
                    "price_return",
                    "total_return",
                    "cash_dividend_vnd",
                    "dividend_events",
                    "vol_annualized",
                    "trading_days",
                    "avg_dollar_volume_vnd",
                    "zero_volume_frac",
                    "stale_close_frac",
                    "start_gap_days",
                    "end_gap_days",
                ]
                # Avoid duplicate column names when ret_col is already in the list.
                return_cols_unique: List[str] = []
                for c in return_cols:
                    if c not in return_cols_unique:
                        return_cols_unique.append(c)

                merged = with_signal.merge(r_hold[return_cols_unique], on="symbol", how="inner")
                merged["ret"] = pd.to_numeric(merged.get(ret_col), errors="coerce")

                # Apply HOLD-year investability constraints (stale end, etc.)
                merged, drops_hold = _apply_investability_filters(merged, config.investability_hold_year, prefix="")
                merged = merged.dropna(subset=["ret"])

                universe_n = int(len(merged))

                benchmark_return = None
                benchmark_vol = None
                if config.benchmark_symbol:
                    bench_row = r_hold.loc[r_hold["symbol"] == str(config.benchmark_symbol)]
                    if not bench_row.empty:
                        if bench_row["price_return"].notna().any():
                            benchmark_return = float(bench_row["price_return"].iloc[0])
                        if bench_row["vol_annualized"].notna().any():
                            benchmark_vol = float(bench_row["vol_annualized"].iloc[0])
                bench_returns.append(benchmark_return)

                if universe_n == 0:
                    yearly_rows.append(
                        {
                            "formation_year": formation_year,
                            "hold_year": hold_year,
                            "universe_n": 0,
                            "selected_n": 0,
                            "portfolio_return_gross": None,
                            "portfolio_return_net": None,
                            "transaction_cost": None,
                            "turnover_one_way": None,
                            "overlap_n": None,
                            "benchmark_return": benchmark_return,
                            "benchmark_vol_annualized": benchmark_vol,
                            "ic_spearman": None,
                            "drops": {"signal_year": drops_signal, "hold_year": drops_hold},
                            "regime": _classify_regime(benchmark_return, benchmark_vol, vol_threshold=vol_threshold),
                            "industry": {"selected_weights": {}, "selected_n": 0},
                        }
                    )
                    prev_selected = None
                    gross_yearly.append(None)
                    net_yearly.append(None)
                    continue

                merged = merged.sort_values("signal", ascending=False)
                selected, selection_meta = _select_portfolio(
                    merged,
                    top_n=int(config.top_n),
                    constraints=config.selection_constraints,
                )
                selected_symbols = selected["symbol"].astype(str).tolist()

                # Portfolio return (equal-weight)
                portfolio_ret = _aggregate_portfolio_return(selected["ret"], config.portfolio_aggregation) if len(selected) else None
                ic = _spearman_rank_correlation(merged["signal"], merged["ret"]) if universe_n >= int(config.min_universe_for_ic) else None
                if ic is not None:
                    ic_vals.append(ic)

                # Turnover + transaction costs
                turnover_one_way, overlap_n = _compute_turnover(prev_selected, selected_symbols)
                ret_net, cost = _apply_transaction_cost(portfolio_ret, turnover_one_way, config.transaction_costs)

                if portfolio_ret is not None:
                    gross_returns.append(portfolio_ret)
                gross_yearly.append(portfolio_ret)
                if ret_net is not None:
                    net_returns.append(ret_net)
                net_yearly.append(ret_net)

                # Industry attribution (weights by count)
                weights: Dict[str, float] = {}
                if "icb_name3" in selected.columns:
                    counts = selected["icb_name3"].fillna("Unknown").value_counts(dropna=False)
                    for k, v in counts.to_dict().items():
                        weights[str(k)] = float(v) / float(len(selected)) if len(selected) else 0.0
                conc = _industry_concentration(selected)

                # IC by industry (within-year; optional / diagnostic only)
                ic_by_industry: Dict[str, float] = {}
                if "icb_name3" in merged.columns and universe_n >= int(config.min_universe_for_ic):
                    for name, g in merged.groupby(merged["icb_name3"].fillna("Unknown")):
                        if len(g) < 30:
                            continue
                        ic_g = _spearman_rank_correlation(g["signal"], g["ret"])
                        if ic_g is not None:
                            ic_by_industry[str(name)] = float(ic_g)

                yearly_rows.append(
                    {
                        "formation_year": formation_year,
                        "hold_year": hold_year,
                        "universe_n": universe_n,
                        "selected_n": int(len(selected)),
                        "portfolio_return_gross": portfolio_ret,
                        "portfolio_return_net": ret_net,
                        "transaction_cost": cost,
                        "turnover_one_way": turnover_one_way,
                        "overlap_n": overlap_n,
                        "benchmark_return": benchmark_return,
                        "benchmark_vol_annualized": benchmark_vol,
                        "ic_spearman": ic,
                        "ic_by_industry": ic_by_industry,
                        "selection": selection_meta,
                        "drops": {"signal_year": drops_signal, "hold_year": drops_hold},
                        "regime": _classify_regime(benchmark_return, benchmark_vol, vol_threshold=vol_threshold),
                        "industry": {"selected_weights": weights, "selected_n": int(len(selected)), "concentration": conc},
                    }
                )

                prev_selected = selected_symbols

            # Regime summaries (net returns)
            by_market: Dict[str, List[float]] = {"BULL": [], "BEAR": []}
            by_vol: Dict[str, List[float]] = {"HIGH_VOL": [], "LOW_VOL": []}
            for row in yearly_rows:
                rnet = row.get("portfolio_return_net")
                if rnet is None:
                    continue
                reg = row.get("regime") or {}
                m = reg.get("market")
                v = reg.get("volatility")
                if m in by_market:
                    by_market[m].append(float(rnet))
                if v in by_vol:
                    by_vol[v].append(float(rnet))

            strategy_reports[spec.id] = {
                "spec": {"id": spec.id, "label": spec.label, "description": spec.description, "components": list(spec.components)},
                "summary": {
                    "gross": _summarize_performance(gross_returns),
                    "net": _summarize_performance(net_returns),
                    "ic": _summarize_ic(ic_vals),
                    "benchmark": _summarize_performance([b for b in bench_returns if b is not None]),
                    "active_vs_benchmark": {
                        "gross": _summarize_active_vs_benchmark(gross_yearly, bench_returns),
                        "net": _summarize_active_vs_benchmark(net_yearly, bench_returns),
                    },
                    "regimes": {
                        "market": {k: _summarize_performance(v) for k, v in by_market.items() if v},
                        "volatility": {k: _summarize_performance(v) for k, v in by_vol.items() if v},
                        "vol_threshold": vol_threshold,
                    },
                    "stress_tests": _stress_summaries(yearly_rows, k=2),
                    "robustness": {
                        "leave_one_year_out_net": _leave_one_year_out(
                            list(range(int(config.start_hold_year), int(config.end_hold_year) + 1)),
                            net_yearly,
                        ),
                        "rolling_3y_net": _rolling_windows(
                            list(range(int(config.start_hold_year), int(config.end_hold_year) + 1)),
                            net_yearly,
                            window=3,
                        ),
                    },
                },
                "yearly": (yearly_rows if include_yearly else []),
            }

    return {
        "config": {
            "start_hold_year": config.start_hold_year,
            "end_hold_year": config.end_hold_year,
            "formation_lag_years": config.formation_lag_years,
            "top_n": config.top_n,
            "benchmark_symbol": config.benchmark_symbol,
            "return_mode": config.return_mode,
            "min_signal_coverage": config.min_signal_coverage,
            "close_scale_vnd": config.close_scale_vnd,
            "signal_robustness": config.signal_robustness.__dict__,
            "portfolio_aggregation": config.portfolio_aggregation.__dict__,
            "selection_constraints": config.selection_constraints.__dict__,
            "investability_signal_year": config.investability_signal_year.__dict__,
            "investability_hold_year": config.investability_hold_year.__dict__,
            "transaction_costs": config.transaction_costs.__dict__,
            "min_universe_for_ic": config.min_universe_for_ic,
            "include_yearly": bool(include_yearly),
        },
        "data_limits": {
            "look_ahead_control": f"signal_year = hold_year - {int(config.formation_lag_years)} (no publication dates)",
            "price_close_unit": f"close * {config.close_scale_vnd} ~ VND (assumed)",
            "total_return": "cash dividends only (events.DIV); no splits/rights adjustments",
            "survivorship_bias": "DB does not provide delisted_date/status reliably; results may be survivorship-biased if delisted tickers are missing.",
        },
        "strategies": strategy_reports,
    }
