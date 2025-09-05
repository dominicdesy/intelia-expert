'use client'

import React, { useState, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useTranslation } from '@/lib/languages/i18n'
import { useAuthStore } from '@/lib/stores/auth'
import { availableLanguages } from '../lib/languages/config'

// Import de la vraie SignupModal depuis le même répertoire
import { SignupModal } from './page_signup_modal'

// Logo Intelia
const InteliaLogo = ({ className = "w-16 h-16" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// Sélecteur de langue utilisant les langues du fichier config.ts
const LanguageSelector = () => {
  const { changeLanguage, currentLanguage } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)

  const currentLang = availableLanguages.find(lang => lang.code === currentLanguage) || availableLanguages[0]

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition-colors"
      >
        <span>{currentLang.flag}</span>
        <span>{currentLang.nativeName}</span>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full right-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
            {availableLanguages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => {
                  changeLanguage(lang.code)
                  setIsOpen(false)
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center space-x-3 ${
                  lang.code === currentLanguage ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
                } first:rounded-t-lg last:rounded-b-lg transition-colors`}
              >
                <span className="text-xl">{lang.flag}</span>
                <div className="flex-1">
                  <div className="font-medium">{lang.nativeName}</div>
                  <div className="text-xs text-gray-500">{lang.region}</div>
                </div>
                {lang.code === currentLanguage && (
                  <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
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
  const { t } = useTranslation()
  const [authMessage, setAuthMessage] = useState('')

  React.useEffect(() => {
    const authStatus = searchParams?.get('auth')
    if (!authStatus) return
    
    if (authStatus === 'success') {
      setAuthMessage(t('auth.success'))
    } else if (authStatus === 'error') {
      setAuthMessage(t('auth.error'))
    } else if (authStatus === 'incomplete') {
      setAuthMessage(t('auth.incomplete'))
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
  }, [searchParams, t])

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

  // États pour le signup
  const [signupData, setSignupData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    linkedinProfile: '',
    country: '',
    countryCode: '',
    areaCode: '',
    phoneNumber: '',
    companyName: '',
    companyWebsite: '',
    companyLinkedin: ''
  })

  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Fonctions de validation utilisant les clés de traduction
  const validatePassword = (password: string) => {
    const errors = []
    if (password.length < 8) errors.push(t('validation.password.minLength'))
    if (!/[A-Z]/.test(password)) errors.push(t('validation.password.uppercase'))
    if (!/[a-z]/.test(password)) errors.push(t('validation.password.lowercase'))
    if (!/[0-9]/.test(password)) errors.push(t('validation.password.number'))
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) errors.push(t('validation.password.special'))
    return { isValid: errors.length === 0, errors }
  }

  const validatePhone = (countryCode: string, areaCode: string, phoneNumber: string) => {
    return countryCode && areaCode && phoneNumber && 
           areaCode.length >= 2 && phoneNumber.length >= 6
  }

  // Gestion des changements du formulaire signup
  const handleSignupChange = (field: string, value: string) => {
    setSignupData(prev => ({ ...prev, [field]: value }))
  }

  // FONCTION SIGNUP CORRIGÉE - Appel Backend API
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Signup attempt:', signupData)

    try {
      // Validation côté client avec traductions
      if (!signupData.email || !signupData.password || !signupData.firstName || !signupData.lastName) {
        throw new Error(t('validation.correctErrors') || 'Tous les champs obligatoires doivent être remplis')
      }

      if (signupData.password !== signupData.confirmPassword) {
        throw new Error(t('validation.password.mismatch'))
      }

      // Validation du mot de passe
      const passwordValidation = validatePassword(signupData.password)
      if (!passwordValidation.isValid) {
        throw new Error(passwordValidation.errors[0])
      }

      // Préparer les données pour l'API backend (format UserRegister)
      const registrationData = {
        email: signupData.email,
        password: signupData.password,
        first_name: signupData.firstName,
        last_name: signupData.lastName,
        full_name: `${signupData.firstName} ${signupData.lastName}`,
        company: signupData.companyName || undefined,
        phone: (signupData.countryCode && signupData.areaCode && signupData.phoneNumber) 
          ? `${signupData.countryCode}${signupData.areaCode}${signupData.phoneNumber}`
          : undefined
      }

      console.log('📤 Envoi vers backend API:', registrationData)

      // CHANGEMENT 1: Construction intelligente de l'URL API
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL
      
      // Construire l'URL intelligemment pour éviter les doubles /api/
      let apiUrl = API_BASE_URL
      if (apiUrl.endsWith('/api')) {
        apiUrl = `${apiUrl}/v1/auth/register`
      } else {
        apiUrl = `${apiUrl}/api/v1/auth/register`
      }
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(registrationData),
        credentials: 'omit' // Éviter les problèmes CORS
      })

      console.log('📥 Réponse backend:', response.status, response.statusText)

      // Lire la réponse
      const responseText = await response.text()
      console.log('📄 Corps de réponse:', responseText)

      if (!response.ok) {
        let errorMessage = t('error.serverError') || `Erreur serveur (${response.status})`
        
        try {
          const errorData = JSON.parse(responseText)
          errorMessage = errorData.detail || errorData.message || errorMessage
        } catch {
          // Si ce n'est pas du JSON, utiliser le texte brut
          errorMessage = responseText || errorMessage
        }
        
        throw new Error(errorMessage)
      }

      // Parser la réponse de succès
      const result = JSON.parse(responseText)
      console.log('✅ Inscription réussie:', result)

      // Vérifier que le backend a bien créé le compte
      if (result.success && result.token) {
        // Succès : afficher le message dans la modal, pas sur la page login
        return {
          success: true,
          message: t('verification.pending.emailSent') || 'Un email de confirmation vous a été envoyé. Vérifiez votre email pour confirmer votre compte.'
        }
        
      } else if (result.success) {
        return {
          success: true,
          message: t('verification.pending.emailSent') || 'Un email de confirmation vous a été envoyé. Vérifiez votre email pour confirmer votre compte.'
        }
      } else {
        throw new Error(t('error.unexpectedResponse') || 'Réponse inattendue du serveur')
      }

    } catch (error: any) {
      console.error('❌ Erreur inscription:', error)
      
      // Messages d'erreur personnalisés avec traductions
      let errorMessage = error.message || t('error.generic')
      
      // Messages spécifiques selon les erreurs backend
      if (errorMessage.includes('already registered') || 
          errorMessage.includes('already exists') || 
          errorMessage.includes('User already exists')) {
        errorMessage = t('auth.emailAlreadyExists') || 'Cette adresse email est déjà utilisée'
	  } else if (errorMessage.includes('Password') || errorMessage.includes('password')) {
	    errorMessage = t('auth.passwordRequirementsNotMet') || 'Le mot de passe ne respecte pas les critères requis'      
	  } else if (errorMessage.includes('Invalid email') || errorMessage.includes('email')) {
        errorMessage = t('error.emailInvalid')
      } else if (errorMessage.includes('NetworkError') || errorMessage.includes('fetch')) {
        errorMessage = t('error.connection') + '. ' + t('error.checkConnection')
      } else if (errorMessage.includes('502') || errorMessage.includes('503')) {
        errorMessage = t('error.serviceUnavailable') || 'Service temporairement indisponible. Réessayez dans quelques minutes.'
      }
      
      // Retourner l'erreur au lieu de la définir globalement
      throw new Error(errorMessage)
    }
  }

  // Logique d'authentification pour la SignupModal
  const authLogic = {
    signupData,
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading, // ← Utiliser le vrai état de loading
    handleSignupChange,
    handleSignup,
    validatePassword,
    validatePhone
  }

  // Fonction de connexion avec clés de traduction
  const handleLogin = async () => {
    setError('')
    setSuccess('')

    if (!email.trim()) {
      setError(t('error.emailRequired'))
      return
    }

    if (!password) {
      setError(t('validation.required.password'))
      return
    }

    setIsLoading(true)

    try {
      await login(email.trim(), password)
      setSuccess(t('auth.success'))
      
      setTimeout(() => {
        router.push('/chat')
      }, 1000)
      
    } catch (error: any) {
      if (error.message?.includes('Invalid login credentials')) {
        setError(t('auth.invalidCredentials') || 'Email ou mot de passe incorrect')
      } else if (error.message?.includes('Email not confirmed')) {
        setError(t('auth.emailNotConfirmed') || 'Email non confirmé. Vérifiez votre boîte mail.')
      } else {
        setError(error.message || t('auth.error'))
      }
    } finally {
      setIsLoading(false)
    }
  }

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
          {t('page.title')}
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

          {/* Footer avec traductions */}
          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">
              {t('gdpr.notice')}
            </p>
            <div className="mt-2 text-xs">
              <Link href="/terms" className="text-blue-600 hover:text-blue-500">
                {t('legal.terms')}
              </Link>
              {' • '}
              <Link href="/privacy" className="text-blue-600 hover:text-blue-500">
                {t('legal.privacy')}
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Modal d'inscription VRAIE */}
      {showSignup && (
        <SignupModal 
          authLogic={authLogic}
          localError=""
          localSuccess=""
          toggleMode={() => setShowSignup(false)}
        />
      )}

      {/* Debug */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 left-4 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
          <strong>Debug:</strong> Langue: {currentLanguage}
        </div>
      )}
    </div>
  )
}

// Composant fallback pour le Suspense principal sans useTranslation
const LoadingFallback = () => (
  <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
    <div className="text-center">
      <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">Chargement...</p>
    </div>
  </div>
)

// PAGE PRINCIPALE avec Suspense
export default function LoginPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <LoginPageContent />
    </Suspense>
  )
}
