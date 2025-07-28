'use client'

import React, { useState, useEffect, useRef } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

// Instance Supabase
const supabase = createClientComponentClient()

// ==================== TYPES ÉTENDUS POUR LOGGING ====================
interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  feedback?: 'positive' | 'negative' | null
  conversation_id?: string
}

interface ExpertApiResponse {
  question: string
  response: string
  conversation_id: string
  rag_used: boolean
  rag_score?: number
  timestamp: string
  language: string
  response_time_ms: number
  mode: string
  user?: string
}

interface ConversationData {
  user_id: string
  question: string
  response: string
  conversation_id: string
  confidence_score?: number
  response_time_ms?: number
  language?: string
  rag_used?: boolean
}

// ==================== SERVICE DE LOGGING ====================
class ConversationService {
  private baseUrl = "https://expert-app-cngws.ondigitalocean.app/api/v1"
  private loggingEnabled = true

  async saveConversation(data: ConversationData): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('📝 Logging désactivé - conversation non sauvegardée:', data.conversation_id)
      return
    }

    try {
      console.log('💾 Sauvegarde conversation:', data.conversation_id)
      
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
    }
  }

  async sendFeedback(conversationId: string, feedback: 1 | -1): Promise<void> {
    if (!this.loggingEnabled) return

    try {
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
      throw error
    }
  }

  async getUserConversations(userId: string, limit = 50): Promise<any[]> {
    if (!this.loggingEnabled) return []

    try {
      const response = await fetch(`${this.baseUrl}/logging/user/${userId}/conversations?limit=${limit}`, {
        headers: { 'Accept': 'application/json' }
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      return data.conversations || []
      
    } catch (error) {
      console.error('❌ Erreur récupération conversations:', error)
      return []
    }
  }

  async deleteConversation(conversationId: string): Promise<void> {
    if (!this.loggingEnabled) return

    try {
      const response = await fetch(`${this.baseUrl}/logging/conversation/${conversationId}`, {
        method: 'DELETE',
        headers: { 'Accept': 'application/json' }
      })
      
      if (!response.ok && response.status !== 404) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }
      
    } catch (error) {
      console.error('❌ Erreur suppression conversation:', error)
      throw error
    }
  }

  async clearAllUserConversations(userId: string): Promise<void> {
    if (!this.loggingEnabled) return

    try {
      const response = await fetch(`${this.baseUrl}/logging/user/${userId}/conversations`, {
        method: 'DELETE',
        headers: { 'Accept': 'application/json' }
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }
      
    } catch (error) {
      console.error('❌ Erreur suppression conversations:', error)
      throw error
    }
  }
}

const conversationService = new ConversationService()

// ==================== FONCTION API SÉCURISÉE ====================
const generateAIResponseSecure = async (question: string, user: any): Promise<ExpertApiResponse> => {
  const apiUrl = 'https://expert-app-cngws.ondigitalocean.app/api/v1/expert/ask'
  
  try {
    console.log('🔐 Envoi question sécurisée:', question)
    
    // Récupérer le token JWT
    const { data: { session }, error: sessionError } = await supabase.auth.getSession()
    
    if (sessionError) {
      throw new Error(`🔐 Erreur d'authentification: ${sessionError.message}`)
    }
    
    if (!session || !session.access_token) {
      throw new Error(`🔐 Session expirée. Veuillez vous reconnecter.`)
    }
    
    // Vérifier et rafraîchir le token si nécessaire
    try {
      const tokenPayload = JSON.parse(atob(session.access_token.split('.')[1]))
      const expiryTime = tokenPayload.exp * 1000
      const timeUntilExpiry = expiryTime - Date.now()
      
      if (timeUntilExpiry < 0) {
        throw new Error('Token expiré')
      }
      
      if (timeUntilExpiry < 5 * 60 * 1000) {
        const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession()
        
        if (refreshError || !refreshData.session) {
          throw new Error('Impossible de rafraîchir la session')
        }
        
        session.access_token = refreshData.session.access_token
      }
      
    } catch (tokenError) {
      throw new Error(`🔐 Token invalide: ${tokenError}`)
    }
    
    const requestBody = {
      text: question.trim(),
      language: user?.language || 'fr',
      speed_mode: 'balanced'
    }
    
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Authorization': `Bearer ${session.access_token}`
    }
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(requestBody)
    })

    if (response.status === 401) {
      throw new Error(`🔐 Session expirée (401). Veuillez vous reconnecter.`)
    }
    
    if (response.status === 403) {
      throw new Error(`🔐 Accès refusé (403). Permissions insuffisantes.`)
    }

    if (response.status === 429) {
      throw new Error(`⏱️ Limite de requêtes dépassée. Attendez quelques minutes.`)
    }

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`❌ Erreur serveur (${response.status}): ${errorText}`)
    }

    const data = await response.json()
    
    const adaptedResponse: ExpertApiResponse = {
      question: data.question || question,
      response: data.response || "Réponse reçue mais vide",
      conversation_id: data.conversation_id || Date.now().toString(),
      rag_used: data.rag_used || false,
      rag_score: data.rag_score,
      timestamp: data.timestamp || new Date().toISOString(),
      language: data.language || 'fr',
      response_time_ms: data.response_time_ms || 0,
      mode: data.mode || 'secure_mode',
      user: data.user
    }
    
    // Sauvegarde sécurisée
    if (user && adaptedResponse.conversation_id) {
      try {
        await conversationService.saveConversation({
          user_id: user.id,
          question: question,
          response: adaptedResponse.response,
          conversation_id: adaptedResponse.conversation_id,
          confidence_score: adaptedResponse.rag_score,
          response_time_ms: adaptedResponse.response_time_ms,
          language: adaptedResponse.language,
          rag_used: adaptedResponse.rag_used
        })
      } catch (saveError) {
        console.warn('⚠️ Erreur sauvegarde:', saveError)
      }
    }
    
    return adaptedResponse
    
  } catch (error: any) {
    console.error('❌ Erreur API sécurisée:', error)
    
    if (error.message.includes('Failed to fetch')) {
      throw new Error(`🌐 Erreur de connexion au serveur sécurisé. Vérifiez votre connexion internet.`)
    }
    
    if (error.message.includes('🔐') || error.message.includes('❌') || error.message.includes('⏱️')) {
      throw error
    }
    
    throw new Error(`❌ Erreur technique: ${error.message}`)
  }
}

