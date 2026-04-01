"""
Industry Router - Routes companies to appropriate industry analysis
Maps ICB industry codes/names to analysis modules
"""
from typing import Any, Dict, Optional, Tuple

# Industry classification mapping based on ICB (Industry Classification Benchmark)
# Maps ICB level 3 names to analysis type

INDUSTRY_MAPPING = {
    # Banking
    "banking": "banking",
    "ngân hàng": "banking",
    "banks": "banking",
    "dịch vụ tài chính": "banking",

    # Real Estate
    "bất động sản": "realestate",
    "real estate": "realestate",
    "realty": "realestate",
    "property": "realestate",
    "development": "realestate",

    # Manufacturing - Steel
    "thép": "manufacturing_steel",
    "steel": "manufacturing_steel",
    "sắt": "manufacturing_steel",

    # Manufacturing - Cement
    "xi măng": "manufacturing_cement",
    "cement": "manufacturing_cement",
    "vật liệu xây dựng": "manufacturing_cement",
    "construction materials": "manufacturing_cement",

    # Manufacturing - Chemicals
    "hóa chất": "manufacturing_chemicals",
    "chemicals": "manufacturing_chemicals",
    "phân bón": "manufacturing_chemicals",
    "fertilizers": "manufacturing_chemicals",
    "nhựa": "manufacturing_chemicals",
    "plastics": "manufacturing_chemicals",

    # Manufacturing - General
    "sản xuất": "manufacturing",
    "manufacturing": "manufacturing",
    "công nghiệp": "manufacturing",

    # Retail
    "bán lẻ": "retail",
    "retail": "retail",
    "thương mại": "retail",
    "trading": "retail",
    "wholesale": "retail",
    "distribution": "retail",

    # Technology
    "công nghệ": "technology",
    "technology": "technology",
    "software": "technology",
    "phần mềm": "technology",
    "it services": "technology",
    "dịch vụ cntt": "technology",
    "telecommunications": "technology",
    "viễn thông": "technology",

    # Oil & Gas
    "dầu khí": "oilgas",
    "oil & gas": "oilgas",
    "oil and gas": "oilgas",
    "exploration": "oilgas",
    "khai thác dầu": "oilgas",
    "dịch vụ dầu khí": "oilgas",

    # Aviation
    "hàng không": "aviation",
    "aviation": "aviation",
    "airlines": "aviation",
    "airline": "aviation",
    "hãng bay": "aviation",
    "transport": "aviation",
    "vận tải": "aviation",

    # Pharmaceutical
    "dược phẩm": "pharmaceutical",
    "pharmaceuticals": "pharmaceutical",
    "pharmaceutical": "pharmaceutical",
    "healthcare": "pharmaceutical",
    "y tế": "pharmaceutical",
    "medical": "pharmaceutical",
    "thuốc": "pharmaceutical",

    # Utilities - Power
    "điện": "utilities",
    "electricity": "utilities",
    "power": "utilities",
    "utilities": "utilities",
    "năng lượng": "utilities",
    "energy": "utilities",
    "nhiệt điện": "utilities",
    "thủy điện": "utilities",
    "điện gió": "utilities",
    "điện mặt trời": "utilities",

    # Insurance
    "bảo hiểm": "insurance",
    "insurance": "insurance",
    "life insurance": "insurance",
    "non-life insurance": "insurance",
}

