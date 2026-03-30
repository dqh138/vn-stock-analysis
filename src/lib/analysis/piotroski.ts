import type { FinancialRatios, BalanceSheet, CashFlow, IncomeStatement } from "@/lib/types";

export interface PiotroskiResult {
  score: number;
  rating: string;
  vietnamese_rating: string;
  interpretation: string;
  signals: {
    roa_positive: boolean | null;
    ocf_positive: boolean | null;
    roa_improving: boolean | null;
    cfo_gt_net_income: boolean | null;  // Vietnam: CFO >= 0.8 × NI
    leverage_improving: boolean | null;
    current_ratio_improving: boolean | null;
    no_dilution: boolean | null;
    gross_margin_improving: boolean | null;
    asset_turnover_improving: boolean | null;
  };
}

function safeGet(obj: Record<string, unknown> | null | undefined, ...keys: string[]): number | null {
  if (!obj) return null;
  for (const key of keys) {
    const v = obj[key];
    if (v !== null && v !== undefined) {
      const n = Number(v);
      if (!isNaN(n)) return n;
    }
  }
  return null;
}

export function calculatePiotroski(
  curr: FinancialRatios,
  prev: FinancialRatios,
  currBalance: BalanceSheet,
  prevBalance: BalanceSheet,
  cashflow: CashFlow,
  currIncome: IncomeStatement,
): PiotroskiResult {
  const c = curr as unknown as Record<string, unknown>;
  const p = prev as unknown as Record<string, unknown>;
  const cb = currBalance as unknown as Record<string, unknown>;
  const pb = prevBalance as unknown as Record<string, unknown>;
  const cf = cashflow as unknown as Record<string, unknown>;
  const ci = currIncome as unknown as Record<string, unknown>;

  // --- ROA positive ---
  const roa = safeGet(c, "roa");
  const roa_positive = roa !== null ? roa > 0 : null;

  // --- OCF positive ---
  const ocf = safeGet(cf, "net_cash_flow_from_operating_activities");
  const ocf_positive = ocf !== null ? ocf > 0 : null;

  // --- ROA improving ---
  const roa_prev = safeGet(p, "roa");
  const roa_improving = (roa !== null && roa_prev !== null) ? roa > roa_prev : null;

  // --- CFO > Net Income (Vietnam: allow CFO >= 0.8 × NI if NI > 0) ---
  const net_income = safeGet(ci, "net_profit", "net_profit_parent_company", "net_income");
  let cfo_gt_net_income: boolean | null = null;
  if (ocf !== null && net_income !== null) {
    if (net_income > 0) {
      cfo_gt_net_income = ocf >= 0.8 * net_income;
    } else {
      cfo_gt_net_income = ocf > net_income;
    }
  }

  // --- Leverage improving (long-term debt / total assets decreased) ---
  const totalAssets = safeGet(cb, "total_assets");
  const totalAssetsPrev = safeGet(pb, "total_assets");
  let leverage_improving: boolean | null = null;
  if (totalAssets && totalAssetsPrev) {
    const debtCurr =
      safeGet(cb, "liabilities_non_current") ??
      safeGet(cb, "liabilities_total");
    const debtPrev =
      safeGet(pb, "liabilities_non_current") ??
      safeGet(pb, "liabilities_total");
    if (debtCurr !== null && debtPrev !== null) {
      leverage_improving = (debtCurr / totalAssets) < (debtPrev / totalAssetsPrev);
    }
  }

  // --- Current ratio improving (prefer ratio table) ---
  const cr = safeGet(c, "current_ratio");
  const crPrev = safeGet(p, "current_ratio");
  let current_ratio_improving: boolean | null = null;
  if (cr !== null && crPrev !== null) {
    current_ratio_improving = cr > crPrev;
  } else if (totalAssets && totalAssetsPrev) {
    const ca = safeGet(cb, "asset_current");
    const cl = safeGet(cb, "liabilities_current");
    const caPrev = safeGet(pb, "asset_current");
    const clPrev = safeGet(pb, "liabilities_current");
    if (ca && cl && caPrev && clPrev) {
      current_ratio_improving = (ca / cl) > (caPrev / clPrev);
    }
  }

  // --- No dilution ---
  const shares = safeGet(c, "shares_outstanding_millions");
  const sharesPrev = safeGet(p, "shares_outstanding_millions");
  let no_dilution: boolean | null = null;
  if (shares !== null && sharesPrev !== null && sharesPrev > 0) {
    no_dilution = shares <= sharesPrev;
  }

  // --- Gross margin improving (prefer ratio table) ---
  const gm = safeGet(c, "gross_margin");
  const gmPrev = safeGet(p, "gross_margin");
  let gross_margin_improving: boolean | null = null;
  if (gm !== null && gmPrev !== null) {
    gross_margin_improving = gm > gmPrev;
  }

  // --- Asset turnover improving (prefer ratio table) ---
  const at = safeGet(c, "asset_turnover");
  const atPrev = safeGet(p, "asset_turnover");
  let asset_turnover_improving: boolean | null = null;
  if (at !== null && atPrev !== null) {
    asset_turnover_improving = at > atPrev;
  }

  const signals = {
    roa_positive,
    ocf_positive,
    roa_improving,
    cfo_gt_net_income,
    leverage_improving,
    current_ratio_improving,
    no_dilution,
    gross_margin_improving,
    asset_turnover_improving,
  };

  const score = Object.values(signals).filter((v) => v === true).length;

  let rating: string, vietnamese_rating: string, interpretation: string;
  if (score >= 8) {
    rating = "Very Strong"; vietnamese_rating = "Rất mạnh";
    interpretation = "Doanh nghiệp có sức khỏe tài chính xuất sắc với khả năng sinh lời mạnh mẽ, quản lý đòn bẩy tốt và hiệu quả vận hành cao.";
  } else if (score >= 6) {
    rating = "Strong"; vietnamese_rating = "Mạnh";
    interpretation = "Doanh nghiệp có sức khỏe tài chính tốt với nhiều yếu tố tích cực. Cần theo dõi một số khu vực cần cải thiện nhưng tổng thể vẫn ổn định.";
  } else if (score >= 4) {
    rating = "Average"; vietnamese_rating = "Trung bình";
    interpretation = "Sức khỏe tài chính ở mức trung bình. Doanh nghiệp có cả điểm mạnh và điểm yếu. Cần phân tích kỹ hơn.";
  } else {
    rating = "Weak"; vietnamese_rating = "Yếu";
    interpretation = "Doanh nghiệp có sức khỏe tài chính yếu với nhiều vấn đề về khả năng sinh lời, đòn bẩy cao hoặc hiệu quả kém.";
  }

  return { score, rating, vietnamese_rating, interpretation, signals };
}
