import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import { calculatePiotroski } from "@/lib/analysis/piotroski";
import { calculateHealthScore } from "@/lib/analysis/health";
import { calculateCAGR } from "@/lib/analysis/cagr";
import { calculateAltman } from "@/lib/analysis/altman";
import { calculateEarlyWarning } from "@/lib/analysis/early_warning";
import { calculateCashFlowQuality } from "@/lib/analysis/cashflow_quality";
import { calculateWorkingCapital } from "@/lib/analysis/working_capital";
import type { FinancialRatios, BalanceSheet, CashFlow, IncomeStatement } from "@/lib/types";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> },
) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();

  const [ratiosRes, balanceRes, cashflowRes, incomeRes] = await Promise.all([
    supabase.from("financial_ratios").select("*").eq("symbol", symbol).is("quarter", null).order("year", { ascending: false }).limit(6),
    supabase.from("balance_sheet").select("*").eq("symbol", symbol).is("quarter", null).order("year", { ascending: false }).limit(6),
    supabase.from("cash_flow_statement").select("*").eq("symbol", symbol).is("quarter", null).order("year", { ascending: false }).limit(4),
    supabase.from("income_statement").select("symbol,year,quarter,revenue,net_revenue,net_profit,net_profit_parent_company,eps,operating_profit,profit_before_tax").eq("symbol", symbol).is("quarter", null).order("year", { ascending: true }).limit(10),
  ]);

  const ratios = (ratiosRes.data ?? []) as FinancialRatios[];
  const balances = (balanceRes.data ?? []) as BalanceSheet[];
  const cashflows = (cashflowRes.data ?? []) as CashFlow[];
  const incomes = (incomeRes.data ?? []) as IncomeStatement[];

  const curr = ratios[0];
  const prev = ratios[1];

  // Piotroski F-Score (needs curr + prev year ratios, balances, latest cashflow + income)
  let piotroski = null;
  if (curr && prev && balances[0] && balances[1] && cashflows[0] && incomes.length > 0) {
    const latestIncome = [...incomes].sort((a, b) => (b.year ?? 0) - (a.year ?? 0))[0];
    piotroski = calculatePiotroski(curr, prev, balances[0], balances[1], cashflows[0], latestIncome);
  }

  // Altman Z-Score
  let altman = null;
  if (balances[0] && incomes.length > 0) {
    const latestIncome = [...incomes].sort((a, b) => (b.year ?? 0) - (a.year ?? 0))[0];
    altman = calculateAltman(balances[0], latestIncome);
  }

  // Health Score
  const health = curr ? calculateHealthScore(curr) : null;

  // CAGR (multi-year from income series)
  const cagr = incomes.length >= 2 ? calculateCAGR(incomes) : null;

  // Early Warning
  const early_warning = ratios.length >= 2
    ? calculateEarlyWarning(ratios, cashflows, altman, piotroski)
    : null;

  // Cash Flow Quality
  const latestCashflow = cashflows[0] ?? null;
  const prevCashflow = cashflows[1] ?? null;
  const latestIncomeForCF = incomes.length > 0
    ? [...incomes].sort((a, b) => (b.year ?? 0) - (a.year ?? 0))[0]
    : null;
  const cashflow_quality = latestCashflow && latestIncomeForCF
    ? calculateCashFlowQuality(latestCashflow, latestIncomeForCF, prevCashflow)
    : null;

  // Working Capital Efficiency
  const working_capital = balances[0] && latestIncomeForCF
    ? calculateWorkingCapital(balances[0], latestIncomeForCF)
    : null;

  return NextResponse.json({
    symbol,
    latest_year: curr?.year ?? null,
    piotroski,
    altman,
    health,
    cagr,
    early_warning,
    cashflow_quality,
    working_capital,
    latest_ratios: curr ?? null,
  });
}