# Known stock tickers with specific industry overrides
TICKER_INDUSTRY_OVERRIDE = {
    # Banks
    "VCB": "banking", "BID": "banking", "CTG": "banking", "TCB": "banking",
    "MBB": "banking", "ACB": "banking", "VPB": "banking", "HDB": "banking",
    "EIB": "banking", "STB": "banking", "LPB": "banking", "KHB": "banking",
    "NAB": "banking", "PGB": "banking", "OCB": "banking", "SHB": "banking",
    "VIB": "banking", "TPB": "banking", "BVB": "banking", "SSB": "banking",

    # Real Estate
    "VIC": "realestate", "VHM": "realestate", "NLG": "realestate", "KDH": "realestate",
    "DIG": "realestate", "PDR": "realestate", "NVL": "realestate", "HQC": "realestate",
    "LDG": "realestate", "IJC": "realestate", "TCH": "realestate", "DXG": "realestate",
    "CRG": "realestate", "CII": "realestate", "RCL": "realestate", "FCN": "realestate",

    # Steel
    "HPG": "manufacturing_steel", "HSG": "manufacturing_steel", "NKG": "manufacturing_steel",
    "TIS": "manufacturing_steel", "MIG": "manufacturing_steel", "HRC": "manufacturing_steel",
    "HPC": "manufacturing_steel", "TLH": "manufacturing_steel",

    # Cement/Construction Materials
    "VNM": "manufacturing_cement", "BTP": "manufacturing_cement", "BCC": "manufacturing_cement",
    "SC5": "manufacturing_cement", "FCM": "manufacturing_cement", "DCC": "manufacturing_cement",

    # Chemicals/Fertilizers
    "DCM": "manufacturing_chemicals", "DPM": "manufacturing_chemicals", "BMP": "manufacturing_chemicals",
    "PVC": "manufacturing_chemicals", "HT1": "manufacturing_chemicals", "LAS": "manufacturing_chemicals",
    "AGC": "manufacturing_chemicals", "HHM": "manufacturing_chemicals",

    # Retail
    "MWG": "retail", "FRT": "retail", "PNJ": "retail", "DGW": "retail",
    "PET": "retail", "MCH": "retail", "FCM": "retail", "ROS": "retail",
    "VRE": "retail", "ABT": "retail", "HNG": "retail", "TRA": "retail",

    # Technology
    "FPT": "technology", "CMG": "technology", "ELC": "technology", "LCG": "technology",
    "ITS": "technology", "FOX": "technology", "KST": "technology", "SEC": "technology",
    "STD": "technology", "CMT": "technology", "ONE": "technology",

    # Oil & Gas
    "GAS": "oilgas", "PVD": "oilgas", "PVS": "oilgas", "PVB": "oilgas",
    "PVT": "oilgas", "BVS": "oilgas", "PXR": "oilgas", "PVC": "oilgas",

    # Aviation
    "VJC": "aviation", "HVN": "aviation", "BAF": "aviation", "ASP": "aviation",
    "MJS": "aviation", "ALC": "aviation",

    # Pharmaceutical
    "DHG": "pharmaceutical", "IMP": "pharmaceutical", "TRA": "pharmaceutical",
    "DPG": "pharmaceutical", "VNR": "pharmaceutical", "BAX": "pharmaceutical",
    "BED": "pharmaceutical", "BBC": "pharmaceutical", "AVF": "pharmaceutical",
    "PMC": "pharmaceutical", "DPH": "pharmaceutical", "Har": "pharmaceutical",

    # Utilities/Power
    "POW": "utilities", "NT2": "utilities", "GEG": "utilities", "PGV": "utilities",
    "BTP": "utilities", "BII": "utilities", "BWM": "utilities", "SBT": "utilities",
    "PGD": "utilities", "NTL": "utilities", "TVD": "utilities", "NHN": "utilities",

    # Insurance
    "BVH": "insurance", "BMI": "insurance", "BIC": "insurance", "PVI": "insurance",
    "VNR": "insurance", "MIG": "insurance",
}


def detect_industry(icb_name: Optional[str], ticker: Optional[str] = None) -> str:
    """
    Detect industry type from ICB name or ticker.

    Args:
        icb_name: ICB industry classification name
        ticker: Stock ticker symbol (for override)

    Returns:
        Industry type string for analysis routing
    """
    # First check ticker override
    if ticker:
        ticker_upper = ticker.upper()
        if ticker_upper in TICKER_INDUSTRY_OVERRIDE:
            return TICKER_INDUSTRY_OVERRIDE[ticker_upper]

    # Then check ICB name mapping
    if icb_name:
        icb_lower = icb_name.lower().strip()

        # Direct match
        if icb_lower in INDUSTRY_MAPPING:
            return INDUSTRY_MAPPING[icb_lower]

        # Partial match (contains)
        for key, industry in INDUSTRY_MAPPING.items():
            if key in icb_lower or icb_lower in key:
                return industry

    # Default to core (general) analysis
    return "core"


