import pandas as pd

from webapp.analysis.return_engine import (
    attach_cash_dividends_to_returns,
    compute_year_price_stats,
)


def test_compute_year_price_stats_basic_gaps_and_returns():
    year_prices = pd.DataFrame(
        {
            "symbol": ["AAA", "AAA", "AAA", "BBB", "BBB"],
            "time": ["2024-01-02", "2024-01-03", "2024-12-30", "2024-01-02", "2024-12-30"],
            "close": [10.0, 11.0, 12.0, 20.0, 18.0],
            "volume": [100.0, 0.0, 100.0, 50.0, 50.0],
        }
    )

    stats = compute_year_price_stats(year_prices, year=2024, close_scale_vnd=1000.0)
    assert set(stats["symbol"]) == {"AAA", "BBB"}

    a = stats.loc[stats["symbol"] == "AAA"].iloc[0]
    assert a["trading_days"] == 3
    assert abs(a["price_return"] - (12.0 / 10.0 - 1.0)) < 1e-9
    assert abs(a["zero_volume_frac"] - (1.0 / 3.0)) < 1e-9
    assert a["start_gap_days"] == 1  # 2024-01-02 vs 2024-01-01
    assert a["end_gap_days"] == 1  # 2024-12-30 vs 2024-12-31

    b = stats.loc[stats["symbol"] == "BBB"].iloc[0]
    assert b["trading_days"] == 2
    assert abs(b["price_return"] - (18.0 / 20.0 - 1.0)) < 1e-9


def test_attach_cash_dividends_total_return_unit_consistent():
    price_stats = pd.DataFrame(
        {
            "symbol": ["AAA", "BBB"],
            "year": [2024, 2024],
            "start_close": [10.0, 20.0],
            "end_close": [12.0, 18.0],
            "price_return": [12.0 / 10.0 - 1.0, 18.0 / 20.0 - 1.0],
        }
    )
    dividends = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "year": [2024],
            "cash_dividend_vnd": [1000.0],
            "dividend_events": [1],
            "last_dividend_date": ["2024-06-01"],
        }
    )

    out = attach_cash_dividends_to_returns(price_stats, dividends, close_scale_vnd=1000.0)
    a = out.loc[out["symbol"] == "AAA"].iloc[0]

    # Close quoted in thousand VND -> start_close 10.0 => 10,000 VND
    expected = (12_000.0 + 1_000.0) / 10_000.0 - 1.0
    assert abs(a["total_return"] - expected) < 1e-9
    assert abs(a["dividend_yield_start"] - (1_000.0 / 10_000.0)) < 1e-9

    b = out.loc[out["symbol"] == "BBB"].iloc[0]
    assert abs(b["total_return"] - b["price_return"]) < 1e-12

