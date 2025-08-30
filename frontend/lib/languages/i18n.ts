// ==================== SYSTÈME DE TRADUCTION INTELIA EXPERT ====================

import { useState, useEffect } from 'react'
import { getSupabaseClient } from '@/lib/supabase/singleton'
import { availableLanguages, DEFAULT_LANGUAGE, getLanguageByCode, isValidLanguageCode, detectBrowserLanguage } from './config'

const supabase = getSupabaseClient()

// Types pour le système de traduction
export interface TranslationKeys {
  // Navigation et Interface
  'nav.history': string
  'nav.newConversation': string
  'nav.profile': string
  'nav.language': string
  'nav.subscription': string
  'nav.contact': string
  'nav.legal': string
  'nav.logout': string
  'nav.clearAll': string
  'nav.inviteFriend': string
  'nav.account': string
  'nav.settings': string

  // Authentication
  'auth.success': string
  'auth.error': string
  'auth.incomplete': string

  // GDPR et Legal
  'gdpr.notice': string
  'legal.terms': string
  'legal.privacy': string

  // Login form
  'login.email': string
  'login.password': string

  // Messages de Chat
  'chat.welcome': string
  'chat.placeholder': string
  'chat.helpfulResponse': string
  'chat.notHelpfulResponse': string
  'chat.voiceRecording': string
  'chat.noConversations': string
  'chat.loading': string
  'chat.errorMessage': string
  'chat.newConversation': string
  'chat.disclaimer': string
  'chat.send': string
  'chat.askQuestion': string

  // Page titles
  'page.title': string

  // Modals
  'modal.close': string
  'modal.cancel': string
  'modal.save': string
  'modal.back': string
  'modal.loading': string
  'modal.updating': string

  // Profil
  'profile.title': string
  'profile.personalInfo': string
  'profile.professionalInfo': string
  'profile.contact': string
  'profile.company': string
  'profile.password': string
  'profile.firstName': string
  'profile.lastName': string
  'profile.linkedinProfile': string
  'profile.linkedinCorporate': string
  'profile.email': string
  'profile.phone': string
  'profile.country': string
  'profile.companyName': string
  'profile.companyWebsite': string
  'profile.companyLinkedin': string
  'profile.currentPassword': string
  'profile.newPassword': string
  'profile.confirmPassword': string
  'profile.passwordRequirements': string
  'profile.passwordRequirements8': string
  'profile.passwordRequirementsUpper': string
  'profile.passwordRequirementsLower': string
  'profile.passwordRequirementsNumber': string
  'profile.passwordRequirementsSpecial': string
  'profile.passwordErrors': string
  'profile.passwordChanged': string
  'profile.profileUpdated': string
  'profile.optional': string

  // Langue
  'language.title': string
  'language.description': string
  'language.updating': string
  'language.changeSuccess': string
  'language.interfaceUpdated': string
  'language.reloadForWidget': string
  'language.reloadNow': string
  'language.continueWithoutReload': string

  // Abonnement
  'subscription.title': string
  'subscription.currentPlan': string
  'subscription.modify': string
  'subscription.payment': string
  'subscription.update': string
  'subscription.invoices': string
  'subscription.cancellation': string
  'subscription.cancel': string
  'subscription.confirmCancel': string

  // Contact
  'contact.title': string
  'contact.phone': string
  'contact.phoneDescription': string
  'contact.email': string
  'contact.emailDescription': string
  'contact.website': string
  'contact.websiteDescription': string
  'contact.subject': string
  'contact.message': string
  'contact.sendMessage': string
  'contact.messageSent': string

  // Dates et Formats
  'date.today': string
  'date.format': string

  // Plans
  'plan.essential': string
  'plan.pro': string
  'plan.max': string

  // Messages d'erreur et succès
  'error.generic': string
  'error.connection': string
  'error.updateProfile': string
  'error.changePassword': string
  'error.firstNameRequired': string
  'error.lastNameRequired': string
  'error.emailRequired': string
  'error.emailInvalid': string
  'error.emailTooLong': string
  'error.firstNameTooLong': string
  'error.lastNameTooLong': string
  'error.companyNameTooLong': string
  'error.urlInvalid': string
  'error.urlProtocol': string
  'error.linkedinInvalid': string
  'error.phonePrefix': string
  'error.currentPasswordRequired': string
  'error.newPasswordRequired': string
  'error.confirmPasswordRequired': string
  'error.currentPasswordIncorrect': string
  'error.passwordServerError': string
  'error.userNotConnected': string
  'error.validationErrors': string
  'success.profileUpdated': string
  'success.passwordChanged': string
  'success.languageUpdated': string

  // Formulaires
  'form.required': string
  'form.phoneFormat': string
  'form.passwordMinLength': string
  'form.passwordUppercase': string
  'form.passwordLowercase': string
  'form.passwordNumber': string
  'form.passwordSpecial': string
  'form.passwordMismatch': string

  // Commun
  'common.optional': string
  'common.unexpectedError': string
  'common.loading': string
  'common.saving': string
  'common.success': string
  'common.error': string
  'common.confirm': string
  'common.delete': string
  'common.edit': string
  'common.view': string
  'common.search': string
  'common.filter': string
  'common.clear': string
  'common.reset': string
  'common.apply': string
  'common.update': string

