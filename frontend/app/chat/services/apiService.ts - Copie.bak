// ==================== API SERVICE UNIFIÉ - COMPATIBLE NOUVEAU BACKEND ====================

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

// 🚀 NOUVELLE FONCTION : Génération UUID compatible navigateur
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

// 🚀 INTERFACE MODIFIÉE : Ajout response_versions
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
  
  // 🚀 NOUVEAU : Toutes les versions de réponse
  response_versions?: {
    ultra_concise: string
    concise: string
    standard: string
    detailed: string
  }
  
  // Clarifications inchangées
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
}

// ✅ INTERFACE INCHANGÉE
interface APIError {
  detail: string
  timestamp: string
  path: string
  version: string
}

/**
 * 🔧 FONCTION PRINCIPALE CORRIGÉE : Utilise endpoint unifié /ask
 */
export const generateAIResponse = async (
  question: string,
  user: any,
  language: string = 'fr',
  conversationId?: string,
  // 🚀 NOUVEAU : Paramètre niveau de concision
  concisionLevel: 'ultra_concise' | 'concise' | 'standard' | 'detailed' = 'concise',
  // ✅ PARAMÈTRES EXISTANTS INCHANGÉS
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

  // 🔧 FIX CRITIQUE : Toujours générer un conversation_id
  const finalConversationId = conversationId || generateUUID()

  console.log('🎯 [apiService] Envoi question vers endpoint unifié /ask:', {
    question: question.substring(0, 50) + '...',
    conversation_id: finalConversationId,
    concisionLevel,
    isClarificationResponse,
    originalQuestion: originalQuestion?.substring(0, 30) + '...'
  })

  try {
    // 🔧 ENDPOINT CORRIGÉ : Utilise le nouvel endpoint unifié
    let endpoint = `${API_BASE_URL}/expert/ask`
    
    // ✅ ENRICHISSEMENT CLARIFICATION INCHANGÉ
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
      } else {
        console.log('⚠️ [apiService] Entités incomplètes détectées')
      }
    }

    // 🔧 BODY MODIFIÉ : Compatible avec le nouveau backend unifié
    const requestBody = {
      text: finalQuestion,
      language: language,
      // 🚀 NOUVEAU : Paramètres concision pour le backend unifié
      concision_level: concisionLevel,
      generate_all_versions: true,
      // 🔧 FIX CRITIQUE : Toujours inclure conversation_id
      conversation_id: finalConversationId,
      // ✅ CLARIFICATIONS INCHANGÉES mais adaptées au nouveau format
      ...(isClarificationResponse && {
        is_clarification_response: true,
        original_question: originalQuestion
      })
    }

    const headers = getAuthHeaders()

    console.log('📤 [apiService] Body pour endpoint unifié /ask:', {
      ...requestBody,
      conversation_id: `${finalConversationId.substring(0, 8)}...`
    })

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    console.log('📡 [apiService] Statut réponse endpoint unifié:', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur endpoint unifié:', errorText)
      
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

    const data: EnhancedAIResponse = await response.json()
    console.log('✅ [apiService] Réponse endpoint unifié reçue:', {
      conversation_id: data.conversation_id,
      language: data.language,
      mode: data.mode,
      rag_used: data.rag_used,
      response_length: data.response?.length || 0,
      // 🚀 NOUVEAU : Log versions reçues
      versions_received: Object.keys(data.response_versions || {}),
      clarification_requested: data.clarification_result?.clarification_requested || false,
      conversation_id_sent: finalConversationId,
      conversation_id_received: data.conversation_id,
      ids_match: finalConversationId === data.conversation_id
    })

    // 🚀 FALLBACK : Si backend pas encore modifié pour response_versions
    if (!data.response_versions) {
      console.warn('⚠️ [apiService] Backend n\'a pas fourni response_versions - utilisation fallback')
      data.response_versions = {
        ultra_concise: data.response,
        concise: data.response,
        standard: data.response,
        detailed: data.response
      }
    }

    // ✅ MAPPING CLARIFICATION INCHANGÉ
    const processedData: EnhancedAIResponse = {
      response: data.response,
      // 🚀 NOUVEAU : Inclure toutes les versions
      response_versions: data.response_versions,
      conversation_id: data.conversation_id,
      language: data.language,
      rag_used: data.rag_used,
      sources: data.sources,
      ai_enhancements_used: data.ai_enhancements_used,
      confidence_score: data.confidence_score,
      response_time: data.response_time,
      mode: data.mode,
      note: data.note,
      timestamp: data.timestamp,
      processing_time: data.processing_time,
      clarification_result: data.clarification_result,
      // ✅ COMPATIBILITÉ CLARIFICATIONS INCHANGÉE
      requires_clarification: data.clarification_result?.clarification_requested || false,
      clarification_questions: data.clarification_result?.missing_information?.map(info => {
        const questionMap: Record<string, string> = {
          'breed': 'Quelle est la race/souche du poulet ?',
          'sex': 'Est-ce un mâle ou une femelle ?',
          'race/souche': 'Quelle est la race/souche du poulet ?',
          'sexe': 'Est-ce un mâle ou une femelle ?'
        }
        return questionMap[info] || `Pouvez-vous préciser : ${info} ?`
      }) || [],
      clarification_type: data.clarification_result?.clarification_type,
      vague_entities: data.clarification_result?.missing_information || []
    }

    console.log('🎯 [apiService] Données traitées avec mapping clarification:', {
      requires_clarification: processedData.requires_clarification,
      clarification_questions_count: processedData.clarification_questions?.length || 0,
      clarification_result_exists: !!processedData.clarification_result,
      versions_available: Object.keys(processedData.response_versions || {}),
      conversation_id_final: processedData.conversation_id
    })

    return processedData

  } catch (error) {
    console.error('❌ [apiService] Erreur complète endpoint unifié:', error)
    
    if (error instanceof Error) {
      throw error
    }
    
    throw new Error('Erreur de communication avec le serveur')
  }
}

