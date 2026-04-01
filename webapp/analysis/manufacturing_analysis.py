"""
Manufacturing Industry Analysis Module
Analyzes manufacturing-specific metrics for Vietnamese companies

Industries covered: Steel, Cement, Chemicals
"""

import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class ManufacturingAnalyzer:
    """Analyzer for manufacturing industry companies"""

    # Industry benchmarks for gross margin
    INDUSTRY_BENCHMARKS = {
        'steel': {'gross_margin_min': 0.10, 'gross_margin_max': 0.15, 'label': 'Thép'},
        'cement': {'gross_margin_min': 0.20, 'gross_margin_max': 0.30, 'label': 'Xi măng'},
        'chemicals': {'gross_margin_min': 0.15, 'gross_margin_max': 0.25, 'label': 'Hóa chất'},
        'default': {'gross_margin_min': 0.15, 'gross_margin_max': 0.25, 'label': 'Sản xuất'}
    }

    def __init__(self, industry: str = 'default'):
        """
        Initialize analyzer with industry type

        Args:
            industry: Industry type ('steel', 'cement', 'chemicals', 'default')
        """
        self.industry = industry.lower() if industry else 'default'
        self.benchmark = self.INDUSTRY_BENCHMARKS.get(self.industry, self.INDUSTRY_BENCHMARKS['default'])

    def analyze(self,
                financial_ratios: Dict[str, Any],
                balance_sheet: Dict[str, Any],
                income_statement: Dict[str, Any],
                cash_flow: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform comprehensive manufacturing analysis

        Args:
            financial_ratios: Dictionary of calculated financial ratios
            balance_sheet: Balance sheet data
            income_statement: Income statement data
            cash_flow: Cash flow statement data (optional)

        Returns:
            Dictionary with all manufacturing metrics and scores
        """
        try:
            results = {
                'industry': self.benchmark['label'],
                'metrics': {},
                'ratings': {},
                'efficiency_score': {
                    'total': 0,
                    'components': {},
                    'rating': '',
                    'interpretation': ''
                }
            }

            # Calculate all metrics
            results['metrics']['inventory_turnover_days'] = self._calculate_inventory_turnover_days(
                income_statement, balance_sheet
            )

            results['metrics']['capacity_utilization_proxy'] = self._calculate_capacity_utilization_proxy(
                income_statement, balance_sheet
            )

            results['metrics']['gross_margin_trend'] = self._calculate_gross_margin_trend(
                income_statement
            )

            results['metrics']['fixed_asset_turnover'] = self._calculate_fixed_asset_turnover(
                income_statement, balance_sheet
            )

            results['metrics']['raw_material_cost_pct'] = self._calculate_raw_material_cost_pct(
                income_statement
            )

            results['metrics']['depreciation_revenue'] = self._calculate_depreciation_revenue(
                income_statement
            )

            results['metrics']['capex_depreciation'] = self._calculate_capex_depreciation(
                income_statement, cash_flow
            )

            results['metrics']['operating_leverage'] = self._calculate_operating_leverage(
                income_statement
            )

            # Calculate ratings for each metric
            results['ratings']['inventory_turnover'] = self._rate_inventory_turnover(
                results['metrics']['inventory_turnover_days']
            )

            results['ratings']['capacity_utilization'] = self._rate_capacity_utilization(
                results['metrics']['capacity_utilization_proxy']
            )

            results['ratings']['gross_margin'] = self._rate_gross_margin(
                results['metrics']['gross_margin_trend']
            )

            results['ratings']['fixed_asset_turnover'] = self._rate_fixed_asset_turnover(
                results['metrics']['fixed_asset_turnover']
            )

            results['ratings']['raw_material_cost'] = self._rate_raw_material_cost(
                results['metrics']['raw_material_cost_pct']
            )

            results['ratings']['capital_investment'] = self._rate_capital_investment(
                results['metrics']['capex_depreciation']
            )

            # Calculate overall efficiency score
            efficiency_results = self._calculate_efficiency_score(
                results['metrics'], financial_ratios
            )
            results['efficiency_score'] = efficiency_results

            return results

        except Exception as e:
            logger.error(f"Error in manufacturing analysis: {str(e)}")
            return self._get_empty_result()

    def _calculate_inventory_turnover_days(self,
                                          income_statement: Dict[str, Any],
                                          balance_sheet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Inventory Turnover Days

        Formula: 365 / (COGS / Average Inventory)
        Rating: < 30 days = Excellent, 30-60 = Good, 60-90 = Average, > 90 = Slow
        """
        try:
            # DB often stores COGS as negative expense; use magnitude
            cogs = income_statement.get('cost_of_goods_sold', 0) or 0
            cogs = abs(cogs) if isinstance(cogs, (int, float)) else abs(float(cogs)) if cogs is not None else 0
            inventory_current = balance_sheet.get('inventory', 0)
            inventory_previous = balance_sheet.get('inventory_previous', inventory_current)

            if cogs and inventory_current:
                avg_inventory = (inventory_current + inventory_previous) / 2
                inventory_turnover = cogs / avg_inventory if avg_inventory else 0
                days = 365 / inventory_turnover if inventory_turnover else 0

                rating = 'Tuyệt vời' if days < 30 else 'Tốt' if days < 60 else 'Trung bình' if days < 90 else 'Chậm'

                return {
                    'value': round(days, 1),
                    'inventory_turnover_ratio': round(inventory_turnover, 2),
                    'rating': rating,
                    'label': 'Ngày quay vòng hàng tồn kho',
                    'interpretation': f'{rating}: Quay vòng hàng tồn kho {days:.1f} ngày/năm'
                }

            return self._missing_metric('Ngày quay vòng hàng tồn kho')

        except Exception as e:
            logger.error(f"Error calculating inventory turnover days: {str(e)}")
            return self._missing_metric('Ngày quay vòng hàng tồn kho')

    def _calculate_capacity_utilization_proxy(self,
                                             income_statement: Dict[str, Any],
                                             balance_sheet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Capacity Utilization Proxy

        Formula: Revenue / (Fixed Assets × 2)
        Higher = better utilization
        """
        try:
            # Prefer net_revenue (revenue in DB may be negative credits for non-banks)
            revenue = income_statement.get('net_revenue')
            if revenue is None:
                revenue = income_statement.get('revenue', 0)
            if isinstance(revenue, (int, float)) and revenue < 0:
                revenue = abs(revenue)

            fixed_assets = balance_sheet.get('fixed_assets') or balance_sheet.get('property_plant_equipment', 0)

            if revenue and fixed_assets:
                utilization = revenue / (fixed_assets * 2) if fixed_assets else 0

                rating = 'Rất cao' if utilization > 1 else 'Cao' if utilization > 0.7 else 'Trung bình' if utilization > 0.4 else 'Thấp'

                return {
                    'value': round(utilization, 2),
                    'rating': rating,
                    'label': 'Tỷ lệ sử dụng công suất (ước tính)',
                    'interpretation': f'{rating}: Tỷ lệ sử dụng công suất {utilization:.1%} (ước tính)'
                }

            return self._missing_metric('Tỷ lệ sử dụng công suất')

        except Exception as e:
            logger.error(f"Error calculating capacity utilization: {str(e)}")
            return self._missing_metric('Tỷ lệ sử dụng công suất')

    def _calculate_gross_margin_trend(self, income_statement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Gross Margin Trend

        Compares current gross margin vs previous year
        Industry benchmarks: Steel 10-15%, Cement 20-30%, Chemicals 15-25%
        """
        try:
            # Prefer net_revenue and normalize sign conventions
            revenue = income_statement.get('net_revenue')
            if revenue is None:
                revenue = income_statement.get('revenue', 0)
            if isinstance(revenue, (int, float)) and revenue < 0:
                revenue = abs(revenue)

            cogs = income_statement.get('cost_of_goods_sold', 0) or 0
            cogs = abs(cogs) if isinstance(cogs, (int, float)) else abs(float(cogs)) if cogs is not None else 0

            revenue_previous = income_statement.get('net_revenue_previous')
            if revenue_previous is None:
                revenue_previous = income_statement.get('revenue_previous', 0)
            if isinstance(revenue_previous, (int, float)) and revenue_previous < 0:
                revenue_previous = abs(revenue_previous)

            cogs_previous = income_statement.get('cost_of_goods_sold_previous', 0) or 0
            cogs_previous = abs(cogs_previous) if isinstance(cogs_previous, (int, float)) else abs(float(cogs_previous)) if cogs_previous is not None else 0

            if revenue and cogs:
                gross_margin_current = (revenue - cogs) / revenue if revenue else 0
                trend = None

                if revenue_previous and cogs_previous:
                    gross_margin_previous = (revenue_previous - cogs_previous) / revenue_previous if revenue_previous else 0
                    change = gross_margin_current - gross_margin_previous
                    trend_pct = change / gross_margin_previous * 100 if gross_margin_previous else 0

                    trend = 'Cải thiện' if change > 0.01 else 'Giảm' if change < -0.01 else 'Ổn định'
                else:
                    trend_pct = 0

                # Compare to industry benchmark
                benchmark_min = self.benchmark['gross_margin_min']
                benchmark_max = self.benchmark['gross_margin_max']

                if gross_margin_current >= benchmark_max:
                    vs_industry = 'Trên trung bình ngành'
                elif gross_margin_current >= benchmark_min:
                    vs_industry = 'Trong khoảng ngành'
                else:
                    vs_industry = 'Dưới trung bình ngành'

                return {
                    'value': round(gross_margin_current * 100, 1),
                    'change_pct': round(trend_pct, 1) if trend_pct else None,
                    'trend': trend,
                    'vs_industry': vs_industry,
                    'industry_range': f"{benchmark_min*100:.0f}-{benchmark_max*100:.0f}%",
                    'label': 'Biên lợi nhuận gộp',
                    'interpretation': f'{gross_margin_current*100:.1f}% - {vs_industry} ({trend or "N/A"})'
                }

            return self._missing_metric('Biên lợi nhuận gộp')

        except Exception as e:
            logger.error(f"Error calculating gross margin trend: {str(e)}")
            return self._missing_metric('Biên lợi nhuận gộp')

    def _calculate_fixed_asset_turnover(self,
                                       income_statement: Dict[str, Any],
                                       balance_sheet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Fixed Asset Turnover

        Formula: Revenue / Average Fixed Assets
        Rating: > 2 = Excellent, 1-2 = Good, 0.5-1 = Average, < 0.5 = Under-utilized
        """
        try:
            revenue = income_statement.get('net_revenue')
            if revenue is None:
                revenue = income_statement.get('revenue', 0)
            if isinstance(revenue, (int, float)) and revenue < 0:
                revenue = abs(revenue)

            fixed_assets_current = balance_sheet.get('fixed_assets') or balance_sheet.get('property_plant_equipment', 0)
            fixed_assets_previous = balance_sheet.get('fixed_assets_previous', fixed_assets_current)
            if not fixed_assets_previous:
                fixed_assets_previous = balance_sheet.get('property_plant_equipment_previous', fixed_assets_current)

            if revenue and fixed_assets_current:
                avg_fixed_assets = (fixed_assets_current + fixed_assets_previous) / 2
                turnover = revenue / avg_fixed_assets if avg_fixed_assets else 0

                rating = 'Tuyệt vời' if turnover > 2 else 'Tốt' if turnover > 1 else 'Trung bình' if turnover > 0.5 else 'Chưa tận dụng'

                return {
                    'value': round(turnover, 2),
                    'rating': rating,
                    'label': 'Vòng quay tài sản cố định',
                    'interpretation': f'{rating}: Mỗi đồng tài sản cố định tạo ra {turnover:.2f} đồng doanh thu'
                }

            return self._missing_metric('Vòng quay tài sản cố định')

        except Exception as e:
            logger.error(f"Error calculating fixed asset turnover: {str(e)}")
            return self._missing_metric('Vòng quay tài sản cố định')

    def _calculate_raw_material_cost_pct(self, income_statement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Raw Material Cost % (approximation)

        Formula: COGS / Revenue
        Higher = more sensitive to commodity prices
        """
        try:
            revenue = income_statement.get('net_revenue')
            if revenue is None:
                revenue = income_statement.get('revenue', 0)
            if isinstance(revenue, (int, float)) and revenue < 0:
                revenue = abs(revenue)

            cogs = income_statement.get('cost_of_goods_sold', 0) or 0
            cogs = abs(cogs) if isinstance(cogs, (int, float)) else abs(float(cogs)) if cogs is not None else 0

            if revenue and cogs:
                raw_material_pct = cogs / revenue if revenue else 0

                rating = 'Thấp' if raw_material_pct < 0.6 else 'Trung bình' if raw_material_pct < 0.8 else 'Cao'
                sensitivity = 'Ít nhạy cảm' if raw_material_pct < 0.6 else 'Nhạy cảm' if raw_material_pct < 0.8 else 'Rất nhạy cảm'

                return {
                    'value': round(raw_material_pct * 100, 1),
                    'rating': rating,
                    'sensitivity': sensitivity,
                    'label': 'Giá vốn hàng bán / Doanh thu',
                    'interpretation': f'{sensitivity} với biến động giá nguyên vật liệu ({raw_material_pct*100:.1f}% COGS)'
                }

            return self._missing_metric('Giá vốn/Doanh thu')

        except Exception as e:
            logger.error(f"Error calculating raw material cost %: {str(e)}")
            return self._missing_metric('Giá vốn/Doanh thu')

    def _calculate_depreciation_revenue(self, income_statement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Depreciation/Revenue Ratio

        Formula: Depreciation / Revenue
        Capital-intensive industries typically have 3-8%
        """
        try:
            revenue = income_statement.get('net_revenue')
            if revenue is None:
                revenue = income_statement.get('revenue', 0)
            if isinstance(revenue, (int, float)) and revenue < 0:
                revenue = abs(revenue)
            depreciation = income_statement.get('depreciation', 0)

            if revenue and depreciation:
                depr_revenue = depreciation / revenue if revenue else 0

                rating = 'Thấp' if depr_revenue < 0.03 else 'Trung bình' if depr_revenue < 0.08 else 'Cao'

                return {
                    'value': round(depr_revenue * 100, 1),
                    'rating': rating,
                    'label': 'Khấu hao / Doanh thu',
                    'interpretation': f'{rating}: Tỷ lệ khấu hao {depr_revenue*100:.1f}% doanh thu (ngành sản xuất thường 3-8%)'
                }

            return self._missing_metric('Khấu hao/Doanh thu')

        except Exception as e:
            logger.error(f"Error calculating depreciation/revenue: {str(e)}")
            return self._missing_metric('Khấu hao/Doanh thu')

    def _calculate_capex_depreciation(self,
                                     income_statement: Dict[str, Any],
                                     cash_flow: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate CapEx/Depreciation Ratio

        Formula: Capital Expenditure / Depreciation
        > 1 = Expanding, < 1 = Harvesting/maintenance mode
        """
        try:
            depreciation = income_statement.get('depreciation', 0)

            # Try to get CapEx from cash flow or income statement
            capex = 0
            if cash_flow:
                # CapEx is typically negative in investing activities
                capex_investing = (
                    cash_flow.get('capital_expenditure') or
                    cash_flow.get('purchase_purchase_fixed_assets') or
                    cash_flow.get('capex') or
                    0
                )
                capex = abs(capex_investing) if capex_investing < 0 else capex_investing

            if not capex:
                # Try alternative fields
                capex = income_statement.get('capital_expenditure', 0)

            if depreciation and capex:
                capex_depr = capex / depreciation if depreciation else 0

                if capex_depr > 1.5:
                    status = 'Mở rộng mạnh'
                elif capex_depr > 1:
                    status = 'Mở rộng'
                elif capex_depr > 0.7:
                    status = 'Duy trì'
                else:
                    status = 'Thu hẹp'

                return {
                    'value': round(capex_depr, 2),
                    'status': status,
                    'label': 'Capex / Khấu hao',
                    'interpretation': f'{status}: Tỷ số {capex_depr:.2f}x ({"Đầu tư > Khấu hao" if capex_depr > 1 else "Đầu tư < Khấu hao"})'
                }

            return self._missing_metric('Capex/Khấu hao')

        except Exception as e:
            logger.error(f"Error calculating CapEx/Depreciation: {str(e)}")
            return self._missing_metric('Capex/Khấu hao')

    def _calculate_operating_leverage(self, income_statement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Operating Leverage (approximation)

        Formula: Fixed costs / Total costs
        Approximated with (D&A + Admin expenses) / Total expenses
        Higher = more sensitive to volume changes
        """
        try:
            depreciation = income_statement.get('depreciation', 0)
            admin_expenses = income_statement.get('selling_general_administrative', 0)
            operating_expenses = income_statement.get('operating_expenses', 0)
            total_expenses = income_statement.get('total_expenses', 0)

            # Calculate fixed costs component
            fixed_costs = depreciation + admin_expenses

            # Use total expenses or operating expenses as denominator
            total_costs = total_expenses if total_expenses else operating_expenses

            if fixed_costs and total_costs:
                operating_leverage = fixed_costs / total_costs if total_costs else 0

                rating = 'Thấp' if operating_leverage < 0.3 else 'Trung bình' if operating_leverage < 0.5 else 'Cao'

                return {
                    'value': round(operating_leverage * 100, 1),
                    'rating': rating,
                    'label': 'Đòn bẩy hoạt động (ước tính)',
                    'interpretation': f'{rating}: Chi phí cố định chiếm {operating_leverage*100:.1f}% tổng chi phí'
                }

            return self._missing_metric('Đòn bẩy hoạt động')

        except Exception as e:
            logger.error(f"Error calculating operating leverage: {str(e)}")
            return self._missing_metric('Đòn bẩy hoạt động')

    def _rate_inventory_turnover(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rating for inventory turnover"""
        if not metric.get('value'):
            return {'score': 0, 'rating': 'N/A', 'color': 'gray'}

        days = metric['value']
        if days < 30:
            return {'score': 100, 'rating': 'Tuyệt vời', 'color': 'green'}
        elif days < 60:
            return {'score': 75, 'rating': 'Tốt', 'color': 'blue'}
        elif days < 90:
            return {'score': 50, 'rating': 'Trung bình', 'color': 'yellow'}
        else:
            return {'score': 25, 'rating': 'Chậm', 'color': 'red'}

    def _rate_capacity_utilization(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rating for capacity utilization"""
        if not metric.get('value'):
            return {'score': 0, 'rating': 'N/A', 'color': 'gray'}

        utilization = metric['value']
        if utilization > 1:
            return {'score': 100, 'rating': 'Rất cao', 'color': 'green'}
        elif utilization > 0.7:
            return {'score': 75, 'rating': 'Cao', 'color': 'blue'}
        elif utilization > 0.4:
            return {'score': 50, 'rating': 'Trung bình', 'color': 'yellow'}
        else:
            return {'score': 25, 'rating': 'Thấp', 'color': 'red'}

    def _rate_gross_margin(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rating for gross margin"""
        if not metric.get('value'):
            return {'score': 0, 'rating': 'N/A', 'color': 'gray'}

        vs_industry = metric.get('vs_industry', '')
        if 'Trên trung bình' in vs_industry:
            return {'score': 100, 'rating': 'Xuất sắc', 'color': 'green'}
        elif 'Trong khoảng' in vs_industry:
            return {'score': 75, 'rating': 'Đạt chuẩn', 'color': 'blue'}
        else:
            return {'score': 40, 'rating': 'Cần cải thiện', 'color': 'red'}

    def _rate_fixed_asset_turnover(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rating for fixed asset turnover"""
        if not metric.get('value'):
            return {'score': 0, 'rating': 'N/A', 'color': 'gray'}

        turnover = metric['value']
        if turnover > 2:
            return {'score': 100, 'rating': 'Tuyệt vời', 'color': 'green'}
        elif turnover > 1:
            return {'score': 75, 'rating': 'Tốt', 'color': 'blue'}
        elif turnover > 0.5:
            return {'score': 50, 'rating': 'Trung bình', 'color': 'yellow'}
        else:
            return {'score': 25, 'rating': 'Chưa tận dụng', 'color': 'red'}

    def _rate_raw_material_cost(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rating for raw material cost"""
        if not metric.get('value'):
            return {'score': 0, 'rating': 'N/A', 'color': 'gray'}

        cost_pct = metric['value']
        # Lower is generally better for cost control
        if cost_pct < 60:
            return {'score': 100, 'rating': 'Tốt', 'color': 'green'}
        elif cost_pct < 80:
            return {'score': 75, 'rating': 'Khá', 'color': 'blue'}
        else:
            return {'score': 50, 'rating': 'Cần kiểm soát', 'color': 'yellow'}

    def _rate_capital_investment(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rating for capital investment"""
        if not metric.get('value'):
            return {'score': 0, 'rating': 'N/A', 'color': 'gray'}

        capex_depr = metric['value']
        if capex_depr > 1.5:
            return {'score': 100, 'rating': 'Mở rộng mạnh', 'color': 'green'}
        elif capex_depr > 1:
            return {'score': 75, 'rating': 'Mở rộng', 'color': 'blue'}
        elif capex_depr > 0.7:
            return {'score': 50, 'rating': 'Duy trì', 'color': 'yellow'}
        else:
            return {'score': 40, 'rating': 'Thu hẹp', 'color': 'red'}

    def _calculate_efficiency_score(self,
                                   metrics: Dict[str, Any],
                                   financial_ratios: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Overall Manufacturing Efficiency Score

        Components:
        - Asset Utilization (30%): Fixed Asset Turnover, Total Asset Turnover
        - Cost Management (30%): Gross Margin, Operating Margin
        - Inventory Management (20%): Inventory Turnover, Days Inventory
        - Capital Investment (20%): CapEx/Depreciation, Asset Age
        """
        try:
            scores = {}

            # Asset Utilization (30%)
            fixed_asset_turnover_score = self._rate_fixed_asset_turnover(
                metrics.get('fixed_asset_turnover', {})
            ).get('score', 0)

            # Try to get total asset turnover from financial_ratios
            total_asset_turnover = financial_ratios.get('asset_turnover') or 0
            if total_asset_turnover:
                if total_asset_turnover > 1.5:
                    total_asset_score = 100
                elif total_asset_turnover > 1:
                    total_asset_score = 75
                elif total_asset_turnover > 0.5:
                    total_asset_score = 50
                else:
                    total_asset_score = 25
            else:
                total_asset_score = 50  # Default score if missing

            asset_utilization_score = (fixed_asset_turnover_score * 0.6 + total_asset_score * 0.4)
            scores['asset_utilization'] = {
                'score': round(asset_utilization_score, 1),
                'weight': 30,
                'weighted_score': round(asset_utilization_score * 0.3, 1),
                'label': 'Hiệu quả sử dụng tài sản'
            }

            # Cost Management (30%)
            gross_margin_score = self._rate_gross_margin(metrics.get('gross_margin_trend', {})).get('score', 0)

            # Get operating margin from ratios or income statement
            operating_margin = (
                financial_ratios.get('ebit_margin') or
                financial_ratios.get('operating_margin') or
                0
            )
            if operating_margin:
                if operating_margin > 0.15:
                    operating_margin_score = 100
                elif operating_margin > 0.10:
                    operating_margin_score = 75
                elif operating_margin > 0.05:
                    operating_margin_score = 50
                else:
                    operating_margin_score = 25
            else:
                operating_margin_score = 50

            cost_management_score = (gross_margin_score * 0.5 + operating_margin_score * 0.5)
            scores['cost_management'] = {
                'score': round(cost_management_score, 1),
                'weight': 30,
                'weighted_score': round(cost_management_score * 0.3, 1),
                'label': 'Quản lý chi phí'
            }

            # Inventory Management (20%)
            inventory_score = self._rate_inventory_turnover(metrics.get('inventory_turnover_days', {})).get('score', 0)
            scores['inventory_management'] = {
                'score': round(inventory_score, 1),
                'weight': 20,
                'weighted_score': round(inventory_score * 0.2, 1),
                'label': 'Quản lý tồn kho'
            }

            # Capital Investment (20%)
            capex_score = self._rate_capital_investment(metrics.get('capex_depreciation', {})).get('score', 0)

            # Asset age approximation (use depreciation/accumulated depreciation ratio if available)
            depr_revenue = metrics.get('depreciation_revenue', {}).get('value', 0)
            if depr_revenue:
                if depr_revenue > 8:
                    asset_age_score = 25  # Very old assets
                elif depr_revenue > 5:
                    asset_age_score = 50
                elif depr_revenue > 3:
                    asset_age_score = 75
                else:
                    asset_age_score = 100  # Newer assets
            else:
                asset_age_score = 50

            capital_investment_score = (capex_score * 0.5 + asset_age_score * 0.5)
            scores['capital_investment'] = {
                'score': round(capital_investment_score, 1),
                'weight': 20,
                'weighted_score': round(capital_investment_score * 0.2, 1),
                'label': 'Đầu tư vốn'
            }

            # Calculate total score
            total_score = sum(s['weighted_score'] for s in scores.values())

            # Overall rating
            if total_score >= 80:
                rating = 'Xuất sắc'
                color = 'green'
                interpretation = 'Hiệu quả sản xuất xuất sắc, quản lý tài sản và chi phí tốt'
            elif total_score >= 70:
                rating = 'Tốt'
                color = 'blue'
                interpretation = 'Hiệu quả sản xuất tốt, có khả năng cạnh tranh cao'
            elif total_score >= 60:
                rating = 'Khá'
                color = 'yellow'
                interpretation = 'Hiệu quả sản xuất khá, cần cải thiện một số khía cạnh'
            elif total_score >= 50:
                rating = 'Trung bình'
                color = 'orange'
                interpretation = 'Hiệu quả sản xuất trung bình, cần cải thiện đáng kể'
            else:
                rating = 'Yếu'
                color = 'red'
                interpretation = 'Hiệu quả sản xuất yếu, cần tái cơ cấu và cải thiện'

            return {
                'total': round(total_score, 1),
                'rating': rating,
                'color': color,
                'interpretation': interpretation,
                'components': scores,
                'label': 'Điểm hiệu quả sản xuất'
            }

        except Exception as e:
            logger.error(f"Error calculating efficiency score: {str(e)}")
            return {
                'total': 0,
                'rating': 'N/A',
                'interpretation': 'Không thể tính toán',
                'components': {},
                'label': 'Điểm hiệu quả sản xuất'
            }

    def _missing_metric(self, label: str) -> Dict[str, Any]:
        """Return a missing metric placeholder"""
        return {
            'value': None,
            'rating': 'N/A',
            'label': label,
            'interpretation': 'Không đủ dữ liệu'
        }

    def _get_empty_result(self) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'industry': self.benchmark['label'],
            'metrics': {},
            'ratings': {},
            'efficiency_score': {
                'total': 0,
                'components': {},
                'rating': 'N/A',
                'interpretation': 'Không thể phân tích'
            }
        }


def analyze_manufacturing_company(financial_ratios: Dict[str, Any],
                                  balance_sheet: Dict[str, Any],
                                  income_statement: Dict[str, Any],
                                  cash_flow: Optional[Dict[str, Any]] = None,
                                  industry: str = 'default') -> Dict[str, Any]:
    """
    Convenience function to analyze a manufacturing company

    Args:
        financial_ratios: Dictionary of calculated financial ratios
        balance_sheet: Balance sheet data
        income_statement: Income statement data
        cash_flow: Cash flow statement data (optional)
        industry: Industry type ('steel', 'cement', 'chemicals', 'default')

    Returns:
        Dictionary with all manufacturing metrics and scores
    """
    analyzer = ManufacturingAnalyzer(industry=industry)
    return analyzer.analyze(financial_ratios, balance_sheet, income_statement, cash_flow)
