// ==================== API SERVICE UNIFIÉ - ADAPTÉ NOUVEAU BACKEND DialogueManager ====================

// ✅ CONFIGURATION INCHANGÉE
const getApiConfig = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
  const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
  
  if (!baseUrl) {
    console.error('❌ NEXT_PUBLIC_API_BASE_URL environment variable is required')
    throw new Error('API configuration missing - check environment variables')
  }
  
  return `${baseUrl}/api/${version}`
}

const API_BASE_URL = getApiConfig()

// ✅ FONCTIONS AUTH INCHANGÉES
const getAuthToken = (): string | null => {
  try {
    const cookieToken = getCookieToken()
    if (cookieToken) {
      console.log('[getAuthToken] Token trouvé dans cookies')
      return cookieToken
    }

    const sbToken = localStorage.getItem('sb-cdrmjshmkdfwwtsfdvbl-auth-token')
    if (sbToken) {
      try {
        const parsed = JSON.parse(sbToken)
        if (Array.isArray(parsed) && parsed[0] && parsed[0] !== 'mock-jwt-token-for-development') {
          console.log('[getAuthToken] Token trouvé dans localStorage')
          return parsed[0]
        }
      } catch (e) {
        console.warn('[getAuthToken] Failed to parse sb localStorage token:', e)
      }
    }

    console.warn('[getAuthToken] Aucun token trouvé dans toutes les sources')
    return null
  } catch (error) {
    console.error('[getAuthToken] Error getting auth token:', error)
    return null
  }
}

const getCookieToken = (): string | null => {
  try {
    const cookies = document.cookie.split(';')
    const sbCookie = cookies.find(cookie => 
      cookie.trim().startsWith('sb-cdrmjshmkdfwwtsfdvbl-auth-token=')
    )
    
    if (sbCookie) {
      const cookieValue = sbCookie.split('=')[1]
      const decodedValue = decodeURIComponent(cookieValue)
      const parsed = JSON.parse(decodedValue)
      
      if (Array.isArray(parsed) && parsed[0] && parsed[0] !== 'mock-jwt-token-for-development') {
        console.log('[getCookieToken] Token valide trouvé dans cookie')
        return parsed[0]
      }
    }
    
    return null
  } catch (error) {
    console.error('[getCookieToken] Error parsing cookie token:', error)
    return null
  }
}

const getAuthHeaders = (): Record<string, string> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const authToken = getAuthToken()
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
    console.log('🔑 [apiService] Token ajouté aux headers')
  } else {
    console.warn('⚠️ [apiService] Aucun token trouvé - requête sans auth')
  }

  return headers
}

