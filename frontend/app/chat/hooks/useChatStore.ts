// ==================== STORE CHAT MIS À JOUR POUR CONVERSATIONS ====================

import { create } from 'zustand'
import { conversationService } from '../services/conversationService'
import { 
  Conversation,
  ConversationWithMessages, 
  ConversationGroup,
  ConversationGroupingOptions,
  Message,
  ConversationItem // Import pour compatibilité
} from '../types'

interface ChatStore {
  // ✅ NOUVEAU: États pour les conversations
  conversations: Conversation[]
  conversationGroups: ConversationGroup[]
  currentConversation: ConversationWithMessages | null
  
  // États de chargement
  isLoading: boolean
  isLoadingHistory: boolean
  isLoadingConversation: boolean
  error: string | null
  
  // ✅ NOUVEAU: Actions principales pour conversations
  loadConversations: (userId: string, options?: ConversationGroupingOptions) => Promise<void>
  loadConversation: (conversationId: string) => Promise<void>
  setCurrentConversation: (conversation: ConversationWithMessages | null) => void
  createNewConversation: () => void
  
  // Actions de gestion
  deleteConversation: (conversationId: string) => Promise<void>
  clearAllConversations: (userId: string) => Promise<void>
  refreshConversations: (userId: string) => Promise<void>
  
  // Actions pour messages dans la conversation courante
  addMessage: (message: Message) => void
  updateMessage: (messageId: string, updates: Partial<Message>) => void
  
  // ✅ HÉRITÉES: Actions pour compatibilité avec l'existant
  addConversation: (conversationId: string, question: string, response: string) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  // États initiaux
  conversations: [],
  conversationGroups: [],
  currentConversation: null,
  isLoading: false,
  isLoadingHistory: false,
  isLoadingConversation: false,
  error: null,

  // ==================== ACTIONS PRINCIPALES ====================

  /**
   * Charge l'historique des conversations pour un utilisateur
   */
  loadConversations: async (userId: string, options?: ConversationGroupingOptions) => {
    if (!userId) {
      console.warn('⚠️ [ChatStore] User ID requis pour charger conversations')
      return
    }

    set({ isLoadingHistory: true, error: null })
    
    try {
      console.log('📂 [ChatStore] Chargement conversations pour:', userId)
      
      // Utiliser la méthode existante avec transformation
      const rawConversations = await conversationService.getUserConversations(userId, options?.limit || 50)
      
      // Grouper par date
      const groups = conversationService.groupConversationsByDate(rawConversations)
      
      set({
        conversations: rawConversations,
        conversationGroups: groups,
        isLoadingHistory: false,
        error: null
      })
      
      console.log('✅ [ChatStore] Conversations chargées:', rawConversations.length, 'conversations,', groups.length, 'groupes')
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur chargement conversations:', error)
      set({
        isLoadingHistory: false,
        error: error instanceof Error ? error.message : 'Erreur de chargement'
      })
    }
  },

  /**
   * Charge une conversation spécifique avec tous ses messages
   */
  loadConversation: async (conversationId: string) => {
    if (!conversationId) {
      console.warn('⚠️ [ChatStore] ID conversation requis')
      return
    }

    set({ isLoadingConversation: true, error: null })
    
    try {
      console.log('📖 [ChatStore] Chargement conversation:', conversationId)
      
      // Chercher dans les conversations existantes
      const { conversations } = get()
      const existingConv = conversations.find(c => c.id === conversationId)
      
      if (existingConv) {
        // Récupérer les données complètes depuis le service
        const rawData = await conversationService.getUserConversations('temp')
        const fullData = rawData.find((c: any) => c.id === conversationId)
        
        if (fullData) {
          const conversationWithMessages = conversationService.transformToConversationWithMessages(fullData)
          
          set({
            currentConversation: conversationWithMessages,
            isLoadingConversation: false,
            error: null
          })
          
          console.log('✅ [ChatStore] Conversation chargée:', conversationWithMessages.message_count, 'messages')
        } else {
          throw new Error('Conversation non trouvée')
        }
      } else {
        throw new Error('Conversation non trouvée dans l\'historique')
      }
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur chargement conversation:', error)
      set({
        isLoadingConversation: false,
        error: error instanceof Error ? error.message : 'Erreur de chargement'
      })
    }
  },

  /**
   * Définit la conversation courante
   */
  setCurrentConversation: (conversation: ConversationWithMessages | null) => {
    console.log('🔄 [ChatStore] Définition conversation courante:', conversation?.id || 'null')
    set({ currentConversation: conversation })
  },

  /**
   * Crée une nouvelle conversation vide
   */
  createNewConversation: () => {
    console.log('✨ [ChatStore] Création nouvelle conversation')
    set({ currentConversation: null })
  },

  // ==================== ACTIONS DE GESTION ====================

  /**
   * Supprime une conversation
   */
  deleteConversation: async (conversationId: string) => {
    try {
      console.log('🗑️ [ChatStore] Suppression conversation:', conversationId)
      
      // Supprimer côté serveur
      await conversationService.deleteConversation(conversationId)
      
      // Mettre à jour le store
      const { conversations, conversationGroups, currentConversation } = get()
      
      const updatedConversations = conversations.filter(c => c.id !== conversationId)
      const updatedGroups = conversationService.groupConversationsByDate(updatedConversations)
      
      set({
        conversations: updatedConversations,
        conversationGroups: updatedGroups,
        currentConversation: currentConversation?.id === conversationId ? null : currentConversation
      })
      
      console.log('✅ [ChatStore] Conversation supprimée')
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur suppression conversation:', error)
      throw error
    }
  },

