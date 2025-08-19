// app/chat/services/apiService.ts - VERSION SUPABASE NATIVE FINALE

import { conversationService } from './conversationService'
import { supabase } from '@/lib/supabase/client'

// Configuration API
const getApiConfig = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app'
  const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
  return `${baseUrl}/api/${version}`
}

const API_BASE_URL = getApiConfig()

// ✅ FONCTION AUTH SUPABASE NATIVE
const getAuthToken = async (): Promise<string | null> => {
  try {
    console.log('[apiService] Récupération token Supabase natif...')
    
    const { data: { session } } = await supabase.auth.getSession()
    const token = session?.access_token
    
    if (token && token !== 'null' && token !== 'undefined') {
      console.log('[apiService] ✅ Token Supabase natif récupéré')
      return token
    }

    console.warn('[apiService] ❌ Aucun token Supabase trouvé')
    return null
  } catch (error) {
    console.error('[apiService] ❌ Erreur récupération token Supabase:', error)
    return null
  }
}

const getAuthHeaders = async (): Promise<Record<string, string>> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Origin': 'https://expert.intelia.com',
  }

  const authToken = await getAuthToken()
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
    console.log('[apiService] 🔑 Token Supabase natif ajouté aux headers')
  } else {
    console.warn('[apiService] ⚠️ Requête sans authentification - pas de token Supabase')
  }

  return headers
}

// UUID Generation
const generateUUID = (): string => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

// Formatage heure locale
export const formatToLocalTime = (utcTimestamp: string): string => {
  try {
    const date = new Date(utcTimestamp);
    const options: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      hour12: false
    };
    return date.toLocaleString('fr-CA', options);
  } catch (error) {
    console.warn('Erreur formatage date:', error);
    return utcTimestamp;
  }
}

