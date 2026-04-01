from __future__ import annotations

import sqlite3
from pathlib import Path

from .dividend_analysis import analyze_dividend


def _create_min_dividend_db(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE stock_price_history (
          id INTEGER PRIMARY KEY,
          symbol TEXT NOT NULL,
          time DATE NOT NULL,
          close REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE events (
          id TEXT PRIMARY KEY,
          symbol TEXT,
          issue_date TEXT,
          exright_date TEXT,
          event_list_code TEXT,
          ratio REAL,
          value REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE financial_ratios (
          id INTEGER PRIMARY KEY,
          symbol TEXT,
          year INTEGER,
          quarter INTEGER,
          dividend_payout_ratio REAL
        )
        """
    )

    # Price stored as thousand VND.
    cur.execute(
        "INSERT INTO stock_price_history(symbol, time, close) VALUES (?,?,?)",
        ("AAA", "2026-02-13", 100.0),
    )

    # Cash dividend: 1,000 VND/share.
    cur.execute(
        "INSERT INTO events(id, symbol, issue_date, exright_date, event_list_code, ratio, value) VALUES (?,?,?,?,?,?,?)",
        ("div1", "AAA", "2025-12-20", "2025-12-01", "DIV", 0.1, 1000.0),
    )

    cur.execute(
        "INSERT INTO financial_ratios(symbol, year, quarter, dividend_payout_ratio) VALUES (?,?,?,?)",
        ("AAA", 2025, None, 0.1),
    )

    conn.commit()
    conn.close()


def test_analyze_dividend_computes_yield_with_stock_price_history_time(tmp_path: Path) -> None:
    db_path = tmp_path / "dividend.db"
    _create_min_dividend_db(db_path)

    out = analyze_dividend(symbol="AAA", db_path=db_path)

    assert out["history"], "Expected dividend history from events.DIV"
    assert out["current_price"] == 100.0
    assert out["current_price_vnd"] == 100000.0

    # 1,000 / 100,000 = 1%
    assert out["dividend_yield"] == 0.01
    assert out["history"][0]["yield"] == 0.01
    assert out["next_ex_date"] == "2025-12-01"


def test_analyze_dividend_no_events_keeps_yield_none(tmp_path: Path) -> None:
    db_path = tmp_path / "no_events.db"
    _create_min_dividend_db(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.execute("DELETE FROM events")
    conn.commit()
    conn.close()

    out = analyze_dividend(symbol="AAA", db_path=db_path)
    assert out["history"] == []
    assert out["dividend_yield"] is None
    assert out["growth_rate"] is None
    assert out["payout_ratio"] == 0.1

