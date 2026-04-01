"""
Real Estate Industry Analysis Module

Module chuyên phân tích ngành bất động sản với các chỉ số đặc thù:
- Tỷ lệ Hàng tồn kho/Tổng tài sản (Inventory/Total Assets)
- Chất lượng hàng tồn kho dự án (Project Inventory Quality)
- Đòn bẩy nợ (Debt/Equity, Interest Coverage)
- Thanh khoản (Cash/Short-term Debt, Current Ratio)
- Biên lợi nhuận (Gross Margin)
- Mẫu hình ghi nhận doanh thu (Revenue Recognition Pattern)

Author: Phase 2 Implementation
Date: 2026-02-15
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class REMetric:
    """Kết quả tính toán một chỉ số phân tích BĐS"""
    value: Optional[float]
    rating: str  # Rating: "Tốt", "Khá", "Trung bình", "Cần xem xét", "Rủi ro"
    label: str  # Nhãn tiếng Việt
    description: str  # Giải thích ý nghĩa
    benchmark: Optional[str]  # Chuẩn mực ngành


def _safe_divide(
    numerator: Optional[float],
    denominator: Optional[float],
    default: Optional[float] = None
) -> Optional[float]:
    """Chia an toàn, xử lý None và division by zero"""
    if numerator is None or denominator is None:
        return default
    if denominator == 0:
        return default
    return numerator / denominator


def _get_value(
    data: Dict[str, Any],
    key: str,
    default: Optional[float] = None
) -> Optional[float]:
    """Lấy giá trị từ dictionary với xử lý None"""
    val = data.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def calculate_inventory_to_assets(
    balance_sheet: Dict[str, Any]
) -> REMetric:
    """
    1. Tỷ lệ Hàng tồn kho / Tổng tài sản (Inventory/Total Assets Ratio)

    - Đối với doanh nghiệp BĐS: Tỷ lệ cao là bình thường (dự án đang phát triển)
    - Rating:
      + 40-70%: Bình thường cho doanh nghiệp phát triển BĐS
      + > 70%: Cần xem xét tốc độ vòng quay tồn kho
      + < 40%: Có thể là giai đoạn giữa các dự án hoặc mô hình dịch vụ BĐS
    """
    inventory = _get_value(balance_sheet, "inventory")
    total_assets = _get_value(balance_sheet, "total_assets")

    ratio = _safe_divide(inventory, total_assets)

    if ratio is None:
        return REMetric(
            value=None,
            rating="Không có dữ liệu",
            label="Tỷ lệ Hàng tồn kho/Tổng tài sản",
            description="Tỷ lệ hàng tồn kho trên tổng tài sản (đặc thù BĐS)",
            benchmark=None
        )

    # Rating theo tiêu chuẩn ngành BĐS
    if ratio >= 0.70:
        rating = "Cần xem xét"
        note = "Tỷ lệ tồn kho cao - cần kiểm tra tốc độ bán hàng"
    elif ratio >= 0.40:
        rating = "Bình thường"
        note = "Tỷ lệ tồn kho phù hợp với doanh nghiệp phát triển BĐS"
    elif ratio >= 0.20:
        rating = "Thấp"
        note = "Tỷ lệ tồn kho thấp - có thể giai đoạn giữa dự án"
    else:
        rating = "Rất thấp"
        note = "Tỷ lệ tồn kho rất thấp - mô hình có thể khác"

    return REMetric(
        value=ratio,
        rating=rating,
        label="Tỷ lệ Hàng tồn kho/Tổng tài sản",
        description=f"{note}. Tỷ lệ {ratio:.1%} cho biết {ratio:.1%} tổng tài sản đang đầu tư vào hàng tồn kho (dự án đang phát triển).",
        benchmark="40-70%: Bình thường"
    )


def calculate_project_inventory_quality(
    balance_sheet: Dict[str, Any]
) -> Dict[str, REMetric]:
    """
    2. Chất lượng hàng tồn kho dự án (Project Inventory Quality)

    Phân tích cấu trúc hàng tồn kho:
    - Construction in Progress / Total Inventory
    - Finished Goods / Total Inventory

    Trong BĐS Việt Nam, thường có:
    - Đất đang đầu tư (Long-term inventory)
    - Chi phí xây dựng dở dang (Construction in progress)
    - Hàng hóa bất động sản hoàn thành (Finished goods)
    """
    inventory = _get_value(balance_sheet, "inventory")
    asset_non_current = _get_value(balance_sheet, "asset_non_current")
    total_assets = _get_value(balance_sheet, "total_assets")

    if inventory is None or total_assets is None:
        return {
            "inventory_to_total": REMetric(
                value=None,
                rating="Không có dữ liệu",
                label="Hàng tồn kho/Tổng tài sản",
                description="Không có dữ liệu về hàng tồn kho",
                benchmark=None
            ),
            "non_current_investment_ratio": REMetric(
                value=None,
                rating="Không có dữ liệu",
                label="Đầu tư dài hạn/Tổng tài sản",
                description="Không có dữ liệu về đầu tư dài hạn",
                benchmark=None
            )
        }

    inventory_ratio = inventory / total_assets if total_assets else None
    non_current_ratio = _safe_divide(asset_non_current, total_assets)

    # Rating cho cấu trúc tồn kho
    if inventory_ratio and non_current_ratio:
        if inventory_ratio > 0.5 and non_current_ratio > 0.3:
            inv_rating = "Đang phát triển mạnh"
            inv_desc = "Cấu trúc tài sản phù hợp với doanh nghiệp BĐS đang triển khai nhiều dự án"
        elif inventory_ratio > 0.3:
            inv_rating = "Bình thường"
            inv_desc = "Cấu trúc tài sản tương đối cân đối"
        else:
            inv_rating = "Tồn kho thấp"
            inv_desc = "Tỷ lệ tồn kho thấp, có thể do giai đoạn giữa các dự án"
    else:
        inv_rating = "Không đánh giá được"
        inv_desc = "Thiếu thông tin để đánh giá"

    return {
        "inventory_to_total": REMetric(
            value=inventory_ratio,
            rating=inv_rating,
            label="Hàng tồn kho/Tổng tài sản",
            description=inv_desc,
            benchmark="30-50%: Bình thường"
        ),
        "non_current_investment_ratio": REMetric(
            value=non_current_ratio,
            rating="Bình thường" if non_current_ratio and non_current_ratio < 0.6 else "Cao",
            label="Đầu tư dài hạn/Tổng tài sản",
            description=f"Đầu tư dài hạn chiếm {non_current_ratio:.1%} tổng tài sản, bao gồm đất và dự án đang phát triển.",
            benchmark="< 60%: Bình thường"
        )
    }


def calculate_debt_to_equity_re(
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any]
) -> REMetric:
    """
    3. Đòn bẩy nợ (Debt/Equity) - Ngành BĐS

    Doanh nghiệp BĐS thường có đòn bẩy cao hơn các ngành khác:
    - < 100%: Conservative (Thận trọng)
    - 100-200%: Normal (Bình thường cho BĐS)
    - 200-300%: Aggressive (Mở rộng mạnh)
    - > 300%: Risky (Rủi ro cao)

    Lưu ý: Cần xem xét thêm Interest Coverage Ratio
    """
    # Ưu tiên lấy từ financial_ratios
    debt_to_equity = _get_value(financial_ratios, "debt_to_equity")

    if debt_to_equity is None:
        # Tính từ balance sheet
        liabilities_total = _get_value(balance_sheet, "liabilities_total")
        equity_total = _get_value(balance_sheet, "equity_total")
        debt_to_equity = _safe_divide(liabilities_total, equity_total)

    if debt_to_equity is None:
        return REMetric(
            value=None,
            rating="Không có dữ liệu",
            label="Đòn bẩy nợ (Debt/Equity)",
            description="Không có dữ liệu về đòn bẩy nợ",
            benchmark=None
        )

    # Rating theo tiêu chuẩn BĐS
    if debt_to_equity > 3.0:
        rating = "Rủi ro cao"
        desc = f"Đòn bẩy rất cao ({debt_to_equity:.2f}x). Rủi ro tài chính lớn, cần kiểm tra kỹ khả năng thanh toán."
    elif debt_to_equity > 2.0:
        rating = "Mở rộng mạnh"
        desc = f"Đòn bẩy cao ({debt_to_equity:.2f}x). Đang mở rộng aggressively, cần theo dõi dòng tiền."
    elif debt_to_equity > 1.0:
        rating = "Bình thường"
        desc = f"Đòn bẩy ở mức bình thường cho ngành BĐS ({debt_to_equity:.2f}x). Cân đối giữa mở rộng và an toàn."
    else:
        rating = "Thận trọng"
        desc = f"Đòn bẩy thấp ({debt_to_equity:.2f}x). Chính sách tài chính thận trọng."

    return REMetric(
        value=debt_to_equity,
        rating=rating,
        label="Đòn bẩy nợ (Debt/Equity)",
        description=desc,
        benchmark="< 100%: Thận trọng | 100-200%: Bình thường | 200-300%: Mở rộng mạnh | > 300%: Rủi ro cao"
    )


def calculate_cash_to_st_debt(
    balance_sheet: Dict[str, Any],
    financial_ratios: Dict[str, Any]
) -> REMetric:
    """
    4. Tỷ lệ Tiền mặt / Nợ ngắn hạn (Cash/Short-term Debt)

    Chỉ số quan trọng để đánh giá khả năng thanh toán tức thời:
    - > 1.0: Strong (Mạnh) - Dễ dàng thanh toán nợ ngắn hạn
    - 0.5-1.0: Adequate (Đủ) - Có đủ thanh khoản cơ bản
    - < 0.5: Liquidity Risk (Rủi ro thanh khoản)

    Đặc biệt quan trọng trong giai đoạn thắt chặt tín dụng
    """
    cash = _get_value(balance_sheet, "cash_and_equivalents")
    short_term_debt_reported = _get_value(balance_sheet, "liabilities_current")
    liabilities_total = _get_value(balance_sheet, "liabilities_total")
    liabilities_non_current = _get_value(balance_sheet, "liabilities_non_current")

    if cash is None:
        return REMetric(
            value=None,
            rating="Không có dữ liệu",
            label="Tiền mặt/Nợ ngắn hạn",
            description="Không có đủ dữ liệu tiền mặt để tính tỷ lệ tiền mặt trên nợ ngắn hạn",
            benchmark=None
        )

    short_term_debt = short_term_debt_reported
    derived_used = False
    if (short_term_debt is None or short_term_debt <= 0) and liabilities_total is not None and liabilities_non_current is not None:
        derived = liabilities_total - liabilities_non_current
        if derived is not None and derived > 0:
            short_term_debt = derived
            derived_used = True

    ratio = _safe_divide(cash, short_term_debt)

    # If the reported short-term debt yields an extreme outlier, try deriving from totals.
    if (ratio is not None and ratio > 20 and not derived_used and
            liabilities_total is not None and liabilities_non_current is not None and
            (liabilities_total - liabilities_non_current) > 0):
        derived = liabilities_total - liabilities_non_current
        ratio_derived = _safe_divide(cash, derived)
        if ratio_derived is not None and (ratio_derived <= 20 or ratio_derived < ratio):
            short_term_debt = derived
            ratio = ratio_derived
            derived_used = True

    if ratio is None or ratio < 0 or ratio > 20:
        return REMetric(
            value=None,
            rating="Không đánh giá được",
            label="Tiền mặt/Nợ ngắn hạn",
            description="Không thể tính/không tin cậy (outlier > 20x hoặc dữ liệu thiếu). Cần kiểm tra lại dữ liệu nợ ngắn hạn hoặc rebuild DB.",
            benchmark=None
        )

    # Rating
    if ratio >= 1.0:
        rating = "Mạnh"
        desc = f"Thanh khoản tốt ({ratio:.2f}x). Tiền mặt đủ để trả toàn bộ nợ ngắn hạn."
    elif ratio >= 0.5:
        rating = "Đủ"
        desc = f"Thanh khoản ở mức chấp nhận được ({ratio:.2f}x). Cần quản trị dòng tiền chặt chẽ."
    else:
        rating = "Rủi ro thanh khoản"
        desc = f"Thanh khoản thấp ({ratio:.2f}x). Cần cân nhắc huy động vốn hoặc tái cấu trúc nợ."

    if derived_used:
        desc += " (Nợ ngắn hạn được suy ra từ tổng nợ - nợ dài hạn do dữ liệu `liabilities_current` không tin cậy.)"

    return REMetric(
        value=ratio,
        rating=rating,
        label="Tiền mặt/Nợ ngắn hạn",
        description=desc,
        benchmark="> 1.0: Mạnh | 0.5-1.0: Đủ | < 0.5: Rủi ro thanh khoản"
    )


def calculate_interest_coverage(
    financial_ratios: Dict[str, Any],
    income_statement: Dict[str, Any]
) -> REMetric:
    """
    5. Interest Coverage Ratio (Khả năng chi trả lãi vay)

    Formula: EBIT / Interest Expense

    - > 3.0: Safe (An toàn)
    - 1.5-3.0: Adequate (Đủ)
    - < 1.5: Risky (Rủi ro)

    Đây là chỉ số quan trọng nhất để đánh giá khả năng phục vụ nợ
    """
    # Ưu tiên lấy từ financial_ratios
    coverage = _get_value(financial_ratios, "interest_coverage_ratio")

    if coverage is None:
        # Tính từ income statement
        # EBIT ≈ Operating Profit + Financial Expense (approximately)
        operating_profit = _get_value(income_statement, "operating_profit")
        financial_expense = _get_value(income_statement, "financial_expense")

        if operating_profit is not None and financial_expense is not None and financial_expense != 0:
            coverage = abs(operating_profit / financial_expense)

    if coverage is None:
        return REMetric(
            value=None,
            rating="Không có dữ liệu",
            label="Interest Coverage Ratio",
            description="Không có dữ liệu về khả năng chi trả lãi vay",
            benchmark=None
        )

    # Rating
    if coverage >= 3.0:
        rating = "An toàn"
        desc = f"Khả năng chi trả lãi vay tốt ({coverage:.2f}x). EBIT đủ để trả lãi vay {coverage:.1f} lần."
    elif coverage >= 1.5:
        rating = "Đủ"
        desc = f"Khả năng chi trả lãi vay ở mức chấp nhận được ({coverage:.2f}x). Cần theo dõi sát."
    else:
        rating = "Rủi ro"
        desc = f"Khả năng chi trả lãi vay thấp ({coverage:.2f}x). EBIT không đủ để chi trả lãi vay, rủi ro thanh khoản cao."

    return REMetric(
        value=coverage,
        rating=rating,
        label="Interest Coverage Ratio",
        description=desc,
        benchmark="> 3.0: An toàn | 1.5-3.0: Đủ | < 1.5: Rủi ro"
    )


def calculate_gross_margin(
    financial_ratios: Dict[str, Any],
    income_statement: Dict[str, Any]
) -> REMetric:
    """
    6. Biên lợi nhuận gộp (Gross Margin)

    Formula: (Revenue - COGS) / Revenue

    - > 40%: Excellent (Xuất sắc)
    - 25-40%: Good (Tốt)
    - < 25%: Low (Thấp)

    Trong BĐS: Gross Margin phản ánh giá trị dự án và vị trí đắc địa
    """
    # Ưu tiên lấy từ financial_ratios
    gross_margin = _get_value(financial_ratios, "gross_margin")

    if gross_margin is None:
        # Tính từ income statement
        revenue = _get_value(income_statement, "net_revenue")
        gross_profit = _get_value(income_statement, "gross_profit")

        if revenue is not None and revenue != 0 and gross_profit is not None:
            gross_margin = gross_profit / revenue  # Result is decimal

    if gross_margin is None:
        return REMetric(
            value=None,
            rating="Không có dữ liệu",
            label="Biên lợi nhuận gộp",
            description="Không có dữ liệu về biên lợi nhuận gộp",
            benchmark=None
        )

    # Normalize to percentage: if value < 1, it's decimal (0.35 = 35%)
    # If value >= 1, assume it's already percentage
    gross_margin_pct = gross_margin * 100 if gross_margin < 1 else gross_margin

    # Rating (gross_margin_pct is now in percentage)
    if gross_margin_pct >= 40:
        rating = "Xuất sắc"
        desc = f"Biên lợi nhuận gộp rất tốt ({gross_margin_pct:.1f}%). Dự án có chất lượng và vị trí cao cấp."
    elif gross_margin_pct >= 25:
        rating = "Tốt"
        desc = f"Biên lợi nhuận gộp tốt ({gross_margin_pct:.1f}%). Cạnh tranh ở mức trung bình."
    else:
        rating = "Thấp"
        desc = f"Biên lợi nhuận gộp thấp ({gross_margin_pct:.1f}%). Có thể do giá vốn cao hoặc giá bán thấp."

    return REMetric(
        value=gross_margin_pct,
        rating=rating,
        label="Biên lợi nhuận gộp",
        description=desc,
        benchmark="> 40%: Xuất sắc | 25-40%: Tốt | < 25%: Thấp"
    )


def analyze_revenue_recognition_pattern(
    income_statement: Dict[str, Any],
    cash_flow: Dict[str, Any]
) -> Dict[str, Any]:
    """
    7. Mẫu hình ghi nhận doanh thu (Revenue Recognition Pattern)

    Phân tích:
    - Biến động doanh thu (doanh thu theo dự án, không đều)
    - So sánh doanh thu với tiền thu được từ khách hàng
    - Đánh giá chất lượng doanh thu

    Trong BĐS: Doanh thu thường ghi nhận theo giai đoạn hoàn thành dự án
    """
    revenue = _get_value(income_statement, "net_revenue")
    revenue_growth = _get_value(income_statement, "revenue_growth")
    cash_from_operating = _get_value(cash_flow, "net_cash_from_operating_activities")
    increase_receivables = _get_value(cash_flow, "increase_decrease_receivables")

    result = {
        "revenue": revenue,
        "revenue_growth": revenue_growth,
        "operating_cash_flow": cash_from_operating,
        "pattern_analysis": ""
    }

    if revenue is None:
        result["pattern_analysis"] = "Không có dữ liệu doanh thu"
        return result

    # Phân tích chất lượng doanh thu
    if cash_from_operating is not None and revenue != 0:
        cash_to_revenue = cash_from_operating / revenue
        if cash_to_revenue > 0.8:
            pattern = "Doanh thu chất lượng cao - tiền về tốt"
        elif cash_to_revenue > 0.5:
            pattern = "Doanh thu chất lượng khá - tiền về trung bình"
        else:
            pattern = "Doanh thu chất lượng thấp - tiền về chậm"
        result["cash_to_revenue_ratio"] = cash_to_revenue
    else:
        pattern = "Không đánh giá được chất lượng doanh thu"

    # Phân tích biến động
    if revenue_growth is not None:
        if revenue_growth > 20:
            volatility = "Tăng trưởng mạnh"
        elif revenue_growth > 0:
            volatility = "Tăng trưởng đều"
        elif revenue_growth > -10:
            volatility = "Ổn định"
        else:
            volatility = "Sụt giảm"
    else:
        volatility = "Không có dữ liệu"

    result["pattern_analysis"] = f"{pattern}. Biến động: {volatility}"

    return result


def calculate_working_capital(
    balance_sheet: Dict[str, Any]
) -> REMetric:
    """
    8. Vốn lưu động (Working Capital)

    Formula: Current Assets - Current Liabilities

    Vốn lưu động dương: Có thể tài trợ hoạt động kinh doanh
    Vốn lưu động âm: Có thể cần vay vốn ngắn hạn để vận hành

    Trong BĐS: Working Capital quan trọng để duy trì tiến độ dự án
    """
    current_assets = _get_value(balance_sheet, "asset_current")
    current_liabilities_reported = _get_value(balance_sheet, "liabilities_current")
    liabilities_total = _get_value(balance_sheet, "liabilities_total")
    liabilities_non_current = _get_value(balance_sheet, "liabilities_non_current")

    if current_assets is None:
        return REMetric(
            value=None,
            rating="Không có dữ liệu",
            label="Vốn lưu động",
            description="Không có dữ liệu về vốn lưu động",
            benchmark=None
        )

    current_liabilities = current_liabilities_reported
    derived_used = False
    if (current_liabilities is None or current_liabilities <= 0) and liabilities_total is not None and liabilities_non_current is not None:
        derived = liabilities_total - liabilities_non_current
        if derived is not None and derived > 0:
            current_liabilities = derived
            derived_used = True

    if current_liabilities is None:
        return REMetric(
            value=None,
            rating="Không có dữ liệu",
            label="Vốn lưu động",
            description="Không có dữ liệu nợ ngắn hạn để tính vốn lưu động",
            benchmark=None
        )

    # Guardrail: flag extreme current ratio as unreliable under current DB limits.
    current_ratio = current_assets / current_liabilities
    if current_ratio < 0:
        return REMetric(
            value=None,
            rating="Không đánh giá được",
            label="Vốn lưu động",
            description="Dữ liệu thanh khoản không hợp lệ (current_ratio < 0).",
            benchmark=None
        )

    # If reported CL yields an extreme outlier, try deriving from totals when possible.
    if (current_ratio > 20 and not derived_used and
            liabilities_total is not None and liabilities_non_current is not None and
            (liabilities_total - liabilities_non_current) > 0):
        derived = liabilities_total - liabilities_non_current
        current_ratio_derived = current_assets / derived
        if current_ratio_derived <= 20 or current_ratio_derived < current_ratio:
            current_liabilities = derived
            current_ratio = current_ratio_derived
            derived_used = True

    # If we still have an extreme outlier without a derivation path, treat as unreliable.
    if current_ratio > 20 and not derived_used:
        return REMetric(
            value=None,
            rating="Không đánh giá được",
            label="Vốn lưu động",
            description="Dữ liệu thanh khoản không tin cậy (current_ratio outlier > 20x). Cần rebuild DB hoặc dùng ratio table.",
            benchmark=None
        )

    working_capital = current_assets - current_liabilities

    if working_capital > 0:
        rating = "Dương"
        desc = f"Vốn lưu động dương ({working_capital:,.0f} tỷ VND). Có thể tự tài trợ hoạt động."
    else:
        rating = "Âm"
        desc = f"Vốn lưu động âm ({working_capital:,.0f} tỷ VND). Cần huy động vốn để duy trì hoạt động."

    if derived_used:
        desc += " (Nợ ngắn hạn được suy ra từ tổng nợ - nợ dài hạn do dữ liệu `liabilities_current` không tin cậy.)"
    elif current_ratio > 20:
        desc += " (Lưu ý: current_ratio rất cao; cần kiểm tra cấu trúc nợ ngắn hạn.)"

    return REMetric(
        value=working_capital,
        rating=rating,
        label="Vốn lưu động",
        description=desc,
        benchmark="Dương: Tốt | Âm: Cần lưu ý"
    )


def calculate_re_health_score(
    metrics: Dict[str, REMetric],
    financial_ratios: Dict[str, Any],
    income_statement: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Tính RE Health Score (Điểm sức khỏe doanh nghiệp BĐS)

    Cấu trúc điểm số:
    - Thanh khoản (30%): Cash/ST Debt, Current Ratio, Working Capital
    - Đòn bẩy (25%): Debt/Equity, Interest Coverage
    - Thực hiện dự án (25%): Inventory ratios, Gross Margin
    - Tăng trưởng (20%): Revenue Growth, Asset Growth

    Tổng điểm: 0-100
    """
    scores = {}
    max_scores = {}

    # 1. Thanh khoản (30%)
    liquidity_score = 0
    cash_st_debt = metrics.get("cash_to_st_debt")
    if cash_st_debt and cash_st_debt.value is not None:
        if cash_st_debt.value >= 1.0:
            liquidity_score += 10
        elif cash_st_debt.value >= 0.5:
            liquidity_score += 7
        else:
            liquidity_score += 3

    current_ratio = _get_value(financial_ratios, "current_ratio")
    if current_ratio is not None and (current_ratio <= 0 or current_ratio > 20):
        current_ratio = None
    if current_ratio is not None:
        if current_ratio >= 1.5:
            liquidity_score += 10
        elif current_ratio >= 1.0:
            liquidity_score += 7
        else:
            liquidity_score += 3

    working_capital = metrics.get("working_capital")
    if working_capital and working_capital.value is not None:
        if working_capital.value > 0:
            liquidity_score += 10
        else:
            liquidity_score += 4

    scores["liquidity"] = liquidity_score
    max_scores["liquidity"] = 30

    # 2. Đòn bẩy (25%)
    leverage_score = 0
    debt_equity = metrics.get("debt_to_equity")
    if debt_equity and debt_equity.value is not None:
        if debt_equity.value < 1.0:
            leverage_score += 12
        elif debt_equity.value < 2.0:
            leverage_score += 10
        elif debt_equity.value < 3.0:
            leverage_score += 6
        else:
            leverage_score += 2

    interest_coverage = metrics.get("interest_coverage")
    if interest_coverage and interest_coverage.value is not None:
        if interest_coverage.value >= 3.0:
            leverage_score += 13
        elif interest_coverage.value >= 1.5:
            leverage_score += 8
        else:
            leverage_score += 3

    scores["leverage"] = leverage_score
    max_scores["leverage"] = 25

    # 3. Thực hiện dự án (25%)
    execution_score = 0
    inventory_ratio = metrics.get("inventory_to_assets")
    if inventory_ratio and inventory_ratio.value is not None:
        if 0.4 <= inventory_ratio.value <= 0.7:
            execution_score += 12
        elif inventory_ratio.value < 0.4:
            execution_score += 8
        else:
            execution_score += 5

    gross_margin = metrics.get("gross_margin")
    if gross_margin and gross_margin.value is not None:
        if gross_margin.value >= 40:
            execution_score += 13
        elif gross_margin.value >= 25:
            execution_score += 9
        else:
            execution_score += 4

    scores["execution"] = execution_score
    max_scores["execution"] = 25

    # 4. Tăng trưởng (20%)
    growth_score = 0
    revenue_growth = _get_value(income_statement, "revenue_growth")
    if revenue_growth is not None:
        if revenue_growth >= 20:
            growth_score += 10
        elif revenue_growth >= 10:
            growth_score += 7
        elif revenue_growth >= 0:
            growth_score += 4
        else:
            growth_score += 1

    asset_growth = _get_value(financial_ratios, "asset_turnover")
    if asset_growth is not None:
        growth_score += 10  # Simplified - trong thực tế cần tính asset growth

    scores["growth"] = growth_score
    max_scores["growth"] = 20

    # Tổng điểm
    total_score = sum(scores.values())
    max_score = sum(max_scores.values())
    final_score = (total_score / max_score) * 100 if max_score > 0 else 0

    # Rating tổng thể
    if final_score >= 80:
        overall_rating = "Sức khỏe tốt"
        overall_desc = "Doanh nghiệp BĐS có sức khỏe tài chính tốt, quản trị rủi ro hiệu quả."
    elif final_score >= 60:
        overall_rating = "Sức khỏe khá"
        overall_desc = "Sức khỏe tài chính ở mức khá, cần theo dõi một số chỉ số."
    elif final_score >= 40:
        overall_rating = "Sức khỏe trung bình"
        overall_desc = "Sức khỏe tài chính trung bình, có rủi ro cần lưu ý."
    else:
        overall_rating = "Sức khỏe yếu"
        overall_desc = "Sức khỏe tài chính yếu, cần cải thiện nhiều chỉ số."

    return {
        "total_score": final_score,
        "max_score": 100,
        "overall_rating": overall_rating,
        "overall_description": overall_desc,
        "component_scores": scores,
        "component_max_scores": max_scores
    }


