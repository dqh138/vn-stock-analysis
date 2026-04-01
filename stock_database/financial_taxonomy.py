from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Metric:
    id: str
    group: str
    label: str
    unit: str
    description: str
    statement: Optional[str] = None
    section: Optional[str] = None


GROUPS: Dict[str, Dict[str, str]] = {
    "market": {"label_vi": "Thị trường", "note": "Quy mô/biến động giá/đầu vào định giá"},
    "valuation": {"label_vi": "Định giá", "note": "Bội số định giá (multiples)"},
    "profitability": {"label_vi": "Sinh lời", "note": "Biên lợi nhuận và ROE/ROA/ROIC"},
    "leverage": {"label_vi": "Đòn bẩy", "note": "Cấu trúc vốn và sức chịu nợ"},
    "liquidity": {"label_vi": "Thanh khoản", "note": "Khả năng thanh toán ngắn hạn"},
    "efficiency": {"label_vi": "Hiệu quả vận hành", "note": "Vòng quay và chu kỳ tiền mặt"},
    "payout": {"label_vi": "Cổ tức", "note": "Chính sách trả cổ tức"},
    "scale": {"label_vi": "Quy mô (absolute)", "note": "Số tuyệt đối (không phải ratio)"},
    "risk": {"label_vi": "Rủi ro", "note": "Độ nhạy thị trường"},
    # Statements (line-items)
    "assets": {"label_vi": "Tài sản", "note": "Balance sheet assets"},
    "liabilities": {"label_vi": "Nợ phải trả", "note": "Balance sheet liabilities"},
    "equity": {"label_vi": "Vốn chủ", "note": "Balance sheet equity"},
    "income": {"label_vi": "Thu nhập", "note": "Income statement income"},
    "expense": {"label_vi": "Chi phí", "note": "Income statement expenses"},
    "profit": {"label_vi": "Lợi nhuận", "note": "Income statement profit lines"},
    "tax": {"label_vi": "Thuế", "note": "Income statement taxes"},
    "per_share": {"label_vi": "Trên mỗi cổ phiếu", "note": "Per-share items"},
    "growth": {"label_vi": "Tăng trưởng", "note": "Growth rates"},
    "cashflow_operating": {"label_vi": "LCTT HĐKD", "note": "Cash flow from operating activities"},
    "cashflow_investing": {"label_vi": "LCTT Đầu tư", "note": "Cash flow from investing activities"},
    "cashflow_financing": {"label_vi": "LCTT Tài chính", "note": "Cash flow from financing activities"},
    "cash": {"label_vi": "Tiền", "note": "Cash & cash equivalents"},
    "noncash_adjustment": {"label_vi": "Điều chỉnh phi tiền", "note": "Non-cash adjustments (cash flow)"},
    "working_capital": {"label_vi": "Vốn lưu động", "note": "Working capital changes (cash flow)"},
}


