"""
Aviation Industry Analysis Module
Provides aviation-specific financial metrics and analysis for Vietnamese airlines
"""

def analyze_aviation_company(financial_ratios, balance_sheet, income_statement, cash_flow):
    """
    Analyze aviation company with industry-specific metrics

    Args:
        financial_ratios: Dict with calculated ratios (ROE, net_margin, etc.)
        balance_sheet: Dict with balance sheet data
        income_statement: Dict with income statement data
        cash_flow: Dict with cash flow data

    Returns:
        Dict with aviation metrics, ratings, and efficiency score
    """
    metrics = {}
    ratings = {}

    # Extract key financial data (DB sign conventions: revenue/costs can be negative)
    revenue = income_statement.get('net_revenue')
    if revenue is None:
        revenue = income_statement.get('revenue') or income_statement.get('total_revenue') or 0
    try:
        revenue = float(revenue)
        if revenue < 0:
            revenue = abs(revenue)
    except (TypeError, ValueError):
        revenue = 0

    operating_income = income_statement.get('operating_income') or income_statement.get('operating_profit') or 0
    net_income = income_statement.get('net_income') or income_statement.get('net_profit') or income_statement.get('net_profit_parent_company') or 0
    cogs = income_statement.get('cogs') or income_statement.get('cost_of_goods_sold') or income_statement.get('cost_of_revenue') or 0
    try:
        cogs = abs(float(cogs))
    except (TypeError, ValueError):
        cogs = 0
    selling_expense = income_statement.get('selling_expense') or income_statement.get('sales_and_marketing_expenses') or 0
    admin_expense = income_statement.get('general_and_administrative_expenses') or income_statement.get('admin_expenses') or 0
    interest_expense = income_statement.get('interest_expense') or income_statement.get('interest_expense_net') or 0

    fixed_assets = balance_sheet.get('fixed_assets') or balance_sheet.get('property_plant_equipment') or balance_sheet.get('ppe') or 0
    total_assets = balance_sheet.get('total_assets') or 0
    total_debt = balance_sheet.get('total_debt') or balance_sheet.get('total_liabilities') or balance_sheet.get('liabilities_total') or 0
    # Liquidity inputs: do not default missing to 0 (0 is a meaningful value)
    def _to_float(val):
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    current_assets = None
    for key in ('current_assets', 'asset_current', 'assets_current'):
        if balance_sheet.get(key) is not None:
            current_assets = _to_float(balance_sheet.get(key))
            break

    current_liabilities = None
    for key in ('current_liabilities', 'liabilities_current'):
        if balance_sheet.get(key) is not None:
            current_liabilities = _to_float(balance_sheet.get(key))
            break
    equity = balance_sheet.get('equity') or balance_sheet.get('total_equity') or balance_sheet.get('equity_total') or 0

    # EBITDA = Operating Profit + Depreciation + Amortization
    # Priority: 1) Use ebitda from financial_ratios (already calculated), 2) Calculate from income_statement + cash_flow
    ebitda = financial_ratios.get('ebitda_billions') * 1_000_000_000 if financial_ratios.get('ebitda_billions') else None
    if ebitda is None or ebitda == 0:
        # Fallback: Calculate from operating_profit + depreciation_fixed_assets
        da = cash_flow.get('depreciation_fixed_assets') or 0
        ebitda = (operating_income or 0) + da

    # Get ratio values if available
    roe = financial_ratios.get('roe') or financial_ratios.get('return_on_equity') or 0
    net_margin = financial_ratios.get('net_profit_margin') or financial_ratios.get('net_margin') or 0

    # ========== AVIATION-SPECIFIC METRICS ==========

    # 1. OPERATING MARGIN
    # Formula: Operating Income / Revenue
    # Aviation is low-margin business
    if revenue and revenue > 0:
        operating_margin = (operating_income / revenue) * 100
        metrics['operating_margin'] = round(operating_margin, 2)

        # Rating: > 10% = Excellent, 5-10% = Good, 0-5% = Marginal, < 0 = Loss
        if operating_margin > 10:
            ratings['operating_margin'] = 'Xuất_sắc'
        elif operating_margin > 5:
            ratings['operating_margin'] = 'Tốt'
        elif operating_margin > 0:
            ratings['operating_margin'] = 'Khá'
        else:
            ratings['operating_margin'] = 'Thua_lỗ'
    else:
        metrics['operating_margin'] = None
        ratings['operating_margin'] = None

    # 2. LOAD FACTOR PROXY
    # Use: Revenue / Fixed Assets as proxy for capacity utilization
    if fixed_assets and fixed_assets > 0:
        load_factor_proxy = (revenue / fixed_assets) * 100
        metrics['load_factor_proxy'] = round(load_factor_proxy, 2)

        # Rating based on asset efficiency
        if load_factor_proxy > 50:
            ratings['load_factor'] = 'Tối_ưu'
        elif load_factor_proxy > 30:
            ratings['load_factor'] = 'Tốt'
        elif load_factor_proxy > 15:
            ratings['load_factor'] = 'Trung_bình'
        else:
            ratings['load_factor'] = 'Thấp'
    else:
        metrics['load_factor_proxy'] = None
        ratings['load_factor'] = None

    # 3. FUEL COST SENSITIVITY
    # Proxy: COGS / Revenue (fuel is major component, typically 25-35% of operating costs)
    if revenue and revenue > 0:
        fuel_sensitivity = (cogs / revenue) * 100
        metrics['fuel_cost_ratio'] = round(fuel_sensitivity, 2)

        # Rating: Lower is better (less sensitive to oil prices)
        if fuel_sensitivity < 50:
            ratings['fuel_sensitivity'] = 'Thấp'
        elif fuel_sensitivity < 70:
            ratings['fuel_sensitivity'] = 'Trung_bình'
        else:
            ratings['fuel_sensitivity'] = 'Cao'
    else:
        metrics['fuel_cost_ratio'] = None
        ratings['fuel_sensitivity'] = None

    # 4. AIRCRAFT UTILIZATION PROXY
    # Revenue / Fixed Assets - higher indicates better utilization
    if fixed_assets and fixed_assets > 0:
        utilization_proxy = revenue / fixed_assets
        metrics['aircraft_utilization'] = round(utilization_proxy, 2)

        # Rating
        if utilization_proxy > 0.5:
            ratings['utilization'] = 'Rất_tốt'
        elif utilization_proxy > 0.3:
            ratings['utilization'] = 'Tốt'
        elif utilization_proxy > 0.1:
            ratings['utilization'] = 'Trung_bình'
        else:
            ratings['utilization'] = 'Thấp'
    else:
        metrics['aircraft_utilization'] = None
        ratings['utilization'] = None

    # 5. DEBT/EBITDA
    # Airlines are capital intensive
    if ebitda and ebitda > 0:
        debt_ebitda = total_debt / ebitda
        metrics['debt_ebitda'] = round(debt_ebitda, 2)

        # Rating: < 3 = Good, 3-5 = Normal, > 5 = High risk
        if debt_ebitda < 3:
            ratings['debt_ebitda'] = 'Tốt'
        elif debt_ebitda < 5:
            ratings['debt_ebitda'] = 'Chấp_nhận_được'
        else:
            ratings['debt_ebitda'] = 'Rủi_ro_cao'
    else:
        metrics['debt_ebitda'] = None
        ratings['debt_ebitda'] = None

    # 6. INTEREST COVERAGE
    # Formula: EBIT / Interest Expense
    if interest_expense and interest_expense > 0 and operating_income:
        interest_coverage = operating_income / interest_expense
        metrics['interest_coverage'] = round(interest_coverage, 2)

        # Rating: > 2 = Adequate, < 2 = Risk
        if interest_coverage > 3:
            ratings['interest_coverage'] = 'An_toàn'
        elif interest_coverage > 2:
            ratings['interest_coverage'] = 'Chấp_nhận_được'
        elif interest_coverage > 1:
            ratings['interest_coverage'] = 'Rủi_ro'
        else:
            ratings['interest_coverage'] = 'Nguy_cơ'
    else:
        metrics['interest_coverage'] = None
        ratings['interest_coverage'] = None

    # 7. WORKING CAPITAL
    # Advance ticket sales = liability, can be negative and still healthy
    working_capital = None
    if current_assets is not None and current_liabilities is not None and current_liabilities > 0:
        current_ratio = current_assets / current_liabilities

        # If liquidity is an extreme outlier, try to derive current liabilities from totals.
        if current_ratio > 20:
            liab_total = _to_float(balance_sheet.get('liabilities_total') or balance_sheet.get('total_liabilities'))
            liab_non_current = _to_float(balance_sheet.get('liabilities_non_current') or balance_sheet.get('non_current_liabilities') or balance_sheet.get('long_term_liabilities'))
            if liab_total is not None and liab_non_current is not None and liab_total > liab_non_current:
                derived_cl = liab_total - liab_non_current
                if derived_cl > 0:
                    derived_ratio = current_assets / derived_cl
                    if derived_ratio <= 20 or derived_ratio < current_ratio:
                        current_liabilities = derived_cl
                        current_ratio = derived_ratio
                        metrics['working_capital_note'] = 'Nợ ngắn hạn được suy ra từ tổng nợ - nợ dài hạn (liabilities_current outlier).'

        if current_ratio < 0:
            metrics['working_capital_note'] = 'Dữ liệu thanh khoản không hợp lệ (current ratio < 0).'
        else:
            # Keep the value even if current_ratio remains very high after derivation, but warn.
            if current_ratio > 20:
                metrics['working_capital_note'] = metrics.get('working_capital_note') or 'Lưu ý: current ratio rất cao; diễn giải thận trọng.'
            working_capital = current_assets - current_liabilities

    metrics['working_capital'] = round(working_capital, 0) if working_capital is not None else None
    ratings['working_capital'] = (
        'Dương' if (working_capital is not None and working_capital > 0)
        else ('Âm' if working_capital is not None else None)
    )

    # 8. REVENUE PER EMPLOYEE PROXY
    # Revenue / (Selling + Admin Expenses) × factor - efficiency indicator
    operating_expenses = selling_expense + admin_expense
    if operating_expenses and operating_expenses > 0:
        revenue_per_employee_proxy = revenue / operating_expenses
        metrics['revenue_employee_proxy'] = round(revenue_per_employee_proxy, 2)

        # Rating
        if revenue_per_employee_proxy > 5:
            ratings['employee_efficiency'] = 'Rất_hiệu_quả'
        elif revenue_per_employee_proxy > 3:
            ratings['employee_efficiency'] = 'Hiệu_quả'
        elif revenue_per_employee_proxy > 1.5:
            ratings['employee_efficiency'] = 'Trung_bình'
        else:
            ratings['employee_efficiency'] = 'Thấp'
    else:
        metrics['revenue_employee_proxy'] = None
        ratings['employee_efficiency'] = None

    # 9. FIXED ASSET TURNOVER
    if fixed_assets and fixed_assets > 0:
        fixed_asset_turnover = revenue / fixed_assets
        metrics['fixed_asset_turnover'] = round(fixed_asset_turnover, 2)

        # Rating
        if fixed_asset_turnover > 0.5:
            ratings['fixed_asset_turnover'] = 'Tốt'
        elif fixed_asset_turnover > 0.3:
            ratings['fixed_asset_turnover'] = 'Trung_bình'
        else:
            ratings['fixed_asset_turnover'] = 'Thấp'
    else:
        metrics['fixed_asset_turnover'] = None
        ratings['fixed_asset_turnover'] = None

    # 10. NET MARGIN (from ratios if available)
    if net_margin:
        metrics['net_margin'] = round(net_margin * 100, 2) if net_margin < 1 else round(net_margin, 2)
    elif revenue and revenue > 0:
        net_margin_calc = (net_income / revenue) * 100
        metrics['net_margin'] = round(net_margin_calc, 2)
    else:
        metrics['net_margin'] = None

    # 11. ROE (from ratios if available)
    if roe:
        metrics['roe'] = round(roe * 100, 2) if roe < 1 else round(roe, 2)
    elif equity and equity > 0:
        roe_calc = (net_income / equity) * 100
        metrics['roe'] = round(roe_calc, 2)
    else:
        metrics['roe'] = None

    # 12. CASK PROXY (Cost per Available Seat Kilometer)
    # Use: Operating Expenses / Revenue as proxy
    operating_costs = cogs + selling_expense + admin_expense
    if revenue and revenue > 0:
        cask_proxy = (operating_costs / revenue) * 100
        metrics['cask_proxy'] = round(cask_proxy, 2)

        # Rating: Lower is better
        if cask_proxy < 80:
            ratings['cask'] = 'Tốt'
        elif cask_proxy < 95:
            ratings['cask'] = 'Trung_bình'
        else:
            ratings['cask'] = 'Cao'
    else:
        metrics['cask_proxy'] = None
        ratings['cask'] = None

    # ========== AVIATION EFFICIENCY SCORE ==========
    # Calculate weighted efficiency score

    scores = {}
    weights = {
        'profitability': 0.30,
        'cost_management': 0.25,
        'financial_health': 0.25,
        'asset_efficiency': 0.20
    }

    # Profitability Score (30%): Operating Margin, Net Margin, ROE
    profitability_score = 0
    profitability_count = 0

    if metrics.get('operating_margin') is not None:
        op_margin = metrics['operating_margin']
        if op_margin > 10:
            profitability_score += 100
        elif op_margin > 5:
            profitability_score += 75
        elif op_margin > 0:
            profitability_score += 50
        else:
            profitability_score += 25
        profitability_count += 1

    if metrics.get('net_margin') is not None:
        net_margin_val = metrics['net_margin']
        if net_margin_val > 8:
            profitability_score += 100
        elif net_margin_val > 4:
            profitability_score += 75
        elif net_margin_val > 0:
            profitability_score += 50
        else:
            profitability_score += 25
        profitability_count += 1

    if metrics.get('roe') is not None:
        roe_val = metrics['roe']
        if roe_val > 15:
            profitability_score += 100
        elif roe_val > 8:
            profitability_score += 75
        elif roe_val > 0:
            profitability_score += 50
        else:
            profitability_score += 25
        profitability_count += 1

    scores['profitability'] = profitability_score / profitability_count if profitability_count > 0 else 0

    # Cost Management Score (25%): Fuel sensitivity, CASK proxy
    cost_score = 0
    cost_count = 0

    if metrics.get('fuel_cost_ratio') is not None:
        fuel_ratio = metrics['fuel_cost_ratio']
        # Lower is better
        if fuel_ratio < 50:
            cost_score += 100
        elif fuel_ratio < 70:
            cost_score += 70
        else:
            cost_score += 40
        cost_count += 1

    if metrics.get('cask_proxy') is not None:
        cask = metrics['cask_proxy']
        # Lower is better
        if cask < 80:
            cost_score += 100
        elif cask < 95:
            cost_score += 70
        else:
            cost_score += 40
        cost_count += 1

    scores['cost_management'] = cost_score / cost_count if cost_count > 0 else 0

    # Financial Health Score (25%): Debt/EBITDA, Interest Coverage
    health_score = 0
    health_count = 0

    if metrics.get('debt_ebitda') is not None:
        debt_ebitda_val = metrics['debt_ebitda']
        # Lower is better
        if debt_ebitda_val < 3:
            health_score += 100
        elif debt_ebitda_val < 5:
            health_score += 70
        else:
            health_score += 40
        health_count += 1

    if metrics.get('interest_coverage') is not None:
        coverage = metrics['interest_coverage']
        # Higher is better
        if coverage > 3:
            health_score += 100
        elif coverage > 2:
            health_score += 70
        elif coverage > 1:
            health_score += 40
        else:
            health_score += 20
        health_count += 1

    scores['financial_health'] = health_score / health_count if health_count > 0 else 0

    # Asset Efficiency Score (20%): Fixed Asset Turnover, Utilization proxy
    asset_score = 0
    asset_count = 0

    if metrics.get('fixed_asset_turnover') is not None:
        turnover = metrics['fixed_asset_turnover']
        if turnover > 0.5:
            asset_score += 100
        elif turnover > 0.3:
            asset_score += 70
        else:
            asset_score += 40
        asset_count += 1

    if metrics.get('aircraft_utilization') is not None:
        utilization = metrics['aircraft_utilization']
        if utilization > 0.5:
            asset_score += 100
        elif utilization > 0.3:
            asset_score += 70
        else:
            asset_score += 40
        asset_count += 1

    scores['asset_efficiency'] = asset_score / asset_count if asset_count > 0 else 0

    # Calculate overall efficiency score
    overall_score = (
        scores['profitability'] * weights['profitability'] +
        scores['cost_management'] * weights['cost_management'] +
        scores['financial_health'] * weights['financial_health'] +
        scores['asset_efficiency'] * weights['asset_efficiency']
    )

    metrics['aviation_efficiency_score'] = round(overall_score, 1)

    # Overall rating
    if overall_score >= 80:
        metrics['aviation_rating'] = 'Xuất_sắc'
    elif overall_score >= 65:
        metrics['aviation_rating'] = 'Tốt'
    elif overall_score >= 50:
        metrics['aviation_rating'] = 'Trung_bình'
    elif overall_score >= 35:
        metrics['aviation_rating'] = 'Yếu'
    else:
        metrics['aviation_rating'] = 'Kém'

    # Component scores for display
    metrics['profitability_score'] = round(scores['profitability'], 1)
    metrics['cost_management_score'] = round(scores['cost_management'], 1)
    metrics['financial_health_score'] = round(scores['financial_health'], 1)
    metrics['asset_efficiency_score'] = round(scores['asset_efficiency'], 1)

    return {
        'metrics': metrics,
        'ratings': ratings
    }


