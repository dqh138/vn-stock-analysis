import type { FinancialRatios, BalanceSheet, CashFlow, PiotroskiResult } from "@/lib/types";

/**
 * Piotroski F-Score (0-9)
 * Requires two consecutive years of data.
 */
export function calculatePiotroski(
  curr: FinancialRatios,
  prev: FinancialRatios,
  cashflow: CashFlow,
  currBalance: BalanceSheet,
  prevBalance: BalanceSheet,
): PiotroskiResult {
  const totalAssets = currBalance.total_assets ?? 0;
  const prevTotalAssets = prevBalance.total_assets ?? 1;

  const roa = curr.roa ?? 0;
  const prevRoa = prev.roa ?? 0;
  const ocf = (cashflow.net_cash_flow_from_operating_activities ?? 0) / (totalAssets || 1);

  // Leverage: use total debt / total assets proxy via D/E and equity
  const currLeverage = curr.debt_to_equity ?? 0;
  const prevLeverage = prev.debt_to_equity ?? 0;

  // Liquidity
  const currCR = curr.current_ratio ?? 0;
  const prevCR = prev.current_ratio ?? 0;

  // Shares dilution
  const currShares = curr.shares_outstanding_millions ?? 0;
  const prevShares = prev.shares_outstanding_millions ?? 0;

  const signals = {
    // Profitability
    roa_positive: roa > 0,
    ocf_positive: ocf > 0,
    roa_improving: roa > prevRoa,
    low_accruals: ocf > roa, // cash earnings > accounting earnings
    // Leverage, liquidity, dilution
    leverage_improving: currLeverage <= prevLeverage,
    liquidity_improving: currCR >= prevCR,
    no_dilution: prevShares === 0 || currShares <= prevShares * 1.02,
    // Operating efficiency
    gross_margin_improving: (curr.gross_margin ?? 0) >= (prev.gross_margin ?? 0),
    asset_turnover_improving: (curr.asset_turnover ?? 0) >= (prev.asset_turnover ?? 0),
  };

  const score = Object.values(signals).filter(Boolean).length;
  void prevTotalAssets; // used above via prevBalance

  return { score, signals };
}