export const simpleLocalTime = (utcTimestamp: string): string => {
  try {
    return new Date(utcTimestamp).toLocaleString('fr-CA', {
      year: 'numeric',
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  } catch (error) {
    console.warn('Erreur formatage date simple:', error);
    return utcTimestamp;
  }
}

// Interface pour les réponses IA
interface EnhancedAIResponse {
  response?: string
  conversation_id: string
  language: string
  ai_enhancements_used?: string[]
  rag_used?: boolean
  sources?: any[]
  confidence_score?: number
  response_time?: number
  mode?: string
  note?: string
  timestamp?: string
  processing_time?: number
  
  response_versions?: {
    ultra_concise?: string
    concise?: string
    standard?: string
    detailed?: string
  }
  
  clarification_result?: {
    clarification_requested: boolean
    clarification_type: string
    missing_information: string[]
    age_detected?: string
    confidence: number
  }
  requires_clarification?: boolean
  clarification_questions?: string[]
  clarification_type?: string
  vague_entities?: string[]
  
  type?: 'answer' | 'clarification' | 'partial_answer' | 'validation_rejected'
  questions?: string[]
  source?: string
  documents_used?: number
  warning?: string
  
  general_answer?: {
    text: string
    source?: string
  }
  follow_up_questions?: Array<{
    field: string
    question: string
    options?: string[]
  }>
  
  message?: string
  validation?: {
    is_valid: boolean
    confidence: number
    suggested_topics?: string[]
    detected_keywords?: string[]
    rejected_keywords?: string[]
  }
  
  full_text?: string
}

interface APIError {
  detail: string
  timestamp: string
  path: string
  version: string
}

/**
 * FONCTION PRINCIPALE - Expert API avec Supabase natif
 */
export const generateAIResponse = async (
  question: string,
  user: any,
  language: string = 'fr',
  conversationId?: string,
  concisionLevel: 'ultra_concise' | 'concise' | 'standard' | 'detailed' = 'concise',
  isClarificationResponse = false,
  originalQuestion?: string,
  clarificationEntities?: Record<string, any>
): Promise<EnhancedAIResponse> => {
  if (!question || question.trim() === '') {
    throw new Error('Question requise')
  }

  if (!user || !user.id) {
    throw new Error('Utilisateur requis')
  }

  const finalConversationId = conversationId || generateUUID()

  console.log('🎯 [apiService] Expert API avec Supabase natif:', {
    question: question.substring(0, 50) + '...',
    session_id: finalConversationId.substring(0, 8) + '...',
    system: 'Supabase → Expert API'
  })

  try {
    const endpoint = `${API_BASE_URL}/expert/ask`
    
    // Enrichissement clarification conservé
    let finalQuestion = question.trim()
    
    if (isClarificationResponse && originalQuestion) {
      console.log('🎪 [apiService] Mode clarification - enrichissement question')
      
      const breedMatch = finalQuestion.match(/(ross\s*308|cobb\s*500|hubbard)/i)
      const sexMatch = finalQuestion.match(/(mâle|male|femelle|female|mixte|mixed)/i)
      
      const breed = breedMatch ? breedMatch[0] : ''
      const sex = sexMatch ? sexMatch[0] : ''
      
      if (breed && sex) {
        finalQuestion = `${originalQuestion} pour ${breed} ${sex}`
        console.log('✅ [apiService] Question enrichie:', finalQuestion)
      }
    }

    const requestBody = {
      session_id: finalConversationId,
      question: finalQuestion
    }

    const headers = await getAuthHeaders()

    console.log('📤 [apiService] Requête Expert API (Supabase natif):', requestBody)

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    console.log('📡 [apiService] Expert API status (Supabase):', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur Expert API (Supabase):', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expirée. Veuillez vous reconnecter.')
      }
      
      if (response.status === 403) {
        throw new Error('Accès non autorisé.')
      }
      
      let errorMessage = `Erreur API: ${response.status}`
      try {
        const errorData: APIError = JSON.parse(errorText)
        errorMessage = errorData.detail || errorMessage
      } catch (e) {
        errorMessage = errorText || errorMessage
      }
      
      throw new Error(errorMessage)
    }

    const data = await response.json()
    
    console.log('✅ [apiService] Réponse Expert API reçue (Supabase):', {
      type: data.type,
      has_answer: !!data.answer,
      answer_text_exists: !!(data.answer?.text),
      has_general_answer: !!data.general_answer,
      has_questions: !!data.questions,
      has_message: !!data.message,
      source: data.source,
      documents_used: data.documents_used
    })

    // Extraction du texte selon le type
    let responseText = ''
    if (data.type === 'answer' && data.answer?.text) {
      responseText = data.answer.text
      console.log('🎯 [apiService] Texte extrait de data.answer.text')
    } else if (data.type === 'partial_answer' && data.general_answer?.text) {
      responseText = data.general_answer.text
      console.log('🎯 [apiService] Texte extrait de data.general_answer.text')
    } else if (data.type === 'validation_rejected') {
      responseText = data.message || "Cette question ne concerne pas le domaine agricole."
      console.log('🚫 [apiService] Question rejetée par validation agricole')
    } else {
      console.warn('⚠️ [apiService] Aucun texte trouvé dans la réponse!')
    }

    // Construction des données de réponse
    const processedData: EnhancedAIResponse = {
      conversation_id: finalConversationId,
      language: language,
      timestamp: new Date().toISOString(),
      
      // Type answer
      ...(data.type === 'answer' ? {
        type: 'answer',
        response: responseText,
        full_text: responseText,
        requires_clarification: false,
        rag_used: true,
        sources: data.answer?.sources || (data.source ? [{ source: data.source }] : []),
        mode: 'perfstore_hit',
        note: data.warning || `Documents utilisés: ${data.documents_used || 0}`,
        confidence_score: data.answer?.confidence || 0.9
      } : {}),
      
      // Type partial_answer
      ...(data.type === 'partial_answer' ? {
        type: 'partial_answer',
        general_answer: data.general_answer,
        follow_up_questions: data.follow_up_questions,
        response: responseText,
        full_text: responseText,
        rag_used: true,
        sources: data.source ? [{ source: data.source }] : [],
        mode: 'rag_partial_answer',
        note: data.warning || `Documents utilisés: ${data.documents_used || 0}`,
        confidence_score: data.documents_used ? Math.min(0.9, 0.5 + (data.documents_used * 0.1)) : 0.5
      } : {}),
      
      // Type clarification
      ...(data.type === 'clarification' ? {
        type: 'clarification',
        requires_clarification: true,
        clarification_questions: data.questions || [],
        clarification_type: 'missing_info',
        vague_entities: ['breed', 'sex'],
        clarification_result: {
          clarification_requested: true,
          clarification_type: 'missing_info',
          missing_information: ['breed', 'sex'],
          confidence: 0.5
        },
        rag_used: false,
        sources: [],
        mode: 'clarification_dialoguemanager',
        note: 'Clarification requise'
      } : {}),

      // Type validation_rejected
      ...(data.type === 'validation_rejected' ? {
        type: 'validation_rejected',
        message: data.message,
        validation: data.validation,
        response: responseText,
        full_text: responseText,
        requires_clarification: false,
        rag_used: false,
        sources: [],
        mode: 'validation_rejected',
        note: 'Question rejetée par validation agricole',
        confidence_score: 0.0
      } : {})
    }

    // Génération automatique des versions de réponse
    if (processedData.response && !processedData.response_versions) {
      console.log('✅ [apiService] Génération automatique response_versions')
      
      const mainResponse = processedData.response
      
      processedData.response_versions = {
        ultra_concise: mainResponse.length > 200 ? 
          mainResponse.substring(0, 150) + '...' : mainResponse,
        concise: mainResponse.length > 400 ? 
          mainResponse.substring(0, 300) + '...' : mainResponse,
        standard: mainResponse,
        detailed: mainResponse + (processedData.sources?.length ? 
          `\n\nSources consultées: ${processedData.sources.length} documents` : '')
      }
    }

    // Stocker le session ID pour l'historique
    try {
      conversationService.storeRecentSessionId(finalConversationId)
      console.log('✅ [apiService] Session ID stocké pour historique')
    } catch (error) {
      console.warn('⚠️ [apiService] Erreur stockage session ID:', error)
    }

    console.log('🎯 [apiService] Réponse traitée (Supabase natif):', {
      type: processedData.type,
      requires_clarification: processedData.requires_clarification,
      clarification_questions_count: processedData.clarification_questions?.length || 0,
      has_response: !!processedData.response,
      response_length: processedData.response?.length || 0,
      has_general_answer: !!processedData.general_answer,
      has_versions: !!processedData.response_versions,
      validation_rejected: processedData.type === 'validation_rejected'
    })

    return processedData

  } catch (error) {
    console.error('❌ [apiService] Erreur Expert API (Supabase):', error)
    
    if (error instanceof Error) {
      throw error
    }
    
    throw new Error('Erreur de communication avec le serveur')
  }
}

