"""
Data Contract Module - Vietnamese Financial Analysis Webapp

Provides standardized data access patterns with column alias mapping,
unit conventions, and safe value extraction.

Author: Core Data Team
Version: 1.0.0
Date: 2026-02-15
"""

from typing import Any, Dict, List, Optional, Union


# ============================================================================
# COLUMN ALIASES - Maps code names to DB column names
# ============================================================================

COLUMN_ALIASES: Dict[str, List[str]] = {
    # Balance Sheet (DB column names verified from data_coverage_report.csv)
    "total_assets": ["total_assets"],
    "current_assets": ["asset_current", "assets_current"],  # DB: asset_current
    "non_current_assets": ["asset_non_current", "non_current_assets"],  # DB: asset_non_current
    "cash_and_cash_equivalents": ["cash_and_equivalents", "cash_and_cash_equivalents", "cash", "cash_equivalents"],  # DB: cash_and_equivalents
    "accounts_receivable": ["accounts_receivable", "receivables", "trade_receivables"],
    "inventory": ["inventory", "inventories"],
    "fixed_assets": ["fixed_assets", "property_plant_equipment", "ppe"],

    # Liabilities (CRITICAL MAPPINGS - DB column names verified from data_coverage_report.csv)
    "total_liabilities": ["liabilities_total"],  # DB: liabilities_total
    "current_liabilities": ["liabilities_current"],  # DB: liabilities_current
    "long_term_liabilities": ["liabilities_non_current", "non_current_liabilities", "long_term_liabilities"],  # DB: liabilities_non_current

    # Equity (CRITICAL MAPPING - DB column names verified from data_coverage_report.csv)
    "total_equity": ["equity_total"],  # DB: equity_total
    "share_capital": ["share_capital", "common_stock", "equity_share_capital"],
    "retained_earnings": ["retained_earnings", "retained_profit"],

    # Debt
    "long_term_debt": ["long_term_debt", "debt_non_current", "non_current_debt"],
    "short_term_debt": ["short_term_debt", "debt_current", "current_debt"],
    "accounts_payable": ["accounts_payable", "payables", "trade_payables"],

    # Income Statement
    # CRITICAL: Prefer net_revenue for non-banks (DB often stores revenue as negative credits)
    "revenue": ["net_revenue", "revenue", "total_revenue", "sales"],
    "cost_of_goods_sold": ["cost_of_goods_sold", "cogs", "cost_of_revenue"],
    "gross_profit": ["gross_profit"],

    # Profit metrics (DB column names verified from data_coverage_report.csv)
    "operating_profit": ["operating_profit", "operating_income"],  # DB: operating_profit
    "profit_before_tax": ["profit_before_tax", "ebt", "earnings_before_tax"],
    "net_income": ["net_profit_parent_company", "net_profit", "net_income", "profit_after_tax"],  # DB: net_profit_parent_company
    "net_profit_parent_company": ["net_profit_parent_company", "net_profit", "net_income"],  # Same as net_income

    # Expenses (DB column names verified from data_coverage_report.csv)
    "operating_expenses": ["operating_expenses", "total_operating_expenses"],
    "selling_expense": ["selling_expense", "selling_expenses", "sales_marketing_expense"],
    "admin_expense": ["admin_expense", "administrative_expense", "general_admin_expense"],
    "financial_expense": ["financial_expense", "interest_expense", "interest_expense"],
    "interest_expense": ["interest_expense", "financial_expense"],
    "corporate_income_tax": ["corporate_income_tax", "income_tax_expense", "tax_expense"],  # DB: corporate_income_tax

    # Other income/expense
    "other_income": ["other_income"],
    "other_expenses": ["other_expenses"],

    # Cash Flow Statement (CRITICAL MAPPINGS - DB column names verified from data_coverage_report.csv)
    "operating_cash_flow": ["net_cash_from_operating_activities"],  # DB: net_cash_from_operating_activities
    "capital_expenditure": ["purchase_purchase_fixed_assets", "capex", "capital_expenditure"],  # DB: purchase_purchase_fixed_assets (typically negative)
    "investing_cash_flow": ["net_cash_from_investing_activities"],
    "financing_cash_flow": ["net_cash_from_financing_activities"],
    "net_change_in_cash": ["net_cash_flow_period", "net_increase_in_cash", "net_change_in_cash"],  # DB: net_cash_flow_period
    "cash_beginning": ["cash_and_cash_equivalents_beginning"],  # DB: cash_and_cash_equivalents_beginning
    "cash_ending": ["cash_and_cash_equivalents_ending"],  # DB: cash_and_cash_equivalents_ending
    "dividends_paid": ["dividends_paid", "dividend_paid"],
    "interest_paid": ["interest_expense_paid", "interest_paid"],  # DB: interest_expense_paid
    "tax_paid": ["corporate_income_tax_paid", "tax_paid"],  # DB: corporate_income_tax_paid

    # Financial Ratios - Liquidity
    "current_ratio": ["current_ratio"],
    "quick_ratio": ["quick_ratio", "acid_test_ratio"],
    "cash_ratio": ["cash_ratio"],

    # Financial Ratios - Leverage
    "debt_to_equity": ["debt_to_equity", "debt_equity_ratio"],
    "debt_to_assets": ["debt_to_assets", "debt_assets_ratio"],
    "interest_coverage": ["interest_coverage_ratio", "interest_coverage"],

    # Financial Ratios - Profitability (decimal format: 0.20 = 20%)
    "gross_margin": ["gross_profit_margin", "gross_margin"],
    "operating_margin": ["operating_margin", "ebit_margin"],
    "net_profit_margin": ["net_profit_margin", "net_margin"],
    "ebitda_margin": ["ebitda_margin"],
    "roe": ["roe", "return_on_equity"],
    "roa": ["roa", "return_on_assets"],
    "roic": ["roic", "return_on_invested_capital"],

    # Financial Ratios - Efficiency (x multiples)
    "asset_turnover": ["asset_turnover"],
    "inventory_turnover": ["inventory_turnover"],
    "receivable_turnover": ["receivable_turnover"],
    "payable_turnover": ["payable_turnover"],

    # Financial Ratios - Days metrics
    "dso": ["days_sales_outstanding", "dso", "receivable_days"],
    "dio": ["days_inventory_outstanding", "dio", "inventory_days"],
    "dpo": ["days_payable_outstanding", "dpo", "payable_days"],

    # Valuation Ratios (x multiples)
    "pe_ratio": ["price_to_earnings", "pe_ratio"],
    "pb_ratio": ["price_to_book", "pb_ratio"],
    "ps_ratio": ["price_to_sales", "ps_ratio"],
    "ev_ebitda": ["ev_to_ebitda", "ev_ebitda"],
}


