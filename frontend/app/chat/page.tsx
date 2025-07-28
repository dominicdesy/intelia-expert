'use client'

import React, { useState, useEffect, useRef } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

// Instance Supabase
const supabase = createClientComponentClient()

// ==================== TYPES ÉTENDUS POUR LOGGING ====================
interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  feedback?: 'positive' | 'negative' | null
  conversation_id?: string  // ID pour le tracking des conversations
}

interface ExpertApiResponse {
  question: string
  response: string
  conversation_id: string
  rag_used: boolean
  rag_score?: number
  timestamp: string
  language: string
  response_time_ms: number
  mode: string
  user?: string
}

interface ConversationData {
  user_id: string
  question: string
  response: string
  conversation_id: string
  confidence_score?: number
  response_time_ms?: number
  language?: string
  rag_used?: boolean
}

// ==================== SERVICE DE LOGGING AVEC URL CORRIGÉE ====================
class ConversationService {
  private baseUrl = "https://expert-app-cngws.ondigitalocean.app/api/v1"
  private loggingEnabled = true

  async saveConversation(data: ConversationData): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('📝 Logging désactivé - conversation non sauvegardée:', data.conversation_id)
      return
    }

    try {
      console.log('💾 Sauvegarde conversation:', data.conversation_id)
      console.log('📡 URL de sauvegarde:', `${this.baseUrl}/logging/conversation`)
      
      const response = await fetch(`${this.baseUrl}/logging/conversation`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          user_id: data.user_id,
          question: data.question,
          response: data.response,
          conversation_id: data.conversation_id,
          confidence_score: data.confidence_score,
          response_time_ms: data.response_time_ms,
          language: data.language || 'fr',
          rag_used: data.rag_used !== undefined ? data.rag_used : true
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('✅ Conversation sauvegardée:', result.message)
      
    } catch (error) {
      console.error('❌ Erreur sauvegarde conversation:', error)
      // Ne pas bloquer l'UX si le logging échoue
    }
  }

  async sendFeedback(conversationId: string, feedback: 1 | -1): Promise<void> {
    if (!this.loggingEnabled) {
      console.log('📊 Logging désactivé - feedback non envoyé:', conversationId)
      return
    }

    try {
      console.log('📊 Envoi feedback:', conversationId, feedback)
      console.log('📡 URL feedback:', `${this.baseUrl}/logging/conversation/${conversationId}/feedback`)
      
      const response = await fetch(`${this.baseUrl}/logging/conversation/${conversationId}/feedback`, {
        method: 'PATCH',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ feedback })
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('✅ Feedback enregistré:', result.message)
      
    } catch (error) {
      console.error('❌ Erreur envoi feedback:', error)
      throw error  // Propager pour afficher erreur à l'utilisateur
    }
  }

  async getUserConversations(userId: string, limit = 50): Promise<any[]> {
    if (!this.loggingEnabled) {
      console.log('🔍 Logging désactivé - conversations non récupérées')
      return []
    }

    try {
      console.log('🔍 Récupération conversations pour:', userId)
      console.log('📡 URL conversations:', `${this.baseUrl}/logging/user/${userId}/conversations?limit=${limit}`)
      
      const response = await fetch(`${this.baseUrl}/logging/user/${userId}/conversations?limit=${limit}`, {
        headers: { 'Accept': 'application/json' }
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      console.log('✅ Conversations récupérées:', data.count)
      return data.conversations || []
      
    } catch (error) {
      console.error('❌ Erreur récupération conversations:', error)
      return []
    }
  }
}

// Instance globale du service
const conversationService = new ConversationService()

// ==================== FONCTION generateAIResponse CORRIGÉE ET SIMPLIFIÉE ====================
const generateAIResponse = async (question: string, user: any): Promise<ExpertApiResponse> => {
  // ✅ URL corrigée selon l'API backend validée
  const apiUrl = 'https://expert-app-cngws.ondigitalocean.app/api/v1/expert/ask-public'
  
  try {
    console.log('🤖 Envoi question au RAG Intelia (endpoint public):', question)
    console.log('📡 URL API:', apiUrl)
    console.log('👤 Utilisateur:', user?.id, user?.email)
    
    // ✅ Corps de la requête aligné avec QuestionRequest du backend
    const requestBody = {
      text: question.trim(),
      language: user?.language || 'fr',
      speed_mode: 'balanced'  // Mode par défaut selon l'API
    }
    
    console.log('📤 Corps de la requête:', requestBody)
    
    // ✅ Headers pour endpoint public (pas d'authentification)
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    }
    
    console.log('📤 Headers (endpoint public):', headers)
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(requestBody)
    })

    console.log('📊 Statut réponse API:', response.status, response.statusText)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ Erreur API détaillée:', errorText)
      throw new Error(`Erreur API: ${response.status} - ${errorText}`)
    }

    const data = await response.json()
    console.log('✅ Réponse RAG reçue:', data)
    
    // ✅ Adapter la réponse selon ExpertResponse du backend
    const adaptedResponse: ExpertApiResponse = {
      question: data.question || question,
      response: data.response || "Réponse reçue mais vide",
      conversation_id: data.conversation_id || Date.now().toString(),
      rag_used: data.rag_used || false,
      rag_score: data.rag_score,
      timestamp: data.timestamp || new Date().toISOString(),
      language: data.language || 'fr',
      response_time_ms: data.response_time_ms || 0,
      mode: data.mode || 'unknown',
      user: data.user
    }
    
    // Sauvegarde optionnelle si logging disponible
    if (user && adaptedResponse.conversation_id) {
      try {
        console.log('💾 Tentative sauvegarde conversation...')
        await conversationService.saveConversation({
          user_id: user.id,
          question: question,
          response: adaptedResponse.response,
          conversation_id: adaptedResponse.conversation_id,
          confidence_score: adaptedResponse.rag_score,
          response_time_ms: adaptedResponse.response_time_ms,
          language: adaptedResponse.language,
          rag_used: adaptedResponse.rag_used
        })
      } catch (saveError) {
        console.warn('⚠️ Erreur sauvegarde (non bloquante):', saveError)
      }
    }
    
    return adaptedResponse
    
  } catch (error: any) {
    console.error('❌ Erreur lors de l\'appel au RAG:', error)
    
    if (error.message.includes('Failed to fetch')) {
      throw new Error(`Erreur de connexion au serveur.

**URL testée:** ${apiUrl}
**Erreur technique:** ${error.message}

Vérifiez votre connexion internet et réessayez.`)
    }
    
    throw new Error(`Erreur technique avec l'API : ${error.message}

**URL testée:** ${apiUrl}
**Type d'erreur:** ${error.name}

Consultez la console développeur (F12) pour plus de détails.`)
  }
}

