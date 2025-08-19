// page.tsx - Version Backend API complète et fonctionnelle

'use client'

import React, { useState, useEffect, useRef, useCallback, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
// 🔄 CHANGEMENT PRINCIPAL: Utiliser le store backend au lieu de Supabase
import { useAuthStore } from '@/lib/stores/auth' // ← Maintenant c'est le store backend
import type { Language, User } from '@/types'


// 🆕 BANNIÈRE TEMPORAIRE pour informer du changement
const BackendMigrationBanner = () => (
  <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
    <div className="flex items-center space-x-2">
      <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span className="text-sm text-green-800 font-medium">
        Service optimisé : Création de compte maintenant plus rapide et fiable
      </span>
    </div>
  </div>
)

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
    connecting: 'Connecting...',
    creating: 'Creating...',
    loginError: 'Login error',
    signupError: 'Signup error',
    emailRequired: 'Email address is required',
    emailInvalid: 'Please enter a valid email address',
    passwordRequired: 'Password is required',
    passwordTooShort: 'Password must contain at least 8 characters, one uppercase and one number',
    passwordMismatch: 'Passwords do not match',
    firstNameRequired: 'First name is required',
    lastNameRequired: 'Last name is required',
    countryRequired: 'Country is required',
    phoneInvalid: 'Invalid phone format',
    terms: 'terms of service',
    privacy: 'privacy policy',
    gdprNotice: 'By signing in, you agree to our',
    needHelp: 'Need help?',
    contactSupport: 'Contact support',
    createAccount: 'Create account',
    backToLogin: 'Back to login',
    confirmationSent: 'Confirmation email sent! Check your mailbox.',
    accountCreated: 'Account created successfully! Check your emails to confirm your account.',
    personalInfo: 'Personal information',
    firstName: 'First name',
    lastName: 'Last name',
    linkedinProfile: 'Personal LinkedIn profile',
    contact: 'Contact',
    country: 'Country',
    countryCode: 'Country code',
    areaCode: 'Area code',
    phoneNumber: 'Phone number',
    company: 'Company',
    companyName: 'Company name',
    companyWebsite: 'Company website',
    companyLinkedin: 'Company LinkedIn page',
    optional: '(optional)',
    required: '*',
    close: 'Close',
    alreadyHaveAccount: 'Already have an account?',
    authSuccess: 'Login successful!',
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
    { code: 'en' as Language, name: 'English', flag: '🇺🇸' },
    { code: 'es' as Language, name: 'Español', flag: '🇪🇸' },
    { code: 'de' as Language, name: 'Deutsch', flag: '🇩🇪' }
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

// Fonctions de validation
const validateEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

const validatePassword = (password: string): { isValid: boolean; errors: string[] } => {
  const errors: string[] = []
  
  if (password.length < 8) {
    errors.push('Au moins 8 caractères')
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('Une majuscule')
  }
  if (!/[0-9]/.test(password)) {
    errors.push('Un chiffre')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

const validatePhone = (countryCode: string, areaCode: string, phoneNumber: string): boolean => {
  if (!countryCode.trim() && !areaCode.trim() && !phoneNumber.trim()) {
    return true
  }
  
  if (countryCode.trim() || areaCode.trim() || phoneNumber.trim()) {
    if (!countryCode.trim() || !/^\+[1-9]\d{0,3}$/.test(countryCode.trim())) {
      return false
    }
    
    if (!areaCode.trim() || !/^\d{3}$/.test(areaCode.trim())) {
      return false
    }
    
    if (!phoneNumber.trim() || !/^\d{7}$/.test(phoneNumber.trim())) {
      return false
    }
  }
  
  return true
}

// 🔧 Contenu principal de la page
function PageContent() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  
  // 🔄 UTILISATION DU STORE BACKEND (API identique à Supabase)
  const { user, isAuthenticated, isLoading, hasHydrated } = useAuthStore()
  const { login, register, initializeSession } = useAuthStore()

  // Refs pour éviter les doubles appels
  const hasInitialized = useRef(false)
  const hasCheckedAuth = useRef(false)
  const redirectLock = useRef(false)
  const sessionInitialized = useRef(false)

  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const t = translations[currentLanguage]
  
  const [isSignupMode, setIsSignupMode] = useState(false)
  const [localError, setLocalError] = useState('')
  const [localSuccess, setLocalSuccess] = useState('')
  
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
  const passwordInputRef = useRef<HTMLInputElement>(null)

  // ✅ FONCTIONS UTILITAIRES
  const rememberMeUtils = {
    save: (email: string, remember: boolean) => {
      try {
        if (remember && email) {
          localStorage.setItem('intelia_remember_email', email)
          localStorage.setItem('intelia_remember_flag', 'true')
          console.log('🔄 [Init] Remember me sauvegardé:', { email, remember })
        } else {
          localStorage.removeItem('intelia_remember_email')
          localStorage.removeItem('intelia_remember_flag')
          console.log('🔄 [Init] Remember me effacé')
        }
      } catch (error) {
        console.warn('⚠️ [Init] Erreur sauvegarde remember me:', error)
      }
    },

    load: () => {
      try {
        const savedEmail = localStorage.getItem('intelia_remember_email') || ''
        const rememberFlag = localStorage.getItem('intelia_remember_flag') === 'true'
        const hasRememberedEmail = !!(savedEmail && rememberFlag)
        
        const result = {
          rememberMe: rememberFlag,
          lastEmail: savedEmail,
          hasRememberedEmail
        }
        
        console.log('🔄 [Init] Chargement remember me:', result)
        return result
      } catch (error) {
        console.warn('⚠️ [Init] Erreur chargement remember me:', error)
        return { rememberMe: false, lastEmail: '', hasRememberedEmail: false }
      }
    }
  }

  const safeRedirectToChat = useCallback(() => {
    if (redirectLock.current) {
      console.log('🔒 [Redirect] Redirection déjà en cours, skip')
      return
    }

    redirectLock.current = true
    console.log('🚀 [Redirect] Redirection vers /chat...')
    
    try {
      router.push('/chat')
    } catch (error) {
      console.error('❌ [Redirect] Erreur redirection:', error)
      redirectLock.current = false
    }
  }, [router])

  // ✅ GESTION DES CHANGEMENTS DE FORMULAIRES
  const handleLoginChange = (field: keyof typeof loginData, value: string | boolean) => {
    setLoginData(prev => ({ ...prev, [field]: value }))
    setLocalError('')
  }

  const handleSignupChange = (field: keyof typeof signupData, value: string) => {
    setSignupData(prev => ({ ...prev, [field]: value }))
    setLocalError('')
  }

  const validateSignupForm = (): string | null => {
    if (!signupData.email) return t.emailRequired
    if (!validateEmail(signupData.email)) return t.emailInvalid
    if (!signupData.password) return t.passwordRequired
    
    const passwordValidation = validatePassword(signupData.password)
    if (!passwordValidation.isValid) {
      return t.passwordTooShort
    }
    
    if (signupData.password !== signupData.confirmPassword) return t.passwordMismatch
    if (!signupData.firstName.trim()) return t.firstNameRequired
    if (!signupData.lastName.trim()) return t.lastNameRequired
    if (!signupData.country) return t.countryRequired
    
    if (!validatePhone(signupData.countryCode, signupData.areaCode, signupData.phoneNumber)) {
      return t.phoneInvalid
    }
    
    return null
  }

  // ✅ GESTION DE LA CONNEXION (fonctionne automatiquement avec le backend)
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')
    setLocalSuccess('')

    if (!loginData.email) {
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

    try {
      console.log('🔄 [Login] Tentative connexion backend...')
      
      // 🔄 APPEL BACKEND VIA LE STORE (API identique)
      await login(loginData.email, loginData.password)
      
      // Sauvegarder remember me
      rememberMeUtils.save(loginData.email, loginData.rememberMe)
      
      setLocalSuccess(t.authSuccess)
      console.log('✅ [Login] Connexion backend réussie')
      
      // Redirection automatique après succès
      setTimeout(() => {
        safeRedirectToChat()
      }, 1000)
      
    } catch (error: any) {
      console.error('❌ [Login] Erreur connexion backend:', error)
      setLocalError(error?.message || t.authError)
    }
  }

  // ✅ GESTION DE L'INSCRIPTION (fonctionne automatiquement avec le backend)
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')
    setLocalSuccess('')

    const validationError = validateSignupForm()
    if (validationError) {
      setLocalError(validationError)
      return
    }

    try {
      console.log('🔄 [Signup] Tentative création compte backend...')
      
      // 🔄 APPEL BACKEND VIA LE STORE (API identique)
      const userData = {
        email: signupData.email,
        firstName: signupData.firstName,
        lastName: signupData.lastName,
        linkedinProfile: signupData.linkedinProfile,
        country: signupData.country,
        countryCode: signupData.countryCode,
        areaCode: signupData.areaCode,
        phoneNumber: signupData.phoneNumber,
        companyName: signupData.companyName,
        companyWebsite: signupData.companyWebsite,
        companyLinkedin: signupData.companyLinkedin
      }
      
      await register(signupData.email, signupData.password, userData)
      
      setLocalSuccess(t.accountCreated)
      console.log('✅ [Signup] Création compte backend réussie')
      
      // Retour au mode login après création
      setTimeout(() => {
        setIsSignupMode(false)
        setLoginData(prev => ({ ...prev, email: signupData.email }))
      }, 2000)
      
    } catch (error: any) {
      console.error('❌ [Signup] Erreur création compte backend:', error)
      setLocalError(error?.message || t.signupError)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (isSignupMode) {
        handleSignup(e as any)
      } else {
        handleLogin(e as any)
      }
    }
  }

  const handleCloseSignup = () => {
    setIsSignupMode(false)
    setLocalError('')
    setLocalSuccess('')
  }

  const toggleMode = () => {
    setIsSignupMode(!isSignupMode)
    setLocalError('')
    setLocalSuccess('')
  }

  // ✅ EFFECTS D'INITIALISATION
  useEffect(() => {
    if (!hasInitialized.current) {
      hasInitialized.current = true
      
      // Charger remember me
      const { rememberMe, lastEmail } = rememberMeUtils.load()
      if (rememberMe && lastEmail) {
        setLoginData(prev => ({
          ...prev,
          email: lastEmail,
          rememberMe: true
        }))
      }
    }
  }, [])

  useEffect(() => {
    if (!hasHydrated) return
    
    if (!sessionInitialized.current) {
      sessionInitialized.current = true
      console.log('🔄 [Session] Initialisation unique de la session')
      initializeSession()
    }
  }, [hasHydrated, initializeSession])

  useEffect(() => {
    if (!hasHydrated) return
    
    if (!hasCheckedAuth.current && !isLoading) {
      hasCheckedAuth.current = true
      console.log('🔍 [Auth] Vérification unique de l\'authentification')
      
      if (isAuthenticated && user) {
        console.log('✅ [Auth] Utilisateur connecté, redirection...')
        safeRedirectToChat()
      } else {
        console.log('❌ [Auth] Utilisateur non connecté')
      }
    }
  }, [hasHydrated, isLoading, isAuthenticated, user, safeRedirectToChat])

  // Affichage loading pendant l'hydratation
  if (!hasHydrated || isLoading) {
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
      <div className="absolute top-4 right-4">
        <LanguageSelector onLanguageChange={setCurrentLanguage} currentLanguage={currentLanguage} />
      </div>
      
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <InteliaLogo className="w-16 h-16" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
          {t.title}
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-2xl">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10 max-h-screen overflow-y-auto relative">
          
          {/* 🆕 BANNIÈRE INFORMATION BACKEND */}
          <BackendMigrationBanner />
          
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
                    {isSignupMode ? t.signupError : t.loginError}
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

          {/* FORMULAIRE DE CONNEXION */}
          {!isSignupMode && (
            <form onSubmit={handleLogin} onKeyPress={handleKeyPress}>
              <div className="space-y-6">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                    {t.email}
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
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    {t.password}
                  </label>
                  <div className="mt-1 relative">
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      required
                      ref={passwordInputRef}
                      value={loginData.password}
                      onChange={(e) => handleLoginChange('password', e.target.value)}
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                        </svg>
                      ) : (
                        <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                      onChange={(e) => handleLoginChange('rememberMe', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                      {t.rememberMe}
                    </label>
                  </div>

                  <div className="text-sm">
                    <Link href="/forgot-password" className="font-medium text-blue-600 hover:text-blue-500">
                      {t.forgotPassword}
                    </Link>
                  </div>
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? t.connecting : t.login}
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* FORMULAIRE D'INSCRIPTION */}
          {isSignupMode && (
            <form onSubmit={handleSignup} onKeyPress={handleKeyPress}>
              <div className="space-y-6">
                {/* Section Informations personnelles */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">{t.personalInfo}</h3>
                  
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        {t.firstName} <span className="text-red-500">{t.required}</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={signupData.firstName}
                        onChange={(e) => handleSignupChange('firstName', e.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        {t.lastName} <span className="text-red-500">{t.required}</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={signupData.lastName}
                        onChange={(e) => handleSignupChange('lastName', e.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t.linkedinProfile} {t.optional}
                    </label>
                    <input
                      type="url"
                      value={signupData.linkedinProfile}
                      onChange={(e) => handleSignupChange('linkedinProfile', e.target.value)}
                      placeholder="https://linkedin.com/in/votre-profil"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>

                {/* Section Contact */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">{t.contact}</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t.email} <span className="text-red-500">{t.required}</span>
                    </label>
                    <input
                      type="email"
                      required
                      value={signupData.email}
                      onChange={(e) => handleSignupChange('email', e.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t.country} <span className="text-red-500">{t.required}</span>
                    </label>
                    <select
                      required
                      value={signupData.country}
                      onChange={(e) => handleSignupChange('country', e.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    >
                      <option value="">Sélectionnez un pays</option>
                      {countries.map(country => (
                        <option key={country.value} value={country.value}>
                          {country.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Téléphone optionnel */}
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t.phoneNumber} {t.optional}
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      <input
                        type="text"
                        placeholder="+1"
                        value={signupData.countryCode}
                        onChange={(e) => handleSignupChange('countryCode', e.target.value)}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                      <input
                        type="text"
                        placeholder="514"
                        value={signupData.areaCode}
                        onChange={(e) => handleSignupChange('areaCode', e.target.value)}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                      <input
                        type="text"
                        placeholder="1234567"
                        value={signupData.phoneNumber}
                        onChange={(e) => handleSignupChange('phoneNumber', e.target.value)}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                    </div>
                  </div>
                </div>

                {/* Section Entreprise */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">{t.company}</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t.companyName} {t.optional}
                    </label>
                    <input
                      type="text"
                      value={signupData.companyName}
                      onChange={(e) => handleSignupChange('companyName', e.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t.companyWebsite} {t.optional}
                    </label>
                    <input
                      type="url"
                      value={signupData.companyWebsite}
                      onChange={(e) => handleSignupChange('companyWebsite', e.target.value)}
                      placeholder="https://votre-entreprise.com"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t.companyLinkedin} {t.optional}
                    </label>
                    <input
                      type="url"
                      value={signupData.companyLinkedin}
                      onChange={(e) => handleSignupChange('companyLinkedin', e.target.value)}
                      placeholder="https://linkedin.com/company/votre-entreprise"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>

                {/* Section Mot de passe */}
                <div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t.password} <span className="text-red-500">{t.required}</span>
                    </label>
                    <div className="mt-1 relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        required
                        value={signupData.password}
                        onChange={(e) => handleSignupChange('password', e.target.value)}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                      <button
                        type="button"
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? (
                          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                          </svg>
                        ) : (
                          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t.confirmPassword} <span className="text-red-500">{t.required}</span>
                    </label>
                    <div className="mt-1 relative">
                      <input
                        type={showConfirmPassword ? "text" : "password"}
                        required
                        value={signupData.confirmPassword}
                        onChange={(e) => handleSignupChange('confirmPassword', e.target.value)}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                      <button
                        type="button"
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      >
                        {showConfirmPassword ? (
                          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                          </svg>
                        ) : (
                          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="flex w-full justify-center rounded-md border border-transparent bg-green-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? t.creating : t.createAccount}
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* Boutons de navigation */}
          <div className="mt-6 text-center">
            {!isSignupMode ? (
              <div>
                <p className="text-sm text-gray-600">
                  {t.newToIntelia}{' '}
                  <button
                    onClick={toggleMode}
                    className="font-medium text-blue-600 hover:text-blue-500"
                  >
                    {t.createAccount}
                  </button>
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm text-gray-600">
                  {t.alreadyHaveAccount}{' '}
                  <button
                    onClick={toggleMode}
                    className="font-medium text-blue-600 hover:text-blue-500"
                  >
                    {t.backToLogin}
                  </button>
                </p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">
              {t.gdprNotice}{' '}
              <Link href="/terms" className="text-blue-600 hover:text-blue-500">
                {t.terms}
              </Link>
              {' '}et notre{' '}
              <Link href="/privacy" className="text-blue-600 hover:text-blue-500">
                {t.privacy}
              </Link>
            </p>
          </div>

          <div className="text-center mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-xs text-blue-700">
              💡 Nouveau : Service optimisé via notre backend sécurisé pour une meilleure fiabilité
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// 🔧 Export principal avec Suspense
export default function Page() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <img 
            src="/images/favicon.png" 
            alt="Intelia Logo" 
            className="w-16 h-16 mx-auto mb-4"
          />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement...</p>
        </div>
      </div>
    }>
      <PageContent />
    </Suspense>
  )
}