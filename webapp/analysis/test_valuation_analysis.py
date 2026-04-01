import sqlite3
from pathlib import Path

from webapp.analysis.valuation_analysis import analyze_valuation


def test_analyze_valuation_includes_price_and_fair_price(tmp_path):
    db_path = Path(tmp_path) / "test.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("CREATE TABLE stock_industry (ticker TEXT, icb_name3 TEXT)")
    cur.execute(
        """
        CREATE TABLE financial_ratios (
            symbol TEXT,
            year INTEGER,
            quarter INTEGER,
            price_to_earnings REAL,
            price_to_book REAL,
            price_to_sales REAL,
            ev_to_ebitda REAL,
            eps_vnd REAL,
            bvps_vnd REAL,
            roe REAL
        )
        """
    )
    cur.execute("CREATE TABLE stock_price_history (symbol TEXT, time TEXT, close REAL)")

    # Industry mapping (AAA is target; BBB is peer)
    cur.executemany(
        "INSERT INTO stock_industry (ticker, icb_name3) VALUES (?, ?)",
        [("AAA", "TestIndustry"), ("BBB", "TestIndustry")],
    )

    # 5-year history for percentiles (FY2021..FY2025)
    pe_hist = [10.0, 12.0, 14.0, 16.0, 18.0]
    pb_hist = [1.0, 1.5, 2.0, 2.5, 3.0]
    eps_hist = [800.0, 850.0, 900.0, 950.0, 1000.0]

    for i, year in enumerate(range(2021, 2026)):
        cur.execute(
            """
            INSERT INTO financial_ratios (
                symbol, year, quarter, price_to_earnings, price_to_book, price_to_sales,
                ev_to_ebitda, eps_vnd, bvps_vnd, roe
            ) VALUES (?, ?, NULL, ?, ?, NULL, NULL, ?, ?, ?)
            """,
            ("AAA", year, pe_hist[i], pb_hist[i], eps_hist[i], 5000.0, 0.20),
        )

    # Peer values for industry median in FY2025
    cur.execute(
        """
        INSERT INTO financial_ratios (
            symbol, year, quarter, price_to_earnings, price_to_book, price_to_sales,
            ev_to_ebitda, eps_vnd, bvps_vnd, roe
        ) VALUES (?, ?, NULL, ?, ?, NULL, NULL, ?, ?, ?)
        """,
        ("BBB", 2025, 10.0, 2.0, 1000.0, 5000.0, 0.15),
    )

    # Latest close price (quoted in thousand VND in this DB convention)
    cur.executemany(
        "INSERT INTO stock_price_history (symbol, time, close) VALUES (?, ?, ?)",
        [("AAA", "2026-02-12", 19.5), ("AAA", "2026-02-13", 20.0)],
    )

    conn.commit()
    conn.close()

    out = analyze_valuation(db_path, "AAA", year=2025)

    assert out["symbol"] == "AAA"
    assert out["year"] == 2025
    assert out["industry"] == "TestIndustry"

    # Price context
    assert out["price"]["as_of"] == "2026-02-13"
    assert out["price"]["close"] == 20.0
    assert out["price"]["close_scale_vnd"] == 1000.0
    assert out["price"]["close_vnd"] == 20_000.0

    # Multiples from current price and per-share fundamentals
    assert out["multiples_current"]["pe"] == 20.0  # 20,000 / 1,000
    assert out["multiples_current"]["pb"] == 4.0  # 20,000 / 5,000

    # Percentile coverage (5 values)
    assert out["pe_percentile"]["n"] == 5
    assert out["pb_percentile"]["n"] == 5

    # Fair price from historical median P/E: EPS(2025)=1000, P50=14 => 14,000 VND => 14.0k
    assert out["fair_price"]["pe_hist"]["fair_close"]["p50"] == 14.0
    assert out["fair_price"]["pe_hist"]["status"] == "expensive"

    # Graham number should be below current price in this setup
    assert out["fair_price"]["graham_number"]["fair_close"] is not None
    assert out["fair_price"]["graham_number"]["status"] == "expensive"