// ✅ GÉNÉRATION UUID INCHANGÉE
const generateUUID = (): string => {
  // Utiliser crypto.randomUUID si disponible (navigateurs modernes)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  
  // Fallback pour navigateurs plus anciens
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

// 🔧 INTERFACE ADAPTÉE : Compatible nouveau backend + garder compatibilité
interface EnhancedAIResponse {
  response: string
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
  
  // 🚀 NOUVEAU : Toutes les versions de réponse (généré côté frontend si absent)
  response_versions?: {
    ultra_concise?: string
    concise?: string
    standard?: string
    detailed?: string
  }
  
  // ✅ CLARIFICATIONS INCHANGÉES
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
  
  // 🚀 NOUVEAU : Support format DialogueManager
  type?: 'answer' | 'clarification'
  questions?: string[]
  source?: string
  documents_used?: number
  warning?: string
  
  // 🚀 AJOUT : Champ pour compatibilité
  full_text?: string
}

// ✅ INTERFACE ERROR INCHANGÉE
interface APIError {
  detail: string
  timestamp: string
  path: string
  version: string
}

/**
 * 🔧 FONCTION PRINCIPALE ADAPTÉE : Compatible DialogueManager + garde compatibilité ancienne
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

  // 🔧 ADAPTÉ : Session ID pour DialogueManager
  const finalConversationId = conversationId || generateUUID()

  console.log('🎯 [apiService] Nouveau système DialogueManager:', {
    question: question.substring(0, 50) + '...',
    session_id: finalConversationId.substring(0, 8) + '...',
    system: 'expert.py + DialogueManager'
  })

  try {
    // 🔧 ADAPTÉ : Endpoint simplifié du nouveau système
    const endpoint = `${API_BASE_URL}/expert/ask`
    
    // ✅ ENRICHISSEMENT CLARIFICATION CONSERVÉ (au cas où)
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

    // 🔧 ADAPTÉ : Body simplifié pour DialogueManager
    const requestBody = {
      question: finalQuestion
    }

    // 🔧 ADAPTÉ : Headers avec session ID pour DialogueManager
    const headers = {
      ...getAuthHeaders(),
      'X-Session-ID': finalConversationId
    }

    console.log('📤 [apiService] Body DialogueManager:', requestBody)
    console.log('📤 [apiService] Session ID:', finalConversationId.substring(0, 8) + '...')

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    console.log('📡 [apiService] Statut DialogueManager:', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur DialogueManager:', errorText)
      
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
    
    // 🔧 CORRECTION : Extraire responseText de la réponse
    let responseText = ''
    if (data.response) {
      // Si data.response est un objet avec answer
      if (typeof data.response === 'object' && data.response.answer) {
        responseText = data.response.answer
      } else if (typeof data.response === 'string') {
        responseText = data.response
      }
    } else if (data.questions && Array.isArray(data.questions)) {
      // Mode clarification
      responseText = data.questions.join('\n')
    }
    
    console.log('✅ [apiService] Réponse DialogueManager reçue:', {
      type: data.type,
      has_response: !!responseText,
      has_questions: !!data.questions,
      response_length: responseText.length,
      questions_count: data.questions?.length || 0,
      source: data.source,
      documents_used: data.documents_used
    })

    // 🔧 ADAPTÉ : Conversion format DialogueManager vers format attendu
    const processedData: EnhancedAIResponse = {
      conversation_id: finalConversationId,
      language: language,
      timestamp: new Date().toISOString(),
      type: data.type,
      
      // 🔧 CHAMPS REQUIS TOUJOURS PRÉSENTS
      response: responseText,
      full_text: responseText, // 🔧 AJOUT : Pour compatibilité
      
      // 🔧 GESTION CLARIFICATION : Format DialogueManager
      ...(data.type === 'clarification' ? {
        requires_clarification: true,
        clarification_questions: data.questions || [],
        clarification_type: 'missing_info',
        vague_entities: ['breed', 'sex'], // Default pour compatibilité
        clarification_result: {
          clarification_requested: true,
          clarification_type: 'missing_info',
          missing_information: ['breed', 'sex'],
          confidence: 0.5
        }
      } : {
        requires_clarification: false
      }),
      
      // 🔧 GESTION RÉPONSE : Format DialogueManager
      ...(data.type === 'answer' ? {
        rag_used: true,
        sources: data.source ? [{ source: data.source }] : [],
        mode: 'rag_dialoguemanager',
        note: data.warning || `Documents utilisés: ${data.documents_used || 0}`,
        confidence_score: data.documents_used ? Math.min(0.9, 0.5 + (data.documents_used * 0.1)) : 0.5
      } : {
        rag_used: false,
        sources: [],
        mode: 'clarification_dialoguemanager',
        note: 'Clarification requise'
      })
    }

    // 🚀 GÉNÉRATION AUTOMATIQUE response_versions (comme avant)
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

    console.log('🎯 [apiService] Données traitées DialogueManager:', {
      requires_clarification: processedData.requires_clarification,
      clarification_questions_count: processedData.clarification_questions?.length || 0,
      has_response: !!responseText,
      has_versions: !!processedData.response_versions,
      type: processedData.type
    })

    return processedData

  } catch (error) {
    console.error('❌ [apiService] Erreur DialogueManager:', error)
    
    if (error instanceof Error) {
      throw error
    }
    
    throw new Error('Erreur de communication avec le serveur')
  }
}

/**
 * 🔧 VERSION PUBLIQUE ADAPTÉE : Compatible DialogueManager (sans auth)
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

  console.log('🌐 [apiService] DialogueManager public:', {
    question: question.substring(0, 50) + '...',
    session_id: finalConversationId.substring(0, 8) + '...'
  })

  try {
    // 🔧 ADAPTÉ : Même endpoint que la version auth (DialogueManager gère)
    const endpoint = `${API_BASE_URL}/expert/ask`
    
    const requestBody = {
      question: question.trim()
    }

    const headers = {
      'Content-Type': 'application/json',
      'X-Session-ID': finalConversationId
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur DialogueManager public:', errorText)
      throw new Error(`Erreur API: ${response.status}`)
    }

    const data = await response.json()
    
    // 🔧 CORRECTION : Même extraction que version auth
    let responseText = ''
    if (data.response) {
      if (typeof data.response === 'object' && data.response.answer) {
        responseText = data.response.answer
      } else if (typeof data.response === 'string') {
        responseText = data.response
      }
    } else if (data.questions && Array.isArray(data.questions)) {
      responseText = data.questions.join('\n')
    }
    
    console.log('✅ [apiService] Réponse DialogueManager public:', {
      type: data.type,
      has_response: !!responseText,
      has_questions: !!data.questions
    })

    // 🔧 MÊME CONVERSION que la version auth
    const processedData: EnhancedAIResponse = {
      conversation_id: finalConversationId,
      language: language,
      timestamp: new Date().toISOString(),
      type: data.type,
      
      // 🔧 CHAMPS REQUIS TOUJOURS PRÉSENTS
      response: responseText,
      full_text: responseText,
      
      // 🔧 GESTION CLARIFICATION
      ...(data.type === 'clarification' ? {
        requires_clarification: true,
        clarification_questions: data.questions || [],
        clarification_type: 'missing_info',
        vague_entities: ['breed', 'sex'],
        clarification_result: {
          clarification_requested: true,
          clarification_type: 'missing_info',
          missing_information: ['breed', 'sex'],
          confidence: 0.5
        }
      } : {
        requires_clarification: false
      }),
      
      // 🔧 GESTION RÉPONSE
      ...(data.type === 'answer' ? {
        rag_used: true,
        sources: data.source ? [{ source: data.source }] : [],
        mode: 'rag_dialoguemanager_public',
        note: data.warning || `Documents utilisés: ${data.documents_used || 0}`,
        confidence_score: data.documents_used ? Math.min(0.9, 0.5 + (data.documents_used * 0.1)) : 0.5
      } : {
        rag_used: false,
        sources: [],
        mode: 'clarification_dialoguemanager_public',
        note: 'Clarification requise'
      })
    }

    // 🚀 GÉNÉRATION response_versions
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

    return processedData

  } catch (error) {
    console.error('❌ [apiService] Erreur DialogueManager public:', error)
    throw error
  }
}

/**
 * ✅ FONCTIONS FEEDBACK, CONVERSATIONS, TOPICS - TOUTES INCHANGÉES
 */
export const sendFeedback = async (
  conversationId: string,
  feedback: 1 | -1,
  comment?: string
): Promise<void> => {
  if (!conversationId) {
    throw new Error('ID de conversation requis')
  }

  console.log('👍👎 [apiService] Envoi feedback:', feedback, 'pour conversation:', conversationId)

  try {
    const requestBody = {
      conversation_id: conversationId,
      rating: feedback === 1 ? 'positive' : 'negative',
      ...(comment && { comment: comment.trim() })
    }

    const headers = getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/expert/feedback`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    console.log('📡 [apiService] Feedback statut:', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur feedback:', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expirée. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur envoi feedback: ${response.status}`)
    }

    console.log('✅ [apiService] Feedback envoyé avec succès')

  } catch (error) {
    console.error('❌ [apiService] Erreur feedback:', error)
    throw error
  }
}

