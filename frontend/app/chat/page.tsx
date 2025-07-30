'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Message } from './types'
import { useAuthStore } from './hooks/useAuthStore'
import { useTranslation } from './hooks/useTranslation'
import { useCurrentConversation, useConversationActions, useChatStore } from './hooks/useChatStore'
import { generateAIResponse } from './services/apiService'
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

// ==================== COMPOSANT PRINCIPAL AVEC GESTION CONVERSATIONS ====================
export default function ChatInterface() {
  const { user, isAuthenticated, isLoading } = useAuthStore()
  const { t, currentLanguage } = useTranslation()
  
  // ✅ Hooks pour conversations
  const { currentConversation, setCurrentConversation, addMessage, updateMessage } = useCurrentConversation()
  const { createNewConversation } = useConversationActions()
  const { loadConversations } = useChatStore()
  
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

  // ✅ Calculer les messages à afficher
  const messages: Message[] = currentConversation?.messages || []
  const hasMessages = messages.length > 0

  // ==================== EFFECTS ====================
  
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
  }, [messages.length, shouldAutoScroll, isUserScrolling])

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

  // ✅ Effect pour initialiser une conversation vide au démarrage
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

  // ✅ Effect pour mettre à jour le message de bienvenue lors du changement de langue
  useEffect(() => {
    if (currentConversation?.id === 'welcome' && currentConversation.messages.length === 1) {
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

  // ✅ Effect pour charger l'historique des conversations au démarrage
  useEffect(() => {
    if (isAuthenticated && user?.id) {
      const loadTimer = setTimeout(() => {
        console.log('🔄 [ChatInterface] Chargement historique pour:', user.id)
        loadConversations(user.id)
          .then(() => console.log('✅ Historique conversations chargé'))
          .catch(err => console.error('❌ Erreur chargement historique:', err))
      }, 800)

      return () => clearTimeout(loadTimer)
    }
  }, [isAuthenticated, user?.id, loadConversations])

  // ==================== HANDLERS ====================

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

  // ✅ CORRECTION FINALE: handleSendMessage simplifié sans logs qui causent la boucle
  const handleSendMessage = async (text: string = inputMessage) => {
    if (!text.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: text.trim(),
      isUser: true,
      timestamp: new Date()
    }

    // Détection du type de conversation
    let conversationIdToSend: string | undefined = undefined
    let isFirstMessage = false

    if (!currentConversation || currentConversation.id === 'welcome') {
      isFirstMessage = true
    } else if (currentConversation.id && !currentConversation.id.startsWith('temp-') && !currentConversation.id.startsWith('welcome')) {
      conversationIdToSend = currentConversation.id
    } else {
      isFirstMessage = true
    }

    // Ajouter le message utilisateur
    addMessage(userMessage)
    setInputMessage('')
    setIsLoadingChat(true)
    
    setShouldAutoScroll(true)
    setIsUserScrolling(false)

    try {
      const response = await generateAIResponse(
        text.trim(), 
        user, 
        currentLanguage, 
        conversationIdToSend
      )

      console.log('🔥 APRÈS API - avant addMessage')

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.response,
        isUser: false,
        timestamp: new Date(),
        conversation_id: response.conversation_id
      }

      console.log('🔥 AVANT addMessage - message créé')
      addMessage(aiMessage)
      console.log('🔥 APRÈS addMessage')

      if (isFirstMessage && response.conversation_id && currentConversation) {
        const updatedConversation = {
          ...currentConversation,
          id: response.conversation_id,
          title: text.trim().substring(0, 60) + (text.trim().length > 60 ? '...' : ''),
          updated_at: new Date().toISOString()
        }
        
        setCurrentConversation(updatedConversation)
        console.log('🔥 CONVERSATION MISE À JOUR')
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

  // ✅ GESTION FEEDBACK (conservée)
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
      console.warn('⚠️ Conversation ID non trouvé pour le feedback', messageId)
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
            console.warn('⚠️ Commentaire non envoyé (endpoint manquant):', commentError)
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

  // ✅ Gestion nouvelle conversation
  const handleNewConversation = () => {
    createNewConversation()
    
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

  // ==================== RENDER ====================
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
                    <span>📖</span>
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
                        {!message.isUser && index > 0 && message.conversation_id && (
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

      {/* Modal Feedback */}
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