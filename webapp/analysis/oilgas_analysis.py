"""
Oil & Gas Industry Analysis Module
Phân tích ngành Dầu khí - Chuyên sâu cho các công ty dầu khí Việt Nam

Phase 6: Oil & Gas Industry Analysis
"""

import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime


def analyze_oil_gas_company(
    financial_ratios: Optional[Dict] = None,
    balance_sheet: Optional[Dict] = None,
    income_statement: Optional[Dict] = None,
    cash_flow: Optional[Dict] = None
) -> Dict:
    """
    Phân tích chuyên sâu cho công ty dầu khí

    Args:
        financial_ratios: Dict chứa các chỉ số tài chính
        balance_sheet: Dict chứa bảng cân đối kế toán
        income_statement: Dict chứa báo cáo kết quả kinh doanh
        cash_flow: Dict chứa báo cáo lưu chuyển tiền tệ

    Returns:
        Dict với tất cả metrics, ratings và health score
    """

    # Khởi tạo kết quả
    result = {
        'industry': 'Dầu khí',
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'metrics': {},
        'ratings': {},
        'health_score': {
            'total': 0,
            'components': {},
            'rating': '',
            'color': ''
        },
        'warnings': [],
        'strengths': [],
        'recommendations': []
    }

    # Lấy dữ liệu từ các nguồn
    ratios = financial_ratios or {}
    bs = balance_sheet or {}
    is_stmt = income_statement or {}
    cf = cash_flow or {}

    # ==================== METRIC 1: EBITDA MARGIN ====================
    ebitda_margin = calculate_ebitda_margin(is_stmt, ratios)
    result['metrics']['ebitda_margin'] = ebitda_margin
    result['metrics']['ebitda_margin_label'] = 'Biên lợi nhuận EBITDA'

    if ebitda_margin is not None:
        if ebitda_margin > 0.30:
            result['ratings']['ebitda_margin'] = 'Xuất sắc'
            result['strengths'].append(f'Biên EBITDA cao ({ebitda_margin:.1%}) - Hiệu quả vận hành tốt')
        elif ebitda_margin > 0.20:
            result['ratings']['ebitda_margin'] = 'Tốt'
        elif ebitda_margin > 0.10:
            result['ratings']['ebitda_margin'] = 'Trung bình'
        else:
            result['ratings']['ebitda_margin'] = 'Thấp'
            result['warnings'].append(f'Biên EBITDA thấp ({ebitda_margin:.1%}) - Cần cải thiện hiệu quả')

    # ==================== METRIC 2: DEBT/EBITDA ====================
    debt_ebitda = calculate_debt_ebitda(bs, is_stmt, ratios)
    result['metrics']['debt_ebitda'] = debt_ebitda
    result['metrics']['debt_ebitda_label'] = 'Nợ trên EBITDA'

    if debt_ebitda is not None:
        if debt_ebitda < 2:
            result['ratings']['debt_ebitda'] = 'Bảo thủ'
            result['strengths'].append(f'Dưới nợ thấp ({debt_ebitda:.1f}x) - An toàn tài chính')
        elif debt_ebitda < 3:
            result['ratings']['debt_ebitda'] = 'Bình thường'
        elif debt_ebitda < 4:
            result['ratings']['debt_ebitda'] = 'Cao'
            result['warnings'].append(f'Dưới nợ cao ({debt_ebitda:.1f}x) - Cần theo dõi')
        else:
            result['ratings']['debt_ebitda'] = 'Rủi ro'
            result['warnings'].append(f'Dưới nợ rất cao ({debt_ebitda:.1f}x) - Nguy cơ thanh khoản')

    # ==================== METRIC 3: INTEREST COVERAGE ====================
    interest_coverage = calculate_interest_coverage(is_stmt, ratios)
    result['metrics']['interest_coverage'] = interest_coverage
    result['metrics']['interest_coverage_label'] = 'Hệ số covering lãi vay'

    if interest_coverage is not None:
        if interest_coverage > 5:
            result['ratings']['interest_coverage'] = 'Mạnh'
            result['strengths'].append(f'Khả năng chi trả lãi vay tốt ({interest_coverage:.1f}x)')
        elif interest_coverage > 2:
            result['ratings']['interest_coverage'] = 'Đủ'
        else:
            result['ratings']['interest_coverage'] = 'Yếu'
            result['warnings'].append(f'Hệ số covering lãi vay thấp ({interest_coverage:.1f}x) - Nguy cơ vỡ nợ')

    # ==================== METRIC 4: CASH FLOW FROM OPERATIONS ====================
    ocf_analysis = analyze_operating_cash_flow(cf, is_stmt)
    result['metrics']['ocf'] = ocf_analysis.get('ocf')
    result['metrics']['ocf_trend'] = ocf_analysis.get('trend')
    result['metrics']['ocf_net_income_ratio'] = ocf_analysis.get('ocf_to_ni_ratio')
    result['metrics']['ocf_label'] = 'Lưu chuyển tiền từ hoạt động KD'

    if ocf_analysis.get('ocf_to_ni_ratio'):
        ratio = ocf_analysis['ocf_to_ni_ratio']
        if ratio > 1.2:
            result['ratings']['ocf_quality'] = 'Rất tốt'
            result['strengths'].append(f'Chất lượng tiền mặt tốt (OCF/NI = {ratio:.2f})')
        elif ratio > 0.8:
            result['ratings']['ocf_quality'] = 'Tốt'
        elif ratio > 0.5:
            result['ratings']['ocf_quality'] = 'Trung bình'
        else:
            result['ratings']['ocf_quality'] = 'Kém'
            result['warnings'].append('Chất lượng tiền mặt thấp - Cần kiểm tra khoản mục không tiền')

    # ==================== METRIC 5: CAPITAL INTENSITY ====================
    cap_intensity = calculate_capital_intensity(cf, is_stmt)
    result['metrics']['capital_intensity'] = cap_intensity
    result['metrics']['capital_intensity_label'] = 'Độ tập trung vốn'

    if cap_intensity is not None:
        if cap_intensity > 0.30:
            result['ratings']['capital_intensity'] = 'Rất cao (E&P)'
            result['ratings']['segment_type'] = 'Khai thác & Sản xuất'
        elif cap_intensity > 0.15:
            result['ratings']['capital_intensity'] = 'Cao'
            result['ratings']['segment_type'] = 'Khai thác & Sản xuất'
        elif cap_intensity > 0.05:
            result['ratings']['capital_intensity'] = 'Trung bình'
            result['ratings']['segment_type'] = 'Dịch vụ'
        else:
            result['ratings']['capital_intensity'] = 'Thấp'
            result['ratings']['segment_type'] = 'Dịch vụ/Điện'

    # ==================== METRIC 6: ASSET TURNOVER ====================
    asset_turnover = calculate_asset_turnover(is_stmt, bs, ratios)
    result['metrics']['asset_turnover'] = asset_turnover
    result['metrics']['asset_turnover_label'] = 'Vòng quay tài sản'

    if asset_turnover is not None:
        if asset_turnover > 0.8:
            result['ratings']['asset_turnover'] = 'Tốt'
        elif asset_turnover > 0.4:
            result['ratings']['asset_turnover'] = 'Trung bình'
        else:
            result['ratings']['asset_turnover'] = 'Thấp'
            result['warnings'].append(f'Vòng quay tài sản thấp ({asset_turnover:.2f}) - Hiệu quả sử dụng tài sản kém')

    # ==================== METRIC 7: RESERVE REPLACEMENT PROXY ====================
    reserve_proxy = calculate_reserve_replacement_proxy(cf, bs)
    result['metrics']['reserve_replacement_proxy'] = reserve_proxy
    result['metrics']['reserve_replacement_proxy_label'] = 'Proxy thay thế trữ lượng'

    if reserve_proxy is not None:
        if reserve_proxy > 1.3:
            result['ratings']['reserve_growth'] = 'Mạnh'
            result['strengths'].append(f'Đầu tư mạnh mẽ (CapEx/Dep = {reserve_proxy:.2f}) - Mở rộng trữ lượng')
        elif reserve_proxy > 1.0:
            result['ratings']['reserve_growth'] = 'Dương'
        elif reserve_proxy > 0.8:
            result['ratings']['reserve_growth'] = 'Duy trì'
        else:
            result['ratings']['reserve_growth'] = 'Giảm'
            result['warnings'].append('Đầu tư thấp hơn khấu hao - Trữ lượng có thể đang giảm')

    # ==================== METRIC 8: OIL PRICE SENSITIVITY ====================
    price_sensitivity = analyze_oil_price_sensitivity(is_stmt, ratios)
    result['metrics']['gross_margin_volatility'] = price_sensitivity.get('volatility')
    result['metrics']['price_sensitivity_label'] = 'Độ nhạy giá dầu'

    if price_sensitivity.get('volatility') is not None:
        vol = price_sensitivity['volatility']
        if vol > 0.15:
            result['ratings']['price_sensitivity'] = 'Cao'
            result['warnings'].append(f'Biên lợi nhuận biến động mạnh ({vol:.1%}) - Rủi ro giá dầu')
        elif vol > 0.08:
            result['ratings']['price_sensitivity'] = 'Trung bình'
        else:
            result['ratings']['price_sensitivity'] = 'Thấp'
            result['strengths'].append('Biên lợi nhuận ổn định - Rủi ro giá dầu thấp')

    # ==================== CALCULATE O&G HEALTH SCORE ====================
    health_score = calculate_oil_gas_health_score(result['metrics'], result['ratings'])
    result['health_score'] = health_score

    # ==================== GENERATE RECOMMENDATIONS ====================
    result['recommendations'] = generate_oil_gas_recommendations(result['metrics'], result['ratings'], result['warnings'])

    return result


