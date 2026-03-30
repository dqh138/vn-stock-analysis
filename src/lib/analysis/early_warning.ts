import type { FinancialRatios, CashFlow } from "@/lib/types";
import type { AltmanResult } from "./altman";
import type { PiotroskiResult } from "./piotroski";

export interface EarlyWarningAlert {
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  message: string;
}

export interface EarlyWarningResult {
  risk_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
  alerts: EarlyWarningAlert[];
  positive_signals: string[];
  recommendation: string;
}

function isDecreasing(values: (number | null)[], consecutive = 3): boolean {
  const valid = values.filter((v): v is number => v !== null);
  if (valid.length < consecutive) return false;
  const last = valid.slice(0, consecutive);
  for (let i = 0; i < last.length - 1; i++) {
    if (last[i] <= last[i + 1]) return false;
  }
  return true;
}

function isIncreasing(values: (number | null)[], consecutive = 3): boolean {
  const valid = values.filter((v): v is number => v !== null);
  if (valid.length < consecutive) return false;
  const last = valid.slice(0, consecutive);
  for (let i = 0; i < last.length - 1; i++) {
    if (last[i] >= last[i + 1]) return false;
  }
  return true;
}

/**
 * Early Warning System — ported from early_warning.py
 * Uses last N years of annual ratios (sorted newest first) to detect trends.
 */
export function calculateEarlyWarning(
  ratiosSeries: FinancialRatios[],   // sorted newest → oldest
  cashflows: CashFlow[],
  altman: AltmanResult | null,
  piotroski: PiotroskiResult | null,
): EarlyWarningResult {
  const alerts: EarlyWarningAlert[] = [];
  const positive_signals: string[] = [];

  const roeValues = ratiosSeries.map((r) => r.roe ?? null);
  const deValues = ratiosSeries.map((r) => r.debt_to_equity ?? null);
  const crValues = ratiosSeries.map((r) => r.current_ratio ?? null);
  const marginValues = ratiosSeries.map((r) => r.net_profit_margin ?? null);

  // 1. ROE declining 3 consecutive years
  if (isDecreasing(roeValues, 3)) {
    alerts.push({ type: "roe_decline", severity: "medium", message: "ROE giảm liên tiếp 3 năm — khả năng sinh lời đang suy yếu." });
  } else if (roeValues[0] !== null && roeValues[0] > 0.15) {
    positive_signals.push("ROE cao (>" + Math.round((roeValues[0] ?? 0) * 100) + "%) — khả năng sinh lời tốt.");
  }

  // 2. Debt/Equity increasing 3 consecutive years
  if (isIncreasing(deValues, 3)) {
    const latestDE = deValues[0];
    const sev = latestDE !== null && latestDE > 2 ? "high" : "medium";
    alerts.push({ type: "debt_increase", severity: sev, message: "Nợ/Vốn chủ sở hữu tăng liên tiếp 3 năm — đòn bẩy đang leo thang." });
  } else if (deValues[0] !== null && deValues[0] < 0.5) {
    positive_signals.push("Đòn bẩy thấp (D/E < 0.5) — cấu trúc vốn lành mạnh.");
  }

  // 3. Current ratio declining 3 consecutive years
  if (isDecreasing(crValues, 3)) {
    alerts.push({ type: "liquidity_decline", severity: "medium", message: "Tỷ số thanh khoản giảm liên tiếp 3 năm — thanh khoản ngắn hạn đang suy yếu." });
  } else if (crValues[0] !== null && crValues[0] >= 2) {
    positive_signals.push("Thanh khoản tốt (Current Ratio ≥ 2).");
  }

  // 4. Negative operating cash flow (latest year)
  const latestCF = cashflows[0];
  if (latestCF) {
    const ocf = latestCF.net_cash_flow_from_operating_activities ?? null;
    if (ocf !== null && ocf < 0) {
      alerts.push({ type: "negative_ocf", severity: "high", message: "Dòng tiền từ hoạt động kinh doanh âm — chất lượng lợi nhuận đáng nghi ngờ." });
    } else if (ocf !== null && ocf > 0) {
      positive_signals.push("Dòng tiền hoạt động dương — lợi nhuận có chất lượng tốt.");
    }
  }

  // 5. Altman Z-Score
  if (altman) {
    if (altman.zone === "distress") {
      alerts.push({ type: "altman_distress", severity: "critical", message: `Altman Z-Score = ${altman.z_score} — vùng nguy hiểm (< 1.81). Rủi ro phá sản cao.` });
    } else if (altman.zone === "grey") {
      alerts.push({ type: "altman_grey", severity: "medium", message: `Altman Z-Score = ${altman.z_score} — vùng xám (1.81–2.99). Cần theo dõi.` });
    } else if (altman.zone === "safe" && altman.z_score !== null) {
      positive_signals.push(`Altman Z-Score = ${altman.z_score} — vùng an toàn.`);
    }
  }

  // 6. Piotroski F-Score
  if (piotroski) {
    if (piotroski.score <= 3) {
      alerts.push({ type: "low_piotroski", severity: "medium", message: `Piotroski F-Score = ${piotroski.score}/9 — sức khỏe tài chính yếu.` });
    } else if (piotroski.score >= 7) {
      positive_signals.push(`Piotroski F-Score = ${piotroski.score}/9 — sức khỏe tài chính tốt.`);
    }
  }

  // 7. Net margin declining 3 consecutive years
  if (isDecreasing(marginValues, 3)) {
    alerts.push({ type: "margin_decline", severity: "medium", message: "Biên lợi nhuận ròng giảm liên tiếp 3 năm — áp lực cạnh tranh hoặc chi phí tăng." });
  }

  // Calculate risk score (0–100, lower = better)
  const severityWeights: Record<string, number> = { low: 5, medium: 15, high: 25, critical: 40 };
  let risk_score = 0;
  for (const alert of alerts) {
    risk_score += severityWeights[alert.severity] ?? 10;
  }
  risk_score = Math.min(100, risk_score);

  const risk_level: EarlyWarningResult["risk_level"] =
    risk_score >= 60 ? "critical" :
    risk_score >= 40 ? "high" :
    risk_score >= 20 ? "medium" : "low";

  const recommendations: Record<string, string> = {
    low: "Doanh nghiệp ở trạng thái tài chính tốt. Tiếp tục theo dõi định kỳ.",
    medium: "Có một số tín hiệu cảnh báo cần chú ý. Phân tích sâu hơn trước khi đầu tư.",
    high: "Nhiều tín hiệu cảnh báo nghiêm trọng. Thận trọng cao khi xem xét đầu tư.",
    critical: "Rủi ro tài chính rất cao. Không nên đầu tư khi chưa hiểu rõ nguyên nhân.",
  };

  return {
    risk_score,
    risk_level,
    alerts,
    positive_signals,
    recommendation: recommendations[risk_level],
  };
}
