import { create } from 'zustand'
import { ConversationItem, Conversation, ConversationWithMessages, ConversationGroup, Message } from '../../../types'
import { conversationService } from '../services/conversationService'
import { loadUserConversations } from '../services/apiService'

// ==================== PROTECTION GLOBALE CONTRE LA BOUCLE ====================
const globalLoadingProtection = {
  isLoading: false,
  currentUserId: null as string | null,
  lastLoadTime: 0,
  COOLDOWN_PERIOD: 3000, // 3 secondes entre les chargements
  MAX_RETRIES: 3,
  retryCount: 0
}

// ==================== INTERFACE DU STORE ====================
interface ChatStoreState {
  conversations: ConversationItem[]
  isLoading: boolean
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

// ==================== STORE ZUSTAND AVEC PROTECTION ====================
export const useChatStore = create<ChatStoreState>((set, get) => ({
  conversations: [],
  isLoading: false,
  conversationGroups: [],
  currentConversation: null,
  isLoadingHistory: false,
  isLoadingConversation: false,

  // ==================== MÉTHODE CORRIGÉE loadConversations ====================
  loadConversations: async (userId: string) => {
    if (!userId) {
      console.warn('⚠️ [ChatStore] Pas d\'userId fourni pour charger les conversations')
      return
    }

    // PROTECTION 1: Vérifier si un chargement est déjà en cours pour ce user
    if (globalLoadingProtection.isLoading && globalLoadingProtection.currentUserId === userId) {
      console.log('🛡️ [ChatStore] Chargement déjà en cours pour cet utilisateur, ignoré')
      return
    }

    // PROTECTION 2: Cooldown entre les chargements
    const now = Date.now()
    if (now - globalLoadingProtection.lastLoadTime < globalLoadingProtection.COOLDOWN_PERIOD) {
      console.log('🛡️ [ChatStore] Cooldown actif, chargement ignoré')
      return
    }

    // PROTECTION 3: Maximum de tentatives
    if (globalLoadingProtection.retryCount >= globalLoadingProtection.MAX_RETRIES) {
      console.log('🛡️ [ChatStore] Maximum de tentatives atteint, chargement bloqué')
      return
    }

    // Marquer comme en cours de chargement
    globalLoadingProtection.isLoading = true
    globalLoadingProtection.currentUserId = userId
    globalLoadingProtection.lastLoadTime = now
    globalLoadingProtection.retryCount++

    set({ isLoading: true, isLoadingHistory: true })
    
    try {
      console.log('📡 [ChatStore] Chargement conversations pour:', userId)
      
      const conversationsData = await loadUserConversations(userId)
      
      if (!conversationsData || !conversationsData.conversations || conversationsData.conversations.length === 0) {
        console.log('🔭 [ChatStore] Aucune conversation trouvée')
        set({ 
          conversations: [], 
          conversationGroups: [],
          isLoading: false,
          isLoadingHistory: false
        })
        return
      }
      
      const userConversations = conversationsData.conversations
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
      
      // SUCCÈS: Reset du compteur de retry
      globalLoadingProtection.retryCount = 0
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur chargement conversations:', error)
      set({ 
        conversations: [],
        conversationGroups: [],
        isLoading: false,
        isLoadingHistory: false
      })
      
      // En cas d'erreur, permettre un nouveau chargement après un délai
      if (globalLoadingProtection.retryCount < globalLoadingProtection.MAX_RETRIES) {
        setTimeout(() => {
          globalLoadingProtection.isLoading = false
        }, 5000) // 5 secondes avant de permettre un retry
      }
      
      throw error
    } finally {
      // IMPORTANT: Reset du flag de chargement
      globalLoadingProtection.isLoading = false
      globalLoadingProtection.lastLoadTime = Date.now()
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
      
      // Reset de la protection globale
      globalLoadingProtection.isLoading = false
      globalLoadingProtection.currentUserId = null
      globalLoadingProtection.retryCount = 0
      
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
    // Reset de la protection pour permettre un refresh manuel
    globalLoadingProtection.isLoading = false
    globalLoadingProtection.retryCount = 0
    globalLoadingProtection.lastLoadTime = 0
    
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

  loadConversation: async (conversationId: string) => {
    if (!conversationId) {
      console.warn('⚠️ [ChatStore] ID conversation requis')
      return
    }

    set({ isLoadingConversation: true })
    
    try {
      console.log('📖 [ChatStore] Chargement conversation:', conversationId)
      
      try {
        const fullConversation = await conversationService.getConversationWithMessages?.(conversationId)
        
        if (fullConversation && fullConversation.messages && fullConversation.messages.length > 0) {
          console.log('✅ [ChatStore] Conversation chargée depuis serveur avec messages complets')
          set({ currentConversation: fullConversation, isLoadingConversation: false })
          return
        }
      } catch (serviceError) {
        console.warn('⚠️ [ChatStore] Service getConversationWithMessages non disponible:', serviceError)
      }
      
      const state = get()
      const existingConv = state.conversations.find(c => c.id === conversationId)
      
      if (existingConv) {
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
        
        set({ currentConversation: conversationWithMessages, isLoadingConversation: false })
        console.log('✅ [ChatStore] Conversation chargée depuis cache local')
        return
      }
      
      const errorConversation: ConversationWithMessages = {
        id: conversationId,
        title: 'Conversation non disponible',
        preview: 'Impossible de charger les messages',
        message_count: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        language: 'fr',
        status: 'active',
        messages: [{
          id: 'error-' + Date.now(),
          content: '❌ Impossible de charger cette conversation. Veuillez réessayer ou commencer une nouvelle conversation.',
          isUser: false,
          timestamp: new Date(),
          conversation_id: conversationId
        }]
      }
      
      set({ currentConversation: errorConversation, isLoadingConversation: false })
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur chargement conversation:', error)
      set({ isLoadingConversation: false })
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
      console.log('🆕 [ChatStore] Conversation temporaire créée:', tempConversation.id)
      return
    }
    
    const messageExists = state.currentConversation.messages?.some(m => m.id === message.id)
    if (messageExists) {
      console.log('⚠️ [ChatStore] Message déjà existant, ignoré')
      return
    }
    
    const updatedMessages = [...(state.currentConversation.messages || []), message]
    
    let updatedId = state.currentConversation.id
    
    if (message.conversation_id && 
        (state.currentConversation.id === 'welcome' || 
         state.currentConversation.id.startsWith('temp-'))) {
      updatedId = message.conversation_id
      console.log('🔄 [ChatStore] ID conversation mis à jour:', state.currentConversation.id, '→', updatedId)
    }
    
    const updatedConversation: ConversationWithMessages = {
      ...state.currentConversation,
      id: updatedId,
      messages: updatedMessages,
      message_count: updatedMessages.length,
      updated_at: new Date().toISOString(),
      title: state.currentConversation.id === 'welcome' && message.isUser 
        ? message.content.substring(0, 60) + (message.content.length > 60 ? '...' : '')
        : state.currentConversation.title,
      last_message_preview: !message.isUser 
        ? message.content.substring(0, 100) + (message.content.length > 100 ? '...' : '')
        : state.currentConversation.last_message_preview || state.currentConversation.preview
    }
    
    set({ currentConversation: updatedConversation })
    
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
  },

  setCurrentConversation: (conversation: ConversationWithMessages | null) => {
    console.log('🔄 [ChatStore] setCurrentConversation appelée:', conversation?.id, 'Messages:', conversation?.messages?.length || 0)
    set({ currentConversation: conversation })
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