'use client'

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { useRouter } from 'next/navigation'
import { Message } from '../../types'
import { useAuthStore } from '@/lib/stores/auth'
import { useTranslation } from './hooks/useTranslation'
import { useChatStore } from './hooks/useChatStore'
import { generateAIResponse } from './services/apiService'
import { conversationService } from './services/conversationService'

import {
  PaperAirplaneIcon,
  UserIcon,
  PlusIcon,
  InteliaLogo,
  ArrowDownIcon,
  ThumbUpIcon,
  ThumbDownIcon,
} from './utils/icons'
import { HistoryMenu } from './components/HistoryMenu'
import { UserMenuButton } from './components/UserMenuButton'
import { ZohoSalesIQ } from './components/ZohoSalesIQ'
import { FeedbackModal } from './components/modals/FeedbackModal'

// Circuit breaker global pour éviter les boucles infinies de chargement - CODE ORIGINAL CONSERVÉ
class PageLoadingCircuitBreaker {
  private attempts = 0
  private lastAttempt = 0
  private readonly MAX_ATTEMPTS = 3
  private readonly RESET_INTERVAL = 30000 // 30 secondes

  canAttempt(): boolean {
    const now = Date.now()
    
    // Reset après interval
    if (now - this.lastAttempt > this.RESET_INTERVAL) {
      this.attempts = 0
    }

    if (this.attempts >= this.MAX_ATTEMPTS) {
      console.warn('Circuit breaker: trop de tentatives de chargement, arrêt temporaire')
      return false
    }

    return true
  }

  recordAttempt(): void {
    this.attempts++
    this.lastAttempt = Date.now()
    console.log(`Circuit breaker: tentative chargement ${this.attempts}/${this.MAX_ATTEMPTS}`)
  }

  recordSuccess(): void {
    this.attempts = 0
    console.log('Circuit breaker: reset après succès chargement')
  }

  recordFailure(): void {
    console.log(`Circuit breaker: échec chargement ${this.attempts}/${this.MAX_ATTEMPTS}`)
  }

  reset(): void {
    this.attempts = 0
    this.lastAttempt = 0
    console.log('Circuit breaker: reset manuel')
  }
}

// Instance globale du circuit breaker pour la page - CODE ORIGINAL CONSERVÉ
const pageLoadingBreaker = new PageLoadingCircuitBreaker()

// 🛠️ CORRECTION MAJEURE : Composant ChatInput isolé avec React.memo
const ChatInput = React.memo(({ 
  inputMessage, 
  setInputMessage, 
  onSendMessage, 
  isLoadingChat, 
  clarificationState,
  isMobileDevice,
  inputRef,
  t 
}: {
  inputMessage: string
  setInputMessage: (value: string) => void
  onSendMessage: () => void
  isLoadingChat: boolean
  clarificationState: any
  isMobileDevice: boolean
  inputRef: React.RefObject<HTMLInputElement>
  t: (key: string) => string
}) => {
  return (
    <div className={`flex items-center min-h-[48px] w-full ${isMobileDevice ? 'mobile-input-container' : 'space-x-3'}`}>
      <div className={`flex-1 ${isMobileDevice ? 'mobile-input-wrapper' : ''}`}>
        <input
          ref={inputRef}
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              onSendMessage()
            }
          }}
          placeholder={clarificationState ? "Répondez à la question ci-dessus..." : t('chat.placeholder')}
          className={`w-full h-12 px-4 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm flex items-center ${isMobileDevice ? 'ios-input-fix' : ''}`}
          disabled={isLoadingChat}
          aria-label={t('chat.placeholder')}
          style={{
            fontSize: isMobileDevice ? '16px' : '14px',
            WebkitAppearance: 'none',
            borderRadius: isMobileDevice ? '25px' : '9999px'
          }}
        />
      </div>

      <button
        onClick={onSendMessage}
        disabled={isLoadingChat || !inputMessage.trim()}
        className={`flex-shrink-0 h-12 w-12 flex items-center justify-center text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors rounded-full hover:bg-blue-50 ${isMobileDevice ? 'mobile-send-button' : ''}`}
        title={isLoadingChat ? 'Envoi en cours...' : 'Envoyer le message'}
        aria-label={isLoadingChat ? 'Envoi en cours...' : 'Envoyer le message'}
        style={{
          minWidth: '48px',
          width: '48px',
          height: '48px'
        }}
      >
        <PaperAirplaneIcon />
      </button>
    </div>
  )
})

ChatInput.displayName = 'ChatInput'

