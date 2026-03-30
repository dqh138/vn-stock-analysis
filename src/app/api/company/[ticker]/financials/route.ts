import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> },
) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();
  const table = req.nextUrl.searchParams.get("table") ?? "ratios";
  const period = req.nextUrl.searchParams.get("period") ?? "annual"; // annual | quarterly

  const isAnnual = period === "annual";

  let query;

  if (table === "ratios") {
    query = supabase
      .from("financial_ratios")
      .select("*")
      .eq("symbol", symbol)
      .order("year", { ascending: false })
      .order("quarter", { ascending: false, nullsFirst: true });
    if (isAnnual) query = query.is("quarter", null);
    else query = query.not("quarter", "is", null);
  } else if (table === "balance") {
    query = supabase
      .from("balance_sheet")
      .select("*")
      .eq("symbol", symbol)
      .order("year", { ascending: false })
      .order("quarter", { ascending: false, nullsFirst: true });
    if (isAnnual) query = query.is("quarter", null);
    else query = query.not("quarter", "is", null);
  } else if (table === "income") {
    query = supabase
      .from("income_statement")
      .select("*")
      .eq("symbol", symbol)
      .order("year", { ascending: false })
      .order("quarter", { ascending: false, nullsFirst: true });
    if (isAnnual) query = query.is("quarter", null);
    else query = query.not("quarter", "is", null);
  } else if (table === "cashflow") {
    query = supabase
      .from("cash_flow_statement")
      .select("*")
      .eq("symbol", symbol)
      .order("year", { ascending: false })
      .order("quarter", { ascending: false, nullsFirst: true });
    if (isAnnual) query = query.is("quarter", null);
    else query = query.not("quarter", "is", null);
  } else {
    return NextResponse.json({ error: "Unknown table" }, { status: 400 });
  }

  const { data, error } = await query.limit(20);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ symbol, table, period, rows: data ?? [] });
}
