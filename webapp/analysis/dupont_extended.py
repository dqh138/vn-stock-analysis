"""
Extended DuPont Analysis (5-Component)

Phân tích DuPont mở rộng với 5 thành phần:
1. Tax Burden = Net Income / EBT (Gánh nặng thuế)
2. Interest Burden = EBT / EBIT (Gánh nặng lãi vay)
3. Operating Margin = EBIT / Revenue (Biên lợi nhuận hoạt động)
4. Asset Turnover = Revenue / Total Assets (Vòng quay tài sản)
5. Financial Leverage = Total Assets / Total Equity (Đòn bẩy tài chính)

ROE = Tax Burden × Interest Burden × Operating Margin × Asset Turnover × Financial Leverage

Author: Financial Analysis Engine
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from .annual_selector import (
    get_financial_ratios_annual,
    get_latest_year,
    select_balance_sheet_annual,
    select_income_statement_annual,
)
from .data_contract import get_value

def calculate_extended_dupont(
    income_statement: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    financial_ratios: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Tính toán phân tích DuPont mở rộng (5 thành phần)

    Args:
        income_statement: Dict chứa báo cáo kết quả kinh doanh
        balance_sheet: Dict chứa bảng cân đối kế toán
        financial_ratios: Dict chứa các chỉ số tài chính

    Returns:
        Dict chứa kết quả phân tích DuPont mở rộng
    """
    # Lấy dữ liệu cần thiết
    net_income = get_value(income_statement, "net_income")
    ebt = get_value(income_statement, "profit_before_tax")

    # EBIT (Earnings Before Interest and Taxes)
    # Prefer operating_profit (closest proxy for EBIT in this dataset).
    # Fallback: EBT + financial_expense (sign-preserving).
    operating_profit = get_value(income_statement, "operating_profit")
    financial_expense = get_value(income_statement, "financial_expense")
    if operating_profit is not None:
        ebit = operating_profit
    elif financial_expense is not None and ebt is not None:
        ebit = ebt + financial_expense
    else:
        ebit = None

    # CRITICAL: use canonical "revenue" mapping (prefers net_revenue over revenue)
    # to avoid tiny/credit-style revenue fields causing distorted margins.
    revenue = get_value(income_statement, "revenue")
    total_assets = get_value(balance_sheet, "total_assets")
    total_equity = get_value(balance_sheet, "total_equity")

    # Lấy ROE từ financial_ratios nếu có
    roe = get_value(financial_ratios, "roe")

    # Tính toán các thành phần DuPont mở rộng
    components = {}
    has_data = False

    # 1. Tax Burden = Net Income / EBT
    tax_burden = None
    if ebt is not None and ebt != 0 and net_income is not None:
        tax_burden = net_income / ebt
        has_data = True
    components['tax_burden'] = {
        'value': tax_burden,
        'label': 'Gánh nặng thuế',
        'description': 'Thuế ảnh hưởng thế nào đến lợi nhuận',
        'formula': 'Net Income / EBT'
    }

    # 2. Interest Burden = EBT / EBIT
    interest_burden = None
    if ebit is not None and ebit != 0 and ebt is not None:
        interest_burden = ebt / ebit
        has_data = True
    components['interest_burden'] = {
        'value': interest_burden,
        'label': 'Gánh nặng lãi vay',
        'description': 'Chi phí lãi vay ảnh hưởng thế nào đến lợi nhuận',
        'formula': 'EBT / EBIT'
    }

    # 3. Operating Margin = EBIT / Revenue
    operating_margin = None
    if revenue is not None and revenue != 0 and ebit is not None:
        operating_margin = ebit / revenue
        has_data = True
    components['operating_margin'] = {
        'value': operating_margin,
        'label': 'Biên lợi nhuận hoạt động',
        'description': 'Hiệu quả hoạt động cốt lõi',
        'formula': 'EBIT / Revenue'
    }

    # 4. Asset Turnover = Revenue / Total Assets
    asset_turnover = None
    if total_assets is not None and total_assets != 0 and revenue is not None:
        asset_turnover = revenue / total_assets
        has_data = True
    components['asset_turnover'] = {
        'value': asset_turnover,
        'label': 'Vòng quay tài sản',
        'description': 'Hiệu quả sử dụng tài sản',
        'formula': 'Revenue / Total Assets'
    }

    # 5. Financial Leverage = Total Assets / Total Equity
    financial_leverage = None
    if total_equity is not None and total_equity != 0 and total_assets is not None:
        financial_leverage = total_assets / total_equity
        has_data = True
    components['financial_leverage'] = {
        'value': financial_leverage,
        'label': 'Đòn bẩy tài chính',
        'description': 'Mức độ sử dụng nợ để tài trợ',
        'formula': 'Total Assets / Total Equity'
    }

    # Tính toán ROE từ DuPont (nếu có đủ thành phần)
    dupont_roe = None
    if all(c['value'] is not None for c in components.values()):
        dupont_roe = (tax_burden * interest_burden * operating_margin *
                     asset_turnover * financial_leverage)

    # Tính toán đóng góp của từng thành phần vào ROE
    contribution = _calculate_component_contribution(components, dupont_roe)

    return {
        'roe': roe,
        'dupont_roe': dupont_roe,
        'components': components,
        'contribution': contribution,
        'has_data': has_data,
        'interpretation': _interpret_dupont_extended(components, roe)
    }


