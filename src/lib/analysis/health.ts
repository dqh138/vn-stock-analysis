import type { FinancialRatios, HealthScore } from "@/lib/types";

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v));
}

function score25(value: number | null, thresholds: [number, number, number]): number {
  if (value === null) return 0;
  const [bad, ok, good] = thresholds;
  if (value >= good) return 25;
  if (value >= ok) return 15;
  if (value >= bad) return 8;
  return 0;
}

/**
 * Health Score 0-100, split across 4 categories of 0-25 each.
 */
export function calculateHealthScore(r: FinancialRatios): HealthScore {
  // --- Profitability (0-25) ---
  const roeScore = score25(r.roe, [0.05, 0.10, 0.15]);
  const roaScore = score25(r.roa, [0.02, 0.05, 0.08]);
  const marginScore = score25(r.net_profit_margin, [0.03, 0.08, 0.15]);
  const profitability = clamp(Math.round((roeScore + roaScore + marginScore) / 3), 0, 25);

  // --- Efficiency (0-25) ---
  const atScore = score25(r.asset_turnover, [0.3, 0.6, 1.0]);
  // Cash conversion cycle: lower is better → invert
  const ccc = r.cash_conversion_cycle;
  const cccScore = ccc === null ? 0 : ccc <= 30 ? 25 : ccc <= 60 ? 15 : ccc <= 90 ? 8 : 0;
  const efficiency = clamp(Math.round((atScore + cccScore) / 2), 0, 25);

  // --- Capital Structure (0-25) ---
  // D/E: lower is better
  const de = r.debt_to_equity;
  const deScore = de === null ? 0 : de <= 0.5 ? 25 : de <= 1.0 ? 15 : de <= 2.0 ? 8 : 0;
  const icScore = score25(r.interest_coverage_ratio, [1.5, 3.0, 5.0]);
  const capital_structure = clamp(Math.round((deScore + icScore) / 2), 0, 25);

  // --- Liquidity (0-25) ---
  const crScore = score25(r.current_ratio, [1.0, 1.5, 2.0]);
  const qrScore = score25(r.quick_ratio, [0.5, 0.8, 1.2]);
  const liquidity = clamp(Math.round((crScore + qrScore) / 2), 0, 25);

  const total = profitability + efficiency + capital_structure + liquidity;

  return { total, profitability, efficiency, capital_structure, liquidity };
}

export function healthLabel(score: number): string {
  if (score >= 75) return "Khỏe";
  if (score >= 50) return "Trung bình";
  return "Yếu";
}

export function healthColor(score: number): string {
  if (score >= 75) return "text-emerald-400";
  if (score >= 50) return "text-amber-400";
  return "text-rose-400";
}
