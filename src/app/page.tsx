"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

interface SearchResult {
  ticker: string;
  name: string;
  industry: string | null;
  exchange: string | null;
}

interface Industry {
  icb_name3: string;
  count: number;
}

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load industries on mount
  useEffect(() => {
    fetch("/api/industries")
      .then((r) => r.json())
      .then(setIndustries)
      .catch(() => {});
  }, []);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setResults([]);
      setShowDropdown(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      setResults(data);
      setShowDropdown(true);
    }, 200);
  }, [query]);

  // Ctrl+K focus
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  function navigate(ticker: string) {
    setShowDropdown(false);
    setQuery("");
    router.push(`/company/${ticker}`);
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-white/10 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">VN Stock Analysis</p>
            <h1 className="text-2xl font-semibold">Phân tích tài chính cổ phiếu Việt Nam</h1>
          </div>
          <a
            href="/rankings"
            className="rounded-full border border-sky-500/40 bg-sky-500/10 px-4 py-2 text-sm text-sky-200 hover:bg-sky-500/20 transition"
          >
            Rankings →
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-12">
        {/* Search */}
        <div className="relative mx-auto max-w-xl">
          <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 focus-within:border-sky-500/60">
            <svg className="h-5 w-5 shrink-0 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              placeholder="Tìm mã cổ phiếu hoặc tên công ty... (Ctrl+K)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && results[0]) navigate(results[0].ticker);
                if (e.key === "Escape") setShowDropdown(false);
              }}
              className="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
            />
          </div>

          {showDropdown && results.length > 0 && (
            <div className="absolute left-0 right-0 top-full z-20 mt-2 rounded-2xl border border-white/10 bg-slate-900 shadow-xl">
              {results.map((r) => (
                <button
                  key={r.ticker}
                  onClick={() => navigate(r.ticker)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-white/5 first:rounded-t-2xl last:rounded-b-2xl"
                >
                  <span className="w-14 shrink-0 font-mono text-sm font-semibold text-sky-300">{r.ticker}</span>
                  <span className="flex-1 truncate text-sm text-slate-200">{r.name}</span>
                  {r.exchange && (
                    <span className="shrink-0 text-xs text-slate-500">{r.exchange}</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Industries grid */}
        <div className="mt-16">
          <h2 className="mb-5 text-lg font-semibold text-slate-200">Ngành</h2>
          {industries.length === 0 ? (
            <p className="text-sm text-slate-500">Đang tải...</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
              {industries.map((ind) => (
                <a
                  key={ind.icb_name3}
                  href={`/rankings?industry=${encodeURIComponent(ind.icb_name3)}`}
                  className="rounded-xl border border-white/10 bg-slate-900/70 p-4 hover:border-sky-500/40 hover:bg-slate-900 transition"
                >
                  <p className="text-sm font-medium text-slate-200 leading-snug">{ind.icb_name3}</p>
                  <p className="mt-1 text-xs text-slate-500">{ind.count} công ty</p>
                </a>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
