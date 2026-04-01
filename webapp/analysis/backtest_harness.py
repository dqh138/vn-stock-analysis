"""
Backtest Harness (research-grade scaffolding under data limits).

Goal:
    Provide a deterministic, walk-forward backtesting framework for factor-like signals
    using only the local SQLite DB. This enables research validation (IC/IR, look-ahead
    controls) without requiring external data sources.

Data limits (explicit):
    - Uses close prices only (no corporate actions / total return adjustments).
    - Uses financial_ratios annual rows (quarter IS NULL) for fundamentals (clean 1 row/year).
    - VNINDEX coverage may be limited in some DB snapshots; benchmark is optional.

Design choices:
    - Walk-forward: form portfolios using fundamentals of (year-1), hold for year.
      This is a pragmatic look-ahead control when publication dates are not available.
    - Equal-weight portfolios by default (no liquidity/float constraints available).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import sqlite3


@dataclass(frozen=True)
class BacktestConfig:
    start_hold_year: int
    end_hold_year: int
    top_n: int = 30
    benchmark_symbol: Optional[str] = "VNINDEX"
    min_signal_coverage: int = 3  # minimum number of signal components available


@dataclass(frozen=True)
class BacktestYearResult:
    formation_year: int
    hold_year: int
    universe_n: int
    selected_n: int
    portfolio_return: Optional[float]
    benchmark_return: Optional[float]
    ic_spearman: Optional[float]


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


def _query_annual_fundamentals(conn: sqlite3.Connection, year: int) -> pd.DataFrame:
    # Use financial_ratios because it is clean 1-row-per-year (quarter IS NULL).
    df = pd.read_sql_query(
        """
        SELECT
          symbol,
          year,
          roe,
          net_profit_margin,
          debt_to_equity,
          price_to_earnings,
          price_to_book
        FROM financial_ratios
        WHERE quarter IS NULL
          AND year = ?
        """,
        conn,
        params=(int(year),),
    )
    return df


def _query_year_returns(conn: sqlite3.Connection, year: int) -> pd.DataFrame:
    """
    Compute simple returns for each symbol within a calendar year from close prices.

    Returns:
        DataFrame columns: symbol, start_close, end_close, ret
    """
    y0 = f"{int(year)}-01-01"
    y1 = f"{int(year) + 1}-01-01"

    df = pd.read_sql_query(
        """
        WITH year_prices AS (
          SELECT symbol, time, close
          FROM stock_price_history
          WHERE time >= ?
            AND time < ?
            AND close IS NOT NULL
        ),
        ranked AS (
          SELECT
            symbol,
            time,
            close,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY time ASC) AS rn_asc,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY time DESC) AS rn_desc
          FROM year_prices
        ),
        starts AS (
          SELECT symbol, close AS start_close
          FROM ranked
          WHERE rn_asc = 1
        ),
        ends AS (
          SELECT symbol, close AS end_close
          FROM ranked
          WHERE rn_desc = 1
        )
        SELECT
          s.symbol AS symbol,
          s.start_close AS start_close,
          e.end_close AS end_close,
          (e.end_close / s.start_close - 1.0) AS ret
        FROM starts s
        JOIN ends e USING(symbol)
        """,
        conn,
        params=(y0, y1),
    )
    return df


def _compute_quality_value_signal(df: pd.DataFrame, *, min_coverage: int) -> pd.DataFrame:
    """
    Compute a simple composite signal using percentile ranks.

    Components (under data limits):
        - quality: roe (high), net_profit_margin (high), debt_to_equity (low)
        - value: price_to_earnings (low), price_to_book (low)
    """
    working = df.copy()

    # Enforce basic validity rules (avoid nonsensical <=0 valuations)
    for col in ["price_to_earnings", "price_to_book"]:
        if col in working.columns:
            working.loc[working[col] <= 0, col] = np.nan

    components: List[pd.Series] = []

    if "roe" in working.columns:
        components.append(working["roe"].rank(pct=True, ascending=True))
    if "net_profit_margin" in working.columns:
        components.append(working["net_profit_margin"].rank(pct=True, ascending=True))
    if "debt_to_equity" in working.columns:
        components.append(working["debt_to_equity"].rank(pct=True, ascending=False))
    if "price_to_earnings" in working.columns:
        components.append(working["price_to_earnings"].rank(pct=True, ascending=False))
    if "price_to_book" in working.columns:
        components.append(working["price_to_book"].rank(pct=True, ascending=False))

    if not components:
        working["signal"] = np.nan
        working["signal_coverage"] = 0
        return working

    comp_df = pd.concat(components, axis=1)
    working["signal_coverage"] = comp_df.notna().sum(axis=1).astype(int)
    working["signal"] = comp_df.mean(axis=1, skipna=True)

    working.loc[working["signal_coverage"] < int(min_coverage), "signal"] = np.nan
    return working


def run_quality_value_backtest(db_path: Path, config: BacktestConfig) -> Dict[str, Any]:
    """
    Run a walk-forward factor backtest using the composite quality+value signal.

    Portfolio formation:
        - Formation year: hold_year - 1
        - Use fundamentals for formation year to compute signal.
        - Select top N by signal.

    Holding:
        - Use same-calendar-year return for hold_year from price closes.
    """
    db_path = Path(db_path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    results: List[BacktestYearResult] = []

    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row

        for hold_year in range(int(config.start_hold_year), int(config.end_hold_year) + 1):
            formation_year = hold_year - 1

            fundamentals = _query_annual_fundamentals(conn, formation_year)
            if fundamentals.empty:
                results.append(
                    BacktestYearResult(
                        formation_year=formation_year,
                        hold_year=hold_year,
                        universe_n=0,
                        selected_n=0,
                        portfolio_return=None,
                        benchmark_return=None,
                        ic_spearman=None,
                    )
                )
                continue

            fundamentals = _compute_quality_value_signal(fundamentals, min_coverage=config.min_signal_coverage)
            fundamentals = fundamentals.dropna(subset=["signal"])

            returns = _query_year_returns(conn, hold_year)
            merged = fundamentals.merge(returns[["symbol", "ret"]], on="symbol", how="inner")
            merged = merged.dropna(subset=["ret"])

            universe_n = int(len(merged))
            if universe_n == 0:
                results.append(
                    BacktestYearResult(
                        formation_year=formation_year,
                        hold_year=hold_year,
                        universe_n=0,
                        selected_n=0,
                        portfolio_return=None,
                        benchmark_return=None,
                        ic_spearman=None,
                    )
                )
                continue

            merged = merged.sort_values("signal", ascending=False)
            selected = merged.head(int(config.top_n))

            portfolio_return = float(selected["ret"].mean()) if len(selected) else None
            ic = _spearman_rank_correlation(merged["signal"], merged["ret"])

            benchmark_return = None
            if config.benchmark_symbol:
                bench = returns.loc[returns["symbol"] == str(config.benchmark_symbol)]
                if not bench.empty and bench["ret"].notna().any():
                    benchmark_return = float(bench["ret"].iloc[0])

            results.append(
                BacktestYearResult(
                    formation_year=formation_year,
                    hold_year=hold_year,
                    universe_n=universe_n,
                    selected_n=int(len(selected)),
                    portfolio_return=portfolio_return,
                    benchmark_return=benchmark_return,
                    ic_spearman=ic,
                )
            )

    # Build summary stats
    rets = np.array([r.portfolio_return for r in results if r.portfolio_return is not None], dtype="float64")
    years = int(len(rets))
    cagr = None
    if years >= 2:
        cagr = float(np.prod(1.0 + rets) ** (1.0 / years) - 1.0)

    vol = float(np.std(rets, ddof=1)) if years >= 2 else None
    mean_ret = float(np.mean(rets)) if years >= 1 else None
    sharpe = float(mean_ret / vol) if (mean_ret is not None and vol is not None and vol > 0) else None

    ic_vals = [r.ic_spearman for r in results if r.ic_spearman is not None]
    ic_mean = float(np.mean(ic_vals)) if ic_vals else None

    return {
        "config": {
            "start_hold_year": config.start_hold_year,
            "end_hold_year": config.end_hold_year,
            "top_n": config.top_n,
            "benchmark_symbol": config.benchmark_symbol,
            "min_signal_coverage": config.min_signal_coverage,
        },
        "data_limits": {
            "price_adjustments": "close_only_no_corporate_actions",
            "look_ahead_control": "signal_year = hold_year - 1",
            "universe": "symbols with fundamentals+prices for the year",
        },
        "summary": {
            "years": years,
            "mean_return": mean_ret,
            "volatility": vol,
            "sharpe": sharpe,
            "cagr": cagr,
            "ic_mean_spearman": ic_mean,
        },
        "yearly": [
            {
                "formation_year": r.formation_year,
                "hold_year": r.hold_year,
                "universe_n": r.universe_n,
                "selected_n": r.selected_n,
                "portfolio_return": r.portfolio_return,
                "benchmark_return": r.benchmark_return,
                "ic_spearman": r.ic_spearman,
            }
            for r in results
        ],
    }

