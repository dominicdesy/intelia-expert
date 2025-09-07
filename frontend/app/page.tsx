'use client'

import React, { useState, Suspense, useEffect } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useTranslation } from '@/lib/languages/i18n'
import { useAuthStore } from '@/lib/stores/auth' // Store unifié
import { availableLanguages } from '../lib/languages/config'
import { rememberMeUtils } from './page_hooks'
import { SignupModal } from './page_signup_modal'

// Logo Intelia dans un carré avec bordure bleue
const InteliaLogo = ({ className = "w-20 h-20" }: { className?: string }) => (
  <div className={`${className} bg-white border-2 border-blue-100 rounded-2xl shadow-lg flex items-center justify-center p-3`}>
    <img 
      src="/images/favicon.png" 
      alt="Intelia Logo" 
      className="w-full h-full object-contain"
    />
  </div>
)

// Sélecteur de langue moderne
const LanguageSelector = () => {
  const { changeLanguage, currentLanguage } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)

  const currentLang = availableLanguages.find(lang => lang.code === currentLanguage) || availableLanguages[0]

  const handleLanguageChange = (langCode: string) => {
    changeLanguage(langCode)
    setIsOpen(false)
  }

  return (
    <div className="relative language-selector">
       <button
         onClick={(e) => {
           e.preventDefault()
           e.stopPropagation()
           setIsOpen(!isOpen)
         }}
         className="flex items-center space-x-2 px-4 py-2.5 text-sm bg-white border border-blue-200 rounded-xl shadow-sm hover:bg-blue-50 transition-all duration-300 text-blue-700 relative z-50"
         aria-expanded={isOpen}
         aria-haspopup="listbox"
       >
        <span>{currentLang.flag}</span>
        <span>{currentLang.nativeName}</span>
        <svg 
          className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full right-0 mt-1 w-48 bg-white border border-blue-200 rounded-xl shadow-xl z-50 max-h-64 overflow-y-auto">
            {availableLanguages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-blue-50 flex items-center space-x-3 transition-colors duration-150 ${
                  lang.code === currentLanguage ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                } first:rounded-t-xl last:rounded-b-xl`}
                role="option"
                aria-selected={lang.code === currentLanguage}
              >
                <span className="text-xl">{lang.flag}</span>
                <div className="flex-1">
                  <div className="font-medium">{lang.nativeName}</div>
                  <div className="text-xs text-gray-500">{lang.region}</div>
                </div>
                {lang.code === currentLanguage && (
                  <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
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
      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 text-blue-700 rounded-xl text-sm">
        {authMessage}
      </div>
    )
  }

  return null
}

// PAGE LOGIN COMPLÈTE - VERSION UNIFIÉE
function LoginPageContent() {
  const router = useRouter()
  const { t } = useTranslation()
  const { login, register } = useAuthStore() // ✅ Store unifié

  // États simples
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showSignup, setShowSignup] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  // Chargement du rememberMe au démarrage
  useEffect(() => {
    const savedData = rememberMeUtils.load()
    if (savedData.rememberMe && savedData.lastEmail) {
      setEmail(savedData.lastEmail)
      setRememberMe(true)
    }
  }, [])

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

  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Fonctions de validation
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

  // ✅ FONCTION SIGNUP UNIFIÉE - utilise le store au lieu de fetch direct
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    console.log('[Signup] Utilisation du store unifié:', signupData)

    setIsLoading(true)
    setError('')

    try {
      // Validation côté client
      if (!signupData.email || !signupData.password || !signupData.firstName || !signupData.lastName) {
        throw new Error(t('validation.correctErrors'))
      }

      if (signupData.password !== signupData.confirmPassword) {
        throw new Error(t('validation.password.mismatch'))
      }

      // Validation du mot de passe
      const passwordValidation = validatePassword(signupData.password)
      if (!passwordValidation.isValid) {
        throw new Error(passwordValidation.errors[0])
      }

      // ✅ UTILISATION DU STORE UNIFIÉ au lieu de fetch direct
      const userData = {
        name: `${signupData.firstName} ${signupData.lastName}`,
        firstName: signupData.firstName,
        lastName: signupData.lastName,
        companyName: signupData.companyName,
        phone: (signupData.countryCode && signupData.areaCode && signupData.phoneNumber) 
          ? `${signupData.countryCode}${signupData.areaCode}${signupData.phoneNumber}`
          : undefined
      }

      await register(signupData.email, signupData.password, userData)

      setSuccess(t('verification.pending.emailSent') || 'Compte créé avec succès!')
      
      // Fermer la modal après succès
      setTimeout(() => {
        setShowSignup(false)
        setSuccess('')
      }, 2000)

      return {
        success: true,
        message: t('verification.pending.emailSent') || 'Compte créé avec succès!'
      }

    } catch (error: any) {
      console.error('[Signup] Erreur store unifié:', error)
      
      let errorMessage = error.message || t('error.generic')
      
      if (errorMessage.includes('already registered') || 
          errorMessage.includes('already exists') || 
          errorMessage.includes('User already exists')) {
        errorMessage = t('auth.emailAlreadyExists') || 'Cette adresse email est déjà utilisée'
      } else if (errorMessage.includes('Password') || errorMessage.includes('password')) {
        errorMessage = t('auth.passwordRequirementsNotMet') || 'Le mot de passe ne respecte pas les critères requis'      
      } else if (errorMessage.includes('Invalid email') || errorMessage.includes('email')) {
        errorMessage = t('error.emailInvalid')
      }
      
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  // Logique d'authentification pour la SignupModal
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

  // ✅ FONCTION DE CONNEXION - déjà correcte avec le store
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
      // ✅ Utilise le store unifié
      await login(email.trim(), password)
      
      // Sauvegarde du rememberMe après succès
      rememberMeUtils.save(email.trim(), rememberMe)
      
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
    <div className="min-h-screen relative overflow-hidden bg-white">
      {/* Background avec lignes de démarcation bleues */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Formes géométriques bleues subtiles */}
        <div className="absolute top-20 left-20 w-32 h-32 bg-blue-100/30 rounded-full blur-xl"></div>
      </div>

      {/* Sélecteur de langue */}
      <div className="absolute top-6 right-6 z-[1000]">
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
            <h1 className="text-3xl font-bold text-gray-800 mb-2">
              {t('page.title')}
            </h1>
            <p className="text-gray-600 text-lg">
              {t('app.description')}
            </p>
          </div>

          {/* Card principale avec bordures bleues */}
          <div className="bg-white border-2 border-blue-100 rounded-3xl shadow-xl p-8 relative overflow-hidden">
            
            {/* Callback d'auth dans Suspense */}
            <Suspense fallback={null}>
              <AuthCallbackHandler />
            </Suspense>
            
            {/* Messages d'erreur */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
                {error}
              </div>
            )}

            {/* Messages de succès */}
            {success && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-xl text-sm">
                {success}
              </div>
            )}

            <div className="space-y-6 relative z-10">
              {/* Email */}
              <div className="space-y-2">
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  {t('login.emailLabel')}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                    </svg>
                  </div>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                    className="w-full pl-12 pr-4 py-4 bg-gray-50 border-2 border-blue-100 rounded-2xl text-gray-800 placeholder-gray-500 focus:border-blue-300 focus:bg-white transition-all duration-300"
                    placeholder={t('login.emailPlaceholder')}
                  />
                </div>
              </div>

              {/* Mot de passe */}
              <div className="space-y-2">
                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                  {t('login.passwordLabel')}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                    className="w-full pl-12 pr-12 py-4 bg-gray-50 border-2 border-blue-100 rounded-2xl text-gray-800 placeholder-gray-500 focus:border-blue-300 focus:bg-white transition-all duration-300"
                    placeholder={t('login.passwordPlaceholder')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-blue-400 hover:text-blue-600 transition-colors"
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

              {/* Remember me & Mot de passe oublié */}
              <div className="flex items-center justify-between">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-blue-300 bg-gray-50 text-blue-600 focus:ring-blue-500 focus:ring-offset-0"
                  />
                  <span className="ml-3 text-sm text-gray-700">{t('login.rememberMe')}</span>
                </label>
                <Link 
                  href="/auth/forgot-password"
                  className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
                >
                  {t('auth.forgotPassword')}
                </Link>
              </div>

              {/* Bouton de connexion */}
              <button
                onClick={handleLogin}
                disabled={isLoading}
                className="w-full relative py-4 px-6 bg-blue-100 hover:bg-blue-200 border-2 border-blue-100 hover:border-blue-200 text-blue-700 font-semibold rounded-2xl shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-5 h-5 border-2 border-blue-700/30 border-t-blue-700 rounded-full animate-spin"></div>
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
                  <div className="w-full border-t border-blue-200"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white text-gray-500">{t('auth.noAccountYet')}</span>
                </div>
              </div>

              {/* Bouton d'inscription */}
              <button
                onClick={() => setShowSignup(true)}
                disabled={isLoading}
                className="w-full py-4 px-6 bg-gray-50 hover:bg-blue-50 border-2 border-blue-100 hover:border-blue-200 text-blue-700 font-medium rounded-2xl transition-all duration-300 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
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

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-xs text-gray-500">
              {t('gdpr.notice')}
            </p>
            <div className="mt-3 space-x-1 text-xs">
              <Link 
                href="/terms" 
                className="transition-colors"
                style={{ color: '#226ae4' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#1e5db3'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#226ae4'
                }}
              >
                {t('legal.terms')}
              </Link>
              <span className="text-gray-400">•</span>
              <Link 
                href="/privacy" 
                className="transition-colors"
                style={{ color: '#226ae4' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#1e5db3'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#226ae4'
                }}
              >
                {t('legal.privacy')}
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Modal d'inscription */}
      {showSignup && (
        <SignupModal 
          authLogic={authLogic}
          localError=""
          localSuccess=""
          toggleMode={() => setShowSignup(false)}
        />
      )}
    </div>
  )
}

// Composant fallback corrigé 
const LoadingFallback = () => {
  const { t } = useTranslation()
  
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <img 
          src="/images/logo.png" 
          alt="Intelia Logo" 
          className="w-16 h-16 mx-auto mb-4 object-contain drop-shadow-lg"
        />
        <div className="w-12 h-12 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-600">{t('common.loading')}</p>
      </div>
    </div>
  )
}

// PAGE PRINCIPALE avec Suspense
export default function LoginPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <LoginPageContent />
    </Suspense>
  )
}