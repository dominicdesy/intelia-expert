'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Message } from './types'
import { useAuthStore } from './hooks/useAuthStore'
import { useTranslation } from './hooks/useTranslation'
import { useChatStore } from './hooks/useChatStore'
// ✅ IMPORT CORRIGÉ: Ajouter buildClarificationEntities
import { generateAIResponse, buildClarificationEntities } from './services/apiService'
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
// ✅ IMPORT NOUVEAU: Composant clarification existant
import { ClarificationInline } from './components/ClarificationInlineComponent'

export default function ChatInterface() {
  const { user, isAuthenticated, isLoading } = useAuthStore()
  const { t, currentLanguage } = useTranslation()
  
  // ✅ SÉLECTEURS ZUSTAND RÉACTIFS
  const currentConversation = useChatStore(state => state.currentConversation)
  const setCurrentConversation = useChatStore(state => state.setCurrentConversation)
  const addMessage = useChatStore(state => state.addMessage)
  const updateMessage = useChatStore(state => state.updateMessage)
  const createNewConversation = useChatStore(state => state.createNewConversation)
  const loadConversations = useChatStore(state => state.loadConversations)
  
  const [inputMessage, setInputMessage] = useState('')
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const [isMobileDevice, setIsMobileDevice] = useState(false)
  
  // ✅ NOUVEAU: État pour les clarifications
  const [clarificationState, setClarificationState] = useState<{
    messageId: string
    originalQuestion: string
    clarificationQuestions: string[]
  } | null>(null)
  const [isProcessingClarification, setIsProcessingClarification] = useState(false)
  
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
  
  // ✅ REFS POUR CONTRÔLE DU COMPOSANT
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const lastMessageCountRef = useRef(0)
  const isMountedRef = useRef(true)
  const hasRedirectedRef = useRef(false)

  const messages: Message[] = currentConversation?.messages || []
  const hasMessages = messages.length > 0

  console.log('🔍 [Render] Messages actuels:', messages.length, 'Conversation ID:', currentConversation?.id)

  // ✅ EFFET POUR MARQUER LE COMPOSANT COMME MONTÉ
  useEffect(() => {
    isMountedRef.current = true
    
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // ✅ GESTION DE LA REDIRECTION SÉCURISÉE
  useEffect(() => {
    if (!isLoading && !isAuthenticated && !hasRedirectedRef.current) {
      hasRedirectedRef.current = true
      console.log('🔄 [ChatInterface] Redirection - utilisateur non authentifié')
      
      // Redirection immédiate et sécurisée
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

  // ✅ LOADING STATE SÉCURISÉ
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

  // ✅ ÉTAT NON AUTHENTIFIÉ SIMPLIFIÉ
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

  // 🎯 FONCTION CORRIGÉE: handleSendMessage avec détection clarification_result
  const handleSendMessage = async (text: string = inputMessage) => {
    if (!text.trim() || !isMountedRef.current) return

    console.log('📤 [ChatInterface] Envoi message:', {
      text: text.substring(0, 50) + '...',
      hasClarificationState: !!clarificationState,
      isAnsweringClarification: !!clarificationState
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
      console.log('🔄 [handleSendMessage] Continuation conversation existante:', conversationIdToSend)
    } else {
      console.log('🆕 [handleSendMessage] Première question - nouvelle conversation')
    }

    addMessage(userMessage)
    setInputMessage('')
    setIsLoadingChat(true)
    
    setShouldAutoScroll(true)
    setIsUserScrolling(false)

    try {
      console.log('📤 [handleSendMessage] Envoi à API avec conversation_id:', conversationIdToSend || 'nouveau')
      
      // 🎯 CORRECTION CRITIQUE: Vérifier si on répond à une clarification
      let response;
      
      if (clarificationState) {
        console.log('🎪 [handleSendMessage] Mode clarification - enrichissement question')
        
        // ✅ CONSTRUIRE LES ENTITÉS DEPUIS LA RÉPONSE
        const answers: Record<string, string> = { '0': text.trim() } // Réponse simple
        const clarificationEntities = buildClarificationEntities(
          answers, 
          clarificationState.clarificationQuestions
        )

        // ✅ APPEL AVEC PARAMÈTRES DE CLARIFICATION
        response = await generateAIResponse(
          clarificationState.originalQuestion,  // Question originale
          user,
          currentLanguage,
          conversationIdToSend,
          true,                                // ✅ isClarificationResponse = true
          clarificationState.originalQuestion, // originalQuestion
          clarificationEntities               // clarificationEntities
        )
        
        // ✅ RÉINITIALISER L'ÉTAT DE CLARIFICATION
        setClarificationState(null)
        console.log('✅ [handleSendMessage] Clarification traitée et état réinitialisé')
        
      } else {
        // ✅ APPEL NORMAL POUR NOUVELLE QUESTION
        response = await generateAIResponse(
          text.trim(), 
          user, 
          currentLanguage, 
          conversationIdToSend
        )
      }

      if (!isMountedRef.current) {
        console.log('⚠️ [handleSendMessage] Composant démonté, abandon')
        return
      }

      console.log('📥 [handleSendMessage] Réponse API reçue:', {
        conversation_id: response.conversation_id,
        response_length: response.response?.length || 0,
        // 🎯 CORRECTION: Vérifier clarification_result au lieu de requires_clarification
        clarification_requested: response.clarification_result?.clarification_requested || false,
        clarification_questions_count: response.clarification_questions?.length || 0
      })

      // 🎯 CORRECTION MAJEURE: Détecter clarification via clarification_result
      const needsClarification = response.clarification_result?.clarification_requested === true &&
                                response.clarification_questions && 
                                response.clarification_questions.length > 0

      if (needsClarification) {
        console.log('❓ [handleSendMessage] Clarifications détectées via clarification_result:', response.clarification_questions)
        
        // ✅ MESSAGE IA AVEC DEMANDE DE CLARIFICATION DIRECTEMENT DANS LE CHAT
        const clarificationMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.response,
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id,
          // ✅ MARQUEURS POUR CLARIFICATION
          is_clarification_request: true,
          clarification_questions: response.clarification_questions,
          original_question: text.trim()
        }

        addMessage(clarificationMessage)

        // ✅ ACTIVER L'ÉTAT DE CLARIFICATION POUR AFFICHAGE INLINE
        setClarificationState({
          messageId: clarificationMessage.id,
          originalQuestion: text.trim(),
          clarificationQuestions: response.clarification_questions
        })

        console.log('🔄 [handleSendMessage] État clarification activé pour message:', clarificationMessage.id)

      } else {
        // ✅ RÉPONSE NORMALE SANS CLARIFICATION
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.response,
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id
        }

        addMessage(aiMessage)
        console.log('✅ [handleSendMessage] Message normal ajouté')
      }

      if (!conversationIdToSend && response.conversation_id) {
        console.log('🆕 [handleSendMessage] Nouvelle conversation créée:', response.conversation_id)
      } else {
        console.log('✅ [handleSendMessage] Conversation existante mise à jour:', response.conversation_id)
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

  // ✅ FONCTION SIMPLIFIÉE: Traitement des réponses de clarification DIRECTEMENT dans le chat
  const handleClarificationSubmit = async (answers: Record<string, string>) => {
    if (!clarificationState || !isMountedRef.current) {
      console.warn('⚠️ [handleClarificationSubmit] Pas d\'état de clarification')
      return
    }

    console.log('🔍 [handleClarificationSubmit] Traitement simple dans le chat:', {
      answers,
      originalQuestion: clarificationState.originalQuestion
    })
    
    // ✅ CONSTRUIRE UNE RÉPONSE TEXTUELLE SIMPLE
    let clarificationText = ""
    Object.entries(answers).forEach(([index, answer]) => {
      if (answer && answer.trim()) {
        clarificationText += answer.trim() + " "
      }
    })

    if (!clarificationText.trim()) {
      console.warn('⚠️ [handleClarificationSubmit] Réponse vide')
      return
    }

    // ✅ ENVOYER LA RÉPONSE COMME MESSAGE NORMAL DANS LE CHAT
    // L'état clarificationState va faire que handleSendMessage traite ça comme une clarification
    await handleSendMessage(clarificationText.trim())
  }

  // ✅ FONCTION SIMPLIFIÉE: Ignorer les clarifications
  const handleClarificationSkip = async () => {
    if (!clarificationState || !isMountedRef.current) {
      console.warn('⚠️ [handleClarificationSkip] Pas d\'état de clarification')
      return
    }

    console.log('⏭️ [handleClarificationSkip] Clarifications ignorées')
    
    // ✅ RÉINITIALISER L'ÉTAT ET RELANCER LA QUESTION ORIGINALE
    const originalQuestion = clarificationState.originalQuestion
    setClarificationState(null)
    
    // Envoyer une demande de réponse générale
    await handleSendMessage(originalQuestion + " (donnez-moi une réponse générale)")
  }

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
    
    // ✅ RÉINITIALISER L'ÉTAT DE CLARIFICATION
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
              <button
                onClick={handleNewConversation}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title={t('nav.newConversation')}
                aria-label={t('nav.newConversation')}
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
                      
                      <div className="max-w-xs lg:max-w-2xl">
                        <div className={`px-4 py-3 rounded-2xl ${message.isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-white border border-gray-200 text-gray-900'}`}>
                          <p className="whitespace-pre-wrap leading-relaxed text-sm">
                            {message.content}
                          </p>
                        </div>
                        
                        {/* 🎯 AFFICHAGE DES CLARIFICATIONS INLINE DANS LE CHAT */}
                        {message.is_clarification_request && 
                         message.clarification_questions && 
                         message.clarification_questions.length > 0 && 
                         clarificationState?.messageId === message.id && (
                          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                            <div className="mb-3">
                              <p className="text-sm text-blue-800 font-medium">
                                💡 Pour vous donner une réponse précise, j'ai besoin de quelques précisions :
                              </p>
                            </div>
                            
                            <ClarificationInline
                              questions={message.clarification_questions}
                              originalQuestion={clarificationState.originalQuestion}
                              language={currentLanguage}
                              onSubmit={handleClarificationSubmit}
                              onSkip={handleClarificationSkip}
                              isSubmitting={isProcessingClarification}
                              conversationId={message.conversation_id}
                            />
                          </div>
                        )}
                        
                        {/* ✅ FEEDBACK BUTTONS - Seulement si ce n'est pas une demande de clarification */}
                        {!message.isUser && 
                         index > 0 && 
                         message.conversation_id && 
                         !message.is_clarification_request && (
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
                      </div>

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
              {/* 🎯 AFFICHAGE INDICATEUR CLARIFICATION SIMPLE */}
              {clarificationState && (
                <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-blue-700 text-sm font-medium">
                      💡 Répondez aux questions ci-dessus ou tapez votre réponse directement
                    </span>
                    <button
                      onClick={() => {
                        setClarificationState(null)
                        console.log('🔄 [ChatInterface] État clarification réinitialisé manuellement')
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
                    placeholder={clarificationState ? "Répondez à la question ci-dessus ou tapez votre réponse..." : t('chat.placeholder')}
                    className="w-full px-4 py-3 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm"
                    disabled={isLoadingChat || isProcessingClarification}
                    aria-label={t('chat.placeholder')}
                  />
                </div>

                <button
                  onClick={() => handleSendMessage()}
                  disabled={isLoadingChat || isProcessingClarification || !inputMessage.trim()}
                  className="flex-shrink-0 p-2 text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors"
                  title={isLoadingChat || isProcessingClarification ? 'Envoi en cours...' : 'Envoyer le message'}
                  aria-label={isLoadingChat || isProcessingClarification ? 'Envoi en cours...' : 'Envoyer le message'}
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