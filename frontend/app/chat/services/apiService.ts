// app/chat/services/apiService.ts - VERSION SUPABASE NATIVE COMPLETE

import { conversationService } from './conversationService'
// ✅ CHANGEMENT CRITIQUE: Utiliser le singleton au lieu d'importer directement
import { getSupabaseClient } from '@/lib/supabase/singleton'

// Configuration API propre
const getApiConfig = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app'
  const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
  
  // Enlever /api s'il est deja present pour eviter /api/api/
  const cleanBaseUrl = baseUrl.replace(/\/api\/?$/, '')
  const finalUrl = `${cleanBaseUrl}/api/${version}`
  
  return finalUrl
}

const API_BASE_URL = getApiConfig()

// ✅ Fonction auth Supabase native MISE À JOUR avec singleton
const getAuthToken = async (): Promise<string | null> => {
  try {
    console.log('[apiService] Recuperation token Supabase natif (singleton)...')
    
    // 🎯 CHANGEMENT: Utiliser getSupabaseClient() au lieu de supabase direct
    const supabase = getSupabaseClient()
    const { data: { session } } = await supabase.auth.getSession()
    const token = session?.access_token
    
    if (token && token !== 'null' && token !== 'undefined') {
      console.log('[apiService] Token Supabase natif recupere (singleton)')
      return token
    }

    console.warn('[apiService] Aucun token Supabase trouve (singleton)')
    return null
  } catch (error) {
    console.error('[apiService] Erreur recuperation token Supabase (singleton):', error)
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
    console.log('[apiService] Token Supabase natif ajoute aux headers (singleton)')
  } else {
    console.warn('[apiService] Requete sans authentification - pas de token Supabase (singleton)')
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

// Interface pour les reponses IA
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
 * FONCTION PRINCIPALE - Expert API avec Supabase natif (singleton)
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

  console.log('[apiService] Expert API avec Supabase natif (singleton):', {
    question: question.substring(0, 50) + '...',
    session_id: finalConversationId.substring(0, 8) + '...',
    system: 'Supabase singleton -> Expert API'
  })

  try {
    const endpoint = `${API_BASE_URL}/expert/ask`
    
    // Enrichissement clarification conserve
    let finalQuestion = question.trim()
    
    if (isClarificationResponse && originalQuestion) {
      console.log('[apiService] Mode clarification - enrichissement question')
      
      const breedMatch = finalQuestion.match(/(ross\s*308|cobb\s*500|hubbard)/i)
      const sexMatch = finalQuestion.match(/(male|male|femelle|female|mixte|mixed)/i)
      
      const breed = breedMatch ? breedMatch[0] : ''
      const sex = sexMatch ? sexMatch[0] : ''
      
      if (breed && sex) {
        finalQuestion = `${originalQuestion} pour ${breed} ${sex}`
        console.log('[apiService] Question enrichie:', finalQuestion)
      }
    }

    const requestBody = {
      session_id: finalConversationId,
      question: finalQuestion
    }

    const headers = await getAuthHeaders()

    console.log('[apiService] Requete Expert API (Supabase singleton):', requestBody)

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    console.log('[apiService] Expert API status (Supabase singleton):', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[apiService] Erreur Expert API (Supabase singleton):', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expiree. Veuillez vous reconnecter.')
      }
      
      if (response.status === 403) {
        throw new Error('Acces non autorise.')
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
    
    console.log('[apiService] Reponse Expert API recue (Supabase singleton):', {
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
      console.log('[apiService] Texte extrait de data.answer.text')
    } else if (data.type === 'partial_answer' && data.general_answer?.text) {
      responseText = data.general_answer.text
      console.log('[apiService] Texte extrait de data.general_answer.text')
    } else if (data.type === 'validation_rejected') {
      responseText = data.message || "Cette question ne concerne pas le domaine agricole."
      console.log('[apiService] Question rejetee par validation agricole')
    } else {
      console.warn('[apiService] Aucun texte trouve dans la reponse!')
    }

    // Construction des donnees de reponse
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
        note: data.warning || `Documents utilises: ${data.documents_used || 0}`,
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
        note: data.warning || `Documents utilises: ${data.documents_used || 0}`,
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
        note: 'Question rejetee par validation agricole',
        confidence_score: 0.0
      } : {})
    }

    // Generation automatique des versions de reponse
    if (processedData.response && !processedData.response_versions) {
      console.log('[apiService] Generation automatique response_versions')
      
      const mainResponse = processedData.response
      
      processedData.response_versions = {
        ultra_concise: mainResponse.length > 200 ? 
          mainResponse.substring(0, 150) + '...' : mainResponse,
        concise: mainResponse.length > 400 ? 
          mainResponse.substring(0, 300) + '...' : mainResponse,
        standard: mainResponse,
        detailed: mainResponse + (processedData.sources?.length ? 
          `\n\nSources consultees: ${processedData.sources.length} documents` : '')
      }
    }

    // Stocker le session ID pour l'historique
    try {
      conversationService.storeRecentSessionId(finalConversationId)
      console.log('[apiService] Session ID stocke pour historique (singleton)')
    } catch (error) {
      console.warn('[apiService] Erreur stockage session ID (singleton):', error)
    }

    console.log('[apiService] Reponse traitee (Supabase singleton):', {
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
    console.error('[apiService] Erreur Expert API (Supabase singleton):', error)
    
    if (error instanceof Error) {
      throw error
    }
    
    throw new Error('Erreur de communication avec le serveur')
  }
}

/**
 * VERSION PUBLIQUE avec Supabase (singleton)
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

  console.log('[apiService] Expert API public (Supabase singleton):', {
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
      console.error('[apiService] Erreur Expert API public (Supabase singleton):', errorText)
      throw new Error(`Erreur API: ${response.status}`)
    }

    const data = await response.json()
    
    console.log('[apiService] Reponse Expert API public (Supabase singleton):', {
      type: data.type,
      has_answer: !!data.answer,
      answer_text_exists: !!(data.answer?.text),
      has_general_answer: !!data.general_answer,
      has_questions: !!data.questions,
      has_message: !!data.message
    })

    // Meme extraction que la version auth
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
        note: data.warning || `Documents utilises: ${data.documents_used || 0}`,
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
        note: data.warning || `Documents utilises: ${data.documents_used || 0}`,
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
        note: 'Question rejetee par validation agricole',
        confidence_score: 0.0
      } : {})
    }

    // Generation response_versions
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
      console.log('[apiService] Session ID stocke pour historique (public singleton)')
    } catch (error) {
      console.warn('[apiService] Erreur stockage session ID (public singleton):', error)
    }

    return processedData

  } catch (error) {
    console.error('[apiService] Erreur Expert API public (Supabase singleton):', error)
    throw error
  }
}

/**
 * Chargement des conversations utilisateur (singleton)
 */
export const loadUserConversations = async (userId: string): Promise<any> => {
  if (!userId) {
    throw new Error('User ID requis')
  }

  console.log('[apiService] Chargement conversations pour (singleton):', userId)

  try {
    const headers = await getAuthHeaders()
    const url = `${API_BASE_URL}/conversations/user/${userId}`

    const response = await fetch(url, {
      method: 'GET',
      headers
    })

    console.log('[apiService] Conversations statut (singleton):', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[apiService] Erreur conversations (singleton):', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expiree. Veuillez vous reconnecter.')
      }
      
      if (response.status === 405 || response.status === 404) {
        // Si l'endpoint n'existe pas encore, retourner des donnees vides
        console.warn('[apiService] Endpoint conversations non disponible - retour donnees vides (singleton)')
        return {
          count: 0,
          conversations: [],
          user_id: userId,
          note: "Fonctionnalite en cours de developpement"
        }
      }
      
      throw new Error(`Erreur chargement conversations: ${response.status}`)
    }

    const data = await response.json()
    console.log('[apiService] Conversations chargees (singleton):', {
      count: data.count,
      conversations: data.conversations?.length || 0
    })

    return data

  } catch (error) {
    console.error('[apiService] Erreur chargement conversations (singleton):', error)
    
    // En cas d'erreur reseau, retourner des donnees vides plutot que de faire planter l'app
    if (error instanceof Error && error.message.includes('Failed to fetch')) {
      console.warn('[apiService] Erreur reseau - retour donnees vides (singleton)')
      return {
        count: 0,
        conversations: [],
        user_id: userId,
        note: "Erreur de connexion - reessayez plus tard"
      }
    }
    
    throw error
  }
}

