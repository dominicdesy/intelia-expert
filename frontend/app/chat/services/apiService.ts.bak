import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { ExpertApiResponse, AuthError, TimeoutError, API_CONFIG } from '../types'
import { conversationService } from './conversationService'

const supabase = createClientComponentClient()

// ==================== FONCTIONS UTILITAIRES POUR L'API ====================

// Récupération session avec gestion d'erreur propre
async function getValidSession() {
  try {
    const { data, error } = await supabase.auth.getSession()
    if (error) throw error
    return data.session
  } catch (sessionError) {
    console.error('❌ Erreur session:', sessionError)
    throw new AuthError('Impossible de récupérer la session utilisateur')
  }
}

// Fetch avec timeout
async function fetchWithTimeout(url: string, options: RequestInit, timeout: number) {
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
      throw new TimeoutError('Timeout - le serveur met trop de temps à répondre')
    }
    throw error
  }
}

// Sauvegarde conversation sécurisée
async function saveConversationSafely(user: any, question: string, response: ExpertApiResponse) {
  if (!user?.id || !response.conversation_id) {
    console.warn('⚠️ Pas de user.id ou conversation_id - historique non sauvegardé')
    return
  }
  
  try {
    console.log('💾 Sauvegarde conversation pour historique...')
    await conversationService.saveConversation({
      user_id: user.id,
      question: question,
      response: response.response,
      conversation_id: response.conversation_id,
      confidence_score: response.rag_score,
      response_time_ms: response.response_time_ms,
      language: response.language,
      rag_used: response.rag_used
    })
    console.log('✅ Conversation sauvegardée:', response.conversation_id)
  } catch (saveError) {
    console.warn('⚠️ Erreur sauvegarde (non bloquante):', saveError)
    // Continue sans bloquer l'UX
  }
}

// ==================== FONCTION generateAIResponse ====================
export const generateAIResponse = async (question: string, user: any): Promise<ExpertApiResponse> => {
  const apiUrl = `${API_CONFIG.BASE_URL}/api/v1/expert/ask`
  
  console.log('🔒 Envoi question au RAG Intelia (endpoint sécurisé):', question.substring(0, 50) + '...')
  
  try {
    // ===== 1. RÉCUPÉRATION SESSION SÉCURISÉE =====
    const session = await getValidSession()
    if (!session?.access_token) {
      throw new AuthError('Session expirée - reconnexion nécessaire')
    }
    
    console.log('✅ Token récupéré, longueur:', session.access_token.length)
    
    // ===== 2. PRÉPARATION REQUÊTE AVEC FORMAT CORRIGÉ =====
    const cleanQuestion = question.trim().normalize('NFC')
    
    // ✅ CORRECTION CRITIQUE: Supprimer request_data wrapper
    const requestBody = {
      text: cleanQuestion,                    // ✅ Direct, pas dans request_data
      language: user?.language || 'fr',       // ✅ Direct, pas dans request_data  
      speed_mode: 'balanced'                  // ✅ Direct, pas dans request_data
    }
    
    // ✅ Headers avec charset UTF-8 explicite
    const headers = {
      'Content-Type': 'application/json; charset=utf-8',
      'Accept': 'application/json',
      'Authorization': `Bearer ${session.access_token}`
    }
    
    console.log('📤 Données envoyées (format corrigé SANS request_data):', JSON.stringify(requestBody, null, 2))
    console.log('📡 URL complète:', apiUrl)
    
    // ===== 3. REQUÊTE AVEC TIMEOUT =====
    const response = await fetchWithTimeout(apiUrl, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(requestBody)
    }, API_CONFIG.TIMEOUT)
    
    console.log('📊 Réponse:', response.status, response.statusText)
    
    // ===== 4. GESTION ERREURS HTTP =====
    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ Erreur HTTP détaillée:', {
        status: response.status,
        statusText: response.statusText,
        body: errorText,
        requestSent: requestBody
      })
      
      throw new Error(`Erreur serveur (${response.status}): ${errorText}`)
    }
    
    // ===== 5. TRAITEMENT RÉPONSE =====
    const data = await response.json()
    console.log('✅ Réponse RAG reçue avec succès:', data)
    
    const adaptedResponse = {
      question: data.question || cleanQuestion,
      response: data.response || "Réponse reçue mais vide",
      conversation_id: data.conversation_id || `conv_${Date.now()}`,
      rag_used: data.rag_used || false,
      rag_score: data.rag_score,
      timestamp: data.timestamp || new Date().toISOString(),
      language: data.language || 'fr',
      response_time_ms: data.response_time_ms || 0,
      mode: data.mode || 'secured',
      user: data.user
    }

    // ===== 6. SAUVEGARDE CONVERSATION =====
    await saveConversationSafely(user, cleanQuestion, adaptedResponse)
    
    return adaptedResponse
    
  } catch (error: any) {
    console.error('❌ Erreur dans generateAIResponse:', error.message)
    
    if (error.message?.includes('Failed to fetch')) {
      throw new Error('Problème de connexion réseau. Vérifiez votre connexion internet.')
    }
    
    throw new Error(`Erreur technique: ${error.message}`)
  }
}