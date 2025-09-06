// lib/api/client.ts - VERSION CORRIGÉE SANS DOUBLE /api

import { ApiResponse } from '@/types'
import { getSupabaseClient } from '@/lib/supabase/singleton'

class ApiClient {
  private baseURL: string
  private defaultHeaders: HeadersInit

  constructor() {
    // CORRECTION: Nettoyer le baseURL pour éviter le double /api
    const rawBaseURL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert.intelia.com'
    // Enlever /api à la fin s'il est présent
    this.baseURL = rawBaseURL.replace(/\/api\/?$/, '')
    
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Origin': 'https://expert.intelia.com',
    }
    console.log('🔧 API Client initialisé avec baseURL nettoyé:', this.baseURL)
  }

  // Méthode de récupération du token - LOGIQUE DU BACKUP QUI FONCTIONNE
  private async getSupabaseToken(): Promise<string | null> {
    try {
      console.log('[apiClient] 🔍 Récupération token avec logique backup...')
      
      // Méthode 1: Récupérer depuis intelia-expert-auth (PRIORITÉ)
      console.log('[apiClient] 🔍 Tentative récupération depuis intelia-expert-auth...')
      const authData = localStorage.getItem('intelia-expert-auth')
      if (authData) {
        const parsed = JSON.parse(authData)
        if (parsed.access_token) {
          console.log('[apiClient] ✅ Token récupéré depuis intelia-expert-auth')
          console.log('[apiClient] 📋 Token preview:', parsed.access_token.substring(0, 30) + '...')
          
          // Vérifier que le token n'est pas expiré
          try {
            const tokenParts = parsed.access_token.split('.')
            if (tokenParts.length === 3) {
              const payload = JSON.parse(atob(tokenParts[1]))
              const now = Math.floor(Date.now() / 1000)
              const isExpired = payload.exp < now
              
              if (isExpired) {
                console.warn('[apiClient] ⚠️ Token expiré dans intelia-expert-auth')
              } else {
                console.log('[apiClient] ✅ Token valide, expire dans:', Math.floor((payload.exp - now) / 60), 'minutes')
                return parsed.access_token
              }
            }
          } catch (decodeError) {
            console.log('[apiClient] 📋 Token JWT non décodable, utilisation directe')
            return parsed.access_token
          }
        }
      }
      
      // Méthode 2: Fallback vers Supabase store (si intelia-expert-auth échoue)
      console.log('[apiClient] 🔍 Tentative fallback vers supabase-auth-store...')
      const supabaseStore = localStorage.getItem('supabase-auth-store')
      if (supabaseStore) {
        const parsed = JSON.parse(supabaseStore)
        const possibleTokens = [
          parsed.state?.session?.access_token,
          parsed.state?.user?.access_token,
          parsed.access_token
        ]
        
        for (const token of possibleTokens) {
          if (token && typeof token === 'string' && token.length > 20) {
            console.log('[apiClient] ✅ Token fallback trouvé dans supabase-auth-store')
            return token
          }
        }
      }
      
      // Méthode 3: Session Supabase directe
      console.log('[apiClient] 🔍 Tentative session Supabase directe...')
      const supabase = getSupabaseClient()
      const { data: { session } } = await supabase.auth.getSession()
      if (session?.access_token) {
        console.log('[apiClient] ✅ Token trouvé via session Supabase')
        return session.access_token
      }
      
      // Méthode 4: Dernière chance avec les cookies
      console.log('[apiClient] 🔍 Tentative dernière chance avec cookies...')
      const cookies = document.cookie.split(';')
      for (const cookie of cookies) {
        if (cookie.includes('sb-') && cookie.includes('auth-token')) {
          try {
            const cookieValue = cookie.split('=')[1]
            const decoded = decodeURIComponent(cookieValue)
            const parsed = JSON.parse(decoded)
            if (Array.isArray(parsed) && parsed[0] && typeof parsed[0] === 'string') {
              console.log('[apiClient] ✅ Token trouvé dans cookies')
              return parsed[0]
            }
          } catch (e) {
            continue
          }
        }
      }
      
      console.error('[apiClient] ❌ Aucun token trouvé dans aucune source')
      return null
      
    } catch (error) {
      console.error('[apiClient] ❌ Erreur récupération token:', error)
      return null
    }
  }

  // CORRECTION: Construction URL sans duplication
  private buildFullUrl(endpoint: string): string {
    const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
    // Nettoyer l'endpoint (enlever / en début si présent)
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
    
    // CORRECTION: Construire l'URL sans duplication d'api
    const fullUrl = `${this.baseURL}/api/${version}/${cleanEndpoint}`
    
    console.log('🔗 [ApiClient] URL construite:', {
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
    const fullUrl = this.buildFullUrl(endpoint)
    
    // Récupérer automatiquement le token Supabase si pas fourni
    let headers = { ...this.defaultHeaders, ...options.headers }
    
    // Si pas d'Authorization header fourni, essayer de récupérer le token Supabase
    if (!headers['Authorization'] && !headers['authorization']) {
      const token = await this.getSupabaseToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
        console.log('🔑 Token Supabase (singleton) ajouté automatiquement')
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
    console.log('📝 PUT Request:', endpoint, 'avec data:', data)
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
    console.log('🗑️ DELETE Request:', endpoint)
    const headers: HeadersInit = {}
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`
    }
    return this.request<T>(endpoint, { method: 'DELETE', headers })
  }

  async patch<T>(endpoint: string, data?: any, authToken?: string): Promise<ApiResponse<T>> {
    console.log('📄 PATCH Request:', endpoint, 'avec data:', data)
    const headers: HeadersInit = {}
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`
    }
    return this.request<T>(endpoint, {
      method: 'PATCH',
      headers,
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  // Versions avec auth automatique Supabase (singleton)
  async getSecure<T>(endpoint: string): Promise<ApiResponse<T>> {
    console.log('🔐 GET Secure Request (Supabase singleton):', endpoint)
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async postSecure<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    console.log('🔐 POST Secure Request (Supabase singleton):', endpoint, 'avec data:', data)
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async putSecure<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    console.log('🔐 PUT Secure Request (Supabase singleton):', endpoint, 'avec data:', data)
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async patchSecure<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    console.log('🔐 PATCH Secure Request (Supabase singleton):', endpoint, 'avec data:', data)
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async deleteSecure<T>(endpoint: string): Promise<ApiResponse<T>> {
    console.log('🔐 DELETE Secure Request (Supabase singleton):', endpoint)
    return this.request<T>(endpoint, { method: 'DELETE' })
  }

  // Méthodes utilitaires
  getBaseURL(): string {
    return this.baseURL
  }

  async healthCheck(): Promise<ApiResponse<any>> {
    console.log('🏥 Health Check Request')
    return this.request<any>('health', { method: 'GET' })
  }

  async uploadFile<T>(endpoint: string, file: File, additionalData?: Record<string, any>): Promise<ApiResponse<T>> {
    console.log('📤 Upload File Request:', endpoint, 'file:', file.name)
    
    const formData = new FormData()
    formData.append('file', file)
    
    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value)
      })
    }

    // Pour les uploads, on ne met pas le Content-Type pour laisser le browser gérer les boundaries
    const headers: HeadersInit = {}
    
    // Récupérer le token Supabase pour l'auth
    const token = await this.getSupabaseToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const fullUrl = this.buildFullUrl(endpoint)

    try {
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers,
        body: formData,
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const data = await response.json()
      return {
        success: true,
        data: data as T
      }

    } catch (error: any) {
      console.error('💥 Erreur upload file:', error)
      return {
        success: false,
        error: {
          code: 'UPLOAD_ERROR',
          message: error.message,
          details: {
            url: fullUrl,
            fileName: file.name
          }
        }
      }
    }
  }

  async downloadFile(endpoint: string): Promise<Blob | null> {
    console.log('📥 Download File Request:', endpoint)
    
    const token = await this.getSupabaseToken()
    const headers: HeadersInit = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const fullUrl = this.buildFullUrl(endpoint)

    try {
      const response = await fetch(fullUrl, {
        method: 'GET',
        headers,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      return await response.blob()

    } catch (error: any) {
      console.error('💥 Erreur download file:', error)
      return null
    }
  }
}

// Export de l'instance singleton
export const apiClient = new ApiClient()

// Export par défaut pour compatibilité
export default apiClient