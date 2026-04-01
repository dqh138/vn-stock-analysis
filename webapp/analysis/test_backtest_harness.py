import pandas as pd

from webapp.analysis.backtest_harness import _compute_quality_value_signal, _spearman_rank_correlation


def test_spearman_rank_correlation_basic():
    x = [1, 2, 3, 4, 5]
    y = [10, 20, 30, 40, 50]
    corr = _spearman_rank_correlation(x, y)
    assert corr is not None
    assert corr > 0.99


def test_quality_value_signal_coverage_gate():
    df = pd.DataFrame(
        {
            "symbol": ["A", "B", "C"],
            "year": [2024, 2024, 2024],
            "roe": [0.2, 0.1, None],
            "net_profit_margin": [0.15, None, None],
            "debt_to_equity": [0.5, 1.0, 0.8],
            # Make C fail coverage: invalid/missing valuations will be nulled before ranking
            "price_to_earnings": [10.0, 12.0, -1.0],
            "price_to_book": [1.5, 2.0, None],
        }
    )
    out = _compute_quality_value_signal(df, min_coverage=3)
    # A: has enough components, should have signal
    assert out.loc[out["symbol"] == "A", "signal"].notna().iloc[0]
    # C: too many missing components, should be gated out
    assert out.loc[out["symbol"] == "C", "signal"].isna().iloc[0]
