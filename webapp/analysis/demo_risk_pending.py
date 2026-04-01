#!/usr/bin/env python3
"""
Real-World Demonstration: Risk Analysis with PENDING Mechanism

This script demonstrates how the PENDING mechanism works in practice,
simulating the gradual filling of the stock_price_history table.

Author: Risk Analysis Engine
Version: 2.0.0 - Phase 6: PENDING Mechanism
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from risk_analysis import RiskAnalysisEngine


def generate_realistic_price_data(symbol: str, days: int, start_price: float) -> List[Dict[str, Any]]:
    """Generate realistic price history for a stock"""
    prices = []
    base_date = datetime.now() - timedelta(days=days)

    # Random walk with drift and volatility
    current_price = start_price
    daily_vol = 0.02  # 2% daily volatility

    for i in range(days):
        # Add some trend
        if i < days * 0.3:
            drift = 0.001  # Uptrend
        elif i < days * 0.6:
            drift = -0.0005  # Downtrend
        else:
            drift = 0.0002  # Slight uptrend

        # Random price change
        change_pct = random.gauss(drift, daily_vol)
        current_price = current_price * (1 + change_pct)

        # Generate OHLC
        high = current_price * random.uniform(1.0, 1.015)
        low = current_price * random.uniform(0.985, 1.0)
        close = current_price

        prices.append({
            'time': (base_date + timedelta(days=i)).strftime('%Y-%m-%d'),
            'open': round(current_price * random.uniform(0.995, 1.005), 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': random.randint(500000, 5000000)
        })

    return prices


def display_metric_status(metric_name: str, metric_data: Dict[str, Any], indent: int = 2):
    """Display a metric's status in a user-friendly format"""
    prefix = " " * indent
    status = metric_data.get('status', 'UNKNOWN')

    if status == 'OK':
        value = metric_data.get('value', 'N/A')
        rating = metric_data.get('rating', '')
        print(f"{prefix}✓ {metric_name:20} | {value:>8} | {rating}")
    elif status.startswith('PENDING'):
        have = metric_data.get('have', 0)
        need = metric_data.get('need', 0)
        progress = int((have / need) * 100) if need > 0 else 0
        print(f"{prefix}○ {metric_name:20} | {have:3}/{need:<3} days | {progress:3}% complete")
    elif status == 'ERROR':
        error_msg = metric_data.get('message', 'Unknown error')
        print(f"{prefix}✗ {metric_name:20} | ERROR: {error_msg}")


def simulate_data_filling_process():
    """Simulate the gradual filling of stock_price_history table"""
    print("\n" + "="*80)
    print("SIMULATION: Gradual Filling of stock_price_history Table")
    print("="*80)
    print("\nSimulating a newly listed stock with price data being filled over time...")
    print()

    # Generate full dataset upfront
    symbol = "ABC"
    full_price_history = generate_realistic_price_data(symbol, 30, 50.0)
    full_market_history = generate_realistic_price_data("VNINDEX", 50, 1200.0)

    # Simulate day-by-day data filling
    checkpoints = [3, 5, 8, 10, 15, 20, 25, 30]

    for days in checkpoints:
        print(f"\n{'─'*80}")
        print(f"DAY {days}: Price history has {days} trading days")
        print(f"{'─'*80}")

        # Slice data to simulate current state
        current_price_history = full_price_history[:days]
        current_market_history = full_market_history[:max(20, days)]

        # Create engine and calculate
        engine = RiskAnalysisEngine(
            price_history=current_price_history,
            market_history=current_market_history,
            risk_free_rate=0.05
        )

        result = engine.calculate_all_risk_metrics()

        # Display overall status
        status_emoji = {
            'OK': '✓',
            'PARTIAL': '◐',
            'MOSTLY_PENDING': '○',
            'PENDING': '○'
        }.get(result['overall_status'], '?')

        print(f"\nOverall Status: {status_emoji} {result['overall_status']}")
        print(f"Coverage: {result['coverage_pct']}% ({result['ok_metrics']}/{result['total_metrics']} metrics)")

        # Display individual metrics
        print(f"\n{'Metric':<22} | {'Value/Progress':<15} | {'Info'}")
        print(f"{'-'*22}+-{'-'*15}+-{'-'*30}")

        for metric_name, metric_data in result['metrics'].items():
            display_metric_status(metric_name, metric_data)

        # Show data quality
        dq = result['data_quality']
        print(f"\nData Quality:")
        print(f"  Price days: {dq['price_days']}")
        print(f"  Return days: {dq['return_days']}")
        print(f"  Market data: {'Yes' if dq['has_market_data'] else 'No'}")

        # Highlight transitions
        print(f"\nTransitions:")
        transitions = []
        for metric_name, metric_data in result['metrics'].items():
            if metric_data['status'] == 'OK':
                transitions.append(metric_name)
        if transitions:
            print(f"  ✓ Metrics now available: {', '.join(transitions)}")
        else:
            print(f"  ○ No new metrics (still gathering data)")


