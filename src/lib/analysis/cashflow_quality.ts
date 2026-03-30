import type { CashFlow, IncomeStatement, CashFlowQuality } from "@/lib/types";

export function calculateCashFlowQuality(
  cashflow: CashFlow,
  income: IncomeStatement,
  prevCashflow?: CashFlow | null,
): CashFlowQuality {
  const ocf = cashflow.net_cash_flow_from_operating_activities;
  const netIncome = income.net_profit ?? income.net_profit_parent_company;

  if (ocf === null || netIncome === null) {
    return {
      score: null,
      rating: "Không đủ dữ liệu",
      vietnamese_rating: "Không đủ dữ liệu",
      ocf_to_net_income: null,
      fcf_to_net_income: null,
      interpretation: "Không đủ dữ liệu để đánh giá chất lượng dòng tiền.",
    };
  }

  // FCF = OCF - |CapEx|
  const capex = cashflow.purchase_of_fixed_assets;
  const fcf = capex !== null ? ocf - Math.abs(capex) : null;

  const ocfToNi = netIncome !== 0 ? ocf / netIncome : null;
  const fcfToNi = fcf !== null && netIncome !== 0 ? fcf / netIncome : null;

  // OCF Consistency
  let positiveOcfYears = 0;
  let totalYears = 0;
  if (ocf > 0) positiveOcfYears++;
  totalYears++;
  if (prevCashflow?.net_cash_flow_from_operating_activities !== undefined && prevCashflow.net_cash_flow_from_operating_activities !== null) {
    if (prevCashflow.net_cash_flow_from_operating_activities > 0) positiveOcfYears++;
    totalYears++;
  }

  const scoreComponents: number[] = [];

  // Component 1: OCF/NI (max 40 pts)
  if (ocfToNi !== null && ocfToNi > 0) {
    if (ocfToNi >= 1.2) scoreComponents.push(40);
    else if (ocfToNi >= 1.0) scoreComponents.push(35);
    else if (ocfToNi >= 0.8) scoreComponents.push(25);
    else if (ocfToNi >= 0.5) scoreComponents.push(15);
    else scoreComponents.push(5);
  }

  // Component 2: FCF/NI (max 30 pts)
  if (fcfToNi !== null && fcfToNi > 0) {
    if (fcfToNi >= 1.0) scoreComponents.push(30);
    else if (fcfToNi >= 0.8) scoreComponents.push(25);
    else if (fcfToNi >= 0.5) scoreComponents.push(15);
    else if (fcfToNi >= 0.3) scoreComponents.push(8);
    else scoreComponents.push(3);
  }

  // Component 3: Consistency (max 30 pts)
  if (totalYears > 0) {
    scoreComponents.push((positiveOcfYears / totalYears) * 30);
  }

  const overallScore = scoreComponents.length > 0 ? scoreComponents.reduce((a, b) => a + b, 0) : null;

  let rating: string;
  if (overallScore === null) {
    rating = "Không đủ dữ liệu";
  } else if (overallScore >= 80) {
    rating = "Rất tốt";
  } else if (overallScore >= 60) {
    rating = "Tốt";
  } else if (overallScore >= 40) {
    rating = "Trung bình";
  } else if (overallScore >= 20) {
    rating = "Yếu";
  } else {
    rating = "Rất yếu";
  }

  // Interpretation
  const parts: string[] = [];
  if (ocfToNi !== null) {
    if (ocfToNi >= 1.0) {
      parts.push(`Dòng tiền từ hoạt động kinh doanh vượt trội so với lợi nhuận (${ocfToNi.toFixed(2)}x), cho thấy chất lượng lợi nhuận cao và chuyển đổi tốt từ lợi nhuận kế toán sang tiền mặt.`);
    } else if (ocfToNi >= 0.8) {
      parts.push(`Dòng tiền từ hoạt động kinh doanh ở mức tốt (${ocfToNi.toFixed(2)}x so với lợi nhuận), cho thấy chuyển đổi lợi nhuận thành tiền mặt khá hiệu quả.`);
    } else if (ocfToNi > 0) {
      parts.push(`Dòng tiền từ hoạt động kinh doanh thấp hơn lợi nhuận (${ocfToNi.toFixed(2)}x), có thể do tăng trưởng vốn lưu động hoặc chi phí không tiền mặt cao.`);
    }
  }
  if (fcfToNi !== null) {
    if (fcfToNi >= 0.8) {
      parts.push(`Dòng tiền tự do mạnh mẽ (${fcfToNi.toFixed(2)}x so với lợi nhuận), doanh nghiệp có dư địa để đầu tư, trả nợ hoặc trả cổ tức.`);
    } else if (fcfToNi > 0) {
      parts.push(`Dòng tiền tự do dương (${fcfToNi.toFixed(2)}x so với lợi nhuận), nhưng cần cân đối giữa đầu tư và duy trì dòng tiền.`);
    } else {
      parts.push(`Dòng tiền tự do âm, doanh nghiệp đang đầu tư mạnh cho mở rộng hoặc gặp áp lực về vốn lưu động.`);
    }
  }

  return {
    score: overallScore !== null ? Math.round(overallScore * 10) / 10 : null,
    rating,
    vietnamese_rating: rating,
    ocf_to_net_income: ocfToNi !== null ? Math.round(ocfToNi * 100) / 100 : null,
    fcf_to_net_income: fcfToNi !== null ? Math.round(fcfToNi * 100) / 100 : null,
    interpretation: parts.length > 0 ? parts.join(" ") : "Không đủ dữ liệu để diễn giải.",
  };
}
