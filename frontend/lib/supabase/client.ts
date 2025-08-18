// lib/supabase/client.ts — CLIENT SUPABASE SÉCURISÉ (timeout 25s) + DEBUG
'use client'

import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { createClient } from '@supabase/supabase-js'
import type { Database } from '@/types/supabase' // Ajustez si besoin

// Client Supabase pour composants React (inchangé)
export const supabase = createClientComponentClient<Database>()

// Configuration env
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

if (!SUPABASE_URL) throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_URL')
if (!SUPABASE_ANON_KEY) throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_ANON_KEY')

// ---- DEBUG ----
const SUPABASE_DEBUG = (
  (typeof window !== 'undefined' && (
    localStorage.getItem('SUPABASE_DEBUG') === '1' ||
    localStorage.getItem('AUTH_DEBUG') === '1'
  )) || process.env.NEXT_PUBLIC_SUPABASE_DEBUG === '1' || process.env.NEXT_PUBLIC_AUTH_DEBUG === '1'
)

const slog = (...args: any[]) => {
  if (SUPABASE_DEBUG) {
    if (typeof window !== 'undefined') console.debug('[SupabaseClient]', ...args)
    else console.debug('[SupabaseClient/SSR]', ...args)
  }
}

slog('✅ Loaded client.ts (supabase client ready)', { url: SUPABASE_URL })

// ⏳ fetch avec timeout (par défaut 25s) — idéal pour signup/signin qui peuvent être lents
let __fetchSeq = 0
export const fetchWithTimeout = (ms: number = 25000) => {
  return async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const idNum = ++__fetchSeq
    const start = typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now()
    const controller = new AbortController()
    const to = setTimeout(() => {
      controller.abort()
      try { slog(`#${idNum} ⏱️ ABORT after ${ms}ms`, (input as any)?.toString?.() ?? String(input)) } catch {}
    }, ms)

    try {
      slog(`#${idNum} → fetch start`, (input as any)?.toString?.() ?? String(input), { timeout_ms: ms })
      const res = await fetch(input, { ...init, signal: controller.signal })
      const dur = Math.round(((typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now()) - start))
      slog(`#${idNum} ← fetch end`, { status: (res as any)?.status, duration_ms: dur })
      return res
    } catch (e) {
      const dur = Math.round(((typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now()) - start))
      slog(`#${idNum} ✖ fetch error after ${dur}ms`, e)
      throw e
    } finally {
      clearTimeout(to)
    }
  }
}

// Client dédié aux opérations d’auth avec fetch temporisé (évite les faux timeouts 504)
export const supabaseAuth = createClient<Database>(SUPABASE_URL, SUPABASE_ANON_KEY, {
  global: { fetch: fetchWithTimeout(25000) },
})

slog('🔐 supabaseAuth created with 25s timeout')

// —— Helpers d’auth (conservent l’API existante) ——
export const auth = {
  async getSession() {
    const { data } = await supabase.auth.getSession()
    slog('getSession →', !!data?.session)
    return data?.session || null
  },

  async getAccessToken() {
    const session = await this.getSession()
    const token = session?.access_token || null
    slog('getAccessToken →', token ? 'present' : 'null')
    return token
  },

  async logout() {
    try {
      slog('logout() called')
      const { error } = await supabase.auth.signOut()
      if (error) throw error
      try { localStorage.removeItem('intelia-chat-storage') } catch {}
      slog('logout() → success')
      return { success: true }
    } catch (error) {
      console.error('❌ Erreur déconnexion:', error)
      return { success: false, error }
    }
  },
}

// —— Requêtes sécurisées (compat) ——
export const secureRequest = {
  async get(url: string, options: RequestInit = {}) {
    const token = await auth.getAccessToken()
    if (!token) throw new Error('Non authentifié')
    slog('secure GET', url)
    return fetch(url, {
      ...options,
      headers: { 'Authorization': `Bearer ${token}`, ...(options.headers || {}) },
      method: 'GET',
    })
  },
  async post(url: string, data: any, options: RequestInit = {}) {
    const token = await auth.getAccessToken()
    if (!token) throw new Error('Non authentifié')
    slog('secure POST', url, { hasBody: true })
    return fetch(url, {
      ...options,
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', ...(options.headers || {}) },
      body: JSON.stringify(data),
    })
  },
}

// Export par défaut (compat)
export default supabase