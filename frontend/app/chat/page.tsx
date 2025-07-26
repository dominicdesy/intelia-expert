'use client'

// Forcer l'utilisation du runtime Node.js au lieu d'Edge Runtime
export const runtime = 'nodejs'

import React, { useState, useEffect, useRef } from 'react'
import Script from 'next/script'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

// Instance Supabase
const supabase = createClientComponentClient()

// ==================== SYSTÈME DE TRADUCTION INTELIA EXPERT ====================

// Types pour le système de traduction
interface TranslationKeys {
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
  'profile.contact': string
  'profile.company': string
  'profile.password': string
  'profile.firstName': string
  'profile.lastName': string
  'profile.linkedinProfile': string
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
  'profile.passwordErrors': string
  'profile.passwordChanged': string
  'profile.profileUpdated': string

  // Langue
  'language.title': string
  'language.description': string
  'language.updating': string

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

// Traductions complètes
const translations: Record<string, TranslationKeys> = {
  fr: {
    // Navigation et Interface
    'nav.history': 'Historique des conversations',
    'nav.newConversation': 'Nouvelle conversation',
    'nav.profile': 'Profil',
    'nav.language': 'Langue',
    'nav.subscription': 'Abonnement',
    'nav.contact': 'Nous joindre',
    'nav.legal': 'Mentions légales',
    'nav.logout': 'Déconnexion',
    'nav.clearAll': 'Tout effacer',

    // Messages de Chat
    'chat.welcome': 'Bonjour ! Comment puis-je vous aider aujourd\'hui ?',
    'chat.placeholder': 'Bonjour ! Comment puis-je vous aider aujourd\'hui ?',
    'chat.helpfulResponse': 'Réponse utile',
    'chat.notHelpfulResponse': 'Réponse non utile',
    'chat.voiceRecording': 'Enregistrement vocal',
    'chat.noConversations': 'Aucune conversation précédente',
    'chat.loading': 'Chargement...',
    'chat.errorMessage': 'Désolé, je rencontre un problème technique. Veuillez réessayer dans quelques instants.',
    'chat.newConversation': 'Nouvelle conversation',

    // Modals
    'modal.close': 'Fermer',
    'modal.cancel': 'Annuler',
    'modal.save': 'Sauvegarder',
    'modal.back': 'Retour',
    'modal.loading': 'Sauvegarde...',
    'modal.updating': 'Mise à jour en cours...',

    // Profil
    'profile.title': 'Profil',
    'profile.personalInfo': 'Informations personnelles',
    'profile.contact': 'Contact',
    'profile.company': 'Entreprise',
    'profile.password': 'Mot de passe',
    'profile.firstName': 'Prénom *',
    'profile.lastName': 'Nom de famille *',
    'profile.linkedinProfile': 'Profil LinkedIn personnel',
    'profile.email': 'Email *',
    'profile.phone': 'Téléphone',
    'profile.country': 'Pays *',
    'profile.companyName': 'Nom de l\'entreprise',
    'profile.companyWebsite': 'Site web de l\'entreprise',
    'profile.companyLinkedin': 'Page LinkedIn de l\'entreprise',
    'profile.currentPassword': 'Mot de passe actuel *',
    'profile.newPassword': 'Nouveau mot de passe *',
    'profile.confirmPassword': 'Confirmer le nouveau mot de passe *',
    'profile.passwordRequirements': 'Le mot de passe doit contenir :',
    'profile.passwordErrors': 'Erreurs :',
    'profile.passwordChanged': 'Mot de passe changé avec succès !',
    'profile.profileUpdated': 'Profil mis à jour avec succès !',

    // Langue
    'language.title': 'Langue',
    'language.description': 'Sélectionnez votre langue préférée pour l\'interface Intelia Expert',
    'language.updating': 'Mise à jour en cours...',

    // Abonnement
    'subscription.title': 'Abonnement',
    'subscription.currentPlan': 'Plan',
    'subscription.modify': 'Modifier l\'abonnement',
    'subscription.payment': 'Paiement',
    'subscription.update': 'Mettre à jour',
    'subscription.invoices': 'Factures',
    'subscription.cancellation': 'Annulation',
    'subscription.cancel': 'Annuler',
    'subscription.confirmCancel': 'Êtes-vous sûr de vouloir annuler votre abonnement ? Vous perdrez l\'accès aux fonctionnalités premium.',

    // Contact
    'contact.title': 'Nous joindre',
    'contact.phone': 'Nous appeler',
    'contact.phoneDescription': 'Si vous ne trouvez pas de solution, appelez-nous pour parler directement avec notre équipe.',
    'contact.email': 'Nous écrire',
    'contact.emailDescription': 'Envoyez-nous un message détaillé et nous vous répondrons rapidement.',
    'contact.website': 'Visiter notre site web',
    'contact.websiteDescription': 'Pour en savoir plus sur nous et la plateforme Intelia, visitez notre site.',

    // Dates et Formats
    'date.today': 'Aujourd\'hui',
    'date.format': 'fr-FR',

    // Plans
    'plan.essential': 'Essentiel',
    'plan.pro': 'Pro',
    'plan.max': 'Max',

    // Messages d'erreur et succès
    'error.generic': 'Une erreur est survenue',
    'error.connection': 'Erreur de connexion',
    'error.updateProfile': 'Erreur lors de la mise à jour du profil',
    'error.changePassword': 'Erreur lors du changement de mot de passe',
    'success.profileUpdated': 'Profil mis à jour avec succès !',
    'success.passwordChanged': 'Mot de passe changé avec succès !',
    'success.languageUpdated': 'Langue mise à jour',

    // Formulaires
    'form.required': 'Champ requis',
    'form.phoneFormat': 'Format',
    'form.passwordMinLength': 'Au moins 8 caractères',
    'form.passwordUppercase': 'Au moins une majuscule',
    'form.passwordLowercase': 'Au moins une minuscule',
    'form.passwordNumber': 'Au moins un chiffre',
    'form.passwordSpecial': 'Au moins un caractère spécial',
    'form.passwordMismatch': 'Les mots de passe ne correspondent pas',

    // RGPD et Confidentialité
    'gdpr.deleteAccount': 'Supprimer mon compte',
    'gdpr.exportData': 'Exporter mes données',
    'gdpr.confirmDelete': 'Êtes-vous sûr de vouloir supprimer définitivement votre compte ? Cette action est irréversible.',
    'gdpr.contactSupport': 'Pour supprimer définitivement votre compte, veuillez contacter support@intelia.com',

    // Pays
    'country.canada': 'Canada',
    'country.usa': 'États-Unis',
    'country.france': 'France',
    'country.belgium': 'Belgique',
    'country.switzerland': 'Suisse',
    'country.mexico': 'Mexique',
    'country.brazil': 'Brésil'
  },

  en: {
    // Navigation et Interface
    'nav.history': 'Conversation history',
    'nav.newConversation': 'New conversation',
    'nav.profile': 'Profile',
    'nav.language': 'Language',
    'nav.subscription': 'Subscription',
    'nav.contact': 'Contact us',
    'nav.legal': 'Legal',
    'nav.logout': 'Logout',
    'nav.clearAll': 'Clear all',

    // Messages de Chat
    'chat.welcome': 'Hello! How can I help you today?',
    'chat.placeholder': 'Hello! How can I help you today?',
    'chat.helpfulResponse': 'Helpful response',
    'chat.notHelpfulResponse': 'Not helpful response',
    'chat.voiceRecording': 'Voice recording',
    'chat.noConversations': 'No previous conversations',
    'chat.loading': 'Loading...',
    'chat.errorMessage': 'Sorry, I\'m experiencing a technical issue. Please try again in a few moments.',
    'chat.newConversation': 'New conversation',

    // Modals
    'modal.close': 'Close',
    'modal.cancel': 'Cancel',
    'modal.save': 'Save',
    'modal.back': 'Back',
    'modal.loading': 'Saving...',
    'modal.updating': 'Updating...',

    // Profil
    'profile.title': 'Profile',
    'profile.personalInfo': 'Personal information',
    'profile.contact': 'Contact',
    'profile.company': 'Company',
    'profile.password': 'Password',
    'profile.firstName': 'First name *',
    'profile.lastName': 'Last name *',
    'profile.linkedinProfile': 'Personal LinkedIn profile',
    'profile.email': 'Email *',
    'profile.phone': 'Phone',
    'profile.country': 'Country *',
    'profile.companyName': 'Company name',
    'profile.companyWebsite': 'Company website',
    'profile.companyLinkedin': 'Company LinkedIn page',
    'profile.currentPassword': 'Current password *',
    'profile.newPassword': 'New password *',
    'profile.confirmPassword': 'Confirm new password *',
    'profile.passwordRequirements': 'Password must contain:',
    'profile.passwordErrors': 'Errors:',
    'profile.passwordChanged': 'Password changed successfully!',
    'profile.profileUpdated': 'Profile updated successfully!',

    // Langue
    'language.title': 'Language',
    'language.description': 'Select your preferred language for the Intelia Expert interface',
    'language.updating': 'Updating...',

    // Abonnement
    'subscription.title': 'Subscription',
    'subscription.currentPlan': 'Plan',
    'subscription.modify': 'Modify subscription',
    'subscription.payment': 'Payment',
    'subscription.update': 'Update',
    'subscription.invoices': 'Invoices',
    'subscription.cancellation': 'Cancellation',
    'subscription.cancel': 'Cancel',
    'subscription.confirmCancel': 'Are you sure you want to cancel your subscription? You will lose access to premium features.',

    // Contact
    'contact.title': 'Contact us',
    'contact.phone': 'Call us',
    'contact.phoneDescription': 'If you can\'t find a solution, call us to speak directly with our team.',
    'contact.email': 'Email us',
    'contact.emailDescription': 'Send us a detailed message and we\'ll respond quickly.',
    'contact.website': 'Visit our website',
    'contact.websiteDescription': 'To learn more about us and the Intelia platform, visit our site.',

    // Dates et Formats
    'date.today': 'Today',
    'date.format': 'en-US',

    // Plans
    'plan.essential': 'Essential',
    'plan.pro': 'Pro',
    'plan.max': 'Max',

    // Messages d'erreur et succès
    'error.generic': 'An error occurred',
    'error.connection': 'Connection error',
    'error.updateProfile': 'Error updating profile',
    'error.changePassword': 'Error changing password',
    'success.profileUpdated': 'Profile updated successfully!',
    'success.passwordChanged': 'Password changed successfully!',
    'success.languageUpdated': 'Language updated',

    // Formulaires
    'form.required': 'Required field',
    'form.phoneFormat': 'Format',
    'form.passwordMinLength': 'At least 8 characters',
    'form.passwordUppercase': 'At least one uppercase',
    'form.passwordLowercase': 'At least one lowercase',
    'form.passwordNumber': 'At least one number',
    'form.passwordSpecial': 'At least one special character',
    'form.passwordMismatch': 'Passwords do not match',

    // RGPD et Confidentialité
    'gdpr.deleteAccount': 'Delete my account',
    'gdpr.exportData': 'Export my data',
    'gdpr.confirmDelete': 'Are you sure you want to permanently delete your account? This action is irreversible.',
    'gdpr.contactSupport': 'To permanently delete your account, please contact support@intelia.com',

    // Pays
    'country.canada': 'Canada',
    'country.usa': 'United States',
    'country.france': 'France',
    'country.belgium': 'Belgium',
    'country.switzerland': 'Switzerland',
    'country.mexico': 'Mexico',
    'country.brazil': 'Brazil'
  },

  es: {
    // Navigation et Interface
    'nav.history': 'Historial de conversaciones',
    'nav.newConversation': 'Nueva conversación',
    'nav.profile': 'Perfil',
    'nav.language': 'Idioma',
    'nav.subscription': 'Suscripción',
    'nav.contact': 'Contáctanos',
    'nav.legal': 'Legal',
    'nav.logout': 'Cerrar sesión',
    'nav.clearAll': 'Borrar todo',

    // Messages de Chat
    'chat.welcome': '¡Hola! ¿Cómo puedo ayudarte hoy?',
    'chat.placeholder': '¡Hola! ¿Cómo puedo ayudarte hoy?',
    'chat.helpfulResponse': 'Respuesta útil',
    'chat.notHelpfulResponse': 'Respuesta no útil',
    'chat.voiceRecording': 'Grabación de voz',
    'chat.noConversations': 'No hay conversaciones anteriores',
    'chat.loading': 'Cargando...',
    'chat.errorMessage': 'Lo siento, tengo un problema técnico. Por favor, inténtalo de nuevo en unos momentos.',
    'chat.newConversation': 'Nueva conversación',

    // Modals
    'modal.close': 'Cerrar',
    'modal.cancel': 'Cancelar',
    'modal.save': 'Guardar',
    'modal.back': 'Volver',
    'modal.loading': 'Guardando...',
    'modal.updating': 'Actualizando...',

    // Profil
    'profile.title': 'Perfil',
    'profile.personalInfo': 'Información personal',
    'profile.contact': 'Contacto',
    'profile.company': 'Empresa',
    'profile.password': 'Contraseña',
    'profile.firstName': 'Nombre *',
    'profile.lastName': 'Apellido *',
    'profile.linkedinProfile': 'Perfil personal de LinkedIn',
    'profile.email': 'Email *',
    'profile.phone': 'Teléfono',
    'profile.country': 'País *',
    'profile.companyName': 'Nombre de la empresa',
    'profile.companyWebsite': 'Sitio web de la empresa',
    'profile.companyLinkedin': 'Página de LinkedIn de la empresa',
    'profile.currentPassword': 'Contraseña actual *',
    'profile.newPassword': 'Nueva contraseña *',
    'profile.confirmPassword': 'Confirmar nueva contraseña *',
    'profile.passwordRequirements': 'La contraseña debe contener:',
    'profile.passwordErrors': 'Errores:',
    'profile.passwordChanged': '¡Contraseña cambiada con éxito!',
    'profile.profileUpdated': '¡Perfil actualizado con éxito!',

    // Langue
    'language.title': 'Idioma',
    'language.description': 'Selecciona tu idioma preferido para la interfaz de Intelia Expert',
    'language.updating': 'Actualizando...',

    // Abonnement
    'subscription.title': 'Suscripción',
    'subscription.currentPlan': 'Plan',
    'subscription.modify': 'Modificar suscripción',
    'subscription.payment': 'Pago',
    'subscription.update': 'Actualizar',
    'subscription.invoices': 'Facturas',
    'subscription.cancellation': 'Cancelación',
    'subscription.cancel': 'Cancelar',
    'subscription.confirmCancel': '¿Estás seguro de que quieres cancelar tu suscripción? Perderás el acceso a las funciones premium.',

    // Contact
    'contact.title': 'Contáctanos',
    'contact.phone': 'Llámanos',
    'contact.phoneDescription': 'Si no encuentras una solución, llámanos para hablar directamente con nuestro equipo.',
    'contact.email': 'Escríbenos',
    'contact.emailDescription': 'Envíanos un mensaje detallado y te responderemos rápidamente.',
    'contact.website': 'Visita nuestro sitio web',
    'contact.websiteDescription': 'Para saber más sobre nosotros y la plataforma Intelia, visita nuestro sitio.',

    // Dates et Formats
    'date.today': 'Hoy',
    'date.format': 'es-ES',

    // Plans
    'plan.essential': 'Esencial',
    'plan.pro': 'Pro',
    'plan.max': 'Máximo',

    // Messages d'erreur et succès
    'error.generic': 'Ocurrió un error',
    'error.connection': 'Error de conexión',
    'error.updateProfile': 'Error al actualizar el perfil',
    'error.changePassword': 'Error al cambiar la contraseña',
    'success.profileUpdated': '¡Perfil actualizado con éxito!',
    'success.passwordChanged': '¡Contraseña cambiada con éxito!',
    'success.languageUpdated': 'Idioma actualizado',

    // Formulaires
    'form.required': 'Campo requerido',
    'form.phoneFormat': 'Formato',
    'form.passwordMinLength': 'Al menos 8 caracteres',
    'form.passwordUppercase': 'Al menos una mayúscula',
    'form.passwordLowercase': 'Al menos una minúscula',
    'form.passwordNumber': 'Al menos un número',
    'form.passwordSpecial': 'Al menos un carácter especial',
    'form.passwordMismatch': 'Las contraseñas no coinciden',

    // RGPD et Confidentialité
    'gdpr.deleteAccount': 'Eliminar mi cuenta',
    'gdpr.exportData': 'Exportar mis datos',
    'gdpr.confirmDelete': '¿Estás seguro de que quieres eliminar permanentemente tu cuenta? Esta acción es irreversible.',
    'gdpr.contactSupport': 'Para eliminar permanentemente tu cuenta, por favor contacta support@intelia.com',

    // Pays
    'country.canada': 'Canadá',
    'country.usa': 'Estados Unidos',
    'country.france': 'Francia',
    'country.belgium': 'Bélgica',
    'country.switzerland': 'Suiza',
    'country.mexico': 'México',
    'country.brazil': 'Brasil'
  }
}

// Hook de traduction
export const useTranslation = () => {
  const [currentLanguage, setCurrentLanguage] = useState<string>('fr')

  // Initialiser avec la langue de l'utilisateur
  useEffect(() => {
    const getUserLanguage = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        if (session?.user?.user_metadata?.language) {
          setCurrentLanguage(session.user.user_metadata.language)
        }
      } catch (error) {
        console.log('Utilisation de la langue par défaut (fr)')
      }
    }
    getUserLanguage()
  }, [])

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
    return translations[currentLanguage]?.[key] || translations['fr'][key] || key
  }

  const changeLanguage = (newLanguage: string) => {
    setCurrentLanguage(newLanguage)
    // Émettre l'événement pour mettre à jour d'autres composants
    window.dispatchEvent(new CustomEvent('languageChanged', { 
      detail: { language: newLanguage } 
    }))
  }

  const getCurrentLanguage = () => currentLanguage

  const formatDate = (date: Date) => {
    const locale = t('date.format')
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
    currentLanguage
  }
}

