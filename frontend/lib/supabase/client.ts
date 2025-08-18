// lib/supabase/client.ts - CLIENT SUPABASE SÉCURISÉ (ajout supabaseAuth + timeout 25s)

'use client'

import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { createClient } from '@supabase/supabase-js'
import type { Database } from '@/types/supabase' // adaptez si besoin

// Client Supabase pour composants React (inchangé)
export const supabase = createClientComponentClient<Database>()

// Configuration
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

if (!SUPABASE_URL) throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_URL')
if (!SUPABASE_ANON_KEY) throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_ANON_KEY')

// ⏳ Fetch avec timeout (25s) pour éviter les faux timeouts sur /auth
export const fetchWithTimeout = (ms: number = 25000) => {
  return (input: RequestInfo | URL, init: RequestInit = {}) => {
    const controller = new AbortController()
    const id = setTimeout(() => controller.abort(), ms)
    const merged: RequestInit = { ...init, signal: controller.signal }
    return fetch(input, merged).finally(() => clearTimeout(id))
  }
}

// Client dédié aux opérations d’auth (signup/signin) avec timeout étendu
export const supabaseAuth = createClient<Database>(SUPABASE_URL, SUPABASE_ANON_KEY, {
  global: { fetch: fetchWithTimeout(25000) }
})

// Helpers de sécurité
export const auth = {
  async isAuthenticated(): Promise<boolean> {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      return !!session
    } catch (error) {
      console.error('❌ isAuthenticated error:', error)
      return false
    }
  },

  async getAccessToken(): Promise<string | null> {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      return session?.access_token || null
    } catch (error) {
      console.error('❌ getAccessToken error:', error)
      return null
    }
  },

  async logout() {
    try {
      const { error } = await supabase.auth.signOut()
      if (error) throw error
      try { localStorage.removeItem('intelia-chat-storage') } catch {}
      return { success: true }
    } catch (error) {
      console.error('❌ Erreur déconnexion:', error)
      return { success: false, error }
    }
  }
}

// Requêtes sécurisées
export const secureRequest = {
  async get(url: string, options: RequestInit = {}) {
    const token = await auth.getAccessToken()
    if (!token) throw new Error('Non authentifié')

    return fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        ...(options.headers || {}),
      },
      method: 'GET'
    })
  },

  async post(url: string, data: any, options: RequestInit = {}) {
    const token = await auth.getAccessToken()
    if (!token) throw new Error('Non authentifié')

    return fetch(url, {
      ...options,
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      body: JSON.stringify(data),
    })
  }
}

// Export par défaut (compat)
export default supabase