# ============================================================================
# UNIT CONVENTIONS - Specifies units for each metric
# ============================================================================

UNIT_CONVENTIONS: Dict[str, str] = {
    # Balance Sheet - All in VND (raw amounts)
    "total_assets": "VND",
    "current_assets": "VND",
    "non_current_assets": "VND",
    "cash_and_cash_equivalents": "VND",
    "accounts_receivable": "VND",
    "inventory": "VND",
    "fixed_assets": "VND",
    "total_liabilities": "VND",
    "current_liabilities": "VND",
    "long_term_liabilities": "VND",
    "total_equity": "VND",
    "share_capital": "VND",
    "retained_earnings": "VND",
    "long_term_debt": "VND",
    "short_term_debt": "VND",
    "accounts_payable": "VND",

    # Income Statement - All in VND (raw amounts)
    "revenue": "VND",
    "cost_of_goods_sold": "VND",
    "gross_profit": "VND",
    "operating_profit": "VND",
    "profit_before_tax": "VND",
    "net_income": "VND",
    "operating_expenses": "VND",
    "selling_expense": "VND",
    "admin_expense": "VND",
    "financial_expense": "VND",
    "interest_expense": "VND",
    "corporate_income_tax": "VND",
    "other_income": "VND",
    "other_expenses": "VND",

    # Cash Flow - All in VND (raw amounts)
    "operating_cash_flow": "VND",
    "capital_expenditure": "VND",
    "investing_cash_flow": "VND",
    "financing_cash_flow": "VND",
    "net_change_in_cash": "VND",
    "cash_beginning": "VND",
    "cash_ending": "VND",
    "dividends_paid": "VND",
    "interest_paid": "VND",
    "tax_paid": "VND",

    # Ratios - Liquidity (x multiples)
    "current_ratio": "x",
    "quick_ratio": "x",
    "cash_ratio": "x",

    # Ratios - Leverage (x multiples)
    "debt_to_equity": "x",
    "debt_to_assets": "x",
    "interest_coverage": "x",

    # Ratios - Profitability (decimal: 0.21 = 21%)
    "gross_margin": "decimal",
    "operating_margin": "decimal",
    "net_profit_margin": "decimal",
    "ebitda_margin": "decimal",
    "roe": "decimal",
    "roa": "decimal",
    "roic": "decimal",

    # Ratios - Efficiency (x multiples)
    "asset_turnover": "x",
    "inventory_turnover": "x",
    "receivable_turnover": "x",
    "payable_turnover": "x",

    # Ratios - Days metrics
    "dso": "days",
    "dio": "days",
    "dpo": "days",

    # Valuation (x multiples)
    "pe_ratio": "x",
    "pb_ratio": "x",
    "ps_ratio": "x",
    "ev_ebitda": "x",
}

