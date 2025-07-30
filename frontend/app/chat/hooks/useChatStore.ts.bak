import { create } from 'zustand'
import { ConversationItem, Conversation, ConversationWithMessages, ConversationGroup, Message } from '../types'
import { conversationService } from '../services/conversationService'

// ==================== INTERFACE DU STORE ====================
interface ChatStoreState {
  // États existants
  conversations: ConversationItem[]
  isLoading: boolean
  
  // Nouveaux états pour conversations style Claude.ai
  conversationGroups: ConversationGroup[]
  currentConversation: ConversationWithMessages | null
  isLoadingHistory: boolean
  isLoadingConversation: boolean
  
  // Actions
  loadConversations: (userId: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  clearAllConversations: (userId?: string) => Promise<void>
  refreshConversations: (userId: string) => Promise<void>
  addConversation: (conversationId: string, question: string, response: string) => void
  loadConversation: (conversationId: string) => Promise<void>
  createNewConversation: () => void
  addMessage: (message: Message) => void
  updateMessage: (messageId: string, updates: Partial<Message>) => void
  setCurrentConversation: (conversation: ConversationWithMessages | null) => void
  syncConversationToHistory: (conversation: ConversationWithMessages) => void
}

// ==================== FONCTION UTILITAIRE GROUPEMENT ====================
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

  // ✅ CORRECTION: Trier par date AVANT groupement
  const sortedConversations = [...conversations].sort((a, b) => 
    new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  )

