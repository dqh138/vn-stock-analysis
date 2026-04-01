"""
Return Engine (research-grade under local DB data limits).

Provides reusable building blocks for:
  - Yearly price return from close prices
  - Cash-dividend-adjusted "total return" (partial total return; no splits/rights)
  - Liquidity and staleness diagnostics for investability filters

Data limits (explicit):
  - Uses `stock_price_history.close` which appears to be quoted in *thousand VND* (e.g., 64.4 ~ 64,400 VND).
  - Adjusts for cash dividends via `events` where `event_list_code='DIV'`.
  - Does NOT adjust for stock splits, bonus issues, rights, or other corporate actions (events 'ISS', 'AIS', ...).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
import sqlite3


DEFAULT_CLOSE_SCALE_VND: float = 1000.0


@dataclass(frozen=True)
class YearWindow:
    year: int

    @property
    def start(self) -> str:
        return f"{int(self.year)}-01-01"

    @property
    def end_exclusive(self) -> str:
        return f"{int(self.year) + 1}-01-01"

    @property
    def end_date(self) -> date:
        return date(int(self.year), 12, 31)

    @property
    def start_date(self) -> date:
        return date(int(self.year), 1, 1)


def query_price_history_year(conn: sqlite3.Connection, year: int) -> pd.DataFrame:
    """
    Fetch daily close+volume for a given calendar year.

    Returns:
        DataFrame columns: symbol, time, close, volume
    """
    w = YearWindow(int(year))
    df = pd.read_sql_query(
        """
        SELECT symbol, time, close, volume
        FROM stock_price_history
        WHERE time >= ?
          AND time < ?
          AND close IS NOT NULL
        ORDER BY symbol, time
        """,
        conn,
        params=(w.start, w.end_exclusive),
    )
    if not df.empty:
        df["symbol"] = df["symbol"].astype(str)
        df["time"] = df["time"].astype(str)
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df = df.dropna(subset=["close"])
    return df


def compute_year_price_stats(
    year_prices: pd.DataFrame,
    *,
    year: int,
    close_scale_vnd: float = DEFAULT_CLOSE_SCALE_VND,
) -> pd.DataFrame:
    """
    Compute per-symbol yearly stats from daily close+volume data.

    Returns DataFrame columns (per symbol):
      - start_date, end_date (YYYY-MM-DD)
      - start_close, end_close
      - price_return
      - trading_days
      - avg_volume
      - avg_dollar_volume_vnd (uses close_scale_vnd)
      - zero_volume_frac
      - stale_close_frac
      - vol_annualized (log-return std * sqrt(252))
      - start_gap_days, end_gap_days (calendar-day gaps)
    """
    if year_prices.empty:
        return pd.DataFrame(
            columns=[
                "symbol",
                "year",
                "start_date",
                "end_date",
                "start_close",
                "end_close",
                "price_return",
                "trading_days",
                "avg_volume",
                "avg_dollar_volume_vnd",
                "zero_volume_frac",
                "stale_close_frac",
                "vol_annualized",
                "start_gap_days",
                "end_gap_days",
            ]
        )

    w = YearWindow(int(year))
    df = year_prices.copy()
    df = df.sort_values(["symbol", "time"], kind="mergesort")

    # Basic per-symbol aggregations
    grouped = df.groupby("symbol", sort=False)
    starts = grouped.first(numeric_only=False).rename(columns={"time": "start_date", "close": "start_close", "volume": "start_volume"})[
        ["start_date", "start_close", "start_volume"]
    ]
    ends = grouped.last(numeric_only=False).rename(columns={"time": "end_date", "close": "end_close", "volume": "end_volume"})[
        ["end_date", "end_close", "end_volume"]
    ]
    base = starts.join(ends, how="inner")
    base.index.name = "symbol"

    trading_days = grouped.size().rename("trading_days")
    avg_volume = grouped["volume"].mean().rename("avg_volume")

    # Dollar volume in VND (assumes close quoted in thousand VND by default)
    dv = (df["close"].astype("float64") * float(close_scale_vnd)) * df["volume"].fillna(0.0).astype("float64")
    df = df.assign(_dv=dv)
    avg_dv = df.groupby("symbol", sort=False)["_dv"].mean().rename("avg_dollar_volume_vnd")

    zero_vol = df["volume"].fillna(0.0) <= 0
    zero_vol_frac = df.assign(_zv=zero_vol.astype("float64")).groupby("symbol", sort=False)["_zv"].mean().rename("zero_volume_frac")

    # Stale close fraction (close unchanged vs previous trading day)
    def _stale_frac(closes: pd.Series) -> float:
        vals = closes.to_numpy(dtype="float64", copy=False)
        if len(vals) <= 1:
            return 0.0
        same = np.isclose(vals[1:], vals[:-1], equal_nan=False)
        return float(np.mean(same)) if len(same) else 0.0

    stale_frac = grouped["close"].apply(_stale_frac).rename("stale_close_frac")

    # Annualized volatility (log returns std)
    def _vol_ann(closes: pd.Series) -> Optional[float]:
        vals = closes.to_numpy(dtype="float64", copy=False)
        if len(vals) < 3:
            return None
        with np.errstate(divide="ignore", invalid="ignore"):
            lr = np.diff(np.log(vals))
        lr = lr[np.isfinite(lr)]
        if len(lr) < 2:
            return None
        vol_d = float(np.std(lr, ddof=1))
        return float(vol_d * np.sqrt(252.0))

    vol_ann = grouped["close"].apply(_vol_ann).rename("vol_annualized")

    out = base.join([trading_days, avg_volume, avg_dv, zero_vol_frac, stale_frac, vol_ann], how="left").reset_index()
    out.insert(1, "year", int(year))

    out["price_return"] = out["end_close"].astype("float64") / out["start_close"].astype("float64") - 1.0
    out.loc[~np.isfinite(out["price_return"].to_numpy()), "price_return"] = np.nan

    # Gap diagnostics (calendar days)
    out["_start_dt"] = pd.to_datetime(out["start_date"], errors="coerce")
    out["_end_dt"] = pd.to_datetime(out["end_date"], errors="coerce")
    out["start_gap_days"] = (out["_start_dt"] - pd.Timestamp(w.start_date)).dt.days
    out["end_gap_days"] = (pd.Timestamp(w.end_date) - out["_end_dt"]).dt.days
    out = out.drop(columns=["_start_dt", "_end_dt"])

    # Ensure stable dtypes
    numeric_cols = [
        "start_close",
        "end_close",
        "price_return",
        "trading_days",
        "avg_volume",
        "avg_dollar_volume_vnd",
        "zero_volume_frac",
        "stale_close_frac",
        "vol_annualized",
        "start_gap_days",
        "end_gap_days",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def query_cash_dividends_year(conn: sqlite3.Connection, year: int) -> pd.DataFrame:
    """
    Aggregate cash dividends per share (VND/share) by symbol for a calendar year.

    Source: `events` where event_list_code='DIV'.
    Uses event date preference: exright_date -> issue_date -> public_date.

    Returns DataFrame columns:
      - symbol
      - year
      - cash_dividend_vnd (sum)
      - dividend_events (count)
      - last_dividend_date (YYYY-MM-DD)
    """
    w = YearWindow(int(year))

    df = pd.read_sql_query(
        """
        SELECT
          symbol,
          COALESCE(exright_date, issue_date, public_date) AS event_date,
          ratio,
          value
        FROM events
        WHERE event_list_code = 'DIV'
          AND symbol IS NOT NULL
          AND COALESCE(exright_date, issue_date, public_date) >= ?
          AND COALESCE(exright_date, issue_date, public_date) < ?
        """,
        conn,
        params=(w.start, w.end_exclusive),
    )

    if df.empty:
        return pd.DataFrame(columns=["symbol", "year", "cash_dividend_vnd", "dividend_events", "last_dividend_date"])

    df["symbol"] = df["symbol"].astype(str)
    df["event_date"] = df["event_date"].astype(str)
    df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Prefer value (VND/share). If missing, infer from ratio as % of par (10,000 VND) if plausible.
    inferred = df["ratio"].fillna(0.0) * 10_000.0
    cash = df["value"].where(df["value"].notna() & (df["value"] > 0), inferred)
    cash = cash.where(cash.notna() & (cash > 0), 0.0)
    df = df.assign(_cash=cash)

    agg = (
        df.groupby("symbol", as_index=False)
        .agg(
            cash_dividend_vnd=("_cash", "sum"),
            dividend_events=("_cash", lambda s: int(np.sum(np.asarray(s) > 0))),
            last_dividend_date=("event_date", "max"),
        )
        .assign(year=int(year))
    )
    return agg[["symbol", "year", "cash_dividend_vnd", "dividend_events", "last_dividend_date"]]


def attach_cash_dividends_to_returns(
    price_stats: pd.DataFrame,
    cash_dividends: pd.DataFrame,
    *,
    close_scale_vnd: float = DEFAULT_CLOSE_SCALE_VND,
) -> pd.DataFrame:
    """
    Merge yearly cash dividends into price stats and compute total return.

    Adds columns:
      - cash_dividend_vnd
      - dividend_events
      - total_return (price + cash dividend, unit-consistent via close_scale_vnd)
      - dividend_yield_start
    """
    out = price_stats.copy()
    # Ensure stable schema even when empty (prevents downstream KeyError in merges).
    if out.empty:
        out["cash_dividend_vnd"] = pd.Series(dtype="float64")
        out["dividend_events"] = pd.Series(dtype="int64")
        out["dividend_yield_start"] = pd.Series(dtype="float64")
        if "price_return" in out.columns:
            out["total_return"] = pd.Series(dtype="float64")
        else:
            out["price_return"] = pd.Series(dtype="float64")
            out["total_return"] = pd.Series(dtype="float64")
        return out

    div = cash_dividends.copy() if cash_dividends is not None else pd.DataFrame()
    if div.empty:
        out["cash_dividend_vnd"] = 0.0
        out["dividend_events"] = 0
        out["total_return"] = out.get("price_return")
        out["dividend_yield_start"] = 0.0
        return out

    merged = out.merge(div[["symbol", "cash_dividend_vnd", "dividend_events"]], on="symbol", how="left")
    merged["cash_dividend_vnd"] = pd.to_numeric(merged["cash_dividend_vnd"], errors="coerce").fillna(0.0)
    merged["dividend_events"] = pd.to_numeric(merged["dividend_events"], errors="coerce").fillna(0).astype(int)

    start_vnd = merged["start_close"].astype("float64") * float(close_scale_vnd)
    end_vnd = merged["end_close"].astype("float64") * float(close_scale_vnd)
    merged["dividend_yield_start"] = np.where(start_vnd > 0, merged["cash_dividend_vnd"].astype("float64") / start_vnd, np.nan)
    merged["total_return"] = np.where(start_vnd > 0, (end_vnd + merged["cash_dividend_vnd"].astype("float64")) / start_vnd - 1.0, np.nan)

    return merged
