/**
 * Singleton
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
"use client";

import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";

// Let TS infer the exact client type from the helper
let _client: ReturnType<typeof createClientComponentClient> | null = null;

export function getSupabaseClient() {
  if (_client) return _client;
  _client = createClientComponentClient();
  return _client;
}

export function resetSupabaseClient() {
  _client = null;
}
