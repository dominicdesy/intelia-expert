'use client'

import React, { useState, useEffect, useRef } from 'react'

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
    try {
      console.log('🚪 Déconnexion en cours...')
      await new Promise(resolve => setTimeout(resolve, 500))
      window.location.href = '/auth/login'
    } catch (error) {
      console.error('❌ Erreur lors de la déconnexion:', error)
      window.location.href = '/auth/login'
    }
  },
  exportUserData: async () => {
    console.log('Export des données...')
  },
  deleteUserData: async () => {
    console.log('Suppression des données...')
  },
  updateProfile: async (data: any) => {
    console.log('Mise à jour profil:', data)
  }
})

const useChatStore = () => ({
  conversations: [
    {
      id: '1',
      title: 'Problème poulets Ross 308',
      messages: [
        { id: '1', role: 'user', content: 'Mes poulets Ross 308 de 25 jours pèsent 800g, est-ce normal ?' },
        { id: '2', role: 'assistant', content: 'Selon notre base documentaire, pour les poulets Ross 308...' }
      ],
      updated_at: '2024-01-20',
      created_at: '2024-01-20'
    }
  ],
  currentConversation: null,
  loadConversations: () => {},
  loadConversation: async (id: string) => {},
  deleteConversation: async (id: string) => {
    console.log('Suppression conversation:', id)
  },
  clearAllConversations: async () => {
    console.log('Suppression toutes conversations')
  },
  createConversation: () => {}
})

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
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0721.485 12 59.77 0 713.27 20.876L5.999 12zm0 0h7.5" />
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

const TrashIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
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

// ==================== COMPOSANTS MODAL ====================
const Modal = ({ isOpen, onClose, title, children }: {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}) => {
  if (!isOpen) return null

  return (
    <>
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-50" 
        onClick={onClose}
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div 
          className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>
          <div className="p-6">
            {children}
          </div>
        </div>
      </div>
    </>
  )
}

const UserInfoModal = ({ user, onClose }: { user: any, onClose: () => void }) => (
  <div className="space-y-4">
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">Nom complet</label>
      <input
        type="text"
        defaultValue={user?.name}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
      <input
        type="email"
        defaultValue={user?.email}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">Type d'utilisateur</label>
      <select 
        defaultValue={user?.user_type}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="producer">Producteur</option>
        <option value="professional">Professionnel</option>
      </select>
    </div>
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">Langue préférée</label>
      <select 
        defaultValue={user?.language}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="fr">Français</option>
        <option value="en">English</option>
        <option value="es">Español</option>
      </select>
    </div>
    <div className="flex justify-end space-x-3 pt-4">
      <button
        onClick={onClose}
        className="px-4 py-2 text-gray-600 hover:text-gray-800"
      >
        Annuler
      </button>
      <button
        onClick={() => {
          console.log('Sauvegarde des informations utilisateur')
          onClose()
        }}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
      >
        Sauvegarder
      </button>
    </div>
  </div>
)

const ContactModal = ({ onClose }: { onClose: () => void }) => (
  <div className="space-y-6">
    {/* Chat with us */}
    <div className="flex items-start space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors">
      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
        <span className="text-2xl">💬</span>
      </div>
      <div className="flex-1">
        <h3 className="font-semibold text-gray-900 mb-2">Chat with us</h3>
        <p className="text-sm text-gray-600 mb-3">
          Get in touch with our support team via in app chat.
        </p>
        <button 
          onClick={() => {
            console.log('Chat support ouvert')
            onClose()
          }}
          className="text-blue-600 hover:text-blue-700 font-medium text-sm"
        >
          Contact Intelia support
        </button>
      </div>
    </div>

    {/* Call Us */}
    <div className="flex items-start space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors">
      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
        <span className="text-2xl">📞</span>
      </div>
      <div className="flex-1">
        <h3 className="font-semibold text-gray-900 mb-2">Call Us</h3>
        <p className="text-sm text-gray-600 mb-3">
          If you can't find a solution to your problem, call us to talk directly with our support team.
        </p>
        <a 
          href="tel:+18666666221"
          className="text-blue-600 hover:text-blue-700 font-medium text-sm"
        >
          +1 (866) 666 6221
        </a>
      </div>
    </div>

    {/* Email Us */}
    <div className="flex items-start space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors">
      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
        <span className="text-2xl">📧</span>
      </div>
      <div className="flex-1">
        <h3 className="font-semibold text-gray-900 mb-2">Email Us</h3>
        <p className="text-sm text-gray-600 mb-3">
          Send us a detailed message and we'll get back to you as soon as possible.
        </p>
        <a 
          href="mailto:support@intelia.com"
          className="text-blue-600 hover:text-blue-700 font-medium text-sm"
        >
          support@intelia.com
        </a>
      </div>
    </div>

    {/* Visit our website */}
    <div className="flex items-start space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors">
      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
        <span className="text-2xl">🌐</span>
      </div>
      <div className="flex-1">
        <h3 className="font-semibold text-gray-900 mb-2">Visit our website</h3>
        <p className="text-sm text-gray-600 mb-3">
          To know more about us and the Intelia platform, visit our website.
        </p>
        <a 
          href="https://www.intelia.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-700 font-medium text-sm"
        >
          www.intelia.com
        </a>
      </div>
    </div>

    {/* Hours */}
    <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
      <h4 className="font-medium text-blue-900 mb-2">Support Hours</h4>
      <p className="text-sm text-blue-700">
        Monday - Friday: 9:00 AM - 5:00 PM (EST)<br/>
        Saturday - Sunday: Closed
      </p>
    </div>

    <div className="flex justify-end pt-4">
      <button
        onClick={onClose}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
      >
        Close
      </button>
    </div>
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
  const [showUserInfoModal, setShowUserInfoModal] = useState(false)
  const [showContactModal, setShowContactModal] = useState(false)

  const userName = user?.name || user?.email || 'Utilisateur'
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)

  const handleContactClick = () => {
    setIsOpen(false)
    setShowContactModal(true)
  }

  const handleUserInfoClick = () => {
    setIsOpen(false)
    setShowUserInfoModal(true)
  }

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

      {/* Modals */}
      <Modal
        isOpen={showUserInfoModal}
        onClose={() => setShowUserInfoModal(false)}
        title="Mes informations"
      >
        <UserInfoModal user={user} onClose={() => setShowUserInfoModal(false)} />
      </Modal>

      <Modal
        isOpen={showContactModal}
        onClose={() => setShowContactModal(false)}
        title="Nous joindre"
      >
        <ContactModal onClose={() => setShowContactModal(false)} />
      </Modal>
    </>
  )
}