/**
 * ENVOI DE FEEDBACK (singleton)
 */
export const sendFeedback = async (
  conversationId: string,
  feedback: 1 | -1,
  comment?: string
): Promise<void> => {
  if (!conversationId) {
    throw new Error('ID de conversation requis')
  }

  console.log('[apiService] Envoi feedback (Supabase singleton):', feedback)

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
      console.error('[apiService] Erreur feedback (Supabase singleton):', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expiree. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur envoi feedback: ${response.status}`)
    }

    console.log('[apiService] Feedback envoye avec succes (Supabase singleton)')

  } catch (error) {
    console.error('[apiService] Erreur feedback (Supabase singleton):', error)
    throw error
  }
}

/**
 * SUPPRESSION DE CONVERSATION (singleton)
 */
export const deleteConversation = async (conversationId: string): Promise<void> => {
  if (!conversationId) {
    throw new Error('ID de conversation requis')
  }

  console.log('[apiService] Suppression conversation (Supabase singleton):', conversationId)

  try {
    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}`, {
      method: 'DELETE',
      headers
    })

    console.log('[apiService] Delete statut (Supabase singleton):', response.status)

    if (!response.ok) {
      if (response.status === 404) {
        console.warn('[apiService] Conversation deja supprimee ou inexistante (singleton)')
        return
      }
      
      const errorText = await response.text()
      console.error('[apiService] Erreur delete conversation (Supabase singleton):', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expiree. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur suppression conversation: ${response.status}`)
    }

    const result = await response.json()
    console.log('[apiService] Conversation supprimee (Supabase singleton):', result.message || 'Succes')

  } catch (error) {
    console.error('[apiService] Erreur suppression conversation (Supabase singleton):', error)
    throw error
  }
}

/**
 * SUPPRESSION DE TOUTES LES CONVERSATIONS (singleton)
 */
export const clearAllUserConversations = async (userId: string): Promise<void> => {
  if (!userId) {
    throw new Error('User ID requis')
  }

  console.log('[apiService] Suppression toutes conversations pour (Supabase singleton):', userId)

  try {
    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/conversations/user/${userId}`, {
      method: 'DELETE',
      headers
    })

    console.log('[apiService] Clear all statut (Supabase singleton):', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[apiService] Erreur clear all conversations (Supabase singleton):', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expiree. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur suppression conversations: ${response.status}`)
    }

    const result = await response.json()
    console.log('[apiService] Toutes conversations supprimees (Supabase singleton):', {
      message: result.message,
      deleted_count: result.deleted_count || 0
    })

  } catch (error) {
    console.error('[apiService] Erreur suppression toutes conversations (Supabase singleton):', error)
    throw error
  }
}