  /**
   * Supprime toutes les conversations d'un utilisateur
   */
  clearAllConversations: async (userId: string) => {
    try {
      console.log('🗑️ [ChatStore] Suppression toutes conversations pour:', userId)
      
      // Supprimer côté serveur
      await conversationService.clearAllUserConversations(userId)
      
      // Vider le store
      set({
        conversations: [],
        conversationGroups: [],
        currentConversation: null
      })
      
      console.log('✅ [ChatStore] Toutes conversations supprimées')
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur suppression toutes conversations:', error)
      throw error
    }
  },

  /**
   * Rafraîchit l'historique des conversations
   */
  refreshConversations: async (userId: string) => {
    console.log('🔄 [ChatStore] Rafraîchissement conversations')
    await get().loadConversations(userId)
  },

  // ==================== ACTIONS POUR MESSAGES ====================

  /**
   * Ajoute un message à la conversation courante
   */
  addMessage: (message: Message) => {
    const { currentConversation } = get()
    
    if (!currentConversation) {
      console.warn('⚠️ [ChatStore] Aucune conversation courante pour ajouter message')
      return
    }
    
    const updatedConversation: ConversationWithMessages = {
      ...currentConversation,
      messages: [...currentConversation.messages, message],
      message_count: currentConversation.message_count + 1,
      updated_at: new Date().toISOString(),
      last_message_preview: message.content.substring(0, 100) + '...'
    }
    
    set({ currentConversation: updatedConversation })
    console.log('➕ [ChatStore] Message ajouté à la conversation courante')
  },

  /**
   * Met à jour un message dans la conversation courante
   */
  updateMessage: (messageId: string, updates: Partial<Message>) => {
    const { currentConversation } = get()
    
    if (!currentConversation) {
      console.warn('⚠️ [ChatStore] Aucune conversation courante pour mettre à jour message')
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
    
    set({ currentConversation: updatedConversation })
    console.log('✏️ [ChatStore] Message mis à jour:', messageId)
  },

  // ==================== MÉTHODES DE COMPATIBILITÉ ====================

  /**
   * Ajoute une conversation (format hérité pour compatibilité)
   */
  addConversation: (conversationId: string, question: string, response: string) => {
    console.log('📝 [ChatStore] Ajout conversation (compatibilité):', conversationId)
    
    const { conversations } = get()
    
    // Vérifier si la conversation existe déjà
    const existingIndex = conversations.findIndex(c => c.id === conversationId)
    
    const newConversation: Conversation = {
      id: conversationId,
      title: question.substring(0, 60) + (question.length > 60 ? '...' : ''),
      preview: question,
      message_count: 2, // question + réponse
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      language: 'fr',
      last_message_preview: response.substring(0, 100) + (response.length > 100 ? '...' : ''),
      status: 'active'
    }
    
    let updatedConversations: Conversation[]
    
    if (existingIndex >= 0) {
      // Mettre à jour l'existante
      updatedConversations = conversations.map((conv, index) =>
        index === existingIndex ? { ...newConversation, created_at: conv.created_at } : conv
      )
    } else {
      // Ajouter la nouvelle en première position
      updatedConversations = [newConversation, ...conversations]
    }
    
    // Regrouper les conversations
    const groups = conversationService.groupConversationsByDate(updatedConversations)
    
    set({
      conversations: updatedConversations,
      conversationGroups: groups
    })
    
    console.log('✅ [ChatStore] Conversation ajoutée/mise à jour')
  }
}))

// ==================== HOOKS UTILITAIRES ====================

/**
 * Hook pour obtenir les conversations groupées
 */
export const useConversationGroups = () => {
  const conversationGroups = useChatStore(state => state.conversationGroups)
  const isLoadingHistory = useChatStore(state => state.isLoadingHistory)
  const loadConversations = useChatStore(state => state.loadConversations)
  
  return {
    conversationGroups,
    isLoadingHistory,
    loadConversations
  }
}

/**
 * Hook pour obtenir la conversation courante
 */
export const useCurrentConversation = () => {
  const currentConversation = useChatStore(state => state.currentConversation)
  const isLoadingConversation = useChatStore(state => state.isLoadingConversation)
  const setCurrentConversation = useChatStore(state => state.setCurrentConversation)
  const loadConversation = useChatStore(state => state.loadConversation)
  const addMessage = useChatStore(state => state.addMessage)
  const updateMessage = useChatStore(state => state.updateMessage)
  
  return {
    currentConversation,
    isLoadingConversation,
    setCurrentConversation,
    loadConversation,
    addMessage,
    updateMessage
  }
}

/**
 * Hook pour les actions de gestion des conversations
 */
export const useConversationActions = () => {
  const deleteConversation = useChatStore(state => state.deleteConversation)
  const clearAllConversations = useChatStore(state => state.clearAllConversations)
  const refreshConversations = useChatStore(state => state.refreshConversations)
  const createNewConversation = useChatStore(state => state.createNewConversation)
  
  return {
    deleteConversation,
    clearAllConversations,
    refreshConversations,
    createNewConversation
  }
}