def demonstrate_frontend_integration():
    """Demonstrate how frontend would display PENDING status"""
    print("\n" + "="*80)
    print("FRONTEND INTEGRATION DEMONSTRATION")
    print("="*80)

    # Scenario: Stock with 15 days of data
    price_history = generate_realistic_price_data("VCB", 15, 85.0)
    market_history = generate_realistic_price_data("VNINDEX", 50, 1200.0)

    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=0.05
    )

    result = engine.calculate_all_risk_metrics()

    print("\n" + "─"*80)
    print("REACT COMPONENT EXAMPLE")
    print("─"*80)

    print("""
function RiskMetricsPanel({ symbol }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchRiskMetrics(symbol).then(result => {
            setData(result);
            setLoading(false);
        });
    }, [symbol]);

    if (loading) return <Spinner />;

    return (
        <div className="risk-panel">
            {/* Overall Status Badge */}
            <StatusBadge
                status={data.overall_status}
                coverage={data.coverage_pct}
            />

            {/* Metrics Grid */}
            <div className="metrics-grid">
                {data.metrics.map(([name, metric]) => (
                    <MetricCard
                        key={name}
                        name={name}
                        metric={metric}
                    />
                ))}
            </div>
        </div>
    );
}

function StatusBadge({ status, coverage }) {
    const config = {
        'OK': { color: 'green', icon: '✓', text: 'Đầy đủ' },
        'PARTIAL': { color: 'yellow', icon: '◐', text: 'Một phần' },
        'MOSTLY_PENDING': { color: 'orange', icon: '○', text: 'Đang chờ' },
        'PENDING': { color: 'gray', icon: '○', text: 'Chưa có dữ liệu' }
    };

    const { color, icon, text } = config[status];

    return (
        <div className={`status-badge ${color}`}>
            <span className="icon">{icon}</span>
            <span className="text">{text}</span>
            <span className="coverage">{coverage}% hoàn thành</span>
        </div>
    );
}

function MetricCard({ name, metric }) {
    switch (metric.status) {
        case 'OK':
            return (
                <div className="metric-card ok">
                    <h3>{metric.metric}</h3>
                    <div className="value">{metric.value}</div>
                    <div className="rating">{metric.rating}</div>
                    <div className="details">
                        <span>N: {metric.n}</span>
                        <span>Method: {metric.method}</span>
                    </div>
                </div>
            );

        case 'PENDING_PRICE_DATA':
            const progress = (metric.have / metric.need) * 100;
            return (
                <div className="metric-card pending">
                    <h3>{metric.metric}</h3>
                    <div className="message">Đang chờ dữ liệu giá</div>
                    <div className="progress-bar">
                        <div style={{ width: `${progress}%` }} />
                    </div>
                    <div className="progress-text">
                        {metric.have} / {metric.need} ngày ({progress.toFixed(0)}%)
                    </div>
                </div>
            );

        case 'PENDING_MARKET_DATA':
            return (
                <div className="metric-card pending">
                    <h3>{metric.metric}</h3>
                    <div className="message">Đang chờ dữ liệu thị trường</div>
                    <div className="hint">Cần dữ liệu VNINDEX</div>
                </div>
            );

        default:
            return <div className="metric-card error">Lỗi</div>;
    }
}
    """)

    print("\n" + "─"*80)
    print("SAMPLE OUTPUT FOR CURRENT DATA:")
    print("─"*80)

    print(f"\nOverall Status: {result['overall_status']}")
    print(f"Coverage: {result['coverage_pct']}%")
    print()

    print("Metrics:")
    for metric_name, metric_data in result['metrics'].items():
        print(f"\n  {metric_name}:")
        print(f"    Status: {metric_data['status']}")
        if metric_data['status'] == 'OK':
            print(f"    Value: {metric_data.get('value', 'N/A')}")
            print(f"    Rating: {metric_data.get('rating', 'N/A')}")
        elif metric_data['status'].startswith('PENDING'):
            print(f"    Progress: {metric_data.get('have', 0)}/{metric_data.get('need', 0)} days")
            print(f"    Message: {metric_data.get('message', '')}")


