'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Message, ClarificationUtils } from './types'
import { useAuthStore } from './hooks/useAuthStore'
import { useTranslation } from './hooks/useTranslation'
import { useChatStore, useClarificationStore } from './hooks/useChatStore'
import { generateAIResponse, generateAIResponseWithClarifications } from './services/apiService'
import { conversationService } from './services/conversationService'
import { 
  PaperAirplaneIcon, 
  UserIcon, 
  PlusIcon, 
  InteliaLogo, 
  ArrowDownIcon,
  ThumbUpIcon,
  ThumbDownIcon
} from './utils/icons'
import { HistoryMenu } from './components/HistoryMenu'
import { UserMenuButton } from './components/UserMenuButton'
import { ZohoSalesIQ } from './components/ZohoSalesIQ'
import { FeedbackModal } from './components/modals/FeedbackModal'
import { ClarificationInline } from './components/ClarificationInline' // 🆕 COMPOSANT INLINE

// ==================== COMPOSANT PRINCIPAL AVEC CLARIFICATIONS INLINE ====================
export default function ChatInterface() {
  const { user, isAuthenticated, isLoading } = useAuthStore()
  const { t, currentLanguage } = useTranslation()
  
  // Store de chat unifié
  const {
    currentConversation,
    setCurrentConversation,
    addMessage,
    updateMessage,
    createNewConversation,
    loadConversations
  } = useChatStore()
  
  // 🆕 Store spécifique aux clarifications
  const {
    pendingClarification,
    isProcessingClarification,
    clarificationHistory,
    setPendingClarification,
    setIsProcessingClarification,
    addToClarificationHistory
  } = useClarificationStore()
  
  // États locaux pour l'interface
  const [inputMessage, setInputMessage] = useState('')
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const [isMobileDevice, setIsMobileDevice] = useState(false)
  
  // États pour le scroll intelligent
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true)
  const [isUserScrolling, setIsUserScrolling] = useState(false)
  const [showScrollButton, setShowScrollButton] = useState(false)
  
  // États pour la modal feedback
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

  // Messages à afficher
  const messages: Message[] = currentConversation?.messages || []
  const hasMessages = messages.length > 0

  // ==================== EFFECTS (IDENTIQUES) ====================
  
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
      setIsMobileDevice(detectMobileDevice())
    }
    
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    if (messages.length > lastMessageCountRef.current && shouldAutoScroll && !isUserScrolling) {
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
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
        setIsUserScrolling(false)
        isScrolling = false
      }, 150)
    }

    chatContainer.addEventListener('scroll', handleScroll, { passive: true })
    return () => {
      chatContainer.removeEventListener('scroll', handleScroll)
      clearTimeout(scrollTimeout)
    }
  }, [messages.length])

  useEffect(() => {
    if (isAuthenticated && !currentConversation && !hasMessages) {
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
        currentConversation.messages[0].content !== t('chat.welcome')) {
      
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
    console.log('❓ Conversation changée, force re-render')
  }, [currentConversation?.messages?.length, currentConversation?.id])

  useEffect(() => {
    if (isAuthenticated && user?.id) {
      const loadTimer = setTimeout(() => {
        console.log('❓ [ChatInterface] Chargement historique pour:', user.id)
        loadConversations(user.id)
          .then(() => console.log('✅ Historique conversations chargé'))
          .catch(err => console.error('❌ Erreur chargement historique:', err))
      }, 800)

      return () => clearTimeout(loadTimer)
    }
  }, [isAuthenticated, user?.id, loadConversations])

  // ==================== HANDLERS MODIFIÉS AVEC CLARIFICATIONS INLINE ====================

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

  // 🆕 HANDLER PRINCIPAL MODIFIÉ POUR GÉRER LES CLARIFICATIONS
  const handleSendMessage = async (text: string = inputMessage) => {
    if (!text.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: text.trim(),
      isUser: true,
      timestamp: new Date()
    }

    let conversationIdToSend: string | undefined = undefined
    let isFirstMessage = false

    if (!currentConversation || currentConversation.id === 'welcome') {
      isFirstMessage = true
    } else if (currentConversation.id && !currentConversation.id.startsWith('temp-') && !currentConversation.id.startsWith('welcome')) {
      conversationIdToSend = currentConversation.id
    } else {
      isFirstMessage = true
    }

    addMessage(userMessage)
    setInputMessage('')
    setIsLoadingChat(true)
    
    setShouldAutoScroll(true)
    setIsUserScrolling(false)

    try {
      console.log('🚀 [ChatInterface] Envoi question avec gestion clarifications inline')
      
      const response = await generateAIResponse(
        text.trim(), 
        user, 
        currentLanguage, 
        conversationIdToSend
      )

      console.log('📨 [ChatInterface] Réponse reçue:', {
        is_clarification: response.is_clarification_request,
        questions_count: response.clarification_questions?.length || 0,
        mode: response.mode
      })

      // 🆕 VÉRIFIER SI C'EST UNE DEMANDE DE CLARIFICATION
      if (response.is_clarification_request && response.clarification_questions && response.clarification_questions.length > 0) {
        console.log('❓ [ChatInterface] Clarification détectée - affichage inline')
        
        // Ajouter le message de clarification avec composant inline
        const clarificationMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.response,
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id,
          is_clarification_request: true,
          clarification_questions: response.clarification_questions,
          original_question: text.trim()
        }

        addMessage(clarificationMessage)
        
        // Stocker la clarification en attente
        setPendingClarification(response)
        
        // Mise à jour de la conversation si c'est le premier message
        if (isFirstMessage && response.conversation_id && currentConversation) {
          const updatedConversation = {
            ...currentConversation,
            id: response.conversation_id,
            title: text.trim().substring(0, 60) + (text.trim().length > 60 ? '...' : ''),
            updated_at: new Date().toISOString()
          }
          
          setCurrentConversation(updatedConversation)
        }
        
      } else {
        // Réponse normale sans clarification
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.response,
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id
        }

        addMessage(aiMessage)

        if (isFirstMessage && response.conversation_id && currentConversation) {
          const updatedConversation = {
            ...currentConversation,
            id: response.conversation_id,
            title: text.trim().substring(0, 60) + (text.trim().length > 60 ? '...' : ''),
            updated_at: new Date().toISOString()
          }
          
          setCurrentConversation(updatedConversation)
        }
      }
        
    } catch (error) {
      console.error('❌ [handleSendMessage] Erreur:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: error instanceof Error ? error.message : t('chat.errorMessage'),
        isUser: false,
        timestamp: new Date()
      }
      addMessage(errorMessage)
    } finally {
      setIsLoadingChat(false)
    }
  }

  // 🆕 HANDLER POUR SOUMETTRE LES RÉPONSES DE CLARIFICATION INLINE
  const handleClarificationSubmit = async (answers: Record<string, string>) => {
    if (!pendingClarification) {
      console.warn('❓ [ChatInterface] Aucune clarification en attente')
      return
    }

    try {
      setIsProcessingClarification(true)
      
      const originalQuestion = pendingClarification.question
      const clarificationQuestions = pendingClarification.clarification_questions || []
      
      console.log('❓ [ChatInterface] Soumission clarification inline:', {
        original: originalQuestion.substring(0, 50) + '...',
        answers_count: Object.keys(answers).length,
        questions_count: clarificationQuestions.length
      })

      // Construire la question enrichie
      const enrichedQuestion = ClarificationUtils.buildEnrichedQuestion(
        originalQuestion,
        answers,
        clarificationQuestions
      )

      console.log('📝 [ChatInterface] Question enrichie:', enrichedQuestion.substring(0, 200) + '...')

      // Soumettre la question enrichie
      const response = await generateAIResponseWithClarifications(
        originalQuestion,
        answers,
        clarificationQuestions,
        user,
        currentLanguage,
        pendingClarification.conversation_id
      )

      // Ajouter la réponse finale
      const finalMessage: Message = {
        id: Date.now().toString(),
        content: response.response,
        isUser: false,
        timestamp: new Date(),
        conversation_id: response.conversation_id
      }

      addMessage(finalMessage)

      // Ajouter à l'historique des clarifications
      addToClarificationHistory({
        original_question: originalQuestion,
        clarification_questions: clarificationQuestions,
        answers: answers,
        final_response: response.response,
        timestamp: new Date().toISOString()
      })

      // Nettoyer l'état de clarification
      setPendingClarification(null)

      console.log('✅ [ChatInterface] Clarification traitée avec succès')
      
      // Auto-scroll vers la réponse
      setTimeout(() => {
        setShouldAutoScroll(true)
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
      }, 300)
      
    } catch (error) {
      console.error('❌ [ChatInterface] Erreur traitement clarification:', error)
      const errorMessage: Message = {
        id: Date.now().toString(),
        content: error instanceof Error ? error.message : 'Erreur lors du traitement de la clarification',
        isUser: false,
        timestamp: new Date()
      }
      addMessage(errorMessage)
    } finally {
      setIsProcessingClarification(false)
    }
  }

  // 🆕 HANDLER POUR IGNORER LES CLARIFICATIONS INLINE
  const handleClarificationSkip = async () => {
    if (!pendingClarification) return

    try {
      setIsProcessingClarification(true)
      
      console.log('⏭️ [ChatInterface] Ignore clarification inline, traitement question originale')

      // Traiter la question originale avec un indicateur de skip
      const skipQuestion = pendingClarification.question + " [RÉPONSE_GÉNÉRALE_DEMANDÉE]"
      
      const response = await generateAIResponse(
        skipQuestion,
        user,
        currentLanguage,
        pendingClarification.conversation_id
      )

      // Ajouter la réponse générale
      const generalMessage: Message = {
        id: Date.now().toString(),
        content: response.response,
        isUser: false,
        timestamp: new Date(),
        conversation_id: response.conversation_id
      }

      addMessage(generalMessage)

      // Nettoyer l'état de clarification
      setPendingClarification(null)

      console.log('✅ [ChatInterface] Réponse générale fournie')
      
      // Auto-scroll vers la réponse
      setTimeout(() => {
        setShouldAutoScroll(true)
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
      }, 300)
      
    } catch (error) {
      console.error('❌ [ChatInterface] Erreur skip clarification:', error)
      const errorMessage: Message = {
        id: Date.now().toString(),
        content: 'Erreur lors du traitement de votre question',
        isUser: false,
        timestamp: new Date()
      }
      addMessage(errorMessage)
    } finally {
      setIsProcessingClarification(false)
    }
  }

  // ==================== HANDLERS FEEDBACK (IDENTIQUES) ====================

  const handleFeedbackClick = (messageId: string, feedback: 'positive' | 'negative') => {
    setFeedbackModal({
      isOpen: true,
      messageId,
      feedbackType: feedback
    })
  }

  const handleFeedbackSubmit = async (feedback: 'positive' | 'negative', comment?: string) => {
    const { messageId } = feedbackModal
    if (!messageId) return

    const message = messages.find(msg => msg.id === messageId)
    if (!message || !message.conversation_id) {
      console.warn('❓ Conversation ID non trouvé pour le feedback', messageId)
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
            console.warn('❓ Commentaire non envoyé (endpoint manquant):', commentError)
          }
        }
      } catch (feedbackError) {
        console.error('❌ Erreur envoi feedback:', feedbackError)
        updateMessage(messageId, { 
          feedback: null,
          feedbackComment: undefined 
        })
        throw feedbackError
      }
      
    } catch (error) {
      console.error('❌ Erreur générale feedback:', error)
      throw error
    } finally {
      setIsSubmittingFeedback(false)
    }
  }

  const handleFeedbackModalClose = () => {
    setFeedbackModal({
      isOpen: false,
      messageId: null,
      feedbackType: null
    })
  }

  // ==================== AUTRES HANDLERS (IDENTIQUES) ====================

  const handleNewConversation = () => {
    createNewConversation()
    
    // 🆕 Nettoyer aussi les clarifications en attente
    setPendingClarification(null)
    
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

  // ==================== RENDER AVEC CLARIFICATIONS INLINE ====================
  return (
    <>
      <ZohoSalesIQ user={user} language={currentLanguage} />

      <div className="h-screen bg-gray-50 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-100 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <HistoryMenu />
              <button
                onClick={handleNewConversation}
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
                {currentConversation && currentConversation.id !== 'welcome' && (
                  <p className="text-xs text-gray-500 truncate max-w-xs">
                    {currentConversation.title}
                  </p>
                )}
              </div>
            </div>
            
            <div className="flex items-center">
              <UserMenuButton />
            </div>
          </div>
        </header>

        {/* Zone de messages */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <div 
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto px-4 py-6"
          >
            <div className="max-w-4xl mx-auto space-y-6">
              {/* DEBUG temporaire */}
              <div className="text-xs text-gray-400 text-center">
                DEBUG: {messages.length} messages - Conversation: {currentConversation?.id}
                {pendingClarification && (
                  <span className="text-yellow-600"> - Clarification en attente</span>
                )}
                {isProcessingClarification && (
                  <span className="text-blue-600"> - Traitement clarification...</span>
                )}
              </div>

              {/* Date */}
              {hasMessages && (
                <div className="text-center">
                  <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                    {getCurrentDate()}
                  </span>
                </div>
              )}

              {/* Indicateur conversation si pas bienvenue */}
              {currentConversation && currentConversation.id !== 'welcome' && (
                <div className="text-center">
                  <div className="inline-flex items-center space-x-2 text-xs text-blue-600 bg-blue-50 px-3 py-2 rounded-full">
                    <span>💬</span>
                    <span>Conversation : {currentConversation.title}</span>
                    <span className="text-blue-400">({currentConversation.message_count} messages)</span>
                  </div>
                </div>
              )}

              {/* Messages */}
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <div className="text-sm">Aucun message à afficher</div>
                </div>
              ) : (
                messages.map((message, index) => (
                  <div key={`${message.id}-${index}`}>
                    {/* Message normal */}
                    <div className={`flex items-start space-x-3 ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                      {!message.isUser && (
                        <div className="relative">
                          <InteliaLogo className="w-8 h-8 flex-shrink-0 mt-1" />
                          {/* 🆕 Indicateur de clarification */}
                          {message.is_clarification_request && (
                            <div className="absolute -top-1 -right-1 w-4 h-4 bg-yellow-500 rounded-full flex items-center justify-center">
                              <span className="text-xs text-white">❓</span>
                            </div>
                          )}
                        </div>
                      )}
                      
                      <div className="max-w-xs lg:max-w-2xl">
                        <div className={`px-4 py-3 rounded-2xl ${message.isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-white border border-gray-200 text-gray-900'}`}>
                          <p className="whitespace-pre-wrap leading-relaxed text-sm">
                            {message.content}
                          </p>
                        </div>
                        
                        {/* Boutons de feedback (seulement pour les réponses normales) */}
                        {!message.isUser && index > 0 && message.conversation_id && !message.is_clarification_request && (
                          <div className="flex items-center space-x-2 mt-2 ml-2">
                            <button
                              onClick={() => handleFeedbackClick(message.id, 'positive')}
                              className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${
                                message.feedback === 'positive' ? 'text-green-600 bg-green-50' : 'text-gray-400'
                              }`}
                              title={t('chat.helpfulResponse')}
                            >
                              <ThumbUpIcon />
                            </button>
                            <button
                              onClick={() => handleFeedbackClick(message.id, 'negative')}
                              className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${
                                message.feedback === 'negative' ? 'text-red-600 bg-red-50' : 'text-gray-400'
                              }`}
                              title={t('chat.notHelpfulResponse')}
                            >
                              <ThumbDownIcon />
                            </button>
                            
                            {/* Status feedback */}
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
                      </div>

                      {message.isUser && (
                        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                          <UserIcon className="w-5 h-5 text-white" />
                        </div>
                      )}
                    </div>
                    
                    {/* 🆕 COMPOSANT DE CLARIFICATION INLINE */}
                    {message.is_clarification_request && 
                     !message.isUser && 
                     message.clarification_questions && 
                     message.clarification_questions.length > 0 && (
                      <div className="mt-4">
                        <ClarificationInline
                          questions={message.clarification_questions}
                          originalQuestion={message.original_question || ''}
                          language={currentLanguage}
                          onSubmit={handleClarificationSubmit}
                          onSkip={handleClarificationSkip}
                          isSubmitting={isProcessingClarification}
                          conversationId={message.conversation_id}
                        />
                      </div>
                    )}
                  </div>
                ))
              )}

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

          {/* Bouton flottant scroll */}
          {showScrollButton && (
            <div className="fixed bottom-24 right-8 z-10">
              <button
                onClick={scrollToBottom}
                className="bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 transition-colors"
                title="Revenir en bas"
              >
                <ArrowDownIcon />
              </button>
            </div>
          )}

          {/* Zone de saisie */}
          <div className="px-4 py-4 bg-white border-t border-gray-100">
            <div className="max-w-4xl mx-auto">
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
                    placeholder={t('chat.placeholder')}
                    className="w-full px-4 py-3 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm"
                    disabled={isLoadingChat || isProcessingClarification}
                  />
                </div>

                <button
                  onClick={() => handleSendMessage()}
                  disabled={isLoadingChat || isProcessingClarification || !inputMessage.trim()}
                  className="flex-shrink-0 p-2 text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors"
                >
                  <PaperAirplaneIcon />
                </button>
              </div>
              
              {/* 🆕 Indicateur de clarification en cours */}
              {isProcessingClarification && (
                <div className="mt-2 text-center">
                  <span className="text-xs text-yellow-600 bg-yellow-50 px-3 py-1 rounded-full">
                    ⚙️ Traitement de la clarification en cours...
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Modal Feedback (conservée) */}
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