def analyze_real_estate_company(
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any],
    cash_flow: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Hàm chính phân tích doanh nghiệp BĐS

    Args:
        financial_ratios: Dict chứa các chỉ số tài chính
        balance_sheet: Dict chứa bảng cân đối kế toán
        income_statement: Dict chứa báo cáo kết quả kinh doanh
        cash_flow: Dict chứa báo cáo lưu chuyển tiền tệ

    Returns:
        Dict chứa tất cả chỉ số phân tích BĐS với ratings và health score
    """
    # Tính toán các chỉ số
    inventory_to_assets = calculate_inventory_to_assets(balance_sheet)
    project_quality = calculate_project_inventory_quality(balance_sheet)
    debt_to_equity = calculate_debt_to_equity_re(financial_ratios, balance_sheet)
    cash_to_st_debt = calculate_cash_to_st_debt(balance_sheet, financial_ratios)
    interest_coverage = calculate_interest_coverage(financial_ratios, income_statement)
    gross_margin = calculate_gross_margin(financial_ratios, income_statement)
    revenue_pattern = analyze_revenue_recognition_pattern(income_statement, cash_flow)
    working_capital = calculate_working_capital(balance_sheet)

    # Gom tất cả metrics
    metrics = {
        "inventory_to_assets": inventory_to_assets,
        "debt_to_equity": debt_to_equity,
        "cash_to_st_debt": cash_to_st_debt,
        "interest_coverage": interest_coverage,
        "gross_margin": gross_margin,
        "working_capital": working_capital
    }

    # Tính Health Score
    health_score = calculate_re_health_score(metrics, financial_ratios, income_statement)

    # Format kết quả trả về
    return {
        "metrics": {
            "inventory_to_total_assets": {
                "value": inventory_to_assets.value,
                "rating": inventory_to_assets.rating,
                "label": inventory_to_assets.label,
                "description": inventory_to_assets.description,
                "benchmark": inventory_to_assets.benchmark
            },
            "project_inventory_quality": {
                "inventory_to_total": {
                    "value": project_quality["inventory_to_total"].value,
                    "rating": project_quality["inventory_to_total"].rating,
                    "label": project_quality["inventory_to_total"].label,
                    "description": project_quality["inventory_to_total"].description,
                    "benchmark": project_quality["inventory_to_total"].benchmark
                },
                "non_current_investment_ratio": {
                    "value": project_quality["non_current_investment_ratio"].value,
                    "rating": project_quality["non_current_investment_ratio"].rating,
                    "label": project_quality["non_current_investment_ratio"].label,
                    "description": project_quality["non_current_investment_ratio"].description,
                    "benchmark": project_quality["non_current_investment_ratio"].benchmark
                }
            },
            "debt_to_equity": {
                "value": debt_to_equity.value,
                "rating": debt_to_equity.rating,
                "label": debt_to_equity.label,
                "description": debt_to_equity.description,
                "benchmark": debt_to_equity.benchmark
            },
            "cash_to_st_debt": {
                "value": cash_to_st_debt.value,
                "rating": cash_to_st_debt.rating,
                "label": cash_to_st_debt.label,
                "description": cash_to_st_debt.description,
                "benchmark": cash_to_st_debt.benchmark
            },
            "interest_coverage": {
                "value": interest_coverage.value,
                "rating": interest_coverage.rating,
                "label": interest_coverage.label,
                "description": interest_coverage.description,
                "benchmark": interest_coverage.benchmark
            },
            "gross_margin": {
                "value": gross_margin.value,
                "rating": gross_margin.rating,
                "label": gross_margin.label,
                "description": gross_margin.description,
                "benchmark": gross_margin.benchmark
            },
            "revenue_recognition_pattern": revenue_pattern,
            "working_capital": {
                "value": working_capital.value,
                "rating": working_capital.rating,
                "label": working_capital.label,
                "description": working_capital.description,
                "benchmark": working_capital.benchmark
            }
        },
        "health_score": health_score,
        "summary": {
            "title": "Tóm tắt phân tích Bất động sản",
            "key_strengths": _extract_strengths(metrics),
            "key_risks": _extract_risks(metrics),
            "recommendations": _generate_recommendations(metrics, health_score)
        }
    }


def _extract_strengths(metrics: Dict[str, REMetric]) -> list[str]:
    """Trích xuất điểm mạnh từ các chỉ số"""
    strengths = []

    if metrics.get("cash_to_st_debt") and metrics["cash_to_st_debt"].value and metrics["cash_to_st_debt"].value >= 1.0:
        strengths.append("Thanh khoản tốt - Tiền mặt đủ trả nợ ngắn hạn")

    if metrics.get("interest_coverage") and metrics["interest_coverage"].value and metrics["interest_coverage"].value >= 3.0:
        strengths.append("Khả năng chi trả lãi vay an toàn")

    if metrics.get("debt_to_equity") and metrics["debt_to_equity"].value and metrics["debt_to_equity"].value < 1.0:
        strengths.append("Đòn bẩy thận trọng - Rủi ro tài chính thấp")

    if metrics.get("gross_margin") and metrics["gross_margin"].value and metrics["gross_margin"].value >= 40:
        strengths.append("Biên lợi nhuận gộp cao - Dự án chất lượng")

    return strengths if strengths else ["Không có điểm mạnh nổi bật"]


def _extract_risks(metrics: Dict[str, REMetric]) -> list[str]:
    """Trích xuất rủi ro từ các chỉ số"""
    risks = []

    if metrics.get("cash_to_st_debt") and metrics["cash_to_st_debt"].value and metrics["cash_to_st_debt"].value < 0.5:
        risks.append("Rủi ro thanh khoản - Tiền mặt không đủ trả nợ ngắn hạn")

    if metrics.get("interest_coverage") and metrics["interest_coverage"].value and metrics["interest_coverage"].value < 1.5:
        risks.append("Rủi ro phục vụ nợ - Khó khăn trong việc chi trả lãi vay")

    if metrics.get("debt_to_equity") and metrics["debt_to_equity"].value and metrics["debt_to_equity"].value > 3.0:
        risks.append("Đòn bẩy quá cao - Rủi ro tài chính lớn")

    if metrics.get("gross_margin") and metrics["gross_margin"].value and metrics["gross_margin"].value < 25:
        risks.append("Biên lợi nhuận thấp - Áp lực cạnh tranh lớn")

    return risks if risks else ["Không có rủi ro nghiêm trọng"]


def _generate_recommendations(metrics: Dict[str, REMetric], health_score: Dict[str, Any]) -> list[str]:
    """Tạo khuyến nghị từ phân tích"""
    recommendations = []

    if metrics.get("cash_to_st_debt") and metrics["cash_to_st_debt"].value and metrics["cash_to_st_debt"].value < 0.5:
        recommendations.append("Cần ưu tiên cải thiện thanh khoản: Huy động vốn, tăng tốc độ bán hàng, hoặc tái cấu trúc nợ")

    if metrics.get("debt_to_equity") and metrics["debt_to_equity"].value and metrics["debt_to_equity"].value > 2.0:
        recommendations.append("Nên giảm đòn bẩy dần: Tăng vốn chủ, hoặc cân đối lại lịch trình phát triển dự án")

    if metrics.get("gross_margin") and metrics["gross_margin"].value and metrics["gross_margin"].value < 25:
        recommendations.append("Cần xem xét lại chiến lược定价: Tìm vị trí dự án tốt hơn, hoặc giảm chi phí xây dựng")

    if health_score["total_score"] < 60:
        recommendations.append("Sức khỏe tài chính trung bình - Cần xây dựng kế hoạch cải thiện toàn diện")

    return recommendations if recommendations else ["Duy trì chiến lược hiện tại, theo dõi định kỳ các chỉ số"]