// ==================== HOOK SESSION SÉCURISÉE ====================
const useSecureSessionCheck = () => {
  const [sessionValid, setSessionValid] = useState(true)
  const [sessionExpiry, setSessionExpiry] = useState<number | null>(null)
  const [lastCheck, setLastCheck] = useState(Date.now())
  
  const checkSession = async (): Promise<boolean> => {
    try {
      const { data: { session }, error } = await supabase.auth.getSession()
      
      if (error || !session || !session.access_token) {
        setSessionValid(false)
        setSessionExpiry(null)
        return false
      }
      
      try {
        const tokenPayload = JSON.parse(atob(session.access_token.split('.')[1]))
        const expiryTime = tokenPayload.exp * 1000
        const timeUntilExpiry = expiryTime - Date.now()
        
        setSessionExpiry(expiryTime)
        
        if (timeUntilExpiry < 0) {
          setSessionValid(false)
          return false
        }
        
        if (timeUntilExpiry < 5 * 60 * 1000) {
          const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession()
          
          if (refreshError || !refreshData.session) {
            setSessionValid(false)
            return false
          }
          
          const newTokenPayload = JSON.parse(atob(refreshData.session.access_token.split('.')[1]))
          setSessionExpiry(newTokenPayload.exp * 1000)
        }
        
      } catch (tokenError) {
        setSessionValid(false)
        setSessionExpiry(null)
        return false
      }
      
      setSessionValid(true)
      setLastCheck(Date.now())
      return true
      
    } catch (error) {
      setSessionValid(false)
      setSessionExpiry(null)
      return false
    }
  }
  
  useEffect(() => {
    const interval = setInterval(() => {
      if (Date.now() - lastCheck > 2 * 60 * 1000) {
        checkSession()
      }
    }, 30 * 1000)
    
    return () => clearInterval(interval)
  }, [lastCheck])
  
  const getTimeUntilExpiry = () => {
    if (!sessionExpiry) return null
    const timeLeft = sessionExpiry - Date.now()
    return timeLeft > 0 ? timeLeft : 0
  }
  
  return { 
    sessionValid, 
    sessionExpiry,
    timeUntilExpiry: getTimeUntilExpiry(),
    checkSession,
    lastCheck: new Date(lastCheck)
  }
}

