"use client";

import { useEffect, useState } from "react";

interface Industry {
  icb_name3: string;
  count: number;
}

const INDUSTRY_ICONS: Record<string, string> = {
  "Ngân hàng": "🏦",
  "Bất động sản": "🏘️",
  "Sản xuất": "🏭",
  "Thực phẩm & Đồ uống": "🍜",
  "Công nghệ thông tin": "💻",
  "Bán lẻ": "🛒",
  "Dịch vụ tài chính": "💰",
  "Năng lượng": "⚡",
  "Xây dựng": "🏗️",
  "Y tế": "⚕️",
  "Vận tải": "🚢",
  "Bảo hiểm": "🛡️",
};
function industryIcon(name: string) {
  for (const [k, v] of Object.entries(INDUSTRY_ICONS)) {
    if (name.toLowerCase().includes(k.toLowerCase())) return v;
  }
  return "🏢";
}

export default function Home() {
  const [industries, setIndustries] = useState<Industry[]>([]);

  useEffect(() => {
    fetch("/api/industries").then((r) => r.json()).then(setIndustries).catch(() => {});
  }, []);

  return (
    <>
      <div className="dashboard-hero">
        <h1 className="dashboard-hero-title">Phân tích Báo cáo Tài chính</h1>
        <p className="dashboard-hero-subtitle">
          Khám phá sức khỏe tài chính của doanh nghiệp Việt Nam qua các báo cáo chi tiết
        </p>
      </div>

      {/* Industries */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">🏭 Duyệt theo ngành (ICB)</h3>
        </div>
        {industries.length === 0 ? (
          <div style={{ textAlign: "center", padding: "2rem" }}>
            <div className="loading-spinner" />
          </div>
        ) : (
          <div className="industry-grid">
            {industries.map((ind) => (
              <a
                key={ind.icb_name3}
                href={`/rankings?industry=${encodeURIComponent(ind.icb_name3)}`}
                className="industry-card"
              >
                <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>
                  {industryIcon(ind.icb_name3)}
                </div>
                <div className="industry-name">{ind.icb_name3}</div>
                <div className="industry-count">{ind.count} công ty</div>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Rankings button */}
      <div className="card" style={{ marginTop: "1rem" }}>
        <div className="card-header">
          <h3 className="card-title">🏆 Bảng xếp hạng cổ phiếu</h3>
        </div>
        <p className="card-subtitle" style={{ marginBottom: "1rem" }}>
          Xếp hạng theo 2 trục: (1) định giá rẻ/đắt so với peers, (2) tiềm năng tăng trưởng (EPS CAGR + chất lượng lợi nhuận).
        </p>
        <a href="/rankings" className="btn-primary">Mở bảng xếp hạng →</a>
      </div>
    </>
  );
}