def _calculate_component_contribution(
    components: Dict[str, Dict[str, Any]],
    dupont_roe: Optional[float]
) -> Dict[str, Any]:
    """
    Tính toán đóng góp của từng thành phần vào ROE

    Args:
        components: Dict chứa các thành phần DuPont
        dupont_roe: ROE tính từ DuPont

    Returns:
        Dict chứa thông tin đóng góp
    """
    if dupont_roe is None or dupont_roe == 0:
        return {}

    contribution = {}
    cumulative = 1.0

    # Thứ tự đóng góp: Tax Burden → Interest Burden → Operating Margin → Asset Turnover → Financial Leverage
    order = ['tax_burden', 'interest_burden', 'operating_margin', 'asset_turnover', 'financial_leverage']

    for key in order:
        comp = components.get(key, {})
        value = comp.get('value')

        if value is None:
            contribution[key] = {
                'value': None,
                'cumulative_effect': None,
                'contribution_pct': None
            }
            continue

        prev_cumulative = cumulative
        cumulative *= value

        # Tính toán đóng góp lũy tiến
        contribution[key] = {
            'value': value,
            'cumulative_effect': cumulative,
            'incremental_effect': cumulative - prev_cumulative,
            'contribution_pct': (cumulative / dupont_roe * 100) if dupont_roe != 0 else None
        }

    return contribution


