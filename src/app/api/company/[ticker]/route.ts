import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> },
) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();

  const [stockRes, exchangeRes, industryRes] = await Promise.all([
    supabase.from("stocks").select("ticker,organ_name,en_organ_name,organ_short_name,status,listed_date").eq("ticker", symbol).single(),
    supabase.from("stock_exchange").select("exchange").eq("ticker", symbol).limit(1).single(),
    supabase.from("stock_industry").select("icb_name3,icb_name2,icb_code").eq("ticker", symbol).limit(1).single(),
  ]);

  if (stockRes.error || !stockRes.data) {
    return NextResponse.json({ error: "Company not found" }, { status: 404 });
  }

  const s = stockRes.data;
  return NextResponse.json({
    ticker: s.ticker,
    organ_name: s.organ_name,
    en_organ_name: s.en_organ_name,
    organ_short_name: s.organ_short_name,
    status: s.status,
    listed_date: s.listed_date,
    exchange: exchangeRes.data?.exchange ?? null,
    icb_name3: industryRes.data?.icb_name3 ?? null,
    icb_name2: industryRes.data?.icb_name2 ?? null,
    icb_code: industryRes.data?.icb_code ?? null,
  });
}
