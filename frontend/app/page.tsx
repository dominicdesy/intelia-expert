'use client'

import React, { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'
import type { Language, User } from '@/types'

const translations = {
  fr: {
    title: 'Intelia Expert',
    email: 'Email',
    password: 'Mot de passe',
    confirmPassword: 'Confirmer le mot de passe',
    login: 'Se connecter',
    signup: 'Créer un compte',
    rememberMe: 'Se souvenir de mon email',
    forgotPassword: 'Mot de passe oublié ?',
    newToIntelia: 'Nouveau sur Intelia ?',
    connecting: 'Connexion en cours...',
    creating: 'Création en cours...',
    loginError: 'Erreur de connexion',
    signupError: 'Erreur de création',
    emailRequired: 'L\'adresse email est requise',
    emailInvalid: 'Veuillez entrer une adresse email valide',
    passwordRequired: 'Le mot de passe est requis',
    passwordTooShort: 'Le mot de passe doit contenir au moins 8 caractères, une majuscule et un chiffre',
    passwordMismatch: 'Les mots de passe ne correspondent pas',
    firstNameRequired: 'Le prénom est requis',
    lastNameRequired: 'Le nom de famille est requis',
    countryRequired: 'Le pays est requis',
    phoneInvalid: 'Format de téléphone invalide',
    terms: 'conditions d\'utilisation',
    privacy: 'politique de confidentialité',
    gdprNotice: 'En vous connectant, vous acceptez nos',
    needHelp: 'Besoin d\'aide ?',
    contactSupport: 'Contactez le support',
    createAccount: 'Créer un compte',
    backToLogin: 'Retour à la connexion',
    confirmationSent: 'Email de confirmation envoyé ! Vérifiez votre boîte mail.',
    accountCreated: 'Compte créé avec succès ! Vérifiez vos emails pour confirmer votre compte.',
    personalInfo: 'Informations personnelles',
    firstName: 'Prénom',
    lastName: 'Nom de famille',
    linkedinProfile: 'Profil LinkedIn personnel',
    contact: 'Contact',
    country: 'Pays',
    countryCode: 'Indicatif pays',
    areaCode: 'Indicatif régional',
    phoneNumber: 'Numéro de téléphone',
    company: 'Entreprise',
    companyName: 'Nom de l\'entreprise',
    companyWebsite: 'Site web de l\'entreprise',
    companyLinkedin: 'Page LinkedIn de l\'entreprise',
    optional: '(optionnel)',
    required: '*',
    close: 'Fermer',
    alreadyHaveAccount: 'Déjà un compte ?',
    authSuccess: 'Connexion réussie !',
    authError: 'Erreur de connexion, veuillez réessayer.',
    authIncomplete: 'Connexion incomplète, veuillez réessayer.',
    sessionCleared: 'Session précédente effacée',
    forceLogout: 'Déconnexion automatique'
  },
  en: {
    title: 'Intelia Expert',
    email: 'Email',
    password: 'Password',
    confirmPassword: 'Confirm password',
    login: 'Sign in',
    signup: 'Create account',
    rememberMe: 'Remember my email',
    forgotPassword: 'Forgot password?',
    newToIntelia: 'New to Intelia?',
    connecting: 'Signing in...',
    creating: 'Creating account...',
    loginError: 'Login error',
    signupError: 'Signup error',
    emailRequired: 'Email address is required',
    emailInvalid: 'Please enter a valid email address',
    passwordRequired: 'Password is required',
    passwordTooShort: 'Password must be at least 8 characters with one uppercase letter and one number',
    passwordMismatch: 'Passwords do not match',
    firstNameRequired: 'First name is required',
    lastNameRequired: 'Last name is required',
    countryRequired: 'Country is required',
    phoneInvalid: 'Invalid phone format',
    terms: 'terms of service',
    privacy: 'privacy policy',
    gdprNotice: 'By signing in, you accept our',
    needHelp: 'Need help?',
    contactSupport: 'Contact support',
    createAccount: 'Create account',
    backToLogin: 'Back to login',
    confirmationSent: 'Confirmation email sent! Check your mailbox.',
    accountCreated: 'Account created successfully! Check your emails to confirm your account.',
    personalInfo: 'Personal Information',
    firstName: 'First Name',
    lastName: 'Last Name',
    linkedinProfile: 'Personal LinkedIn Profile',
    contact: 'Contact',
    country: 'Country',
    countryCode: 'Country Code',
    areaCode: 'Area Code',
    phoneNumber: 'Phone Number',
    company: 'Company',
    companyName: 'Company Name',
    companyWebsite: 'Company Website',
    companyLinkedin: 'Company LinkedIn Page',
    optional: '(optional)',
    required: '*',
    close: 'Close',
    alreadyHaveAccount: 'Already have an account?',
    authSuccess: 'Successfully logged in!',
    authError: 'Login error, please try again.',
    authIncomplete: 'Incomplete login, please try again.',
    sessionCleared: 'Previous session cleared',
    forceLogout: 'Automatic logout'
  }
}

const countries = [
  { value: 'CA', label: 'Canada' },
  { value: 'US', label: 'États-Unis' },
  { value: 'FR', label: 'France' },
  { value: 'BE', label: 'Belgique' },
  { value: 'CH', label: 'Suisse' },
  { value: 'MX', label: 'Mexique' },
  { value: 'BR', label: 'Brésil' }
]

const InteliaLogo = ({ className = "w-16 h-16" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

const LanguageSelector = ({ onLanguageChange, currentLanguage }: { 
  onLanguageChange: (lang: Language) => void
  currentLanguage: Language 
}) => {
  const [isOpen, setIsOpen] = useState(false)

  const languages = [
    { code: 'fr' as Language, name: 'Français', flag: '🇫🇷' },
    { code: 'en' as Language, name: 'English', flag: '🇺🇸' }
  ]

  const currentLang = languages.find(lang => lang.code === currentLanguage)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition-colors"
      >
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
        </svg>
        <span>{currentLang?.name}</span>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
            {languages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => {
                  onLanguageChange(lang.code)
                  setIsOpen(false)
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center space-x-2 ${
                  lang.code === currentLanguage ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
                } first:rounded-t-lg last:rounded-b-lg transition-colors`}
              >
                <span>{lang.flag}</span>
                <span>{lang.name}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

const validateEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export default function LoginPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  const { 
    login, 
    register,
    logout,
    isLoading, 
    isAuthenticated,
    hasHydrated 
  } = useAuthStore()

  const [isInitialized, setIsInitialized] = useState(false)
  const [hasLoggedOut, setHasLoggedOut] = useState(false)
  const [isRedirecting, setIsRedirecting] = useState(false)

  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const [localError, setLocalError] = useState('')
  const [localSuccess, setLocalSuccess] = useState('')
  
  const [isSignupMode, setIsSignupMode] = useState(false)
  
  const [loginData, setLoginData] = useState({
    email: '',
    password: '',
    rememberMe: false
  })

  const [signupData, setSignupData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    country: ''
  })

  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const passwordInputRef = useRef<HTMLInputElement>(null)
  const t = translations[currentLanguage]

  // Debug logs
  useEffect(() => {
    console.log('🔍 [Debug] LoginData état actuel:', {
      email: loginData.email,
      hasPassword: !!loginData.password,
      rememberMe: loginData.rememberMe,
      localStorage_rememberMe: localStorage.getItem('intelia-remember-me'),
      localStorage_lastEmail: localStorage.getItem('intelia-last-email')
    })
  }, [loginData])

  // Initialisation avec remember email
  useEffect(() => {
    if (isInitialized) return
    
    console.log('🔧 [Login] Initialisation + force logout systématique')
    
    if (isAuthenticated && hasHydrated) {
      console.log('🚨 [Login] FORCE LOGOUT pour sécurité - garde email si remember me')
      logout().then(() => {
        setHasLoggedOut(true)
        setLocalSuccess(t.sessionCleared)
      }).catch((error) => {
        console.error('❌ [Login] Erreur force logout:', error)
      })
    }
    
    const savedLanguage = localStorage.getItem('intelia-language') as Language
    if (savedLanguage && translations[savedLanguage]) {
      setCurrentLanguage(savedLanguage)
    }

    const rememberMe = localStorage.getItem('intelia-remember-me') === 'true'
    const lastEmail = localStorage.getItem('intelia-last-email') || ''
    
    if (rememberMe && lastEmail) {
      console.log('💾 [Login] Restauration email depuis remember me:', lastEmail)
      setLoginData(prev => ({
        ...prev,
        email: lastEmail,
        rememberMe: true,
        password: ''
      }))
      
      setLocalSuccess(`Email restauré : ${lastEmail}. Entrez votre mot de passe.`)
      
      setTimeout(() => {
        setLocalSuccess('')
      }, 4000)
    }

    setIsInitialized(true)
  }, [isAuthenticated, hasHydrated, logout, t])

  // Focus automatique sur mot de passe
  useEffect(() => {
    const rememberMe = localStorage.getItem('intelia-remember-me') === 'true'
    const lastEmail = localStorage.getItem('intelia-last-email') || ''
    
    if (rememberMe && lastEmail && loginData.email && !loginData.password && passwordInputRef.current) {
      console.log('🎯 [UX] Focus automatique sur mot de passe')
      setTimeout(() => {
        passwordInputRef.current?.focus()
      }, 500)
    }
  }, [loginData.email, loginData.password])

  // Gestion URL callback
  useEffect(() => {
    if (!isInitialized) return

    const authStatus = searchParams.get('auth')
    if (!authStatus) return
    
    if (authStatus === 'success') {
      setLocalSuccess(t.authSuccess)
    } else if (authStatus === 'error') {
      setLocalError(t.authError)  
    } else if (authStatus === 'incomplete') {
      setLocalError(t.authIncomplete)
    }
    
    const url = new URL(window.location.href)
    url.searchParams.delete('auth')
    window.history.replaceState({}, '', url.pathname)

    const timer = setTimeout(() => {
      setLocalSuccess('')
      setLocalError('')
    }, 3000)
    
    return () => clearTimeout(timer)
  }, [searchParams, t, isInitialized])

  const handleLanguageChange = (newLanguage: Language) => {
    setCurrentLanguage(newLanguage)
    localStorage.setItem('intelia-language', newLanguage)
  }

  const handleLoginChange = (field: string, value: string | boolean) => {
    console.log('🔄 [LoginChange] Field:', field, 'Value:', value)
    setLoginData(prev => ({ ...prev, [field]: value }))
    if (localError) setLocalError('')
    if (localSuccess) setLocalSuccess('')
  }

  const handleSignupChange = (field: string, value: string) => {
    setSignupData(prev => ({ ...prev, [field]: value }))
    if (localError) setLocalError('')
    if (localSuccess) setLocalSuccess('')
  }

  const handleLogin = async () => {
    setLocalError('')
    setLocalSuccess('')
    
    try {
      if (!loginData.email.trim()) {
        setLocalError(t.emailRequired)
        return
      }
      
      if (!validateEmail(loginData.email)) {
        setLocalError(t.emailInvalid)
        return
      }
      
      if (!loginData.password) {
        setLocalError(t.passwordRequired)
        return
      }

      if (loginData.password.length < 6) {
        setLocalError(t.passwordTooShort)
        return
      }

      console.log('🔐 [Login] Connexion:', loginData.email, 'Remember email:', loginData.rememberMe)
      
      await login(loginData.email.trim(), loginData.password)
      
      if (loginData.rememberMe) {
        console.log('💾 [Login] Sauvegarde EMAIL pour remember me')
        localStorage.setItem('intelia-remember-me', 'true')
        localStorage.setItem('intelia-last-email', loginData.email.trim())
      } else {
        console.log('🗑️ [Login] Suppression remember me')
        localStorage.removeItem('intelia-remember-me')
        localStorage.removeItem('intelia-last-email')
      }
      
      console.log('✅ [Login] Connexion réussie - redirection en cours...')
      
      setIsRedirecting(true)
      window.location.href = '/chat'
      
    } catch (error: any) {
      console.error('❌ [Login] Erreur:', error)
      setIsRedirecting(false)
      
      if (error.message?.includes('Invalid login credentials')) {
        setLocalError('Email ou mot de passe incorrect. Vérifiez vos identifiants.')
      } else if (error.message?.includes('Email not confirmed')) {
        setLocalError('Email non confirmé. Vérifiez votre boîte mail.')
      } else if (error.message?.includes('Too many requests')) {
        setLocalError('Trop de tentatives. Attendez quelques minutes.')
      } else {
        setLocalError(error.message || 'Erreur de connexion')
      }
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading && !isRedirecting) {
      handleLogin()
    }
  }

  const toggleMode = () => {
    setIsSignupMode(!isSignupMode)
    setLocalError('')
    setLocalSuccess('')
    
    if (!isSignupMode) {
      setLoginData({ email: '', password: '', rememberMe: false })
    } else {
      const rememberMe = localStorage.getItem('intelia-remember-me') === 'true'
      const lastEmail = localStorage.getItem('intelia-last-email') || ''
      
      setLoginData({ 
        email: rememberMe ? lastEmail : '', 
        password: '', 
        rememberMe 
      })
      
      if (rememberMe && lastEmail) {
        setLocalSuccess(`Email restauré : ${lastEmail}`)
        setTimeout(() => setLocalSuccess(''), 3000)
      }
    }
    
    setSignupData({
      email: '', password: '', confirmPassword: '',
      firstName: '', lastName: '', country: ''
    })
  }

  // Écrans de chargement
  if (!hasHydrated || !isInitialized) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Initialisation...</p>
        </div>
      </div>
    )
  }

  if (isRedirecting) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-6 text-lg font-medium text-gray-900">Connexion réussie !</p>
          <p className="mt-2 text-gray-600">Redirection vers votre chat...</p>
          <div className="mt-4 bg-blue-50 rounded-lg p-4 max-w-sm mx-auto">
            <div className="flex items-center justify-center">
              <svg className="animate-pulse h-5 w-5 text-blue-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span className="text-sm text-blue-700">Chargement en cours...</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
      <div className="absolute top-4 right-4">
        <LanguageSelector onLanguageChange={handleLanguageChange} currentLanguage={currentLanguage} />
      </div>
      
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <InteliaLogo className="w-16 h-16" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
          {t.title}
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
          
          {/* Messages d'erreur et succès */}
          {localError && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">
                    {t.loginError}
                  </h3>
                  <div className="mt-1 text-sm text-red-700">
                    {localError}
                  </div>
                </div>
              </div>
            </div>
          )}

          {localSuccess && (
            <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <div className="text-sm text-green-700">
                    {localSuccess}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Formulaire de connexion */}
          <div className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                {t.email} <span className="text-red-500">*</span>
              </label>
              <div className="mt-1">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={loginData.email}
                  onChange={(e) => handleLoginChange('email', e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm transition-colors"
                  placeholder="votre@email.com"
                  disabled={isLoading || isRedirecting}
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                {t.password} <span className="text-red-500">*</span>
              </label>
              <div className="mt-1 relative">
                <input
                  ref={passwordInputRef}
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={loginData.password}
                  onChange={(e) => handleLoginChange('password', e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm transition-colors"
                  placeholder={loginData.email ? "Entrez votre mot de passe" : "••••••••"}
                  disabled={isLoading || isRedirecting}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center hover:text-gray-600 transition-colors"
                  disabled={isLoading || isRedirecting}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.34 6.34m6.822 10.565l-3.536-3.536" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  checked={loginData.rememberMe}
                  onChange={(e) => {
                    console.log('📝 [Checkbox] Remember me clicked:', e.target.checked)
                    handleLoginChange('rememberMe', e.target.checked)
                  }}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  disabled={isLoading || isRedirecting}
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                  {t.rememberMe}
                </label>
              </div>

              <div className="text-sm">
                <Link 
                  href="/auth/forgot-password" 
                  className="font-medium text-blue-600 hover:text-blue-500 transition-colors"
                >
                  {t.forgotPassword}
                </Link>
              </div>
            </div>

            <div>
              <button
                type="button"
                onClick={handleLogin}
                disabled={isLoading || isRedirecting || !loginData.email || !loginData.password}
                className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>{t.connecting}</span>
                  </div>
                ) : isRedirecting ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Redirection...</span>
                  </div>
                ) : (
                  t.login
                )}
              </button>
            </div>
          </div>

          {/* Section d'inscription */}
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-white px-2 text-gray-500">
                  {t.newToIntelia}
                </span>
              </div>
            </div>

            <div className="mt-6">
              <button
                type="button"
                onClick={toggleMode}
                className="flex w-full justify-center rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                disabled={isLoading || isRedirecting}
              >
                {t.createAccount}
              </button>
            </div>
          </div>

          {/* Section RGPD */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center leading-relaxed">
              {t.gdprNotice}{' '}
              <a href="/terms" className="text-blue-600 hover:text-blue-500 transition-colors">
                {t.terms}
              </a>{' '}
              et notre{' '}
              <a href="/privacy" className="text-blue-600 hover:text-blue-500 transition-colors">
                {t.privacy}
              </a>
              .
            </p>
          </div>
        </div>
      </div>

      {/* Section d'aide */}
      <div className="mt-8 text-center">
        <p className="text-xs text-gray-500">
          {t.needHelp}{' '}
          <button
            type="button"
            onClick={() => window.open('mailto:support@intelia.com', '_blank')}
            className="text-blue-600 hover:underline font-medium"
          >
            {t.contactSupport}
          </button>
        </p>
      </div>
    </div>
  )
}