// ==================== TRANSLATIONS COMPLÈTES 3 LANGUES ====================
const translations = {
  fr: {
    'chat.welcome': 'Bonjour ! Comment puis-je vous aider aujourd\'hui ?',
    'chat.placeholder': 'Posez votre question à l\'expert...',
    'chat.loading': 'Chargement...',
    'chat.errorMessage': 'Désolé, je rencontre un problème technique. Veuillez réessayer dans quelques instants.',
    'chat.helpfulResponse': 'Réponse utile',
    'chat.notHelpfulResponse': 'Réponse non utile',
    'chat.voiceRecording': 'Enregistrement vocal (bientôt disponible)',
    'chat.noConversations': 'Aucune conversation',
    'nav.newConversation': 'Nouvelle conversation',
    'nav.history': 'Historique',
    'nav.clearAll': 'Tout effacer',
    'nav.profile': 'Profil',
    'nav.contact': 'Contact',
    'nav.legal': 'Mentions légales',
    'nav.logout': 'Déconnexion',
    'nav.language': 'Langue',
    'subscription.title': 'Abonnement',
    'subscription.currentPlan': 'Forfait actuel',
    'subscription.modify': 'Modifier le forfait',
    'subscription.update': 'Mettre à jour',
    'plan.essential': 'Essentiel',
    'plan.pro': 'Pro',
    'plan.max': 'Max',
    'profile.title': 'Profil utilisateur',
    'profile.personalInfo': 'Informations personnelles',
    'profile.firstName': 'Prénom',
    'profile.lastName': 'Nom',
    'profile.email': 'Email',
    'profile.phone': 'Téléphone',
    'profile.country': 'Pays',
    'profile.company': 'Entreprise',
    'profile.companyName': 'Nom de l\'entreprise',
    'profile.companyWebsite': 'Site web',
    'profile.password': 'Changer le mot de passe',
    'profile.currentPassword': 'Mot de passe actuel',
    'profile.newPassword': 'Nouveau mot de passe',
    'profile.confirmPassword': 'Confirmer le mot de passe',
    'contact.title': 'Nous joindre',
    'contact.phone': 'Nous appeler',
    'contact.phoneDescription': 'Si vous ne trouvez pas de solution, appelez-nous pour parler directement avec notre équipe.',
    'contact.email': 'Nous écrire',
    'contact.emailDescription': 'Envoyez-nous un message détaillé et nous vous répondrons rapidement.',
    'contact.website': 'Visiter notre site web',
    'contact.websiteDescription': 'Pour en savoir plus sur nous et la plateforme Intelia, visitez notre site.',
    'modal.close': 'Fermer',
    'modal.save': 'Sauvegarder',
    'modal.cancel': 'Annuler',
    'modal.loading': 'Chargement...',
    'language.title': 'Changer la langue',
    'language.description': 'Sélectionnez votre langue préférée pour l\'interface Intelia Expert'
  },
  en: {
    'chat.welcome': 'Hello! How can I help you today?',
    'chat.placeholder': 'Ask your question to the expert...',
    'chat.loading': 'Loading...',
    'chat.errorMessage': 'Sorry, I\'m experiencing a technical issue. Please try again in a few moments.',
    'chat.helpfulResponse': 'Helpful response',
    'chat.notHelpfulResponse': 'Not helpful response',
    'chat.voiceRecording': 'Voice recording (coming soon)',
    'chat.noConversations': 'No conversations',
    'nav.newConversation': 'New conversation',
    'nav.history': 'History',
    'nav.clearAll': 'Clear all',
    'nav.profile': 'Profile',
    'nav.contact': 'Contact',
    'nav.legal': 'Legal notices',
    'nav.logout': 'Logout',
    'nav.language': 'Language',
    'subscription.title': 'Subscription',
    'subscription.currentPlan': 'Current plan',
    'subscription.modify': 'Modify plan',
    'subscription.update': 'Update',
    'plan.essential': 'Essential',
    'plan.pro': 'Pro',
    'plan.max': 'Max',
    'profile.title': 'User profile',
    'profile.personalInfo': 'Personal information',
    'profile.firstName': 'First name',
    'profile.lastName': 'Last name',
    'profile.email': 'Email',
    'profile.phone': 'Phone',
    'profile.country': 'Country',
    'profile.company': 'Company',
    'profile.companyName': 'Company name',
    'profile.companyWebsite': 'Website',
    'profile.password': 'Change password',
    'profile.currentPassword': 'Current password',
    'profile.newPassword': 'New password',
    'profile.confirmPassword': 'Confirm password',
    'contact.title': 'Contact us',
    'contact.phone': 'Call us',
    'contact.phoneDescription': 'If you can\'t find a solution, call us to speak directly with our team.',
    'contact.email': 'Email us',
    'contact.emailDescription': 'Send us a detailed message and we\'ll respond quickly.',
    'contact.website': 'Visit our website',
    'contact.websiteDescription': 'To learn more about us and the Intelia platform, visit our site.',
    'modal.close': 'Close',
    'modal.save': 'Save',
    'modal.cancel': 'Cancel',
    'modal.loading': 'Loading...',
    'language.title': 'Change language',
    'language.description': 'Select your preferred language for the Intelia Expert interface'
  },
  es: {
    'chat.welcome': '¡Hola! ¿Cómo puedo ayudarte hoy?',
    'chat.placeholder': 'Haz tu pregunta al experto...',
    'chat.loading': 'Cargando...',
    'chat.errorMessage': 'Lo siento, tengo un problema técnico. Por favor, inténtalo de nuevo en unos momentos.',
    'chat.helpfulResponse': 'Respuesta útil',
    'chat.notHelpfulResponse': 'Respuesta no útil',
    'chat.voiceRecording': 'Grabación de voz (próximamente)',
    'chat.noConversations': 'Sin conversaciones',
    'nav.newConversation': 'Nueva conversación',
    'nav.history': 'Historial',
    'nav.clearAll': 'Borrar todo',
    'nav.profile': 'Perfil',
    'nav.contact': 'Contacto',
    'nav.legal': 'Aviso legal',
    'nav.logout': 'Cerrar sesión',
    'nav.language': 'Idioma',
    'subscription.title': 'Suscripción',
    'subscription.currentPlan': 'Plan actual',
    'subscription.modify': 'Modificar plan',
    'subscription.update': 'Actualizar',
    'plan.essential': 'Esencial',
    'plan.pro': 'Pro',
    'plan.max': 'Máximo',
    'profile.title': 'Perfil de usuario',
    'profile.personalInfo': 'Información personal',
    'profile.firstName': 'Nombre',
    'profile.lastName': 'Apellido',
    'profile.email': 'Email',
    'profile.phone': 'Teléfono',
    'profile.country': 'País',
    'profile.company': 'Empresa',
    'profile.companyName': 'Nombre de la empresa',
    'profile.companyWebsite': 'Sitio web',
    'profile.password': 'Cambiar contraseña',
    'profile.currentPassword': 'Contraseña actual',
    'profile.newPassword': 'Nueva contraseña',
    'profile.confirmPassword': 'Confirmar contraseña',
    'contact.title': 'Contáctanos',
    'contact.phone': 'Llámanos',
    'contact.phoneDescription': 'Si no encuentras una solución, llámanos para hablar directamente con nuestro equipo.',
    'contact.email': 'Escríbenos',
    'contact.emailDescription': 'Envíanos un mensaje detallado y te responderemos rápidamente.',
    'contact.website': 'Visita nuestro sitio web',
    'contact.websiteDescription': 'Para saber más sobre nosotros y la plataforma Intelia, visita nuestro sitio.',
    'modal.close': 'Cerrar',
    'modal.save': 'Guardar',
    'modal.cancel': 'Cancelar',
    'modal.loading': 'Cargando...',
    'language.title': 'Cambiar idioma',
    'language.description': 'Selecciona tu idioma preferido para la interfaz de Intelia Expert'
  }
}

