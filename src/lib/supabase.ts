import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl) throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL");

const key = serviceRoleKey ?? anonKey;
if (!key) throw new Error("Missing Supabase key");

export const supabase = createClient(supabaseUrl, key, {
  auth: { persistSession: false },
});
