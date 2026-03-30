import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> },
) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();

  const { data, error } = await supabase
    .from("stocks")
    .select(`
      ticker,
      organ_name,
      en_organ_name,
      organ_short_name,
      status,
      listed_date,
      stock_exchange(exchange),
      stock_industry(icb_name3, icb_name2, icb_code)
    `)
    .eq("ticker", symbol)
    .single();

  if (error || !data) {
    return NextResponse.json({ error: "Company not found" }, { status: 404 });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const row = data as any;
  return NextResponse.json({
    ticker: row.ticker,
    organ_name: row.organ_name,
    en_organ_name: row.en_organ_name,
    organ_short_name: row.organ_short_name,
    status: row.status,
    listed_date: row.listed_date,
    exchange: row.stock_exchange?.[0]?.exchange ?? null,
    icb_name3: row.stock_industry?.[0]?.icb_name3 ?? null,
    icb_name2: row.stock_industry?.[0]?.icb_name2 ?? null,
    icb_code: row.stock_industry?.[0]?.icb_code ?? null,
  });
}
