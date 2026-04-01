import sqlite3
from pathlib import Path

import pandas as pd

from webapp.analysis.backtest_factor_library import (
    DEFAULT_FACTOR_LIBRARY,
    FactorBacktestConfig,
    InvestabilityFilters,
    PortfolioAggregation,
    SelectionConstraints,
    SignalRobustness,
    TransactionCostModel,
    _aggregate_portfolio_return,
    _mad_clip_series,
    _select_portfolio,
    _winsorize_series,
    run_factor_library_backtest,
)


def _create_min_backtest_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()

    cur.execute(
        """
        CREATE TABLE financial_ratios (
          symbol TEXT,
          year INTEGER,
          quarter INTEGER,
          roe REAL,
          net_profit_margin REAL,
          debt_to_equity REAL,
          interest_coverage_ratio REAL,
          price_to_earnings REAL,
          price_to_book REAL,
          ev_to_ebitda REAL,
          market_cap_billions REAL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE stock_price_history (
          symbol TEXT,
          time TEXT,
          close REAL,
          volume REAL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE events (
          symbol TEXT,
          event_list_code TEXT,
          exright_date TEXT,
          issue_date TEXT,
          public_date TEXT,
          ratio REAL,
          value REAL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE stock_industry (
          ticker TEXT,
          icb_name3 TEXT,
          icb_code3 TEXT
        )
        """
    )

    # Industry mapping
    cur.executemany(
        "INSERT INTO stock_industry(ticker, icb_name3, icb_code3) VALUES (?,?,?)",
        [
            ("AAA", "Test", "0000"),
            ("BBB", "Test", "0000"),
        ],
    )

    # Formation year (2020) fundamentals
    cur.executemany(
        """
        INSERT INTO financial_ratios(
          symbol, year, quarter, roe, net_profit_margin, debt_to_equity,
          interest_coverage_ratio, price_to_earnings, price_to_book, ev_to_ebitda, market_cap_billions
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            ("AAA", 2020, None, 0.20, 0.10, 0.50, 5.0, 10.0, 1.0, 6.0, 1000.0),
            ("BBB", 2020, None, 0.10, 0.05, 1.00, 3.0, 15.0, 2.0, 8.0, 900.0),
        ],
    )

    # Price history (2020 signal year)
    cur.executemany(
        "INSERT INTO stock_price_history(symbol,time,close,volume) VALUES (?,?,?,?)",
        [
            ("AAA", "2020-01-02", 10.0, 1000),
            ("AAA", "2020-06-01", 11.0, 1000),
            ("AAA", "2020-12-30", 12.0, 1000),
            ("BBB", "2020-01-02", 10.0, 1000),
            ("BBB", "2020-06-01", 10.5, 1000),
            ("BBB", "2020-12-30", 11.0, 1000),
        ],
    )

    # Price history (2021 hold year)
    cur.executemany(
        "INSERT INTO stock_price_history(symbol,time,close,volume) VALUES (?,?,?,?)",
        [
            ("AAA", "2021-01-02", 12.0, 1000),
            ("AAA", "2021-06-01", 15.0, 1000),
            ("AAA", "2021-12-30", 18.0, 1000),
            ("BBB", "2021-01-02", 11.0, 1000),
            ("BBB", "2021-12-30", 12.0, 1000),
        ],
    )

    # Cash dividend for AAA in 2021 (VND/share)
    cur.execute(
        """
        INSERT INTO events(symbol,event_list_code,exright_date,issue_date,public_date,ratio,value)
        VALUES (?,?,?,?,?,?,?)
        """,
        ("AAA", "DIV", "2021-06-01", "2021-06-01", "2021-06-01", 0.10, 1000.0),
    )

    con.commit()
    con.close()


def test_factor_backtest_minimal_total_return_cash_div(tmp_path: Path):
    db_path = tmp_path / "mini.db"
    _create_min_backtest_db(db_path)

    invest = InvestabilityFilters(
        min_trading_days=1,
        max_start_gap_days=400,
        max_end_gap_days=400,
        min_avg_dollar_volume_vnd=None,
        max_zero_volume_frac=1.0,
        max_stale_close_frac=1.0,
    )

    cfg = FactorBacktestConfig(
        start_hold_year=2021,
        end_hold_year=2021,
        top_n=1,
        benchmark_symbol=None,
        return_mode="total_return_cash_div",
        min_signal_coverage=3,
        close_scale_vnd=1000.0,
        investability_signal_year=invest,
        investability_hold_year=invest,
        transaction_costs=TransactionCostModel(enabled=False, cost_bps_per_side=0.0),
        min_universe_for_ic=1,
    )

    report = run_factor_library_backtest(db_path, cfg, factor_library=(DEFAULT_FACTOR_LIBRARY[0],))
    strat = report["strategies"]["quality_value"]
    y = strat["yearly"][0]

    assert y["hold_year"] == 2021
    assert y["selected_n"] == 1

    # AAA: start 12.0 (=> 12,000 VND), end 18.0 (=> 18,000 VND), dividend 1,000 VND
    expected = (18_000.0 + 1_000.0) / 12_000.0 - 1.0
    assert abs(y["portfolio_return_gross"] - expected) < 1e-9


def test_select_portfolio_industry_cap_honors_cap_without_relax():
    df = pd.DataFrame(
        {
            "symbol": [f"S{i}" for i in range(8)],
            "signal": [0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55],
            "icb_name3": ["A", "A", "A", "A", "B", "B", "B", "B"],
            "ret": [0.1] * 8,
        }
    )
    # top_n=6, cap=0.5 => max_per_industry=floor(3) => can pick 3 from each without relax.
    selected, meta = _select_portfolio(df, top_n=6, constraints=SelectionConstraints(method="industry_cap", industry_max_weight=0.50))
    assert meta["method"] == "industry_cap"
    assert meta["cap_relaxed"] is False
    assert len(selected) == 6
    counts = selected["icb_name3"].value_counts().to_dict()
    assert counts.get("A", 0) <= meta["max_per_industry"]
    assert counts.get("B", 0) <= meta["max_per_industry"]


def test_signal_robustness_winsorize_and_mad_clip():
    s = pd.Series(list(range(1, 30)) + [10_000], dtype="float64")
    w = _winsorize_series(s, 10.0)
    assert w.max() < s.max()

    mc = _mad_clip_series(s, 3.0)
    assert mc.isna().sum() >= 1


def test_portfolio_aggregation_trimmed_mean():
    rets = pd.Series([0.0, 0.01, 0.02, 1.0], dtype="float64")
    mean = _aggregate_portfolio_return(rets, PortfolioAggregation(method="mean", trimmed_mean_pct=0.25))
    trimmed = _aggregate_portfolio_return(rets, PortfolioAggregation(method="trimmed_mean", trimmed_mean_pct=0.25))
    assert mean is not None and trimmed is not None
    assert trimmed < mean
