// services/apiService.ts - VERSION AVEC SUPPORT LANGUE

import { User } from '../types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface AIResponse {
  question: string
  response: string
  conversation_id: string
  rag_used: boolean
  rag_score?: number
  timestamp: string
  language: string
  response_time_ms: number
  mode: string
  user?: string
  logged: boolean
}

// ✅ AJOUT DU PARAMÈTRE LANGUAGE AVEC VALEUR PAR DÉFAUT
export async function generateAIResponse(
  question: string, 
  user?: User | null,
  language: string = 'fr' // ✅ NOUVEAU PARAMÈTRE AVEC DÉFAUT
): Promise<AIResponse> {
  try {
    console.log('🔒 [apiService] Envoi question avec authentification')
    console.log('🌐 [apiService] Langue transmise:', language) // ✅ LOG DE DEBUG
    
    // Vérifier l'authentification
    const token = localStorage.getItem('supabase.auth.token')
    
    if (!token) {
      throw new Error('Token d\'authentification manquant')
    }

    let parsedToken
    try {
      parsedToken = JSON.parse(token)
    } catch (e) {
      throw new Error('Token d\'authentification invalide')
    }

    const accessToken = parsedToken?.access_token
    if (!accessToken) {
      throw new Error('Access token manquant')
    }

    console.log('🔑 [apiService] Token trouvé:', accessToken.substring(0, 20) + '...')

    // ✅ REQUÊTE AVEC LANGUAGE INCLUS DANS LE BODY
    const response = await fetch(`${API_BASE_URL}/api/v1/expert/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`, // Format Bearer correct
      },
      body: JSON.stringify({
        text: question,
        language: language, // ✅ TRANSMISSION DE LA LANGUE
        speed_mode: 'balanced'
      }),
    })

    console.log('📡 [apiService] Statut réponse:', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur API:', response.status, errorText)
      
      if (response.status === 401) {
        // Rediriger vers login si non authentifié
        localStorage.removeItem('supabase.auth.token')
        window.location.href = '/login'
        throw new Error('Session expirée. Redirection vers la connexion...')
      }
      
      throw new Error(`Erreur API (${response.status}): ${errorText}`)
    }

    const data: AIResponse = await response.json()
    
    console.log('✅ [apiService] Réponse reçue:', {
      question: data.question?.substring(0, 50) + '...',
      response: data.response?.substring(0, 100) + '...',
      conversation_id: data.conversation_id,
      language: data.language, // ✅ LOG DE LA LANGUE RETOURNÉE
      rag_used: data.rag_used,
      logged: data.logged
    })

    return data

  } catch (error) {
    console.error('❌ [apiService] Erreur génération réponse:', error)
    
    if (error instanceof Error) {
      throw error
    }
    
    throw new Error('Erreur de connexion au service IA')
  }
}

// ✅ FONCTION PUBLIQUE AUSSI MISE À JOUR (si elle existe)
export async function generateAIResponsePublic(
  question: string,
  language: string = 'fr' // ✅ SUPPORT LANGUE AUSSI
): Promise<AIResponse> {
  try {
    console.log('🌐 [apiService] Envoi question publique avec langue:', language)
    
    const response = await fetch(`${API_BASE_URL}/api/v1/expert/ask-public`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: question,
        language: language, // ✅ TRANSMISSION DE LA LANGUE
        speed_mode: 'balanced'
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur API publique:', response.status, errorText)
      throw new Error(`Erreur API publique (${response.status}): ${errorText}`)
    }

    const data: AIResponse = await response.json()
    
    console.log('✅ [apiService] Réponse publique reçue avec langue:', data.language)

    return data

  } catch (error) {
    console.error('❌ [apiService] Erreur génération réponse publique:', error)
    
    if (error instanceof Error) {
      throw error
    }
    
    throw new Error('Erreur de connexion au service IA')
  }
}