// ==================== TRANSLATIONS ====================
const translations = {
  fr: {
    'chat.welcome': 'Bonjour ! Comment puis-je vous aider aujourd\'hui ?',
    'chat.placeholder': 'Posez votre question à l\'expert...',
    'chat.loading': 'Chargement...',
    'chat.errorMessage': 'Désolé, je rencontre un problème technique. Veuillez réessayer dans quelques instants.',
    'chat.helpfulResponse': 'Réponse utile',
    'chat.notHelpfulResponse': 'Réponse non utile',
    'chat.voiceRecording': 'Enregistrement vocal (bientôt disponible)',
    'chat.noConversations': 'Aucune conversation',
    'chat.secureMode': 'Mode sécurisé actif',
    'chat.sessionExpiry': 'Session expire dans',
    'nav.newConversation': 'Nouvelle conversation',
    'nav.history': 'Historique',
    'nav.clearAll': 'Tout effacer',
    'nav.profile': 'Profil',
    'nav.contact': 'Contact',
    'nav.legal': 'Mentions légales',
    'nav.logout': 'Déconnexion',
    'nav.language': 'Langue'
  }
}

const useTranslation = () => {
  const [currentLanguage, setCurrentLanguage] = useState('fr')
  
  const t = (key: string): string => {
    return translations[currentLanguage as keyof typeof translations]?.[key as keyof typeof translations['fr']] || key
  }
  
  const changeLanguage = (lang: string) => {
    setCurrentLanguage(lang)
    localStorage.setItem('intelia_language', lang)
    window.dispatchEvent(new Event('languageChanged'))
  }
  
  useEffect(() => {
    const savedLang = localStorage.getItem('intelia_language')
    if (savedLang && translations[savedLang as keyof typeof translations]) {
      setCurrentLanguage(savedLang)
    }
  }, [])

  useEffect(() => {
    const handleLanguageChange = () => {
      const savedLang = localStorage.getItem('intelia_language')
      if (savedLang && savedLang !== currentLanguage) {
        setCurrentLanguage(savedLang)
      }
    }

    window.addEventListener('languageChanged', handleLanguageChange)
    return () => window.removeEventListener('languageChanged', handleLanguageChange)
  }, [currentLanguage])
  
  return { t, changeLanguage, currentLanguage }
}

// ==================== STORE AUTH ====================
const useAuthStore = () => {
  const [user, setUser] = useState<any>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadUser = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          setIsAuthenticated(false)
          setIsLoading(false)
          return
        }

        if (session?.user) {
          const userData = {
            id: session.user.id,
            email: session.user.email,
            name: session.user.email?.split('@')[0],
            language: session.user.user_metadata?.language || 'fr'
          }
          
          setUser(userData)
          setIsAuthenticated(true)
        } else {
          setIsAuthenticated(false)
        }
      } catch (error) {
        setIsAuthenticated(false)
      } finally {
        setIsLoading(false)
      }
    }

    loadUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === 'SIGNED_OUT') {
          setUser(null)
          setIsAuthenticated(false)
        } else if (event === 'SIGNED_IN' && session?.user) {
          loadUser()
        }
      }
    )

    return () => {
      subscription?.unsubscribe?.()
    }
  }, [])

  const logout = async () => {
    try {
      const { error } = await supabase.auth.signOut()
      if (error) return
      
      setUser(null)
      setIsAuthenticated(false)
      window.location.href = '/'
    } catch (error) {
      console.error('Erreur déconnexion:', error)
    }
  }

  return { user, isAuthenticated, isLoading, logout }
}