/**
 * VERSION PUBLIQUE avec Supabase
 */
export const generateAIResponsePublic = async (
  question: string,
  language: string = 'fr',
  conversationId?: string,
  concisionLevel: 'ultra_concise' | 'concise' | 'standard' | 'detailed' = 'concise'
): Promise<EnhancedAIResponse> => {
  if (!question || question.trim() === '') {
    throw new Error('Question requise')
  }

  const finalConversationId = conversationId || generateUUID()

  console.log('🌍 [apiService] Expert API public (Supabase):', {
    question: question.substring(0, 50) + '...',
    session_id: finalConversationId.substring(0, 8) + '...'
  })

  try {
    const endpoint = `${API_BASE_URL}/expert/ask-public`
    
    const requestBody = {
      session_id: finalConversationId,
      question: question.trim()
    }

    const headers = {
      'Content-Type': 'application/json',
      'Origin': 'https://expert.intelia.com'
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur Expert API public (Supabase):', errorText)
      throw new Error(`Erreur API: ${response.status}`)
    }

    const data = await response.json()
    
    console.log('✅ [apiService] Réponse Expert API public (Supabase):', {
      type: data.type,
      has_answer: !!data.answer,
      answer_text_exists: !!(data.answer?.text),
      has_general_answer: !!data.general_answer,
      has_questions: !!data.questions,
      has_message: !!data.message
    })

    // Même extraction que la version auth
    let responseText = ''
    if (data.type === 'answer' && data.answer?.text) {
      responseText = data.answer.text
    } else if (data.type === 'partial_answer' && data.general_answer?.text) {
      responseText = data.general_answer.text
    } else if (data.type === 'validation_rejected') {
      responseText = data.message || "Cette question ne concerne pas le domaine agricole."
    }

    const processedData: EnhancedAIResponse = {
      conversation_id: finalConversationId,
      language: language,
      timestamp: new Date().toISOString(),
      
      ...(data.type === 'answer' ? {
        type: 'answer',
        response: responseText,
        full_text: responseText,
        requires_clarification: false,
        rag_used: true,
        sources: data.answer?.sources || (data.source ? [{ source: data.source }] : []),
        mode: 'perfstore_hit_public',
        note: data.warning || `Documents utilisés: ${data.documents_used || 0}`,
        confidence_score: data.answer?.confidence || 0.9
      } : {}),
      
      ...(data.type === 'partial_answer' ? {
        type: 'partial_answer',
        general_answer: data.general_answer,
        follow_up_questions: data.follow_up_questions,
        response: responseText,
        full_text: responseText,
        rag_used: true,
        sources: data.source ? [{ source: data.source }] : [],
        mode: 'rag_partial_answer_public',
        note: data.warning || `Documents utilisés: ${data.documents_used || 0}`,
        confidence_score: data.documents_used ? Math.min(0.9, 0.5 + (data.documents_used * 0.1)) : 0.5
      } : {}),
      
      ...(data.type === 'clarification' ? {
        type: 'clarification',
        requires_clarification: true,
        clarification_questions: data.questions || [],
        clarification_type: 'missing_info',
        vague_entities: ['breed', 'sex'],
        clarification_result: {
          clarification_requested: true,
          clarification_type: 'missing_info',
          missing_information: ['breed', 'sex'],
          confidence: 0.5
        },
        rag_used: false,
        sources: [],
        mode: 'clarification_dialoguemanager_public',
        note: 'Clarification requise'
      } : {}),

      ...(data.type === 'validation_rejected' ? {
        type: 'validation_rejected',
        message: data.message,
        validation: data.validation,
        response: responseText,
        full_text: responseText,
        requires_clarification: false,
        rag_used: false,
        sources: [],
        mode: 'validation_rejected_public',
        note: 'Question rejetée par validation agricole',
        confidence_score: 0.0
      } : {})
    }

    // Génération response_versions
    if (processedData.response && !processedData.response_versions) {
      const mainResponse = processedData.response
      
      processedData.response_versions = {
        ultra_concise: mainResponse.length > 200 ? 
          mainResponse.substring(0, 150) + '...' : mainResponse,
        concise: mainResponse.length > 400 ? 
          mainResponse.substring(0, 300) + '...' : mainResponse,
        standard: mainResponse,
        detailed: mainResponse
      }
    }

    // Stocker le session ID
    try {
      conversationService.storeRecentSessionId(finalConversationId)
      console.log('✅ [apiService] Session ID stocké pour historique (public)')
    } catch (error) {
      console.warn('⚠️ [apiService] Erreur stockage session ID (public):', error)
    }

    return processedData

  } catch (error) {
    console.error('❌ [apiService] Erreur Expert API public (Supabase):', error)
    throw error
  }
}

