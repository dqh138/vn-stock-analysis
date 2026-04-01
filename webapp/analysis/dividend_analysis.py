"""
Dividend Analysis Module - Phân tích Cổ tức

Module này cung cấp các công cụ phân tích cổ tức cho công ty niêm yết:
- Tính toán Dividend Yield (Tỷ suất cổ tức)
- Phân tích tính nhất quán của cổ tức (Consistency)
- Tính toán tốc độ tăng trưởng cổ tức (CAGR)
- Lịch sử trả cổ tức qua các năm

Author: Financial Analysis Engine
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime
from pathlib import Path


_PRICE_TABLE_CANDIDATES: Tuple[str, ...] = ("stock_price_history", "price_history", "stock_prices")
_PRICE_TIME_COL_CANDIDATES: Tuple[str, ...] = ("time", "date", "trading_date", "day", "datetime", "timestamp")
_STOCK_PRICE_HISTORY_CLOSE_SCALE_VND: float = 1000.0  # `stock_price_history.close` stored in thousand VND


def _get_table_columns(cursor: Any, table: str) -> List[str]:
    cursor.execute(
        "SELECT column_name AS name FROM information_schema.columns WHERE table_name = %s AND table_schema = 'public'",
        (table,)
    )
    return [row["name"] for row in cursor.fetchall()]


def _fetch_latest_close_price(
    cursor: Any,
    *,
    symbol: str,
    available_tables: List[str],
) -> Optional[Tuple[float, str, str]]:
    """
    Returns (close_price, table_name, time_col_name) or None if not found.
    """
    available = set(available_tables)
    for table in _PRICE_TABLE_CANDIDATES:
        if table not in available:
            continue
        try:
            cols = set(_get_table_columns(cursor, table))
            if "symbol" not in cols or "close" not in cols:
                continue
            time_col = next((c for c in _PRICE_TIME_COL_CANDIDATES if c in cols), None)
            if not time_col:
                continue

            cursor.execute(
                f"""
                    SELECT close
                    FROM {table}
                    WHERE symbol = %s
                    ORDER BY {time_col} DESC
                    LIMIT 1
                """,
                (symbol,),
            )
            row = cursor.fetchone()
            if row and row["close"] is not None:
                return float(row["close"]), table, time_col
        except Exception:
            continue
    return None


def analyze_dividend(
    symbol: str,
    db_path=None,
    current_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Phân tích cổ tức toàn diện cho một mã cổ phiếu

    Args:
        symbol: Mã cổ phiếu (VD: VCB, HPG)
        db_path: Ignored; connection comes from DATABASE_URL
        current_price: Giá hiện tại (nếu None, sẽ lấy từ DB)

    Returns:
        Dict chứa:
        - dividend_yield: Tỷ suất cổ tức hiện tại (%)
        - payout_ratio: Tỷ lệ trả cổ tức (%)
        - consistency: Thông tin nhất quán (số năm, điểm số, đánh giá)
        - history: Danh sách lịch sử cổ tức theo năm
        - growth_rate: Tốc độ tăng trưởng CAGR (%)
        - next_ex_date: Ngày chia cổ tức gần nhất
    """
    from .. import db as _db
    with _db.connect() as conn:
        with conn.cursor() as cursor:

            result = {
                "symbol": symbol,
                "dividend_yield": None,
                "payout_ratio": None,
                "consistency": {
                    "years_with_dividend": 0,
                    "total_years": 0,
                    "score": 0.0,
                    "rating": "Không có dữ liệu"
                },
                "history": [],
                "growth_rate": None,
                "next_ex_date": None
            }

            try:
                # Check available tables
                cursor.execute("""
                    SELECT table_name AS name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                available_tables = [row["name"] for row in cursor.fetchall()]

                # 1. Lấy giá hiện tại (try different table names)
                if current_price is None:
                    fetched = _fetch_latest_close_price(cursor, symbol=symbol, available_tables=available_tables)
                    if fetched:
                        current_price, price_table, _time_col = fetched
                        result["price_source"] = price_table
                    else:
                        result["price_source"] = None

                # Normalize price to VND for yield computations.
                # `current_price` is the latest close from DB; for `stock_price_history` it is stored in thousand VND.
                price_vnd: Optional[float] = None
                if current_price is not None and current_price > 0:
                    if result.get("price_source") == "stock_price_history":
                        price_vnd = float(current_price) * _STOCK_PRICE_HISTORY_CLOSE_SCALE_VND
                    else:
                        price_vnd = float(current_price)
                result["current_price"] = current_price
                result["current_price_vnd"] = price_vnd

                # 2. Lấy lịch sử cổ tức từ bảng events (nếu có)
                dividend_events = []

                # Try events table first
                if "events" in available_tables:
                    try:
                        cursor.execute("""
                            SELECT
                                EXTRACT(YEAR FROM issue_date::date)::text as year,
                                issue_date,
                                exright_date,
                                ratio,
                                value
                            FROM events
                            WHERE symbol = %s
                              AND event_list_code = 'DIV'
                              AND issue_date IS NOT NULL
                            ORDER BY issue_date DESC
                        """, (symbol,))
                        dividend_events = cursor.fetchall()
                    except Exception:
                        pass

                # If no events, try dividend_history table
                if not dividend_events and "dividend_history" in available_tables:
                    try:
                        cursor.execute("""
                            SELECT
                                year,
                                dividend_amount,
                                ex_date
                            FROM dividend_history
                            WHERE symbol = %s
                            ORDER BY year DESC
                        """, (symbol,))
                        dividend_events = cursor.fetchall()
                    except Exception:
                        pass

                # 3. Xử lý dữ liệu cổ tức
                if dividend_events:
                    # Nhóm theo năm
                    yearly_dividends = {}
                    for event in dividend_events:
                        year = event["year"]
                        # Lấy giá trị cổ tức (ưu tiên value, nếu không có thì tính từ ratio)
                        try:
                            dividend_amount = event["value"] if event["value"] else 0
                        except (KeyError, TypeError):
                            dividend_amount = 0

                        if year not in yearly_dividends:
                            ex_date = None
                            try:
                                ex_date = event["exright_date"] if event["exright_date"] else event["ex_date"] if event["ex_date"] else None
                            except (KeyError, TypeError):
                                ex_date = None
                            yearly_dividends[year] = {
                                "amount": 0,
                                "count": 0,
                                "ex_date": ex_date
                            }

                        yearly_dividends[year]["amount"] += dividend_amount
                        yearly_dividends[year]["count"] += 1

                    # Chuyển thành list và sắp xếp
                    dividend_history = []
                    for year in sorted(yearly_dividends.keys(), reverse=True):
                        data = yearly_dividends[year]
                        dividend_per_share = data["amount"]

                        # Tính yield nếu có giá
                        yield_val = None
                        if price_vnd and price_vnd > 0:
                            yield_val = (dividend_per_share / price_vnd) if dividend_per_share else 0

                        dividend_history.append({
                            "year": int(year),
                            "dividend_per_share": dividend_per_share,
                            "times_paid": data["count"],
                            "yield": round(yield_val, 4) if yield_val is not None else None,
                            "ex_date": data.get("ex_date")
                        })

                    result["history"] = dividend_history

                    # 4. Tính toán các chỉ số
                    if dividend_history:
                        # Lấy năm gần nhất
                        latest_div = dividend_history[0]
                        latest_yearly_dividend = latest_div["dividend_per_share"]

                        # Dividend Yield
                        if price_vnd and price_vnd > 0 and latest_yearly_dividend:
                            result["dividend_yield"] = round(latest_yearly_dividend / price_vnd, 4)

                        # Consistency (tính nhất quán)
                        years_with_div = len([d for d in dividend_history if d["dividend_per_share"] > 0])
                        total_years = len(dividend_history)
                        consistency_score = years_with_div / total_years if total_years > 0 else 0

                        result["consistency"] = {
                            "years_with_dividend": years_with_div,
                            "total_years": total_years,
                            "score": round(consistency_score, 2),
                            "rating": _get_consistency_rating(consistency_score)
                        }

                        # Growth Rate (CAGR)
                        if len(dividend_history) >= 2:
                            # Lấy dividend của năm cũ nhất và mới nhất
                            oldest_div = dividend_history[-1]["dividend_per_share"]
                            newest_div = dividend_history[0]["dividend_per_share"]

                            if oldest_div and newest_div and oldest_div > 0:
                                years_diff = dividend_history[0]["year"] - dividend_history[-1]["year"]
                                if years_diff > 0:
                                    cagr = ((newest_div / oldest_div) ** (1 / years_diff)) - 1
                                    result["growth_rate"] = round(cagr, 4)

                        # Next Ex-Date
                        if latest_div and latest_div.get("ex_date"):
                            result["next_ex_date"] = latest_div["ex_date"]

                # 5. Lấy payout_ratio từ financial_ratios
                if "financial_ratios" in available_tables:
                    cursor.execute("""
                        SELECT dividend_payout_ratio
                        FROM financial_ratios
                        WHERE symbol = %s
                          AND quarter IS NULL
                        ORDER BY year DESC
                        LIMIT 1
                    """, (symbol,))

                    payout_row = cursor.fetchone()
                    if payout_row and payout_row["dividend_payout_ratio"] is not None:
                        result["payout_ratio"] = round(float(payout_row["dividend_payout_ratio"]), 4)

            except Exception as e:
                # Log lỗi nhưng vẫn trả về kết quả
                result["error"] = str(e)

    return result


def _get_consistency_rating(score: float) -> str:
    """
    Đánh giá mức độ nhất quán của cổ tức

    Args:
        score: Điểm số (0-1)

    Returns:
        Xếp hạng bằng tiếng Việt
    """
    if score >= 0.9:
        return "Rất tốt"
    elif score >= 0.75:
        return "Tốt"
    elif score >= 0.5:
        return "Trung bình"
    elif score >= 0.25:
        return "Thấp"
    else:
        return "Không đều"


def calculate_dividend_yield(dividend_per_share: float, stock_price: float) -> Optional[float]:
    """
    Tính toán Dividend Yield

    Args:
        dividend_per_share: Cổ tức trên mỗi cổ phiếu (VND)
        stock_price: Giá cổ phiếu (VND)

    Returns:
        Dividend Yield (%)
    """
    if not dividend_per_share or not stock_price or stock_price == 0:
        return None
    return round(dividend_per_share / stock_price, 4)


def calculate_dividend_cagr(dividends: List[float], years: List[int]) -> Optional[float]:
    """
    Tính toán tốc độ tăng trưởng cổ tức (CAGR)

    Args:
        dividends: Danh sách cổ tức theo các năm
        years: Danh sách các năm tương ứng

    Returns:
        CAGR (%)
    """
    if len(dividends) < 2 or len(years) < 2:
        return None

    oldest_div = dividends[-1]
    newest_div = dividends[0]

    if not oldest_div or not newest_div or oldest_div <= 0:
        return None

    years_diff = years[0] - years[-1]
    if years_diff <= 0:
        return None

    cagr = ((newest_div / oldest_div) ** (1 / years_diff)) - 1
    return round(cagr, 4)


def get_dividend_consistency_score(dividend_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tính toán điểm nhất quán của cổ tức

    Args:
        dividend_history: Danh sách lịch sử cổ tức

    Returns:
        Dict chứa điểm số và đánh giá
    """
    if not dividend_history:
        return {
            "years_with_dividend": 0,
            "total_years": 0,
            "score": 0.0,
            "rating": "Không có dữ liệu"
        }

    years_with_div = len([d for d in dividend_history if d.get("dividend_per_share", 0) > 0])
    total_years = len(dividend_history)
    score = years_with_div / total_years if total_years > 0 else 0

    return {
        "years_with_dividend": years_with_div,
        "total_years": total_years,
        "score": round(score, 2),
        "rating": _get_consistency_rating(score)
    }


def format_dividend_amount(amount: float) -> str:
    """
    Format số tiền cổ tức sang dạng đọc được

    Args:
        amount: Số tiền cổ tức (VND)

    Returns:
        Chuỗi format (VD: "1,500 ₫", "2.5k ₫")
    """
    if amount is None:
        return "N/A"

    if amount >= 1_000_000:
        return f"{amount/1_000_000:.1f}M ₫"
    elif amount >= 1_000:
        return f"{amount/1_000:.1f}k ₫"
    else:
        return f"{amount:.0f} ₫"


def get_dividend_rating_label(dividend_yield: Optional[float]) -> Dict[str, Any]:
    """
    Đánh giá mức độ hấp dẫn của dividend yield

    Args:
        dividend_yield: Tỷ suất cổ tức (%)

    Returns:
        Dict containing label và color class
    """
    if dividend_yield is None:
        return {"label": "N/A", "class": "neutral"}

    if dividend_yield >= 0.08:  # >= 8%
        return {"label": "Rất cao", "class": "excellent"}
    elif dividend_yield >= 0.06:  # >= 6%
        return {"label": "Cao", "class": "good"}
    elif dividend_yield >= 0.04:  # >= 4%
        return {"label": "Trung bình", "class": "neutral"}
    elif dividend_yield >= 0.02:  # >= 2%
        return {"label": "Thấp", "class": "low"}
    else:
        return {"label": "Rất thấp", "class": "very-low"}