# ==================== HELPER FUNCTIONS ====================

def calculate_ebitda_margin(income_stmt: Dict, ratios: Dict) -> Optional[float]:
    """Tính biên EBITDA = EBITDA / Doanh thu"""
    try:
        # Thử lấy EBITDA từ ratios
        if 'ebitda' in ratios and 'revenue' in ratios:
            ebitda = ratios['ebitda']
            revenue = ratios['revenue']
            if revenue and revenue > 0:
                return ebitda / revenue

        # Tính từ income statement
        if revenue := income_stmt.get('revenue') or income_stmt.get('doanh_thu'):
            ebit = income_stmt.get('ebit') or income_stmt.get('loi_nhuan_thuan')
            depreciation = income_stmt.get('depreciation') or income_stmt.get('khau_hao')

            if ebit is not None and depreciation is not None:
                ebitda = ebit + depreciation
                return ebitda / revenue if revenue > 0 else None

        return None
    except Exception:
        return None


def calculate_debt_ebitda(balance_sheet: Dict, income_stmt: Dict, ratios: Dict) -> Optional[float]:
    """Tính Debt/EBITDA = Tổng nợ / EBITDA"""
    try:
        # Lấy EBITDA
        ebitda = ratios.get('ebitda')
        if ebitda is None or ebitda <= 0:
            return None

        # Lấy tổng nợ
        total_debt = (balance_sheet.get('short_term_debt') or
                     balance_sheet.get('no_ngan_han') or 0)
        total_debt += (balance_sheet.get('long_term_debt') or
                      balance_sheet.get('no_dai_han') or 0)

        if total_debt and total_debt > 0:
            return total_debt / ebitda

        return None
    except Exception:
        return None


