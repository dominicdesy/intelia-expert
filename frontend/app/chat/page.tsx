'use client'

import React, { useState, useEffect, useRef } from 'react'
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
  ThumbDownIcon
} from './utils/icons'
import { HistoryMenu } from './components/HistoryMenu'
import { UserMenuButton } from './components/UserMenuButton'
import { ZohoSalesIQ } from './components/ZohoSalesIQ'
import { FeedbackModal } from './components/modals/FeedbackModal'

// ==================== COMPOSANT PRINCIPAL AVEC MODAL FEEDBACK ====================
export default function ChatInterface() {
  const { user, isAuthenticated, isLoading } = useAuthStore()
  const { t, currentLanguage } = useTranslation()
  const { addConversation } = useChatStore()
  
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const [isMobileDevice, setIsMobileDevice] = useState(false)
  
  // États pour le scroll intelligent
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true)
  const [isUserScrolling, setIsUserScrolling] = useState(false)
  const [showScrollButton, setShowScrollButton] = useState(false)
  
  // ✅ NOUVEAUX ÉTATS POUR LA MODAL FEEDBACK
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

  // [TOUT LE CODE DE DÉTECTION MOBILE ET SCROLL RESTE IDENTIQUE]
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
  }, [messages.length])

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
    if (isAuthenticated && messages.length === 0) {
      const welcomeMessage: Message = {
        id: '1',
        content: t('chat.welcome'),
        isUser: false,
        timestamp: new Date()
      }
      
      setMessages([welcomeMessage])
      lastMessageCountRef.current = 1
    }
  }, [isAuthenticated, t, currentLanguage])

  useEffect(() => {
    if (messages.length > 0 && messages[0].id === '1' && !messages[0].isUser) {
      setMessages(prev => prev.map((msg, index) => 
        index === 0 ? { ...msg, content: t('chat.welcome') } : msg
      ))
    }
  }, [currentLanguage, t])

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

  // FONCTION ENVOI DE MESSAGE (RESTE IDENTIQUE)
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
    
    setShouldAutoScroll(true)
    setIsUserScrolling(false)

    try {
      console.log('🔒 [handleSendMessage] Envoi question avec langue:', currentLanguage)
      
      const response = await generateAIResponse(text.trim(), user, currentLanguage)
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.response,
        isUser: false,
        timestamp: new Date(),
        conversation_id: response.conversation_id
      }

      setMessages(prev => [...prev, aiMessage])
      console.log('✅ [handleSendMessage] Message ajouté avec conversation_id:', response.conversation_id)
      
      if (user && response.conversation_id) {
        addConversation(response.conversation_id, text.trim(), response.response)
      }
      
    } catch (error) {
      console.error('❌ [handleSendMessage] Error generating response:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: error instanceof Error ? error.message : t('chat.errorMessage'),
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoadingChat(false)
    }
  }

  // ✅ NOUVELLE FONCTION GESTION FEEDBACK AVEC MODAL
  const handleFeedbackClick = (messageId: string, feedback: 'positive' | 'negative') => {
    console.log('👆 [handleFeedbackClick] Ouverture modal feedback:', messageId, feedback)
    
    setFeedbackModal({
      isOpen: true,
      messageId,
      feedbackType: feedback
    })
  }

  // ✅ FONCTION SOUMISSION FEEDBACK AVEC COMMENTAIRE
  const handleFeedbackSubmit = async (feedback: 'positive' | 'negative', comment?: string) => {
    const { messageId } = feedbackModal
    if (!messageId) return

    const message = messages.find(msg => msg.id === messageId)
    if (!message || !message.conversation_id) {
      console.warn('⚠️ Conversation ID non trouvé pour le feedback', messageId)
      alert('Impossible d\'enregistrer le feedback - ID de conversation manquant')
      return
    }

    setIsSubmittingFeedback(true)
    try {
      console.log('📊 [handleFeedbackSubmit] Envoi feedback avec commentaire:', {
        conversation_id: message.conversation_id,
        feedback,
        comment: comment || 'Aucun commentaire'
      })
      
      // ✅ MISE À JOUR IMMÉDIATE DE L'UI
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { 
          ...msg, 
          feedback,
          feedbackComment: comment 
        } : msg
      ))

      // ✅ ENVOIS SÉPARÉS : FEEDBACK + COMMENTAIRE (SI FOURNI)
      const feedbackValue = feedback === 'positive' ? 1 : -1
      
      // 1. Envoyer le feedback principal
      await conversationService.sendFeedback(message.conversation_id, feedbackValue)
      console.log('✅ Feedback principal enregistré')

      // 2. Envoyer le commentaire si fourni (extension future du service)
      if (comment && comment.trim()) {
        try {
          // Essayer d'envoyer le commentaire (méthode à développer côté serveur)
          await conversationService.sendFeedbackComment(message.conversation_id, comment.trim())
          console.log('✅ Commentaire feedback enregistré')
        } catch (commentError) {
          console.warn('⚠️ Commentaire non envoyé (endpoint manquant):', commentError)
          // Le feedback principal est déjà enregistré, continuer
        }
      }
      
      console.log(`✅ Feedback ${feedback} avec commentaire enregistré pour conversation ${message.conversation_id}`)
      
    } catch (error) {
      console.error('❌ Erreur envoi feedback:', error)
      
      // ✅ ROLLBACK EN CAS D'ERREUR
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { 
          ...msg, 
          feedback: null,
          feedbackComment: undefined 
        } : msg
      ))
      
      alert('Erreur lors de l\'envoi du feedback. Veuillez réessayer.')
    } finally {
      setIsSubmittingFeedback(false)
    }
  }

  // ✅ FERMETURE MODAL FEEDBACK
  const handleFeedbackModalClose = () => {
    setFeedbackModal({
      isOpen: false,
      messageId: null,
      feedbackType: null
    })
  }

  // [AUTRES FONCTIONS RESTENT IDENTIQUES]
  const handleNewConversation = () => {
    const welcomeMessage = {
      id: '1',
      content: t('chat.welcome'),
      isUser: false,
      timestamp: new Date()
    }
    
    setMessages([welcomeMessage])
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

  // [LE RESTE DU COMPOSANT AVEC MODAL AJOUTÉE]
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
              </div>
            </div>
            
            <div className="flex items-center">
              <UserMenuButton />
            </div>
          </div>
        </header>

        {/* Zone de messages avec scroll intelligent */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <div 
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto px-4 py-6"
          >
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
                      
                      {/* ✅ BOUTONS DE FEEDBACK AVEC MODAL - CORRIGÉS */}
                      {!message.isUser && index > 0 && message.conversation_id && (
                        <div className="flex items-center space-x-2 mt-2 ml-2">
                          <button
                            onClick={() => {
                              console.log('👍 Clic bouton positif pour message:', message.id)
                              handleFeedbackClick(message.id, 'positive')
                            }}
                            className={`p-1.5 rounded-full transition-colors ${
                              message.feedback === 'positive' 
                                ? 'text-green-600 bg-green-50' 
                                : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
                            }`}
                            title="Cette réponse est utile"
                            disabled={message.feedback !== null}
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 .75-.75 2.25 2.25 0 0 1 2.25 2.25c0 1.152-.26 2.243-.723 3.218-.266.558-.641 1.05-1.085 1.441-.807.71-1.96 1.398-3.092 1.75a4.5 4.5 0 0 0-2.592 1.33c-.284.29-.568.606-.725.936-.12.253-.18.526-.18.801 0 .546.146 1.069.378 1.526.209.417.49.777.84 1.047.35.27.747.447 1.177.447h.462c1.097 0 2.137.462 2.86 1.273a3.73 3.73 0 0 1 1.14 2.677v.462A.75.75 0 0 1 12 21.75h-3.75a.75.75 0 0 1-.75-.75v-.462c0-.552-.11-1.098-.322-1.598-.202-.477-.497-.9-.878-1.235a3.75 3.75 0 0 1-1.28-2.83c0-.552.11-1.098.322-1.598.202-.477.497-.9.878-1.235z" />
                            </svg>
                          </button>
                          
                          <button
                            onClick={() => {
                              console.log('👎 Clic bouton négatif pour message:', message.id)
                              handleFeedbackClick(message.id, 'negative')
                            }}
                            className={`p-1.5 rounded-full transition-colors ${
                              message.feedback === 'negative' 
                                ? 'text-red-600 bg-red-50' 
                                : 'text-gray-400 hover:text-red-600 hover:bg-red-50'
                            }`}
                            title="Cette réponse n'est pas utile"
                            disabled={message.feedback !== null}
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M7.498 15.25H4.372c-1.026 0-1.945-.694-2.054-1.715a12.137 12.137 0 0 1-.068-1.285c0-2.848.992-5.464 2.649-7.521C5.287 4.247 5.886 4 6.504 4h4.016a4.5 4.5 0 0 1 1.423.23l3.114 1.04a4.5 4.5 0 0 0 1.423.23h1.294M7.498 15.25c.618 0 .991.724.725 1.282A7.471 7.471 0 0 0 7.5 19.75 2.25 2.25 0 0 0 9.75 22a.75.75 0 0 0 .75-.75v-.633c0-.573.11-1.14.322-1.672.304-.76.93-1.33 1.653-1.715a9.04 9.04 0 0 0 2.86-2.4c.498-.634 1.226-1.08 2.032-1.08h.384m-10.253 1.5H9.7m8.075-9.75c.01.05.027.1.05.148.593 1.2.925 2.55.925 3.977 0 1.487-.36 2.89-.999 4.125m.023-8.25c-.076-.365.183-.75.575-.75h.908c.889 0 1.713.518 1.972 1.368.339 1.11.521 2.287.521 3.507 0 1.553-.295 3.036-.831 4.398C20.613 14.547 19.833 15 19.05 15h-1.613m-6.844-13.5c.76.15 1.463.423 2.068.827.193.122.4.248.6.383.774.519 1.466 1.187 2.031 1.966a10.462 10.462 0 0 1 1.244 3.562c.06.369.09.742.09 1.115-.013 1.05-.313 2.047-.78 2.917-.512.95-1.234 1.793-2.137 2.453a1.507 1.507 0 0 1-1.556.008c-.784-.57-1.227-1.432-1.227-2.332v-.84c0-.769-.263-1.514-.74-2.101-.195-.24-.4-.458-.615-.652-.711-.642-1.518-1.113-2.384-1.399-.867-.286-1.77-.442-2.723-.442H2.255a.75.75 0 0 1-.75-.75 2.25 2.25 0 0 1 2.25-2.25Z" />
                            </svg>
                          </button>
                          
                          {/* ✅ AFFICHAGE STATUS FEEDBACK */}
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
                          
                          {message.conversation_id && (
                            <span className="text-xs text-gray-400 ml-2" title={`ID: ${message.conversation_id}`}>
                              🔗 {message.feedback ? `(${message.feedback})` : '(no feedback)'}
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

          {/* Bouton flottant "revenir en bas" */}
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

      {/* ✅ MODAL FEEDBACK */}
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