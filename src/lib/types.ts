export interface Company {
  ticker: string;
  organ_name: string;
  en_organ_name: string | null;
  organ_short_name: string | null;
  status: string;
  listed_date: string | null;
  exchange: string | null;
  icb_name3: string | null;
  icb_name2: string | null;
  icb_code: string | null;
}

export interface FinancialRatios {
  symbol: string;
  year: number;
  quarter: number | null;
  // Valuation
  price_to_book: number | null;
  price_to_earnings: number | null;
  price_to_sales: number | null;
  price_to_cash_flow: number | null;
  ev_to_ebitda: number | null;
  ev_to_ebit: number | null;
  eps_vnd: number | null;
  bvps_vnd: number | null;
  market_cap_billions: number | null;
  shares_outstanding_millions: number | null;
  // Profitability
  gross_margin: number | null;
  ebit_margin: number | null;
  net_profit_margin: number | null;
  roe: number | null;
  roa: number | null;
  roic: number | null;
  // Efficiency
  asset_turnover: number | null;
  fixed_asset_turnover: number | null;
  days_sales_outstanding: number | null;
  days_inventory_outstanding: number | null;
  days_payable_outstanding: number | null;
  cash_conversion_cycle: number | null;
  inventory_turnover: number | null;
  // Leverage & Liquidity
  debt_to_equity: number | null;
  debt_to_equity_adjusted: number | null;
  fixed_assets_to_equity: number | null;
  equity_to_charter_capital: number | null;
  current_ratio: number | null;
  quick_ratio: number | null;
  cash_ratio: number | null;
  interest_coverage_ratio: number | null;
  financial_leverage: number | null;
  // Other
  beta: number | null;
  dividend_payout_ratio: number | null;
  ebitda_billions: number | null;
  ebit_billions: number | null;
}

export interface BalanceSheet {
  symbol: string;
  year: number;
  quarter: number | null;
  period: string | null;
  total_assets: number | null;
  asset_current: number | null;
  asset_non_current: number | null;
  cash_and_equivalents: number | null;
  short_term_investments: number | null;
  accounts_receivable: number | null;
  inventory: number | null;
  current_assets_other: number | null;
  long_term_receivables: number | null;
  fixed_assets: number | null;
  long_term_investments: number | null;
  non_current_assets_other: number | null;
  liabilities_total: number | null;
  liabilities_current: number | null;
  liabilities_non_current: number | null;
  equity_total: number | null;
  share_capital: number | null;
  retained_earnings: number | null;
  equity_other: number | null;
  total_equity_and_liabilities: number | null;
}

export interface IncomeStatement {
  symbol: string;
  year: number;
  quarter: number | null;
  period: string | null;
  revenue: number | null;
  net_revenue: number | null;
  cost_of_goods_sold: number | null;
  gross_profit: number | null;
  financial_income: number | null;
  financial_expense: number | null;
  net_financial_income: number | null;
  operating_expenses: number | null;
  operating_profit: number | null;
  other_income: number | null;
  profit_before_tax: number | null;
  corporate_income_tax: number | null;
  deferred_income_tax: number | null;
  net_profit: number | null;
  net_profit_parent_company: number | null;
  net_profit_parent_company_post: number | null;
  minority_interest: number | null;
  eps: number | null;
  profit_growth: number | null;
  revenue_growth: number | null;
}

export interface CashFlow {
  symbol: string;
  year: number;
  quarter: number | null;
  period: string | null;
  profit_before_tax: number | null;
  depreciation_fixed_assets: number | null;
  net_cash_flow_from_operating_activities: number | null;
  purchase_of_fixed_assets: number | null;
  net_cash_flow_from_investing_activities: number | null;
  proceeds_from_share_issuance: number | null;
  repayment_of_borrowings: number | null;
  dividends_paid: number | null;
  net_cash_flow_from_financing_activities: number | null;
  net_cash_flow_period: number | null;
  cash_beginning_of_period: number | null;
  cash_end_of_period: number | null;
}

export interface RankingRow {
  rank: number;
  ticker: string;
  organ_name: string;
  icb_name3: string | null;
  exchange: string | null;
  pe: number | null;
  pb: number | null;
  roe: number | null;
  eps_vnd: number | null;
  net_profit_margin: number | null;
  eps_cagr_5y: number | null;
  valuation_score: number | null;
  growth_score: number | null;
  valuation_band: string | null;
  growth_band: string | null;
  score: number;
}

/** Piotroski F-Score — 9 signals (null = insufficient data for that signal) */
export interface PiotroskiResult {
  score: number;
  rating: string;
  vietnamese_rating: string;
  interpretation: string;
  signals: {
    roa_positive: boolean | null;
    ocf_positive: boolean | null;
    roa_improving: boolean | null;
    cfo_gt_net_income: boolean | null;
    leverage_improving: boolean | null;
    current_ratio_improving: boolean | null;
    no_dilution: boolean | null;
    gross_margin_improving: boolean | null;
    asset_turnover_improving: boolean | null;
  };
}

/**
 * Health Score 0-100
 * Components (profitability/efficiency/leverage/liquidity) are also 0-100.
 * overall = profitability×30% + efficiency×25% + leverage×25% + liquidity×20%
 */
export interface HealthScore {
  overall_score: number;
  rating: string;
  vietnamese_rating: string;
  interpretation: string;
  components: {
    profitability: { score: number; metrics: Record<string, number | null> };
    efficiency:   { score: number; metrics: Record<string, number | null> };
    leverage:     { score: number; metrics: Record<string, number | null> };
    liquidity:    { score: number; metrics: Record<string, number | null> };
  };
}

export interface CAGRResult {
  years: number;
  revenue_cagr: number | null;
  profit_cagr: number | null;
  eps_cagr: number | null;
}

export interface CashFlowQuality {
  score: number | null;
  rating: string;
  vietnamese_rating: string;
  ocf_to_net_income: number | null;
  fcf_to_net_income: number | null;
  interpretation: string;
}

export interface WorkingCapitalEfficiency {
  ccc: number | null;  // Cash Conversion Cycle (days)
  dso: number | null;  // Days Sales Outstanding
  dio: number | null;  // Days Inventory Outstanding
  dpo: number | null;  // Days Payable Outstanding
  rating: string;
  vietnamese_rating: string;
  interpretation: string;
}