/**
 * 🔧 VERSION PUBLIQUE CORRIGÉE : Utilise endpoint unifié /ask-public
 */
export const generateAIResponsePublic = async (
  question: string,
  language: string = 'fr',
  conversationId?: string,
  // 🚀 NOUVEAU : Paramètre concision pour version publique
  concisionLevel: 'ultra_concise' | 'concise' | 'standard' | 'detailed' = 'concise'
): Promise<EnhancedAIResponse> => {
  if (!question || question.trim() === '') {
    throw new Error('Question requise')
  }

  // 🔧 FIX CRITIQUE : Toujours générer un conversation_id
  const finalConversationId = conversationId || generateUUID()

  console.log('🌐 [apiService] Question publique vers endpoint unifié /ask-public:', {
    question: question.substring(0, 50) + '...',
    conversation_id: finalConversationId,
    concisionLevel
  })

  try {
    // 🔧 BODY CORRIGÉ : Compatible avec endpoint unifié
    const requestBody = {
      text: question.trim(),
      language: language,
      concision_level: concisionLevel,
      generate_all_versions: true,
      // 🔧 FIX CRITIQUE : Toujours inclure conversation_id
      conversation_id: finalConversationId
    }

    // 🔧 ENDPOINT CORRIGÉ : Utilise le nouvel endpoint unifié public
    const response = await fetch(`${API_BASE_URL}/expert/ask-public`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur endpoint unifié public:', errorText)
      throw new Error(`Erreur API: ${response.status}`)
    }

    const data: EnhancedAIResponse = await response.json()
    console.log('✅ [apiService] Réponse endpoint unifié public reçue:', {
      conversation_id: data.conversation_id,
      mode: data.mode,
      rag_used: data.rag_used,
      conversation_id_sent: finalConversationId,
      conversation_id_received: data.conversation_id
    })

    // 🚀 FALLBACK : Si backend pas modifié pour response_versions
    if (!data.response_versions) {
      data.response_versions = {
        ultra_concise: data.response,
        concise: data.response,
        standard: data.response,
        detailed: data.response
      }
    }

    // ✅ MAPPING CLARIFICATION INCHANGÉ
    return {
      ...data,
      requires_clarification: data.clarification_result?.clarification_requested || false,
      clarification_questions: data.clarification_result?.missing_information?.map(info => {
        const questionMap: Record<string, string> = {
          'breed': 'Quelle est la race/souche du poulet ?',
          'sex': 'Est-ce un mâle ou une femelle ?',
          'race/souche': 'Quelle est la race/souche du poulet ?',
          'sexe': 'Est-ce un mâle ou une femelle ?'
        }
        return questionMap[info] || `Pouvez-vous préciser : ${info} ?`
      }) || [],
      clarification_type: data.clarification_result?.clarification_type,
      vague_entities: data.clarification_result?.missing_information || []
    }

  } catch (error) {
    console.error('❌ [apiService] Erreur endpoint unifié public:', error)
    throw error
  }
}

