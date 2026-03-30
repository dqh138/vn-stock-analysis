"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

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

function fmt(v: number | null, decimals = 1): string {
  if (v === null || isNaN(v)) return "—";
  return v.toFixed(decimals);
}

function pct(v: number | null): string {
  if (v === null || isNaN(v)) return "—";
  return `${(v * 100).toFixed(1)}%`;
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
      .then((r) => r.json())
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .then((data: any[]) => setIndustries(data.map((d) => d.icb_name3)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setIsLoading(true);
    const params = new URLSearchParams({ sort_by: sortBy, limit: "100" });
    if (industry) params.set("industry", industry);
    if (exchange) params.set("exchange", exchange);

    fetch(`/api/rankings?${params}`)
      .then((r) => r.json())
      .then((data) => {
        setRows(data.rankings ?? []);
        setYear(data.year ?? null);
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [sortBy, industry, exchange]);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/10 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-6 py-5">
          <div className="flex-1">
            <a href="/" className="text-xs text-slate-400 hover:text-slate-200">← Trang chủ</a>
            <h1 className="mt-1 text-2xl font-semibold">
              Rankings {year ? <span className="text-slate-400 text-lg font-normal">{year}</span> : ""}
            </h1>
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            <FilterSelect
              value={sortBy}
              onChange={setSortBy}
              options={[
                { value: "overall", label: "Overall" },
                { value: "valuation", label: "Valuation" },
                { value: "growth", label: "Quality" },
              ]}
            />
            <FilterSelect
              value={exchange}
              onChange={setExchange}
              options={[
                { value: "", label: "All exchanges" },
                { value: "HOSE", label: "HOSE" },
                { value: "HNX", label: "HNX" },
                { value: "UPCOM", label: "UPCOM" },
              ]}
            />
            <FilterSelect
              value={industry}
              onChange={setIndustry}
              options={[
                { value: "", label: "All industries" },
                ...industries.map((i) => ({ value: i, label: i })),
              ]}
            />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {isLoading ? (
          <p className="text-slate-400 text-center py-16">Đang tải...</p>
        ) : rows.length === 0 ? (
          <p className="text-slate-400 text-center py-16">Không có dữ liệu.</p>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-white/10">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-xs uppercase tracking-wider text-slate-400">
                  <th className="px-4 py-3 text-left">#</th>
                  <th className="px-4 py-3 text-left">Mã</th>
                  <th className="px-4 py-3 text-left">Công ty</th>
                  <th className="px-4 py-3 text-left">Ngành</th>
                  <th className="px-4 py-3 text-center">Sàn</th>
                  <th className="px-4 py-3 text-right">P/E</th>
                  <th className="px-4 py-3 text-right">P/B</th>
                  <th className="px-4 py-3 text-right">ROE</th>
                  <th className="px-4 py-3 text-right">Biên LN</th>
                  <th className="px-4 py-3 text-right">EPS CAGR 5Y</th>
                  <th className="px-4 py-3 text-right">Đ.Giá trị</th>
                  <th className="px-4 py-3 text-right">Đ.Tăng trưởng</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.ticker}
                    className="border-b border-white/5 hover:bg-white/3 transition"
                  >
                    <td className="px-4 py-3 text-slate-500">{row.rank}</td>
                    <td className="px-4 py-3">
                      <a
                        href={`/company/${row.ticker}`}
                        className="font-mono font-semibold text-sky-300 hover:text-sky-200"
                      >
                        {row.ticker}
                      </a>
                    </td>
                    <td className="px-4 py-3 max-w-48 truncate text-slate-200">{row.organ_name}</td>
                    <td className="px-4 py-3 max-w-36 truncate text-slate-400 text-xs">{row.icb_name3 ?? "—"}</td>
                    <td className="px-4 py-3 text-center text-xs text-slate-400">{row.exchange ?? "—"}</td>
                    <td className="px-4 py-3 text-right text-slate-200">{fmt(row.pe)}</td>
                    <td className="px-4 py-3 text-right text-slate-200">{fmt(row.pb)}</td>
                    <td className="px-4 py-3 text-right text-emerald-300">{pct(row.roe)}</td>
                    <td className="px-4 py-3 text-right text-slate-200">{pct(row.net_profit_margin)}</td>
                    <td className="px-4 py-3 text-right text-slate-200">
                      {row.eps_cagr_5y !== null ? `${row.eps_cagr_5y > 0 ? "+" : ""}${row.eps_cagr_5y.toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        row.valuation_band === "cheap" ? "bg-emerald-500/20 text-emerald-300" :
                        row.valuation_band === "expensive" ? "bg-red-500/20 text-red-300" :
                        "bg-slate-700 text-slate-300"
                      }`}>
                        {row.valuation_band === "cheap" ? "Rẻ" : row.valuation_band === "expensive" ? "Đắt" : row.valuation_band === "fair" ? "Hợp lý" : "—"}
                        {row.valuation_score !== null ? ` ${Math.round(row.valuation_score)}` : ""}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        row.growth_band === "high" ? "bg-sky-500/20 text-sky-300" :
                        row.growth_band === "low" ? "bg-slate-700 text-slate-400" :
                        "bg-slate-700 text-slate-300"
                      }`}>
                        {row.growth_band === "high" ? "Cao" : row.growth_band === "medium" ? "TB" : row.growth_band === "low" ? "Thấp" : "—"}
                        {row.growth_score !== null ? ` ${Math.round(row.growth_score)}` : ""}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}

function FilterSelect({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-full border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:outline-none"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value} className="bg-slate-900">
          {o.label}
        </option>
      ))}
    </select>
  );
}

export default function RankingsPage() {
  return (
    <Suspense>
      <RankingsTable />
    </Suspense>
  );
}