// Toutes les autres fonctions utilitaires restent identiques...
export const sendFeedback = async (
  conversationId: string,
  feedback: 1 | -1,
  comment?: string
): Promise<void> => {
  if (!conversationId) {
    throw new Error('ID de conversation requis')
  }

  console.log('👍👎 [apiService] Envoi feedback (Supabase):', feedback)

  try {
    const requestBody = {
      conversation_id: conversationId,
      rating: feedback === 1 ? 'positive' : 'negative',
      ...(comment && { comment: comment.trim() })
    }

    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/expert/feedback`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur feedback (Supabase):', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expirée. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur envoi feedback: ${response.status}`)
    }

    console.log('✅ [apiService] Feedback envoyé avec succès (Supabase)')

  } catch (error) {
    console.error('❌ [apiService] Erreur feedback (Supabase):', error)
    throw error
  }
}

// Export des autres fonctions...
export const deleteConversation = async (conversationId: string): Promise<void> => {
  if (!conversationId) {
    throw new Error('ID de conversation requis')
  }

  console.log('🗑️ [apiService] Suppression conversation (Supabase):', conversationId)

  try {
    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}`, {
      method: 'DELETE',
      headers
    })

    console.log('📡 [apiService] Delete statut (Supabase):', response.status)

    if (!response.ok) {
      if (response.status === 404) {
        console.warn('⚠️ [apiService] Conversation déjà supprimée ou inexistante')
        return
      }
      
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur delete conversation (Supabase):', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expirée. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur suppression conversation: ${response.status}`)
    }

    const result = await response.json()
    console.log('✅ [apiService] Conversation supprimée (Supabase):', result.message || 'Succès')

  } catch (error) {
    console.error('❌ [apiService] Erreur suppression conversation (Supabase):', error)
    throw error
  }
}

