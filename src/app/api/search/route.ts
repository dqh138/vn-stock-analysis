import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q")?.trim().slice(0, 64) ?? "";
  if (!q) return NextResponse.json([]);

  const upper = q.toUpperCase();

  // Ticker prefix match first, then name substring match
  const { data, error } = await supabase
    .from("stocks")
    .select(`
      ticker,
      organ_name,
      stock_industry!inner(icb_name3),
      stock_exchange!inner(exchange)
    `)
    .or(`ticker.ilike.${upper}%,organ_name.ilike.%${q}%`)
    .eq("status", "listed")
    .limit(20);

  if (error) return NextResponse.json([], { status: 500 });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const results = (data ?? []).map((row: any) => ({
    ticker: row.ticker,
    name: row.organ_name,
    industry: row.stock_industry?.[0]?.icb_name3 ?? null,
    exchange: row.stock_exchange?.[0]?.exchange ?? null,
  }));

  // Sort: exact ticker matches first
  results.sort((a, b) => {
    const aExact = a.ticker === upper ? -1 : 0;
    const bExact = b.ticker === upper ? -1 : 0;
    return aExact - bExact;
  });

  return NextResponse.json(results);
}