/**
 * ✅ FONCTION FEEDBACK INCHANGÉE
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

/**
 * ✅ FONCTION CONVERSATIONS INCHANGÉE
 */
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

/**
 * ✅ FONCTION TOPICS INCHANGÉE
 */
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

/**
 * ✅ FONCTION HEALTH CHECK MISE À JOUR
 */
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
 * ✅ FONCTION CLARIFICATION ENTITIES INCHANGÉE
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
 * 🔧 FONCTION DEBUG MISE À JOUR - Compatible nouveau backend
 */
export const debugEnhancedAPI = () => {
  console.group('🔧 [apiService] Configuration API unifiée + RESPONSE_VERSIONS')
  console.log('API_BASE_URL:', API_BASE_URL)
  console.log('Endpoints nouveaux (backend unifié):')
  console.log('- Ask unifié (auth):', `${API_BASE_URL}/expert/ask`)
  console.log('- Ask unifié (public):', `${API_BASE_URL}/expert/ask-public`)
  console.log('- Feedback:', `${API_BASE_URL}/expert/feedback`)
  console.log('- Topics:', `${API_BASE_URL}/expert/topics`)
  console.log('- Conversations:', `${API_BASE_URL}/conversations/user/{userId}`)
  console.log('🔧 CORRECTIONS BACKEND UNIFIÉ:')
  console.log('  ✅ Plus d\'endpoint /ask-enhanced-v2 (supprimé)')
  console.log('  ✅ Nouvel endpoint /ask unifié (authentifié)')
  console.log('  ✅ Nouvel endpoint /ask-public unifié (public)')
  console.log('  ✅ conversation_id toujours généré automatiquement')
  console.log('  ✅ Logs détaillés pour debugging')
  console.log('NOUVELLES FEATURES PRÉSERVÉES:')
  console.log('  🚀 concision_level dans body request')
  console.log('  🚀 generate_all_versions: true')
  console.log('  🚀 response_versions dans réponse')
  console.log('  🚀 Sélection version côté frontend')
  console.log('FEATURES PRÉSERVÉES:')
  console.log('  ✅ Détection clarification via clarification_result')
  console.log('  ✅ Mapping clarification_result vers requires_clarification')
  console.log('  ✅ Support clarifications complet')
  console.log('  ✅ Authentification JWT maintenue')
  console.log('  ✅ Toutes fonctions existantes préservées')
  console.groupEnd()
}

/**
 * 🔧 FONCTION TEST CORRIGÉE - Compatible backend unifié
 */
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
    console.log('🧪 [apiService] Test continuité conversation backend unifié...')
    
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
    
    console.log('🧪 [apiService] Test backend unifié résultat:', {
      first_id: firstResponse.conversation_id,
      second_id: secondResponse.conversation_id,
      same_id: sameId,
      first_enhancements: firstResponse.ai_enhancements_used,
      second_enhancements: secondResponse.ai_enhancements_used,
      both_ids_present: !!(firstResponse.conversation_id && secondResponse.conversation_id)
    })
    
    return {
      first_conversation_id: firstResponse.conversation_id,
      second_conversation_id: secondResponse.conversation_id,
      same_id: sameId,
      success: true,
      enhancements_used: [
        ...(firstResponse.ai_enhancements_used || []),
        ...(secondResponse.ai_enhancements_used || [])
      ]
    }
    
  } catch (error) {
    console.error('❌ [apiService] Erreur test backend unifié continuité:', error)
    return {
      first_conversation_id: '',
      second_conversation_id: '',
      same_id: false,
      success: false,
      enhancements_used: []
    }
  }
}

