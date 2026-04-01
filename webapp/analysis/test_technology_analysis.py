"""
Test suite for Technology Analysis module
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webapp.analysis import analyze_technology_company


def test_tech_company_full_data():
    """Test with complete data"""
    ratios = {
        "gross_margin": 35.5,
        "ebit_margin": 18.2,
        "roic": 22.0,
        "asset_turnover": 0.95,
        "revenue_growth": 25.0
    }

    balance_sheet = {
        "total_assets": 1000000000000,
        "fixed_assets": 200000000000,
        "cash_and_equivalents": 200000000000,
        "liabilities_total": 300000000000,
        "equity_total": 700000000000
    }

    income_statement = {
        "revenue": 1000000000000,
        "net_revenue": 950000000000,
        "operating_expenses": 300000000000,
        "gross_profit": 400000000000,
        "operating_profit": 200000000000,
        "net_profit": 150000000000,
        "corporate_income_tax": 50000000000
    }

    cash_flow = {
        "net_cash_from_operating_activities": 160000000000
    }

    result = analyze_technology_company(ratios, balance_sheet, income_statement, cash_flow)

    print("Test 1: Full Data - Technology Company")
    print(f"  Scalability Score: {result['scalability_score']['overall_score_formatted']}")
    print(f"  Rating: {result['scalability_score']['overall_rating']}")
    print(f"  R&D Intensity: {result['metrics']['rd_intensity']['value_formatted']} ({result['metrics']['rd_intensity']['rating_vi']})")
    print(f"  Asset-Light Ratio: {result['metrics']['asset_light_ratio']['value_formatted']} ({result['metrics']['asset_light_ratio']['rating_vi']})")
    print(f"  Gross Margin: {result['metrics']['gross_margin']['value_formatted']} ({result['metrics']['gross_margin']['rating_vi']})")
    print(f"  ROIC: {result['metrics']['roic']['value_formatted']} ({result['metrics']['roic']['rating_vi']})")
    print(f"  Summary Points: {len(result['summary'])}")
    print("  ✓ PASSED\n")


def test_tech_company_minimal_data():
    """Test with minimal/incomplete data"""
    ratios = {
        "revenue_growth": 10.0
    }

    balance_sheet = {
        "total_assets": 500000000000,
        "fixed_assets": 150000000000
    }

    income_statement = {
        "revenue": 300000000000,
        "operating_expenses": 150000000000
    }

    result = analyze_technology_company(ratios, balance_sheet, income_statement)

    print("Test 2: Minimal Data - Handling Missing Fields")
    print(f"  Scalability Score: {result['scalability_score']['overall_score_formatted']}")
    print(f"  R&D Intensity: {result['metrics']['rd_intensity']['value_formatted']}")
    print(f"  ROIC: {result['metrics']['roic']['value_formatted']}")
    print(f"  Summary Points: {len(result['summary'])}")
    print("  ✓ PASSED (handles missing data)\n")


def test_hardware_tech_company():
    """Test hardware company with lower margins but high turnover"""
    ratios = {
        "gross_margin": 18.0,
        "ebit_margin": 8.0,
        "roic": 14.0,
        "asset_turnover": 1.2,
        "revenue_growth": 15.0
    }

    balance_sheet = {
        "total_assets": 800000000000,
        "fixed_assets": 350000000000,
        "cash_and_equivalents": 100000000000,
        "liabilities_total": 400000000000,
        "equity_total": 400000000000
    }

    income_statement = {
        "revenue": 960000000000,
        "operating_expenses": 200000000000,
        "gross_profit": 172800000000,
        "operating_profit": 76800000000,
        "net_profit": 57600000000
    }

    result = analyze_technology_company(ratios, balance_sheet, income_statement)

    print("Test 3: Hardware Tech Company (Lower Margin, High Turnover)")
    print(f"  Scalability Score: {result['scalability_score']['overall_score_formatted']}")
    print(f"  Rating: {result['scalability_score']['overall_rating']}")
    print(f"  Gross Margin: {result['metrics']['gross_margin']['value_formatted']} ({result['metrics']['gross_margin']['rating_vi']})")
    print(f"  Asset-Light Ratio: {result['metrics']['asset_light_ratio']['value_formatted']} ({result['metrics']['asset_light_ratio']['rating_vi']})")
    print(f"  Asset Turnover: {result['metrics']['asset_turnover']['value_formatted']} ({result['metrics']['asset_turnover']['rating_vi']})")
    print("  ✓ PASSED\n")


def test_software_company():
    """Test software company with high margins and asset-light model"""
    ratios = {
        "gross_margin": 65.0,
        "ebit_margin": 25.0,
        "roic": 28.0,
        "asset_turnover": 0.7,
        "revenue_growth": 30.0
    }

    balance_sheet = {
        "total_assets": 200000000000,
        "fixed_assets": 30000000000,
        "cash_and_equivalents": 80000000000,
        "liabilities_total": 40000000000,
        "equity_total": 160000000000
    }

    income_statement = {
        "revenue": 140000000000,
        "operating_expenses": 40000000000,
        "gross_profit": 91000000000,
        "operating_profit": 35000000000,
        "net_profit": 28000000000,
        "corporate_income_tax": 7000000000
    }

    result = analyze_technology_company(ratios, balance_sheet, income_statement)

    print("Test 4: Software Company (High Margin, Asset-Light)")
    print(f"  Scalability Score: {result['scalability_score']['overall_score_formatted']}")
    print(f"  Rating: {result['scalability_score']['overall_rating']}")
    print(f"  Gross Margin: {result['metrics']['gross_margin']['value_formatted']} ({result['metrics']['gross_margin']['rating_vi']})")
    print(f"  Asset-Light Ratio: {result['metrics']['asset_light_ratio']['value_formatted']} ({result['metrics']['asset_light_ratio']['rating_vi']})")
    print(f"  ROIC: {result['metrics']['roic']['value_formatted']} ({result['metrics']['roic']['rating_vi']})")
    print("  ✓ PASSED\n")


def test_edge_case_zero_values():
    """Test handling of zero and edge case values"""
    ratios = {}
    balance_sheet = {
        "total_assets": 0,
        "fixed_assets": 0
    }
    income_statement = {
        "revenue": 0,
        "operating_expenses": 0
    }

    result = analyze_technology_company(ratios, balance_sheet, income_statement)

    print("Test 5: Edge Cases - Zero Values")
    print(f"  Scalability Score: {result['scalability_score']['overall_score_formatted']}")
    print(f"  All metrics should handle zero values gracefully")
    print("  ✓ PASSED (no crashes)\n")


if __name__ == "__main__":
    print("=" * 60)
    print("TECHNOLOGY ANALYSIS MODULE - TEST SUITE")
    print("=" * 60)
    print()

    test_tech_company_full_data()
    test_tech_company_minimal_data()
    test_hardware_tech_company()
    test_software_company()
    test_edge_case_zero_values()

    print("=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
