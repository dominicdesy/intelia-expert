'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTranslation } from '@/lib/languages/i18n'
import { useAuthStore } from '@/lib/stores/auth'

// Import des composants corrigés
import { InteliaLogo, LanguageSelector, AlertMessage, AuthFooter } from './page_components'
import { SignupModal } from './page_signup_modal'
import { useAuthenticationLogic } from './page_authentication'
import { usePageInitialization } from './page_initialization'

export default function LoginPage() {
  const router = useRouter()
  const { t, currentLanguage } = useTranslation() // Comme ContactModal
  const { login } = useAuthStore()

  // Utilisation des hooks d'initialisation et d'auth
  const {
    isSignupMode,
    toggleMode,
    localError,
    localSuccess,
    hasHydrated
  } = usePageInitialization()

  const authLogic = useAuthenticationLogic({
    currentLanguage,
    t,
    isSignupMode,
    setCurrentLanguage: () => {} // Pas utilisé dans ce contexte
  })

  // États simples pour le login
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

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

  // Attendre l'hydratation
  if (!hasHydrated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">{t('common.loading')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      
      {/* Sélecteur de langue unifié */}
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
          
          {/* Messages d'erreur et succès locaux + initialization */}
          {(error || localError) && (
            <AlertMessage 
              type="error" 
              title={t('error.generic')} 
              message={error || localError} 
            />
          )}

          {(success || localSuccess) && (
            <AlertMessage 
              type="success" 
              title="" 
              message={success || localSuccess} 
            />
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
                onClick={toggleMode}
                className="font-medium text-blue-600 hover:text-blue-500"
              >
                {t('auth.createAccount')}
              </button>
            </p>
          </div>

          {/* Footer */}
          <AuthFooter />
        </div>
      </div>

      {/* Modal d'inscription VRAIE - connectée aux hooks */}
      {isSignupMode && (
        <SignupModal 
          authLogic={authLogic}
          localError={localError}
          localSuccess={localSuccess}
          toggleMode={toggleMode}
        />
      )}

      {/* Debug */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 left-4 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
          <strong>Debug:</strong> Langue: {currentLanguage} | Signup: {isSignupMode ? 'ON' : 'OFF'}
        </div>
      )}
    </div>
  )
}