/**
 * ✅ UTILITAIRES INCHANGÉS
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
  
  if (error?.message?.includes('endpoint unifié') || error?.message?.includes('ask')) {
    return 'Erreur du système expert. Veuillez réessayer.'
  }
  
  return error?.message || 'Une erreur inattendue s\'est produite.'
}

export const debugEnhancedConversationFlow = (
  step: string,
  conversationId: string | undefined,
  additionalInfo?: any
) => {
  console.log(`🔍 [Enhanced Conversation Debug] ${step}:`, {
    conversation_id: conversationId || 'GÉNÉRÉ_AUTO',
    endpoint: 'ask (unifié)',
    timestamp: new Date().toISOString(),
    ...additionalInfo
  })
}

/**
 * 🔧 DÉTECTION API MISE À JOUR - Compatible backend unifié
 */
export const detectAPIVersion = async (): Promise<'unified' | 'legacy' | 'error'> => {
  try {
    // Test du nouvel endpoint unifié
    const unifiedResponse = await fetch(`${API_BASE_URL}/expert/ask`, {
      method: 'OPTIONS',
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (unifiedResponse.ok || unifiedResponse.status === 405) {
      console.log('✅ [detectAPIVersion] Backend unifié /ask disponible')
      return 'unified'
    }
    
    // Fallback vers l'ancien système si besoin
    const legacyResponse = await fetch(`${API_BASE_URL}/expert/ask-enhanced`, {
      method: 'OPTIONS', 
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (legacyResponse.ok || legacyResponse.status === 405) {
      console.log('⚠️ [detectAPIVersion] Fallback vers ask-enhanced legacy')
      return 'legacy'
    }
    
    return 'error'
    
  } catch (error) {
    console.error('❌ [detectAPIVersion] Erreur détection:', error)
    return 'error'
  }
}

export const generateAIResponseSmart = async (
  question: string,
  user: any,
  language: string = 'fr',
  conversationId?: string
): Promise<EnhancedAIResponse> => {
  
  const apiVersion = await detectAPIVersion()
  
  console.log(`🤖 [generateAIResponseSmart] Utilisation API: ${apiVersion}`)
  
  switch (apiVersion) {
    case 'unified':
      return await generateAIResponse(question, user, language, conversationId)
      
    case 'legacy':
      console.warn('⚠️ [generateAIResponseSmart] Fallback vers API legacy')
      return await generateAIResponse(question, user, language, conversationId)
      
    case 'error':
    default:
      throw new Error('API non disponible. Veuillez vérifier votre connexion.')
  }
}

/**
 * 🚀 NOUVELLE FONCTION : Information configuration backend unifié
 */
export const logEnhancedAPIInfo = () => {
  console.group('🚀 [apiService] Configuration Backend Unifié + Response Versions')
  console.log('Version:', 'Backend Unifié v2.0 avec response_versions')
  console.log('Base URL:', API_BASE_URL)
  console.log('🔧 CHANGEMENTS MAJEURS BACKEND:')
  console.log('  - 🔧 Endpoint /ask-enhanced-v2: SUPPRIMÉ (404)')
  console.log('  - 🚀 Nouvel endpoint /ask: UNIFIÉ et sécurisé')
  console.log('  - 🚀 Nouvel endpoint /ask-public: UNIFIÉ et public')
  console.log('  - 🔧 conversation_id: TOUJOURS généré automatiquement')
  console.log('  - 🔧 Compatible avec l\'ancien frontend')
  console.log('NOUVELLES FONCTIONNALITÉS BACKEND:')
  console.log('  - 🚀 concision_level: ultra_concise|concise|standard|detailed')
  console.log('  - 🚀 generate_all_versions: true (backend génère toutes versions)')
  console.log('  - 🚀 response_versions: object avec toutes les versions')
  console.log('  - 🚀 Système expert unifié et simplifié')
  console.log('FONCTIONNALITÉS PRÉSERVÉES:')
  console.log('  - ✅ Détection automatique questions vagues')
  console.log('  - ✅ Clarification intelligente race/sexe')
  console.log('  - ✅ Enrichissement automatique questions')
  console.log('  - ✅ Traitement réponses clarification')
  console.log('  - ✅ Toutes fonctions existantes (feedback, conversations, etc.)')
  console.log('Endpoints (NOUVEAUX):')
  console.log('  - POST /expert/ask (authentifié, unifié)')
  console.log('  - POST /expert/ask-public (public, unifié)')
  console.log('  - POST /expert/feedback')
  console.log('  - GET /expert/topics')
  console.log('  - GET /conversations/user/{userId}')
  console.log('  - GET /system/health')
  console.groupEnd()
}

// Export par défaut de la fonction principale
export default generateAIResponse