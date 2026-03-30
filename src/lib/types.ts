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
  operating_expenses: number | null;
  operating_profit: number | null;
  profit_before_tax: number | null;
  corporate_income_tax: number | null;
  net_profit: number | null;
  net_profit_parent_company: number | null;
  eps: number | null;
  profit_growth: number | null;
  revenue_growth: number | null;
}

export interface CashFlow {
  symbol: string;
  year: number;
  quarter: number | null;
  period: string | null;
  net_cash_flow_from_operating_activities: number | null;
  net_cash_flow_from_investing_activities: number | null;
  net_cash_flow_from_financing_activities: number | null;
  net_cash_flow_period: number | null;
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
  score: number;
}

export interface PiotroskiResult {
  score: number;
  signals: {
    roa_positive: boolean;
    ocf_positive: boolean;
    roa_improving: boolean;
    low_accruals: boolean;
    leverage_improving: boolean;
    liquidity_improving: boolean;
    no_dilution: boolean;
    gross_margin_improving: boolean;
    asset_turnover_improving: boolean;
  };
}

export interface HealthScore {
  total: number;
  profitability: number;
  efficiency: number;
  capital_structure: number;
  liquidity: number;
}

export interface CAGRResult {
  years: number;
  revenue_cagr: number | null;
  profit_cagr: number | null;
  eps_cagr: number | null;
}