  // Interface utilisateur
  'ui.menu': string
  'ui.close': string
  'ui.open': string
  'ui.expand': string
  'ui.collapse': string
  'ui.previous': string
  'ui.next': string

  // Modales et dialogues
  'dialog.confirm': string
  'dialog.cancel': string
  'dialog.ok': string
  'dialog.yes': string
  'dialog.no': string

  // Messages d'état
  'status.online': string
  'status.offline': string
  'status.connecting': string
  'status.connected': string
  'status.disconnected': string

  // Invitations
  'invite.emailPlaceholder': string
  'invite.namePlaceholder': string
  'invite.messagePlaceholder': string
  'invite.sendButton': string
  'invite.sentSuccess': string
  'invite.error': string
  'invite.invalidEmail': string

  // Compte
  'account.settings': string
  'account.preferences': string
  'account.security': string
  'account.privacy': string
  'account.notifications': string

  // Historique
  'history.clear': string
  'history.delete': string
  'history.export': string
  'history.search': string
  'history.filter': string
  'history.noResults': string
  'history.confirmClear': string

  // Menu utilisateur
  'user.menu': string
  'user.profile': string
  'user.settings': string
  'user.logout': string
  'user.account': string

  // Placeholders
  'placeholder.linkedinPersonal': string
  'placeholder.companyName': string
  'placeholder.companyWebsite': string
  'placeholder.linkedinCorporate': string
  'placeholder.countrySelect': string
  'placeholder.currentPassword': string
  'placeholder.newPassword': string
  'placeholder.confirmPassword': string

  // RGPD et Confidentialité
  'gdpr.deleteAccount': string
  'gdpr.exportData': string
  'gdpr.confirmDelete': string
  'gdpr.contactSupport': string

  // Pays
  'country.canada': string
  'country.usa': string
  'country.france': string
  'country.belgium': string
  'country.switzerland': string
  'country.mexico': string
  'country.brazil': string
}

// ✅ SYSTÈME DE NOTIFICATION POUR FORCER LES RE-RENDERS
class I18nNotificationManager {
  private static instance: I18nNotificationManager
  private subscribers: Array<() => void> = []

  static getInstance(): I18nNotificationManager {
    if (!I18nNotificationManager.instance) {
      I18nNotificationManager.instance = new I18nNotificationManager()
    }
    return I18nNotificationManager.instance
  }

  subscribe(callback: () => void): () => void {
    this.subscribers.push(callback)
    return () => {
      this.subscribers = this.subscribers.filter(cb => cb !== callback)
    }
  }

  notify(): void {
    this.subscribers.forEach(callback => {
      try {
        callback()
      } catch (error) {
        console.error('Erreur notification i18n:', error)
      }
    })
  }
}

const notificationManager = I18nNotificationManager.getInstance()

// Cache pour les traductions chargées
const translationsCache: Record<string, TranslationKeys> = {}

// Variables globales pour la synchronisation
let globalTranslations: TranslationKeys = {} as TranslationKeys
let globalLoading = true
let globalLanguage = 'fr'

// ✅ EXPOSER LES VARIABLES POUR LE DEBUG
if (typeof window !== 'undefined') {
  (window as any).i18nDebug = {
    getGlobalTranslations: () => globalTranslations,
    getGlobalLoading: () => globalLoading,
    getGlobalLanguage: () => globalLanguage,
    getTranslationsCache: () => translationsCache,
    notificationManager
  }
}

// Fonction pour récupérer la langue depuis le store Zustand
const getStoredLanguage = (): string => {
  try {
    const storedLang = localStorage.getItem('intelia-language')
    if (storedLang) {
      const parsed = JSON.parse(storedLang)
      return parsed?.state?.currentLanguage || DEFAULT_LANGUAGE
    }
  } catch (error) {
    console.warn('Erreur lecture langue stockée:', error)
  }
  return DEFAULT_LANGUAGE
}

// Fonction pour charger les traductions depuis les fichiers JSON
async function loadTranslations(language: string): Promise<TranslationKeys> {
  if (translationsCache[language]) {
    globalTranslations = translationsCache[language]
    globalLoading = false
    globalLanguage = language
    
    // ✅ NOTIFIER TOUS LES COMPOSANTS
    notificationManager.notify()
    
    return translationsCache[language]
  }

  try {
    const response = await fetch(`/locales/${language}.json`)
    if (!response.ok) {
      throw new Error(`Failed to load translations for ${language}`)
    }
    
    const translations = await response.json()
    translationsCache[language] = translations
    globalTranslations = translations
    globalLoading = false
    globalLanguage = language
    
    // ✅ NOTIFIER TOUS LES COMPOSANTS
    notificationManager.notify()
    
    return translations
  } catch (error) {
    console.warn(`Could not load translations for ${language}, falling back to French`)
    
    // Fallback vers le français
    if (language !== 'fr') {
      return loadTranslations('fr')
    }
    
    // Si même le français échoue, retourner des clés vides
    return {} as TranslationKeys
  }
}

