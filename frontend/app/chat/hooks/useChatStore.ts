import { useState, useCallback } from 'react'
import { ConversationItem, ChatStore, Conversation, ConversationWithMessages, ConversationGroup, ConversationGroupingOptions, Message } from '../types'
import { conversationService } from '../services/conversationService'

// ==================== HOOK CHAT AMÉLIORÉ AVEC CONVERSATIONS STYLE CLAUDE.AI ====================
export const useChatStore = (): ChatStore => {
  // ✅ ÉTATS EXISTANTS CONSERVÉS
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // ✅ NOUVEAUX ÉTATS POUR CONVERSATIONS STYLE CLAUDE.AI
  const [conversationGroups, setConversationGroups] = useState<ConversationGroup[]>([])
  const [currentConversation, setCurrentConversation] = useState<ConversationWithMessages | null>(null)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [isLoadingConversation, setIsLoadingConversation] = useState(false)

  // ==================== FONCTIONS EXISTANTES CONSERVÉES ====================

  const loadConversations = async (userId: string): Promise<void> => {
    if (!userId) {
      console.warn('⚠️ [useChatStore] Pas d\'userId fourni pour charger les conversations')
      return
    }

    setIsLoading(true)
    setIsLoadingHistory(true) // ✅ NOUVEAU: état pour l'historique
    
    try {
      console.log('🔄 [useChatStore] Chargement conversations pour userId:', userId)
      const userConversations = await conversationService.getUserConversations(userId, 100)
      
      console.log('📊 [useChatStore] Conversations brutes reçues:', userConversations.length, userConversations)
      
      if (!userConversations || userConversations.length === 0) {
        console.log('📭 [useChatStore] Aucune conversation trouvée')
        setConversations([])
        setConversationGroups([]) // ✅ NOUVEAU: vider les groupes
        return
      }
      
      // ✅ LOGIQUE EXISTANTE CONSERVÉE
      const formattedConversations: ConversationItem[] = userConversations.map(conv => {
        const title = conv.title && conv.title.length > 0 
          ? (conv.title.length > 50 ? conv.title.substring(0, 50) + '...' : conv.title)
          : 'Conversation sans titre'
          
        return {
          id: conv.id || Date.now().toString(),
          title: title,
          messages: [
            { id: `${conv.id}-q`, role: 'user', content: conv.preview || 'Question non disponible' },
            { id: `${conv.id}-a`, role: 'assistant', content: conv.last_message_preview || 'Réponse non disponible' }
          ],
          updated_at: conv.updated_at || new Date().toISOString(),
          created_at: conv.created_at || new Date().toISOString(),
          feedback: conv.feedback || null
        }
      })
      
      // Trier par date de mise à jour (plus récent en premier)
      const sortedConversations = formattedConversations.sort((a, b) => 
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      
      setConversations(sortedConversations)
      
      // ✅ NOUVEAU: Grouper par date
      const groups = groupConversationsByDate(userConversations)
      setConversationGroups(groups)
      
      console.log('✅ [useChatStore] Conversations formatées et triées:', sortedConversations.length)
      console.log('✅ [useChatStore] Groupes créés:', groups.length)
      
    } catch (error) {
      console.error('❌ [useChatStore] Erreur chargement conversations:', error)
      setConversations([])
      setConversationGroups([])
    } finally {
      setIsLoading(false)
      setIsLoadingHistory(false)
    }
  }

  const deleteConversation = async (id: string): Promise<void> => {
    try {
      console.log('🗑️ [useChatStore] Suppression conversation:', id)
      
      // 1. Mise à jour optimiste de l'UI (suppression immédiate)
      setConversations(prev => prev.filter(conv => conv.id !== id))
      
      // ✅ NOUVEAU: Supprimer des groupes aussi
      setConversationGroups(prev => 
        prev.map(group => ({
          ...group,
          conversations: group.conversations.filter(conv => conv.id !== id)
        })).filter(group => group.conversations.length > 0)
      )
      
      // ✅ NOUVEAU: Si c'est la conversation courante, la déselectionner
      if (currentConversation?.id === id) {
        setCurrentConversation(null)
      }
      
      // 2. Suppression côté serveur
      await conversationService.deleteConversation(id)
      
      console.log('✅ [useChatStore] Conversation supprimée du serveur:', id)
      
    } catch (error) {
      console.error('❌ [useChatStore] Erreur suppression conversation serveur:', error)
    }
  }

  const clearAllConversations = async (userId?: string): Promise<void> => {
    try {
      console.log('🗑️ [useChatStore] Suppression toutes conversations')
      
      // 1. Mise à jour optimiste de l'UI (suppression immédiate)
      setConversations([])
      setConversationGroups([]) // ✅ NOUVEAU: vider les groupes
      setCurrentConversation(null) // ✅ NOUVEAU: déselectionner conversation courante
      
      // 2. Suppression côté serveur si userId disponible
      if (userId) {
        await conversationService.clearAllUserConversations(userId)
        console.log('✅ [useChatStore] Toutes conversations supprimées du serveur')
      } else {
        console.warn('⚠️ [useChatStore] Pas d\'userId pour suppression serveur')
      }
      
    } catch (error) {
      console.error('❌ [useChatStore] Erreur suppression conversations serveur:', error)
    }
  }

  const refreshConversations = async (userId: string): Promise<void> => {
    console.log('🔄 [useChatStore] Rechargement forcé des conversations')
    await loadConversations(userId)
  }

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

    // ✅ NOUVEAU: Ajouter au nouveau format aussi
    const newFormatConversation: Conversation = {
      id: conversationId,
      title: question.length > 60 ? question.substring(0, 60) + '...' : question,
      preview: question,
      message_count: 2,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      language: 'fr',
      last_message_preview: response.substring(0, 100) + (response.length > 100 ? '...' : ''),
      status: 'active'
    }

    // Mettre à jour les groupes
    setConversationGroups(prev => {
      // Créer une nouvelle liste avec la nouvelle conversation
      const allConversations = [newFormatConversation, ...prev.flatMap(g => g.conversations)]
      return groupConversationsByDate(allConversations)
    })
    
    console.log('✅ [useChatStore] Nouvelle conversation ajoutée localement:', conversationId)
  }

  // ==================== NOUVELLES FONCTIONS POUR CONVERSATIONS STYLE CLAUDE.AI ====================

  /**
   * Charge une conversation spécifique avec tous ses messages
   */
  const loadConversation = async (conversationId: string): Promise<void> => {
    if (!conversationId) {
      console.warn('⚠️ [useChatStore] ID conversation requis')
      return
    }

    setIsLoadingConversation(true)
    
    try {
      console.log('📖 [useChatStore] Chargement conversation:', conversationId)
      
      // Chercher dans les conversations existantes (format ancien)
      const existingConv = conversations.find(c => c.id === conversationId)
      
      if (existingConv) {
        // Transformer vers le nouveau format avec messages
        const conversationWithMessages: ConversationWithMessages = {
          id: existingConv.id,
          title: existingConv.title,
          preview: existingConv.messages.find(m => m.role === 'user')?.content || 'Aucun aperçu',
          message_count: existingConv.messages.length,
          created_at: existingConv.created_at,
          updated_at: existingConv.updated_at,
          language: 'fr',
          status: 'active',
          feedback: existingConv.feedback,
          messages: existingConv.messages.map(msg => ({
            id: msg.id,
            content: msg.content,
            isUser: msg.role === 'user',
            timestamp: new Date(existingConv.updated_at),
            conversation_id: conversationId,
            feedback: msg.role === 'assistant' && existingConv.feedback === 1 ? 'positive' 
                    : msg.role === 'assistant' && existingConv.feedback === -1 ? 'negative' 
                    : null
          }))
        }
        
        setCurrentConversation(conversationWithMessages)
        console.log('✅ [useChatStore] Conversation chargée:', conversationWithMessages.message_count, 'messages')
      } else {
        throw new Error('Conversation non trouvée dans l\'historique')
      }
      
    } catch (error) {
      console.error('❌ [useChatStore] Erreur chargement conversation:', error)
    } finally {
      setIsLoadingConversation(false)
    }
  }

  /**
   * Crée une nouvelle conversation vide
   */
  const createNewConversation = (): void => {
    console.log('✨ [useChatStore] Création nouvelle conversation')
    setCurrentConversation(null)
  }

  /**
   * Ajoute un message à la conversation courante
   */
  const addMessage = (message: Message): void => {
    console.log('💬 [addMessage] Tentative ajout:', {
      messageId: message.id,
      isUser: message.isUser,
      content: message.content.substring(0, 50) + '...',
      conversationId: currentConversation?.id,
      currentMessagesCount: currentConversation?.messages?.length || 0
    })
    
    if (!currentConversation) {
      console.warn('⚠️ [addMessage] Aucune conversation - création temporaire')
      
      const tempConversation: ConversationWithMessages = {
        id: 'temp-' + Date.now(),
        title: message.isUser ? message.content.substring(0, 60) + '...' : 'Nouvelle conversation',
        preview: message.content,
        message_count: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        language: 'fr',
        status: 'active',
        messages: [message]
      }
      
      setCurrentConversation(tempConversation)
      console.log('✅ [addMessage] Conversation temporaire créée avec message')
      return
    }
    
    // Vérification doublons améliorée
    const messageExists = currentConversation.messages?.some(m => 
      m.id === message.id || 
      (m.content === message.content && m.isUser === message.isUser)
    )
    
    if (messageExists) {
      console.warn('⚠️ [addMessage] Message doublon détecté, ignoré:', message.id)
      return
    }
    
    // Mise à jour conversation avec nouveau message
    const updatedMessages = [...(currentConversation.messages || []), message]
    
    const updatedConversation: ConversationWithMessages = {
      ...currentConversation,
      messages: updatedMessages,
      message_count: updatedMessages.length,
      updated_at: new Date().toISOString(),
      title: currentConversation.id === 'welcome' && message.isUser 
        ? message.content.substring(0, 60) + (message.content.length > 60 ? '...' : '')
        : currentConversation.title,
      last_message_preview: !message.isUser 
        ? message.content.substring(0, 100) + (message.content.length > 100 ? '...' : '')
        : currentConversation.last_message_preview || currentConversation.preview
    }
    
    console.log('🔄 [addMessage] Conversation mise à jour:', {
      id: updatedConversation.id,
      messageCount: updatedConversation.messages.length,
      title: updatedConversation.title.substring(0, 30) + '...'
    })
    
    setCurrentConversation(updatedConversation)
    
    // Force re-render avec log de vérification
    setTimeout(() => {
      console.log('🔍 [addMessage] Vérification post-ajout:', {
        conversationId: updatedConversation.id,
        messagesInState: updatedConversation.messages.length,
        lastMessage: updatedConversation.messages[updatedConversation.messages.length - 1]?.content.substring(0, 30) + '...'
      })
    }, 100)
  }

  /**
   * Met à jour un message dans la conversation courante
   */
  const updateMessage = (messageId: string, updates: Partial<Message>): void => {
    if (!currentConversation) {
      console.warn('⚠️ [useChatStore] Aucune conversation courante pour mettre à jour message')
      return
    }
    
    const updatedMessages = currentConversation.messages.map(msg =>
      msg.id === messageId ? { ...msg, ...updates } : msg
    )
    
    const updatedConversation: ConversationWithMessages = {
      ...currentConversation,
      messages: updatedMessages,
      updated_at: new Date().toISOString()
    }
    
    setCurrentConversation(updatedConversation)
    console.log('✏️ [useChatStore] Message mis à jour:', messageId)
  }

  // ==================== FONCTION UTILITAIRE POUR GROUPEMENT ====================

  /**
   * Groupe les conversations par date
   */
  const groupConversationsByDate = (conversations: Conversation[]): ConversationGroup[] => {
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

  // ==================== RETOUR INTERFACE ÉTENDUE ====================

  return {
    // ✅ PROPRIÉTÉS EXISTANTES CONSERVÉES
    conversations,
    isLoading,
    loadConversations,
    deleteConversation,
    clearAllConversations,
    refreshConversations,
    addConversation,

    // ✅ NOUVELLES PROPRIÉTÉS POUR CONVERSATIONS STYLE CLAUDE.AI
    conversationGroups,
    currentConversation,
    isLoadingHistory,
    isLoadingConversation,
    loadConversation,
    createNewConversation,
    addMessage,
    updateMessage,
    setCurrentConversation
  }
}

// ==================== HOOKS UTILITAIRES POUR CONVERSATIONS ====================

/**
 * Hook pour obtenir les conversations groupées
 */
export const useConversationGroups = () => {
  const store = useChatStore()
  
  return {
    conversationGroups: store.conversationGroups,
    isLoadingHistory: store.isLoadingHistory,
    loadConversations: store.loadConversations
  }
}

/**
 * Hook pour obtenir la conversation courante
 */
export const useCurrentConversation = () => {
  const store = useChatStore()
  
  return {
    currentConversation: store.currentConversation,
    isLoadingConversation: store.isLoadingConversation,
    setCurrentConversation: store.setCurrentConversation,
    loadConversation: store.loadConversation,
    addMessage: store.addMessage,
    updateMessage: store.updateMessage
  }
}

/**
 * Hook pour les actions de gestion des conversations
 */
export const useConversationActions = () => {
  const store = useChatStore()
  
  return {
    deleteConversation: store.deleteConversation,
    clearAllConversations: store.clearAllConversations,
    refreshConversations: store.refreshConversations,
    createNewConversation: store.createNewConversation
  }
}