// Utilitaires clarification inchangés
export const buildClarificationEntities = (
  clarificationAnswers: Record<string, string>,
  clarificationQuestions: string[]
): Record<string, any> => {
  const entities: Record<string, any> = {}
  
  Object.entries(clarificationAnswers).forEach(([index, answer]) => {
    if (answer && answer.trim()) {
      try {
        const questionIndex = parseInt(index)
        if (questionIndex >= 0 && questionIndex < clarificationQuestions.length) {
          const question = clarificationQuestions[questionIndex].toLowerCase()
          
          if (question.includes('race') || question.includes('breed') || question.includes('souche')) {
            entities.breed = answer.trim()
          } else if (question.includes('sexe') || question.includes('sex') || question.includes('mâle') || question.includes('femelle')) {
            entities.sex = answer.trim()
          } else if (question.includes('âge') || question.includes('age') || question.includes('jour') || question.includes('semaine')) {
            entities.age = answer.trim()
          } else if (question.includes('poids') || question.includes('weight')) {
            entities.weight = answer.trim()
          } else if (question.includes('température') || question.includes('temperature')) {
            entities.temperature = answer.trim()
          } else if (question.includes('nombre') || question.includes('quantité') || question.includes('effectif')) {
            entities.quantity = answer.trim()
          } else {
            entities[`answer_${questionIndex}`] = answer.trim()
          }
        }
      } catch {
        // Ignorer les index invalides
      }
    }
  })
  
  console.log('🔍 [apiService] Entités construites:', entities)
  return entities
}

export const handleEnhancedNetworkError = (error: any): string => {
  if (error?.message?.includes('Failed to fetch')) {
    return 'Problème de connexion. Vérifiez votre connexion internet.'
  }
  
  if (error?.message?.includes('Session expirée')) {
    return 'Votre session a expiré. Veuillez vous reconnecter.'
  }
  
  if (error?.message?.includes('Accès non autorisé')) {
    return 'Vous n\'avez pas l\'autorisation d\'effectuer cette action.'
  }
  
  return error?.message || 'Une erreur inattendue s\'est produite.'
}

// Export par défaut
export default generateAIResponse