def _interpret_dupont_extended(
    components: Dict[str, Dict[str, Any]],
    roe: Optional[float]
) -> str:
    """
    Diễn giải kết quả phân tích DuPont mở rộng

    Args:
        components: Dict chứa các thành phần DuPont
        roe: ROE

    Returns:
        Chuỗi diễn giải tiếng Việt
    """
    if not any(c.get('value') is not None for c in components.values()):
        return "Không đủ dữ liệu để phân tích DuPont mở rộng."

    interpretations = []

    # Tax Burden
    tax_burden = components.get('tax_burden', {}).get('value')
    if tax_burden is not None:
        if tax_burden >= 0.85:
            interpretations.append(
                f"Tỷ lệ gánh nặng thuế cao ({tax_burden:.1%}), "
                "doanh nghiệp được hưởng ưu đãi thuế hoặc có quản lý thuế tốt."
            )
        elif tax_burden >= 0.75:
            interpretations.append(
                f"Tỷ lệ gánh nặng thuế ở mức trung bình ({tax_burden:.1%})."
            )
        else:
            interpretations.append(
                f"Tỷ lệ gánh nặng thuế thấp ({tax_burden:.1%}), "
                "doanh nghiệp chịu mức thuế suất thực tế cao."
            )

    # Interest Burden
    interest_burden = components.get('interest_burden', {}).get('value')
    if interest_burden is not None:
        if interest_burden >= 0.95:
            interpretations.append(
                f"Gánh nặng lãi vay rất thấp ({interest_burden:.1%}), "
                "doanh nghiệp sử dụng nợ ít hoặc chi phí lãi vay thấp."
            )
        elif interest_burden >= 0.85:
            interpretations.append(
                f"Gánh nặng lãi vay ở mức chấp nhận được ({interest_burden:.1%})."
            )
        else:
            interpretations.append(
                f"Gánh nặng lãi vay cao ({interest_burden:.1%}), "
                "chi phí lãi vay ảnh hưởng đáng kể đến lợi nhuận."
            )

    # Operating Margin
    operating_margin = components.get('operating_margin', {}).get('value')
    if operating_margin is not None:
        if operating_margin >= 0.20:
            interpretations.append(
                f"Biên lợi nhuận hoạt động xuất sắc ({operating_margin:.1%}), "
                "doanh nghiệp có lợi thế cạnh tranh mạnh."
            )
        elif operating_margin >= 0.10:
            interpretations.append(
                f"Biên lợi nhuận hoạt động tốt ({operating_margin:.1%})."
            )
        elif operating_margin >= 0.05:
            interpretations.append(
                f"Biên lợi nhuận hoạt động trung bình ({operating_margin:.1%})."
            )
        else:
            interpretations.append(
                f"Biên lợi nhuận hoạt động thấp ({operating_margin:.1%}), "
                "cần cải thiện hiệu quả hoạt động."
            )

    # Asset Turnover
    asset_turnover = components.get('asset_turnover', {}).get('value')
    if asset_turnover is not None:
        if asset_turnover >= 1.5:
            interpretations.append(
                f"Vòng quay tài sản rất cao ({asset_turnover:.2f}x), "
                "sử dụng tài sản rất hiệu quả."
            )
        elif asset_turnover >= 1.0:
            interpretations.append(
                f"Vòng quay tài sản tốt ({asset_turnover:.2f}x)."
            )
        elif asset_turnover >= 0.5:
            interpretations.append(
                f"Vòng quay tài sản trung bình ({asset_turnover:.2f}x)."
            )
        else:
            interpretations.append(
                f"Vòng quay tài sản thấp ({asset_turnover:.2f}x), "
                "cần tối ưu hóa sử dụng tài sản."
            )

    # Financial Leverage
    financial_leverage = components.get('financial_leverage', {}).get('value')
    if financial_leverage is not None:
        if financial_leverage >= 3.0:
            interpretations.append(
                f"Đòn bẩy tài chính rất cao ({financial_leverage:.2f}x), "
                "rủi ro tài chính lớn nhưng có thể tăng cường ROE."
            )
        elif financial_leverage >= 2.0:
            interpretations.append(
                f"Đòn bẩy tài chính cao ({financial_leverage:.2f}x), "
                "sử dụng nợ đáng kể để tài trợ hoạt động."
            )
        elif financial_leverage >= 1.5:
            interpretations.append(
                f"Đòn bẩy tài chính trung bình ({financial_leverage:.2f}x)."
            )
        else:
            interpretations.append(
                f"Đòn bẩy tài chính thấp ({financial_leverage:.2f}x), "
                "sử dụng vốn chủ sở hữu nhiều hơn nợ."
            )

    # ROE interpretation
    if roe is not None:
        if roe >= 0.20:
            interpretations.append(
                f"Tổng thể: ROE cao ({roe:.1%}), cho thấy khả năng sinh lời trên vốn chủ sở hữu xuất sắc."
            )
        elif roe >= 0.15:
            interpretations.append(
                f"Tổng thể: ROE tốt ({roe:.1%}), khả năng sinh lời trên vốn chủ sở hữu ở mức ổn định."
            )
        elif roe >= 0.10:
            interpretations.append(
                f"Tổng thể: ROE trung bình ({roe:.1%}), cần cải thiện hiệu quả sử dụng vốn."
            )
        else:
            interpretations.append(
                f"Tổng thể: ROE thấp ({roe:.1%}), cần xem xét lại chiến lược vốn và hiệu quả hoạt động."
            )

    return " ".join(interpretations)


