'use client'

import { useSearchParams } from 'next/navigation'
import { useRouter } from 'next/navigation'
import React, { useState, useEffect, useRef, useMemo, useCallback, Suspense } from 'react'
import ReactMarkdown from 'react-markdown'
import { Message } from '../../types'
import { useAuthStore } from '@/lib/stores/auth'
import { useTranslation } from '@/lib/languages/i18n'
import { useChatStore } from './hooks/useChatStore'
import { generateAIResponse } from './services/apiService'
import { conversationService } from './services/conversationService'
import { getSupabaseClient } from '@/lib/supabase/singleton'

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

// Composant ChatInput optimise avec React.memo
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
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSendMessage()
    }
  }, [onSendMessage])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setInputMessage(e.target.value)
  }, [setInputMessage])

  return (
    <div className={`flex items-center min-h-[48px] w-full ${isMobileDevice ? 'mobile-input-container' : 'space-x-3'}`}>
      <div className={`flex-1 ${isMobileDevice ? 'mobile-input-wrapper' : ''}`}>
        <input
          ref={inputRef}
          type="text"
          value={inputMessage}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={clarificationState ? t('chat.clarificationPlaceholder') : t('chat.placeholder')}
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
        title={isLoadingChat ? t('chat.sending') : t('chat.send')}
        aria-label={isLoadingChat ? t('chat.sending') : t('chat.send')}
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

// Composant MessageList optimise avec React.memo
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
                    {t('chat.feedbackThanks')}
                  </span>
                  {message.feedbackComment && (
                    <span className="text-xs text-blue-600" title={`${t('chat.feedbackComment')}: ${message.feedbackComment}`}>
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
          <div className="text-sm">{t('chat.noMessages')}</div>
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

// Composant principal ChatInterface (renomme depuis l'export par defaut)
function ChatInterface() {
  const { user, isAuthenticated, isLoading, hasHydrated, initializeSession } = useAuthStore()
  const { t, currentLanguage } = useTranslation()
  const searchParams = useSearchParams()
  const router = useRouter()

  // Stores Zustand
  const currentConversation = useChatStore(state => state.currentConversation)
  const setCurrentConversation = useChatStore(state => state.setCurrentConversation)
  const addMessage = useChatStore(state => state.addMessage)
  const updateMessage = useChatStore(state => state.updateMessage)
  const createNewConversation = useChatStore(state => state.createNewConversation)
  const loadConversations = useChatStore(state => state.loadConversations)

  // Etats separes pour eviter les cascades de re-renders
  const [inputMessage, setInputMessage] = useState('')
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const [isMobileDevice, setIsMobileDevice] = useState(false)
  const [isKeyboardVisible, setIsKeyboardVisible] = useState(false)
  const [keyboardHeight, setKeyboardHeight] = useState(0)
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true)
  const [isUserScrolling, setIsUserScrolling] = useState(false)
  const [showScrollButton, setShowScrollButton] = useState(false)
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false)
  const [viewportHeight, setViewportHeight] = useState(0)

  // Etats pour gestion OAuth
  const [isProcessingOAuth, setIsProcessingOAuth] = useState(false)
  const [oauthError, setOAuthError] = useState<string | null>(null)

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

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const lastMessageCountRef = useRef(0)
  const isMountedRef = useRef(true)
  const inputRef = useRef<HTMLInputElement>(null)
  const hasLoadedConversationsRef = useRef(false)

  // Memorisation stable des donnees
  const messages: Message[] = useMemo(() => {
    return currentConversation?.messages || []
  }, [currentConversation?.messages])

  const hasMessages = useMemo(() => {
    return messages.length > 0
  }, [messages.length])

  // Gestion amelioree des erreurs d'authentification
  const handleAuthError = useCallback((error: any) => {
    console.error('[Chat] Auth error detectee:', error)
    
    // Verifier si c'est une erreur de session expiree
    const isSessionExpired = (
      error?.status === 401 || 
      error?.status === 403 ||
      error?.message?.includes('Token expired') ||
      error?.message?.includes('Auth session missing') ||
      error?.message?.includes('Unauthorized') ||
      error?.message?.includes('Forbidden') ||
      error?.message?.includes('authentication_failed') ||
      error?.message?.includes('Session expiree') ||
      error?.detail === 'Token expired'
    )
    
    if (isSessionExpired) {
      console.log('[Chat] Session expiree detectee - deconnexion automatique')
      
      // Nettoyer l'etat local immediatement pour eviter les erreurs en cascade
      if (isMountedRef.current) {
        setCurrentConversation(null)
        setClarificationState(null)
        setInputMessage('')
        setIsLoadingChat(false)
      }
      
      // Utiliser le service de logout pour une deconnexion propre
      import('@/lib/services/logoutService').then(({ logoutService }) => {
        logoutService.performLogout(user)
      }).catch(err => {
        console.warn('[Chat] Fallback - redirection directe:', err)
        // Fallback : redirection directe si le service echoue
        setTimeout(() => {
          window.location.href = '/'
        }, 100)
      })
      
      return
    }
    
    // Pour les autres erreurs, juste logger sans redirection
    console.warn('[Chat] Erreur non-auth (pas de redirection):', error)
  }, [user, setCurrentConversation, setClarificationState, setInputMessage, setIsLoadingChat])

  // Fonctions utilitaires (conservees integralement)
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
    processed = processed.replace(/(Causes Possibles|Recommandations|Prevention|Court terme|Long terme|Immediat)([^-:])/g, '\n\n### $1\n\n$2')
    processed = processed.replace(/[ \t]+/g, ' ')
    processed = processed.replace(/\n\n\n+/g, '\n\n')
    processed = processed.trim()

    return processed
  }, [])

  const cleanResponseText = useCallback((text: string): string => {
    if (!text) return ""
    if (text.length < 100) return text.trim()

    let cleaned = text
    // Nettoyage des artefacts de source
    cleaned = cleaned.replace(/\*\*Source:\s*[^*]+\*\*/g, '')
    cleaned = cleaned.replace(/Source:\s*[^\n]+/g, '')
    cleaned = cleaned.replace(/protection, regardless of the species involved[^.]+\./g, '')
    cleaned = cleaned.replace(/^\d+\.\s+[A-Z][^:]+:\s*$/gm, '')
    cleaned = cleaned.replace(/^\w\.\s+[A-Z][^:]+:\s*$/gm, '')
    cleaned = cleaned.replace(/^INTRODUCTION[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^[A-Z\s]{10,}:?\s*$/gm, '')
    cleaned = cleaned.replace(/Page\s+\d+\s+of\s+\d+/gi, '')
    cleaned = cleaned.replace(/\bDOI:\s*[^\s]+/gi, '')
    cleaned = cleaned.replace(/\s+/g, ' ')
    cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n')
    cleaned = cleaned.replace(/^\s*\n+/, '')
    cleaned = cleaned.replace(/\n+\s*$/, '')

    return cleaned.trim()
  }, [])

  const processedMessages = useMemo(() => {
    return messages.map(message => ({
      ...message,
      processedContent: message.isUser ? message.content : preprocessMarkdown(message.content)
    }))
  }, [messages, preprocessMarkdown])

  // Effet de nettoyage au demontage
  useEffect(() => {
    isMountedRef.current = true
    
    return () => {
      isMountedRef.current = false
      document.body.classList.remove('keyboard-open')
      hasLoadedConversationsRef.current = false
    }
  }, [])

  // Gestionnaire OAuth dans la page chat
  useEffect(() => {
    const handleOAuthCallback = async () => {
      const authStatus = searchParams?.get('auth')
      
      if (authStatus === 'success') {
        console.log('[OAuth Chat] Finalisation authentification OAuth...')
        setIsProcessingOAuth(true)
        setOAuthError(null)
        
        try {
          setIsProcessingOAuth(true)
          const supabase = getSupabaseClient()
          
          // Recuperer la session actuelle apres l'OAuth
          const { data: { session }, error } = await supabase.auth.getSession()
          
          if (error) {
            console.error('[OAuth Chat] Erreur recuperation session:', error)
            setOAuthError(error.message)
            router.replace('/?auth=error&message=' + encodeURIComponent(error.message))
            return
          }

          if (session?.user) {
            // Utiliser initializeSession qui met automatiquement a jour le store
            await initializeSession()
            
            // Nettoyer l'URL
            const url = new URL(window.location.href)
            url.searchParams.delete('auth')
            window.history.replaceState({}, '', url.pathname)
            
            console.log('[OAuth Chat] OAuth complete avec succes pour:', session.user.email)
          } else {
            console.error('[OAuth Chat] Session OAuth incomplete')
            setOAuthError('Session incomplete')
            router.replace('/?auth=error&message=incomplete_session')
          }
        } catch (error: any) {
          console.error('[OAuth Chat] Erreur traitement OAuth:', error)
          setOAuthError(error.message)
          router.replace('/?auth=error&message=' + encodeURIComponent(error.message))
        } finally {
          setIsProcessingOAuth(false)
        }
      } else if (authStatus === 'error') {
        const message = searchParams?.get('message') || 'Erreur d\'authentification'
        console.error('[OAuth Chat] Erreur OAuth recue:', message)
        setOAuthError(message)
        router.replace('/?auth=error&message=' + encodeURIComponent(message))
      }
    }

    if (searchParams?.has('auth')) {
      handleOAuthCallback()
    }
  }, [searchParams, router, initializeSession])

  // Detection de device mobile (conservee)
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

    setIsMobileDevice(detectMobileDevice())

    const handleResize = () => {
      if (isMountedRef.current) {
        setIsMobileDevice(detectMobileDevice())
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Gestion clavier mobile (conservee)
  useEffect(() => {
    if (!isMobileDevice || !isMountedRef.current) return

    let initialViewportHeight = window.visualViewport?.height || window.innerHeight
    let isCancelled = false

    setViewportHeight(initialViewportHeight)
    
    const handleViewportChange = () => {
      if (isCancelled || !isMountedRef.current) return
      
      if (window.visualViewport) {
        const currentHeight = window.visualViewport.height
        const heightDifference = initialViewportHeight - currentHeight
        
        setViewportHeight(currentHeight)
        setIsKeyboardVisible(heightDifference > 150)
        setKeyboardHeight(heightDifference > 150 ? heightDifference : 0)
        
        if (heightDifference > 150) {
          document.body.classList.add('keyboard-open')
        } else {
          document.body.classList.remove('keyboard-open')
        }
      }
    }

    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', handleViewportChange)
    }

    return () => {
      isCancelled = true
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', handleViewportChange)
      }
      document.body.classList.remove('keyboard-open')
    }
  }, [isMobileDevice])

  // Auto-scroll (conservee)
  useEffect(() => {
    if (!isMountedRef.current) return

    if (messages.length > lastMessageCountRef.current && 
        shouldAutoScroll && 
        !isUserScrolling) {
      
      const timeoutId = setTimeout(() => {
        if (isMountedRef.current && messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
        }
      }, 100)

      return () => clearTimeout(timeoutId)
    }

    lastMessageCountRef.current = messages.length
  }, [messages.length, shouldAutoScroll, isUserScrolling])

  // Gestion du scroll (conservee)
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
        if (isMountedRef.current && !isCancelled) {
          setIsUserScrolling(false)
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

  // Message de bienvenue (conserve)
  useEffect(() => {
    if (isAuthenticated && !currentConversation && !hasMessages && isMountedRef.current && !isProcessingOAuth) {
      const welcomeMessage: Message = {
        id: 'welcome',
        content: t('chat.welcome'),
        isUser: false,
        timestamp: new Date()
      }

      const welcomeConversation = {
        id: 'welcome',
        title: t('chat.newConversation'),
        preview: t('chat.startQuestion'),
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
  }, [isAuthenticated, currentConversation, hasMessages, t, currentLanguage, setCurrentConversation, isProcessingOAuth])

  // useEffect pour les changements de langue (unifie et corrige)
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

  // Chargement initial VRAIMENT unique
  useEffect(() => {
    // Protection absolue : ne charger QU'UNE SEULE FOIS
    if (isAuthenticated && 
        user?.email && 
        !hasLoadedConversationsRef.current && 
        isMountedRef.current &&
        !isProcessingOAuth) {
      
      console.log('[Chat] Chargement initial UNIQUE pour:', user.email)
      hasLoadedConversationsRef.current = true

      // CAPTURE STABLE des valeurs au moment de l'execution
      const userEmail = user.email

      // FONCTION LOCALE qui utilise le store directement
      const performInitialLoad = async () => {
        try {
          // Appeler le store directement sans capturer la fonction
          const { loadConversations: loadFn } = useChatStore.getState()
          await loadFn(userEmail)
          console.log('[Chat] Chargement initial termine avec succes')
        } catch (error) {
          console.error('[Chat] Erreur chargement initial:', error)
          
          // GESTION D'ERREUR LOCALE sans redependance
          if (error?.status === 401 || error?.status === 403) {
            console.log('[Chat] Session expiree detectee - redirection')
            hasLoadedConversationsRef.current = false // Permettre de reessayer
            setTimeout(() => {
              window.location.href = '/'
            }, 1000)
          } else {
            // En cas d'autre erreur, permettre de reessayer
            hasLoadedConversationsRef.current = false
          }
        }
      }

      // EXECUTION UNIQUE avec delai pour eviter les race conditions
      setTimeout(performInitialLoad, 100)
    }
  }, [isAuthenticated, user?.email, isProcessingOAuth])

  // Fonctions de gestion des messages (toutes conservees)
  const extractAnswerAndSources = useCallback((result: any): [string, any[]] => {
    let answerText = ""
    let sources: any[] = []

    if (result?.type === 'validation_rejected') {
      let rejectionMessage = result.message || t('chat.rejectionMessage')

      if (result.validation?.suggested_topics && result.validation.suggested_topics.length > 0) {
        rejectionMessage += `\n\n**${t('chat.suggestedTopics')}**\n`
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
        answerText = t('chat.formatError')
      }
    } else {
      answerText = String(responseContent).trim() || t('chat.formatError')

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
  }, [t])

  const handleSendMessage = useCallback(async (text?: string) => {
    const safeText = text || inputMessage
    
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
    setInputMessage('')
    setIsLoadingChat(true)
    setShouldAutoScroll(true)
    setIsUserScrolling(false)

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

      // Verifier si la reponse indique une session expiree
      if (response?.error === 'authentication_failed' || 
          response?.detail === 'Token expired' ||
          response?.message?.includes('Session expiree')) {
        handleAuthError({ 
          status: 401, 
          message: 'Token expired from API response',
          detail: 'Token expired'
        })
        return
      }

      const needsClarification = response.clarification_result?.clarification_requested === true

      if (needsClarification) {
        const clarificationMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: (response.full_text || response.response) + `\n\n${t('chat.clarificationInstruction')}`,
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
          content: cleanedText || t('chat.emptyContent'),
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id,
          response_versions: response.response_versions,
          originalResponse: response.response
        }

        addMessage(aiMessage)
      }

    } catch (error) {
      console.error(t('chat.sendError'), error)
      handleAuthError(error) // Utilise la nouvelle gestion d'erreur amelioree

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
  }, [inputMessage, currentConversation, addMessage, clarificationState, user, currentLanguage, cleanResponseText, handleAuthError, t, extractAnswerAndSources])

  // Fonctions de feedback (conservees)
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
            console.warn(t('chat.commentNotSent'), commentError)
          }
        }
      } catch (feedbackError) {
        console.error(t('chat.feedbackSendError'), feedbackError)
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
      console.error(t('chat.feedbackGeneralError'), error)
      throw error
    } finally {
      if (isMountedRef.current) {
        setIsSubmittingFeedback(false)
      }
    }
  }, [feedbackModal, messages, updateMessage, handleAuthError, t])

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
      title: t('chat.newConversation'),
      preview: t('chat.startQuestion'),
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

  const getCurrentDate = useCallback(() => {
    return new Date().toLocaleDateString(currentLanguage === 'fr' ? 'fr-FR' : 'en-US', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    })
  }, [currentLanguage])

  // Calcul des styles dynamiques pour mobile (conserve)
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

  // Etats de chargement simplifies
  if (!hasHydrated) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">{t('chat.loading')}</p>
        </div>
      </div>
    )
  }

  if (isLoading || isProcessingOAuth) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">
            {isProcessingOAuth ? 'Finalisation OAuth LinkedIn...' : t('chat.loading')}
          </p>
        </div>
      </div>
    )
  }

  // Affichage erreur OAuth
  if (oauthError) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-red-600 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Erreur d'authentification</h2>
          <p className="text-gray-600 mb-4">{oauthError}</p>
          <button
            onClick={() => router.push('/')}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retour à l'accueil
          </button>
        </div>
      </div>
    )
  }

  // Condition de rendu amelioree pour OAuth
  if (!isAuthenticated || !user) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">{t('chat.loading')}</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <ZohoSalesIQ user={user} />
      <div 
        className={`bg-gray-50 flex flex-col relative z-0 ${isMobileDevice ? 'chat-main-container' : 'min-h-dvh h-screen'}`}
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
              <h1 className="text-lg font-medium text-gray-900 truncate">{t('common.appName')}</h1>
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
                title={t('chat.scrollToBottom')}
                aria-label={t('chat.scrollToBottom')}
              >
                <ArrowDownIcon />
              </button>
            </div>
          )}

          <div 
            className={`px-2 sm:px-4 py-2 bg-white border-t border-gray-100 z-20 ${isMobileDevice ? 'chat-input-fixed' : 'sticky bottom-0'}`}
            style={{
              paddingBottom: isMobileDevice 
                ? `calc(env(safe-area-inset-bottom) + 8px)`
                : 'calc(env(safe-area-inset-bottom) + 8px)',
              position: isMobileDevice ? 'fixed' : 'sticky',
              bottom: 0,
              left: 0,
              right: 0,
              backgroundColor: 'white',
              borderTop: '1px solid rgb(243 244 246)',
              zIndex: 1000,
              minHeight: isMobileDevice ? '70px' : 'auto',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <div className="max-w-full sm:max-w-4xl lg:max-w-5xl xl:max-w-6xl mx-auto w-full sm:w-[90%] lg:w-[75%] xl:w-[60%]">
              {clarificationState && (
                <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-blue-700 text-sm font-medium">
                      {t('chat.clarificationMode')}
                    </span>
                    <button
                      onClick={() => setClarificationState(null)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      {t('modal.cancel')}
                    </button>
                  </div>
                </div>
              )}

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
                  {t('chat.disclaimer')}
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
        feedbackType={feedbackModal.feedbackType ?? undefined}
        isSubmitting={isSubmittingFeedback}
      />
    </>
  )
}

// Composant de chargement
function ChatLoading() {
  return (
    <div className="h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Chargement du chat...</p>
      </div>
    </div>
  )
}

// Export par defaut avec Suspense
export default function ChatPage() {
  return (
    <Suspense fallback={<ChatLoading />}>
      <ChatInterface />
    </Suspense>
  )
}
