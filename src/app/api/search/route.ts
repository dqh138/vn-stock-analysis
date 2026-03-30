import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q")?.trim().slice(0, 64) ?? "";
  if (!q) return NextResponse.json([]);

  const upper = q.toUpperCase();

  const { data, error } = await supabase
    .from("stocks")
    .select("ticker,organ_name")
    .or(`ticker.ilike.${upper}%,organ_name.ilike.%${q}%`)
    .eq("status", "listed")
    .limit(20);

  if (error) return NextResponse.json([], { status: 500 });

  const tickers = (data ?? []).map((r) => r.ticker);
  if (tickers.length === 0) return NextResponse.json([]);

  const [industryRes, exchangeRes] = await Promise.all([
    supabase.from("stock_industry").select("ticker,icb_name3").in("ticker", tickers),
    supabase.from("stock_exchange").select("ticker,exchange").in("ticker", tickers),
  ]);

  const industryMap = Object.fromEntries((industryRes.data ?? []).map((r) => [r.ticker, r.icb_name3]));
  const exchangeMap = Object.fromEntries((exchangeRes.data ?? []).map((r) => [r.ticker, r.exchange]));

  const results = (data ?? []).map((row) => ({
    ticker: row.ticker,
    name: row.organ_name,
    industry: industryMap[row.ticker] ?? null,
    exchange: exchangeMap[row.ticker] ?? null,
  }));

  results.sort((a, b) => (a.ticker === upper ? -1 : b.ticker === upper ? 1 : 0));

  return NextResponse.json(results);
}
