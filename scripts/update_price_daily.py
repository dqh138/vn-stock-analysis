"""
Crawl giá cổ phiếu hôm nay từ vnstock và upsert vào Supabase.
Chạy mỗi ngày sau 16:00 (sau khi thị trường đóng cửa).

Usage:
    python scripts/update_price_daily.py
    python scripts/update_price_daily.py --date 2026-04-01
    python scripts/update_price_daily.py --days 5   # crawl 5 ngày gần nhất
"""
import os
import sys
import time
import argparse
import logging
from datetime import datetime, timedelta, date

import psycopg2
import psycopg2.extras

try:
    from vnstock import Quote
except ImportError:
    print("Cần cài đặt vnstock: pip install vnstock")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    # Fallback: đọc từ .env.local nếu có
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env.local")
    if os.path.exists(env_file):
        for line in open(env_file):
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                DATABASE_URL = line.split("=", 1)[1].strip().strip('"').strip("'")

if not DATABASE_URL:
    print("Cần set DATABASE_URL environment variable.")
    print("Ví dụ: set DATABASE_URL=postgresql://...")
    sys.exit(1)

RATE_LIMIT_DELAY = 1.2  # giây giữa các API call


def is_business_day(d: date) -> bool:
    return d.weekday() < 5  # 0=Mon, 4=Fri


def get_all_symbols(conn) -> list:
    with conn.cursor() as cur:
        cur.execute("SELECT ticker FROM stocks WHERE ticker ~ '^[A-Z]{3}$' ORDER BY ticker")
        return [r["ticker"] for r in cur.fetchall()]


def fetch_price(symbol: str, start: str, end: str) -> list:
    """Fetch OHLCV từ vnstock, trả về list of dicts."""
    try:
        q = Quote(source='vci', symbol=symbol)
        df = q.history(start=start, end=end, interval="1D")
        if df is None or df.empty:
            return []
        df = df.reset_index(drop=True)
        # Normalize columns
        col_map = {
            "time": "time", "date": "time",
            "open": "open", "high": "high", "low": "low",
            "close": "close", "volume": "volume",
        }
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        required = {"time", "close"}
        if not required.issubset(df.columns):
            return []
        # Convert time to string YYYY-MM-DD
        df["time"] = df["time"].astype(str).str[:10]
        # Scale: vnstock returns actual VND, DB stores in thousands VND
        for col in ("open", "high", "low", "close"):
            if col in df.columns:
                df[col] = df[col] / 1000.0
        rows = []
        for _, row in df.iterrows():
            rows.append({
                "symbol": symbol,
                "time": row["time"],
                "open": float(row["open"]) if "open" in row and row["open"] == row["open"] else None,
                "high": float(row["high"]) if "high" in row and row["high"] == row["high"] else None,
                "low": float(row["low"]) if "low" in row and row["low"] == row["low"] else None,
                "close": float(row["close"]) if row["close"] == row["close"] else None,
                "volume": int(row["volume"]) if "volume" in row and row["volume"] == row["volume"] else None,
            })
        return rows
    except Exception as e:
        log.warning(f"  {symbol}: fetch error — {e}")
        return []


def upsert_prices(conn, rows: list):
    if not rows:
        return 0
    sql = """
        INSERT INTO stock_price_history (symbol, time, open, high, low, close, volume)
        VALUES (%(symbol)s, %(time)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
        ON CONFLICT (symbol, time) DO UPDATE SET
            open   = EXCLUDED.open,
            high   = EXCLUDED.high,
            low    = EXCLUDED.low,
            close  = EXCLUDED.close,
            volume = EXCLUDED.volume
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, rows, page_size=500)
    conn.commit()
    return len(rows)


def ensure_unique_index(conn):
    """Tạo unique index (symbol, time) nếu chưa có — cần cho ON CONFLICT."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'stock_price_history'
              AND indexname = 'uix_price_symbol_time'
        """)
        if not cur.fetchone():
            log.info("Tạo unique index (symbol, time) trên stock_price_history...")
            cur.execute("""
                CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uix_price_symbol_time
                ON stock_price_history (symbol, time)
            """)
            log.info("Done.")
    conn.commit()


def run(target_dates: list):
    log.info(f"Kết nối Supabase...")
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
        sslmode="require",
        connect_timeout=20,
    )
    conn.autocommit = False

    ensure_unique_index(conn)

    symbols = get_all_symbols(conn)
    log.info(f"Tìm thấy {len(symbols):,} mã cổ phiếu")

    start_date = min(target_dates)
    end_date = max(target_dates)
    log.info(f"Crawl từ {start_date} đến {end_date}")

    total_inserted = 0
    for i, symbol in enumerate(symbols, 1):
        rows = fetch_price(symbol, start_date, end_date)
        # Chỉ giữ rows thuộc target_dates
        rows = [r for r in rows if r["time"] in target_dates]
        if rows:
            n = upsert_prices(conn, rows)
            total_inserted += n
            log.info(f"[{i}/{len(symbols)}] {symbol}: {n} rows upserted")
        else:
            log.debug(f"[{i}/{len(symbols)}] {symbol}: no data")
        time.sleep(RATE_LIMIT_DELAY)

    conn.close()
    log.info(f"Hoàn tất. Tổng: {total_inserted:,} rows upserted.")


def main():
    parser = argparse.ArgumentParser(description="Cập nhật giá cổ phiếu vào Supabase")
    parser.add_argument("--date", help="Ngày cụ thể YYYY-MM-DD (mặc định: hôm nay)")
    parser.add_argument("--days", type=int, default=1, help="Số ngày gần nhất cần crawl (mặc định: 1)")
    args = parser.parse_args()

    if args.date:
        target_dates = [args.date]
    else:
        today = date.today()
        target_dates = []
        d = today
        collected = 0
        while collected < args.days:
            if is_business_day(d):
                target_dates.append(d.strftime("%Y-%m-%d"))
                collected += 1
            d -= timedelta(days=1)
        target_dates = sorted(set(target_dates))

    log.info(f"Target dates: {target_dates}")
    run(target_dates)


if __name__ == "__main__":
    main()
