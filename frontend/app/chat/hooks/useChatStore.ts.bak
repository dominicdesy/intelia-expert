import { create } from 'zustand'
import { ConversationItem, Conversation, ConversationWithMessages, ConversationGroup, Message } from '../../../types'
import { conversationService } from '../services/conversationService'
import { loadUserConversations } from '../services/apiService'

// PROTECTION GLOBALE ULTRA-RENFORCÉE CONTRE LE POLLING
const globalLoadingProtection = {
  isLoading: false,
  currentUserId: null as string | null,
  lastLoadTime: 0,
  lastSuccessfulLoad: 0,
  COOLDOWN_PERIOD: 600000, // 10 MINUTES au lieu de 3 secondes
  SUCCESS_CACHE_DURATION: 1800000, // 30 MINUTES de cache après succès
  MAX_RETRIES: 1, // Seulement 1 retry au lieu de 3
  retryCount: 0,
  
  // Méthode de reset manuel seulement
  forceReset: function() {
    this.isLoading = false
    this.retryCount = 0
    this.lastLoadTime = 0
    console.log('🔄 [GlobalProtection] Reset forcé manuel')
  },
  
  // Vérification ultra-stricte
  canLoad: function(userId: string): boolean {
    const now = Date.now()
    
    // BLOQUAGE 1: Si chargement en cours pour le même user
    if (this.isLoading && this.currentUserId === userId) {
      console.log('🛡️ [GlobalProtection] Chargement déjà en cours, BLOQUÉ')
      return false
    }
    
    // BLOQUAGE 2: Si dernier chargement réussi trop récent (30 minutes)
    if (this.lastSuccessfulLoad > 0 && 
        (now - this.lastSuccessfulLoad) < this.SUCCESS_CACHE_DURATION) {
      const remainingTime = Math.ceil((this.SUCCESS_CACHE_DURATION - (now - this.lastSuccessfulLoad)) / 60000)
      console.log(`🛡️ [GlobalProtection] Cache encore valide pour ${remainingTime} minutes, BLOQUÉ`)
      return false
    }
    
    // BLOQUAGE 3: Cooldown entre tentatives (10 minutes)
    if ((now - this.lastLoadTime) < this.COOLDOWN_PERIOD) {
      const remainingCooldown = Math.ceil((this.COOLDOWN_PERIOD - (now - this.lastLoadTime)) / 60000)
      console.log(`🛡️ [GlobalProtection] Cooldown actif encore ${remainingCooldown} minutes, BLOQUÉ`)
      return false
    }
    
    // BLOQUAGE 4: Max retries atteint
    if (this.retryCount >= this.MAX_RETRIES) {
      console.log('🛡️ [GlobalProtection] Max retries atteint, BLOQUÉ définitivement')
      return false
    }
    
    return true
  },
  
  // Marquer le succès avec cache ultra-long
  recordSuccess: function() {
    this.lastSuccessfulLoad = Date.now()
    this.retryCount = 0
    this.isLoading = false
    console.log('✅ [GlobalProtection] Succès enregistré - Cache valide 30 minutes')
  }
}

// Interface du store
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

// Fonction utilitaire groupement
const groupConversationsByDate = (conversations: Conversation[]): ConversationGroup[] => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000)
  const thisWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)
  const thisMonth = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)

  const groups: ConversationGroup[] = [
    { title: "today", conversations: [] },
    { title: "yesterday", conversations: [] },
    { title: "thisWeek", conversations: [] },
    { title: "thisMonth", conversations: [] },
    { title: "older", conversations: [] }
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

// STORE ZUSTAND AVEC PROTECTION ANTI-POLLING MAXIMALE
export const useChatStore = create<ChatStoreState>((set, get) => ({
  conversations: [],
  isLoading: false,
  conversationGroups: [],
  currentConversation: null,
  isLoadingHistory: false,
  isLoadingConversation: false,

  // MÉTHODE loadConversations AVEC PROTECTION MAXIMALE
  loadConversations: async (userId: string) => {
    if (!userId) {
      console.warn('⚠️ [ChatStore] Pas d\'userId fourni')
      return
    }

    // PROTECTION STRICTE: Vérification absolue
    if (!globalLoadingProtection.canLoad(userId)) {
      console.log('🚫 [ChatStore] Chargement DÉFINITIVEMENT BLOQUÉ par protection globale')
      return
    }

    console.log('🟢 [ChatStore] Protection OK - SEUL chargement autorisé pour les 30 prochaines minutes')
    
    // Lock ultra-strict
    globalLoadingProtection.isLoading = true
    globalLoadingProtection.currentUserId = userId
    globalLoadingProtection.lastLoadTime = Date.now()
    globalLoadingProtection.retryCount++

    set({ isLoading: true, isLoadingHistory: true })
    
    try {
      console.log('📡 [ChatStore] Appel API loadUserConversations...')
      
      const conversationsData = await loadUserConversations(userId)
      
      if (!conversationsData || !conversationsData.conversations) {
        console.log('📭 [ChatStore] Aucune conversation trouvée')
        set({ 
          conversations: [], 
          conversationGroups: [],
          isLoading: false,
          isLoadingHistory: false
        })
        
        // Marquer comme succès même sans données
        globalLoadingProtection.recordSuccess()
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
      
      // MARQUER LE SUCCÈS AVEC CACHE ULTRA-LONG (30 minutes)
      globalLoadingProtection.recordSuccess()
      
      console.log('✅ [ChatStore] État mis à jour - AUCUN autre chargement pendant 30 minutes')
      
    } catch (error) {
      console.error('❌ [ChatStore] Erreur chargement:', error)
      set({ 
        conversations: [],
        conversationGroups: [],
        isLoading: false,
        isLoadingHistory: false
      })
      
      // En cas d'erreur, pas de retry automatique
      globalLoadingProtection.isLoading = false
      console.log('❌ [ChatStore] Erreur - pas de retry, attendre 10 minutes')
      throw error
      
    } finally {
      // UNLOCK DIFFÉRÉ DE 60 SECONDES pour éviter toute race condition
      setTimeout(() => {
        globalLoadingProtection.isLoading = false
        console.log('🔓 [ChatStore] Lock libéré après délai de sécurité')
      }, 60000) // 1 minute de délai de sécurité
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
      
      // Reset complet de la protection
      globalLoadingProtection.forceReset()
      globalLoadingProtection.lastSuccessfulLoad = 0
      
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
    // Reset SEULEMENT pour refresh manuel
    console.log('🔄 [ChatStore] Refresh manuel - Reset protection')
    globalLoadingProtection.forceReset()
    globalLoadingProtection.lastSuccessfulLoad = 0
    
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

// Hooks utilitaires
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