# ============================================================================
# SIGN CONVENTIONS (DATA LIMITS)
# ============================================================================

# Some upstream sources store income-statement credit items (e.g., revenue) as negative numbers.
# For research-grade ratio math, many "flow magnitude" inputs should be treated by magnitude.
#
# NOTE:
# - We do NOT apply this implicitly inside get_value(), because callers sometimes need raw signs for QA/audit.
# - Use get_value_magnitude() explicitly in computation layers that require consistent sign semantics.
MAGNITUDE_ONLY_METRICS = {
    # Income statement flows (used as denominators / intensity metrics)
    "revenue",
    "cost_of_goods_sold",
    "operating_expenses",
    "selling_expense",
    "admin_expense",
    "financial_expense",
    "interest_expense",
    "corporate_income_tax",
    "other_expenses",
}


# ============================================================================
# DATA TYPE CONVENTIONS
# ============================================================================

DATA_TYPES: Dict[str, str] = {
    # Balance Sheet
    "total_assets": "DECIMAL",
    "current_assets": "DECIMAL",
    "total_liabilities": "DECIMAL",
    "current_liabilities": "DECIMAL",
    "total_equity": "DECIMAL",

    # Income Statement
    "revenue": "DECIMAL",
    "net_income": "DECIMAL",
    "operating_profit": "DECIMAL",

    # Cash Flow
    "operating_cash_flow": "DECIMAL",
    "capital_expenditure": "DECIMAL",

    # Ratios (stored as decimal: 0.21 = 21%)
    "roe": "DECIMAL",
    "roa": "DECIMAL",
    "gross_margin": "DECIMAL",
    "net_profit_margin": "DECIMAL",
}


# ============================================================================
# VALUE EXTRACTION FUNCTIONS
# ============================================================================

def get_value(
    data: Dict[str, Any],
    code_name: str,
    default: Optional[float] = None
) -> Optional[float]:
    """
    Get value from data dict using code name with automatic alias resolution.

    Tries multiple column names in order of preference:
    1. Primary DB column name (first in COLUMN_ALIASES[code_name])
    2. Fallback aliases (subsequent names in list)

    Args:
        data: Dictionary containing DB row data (flat format)
        code_name: Code variable name (e.g., 'total_liabilities')
        default: Default value if not found (default: None)

    Returns:
        Float value or default if not found

    Examples:
        >>> balance_sheet = {'liabilities_total': 1000000}
        >>> get_value(balance_sheet, 'total_liabilities')
        1000000.0

        >>> # Works with aliases too
        >>> balance_sheet = {'liabilities_current': 500000}
        >>> get_value(balance_sheet, 'current_liabilities')
        500000.0
    """
    if code_name not in COLUMN_ALIASES:
        # Code name not in aliases - try direct lookup
        value = data.get(code_name)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
        return default

    # Try each alias in order
    for alias in COLUMN_ALIASES[code_name]:
        value = data.get(alias)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue

    # CRITICAL FIX: Also try the code_name itself as fallback
    # This handles cases where data uses code names directly (e.g., tests, in-memory dicts)
    # while COLUMN_ALIASES maps to DB column names
    if code_name in data:
        value = data.get(code_name)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass

    # No value found
    return default


def get_value_safe(
    data: Dict[str, Any],
    code_name: str,
    default: float = 0.0
) -> float:
    """
    Get value from data dict with default=0.0 (never returns None).

    Same as get_value() but ensures a float return value (never None).

    Args:
        data: Dictionary containing DB row data
        code_name: Code variable name
        default: Default value if not found (default: 0.0)

    Returns:
        Float value (never None)

    Examples:
        >>> get_value_safe(balance_sheet, 'total_assets')
        1000000.0

        >>> # Missing data returns default (0.0)
        >>> get_value_safe(balance_sheet, 'missing_field')
        0.0
    """
    result = get_value(data, code_name, default=default)
    return result if result is not None else default


