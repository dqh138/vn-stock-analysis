"""
Technology Industry Analysis Module for Vietnamese Tech Companies

Analyzes technology-specific metrics including:
- R&D intensity (with proxy calculations)
- Employee productivity
- Asset-light ratio
- Profitability metrics
- Scalability score
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TechMetric:
    """Container for a single metric with rating"""
    value: Optional[float]
    value_formatted: str
    rating: str
    rating_vi: str
    note: Optional[str] = None


def _safe_divide(numerator: Optional[float], denominator: Optional[float], default: float = 0.0) -> Optional[float]:
    """Safely divide two numbers, handling None and zero"""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _format_percent(value: Optional[float], decimals: int = 1) -> str:
    """Format a value as percentage"""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}%"


def _format_ratio(value: Optional[float], decimals: int = 2) -> str:
    """Format a value as ratio"""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}x"


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_sales(income_statement: Dict[str, Any]) -> Optional[float]:
    """
    Get a consistent sales/revenue value from income statement.

    DB convention notes:
    - Non-banks: `revenue` can be negative (credit sign), while `net_revenue` is positive.
    - Banks: `net_revenue` is often NULL; use `revenue`.
    """
    net_revenue = _to_float(income_statement.get("net_revenue"))
    if net_revenue is not None and net_revenue != 0:
        return net_revenue

    revenue = _to_float(income_statement.get("revenue"))
    if revenue is None:
        return None
    return abs(revenue) if revenue < 0 else revenue


def _expense_magnitude(value: Any) -> Optional[float]:
    """Expense fields in DB are often negative; use magnitude for ratios."""
    value_f = _to_float(value)
    if value_f is None:
        return None
    return abs(value_f)


def _get_rd_rating(rd_ratio: Optional[float]) -> Tuple[str, str]:
    """Get R&D intensity rating"""
    if rd_ratio is None:
        return "N/A", "Không có dữ liệu"
    if rd_ratio > 5:
        return "Innovation Leader", "Dẫn đầu đổi mới sáng tạo"
    elif rd_ratio > 2:
        return "Active", "Đầu tư R&D tích cực"
    else:
        return "Low", "Đầu tư R&D thấp"


def _get_margin_rating(margin: Optional[float], high_threshold: float = 30, good_threshold: float = 20) -> Tuple[str, str]:
    """Get margin rating"""
    if margin is None:
        return "N/A", "Không có dữ liệu"
    if margin > high_threshold:
        return "Strong", "Mạnh"
    elif margin > good_threshold:
        return "Good", "Khá"
    else:
        return "Low", "Thấp"


def _get_roic_rating(roic: Optional[float]) -> Tuple[str, str]:
    """Get ROIC rating"""
    if roic is None:
        return "N/A", "Không có dữ liệu"
    if roic > 20:
        return "Excellent", "Xuất sắc"
    elif roic > 12:
        return "Good", "Tốt"
    else:
        return "Low", "Thấp"


def _calculate_rd_intensity(
    income_statement: Dict[str, Any],
    balance_sheet: Dict[str, Any]
) -> Tuple[Optional[float], TechMetric]:
    """
    Calculate R&D/Revenue ratio

    Note: Vietnamese tech companies often bundle R&D in COGS/Admin expenses.
    We use operating_expenses as a proxy when R&D is not separately disclosed.
    """
    revenue = _get_sales(income_statement)
    operating_expenses = _expense_magnitude(income_statement.get("operating_expenses"))

    # Try direct R&D if available (some companies disclose separately)
    # For Vietnamese companies, we typically use operating_expenses as proxy
    rd_proxy = operating_expenses

    rd_ratio = _safe_divide(
        rd_proxy,
        revenue,
        default=None
    )

    if rd_ratio is not None:
        rd_ratio_percent = rd_ratio * 100
        rating, rating_vi = _get_rd_rating(rd_ratio_percent)

        return rd_ratio_percent, TechMetric(
            value=rd_ratio_percent,
            value_formatted=_format_percent(rd_ratio_percent),
            rating=rating,
            rating_vi=rating_vi,
            note="Proxy: Chi phí hoạt động/Doanh thu (R&D thường gộp trong COGS/Admin)"
        )

    return None, TechMetric(
        value=None,
        value_formatted="N/A",
        rating="N/A",
        rating_vi="Không có dữ liệu"
    )


def _calculate_employee_productivity(
    income_statement: Dict[str, Any],
    balance_sheet: Dict[str, Any]
) -> Tuple[Optional[float], TechMetric]:
    """
    Calculate employee productivity proxy

    Formula: Revenue / (Operating Expenses) * adjustment_factor
    This is a proxy for revenue per employee when headcount data is unavailable
    """
    revenue = _get_sales(income_statement)
    operating_expenses = _expense_magnitude(income_statement.get("operating_expenses"))

    # Calculate productivity ratio (revenue generated per unit of operating expense)
    productivity = _safe_divide(revenue, operating_expenses)

    if productivity is not None:
        # Higher is better - more revenue generated per expense unit
        if productivity > 3:
            rating, rating_vi = "Excellent", "Xuất sắc"
        elif productivity > 2:
            rating, rating_vi = "Good", "Tốt"
        elif productivity > 1.5:
            rating, rating_vi = "Average", "Trung bình"
        else:
            rating, rating_vi = "Low", "Thấp"

        return productivity, TechMetric(
            value=productivity,
            value_formatted=_format_ratio(productivity),
            rating=rating,
            rating_vi=rating_vi,
            note="Proxy: Doanh thu/Chi phí hoạt động (cao hơn = hiệu suất tốt hơn)"
        )

    return None, TechMetric(
        value=None,
        value_formatted="N/A",
        rating="N/A",
        rating_vi="Không có dữ liệu"
    )


def _calculate_asset_light_ratio(
    balance_sheet: Dict[str, Any]
) -> Tuple[Optional[float], TechMetric]:
    """
    Calculate asset-light ratio

    Formula: (Total Assets - Fixed Assets) / Total Assets
    Tech companies typically > 70% (less capital intensive)
    """
    total_assets = balance_sheet.get("total_assets")
    fixed_assets = balance_sheet.get("fixed_assets")

    if total_assets and fixed_assets:
        intangible_assets = total_assets - fixed_assets
        asset_light_ratio = (intangible_assets / total_assets) * 100 if total_assets != 0 else None

        if asset_light_ratio is not None:
            if asset_light_ratio > 70:
                rating, rating_vi = "Highly Scalable", "Độ mở rộng cao"
            elif asset_light_ratio > 50:
                rating, rating_vi = "Moderate", "Trung bình"
            else:
                rating, rating_vi = "Capital Intensive", "Thâm dụng vốn"

            return asset_light_ratio, TechMetric(
                value=asset_light_ratio,
                value_formatted=_format_percent(asset_light_ratio),
                rating=rating,
                rating_vi=rating_vi,
                note="Tỷ lệ tài sản phi vật lý trên tổng tài sản (cao hơn = mô hình kinh doanh nhẹ hơn)"
            )

    return None, TechMetric(
        value=None,
        value_formatted="N/A",
        rating="N/A",
        rating_vi="Không có dữ liệu"
    )


def _calculate_gross_margin(
    financial_ratios: Dict[str, Any],
    income_statement: Dict[str, Any]
) -> Tuple[Optional[float], TechMetric]:
    """
    Calculate and rate gross margin

    Software/services: 30-50%+
    Hardware/integration: 15-25%
    """
    # Try to get from ratios first
    gross_margin = financial_ratios.get("gross_margin")

    if gross_margin is None:
        # Calculate from income statement
        revenue = _get_sales(income_statement)
        gross_profit = income_statement.get("gross_profit")

        if revenue and revenue != 0 and gross_profit is not None:
            gross_margin = gross_profit / revenue  # Result is decimal

    # Normalize to percentage: if value < 1, it's decimal (0.30 = 30%)
    if gross_margin is not None:
        gross_margin_pct = gross_margin * 100 if gross_margin < 1 else gross_margin
        rating, rating_vi = _get_margin_rating(gross_margin_pct, high_threshold=30, good_threshold=20)

        return gross_margin_pct, TechMetric(
            value=gross_margin_pct,
            value_formatted=_format_percent(gross_margin_pct),
            rating=rating,
            rating_vi=rating_vi,
            note="Biên lợi nhuận gộp: Phần mềm/dịch vụ > 30%, Phần cứng 15-25%"
        )

    return None, TechMetric(
        value=None,
        value_formatted="N/A",
        rating="N/A",
        rating_vi="Không có dữ liệu"
    )


def _calculate_operating_margin(
    financial_ratios: Dict[str, Any],
    income_statement: Dict[str, Any]
) -> Tuple[Optional[float], TechMetric]:
    """
    Calculate and rate operating margin

    Rating: > 15% = Excellent, 8-15% = Good, < 8% = Low
    """
    # Try to get from ratios first (ebit_margin is similar)
    operating_margin = financial_ratios.get("ebit_margin")

    if operating_margin is None:
        # Calculate from income statement
        revenue = _get_sales(income_statement)
        operating_profit = income_statement.get("operating_profit")

        if revenue and revenue != 0 and operating_profit is not None:
            operating_margin = operating_profit / revenue  # Result is decimal

    # Normalize to percentage: if value < 1, it's decimal (0.15 = 15%)
    if operating_margin is not None:
        operating_margin_pct = operating_margin * 100 if operating_margin < 1 else operating_margin
        rating, rating_vi = _get_margin_rating(operating_margin_pct, high_threshold=15, good_threshold=8)

        return operating_margin_pct, TechMetric(
            value=operating_margin_pct,
            value_formatted=_format_percent(operating_margin_pct),
            rating=rating,
            rating_vi=rating_vi,
            note="Biên lợi nhuận hoạt động"
        )

    return None, TechMetric(
        value=None,
        value_formatted="N/A",
        rating="N/A",
        rating_vi="Không có dữ liệu"
    )


def _calculate_roic(
    financial_ratios: Dict[str, Any],
    income_statement: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    cash_flow: Dict[str, Any]
) -> Tuple[Optional[float], TechMetric]:
    """
    Calculate Return on Invested Capital (ROIC)

    Formula: NOPAT / (Debt + Equity - Cash)
    Note: Using interest-bearing debt (short + long term), not total liabilities
    Rating: > 20% = Excellent, 12-20% = Good, < 12% = Low
    """
    # Try to get from ratios first
    roic = financial_ratios.get("roic")
    # Normalize DB decimals to percent when needed (0.18 -> 18%)
    if roic is not None:
        try:
            roic_f = float(roic)
            roic = roic_f * 100 if roic_f < 1 else roic_f
        except (TypeError, ValueError):
            roic = None

    if roic is None:
        # Calculate ROIC manually
        net_profit = income_statement.get("net_profit") or income_statement.get("net_profit_parent_company")
        corporate_income_tax = income_statement.get("corporate_income_tax")
        tax_expense = _expense_magnitude(corporate_income_tax)
        profit_before_tax = income_statement.get("profit_before_tax")

        # NOPAT = Net Profit + Tax (to get pre-tax profit adjusted)
        # Or use operating profit * (1 - tax rate)
        operating_profit = income_statement.get("operating_profit")

        if operating_profit and tax_expense:
            denom = profit_before_tax if profit_before_tax not in (None, 0) else (operating_profit + tax_expense)
            tax_rate = _safe_divide(tax_expense, denom)
            if tax_rate is not None and 0 <= tax_rate < 1:
                nopat = operating_profit * (1 - tax_rate)

                # Invested Capital = Interest-bearing Debt + Equity - Cash
                # Use short_term_debt + long_term_debt (not total liabilities)
                short_term_debt = balance_sheet.get("short_term_debt") or balance_sheet.get("debt_current") or 0
                long_term_debt = balance_sheet.get("long_term_debt") or balance_sheet.get("debt_non_current") or 0
                debt = short_term_debt + long_term_debt

                # Fallback: if no debt fields, use liabilities_total as proxy (less accurate)
                if debt == 0:
                    debt = balance_sheet.get("liabilities_total") or balance_sheet.get("total_liabilities") or 0

                equity = balance_sheet.get("equity_total") or balance_sheet.get("total_equity")
                cash = balance_sheet.get("cash_and_equivalents")

                if equity:
                    invested_capital = (debt + equity) - (cash or 0)
                    if invested_capital != 0 and invested_capital > 0:
                        roic = (nopat / invested_capital) * 100

    if roic is not None:
        rating, rating_vi = _get_roic_rating(roic)

        return roic, TechMetric(
            value=roic,
            value_formatted=_format_percent(roic),
            rating=rating,
            rating_vi=rating_vi,
            note="Tỷ suất sinh lời trên vốn đầu tư (ước tính)"
        )

    return None, TechMetric(
        value=None,
        value_formatted="N/A",
        rating="N/A",
        rating_vi="Không có dữ liệu"
    )


def _calculate_asset_turnover(
    financial_ratios: Dict[str, Any],
    income_statement: Dict[str, Any],
    balance_sheet: Dict[str, Any]
) -> Tuple[Optional[float], TechMetric]:
    """
    Calculate asset turnover ratio

    Higher is better for tech companies (efficient asset utilization)
    """
    # Try to get from ratios first
    asset_turnover = financial_ratios.get("asset_turnover")

    if asset_turnover is None:
        # Calculate manually
        revenue = _get_sales(income_statement)
        total_assets = balance_sheet.get("total_assets")

        if total_assets and total_assets != 0:
            asset_turnover = revenue / total_assets

    if asset_turnover is not None:
        if asset_turnover > 1.0:
            rating, rating_vi = "Excellent", "Xuất sắc"
        elif asset_turnover > 0.7:
            rating, rating_vi = "Good", "Tốt"
        elif asset_turnover > 0.5:
            rating, rating_vi = "Average", "Trung bình"
        else:
            rating, rating_vi = "Low", "Thấp"

        return asset_turnover, TechMetric(
            value=asset_turnover,
            value_formatted=_format_ratio(asset_turnover),
            rating=rating,
            rating_vi=rating_vi,
            note="Vòng quay tổng tài sản (cao hơn = hiệu quả sử dụng tài sản tốt hơn)"
        )

    return None, TechMetric(
        value=None,
        value_formatted="N/A",
        rating="N/A",
        rating_vi="Không có dữ liệu"
    )


def _calculate_revenue_growth(
    financial_ratios: Dict[str, Any],
    income_statement: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[float], TechMetric]:
    """
    Get revenue growth rate
    """
    revenue_growth = financial_ratios.get("revenue_growth")
    if revenue_growth is None and income_statement:
        revenue_growth = income_statement.get("revenue_growth")

    if revenue_growth is not None:
        if revenue_growth > 20:
            rating, rating_vi = "High Growth", "Tăng trưởng cao"
        elif revenue_growth > 10:
            rating, rating_vi = "Moderate Growth", "Tăng trưởng trung bình"
        elif revenue_growth > 0:
            rating, rating_vi = "Low Growth", "Tăng trưởng thấp"
        else:
            rating, rating_vi = "Declining", "Giảm"

        return revenue_growth, TechMetric(
            value=revenue_growth,
            value_formatted=_format_percent(revenue_growth),
            rating=rating,
            rating_vi=rating_vi,
            note="Tốc độ tăng trưởng doanh thu"
        )

    return None, TechMetric(
        value=None,
        value_formatted="N/A",
        rating="N/A",
        rating_vi="Không có dữ liệu"
    )


def _calculate_scalability_score(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate Tech Scalability Score

    Components:
    - Profitability (30%): Gross Margin, Operating Margin, ROIC
    - Efficiency (25%): Asset Turnover, Asset-Light Ratio
    - Innovation (25%): R&D intensity (proxy)
    - Growth (20%): Revenue Growth, Margin Expansion
    """
    scores = {}

    # Profitability Score (30% weight)
    profit_metrics = []
    if metrics.get("gross_margin", {}).get("value") is not None:
        gm = metrics["gross_margin"]["value"]
        profit_metrics.append(min(gm / 40, 1.0) * 100)  # Max 40% = 100 points

    if metrics.get("operating_margin", {}).get("value") is not None:
        om = metrics["operating_margin"]["value"]
        profit_metrics.append(min(om / 20, 1.0) * 100)  # Max 20% = 100 points

    if metrics.get("roic", {}).get("value") is not None:
        roic = metrics["roic"]["value"]
        profit_metrics.append(min(roic / 25, 1.0) * 100)  # Max 25% = 100 points

    profitability_score = sum(profit_metrics) / len(profit_metrics) if profit_metrics else None

    # Efficiency Score (25% weight)
    efficiency_metrics = []
    if metrics.get("asset_turnover", {}).get("value") is not None:
        at = metrics["asset_turnover"]["value"]
        efficiency_metrics.append(min(at / 1.5, 1.0) * 100)  # Max 1.5x = 100 points

    if metrics.get("asset_light_ratio", {}).get("value") is not None:
        alr = metrics["asset_light_ratio"]["value"]
        efficiency_metrics.append(min(alr / 80, 1.0) * 100)  # Max 80% = 100 points

    efficiency_score = sum(efficiency_metrics) / len(efficiency_metrics) if efficiency_metrics else None

    # Innovation Score (25% weight)
    innovation_metrics = []
    if metrics.get("rd_intensity", {}).get("value") is not None:
        rd = metrics["rd_intensity"]["value"]
        # Higher R&D is better, but cap at 8%
        innovation_metrics.append(min(rd / 8, 1.0) * 100)

    innovation_score = innovation_metrics[0] if innovation_metrics else None

    # Growth Score (20% weight)
    growth_metrics = []
    if metrics.get("revenue_growth", {}).get("value") is not None:
        rg = metrics["revenue_growth"]["value"]
        # Cap at 30% growth
        growth_metrics.append(min(max(rg, 0) / 30, 1.0) * 100)

    growth_score = growth_metrics[0] if growth_metrics else None

    # Calculate weighted overall score
    valid_scores = []
    if profitability_score is not None:
        valid_scores.append(("profitability", profitability_score, 30))
    if efficiency_score is not None:
        valid_scores.append(("efficiency", efficiency_score, 25))
    if innovation_score is not None:
        valid_scores.append(("innovation", innovation_score, 25))
    if growth_score is not None:
        valid_scores.append(("growth", growth_score, 20))

    if valid_scores:
        total_weight = sum(w for _, _, w in valid_scores)
        weighted_score = sum(score * weight for _, score, weight in valid_scores) / total_weight
    else:
        weighted_score = None

    # Determine overall rating
    if weighted_score is not None:
        if weighted_score >= 75:
            overall_rating = "Cao khả năng mở rộng"
            overall_rating_en = "Highly Scalable"
        elif weighted_score >= 60:
            overall_rating = "Khả năng mở rộng tốt"
            overall_rating_en = "Good Scalability"
        elif weighted_score >= 45:
            overall_rating = "Khả năng mở rộng trung bình"
            overall_rating_en = "Moderate Scalability"
        else:
            overall_rating = "Khả năng mở rộng thấp"
            overall_rating_en = "Low Scalability"
    else:
        overall_rating = "Không có dữ liệu"
        overall_rating_en = "Insufficient Data"

    return {
        "overall_score": weighted_score,
        "overall_score_formatted": f"{weighted_score:.1f}/100" if weighted_score is not None else "N/A",
        "overall_rating": overall_rating,
        "overall_rating_en": overall_rating_en,
        "components": {
            "profitability": {
                "score": profitability_score,
                "weight": 30,
                "label": "Khả năng sinh lời",
                "label_en": "Profitability"
            },
            "efficiency": {
                "score": efficiency_score,
                "weight": 25,
                "label": "Hiệu quả vận hành",
                "label_en": "Efficiency"
            },
            "innovation": {
                "score": innovation_score,
                "weight": 25,
                "label": "Đổi mới sáng tạo",
                "label_en": "Innovation"
            },
            "growth": {
                "score": growth_score,
                "weight": 20,
                "label": "Tăng trưởng",
                "label_en": "Growth"
            }
        }
    }


