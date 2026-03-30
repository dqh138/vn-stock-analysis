import type { IncomeStatement, CAGRResult } from "@/lib/types";

function cagr(start: number, end: number, years: number): number | null {
  if (!start || !end || years <= 0 || start <= 0) return null;
  return (end / start) ** (1 / years) - 1;
}

/**
 * Calculates revenue, profit, and EPS CAGR over the available year range.
 * Rows should be sorted ascending by year, annual only (quarter IS NULL).
 */
export function calculateCAGR(rows: IncomeStatement[]): CAGRResult {
  const annual = rows.filter((r) => r.quarter === null || r.quarter === undefined);
  annual.sort((a, b) => a.year - b.year);

  if (annual.length < 2) {
    return { years: 0, revenue_cagr: null, profit_cagr: null, eps_cagr: null };
  }

  const first = annual[0];
  const last = annual[annual.length - 1];
  const years = last.year - first.year;

  return {
    years,
    revenue_cagr: cagr(first.revenue ?? 0, last.revenue ?? 0, years),
    profit_cagr: cagr(
      first.net_profit_parent_company ?? first.net_profit ?? 0,
      last.net_profit_parent_company ?? last.net_profit ?? 0,
      years,
    ),
    eps_cagr: cagr(first.eps ?? 0, last.eps ?? 0, years),
  };
}

export function formatCAGR(v: number | null): string {
  if (v === null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}
