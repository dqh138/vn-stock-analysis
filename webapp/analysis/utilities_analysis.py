"""
Utilities (Power) Industry Analysis Module
Phân tích ngành Điện lực

Utilities-specific metrics for Vietnamese power companies.
"""

from typing import Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class UtilitiesAnalyzer:
    """
    Analyzer for Utilities (Power) industry companies.

    Power utilities have unique characteristics:
    - Capital-intensive with high debt
    - Stable cash flows from regulated tariffs
    - EBITDA is key metric (high depreciation)
    - Dividend plays with consistent payouts
    - Capacity utilization matters
    """

    def __init__(self):
        """Initialize analyzer with industry-specific thresholds."""
        # EBITDA margin thresholds (power utilities typically 40-60%)
        self.ebitda_margin = {
            'excellent': 50.0,    # > 50%
            'good': 35.0,         # 35-50%
            'low': 35.0           # < 35%
        }

        # Interest coverage (high debt normal in utilities)
        self.interest_coverage = {
            'strong': 3.0,        # > 3x
            'adequate': 2.0,      # 2-3x
            'risk': 2.0           # < 2x
        }

        # Debt/EBITDA (utilities carry high debt)
        self.debt_ebitda = {
            'conservative': 4.0,  # < 4x
            'normal': 6.0,        # 4-6x
            'high': 6.0           # > 6x
        }

        # Dividend payout ratio (utilities are dividend plays)
        self.payout_ratio = {
            'sustainable': 80.0,  # 50-80%
            'unsustainable': 80.0, # > 80%
            'retaining': 50.0     # < 50%
        }

        # Stability score weights
        self.weights = {
            'cash_generation': 0.35,  # EBITDA, OCF stability
            'financial_strength': 0.30,  # Debt, interest coverage
            'dividend_quality': 0.20,  # Payout, consistency
            'asset_efficiency': 0.15   # Capacity, turnover
        }

    def analyze(self, financial_ratios: Dict[str, Any],
                balance_sheet: Dict[str, Any],
                income_statement: Dict[str, Any],
                cash_flow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive utilities industry analysis.

        Args:
            financial_ratios: Dict with calculated ratios
            balance_sheet: Dict with balance sheet data
            income_statement: Dict with income statement data
            cash_flow: Dict with cash flow data

        Returns:
            Dict with all utilities metrics, ratings, and stability score
        """
        try:
            results = {
                'industry': 'Utilities',
                'industry_vn': 'Điện lực',
                'metrics': {},
                'ratings': {},
                'stability_score': None,
                'stability_level': None,
                'data_quality': {
                    'missing_fields': [],
                    'completeness': 0.0
                }
            }

            # Calculate all metrics
            ebitda_metrics = self._analyze_ebitda(financial_ratios, income_statement)
            results['metrics'].update(ebitda_metrics)

            debt_metrics = self._analyze_debt_capacity(financial_ratios, cash_flow, income_statement)
            results['metrics'].update(debt_metrics)

            dividend_metrics = self._analyze_dividend_quality(financial_ratios, cash_flow)
            results['metrics'].update(dividend_metrics)

            efficiency_metrics = self._analyze_asset_efficiency(financial_ratios,
                                                                balance_sheet,
                                                                income_statement)
            results['metrics'].update(efficiency_metrics)

            stability_metrics = self._analyze_cash_flow_stability(cash_flow)
            results['metrics'].update(stability_metrics)

            # Generate ratings for each metric
            results['ratings'] = self._generate_ratings(results['metrics'])

            # Calculate overall stability score
            stability_score = self._calculate_stability_score(results['metrics'],
                                                             results['ratings'])
            results['stability_score'] = stability_score
            results['stability_level'] = self._get_stability_level(stability_score)

            # Calculate data quality
            results['data_quality'] = self._assess_data_quality(results['metrics'])

            return results

        except Exception as e:
            logger.error(f"Error in utilities analysis: {e}")
            return self._get_empty_results()

    def _analyze_ebitda(self, financial_ratios: Dict[str, Any],
                       income_statement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze EBITDA margin - key metric for utilities.

        Power utilities have high depreciation, so EBITDA better
        reflects operating performance than net income.
        """
        metrics = {}

        # Try to get EBITDA margin from ratios
        ebitda_margin = financial_ratios.get('ebitda_margin')

        if ebitda_margin is not None:
            metrics['ebitda_margin'] = ebitda_margin

            # Rating based on utility standards
            if ebitda_margin >= self.ebitda_margin['excellent']:
                metrics['ebitda_margin_rating'] = 'Xuất sắc'
                metrics['ebitda_margin_score'] = 100
            elif ebitda_margin >= self.ebitda_margin['good']:
                metrics['ebitda_margin_rating'] = 'Tốt'
                metrics['ebitda_margin_score'] = 75
            else:
                metrics['ebitda_margin_rating'] = 'Thấp'
                metrics['ebitda_margin_score'] = 40

        # Calculate manually if not available
        if 'ebitda_margin' not in metrics:
            revenue = income_statement.get('revenue') or income_statement.get('doanh_thu')
            ebit = income_statement.get('ebit') or income_statement.get('loi_nhuan_gop_amortization')
            depreciation = income_statement.get('depreciation') or income_statement.get('hao_mon')

            if revenue and revenue > 0:
                ebitda = (ebit or 0) + (depreciation or 0)
                calculated_margin = (ebitda / revenue) * 100

                metrics['ebitda_margin'] = calculated_margin

                if calculated_margin >= self.ebitda_margin['excellent']:
                    metrics['ebitda_margin_rating'] = 'Xuất sắc'
                    metrics['ebitda_margin_score'] = 100
                elif calculated_margin >= self.ebitda_margin['good']:
                    metrics['ebitda_margin_rating'] = 'Tốt'
                    metrics['ebitda_margin_score'] = 75
                else:
                    metrics['ebitda_margin_rating'] = 'Thấp'
                    metrics['ebitda_margin_score'] = 40
            else:
                metrics['ebitda_margin'] = None
                metrics['ebitda_margin_rating'] = 'N/A'
                metrics['ebitda_margin_score'] = 0

        return metrics

    def _analyze_debt_capacity(self, financial_ratios: Dict[str, Any],
                              cash_flow: Dict[str, Any],
                              income_statement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze debt capacity - critical for capital-intensive utilities.

        Power companies require significant capex, so debt analysis
        must consider industry norms (higher debt acceptable).
        """
        metrics = {}

        # Interest Coverage
        interest_coverage = financial_ratios.get('interest_coverage')
        interest_expense = income_statement.get('interest_expense') or income_statement.get('chi_phi_lai_vay')
        ebit = income_statement.get('ebit') or income_statement.get('loi_nhuan_thuan')

        if interest_coverage is None and interest_expense and interest_expense > 0:
            interest_coverage = ebit / interest_expense

        if interest_coverage is not None:
            metrics['interest_coverage'] = interest_coverage

            if interest_coverage >= self.interest_coverage['strong']:
                metrics['interest_coverage_rating'] = 'Mạnh'
                metrics['interest_coverage_score'] = 100
            elif interest_coverage >= self.interest_coverage['adequate']:
                metrics['interest_coverage_rating'] = 'Đủ'
                metrics['interest_coverage_score'] = 70
            else:
                metrics['interest_coverage_rating'] = 'Rủi ro'
                metrics['interest_coverage_score'] = 30
        else:
            metrics['interest_coverage'] = None
            metrics['interest_coverage_rating'] = 'N/A'
            metrics['interest_coverage_score'] = 0

        # Debt/EBITDA
        total_debt = financial_ratios.get('total_debt')
        ebitda = financial_ratios.get('ebitda')

        # Calculate EBITDA if not available
        if ebitda is None:
            ebit = income_statement.get('ebit') or 0
            depreciation = income_statement.get('depreciation') or income_statement.get('hao_mon') or 0
            ebitda = ebit + depreciation

        if total_debt and ebitda and ebitda > 0:
            debt_ebitda_ratio = total_debt / ebitda
            metrics['debt_ebitda'] = debt_ebitda_ratio

            if debt_ebitda_ratio <= self.debt_ebitda['conservative']:
                metrics['debt_ebitda_rating'] = 'Thận trọng'
                metrics['debt_ebitda_score'] = 100
            elif debt_ebitda_ratio <= self.debt_ebitda['normal']:
                metrics['debt_ebitda_rating'] = 'Bình thường'
                metrics['debt_ebitda_score'] = 75
            else:
                metrics['debt_ebitda_rating'] = 'Cao'
                metrics['debt_ebitda_score'] = 40
        else:
            metrics['debt_ebitda'] = None
            metrics['debt_ebitda_rating'] = 'N/A'
            metrics['debt_ebitda_score'] = 0

        return metrics

    def _analyze_dividend_quality(self, financial_ratios: Dict[str, Any],
                                  cash_flow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze dividend quality - utilities are dividend plays.

        Investors expect consistent, sustainable dividends from utilities.
        """
        metrics = {}

        # Dividend Payout Ratio
        payout_ratio = financial_ratios.get('dividend_payout_ratio')
        net_income = financial_ratios.get('net_income')
        dividends = financial_ratios.get('dividends')

        if payout_ratio is None and net_income and net_income > 0:
            payout_ratio = (dividends or 0) / net_income * 100

        if payout_ratio is not None:
            metrics['dividend_payout_ratio'] = payout_ratio

            if payout_ratio <= self.payout_ratio['unsustainable']:
                if payout_ratio >= self.payout_ratio['retaining']:
                    metrics['payout_ratio_rating'] = 'Bền vững'
                    metrics['payout_ratio_score'] = 100
                else:
                    metrics['payout_ratio_rating'] = 'Tích lũy'
                    metrics['payout_ratio_score'] = 80
            else:
                metrics['payout_ratio_rating'] = 'Không bền vững'
                metrics['payout_ratio_score'] = 30
        else:
            metrics['dividend_payout_ratio'] = None
            metrics['payout_ratio_rating'] = 'N/A'
            metrics['payout_ratio_score'] = 0

        # Dividend consistency (check if dividends paid consistently)
        # Would need historical data - using OCF as proxy for sustainability
        operating_cf = cash_flow.get('operating_cash_flow') or cash_flow.get('dong_tien_luu_chuyen')

        if dividends and operating_cf:
            if operating_cf >= dividends:
                metrics['dividend_coverage'] = 'Phù hợp'
                metrics['dividend_coverage_score'] = 100
            else:
                metrics['dividend_coverage'] = 'Rủi ro'
                metrics['dividend_coverage_score'] = 40
        else:
            metrics['dividend_coverage'] = 'N/A'
            metrics['dividend_coverage_score'] = 0

        return metrics

    def _analyze_asset_efficiency(self, financial_ratios: Dict[str, Any],
                                 balance_sheet: Dict[str, Any],
                                 income_statement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze asset efficiency - capacity utilization matters.

        For power companies, generating capacity utilization is key.
        Using revenue/fixed assets as proxy.
        """
        metrics = {}

        # Fixed Asset Turnover
        fixed_asset_turnover = financial_ratios.get('fixed_asset_turnover')
        revenue = income_statement.get('revenue') or income_statement.get('doanh_thu')
        fixed_assets = balance_sheet.get('fixed_assets') or balance_sheet.get('tai_san_co_dinh')

        if fixed_asset_turnover is None and fixed_assets and fixed_assets > 0:
            fixed_asset_turnover = revenue / fixed_assets

        if fixed_asset_turnover is not None:
            metrics['fixed_asset_turnover'] = fixed_asset_turnover

            # For utilities, higher turnover indicates better capacity utilization
            if fixed_asset_turnover >= 0.5:
                metrics['asset_turnover_rating'] = 'Tốt'
                metrics['asset_turnover_score'] = 100
            elif fixed_asset_turnover >= 0.3:
                metrics['asset_turnover_rating'] = 'Trung bình'
                metrics['asset_turnover_score'] = 70
            else:
                metrics['asset_turnover_rating'] = 'Thấp'
                metrics['asset_turnover_score'] = 40
        else:
            metrics['fixed_asset_turnover'] = None
            metrics['asset_turnover_rating'] = 'N/A'
            metrics['asset_turnover_score'] = 0

        # Capacity Factor Proxy
        # Revenue / (Fixed Assets * 0.5) as rough capacity utilization proxy
        if revenue and fixed_assets and fixed_assets > 0:
            capacity_proxy = revenue / (fixed_assets * 0.5)
            metrics['capacity_factor_proxy'] = capacity_proxy

            if capacity_proxy >= 1.0:
                metrics['capacity_utilization'] = 'Cao'
                metrics['capacity_score'] = 100
            elif capacity_proxy >= 0.5:
                metrics['capacity_utilization'] = 'Đủ'
                metrics['capacity_score'] = 70
            else:
                metrics['capacity_utilization'] = 'Thấp'
                metrics['capacity_score'] = 40
        else:
            metrics['capacity_factor_proxy'] = None
            metrics['capacity_utilization'] = 'N/A'
            metrics['capacity_score'] = 0

        return metrics

    def _analyze_cash_flow_stability(self, cash_flow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze cash flow stability and quality.

        Utilities should have stable, predictable OCF.
        Higher OCF/Net Income = better quality.
        """
        metrics = {}

        operating_cf = cash_flow.get('operating_cash_flow') or cash_flow.get('dong_tien_luu_chuyen')
        net_income = cash_flow.get('net_income') or cash_flow.get('loi_nhuan')

        if operating_cf and net_income and net_income != 0:
            ocf_to_ni = operating_cf / net_income
            metrics['ocf_to_net_income'] = ocf_to_ni

            if ocf_to_ni >= 1.2:
                metrics['ocf_quality'] = 'Rất cao'
                metrics['ocf_quality_score'] = 100
            elif ocf_to_ni >= 1.0:
                metrics['ocf_quality'] = 'Cao'
                metrics['ocf_quality_score'] = 85
            elif ocf_to_ni >= 0.8:
                metrics['ocf_quality'] = 'Khá'
                metrics['ocf_quality_score'] = 70
            else:
                metrics['ocf_quality'] = 'Thấp'
                metrics['ocf_quality_score'] = 40
        else:
            metrics['ocf_to_net_income'] = None
            metrics['ocf_quality'] = 'N/A'
            metrics['ocf_quality_score'] = 0

        # OCF positivity (basic check)
        if operating_cf:
            if operating_cf > 0:
                metrics['ocf_positive'] = True
                metrics['ocf_positive_score'] = 100
            else:
                metrics['ocf_positive'] = False
                metrics['ocf_positive_score'] = 0
        else:
            metrics['ocf_positive'] = None
            metrics['ocf_positive_score'] = 0

        return metrics

    def _generate_ratings(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate overall ratings for each category."""
        ratings = {}

        # EBITDA Rating
        if metrics.get('ebitda_margin_rating'):
            ratings['ebitda'] = metrics['ebitda_margin_rating']

        # Financial Strength Rating (combination of debt metrics)
        debt_score = (metrics.get('interest_coverage_score', 0) +
                     metrics.get('debt_ebitda_score', 0)) / 2
        if debt_score > 0:
            if debt_score >= 80:
                ratings['financial_strength'] = 'Mạnh'
            elif debt_score >= 60:
                ratings['financial_strength'] = 'Đủ'
            else:
                ratings['financial_strength'] = 'Yếu'

        # Dividend Quality Rating
        if metrics.get('payout_ratio_rating'):
            ratings['dividend_quality'] = metrics['payout_ratio_rating']

        # Asset Efficiency Rating
        if metrics.get('capacity_utilization'):
            ratings['asset_efficiency'] = metrics['capacity_utilization']

        return ratings

    def _calculate_stability_score(self, metrics: Dict[str, Any],
                                  ratings: Dict[str, str]) -> float:
        """
        Calculate overall Utilities Stability Score.

        Weights:
        - Cash Generation (35%): EBITDA Margin, OCF Quality, OCF/Net Income
        - Financial Strength (30%): Debt/EBITDA, Interest Coverage
        - Dividend Quality (20%): Payout Ratio, Dividend Coverage
        - Asset Efficiency (15%): Capacity Factor, Fixed Asset Turnover
        """
        # Cash Generation (35%)
        cash_gen_score = (
            metrics.get('ebitda_margin_score', 0) * 0.4 +
            metrics.get('ocf_quality_score', 0) * 0.3 +
            metrics.get('ocf_positive_score', 0) * 0.3
        )

        # Financial Strength (30%)
        fin_strength_score = (
            metrics.get('interest_coverage_score', 0) * 0.5 +
            metrics.get('debt_ebitda_score', 0) * 0.5
        )

        # Dividend Quality (20%)
        dividend_score = (
            metrics.get('payout_ratio_score', 0) * 0.6 +
            metrics.get('dividend_coverage_score', 0) * 0.4
        )

        # Asset Efficiency (15%)
        asset_eff_score = (
            metrics.get('capacity_score', 0) * 0.5 +
            metrics.get('asset_turnover_score', 0) * 0.5
        )

        # Weighted total
        total_score = (
            cash_gen_score * self.weights['cash_generation'] +
            fin_strength_score * self.weights['financial_strength'] +
            dividend_score * self.weights['dividend_quality'] +
            asset_eff_score * self.weights['asset_efficiency']
        )

        return round(total_score, 1)

    def _get_stability_level(self, score: float) -> str:
        """Convert stability score to level label."""
        if score >= 80:
            return 'Rất ổn định'
        elif score >= 65:
            return 'Ổn định'
        elif score >= 50:
            return 'Trung bình'
        elif score >= 35:
            return 'Yếu'
        else:
            return 'Rủi ro'

    def _assess_data_quality(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess completeness of data availability."""
        key_metrics = [
            'ebitda_margin', 'interest_coverage', 'debt_ebitda',
            'dividend_payout_ratio', 'ocf_to_net_income', 'capacity_factor_proxy'
        ]

        missing = [m for m in key_metrics if metrics.get(m) is None]
        completeness = (len(key_metrics) - len(missing)) / len(key_metrics) * 100

        return {
            'missing_fields': missing,
            'completeness': round(completeness, 1),
            'total_metrics': len(key_metrics),
            'available_metrics': len(key_metrics) - len(missing)
        }

    def _get_empty_results(self) -> Dict[str, Any]:
        """Return empty results structure for error cases."""
        return {
            'industry': 'Utilities',
            'industry_vn': 'Điện lực',
            'metrics': {},
            'ratings': {},
            'stability_score': 0.0,
            'stability_level': 'Không có dữ liệu',
            'data_quality': {
                'missing_fields': [],
                'completeness': 0.0
            },
            'error': 'Analysis failed'
        }


def analyze_utilities(financial_ratios: Dict[str, Any],
                     balance_sheet: Dict[str, Any],
                     income_statement: Dict[str, Any],
                     cash_flow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for utilities industry analysis.

    Args:
        financial_ratios: Dict with calculated ratios
        balance_sheet: Dict with balance sheet data
        income_statement: Dict with income statement data
        cash_flow: Dict with cash flow data

    Returns:
        Dict with all utilities metrics, ratings, and stability score
    """
    analyzer = UtilitiesAnalyzer()
    return analyzer.analyze(financial_ratios, balance_sheet,
                          income_statement, cash_flow)