// ==================== STORE CHAT ====================
interface ConversationItem {
  id: string
  title: string
  messages: Array<{ id: string; role: string; content: string }>
  updated_at: string
  created_at: string
  feedback?: number | null
}

const useChatStore = () => {
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const loadConversations = async (userId: string) => {
    if (!userId) return
    setIsLoading(true)
    
    try {
      const userConversations = await conversationService.getUserConversations(userId, 100)
      
      if (!userConversations || userConversations.length === 0) {
        setConversations([])
        return
      }
      
      const formattedConversations: ConversationItem[] = userConversations.map(conv => ({
        id: conv.conversation_id || conv.id || Date.now().toString(),
        title: conv.question?.length > 50 ? conv.question.substring(0, 50) + '...' : conv.question || 'Conversation sans titre',
        messages: [
          { id: `${conv.conversation_id}-q`, role: 'user', content: conv.question || 'Question non disponible' },
          { id: `${conv.conversation_id}-a`, role: 'assistant', content: conv.response || 'Réponse non disponible' }
        ],
        updated_at: conv.updated_at || conv.timestamp || new Date().toISOString(),
        created_at: conv.timestamp || conv.created_at || new Date().toISOString(),
        feedback: conv.feedback || null
      }))
      
      const sortedConversations = formattedConversations.sort((a, b) => 
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      
      setConversations(sortedConversations)
      
    } catch (error) {
      setConversations([])
    } finally {
      setIsLoading(false)
    }
  }

  const addConversation = (conversationId: string, question: string, response: string) => {
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
    
    setConversations(prev => [newConversation, ...prev])
  }

  return { conversations, isLoading, loadConversations, addConversation }
}

// ==================== ICÔNES ====================
const PaperAirplaneIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0 1 21.485 12 59.77 59.77 0 0 1 3.27 20.876L5.999 12zm0 0h7.5" />
  </svg>
)

const UserIcon = ({ className = "w-8 h-8" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
  </svg>
)

const PlusIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
  </svg>
)

const ThumbUpIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
  </svg>
)

const ThumbDownIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.43a2 2 0 00-1.106-1.79l-.05-.025A4 4 0 0011.057 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
  </svg>
)

const ShieldCheckIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.623 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
  </svg>
)

const InteliaLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== COMPOSANT PRINCIPAL ====================
export default function ChatInterface() {
  const { user, isAuthenticated, isLoading } = useAuthStore()
  const { t, currentLanguage } = useTranslation()
  const { addConversation } = useChatStore()
  const { sessionValid, timeUntilExpiry, checkSession } = useSecureSessionCheck()
  
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    if (isAuthenticated) {
      const welcomeMessage: Message = {
        id: '1',
        content: t('chat.welcome'),
        isUser: false,
        timestamp: new Date()
      }
      
      if (messages.length === 0) {
        setMessages([welcomeMessage])
      }
    }
  }, [isAuthenticated, t])

  if (isLoading) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">{t('chat.loading')}</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    useEffect(() => {
      window.location.href = '/'
    }, [])
    
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">Redirection...</p>
        </div>
      </div>
    )
  }

  const handleSendMessage = async (text: string = inputMessage) => {
    if (!text.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: text.trim(),
      isUser: true,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoadingChat(true)

    try {
      const response = await generateAIResponseSecure(text.trim(), user)
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.response,
        isUser: false,
        timestamp: new Date(),
        conversation_id: response.conversation_id
      }

      setMessages(prev => [...prev, aiMessage])
      
      if (user && response.conversation_id) {
        addConversation(response.conversation_id, text.trim(), response.response)
      }
      
    } catch (error) {
      const errorContent = error instanceof Error ? error.message : t('chat.errorMessage')
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: errorContent,
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoadingChat(false)
    }
  }

  const handleFeedback = async (messageId: string, feedback: 'positive' | 'negative') => {
    const message = messages.find(msg => msg.id === messageId)
    
    if (!message?.conversation_id) {
      alert('Impossible d\'enregistrer le feedback - ID de conversation manquant')
      return
    }

    try {
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, feedback } : msg
      ))

      const feedbackValue = feedback === 'positive' ? 1 : -1
      await conversationService.sendFeedback(message.conversation_id, feedbackValue)
      
    } catch (error) {
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, feedback: null } : msg
      ))
      alert('Erreur lors de l\'envoi du feedback. Veuillez réessayer.')
    }
  }

  const formatTimeLeft = (milliseconds: number) => {
    const minutes = Math.floor(milliseconds / (1000 * 60))
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`
    }
    return `${minutes}m`
  }

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setMessages([{
                id: '1',
                content: t('chat.welcome'),
                isUser: false,
                timestamp: new Date()
              }])}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              title={t('nav.newConversation')}
            >
              <PlusIcon className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 flex justify-center items-center space-x-3">
            <InteliaLogo className="w-8 h-8" />
            <div className="text-center">
              <h1 className="text-lg font-medium text-gray-900">Intelia Expert</h1>
              <div className="flex items-center justify-center space-x-1 mt-1">
                <ShieldCheckIcon className="w-3 h-3 text-green-600" />
                <span className="text-xs text-green-600 font-medium">Mode Sécurisé</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center">
            <button
              onClick={() => {}}
              className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors"
            >
              <span className="text-white text-xs font-medium">
                {user?.name?.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2) || 'U'}
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* Zone de messages */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Indicateur de sécurité */}
            {!sessionValid ? (
              <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-3 mb-4">
                <div className="flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
                  </svg>
                  <div>
                    <span className="font-medium">🔐 Session expirée</span>
                    <p className="text-sm mt-1">Veuillez vous reconnecter pour continuer.</p>
                  </div>
                </div>
              </div>
            ) : timeUntilExpiry && timeUntilExpiry < 10 * 60 * 1000 ? (
              <div className="bg-orange-100 border-l-4 border-orange-500 text-orange-700 p-3 mb-4">
                <div className="flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
                  </svg>
                  <div>
                    <span className="font-medium">⚠️ Session expire bientôt</span>
                    <p className="text-sm mt-1">
                      Session expire dans {formatTimeLeft(timeUntilExpiry)}. Sera rafraîchie automatiquement.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-green-100 border-l-4 border-green-500 text-green-700 p-2 mb-4">
                <div className="flex items-center">
                  <ShieldCheckIcon className="w-4 h-4 mr-2" />
                  <span className="text-sm font-medium">Mode sécurisé actif</span>
                  {timeUntilExpiry && (
                    <span className="text-xs ml-2 opacity-75">
                      • Session valide {formatTimeLeft(timeUntilExpiry)}
                    </span>
                  )}
                </div>
              </div>
            )}
            
            {/* Date */}
            {messages.length > 0 && (
              <div className="text-center">
                <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                  {new Date().toLocaleDateString('fr-FR', { 
                    day: 'numeric', 
                    month: 'long', 
                    year: 'numeric' 
                  })}
                  <span className="ml-2 text-green-600">🔐 API Sécurisée</span>
                </span>
              </div>
            )}

            {messages.map((message, index) => (
              <div key={message.id}>
                <div className={`flex items-start space-x-3 ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                  {!message.isUser && (
                    <div className="relative">
                      <InteliaLogo className="w-8 h-8 flex-shrink-0 mt-1" />
                      <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-600 rounded-full flex items-center justify-center">
                        <ShieldCheckIcon className="w-2.5 h-2.5 text-white" />
                      </div>
                    </div>
                  )}
                  
                  <div className="max-w-xs lg:max-w-2xl">
                    <div className={`px-4 py-3 rounded-2xl ${message.isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-white border border-gray-200 text-gray-900'}`}>
                      <p className="whitespace-pre-wrap leading-relaxed text-sm">
                        {message.content}
                      </p>
                    </div>
                    
                    {!message.isUser && index > 0 && message.conversation_id && (
                      <div className="flex items-center space-x-2 mt-2 ml-2">
                        <button
                          onClick={() => handleFeedback(message.id, 'positive')}
                          className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${message.feedback === 'positive' ? 'text-green-600 bg-green-50' : 'text-gray-400'}`}
                          title={t('chat.helpfulResponse')}
                          disabled={message.feedback !== null}
                        >
                          <ThumbUpIcon />
                        </button>
                        <button
                          onClick={() => handleFeedback(message.id, 'negative')}
                          className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${message.feedback === 'negative' ? 'text-red-600 bg-red-50' : 'text-gray-400'}`}
                          title={t('chat.notHelpfulResponse')}
                          disabled={message.feedback !== null}
                        >
                          <ThumbDownIcon />
                        </button>
                        {message.feedback && (
                          <span className="text-xs text-gray-500 ml-2">
                            Merci pour votre retour !
                          </span>
                        )}
                        <div className="flex items-center space-x-1 ml-2">
                          <ShieldCheckIcon className="w-3 h-3 text-green-600" />
                          <span className="text-xs text-green-600">Authentifié</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {message.isUser && (
                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                      <UserIcon className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoadingChat && (
              <div className="flex items-start space-x-3">
                <div className="relative">
                  <InteliaLogo className="w-8 h-8 flex-shrink-0 mt-1" />
                  <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-600 rounded-full flex items-center justify-center">
                    <ShieldCheckIcon className="w-2.5 h-2.5 text-white" />
                  </div>
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-xs text-green-600 font-medium">API Sécurisée</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Zone de saisie */}
        <div className="px-4 py-4 bg-white border-t border-gray-100">
          <div className="max-w-4xl mx-auto">
            {!sessionValid && (
              <div className="mb-3 text-center">
                <span className="text-xs text-red-600 bg-red-50 px-3 py-1 rounded-full border border-red-200">
                  ⚠️ Session expirée - Reconnexion requise
                </span>
              </div>
            )}
            
            <div className="flex items-center space-x-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      if (sessionValid) {
                        handleSendMessage()
                      } else {
                        alert('Session expirée. Veuillez vous reconnecter.')
                      }
                    }
                  }}
                  placeholder={sessionValid ? t('chat.placeholder') : 'Session expirée - Reconnexion requise'}
                  className={`w-full px-4 py-3 bg-gray-100 border-0 rounded-full focus:ring-2 focus:bg-white outline-none text-sm pr-12 ${
                    sessionValid 
                      ? 'focus:ring-blue-500' 
                      : 'bg-red-50 text-red-500 placeholder-red-400 focus:ring-red-500'
                  }`}
                  disabled={isLoadingChat || !sessionValid}
                />
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  {sessionValid ? (
                    <div title="API Sécurisée Active">
                      <ShieldCheckIcon className="w-4 h-4 text-green-600" />
                    </div>
                  ) : (
                    <div title="Session Expirée">
                      <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
                      </svg>
                    </div>
                  )}
                </div>
              </div>
              
              <button
                onClick={() => sessionValid ? handleSendMessage() : checkSession()}
                disabled={isLoadingChat || (!sessionValid && Boolean(inputMessage.trim()))}
                className={`flex-shrink-0 p-2 transition-colors ${
                  sessionValid 
                    ? 'text-blue-600 hover:text-blue-700 disabled:text-gray-300'
                    : 'text-red-600 hover:text-red-700'
                }`}
                title={sessionValid ? 'Envoyer' : 'Vérifier la session'}
              >
                {sessionValid ? (
                  <PaperAirplaneIcon />
                ) : (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l9.004-9.003m8.015 8.983a9.956 9.956 0 01-1.6 3.18c-.913 1.21-2.094 2.19-3.428 2.846a9.959 9.959 0 01-4.061.823c-2.649 0-5.106-.993-6.96-2.847m2.068-13.252a9.957 9.957 0 013.18-1.6 9.959 9.959 0 014.061-.823c2.649 0 5.106.993 6.96 2.847l1.6 1.6" />
                  </svg>
                )}
              </button>
            </div>
            
            <div className="mt-2 text-center">
              <span className={`text-xs px-2 py-1 rounded-full ${
                sessionValid 
                  ? 'text-green-600 bg-green-50' 
                  : 'text-red-600 bg-red-50'
              }`}>
                {sessionValid 
                  ? '🔐 Connexion sécurisée active' 
                  : '⚠️ Session expirée - Reconnexion requise'
                }
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}