import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import { calculatePiotroski } from "@/lib/analysis/piotroski";
import { calculateHealthScore } from "@/lib/analysis/health";
import { calculateCAGR } from "@/lib/analysis/cagr";
import type { FinancialRatios, BalanceSheet, CashFlow, IncomeStatement } from "@/lib/types";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> },
) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();

  // Fetch last 6 years of annual data in parallel
  const [ratiosRes, balanceRes, cashflowRes, incomeRes] = await Promise.all([
    supabase
      .from("financial_ratios")
      .select("*")
      .eq("symbol", symbol)
      .is("quarter", null)
      .order("year", { ascending: false })
      .limit(6),
    supabase
      .from("balance_sheet")
      .select("*")
      .eq("symbol", symbol)
      .is("quarter", null)
      .order("year", { ascending: false })
      .limit(6),
    supabase
      .from("cash_flow_statement")
      .select("*")
      .eq("symbol", symbol)
      .is("quarter", null)
      .order("year", { ascending: false })
      .limit(2),
    supabase
      .from("income_statement")
      .select("symbol,year,quarter,revenue,net_profit,net_profit_parent_company,eps")
      .eq("symbol", symbol)
      .is("quarter", null)
      .order("year", { ascending: true })
      .limit(10),
  ]);

  const ratios = (ratiosRes.data ?? []) as FinancialRatios[];
  const balances = (balanceRes.data ?? []) as BalanceSheet[];
  const cashflows = (cashflowRes.data ?? []) as CashFlow[];
  const incomes = (incomeRes.data ?? []) as IncomeStatement[];

  const curr = ratios[0];
  const prev = ratios[1];

  let piotroski = null;
  if (curr && prev && cashflows[0] && balances[0] && balances[1]) {
    piotroski = calculatePiotroski(curr, prev, cashflows[0], balances[0], balances[1]);
  }

  const health = curr ? calculateHealthScore(curr) : null;
  const cagr = incomes.length >= 2 ? calculateCAGR(incomes) : null;

  return NextResponse.json({
    symbol,
    latest_year: curr?.year ?? null,
    piotroski,
    health,
    cagr,
    latest_ratios: curr ?? null,
  });
}
