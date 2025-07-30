// ==================== API SERVICE AVEC AUTHENTIFICATION + CONVERSATION_ID ====================

// Configuration de base
const API_BASE_URL = 'https://expert-app-cngws.ondigitalocean.app/api/v1'

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

    // Ensuite essayer le token Supabase standard
    const supabaseToken = localStorage.getItem('supabase.auth.token')
    if (supabaseToken) {
      const parsed = JSON.parse(supabaseToken)
      if (parsed.access_token && parsed.access_token !== 'mock-jwt-token-for-development') {
        console.log('[getAuthToken] Token trouvé dans supabase.auth.token')
        return parsed.access_token
      }
    }

    // Enfin essayer le token depuis l'auth storage Intelia
    const authStorage = localStorage.getItem('intelia-auth-storage')
    if (authStorage) {
      const parsed = JSON.parse(authStorage)
      if (parsed?.state?.token) {
        console.log('[getAuthToken] Token trouvé dans intelia-auth-storage')
        return parsed.state.token
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
    // Récupérer le cookie Supabase
    const cookies = document.cookie.split(';')
    const sbCookie = cookies.find(cookie => 
      cookie.trim().startsWith('sb-cdrmjshmkdfwwtsfdvbl-auth-token=')
    )
    
    if (sbCookie) {
      // Extraire la valeur du cookie
      const cookieValue = sbCookie.split('=')[1]
      
      // Décoder l'URL
      const decodedValue = decodeURIComponent(cookieValue)
      console.log('[getCookieToken] Cookie value décodé:', decodedValue.substring(0, 50) + '...')
      
      // Parser le JSON
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

// Interface pour la réponse de l'API
interface AIResponse {
  response: string
  conversation_id: string
  language: string
  rag_used?: boolean
  sources?: string[]
}

// Interface pour les erreurs API
interface APIError {
  detail: string
  timestamp: string
  path: string
  version: string
}

/**
 * Génère une réponse IA via l'API Expert avec support conversation_id
 */
export const generateAIResponse = async (
  question: string,
  user: any,
  language: string = 'fr',
  conversationId?: string  // ✅ PARAMÈTRE POUR CONTINUATION CONVERSATION
): Promise<AIResponse> => {
  if (!question || question.trim() === '') {
    throw new Error('Question requise')
  }

  if (!user || !user.id) {
    throw new Error('Utilisateur requis')
  }

  console.log('🔥 [apiService] Envoi question:', question.substring(0, 50) + '...')
  console.log('🔥 [apiService] User ID:', user.id)
  console.log('🔥 [apiService] Conversation ID:', conversationId || 'Nouvelle conversation')

  try {
    // ✅ CORRECTION CRITIQUE: Inclure conversation_id ET user_id dans le body
    const requestBody = {
      text: question.trim(),
      user_id: user.id,  // ✅ AJOUT: user_id explicite
      language: language,
      speed_mode: 'balanced',  // ✅ AJOUT: mode par défaut
      ...(conversationId && { conversation_id: conversationId })  // ✅ AJOUT: conversation_id si fourni
    }

    const headers = getAuthHeaders()

    console.log('📤 [apiService] Body:', requestBody)
    console.log('📤 [apiService] Headers:', Object.keys(headers))

    const response = await fetch(`${API_BASE_URL}/expert/ask`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    console.log('📡 [apiService] Statut réponse:', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ [apiService] Erreur réponse:', errorText)
      
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

    const data: AIResponse = await response.json()
    console.log('✅ [apiService] Réponse reçue:', {
      conversation_id: data.conversation_id,
      language: data.language,
      rag_used: data.rag_used,
      response_length: data.response?.length || 0
    })

    return data

  } catch (error) {
    console.error('❌ [apiService] Erreur complète:', error)
    
    if (error instanceof Error) {
      throw error
    }
    
    throw new Error('Erreur de communication avec le serveur')
  }
}

/**
 * Envoie un feedback pour une conversation
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
      rating: feedback === 1 ? 'positive' : 'negative',  // ✅ CORRIGÉ: utiliser 'rating' comme attendu
      conversation_id: conversationId,
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
 * Récupère les suggestions de sujets populaires
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
      
      // Retourner des sujets par défaut en cas d'erreur
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
    
    // Retourner des sujets par défaut en cas d'erreur
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
 * Vérifie l'état de santé de l'API
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
 * ✅ NOUVELLE FONCTION: Test de l'API avec conversation_id
 */
export const testConversationContinuity = async (
  user: any,
  language: string = 'fr'
): Promise<{
  first_conversation_id: string,
  second_conversation_id: string,
  same_id: boolean,
  success: boolean
}> => {
  try {
    console.log('🧪 [apiService] Test continuité conversation...')
    
    // Première question
    const firstResponse = await generateAIResponse(
      "Test question 1: Qu'est-ce que Ross 308 ?",
      user,
      language
    )
    
    // Attendre un peu
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Deuxième question avec le même conversation_id
    const secondResponse = await generateAIResponse(
      "Test question 2: Quel est leur poids à 12 jours ?",
      user,
      language,
      firstResponse.conversation_id  // ✅ PASSER L'ID DE LA PREMIÈRE RÉPONSE
    )
    
    const sameId = firstResponse.conversation_id === secondResponse.conversation_id
    
    console.log('🧪 [apiService] Test résultat:', {
      first_id: firstResponse.conversation_id,
      second_id: secondResponse.conversation_id,
      same_id: sameId
    })
    
    return {
      first_conversation_id: firstResponse.conversation_id,
      second_conversation_id: secondResponse.conversation_id,
      same_id: sameId,
      success: true
    }
    
  } catch (error) {
    console.error('❌ [apiService] Erreur test continuité:', error)
    return {
      first_conversation_id: '',
      second_conversation_id: '',
      same_id: false,
      success: false
    }
  }
}

/**
 * Utilitaire pour gérer les erreurs réseau
 */
export const handleNetworkError = (error: any): string => {
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

/**
 * ✅ NOUVELLE FONCTION: Debug conversation_id dans la console
 */
export const debugConversationFlow = (
  step: string,
  conversationId: string | undefined,
  additionalInfo?: any
) => {
  console.log(`🔍 [Conversation Debug] ${step}:`, {
    conversation_id: conversationId || 'NOUVEAU',
    timestamp: new Date().toISOString(),
    ...additionalInfo
  })
}

// Export par défaut de la fonction principale
export default generateAIResponse