def calculate_interest_coverage(income_stmt: Dict, ratios: Dict) -> Optional[float]:
    """Tính Interest Coverage = EBIT / Interest Expense"""
    try:
        # Thử lấy từ ratios
        if 'interest_coverage' in ratios:
            return ratios['interest_coverage']

        # Tính từ income statement
        ebit = income_stmt.get('ebit') or income_stmt.get('loi_nhuan_thuan')
        interest_expense = (income_stmt.get('interest_expense') or
                           income_stmt.get('chi_phi_lai_vay') or
                           income_stmt.get('lai_vay_phai_tra'))

        if interest_expense and interest_expense != 0 and ebit is not None:
            return ebit / interest_expense

        return None
    except Exception:
        return None


def analyze_operating_cash_flow(cash_flow: Dict, income_stmt: Dict) -> Dict:
    """Phân tích lưu chuyển tiền từ hoạt động kinh doanh"""
    result = {
        'ocf': None,
        'trend': None,
        'ocf_to_ni_ratio': None
    }

    try:
        ocf = cash_flow.get('operating_cash_flow') or cash_flow.get('lctt_hdkd')
        net_income = (income_stmt.get('net_income') or
                     income_stmt.get('loi_nhuan_sau_thue'))

        result['ocf'] = ocf

        # Tính tỷ lệ OCF/Net Income
        if ocf is not None and net_income is not None and net_income != 0:
            result['ocf_to_ni_ratio'] = ocf / net_income

        # Phân tích xu hướng (nếu có nhiều năm)
        ocf_history = cash_flow.get('ocf_history') or []
        if len(ocf_history) >= 2:
            if ocf_history[-1] > ocf_history[-2] * 1.05:
                result['trend'] = 'Tăng'
            elif ocf_history[-1] < ocf_history[-2] * 0.95:
                result['trend'] = 'Giảm'
            else:
                result['trend'] = 'Ổn định'

        return result
    except Exception:
        return result


