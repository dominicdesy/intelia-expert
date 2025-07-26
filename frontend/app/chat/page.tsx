'use client'

import React, { useState, useEffect, useRef } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

// Instance Supabase
const supabase = createClientComponentClient()

// ==================== STORE D'AUTHENTIFICATION ====================
const useAuthStore = () => {
  const [user, setUser] = useState<any>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadUser = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('❌ Erreur récupération session:', error)
          setIsAuthenticated(false)
          setIsLoading(false)
          return
        }

        if (session?.user) {
          console.log('✅ Utilisateur connecté:', session.user.email)
          
          const userData = {
            id: session.user.id,
            email: session.user.email,
            name: `${session.user.user_metadata?.first_name || ''} ${session.user.user_metadata?.last_name || ''}`.trim() || session.user.email?.split('@')[0],
            firstName: session.user.user_metadata?.first_name || '',
            lastName: session.user.user_metadata?.last_name || '',
            user_type: session.user.user_metadata?.role || 'producer',
            language: 'fr',
            created_at: session.user.created_at,
            plan: 'essentiel'
          }
          
          setUser(userData)
          setIsAuthenticated(true)
        } else {
          console.log('ℹ️ Aucun utilisateur connecté')
          setIsAuthenticated(false)
        }
      } catch (error) {
        console.error('❌ Erreur chargement utilisateur:', error)
        setIsAuthenticated(false)
      } finally {
        setIsLoading(false)
      }
    }

    loadUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('🔄 Changement auth:', event, session?.user?.email)
        
        if (event === 'SIGNED_OUT') {
          setUser(null)
          setIsAuthenticated(false)
        } else if (event === 'SIGNED_IN' && session?.user) {
          loadUser()
        }
      }
    )

    return () => {
      if (subscription?.unsubscribe) {
        subscription.unsubscribe()
      }
    }
  }, [])

  const logout = async () => {
    try {
      console.log('🚪 Déconnexion en cours...')
      const { error } = await supabase.auth.signOut()
      
      if (error) {
        console.error('❌ Erreur déconnexion:', error)
        return
      }
      
      setUser(null)
      setIsAuthenticated(false)
      window.location.href = '/'
    } catch (error) {
      console.error('❌ Erreur critique déconnexion:', error)
    }
  }

  return {
    user,
    isAuthenticated,
    isLoading,
    logout
  }
}

// ==================== TYPES ====================
interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  feedback?: 'positive' | 'negative' | null
}

