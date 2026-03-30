"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

interface SearchResult {
  ticker: string;
  name: string;
  exchange: string | null;
}

export default function AppHeader() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) { setResults([]); setShowDropdown(false); return; }
    debounceRef.current = setTimeout(async () => {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      setResults(data);
      setShowDropdown(true);
    }, 200);
  }, [query]);

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
    <header className="app-header">
      <a href="/" className="header-logo">
        <div className="header-logo-icon">📊</div>
        <span>Báo cáo Tài chính</span>
      </a>

      <div className="header-search">
        <div className="search-input-wrapper">
          <span className="search-icon">🔍</span>
          <input
            ref={inputRef}
            type="text"
            className="search-input"
            placeholder="Tìm công ty (VD: VCB, HPG...) — Ctrl+K"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && results[0]) navigate(results[0].ticker);
              if (e.key === "Escape") setShowDropdown(false);
            }}
            autoComplete="off"
          />
          {showDropdown && results.length > 0 && (
            <div className="search-results">
              {results.map((r) => (
                <button key={r.ticker} className="search-result-item" onClick={() => navigate(r.ticker)}>
                  <span className="search-result-ticker">{r.ticker}</span>
                  <span className="search-result-name">{r.name}</span>
                  {r.exchange && <span className="search-result-exchange">{r.exchange}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="header-actions">
        <a href="/rankings" className="btn-icon" title="Bảng xếp hạng">🏆</a>
      </div>
    </header>
  );
}
