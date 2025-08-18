// lib/supabase/client.ts - CLIENT SUPABASE SÉCURISÉ
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { Database } from '@/types/supabase' // Types à créer plus tard

// Client Supabase pour composants React
export const supabase = createClientComponentClient<Database>()

// Configuration sécurisée
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Vérifications de sécurité
if (!supabaseUrl) {
  throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_URL')
}

if (!supabaseAnonKey) {
  throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_ANON_KEY')
}

// Log de configuration (en développement seulement)
if (process.env.NEXT_PUBLIC_ENVIRONMENT === 'development') {
  console.log('🔧 Supabase configuré:', {
    url: supabaseUrl,
    environment: process.env.NEXT_PUBLIC_ENVIRONMENT,
    hasKey: !!supabaseAnonKey
  })
}

// Helpers de sécurité
export const auth = {
  // Vérifier si l'utilisateur est connecté
  async isAuthenticated(): Promise<boolean> {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      return !!session
    } catch (error) {
      console.error('❌ Erreur vérification auth:', error)
      return false
    }
  },

  // Obtenir l'utilisateur courant
  async getCurrentUser() {
    try {
      const { data: { user }, error } = await supabase.auth.getUser()
      if (error) throw error
      return user
    } catch (error) {
      console.error('❌ Erreur récupération utilisateur:', error)
      return null
    }
  },

  // Obtenir le token d'accès
  async getAccessToken(): Promise<string | null> {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      return session?.access_token || null
    } catch (error) {
      console.error('❌ Erreur récupération token:', error)
      return null
    }
  },

  // Déconnexion sécurisée
  async signOut() {
    try {
      const { error } = await supabase.auth.signOut()
      if (error) throw error
      
      // Nettoyer le localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('intelia-auth-storage')
        localStorage.removeItem('intelia-chat-storage')
      }
      
      return { success: true }
    } catch (error) {
      console.error('❌ Erreur déconnexion:', error)
      return { success: false, error }
    }
  }
}

// Helpers pour les requêtes sécurisées
export const secureRequest = {
  // GET avec authentification
  async get(url: string, options: RequestInit = {}) {
    const token = await auth.getAccessToken()
    
    if (!token) {
      throw new Error('Non authentifié')
    }

    return fetch(url, {
      ...options,
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })
  },

  // POST avec authentification
  async post(url: string, data: any, options: RequestInit = {}) {
    const token = await auth.getAccessToken()
    
    if (!token) {
      throw new Error('Non authentifié')
    }

    return fetch(url, {
      ...options,
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
      body: JSON.stringify(data),
    })
  }
}

// Export par défaut
export default supabase