def get_aviation_metric_labels():
    """
    Returns Vietnamese labels for aviation metrics
    """
    return {
        'operating_margin': 'Biên_lợi_nhuận_hoạt_động',
        'load_factor_proxy': 'Tỷ_lệ_lấp đầy_ước_tính',
        'fuel_cost_ratio': 'Tỷ_lệ_chi_phí_nhiên_liệu',
        'aircraft_utilization': 'Hiệu_suất_sử_dụng_tàu_bay',
        'debt_ebitda': 'Nợ trên EBITDA',
        'interest_coverage': 'Hệ_số_trả_lãi',
        'working_capital': 'Vốn_làm_việc',
        'revenue_employee_proxy': 'Doanh_thu_trên_nhân_sự_ước_tính',
        'fixed_asset_turnover': 'Vòng_quả_tài_sản_cố_định',
        'net_margin': 'Biên_lợi_nhuận_ròng',
        'roe': 'ROE',
        'cask_proxy': 'Chi_phí_trên_ghế_ước_tính',
        'aviation_efficiency_score': 'Điểm_hiệu_quả_hàng_không',
        'aviation_rating': 'Xếp_hạng_hàng_không',
        'profitability_score': 'Điểm_lợi_nhuận',
        'cost_management_score': 'Điểm_quản_lý_chi_phí',
        'financial_health_score': 'Điểm_sức_khỏe_tài_chính',
        'asset_efficiency_score': 'Điểm_hiệu_quả_tài_sản'
    }


def get_aviation_rating_labels():
    """
    Returns Vietnamese labels for aviation ratings
    """
    return {
        'operating_margin': 'Đánh_giá_biên_lợi_nhuận',
        'load_factor': 'Đánh_giá_tỷ_lệ_lấp đầy',
        'fuel_sensitivity': 'Đánh_giá_nhạy_cả_giá_xăng',
        'utilization': 'Đánh_giá_hiệu_suất_tàu_bay',
        'debt_ebitda': 'Đánh_giá_nợ',
        'interest_coverage': 'Đánh_giá_khả_năng_trả_lãi',
        'working_capital': 'Đánh_giá_vốn_làm_việc',
        'employee_efficiency': 'Đánh_giá_hiệu_quả_nhân_sự',
        'fixed_asset_turnover': 'Đánh_giá_vòng_quả_tài_sản',
        'cask': 'Đánh_giá_chi_phí_exploit'
    }
