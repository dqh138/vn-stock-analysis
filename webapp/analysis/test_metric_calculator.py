"""
Test script for Metric Calculator and Core Analysis fixes

Validates:
1. Metric calculator follows source policy correctly
2. FCF calculation uses abs(CapEx)
3. CAGR returns None (not 0) for invalid inputs
4. CCC calculation handles null values correctly
5. ROE scoring normalizes decimal vs percent correctly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.metric_calculator import MetricCalculator, calculate_metric
from analysis.core_analysis import CoreAnalysisEngine


def test_fcf_calculation():
    """Test FCF calculation with negative CapEx"""
    print("=" * 60)
    print("TEST 1: FCF Calculation (Negative CapEx)")
    print("=" * 60)

    # Test data with negative CapEx (typical in DB)
    cash_flow = {
        'year': 2024,
        'net_cash_from_operating_activities': 150000000000,  # 150 billion
        'purchase_purchase_fixed_assets': -50000000000  # -50 billion (negative!)
    }

    calculator = MetricCalculator({}, {}, {}, cash_flow)

    # Calculate FCF using data_contract function
    from analysis.data_contract import calculate_free_cash_flow
    fcf = calculate_free_cash_flow(
        cash_flow.get('net_cash_from_operating_activities'),
        cash_flow.get('purchase_purchase_fixed_assets')
    )

    print(f"Operating Cash Flow: {cash_flow['net_cash_from_operating_activities']:,.0f} VND")
    print(f"Capital Expenditure: {cash_flow['purchase_purchase_fixed_assets']:,.0f} VND (negative)")
    print(f"Expected FCF: 150 - 50 = 100 billion VND")
    print(f"Calculated FCF: {fcf:,.0f} VND")
    print(f"Status: {'PASS' if fcf == 100000000000 else 'FAIL'}")
    print()


def test_cagr_returns_none():
    """Test CAGR returns None (not 0) for invalid inputs"""
    print("=" * 60)
    print("TEST 2: CAGR Returns None for Invalid Inputs")
    print("=" * 60)

    # Test case 1: start_value = 0
    print("Case 1: start_value = 0")
    income_statement = {'year': 2024, 'revenue': 1000}
    previous_income_statement = {'year': 2023, 'revenue': 0}

    engine = CoreAnalysisEngine({}, {}, income_statement, {}, previous_income_statement=previous_income_statement)
    result = engine.calculate_cagr('revenue', years=3)

    print(f"Start value: {result['start_value']}")
    print(f"End value: {result['end_value']}")
    print(f"CAGR: {result['cagr']}")
    print(f"Status: {'PASS' if result['cagr'] is None else 'FAIL'}")
    print()

    # Test case 2: start_value is None
    print("Case 2: start_value is None (no previous year)")
    income_statement = {'year': 2024, 'revenue': 1000}
    previous_income_statement = {}

    engine = CoreAnalysisEngine({}, {}, income_statement, {}, previous_income_statement=previous_income_statement)
    result = engine.calculate_cagr('revenue', years=3)

    print(f"Start value: {result['start_value']}")
    print(f"End value: {result['end_value']}")
    print(f"CAGR: {result['cagr']}")
    print(f"Status: {'PASS' if result['cagr'] is None else 'FAIL'}")
    print()

    # Test case 3: Valid CAGR calculation
    print("Case 3: Valid CAGR (growth from 1000 to 1200)")
    income_statement = {'year': 2024, 'revenue': 1200}
    previous_income_statement = {'year': 2023, 'revenue': 1000}

    engine = CoreAnalysisEngine({}, {}, income_statement, {}, previous_income_statement=previous_income_statement)
    result = engine.calculate_cagr('revenue', years=3)

    print(f"Start value: {result['start_value']}")
    print(f"End value: {result['end_value']}")
    print(f"CAGR: {result['cagr']}%")
    expected_cagr = ((1200 / 1000) - 1) * 100
    print(f"Expected CAGR: {expected_cagr:.2f}%")
    print(f"Status: {'PASS' if abs(result['cagr'] - expected_cagr) < 0.01 else 'FAIL'}")
    print()


def test_ccc_calculation():
    """Test CCC calculation with null handling"""
    print("=" * 60)
    print("TEST 3: CCC Calculation with Null Handling")
    print("=" * 60)

    # Test case 1: All data available
    print("Case 1: All data available")
    income_statement = {
        'year': 2024,
        'revenue': 500000000000,  # 500 billion
        'cost_of_goods_sold': 300000000000  # 300 billion
    }
    balance_sheet = {
        'year': 2024,
        'accounts_receivable': 50000000000,  # 50 billion
        'inventory': 60000000000,  # 60 billion
        'accounts_payable': 40000000000  # 40 billion
    }

    engine = CoreAnalysisEngine({}, balance_sheet, income_statement, {})
    result = engine.calculate_working_capital_efficiency()

    print(f"DSO: {result['dso']:.1f} days (expected: 36.5)")
    print(f"DIO: {result['dio']:.1f} days (expected: 73.0)")
    print(f"DPO: {result['dpo']:.1f} days (expected: 48.7)")
    print(f"CCC: {result['ccc']:.1f} days (expected: 60.8)")
    print(f"Status: {'PASS' if result['ccc'] is not None else 'FAIL'}")
    print()

    # Test case 2: Missing COGS (should return None)
    print("Case 2: Missing COGS")
    income_statement = {
        'year': 2024,
        'revenue': 500000000000
        # cost_of_goods_sold missing
    }
    balance_sheet = {
        'year': 2024,
        'accounts_receivable': 50000000000,
        'inventory': 60000000000,
        'accounts_payable': 40000000000
    }

    engine = CoreAnalysisEngine({}, balance_sheet, income_statement, {})
    result = engine.calculate_working_capital_efficiency()

    print(f"DSO: {result['dso']}")
    print(f"DIO: {result['dio']}")
    print(f"DPO: {result['dpo']}")
    print(f"CCC: {result['ccc']}")
    print(f"Status: {'PASS' if result['ccc'] is None else 'FAIL'}")
    print()


def test_roe_scoring():
    """Test ROE scoring with decimal normalization"""
    print("=" * 60)
    print("TEST 4: ROE Scoring (Decimal Normalization)")
    print("=" * 60)

    # Test case 1: ROE = 0.21 (21% in decimal format)
    print("Case 1: ROE = 0.21 (21% in decimal)")
    financial_ratios = {'year': 2024, 'roe': 0.21, 'roa': 0.12, 'net_profit_margin': 0.15}

    engine = CoreAnalysisEngine(financial_ratios, {}, {}, {})
    score = engine._calculate_profitability_score(0.21, 0.12, 0.15)

    print(f"ROE: 0.21 (decimal format)")
    print(f"ROA: 0.12 (decimal format)")
    print(f"Net Margin: 0.15 (decimal format)")
    print(f"Profitability Score: {score:.1f}/100")

    # Expected: ROE >= 0.20 gets 40 points, ROA >= 0.10 gets 35 points, Net Margin >= 0.15 gets 25 points
    # Average: (40 + 35 + 25) / 3 = 33.33
    expected_score = (40 + 35 + 25) / 3
    print(f"Expected Score: {expected_score:.1f}/100")
    print(f"Status: {'PASS' if abs(score - expected_score) < 0.1 else 'FAIL'}")
    print()

    # Test case 2: ROE = 21.0 (percent format - should be handled correctly)
    print("Case 2: ROE = 21.0 (if stored as percent)")
    score2 = engine._calculate_profitability_score(21.0, 12.0, 15.0)
    print(f"ROE: 21.0 (percent format)")
    print(f"Profitability Score: {score2:.1f}/100")
    print(f"Note: If stored as percent, score should be very high (>= 0.20 threshold met)")
    print()


def test_metric_calculator():
    """Test Metric Calculator with source policy"""
    print("=" * 60)
    print("TEST 5: Metric Calculator Source Policy")
    print("=" * 60)

    financial_ratios = {
        'year': 2024,
        'roe': 0.21,
        'roa': 0.12,
        'price_to_earnings': 15.5
    }

    balance_sheet = {
        'year': 2024,
        'liabilities_total': 400000000000,
        'liabilities_current': 200000000000,
        'equity_total': 600000000000,
        'assets_current': 300000000000
    }

    income_statement = {
        'year': 2024,
        'net_profit': 126000000000,
        'revenue': 500000000000,
        'gross_profit': 200000000000
    }

    cash_flow_statement = {
        'year': 2024,
        'net_cash_from_operating_activities': 150000000000,
        'purchase_purchase_fixed_assets': -50000000000
    }

    calculator = MetricCalculator(financial_ratios, balance_sheet, income_statement, cash_flow_statement)

    # Test computed metric (gross_margin)
    print("Test: Computed Metric (gross_margin)")
    result = calculator.calculate_metric('gross_margin')
    print(f"Metric: {result['metric']}")
    print(f"Value: {result['value']}")
    print(f"Source: {result['source']}")
    print(f"Status: {result['status']}")
    print(f"Formula: {result['formula']}")
    print(f"Inputs: {result['inputs_used']}")
    print(f"Status: {'PASS' if result['status'] == 'OK' else 'FAIL'}")
    print()

    # Test provided metric (pe_ratio)
    print("Test: Provided Metric (pe_ratio)")
    result = calculator.calculate_metric('pe_ratio')
    print(f"Metric: {result['metric']}")
    print(f"Value: {result['value']}")
    print(f"Source: {result['source']}")
    print(f"Status: {result['status']}")
    print(f"Status: {'PASS' if result['status'] == 'OK' else 'FAIL'}")
    print()

    # Test hybrid metric (roe)
    print("Test: Hybrid Metric (roe)")
    result = calculator.calculate_metric('roe')
    print(f"Metric: {result['metric']}")
    print(f"Value: {result['value']}")
    print(f"Source: {result['source']}")
    print(f"Status: {result['status']}")
    print(f"Formula: {result['formula']}")
    print(f"Inputs: {result['inputs_used']}")
    print(f"Status: {'PASS' if result['status'] == 'OK' else 'FAIL'}")
    print()

    # Test disabled metric (nim)
    print("Test: Disabled Metric (nim)")
    result = calculator.calculate_metric('nim')
    print(f"Metric: {result['metric']}")
    print(f"Value: {result['value']}")
    print(f"Source: {result['source']}")
    print(f"Status: {result['status']}")
    print(f"Reason: {result.get('reason', 'N/A')}")
    print(f"Status: {'PASS' if result['status'] == 'DISABLED' else 'FAIL'}")
    print()

    # Test metric summary
    print("Test: Metric Summary")
    summary = calculator.get_metric_summary()
    print(f"Total Metrics: {summary['total_metrics']}")
    print(f"Available: {summary['available_count']}")
    print(f"Missing: {summary['missing_count']}")
    print(f"Disabled: {summary['disabled_count']}")
    print(f"As of Year: {summary['as_of_year']}")
    print()


if __name__ == "__main__":
    print("\n")
    print("*" * 60)
    print("* METRIC CALCULATOR AND CORE ANALYSIS TEST SUITE")
    print("*" * 60)
    print("\n")

    test_fcf_calculation()
    test_cagr_returns_none()
    test_ccc_calculation()
    test_roe_scoring()
    test_metric_calculator()

    print("=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)