// Hook de traduction simple
const useTranslation = () => {
  const [currentLanguage, setCurrentLanguage] = useState('fr')
  
  const t = (key: string): string => {
    return translations[currentLanguage as keyof typeof translations]?.[key as keyof typeof translations['fr']] || key
  }
  
  const changeLanguage = (lang: string) => {
    console.log('🌐 [useTranslation] changeLanguage appelée:', currentLanguage, '→', lang)
    setCurrentLanguage(lang)
    localStorage.setItem('intelia_language', lang)
    console.log('✅ [useTranslation] État langue mis à jour:', lang)
  }
  
  useEffect(() => {
    const savedLang = localStorage.getItem('intelia_language')
    if (savedLang && translations[savedLang as keyof typeof translations]) {
      setCurrentLanguage(savedLang)
    }
  }, [])
  
  return { t, changeLanguage, currentLanguage }
}

// ==================== COMPOSANT ZOHO SALESIQ - VERSION MULTILINGUE ====================
const ZohoSalesIQ = ({ user }: { user: any }) => {
  const [isZohoReady, setIsZohoReady] = useState(false)
  const [hasError, setHasError] = useState(false)
  const { currentLanguage } = useTranslation()
  const initializationRef = useRef(false)
  const lastLanguageRef = useRef<string>('')
  
  // Fonction pour mapper les codes de langue vers les codes Zoho SalesIQ
  const getZohoLanguage = (lang: string): string => {
    const languageMap: Record<string, string> = {
      'fr': 'fr',      // Français
      'en': 'en',      // English  
      'es': 'es'       // Español
    }
    return languageMap[lang] || 'en' // Défaut anglais si langue non supportée
  }
  
  // Fonction pour changer la langue de Zoho avec rechargement complet
  const changeZohoLanguage = (language: string) => {
    console.log('🌐 [ZohoSalesIQ] changeZohoLanguage appelée avec:', language)
    
    // Pour Zoho SalesIQ, la seule façon fiable de changer la langue
    // est de recharger complètement le widget avec le bon paramètre de langue
    try {
      console.log('🔄 [ZohoSalesIQ] Rechargement complet du widget pour changement langue')
      setIsZohoReady(false)
      
      // 1. Supprimer l'ancien script
      const oldScript = document.getElementById('zsiqscript')
      if (oldScript) {
        oldScript.remove()
        console.log('🗑️ [ZohoSalesIQ] Ancien script supprimé')
      }
      
      // 2. Nettoyer tous les éléments du widget
      const widgets = document.querySelectorAll('[id*="zsiq"], [class*="zsiq"]')
      widgets.forEach(widget => widget.remove())
      console.log('🧹 [ZohoSalesIQ] Widgets nettoyés:', widgets.length)
      
      // 3. Nettoyer l'objet global Zoho
      const globalWindow = window as any
      if (globalWindow.$zoho && globalWindow.$zoho.salesiq) {
        // Garder seulement le widget code
        const widgetCode = globalWindow.$zoho.salesiq.widgetcode
        delete globalWindow.$zoho.salesiq
        globalWindow.$zoho.salesiq = { widgetcode: widgetCode }
        console.log('🧹 [ZohoSalesIQ] Objet Zoho réinitialisé')
      }
      
      // 4. Recharger avec la nouvelle langue après un délai
      setTimeout(() => {
        console.log('🚀 [ZohoSalesIQ] Rechargement script avec langue:', language)
        loadZohoScriptWithLanguage(getZohoLanguage(language))
      }, 1000)
      
    } catch (error) {
      console.warn('❌ [ZohoSalesIQ] Erreur rechargement widget:', error)
    }
  }
  
  // Fonction pour charger le script Zoho avec une langue spécifique
  const loadZohoScriptWithLanguage = (language: string) => {
    console.log('📡 [ZohoSalesIQ] loadZohoScriptWithLanguage appelée avec:', language)
    const globalWindow = window as any
    
    // Réinitialiser l'objet Zoho avec la nouvelle langue
    globalWindow.$zoho = globalWindow.$zoho || {}
    globalWindow.$zoho.salesiq = globalWindow.$zoho.salesiq || {}
    globalWindow.$zoho.salesiq.widgetcode = 'siq31d58179214fbbfbb0a5b5eb16ab9173ba0ee84601e9d7d04840d96541bc7e4f'
    
    // Configuration du callback ready avec la langue
    globalWindow.$zoho.salesiq.ready = function() {
      console.log('🎯 [ZohoSalesIQ] Widget prêt avec langue:', language)
      
      setTimeout(() => {
        try {
          const zoho = globalWindow.$zoho?.salesiq
          if (!zoho) return
          
          // Configuration visiteur
          if (zoho.visitor && typeof zoho.visitor.info === 'function') {
            zoho.visitor.info({
              name: user.name || 'Utilisateur Intelia',
              email: user.email || ''
            })
            console.log('👤 [ZohoSalesIQ] Visiteur configuré')
          }
          
          // Démarrage chat
          setTimeout(() => {
            if (zoho.chat && typeof zoho.chat.start === 'function') {
              zoho.chat.start()
              console.log('💬 [ZohoSalesIQ] Chat démarré')
            }
          }, 2000)
          
          // Affichage widget
          setTimeout(() => {
            if (zoho.floatbutton && typeof zoho.floatbutton.visible === 'function') {
              zoho.floatbutton.visible('show')
              console.log('👀 [ZohoSalesIQ] Widget visible')
              setIsZohoReady(true)
            }
          }, 3000)
          
        } catch (error) {
          console.warn('⚠️ [ZohoSalesIQ] Erreur configuration widget:', error)
        }
      }, 1000)
    }
    
    // Créer et charger le script avec la langue
    const script = document.createElement('script')
    script.type = 'text/javascript'
    script.async = true
    script.defer = true
    script.id = 'zsiqscript'
    script.crossOrigin = 'anonymous'
    
    // URL avec paramètre de langue pour SalesIQ
    script.src = `https://salesiq.zohopublic.com/widget?wc=${globalWindow.$zoho.salesiq.widgetcode}&locale=${language}`
    
    console.log('📡 [ZohoSalesIQ] URL script avec langue:', script.src)
    
    script.onload = () => {
      console.log(`✅ [ZohoSalesIQ] Script chargé avec langue: ${language}`)
    }
    
    script.onerror = (error) => {
      console.error('❌ [ZohoSalesIQ] Erreur chargement script:', error)
      setHasError(true)
    }
    
    document.head.appendChild(script)
  }
  
  // Effet pour gérer le changement de langue - rechargement immédiat
  useEffect(() => {
    console.log('🎯 [ZohoSalesIQ] useEffect déclenché - currentLanguage:', currentLanguage, 'isZohoReady:', isZohoReady, 'lastLanguage:', lastLanguageRef.current)
    
    if (isZohoReady && currentLanguage && currentLanguage !== lastLanguageRef.current) {
      console.log(`🔄 [ZohoSalesIQ] Changement langue Zoho: ${lastLanguageRef.current} → ${currentLanguage}`)
      
      // Pour Zoho SalesIQ, rechargement immédiat du widget
      changeZohoLanguage(currentLanguage)
      lastLanguageRef.current = currentLanguage
      console.log('✅ [ZohoSalesIQ] lastLanguageRef mis à jour:', currentLanguage)
    } else {
      console.log('⏸️ [ZohoSalesIQ] useEffect - conditions non remplies pour changement langue')
    }
  }, [currentLanguage, isZohoReady])
  
  useEffect(() => {
    if (!user || hasError || initializationRef.current) return

    console.log('🚀 Initialisation Zoho SalesIQ pour:', user.email, 'Langue:', currentLanguage)
    initializationRef.current = true
    lastLanguageRef.current = currentLanguage
    
    const initializeZohoSafely = () => {
      try {
        // 1. Configuration globale sécurisée avec le bon widget code
        const globalWindow = window as any
        globalWindow.$zoho = globalWindow.$zoho || {}
        globalWindow.$zoho.salesiq = globalWindow.$zoho.salesiq || {}
        globalWindow.$zoho.salesiq.widgetcode = 'siq31d58179214fbbfbb0a5b5eb16ab9173ba0ee84601e9d7d04840d96541bc7e4f'
        
        // 2. Override ready function avec gestion d'erreurs complète + langue
        globalWindow.$zoho.salesiq.ready = function() {
          console.log('🎯 Zoho ready callback - Initialisation sécurisée avec langue:', currentLanguage)
          
          // Attendre que le DOM et Zoho soient complètement chargés
          setTimeout(() => {
            try {
              const zoho = globalWindow.$zoho?.salesiq
              if (!zoho) {
                throw new Error('Zoho SalesIQ object not available')
              }
              
              // 3. Configuration visiteur avec vérifications strictes
              if (zoho.visitor && typeof zoho.visitor.info === 'function') {
                zoho.visitor.info({
                  name: user.name || 'Utilisateur Intelia',
                  email: user.email || ''
                })
                console.log('👤 Visiteur configuré:', user.name)
              }
              
              // 4. Configuration langue dès l'initialisation
              const initialLanguage = getZohoLanguage(currentLanguage)
              if (zoho.set && typeof zoho.set === 'function') {
                zoho.set('locale', initialLanguage)
                console.log(`🌐 Langue Zoho initialisée: ${initialLanguage}`)
              }
              
              // 5. Démarrage chat avec protection addClass
              setTimeout(() => {
                try {
                  if (zoho.chat && typeof zoho.chat.start === 'function') {
                    // Vérifier que les éléments DOM sont prêts
                    const checkDOMReady = () => {
                      const widget = document.querySelector('#zsiq_float') || 
                                   document.querySelector('[id*="zsiq"]') ||
                                   document.querySelector('.zsiq_float')
                      
                      if (widget || document.readyState === 'complete') {
                        zoho.chat.start()
                        console.log('💬 Chat Zoho démarré avec succès')
                        return true
                      }
                      return false
                    }
                    
                    if (!checkDOMReady()) {
                      // Retry après chargement complet
                      window.addEventListener('load', () => {
                        setTimeout(() => {
                          try {
                            zoho.chat.start()
                            console.log('💬 Chat Zoho démarré (après load)')
                          } catch (e) {
                            console.warn('⚠️ Chat start failed (non-critical)')
                          }
                        }, 1000)
                      })
                    }
                  }
                } catch (chatError) {
                  console.warn('⚠️ Erreur chat start (non critique):', chatError.message)
                }
              }, 4000) // Délai augmenté pour stabilité
              
              // 6. Affichage widget avec protection addClass  
              setTimeout(() => {
                try {
                  if (zoho.floatbutton && typeof zoho.floatbutton.visible === 'function') {
                    // Double vérification DOM avant addClass
                    const ensureWidgetReady = () => {
                      const widgetElements = document.querySelectorAll('[class*="zsiq"], [id*="zsiq"]')
                      if (widgetElements.length > 0) {
                        zoho.floatbutton.visible('show')
                        console.log('👀 Widget Zoho visible')
                        setIsZohoReady(true)
                        return true
                      }
                      return false
                    }
                    
                    if (!ensureWidgetReady()) {
                      // Observer pour détecter l'ajout des éléments Zoho
                      const observer = new MutationObserver((mutations) => {
                        mutations.forEach((mutation) => {
                          if (mutation.addedNodes.length > 0) {
                            const hasZohoNode = Array.from(mutation.addedNodes).some(node => 
                              node.nodeType === 1 && 
                              (node as Element).id?.includes('zsiq') ||
                              (node as Element).className?.includes('zsiq')
                            )
                            if (hasZohoNode && ensureWidgetReady()) {
                              observer.disconnect()
                            }
                          }
                        })
                      })
                      
                      observer.observe(document.body, {
                        childList: true,
                        subtree: true
                      })
                      
                      // Timeout safety
                      setTimeout(() => {
                        observer.disconnect()
                        if (!isZohoReady) {
                          console.log('⚠️ Timeout widget detection - fonctionnement silencieux')
                        }
                      }, 10000)
                    }
                  }
                } catch (widgetError) {
                  console.warn('⚠️ Erreur widget visibility (non critique):', widgetError.message)
                }
              }, 6000) // Délai augmenté pour stabilité
              
            } catch (error) {
              console.warn('⚠️ Erreur configuration Zoho (non bloquante):', error.message)
              setHasError(true)
            }
          }, 3000) // Délai initial augmenté
        }
        
        // 3. Chargement script avec gestion d'erreurs robuste et langue initiale
        const loadZohoScript = () => {
          // Nettoyer anciens scripts
          document.querySelectorAll('script[src*="salesiq.zohopublic.com"]').forEach(s => s.remove())
          
          const script = document.createElement('script')
          script.type = 'text/javascript'
          script.async = true
          script.defer = true
          script.id = 'zsiqscript'
          script.crossOrigin = 'anonymous'
          
          // Inclure la langue dans l'URL du script
          const initialLanguage = getZohoLanguage(currentLanguage)
          script.src = `https://salesiq.zohopublic.com/widget?wc=${globalWindow.$zoho.salesiq.widgetcode}&locale=${initialLanguage}`
          
          script.onload = () => {
            console.log(`✅ Script Zoho chargé avec succès (langue: ${initialLanguage})`)
          }
          
          script.onerror = (error) => {
            console.error('❌ Erreur chargement Zoho script:', error)
            setHasError(true)
          }
          
          // Timeout de sécurité
          setTimeout(() => {
            if (!document.head.contains(script)) {
              console.warn('⚠️ Timeout script Zoho')
              setHasError(true)
            }
          }, 15000)
          
          document.head.appendChild(script)
        }
        
        // 4. Démarrage avec délai de sécurité
        setTimeout(loadZohoScript, 2000)
        
      } catch (error) {
        console.error('❌ Erreur critique Zoho:', error)
        setHasError(true)
      }
    }
    
    // Gestion des erreurs CSP
    const handleSecurityError = (event: any) => {
      if (event.sourceFile?.includes('zoho') || event.violatedDirective?.includes('connect-src')) {
        console.warn('⚠️ Erreur sécurité Zoho détectée:', event.violatedDirective)
        setHasError(true)
      }
    }
    
    window.addEventListener('securitypolicyviolation', handleSecurityError)
    window.addEventListener('error', (event) => {
      if (event.filename?.includes('zoho')) {
        console.warn('⚠️ Erreur script Zoho détectée')
        setHasError(true)
      }
    })
    
    // Initialisation
    initializeZohoSafely()
    
    return () => {
      window.removeEventListener('securitypolicyviolation', handleSecurityError)
      initializationRef.current = false
    }
    
  }, [user, hasError, currentLanguage]) // Ajout de currentLanguage dans les dépendances
  
  // Feedback utilisateur
  useEffect(() => {
    if (hasError) {
      console.log('📞 Support Intelia: support@intelia.com | +1 (866) 666 6221')
    } else if (isZohoReady) {
      console.log('🎉 Zoho SalesIQ totalement opérationnel')
    }
  }, [hasError, isZohoReady])

  return null
}

