'use client'

import { createClientComponentClient, type SupabaseClient } from '@supabase/auth-helpers-nextjs'
// (Optionnel) si tu as des types générés par supabase:
// import type { Database } from '@/types/supabase'

// Si tu n'as pas de types, remplace SupabaseClient<any> par SupabaseClient
let _client: SupabaseClient/*<Database>*/ | null = null

export function getSupabaseClient(): SupabaseClient/*<Database>*/ {
  if (_client) return _client
  // ✅ Indispensable: client "component" côté navigateur -> gère PKCE (code_verifier en cookie)
  _client = createClientComponentClient/*<Database>*/()
  return _client
}

export function resetSupabaseClient() {
  _client = null
}