def calculate_capital_intensity(cash_flow: Dict, income_stmt: Dict) -> Optional[float]:
    """Tính Capital Intensity = CapEx / Revenue"""
    try:
        capex = (cash_flow.get('capital_expenditure') or
                cash_flow.get('mua_tscd') or
                cash_flow.get('capex'))

        revenue = (income_stmt.get('revenue') or
                  income_stmt.get('doanh_thu'))

        if capex and revenue and revenue > 0:
            return abs(capex) / revenue

        return None
    except Exception:
        return None


def calculate_asset_turnover(income_stmt: Dict, balance_sheet: Dict, ratios: Dict) -> Optional[float]:
    """Tính Asset Turnover = Revenue / Total Assets"""
    try:
        # Thử lấy từ ratios
        if 'asset_turnover' in ratios:
            return ratios['asset_turnover']

        revenue = (income_stmt.get('revenue') or
                  income_stmt.get('doanh_thu'))

        total_assets = (balance_sheet.get('total_assets') or
                       balance_sheet.get('tong_tai_san'))

        if revenue and total_assets and total_assets > 0:
            return revenue / total_assets

        return None
    except Exception:
        return None


def calculate_reserve_replacement_proxy(cash_flow: Dict, balance_sheet: Dict) -> Optional[float]:
    """Tính Reserve Replacement Proxy = CapEx / Depreciation"""
    try:
        capex = (cash_flow.get('capital_expenditure') or
                cash_flow.get('mua_tscd') or
                cash_flow.get('capex'))

        depreciation = (balance_sheet.get('accumulated_depreciation') or
                       balance_sheet.get('khau_hao_luy_ke'))

        # Nếu không có lũy kế, thử lấy từ cash flow
        if depreciation is None or depreciation == 0:
            depreciation = cash_flow.get('depreciation') or cash_flow.get('khau_hao')

        if capex and depreciation and depreciation > 0:
            return abs(capex) / depreciation

        return None
    except Exception:
        return None


def analyze_oil_price_sensitivity(income_stmt: Dict, ratios: Dict) -> Dict:
    """Phân tích độ nhạy với giá dầu thông qua biên lợi nhuận gộp"""
    result = {'volatility': None}

    try:
        # Lấy lịch sử biên lợi nhuận gộp
        gross_margin_history = ratios.get('gross_margin_history') or []

        if len(gross_margin_history) >= 3:
            # Tính độ lệch chuẩn
            std_dev = np.std(gross_margin_history)
            mean = np.mean(gross_margin_history)

            if mean > 0:
                result['volatility'] = std_dev / mean

        return result
    except Exception:
        return result