// ==================== STORE D'AUTHENTIFICATION ÉTENDU ====================
const useAuthStore = () => {
  const [user, setUser] = useState<any>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadUser = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('❌ Erreur récupération session:', error)
          setIsAuthenticated(false)
          setIsLoading(false)
          return
        }

        if (session?.user) {
          console.log('✅ Utilisateur connecté:', session.user.email)
          
          const userData = {
            id: session.user.id,
            email: session.user.email,
            name: `${session.user.user_metadata?.first_name || ''} ${session.user.user_metadata?.last_name || ''}`.trim() || session.user.email?.split('@')[0],
            firstName: session.user.user_metadata?.first_name || '',
            lastName: session.user.user_metadata?.last_name || '',
            phone: session.user.user_metadata?.phone || '',
            country: session.user.user_metadata?.country || '',
            linkedinProfile: session.user.user_metadata?.linkedin_profile || '',
            companyName: session.user.user_metadata?.company_name || '',
            companyWebsite: session.user.user_metadata?.company_website || '',
            linkedinCorporate: session.user.user_metadata?.linkedin_corporate || '',
            user_type: session.user.user_metadata?.role || 'producer',
            language: session.user.user_metadata?.language || 'fr',
            created_at: session.user.created_at,
            plan: 'essential'
          }
          
          setUser(userData)
          setIsAuthenticated(true)
        } else {
          console.log('ℹ️ Aucun utilisateur connecté')
          setIsAuthenticated(false)
        }
      } catch (error) {
        console.error('❌ Erreur chargement utilisateur:', error)
        setIsAuthenticated(false)
      } finally {
        setIsLoading(false)
      }
    }

    loadUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('🔄 Changement auth:', event, session?.user?.email)
        
        if (event === 'SIGNED_OUT') {
          setUser(null)
          setIsAuthenticated(false)
        } else if (event === 'SIGNED_IN' && session?.user) {
          loadUser()
        }
      }
    )

    return () => {
      if (subscription?.unsubscribe) {
        subscription.unsubscribe()
      }
    }
  }, [])

  const logout = async () => {
    try {
      console.log('🚪 Déconnexion en cours...')
      const { error } = await supabase.auth.signOut()
      
      if (error) {
        console.error('❌ Erreur déconnexion:', error)
        return
      }
      
      setUser(null)
      setIsAuthenticated(false)
      window.location.href = '/'
    } catch (error) {
      console.error('❌ Erreur critique déconnexion:', error)
    }
  }

  const updateProfile = async (data: any) => {
    try {
      console.log('📝 Mise à jour profil:', data)
      
      // Préparer les métadonnées utilisateur avec toutes les nouvelles données
      const updates = {
        data: {
          first_name: data.firstName,
          last_name: data.lastName,
          phone: data.phone,
          country: data.country,
          linkedin_profile: data.linkedinProfile,
          company_name: data.companyName,
          company_website: data.companyWebsite,
          linkedin_corporate: data.linkedinCorporate,
          language: data.language
        }
      }
      
      const { error } = await supabase.auth.updateUser(updates)
      
      if (error) {
        console.error('❌ Erreur mise à jour profil:', error)
        return { success: false, error: error.message }
      }
      
      // Mise à jour des données utilisateur locales avec toutes les nouvelles informations
      const updatedUser = {
        ...user,
        ...data,
        name: `${data.firstName} ${data.lastName}`.trim(),
        phone: data.phone,
        country: data.country,
        linkedinProfile: data.linkedinProfile,
        companyName: data.companyName,
        companyWebsite: data.companyWebsite,
        linkedinCorporate: data.linkedinCorporate
      }
      
      setUser(updatedUser)
      console.log('✅ Profil mis à jour localement:', updatedUser)
      
      return { success: true }
    } catch (error: any) {
      console.error('❌ Erreur critique mise à jour:', error)
      return { success: false, error: error.message }
    }
  }

  return {
    user,
    isAuthenticated,
    isLoading,
    logout,
    updateProfile
  }
}

