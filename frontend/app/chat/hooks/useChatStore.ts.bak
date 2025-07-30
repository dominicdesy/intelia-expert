import { useState } from 'react'
import { ConversationItem, ChatStore } from '../types'
import { conversationService } from '../services/conversationService'

// ==================== HOOK CHAT AVEC LOGGING AMÉLIORÉ ====================
export const useChatStore = (): ChatStore => {
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const loadConversations = async (userId: string): Promise<void> => {
    if (!userId) {
      console.warn('⚠️ [useChatStore] Pas d\'userId fourni pour charger les conversations')
      return
    }

    setIsLoading(true)
    try {
      console.log('🔄 [useChatStore] Chargement conversations pour userId:', userId)
      const userConversations = await conversationService.getUserConversations(userId, 100) // Augmenter la limite
      
      console.log('📊 [useChatStore] Conversations brutes reçues:', userConversations.length, userConversations)
      
      if (!userConversations || userConversations.length === 0) {
        console.log('📭 [useChatStore] Aucune conversation trouvée')
        setConversations([])
        return
      }
      
      const formattedConversations: ConversationItem[] = userConversations.map(conv => {
        const title = conv.question && conv.question.length > 0 
          ? (conv.question.length > 50 ? conv.question.substring(0, 50) + '...' : conv.question)
          : 'Conversation sans titre'
          
        return {
          id: conv.conversation_id || conv.id || Date.now().toString(),
          title: title,
          messages: [
            { id: `${conv.conversation_id}-q`, role: 'user', content: conv.question || 'Question non disponible' },
            { id: `${conv.conversation_id}-a`, role: 'assistant', content: conv.response || 'Réponse non disponible' }
          ],
          updated_at: conv.updated_at || conv.timestamp || new Date().toISOString(),
          created_at: conv.timestamp || conv.created_at || new Date().toISOString(),
          feedback: conv.feedback || null
        }
      })
      
      // Trier par date de mise à jour (plus récent en premier)
      const sortedConversations = formattedConversations.sort((a, b) => 
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      
      setConversations(sortedConversations)
      console.log('✅ [useChatStore] Conversations formatées et triées:', sortedConversations.length)
      
    } catch (error) {
      console.error('❌ [useChatStore] Erreur chargement conversations:', error)
      setConversations([])
    } finally {
      setIsLoading(false)
    }
  }

  const deleteConversation = async (id: string): Promise<void> => {
    try {
      console.log('🗑️ [useChatStore] Suppression conversation:', id)
      
      // 1. Mise à jour optimiste de l'UI (suppression immédiate)
      setConversations(prev => prev.filter(conv => conv.id !== id))
      
      // 2. Suppression côté serveur
      await conversationService.deleteConversation(id)
      
      console.log('✅ [useChatStore] Conversation supprimée du serveur:', id)
      
    } catch (error) {
      console.error('❌ [useChatStore] Erreur suppression conversation serveur:', error)
      
      // En cas d'erreur serveur, on pourrait remettre la conversation dans la liste
      // mais pour l'instant on garde la suppression locale même si le serveur échoue
      // pour éviter de confuser l'utilisateur
      
      // Optionnel: alerter l'utilisateur
      // alert('Erreur lors de la suppression sur le serveur, mais conversation supprimée localement')
    }
  }

  const clearAllConversations = async (userId?: string): Promise<void> => {
    try {
      console.log('🗑️ [useChatStore] Suppression toutes conversations')
      
      // 1. Mise à jour optimiste de l'UI (suppression immédiate)
      setConversations([])
      
      // 2. Suppression côté serveur si userId disponible
      if (userId) {
        await conversationService.clearAllUserConversations(userId)
        console.log('✅ [useChatStore] Toutes conversations supprimées du serveur')
      } else {
        console.warn('⚠️ [useChatStore] Pas d\'userId pour suppression serveur')
      }
      
    } catch (error) {
      console.error('❌ [useChatStore] Erreur suppression conversations serveur:', error)
      // Même principe: on garde la suppression locale
    }
  }

  // Fonction pour forcer le rechargement
  const refreshConversations = async (userId: string): Promise<void> => {
    console.log('🔄 [useChatStore] Rechargement forcé des conversations')
    await loadConversations(userId)
  }

  // ✅ CORRECTION: Fonction pour ajouter une nouvelle conversation à la liste locale
  const addConversation = (conversationId: string, question: string, response: string): void => {
    const newConversation: ConversationItem = {
      id: conversationId,
      title: question.length > 50 ? question.substring(0, 50) + '...' : question,
      messages: [
        { id: `${conversationId}-q`, role: 'user', content: question },
        { id: `${conversationId}-a`, role: 'assistant', content: response }
      ],
      updated_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      feedback: null
    }
    
    // Ajouter en première position (plus récent)
    setConversations(prev => [newConversation, ...prev])
    console.log('✅ [useChatStore] Nouvelle conversation ajoutée localement:', conversationId)
  }

  return {
    conversations,
    isLoading,
    loadConversations,
    deleteConversation,
    clearAllConversations,
    refreshConversations,
    addConversation
  }
}