'use client'

import React, { useState, useEffect, useRef, useCallback, Suspense, useMemo } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'
import type { Language, User } from '@/types'

// Imports locaux
import { translations } from './page_translations'
import { 
  useCountries, 
  useCountryCodeMap, 
  validateEmail, 
  validatePassword, 
  validatePhone,
  validateLinkedIn,
  validateWebsite, 
  rememberMeUtils 
} from './page_hooks'
import { InteliaLogo, LanguageSelector, AlertMessage, PasswordInput, PasswordMatchIndicator, LoadingSpinner, AuthFooter } from './page_components'
import type { LoginData, SignupData } from './page_types'

// Contenu principal de la page
function PageContent() {
  console.log('🚀 [PageContent] Composant PageContent rendu')
  
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  
  const { user, isAuthenticated, isLoading, hasHydrated } = useAuthStore()
  const { login, register, initializeSession } = useAuthStore()

  // ⭐ HOOK APPELÉ IMMÉDIATEMENT - PAS DE CONDITION
  console.log('🎯 [PageContent] Appel du hook useCountries...')
  const { countries, loading: countriesLoading, usingFallback } = useCountries()
  console.log('📊 [PageContent] Hook useCountries retourné:', { 
    countriesLength: countries.length, 
    loading: countriesLoading, 
    usingFallback 
  })
  
  // Créer le mapping des codes téléphoniques dynamiquement
  const countryCodeMap = useCountryCodeMap(countries)

  // Refs pour éviter les doubles appels
  const hasInitialized = useRef(false)
  const hasCheckedAuth = useRef(false)
  const redirectLock = useRef(false)
  const sessionInitialized = useRef(false)

  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const t = useMemo(() => translations[currentLanguage], [currentLanguage])
  
  const [isSignupMode, setIsSignupMode] = useState(false) // ⭐ COMMENCER EN MODE LOGIN
  const [localError, setLocalError] = useState('')
  const [localSuccess, setLocalSuccess] = useState('')
  
  const [loginData, setLoginData] = useState<LoginData>({
    email: '',
    password: '',
    rememberMe: false
  })

  // États locaux avec gestion avancée
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const passwordInputRef = useRef<HTMLInputElement>(null)
  
  const [signupData, setSignupData] = useState<SignupData>({
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

  // Fonction de redirection sécurisée avec logique pathname
  const safeRedirectToChat = useCallback(() => {
    if (redirectLock.current) {
      console.log('🔒 [Redirect] Déjà en cours de redirection, ignoré')
      return
    }
    
    // NE PAS rediriger si on est déjà sur /chat
    if (pathname?.startsWith("/chat")) {
      console.log('🔧 [Redirect] Déjà sur /chat, pas de redirection')
      return
    }
    
    console.log('🚀 [Redirect] Redirection vers /chat depuis:', pathname)
    redirectLock.current = true
    
    // Utiliser router.replace au lieu de window.location
    // pour éviter le reload et donc la re-montée des providers
    router.replace('/chat')
  }, [pathname, router])

  // Gestion des changements de formulaires avec logique avancée
  const handleLoginChange = (field: keyof LoginData, value: string | boolean) => {
    setLoginData(prev => {
      const newData = { ...prev, [field]: value }
      
      // Gestion spéciale pour rememberMe
      if (field === 'rememberMe') {
        const isRememberChecked = value as boolean
        console.log('🛯 [HandleChange] RememberMe changé:', isRememberChecked)
        
        // Persistence en temps réel du statut rememberMe
        if (isRememberChecked && prev.email?.trim()) {
          // Si on coche ET qu'il y a un email, sauvegarder
          rememberMeUtils.save(prev.email.trim(), true)
          console.log('✅ [HandleChange] Email sauvegardé immédiatement:', prev.email.trim())
        } else if (!isRememberChecked) {
          // Si on décoche, effacer immédiatement
          rememberMeUtils.save('', false)
          console.log('🗑️ [HandleChange] Remember Me désactivé')
        }
      }
      
      // Gestion spéciale pour l'email quand rememberMe est actif
      if (field === 'email' && prev.rememberMe) {
        const emailValue = (value as string).trim()
        if (emailValue && validateEmail(emailValue)) {
          // Sauvegarder le nouvel email si remember est actif et email valide
          rememberMeUtils.save(emailValue, true)
          console.log('✅ [HandleChange] Nouvel email sauvegardé:', emailValue)
        }
      }
      
      return newData
    })
    
    if (localError) setLocalError('')
    if (localSuccess) setLocalSuccess('')
  }

  const handleSignupChange = (field: keyof SignupData, value: string) => {
    setSignupData(prev => {
      const newData = { ...prev, [field]: value }
      
      // Auto-remplir l'indicatif pays quand le pays change
      if (field === 'country' && value && countryCodeMap[value]) {
        console.log('🏳️ [Country] Auto-remplissage code pays:', value, '->', countryCodeMap[value])
        newData.countryCode = countryCodeMap[value]
      }
      
      return newData
    })
    setLocalError('')
  }

  const validateSignupForm = (): string | null => {
    const { 
      email, password, confirmPassword, firstName, lastName, country, 
      countryCode, areaCode, phoneNumber,
      linkedinProfile, companyWebsite, companyLinkedin 
    } = signupData

    if (!email.trim()) return t.emailRequired
    if (!validateEmail(email)) return t.emailInvalid
    if (!password) return t.passwordRequired
    
    const passwordValidation = validatePassword(password)
    if (!passwordValidation.isValid) return t.passwordTooShort
    
    if (password !== confirmPassword) return t.passwordMismatch
    if (!firstName.trim()) return t.firstNameRequired
    if (!lastName.trim()) return t.lastNameRequired
    if (!country) return t.countryRequired
    
    if (!validatePhone(countryCode, areaCode, phoneNumber)) {
      return 'Format de téléphone invalide. Si vous renseignez le téléphone, tous les champs (indicatif pays, indicatif régional, numéro) sont requis.'
    }
    
    if (linkedinProfile && !validateLinkedIn(linkedinProfile)) return 'Format LinkedIn invalide'
    if (companyWebsite && !validateWebsite(companyWebsite)) return 'Format de site web invalide'
    if (companyLinkedin && !validateLinkedIn(companyLinkedin)) return 'Format LinkedIn entreprise invalide'
    
    return null
  }

  // Gestion de la connexion avec logique avancée
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')
    setLocalSuccess('')

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

    try {
      console.log('🔑 [Login] Tentative connexion...')
      
      await login(loginData.email.trim(), loginData.password)
      
      // Gestion "Se souvenir de moi" avec fonction utilitaire
      rememberMeUtils.save(loginData.email.trim(), loginData.rememberMe)
      console.log('✅ [Login] Confirmation persistence remember me:', loginData.rememberMe)
      
      setLocalSuccess(t.authSuccess)
      console.log('✅ [Login] Connexion réussie')
      
      // Pas de redirection manuelle ici, elle sera gérée par useEffect
      
    } catch (error: any) {
      console.error('❌ [Login] Erreur connexion:', error)
      
      // Réinitialiser les verrous en cas d'erreur
      redirectLock.current = false
      
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

  // Gestion de l'inscription avec validation avancée
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
      console.log('🔑 [Signup] Tentative création compte...')
      
      const userData: Partial<User> = {
        name: `${signupData.firstName.trim()} ${signupData.lastName.trim()}`,
        user_type: 'producer',
        language: currentLanguage
      }
      
      await register(signupData.email.trim(), signupData.password, userData)
      
      setLocalSuccess(t.accountCreated)
      console.log('✅ [Signup] Création compte réussie')
      
      // Réinitialiser le formulaire
      setSignupData({
        email: '', password: '', confirmPassword: '',
        firstName: '', lastName: '', linkedinProfile: '',
        country: '', countryCode: '', areaCode: '', phoneNumber: '',
        companyName: '', companyWebsite: '', companyLinkedin: ''
      })
      
      // Passer en mode login après 4 secondes
      setTimeout(() => {
        setIsSignupMode(false)
        setLocalSuccess('')
      }, 4000)
      
    } catch (error: any) {
      console.error('❌ [Signup] Erreur création compte:', error)
      setLocalError(error.message || 'Erreur lors de la création du compte')
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

  const toggleMode = () => {
    console.log('🔄 [UI] Basculement mode:', isSignupMode ? 'signup → login' : 'login → signup')
    setIsSignupMode(!isSignupMode)
    setLocalError('')
    setLocalSuccess('')
  }

  // Effects d'initialisation avec Remember Me
  useEffect(() => {
    if (!hasInitialized.current) {
      hasInitialized.current = true
      console.log('🎯 [Init] Initialisation unique')
      
      // Charger les préférences utilisateur
      const savedLanguage = localStorage.getItem('intelia-language') as Language
      if (savedLanguage && translations[savedLanguage]) {
        setCurrentLanguage(savedLanguage)
      } else {
        const browserLanguage = navigator.language.substring(0, 2) as Language
        if (translations[browserLanguage]) {
          setCurrentLanguage(browserLanguage)
        }
      }

      // Restaurer EMAIL avec fonction utilitaire
      const { rememberMe, lastEmail, hasRememberedEmail } = rememberMeUtils.load()
      
      console.log('🔄 [Init] Chargement remember me:', { rememberMe, lastEmail, hasRememberedEmail })
      
      if (hasRememberedEmail) {
        setLoginData({
          email: lastEmail,
          password: '', // Toujours vider le mot de passe
          rememberMe: true
        })
        
        setLocalSuccess(`Email restauré : ${lastEmail}. Entrez votre mot de passe.`)
        setTimeout(() => setLocalSuccess(''), 4000)
      }
    }
  }, [])

  useEffect(() => {
    if (!hasHydrated) return
    
    if (!sessionInitialized.current) {
      sessionInitialized.current = true
      console.log('🔐 [Session] Initialisation unique de la session')
      initializeSession()
    }
  }, [hasHydrated, initializeSession])

  // Vérification authentification avec logique avancée
  useEffect(() => {
    if (!hasHydrated || !hasInitialized.current || hasCheckedAuth.current) {
      return
    }

    hasCheckedAuth.current = true
    console.log('🔐 [Auth] Vérification unique de l\'authentification')

    // Si déjà connecté, rediriger immédiatement
    if (isAuthenticated) {
      console.log('✅ [Auth] Déjà connecté, redirection immédiate')
      safeRedirectToChat()
      return
    }

    // Sinon, initialiser la session une seule fois
    if (!sessionInitialized.current) {
      sessionInitialized.current = true
      console.log('🔄 [Session] Initialisation unique de la session')
      
      initializeSession().then((sessionFound) => {
        if (sessionFound) {
          console.log('✅ [Session] Session trouvée, redirection automatique')
          // La redirection sera gérée par le changement d'état isAuthenticated
        } else {
          console.log('❌ [Session] Aucune session trouvée')
        }
      }).catch(error => {
        console.error('❌ [Session] Erreur initialisation:', error)
      })
    }
  }, [hasHydrated, hasInitialized.current, isAuthenticated, initializeSession, safeRedirectToChat])

  // Surveillance changement AUTH
  useEffect(() => {
    if (!hasHydrated || !hasInitialized.current || !hasCheckedAuth.current) {
      return
    }

    // Uniquement quand l'auth est prête ET valide
    if (!isLoading && isAuthenticated) {
      console.log('🔄 [Auth] État auth changé, redirection sécurisée')
      safeRedirectToChat()
    }
  }, [isAuthenticated, isLoading, hasHydrated, safeRedirectToChat])

  // Focus automatique sur mot de passe si email pré-rempli
  useEffect(() => {
    const { rememberMe, lastEmail } = rememberMeUtils.load()
    
    if (rememberMe && lastEmail && loginData.email && !loginData.password && passwordInputRef.current) {
      setTimeout(() => {
        passwordInputRef.current?.focus()
      }, 500)
    }
  }, [loginData.email, loginData.password])

  // Gestion URL callback
  useEffect(() => {
    if (!hasInitialized.current) return

    const authStatus = searchParams.get('auth')
    if (!authStatus) return
    
    if (authStatus === 'success') {
      setLocalSuccess(t.authSuccess)
    } else if (authStatus === 'error') {
      setLocalError(t.authError)
    } else if (authStatus === 'incomplete') {
      setLocalError(t.authIncomplete)
    }
    
    // Nettoyer l'URL
    const url = new URL(window.location.href)
    url.searchParams.delete('auth')
    window.history.replaceState({}, '', url.pathname)
    
    // Masquer les messages après 3 secondes
    const timer = setTimeout(() => {
      setLocalSuccess('')
      setLocalError('')
    }, 3000)
    
    return () => clearTimeout(timer)
  }, [searchParams, t])

  // 🔒 EFFET POUR BLOQUER LE SCROLL HTML + BODY EN MODE SIGNUP (CORRIGÉ)
  useEffect(() => {
    if (isSignupMode) {
      // Bloquer le scroll du body ET du html
      document.body.style.overflow = 'hidden'
      document.documentElement.style.overflow = 'hidden'
    } else {
      // Restaurer le scroll du body ET du html
      document.body.style.overflow = 'unset'
      document.documentElement.style.overflow = 'unset'
    }
    
    // Cleanup au démontage
    return () => {
      document.body.style.overflow = 'unset'
      document.documentElement.style.overflow = 'unset'
    }
  }, [isSignupMode])

  // 🔒 EFFET POUR BLOQUER LE SCROLL HTML + BODY EN MODE SIGNUP (CORRIGÉ)
  useEffect(() => {
    if (isSignupMode) {
      // Bloquer le scroll du body ET du html
      document.body.style.overflow = 'hidden'
      document.documentElement.style.overflow = 'hidden'
    } else {
      // Restaurer le scroll du body ET du html
      document.body.style.overflow = 'unset'
      document.documentElement.style.overflow = 'unset'
    }
    
    // Cleanup au démontage
    return () => {
      document.body.style.overflow = 'unset'
      document.documentElement.style.overflow = 'unset'
    }
  }, [isSignupMode])

  // Affichage conditionnel avec spinner amélioré
  if (!hasHydrated || !hasInitialized.current) {
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

  const handleLanguageChange = (newLanguage: Language) => {
    setCurrentLanguage(newLanguage)
    localStorage.setItem('intelia-language', newLanguage)
  }

  const toggleMode = () => {
    console.log('🔄 [UI] Basculement mode:', isSignupMode ? 'signup → login' : 'login → signup')
    setIsSignupMode(!isSignupMode)
    setLocalError('')
    setLocalSuccess('')
    
    if (!isSignupMode) {
      // Passage en mode signup - vider login
      setLoginData({ email: '', password: '', rememberMe: false })
    } else {
      // Retour en mode login - restaurer EMAIL avec fonction utilitaire
      const { rememberMe, lastEmail } = rememberMeUtils.load()
      
      console.log('🔄 [Toggle] Retour login - restore email:', lastEmail)
      
      setLoginData({ 
        email: lastEmail, 
        password: '', // Toujours vider mot de passe
        rememberMe 
      })
      
      // Message si email restauré
      if (rememberMe && lastEmail) {
        setLocalSuccess(`Email restauré : ${lastEmail}`)
        setTimeout(() => setLocalSuccess(''), 3000)
      }
    }
    
    setSignupData({
      email: '', password: '', confirmPassword: '',
      firstName: '', lastName: '', linkedinProfile: '',
      country: '', countryCode: '', areaCode: '', phoneNumber: '',
      companyName: '', companyWebsite: '', companyLinkedin: ''
    })
  }

  console.log('🎨 [Render] Rendu de la page principale')

  return (
    <>
      {/* PAGE PRINCIPALE (LOGIN) - RETRAIT DE LA CONDITION overflow-hidden */}
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
        
        {/* ⭐ BOÎTE DE DEBUG GLOBALE - RETIRÉE EN PRODUCTION */}
        {process.env.NODE_ENV === 'development' && (
          <div className="fixed top-16 right-4 bg-purple-50 border border-purple-200 rounded-lg p-4 text-xs max-w-sm z-50">
            <div className="font-semibold text-purple-800 mb-2">🧪 Debug Global</div>
            <div className="space-y-1 text-purple-700">
              <div>🎭 Mode: <span className="font-mono bg-purple-100 px-1 rounded">{isSignupMode ? 'Modal' : 'Page'}</span></div>
              <div>📊 Pays: <span className="font-mono bg-purple-100 px-1 rounded">{countries.length}</span></div>
              <div>⏳ Loading: <span className="font-mono bg-purple-100 px-1 rounded">{countriesLoading ? 'Oui' : 'Non'}</span></div>
              <div>🔄 Fallback: <span className="font-mono bg-purple-100 px-1 rounded">{usingFallback ? 'Oui' : 'Non'}</span></div>
            </div>
            <button 
              onClick={toggleMode}
              className="mt-2 text-xs bg-purple-100 hover:bg-purple-200 px-2 py-1 rounded"
            >
              {isSignupMode ? 'Fermer Modal' : 'Ouvrir Modal'}
            </button>
          </div>
        )}
        
        <div className="absolute top-4 right-4">
          <LanguageSelector onLanguageChange={(lang) => {
            setCurrentLanguage(lang)
            localStorage.setItem('intelia-language', lang)
          }} currentLanguage={currentLanguage} />
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
            
            {/* Messages d'erreur et succès pour login */}
            {localError && !isSignupMode && (
              <AlertMessage 
                type="error" 
                title={t.loginError} 
                message={localError} 
              />
            )}

            {localSuccess && !isSignupMode && (
              <AlertMessage 
                type="success" 
                title="" 
                message={localSuccess} 
              />
            )}

            {/* FORMULAIRE DE CONNEXION */}
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
                  <div className="mt-1">
                    <PasswordInput
                      id="password"
                      name="password"
                      value={loginData.password}
                      onChange={(e) => handleLoginChange('password', e.target.value)}
                      autoComplete="current-password"
                      required
                    />
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
                        console.log('🛯 [Checkbox] Événement onChange déclenché!')
                        console.log('🛯 [Checkbox] e.target.checked:', e.target.checked)
                        console.log('🛯 [Checkbox] État actuel rememberMe:', loginData.rememberMe)
                        
                        // Appel simplifié et direct
                        handleLoginChange('rememberMe', e.target.checked)
                      }}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      disabled={isLoading}
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
                    disabled={isLoading || !loginData.email || !loginData.password}
                    className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isLoading ? (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        <span>{t.connecting}</span>
                      </div>
                    ) : (
                      t.login
                    )}
                  </button>
                </div>
              </div>
            </form>

            {/* Bouton pour ouvrir la modale d'inscription */}
            <div className="mt-6 text-center">
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

            {/* Footer */}
            <AuthFooter t={t} />
          </div>
        </div>
      </div>

      {/* 🔧 MODAL D'INSCRIPTION - VERSION CORRIGÉE SANS DOUBLE SCROLL */}
      {isSignupMode && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-50 p-4 overflow-hidden overscroll-none">
          <div className="w-full max-w-2xl mx-auto bg-white rounded-lg shadow-xl max-h-[calc(100vh-2rem)] overflow-y-auto overscroll-contain">
              
              {/* Header de la modale avec bouton fermer */}
              <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-lg">
                <h3 className="text-lg font-semibold text-gray-900">{t.createAccount}</h3>
                <button
                  onClick={toggleMode}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Corps de la modale */}
              <div className="flex-1 px-6 py-4">
                
                {/* Messages d'erreur et succès pour signup */}
                {localError && (
                  <AlertMessage 
                    type="error" 
                    title={t.signupError} 
                    message={localError} 
                  />
                )}

                {localSuccess && (
                  <AlertMessage 
                    type="success" 
                    title="" 
                    message={localSuccess} 
                  />
                )}

                {/* FORMULAIRE D'INSCRIPTION */}
                <form onSubmit={handleSignup} onKeyPress={handleKeyPress}>
                  <div className="space-y-6">
                    {/* Section Informations personnelles */}
                    <div className="border-b border-gray-200 pb-6">
                      <h4 className="text-md font-medium text-gray-900 mb-4">{t.personalInfo}</h4>
                      
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
                      <h4 className="text-md font-medium text-gray-900 mb-4">{t.contact}</h4>
                      
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

                      {/* Sélecteur de pays */}
                      <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700">
                          {t.country} <span className="text-red-500">{t.required}</span>
                        </label>
                        
                        {countriesLoading ? (
                          <div className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-gray-50">
                            <div className="flex items-center space-x-2">
                              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                              <span className="text-sm text-gray-600">{t.loadingCountries}</span>
                            </div>
                          </div>
                        ) : (
                          <select
                            required
                            value={signupData.country}
                            onChange={(e) => handleSignupChange('country', e.target.value)}
                            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-white shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          >
                            <option value="">{t.selectCountry}</option>
                            {countries.map((country) => (
                              <option key={country.value} value={country.value}>
                                {country.flag ? `${country.flag} ` : ''}{country.label} ({country.phoneCode})
                              </option>
                            ))}
                          </select>
                        )}
                      </div>

                      {/* Téléphone optionnel */}
                      <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t.phoneNumber} {t.optional}
                        </label>
                        <div className="grid grid-cols-3 gap-2">
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">{t.countryCode}</label>
                            <input
                              type="text"
                              placeholder="+1"
                              value={signupData.countryCode}
                              onChange={(e) => handleSignupChange('countryCode', e.target.value)}
                              className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">{t.areaCode}</label>
                            <input
                              type="text"
                              placeholder="514"
                              value={signupData.areaCode}
                              onChange={(e) => handleSignupChange('areaCode', e.target.value)}
                              className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">{t.phoneNumber}</label>
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
                    </div>

                    {/* Section Entreprise */}
                    <div className="border-b border-gray-200 pb-6">
                      <h4 className="text-md font-medium text-gray-900 mb-4">{t.company}</h4>
                      
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
                        <div className="mt-1">
                          <PasswordInput
                            value={signupData.password}
                            onChange={(e) => handleSignupChange('password', e.target.value)}
                            required
                          />
                        </div>
                      </div>

                      <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700">
                          {t.confirmPassword} <span className="text-red-500">{t.required}</span>
                        </label>
                        <div className="mt-1">
                          <PasswordInput
                            value={signupData.confirmPassword}
                            onChange={(e) => handleSignupChange('confirmPassword', e.target.value)}
                            required
                          />
                        </div>
                      </div>

                      {/* Indicateur de correspondance des mots de passe */}
                      <PasswordMatchIndicator 
                        password={signupData.password} 
                        confirmPassword={signupData.confirmPassword} 
                      />
                    </div>
                  </div>
                </form>
              </div>

              {/* Footer de la modale avec boutons */}
              <div className="flex-shrink-0 bg-gray-50 border-t border-gray-200 px-6 py-4 rounded-b-lg">
                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={toggleMode}
                    className="flex-1 rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  >
                    {t.backToLogin}
                  </button>
                  <button
                    onClick={handleSignup}
                    disabled={isLoading}
                    className="flex-1 rounded-md border border-transparent bg-green-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? t.creating : t.createAccount}
                  </button>
                </div>
              </div>
            </div>
          </div>
      )}
      {/* 🔧 MODAL D'INSCRIPTION - VERSION CORRIGÉE SANS DOUBLE SCROLL */}
      {isSignupMode && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-50 p-4 overflow-hidden overscroll-none">
          <div className="w-full max-w-2xl mx-auto bg-white rounded-lg shadow-xl max-h-[calc(100vh-2rem)] overflow-y-auto overscroll-contain">
              
              {/* Header de la modale avec bouton fermer */}
              <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-lg">
                <h3 className="text-lg font-semibold text-gray-900">{t.createAccount}</h3>
                <button
                  onClick={toggleMode}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Corps de la modale */}
              <div className="flex-1 px-6 py-4">
                
                {/* Messages d'erreur et succès pour signup */}
                {localError && (
                  <AlertMessage 
                    type="error" 
                    title={t.signupError} 
                    message={localError} 
                  />
                )}

                {localSuccess && (
                  <AlertMessage 
                    type="success" 
                    title="" 
                    message={localSuccess} 
                  />
                )}

                {/* FORMULAIRE D'INSCRIPTION COMPLET */}
                <form onSubmit={handleSignup} onKeyPress={handleKeyPress}>
                  <div className="space-y-6">
                    {/* Section Informations personnelles */}
                    <div className="border-b border-gray-200 pb-6">
                      <h4 className="text-md font-medium text-gray-900 mb-4">{t.personalInfo}</h4>
                      
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
                            disabled={isLoading}
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
                            disabled={isLoading}
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
                          disabled={isLoading}
                        />
                      </div>
                    </div>

                    {/* Section Contact */}
                    <div className="border-b border-gray-200 pb-6">
                      <h4 className="text-md font-medium text-gray-900 mb-4">{t.contact}</h4>
                      
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
                          disabled={isLoading}
                        />
                      </div>

                      {/* Sélecteur de pays */}
                      <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700">
                          {t.country} <span className="text-red-500">{t.required}</span>
                        </label>
                        
                        {countriesLoading ? (
                          <div className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-gray-50">
                            <div className="flex items-center space-x-2">
                              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                              <span className="text-sm text-gray-600">{t.loadingCountries}</span>
                            </div>
                          </div>
                        ) : (
                          <select
                            required
                            value={signupData.country}
                            onChange={(e) => handleSignupChange('country', e.target.value)}
                            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-white shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                            disabled={isLoading}
                          >
                            <option value="">{t.selectCountry}</option>
                            {countries.map((country) => (
                              <option key={country.value} value={country.value}>
                                {country.flag ? `${country.flag} ` : ''}{country.label} ({country.phoneCode})
                              </option>
                            ))}
                          </select>
                        )}
                      </div>

                      {/* Téléphone optionnel */}
                      <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Téléphone {t.optional}
                        </label>
                        <div className="grid grid-cols-3 gap-3">
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">{t.countryCode}</label>
                            <input
                              type="text"
                              value={signupData.countryCode}
                              onChange={(e) => handleSignupChange('countryCode', e.target.value)}
                              placeholder="+1"
                              className="block w-full rounded-md border border-gray-300 px-2 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                              disabled={isLoading}
                            />
                          </div>
                          
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">{t.areaCode}</label>
                            <input
                              type="tel"
                              value={signupData.areaCode}
                              onChange={(e) => handleSignupChange('areaCode', e.target.value)}
                              placeholder="514"
                              maxLength={3}
                              className="block w-full rounded-md border border-gray-300 px-2 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                              disabled={isLoading}
                            />
                          </div>
                          
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">{t.phoneNumber}</label>
                            <input
                              type="tel"
                              value={signupData.phoneNumber}
                              onChange={(e) => handleSignupChange('phoneNumber', e.target.value)}
                              placeholder="1234567"
                              maxLength={7}
                              className="block w-full rounded-md border border-gray-300 px-2 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                              disabled={isLoading}
                            />
                          </div>
                        </div>
                        
                        {(signupData.countryCode || signupData.areaCode || signupData.phoneNumber) && (
                          <div className="mt-2">
                            {validatePhone(signupData.countryCode, signupData.areaCode, signupData.phoneNumber) ? (
                              <div className="flex items-center text-xs text-green-600">
                                <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                Format téléphone valide
                              </div>
                            ) : (
                              <div className="flex items-center text-xs text-red-600">
                                <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                Tous les champs téléphone sont requis
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Section Entreprise */}
                    <div className="border-b border-gray-200 pb-6">
                      <h4 className="text-md font-medium text-gray-900 mb-4">{t.company}</h4>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          {t.companyName} {t.optional}
                        </label>
                        <input
                          type="text"
                          value={signupData.companyName}
                          onChange={(e) => handleSignupChange('companyName', e.target.value)}
                          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          disabled={isLoading}
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
                          placeholder="https://www.entreprise.com"
                          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          disabled={isLoading}
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
                          disabled={isLoading}
                        />
                      </div>
                    </div>

                    {/* Section Mot de passe */}
                    <div>
                      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
                              placeholder="••••••••"
                              disabled={isLoading}
                            />
                            <button
                              type="button"
                              onClick={() => setShowPassword(!showPassword)}
                              className="absolute inset-y-0 right-0 pr-3 flex items-center"
                              tabIndex={-1}
                            >
                              <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                            </button>
                          </div>
                          {signupData.password && (
                            <div className="mt-2 space-y-1">
                              {(() => {
                                const validation = validatePassword(signupData.password)
                                return validation.errors.map((error, index) => (
                                  <div key={index} className="flex items-center text-xs text-red-600">
                                    <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                    </svg>
                                    {error}
                                  </div>
                                ))
                              })()}
                              {validatePassword(signupData.password).isValid && (
                                <div className="flex items-center text-xs text-green-600">
                                  <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                  </svg>
                                  Mot de passe valide
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        <div>
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
                              placeholder="••••••••"
                              disabled={isLoading}
                            />
                            <button
                              type="button"
                              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                              className="absolute inset-y-0 right-0 pr-3 flex items-center"
                              tabIndex={-1}
                            >
                              <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                            </button>
                          </div>
                          {signupData.confirmPassword && (
                            <div className="mt-2">
                              {signupData.password === signupData.confirmPassword ? (
                                <div className="flex items-center text-xs text-green-600">
                                  <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                  </svg>
                                  Mots de passe identiques
                                </div>
                              ) : (
                                <div className="flex items-center text-xs text-red-600">
                                  <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                  </svg>
                                  Les mots de passe ne correspondent pas
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </form>
              </div>

              {/* Footer de la modale avec boutons */}
              <div className="flex-shrink-0 bg-gray-50 border-t border-gray-200 px-6 py-4 rounded-b-lg">
                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={toggleMode}
                    className="flex-1 rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  >
                    {t.backToLogin}
                  </button>
                  <button
                    onClick={handleSignup}
                    disabled={isLoading}
                    className="flex-1 rounded-md border border-transparent bg-green-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? t.creating : t.createAccount}
                  </button>
                </div>
              </div>
            </div>
          </div>
      )}
}

// Export principal avec Suspense
export default function Page() {
  console.log('🎁 [Page] Composant Page principal appelé')
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <PageContent />
    </Suspense>
  )
}