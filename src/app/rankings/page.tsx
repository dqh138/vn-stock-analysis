"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";

interface RankingRow {
  rank: number;
  ticker: string;
  organ_name: string;
  icb_name3: string | null;
  exchange: string | null;
  pe: number | null;
  pb: number | null;
  roe: number | null;
  eps_vnd: number | null;
  net_profit_margin: number | null;
  eps_cagr_5y: number | null;
  valuation_score: number | null;
  growth_score: number | null;
  valuation_band: string | null;
  growth_band: string | null;
  score: number;
}

function fmt(v: number | null, d = 1) {
  if (v === null || isNaN(v)) return "—";
  return v.toFixed(d);
}
function pct(v: number | null) {
  if (v === null || isNaN(v)) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function ValuationBand({ band, score }: { band: string | null; score: number | null }) {
  if (!band || band === "unknown") return <span style={{ color: "var(--text-tertiary)" }}>—</span>;
  const cls = band === "cheap" ? "band-cheap" : band === "expensive" ? "band-expensive" : "band-fair";
  const label = band === "cheap" ? "Rẻ" : band === "expensive" ? "Đắt" : "Hợp lý";
  return <span className={cls}>{label}{score !== null ? ` ${Math.round(score)}` : ""}</span>;
}

function GrowthBand({ band, score }: { band: string | null; score: number | null }) {
  if (!band || band === "unknown") return <span style={{ color: "var(--text-tertiary)" }}>—</span>;
  const cls = band === "high" ? "band-high" : band === "medium" ? "band-medium" : "band-low";
  const label = band === "high" ? "Cao" : band === "medium" ? "TB" : "Thấp";
  return <span className={cls}>{label}{score !== null ? ` ${Math.round(score)}` : ""}</span>;
}

function RankingsTable() {
  const searchParams = useSearchParams();
  const [rows, setRows] = useState<RankingRow[]>([]);
  const [year, setYear] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sortBy, setSortBy] = useState("overall");
  const [industry, setIndustry] = useState(searchParams.get("industry") ?? "");
  const [exchange, setExchange] = useState("");
  const [industries, setIndustries] = useState<string[]>([]);

  useEffect(() => {
    fetch("/api/industries")
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .then((r) => r.json()).then((data: any[]) => setIndustries(data.map((d) => d.icb_name3)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setIsLoading(true);
    const params = new URLSearchParams({ sort_by: sortBy, limit: "100" });
    if (industry) params.set("industry", industry);
    if (exchange) params.set("exchange", exchange);
    fetch(`/api/rankings?${params}`)
      .then((r) => r.json())
      .then((data) => { setRows(data.rankings ?? []); setYear(data.year ?? null); })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [sortBy, industry, exchange]);

  return (
    <>
      <div className="dashboard-hero" style={{ paddingBottom: "1.5rem" }}>
        <div className="rankings-hero-row">
          <div>
            <h1 className="dashboard-hero-title" style={{ textAlign: "left" }}>🏆 Bảng xếp hạng cổ phiếu</h1>
            <p className="dashboard-hero-subtitle" style={{ textAlign: "left", margin: 0 }}>
              {year ? `Năm tài chính ${year} — ` : ""}{isLoading ? "Đang tải..." : `${rows.length} công ty`}
            </p>
          </div>
          <div className="rankings-controls">
            <select className="select-input" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="overall">Tổng hợp</option>
              <option value="valuation">Định giá (rẻ → đắt)</option>
              <option value="growth">Tăng trưởng (cao → thấp)</option>
            </select>
            <select className="select-input" value={exchange} onChange={(e) => setExchange(e.target.value)}>
              <option value="">Tất cả sàn</option>
              <option value="HOSE">HOSE</option>
              <option value="HNX">HNX</option>
              <option value="UPCOM">UPCOM</option>
            </select>
            <select className="select-input" value={industry} onChange={(e) => setIndustry(e.target.value)} style={{ maxWidth: 180 }}>
              <option value="">Tất cả ngành</option>
              {industries.map((i) => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Kết quả</h3>
        </div>
        <div className="rankings-table-wrap">
          {isLoading ? (
            <div style={{ textAlign: "center", padding: "3rem" }}>
              <div className="loading-spinner" />
              <p style={{ marginTop: "1rem", color: "var(--text-secondary)" }}>Đang tải...</p>
            </div>
          ) : rows.length === 0 ? (
            <p style={{ textAlign: "center", padding: "3rem", color: "var(--text-secondary)" }}>Không có dữ liệu.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Mã</th>
                  <th>Doanh nghiệp</th>
                  <th>Ngành</th>
                  <th>Sàn</th>
                  <th className="number">Điểm ĐG</th>
                  <th>ĐG</th>
                  <th className="number">P/E</th>
                  <th className="number">P/B</th>
                  <th className="number">Điểm TG</th>
                  <th>TG</th>
                  <th className="number">EPS CAGR 5y</th>
                  <th className="number">ROE</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.ticker}>
                    <td style={{ color: "var(--text-tertiary)" }}>{row.rank}</td>
                    <td><a href={`/company/${row.ticker}`} className="ticker-link">{row.ticker}</a></td>
                    <td style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.organ_name}</td>
                    <td style={{ maxWidth: 150, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--text-secondary)", fontSize: "0.75rem" }}>{row.icb_name3 ?? "—"}</td>
                    <td style={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>{row.exchange ?? "—"}</td>
                    <td className="number">{fmt(row.valuation_score)}</td>
                    <td><ValuationBand band={row.valuation_band} score={null} /></td>
                    <td className="number">{fmt(row.pe)}</td>
                    <td className="number">{fmt(row.pb, 2)}</td>
                    <td className="number">{fmt(row.growth_score)}</td>
                    <td><GrowthBand band={row.growth_band} score={null} /></td>
                    <td className="number" style={{ color: row.eps_cagr_5y !== null && row.eps_cagr_5y > 0 ? "#86efac" : row.eps_cagr_5y !== null && row.eps_cagr_5y < 0 ? "#fca5a5" : undefined }}>
                      {row.eps_cagr_5y !== null ? `${row.eps_cagr_5y > 0 ? "+" : ""}${row.eps_cagr_5y.toFixed(1)}%` : "—"}
                    </td>
                    <td className="number" style={{ color: "#86efac" }}>{pct(row.roe)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

export default function RankingsPage() {
  return (
    <Suspense>
      <RankingsTable />
    </Suspense>
  );
}