FINANCIAL_RATIOS_METRICS: Dict[str, Metric] = {
    # Market / scale inputs
    "market_cap_billions": Metric(
        id="market_cap_billions",
        group="market",
        label="Market Cap",
        unit="tỷ VND",
        description="Vốn hoá thị trường (ước tính, đơn vị tỷ VND)",
        statement="financial_ratios",
    ),
    "shares_outstanding_millions": Metric(
        id="shares_outstanding_millions",
        group="market",
        label="Shares Outstanding",
        unit="triệu cp",
        description="Số lượng cổ phiếu lưu hành (triệu cổ phiếu)",
        statement="financial_ratios",
    ),
    "beta": Metric(
        id="beta",
        group="risk",
        label="Beta",
        unit="x",
        description="Độ nhạy giá so với thị trường (beta)",
        statement="financial_ratios",
    ),
    # Valuation
    "price_to_earnings": Metric(
        id="price_to_earnings",
        group="valuation",
        label="P/E",
        unit="x",
        description="Giá / Lợi nhuận (P/E)",
        statement="financial_ratios",
    ),
    "price_to_book": Metric(
        id="price_to_book",
        group="valuation",
        label="P/B",
        unit="x",
        description="Giá / Giá trị sổ sách (P/B)",
        statement="financial_ratios",
    ),
    "price_to_sales": Metric(
        id="price_to_sales",
        group="valuation",
        label="P/S",
        unit="x",
        description="Giá / Doanh thu (P/S)",
        statement="financial_ratios",
    ),
    "price_to_cash_flow": Metric(
        id="price_to_cash_flow",
        group="valuation",
        label="P/CF",
        unit="x",
        description="Giá / Dòng tiền (P/CF)",
        statement="financial_ratios",
    ),
    "ev_to_ebitda": Metric(
        id="ev_to_ebitda",
        group="valuation",
        label="EV/EBITDA",
        unit="x",
        description="Giá trị doanh nghiệp / EBITDA (EV/EBITDA)",
        statement="financial_ratios",
    ),
    "ev_to_ebit": Metric(
        id="ev_to_ebit",
        group="valuation",
        label="EV/EBIT",
        unit="x",
        description="Giá trị doanh nghiệp / EBIT (EV/EBIT)",
        statement="financial_ratios",
    ),
    # Profitability (margins + returns)
    "gross_margin": Metric(
        id="gross_margin",
        group="profitability",
        label="Gross Margin",
        unit="%",
        description="Biên lợi nhuận gộp (%)",
        statement="financial_ratios",
    ),
    "ebit_margin": Metric(
        id="ebit_margin",
        group="profitability",
        label="EBIT Margin",
        unit="%",
        description="Biên EBIT (%)",
        statement="financial_ratios",
    ),
    "net_profit_margin": Metric(
        id="net_profit_margin",
        group="profitability",
        label="Net Margin",
        unit="%",
        description="Biên lợi nhuận ròng (%)",
        statement="financial_ratios",
    ),
    "roe": Metric(
        id="roe",
        group="profitability",
        label="ROE",
        unit="%",
        description="Tỷ suất sinh lời trên vốn chủ (ROE, %)",
        statement="financial_ratios",
    ),
    "roa": Metric(
        id="roa",
        group="profitability",
        label="ROA",
        unit="%",
        description="Tỷ suất sinh lời trên tổng tài sản (ROA, %)",
        statement="financial_ratios",
    ),
    "roic": Metric(
        id="roic",
        group="profitability",
        label="ROIC",
        unit="%",
        description="Tỷ suất sinh lời trên vốn đầu tư (ROIC, %)",
        statement="financial_ratios",
    ),
    # Leverage / coverage
    "debt_to_equity": Metric(
        id="debt_to_equity",
        group="leverage",
        label="Debt/Equity",
        unit="x",
        description="Nợ / Vốn chủ (D/E)",
        statement="financial_ratios",
    ),
    "debt_to_equity_adjusted": Metric(
        id="debt_to_equity_adjusted",
        group="leverage",
        label="Debt/Equity (Adj.)",
        unit="x",
        description="Nợ / Vốn chủ (điều chỉnh)",
        statement="financial_ratios",
    ),
    "fixed_assets_to_equity": Metric(
        id="fixed_assets_to_equity",
        group="leverage",
        label="Fixed Assets/Equity",
        unit="x",
        description="TSCĐ / Vốn chủ",
        statement="financial_ratios",
    ),
    "equity_to_charter_capital": Metric(
        id="equity_to_charter_capital",
        group="leverage",
        label="Equity/Charter Capital",
        unit="x",
        description="Vốn chủ / Vốn điều lệ",
        statement="financial_ratios",
    ),
    "financial_leverage": Metric(
        id="financial_leverage",
        group="leverage",
        label="Financial Leverage",
        unit="x",
        description="Đòn bẩy tài chính (khái niệm tổng quát, tuỳ nguồn tính)",
        statement="financial_ratios",
    ),
    "interest_coverage_ratio": Metric(
        id="interest_coverage_ratio",
        group="leverage",
        label="Interest Coverage",
        unit="x",
        description="Khả năng chi trả lãi vay (EBIT/Interest)",
        statement="financial_ratios",
    ),
    # Liquidity
    "current_ratio": Metric(
        id="current_ratio",
        group="liquidity",
        label="Current Ratio",
        unit="x",
        description="Khả năng thanh toán hiện thời",
        statement="financial_ratios",
    ),
    "quick_ratio": Metric(
        id="quick_ratio",
        group="liquidity",
        label="Quick Ratio",
        unit="x",
        description="Khả năng thanh toán nhanh",
        statement="financial_ratios",
    ),
    "cash_ratio": Metric(
        id="cash_ratio",
        group="liquidity",
        label="Cash Ratio",
        unit="x",
        description="Khả năng thanh toán tiền mặt",
        statement="financial_ratios",
    ),
    # Efficiency / working capital cycle
    "asset_turnover": Metric(
        id="asset_turnover",
        group="efficiency",
        label="Asset Turnover",
        unit="x",
        description="Vòng quay tổng tài sản",
        statement="financial_ratios",
    ),
    "fixed_asset_turnover": Metric(
        id="fixed_asset_turnover",
        group="efficiency",
        label="Fixed Asset Turnover",
        unit="x",
        description="Vòng quay tài sản cố định",
        statement="financial_ratios",
    ),
    "inventory_turnover": Metric(
        id="inventory_turnover",
        group="efficiency",
        label="Inventory Turnover",
        unit="x",
        description="Vòng quay tồn kho",
        statement="financial_ratios",
    ),
    "days_sales_outstanding": Metric(
        id="days_sales_outstanding",
        group="efficiency",
        label="DSO",
        unit="days",
        description="Số ngày thu tiền (Days Sales Outstanding)",
        statement="financial_ratios",
    ),
    "days_inventory_outstanding": Metric(
        id="days_inventory_outstanding",
        group="efficiency",
        label="DIO",
        unit="days",
        description="Số ngày tồn kho (Days Inventory Outstanding)",
        statement="financial_ratios",
    ),
    "days_payable_outstanding": Metric(
        id="days_payable_outstanding",
        group="efficiency",
        label="DPO",
        unit="days",
        description="Số ngày phải trả (Days Payable Outstanding)",
        statement="financial_ratios",
    ),
    "cash_conversion_cycle": Metric(
        id="cash_conversion_cycle",
        group="efficiency",
        label="CCC",
        unit="days",
        description="Chu kỳ chuyển đổi tiền mặt (Cash Conversion Cycle)",
        statement="financial_ratios",
    ),
    # Payout
    "dividend_payout_ratio": Metric(
        id="dividend_payout_ratio",
        group="payout",
        label="Dividend Payout",
        unit="%",
        description="Tỷ lệ chi trả cổ tức (%)",
        statement="financial_ratios",
    ),
    # Absolute financials (from ratios table)
    "ebitda_billions": Metric(
        id="ebitda_billions",
        group="scale",
        label="EBITDA",
        unit="tỷ VND",
        description="EBITDA (tỷ VND) - số tuyệt đối",
        statement="financial_ratios",
    ),
    "ebit_billions": Metric(
        id="ebit_billions",
        group="scale",
        label="EBIT",
        unit="tỷ VND",
        description="EBIT (tỷ VND) - số tuyệt đối",
        statement="financial_ratios",
    ),
    "eps_vnd": Metric(
        id="eps_vnd",
        group="scale",
        label="EPS",
        unit="VND",
        description="Lợi nhuận trên mỗi cổ phiếu (EPS, VND)",
        statement="financial_ratios",
    ),
    "bvps_vnd": Metric(
        id="bvps_vnd",
        group="scale",
        label="BVPS",
        unit="VND",
        description="Giá trị sổ sách trên mỗi cổ phiếu (BVPS, VND)",
        statement="financial_ratios",
    ),
}