def get_industry_display_name(industry_type: str) -> str:
    """Get Vietnamese display name for industry type."""
    display_names = {
        "banking": "Ngân hàng",
        "realestate": "Bất động sản",
        "manufacturing": "Sản xuất",
        "manufacturing_steel": "Thép",
        "manufacturing_cement": "Xi măng",
        "manufacturing_chemicals": "Hóa chất",
        "retail": "Bán lẻ",
        "technology": "Công nghệ",
        "oilgas": "Dầu khí",
        "aviation": "Hàng không",
        "pharmaceutical": "Dược phẩm",
        "utilities": "Điện力",
        "insurance": "Bảo hiểm",
        "core": "Tổng hợp",
    }
    return display_names.get(industry_type, "Tổng hợp")


def run_industry_analysis(
    industry_type: str,
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any],
    cash_flow: Optional[Dict[str, Any]] = None,
    previous_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run appropriate industry analysis based on detected type.

    Args:
        industry_type: Industry type from detect_industry()
        financial_ratios: Financial ratios dict
        balance_sheet: Balance sheet dict
        income_statement: Income statement dict
        cash_flow: Cash flow statement dict (optional)
        previous_data: Previous year data for comparison (optional)

    Returns:
        Analysis results dict with metrics, scores, and ratings
    """
    from . import (
        analyze_banking_sector,
        analyze_real_estate_company,
        analyze_manufacturing_company,
        analyze_retail,
        analyze_technology_company,
        analyze_oil_gas_company,
        analyze_aviation_company,
        analyze_pharmaceutical_company,
        analyze_utilities,
        analyze_insurance_industry,
        analyze_core_financials,
    )

    # Normalize industry type
    base_industry = industry_type.split("_")[0] if "_" in industry_type else industry_type
    sub_industry = industry_type.split("_")[1] if "_" in industry_type else None

    try:
        if base_industry == "banking":
            # Banking requires specialized metrics not yet available in DB
            # Fall back to core analysis with note
            core_result = analyze_core_financials(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )
            core_result['note'] = 'Phân tích ngành Ngân hàng chuyên biệt chưa sẵn có. Hiển thị phân tích tổng hợp.'
            core_result['specialized_analysis_available'] = False
            return core_result

        elif base_industry == "realestate":
            return analyze_real_estate_company(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )

        elif base_industry == "manufacturing":
            industry = sub_industry if sub_industry else "default"
            return analyze_manufacturing_company(
                financial_ratios, balance_sheet, income_statement, cash_flow,
                industry=industry
            )

        elif base_industry == "retail":
            return analyze_retail(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )

        elif base_industry == "technology":
            return analyze_technology_company(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )

        elif base_industry == "oilgas":
            return analyze_oil_gas_company(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )

        elif base_industry == "aviation":
            return analyze_aviation_company(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )

        elif base_industry == "pharmaceutical":
            # Pharmaceutical requires specialized metrics not yet available in DB
            # Fall back to core analysis with note
            core_result = analyze_core_financials(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )
            core_result['note'] = 'Phân tích ngành Dược phẩm chuyên biệt chưa sẵn có. Hiển thị phân tích tổng hợp.'
            core_result['specialized_analysis_available'] = False
            return core_result

        elif base_industry == "utilities":
            return analyze_utilities(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )

        elif base_industry == "insurance":
            # Insurance requires specialized metrics not yet available in DB
            # Fall back to core analysis with note
            core_result = analyze_core_financials(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )
            core_result['note'] = 'Phân tích ngành Bảo hiểm chuyên biệt chưa sẵn có. Hiển thị phân tích tổng hợp.'
            core_result['specialized_analysis_available'] = False
            return core_result

        else:
            # Default to core analysis
            return analyze_core_financials(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )

    except Exception as e:
        # Fallback to core analysis on error
        return {
            "error": str(e),
            "fallback": True,
            **analyze_core_financials(
                financial_ratios, balance_sheet, income_statement, cash_flow
            )
        }


def get_supported_industries() -> Dict[str, str]:
    """Get list of supported industries with display names."""
    return {
        "banking": "Ngân hàng",
        "realestate": "Bất động sản",
        "manufacturing_steel": "Thép",
        "manufacturing_cement": "Xi măng",
        "manufacturing_chemicals": "Hóa chất",
        "retail": "Bán lẻ",
        "technology": "Công nghệ",
        "oilgas": "Dầu khí",
        "aviation": "Hàng không",
        "pharmaceutical": "Dược phẩm",
        "utilities": "Điện力",
        "insurance": "Bảo hiểm",
        "core": "Tổng hợp (Mặc định)",
    }
