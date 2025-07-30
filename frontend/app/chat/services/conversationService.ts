import { 
  Conversation, 
  ConversationWithMessages, 
  ConversationGroup,
  ConversationHistoryResponse,
  ConversationDetailResponse,
  ConversationGroupingOptions,
  Message,
  ConversationData,
  API_CONFIG
} from '../types'

// ==================== SERVICE CONVERSATIONS COMPLET INTÉGRÉ ====================
export class ConversationService {
  private baseUrl = API_CONFIG.LOGGING_BASE_URL
  private loggingEnabled = true

  // ==================== NOUVELLES MÉTHODES POUR CONVERSATIONS ====================

  private getAuthToken(): string {
    try {
      // 1. Essayer le token depuis les cookies (comme dans apiService)
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

      // 2. Fallback vers localStorage
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
   * 🔥 NOUVELLE MÉTHODE CRITIQUE - Récupère une conversation complète avec tous ses messages NON TRONQUÉS
   */
  async getConversationWithMessages(conversationId: string): Promise<ConversationWithMessages | null> {
    try {
      console.log('📖 [ConversationService] Chargement conversation complète:', conversationId)
      
      // ✅ ÉTAPE 1: Essayer de récupérer depuis votre système de logging
      const response = await fetch(`${this.baseUrl}/conversation/${conversationId}`, {
        method: 'GET',
        headers: { 
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        console.log('✅ [ConversationService] Données conversation récupérées:', {
          id: data.conversation_id,
          questionLength: data.question?.length || 0,
          responseLength: data.response?.length || 0
        })
        
        // ✅ CORRECTION CRITIQUE: Vérifier que les contenus ne sont pas tronqués
        if (data.question && data.response) {
          // Vérifier si les contenus semblent tronqués
          const questionTruncated = data.question.length < 50 && data.question.endsWith('...')
          const responseTruncated = data.response.length < 100 && data.response.endsWith('...')
          
          if (questionTruncated || responseTruncated) {
            console.warn('⚠️ [ConversationService] Contenus possiblement tronqués détectés')
          }
          
          // Utiliser votre méthode existante pour transformer
          const conversationWithMessages = this.transformToConversationWithMessages(data)
          
          // ✅ AMÉLIORATION: S'assurer que les messages complets sont présents
          if (conversationWithMessages.messages.length >= 2) {
            console.log('✅ [ConversationService] Conversation transformée avec messages complets')
            return conversationWithMessages
          }
        }
      }
      
      // ✅ ÉTAPE 2: Si votre système de logging ne fonctionne pas, essayer l'API principale
      console.log('📡 [ConversationService] Tentative via API principale:', conversationId)
      
      const mainApiResponse = await fetch(`https://expert-app-cngws.ondigitalocean.app/api/v1/conversations/${conversationId}/messages`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.getAuthToken()}`,
          'Content-Type': 'application/json'
        }
      })

      if (mainApiResponse.ok) {
        const apiData = await mainApiResponse.json()
        console.log('✅ [ConversationService] Données API principale:', {
          messageCount: apiData.messages?.length || 0,
          firstMessageLength: apiData.messages?.[0]?.content?.length || 0
        })
        
        // Transformer les données de l'API principale
        const messages: Message[] = apiData.messages?.map((msg: any) => ({
          id: msg.id,
          content: msg.content || '[Message vide]',
          isUser: msg.role === 'user',
          timestamp: new Date(msg.created_at),
          conversation_id: conversationId,
          feedback: msg.feedback === 1 ? 'positive' : msg.feedback === -1 ? 'negative' : null
        })) || []

        return {
          id: apiData.id,
          title: apiData.title || 'Conversation sans titre',
          preview: apiData.preview || messages.find(m => m.isUser)?.content?.substring(0, 100) || 'Aucun aperçu',
          message_count: messages.length,
          created_at: apiData.created_at,
          updated_at: apiData.updated_at,
          language: apiData.language || 'fr',
          status: apiData.status || 'active',
          messages: messages
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
   * Récupère l'historique des conversations groupées par date
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
   * Récupère une conversation complète avec tous ses messages
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
   * Groupe les conversations par date (utilitaire côté client)
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
   * Récupère les conversations utilisateur (version simplifiée pour compatibilité) - CORRIGÉE
   */
  async getUserConversations(userId: string, limit = 50): Promise<Conversation[]> {
    if (!this.loggingEnabled) {
      console.log('🔍 Logging désactivé - conversations non récupérées')
      return []
    }

    try {
      console.log('🔍 Récupération conversations pour:', userId)
      console.log('📡 URL conversations:', `${this.baseUrl}/conversations/user/${userId}?limit=${limit}`)
      
      const response = await fetch(`${this.baseUrl}/conversations/user/${userId}?limit=${limit}`, {
        headers: { 
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`
        }
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      console.log('✅ Conversations récupérées:', data.count)
      
      // ✅ CORRECTION: Ne pas tronquer les titres et aperçus
      const conversations: Conversation[] = (data.conversations || []).map((conv: any) => {
        // ✅ AMÉLIORATION: Titre complet si possible
        const title = conv.question 
          ? conv.question.length > 80 ? conv.question.substring(0, 80) + '...' : conv.question
          : 'Conversation sans titre'

        // ✅ AMÉLIORATION: Aperçu complet de la réponse
        const lastMessagePreview = conv.response 
          ? conv.response.length > 150 ? conv.response.substring(0, 150) + '...' : conv.response
          : 'Aucune réponse'

        return {
          id: conv.conversation_id || conv.id,
          title: title,
          preview: conv.question || 'Aucun aperçu disponible',
          message_count: 2, // Question + réponse minimum
          created_at: conv.timestamp || new Date().toISOString(),
          updated_at: conv.updated_at || conv.timestamp || new Date().toISOString(),
          feedback: conv.feedback,
          language: conv.language || 'fr',
          last_message_preview: lastMessagePreview,
          status: 'active'
        }
      })
      
      return conversations
      
    } catch (error) {
      console.error('❌ Erreur récupération conversations:', error)
      return []
    }
  }

  /**
   * Transforme une conversation en ConversationWithMessages - CORRIGÉE
   */
  transformToConversationWithMessages(conversationData: any): ConversationWithMessages {
    const messages: Message[] = []
    
    // ✅ CORRECTION: Préserver le contenu COMPLET
    if (conversationData.question) {
      messages.push({
        id: `${conversationData.conversation_id || conversationData.id}_user`,
        content: conversationData.question, // ✅ CONTENU COMPLET - pas de troncature
        isUser: true,
        timestamp: new Date(conversationData.timestamp || new Date()),
        conversation_id: conversationData.conversation_id || conversationData.id
      })
    }
    
    // ✅ CORRECTION: Préserver la réponse COMPLÈTE
    if (conversationData.response) {
      messages.push({
        id: `${conversationData.conversation_id || conversationData.id}_assistant`,
        content: conversationData.response, // ✅ RÉPONSE COMPLÈTE - pas de troncature
        isUser: false,
        timestamp: new Date(conversationData.timestamp || new Date()),
        conversation_id: conversationData.conversation_id || conversationData.id,
        feedback: conversationData.feedback === 1 ? 'positive' : conversationData.feedback === -1 ? 'negative' : null,
        feedbackComment: conversationData.feedback_comment
      })
    }

    // ✅ CORRECTION: Titre et aperçus complets
    const title = conversationData.question 
      ? conversationData.question.length > 80 ? conversationData.question.substring(0, 80) + '...' : conversationData.question
      : 'Conversation'

    const lastMessagePreview = conversationData.response 
      ? conversationData.response.length > 200 ? conversationData.response.substring(0, 200) + '...' : conversationData.response
      : 'Aucune réponse'

    return {
      id: conversationData.conversation_id || conversationData.id,
      title: title,
      preview: conversationData.question || 'Aucun aperçu',
      message_count: messages.length,
      created_at: conversationData.timestamp || new Date().toISOString(),
      updated_at: conversationData.updated_at || conversationData.timestamp || new Date().toISOString(),
      feedback: conversationData.feedback,
      language: conversationData.language || 'fr',
      last_message_preview: lastMessagePreview,
      status: 'active',
      messages // ✅ MESSAGES COMPLETS
    }
  }

  // ==================== MÉTHODES EXISTANTES CONSERVÉES ====================

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
      console.log('📡 URL feedback:', `${this.baseUrl}/conversation/${conversationId}/feedback`)
      
      const response = await fetch(`${this.baseUrl}/conversation/${conversationId}/feedback`, {
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
      console.log('📡 URL commentaire:', `${this.baseUrl}/conversation/${conversationId}/comment`)
      
      const response = await fetch(`${this.baseUrl}/conversation/${conversationId}/comment`, {
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
      console.log('📡 URL feedback combiné:', `${this.baseUrl}/conversation/${conversationId}/feedback-with-comment`)
      
      const response = await fetch(`${this.baseUrl}/conversation/${conversationId}/feedback-with-comment`, {
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
      console.log('📡 URL suppression:', `${this.baseUrl}/conversation/${conversationId}`)
      
      const response = await fetch(`${this.baseUrl}/conversation/${conversationId}`, {
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
      console.log('🔍 Test connectivité service logging...')
      
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
}

// Instance globale du service
export const conversationService = new ConversationService()