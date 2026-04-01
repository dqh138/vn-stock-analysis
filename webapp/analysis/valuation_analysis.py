"""
Valuation Analysis Module

Provides advanced valuation metrics including:
- PEG Ratio (Price/Earnings-to-Growth)
- Historical percentile analysis
- Industry comparison
"""

from typing import Any, Dict, List, Optional, Tuple
import math
from pathlib import Path


def calculate_cagr(
    values: List[float],
    years: int
) -> Optional[float]:
    """
    Calculate Compound Annual Growth Rate (CAGR).

    Args:
        values: List of values (oldest to newest)
        years: Number of years

    Returns:
        CAGR as decimal (e.g., 0.15 for 15%) or None if calculation fails
    """
    if not values or len(values) < 2 or years <= 0:
        return None

    try:
        start_value = values[0]
        end_value = values[-1]

        if start_value <= 0 or end_value <= 0:
            return None

        cagr = (end_value / start_value) ** (1 / years) - 1
        return cagr
    except (ZeroDivisionError, ValueError, OverflowError):
        return None


def calculate_percentiles(
    historical_values: List[float]
) -> Dict[str, float]:
    """
    Calculate percentile distribution from historical values.

    Uses numpy-style linear interpolation method (type 7 in numpy.percentile)
    for consistency with the benchmark endpoint.

    Args:
        historical_values: List of historical values

    Returns:
        Dictionary with p5, p25, p50, p75, p95 percentiles
    """
    if not historical_values:
        return {"p5": None, "p25": None, "p50": None, "p75": None, "p95": None}

    # Filter out None values and sort
    valid_values = sorted([v for v in historical_values if v is not None])

    if not valid_values:
        return {"p5": None, "p25": None, "p50": None, "p75": None, "p95": None}

    def get_percentile(p: float) -> Optional[float]:
        """
        Get percentile value using linear interpolation method.

        This matches the method used in app.py benchmark endpoint
        for academic rigor and consistency.
        """
        if not valid_values:
            return None

        n = len(valid_values)
        if n == 1:
            return valid_values[0]

        # Calculate the index using numpy's method (linear interpolation)
        # index = (percentile / 100) * (n - 1)
        index = (p / 100.0) * (n - 1)

        # Get the integer and fractional parts
        lower_index = int(index)
        upper_index = min(lower_index + 1, n - 1)
        fraction = index - lower_index

        # Linear interpolation
        if lower_index == upper_index:
            return valid_values[lower_index]
        else:
            lower_value = valid_values[lower_index]
            upper_value = valid_values[upper_index]
            return lower_value + fraction * (upper_value - lower_value)

    return {
        "p5": get_percentile(5),
        "p25": get_percentile(25),
        "p50": get_percentile(50),
        "p75": get_percentile(75),
        "p95": get_percentile(95)
    }


def get_peg_rating(peg_ratio: float) -> Tuple[str, str]:
    """
    Get PEG ratio rating and description.

    Args:
        peg_ratio: PEG ratio value

    Returns:
        Tuple of (rating, description)
    """
    if peg_ratio is None:
        return "unknown", "Không thể tính toán"

    if peg_ratio < 0:
        return "negative", "Tăng trưởng âm"

    if peg_ratio < 1.0:
        return "very_cheap", "Rẻ - Định giá hấp dẫn"
    elif peg_ratio < 2.0:
        return "cheap", "Khá rẻ - Định giá hợp lý"
    elif peg_ratio < 3.0:
        return "fair", "Hợp lý - Định giá công bằng"
    else:
        return "expensive", "Đắt - Định giá cao"


