// services/apiService.ts - VERSION CORRIGÉE AVEC SUPABASE AUTH HELPERS + LANGUE

import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { User } from '../types'

const supabase = createClientComponentClient()
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

// ✅ FONCTION HELPER POUR RÉCUPÉRER SESSION SUPABASE
async function getValidSession() {
  try {
    const { data, error } = await supabase.auth.getSession()
    if (error) {
      console.error('❌ [apiService] Erreur session Supabase:', error)
      throw error
    }
    return data.session
  } catch (sessionError) {
    console.error('❌ [apiService] Impossible de récupérer la session:', sessionError)
    throw new Error('Session expirée - reconnexion nécessaire')
  }
}

// ✅ FONCTION FETCH AVEC TIMEOUT
async function fetchWithTimeout(url: string, options: RequestInit, timeout: number = 30000) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    })
    clearTimeout(timeoutId)
    return response
  } catch (error) {
    clearTimeout(timeoutId)
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Timeout - le serveur met trop de temps à répondre')
    }
    throw error
  }
}

// ✅ FONCTION PRINCIPALE AVEC LANGUE + AUTH SUPABASE
export async function generateAIResponse(
  question: string, 
  user?: User | null,
  language: string = 'fr'
): Promise<AIResponse> {
  try {
    console.log('🔒 [apiService] Envoi question avec authentification Supabase')
    console.log('🌐 [apiService] Langue transmise:', language)
    
    // ✅ RÉCUPÉRATION SESSION SUPABASE (MÉTHODE CORRECTE)
    const session = await getValidSession()
    if (!session?.access_token) {
      throw new Error('Session expirée - reconnexion nécessaire')
    }

    console.log('✅ [apiService] Token Supabase récupéré, longueur:', session.access_token.length)

    // ✅ PRÉPARATION REQUÊTE AVEC LANGUE
    const cleanQuestion = question.trim().normalize('NFC')
    
    const requestBody = {
      text: cleanQuestion,
      language: language, // ✅ PARAMÈTRE LANGUE AJOUTÉ
      speed_mode: 'balanced'
    }

    // ✅ HEADERS AVEC TOKEN SUPABASE
    const headers = {
      'Content-Type': 'application/json; charset=utf-8',
      'Accept': 'application/json',
      'Authorization': `Bearer ${session.access_token}` // ✅ TOKEN SUPABASE AUTOMATIQUE
    }

    console.log('📤 [apiService] Données envoyées:', JSON.stringify(requestBody, null, 2))

    // ✅ REQUÊTE AVEC TIMEOUT
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/expert/ask`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(requestBody)
    })

    console.log('📡 [apiService] Statut réponse:', response.status)

    // ✅ GESTION ERREURS HTTP
    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur API:', response.status, errorText)
      
      if (response.status === 401) {
        // Session expirée, forcer refresh
        await supabase.auth.signOut()
        window.location.href = '/'
        throw new Error('Session expirée. Redirection vers la connexion...')
      }
      
      throw new Error(`Erreur API (${response.status}): ${errorText}`)
    }

    // ✅ TRAITEMENT RÉPONSE
    const data: AIResponse = await response.json()
    
    console.log('✅ [apiService] Réponse reçue:', {
      question: data.question?.substring(0, 50) + '...',
      response: data.response?.substring(0, 100) + '...',
      conversation_id: data.conversation_id,
      language: data.language, // ✅ LANGUE RETOURNÉE
      rag_used: data.rag_used,
      logged: data.logged
    })

    return data

  } catch (error) {
    console.error('❌ [apiService] Erreur génération réponse:', error)
    
    if (error instanceof Error) {
      // Gestion erreurs spécifiques
      if (error.message.includes('Failed to fetch')) {
        throw new Error('Problème de connexion réseau. Vérifiez votre connexion internet.')
      }
      throw error
    }
    
    throw new Error('Erreur de connexion au service IA')
  }
}

// ✅ FONCTION PUBLIQUE AVEC LANGUE (si nécessaire)
export async function generateAIResponsePublic(
  question: string,
  language: string = 'fr'
): Promise<AIResponse> {
  try {
    console.log('🌐 [apiService] Envoi question publique avec langue:', language)
    
    const requestBody = {
      text: question.trim().normalize('NFC'),
      language: language,
      speed_mode: 'balanced'
    }

    const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/expert/ask-public`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json'
      },
      body: JSON.stringify(requestBody)
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