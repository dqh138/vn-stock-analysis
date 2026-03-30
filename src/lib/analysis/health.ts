import type { FinancialRatios, HealthScore } from "@/lib/types";

function calcProfitability(
  roe: number | null,
  roa: number | null,
  net_margin: number | null,
): number {
  let score = 0;
  let count = 0;

  if (roe !== null) {
    if (roe >= 0.20) score += 40;
    else if (roe >= 0.15) score += 32;
    else if (roe >= 0.10) score += 24;
    else if (roe >= 0.05) score += 16;
    else if (roe >= 0) score += 8;
    // else 0
    count++;
  }

  if (roa !== null) {
    if (roa >= 0.10) score += 35;
    else if (roa >= 0.07) score += 28;
    else if (roa >= 0.05) score += 21;
    else if (roa >= 0.03) score += 14;
    else if (roa >= 0) score += 7;
    // else 0
    count++;
  }

  if (net_margin !== null) {
    if (net_margin >= 0.15) score += 25;
    else if (net_margin >= 0.10) score += 20;
    else if (net_margin >= 0.05) score += 15;
    else if (net_margin >= 0.02) score += 10;
    else if (net_margin >= 0) score += 5;
    // else 0
    count++;
  }

  return count > 0 ? score / count : 0;
}

function calcEfficiency(
  asset_turnover: number | null,
  inventory_turnover: number | null,
): number {
  let score = 0;
  let count = 0;

  if (asset_turnover !== null) {
    if (asset_turnover <= 0) score += 0;
    else if (asset_turnover >= 1.5) score += 50;
    else if (asset_turnover >= 1.2) score += 40;
    else if (asset_turnover >= 1.0) score += 30;
    else if (asset_turnover >= 0.8) score += 20;
    else score += 10;
    count++;
  }

  if (inventory_turnover !== null) {
    if (inventory_turnover <= 0) score += 0;
    else if (inventory_turnover >= 10) score += 50;
    else if (inventory_turnover >= 7) score += 40;
    else if (inventory_turnover >= 5) score += 30;
    else if (inventory_turnover >= 3) score += 20;
    else score += 10;
    count++;
  }

  return count > 0 ? score / count : 0;
}

function calcLeverage(
  debt_to_equity: number | null,
  interest_coverage: number | null,
): number {
  let score = 0;
  let count = 0;

  if (debt_to_equity !== null) {
    if (debt_to_equity < 0) score += 0;
    else if (debt_to_equity <= 0.5) score += 50;
    else if (debt_to_equity <= 1.0) score += 40;
    else if (debt_to_equity <= 1.5) score += 30;
    else if (debt_to_equity <= 2.0) score += 20;
    else score += 10;
    count++;
  }

  if (interest_coverage !== null) {
    if (interest_coverage <= 0) score += 0;
    else if (interest_coverage >= 5) score += 50;
    else if (interest_coverage >= 3) score += 40;
    else if (interest_coverage >= 2) score += 30;
    else if (interest_coverage >= 1.5) score += 20;
    else score += 10;
    count++;
  }

  return count > 0 ? score / count : 0;
}

function calcLiquidity(
  current_ratio: number | null,
  quick_ratio: number | null,
): number {
  let score = 0;
  let count = 0;

  if (current_ratio !== null) {
    if (current_ratio <= 0) score += 0;
    else if (current_ratio >= 2.0) score += 50;
    else if (current_ratio >= 1.5) score += 40;
    else if (current_ratio >= 1.2) score += 30;
    else if (current_ratio >= 1.0) score += 20;
    else score += 10;
    count++;
  }

  if (quick_ratio !== null) {
    if (quick_ratio <= 0) score += 0;
    else if (quick_ratio >= 1.5) score += 50;
    else if (quick_ratio >= 1.2) score += 40;
    else if (quick_ratio >= 1.0) score += 30;
    else if (quick_ratio >= 0.8) score += 20;
    else score += 10;
    count++;
  }

  return count > 0 ? score / count : 0;
}

function interpretHealth(score: number): string {
  if (score >= 80) {
    return `Doanh nghiệp có sức khỏe tài chính rất mạnh (${score.toFixed(1)}/100). Khả năng sinh lời cao, quản lý hiệu quả, đòn bẩy an toàn và thanh khoản tốt. Vị thế tài chính vững chắc để tiếp tục phát triển và vượt qua biến động thị trường.`;
  } else if (score >= 60) {
    return `Doanh nghiệp có sức khỏe tài chính mạnh (${score.toFixed(1)}/100). Nhiều chỉ số tài chính ở mức tốt, cần duy trì và cải thiện thêm một số khu vực để nâng cao hiệu quả hoạt động.`;
  } else if (score >= 40) {
    return `Doanh nghiệp có sức khỏe tài chính trung bình (${score.toFixed(1)}/100). Có cả điểm mạnh và điểm yếu. Cần tập trung cải thiện các khu vực yếu kém để nâng cao vị thế tài chính.`;
  } else if (score >= 20) {
    return `Doanh nghiệp có sức khỏe tài chính yếu (${score.toFixed(1)}/100). Nhiều chỉ số tài chính ở mức thấp, cần có kế hoạch tái cấu trúc và cải thiện mạnh mẽ để tránh rủi ro tài chính.`;
  }
  return `Doanh nghiệp có sức khỏe tài chính rất yếu (${score.toFixed(1)}/100). Cảnh báo: Rủi ro tài chính cao, cần đánh giá lại chiến lược kinh doanh và có biện pháp khắc phục ngay lập tức.`;
}

export function calculateHealthScore(r: FinancialRatios): HealthScore {
  const profitabilityScore = calcProfitability(r.roe, r.roa, r.net_profit_margin);
  const efficiencyScore = calcEfficiency(r.asset_turnover, r.inventory_turnover);
  const leverageScore = calcLeverage(r.debt_to_equity, r.interest_coverage_ratio);
  const liquidityScore = calcLiquidity(r.current_ratio, r.quick_ratio);

  const overall = Math.round(
    (profitabilityScore * 0.30 + efficiencyScore * 0.25 + leverageScore * 0.25 + liquidityScore * 0.20) * 10
  ) / 10;

  let rating: string;
  let vietnamese_rating: string;
  if (overall >= 80) { rating = "Very Strong"; vietnamese_rating = "Rất mạnh"; }
  else if (overall >= 60) { rating = "Strong"; vietnamese_rating = "Mạnh"; }
  else if (overall >= 40) { rating = "Average"; vietnamese_rating = "Trung bình"; }
  else if (overall >= 20) { rating = "Weak"; vietnamese_rating = "Yếu"; }
  else { rating = "Very Weak"; vietnamese_rating = "Rất yếu"; }

  return {
    overall_score: overall,
    rating,
    vietnamese_rating,
    interpretation: interpretHealth(overall),
    components: {
      profitability: {
        score: Math.round(profitabilityScore * 10) / 10,
        metrics: { roe: r.roe, roa: r.roa, net_margin: r.net_profit_margin },
      },
      efficiency: {
        score: Math.round(efficiencyScore * 10) / 10,
        metrics: { asset_turnover: r.asset_turnover, inventory_turnover: r.inventory_turnover },
      },
      leverage: {
        score: Math.round(leverageScore * 10) / 10,
        metrics: { debt_to_equity: r.debt_to_equity, interest_coverage: r.interest_coverage_ratio },
      },
      liquidity: {
        score: Math.round(liquidityScore * 10) / 10,
        metrics: { current_ratio: r.current_ratio, quick_ratio: r.quick_ratio },
      },
    },
  };
}