// 🛠️ CORRECTION MAJEURE : Composant MessageList isolé avec React.memo
const MessageList = React.memo(({ 
  processedMessages, 
  isLoadingChat, 
  handleFeedbackClick, 
  getUserInitials, 
  user,
  t
}: {
  processedMessages: any[]
  isLoadingChat: boolean
  handleFeedbackClick: (messageId: string, feedback: 'positive' | 'negative') => void
  getUserInitials: (user: any) => string
  user: any
  t: (key: string) => string
}) => {
  // 🛠️ CORRECTION : Mémoisation des composants de messages pour éviter les re-rendus
  const messageComponents = useMemo(() => {
    return processedMessages.map((message, index) => (
      <div key={`${message.id}-${index}`}>
        <div className={`flex items-start space-x-3 min-w-0 ${message.isUser ? 'justify-end' : 'justify-start'}`}>
          {!message.isUser && (
            <div className="flex-shrink-0 w-10 h-10 grid place-items-center">
              <InteliaLogo className="h-8 w-auto" />
            </div>
          )}

          <div className={`px-3 sm:px-4 py-2 rounded-2xl max-w-[85%] sm:max-w-none break-words ${message.isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-white border border-gray-200 text-gray-900'}`}>
            {message.isUser ? (
              <p className="whitespace-pre-wrap leading-relaxed text-sm">
                {message.content}
              </p>
            ) : (
              <ReactMarkdown
                className="prose prose-sm max-w-none break-words prose-p:my-3 prose-li:my-1 prose-ul:my-4 prose-strong:text-gray-900 prose-headings:font-bold prose-headings:text-gray-900"
                components={{
                  h2: ({node, ...props}) => (
                    <h2 className="text-xl font-bold text-blue-900 mt-8 mb-6 border-b-2 border-blue-200 pb-3 bg-blue-50 px-4 py-2 rounded-t-lg" {...props} />
                  ),
                  h3: ({node, ...props}) => (
                    <h3 className="text-lg font-semibold text-gray-800 mt-6 mb-4 border-l-4 border-blue-400 pl-4 bg-gray-50 py-2" {...props} />
                  ),
                  p: ({node, ...props}) => (
                    <p className="leading-relaxed text-gray-800 my-4 text-justify" {...props} />
                  ),
                  ul: ({node, ...props}) => (
                    <ul className="list-disc list-outside space-y-3 text-gray-800 my-6 ml-6 pl-2" {...props} />
                  ),
                  li: ({node, ...props}) => (
                    <li className="leading-relaxed pl-2 my-2" {...props} />
                  ),
                  strong: ({node, ...props}) => (
                    <strong className="font-bold text-blue-800 bg-blue-50 px-1 rounded" {...props} />
                  ),
                  table: ({node, ...props}) => (
                    <div className="overflow-x-auto my-6 -mx-1 sm:mx-0">
                      <table className="min-w-full border border-gray-300 rounded-lg shadow-sm" {...props} />
                    </div>
                  ),
                  th: ({node, ...props}) => (
                    <th className="border border-gray-300 px-4 py-3 bg-blue-100 font-bold text-left text-blue-900" {...props} />
                  ),
                  td: ({node, ...props}) => (
                    <td className="border border-gray-300 px-4 py-3 hover:bg-gray-50" {...props} />
                  ),
                }}
              >
                {message.processedContent}
              </ReactMarkdown>
            )}
          </div>

          {!message.isUser &&
          index > 0 &&
          message.conversation_id && (
            <div className="flex items-center space-x-2 mt-2 ml-2">
              <button
                onClick={() => handleFeedbackClick(message.id, 'positive')}
                className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${
                  message.feedback === 'positive' ? 'text-green-600 bg-green-50' : 'text-gray-400'
                }`}
                title={t('chat.helpfulResponse')}
                aria-label={t('chat.helpfulResponse')}
              >
                <ThumbUpIcon />
              </button>
              <button
                onClick={() => handleFeedbackClick(message.id, 'negative')}
                className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${
                  message.feedback === 'negative' ? 'text-red-600 bg-red-50' : 'text-gray-400'
                }`}
                title={t('chat.notHelpfulResponse')}
                aria-label={t('chat.notHelpfulResponse')}
              >
                <ThumbDownIcon />
              </button>

              {message.feedback && (
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-gray-500">
                    Merci pour votre retour !
                  </span>
                  {message.feedbackComment && (
                    <span className="text-xs text-blue-600" title={`Commentaire: ${message.feedbackComment}`}>
                      💬
                    </span>
                  )}
                </div>
              )}
            </div>
          )}

          {message.isUser && (
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
              <span className="text-white text-sm font-medium">
                {getUserInitials(user)}
              </span>
            </div>
          )}
        </div>
      </div>
    ))
  }, [processedMessages, handleFeedbackClick, getUserInitials, user, t])

  return (
    <>
      {processedMessages.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <div className="text-sm">Aucun message à afficher</div>
        </div>
      ) : (
        messageComponents
      )}

      {isLoadingChat && (
        <div className="flex items-start space-x-3">
          <div className="w-10 h-10 grid place-items-center flex-shrink-0">
            <InteliaLogo className="h-8 w-auto" />
          </div>
          <div className="bg-white border border-gray-200 rounded-2xl px-3 sm:px-4 py-3 max-w-[85%] sm:max-w-none break-words">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        </div>
      )}
    </>
  )
})

MessageList.displayName = 'MessageList'

