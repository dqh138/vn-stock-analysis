import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

// --- Percentile helpers (ported from rankings.py) ---

function percentileRank(sorted: number[], x: number | null): number | null {
  if (x === null || sorted.length === 0) return null;
  let lo = 0, hi = 0;
  for (let i = 0; i < sorted.length; i++) {
    if (sorted[i] < x) lo = i + 1;
    if (sorted[i] <= x) hi = i + 1;
  }
  const avgRank = (lo + hi) / 2;
  return Math.max(0, Math.min(1, avgRank / (sorted.length === 1 ? 1 : sorted.length - 1)));
}

function weightedMean(pairs: [number | null, number][]): number | null {
  let total = 0, weight = 0;
  for (const [v, w] of pairs) {
    if (v === null || w <= 0) continue;
    total += v * w;
    weight += w;
  }
  return weight > 0 ? total / weight : null;
}

function scoreFromPercentile(pct: number | null, invert = false): number | null {
  if (pct === null) return null;
  const s = invert ? (1 - pct) * 100 : pct * 100;
  return Math.max(0, Math.min(100, s));
}

function epsCagr(start: number, end: number, years: number): number | null {
  if (years <= 0 || start <= 0 || end <= 0) return null;
  try { return Math.pow(end / start, 1 / years) - 1; } catch { return null; }
}

