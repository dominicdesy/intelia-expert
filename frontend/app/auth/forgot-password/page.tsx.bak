'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'
import type { Language } from '@/types'

// ==================== TRADUCTIONS ====================
const translations = {
  fr: {
    title: 'Mot de passe oublié',
    description: 'Entrez votre adresse email et nous vous enverrons un lien pour réinitialiser votre mot de passe',
    emailLabel: 'Adresse email',
    emailPlaceholder: 'votre@email.com',
    sendButton: 'Envoyer le lien de réinitialisation',
    sending: 'Envoi en cours...',
    backToLogin: 'Retour à la connexion',
    noAccount: 'Vous n\'avez pas de compte ?',
    createAccount: 'Créer un compte',
    supportProblem: 'Problème avec la réinitialisation ?',
    contactSupport: 'Contactez le support',
    securityInfo: 'Pour votre sécurité, le lien de réinitialisation expire dans 1 heure.',
    securityInfo2: 'Aucun email reçu ? Vérifiez vos spams ou contactez le support.',
    redirecting: 'Redirection en cours...',
    // Messages d'erreur et succès
    enterEmail: 'Veuillez entrer votre adresse email',
    invalidEmail: 'Veuillez entrer une adresse email valide',
    emailSent: 'Un email de réinitialisation a été envoyé à',
    checkInbox: 'Vérifiez votre boîte de réception et vos spams',
    emailNotFound: 'Cette adresse email n\'est pas associée à un compte',
    tooManyAttempts: 'Trop de tentatives. Veuillez réessayer dans quelques minutes',
    connectionError: 'Problème de connexion. Vérifiez votre connexion internet',
    genericError: 'Erreur lors de l\'envoi de l\'email de réinitialisation'
  },
  en: {
    title: 'Forgot Password',
    description: 'Enter your email address and we\'ll send you a link to reset your password',
    emailLabel: 'Email address',
    emailPlaceholder: 'your@email.com',
    sendButton: 'Send reset link',
    sending: 'Sending...',
    backToLogin: 'Back to login',
    noAccount: 'Don\'t have an account?',
    createAccount: 'Create account',
    supportProblem: 'Problem with reset?',
    contactSupport: 'Contact support',
    securityInfo: 'For your security, the reset link expires in 1 hour.',
    securityInfo2: 'No email received? Check your spam folder or contact support.',
    redirecting: 'Redirecting...',
    // Messages d'erreur et succès
    enterEmail: 'Please enter your email address',
    invalidEmail: 'Please enter a valid email address',
    emailSent: 'A reset email has been sent to',
    checkInbox: 'Check your inbox and spam folder',
    emailNotFound: 'This email address is not associated with an account',
    tooManyAttempts: 'Too many attempts. Please try again in a few minutes',
    connectionError: 'Connection problem. Check your internet connection',
    genericError: 'Error sending reset email'
  },
  es: {
    title: 'Contraseña olvidada',
    description: 'Ingresa tu dirección de email y te enviaremos un enlace para restablecer tu contraseña',
    emailLabel: 'Dirección de email',
    emailPlaceholder: 'tu@email.com',
    sendButton: 'Enviar enlace de restablecimiento',
    sending: 'Enviando...',
    backToLogin: 'Volver al inicio',
    noAccount: '¿No tienes cuenta?',
    createAccount: 'Crear cuenta',
    supportProblem: '¿Problema con el restablecimiento?',
    contactSupport: 'Contactar soporte',
    securityInfo: 'Por tu seguridad, el enlace de restablecimiento expira en 1 hora.',
    securityInfo2: '¿No recibiste email? Revisa tu spam o contacta soporte.',
    redirecting: 'Redirigiendo...',
    // Messages d'erreur et succès
    enterEmail: 'Por favor ingresa tu dirección de email',
    invalidEmail: 'Por favor ingresa una dirección de email válida',
    emailSent: 'Un email de restablecimiento ha sido enviado a',
    checkInbox: 'Revisa tu bandeja de entrada y spam',
    emailNotFound: 'Esta dirección de email no está asociada con una cuenta',
    tooManyAttempts: 'Demasiados intentos. Inténtalo de nuevo en unos minutos',
    connectionError: 'Problema de conexión. Verifica tu conexión a internet',
    genericError: 'Error al enviar el email de restablecimiento'
  },
  de: {
    title: 'Passwort vergessen',
    description: 'Geben Sie Ihre E-Mail-Adresse ein und wir senden Ihnen einen Link zum Zurücksetzen Ihres Passworts',
    emailLabel: 'E-Mail-Adresse',
    emailPlaceholder: 'ihre@email.com',
    sendButton: 'Reset-Link senden',
    sending: 'Wird gesendet...',
    backToLogin: 'Zurück zur Anmeldung',
    noAccount: 'Haben Sie kein Konto?',
    createAccount: 'Konto erstellen',
    supportProblem: 'Problem beim Zurücksetzen?',
    contactSupport: 'Support kontaktieren',
    securityInfo: 'Zu Ihrer Sicherheit läuft der Reset-Link in 1 Stunde ab.',
    securityInfo2: 'Keine E-Mail erhalten? Überprüfen Sie Ihren Spam-Ordner oder kontaktieren Sie den Support.',
    redirecting: 'Weiterleitung...',
    // Messages d'erreur et succès
    enterEmail: 'Bitte geben Sie Ihre E-Mail-Adresse ein',
    invalidEmail: 'Bitte geben Sie eine gültige E-Mail-Adresse ein',
    emailSent: 'Eine Reset-E-Mail wurde gesendet an',
    checkInbox: 'Überprüfen Sie Ihren Posteingang und Spam-Ordner',
    emailNotFound: 'Diese E-Mail-Adresse ist nicht mit einem Konto verknüpft',
    tooManyAttempts: 'Zu viele Versuche. Versuchen Sie es in ein paar Minuten erneut',
    connectionError: 'Verbindungsproblem. Überprüfen Sie Ihre Internetverbindung',
    genericError: 'Fehler beim Senden der Reset-E-Mail'
  }
}

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-12 h-12" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== PAGE MOT DE PASSE OUBLIÉ ====================
export default function ForgotPasswordPage() {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()
  
  // États
  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [isClient, setIsClient] = useState(false)

  // Hydratation côté client
  useEffect(() => {
    setIsClient(true)
    
    // Détection de la langue UNIQUEMENT côté client
    const detectLanguage = () => {
      // Priorité 1: Paramètre lang dans l'URL
      const urlParams = new URLSearchParams(window.location.search)
      const langParam = urlParams.get('lang') as Language
      if (langParam && translations[langParam]) {
        setCurrentLanguage(langParam)
        localStorage.setItem('intelia-language', langParam)
        return
      }

      // Priorité 2: localStorage
      const savedLanguage = localStorage.getItem('intelia-language') as Language
      if (savedLanguage && translations[savedLanguage]) {
        setCurrentLanguage(savedLanguage)
        return
      }

      // Priorité 3: Langue du navigateur
      const browserLanguage = navigator.language.substring(0, 2) as Language
      if (translations[browserLanguage]) {
        setCurrentLanguage(browserLanguage)
        localStorage.setItem('intelia-language', browserLanguage)
      }
    }

    detectLanguage()
  }, [])

  // Redirection si déjà connecté
  useEffect(() => {
    if (isClient && isAuthenticated && user) {
      console.log('Utilisateur déjà connecté, redirection...')
      router.push('/chat')
    }
  }, [isClient, isAuthenticated, user, router])

  // Récupération des traductions pour la langue courante
  const t = translations[currentLanguage]

  const handleSubmit = async () => {
    setError('')
    setSuccess('')
    
    // Validations
    if (!email.trim()) {
      setError(t.enterEmail)
      return
    }
    
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError(t.invalidEmail)
      return
    }

    setIsLoading(true)

    try {
      console.log('Demande réinitialisation pour:', email.trim())
      
      // Appel API pour la réinitialisation
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app/api'}/v1/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim()
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Erreur ${response.status}`)
      }

      const data = await response.json()
      console.log('Email envoyé avec succès')
      
      setSuccess(`${t.emailSent} ${email.trim()}`)
      setEmail('')
      
    } catch (error: any) {
      console.error('Erreur:', error)
      
      // Gestion d'erreurs spécifiques
      if (error.message.includes('404')) {
        setError(t.emailNotFound)
      } else if (error.message.includes('429')) {
        setError(t.tooManyAttempts)
      } else if (error.message.includes('Failed to fetch')) {
        setError(t.connectionError)
      } else {
        setError(error.message || t.genericError)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      handleSubmit()
    }
  }

  // Affichage de chargement pendant l'hydratation
  if (!isClient) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement...</p>
        </div>
      </div>
    )
  }

  // Si l'utilisateur est connecté, on affiche un loader pendant la redirection
  if (isAuthenticated && user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">{t.redirecting}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <InteliaLogo className="w-12 h-12" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {t.title}
          </h1>
          <p className="text-gray-600 leading-relaxed">
            {t.description}
          </p>
        </div>

        {/* Messages d'erreur */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Messages de succès */}
        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{success}</span>
            </div>
            <div className="mt-2 text-xs text-green-600">
              {t.checkInbox}
            </div>
          </div>
        )}

        {/* Formulaire */}
        <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200">
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                {t.emailLabel}
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyPress={handleKeyPress}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
                placeholder={t.emailPlaceholder}
                disabled={isLoading}
                autoComplete="email"
              />
            </div>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || !email.trim()}
              className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>{t.sending}</span>
                </div>
              ) : (
                t.sendButton
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <div className="mt-6 text-center space-y-3">
          <Link
            href={`/?lang=${currentLanguage}`}
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            {t.backToLogin}
          </Link>
          
          <div className="text-xs text-gray-500">
            {t.noAccount}{' '}
            <Link href={`/?signup=true&lang=${currentLanguage}`} className="text-blue-600 hover:underline transition-colors">
              {t.createAccount}
            </Link>
          </div>
        </div>

        {/* Support */}
        <div className="mt-4 p-3 bg-gray-50 rounded-lg text-center">
          <p className="text-xs text-gray-600">
            {t.supportProblem}{' '}
            <button
              type="button"
              onClick={() => window.open('mailto:support@intelia.com?subject=Problème réinitialisation mot de passe', '_blank')}
              className="text-blue-600 hover:underline font-medium transition-colors"
            >
              {t.contactSupport}
            </button>
          </p>
        </div>

        {/* Information sécurité */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500 leading-relaxed">
            {t.securityInfo}
            <br />
            {t.securityInfo2}
          </p>
        </div>

        {/* Debug en développement */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-4 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
            <strong>Dev Debug:</strong>
            <br />• API URL: {process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app/api'}
            <br />• Endpoint: /v1/auth/reset-password
            <br />• Current Language: {currentLanguage}
          </div>
        )}
      </div>
    </div>
  )
}