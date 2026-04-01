"""
Reconciliation System - Vietnamese Financial Analysis Webapp

Detects discrepancies between computed and provided financial metrics.
This catches data quality issues and formula mismatches.

Author: Data Quality Team
Version: 1.0.0
Date: 2026-02-15
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from .data_contract import (
    get_value,
    get_value_safe,
    get_value_magnitude,
    safe_divide,
    COLUMN_ALIASES,
    UNIT_CONVENTIONS
)

from .annual_selector import (
    get_financial_ratios_annual,
    select_balance_sheet_annual,
    select_cash_flow_annual,
    select_income_statement_annual,
)

# ============================================================================
# RECONCILIATION CONFIGURATION
# ============================================================================

# Default tolerances by metric type (as percentage)
DEFAULT_TOLERANCES = {
    "ratio": 0.05,      # 5% for ratios (ROE, ROA, margins, etc.)
    "margin": 0.03,     # 3% for margins (stricter match)
    "multiple": 0.10,   # 10% for multiples (market data noisy)
    "turnover": 0.05,   # 5% for turnover ratios
    "days": 0.05,       # 5% for days metrics
    "leverage": 0.05,   # 5% for leverage ratios
}

# Metric type classification
METRIC_TYPES = {
    # Profitability ratios
    "roe": "ratio",
    "roa": "ratio",
    "roic": "ratio",
    "net_profit_margin": "margin",
    "gross_margin": "margin",
    "ebit_margin": "margin",
    "operating_margin": "margin",

    # Liquidity ratios
    "current_ratio": "ratio",
    "quick_ratio": "ratio",
    "cash_ratio": "ratio",

    # Leverage ratios
    "debt_to_equity": "leverage",
    "debt_to_equity_adjusted": "leverage",
    "financial_leverage": "leverage",
    "equity_to_charter_capital": "ratio",

    # Efficiency ratios
    "asset_turnover": "turnover",
    "fixed_asset_turnover": "turnover",
    "inventory_turnover": "turnover",

    # Days metrics
    "days_sales_outstanding": "days",
    "days_inventory_outstanding": "days",
    "days_payable_outstanding": "days",
    "cash_conversion_cycle": "days",

    # Valuation multiples
    "price_to_earnings": "multiple",
    "price_to_book": "multiple",
    "price_to_sales": "multiple",
    "ev_to_ebitda": "multiple",
    "ev_to_ebit": "multiple",
    "price_to_cash_flow": "multiple",
}


# ============================================================================
# METRIC COMPUTATION FORMULAS
# ============================================================================

def compute_metric(
    metric: str,
    income_statement: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    cash_flow: Dict[str, Any]
) -> Tuple[Optional[float], List[str], str]:
    """
    Compute a metric from raw financial data.

    Returns:
        (computed_value, input_descriptions, formula)

    Args:
        metric: Metric name (e.g., 'roe')
        income_statement: Income statement data
        balance_sheet: Balance sheet data
        cash_flow: Cash flow statement data

    Returns:
        Tuple of (computed_value, input_descriptions, formula)
    """
    # Helper to format input descriptions
    def format_inputs(**kwargs) -> List[str]:
        """Format input values as list of strings."""
        inputs = []
        for name, value in kwargs.items():
            if value is not None:
                # Convert to billions for readability
                if abs(value) >= 1_000_000_000:
                    display = f"{name}={value/1_000_000_000:.1f}B"
                else:
                    display = f"{name}={value:,.0f}"
                inputs.append(display)
        return inputs

    # Helper to format VND values
    def format_vnd(value: Optional[float]) -> Optional[str]:
        if value is None:
            return None
        if abs(value) >= 1_000_000_000:
            return f"{value/1_000_000_000:.1f}B VND"
        return f"{value:,.0f} VND"

    # Profitability Ratios
    if metric == "roe":
        # ROE = Net Income / Average Equity
        # Try net_profit_parent_company first (more accurate for VN companies)
        net_income = get_value(income_statement, "net_profit_parent_company")
        if net_income is None:
            net_income = get_value(income_statement, "net_income")
        equity = get_value(balance_sheet, "total_equity")

        if net_income is None or equity is None or equity == 0:
            return None, [], "net_profit_parent_company / equity_total"

        computed = net_income / equity
        inputs = format_inputs(net_profit_parent_company=net_income, equity_total=equity)
        return computed, inputs, "net_profit_parent_company / equity_total"

    elif metric == "roa":
        # ROA = Net Income / Total Assets
        # Try net_profit_parent_company first
        net_income = get_value(income_statement, "net_profit_parent_company")
        if net_income is None:
            net_income = get_value(income_statement, "net_income")
        assets = get_value(balance_sheet, "total_assets")

        if net_income is None or assets is None or assets == 0:
            return None, [], "net_profit_parent_company / total_assets"

        computed = net_income / assets
        inputs = format_inputs(net_profit_parent_company=net_income, total_assets=assets)
        return computed, inputs, "net_profit_parent_company / total_assets"

    elif metric == "net_profit_margin":
        # Net Margin = Net Income / Revenue
        # Try net_profit_parent_company first
        net_income = get_value(income_statement, "net_profit_parent_company")
        if net_income is None:
            net_income = get_value(income_statement, "net_income")
        revenue_raw = get_value(income_statement, "revenue")
        revenue = get_value_magnitude(income_statement, "revenue")

        if net_income is None or revenue is None or revenue == 0:
            return None, [], "net_profit_parent_company / net_revenue"

        computed = net_income / revenue
        inputs = format_inputs(net_profit_parent_company=net_income, net_revenue=revenue)
        if revenue_raw is not None and revenue is not None and revenue_raw != revenue:
            inputs.append("NOTE: abs(revenue) used due to sign convention")
        return computed, inputs, "net_profit_parent_company / net_revenue"

    elif metric == "gross_margin":
        # Gross Margin = Gross Profit / Revenue
        gross_profit = get_value(income_statement, "gross_profit")
        revenue_raw = get_value(income_statement, "revenue")
        revenue = get_value_magnitude(income_statement, "revenue")

        if gross_profit is None or revenue is None or revenue == 0:
            return None, [], "gross_profit / net_revenue"

        computed = gross_profit / revenue
        inputs = format_inputs(gross_profit=gross_profit, net_revenue=revenue)
        if revenue_raw is not None and revenue is not None and revenue_raw != revenue:
            inputs.append("NOTE: abs(revenue) used due to sign convention")
        return computed, inputs, "gross_profit / net_revenue"

    elif metric == "ebit_margin" or metric == "operating_margin":
        # EBIT Margin = Operating Profit / Revenue
        operating_profit = get_value(income_statement, "operating_profit")
        revenue_raw = get_value(income_statement, "revenue")
        revenue = get_value_magnitude(income_statement, "revenue")

        if operating_profit is None or revenue is None or revenue == 0:
            return None, [], "operating_profit / net_revenue"

        computed = operating_profit / revenue
        inputs = format_inputs(operating_profit=operating_profit, net_revenue=revenue)
        if revenue_raw is not None and revenue is not None and revenue_raw != revenue:
            inputs.append("NOTE: abs(revenue) used due to sign convention")
        return computed, inputs, "operating_profit / net_revenue"

    # Liquidity Ratios
    elif metric == "current_ratio":
        # Current Ratio = Current Assets / Current Liabilities
        current_assets = get_value(balance_sheet, "current_assets")
        current_liabilities_reported = get_value(balance_sheet, "current_liabilities")
        liabilities_total = get_value(balance_sheet, "total_liabilities")
        liabilities_non_current = get_value(balance_sheet, "long_term_liabilities")

        derived_current_liabilities = None
        if (liabilities_total is not None and liabilities_non_current is not None and
                liabilities_total > liabilities_non_current and (liabilities_total - liabilities_non_current) > 0):
            derived_current_liabilities = liabilities_total - liabilities_non_current

        current_liabilities = current_liabilities_reported
        denom_formula = "liabilities_current"
        if current_liabilities is None or current_liabilities <= 0:
            if derived_current_liabilities is not None:
                current_liabilities = derived_current_liabilities
                denom_formula = "(liabilities_total - liabilities_non_current)"
        elif current_assets is not None and derived_current_liabilities is not None:
            try:
                cr_reported = current_assets / current_liabilities
                cr_derived = current_assets / derived_current_liabilities
            except Exception:
                cr_reported = None
                cr_derived = None
            # If reported liquidity is an extreme outlier, prefer derived when it materially reduces the outlier.
            if cr_reported is not None and cr_reported > 20 and cr_derived is not None and (cr_derived <= 20 or cr_derived < cr_reported):
                current_liabilities = derived_current_liabilities
                denom_formula = "(liabilities_total - liabilities_non_current)"

        if current_assets is None or current_liabilities is None or current_liabilities <= 0:
            return None, [], "assets_current / liabilities_current"

        computed = current_assets / current_liabilities
        inputs = format_inputs(
            assets_current=current_assets,
            liabilities_current=current_liabilities_reported,
            liabilities_total=liabilities_total,
            liabilities_non_current=liabilities_non_current,
        )
        if denom_formula != "liabilities_current":
            inputs.append("NOTE: liabilities_current derived from totals")
        # Guardrail: under current DB limits, extreme liquidity ratios are often caused by
        # semantically unreliable `liabilities_current` (mapping collisions or partial rows).
        if computed < 0 or computed > 20:
            inputs.append("UNRELIABLE_INPUT: current_ratio outlier (>20x or <0)")
            return None, inputs, "assets_current / liabilities_current"
        return computed, inputs, f"assets_current / {denom_formula}"

    elif metric == "quick_ratio":
        # Quick Ratio = (Current Assets - Inventory) / Current Liabilities
        current_assets = get_value(balance_sheet, "current_assets")
        inventory = get_value(balance_sheet, "inventory")
        current_liabilities_reported = get_value(balance_sheet, "current_liabilities")
        liabilities_total = get_value(balance_sheet, "total_liabilities")
        liabilities_non_current = get_value(balance_sheet, "long_term_liabilities")

        derived_current_liabilities = None
        if (liabilities_total is not None and liabilities_non_current is not None and
                liabilities_total > liabilities_non_current and (liabilities_total - liabilities_non_current) > 0):
            derived_current_liabilities = liabilities_total - liabilities_non_current

        current_liabilities = current_liabilities_reported
        denom_formula = "liabilities_current"
        if current_liabilities is None or current_liabilities <= 0:
            if derived_current_liabilities is not None:
                current_liabilities = derived_current_liabilities
                denom_formula = "(liabilities_total - liabilities_non_current)"
        elif current_assets is not None and inventory is not None and derived_current_liabilities is not None:
            numerator = current_assets - inventory
            if numerator is not None:
                try:
                    qr_reported = numerator / current_liabilities
                    qr_derived = numerator / derived_current_liabilities
                except Exception:
                    qr_reported = None
                    qr_derived = None
                if qr_reported is not None and qr_reported > 20 and qr_derived is not None and (qr_derived <= 20 or qr_derived < qr_reported):
                    current_liabilities = derived_current_liabilities
                    denom_formula = "(liabilities_total - liabilities_non_current)"

        if current_assets is None or inventory is None or current_liabilities is None or current_liabilities <= 0:
            return None, [], "(assets_current - inventory) / liabilities_current"

        computed = (current_assets - inventory) / current_liabilities
        inputs = format_inputs(
            assets_current=current_assets,
            inventory=inventory,
            liabilities_current=current_liabilities_reported,
            liabilities_total=liabilities_total,
            liabilities_non_current=liabilities_non_current,
        )
        if denom_formula != "liabilities_current":
            inputs.append("NOTE: liabilities_current derived from totals")
        if computed < 0 or computed > 20:
            inputs.append("UNRELIABLE_INPUT: quick_ratio outlier (>20x or <0)")
            return None, inputs, "(assets_current - inventory) / liabilities_current"
        return computed, inputs, f"(assets_current - inventory) / {denom_formula}"

    # Leverage Ratios
    elif metric == "debt_to_equity" or metric == "debt_to_equity_adjusted":
        # Debt/Equity = Total Liabilities / Total Equity
        total_liabilities = get_value(balance_sheet, "total_liabilities")
        total_equity = get_value(balance_sheet, "total_equity")

        if total_liabilities is None or total_equity is None or total_equity == 0:
            return None, [], "liabilities_total / equity_total"

        computed = total_liabilities / total_equity
        inputs = format_inputs(liabilities_total=total_liabilities, equity_total=total_equity)
        return computed, inputs, "liabilities_total / equity_total"

    elif metric == "financial_leverage":
        # Financial Leverage = Total Assets / Total Equity
        total_assets = get_value(balance_sheet, "total_assets")
        total_equity = get_value(balance_sheet, "total_equity")

        if total_assets is None or total_equity is None or total_equity == 0:
            return None, [], "total_assets / equity_total"

        computed = total_assets / total_equity
        inputs = format_inputs(total_assets=total_assets, equity_total=total_equity)
        return computed, inputs, "total_assets / equity_total"

    # Efficiency Ratios
    elif metric == "asset_turnover":
        # Asset Turnover = Revenue / Total Assets
        revenue_raw = get_value(income_statement, "revenue")
        revenue = get_value_magnitude(income_statement, "revenue")
        total_assets = get_value(balance_sheet, "total_assets")

        if revenue is None or total_assets is None or total_assets == 0:
            return None, [], "net_revenue / total_assets"

        computed = revenue / total_assets
        inputs = format_inputs(net_revenue=revenue, total_assets=total_assets)
        if revenue_raw is not None and revenue is not None and revenue_raw != revenue:
            inputs.append("NOTE: abs(revenue) used due to sign convention")
        return computed, inputs, "net_revenue / total_assets"

    elif metric == "fixed_asset_turnover":
        # Fixed Asset Turnover = Revenue / Fixed Assets
        revenue_raw = get_value(income_statement, "revenue")
        revenue = get_value_magnitude(income_statement, "revenue")
        # Try non-current assets as proxy for fixed assets
        fixed_assets = get_value(balance_sheet, "non_current_assets")

        if revenue is None or fixed_assets is None or fixed_assets == 0:
            return None, [], "net_revenue / non_current_assets"

        computed = revenue / fixed_assets
        inputs = format_inputs(net_revenue=revenue, non_current_assets=fixed_assets)
        if revenue_raw is not None and revenue is not None and revenue_raw != revenue:
            inputs.append("NOTE: abs(revenue) used due to sign convention")
        return computed, inputs, "net_revenue / non_current_assets"

    elif metric == "inventory_turnover":
        # Inventory Turnover = COGS / Average Inventory
        cogs_raw = get_value(income_statement, "cost_of_goods_sold")
        cogs = get_value_magnitude(income_statement, "cost_of_goods_sold")
        inventory = get_value(balance_sheet, "inventory")

        if cogs is None or inventory is None or inventory == 0:
            return None, [], "cost_of_goods_sold / inventory"

        computed = cogs / inventory
        inputs = format_inputs(cost_of_goods_sold=cogs, inventory=inventory)
        if cogs_raw is not None and cogs is not None and cogs_raw != cogs:
            inputs.append("NOTE: abs(COGS) used due to sign convention")
        return computed, inputs, "cost_of_goods_sold / inventory"

    # Valuation Multiples (cannot compute from statements - need market data)
    elif metric in ["price_to_earnings", "price_to_book", "price_to_sales",
                    "ev_to_ebitda", "ev_to_ebit", "price_to_cash_flow"]:
        # These require market price data - mark as NOT_APPLICABLE for computation
        return None, [], f"{metric} (requires market data)"

    # Default: unknown metric
    return None, [], f"Unknown formula for {metric}"


# ============================================================================
# RECONCILIATION FUNCTION
# ============================================================================

def reconcile_metric(
    symbol: str,
    year: int,
    metric: str,
    db_path=None,
    tolerance: Optional[float] = None
) -> Dict[str, Any]:
    """
    Compare computed vs provided value for a metric.

    Args:
        symbol: Stock ticker (e.g., 'FPT')
        year: Year to reconcile
        metric: Metric name (e.g., 'roe', 'net_profit_margin')
        db_path: Path to SQLite database
        tolerance: Optional custom tolerance (overrides default)

    Returns:
        {
            "symbol": "FPT",
            "year": 2024,
            "metric": "roe",
            "computed": 0.215,
            "provided": 0.21,
            "delta_abs": 0.005,
            "delta_pct": 2.38,
            "status": "OK",  # OK, WARN, FAIL, MISSING_INPUT, NOT_APPLICABLE
            "tolerance": 0.05,
            "inputs_used": ["net_income=2100B", "equity_total=9767B"],
            "formula": "net_income / equity_total"
        }
    """
    # Validate inputs
    symbol = symbol.strip().upper()
    metric = metric.strip()

    # Determine tolerance
    metric_type = METRIC_TYPES.get(metric, "ratio")
    if tolerance is None:
        tolerance = DEFAULT_TOLERANCES.get(metric_type, 0.05)

    # Connect to database
    from .. import db as _db
    with _db.connect() as conn:
        ratios_row = get_financial_ratios_annual(conn, symbol, year)
        provided_val = ratios_row.get(metric) if ratios_row else None
        provided = float(provided_val) if provided_val is not None else None

        income_statement = select_income_statement_annual(conn, symbol, year) or {}
        balance_sheet = select_balance_sheet_annual(conn, symbol, year, financial_ratios_row=ratios_row) or {}
        cash_flow = select_cash_flow_annual(conn, symbol, year, balance_sheet_row=balance_sheet) or {}

    # Compute metric from raw data
    computed, inputs_used, formula = compute_metric(
        metric, income_statement, balance_sheet, cash_flow
    )

    # Determine status
    if computed is None:
        if metric in ["price_to_earnings", "price_to_book", "price_to_sales",
                      "ev_to_ebitda", "ev_to_ebit", "price_to_cash_flow"]:
            status = "NOT_APPLICABLE"
        elif inputs_used:
            status = "INVALID"
        else:
            status = "MISSING_INPUT"
        delta_abs = None
        delta_pct = None
    elif provided is None:
        status = "MISSING_INPUT"
        delta_abs = None
        delta_pct = None
    else:
        delta_abs = abs(computed - provided)
        # Use provided as base for percentage (avoid division by zero)
        if provided != 0:
            delta_pct = (delta_abs / abs(provided)) * 100
        else:
            # If provided is 0, use computed as base
            if computed != 0:
                delta_pct = (delta_abs / abs(computed)) * 100
            else:
                delta_pct = 0.0

        # Determine status based on tolerance
        tolerance_pct = tolerance * 100  # Convert to percentage
        if delta_pct < tolerance_pct:
            status = "OK"
        elif delta_pct < 2 * tolerance_pct:
            status = "WARN"
        else:
            status = "FAIL"

    return {
        "symbol": symbol,
        "year": year,
        "metric": metric,
        "metric_type": metric_type,
        "computed": round(computed, 6) if computed is not None else None,
        "provided": round(provided, 6) if provided is not None else None,
        "delta_abs": round(delta_abs, 6) if delta_abs is not None else None,
        "delta_pct": round(delta_pct, 2) if delta_pct is not None else None,
        "status": status,
        "tolerance": tolerance,
        "tolerance_pct": round(tolerance * 100, 1),
        "inputs_used": inputs_used,
        "formula": formula
    }


def reconcile_all_metrics(
    symbol: str,
    year: int,
    db_path=None,
    metrics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Reconcile multiple metrics for a symbol/year.

    Args:
        symbol: Stock ticker
        year: Year to reconcile
        db_path: Path to database
        metrics: List of metrics to reconcile (default: all hybrid metrics)

    Returns:
        {
            "symbol": "FPT",
            "year": 2024,
            "metrics": [...],
            "summary": {
                "total": 10,
                "ok": 8,
                "warn": 1,
                "fail": 0,
                "missing_input": 1,
                "not_applicable": 0
            }
        }
    """
    # Default to all computable metrics if not specified
    if metrics is None:
        metrics = [
            "roe", "roa", "net_profit_margin", "gross_margin", "ebit_margin",
            "current_ratio", "quick_ratio", "debt_to_equity",
            "asset_turnover", "inventory_turnover"
        ]

    results = []
    summary = {
        "total": len(metrics),
        "ok": 0,
        "warn": 0,
        "fail": 0,
        "missing_input": 0,
        "invalid": 0,
        "not_applicable": 0
    }

    for metric in metrics:
        result = reconcile_metric(symbol, year, metric, db_path)
        results.append(result)
        status_key = (result.get("status") or "").lower()
        summary[status_key] = summary.get(status_key, 0) + 1

    return {
        "symbol": symbol,
        "year": year,
        "metrics": results,
        "summary": summary
    }


# ============================================================================
# EXPORTED FUNCTIONS
# ============================================================================

__all__ = [
    "reconcile_metric",
    "reconcile_all_metrics",
    "METRIC_TYPES",
    "DEFAULT_TOLERANCES",
    "compute_metric"
]