_FINANCIAL_RATIOS_METADATA_COLUMNS = {
    "id",
    "symbol",
    "period",
    "year",
    "quarter",
    "data_json",
    "source",
    "created_at",
    "updated_at",
}


_STATEMENT_METADATA_COLUMNS = {
    "id",
    "symbol",
    "period",
    "year",
    "quarter",
    "data_json",
    "source",
    "created_at",
    "updated_at",
}


BALANCE_SHEET_METRICS: Dict[str, Metric] = {
    # Assets
    "asset_current": Metric("asset_current", "assets", "Tài sản ngắn hạn", "VND", "Tổng tài sản ngắn hạn", "balance_sheet", "assets_current"),
    "cash_and_equivalents": Metric("cash_and_equivalents", "assets", "Tiền & tương đương tiền", "VND", "Tiền và các khoản tương đương tiền", "balance_sheet", "assets_current"),
    "short_term_investments": Metric("short_term_investments", "assets", "Đầu tư ngắn hạn", "VND", "Các khoản đầu tư tài chính ngắn hạn", "balance_sheet", "assets_current"),
    "accounts_receivable": Metric("accounts_receivable", "assets", "Phải thu", "VND", "Các khoản phải thu", "balance_sheet", "assets_current"),
    "inventory": Metric("inventory", "assets", "Hàng tồn kho", "VND", "Giá trị hàng tồn kho", "balance_sheet", "assets_current"),
    "current_assets_other": Metric("current_assets_other", "assets", "Tài sản NH khác", "VND", "Các tài sản ngắn hạn khác", "balance_sheet", "assets_current"),
    "asset_non_current": Metric("asset_non_current", "assets", "Tài sản dài hạn", "VND", "Tổng tài sản dài hạn", "balance_sheet", "assets_non_current"),
    "long_term_receivables": Metric("long_term_receivables", "assets", "Phải thu dài hạn", "VND", "Các khoản phải thu dài hạn", "balance_sheet", "assets_non_current"),
    "fixed_assets": Metric("fixed_assets", "assets", "Tài sản cố định", "VND", "Giá trị tài sản cố định", "balance_sheet", "assets_non_current"),
    "long_term_investments": Metric("long_term_investments", "assets", "Đầu tư dài hạn", "VND", "Các khoản đầu tư dài hạn", "balance_sheet", "assets_non_current"),
    "non_current_assets_other": Metric("non_current_assets_other", "assets", "Tài sản DH khác", "VND", "Các tài sản dài hạn khác", "balance_sheet", "assets_non_current"),
    "total_assets": Metric("total_assets", "assets", "Tổng tài sản", "VND", "Tổng tài sản", "balance_sheet", "total"),
    # Liabilities
    "liabilities_total": Metric("liabilities_total", "liabilities", "Tổng nợ phải trả", "VND", "Tổng nợ phải trả", "balance_sheet", "total"),
    "liabilities_current": Metric("liabilities_current", "liabilities", "Nợ ngắn hạn", "VND", "Tổng nợ ngắn hạn", "balance_sheet", "liabilities_current"),
    "liabilities_non_current": Metric("liabilities_non_current", "liabilities", "Nợ dài hạn", "VND", "Tổng nợ dài hạn", "balance_sheet", "liabilities_non_current"),
    # Equity
    "equity_total": Metric("equity_total", "equity", "Vốn chủ sở hữu", "VND", "Tổng vốn chủ sở hữu", "balance_sheet", "equity"),
    "share_capital": Metric("share_capital", "equity", "Vốn góp", "VND", "Vốn góp của chủ sở hữu (share capital)", "balance_sheet", "equity"),
    "retained_earnings": Metric("retained_earnings", "equity", "LN giữ lại", "VND", "Lợi nhuận sau thuế chưa phân phối", "balance_sheet", "equity"),
    "equity_other": Metric("equity_other", "equity", "Vốn CSH khác", "VND", "Các khoản mục vốn chủ sở hữu khác", "balance_sheet", "equity"),
    "total_equity_and_liabilities": Metric("total_equity_and_liabilities", "liabilities", "Tổng nguồn vốn", "VND", "Tổng nợ phải trả và vốn chủ sở hữu", "balance_sheet", "total"),
}


