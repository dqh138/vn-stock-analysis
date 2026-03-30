import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET() {
  const { data, error } = await supabase
    .from("stock_industry")
    .select("icb_name3, icb_code3")
    .not("icb_name3", "is", null);

  if (error) return NextResponse.json([], { status: 500 });

  // Count companies per industry
  const counts = new Map<string, { icb_name3: string; icb_code3: string; count: number }>();
  for (const row of data ?? []) {
    const key = row.icb_name3 as string;
    if (!counts.has(key)) {
      counts.set(key, { icb_name3: key, icb_code3: row.icb_code3 ?? "", count: 0 });
    }
    counts.get(key)!.count++;
  }

  const industries = Array.from(counts.values()).sort((a, b) => b.count - a.count);
  return NextResponse.json(industries);
}
