"""
Core Analysis Engine - Phân tích tài chính cốt lõi

Module này cung cấp các phương pháp phân tích tài chính cơ bản áp dụng cho mọi ngành nghề.
Bao gồm: Piotroski F-Score, Altman Z-Score, CAGR, Chất lượng dòng tiền, Hiệu quả vốn lưu động, và Điểm sức khỏe tổng thể.

Author: Core Analysis Engine
Version: 1.0.0
Date: 2026-02-16
"""

from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
import math

# Import data_contract for standardized calculations
from .data_contract import (
    get_value,
    get_value_safe,
    get_unit,
    safe_divide,
    safe_sum,
    calculate_free_cash_flow,
    COLUMN_ALIASES
)


class CoreAnalysisEngine:
    """
    Engine phân tích tài chính cốt lõi

    Cung cấp các phương pháp phân tích tài chính cơ bản áp dụng cho mọi ngành nghề.

    Accepts flat row data format from API:
        {'year': 2024, 'revenue': 1000, 'net_income': 200, ...}
    """

    def __init__(self, financial_ratios: Dict[str, Any], balance_sheet: Dict[str, Any],
                 income_statement: Dict[str, Any], cash_flow: Dict[str, Any],
                 previous_balance_sheet: Optional[Dict[str, Any]] = None,
                 previous_income_statement: Optional[Dict[str, Any]] = None,
                 previous_cash_flow: Optional[Dict[str, Any]] = None,
                 previous_financial_ratios: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo Core Analysis Engine

        Args:
            financial_ratios: Dict chứa các chỉ số tài chính (flat row format)
            balance_sheet: Dict chứa bảng cân đối kế toán (flat row format)
            income_statement: Dict chứa báo cáo kết quả kinh doanh (flat row format)
            cash_flow: Dict chứa báo cáo dòng tiền (flat row format)
            previous_balance_sheet: Optional previous year balance sheet (flat row format)
            previous_income_statement: Optional previous year income statement (flat row format)
            previous_cash_flow: Optional previous year cash flow (flat row format)
            previous_financial_ratios: Optional previous year financial ratios (flat row format)
        """
        self.financial_ratios = financial_ratios or {}
        self.balance_sheet = balance_sheet or {}
        self.income_statement = income_statement or {}
        self.cash_flow = cash_flow or {}

        # Previous year data for YoY comparisons
        self.previous_balance_sheet = previous_balance_sheet or {}
        self.previous_income_statement = previous_income_statement or {}
        self.previous_cash_flow = previous_cash_flow or {}
        self.previous_financial_ratios = previous_financial_ratios or {}

    def _get_year(self, data: Dict[str, Any]) -> Optional[int]:
        """Extract year from flat row data."""
        year = data.get('year')
        return int(year) if year is not None else None

    # Column name aliases (DB schema vs code expectations) - class level for reuse
    _COLUMN_ALIASES = {
        'total_liabilities': ['liabilities_total'],
        'current_liabilities': ['liabilities_current'],
        'total_equity': ['equity_total'],
        'current_assets': ['asset_current', 'assets_current'],
        'long_term_debt': ['debt_non_current', 'non_current_debt'],
        'short_term_debt': ['debt_current', 'current_debt'],
        'accounts_payable': ['payables'],
        'retained_earnings': ['retained_earnings', 'retained_profit'],
        'operating_profit': ['operating_profit', 'operating_income'],
        'operating_income': ['operating_profit', 'operating_income'],
        'corporate_income_tax': ['corporate_income_tax', 'income_tax_expense', 'tax_expense'],
        'tax_expense': ['corporate_income_tax', 'income_tax_expense'],
        # Prefer net_revenue in DB (non-banks often store revenue as negative credits)
        'revenue': ['net_revenue', 'revenue', 'total_revenue', 'sales'],
        'net_income': ['net_profit', 'net_income', 'profit_after_tax', 'net_profit_parent_company'],
    }

    def _get_aliases(self, key: str) -> List[str]:
        """
        Get list of possible column names for a key.

        Preference order:
        1) Standardized aliases from data_contract.COLUMN_ALIASES (DB-first)
        2) Local fallbacks (_COLUMN_ALIASES)
        3) The code key itself (tests/in-memory dicts)
        """
        candidates: List[str] = []

        # Prefer standardized aliases (DB schema)
        if key in COLUMN_ALIASES:
            candidates.extend(COLUMN_ALIASES[key])

        # Local extra fallbacks (kept for backward compatibility)
        if key in self._COLUMN_ALIASES:
            candidates.extend(self._COLUMN_ALIASES[key])

        # Always try the code key last (tests often use code names directly)
        candidates.append(key)

        # De-duplicate while preserving order
        seen = set()
        ordered: List[str] = []
        for name in candidates:
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered

    def _safe_get(self, data: Dict, key: str, default: float = 0.0) -> float:
        """
        Lấy giá trị từ dict an toàn, xử lý None và chuyển đổi thành float

        Also handles DB column name aliases using _COLUMN_ALIASES.

        Args:
            data: Dict nguồn
            key: Key cần lấy
            default: Giá trị mặc định nếu không tìm thấy hoặc None

        Returns:
            Giá trị float
        """
        # Try all possible column names (key + aliases)
        for alias in self._get_aliases(key):
            value = data.get(alias)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue

        return default

    def calculate_piotroski_f_score(self) -> Dict[str, Any]:
        """
        Tính toán Piotroski F-Score (9 điểm)

        Đánh giá sức khỏe tài chính dựa trên 9 tiêu chí:
        - Khả năng sinh lời (4 điểm): ROA > 0, CFO > 0, ROA cải thiện, CFO > Net Income
        - Đòn bẩy (3 điểm): Nợ/Tài sản giảm, Tài sản lưu động/Tổng nợ ngắn hạn cải thiện, Không phát hành thêm cổ phiếu
        - Hiệu quả (2 điểm): Biên lợi nhuận gộp cải thiện, Vòng quay tài sản cải thiện

        Returns:
            Dict chứa điểm số (0-9), chi tiết từng tiêu chí, và xếp hạng
        """
        score = 0
        details = {}

        # Check if we have basic data
        if not self.income_statement and not self.balance_sheet:
            return {
                'score': 0,
                'rating': 'Không đủ dữ liệu',
                'details': {},
                'vietnamese_rating': 'Không đủ dữ liệu'
            }

        # Get current year data directly from flat rows
        net_income_current = self._safe_get(self.income_statement, 'net_income')
        net_income_prev = self._safe_get(self.previous_income_statement, 'net_income')

        # Cash flow from operations
        cfo_current = self._safe_get(self.cash_flow, 'operating_cash_flow')

        # Total assets
        total_assets_current = self._safe_get(self.balance_sheet, 'total_assets')
        total_assets_prev = self._safe_get(self.previous_balance_sheet, 'total_assets')

        # Gross profit and revenue
        gross_profit_current = self._safe_get(self.income_statement, 'gross_profit')
        gross_profit_prev = self._safe_get(self.previous_income_statement, 'gross_profit')
        # DB may store revenue as negative credits; use magnitude for ratio math
        revenue_current = abs(self._safe_get(self.income_statement, 'revenue'))
        revenue_prev = abs(self._safe_get(self.previous_income_statement, 'revenue'))

        # Long-term debt
        long_term_debt_current = self._safe_get(self.balance_sheet, 'long_term_debt')
        long_term_debt_prev = self._safe_get(self.previous_balance_sheet, 'long_term_debt')

        # Current assets and current liabilities
        current_assets_current = self._safe_get(self.balance_sheet, 'current_assets')
        current_assets_prev = self._safe_get(self.previous_balance_sheet, 'current_assets')
        current_liabilities_current = self._safe_get(self.balance_sheet, 'current_liabilities')
        current_liabilities_prev = self._safe_get(self.previous_balance_sheet, 'current_liabilities')

        # Shares outstanding (if available)
        shares_current = self._safe_get(self.balance_sheet, 'shares_outstanding')
        shares_prev = self._safe_get(self.previous_balance_sheet, 'shares_outstanding')

        # Fallback: use financial_ratios.shares_outstanding_millions if balance sheet doesn't include shares
        # Note: despite the name, DB may store either "millions" (e.g., 1703) or absolute shares (e.g., 1.7e9)
        # Use a heuristic to avoid multiplying already-absolute share counts.
        if shares_current == 0:
            candidate = self.financial_ratios.get('shares_outstanding_millions')
            if candidate is not None:
                try:
                    candidate_f = float(candidate)
                    shares_current = candidate_f if candidate_f > 1_000_000 else candidate_f * 1_000_000
                except (TypeError, ValueError):
                    pass

        if shares_prev == 0:
            candidate = self.previous_financial_ratios.get('shares_outstanding_millions')
            if candidate is not None:
                try:
                    candidate_f = float(candidate)
                    shares_prev = candidate_f if candidate_f > 1_000_000 else candidate_f * 1_000_000
                except (TypeError, ValueError):
                    pass

        # Check if we have previous year data for YoY comparisons
        has_prev_data = bool(self.previous_income_statement or self.previous_balance_sheet)

        # 1. ROA > 0 (Return on Assets positive)
        roa_current = self._safe_get(self.financial_ratios, 'roa')
        if roa_current > 0:
            score += 1
            details['roa_positive'] = 1
        else:
            details['roa_positive'] = 0

        # 2. CFO > 0 (Positive Operating Cash Flow)
        if cfo_current > 0:
            score += 1
            details['cfo_positive'] = 1
        else:
            details['cfo_positive'] = 0

        # 3. ROA improved (Return on Assets improved from previous year)
        if has_prev_data and total_assets_prev > 0:
            # Prefer previous-year ROA from ratios if available (keeps definition consistent)
            roa_prev_ratio = get_value(self.previous_financial_ratios, 'roa')
            roa_prev = float(roa_prev_ratio) if roa_prev_ratio is not None else (net_income_prev / total_assets_prev)
            if roa_current > roa_prev:
                score += 1
                details['roa_improved'] = 1
            else:
                details['roa_improved'] = 0
        else:
            details['roa_improved'] = 0

        # 4. CFO > Net Income (Accruals quality)
        # Vietnam adjustment (documented in methodology):
        # - If Net Income > 0, allow CFO/NI >= 0.8 (instead of strict > 1) due to working-capital dynamics.
        # - If Net Income <= 0, fall back to the classic comparison CFO > Net Income.
        if net_income_current > 0:
            if cfo_current >= 0.8 * net_income_current:
                score += 1
                details['cfo_gt_net_income'] = 1
            else:
                details['cfo_gt_net_income'] = 0
        else:
            if cfo_current > net_income_current:
                score += 1
                details['cfo_gt_net_income'] = 1
            else:
                details['cfo_gt_net_income'] = 0

        # 5. Debt/Assets decreased (Leverage improved)
        if has_prev_data and total_assets_current > 0 and total_assets_prev > 0:
            # Academic definition uses Long-Term Debt / Total Assets.
            # DB may not always have a clean long-term-debt line item, so we fallback
            # to the best available proxy (non-current liabilities, then total liabilities),
            # but only if BOTH years have the same proxy available.
            debt_current = get_value(self.balance_sheet, "long_term_debt", default=None)
            debt_prev = get_value(self.previous_balance_sheet, "long_term_debt", default=None)

            if debt_current is None or debt_prev is None:
                debt_current = get_value(self.balance_sheet, "liabilities_non_current", default=None)
                debt_prev = get_value(self.previous_balance_sheet, "liabilities_non_current", default=None)

            if debt_current is None or debt_prev is None:
                debt_current = get_value(self.balance_sheet, "total_liabilities", default=None)
                debt_prev = get_value(self.previous_balance_sheet, "total_liabilities", default=None)

            if debt_current is None or debt_prev is None:
                details['leverage_improved'] = 0
            else:
                debt_to_assets_current = debt_current / total_assets_current
                debt_to_assets_prev = debt_prev / total_assets_prev
                if debt_to_assets_current < debt_to_assets_prev:
                    score += 1
                    details['leverage_improved'] = 1
                else:
                    details['leverage_improved'] = 0
        else:
            details['leverage_improved'] = 0

        # 6. Current Ratio improved (Liquidity improved)
        if has_prev_data:
            # Prefer ratio-table values when available (statement `liabilities_current` may be incomplete in some DBs).
            cr_current = get_value(self.financial_ratios, "current_ratio", default=None)
            cr_prev = get_value(self.previous_financial_ratios, "current_ratio", default=None)
            if cr_current is not None and cr_prev is not None:
                if cr_current > cr_prev:
                    score += 1
                    details['current_ratio_improved'] = 1
                else:
                    details['current_ratio_improved'] = 0
            else:
                current_ratio_current = current_assets_current / current_liabilities_current if current_liabilities_current > 0 else 0
                current_ratio_prev = current_assets_prev / current_liabilities_prev if current_liabilities_prev > 0 else 0
                if current_ratio_current > current_ratio_prev:
                    score += 1
                    details['current_ratio_improved'] = 1
                else:
                    details['current_ratio_improved'] = 0
        else:
            details['current_ratio_improved'] = 0

        # 7. No new shares issued (Dilution check)
        # Track available criteria for partial scoring
        if has_prev_data and shares_prev > 0 and shares_current > 0:
            if shares_current <= shares_prev:
                score += 1
                details['no_dilution'] = 1
            else:
                details['no_dilution'] = 0
            details['no_dilution_available'] = True
        else:
            # Missing data - don't score, mark as unavailable
            details['no_dilution'] = None
            details['no_dilution_available'] = False

        # 8. Gross Margin improved
        if has_prev_data and revenue_current > 0 and revenue_prev > 0:
            # Prefer ratio-table gross margin if available (more consistent across vendors).
            gm_current = get_value(self.financial_ratios, "gross_margin", default=None)
            gm_prev = get_value(self.previous_financial_ratios, "gross_margin", default=None)
            if gm_current is not None and gm_prev is not None:
                if gm_current > gm_prev:
                    score += 1
                    details['gross_margin_improved'] = 1
                else:
                    details['gross_margin_improved'] = 0
            else:
                gross_margin_current = (gross_profit_current / revenue_current) if revenue_current > 0 else 0
                gross_margin_prev = (gross_profit_prev / revenue_prev) if revenue_prev > 0 else 0
                if gross_margin_current > gross_margin_prev:
                    score += 1
                    details['gross_margin_improved'] = 1
                else:
                    details['gross_margin_improved'] = 0
        else:
            details['gross_margin_improved'] = 0

        # 9. Asset Turnover improved
        if has_prev_data and total_assets_current > 0 and total_assets_prev > 0:
            # Prefer ratio-table asset turnover if available (statement selection + sign conventions can vary).
            at_current = get_value(self.financial_ratios, "asset_turnover", default=None)
            at_prev = get_value(self.previous_financial_ratios, "asset_turnover", default=None)
            if at_current is not None and at_prev is not None:
                if at_current > at_prev:
                    score += 1
                    details['asset_turnover_improved'] = 1
                else:
                    details['asset_turnover_improved'] = 0
            else:
                asset_turnover_current = (revenue_current / total_assets_current) if total_assets_current > 0 else 0
                asset_turnover_prev = (revenue_prev / total_assets_prev) if total_assets_prev > 0 else 0
                if asset_turnover_current > asset_turnover_prev:
                    score += 1
                    details['asset_turnover_improved'] = 1
                else:
                    details['asset_turnover_improved'] = 0
        else:
            details['asset_turnover_improved'] = 0

        # Determine rating (adjusted for partial scoring)
        # Academic note: many criteria require previous-year data. We keep the criterion score as 0
        # when unavailable (backward-compatible), but separately compute "availability" so downstream
        # logic (e.g., early-warning) can avoid over-interpreting a partial F-Score.
        roa_current_val = get_value(self.financial_ratios, "roa", default=None)
        roa_prev_val = get_value(self.previous_financial_ratios, "roa", default=None)
        cfo_current_val = get_value(self.cash_flow, "operating_cash_flow", default=None)
        net_income_current_val = get_value(self.income_statement, "net_income", default=None)

        total_assets_current_val = get_value(self.balance_sheet, "total_assets", default=None)
        total_assets_prev_val = get_value(self.previous_balance_sheet, "total_assets", default=None)

        current_assets_current_val = get_value(self.balance_sheet, "current_assets", default=None)
        current_assets_prev_val = get_value(self.previous_balance_sheet, "current_assets", default=None)
        current_liabilities_current_val = get_value(self.balance_sheet, "current_liabilities", default=None)
        current_liabilities_prev_val = get_value(self.previous_balance_sheet, "current_liabilities", default=None)

        cr_current_val = get_value(self.financial_ratios, "current_ratio", default=None)
        cr_prev_val = get_value(self.previous_financial_ratios, "current_ratio", default=None)
        gm_current_val = get_value(self.financial_ratios, "gross_margin", default=None)
        gm_prev_val = get_value(self.previous_financial_ratios, "gross_margin", default=None)
        at_current_val = get_value(self.financial_ratios, "asset_turnover", default=None)
        at_prev_val = get_value(self.previous_financial_ratios, "asset_turnover", default=None)

        availability = {
            "roa_positive": roa_current_val is not None,
            "cfo_positive": cfo_current_val is not None,
            "roa_improved": bool(
                has_prev_data
                and (roa_current_val is not None)
                and (
                    roa_prev_val is not None
                    or (
                        get_value(self.previous_income_statement, "net_income", default=None) is not None
                        and total_assets_prev_val not in (None, 0)
                    )
                )
            ),
            "cfo_gt_net_income": (cfo_current_val is not None and net_income_current_val is not None),
            "leverage_improved": bool(
                has_prev_data
                and (total_assets_current_val not in (None, 0))
                and (total_assets_prev_val not in (None, 0))
                and (
                    (
                        get_value(self.balance_sheet, "long_term_debt", default=None) is not None
                        and get_value(self.previous_balance_sheet, "long_term_debt", default=None) is not None
                    )
                    or (
                        get_value(self.balance_sheet, "liabilities_non_current", default=None) is not None
                        and get_value(self.previous_balance_sheet, "liabilities_non_current", default=None) is not None
                    )
                    or (
                        get_value(self.balance_sheet, "total_liabilities", default=None) is not None
                        and get_value(self.previous_balance_sheet, "total_liabilities", default=None) is not None
                    )
                )
            ),
            "current_ratio_improved": bool(
                has_prev_data
                and (
                    (cr_current_val is not None and cr_prev_val is not None)
                    or (
                        current_assets_current_val is not None
                        and current_liabilities_current_val not in (None, 0)
                        and current_assets_prev_val is not None
                        and current_liabilities_prev_val not in (None, 0)
                    )
                )
            ),
            "no_dilution": bool(details.get("no_dilution_available")),
            "gross_margin_improved": bool(
                has_prev_data
                and (
                    (gm_current_val is not None and gm_prev_val is not None)
                    or (
                        get_value(self.income_statement, "gross_profit", default=None) is not None
                        and get_value(self.income_statement, "revenue", default=None) not in (None, 0)
                        and get_value(self.previous_income_statement, "gross_profit", default=None) is not None
                        and get_value(self.previous_income_statement, "revenue", default=None) not in (None, 0)
                    )
                )
            ),
            "asset_turnover_improved": bool(
                has_prev_data
                and (
                    (at_current_val is not None and at_prev_val is not None)
                    or (
                        get_value(self.income_statement, "revenue", default=None) is not None
                        and total_assets_current_val not in (None, 0)
                        and get_value(self.previous_income_statement, "revenue", default=None) is not None
                        and total_assets_prev_val not in (None, 0)
                    )
                )
            ),
        }
        criteria_available = sum(1 for v in availability.values() if v)

        if score >= 8:
            rating = 'Very Strong'
            vietnamese_rating = 'Rất mạnh'
        elif score >= 6:
            rating = 'Strong'
            vietnamese_rating = 'Mạnh'
        elif score >= 4:
            rating = 'Average'
            vietnamese_rating = 'Trung bình'
        else:
            rating = 'Weak'
            vietnamese_rating = 'Yếu'

        # Create UI-compatible criteria aliases
        criteria = {
            'roa_positive': details.get('roa_positive'),
            'ocf_positive': details.get('cfo_positive'),  # Alias
            'roa_improving': details.get('roa_improved'),  # Alias
            'ocf_gt_net_income': details.get('cfo_gt_net_income'),  # Same
            'leverage_decreasing': details.get('leverage_improved'),  # Alias
            'current_ratio_increasing': details.get('current_ratio_improved'),  # Alias
            'no_new_shares': details.get('no_dilution'),  # Alias
            'gross_margin_improving': details.get('gross_margin_improved'),  # Alias
            'gross_margin_increasing': details.get('gross_margin_improved'),  # UI-compatible alias
            'asset_turnover_improving': details.get('asset_turnover_improved'),  # Alias
            'asset_turnover_increasing': details.get('asset_turnover_improved')  # UI-compatible alias
        }

        return {
            'score': score,
            'criteria_available': criteria_available,  # For partial scoring display
            'criteria_total': 9,
            'rating': rating,
            'vietnamese_rating': vietnamese_rating,
            'details': details,
            'criteria': criteria,  # UI-friendly aliases
            'interpretation': self._interpret_piotroski_score(score)
        }

    def _interpret_piotroski_score(self, score: int) -> str:
        """
        Diễn giải điểm số Piotroski F-Score

        Args:
            score: Điểm số F-Score (0-9)

        Returns:
            Chuỗi diễn giải tiếng Việt
        """
        interpretations = {
            (8, 9): "Doanh nghiệp có sức khỏe tài chính xuất sắc với khả năng sinh lời mạnh mẽ, "
                    "quản lý đòn bẩy tốt và hiệu quả vận hành cao. Khả năng tiếp tục tăng trưởng và "
                    "tránh được khó khăn tài chính là rất cao.",
            (6, 7): "Doanh nghiệp có sức khỏe tài chính tốt với nhiều yếu tố tích cực. "
                    "Cần theo dõi một số khu vực cần cải thiện nhưng tổng thể vẫn ổn định.",
            (4, 5): "Sức khỏe tài chính ở mức trung bình. Doanh nghiệp có cả điểm mạnh và điểm yếu. "
                    "Cần phân tích kỹ hơn để hiểu rõ các rủi ro và cơ hội.",
            (0, 3): "Doanh nghiệp có sức khỏe tài chính yếu với nhiều vấn đề về khả năng sinh lời, "
                    "đòn bẩy cao hoặc hiệu quả kém. Cần thận trọng khi xem xét đầu tư."
        }

        for (low, high), interpretation in interpretations.items():
            if low <= score <= high:
                return interpretation
        return "Không thể diễn giải"

    def calculate_altman_z_score(self, market_cap: Optional[float] = None) -> Dict[str, Any]:
        """
        Tính toán Altman Z-Score (Cảnh báo phá sản)

        Z = 1.2×(Vốn lưu động/Tổng tài sản) + 1.4×(Lợi nhuận giữ lại/Tổng tài sản) +
            3.3×(EBIT/Tổng tài sản) + 0.6×(Vốn hóa thị trường/Giá trị nợ) + 1.0×(Doanh thu/Tổng tài sản)

        Xếp hạng:
        - Z > 2.99: An toàn (Safe)
        - 1.81 <= Z <= 2.99: Vùng xám (Grey Zone)
        - Z < 1.81: Nguy hiểm (Distress)

        Args:
            market_cap: Vốn hóa thị trường (tùy chọn)

        Returns:
            Dict chứa điểm Z, xếp hạng, và các thành phần
        """
        # Check for data availability - now using flat row format
        if not self.balance_sheet:
            return {
                'z_score': None,
                'rating': 'Không đủ dữ liệu',
                'vietnamese_rating': 'Không đủ dữ liệu',
                'components': {}
            }

        # Check for essential data presence (not just key existence, but actual non-None values)
        # Z-Score requires: total_assets, current_assets/liabilities, retained_earnings, ebit, sales, liabilities
        essential_balance_keys = ['total_assets', 'current_assets', 'current_liabilities',
                                   'retained_earnings', 'total_liabilities']

        # Helper to check if ANY alias has a non-None value
        def has_valid_value(data_dict, key):
            for alias in self._get_aliases(key):
                val = data_dict.get(alias)
                if val is not None and val != '' and val != 0:
                    return True
            return False

        # Count missing essential balance sheet data (None or not present)
        missing_balance = [k for k in essential_balance_keys if not has_valid_value(self.balance_sheet, k)]

        # For income, we can use net_income if operating_profit is missing
        has_revenue = has_valid_value(self.income_statement, 'revenue')
        has_operating_profit = has_valid_value(self.income_statement, 'operating_profit')
        has_net_income = has_valid_value(self.income_statement, 'net_income')

        # If more than half of essential balance sheet data is missing, return insufficient data
        if len(missing_balance) > len(essential_balance_keys) // 2:
            return {
                'z_score': None,
                'rating': 'Không đủ dữ liệu',
                'vietnamese_rating': 'Không đủ dữ liệu',
                'components': {},
                'error': f'Thiếu dữ liệu bảng cân đối: {", ".join(missing_balance)}'
            }

        if not has_revenue:
            return {
                'z_score': None,
                'rating': 'Không đủ dữ liệu',
                'vietnamese_rating': 'Không đủ dữ liệu',
                'components': {},
                'error': 'Thiếu dữ liệu doanh thu'
            }

        if not has_operating_profit and not has_net_income:
            return {
                'z_score': None,
                'rating': 'Không đủ dữ liệu',
                'vietnamese_rating': 'Không đủ dữ liệu',
                'components': {},
                'error': 'Thiếu dữ liệu EBIT/Operating Profit'
            }

        # Lấy dữ liệu trực tiếp từ flat rows
        total_assets = self._safe_get(self.balance_sheet, 'total_assets')
        current_assets = self._safe_get(self.balance_sheet, 'current_assets')
        current_liabilities = self._safe_get(self.balance_sheet, 'current_liabilities')
        retained_earnings = self._safe_get(self.balance_sheet, 'retained_earnings')

        # EBIT (Earnings Before Interest and Taxes) - use operating_profit first (actual DB column)
        ebit = self._safe_get(self.income_statement, 'operating_profit')
        if ebit == 0:
            # If operating profit not available, try operating_income (alias)
            ebit = self._safe_get(self.income_statement, 'operating_income')

        if ebit == 0:
            # If still not available, use net income + interest expense + tax expense
            net_income = self._safe_get(self.income_statement, 'net_income')
            interest_expense = self._safe_get(self.income_statement, 'interest_expense')
            tax_expense = self._safe_get(self.income_statement, 'corporate_income_tax')
            ebit = net_income + interest_expense + tax_expense

        # Book value of debt (total liabilities)
        total_liabilities = self._safe_get(self.balance_sheet, 'total_liabilities')

        # Sales/Revenue
        sales = self._safe_get(self.income_statement, 'revenue')

        # Tính toán các tỷ số thành phần
        if total_assets == 0:
            return {
                'z_score': None,
                'rating': 'Không đủ dữ liệu',
                'vietnamese_rating': 'Không đủ dữ liệu',
                'components': {},
                'error': 'Tổng tài sản bằng 0'
            }

        # X1: Working Capital / Total Assets
        working_capital = current_assets - current_liabilities
        x1 = working_capital / total_assets

        # X2: Retained Earnings / Total Assets
        x2 = retained_earnings / total_assets

        # X3: EBIT / Total Assets
        x3 = ebit / total_assets

        # X4: Market Cap / Book Value of Debt
        if market_cap and total_liabilities > 0:
            x4 = market_cap / total_liabilities
        else:
            # Nếu không có market_cap, sử dụng equity/total_debt như approximation
            equity = self._safe_get(self.balance_sheet, 'total_equity')
            if total_liabilities > 0:
                x4 = equity / total_liabilities
            else:
                x4 = 0

        # X5: Sales / Total Assets
        x5 = sales / total_assets

        # Tính Z-Score
        z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

        # Xếp hạng
        if z_score > 2.99:
            rating = 'Safe'
            vietnamese_rating = 'An toàn'
            interpretation = "Doanh nghiệp có khả năng tài chính mạnh, rủi ro phá sản thấp."
        elif z_score >= 1.81:
            rating = 'Grey Zone'
            vietnamese_rating = 'Vùng xám'
            interpretation = "Doanh nghiệp ở mức trung bình, cần theo dõi chặt chẽ các chỉ số tài chính."
        else:
            rating = 'Distress'
            vietnamese_rating = 'Nguy hiểm'
            interpretation = "Cảnh báo: Doanh nghiệp có rủi ro tài chính cao, có thể gặp khó khăn nghiêm trọng."

        return {
            'z_score': round(z_score, 2),
            # UI/backward-compatible alias fields
            'score': round(z_score, 2),
            'zone': 'safe' if rating == 'Safe' else 'grey' if rating == 'Grey Zone' else 'distress',
            'rating': rating,
            'vietnamese_rating': vietnamese_rating,
            'components': {
                # Full descriptive names
                'working_capital_to_assets': round(x1, 4),
                'retained_earnings_to_assets': round(x2, 4),
                'ebit_to_assets': round(x3, 4),
                'market_cap_to_debt': round(x4, 4),
                'sales_to_assets': round(x5, 4),
                # UI-friendly aliases (x1_, x2_, etc.)
                'x1_working_capital': round(x1, 4),
                'x2_retained_earnings': round(x2, 4),
                'x3_ebit': round(x3, 4),
                'x4_market_cap_debt': round(x4, 4),
                'x5_asset_turnover': round(x5, 4)
            },
            'interpretation': interpretation
        }

    def calculate_cagr(self, metric: str, years: int = 3) -> Dict[str, float]:
        """
        Tính toán CAGR (Compound Annual Growth Rate)

        Formula: (End/Start)^(1/n) - 1

        CRITICAL FIX: Return None for invalid CAGR, NOT 0.
        - Return None if start_value <= 0 (cannot calculate CAGR)
        - Return None if end_value <= 0 (business ceased)
        - Return None if no previous year data
        This distinguishes "no growth data" from "zero/negative growth".

        Args:
            metric: Tên chỉ số cần tính ('revenue', 'net_profit', 'total_assets', 'equity')
            years: Số năm (3, 5, hoặc 10)

        Returns:
            Dict chứa CAGR và các thông tin liên quan
        """
        # With flat row format, we only have single year data
        # CAGR requires multi-year comparison
        if not self.income_statement and not self.balance_sheet:
            return {
                'cagr': None,
                'start_value': None,
                'end_value': None,
                'period_years': years,
                'metric': metric,
                'note': 'Không đủ dữ liệu'
            }

        # Get current value from flat row
        if metric == 'revenue':
            end_value = self._safe_get(self.income_statement, 'revenue')
        elif metric == 'net_profit':
            end_value = self._safe_get(self.income_statement, 'net_income')
        elif metric == 'total_assets':
            end_value = self._safe_get(self.balance_sheet, 'total_assets')
        elif metric == 'equity':
            end_value = self._safe_get(self.balance_sheet, 'total_equity')
        else:
            return {
                'cagr': None,
                'start_value': None,
                'end_value': None,
                'period_years': years,
                'metric': metric,
                'note': 'Metric không hợp lệ'
            }

        # Get previous year value if available
        if metric == 'revenue':
            start_value = self._safe_get(self.previous_income_statement, 'revenue')
        elif metric == 'net_profit':
            start_value = self._safe_get(self.previous_income_statement, 'net_income')
        elif metric == 'total_assets':
            start_value = self._safe_get(self.previous_balance_sheet, 'total_assets')
        elif metric == 'equity':
            start_value = self._safe_get(self.previous_balance_sheet, 'total_equity')
        else:
            start_value = None

        current_year = self._get_year(self.income_statement) or self._get_year(self.balance_sheet)

        # CRITICAL FIX: Check for valid inputs before CAGR calculation
        # Return None (not 0) if inputs are invalid
        if start_value is None or start_value <= 0:
            return {
                'cagr': None,
                'start_value': start_value,
                'end_value': round(end_value, 2) if end_value else None,
                'period_years': years,
                'metric': metric,
                'note': 'Cần dữ liệu nhiều năm để tính CAGR (start_value missing or <= 0)'
            }

        if end_value is None or end_value <= 0:
            return {
                'cagr': None,
                'start_value': round(start_value, 2),
                'end_value': end_value,
                'period_years': years,
                'metric': metric,
                'note': 'Không thể tính CAGR (end_value missing or <= 0)'
            }

        # Calculate CAGR for 1-year period
        # Formula: (end/start)^(1/n) - 1, where n=1 for 1-year comparison
        try:
            cagr = (end_value / start_value) - 1
        except (ZeroDivisionError, TypeError):
            cagr = None

        return {
            'cagr': round(cagr * 100, 2) if cagr is not None else None,
            'start_value': round(start_value, 2),
            'end_value': round(end_value, 2),
            'actual_period_years': 1,
            'requested_period_years': years,
            'metric': metric,
            'start_year': current_year - 1 if current_year else None,
            'end_year': current_year,
            'note': 'CAGR 1 năm (cần dữ liệu nhiều năm cho CAGR chính xác)'
        }

    def calculate_all_cagrs(self) -> Dict[str, Dict[str, float]]:
        """
        Tính toán CAGR cho tất cả các chỉ số chính với các kỳ 3, 5, 10 năm

        Returns:
            Dict chứa CAGR của tất cả các chỉ số
        """
        metrics = ['revenue', 'net_profit', 'total_assets', 'equity']
        periods = [3, 5, 10]

        results = {}
        for metric in metrics:
            results[metric] = {}
            for period in periods:
                cagr_data = self.calculate_cagr(metric, period)
                results[metric][f'{period}_year'] = cagr_data

        return results

    def calculate_cash_flow_quality_score(self) -> Dict[str, Any]:
        """
        Tính toán điểm chất lượng dòng tiền

        Các yếu tố đánh giá:
        1. Tỷ lệ OCF/Net Income (lý tưởng > 1)
        2. Tỷ lệ FCF/Net Income
        3. Tính nhất quán của OCF (số năm dương) - requires previous year data

        Returns:
            Dict chứa các chỉ số chất lượng dòng tiền và điểm số
        """
        if not self.cash_flow or not self.income_statement:
            return {
                'overall_score': None,
                'rating': 'Không đủ dữ liệu',
                'ocf_to_net_income': None,
                'fcf_to_net_income': None,
                'ocf_consistency_years': 0,
                'total_years': 0
            }

        # Get data directly from flat rows
        ocf = self._safe_get(self.cash_flow, 'operating_cash_flow')
        net_income = self._safe_get(self.income_statement, 'net_income')

        # FCF (Free Cash Flow = OCF - Capital Expenditures)
        # CRITICAL FIX: CapEx in DB is typically negative (cash outflow)
        # Always subtract absolute value: FCF = OCF - |CapEx|
        capex = self._safe_get(self.cash_flow, 'capital_expenditure')
        fcf = ocf - abs(capex) if capex is not None else None

        # OCF to Net Income ratio
        ocf_to_ni = (ocf / net_income) if net_income != 0 else None

        # FCF to Net Income ratio
        fcf_to_ni = (fcf / net_income) if net_income != 0 else None

        # OCF Consistency - count positive OCF (current + previous if available)
        positive_ocf_years = 0
        total_years = 0

        if ocf > 0:
            positive_ocf_years += 1
        total_years += 1

        # Check previous year if available
        if self.previous_cash_flow:
            prev_ocf = self._safe_get(self.previous_cash_flow, 'operating_cash_flow')
            if prev_ocf > 0:
                positive_ocf_years += 1
            total_years += 1

        # Calculate overall quality score (0-100)
        score_components = []

        # Component 1: OCF/Net Income (max 40 points)
        if ocf_to_ni is not None and ocf_to_ni > 0:
            if ocf_to_ni >= 1.2:
                score_components.append(40)
            elif ocf_to_ni >= 1.0:
                score_components.append(35)
            elif ocf_to_ni >= 0.8:
                score_components.append(25)
            elif ocf_to_ni >= 0.5:
                score_components.append(15)
            else:
                score_components.append(5)

        # Component 2: FCF/Net Income (max 30 points)
        if fcf_to_ni is not None and fcf_to_ni > 0:
            if fcf_to_ni >= 1.0:
                score_components.append(30)
            elif fcf_to_ni >= 0.8:
                score_components.append(25)
            elif fcf_to_ni >= 0.5:
                score_components.append(15)
            elif fcf_to_ni >= 0.3:
                score_components.append(8)
            else:
                score_components.append(3)

        # Component 3: OCF Consistency (max 30 points)
        if total_years > 0:
            consistency_ratio = positive_ocf_years / total_years
            consistency_score = consistency_ratio * 30
            score_components.append(consistency_score)

        overall_score = sum(score_components) if score_components else None

        # Rating
        if overall_score is not None:
            if overall_score >= 80:
                rating = 'Rất tốt'
                english_rating = 'Excellent'
            elif overall_score >= 60:
                rating = 'Tốt'
                english_rating = 'Good'
            elif overall_score >= 40:
                rating = 'Trung bình'
                english_rating = 'Average'
            elif overall_score >= 20:
                rating = 'Yếu'
                english_rating = 'Weak'
            else:
                rating = 'Rất yếu'
                english_rating = 'Very Weak'
        else:
            rating = 'Không đủ dữ liệu'
            english_rating = 'Insufficient Data'

        return {
            'overall_score': round(overall_score, 1) if overall_score is not None else None,
            # UI/backward-compatible alias
            'score': round(overall_score, 1) if overall_score is not None else None,
            'rating': rating,
            'vietnamese_rating': rating,
            'english_rating': english_rating,
            'ocf_to_net_income': round(ocf_to_ni, 2) if ocf_to_ni is not None else None,
            'fcf_to_net_income': round(fcf_to_ni, 2) if fcf_to_ni is not None else None,
            # Nested metrics for UI cards
            'metrics': {
                'ocf_to_net_income': round(ocf_to_ni, 2) if ocf_to_ni is not None else None,
                'fcf_to_net_income': round(fcf_to_ni, 2) if fcf_to_ni is not None else None,
            },
            'ocf_consistency_years': positive_ocf_years,
            'total_years': total_years,
            'interpretation': self._interpret_cash_flow_quality(overall_score, ocf_to_ni, fcf_to_ni)
        }

    def _interpret_cash_flow_quality(self, score: Optional[float],
                                    ocf_to_ni: Optional[float],
                                    fcf_to_ni: Optional[float]) -> str:
        """
        Diễn giải chất lượng dòng tiền

        Args:
            score: Điểm chất lượng tổng thể
            ocf_to_ni: Tỷ lệ OCF/Net Income
            fcf_to_ni: Tỷ lệ FCF/Net Income

        Returns:
            Chuỗi diễn giải tiếng Việt
        """
        if score is None:
            return "Không đủ dữ liệu để đánh giá chất lượng dòng tiền."

        interpretation_parts = []

        if ocf_to_ni is not None:
            if ocf_to_ni >= 1.0:
                interpretation_parts.append(
                    f"Dòng tiền từ hoạt động kinh doanh vượt trội so với lợi nhuận ({ocf_to_ni:.2f}x), "
                    "cho thấy chất lượng lợi nhuận cao và chuyển đổi tốt từ lợi nhuận kế toán sang tiền mặt."
                )
            elif ocf_to_ni >= 0.8:
                interpretation_parts.append(
                    f"Dòng tiền từ hoạt động kinh doanh ở mức tốt ({ocf_to_ni:.2f}x so với lợi nhuận), "
                    "cho thấy chuyển đổi lợi nhuận thành tiền mặt khá hiệu quả."
                )
            elif ocf_to_ni > 0:
                interpretation_parts.append(
                    f"Dòng tiền từ hoạt động kinh doanh thấp hơn lợi nhuận ({ocf_to_ni:.2f}x), "
                    "có thể do tăng trưởng vốn lưu động hoặc chi phí không tiền mặt cao."
                )

        if fcf_to_ni is not None:
            if fcf_to_ni >= 0.8:
                interpretation_parts.append(
                    f"Dòng tiền tự do mạnh mẽ ({fcf_to_ni:.2f}x so với lợi nhuận), "
                    "doanh nghiệp có dư địa để đầu tư, trả nợ hoặc trả cổ tức."
                )
            elif fcf_to_ni > 0:
                interpretation_parts.append(
                    f"Dòng tiền tự bằng dương ({fcf_to_ni:.2f}x so với lợi nhuận), "
                    "nhưng cần cân đối giữa đầu tư và duy trì dòng tiền."
                )
            else:
                interpretation_parts.append(
                    f"Dòng tiền tự bằng âm, doanh nghiệp đang đầu tư mạnh cho mở rộng "
                    "hoặc gặp áp lực về vốn lưu động."
                )

        return " ".join(interpretation_parts) if interpretation_parts else "Không đủ dữ liệu để diễn giải."

    def calculate_working_capital_efficiency(self) -> Dict[str, Any]:
        """
        Tính toán hiệu quả vốn lưu động

        Các chỉ số:
        1. Cash Conversion Cycle (CCC) = DSO + DIO - DPO
        2. Days Sales Outstanding (DSO) - Số ngày thu tiền
        3. Days Inventory Outstanding (DIO) - Số ngày hàng tồn kho
        4. Days Payable Outstanding (DPO) - Số ngày trả tiền nhà cung cấp

        CRITICAL FIX: Use correct formula with proper null handling.
        - DSO = (Accounts Receivable / Revenue) * 365
        - DIO = (Inventory / COGS) * 365
        - DPO = (Accounts Payable / COGS) * 365
        - CCC = DSO + DIO - DPO
        - Return None (not 0) for invalid calculations

        Returns:
            Dict chứa các chỉ số hiệu quả vốn lưu động
        """
        # Check for data - now using flat row format
        if not self.income_statement or not self.balance_sheet:
            return {
                'ccc': None,
                'dso': None,
                'dio': None,
                'dpo': None,
                'rating': 'Không đủ dữ liệu'
            }

        # Get necessary data directly from flat rows
        # Use data_contract.get_value() here to preserve None for missing inputs
        # (important for DBs where some working-capital line items are not available)
        revenue = get_value(self.income_statement, 'revenue')
        if revenue is not None and revenue < 0:
            # DB may store revenue as negative credits; use magnitude for day-metrics
            revenue = abs(revenue)

        cogs = get_value(self.income_statement, 'cost_of_goods_sold')
        if cogs is not None:
            # COGS is often stored as negative expense in DB; use magnitude
            cogs = abs(cogs)

        accounts_receivable = get_value(self.balance_sheet, 'accounts_receivable')
        inventory = get_value(self.balance_sheet, 'inventory')
        accounts_payable = get_value(self.balance_sheet, 'accounts_payable')

        # Calculate metrics (assuming 365 days)
        days_per_year = 365

        # DSO: Days Sales Outstanding
        # CRITICAL: Return None if revenue is 0 or missing
        dso = None
        if revenue is not None and revenue > 0 and accounts_receivable is not None:
            dso = (accounts_receivable / revenue) * days_per_year

        # DIO: Days Inventory Outstanding
        # CRITICAL: Return None if COGS is 0 or missing
        dio = None
        if cogs is not None and cogs > 0 and inventory is not None:
            dio = (inventory / cogs) * days_per_year

        # DPO: Days Payable Outstanding
        # CRITICAL: Return None if COGS is 0 or missing
        dpo = None
        if cogs is not None and cogs > 0 and accounts_payable is not None:
            dpo = (accounts_payable / cogs) * days_per_year

        # CCC: Cash Conversion Cycle
        # CRITICAL: Only calculate CCC if all components are available
        ccc = None
        if all([dso is not None, dio is not None, dpo is not None]):
            ccc = dso + dio - dpo

        # Rating based on CCC (industry-dependent, but general guidelines)
        if ccc is not None:
            if ccc < 30:
                rating = 'Xuất sắc'
                english_rating = 'Excellent'
            elif ccc < 60:
                rating = 'Tốt'
                english_rating = 'Good'
            elif ccc < 90:
                rating = 'Trung bình'
                english_rating = 'Average'
            elif ccc < 120:
                rating = 'Cần cải thiện'
                english_rating = 'Needs Improvement'
            else:
                rating = 'Kém'
                english_rating = 'Poor'
        else:
            rating = 'Không đủ dữ liệu'
            english_rating = 'Insufficient Data'

        return {
            'ccc': round(ccc, 1) if ccc is not None else None,
            'dso': round(dso, 1) if dso is not None else None,
            'dio': round(dio, 1) if dio is not None else None,
            'dpo': round(dpo, 1) if dpo is not None else None,
            'rating': rating,
            'vietnamese_rating': rating,
            'english_rating': english_rating,
            'interpretation': self._interpret_working_capital_efficiency(ccc, dso, dio, dpo)
        }

    def _interpret_working_capital_efficiency(self, ccc: Optional[float],
                                            dso: Optional[float],
                                            dio: Optional[float],
                                            dpo: Optional[float]) -> str:
        """
        Diễn giải hiệu quả vốn lưu động

        Args:
            ccc: Cash Conversion Cycle
            dso: Days Sales Outstanding
            dio: Days Inventory Outstanding
            dpo: Days Payable Outstanding

        Returns:
            Chuỗi diễn giải tiếng Việt
        """
        if ccc is None:
            return "Không đủ dữ liệu để đánh giá hiệu quả vốn lưu động."

        parts = []

        # CCC interpretation
        if ccc < 30:
            parts.append(
                f"Vòng chuyển đổi tiền mặt xuất sắc ({ccc:.1f} ngày), "
                "doanh nghiệp thu tiền rất nhanh và quản lý vốn lưu động hiệu quả."
            )
        elif ccc < 60:
            parts.append(
                f"Vòng chuyển đổi tiền mặt tốt ({ccc:.1f} ngày), "
                "quản lý vốn lưu động ở mức hiệu quả."
            )
        elif ccc < 90:
            parts.append(
                f"Vòng chuyển đổi tiền mặt trung bình ({ccc:.1f} ngày), "
                "cần tối ưu hóa vòng quay vốn lưu động."
            )
        else:
            parts.append(
                f"Vòng chuyển đổi tiền mặt chậm ({ccc:.1f} ngày), "
                "doanh nghiệp cần rà soát lại quy trình thu tiền và quản lý tồn kho."
            )

        # DSO interpretation
        if dso is not None:
            if dso < 45:
                parts.append(f"Thu tiền khách hàng nhanh ({dso:.1f} ngày).")
            elif dso < 60:
                parts.append(f"Thời gian thu tiền ở mức chấp nhận được ({dso:.1f} ngày).")
            else:
                parts.append(f"Thời gian thu tiền chậm ({dso:.1f} ngày), cần tightening credit policy.")

        # DIO interpretation
        if dio is not None:
            if dio < 60:
                parts.append(f"Quản lý tồn kho tốt ({dio:.1f} ngày).")
            elif dio < 90:
                parts.append(f"Tồn kho ở mức trung bình ({dio:.1f} ngày).")
            else:
                parts.append(f"Tồn kho cao ({dio:.1f} ngày), cần tối ưu hóa quản lý kho.")

        # DPO interpretation
        if dpo is not None:
            if dpo > 60:
                parts.append(f"Tận dụng tốt credit term từ nhà cung cấp ({dpo:.1f} ngày).")
            else:
                parts.append(f"Có thể tối ưu hóa thời gian trả tiền nhà cung cấp ({dpo:.1f} ngày).")

        return " ".join(parts)

    def calculate_overall_health_score(self) -> Dict[str, Any]:
        """
        Tính toán điểm sức khỏe tổng thể (phiên bản cải tiến)

        Thành phần:
        1. Điểm sinh lời (30%): ROE, ROA, Biên lợi nhuận ròng
        2. Điểm hiệu quả (25%): Vòng quay tài sản, Vòng quay tồn kho
        3. Điểm đòn bẩy (25%): Nợ/Vốn chủ sở hữu, Khả năng thanh toán lãi vay
        4. Điểm thanh khoản (20%): Tỷ thanh toán hiện hành, Tỷ thanh toán nhanh

        Returns:
            Dict chứa điểm tổng thể và các thành phần chi tiết
        """
        # Extract ratios from financial_ratios
        # IMPORTANT: preserve None for missing/non-applicable metrics (e.g., banks often have no inventory turnover).
        roe = get_value(self.financial_ratios, 'roe', default=None)
        roa = get_value(self.financial_ratios, 'roa', default=None)
        net_margin = get_value(self.financial_ratios, 'net_profit_margin', default=None)

        asset_turnover = get_value(self.financial_ratios, 'asset_turnover', default=None)
        inventory_turnover = get_value(self.financial_ratios, 'inventory_turnover', default=None)

        debt_to_equity = get_value(self.financial_ratios, 'debt_to_equity', default=None)
        interest_coverage = get_value(self.financial_ratios, 'interest_coverage', default=None)

        # Data fix: DB may store interest coverage with wrong sign when interest expense is negative.
        # If we can recompute a proxy from statements, prefer that (keeps negative if EBIT is negative).
        try:
            ebit = get_value(self.income_statement, 'operating_profit')
            financial_expense = get_value(self.income_statement, 'financial_expense')
            if ebit is not None and financial_expense is not None and financial_expense != 0:
                computed_coverage = ebit / abs(financial_expense)
                if interest_coverage is None or interest_coverage == 0 or (interest_coverage < 0 and computed_coverage > 0):
                    interest_coverage = computed_coverage
        except Exception:
            # Keep the ratio-table value if recomputation fails
            pass

        current_ratio = get_value(self.financial_ratios, 'current_ratio', default=None)
        quick_ratio = get_value(self.financial_ratios, 'quick_ratio', default=None)

        # Calculate component scores

        # 1. Profitability Score (30%)
        profitability_score = self._calculate_profitability_score(roe, roa, net_margin)

        # 2. Efficiency Score (25%)
        efficiency_score = self._calculate_efficiency_score(asset_turnover, inventory_turnover)

        # 3. Leverage Score (25%)
        leverage_score = self._calculate_leverage_score(debt_to_equity, interest_coverage)

        # 4. Liquidity Score (20%)
        liquidity_score = self._calculate_liquidity_score(current_ratio, quick_ratio)

        # Calculate overall score
        overall_score = (
            profitability_score * 0.30 +
            efficiency_score * 0.25 +
            leverage_score * 0.25 +
            liquidity_score * 0.20
        )

        # Determine rating
        if overall_score >= 80:
            rating = 'Rất mạnh'
            english_rating = 'Very Strong'
            color = 'green'
        elif overall_score >= 60:
            rating = 'Mạnh'
            english_rating = 'Strong'
            color = 'blue'
        elif overall_score >= 40:
            rating = 'Trung bình'
            english_rating = 'Average'
            color = 'yellow'
        elif overall_score >= 20:
            rating = 'Yếu'
            english_rating = 'Weak'
            color = 'orange'
        else:
            rating = 'Rất yếu'
            english_rating = 'Very Weak'
            color = 'red'

        return {
            'overall_score': round(overall_score, 1),
            'rating': rating,
            'vietnamese_rating': rating,
            'english_rating': english_rating,
            'color': color,
            'components': {
                'profitability': {
                    'score': round(profitability_score, 1),
                    'weight': 0.30,
                    'weighted_score': round(profitability_score * 0.30, 1),
                    'metrics': {
                        'roe': roe,
                        'roa': roa,
                        'net_margin': net_margin
                    }
                },
                'efficiency': {
                    'score': round(efficiency_score, 1),
                    'weight': 0.25,
                    'weighted_score': round(efficiency_score * 0.25, 1),
                    'metrics': {
                        'asset_turnover': asset_turnover,
                        'inventory_turnover': inventory_turnover
                    }
                },
                'leverage': {
                    'score': round(leverage_score, 1),
                    'weight': 0.25,
                    'weighted_score': round(leverage_score * 0.25, 1),
                    'metrics': {
                        'debt_to_equity': debt_to_equity,
                        'interest_coverage': interest_coverage
                    }
                },
                'liquidity': {
                    'score': round(liquidity_score, 1),
                    'weight': 0.20,
                    'weighted_score': round(liquidity_score * 0.20, 1),
                    'metrics': {
                        'current_ratio': current_ratio,
                        'quick_ratio': quick_ratio
                    }
                }
            },
            'interpretation': self._interpret_health_score(overall_score, rating)
        }

    def _calculate_profitability_score(
        self,
        roe: Optional[float],
        roa: Optional[float],
        net_margin: Optional[float],
    ) -> float:
        """
        Tính điểm sinh lời (0-100)

        CRITICAL FIX: Normalize decimal vs percent correctly.
        - DB stores ratios as decimals: 0.20 = 20%
        - Do NOT multiply by 100 - thresholds already in decimal format
        - Ensure consistent decimal handling across all metrics

        Args:
            roe: Return on Equity (decimal format: 0.20 = 20%)
            roa: Return on Assets (decimal format: 0.10 = 10%)
            net_margin: Net Profit Margin (decimal format: 0.15 = 15%)

        Returns:
            Điểm sinh lời (0-100)
        """
        score = 0
        count = 0

        # ROE scoring (decimal format: 0.20 = 20%)
        if roe is not None:
            if roe >= 0.20:  # >= 20%
                score += 40
            elif roe >= 0.15:  # >= 15%
                score += 32
            elif roe >= 0.10:  # >= 10%
                score += 24
            elif roe >= 0.05:  # >= 5%
                score += 16
            elif roe >= 0:
                score += 8
            else:
                score += 0
            count += 1

        # ROA scoring (decimal format: 0.10 = 10%)
        if roa is not None:
            if roa >= 0.10:  # >= 10%
                score += 35
            elif roa >= 0.07:  # >= 7%
                score += 28
            elif roa >= 0.05:  # >= 5%
                score += 21
            elif roa >= 0.03:  # >= 3%
                score += 14
            elif roa >= 0:
                score += 7
            else:
                score += 0
            count += 1

        # Net Margin scoring (decimal format: 0.15 = 15%)
        if net_margin is not None:
            if net_margin >= 0.15:  # >= 15%
                score += 25
            elif net_margin >= 0.10:  # >= 10%
                score += 20
            elif net_margin >= 0.05:  # >= 5%
                score += 15
            elif net_margin >= 0.02:  # >= 2%
                score += 10
            elif net_margin >= 0:
                score += 5
            else:
                score += 0
            count += 1

        return (score / count) if count > 0 else 0

    def _calculate_efficiency_score(
        self,
        asset_turnover: Optional[float],
        inventory_turnover: Optional[float],
    ) -> float:
        """
        Tính điểm hiệu quả (0-100)

        Args:
            asset_turnover: Vòng quay tài sản
            inventory_turnover: Vòng quay tồn kho

        Returns:
            Điểm hiệu quả (0-100)
        """
        score = 0
        count = 0

        # Asset Turnover scoring
        if asset_turnover is not None:
            if asset_turnover <= 0:
                score += 0
            elif asset_turnover >= 1.5:
                score += 50
            elif asset_turnover >= 1.2:
                score += 40
            elif asset_turnover >= 1.0:
                score += 30
            elif asset_turnover >= 0.8:
                score += 20
            else:
                score += 10
            count += 1

        # Inventory Turnover scoring
        if inventory_turnover is not None:
            if inventory_turnover <= 0:
                score += 0
            elif inventory_turnover >= 10:
                score += 50
            elif inventory_turnover >= 7:
                score += 40
            elif inventory_turnover >= 5:
                score += 30
            elif inventory_turnover >= 3:
                score += 20
            else:
                score += 10
            count += 1

        return (score / count) if count > 0 else 0

    def _calculate_leverage_score(
        self,
        debt_to_equity: Optional[float],
        interest_coverage: Optional[float],
    ) -> float:
        """
        Tính điểm đòn bẩy (0-100)

        Args:
            debt_to_equity: Nợ/Vốn chủ sở hữu
            interest_coverage: Khả năng thanh toán lãi vay

        Returns:
            Điểm đòn bẩy (0-100)
        """
        score = 0
        count = 0

        # Debt-to-Equity scoring (lower is better)
        if debt_to_equity is not None:
            # Negative D/E usually means negative equity -> high risk.
            if debt_to_equity < 0:
                score += 0
            elif debt_to_equity <= 0.5:
                score += 50
            elif debt_to_equity <= 1.0:
                score += 40
            elif debt_to_equity <= 1.5:
                score += 30
            elif debt_to_equity <= 2.0:
                score += 20
            else:
                score += 10
            count += 1

        # Interest Coverage scoring (higher is better)
        if interest_coverage is not None:
            if interest_coverage <= 0:
                score += 0
            elif interest_coverage >= 5:
                score += 50
            elif interest_coverage >= 3:
                score += 40
            elif interest_coverage >= 2:
                score += 30
            elif interest_coverage >= 1.5:
                score += 20
            else:
                score += 10
            count += 1

        return (score / count) if count > 0 else 0

    def _calculate_liquidity_score(
        self,
        current_ratio: Optional[float],
        quick_ratio: Optional[float],
    ) -> float:
        """
        Tính điểm thanh khoản (0-100)

        Args:
            current_ratio: Tỷ thanh toán hiện hành
            quick_ratio: Tỷ thanh toán nhanh

        Returns:
            Điểm thanh khoản (0-100)
        """
        score = 0
        count = 0

        # Current Ratio scoring
        if current_ratio is not None:
            if current_ratio <= 0:
                score += 0
            elif current_ratio >= 2.0:
                score += 50
            elif current_ratio >= 1.5:
                score += 40
            elif current_ratio >= 1.2:
                score += 30
            elif current_ratio >= 1.0:
                score += 20
            else:
                score += 10
            count += 1

        # Quick Ratio scoring
        if quick_ratio is not None:
            if quick_ratio <= 0:
                score += 0
            elif quick_ratio >= 1.5:
                score += 50
            elif quick_ratio >= 1.2:
                score += 40
            elif quick_ratio >= 1.0:
                score += 30
            elif quick_ratio >= 0.8:
                score += 20
            else:
                score += 10
            count += 1

        return (score / count) if count > 0 else 0

    def _interpret_health_score(self, score: float, rating: str) -> str:
        """
        Diễn giải điểm sức khỏe tổng thể

        Args:
            score: Điểm số (0-100)
            rating: Xếp hạng

        Returns:
            Chuỗi diễn giải tiếng Việt
        """
        if score >= 80:
            return (
                f"Doanh nghiệp có sức khỏe tài chính rất mạnh ({score:.1f}/100). "
                "Khả năng sinh lời cao, quản lý hiệu quả, đòn bẩy an toàn và thanh khoản tốt. "
                "Vị thế tài chính vững chắc để tiếp tục phát triển và vượt qua biến động thị trường."
            )
        elif score >= 60:
            return (
                f"Doanh nghiệp có sức khỏe tài chính mạnh ({score:.1f}/100). "
                "Nhiều chỉ số tài chính ở mức tốt, cần duy trì và cải thiện thêm một số khu vực "
                "để nâng cao hiệu quả hoạt động."
            )
        elif score >= 40:
            return (
                f"Doanh nghiệp có sức khỏe tài chính trung bình ({score:.1f}/100). "
                "Có cả điểm mạnh và điểm yếu. Cần tập trung cải thiện các khu vực yếu kém "
                "để nâng cao vị thế tài chính."
            )
        elif score >= 20:
            return (
                f"Doanh nghiệp có sức khỏe tài chính yếu ({score:.1f}/100). "
                "Nhiều chỉ số tài chính ở mức thấp, cần có kế hoạch tái cấu trúc và cải thiện mạnh mẽ "
                "để tránh rủi ro tài chính."
            )
        else:
            return (
                f"Doanh nghiệp có sức khỏe tài chính rất yếu ({score:.1f}/100). "
                "Cảnh báo: Rủi ro tài chính cao, cần đánh giá lại chiến lược kinh doanh "
                "và có biện pháp khắc phục ngay lập tức."
            )

    def generate_comprehensive_report(self, market_cap: Optional[float] = None) -> Dict[str, Any]:
        """
        Tạo báo cáo phân tích toàn diện

        Args:
            market_cap: Vốn hóa thị trường (tùy chọn, cho Altman Z-Score)

        Returns:
            Dict chứa tất cả các phân tích
        """
        report = {
            'piotroski_f_score': self.calculate_piotroski_f_score(),
            'altman_z_score': self.calculate_altman_z_score(market_cap),
            'cagr_analysis': self.calculate_all_cagrs(),
            'cash_flow_quality': self.calculate_cash_flow_quality_score(),
            'working_capital_efficiency': self.calculate_working_capital_efficiency(),
            'overall_health_score': self.calculate_overall_health_score()
        }

        return report


# Convenience functions for direct usage
def analyze_core_financials(financial_ratios: Dict[str, Any],
                           balance_sheet: Dict[str, Any],
                           income_statement: Dict[str, Any],
                           cash_flow: Dict[str, Any],
                           market_cap: Optional[float] = None,
                           previous_balance_sheet: Optional[Dict[str, Any]] = None,
                           previous_income_statement: Optional[Dict[str, Any]] = None,
                           previous_cash_flow: Optional[Dict[str, Any]] = None,
                           previous_financial_ratios: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Hàm tiện ích để phân tích tài chính cốt lõi

    Args:
        financial_ratios: Dict chứa các chỉ số tài chính (flat row format)
        balance_sheet: Dict chứa bảng cân đối kế toán (flat row format)
        income_statement: Dict chứa báo cáo kết quả kinh doanh (flat row format)
        cash_flow: Dict chứa báo cáo dòng tiền (flat row format)
        market_cap: Vốn hóa thị trường (tùy chọn)
        previous_balance_sheet: Optional previous year balance sheet (flat row format)
        previous_income_statement: Optional previous year income statement (flat row format)
        previous_cash_flow: Optional previous year cash flow (flat row format)
        previous_financial_ratios: Optional previous year financial ratios (flat row format)

    Returns:
        Dict chứa tất cả các phân tích cốt lõi
    """
    engine = CoreAnalysisEngine(
        financial_ratios, balance_sheet, income_statement, cash_flow,
        previous_balance_sheet, previous_income_statement, previous_cash_flow,
        previous_financial_ratios
    )
    return engine.generate_comprehensive_report(market_cap)