INCOME_STATEMENT_METRICS: Dict[str, Metric] = {
    # Income / top line
    "revenue": Metric("revenue", "income", "Doanh thu", "VND", "Doanh thu (tổng)", "income_statement", "income"),
    "net_revenue": Metric("net_revenue", "income", "Doanh thu thuần", "VND", "Doanh thu thuần", "income_statement", "income"),
    "revenue_growth": Metric("revenue_growth", "growth", "Tăng trưởng doanh thu", "%", "Tăng trưởng doanh thu (%)", "income_statement", "growth"),
    # Costs / profits
    "cost_of_goods_sold": Metric("cost_of_goods_sold", "expense", "Giá vốn", "VND", "Giá vốn hàng bán", "income_statement", "cost"),
    "gross_profit": Metric("gross_profit", "profit", "Lợi nhuận gộp", "VND", "Lợi nhuận gộp", "income_statement", "profit"),
    "financial_income": Metric("financial_income", "income", "Doanh thu tài chính", "VND", "Doanh thu hoạt động tài chính", "income_statement", "income"),
    "financial_expense": Metric("financial_expense", "expense", "Chi phí tài chính", "VND", "Chi phí tài chính", "income_statement", "expense"),
    "net_financial_income": Metric("net_financial_income", "profit", "LN tài chính thuần", "VND", "Thu nhập tài chính thuần", "income_statement", "profit"),
    "operating_expenses": Metric("operating_expenses", "expense", "Chi phí hoạt động", "VND", "Chi phí bán hàng & QLDN (tuỳ nguồn)", "income_statement", "expense"),
    "operating_profit": Metric("operating_profit", "profit", "Lợi nhuận hoạt động", "VND", "Lợi nhuận từ hoạt động kinh doanh", "income_statement", "profit"),
    "other_income": Metric("other_income", "income", "Thu nhập khác", "VND", "Thu nhập khác", "income_statement", "income"),
    "profit_before_tax": Metric("profit_before_tax", "profit", "Lợi nhuận trước thuế", "VND", "Lợi nhuận trước thuế", "income_statement", "profit"),
    "corporate_income_tax": Metric("corporate_income_tax", "tax", "Thuế TNDN hiện hành", "VND", "Thuế thu nhập doanh nghiệp hiện hành", "income_statement", "tax"),
    "deferred_income_tax": Metric("deferred_income_tax", "tax", "Thuế TNDN hoãn lại", "VND", "Thuế thu nhập doanh nghiệp hoãn lại", "income_statement", "tax"),
    "net_profit": Metric("net_profit", "profit", "Lợi nhuận sau thuế", "VND", "Lợi nhuận sau thuế", "income_statement", "profit"),
    "minority_interest": Metric("minority_interest", "profit", "Lợi ích CĐTS", "VND", "Lợi ích của cổ đông thiểu số", "income_statement", "profit"),
    "net_profit_parent_company": Metric("net_profit_parent_company", "profit", "LN thuộc CĐ mẹ", "VND", "Lợi nhuận thuộc về cổ đông công ty mẹ", "income_statement", "profit"),
    "net_profit_parent_company_post": Metric("net_profit_parent_company_post", "profit", "LN thuộc CĐ mẹ (post)", "VND", "Lợi nhuận thuộc về CĐ mẹ (biến thể theo nguồn)", "income_statement", "profit"),
    "profit_growth": Metric("profit_growth", "growth", "Tăng trưởng lợi nhuận", "%", "Tăng trưởng lợi nhuận (%)", "income_statement", "growth"),
    "eps": Metric("eps", "per_share", "EPS", "VND", "Lợi nhuận trên mỗi cổ phiếu (EPS)", "income_statement", "per_share"),
}


