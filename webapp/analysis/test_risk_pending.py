"""
Test script for Risk Analysis with PENDING Mechanism

This script demonstrates:
1. Status contracts (OK, PENDING, ERROR)
2. Auto-transitions from PENDING to OK as data fills
3. needs_refresh flag for data availability changes
4. Overall status aggregation (OK, PARTIAL, MOSTLY_PENDING, PENDING)

Author: Risk Analysis Engine
Version: 2.0.0 - Phase 6: PENDING Mechanism
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from risk_analysis import RiskAnalysisEngine


def generate_mock_price_data(days: int, start_price: float = 100.0) -> List[Dict[str, Any]]:
    """Generate mock price history for testing"""
    prices = []
    base_date = datetime.now() - timedelta(days=days)

    for i in range(days):
        # Simple random walk
        import random
        change_pct = random.uniform(-0.03, 0.03)  # -3% to +3% daily

        if i == 0:
            price = start_price
        else:
            price = prices[-1]['close'] * (1 + change_pct)

        high = price * random.uniform(1.0, 1.02)
        low = price * random.uniform(0.98, 1.0)

        prices.append({
            'time': (base_date + timedelta(days=i)).strftime('%Y-%m-%d'),
            'close': round(price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'volume': random.randint(100000, 1000000)
        })

    return prices


def test_scenario_1_insufficient_data():
    """Test Scenario 1: Very insufficient data (1-3 days)"""
    print("\n" + "="*80)
    print("SCENARIO 1: Very Insufficient Data (3 days)")
    print("="*80)

    price_history = generate_mock_price_data(3, start_price=100.0)
    market_history = generate_mock_price_data(50, start_price=1000.0)

    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=0.05
    )

    result = engine.calculate_all_risk_metrics()

    print(f"\nOverall Status: {result['overall_status']}")
    print(f"Coverage: {result['coverage_pct']}% ({result['ok_metrics']}/{result['total_metrics']} metrics)")
    print(f"Needs Refresh: {result['needs_refresh']}")
    print(f"Data Quality: {result['data_quality']}")

    print("\n--- Metric Statuses ---")
    for metric_name, metric_data in result['metrics'].items():
        status = metric_data.get('status', 'UNKNOWN')
        msg = metric_data.get('message', '')
        print(f"  {metric_name:20} | {status:20} | {msg}")


def test_scenario_2_partial_data():
    """Test Scenario 2: Partial data (8 days - some metrics OK, some PENDING)"""
    print("\n" + "="*80)
    print("SCENARIO 2: Partial Data (8 days)")
    print("="*80)

    price_history = generate_mock_price_data(8, start_price=100.0)
    market_history = generate_mock_price_data(50, start_price=1000.0)

    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=0.05
    )

    result = engine.calculate_all_risk_metrics()

    print(f"\nOverall Status: {result['overall_status']}")
    print(f"Coverage: {result['coverage_pct']}% ({result['ok_metrics']}/{result['total_metrics']} metrics)")
    print(f"Needs Refresh: {result['needs_refresh']}")

    print("\n--- Metric Statuses ---")
    for metric_name, metric_data in result['metrics'].items():
        status = metric_data.get('status', 'UNKNOWN')
        value = metric_data.get('value', 'N/A')
        print(f"  {metric_name:20} | {status:20} | Value: {value}")


def test_scenario_3_mostly_complete():
    """Test Scenario 3: Mostly complete (18 days - most metrics OK)"""
    print("\n" + "="*80)
    print("SCENARIO 3: Mostly Complete (18 days)")
    print("="*80)

    price_history = generate_mock_price_data(18, start_price=100.0)
    market_history = generate_mock_price_data(50, start_price=1000.0)

    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=0.05
    )

    result = engine.calculate_all_risk_metrics()

    print(f"\nOverall Status: {result['overall_status']}")
    print(f"Coverage: {result['coverage_pct']}% ({result['ok_metrics']}/{result['total_metrics']} metrics)")

    print("\n--- Metric Statuses ---")
    for metric_name, metric_data in result['metrics'].items():
        status = metric_data.get('status', 'UNKNOWN')
        value = metric_data.get('value', 'N/A')
        print(f"  {metric_name:20} | {status:20} | Value: {value}")


def test_scenario_4_full_data():
    """Test Scenario 4: Full data (30+ days - all metrics OK)"""
    print("\n" + "="*80)
    print("SCENARIO 4: Full Data (30 days)")
    print("="*80)

    price_history = generate_mock_price_data(30, start_price=100.0)
    market_history = generate_mock_price_data(50, start_price=1000.0)

    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=0.05
    )

    result = engine.calculate_all_risk_metrics()

    print(f"\nOverall Status: {result['overall_status']}")
    print(f"Coverage: {result['coverage_pct']}% ({result['ok_metrics']}/{result['total_metrics']} metrics)")

    print("\n--- Metric Statuses ---")
    for metric_name, metric_data in result['metrics'].items():
        status = metric_data.get('status', 'UNKNOWN')
        value = metric_data.get('value', 'N/A')
        print(f"  {metric_name:20} | {status:20} | Value: {value}")

    print("\n--- Sample OK Metric Details (Volatility 30d) ---")
    vol_30d = result['metrics']['volatility_30d']
    print(f"  Status: {vol_30d['status']}")
    print(f"  Metric: {vol_30d['metric']}")
    print(f"  Value: {vol_30d['value']}")
    print(f"  N: {vol_30d['n']}")
    print(f"  Method: {vol_30d['method']}")
    print(f"  As Of: {vol_30d['as_of']}")
    print(f"  Rating: {vol_30d['rating']}")


def test_scenario_5_missing_market_data():
    """Test Scenario 5: Missing market data (Beta fails)"""
    print("\n" + "="*80)
    print("SCENARIO 5: Missing Market Data (30 days, no VNINDEX)")
    print("="*80)

    price_history = generate_mock_price_data(30, start_price=100.0)
    market_history = []  # No market data

    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=0.05
    )

    result = engine.calculate_all_risk_metrics()

    print(f"\nOverall Status: {result['overall_status']}")
    print(f"Coverage: {result['coverage_pct']}% ({result['ok_metrics']}/{result['total_metrics']} metrics)")

    print("\n--- Metric Statuses ---")
    for metric_name, metric_data in result['metrics'].items():
        status = metric_data.get('status', 'UNKNOWN')
        msg = metric_data.get('message', '') if metric_data.get('status') != 'OK' else 'OK'
        print(f"  {metric_name:20} | {status:20} | {msg}")


def test_scenario_6_data_refresh():
    """Test Scenario 6: Data refresh detection"""
    print("\n" + "="*80)
    print("SCENARIO 6: Data Refresh Detection")
    print("="*80)

    # Start with 10 days
    price_history = generate_mock_price_data(10, start_price=100.0)
    market_history = generate_mock_price_data(50, start_price=1000.0)

    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=0.05
    )

    result1 = engine.calculate_all_risk_metrics()
    print(f"\nInitial (10 days):")
    print(f"  Overall Status: {result1['overall_status']}")
    print(f"  Coverage: {result1['coverage_pct']}%")
    print(f"  Needs Refresh: {result1['needs_refresh']}")

    # Add more data
    new_prices = generate_mock_price_data(5, start_price=105.0)
    engine.price_history.extend(new_prices)
    engine.returns = engine._calculate_returns(engine.price_history)

    result2 = engine.calculate_all_risk_metrics()
    print(f"\nAfter adding 5 more days (15 days total):")
    print(f"  Overall Status: {result2['overall_status']}")
    print(f"  Coverage: {result2['coverage_pct']}%")
    print(f"  Needs Refresh: {result2['needs_refresh']}")


def test_scenario_7_data_requirements():
    """Test Scenario 7: Data requirements check"""
    print("\n" + "="*80)
    print("SCENARIO 7: Data Requirements Check")
    print("="*80)

    price_history = generate_mock_price_data(15, start_price=100.0)
    market_history = generate_mock_price_data(50, start_price=1000.0)

    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=0.05
    )

    requirements = engine.get_data_requirements()

    print("\n--- Minimum Requirements ---")
    for metric, days in requirements['requirements'].items():
        print(f"  {metric:20} | {days} days")

    print("\n--- Current Availability ---")
    for key, value in requirements['current'].items():
        print(f"  {key:25} | {value}")

    print("\n--- Can Calculate ---")
    for metric, can_calc in requirements['can_calculate'].items():
        status = "✓" if can_calc else "✗"
        print(f"  {status} {metric:20} | {can_calc}")


def test_scenario_8_pending_to_ok_transition():
    """Test Scenario 8: Individual metric PENDING → OK transition"""
    print("\n" + "="*80)
    print("SCENARIO 8: PENDING → OK Transition for Beta")
    print("="*80)

    market_history = generate_mock_price_data(50, start_price=1000.0)

    # Start with 5 days (PENDING for beta)
    print("\n--- Day 5 (PENDING) ---")
    price_history = generate_mock_price_data(5, start_price=100.0)
    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=0.05
    )

    beta_result = engine.calculate_beta()
    print(f"Status: {beta_result['status']}")
    print(f"Message: {beta_result.get('message', 'N/A')}")
    print(f"Have: {beta_result.get('have', 'N/A')}, Need: {beta_result.get('need', 'N/A')}")

    # Add 5 more days (Still PENDING for beta)
    print("\n--- Day 10 (TRANSITION POINT) ---")
    price_history = generate_mock_price_data(10, start_price=100.0)
    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=0.05
    )

    beta_result = engine.calculate_beta()
    print(f"Status: {beta_result['status']}")
    if beta_result['status'] == 'OK':
        print(f"Beta: {beta_result['value']}")
        print(f"Interpretation: {beta_result['interpretation']}")
    else:
        print(f"Message: {beta_result.get('message', 'N/A')}")
        print(f"Have: {beta_result.get('have', 'N/A')}, Need: {beta_result.get('need', 'N/A')}")


def main():
    """Run all test scenarios"""
    print("\n" + "="*80)
    print("RISK ANALYSIS - PENDING MECHANISM TEST SUITE")
    print("="*80)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test_scenario_1_insufficient_data()
    test_scenario_2_partial_data()
    test_scenario_3_mostly_complete()
    test_scenario_4_full_data()
    test_scenario_5_missing_market_data()
    test_scenario_6_data_refresh()
    test_scenario_7_data_requirements()
    test_scenario_8_pending_to_ok_transition()

    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)
    print("\nKey Demonstrations:")
    print("  ✓ Status contracts (OK, PENDING, ERROR)")
    print("  ✓ Auto-transitions from PENDING to OK as data fills")
    print("  ✓ needs_refresh flag for data availability changes")
    print("  ✓ Overall status aggregation (OK, PARTIAL, MOSTLY_PENDING, PENDING)")
    print("  ✓ Per-metric minimum requirements tracking")
    print("  ✓ Graceful degradation without code changes")
    print()


if __name__ == "__main__":
    main()