// Fonction utilitaire pour obtenir les langues disponibles
export const getAvailableLanguages = () => [
  { code: 'en', name: 'English', region: 'United States' },
  { code: 'fr', name: 'Français', region: 'France' },
  { code: 'es', name: 'Español', region: 'Latinoamérica' }
]

// ==================== COMPOSANT ZOHO SALESIQ SOLIDE ====================
const ZohoSalesIQ = ({ user }: { user: any }) => {
  useEffect(() => {
    if (!user) return

    console.log('🚀 Initialisation Zoho SalesIQ pour:', user.email)
    
    // 1. Configuration globale AVANT le chargement du script
    const initializeZohoConfig = () => {
      console.log('🔧 Configuration initiale Zoho SalesIQ')
      
      // Configuration globale requise par Zoho
      ;(window as any).$zoho = (window as any).$zoho || {}
      ;(window as any).$zoho.salesiq = (window as any).$zoho.salesiq || {}
      ;(window as any).$zoho.salesiq.widgetcode = 'siq657f7803e2e48661958a7ad1d48f293e50d5ba705ca11222b8cc9df0c8d01f09'
      
      // Fonction ready qui sera appelée automatiquement par Zoho
      ;(window as any).$zoho.salesiq.ready = function() {
        console.log('✅ Zoho SalesIQ initialisé avec succès')
        
        try {
          // Configuration utilisateur
          if ((window as any).$zoho.salesiq.visitor) {
            ;(window as any).$zoho.salesiq.visitor.info({
              name: user.name || 'Utilisateur',
              email: user.email || ''
            })
            console.log('👤 Informations utilisateur configurées:', { 
              name: user.name || 'Utilisateur', 
              email: user.email || '' 
            })
          }
          
          // Activation du chat
          if ((window as any).$zoho.salesiq.chat) {
            ;(window as any).$zoho.salesiq.chat.start()
            console.log('💬 Chat démarré')
          }
          
          // S'assurer que le widget est visible
          if ((window as any).$zoho.salesiq.floatbutton) {
            ;(window as any).$zoho.salesiq.floatbutton.visible('show')
            console.log('👀 Widget rendu visible')
          }
          
        } catch (error) {
          console.error('❌ Erreur configuration Zoho:', error)
        }
      }
    }

    // 2. Chargement du script de manière propre
    const loadZohoScript = () => {
      console.log('📡 Chargement script Zoho SalesIQ')
      
      // Supprimer les anciens scripts pour éviter les conflits
      const existingScripts = document.querySelectorAll('script[src*="salesiq.zohopublic.com"]')
      existingScripts.forEach(script => script.remove())
      
      // Créer et configurer le nouveau script
      const script = document.createElement('script')
      script.type = 'text/javascript'
      script.async = true
      script.defer = true
      script.src = `https://salesiq.zohopublic.com/widget?wc=${(window as any).$zoho.salesiq.widgetcode}`
      
      // Gestion succès/erreur
      script.onload = () => {
        console.log('✅ Script Zoho SalesIQ chargé avec succès')
        
        // Vérification que tout fonctionne
        setTimeout(() => {
          const zohoElements = document.querySelectorAll('[id*="siq"], [class*="siq"]')
          console.log(`🔍 ${zohoElements.length} éléments Zoho détectés dans le DOM`)
          
          if (zohoElements.length === 0) {
            console.warn('⚠️ Aucun élément widget visible, tentative de force')
            if ((window as any).$zoho?.salesiq?.ready) {
              ;(window as any).$zoho.salesiq.ready()
            }
          } else {
            console.log('✅ Widget Zoho opérationnel!')
          }
        }, 2000)
      }
      
      script.onerror = (error) => {
        console.error('❌ Erreur chargement script Zoho:', error)
        console.error('🔍 Vérifiez la CSP et la connectivité réseau')
      }
      
      // Ajouter au DOM
      document.head.appendChild(script)
    }

    // 3. Exécution séquentielle
    initializeZohoConfig()
    
    // Délai pour s'assurer que la config est prête
    setTimeout(() => {
      loadZohoScript()
    }, 100)

    // 4. Diagnostic périodique pour le debug
    const diagnosticInterval = setInterval(() => {
      const zohoElements = document.querySelectorAll('[id*="siq"], [class*="siq"]')
      
      if (zohoElements.length > 0) {
        console.log('✅ Widget Zoho actif et visible')
        clearInterval(diagnosticInterval)
      }
    }, 5000)

    // Nettoyage
    return () => {
      clearInterval(diagnosticInterval)
    }
  }, [user])

  return null // Ce composant n'a pas de rendu visuel
}