export default function ChatInterface() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading, hasHydrated, initializeSession } = useAuthStore()
  const { t, currentLanguage } = useTranslation()

  const currentConversation = useChatStore(state => state.currentConversation)
  const conversationsCount = useChatStore(state => state.conversations.length)
  const setCurrentConversation = useChatStore(state => state.setCurrentConversation)
  const addMessage = useChatStore(state => state.addMessage)
  const updateMessage = useChatStore(state => state.updateMessage)
  const createNewConversation = useChatStore(state => state.createNewConversation)

  // Default config for now since we can't see the original hook - CODE ORIGINAL CONSERVÉ
  const config = { level: 'standard' }

  const [inputMessage, setInputMessage] = useState('')
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const [isMobileDevice, setIsMobileDevice] = useState(false)
  const [showConcisionSettings, setShowConcisionSettings] = useState(false)

  // NOUVEAUX ÉTATS pour gestion clavier mobile - CODE ORIGINAL CONSERVÉ
  const [keyboardHeight, setKeyboardHeight] = useState(0)
  const [isKeyboardVisible, setIsKeyboardVisible] = useState(false)
  const [viewportHeight, setViewportHeight] = useState(0)

  // États existants inchangés - CODE ORIGINAL CONSERVÉ
  const [clarificationState, setClarificationState] = useState<{
    messageId: string
    originalQuestion: string
    clarificationQuestions: string[]
  } | null>(null)

  const [shouldAutoScroll, setShouldAutoScroll] = useState(true)
  const [isUserScrolling, setIsUserScrolling] = useState(false)
  const [showScrollButton, setShowScrollButton] = useState(false)

  const [feedbackModal, setFeedbackModal] = useState<{
    isOpen: boolean
    messageId: string | null
    feedbackType: 'positive' | 'negative' | null
  }>({
    isOpen: false,
    messageId: null,
    feedbackType: null
  })
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const lastMessageCountRef = useRef(0)
  const isMountedRef = useRef(true)
  
  // Nouveaux refs pour contrôler la redirection avec délai - CODE ORIGINAL CONSERVÉ
  const redirectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const authCheckTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  
  // Refs pour éviter les re-chargements multiples et contrôler les tentatives - CODE ORIGINAL CONSERVÉ
  const hasLoadedConversationsRef = useRef(false)
  const loadingTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const conversationLoadingAttemptsRef = useRef(0)

  // NOUVEAU REF pour l'input mobile - CODE ORIGINAL CONSERVÉ
  const inputRef = useRef<HTMLInputElement>(null)

  // 🛠️ CORRECTION CRITIQUE : Mémoisation stable des données pour éviter les re-rendus
  const messages: Message[] = useMemo(() => {
    return currentConversation?.messages || []
  }, [currentConversation?.messages])

  const hasMessages = useMemo(() => {
    return messages.length > 0
  }, [messages.length])

  // 🛠️ CORRECTION : Log de debug CONDITIONNEL pour éviter le spam
  const debugRenderCount = useRef(0)
  useMemo(() => {
    debugRenderCount.current++
    // Ne loguer que les 5 premiers rendus, puis tous les 10 rendus
    if (debugRenderCount.current <= 5 || debugRenderCount.current % 10 === 0) {
      console.log(`🔄 [ChatInterface] Rendu #${debugRenderCount.current}:`, {
        messages_count: messages.length,
        clarification_active: !!clarificationState,
        concision: config.level,
        input_length: inputMessage.length
      })
    }
  }, [messages.length, clarificationState, config.level, inputMessage.length])

  // 🛠️ CORRECTION : Mémoisation des fonctions pour éviter les re-créations
  const handleAuthError = useCallback((error: any) => {
    console.log('🔧 [Auth] Gestion erreur auth:', error)
    
    if (error?.status === 403 || 
        error?.message?.includes('Auth session missing') ||
        error?.message?.includes('Forbidden')) {
      
      console.log('🔄 [Auth] Session expirée détectée, redirection')
      handleRedirectToLogin('Session expirée')
    }
  }, []) // Pas de dépendances pour éviter les re-créations

  // 🛠️ CORRECTION : Fonction de redirection stable
  const handleRedirectToLogin = useCallback((reason: string = 'Session expirée') => {
    console.log('🔄 [Auth] Redirection vers login:', reason)
    
    // Nettoyer tous les timeouts
    if (redirectTimeoutRef.current) clearTimeout(redirectTimeoutRef.current)
    if (authCheckTimeoutRef.current) clearTimeout(authCheckTimeoutRef.current)
    
    // Méthode 1: Tentative avec Next.js router
    try {
      console.log('🔄 [Auth] Tentative redirection via router')
      router.push('/')
      
      // Fallback de sécurité au cas où router.push ne fonctionne pas
      setTimeout(() => {
        if (window.location.pathname === '/chat') {
          console.log('🔄 [Auth] Router.push a échoué, utilisation window.location')
          window.location.href = '/'
        }
      }, 1000)
      
    } catch (error) {
      console.error('🔧 [Auth] Erreur redirection router, fallback immédiat')
      window.location.href = '/'
    }
  }, [router])

  // FONCTION UTILITAIRE : Extraire les initiales de l'utilisateur - CODE ORIGINAL CONSERVÉ
  const getUserInitials = useCallback((user: any): string => {
    if (!user) return 'U'

    // Essayer depuis le nom complet
    if (user.name) {
      const names = user.name.trim().split(' ')
      if (names.length >= 2) {
        return (names[0][0] + names[names.length - 1][0]).toUpperCase()
      }
      return names[0][0].toUpperCase()
    }

    // Essayer depuis l'email
    if (user.email) {
      const emailPart = user.email.split('@')[0]
      if (emailPart.includes('.')) {
        const parts = emailPart.split('.')
        return (parts[0][0] + parts[1][0]).toUpperCase()
      }
      return emailPart.substring(0, 2).toUpperCase()
    }

    return 'U'
  }, [])

  // FONCTION RENFORCÉE : Préprocesseur Markdown pour réparer le formatage cassé - CODE ORIGINAL CONSERVÉ
  const preprocessMarkdown = useCallback((content: string): string => {
    if (!content) return ""

    let processed = content

    // Réparer les titres collés au texte suivant
    processed = processed.replace(/(#{1,6})\s*([^#\n]+?)([A-Z][a-z])/g, '$1 $2\n\n$3')

    // Ajouter saut de ligne après tous les titres si manquant
    processed = processed.replace(/^(#{1,6}[^\n]+)(?!\n)/gm, '$1\n')

    // Séparer les mots collés par une virgule manquante
    processed = processed.replace(/([a-z])([A-Z])/g, '$1, $2')

    // Réparer les phrases collées après ponctuation
    processed = processed.replace(/([.!?:])([A-Z])/g, '$1 $2')

    // Ajouter espaces avant les mots importants en gras
    processed = processed.replace(/([a-z])(\*\*[A-Z])/g, '$1 $2')

    // Séparer les sections importantes collées
    processed = processed.replace(/([.!?:])\s*(\*\*[^*]+\*\*)/g, '$1\n\n$2')

    // Structure en sections avec ### pour sous-parties
    processed = processed.replace(/([.!?:])\s*-\s*([A-Z][^:]+:)/g, '$1\n\n### $2')

    // Améliorer la structure des listes
    processed = processed.replace(/([.!?:])\s*-\s*([A-Z][^-]+)/g, '$1\n\n- $2')

    // Ajouter espacement avant les listes
    processed = processed.replace(/([^.\n])\n([•\-\*]\s)/g, '$1\n\n$2')

    // Ajouter espacement après les listes
    processed = processed.replace(/([•\-\*]\s[^\n]+)\n([A-Z][^•\-\*])/g, '$1\n\n$2')

    // Gérer les sections spéciales
    processed = processed.replace(/(Causes Possibles|Recommandations|Prévention|Court terme|Long terme|Immédiat)([^-:])/g, '\n\n### $1\n\n$2')

    // Normaliser les espaces multiples
    processed = processed.replace(/[ \t]+/g, ' ')

    // Éviter les triples sauts de ligne
    processed = processed.replace(/\n\n\n+/g, '\n\n')

    // Supprimer espaces en début/fin
    processed = processed.trim()

    return processed
  }, [])

  // 🛠️ CORRECTION : Mémoisation stable du contenu traité
  const processedMessages = useMemo(() => {
    return messages.map(message => ({
      ...message,
      processedContent: message.isUser ? message.content : preprocessMarkdown(message.content)
    }))
  }, [messages, preprocessMarkdown])

  // FONCTION ÉTENDUE : Nettoyer le texte de réponse - CODE ORIGINAL CONSERVÉ avec mémoisation
  const cleanResponseText = useCallback((text: string): string => {
    if (!text) return ""

    // Ne pas nettoyer les réponses courtes PerfStore
    if (text.length < 100) {
      console.log('[cleanResponseText] Réponse courte protégée:', text)
      return text.trim()
    }

    let cleaned = text

    // Retirer toutes les références aux sources
    cleaned = cleaned.replace(/\*\*Source:\s*[^*]+\*\*/g, '')
    cleaned = cleaned.replace(/\*\*ource:\s*[^*]+\*\*/g, '')
    cleaned = cleaned.replace(/\*\*Source[^*]*\*\*/g, '')
    cleaned = cleaned.replace(/Source:\s*[^\n]+/g, '')

    // Retirer les longs passages de texte technique des PDFs
    cleaned = cleaned.replace(/protection, regardless of the species involved[^.]+\./g, '')
    cleaned = cleaned.replace(/bird ages, from the adverse effects[^.]+\./g, '')
    cleaned = cleaned.replace(/oocyst production reaches a maximum[^.]+\./g, '')
    cleaned = cleaned.replace(/oocyst production begins to diminish[^.]+\./g, '')
    cleaned = cleaned.replace(/oocyst production ceases[^.]+\./g, '')
    cleaned = cleaned.replace(/immunosuppressive response after[^.]+\./g, '')

    // Retirer les fragments de phrases coupées
    cleaned = cleaned.replace(/^[a-z][^.]+\.\.\./gm, '')

    // Retirer les fragments techniques génériques
    cleaned = cleaned.replace(/ould be aware of local legislation[^.]+\./g, '')
    cleaned = cleaned.replace(/Apply your knowledge and judgment[^.]+\./g, '')

    // Nettoyer les tableaux mal formatés
    cleaned = cleaned.replace(/Age \(days\) Weight \(lb\)[^|]+\|[^|]+\|/g, '')

    // Retirer les répétitions de mots coupés
    cleaned = cleaned.replace(/\b\w{1,3}\.\.\./g, '')

    // Retirer les phrases qui se terminent abruptement par ---
    cleaned = cleaned.replace(/[^.!?]+---\s*/g, '')

    // Retirer les numérotations orphelines
    cleaned = cleaned.replace(/^\d+\.\s+[A-Z][^:]+:\s*$/gm, '')
    cleaned = cleaned.replace(/^\w\.\s+[A-Z][^:]+:\s*$/gm, '')

    // En-têtes "INTRODUCTION", "Cobb MX" et variants
    cleaned = cleaned.replace(/^INTRODUCTION[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Introduction[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Cobb MX[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^COBB MX[^\n]*$/gm, '')

    // En-têtes techniques génériques en majuscules
    cleaned = cleaned.replace(/^[A-Z\s]{10,}:?\s*$/gm, '')
    cleaned = cleaned.replace(/^[A-Z][A-Z\s]+GUIDE[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^[A-Z][A-Z\s]+MANUAL[^\n]*$/gm, '')

    // Tableaux mal formattés
    cleaned = cleaned.replace(/\|\s*Age\s*\|\s*Weight[^|]*\|[^\n]*\n/g, '')
    cleaned = cleaned.replace(/\|\s*Days\s*\|\s*Grams[^|]*\|[^\n]*\n/g, '')

    // Fragments de PDF mal parsés
    cleaned = cleaned.replace(/[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}/g, '')
    cleaned = cleaned.replace(/\b[A-Z]\.[A-Z]\.[A-Z]\./g, '')
    cleaned = cleaned.replace(/Page\s+\d+\s+of\s+\d+/gi, '')

    // Références bibliographiques orphelines
    cleaned = cleaned.replace(/^\([^)]+\)\s*$/gm, '')
    cleaned = cleaned.replace(/^et\s+al\.[^\n]*$/gm, '')

    // Codes et identifiants techniques
    cleaned = cleaned.replace(/\b[A-Z]{2,}\-[0-9]+\b/g, '')
    cleaned = cleaned.replace(/\b[0-9]{4,}\-[0-9]{2,}\b/g, '')
    cleaned = cleaned.replace(/\bDOI:\s*[^\s]+/gi, '')

    // Normaliser les espaces multiples
    cleaned = cleaned.replace(/\s+/g, ' ')
    cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n')
    cleaned = cleaned.replace(/\n\s*\n/g, '\n\n')

    // Retirer les lignes vides en début et fin
    cleaned = cleaned.replace(/^\s*\n+/, '')
    cleaned = cleaned.replace(/\n+\s*$/, '')

    return cleaned.trim()
  }, [])

  // 🛠️ CORRECTION : Fonction de chargement des conversations avec dépendances stables
  const loadConversationsWithBreaker = useCallback(async (userId: string) => {
    // Vérification du circuit breaker
    if (!pageLoadingBreaker.canAttempt()) {
      console.warn('[loadConversationsWithBreaker] Circuit breaker actif - chargement bloqué')
      return
    }

    // Vérification que c'est déjà fait
    if (hasLoadedConversationsRef.current) {
      console.log('[loadConversationsWithBreaker] Conversations déjà chargées, skip')
      return
    }

    pageLoadingBreaker.recordAttempt()
    conversationLoadingAttemptsRef.current++

    try {
      console.log(`[loadConversationsWithBreaker] Tentative ${conversationLoadingAttemptsRef.current} pour:`, userId)
      
      // Appel direct via useChatStore.getState()
      await useChatStore.getState().loadConversations(userId)
      
      // Marquer comme chargé avec succès
      hasLoadedConversationsRef.current = true
      conversationLoadingAttemptsRef.current = 0
      pageLoadingBreaker.recordSuccess()
      
      console.log('[loadConversationsWithBreaker] Conversations chargées avec succès')
      
    } catch (error) {
      pageLoadingBreaker.recordFailure()
      console.error(`[loadConversationsWithBreaker] Tentative ${conversationLoadingAttemptsRef.current} échouée:`, error)
      
      // Nouvelle logique : Gestion des erreurs auth
      handleAuthError(error)
      
      // Reset le flag pour permettre une nouvelle tentative
      hasLoadedConversationsRef.current = false
      
      // Si trop de tentatives, arrêter complètement
      if (conversationLoadingAttemptsRef.current >= 3) {
        console.error('[loadConversationsWithBreaker] Abandon après 3 tentatives')
        hasLoadedConversationsRef.current = true
      }
      
      throw error
    }
  }, [handleAuthError])

  // 🛠️ CORRECTION MAJEURE : useEffect pour auth backend avec dépendances stables
  useEffect(() => {
    // Vérifier si on a déjà initialisé pour éviter les boucles
    let isInitializing = false
    
    const initAuth = async () => {
      if (isInitializing || !hasHydrated) return
      isInitializing = true
      
      console.log('🔐 [Auth] Initialisation auth backend')
      
      try {
        const sessionValid = await initializeSession()
        
        if (!sessionValid && isMountedRef.current) {
          console.log('❌ [Auth] Session invalide, redirection')
          handleRedirectToLogin('Session expirée')
        } else {
          console.log('✅ [Auth] Session valide')
        }
      } catch (error) {
        console.error('❌ [Auth] Erreur initialisation:', error)
        if (isMountedRef.current) {
          handleAuthError(error)
        }
      } finally {
        isInitializing = false
      }
    }
    
    // ✅ CORRECTION : Ne pas initialiser si l'utilisateur vient de se déconnecter
    if (hasHydrated && isAuthenticated !== false) {
      initAuth()
    }
  }, [hasHydrated, isAuthenticated, initializeSession, handleRedirectToLogin, handleAuthError])

  // ✅ CORRECTION : useEffect pour gérer la déconnexion avec dépendances stables
  useEffect(() => {
    // Si l'utilisateur n'est plus authentifié et que le store a été hydraté
    if (hasHydrated && isAuthenticated === false && !isLoading) {
      console.log('🔄 [Auth] Déconnexion détectée, redirection immédiate')
      handleRedirectToLogin('Déconnexion')
    }
  }, [hasHydrated, isAuthenticated, isLoading, handleRedirectToLogin])

  // 🛠️ CORRECTION : useEffect pour gestion clavier mobile avec cleanup approprié
  useEffect(() => {
    if (!isMobileDevice) return

    let initialViewportHeight = window.visualViewport?.height || window.innerHeight
    setViewportHeight(initialViewportHeight)
    
    const handleViewportChange = () => {
      if (window.visualViewport) {
        const currentHeight = window.visualViewport.height
        const heightDifference = initialViewportHeight - currentHeight
        
        setViewportHeight(currentHeight)
        
        // Si la différence est significative (> 150px), le clavier est probablement ouvert
        if (heightDifference > 150) {
          setIsKeyboardVisible(true)
          setKeyboardHeight(heightDifference)
          
          // Ajouter classe pour CSS
          document.body.classList.add('keyboard-open')
          
          // Scroll automatique vers le bas quand le clavier s'ouvre
          setTimeout(() => {
            if (messagesEndRef.current && isMountedRef.current) {
              messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" })
            }
          }, 100)
        } else {
          setIsKeyboardVisible(false)
          setKeyboardHeight(0)
          
          // Retirer classe CSS
          document.body.classList.remove('keyboard-open')
        }
      }
    }

    // Fallback pour les anciens navigateurs iOS
    const handleResize = () => {
      const currentHeight = window.innerHeight
      const heightDifference = initialViewportHeight - currentHeight
      
      setViewportHeight(currentHeight)
      
      if (heightDifference > 150) {
        setIsKeyboardVisible(true)
        setKeyboardHeight(heightDifference)
        document.body.classList.add('keyboard-open')
      } else {
        setIsKeyboardVisible(false)
        setKeyboardHeight(0)
        document.body.classList.remove('keyboard-open')
      }
    }

    // Écouter les changements de viewport (iOS 13+)
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', handleViewportChange)
    } else {
      // Fallback pour iOS plus anciens
      window.addEventListener('resize', handleResize)
    }

    // Focus/blur sur l'input pour détecter le clavier
    const inputElement = inputRef.current
    
    const handleFocus = () => {
      setIsKeyboardVisible(true)
      document.body.classList.add('keyboard-open')
      
      setTimeout(() => {
        if (messagesEndRef.current && isMountedRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" })
        }
      }, 300) // Délai pour laisser le clavier s'ouvrir
    }

    const handleBlur = () => {
      // Délai avant de cacher pour éviter les flickers
      setTimeout(() => {
        if (isMountedRef.current) {
          setIsKeyboardVisible(false)
          setKeyboardHeight(0)
          document.body.classList.remove('keyboard-open')
        }
      }, 100)
    }

    if (inputElement) {
      inputElement.addEventListener('focus', handleFocus)
      inputElement.addEventListener('blur', handleBlur)
    }

    return () => {
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', handleViewportChange)
      } else {
        window.removeEventListener('resize', handleResize)
      }
      
      // Nettoyer classe CSS
      document.body.classList.remove('keyboard-open')
      
      if (inputElement) {
        inputElement.removeEventListener('focus', handleFocus)
        inputElement.removeEventListener('blur', handleBlur)
      }
    }
  }, [isMobileDevice])

  // 🛠️ CORRECTION : useEffect de montage avec cleanup complet
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      // Nettoyer TOUS les timeouts
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current)
      }
      if (redirectTimeoutRef.current) {
        clearTimeout(redirectTimeoutRef.current)
      }
      if (authCheckTimeoutRef.current) {
        clearTimeout(authCheckTimeoutRef.current)
      }
    }
  }, [])

  // 🛠️ CORRECTION : Détection de device mobile avec dépendances stables
  useEffect(() => {
    const detectMobileDevice = () => {
      const userAgent = navigator.userAgent.toLowerCase()
      const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent)
      const isTabletScreen = window.innerWidth <= 1024
      const hasTouchScreen = 'ontouchstart' in window || navigator.maxTouchPoints > 0
      const isIPadOS = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1
      const isDesktopTouchscreen = window.innerWidth > 1200 && navigator.maxTouchPoints > 0 && !isIPadOS

      return (isMobileUA || isIPadOS || (isTabletScreen && hasTouchScreen)) && !isDesktopTouchscreen
    }

    setIsMobileDevice(detectMobileDevice())

    const handleResize = () => {
      if (isMountedRef.current) {
        setIsMobileDevice(detectMobileDevice())
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // 🛠️ CORRECTION : Auto-scroll avec dépendances optimisées
  useEffect(() => {
    if (isMountedRef.current && messages.length > lastMessageCountRef.current && shouldAutoScroll && !isUserScrolling) {
      const scrollTimeout = setTimeout(() => {
        if (isMountedRef.current) {
          messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
        }
      }, 100)
      
      return () => clearTimeout(scrollTimeout)
    }

    lastMessageCountRef.current = messages.length
  }, [messages.length, shouldAutoScroll, isUserScrolling])

  // 🛠️ CORRECTION : Gestion du scroll avec cleanup approprié
  useEffect(() => {
    const chatContainer = chatContainerRef.current
    if (!chatContainer) return

    let scrollTimeout: NodeJS.Timeout
    let isScrolling = false

    const handleScroll = () => {
      if (!isMountedRef.current) return

      const { scrollTop, scrollHeight, clientHeight } = chatContainer
      const isAtBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 50
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100

      if (!isScrolling) {
        setIsUserScrolling(true)
        isScrolling = true
      }

      setShowScrollButton(!isNearBottom && messages.length > 3)

      if (isAtBottom) {
        setShouldAutoScroll(true)
      } else {
        setShouldAutoScroll(false)
      }

      clearTimeout(scrollTimeout)
      scrollTimeout = setTimeout(() => {
        if (isMountedRef.current) {
          setIsUserScrolling(false)
          isScrolling = false
        }
      }, 150)
    }

    chatContainer.addEventListener('scroll', handleScroll, { passive: true })
    return () => {
      chatContainer.removeEventListener('scroll', handleScroll)
      clearTimeout(scrollTimeout)
    }
  }, [messages.length])

  // 🛠️ CORRECTION : Gestion du message de bienvenue avec dépendances stables
  useEffect(() => {
    if (isAuthenticated && !currentConversation && !hasMessages && isMountedRef.current) {
      const welcomeMessage: Message = {
        id: 'welcome',
        content: t('chat.welcome'),
        isUser: false,
        timestamp: new Date()
      }

      const welcomeConversation = {
        id: 'welcome',
        title: 'Nouvelle conversation',
        preview: 'Commencez par poser une question',
        message_count: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        language: currentLanguage,
        status: 'active' as const,
        messages: [welcomeMessage]
      }

      setCurrentConversation(welcomeConversation)
      lastMessageCountRef.current = 1
    }
  }, [isAuthenticated, currentConversation, hasMessages, t, currentLanguage, setCurrentConversation])

  // 🛠️ CORRECTION : Update du message de bienvenue avec dépendances stables
  useEffect(() => {
    if (currentConversation?.id === 'welcome' &&
        currentConversation.messages.length === 1 &&
        currentConversation.messages[0].content !== t('chat.welcome') &&
        isMountedRef.current) {

      const updatedMessage: Message = {
        ...currentConversation.messages[0],
        content: t('chat.welcome')
      }

      const updatedConversation = {
        ...currentConversation,
        messages: [updatedMessage]
      }

      setCurrentConversation(updatedConversation)
    }
  }, [currentLanguage, t, currentConversation, setCurrentConversation])

  // 🛠️ CORRECTION MAJEURE : Chargement des conversations avec timeout et dépendances stables
  useEffect(() => {
    if (isAuthenticated && user?.id && isMountedRef.current && !hasLoadedConversationsRef.current) {
      // Nettoyer le timeout précédent si existant
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current)
      }

      loadingTimeoutRef.current = setTimeout(() => {
        if (isMountedRef.current && !hasLoadedConversationsRef.current) {
          console.log('[ChatInterface] Chargement historique pour:', user.email || user.id)
          
          loadConversationsWithBreaker(user.email || user.id)
            .then(() => {
              if (isMountedRef.current) {
                console.log('Historique conversations chargé avec succès')
              }
            })
            .catch(err => {
              if (isMountedRef.current) {
                console.error('Erreur chargement historique:', err)
              }
            })
        }
      }, 800)

      return () => {
        if (loadingTimeoutRef.current) {
          clearTimeout(loadingTimeoutRef.current)
        }
      }
    }
  }, [isAuthenticated, user?.id, loadConversationsWithBreaker])

  // 🛠️ CORRECTION : Reset circuit breaker avec dépendances stables
  useEffect(() => {
    if (user?.id) {
      // Reset les flags et circuit breaker pour un nouvel utilisateur
      hasLoadedConversationsRef.current = false
      conversationLoadingAttemptsRef.current = 0
      pageLoadingBreaker.reset()
      console.log('[ChatInterface] Reset circuit breaker pour nouvel utilisateur:', user.id)
    }
  }, [user?.id])

  // ✅ ÉTATS DE CHARGEMENT CORRIGÉS
  if (isLoading || !hasHydrated) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">{t('chat.loading')}</p>
        </div>
      </div>
    )
  }

  // ✅ GESTION SIMPLIFIÉE DE L'ÉTAT NON-AUTHENTIFIÉ
  if (!isAuthenticated) {
    // Redirection immédiate sans affichage de chargement infini
    handleRedirectToLogin('Non authentifié')
    
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Redirection en cours...</p>
        </div>
      </div>
    )
  }

  // ✅ Vérification SUPPLÉMENTAIRE POUR L'UTILISATEUR
  if (!user) {
    console.log('❌ [Auth] Utilisateur manquant malgré authentification')
    handleRedirectToLogin('Utilisateur manquant')
    
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Redirection vers la connexion...</p>
        </div>
      </div>
    )
  }

  const getCurrentDate = () => {
    return new Date().toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    })
  }

  // FONCTION CORRIGÉE : extractAnswerAndSources avec support validation_rejected - CODE ORIGINAL CONSERVÉ
  const extractAnswerAndSources = (result: any): [string, any[]] => {
    let answerText = ""
    let sources: any[] = []

    console.log('[extractAnswerAndSources] Début extraction:', {
      type: result?.type,
      has_answer: !!result?.answer,
      has_general_answer: !!result?.general_answer
    })

    // Gérer le type "validation_rejected"
    if (result?.type === 'validation_rejected') {
      console.log('[extractAnswerAndSources] Question rejetée par validation agricole')

      let rejectionMessage = result.message || "Cette question ne concerne pas le domaine agricole."

      if (result.validation?.suggested_topics && result.validation.suggested_topics.length > 0) {
        rejectionMessage += "\n\n**Voici quelques sujets que je peux vous aider :**\n"
        result.validation.suggested_topics.forEach((topic: string, index: number) => {
          rejectionMessage += `• ${topic}\n`
        })
      }

      return [rejectionMessage, []]
    }

    // Traiter type "answer" EN PREMIER
    if (result?.type === 'answer' && result?.answer) {
      console.log('[extractAnswerAndSources] Type answer détecté')
      answerText = result.answer.text || ""
      console.log('[extractAnswerAndSources] Answer text extraite:', answerText.substring(0, 100))
      return [answerText, []]
    }

    // Support type "partial_answer"
    if (result?.type === 'partial_answer' && result?.general_answer) {
      console.log('[extractAnswerAndSources] Type partial_answer détecté')
      answerText = result.general_answer.text || ""
      console.log('[extractAnswerAndSources] General answer text extraite:', answerText.substring(0, 100))
      return [answerText, []]
    }

    // Code original pour compatibilité
    const responseContent = result?.response || ""

    if (typeof responseContent === 'object' && responseContent !== null) {
      answerText = String(responseContent.answer || "").trim()
      if (!answerText) {
        answerText = "Désolé, je n'ai pas pu formater la réponse."
      }
    } else {
      answerText = String(responseContent).trim() || "Désolé, je n'ai pas pu formater la réponse."

      if (answerText.includes("'type': 'text'") && answerText.includes("'answer':")) {
        const match = answerText.match(/'answer': "(.+?)"/)
        if (match) {
          answerText = match[1]
            .replace(/\\"/g, '"')
            .replace(/\\n/g, '\n')
            .replace(/\\\\/g, '\\')
        }
      }
    }

    console.log('[extractAnswerAndSources] Résultat final:', answerText.substring(0, 100))
    return [answerText, []]
  }

  // 🛠️ CORRECTION : handleSendMessage avec mémoisation et cleanup
  const handleSendMessage = useCallback(async (text: string = inputMessage) => {
    if (!text.trim() || !isMountedRef.current) return

    console.log('[ChatInterface] Envoi message:', {
      text: text.substring(0, 50) + '...',
      hasClarificationState: !!clarificationState,
      concisionLevel: config.level
    })

    const userMessage: Message = {
      id: Date.now().toString(),
      content: text.trim(),
      isUser: true,
      timestamp: new Date()
    }

    let conversationIdToSend: string | undefined = undefined

    if (currentConversation &&
        currentConversation.id !== 'welcome' &&
        !currentConversation.id.startsWith('temp-')) {
      conversationIdToSend = currentConversation.id
    }

    addMessage(userMessage)
    setInputMessage('')
    setIsLoadingChat(true)

    setShouldAutoScroll(true)
    setIsUserScrolling(false)

    try {
      let response;

      const optimalLevel = undefined;
      console.log('[handleSendMessage] Niveau optimal détecté:', optimalLevel)

      if (clarificationState) {
        console.log('[handleSendMessage] Mode clarification')

        response = await generateAIResponse(
          clarificationState.originalQuestion + " " + text.trim(),
          user,
          currentLanguage,
          conversationIdToSend,
          optimalLevel,
          true,
          clarificationState.originalQuestion,
          { answer: text.trim() }
        )

        setClarificationState(null)
        console.log('[handleSendMessage] Clarification traitée')

      } else {
        response = await generateAIResponse(
          text.trim(),
          user,
          currentLanguage,
          conversationIdToSend,
          optimalLevel
        )
      }

      if (!isMountedRef.current) return

      console.log('[handleSendMessage] Réponse reçue:', {
        conversation_id: response.conversation_id,
        response_length: response.response?.length || 0,
        versions_received: Object.keys(response.response_versions || {}),
        clarification_requested: response.clarification_result?.clarification_requested || false,
        type: response.type
      })

      const needsClarification = response.clarification_result?.clarification_requested === true

      if (needsClarification) {
        console.log('[handleSendMessage] Clarification demandée')

        const clarificationMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: (response.full_text || response.response) + "\n\nRépondez simplement dans le chat avec les informations demandées.",
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id
        }

        addMessage(clarificationMessage)
        setClarificationState({
          messageId: clarificationMessage.id,
          originalQuestion: text.trim(),
          clarificationQuestions: response.clarification_questions || []
        })

        console.log('[handleSendMessage] État clarification activé')

      } else {
        const [answerText, sources] = extractAnswerAndSources(response)

        console.log('[handleSendMessage] Texte extrait:', {
          length: answerText.length,
          preview: answerText.substring(0, 100),
          empty: !answerText || answerText.trim() === ''
        })

        const cleanedText = cleanResponseText(answerText)

        console.log('[handleSendMessage] Texte nettoyé:', {
          length: cleanedText.length,
          preview: cleanedText.substring(0, 100),
          empty: !cleanedText || cleanedText.trim() === ''
        })

        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: cleanedText || "Erreur: contenu vide",
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id,
          response_versions: response.response_versions,
          originalResponse: response.response
        }

        console.log('[handleSendMessage] Message AI créé:', {
          id: aiMessage.id,
          content_length: aiMessage.content.length,
          content_preview: aiMessage.content.substring(0, 100),
          has_versions: !!aiMessage.response_versions
        })

        addMessage(aiMessage)
        console.log('[handleSendMessage] Message ajouté avec versions:', Object.keys(response.response_versions || {}))
      }

    } catch (error) {
      console.error('[handleSendMessage] Erreur:', error)

      // NOUVELLE LOGIQUE : Gestion des erreurs auth
      handleAuthError(error)

      if (isMountedRef.current) {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: error instanceof Error ? error.message : t('chat.errorMessage'),
          isUser: false,
          timestamp: new Date()
        }
        addMessage(errorMessage)
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoadingChat(false)
      }
    }
  }, [inputMessage, clarificationState, config.level, currentConversation, addMessage, user, currentLanguage, t, handleAuthError, cleanResponseText])

  // 🛠️ CORRECTION : Fonctions de feedback avec mémoisation
  const handleFeedbackClick = useCallback((messageId: string, feedback: 'positive' | 'negative') => {
    if (!isMountedRef.current) return

    setFeedbackModal({
      isOpen: true,
      messageId,
      feedbackType: feedback
    })
  }, [])

  const handleFeedbackSubmit = useCallback(async (feedback: 'positive' | 'negative', comment?: string) => {
    const { messageId } = feedbackModal
    if (!messageId || !isMountedRef.current) return

    const message = messages.find(msg => msg.id === messageId)
    if (!message || !message.conversation_id) {
      console.warn('Conversation ID non trouvé pour le feedback', messageId)
      return
    }

    setIsSubmittingFeedback(true)
    try {
      updateMessage(messageId, {
        feedback,
        feedbackComment: comment
      })

      const feedbackValue = feedback === 'positive' ? 1 : -1

      try {
        await conversationService.sendFeedback(message.conversation_id, feedbackValue)

        if (comment && comment.trim()) {
          try {
            await conversationService.sendFeedbackComment(message.conversation_id, comment.trim())
          } catch (commentError) {
            console.warn('Commentaire non envoyé (endpoint manquant):', commentError)
          }
        }
      } catch (feedbackError) {
        console.error('Erreur envoi feedback:', feedbackError)
        
        // NOUVELLE LOGIQUE : Gestion des erreurs auth
        handleAuthError(feedbackError)
        
        if (isMountedRef.current) {
          updateMessage(messageId, {
            feedback: null,
            feedbackComment: undefined
          })
        }
        throw feedbackError
      }

    } catch (error) {
      console.error('Erreur générale feedback:', error)
      throw error
    } finally {
      if (isMountedRef.current) {
        setIsSubmittingFeedback(false)
      }
    }
  }, [feedbackModal, messages, updateMessage, handleAuthError])

  const handleFeedbackModalClose = useCallback(() => {
    if (!isMountedRef.current) return

    setFeedbackModal({
      isOpen: false,
      messageId: null,
      feedbackType: null
    })
  }, [])

  const handleNewConversation = useCallback(() => {
    if (!isMountedRef.current) return

    createNewConversation()
    setClarificationState(null)

    const welcomeMessage: Message = {
      id: 'welcome',
      content: t('chat.welcome'),
      isUser: false,
      timestamp: new Date()
    }

    const welcomeConversation = {
      id: 'welcome',
      title: 'Nouvelle conversation',
      preview: 'Commencez par poser une question',
      message_count: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      language: currentLanguage,
      status: 'active' as const,
      messages: [welcomeMessage]
    }

    setCurrentConversation(welcomeConversation)
    lastMessageCountRef.current = 1

    setShouldAutoScroll(true)
    setIsUserScrolling(false)
    setShowScrollButton(false)
  }, [createNewConversation, t, currentLanguage, setCurrentConversation])

  const scrollToBottom = useCallback(() => {
    if (!isMountedRef.current) return

    setShouldAutoScroll(true)
    setIsUserScrolling(false)
    setShowScrollButton(false)
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  // CALCUL des styles dynamiques pour mobile - CODE ORIGINAL CONSERVÉ avec mémoisation
  const containerStyle = useMemo(() => {
    return isMobileDevice ? {
      height: '100vh',
      minHeight: '100vh',
      maxHeight: '100vh'
    } : {}
  }, [isMobileDevice])

  const chatScrollStyle = useMemo(() => {
    return isMobileDevice ? {
      height: isKeyboardVisible 
        ? `calc(100vh - 140px - ${keyboardHeight}px)` 
        : 'calc(100vh - 140px)',
      maxHeight: isKeyboardVisible 
        ? `calc(100vh - 140px - ${keyboardHeight}px)` 
        : 'calc(100vh - 140px)',
      overflow: 'auto',
      paddingBottom: '1rem'
    } : {
      scrollPaddingBottom: '7rem'
    }
  }, [isMobileDevice, isKeyboardVisible, keyboardHeight])

  return (
    <>
      <ZohoSalesIQ user={user} language={currentLanguage} />

      {/* CONTAINER PRINCIPAL avec styles dynamiques mobile - CODE ORIGINAL CONSERVÉ */}
      <div 
        className={`bg-gray-50 flex flex-col ${isMobileDevice ? 'chat-main-container' : 'min-h-dvh h-screen'}`}
        style={containerStyle}
      >

        <header className="bg-white border-b border-gray-100 px-2 sm:px-4 py-3 flex-shrink-0">
          <div className="flex items-center justify-between">
            {/* Gauche – + puis Historique */}
            <div className="flex items-center space-x-2">
              <button
                onClick={handleNewConversation}
                className="w-10 h-10 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-center border border-gray-200"
                title={t('nav.newConversation')}
                aria-label={t('nav.newConversation')}
              >
                <PlusIcon className="w-5 h-5" />
              </button>

              {/* 🛠️ CORRECTION : History avec clé stable pour éviter les re-créations */}
              <div className="header-icon-container history-menu-container">
                <HistoryMenu key="history-stable" />
              </div>
            </div>

            {/* Centre – Logo + Titre */}
            <div className="flex-1 min-w-0 flex justify-center items-center space-x-3">
              <div className="w-10 h-10 grid place-items-center">
                <InteliaLogo className="h-8 w-auto" />
              </div>
              <h1 className="text-lg font-medium text-gray-900 truncate">Intelia Expert</h1>
            </div>

            {/* Droite – Bouton DD */}
            <div className="flex items-center space-x-2">
              {/* 🛠️ CORRECTION : UserMenu avec clé stable pour éviter les re-créations */}
              <div className="header-icon-container user-menu-container">
                <UserMenuButton key="user-stable" />
              </div>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          {/* ZONE CHAT avec styles dynamiques mobile - CODE ORIGINAL CONSERVÉ */}
          <div
            ref={chatContainerRef}
            className={`flex-1 overflow-y-auto px-2 sm:px-4 py-6 pb-28 overscroll-contain ${isMobileDevice ? 'chat-scroll-area' : ''}`}
            style={chatScrollStyle}
          >
            <div className="max-w-full sm:max-w-4xl mx-auto space-y-6 px-2 sm:px-4">
              {hasMessages && (
                <div className="text-center">
                  <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                    {getCurrentDate()}
                  </span>
                </div>
              )}

              {/* 🛠️ CORRECTION MAJEURE : Utilisation du composant MessageList isolé */}
              <MessageList 
                processedMessages={processedMessages}
                isLoadingChat={isLoadingChat}
                handleFeedbackClick={handleFeedbackClick}
                getUserInitials={getUserInitials}
                user={user}
                t={t}
              />

              <div ref={messagesEndRef} />
            </div>
          </div>

          {showScrollButton && (
            <div className="fixed bottom-24 right-8 z-10">
              <button
                onClick={scrollToBottom}
                className="bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 transition-colors"
                title="Revenir en bas"
                aria-label="Revenir en bas de la conversation"
              >
                <ArrowDownIcon />
              </button>
            </div>
          )}

          {/* BARRE DE SAISIE avec correction mobile complète - CODE ORIGINAL CONSERVÉ */}
          <div 
            className={`px-2 sm:px-4 py-2 bg-white border-t border-gray-100 z-20 ${isMobileDevice ? 'chat-input-fixed' : 'sticky bottom-0'}`}
            style={{
              paddingBottom: isMobileDevice 
                ? `calc(env(safe-area-inset-bottom) + 8px)`
                : 'calc(env(safe-area-inset-bottom) + 8px)',
              // Force la position fixed sur mobile quand clavier ouvert
              position: isMobileDevice ? 'fixed' : 'sticky',
              bottom: 0,
              left: 0,
              right: 0,
              backgroundColor: 'white',
              borderTop: '1px solid rgb(243 244 246)',
              zIndex: 1000,
              minHeight: isMobileDevice ? '70px' : 'auto',
              display: 'flex',
              alignItems: 'center',
              // Assurer visibilité avec clavier
              transform: 'translateY(0)',
              visibility: 'visible',
              opacity: 1
            }}
          >
            <div className="max-w-full sm:max-w-4xl lg:max-w-5xl xl:max-w-6xl mx-auto w-full sm:w-[90%] lg:w-[75%] xl:w-[60%]">
              {clarificationState && (
                <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-blue-700 text-sm font-medium">
                      Mode clarification : répondez à la question ci-dessus
                    </span>
                    <button
                      onClick={() => {
                        setClarificationState(null)
                        console.log('[ChatInterface] Clarification annulée')
                      }}
                      className="text-blue-600 hover:text-blue-800 text-sm underline"
                    >
                      Annuler
                    </button>
                  </div>
                </div>
              )}

              {/* 🛠️ CORRECTION MAJEURE : Utilisation du composant ChatInput isolé */}
              <ChatInput
                inputMessage={inputMessage}
                setInputMessage={setInputMessage}
                onSendMessage={handleSendMessage}
                isLoadingChat={isLoadingChat}
                clarificationState={clarificationState}
                isMobileDevice={isMobileDevice}
                inputRef={inputRef}
                t={t}
              />

              <div className="text-center mt-2">
                <p className="text-xs text-gray-500">
                  Intelia Expert peut faire des erreurs. Faites vérifiez les réponses par un professionnel au besoin.
                </p>
              </div>
              
            </div>
          </div>
        </div>
      </div>

      <FeedbackModal
        isOpen={feedbackModal.isOpen}
        onClose={handleFeedbackModalClose}
        onSubmit={handleFeedbackSubmit}
        feedbackType={feedbackModal.feedbackType!}
        isSubmitting={isSubmittingFeedback}
      />
    </>
  )
}