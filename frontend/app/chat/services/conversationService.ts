import { 
  Conversation, 
  ConversationWithMessages, 
  ConversationGroup,
  ConversationHistoryResponse,
  ConversationDetailResponse,
  ConversationGroupingOptions,
  Message,
  ConversationData
} from '../../../types'

// Import critique: Utiliser loadUserConversations d'apiService au lieu de dupliquer la logique
import { loadUserConversations, sendFeedback, deleteConversation } from './apiService'

// Interface cache côté frontend pour les conversations
interface ConversationCache {
  conversations: Conversation[]
  timestamp: number
  userId: string
}

// Circuit breaker corrigé avec reset moins fréquent
class ConversationLoadingCircuitBreaker {
  private attempts = 0
  private lastAttempt = 0
  private readonly MAX_ATTEMPTS = 2
  private readonly RESET_INTERVAL = 600000 // 10 minutes au lieu de 30 secondes

  canAttempt(): boolean {
    const now = Date.now()
    
    if (now - this.lastAttempt > this.RESET_INTERVAL) {
      this.attempts = 0
    }

    if (this.attempts >= this.MAX_ATTEMPTS) {
      console.warn('[ConversationService] Circuit breaker: BLOQUÉ pour 10 minutes')
      return false
    }

    return true
  }

  recordAttempt(): void {
    this.attempts++
    this.lastAttempt = Date.now()
    console.log(`[ConversationService] Circuit breaker: tentative ${this.attempts}/${this.MAX_ATTEMPTS}`)
  }

  recordSuccess(): void {
    this.attempts = 0
    console.log('[ConversationService] Circuit breaker: reset après succès')
  }

  recordFailure(): void {
    console.log(`[ConversationService] Circuit breaker: échec ${this.attempts}/${this.MAX_ATTEMPTS}`)
  }
}

// Fonction utilitaire pour créer un objet Conversation typé
function createConversation(data: {
  id: string
  title: string
  preview: string
  message_count: number
  created_at: string
  updated_at: string
  feedback?: any
  language: string
  last_message_preview: string
}): Conversation {
  return {
    id: data.id,
    title: data.title,
    preview: data.preview,
    message_count: data.message_count,
    created_at: data.created_at,
    updated_at: data.updated_at,
    feedback: data.feedback,
    language: data.language,
    last_message_preview: data.last_message_preview,
    status: 'active' as const
  }
}

// Service conversations corrigé - utilise apiService.ts pour éviter duplication
export class ConversationService {
  private baseUrl: string
  private loggingEnabled = true
  private circuitBreaker = new ConversationLoadingCircuitBreaker()
  
  // Propriétés cache côté frontend
  private conversationsCache: ConversationCache | null = null
  private readonly CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

  constructor() {
    // Construction URL plus propre
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, '') // Enlever trailing slashes
    const apiVersion = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
    
    if (!apiBaseUrl) {
      console.error('NEXT_PUBLIC_API_BASE_URL environment variable missing')
      this.loggingEnabled = false
      this.baseUrl = ''
      return
    }
    
