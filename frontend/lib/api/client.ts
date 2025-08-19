// lib/api/client.ts - VERSION CORRIGÉE AVEC SUPABASE
import { ApiResponse } from '@/types'
import { supabase } from '@/lib/supabase/client'

class ApiClient {
  private baseURL: string
  private defaultHeaders: HeadersInit

  constructor() {
    // 🔧 CORRECTION CRITIQUE: 
    // 1. Utiliser NEXT_PUBLIC_API_BASE_URL (avec _BASE)
    // 2. Fallback SANS /api pour éviter le double /api/api/
    this.baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app'
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Origin': 'https://expert.intelia.com', // 🔧 AJOUT: Header CORS obligatoire
    }
    console.log('🔧 API Client initialisé avec baseURL:', this.baseURL)
  }

  // 🆕 NOUVELLE MÉTHODE: Récupérer le token Supabase
  private async getSupabaseToken(): Promise<string | null> {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token || null
      console.log('🔑 Token Supabase:', token ? 'présent' : 'absent')
      return token
    } catch (error) {
      console.error('❌ Erreur récupération token Supabase:', error)
      return null
    }
  }

  // 🔧 NOUVELLE MÉTHODE: Construction URL correcte avec /api/v1
  private buildFullUrl(endpoint: string): string {
    const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
    // Nettoyer l'endpoint (enlever / en début si présent)
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
    // Construire l'URL complète
    const fullUrl = `${this.baseURL}/api/${version}/${cleanEndpoint}`
    
    console.log('🔍 [ApiClient] URL construite:', {
      baseURL: this.baseURL,
      version,
      endpoint: cleanEndpoint,
      fullUrl
    })
    
    return fullUrl
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    // 🔧 CORRECTION: Utiliser la nouvelle méthode de construction URL
    const fullUrl = this.buildFullUrl(endpoint)
    
    // 🔧 CORRECTION: Récupérer automatiquement le token Supabase si pas fourni
    let headers = { ...this.defaultHeaders, ...options.headers }
    
    // Si pas d'Authorization header fourni, essayer de récupérer le token Supabase
    if (!headers['Authorization'] && !headers['authorization']) {
      const token = await this.getSupabaseToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
        console.log('🔑 Token Supabase ajouté automatiquement')
      }
    }
    
    console.log('📤 Requête API:', {
      url: fullUrl,
      method: options.method || 'GET',
      headers: headers,
      body: options.body
    })

    try {
      const response = await fetch(fullUrl, {
        ...options,
        headers,
      })

      console.log('📥 Réponse API Status:', response.status, response.statusText)

      // Vérifier si la réponse est ok
      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Réponse non-OK:', {
          status: response.status,
          statusText: response.statusText,
          errorText: errorText
        })
        
        // Gestion spécifique des erreurs d'authentification
        if (response.status === 401) {
          console.error('🚫 Erreur d\'authentification - token Supabase invalide ou expiré')
          throw new Error('Session expirée. Veuillez vous reconnecter.')
        }
        
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      // Lire la réponse
      const responseText = await response.text()
      console.log('📄 Réponse brute:', responseText)

      let data: any
      try {
        data = JSON.parse(responseText)
        console.log('✅ JSON parsé avec succès:', data)
      } catch (parseError) {
        console.error('❌ Erreur parsing JSON:', parseError)
        throw new Error(`Erreur parsing JSON: ${parseError}`)
      }

      // Retourner la réponse formatée
      const apiResponse: ApiResponse<T> = {
        success: true,
        data: data as T
      }

      console.log('🎯 Réponse finale formatée:', apiResponse)
      return apiResponse

    } catch (error: any) {
      console.error('💥 Erreur complète dans request:', {
        message: error.message,
        stack: error.stack,
        url: fullUrl,
        options: options
      })

      return {
        success: false,
        error: {
          code: 'FETCH_ERROR',
          message: error.message,
          details: {
            url: fullUrl,
            method: options.method || 'GET'
          }
        }
      }
    }
  }

  async get<T>(endpoint: string, authToken?: string): Promise<ApiResponse<T>> {
    console.log('🔍 GET Request:', endpoint)
    const headers: HeadersInit = {}
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`
    }
    return this.request<T>(endpoint, { method: 'GET', headers })
  }

  async post<T>(endpoint: string, data?: any, authToken?: string): Promise<ApiResponse<T>> {
    console.log('📮 POST Request:', endpoint, 'avec data:', data)
    const headers: HeadersInit = {}
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`
    }
    return this.request<T>(endpoint, {
      method: 'POST',
      headers,
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(endpoint: string, data?: any, authToken?: string): Promise<ApiResponse<T>> {
    const headers: HeadersInit = {}
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`
    }
    return this.request<T>(endpoint, {
      method: 'PUT',
      headers,
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string, authToken?: string): Promise<ApiResponse<T>> {
    const headers: HeadersInit = {}
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`
    }
    return this.request<T>(endpoint, { method: 'DELETE', headers })
  }

  // 🆕 NOUVELLES MÉTHODES: Versions avec auth automatique Supabase
  async getSecure<T>(endpoint: string): Promise<ApiResponse<T>> {
    console.log('🔒 GET Secure Request (Supabase):', endpoint)
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async postSecure<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    console.log('🔒 POST Secure Request (Supabase):', endpoint, 'avec data:', data)
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async putSecure<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    console.log('🔒 PUT Secure Request (Supabase):', endpoint)
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async deleteSecure<T>(endpoint: string): Promise<ApiResponse<T>> {
    console.log('🔒 DELETE Secure Request (Supabase):', endpoint)
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

export const apiClient = new ApiClient()