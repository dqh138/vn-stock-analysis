#!/usr/bin/env python3
"""
Test script for Banking Analysis Module

This script tests the banking analysis module with sample data for a Vietnamese bank.
"""

import sys
from pathlib import Path

# Add the webapp directory to the path
webapp_dir = Path(__file__).parent
sys.path.insert(0, str(webapp_dir.parent.parent))

from webapp.analysis.banking_analysis import analyze_banking_sector


def test_banking_analysis():
    """Test banking analysis with sample data for a typical Vietnamese bank."""

    # Sample financial ratios (in billions VND)
    financial_ratios = {
        "net_interest_income": 25000,  # 25 trillion VND
        "roe": 18.5,  # 18.5%
        "roa": 1.8,   # 1.8%
    }

    # Sample balance sheet (in billions VND)
    balance_sheet = {
        "total_assets": 1500000,  # 1.5 quadrillion VND
        "equity_total": 150000,   # 150 trillion VND
        "loans_to_customers": 900000,  # 900 trillion VND
        "customer_deposits": 850000,   # 850 trillion VND
        "liabilities_current": 950000,  # 950 trillion VND
        "provision_credit_loss": 18000,  # 18 trillion VND
    }

    # Sample income statement (in billions VND)
    income_statement = {
        "interest_income": 50000,  # 50 trillion VND
        "financial_expense": 25000,  # 25 trillion VND
        "operating_expenses": 12000,  # 12 trillion VND
        "operating_profit": 28000,  # 28 trillion VND
        "other_income": 3000,  # 3 trillion VND
    }

    # Previous year balance sheet (for growth calculations)
    previous_balance_sheet = {
        "loans_to_customers": 800000,  # 800 trillion VND
        "customer_deposits": 780000,   # 780 trillion VND
        "liabilities_current": 870000,  # 870 trillion VND
    }

    # Perform banking analysis
    print("=" * 80)
    print("BANKING INDUSTRY ANALYSIS - TEST CASE")
    print("=" * 80)
    print()

    result = analyze_banking_sector(
        financial_ratios=financial_ratios,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        previous_balance_sheet=previous_balance_sheet
    )

    # Print results
    print(f"Analysis Type: {result['analysis_type']}")
    print(f"Industry: {result['industry']}")
    print(f"Description: {result['description']}")
    print()

    print("-" * 80)
    print("BANKING METRICS")
    print("-" * 80)

    # NIM
    nim = result['nim']
    print(f"\n{nim['label']} ({nim['label_en']})")
    print(f"  Value: {nim['value']}%")
    print(f"  Rating: {nim['rating']} ({nim['rating_en']})")
    print(f"  Description: {nim['description']}")

    # NPL Ratio
    npl = result['npl_ratio']
    print(f"\n{npl['label']} ({npl['label_en']})")
    print(f"  Value: {npl['value']}%")
    print(f"  Rating: {npl['rating']} ({npl['rating_en']})")
    print(f"  Description: {npl['description']}")

    # LLR
    llr = result['llr']
    print(f"\n{llr['label']} ({llr['label_en']})")
    print(f"  Value: {llr['value']}%")
    print(f"  Rating: {llr['rating']} ({llr['rating_en']})")
    print(f"  Description: {llr['description']}")

    # CAR
    car = result['car']
    print(f"\n{car['label']} ({car['label_en']})")
    print(f"  Value: {car['value']}%")
    print(f"  Rating: {car['rating']} ({car['rating_en']})")
    print(f"  Description: {car['description']}")

    # Cost-to-Income
    cti = result['cost_to_income']
    print(f"\n{cti['label']} ({cti['label_en']})")
    print(f"  Value: {cti['value']}%")
    print(f"  Rating: {cti['rating']} ({cti['rating_en']})")
    print(f"  Description: {cti['description']}")

    # LDR
    ldr = result['ldr']
    print(f"\n{ldr['label']} ({ldr['label_en']})")
    print(f"  Value: {ldr['value']}%")
    print(f"  Rating: {ldr['rating']} ({ldr['rating_en']})")
    print(f"  Description: {ldr['description']}")

    # Credit Growth
    credit_growth = result['credit_growth']
    print(f"\n{credit_growth['label']} ({credit_growth['label_en']})")
    print(f"  Value: {credit_growth['value']}%")
    print(f"  Rating: {credit_growth['rating']} ({credit_growth['rating_en']})")
    print(f"  Description: {credit_growth['description']}")

    # Deposit Growth
    deposit_growth = result['deposit_growth']
    print(f"\n{deposit_growth['label']} ({deposit_growth['label_en']})")
    print(f"  Value: {deposit_growth['value']}%")
    print(f"  Rating: {deposit_growth['rating']} ({deposit_growth['rating_en']})")
    print(f"  Description: {deposit_growth['description']}")

    # Health Score
    health = result['health_score']
    print("\n" + "=" * 80)
    print(f"{health['label']} ({health['label_en']})")
    print("=" * 80)
    print(f"Overall Score: {health['overall_score']}/100")
    print(f"Overall Rating: {health['overall_rating']} ({health['overall_rating_en']})")
    print(f"Description: {health['description']}")
    print()

    print("Component Scores:")
    for component_name, component_data in health['components'].items():
        print(f"\n  {component_data['label']} ({component_data['label_en']})")
        print(f"    Score: {component_data['score']}/100 (Weight: {component_data['weight']}%)")
        print(f"    Metrics:")
        for metric_name, metric_value in component_data['metrics'].items():
            print(f"      - {metric_name}: {metric_value:.2f}")

    print("\n" + "=" * 80)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    test_banking_analysis()
