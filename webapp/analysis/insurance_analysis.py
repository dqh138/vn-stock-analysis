"""
Insurance Industry Analysis Module
Analyzes insurance companies with industry-specific metrics including:
- Combined Ratio (underwriting profitability)
- Investment Yield (investment returns)
- Loss & Expense Ratios (operational efficiency)
- Solvency & Capital Strength
- Premium Growth & Float Utilization
"""

from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def analyze_insurance_industry(
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any],
    cash_flow: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze insurance company with industry-specific metrics.

    Args:
        financial_ratios: Dict of calculated financial ratios
        balance_sheet: Dict of balance sheet items
        income_statement: Dict of income statement items
        cash_flow: Dict of cash flow items

    Returns:
        Dict with insurance metrics, ratings, and quality score
    """

    metrics = {}
    ratings = {}

    # Extract key values
    revenue = income_statement.get('revenue', 0) or income_statement.get('net_sales', 0) or 0
    cogs = income_statement.get('cogs', 0) or income_statement.get('cost_of_revenue', 0) or 0
    admin_expense = income_statement.get('sga_expense', 0) or income_statement.get('admin_expense', 0) or 0
    selling_expense = income_statement.get('selling_expense', 0) or 0
    financial_income = income_statement.get('financial_income', 0) or income_statement.get('other_income', 0) or 0
    other_income = income_statement.get('other_income', 0) or 0

    total_assets = balance_sheet.get('total_assets', 0) or 0
    current_liabilities = balance_sheet.get('current_liabilities', 0) or 0
    total_liabilities = balance_sheet.get('total_liabilities', 0) or 0
    equity = balance_sheet.get('equity', 0) or balance_sheet.get('total_equity', 0) or 0

    net_income = income_statement.get('net_income', 0) or 0

    # Get year-over-year growth data
    revenue_yoy_growth = financial_ratios.get('revenue_yoy_growth', 0) or 0
    equity_yoy_growth = financial_ratios.get('equity_yoy_growth', 0) or 0
    roe = financial_ratios.get('roe', 0) or 0
    roa = financial_ratios.get('roa', 0) or 0

    # === 1. COMBINED RATIO (Underwriting Profitability) ===
    # Combined Ratio = (Claims + Expenses) / Premiums
    # Proxy: (COGS + Admin + Selling) / Revenue
    # < 95% = Profitable underwriting, 95-100% = Marginal, > 100% = Underwriting loss

    combined_ratio = None
    combined_ratio_rating = "Không đủ dữ liệu"
    if revenue > 0:
        combined_ratio = ((cogs + admin_expense + selling_expense) / revenue) * 100
        if combined_ratio < 95:
            combined_ratio_rating = "Tốt - Có lãi từ nghiệp vụ bảo hiểm"
        elif combined_ratio < 100:
            combined_ratio_rating = "Trung bình - Đạt điểm hòa vốn"
        else:
            combined_ratio_rating = "Yếu - Lỗ từ nghiệp vụ bảo hiểm"

    metrics['combined_ratio'] = {
        'value': combined_ratio,
        'label': 'Tỷ lệ kết hợp (Combined Ratio)',
        'rating': combined_ratio_rating,
        'description': 'Đ衡量 tính sinh lời của nghiệp vụ bảo hiểm. < 95% là tốt'
    }

    # === 2. INVESTMENT YIELD (Investment Returns) ===
    # Investment Yield = Financial Income / Investment Assets
    # Proxy: Financial Income / Total Assets
    # Or: Other Income / Total Assets * factor
    # > 5% = Good, 3-5% = Normal, < 3% = Low

    investment_yield = None
    investment_yield_rating = "Không đủ dữ liệu"
    if total_assets > 0 and financial_income > 0:
        investment_yield = (financial_income / total_assets) * 100
        if investment_yield > 5:
            investment_yield_rating = "Tốt - Hiệu quả đầu tư cao"
        elif investment_yield > 3:
            investment_yield_rating = "Trung bình - Hiệu quả đầu tư bình thường"
        else:
            investment_yield_rating = "Yếu - Hiệu quả đầu tư thấp"
    elif total_assets > 0 and other_income > 0:
        # Use other income as proxy
        investment_yield = (other_income / total_assets) * 100
        if investment_yield > 5:
            investment_yield_rating = "Tốt - Thu nhập khác cao"
        elif investment_yield > 3:
            investment_yield_rating = "Trung bình - Thu nhập khác bình thường"
        else:
            investment_yield_rating = "Yếu - Thu nhập khác thấp"

    metrics['investment_yield'] = {
        'value': investment_yield,
        'label': 'Tỷ suất sinh lời đầu tư (Investment Yield)',
        'rating': investment_yield_rating,
        'description': 'Hiệu quả đầu tư trên tài sản. > 5% là tốt'
    }

    # === 3. LOSS RATIO PROXY (Claims Efficiency) ===
    # Loss Ratio = Claims Paid / Premiums Earned
    # Proxy: COGS / Revenue
    # Lower = better underwriting

    loss_ratio = None
    loss_ratio_rating = "Không đủ dữ liệu"
    if revenue > 0:
        loss_ratio = (cogs / revenue) * 100
        if loss_ratio < 60:
            loss_ratio_rating = "Tốt - Tỷ lệ bồi thường thấp"
        elif loss_ratio < 75:
            loss_ratio_rating = "Trung bình - Tỷ lệ bồi thường ổn định"
        else:
            loss_ratio_rating = "Cần xem xét - Tỷ lệ bồi thường cao"

    metrics['loss_ratio'] = {
        'value': loss_ratio,
        'label': 'Tỷ lệ bồi thường (Loss Ratio)',
        'rating': loss_ratio_rating,
        'description': 'Tỷ lệ chi phí bồi thường trên phí thu. Thấp hơn là tốt hơn'
    }

    # === 4. EXPENSE RATIO PROXY (Operational Efficiency) ===
    # Expense Ratio = Operating Expenses / Premiums
    # Proxy: (Admin + Selling) / Revenue
    # < 25% = Efficient, 25-35% = Normal, > 35% = High

    expense_ratio = None
    expense_ratio_rating = "Không đủ dữ liệu"
    if revenue > 0:
        expense_ratio = ((admin_expense + selling_expense) / revenue) * 100
        if expense_ratio < 25:
            expense_ratio_rating = "Tốt - Hoạt động hiệu quả"
        elif expense_ratio < 35:
            expense_ratio_rating = "Trung bình - Chi phí bình thường"
        else:
            expense_ratio_rating = "Cần cải thiện - Chi phí cao"

    metrics['expense_ratio'] = {
        'value': expense_ratio,
        'label': 'Tỷ lệ chi phí (Expense Ratio)',
        'rating': expense_ratio_rating,
        'description': 'Tỷ lệ chi phí hoạt động trên phí thu. < 25% là hiệu quả'
    }

    # === 5. PREMIUM GROWTH (Business Growth) ===
    # YoY revenue growth
    # > 15% = Strong, 8-15% = Good, < 8% = Slow

    premium_growth = None
    premium_growth_rating = "Không đủ dữ liệu"
    if revenue_yoy_growth is not None:
        premium_growth = revenue_yoy_growth
        if premium_growth > 15:
            premium_growth_rating = "Tốt - Tăng trưởng mạnh"
        elif premium_growth > 8:
            premium_growth_rating = "Khá - Tăng trưởng ổn định"
        elif premium_growth > 0:
            premium_growth_rating = "Trung bình - Tăng trưởng chậm"
        else:
            premium_growth_rating = "Yếu - Suy giảm doanh thu"

    metrics['premium_growth'] = {
        'value': premium_growth,
        'label': 'Tăng trưởng phí thu (Premium Growth)',
        'rating': premium_growth_rating,
        'description': 'Tốc độ tăng trưởng doanh thu năm qua. > 15% là mạnh'
    }

    # === 6. SOLVENCY PROXY (Capital Strength) ===
    # Solvency Ratio = Equity / Total Assets
    # Higher = better cushion
    # > 15% = Strong, 10-15% = Adequate, < 10% = Watch

    solvency_ratio = None
    solvency_rating = "Không đủ dữ liệu"
    if total_assets > 0:
        solvency_ratio = (equity / total_assets) * 100
        if solvency_ratio > 15:
            solvency_rating = "Mạnh - Vốn chủ sở hữu cao"
        elif solvency_ratio > 10:
            solvency_rating = "Đủ - Vốn chủ sở hữu ổn định"
        else:
            solvency_rating = "Cần xem xét - Vốn chủ sở hữu thấp"

    metrics['solvency_ratio'] = {
        'value': solvency_ratio,
        'label': 'Tỷ lệ thanh khả thi (Solvency Ratio)',
        'rating': solvency_rating,
        'description': 'Độ mạnh vốn. > 15% là mạnh'
    }

    # === 7. FLOAT UTILIZATION (Investment Capital) ===
    # Insurance float = premiums collected before claims
    # Current Liabilities / Total Assets (higher = more float)
    # More float = more investment capital

    float_utilization = None
    float_rating = "Không đủ dữ liệu"
    if total_assets > 0:
        float_utilization = (current_liabilities / total_assets) * 100
        if float_utilization > 40:
            float_rating = "Cao - Nhiều vốn đầu tư từ phí thu"
        elif float_utilization > 25:
            float_rating = "Trung bình - Vốn đầu tư bình thường"
        else:
            float_rating = "Thấp - Ít vốn đầu tư từ phí thu"

    metrics['float_utilization'] = {
        'value': float_utilization,
        'label': 'Tỷ lệ sử dụng quỹ (Float Utilization)',
        'rating': float_rating,
        'description': 'Tỷ lệ nợ ngắn hạn trên tổng tài sản (phí thu chưa thanh toán). Cao hơn = nhiều vốn đầu tư hơn'
    }

    # === 8. ROE (Return on Equity) ===
    # Insurance should generate good ROE on thin margins
    # > 12% = Good, 8-12% = Adequate, < 8% = Weak

    roe_rating = "Không đủ dữ liệu"
    if roe is not None:
        if roe > 12:
            roe_rating = "Tốt - Sinh lời vốn cao"
        elif roe > 8:
            roe_rating = "Đủ - Sinh lời vốn ổn định"
        elif roe > 0:
            roe_rating = "Thấp - Sinh lời vốn kém"
        else:
            roe_rating = "Yếu - Vốn sinh lời âm"

    metrics['roe'] = {
        'value': roe,
        'label': 'Tỷ suất sinh lời trên vốn chủ sở hữu (ROE)',
        'rating': roe_rating,
        'description': 'Đ衡量 hiệu quả sử dụng vốn. > 12% là tốt'
    }

    # === CALCULATE QUALITY SCORE ===
    # Underwriting (30%): Combined Ratio, Loss Ratio
    # Investment (25%): Investment Yield, ROA
    # Capital Strength (25%): Solvency Ratio, ROE
    # Growth (20%): Premium Growth, Float Growth (proxy: equity growth)

    score_components = {}
    total_score = 0
    max_score = 0

    # Underwriting Score (30%)
    underwriting_score = 0
    underwriting_max = 30

    if combined_ratio is not None:
        if combined_ratio < 95:
            underwriting_score += 15  # Max points for combined ratio
        elif combined_ratio < 100:
            underwriting_score += 10  # Marginal
        else:
            underwriting_score += 5   # Underwriting loss
        max_score += 15

    if loss_ratio is not None:
        if loss_ratio < 60:
            underwriting_score += 15
        elif loss_ratio < 75:
            underwriting_score += 10
        else:
            underwriting_score += 5
        max_score += 15

    score_components['underwriting'] = {
        'score': underwriting_score,
        'max_score': underwriting_max,
        'percentage': (underwriting_score / underwriting_max * 100) if underwriting_max > 0 else 0
    }

    # Investment Score (25%)
    investment_score = 0
    investment_max = 25

    if investment_yield is not None:
        if investment_yield > 5:
            investment_score += 12.5
        elif investment_yield > 3:
            investment_score += 8
        else:
            investment_score += 4
        max_score += 12.5

    if roa is not None:
        if roa > 5:
            investment_score += 12.5
        elif roa > 3:
            investment_score += 8
        else:
            investment_score += 4
        max_score += 12.5

    score_components['investment'] = {
        'score': investment_score,
        'max_score': investment_max,
        'percentage': (investment_score / investment_max * 100) if investment_max > 0 else 0
    }

    # Capital Strength Score (25%)
    capital_score = 0
    capital_max = 25

    if solvency_ratio is not None:
        if solvency_ratio > 15:
            capital_score += 12.5
        elif solvency_ratio > 10:
            capital_score += 8
        else:
            capital_score += 4
        max_score += 12.5

    if roe is not None:
        if roe > 12:
            capital_score += 12.5
        elif roe > 8:
            capital_score += 8
        else:
            capital_score += 4
        max_score += 12.5

    score_components['capital_strength'] = {
        'score': capital_score,
        'max_score': capital_max,
        'percentage': (capital_score / capital_max * 100) if capital_max > 0 else 0
    }

    # Growth Score (20%)
    growth_score = 0
    growth_max = 20

    if premium_growth is not None:
        if premium_growth > 15:
            growth_score += 10
        elif premium_growth > 8:
            growth_score += 7
        elif premium_growth > 0:
            growth_score += 4
        else:
            growth_score += 2
        max_score += 10

    if equity_yoy_growth is not None:
        if equity_yoy_growth > 10:
            growth_score += 10
        elif equity_yoy_growth > 5:
            growth_score += 7
        elif equity_yoy_growth > 0:
            growth_score += 4
        else:
            growth_score += 2
        max_score += 10

    score_components['growth'] = {
        'score': growth_score,
        'max_score': growth_max,
        'percentage': (growth_score / growth_max * 100) if growth_max > 0 else 0
    }

    # Calculate final quality score
    total_score = underwriting_score + investment_score + capital_score + growth_score
    quality_percentage = (total_score / 100 * 100) if max_score > 0 else 0

    # Determine overall quality rating
    if quality_percentage >= 80:
        overall_rating = "Chất lượng cao - Công ty bảo hiểm mạnh"
    elif quality_percentage >= 65:
        overall_rating = "Chất lượng tốt - Hoạt động ổn định"
    elif quality_percentage >= 50:
        overall_rating = "Chất lượng trung bình - Cần cải thiện"
    elif quality_percentage >= 35:
        overall_rating = "Chất lượng yếu - Nhiều rủi ro"
    else:
        overall_rating = "Chất lượng kém - Cần xem xét kỹ"

    # Compile result
    result = {
        'metrics': metrics,
        'quality_score': {
            'total_score': total_score,
            'max_score': 100,
            'percentage': quality_percentage,
            'rating': overall_rating,
            'components': score_components
        },
        'summary': {
            'underwriting_profitability': combined_ratio_rating,
            'investment_performance': investment_yield_rating,
            'capital_strength': solvency_rating,
            'growth_trend': premium_growth_rating,
            'overall_assessment': overall_rating
        }
    }

    logger.info(f"Insurance analysis completed. Quality Score: {quality_percentage:.1f}/100 - {overall_rating}")

    return result


def format_insurance_analysis(analysis: Dict[str, Any]) -> str:
    """
    Format insurance analysis results for display.

    Args:
        analysis: Dict from analyze_insurance_industry()

    Returns:
        Formatted string with Vietnamese labels
    """

    if not analysis:
        return "Không có dữ liệu phân tích bảo hiểm"

    lines = []
    lines.append("=" * 60)
    lines.append("PHÂN TÍCH NGÀNH BẢO HIỂM")
    lines.append("=" * 60)
    lines.append("")

    # Quality Score
    quality = analysis.get('quality_score', {})
    lines.append("ĐÁNH GIÁ CHẤT LƯỢNG TỔNG QUAN")
    lines.append("-" * 40)
    lines.append(f"Điểm số: {quality.get('percentage', 0):.1f}/100")
    lines.append(f"Xếp hạng: {quality.get('rating', 'N/A')}")
    lines.append("")

    # Components
    components = quality.get('components', {})
    lines.append("CHI TIẾT ĐIỂM SỐ:")
    for component_name, component_data in components.items():
        lines.append(f"  {component_name}: {component_data['score']:.1f}/{component_data['max_score']} ({component_data['percentage']:.1f}%)")
    lines.append("")

    # Metrics
    metrics = analysis.get('metrics', {})
    lines.append("CHỈ SỐ BẢO HIỂM:")
    lines.append("-" * 40)

    for metric_key, metric_data in metrics.items():
        value = metric_data.get('value')
        label = metric_data.get('label', '')
        rating = metric_data.get('rating', '')
        description = metric_data.get('description', '')

        if value is not None:
            if 'ratio' in metric_key.lower() or 'growth' in metric_key.lower() or 'yield' in metric_key.lower() or 'roe' in metric_key.lower():
                lines.append(f"{label}: {value:.2f}%")
            else:
                lines.append(f"{label}: {value:.2f}")
        else:
            lines.append(f"{label}: N/A")

        lines.append(f"  Đánh giá: {rating}")
        if description:
            lines.append(f"  Giải thích: {description}")
        lines.append("")

    # Summary
    summary = analysis.get('summary', {})
    lines.append("TỔNG HỢP:")
    lines.append("-" * 40)
    lines.append(f"Khả năng sinh lời nghiệp vụ: {summary.get('underwriting_profitability', 'N/A')}")
    lines.append(f"Hiệu quả đầu tư: {summary.get('investment_performance', 'N/A')}")
    lines.append(f"Độ mạnh vốn: {summary.get('capital_strength', 'N/A')}")
    lines.append(f"Xu hướng tăng trưởng: {summary.get('growth_trend', 'N/A')}")
    lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


def get_insurance_strengths_weaknesses(analysis: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Extract key strengths and weaknesses from insurance analysis.

    Args:
        analysis: Dict from analyze_insurance_industry()

    Returns:
        Tuple of (strengths_dict, weaknesses_dict)
    """

    strengths = {}
    weaknesses = {}
    metrics = analysis.get('metrics', {})

    # Check Combined Ratio
    combined_ratio = metrics.get('combined_ratio', {}).get('value')
    if combined_ratio is not None and combined_ratio < 95:
        strengths['Nghiệp vụ bảo hiểm'] = f"Tỷ lệ kết hợp tốt ({combined_ratio:.1f}%) - Có lãi từ nghiệp vụ bảo hiểm"
    elif combined_ratio is not None and combined_ratio > 100:
        weaknesses['Nghiệp vụ bảo hiểm'] = f"Tỷ lệ kết hợp cao ({combined_ratio:.1f}%) - Lỗ từ nghiệp vụ bảo hiểm"

    # Check Investment Yield
    investment_yield = metrics.get('investment_yield', {}).get('value')
    if investment_yield is not None and investment_yield > 5:
        strengths['Hiệu quả đầu tư'] = f"Tỷ suất sinh lời cao ({investment_yield:.1f}%)"
    elif investment_yield is not None and investment_yield < 3:
        weaknesses['Hiệu quả đầu tư'] = f"Tỷ suất sinh lời thấp ({investment_yield:.1f}%)"

    # Check Solvency
    solvency_ratio = metrics.get('solvency_ratio', {}).get('value')
    if solvency_ratio is not None and solvency_ratio > 15:
        strengths['Độ mạnh vốn'] = f"Vốn chủ sở hữu cao ({solvency_ratio:.1f}%)"
    elif solvency_ratio is not None and solvency_ratio < 10:
        weaknesses['Độ mạnh vốn'] = f"Vốn chủ sở hữu thấp ({solvency_ratio:.1f}%) - Cần thận trọng"

    # Check Growth
    premium_growth = metrics.get('premium_growth', {}).get('value')
    if premium_growth is not None and premium_growth > 15:
        strengths['Tăng trưởng'] = f"Tăng trưởng doanh thu mạnh ({premium_growth:.1f}%)"
    elif premium_growth is not None and premium_growth < 0:
        weaknesses['Tăng trưởng'] = f"Doanh thu suy giảm ({premium_growth:.1f}%)"

    # Check ROE
    roe = metrics.get('roe', {}).get('value')
    if roe is not None and roe > 12:
        strengths['Sinh lời vốn'] = f"ROE cao ({roe:.1f}%) - Hiệu quả sử dụng vốn tốt"
    elif roe is not None and roe < 8:
        weaknesses['Sinh lời vốn'] = f"ROE thấp ({roe:.1f}%) - Hiệu quả sử dụng vốn kém"

    # Check Float
    float_utilization = metrics.get('float_utilization', {}).get('value')
    if float_utilization is not None and float_utilization > 40:
        strengths['Vốn đầu tư'] = f"Nhiều vốn từ phí thu ({float_utilization:.1f}%) - Tiềm năng đầu tư lớn"

    return strengths, weaknesses
