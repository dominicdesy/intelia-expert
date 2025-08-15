import { 
  Conversation, 
  ConversationWithMessages, 
  ConversationGroup,
  ConversationHistoryResponse,
  ConversationDetailResponse,
  ConversationGroupingOptions,
  Message,
  ConversationData
} from '../types'

// ✅ NOUVEAU : Circuit breaker pour éviter les boucles infinies
class ConversationLoadingCircuitBreaker {
  private attempts = 0
  private lastAttempt = 0
  private readonly MAX_ATTEMPTS = 3
  private readonly RESET_INTERVAL = 30000 // 30 secondes

  canAttempt(): boolean {
    const now = Date.now()
    
    // Reset après interval
    if (now - this.lastAttempt > this.RESET_INTERVAL) {
      this.attempts = 0
    }

    if (this.attempts >= this.MAX_ATTEMPTS) {
      console.warn('🚫 [ConversationService] Circuit breaker: trop de tentatives, arrêt temporaire')
      return false
    }

    return true
  }

  recordAttempt(): void {
    this.attempts++
    this.lastAttempt = Date.now()
    console.log(`🔄 [ConversationService] Circuit breaker: tentative ${this.attempts}/${this.MAX_ATTEMPTS}`)
  }

  recordSuccess(): void {
    this.attempts = 0
    console.log('✅ [ConversationService] Circuit breaker: reset après succès')
  }

  recordFailure(): void {
    console.log(`❌ [ConversationService] Circuit breaker: échec ${this.attempts}/${this.MAX_ATTEMPTS}`)
  }
}

// ==================== SERVICE CONVERSATIONS COMPLET AVEC FALLBACK LOCALSTORAGE + CIRCUIT BREAKER ====================
export class ConversationService {
  private baseUrl: string
  private loggingEnabled = true
  // ✅ NOUVEAU : Circuit breaker intégré
  private circuitBreaker = new ConversationLoadingCircuitBreaker()

  constructor() {
    // ✅ SÉCURISÉ: Configuration depuis variables d'environnement (INCHANGÉ)
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
    const apiVersion = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
    
    if (!apiBaseUrl) {
      console.error('❌ NEXT_PUBLIC_API_BASE_URL environment variable missing')
      this.loggingEnabled = false
      this.baseUrl = ''
      return
    }
    
    this.baseUrl = `${apiBaseUrl}/api/${apiVersion}`
    console.log('✅ ConversationService configuré:', this.baseUrl)
  }

  // ==================== NOUVELLES MÉTHODES POUR CONVERSATIONS (INCHANGÉES) ====================

