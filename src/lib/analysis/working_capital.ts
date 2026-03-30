import type { BalanceSheet, IncomeStatement, WorkingCapitalEfficiency } from "@/lib/types";

export function calculateWorkingCapital(
  balance: BalanceSheet,
  income: IncomeStatement,
): WorkingCapitalEfficiency {
  if (!balance || !income) {
    return { ccc: null, dso: null, dio: null, dpo: null, rating: "Không đủ dữ liệu", vietnamese_rating: "Không đủ dữ liệu", interpretation: "Không đủ dữ liệu để đánh giá hiệu quả vốn lưu động." };
  }

  let revenue = income.revenue ?? income.net_revenue;
  if (revenue !== null && revenue < 0) revenue = Math.abs(revenue);

  let cogs = income.cost_of_goods_sold;
  if (cogs !== null) cogs = Math.abs(cogs);

  const ar = balance.accounts_receivable;
  const inv = balance.inventory;
  // accounts_payable not in BalanceSheet type — use liabilities_current as proxy if needed
  // (The original schema doesn't store accounts_payable separately)
  const ap: number | null = null; // not available in current schema

  const DAYS = 365;

  const dso: number | null = (revenue !== null && revenue > 0 && ar !== null)
    ? (ar / revenue) * DAYS : null;

  const dio: number | null = (cogs !== null && cogs > 0 && inv !== null)
    ? (inv / cogs) * DAYS : null;

  const dpo: number | null = (cogs !== null && cogs > 0 && ap !== null)
    ? (ap / cogs) * DAYS : null;

  const ccc: number | null = (dso !== null && dio !== null && dpo !== null)
    ? dso + dio - dpo
    : (dso !== null && dio !== null)
    ? dso + dio // partial CCC without DPO
    : null;

  let rating: string;
  if (ccc === null) {
    rating = "Không đủ dữ liệu";
  } else if (ccc < 30) {
    rating = "Xuất sắc";
  } else if (ccc < 60) {
    rating = "Tốt";
  } else if (ccc < 90) {
    rating = "Trung bình";
  } else if (ccc < 120) {
    rating = "Cần cải thiện";
  } else {
    rating = "Kém";
  }

  // Interpretation
  const parts: string[] = [];
  if (ccc === null) {
    parts.push("Không đủ dữ liệu để đánh giá hiệu quả vốn lưu động.");
  } else {
    if (ccc < 30) parts.push(`Vòng chuyển đổi tiền mặt xuất sắc (${ccc.toFixed(1)} ngày), doanh nghiệp thu tiền rất nhanh và quản lý vốn lưu động hiệu quả.`);
    else if (ccc < 60) parts.push(`Vòng chuyển đổi tiền mặt tốt (${ccc.toFixed(1)} ngày), quản lý vốn lưu động ở mức hiệu quả.`);
    else if (ccc < 90) parts.push(`Vòng chuyển đổi tiền mặt trung bình (${ccc.toFixed(1)} ngày), cần tối ưu hóa vòng quay vốn lưu động.`);
    else parts.push(`Vòng chuyển đổi tiền mặt chậm (${ccc.toFixed(1)} ngày), doanh nghiệp cần rà soát lại quy trình thu tiền và quản lý tồn kho.`);
  }
  if (dso !== null) {
    if (dso < 45) parts.push(`Thu tiền khách hàng nhanh (${dso.toFixed(1)} ngày).`);
    else if (dso < 60) parts.push(`Thời gian thu tiền ở mức chấp nhận được (${dso.toFixed(1)} ngày).`);
    else parts.push(`Thời gian thu tiền chậm (${dso.toFixed(1)} ngày), cần xem xét lại chính sách tín dụng.`);
  }
  if (dio !== null) {
    if (dio < 60) parts.push(`Quản lý tồn kho tốt (${dio.toFixed(1)} ngày).`);
    else if (dio < 90) parts.push(`Tồn kho ở mức trung bình (${dio.toFixed(1)} ngày).`);
    else parts.push(`Tồn kho cao (${dio.toFixed(1)} ngày), cần tối ưu hóa quản lý kho.`);
  }

  return {
    ccc: ccc !== null ? Math.round(ccc * 10) / 10 : null,
    dso: dso !== null ? Math.round(dso * 10) / 10 : null,
    dio: dio !== null ? Math.round(dio * 10) / 10 : null,
    dpo: dpo !== null ? Math.round(dpo * 10) / 10 : null,
    rating,
    vietnamese_rating: rating,
    interpretation: parts.join(" "),
  };
}