// ==================== HOOK CHAT AVEC LOGGING ====================
interface ConversationItem {
  id: string
  title: string
  messages: Array<{
    id: string
    role: string
    content: string
  }>
  updated_at: string
  created_at: string
  feedback?: number | null
}

const useChatStore = () => {
  const [conversations, setConversations] = useState<ConversationItem[]>([])

  const loadConversations = async (userId: string) => {
    try {
      console.log('🔄 Chargement conversations depuis le logging...')
      const userConversations = await conversationService.getUserConversations(userId)
      
      const formattedConversations: ConversationItem[] = userConversations.map(conv => ({
        id: conv.conversation_id,
        title: conv.question.substring(0, 50) + '...',
        messages: [
          { id: `${conv.conversation_id}-q`, role: 'user', content: conv.question },
          { id: `${conv.conversation_id}-a`, role: 'assistant', content: conv.response }
        ],
        updated_at: conv.updated_at,
        created_at: conv.timestamp,
        feedback: conv.feedback || null
      }))
      
      setConversations(formattedConversations)
      console.log('✅ Conversations chargées:', formattedConversations.length)
    } catch (error) {
      console.error('❌ Erreur chargement conversations:', error)
    }
  }

  const deleteConversation = async (id: string) => {
    try {
      console.log('🗑️ Suppression conversation:', id)
      setConversations(prev => prev.filter(conv => conv.id !== id))
    } catch (error) {
      console.error('❌ Erreur suppression conversation:', error)
    }
  }

  const clearAllConversations = async () => {
    try {
      console.log('🗑️ Suppression toutes conversations')
      setConversations([])
    } catch (error) {
      console.error('❌ Erreur suppression conversations:', error)
    }
  }

  return {
    conversations,
    loadConversations,
    deleteConversation,
    clearAllConversations
  }
}

// ==================== ICÔNES SVG ====================
const PaperAirplaneIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0 1 21.485 12 59.77 59.77 0 0 1 3.27 20.876L5.999 12zm0 0h7.5" />
  </svg>
)

const UserIcon = ({ className = "w-8 h-8" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
  </svg>
)

const PlusIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
  </svg>
)

const EllipsisVerticalIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
  </svg>
)

const ThumbUpIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
  </svg>
)

const ThumbDownIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.43a2 2 0 00-1.106-1.79l-.05-.025A4 4 0 0011.057 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
  </svg>
)

const TrashIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
  </svg>
)

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== COMPOSANTS MODAL ====================
const Modal = ({ isOpen, onClose, title, children }: {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}) => {
  if (!isOpen) return null

  return (
    <>
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-50" 
        onClick={onClose}
      />
      <div 
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
      >
        <div 
          className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>
          <div className="p-6">
            {children}
          </div>
        </div>
      </div>
    </>
  )
}

