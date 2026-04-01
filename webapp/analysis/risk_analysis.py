"""
Risk Analysis Engine - Phân tích rủi ro cổ phiếu

Module này cung cấp các phương pháp phân tích rủi ro dựa trên lịch sử giá:
- Volatility (Độ biến động): 30-day, 90-day, 1-year
- Beta: So với VNINDEX
- VaR (Value at Risk): 95%, 99%
- Sharpe Ratio
- Maximum Drawdown

Features:
- Status contracts (OK, PENDING, ERROR) for graceful degradation
- Auto-transitions from PENDING to OK as data fills
- needs_refresh flag for data availability changes

Author: Risk Analysis Engine
Version: 2.0.0 - Phase 6: PENDING Mechanism
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import math


class RiskAnalysisEngine:
    """
    Engine phân tích rủi ro cổ phiếu

    Calculations based on historical price data from stock_price_history table.
    Returns status contracts for graceful degradation when data is insufficient.
    """

    # Minimum data requirements for each metric
    MIN_DAYS = {
        'volatility': 5,
        'beta': 10,
        'var': 20,
        'sharpe': 20,
        'sortino': 20,
        'expected_shortfall': 20,
        'calmar': 20,
        'max_drawdown': 2,
    }

    def __init__(self, price_history: List[Dict[str, Any]],
                 market_history: Optional[List[Dict[str, Any]]] = None,
                 risk_free_rate: float = 0.05):
        """
        Khởi tạo Risk Analysis Engine

        Args:
            price_history: List of daily price data dicts with keys:
                - 'time': date string (YYYY-MM-DD)
                - 'close': closing price
                - 'high': high price
                - 'low': low price
            market_history: Optional market index (VNINDEX) history for beta calculation
            risk_free_rate: Annual risk-free rate (default 5% for Vietnam)
        """
        self.price_history = price_history or []
        self.market_history = market_history or []
        self.risk_free_rate = risk_free_rate

        # Deterministic as-of date (prefer latest available price date)
        self.as_of = self._infer_as_of(self.price_history)

        # Pre-calculate daily returns
        self.returns = self._calculate_returns(self.price_history)
        self.market_returns = self._calculate_returns(self.market_history) if self.market_history else []

        # Track last data availability for needs_refresh
        self._last_data_count = len(self.price_history)
        self._last_market_count = len(self.market_history)

    def _infer_as_of(self, price_data: List[Dict[str, Any]]) -> str:
        """
        Infer as-of date deterministically from the latest available price point.

        Uses lexicographic max on YYYY-MM-DD strings (valid for ISO dates).
        Falls back to today's date if missing.
        """
        dates = [d.get("time") for d in (price_data or []) if d.get("time")]
        if dates:
            try:
                return str(max(dates))
            except Exception:
                pass
        return datetime.now().strftime("%Y-%m-%d")

    def _calculate_returns(self, price_data: List[Dict]) -> List[float]:
        """Calculate daily log returns from price data."""
        if len(price_data) < 2:
            return []

        # Sort by date ascending
        sorted_data = sorted(price_data, key=lambda x: x.get('time', ''))
        returns = []

        for i in range(1, len(sorted_data)):
            prev_close = sorted_data[i-1].get('close', 0)
            curr_close = sorted_data[i].get('close', 0)

            if prev_close > 0 and curr_close > 0:
                # Log return: ln(P_t / P_{t-1})
                log_return = math.log(curr_close / prev_close)
                returns.append(log_return)

        return returns

    def _get_returns_for_period(self, days: int) -> List[float]:
        """Get returns for the last N trading days."""
        if len(self.returns) <= days:
            return self.returns
        return self.returns[-days:]

    def calculate_volatility(self, days: Optional[int] = None) -> Dict[str, Any]:
        """
        Tính độ biến động (Volatility)

        Args:
            days: Số ngày giao dịch (None = all available)

        Returns:
            Dict containing daily and annualized volatility with status contract
        """
        returns = self._get_returns_for_period(days) if days else self.returns
        min_required = self.MIN_DAYS['volatility']
        current_time = self.as_of

        # Check minimum data requirement
        if len(returns) < min_required:
            return {
                "status": "PENDING_PRICE_DATA",
                "metric": "volatility",
                "have": len(returns),
                "need": min_required,
                "window_days": days,
                "as_of": current_time,
                "message": f"Cần ít nhất {min_required} ngày giao dịch để tính độ biến động (có {len(returns)} ngày)"
            }

        # Calculate standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        daily_vol = math.sqrt(variance)

        # Annualize (assuming 252 trading days per year)
        annualized_vol = daily_vol * math.sqrt(252)

        # Rating based on annualized volatility
        if annualized_vol < 0.20:  # < 20%
            rating = 'Thấp'
            color = 'green'
        elif annualized_vol < 0.35:  # 20-35%
            rating = 'Trung bình'
            color = 'yellow'
        elif annualized_vol < 0.50:  # 35-50%
            rating = 'Cao'
            color = 'orange'
        else:
            rating = 'Rất cao'
            color = 'red'

        return {
            "status": "OK",
            "metric": "volatility",
            "value": round(annualized_vol * 100, 2),
            "n": len(returns),
            "method": "log_returns_std",
            "as_of": current_time,
            'daily_volatility': round(daily_vol, 4),
            'daily_volatility_pct': round(daily_vol * 100, 2),
            'annualized_volatility': round(annualized_vol, 4),
            'annualized_volatility_pct': round(annualized_vol * 100, 2),
            'trading_days': len(returns),
            'period_days': days,
            'rating': rating,
            'color': color
        }

    def calculate_beta(self) -> Dict[str, Any]:
        """
        Tính Beta so với VNINDEX

        Beta = Cov(Stock, Market) / Var(Market)

        Returns:
            Dict containing beta and interpretation with status contract
        """
        min_required = self.MIN_DAYS['beta']
        current_time = self.as_of

        # Check market data availability
        if not self.market_returns:
            return {
                "status": "PENDING_MARKET_DATA",
                "metric": "beta",
                "have": len(self.returns),
                "need": min_required,
                "as_of": current_time,
                "message": "Cần dữ liệu VNINDEX để tính Beta",
                "missing_data": "VNINDEX"
            }

        # Check minimum stock data
        if len(self.returns) < min_required:
            return {
                "status": "PENDING_PRICE_DATA",
                "metric": "beta",
                "have": len(self.returns),
                "need": min_required,
                "as_of": current_time,
                "message": f"Cần ít nhất {min_required} ngày giao dịch để tính Beta (có {len(self.returns)} ngày)"
            }

        # Align returns by date intersection
        # Create date-indexed dictionaries (skip first element as returns start from second day)
        stock_by_date = {d['time']: r for d, r in zip(self.price_history[1:], self.returns)}
        market_by_date = {d['time']: r for d, r in zip(self.market_history[1:], self.market_returns)}

        # Find common dates
        common_dates = sorted(set(stock_by_date.keys()) & set(market_by_date.keys()))

        # Check if we have enough common dates
        if len(common_dates) < min_required:
            return {
                "status": "PENDING_PRICE_DATA",
                "metric": "beta",
                "have": len(common_dates),
                "need": min_required,
                "as_of": current_time,
                "message": f"Cần ít nhất {min_required} ngày giao dịch chung để tính Beta (có {len(common_dates)} ngày)"
            }

        # Align returns by date
        aligned_stock = [stock_by_date[d] for d in common_dates]
        aligned_market = [market_by_date[d] for d in common_dates]

        if len(aligned_stock) < min_required:
            return {
                "status": "PENDING_PRICE_DATA",
                "metric": "beta",
                "have": len(aligned_stock),
                "need": min_required,
                "as_of": current_time,
                "message": f"Cần ít nhất {min_required} ngày giao dịch để tính Beta (có {len(aligned_stock)} ngày)"
            }

        # Calculate covariance and variance using aligned returns
        mean_stock = sum(aligned_stock) / len(aligned_stock)
        mean_market = sum(aligned_market) / len(aligned_market)

        covariance = sum((s - mean_stock) * (m - mean_market)
                        for s, m in zip(aligned_stock, aligned_market)) / (len(aligned_stock) - 1)

        market_variance = sum((m - mean_market) ** 2 for m in aligned_market) / (len(aligned_market) - 1)

        # Calculate standard deviations for correlation
        std_stock = math.sqrt(sum((s - mean_stock) ** 2 for s in aligned_stock) / (len(aligned_stock) - 1))
        std_market = math.sqrt(sum((m - mean_market) ** 2 for m in aligned_market) / (len(aligned_market) - 1))

        if market_variance == 0:
            return {
                "status": "ERROR",
                "metric": "beta",
                "as_of": current_time,
                "error": "market_variance_zero",
                "message": "Phương sai thị trường bằng 0"
            }

        beta = covariance / market_variance

        # Calculate correlation: Covariance / (StdDev_Stock * StdDev_Market)
        correlation = covariance / (std_stock * std_market) if std_stock * std_market != 0 else None

        # Interpretation
        if beta < 0:
            rating = 'Phản hướng'
            interpretation = f"Beta âm ({beta:.2f}): Cổ phiếu di chuyển ngược hướng thị trường."
        elif beta < 0.5:
            rating = 'Phòng thủ'
            interpretation = f"Beta thấp ({beta:.2f}): Cổ phiếu ít biến động hơn thị trường, phù hợp nhà đầu tư thận trọng."
        elif beta < 1.0:
            rating = 'Trung bình'
            interpretation = f"Beta trung bình ({beta:.2f}): Cổ phiếu biến động thấp hơn thị trường."
        elif beta < 1.5:
            rating = 'Aggressive'
            interpretation = f"Beta cao ({beta:.2f}): Cổ phiếu biến động mạnh hơn thị trường."
        else:
            rating = 'Rủi ro cao'
            interpretation = f"Beta rất cao ({beta:.2f}): Cổ phiếu biến động rất mạnh, rủi ro cao."

        return {
            "status": "OK",
            "metric": "beta",
            "value": round(beta, 2),
            "n": len(aligned_stock),
            "method": "OLS_log_returns",
            "as_of": current_time,
            'beta': round(beta, 2),
            'correlation': round(correlation, 2) if correlation is not None else None,
            'trading_days': len(aligned_stock),
            'rating': rating,
            'interpretation': interpretation
        }

    def calculate_var(self, confidence: float = 0.95) -> Dict[str, Any]:
        """
        Tính Value at Risk (VaR)

        VaR là mức lỗ tối đa ở một mức tin cậy nhất định trong 1 ngày.

        Args:
            confidence: Mức tin cậy (0.95 hoặc 0.99)

        Returns:
            Dict containing VaR values with status contract
        """
        min_required = self.MIN_DAYS['var']
        current_time = self.as_of

        # Check minimum data requirement
        if len(self.returns) < min_required:
            return {
                "status": "PENDING_PRICE_DATA",
                "metric": "var",
                "have": len(self.returns),
                "need": min_required,
                "as_of": current_time,
                "message": f"Cần ít nhất {min_required} ngày giao dịch để tính VaR (có {len(self.returns)} ngày)"
            }

        # Sort returns (ascending: worst losses first)
        sorted_returns = sorted(self.returns)
        n = len(sorted_returns)

        def percentile_value(p: float) -> Optional[float]:
            """
            Numpy-style percentile (type-7) with linear interpolation.
            Matches the project's benchmark percentile method for consistency.
            """
            if not sorted_returns:
                return None
            if n == 1:
                return sorted_returns[0]

            index = (p / 100.0) * (n - 1)
            lower = int(index)
            upper = min(lower + 1, n - 1)
            frac = index - lower
            if lower == upper:
                return sorted_returns[lower]
            return sorted_returns[lower] + frac * (sorted_returns[upper] - sorted_returns[lower])

        # Loss-tail percentiles (e.g., 5% for 95% VaR)
        p_loss = max(0.0, min(100.0, (1.0 - float(confidence)) * 100.0))

        # VaR is reported as a positive loss magnitude (clip at 0 when tail quantile is >= 0)
        var_conf: Optional[float] = None
        q = percentile_value(p_loss)
        if q is not None:
            var_conf = max(0.0, -q)

        # Also compute standard 95/99 for display
        q95 = percentile_value(5.0)
        q99 = percentile_value(1.0)
        var_95 = max(0.0, -q95) if q95 is not None else None
        var_99 = max(0.0, -q99) if q99 is not None else None

        # Get latest price deterministically (do not assume input is sorted)
        latest_price = 100.0
        if self.price_history:
            try:
                latest_row = max(self.price_history, key=lambda d: str(d.get("time") or ""))
                latest_price = float(latest_row.get("close") or 100.0)
            except (TypeError, ValueError):
                latest_price = float(self.price_history[-1].get("close") or 100.0)

        # Rating based on requested confidence VaR (fallback to 95%)
        basis = var_conf if var_conf is not None else var_95
        if basis is not None and basis < 0.03:  # < 3%
            rating = 'Thấp'
        elif basis is not None and basis < 0.05:  # < 5%
            rating = 'Trung bình'
        elif basis is not None and basis < 0.08:  # < 8%
            rating = 'Cao'
        else:
            rating = 'Rất cao'

        return {
            "status": "OK",
            "metric": "var",
            "value": round(var_conf * 100, 2) if var_conf is not None else None,
            "n": n,
            "method": "historical_percentile",
            "as_of": current_time,
            'var_95': round(var_95, 4) if var_95 is not None else None,
            'var_95_pct': round(var_95 * 100, 2) if var_95 is not None else None,
            'var_99': round(var_99, 4) if var_99 is not None else None,
            'var_99_pct': round(var_99 * 100, 2) if var_99 is not None else None,
            'var_amount': round(var_conf * latest_price, 2) if var_conf is not None else None,
            'var_amount_log_to_simple': round((1 - math.exp(-var_conf)) * latest_price, 2) if var_conf is not None else None,
            'var_95_amount': round(var_95 * latest_price, 2) if var_95 is not None else None,
            'var_95_amount_log_to_simple': round((1 - math.exp(-var_95)) * latest_price, 2) if var_95 is not None else None,
            'var_99_amount': round(var_99 * latest_price, 2) if var_99 is not None else None,
            'var_99_amount_log_to_simple': round((1 - math.exp(-var_99)) * latest_price, 2) if var_99 is not None else None,
            'latest_price': latest_price,
            'confidence_level': confidence,
            'rating': rating,
            'interpretation': (
                f"Với mức tin cậy {confidence*100:.0f}%, khả năng lỗ không vượt quá {var_conf*100:.2f}% trong 1 ngày."
                if var_conf is not None else None
            )
        }

    def calculate_sharpe_ratio(self) -> Dict[str, Any]:
        """
        Tính Sharpe Ratio

        Sharpe Ratio = (Return - Risk Free Rate) / Volatility

        Returns:
            Dict containing Sharpe ratio and interpretation with status contract
        """
        min_required = self.MIN_DAYS['sharpe']
        current_time = self.as_of

        # Check minimum data requirement
        if len(self.returns) < min_required:
            return {
                "status": "PENDING_PRICE_DATA",
                "metric": "sharpe_ratio",
                "have": len(self.returns),
                "need": min_required,
                "as_of": current_time,
                "message": f"Cần ít nhất {min_required} ngày giao dịch để tính Sharpe Ratio (có {len(self.returns)} ngày)"
            }

        # Use log-return consistent Sharpe:
        # - returns are daily log returns
        # - annual log return = mean_log * 252
        # - risk-free converted to log: ln(1 + rf)
        trading_days = len(self.returns)
        mean_log = (sum(self.returns) / trading_days) if trading_days > 0 else 0.0
        annual_log_return = mean_log * 252

        vol_result = self.calculate_volatility()
        annualized_vol = vol_result.get('annualized_volatility', 0)

        if annualized_vol == 0:
            return {
                "status": "ERROR",
                "metric": "sharpe_ratio",
                "as_of": current_time,
                "error": "zero_volatility",
                "message": "Độ biến động bằng 0"
            }

        # Convert risk-free to log form for consistency with log returns
        rf_log = math.log(1 + self.risk_free_rate) if self.risk_free_rate > -1 else 0.0
        excess_return = annual_log_return - rf_log

        sharpe = excess_return / annualized_vol

        # Rating
        if sharpe < 0:
            rating = 'Kém'
            interpretation = f"Sharpe âm ({sharpe:.2f}): Lợi nhuận thấp hơn lãi suất phi rủi ro."
        elif sharpe < 0.5:
            rating = 'Yếu'
            interpretation = f"Sharpe thấp ({sharpe:.2f}): Lợi nhuận điều chỉnh rủi ro chưa hấp dẫn."
        elif sharpe < 1.0:
            rating = 'Trung bình'
            interpretation = f"Sharpe trung bình ({sharpe:.2f}): Hiệu suất tương đối tốt."
        elif sharpe < 2.0:
            rating = 'Tốt'
            interpretation = f"Sharpe tốt ({sharpe:.2f}): Hiệu suất điều chỉnh rủi ro cao."
        else:
            rating = 'Xuất sắc'
            interpretation = f"Sharpe xuất sắc ({sharpe:.2f}): Hiệu suất rất cao."

        return {
            "status": "OK",
            "metric": "sharpe_ratio",
            "value": round(sharpe, 2),
            "n": trading_days,
            "method": "log_return_sharpe",
            "as_of": current_time,
            'sharpe_ratio': round(sharpe, 2),
            # Display as simple annual return for readability
            'annualized_return': round((math.exp(annual_log_return) - 1) * 100, 2),
            'annualized_log_return': round(annual_log_return * 100, 2),
            'annualized_volatility': round(annualized_vol * 100, 2),
            'risk_free_rate': round(self.risk_free_rate * 100, 2),
            'trading_days': trading_days,
            'rating': rating,
            'interpretation': interpretation
        }

    def calculate_sortino_ratio(self, target_return: float = 0.0) -> Dict[str, Any]:
        """
        Tính Sortino Ratio (điều chỉnh rủi ro phía giảm).

        Sortino = (Return - Target) / Downside Deviation

        Notes:
            - Dùng daily log returns để nhất quán với Sharpe.
            - target_return là annual simple rate (ví dụ 0.0 = 0%), quy đổi sang daily log target.
        """
        min_required = self.MIN_DAYS['sortino']
        current_time = self.as_of

        if len(self.returns) < min_required:
            return {
                "status": "PENDING_PRICE_DATA",
                "metric": "sortino_ratio",
                "have": len(self.returns),
                "need": min_required,
                "as_of": current_time,
                "message": f"Cần ít nhất {min_required} ngày giao dịch để tính Sortino Ratio (có {len(self.returns)} ngày)"
            }

        trading_days = len(self.returns)
        mean_log = (sum(self.returns) / trading_days) if trading_days > 0 else 0.0
        annual_log_return = mean_log * 252

        # Convert target (annual simple) to daily log target
        if target_return <= -1:
            target_log_daily = 0.0
        else:
            target_log_daily = math.log(1 + float(target_return)) / 252.0

        downside = []
        for r in self.returns:
            diff = r - target_log_daily
            downside.append(min(0.0, diff))

        if len(downside) < 2:
            return {
                "status": "ERROR",
                "metric": "sortino_ratio",
                "as_of": current_time,
                "error": "insufficient_downside_points",
                "message": "Không đủ dữ liệu để tính downside deviation"
            }

        mean_down = sum(downside) / len(downside)
        var_down = sum((d - mean_down) ** 2 for d in downside) / (len(downside) - 1)
        downside_daily = math.sqrt(var_down)
        downside_annual = downside_daily * math.sqrt(252)

        if downside_annual == 0:
            return {
                "status": "ERROR",
                "metric": "sortino_ratio",
                "as_of": current_time,
                "error": "zero_downside_deviation",
                "message": "Downside deviation bằng 0"
            }

        target_log_annual = target_log_daily * 252
        excess = annual_log_return - target_log_annual
        sortino = excess / downside_annual

        if sortino < 0:
            rating = 'Kém'
        elif sortino < 0.5:
            rating = 'Yếu'
        elif sortino < 1.0:
            rating = 'Trung bình'
        elif sortino < 2.0:
            rating = 'Tốt'
        else:
            rating = 'Xuất sắc'

        return {
            "status": "OK",
            "metric": "sortino_ratio",
            "value": round(sortino, 2),
            "n": trading_days,
            "method": "log_return_sortino",
            "as_of": current_time,
            "sortino_ratio": round(sortino, 2),
            "annualized_return": round((math.exp(annual_log_return) - 1) * 100, 2),
            "downside_deviation_annual_pct": round(downside_annual * 100, 2),
            "target_return_pct": round(float(target_return) * 100, 2),
            "rating": rating,
        }

    def calculate_expected_shortfall(self, confidence: float = 0.95) -> Dict[str, Any]:
        """
        Tính Expected Shortfall (ES / CVaR) theo phương pháp lịch sử.

        ES(conf) = E[Loss | Loss >= VaR(conf)]

        Notes:
            - Uses daily log returns (consistent with VaR implementation).
            - Reported as positive loss magnitude.
        """
        min_required = self.MIN_DAYS['expected_shortfall']
        current_time = self.as_of

        if len(self.returns) < min_required:
            return {
                "status": "PENDING_PRICE_DATA",
                "metric": "expected_shortfall",
                "have": len(self.returns),
                "need": min_required,
                "as_of": current_time,
                "message": f"Cần ít nhất {min_required} ngày giao dịch để tính Expected Shortfall (có {len(self.returns)} ngày)"
            }

        sorted_returns = sorted(self.returns)
        n = len(sorted_returns)

        def percentile_value(p: float) -> Optional[float]:
            if not sorted_returns:
                return None
            if n == 1:
                return sorted_returns[0]
            index = (p / 100.0) * (n - 1)
            lower = int(index)
            upper = min(lower + 1, n - 1)
            frac = index - lower
            if lower == upper:
                return sorted_returns[lower]
            return sorted_returns[lower] + frac * (sorted_returns[upper] - sorted_returns[lower])

        p_loss = max(0.0, min(100.0, (1.0 - float(confidence)) * 100.0))
        q = percentile_value(p_loss)
        if q is None:
            return {
                "status": "ERROR",
                "metric": "expected_shortfall",
                "as_of": current_time,
                "error": "percentile_failed",
                "message": "Không thể tính percentile cho ES"
            }

        var_log = max(0.0, -q)
        threshold_return = -var_log  # <= 0 when var_log >= 0
        tail = [r for r in sorted_returns if r <= threshold_return]

        # If there is no non-positive return in the sample, ES is 0 (no observed loss tail).
        es_log = 0.0
        if tail:
            es_log = max(0.0, -sum(tail) / len(tail))

        latest_price = 100.0
        if self.price_history:
            try:
                latest_row = max(self.price_history, key=lambda d: str(d.get("time") or ""))
                latest_price = float(latest_row.get("close") or 100.0)
            except (TypeError, ValueError):
                latest_price = float(self.price_history[-1].get("close") or 100.0)

        return {
            "status": "OK",
            "metric": "expected_shortfall",
            "value": round(es_log * 100, 2),
            "n": len(self.returns),
            "tail_n": len(tail),
            "method": "historical_es_log_returns",
            "as_of": current_time,
            "confidence_level": confidence,
            "expected_shortfall": round(es_log, 4),
            "expected_shortfall_pct": round(es_log * 100, 2),
            "expected_shortfall_amount": round(es_log * latest_price, 2),
            "expected_shortfall_amount_log_to_simple": round((1 - math.exp(-es_log)) * latest_price, 2),
            "latest_price": latest_price,
        }

    def calculate_calmar_ratio(self) -> Dict[str, Any]:
        """
        Tính Calmar Ratio = Annual Return / Max Drawdown.

        Notes:
            - Annual return is derived from mean daily log return (annualized).
            - Max drawdown is computed from the available window; interpret with window context.
        """
        min_required = self.MIN_DAYS['calmar']
        current_time = self.as_of

        if len(self.returns) < min_required:
            return {
                "status": "PENDING_PRICE_DATA",
                "metric": "calmar_ratio",
                "have": len(self.returns),
                "need": min_required,
                "as_of": current_time,
                "message": f"Cần ít nhất {min_required} ngày giao dịch để tính Calmar Ratio (có {len(self.returns)} ngày)"
            }

        mdd = self.calculate_max_drawdown()
        if mdd.get("status") != "OK":
            return {
                "status": mdd.get("status", "PENDING_PRICE_DATA"),
                "metric": "calmar_ratio",
                "as_of": current_time,
                "message": "Cần Max Drawdown hợp lệ để tính Calmar Ratio",
            }

        max_dd = mdd.get("max_drawdown")
        if max_dd is None or max_dd == 0:
            return {
                "status": "ERROR",
                "metric": "calmar_ratio",
                "as_of": current_time,
                "error": "zero_drawdown",
                "message": "Max drawdown bằng 0"
            }

        trading_days = len(self.returns)
        mean_log = (sum(self.returns) / trading_days) if trading_days > 0 else 0.0
        annual_log_return = mean_log * 252
        annual_simple_return = math.exp(annual_log_return) - 1

        calmar = annual_simple_return / float(max_dd)

        return {
            "status": "OK",
            "metric": "calmar_ratio",
            "value": round(calmar, 2),
            "n": trading_days,
            "method": "annual_return_over_mdd",
            "as_of": current_time,
            "calmar_ratio": round(calmar, 2),
            "annualized_return_pct": round(annual_simple_return * 100, 2),
            "max_drawdown_pct": round(float(max_dd) * 100, 2),
        }

    def calculate_max_drawdown(self) -> Dict[str, Any]:
        """
        Tính Maximum Drawdown

        MDD = (Peak - Trough) / Peak

        Returns:
            Dict containing max drawdown and recovery info with status contract
        """
        min_required = self.MIN_DAYS['max_drawdown']
        current_time = self.as_of

        # Check minimum data requirement
        if len(self.price_history) < min_required:
            return {
                "status": "PENDING_PRICE_DATA",
                "metric": "max_drawdown",
                "have": len(self.price_history),
                "need": min_required,
                "as_of": current_time,
                "message": f"Cần ít nhất {min_required} ngày giao dịch để tính Max Drawdown (có {len(self.price_history)} ngày)"
            }

        # Sort by date ascending
        sorted_data = sorted(self.price_history, key=lambda x: x.get('time', ''))
        prices = [d.get('close', 0) for d in sorted_data]

        if not prices or max(prices) == 0:
            return {
                "status": "ERROR",
                "metric": "max_drawdown",
                "as_of": current_time,
                "error": "invalid_price_data",
                "message": "Dữ liệu giá không hợp lệ"
            }

        peak = prices[0]
        max_dd = 0
        peak_idx = 0
        trough_idx = 0

        for i, price in enumerate(prices):
            if price > peak:
                peak = price
                peak_idx = i

            if peak > 0:
                dd = (peak - price) / peak
                if dd > max_dd:
                    max_dd = dd
                    trough_idx = i

        # Rating
        if max_dd < 0.10:  # < 10%
            rating = 'Thấp'
            color = 'green'
        elif max_dd < 0.20:  # < 20%
            rating = 'Trung bình'
            color = 'yellow'
        elif max_dd < 0.35:  # < 35%
            rating = 'Cao'
            color = 'orange'
        else:
            rating = 'Rất cao'
            color = 'red'

        return {
            "status": "OK",
            "metric": "max_drawdown",
            "value": round(max_dd * 100, 2),
            "n": len(prices),
            "method": "peak_to_trough",
            "as_of": current_time,
            'max_drawdown': round(max_dd, 4),
            'max_drawdown_pct': round(max_dd * 100, 2),
            'peak_price': round(peak, 2),
            'trough_price': round(prices[trough_idx], 2) if trough_idx < len(prices) else None,
            'rating': rating,
            'color': color,
            'interpretation': f"Drawdown tối đa là {max_dd*100:.2f}% từ đỉnh {peak:.2f}."
        }

    def calculate_all_risk_metrics(self) -> Dict[str, Any]:
        """
        Tính tất cả các chỉ số rủi ro với status contract

        Returns:
            Dict containing all risk metrics with overall status and coverage
        """
        current_time = self.as_of

        # Calculate all metrics
        volatility_30d = self.calculate_volatility(30)
        volatility_90d = self.calculate_volatility(90)
        volatility_1y = self.calculate_volatility(252)
        beta = self.calculate_beta()
        var = self.calculate_var()
        sharpe_ratio = self.calculate_sharpe_ratio()
        sortino_ratio = self.calculate_sortino_ratio()
        expected_shortfall = self.calculate_expected_shortfall()
        max_drawdown = self.calculate_max_drawdown()
        calmar_ratio = self.calculate_calmar_ratio()

        # Collect all metric results for status calculation
        all_metrics = {
            'volatility_30d': volatility_30d,
            'volatility_90d': volatility_90d,
            'volatility_1y': volatility_1y,
            'beta': beta,
            'var': var,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'expected_shortfall': expected_shortfall,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio
        }

        # Calculate overall status and coverage
        ok_count = sum(1 for m in all_metrics.values() if m.get('status') == 'OK')
        total_count = len(all_metrics)
        coverage_pct = int((ok_count / total_count) * 100) if total_count > 0 else 0

        # Determine overall status
        if coverage_pct == 100:
            overall_status = 'OK'
        elif coverage_pct >= 50:
            overall_status = 'PARTIAL'
        elif coverage_pct > 0:
            overall_status = 'MOSTLY_PENDING'
        else:
            overall_status = 'PENDING'

        # Check if data has changed (needs refresh)
        current_data_count = len(self.price_history)
        current_market_count = len(self.market_history)
        needs_refresh = (current_data_count > self._last_data_count or
                        current_market_count > self._last_market_count)

        return {
            'overall_status': overall_status,
            'coverage_pct': coverage_pct,
            'ok_metrics': ok_count,
            'total_metrics': total_count,
            'needs_refresh': needs_refresh,
            'as_of': current_time,
            'metrics': all_metrics,
            'data_quality': {
                'price_days': len(self.price_history),
                'return_days': len(self.returns),
                'has_market_data': bool(self.market_history),
                'market_days': len(self.market_history)
            }
        }

    def get_data_requirements(self) -> Dict[str, Any]:
        """
        Get data requirements for all metrics

        Returns:
            Dict containing minimum requirements and current availability
        """
        return {
            'requirements': self.MIN_DAYS,
            'current': {
                'price_history_days': len(self.price_history),
                'return_days': len(self.returns),
                'market_history_days': len(self.market_history),
                'market_return_days': len(self.market_returns)
            },
            'can_calculate': {
                'volatility': len(self.returns) >= self.MIN_DAYS['volatility'],
                'beta': (len(self.returns) >= self.MIN_DAYS['beta'] and
                        bool(self.market_returns)),
                'var': len(self.returns) >= self.MIN_DAYS['var'],
                'sharpe': len(self.returns) >= self.MIN_DAYS['sharpe'],
                'sortino': len(self.returns) >= self.MIN_DAYS['sortino'],
                'expected_shortfall': len(self.returns) >= self.MIN_DAYS['expected_shortfall'],
                'calmar': (len(self.returns) >= self.MIN_DAYS['calmar'] and
                           len(self.price_history) >= self.MIN_DAYS['max_drawdown']),
                'max_drawdown': len(self.price_history) >= self.MIN_DAYS['max_drawdown']
            }
        }


def analyze_stock_risk(db_path: Optional[str] = None, symbol: str = "",
                       days: int = 365,
                       risk_free_rate: float = 0.05) -> Dict[str, Any]:
    """
    Phân tích rủi ro cổ phiếu từ Supabase PostgreSQL.

    Args:
        db_path: Ignored (kept for backwards-compat). Connection uses DATABASE_URL.
        symbol: Mã cổ phiếu
        days: Số ngày lịch sử giá cần lấy
        risk_free_rate: Lãi suất phi rủi ro hàng năm

    Returns:
        Dict chứa tất cả các chỉ số rủi ro
    """
    from .. import db as _db

    with _db.connect() as conn:
        with conn.cursor() as cursor:
            # Deterministic as-of based on latest available price date for the symbol
            cursor.execute(
                "SELECT MAX(time) AS max_time FROM stock_price_history WHERE symbol = %s",
                (symbol,),
            )
            row = cursor.fetchone()
            max_time = row["max_time"] if row and row["max_time"] else None
            try:
                if max_time is None:
                    end_date = datetime.now()
                elif hasattr(max_time, 'strftime'):
                    end_date = datetime(max_time.year, max_time.month, max_time.day)
                else:
                    end_date = datetime.strptime(str(max_time), "%Y-%m-%d")
            except (TypeError, ValueError):
                end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Get stock price history
            cursor.execute("""
                SELECT time, open, high, low, close, volume
                FROM stock_price_history
                WHERE symbol = %s AND time >= %s AND time <= %s
                ORDER BY time ASC
            """, (symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            price_history = [dict(r) for r in cursor.fetchall()]

            # Get VNINDEX history for beta calculation
            cursor.execute("""
                SELECT time, close
                FROM stock_price_history
                WHERE symbol = 'VNINDEX' AND time >= %s AND time <= %s
                ORDER BY time ASC
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            market_history = [dict(r) for r in cursor.fetchall()]

    # Normalise date values to strings for downstream math
    for row in price_history:
        if row.get("time") and hasattr(row["time"], "strftime"):
            row["time"] = row["time"].strftime("%Y-%m-%d")
    for row in market_history:
        if row.get("time") and hasattr(row["time"], "strftime"):
            row["time"] = row["time"].strftime("%Y-%m-%d")

    # Create engine and calculate
    engine = RiskAnalysisEngine(
        price_history=price_history,
        market_history=market_history,
        risk_free_rate=risk_free_rate
    )

    return engine.calculate_all_risk_metrics()
