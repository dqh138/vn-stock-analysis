"""
Pharmaceutical Industry Analysis Module
Analyzes pharmaceutical companies with industry-specific metrics including:
- Gross margin analysis (branded vs generic mix)
- R&D intensity and innovation capability
- SG&A efficiency and marketing effectiveness
- Inventory management (expiry risk)
- Working capital efficiency (hospital payment cycles)
- Distribution network quality

Focus on Vietnamese pharmaceutical market characteristics.
"""

from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PharmaceuticalAnalyzer:
    """Analyzes pharmaceutical companies with industry-specific metrics"""

    def __init__(self):
        """Initialize pharmaceutical analyzer with Vietnamese market benchmarks"""
        self.vietnamese_market_benchmarks = {
            'branded_gross_margin': (40, 60),  # (%)
            'generic_gross_margin': (20, 35),  # (%)
            'rd_ratio_international': (10, 20),  # (% of revenue)
            'rd_ratio_vietnamese': (0.5, 2),  # (% of revenue)
            'sga_ratio_typical': (15, 30),  # (% of revenue)
            'sga_ratio_efficient': 20,  # (%)
            'dio_excellent': 90,  # days
            'dio_good': 150,  # days
            'net_margin_excellent': 12,  # (%)
            'net_margin_good': 8,  # (%)
            'roe_strong': 15,  # (%)
            'roa_strong': 10,  # (%)
            'dso_hospital_slow': 90,  # days (hospitals pay slowly)
        }

    def analyze(self,
                financial_ratios: Optional[Dict[str, Any]],
                balance_sheet: Optional[Dict[str, Any]],
                income_statement: Optional[Dict[str, Any]],
                cash_flow: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform comprehensive pharmaceutical analysis

        Args:
            financial_ratios: Dict with pre-calculated financial ratios
            balance_sheet: Dict with balance sheet data
            income_statement: Dict with income statement data
            cash_flow: Dict with cash flow statement data

        Returns:
            Dict with all pharmaceutical metrics, ratings, and quality score
        """

        # Extract key metrics
        metrics = self._extract_metrics(financial_ratios, balance_sheet, income_statement, cash_flow)

        # Calculate pharmaceutical-specific metrics
        gross_margin_analysis = self._analyze_gross_margin(metrics)
        rd_analysis = self._analyze_rd_intensity(metrics)
        sga_analysis = self._analyze_sga_efficiency(metrics)
        inventory_analysis = self._analyze_inventory_management(metrics)
        profitability_analysis = self._analyze_profitability(metrics)
        return_analysis = self._analyze_returns(metrics)
        working_capital_analysis = self._analyze_working_capital(metrics)
        distribution_analysis = self._analyze_distribution_network(metrics)

        # Calculate quality score
        quality_score = self._calculate_quality_score({
            'gross_margin': gross_margin_analysis,
            'rd': rd_analysis,
            'sga': sga_analysis,
            'inventory': inventory_analysis,
            'profitability': profitability_analysis,
            'returns': return_analysis,
            'working_capital': working_capital_analysis,
            'distribution': distribution_analysis,
        }, metrics)

        return {
            'metrics': metrics,
            'gross_margin_analysis': gross_margin_analysis,
            'rd_analysis': rd_analysis,
            'sga_analysis': sga_analysis,
            'inventory_analysis': inventory_analysis,
            'profitability_analysis': profitability_analysis,
            'return_analysis': return_analysis,
            'working_capital_analysis': working_capital_analysis,
            'distribution_analysis': distribution_analysis,
            'quality_score': quality_score,
            'recommendations': self._generate_recommendations({
                'gross_margin': gross_margin_analysis,
                'rd': rd_analysis,
                'sga': sga_analysis,
                'inventory': inventory_analysis,
                'profitability': profitability_analysis,
                'returns': return_analysis,
                'working_capital': working_capital_analysis,
                'distribution': distribution_analysis,
            })
        }

    def _extract_metrics(self,
                        financial_ratios: Optional[Dict[str, Any]],
                        balance_sheet: Optional[Dict[str, Any]],
                        income_statement: Optional[Dict[str, Any]],
                        cash_flow: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract key financial metrics from input data"""

        metrics = {}

        # From financial ratios
        if financial_ratios:
            metrics['gross_margin'] = financial_ratios.get('gross_margin')
            metrics['net_margin'] = financial_ratios.get('net_margin')
            metrics['roe'] = financial_ratios.get('roe')
            metrics['roa'] = financial_ratios.get('roa')
            metrics['current_ratio'] = financial_ratios.get('current_ratio')
            metrics['quick_ratio'] = financial_ratios.get('quick_ratio')

            # Working capital metrics
            metrics['dso'] = financial_ratios.get('days_sales_outstanding')
            metrics['dio'] = financial_ratios.get('days_inventory_outstanding')
            metrics['dpo'] = financial_ratios.get('days_payable_outstanding')
            metrics['cash_conversion_cycle'] = financial_ratios.get('cash_conversion_cycle')

            # Growth rates
            metrics['revenue_growth'] = financial_ratios.get('revenue_growth')
            metrics['net_income_growth'] = financial_ratios.get('net_income_growth')

        # From income statement
        if income_statement:
            # Get values for current and previous year
            current = income_statement.get('current', {})
            previous = income_statement.get('previous', {})

            metrics['revenue'] = current.get('revenue') or current.get('total_revenue')
            metrics['cogs'] = current.get('cost_of_goods_sold') or current.get('cogs')
            metrics['sga'] = current.get('selling_general_administrative') or current.get('sga_expenses')
            metrics['rd_expenses'] = current.get('research_development') or current.get('rd_expenses')
            metrics['net_income'] = current.get('net_income')

            # Previous year for trend analysis
            prev_revenue = previous.get('revenue') or previous.get('total_revenue')
            prev_cogs = previous.get('cost_of_goods_sold') or previous.get('cogs')
            prev_sga = previous.get('selling_general_administrative') or previous.get('sga_expenses')
            prev_net_income = previous.get('net_income')

            metrics['prev_revenue'] = prev_revenue
            metrics['prev_cogs'] = prev_cogs
            metrics['prev_sga'] = prev_sga
            metrics['prev_net_income'] = prev_net_income

            # Calculate growth if not provided
            if metrics.get('revenue_growth') is None and metrics.get('revenue') and prev_revenue:
                metrics['revenue_growth'] = ((metrics['revenue'] - prev_revenue) / prev_revenue) * 100

            # Calculate gross margin if not provided
            if metrics.get('gross_margin') is None and metrics.get('revenue') and metrics.get('cogs'):
                metrics['gross_margin'] = ((metrics['revenue'] - metrics['cogs']) / metrics['revenue']) * 100

            # Calculate net margin if not provided
            if metrics.get('net_margin') is None and metrics.get('revenue') and metrics.get('net_income'):
                metrics['net_margin'] = (metrics['net_income'] / metrics['revenue']) * 100

        # From balance sheet
        if balance_sheet:
            current = balance_sheet.get('current', {})

            metrics['inventory'] = current.get('inventory')
            metrics['total_assets'] = current.get('total_assets')
            metrics['total_equity'] = current.get('total_equity')
            metrics['accounts_receivable'] = current.get('accounts_receivable') or current.get('trade_receivables')
            metrics['accounts_payable'] = current.get('accounts_payable') or current.get('trade_payables')

        # From cash flow
        if cash_flow:
            current = cash_flow.get('current', {})
            metrics['operating_cash_flow'] = current.get('operating_cash_flow') or current.get('cash_from_operating_activities')

        # Calculate derived metrics
        self._calculate_derived_metrics(metrics)

        return metrics

    def _calculate_derived_metrics(self, metrics: Dict[str, Any]) -> None:
        """Calculate derived pharmaceutical metrics"""

        # R&D/Revenue ratio
        if metrics.get('rd_expenses') and metrics.get('revenue'):
            metrics['rd_ratio'] = (metrics['rd_expenses'] / metrics['revenue']) * 100

        # SG&A/Revenue ratio
        if metrics.get('sga') and metrics.get('revenue'):
            metrics['sga_ratio'] = (metrics['sga'] / metrics['revenue']) * 100

        # Previous year ratios for trend
        if metrics.get('prev_revenue') and metrics.get('prev_cogs'):
            metrics['prev_gross_margin'] = ((metrics['prev_revenue'] - metrics['prev_cogs']) / metrics['prev_revenue']) * 100

        if metrics.get('prev_revenue') and metrics.get('prev_net_income'):
            metrics['prev_net_margin'] = (metrics['prev_net_income'] / metrics['prev_revenue']) * 100

        # Gross margin trend
        if metrics.get('gross_margin') and metrics.get('prev_gross_margin'):
            metrics['gross_margin_trend'] = metrics['gross_margin'] - metrics['prev_gross_margin']

        # SG&A growth vs Revenue growth
        if metrics.get('sga') and metrics.get('prev_sga') and metrics.get('prev_revenue'):
            sga_growth = ((metrics['sga'] - metrics['prev_sga']) / metrics['prev_sga']) * 100
            revenue_growth = metrics.get('revenue_growth', 0)
            metrics['sga_vs_revenue_growth'] = sga_growth - revenue_growth

    def _analyze_gross_margin(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze gross margin to determine product mix (branded vs generic)"""

        gross_margin = metrics.get('gross_margin')

        if gross_margin is None:
            return {
                'value': None,
                'rating': 'unknown',
                'label': 'Biên lợi nhuận gộp',
                'assessment': 'Không có dữ liệu',
                'interpretation': 'Không thể xác định cơ cấu sản phẩm',
                'score': 0
            }

        # Determine product mix based on gross margin
        if gross_margin >= 40:
            mix_type = 'branded_dominant'
            assessment = 'Tỷ lệ thương hiệu mạnh'
            interpretation = 'Công ty tập trung vào sản phẩm thương hiệu với biên lợi nhuận cao, có định vị giá tốt'
            score = 100
        elif gross_margin >= 25:
            mix_type = 'balanced'
            assessment = 'Cân bằng thương hiệu - generic'
            interpretation = 'Công ty có cơ cấu sản phẩm cân bằng giữa thuốc thương hiệu và generic'
            score = 70
        else:
            mix_type = 'generic_commodity'
            assessment = 'Tỷ lệ generic cao'
            interpretation = 'Công ty chủ yếu tập trung vào thuốc generic với biên lợi nhuận thấp, cạnh tranh về giá'
            score = 40

        return {
            'value': round(gross_margin, 2),
            'rating': mix_type,
            'label': 'Biên lợi nhuận gộp',
            'assessment': assessment,
            'interpretation': interpretation,
            'score': score,
            'vietnamese_benchmark': 'Thương hiệu: 40-60%, Generic: 20-35%'
        }

    def _analyze_rd_intensity(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze R&D intensity as indicator of innovation capability"""

        rd_ratio = metrics.get('rd_ratio')

        if rd_ratio is None:
            return {
                'value': None,
                'rating': 'unknown',
                'label': 'Tỷ lệ chi phí R&D',
                'assessment': 'Không có dữ liệu',
                'interpretation': 'Không thể đánh giá năng lực đổi mới',
                'score': 0
            }

        # Vietnamese pharma typically has low R&D
        if rd_ratio >= 5:
            level = 'very_high'
            assessment = 'R&D rất cao'
            interpretation = 'Mức đầu tư R&D cao hơn nhiều so với trung bình ngành dược Việt Nam, tiềm năng đổi mới lớn'
            score = 100
        elif rd_ratio >= 2:
            level = 'high'
            assessment = 'R&D cao'
            interpretation = 'Đầu tư R&D tốt, có khả năng phát triển sản phẩm mới'
            score = 80
        elif rd_ratio >= 1:
            level = 'moderate'
            assessment = 'R&D trung bình'
            interpretation = 'Đầu tư R&D ở mức trung bình cho doanh nghiệp dược Việt Nam'
            score = 60
        else:
            level = 'low'
            assessment = 'R&D thấp'
            interpretation = 'Đầu tư R&D thấp, chủ yếu sản xuất generic hoặc mua bán nguyên liệu'
            score = 30

        return {
            'value': round(rd_ratio, 2),
            'rating': level,
            'label': 'Tỷ lệ chi phí R&D / Doanh thu (%)',
            'assessment': assessment,
            'interpretation': interpretation,
            'score': score,
            'vietnamese_benchmark': 'Việt Nam: < 2%, Quốc tế: 10-20%'
        }

    def _analyze_sga_efficiency(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze SG&A efficiency (marketing and distribution costs)"""

        sga_ratio = metrics.get('sga_ratio')

        if sga_ratio is None:
            return {
                'value': None,
                'rating': 'unknown',
                'label': 'Tỷ lệ chi phí bán hàng & quản lý',
                'assessment': 'Không có dữ liệu',
                'interpretation': 'Không thể đánh giá hiệu quả marketing',
                'score': 0
            }

        # Analyze SG&A efficiency
        if sga_ratio <= 20:
            efficiency = 'excellent'
            assessment = 'Rất hiệu quả'
            interpretation = 'Chi phí marketing và phân phối được kiểm soát tốt, hiệu quả cao'
            score = 100
        elif sga_ratio <= 30:
            efficiency = 'normal'
            assessment = 'Bình thường'
            interpretation = 'Chi phí marketing và phân phối ở mức bình thường cho ngành dược'
            score = 70
        else:
            efficiency = 'high'
            assessment = 'Chi phí cao'
            interpretation = 'Chi phí marketing và phân phối cao, cần tối ưu hóa để cải thiện biên lợi nhuận'
            score = 40

        return {
            'value': round(sga_ratio, 2),
            'rating': efficiency,
            'label': 'Tỷ lệ SG&A / Doanh thu (%)',
            'assessment': assessment,
            'interpretation': interpretation,
            'score': score,
            'vietnamese_benchmark': 'Tiêu chuẩn: 15-30%, Hiệu quả: < 20%'
        }

    def _analyze_inventory_management(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze inventory management - critical in pharma due to expiry risk"""

        dio = metrics.get('dio')  # Days Inventory Outstanding

        if dio is None:
            return {
                'value': None,
                'rating': 'unknown',
                'label': 'Ngày tồn kho',
                'assessment': 'Không có dữ liệu',
                'interpretation': 'Không thể đánh giá rủi ro hết hạn',
                'score': 0
            }

        # Analyze inventory turnover
        if dio <= 90:
            management = 'excellent'
            assessment = 'Quản lý xuất sắc'
            interpretation = 'Xoay vòng tồn kho nhanh, rủi ro hết hạn thấp, hiệu quả cao'
            score = 100
        elif dio <= 150:
            management = 'good'
            assessment = 'Quản lý tốt'
            interpretation = 'Xoay vòng tồn kho ở mức tốt, kiểm soát được rủi ro hết hạn'
            score = 75
        elif dio <= 210:
            management = 'acceptable'
            assessment = 'Chấp nhận được'
            interpretation = 'Xoay vòng tồn kho chậm, có rủi ro hết hạn cần theo dõi'
            score = 50
        else:
            management = 'risky'
            assessment = 'Rủi ro cao'
            interpretation = 'Tồn kho xoay vòng chậm, rủi ro hết hạn lớn, có thể ảnh hưởng lợi nhuận'
            score = 20

        return {
            'value': round(dio, 1),
            'rating': management,
            'label': 'Ngày tồn kho (DIO)',
            'assessment': assessment,
            'interpretation': interpretation,
            'score': score,
            'vietnamese_benchmark': 'Xuất sắc: < 90 ngày, Tốt: 90-150 ngày',
            'expiry_risk': 'low' if dio <= 90 else 'medium' if dio <= 150 else 'high'
        }

    def _analyze_profitability(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze net margin"""

        net_margin = metrics.get('net_margin')

        if net_margin is None:
            return {
                'value': None,
                'rating': 'unknown',
                'label': 'Biên lợi nhuận ròng',
                'assessment': 'Không có dữ liệu',
                'score': 0
            }

        # Analyze net margin
        if net_margin >= 12:
            level = 'excellent'
            assessment = 'Xuất sắc'
            interpretation = 'Khả năng sinh lời tốt, quản lý chi phí hiệu quả'
            score = 100
        elif net_margin >= 8:
            level = 'good'
            assessment = 'Tốt'
            interpretation = 'Khả năng sinh lời ở mức tốt'
            score = 75
        elif net_margin >= 4:
            level = 'acceptable'
            assessment = 'Chấp nhận được'
            interpretation = 'Khả năng sinh lời ở mức trung bình, có cải thiện'
            score = 50
        else:
            level = 'low'
            assessment = 'Thấp'
            interpretation = 'Khả năng sinh lời thấp, cần xem lại chiến lược giá và chi phí'
            score = 25

        return {
            'value': round(net_margin, 2),
            'rating': level,
            'label': 'Biên lợi nhuận ròng (%)',
            'assessment': assessment,
            'interpretation': interpretation,
            'score': score,
            'vietnamese_benchmark': 'Xuất sắc: > 12%, Tốt: 8-12%'
        }

    def _analyze_returns(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze ROE and ROA - pharma is capital-light so should have high returns"""

        roe = metrics.get('roe')
        roa = metrics.get('roa')

        if roe is None and roa is None:
            return {
                'roe': None,
                'roa': None,
                'rating': 'unknown',
                'assessment': 'Không có dữ liệu',
                'score': 0
            }

        # Analyze ROE
        if roe is not None:
            if roe >= 15:
                roe_level = 'excellent'
                roe_score = 100
            elif roe >= 10:
                roe_level = 'good'
                roe_score = 75
            elif roe >= 5:
                roe_level = 'acceptable'
                roe_score = 50
            else:
                roe_level = 'low'
                roe_score = 25
        else:
            roe_level = 'unknown'
            roe_score = 0

        # Analyze ROA
        if roa is not None:
            if roa >= 10:
                roa_level = 'excellent'
                roa_score = 100
            elif roa >= 6:
                roa_level = 'good'
                roa_score = 75
            elif roa >= 3:
                roa_level = 'acceptable'
                roa_score = 50
            else:
                roa_level = 'low'
                roa_score = 25
        else:
            roa_level = 'unknown'
            roa_score = 0

        # Overall rating
        overall_score = (roe_score + roa_score) / 2 if roe_score > 0 and roa_score > 0 else max(roe_score, roa_score)

        if overall_score >= 75:
            assessment = 'Hiệu quả sử dụng vốn xuất sắc'
            interpretation = 'Doanh nghiệp vốn nhẹ, sinh lời cao trên vốn đầu tư'
        elif overall_score >= 50:
            assessment = 'Hiệu quả sử dụng vốn tốt'
            interpretation = 'Sinh lời tốt trên vốn đầu tư'
        elif overall_score >= 25:
            assessment = 'Hiệu quả sử dụng vốn trung bình'
            interpretation = 'Sinh lời ở mức trung bình'
        else:
            assessment = 'Hiệu quả sử dụng vốn thấp'
            interpretation = 'Cần cải thiện hiệu quả sử dụng vốn'

        return {
            'roe': round(roe, 2) if roe is not None else None,
            'roa': round(roa, 2) if roa is not None else None,
            'roe_rating': roe_level,
            'roa_rating': roa_level,
            'rating': 'excellent' if overall_score >= 75 else 'good' if overall_score >= 50 else 'acceptable' if overall_score >= 25 else 'low',
            'assessment': assessment,
            'interpretation': interpretation,
            'score': overall_score,
            'vietnamese_benchmark': 'ROE mạnh: > 15%, ROA mạnh: > 10%'
        }

    def _analyze_working_capital(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze working capital efficiency - critical for pharma due to hospital payment cycles"""

        dso = metrics.get('dso')  # Days Sales Outstanding
        dpo = metrics.get('dpo')  # Days Payable Outstanding
        ccc = metrics.get('cash_conversion_cycle')  # Cash Conversion Cycle

        if dso is None and ccc is None:
            return {
                'dso': None,
                'dpo': None,
                'ccc': None,
                'rating': 'unknown',
                'assessment': 'Không có dữ liệu',
                'score': 0
            }

        # Analyze DSO (hospitals pay slowly in Vietnam)
        dso_score = 0
        dso_assessment = ''
        if dso is not None:
            if dso <= 60:
                dso_assessment = 'Thu tiền nhanh'
                dso_score = 100
            elif dso <= 90:
                dso_assessment = 'Thu tiền ở mức tốt'
                dso_score = 75
            elif dso <= 120:
                dso_assessment = 'Thu tiền chậm'
                dso_score = 50
            else:
                dso_assessment = 'Thu tiền rất chậm'
                dso_score = 25

        # Analyze Cash Conversion Cycle
        ccc_score = 0
        ccc_assessment = ''
        if ccc is not None:
            if ccc <= 30:
                ccc_assessment = 'Xuất sắc'
                ccc_score = 100
            elif ccc <= 60:
                ccc_assessment = 'Tốt'
                ccc_score = 75
            elif ccc <= 90:
                ccc_assessment = 'Chấp nhận được'
                ccc_score = 50
            else:
                ccc_assessment = 'Chậm'
                ccc_score = 25

        # Overall working capital efficiency
        overall_score = (dso_score + ccc_score) / 2 if dso_score > 0 and ccc_score > 0 else max(dso_score, ccc_score)

        if overall_score >= 75:
            assessment = 'Quản lý vốn lưu động xuất sắc'
            interpretation = 'Tự do dòng tiền tốt, không áp lực thanh khoản'
        elif overall_score >= 50:
            assessment = 'Quản lý vốn lưu động tốt'
            interpretation = 'Tự do dòng tiền ở mức tốt'
        elif overall_score >= 25:
            assessment = 'Quản lý vốn lưu động trung bình'
            interpretation = 'Cần cải thiện tốc độ thu tiền'
        else:
            assessment = 'Quản lý vốn lưu động kém'
            interpretation = 'Chu kỳ tiền mặt dài, áp lực thanh khoản cao'

        return {
            'dso': round(dso, 1) if dso is not None else None,
            'dpo': round(dpo, 1) if dpo is not None else None,
            'ccc': round(ccc, 1) if ccc is not None else None,
            'dso_assessment': dso_assessment,
            'ccc_assessment': ccc_assessment,
            'rating': 'excellent' if overall_score >= 75 else 'good' if overall_score >= 50 else 'acceptable' if overall_score >= 25 else 'poor',
            'assessment': assessment,
            'interpretation': interpretation,
            'score': overall_score,
            'vietnamese_benchmark': 'DSO bệnh viện: ~90 ngày, CCC tốt: < 60 ngày'
        }

    def _analyze_distribution_network(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze distribution network quality through SG&A efficiency and revenue growth"""

        sga_vs_revenue = metrics.get('sga_vs_revenue_growth')
        revenue_growth = metrics.get('revenue_growth')
        sga_ratio = metrics.get('sga_ratio')

        if sga_vs_revenue is None and revenue_growth is None:
            return {
                'rating': 'unknown',
                'assessment': 'Không có dữ liệu',
                'score': 0
            }

        # Analyze distribution efficiency
        score = 50
        assessment_parts = []

        # Check if SG&A growth is justified by revenue growth
        if sga_vs_revenue is not None:
            if sga_vs_revenue < 0:
                # SG&A growing slower than revenue = efficient
                score = 100
                assessment_parts.append('Mở rộng kênh phân phối hiệu quả')
            elif sga_vs_revenue < 5:
                # SG&A growing slightly faster than revenue = acceptable
                score = 75
                assessment_parts.append('Mở rộng kênh phân phối ở mức chấp nhận')
            else:
                # SG&A growing much faster than revenue = inefficient
                score = 40
                assessment_parts.append('Chi phí mở rộng kênh phân phối cao')

        # Check revenue growth
        if revenue_growth is not None:
            if revenue_growth >= 15:
                growth_assessment = 'Tăng trưởng doanh thu mạnh'
                score = min(score + 20, 100)
            elif revenue_growth >= 8:
                growth_assessment = 'Tăng trưởng doanh thu tốt'
                score = min(score + 10, 100)
            elif revenue_growth >= 0:
                growth_assessment = 'Tăng trưởng doanh thu chậm'
                score = max(score - 10, 0)
            else:
                growth_assessment = 'Doanh thu giảm'
                score = max(score - 30, 0)

            assessment_parts.append(growth_assessment)

        # Check SG&A ratio level
        if sga_ratio is not None:
            if sga_ratio <= 20:
                assessment_parts.append('Chi phí phân phối thấp')
            elif sga_ratio <= 30:
                assessment_parts.append('Chi phí phân phối ở mức trung bình')
            else:
                assessment_parts.append('Chi phí phân phối cao')

        assessment = '. '.join(assessment_parts) if assessment_parts else 'Không thể đánh giá'

        if score >= 80:
            interpretation = 'Mạng lưới phân phối mạnh và hiệu quả'
        elif score >= 60:
            interpretation = 'Mạng lưới phân phối tốt'
        elif score >= 40:
            interpretation = 'Mạng lưới phân phối ở mức trung bình'
        else:
            interpretation = 'Cần cải thiện hiệu quả mạng lưới phân phối'

        return {
            'sga_vs_revenue_growth': round(sga_vs_revenue, 2) if sga_vs_revenue is not None else None,
            'revenue_growth': round(revenue_growth, 2) if revenue_growth is not None else None,
            'sga_ratio': round(sga_ratio, 2) if sga_ratio is not None else None,
            'rating': 'excellent' if score >= 80 else 'good' if score >= 60 else 'acceptable' if score >= 40 else 'poor',
            'assessment': assessment,
            'interpretation': interpretation,
            'score': score
        }

    def _calculate_quality_score(self, analyses: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall pharmaceutical quality score"""

        # Weight breakdown
        # Profitability (35%): Gross Margin, Net Margin, ROE
        profitability_score = (
            analyses['gross_margin']['score'] * 0.4 +
            analyses['profitability_analysis']['score'] * 0.3 +
            analyses['returns']['score'] * 0.3
        )

        # Product Mix (25%): Gross Margin level, R&D intensity
        product_mix_score = (
            analyses['gross_margin']['score'] * 0.6 +
            analyses['rd']['score'] * 0.4
        )

        # Operations (25%): Inventory management, Working Capital
        operations_score = (
            analyses['inventory']['score'] * 0.5 +
            analyses['working_capital']['score'] * 0.5
        )

        # Growth (15%): Revenue growth, Margin trend
        growth_score = analyses['distribution']['score']  # Uses revenue growth

        # Calculate weighted overall score
        overall_score = (
            profitability_score * 0.35 +
            product_mix_score * 0.25 +
            operations_score * 0.25 +
            growth_score * 0.15
        )

        # Determine rating
        if overall_score >= 80:
            rating = 'excellent'
            vietnamese_rating = 'Xuất sắc'
            description = 'Công ty dược phẩm chất lượng cao với sản phẩm thương hiệu mạnh, quản lý tồn kho tốt và khả năng sinh lời xuất sắc'
        elif overall_score >= 65:
            rating = 'good'
            vietnamese_rating = 'Tốt'
            description = 'Công ty dược phẩm tốt với cân bằng sản phẩm và hoạt động hiệu quả'
        elif overall_score >= 50:
            rating = 'acceptable'
            vietnamese_rating = 'Chấp nhận được'
            description = 'Công ty dược phẩm ở mức trung bình, có điểm cần cải thiện'
        elif overall_score >= 35:
            rating = 'weak'
            vietnamese_rating = 'Yếu'
            description = 'Công ty dược phẩm có nhiều điểm yếu cần chú ý'
        else:
            rating = 'poor'
            vietnamese_rating = 'Kém'
            description = 'Công ty dược phẩm kém chất lượng, rủi ro cao'

        return {
            'overall_score': round(overall_score, 1),
            'rating': rating,
            'vietnamese_rating': vietnamese_rating,
            'description': description,
            'breakdown': {
                'profitability': {
                    'score': round(profitability_score, 1),
                    'weight': 35,
                    'components': {
                        'gross_margin': analyses['gross_margin']['score'],
                        'net_margin': analyses['profitability_analysis']['score'],
                        'returns': analyses['returns']['score']
                    }
                },
                'product_mix': {
                    'score': round(product_mix_score, 1),
                    'weight': 25,
                    'components': {
                        'gross_margin_mix': analyses['gross_margin']['score'],
                        'rd_intensity': analyses['rd']['score']
                    }
                },
                'operations': {
                    'score': round(operations_score, 1),
                    'weight': 25,
                    'components': {
                        'inventory': analyses['inventory']['score'],
                        'working_capital': analyses['working_capital']['score']
                    }
                },
                'growth': {
                    'score': round(growth_score, 1),
                    'weight': 15,
                    'components': {
                        'distribution': analyses['distribution']['score']
                    }
                }
            }
        }

    def _generate_recommendations(self, analyses: Dict[str, Any]) -> list:
        """Generate actionable recommendations based on analysis"""

        recommendations = []

        # Gross margin recommendations
        if analyses['gross_margin']['score'] < 60:
            recommendations.append({
                'priority': 'high',
                'area': 'Cơ cấu sản phẩm',
                'recommendation': 'Tăng tỷ lệ sản phẩm thương hiệu để cải thiện biên lợi nhuận',
                'action': 'Phát triển sản phẩm độc quyền hoặc nhượng quyền, giảm tỷ lệ generic thuần túy'
            })

        # R&D recommendations
        if analyses['rd']['score'] < 60:
            recommendations.append({
                'priority': 'medium',
                'area': 'Đổi mới sáng tạo',
                'recommendation': 'Tăng đầu tư R&D để phát triển sản phẩm mới',
                'action': 'Dành 2-5% doanh thu cho R&D, tập trung vào sản phẩm biệt dược gốc hoặc dạng bào chế mới'
            })

        # SG&A recommendations
        if analyses['sga']['score'] < 60:
            recommendations.append({
                'priority': 'medium',
                'area': 'Hiệu quả chi phí',
                'recommendation': 'Tối ưu hóa chi phí marketing và phân phối',
                'action': 'Đánh giá hiệu quả các kênh phân phối, tập trung vào kênh hiệu quả nhất'
            })

        # Inventory recommendations
        if analyses['inventory']['score'] < 70:
            recommendations.append({
                'priority': 'high' if analyses['inventory']['score'] < 50 else 'medium',
                'area': 'Quản lý tồn kho',
                'recommendation': 'Cải thiện quản lý tồn kho để giảm rủi ro hết hạn',
                'action': 'Triển khai hệ thống dự báo nhu cầu tốt hơn, giảm tồn kho chậm xoay vòng'
            })

        # Working capital recommendations
        if analyses['working_capital']['score'] < 60:
            recommendations.append({
                'priority': 'high',
                'area': 'Vốn lưu động',
                'recommendation': 'Cải thiện tốc độ thu tiền từ khách hàng',
                'action': 'Thắt chặt chính sách tín dụng, đàm phán thanh toán nhanh hơn với bệnh viện'
            })

        # Profitability recommendations
        if analyses['profitability_analysis']['score'] < 60:
            recommendations.append({
                'priority': 'high',
                'area': 'Khả năng sinh lời',
                'recommendation': 'Cải thiện biên lợi nhuận ròng',
                'action': 'Tăng giá sản phẩm thương hiệu, kiểm soát chi phí, tối ưu hóa cơ cấu sản phẩm'
            })

        # Return recommendations
        if analyses['returns']['score'] < 60:
            recommendations.append({
                'priority': 'medium',
                'area': 'Hiệu quả vốn',
                'recommendation': 'Cải thiện hiệu quả sử dụng vốn',
                'action': 'Tối ưu hóa cơ cấu vốn, giảm tài sản kém hiệu quả'
            })

        # Distribution recommendations
        if analyses['distribution']['score'] < 60:
            recommendations.append({
                'priority': 'medium',
                'area': 'Mạng lưới phân phối',
                'recommendation': 'Nâng cao hiệu quả mạng lưới phân phối',
                'action': 'Tập trung vào kênh phân phối hiệu quả, loại bỏ kênh kém hiệu quả'
            })

        return recommendations


def analyze_pharmaceutical_company(
    financial_ratios: Optional[Dict[str, Any]],
    balance_sheet: Optional[Dict[str, Any]],
    income_statement: Optional[Dict[str, Any]],
    cash_flow: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convenience function to analyze a pharmaceutical company

    Args:
        financial_ratios: Dict with pre-calculated financial ratios
        balance_sheet: Dict with balance sheet data
        income_statement: Dict with income statement data
        cash_flow: Dict with cash flow statement data

    Returns:
        Dict with comprehensive pharmaceutical analysis

    Example:
        >>> result = analyze_pharmaceutical_company(
        ...     financial_ratios={'gross_margin': 45, 'net_margin': 12, 'roe': 18},
        ...     balance_sheet={'current': {'inventory': 100, 'total_assets': 500}},
        ...     income_statement={'current': {'revenue': 1000, 'cogs': 550, 'sga_expenses': 200}},
        ...     cash_flow=None
        ... )
        >>> print(result['quality_score']['overall_score'])
    """

    analyzer = PharmaceuticalAnalyzer()
    return analyzer.analyze(financial_ratios, balance_sheet, income_statement, cash_flow)


if __name__ == '__main__':
    # Example usage with sample data
    sample_ratios = {
        'gross_margin': 42,
        'net_margin': 11,
        'roe': 16,
        'roa': 8,
        'days_inventory_outstanding': 85,
        'days_sales_outstanding': 75,
        'days_payable_outstanding': 60,
        'cash_conversion_cycle': 100,
        'revenue_growth': 12
    }

    sample_balance_sheet = {
        'current': {
            'inventory': 150000,
            'total_assets': 800000,
            'total_equity': 400000
        }
    }

    sample_income_statement = {
        'current': {
            'revenue': 1000000,
            'cost_of_goods_sold': 580000,
            'selling_general_administrative': 180000,
            'research_development': 15000,
            'net_income': 110000
        },
        'previous': {
            'revenue': 892857,
            'cost_of_goods_sold': 517143,
            'selling_general_administrative': 160714,
            'net_income': 96429
        }
    }

    result = analyze_pharmaceutical_company(
        sample_ratios,
        sample_balance_sheet,
        sample_income_statement,
        None
    )

    print("Pharmaceutical Analysis Results:")
    print(f"Quality Score: {result['quality_score']['overall_score']}/100")
    print(f"Rating: {result['quality_score']['vietnamese_rating']}")
    print(f"\nGross Margin: {result['gross_margin_analysis']['assessment']}")
    print(f"R&D Intensity: {result['rd_analysis']['assessment']}")
    print(f"Inventory Management: {result['inventory_analysis']['assessment']}")
    print(f"Profitability: {result['profitability_analysis']['assessment']}")

    print("\nRecommendations:")
    for rec in result['recommendations']:
        print(f"- [{rec['priority'].upper()}] {rec['area']}: {rec['recommendation']}")
