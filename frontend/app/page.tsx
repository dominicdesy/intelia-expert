'use client'

import React, { useState, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useTranslation } from '@/lib/languages/i18n'
import { useAuthStore } from '@/lib/stores/auth'

// Logo Intelia
const InteliaLogo = ({ className = "w-16 h-16" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// Sélecteur de langue simple
const LanguageSelector = () => {
  const { changeLanguage, currentLanguage } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)

  const languages = [
    { code: 'fr', name: 'Français', flag: '🇫🇷' },
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Español', flag: '🇪🇸' }
  ]

  const currentLang = languages.find(lang => lang.code === currentLanguage) || languages[0]

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition-colors"
      >
        <span>{currentLang.flag}</span>
        <span>{currentLang.name}</span>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full right-0 mt-1 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
            {languages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => {
                  changeLanguage(lang.code)
                  setIsOpen(false)
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center space-x-2 ${
                  lang.code === currentLanguage ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
                } first:rounded-t-lg last:rounded-b-lg transition-colors`}
              >
                <span>{lang.flag}</span>
                <span>{lang.name}</span>
                {lang.code === currentLanguage && (
                  <svg className="w-4 h-4 text-blue-500 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// Composant qui gère useSearchParams dans Suspense
function AuthCallbackHandler() {
  const searchParams = useSearchParams()
  const [authMessage, setAuthMessage] = useState('')

  React.useEffect(() => {
    const authStatus = searchParams?.get('auth')
    if (!authStatus) return
    
    if (authStatus === 'success') {
      setAuthMessage('Connexion réussie !')
    } else if (authStatus === 'error') {
      setAuthMessage('Erreur de connexion')
    } else if (authStatus === 'incomplete') {
      setAuthMessage('Informations manquantes')
    }
    
    // Nettoyer l'URL
    try {
      const url = new URL(window.location.href)
      url.searchParams.delete('auth')
      window.history.replaceState({}, '', url.pathname)
    } catch (error) {
      console.error('Erreur nettoyage URL:', error)
    }
    
    setTimeout(() => {
      setAuthMessage('')
    }, 3000)
  }, [searchParams])

  if (authMessage) {
    return (
      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 text-blue-700 rounded text-sm">
        {authMessage}
      </div>
    )
  }

  return null
}

// PAGE LOGIN SIMPLIFIÉE
function LoginPageContent() {
  const router = useRouter()
  const { t, currentLanguage } = useTranslation()
  const { login } = useAuthStore()

  // États simples
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showSignup, setShowSignup] = useState(false)

  // Fonction de connexion simple
  const handleLogin = async () => {
    setError('')
    setSuccess('')

    if (!email.trim()) {
      setError(t('login.emailLabel') || 'Email requis')
      return
    }

    if (!password) {
      setError(t('login.passwordLabel') || 'Mot de passe requis')
      return
    }

    setIsLoading(true)

    try {
      await login(email.trim(), password)
      setSuccess(t('auth.success') || 'Connexion réussie')
      
      setTimeout(() => {
        router.push('/chat')
      }, 1000)
      
    } catch (error: any) {
      if (error.message?.includes('Invalid login credentials')) {
        setError('Email ou mot de passe incorrect')
      } else if (error.message?.includes('Email not confirmed')) {
        setError('Email non confirmé. Vérifiez votre boîte mail.')
      } else {
        setError(error.message || 'Erreur de connexion')
      }
    } finally {
      setIsLoading(false)
    }
  }

  // Modal d'inscription simple
  const SignupModal = () => (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">{t('auth.createAccount')}</h3>
          <button onClick={() => setShowSignup(false)} className="text-gray-400 hover:text-gray-600">
            ×
          </button>
        </div>
        <p className="text-gray-600 mb-4">
          Inscription disponible bientôt. Pour l'instant, contactez-nous pour créer un compte.
        </p>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowSignup(false)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            {t('modal.cancel') || 'Annuler'}
          </button>
          <button
            onClick={() => window.open('mailto:support@intelia.com?subject=Demande création compte', '_blank')}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Nous contacter
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      
      {/* Sélecteur de langue */}
      <div className="absolute top-4 right-4">
        <LanguageSelector />
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <InteliaLogo className="w-16 h-16" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
          {t('page.title') || 'Connexion à Intelia Expert'}
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          
          {/* Callback d'auth dans Suspense */}
          <Suspense fallback={null}>
            <AuthCallbackHandler />
          </Suspense>
          
          {/* Messages d'erreur */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
              {error}
            </div>
          )}

          {/* Messages de succès */}
          {success && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded text-sm">
              {success}
            </div>
          )}

          <div className="space-y-6">
            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                {t('login.emailLabel')}
              </label>
              <div className="mt-1">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                  placeholder={t('login.emailPlaceholder')}
                />
              </div>
            </div>

            {/* Mot de passe */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                {t('login.passwordLabel')}
              </label>
              <div className="mt-1">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                  placeholder={t('login.passwordPlaceholder')}
                />
              </div>
            </div>

            {/* Remember me & Mot de passe oublié */}
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                  {t('login.rememberMe')}
                </label>
              </div>

              <div className="text-sm">
                <Link 
                  href="/auth/forgot-password"
                  className="font-medium text-blue-600 hover:text-blue-500"
                >
                  {t('auth.forgotPassword')}
                </Link>
              </div>
            </div>

            {/* Bouton de connexion */}
            <div>
              <button
                onClick={handleLogin}
                disabled={isLoading}
                className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>{t('auth.connecting')}</span>
                  </div>
                ) : (
                  t('auth.login')
                )}
              </button>
            </div>
          </div>

          {/* Séparateur */}
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">{t('common.or')}</span>
              </div>
            </div>
          </div>

          {/* Bouton d'inscription */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              {t('auth.newToIntelia')}{' '}
              <button
                onClick={() => setShowSignup(true)}
                className="font-medium text-blue-600 hover:text-blue-500"
              >
                {t('auth.createAccount')}
              </button>
            </p>
          </div>

          {/* Footer */}
          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">
              En continuant, vous acceptez nos{' '}
              <Link href="/terms" className="text-blue-600 hover:text-blue-500">
                Conditions d'utilisation
              </Link>
              {' et notre '}
              <Link href="/privacy" className="text-blue-600 hover:text-blue-500">
                Politique de confidentialité
              </Link>
            </p>
          </div>
        </div>
      </div>

      {/* Modal d'inscription */}
      {showSignup && <SignupModal />}

      {/* Debug */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 left-4 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
          <strong>Debug:</strong> Langue: {currentLanguage}
        </div>
      )}
    </div>
  )
}

// PAGE PRINCIPALE avec Suspense
export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement...</p>
        </div>
      </div>
    }>
      <LoginPageContent />
    </Suspense>
  )
}