def analyze_technology_company(
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any],
    cash_flow: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze a technology company with tech-specific metrics

    Args:
        financial_ratios: Dict of financial ratios
        balance_sheet: Dict of balance sheet items
        income_statement: Dict of income statement items
        cash_flow: Optional dict of cash flow items

    Returns:
        Dict containing:
        - metrics: All calculated metrics with ratings
        - scalability_score: Overall tech scalability score
        - summary: Key insights
    """
    if cash_flow is None:
        cash_flow = {}

    # Calculate all metrics
    rd_value, rd_metric = _calculate_rd_intensity(income_statement, balance_sheet)
    productivity_value, productivity_metric = _calculate_employee_productivity(income_statement, balance_sheet)
    asset_light_value, asset_light_metric = _calculate_asset_light_ratio(balance_sheet)
    gross_margin_value, gross_margin_metric = _calculate_gross_margin(financial_ratios, income_statement)
    operating_margin_value, operating_margin_metric = _calculate_operating_margin(financial_ratios, income_statement)
    roic_value, roic_metric = _calculate_roic(financial_ratios, income_statement, balance_sheet, cash_flow)
    asset_turnover_value, asset_turnover_metric = _calculate_asset_turnover(financial_ratios, income_statement, balance_sheet)
    revenue_growth_value, revenue_growth_metric = _calculate_revenue_growth(financial_ratios, income_statement)

    # Build metrics dict
    metrics = {
        "rd_intensity": {
            "value": rd_value,
            "label": "R&D/Doanh thu",
            "label_en": "R&D/Revenue",
            "value_formatted": rd_metric.value_formatted,
            "rating": rd_metric.rating,
            "rating_vi": rd_metric.rating_vi,
            "note": rd_metric.note
        },
        "employee_productivity": {
            "value": productivity_value,
            "label": "Hiệu suất nhân viên",
            "label_en": "Employee Productivity",
            "value_formatted": productivity_metric.value_formatted,
            "rating": productivity_metric.rating,
            "rating_vi": productivity_metric.rating_vi,
            "note": productivity_metric.note
        },
        "asset_light_ratio": {
            "value": asset_light_value,
            "label": "Tỷ lệ tài sản nhẹ",
            "label_en": "Asset-Light Ratio",
            "value_formatted": asset_light_metric.value_formatted,
            "rating": asset_light_metric.rating,
            "rating_vi": asset_light_metric.rating_vi,
            "note": asset_light_metric.note
        },
        "gross_margin": {
            "value": gross_margin_value,
            "label": "Biên lợi nhuận gộp",
            "label_en": "Gross Margin",
            "value_formatted": gross_margin_metric.value_formatted,
            "rating": gross_margin_metric.rating,
            "rating_vi": gross_margin_metric.rating_vi,
            "note": gross_margin_metric.note
        },
        "operating_margin": {
            "value": operating_margin_value,
            "label": "Biên lợi nhuận hoạt động",
            "label_en": "Operating Margin",
            "value_formatted": operating_margin_metric.value_formatted,
            "rating": operating_margin_metric.rating,
            "rating_vi": operating_margin_metric.rating_vi,
            "note": operating_margin_metric.note
        },
        "roic": {
            "value": roic_value,
            "label": "ROIC",
            "label_en": "Return on Invested Capital",
            "value_formatted": roic_metric.value_formatted,
            "rating": roic_metric.rating,
            "rating_vi": roic_metric.rating_vi,
            "note": roic_metric.note
        },
        "asset_turnover": {
            "value": asset_turnover_value,
            "label": "Vòng quay tài sản",
            "label_en": "Asset Turnover",
            "value_formatted": asset_turnover_metric.value_formatted,
            "rating": asset_turnover_metric.rating,
            "rating_vi": asset_turnover_metric.rating_vi,
            "note": asset_turnover_metric.note
        },
        "revenue_growth": {
            "value": revenue_growth_value,
            "label": "Tăng trưởng doanh thu",
            "label_en": "Revenue Growth",
            "value_formatted": revenue_growth_metric.value_formatted,
            "rating": revenue_growth_metric.rating,
            "rating_vi": revenue_growth_metric.rating_vi,
            "note": revenue_growth_metric.note
        }
    }

    # Calculate scalability score
    scalability_score = _calculate_scalability_score(metrics)

    # Generate summary
    summary_points = []

    if rd_value and rd_value > 3:
        summary_points.append(f"Đầu tư mạnh vào R&D ({rd_value:.1f}% của doanh thu)")

    if gross_margin_value and gross_margin_value > 30:
        summary_points.append(f"Biên lợi nhuận gộp cao ({gross_margin_value:.1f}%) - lợi thế cạnh tranh bền vững")
    elif gross_margin_value and gross_margin_value < 20:
        summary_points.append(f"Biên lợi nhuận gộp thấp ({gross_margin_value:.1f}%) - cần cải thiện hiệu quả")

    if asset_light_value and asset_light_value > 70:
        summary_points.append(f"Mô hình kinh doanh tài sản nhẹ ({asset_light_value:.1f}%) - khả năng mở rộng cao")

    if roic_value and roic_value > 15:
        summary_points.append(f"ROIC xuất sắc ({roic_value:.1f}%) - sử dụng vốn hiệu quả")

    if revenue_growth_value and revenue_growth_value > 15:
        summary_points.append(f"Tăng trưởng doanh thu mạnh ({revenue_growth_value:.1f}%)")
    elif revenue_growth_value and revenue_growth_value < 5:
        summary_points.append(f"Tăng trưởng chậm ({revenue_growth_value:.1f}%) - cần tìm động lực mới")

    if scalability_score["overall_score"] is not None:
        summary_points.append(f"Điểm khả năng mở rộng: {scalability_score['overall_score_formatted']} ({scalability_score['overall_rating']})")

    return {
        "metrics": metrics,
        "scalability_score": scalability_score,
        "summary": summary_points if summary_points else ["Không đủ dữ liệu để đánh giá"]
    }


# Example usage and testing
if __name__ == "__main__":
    # Example data for a Vietnamese tech company
    example_ratios = {
        "gross_margin": 35.5,
        "roic": 18.2,
        "asset_turnover": 0.85,
        "revenue_growth": 22.5
    }

    example_balance_sheet = {
        "total_assets": 1000000000000,
        "fixed_assets": 250000000000,
        "cash_and_equivalents": 150000000000,
        "liabilities_total": 400000000000,
        "equity_total": 600000000000
    }

    example_income_statement = {
        "revenue": 800000000000,
        "net_revenue": 750000000000,
        "operating_expenses": 250000000000,
        "gross_profit": 300000000000,
        "operating_profit": 120000000000,
        "net_profit": 90000000000,
        "corporate_income_tax": 30000000000
    }

    example_cash_flow = {
        "net_cash_from_operating_activities": 95000000000
    }

    result = analyze_technology_company(
        example_ratios,
        example_balance_sheet,
        example_income_statement,
        example_cash_flow
    )

    print("Technology Analysis Results:")
    print(f"Overall Scalability Score: {result['scalability_score']['overall_score_formatted']}")
    print(f"Rating: {result['scalability_score']['overall_rating']}")
    print("\nSummary:")
    for point in result['summary']:
        print(f"  - {point}")