// Hook de traduction
export const useTranslation = () => {
  const [currentLanguage, setCurrentLanguage] = useState<string>('fr')
  const [translations, setTranslations] = useState<TranslationKeys>({} as TranslationKeys)
  const [loading, setLoading] = useState(true)
  const [, forceRender] = useState({}) // ✅ Pour forcer les re-renders

  // ✅ S'ABONNER AUX NOTIFICATIONS
  useEffect(() => {
    const unsubscribe = notificationManager.subscribe(() => {
      console.log('🔄 [i18n] Force re-render suite à notification globale')
      forceRender({}) // Force un re-render
    })

    return unsubscribe
  }, [])

  // Initialiser avec la langue de l'utilisateur ou celle du navigateur
  useEffect(() => {
    const getUserLanguage = async () => {
      try {
        // D'abord vérifier le localStorage Zustand
        const storedLang = getStoredLanguage()
        if (storedLang !== DEFAULT_LANGUAGE && isValidLanguageCode(storedLang)) {
          setCurrentLanguage(storedLang)
          return
        }

        // Puis vérifier Supabase
        const { data: { session } } = await supabase.auth.getSession()
        const userLang = session?.user?.user_metadata?.language
        
        if (userLang && isValidLanguageCode(userLang)) {
          setCurrentLanguage(userLang)
        } else {
          // Utiliser la langue du navigateur comme fallback
          const browserLang = detectBrowserLanguage()
          setCurrentLanguage(browserLang)
        }
      } catch (error) {
        console.log('Utilisation de la langue par défaut ou du navigateur')
        const browserLang = detectBrowserLanguage()
        setCurrentLanguage(browserLang)
      }
    }
    getUserLanguage()
  }, [])

  // Charger les traductions quand la langue change
  useEffect(() => {
    const loadLanguage = async () => {
      console.log('🚀 [i18n] Début chargement langue:', currentLanguage);
      setLoading(true)
      try {
        const loadedTranslations = await loadTranslations(currentLanguage)
        console.log('✅ [i18n] Traductions chargées:', Object.keys(loadedTranslations).length, 'clés');
        
        // IMPORTANT: Mettre à jour les translations AVANT de mettre loading à false
        setTranslations(loadedTranslations)
        setLoading(false)
        
      } catch (error) {
        console.error('❌ [i18n] Erreur chargement traductions:', error)
        setLoading(false)
      }
    }

    loadLanguage()
  }, [currentLanguage])

  // Écouter les changements de langue
  useEffect(() => {
    const handleLanguageChange = (event: CustomEvent) => {
      setCurrentLanguage(event.detail.language)
    }

    window.addEventListener('languageChanged', handleLanguageChange as EventListener)
    
    return () => {
      window.removeEventListener('languageChanged', handleLanguageChange as EventListener)
    }
  }, [])

  const t = (key: keyof TranslationKeys): string => {
    // ✅ LOGIQUE SIMPLIFIÉE : priorité aux translations locales, puis globales
    const finalTranslations = Object.keys(translations).length > 0 ? translations : globalTranslations
    const isStillLoading = loading && globalLoading
    
    // 🔍 LOGS DE DEBUG DÉTAILLÉS POUR IDENTIFIER LE PROBLÈME
    console.log('Translation debug DÉTAILLÉ:', JSON.stringify({ 
      key, 
      loading: isStillLoading,
      translationsKeys: Object.keys(finalTranslations).slice(0, 20), // Premier 20 clés seulement
      translationsLength: Object.keys(finalTranslations).length,
      translationValue: finalTranslations[key],
      currentLanguage,
      usingGlobal: Object.keys(translations).length === 0,
      hasKey: finalTranslations.hasOwnProperty(key)
    }, null, 2));
    
    if (isStillLoading || !finalTranslations[key]) {
      return key
    }
    
    return finalTranslations[key]
  }

  const changeLanguage = async (newLanguage: string) => {
    setCurrentLanguage(newLanguage)
    
    // Précharger les traductions
    await loadTranslations(newLanguage)
    
    // Émettre l'événement pour mettre à jour d'autres composants
    window.dispatchEvent(new CustomEvent('languageChanged', { 
      detail: { language: newLanguage } 
    }))
  }

  const getCurrentLanguage = () => currentLanguage

  const formatDate = (date: Date) => {
    const langConfig = getLanguageByCode(currentLanguage)
    const locale = langConfig?.dateFormat || 'fr-FR'
    return date.toLocaleDateString(locale, { 
      day: 'numeric', 
      month: 'long', 
      year: 'numeric' 
    })
  }

  return {
    t,
    changeLanguage,
    getCurrentLanguage,
    formatDate,
    currentLanguage,
    loading
  }
}

// Fonction utilitaire pour obtenir les langues disponibles (compatibilité)
export const getAvailableLanguages = () => availableLanguages.map(lang => ({
  code: lang.code,
  name: lang.nativeName,
  region: lang.region
}))

// Export de la configuration complète pour les composants
export { availableLanguages, DEFAULT_LANGUAGE, getLanguageByCode } from './config'