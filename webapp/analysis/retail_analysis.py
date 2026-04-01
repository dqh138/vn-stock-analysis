"""
Retail Industry Analysis Module for Vietnamese Financial Analysis Webapp

This module provides retail-specific financial metrics and analysis including:
- Gross Margin analysis by segment
- Inventory Turnover efficiency
- Days Sales of Inventory
- Working Capital efficiency
- SG&A cost control
- Same-store growth proxies
- Net Margin analysis
- Cash Conversion Cycle
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def safe_divide(numerator: Optional[float], denominator: Optional[float], default: float = None) -> Optional[float]:
    """
    Safely divide two numbers, handling None and zero denominator.

    Args:
        numerator: Numerator value (can be None)
        denominator: Denominator value (can be None or zero)
        default: Default value to return if division is not possible

    Returns:
        Result of division or default value
    """
    if numerator is None or denominator is None:
        return default
    if denominator == 0:
        return default
    return numerator / denominator


def get_value(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely get a value from nested dictionary using multiple possible keys.

    Args:
        data: Dictionary to search
        *keys: Possible keys to try (in order)
        default: Default value if none found

    Returns:
        Value from dictionary or default
    """
    if not data:
        return default
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def calculate_inventory_metrics(balance_sheet: Dict[str, Any], income_statement: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate inventory-related metrics for retail analysis.

    Args:
        balance_sheet: Balance sheet data dict
        income_statement: Income statement data dict

    Returns:
        Dictionary with inventory metrics
    """
    # Extract values
    inventory_current = get_value(balance_sheet, "inventory", "inventories", default=0)
    inventory_previous = get_value(balance_sheet, "inventory_previous", "inventories_previous", default=inventory_current)
    cogs = get_value(income_statement, "cost_of_goods_sold", "cogs", "cost_of_revenue", default=0)
    # DB often stores COGS as negative expense
    try:
        cogs = abs(float(cogs))
    except (TypeError, ValueError):
        cogs = 0

    # Calculate average inventory - check for None, not truthy (0 is valid)
    if inventory_current is not None and inventory_previous is not None:
        average_inventory = (inventory_current + inventory_previous) / 2
    else:
        average_inventory = inventory_current

    # Calculate Inventory Turnover: COGS / Average Inventory
    inventory_turnover = safe_divide(cogs, average_inventory, default=None)

    # Calculate Days Sales of Inventory: 365 / Inventory Turnover
    days_sales_inventory = None
    if inventory_turnover and inventory_turnover > 0:
        days_sales_inventory = 365 / inventory_turnover

    return {
        "inventory_current": inventory_current,
        "inventory_previous": inventory_previous,
        "average_inventory": average_inventory,
        "inventory_turnover": inventory_turnover,
        "days_sales_inventory": days_sales_inventory,
    }


def rate_inventory_turnover(turnover: Optional[float]) -> Dict[str, Any]:
    """
    Rate inventory turnover performance.

    Rating thresholds:
    - Excellent: > 8 (turns over 8+ times per year)
    - Good: 5-8
    - Average: 3-5
    - Slow: < 3

    Args:
        turnover: Inventory turnover ratio

    Returns:
        Dictionary with rating and label
    """
    if turnover is None:
        return {"rating": "N/A", "label_vi": "Không có dữ liệu", "label_en": "No Data", "score": 0}

    if turnover > 8:
        return {
            "rating": "Xuất sắc",
            "label_vi": "Xuất sắc",
            "label_en": "Excellent",
            "score": 5,
            "benchmark": " > 8 lần/năm",
        }
    elif turnover >= 5:
        return {
            "rating": "Tốt",
            "label_vi": "Tốt",
            "label_en": "Good",
            "score": 4,
            "benchmark": "5-8 lần/năm",
        }
    elif turnover >= 3:
        return {
            "rating": "Trung bình",
            "label_vi": "Trung bình",
            "label_en": "Average",
            "score": 3,
            "benchmark": "3-5 lần/năm",
        }
    else:
        return {
            "rating": "Chậm",
            "label_vi": "Chậm",
            "label_en": "Slow",
            "score": 1,
            "benchmark": "< 3 lần/năm",
        }


def rate_days_sales_inventory(dsi: Optional[float]) -> Dict[str, Any]:
    """
    Rate Days Sales of Inventory performance.

    Rating thresholds (lower is better):
    - Excellent: < 45 days
    - Good: 45-75 days
    - Risk: > 75 days (risk of obsolescence)

    Args:
        dsi: Days Sales of Inventory

    Returns:
        Dictionary with rating and label
    """
    if dsi is None:
        return {"rating": "N/A", "label_vi": "Không có dữ liệu", "label_en": "No Data", "score": 0}

    if dsi < 45:
        return {
            "rating": "Xuất sắc",
            "label_vi": "Xuất sắc",
            "label_en": "Excellent",
            "score": 5,
            "benchmark": "< 45 ngày",
            "note": "Vòng quay tồn kho nhanh",
        }
    elif dsi <= 75:
        return {
            "rating": "Tốt",
            "label_vi": "Tốt",
            "label_en": "Good",
            "score": 4,
            "benchmark": "45-75 ngày",
            "note": "Vòng kho tồn kho acceptable",
        }
    else:
        return {
            "rating": "Rủi ro",
            "label_vi": "Rủi ro",
            "label_en": "Risk",
            "score": 2,
            "benchmark": "> 75 ngày",
            "note": "Rủi ro hàng tồn kho lỗi thời",
        }


def calculate_margins(income_statement: Dict[str, Any], financial_ratios: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate retail-specific margin metrics.

    Args:
        income_statement: Income statement data dict
        financial_ratios: Financial ratios data dict

    Returns:
        Dictionary with margin metrics
    """
    # Extract values
    # Prefer net_revenue (revenue can be negative credits in DB for non-banks)
    revenue = get_value(income_statement, "net_revenue", "revenue", "total_revenue", default=0)
    try:
        revenue = float(revenue)
        if revenue < 0:
            revenue = abs(revenue)
    except (TypeError, ValueError):
        revenue = 0
    cogs = get_value(income_statement, "cost_of_goods_sold", "cogs", "cost_of_revenue", default=0)
    try:
        cogs = abs(float(cogs))
    except (TypeError, ValueError):
        cogs = 0
    net_income = get_value(income_statement, "net_income", "net_profit", "profit_after_tax", default=0)

    # Calculate Gross Margin: (Revenue - COGS) / Revenue
    gross_margin = safe_divide((revenue - cogs), revenue, default=None)
    gross_margin_pct = gross_margin * 100 if gross_margin is not None else None

    # Calculate Net Margin: Net Income / Revenue
    net_margin = safe_divide(net_income, revenue, default=None)
    net_margin_pct = net_margin * 100 if net_margin is not None else None

    # Get operating margin from ratios if available
    operating_margin = get_value(financial_ratios, "operating_margin", "ebit_margin", default=None)
    operating_margin_pct = operating_margin * 100 if operating_margin is not None else None

    return {
        "gross_margin": gross_margin,
        "gross_margin_pct": gross_margin_pct,
        "net_margin": net_margin,
        "net_margin_pct": net_margin_pct,
        "operating_margin": operating_margin,
        "operating_margin_pct": operating_margin_pct,
    }


def rate_gross_margin(margin_pct: Optional[float], segment: str = "general") -> Dict[str, Any]:
    """
    Rate gross margin against retail segment benchmarks.

    Segment benchmarks (Vietnam market):
    - Electronics: 10-20%
    - Fashion: 30-50%
    - Grocery: 5-15%
    - Jewelry: 20-40%
    - General: 15-25%

    Args:
        margin_pct: Gross margin percentage
        segment: Retail segment type

    Returns:
        Dictionary with rating and benchmark comparison
    """
    if margin_pct is None:
        return {"rating": "N/A", "label_vi": "Không có dữ liệu", "label_en": "No Data", "score": 0}

    # Define segment benchmarks
    benchmarks = {
        "electronics": (10, 20, "Điện tử"),
        "fashion": (30, 50, "Thời trang"),
        "grocery": (5, 15, "Thực phẩm"),
        "jewelry": (20, 40, "Trang sức"),
        "general": (15, 25, "Bán lẻ tổng hợp"),
    }

    segment_lower = segment.lower()
    if segment_lower not in benchmarks:
        segment_lower = "general"

    min_benchmark, max_benchmark, segment_name_vi = benchmarks[segment_lower]

    if margin_pct > max_benchmark:
        return {
            "rating": "Xuất sắc",
            "label_vi": f"Vượt trung bình {segment_name_vi}",
            "label_en": f"Above {segment_lower.capitalize()} avg",
            "score": 5,
            "benchmark": f"{min_benchmark}-{max_benchmark}%",
            "comparison": f"+{margin_pct - max_benchmark:.1f} ppt",
        }
    elif margin_pct >= min_benchmark:
        return {
            "rating": "Tốt",
            "label_vi": f"Đạt chuẩn {segment_name_vi}",
            "label_en": f"Meets {segment_lower.capitalize()} benchmark",
            "score": 4,
            "benchmark": f"{min_benchmark}-{max_benchmark}%",
            "comparison": "Trong khoảng",
        }
    else:
        return {
            "rating": "Thấp",
            "label_vi": f"Dưới trung bình {segment_name_vi}",
            "label_en": f"Below {segment_lower.capitalize()} avg",
            "score": 2,
            "benchmark": f"{min_benchmark}-{max_benchmark}%",
            "comparison": f"{margin_pct - min_benchmark:.1f} ppt",
        }


def rate_net_margin(margin_pct: Optional[float]) -> Dict[str, Any]:
    """
    Rate net margin performance.

    Rating thresholds:
    - Excellent: > 5%
    - Good: 2-5%
    - Low: < 2%

    Args:
        margin_pct: Net margin percentage

    Returns:
        Dictionary with rating and label
    """
    if margin_pct is None:
        return {"rating": "N/A", "label_vi": "Không có dữ liệu", "label_en": "No Data", "score": 0}

    if margin_pct > 5:
        return {
            "rating": "Xuất sắc",
            "label_vi": "Xuất sắc",
            "label_en": "Excellent",
            "score": 5,
            "benchmark": "> 5%",
        }
    elif margin_pct >= 2:
        return {
            "rating": "Tốt",
            "label_vi": "Tốt",
            "label_en": "Good",
            "score": 4,
            "benchmark": "2-5%",
        }
    else:
        return {
            "rating": "Thấp",
            "label_vi": "Thấp",
            "label_en": "Low",
            "score": 2,
            "benchmark": "< 2%",
        }


def calculate_working_capital_efficiency(balance_sheet: Dict[str, Any], income_statement: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate working capital efficiency metrics.

    Working Capital Efficiency: (Current Assets - Current Liabilities) / Revenue
    Lower or negative = more efficient (supplier-financed)

    Args:
        balance_sheet: Balance sheet data dict
        income_statement: Income statement data dict

    Returns:
        Dictionary with working capital metrics
    """
    # Extract values (do NOT default missing to 0; distinguish missing vs real zero)
    current_assets_raw = get_value(balance_sheet, "current_assets", "asset_current", "total_current_assets", default=None)
    current_liabilities_raw = get_value(balance_sheet, "current_liabilities", "liabilities_current", "total_current_liabilities", default=None)
    liabilities_total_raw = get_value(balance_sheet, "liabilities_total", "total_liabilities", default=None)
    liabilities_non_current_raw = get_value(balance_sheet, "liabilities_non_current", "non_current_liabilities", "long_term_liabilities", default=None)
    revenue_raw = get_value(income_statement, "net_revenue", "revenue", "total_revenue", default=None)

    def to_float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    current_assets = to_float(current_assets_raw)
    current_liabilities_reported = to_float(current_liabilities_raw)
    liabilities_total = to_float(liabilities_total_raw)
    liabilities_non_current = to_float(liabilities_non_current_raw)
    revenue = to_float(revenue_raw)

    # DB sign conventions: revenue may be negative credits in some sources
    if revenue is not None and revenue < 0:
        revenue = abs(revenue)

    data_quality_note = None

    # Working capital requires both current assets and current liabilities
    working_capital: Optional[float]
    if current_assets is None:
        working_capital = None
        data_quality_note = "Thiếu dữ liệu tài sản ngắn hạn."
    else:
        current_liabilities = current_liabilities_reported
        derived_used = False

        derived_current_liabilities = None
        if liabilities_total is not None and liabilities_non_current is not None and liabilities_total > liabilities_non_current:
            derived = liabilities_total - liabilities_non_current
            if derived > 0:
                derived_current_liabilities = derived

        if current_liabilities is None or current_liabilities <= 0:
            if derived_current_liabilities is not None:
                current_liabilities = derived_current_liabilities
                derived_used = True
                data_quality_note = "Nợ ngắn hạn được suy ra từ tổng nợ - nợ dài hạn (do thiếu/không hợp lệ liabilities_current)."
            else:
                working_capital = None
                data_quality_note = "Thiếu dữ liệu nợ ngắn hạn."
        else:
            current_ratio = safe_divide(current_assets, current_liabilities, default=None)
            if current_ratio is not None and current_ratio < 0:
                working_capital = None
                data_quality_note = "Dữ liệu thanh khoản không hợp lệ (current_ratio < 0)."
            else:
                # If reported CL yields an extreme outlier, prefer derived when available and improves plausibility.
                if current_ratio is not None and current_ratio > 20 and derived_current_liabilities is not None:
                    current_ratio_derived = safe_divide(current_assets, derived_current_liabilities, default=None)
                    if current_ratio_derived is not None and (current_ratio_derived <= 20 or current_ratio_derived < current_ratio):
                        current_liabilities = derived_current_liabilities
                        derived_used = True
                        current_ratio = current_ratio_derived
                        data_quality_note = "Nợ ngắn hạn được suy ra từ tổng nợ - nợ dài hạn (liabilities_current outlier)."

                working_capital = current_assets - current_liabilities

                if derived_used and current_ratio is not None and current_ratio > 20:
                    # Still very high after derivation: keep value but warn.
                    data_quality_note = (data_quality_note or "") + " Lưu ý: current_ratio rất cao; diễn giải thận trọng."

    wc_efficiency = safe_divide(working_capital, revenue, default=None) if working_capital is not None else None
    wc_to_sales_pct = (wc_efficiency * 100) if wc_efficiency is not None else None

    return {
        "working_capital": working_capital,
        "wc_efficiency_ratio": wc_efficiency,
        "wc_to_sales_pct": wc_to_sales_pct,
        "is_supplier_financed": (working_capital < 0) if working_capital is not None else None,
        "data_quality_note": data_quality_note,
    }


def rate_working_capital_efficiency(wc_ratio: Optional[float]) -> Dict[str, Any]:
    """
    Rate working capital efficiency.

    For retail, negative WC (supplier-financed) is ideal:
    - Excellent: <-5% (strong supplier financing)
    - Good: -5% to 5%
    - Average: 5-15%
    - Poor: > 15%

    Args:
        wc_ratio: Working capital to revenue ratio

    Returns:
        Dictionary with rating and interpretation
    """
    if wc_ratio is None:
        return {"rating": "N/A", "label_vi": "Không có dữ liệu", "label_en": "No Data", "score": 0}

    wc_pct = wc_ratio * 100

    if wc_pct < -5:
        return {
            "rating": "Xuất sắc",
            "label_vi": "Tài trợ bởi nhà cung cấp xuất sắc",
            "label_en": "Excellent supplier financing",
            "score": 5,
            "interpretation": "Vốn lưu động âm - nhà cung cấp tài trợ kinh doanh",
        }
    elif wc_pct <= 5:
        return {
            "rating": "Tốt",
            "label_vi": "Hiệu quả vốn lưu động tốt",
            "label_en": "Good working capital efficiency",
            "score": 4,
            "interpretation": "Vốn lưu động gần bằng 0 - tối ưu dòng tiền",
        }
    elif wc_pct <= 15:
        return {
            "rating": "Trung bình",
            "label_vi": "Vốn lưu động trung bình",
            "label_en": "Average working capital",
            "score": 3,
            "interpretation": "Cần vốn lưu động để vận hành",
        }
    else:
        return {
            "rating": "Cần cải thiện",
            "label_vi": "Sử dụng vốn lưu động cao",
            "label_en": "High working capital usage",
            "score": 2,
            "interpretation": "Đòi hỏi nhiều vốn lưu động để vận hành",
        }


def calculate_sga_efficiency(income_statement: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate Selling, General & Administrative expense efficiency.

    SG&A/Revenue: Lower is better (indicates better cost control)

    Args:
        income_statement: Income statement data dict

    Returns:
        Dictionary with SG&A metrics
    """
    # Extract values
    revenue = get_value(income_statement, "net_revenue", "revenue", "total_revenue", default=0)
    try:
        revenue = float(revenue)
        if revenue < 0:
            revenue = abs(revenue)
    except (TypeError, ValueError):
        revenue = 0

    # Try to get SG&A components
    selling_expense = get_value(income_statement, "selling_expense", "selling_expenses", "sales_marketing_expense", default=0)
    admin_expense = get_value(income_statement, "admin_expense", "administrative_expense", "general_admin_expense", default=0)
    sga_total = get_value(income_statement, "sga_expense", "selling_general_admin_expense", default=selling_expense + admin_expense)

    # Calculate SG&A to Revenue ratio
    sga_to_revenue = safe_divide(sga_total, revenue, default=None)
    sga_to_revenue_pct = sga_to_revenue * 100 if sga_to_revenue else None

    return {
        "selling_expense": selling_expense,
        "admin_expense": admin_expense,
        "sga_total": sga_total,
        "sga_to_revenue": sga_to_revenue,
        "sga_to_revenue_pct": sga_to_revenue_pct,
    }


def rate_sga_efficiency(sga_pct: Optional[float]) -> Dict[str, Any]:
    """
    Rate SG&A efficiency.

    Rating thresholds (lower is better):
    - Excellent: < 15%
    - Good: 15-25%
    - High: > 25%

    Args:
        sga_pct: SG&A as percentage of revenue

    Returns:
        Dictionary with rating and label
    """
    if sga_pct is None:
        return {"rating": "N/A", "label_vi": "Không có dữ liệu", "label_en": "No Data", "score": 0}

    if sga_pct < 15:
        return {
            "rating": "Xuất sắc",
            "label_vi": "Kiểm soát chi phí xuất sắc",
            "label_en": "Excellent cost control",
            "score": 5,
            "benchmark": "< 15%",
            "note": "Chi phí vận hành thấp",
        }
    elif sga_pct <= 25:
        return {
            "rating": "Tốt",
            "label_vi": "Kiểm soát chi phí tốt",
            "label_en": "Good cost control",
            "score": 4,
            "benchmark": "15-25%",
            "note": "Chi phí vận hành acceptable",
        }
    else:
        return {
            "rating": "Chi phí cao",
            "label_vi": "Chi phí vận hành cao",
            "label_en": "High operating costs",
            "score": 2,
            "benchmark": "> 25%",
            "note": "Cần tối ưu hóa chi phí vận hành",
        }


def calculate_cash_conversion_cycle(balance_sheet: Dict[str, Any], income_statement: Dict[str, Any], financial_ratios: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate Cash Conversion Cycle (CCC).

    CCC = DSO + DIO - DPO
    Retail ideally has negative CCC (sell before paying suppliers)

    Args:
        balance_sheet: Balance sheet data dict
        income_statement: Income statement data dict
        financial_ratios: Financial ratios data dict

    Returns:
        Dictionary with CCC components and total
    """
    # Get DSO from ratios or calculate
    dso = get_value(financial_ratios, "days_sales_outstanding", "dso", "receivable_days", default=None)

    # Get DIO (same as Days Sales of Inventory)
    inventory_metrics = calculate_inventory_metrics(balance_sheet, income_statement)
    dio = inventory_metrics["days_sales_inventory"]

    # Get DPO from ratios or calculate
    dpo = get_value(financial_ratios, "days_payable_outstanding", "dpo", "payable_days", default=None)

    # Calculate CCC
    ccc = None
    if dso is not None and dio is not None and dpo is not None:
        ccc = dso + dio - dpo

    return {
        "dso": dso,
        "dio": dio,
        "dpo": dpo,
        "ccc": ccc,
        "is_negative_ccc": ccc < 0 if ccc is not None else None,
    }


def rate_cash_conversion_cycle(ccc: Optional[float]) -> Dict[str, Any]:
    """
    Rate Cash Conversion Cycle performance.

    Rating thresholds (lower is better):
    - Excellent: < -15 days (negative CCC - sell before paying)
    - Good: -15 to 30 days
    - Average: 30-60 days
    - Poor: > 60 days

    Args:
        ccc: Cash Conversion Cycle in days

    Returns:
        Dictionary with rating and interpretation
    """
    if ccc is None:
        return {"rating": "N/A", "label_vi": "Không có dữ liệu", "label_en": "No Data", "score": 0}

    if ccc < -15:
        return {
            "rating": "Xuất sắc",
            "label_vi": "CCC âm xuất sắc",
            "label_en": "Excellent negative CCC",
            "score": 5,
            "interpretation": "Bán hàng trước khi trả tiền nhà cung cấp - dòng tiền tuyệt vời",
        }
    elif ccc <= 30:
        return {
            "rating": "Tốt",
            "label_vi": "CCC hiệu quả",
            "label_en": "Efficient CCC",
            "score": 4,
            "interpretation": "Vòng quay vốn nhanh",
        }
    elif ccc <= 60:
        return {
            "rating": "Trung bình",
            "label_vi": "CCC trung bình",
            "label_en": "Average CCC",
            "score": 3,
            "interpretation": "Vòng quay vốn acceptable",
        }
    else:
        return {
            "rating": "Chậm",
            "label_vi": "CCC chậm",
            "label_en": "Slow CCC",
            "score": 2,
            "interpretation": "Vốn bị chôn trong chu kỳ cung ứng lâu",
        }


def calculate_asset_turnover(balance_sheet: Dict[str, Any], income_statement: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate asset turnover metrics.

    Asset Turnover: Revenue / Average Total Assets
    Higher is better for retail

    Args:
        balance_sheet: Balance sheet data dict
        income_statement: Income statement data dict

    Returns:
        Dictionary with asset turnover metrics
    """
    # Extract values
    revenue = get_value(income_statement, "net_revenue", "revenue", "total_revenue", default=0)
    try:
        revenue = float(revenue)
        if revenue < 0:
            revenue = abs(revenue)
    except (TypeError, ValueError):
        revenue = 0
    total_assets = get_value(balance_sheet, "total_assets", default=0)
    total_assets_previous = get_value(balance_sheet, "total_assets_previous", default=total_assets)

    # Calculate average assets
    average_assets = (total_assets + total_assets_previous) / 2 if total_assets and total_assets_previous else total_assets

    # Calculate Asset Turnover
    asset_turnover = safe_divide(revenue, average_assets, default=None)

    return {
        "total_assets": total_assets,
        "total_assets_previous": total_assets_previous,
        "average_assets": average_assets,
        "asset_turnover": asset_turnover,
    }


def calculate_same_store_growth_proxy(income_statement: Dict[str, Any], balance_sheet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate same-store growth proxy metrics.

    Since we may not have store count data, we use:
    - Revenue per unit of selling expenses trend
    - Revenue growth rate

    Args:
        income_statement: Income statement data dict
        balance_sheet: Balance sheet data dict (for potential expansion assets)

    Returns:
        Dictionary with same-store growth proxy metrics
    """
    revenue = get_value(income_statement, "net_revenue", "revenue", "total_revenue", default=0)
    try:
        revenue = float(revenue)
        if revenue < 0:
            revenue = abs(revenue)
    except (TypeError, ValueError):
        revenue = 0
    selling_expense = get_value(income_statement, "selling_expense", "selling_expenses", default=0)

    # Revenue per unit of selling expenses (proxy for sales productivity)
    revenue_per_selling = safe_divide(revenue, selling_expense, default=None)

    # Look for expansion indicators in balance sheet
    # (e.g., leasehold improvements, equipment, deposits)
    leasehold_improvements = get_value(balance_sheet, "leasehold_improvements", "lease_improvements", default=0)
    equipment = get_value(balance_sheet, "equipment", "fixed_assets", default=0)
    expansion_assets = leasehold_improvements + (equipment * 0.3)  # Proxy

    return {
        "revenue_per_selling_expense": revenue_per_selling,
        "expansion_assets_proxy": expansion_assets,
        "has_expansion_indicators": expansion_assets > 0 if expansion_assets else False,
    }


def calculate_retail_efficiency_score(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate overall Retail Efficiency Score.

    Scoring weights:
    - Margin (30%): Gross Margin (15%), Net Margin (15%)
    - Turnover (30%): Inventory Turnover (15%), Asset Turnover (15%)
    - Cost Control (20%): SG&A/Revenue (10%), Operating Margin (10%)
    - Cash Efficiency (20%): Working Capital (10%), CCC (10%)

    Args:
        metrics: Dictionary of all calculated metrics

    Returns:
        Dictionary with efficiency score components and total
    """
    scores = {}
    max_score = 100

    # Margin Component (30 points)
    gross_margin_score = metrics.get("gross_margin_rating", {}).get("score", 0)
    net_margin_score = metrics.get("net_margin_rating", {}).get("score", 0)
    margin_component = (gross_margin_score * 3) + (net_margin_score * 3)  # Max 30 points

    # Turnover Component (30 points)
    inventory_turnover_score = metrics.get("inventory_turnover_rating", {}).get("score", 0)
    asset_turnover_score = metrics.get("asset_turnover_rating", {}).get("score", 0)
    turnover_component = (inventory_turnover_score * 3) + (asset_turnover_score * 3)  # Max 30 points

    # Cost Control Component (20 points)
    sga_score = metrics.get("sga_rating", {}).get("score", 0)
    operating_margin_score = metrics.get("operating_margin_rating", {}).get("score", 0)
    cost_control_component = (sga_score * 2) + (operating_margin_score * 2)  # Max 20 points

    # Cash Efficiency Component (20 points)
    wc_score = metrics.get("working_capital_rating", {}).get("score", 0)
    ccc_score = metrics.get("ccc_rating", {}).get("score", 0)
    cash_efficiency_component = (wc_score * 2) + (ccc_score * 2)  # Max 20 points

    total_score = margin_component + turnover_component + cost_control_component + cash_efficiency_component

    # Determine overall rating
    if total_score >= 85:
        overall_rating = "Xuất sắc"
        overall_rating_en = "Excellent"
    elif total_score >= 70:
        overall_rating = "Tốt"
        overall_rating_en = "Good"
    elif total_score >= 50:
        overall_rating = "Trung bình"
        overall_rating_en = "Average"
    else:
        overall_rating = "Cần cải thiện"
        overall_rating_en = "Needs Improvement"

    return {
        "total_score": total_score,
        "max_score": max_score,
        "overall_rating": overall_rating,
        "overall_rating_en": overall_rating_en,
        "components": {
            "margin": {"score": margin_component, "max": 30, "weight_pct": 30},
            "turnover": {"score": turnover_component, "max": 30, "weight_pct": 30},
            "cost_control": {"score": cost_control_component, "max": 20, "weight_pct": 20},
            "cash_efficiency": {"score": cash_efficiency_component, "max": 20, "weight_pct": 20},
        },
    }


def analyze_retail(
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any],
    cash_flow: Optional[Dict[str, Any]] = None,
    segment: str = "general",
) -> Dict[str, Any]:
    """
    Perform comprehensive retail industry analysis.

    Args:
        financial_ratios: Financial ratios data dict
        balance_sheet: Balance sheet data dict
        income_statement: Income statement data dict
        cash_flow: Cash flow statement data dict (optional)
        segment: Retail segment (electronics, fashion, grocery, jewelry, general)

    Returns:
        Dictionary with all retail metrics, ratings, and efficiency score
    """
    # Calculate all metrics
    inventory_metrics = calculate_inventory_metrics(balance_sheet, income_statement)
    margin_metrics = calculate_margins(income_statement, financial_ratios)
    working_capital_metrics = calculate_working_capital_efficiency(balance_sheet, income_statement)
    sga_metrics = calculate_sga_efficiency(income_statement)
    ccc_metrics = calculate_cash_conversion_cycle(balance_sheet, income_statement, financial_ratios)
    asset_turnover_metrics = calculate_asset_turnover(balance_sheet, income_statement)
    same_store_metrics = calculate_same_store_growth_proxy(income_statement, balance_sheet)

    # Rate all metrics
    inventory_turnover_rating = rate_inventory_turnover(inventory_metrics["inventory_turnover"])
    dsi_rating = rate_days_sales_inventory(inventory_metrics["days_sales_inventory"])
    gross_margin_rating = rate_gross_margin(margin_metrics["gross_margin_pct"], segment)
    net_margin_rating = rate_net_margin(margin_metrics["net_margin_pct"])
    working_capital_rating = rate_working_capital_efficiency(working_capital_metrics["wc_efficiency_ratio"])
    sga_rating = rate_sga_efficiency(sga_metrics["sga_to_revenue_pct"])
    ccc_rating = rate_cash_conversion_cycle(ccc_metrics["ccc"])

    # Rate asset turnover
    asset_turnover = asset_turnover_metrics["asset_turnover"]
    if asset_turnover is None:
        asset_turnover_rating = {"rating": "N/A", "score": 0}
    elif asset_turnover > 2.0:
        asset_turnover_rating = {"rating": "Xuất sắc", "label_vi": "Xuất sắc", "score": 5}
    elif asset_turnover > 1.5:
        asset_turnover_rating = {"rating": "Tốt", "label_vi": "Tốt", "score": 4}
    elif asset_turnover > 1.0:
        asset_turnover_rating = {"rating": "Trung bình", "label_vi": "Trung bình", "score": 3}
    else:
        asset_turnover_rating = {"rating": "Thấp", "label_vi": "Thấp", "score": 2}

    # Rate operating margin
    operating_margin_pct = margin_metrics["operating_margin_pct"]
    if operating_margin_pct is None:
        operating_margin_rating = {"rating": "N/A", "score": 0}
    elif operating_margin_pct > 10:
        operating_margin_rating = {"rating": "Xuất sắc", "label_vi": "Xuất sắc", "score": 5}
    elif operating_margin_pct > 5:
        operating_margin_rating = {"rating": "Tốt", "label_vi": "Tốt", "score": 4}
    elif operating_margin_pct > 2:
        operating_margin_rating = {"rating": "Trung bình", "label_vi": "Trung bình", "score": 3}
    else:
        operating_margin_rating = {"rating": "Thấp", "label_vi": "Thấp", "score": 2}

    # Compile all ratings
    all_metrics = {
        "gross_margin_rating": gross_margin_rating,
        "net_margin_rating": net_margin_rating,
        "inventory_turnover_rating": inventory_turnover_rating,
        "asset_turnover_rating": asset_turnover_rating,
        "sga_rating": sga_rating,
        "operating_margin_rating": operating_margin_rating,
        "working_capital_rating": working_capital_rating,
        "ccc_rating": ccc_rating,
    }

    # Calculate efficiency score
    efficiency_score = calculate_retail_efficiency_score(all_metrics)

    # Compile complete analysis
    return {
        "segment": segment,
        "inventory_metrics": {
            **inventory_metrics,
            "rating": inventory_turnover_rating,
            "dsi_rating": dsi_rating,
        },
        "margin_metrics": {
            **margin_metrics,
            "gross_margin_rating": gross_margin_rating,
            "net_margin_rating": net_margin_rating,
            "operating_margin_rating": operating_margin_rating,
        },
        "working_capital_metrics": {
            **working_capital_metrics,
            "rating": working_capital_rating,
        },
        "sga_metrics": {
            **sga_metrics,
            "rating": sga_rating,
        },
        "cash_conversion_metrics": {
            **ccc_metrics,
            "rating": ccc_rating,
        },
        "asset_turnover_metrics": {
            **asset_turnover_metrics,
            "rating": asset_turnover_rating,
        },
        "same_store_growth_proxy": same_store_metrics,
        "efficiency_score": efficiency_score,
    }