// ==================== ICÔNES SVG ====================
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

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== MENU UTILISATEUR ====================
const UserMenuButton = () => {
  const { user, logout } = useAuthStore()
  const [isOpen, setIsOpen] = useState(false)

  const userName = user?.name || user?.email || 'Utilisateur'
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
  
  const currentPlan = user?.plan || 'essentiel'
  const planConfig = {
    essentiel: { name: 'Essentiel', bgColor: 'bg-green-50', textColor: 'text-green-600', borderColor: 'border-green-200' },
    pro: { name: 'Pro', bgColor: 'bg-blue-50', textColor: 'text-blue-600', borderColor: 'border-blue-200' },
    entreprise: { name: 'Entreprise', bgColor: 'bg-purple-50', textColor: 'text-purple-600', borderColor: 'border-purple-200' }
  }
  const plan = planConfig[currentPlan as keyof typeof planConfig] || planConfig.essentiel

  return (
    <>
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
                <div className="mt-2">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${plan.bgColor} ${plan.textColor} border ${plan.borderColor}`}>
                    {plan.name}
                  </span>
                </div>
              </div>

              <button
                onClick={() => window.open('https://intelia.com/privacy-policy/', '_blank')}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875v12.75c0 .621.504 1.125 1.125 1.125h2.25" />
                </svg>
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
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
                  </svg>
                  <span>Déconnexion</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}

// ==================== COMPOSANT PRINCIPAL ====================
export default function ChatInterface() {
  const { user, isAuthenticated, isLoading } = useAuthStore()
  
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll automatique
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Message de bienvenue
  useEffect(() => {
    if (isAuthenticated && messages.length === 0) {
      const welcomeMessage: Message = {
        id: '1',
        content: `Bonjour ${user?.name || 'cher utilisateur'} ! Comment puis-je vous aider aujourd'hui ?`,
        isUser: false,
        timestamp: new Date()
      }
      setMessages([welcomeMessage])
    }
  }, [isAuthenticated, messages.length, user?.name])

  // Rediriger si pas connecté
  if (isLoading) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">Chargement...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    window.location.href = '/'
    return null
  }

  // ✅ FONCTION CORRIGÉE - API AUTHENTIFIÉE
  const generateAIResponse = async (question: string): Promise<string> => {
    const apiUrl = 'https://expert-app-cngws.ondigitalocean.app/api/v1/expert/ask'
    
    try {
      console.log('🤖 Envoi question au RAG Intelia (authentifié):', question)
      console.log('📡 URL API sécurisée:', apiUrl)
      
      // ✅ Récupérer le token d'authentification Supabase
      const { data: { session }, error } = await supabase.auth.getSession()
      
      if (error || !session?.access_token) {
        console.error('❌ Pas de session authentifiée:', error)
        throw new Error('Session expirée - veuillez vous reconnecter')
      }
      
      console.log('🎫 Token session récupéré:', session.access_token?.substring(0, 20) + '...')
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          // ✅ Header d'authentification
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          // ✅ Format unifié pour compatibilité
          text: question.trim(),
          question: question.trim(),
          language: user?.language || 'fr',
          speed_mode: 'balanced',
          user_id: user?.id || session.user.id,
          context: `Utilisateur: ${user?.email || session.user.email}`
        })
      })

      console.log('📊 Statut réponse API:', response.status, response.statusText)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Erreur API détaillée:', errorText)
        
        // Gestion spécifique des erreurs d'authentification
        if (response.status === 401) {
          throw new Error('Session expirée - veuillez vous reconnecter')
        } else if (response.status === 403) {
          throw new Error('Accès refusé - permissions insuffisantes')
        } else if (response.status === 422) {
          console.error('❌ Erreur de validation (422):', errorText)
          throw new Error('Format de données incorrect - veuillez réessayer')
        }
        
        throw new Error(`Erreur API: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('✅ Réponse RAG reçue (authentifiée):', data)
      
      const responseText = data.response || data.answer || data.message || data.content
      
      if (responseText) {
        return responseText
      } else {
        console.warn('⚠️ Structure de réponse inattendue:', data)
        return 'Le système RAG a répondu mais dans un format inattendu.'
      }
      
    } catch (error: any) {
      console.error('❌ Erreur lors de l\'appel au RAG authentifié:', error)
      
      // Gestion spécifique des erreurs d'authentification
      if (error.message.includes('authentifié') || error.message.includes('Session expirée')) {
        return `🔐 Erreur d'authentification : ${error.message}

Veuillez actualiser la page ou vous reconnecter.`
      }
      
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        return `Erreur de connexion au serveur RAG sécurisé.

🔧 **Diagnostic suggéré :**
1. Le serveur expert-app-cngws.ondigitalocean.app est-il accessible ?
2. Votre session Supabase est-elle valide ?
3. Y a-t-il des problèmes de CORS avec l'authentification ?

**Erreur technique :** ${error.message}`
      }
      
      return `Erreur technique avec l'API sécurisée : ${error.message}

**URL testée :** ${apiUrl}
**Type d'erreur :** ${error.name}

Consultez la console développeur (F12) pour plus de détails.`
    }
  }

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
    setIsLoadingChat(true)

    try {
      const response = await generateAIResponse(text.trim())
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response,
        isUser: false,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      console.error('❌ Error generating response:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "Désolé, je rencontre un problème technique. Veuillez réessayer dans quelques instants.",
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoadingChat(false)
    }
  }

  // Gestion feedback
  const handleFeedback = (messageId: string, feedback: 'positive' | 'negative') => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, feedback } : msg
    ))
    console.log(`📊 Feedback ${feedback} pour le message ${messageId}`)
  }

  const handleNewConversation = () => {
    setMessages([{
      id: '1',
      content: `Bonjour ${user?.name || 'cher utilisateur'} ! Comment puis-je vous aider aujourd'hui ?`,
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
          {/* Bouton nouvelle conversation à gauche */}
          <div className="flex items-center space-x-2">
            <button
              onClick={handleNewConversation}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              title="Nouvelle conversation"
            >
              <PlusIcon className="w-5 h-5" />
            </button>
          </div>

          {/* Titre centré avec logo */}
          <div className="flex-1 flex justify-center items-center space-x-3">
            <InteliaLogo className="w-8 h-8" />
            <div className="text-center">
              <h1 className="text-lg font-medium text-gray-900">Intelia Expert</h1>
            </div>
          </div>
          
          {/* Avatar utilisateur à droite */}
          <div className="flex items-center">
            <UserMenuButton />
          </div>
        </div>
      </header>

      {/* Zone de messages */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Date */}
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
                    </div>
                    
                    {/* Boutons de feedback */}
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

            {/* Indicateur de frappe */}
            {isLoadingChat && (
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
                title="Enregistrement vocal (bientôt disponible)"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                </svg>
              </button>
              
              <div className="flex-1">
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
                  placeholder="Posez votre question à l'expert..."
                  className="w-full px-4 py-3 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm"
                  disabled={isLoadingChat}
                />
              </div>
              
              <button
                onClick={() => handleSendMessage()}
                disabled={isLoadingChat || !inputMessage.trim()}
                className="flex-shrink-0 p-2 text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors"
              >
                <PaperAirplaneIcon />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}