CASH_FLOW_STATEMENT_METRICS: Dict[str, Metric] = {
    # Base and non-cash adjustments
    "profit_before_tax": Metric("profit_before_tax", "profit", "LNTT", "VND", "Lợi nhuận trước thuế (base)", "cash_flow_statement", "operating_base"),
    "depreciation_fixed_assets": Metric("depreciation_fixed_assets", "noncash_adjustment", "Khấu hao", "VND", "Khấu hao tài sản cố định", "cash_flow_statement", "operating_adjustments"),
    "provision_credit_loss_real_estate": Metric("provision_credit_loss_real_estate", "noncash_adjustment", "Dự phòng/chi phí tín dụng/BĐS", "VND", "Dự phòng (tên trường theo nguồn)", "cash_flow_statement", "operating_adjustments"),
    "profit_loss_from_disposal_fixed_assets": Metric("profit_loss_from_disposal_fixed_assets", "noncash_adjustment", "Lãi/lỗ thanh lý TSCĐ", "VND", "Lãi/lỗ từ thanh lý TSCĐ", "cash_flow_statement", "operating_adjustments"),
    "profit_loss_investment_activities": Metric("profit_loss_investment_activities", "noncash_adjustment", "Lãi/lỗ đầu tư", "VND", "Lãi/lỗ từ hoạt động đầu tư", "cash_flow_statement", "operating_adjustments"),
    "interest_income": Metric("interest_income", "noncash_adjustment", "Thu nhập lãi", "VND", "Thu nhập lãi (theo nguồn)", "cash_flow_statement", "operating_adjustments"),
    "interest_and_dividend_income": Metric("interest_and_dividend_income", "noncash_adjustment", "Thu lãi & cổ tức", "VND", "Thu nhập lãi và cổ tức", "cash_flow_statement", "operating_adjustments"),
    "net_cash_flow_from_operating_activities_before_working_capital": Metric(
        "net_cash_flow_from_operating_activities_before_working_capital",
        "cashflow_operating",
        "LCTT HĐKD trước VLĐ",
        "VND",
        "Dòng tiền từ HĐKD trước biến động vốn lưu động",
        "cash_flow_statement",
        "operating_subtotal",
    ),
    # Working capital changes
    "increase_decrease_receivables": Metric("increase_decrease_receivables", "working_capital", "± Phải thu", "VND", "Tăng/giảm các khoản phải thu", "cash_flow_statement", "working_capital"),
    "increase_decrease_inventory": Metric("increase_decrease_inventory", "working_capital", "± Tồn kho", "VND", "Tăng/giảm hàng tồn kho", "cash_flow_statement", "working_capital"),
    "increase_decrease_payables": Metric("increase_decrease_payables", "working_capital", "± Phải trả", "VND", "Tăng/giảm các khoản phải trả", "cash_flow_statement", "working_capital"),
    "increase_decrease_prepaid_expenses": Metric("increase_decrease_prepaid_expenses", "working_capital", "± Trả trước", "VND", "Tăng/giảm chi phí trả trước", "cash_flow_statement", "working_capital"),
    # Cash paid / received (operating)
    "interest_expense_paid": Metric("interest_expense_paid", "cashflow_operating", "Chi lãi vay", "VND", "Tiền lãi vay đã trả", "cash_flow_statement", "operating_cash"),
    "corporate_income_tax_paid": Metric("corporate_income_tax_paid", "cashflow_operating", "Thuế TNDN đã nộp", "VND", "Thuế TNDN đã nộp", "cash_flow_statement", "operating_cash"),
    "other_cash_from_operating_activities": Metric("other_cash_from_operating_activities", "cashflow_operating", "Thu khác HĐKD", "VND", "Các khoản thu khác từ HĐKD", "cash_flow_statement", "operating_cash"),
    "other_cash_paid_for_operating_activities": Metric("other_cash_paid_for_operating_activities", "cashflow_operating", "Chi khác HĐKD", "VND", "Các khoản chi khác cho HĐKD", "cash_flow_statement", "operating_cash"),
    "net_cash_from_operating_activities": Metric("net_cash_from_operating_activities", "cashflow_operating", "LCTT thuần từ HĐKD", "VND", "Dòng tiền thuần từ HĐKD", "cash_flow_statement", "operating_total"),
    # Investing
    "purchase_purchase_fixed_assets": Metric("purchase_purchase_fixed_assets", "cashflow_investing", "Mua sắm TSCĐ", "VND", "Tiền chi mua sắm/xd TSCĐ", "cash_flow_statement", "investing"),
    "proceeds_from_disposal_fixed_assets": Metric("proceeds_from_disposal_fixed_assets", "cashflow_investing", "Thanh lý TSCĐ", "VND", "Tiền thu từ thanh lý/nhượng bán TSCĐ", "cash_flow_statement", "investing"),
    "loans_other_collections": Metric("loans_other_collections", "cashflow_investing", "Thu hồi cho vay/thu khác", "VND", "Thu hồi cho vay và các khoản thu khác", "cash_flow_statement", "investing"),
    "investments_other_companies": Metric("investments_other_companies", "cashflow_investing", "Đầu tư đơn vị khác", "VND", "Tiền chi đầu tư vào đơn vị khác", "cash_flow_statement", "investing"),
    "proceeds_from_sale_investments_other_companies": Metric(
        "proceeds_from_sale_investments_other_companies",
        "cashflow_investing",
        "Thu từ bán đầu tư",
        "VND",
        "Tiền thu từ bán/thu hồi đầu tư vào đơn vị khác",
        "cash_flow_statement",
        "investing",
    ),
    "dividends_and_profits_received": Metric("dividends_and_profits_received", "cashflow_investing", "Cổ tức & lợi nhuận nhận", "VND", "Cổ tức và lợi nhuận được chia", "cash_flow_statement", "investing"),
    "net_cash_from_investing_activities": Metric("net_cash_from_investing_activities", "cashflow_investing", "LCTT thuần từ ĐT", "VND", "Dòng tiền thuần từ hoạt động đầu tư", "cash_flow_statement", "investing_total"),
    # Financing
    "increase_share_capital_contribution_equity": Metric(
        "increase_share_capital_contribution_equity",
        "cashflow_financing",
        "Tăng vốn góp",
        "VND",
        "Tiền thu từ phát hành cổ phiếu/nhận góp vốn",
        "cash_flow_statement",
        "financing",
    ),
    "payment_for_capital_contribution_buyback_shares": Metric(
        "payment_for_capital_contribution_buyback_shares",
        "cashflow_financing",
        "Chi góp vốn/mua lại CP",
        "VND",
        "Tiền chi góp vốn hoặc mua lại cổ phiếu",
        "cash_flow_statement",
        "financing",
    ),
    "proceeds_from_borrowings": Metric("proceeds_from_borrowings", "cashflow_financing", "Thu từ đi vay", "VND", "Tiền thu từ đi vay", "cash_flow_statement", "financing"),
    "repayments_of_borrowings": Metric("repayments_of_borrowings", "cashflow_financing", "Trả nợ vay", "VND", "Tiền trả nợ gốc vay", "cash_flow_statement", "financing"),
    "lease_principal_payments": Metric("lease_principal_payments", "cashflow_financing", "Trả nợ thuê tài chính", "VND", "Tiền trả nợ gốc thuê tài chính", "cash_flow_statement", "financing"),
    "dividends_paid": Metric("dividends_paid", "cashflow_financing", "Cổ tức đã trả", "VND", "Cổ tức đã trả", "cash_flow_statement", "financing"),
    "other_cash_from_financing_activities": Metric("other_cash_from_financing_activities", "cashflow_financing", "Thu/chi khác TC", "VND", "Các khoản thu/chi khác từ HĐ tài chính", "cash_flow_statement", "financing"),
    "net_cash_from_financing_activities": Metric("net_cash_from_financing_activities", "cashflow_financing", "LCTT thuần từ TC", "VND", "Dòng tiền thuần từ hoạt động tài chính", "cash_flow_statement", "financing_total"),
    # Net / cash position
    "net_cash_flow_period": Metric("net_cash_flow_period", "cash", "Lưu chuyển tiền thuần", "VND", "Lưu chuyển tiền thuần trong kỳ", "cash_flow_statement", "net"),
    "cash_and_cash_equivalents_beginning": Metric("cash_and_cash_equivalents_beginning", "cash", "Tiền đầu kỳ", "VND", "Tiền và tương đương tiền đầu kỳ", "cash_flow_statement", "cash_position"),
    "cash_and_cash_equivalents_ending": Metric("cash_and_cash_equivalents_ending", "cash", "Tiền cuối kỳ", "VND", "Tiền và tương đương tiền cuối kỳ", "cash_flow_statement", "cash_position"),
}