def compare_valuation(
    company_value: Optional[float],
    industry_value: Optional[float],
    lower_is_better: bool = False
) -> Dict[str, Any]:
    """
    Compare company value to industry average.

    Args:
        company_value: Company's metric value
        industry_value: Industry average value
        lower_is_better: Whether lower values are better (e.g., P/E)

    Returns:
        Dictionary with company, industry, status
    """
    if company_value is None or industry_value is None:
        return {
            "company": None,
            "industry": None,
            "status": "unknown"
        }

    # Allow 5% tolerance
    tolerance = 0.05
    diff = (company_value - industry_value) / industry_value

    if abs(diff) <= tolerance:
        status = "similar"
    elif lower_is_better:
        status = "cheaper" if company_value < industry_value else "expensive"
    else:
        status = "better" if company_value > industry_value else "worse"

    return {
        "company": round(company_value, 2),
        "industry": round(industry_value, 2),
        "status": status
    }


def analyze_valuation(
    db_path=None,
    symbol: str = "",
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive valuation analysis.

    Args:
        db_path: Path to SQLite database
        symbol: Stock symbol
        year: Year to analyze (default: latest available)

    Returns:
        Dictionary with valuation analysis results
    """
    from .. import db as _db
    with _db.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT icb_name3 FROM stock_industry WHERE ticker = %s", (symbol,))
            industry_row = cursor.fetchone()
        industry = industry_row["icb_name3"] if industry_row else None

        if year is None:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT year FROM financial_ratios
                    WHERE symbol = %s AND quarter IS NULL
                    ORDER BY year DESC LIMIT 1
                """, (symbol,))
                year_row = cursor.fetchone()
                year = year_row["year"] if year_row else None

        if year is None:
            return {"error": "No data available for symbol"}

        cursor = conn.cursor()

    # Latest price (close is quoted in "thousand VND" for VN stocks in this DB)
    cursor.execute(
        """
        SELECT time, close
        FROM stock_price_history
        WHERE symbol = %s
        ORDER BY time DESC
        LIMIT 1
        """,
        (symbol,),
    )
    price_row = cursor.fetchone()
    close_scale_vnd = 1000.0
    latest_price = {
        "as_of": price_row["time"] if price_row else None,
        "close": float(price_row["close"]) if (price_row and price_row["close"] is not None) else None,
        "close_scale_vnd": close_scale_vnd,
        "close_vnd": (float(price_row["close"]) * close_scale_vnd) if (price_row and price_row["close"] is not None) else None,
    }

    # Get current financial ratios
    cursor.execute("""
        SELECT price_to_earnings, price_to_book, price_to_sales,
               ev_to_ebitda, eps_vnd, bvps_vnd, roe
        FROM financial_ratios
        WHERE symbol = %s AND year = %s AND quarter IS NULL
    """, (symbol, year))
    current_ratios = cursor.fetchone()

    if not current_ratios:
        return {"error": f"No financial ratios found for {symbol} in {year}"}

    # Use price_to_earnings as P/E ratio
    current_pe = current_ratios["price_to_earnings"]
    current_pb = current_ratios["price_to_book"]
    current_ps = current_ratios["price_to_sales"]
    current_ev_ebitda = current_ratios["ev_to_ebitda"]
    current_eps_vnd = current_ratios["eps_vnd"]
    current_bvps_vnd = current_ratios["bvps_vnd"]
    current_roe = current_ratios["roe"]

    # Current multiples from (latest close price / per-share fundamentals)
    current_price_vnd = latest_price.get("close_vnd")
    current_multiples = {"pe": None, "pb": None}
    if current_price_vnd is not None and current_eps_vnd is not None and current_eps_vnd > 0:
        current_multiples["pe"] = round(float(current_price_vnd) / float(current_eps_vnd), 2)
    if current_price_vnd is not None and current_bvps_vnd is not None and current_bvps_vnd > 0:
        current_multiples["pb"] = round(float(current_price_vnd) / float(current_bvps_vnd), 2)

    # ============================================================================
    # 1. Calculate PEG Ratio
    # ============================================================================

    peg_result = {
        "value": None,
        "rating": "unknown",
        "description": "Không thể tính toán"
    }

    if current_pe and current_pe > 0:
        # Academic fix: income_statement.eps is NULL in this DB; use financial_ratios.eps_vnd for earnings growth.
        cursor.execute(
            """
            SELECT year, eps_vnd
            FROM financial_ratios
            WHERE symbol = %s AND quarter IS NULL
              AND eps_vnd IS NOT NULL AND eps_vnd > 0
            ORDER BY year DESC
            LIMIT 5
            """,
            (symbol,),
        )

        eps_history = list(reversed(cursor.fetchall()))  # Oldest -> newest

        if len(eps_history) >= 2:
            first_year = eps_history[0]["year"]
            last_year = eps_history[-1]["year"]
            years_span = (last_year - first_year) if (first_year is not None and last_year is not None) else (len(eps_history) - 1)
            eps_values = [row["eps_vnd"] for row in eps_history]

            earnings_growth_rate = calculate_cagr(eps_values, years_span) if years_span and years_span > 0 else None

            if earnings_growth_rate is not None and earnings_growth_rate > 0:
                # PEG = P/E / (EPS CAGR in %)
                peg_ratio = current_pe / (earnings_growth_rate * 100)
                peg_result = {
                    "value": round(peg_ratio, 2),
                    "rating": get_peg_rating(peg_ratio)[0],
                    "description": get_peg_rating(peg_ratio)[1],
                    "earnings_growth_rate": round(earnings_growth_rate * 100, 2),
                    "pe_used": round(current_pe, 2),
                    "growth_basis": "EPS (eps_vnd) CAGR",
                }
            else:
                peg_result["description"] = "Tăng trưởng EPS không đủ hoặc âm"
        else:
            peg_result["description"] = "Không đủ dữ liệu EPS lịch sử"

    else:
        peg_result["description"] = "P/E không có hoặc âm"

    # ============================================================================
    # 2. Calculate Historical Percentiles
    # ============================================================================

    pe_percentile = {"current": round(current_pe, 2) if current_pe else None}
    pb_percentile = {"current": round(current_pb, 2) if current_pb else None}

    # Get 5-year P/E history
    cursor.execute("""
        SELECT price_to_earnings
        FROM financial_ratios
        WHERE symbol = %s AND quarter IS NULL
          AND year >= %s AND year <= %s
        ORDER BY year
    """, (symbol, year - 4, year))

    pe_history = cursor.fetchall()
    pe_values = []
    for row in pe_history:
        val = row["price_to_earnings"]
        if val is not None and val > 0:
            pe_values.append(val)

    pe_percentiles = calculate_percentiles(pe_values)
    pe_percentile.update(pe_percentiles)
    pe_percentile["n"] = len(pe_values)

    # Get 5-year P/B history
    cursor.execute("""
        SELECT price_to_book
        FROM financial_ratios
        WHERE symbol = %s AND quarter IS NULL
          AND year >= %s AND year <= %s
        ORDER BY year
    """, (symbol, year - 4, year))

    pb_history = cursor.fetchall()
    pb_values = [row["price_to_book"] for row in pb_history
                 if row["price_to_book"] is not None and row["price_to_book"] > 0]

    pb_percentiles = calculate_percentiles(pb_values)
    pb_percentile.update(pb_percentiles)
    pb_percentile["n"] = len(pb_values)

    # ============================================================================
    # 3. Industry Comparison
    # ============================================================================

    valuation_summary = {
        "pe_vs_industry": compare_valuation(current_pe, None, lower_is_better=True),
        "pb_vs_industry": compare_valuation(current_pb, None, lower_is_better=True),
        "overall": "unknown"
    }

    if industry:
        # Industry benchmark using MEDIAN (p50) for robustness (matches METHODOLOGY.md)
        # Compute each metric independently (avoid forcing a joint-validity intersection set).

        # P/E: valid when EPS > 0 (use financial_ratios.eps_vnd), P/E > 0
        cursor.execute(
            """
            SELECT f.price_to_earnings AS value
            FROM financial_ratios f
            JOIN stock_industry s ON f.symbol = s.ticker
            WHERE s.icb_name3 = %s AND f.year = %s AND f.quarter IS NULL
              AND f.price_to_earnings IS NOT NULL AND f.price_to_earnings > 0
              AND f.eps_vnd IS NOT NULL AND f.eps_vnd > 0
            """,
            (industry, year),
        )
        pe_peer_values = [row["value"] for row in cursor.fetchall() if row["value"] is not None]
        pe_median = calculate_percentiles(pe_peer_values).get("p50") if pe_peer_values else None
        if pe_median is not None:
            valuation_summary["pe_vs_industry"] = compare_valuation(current_pe, pe_median, lower_is_better=True)

        # P/B: valid when BVPS > 0 (proxy for Equity > 0), P/B > 0
        cursor.execute(
            """
            SELECT f.price_to_book AS value
            FROM financial_ratios f
            JOIN stock_industry s ON f.symbol = s.ticker
            WHERE s.icb_name3 = %s AND f.year = %s AND f.quarter IS NULL
              AND f.price_to_book IS NOT NULL AND f.price_to_book > 0
              AND f.bvps_vnd IS NOT NULL AND f.bvps_vnd > 0
            """,
            (industry, year),
        )
        pb_peer_values = [row["value"] for row in cursor.fetchall() if row["value"] is not None]
        pb_median = calculate_percentiles(pb_peer_values).get("p50") if pb_peer_values else None
        if pb_median is not None:
            valuation_summary["pb_vs_industry"] = compare_valuation(current_pb, pb_median, lower_is_better=True)

        # Determine overall valuation
        pe_status = valuation_summary["pe_vs_industry"]["status"]
        pb_status = valuation_summary["pb_vs_industry"]["status"]

        if pe_status == "unknown" or pb_status == "unknown":
            valuation_summary["overall"] = "unknown"
        elif pe_status in ["cheaper", "similar"] and pb_status in ["cheaper", "similar"]:
            valuation_summary["overall"] = "undervalued"
        elif pe_status == "expensive" and pb_status == "expensive":
            valuation_summary["overall"] = "overvalued"
        else:
            valuation_summary["overall"] = "fair"

    # ============================================================================
    # 4. Fair price heuristics (data-limited)
    # ============================================================================

    def _classify_band(current_close: Optional[float], low_close: Optional[float], high_close: Optional[float]) -> str:
        if current_close is None or low_close is None or high_close is None:
            return "unknown"
        if current_close < low_close:
            return "cheap"
        if current_close > high_close:
            return "expensive"
        return "fair"

    def _classify_point(current_close: Optional[float], fair_close: Optional[float], tolerance: float = 0.10) -> str:
        if current_close is None or fair_close is None or fair_close <= 0:
            return "unknown"
        diff = (current_close - fair_close) / fair_close
        if abs(diff) <= tolerance:
            return "fair"
        return "cheap" if diff < 0 else "expensive"

    def _fair_close(per_share_vnd: Optional[float], multiple: Optional[float]) -> Optional[float]:
        if per_share_vnd is None or multiple is None:
            return None
        try:
            per_share_vnd_f = float(per_share_vnd)
            multiple_f = float(multiple)
        except (TypeError, ValueError):
            return None
        if per_share_vnd_f <= 0 or multiple_f <= 0:
            return None
        return (per_share_vnd_f * multiple_f) / close_scale_vnd

    current_close = latest_price.get("close")

    pe_hist_p25 = pe_percentile.get("p25")
    pe_hist_p50 = pe_percentile.get("p50")
    pe_hist_p75 = pe_percentile.get("p75")
    pb_hist_p25 = pb_percentile.get("p25")
    pb_hist_p50 = pb_percentile.get("p50")
    pb_hist_p75 = pb_percentile.get("p75")

    fair_pe_hist = {
        "p25": _fair_close(current_eps_vnd, pe_hist_p25),
        "p50": _fair_close(current_eps_vnd, pe_hist_p50),
        "p75": _fair_close(current_eps_vnd, pe_hist_p75),
    }
    fair_pb_hist = {
        "p25": _fair_close(current_bvps_vnd, pb_hist_p25),
        "p50": _fair_close(current_bvps_vnd, pb_hist_p50),
        "p75": _fair_close(current_bvps_vnd, pb_hist_p75),
    }

    # Industry medians already computed in valuation_summary (rounded), but keep raw medians if available.
    pe_industry_median = None
    pb_industry_median = None
    if valuation_summary.get("pe_vs_industry", {}).get("industry") is not None:
        pe_industry_median = float(valuation_summary["pe_vs_industry"]["industry"])
    if valuation_summary.get("pb_vs_industry", {}).get("industry") is not None:
        pb_industry_median = float(valuation_summary["pb_vs_industry"]["industry"])

    fair_pe_industry = _fair_close(current_eps_vnd, pe_industry_median)
    fair_pb_industry = _fair_close(current_bvps_vnd, pb_industry_median)

    # Graham Number: sqrt(22.5 * EPS * BVPS) (heuristic, requires positive EPS & BVPS)
    graham_close = None
    if current_eps_vnd is not None and current_bvps_vnd is not None and current_eps_vnd > 0 and current_bvps_vnd > 0:
        try:
            graham_vnd = math.sqrt(22.5 * float(current_eps_vnd) * float(current_bvps_vnd))
            graham_close = graham_vnd / close_scale_vnd
        except (ValueError, OverflowError):
            graham_close = None

    fair_price = {
        "pe_hist": {
            "fair_close": {
                "p25": round(fair_pe_hist["p25"], 2) if fair_pe_hist["p25"] is not None else None,
                "p50": round(fair_pe_hist["p50"], 2) if fair_pe_hist["p50"] is not None else None,
                "p75": round(fair_pe_hist["p75"], 2) if fair_pe_hist["p75"] is not None else None,
            },
            "status": _classify_band(current_close, fair_pe_hist["p25"], fair_pe_hist["p75"]),
        },
        "pb_hist": {
            "fair_close": {
                "p25": round(fair_pb_hist["p25"], 2) if fair_pb_hist["p25"] is not None else None,
                "p50": round(fair_pb_hist["p50"], 2) if fair_pb_hist["p50"] is not None else None,
                "p75": round(fair_pb_hist["p75"], 2) if fair_pb_hist["p75"] is not None else None,
            },
            "status": _classify_band(current_close, fair_pb_hist["p25"], fair_pb_hist["p75"]),
        },
        "pe_industry": {
            "fair_close": round(fair_pe_industry, 2) if fair_pe_industry is not None else None,
            "status": _classify_point(current_close, fair_pe_industry),
        },
        "pb_industry": {
            "fair_close": round(fair_pb_industry, 2) if fair_pb_industry is not None else None,
            "status": _classify_point(current_close, fair_pb_industry),
        },
        "graham_number": {
            "fair_close": round(graham_close, 2) if graham_close is not None else None,
            "status": _classify_point(current_close, graham_close),
        },
    }

    # ============================================================================
    # 5. Build Result
    # ============================================================================

    return {
        "symbol": symbol,
        "year": year,
        "industry": industry,
        "price": latest_price,
        "fundamentals_used": {
            "eps_vnd": round(float(current_eps_vnd), 2) if current_eps_vnd is not None else None,
            "bvps_vnd": round(float(current_bvps_vnd), 2) if current_bvps_vnd is not None else None,
            "roe": round(float(current_roe), 6) if current_roe is not None else None,
        },
        "multiples_current": current_multiples,
        "peg_ratio": peg_result,
        "pe_percentile": pe_percentile,
        "pb_percentile": pb_percentile,
        "valuation_summary": valuation_summary,
        "fair_price": fair_price,
    }


def get_valuation_summary_text(overall_status: str) -> str:
    """
    Get Vietnamese description for overall valuation status.

    Args:
        overall_status: Overall valuation status

    Returns:
        Vietnamese description
    """
    status_map = {
        "undervalued": "Định giá thấp - Tiềm năng tăng trưởng",
        "fair": "Định giá hợp lý - Giá công bằng",
        "overvalued": "Định giá cao - Cần thận trọng",
        "unknown": "Không đủ dữ liệu để đánh giá"
    }
    return status_map.get(overall_status, "Không xác định")