def calculate_oil_gas_health_score(metrics: Dict, ratings: Dict) -> Dict:
    """Tính O&G Health Score tổng hợp"""

    # ===== COMPONENT 1: CASH GENERATION (30%) =====
    cash_score = 0
    cash_factors = 0

    # EBITDA Margin (0-10 points)
    ebitda_margin = metrics.get('ebitda_margin')
    if ebitda_margin:
        cash_factors += 1
        if ebitda_margin > 0.30:
            cash_score += 10
        elif ebitda_margin > 0.20:
            cash_score += 7
        elif ebitda_margin > 0.10:
            cash_score += 4
        else:
            cash_score += 1

    # OCF/Net Income Ratio (0-10 points)
    ocf_ratio = metrics.get('ocf_net_income_ratio')
    if ocf_ratio:
        cash_factors += 1
        if ocf_ratio > 1.2:
            cash_score += 10
        elif ocf_ratio > 0.8:
            cash_score += 7
        elif ocf_ratio > 0.5:
            cash_score += 4
        else:
            cash_score += 1

    # OCF Trend (0-10 points)
    ocf_trend = metrics.get('ocf_trend')
    if ocf_trend:
        cash_factors += 1
        if ocf_trend == 'Tăng':
            cash_score += 10
        elif ocf_trend == 'Ổn định':
            cash_score += 6
        else:
            cash_score += 2

    # Normalize cash score to 30%
    if cash_factors > 0:
        cash_component = (cash_score / (cash_factors * 10)) * 30
    else:
        cash_component = 0

    # ===== COMPONENT 2: FINANCIAL STRENGTH (30%) =====
    strength_score = 0
    strength_factors = 0

    # Debt/EBITDA (0-15 points)
    debt_ebitda = metrics.get('debt_ebitda')
    if debt_ebitda:
        strength_factors += 1
        if debt_ebitda < 2:
            strength_score += 15
        elif debt_ebitda < 3:
            strength_score += 10
        elif debt_ebitda < 4:
            strength_score += 5
        else:
            strength_score += 1

    # Interest Coverage (0-15 points)
    interest_cov = metrics.get('interest_coverage')
    if interest_cov:
        strength_factors += 1
        if interest_cov > 5:
            strength_score += 15
        elif interest_cov > 2:
            strength_score += 10
        else:
            strength_score += 3

    # Normalize strength score to 30%
    if strength_factors > 0:
        strength_component = (strength_score / (strength_factors * 15)) * 30
    else:
        strength_component = 0

    # ===== COMPONENT 3: CAPITAL EFFICIENCY (20%) =====
    efficiency_score = 0
    efficiency_factors = 0

    # Asset Turnover (0-10 points)
    asset_turnover = metrics.get('asset_turnover')
    if asset_turnover:
        efficiency_factors += 1
        if asset_turnover > 0.8:
            efficiency_score += 10
        elif asset_turnover > 0.4:
            efficiency_score += 6
        else:
            efficiency_score += 3

    # ROCE (0-10 points) - nếu có
    roce = metrics.get('roce')
    if roce:
        efficiency_factors += 1
        if roce > 0.15:
            efficiency_score += 10
        elif roce > 0.08:
            efficiency_score += 6
        else:
            efficiency_score += 3

    # Normalize efficiency score to 20%
    if efficiency_factors > 0:
        efficiency_component = (efficiency_score / (efficiency_factors * 10)) * 20
    else:
        efficiency_component = 0

    # ===== COMPONENT 4: RESERVE QUALITY (20%) =====
    reserve_score = 0
    reserve_factors = 0

    # Reserve Replacement Proxy (0-10 points)
    reserve_proxy = metrics.get('reserve_replacement_proxy')
    if reserve_proxy:
        reserve_factors += 1
        if reserve_proxy > 1.3:
            reserve_score += 10
        elif reserve_proxy > 1.0:
            reserve_score += 7
        elif reserve_proxy > 0.8:
            reserve_score += 4
        else:
            reserve_score += 1

    # Capital Intensity (0-10 points) - Lower is better for non-E&P
    cap_intensity = metrics.get('capital_intensity')
    if cap_intensity:
        reserve_factors += 1
        # For E&P (high capex), this is normal
        if cap_intensity > 0.15:
            reserve_score += 10  # E&P company
        elif cap_intensity > 0.05:
            reserve_score += 7   # Services
        else:
            reserve_score += 5   # Low capex

    # Normalize reserve score to 20%
    if reserve_factors > 0:
        reserve_component = (reserve_score / (reserve_factors * 10)) * 20
    else:
        reserve_component = 0

    # ===== TOTAL SCORE =====
    total_score = cash_component + strength_component + efficiency_component + reserve_component

    # ===== RATING =====
    if total_score >= 80:
        rating = 'Rất tốt'
        color = '#10B981'  # Green
    elif total_score >= 60:
        rating = 'Tốt'
        color = '#3B82F6'  # Blue
    elif total_score >= 40:
        rating = 'Trung bình'
        color = '#F59E0B'  # Orange
    else:
        rating = 'Yếu'
        color = '#EF4444'  # Red

    return {
        'total': round(total_score, 1),
        'components': {
            'cash_generation': round(cash_component, 1),
            'financial_strength': round(strength_component, 1),
            'capital_efficiency': round(efficiency_component, 1),
            'reserve_quality': round(reserve_component, 1)
        },
        'rating': rating,
        'color': color
    }