def get_value_magnitude(
    data: Dict[str, Any],
    code_name: str,
    default: Optional[float] = None,
) -> Optional[float]:
    """
    Get value like get_value(), but normalize to magnitude for selected flow metrics.

    Academic rationale:
        Some DB variants store credit items (e.g., revenue) as negative. For many ratios,
        we need consistent, positive denominators. This helper enforces that *explicitly*.
    """
    value = get_value(data, code_name, default=default)
    if value is None:
        return default
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return abs(v) if code_name in MAGNITUDE_ONLY_METRICS else v


def get_unit(code_name: str) -> str:
    """
    Get unit convention for a metric.

    Args:
        code_name: Code variable name

    Returns:
        Unit string ('VND', 'decimal', 'x', 'days')

    Examples:
        >>> get_unit('revenue')
        'VND'

        >>> get_unit('roe')
        'decimal'

        >>> get_unit('pe_ratio')
        'x'
    """
    return UNIT_CONVENTIONS.get(code_name, "unknown")


def normalize_value(
    value: Optional[float],
    code_name: str,
    target_unit: str = "billions"
) -> Optional[float]:
    """
    Convert value to specified unit for display.

    Args:
        value: Raw value from database
        code_name: Code variable name (to determine source unit)
        target_unit: Target unit ('billions', 'millions', 'percent', 'raw')

    Returns:
        Normalized value

    Examples:
        >>> # Convert VND to billions
        >>> normalize_value(15000000000, 'revenue', 'billions')
        15.0

        >>> # Convert decimal ratio to percentage
        >>> normalize_value(0.20, 'roe', 'percent')
        20.0

        >>> # Return raw value
        >>> normalize_value(1.5, 'current_ratio', 'raw')
        1.5
    """
    if value is None:
        return None

    source_unit = get_unit(code_name)

    # VND conversions
    if source_unit == "VND":
        if target_unit == "billions":
            return value / 1_000_000_000
        elif target_unit == "millions":
            return value / 1_000_000
        elif target_unit == "percent":
            return value  # No conversion for VND to percent
        else:
            return value  # raw

    # Decimal to percent
    elif source_unit == "decimal":
        if target_unit == "percent":
            return value * 100
        else:
            return value  # raw

    # Other units (x, days) - return raw
    else:
        return value


def format_value(
    value: Optional[float],
    code_name: str,
    unit: str = "auto"
) -> str:
    """
    Format value for display with appropriate unit suffix.

    Args:
        value: Raw value from database
        code_name: Code variable name
        unit: Unit display ('auto', 'billions', 'millions', 'percent', 'raw')

    Returns:
        Formatted string

    Examples:
        >>> format_value(15000000000, 'revenue', 'billions')
        '15.00 tỷ'

        >>> format_value(0.20, 'roe', 'percent')
        '20.0%'

        >>> format_value(1.5, 'current_ratio', 'auto')
        '1.50x'
    """
    if value is None:
        return "N/A"

    source_unit = get_unit(code_name)

    # Auto-determine unit
    if unit == "auto":
        if source_unit == "VND":
            if abs(value) >= 1_000_000_000:
                unit = "billions"
            else:
                unit = "millions"
        elif source_unit == "decimal":
            unit = "percent"
        else:
            unit = "raw"

    # Normalize value
    normalized = normalize_value(value, code_name, unit)

    if normalized is None:
        return "N/A"

    # Format with unit suffix
    if unit == "billions":
        return f"{normalized:,.2f} tỷ"
    elif unit == "millions":
        return f"{normalized:,.0f} triệu"
    elif unit == "percent":
        return f"{normalized:,.1f}%"
    elif source_unit == "x":
        return f"{normalized:.2f}x"
    elif source_unit == "days":
        return f"{normalized:.0f} ngày"
    else:
        return f"{normalized:,.0f}"


# ============================================================================
# DATA VALIDATION FUNCTIONS
# ============================================================================