def get_extended_dupont_from_db(
    db_path=None,
    symbol: str = "",
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Lấy dữ liệu và tính toán phân tích DuPont mở rộng từ database

    Args:
        db_path: Ignored; connection comes from DATABASE_URL
        symbol: Mã chứng khoán
        year: Năm cần phân tích (nếu None, lấy năm mới nhất)

    Returns:
        Dict chứa kết quả phân tích DuPont mở rộng
    """
    from .. import db as _db
    with _db.connect() as conn:
        try:
            effective_year = int(year) if year is not None else get_latest_year(conn, symbol)
            if effective_year is None:
                return {
                    "symbol": symbol,
                    "year": year,
                    "effective_year": None,
                    "error": "No annual data available",
                }

            financial_ratios = get_financial_ratios_annual(conn, symbol, effective_year)
            income_statement = select_income_statement_annual(conn, symbol, effective_year)
            balance_sheet = select_balance_sheet_annual(conn, symbol, effective_year, financial_ratios_row=financial_ratios)
        except Exception:
            raise

    if not income_statement or not balance_sheet:
        return {
            "symbol": symbol,
            "year": year,
            "effective_year": effective_year,
            "error": "Insufficient data",
        }

    # Tính toán DuPont mở rộng
    result = calculate_extended_dupont(income_statement, balance_sheet, financial_ratios)

    # Thêm thông tin metadata
    result["symbol"] = symbol
    result["year"] = year
    result["effective_year"] = effective_year

    return result


def compare_extended_dupont_years(
    db_path=None,
    symbol: str = "",
    year1: int = 0,
    year2: int = 0
) -> Dict[str, Any]:
    """
    So sánh phân tích DuPont mở rộng giữa 2 năm

    Args:
        db_path: Ignored; connection comes from DATABASE_URL
        symbol: Mã chứng khoán
        year1: Năm đầu tiên
        year2: Năm thứ hai

    Returns:
        Dict chứa kết quả so sánh
    """
    result1 = get_extended_dupont_from_db(db_path, symbol, year1)
    result2 = get_extended_dupont_from_db(db_path, symbol, year2)

    comparison = {
        'symbol': symbol,
        'year1': year1,
        'year2': year2,
        'data1': result1,
        'data2': result2,
        'changes': {}
    }

    # Tính toán thay đổi từng thành phần
    components = ['tax_burden', 'interest_burden', 'operating_margin',
                 'asset_turnover', 'financial_leverage']

    for comp in components:
        val1 = result1.get('components', {}).get(comp, {}).get('value')
        val2 = result2.get('components', {}).get(comp, {}).get('value')

        if val1 is not None and val2 is not None:
            change = val2 - val1
            change_pct = ((val2 - val1) / val1 * 100) if val1 != 0 else None

            comparison['changes'][comp] = {
                'value1': val1,
                'value2': val2,
                'change': change,
                'change_pct': change_pct,
                'improved': change > 0 if comp in ['tax_burden', 'interest_burden',
                                                     'operating_margin', 'asset_turnover']
                             else change < 0  # Financial leverage: lower is better
            }

    # So sánh ROE
    roe1 = result1.get('roe')
    roe2 = result2.get('roe')
    if roe1 is not None and roe2 is not None:
        comparison['changes']['roe'] = {
            'value1': roe1,
            'value2': roe2,
            'change': roe2 - roe1,
            'change_pct': ((roe2 - roe1) / roe1 * 100) if roe1 != 0 else None,
            'improved': roe2 > roe1
        }

    return comparison
