-- Add foreign keys so PostgREST can resolve joins
-- NOT VALID skips checking existing rows (safe for imported data)

ALTER TABLE stock_exchange
  ADD CONSTRAINT fk_stock_exchange_ticker
  FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE NOT VALID;

ALTER TABLE stock_industry
  ADD CONSTRAINT fk_stock_industry_ticker
  FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE NOT VALID;

ALTER TABLE balance_sheet
  ADD CONSTRAINT fk_balance_sheet_symbol
  FOREIGN KEY (symbol) REFERENCES stocks(ticker) ON DELETE CASCADE NOT VALID;

ALTER TABLE income_statement
  ADD CONSTRAINT fk_income_statement_symbol
  FOREIGN KEY (symbol) REFERENCES stocks(ticker) ON DELETE CASCADE NOT VALID;

ALTER TABLE cash_flow_statement
  ADD CONSTRAINT fk_cash_flow_symbol
  FOREIGN KEY (symbol) REFERENCES stocks(ticker) ON DELETE CASCADE NOT VALID;

ALTER TABLE financial_ratios
  ADD CONSTRAINT fk_financial_ratios_symbol
  FOREIGN KEY (symbol) REFERENCES stocks(ticker) ON DELETE CASCADE NOT VALID;

ALTER TABLE stock_price_history
  ADD CONSTRAINT fk_price_history_symbol
  FOREIGN KEY (symbol) REFERENCES stocks(ticker) ON DELETE CASCADE NOT VALID;

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';
