'use client'

import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Message } from './types'
import { useAuthStore } from './hooks/useAuthStore'
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
  /*CogIcon*/
} from './utils/icons'
import { HistoryMenu } from './components/HistoryMenu'
import { UserMenuButton } from './components/UserMenuButton'
import { ZohoSalesIQ } from './components/ZohoSalesIQ'
import { FeedbackModal } from './components/modals/FeedbackModal'

export default function ChatInterface() {
  const { user, isAuthenticated, isLoading } = useAuthStore()
  const { t, currentLanguage } = useTranslation()
  
  const currentConversation = useChatStore(state => state.currentConversation)
  const setCurrentConversation = useChatStore(state => state.setCurrentConversation)
  const addMessage = useChatStore(state => state.addMessage)
  const updateMessage = useChatStore(state => state.updateMessage)
  const createNewConversation = useChatStore(state => state.createNewConversation)
  const loadConversations = useChatStore(state => state.loadConversations)
  
  // Default config for now since we can't see the original hook
  const config = { level: 'standard' }
  
  const [inputMessage, setInputMessage] = useState('')
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const [isMobileDevice, setIsMobileDevice] = useState(false)
  const [showConcisionSettings, setShowConcisionSettings] = useState(false)
  
  // États existants inchangés
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
  const hasRedirectedRef = useRef(false)

  const messages: Message[] = currentConversation?.messages || []
  const hasMessages = messages.length > 0

  console.log('🔍 [Render] Messages:', messages.length, 'Clarification:', !!clarificationState, 'Concision:', config.level)

  // 🚀 FONCTION NOUVELLE : Reprocesser tous les messages avec nouvelles versions
  const reprocessAllMessages = () => {
    if (!currentConversation?.messages) return

    const updatedMessages = currentConversation.messages.map(message => {
      // Ne traiter que les réponses IA qui ont response_versions
      if (!message.isUser && 
          message.id !== 'welcome' && 
          message.response_versions &&
          !message.content.includes('Mode clarification') &&
          !message.content.includes('💡 Répondez simplement')) {
        
        // 🚀 SÉLECTION DE VERSION : Utiliser selectVersionFromResponse
        const selectedContent = (message.response_versions?.standard || message.response_versions?.detailed || message.response_versions?.concise || Object.values(message.response_versions || {})[0] || '')
        
        console.log(`📋 [reprocessAllMessages] Message ${message.id} - passage à ${config.level}`, {
          original_length: message.content.length,
          new_length: selectedContent.length,
          versions_available: Object.keys(message.response_versions)
        })
        
        return {
          ...message,
          content: selectedContent
        }
      }
      return message
    })

    const updatedConversation = {
      ...currentConversation,
      messages: updatedMessages
    }

    setCurrentConversation(updatedConversation)
    console.log('✅ [reprocessAllMessages] Tous les messages retraités avec niveau:', config.level)
  }

  // Tous les useEffect existants restent identiques
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !hasRedirectedRef.current) {
      hasRedirectedRef.current = true
      console.log('🔄 [ChatInterface] Redirection - utilisateur non authentifié')
      
      if (typeof window !== 'undefined') {
        window.location.replace('/')
      }
    }
  }, [isLoading, isAuthenticated])

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

  useEffect(() => {
    if (isMountedRef.current && messages.length > lastMessageCountRef.current && shouldAutoScroll && !isUserScrolling) {
      setTimeout(() => {
        if (isMountedRef.current) {
          messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
        }
      }, 100)
    }
    
    lastMessageCountRef.current = messages.length
  }, [messages.length, messages, shouldAutoScroll, isUserScrolling])

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
  }, [currentLanguage, t])

  useEffect(() => {
    if (isAuthenticated && user?.id && isMountedRef.current) {
      const loadTimer = setTimeout(() => {
        if (isMountedRef.current) {
          console.log('[ChatInterface] Chargement historique pour:', user.id)
          loadConversations(user.id)
            .then(() => {
              if (isMountedRef.current) {
                console.log('Historique conversations chargé')
              }
            })
            .catch(err => {
              if (isMountedRef.current) {
                console.error('Erreur chargement historique:', err)
              }
            })
        }
      }, 800)

      return () => clearTimeout(loadTimer)
    }
  }, [isAuthenticated, user?.id, loadConversations])

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
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">Redirection...</p>
        </div>
      </div>
    )
  }

  // 🚀 FONCTION MODIFIÉE : handleSendMessage avec niveau détecté automatiquement
  const handleSendMessage = async (text: string = inputMessage) => {
    if (!text.trim() || !isMountedRef.current) return

    console.log('📤 [ChatInterface] Envoi message:', {
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
      
      // 🚀 DÉTECTION AUTOMATIQUE : Niveau optimal pour la question
      const optimalLevel = undefined;
      console.log('🎯 [handleSendMessage] Niveau optimal détecté:', optimalLevel)
      
      if (clarificationState) {
        console.log('🎪 [handleSendMessage] Mode clarification')
        
        response = await generateAIResponse(
          clarificationState.originalQuestion + " " + text.trim(),
          user,
          currentLanguage,
          conversationIdToSend,
          optimalLevel, // 🚀 NOUVEAU : Passer niveau optimal
          true,
          clarificationState.originalQuestion,
          { answer: text.trim() }
        )
        
        setClarificationState(null)
        console.log('✅ [handleSendMessage] Clarification traitée')
        
      } else {
        // 🚀 APPEL MODIFIÉ : Passer niveau optimal au backend
        response = await generateAIResponse(
          text.trim(), 
          user, 
          currentLanguage, 
          conversationIdToSend,
          optimalLevel // 🚀 NOUVEAU : Niveau optimal détecté automatiquement
        )
      }

      if (!isMountedRef.current) return

      console.log('📥 [handleSendMessage] Réponse reçue:', {
        conversation_id: response.conversation_id,
        response_length: response.response?.length || 0,
        versions_received: Object.keys(response.response_versions || {}),
        clarification_requested: response.clarification_result?.clarification_requested || false
      })

      const needsClarification = response.clarification_result?.clarification_requested === true

      if (needsClarification) {
        console.log('❓ [handleSendMessage] Clarification demandée')
        
        const clarificationMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: (response.full_text || response.response) + "\n\n💡 Répondez simplement dans le chat avec les informations demandées.",
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

        console.log('🔄 [handleSendMessage] État clarification activé')

      } else {
        // 🚀 NOUVEAU : Stocker toutes les versions + afficher la réponse du niveau demandé
        let displayContent = response.full_text || response.response
        
        // Si on a des versions, utiliser la version appropriée au niveau actuel
        if (response.response_versions) {
          displayContent = (response.response_versions?.standard || response.response_versions?.detailed || response.response_versions?.concise || Object.values(response.response_versions || {})[0] || '')
          console.log('📋 [handleSendMessage] Version sélectionnée:', {
            level: config.level,
            content_length: displayContent.length,
            versions_available: Object.keys(response.response_versions)
          })
        }

        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: displayContent,
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id,
          // 🚀 NOUVEAU : Stocker toutes les versions reçues du backend
          response_versions: response.response_versions,
          // Garder pour compatibilité (peut être supprimé plus tard)
          originalResponse: response.response
        }

        addMessage(aiMessage)
        console.log('✅ [handleSendMessage] Message ajouté avec versions:', Object.keys(response.response_versions || {}))
      }
      
    } catch (error) {
      console.error('[handleSendMessage] Erreur:', error)
      
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
  }

  // Toutes les autres fonctions restent identiques
  const handleFeedbackClick = (messageId: string, feedback: 'positive' | 'negative') => {
    if (!isMountedRef.current) return
    
    setFeedbackModal({
      isOpen: true,
      messageId,
      feedbackType: feedback
    })
  }

  const handleFeedbackSubmit = async (feedback: 'positive' | 'negative', comment?: string) => {
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
  }

  const handleFeedbackModalClose = () => {
    if (!isMountedRef.current) return
    
    setFeedbackModal({
      isOpen: false,
      messageId: null,
      feedbackType: null
    })
  }

  const handleNewConversation = () => {
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
  }

  const scrollToBottom = () => {
    if (!isMountedRef.current) return
    
    setShouldAutoScroll(true)
    setIsUserScrolling(false)
    setShowScrollButton(false)
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const getCurrentDate = () => {
    return new Date().toLocaleDateString('fr-FR', { 
      day: 'numeric', 
      month: 'long', 
      year: 'numeric' 
    })
  }

  return (
    <>
      <ZohoSalesIQ user={user} language={currentLanguage} />

      <div className="h-screen bg-gray-50 flex flex-col">
        <header className="bg-white border-b border-gray-100 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <HistoryMenu />
              <UserMenuButton />
            </div>
          </div>

          {showConcisionSettings && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium text-gray-700">Paramètres de concision</h3>
                <button
                  onClick={() => setShowConcisionSettings(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              
              {hasMessages && (
                <button
                  onClick={reprocessAllMessages}
                  className="mt-3 px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 text-sm transition-colors"
                >
                  🔄 Appliquer à toutes les réponses
                </button>
              )}
            </div>
          )}
        </header>

        <div className="flex-1 overflow-hidden flex flex-col">
          <div 
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto px-4 py-6"
          >
            <div className="max-w-4xl mx-auto space-y-6">
              {hasMessages && (
                <div className="text-center">
                  <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                    {getCurrentDate()}
                  </span>
                </div>
              )}

              {messages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <div className="text-sm">Aucun message à afficher</div>
                </div>
              ) : (
                messages.map((message, index) => (
                  <div key={`${message.id}-${index}`}>
                    <div className={`flex items-start space-x-3 ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                      {!message.isUser && (
                        <div className="relative">
                          <InteliaLogo className="w-8 h-8 flex-shrink-0 mt-1" />
                        </div>
                      )}
                      
                      <div className={`px-4 py-3 rounded-2xl ${message.isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-white border border-gray-200 text-gray-900'}`}>
                        {message.isUser ? (
                          <p className="whitespace-pre-wrap leading-relaxed text-sm">
                            {message.content}
                          </p>
                        ) : (
                          <ReactMarkdown
                            className="prose prose-sm max-w-none prose-p:my-1 prose-li:my-0 prose-strong:text-gray-900"
                            components={{
                              h2: ({node, ...props}) => (
                                <h2 className="text-base font-bold text-gray-900 mt-0 mb-2 flex items-center gap-1" {...props} />
                              ),
                              p: ({node, ...props}) => (
                                <p className="leading-relaxed text-gray-800 my-1" {...props} />
                              ),
                              ul: ({node, ...props}) => (
                                <ul className="list-disc list-inside space-y-1 text-gray-800 my-1" {...props} />
                              ),
                              li: ({node, ...props}) => (
                                <li className="leading-snug" {...props} />
                              ),
                              strong: ({node, ...props}) => (
                                <strong className="font-semibold text-gray-900" {...props} />
                              ),
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        )}
                      </div>

                      {!message.isUser && 
                       message.response_versions && 
                       Object.keys(message.response_versions).length > 0 && (
                        <div className="mt-2 ml-2">
                          <details className="text-xs">
                            <summary className="text-gray-500 cursor-pointer hover:text-gray-700">
                              📋 Voir autres versions ({Object.keys(message.response_versions).length} disponibles)
                            </summary>
                            <div className="mt-2 space-y-2">
                              {Object.entries(message.response_versions).map(([level, content]) => {
                                if (content && content !== message.content) {
                                  const levelLabels = {
                                    ultra_concise: '⚡ Minimal',
                                    concise: '🎯 Concis', 
                                    standard: '📝 Standard',
                                    detailed: '📚 Détaillé'
                                  }
                                  return (
                                    <div key={level} className="p-2 bg-gray-50 rounded border-l-2 border-gray-300">
                                      <div className="text-xs font-medium text-gray-600 mb-1">
                                        {levelLabels[level as keyof typeof levelLabels] || level}
                                      </div>
                                      <div className="text-gray-700 text-sm">
                                        <ReactMarkdown
                                          className="prose prose-sm max-w-none prose-p:my-1 prose-li:my-0"
                                        >
                                          {content}
                                        </ReactMarkdown>
                                      </div>
                                    </div>
                                  )
                                }
                                return null
                              })}
                            </div>
                          </details>
                        </div>
                      )}
                      
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
                          <UserIcon className="w-5 h-5 text-white" />
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}

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

          <div className="px-4 py-4 bg-white border-t border-gray-100">
            <div className="max-w-4xl mx-auto">
              {clarificationState && (
                <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-blue-700 text-sm font-medium">
                      💡 Mode clarification : répondez à la question ci-dessus
                    </span>
                    <button
                      onClick={() => {
                        setClarificationState(null)
                        console.log('🔄 [ChatInterface] Clarification annulée')
                      }}
                      className="text-blue-600 hover:text-blue-800 text-sm underline"
                    >
                      Annuler
                    </button>
                  </div>
                </div>
              )}
              
              <div className="flex items-center space-x-3">
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
                    placeholder={clarificationState ? "Répondez à la question ci-dessus..." : t('chat.placeholder')}
                    className="w-full px-4 py-3 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm"
                    disabled={isLoadingChat}
                    aria-label={t('chat.placeholder')}
                  />
                </div>

                <button
                  onClick={() => handleSendMessage()}
                  disabled={isLoadingChat || !inputMessage.trim()}
                  className="flex-shrink-0 p-2 text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors"
                  title={isLoadingChat ? 'Envoi en cours...' : 'Envoyer le message'}
                  aria-label={isLoadingChat ? 'Envoi en cours...' : 'Envoyer le message'}
                >
                  <PaperAirplaneIcon />
                </button>
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