// ==================== STORE D'AUTHENTIFICATION ====================
const useAuthStore = () => {
  const [user, setUser] = useState<any>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const handleProfileUpdate = (event: CustomEvent) => {
      console.log('🔄 Mise à jour profil reçue:', event.detail)
      setUser(event.detail)
    }

    window.addEventListener('userProfileUpdated', handleProfileUpdate as EventListener)
    
    return () => {
      window.removeEventListener('userProfileUpdated', handleProfileUpdate as EventListener)
    }
  }, [])

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
          console.log('✅ Utilisateur connecté:', session.user)
          
          const userData = {
            id: session.user.id,
            email: session.user.email,
            name: `${session.user.user_metadata?.first_name || ''} ${session.user.user_metadata?.last_name || ''}`.trim() || session.user.email?.split('@')[0],
            
            firstName: session.user.user_metadata?.first_name || '',
            lastName: session.user.user_metadata?.last_name || '',
            linkedinProfile: session.user.user_metadata?.linkedin_profile || '',
            
            country: session.user.user_metadata?.country || 'CA',
            phone: session.user.user_metadata?.phone || '',
            
            companyName: session.user.user_metadata?.company_name || '',
            companyWebsite: session.user.user_metadata?.company_website || '',
            linkedinCorporate: session.user.user_metadata?.company_linkedin || '',
            
            user_type: session.user.user_metadata?.role || 'producer',
            language: session.user.user_metadata?.language || 'fr',
            created_at: session.user.created_at,
            consentGiven: true,
            consentDate: new Date(session.user.created_at)
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
      
      const updates = {
        data: {
          first_name: data.firstName,
          last_name: data.lastName,
          linkedin_profile: data.linkedinProfile,
          country: data.country,
          phone: data.phone,
          company_name: data.companyName,
          company_website: data.companyWebsite,
          company_linkedin: data.linkedinCorporate,
          language: data.language
        }
      }
      
      const { error } = await supabase.auth.updateUser(updates)
      
      if (error) {
        console.error('❌ Erreur mise à jour profil:', error)
        return { success: false, error: error.message }
      }
      
      const updatedUser = {
        ...user,
        ...data,
        name: `${data.firstName} ${data.lastName}`.trim()
      }
      
      setUser(updatedUser)
      console.log('✅ Profil mis à jour localement:', updatedUser)
      
      return { success: true }
    } catch (error: any) {
      console.error('❌ Erreur critique mise à jour:', error)
      return { success: false, error: error.message }
    }
  }

  const changePassword = async (currentPassword: string, newPassword: string) => {
    try {
      console.log('🔑 Changement mot de passe demandé')
      
      const { error } = await supabase.auth.updateUser({
        password: newPassword
      })
      
      if (error) {
        console.error('❌ Erreur changement mot de passe:', error)
        return { success: false, error: error.message }
      }
      
      return { success: true }
    } catch (error: any) {
      console.error('❌ Erreur critique changement mot de passe:', error)
      return { success: false, error: error.message }
    }
  }

  const exportUserData = async () => {
    try {
      console.log('📤 Export données utilisateur...')
      
      if (!user) {
        console.warn('⚠️ Aucun utilisateur à exporter')
        return
      }
      
      const exportData = {
        user_info: user,
        export_date: new Date().toISOString(),
        export_type: 'user_data_export'
      }
      
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json'
      })
      
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `intelia_export_${user.email}_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
      console.log('✅ Export réalisé avec succès')
    } catch (error) {
      console.error('❌ Erreur export données:', error)
    }
  }

  const deleteUserData = async () => {
    try {
      console.log('🗑️ Suppression données utilisateur...')
      
      if (!confirm('Êtes-vous sûr de vouloir supprimer définitivement votre compte ? Cette action est irréversible.')) {
        return
      }
      
      alert('Pour supprimer définitivement votre compte, veuillez contacter support@intelia.com')
      
    } catch (error) {
      console.error('❌ Erreur suppression données:', error)
    }
  }

  return {
    user,
    isAuthenticated,
    isLoading,
    logout,
    updateProfile,
    changePassword,
    exportUserData,
    deleteUserData
  }
}

// ==================== HOOK CHAT ====================
const useChatStore = () => ({
  conversations: [
    {
      id: '1',
      title: 'Problème poulets Ross 308',
      messages: [
        { id: '1', role: 'user', content: 'Mes poulets Ross 308 de 25 jours pèsent 800g, est-ce normal ?' },
        { id: '2', role: 'assistant', content: 'Selon notre base documentaire, pour les poulets Ross 308...' }
      ],
      updated_at: '2024-01-20',
      created_at: '2024-01-20'
    }
  ],
  currentConversation: null,
  loadConversations: () => {},
  loadConversation: async (id: string) => {},
  deleteConversation: async (id: string) => {
    console.log('Suppression conversation:', id)
  },
  clearAllConversations: async () => {
    console.log('Suppression toutes conversations')
  },
  createConversation: () => {}
})

// ==================== TYPES ====================
interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  feedback?: 'positive' | 'negative' | null
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
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div 
          className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto"
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

// ==================== MODAL PROFIL ====================
const UserInfoModal = ({ user, onClose }: { user: any, onClose: () => void }) => {
  const { updateProfile, changePassword } = useAuthStore()
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<'profile' | 'password'>('profile')
  const [isLoading, setIsLoading] = useState(false)
  
  const [formData, setFormData] = useState({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    linkedinProfile: user?.linkedinProfile || '',
    companyName: user?.companyName || '',
    companyWebsite: user?.companyWebsite || '',
    linkedinCorporate: user?.linkedinCorporate || '',
    email: user?.email || '',
    phone: user?.phone || '',
    country: user?.country || 'CA'
  })

  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })

  const [passwordErrors, setPasswordErrors] = useState<string[]>([])

  const countries = [
    { code: 'CA', name: t('country.canada'), format: '+1 (XXX) XXX-XXXX' },
    { code: 'US', name: t('country.usa'), format: '+1 (XXX) XXX-XXXX' },
    { code: 'FR', name: t('country.france'), format: '+33 X XX XX XX XX' },
    { code: 'BE', name: t('country.belgium'), format: '+32 XXX XX XX XX' },
    { code: 'CH', name: t('country.switzerland'), format: '+41 XX XXX XX XX' },
    { code: 'MX', name: t('country.mexico'), format: '+52 XXX XXX XXXX' },
    { code: 'BR', name: t('country.brazil'), format: '+55 (XX) XXXXX-XXXX' }
  ]

  const formatPhoneNumber = (phone: string, countryCode: string) => {
    const cleaned = phone.replace(/\D/g, '')
    
    switch (countryCode) {
      case 'CA':
      case 'US':
        if (cleaned.length >= 10) {
          return `+1 (${cleaned.slice(-10, -7)}) ${cleaned.slice(-7, -4)}-${cleaned.slice(-4)}`
        }
        break
      case 'FR':
        if (cleaned.length >= 9) {
          return `+33 ${cleaned.slice(-9, -8)} ${cleaned.slice(-8, -6)} ${cleaned.slice(-6, -4)} ${cleaned.slice(-4, -2)} ${cleaned.slice(-2)}`
        }
        break
      case 'BE':
        if (cleaned.length >= 8) {
          return `+32 ${cleaned.slice(-8, -5)} ${cleaned.slice(-5, -3)} ${cleaned.slice(-3, -1)} ${cleaned.slice(-1)}`
        }
        break
      case 'CH':
        if (cleaned.length >= 9) {
          return `+41 ${cleaned.slice(-9, -7)} ${cleaned.slice(-7, -4)} ${cleaned.slice(-4, -2)} ${cleaned.slice(-2)}`
        }
        break
      case 'MX':
        if (cleaned.length >= 10) {
          return `+52 ${cleaned.slice(-10, -7)} ${cleaned.slice(-7, -4)} ${cleaned.slice(-4)}`
        }
        break
      case 'BR':
        if (cleaned.length >= 10) {
          return `+55 (${cleaned.slice(-10, -8)}) ${cleaned.slice(-8, -3)}-${cleaned.slice(-3)}`
        }
        break
    }
    return phone
  }

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value, formData.country)
    setFormData(prev => ({ ...prev, phone: formatted }))
  }

  const handleCountryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newCountry = e.target.value
    setFormData(prev => ({ 
      ...prev, 
      country: newCountry,
      phone: formatPhoneNumber(prev.phone, newCountry)
    }))
  }

  const getCurrentCountryFormat = () => {
    return countries.find(c => c.code === formData.country)?.format || ''
  }

  const validatePassword = (password: string): string[] => {
    const errors: string[] = []
    if (password.length < 8) errors.push(t('form.passwordMinLength'))
    if (!/[A-Z]/.test(password)) errors.push(t('form.passwordUppercase'))
    if (!/[a-z]/.test(password)) errors.push(t('form.passwordLowercase'))
    if (!/[0-9]/.test(password)) errors.push(t('form.passwordNumber'))
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) errors.push(t('form.passwordSpecial'))
    return errors
  }

  const handlePasswordChange = async () => {
    const errors: string[] = []
    
    if (!passwordData.currentPassword) {
      errors.push(t('form.required'))
    }
    
    if (!passwordData.newPassword) {
      errors.push(t('form.required'))
    } else {
      const passwordValidationErrors = validatePassword(passwordData.newPassword)
      errors.push(...passwordValidationErrors)
    }
    
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      errors.push(t('form.passwordMismatch'))
    }

    setPasswordErrors(errors)

    if (errors.length === 0) {
      setIsLoading(true)
      try {
        const result = await changePassword(passwordData.currentPassword, passwordData.newPassword)
        if (result.success) {
          alert(t('success.passwordChanged'))
          setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' })
          setActiveTab('profile')
        } else {
          setPasswordErrors([t('error.changePassword')])
        }
      } catch (error) {
        setPasswordErrors([t('error.changePassword')])
      }
      setIsLoading(false)
    }
  }

  const handleProfileSave = async () => {
    setIsLoading(true)
    try {
      const result = await updateProfile(formData)
      if (result.success) {
        alert(t('success.profileUpdated'))
        
        const updatedName = `${formData.firstName} ${formData.lastName}`.trim()
        const updatedInitials = updatedName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
        
        document.querySelectorAll('[data-user-name]').forEach(el => {
          el.textContent = updatedName
        })
        document.querySelectorAll('[data-user-initials]').forEach(el => {
          el.textContent = updatedInitials
        })

        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (!error && session?.user) {
          console.log('🔄 Rechargement données utilisateur après mise à jour')
          
          const updatedUserData = {
            ...user,
            name: `${formData.firstName} ${formData.lastName}`.trim(),
            firstName: formData.firstName,
            lastName: formData.lastName,
            linkedinProfile: formData.linkedinProfile,
            country: formData.country,
            phone: formData.phone,
            companyName: formData.companyName,
            companyWebsite: formData.companyWebsite,
            linkedinCorporate: formData.linkedinCorporate,
            email: formData.email
          }
          
          window.dispatchEvent(new CustomEvent('userProfileUpdated', { 
            detail: updatedUserData 
          }))
        }
        
        onClose()
      } else {
        alert(t('error.updateProfile') + ': ' + (result.error || t('error.generic')))
      }
    } catch (error) {
      console.error('❌ Erreur mise à jour profil:', error)
      alert(t('error.updateProfile'))
    }
    setIsLoading(false)
  }

  return (
    <div className="space-y-4 max-h-[70vh] overflow-y-auto">
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('profile')}
          className={`px-4 py-2 text-sm font-medium ${activeTab === 'profile' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
        >
          {t('profile.personalInfo')}
        </button>
        <button
          onClick={() => setActiveTab('password')}
          className={`px-4 py-2 text-sm font-medium ${activeTab === 'password' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
        >
          {t('profile.password')}
        </button>
      </div>

      {activeTab === 'profile' && (
        <>
          <div className="border-b border-gray-200 pb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-3">{t('profile.personalInfo')}</h3>
            
            <div className="grid grid-cols-2 gap-4">
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
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.linkedinProfile')}</label>
              <input
                type="url"
                value={formData.linkedinProfile}
                onChange={(e) => setFormData(prev => ({ ...prev, linkedinProfile: e.target.value }))}
                placeholder="https://linkedin.com/in/votre-profil"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="border-b border-gray-200 pb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-3">{t('profile.contact')}</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.email')}</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.country')}</label>
              <select 
                value={formData.country}
                onChange={handleCountryChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                {countries.map(country => (
                  <option key={country.code} value={country.code}>
                    {country.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('profile.phone')}
                <span className="text-xs text-gray-500 ml-2">{t('form.phoneFormat')}: {getCurrentCountryFormat()}</span>
              </label>
              <input
                type="tel"
                value={formData.phone}
                onChange={handlePhoneChange}
                placeholder={getCurrentCountryFormat()}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="pb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-3">{t('profile.company')}</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.companyName')}</label>
              <input
                type="text"
                value={formData.companyName}
                onChange={(e) => setFormData(prev => ({ ...prev, companyName: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.companyWebsite')}</label>
              <input
                type="url"
                value={formData.companyWebsite}