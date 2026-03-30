"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { healthLabel, healthColor } from "@/lib/analysis/health";
import { formatCAGR } from "@/lib/analysis/cagr";
import type {
  Company, FinancialRatios, BalanceSheet,
  IncomeStatement, CashFlow, PiotroskiResult, HealthScore, CAGRResult,
} from "@/lib/types";
import type { AltmanResult } from "@/lib/analysis/altman";
import type { EarlyWarningResult } from "@/lib/analysis/early_warning";

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmt(v: number | null, decimals = 2): string {
  if (v === null || v === undefined || isNaN(v)) return "—";
  return v.toFixed(decimals);
}
function pct(v: number | null): string {
  if (v === null || isNaN(v)) return "—";
  return `${(v * 100).toFixed(1)}%`;
}
function bil(v: number | null): string {
  if (v === null) return "—";
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)} nghìn tỷ`;
  return `${v.toFixed(0)} tỷ`;
}
function vnd(v: number | null): string {
  if (v === null) return "—";
  return Math.round(v).toLocaleString("vi-VN");
}

// ── Analysis card ─────────────────────────────────────────────────────────────

function HealthCard({ health }: { health: HealthScore }) {
  const label = healthLabel(health.total);
  const color = healthColor(health.total);
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
      <p className="text-xs uppercase tracking-widest text-slate-400">Sức khỏe tài chính</p>
      <div className="mt-2 flex items-end gap-3">
        <span className={`text-4xl font-bold ${color}`}>{health.total}</span>
        <span className={`mb-1 text-sm font-medium ${color}`}>{label}</span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        {[
          { label: "Sinh lời", value: health.profitability },
          { label: "Hiệu quả", value: health.efficiency },
          { label: "Cơ cấu", value: health.capital_structure },
          { label: "Thanh khoản", value: health.liquidity },
        ].map((item) => (
          <div key={item.label} className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2">
            <span className="text-slate-400">{item.label}</span>
            <span className="font-semibold text-slate-200">{item.value}/25</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AltmanCard({ a }: { a: AltmanResult }) {
  const color = a.zone === "safe" ? "text-emerald-400" : a.zone === "grey" ? "text-amber-400" : a.zone === "distress" ? "text-rose-400" : "text-slate-400";
  const bg = a.zone === "safe" ? "border-emerald-500/30" : a.zone === "grey" ? "border-amber-500/30" : a.zone === "distress" ? "border-rose-500/30" : "border-white/10";
  return (
    <div className={`rounded-2xl border ${bg} bg-slate-900/70 p-5`}>
      <p className="text-xs uppercase tracking-widest text-slate-400">Altman Z-Score</p>
      <div className="mt-2 flex items-end gap-3">
        <span className={`text-4xl font-bold ${color}`}>{a.z_score ?? "—"}</span>
        <span className={`mb-1 text-sm font-medium ${color}`}>{a.vietnamese_rating}</span>
      </div>
      <p className="mt-2 text-xs text-slate-400">{a.interpretation}</p>
      {a.z_score !== null && (
        <div className="mt-3 grid grid-cols-2 gap-1 text-xs">
          {Object.entries(a.components).map(([k, v]) => (
            <div key={k} className="flex justify-between rounded bg-white/5 px-2 py-1">
              <span className="text-slate-500">{k.replace(/_/g, " ").replace("x", "X")}</span>
              <span className="text-slate-300">{v?.toFixed(3)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EarlyWarningCard({ ew }: { ew: EarlyWarningResult }) {
  const levelColor = ew.risk_level === "low" ? "text-emerald-400" : ew.risk_level === "medium" ? "text-amber-400" : ew.risk_level === "high" ? "text-orange-400" : "text-rose-400";
  const levelLabel: Record<string, string> = { low: "Thấp", medium: "Trung bình", high: "Cao", critical: "Nghiêm trọng" };
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
      <p className="text-xs uppercase tracking-widest text-slate-400">Cảnh báo sớm</p>
      <div className="mt-2 flex items-end gap-3">
        <span className={`text-4xl font-bold ${levelColor}`}>{ew.risk_score}</span>
        <span className={`mb-1 text-sm font-medium ${levelColor}`}>{levelLabel[ew.risk_level]}</span>
      </div>
      {ew.alerts.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs">
          {ew.alerts.map((a, i) => (
            <li key={i} className="flex gap-1.5 text-rose-300">
              <span>⚠</span><span>{a.message}</span>
            </li>
          ))}
        </ul>
      )}
      {ew.positive_signals.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs">
          {ew.positive_signals.map((s, i) => (
            <li key={i} className="flex gap-1.5 text-emerald-300">
              <span>✓</span><span>{s}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PiotroskiCard({ p }: { p: PiotroskiResult }) {
  const color = p.score >= 7 ? "text-emerald-400" : p.score >= 4 ? "text-amber-400" : "text-rose-400";
  const signals = [
    { label: "ROA dương", value: p.signals.roa_positive },
    { label: "Dòng tiền dương", value: p.signals.ocf_positive },
    { label: "ROA cải thiện", value: p.signals.roa_improving },
    { label: "CFO ≥ 0.8×NI", value: p.signals.cfo_gt_net_income },
    { label: "Đòn bẩy cải thiện", value: p.signals.leverage_improving },
    { label: "Thanh khoản tốt hơn", value: p.signals.current_ratio_improving },
    { label: "Không pha loãng", value: p.signals.no_dilution },
    { label: "Biên gộp cải thiện", value: p.signals.gross_margin_improving },
    { label: "Hiệu suất tài sản tốt", value: p.signals.asset_turnover_improving },
  ];
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
      <p className="text-xs uppercase tracking-widest text-slate-400">Piotroski F-Score</p>
      <div className="mt-2 flex items-end gap-2">
        <span className={`text-4xl font-bold ${color}`}>{p.score}</span>
        <span className="mb-1 text-sm text-slate-400">/ 9</span>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-1 text-xs">
        {signals.map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <span className={s.value ? "text-emerald-400" : "text-slate-600"}>{s.value ? "✓" : "✗"}</span>
            <span className={s.value ? "text-slate-300" : "text-slate-600"}>{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CAGRCard({ c }: { c: CAGRResult }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
      <p className="text-xs uppercase tracking-widest text-slate-400">CAGR ({c.years} năm)</p>
      <div className="mt-4 grid grid-cols-1 gap-2 text-sm">
        {[
          { label: "Doanh thu", value: c.revenue_cagr },
          { label: "Lợi nhuận", value: c.profit_cagr },
          { label: "EPS", value: c.eps_cagr },
        ].map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="text-slate-400">{item.label}</span>
            <span className={`font-semibold ${(item.value ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
              {formatCAGR(item.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Key metrics grid ──────────────────────────────────────────────────────────

function KeyMetrics({ r }: { r: FinancialRatios }) {
  const metrics = [
    { label: "P/E", value: fmt(r.price_to_earnings, 1), group: "Định giá" },
    { label: "P/B", value: fmt(r.price_to_book, 2), group: "Định giá" },
    { label: "EV/EBITDA", value: fmt(r.ev_to_ebitda, 1), group: "Định giá" },
    { label: "EPS (VND)", value: vnd(r.eps_vnd), group: "Định giá" },
    { label: "Vốn hóa (tỷ)", value: fmt(r.market_cap_billions, 0), group: "Định giá" },
    { label: "ROE", value: pct(r.roe), group: "Sinh lời" },
    { label: "ROA", value: pct(r.roa), group: "Sinh lời" },
    { label: "Biên gộp", value: pct(r.gross_margin), group: "Sinh lời" },
    { label: "Biên lợi nhuận", value: pct(r.net_profit_margin), group: "Sinh lời" },
    { label: "D/E", value: fmt(r.debt_to_equity, 2), group: "Cơ cấu" },
    { label: "Thanh toán hiện hành", value: fmt(r.current_ratio, 2), group: "Thanh khoản" },
    { label: "Thanh toán nhanh", value: fmt(r.quick_ratio, 2), group: "Thanh khoản" },
    { label: "Khả năng trả lãi", value: fmt(r.interest_coverage_ratio, 1), group: "Cơ cấu" },
    { label: "Beta", value: fmt(r.beta, 2), group: "Thị trường" },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {metrics.map((m) => (
        <div key={m.label} className="rounded-xl border border-white/10 bg-slate-900/60 px-4 py-3">
          <p className="text-xs text-slate-500">{m.label}</p>
          <p className="mt-1 font-semibold text-slate-100">{m.value}</p>
        </div>
      ))}
    </div>
  );
}

// ── Financial table ───────────────────────────────────────────────────────────

type TableRow = Record<string, number | string | null>;

function FinancialTable({
  rows,
  cols,
}: {
  rows: TableRow[];
  cols: { key: string; label: string; format?: (v: number | null) => string }[];
}) {
  if (!rows.length) return <p className="text-sm text-slate-500 py-6">Không có dữ liệu.</p>;

  const periods = rows.map((r) =>
    r.quarter ? `${r.year} Q${r.quarter}` : String(r.year)
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 text-xs text-slate-400">
            <th className="py-3 pr-4 text-left font-normal">Chỉ tiêu</th>
            {periods.map((p) => (
              <th key={p} className="py-3 px-3 text-right font-normal">{p}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cols.map((col) => (
            <tr key={col.key} className="border-b border-white/5 hover:bg-white/3">
              <td className="py-2 pr-4 text-slate-400 whitespace-nowrap">{col.label}</td>
              {rows.map((r, i) => {
                const v = r[col.key] as number | null;
                const formatted = col.format ? col.format(v) : fmt(v, 1);
                return (
                  <td key={i} className="py-2 px-3 text-right text-slate-200 whitespace-nowrap">
                    {formatted}
                  </td>
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

const TABS = ["Tổng quan", "Cân đối KT", "Kết quả KD", "Dòng tiền", "Chỉ số TC"] as const;
type Tab = (typeof TABS)[number];

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
    latest_ratios: FinancialRatios | null;
  } | null>(null);
  const [tab, setTab] = useState<Tab>("Tổng quan");
  const [tabData, setTabData] = useState<TableRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [tabLoading, setTabLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load company info + analysis
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

  // Load tab data
  useEffect(() => {
    if (tab === "Tổng quan" || !symbol) return;
    const tableMap: Record<string, string> = {
      "Cân đối KT": "balance",
      "Kết quả KD": "income",
      "Dòng tiền": "cashflow",
      "Chỉ số TC": "ratios",
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

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        Đang tải...
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        {error ?? "Không tìm thấy công ty."}
      </div>
    );
  }

  const ratios = analysis?.latest_ratios;

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-white/10 bg-slate-950/80 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <a href="/" className="text-xs text-slate-400 hover:text-slate-200">← Trang chủ</a>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold text-sky-300">{company.ticker}</h1>
            <div>
              <p className="text-lg font-semibold leading-tight">{company.organ_name}</p>
              {company.en_organ_name && (
                <p className="text-xs text-slate-400">{company.en_organ_name}</p>
              )}
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              {company.exchange && (
                <span className="rounded-full border border-sky-500/40 bg-sky-500/10 px-3 py-1 text-sky-200">
                  {company.exchange}
                </span>
              )}
              {company.icb_name3 && (
                <span className="rounded-full border border-slate-500/40 bg-slate-800 px-3 py-1 text-slate-300">
                  {company.icb_name3}
                </span>
              )}
              {analysis?.latest_year && (
                <span className="rounded-full border border-slate-600/40 px-3 py-1 text-slate-400">
                  FY{analysis.latest_year}
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
        {/* Analysis cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {analysis?.health && <HealthCard health={analysis.health} />}
          {analysis?.piotroski && <PiotroskiCard p={analysis.piotroski} />}
          {analysis?.cagr && analysis.cagr.years > 0 && <CAGRCard c={analysis.cagr} />}
          {analysis?.altman && <AltmanCard a={analysis.altman} />}
          {analysis?.early_warning && <EarlyWarningCard ew={analysis.early_warning} />}
        </div>

        {/* Key metrics */}
        {ratios && (
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-slate-400">
              Chỉ số chính
            </h2>
            <KeyMetrics r={ratios} />
          </section>
        )}

        {/* Tabs */}
        <section>
          <div className="flex gap-1 border-b border-white/10">
            {TABS.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm transition ${
                  tab === t
                    ? "border-b-2 border-sky-400 text-sky-300"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <div className="mt-4">
            {tab === "Tổng quan" ? (
              <OverviewTab ratios={analysis?.latest_ratios} />
            ) : tabLoading ? (
              <p className="py-8 text-center text-slate-500">Đang tải...</p>
            ) : tab === "Cân đối KT" ? (
              <FinancialTable
                rows={tabData}
                cols={BALANCE_COLS}
              />
            ) : tab === "Kết quả KD" ? (
              <FinancialTable rows={tabData} cols={INCOME_COLS} />
            ) : tab === "Dòng tiền" ? (
              <FinancialTable rows={tabData} cols={CASHFLOW_COLS} />
            ) : (
              <FinancialTable rows={tabData} cols={RATIOS_COLS} />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function OverviewTab({ ratios }: { ratios: FinancialRatios | null | undefined }) {
  if (!ratios) return <p className="text-slate-500 text-sm">Không có dữ liệu tổng quan.</p>;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[
        { label: "Doanh thu thuần", value: ratios.ebitda_billions ? bil(ratios.ebitda_billions) : "—" },
        { label: "EBITDA (tỷ)", value: bil(ratios.ebitda_billions) },
        { label: "Vốn hóa (tỷ)", value: bil(ratios.market_cap_billions) },
        { label: "EPS (VND)", value: vnd(ratios.eps_vnd) },
        { label: "Book Value/Share (VND)", value: vnd(ratios.bvps_vnd) },
        { label: "Cổ phiếu lưu hành (triệu)", value: fmt(ratios.shares_outstanding_millions, 1) },
      ].map((item) => (
        <div key={item.label} className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
          <p className="text-xs text-slate-500">{item.label}</p>
          <p className="mt-1 text-lg font-semibold text-slate-100">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

// ── Column definitions ────────────────────────────────────────────────────────

const BALANCE_COLS: { key: string; label: string; format?: (v: number | null) => string }[] = [
  { key: "total_assets", label: "Tổng tài sản (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "asset_current", label: "Tài sản ngắn hạn (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "cash_and_equivalents", label: "Tiền & tương đương (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "inventory", label: "Hàng tồn kho (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "asset_non_current", label: "Tài sản dài hạn (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "fixed_assets", label: "TSCĐ (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "liabilities_total", label: "Tổng nợ phải trả (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "liabilities_current", label: "Nợ ngắn hạn (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "equity_total", label: "Vốn chủ sở hữu (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
];

const INCOME_COLS: { key: string; label: string; format?: (v: number | null) => string }[] = [
  { key: "revenue", label: "Doanh thu (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "gross_profit", label: "Lợi nhuận gộp (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "operating_profit", label: "Lợi nhuận HĐKD (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "profit_before_tax", label: "Lợi nhuận trước thuế (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "net_profit", label: "Lợi nhuận sau thuế (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "net_profit_parent_company", label: "LNST cổ đông công ty mẹ (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "eps", label: "EPS (VND)", format: (v) => v ? Math.round(v).toLocaleString("vi-VN") : "—" },
  { key: "revenue_growth", label: "Tăng trưởng DT", format: (v) => v !== null ? `${(v * 100).toFixed(1)}%` : "—" },
  { key: "profit_growth", label: "Tăng trưởng LN", format: (v) => v !== null ? `${(v * 100).toFixed(1)}%` : "—" },
];

const CASHFLOW_COLS: { key: string; label: string; format?: (v: number | null) => string }[] = [
  { key: "net_cash_flow_from_operating_activities", label: "CF hoạt động KD (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "net_cash_flow_from_investing_activities", label: "CF hoạt động đầu tư (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "net_cash_flow_from_financing_activities", label: "CF hoạt động tài chính (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
  { key: "net_cash_flow_period", label: "CF thuần trong kỳ (tỷ)", format: (v) => v ? (v / 1e9).toFixed(1) : "—" },
];

const RATIOS_COLS: { key: string; label: string; format?: (v: number | null) => string }[] = [
  { key: "price_to_earnings", label: "P/E", format: (v) => fmt(v, 1) },
  { key: "price_to_book", label: "P/B", format: (v) => fmt(v, 2) },
  { key: "ev_to_ebitda", label: "EV/EBITDA", format: (v) => fmt(v, 1) },
  { key: "roe", label: "ROE", format: (v) => pct(v) },
  { key: "roa", label: "ROA", format: (v) => pct(v) },
  { key: "roic", label: "ROIC", format: (v) => pct(v) },
  { key: "gross_margin", label: "Biên gộp", format: (v) => pct(v) },
  { key: "net_profit_margin", label: "Biên lợi nhuận", format: (v) => pct(v) },
  { key: "debt_to_equity", label: "D/E", format: (v) => fmt(v, 2) },
  { key: "current_ratio", label: "Thanh toán hiện hành", format: (v) => fmt(v, 2) },
  { key: "quick_ratio", label: "Thanh toán nhanh", format: (v) => fmt(v, 2) },
  { key: "asset_turnover", label: "Vòng quay tài sản", format: (v) => fmt(v, 2) },
  { key: "interest_coverage_ratio", label: "Khả năng trả lãi", format: (v) => fmt(v, 1) },
  { key: "beta", label: "Beta", format: (v) => fmt(v, 2) },
  { key: "dividend_payout_ratio", label: "Tỷ lệ cổ tức", format: (v) => pct(v) },
];
