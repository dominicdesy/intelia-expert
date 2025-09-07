// lib/api/client.ts - CLIENT API CORRIGÉ (supprime le double /api)

interface APIResponse<T = any> {
  success: boolean
  data?: T
  error?: {
    message: string
    status?: number
  }
}

export class APIClient {
  private baseURL: string
  private headers: Record<string, string>

  constructor() {
    // 🔧 CORRECTION: Utiliser la variable d'environnement DigitalOcean sans ajouter /api
    this.baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app'
    
    this.headers = {
      'Content-Type': 'application/json',
      'Origin': 'https://expert.intelia.com',
    }
    
    console.log('🔧 [APIClient] Initialisé avec baseURL:', this.baseURL)
  }

  // 🔧 CORRECTION CRITIQUE: Construction URL propre
  private buildURL(endpoint: string): string {
    // Enlever leading slash si présent
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
    
    // 🔧 IMPORTANT: Enlever /api s'il est déjà présent dans baseURL
    const cleanBaseUrl = this.baseURL.replace(/\/api\/?$/, '')
    
    // Construire l'URL avec /api/v1 une seule fois
    const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
    const fullUrl = `${cleanBaseUrl}/api/${version}/${cleanEndpoint}`
    
    console.log('🔍 [APIClient] URL construite:', fullUrl)
    return fullUrl
  }

  // Méthode de base pour les requêtes
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<APIResponse<T>> {
    const url = this.buildURL(endpoint)
    
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.headers,
        ...options.headers,
      },
      credentials: 'include',
    }

    console.log('📡 [APIClient] Requête:', options.method || 'GET', url)
    
    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        console.error(`❌ [APIClient] HTTP ${response.status}:`, response.statusText)
        return {
          success: false,
          error: {
            message: response.statusText || 'Request failed',
            status: response.status
          }
        }
      }
      
      const data = await response.json()
      console.log('✅ [APIClient] Succès:', data)
      
      return {
        success: true,
        data
      }
      
    } catch (error: any) {
      console.error('❌ [APIClient] Erreur réseau:', error)
      return {
        success: false,
        error: {
          message: error.message || 'Network error'
        }
      }
    }
  }

  // Méthodes GET
  async get<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async getSecure<T>(endpoint: string): Promise<APIResponse<T>> {
    const token = await this.getAuthToken()
    return this.request<T>(endpoint, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
  }

  // Méthodes POST
  async post<T>(endpoint: string, data?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined
    })
  }

  async postSecure<T>(endpoint: string, data?: any): Promise<APIResponse<T>> {
    const token = await this.getAuthToken()
    return this.request<T>(endpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: data ? JSON.stringify(data) : undefined
    })
  }

  // Méthodes PUT
  async put<T>(endpoint: string, data?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined
    })
  }

  async putSecure<T>(endpoint: string, data?: any): Promise<APIResponse<T>> {
    const token = await this.getAuthToken()
    return this.request<T>(endpoint, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: data ? JSON.stringify(data) : undefined
    })
  }

  // Méthodes DELETE
  async delete<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }

  async deleteSecure<T>(endpoint: string): Promise<APIResponse<T>> {
    const token = await this.getAuthToken()
    return this.request<T>(endpoint, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
  }

  // Récupération du token d'authentification
  private async getAuthToken(): Promise<string | null> {
    try {
      const authData = localStorage.getItem('intelia-expert-auth')
      if (!authData) {
        console.warn('⚠️ [APIClient] Aucun token d\'authentification trouvé')
        return null
      }
      
      const parsed = JSON.parse(authData)
      const token = parsed.access_token
      
      if (!token) {
        console.warn('⚠️ [APIClient] Token invalide dans localStorage')
        return null
      }
      
      return token
    } catch (error) {
      console.error('❌ [APIClient] Erreur récupération token:', error)
      return null
    }
  }
}

// 🔧 EXPORT CORRIGÉ: Instance unique exportée
export const apiClient = new APIClient()

// Export par défaut de la classe pour les cas spéciaux si nécessaire
export default APIClient