export const loadUserConversations = async (userId: string): Promise<any> => {
  if (!userId) {
    throw new Error('User ID requis')
  }

  console.log('📂 [apiService] Chargement conversations pour:', userId)

  try {
    const headers = getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/conversations/user/${userId}`, {
      method: 'GET',
      headers
    })

    console.log('📡 [apiService] Conversations statut:', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur conversations:', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expirée. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur chargement conversations: ${response.status}`)
    }

    const data = await response.json()
    console.log('✅ [apiService] Conversations chargées:', {
      count: data.count,
      conversations: data.conversations?.length || 0
    })

    return data

  } catch (error) {
    console.error('❌ [apiService] Erreur chargement conversations:', error)
    throw error
  }
}

export const getTopicSuggestions = async (language: string = 'fr'): Promise<string[]> => {
  console.log('💡 [apiService] Récupération suggestions sujets:', language)

  try {
    const headers = getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/expert/topics?language=${language}`, {
      method: 'GET',
      headers
    })

    if (!response.ok) {
      console.warn('⚠️ [apiService] Erreur récupération sujets:', response.status)
      
      return [
        "Problèmes de croissance poulets",
        "Conditions environnementales optimales",
        "Protocoles de vaccination",
        "Diagnostic problèmes de santé",
        "Nutrition et alimentation",
        "Gestion de la mortalité"
      ]
    }

    const data = await response.json()
    console.log('✅ [apiService] Sujets récupérés:', data.topics?.length || 0)

    return Array.isArray(data.topics) ? data.topics : []

  } catch (error) {
    console.error('❌ [apiService] Erreur sujets:', error)
    
    return [
      "Problèmes de croissance poulets",
      "Conditions environnementales optimales", 
      "Protocoles de vaccination",
      "Diagnostic problèmes de santé",
      "Nutrition et alimentation",
      "Gestion de la mortalité"
    ]
  }
}

export const checkAPIHealth = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/system/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    const isHealthy = response.ok
    console.log('🏥 [apiService] API Health:', isHealthy ? 'OK' : 'KO')
    
    return isHealthy

  } catch (error) {
    console.error('❌ [apiService] Erreur health check:', error)
    return false
  }
}

/**
 * ✅ UTILITAIRES CLARIFICATION - INCHANGÉS
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

/**
 * ✅ UTILITAIRES DEBUG ET TEST - ADAPTÉS
 */
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
  
  if (error?.message?.includes('DialogueManager') || error?.message?.includes('ask')) {
    return 'Erreur du système expert. Veuillez réessayer.'
  }
  
  return error?.message || 'Une erreur inattendue s\'est produite.'
}

export const debugEnhancedConversationFlow = (
  step: string,
  conversationId: string | undefined,
  additionalInfo?: any
) => {
  console.log(`🔍 [DialogueManager Debug] ${step}:`, {
    session_id: conversationId || 'GÉNÉRÉ_AUTO',
    endpoint: 'ask (DialogueManager)',
    timestamp: new Date().toISOString(),
    ...additionalInfo
  })
}

export const debugEnhancedAPI = () => {
  console.group('🔧 [apiService] Configuration DialogueManager + expert.py')
  console.log('API_BASE_URL:', API_BASE_URL)
  console.log('Système backend: DialogueManager + expert.py')
  console.log('Endpoint principal:', `${API_BASE_URL}/expert/ask`)
  console.log('🔧 ADAPTATIONS EFFECTUÉES:')
  console.log('  ✅ Body simplifié: { question }')
  console.log('  ✅ Session ID via header X-Session-ID')
  console.log('  ✅ Conversion format DialogueManager vers format frontend')
  console.log('  ✅ Support clarification via type: "clarification"')
  console.log('  ✅ Support réponse via type: "answer"')
  console.log('  ✅ Génération automatique response_versions')
  console.log('  ✅ Toutes fonctions auxiliaires préservées')
  console.log('FONCTIONNALITÉS PRÉSERVÉES:')
  console.log('  ✅ Authentification JWT')
  console.log('  ✅ Feedback, conversations, topics')
  console.log('  ✅ Gestion erreurs')
  console.log('  ✅ Health check')
  console.log('  ✅ Utilitaires clarification')
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
    console.log('🧪 [apiService] Test continuité DialogueManager...')
    
    const firstResponse = await generateAIResponse(
      "Test question 1: Qu'est-ce que les poulets de chair ?",
      user,
      language
    )
    
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    const secondResponse = await generateAIResponse(
      "Test question 2: Quel est leur poids optimal à 12 jours ?",
      user,
      language,
      firstResponse.conversation_id
    )
    
    const sameId = firstResponse.conversation_id === secondResponse.conversation_id
    
    console.log('🧪 [apiService] Test DialogueManager résultat:', {
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
      enhancements_used: ['DialogueManager', 'expert.py']
    }
    
  } catch (error) {
    console.error('❌ [apiService] Erreur test DialogueManager:', error)
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
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (response.ok || response.status === 405) {
      console.log('✅ [detectAPIVersion] DialogueManager /ask disponible')
      return 'dialoguemanager'
    }
    
    return 'error'
    
  } catch (error) {
    console.error('❌ [detectAPIVersion] Erreur détection:', error)
    return 'error'
  }
}

export const logEnhancedAPIInfo = () => {
  console.group('🚀 [apiService] DialogueManager + expert.py Integration')
  console.log('Version:', 'DialogueManager v1.0')
  console.log('Base URL:', API_BASE_URL)
  console.log('Backend: expert.py + DialogueManager')
  console.log('🔧 CHANGEMENTS MAJEURS:')
  console.log('  - 🚀 Utilisation endpoint /ask simplifié')
  console.log('  - 🚀 Session ID via header X-Session-ID')
  console.log('  - 🚀 Body simplifié: { question }')
  console.log('  - 🚀 Support type: clarification/answer')
  console.log('  - 🚀 Conversion automatique format')
  console.log('FONCTIONNALITÉS:')
  console.log('  - ✅ Clarification intelligente automatique')
  console.log('  - ✅ Gestion mémoire conversation Postgres')
  console.log('  - ✅ Pipeline RAG modulaire')
  console.log('  - ✅ Toutes fonctions frontend préservées')
  console.groupEnd()
}

// Export par défaut de la fonction principale
export default generateAIResponse