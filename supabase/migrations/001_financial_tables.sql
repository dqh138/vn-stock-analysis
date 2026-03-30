-- ============================================================
-- VN Stock Analysis — Supabase schema
-- Run this in the Supabase SQL editor (same project as vn-econ-news)
-- ============================================================

-- Companies
CREATE TABLE IF NOT EXISTS stocks (
  ticker TEXT PRIMARY KEY,
  organ_name TEXT,
  en_organ_name TEXT,
  organ_short_name TEXT,
  en_organ_short_name TEXT,
  com_type_code TEXT,
  status TEXT DEFAULT 'listed',
  listed_date TEXT,
  delisted_date TEXT,
  company_id TEXT,
  tax_code TEXT,
  isin TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Exchange membership (HOSE / HNX / UPCOM)
CREATE TABLE IF NOT EXISTS stock_exchange (
  ticker TEXT NOT NULL,
  exchange TEXT NOT NULL,
  id INTEGER,
  type TEXT,
  PRIMARY KEY (ticker, exchange)
);

-- Industry classification (ICB)
CREATE TABLE IF NOT EXISTS stock_industry (
  ticker TEXT NOT NULL,
  icb_code TEXT NOT NULL,
  icb_name2 TEXT,
  en_icb_name2 TEXT,
  icb_name3 TEXT,
  en_icb_name3 TEXT,
  icb_name4 TEXT,
  en_icb_name4 TEXT,
  icb_code1 TEXT,
  icb_code2 TEXT,
  icb_code3 TEXT,
  icb_code4 TEXT,
  PRIMARY KEY (ticker, icb_code)
);

-- Index membership (VN30, VN100, etc.)
CREATE TABLE IF NOT EXISTS stock_index (
  ticker TEXT NOT NULL,
  index_code TEXT NOT NULL,
  PRIMARY KEY (ticker, index_code)
);

-- ============================================================
-- Financial Statements (annual + quarterly)
-- year + quarter IS NULL  → annual
-- year + quarter 1-4      → quarterly
-- ============================================================

CREATE TABLE IF NOT EXISTS balance_sheet (
  id BIGSERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  period TEXT,
  year INTEGER,
  quarter INTEGER,
  -- Assets
  asset_current REAL,
  cash_and_equivalents REAL,
  short_term_investments REAL,
  accounts_receivable REAL,
  inventory REAL,
  current_assets_other REAL,
  asset_non_current REAL,
  long_term_receivables REAL,
  fixed_assets REAL,
  long_term_investments REAL,
  non_current_assets_other REAL,
  total_assets REAL,
  -- Liabilities & Equity
  liabilities_current REAL,
  liabilities_non_current REAL,
  liabilities_total REAL,
  equity_total REAL,
  share_capital REAL,
  retained_earnings REAL,
  equity_other REAL,
  total_equity_and_liabilities REAL,
  data_json JSONB,
  source TEXT DEFAULT 'VCI',
  UNIQUE (symbol, year, quarter)
);

CREATE TABLE IF NOT EXISTS income_statement (
  id BIGSERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  period TEXT,
  year INTEGER,
  quarter INTEGER,
  revenue REAL,
  revenue_growth REAL,
  net_revenue REAL,
  cost_of_goods_sold REAL,
  gross_profit REAL,
  financial_income REAL,
  financial_expense REAL,
  net_financial_income REAL,
  operating_expenses REAL,
  operating_profit REAL,
  other_income REAL,
  profit_before_tax REAL,
  corporate_income_tax REAL,
  deferred_income_tax REAL,
  net_profit REAL,
  net_profit_parent_company REAL,
  net_profit_parent_company_post REAL,
  minority_interest REAL,
  profit_growth REAL,
  eps REAL,
  data_json JSONB,
  source TEXT DEFAULT 'VCI',
  UNIQUE (symbol, year, quarter)
);

CREATE TABLE IF NOT EXISTS cash_flow_statement (
  id BIGSERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  period TEXT,
  year INTEGER,
  quarter INTEGER,
  profit_before_tax REAL,
  depreciation_fixed_assets REAL,
  provisions REAL,
  increase_decrease_receivables REAL,
  increase_decrease_inventory REAL,
  increase_decrease_payables REAL,
  increase_decrease_prepaid_expenses REAL,
  interest_expense_paid REAL,
  corporate_income_tax_paid REAL,
  net_cash_flow_from_operating_activities REAL,
  purchase_of_fixed_assets REAL,
  proceeds_from_disposal_of_fixed_assets REAL,
  loans_to_other_entities REAL,
  collection_of_loans REAL,
  purchase_of_investments REAL,
  proceeds_from_investments REAL,
  dividends_received REAL,
  net_cash_flow_from_investing_activities REAL,
  proceeds_from_share_issuance REAL,
  repayment_of_borrowings REAL,
  dividends_paid REAL,
  net_cash_flow_from_financing_activities REAL,
  net_cash_flow_period REAL,
  cash_beginning_of_period REAL,
  cash_end_of_period REAL,
  data_json JSONB,
  source TEXT DEFAULT 'VCI',
  UNIQUE (symbol, year, quarter)
);

-- Financial ratios (annual only — pre-computed by VNSTOCK)
CREATE TABLE IF NOT EXISTS financial_ratios (
  id BIGSERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  year INTEGER NOT NULL,
  quarter INTEGER,
  -- Valuation
  price_to_book REAL,
  price_to_earnings REAL,
  price_to_sales REAL,
  price_to_cash_flow REAL,
  ev_to_ebitda REAL,
  ev_to_ebit REAL,
  eps_vnd REAL,
  bvps_vnd REAL,
  market_cap_billions REAL,
  shares_outstanding_millions REAL,
  -- Profitability
  gross_margin REAL,
  ebit_margin REAL,
  net_profit_margin REAL,
  roe REAL,
  roa REAL,
  roic REAL,
  -- Efficiency
  asset_turnover REAL,
  fixed_asset_turnover REAL,
  days_sales_outstanding REAL,
  days_inventory_outstanding REAL,
  days_payable_outstanding REAL,
  cash_conversion_cycle REAL,
  inventory_turnover REAL,
  -- Leverage & Liquidity
  debt_to_equity REAL,
  debt_to_equity_adjusted REAL,
  fixed_assets_to_equity REAL,
  equity_to_charter_capital REAL,
  current_ratio REAL,
  quick_ratio REAL,
  cash_ratio REAL,
  interest_coverage_ratio REAL,
  financial_leverage REAL,
  -- Other
  beta REAL,
  dividend_payout_ratio REAL,
  ebitda_billions REAL,
  ebit_billions REAL,
  UNIQUE (symbol, year, quarter)
);

-- Price history (for risk/beta calculations)
CREATE TABLE IF NOT EXISTS stock_price_history (
  id BIGSERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  time DATE NOT NULL,
  open REAL,
  high REAL,
  low REAL,
  close REAL,
  volume BIGINT,
  UNIQUE (symbol, time)
);

-- ============================================================
-- Indexes for common query patterns
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_balance_sheet_symbol_year ON balance_sheet (symbol, year);
CREATE INDEX IF NOT EXISTS idx_income_statement_symbol_year ON income_statement (symbol, year);
CREATE INDEX IF NOT EXISTS idx_cash_flow_symbol_year ON cash_flow_statement (symbol, year);
CREATE INDEX IF NOT EXISTS idx_financial_ratios_symbol_year ON financial_ratios (symbol, year);
CREATE INDEX IF NOT EXISTS idx_price_history_symbol_time ON stock_price_history (symbol, time);
CREATE INDEX IF NOT EXISTS idx_stock_industry_icb3 ON stock_industry (icb_name3);
CREATE INDEX IF NOT EXISTS idx_stock_exchange_exchange ON stock_exchange (exchange);

-- ============================================================
-- Row Level Security — read-only public access
-- ============================================================

ALTER TABLE stocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_exchange ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_industry ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_ratios ENABLE ROW LEVEL SECURITY;
ALTER TABLE balance_sheet ENABLE ROW LEVEL SECURITY;
ALTER TABLE income_statement ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_flow_statement ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_index ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read stocks" ON stocks FOR SELECT USING (true);
CREATE POLICY "public read stock_exchange" ON stock_exchange FOR SELECT USING (true);
CREATE POLICY "public read stock_industry" ON stock_industry FOR SELECT USING (true);
CREATE POLICY "public read financial_ratios" ON financial_ratios FOR SELECT USING (true);
CREATE POLICY "public read balance_sheet" ON balance_sheet FOR SELECT USING (true);
CREATE POLICY "public read income_statement" ON income_statement FOR SELECT USING (true);
CREATE POLICY "public read cash_flow_statement" ON cash_flow_statement FOR SELECT USING (true);
CREATE POLICY "public read stock_price_history" ON stock_price_history FOR SELECT USING (true);
CREATE POLICY "public read stock_index" ON stock_index FOR SELECT USING (true);