export async function GET(req: NextRequest) {
  const params = req.nextUrl.searchParams;
  const year = parseInt(params.get("year") ?? "0") || null;
  const industry = params.get("industry") ?? null;
  const exchange = params.get("exchange") ?? null;
  const sortBy = params.get("sort_by") ?? "overall";
  const limit = Math.min(parseInt(params.get("limit") ?? "50") || 50, 200);

  // Resolve target year
  let targetYear = year;
  if (!targetYear) {
    const { data: yearData } = await supabase
      .from("financial_ratios").select("year").is("quarter", null).order("year", { ascending: false }).limit(1).single();
    targetYear = yearData?.year ?? new Date().getFullYear() - 1;
  }

  // Fetch current year ratios (full market scan)
  const { data: ratios, error } = await supabase
    .from("financial_ratios")
    .select("symbol,year,price_to_earnings,price_to_book,ev_to_ebitda,eps_vnd,bvps_vnd,roe,roa,net_profit_margin,gross_margin,asset_turnover,debt_to_equity,current_ratio,market_cap_billions")
    .eq("year", targetYear)
    .is("quarter", null)
    .limit(2000);

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (!ratios || ratios.length === 0) return NextResponse.json({ year: targetYear, rankings: [] });

  const tickers = ratios.map((r) => r.symbol as string);

  // Fetch EPS 5 years ago for CAGR
  const startYear = targetYear - 5;
  const [stocksRes, industryRes, exchangeRes, epsStartRes] = await Promise.all([
    supabase.from("stocks").select("ticker,organ_name,status").in("ticker", tickers),
    supabase.from("stock_industry").select("ticker,icb_name3").in("ticker", tickers),
    supabase.from("stock_exchange").select("ticker,exchange").in("ticker", tickers),
    supabase.from("financial_ratios").select("symbol,eps_vnd").eq("year", startYear).is("quarter", null).in("symbol", tickers),
  ]);

  const stockMap = Object.fromEntries((stocksRes.data ?? []).map((s) => [s.ticker, s]));
  const industryMap = Object.fromEntries((industryRes.data ?? []).map((s) => [s.ticker, s.icb_name3 as string]));
  const exchangeMap = Object.fromEntries((exchangeRes.data ?? []).map((s) => [s.ticker, s.exchange as string]));
  const epsStartMap = Object.fromEntries((epsStartRes.data ?? []).filter((r) => r.eps_vnd).map((r) => [r.symbol, r.eps_vnd as number]));

  // Filter to listed stocks
  const rows = ratios.filter((r) => {
    const stock = stockMap[r.symbol as string];
    if (!stock || stock.status !== "listed") return false;
    if (industry && industryMap[r.symbol as string] !== industry) return false;
    if (exchange && exchangeMap[r.symbol as string] !== exchange) return false;
    return true;
  });

  // Build sorted distributions for percentile ranking
  const peList: number[] = [], pbList: number[] = [], evList: number[] = [];
  const roeList: number[] = [], marginList: number[] = [], epsCagrList: number[] = [];

  const epsCagrMap: Record<string, number> = {};
  for (const r of rows) {
    const sym = r.symbol as string;
    const endEps = r.eps_vnd as number | null;
    const startEps = epsStartMap[sym];
    if (endEps && startEps && endEps > 0 && startEps > 0) {
      const c = epsCagr(startEps, endEps, 5);
      if (c !== null) { epsCagrMap[sym] = c; epsCagrList.push(c); }
    }
  }

  // Build market distributions (industry-specific omitted for simplicity — use market-wide)
  for (const r of rows) {
    const pe = r.price_to_earnings as number | null;
    const pb = r.price_to_book as number | null;
    const ev = r.ev_to_ebitda as number | null;
    const roe = r.roe as number | null;
    const margin = r.net_profit_margin as number | null;
    const eps = r.eps_vnd as number | null;
    const bvps = r.bvps_vnd as number | null;

    if (pe && pe > 0 && eps && eps > 0) peList.push(pe);
    if (pb && pb > 0 && bvps && bvps > 0) pbList.push(pb);
    if (ev && ev > 0) evList.push(ev);
    if (roe !== null) roeList.push(roe);
    if (margin !== null) marginList.push(margin);
  }

  peList.sort((a, b) => a - b);
  pbList.sort((a, b) => a - b);
  evList.sort((a, b) => a - b);
  roeList.sort((a, b) => a - b);
  marginList.sort((a, b) => a - b);
  epsCagrList.sort((a, b) => a - b);

  // Score each company
  const scored = rows.map((row) => {
    const sym = row.symbol as string;
    const pe = row.price_to_earnings as number | null;
    const pb = row.price_to_book as number | null;
    const ev = row.ev_to_ebitda as number | null;
    const roe = row.roe as number | null;
    const margin = row.net_profit_margin as number | null;
    const eps = row.eps_vnd as number | null;
    const bvps = row.bvps_vnd as number | null;

    // Valuation: lower P/E, P/B, EV/EBITDA = better → invert=true
    const peScore = scoreFromPercentile(pe && pe > 0 && eps && eps > 0 ? percentileRank(peList, pe) : null, true);
    const pbScore = scoreFromPercentile(pb && pb > 0 && bvps && bvps > 0 ? percentileRank(pbList, pb) : null, true);
    const evScore = scoreFromPercentile(ev && ev > 0 ? percentileRank(evList, ev) : null, true);
    const valuation_score = weightedMean([[peScore, 0.40], [pbScore, 0.30], [evScore, 0.30]]);

    // Valuation band
    const valPctAvg = weightedMean([
      [pe && pe > 0 && eps && eps > 0 ? percentileRank(peList, pe) : null, 0.40],
      [pb && pb > 0 && bvps && bvps > 0 ? percentileRank(pbList, pb) : null, 0.30],
      [ev && ev > 0 ? percentileRank(evList, ev) : null, 0.30],
    ]);
    const valuation_band = valPctAvg === null ? "unknown" : valPctAvg <= 0.33 ? "cheap" : valPctAvg >= 0.67 ? "expensive" : "fair";

    // Growth: higher EPS CAGR + ROE + margin = better → invert=false
    const epsCagrVal = epsCagrMap[sym] ?? null;
    const epsCagrScore = scoreFromPercentile(epsCagrList.length > 0 ? percentileRank(epsCagrList, epsCagrVal) : null);
    let growth_score: number | null = null;
    let growth_band = "unknown";
    if (epsCagrScore !== null) {
      const roeScore = scoreFromPercentile(roeList.length > 0 ? percentileRank(roeList, roe) : null);
      const marginScore = scoreFromPercentile(marginList.length > 0 ? percentileRank(marginList, margin) : null);
      growth_score = weightedMean([[epsCagrScore, 0.60], [roeScore, 0.20], [marginScore, 0.20]]);
      growth_band = growth_score === null ? "unknown" : growth_score >= 70 ? "high" : growth_score >= 40 ? "medium" : "low";
    }

    const overall_score =
      sortBy === "valuation" ? valuation_score :
      sortBy === "growth" ? growth_score :
      weightedMean([[valuation_score, 0.50], [growth_score, 0.50]]);

    return {
      ticker: sym,
      organ_name: stockMap[sym]?.organ_name ?? sym,
      icb_name3: industryMap[sym] ?? null,
      exchange: exchangeMap[sym] ?? null,
      pe: pe ?? null,
      pb: pb ?? null,
      roe: roe ?? null,
      eps_vnd: eps ?? null,
      net_profit_margin: margin ?? null,
      eps_cagr_5y: epsCagrVal !== null ? Math.round(epsCagrVal * 1000) / 10 : null, // as %
      valuation_score: valuation_score !== null ? Math.round(valuation_score * 10) / 10 : null,
      growth_score: growth_score !== null ? Math.round(growth_score * 10) / 10 : null,
      valuation_band,
      growth_band,
      score: overall_score ?? 0,
    };
  });

  scored.sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  const rankings = scored.slice(0, limit).map((r, i) => ({ rank: i + 1, ...r }));

  return NextResponse.json({ year: targetYear, rankings });
}
