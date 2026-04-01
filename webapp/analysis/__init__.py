"""
Analysis Module - Module phân tích tài chính

Cung cấp các công cụ phân tích tài chính chuyên sâu cho thị trường Việt Nam.

Modules:
    - core_analysis: Phân tích cốt lõi áp dụng cho mọi ngành
    - risk_analysis: Phân tích rủi ro (volatility, beta, VaR, Sharpe)
    - banking_analysis: Phân tích ngành ngân hàng
    - realestate_analysis: Phân tích ngành bất động sản
    - manufacturing_analysis: Phân tích ngành sản xuất (thép, xi măng, hóa chất)
    - retail_analysis: Phân tích ngành bán lẻ
    - technology_analysis: Phân tích ngành công nghệ
    - oilgas_analysis: Phân tích ngành dầu khí
    - aviation_analysis: Phân tích ngành hàng không
    - pharmaceutical_analysis: Phân tích ngành dược phẩm
    - utilities_analysis: Phân tích ngành điện
    - insurance_analysis: Phân tích ngành bảo hiểm
    - industry_router: Tự động nhận diện ngành và điều hướng phân tích

Main exports:
    - CoreAnalysisEngine: Class phân tích tài chính cốt lõi
    - analyze_core_financials: Hàm tiện ích phân tích nhanh
    - RiskAnalysisEngine: Class phân tích rủi ro
    - analyze_stock_risk: Hàm tiện ích phân tích rủi ro
    - detect_industry: Tự động nhận diện ngành từ ICB code
    - run_industry_analysis: Chạy phân tích theo ngành phù hợp

Usage:
    from webapp.analysis import detect_industry, run_industry_analysis

    # Tự động nhận diện ngành
    industry = detect_industry(icb_name="Ngân hàng", ticker="VCB")

    # Chạy phân tích theo ngành
    result = run_industry_analysis(
        industry_type=industry,
        financial_ratios=ratios,
        balance_sheet=bs,
        income_statement=is,
        cash_flow=cf
    )
"""

# Core analysis (áp dụng cho mọi ngành)
from .core_analysis import (
    CoreAnalysisEngine,
    analyze_core_financials
)

# Risk analysis
from .risk_analysis import (
    RiskAnalysisEngine,
    analyze_stock_risk
)

# Industry router
from .industry_router import (
    detect_industry,
    get_industry_display_name,
    run_industry_analysis,
    get_supported_industries,
    INDUSTRY_MAPPING,
    TICKER_INDUSTRY_OVERRIDE,
)

# Industry-specific analysis
from .banking_analysis import (
    analyze_banking_sector,
    calculate_nim,
    calculate_npl_ratio,
    calculate_llr,
    calculate_car,
    calculate_cost_to_income,
    calculate_ldr,
    calculate_credit_growth,
    calculate_deposit_growth,
    calculate_bank_health_score,
    calculate_single_banking_metric,
)

from .realestate_analysis import (
    analyze_real_estate_company,
    calculate_inventory_to_assets,
    calculate_project_inventory_quality,
    calculate_debt_to_equity_re,
    calculate_cash_to_st_debt,
    calculate_interest_coverage,
    calculate_gross_margin,
    analyze_revenue_recognition_pattern,
    calculate_working_capital,
    calculate_re_health_score,
    REMetric
)

from .manufacturing_analysis import (
    analyze_manufacturing_company,
)

from .retail_analysis import (
    analyze_retail,
)

from .technology_analysis import (
    analyze_technology_company,
)

from .oilgas_analysis import (
    analyze_oil_gas_company,
)

from .aviation_analysis import (
    analyze_aviation_company,
    get_aviation_metric_labels,
    get_aviation_rating_labels,
)

from .pharmaceutical_analysis import (
    analyze_pharmaceutical_company,
)

from .utilities_analysis import (
    analyze_utilities,
)

from .insurance_analysis import (
    analyze_insurance_industry,
)


__all__ = [
    # Core analysis
    'CoreAnalysisEngine',
    'analyze_core_financials',

    # Industry router
    'detect_industry',
    'get_industry_display_name',
    'run_industry_analysis',
    'get_supported_industries',
    'INDUSTRY_MAPPING',
    'TICKER_INDUSTRY_OVERRIDE',

    # Banking analysis
    'analyze_banking_sector',
    'calculate_nim',
    'calculate_npl_ratio',
    'calculate_llr',
    'calculate_car',
    'calculate_cost_to_income',
    'calculate_ldr',
    'calculate_credit_growth',
    'calculate_deposit_growth',
    'calculate_bank_health_score',
    'calculate_single_banking_metric',

    # Real estate analysis
    'analyze_real_estate_company',
    'calculate_inventory_to_assets',
    'calculate_project_inventory_quality',
    'calculate_debt_to_equity_re',
    'calculate_cash_to_st_debt',
    'calculate_interest_coverage',
    'calculate_gross_margin',
    'analyze_revenue_recognition_pattern',
    'calculate_working_capital',
    'calculate_re_health_score',
    'REMetric',

    # Manufacturing analysis
    'analyze_manufacturing_company',

    # Retail analysis
    'analyze_retail',

    # Technology analysis
    'analyze_technology_company',

    # Oil & Gas analysis
    'analyze_oil_gas_company',

    # Aviation analysis
    'analyze_aviation_company',
    'get_aviation_metric_labels',
    'get_aviation_rating_labels',

    # Pharmaceutical analysis
    'analyze_pharmaceutical_company',

    # Utilities analysis
    'analyze_utilities',

    # Insurance analysis
    'analyze_insurance_industry',
]

__version__ = '2.0.0'
__author__ = 'Financial Analysis Engine'
