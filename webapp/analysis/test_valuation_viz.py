import math
import sqlite3
from pathlib import Path

from webapp.analysis.valuation_viz import get_return_decomposition, get_valuation_timeseries


def test_get_valuation_timeseries_computes_year_end_multiples(tmp_path):
    db_path = Path(tmp_path) / "test.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE financial_ratios (
            symbol TEXT,
            year INTEGER,
            quarter INTEGER,
            eps_vnd REAL,
            bvps_vnd REAL
        )
        """
    )
    cur.execute("CREATE TABLE stock_price_history (symbol TEXT, time TEXT, close REAL)")
    cur.execute(
        """
        CREATE TABLE events (
            id TEXT PRIMARY KEY,
            symbol TEXT,
            event_list_code TEXT,
            value REAL,
            exright_date TEXT,
            record_date TEXT,
            public_date TEXT
        )
        """
    )

    # Annual fundamentals FY2021..FY2025
    eps = {2021: 1000.0, 2022: 1100.0, 2023: 1210.0, 2024: 1331.0, 2025: 1464.1}
    bvps = {y: 5000.0 for y in eps.keys()}
    for y in sorted(eps.keys()):
        cur.execute(
            "INSERT INTO financial_ratios (symbol, year, quarter, eps_vnd, bvps_vnd) VALUES (?, ?, NULL, ?, ?)",
            ("AAA", y, eps[y], bvps[y]),
        )

    # Year-end prices chosen so P/E is constant 10x (close quoted in thousand VND)
    for y in sorted(eps.keys()):
        close_k = (eps[y] * 10.0) / 1000.0
        cur.execute(
            "INSERT INTO stock_price_history (symbol, time, close) VALUES (?, ?, ?)",
            ("AAA", f"{y}-12-31", close_k),
        )

    # Cash dividends 100 VND per share in FY2022..FY2025
    for y in [2022, 2023, 2024, 2025]:
        cur.execute(
            "INSERT INTO events (id, symbol, event_list_code, value, exright_date, record_date, public_date) VALUES (?, ?, 'DIV', ?, ?, ?, ?)",
            (f"DIV-{y}", "AAA", 100.0, f"{y}-06-01", f"{y}-06-02", f"{y}-05-20"),
        )

    conn.commit()
    conn.close()

    ts = get_valuation_timeseries(db_path, "AAA", years=5)
    assert ts["symbol"] == "AAA"
    assert ts["period"]["start_year"] == 2021
    assert ts["period"]["end_year"] == 2025
    assert ts["years"] == [2021, 2022, 2023, 2024, 2025]
    assert len(ts["series"]) == 5

    pe_end = [pt["valuation"]["pe_end"] for pt in ts["series"]]
    assert all(v is not None for v in pe_end)
    assert all(abs(v - 10.0) < 1e-9 for v in pe_end)

    # P/E band percentiles should all be ~10 for a constant series
    assert abs(ts["bands"]["pe_end"]["p25"] - 10.0) < 1e-9
    assert abs(ts["bands"]["pe_end"]["p50"] - 10.0) < 1e-9
    assert abs(ts["bands"]["pe_end"]["p75"] - 10.0) < 1e-9
    assert ts["bands"]["pe_end"]["n"] == 5

    # Fair price from P/E P50 in FY2021: eps=1000, multiple=10 => 10k
    fair_2021 = ts["fair_lines"][0]["fair_close"]["pe_p50"]
    assert abs(fair_2021 - 10.0) < 1e-9

    decomp = get_return_decomposition(db_path, "AAA", horizon_years=4)
    assert decomp["symbol"] == "AAA"
    assert decomp["period"]["start_year"] == 2021
    assert decomp["period"]["end_year"] == 2025
    assert decomp["period"]["intervals_used"] == 4

    # EPS growth: 1000 -> 1464.1 (10% compounded over 4 years)
    expected_eps_log = math.log(1464.1 / 1000.0)
    assert abs(decomp["components_log_pct"]["eps_growth"] - round(expected_eps_log * 100.0, 2)) < 1e-9

    # P/E rerating should be ~0 (constant P/E)
    assert abs(decomp["components_log_pct"]["pe_rerating"]) < 1e-9

    # Dividend component should be positive
    assert decomp["components_log_pct"]["cash_dividends"] > 0

