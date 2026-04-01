import sqlite3
from pathlib import Path

from webapp.analysis.ttm_analysis import get_ttm_series


def test_get_ttm_series_requires_consecutive_quarters(tmp_path):
    db_path = Path(tmp_path) / "test.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE income_statement (
            symbol TEXT,
            year INTEGER,
            quarter INTEGER,
            net_revenue REAL,
            revenue REAL,
            gross_profit REAL,
            operating_profit REAL,
            net_profit_parent_company REAL,
            net_profit REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE cash_flow_statement (
            symbol TEXT,
            year INTEGER,
            quarter INTEGER,
            net_cash_from_operating_activities REAL,
            purchase_purchase_fixed_assets REAL
        )
        """
    )

    # 8 consecutive quarters: 2024Q1..Q4, 2025Q1..Q4
    for y, q in [(2024, 1), (2024, 2), (2024, 3), (2024, 4), (2025, 1), (2025, 2), (2025, 3), (2025, 4)]:
        nr = 1000.0 + (y - 2024) * 100.0 + q * 10.0
        gp = nr * 0.3
        op = nr * 0.15
        np = nr * 0.08
        cur.execute(
            """
            INSERT INTO income_statement (
                symbol, year, quarter, net_revenue, revenue, gross_profit, operating_profit,
                net_profit_parent_company, net_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("AAA", y, q, nr, None, gp, op, np, np),
        )

        cfo = nr * 0.10
        capex = -(nr * 0.05)
        cur.execute(
            """
            INSERT INTO cash_flow_statement (
                symbol, year, quarter, net_cash_from_operating_activities, purchase_purchase_fixed_assets
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("AAA", y, q, cfo, capex),
        )

    conn.commit()
    conn.close()

    out = get_ttm_series(db_path, "AAA", count=4)
    assert out["symbol"] == "AAA"
    assert out["status"] in {"OK", "PENDING_QUARTER_DATA"}
    pts = out["points"]
    assert len(pts) == 4
    assert pts[-1]["period"] == "Q4 2025"

    # Latest point should be OK with 4-quarter sums
    latest = pts[-1]
    assert latest["status"] == "OK"
    assert latest["coverage"]["consecutive"] is True

    # Revenue TTM should be sum of net_revenue of 2025Q1..Q4
    expected_rev = sum(
        1000.0 + (2025 - 2024) * 100.0 + q * 10.0 for q in [1, 2, 3, 4]
    )
    assert abs(latest["ttm"]["revenue"] - expected_rev) < 1e-9

    # FCF should be CFO - abs(CapEx)
    expected_cfo = expected_rev * 0.10
    expected_capex = sum(-(1000.0 + 100.0 + q * 10.0) * 0.05 for q in [1, 2, 3, 4])
    assert abs(latest["ttm"]["cfo"] - expected_cfo) < 1e-9
    assert abs(latest["ttm"]["capex"] - expected_capex) < 1e-9
    assert abs(latest["ttm"]["fcf"] - (expected_cfo - abs(expected_capex))) < 1e-9