def generate_oil_gas_recommendations(metrics: Dict, ratings: Dict, warnings: list) -> list:
    """Tạo khuyến nghị dựa trên phân tích"""
    recommendations = []

    # Khuyến nghị dựa trên Debt/EBITDA
    debt_ebitda = metrics.get('debt_ebitda')
    if debt_ebitda and debt_ebitda > 3:
        recommendations.append(
            f'Cần cơ cấu lại nợ: Debt/EBITDA {debt_ebitda:.1f}x cao hơn mức an toàn (2-3x). '
            'Nên cân nhắc tăng vốn chủ sở hữu hoặc bán tài sản không cốt lõi.'
        )

    # Khuyến nghị dựa trên EBITDA Margin
    ebitda_margin = metrics.get('ebitda_margin')
    if ebitda_margin and ebitda_margin < 0.20:
        recommendations.append(
            f'Cải thiện biên lợi nhuận: EBITDA Margin {ebitda_margin:.1%} thấp. '
            'Nên tối ưu hóa chi phí vận hành và tăng giá bán nếu có thể.'
        )

    # Khuyến nghị dựa trên OCF/Net Income
    ocf_ratio = metrics.get('ocf_net_income_ratio')
    if ocf_ratio and ocf_ratio < 0.8:
        recommendations.append(
            'Kiểm soát chất lượng lợi nhuận: OCF/Net Income thấp cho thấy nhiều khoản mục không tiền. '
            'Cần rà soát các khoản phải thu và tồn kho.'
        )

    # Khuyến nghị dựa trên Reserve Replacement
    reserve_proxy = metrics.get('reserve_replacement_proxy')
    if reserve_proxy and reserve_proxy < 0.8:
        recommendations.append(
            'Đầu tư vào trữ lượng: CapEx thấp hơn khấu hao, có nguy cơ suy giảm trữ lượng. '
            'Nên cân nhắc tăng đầu tư thăm dò và phát triển.'
        )

    # Khuyến nghị dựa trên Interest Coverage
    interest_cov = metrics.get('interest_coverage')
    if interest_cov and interest_cov < 2:
        recommendations.append(
            f'Nguy cơ thanh khoản: Hệ số covering lãi vay {interest_cov:.1f}x thấp. '
            'Cần ưu tiên trả nợ hoặc tái cơ cấu kỳ hạn nợ.'
        )

    # Khuyến nghị chung cho ngành dầu khí
    recommendations.append(
        'Theo dõi giá dầu: Biến động giá dầu ảnh hưởng lớn đến biên lợi nhuận. '
        'Nên xem xét công cụ phòng ngừa rủi ro (hedging).'
    )

    if len(recommendations) == 0:
        recommendations.append(
            'Sức khỏe tài chính tốt: Duy trì chiến lược hiện tại và theo dõi chặt chẽ các chỉ số. '
            'Tiếp tục tối ưu hóa chi phí và đầu tư có chọn lọc.'
        )

    return recommendations


# ==================== TESTING ====================

if __name__ == '__main__':
    # Test với dữ liệu mẫu
    sample_ratios = {
        'ebitda': 5000,
        'revenue': 15000,
        'ebit': 3500,
        'net_income': 2000,
        'interest_coverage': 4.5,
        'asset_turnover': 0.5
    }

    sample_balance_sheet = {
        'short_term_debt': 2000,
        'long_term_debt': 6000,
        'total_assets': 25000,
        'accumulated_depreciation': 1500
    }

    sample_income_stmt = {
        'revenue': 15000,
        'ebit': 3500,
        'depreciation': 1500,
        'interest_expense': 800,
        'net_income': 2000,
        'gross_profit': 6000
    }

    sample_cash_flow = {
        'operating_cash_flow': 2500,
        'capital_expenditure': 2000,
        'depreciation': 1500,
        'ocf_history': [2200, 2400, 2500]
    }

    result = analyze_oil_gas_company(
        sample_ratios,
        sample_balance_sheet,
        sample_income_stmt,
        sample_cash_flow
    )

    print("=== OIL & GAS ANALYSIS RESULTS ===")
    print(f"Industry: {result['industry']}")
    print(f"Date: {result['analysis_date']}")
    print(f"\n--- Health Score ---")
    print(f"Total: {result['health_score']['total']}/100 - {result['health_score']['rating']}")
    print(f"Components: {result['health_score']['components']}")
    print(f"\n--- Key Metrics ---")
    for key, value in result['metrics'].items():
        if not key.endswith('_label') and isinstance(value, (int, float)):
            print(f"{key}: {value}")
    print(f"\n--- Ratings ---")
    for key, value in result['ratings'].items():
        print(f"{key}: {value}")
    print(f"\n--- Strengths ---")
    for s in result['strengths']:
        print(f"✓ {s}")
    print(f"\n--- Warnings ---")
    for w in result['warnings']:
        print(f"⚠ {w}")
    print(f"\n--- Recommendations ---")
    for i, r in enumerate(result['recommendations'], 1):
        print(f"{i}. {r}")