// ==================== MODAL PROFIL ÉTENDU AVEC ONGLETS ====================
const UserInfoModal = ({ user, onClose }: { user: any, onClose: () => void }) => {
  const { updateProfile } = useAuthStore()
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')
  
  const [formData, setFormData] = useState({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    email: user?.email || '',
    phone: user?.phone || '',
    country: user?.country || '',
    linkedinProfile: user?.linkedinProfile || '',
    companyName: user?.companyName || '',
    companyWebsite: user?.companyWebsite || '',
    linkedinCorporate: user?.linkedinCorporate || ''
  })

  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })

  const [passwordErrors, setPasswordErrors] = useState<string[]>([])

  const validatePassword = (password: string): string[] => {
    const errors: string[] = []
    
    if (password.length < 8) {
      errors.push('Le mot de passe doit contenir au moins 8 caractères')
    }
    if (!/[A-Z]/.test(password)) {
      errors.push('Le mot de passe doit contenir au moins une majuscule')
    }
    if (!/[a-z]/.test(password)) {
      errors.push('Le mot de passe doit contenir au moins une minuscule')
    }
    if (!/\d/.test(password)) {
      errors.push('Le mot de passe doit contenir au moins un chiffre')
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      errors.push('Le mot de passe doit contenir au moins un caractère spécial')
    }
    
    return errors
  }

  const handleProfileSave = async () => {
    setIsLoading(true)
    try {
      const result = await updateProfile(formData)
      if (result.success) {
        alert(t('profile.title') + ' mis à jour avec succès!')
        onClose()
      } else {
        alert('Erreur lors de la mise à jour: ' + (result.error || 'Erreur inconnue'))
      }
    } catch (error) {
      console.error('❌ Erreur mise à jour profil:', error)
      alert('Erreur lors de la mise à jour du profil')
    }
    setIsLoading(false)
  }

  const handlePasswordChange = async () => {
    // Validation des mots de passe
    const errors: string[] = []
    
    if (!passwordData.currentPassword) {
      errors.push('Le mot de passe actuel est requis')
    }
    if (!passwordData.newPassword) {
      errors.push('Le nouveau mot de passe est requis')
    }
    if (!passwordData.confirmPassword) {
      errors.push('La confirmation du mot de passe est requise')
    }
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      errors.push('Les mots de passe ne correspondent pas')
    }
    
    // Validation de la complexité du nouveau mot de passe
    const passwordValidationErrors = validatePassword(passwordData.newPassword)
    errors.push(...passwordValidationErrors)
    
    setPasswordErrors(errors)
    
    if (errors.length > 0) {
      return
    }

    setIsLoading(true)
    try {
      console.log('🔒 Changement de mot de passe en cours...')
      
      const { error } = await supabase.auth.updateUser({
        password: passwordData.newPassword
      })
      
      if (error) {
        console.error('❌ Erreur changement mot de passe:', error)
        setPasswordErrors([error.message || 'Erreur lors du changement de mot de passe'])
        return
      }
      
      console.log('✅ Mot de passe changé avec succès')
      alert('Mot de passe changé avec succès!')
      
      // Réinitialiser le formulaire
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      })
      setPasswordErrors([])
      
      onClose()
      
    } catch (error: any) {
      console.error('❌ Erreur critique changement mot de passe:', error)
      setPasswordErrors([error.message || 'Erreur technique lors du changement de mot de passe'])
    } finally {
      setIsLoading(false)
    }
  }

  const tabs = [
    { id: 'profile', label: 'Profil', icon: '👤' },
    { id: 'password', label: 'Mot de passe', icon: '🔒' }
  ]

  return (
    <div className="space-y-4">
      {/* Onglets */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Contenu des onglets */}
      <div className="space-y-6 max-h-[60vh] overflow-y-auto">
        {activeTab === 'profile' && (
          <>
            {/* Section Informations Personnelles */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4 border-b border-gray-200 pb-2">
                {t('profile.personalInfo')}
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.firstName')}</label>
                  <input
                    type="text"
                    value={formData.firstName}
                    onChange={(e) => setFormData(prev => ({ ...prev, firstName: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.lastName')}</label>
                  <input
                    type="text"
                    value={formData.lastName}
                    onChange={(e) => setFormData(prev => ({ ...prev, lastName: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.email')}</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.phone')}</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                    placeholder="+1 (555) 123-4567"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.country')}</label>
                  <select
                    value={formData.country}
                    onChange={(e) => setFormData(prev => ({ ...prev, country: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Sélectionner un pays</option>
                    <option value="CA">🇨🇦 Canada</option>
                    <option value="US">🇺🇸 États-Unis</option>
                    <option value="FR">🇫🇷 France</option>
                    <option value="BE">🇧🇪 Belgique</option>
                    <option value="CH">🇨🇭 Suisse</option>
                    <option value="MX">🇲🇽 Mexique</option>
                    <option value="BR">🇧🇷 Brésil</option>
                    <option value="other">🌍 Autre</option>
                  </select>
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Profil LinkedIn Personnel
                </label>
                <input
                  type="url"
                  value={formData.linkedinProfile}
                  onChange={(e) => setFormData(prev => ({ ...prev, linkedinProfile: e.target.value }))}
                  placeholder="https://linkedin.com/in/votre-profil"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Section Entreprise */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4 border-b border-gray-200 pb-2">
                {t('profile.company')}
              </h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.companyName')}</label>
                <input
                  type="text"
                  value={formData.companyName}
                  onChange={(e) => setFormData(prev => ({ ...prev, companyName: e.target.value }))}
                  placeholder="Nom de votre entreprise ou exploitation"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.companyWebsite')}</label>
                <input
                  type="url"
                  value={formData.companyWebsite}
                  onChange={(e) => setFormData(prev => ({ ...prev, companyWebsite: e.target.value }))}
                  placeholder="https://www.votre-entreprise.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Page LinkedIn Entreprise
                </label>
                <input
                  type="url"
                  value={formData.linkedinCorporate}
                  onChange={(e) => setFormData(prev => ({ ...prev, linkedinCorporate: e.target.value }))}
                  placeholder="https://linkedin.com/company/votre-entreprise"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </>
        )}

        {activeTab === 'password' && (
          <div className="pb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4 border-b border-gray-200 pb-2">
              {t('profile.password')}
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.currentPassword')} *</label>
                <input
                  type="password"
                  value={passwordData.currentPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, currentPassword: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.newPassword')} *</label>
                <input
                  type="password"
                  value={passwordData.newPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, newPassword: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <div className="mt-2 text-xs text-gray-600">
                  <p>Le mot de passe doit contenir :</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Au moins 8 caractères</li>
                    <li>Au moins une majuscule</li>
                    <li>Au moins une minuscule</li>
                    <li>Au moins un chiffre</li>
                    <li>Au moins un caractère spécial</li>
                  </ul>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.confirmPassword')} *</label>
                <input
                  type="password"
                  value={passwordData.confirmPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              {passwordErrors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                  <div className="text-sm text-red-800">
                    <p className="font-medium">Erreurs :</p>
                    <ul className="list-disc list-inside mt-1">
                      {passwordErrors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <button
          onClick={onClose}
          className="px-4 py-2 text-gray-600 hover:text-gray-800"
          disabled={isLoading}
        >
          {t('modal.cancel')}
        </button>
        <button
          onClick={activeTab === 'profile' ? handleProfileSave : handlePasswordChange}
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? t('modal.loading') : t('modal.save')}
        </button>
      </div>
    </div>
  )
}

const AccountModal = ({ user, onClose }: { user: any, onClose: () => void }) => {
  const { t } = useTranslation()
  
  const currentPlan = user?.plan || 'essential'
  
  const plans = {
    essential: {
      name: t('plan.essential'),
      price: 'Gratuit',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      features: [
        '50 questions par mois',
        'Accès aux documents publics',
        'Support par email',
        'Interface web'
      ]
    },
    pro: {
      name: t('plan.pro'),
      price: '29$ / mois',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      features: [
        'Questions illimitées',
        'Accès documents confidentiels',
        'Support prioritaire',
        'Interface web + mobile',
        'Analytics avancées'
      ]
    }
  }

  const userPlan = plans[currentPlan as keyof typeof plans]

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('subscription.currentPlan')}</h3>
        <div className={`inline-flex items-center px-4 py-2 rounded-full ${userPlan.bgColor} ${userPlan.borderColor} border`}>
          <span className={`font-medium ${userPlan.color}`}>{userPlan.name}</span>
          <span className="mx-2 text-gray-400">•</span>
          <span className={`font-bold ${userPlan.color}`}>{userPlan.price}</span>
        </div>
      </div>

      <div className={`p-4 rounded-lg ${userPlan.bgColor} ${userPlan.borderColor} border`}>
        <h4 className="font-medium text-gray-900 mb-3">Fonctionnalités incluses :</h4>
        <ul className="space-y-2">
          {userPlan.features.map((feature, index) => (
            <li key={index} className="flex items-center text-sm text-gray-700">
              <span className="text-green-500 mr-2">✓</span>
              {feature}
            </li>
          ))}
        </ul>
      </div>

      <div className="flex justify-end pt-4">
        <button
          onClick={onClose}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          {t('modal.close')}
        </button>
      </div>
    </div>
  )
}

const LanguageModal = ({ onClose }: { onClose: () => void }) => {
  const { t, changeLanguage, currentLanguage } = useTranslation()
  const { updateProfile } = useAuthStore()
  const [isUpdating, setIsUpdating] = useState(false)
  
  const languages = [
    { 
      code: 'fr', 
      name: 'Français', 
      region: 'France', 
      flag: '🇫🇷',
      description: 'Interface en français'
    },
    { 
      code: 'en', 
      name: 'English', 
      region: 'United States', 
      flag: '🇺🇸',
      description: 'Interface in English'
    },
    { 
      code: 'es', 
      name: 'Español', 
      region: 'Latinoamérica', 
      flag: '🇪🇸',
      description: 'Interfaz en español'
    }
  ]

  const handleLanguageChange = async (languageCode: string) => {
    if (languageCode === currentLanguage) return

    setIsUpdating(true)
    try {
      console.log('🔄 [LanguageModal] Début changement langue:', currentLanguage, '→', languageCode)
      
      changeLanguage(languageCode)
      console.log('✅ [LanguageModal] changeLanguage() appelée avec:', languageCode)
      
      await updateProfile({ language: languageCode })
      console.log('✅ [LanguageModal] updateProfile() terminé')
      console.log('📊 [LanguageModal] Langue mise à jour:', languageCode)
      
      // Fermeture immédiate - le changement est maintenant dynamique
      onClose()
    } catch (error) {
      console.error('❌ [LanguageModal] Erreur changement langue:', error)
    }
    setIsUpdating(false)
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 mb-4">
        {t('language.description')}
      </p>
      
      <div className="space-y-3">
        {languages.map((language) => (
          <button
            key={language.code}
            onClick={() => handleLanguageChange(language.code)}
            disabled={isUpdating}
            className={`w-full flex items-center justify-between p-4 rounded-xl border-2 transition-all duration-200 ${
              currentLanguage === language.code
                ? 'border-blue-500 bg-blue-50 text-blue-900 shadow-md'
                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
            } ${isUpdating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <div className="flex items-center space-x-4">
              <span className="text-3xl">{language.flag}</span>
              <div className="text-left">
                <div className="font-semibold text-base">{language.name}</div>
                <div className="text-xs text-gray-500">{language.region}</div>
                <div className="text-xs text-gray-400 mt-1">{language.description}</div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              {currentLanguage === language.code && (
                <div className="flex items-center space-x-2">
                  {isUpdating ? (
                    <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                  <span className="text-sm font-medium text-blue-600">
                    {isUpdating ? 'Updating...' : 'Active'}
                  </span>
                </div>
              )}
            </div>
          </button>
        ))}
      </div>

      <div className="flex justify-end pt-4 border-t border-gray-200">
        <button
          onClick={onClose}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          disabled={isUpdating}
        >
          {t('modal.close')}
        </button>
      </div>
    </div>
  )
}

const ContactModal = ({ onClose }: { onClose: () => void }) => {
  const { t } = useTranslation()
  
  return (
    <div className="space-y-4">
      {/* Call Us */}
      <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">{t('contact.phone')}</h3>
          <p className="text-sm text-gray-600 mb-2">
            {t('contact.phoneDescription')}
          </p>
          <a 
            href="tel:+18666666221"
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            +1 (866) 666 6221
          </a>
        </div>
      </div>

      {/* Email Us */}
      <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">{t('contact.email')}</h3>
          <p className="text-sm text-gray-600 mb-2">
            {t('contact.emailDescription')}
          </p>
          <a 
            href="mailto:support@intelia.com"
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            support@intelia.com
          </a>
        </div>
      </div>

      {/* Visit our website */}
      <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3s-4.5 4.03-4.5 9 2.015 9 4.5 9zm0 0c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3s4.5 4.03 4.5 9-2.015 9-4.5 9z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">{t('contact.website')}</h3>
          <p className="text-sm text-gray-600 mb-2">
            {t('contact.websiteDescription')}
          </p>
          <a 
            href="https://www.intelia.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            www.intelia.com
          </a>
        </div>
      </div>

      <div className="flex justify-end pt-3">
        <button
          onClick={onClose}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          {t('modal.close')}
        </button>
      </div>
    </div>
  )
}

// ==================== MENU HISTORIQUE AVEC LOGGING ====================
const HistoryMenu = () => {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const { conversations, deleteConversation, clearAllConversations, loadConversations } = useChatStore()
  const { user } = useAuthStore()

  const handleToggle = () => {
    if (!isOpen && user) {
      loadConversations(user.id)
    }
    setIsOpen(!isOpen)
  }

  return (
    <div className="relative">
      <button
        onClick={handleToggle}
        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        title={t('nav.history')}
      >
        <EllipsisVerticalIcon className="w-5 h-5" />
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          <div className="absolute left-0 top-full mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-96 overflow-y-auto">
            <div className="p-4 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">{t('nav.history')}</h3>
                <button
                  onClick={() => {
                    clearAllConversations()
                    setIsOpen(false)
                  }}
                  className="text-red-600 hover:text-red-700 text-sm"
                >
                  {t('nav.clearAll')}
                </button>
              </div>
            </div>
            
            <div className="max-h-64 overflow-y-auto">
              {conversations.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-sm">
                  {t('chat.noConversations')}
                </div>
              ) : (
                conversations.map((conv) => (
                  <div key={conv.id} className="p-3 hover:bg-gray-50 border-b border-gray-50 last:border-b-0">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {conv.title}
                        </h4>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(conv.updated_at).toLocaleDateString('fr-FR')}
                        </p>
                        {conv.feedback && (
                          <div className="text-xs text-gray-400 mt-1">
                            {conv.feedback === 1 ? '👍 Apprécié' : '👎 Pas utile'}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => deleteConversation(conv.id)}
                        className="ml-2 p-1 text-gray-400 hover:text-red-600 transition-colors"
                        title="Supprimer"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ==================== MENU UTILISATEUR ====================
const UserMenuButton = () => {
  const { user, logout } = useAuthStore()
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [showUserInfoModal, setShowUserInfoModal] = useState(false)
  const [showContactModal, setShowContactModal] = useState(false)
  const [showAccountModal, setShowAccountModal] = useState(false)
  const [showLanguageModal, setShowLanguageModal] = useState(false)

  const userName = user?.name || user?.email || 'Utilisateur'
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
  
  const currentPlan = user?.plan || 'essential'
  const planConfig = {
    essential: { name: t('plan.essential'), bgColor: 'bg-green-50', textColor: 'text-green-600', borderColor: 'border-green-200' },
    pro: { name: t('plan.pro'), bgColor: 'bg-blue-50', textColor: 'text-blue-600', borderColor: 'border-blue-200' }
  }
  const plan = planConfig[currentPlan as keyof typeof planConfig] || planConfig.essential

  const handleContactClick = () => {
    setIsOpen(false)
    setShowContactModal(true)
  }

  const handleUserInfoClick = () => {
    setIsOpen(false)
    setShowUserInfoModal(true)
  }

  const handleAccountClick = () => {
    setIsOpen(false)
    setShowAccountModal(true)
  }

  const handleLanguageClick = () => {
    setIsOpen(false)
    setShowLanguageModal(true)
  }

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors"
        >
          <span className="text-white text-xs font-medium">{userInitials}</span>
        </button>

        {isOpen && (
          <>
            <div 
              className="fixed inset-0 z-40" 
              onClick={() => setIsOpen(false)}
            />
            
            <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
                <div className="mt-2">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${plan.bgColor} ${plan.textColor} border ${plan.borderColor}`}>
                    {plan.name}
                  </span>
                </div>
              </div>

              <button
                onClick={handleAccountClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z" />
                </svg>
                <span>{t('subscription.title')}</span>
              </button>

              <button
                onClick={handleUserInfoClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
                <span>{t('nav.profile')}</span>
              </button>

              <button
                onClick={handleLanguageClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m10.5 21 5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 0 1 6-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 0 1-3.827-5.802" />
                </svg>
                <span>{t('nav.language')}</span>
              </button>

              <button
                onClick={handleContactClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                </svg>
                <span>{t('nav.contact')}</span>
              </button>

              <button
                onClick={() => window.open('https://intelia.com/privacy-policy/', '_blank')}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875v12.75c0 .621.504 1.125 1.125 1.125h2.25" />
                </svg>
                <span>{t('nav.legal')}</span>
              </button>
              
              <div className="border-t border-gray-100 mt-2 pt-2">
                <button
                  onClick={() => {
                    logout()
                    setIsOpen(false)
                  }}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
                  </svg>
                  <span>{t('nav.logout')}</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      <Modal
        isOpen={showAccountModal}
        onClose={() => setShowAccountModal(false)}
        title={t('subscription.title')}
      >
        <AccountModal user={user} onClose={() => setShowAccountModal(false)} />
      </Modal>

      <Modal
        isOpen={showUserInfoModal}
        onClose={() => setShowUserInfoModal(false)}
        title={t('profile.title')}
      >
        <UserInfoModal user={user} onClose={() => setShowUserInfoModal(false)} />
      </Modal>

      <Modal
        isOpen={showLanguageModal}
        onClose={() => setShowLanguageModal(false)}
        title={t('language.title')}
      >
        <LanguageModal onClose={() => setShowLanguageModal(false)} />
      </Modal>

      <Modal
        isOpen={showContactModal}
        onClose={() => setShowContactModal(false)}
        title={t('contact.title')}
      >
        <ContactModal onClose={() => setShowContactModal(false)} />
      </Modal>
    </>
  )
}

// ==================== COMPOSANT PRINCIPAL AVEC TOUTES LES FONCTIONNALITÉS ====================
export default function ChatInterface() {
  const { user, isAuthenticated, isLoading } = useAuthStore()
  const { t, currentLanguage } = useTranslation()
  
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    if (isAuthenticated) {
      const welcomeMessage: Message = {
        id: '1',
        content: t('chat.welcome'),
        isUser: false,
        timestamp: new Date()
      }
      
      if (messages.length === 0) {
        setMessages([welcomeMessage])
      } else {
        // Mise à jour dynamique du message de bienvenue lors du changement de langue
        setMessages(prev => prev.map((msg, index) => 
          index === 0 && !msg.isUser && msg.id === '1' 
            ? { ...msg, content: t('chat.welcome') }
            : msg
        ))
      }
    }
  }, [isAuthenticated, t, currentLanguage])

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
    window.location.href = '/'
    return null
  }

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

    try {
      const response = await generateAIResponse(text.trim(), user)
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.response,
        isUser: false,
        timestamp: new Date(),
        conversation_id: response.conversation_id
      }

      setMessages(prev => [...prev, aiMessage])
      console.log('✅ Message ajouté avec conversation_id:', response.conversation_id)
      
    } catch (error) {
      console.error('❌ Error generating response:', error)
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

  const handleFeedback = async (messageId: string, feedback: 'positive' | 'negative') => {
    const message = messages.find(msg => msg.id === messageId)
    
    if (!message || !message.conversation_id) {
      console.warn('⚠️ Conversation ID non trouvé pour le feedback', messageId)
      alert('Impossible d\'enregistrer le feedback - ID de conversation manquant')
      return
    }

    try {
      console.log('📊 Envoi feedback pour conversation:', message.conversation_id, feedback)
      
      // Mise à jour optimiste de l'UI
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, feedback } : msg
      ))

      const feedbackValue = feedback === 'positive' ? 1 : -1
      await conversationService.sendFeedback(message.conversation_id, feedbackValue)
      
      console.log(`✅ Feedback ${feedback} enregistré avec succès pour conversation ${message.conversation_id}`)
      
    } catch (error) {
      console.error('❌ Erreur envoi feedback:', error)
      
      // Annulation en cas d'erreur
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, feedback: null } : msg
      ))
      
      alert('Erreur lors de l\'envoi du feedback. Veuillez réessayer.')
    }
  }

  const handleNewConversation = () => {
    setMessages([{
      id: '1',
      content: t('chat.welcome'),
      isUser: false,
      timestamp: new Date()
    }])
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
      <ZohoSalesIQ user={user} />

      <div className="h-screen bg-gray-50 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-100 px-4 py-3">
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

            {/* Titre centré avec logo */}
            <div className="flex-1 flex justify-center items-center space-x-3">
              <InteliaLogo className="w-8 h-8" />
              <div className="text-center">
                <h1 className="text-lg font-medium text-gray-900">Intelia Expert</h1>
              </div>
            </div>
            
            {/* Avatar utilisateur à droite */}
            <div className="flex items-center">
              <UserMenuButton />
            </div>
          </div>
        </header>

        {/* Zone de messages */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto px-4 py-6">
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
                      
                      {/* Boutons de feedback avec conversation_id */}
                      {!message.isUser && index > 0 && message.conversation_id && (
                        <div className="flex items-center space-x-2 mt-2 ml-2">
                          <button
                            onClick={() => handleFeedback(message.id, 'positive')}
                            className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${message.feedback === 'positive' ? 'text-green-600 bg-green-50' : 'text-gray-400'}`}
                            title={t('chat.helpfulResponse')}
                            disabled={message.feedback !== null}
                          >
                            <ThumbUpIcon />
                          </button>
                          <button
                            onClick={() => handleFeedback(message.id, 'negative')}
                            className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${message.feedback === 'negative' ? 'text-red-600 bg-red-50' : 'text-gray-400'}`}
                            title={t('chat.notHelpfulResponse')}
                            disabled={message.feedback !== null}
                          >
                            <ThumbDownIcon />
                          </button>
                          {message.feedback && (
                            <span className="text-xs text-gray-500 ml-2">
                              Merci pour votre retour !
                            </span>
                          )}
                          {message.conversation_id && (
                            <span className="text-xs text-gray-400 ml-2" title={`ID: ${message.conversation_id}`}>
                              🔗
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

          {/* Zone de saisie */}
          <div className="px-4 py-4 bg-white border-t border-gray-100">
            <div className="max-w-4xl mx-auto">
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                  title={t('chat.voiceRecording')}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                  </svg>
                </button>
                
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
    </>
  )
}