// lib/api/client.ts - Client API unifié pour l'architecture backend-only

interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: {
    message: string
    status?: number
  }
}

class ApiClient {
  private baseURL: string

  constructor() {
    // Utilise la variable d'environnement correcte
    this.baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app'
    console.log('[ApiClient] Initialisé avec baseURL:', this.baseURL)
  }

  private async getAuthToken(): Promise<string | null> {
    try {
      const authData = localStorage.getItem('intelia-expert-auth')
      if (!authData) return null
      
      const parsed = JSON.parse(authData)
      return parsed.access_token || null
    } catch (error) {
      console.error('[ApiClient] Erreur récupération token:', error)
      return null
    }
  }

  private buildURL(endpoint: string): string {
    // Nettoyer l'endpoint
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
    
    // Construire l'URL complète
    const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
    return `${this.baseURL}/api/${version}/${cleanEndpoint}`
  }

  async request<T = any>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = this.buildURL(endpoint)
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      })

      const data = await response.json()

      if (!response.ok) {
        return {
          success: false,
          error: {
            message: data.message || data.detail || `HTTP ${response.status}`,
            status: response.status
          }
        }
      }

      return {
        success: true,
        data
      }
    } catch (error) {
      console.error('[ApiClient] Erreur requête:', error)
      return {
        success: false,
        error: {
          message: error instanceof Error ? error.message : 'Erreur réseau'
        }
      }
    }
  }

  async requestSecure<T = any>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const token = await this.getAuthToken()
    
    if (!token) {
      return {
        success: false,
        error: {
          message: 'Token d\'authentification manquant',
          status: 401
        }
      }
    }

    return this.request<T>(endpoint, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
      },
    })
  }

  // Méthodes HTTP
  async get<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }

  // Méthodes sécurisées (avec authentification)
  async getSecure<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.requestSecure<T>(endpoint, { method: 'GET' })
  }

  async postSecure<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.requestSecure<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async putSecure<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.requestSecure<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async deleteSecure<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.requestSecure<T>(endpoint, { method: 'DELETE' })
  }
}

// ✅ EXPORT CRUCIAL - C'est ce qui manquait !
export const apiClient = new ApiClient()

// Export par défaut pour compatibilité
export default apiClient