TABLE_METRICS: Dict[str, Dict[str, Metric]] = {
    "financial_ratios": FINANCIAL_RATIOS_METRICS,
    "balance_sheet": BALANCE_SHEET_METRICS,
    "income_statement": INCOME_STATEMENT_METRICS,
    "cash_flow_statement": CASH_FLOW_STATEMENT_METRICS,
}


def metric_for(table: str, column_name: str) -> Optional[Metric]:
    table = table.strip()
    metrics = TABLE_METRICS.get(table)
    if not metrics:
        return None
    return metrics.get(column_name)


def is_metric_column(table: str, column_name: str) -> bool:
    if table == "financial_ratios":
        return is_financial_ratios_metric_column(column_name)
    return column_name not in _STATEMENT_METADATA_COLUMNS


def validate_profile_columns(table: str, columns: Sequence[str]) -> List[str]:
    metrics = TABLE_METRICS.get(table, {})
    return [c for c in columns if c not in metrics]


def financial_ratios_metric_ids() -> List[str]:
    return sorted(FINANCIAL_RATIOS_METRICS.keys())


def is_financial_ratios_metric_column(column_name: str) -> bool:
    return column_name not in _FINANCIAL_RATIOS_METADATA_COLUMNS


def metric_for_financial_ratios_column(column_name: str) -> Optional[Metric]:
    return FINANCIAL_RATIOS_METRICS.get(column_name)


def _profile_general() -> List[str]:
    return [
        "market_cap_billions",
        "price_to_earnings",
        "price_to_book",
        "ev_to_ebitda",
        "ev_to_ebit",
        "beta",
        "roe",
        "roa",
        "roic",
        "gross_margin",
        "ebit_margin",
        "net_profit_margin",
        "debt_to_equity",
        "interest_coverage_ratio",
        "current_ratio",
        "cash_conversion_cycle",
        "asset_turnover",
        "inventory_turnover",
        "dividend_payout_ratio",
    ]


def _profile_banks() -> List[str]:
    return [
        "market_cap_billions",
        "price_to_book",
        "price_to_earnings",
        "eps_vnd",
        "bvps_vnd",
        "roe",
        "roa",
        "financial_leverage",
        "beta",
        "dividend_payout_ratio",
    ]


def _profile_financial_services() -> List[str]:
    return [
        "market_cap_billions",
        "price_to_book",
        "price_to_earnings",
        "roe",
        "roa",
        "financial_leverage",
        "beta",
        "dividend_payout_ratio",
    ]


