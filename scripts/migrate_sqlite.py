"""
SQLite → Supabase migration script for baocaotaichinh- data.

Usage:
    pip install supabase python-dotenv
    python scripts/migrate_sqlite.py --db D:/Projects/baocaotaichinh-/vietnam_stocks.db

Set environment variables in .env.local or export them:
    NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
    SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
"""

import argparse
import json
import os
import sqlite3
import sys
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv(".env.local")
except ImportError:
    pass

try:
    from supabase import create_client
except ImportError:
    print("ERROR: Run:  pip install supabase python-dotenv")
    sys.exit(1)

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_SIZE = 500


def rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# Columns that exist in SQLite but are auto-managed by Supabase — skip them.
_SKIP_COLS = {"id", "created_at", "updated_at"}


def clean(row: dict) -> dict:
    """Strip auto-managed columns, coerce empty strings to NULL, parse data_json."""
    result = {}
    for k, v in row.items():
        if k in _SKIP_COLS:
            continue
        if v is None or v == "":
            result[k] = None
        elif k == "data_json" and isinstance(v, str):
            try:
                result[k] = json.loads(v)
            except Exception:
                result[k] = None
        else:
            result[k] = v
    return result


# Explicit column allowlists derived from 001_financial_tables.sql
# Any SQLite column NOT in this set is silently dropped.
_TABLE_COLS: dict[str, set[str]] = {
    "stocks": {
        "ticker","organ_name","en_organ_name","organ_short_name","en_organ_short_name",
        "com_type_code","status","listed_date","delisted_date","company_id","tax_code","isin",
    },
    "stock_exchange": {"ticker","exchange","id","type"},
    "stock_industry": {
        "ticker","icb_code","icb_name2","en_icb_name2","icb_name3","en_icb_name3",
        "icb_name4","en_icb_name4","icb_code1","icb_code2","icb_code3","icb_code4",
    },
    "stock_index": {"ticker","index_code"},
    "balance_sheet": {
        "symbol","period","year","quarter",
        "asset_current","cash_and_equivalents","short_term_investments","accounts_receivable",
        "inventory","current_assets_other","asset_non_current","long_term_receivables",
        "fixed_assets","long_term_investments","non_current_assets_other","total_assets",
        "liabilities_current","liabilities_non_current","liabilities_total","equity_total",
        "share_capital","retained_earnings","equity_other","total_equity_and_liabilities",
        "data_json","source",
    },
    "income_statement": {
        "symbol","period","year","quarter",
        "revenue","revenue_growth","net_revenue","cost_of_goods_sold","gross_profit",
        "financial_income","financial_expense","net_financial_income","operating_expenses",
        "operating_profit","other_income","profit_before_tax","corporate_income_tax",
        "deferred_income_tax","net_profit","net_profit_parent_company",
        "net_profit_parent_company_post","minority_interest","profit_growth","eps",
        "data_json","source",
    },
    "cash_flow_statement": {
        "symbol","period","year","quarter",
        "profit_before_tax","depreciation_fixed_assets","provisions",
        "increase_decrease_receivables","increase_decrease_inventory","increase_decrease_payables",
        "increase_decrease_prepaid_expenses","interest_expense_paid","corporate_income_tax_paid",
        "net_cash_flow_from_operating_activities","purchase_of_fixed_assets",
        "proceeds_from_disposal_of_fixed_assets","loans_to_other_entities","collection_of_loans",
        "purchase_of_investments","proceeds_from_investments","dividends_received",
        "net_cash_flow_from_investing_activities","proceeds_from_share_issuance",
        "repayment_of_borrowings","dividends_paid","net_cash_flow_from_financing_activities",
        "net_cash_flow_period","cash_beginning_of_period","cash_end_of_period",
        "data_json","source",
    },
    "financial_ratios": {
        "symbol","year","quarter",
        "price_to_book","price_to_earnings","price_to_sales","price_to_cash_flow",
        "ev_to_ebitda","ev_to_ebit","eps_vnd","bvps_vnd","market_cap_billions",
        "shares_outstanding_millions","gross_margin","ebit_margin","net_profit_margin",
        "roe","roa","roic","asset_turnover","fixed_asset_turnover","days_sales_outstanding",
        "days_inventory_outstanding","days_payable_outstanding","cash_conversion_cycle",
        "inventory_turnover","debt_to_equity","debt_to_equity_adjusted","fixed_assets_to_equity",
        "equity_to_charter_capital","current_ratio","quick_ratio","cash_ratio",
        "interest_coverage_ratio","financial_leverage","beta","dividend_payout_ratio",
        "ebitda_billions","ebit_billions",
    },
    "stock_price_history": {"symbol","time","open","high","low","close","volume"},
}


