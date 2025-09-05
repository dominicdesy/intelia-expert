'use client'

import React, { useState, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useTranslation } from '@/lib/languages/i18n'
import { useAuthStore } from '@/lib/stores/auth'
import { availableLanguages } from '../lib/languages/config'

// Import de la vraie SignupModal depuis le même répertoire
import { SignupModal } from './page_signup_modal'

// Logo Intelia moderne avec gradient
const InteliaLogo = ({ className = "w-16 h-16" }: { className?: string }) => (
  <div className={`${className} bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl flex items-center justify-center text-white font-bold text-2xl shadow-lg`}>
    <img 
      src="/images/favicon.png" 
      alt="Intelia Logo" 
      className="w-10 h-10 object-contain"
    />
  </div>
)

// Sélecteur de langue moderne avec glassmorphism
const LanguageSelector = () => {
  const { changeLanguage, currentLanguage } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)

  const currentLang = availableLanguages.find(lang => lang.code === currentLanguage) || availableLanguages[0]

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-4 py-2.5 text-sm bg-white/10 backdrop-blur-md border border-white/20 rounded-xl shadow-lg hover:bg-white/20 transition-all duration-300 text-white"
      >
        <span>{currentLang.flag}</span>
        <span>{currentLang.nativeName}</span>
        <svg className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full right-0 mt-1 w-48 bg-white/10 backdrop-blur-xl border border-white/20 rounded-xl shadow-xl z-50 max-h-64 overflow-y-auto">
            {availableLanguages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => {
                  changeLanguage(lang.code)
                  setIsOpen(false)
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-white/20 flex items-center space-x-3 ${
                  lang.code === currentLanguage ? 'bg-white/20 text-white' : 'text-white/90'
                } first:rounded-t-xl last:rounded-b-xl transition-colors`}
              >
                <span className="text-xl">{lang.flag}</span>
                <div className="flex-1">
                  <div className="font-medium">{lang.nativeName}</div>
                  <div className="text-xs text-white/60">{lang.region}</div>
                </div>
                {lang.code === currentLanguage && (
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
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

// Composant qui gère useSearchParams dans Suspense - CONSERVÉ INTÉGRALEMENT
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
      <div className="mb-4 p-3 bg-blue-50/80 backdrop-blur-sm border border-blue-200/50 text-blue-700 rounded-xl text-sm">
        {authMessage}
      </div>
    )
  }

  return null
}

// PAGE LOGIN COMPLÈTE avec design moderne
function LoginPageContent() {
  const router = useRouter()
  const { t, currentLanguage } = useTranslation()
  const { login } = useAuthStore()

  // États simples - CONSERVÉS
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showSignup, setShowSignup] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  // États pour le signup - CONSERVÉS
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

  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Fonctions de validation - CONSERVÉES INTÉGRALEMENT
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

  // Gestion des changements du formulaire signup - CONSERVÉE
  const handleSignupChange = (field: string, value: string) => {
    setSignupData(prev => ({ ...prev, [field]: value }))
  }

  // FONCTION SIGNUP COMPLÈTE - CONSERVÉE INTÉGRALEMENT
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

      // Construction intelligente de l'URL API
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL
      
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
        credentials: 'omit'
      })

      console.log('🔥 Réponse backend:', response.status, response.statusText)

      const responseText = await response.text()
      console.log('📄 Corps de réponse:', responseText)

      if (!response.ok) {
        let errorMessage = t('error.serverError') || `Erreur serveur (${response.status})`
        
        try {
          const errorData = JSON.parse(responseText)
          errorMessage = errorData.detail || errorData.message || errorMessage
        } catch {
          errorMessage = responseText || errorMessage
        }
        
        throw new Error(errorMessage)
      }

      const result = JSON.parse(responseText)
      console.log('✅ Inscription réussie:', result)

      if (result.success && result.token) {
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
      
      let errorMessage = error.message || t('error.generic')
      
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
      
      throw new Error(errorMessage)
    }
  }

  // Logique d'authentification pour la SignupModal - CONSERVÉE
  const authLogic = {
    signupData,
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading,
    handleSignupChange,
    handleSignup,
    validatePassword,
    validatePhone
  }

  // Fonction de connexion - CONSERVÉE INTÉGRALEMENT
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
    <div className="min-h-screen relative overflow-hidden">
      {/* Background avec gradient animé */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-purple-700 to-indigo-800">
        <div 
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Ccircle cx='30' cy='30' r='2'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
          }}
        ></div>
        
        {/* Formes géométriques flottantes */}
        <div className="absolute top-20 left-20 w-32 h-32 bg-white/10 rounded-full blur-xl animate-pulse"></div>
        <div className="absolute bottom-20 right-20 w-40 h-40 bg-purple-400/20 rounded-full blur-xl animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/3 w-24 h-24 bg-blue-300/15 rounded-full blur-lg animate-pulse delay-500"></div>
      </div>

      {/* Sélecteur de langue */}
      <div className="absolute top-6 right-6 z-10">
        <LanguageSelector />
      </div>

      {/* Contenu principal */}
      <div className="relative z-10 flex flex-col justify-center items-center min-h-screen px-4 sm:px-6 lg:px-8">
        
        <div className="w-full max-w-md">
          
          {/* Header avec logo */}
          <div className="text-center mb-8">
            <div className="flex justify-center mb-6">
              <InteliaLogo className="w-16 h-16" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">
              {t('page.title')}
            </h1>
            <p className="text-blue-100/80 text-lg">
              Votre assistant IA spécialisé en agriculture
            </p>
          </div>

          {/* Card principale avec glassmorphism */}
          <div className="bg-white/10 backdrop-blur-2xl border border-white/20 rounded-3xl shadow-2xl p-8">
            
            {/* Callback d'auth dans Suspense - CONSERVÉ */}
            <Suspense fallback={null}>
              <AuthCallbackHandler />
            </Suspense>
            
            {/* Messages d'erreur - CONSERVÉS avec style moderne */}
            {error && (
              <div className="mb-4 p-3 bg-red-500/20 backdrop-blur-sm border border-red-300/50 text-red-100 rounded-xl text-sm">
                {error}
              </div>
            )}

            {/* Messages de succès - CONSERVÉS avec style moderne */}
            {success && (
              <div className="mb-4 p-3 bg-green-500/20 backdrop-blur-sm border border-green-300/50 text-green-100 rounded-xl text-sm">
                {success}
              </div>
            )}

            <div className="space-y-6">
              {/* Email */}
              <div className="space-y-2">
                <label htmlFor="email" className="block text-sm font-medium text-white/90">
                  {t('login.emailLabel')}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                    </svg>
                  </div>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                    className="w-full pl-12 pr-4 py-4 bg-white/10 border border-white/20 rounded-2xl text-white placeholder-white/60 focus:border-white/40 focus:bg-white/15 transition-all duration-300 backdrop-blur-sm"
                    placeholder={t('login.emailPlaceholder')}
                  />
                </div>
              </div>

              {/* Mot de passe */}
              <div className="space-y-2">
                <label htmlFor="password" className="block text-sm font-medium text-white/90">
                  {t('login.passwordLabel')}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                    className="w-full pl-12 pr-12 py-4 bg-white/10 border border-white/20 rounded-2xl text-white placeholder-white/60 focus:border-white/40 focus:bg-white/15 transition-all duration-300 backdrop-blur-sm"
                    placeholder={t('login.passwordPlaceholder')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-white/60 hover:text-white/80 transition-colors"
                  >
                    {showPassword ? (
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                      </svg>
                    ) : (
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Remember me & Mot de passe oublié - CONSERVÉS */}
              <div className="flex items-center justify-between">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-white/30 bg-white/10 text-blue-600 focus:ring-blue-500 focus:ring-offset-0"
                  />
                  <span className="ml-3 text-sm text-white/90">{t('login.rememberMe')}</span>
                </label>
                <Link 
                  href="/auth/forgot-password"
                  className="text-sm text-blue-200 hover:text-white transition-colors"
                >
                  {t('auth.forgotPassword')}
                </Link>
              </div>

              {/* Bouton de connexion - CONSERVÉ avec style moderne */}
              <button
                onClick={handleLogin}
                disabled={isLoading}
                className="w-full relative py-4 px-6 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-semibold rounded-2xl shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>{t('auth.connecting')}</span>
                  </div>
                ) : (
                  <span className="flex items-center justify-center space-x-2">
                    <span>{t('auth.login')}</span>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </span>
                )}
              </button>

              {/* Séparateur */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/20"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-transparent text-white/70">{t('common.or')}</span>
                </div>
              </div>

              {/* Bouton d'inscription */}
              <button
                onClick={() => setShowSignup(true)}
                className="w-full py-4 px-6 bg-white/10 hover:bg-white/15 border border-white/20 hover:border-white/30 text-white font-medium rounded-2xl transition-all duration-300 transform hover:scale-[1.02]"
              >
                <span className="flex items-center justify-center space-x-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                  <span>{t('auth.createAccount')}</span>
                </span>
              </button>
            </div>
          </div>

          {/* Footer - CONSERVÉ avec style moderne */}
          <div className="mt-8 text-center">
            <p className="text-xs text-white/60">
              {t('gdpr.notice')}
            </p>
            <div className="mt-3 space-x-1 text-xs">
              <Link href="/terms" className="text-blue-200 hover:text-white transition-colors">
                {t('legal.terms')}
              </Link>
              <span className="text-white/40">•</span>
              <Link href="/privacy" className="text-blue-200 hover:text-white transition-colors">
                {t('legal.privacy')}
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Modal d'inscription VRAIE - CONSERVÉE INTÉGRALEMENT */}
      {showSignup && (
        <SignupModal 
          authLogic={authLogic}
          localError=""
          localSuccess=""
          toggleMode={() => setShowSignup(false)}
        />
      )}

      {/* Debug - CONSERVÉ */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 left-4 p-2 bg-black/20 backdrop-blur-sm border border-white/20 rounded text-xs text-white">
          <strong>Debug:</strong> Langue: {currentLanguage}
        </div>
      )}
    </div>
  )
}

// Composant fallback - CONSERVÉ avec style moderne
const LoadingFallback = () => (
  <div className="min-h-screen bg-gradient-to-br from-blue-600 via-purple-700 to-indigo-800 flex items-center justify-center">
    <div className="text-center">
      <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
      <div className="w-12 h-12 border-2 border-white/30 border-t-white rounded-full animate-spin mx-auto mb-4"></div>
      <p className="text-white">Chargement...</p>
    </div>
  </div>
)

// PAGE PRINCIPALE avec Suspense - CONSERVÉE
export default function LoginPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <LoginPageContent />
    </Suspense>
  )
}