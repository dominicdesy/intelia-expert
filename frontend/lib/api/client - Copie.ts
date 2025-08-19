// lib/api/client.ts - VERSION DEBUG COMPLÈTE
import { ApiResponse } from '@/types'

class ApiClient {
  private baseURL: string
  private defaultHeaders: HeadersInit

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
    console.log('🔧 API Client initialisé avec baseURL:', this.baseURL)
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const fullUrl = `${this.baseURL}${endpoint}`
    console.log('📤 Requête API:', {
      url: fullUrl,
      method: options.method || 'GET',
      headers: this.defaultHeaders,
      body: options.body
    })

    try {
      const response = await fetch(fullUrl, {
        ...options,
        headers: {
          ...this.defaultHeaders,
          ...options.headers,
        },
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

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    console.log('🔍 GET Request:', endpoint)
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    console.log('📮 POST Request:', endpoint, 'avec data:', data)
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

export const apiClient = new ApiClient()