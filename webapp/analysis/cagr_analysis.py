"""
CAGR Analysis Module - Tỷ lệ Tăng trưởng Kép Hàng năm

Provides Compound Annual Growth Rate analysis for:
- Revenue (Doanh thu)
- Net Profit (Lợi nhuận sau thuế)
- Total Assets (Tổng tài sản)
- Equity (Vốn chủ sở hữu)

Author: Financial Analysis Engine
Version: 1.0.0
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from .annual_selector import (
    get_financial_ratios_annual,
    select_balance_sheet_annual,
    select_income_statement_annual,
)

def calculate_cagr(
    start_value: float,
    end_value: float,
    years: int
) -> Optional[float]:
    """
    Calculate Compound Annual Growth Rate (CAGR).

    Args:
        start_value: Starting value
        end_value: Ending value
        years: Number of years

    Returns:
        CAGR as decimal (e.g., 0.15 for 15%) or None if calculation fails
    """
    if start_value is None or end_value is None or years is None:
        return None

    if years <= 0:
        return None

    try:
        if start_value <= 0 or end_value <= 0:
            return None

        cagr = (end_value / start_value) ** (1 / years) - 1
        return cagr
    except (ZeroDivisionError, ValueError, OverflowError):
        return None


def get_cagr_rating(cagr_value: float, metric_type: str = "general") -> Tuple[str, str]:
    """
    Get CAGR rating and description based on value and metric type.

    Args:
        cagr_value: CAGR value as decimal (0.15 = 15%)
        metric_type: Type of metric (revenue, profit, assets, equity)

    Returns:
        Tuple of (rating, description)
    """
    if cagr_value is None:
        return "unknown", "Không có dữ liệu"

    # Convert to percentage for comparison
    pct = cagr_value * 100

    if cagr_value < 0:
        return "negative", f"Giảm {abs(pct):.1f}% mỗi năm"
    elif pct < 5:
        return "low", f"Tăng trưởng thấp ({pct:.1f}%)"
    elif pct < 10:
        return "moderate", f"Tăng trưởng khá ({pct:.1f}%)"
    elif pct < 20:
        return "good", f"Tăng trưởng tốt ({pct:.1f}%)"
    elif pct < 30:
        return "strong", f"Tăng trưởng mạnh ({pct:.1f}%)"
    else:
        return "excellent", f"Tăng trưởng xuất sắc ({pct:.1f}%)"


def analyze_cagr(
    db_path=None,
    symbol: str = "",
    years: int = 5
) -> Dict[str, Any]:
    """
    Perform comprehensive CAGR analysis.

    Args:
        db_path: Ignored; connection comes from DATABASE_URL
        symbol: Stock symbol
        years: Number of years to analyze (default: 5)

    Returns:
        Dictionary with CAGR analysis results
    """
    from .. import db as _db
    with _db.connect() as conn:
        with conn.cursor() as cursor:

            # Get the latest year available
            cursor.execute("""
                SELECT MAX(year) as latest_year
                FROM financial_ratios
                WHERE symbol = %s AND quarter IS NULL
            """, (symbol,))

            row = cursor.fetchone()
            latest_year = row['latest_year'] if row else None

            if latest_year is None:
                return {
                    "symbol": symbol,
                    "error": "No data available for symbol"
                }

            end_year = latest_year
            start_year = end_year - years

            # Build annual, deterministic series per year.
            # NOTE: statement tables may contain many duplicated quarter=NULL rows; use annual_selector.
            data_by_year: Dict[int, Dict[str, Any]] = {}
            for y in range(start_year, end_year + 1):
                ratios_row = get_financial_ratios_annual(conn, symbol, y)
                income_row = select_income_statement_annual(conn, symbol, y)
                balance_row = select_balance_sheet_annual(conn, symbol, y, financial_ratios_row=ratios_row)

                # Prefer net_revenue over revenue (DB often stores revenue as negative credits)
                revenue = income_row.get("net_revenue")
                if revenue is None:
                    revenue = income_row.get("revenue")

                # Prefer parent-company profit if available
                net_profit = income_row.get("net_profit_parent_company")
                if net_profit is None:
                    net_profit = income_row.get("net_profit")

                data = {
                    "revenue": revenue,
                    "net_profit": net_profit,
                    "total_assets": balance_row.get("total_assets") if balance_row else None,
                    "equity_total": balance_row.get("equity_total") if balance_row else None,
                }

                # Keep the year only if we have at least one value
                if any(v is not None for v in data.values()):
                    data_by_year[y] = data

    years_data = sorted(data_by_year.keys())
    if len(years_data) < 2:
        return {
            "symbol": symbol,
            "error": "Insufficient data for CAGR calculation",
            "data_points": len(years_data),
        }

    # Helpers: metric-specific start/end (CAGR requires positive values)
    def series(metric_key: str) -> List[Tuple[int, float]]:
        out: List[Tuple[int, float]] = []
        for y in years_data:
            v = data_by_year[y].get(metric_key)
            try:
                v_f = float(v) if v is not None else None
            except (TypeError, ValueError):
                v_f = None
            if v_f is not None and v_f > 0:
                out.append((y, v_f))
        return out

    # Calculate CAGR for each metric
    results: Dict[str, Any] = {
        "symbol": symbol,
        "period": {
            "start_year": years_data[0],
            "end_year": years_data[-1],
            "years": years_data[-1] - years_data[0]
        },
        "metrics": {}
    }

    # Revenue CAGR
    revenue_series = series("revenue")
    revenue_cagr = None
    revenue_start = revenue_end = None
    revenue_years = None
    if len(revenue_series) >= 2:
        revenue_start = revenue_series[0]
        revenue_end = revenue_series[-1]
        revenue_years = revenue_end[0] - revenue_start[0]
        revenue_cagr = calculate_cagr(revenue_start[1], revenue_end[1], revenue_years) if revenue_years > 0 else None
    rating, description = get_cagr_rating(revenue_cagr, "revenue")
    results["metrics"]["revenue"] = {
        "name": "Doanh thu",
        "cagr": revenue_cagr,
        "cagr_percent": round(revenue_cagr * 100, 2) if revenue_cagr is not None else None,
        "rating": rating,
        "description": description,
        "start_year": revenue_start[0] if revenue_start else None,
        "end_year": revenue_end[0] if revenue_end else None,
        "years": revenue_years,
        "start_value": revenue_start[1] if revenue_start else None,
        "end_value": revenue_end[1] if revenue_end else None,
    }

    # Net Profit CAGR
    profit_series = series("net_profit")
    profit_cagr = None
    profit_start = profit_end = None
    profit_years = None
    if len(profit_series) >= 2:
        profit_start = profit_series[0]
        profit_end = profit_series[-1]
        profit_years = profit_end[0] - profit_start[0]
        profit_cagr = calculate_cagr(profit_start[1], profit_end[1], profit_years) if profit_years > 0 else None
    rating, description = get_cagr_rating(profit_cagr, "profit")
    results["metrics"]["net_profit"] = {
        "name": "Lợi nhuận sau thuế",
        "cagr": profit_cagr,
        "cagr_percent": round(profit_cagr * 100, 2) if profit_cagr is not None else None,
        "rating": rating,
        "description": description,
        "start_year": profit_start[0] if profit_start else None,
        "end_year": profit_end[0] if profit_end else None,
        "years": profit_years,
        "start_value": profit_start[1] if profit_start else None,
        "end_value": profit_end[1] if profit_end else None,
    }

    # Total Assets CAGR
    assets_series = series("total_assets")
    assets_cagr = None
    assets_start = assets_end = None
    assets_years = None
    if len(assets_series) >= 2:
        assets_start = assets_series[0]
        assets_end = assets_series[-1]
        assets_years = assets_end[0] - assets_start[0]
        assets_cagr = calculate_cagr(assets_start[1], assets_end[1], assets_years) if assets_years > 0 else None
    rating, description = get_cagr_rating(assets_cagr, "assets")
    results["metrics"]["total_assets"] = {
        "name": "Tổng tài sản",
        "cagr": assets_cagr,
        "cagr_percent": round(assets_cagr * 100, 2) if assets_cagr is not None else None,
        "rating": rating,
        "description": description,
        "start_year": assets_start[0] if assets_start else None,
        "end_year": assets_end[0] if assets_end else None,
        "years": assets_years,
        "start_value": assets_start[1] if assets_start else None,
        "end_value": assets_end[1] if assets_end else None,
    }

    # Equity CAGR
    equity_series = series("equity_total")
    equity_cagr = None
    equity_start = equity_end = None
    equity_years = None
    if len(equity_series) >= 2:
        equity_start = equity_series[0]
        equity_end = equity_series[-1]
        equity_years = equity_end[0] - equity_start[0]
        equity_cagr = calculate_cagr(equity_start[1], equity_end[1], equity_years) if equity_years > 0 else None
    rating, description = get_cagr_rating(equity_cagr, "equity")
    results["metrics"]["equity_total"] = {
        "name": "Vốn chủ sở hữu",
        "cagr": equity_cagr,
        "cagr_percent": round(equity_cagr * 100, 2) if equity_cagr is not None else None,
        "rating": rating,
        "description": description,
        "start_year": equity_start[0] if equity_start else None,
        "end_year": equity_end[0] if equity_end else None,
        "years": equity_years,
        "start_value": equity_start[1] if equity_start else None,
        "end_value": equity_end[1] if equity_end else None,
    }

    # Historical data for chart
    results["historical_data"] = []
    for year in years_data:
        data = data_by_year[year]
        results["historical_data"].append({
            "year": year,
            "revenue": data['revenue'],
            "net_profit": data['net_profit'],
            "total_assets": data['total_assets'],
            "equity_total": data['equity_total']
        })

    # Overall assessment
    results["overall_assessment"] = _generate_overall_assessment(results["metrics"])

    return results


def _generate_overall_assessment(metrics: Dict) -> Dict[str, Any]:
    """
    Generate overall CAGR assessment.
    """
    valid_cagrs = [
        m['cagr'] for m in metrics.values()
        if m['cagr'] is not None
    ]

    if not valid_cagrs:
        return {
            "rating": "unknown",
            "summary": "Không đủ dữ liệu để đánh giá"
        }

    avg_cagr = sum(valid_cagrs) / len(valid_cagrs)

    # Count positive growths
    positive_count = sum(1 for c in valid_cagrs if c > 0)
    growth_ratio = positive_count / len(valid_cagrs)

    if avg_cagr >= 0.15 and growth_ratio >= 0.75:
        rating = "excellent"
        summary = "Tăng trưởng xuất sắc trên nhiều chỉ số"
    elif avg_cagr >= 0.10 and growth_ratio >= 0.5:
        rating = "good"
        summary = "Tăng trưởng tốt và đồng đều"
    elif avg_cagr >= 0.05:
        rating = "moderate"
        summary = "Tăng trưởng ở mức trung bình"
    elif avg_cagr >= 0:
        rating = "low"
        summary = "Tăng trưởng thấp"
    else:
        rating = "negative"
        summary = "Có xu hướng giảm"

    return {
        "rating": rating,
        "summary": summary,
        "average_cagr": round(avg_cagr * 100, 2),
        "positive_growth_ratio": round(growth_ratio * 100, 1)
    }