def is_valid_positive(value: Optional[float], allow_zero: bool = True) -> bool:
    """
    Check if value is valid and positive.

    Args:
        value: Value to check
        allow_zero: Whether zero is considered valid

    Returns:
        True if value is valid and positive (or zero if allow_zero=True)
    """
    if value is None:
        return False
    if value < 0:
        return False
    if value == 0 and not allow_zero:
        return False
    return True


def is_valid_ratio(value: Optional[float]) -> bool:
    """
    Check if value is a valid ratio (decimal or multiple).

    Valid ratios: -10 <= value <= 1000 (allows for extreme but valid cases)

    Args:
        value: Value to check

    Returns:
        True if value is a valid ratio
    """
    if value is None:
        return False
    return -10 <= value <= 1000


def validate_calculation_inputs(
    numerator: Optional[float],
    denominator: Optional[float],
    allow_negative_numerator: bool = True,
    allow_negative_denominator: bool = True
) -> bool:
    """
    Validate inputs for division-based calculations.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        allow_negative_numerator: Allow negative numerator (common in finance)
        allow_negative_denominator: Allow negative denominator (possible with negative equity, etc.)

    Returns:
        True if inputs are valid for calculation
    """
    if numerator is None or denominator is None:
        return False

    if denominator == 0:
        return False

    if not allow_negative_numerator and numerator < 0:
        return False

    if not allow_negative_denominator and denominator < 0:
        return False

    return True


# ============================================================================
# SAFE CALCULATION FUNCTIONS
# ============================================================================

def safe_divide(
    numerator: Optional[float],
    denominator: Optional[float],
    default: Optional[float] = None
) -> Optional[float]:
    """
    Perform safe division with null/zero checking.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value if division fails (default: None)

    Returns:
        Result of division or default if failed

    Examples:
        >>> safe_divide(100, 50)
        2.0

        >>> safe_divide(100, 0)
        None

        >>> safe_divide(100, 0, default=0)
        0
    """
    if not validate_calculation_inputs(numerator, denominator):
        return default

    return numerator / denominator


def safe_sum(*values: Optional[float]) -> float:
    """
    Sum multiple values, ignoring None values.

    Args:
        *values: Values to sum

    Returns:
        Sum of valid values (0.0 if all None)

    Examples:
        >>> safe_sum(10, 20, 30)
        60.0

        >>> safe_sum(10, None, 30)
        40.0

        >>> safe_sum(None, None)
        0.0
    """
    total = 0.0
    for v in values:
        if v is not None:
            total += v
    return total


def safe_multiply(
    *values: Optional[float],
    default: Optional[float] = None
) -> Optional[float]:
    """
    Multiply multiple values, returning default if any is None or zero.

    Args:
        *values: Values to multiply
        default: Default value if multiplication fails

    Returns:
        Product of values or default if failed

    Examples:
        >>> safe_multiply(2, 3, 4)
        24.0

        >>> safe_multiply(2, None, 4)
        None

        >>> safe_multiply(2, 0, 4)
        0.0
    """
    result = 1.0
    for v in values:
        if v is None:
            return default
        result *= v
    return result


# ============================================================================
# SPECIAL CALCULATIONS
# ============================================================================

def calculate_free_cash_flow(
    operating_cash_flow: Optional[float],
    capital_expenditure: Optional[float]
) -> Optional[float]:
    """
    Calculate Free Cash Flow (FCF).

    CRITICAL: capital_expenditure is typically negative in DB.
    Formula: FCF = operating_cash_flow - ABS(capital_expenditure)

    Args:
        operating_cash_flow: Operating cash flow from 'net_cash_from_operating_activities'
        capital_expenditure: CapEx from 'purchase_purchase_fixed_assets' (typically negative)

    Returns:
        Free Cash Flow or None if calculation fails

    Examples:
        >>> calculate_free_cash_flow(1000000000, -500000000)
        500000000.0

        >>> calculate_free_cash_flow(1000000000, 500000000)
        500000000.0  # Handles positive capex too
    """
    if operating_cash_flow is None or capital_expenditure is None:
        return None

    # Always subtract absolute value of CapEx
    return operating_cash_flow - abs(capital_expenditure)


def calculate_working_capital(
    current_assets: Optional[float],
    current_liabilities: Optional[float]
) -> Optional[float]:
    """
    Calculate Working Capital.

    Formula: Working Capital = Current Assets - Current Liabilities

    Args:
        current_assets: From 'assets_current'
        current_liabilities: From 'liabilities_current'

    Returns:
        Working Capital or None if calculation fails
    """
    if current_assets is None or current_liabilities is None:
        return None

    return current_assets - current_liabilities