// ==================== COMPOSANT PRINCIPAL ====================
export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { user } = useAuthStore()

  // Scroll automatique
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Message de bienvenue
  useEffect(() => {
    const welcomeMessage: Message = {
      id: '1',
      content: "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
      isUser: false,
      timestamp: new Date()
    }
    setMessages([welcomeMessage])
  }, [])

  // Générer réponse RAG
  const generateAIResponse = async (question: string): Promise<string> => {
    try {
      console.log('🤖 Envoi question au RAG Intelia:', question)
      
      // Utiliser l'URL de l'API depuis les variables d'environnement
      const apiUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/expert/ask`
      console.log('📡 URL API:', apiUrl)
      
      // Headers avec authentification Supabase
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      }
      
      // Ajouter le token Supabase pour l'authentification
      const supabaseToken = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
      if (supabaseToken) {
        headers['Authorization'] = `Bearer ${supabaseToken}`
        console.log('🔑 Token Supabase ajouté pour authentification')
      }
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          question: question.trim(),
          user_id: user?.id || 'demo_user',
          language: user?.language || 'fr',
          context: {
            user_type: user?.user_type || 'producer',
            timestamp: new Date().toISOString()
          }
        })
      })

      console.log('📊 Statut réponse API:', response.status, response.statusText)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Erreur API détaillée:', errorText)
        
        if (response.status === 403) {
          throw new Error(`Authentification requise. Vérifiez que le token Supabase est correct. Status: ${response.status}`)
        }
        
        throw new Error(`Erreur API: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('✅ Réponse RAG reçue:', data)
      
      if (data.answer || data.response || data.message) {
        return data.answer || data.response || data.message
      } else {
        console.warn('⚠️ Structure de réponse inattendue:', data)
        return 'Le système RAG a répondu mais dans un format inattendu.'
      }
      
    } catch (error: any) {
      console.error('❌ Erreur lors de l\'appel au RAG:', error)
      
      if (error.message.includes('403')) {
        return `🔒 **Problème d'authentification avec l'API**

**Solutions possibles :**
1. Vérifiez que les variables d'environnement sont bien configurées
2. Le token Supabase est-il valide dans votre API ?
3. L'API attend-elle un autre type d'authentification ?

**Variables d'environnement :**
- NEXT_PUBLIC_API_URL: ${process.env.NEXT_PUBLIC_API_URL || 'NON DÉFINIE'}
- Token Supabase: ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? 'PRÉSENT' : 'MANQUANT'}

**Erreur détaillée :** ${error.message}`
      }
      
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        return `Erreur de connexion au serveur RAG. 

🔧 **Vérifications suggérées :**
- Le serveur ${process.env.NEXT_PUBLIC_API_URL || 'DigitalOcean'} est-il accessible ?
- Y a-t-il des problèmes de CORS ?
- Le service est-il en cours d'exécution ?

**Erreur technique :** ${error.message}`
      }
      
      return `Erreur technique avec l'API : ${error.message}

**URL testée :** ${process.env.NEXT_PUBLIC_API_URL}/api/v1/expert/ask
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
    setIsLoading(true)

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
      setIsLoading(false)
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
      content: "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
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
          {/* Boutons à gauche */}
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
                title="Enregistrement vocal"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                </svg>
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
                  placeholder="Bonjour ! Comment puis-je vous aider aujourd'hui ?"
                  className="w-full px-4 py-3 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm"
                  disabled={isLoading}
                />
              </div>
              
              <button
                onClick={() => handleSendMessage()}
                disabled={isLoading || !inputMessage.trim()}
                className="p-2 text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors"
              >
                <PaperAirplaneIcon />
              </button>
            </div>
            
            {/* Indicateur RAG en bas */}
            <div className="mt-2 text-center">
              <span className="text-xs text-gray-400">
                🔍 Assistant IA spécialisé en santé et nutrition animale
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}