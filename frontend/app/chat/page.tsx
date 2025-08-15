'use client'

import React, { useState, useEffect, useRef, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import { Message } from './types'
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

  // Ã‰tats existants inchangÃ©s
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
  const hasLoadedConversationsRef = useRef(false)

  const messages: Message[] = currentConversation?.messages || []
  const hasMessages = messages.length > 0

  console.log('ðŸ" [Render] Messages:', messages.length, 'Clarification:', !!clarificationState, 'Concision:', config.level)

  // ðŸ"§ FONCTION UTILITAIRE : Extraire les initiales de l'utilisateur
  const getUserInitials = (user: any): string => {
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
  }

  // ðŸ"§ FONCTION RENFORCÃ‰E : PrÃ©processeur Markdown pour rÃ©parer le formatage cassÃ©
  const preprocessMarkdown = (content: string): string => {
    if (!content) return ""

    let processed = content

    // ðŸš¨ CORRECTION CRITIQUE : RÃ©parer les titres collÃ©s au texte suivant
    // Exemple: "## Diagnostic PrincipalLa mortalitÃ©" â†' "## Diagnostic Principal\n\nLa mortalitÃ©"
    processed = processed.replace(/(#{1,6})\s*([^#\n]+?)([A-Z][a-z])/g, '$1 $2\n\n$3')

    // ðŸš¨ CORRECTION : Ajouter saut de ligne aprÃ¨s tous les titres si manquant
    processed = processed.replace(/^(#{1,6}[^\n]+)(?!\n)/gm, '$1\n')

    // ðŸš¨ CORRECTION : SÃ©parer les mots collÃ©s par une virgule manquante
    // Exemple: "diarrhÃ©e hÃ©morragique, suggÃ¨re" au lieu de "diarrhÃ©e hÃ©morragiquesugÃ¨re"
    processed = processed.replace(/([a-z])([A-Z])/g, '$1, $2')

    // ðŸš¨ CORRECTION : RÃ©parer les phrases collÃ©es aprÃ¨s ponctuation
    processed = processed.replace(/([.!?:])([A-Z])/g, '$1 $2')

    // ðŸš¨ CORRECTION : Ajouter espaces avant les mots importants en gras
    processed = processed.replace(/([a-z])(\*\*[A-Z])/g, '$1 $2')

    // ðŸš¨ CORRECTION : SÃ©parer les sections importantes collÃ©es
    processed = processed.replace(/([.!?:])\s*(\*\*[^*]+\*\*)/g, '$1\n\n$2')

    // ðŸ"¨ CORRECTION : Structure en sections avec ### pour sous-parties
    processed = processed.replace(/([.!?:])\s*-\s*([A-Z][^:]+:)/g, '$1\n\n### $2')

    // ðŸ"¨ CORRECTION : AmÃ©liorer la structure des listes
    processed = processed.replace(/([.!?:])\s*-\s*([A-Z][^-]+)/g, '$1\n\n- $2')

    // ðŸ"¨ CORRECTION : Ajouter espacement avant les listes
    processed = processed.replace(/([^.\n])\n([â€¢\-\*]\s)/g, '$1\n\n$2')

    // ðŸ"¨ CORRECTION : Ajouter espacement aprÃ¨s les listes
    processed = processed.replace(/([â€¢\-\*]\s[^\n]+)\n([A-Z][^â€¢\-\*])/g, '$1\n\n$2')

    // ðŸ"¨ CORRECTION : GÃ©rer les sections spÃ©ciales (Causes, Recommandations, etc.)
    processed = processed.replace(/(Causes Possibles|Recommandations|PrÃ©vention|Court terme|Long terme|ImmÃ©diat)([^-:])/g, '\n\n### $1\n\n$2')

    // ðŸ"¨ NORMALISATION : Nettoyer les espaces multiples
    processed = processed.replace(/[ \t]+/g, ' ')

    // ðŸ"¨ NORMALISATION : Ã‰viter les triples sauts de ligne
    processed = processed.replace(/\n\n\n+/g, '\n\n')

    // ðŸ"¨ NETTOYAGE : Supprimer espaces en dÃ©but/fin
    processed = processed.trim()

    console.log('ðŸ"§ [preprocessMarkdown] RÃ©paration intensive:', {
      original_length: content.length,
      processed_length: processed.length,
      repairs_made: content !== processed,
      preview: processed.substring(0, 300)
    })

    return processed
  }

  // ðŸ"„ CORRECTION USEMEMO : Calculer le contenu préprocessé avant le rendu
  const processedMessages = useMemo(() => {
    return messages.map(message => ({
      ...message,
      processedContent: message.isUser ? message.content : preprocessMarkdown(message.content)
    }))
  }, [messages])

  // ðŸ"„ FONCTION NOUVELLE : Reprocesser tous les messages avec nouvelles versions
  const reprocessAllMessages = () => {
    if (!currentConversation?.messages) return

    const updatedMessages = currentConversation.messages.map(message => {
      // Ne traiter que les rÃ©ponses IA qui ont response_versions
      if (!message.isUser &&
          message.id !== 'welcome' &&
          message.response_versions &&
          !message.content.includes('Mode clarification') &&
          !message.content.includes('ðŸŽ¯ RÃ©pondez simplement')) {

        // ðŸ"„ SÃ‰LECTION DE VERSION : Utiliser selectVersionFromResponse
        const selectedContent = (message.response_versions?.standard || message.response_versions?.detailed || message.response_versions?.concise || Object.values(message.response_versions || {})[0] || '')

        console.log(`ðŸ" [reprocessAllMessages] Message ${message.id} - passage Ã  ${config.level}`, {
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
    console.log('âœ… [reprocessAllMessages] Tous les messages retraitÃ©s avec niveau:', config.level)
  }

  // ðŸ"„ FONCTION Ã‰TENDUE : Nettoyer le texte de rÃ©ponse (synchronisÃ©e avec backend _final_sanitize)
  const cleanResponseText = (text: string): string => {
    if (!text) return ""

    // ðŸ"¨ PROTECTION CRITIQUE : Ne pas nettoyer les rÃ©ponses courtes PerfStore
    if (text.length < 100) {
      console.log('ðŸ›¡ï¸ [cleanResponseText] RÃ©ponse courte protÃ©gÃ©e:', text)
      return text.trim()
    }

    let cleaned = text

    // ========================
    // âœ… CODE ORIGINAL CONSERVÃ‰ (fonctionne bien)
    // ========================

    // Retirer toutes les rÃ©fÃ©rences aux sources (patterns multiples)
    cleaned = cleaned.replace(/\*\*Source:\s*[^*]+\*\*/g, '')
    cleaned = cleaned.replace(/\*\*ource:\s*[^*]+\*\*/g, '') // Cas tronquÃ©
    cleaned = cleaned.replace(/\*\*Source[^*]*\*\*/g, '') // Cas gÃ©nÃ©riques
    cleaned = cleaned.replace(/Source:\s*[^\n]+/g, '') // Sans astÃ©risques

    // Retirer les longs passages de texte technique des PDFs (patterns Ã©tendus)
    cleaned = cleaned.replace(/protection, regardless of the species involved[^.]+\./g, '')
    cleaned = cleaned.replace(/bird ages, from the adverse effects[^.]+\./g, '')
    cleaned = cleaned.replace(/oocyst production reaches a maximum[^.]+\./g, '')
    cleaned = cleaned.replace(/oocyst production begins to diminish[^.]+\./g, '')
    cleaned = cleaned.replace(/oocyst production ceases[^.]+\./g, '')
    cleaned = cleaned.replace(/immunosuppressive response after[^.]+\./g, '')
    cleaned = cleaned.replace(/Ecchymotic hemorrhages in muscles[^.]+\./g, '')
    cleaned = cleaned.replace(/The virus is highly contagious[^.]+\./g, '')
    cleaned = cleaned.replace(/Mice and darkling beetles[^.]+\./g, '')
    cleaned = cleaned.replace(/IBD does not transmit[^.]+\./g, '')

    // Retirer les fragments de phrases coupÃ©es qui commencent sans majuscule
    cleaned = cleaned.replace(/^[a-z][^.]+\.\.\./gm, '')

    // Retirer les fragments techniques gÃ©nÃ©riques
    cleaned = cleaned.replace(/ould be aware of local legislation[^.]+\./g, '')
    cleaned = cleaned.replace(/Apply your knowledge and judgment[^.]+\./g, '')

    // Nettoyer les tableaux mal formatÃ©s
    cleaned = cleaned.replace(/Age \(days\) Weight \(lb\)[^|]+\|[^|]+\|/g, '')

    // Retirer les rÃ©pÃ©titions de mots coupÃ©s
    cleaned = cleaned.replace(/\b\w{1,3}\.\.\./g, '')

    // Retirer les phrases qui se terminent abruptement par ---
    cleaned = cleaned.replace(/[^.!?]+---\s*/g, '')

    // Nettoyer les numÃ©rotations orphelines (ex: "2. Gross and Microscopic Lesions:")
    cleaned = cleaned.replace(/^\d+\.\s+[A-Z][^:]+:\s*$/gm, '')
    cleaned = cleaned.replace(/^\w\.\s+[A-Z][^:]+:\s*$/gm, '')

    // ========================
    // ðŸ"„ NOUVELLES REGEX (synchronisÃ©es avec backend _final_sanitize)
    // ========================

    // En-tÃªtes "INTRODUCTIONâ€¦", "Cobb MXâ€¦" et variants
    cleaned = cleaned.replace(/^INTRODUCTION[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Introduction[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Cobb MX[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^COBB MX[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Cobb [0-9]+[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^COBB [0-9]+[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Ross [0-9]+[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^ROSS [0-9]+[^\n]*$/gm, '')

    // En-tÃªtes techniques gÃ©nÃ©riques en majuscules
    cleaned = cleaned.replace(/^[A-Z\s]{10,}:?\s*$/gm, '') // Lignes tout en majuscules
    cleaned = cleaned.replace(/^[A-Z][A-Z\s]+GUIDE[^\n]*$/gm, '') // Guides techniques
    cleaned = cleaned.replace(/^[A-Z][A-Z\s]+MANUAL[^\n]*$/gm, '') // Manuels
    cleaned = cleaned.replace(/^[A-Z][A-Z\s]+MANAGEMENT[^\n]*$/gm, '') // Management

    // Tableaux mal formattÃ©s - patterns Ã©tendus
    cleaned = cleaned.replace(/\|\s*Age\s*\|\s*Weight[^|]*\|[^\n]*\n/g, '') // En-tÃªtes de tableaux
    cleaned = cleaned.replace(/\|\s*Days\s*\|\s*Grams[^|]*\|[^\n]*\n/g, '')
    cleaned = cleaned.replace(/\|\s*Week\s*\|\s*Target[^|]*\|[^\n]*\n/g, '')
    cleaned = cleaned.replace(/\|[\s\-]+\|[\s\-]+\|/g, '') // SÃ©parateurs de tableaux

    // Fragments de PDF mal parsÃ©s
    cleaned = cleaned.replace(/[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}/g, '') // SÃ©quences majuscules
    cleaned = cleaned.replace(/\b[A-Z]\.[A-Z]\.[A-Z]\./g, '') // Initiales orphelines
    cleaned = cleaned.replace(/Page\s+\d+\s+of\s+\d+/gi, '') // NumÃ©ros de pages
    cleaned = cleaned.replace(/Copyright\s+[Â©\(c\)]\s*[^\n]*/gi, '') // Copyright

    // RÃ©fÃ©rences bibliographiques orphelines
    cleaned = cleaned.replace(/^\([^)]+\)\s*$/gm, '') // RÃ©fÃ©rences entre parenthÃ¨ses seules
    cleaned = cleaned.replace(/^et\s+al\.[^\n]*$/gm, '') // "et al." orphelin
    cleaned = cleaned.replace(/^[A-Z][a-z]+,\s+[A-Z]\.[^\n]*$/gm, '') // Citations d'auteurs

    // Codes et identifiants techniques
    cleaned = cleaned.replace(/\b[A-Z]{2,}\-[0-9]+\b/g, '') // Codes type ABC-123
    cleaned = cleaned.replace(/\b[0-9]{4,}\-[0-9]{2,}\b/g, '') // Codes numÃ©riques
    cleaned = cleaned.replace(/\bDOI:\s*[^\s]+/gi, '') // DOI
    cleaned = cleaned.replace(/\bISSN:\s*[^\s]+/gi, '') // ISSN

    // ========================
    // âœ… NETTOYAGE FINAL ORIGINAL CONSERVÃ‰
    // ========================

    // Normaliser les espaces multiples
    cleaned = cleaned.replace(/\s+/g, ' ')
    cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n')
    cleaned = cleaned.replace(/\n\s*\n/g, '\n\n')

    // Retirer les lignes vides en dÃ©but et fin
    cleaned = cleaned.replace(/^\s*\n+/, '')
    cleaned = cleaned.replace(/\n+\s*$/, '')

    return cleaned.trim()
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
      console.log('ðŸ"ž [ChatInterface] Redirection - utilisateur non authentifiÃ©')

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
          console.log('[ChatInterface] Chargement historique pour:', user.email || user.id)
          loadConversations(user.email || user.id)

            .then(() => {
              if (isMountedRef.current) {
                console.log('Historique conversations chargÃ©')
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

  const getCurrentDate = () => {
    return new Date().toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    })
  }

  // ðŸŒ¾ FONCTION CORRIGÃ‰E : extractAnswerAndSources avec support validation_rejected
  const extractAnswerAndSources = (result: any): [string, any[]] => {
    let answerText = ""
    let sources: any[] = [] // Toujours vide maintenant

    console.log('ðŸ"¯ [extractAnswerAndSources] DÃ©but extraction:', {
      type: result?.type,
      has_answer: !!result?.answer,
      has_general_answer: !!result?.general_answer
    })

    // ðŸŒ¾ NOUVEAU : GÃ©rer le type "validation_rejected"
    if (result?.type === 'validation_rejected') {
      console.log('ðŸš« [extractAnswerAndSources] Question rejetÃ©e par validation agricole')

      // CrÃ©er un message informatif avec suggestions
      let rejectionMessage = result.message || "Cette question ne concerne pas le domaine agricole."

      // Ajouter les sujets suggÃ©rÃ©s si disponibles
      if (result.validation?.suggested_topics && result.validation.suggested_topics.length > 0) {
        rejectionMessage += "\n\n**Voici quelques sujets que je peux vous aider :**\n"
        result.validation.suggested_topics.forEach((topic: string, index: number) => {
          rejectionMessage += `â€¢ ${topic}\n`
        })
      }

      return [rejectionMessage, []]
    }

    // ðŸ"¨ CORRECTION CRITIQUE : Traiter type "answer" EN PREMIER
    if (result?.type === 'answer' && result?.answer) {
      console.log('ðŸ"¯ [extractAnswerAndSources] Type answer dÃ©tectÃ©')
      answerText = result.answer.text || ""
      console.log('ðŸ"¯ [extractAnswerAndSources] Answer text extraite:', answerText.substring(0, 100))
      return [answerText, []]
    }

    // ðŸ"„ Support type "partial_answer" du DialogueManager hybride
    if (result?.type === 'partial_answer' && result?.general_answer) {
      console.log('ðŸ"¯ [extractAnswerAndSources] Type partial_answer dÃ©tectÃ©')

      answerText = result.general_answer.text || ""
      console.log('ðŸ"¯ [extractAnswerAndSources] General answer text extraite:', answerText.substring(0, 100))

      return [answerText, []] // Toujours retourner sources vides
    }

    // âœ… ANCIEN CODE CONSERVÃ‰ pour compatibilitÃ©
    const responseContent = result?.response || ""

    if (typeof responseContent === 'object' && responseContent !== null) {
      answerText = String(responseContent.answer || "").trim()
      if (!answerText) {
        answerText = "DÃ©solÃ©, je n'ai pas pu formater la rÃ©ponse."
      }
    } else {
      answerText = String(responseContent).trim() || "DÃ©solÃ©, je n'ai pas pu formater la rÃ©ponse."

      // âœ… CORRECTION: Nettoyer le JSON visible si prÃ©sent
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

    console.log('ðŸ"¯ [extractAnswerAndSources] RÃ©sultat final:', answerText.substring(0, 100))
    return [answerText, []] // Toujours retourner sources vides
  }

  // ðŸ"„ FONCTION MODIFIÃ‰E : handleSendMessage avec nettoyage du texte
  const handleSendMessage = async (text: string = inputMessage) => {
    if (!text.trim() || !isMountedRef.current) return

    console.log('ðŸ"¤ [ChatInterface] Envoi message:', {
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

      // ðŸ"„ DÃ‰TECTION AUTOMATIQUE : Niveau optimal pour la question
      const optimalLevel = undefined;
      console.log('ðŸ"¯ [handleSendMessage] Niveau optimal dÃ©tectÃ©:', optimalLevel)

      if (clarificationState) {
        console.log('ðŸ"ª [handleSendMessage] Mode clarification')

        response = await generateAIResponse(
          clarificationState.originalQuestion + " " + text.trim(),
          user,
          currentLanguage,
          conversationIdToSend,
          optimalLevel, // ðŸ"„ NOUVEAU : Passer niveau optimal
          true,
          clarificationState.originalQuestion,
          { answer: text.trim() }
        )

        setClarificationState(null)
        console.log('âœ… [handleSendMessage] Clarification traitÃ©e')

      } else {
        // ðŸ"„ APPEL MODIFIÃ‰ : Passer niveau optimal au backend
        response = await generateAIResponse(
          text.trim(),
          user,
          currentLanguage,
          conversationIdToSend,
          optimalLevel // ðŸ"„ NOUVEAU : Niveau optimal dÃ©tectÃ© automatiquement
        )
      }

      if (!isMountedRef.current) return

      console.log('ðŸ"¥ [handleSendMessage] RÃ©ponse reÃ§ue:', {
        conversation_id: response.conversation_id,
        response_length: response.response?.length || 0,
        versions_received: Object.keys(response.response_versions || {}),
        clarification_requested: response.clarification_result?.clarification_requested || false,
        type: response.type // ðŸŒ¾ NOUVEAU : Log du type de rÃ©ponse
      })

      const needsClarification = response.clarification_result?.clarification_requested === true

      if (needsClarification) {
        console.log('â" [handleSendMessage] Clarification demandÃ©e')

        const clarificationMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: (response.full_text || response.response) + "\n\nðŸŽ¯ RÃ©pondez simplement dans le chat avec les informations demandÃ©es.",
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

        console.log('ðŸ"ž [handleSendMessage] Ã‰tat clarification activÃ©')

      } else {
        // ðŸ"¨ CORRECTION CRITIQUE : Extraction avec fonction corrigÃ©e
        const [answerText, sources] = extractAnswerAndSources(response)

        console.log('ðŸ"¯ [handleSendMessage] Texte extrait:', {
          length: answerText.length,
          preview: answerText.substring(0, 100),
          empty: !answerText || answerText.trim() === ''
        })

        const cleanedText = cleanResponseText(answerText) // ðŸ"„ NOUVEAU : Appliquer le nettoyage

        console.log('ðŸ"¯ [handleSendMessage] Texte nettoyÃ©:', {
          length: cleanedText.length,
          preview: cleanedText.substring(0, 100),
          empty: !cleanedText || cleanedText.trim() === ''
        })

        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: cleanedText || "Erreur: contenu vide", // ðŸ"¨ PROTECTION: Fallback si vide
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id,
          // ðŸ"„ NOUVEAU : Stocker toutes les versions reÃ§ues du backend
          response_versions: response.response_versions,
          // Garder pour compatibilitÃ© (peut Ãªtre supprimÃ© plus tard)
          originalResponse: response.response
        }

        console.log('ðŸ"¯ [handleSendMessage] Message AI crÃ©Ã©:', {
          id: aiMessage.id,
          content_length: aiMessage.content.length,
          content_preview: aiMessage.content.substring(0, 100),
          has_versions: !!aiMessage.response_versions
        })

        addMessage(aiMessage)
        console.log('âœ… [handleSendMessage] Message ajoutÃ© avec versions:', Object.keys(response.response_versions || {}))
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
      console.warn('Conversation ID non trouvÃ© pour le feedback', messageId)
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
            console.warn('Commentaire non envoyÃ© (endpoint manquant):', commentError)
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
      console.error('Erreur gÃ©nÃ©rale feedback:', error)
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

  return (
    <>
      <ZohoSalesIQ user={user} language={currentLanguage} />

      {/* ðŸ"± MODIFICATION 1: Utiliser 100dvh pour Ã©viter la zone "perdue" sous la barre d'adresse */}
      <div className="min-h-dvh h-screen bg-gray-50 flex flex-col">
        <header className="bg-white border-b border-gray-100 px-2 sm:px-4 py-3">
          <div className="flex items-center justify-between">
            {/* Boutons gauche */}
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

            {/* Titre centrÃ© avec logo (min-w-0 pour ne pas pousser la page en largeur) */}
            <div className="flex-1 min-w-0 flex justify-center items-center space-x-3">
              <div className="w-8 h-8 grid place-items-center">
                <InteliaLogo className="h-7 w-auto" />
              </div>
              <div className="text-center">
                <h1 className="text-lg font-medium text-gray-900 truncate">Intelia Expert</h1>
              </div>
            </div>

            {/* Avatar utilisateur Ã  droite */}
            <div className="flex items-center">
              <UserMenuButton />
            </div>
          </div>

          {showConcisionSettings && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium text-gray-700">ParamÃ¨tres de concision</h3>
                <button
                  onClick={() => setShowConcisionSettings(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  âœ•
                </button>
              </div>

              {hasMessages && (
                <button
                  onClick={reprocessAllMessages}
                  className="mt-3 px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 text-sm transition-colors"
                >
                  ðŸ"ž Appliquer Ã  toutes les rÃ©ponses
                </button>
              )}
            </div>
          )}
        </header>

        <div className="flex-1 overflow-hidden flex flex-col">
          {/* ðŸ"± MODIFICATION 2: Ajouter pb-28 pour Ã©viter que les messages soient cachÃ©s par la barre sticky */}
          <div
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto px-2 sm:px-4 py-6 pb-28 overscroll-contain"
            style={{ scrollPaddingBottom: '7rem' }}
          >
            <div className="max-w-full sm:max-w-4xl mx-auto space-y-6 px-2 sm:px-4">
              {hasMessages && (
                <div className="text-center">
                  <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                    {getCurrentDate()}
                  </span>
                </div>
              )}

              {processedMessages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <div className="text-sm">Aucun message Ã  afficher</div>
                </div>
              ) : (
                processedMessages.map((message, index) => (
                  <div key={`${message.id}-${index}`}>
                    {/* min-w-0 pour Ã©viter que le contenu force un viewport plus large sur iOS */}
                    <div className={`flex items-start space-x-3 min-w-0 ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                      {/* ðŸ"§ CORRECTION LOGO: Container avec largeur fixe pour Ã©viter l'Ã©crasement */}
                      {!message.isUser && (
                        <div className="flex-shrink-0 w-8 h-8 grid place-items-center">
                          <InteliaLogo className="h-7 w-auto" />
                        </div>
                      )}

                      {/* iPhone: limiter la largeur des bulles + autoriser les cÃ©sures */}
                      <div className={`px-3 sm:px-4 py-3 rounded-2xl max-w-[85%] sm:max-w-none break-words ${message.isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-white border border-gray-200 text-gray-900'}`}>
                        {message.isUser ? (
                          <p className="whitespace-pre-wrap leading-relaxed text-sm">
                            {message.content}
                          </p>
                        ) : (
                          <ReactMarkdown
                            className="prose prose-sm max-w-none break-words prose-p:my-3 prose-li:my-1 prose-ul:my-4 prose-strong:text-gray-900 prose-headings:font-bold prose-headings:text-gray-900"
                            components={{
                              // ðŸ"¨ TITRES H2 : Style amÃ©liorÃ© avec plus d'espacement
                              h2: ({node, ...props}) => (
                                <h2 className="text-xl font-bold text-blue-900 mt-8 mb-6 border-b-2 border-blue-200 pb-3 bg-blue-50 px-4 py-2 rounded-t-lg" {...props} />
                              ),

                              // ðŸ"¨ TITRES H3 : Style pour les sous-sections
                              h3: ({node, ...props}) => (
                                <h3 className="text-lg font-semibold text-gray-800 mt-6 mb-4 border-l-4 border-blue-400 pl-4 bg-gray-50 py-2" {...props} />
                              ),

                              // ðŸ"¨ PARAGRAPHES : Espacement gÃ©nÃ©reux
                              p: ({node, ...props}) => (
                                <p className="leading-relaxed text-gray-800 my-4 text-justify" {...props} />
                              ),

                              // ðŸ"¨ LISTES : Style amÃ©liorÃ© avec plus d'espace
                              ul: ({node, ...props}) => (
                                <ul className="list-disc list-outside space-y-3 text-gray-800 my-6 ml-6 pl-2" {...props} />
                              ),

                              // ðŸ"¨ Ã‰LÃ‰MENTS DE LISTE : Meilleur spacing
                              li: ({node, ...props}) => (
                                <li className="leading-relaxed pl-2 my-2" {...props} />
                              ),

                              // ðŸ"¨ TEXTE EN GRAS : Plus visible
                              strong: ({node, ...props}) => (
                                <strong className="font-bold text-blue-800 bg-blue-50 px-1 rounded" {...props} />
                              ),

                              // ðŸ"„ TABLEAUX : Style amÃ©liorÃ©
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
                                  ðŸ'¬
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* ðŸ"§ CORRECTION 2: Avatar avec initiales pour les messages utilisateur */}
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
              )}

              {isLoadingChat && (
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 grid place-items-center flex-shrink-0">
                    <InteliaLogo className="h-7 w-auto" />
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

          {/* ðŸ"± MODIFICATION 3: Barre sticky avec safe-area conditionnel + hauteurs uniformisÃ©es */}
          <div className="px-2 sm:px-4 py-2 bg-white border-t border-gray-100 sticky bottom-0 z-20 pb-[env(safe-area-inset-bottom)] sm:pb-2">
            <div className="max-w-full sm:max-w-4xl mx-auto px-2 sm:px-4">
              {clarificationState && (
                <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-blue-700 text-sm font-medium">
                      ðŸŽ¯ Mode clarification : rÃ©pondez Ã  la question ci-dessus
                    </span>
                    <button
                      onClick={() => {
                        setClarificationState(null)
                        console.log('ðŸ"ž [ChatInterface] Clarification annulÃ©e')
                      }}
                      className="text-blue-600 hover:text-blue-800 text-sm underline"
                    >
                      Annuler
                    </button>
                  </div>
                </div>
              )}

              {/* ðŸ"± MODIFICATION 4: Hauteurs uniformisÃ©es (h-12 = 48px) et centrage parfait */}
              <div className="flex items-center space-x-3 min-h-[48px]">
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
                    placeholder={clarificationState ? "RÃ©pondez Ã  la question ci-dessus..." : t('chat.placeholder')}
                    className="w-full h-12 px-4 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm flex items-center"
                    disabled={isLoadingChat}
                    aria-label={t('chat.placeholder')}
                  />
                </div>

                <button
                  onClick={() => handleSendMessage()}
                  disabled={isLoadingChat || !inputMessage.trim()}
                  className="flex-shrink-0 h-12 w-12 flex items-center justify-center text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors rounded-full hover:bg-blue-50"
                  title={isLoadingChat ? 'Envoi en cours...' : 'Envoyer le message'}
                  aria-label={isLoadingChat ? 'Envoi en cours...' : 'Envoyer le message'}
                >
                  <PaperAirplaneIcon />
                </button>
              </div>

              {/* âœ… AJOUTEZ CES LIGNES ICI - EXACTEMENT APRÃˆS LA FERMETURE DU DIV PRÃ‰CÃ‰DENT */}
              <div className="text-center mt-2">
                <p className="text-xs text-gray-500">
                  Intelia Expert peut faire des erreurs. Faites vérifiez les réponses par un professionnel au besoin.
                </p>
              </div>
              {/* âœ… FIN DE L'AJOUT */}
			  			  
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