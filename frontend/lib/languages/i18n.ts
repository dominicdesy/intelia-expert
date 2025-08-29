// ==================== SYSTÈME DE TRADUCTION INTELIA EXPERT ====================

import { useState, useEffect } from 'react'
// ✅ CHANGEMENT: Utiliser le singleton au lieu de createClientComponentClient
import { getSupabaseClient } from '@/lib/supabase/singleton'

// ✅ CHANGEMENT: Utiliser le singleton au lieu de createClientComponentClient
const supabase = getSupabaseClient()

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
  'chat.disclaimer': string  // ✅ AJOUTÉ

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
  'language.changeSuccess': string      // ✅ AJOUTÉ
  'language.interfaceUpdated': string   // ✅ AJOUTÉ
  'language.reloadForWidget': string    // ✅ AJOUTÉ
  'language.reloadNow': string          // ✅ AJOUTÉ
  'language.continueWithoutReload': string // ✅ AJOUTÉ

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
    'chat.disclaimer': 'Intelia Expert peut faire des erreurs. Faites vérifier les réponses par un professionnel au besoin.',  // ✅ AJOUTÉ

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
    'language.changeSuccess': 'Langue modifiée !',                            // ✅ AJOUTÉ
    'language.interfaceUpdated': 'L\'interface a été mise à jour immédiatement.',  // ✅ AJOUTÉ
    'language.reloadForWidget': 'Pour que le widget de chat soit également dans la nouvelle langue, un rechargement de page est recommandé.',  // ✅ AJOUTÉ
    'language.reloadNow': '🔄 Recharger maintenant',                          // ✅ AJOUTÉ
    'language.continueWithoutReload': '⏭️ Continuer sans recharger',          // ✅ AJOUTÉ

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
    'chat.disclaimer': 'Intelia Expert can make mistakes. Please verify the answers with a professional if necessary.',  // ✅ AJOUTÉ

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
    'language.changeSuccess': 'Language Changed!',                            // ✅ AJOUTÉ
    'language.interfaceUpdated': 'The interface has been updated immediately.',   // ✅ AJOUTÉ
    'language.reloadForWidget': 'For the chat widget to also be in the new language, a page reload is recommended.',  // ✅ AJOUTÉ
    'language.reloadNow': '🔄 Reload Now',                                   // ✅ AJOUTÉ
    'language.continueWithoutReload': '⏭️ Continue Without Reload',          // ✅ AJOUTÉ

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
    'chat.disclaimer': 'Intelia Expert puede cometer errores. Verifique las respuestas con un profesional si es necesario.',  // ✅ AJOUTÉ

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
    'language.changeSuccess': '¡Idioma Cambiado!',                            // ✅ AJOUTÉ
    'language.interfaceUpdated': 'La interfaz se ha actualizado inmediatamente.',  // ✅ AJOUTÉ
    'language.reloadForWidget': 'Para que el widget de chat también esté en el nuevo idioma, se recomienda recargar la página.',  // ✅ AJOUTÉ
    'language.reloadNow': '🔄 Recargar Ahora',                               // ✅ AJOUTÉ
    'language.continueWithoutReload': '⏭️ Continuar Sin Recargar',           // ✅ AJOUTÉ

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

// Hook de traduction (avec singleton)
export const useTranslation = () => {
  const [currentLanguage, setCurrentLanguage] = useState<string>('fr')

  // ✅ Initialiser avec la langue de l'utilisateur (utilise le singleton)
  useEffect(() => {
    const getUserLanguage = async () => {
      try {
        // ✅ Le client singleton est déjà initialisé plus haut
        const { data: { session } } = await supabase.auth.getSession()
        if (session?.user?.user_metadata?.language) {
          setCurrentLanguage(session.user.user_metadata.language)
        }
      } catch (error) {
        console.log('Utilisation de la langue par défaut (fr) - singleton')
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

// Export du type pour utilisation dans d'autres composants
export type { TranslationKeys }