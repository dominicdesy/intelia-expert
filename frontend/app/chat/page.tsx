'use client'

import React, { useState, useEffect, useRef } from 'react'

// ==================== CONFIGURATION API ====================
const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'https://expert-app-cngws.ondigitalocean.app',
  ENDPOINTS: {
    ASK: '/api/api/v1/expert/ask',
    ASK_PUBLIC: '/api/api/v1/expert/ask-public',
    FEEDBACK: '/api/api/v1/expert/feedback',
    HISTORY: '/api/api/v1/expert/history',
    TOPICS: '/api/api/v1/expert/topics',
    HEALTH: '/api/health'
  },
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 2
}

// ==================== STORES SIMULÉS ====================
const useAuthStore = () => ({
  user: {
    id: '1',
    name: 'Jean Dupont',
    email: 'jean.dupont@exemple.com',
    user_type: 'producer',
    language: 'fr',
    created_at: '2024-01-15',
    consentGiven: true,
    consentDate: new Date('2024-01-15')
  },
  isAuthenticated: true,
  logout: async () => {
    console.log('🚪 Déconnexion en cours...')
    await new Promise(resolve => setTimeout(resolve, 500))
    window.location.href = '/auth/login'
  }
})

const useChatStore = () => ({
  conversations: [
    {
      id: '1',
      title: 'Problème poulets Ross 308',
      messages: [],
      updated_at: '2024-01-20',
      created_at: '2024-01-20'
    }
  ],
  deleteConversation: async (id: string) => {
    console.log('Suppression conversation:', id)
  },
  clearAllConversations: async () => {
    console.log('Suppression toutes conversations')
  }
})

// ==================== TYPES ====================
interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  feedback?: 'positive' | 'negative' | null
  processing_time?: number
  mode?: string
  fallback_used?: boolean
}

interface APIResponse {
  question: string
  response: string
  mode: string
  note?: string
  sources?: Array<any>
  timestamp: string
  processing_time: number
  language: string
  fallback_used?: boolean
}

// ==================== UTILITAIRES API ====================
class APIClient {
  private static async makeRequest(url: string, options: RequestInit = {}): Promise<Response> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT)

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...options.headers
        }
      })

      clearTimeout(timeoutId)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      return response
    } catch (error: any) {
      clearTimeout(timeoutId)
      throw error
    }
  }

  static async askQuestion(question: string, language: string = 'fr'): Promise<APIResponse> {
    const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.ASK_PUBLIC}`
    
    console.log('🤖 Envoi question:', question.substring(0, 50))

    const response = await this.makeRequest(url, {
      method: 'POST',
      body: JSON.stringify({
        text: question.trim(),
        language,
        speed_mode: 'balanced'
      })
    })

    const data = await response.json()
    console.log('✅ Réponse API reçue:', { 
      mode: data.mode, 
      processing_time: data.processing_time,
      fallback_used: data.fallback_used 
    })

    return data
  }

  static async checkHealth(): Promise<boolean> {
    try {
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.HEALTH}`
      const response = await this.makeRequest(url, { method: 'GET' })
      const data = await response.json()
      return data.status === 'healthy'
    } catch (error) {
      console.error('❌ Health check failed:', error)
      return false
    }
  }
}

// ==================== ICÔNES SVG ====================
const PaperAirplaneIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 0 713.27 20.876L5.999 12zm0 0h7.5" />
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

const EllipsisVerticalIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
  </svg>
)

const ThumbUpIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.5c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 712.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 00.322-1.672V3a.75.75 0 01.75-.75A2.25 2.25 0 0116.5 4.5c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 01-2.649 7.521c-.388.482-.987.729-1.605.729H13.48c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 00-1.423-.23H5.904M14.25 9h2.25M5.904 18.75c.083.205.173.405.27.602.398.83 1.169 1.448 2.126 1.448h.386c.114 0 .228-.007.34-.02a4.877 4.877 0 004.2-3.204 4.877 4.877 0 00.258-1.826v-1.25a1.125 1.125 0 00-1.125-1.125H5.904z" />
  </svg>
)

const ThumbDownIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 15h2.25m8.024-9.75c.011.05.028.1.052.148.591 1.2.924 2.55.924 3.977a8.96 8.96 0 01-.999 4.125m.023-8.25c-.076-.365.183-.75.575-.75h.908c.889 0 1.713.518 1.972 1.368.339 1.11.521 2.287.521 3.507 0 1.553-.295 3.036-.831 4.398C20.613 14.547 19.833 15 19 15h-1.053c-.472 0-.745-.556-.5-.96a8.95 8.95 0 00.303-.54m.023-8.25H16.48a4.5 4.5 0 01-1.423-.23l-3.114-1.04a4.5 4.5 0 00-1.423-.23H6.504c-.618 0-1.217.247-1.605.729A11.95 11.95 0 002.25 12c0 .434.023.863.068 1.285C2.427 14.306 3.346 15 4.372 15h3.126c.618 0 .991.724.725 1.282A7.471 7.471 0 007.5 19.5a2.25 2.25 0 002.25 2.25.75.75 0 00.75-.75v-.633c0-.573.11-1.14.322-1.672.304-.76.93-1.33 1.653-1.715a9.04 9.04 0 002.86-2.4c.498-.634 1.226-1.08 2.032-1.08h.384z" />
  </svg>
)

const MicrophoneIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
  </svg>
)

const TrashIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
  </svg>
)

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <div className={`${className} bg-blue-600 rounded-lg flex items-center justify-center`}>
    <span className="text-white font-bold text-xs">I</span>
  </div>
)

// ==================== STATUS SYSTEM ====================
const SystemStatus = ({ isHealthy }: { isHealthy: boolean }) => (
  <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-xs ${
    isHealthy ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
  }`}>
    <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-green-600' : 'bg-red-600'}`} />
    <span>{isHealthy ? 'Système opérationnel' : 'Problème système'}</span>
  </div>
)

// ==================== MENU HISTORIQUE ====================
const HistoryMenu = () => {
  const [isOpen, setIsOpen] = useState(false)
  const { conversations, deleteConversation, clearAllConversations } = useChatStore()

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        title="Historique des conversations"
      >
        <EllipsisVerticalIcon className="w-5 h-5" />
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          <div className="absolute left-0 top-full mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-96 overflow-y-auto">
            <div className="p-4 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">Historique</h3>
                <button
                  onClick={() => {
                    clearAllConversations()
                    setIsOpen(false)
                  }}
                  className="text-red-600 hover:text-red-700 text-sm"
                >
                  Tout effacer
                </button>
              </div>
            </div>
            
            <div className="max-h-64 overflow-y-auto">
              {conversations.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-sm">
                  Aucune conversation précédente
                </div>
              ) : (
                conversations.map((conv) => (
                  <div key={conv.id} className="p-3 hover:bg-gray-50 border-b border-gray-50 last:border-b-0">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {conv.title}
                        </h4>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(conv.updated_at).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                      <button
                        onClick={() => deleteConversation(conv.id)}
                        className="ml-2 p-1 text-gray-400 hover:text-red-600 transition-colors"
                        title="Supprimer"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ==================== MENU UTILISATEUR ====================
const UserMenuButton = () => {
  const { user, logout } = useAuthStore()
  const [isOpen, setIsOpen] = useState(false)

  const userName = user?.name || user?.email || 'Utilisateur'
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)

  const handleContactClick = () => {
    window.open('mailto:support@intelia.com?subject=Support Intelia Expert', '_blank')
    setIsOpen(false)
  }

  const handleUserInfoClick = () => {
    alert(`Informations utilisateur:\n\nNom: ${user?.name}\nEmail: ${user?.email}\nType: ${user?.user_type}\nMembre depuis: ${new Date(user?.created_at || '').toLocaleDateString('fr-FR')}`)
    setIsOpen(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors"
      >
        <span className="text-white text-xs font-medium">{userInitials}</span>
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
            <div className="px-4 py-3 border-b border-gray-100">
              <p className="text-sm font-medium text-gray-900">{user?.name}</p>
              <p className="text-xs text-gray-500">{user?.email}</p>
              <p className="text-xs text-gray-400 mt-1">
                Membre depuis {new Date(user?.created_at || '').toLocaleDateString('fr-FR')}
              </p>
            </div>

            <button
              onClick={handleUserInfoClick}
              className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <span>👤</span>
              <span>Mes informations</span>
            </button>

            <button
              onClick={handleContactClick}
              className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <span>📞</span>
              <span>Nous joindre</span>
            </button>

            <button
              onClick={() => window.open('https://intelia.com/privacy-policy/', '_blank')}
              className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <span>⚖️</span>
              <span>Mentions légales</span>
            </button>
            
            <div className="border-t border-gray-100 mt-2 pt-2">
              <button
                onClick={() => {
                  logout()
                  setIsOpen(false)
                }}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <span>🚪</span>
                <span>Déconnexion</span>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ==================== COMPOSANT PRINCIPAL ====================
export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [systemHealthy, setSystemHealthy] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { user } = useAuthStore()

  // Sujets suggérés
  const suggestedTopics = [
    { label: "About Intelia", color: "bg-blue-100 text-blue-800" },
    { label: "Farm Management", color: "bg-green-100 text-green-800" },
    { label: "Animal Genetics", color: "bg-purple-100 text-purple-800" },
    { label: "Animal Health", color: "bg-red-100 text-red-800" },
    { label: "Animal Nutrition", color: "bg-yellow-100 text-yellow-800" }
  ]

  // Scroll automatique
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Message de bienvenue + Health check
  useEffect(() => {
    const initializeChat = async () => {
      const isHealthy = await APIClient.checkHealth()
      setSystemHealthy(isHealthy)

      const welcomeMessage: Message = {
        id: '1',
        content: "Bonjour ! Je suis votre expert IA en santé et nutrition animale. Comment puis-je vous aider aujourd'hui ?",
        isUser: false,
        timestamp: new Date()
      }
      setMessages([welcomeMessage])
    }

    initializeChat()
  }, [])

  // Envoi message
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
    setIsLoading(true)

    try {
      const startTime = Date.now()
      const result = await APIClient.askQuestion(text.trim(), user?.language || 'fr')
      const processingTime = Date.now() - startTime

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: result.response,
        isUser: false,
        timestamp: new Date(),
        processing_time: result.processing_time || processingTime / 1000,
        mode: result.mode,
        fallback_used: result.fallback_used
      }

      setMessages(prev => [...prev, aiMessage])

    } catch (error: any) {
      console.error('❌ Erreur lors de l\'envoi:', error)
      
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        content: "Désolé, je rencontre un problème technique. Veuillez réessayer.",
        isUser: false,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, errorMsg])
      setSystemHealthy(false)
    } finally {
      setIsLoading(false)
    }
  }

  // Gestion feedback
  const handleFeedback = async (messageId: string, feedback: 'positive' | 'negative') => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, feedback } : msg
    ))
    console.log(`📊 Feedback ${feedback} pour le message ${messageId}`)
  }

  const handleNewConversation = () => {
    setMessages([{
      id: '1',
      content: "Bonjour ! Je suis votre expert IA en santé et nutrition animale. Comment puis-je vous aider aujourd'hui ?",
      isUser: false,
      timestamp: new Date()
    }])
  }

  const getCurrentDate = () => {
    return new Date().toLocaleDateString('fr-FR', { 
      day: 'numeric', 
      month: 'long', 
      year: 'numeric' 
    })
  }

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <HistoryMenu />
            <button
              onClick={handleNewConversation}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              title="Nouvelle conversation"
            >
              <PlusIcon className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 flex justify-center items-center space-x-3">
            <InteliaLogo className="w-8 h-8" />
            <div className="text-center">
              <h1 className="text-lg font-medium text-gray-900">Intelia | Expert</h1>
              <SystemStatus isHealthy={systemHealthy} />
            </div>
          </div>
          
          <div className="flex items-center">
            <UserMenuButton />
          </div>
        </div>
      </header>

      {/* Zone de messages */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length > 0 && (
              <div className="text-center">
                <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                  {getCurrentDate()}
                </span>
              </div>
            )}

            {messages.map((message, index) => (
              <div key={message.id}>
                <div className={`flex items-start space-x-3 ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                  {!message.isUser && (
                    <div className="relative">
                      <InteliaLogo className="w-8 h-8 flex-shrink-0 mt-1" />
                    </div>
                  )}
                  
                  <div className="max-w-xs lg:max-w-2xl">
                    <div className={`px-4 py-3 rounded-2xl ${message.isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-white border border-gray-200 text-gray-900'}`}>
                      <p className="whitespace-pre-wrap leading-relaxed text-sm">
                        {message.content}
                      </p>
                      
                      {!message.isUser && message.processing_time && (
                        <div className="mt-2 text-xs text-gray-500 border-t pt-2">
                          <span>⚡ {message.processing_time}s</span>
                          {message.mode && (
                            <span className="ml-2">🤖 {message.mode}</span>
                          )}
                        </div>
                      )}
                    </div>
                    
                    {!message.isUser && index > 0 && (
                      <div className="flex items-center space-x-2 mt-2 ml-2">
                        <button
                          onClick={() => handleFeedback(message.id, 'positive')}
                          className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${message.feedback === 'positive' ? 'text-green-600 bg-green-50' : 'text-gray-400'}`}
                          title="Réponse utile"
                        >
                          <ThumbUpIcon />
                        </button>
                        <button
                          onClick={() => handleFeedback(message.id, 'negative')}
                          className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${message.feedback === 'negative' ? 'text-red-600 bg-red-50' : 'text-gray-400'}`}
                          title="Réponse non utile"
                        >
                          <ThumbDownIcon />
                        </button>
                        {message.fallback_used && (
                          <span className="text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded-full" title="Système de secours utilisé">
                            🔄 Fallback
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {message.isUser && (
                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                      <UserIcon className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>

                {!message.isUser && index === 0 && (
                  <div className="mt-4 flex flex-wrap gap-2 justify-center">
                    {suggestedTopics.map((topic, topicIndex) => (
                      <button
                        key={topicIndex}
                        onClick={() => handleSendMessage(`Tell me about ${topic.label}`)}
                        className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:opacity-80 ${topic.color}`}
                      >
                        {topic.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex items-start space-x-3">
                <div className="relative">
                  <InteliaLogo className="w-8 h-8 flex-shrink-0 mt-1" />
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
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
            <div className="flex items-center space-x-3">
              <button
                type="button"
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                title="Bientôt disponible"
                disabled
              >
                <MicrophoneIcon />
              </button>
              
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSendMessage()
                    }
                  }}
                  placeholder="Posez votre question…"
                  className="w-full px-4 py-3 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm"
                  disabled={isLoading}
                  maxLength={1000}
                />
              </div>
              
              <button
                onClick={handleSendMessage}
                disabled={isLoading || !inputMessage.trim()}
                className="p-2 text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors"
              >
                <PaperAirplaneIcon />
              </button>
            </div>
            
            <div className="mt-2 text-center">
              <span className="text-xs text-gray-400">
                🔍 Assistant IA spécialisé • API v2.1.0 • {systemHealthy ? '🟢' : '🔴'} Statut système
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}