  sortedConversations.forEach(conv => {
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

// ==================== STORE ZUSTAND CENTRALISÉ ====================
export const useChatStore = create<ChatStoreState>((set, get) => ({
  // États initiaux
  conversations: [],
  isLoading: false,
  conversationGroups: [],
  currentConversation: null,
  isLoadingHistory: false,
  isLoadingConversation: false,

  // ==================== ACTIONS EXISTANTES ====================
  
  loadConversations: async (userId: string) => {
    if (!userId) {
      console.warn('⚠️ [ChatStore] Pas d\'userId fourni pour charger les conversations')
      return
    }

    set({ isLoading: true, isLoadingHistory: true })
    
    try {
      console.log('📡 [ChatStore] Chargement conversations pour:', userId)
      const userConversations = await conversationService.getUserConversations(userId, 100)
      
      if (!userConversations || userConversations.length === 0) {
        console.log('📭 [ChatStore] Aucune conversation trouvée')
        set({ 
          conversations: [], 
          conversationGroups: [],
          isLoading: false,
          isLoadingHistory: false
        })
        return
      }
      
      console.log('✅ [ChatStore] Conversations récupérées:', userConversations.length)
      
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
      
      const sortedConversations = formattedConversations.sort((a, b) => 
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      
      const groups = groupConversationsByDate(userConversations)
      
      set({ 
        conversations: sortedConversations,
        conversationGroups: groups,
        isLoading: false,
        isLoadingHistory: false
      })
      
      console.log('✅ [ChatStore] État mis à jour - Conversations:', sortedConversations.length, 'Groupes:', groups.length)
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur chargement conversations:', error)
      set({ 
        conversations: [],
        conversationGroups: [],
        isLoading: false,
        isLoadingHistory: false
      })
    }
  },

  deleteConversation: async (id: string) => {
    try {
      console.log('🗑️ [ChatStore] Suppression conversation:', id)
      
      const state = get()
      const updatedConversations = state.conversations.filter(conv => conv.id !== id)
      const updatedGroups = state.conversationGroups.map(group => ({
        ...group,
        conversations: group.conversations.filter(conv => conv.id !== id)
      })).filter(group => group.conversations.length > 0)
      
      set({ 
        conversations: updatedConversations,
        conversationGroups: updatedGroups,
        currentConversation: state.currentConversation?.id === id ? null : state.currentConversation
      })
      
      await conversationService.deleteConversation(id)
      console.log('✅ [ChatStore] Conversation supprimée côté serveur')
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur suppression conversation:', error)
    }
  },

  clearAllConversations: async (userId?: string) => {
    try {
      console.log('🗑️ [ChatStore] Suppression toutes conversations')
      
      set({ 
        conversations: [],
        conversationGroups: [],
        currentConversation: null
      })
      
      if (userId) {
        await conversationService.clearAllUserConversations(userId)
        console.log('✅ [ChatStore] Toutes conversations supprimées côté serveur')
      }
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur suppression conversations:', error)
    }
  },

  refreshConversations: async (userId: string) => {
    await get().loadConversations(userId)
  },

  addConversation: (conversationId: string, question: string, response: string) => {
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
    
    const state = get()
    const updatedConversations = [newConversation, ...state.conversations]

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

    const allConversations = [newFormatConversation, ...state.conversationGroups.flatMap(g => g.conversations)]
    const updatedGroups = groupConversationsByDate(allConversations)

    set({ 
      conversations: updatedConversations,
      conversationGroups: updatedGroups
    })
  },

  // ==================== NOUVELLE ACTION CORRIGÉE - loadConversation ====================

  loadConversation: async (conversationId: string) => {
    if (!conversationId) {
      console.warn('⚠️ [ChatStore] ID conversation requis')
      return
    }

    set({ isLoadingConversation: true })
    
    try {
      console.log('📖 [ChatStore] Chargement conversation complète:', conversationId)
      
      // ✅ CORRECTION CRITIQUE: Utiliser la nouvelle méthode getConversationWithMessages
      const fullConversation = await conversationService.getConversationWithMessages(conversationId)
      
      if (fullConversation && fullConversation.messages && fullConversation.messages.length > 0) {
        console.log('✅ [ChatStore] Conversation chargée depuis serveur:', fullConversation.messages.length, 'messages')
        set({ currentConversation: fullConversation, isLoadingConversation: false })
        return
      }
      
      // ✅ CORRECTION: Fallback amélioré - ne pas utiliser les aperçus tronqués
      console.warn('⚠️ [ChatStore] Serveur non disponible, mais éviter les aperçus tronqués')
      
      // Créer une conversation avec message d'erreur informatif
      const fallbackConversation: ConversationWithMessages = {
        id: conversationId,
        title: 'Conversation non disponible',
        preview: 'Impossible de charger les messages complets',
        message_count: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        language: 'fr',
        status: 'active',
        messages: [{
          id: 'error-' + Date.now(),
          content: '❌ Impossible de charger cette conversation. Les messages complets ne sont pas disponibles. Veuillez réessayer ou commencer une nouvelle conversation.',
          isUser: false,
          timestamp: new Date(),
          conversation_id: conversationId
        }]
      }
      
      set({ currentConversation: fallbackConversation, isLoadingConversation: false })
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur chargement conversation:', error)
      
      // Message d'erreur utilisateur-friendly
      const errorConversation: ConversationWithMessages = {
        id: conversationId,
        title: 'Erreur de chargement',
        preview: 'Une erreur est survenue',
        message_count: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        language: 'fr',
        status: 'active',
        messages: [{
          id: 'error-' + Date.now(),
          content: '❌ Une erreur est survenue lors du chargement de cette conversation. Veuillez réessayer plus tard.',
          isUser: false,
          timestamp: new Date(),
          conversation_id: conversationId
        }]
      }
      
      set({ currentConversation: errorConversation, isLoadingConversation: false })
    }
  },

  createNewConversation: () => {
    console.log('✨ [ChatStore] Nouvelle conversation')
    set({ currentConversation: null })
  },

  addMessage: (message: Message) => {
    console.log('💬 [ChatStore] Ajout message:', message.id, 'User:', message.isUser)
    
    const state = get()
    
    if (!state.currentConversation) {
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
      
      set({ currentConversation: tempConversation })
      return
    }
    
    const messageExists = state.currentConversation.messages?.some(m => m.id === message.id)
    if (messageExists) {
      console.log('⚠️ [ChatStore] Message déjà existant, ignoré')
      return
    }
    
    const updatedMessages = [...(state.currentConversation.messages || []), message]
    
    const updatedConversation: ConversationWithMessages = {
      ...state.currentConversation,
      messages: updatedMessages,
      message_count: updatedMessages.length,
      updated_at: new Date().toISOString(),
      id: message.conversation_id || state.currentConversation.id,
      title: state.currentConversation.id === 'welcome' && message.isUser 
        ? message.content.substring(0, 60) + (message.content.length > 60 ? '...' : '')
        : state.currentConversation.title,
      last_message_preview: !message.isUser 
        ? message.content.substring(0, 100) + (message.content.length > 100 ? '...' : '')
        : state.currentConversation.last_message_preview || state.currentConversation.preview
    }
    
    set({ currentConversation: updatedConversation })
    
    // ✅ NOUVEAU: Synchroniser avec l'historique si conversation confirmée
    if (message.conversation_id && !message.conversation_id.startsWith('temp-')) {
      get().syncConversationToHistory(updatedConversation)
    }
    
    console.log('✅ [ChatStore] Message ajouté - Total:', updatedMessages.length, 'Conv ID:', updatedConversation.id)
  },

  updateMessage: (messageId: string, updates: Partial<Message>) => {
    const state = get()
    if (!state.currentConversation) return
    
    const updatedMessages = state.currentConversation.messages.map(msg =>
      msg.id === messageId ? { ...msg, ...updates } : msg
    )
    
    const updatedConversation: ConversationWithMessages = {
      ...state.currentConversation,
      messages: updatedMessages,
      updated_at: new Date().toISOString()
    }
    
    set({ currentConversation: updatedConversation })
    
    // Synchroniser vers historique si conversation confirmée
    if (updatedConversation.id && !updatedConversation.id.startsWith('temp-')) {
      get().syncConversationToHistory(updatedConversation)
    }
  },

  setCurrentConversation: (conversation: ConversationWithMessages | null) => {
    console.log('🔄 [ChatStore] setCurrentConversation appelé:', conversation?.id, 'Messages:', conversation?.messages?.length || 0)
    set({ currentConversation: conversation })
  },

  // ==================== NOUVELLE ACTION: Synchroniser conversation vers historique ====================
  syncConversationToHistory: (conversation: ConversationWithMessages) => {
    if (!conversation.id || conversation.id.startsWith('temp-') || conversation.id === 'welcome') {
      return
    }

    const state = get()
    
    // Convertir en format pour l'historique
    const historyItem: ConversationItem = {
      id: conversation.id,
      title: conversation.title,
      messages: conversation.messages.map(msg => ({
        id: msg.id,
        role: msg.isUser ? 'user' : 'assistant',
        content: msg.content
      })),
      updated_at: conversation.updated_at,
      created_at: conversation.created_at,
      feedback: null // À récupérer depuis les messages si nécessaire
    }

    // Mettre à jour ou ajouter dans l'historique
    const existingIndex = state.conversations.findIndex(c => c.id === conversation.id)
    let updatedConversations: ConversationItem[]

    if (existingIndex >= 0) {
      // Mettre à jour conversation existante
      updatedConversations = [...state.conversations]
      updatedConversations[existingIndex] = historyItem
    } else {
      // Ajouter nouvelle conversation en tête
      updatedConversations = [historyItem, ...state.conversations]
    }

    // Regrouper pour l'affichage
    const serverFormat: Conversation = {
      id: conversation.id,
      title: conversation.title,
      preview: conversation.preview,
      message_count: conversation.message_count,
      created_at: conversation.created_at,
      updated_at: conversation.updated_at,
      language: conversation.language,
      status: conversation.status,
      last_message_preview: conversation.last_message_preview || conversation.preview
    }

    const allConversations = [serverFormat, ...state.conversationGroups.flatMap(g => g.conversations).filter(c => c.id !== conversation.id)]
    const updatedGroups = groupConversationsByDate(allConversations)

    set({ 
      conversations: updatedConversations,
      conversationGroups: updatedGroups
    })

    console.log('🔄 [ChatStore] Conversation synchronisée vers historique:', conversation.id)
  }
}))

// ==================== HOOKS UTILITAIRES ====================

export const useConversationGroups = () => {
  const conversationGroups = useChatStore(state => state.conversationGroups)
  const isLoadingHistory = useChatStore(state => state.isLoadingHistory)
  const loadConversations = useChatStore(state => state.loadConversations)
  
  return { conversationGroups, isLoadingHistory, loadConversations }
}

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