    // URL construite proprement
    this.baseUrl = `${apiBaseUrl}/api/${apiVersion}`
    console.log('ConversationService configuré:', apiBaseUrl)
  }

  private getAuthToken(): string {
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
          return parsed[0]
        }
      }

      const sbToken = localStorage.getItem('sb-cdrmjshmkdfwwtsfdvbl-auth-token')
      if (sbToken) {
        try {
          const parsed = JSON.parse(sbToken)
          if (Array.isArray(parsed) && parsed[0]) {
            return parsed[0]
          }
        } catch (e) {
          console.warn('[ConversationService] Failed to parse localStorage token')
        }
      }

      return ''
    } catch (error) {
      console.error('[ConversationService] Error getting auth token:', error)
      return ''
    }
  }

  // Headers GET nettoyés - pas de Content-Type pour éviter preflight CORS
  private getHeaders(method: 'GET' | 'POST' | 'PATCH' | 'DELETE' = 'GET'): Record<string, string> {
    const token = this.getAuthToken()
    
    if (method === 'GET') {
      // Seulement Authorization et Accept pour GET - pas de Content-Type
      return {
        'Accept': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      }
    } else {
      // Pour POST/PATCH/DELETE: headers complets
      return {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      }
    }
  }

  // Gestion du cache
  private getCachedConversations(userId: string): Conversation[] | null {
    if (!this.conversationsCache) {
      return null
    }

    const now = Date.now()
    const isExpired = (now - this.conversationsCache.timestamp) > this.CACHE_DURATION
    const isDifferentUser = this.conversationsCache.userId !== userId

    if (isExpired || isDifferentUser) {
      console.log('[ConversationService] Cache expiré ou utilisateur différent')
      this.conversationsCache = null
      return null
    }

    console.log('[ConversationService] Utilisation cache local')
    return this.conversationsCache.conversations
  }

  // Mise à jour du cache
  private setCachedConversations(userId: string, conversations: Conversation[]): void {
    this.conversationsCache = {
      conversations: [...conversations], // Copie pour éviter les mutations
      timestamp: Date.now(),
      userId: userId
    }
    console.log(`[ConversationService] Cache mis à jour: ${conversations.length} conversations`)
  }

  // Cache avec délégation vers apiService
  private async loadConversationsWithCache(userId: string): Promise<{ conversations: Conversation[], fromCache: boolean }> {
    // Vérifier le cache d'abord
    const cached = this.getCachedConversations(userId)
    if (cached && cached.length > 0) {
      return { conversations: cached, fromCache: true }
    }

    // Pas de cache valide, appeler l'API
    console.log('[ConversationService] Chargement depuis API...')
    const result = await loadUserConversations(userId)
    
    if (result && result.conversations) {
      // Transformer les données pour compatibilité
      const formattedConversations: Conversation[] = result.conversations.map((conv: any) => {
        // Si c'est déjà au bon format, l'utiliser directement
        if (conv.title && conv.preview && conv.message_count !== undefined) {
          return conv as Conversation
        }
        
        // Sinon transformer depuis format ancien
        const firstQuestion = conv.question?.split('\n--- Question suivante ---\n')?.[0] || conv.question || 'Conversation sans titre'
        const title = firstQuestion.length > 100 ? firstQuestion.substring(0, 100) + '...' : firstQuestion
        
        const responses = conv.response?.split('\n--- Réponse suivante ---\n') || [conv.response]
        const lastResponse = responses[responses.length - 1] || 'Aucune réponse'
        const lastMessagePreview = lastResponse.length > 300 ? lastResponse.substring(0, 300) + '...' : lastResponse

        return createConversation({
          id: conv.conversation_id || conv.id || conv.session_id,
          title: title,
          preview: firstQuestion,
          message_count: conv.message_count || 2,
          created_at: conv.timestamp || conv.created_at || new Date().toISOString(),
          updated_at: conv.updated_at || conv.timestamp || new Date().toISOString(),
          feedback: conv.feedback,
          language: conv.language || 'fr',
          last_message_preview: lastMessagePreview
        })
      })

      // Mettre à jour le cache
      this.setCachedConversations(userId, formattedConversations)
      
      return { conversations: formattedConversations, fromCache: false }
    }

    return { conversations: [], fromCache: false }
  }

  async getConversationWithMessages(conversationId: string): Promise<ConversationWithMessages | null> {
    try {
      console.log('[ConversationService] Chargement conversation complète:', conversationId)
      
      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}`, {
        method: 'GET',
        headers: this.getHeaders('GET')
      })
      
      if (response.ok) {
        const data = await response.json()
        
        console.log('[ConversationService] Données récupérées:', {
          id: data.conversation?.conversation_id,
          questionLength: data.conversation?.question?.length || 0,
          responseLength: (data.conversation?.full_text ?? data.conversation?.response)?.length || 0
        })
        
        if (data.conversation && data.conversation.question && data.conversation.response) {
          const conversationWithMessages = this.transformToConversationWithMessages(data.conversation)
          
          if (conversationWithMessages.messages.length > 0) {
            console.log('[ConversationService] Conversation transformée avec messages complets')
            return conversationWithMessages
          }
        }
      }
      
      console.warn('[ConversationService] Impossible de récupérer la conversation complète')
      return null
      
    } catch (error) {
      console.error('[ConversationService] Erreur getConversationWithMessages:', error)
      return null
    }
  }

  async getConversationHistory(
    userId: string, 
    options: ConversationGroupingOptions = {
      groupBy: 'date',
      sortBy: 'updated_at', 
      sortOrder: 'desc',
      limit: 50
    }
  ): Promise<ConversationHistoryResponse> {
    try {
      console.log('[ConversationService] Chargement historique pour:', userId)
      
      const params = new URLSearchParams({
        groupBy: options.groupBy,
        sortBy: options.sortBy,
        sortOrder: options.sortOrder,
        ...(options.limit && { limit: options.limit.toString() }),
        ...(options.offset && { offset: options.offset.toString() })
      })

      const response = await fetch(
        `${this.baseUrl}/v1/conversations/history/${userId}?${params}`,
        {
          method: 'GET',
          headers: this.getHeaders('GET')
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to load conversation history`)
      }

      const data = await response.json()
      console.log('[ConversationService] Historique chargé:', data.total_count, 'conversations')
      
      return data
      
    } catch (error) {
      console.error('[ConversationService] Erreur chargement historique:', error)
      throw error
    }
  }

  async getConversationDetail(conversationId: string): Promise<ConversationDetailResponse> {
    try {
      console.log('[ConversationService] Chargement conversation:', conversationId)
      
      const response = await fetch(
        `${this.baseUrl}/v1/conversations/${conversationId}`,
        {
          method: 'GET',
          headers: this.getHeaders('GET')
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to load conversation`)
      }

      const data = await response.json()
      console.log('[ConversationService] Conversation chargée:', data.conversation.message_count, 'messages')
      
      return data
      
    } catch (error) {
      console.error('[ConversationService] Erreur chargement conversation:', error)
      throw error
    }
  }

  groupConversationsByDate(conversations: Conversation[]): ConversationGroup[] {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000)
    const thisWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)
    const thisMonth = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)

    const groups: ConversationGroup[] = [
      { title: "Aujourd'hui", conversations: [] },
      { title: "Hier", conversations: [] },
      { title: "Cette semaine", conversations: [] },
      { title: "Ce mois-ci", conversations: [] },
      { title: "Plus ancien", conversations: [] }
    ]

    conversations.forEach(conv => {
      const convDate = new Date(conv.updated_at)
      
      if (convDate >= today) {
        groups[0].conversations.push(conv)
      } else if (convDate >= yesterday) {
        groups[1].conversations.push(conv)
      } else if (convDate >= thisWeek) {
        groups[2].conversations.push(conv)
      } else if (convDate >= thisMonth) {
        groups[3].conversations.push(conv)
      } else {
        groups[4].conversations.push(conv)
      }
    })

    return groups.filter(group => group.conversations.length > 0)
  }

  // Méthode critique modifiée - utilise apiService.ts avec cache
  async getUserConversations(userId: string, limit = 50): Promise<Conversation[]> {
    if (!this.circuitBreaker.canAttempt()) {
      console.warn('[ConversationService] Circuit breaker actif - tentatives bloquées temporairement')
      
      // Même en circuit breaker, essayer le cache
      const cached = this.getCachedConversations(userId)
      if (cached && cached.length > 0) {
        console.log('[ConversationService] Utilisation cache malgré circuit breaker')
        return cached.slice(0, limit)
      }
      
      return []
    }

    if (!this.loggingEnabled) {
      console.log('Logging désactivé - conversations non récupérées')
      return []
    }

    console.log('[ConversationService] Récupération conversations pour:', userId)
    this.circuitBreaker.recordAttempt()

    try {
      // Utiliser la méthode avec cache
      const { conversations, fromCache } = await this.loadConversationsWithCache(userId)
      
      if (!conversations || conversations.length === 0) {
        console.log('[ConversationService] Aucune conversation via cache/API, essai fallback localStorage...')
        const fallbackResult = await this.getConversationsFromLocalStorage(limit)
        if (fallbackResult.length > 0) {
          // Mettre à jour le cache avec le fallback
          this.setCachedConversations(userId, fallbackResult)
          this.circuitBreaker.recordSuccess()
        } else {
          this.circuitBreaker.recordFailure()
        }
        return fallbackResult
      }

      console.log(`[ConversationService] ${conversations.length} conversations récupérées ${fromCache ? '(cache)' : '(API)'}`)
      
      this.circuitBreaker.recordSuccess()
      return conversations.slice(0, limit)
      
    } catch (error) {
      console.error('[ConversationService] Erreur cache/API, fallback localStorage...', error)
      
      // En cas d'erreur, essayer le cache en dernier recours
      const cached = this.getCachedConversations(userId)
      if (cached && cached.length > 0) {
        console.log('[ConversationService] Utilisation cache en fallback d\'erreur')
        this.circuitBreaker.recordSuccess()
        return cached.slice(0, limit)
      }
      
      try {
        const fallbackResult = await this.getConversationsFromLocalStorage(limit)
        if (fallbackResult.length > 0) {
          this.setCachedConversations(userId, fallbackResult)
          this.circuitBreaker.recordSuccess()
        } else {
          this.circuitBreaker.recordFailure()
        }
        return fallbackResult
      } catch (fallbackError) {
        console.error('Erreur fallback localStorage:', fallbackError)
        this.circuitBreaker.recordFailure()
        return []
      }
    }
  }

  async getConversationsFromLocalStorage(limit: number): Promise<Conversation[]> {
    try {
      const recentSessionIds = this.getRecentSessionIds()
      
      if (recentSessionIds.length === 0) {
        console.log('Aucune session localStorage trouvée')
        return []
      }
      
      console.log(`${recentSessionIds.length} sessions localStorage trouvées`)
      
      const conversations: Conversation[] = []
      
      for (const sessionId of recentSessionIds.slice(0, limit)) {
        try {
          console.log(`Récupération session: ${sessionId}`)
          
          const response = await fetch(`${this.baseUrl}/conversations/${sessionId}`, {
            method: 'GET',
            headers: this.getHeaders('GET')
          })
          
          if (response.ok) {
            const data = await response.json()
            
            if (data.session_id) {
              const conversation = createConversation({
                id: data.session_id,
                title: this.extractTitleFromConversation(data),
                preview: this.extractPreviewFromConversation(data),
                message_count: this.extractMessageCount(data),
                created_at: data.timestamp || new Date().toISOString(),
                updated_at: data.updated_at || data.timestamp || new Date().toISOString(),
                feedback: data.feedback,
                language: data.language || 'fr',
                last_message_preview: this.extractLastMessagePreview(data)
              })
              
              conversations.push(conversation)
              console.log(`Session ${sessionId} transformée`)
            } else {
              console.log(`Session ${sessionId} - pas de session_id`)
            }
          } else {
            console.log(`Session ${sessionId} - status ${response.status}`)
          }
        } catch (error) {
          console.log(`Erreur récupération session ${sessionId}:`, error)
        }
      }
      
      console.log(`${conversations.length} conversations récupérées via localStorage fallback`)
      
      conversations.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      
      return conversations
      
    } catch (error) {
      console.error('Erreur fallback localStorage:', error)
      return []
    }
  }

  private extractTitleFromConversation(data: any): string {
    if (data.question && typeof data.question === 'string') {
      const title = data.question.substring(0, 100)
      return title.length === 100 ? title + '...' : title
    }
    
    if (data.context?.messages?.length > 0) {
      const firstUserMessage = data.context.messages.find((m: any) => m.isUser)
      if (firstUserMessage?.content) {
        const title = firstUserMessage.content.substring(0, 100)
        return title.length === 100 ? title + '...' : title
      }
    }
    
    return `Conversation ${data.session_id?.substring(0, 8) || 'inconnue'}`
  }

  private extractPreviewFromConversation(data: any): string {
    if (data.question && typeof data.question === 'string') {
      return data.question
    }
    
    if (data.context?.messages?.length > 0) {
      const firstUserMessage = data.context.messages.find((m: any) => m.isUser)
      if (firstUserMessage?.content) {
        return firstUserMessage.content
      }
    }
    
    return 'Conversation sans question définie'
  }

  private extractMessageCount(data: any): number {
    if (data.context?.messages?.length > 0) {
      return data.context.messages.length
    }
    
    let count = 0
    if (data.question) count++
    if (data.response) count++
    
    return count || 2
  }

  private extractLastMessagePreview(data: any): string {
    if (data.response && typeof data.response === 'string') {
      const preview = data.response.substring(0, 300)
      return preview.length === 300 ? preview + '...' : preview
    }
    
    if (data.context?.messages?.length > 0) {
      const lastAssistantMessage = [...data.context.messages].reverse().find((m: any) => !m.isUser)
      if (lastAssistantMessage?.content) {
        const preview = lastAssistantMessage.content.substring(0, 300)
        return preview.length === 300 ? preview + '...' : preview
      }
    }
    
    return 'Aucune réponse disponible'
  }

  private getRecentSessionIds(): string[] {
    try {
      const stored = localStorage.getItem('recent_conversation_sessions')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed)) {
          return parsed.slice(0, 20)
        }
      }
    } catch (error) {
      console.warn('Erreur lecture sessions récentes:', error)
    }
    
    return []
  }

  storeRecentSessionId(sessionId: string): void {
    try {
      const existing = this.getRecentSessionIds()
      const updated = [sessionId, ...existing.filter(id => id !== sessionId)].slice(0, 50)
      localStorage.setItem('recent_conversation_sessions', JSON.stringify(updated))
      console.log('Session ID stocké pour historique:', sessionId.substring(0, 8) + '...')
    } catch (error) {
      console.warn('Erreur stockage session ID:', error)
    }
  }

  async discoverWorkingEndpoints(): Promise<string[]> {
    console.log('=== DÉCOUVERTE DES ENDPOINTS FONCTIONNELS ===')
    
    const endpointsToTest = [
      '/conversations',
      '/conversations/list', 
      '/conversations/all',
      '/conversations/history',
      '/expert/conversations',
      '/expert/sessions',
      '/expert/list',
      '/sessions',
      '/sessions/list',
      '/history'
    ]
    
    const workingEndpoints: string[] = []
    
    for (const endpoint of endpointsToTest) {
      try {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
          method: 'GET',
          headers: this.getHeaders('GET')
        })
        
        console.log(`${endpoint}: ${response.status} ${response.statusText}`)
        
        if (response.ok) {
          const data = await response.json()
          console.log(`ENDPOINT FONCTIONNEL: ${endpoint}`)
          console.log(`Structure:`, Array.isArray(data) ? `Array[${data.length}]` : Object.keys(data))
          workingEndpoints.push(endpoint)
        }
      } catch (error) {
        console.log(`${endpoint}: ${error.message}`)
      }
    }
    
    console.log('Endpoints fonctionnels découverts:', workingEndpoints)
    return workingEndpoints
  }

  transformToConversationWithMessages(conversationData: any): ConversationWithMessages {
    const messages: Message[] = []
    
    if (conversationData.question && conversationData.response) {
      const questions = conversationData.question.split('\n--- Question suivante ---\n')
      const responses = (conversationData.full_text ?? conversationData.response).split('\n--- Réponse suivante ---\n')
      
      for (let i = 0; i < Math.max(questions.length, responses.length); i++) {
        if (questions[i]) {
          messages.push({
            id: `${conversationData.conversation_id || conversationData.id}_user_${i}`,
            content: questions[i].trim(),
            isUser: true,
            timestamp: new Date(conversationData.timestamp || new Date()),
            conversation_id: conversationData.conversation_id || conversationData.id
          })
        }
        
        if (responses[i]) {
          messages.push({
            id: `${conversationData.conversation_id || conversationData.id}_assistant_${i}`,
            content: responses[i].trim(),
            isUser: false,
            timestamp: new Date(conversationData.timestamp || new Date()),
            conversation_id: conversationData.conversation_id || conversationData.id,
            feedback: i === responses.length - 1 && conversationData.feedback === 1 ? 'positive' 
                    : i === responses.length - 1 && conversationData.feedback === -1 ? 'negative' 
                    : null,
            feedbackComment: i === responses.length - 1 ? conversationData.feedback_comment : undefined
          })
        }
      }
    }

    const firstQuestion = messages.find(m => m.isUser)?.content || 'Conversation'
    const title = firstQuestion.length > 100 ? firstQuestion.substring(0, 100) + '...' : firstQuestion

    const lastResponse = messages.filter(m => !m.isUser).pop()?.content || 'Aucune réponse'
    const lastMessagePreview = lastResponse.length > 300 ? lastResponse.substring(0, 300) + '...' : lastResponse

    return {
      id: conversationData.conversation_id || conversationData.id,
      title: title,
      preview: firstQuestion,
      message_count: messages.length,
      created_at: conversationData.timestamp || new Date().toISOString(),
      updated_at: conversationData.updated_at || conversationData.timestamp || new Date().toISOString(),
      feedback: conversationData.feedback,
      language: conversationData.language || 'fr',
      last_message_preview: lastMessagePreview,
      status: 'active' as const,
      messages
    }
  }

  // Invalidation du cache après sauvegarde
  async saveConversation(data: ConversationData): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('Logging désactivé - conversation non sauvegardée:', data.conversation_id)
      return
    }

    try {
      console.log('Sauvegarde conversation:', data.conversation_id)
      console.log('URL de sauvegarde:', `${this.baseUrl}/conversation`)
      
      const response = await fetch(`${this.baseUrl}/conversation`, {
        method: 'POST',
        headers: this.getHeaders('POST'),
        body: JSON.stringify({
          user_id: data.user_id,
          question: data.question,
          response: data.response,
          full_text: data.full_text ?? undefined,
          conversation_id: data.conversation_id,
          confidence_score: data.confidence_score,
          response_time_ms: data.response_time_ms,
          language: data.language || 'fr',
          rag_used: data.rag_used !== undefined ? data.rag_used : true
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('Conversation sauvegardée:', result.message)
      
      // Invalidation du cache après sauvegarde
      this.invalidateCache()
      
    } catch (error) {
      console.error('Erreur sauvegarde conversation:', error)
    }
  }

  // Délégation vers apiService.ts
  async sendFeedback(conversationId: string, feedback: 1 | -1): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('Logging désactivé - feedback non envoyé:', conversationId)
      return
    }

    console.log('[ConversationService] Délégation feedback vers apiService...')
    await sendFeedback(conversationId, feedback)
    
    // Invalidation du cache après feedback
    this.invalidateCache()
  }

  async sendFeedbackComment(conversationId: string, comment: string): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('Logging désactivé - commentaire non envoyé:', conversationId)
      return
    }

    try {
      console.log('Envoi commentaire feedback:', conversationId, comment.substring(0, 50) + '...')
      console.log('URL commentaire:', `${this.baseUrl}/conversations/${conversationId}/comment`)
      
      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}/comment`, {
        method: 'PATCH',
        headers: this.getHeaders('PATCH'),
        body: JSON.stringify({ 
          comment: comment,
          timestamp: new Date().toISOString()
        })
      })
      
      if (!response.ok) {
        if (response.status === 404) {
          console.warn('Endpoint commentaire feedback pas encore implémenté sur le serveur')
          return
        }
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('Commentaire feedback enregistré:', result.message)
      
      // Invalidation du cache après commentaire
      this.invalidateCache()
      
    } catch (error) {
      console.error('Erreur envoi commentaire feedback:', error)
    }
  }

  async sendFeedbackWithComment(
    conversationId: string, 
    feedback: 1 | -1, 
    comment?: string
  ): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('Logging désactivé - feedback avec commentaire non envoyé:', conversationId)
      return
    }

    try {
      console.log('Envoi feedback avec commentaire:', conversationId, feedback, comment ? 'avec commentaire' : 'sans commentaire')
      console.log('URL feedback combiné:', `${this.baseUrl}/conversations/${conversationId}/feedback-with-comment`)
      
      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}/feedback-with-comment`, {
        method: 'PATCH',
        headers: this.getHeaders('PATCH'),
        body: JSON.stringify({ 
          feedback,
          comment: comment || null,
          timestamp: new Date().toISOString()
        })
      })
      
      if (!response.ok) {
        if (response.status === 404) {
          console.warn('Endpoint combiné non disponible, utilisation méthodes séparées')
          await this.sendFeedback(conversationId, feedback)
          if (comment) {
            await this.sendFeedbackComment(conversationId, comment)
          }
          return
        }
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('Feedback avec commentaire enregistré:', result.message)
      
      // Invalidation du cache après feedback combiné
      this.invalidateCache()
      
    } catch (error) {
      console.error('Erreur envoi feedback avec commentaire:', error)
      throw error
    }
  }

  // Invalidation du cache après suppression
  async deleteConversation(conversationId: string): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('Logging désactivé - conversation non supprimée:', conversationId)
      return
    }

    console.log('[ConversationService] Délégation suppression vers apiService...')
    await deleteConversation(conversationId)
    
    // Invalidation du cache après suppression
    this.invalidateCache()
  }

  async clearAllUserConversations(userId: string): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('Logging désactivé - conversations non supprimées:', userId)
      return
    }

    try {
      console.log('Suppression toutes conversations serveur pour:', userId)
      console.log('URL suppression globale:', `${this.baseUrl}/conversations/user/${userId}`)
      
      const response = await fetch(`${this.baseUrl}/conversations/user/${userId}`, {
        method: 'DELETE',
        headers: this.getHeaders('DELETE')
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('Toutes conversations supprimées du serveur:', result.message, 'Count:', result.deleted_count)
      
      // Invalidation du cache après suppression globale
      this.invalidateCache()
      
    } catch (error) {
      console.error('Erreur suppression toutes conversations serveur:', error)
      throw error
    }
  }

  async getFeedbackStats(userId?: string, days: number = 7): Promise<any> {
    if (!this.loggingEnabled) {
      console.log('Logging désactivé - stats feedback non récupérées')
      return null
    }

    try {
      const params = new URLSearchParams()
      if (userId) params.append('user_id', userId)
      params.append('days', days.toString())
      
      const url = `${this.baseUrl}/analytics/feedback?${params.toString()}`
      console.log('Récupération stats feedback:', url)
      
      const response = await fetch(url, {
        headers: this.getHeaders('GET')
      })
      
      if (!response.ok) {
        if (response.status === 404) {
          console.warn('Endpoint stats feedback pas encore implémenté')
          return null
        }
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      console.log('Stats feedback récupérées:', data)
      return data
      
    } catch (error) {
      console.error('Erreur récupération stats feedback:', error)
      return null
    }
  }

  async testConnection(): Promise<boolean> {
    try {
      console.log('Test connectivité service logging...')
      
      const response = await fetch(`${this.baseUrl}/test-comments`, {
        headers: this.getHeaders('GET')
      })
      
      if (response.ok) {
        const data = await response.json()
        console.log('Service logging opérationnel:', data.message)
        return true
      } else {
        console.warn('Service logging indisponible:', response.status)
        return false
      }
      
    } catch (error) {
      console.error('Erreur test connectivité:', error)
      return false
    }
  }

  resetCircuitBreaker(): void {
    this.circuitBreaker = new ConversationLoadingCircuitBreaker()
    console.log('[ConversationService] Circuit breaker resetté manuellement')
  }

  getCircuitBreakerStatus(): { attempts: number, canAttempt: boolean } {
    return {
      attempts: (this.circuitBreaker as any).attempts,
      canAttempt: this.circuitBreaker.canAttempt()
    }
  }

  // Gestion du cache
  
  /**
   * Invalidation manuelle du cache
   */
  invalidateCache(): void {
    this.conversationsCache = null
    console.log('[ConversationService] Cache invalidé manuellement')
  }

  /**
   * Forcer le rechargement en ignorant le cache
   */
  async forceReload(userId: string, limit = 50): Promise<Conversation[]> {
    console.log('[ConversationService] Rechargement forcé demandé')
    this.invalidateCache()
    return await this.getUserConversations(userId, limit)
  }

  /**
   * Status du cache pour debug
   */
  getCacheStatus(): { hasCache: boolean, cacheAge: number, cacheSize: number } {
    if (!this.conversationsCache) {
      return { hasCache: false, cacheAge: 0, cacheSize: 0 }
    }

    const cacheAge = Date.now() - this.conversationsCache.timestamp
    return {
      hasCache: true,
      cacheAge: cacheAge,
      cacheSize: this.conversationsCache.conversations.length
    }
  }
}

// Instance globale du service
export const conversationService = new ConversationService()