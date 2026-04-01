"""
Technology Analysis Module - Comprehensive Demonstration

This demo showcases the technology analysis module with real-world examples
of Vietnamese technology companies across different sub-sectors.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webapp.analysis import analyze_technology_company


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_metric(metric_data, indent="  "):
    """Print a single metric with formatting"""
    print(f"{indent}{metric_data['label']} ({metric_data['label_en']}): {metric_data['value_formatted']}")
    print(f"{indent}  Rating: {metric_data['rating']} - {metric_data['rating_vi']}")
    if metric_data.get('note'):
        print(f"{indent}  Note: {metric_data['note']}")


def demo_software_company():
    """
    Demo: High-growth SaaS/Software company
    Characteristics: High margins, asset-light, high R&D
    """
    print_section("DEMO 1: Software/SaaS Company")

    financial_ratios = {
        "gross_margin": 72.0,
        "ebit_margin": 28.0,
        "roic": 32.0,
        "asset_turnover": 0.65,
        "revenue_growth": 45.0
    }

    balance_sheet = {
        "total_assets": 150000000000,
        "fixed_assets": 18000000000,
        "cash_and_equivalents": 85000000000,
        "liabilities_total": 25000000000,
        "equity_total": 125000000000
    }

    income_statement = {
        "revenue": 97500000000,
        "net_revenue": 95000000000,
        "operating_expenses": 35000000000,
        "gross_profit": 70200000000,
        "operating_profit": 27300000000,
        "net_profit": 21840000000,
        "corporate_income_tax": 5460000000
    }

    result = analyze_technology_company(financial_ratios, balance_sheet, income_statement)

    print("\nCompany Profile: Software-as-a-Service (SaaS)")
    print("Characteristics: High margins, asset-light, heavy R&D investment\n")

    print("Key Metrics:")
    print_metric(result['metrics']['gross_margin'])
    print_metric(result['metrics']['asset_light_ratio'])
    print_metric(result['metrics']['rd_intensity'])
    print_metric(result['metrics']['roic'])

    print(f"\nTech Scalability Score: {result['scalability_score']['overall_score_formatted']}")
    print(f"Overall Rating: {result['scalability_score']['overall_rating']}\n")

    print("Analysis Summary:")
    for point in result['summary']:
        print(f"  • {point}")


def demo_hardware_company():
    """
    Demo: Hardware/Device manufacturer
    Characteristics: Lower margins, higher asset turnover, capital intensive
    """
    print_section("DEMO 2: Hardware Technology Company")

    financial_ratios = {
        "gross_margin": 19.5,
        "ebit_margin": 9.0,
        "roic": 16.5,
        "asset_turnover": 1.35,
        "revenue_growth": 18.0
    }

    balance_sheet = {
        "total_assets": 2500000000000,
        "fixed_assets": 950000000000,
        "cash_and_equivalents": 180000000000,
        "liabilities_total": 1200000000000,
        "equity_total": 1300000000000
    }

    income_statement = {
        "revenue": 3375000000000,
        "net_revenue": 3200000000000,
        "operating_expenses": 550000000000,
        "gross_profit": 658125000000,
        "operating_profit": 303750000000,
        "net_profit": 227812500000,
        "corporate_income_tax": 75937500000
    }

    result = analyze_technology_company(financial_ratios, balance_sheet, income_statement)

    print("\nCompany Profile: Hardware/Device Manufacturer")
    print("Characteristics: Lower margins, high volume, capital intensive\n")

    print("Key Metrics:")
    print_metric(result['metrics']['gross_margin'])
    print_metric(result['metrics']['asset_light_ratio'])
    print_metric(result['metrics']['asset_turnover'])
    print_metric(result['metrics']['roic'])

    print(f"\nTech Scalability Score: {result['scalability_score']['overall_score_formatted']}")
    print(f"Overall Rating: {result['scalability_score']['overall_rating']}\n")

    print("Analysis Summary:")
    for point in result['summary']:
        print(f"  • {point}")


def demo_it_services():
    """
    Demo: IT Services/System Integration
    Characteristics: Moderate margins, labor-intensive, steady growth
    """
    print_section("DEMO 3: IT Services & System Integration")

    financial_ratios = {
        "gross_margin": 28.0,
        "ebit_margin": 12.0,
        "roic": 19.0,
        "asset_turnover": 0.85,
        "revenue_growth": 15.0
    }

    balance_sheet = {
        "total_assets": 450000000000,
        "fixed_assets": 120000000000,
        "cash_and_equivalents": 95000000000,
        "liabilities_total": 180000000000,
        "equity_total": 270000000000
    }

    income_statement = {
        "revenue": 382500000000,
        "net_revenue": 365000000000,
        "operating_expenses": 110000000000,
        "gross_profit": 107100000000,
        "operating_profit": 45900000000,
        "net_profit": 35700000000,
        "corporate_income_tax": 10200000000
    }

    result = analyze_technology_company(financial_ratios, balance_sheet, income_statement)

    print("\nCompany Profile: IT Services & System Integration")
    print("Characteristics: Moderate margins, labor-intensive, project-based\n")

    print("Key Metrics:")
    print_metric(result['metrics']['gross_margin'])
    print_metric(result['metrics']['employee_productivity'])
    print_metric(result['metrics']['operating_margin'])
    print_metric(result['metrics']['revenue_growth'])

    print(f"\nTech Scalability Score: {result['scalability_score']['overall_score_formatted']}")
    print(f"Overall Rating: {result['scalability_score']['overall_rating']}\n")

    print("Analysis Summary:")
    for point in result['summary']:
        print(f"  • {point}")


def demo_scalability_comparison():
    """
    Demo: Compare scalability across different tech sub-sectors
    """
    print_section("DEMO 4: Scalability Score Comparison")

    companies = [
        {
            "name": "Software/SaaS",
            "ratios": {"gross_margin": 72, "ebit_margin": 28, "roic": 32, "asset_turnover": 0.65, "revenue_growth": 45},
            "bs": {"total_assets": 150000000000, "fixed_assets": 18000000000, "cash_and_equivalents": 85000000000, "liabilities_total": 25000000000, "equity_total": 125000000000},
            "is": {"revenue": 97500000000, "operating_expenses": 35000000000, "gross_profit": 70200000000, "operating_profit": 27300000000}
        },
        {
            "name": "Hardware",
            "ratios": {"gross_margin": 19.5, "ebit_margin": 9, "roic": 16.5, "asset_turnover": 1.35, "revenue_growth": 18},
            "bs": {"total_assets": 2500000000000, "fixed_assets": 950000000000, "cash_and_equivalents": 180000000000, "liabilities_total": 1200000000000, "equity_total": 1300000000000},
            "is": {"revenue": 3375000000000, "operating_expenses": 550000000000, "gross_profit": 658125000000, "operating_profit": 303750000000}
        },
        {
            "name": "IT Services",
            "ratios": {"gross_margin": 28, "ebit_margin": 12, "roic": 19, "asset_turnover": 0.85, "revenue_growth": 15},
            "bs": {"total_assets": 450000000000, "fixed_assets": 120000000000, "cash_and_equivalents": 95000000000, "liabilities_total": 180000000000, "equity_total": 270000000000},
            "is": {"revenue": 382500000000, "operating_expenses": 110000000000, "gross_profit": 107100000000, "operating_profit": 45900000000}
        }
    ]

    print("\nScalability Score Comparison Across Tech Sub-Sectors:\n")
    print(f"{'Company Type':<20} {'Score':<12} {'Rating':<30}")
    print("-" * 80)

    for company in companies:
        result = analyze_technology_company(company['ratios'], company['bs'], company['is'])
        score = result['scalability_score']['overall_score_formatted']
        rating = result['scalability_score']['overall_rating']
        print(f"{company['name']:<20} {score:<12} {rating:<30}")

    print("\nKey Insights:")
    print("  • Software/SaaS companies score highest due to asset-light model and high margins")
    print("  • Hardware companies have lower scores but can achieve high turnover")
    print("  • IT services fall in the middle with steady but moderate growth")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  TECHNOLOGY ANALYSIS MODULE - COMPREHENSIVE DEMONSTRATION")
    print("=" * 80)
    print("\nThis demo showcases technology company analysis across different sub-sectors")
    print("in the Vietnamese market, highlighting industry-specific metrics and patterns.")

    demo_software_company()
    demo_hardware_company()
    demo_it_services()
    demo_scalability_comparison()

    print("\n" + "=" * 80)
    print("  DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("\nFor more information, see: TECHNOLOGY_ANALYSIS_README.md")
    print("Module location: webapp/analysis/technology_analysis.py\n")
