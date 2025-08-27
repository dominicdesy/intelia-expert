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

// Circuit breaker global pour éviter les boucles infinies de chargement
class PageLoadingCircuitBreaker {
  private attempts = 0
  private lastAttempt = 0
  private readonly MAX_ATTEMPTS = 3
  private readonly RESET_INTERVAL = 30000 // 30 secondes

  canAttempt(): boolean {
    const now = Date.now()
    
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

// Instance globale du circuit breaker pour la page
const pageLoadingBreaker = new PageLoadingCircuitBreaker()

// Circuit breaker pour les re-renders
class RenderCircuitBreaker {
  private renderCount = 0
  private lastReset = Date.now()
  private readonly MAX_RENDERS = 100
  private readonly RESET_INTERVAL = 10000 // 10 secondes

  checkRender(): boolean {
    const now = Date.now()
    
    if (now - this.lastReset > this.RESET_INTERVAL) {
      this.renderCount = 0
      this.lastReset = now
    }

    this.renderCount++
    
    if (this.renderCount > this.MAX_RENDERS) {
      console.error('Trop de re-renders détectés, rechargement de la page')
      setTimeout(() => window.location.reload(), 1000)
      return false
    }

    return true
  }
}

const renderBreaker = new RenderCircuitBreaker()

// Composant ChatInput isolé avec React.memo
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

// Composant MessageList isolé avec React.memo
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
  // Vérifier les re-renders excessifs
  if (!renderBreaker.checkRender()) {
    return null
  }

  const router = useRouter()
  const { user, isAuthenticated, isLoading, hasHydrated, initializeSession } = useAuthStore()
  const { t, currentLanguage } = useTranslation()

  const currentConversation = useChatStore(state => state.currentConversation)
  const conversationsCount = useChatStore(state => state.conversations.length)
  const setCurrentConversation = useChatStore(state => state.setCurrentConversation)
  const addMessage = useChatStore(state => state.addMessage)
  const updateMessage = useChatStore(state => state.updateMessage)
  const createNewConversation = useChatStore(state => state.createNewConversation)

  const config = { level: 'standard' }

  // Regrouper les états UI liés
  const [uiState, setUiState] = useState({
    inputMessage: '',
    isLoadingChat: false,
    isMobileDevice: false,
    showConcisionSettings: false,
    keyboardHeight: 0,
    isKeyboardVisible: false,
    viewportHeight: 0,
    shouldAutoScroll: true,
    isUserScrolling: false,
    showScrollButton: false,
    isSubmittingFeedback: false
  })

  const [clarificationState, setClarificationState] = useState<{
    messageId: string
    originalQuestion: string
    clarificationQuestions: string[]
  } | null>(null)

  const [feedbackModal, setFeedbackModal] = useState<{
    isOpen: boolean
    messageId: string | null
    feedbackType: 'positive' | 'negative' | null
  }>({
    isOpen: false,
    messageId: null,
    feedbackType: null
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const lastMessageCountRef = useRef(0)
  const isMountedRef = useRef(true)
  const redirectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const authCheckTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const hasLoadedConversationsRef = useRef(false)
  const loadingTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const conversationLoadingAttemptsRef = useRef(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const isRedirectingRef = useRef(false)

  // Mémoisation stable des données
  const messages: Message[] = useMemo(() => {
    return currentConversation?.messages || []
  }, [currentConversation?.messages])

  const hasMessages = useMemo(() => {
    return messages.length > 0
  }, [messages.length])

  // CORRECTION: redirectToLogin améliorée avec nettoyage complet
  const redirectToLogin = useCallback((reason: string = 'Session expirée') => {
    // Protection contre les appels multiples RENFORCÉE
    if (isRedirectingRef.current) {
      console.log('Redirection déjà en cours, ignore:', reason)
      return Promise.resolve()
    }

    isRedirectingRef.current = true
    console.log('Redirection vers login:', reason)
    
    // Nettoyer immédiatement TOUS les timeouts
    [redirectTimeoutRef, authCheckTimeoutRef, loadingTimeoutRef].forEach(ref => {
      if (ref.current) {
        clearTimeout(ref.current)
        ref.current = null
      }
    })
    
    // Marquer le composant comme démonté pour empêcher les setState
    isMountedRef.current = false
    
    // Nettoyer les stores avant la redirection
    try {
      // Reset du store de chat pour éviter les états incohérents
      const chatStore = useChatStore.getState()
      if (chatStore.reset) {
        chatStore.reset()
      } else {
        // Reset manuel si pas de méthode reset
        useChatStore.setState({
          currentConversation: null,
          conversations: [],
          isLoading: false
        })
      }
    } catch (error) {
      console.warn('Erreur nettoyage stores:', error)
    }
    
    // Nettoyer les classes CSS
    document.body.classList.remove('keyboard-open')
    
    try {
      router.push('/')
      
      // Fallback plus court et plus robuste
      redirectTimeoutRef.current = setTimeout(() => {
        if (window.location.pathname === '/chat') {
          window.location.href = '/'
        }
      }, 500) // Réduit de 1000ms à 500ms
      
    } catch (error) {
      console.error('Erreur redirection router, fallback immédiat')
      window.location.href = '/'
    }
    
    return Promise.resolve()
  }, [router])

  const handleAuthError = useCallback((error: any) => {
    console.log('Gestion erreur auth:', error)
    
    // Empêcher les opérations si le composant n'est plus monté
    if (!isMountedRef.current) {
      console.log('Composant démonté, ignore erreur auth')
      return
    }
    
    if (error?.status === 403 || 
        error?.message?.includes('Auth session missing') ||
        error?.message?.includes('Forbidden')) {
      
      console.log('Session expirée détectée, redirection')
      redirectToLogin('Session expirée')
    }
  }, [redirectToLogin])

  // Fonctions simplifiées
  const getUserInitials = useCallback((user: any): string => {
    if (!user) return 'U'

    if (user.name) {
      const names = user.name.trim().split(' ')
      if (names.length >= 2) {
        return (names[0][0] + names[names.length - 1][0]).toUpperCase()
      }
      return names[0][0].toUpperCase()
    }

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

  const preprocessMarkdown = useCallback((content: string): string => {
    if (!content) return ""

    let processed = content

    processed = processed.replace(/(#{1,6})\s*([^#\n]+?)([A-Z][a-z])/g, '$1 $2\n\n$3')
    processed = processed.replace(/^(#{1,6}[^\n]+)(?!\n)/gm, '$1\n')
    processed = processed.replace(/([a-z])([A-Z])/g, '$1, $2')
    processed = processed.replace(/([.!?:])([A-Z])/g, '$1 $2')
    processed = processed.replace(/([a-z])(\*\*[A-Z])/g, '$1 $2')
    processed = processed.replace(/([.!?:])\s*(\*\*[^*]+\*\*)/g, '$1\n\n$2')
    processed = processed.replace(/([.!?:])\s*-\s*([A-Z][^:]+:)/g, '$1\n\n### $2')
    processed = processed.replace(/([.!?:])\s*-\s*([A-Z][^-]+)/g, '$1\n\n- $2')
    processed = processed.replace(/([^.\n])\n([•\-\*]\s)/g, '$1\n\n$2')
    processed = processed.replace(/([•\-\*]\s[^\n]+)\n([A-Z][^•\-\*])/g, '$1\n\n$2')
    processed = processed.replace(/(Causes Possibles|Recommandations|Prévention|Court terme|Long terme|Immédiat)([^-:])/g, '\n\n### $1\n\n$2')
    processed = processed.replace(/[ \t]+/g, ' ')
    processed = processed.replace(/\n\n\n+/g, '\n\n')
    processed = processed.trim()

    return processed
  }, [])

  const processedMessages = useMemo(() => {
    return messages.map(message => ({
      ...message,
      processedContent: message.isUser ? message.content : preprocessMarkdown(message.content)
    }))
  }, [messages, preprocessMarkdown])

  const cleanResponseText = useCallback((text: string): string => {
    if (!text) return ""

    if (text.length < 100) {
      return text.trim()
    }

    let cleaned = text

    // Nettoyage des références aux sources et autres éléments indésirables
    cleaned = cleaned.replace(/\*\*Source:\s*[^*]+\*\*/g, '')
    cleaned = cleaned.replace(/\*\*ource:\s*[^*]+\*\*/g, '')
    cleaned = cleaned.replace(/\*\*Source[^*]*\*\*/g, '')
    cleaned = cleaned.replace(/Source:\s*[^\n]+/g, '')
    cleaned = cleaned.replace(/protection, regardless of the species involved[^.]+\./g, '')
    cleaned = cleaned.replace(/bird ages, from the adverse effects[^.]+\./g, '')
    cleaned = cleaned.replace(/oocyst production reaches a maximum[^.]+\./g, '')
    cleaned = cleaned.replace(/oocyst production begins to diminish[^.]+\./g, '')
    cleaned = cleaned.replace(/oocyst production ceases[^.]+\./g, '')
    cleaned = cleaned.replace(/immunosuppressive response after[^.]+\./g, '')
    cleaned = cleaned.replace(/^[a-z][^.]+\.\.\./gm, '')
    cleaned = cleaned.replace(/ould be aware of local legislation[^.]+\./g, '')
    cleaned = cleaned.replace(/Apply your knowledge and judgment[^.]+\./g, '')
    cleaned = cleaned.replace(/Age \(days\) Weight \(lb\)[^|]+\|[^|]+\|/g, '')
    cleaned = cleaned.replace(/\b\w{1,3}\.\.\./g, '')
    cleaned = cleaned.replace(/[^.!?]+---\s*/g, '')
    cleaned = cleaned.replace(/^\d+\.\s+[A-Z][^:]+:\s*$/gm, '')
    cleaned = cleaned.replace(/^\w\.\s+[A-Z][^:]+:\s*$/gm, '')
    cleaned = cleaned.replace(/^INTRODUCTION[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Introduction[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Cobb MX[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^COBB MX[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^[A-Z\s]{10,}:?\s*$/gm, '')
    cleaned = cleaned.replace(/^[A-Z][A-Z\s]+GUIDE[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^[A-Z][A-Z\s]+MANUAL[^\n]*$/gm, '')
    cleaned = cleaned.replace(/\|\s*Age\s*\|\s*Weight[^|]*\|[^\n]*\n/g, '')
    cleaned = cleaned.replace(/\|\s*Days\s*\|\s*Grams[^|]*\|[^\n]*\n/g, '')
    cleaned = cleaned.replace(/[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}/g, '')
    cleaned = cleaned.replace(/\b[A-Z]\.[A-Z]\.[A-Z]\./g, '')
    cleaned = cleaned.replace(/Page\s+\d+\s+of\s+\d+/gi, '')
    cleaned = cleaned.replace(/^\([^)]+\)\s*$/gm, '')
    cleaned = cleaned.replace(/^et\s+al\.[^\n]*$/gm, '')
    cleaned = cleaned.replace(/\b[A-Z]{2,}\-[0-9]+\b/g, '')
    cleaned = cleaned.replace(/\b[0-9]{4,}\-[0-9]{2,}\b/g, '')
    cleaned = cleaned.replace(/\bDOI:\s*[^\s]+/gi, '')
    cleaned = cleaned.replace(/\s+/g, ' ')
    cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n')
    cleaned = cleaned.replace(/\n\s*\n/g, '\n\n')
    cleaned = cleaned.replace(/^\s*\n+/, '')
    cleaned = cleaned.replace(/\n+\s*$/, '')

    return cleaned.trim()
  }, [])

  // loadConversationsWithBreaker simplifiée
  const loadConversationsWithBreaker = useCallback(async (userId: string) => {
    if (!pageLoadingBreaker.canAttempt() || hasLoadedConversationsRef.current || !isMountedRef.current) {
      return
    }

    pageLoadingBreaker.recordAttempt()
    conversationLoadingAttemptsRef.current++

    try {
      await useChatStore.getState().loadConversations(userId)
      
      if (isMountedRef.current) {
        hasLoadedConversationsRef.current = true
        conversationLoadingAttemptsRef.current = 0
        pageLoadingBreaker.recordSuccess()
      }
    } catch (error) {
      pageLoadingBreaker.recordFailure()
      
      if (isMountedRef.current) {
        handleAuthError(error)
        hasLoadedConversationsRef.current = false
        
        if (conversationLoadingAttemptsRef.current >= 3) {
          hasLoadedConversationsRef.current = true
        }
      }
      
      throw error
    }
  }, [handleAuthError])

  // CORRECTION: useEffect pour auth backend avec nettoyage approprié
  useEffect(() => {
    let isInitializing = false
    let isCancelled = false
    
    const initAuth = async () => {
      if (isInitializing || !hasHydrated || isCancelled || !isMountedRef.current) return
      isInitializing = true
      
      try {
        const sessionValid = await initializeSession()
        
        if (!sessionValid && isMountedRef.current && !isCancelled) {
          redirectToLogin('Session expirée')
        }
      } catch (error) {
        console.error('Erreur initialisation:', error)
        if (isMountedRef.current && !isCancelled) {
          handleAuthError(error)
        }
      } finally {
        isInitializing = false
      }
    }
    
    if (hasHydrated && isAuthenticated !== false) {
      initAuth()
    }

    return () => {
      isCancelled = true
    }
  }, [hasHydrated, isAuthenticated, initializeSession, redirectToLogin, handleAuthError])

  // CORRECTION: useEffect pour gestion de la déconnexion avec protection
  useEffect(() => {
    let timeoutId: NodeJS.Timeout | null = null

    if (hasHydrated && isAuthenticated === false && !isLoading && isMountedRef.current) {
      timeoutId = setTimeout(() => {
        if (isMountedRef.current) {
          redirectToLogin('Déconnexion')
        }
      }, 100)
    }

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }, [hasHydrated, isAuthenticated, isLoading, redirectToLogin])

  // CORRECTION: useEffect pour gestion clavier mobile avec cleanup complet
  useEffect(() => {
    if (!uiState.isMobileDevice || !isMountedRef.current) return

    let initialViewportHeight = window.visualViewport?.height || window.innerHeight
    let isCancelled = false

    if (isMountedRef.current && !isCancelled) {
      setUiState(prev => ({ ...prev, viewportHeight: initialViewportHeight }))
    }
    
    const handleViewportChange = () => {
      if (isCancelled || !isMountedRef.current) return
      
      if (window.visualViewport) {
        const currentHeight = window.visualViewport.height
        const heightDifference = initialViewportHeight - currentHeight
        
        setUiState(prev => ({
          ...prev,
          viewportHeight: currentHeight,
          isKeyboardVisible: heightDifference > 150,
          keyboardHeight: heightDifference > 150 ? heightDifference : 0
        }))
        
        if (heightDifference > 150) {
          document.body.classList.add('keyboard-open')
          setTimeout(() => {
            if (messagesEndRef.current && isMountedRef.current && !isCancelled) {
              messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" })
            }
          }, 100)
        } else {
          document.body.classList.remove('keyboard-open')
        }
      }
    }

    const handleResize = () => {
      if (isCancelled || !isMountedRef.current) return
      
      const currentHeight = window.innerHeight
      const heightDifference = initialViewportHeight - currentHeight
      
      setUiState(prev => ({
        ...prev,
        viewportHeight: currentHeight,
        isKeyboardVisible: heightDifference > 150,
        keyboardHeight: heightDifference > 150 ? heightDifference : 0
      }))
      
      if (heightDifference > 150) {
        document.body.classList.add('keyboard-open')
      } else {
        document.body.classList.remove('keyboard-open')
      }
    }

    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', handleViewportChange)
    } else {
      window.addEventListener('resize', handleResize)
    }

    const inputElement = inputRef.current
    
    const handleFocus = () => {
      if (isCancelled || !isMountedRef.current) return
      
      setUiState(prev => ({ ...prev, isKeyboardVisible: true }))
      document.body.classList.add('keyboard-open')
      
      setTimeout(() => {
        if (messagesEndRef.current && isMountedRef.current && !isCancelled) {
          messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" })
        }
      }, 300)
    }

    const handleBlur = () => {
      setTimeout(() => {
        if (isMountedRef.current && !isCancelled) {
          setUiState(prev => ({ 
            ...prev, 
            isKeyboardVisible: false,
            keyboardHeight: 0
          }))
          document.body.classList.remove('keyboard-open')
        }
      }, 100)
    }

    if (inputElement) {
      inputElement.addEventListener('focus', handleFocus)
      inputElement.addEventListener('blur', handleBlur)
    }

    return () => {
      isCancelled = true
      
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', handleViewportChange)
      } else {
        window.removeEventListener('resize', handleResize)
      }
      
      document.body.classList.remove('keyboard-open')
      
      if (inputElement) {
        inputElement.removeEventListener('focus', handleFocus)
        inputElement.removeEventListener('blur', handleBlur)
      }
    }
  }, [uiState.isMobileDevice])

  // CORRECTION: useEffect de montage avec cleanup complet
  useEffect(() => {
    isMountedRef.current = true
    
    return () => {
      console.log('ChatInterface: Nettoyage complet au démontage')
      isMountedRef.current = false
      isRedirectingRef.current = false
      
      // Nettoyer TOUS les timeouts
      [loadingTimeoutRef, redirectTimeoutRef, authCheckTimeoutRef].forEach(ref => {
        if (ref.current) {
          clearTimeout(ref.current)
          ref.current = null
        }
      })
      
      // Nettoyer les classes CSS
      document.body.classList.remove('keyboard-open')
      
      // Réinitialiser les refs
      hasLoadedConversationsRef.current = false
      conversationLoadingAttemptsRef.current = 0
      pageLoadingBreaker.reset()
    }
  }, [])

  // Détection de device mobile
  useEffect(() => {
    if (!isMountedRef.current) return

    const detectMobileDevice = () => {
      const userAgent = navigator.userAgent.toLowerCase()
      const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent)
      const isTabletScreen = window.innerWidth <= 1024
      const hasTouchScreen = 'ontouchstart' in window || navigator.maxTouchPoints > 0
      const isIPadOS = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1
      const isDesktopTouchscreen = window.innerWidth > 1200 && navigator.maxTouchPoints > 0 && !isIPadOS

      return (isMobileUA || isIPadOS || (isTabletScreen && hasTouchScreen)) && !isDesktopTouchscreen
    }

    if (isMountedRef.current) {
      setUiState(prev => ({ ...prev, isMobileDevice: detectMobileDevice() }))
    }

    const handleResize = () => {
      if (isMountedRef.current) {
        setUiState(prev => ({ ...prev, isMobileDevice: detectMobileDevice() }))
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // CORRECTION: Auto-scroll avec protection complète
  useEffect(() => {
    if (!isMountedRef.current) return

    let timeoutId: NodeJS.Timeout | null = null

    if (messages.length > lastMessageCountRef.current && 
        uiState.shouldAutoScroll && 
        !uiState.isUserScrolling) {
      
      timeoutId = setTimeout(() => {
        if (isMountedRef.current && messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
        }
      }, 100)
    }

    lastMessageCountRef.current = messages.length

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }, [messages.length, uiState.shouldAutoScroll, uiState.isUserScrolling])

  // CORRECTION: Gestion du scroll avec cleanup approprié et protection
  useEffect(() => {
    const chatContainer = chatContainerRef.current
    if (!chatContainer || !isMountedRef.current) return

    let scrollTimeout: NodeJS.Timeout
    let isScrolling = false
    let isCancelled = false

    const handleScroll = () => {
      if (!isMountedRef.current || isCancelled) return

      const { scrollTop, scrollHeight, clientHeight } = chatContainer
      const isAtBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 50
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100

      if (!isScrolling) {
        setUiState(prev => ({ ...prev, isUserScrolling: true }))
        isScrolling = true
      }

      setUiState(prev => ({ ...prev, showScrollButton: !isNearBottom && messages.length > 3 }))

      if (isAtBottom) {
        setUiState(prev => ({ ...prev, shouldAutoScroll: true }))
      } else {
        setUiState(prev => ({ ...prev, shouldAutoScroll: false }))
      }

      clearTimeout(scrollTimeout)
      scrollTimeout = setTimeout(() => {
        if (isMountedRef.current && !isCancelled) {
          setUiState(prev => ({ ...prev, isUserScrolling: false }))
          isScrolling = false
        }
      }, 150)
    }

    chatContainer.addEventListener('scroll', handleScroll, { passive: true })
    
    return () => {
      isCancelled = true
      chatContainer.removeEventListener('scroll', handleScroll)
      clearTimeout(scrollTimeout)
    }
  }, [messages.length])

  // Gestion du message de bienvenue
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

  // Update du message de bienvenue
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

  // Chargement des conversations avec timeout et protection
  useEffect(() => {
    if (isAuthenticated && user?.id && isMountedRef.current && !hasLoadedConversationsRef.current) {
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current)
      }

      loadingTimeoutRef.current = setTimeout(() => {
        if (isMountedRef.current && !hasLoadedConversationsRef.current) {
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
          loadingTimeoutRef.current = null
        }
      }
    }
  }, [isAuthenticated, user?.id, loadConversationsWithBreaker])

  // Reset circuit breaker
  useEffect(() => {
    if (user?.id && isMountedRef.current) {
      hasLoadedConversationsRef.current = false
      conversationLoadingAttemptsRef.current = 0
      pageLoadingBreaker.reset()
    }
  }, [user?.id])

  // États de chargement avec protection
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

  if (!isAuthenticated) {
    if (!isRedirectingRef.current) {
      redirectToLogin('Non authentifié')
    }
    
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Redirection en cours...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    if (!isRedirectingRef.current) {
      redirectToLogin('Utilisateur manquant')
    }
    
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

  const extractAnswerAndSources = (result: any): [string, any[]] => {
    let answerText = ""
    let sources: any[] = []

    if (result?.type === 'validation_rejected') {
      let rejectionMessage = result.message || "Cette question ne concerne pas le domaine agricole."

      if (result.validation?.suggested_topics && result.validation.suggested_topics.length > 0) {
        rejectionMessage += "\n\n**Voici quelques sujets que je peux vous aider :**\n"
        result.validation.suggested_topics.forEach((topic: string) => {
          rejectionMessage += `• ${topic}\n`
        })
      }

      return [rejectionMessage, []]
    }

    if (result?.type === 'answer' && result?.answer) {
      answerText = result.answer.text || ""
      return [answerText, []]
    }

    if (result?.type === 'partial_answer' && result?.general_answer) {
      answerText = result.general_answer.text || ""
      return [answerText, []]
    }

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

    return [answerText, []]
  }

  // handleSendMessage avec protection renforcée
  const handleSendMessage = useCallback(async (text?: string) => {
    const safeText = text || uiState.inputMessage
    
    if (!safeText.trim() || !isMountedRef.current) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: safeText.trim(),
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
    setUiState(prev => ({ 
      ...prev, 
      inputMessage: '', 
      isLoadingChat: true,
      shouldAutoScroll: true,
      isUserScrolling: false 
    }))

    try {
      let response;
      const optimalLevel = undefined;

      if (clarificationState) {
        response = await generateAIResponse(
          clarificationState.originalQuestion + " " + safeText.trim(),
          user,
          currentLanguage,
          conversationIdToSend,
          optimalLevel,
          true,
          clarificationState.originalQuestion,
          { answer: safeText.trim() }
        )

        setClarificationState(null)
      } else {
        response = await generateAIResponse(
          safeText.trim(),
          user,
          currentLanguage,
          conversationIdToSend,
          optimalLevel
        )
      }

      if (!isMountedRef.current) return

      const needsClarification = response.clarification_result?.clarification_requested === true

      if (needsClarification) {
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
          originalQuestion: safeText.trim(),
          clarificationQuestions: response.clarification_questions || []
        })
      } else {
        const [answerText, sources] = extractAnswerAndSources(response)
        const cleanedText = cleanResponseText(answerText)

        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: cleanedText || "Erreur: contenu vide",
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id,
          response_versions: response.response_versions,
          originalResponse: response.response
        }

        addMessage(aiMessage)
      }

    } catch (error) {
      console.error('Erreur:', error)
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
        setUiState(prev => ({ ...prev, isLoadingChat: false }))
      }
    }
  }, [uiState.inputMessage, currentConversation, addMessage, clarificationState, user, currentLanguage, cleanResponseText, handleAuthError, t])

  // Fonctions de feedback avec protection
  const handleFeedbackClick = useCallback((messageId: string, feedback: 'positive' | 'negative') => {
    if (!isMountedRef.current) return

    setFeedbackModal({
      isOpen: true,
      messageId,
      feedbackType: feedback
    })
  }, [])

  // CORRECTION: handleFeedbackSubmit avec protection complète
  const handleFeedbackSubmit = useCallback(async (feedback: 'positive' | 'negative', comment?: string) => {
    const { messageId } = feedbackModal
    if (!messageId || !isMountedRef.current) return

    const message = messages.find(msg => msg.id === messageId)
    if (!message || !message.conversation_id) {
      return
    }

    setUiState(prev => ({ ...prev, isSubmittingFeedback: true }))
    
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
      // CORRECTION: Vérifier que le composant est encore monté
      if (isMountedRef.current) {
        setUiState(prev => ({ ...prev, isSubmittingFeedback: false }))
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

    setUiState(prev => ({
      ...prev,
      shouldAutoScroll: true,
      isUserScrolling: false,
      showScrollButton: false
    }))
  }, [createNewConversation, t, currentLanguage, setCurrentConversation])

  const scrollToBottom = useCallback(() => {
    if (!isMountedRef.current) return

    setUiState(prev => ({
      ...prev,
      shouldAutoScroll: true,
      isUserScrolling: false,
      showScrollButton: false
    }))
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  // Calcul des styles dynamiques pour mobile
  const containerStyle = useMemo(() => {
    return uiState.isMobileDevice ? {
      height: '100vh',
      minHeight: '100vh',
      maxHeight: '100vh'
    } : {}
  }, [uiState.isMobileDevice])

  const chatScrollStyle = useMemo(() => {
    return uiState.isMobileDevice ? {
      height: uiState.isKeyboardVisible 
        ? `calc(100vh - 140px - ${uiState.keyboardHeight}px)` 
        : 'calc(100vh - 140px)',
      maxHeight: uiState.isKeyboardVisible 
        ? `calc(100vh - 140px - ${uiState.keyboardHeight}px)` 
        : 'calc(100vh - 140px)',
      overflow: 'auto',
      paddingBottom: '1rem'
    } : {
      scrollPaddingBottom: '7rem'
    }
  }, [uiState.isMobileDevice, uiState.isKeyboardVisible, uiState.keyboardHeight])

  return (
    <>
      <ZohoSalesIQ user={user} language={currentLanguage} />

      <div 
        className={`bg-gray-50 flex flex-col ${uiState.isMobileDevice ? 'chat-main-container' : 'min-h-dvh h-screen'}`}
        style={containerStyle}
      >

        <header className="bg-white border-b border-gray-100 px-2 sm:px-4 py-3 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <button
                onClick={handleNewConversation}
                className="w-10 h-10 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-center border border-gray-200"
                title={t('nav.newConversation')}
                aria-label={t('nav.newConversation')}
              >
                <PlusIcon className="w-5 h-5" />
              </button>

              <div className="header-icon-container history-menu-container">
                <HistoryMenu />
              </div>
            </div>

            <div className="flex-1 min-w-0 flex justify-center items-center space-x-3">
              <div className="w-10 h-10 grid place-items-center">
                <InteliaLogo className="h-8 w-auto" />
              </div>
              <h1 className="text-lg font-medium text-gray-900 truncate">Intelia Expert</h1>
            </div>

            <div className="flex items-center space-x-2">
              <div className="header-icon-container user-menu-container">
                <UserMenuButton />
              </div>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          <div
            ref={chatContainerRef}
            className={`flex-1 overflow-y-auto px-2 sm:px-4 py-6 pb-28 overscroll-contain ${uiState.isMobileDevice ? 'chat-scroll-area' : ''}`}
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

              <MessageList 
                processedMessages={processedMessages}
                isLoadingChat={uiState.isLoadingChat}
                handleFeedbackClick={handleFeedbackClick}
                getUserInitials={getUserInitials}
                user={user}
                t={t}
              />

              <div ref={messagesEndRef} />
            </div>
          </div>

          {uiState.showScrollButton && (
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

          <div 
            className={`px-2 sm:px-4 py-2 bg-white border-t border-gray-100 z-20 ${uiState.isMobileDevice ? 'chat-input-fixed' : 'sticky bottom-0'}`}
            style={{
              paddingBottom: uiState.isMobileDevice 
                ? `calc(env(safe-area-inset-bottom) + 8px)`
                : 'calc(env(safe-area-inset-bottom) + 8px)',
              position: uiState.isMobileDevice ? 'fixed' : 'sticky',
              bottom: 0,
              left: 0,
              right: 0,
              backgroundColor: 'white',
              borderTop: '1px solid rgb(243 244 246)',
              zIndex: 1000,
              minHeight: uiState.isMobileDevice ? '70px' : 'auto',
              display: 'flex',
              alignItems: 'center',
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
                      onClick={() => setClarificationState(null)}
                      className="text-blue-600 hover:text-blue-800 text-sm underline"
                    >
                      Annuler
                    </button>
                  </div>
                </div>
              )}

              <ChatInput
                inputMessage={uiState.inputMessage}
                setInputMessage={(value: string) => setUiState(prev => ({ ...prev, inputMessage: value }))}
                onSendMessage={handleSendMessage}
                isLoadingChat={uiState.isLoadingChat}
                clarificationState={clarificationState}
                isMobileDevice={uiState.isMobileDevice}
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
        isSubmitting={uiState.isSubmittingFeedback}
      />
    </>
  )
}