// lib/supabase/client.ts - CLIENT SUPABASE SÉCURISÉ (avec client auth à timeout étendu)
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { createClient } from '@supabase/supabase-js'
import { Database } from '@/types/supabase' // Types à créer/ajuster au besoin

// Client Supabase pour composants React (conserve le comportement d’origine)
export const supabase = createClientComponentClient<Database>()

// Configuration sécurisée (déjà utilisée dans le projet)
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Vérifications de sécurité
if (!supabaseUrl) {
  throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_URL')
}
if (!supabaseAnonKey) {
  throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_ANON_KEY')
}

// ⏳ Fetch avec timeout global (25s) — utilisé par le client d’auth pour éviter les faux timeouts
export const fetchWithTimeout = (ms: number = 25000) => {
  return (input: RequestInfo | URL, init: RequestInit = {}) => {
    const controller = new AbortController()
    const id = setTimeout(() => controller.abort(), ms)
    const merged: RequestInit = { ...init, signal: controller.signal }
    return fetch(input, merged).finally(() => clearTimeout(id))
  }
}

// Client Supabase dédié aux opérations d’auth (signup/signin) avec fetch temporisé
export const supabaseAuth = createClient<Database>(supabaseUrl, supabaseAnonKey, {
  global: { fetch: fetchWithTimeout(25000) }
})

// —— API d’assistance auth (conservée) ——
export const auth = {
  // Récupère la session courante
  async getSession() {
    const { data } = await supabase.auth.getSession()
    return data?.session || null
  },

  // Retourne le token d’accès si disponible
  async getAccessToken() {
    const session = await this.getSession()
    return session?.access_token || null
  },

  // Déconnexion + nettoyage localStorage
  async logout() {
    try {
      const { error } = await supabase.auth.signOut()
      if (error) throw error

      // Nettoyage éventuel de vos stores persistés
      try {
        localStorage.removeItem('intelia-chat-storage')
      } catch {}

      return { success: true }
    } catch (error) {
      console.error('❌ Erreur déconnexion:', error)
      return { success: false, error }
    }
  }
}

// —— Helpers pour les requêtes sécurisées (conservés) ——
export const secureRequest = {
  // GET avec authentification
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

  // POST JSON avec authentification
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

// Export par défaut (conserve la compatibilité existante)
export default supabase