def _profile_insurance() -> List[str]:
    return [
        "market_cap_billions",
        "price_to_book",
        "price_to_earnings",
        "roe",
        "roa",
        "financial_leverage",
        "beta",
        "dividend_payout_ratio",
    ]


def _profile_real_estate() -> List[str]:
    return [
        "market_cap_billions",
        "price_to_book",
        "price_to_earnings",
        "debt_to_equity",
        "interest_coverage_ratio",
        "current_ratio",
        "cash_ratio",
        "days_inventory_outstanding",
        "cash_conversion_cycle",
        "roe",
        "net_profit_margin",
        "beta",
    ]


def _profile_construction_materials() -> List[str]:
    return [
        "market_cap_billions",
        "price_to_earnings",
        "ev_to_ebitda",
        "gross_margin",
        "ebit_margin",
        "net_profit_margin",
        "asset_turnover",
        "days_sales_outstanding",
        "days_payable_outstanding",
        "cash_conversion_cycle",
        "debt_to_equity",
        "interest_coverage_ratio",
        "beta",
    ]


def _profile_manufacturing_inventory_heavy() -> List[str]:
    return [
        "market_cap_billions",
        "price_to_earnings",
        "ev_to_ebitda",
        "gross_margin",
        "net_profit_margin",
        "inventory_turnover",
        "days_inventory_outstanding",
        "days_sales_outstanding",
        "cash_conversion_cycle",
        "asset_turnover",
        "debt_to_equity",
        "interest_coverage_ratio",
        "beta",
    ]


def _profile_utilities() -> List[str]:
    return [
        "market_cap_billions",
        "ev_to_ebitda",
        "price_to_earnings",
        "dividend_payout_ratio",
        "debt_to_equity",
        "interest_coverage_ratio",
        "roe",
        "beta",
    ]


def _profile_tech_services() -> List[str]:
    return [
        "market_cap_billions",
        "price_to_earnings",
        "ev_to_ebitda",
        "gross_margin",
        "ebit_margin",
        "roe",
        "roic",
        "asset_turnover",
        "beta",
    ]


def industry_profile_metric_ids(icb_name3: Optional[str]) -> List[str]:
    if not icb_name3:
        return _profile_general()

    name = icb_name3.strip().lower()

    if "ngân hàng" in name:
        return _profile_banks()
    if "bảo hiểm" in name:
        return _profile_insurance()
    if "dịch vụ tài chính" in name:
        return _profile_financial_services()

    if "bất động sản" in name:
        return _profile_real_estate()

    if "xây dựng" in name or "vật liệu" in name:
        return _profile_construction_materials()

    if "sản xuất thực phẩm" in name or "bia" in name or "đồ uống" in name or "hàng gia dụng" in name:
        return _profile_manufacturing_inventory_heavy()

    if "hóa chất" in name or "kim loại" in name or "khai khoáng" in name or "dầu khí" in name:
        return _profile_construction_materials()

    if "sản xuất & phân phối điện" in name or "nước" in name or "khí đốt" in name:
        return _profile_utilities()

    if "phần mềm" in name or "dịch vụ máy tính" in name or "viễn thông" in name:
        return _profile_tech_services()

    return _profile_general()


def validate_profile(profile_metric_ids: Sequence[str]) -> List[str]:
    return [mid for mid in profile_metric_ids if mid not in FINANCIAL_RATIOS_METRICS]


def _profile_balance_sheet_general() -> List[str]:
    return [
        "total_assets",
        "asset_current",
        "cash_and_equivalents",
        "accounts_receivable",
        "inventory",
        "asset_non_current",
        "liabilities_total",
        "liabilities_current",
        "liabilities_non_current",
        "equity_total",
        "retained_earnings",
    ]


def _profile_income_statement_general() -> List[str]:
    return [
        "net_revenue",
        "revenue_growth",
        "gross_profit",
        "operating_profit",
        "profit_before_tax",
        "net_profit",
        "profit_growth",
    ]


def _profile_cash_flow_general() -> List[str]:
    return [
        "net_cash_from_operating_activities",
        "net_cash_from_investing_activities",
        "net_cash_from_financing_activities",
        "net_cash_flow_period",
        "cash_and_cash_equivalents_beginning",
        "cash_and_cash_equivalents_ending",
        "depreciation_fixed_assets",
        "corporate_income_tax_paid",
    ]


