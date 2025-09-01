'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'
import { useTranslation } from '@/lib/languages/i18n'

// Logo Intelia
const InteliaLogo = ({ className = "w-12 h-12" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// Page Mot de Passe Oublié
export default function ForgotPasswordPage() {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()
  
  // ✅ CORRECTION : utilisation directe du hook sans useMemo
  const { t, currentLanguage, loading: translationsLoading, changeLanguage } = useTranslation()
  
  // États
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [isClient, setIsClient] = useState(false)

  // Refs pour éviter les doubles appels
  const hasInitialized = useRef(false)
  const hasCheckedAuth = useRef(false)
  const isMounted = useRef(true)

  // ✅ CORRECTION : Hydratation côté client SANS boucle
  useEffect(() => {
    if (hasInitialized.current || !isMounted.current) return
    
    hasInitialized.current = true
    setIsClient(true)
    
    // Synchronisation directe sans fonction externe pour éviter les dépendances
    const timer = setTimeout(() => {
      if (isMounted.current) {
        try {
          const savedLanguage = localStorage.getItem('intelia-language')
          if (savedLanguage && savedLanguage !== currentLanguage) {
            console.log('[ForgotPassword] Synchronisation avec langue système:', savedLanguage)
            
            // CORRECTION : Parser le JSON pour extraire la vraie langue
            let languageCode = savedLanguage
            try {
              const parsed = JSON.parse(savedLanguage)
              if (parsed?.state?.currentLanguage) {
                languageCode = parsed.state.currentLanguage
              }
            } catch (parseError) {
              // Si ce n'est pas du JSON, utiliser directement la valeur
              languageCode = savedLanguage
            }
            
            console.log('[ForgotPassword] Code langue extrait:', languageCode)
            if (languageCode !== currentLanguage) {
              changeLanguage(languageCode)
            }
          }
        } catch (error) {
          console.warn('[ForgotPassword] Erreur synchronisation langue:', error)
        }
      }
    }, 100)

    return () => clearTimeout(timer)
  }, []) // ✅ AUCUNE dépendance pour éviter les boucles

  // CORRECTION : Écouter les changements de langue en temps réel
  useEffect(() => {
    const handleLanguageChange = (event: CustomEvent) => {
      const newLanguage = event.detail.language
      if (newLanguage && newLanguage !== currentLanguage) {
        console.log('[ForgotPassword] Changement langue détecté:', newLanguage)
        changeLanguage(newLanguage)
      }
    }

    window.addEventListener('languageChanged', handleLanguageChange as EventListener)
    
    return () => {
      window.removeEventListener('languageChanged', handleLanguageChange as EventListener)
    }
  }, [currentLanguage, changeLanguage])

  // ✅ CORRECTION : Redirection si déjà connecté AVEC protection
  useEffect(() => {
    if (hasCheckedAuth.current || !isMounted.current) return
    
    if (isClient && isAuthenticated && user && !translationsLoading) {
      hasCheckedAuth.current = true
      console.log('Utilisateur déjà connecté, redirection...')
      
      // Protection contre les redirections multiples
      const timer = setTimeout(() => {
        if (isMounted.current && window.location.pathname !== '/chat') {
          router.push('/chat')
        }
      }, 100)

      return () => clearTimeout(timer)
    }
  }, [isClient, isAuthenticated, user, translationsLoading, router])

  // CORRECTION : Fonction de soumission stable
  const handleSubmit = useCallback(async () => {
    setError('')
    setSuccess('')
    
    // Validations
    if (!email.trim()) {
      setError(t('forgotPassword.enterEmail') || 'Veuillez saisir votre email')
      return
    }
    
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError(t('forgotPassword.invalidEmail') || 'Format d\'email invalide')
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
      
      setSuccess(`${t('forgotPassword.emailSent') || 'Email envoyé à'} ${email.trim()}`)
      setEmail('')
      
    } catch (error: any) {
      console.error('Erreur:', error)
      
      // Gestion d'erreurs spécifiques avec fallbacks
      if (error.message.includes('404')) {
        setError(t('forgotPassword.emailNotFound') || 'Email non trouvé')
      } else if (error.message.includes('429')) {
        setError(t('forgotPassword.tooManyAttempts') || 'Trop de tentatives')
      } else if (error.message.includes('Failed to fetch')) {
        setError(t('forgotPassword.connectionError') || 'Erreur de connexion')
      } else {
        setError(error.message || t('forgotPassword.genericError') || 'Erreur inconnue')
      }
    } finally {
      setIsLoading(false)
    }
  }, [email, t]) // ✅ Dépendances minimales et stables

  // ✅ CORRECTION : Gestionnaire de touches stable
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading && email.trim()) {
      handleSubmit()
    }
  }, [isLoading, email, handleSubmit])

  // Cleanup au démontage
  useEffect(() => {
    return () => {
      isMounted.current = false
    }
  }, [])

  // ✅ CORRECTION : Condition d'affichage simplifiée
  if (!isClient || translationsLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">{t('common.loading') || 'Chargement...'}</p>
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
          <p className="text-gray-600">{t('forgotPassword.redirecting') || 'Redirection...'}</p>
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
            {t('forgotPassword.title') || 'Mot de passe oublié'}
          </h1>
          <p className="text-gray-600 leading-relaxed">
            {t('forgotPassword.description') || 'Saisissez votre email pour recevoir un lien de réinitialisation'}
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
              {t('forgotPassword.checkInbox') || 'Vérifiez votre boîte mail'}
            </div>
          </div>
        )}

        {/* Formulaire */}
        <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200">
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                {t('forgotPassword.emailLabel') || 'Adresse email'}
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyPress={handleKeyPress}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
                placeholder={t('forgotPassword.emailPlaceholder') || 'votre@email.com'}
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
                  <span>{t('forgotPassword.sending') || 'Envoi en cours...'}</span>
                </div>
              ) : (
                t('forgotPassword.sendButton') || 'Envoyer le lien'
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <div className="mt-6 text-center space-y-3">
          <Link
            href="/"
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            {t('forgotPassword.backToLogin') || 'Retour à la connexion'}
          </Link>
          
          <div className="text-xs text-gray-500">
            {t('forgotPassword.noAccount') || 'Pas de compte ?'}{' '}
            <Link href="/?signup=true" className="text-blue-600 hover:underline transition-colors">
              {t('auth.createAccount') || 'Créer un compte'}
            </Link>
          </div>
        </div>

        {/* Support */}
        <div className="mt-4 p-3 bg-gray-50 rounded-lg text-center">
          <p className="text-xs text-gray-600">
            {t('forgotPassword.supportProblem') || 'Un problème ?'}{' '}
            <button
              type="button"
              onClick={() => window.open('mailto:support@intelia.com?subject=Problème réinitialisation mot de passe', '_blank')}
              className="text-blue-600 hover:underline font-medium transition-colors"
            >
              {t('forgotPassword.contactSupport') || 'Contactez le support'}
            </button>
          </p>
        </div>

        {/* Information sécurité */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500 leading-relaxed">
            {t('forgotPassword.securityInfo') || 'Pour votre sécurité, le lien expirera dans 1 heure.'}
            <br />
            {t('forgotPassword.securityInfo2') || 'Vérifiez aussi vos spams.'}
          </p>
        </div>

        {/* Debug en développement */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-4 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
            <strong>Dev Debug:</strong>
            <br />• API URL: {process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app/api'}
            <br />• Endpoint: /v1/auth/reset-password
            <br />• Current Language: {currentLanguage}
            <br />• Translations Loading: {translationsLoading ? 'Yes' : 'No'}
            <br />• Test Translation: {t('forgotPassword.title') || 'FALLBACK'}
          </div>
        )}
      </div>
    </div>
  )
}