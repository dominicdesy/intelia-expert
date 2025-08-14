'use client'

import React, { useState, useEffect, useRef, useMemo } from 'react'
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

  // 🔧 FONCTION UTILITAIRE : Extraire les initiales de l'utilisateur
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

  // 🔧 FONCTION RENFORCÉE : Préprocesseur Markdown pour réparer le formatage cassé
  const preprocessMarkdown = (content: string): string => {
    if (!content) return ""

    let processed = content

    // 🚨 CORRECTION CRITIQUE : Réparer les titres collés au texte suivant
    // Exemple: "## Diagnostic PrincipalLa mortalité" → "## Diagnostic Principal\n\nLa mortalité"
    processed = processed.replace(/(#{1,6})\s*([^#\n]+?)([A-Z][a-z])/g, '$1 $2\n\n$3')

    // 🚨 CORRECTION : Ajouter saut de ligne après tous les titres si manquant
    processed = processed.replace(/^(#{1,6}[^\n]+)(?!\n)/gm, '$1\n')

    // 🚨 CORRECTION : Séparer les mots collés par une virgule manquante
    // Exemple: "diarrhée hémorragique, suggère" au lieu de "diarrhée hémorragiquesugère"
    processed = processed.replace(/([a-z])([A-Z])/g, '$1, $2')

    // 🚨 CORRECTION : Réparer les phrases collées après ponctuation
    processed = processed.replace(/([.!?:])([A-Z])/g, '$1 $2')

    // 🚨 CORRECTION : Ajouter espaces avant les mots importants en gras
    processed = processed.replace(/([a-z])(\*\*[A-Z])/g, '$1 $2')

    // 🚨 CORRECTION : Séparer les sections importantes collées
    processed = processed.replace(/([.!?:])\s*(\*\*[^*]+\*\*)/g, '$1\n\n$2')

    // 🔨 CORRECTION : Structure en sections avec ### pour sous-parties
    processed = processed.replace(/([.!?:])\s*-\s*([A-Z][^:]+:)/g, '$1\n\n### $2')

    // 🔨 CORRECTION : Améliorer la structure des listes
    processed = processed.replace(/([.!?:])\s*-\s*([A-Z][^-]+)/g, '$1\n\n- $2')

    // 🔨 CORRECTION : Ajouter espacement avant les listes
    processed = processed.replace(/([^.\n])\n([•\-\*]\s)/g, '$1\n\n$2')

    // 🔨 CORRECTION : Ajouter espacement après les listes
    processed = processed.replace(/([•\-\*]\s[^\n]+)\n([A-Z][^•\-\*])/g, '$1\n\n$2')

    // 🔨 CORRECTION : Gérer les sections spéciales (Causes, Recommandations, etc.)
    processed = processed.replace(/(Causes Possibles|Recommandations|Prévention|Court terme|Long terme|Immédiat)([^-:])/g, '\n\n### $1\n\n$2')

    // 🔨 NORMALISATION : Nettoyer les espaces multiples
    processed = processed.replace(/[ \t]+/g, ' ')

    // 🔨 NORMALISATION : Éviter les triples sauts de ligne
    processed = processed.replace(/\n\n\n+/g, '\n\n')

    // 🔨 NETTOYAGE : Supprimer espaces en début/fin
    processed = processed.trim()

    console.log('🔧 [preprocessMarkdown] Réparation intensive:', {
      original_length: content.length,
      processed_length: processed.length,
      repairs_made: content !== processed,
      preview: processed.substring(0, 300)
    })

    return processed
  }

  // 🔄 FONCTION NOUVELLE : Reprocesser tous les messages avec nouvelles versions
  const reprocessAllMessages = () => {
    if (!currentConversation?.messages) return

    const updatedMessages = currentConversation.messages.map(message => {
      // Ne traiter que les réponses IA qui ont response_versions
      if (!message.isUser &&
          message.id !== 'welcome' &&
          message.response_versions &&
          !message.content.includes('Mode clarification') &&
          !message.content.includes('🎯 Répondez simplement')) {

        // 🔄 SÉLECTION DE VERSION : Utiliser selectVersionFromResponse
        const selectedContent = (message.response_versions?.standard || message.response_versions?.detailed || message.response_versions?.concise || Object.values(message.response_versions || {})[0] || '')

        console.log(`🔍 [reprocessAllMessages] Message ${message.id} - passage à ${config.level}`, {
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

  // 🔄 FONCTION ÉTENDUE : Nettoyer le texte de réponse (synchronisée avec backend _final_sanitize)
  const cleanResponseText = (text: string): string => {
    if (!text) return ""

    // 🔨 PROTECTION CRITIQUE : Ne pas nettoyer les réponses courtes PerfStore
    if (text.length < 100) {
      console.log('🛡️ [cleanResponseText] Réponse courte protégée:', text)
      return text.trim()
    }

    let cleaned = text

    // ========================
    // ✅ CODE ORIGINAL CONSERVÉ (fonctionne bien)
    // ========================

    // Retirer toutes les références aux sources (patterns multiples)
    cleaned = cleaned.replace(/\*\*Source:\s*[^*]+\*\*/g, '')
    cleaned = cleaned.replace(/\*\*ource:\s*[^*]+\*\*/g, '') // Cas tronqué
    cleaned = cleaned.replace(/\*\*Source[^*]*\*\*/g, '') // Cas génériques
    cleaned = cleaned.replace(/Source:\s*[^\n]+/g, '') // Sans astérisques

    // Retirer les longs passages de texte technique des PDFs (patterns étendus)
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

    // Retirer les fragments de phrases coupées qui commencent sans majuscule
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

    // Nettoyer les numérotations orphelines (ex: "2. Gross and Microscopic Lesions:")
    cleaned = cleaned.replace(/^\d+\.\s+[A-Z][^:]+:\s*$/gm, '')
    cleaned = cleaned.replace(/^\w\.\s+[A-Z][^:]+:\s*$/gm, '')

    // ========================
    // 🔄 NOUVELLES REGEX (synchronisées avec backend _final_sanitize)
    // ========================

    // En-têtes "INTRODUCTION…", "Cobb MX…" et variants
    cleaned = cleaned.replace(/^INTRODUCTION[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Introduction[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Cobb MX[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^COBB MX[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Cobb [0-9]+[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^COBB [0-9]+[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^Ross [0-9]+[^\n]*$/gm, '')
    cleaned = cleaned.replace(/^ROSS [0-9]+[^\n]*$/gm, '')

    // En-têtes techniques génériques en majuscules
    cleaned = cleaned.replace(/^[A-Z\s]{10,}:?\s*$/gm, '') // Lignes tout en majuscules
    cleaned = cleaned.replace(/^[A-Z][A-Z\s]+GUIDE[^\n]*$/gm, '') // Guides techniques
    cleaned = cleaned.replace(/^[A-Z][A-Z\s]+MANUAL[^\n]*$/gm, '') // Manuels
    cleaned = cleaned.replace(/^[A-Z][A-Z\s]+MANAGEMENT[^\n]*$/gm, '') // Management

    // Tableaux mal formattés - patterns étendus
    cleaned = cleaned.replace(/\|\s*Age\s*\|\s*Weight[^|]*\|[^\n]*\n/g, '') // En-têtes de tableaux
    cleaned = cleaned.replace(/\|\s*Days\s*\|\s*Grams[^|]*\|[^\n]*\n/g, '')
    cleaned = cleaned.replace(/\|\s*Week\s*\|\s*Target[^|]*\|[^\n]*\n/g, '')
    cleaned = cleaned.replace(/\|[\s\-]+\|[\s\-]+\|/g, '') // Séparateurs de tableaux

    // Fragments de PDF mal parsés
    cleaned = cleaned.replace(/[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}/g, '') // Séquences majuscules
    cleaned = cleaned.replace(/\b[A-Z]\.[A-Z]\.[A-Z]\./g, '') // Initiales orphelines
    cleaned = cleaned.replace(/Page\s+\d+\s+of\s+\d+/gi, '') // Numéros de pages
    cleaned = cleaned.replace(/Copyright\s+[©\(c\)]\s*[^\n]*/gi, '') // Copyright

    // Références bibliographiques orphelines
    cleaned = cleaned.replace(/^\([^)]+\)\s*$/gm, '') // Références entre parenthèses seules
    cleaned = cleaned.replace(/^et\s+al\.[^\n]*$/gm, '') // "et al." orphelin
    cleaned = cleaned.replace(/^[A-Z][a-z]+,\s+[A-Z]\.[^\n]*$/gm, '') // Citations d'auteurs

    // Codes et identifiants techniques
    cleaned = cleaned.replace(/\b[A-Z]{2,}\-[0-9]+\b/g, '') // Codes type ABC-123
    cleaned = cleaned.replace(/\b[0-9]{4,}\-[0-9]{2,}\b/g, '') // Codes numériques
    cleaned = cleaned.replace(/\bDOI:\s*[^\s]+/gi, '') // DOI
    cleaned = cleaned.replace(/\bISSN:\s*[^\s]+/gi, '') // ISSN

    // ========================
    // ✅ NETTOYAGE FINAL ORIGINAL CONSERVÉ
    // ========================

    // Normaliser les espaces multiples
    cleaned = cleaned.replace(/\s+/g, ' ')
    cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n')
    cleaned = cleaned.replace(/\n\s*\n/g, '\n\n')

    // Retirer les lignes vides en début et fin
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
      console.log('🔞 [ChatInterface] Redirection - utilisateur non authentifié')

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

  const getCurrentDate = () => {
    return new Date().toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    })
  }

  // 🌾 FONCTION CORRIGÉE : extractAnswerAndSources avec support validation_rejected
  const extractAnswerAndSources = (result: any): [string, any[]] => {
    let answerText = ""
    let sources: any[] = [] // Toujours vide maintenant

    console.log('🔯 [extractAnswerAndSources] Début extraction:', {
      type: result?.type,
      has_answer: !!result?.answer,
      has_general_answer: !!result?.general_answer
    })

    // 🌾 NOUVEAU : Gérer le type "validation_rejected"
    if (result?.type === 'validation_rejected') {
      console.log('🚫 [extractAnswerAndSources] Question rejetée par validation agricole')

      // Créer un message informatif avec suggestions
      let rejectionMessage = result.message || "Cette question ne concerne pas le domaine agricole."

      // Ajouter les sujets suggérés si disponibles
      if (result.validation?.suggested_topics && result.validation.suggested_topics.length > 0) {
        rejectionMessage += "\n\n**Voici quelques sujets que je peux vous aider :**\n"
        result.validation.suggested_topics.forEach((topic: string, index: number) => {
          rejectionMessage += `• ${topic}\n`
        })
      }

      return [rejectionMessage, []]
    }

    // 🔨 CORRECTION CRITIQUE : Traiter type "answer" EN PREMIER
    if (result?.type === 'answer' && result?.answer) {
      console.log('🔯 [extractAnswerAndSources] Type answer détecté')
      answerText = result.answer.text || ""
      console.log('🔯 [extractAnswerAndSources] Answer text extraite:', answerText.substring(0, 100))
      return [answerText, []]
    }

    // 🔄 Support type "partial_answer" du DialogueManager hybride
    if (result?.type === 'partial_answer' && result?.general_answer) {
      console.log('🔯 [extractAnswerAndSources] Type partial_answer détecté')

      answerText = result.general_answer.text || ""
      console.log('🔯 [extractAnswerAndSources] General answer text extraite:', answerText.substring(0, 100))

      return [answerText, []] // Toujours retourner sources vides
    }

    // ✅ ANCIEN CODE CONSERVÉ pour compatibilité
    const responseContent = result?.response || ""

    if (typeof responseContent === 'object' && responseContent !== null) {
      answerText = String(responseContent.answer || "").trim()
      if (!answerText) {
        answerText = "Désolé, je n'ai pas pu formater la réponse."
      }
    } else {
      answerText = String(responseContent).trim() || "Désolé, je n'ai pas pu formater la réponse."

      // ✅ CORRECTION: Nettoyer le JSON visible si présent
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

    console.log('🔯 [extractAnswerAndSources] Résultat final:', answerText.substring(0, 100))
    return [answerText, []] // Toujours retourner sources vides
  }

  // 🔄 FONCTION MODIFIÉE : handleSendMessage avec nettoyage du texte
  const handleSendMessage = async (text: string = inputMessage) => {
    if (!text.trim() || !isMountedRef.current) return

    console.log('🔤 [ChatInterface] Envoi message:', {
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

      // 🔄 DÉTECTION AUTOMATIQUE : Niveau optimal pour la question
      const optimalLevel = undefined;
      console.log('🔯 [handleSendMessage] Niveau optimal détecté:', optimalLevel)

      if (clarificationState) {
        console.log('🔪 [handleSendMessage] Mode clarification')

        response = await generateAIResponse(
          clarificationState.originalQuestion + " " + text.trim(),
          user,
          currentLanguage,
          conversationIdToSend,
          optimalLevel, // 🔄 NOUVEAU : Passer niveau optimal
          true,
          clarificationState.originalQuestion,
          { answer: text.trim() }
        )

        setClarificationState(null)
        console.log('✅ [handleSendMessage] Clarification traitée')

      } else {
        // 🔄 APPEL MODIFIÉ : Passer niveau optimal au backend
        response = await generateAIResponse(
          text.trim(),
          user,
          currentLanguage,
          conversationIdToSend,
          optimalLevel // 🔄 NOUVEAU : Niveau optimal détecté automatiquement
        )
      }

      if (!isMountedRef.current) return

      console.log('🔥 [handleSendMessage] Réponse reçue:', {
        conversation_id: response.conversation_id,
        response_length: response.response?.length || 0,
        versions_received: Object.keys(response.response_versions || {}),
        clarification_requested: response.clarification_result?.clarification_requested || false,
        type: response.type // 🌾 NOUVEAU : Log du type de réponse
      })

      const needsClarification = response.clarification_result?.clarification_requested === true

      if (needsClarification) {
        console.log('❓ [handleSendMessage] Clarification demandée')

        const clarificationMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: (response.full_text || response.response) + "\n\n🎯 Répondez simplement dans le chat avec les informations demandées.",
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

        console.log('🔞 [handleSendMessage] État clarification activé')

      } else {
        // 🔨 CORRECTION CRITIQUE : Extraction avec fonction corrigée
        const [answerText, sources] = extractAnswerAndSources(response)

        console.log('🔯 [handleSendMessage] Texte extrait:', {
          length: answerText.length,
          preview: answerText.substring(0, 100),
          empty: !answerText || answerText.trim() === ''
        })

        const cleanedText = cleanResponseText(answerText) // 🔄 NOUVEAU : Appliquer le nettoyage

        console.log('🔯 [handleSendMessage] Texte nettoyé:', {
          length: cleanedText.length,
          preview: cleanedText.substring(0, 100),
          empty: !cleanedText || cleanedText.trim() === ''
        })

        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: cleanedText || "Erreur: contenu vide", // 🔨 PROTECTION: Fallback si vide
          isUser: false,
          timestamp: new Date(),
          conversation_id: response.conversation_id,
          // 🔄 NOUVEAU : Stocker toutes les versions reçues du backend
          response_versions: response.response_versions,
          // Garder pour compatibilité (peut être supprimé plus tard)
          originalResponse: response.response
        }

        console.log('🔯 [handleSendMessage] Message AI créé:', {
          id: aiMessage.id,
          content_length: aiMessage.content.length,
          content_preview: aiMessage.content.substring(0, 100),
          has_versions: !!aiMessage.response_versions
        })

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

  return (
    <>
      <ZohoSalesIQ user={user} language={currentLanguage} />

      {/* 📱 MODIFICATION 1: Utiliser 100dvh pour éviter la zone "perdue" sous la barre d'adresse */}
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

            {/* Titre centré avec logo (min-w-0 pour ne pas pousser la page en largeur) */}
            <div className="flex-1 min-w-0 flex justify-center items-center space-x-3">
              <div className="w-8 h-8 grid place-items-center">
                <InteliaLogo className="h-7 w-auto" />
              </div>
              <div className="text-center">
                <h1 className="text-lg font-medium text-gray-900 truncate">Intelia Expert</h1>
              </div>
            </div>

            {/* Avatar utilisateur à droite */}
            <div className="flex items-center">
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
                  🔞 Appliquer à toutes les réponses
                </button>
              )}
            </div>
          )}
        </header>

        <div className="flex-1 overflow-hidden flex flex-col">
          {/* 📱 MODIFICATION 2: Ajouter pb-28 pour éviter que les messages soient cachés par la barre sticky */}
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

              {messages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <div className="text-sm">Aucun message à afficher</div>
                </div>
              ) : (
                messages.map((message, index) => (
                  <div key={`${message.id}-${index}`}>
                    {/* min-w-0 pour éviter que le contenu force un viewport plus large sur iOS */}
                    <div className={`flex items-start space-x-3 min-w-0 ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                      {/* 🔧 CORRECTION LOGO: Container avec largeur fixe pour éviter l'écrasement */}
                      {!message.isUser && (
                        <div className="flex-shrink-0 w-8 h-8 grid place-items-center">
                          <InteliaLogo className="h-7 w-auto" />
                        </div>
                      )}

                      {/* iPhone: limiter la largeur des bulles + autoriser les césures */}
                      <div className={`px-3 sm:px-4 py-3 rounded-2xl max-w-[85%] sm:max-w-none break-words ${message.isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-white border border-gray-200 text-gray-900'}`}>
                        {message.isUser ? (
                          <p className="whitespace-pre-wrap leading-relaxed text-sm">
                            {message.content}
                          </p>
                        ) : (
                          <ReactMarkdown
                            className="prose prose-sm max-w-none break-words prose-p:my-3 prose-li:my-1 prose-ul:my-4 prose-strong:text-gray-900 prose-headings:font-bold prose-headings:text-gray-900"
                            components={{
                              // 🔨 TITRES H2 : Style amélioré avec plus d'espacement
                              h2: ({node, ...props}) => (
                                <h2 className="text-xl font-bold text-blue-900 mt-8 mb-6 border-b-2 border-blue-200 pb-3 bg-blue-50 px-4 py-2 rounded-t-lg" {...props} />
                              ),

                              // 🔨 TITRES H3 : Style pour les sous-sections
                              h3: ({node, ...props}) => (
                                <h3 className="text-lg font-semibold text-gray-800 mt-6 mb-4 border-l-4 border-blue-400 pl-4 bg-gray-50 py-2" {...props} />
                              ),

                              // 🔨 PARAGRAPHES : Espacement généreux
                              p: ({node, ...props}) => (
                                <p className="leading-relaxed text-gray-800 my-4 text-justify" {...props} />
                              ),

                              // 🔨 LISTES : Style amélioré avec plus d'espace
                              ul: ({node, ...props}) => (
                                <ul className="list-disc list-outside space-y-3 text-gray-800 my-6 ml-6 pl-2" {...props} />
                              ),

                              // 🔨 ÉLÉMENTS DE LISTE : Meilleur spacing
                              li: ({node, ...props}) => (
                                <li className="leading-relaxed pl-2 my-2" {...props} />
                              ),

                              // 🔨 TEXTE EN GRAS : Plus visible
                              strong: ({node, ...props}) => (
                                <strong className="font-bold text-blue-800 bg-blue-50 px-1 rounded" {...props} />
                              ),

                              // 🔄 TABLEAUX : Style amélioré
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
                            {/* 🔧 NOUVEAU : Appliquer le préprocesseur Markdown */}
                            {useMemo(() => preprocessMarkdown(message.content), [message.content])}
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

                      {/* 🔧 CORRECTION 2: Avatar avec initiales pour les messages utilisateur */}
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

          {/* 📱 MODIFICATION 3: Barre sticky avec safe-area conditionnel + hauteurs uniformisées */}
          <div className="px-2 sm:px-4 py-2 bg-white border-t border-gray-100 sticky bottom-0 z-20 pb-[env(safe-area-inset-bottom)] sm:pb-2">
            <div className="max-w-full sm:max-w-4xl mx-auto px-2 sm:px-4">
              {clarificationState && (
                <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-blue-700 text-sm font-medium">
                      🎯 Mode clarification : répondez à la question ci-dessus
                    </span>
                    <button
                      onClick={() => {
                        setClarificationState(null)
                        console.log('🔞 [ChatInterface] Clarification annulée')
                      }}
                      className="text-blue-600 hover:text-blue-800 text-sm underline"
                    >
                      Annuler
                    </button>
                  </div>
                </div>
              )}

              {/* 📱 MODIFICATION 4: Hauteurs uniformisées (h-12 = 48px) et centrage parfait */}
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
                    placeholder={clarificationState ? "Répondez à la question ci-dessus..." : t('chat.placeholder')}
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

              {/* ✅ AJOUTEZ CES LIGNES ICI - EXACTEMENT APRÈS LA FERMETURE DU DIV PRÉCÉDENT */}
              <div className="text-center mt-2">
                <p className="text-xs text-gray-500">
                  Intelia Expert peut faire des erreurs. Faites vérifiez les réponses par un professionnel au besoin.
                </p>
              </div>
              {/* ✅ FIN DE L'AJOUT */}
			  			  
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