def industry_profile(icb_name3: Optional[str]) -> Dict[str, List[str]]:
    """
    Bộ chỉ số/line-items đặc trưng theo ngành cho 4 bảng:
    - financial_ratios (ratios/multiples)
    - balance_sheet (stock variables)
    - income_statement (flow variables)
    - cash_flow_statement (cash flows)
    """
    ratios = industry_profile_metric_ids(icb_name3)
    if not icb_name3:
        return {
            "financial_ratios": ratios,
            "balance_sheet": _profile_balance_sheet_general(),
            "income_statement": _profile_income_statement_general(),
            "cash_flow_statement": _profile_cash_flow_general(),
        }

    name = icb_name3.strip().lower()

    # Banks / financials: trọng tâm là chất lượng lợi nhuận + cấu trúc vốn + thanh khoản,
    # đồng thời vẫn giữ các line-item tổng quát để không bị thiếu.
    if "ngân hàng" in name or "dịch vụ tài chính" in name or "bảo hiểm" in name:
        return {
            "financial_ratios": ratios,
            "balance_sheet": [
                "total_assets",
                "cash_and_equivalents",
                "short_term_investments",
                "liabilities_total",
                "liabilities_current",
                "equity_total",
            ],
            "income_statement": [
                "net_financial_income",
                "operating_profit",
                "profit_before_tax",
                "net_profit",
                "net_profit_parent_company",
                "profit_growth",
            ],
            "cash_flow_statement": [
                "interest_income",
                "interest_expense_paid",
                "net_cash_from_operating_activities",
                "net_cash_flow_period",
                "cash_and_cash_equivalents_ending",
            ],
        }

    if "bất động sản" in name:
        return {
            "financial_ratios": ratios,
            "balance_sheet": [
                "total_assets",
                "inventory",
                "accounts_receivable",
                "cash_and_equivalents",
                "liabilities_total",
                "liabilities_current",
                "liabilities_non_current",
                "equity_total",
            ],
            "income_statement": [
                "net_revenue",
                "gross_profit",
                "operating_profit",
                "profit_before_tax",
                "net_profit",
                "revenue_growth",
                "profit_growth",
            ],
            "cash_flow_statement": [
                "increase_decrease_inventory",
                "increase_decrease_receivables",
                "increase_decrease_payables",
                "net_cash_from_operating_activities",
                "purchase_purchase_fixed_assets",
                "net_cash_from_investing_activities",
                "net_cash_flow_period",
                "cash_and_cash_equivalents_ending",
            ],
        }

    if "xây dựng" in name or "vật liệu" in name or "hóa chất" in name or "kim loại" in name:
        return {
            "financial_ratios": ratios,
            "balance_sheet": [
                "total_assets",
                "asset_current",
                "accounts_receivable",
                "inventory",
                "fixed_assets",
                "liabilities_total",
                "equity_total",
            ],
            "income_statement": [
                "net_revenue",
                "revenue_growth",
                "gross_profit",
                "operating_expenses",
                "operating_profit",
                "profit_before_tax",
                "net_profit",
            ],
            "cash_flow_statement": [
                "depreciation_fixed_assets",
                "increase_decrease_receivables",
                "increase_decrease_inventory",
                "increase_decrease_payables",
                "net_cash_from_operating_activities",
                "purchase_purchase_fixed_assets",
                "net_cash_flow_period",
            ],
        }

    if "sản xuất thực phẩm" in name or "bia" in name or "đồ uống" in name or "hàng gia dụng" in name:
        return {
            "financial_ratios": ratios,
            "balance_sheet": [
                "total_assets",
                "cash_and_equivalents",
                "accounts_receivable",
                "inventory",
                "liabilities_total",
                "equity_total",
            ],
            "income_statement": [
                "net_revenue",
                "cost_of_goods_sold",
                "gross_profit",
                "operating_expenses",
                "operating_profit",
                "net_profit",
                "revenue_growth",
            ],
            "cash_flow_statement": [
                "increase_decrease_inventory",
                "increase_decrease_receivables",
                "increase_decrease_payables",
                "net_cash_from_operating_activities",
                "net_cash_flow_period",
            ],
        }

    if "sản xuất & phân phối điện" in name or "nước" in name or "khí đốt" in name:
        return {
            "financial_ratios": ratios,
            "balance_sheet": [
                "total_assets",
                "fixed_assets",
                "liabilities_total",
                "equity_total",
                "cash_and_equivalents",
            ],
            "income_statement": [
                "net_revenue",
                "revenue_growth",
                "gross_profit",
                "operating_profit",
                "net_profit",
            ],
            "cash_flow_statement": [
                "depreciation_fixed_assets",
                "net_cash_from_operating_activities",
                "purchase_purchase_fixed_assets",
                "net_cash_from_investing_activities",
                "dividends_paid",
                "net_cash_flow_period",
            ],
        }

    if "phần mềm" in name or "dịch vụ máy tính" in name or "viễn thông" in name:
        return {
            "financial_ratios": ratios,
            "balance_sheet": [
                "total_assets",
                "cash_and_equivalents",
                "asset_current",
                "liabilities_total",
                "equity_total",
            ],
            "income_statement": [
                "net_revenue",
                "revenue_growth",
                "gross_profit",
                "operating_expenses",
                "operating_profit",
                "net_profit",
            ],
            "cash_flow_statement": [
                "net_cash_from_operating_activities",
                "purchase_purchase_fixed_assets",
                "net_cash_flow_period",
                "cash_and_cash_equivalents_ending",
            ],
        }

    return {
        "financial_ratios": ratios,
        "balance_sheet": _profile_balance_sheet_general(),
        "income_statement": _profile_income_statement_general(),
        "cash_flow_statement": _profile_cash_flow_general(),
    }


def validate_industry_profile(profile: Dict[str, List[str]]) -> Dict[str, List[str]]:
    problems: Dict[str, List[str]] = {}
    for table, cols in profile.items():
        if table == "financial_ratios":
            unknown = validate_profile(cols)
        else:
            unknown = validate_profile_columns(table, cols)
        if unknown:
            problems[table] = unknown
    return problems