  private getAuthToken(): string {
    try {
      // 1. Essayer le token depuis les cookies (comme dans apiService) - INCHANGÉ
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

      // 2. Fallback vers localStorage - INCHANGÉ
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

  /**
   * ✅ MÉTHODE CORRIGÉE - Récupère une conversation avec messages complets (INCHANGÉE)
   */
  async getConversationWithMessages(conversationId: string): Promise<ConversationWithMessages | null> {
    try {
      console.log('📖 [ConversationService] Chargement conversation complète:', conversationId)
      
      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}`, {
        method: 'GET',
        headers: { 
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        
        // ✅ CORRECTION: Accéder aux données dans data.conversation - INCHANGÉ
        console.log('✅ [ConversationService] Données récupérées:', {
          id: data.conversation?.conversation_id,
          questionLength: data.conversation?.question?.length || 0,
          responseLength: (data.conversation?.full_text ?? data.conversation?.response)?.length || 0
        })
        
        // ✅ CORRECTION: Passer data.conversation à la méthode transform - INCHANGÉ
        if (data.conversation && data.conversation.question && data.conversation.response) {
          const conversationWithMessages = this.transformToConversationWithMessages(data.conversation)
          
          if (conversationWithMessages.messages.length > 0) {
            console.log('✅ [ConversationService] Conversation transformée avec messages complets')
            return conversationWithMessages
          }
        }
      }
      
      console.warn('⚠️ [ConversationService] Impossible de récupérer la conversation complète')
      return null
      
    } catch (error) {
      console.error('❌ [ConversationService] Erreur getConversationWithMessages:', error)
      return null
    }
  }

  /**
   * Récupère l'historique des conversations groupées par date (INCHANGÉE)
   */
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
      console.log('📂 [ConversationService] Chargement historique pour:', userId)
      
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
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.getAuthToken()}`
          }
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to load conversation history`)
      }

      const data = await response.json()
      console.log('✅ [ConversationService] Historique chargé:', data.total_count, 'conversations')
      
      return data
      
    } catch (error) {
      console.error('❌ [ConversationService] Erreur chargement historique:', error)
      throw error
    }
  }

  /**
   * Récupère une conversation complète avec tous ses messages (INCHANGÉE)
   */
  async getConversationDetail(conversationId: string): Promise<ConversationDetailResponse> {
    try {
      console.log('📖 [ConversationService] Chargement conversation:', conversationId)
      
      const response = await fetch(
        `${this.baseUrl}/v1/conversations/${conversationId}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.getAuthToken()}`
          }
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to load conversation`)
      }

      const data = await response.json()
      console.log('✅ [ConversationService] Conversation chargée:', data.conversation.message_count, 'messages')
      
      return data
      
    } catch (error) {
      console.error('❌ [ConversationService] Erreur chargement conversation:', error)
      throw error
    }
  }

  /**
   * Groupe les conversations par date (utilitaire côté client) (INCHANGÉE)
   */
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

    // Filtrer les groupes vides
    return groups.filter(group => group.conversations.length > 0)
  }

  /**
   * 🔧 MÉTHODE CORRIGÉE AVEC FALLBACK LOCALSTORAGE + CIRCUIT BREAKER
   */
  async getUserConversations(userId: string, limit = 50): Promise<Conversation[]> {
    // ✅ NOUVEAU : Vérification circuit breaker
    if (!this.circuitBreaker.canAttempt()) {
      console.warn('🚫 [ConversationService] Circuit breaker actif - tentatives bloquées temporairement')
      return []
    }

    if (!this.loggingEnabled) {
      console.log('📝 Logging désactivé - conversations non récupérées')
      return []
    }

    console.log('📂 [ConversationService] Récupération conversations pour:', userId)

    // ✅ NOUVEAU : Enregistrer la tentative
    this.circuitBreaker.recordAttempt()

    // 1️⃣ ESSAYER L'ENDPOINT BACKEND D'ABORD
    try {
      console.log('🔍 Test endpoint backend principal...')
      
      const response = await fetch(`${this.baseUrl}/conversations/user/${userId}?limit=${limit}`, {
        method: 'GET',
        headers: { 
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        }
      })
      
      console.log(`📊 Backend endpoint: ${response.status} ${response.statusText}`)
      
      if (response.ok) {
        const data = await response.json()
        console.log(`✅ Backend data:`, data)
        
        // Adapter selon la structure de réponse - INCHANGÉ
        let conversations = []
        
        if (Array.isArray(data)) {
          conversations = data
        } else if (data.conversations && Array.isArray(data.conversations)) {
          conversations = data.conversations
        } else if (data.data && Array.isArray(data.data)) {
          conversations = data.data
        }
        
        if (conversations.length > 0) {
          console.log(`✅ ${conversations.length} conversations backend récupérées`)
          
          // Transformer en format Conversation[] - INCHANGÉ
          const formattedConversations = conversations.map((conv: any) => {
            const firstQuestion = conv.question?.split('\n--- Question suivante ---\n')?.[0] || conv.question || 'Conversation sans titre'
            const title = firstQuestion.length > 100 ? firstQuestion.substring(0, 100) + '...' : firstQuestion
            
            const responses = conv.response?.split('\n--- Réponse suivante ---\n') || [conv.response]
            const lastResponse = responses[responses.length - 1] || 'Aucune réponse'
            const lastMessagePreview = lastResponse.length > 300 ? lastResponse.substring(0, 300) + '...' : lastResponse

            return {
              id: conv.conversation_id || conv.id || conv.session_id,
              title: title,
              preview: firstQuestion,
              message_count: conv.message_count || 2,
              created_at: conv.timestamp || conv.created_at || new Date().toISOString(),
              updated_at: conv.updated_at || conv.timestamp || new Date().toISOString(),
              feedback: conv.feedback,
              language: conv.language || 'fr',
              last_message_preview: lastMessagePreview,
              status: 'active'
            }
          })
          
          // ✅ NOUVEAU : Enregistrer le succès et retourner immédiatement
          this.circuitBreaker.recordSuccess()
          return formattedConversations
        } else {
          console.log('⚠️ Backend retourne 0 conversations, essai fallback localStorage...')
          // ✅ CORRECTION CRITIQUE : RETOURNER le fallback, ne pas continuer
          const fallbackResult = await this.getConversationsFromLocalStorage(limit)
          if (fallbackResult.length > 0) {
            this.circuitBreaker.recordSuccess()
          } else {
            this.circuitBreaker.recordFailure()
          }
          return fallbackResult
        }
      } else {
        console.log(`❌ Backend endpoint failed: ${response.status}, essai fallback localStorage...`)
        // ✅ CORRECTION CRITIQUE : RETOURNER le fallback, ne pas continuer
        const fallbackResult = await this.getConversationsFromLocalStorage(limit)
        if (fallbackResult.length > 0) {
          this.circuitBreaker.recordSuccess()
        } else {
          this.circuitBreaker.recordFailure()
        }
        return fallbackResult
      }
    } catch (error) {
      console.log(`❌ Backend endpoint error: ${error.message}, essai fallback localStorage...`)
      
      // ✅ CORRECTION CRITIQUE : RETOURNER le fallback, ne pas continuer
      try {
        const fallbackResult = await this.getConversationsFromLocalStorage(limit)
        if (fallbackResult.length > 0) {
          this.circuitBreaker.recordSuccess()
        } else {
          this.circuitBreaker.recordFailure()
        }
        return fallbackResult
      } catch (fallbackError) {
        console.error('❌ Erreur fallback localStorage:', fallbackError)
        this.circuitBreaker.recordFailure()
        return []
      }
    }

    // ❌ ANCIEN CODE PROBLÉMATIQUE SUPPRIMÉ
    // Plus de fallback automatique ici qui causait la boucle !
  }

  /**
   * 🚀 NOUVELLE MÉTHODE: Récupération depuis localStorage comme fallback (INCHANGÉE)
   */
  async getConversationsFromLocalStorage(limit: number): Promise<Conversation[]> {
    try {
      const recentSessionIds = this.getRecentSessionIds()
      
      if (recentSessionIds.length === 0) {
        console.log('⚠️ Aucune session localStorage trouvée')
        return []
      }
      
      console.log(`🔍 ${recentSessionIds.length} sessions localStorage trouvées`)
      
      const conversations: Conversation[] = []
      
      // Récupérer les détails de chaque session - INCHANGÉ
      for (const sessionId of recentSessionIds.slice(0, limit)) {
        try {
          console.log(`🔍 Récupération session: ${sessionId}`)
          
          // Utiliser l'endpoint qui fonctionne selon le diagnostic
          const response = await fetch(`${this.baseUrl}/conversations/${sessionId}`, {
            method: 'GET',
            headers: { 
              'Accept': 'application/json',
              'Authorization': `Bearer ${this.getAuthToken()}`
            }
          })
          
          if (response.ok) {
            const data = await response.json()
            
            if (data.session_id) {
              // Transformer en conversation
              const conversation: Conversation = {
                id: data.session_id,
                title: this.extractTitleFromConversation(data),
                preview: this.extractPreviewFromConversation(data),
                message_count: this.extractMessageCount(data),
                created_at: data.timestamp || new Date().toISOString(),
                updated_at: data.updated_at || data.timestamp || new Date().toISOString(),
                feedback: data.feedback,
                language: data.language || 'fr',
                last_message_preview: this.extractLastMessagePreview(data),
                status: 'active' as const
              }
              
              conversations.push(conversation)
              console.log(`✅ Session ${sessionId} transformée`)
            } else {
              console.log(`⚠️ Session ${sessionId} - pas de session_id`)
            }
          } else {
            console.log(`❌ Session ${sessionId} - status ${response.status}`)
          }
        } catch (error) {
          console.log(`❌ Erreur récupération session ${sessionId}:`, error)
        }
      }
      
      console.log(`✅ ${conversations.length} conversations récupérées via localStorage fallback`)
      
      // Trier par date (plus récentes en premier)
      conversations.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      
      return conversations
      
    } catch (error) {
      console.error('❌ Erreur fallback localStorage:', error)
      return []
    }
  }

  /**
   * 🔧 MÉTHODES UTILITAIRES POUR EXTRACTION DE DONNÉES (INCHANGÉES)
   */
  private extractTitleFromConversation(data: any): string {
    // Essayer d'extraire le titre depuis différentes sources
    if (data.question && typeof data.question === 'string') {
      const title = data.question.substring(0, 100)
      return title.length === 100 ? title + '...' : title
    }
    
    // Si c'est dans le contexte
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
    // Même logique que le titre mais pour l'aperçu
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
    // Compter les messages depuis le contexte
    if (data.context?.messages?.length > 0) {
      return data.context.messages.length
    }
    
    // Estimation basée sur question/réponse
    let count = 0
    if (data.question) count++
    if (data.response) count++
    
    return count || 2 // Minimum estimé
  }

  private extractLastMessagePreview(data: any): string {
    // Dernière réponse comme aperçu
    if (data.response && typeof data.response === 'string') {
      const preview = data.response.substring(0, 300)
      return preview.length === 300 ? preview + '...' : preview
    }
    
    // Si dans le contexte
    if (data.context?.messages?.length > 0) {
      const lastAssistantMessage = [...data.context.messages].reverse().find((m: any) => !m.isUser)
      if (lastAssistantMessage?.content) {
        const preview = lastAssistantMessage.content.substring(0, 300)
        return preview.length === 300 ? preview + '...' : preview
      }
    }
    
    return 'Aucune réponse disponible'
  }

  /**
   * 🔧 UTILITAIRE - Récupère les session IDs récents depuis le localStorage (INCHANGÉ)
   */
  private getRecentSessionIds(): string[] {
    try {
      const stored = localStorage.getItem('recent_conversation_sessions')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed)) {
          return parsed.slice(0, 20) // Max 20 sessions récentes
        }
      }
    } catch (error) {
      console.warn('⚠️ Erreur lecture sessions récentes:', error)
    }
    
    return []
  }

  /**
   * 🔧 UTILITAIRE - Stocke un session ID pour la récupération future (INCHANGÉ)
   * À appeler depuis apiService après création d'une conversation
   */
  storeRecentSessionId(sessionId: string): void {
    try {
      const existing = this.getRecentSessionIds()
      const updated = [sessionId, ...existing.filter(id => id !== sessionId)].slice(0, 50)
      localStorage.setItem('recent_conversation_sessions', JSON.stringify(updated))
      console.log('🔍 Session ID stocké pour historique:', sessionId.substring(0, 8) + '...')
    } catch (error) {
      console.warn('⚠️ Erreur stockage session ID:', error)
    }
  }

  // 🔧 NOUVELLE MÉTHODE - Test tous les endpoints pour trouver le bon (INCHANGÉE)
  async discoverWorkingEndpoints(): Promise<string[]> {
    console.log('🔍 === DÉCOUVERTE DES ENDPOINTS FONCTIONNELS ===')
    
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
          headers: { 
            'Accept': 'application/json',
            'Authorization': `Bearer ${this.getAuthToken()}`
          }
        })
        
        console.log(`📡 ${endpoint}: ${response.status} ${response.statusText}`)
        
        if (response.ok) {
          const data = await response.json()
          console.log(`✅ ENDPOINT FONCTIONNEL: ${endpoint}`)
          console.log(`📊 Structure:`, Array.isArray(data) ? `Array[${data.length}]` : Object.keys(data))
          workingEndpoints.push(endpoint)
        }
      } catch (error) {
        console.log(`❌ ${endpoint}: ${error.message}`)
      }
    }
    
    console.log('✅ Endpoints fonctionnels découverts:', workingEndpoints)
    return workingEndpoints
  }

  /**
   * Transforme une conversation en ConversationWithMessages - AVEC PARSING DES MESSAGES MULTIPLES (INCHANGÉE)
   */
  transformToConversationWithMessages(conversationData: any): ConversationWithMessages {
    const messages: Message[] = []
    
    if (conversationData.question && conversationData.response) {
      // ✅ NOUVEAU: Parser les questions et réponses multiples
      const questions = conversationData.question.split('\n--- Question suivante ---\n')
      const responses = (conversationData.full_text ?? conversationData.response).split('\n--- Réponse suivante ---\n')
      
      // Créer des messages alternés (question/réponse)
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

    // Premier message pour le titre
    const firstQuestion = messages.find(m => m.isUser)?.content || 'Conversation'
    const title = firstQuestion.length > 100 ? firstQuestion.substring(0, 100) + '...' : firstQuestion

    // Dernière réponse pour l'aperçu
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

  // ==================== MÉTHODES EXISTANTES CONSERVÉES (TOUTES INCHANGÉES) ====================

  async saveConversation(data: ConversationData): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('📝 Logging désactivé - conversation non sauvegardée:', data.conversation_id)
      return
    }

    try {
      console.log('💾 Sauvegarde conversation:', data.conversation_id)
      console.log('📡 URL de sauvegarde:', `${this.baseUrl}/conversation`)
      
      const response = await fetch(`${this.baseUrl}/conversation`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        },
        body: JSON.stringify({
          user_id: data.user_id,
          question: data.question,
          response: data.response,
          // ✅ plein texte non tronqué si disponible
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
      console.log('✅ Conversation sauvegardée:', result.message)
      
    } catch (error) {
      console.error('❌ Erreur sauvegarde conversation:', error)
    }
  }

  async sendFeedback(conversationId: string, feedback: 1 | -1): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('📊 Logging désactivé - feedback non envoyé:', conversationId)
      return
    }

    try {
      console.log('📊 Envoi feedback:', conversationId, feedback)
      console.log('📡 URL feedback:', `${this.baseUrl}/conversations/${conversationId}/feedback`)
      
      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}/feedback`, {
        method: 'PATCH',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        },
        body: JSON.stringify({ feedback })
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('✅ Feedback enregistré:', result.message)
      
    } catch (error) {
      console.error('❌ Erreur envoi feedback:', error)
      throw error
    }
  }

  async sendFeedbackComment(conversationId: string, comment: string): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('💬 Logging désactivé - commentaire non envoyé:', conversationId)
      return
    }

    try {
      console.log('💬 Envoi commentaire feedback:', conversationId, comment.substring(0, 50) + '...')
      console.log('📡 URL commentaire:', `${this.baseUrl}/conversations/${conversationId}/comment`)
      
      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}/comment`, {
        method: 'PATCH',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        },
        body: JSON.stringify({ 
          comment: comment,
          timestamp: new Date().toISOString()
        })
      })
      
      if (!response.ok) {
        if (response.status === 404) {
          console.warn('⚠️ Endpoint commentaire feedback pas encore implémenté sur le serveur')
          return
        }
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('✅ Commentaire feedback enregistré:', result.message)
      
    } catch (error) {
      console.error('❌ Erreur envoi commentaire feedback:', error)
    }
  }

  async sendFeedbackWithComment(
    conversationId: string, 
    feedback: 1 | -1, 
    comment?: string
  ): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('📊💬 Logging désactivé - feedback avec commentaire non envoyé:', conversationId)
      return
    }

    try {
      console.log('📊💬 Envoi feedback avec commentaire:', conversationId, feedback, comment ? 'avec commentaire' : 'sans commentaire')
      console.log('📡 URL feedback combiné:', `${this.baseUrl}/conversations/${conversationId}/feedback-with-comment`)
      
      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}/feedback-with-comment`, {
        method: 'PATCH',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        },
        body: JSON.stringify({ 
          feedback,
          comment: comment || null,
          timestamp: new Date().toISOString()
        })
      })
      
      if (!response.ok) {
        if (response.status === 404) {
          console.warn('⚠️ Endpoint combiné non disponible, utilisation méthodes séparées')
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
      console.log('✅ Feedback avec commentaire enregistré:', result.message)
      
    } catch (error) {
      console.error('❌ Erreur envoi feedback avec commentaire:', error)
      throw error
    }
  }

  async deleteConversation(conversationId: string): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('🗑️ Logging désactivé - conversation non supprimée:', conversationId)
      return
    }

    try {
      console.log('🗑️ Suppression conversation serveur:', conversationId)
      console.log('📡 URL suppression:', `${this.baseUrl}/conversations/${conversationId}`)
      
      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: { 
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        }
      })
      
      if (!response.ok) {
        if (response.status === 404) {
          console.warn('⚠️ Endpoint de suppression non disponible sur le serveur')
          return
        }
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('✅ Conversation supprimée du serveur:', result.message)
      
    } catch (error) {
      console.error('❌ Erreur suppression conversation serveur:', error)
      throw error
    }
  }

  async clearAllUserConversations(userId: string): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('🗑️ Logging désactivé - conversations non supprimées:', userId)
      return
    }

    try {
      console.log('🗑️ Suppression toutes conversations serveur pour:', userId)
      console.log('📡 URL suppression globale:', `${this.baseUrl}/conversations/user/${userId}`)
      
      const response = await fetch(`${this.baseUrl}/conversations/user/${userId}`, {
        method: 'DELETE',
        headers: { 
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        }
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('✅ Toutes conversations supprimées du serveur:', result.message, 'Count:', result.deleted_count)
      
    } catch (error) {
      console.error('❌ Erreur suppression toutes conversations serveur:', error)
      throw error
    }
  }

  async getFeedbackStats(userId?: string, days: number = 7): Promise<any> {
    if (!this.loggingEnabled) {
      console.log('📊 Logging désactivé - stats feedback non récupérées')
      return null
    }

    try {
      const params = new URLSearchParams()
      if (userId) params.append('user_id', userId)
      params.append('days', days.toString())
      
      const url = `${this.baseUrl}/analytics/feedback?${params.toString()}`
      console.log('📊 Récupération stats feedback:', url)
      
      const response = await fetch(url, {
        headers: { 
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        }
      })
      
      if (!response.ok) {
        if (response.status === 404) {
          console.warn('⚠️ Endpoint stats feedback pas encore implémenté')
          return null
        }
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      console.log('✅ Stats feedback récupérées:', data)
      return data
      
    } catch (error) {
      console.error('❌ Erreur récupération stats feedback:', error)
      return null
    }
  }

  async testConnection(): Promise<boolean> {
    try {
      console.log('🔌 Test connectivité service logging...')
      
      const response = await fetch(`${this.baseUrl}/test-comments`, {
        headers: { 
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        console.log('✅ Service logging opérationnel:', data.message)
        return true
      } else {
        console.warn('⚠️ Service logging indisponible:', response.status)
        return false
      }
      
    } catch (error) {
      console.error('❌ Erreur test connectivité:', error)
      return false
    }
  }

  // ✅ NOUVEAU : Méthodes utilitaires pour le circuit breaker
  resetCircuitBreaker(): void {
    this.circuitBreaker = new ConversationLoadingCircuitBreaker()
    console.log('🔄 [ConversationService] Circuit breaker resetté manuellement')
  }

  getCircuitBreakerStatus(): { attempts: number, canAttempt: boolean } {
    return {
      attempts: (this.circuitBreaker as any).attempts,
      canAttempt: this.circuitBreaker.canAttempt()
    }
  }
}

// Instance globale du service
export const conversationService = new ConversationService()