def calculate_ebit(
    operating_profit: Optional[float],
    profit_before_tax: Optional[float],
    interest_expense: Optional[float] = None
) -> Optional[float]:
    """
    Calculate EBIT (Earnings Before Interest and Taxes).

    Args:
        operating_profit: From 'operating_profit' (preferred)
        profit_before_tax: From 'profit_before_tax' (fallback)
        interest_expense: From 'interest_expense' (needed if using profit_before_tax)

    Returns:
        EBIT or None if calculation fails

    Examples:
        >>> # Method 1: Direct from operating_profit
        >>> calculate_ebit(operating_profit=100000, profit_before_tax=None)
        100000

        >>> # Method 2: Calculate from profit_before_tax
        >>> calculate_ebit(profit_before_tax=80000, interest_expense=20000)
        100000
    """
    # Prefer operating_profit
    if operating_profit is not None:
        return operating_profit

    # Fallback: calculate from profit_before_tax
    if profit_before_tax is not None and interest_expense is not None:
        return profit_before_tax + interest_expense

    return None


# ============================================================================
# EXPORTED FUNCTIONS SUMMARY
# ============================================================================

__all__ = [
    # Column mappings
    "COLUMN_ALIASES",
    "UNIT_CONVENTIONS",
    "DATA_TYPES",

    # Value extraction
    "get_value",
    "get_value_safe",
    "get_unit",
    "normalize_value",
    "format_value",

    # Validation
    "is_valid_positive",
    "is_valid_ratio",
    "validate_calculation_inputs",

    # Safe calculations
    "safe_divide",
    "safe_sum",
    "safe_multiply",

    # Special calculations
    "calculate_free_cash_flow",
    "calculate_working_capital",
    "calculate_ebit",
]


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Example data (simulating DB rows)
    balance_sheet = {
        "total_assets": 1_000_000_000_000,  # 1,000 billion VND
        "liabilities_total": 400_000_000_000,  # 400 billion VND
        "liabilities_current": 200_000_000_000,  # 200 billion VND
        "equity_total": 600_000_000_000,  # 600 billion VND
    }

    income_statement = {
        "revenue": 500_000_000_000,  # 500 billion VND
        "operating_profit": 100_000_000_000,  # 100 billion VND
        "net_profit": 75_000_000_000,  # 75 billion VND
    }

    cash_flow = {
        "net_cash_from_operating_activities": 120_000_000_000,  # 120 billion VND
        "purchase_purchase_fixed_assets": -30_000_000_000,  # -30 billion VND (negative!)
    }

    financial_ratios = {
        "roe": 0.125,  # 12.5%
        "current_ratio": 1.5,  # 1.5x
        "debt_to_equity": 0.67,  # 0.67x
    }

    # Example 1: Get value with alias resolution
    print("Example 1: Get value with alias resolution")
    total_liab = get_value(balance_sheet, "total_liabilities")
    print(f"  Total Liabilities: {format_value(total_liab, 'total_liabilities', 'billions')}")

    # Example 2: Calculate ratios
    print("\nExample 2: Calculate ratios")
    debt_to_equity = safe_divide(
        get_value(balance_sheet, "total_liabilities"),
        get_value(balance_sheet, "total_equity")
    )
    print(f"  Debt/Equity: {format_value(debt_to_equity, 'debt_to_equity', 'raw')}")

    # Example 3: Free Cash Flow (handles negative CapEx)
    print("\nExample 3: Free Cash Flow")
    fcf = calculate_free_cash_flow(
        get_value(cash_flow, "operating_cash_flow"),
        get_value(cash_flow, "capital_expenditure")
    )
    print(f"  Free Cash Flow: {format_value(fcf, 'operating_cash_flow', 'billions')}")

    # Example 4: Format ROE as percentage
    print("\nExample 4: Format ROE as percentage")
    roe = get_value(financial_ratios, "roe")
    print(f"  ROE: {format_value(roe, 'roe', 'percent')}")

    # Example 5: Working Capital
    print("\nExample 5: Working Capital")
    working_cap = calculate_working_capital(
        get_value(balance_sheet, "current_assets"),
        get_value(balance_sheet, "current_liabilities")
    )
    print(f"  Working Capital: {format_value(working_cap, 'current_assets', 'billions')}")
