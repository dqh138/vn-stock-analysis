import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(req: NextRequest) {
  const params = req.nextUrl.searchParams;
  const year = parseInt(params.get("year") ?? "0") || null;
  const industry = params.get("industry") ?? null;
  const exchange = params.get("exchange") ?? null;
  const sortBy = params.get("sort_by") ?? "overall";
  const limit = Math.min(parseInt(params.get("limit") ?? "50") || 50, 200);

  // Get latest available year if not specified
  let targetYear = year;
  if (!targetYear) {
    const { data: yearData } = await supabase
      .from("financial_ratios")
      .select("year")
      .is("quarter", null)
      .order("year", { ascending: false })
      .limit(1)
      .single();
    targetYear = yearData?.year ?? new Date().getFullYear() - 1;
  }

  // Build query: join ratios with company info
  let query = supabase
    .from("financial_ratios")
    .select(`
      symbol,
      year,
      price_to_earnings,
      price_to_book,
      roe,
      roa,
      eps_vnd,
      net_profit_margin,
      gross_margin,
      asset_turnover,
      debt_to_equity,
      current_ratio,
      market_cap_billions,
      stocks!inner(organ_name, status),
      stock_industry!inner(icb_name3),
      stock_exchange!inner(exchange)
    `)
    .eq("year", targetYear)
    .is("quarter", null)
    .eq("stocks.status", "listed");

  if (industry) {
    query = query.eq("stock_industry.icb_name3", industry);
  }
  if (exchange) {
    query = query.eq("stock_exchange.exchange", exchange);
  }

  const { data, error } = await query.limit(500);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  // Score each company
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const scored = (data ?? []).map((row: any) => {
    const pe = row.price_to_earnings as number | null;
    const pb = row.price_to_book as number | null;
    const roe = row.roe as number | null;
    const roa = row.roa as number | null;
    const margin = row.net_profit_margin as number | null;
    const de = row.debt_to_equity as number | null;
    const cr = row.current_ratio as number | null;
    const at = row.asset_turnover as number | null;

    // Valuation score: lower P/E and P/B is better (value)
    let valScore = 0;
    if (pe !== null && pe > 0 && pe < 50) valScore += (50 - pe) / 50 * 30;
    if (pb !== null && pb > 0 && pb < 5) valScore += (5 - pb) / 5 * 20;

    // Growth/quality score
    let qualScore = 0;
    if (roe !== null) qualScore += Math.min(roe * 100, 30);
    if (roa !== null) qualScore += Math.min(roa * 100, 15);
    if (margin !== null) qualScore += Math.min(margin * 100, 15);
    if (de !== null && de < 2) qualScore += (2 - de) / 2 * 10;
    if (cr !== null && cr >= 1) qualScore += Math.min((cr - 1) * 5, 10);
    if (at !== null) qualScore += Math.min(at * 10, 10);

    const score = sortBy === "valuation" ? valScore
      : sortBy === "growth" ? qualScore
      : (valScore + qualScore) / 2;

    return {
      ticker: row.symbol,
      organ_name: (row.stocks as { organ_name: string }).organ_name,
      icb_name3: (row.stock_industry as Array<{ icb_name3: string }>)[0]?.icb_name3 ?? null,
      exchange: (row.stock_exchange as Array<{ exchange: string }>)[0]?.exchange ?? null,
      pe,
      pb,
      roe,
      eps_vnd: row.eps_vnd as number | null,
      net_profit_margin: margin,
      score,
    };
  });

  scored.sort((a, b) => b.score - a.score);
  const rankings = scored.slice(0, limit).map((r, i) => ({ rank: i + 1, ...r }));

  return NextResponse.json({ year: targetYear, rankings });
}
