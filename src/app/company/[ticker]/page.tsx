"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { formatCAGR } from "@/lib/analysis/cagr";
import type {
  Company, FinancialRatios, PiotroskiResult, HealthScore, CAGRResult,
  CashFlowQuality, WorkingCapitalEfficiency,
} from "@/lib/types";
import type { AltmanResult } from "@/lib/analysis/altman";
import type { EarlyWarningResult } from "@/lib/analysis/early_warning";

// ── Formatters ────────────────────────────────────────────────────────────────

function fmt(v: number | null, d = 2) {
  if (v === null || v === undefined || isNaN(v)) return "—";
  return v.toFixed(d);
}
function pct(v: number | null) {
  if (v === null || isNaN(v)) return "—";
  return `${(v * 100).toFixed(1)}%`;
}
function bil(v: number | null) {
  if (v === null) return "—";
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)} nghìn tỷ`;
  return `${v.toFixed(0)} tỷ`;
}
function vnd(v: number | null) {
  if (v === null) return "—";
  return Math.round(v).toLocaleString("vi-VN");
}

// ── Score Card ────────────────────────────────────────────────────────────────

function ScoreCard({ health }: { health: HealthScore }) {
  const s = health.overall_score;
  const statusEmoji = s >= 70 ? "🟢" : s >= 50 ? "🟡" : "🔴";
  const statusLabel = s >= 70 ? "KHỎE" : s >= 50 ? "TRUNG BÌNH" : "YẾU";
  return (
    <div className="score-card">
      <div className="score-top">
        <div>
          <div className="score-value">{s.toFixed(1)}<span>/100</span></div>
          <div className="score-label">Điểm sức khỏe tài chính — {health.vietnamese_rating}</div>
        </div>
        <div className="score-status">{statusEmoji} {statusLabel}</div>
      </div>
      <div className="score-bar">
        <div className="score-bar-fill" style={{ width: `${s}%` }} />
      </div>
      <div className="score-details">
        {[
          { label: "Sinh lời (30%)", value: health.components.profitability.score },
          { label: "Hiệu quả (25%)", value: health.components.efficiency.score },
          { label: "Đòn bẩy (25%)", value: health.components.leverage.score },
          { label: "Thanh khoản (20%)", value: health.components.liquidity.score },
        ].map((item) => (
          <div key={item.label}>
            <div className="score-detail-label">{item.label}</div>
            <div className="score-detail-value">{item.value.toFixed(0)}/100</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Cash Flow Quality Card ────────────────────────────────────────────────────

function CashFlowQualityCard({ cfq }: { cfq: CashFlowQuality }) {
  const score = cfq.score ?? 0;
  const barColor = score >= 80 ? "#22c55e" : score >= 60 ? "#60a5fa" : score >= 40 ? "#f59e0b" : "#ef4444";
  return (
    <div className="cfq-card">
      <div className="cfq-header">
        <div className="cfq-title-section">
          <div className="cfq-icon">💰</div>
          <div>
            <div className="cfq-title">Chất lượng Dòng tiền</div>
            <div className="cfq-subtitle">{cfq.vietnamese_rating}</div>
          </div>
        </div>
        <div className="cfq-score-section">
          <div className="cfq-score">{cfq.score !== null ? cfq.score.toFixed(1) : "—"}</div>
          <div className="cfq-score-label">/100</div>
        </div>
      </div>
      <div className="cfq-progress-bar">
        <div className="cfq-progress-fill" style={{ width: `${score}%`, background: barColor }} />
      </div>
      <div className="cfq-metrics">
        <div className="cfq-metric">
          <div className="cfq-metric-label">OCF / Net Income</div>
          <div className="cfq-metric-value">{cfq.ocf_to_net_income !== null ? cfq.ocf_to_net_income.toFixed(2) + "x" : "—"}</div>
        </div>
        <div className="cfq-metric">
          <div className="cfq-metric-label">FCF / Net Income</div>
          <div className="cfq-metric-value">{cfq.fcf_to_net_income !== null ? cfq.fcf_to_net_income.toFixed(2) + "x" : "—"}</div>
        </div>
      </div>
      {cfq.interpretation && (
        <div className="cfq-interpretation">{cfq.interpretation}</div>
      )}
    </div>
  );
}

// ── Working Capital Card ──────────────────────────────────────────────────────

function WorkingCapitalCard({ wc }: { wc: WorkingCapitalEfficiency }) {
  const ccc = wc.ccc;
  const color = ccc === null ? "var(--text-tertiary)" : ccc < 30 ? "#22c55e" : ccc < 60 ? "#60a5fa" : ccc < 90 ? "#f59e0b" : "#ef4444";
  return (
    <div className="card">
      <div className="card-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{ fontSize: "1.25rem" }}>💸</span>
          <div>
            <div className="card-title">Hiệu quả Vốn lưu động</div>
            <div className="card-subtitle">{wc.vietnamese_rating}</div>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "1.75rem", fontWeight: 700, color }}>{ccc !== null ? ccc.toFixed(0) : "—"}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>ngày CCC</div>
        </div>
      </div>
      <div className="wc-metrics">
        {[
          { label: "DSO", sublabel: "Thu tiền", value: wc.dso },
          { label: "DIO", sublabel: "Tồn kho", value: wc.dio },
          { label: "DPO", sublabel: "Trả NCC", value: wc.dpo },
        ].map((m) => (
          <div key={m.label} className="wc-metric">
            <div className="wc-metric-label">{m.label}</div>
            <div style={{ fontSize: "0.625rem", color: "var(--text-tertiary)", marginBottom: "0.25rem" }}>{m.sublabel}</div>
            <div className="wc-metric-value" style={{ color: "var(--text-primary)" }}>
              {m.value !== null ? m.value.toFixed(0) + "d" : "—"}
            </div>
          </div>
        ))}
      </div>
      {wc.interpretation && (
        <div className="cfq-interpretation" style={{ marginTop: "0.75rem" }}>{wc.interpretation}</div>
      )}
    </div>
  );
}

// ── Piotroski Card ────────────────────────────────────────────────────────────

function PiotroskiCard({ p }: { p: PiotroskiResult }) {
  const color = p.score >= 7 ? "#22c55e" : p.score >= 4 ? "#f59e0b" : "#ef4444";
  const signals = [
    { label: "ROA dương", value: p.signals.roa_positive },
    { label: "Dòng tiền hoạt động dương", value: p.signals.ocf_positive },
    { label: "ROA cải thiện so với năm trước", value: p.signals.roa_improving },
    { label: "CFO ≥ 0.8 × Net Income", value: p.signals.cfo_gt_net_income },
    { label: "Đòn bẩy giảm (tốt hơn)", value: p.signals.leverage_improving },
    { label: "Thanh khoản cải thiện", value: p.signals.current_ratio_improving },
    { label: "Không pha loãng cổ phiếu", value: p.signals.no_dilution },
    { label: "Biên lợi nhuận gộp cải thiện", value: p.signals.gross_margin_improving },
    { label: "Hiệu suất tài sản cải thiện", value: p.signals.asset_turnover_improving },
  ];
  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">🎯 Piotroski F-Score</h3>
        <div style={{ fontSize: "1.5rem", fontWeight: 700, color }}>{p.score}<span style={{ fontSize: "1rem", color: "var(--text-tertiary)" }}>/9</span></div>
      </div>
      <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: "0.75rem" }}>
        {p.interpretation}
      </p>
      <div>
        {signals.map((s) => (
          <div key={s.label} className="signal-row">
            <div className={`signal-dot ${s.value ? "pass" : "fail"}`} />
            <span className="signal-label" style={{ color: s.value ? "var(--text-primary)" : "var(--text-tertiary)" }}>
              {s.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Altman Card ───────────────────────────────────────────────────────────────

function AltmanCard({ a }: { a: AltmanResult }) {
  const color = a.zone === "safe" ? "#22c55e" : a.zone === "grey" ? "#f59e0b" : a.zone === "distress" ? "#ef4444" : "var(--text-secondary)";
  const borderColor = a.zone === "safe" ? "rgba(34,197,94,0.3)" : a.zone === "grey" ? "rgba(245,158,11,0.3)" : "rgba(239,68,68,0.3)";
  return (
    <div className="card" style={{ borderColor }}>
      <div className="card-header">
        <h3 className="card-title">⚡ Altman Z-Score</h3>
        <div style={{ fontSize: "1.5rem", fontWeight: 700, color }}>{a.z_score ?? "—"}</div>
      </div>
      <p style={{ fontSize: "0.8125rem", color, marginBottom: "0.75rem" }}>{a.vietnamese_rating}</p>
      <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: "0.75rem" }}>{a.interpretation}</p>
      {a.z_score !== null && (
        <div className="altman-components">
          {Object.entries(a.components).map(([k, v]) => (
            <div key={k} className="altman-comp">
              <span className="altman-comp-label">{k.replace("_", " ").toUpperCase()}</span>
              <span className="altman-comp-value">{v?.toFixed(3)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Early Warning Card ────────────────────────────────────────────────────────

function EarlyWarningCard({ ew }: { ew: EarlyWarningResult }) {
  const levelColor = ew.risk_level === "low" ? "#22c55e" : ew.risk_level === "medium" ? "#f59e0b" : ew.risk_level === "high" ? "#f97316" : "#ef4444";
  const levelLabel: Record<string, string> = { low: "Thấp", medium: "Trung bình", high: "Cao", critical: "Nghiêm trọng" };
  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">🚨 Cảnh báo sớm</h3>
        <div style={{ fontSize: "1.5rem", fontWeight: 700, color: levelColor }}>
          {ew.risk_score}
          <span style={{ fontSize: "0.875rem", marginLeft: "0.5rem", fontWeight: 400 }}>{levelLabel[ew.risk_level]}</span>
        </div>
      </div>
      {ew.alerts.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "0.5rem" }}>
          {ew.alerts.map((a, i) => (
            <div key={i} className={`ew-alert ${a.severity}`}>
              <span>⚠</span><span>{a.message}</span>
            </div>
          ))}
        </div>
      )}
      {ew.positive_signals.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          {ew.positive_signals.map((s, i) => (
            <div key={i} className="ew-positive"><span>✓</span><span>{s}</span></div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── CAGR Card ─────────────────────────────────────────────────────────────────

function CAGRCard({ c }: { c: CAGRResult }) {
  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">📈 CAGR ({c.years} năm)</h3>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {[
          { label: "Doanh thu", value: c.revenue_cagr },
          { label: "Lợi nhuận", value: c.profit_cagr },
          { label: "EPS", value: c.eps_cagr },
        ].map((item) => {
          const val = item.value;
          const color = val === null ? "var(--text-secondary)" : val >= 0.10 ? "#22c55e" : val >= 0 ? "#f59e0b" : "#ef4444";
          return (
            <div key={item.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>{item.label}</span>
              <span style={{ fontWeight: 600, color }}>{formatCAGR(val)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Key Metrics ───────────────────────────────────────────────────────────────

function KeyMetrics({ r }: { r: FinancialRatios }) {
  const metrics = [
    { label: "P/E", value: fmt(r.price_to_earnings, 1) },
    { label: "P/B", value: fmt(r.price_to_book, 2) },
    { label: "EV/EBITDA", value: fmt(r.ev_to_ebitda, 1) },
    { label: "EPS (VND)", value: vnd(r.eps_vnd) },
    { label: "Vốn hóa", value: bil(r.market_cap_billions) },
    { label: "ROE", value: pct(r.roe) },
    { label: "ROA", value: pct(r.roa) },
    { label: "ROIC", value: pct(r.roic) },
    { label: "Biên gộp", value: pct(r.gross_margin) },
    { label: "Biên LN ròng", value: pct(r.net_profit_margin) },
    { label: "D/E", value: fmt(r.debt_to_equity, 2) },
    { label: "Current Ratio", value: fmt(r.current_ratio, 2) },
    { label: "Quick Ratio", value: fmt(r.quick_ratio, 2) },
    { label: "Khả năng trả lãi", value: fmt(r.interest_coverage_ratio, 1) },
    { label: "Beta", value: fmt(r.beta, 2) },
  ];
  return (
    <div className="metrics-grid">
      {metrics.map((m) => (
        <div key={m.label} className="metric-card">
          <div className="metric-label">{m.label}</div>
          <div className="metric-value">{m.value}</div>
        </div>
      ))}
    </div>
  );
}

// ── Financial Table ───────────────────────────────────────────────────────────

type TableRow = Record<string, number | string | null>;

function FinancialTable({
  rows,
  cols,
}: {
  rows: TableRow[];
  cols: { key: string; label: string; format?: (v: number | null) => string }[];
}) {
  if (!rows.length) return <p style={{ color: "var(--text-secondary)", padding: "2rem" }}>Không có dữ liệu.</p>;
  const periods = rows.map((r) => r.quarter ? `${r.year} Q${r.quarter}` : String(r.year));
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>Chỉ tiêu</th>
            {periods.map((p) => <th key={p} className="number">{p}</th>)}
          </tr>
        </thead>
        <tbody>
          {cols.map((col) => (
            <tr key={col.key}>
              <td style={{ color: "var(--text-secondary)", whiteSpace: "nowrap" }}>{col.label}</td>
              {rows.map((r, i) => {
                const v = r[col.key] as number | null;
                return (
                  <td key={i} className="number">{col.format ? col.format(v) : fmt(v, 1)}</td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Tab definitions ───────────────────────────────────────────────────────────

const TABS = [
  { id: "overview", icon: "🏠", label: "Tổng quan" },
  { id: "balance", icon: "🧾", label: "Cân đối KT" },
  { id: "income", icon: "📈", label: "Kết quả KD" },
  { id: "cashflow", icon: "💸", label: "Dòng tiền" },
  { id: "ratios", icon: "📊", label: "Chỉ số TC" },
  { id: "analysis", icon: "🧠", label: "Phân tích nâng cao" },
] as const;
type TabId = (typeof TABS)[number]["id"];

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CompanyPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const symbol = ticker?.toUpperCase() ?? "";

  const [company, setCompany] = useState<Company | null>(null);
  const [analysis, setAnalysis] = useState<{
    latest_year: number | null;
    piotroski: PiotroskiResult | null;
    altman: AltmanResult | null;
    health: HealthScore | null;
    cagr: CAGRResult | null;
    early_warning: EarlyWarningResult | null;
    cashflow_quality: CashFlowQuality | null;
    working_capital: WorkingCapitalEfficiency | null;
    latest_ratios: FinancialRatios | null;
  } | null>(null);
  const [tab, setTab] = useState<TabId>("overview");
  const [tabData, setTabData] = useState<TableRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [tabLoading, setTabLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;
    setIsLoading(true);
    Promise.all([
      fetch(`/api/company/${symbol}`).then((r) => r.json()),
      fetch(`/api/company/${symbol}/analysis`).then((r) => r.json()),
    ])
      .then(([co, an]) => {
        if (co.error) { setError(co.error); return; }
        setCompany(co);
        setAnalysis(an);
      })
      .catch(() => setError("Lỗi kết nối."))
      .finally(() => setIsLoading(false));
  }, [symbol]);

  useEffect(() => {
    if (tab === "overview" || tab === "analysis" || !symbol) return;
    const tableMap: Record<string, string> = {
      balance: "balance",
      income: "income",
      cashflow: "cashflow",
      ratios: "ratios",
    };
    const tableKey = tableMap[tab];
    if (!tableKey) return;
    setTabLoading(true);
    fetch(`/api/company/${symbol}/financials?table=${tableKey}`)
      .then((r) => r.json())
      .then((d) => setTabData(d.rows ?? []))
      .catch(() => setTabData([]))
      .finally(() => setTabLoading(false));
  }, [tab, symbol]);

  if (isLoading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh", flexDirection: "column", gap: "1rem" }}>
      <div className="loading-spinner" />
      <p style={{ color: "var(--text-secondary)" }}>Đang tải...</p>
    </div>
  );

  if (error || !company) return (
    <div style={{ textAlign: "center", padding: "4rem", color: "var(--text-secondary)" }}>
      {error ?? "Không tìm thấy công ty."}
    </div>
  );

  const ratios = analysis?.latest_ratios;

  return (
    <>
      {/* Company header */}
      <div className="company-header">
        <div className="company-ticker-badge">
          {symbol.slice(0, 3)}
        </div>
        <div style={{ flex: 1 }}>
          <div className="company-name">{company.organ_name}</div>
          {company.en_organ_name && (
            <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "0.125rem" }}>{company.en_organ_name}</div>
          )}
          <div className="company-badges">
            {company.exchange && <span className="company-badge">{company.exchange}</span>}
            {company.icb_name3 && <span className="company-badge">{company.icb_name3}</span>}
            {analysis?.latest_year && <span className="company-badge">FY{analysis.latest_year}</span>}
            {company.listed_date && <span className="company-badge">Niêm yết: {company.listed_date}</span>}
          </div>
        </div>
      </div>

      {/* Health score card */}
      {analysis?.health && <ScoreCard health={analysis.health} />}

      {/* Cash Flow Quality */}
      {analysis?.cashflow_quality && <CashFlowQualityCard cfq={analysis.cashflow_quality} />}

      {/* Key metrics */}
      {ratios && <KeyMetrics r={ratios} />}

      {/* Tabs layout */}
      <div className="tabs-layout">
        {/* Left sidebar */}
        <div className="tabs-container">
          <ul className="tabs-list">
            {TABS.map((t) => (
              <li key={t.id}>
                <button
                  className={`tab-button ${tab === t.id ? "active" : ""}`}
                  onClick={() => setTab(t.id)}
                >
                  <span className="tab-icon">{t.icon}</span>
                  <span>{t.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Tab content */}
        <div>
          {tab === "overview" && (
            <div>
              {/* CAGR */}
              {analysis?.cagr && analysis.cagr.years > 0 && (
                <CAGRCard c={analysis.cagr} />
              )}
              {/* Working capital */}
              {analysis?.working_capital && (
                <div style={{ marginTop: "1rem" }}>
                  <WorkingCapitalCard wc={analysis.working_capital} />
                </div>
              )}
              {/* Overview metrics */}
              {ratios && (
                <div className="card" style={{ marginTop: "1rem" }}>
                  <div className="card-header">
                    <h3 className="card-title">📊 Tổng quan tài chính</h3>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "0.75rem" }}>
                    {[
                      { label: "EBITDA", value: bil(ratios.ebitda_billions) },
                      { label: "EBIT", value: bil(ratios.ebit_billions) },
                      { label: "Vốn hóa", value: bil(ratios.market_cap_billions) },
                      { label: "EPS (VND)", value: vnd(ratios.eps_vnd) },
                      { label: "BVPS (VND)", value: vnd(ratios.bvps_vnd) },
                      { label: "Cổ phiếu lưu hành", value: ratios.shares_outstanding_millions ? `${fmt(ratios.shares_outstanding_millions, 1)}M` : "—" },
                    ].map((item) => (
                      <div key={item.label} className="metric-card">
                        <div className="metric-label">{item.label}</div>
                        <div className="metric-value" style={{ fontSize: "1rem" }}>{item.value}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === "balance" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title">🧾 Bảng Cân đối Kế toán</h3></div>
              {tabLoading ? <div style={{ textAlign: "center", padding: "2rem" }}><div className="loading-spinner" /></div> : <FinancialTable rows={tabData} cols={BALANCE_COLS} />}
            </div>
          )}

          {tab === "income" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title">📈 Kết quả Kinh doanh</h3></div>
              {tabLoading ? <div style={{ textAlign: "center", padding: "2rem" }}><div className="loading-spinner" /></div> : <FinancialTable rows={tabData} cols={INCOME_COLS} />}
            </div>
          )}

          {tab === "cashflow" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title">💸 Báo cáo Lưu chuyển Tiền tệ</h3></div>
              {tabLoading ? <div style={{ textAlign: "center", padding: "2rem" }}><div className="loading-spinner" /></div> : <FinancialTable rows={tabData} cols={CASHFLOW_COLS} />}
            </div>
          )}

          {tab === "ratios" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title">📊 Chỉ số Tài chính</h3></div>
              {tabLoading ? <div style={{ textAlign: "center", padding: "2rem" }}><div className="loading-spinner" /></div> : <FinancialTable rows={tabData} cols={RATIOS_COLS} />}
            </div>
          )}

          {tab === "analysis" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {analysis?.piotroski && <PiotroskiCard p={analysis.piotroski} />}
              {analysis?.altman && <AltmanCard a={analysis.altman} />}
              {analysis?.early_warning && <EarlyWarningCard ew={analysis.early_warning} />}
              {!analysis?.piotroski && !analysis?.altman && (
                <div className="card">
                  <p style={{ color: "var(--text-secondary)", textAlign: "center", padding: "2rem" }}>Không đủ dữ liệu để phân tích nâng cao.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// ── Column definitions ────────────────────────────────────────────────────────

const B = (v: number | null) => v ? (v / 1e9).toFixed(1) + " tỷ" : "—";

const BALANCE_COLS = [
  { key: "total_assets", label: "Tổng tài sản", format: B },
  { key: "asset_current", label: "Tài sản ngắn hạn", format: B },
  { key: "cash_and_equivalents", label: "Tiền & tương đương", format: B },
  { key: "short_term_investments", label: "Đầu tư ngắn hạn", format: B },
  { key: "accounts_receivable", label: "Phải thu ngắn hạn", format: B },
  { key: "inventory", label: "Hàng tồn kho", format: B },
  { key: "asset_non_current", label: "Tài sản dài hạn", format: B },
  { key: "fixed_assets", label: "TSCĐ", format: B },
  { key: "long_term_investments", label: "Đầu tư dài hạn", format: B },
  { key: "liabilities_total", label: "Tổng nợ phải trả", format: B },
  { key: "liabilities_current", label: "Nợ ngắn hạn", format: B },
  { key: "liabilities_non_current", label: "Nợ dài hạn", format: B },
  { key: "equity_total", label: "Vốn chủ sở hữu", format: B },
  { key: "share_capital", label: "Vốn điều lệ", format: B },
  { key: "retained_earnings", label: "Lợi nhuận chưa phân phối", format: B },
];

const INCOME_COLS = [
  { key: "revenue", label: "Doanh thu", format: B },
  { key: "net_revenue", label: "Doanh thu thuần", format: B },
  { key: "cost_of_goods_sold", label: "Giá vốn hàng bán", format: B },
  { key: "gross_profit", label: "Lợi nhuận gộp", format: B },
  { key: "operating_profit", label: "Lợi nhuận HĐKD", format: B },
  { key: "profit_before_tax", label: "Lợi nhuận trước thuế", format: B },
  { key: "net_profit", label: "LNST", format: B },
  { key: "net_profit_parent_company", label: "LNST cổ đông công ty mẹ", format: B },
  { key: "eps", label: "EPS (VND)", format: (v: number | null) => v ? Math.round(v).toLocaleString("vi-VN") : "—" },
  { key: "revenue_growth", label: "Tăng trưởng DT", format: (v: number | null) => v !== null ? `${(v * 100).toFixed(1)}%` : "—" },
  { key: "profit_growth", label: "Tăng trưởng LN", format: (v: number | null) => v !== null ? `${(v * 100).toFixed(1)}%` : "—" },
];

const CASHFLOW_COLS = [
  { key: "net_cash_flow_from_operating_activities", label: "CF hoạt động KD", format: B },
  { key: "purchase_of_fixed_assets", label: "Mua TSCĐ (CapEx)", format: B },
  { key: "net_cash_flow_from_investing_activities", label: "CF hoạt động đầu tư", format: B },
  { key: "dividends_paid", label: "Cổ tức đã trả", format: B },
  { key: "net_cash_flow_from_financing_activities", label: "CF hoạt động tài chính", format: B },
  { key: "net_cash_flow_period", label: "CF thuần trong kỳ", format: B },
  { key: "cash_beginning_of_period", label: "Tiền đầu kỳ", format: B },
  { key: "cash_end_of_period", label: "Tiền cuối kỳ", format: B },
];

const RATIOS_COLS = [
  { key: "price_to_earnings", label: "P/E", format: (v: number | null) => fmt(v, 1) },
  { key: "price_to_book", label: "P/B", format: (v: number | null) => fmt(v, 2) },
  { key: "ev_to_ebitda", label: "EV/EBITDA", format: (v: number | null) => fmt(v, 1) },
  { key: "roe", label: "ROE", format: pct },
  { key: "roa", label: "ROA", format: pct },
  { key: "roic", label: "ROIC", format: pct },
  { key: "gross_margin", label: "Biên gộp", format: pct },
  { key: "ebit_margin", label: "Biên EBIT", format: pct },
  { key: "net_profit_margin", label: "Biên LN ròng", format: pct },
  { key: "debt_to_equity", label: "D/E", format: (v: number | null) => fmt(v, 2) },
  { key: "current_ratio", label: "Thanh toán hiện hành", format: (v: number | null) => fmt(v, 2) },
  { key: "quick_ratio", label: "Thanh toán nhanh", format: (v: number | null) => fmt(v, 2) },
  { key: "asset_turnover", label: "Vòng quay tài sản", format: (v: number | null) => fmt(v, 2) },
  { key: "inventory_turnover", label: "Vòng quay tồn kho", format: (v: number | null) => fmt(v, 1) },
  { key: "interest_coverage_ratio", label: "Khả năng trả lãi", format: (v: number | null) => fmt(v, 1) },
  { key: "beta", label: "Beta", format: (v: number | null) => fmt(v, 2) },
  { key: "dividend_payout_ratio", label: "Tỷ lệ cổ tức", format: pct },
];
