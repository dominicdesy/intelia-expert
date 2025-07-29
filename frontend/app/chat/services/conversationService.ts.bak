import { ConversationData, API_CONFIG } from '../types'

// ==================== SERVICE DE LOGGING AVEC URL CORRIGÉE ====================
export class ConversationService {
  private baseUrl = API_CONFIG.LOGGING_BASE_URL
  private loggingEnabled = true

  async saveConversation(data: ConversationData): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('📝 Logging désactivé - conversation non sauvegardée:', data.conversation_id)
      return
    }

    try {
      console.log('💾 Sauvegarde conversation:', data.conversation_id)
      console.log('📡 URL de sauvegarde:', `${this.baseUrl}/logging/conversation`)
      
      const response = await fetch(`${this.baseUrl}/logging/conversation`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
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
      // Ne pas bloquer l'UX si le logging échoue
    }
  }

  async sendFeedback(conversationId: string, feedback: 1 | -1): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('📊 Logging désactivé - feedback non envoyé:', conversationId)
      return
    }

    try {
      console.log('📊 Envoi feedback:', conversationId, feedback)
      console.log('📡 URL feedback:', `${this.baseUrl}/logging/conversation/${conversationId}/feedback`)
      
      const response = await fetch(`${this.baseUrl}/logging/conversation/${conversationId}/feedback`, {
        method: 'PATCH',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
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
      throw error  // Propager pour afficher erreur à l'utilisateur
    }
  }

  async getUserConversations(userId: string, limit = 50): Promise<any[]> {
    if (!this.loggingEnabled) {
      console.log('🔍 Logging désactivé - conversations non récupérées')
      return []
    }

    try {
      console.log('🔍 Récupération conversations pour:', userId)
      console.log('📡 URL conversations:', `${this.baseUrl}/logging/user/${userId}/conversations?limit=${limit}`)
      
      const response = await fetch(`${this.baseUrl}/logging/user/${userId}/conversations?limit=${limit}`, {
        headers: { 'Accept': 'application/json' }
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      console.log('✅ Conversations récupérées:', data.count)
      return data.conversations || []
      
    } catch (error) {
      console.error('❌ Erreur récupération conversations:', error)
      return []
    }
  }

  async deleteConversation(conversationId: string): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('🗑️ Logging désactivé - conversation non supprimée:', conversationId)
      return
    }

    try {
      console.log('🗑️ Suppression conversation serveur:', conversationId)
      console.log('📡 URL suppression:', `${this.baseUrl}/logging/conversation/${conversationId}`)
      
      const response = await fetch(`${this.baseUrl}/logging/conversation/${conversationId}`, {
        method: 'DELETE',
        headers: { 
          'Accept': 'application/json'
        }
      })
      
      if (!response.ok) {
        // Si l'endpoint n'existe pas (404), on continue sans erreur
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
      throw error  // Propager pour que l'UI puisse gérer l'erreur
    }
  }

  async clearAllUserConversations(userId: string): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('🗑️ Logging désactivé - conversations non supprimées:', userId)
      return
    }

    try {
      console.log('🗑️ Suppression toutes conversations serveur pour:', userId)
      console.log('📡 URL suppression globale:', `${this.baseUrl}/logging/user/${userId}/conversations`)
      
      const response = await fetch(`${this.baseUrl}/logging/user/${userId}/conversations`, {
        method: 'DELETE',
        headers: { 
          'Accept': 'application/json'
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
      throw error  // Propager pour que l'UI puisse gérer l'erreur
    }
  }
}

// Instance globale du service
export const conversationService = new ConversationService()