def demonstrate_error_handling():
    """Demonstrate error handling"""
    print("\n" + "="*80)
    print("ERROR HANDLING DEMONSTRATION")
    print("="*80)

    # Scenario 1: Constant prices (zero volatility)
    print("\nScenario 1: Constant Prices (Zero Volatility)")
    print("─"*80)

    constant_prices = [
        {'time': '2026-02-01', 'close': 100.0, 'high': 100.0, 'low': 100.0},
        {'time': '2026-02-02', 'close': 100.0, 'high': 100.0, 'low': 100.0},
        {'time': '2026-02-03', 'close': 100.0, 'high': 100.0, 'low': 100.0},
    ] * 10  # 30 days of constant prices

    engine = RiskAnalysisEngine(
        price_history=constant_prices,
        market_history=[],
        risk_free_rate=0.05
    )

    sharpe = engine.calculate_sharpe_ratio()
    print(f"Sharpe Ratio Status: {sharpe['status']}")
    print(f"Error: {sharpe.get('error', 'N/A')}")
    print(f"Message: {sharpe.get('message', 'N/A')}")

    # Scenario 2: Invalid price data
    print("\n\nScenario 2: Invalid Price Data")
    print("─"*80)

    invalid_prices = [
        {'time': '2026-02-01', 'close': 0, 'high': 0, 'low': 0},
        {'time': '2026-02-02', 'close': 0, 'high': 0, 'low': 0},
    ]

    engine = RiskAnalysisEngine(
        price_history=invalid_prices,
        market_history=[],
        risk_free_rate=0.05
    )

    mdd = engine.calculate_max_drawdown()
    print(f"Max Drawdown Status: {mdd['status']}")
    print(f"Error: {mdd.get('error', 'N/A')}")
    print(f"Message: {mdd.get('message', 'N/A')}")


def main():
    """Run all demonstrations"""
    print("\n" + "="*80)
    print("RISK ANALYSIS - PENDING MECHANISM REAL-WORLD DEMONSTRATION")
    print("="*80)
    print(f"Demo Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    simulate_data_filling_process()
    demonstrate_frontend_integration()
    demonstrate_error_handling()

    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nKey Takeaways:")
    print("  ✓ Metrics automatically transition PENDING → OK as data fills")
    print("  ✓ Clear status messaging in Vietnamese for users")
    print("  ✓ Frontend can display progress bars for pending metrics")
    print("  ✓ Error handling prevents crashes with invalid data")
    print("  ✓ No code changes needed when data becomes available")
    print()


if __name__ == "__main__":
    main()
