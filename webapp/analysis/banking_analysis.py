"""
Banking Industry Analysis Module for Vietnamese Financial Analysis Webapp

This module provides banking-specific financial metrics and health scoring
tailored for Vietnamese banks (VCB, TCB, MBB, STB, etc.).

Calculates industry-specific metrics:
- NIM (Net Interest Margin)
- NPL Ratio (Non-Performing Loans)
- LLR (Loan Loss Reserve)
- CAR (Capital Adequacy Ratio)
- Cost-to-Income Ratio
- LDR (Loan-to-Deposit Ratio)
- Credit Growth & Deposit Growth
- Bank Health Score (comprehensive rating)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _safe_divide(numerator: Optional[float], denominator: Optional[float], default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if division is not possible."""
    if numerator is None or denominator is None or denominator == 0:
        return default
    return numerator / denominator


def _safe_get(data: Dict[str, Any], *keys: str, default: Any = 0.0) -> Any:
    """Safely get nested dictionary value with default fallback."""
    if not data:
        return default
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data if data is not None else default


def _calculate_yoy_growth(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    """Calculate year-over-year growth percentage."""
    if current is None or previous is None or previous == 0:
        return None
    return ((current - previous) / previous) * 100


def _rate_metric(value: float, thresholds: Dict[str, Tuple[float, float]]) -> str:
    """
    Rate a metric based on thresholds.

    thresholds format: {
        "excellent": (min, max),
        "good": (min, max),
        "acceptable": (min, max),
        "weak": (min, max)
    }
    """
    for rating, (min_val, max_val) in thresholds.items():
        if min_val <= value < max_val:
            return rating
    # If out of range, return closest boundary
    if value < thresholds.get("excellent", (0, 0))[0]:
        return "excellent"
    return "weak"


def calculate_nim(
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate Net Interest Margin (NIM).

    Formula: (Interest Income - Interest Expense) / Average Earning Assets
    Approximation: Net Interest Income / Total Assets

    Rating:
    - > 3.5% = Excellent
    - 2.5-3.5% = Good
    - < 2.5% = Weak
    """
    # Try to get net interest income directly from financial ratios
    net_interest_income = _safe_get(financial_ratios, "net_interest_income")

    # If not available, calculate from income statement
    if net_interest_income == 0:
        interest_income = _safe_get(income_statement, "interest_income")
        interest_expense = _safe_get(income_statement, "financial_expense")
        net_interest_income = interest_income - interest_expense

    total_assets = _safe_get(balance_sheet, "total_assets")

    nim = _safe_divide(net_interest_income * 100, total_assets)  # Convert to percentage

    # Rate NIM
    if nim >= 3.5:
        rating = "Xuất sắc"
        rating_en = "excellent"
    elif nim >= 2.5:
        rating = "Tốt"
        rating_en = "good"
    else:
        rating = "Yếu"
        rating_en = "weak"

    return {
        "value": round(nim, 2),
        "value_raw": nim,
        "rating": rating,
        "rating_en": rating_en,
        "label": "Biên lãi thuần (NIM)",
        "label_en": "Net Interest Margin",
        "unit": "%",
        "description": "Biên lãi thuần đo lường khả năng sinh lời từ hoạt động cho vay",
        "components": {
            "net_interest_income": net_interest_income,
            "total_assets": total_assets
        }
    }


def calculate_npl_ratio(
    balance_sheet: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate Non-Performing Loan (NPL) Ratio.

    Formula: Non-performing Loans / Total Loans
    Proxy: Loan Loss Reserve / Total Loans (if NPL not directly available)

    Rating:
    - < 1% = Excellent
    - 1-2% = Good
    - 2-3% = Acceptable
    - > 3% = Risky
    """
    # Try to get NPL directly
    npl = _safe_get(balance_sheet, "non_performing_loans")
    total_loans = _safe_get(balance_sheet, "loans_to_customers")

    # If NPL not available, use loan loss reserve as proxy
    if npl == 0:
        loan_loss_reserve = _safe_get(balance_sheet, "provision_credit_loss")
        npl = loan_loss_reserve

    npl_ratio = _safe_divide(npl * 100, total_loans)

    # Rate NPL Ratio
    if npl_ratio < 1:
        rating = "Xuất sắc"
        rating_en = "excellent"
    elif npl_ratio < 2:
        rating = "Tốt"
        rating_en = "good"
    elif npl_ratio < 3:
        rating = "Chấp nhận được"
        rating_en = "acceptable"
    else:
        rating = "Rủi ro cao"
        rating_en = "risky"

    return {
        "value": round(npl_ratio, 2),
        "value_raw": npl_ratio,
        "rating": rating,
        "rating_en": rating_en,
        "label": "Tỷ lệ nợ xấu (NPL)",
        "label_en": "Non-Performing Loan Ratio",
        "unit": "%",
        "description": "Tỷ lệ nợ xấu cho thấy chất lượng tài sản tín dụng",
        "components": {
            "npl_or_llr": npl,
            "total_loans": total_loans
        }
    }


def calculate_llr(
    balance_sheet: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate Loan Loss Reserve (LLR) Ratio.

    Formula: Loan Loss Reserve / Total Loans

    Higher ratio indicates more conservative provisioning.
    """
    loan_loss_reserve = _safe_get(balance_sheet, "provision_credit_loss")
    total_loans = _safe_get(balance_sheet, "loans_to_customers")

    llr = _safe_divide(loan_loss_reserve * 100, total_loans)

    # Rate LLR (higher is generally better for risk management)
    if llr >= 3:
        rating = "Thận trọng cao"
        rating_en = "very_conservative"
    elif llr >= 2:
        rating = "Thận trọng"
        rating_en = "conservative"
    elif llr >= 1:
        rating = "Trung bình"
        rating_en = "moderate"
    else:
        rating = "Dự phòng thấp"
        rating_en = "low"

    return {
        "value": round(llr, 2),
        "value_raw": llr,
        "rating": rating,
        "rating_en": rating_en,
        "label": "Tỷ lệ dự phòng rủi ro (LLR)",
        "label_en": "Loan Loss Reserve Ratio",
        "unit": "%",
        "description": "Tỷ lệ dự phòng rủi ro tín dụng trên tổng dư nợ",
        "components": {
            "loan_loss_reserve": loan_loss_reserve,
            "total_loans": total_loans
        }
    }


def calculate_car(
    balance_sheet: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate Capital Adequacy Ratio (CAR) - Proxy.

    Simplified Formula: (Equity / Total Assets) * 10
    This approximates Basel CAR ratio (normally based on risk-weighted assets).

    Rating:
    - > 12% = Strong
    - 8-12% = Adequate
    - < 8% = Weak
    """
    equity = _safe_get(balance_sheet, "equity_total")
    total_assets = _safe_get(balance_sheet, "total_assets")

    # Simplified CAR proxy: equity/assets * 10 (to approximate Basel ratio)
    car = _safe_divide(equity, total_assets, default=0) * 10

    # Rate CAR
    if car >= 12:
        rating = "Mạnh"
        rating_en = "strong"
    elif car >= 8:
        rating = "Đủ"
        rating_en = "adequate"
    else:
        rating = "Yếu"
        rating_en = "weak"

    return {
        "value": round(car, 2),
        "value_raw": car,
        "rating": rating,
        "rating_en": rating_en,
        "label": "Tỷ lệ an toàn vốn (CAR)",
        "label_en": "Capital Adequacy Ratio",
        "unit": "%",
        "description": "Tỷ lệ an toàn vốn (ước tính theo chuẩn Basel)",
        "components": {
            "equity": equity,
            "total_assets": total_assets
        }
    }


def calculate_cost_to_income(
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate Cost-to-Income Ratio.

    Formula: Operating Expenses / Operating Income
    Approximation: (Selling Expenses + Admin Expenses) / (Net Interest Income + Fee Income)

    Rating:
    - < 40% = Excellent
    - 40-50% = Good
    - 50-60% = Average
    - > 60% = Weak
    """
    # Get operating expenses
    operating_expenses = _safe_get(income_statement, "operating_expenses")

    # Get operating income (try multiple sources)
    net_interest_income = _safe_get(financial_ratios, "net_interest_income")
    if net_interest_income == 0:
        interest_income = _safe_get(income_statement, "interest_income")
        financial_expense = _safe_get(income_statement, "financial_expense")
        net_interest_income = interest_income - financial_expense

    # Use operating profit as proxy for operating income if fee income not available
    operating_income = _safe_get(income_statement, "operating_profit")
    if operating_income == 0:
        operating_income = net_interest_income + _safe_get(income_statement, "other_income")

    # Formula: Operating Expenses / Operating Income (not operating_income + operating_expenses)
    cost_to_income = _safe_divide(operating_expenses * 100, operating_income)

    # Rate Cost-to-Income
    if cost_to_income < 40:
        rating = "Xuất sắc"
        rating_en = "excellent"
    elif cost_to_income < 50:
        rating = "Tốt"
        rating_en = "good"
    elif cost_to_income < 60:
        rating = "Trung bình"
        rating_en = "average"
    else:
        rating = "Yếu"
        rating_en = "weak"

    return {
        "value": round(cost_to_income, 2),
        "value_raw": cost_to_income,
        "rating": rating,
        "rating_en": rating_en,
        "label": "Tỷ lệ chi phí trên thu nhập",
        "label_en": "Cost-to-Income Ratio",
        "unit": "%",
        "description": "Hiệu quả quản lý chi phí so với thu nhập",
        "components": {
            "operating_expenses": operating_expenses,
            "operating_income": operating_income
        }
    }


def calculate_ldr(
    balance_sheet: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate Loan-to-Deposit Ratio (LDR).

    Formula: Total Loans / Total Deposits

    Rating:
    - 80-100% = Optimal
    - < 80% = Under-lending
    - > 100% = Over-leveraged
    """
    # Try to get loans and deposits
    loans = _safe_get(balance_sheet, "loans_to_customers")
    deposits = _safe_get(balance_sheet, "customer_deposits")

    # If not available, use proxies
    if loans == 0:
        loans = _safe_get(balance_sheet, "accounts_receivable")  # Short-term loans proxy
    if deposits == 0:
        # Use current liabilities as proxy (simplified)
        deposits = _safe_get(balance_sheet, "liabilities_current")

    ldr = _safe_divide(loans * 100, deposits)

    # Rate LDR
    if 80 <= ldr <= 100:
        rating = "Tối ưu"
        rating_en = "optimal"
    elif ldr < 80:
        rating = "Cho vay thấp"
        rating_en = "under_lending"
    else:
        rating = "Vượt mức an toàn"
        rating_en = "over_leveraged"

    return {
        "value": round(ldr, 2),
        "value_raw": ldr,
        "rating": rating,
        "rating_en": rating_en,
        "label": "Tỷ lệ cho vay trên huy động (LDR)",
        "label_en": "Loan-to-Deposit Ratio",
        "unit": "%",
        "description": "Tỷ lệ sử dụng tiền huy động để cho vay",
        "components": {
            "loans": loans,
            "deposits": deposits
        }
    }


def calculate_credit_growth(
    balance_sheet: Dict[str, Any],
    previous_balance_sheet: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate Credit Growth (Year-over-Year).

    Compares total loans current vs previous year.
    """
    current_loans = _safe_get(balance_sheet, "loans_to_customers")

    if current_loans == 0:
        current_loans = _safe_get(balance_sheet, "accounts_receivable")

    if previous_balance_sheet:
        previous_loans = _safe_get(previous_balance_sheet, "loans_to_customers")
        if previous_loans == 0:
            previous_loans = _safe_get(previous_balance_sheet, "accounts_receivable")

        growth = _calculate_yoy_growth(current_loans, previous_loans)
    else:
        growth = None

    if growth is not None:
        if growth > 20:
            rating = "Tăng trưởng mạnh"
            rating_en = "strong_growth"
        elif growth > 10:
            rating = "Tăng trưởng tốt"
            rating_en = "good_growth"
        elif growth > 0:
            rating = "Tăng trưởng"
            rating_en = "growth"
        else:
            rating = "Giảm"
            rating_en = "decline"
    else:
        rating = "Không có dữ liệu"
        rating_en = "no_data"

    return {
        "value": round(growth, 2) if growth is not None else None,
        "value_raw": growth,
        "rating": rating,
        "rating_en": rating_en,
        "label": "Tăng trưởng tín dụng",
        "label_en": "Credit Growth",
        "unit": "%",
        "description": "Tốc độ tăng trưởng dư nợ cho vay so với cùng kỳ năm trước",
        "components": {
            "current_loans": current_loans,
            "previous_loans": _safe_get(previous_balance_sheet, "loans_to_customers") if previous_balance_sheet else None
        }
    }


def calculate_deposit_growth(
    balance_sheet: Dict[str, Any],
    previous_balance_sheet: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate Deposit Growth (Year-over-Year).

    Compares customer deposits current vs previous year.
    """
    current_deposits = _safe_get(balance_sheet, "customer_deposits")

    if current_deposits == 0:
        current_deposits = _safe_get(balance_sheet, "liabilities_current")

    if previous_balance_sheet:
        previous_deposits = _safe_get(previous_balance_sheet, "customer_deposits")
        if previous_deposits == 0:
            previous_deposits = _safe_get(previous_balance_sheet, "liabilities_current")

        growth = _calculate_yoy_growth(current_deposits, previous_deposits)
    else:
        growth = None

    if growth is not None:
        if growth > 20:
            rating = "Tăng trưởng mạnh"
            rating_en = "strong_growth"
        elif growth > 10:
            rating = "Tăng trưởng tốt"
            rating_en = "good_growth"
        elif growth > 0:
            rating = "Tăng trưởng"
            rating_en = "growth"
        else:
            rating = "Giảm"
            rating_en = "decline"
    else:
        rating = "Không có dữ liệu"
        rating_en = "no_data"

    return {
        "value": round(growth, 2) if growth is not None else None,
        "value_raw": growth,
        "rating": rating,
        "rating_en": rating_en,
        "label": "Tăng trưởng tiền gửi",
        "label_en": "Deposit Growth",
        "unit": "%",
        "description": "Tốc độ tăng trưởng tiền gửi khách hàng so với cùng kỳ năm trước",
        "components": {
            "current_deposits": current_deposits,
            "previous_deposits": _safe_get(previous_balance_sheet, "customer_deposits") if previous_balance_sheet else None
        }
    }


def calculate_bank_health_score(
    nim: Dict[str, Any],
    npl_ratio: Dict[str, Any],
    llr: Dict[str, Any],
    car: Dict[str, Any],
    cost_to_income: Dict[str, Any],
    ldr: Dict[str, Any],
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate Comprehensive Bank Health Score.

    Components:
    - Asset Quality (25%): NPL ratio, LLR coverage
    - Capital Strength (25%): CAR, Equity/Assets
    - Profitability (25%): NIM, ROE, ROA
    - Efficiency (25%): Cost/Income, LDR
    """
    # Asset Quality Score (0-100)
    asset_quality_score = 0
    npl_value = npl_ratio.get("value_raw", 0)
    llr_value = llr.get("value_raw", 0)

    # NPL score: lower is better (0% = 100 points, 5%+ = 0 points)
    npl_score = max(0, 100 - (npl_value / 5) * 100)
    # LLR score: higher is better (3%+ = 100 points, 0% = 0 points)
    llr_score = min(100, (llr_value / 3) * 100)

    asset_quality_score = (npl_score * 0.6 + llr_score * 0.4)

    # Capital Strength Score (0-100)
    capital_strength_score = 0
    car_value = car.get("value_raw", 0)
    equity = _safe_get(balance_sheet, "equity_total")
    total_assets = _safe_get(balance_sheet, "total_assets")
    equity_to_assets = _safe_divide(equity * 100, total_assets)

    # CAR score: higher is better (15%+ = 100 points, 5% = 0 points)
    car_score = max(0, min(100, (car_value - 5) / 10 * 100))
    # Equity/Assets score: higher is better (15%+ = 100 points, 5% = 0 points)
    equity_score = max(0, min(100, (equity_to_assets - 5) / 10 * 100))

    capital_strength_score = (car_score * 0.6 + equity_score * 0.4)

    # Profitability Score (0-100)
    profitability_score = 0
    nim_value = nim.get("value_raw", 0)
    # DB stores decimals (0.20 = 20%), so no conversion needed
    roe_raw = financial_ratios.get("roe", 0) if financial_ratios else 0
    roa_raw = financial_ratios.get("roa", 0) if financial_ratios else 0
    # Handle legacy data that might be stored as percentages (>1)
    roe = roe_raw if roe_raw < 1 else roe_raw / 100
    roa = roa_raw if roa_raw < 1 else roa_raw / 100

    # NIM score: higher is better (5%+ = 100 points, 1% = 0 points)
    nim_score = max(0, min(100, (nim_value - 1) / 4 * 100))
    # ROE score: higher is better (20%+ = 100 points, 0% = 0 points)
    # DB stores decimal: 0.20 = 20%, so multiply by 500 to get 0-100 scale
    roe_score = min(100, roe * 500)
    # ROA score: higher is better (2%+ = 100 points, 0% = 0 points)
    # DB stores decimal: 0.02 = 2%, so multiply by 5000 to get 0-100 scale
    roa_score = min(100, roa * 5000)

    profitability_score = (nim_score * 0.4 + roe_score * 0.4 + roa_score * 0.2)

    # Efficiency Score (0-100)
    efficiency_score = 0
    cost_to_income_value = cost_to_income.get("value_raw", 0)
    ldr_value = ldr.get("value_raw", 0)

    # Cost-to-Income score: lower is better (30% = 100 points, 80%+ = 0 points)
    cti_score = max(0, min(100, (80 - cost_to_income_value) / 50 * 100))
    # LDR score: 80-100% is optimal (90% = 100 points)
    if 80 <= ldr_value <= 100:
        ldr_score = 100 - abs(ldr_value - 90) * 5
    else:
        ldr_score = max(0, 100 - abs(ldr_value - 90) * 2)

    efficiency_score = (cti_score * 0.5 + ldr_score * 0.5)

    # Overall Health Score (weighted average)
    overall_score = (
        asset_quality_score * 0.25 +
        capital_strength_score * 0.25 +
        profitability_score * 0.25 +
        efficiency_score * 0.25
    )

    # Determine overall rating
    if overall_score >= 80:
        overall_rating = "Rất mạnh"
        overall_rating_en = "very_strong"
        health_color = "#22c55e"  # green
    elif overall_score >= 65:
        overall_rating = "Mạnh"
        overall_rating_en = "strong"
        health_color = "#3b82f6"  # blue
    elif overall_score >= 50:
        overall_rating = "Trung bình"
        overall_rating_en = "average"
        health_color = "#eab308"  # yellow
    elif overall_score >= 35:
        overall_rating = "Yếu"
        overall_rating_en = "weak"
        health_color = "#f97316"  # orange
    else:
        overall_rating = "Rất yếu"
        overall_rating_en = "very_weak"
        health_color = "#ef4444"  # red

    return {
        "overall_score": round(overall_score, 1),
        "overall_rating": overall_rating,
        "overall_rating_en": overall_rating_en,
        "health_color": health_color,
        "label": "Điểm sức khỏe tài chính",
        "label_en": "Bank Health Score",
        "description": "Đánh giá tổng quan về sức khỏe tài chính của ngân hàng",
        "components": {
            "asset_quality": {
                "score": round(asset_quality_score, 1),
                "weight": 25,
                "label": "Chất lượng tài sản",
                "label_en": "Asset Quality",
                "metrics": {
                    "npl_ratio": npl_ratio.get("value_raw", 0),
                    "llr": llr.get("value_raw", 0)
                }
            },
            "capital_strength": {
                "score": round(capital_strength_score, 1),
                "weight": 25,
                "label": "Sức mạnh vốn",
                "label_en": "Capital Strength",
                "metrics": {
                    "car": car.get("value_raw", 0),
                    "equity_to_assets": equity_to_assets
                }
            },
            "profitability": {
                "score": round(profitability_score, 1),
                "weight": 25,
                "label": "Khả năng sinh lời",
                "label_en": "Profitability",
                "metrics": {
                    "nim": nim.get("value_raw", 0),
                    "roe": roe,
                    "roa": roa
                }
            },
            "efficiency": {
                "score": round(efficiency_score, 1),
                "weight": 25,
                "label": "Hiệu quả vận hành",
                "label_en": "Efficiency",
                "metrics": {
                    "cost_to_income": cost_to_income_value,
                    "ldr": ldr_value
                }
            }
        }
    }


def analyze_banking_sector(
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any],
    previous_balance_sheet: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive banking industry analysis.

    Args:
        financial_ratios: Dict containing calculated financial ratios
        balance_sheet: Dict containing balance sheet data
        income_statement: Dict containing income statement data
        previous_balance_sheet: Optional dict containing previous year balance sheet for growth calculations

    Returns:
        Dict containing all banking metrics, ratings, and health score
    """
    # Calculate all banking-specific metrics
    nim = calculate_nim(financial_ratios, balance_sheet, income_statement)
    npl_ratio = calculate_npl_ratio(balance_sheet)
    llr = calculate_llr(balance_sheet)
    car = calculate_car(balance_sheet)
    cost_to_income = calculate_cost_to_income(financial_ratios, balance_sheet, income_statement)
    ldr = calculate_ldr(balance_sheet)
    credit_growth = calculate_credit_growth(balance_sheet, previous_balance_sheet)
    deposit_growth = calculate_deposit_growth(balance_sheet, previous_balance_sheet)

    # Calculate comprehensive health score
    health_score = calculate_bank_health_score(
        nim, npl_ratio, llr, car, cost_to_income, ldr,
        financial_ratios, balance_sheet
    )

    return {
        "nim": nim,
        "npl_ratio": npl_ratio,
        "llr": llr,
        "car": car,
        "cost_to_income": cost_to_income,
        "ldr": ldr,
        "credit_growth": credit_growth,
        "deposit_growth": deposit_growth,
        "health_score": health_score,
        "analysis_type": "banking",
        "industry": "Ngân hàng",
        "description": "Phân tích chuyên sâu các chỉ số tài chính ngành ngân hàng"
    }


# Convenience function for single-metric calculation
def calculate_single_banking_metric(
    metric_name: str,
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any],
    previous_balance_sheet: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Calculate a single banking metric by name.

    Supported metric names:
    - nim, npl_ratio, llr, car, cost_to_income, ldr, credit_growth, deposit_growth
    """
    metric_functions = {
        "nim": lambda: calculate_nim(financial_ratios, balance_sheet, income_statement),
        "npl_ratio": lambda: calculate_npl_ratio(balance_sheet),
        "llr": lambda: calculate_llr(balance_sheet),
        "car": lambda: calculate_car(balance_sheet),
        "cost_to_income": lambda: calculate_cost_to_income(financial_ratios, balance_sheet, income_statement),
        "ldr": lambda: calculate_ldr(balance_sheet),
        "credit_growth": lambda: calculate_credit_growth(balance_sheet, previous_balance_sheet),
        "deposit_growth": lambda: calculate_deposit_growth(balance_sheet, previous_balance_sheet),
    }

    func = metric_functions.get(metric_name.lower())
    if func:
        return func()
    return None
