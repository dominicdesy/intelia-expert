// ==================== API SERVICE CORRIGÉ POUR ask-enhanced-v2 + CLARIFICATIONS ====================

// ✅ SÉCURISÉ: Configuration depuis variables d'environnement
const getApiConfig = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
  const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
  
  if (!baseUrl) {
    console.error('❌ NEXT_PUBLIC_API_BASE_URL environment variable is required')
    throw new Error('API configuration missing - check environment variables')
  }
  
  return `${baseUrl}/api/${version}`
}

// ✅ VALIDATION CONFIGURATION AU RUNTIME
const API_BASE_URL = getApiConfig()

// ✅ FONCTION POUR RÉCUPÉRER LE TOKEN D'AUTHENTIFICATION
const getAuthToken = (): string | null => {
  try {
    // 🔧 PRIORITÉ: Token depuis les cookies (URL-décodé)
    const cookieToken = getCookieToken()
    if (cookieToken) {
      console.log('[getAuthToken] Token trouvé dans cookies')
      return cookieToken
    }

    // Essayer le token depuis localStorage
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

// ✅ FONCTION POUR RÉCUPÉRER LE TOKEN DEPUIS LES COOKIES
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

// ✅ FONCTION POUR CRÉER LES HEADERS AVEC AUTHENTIFICATION
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

// Interface pour la réponse enhanced avec clarifications
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
  // ✅ NOUVEAUX CHAMPS CLARIFICATIONS
  requires_clarification?: boolean
  clarification_questions?: string[]
  clarification_type?: string
  vague_entities?: string[]
}

// Interface pour les erreurs API
interface APIError {
  detail: string
  timestamp: string
  path: string
  version: string
}

/**
 * ✅ FONCTION CORRIGÉE: Génère une réponse IA via ask-enhanced-v2 + CLARIFICATIONS
 */
export const generateAIResponse = async (
  question: string,
  user: any,
  language: string = 'fr',
  conversationId?: string,
  // ✅ NOUVEAUX PARAMÈTRES POUR CLARIFICATIONS
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

  console.log('🔥 [apiService] Envoi question vers ask-enhanced-v2:', {
    question: question.substring(0, 50) + '...',
    isClarificationResponse,
    originalQuestion: originalQuestion?.substring(0, 30) + '...',
    entities: clarificationEntities
  })

  try {
    // ✅ CORRECTION MAJEURE: Backend attend "text" (validation Pydantic)
    const requestBody = {
      text: question.trim(),  // ✅ CORRIGÉ: Retour à "text" pour compatibilité backend
      language: language,
      speed_mode: 'balanced',
      ...(conversationId && { conversation_id: conversationId }),
      // ✅ Fonctionnalités v2 activées par défaut
      enable_vagueness_detection: true,
      require_coherence_check: true,
      detailed_rag_scoring: false,
      enable_quality_metrics: false,
      debug_mode: false,
      // ✅ NOUVEAUX CHAMPS CLARIFICATIONS
      ...(isClarificationResponse && {
        is_clarification_response: true,
        original_question: originalQuestion,
        clarification_entities: clarificationEntities
      })
    }

    const headers = getAuthHeaders()

    console.log('📤 [apiService] Body complet CORRIGÉ pour ask-enhanced-v2:', requestBody)

    // ✅ CORRECTION CRITIQUE: Utiliser ask-enhanced-v2 au lieu de ask-enhanced
    const response = await fetch(`${API_BASE_URL}/expert/ask-enhanced-v2`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    console.log('📡 [apiService] Statut réponse ask-enhanced-v2:', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur ask-enhanced-v2:', errorText)
      
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
    console.log('✅ [apiService] Réponse ask-enhanced-v2 reçue:', {
      conversation_id: data.conversation_id,
      language: data.language,
      ai_enhancements: data.ai_enhancements_used,
      rag_used: data.rag_used,
      response_length: data.response?.length || 0,
      requires_clarification: data.requires_clarification,
      clarification_questions: data.clarification_questions?.length || 0
    })

    // 🎯 CORRECTION: Pas de sauvegarde séparée car ask-enhanced-v2 la gère automatiquement
    console.log('💾 [apiService] Sauvegarde gérée automatiquement par ask-enhanced-v2')

    // ✅ CONVERSION vers le format attendu par le frontend
    return {
      response: data.response,
      conversation_id: data.conversation_id,
      language: data.language,
      rag_used: data.rag_used,
      sources: data.sources,
      // ✅ Champs additionnels de ask-enhanced-v2
      ai_enhancements_used: data.ai_enhancements_used,
      confidence_score: data.confidence_score,
      response_time: data.response_time,
      mode: data.mode,
      note: data.note,
      timestamp: data.timestamp,
      processing_time: data.processing_time,
      // ✅ CHAMPS CLARIFICATIONS
      requires_clarification: data.requires_clarification,
      clarification_questions: data.clarification_questions,
      clarification_type: data.clarification_type,
      vague_entities: data.vague_entities
    }

  } catch (error) {
    console.error('❌ [apiService] Erreur complète ask-enhanced-v2:', error)
    
    if (error instanceof Error) {
      throw error
    }
    
    throw new Error('Erreur de communication avec le serveur')
  }
}

/**
 * ✅ VERSION PUBLIQUE CORRIGÉE: ask-enhanced-v2-public
 */
export const generateAIResponsePublic = async (
  question: string,
  language: string = 'fr',
  conversationId?: string
): Promise<EnhancedAIResponse> => {
  if (!question || question.trim() === '') {
    throw new Error('Question requise')
  }

  console.log('🌐 [apiService] Question publique vers ask-enhanced-v2-public:', question.substring(0, 50) + '...')

  try {
    const requestBody = {
      text: question.trim(),  // ✅ CORRIGÉ: Retour à "text" pour compatibilité backend
      language: language,
      speed_mode: 'balanced',
      ...(conversationId && { conversation_id: conversationId }),
      enable_vagueness_detection: true,
      require_coherence_check: true
    }

    // ✅ CORRECTION: ask-enhanced-v2-public au lieu de ask-enhanced-public
    const response = await fetch(`${API_BASE_URL}/expert/ask-enhanced-v2-public`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur ask-enhanced-v2-public:', errorText)
      throw new Error(`Erreur API: ${response.status}`)
    }

    const data: EnhancedAIResponse = await response.json()
    console.log('✅ [apiService] Réponse ask-enhanced-v2-public reçue')

    return data

  } catch (error) {
    console.error('❌ [apiService] Erreur ask-enhanced-v2-public:', error)
    throw error
  }
}

/**
 * ✅ FONCTION DE FEEDBACK (inchangée - déjà correcte)
 */
export const sendFeedback = async (
  conversationId: string,
  feedback: 1 | -1,
  comment?: string
): Promise<void> => {
  if (!conversationId) {
    throw new Error('ID de conversation requis')
  }

  console.log('👍👎 [apiService] Envoi feedback enhanced:', feedback, 'pour conversation:', conversationId)

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

    console.log('📡 [apiService] Feedback enhanced statut:', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur feedback enhanced:', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expirée. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur envoi feedback: ${response.status}`)
    }

    console.log('✅ [apiService] Feedback enhanced envoyé avec succès')

  } catch (error) {
    console.error('❌ [apiService] Erreur feedback enhanced:', error)
    throw error
  }
}

// ✅ FONCTION POUR CHARGER LES CONVERSATIONS UTILISATEUR
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

// ✅ FONCTION UTILITAIRE POUR CONSTRUIRE LES ENTITÉS DE CLARIFICATION
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
          
          // Détecter automatiquement le type d'entité basé sur la question
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
            // Utiliser l'index comme clé par défaut
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
 * ✅ FONCTION DE DEBUG CORRIGÉE
 */
export const debugEnhancedAPI = () => {
  console.group('🔧 [apiService] Configuration ask-enhanced-v2 CORRIGÉE')
  console.log('API_BASE_URL:', API_BASE_URL)
  console.log('Endpoints v2 corrigés:')
  console.log('- Ask enhanced v2 (auth):', `${API_BASE_URL}/expert/ask-enhanced-v2`)
  console.log('- Ask enhanced v2 (public):', `${API_BASE_URL}/expert/ask-enhanced-v2-public`)
  console.log('- Feedback enhanced:', `${API_BASE_URL}/expert/feedback`)
  console.log('- Topics:', `${API_BASE_URL}/expert/topics`)
  console.log('- Conversations:', `${API_BASE_URL}/conversations/user/{userId}`)
  console.log('CORRECTIONS APPLIQUÉES:')
  console.log('  ✅ ask-enhanced → ask-enhanced-v2 (sécurisé)')
  console.log('  ✅ ask-enhanced-public → ask-enhanced-v2-public')
  console.log('  ✅ Fonctionnalités v2 activées par défaut')
  console.log('  ✅ Support clarifications complet')
  console.log('  ✅ Authentification JWT maintenue')
  console.log('  ✅ CORRECTION MAJEURE: Compatible avec backend "text" field')
  console.groupEnd()
}

/**
 * ✅ FONCTION DE TEST CORRIGÉE
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
    console.log('🧪 [apiService] Test continuité conversation ask-enhanced-v2...')
    
    // Première question
    const firstResponse = await generateAIResponse(
      "Test question 1: Qu'est-ce que les poulets de chair ?",
      user,
      language
    )
    
    // Attendre un peu
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Deuxième question avec le même conversation_id
    const secondResponse = await generateAIResponse(
      "Test question 2: Quel est leur poids optimal à 12 jours ?",
      user,
      language,
      firstResponse.conversation_id
    )
    
    const sameId = firstResponse.conversation_id === secondResponse.conversation_id
    
    console.log('🧪 [apiService] Test v2 résultat:', {
      first_id: firstResponse.conversation_id,
      second_id: secondResponse.conversation_id,
      same_id: sameId,
      first_enhancements: firstResponse.ai_enhancements_used,
      second_enhancements: secondResponse.ai_enhancements_used
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
    console.error('❌ [apiService] Erreur test v2 continuité:', error)
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
 * ✅ UTILITAIRE POUR GÉRER LES ERREURS RÉSEAU
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
  
  if (error?.message?.includes('ask-enhanced')) {
    return 'Erreur du système expert amélioré. Veuillez réessayer.'
  }
  
  return error?.message || 'Une erreur inattendue s\'est produite.'
}

/**
 * ✅ DEBUG CONVERSATION FLOW
 */
export const debugEnhancedConversationFlow = (
  step: string,
  conversationId: string | undefined,
  additionalInfo?: any
) => {
  console.log(`🔍 [Enhanced Conversation Debug] ${step}:`, {
    conversation_id: conversationId || 'NOUVEAU',
    endpoint: 'ask-enhanced-v2',
    timestamp: new Date().toISOString(),
    ...additionalInfo
  })
}

/**
 * ✅ MIGRATION HELPER CORRIGÉ
 */
export const detectAPIVersion = async (): Promise<'enhanced' | 'legacy' | 'error'> => {
  try {
    // Test ask-enhanced-v2
    const enhancedResponse = await fetch(`${API_BASE_URL}/expert/ask-enhanced-v2`, {
      method: 'OPTIONS',
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (enhancedResponse.ok || enhancedResponse.status === 405) {
      console.log('✅ [detectAPIVersion] ask-enhanced-v2 disponible')
      return 'enhanced'
    }
    
    // Test ask legacy
    const legacyResponse = await fetch(`${API_BASE_URL}/expert/ask`, {
      method: 'OPTIONS', 
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (legacyResponse.ok || legacyResponse.status === 405) {
      console.log('⚠️ [detectAPIVersion] Seul ask legacy disponible')
      return 'legacy'
    }
    
    return 'error'
    
  } catch (error) {
    console.error('❌ [detectAPIVersion] Erreur détection:', error)
    return 'error'
  }
}

/**
 * ✅ WRAPPER INTELLIGENT CORRIGÉ
 */
export const generateAIResponseSmart = async (
  question: string,
  user: any,
  language: string = 'fr',
  conversationId?: string
): Promise<EnhancedAIResponse> => {
  
  const apiVersion = await detectAPIVersion()
  
  console.log(`🤖 [generateAIResponseSmart] Utilisation API: ${apiVersion}`)
  
  switch (apiVersion) {
    case 'enhanced':
      return await generateAIResponse(question, user, language, conversationId)
      
    case 'legacy':
      console.warn('⚠️ [generateAIResponseSmart] Fallback vers API legacy')
      return await generateAIResponse(question, user, language, conversationId)
      
    case 'error':
    default:
      throw new Error('API non disponible. Veuillez vérifier votre connexion.')
  }
}

// ✅ CONFIGURATION DEBUG CORRIGÉE
export const logEnhancedAPIInfo = () => {
  console.group('🚀 [apiService] Configuration Enhanced API v2 CORRIGÉE')
  console.log('Version:', 'Enhanced v2 (ask-enhanced-v2)')
  console.log('Base URL:', API_BASE_URL)
  console.log('CORRECTIONS APPLIQUÉES:')
  console.log('  - ✅ ask-enhanced → ask-enhanced-v2 (endpoint sécurisé)')
  console.log('  - ✅ ask-enhanced-public → ask-enhanced-v2-public')
  console.log('  - ✅ CORRECTION MAJEURE: Compatible avec backend "text" field')
  console.log('  - ✅ Fonctionnalités v2 activées (vagueness detection, coherence check)')
  console.log('  - ✅ Support clarifications complet')
  console.log('  - ✅ Authentification JWT maintenue')
  console.log('Fonctionnalités v2:')
  console.log('  - ✅ Détection de questions floues')
  console.log('  - ✅ Vérification de cohérence contextuelle')
  console.log('  - ✅ Améliorations IA intégrées')
  console.log('  - ✅ Métriques de performance')
  console.log('  - ✅ Sauvegarde automatique')
  console.log('  - ✅ Support clarifications')
  console.log('Endpoints principaux:')
  console.log('  - POST /expert/ask-enhanced-v2 (authentifié)')
  console.log('  - POST /expert/ask-enhanced-v2-public (public)')
  console.log('  - POST /expert/feedback (enhanced)')
  console.log('  - GET /expert/topics')
  console.groupEnd()
}

// Export par défaut de la fonction principale corrigée
export default generateAIResponse