/**
 * SUGGESTIONS DE SUJETS (singleton)
 */
export const getTopicSuggestions = async (language: string = 'fr'): Promise<string[]> => {
  console.log('[apiService] Recuperation suggestions sujets (Supabase singleton):', language)

  try {
    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/expert/topics?language=${language}`, {
      method: 'GET',
      headers
    })

    if (!response.ok) {
      console.warn('[apiService] Erreur recuperation sujets (Supabase singleton):', response.status)
      
      return [
        "Problemes de croissance poulets",
        "Conditions environnementales optimales",
        "Protocoles de vaccination",
        "Diagnostic problemes de sante",
        "Nutrition et alimentation",
        "Gestion de la mortalite"
      ]
    }

    const data = await response.json()
    console.log('[apiService] Sujets recuperes (Supabase singleton):', data.topics?.length || 0)

    return Array.isArray(data.topics) ? data.topics : []

  } catch (error) {
    console.error('[apiService] Erreur sujets (Supabase singleton):', error)
    
    return [
      "Problemes de croissance poulets",
      "Conditions environnementales optimales", 
      "Protocoles de vaccination",
      "Diagnostic problemes de sante",
      "Nutrition et alimentation",
      "Gestion de la mortalite"
    ]
  }
}

/**
 * HEALTH CHECK (singleton)
 */
export const checkAPIHealth = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/system/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Origin': 'https://expert.intelia.com'
      }
    })

    const isHealthy = response.ok
    console.log('[apiService] API Health (Supabase singleton):', isHealthy ? 'OK' : 'KO')
    
    return isHealthy

  } catch (error) {
    console.error('[apiService] Erreur health check (Supabase singleton):', error)
    return false
  }
}

/**
 * UTILITAIRES CLARIFICATION
 */
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
          } else if (question.includes('sexe') || question.includes('sex') || question.includes('male') || question.includes('femelle')) {
            entities.sex = answer.trim()
          } else if (question.includes('age') || question.includes('age') || question.includes('jour') || question.includes('semaine')) {
            entities.age = answer.trim()
          } else if (question.includes('poids') || question.includes('weight')) {
            entities.weight = answer.trim()
          } else if (question.includes('temperature') || question.includes('temperature')) {
            entities.temperature = answer.trim()
          } else if (question.includes('nombre') || question.includes('quantite') || question.includes('effectif')) {
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
  
  console.log('[apiService] Entites construites (singleton):', entities)
  return entities
}

export const handleEnhancedNetworkError = (error: any): string => {
  if (error?.message?.includes('Failed to fetch')) {
    return 'Probleme de connexion. Verifiez votre connexion internet.'
  }
  
  if (error?.message?.includes('Session expiree')) {
    return 'Votre session a expire. Veuillez vous reconnecter.'
  }
  
  if (error?.message?.includes('Acces non autorise')) {
    return 'Vous n\'avez pas l\'autorisation d\'effectuer cette action.'
  }
  
  return error?.message || 'Une erreur inattendue s\'est produite.'
}

/**
 * FONCTIONS DE DEBUG ET TEST (singleton)
 */
export const debugEnhancedAPI = () => {
  console.group('[apiService] Configuration DialogueManager + expert.py + SUPABASE SINGLETON')
  console.log('API_BASE_URL:', API_BASE_URL)
  console.log('Systeme backend: DialogueManager + expert.py')
  console.log('Systeme auth: Supabase SINGLETON')
  console.log('Endpoint principal:', `${API_BASE_URL}/expert/ask`)
  console.log('CORRECTIONS EFFECTUEES:')
  console.log('  - Body avec session_id: { session_id, question }')
  console.log('  - Headers avec CORS Origin obligatoire')
  console.log('  - Supabase SINGLETON: Token dans Authorization header')
  console.log('  - Extraction correcte du texte selon type')
  console.log('  - Support type: "answer" avec data.answer.text')
  console.log('  - Support type: "partial_answer"')
  console.log('  - Support type: "clarification"')
  console.log('  - Support type: "validation_rejected"')
  console.log('  - Generation automatique response_versions')
  console.log('  - Stockage automatique session ID pour historique')
  console.log('  - DELETE conversation corrige (/conversations au pluriel)')
  console.log('  - CLEAR ALL conversations ajoute')
  console.log('  - Formatage heure locale')
  console.log('  - SUPABASE SINGLETON: Headers avec Origin + Authorization')
  console.log('  - ✅ SINGLETON: Une seule instance GoTrueClient')
  console.log('FONCTIONNALITES PRESERVEES:')
  console.log('  - Authentification JWT (Supabase SINGLETON)')
  console.log('  - Feedback, conversations, topics')
  console.log('  - Gestion erreurs')
  console.log('  - Health check')
  console.log('  - Utilitaires clarification')
  console.log('  - Integration ConversationService')
  console.groupEnd()
}

export const testEnhancedConversationContinuity = async (
  user: any,
  language: string = 'fr'
): Promise<{
  first_conversation_id: string,
  second_conversation_id: string,
  same_id: boolean,
  success: boolean,
  enhancements_used: string[]
}> => {
  try {
    console.log('[apiService] Test continuite DialogueManager (Supabase singleton)...')
    
    const firstResponse = await generateAIResponse(
      "Test question 1: Qu'est-ce que les poulets de chair ?",
      user,
      language
    )
    
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    const secondResponse = await generateAIResponse(
      "Test question 2: Quel est leur poids optimal a 12 jours ?",
      user,
      language,
      firstResponse.conversation_id
    )
    
    const sameId = firstResponse.conversation_id === secondResponse.conversation_id
    
    console.log('[apiService] Test DialogueManager resultat (Supabase singleton):', {
      first_id: firstResponse.conversation_id,
      second_id: secondResponse.conversation_id,
      same_id: sameId,
      first_type: firstResponse.type,
      second_type: secondResponse.type
    })
    
    return {
      first_conversation_id: firstResponse.conversation_id,
      second_conversation_id: secondResponse.conversation_id,
      same_id: sameId,
      success: true,
      enhancements_used: ['DialogueManager', 'expert.py', 'ConversationService', 'DeleteFix', 'HeureLocale', 'Supabase', 'SINGLETON']
    }
    
  } catch (error) {
    console.error('[apiService] Erreur test DialogueManager (Supabase singleton):', error)
    return {
      first_conversation_id: '',
      second_conversation_id: '',
      same_id: false,
      success: false,
      enhancements_used: []
    }
  }
}

export const detectAPIVersion = async (): Promise<'dialoguemanager' | 'legacy' | 'error'> => {
  try {
    const response = await fetch(`${API_BASE_URL}/expert/ask`, {
      method: 'OPTIONS',
      headers: { 
        'Content-Type': 'application/json',
        'Origin': 'https://expert.intelia.com'
      }
    })
    
    if (response.ok || response.status === 405) {
      console.log('[detectAPIVersion] DialogueManager /ask disponible (Supabase singleton)')
      return 'dialoguemanager'
    }
    
    return 'error'
    
  } catch (error) {
    console.error('[detectAPIVersion] Erreur detection (Supabase singleton):', error)
    return 'error'
  }
}

export const logEnhancedAPIInfo = () => {
  console.group('[apiService] DialogueManager + expert.py Integration + SUPABASE SINGLETON')
  console.log('Version:', 'DialogueManager v1.0 - SUPABASE SINGLETON FIXED')
  console.log('Base URL:', API_BASE_URL)
  console.log('Backend: expert.py + DialogueManager + Agricultural Validator')
  console.log('Auth System: Supabase SINGLETON')
  console.log('CHANGEMENTS MAJEURS CORRIGES:')
  console.log('  - Utilisation endpoint /ask simplifie')
  console.log('  - Session ID dans le BODY (corrige !)')
  console.log('  - Headers avec CORS Origin obligatoire')
  console.log('  - Supabase SINGLETON: Token JWT dans Authorization header')
  console.log('  - Extraction type: "answer" de data.answer.text (CORRIGE !)')
  console.log('  - Support type: "validation_rejected"')
  console.log('  - Stockage automatique session ID pour historique')
  console.log('  - DELETE conversation corrige (/conversations au pluriel)')
  console.log('  - CLEAR ALL conversations ajoute')
  console.log('  - Formatage heure locale')
  console.log('  - Body: { session_id, question }')
  console.log('  - Support type: clarification/answer/partial_answer/validation_rejected')
  console.log('  - PRESERVATION format partial_answer')
  console.log('  - Conversion automatique format')
  console.log('  - SUPABASE SINGLETON: JWT token authentique + profil utilisateur')
  console.log('  - ✅ SINGLETON: Elimination Multiple GoTrueClient instances')
  console.log('FONCTIONNALITES:')
  console.log('  - Clarification intelligente automatique')
  console.log('  - Gestion memoire conversation Postgres')
  console.log('  - Pipeline RAG modulaire')
  console.log('  - Validation agricole integree')
  console.log('  - Toutes fonctions frontend preservees')
  console.log('  - Support PerfStore avec type: "answer"')
  console.log('  - Integration ConversationService pour historique')
  console.log('  - Sauvegarde automatique via /expert/ask')
  console.log('  - Gestion DELETE conversations')
  console.log('  - Formatage heure locale automatique')
  console.log('  - Supabase SINGLETON: Auth moderne + profils utilisateur')
  console.log('  - ✅ Une seule instance GoTrueClient dans toute l\'application')
  console.groupEnd()
}

// Export par defaut
export default generateAIResponse