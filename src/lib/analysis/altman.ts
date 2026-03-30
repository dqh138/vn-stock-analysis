import type { BalanceSheet, IncomeStatement } from "@/lib/types";

export interface AltmanResult {
  z_score: number | null;
  zone: "safe" | "grey" | "distress" | "insufficient_data";
  rating: string;
  vietnamese_rating: string;
  interpretation: string;
  components: {
    x1_working_capital: number | null;
    x2_retained_earnings: number | null;
    x3_ebit: number | null;
    x4_equity_to_debt: number | null;
    x5_asset_turnover: number | null;
  };
}

function get(obj: Record<string, unknown> | null | undefined, ...keys: string[]): number | null {
  if (!obj) return null;
  for (const k of keys) {
    const v = obj[k];
    if (v !== null && v !== undefined) {
      const n = Number(v);
      if (!isNaN(n)) return n;
    }
  }
  return null;
}

/**
 * Altman Z-Score
 * Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5
 *
 * Z > 2.99  → Safe
 * 1.81–2.99 → Grey Zone
 * < 1.81    → Distress
 */
export function calculateAltman(
  balance: BalanceSheet,
  income: IncomeStatement,
): AltmanResult {
  const insufficient: AltmanResult = {
    z_score: null,
    zone: "insufficient_data",
    rating: "Insufficient Data",
    vietnamese_rating: "Không đủ dữ liệu",
    interpretation: "Không đủ dữ liệu để tính Altman Z-Score.",
    components: { x1_working_capital: null, x2_retained_earnings: null, x3_ebit: null, x4_equity_to_debt: null, x5_asset_turnover: null },
  };

  const b = balance as unknown as Record<string, unknown>;
  const inc = income as unknown as Record<string, unknown>;

  const totalAssets = get(b, "total_assets");
  if (!totalAssets || totalAssets === 0) return insufficient;

  const currentAssets = get(b, "asset_current");
  const currentLiabilities = get(b, "liabilities_current");
  const retainedEarnings = get(b, "retained_earnings");
  const totalLiabilities = get(b, "liabilities_total");
  const equity = get(b, "equity_total");

  // EBIT: prefer operating_profit, fallback to net_profit
  const ebit = get(inc, "operating_profit") ?? get(inc, "profit_before_tax") ?? get(inc, "net_profit");
  const sales = get(inc, "net_revenue") ?? get(inc, "revenue");

  if (currentAssets === null || currentLiabilities === null || totalLiabilities === null || ebit === null || sales === null) {
    return insufficient;
  }

  // X1: Working Capital / Total Assets
  const x1 = (currentAssets - currentLiabilities) / totalAssets;

  // X2: Retained Earnings / Total Assets
  const x2 = retainedEarnings !== null ? retainedEarnings / totalAssets : 0;

  // X3: EBIT / Total Assets
  const x3 = ebit / totalAssets;

  // X4: Equity / Total Liabilities (proxy when market cap unavailable)
  const x4 = (equity !== null && totalLiabilities > 0) ? equity / totalLiabilities : 0;

  // X5: Sales / Total Assets
  const x5 = sales / totalAssets;

  const z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5;

  let zone: AltmanResult["zone"];
  let rating: string, vietnamese_rating: string, interpretation: string;

  if (z > 2.99) {
    zone = "safe"; rating = "Safe"; vietnamese_rating = "An toàn";
    interpretation = "Doanh nghiệp có khả năng tài chính mạnh, rủi ro phá sản thấp.";
  } else if (z >= 1.81) {
    zone = "grey"; rating = "Grey Zone"; vietnamese_rating = "Vùng xám";
    interpretation = "Doanh nghiệp ở mức trung bình, cần theo dõi chặt chẽ các chỉ số tài chính.";
  } else {
    zone = "distress"; rating = "Distress"; vietnamese_rating = "Nguy hiểm";
    interpretation = "Cảnh báo: Doanh nghiệp có rủi ro tài chính cao, có thể gặp khó khăn nghiêm trọng.";
  }

  return {
    z_score: Math.round(z * 100) / 100,
    zone, rating, vietnamese_rating, interpretation,
    components: {
      x1_working_capital: Math.round(x1 * 10000) / 10000,
      x2_retained_earnings: Math.round(x2 * 10000) / 10000,
      x3_ebit: Math.round(x3 * 10000) / 10000,
      x4_equity_to_debt: Math.round(x4 * 10000) / 10000,
      x5_asset_turnover: Math.round(x5 * 10000) / 10000,
    },
  };
}