def get_supabase_columns(table: str) -> set[str]:
    return _TABLE_COLS.get(table, set())


def upsert_batch(table: str, rows: list[dict], conflict_cols: str, allowed_cols: set[str]) -> int:
    if not rows:
        return 0
    cleaned = [clean(r) for r in rows]
    if allowed_cols:
        cleaned = [{k: v for k, v in r.items() if k in allowed_cols} for r in cleaned]
    res = supabase.table(table).upsert(cleaned, on_conflict=conflict_cols, returning="minimal").execute()
    return len(cleaned)


def migrate_table(
    conn: sqlite3.Connection,
    sqlite_table: str,
    supabase_table: str,
    conflict_cols: str,
    query: str | None = None,
    total_label: str | None = None,
) -> None:
    allowed_cols = get_supabase_columns(supabase_table)

    cur = conn.cursor()
    sql = query or f"SELECT * FROM {sqlite_table}"
    cur.execute(sql)

    batch: list[dict] = []
    total = 0

    label = total_label or supabase_table
    print(f"  Migrating {label}...", end="", flush=True)

    while True:
        chunk = cur.fetchmany(BATCH_SIZE)
        if not chunk:
            break
        columns = [d[0] for d in cur.description]
        rows = [dict(zip(columns, row)) for row in chunk]
        batch.extend(rows)

        if len(batch) >= BATCH_SIZE:
            upsert_batch(supabase_table, batch, conflict_cols, allowed_cols)
            total += len(batch)
            print(f" {total}", end="", flush=True)
            batch = []

    if batch:
        upsert_batch(supabase_table, batch, conflict_cols, allowed_cols)
        total += len(batch)

    print(f" → {total} rows ✓")


def main(db_path: str) -> None:
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    print(f"Connected to {db_path}")
    print()

    # ── Core company tables ──────────────────────────────────────────────────
    migrate_table(conn, "stocks", "stocks", "ticker")
    migrate_table(conn, "stock_exchange", "stock_exchange", "ticker,exchange")
    migrate_table(conn, "stock_industry", "stock_industry", "ticker,icb_code")

    # stock_index (optional, skip if table doesn't exist)
    try:
        migrate_table(conn, "stock_index", "stock_index", "ticker,index_code")
    except Exception as e:
        print(f"  Skipped stock_index: {e}")

    # ── Financial statements ─────────────────────────────────────────────────
    # Annual rows: quarter IS NULL
    # Quarterly rows: quarter IN (1,2,3,4)

    migrate_table(
        conn,
        "balance_sheet",
        "balance_sheet",
        "symbol,year,quarter",
        query="SELECT * FROM balance_sheet WHERE quarter IS NULL",
        total_label="balance_sheet (annual)",
    )
    migrate_table(
        conn,
        "balance_sheet",
        "balance_sheet",
        "symbol,year,quarter",
        query="SELECT * FROM balance_sheet WHERE quarter IS NOT NULL",
        total_label="balance_sheet (quarterly)",
    )

    migrate_table(
        conn,
        "income_statement",
        "income_statement",
        "symbol,year,quarter",
        query="SELECT * FROM income_statement WHERE quarter IS NULL",
        total_label="income_statement (annual)",
    )
    migrate_table(
        conn,
        "income_statement",
        "income_statement",
        "symbol,year,quarter",
        query="SELECT * FROM income_statement WHERE quarter IS NOT NULL",
        total_label="income_statement (quarterly)",
    )

    migrate_table(
        conn,
        "cash_flow_statement",
        "cash_flow_statement",
        "symbol,year,quarter",
        query="SELECT * FROM cash_flow_statement WHERE quarter IS NULL",
        total_label="cash_flow_statement (annual)",
    )
    migrate_table(
        conn,
        "cash_flow_statement",
        "cash_flow_statement",
        "symbol,year,quarter",
        query="SELECT * FROM cash_flow_statement WHERE quarter IS NOT NULL",
        total_label="cash_flow_statement (quarterly)",
    )

    migrate_table(
        conn,
        "financial_ratios",
        "financial_ratios",
        "symbol,year,quarter",
    )

    # ── Price history (large — migrate last) ────────────────────────────────
    answer = input("\nMigrate stock_price_history? (needed for risk analysis) [y/N]: ").strip().lower()
    if answer == "y":
        migrate_table(
            conn,
            "stock_price_history",
            "stock_price_history",
            "symbol,time",
        )

    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite → Supabase")
    parser.add_argument(
        "--db",
        default="D:/Projects/baocaotaichinh-/vietnam_stocks.db",
        help="Path to the SQLite database file",
    )
    args = parser.parse_args()
    main(args.db)
